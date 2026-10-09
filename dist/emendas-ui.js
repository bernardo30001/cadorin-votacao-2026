'use strict';

const amendmentMoneyFormat = new Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL', minimumFractionDigits:2, maximumFractionDigits:2});
const amendmentMoney = cents => amendmentMoneyFormat.format(cents / 100);
const amendmentMetricMoney = cents => `<span class="emenda-money-value"><span>R$</span><span>${amendmentMoney(cents).replace(/^R\$\s*/,'')}</span></span>`;
const amendmentNormalize = value => String(value || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('pt-BR');
const amendmentSortLabels = {amount:'Maior valor destinado', paid:'Maior valor em PAGO', votes:'Mais votos em 2026', percent:'Maior % dos votos válidos', cost:'Menor custo por voto', costDesc:'Maior custo por voto', name:'Cidade A–Z'};

function amendmentRecords(year = state.emendaYear) {
  return (window.AMENDMENTS_DATA?.records || []).filter(r => year === 'all' || String(r.year) === String(year));
}

function amendmentAggregate(records) {
  const result = {amountCents:0, paidAmountCents:0, unpaidAmountCents:0, partialAmountCents:0, recordCount:0, sharedAmountCents:0, sharedRecordCount:0};
  records.forEach(r => {
    if (r.shared) { result.sharedAmountCents += r.amountCents; result.sharedRecordCount++; return; }
    result.amountCents += r.amountCents;
    result.recordCount++;
    if (r.status === 'PAGO') result.paidAmountCents += r.amountCents;
    if (r.status === 'NÃO PAGO') result.unpaidAmountCents += r.amountCents;
    if (r.status === 'PAGTO PARCIAL') result.partialAmountCents += r.amountCents;
  });
  return result;
}

function amendmentCityRows() {
  const records = amendmentRecords(), query = amendmentNormalize(state.emendaSearch);
  return D.municipalities.map(c => ({...c, ...amendmentAggregate(records.filter(r => r.municipalityCodes.includes(String(c.code))))}))
    .filter(c => (state.emendaAll || c.recordCount || c.sharedRecordCount) && amendmentNormalize(c.name).includes(query))
    .sort((a,b) => {
      if (['cost','costDesc'].includes(state.emendaSort)) {
        const ac=amendmentCost(a),bc=amendmentCost(b);
        if(ac===null&&bc!==null)return 1;
        if(bc===null&&ac!==null)return -1;
        if(ac!==null&&bc!==null&&ac!==bc)return state.emendaSort==='cost'?ac-bc:bc-ac;
      }
      const difference = ['name','cost','costDesc'].includes(state.emendaSort) ? 0 : state.emendaSort === 'paid' ? b.paidAmountCents-a.paidAmountCents : state.emendaSort === 'votes' ? b.votes-a.votes : state.emendaSort === 'percent' ? (pct(b.votes,b.validVotes)||0)-(pct(a.votes,a.validVotes)||0) : b.amountCents-a.amountCents;
      return difference || a.name.localeCompare(b.name, 'pt-BR');
    });
}

function amendmentCost(city) {
  return city.recordCount && city.votes>0 ? city.amountCents/city.votes : null;
}

function amendmentCostLabel(city, asMetric=false) {
  const cost=amendmentCost(city);
  if(cost!==null)return asMetric?amendmentMetricMoney(cost):amendmentMoney(cost);
  if(!city.recordCount)return city.sharedRecordCount?'Sem rateio':'Sem registro';
  return 'Sem votos';
}

function amendmentScope(rows,records) {
  const codes=new Set(rows.map(c=>String(c.code)));
  const relevant=records.filter(r=>r.municipalityCodes.some(code=>codes.has(code)));
  // A shared amount enters a filtered total only with every beneficiary city.
  const included=relevant.filter(r=>r.municipalityCodes.every(code=>codes.has(code)));
  const recipients=new Set(included.flatMap(r=>r.municipalityCodes));
  const votes=rows.filter(c=>recipients.has(String(c.code))).reduce((sum,c)=>sum+c.votes,0);
  const amountCents=included.reduce((sum,r)=>sum+r.amountCents,0);
  return {relevant,included,votes,amountCents,costCents:included.length&&votes>0?amountCents/votes:null,partialShared:relevant.filter(r=>!included.includes(r)).length};
}

function amendmentPeriod() { return state.emendaYear === 'all' ? '2023–2025' : esc(state.emendaYear); }

function amendmentControls(detail = false) {
  const years=window.AMENDMENTS_DATA?.meta.years||[2023,2024,2025];
  const yearField=`<div class="emenda-field"><label for="emenda-year">Ano das emendas</label><select id="emenda-year"><option value="all" ${state.emendaYear==='all'?'selected':''}>Todos · 2023–2025</option>${years.map(y=>`<option value="${esc(y)}" ${String(y)===String(state.emendaYear)?'selected':''}>${esc(y)}</option>`).join('')}</select></div>`;
  if(detail)return `<div class="toolbar emenda-toolbar emenda-main-controls"><div class="emenda-field emenda-city-field"><label for="emenda-city">Cidade</label><select id="emenda-city"><option value="">Todas as cidades · ranking</option>${[...D.municipalities].sort((a,b)=>a.name.localeCompare(b.name,'pt-BR')).map(c=>`<option value="${esc(c.code)}" ${String(c.code)===state.emendaCity?'selected':''}>${esc(c.name)}</option>`).join('')}</select></div>${yearField}</div>`;
  return `<div class="toolbar emenda-toolbar emenda-main-controls"><div class="emenda-field emenda-search-field"><label for="emenda-search">Buscar cidade</label><input type="search" id="emenda-search" value="${esc(state.emendaSearch)}" placeholder="Nome da cidade…"></div>${yearField}<details class="emenda-filters" ${state.emendaFiltersOpen?'open':''}><summary>Mais filtros${state.emendaAll?' · todas as cidades':''}</summary><div class="emenda-extra-controls"><div class="emenda-field"><label for="emenda-sort">Ordenar por</label><select id="emenda-sort">${Object.entries(amendmentSortLabels).map(([key,label])=>`<option value="${key}" ${state.emendaSort===key?'selected':''}>${label}</option>`).join('')}</select></div><label class="emenda-checkbox"><input type="checkbox" id="emenda-all" ${state.emendaAll?'checked':''}> Incluir cidades sem registro</label></div></details></div>`;
}

function amendmentSourceNote() {
  return `<p class="small emenda-source">Emendas: <strong>Emendas.xlsx</strong>, recebida em 09/10/2026, anos 2023–2025. Votação: base TSE consultada em 05/10/2026. “Destinado” é o valor registrado na planilha. A situação de pagamento é a informada nela; não há valor efetivamente pago para os registros parciais.</p>`;
}

function amendmentNormalizationNote() {
  return `<p><strong>Valor interpretado na planilha:</strong> E46 contém “R$ 182.076.28”, interpretado como R$ 182.076,28. O total original de R$ 35.114.327,30 não incluía a célula textual. A base completa do painel soma R$ 35.296.403,58. O arquivo original foi preservado.</p>`;
}

function amendmentStatus(status) {
  const type = status === 'PAGO' ? 'paid' : status === 'NÃO PAGO' ? 'unpaid' : 'partial';
  return `<span class="emenda-status emenda-status-${type}">${esc(status)}</span>`;
}

function amendmentRecordsTable(records, shared = false) {
  if (!records.length) return `<div class="empty"><strong>Sem registro neste recorte</strong>A ausência na planilha não permite concluir que não houve destinação de recursos.</div>`;
  return `<div class="table-wrap"><table class="emenda-records"><thead><tr><th scope="col">Emenda / processo</th>${shared?'<th scope="col">Cidades indicadas</th>':''}<th scope="col">Objeto</th><th scope="col">Ano</th><th scope="col" class="num">${shared?'Valor conjunto':'Valor destinado'}</th><th scope="col">Situação</th></tr></thead><tbody>${[...records].sort((a,b)=>b.year-a.year || b.amountCents-a.amountCents || a.sourceRow-b.sourceRow).map(r=>`<tr><td><strong>${esc(r.number||'Não informado')}</strong><small>${esc(r.process||'Processo não informado')}</small><small>Linha ${n(r.sourceRow)} da planilha</small></td>${shared?`<td class="emenda-shared-cities">${r.municipalityNames.map(esc).join(' · ')}</td>`:''}<td class="emenda-object">${esc(r.object||'Objeto não informado')}</td><td>${esc(r.year)}</td><td class="num"><strong>${amendmentMoney(r.amountCents)}</strong>${r.sourceRow===46?'<small class="emenda-value-note">Valor interpretado da célula E46;<br>ver Fontes e metodologia.</small>':''}</td><td>${amendmentStatus(r.status)}</td></tr>`).join('')}</tbody></table></div>`;
}

function amendmentSharedPanel(records) {
  const shared = records.filter(r=>r.shared);
  if (!shared.length) return '';
  return panel('Emendas compartilhadas', 'Valores conjuntos, apresentados uma única vez e fora dos totais exclusivos de cada cidade.', `<div class="callout emenda-inline-note">${amendmentMoney(shared.reduce((sum,r)=>sum+r.amountCents,0))} em ${n(shared.length)} registro${shared.length===1?'':'s'}. A planilha não informa a divisão entre as cidades; nenhum rateio foi estimado.</div>${amendmentRecordsTable(shared,true)}`);
}

function amendmentSortHeader(key, text, numeric = false) {
  const active=state.emendaSort===key||(key==='cost'&&state.emendaSort==='costDesc');
  const ascending=state.emendaSort==='name'||state.emendaSort==='cost';
  return `<th scope="col" ${numeric?'class="num"':''} aria-sort="${active?(ascending?'ascending':'descending'):'none'}"><button class="emenda-sort-button" data-emenda-sort="${key}">${text}${active?(ascending?' ↑':' ↓'):''}</button></th>`;
}

function amendmentRanking() {
  const rows=amendmentCityRows(),scope=amendmentScope(rows,amendmentRecords());
  state.emendaPage=Math.max(0,Math.min(state.emendaPage,Math.ceil(rows.length/25)-1));
  const start=state.emendaPage*25,list=rows.slice(start,start+25);
  const total=scope.included.length?amendmentMetricMoney(scope.amountCents):scope.relevant.length?'Sem rateio':'Sem registro';
  const average=scope.costCents!==null?amendmentMetricMoney(scope.costCents):scope.included.length?'Sem votos':scope.relevant.length?'Sem rateio':'Sem registro';
  const table=rows.length?`<div class="table-wrap"><table class="emenda-ranking"><thead><tr>${amendmentSortHeader('name','Cidade')}${amendmentSortHeader('amount','Total destinado',true)}${amendmentSortHeader('votes','Votos 2026',true)}${amendmentSortHeader('cost','Custo por voto',true)}</tr></thead><tbody>${list.map(c=>`<tr class="${String(c.code)==='81795'?'highlight-row':''}"><td><button class="row-link" data-emenda-city="${esc(c.code)}">${esc(c.name)}</button>${c.sharedRecordCount?'<small>Compartilhada em separado</small>':''}</td><td class="num"><strong>${c.recordCount?amendmentMoney(c.amountCents):'<span class="emenda-no-record">'+(c.sharedRecordCount?'Sem rateio':'Sem registro')+'</span>'}</strong></td><td class="num">${n(c.votes)}</td><td class="num"><strong>${amendmentCostLabel(c)}</strong></td></tr>`).join('')}</tbody></table></div><div class="table-foot"><span>${n(start+1)}–${n(Math.min(start+25,rows.length))} de ${n(rows.length)} cidades</span><div class="pagination"><button data-emenda-page="-1" ${state.emendaPage===0?'disabled':''} aria-label="Página anterior de emendas">←</button><span>${state.emendaPage+1} / ${Math.max(1,Math.ceil(rows.length/25))}</span><button data-emenda-page="1" ${start+25>=rows.length?'disabled':''} aria-label="Próxima página de emendas">→</button></div></div>`:'<div class="empty"><strong>Nenhuma cidade encontrada</strong>Ajuste a busca ou o ano.</div>';
  return `<div class="emenda-view"><div class="metrics emenda-metrics emenda-overview-metrics">${metric('Total destinado',total,amendmentPeriod()+' · valores registrados',true)}${metric('Custo médio por voto',average,scope.included.length?'Total destinado ÷ '+n(scope.votes)+' votos':'Nenhum total atribuível neste recorte')}</div>${scope.partialShared?'<p class="small emenda-scope-note">Emenda compartilhada fora do total filtrado: não há rateio para atribuir seu valor apenas às cidades desta busca.</p>':''}${panel('Emendas por cidade','Clique na cidade para ver os detalhes.',amendmentControls()+table)}<details class="emenda-details"><summary>Como o cálculo funciona e conferência da fonte</summary><div class="emenda-details-body"><p><strong>Custo por voto:</strong> total de emendas da cidade ÷ votos de Cadorin em 2026. Inclui os valores registrados em todas as situações de pagamento.</p><p><strong>Média do recorte:</strong> soma das emendas ÷ soma dos votos das cidades com registros, contadas uma única vez. Os filtros de ano e busca são respeitados. As cidades sem registro não entram nessa média.</p><p>Valores compartilhados entram uma vez na média somente quando todas as cidades beneficiárias estão no recorte. Sem rateio, ficam fora dos custos individuais. Sem votos, a divisão fica indisponível.</p>${amendmentNormalizationNote()}${amendmentSourceNote()}</div></details>${scope.relevant.some(r=>r.shared)?`<details class="emenda-details"><summary>Emendas compartilhadas · sem rateio</summary><div class="emenda-details-body">${amendmentSharedPanel(scope.relevant)}</div></details>`:''}</div>`;
}

function amendmentCityDetail() {
  const city=D.municipalities.find(c=>String(c.code)===state.emendaCity);
  if(!city)return amendmentRanking();
  const records=amendmentRecords().filter(r=>r.municipalityCodes.includes(String(city.code))),summary=amendmentAggregate(records),exclusive=records.filter(r=>!r.shared),row={...city,...summary};
  const total=exclusive.length?amendmentMetricMoney(summary.amountCents):summary.sharedRecordCount?'Sem rateio':'Sem registro';
  return `<div class="emenda-view"><button class="back" data-emenda-city="">← Voltar ao ranking</button><div class="metrics emenda-metrics emenda-city-metrics">${metric('Total destinado',total,amendmentPeriod()+' · exclusivo da cidade',true)}${metric('Votos em 2026',n(city.votes),p(pct(city.votes,city.validVotes))+' dos votos válidos')}${metric('Custo por voto',amendmentCostLabel(row,true),'Total destinado ÷ votos de 2026')}</div>${panel('Emendas de '+esc(city.name),'',amendmentControls(true),`<button class="text-link" data-city="${esc(city.code)}">Ver votação e bairros ↗</button>`)}${exclusive.length?`<details class="emenda-details"><summary>Situação dos pagamentos</summary><div class="emenda-details-body"><div class="emenda-payment-summary"><div><span class="emenda-status emenda-status-paid">PAGO</span><strong>${amendmentMoney(summary.paidAmountCents)}</strong></div><div><span class="emenda-status emenda-status-unpaid">NÃO PAGO</span><strong>${amendmentMoney(summary.unpaidAmountCents)}</strong></div><div><span class="emenda-status emenda-status-partial">PAGTO PARCIAL</span><strong>${amendmentMoney(summary.partialAmountCents)}</strong><small>Valor total das emendas; parcela paga não informada</small></div></div></div></details>`:''}${panel('Emendas individuais',amendmentPeriod()+' · '+n(exclusive.length)+' registros',amendmentRecordsTable(exclusive),exclusive.length?'<button class="text-link" id="emenda-export-detail">↓ Exportar emendas</button>':'')}${amendmentSharedPanel(records)}<details class="emenda-details"><summary>Sobre os valores e o custo por voto</summary><div class="emenda-details-body"><p>Custo por voto = total destinado exclusivamente à cidade ÷ votos de Cadorin em 2026. Inclui todos os estados de pagamento. Valores compartilhados sem rateio ficam fora dessa divisão.</p>${amendmentNormalizationNote()}${amendmentSourceNote()}</div></details></div>`;
}

function renderAmendments() {
  if (!window.AMENDMENTS_DATA) return '<div class="empty"><strong>Não foi possível carregar as emendas</strong>Atualize a página para tentar novamente.</div>';
  return state.emendaCity ? amendmentCityDetail() : amendmentRanking();
}

function bindAmendments() {
  document.querySelectorAll('[data-emenda-city]').forEach(button=>button.onclick=()=>{if(button.hasAttribute('data-emenda-reset-year'))state.emendaYear='all';openAmendments(button.dataset.emendaCity);});
  document.querySelectorAll('[data-emenda-page]').forEach(button=>button.onclick=()=>{state.emendaPage+=Number(button.dataset.emendaPage);render();});
  const setSort = value => { state.emendaSort=value;state.emendaPage=0;render(); };
  document.querySelectorAll('[data-emenda-sort]').forEach(button=>button.onclick=()=>setSort(button.dataset.emendaSort==='cost'&&state.emendaSort==='cost'?'costDesc':button.dataset.emendaSort));
  const filters=$('.emenda-filters');if(filters)filters.ontoggle=()=>{state.emendaFiltersOpen=filters.open;};
  const city = $('#emenda-city'), year = $('#emenda-year'), search = $('#emenda-search'), sort = $('#emenda-sort'), all = $('#emenda-all'), exportDetail = $('#emenda-export-detail');
  if (city) city.onchange=()=>openAmendments(city.value);
  if (year) year.onchange=()=>{state.emendaYear=year.value;state.emendaPage=0;syncAmendmentsHash();render();};
  if (search) search.oninput=()=>{const position=search.selectionStart;state.emendaSearch=search.value;state.emendaPage=0;render();const input=$('#emenda-search');input.focus();input.setSelectionRange(position,position);};
  if (sort) sort.onchange=()=>setSort(sort.value);
  if (all) all.onchange=()=>{state.emendaAll=all.checked;state.emendaPage=0;render();};
  if (exportDetail) exportDetail.onclick=()=>exportAmendments(true);
}

function amendmentCsvDownload(rows, filename) {
  if (!rows.length) return;
  const keys=Object.keys(rows[0]), cell=value=>{let text=String(value??'');if(typeof value==='string'&&/^[\s\u0000-\u001f]*[=+@-]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"';};
  const csv='\uFEFF'+[keys.map(cell).join(';'),...rows.map(row=>keys.map(key=>cell(row[key])).join(';'))].join('\r\n');
  const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
}

function exportAmendments(detail = false) {
  if (!window.AMENDMENTS_DATA) return;
  const period=state.emendaYear==='all'?'2023-2025':state.emendaYear;
  if (detail && state.emendaCity) {
    const records=amendmentRecords().filter(r=>r.municipalityCodes.includes(state.emendaCity));
    amendmentCsvDownload(records.map(r=>({linha_planilha:r.sourceRow,numero_emenda:r.number,processo:r.process,objeto:r.object,ano:r.year,cidades:r.municipalityNames.join(' / '),codigos_tse:r.municipalityCodes.join(' / '),valor_emenda_reais:(r.amountCents/100).toFixed(2).replace('.',','),observacao_valor:r.sourceRow===46?'Célula E46 textual: R$ 182.076.28, interpretada como R$ 182.076,28; excluída do total da fórmula original':'',situacao:r.status,compartilhada:r.shared?'Sim — sem rateio; fora do total exclusivo':'Não',fonte:'Emendas.xlsx',recebida_em:'09/10/2026'})),`cadorin-emendas-${state.emendaCity}-${period}.csv`);
    return;
  }
  const selectedCity=D.municipalities.find(c=>String(c.code)===state.emendaCity);
  const rows=selectedCity?[{...selectedCity,...amendmentAggregate(amendmentRecords().filter(r=>r.municipalityCodes.includes(state.emendaCity)))}]:amendmentCityRows();
  amendmentCsvDownload(rows.map(c=>({codigo_municipio_tse:c.code,cidade:c.name,periodo_emendas:period,valor_destinado_exclusivo_reais:c.recordCount?(c.amountCents/100).toFixed(2).replace('.',','):'Sem registro',valor_em_situacao_pago_reais:c.recordCount?(c.paidAmountCents/100).toFixed(2).replace('.',','):'Sem registro',valor_em_situacao_nao_pago_reais:c.recordCount?(c.unpaidAmountCents/100).toFixed(2).replace('.',','):'Sem registro',valor_em_situacao_parcial_reais:c.recordCount?(c.partialAmountCents/100).toFixed(2).replace('.',','):'Sem registro',emendas_exclusivas:c.recordCount||'Sem registro',emendas_compartilhadas:c.sharedRecordCount,observacao_compartilhadas:c.sharedRecordCount?'Sem rateio; fora do total exclusivo da cidade':'',votos_cadorin_2026:c.votes,custo_por_voto_reais:amendmentCost(c)===null?amendmentCostLabel(c):(amendmentCost(c)/100).toFixed(2).replace('.',','),votos_validos_deputado_estadual:c.validVotes,percentual_votos_validos:c.validVotes?String(pct(c.votes,c.validVotes)).replace('.',','):'',fonte_emendas:'Emendas.xlsx · recebida 09/10/2026',fonte_votos:'TSE · consulta 05/10/2026'})),`cadorin-emendas-e-votos-${state.emendaCity||'cidades'}-${period}.csv`);
}

function amendmentsCitySummary(city) {
  if (!window.AMENDMENTS_DATA) return '';
  const records=amendmentRecords('all').filter(r=>r.municipalityCodes.includes(String(city.code))), summary=amendmentAggregate(records);
  return panel('Emendas destinadas a '+esc(city.name),'Planilha recebida em 09/10/2026 · anos 2023–2025',`<div class="panel-body emenda-city-summary"><div><span class="small">Valor exclusivo da cidade</span><strong>${summary.recordCount?amendmentMoney(summary.amountCents):'Sem registro'}</strong><p class="small">${summary.recordCount?n(summary.recordCount)+' emendas exclusivas':'Nenhum registro exclusivo na planilha'}${summary.sharedRecordCount?' · '+n(summary.sharedRecordCount)+' compartilhada(s), fora desse total':''}.</p></div><button class="secondary" data-emenda-city="${esc(city.code)}" data-emenda-reset-year>Abrir emendas e votos →</button></div>`);
}

function amendmentsMethod() {
  return `<h3>Emendas por cidade</h3><p><strong>Custo por voto:</strong> total de emendas atribuídas à cidade dividido pelos votos de Cadorin em 2026. A média do recorte divide a soma das emendas pela soma dos votos das cidades com registros, uma vez por cidade. Não é uma média simples dos quocientes. Registros compartilhados entram uma única vez na média quando todas as cidades beneficiárias estão no recorte; sem rateio, não entram no cálculo individual. Cidades sem registro não acrescentam votos ao denominador e zero votos torna o quociente individual indisponível.</p><p>A fonte é a planilha <strong>Emendas.xlsx</strong> fornecida em 09/10/2026, com registros de 2023, 2024 e 2025. Os valores são somados por município e por ano da emenda, mantendo número, processo, objeto e situação informada. “Valor destinado” não significa valor integralmente pago. O quadro PAGO soma o valor dos registros assim classificados; PAGTO PARCIAL exibe o valor total da emenda porque a planilha não informa a parcela paga.</p><p>A célula E46 contém o texto “R$ 182.076.28”, interpretado como R$ 182.076,28. A fórmula do total na célula E146 não inclui esse valor textual e resulta em R$ 35.114.327,30. O total importado pelo painel é R$ 35.296.403,58, incluindo a interpretação explicitada de E46. O arquivo original é preservado.</p><p>A emenda conjunta de R$ 100.000,00 para Ascurra, Apiúna e Rodeio aparece uma única vez no total do recorte e em quadro separado. Sem indicação de rateio, seu valor não é atribuído ao total exclusivo de nenhuma das três cidades. “Sem registro” indica ausência na planilha, sem afirmar ausência de repasses. Os votos continuam sendo os resultados de 2026 da base TSE consultada em 05/10/2026. A apresentação lado a lado não estabelece relação causal entre emendas e votação.</p><p><a href="emendas.json" download>Baixar base de emendas e notas da importação (JSON) ↓</a></p>`;
}
