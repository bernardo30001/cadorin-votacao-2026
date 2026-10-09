# Cadorin · Votação 2026

**Acessar o dashboard:** https://bernardo30001.github.io/cadorin-votacao-2026/

Dashboard descritivo dos resultados oficiais do TSE para deputado estadual em Santa Catarina, primeiro turno de 2026. Consulta em 5 de outubro de 2026.

## Cobertura

295 municípios, 2.797 bairros/localidades do cadastro eleitoral, 3.450 locais e 17.326 seções principais. Foco inicial: Joinville, 15.043 votos, 43 bairros/localidades e 104 locais.

## Metodologia

Percentual principal = votos do candidato / votos válidos nominais e de legenda no mesmo recorte. O percentual oficial TSE baseado em votos concorrentes é preservado nos municípios. Bairros identificam o local de votação no cadastro eleitoral, não a residência de eleitores. Seções agregadas são contadas uma única vez.

245 remanejamentos usam o local atual do cadastro, conferido pelo código original do local no BU; ver metodologia no painel.

O painel contém dados estáticos, sem atualização automática. As fontes oficiais e relatórios de conferência estão na página Fontes e metodologia.

## Emendas e votos por cidade

A aba [Emendas e votos](https://bernardo30001.github.io/cadorin-votacao-2026/#emendas) cruza os registros da planilha `Emendas.xlsx`, recebida em 9 de outubro de 2026, com a votação municipal de 2026 já publicada. As emendas abrangem 2023–2025. O ranking permite ordenar por valor destinado, valor com situação PAGO, votos, percentual de votos ou município, com filtros por ano e cidade.

Cada cidade tem um detalhamento com os objetos, números, processos, anos, valores e situações das emendas. Valores classificados como PAGO, NÃO PAGO e PAGTO PARCIAL permanecem separados. O valor integral de uma emenda parcialmente paga não é tratado como montante pago. Um registro compartilhado entre Ascurra, Apiúna e Rodeio aparece uma única vez no total geral e separado dos totais municipais, pois a planilha não informa rateio. Ausência de registro na planilha não comprova ausência de destinação.

O cruzamento é descritivo e não atribui os votos às emendas. Os votos preservam o retrato de 5 de outubro de 2026; importar a planilha não atualiza a apuração eleitoral. A aba Fontes e metodologia documenta a importação e suas correções de formato.

**Custo por voto** divide o valor total das emendas exclusivamente atribuídas ao município pelos votos de Cadorin em 2026. Inclui todas as situações de pagamento. A média do recorte é a razão entre as somas, respeitando ano e busca, com os votos de cada cidade com registros contados uma vez. Emendas compartilhadas entram uma vez nessa média apenas quando todas as cidades beneficiárias estão no recorte. Sem rateio, não entram no custo individual. Cidades sem registro não entram no denominador; custo individual com zero votos permanece indisponível. O resumo mostra apenas total destinado e custo médio, com conferências e filtros secundários recolhidos.

Para atualizar a base, execute `python3 scripts/import_emendas.py --help` e informe a nova planilha. O importador usa `openpyxl` para leitura, não altera o arquivo original e gera `dist/emendas.json` e `dist/emendas.js`. O arquivo original não é distribuído no site.

## Arquivos

`dist/` contém o site autocontido; abrir por servidor HTTP estático. `dist/base-completa.json` contém os dados. `scripts/validate_data.py` reconcilia níveis territoriais e os 295 municípios. Os scripts de leitura e agregação foram preservados para reprodutibilidade; seus insumos são os arquivos oficiais baixados da Justiça Eleitoral.

## Verificação

`python3 scripts/validate_data.py`

`node --check dist/app.js`

`node --check dist/emendas-ui.js`

## Publicação

O GitHub Pages publica o conteúdo de `dist/` automaticamente após atualizações na branch `main`. O processo também pode ser iniciado manualmente em Actions, no fluxo “Publicar dashboard no GitHub Pages”.
