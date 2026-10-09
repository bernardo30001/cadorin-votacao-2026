const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const dist = path.join(__dirname, '../dist');
const context = vm.createContext({
  window: { AMENDMENTS_DATA: JSON.parse(fs.readFileSync(path.join(dist, 'emendas.json'))) },
  D: JSON.parse(fs.readFileSync(path.join(dist, 'base-completa.json'))),
  state: { emendaYear: 'all', emendaSearch: '', emendaSort: 'amount', emendaAll: false, emendaCity: '' },
  pct: (a,b) => b ? 100*a/b : null,
});
vm.runInContext(fs.readFileSync(path.join(dist, 'emendas-ui.js'), 'utf8'), context);
const run = code => vm.runInContext(code, context);
const snapshot = code => JSON.parse(run(`JSON.stringify(${code})`));
const scope = () => snapshot('amendmentScope(amendmentCityRows(), amendmentRecords())');
const reais = cents => (cents/100).toFixed(2);
const set = values => Object.assign(context.state, values);

let summary = scope();
assert.equal(summary.amountCents, 3529640358);
assert.equal(summary.votes, 20138);
assert.equal(reais(summary.costCents), '1752.73');
assert.equal(summary.included.filter(r => r.shared).length, 1);

set({emendaAll: true});
assert.equal(scope().votes, 20138, 'Cities without amendment records must not dilute the mean');
set({emendaSearch: 'Joinville'});
assert.equal(reais(scope().costCents), '1322.56');
set({emendaYear: '2024'});
assert.equal(scope().amountCents, 767202538);
assert.equal(scope().votes, 15043);
assert.equal(reais(scope().costCents), '510.01');

set({emendaYear: 'all', emendaSearch: 'Ascurra'});
assert.equal(scope().amountCents, 85000000, 'Do not assign a joint grant in full to one city');
assert.equal(scope().votes, 182);
assert.equal(scope().partialShared, 1);
assert.equal(reais(scope().costCents), '4670.33');
set({emendaSearch: 'Apiúna'});
assert.equal(scope().costCents, null);
assert.equal(run('amendmentCostLabel(amendmentCityRows()[0])'), 'Sem rateio');

set({emendaSearch: 'Monte Castelo'});
assert.equal(scope().amountCents, 26000000);
assert.equal(scope().costCents, null);
assert.equal(run('amendmentCostLabel(amendmentCityRows()[0])'), 'Sem votos');
set({emendaSearch: 'Abdon Batista'});
assert.equal(scope().votes, 0);
assert.equal(scope().costCents, null);
assert.equal(run('amendmentCostLabel(amendmentCityRows()[0])'), 'Sem registro');
set({emendaSearch: 'nonexistent-city'});
assert.equal(scope().costCents, null);

for (const sort of ['cost','costDesc']) {
  set({emendaSearch: '', emendaSort: sort});
  const costs=snapshot('amendmentCityRows().map(amendmentCost)');
  const numbers=costs.filter(v=>v!==null);
  assert.ok(costs.slice(numbers.length).every(v=>v===null));
  assert.ok(numbers.every((v,i)=>!i||(sort==='cost'?v>=numbers[i-1]:v<=numbers[i-1])));
}

set({emendaSearch: 'Joinville'});
run('amendmentCsvDownload = rows => { capturedRows = rows; }; var capturedRows; exportAmendments();');
const exported = snapshot('capturedRows');
assert.equal(exported.length, 1);
assert.equal(exported[0].custo_por_voto_reais, '1322,56');
console.log('PASS: totals, weighted mean, filters, shared grants, zero votes, missing data, sorting and CSV.');
