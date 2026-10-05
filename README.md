# Cadorin · Votação 2026

Dashboard descritivo dos resultados oficiais do TSE para deputado estadual em Santa Catarina, primeiro turno de 2026. Consulta em 5 de outubro de 2026.

## Cobertura

295 municípios, 2.797 bairros/localidades do cadastro eleitoral, 3.450 locais e 17.326 seções principais. Foco inicial: Joinville, 15.043 votos, 43 bairros/localidades e 104 locais.

## Metodologia

Percentual principal = votos do candidato / votos válidos nominais e de legenda no mesmo recorte. O percentual oficial TSE baseado em votos concorrentes é preservado nos municípios. Bairros identificam o local de votação no cadastro eleitoral, não a residência de eleitores. Seções agregadas são contadas uma única vez.

245 remanejamentos usam o local atual do cadastro, conferido pelo código original do local no BU; ver metodologia no painel.

O painel contém dados estáticos, sem atualização automática. As fontes oficiais e relatórios de conferência estão na página Fontes e metodologia.

## Arquivos

`dist/` contém o site autocontido; abrir por servidor HTTP estático. `dist/base-completa.json` contém os dados. `scripts/validate_data.py` reconcilia níveis territoriais e os 295 municípios. Os scripts de leitura e agregação foram preservados para reprodutibilidade; seus insumos são os arquivos oficiais baixados da Justiça Eleitoral.

## Verificação

`python3 scripts/validate_data.py`

`node --check dist/app.js`
