import json, sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'dist'/'data.js'
d=json.loads(p.read_text().removeprefix('window.ELECTION_DATA = ').strip().removesuffix(';'))
assert len(d['municipalities'])==295
assert sum(c['votes'] for c in d['municipalities'])==d['state']['votes']==22776
assert len(d['sections'])==17326
assert len({s['id'] for s in d['sections']})==17326
locs={l['id']:l for l in d['locations']}
assert len(locs)==len(d['locations'])
for s in d['sections']:
 assert s['locationId'] in locs
 assert s['votes']<=s['validVotes']<=s['turnout']<=s['electorate']
 assert s['validVotes']==s['nominalValidVotes']+s['partyVotes']
for c in d['municipalities']:
 for group in ['neighborhoods','locations','sections','zones']:
  rows=[x for x in d[group] if x['municipalityCode']==c['code']]
  assert rows,(group,c['name'])
  for metric in ['votes','validVotes','turnout','electorate','blankVotes','nullVotes','subJudiceVotes']:
   assert sum(r[metric] for r in rows)==c[metric],(group,c['name'],metric)
for l in d['locations']:
 rows=[s for s in d['sections'] if s['locationId']==l['id']]
 assert len(rows)==l['sections']
 for field in ['votes','validVotes']:
  assert sum(s[field] for s in rows)==l[field]
for b in d['neighborhoods']:
 rows=[l for l in d['locations'] if l['municipalityCode']==b['municipalityCode'] and l['neighborhood']==b['name']]
 assert len(rows)==b['locations']
 assert sum(l['votes'] for l in rows)==b['votes']
print(json.dumps({'result':'PASS','municipalities':len(d['municipalities']),'neighborhoods':len(d['neighborhoods']),'locations':len(locs),'sections':len(d['sections']),'votes':d['state']['votes']},ensure_ascii=False))
