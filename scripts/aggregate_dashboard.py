#!/usr/bin/env python3
"""Aggregate official decoded BUs using official polling-place geography.

python3 aggregate_dashboard.py --input decoded.json --manifest manifest.json --output dashboard.json
Repeat --input and --manifest to aggregate several batches, including all Santa Catarina.
"""
import argparse
import collections
import json
from pathlib import Path

DATA = Path('/private/tmp/cadorin-resultados-research')
CADASTRO = Path('/private/tmp/cadorin-bairros-research')
COUNT_FIELDS = ['votes','validVotes','nominalValidVotes','partyVotes','blankVotes','nullVotes','technicalNullVotes','subJudiceVotes','otherInvalidVotes','turnout','electorate']

def read(path):
    return json.loads(Path(path).read_text())

def coordinate(value):
    try:
        number = float(value.replace(',','.'))
        return None if number in (-1, -3) else number
    except (ValueError, AttributeError):
        return None

def add(group, row):
    for field in COUNT_FIELDS:
        group[field] = group.get(field, 0) + row[field]
    group['sections'] = group.get('sections', 0) + 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', action='append', required=True)
    ap.add_argument('--manifest', action='append', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    registration = read(CADASTRO / 'sc-secoes-locais-2026.json')
    register = {(r['CD_MUNICIPIO'], int(r['NR_ZONA']), int(r['NR_SECAO'])): r for r in registration}
    aggregates = collections.defaultdict(list)
    for r in registration:
        if r['DS_TIPO_SECAO_AGREGADA'] == 'Agregada':
            aggregates[(r['CD_MUNICIPIO'], int(r['NR_ZONA']), int(r['NR_SECAO_PRINCIPAL']))].append(int(r['NR_SECAO']))
    sources = {}
    for path in args.manifest:
        for r in read(path):
            sources[(str(r.get('municipio', 81795)), r['zona'], r['secao'])] = r
    spatial = {(str(r['zona']), str(r['local'])):r for r in read(CADASTRO / 'joinville-checagem-espacial-locais.json')}
    official = {}
    valid_candidates = {}
    candidate_statuses = {}
    valid_parties = {}
    sections, neighborhoods, locations, zones, municipality_totals = [], {}, {}, {}, {}
    seen = set()
    missing_in_unified = collections.Counter()
    for path in args.input:
        for bu in read(path):
            code = str(bu['municipio'])
            key = (code, bu['zona'], bu['secao'])
            assert key not in seen, ('Duplicate BU', key)
            seen.add(key)
            if code not in official:
                off = read(DATA / 'municipios' / ('sc'+code+'.json'))
                official[code] = off
                parties = [p for a in off['carg'][0]['agr'] for p in a['par']]
                candidate_statuses[code] = {int(c['n']): c['dvt'] for p in parties for c in p['cand']}
                valid_candidates[code] = {n for n, status in candidate_statuses[code].items() if status == 'Válido'}
                valid_parties[code] = {int(p['n']) for p in parties if p['dvt'] == 'Válido (legenda)'}
            reg = register[key]
            location_code = int(reg['NR_LOCAL_VOTACAO'])
            relocated = location_code != bu['local']
            assert not relocated or int(reg['NR_LOCAL_VOTACAO_ORIGINAL']) == bu['local'], ('BU/registered original local mismatch', key)
            assert reg['DS_TIPO_SECAO_AGREGADA'] == 'Principal', ('Nonprincipal BU', key)
            assert key in sources, ('Missing source manifest', key)
            location_id = f"{code}-{bu['zona']}-{location_code}"
            s = {
                'id': f"{code}-{bu['zona']}-{bu['secao']}",
                'locationId': location_id, 'municipalityCode': code, 'municipality': reg['NM_MUNICIPIO'],
                'zone': bu['zona'], 'section': bu['secao'], 'neighborhood': reg['NM_BAIRRO'],
                'locationCode': location_code, 'originalLocationCode': bu['local'], 'relocated': relocated,
                'votes': 0, 'validVotes': 0, 'nominalValidVotes': 0, 'partyVotes': 0,
                'blankVotes': 0, 'nullVotes': 0, 'technicalNullVotes': 0, 'subJudiceVotes': 0, 'otherInvalidVotes': 0,
                'turnout': bu['comparecimento'], 'electorate': bu['aptosBu'],
                'aggregatedSections': sorted(aggregates.get(key, [])),
                'source': sources[key]['url'], 'emittedAt': bu['emissao'],
            }
            for v in bu['votos']:
                n, amount, kind = v['numero'], v['votos'], v['tipo']
                if kind == 1:
                    if n in valid_candidates[code]:
                        s['nominalValidVotes'] += amount
                        if n == 30000:
                            s['votes'] += amount
                    elif n not in candidate_statuses[code]:
                        s['technicalNullVotes'] += amount
                        missing_in_unified[str(n)] += amount
                    elif candidate_statuses[code][n] == 'Anulado sub judice':
                        s['subJudiceVotes'] += amount
                    else:
                        s['otherInvalidVotes'] += amount
                elif kind == 2:
                    s['blankVotes'] += amount
                elif kind == 3:
                    s['nullVotes'] += amount
                elif kind == 4:
                    if v['partido'] in valid_parties[code]:
                        s['partyVotes'] += amount
                    else:
                        s['otherInvalidVotes'] += amount
                else:
                    raise AssertionError(('Unknown BU vote type', kind))
            s['validVotes'] = s['nominalValidVotes'] + s['partyVotes']
            s['nullVotes'] += s['technicalNullVotes']
            assert s['turnout'] == sum(s[k] for k in ['validVotes','blankVotes','nullVotes','subJudiceVotes','otherInvalidVotes']), ('BU totals mismatch', key)
            sections.append(s)
            neighborhood_key = (code, reg['NM_BAIRRO'])
            if neighborhood_key not in neighborhoods:
                neighborhoods[neighborhood_key] = {'municipalityCode':code,'name':reg['NM_BAIRRO'],'locationIds':set()}
            nb = neighborhoods[neighborhood_key]
            nb['locationIds'].add(location_id)
            add(nb,s)
            if location_id not in locations:
                lc = {
                    'municipalityCode':code,'id':location_id,'code':location_code,'name':reg['NM_LOCAL_VOTACAO'],
                    'zone':bu['zona'],'neighborhood':reg['NM_BAIRRO'],'address':reg['DS_ENDERECO'],
                    'latitude':coordinate(reg['NR_LATITUDE']),'longitude':coordinate(reg['NR_LONGITUDE']),
                    'sectionNumbers':[], 'aggregatedSectionNumbers':[],
                }
                if code == '81795':
                    lc['geographicNeighborhood'] = spatial[(str(bu['zona']),str(bu['local']))]['bairro_por_coordenada']
                locations[location_id] = lc
            lc = locations[location_id]
            lc['sectionNumbers'].append(s['section'])
            lc['aggregatedSectionNumbers'].extend(s['aggregatedSections'])
            add(lc,s)
            zone_key = (code,bu['zona'])
            if zone_key not in zones:
                zones[zone_key] = {'municipalityCode':code,'zone':bu['zona'],'name':f"Zona {bu['zona']}",'locationIds':set()}
            zones[zone_key]['locationIds'].add(location_id)
            add(zones[zone_key],s)
            if code not in municipality_totals:
                municipality_totals[code] = {'municipalityCode':code, 'name':reg['NM_MUNICIPIO']}
            add(municipality_totals[code],s)

    audit = []
    for code, agg in municipality_totals.items():
        off = official[code]
        candidate = next(c for a in off['carg'][0]['agr'] for p in a['par'] for c in p['cand'] if c['n'] == '30000')
        expected = {
            'votes':int(candidate['vap']), 'validVotes':int(off['v']['vv']),
            'nominalValidVotes':int(off['v']['vnom']), 'partyVotes':int(off['v']['vl']),
            'blankVotes':int(off['v']['vb']), 'nullVotes':int(off['v']['tvn']),
            'technicalNullVotes':int(off['v']['vnt']), 'subJudiceVotes':int(off['v']['vansj']),
            'turnout':int(off['e']['c']), 'electorate':int(off['e']['te']), 'sections':int(off['s']['st']),
        }
        differences = {k:{'actual':agg[k],'expected':v} for k,v in expected.items() if agg[k] != v}
        assert not differences, ('Municipality reconciliation failed',code,differences)
        audit.append({'municipalityCode':code,'passed':True,'totals':expected,'source':f'https://resultados.tse.jus.br/oficial/ele2026/6259/dados/sc/sc{code}-c0007-e006259-u.json'})
    for row in list(neighborhoods.values()) + list(zones.values()):
        row['locationIds'] = sorted(row['locationIds'])
        row['locations'] = len(row['locationIds'])
    for lc in locations.values():
        lc['sectionNumbers'].sort()
        lc['aggregatedSectionNumbers'].sort()
    out = {
        'metadata': {
            'electionYear':2026,'round':1,'electionCode':'6259','officeCode':'7','candidateNumber':30000,
            'candidateName':'MATHEUS CADORIN','registrationGeneratedAt':'2026-10-05T06:29:34-03:00',
            'neighborhoodDefinition':'Bairro/localidade do local de votação cadastrado no TSE; não corresponde necessariamente ao bairro de residência dos eleitores ou aos limites municipais atuais.',
            'validVoteDefinition':'Votos nominais com dvt Válido + legenda com dvt Válido (legenda), usando o resultado oficial do município. Exclui votos anulados, sub judice e votos em candidatos ausentes do resultado unificado (nulos técnicos).',
            'sectionDefinition':'Uma linha por seção principal/BU. Seções agregadas listadas separadamente; votos não são duplicados.',
                'registrationSource':'https://cdn.tse.jus.br/estatistica/sead/odsele/eleitorado_locais_votacao/eleitorado_local_votacao_2026.zip',
                'sourceManifests':args.manifest,'missingCandidateVotes':dict(missing_in_unified),
                'nullVoteDefinition':'nullVotes inclui technicalNullVotes, que é um subconjunto. Não somar esses dois campos.',
                'relocatedPollingPlaces':'A junção usa município+zona+seção. Quando BU.local coincide com o local original do cadastro TSE, o agrupamento territorial usa o local atual de votação informado no cadastro; originalLocationCode e relocated preservam essa informação.',
                'relocatedSections':sum(s['relocated'] for s in sections),
        },
        'neighborhoods': sorted(neighborhoods.values(),key=lambda r:(r['municipalityCode'],-r['votes'],r['name'])),
        'locations': sorted(locations.values(),key=lambda r:(r['municipalityCode'],-r['votes'],r['id'])),
        'sections': sorted(sections,key=lambda r:(r['municipalityCode'],r['zone'],r['section'])),
        'zones': sorted(zones.values(),key=lambda r:(r['municipalityCode'],r['zone'])),
        'municipalityAudit':audit,
        'sourceManifest':[{'municipalityCode':k[0],'zone':k[1],'section':k[2],**v} for k,v in sources.items() if k in seen],
    }
    Path(args.output).write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
    print(json.dumps({'output':args.output,'municipalities':len(audit),'neighborhoods':len(out['neighborhoods']),'locations':len(locations),'sections':len(sections),'votes':sum(s['votes'] for s in sections),'validVotes':sum(s['validVotes'] for s in sections)},ensure_ascii=False))

if __name__ == '__main__':
    main()
