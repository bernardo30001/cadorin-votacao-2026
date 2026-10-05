from der_reader import parse
from pathlib import Path
import json

def decode_file(path):
 root=parse(Path(path).read_bytes())[0][1]
 assert root[1]==(10,2),'non official envelope'
 inner=parse(next(v for k,v in root if k==4))[0][1]
 assert inner[1]==(10,2),'non official BU'
 ident=inner[3][1]; mz=ident[0][1]
 meta={'municipio':mz[0][1],'zona':mz[1][1],'local':ident[1][1],'secao':ident[2][1],'emissao':inner[4][1]}
 election_lists=[v for k,v in inner if k==48 and v and isinstance(v[0][1],list) and v[0][1] and v[0][1][0][0]==2 and v[0][1][0][1] in (6257,6259)]
 assert len(election_lists)==1,(path,'elections',len(election_lists))
 elections=election_lists[0]
 ele=next(v for k,v in elections if v[0]==(2,6259))
 meta['aptosBu']=ele[1][1]
 results=next(v for k,v in ele if k==48)
 cargo=[];comparecimento=None
 for _,v in results:
  for _,c in v[2][1]:
   if c[0]==(129,7):cargo.append(c);comparecimento=v[1][1]
 assert len(cargo)==1,(path,'cargo',len(cargo))
 votes=[]
 for _,v in cargo[0][2][1]:
  kind=v[0][1];q=v[1][1];idv=next((v for k,v in v if k==163),None)
  votes.append({'tipo':kind,'votos':q,'partido':idv[0][1] if idv else None,'numero':idv[1][1] if idv else None})
 meta['comparecimento']=comparecimento;meta['votos']=votes
 return meta

if __name__=='__main__':
 print(json.dumps(decode_file('/private/tmp/cadorin-resultados-research/bu-exemplo.dat'),ensure_ascii=False,indent=2))
