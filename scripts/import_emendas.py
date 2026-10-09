#!/usr/bin/env python3
"""Read the supplied amendments workbook and export public dashboard data.

Requires openpyxl for read-only extraction. The workbook is never changed.
Municipality names join the existing election base. Shared amounts are counted
once in the global total and never allocated to individual municipalities.
"""

import argparse
from collections import Counter
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
HEADERS = ["NÚMERO", "SGP-e", "OBJETO", "MUNICÍPIO", "VALOR", "SITUAÇÃO", "ANO"]
STATUSES = {"PAGO": "paidAmountCents", "NÃO PAGO": "unpaidAmountCents", "PAGTO PARCIAL": "partialAmountCents"}
ALIASES = {
    "barra do sul": "Balneário Barra do Sul",
    "concodia": "Concórdia",
    "sao lourenca do oeste": "São Lourenço do Oeste",
    "monste castelo": "Monte Castelo",
}
SHARED_CITIES = {"Ascurra, Apiúna e Rodeio": ["Ascurra", "Apiúna", "Rodeio"]}


def normalized(value):
    text = unicodedata.normalize("NFKD", str(value).strip())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).casefold().split())


def string_value(value):
    if value is None:
        return ""
    if isinstance(value, (float, int)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def reais(cents):
    integer, fraction = divmod(cents, 100)
    return "R$ " + f"{integer:,}".replace(",", ".") + f",{fraction:02d}"


def amount_cents(value, row, adjustments):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Plan1!E{row}: missing or invalid amount")
    if isinstance(value, (int, float)):
        amount = Decimal(str(value))
    elif row == 46 and str(value).strip() == "R$ 182.076.28":
        amount = Decimal("182076.28")
        adjustments.append({"cell": "E46", "original": value, "amountCents": 18207628,
                            "reason": "Interpretação de formatação: último ponto como separador dos centavos. A planilha original não foi alterada."})
    else:
        text = str(value).strip().replace("R$", "").replace(" ", "")
        if not re.fullmatch(r"(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}", text):
            raise ValueError(f"Plan1!E{row}: unrecognized currency format {value!r}")
        amount = Decimal(text.replace(".", "").replace(",", "."))
    if not amount.is_finite() or amount < 0 or amount * 100 != (amount * 100).to_integral_value():
        raise ValueError(f"Plan1!E{row}: amount must be nonnegative and have at most two decimals")
    return int(amount * 100)


def import_workbook(source, base, imported_date):
    import_label = date.fromisoformat(imported_date).strftime("%d/%m/%Y")
    election = json.loads(base.read_text(encoding="utf-8"))
    by_name = {normalized(m["name"]): m for m in election["municipalities"]}
    if len(by_name) != len(election["municipalities"]):
        raise ValueError("Election base contains duplicate normalized municipality names")
    workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
    sheet = workbook["Plan1"]
    rows = sheet.iter_rows(values_only=True)
    header = list(next(rows))[:7]
    if header != HEADERS:
        raise ValueError(f"Unexpected Plan1 header: {header!r}")

    records, adjustments, aliases, ignored = [], [], [], []
    source_subtotal = None
    numeric_source_total = 0
    for row_number, raw in enumerate(rows, 2):
        cells = (list(raw) + [None] * 7)[:7]
        number, process, obj, municipality, value, status, year = cells
        if not any(v is not None for v in cells):
            continue
        if not municipality and string_value(number) == "OBS*":
            ignored.append({"row": row_number, "reason": "Observação, sem valor transacional"})
            continue
        if not municipality and value is not None and not any(v is not None for i, v in enumerate(cells) if i != 4):
            if source_subtotal is not None:
                raise ValueError("Multiple source subtotals require review")
            source_subtotal = amount_cents(value, row_number, adjustments)
            ignored.append({"row": row_number, "reason": "Subtotal da planilha, não somado novamente"})
            continue
        if not all(v is not None for v in (obj, municipality, value, status, year)):
            raise ValueError(f"Incomplete amendment record at Plan1 row {row_number}")
        year_number = int(year)
        if Decimal(str(year)) != year_number:
            raise ValueError(f"Invalid year at row {row_number}")
        clean_status = string_value(status).upper()
        if clean_status not in STATUSES:
            raise ValueError(f"Unknown status at row {row_number}: {status!r}")
        original_municipality = string_value(municipality)
        names = SHARED_CITIES.get(original_municipality, [original_municipality])
        matched = []
        for name in names:
            key = normalized(name)
            mapped = ALIASES.get(key, name)
            city = by_name.get(normalized(mapped))
            if city is None:
                raise ValueError(f"Unmatched municipality at row {row_number}: {name!r}")
            if name != city["name"]:
                aliases.append({"source": name, "name": city["name"], "code": city["code"]})
            matched.append(city)
        amount = amount_cents(value, row_number, adjustments)
        if isinstance(value, (float, int)):
            numeric_source_total += amount
        record = {
            "id": f"plan1-r{row_number}", "sourceRow": row_number,
            "number": string_value(number), "process": string_value(process),
            "object": string_value(obj),
            "municipalityCodes": [str(city["code"]) for city in matched],
            "municipalityNames": [city["name"] for city in matched],
            "amountCents": amount, "year": year_number, "status": clean_status,
            "shared": len(matched) > 1,
        }
        if not isinstance(value, (int, float)):
            record["amountOriginal"] = string_value(value)
            record["amountNote"] = f"Valor textual interpretado como {reais(amount)}; original preservado para conferência."
        if original_municipality != ", ".join(record["municipalityNames"]):
            record["municipalityOriginal"] = original_municipality
        records.append(record)
    workbook.close()

    exact_keys = [tuple(json.dumps(r[k], ensure_ascii=False, sort_keys=True) for k in
                        ("number", "process", "object", "municipalityCodes", "amountCents", "year", "status")) for r in records]
    exact_duplicates = [key for key, count in Counter(exact_keys).items() if count > 1]
    number_keys = [(r["number"], r["year"]) for r in records if r["number"] not in ("", "Indicação")]
    number_duplicates = [key for key, count in Counter(number_keys).items() if count > 1]
    if exact_duplicates or number_duplicates:
        raise ValueError("Potential duplicate amendments require review before export")

    municipalities = {}
    for record in records:
        for code, name in zip(record["municipalityCodes"], record["municipalityNames"]):
            summary = municipalities.setdefault(code, {
                "code": code, "name": name, "amountCents": 0, "recordCount": 0,
                "paidAmountCents": 0, "unpaidAmountCents": 0, "partialAmountCents": 0,
                "sharedAmountCents": 0, "sharedRecordCount": 0,
            })
            if record["shared"]:
                summary["sharedAmountCents"] += record["amountCents"]
                summary["sharedRecordCount"] += 1
            else:
                summary["amountCents"] += record["amountCents"]
                summary["recordCount"] += 1
                summary[STATUSES[record["status"]]] += record["amountCents"]

    total = sum(r["amountCents"] for r in records)
    shared_total = sum(r["amountCents"] for r in records if r["shared"])
    by_status = [{"status": status, "recordCount": sum(r["status"] == status for r in records),
                  "amountCents": sum(r["amountCents"] for r in records if r["status"] == status)} for status in STATUSES]
    years = sorted({r["year"] for r in records})
    by_year = [{"year": year, "recordCount": sum(r["year"] == year for r in records),
                "amountCents": sum(r["amountCents"] for r in records if r["year"] == year)} for year in years]
    if sum(m["amountCents"] for m in municipalities.values()) + shared_total != total:
        raise AssertionError("Municipality totals do not reconcile")
    if sum(s["amountCents"] for s in by_status) != total or sum(y["amountCents"] for y in by_year) != total:
        raise AssertionError("Status/year totals do not reconcile")
    if source_subtotal != numeric_source_total:
        raise ValueError("Source subtotal differs from numeric source records; review needed")
    unique_aliases = {json.dumps(a, sort_keys=True, ensure_ascii=False): a for a in aliases}
    notes = [
        "Fonte: planilha Emendas.xlsx fornecida pelo usuário, aba Plan1. Situações de pagamento são as informadas na planilha, sem verificação externa ou atualização automática.",
        f"Valores registrados abrangem {min(years)} a {max(years)}. A importação de {import_label} não representa uma data de atualização das situações de pagamento.",
        "O total inclui emendas pagas, não pagas e com pagamento parcial. Para registros parciais, o valor efetivamente pago não foi informado e não foi estimado.",
        "Emendas compartilhadas são contadas uma vez no total geral. Sem rateio informado, aparecem como contexto nas cidades abrangidas e ficam fora dos totais municipais individuais.",
        "Nomes de municípios foram padronizados para correspondência com a base eleitoral. Contagens de outras abas e o subtotal não são somados novamente.",
    ]
    if adjustments:
        for adjustment in adjustments:
            notes.append(f"Plan1!{adjustment['cell']} contém o texto {adjustment['original']}, interpretado como {reais(adjustment['amountCents'])}. O arquivo original não foi alterado.")
    if total != source_subtotal:
        notes.append(f"O subtotal original de {reais(source_subtotal)} ignora células monetárias textuais. A soma após interpretar esses valores é {reais(total)}, uma diferença de {reais(total - source_subtotal)}.")
    return {
        "meta": {
            "sourceFile": source.name, "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "sheet": "Plan1", "sourceRange": f"A2:G{max(r['sourceRow'] for r in records)}",
            "importedDate": imported_date, "years": years, "currency": "BRL",
            "recordCount": len(records), "municipalityCount": len(municipalities),
            "individualMunicipalityCount": sum(m["recordCount"] > 0 for m in municipalities.values()),
            "totalAmountCents": total, "individualAmountCents": total - shared_total,
            "sharedAmountCents": shared_total, "sharedRecordCount": sum(r["shared"] for r in records),
            "sourceSubtotalCents": source_subtotal, "numericSourceTotalCents": numeric_source_total,
            "subtotalDifferenceCents": total - source_subtotal,
            "statusTotals": by_status, "yearTotals": by_year,
            "amountAdjustments": adjustments,
            "municipalityNormalizations": list(unique_aliases.values()),
            "ignoredRows": ignored, "unmatchedMunicipalities": [],
            "duplicateRecordCount": 0, "duplicateNumberYearCount": 0,
            "notes": notes,
        },
        "records": records,
        "municipalities": sorted(municipalities.values(), key=lambda m: (-m["amountCents"], normalized(m["name"]))),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Path to Emendas.xlsx (read-only)")
    parser.add_argument("--base", type=Path, default=ROOT / "dist/base-completa.json", help="Existing election dataset")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist", help="Directory for emendas.json and emendas.js")
    parser.add_argument("--imported-date", default="2026-10-09", help="Import date in YYYY-MM-DD format")
    args = parser.parse_args()
    data = import_workbook(args.source, args.base, args.imported_date)
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "emendas.json").write_text(serialized + "\n", encoding="utf-8")
    (args.output_dir / "emendas.js").write_text("window.AMENDMENTS_DATA=" + serialized + ";\n", encoding="utf-8")
    joinville = next(m for m in data["municipalities"] if m["name"] == "Joinville")
    print(json.dumps({"recordCount": data["meta"]["recordCount"],
                      "totalAmountCents": data["meta"]["totalAmountCents"],
                      "municipalityCount": data["meta"]["municipalityCount"],
                      "sharedAmountCents": data["meta"]["sharedAmountCents"],
                      "joinville": joinville}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
