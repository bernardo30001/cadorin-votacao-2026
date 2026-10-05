from pathlib import Path

def parse(data):
 out=[];i=0
 while i<len(data):
  tag=data[i];i+=1
  n=data[i];i+=1
  if n&128:
   nb=n&127;n=int.from_bytes(data[i:i+nb]);i+=nb
  val=data[i:i+n];i+=n
  if len(val)!=n: raise ValueError('bad length')
  if tag&32:val=parse(val)
  elif tag in [2,10,129,130,131]:val=int.from_bytes(val,signed=True)
  elif tag==27:val=val.decode()
  out.append((tag,val))
 return out

def show(xs,level=0):
 for k,v in xs:
  if isinstance(v,list):
   print(' '*level,hex(k),'len',len(v))
   if level<7:show(v,level+1)
  else:print(' '*level,hex(k),('BYTES '+str(len(v))) if isinstance(v,bytes) else v)

if __name__=='__main__':
 root=parse(Path('/private/tmp/cadorin-resultados-research/bu-exemplo.dat').read_bytes())[0][1]
 inn=parse(next(v for k,v in root if k==4))
 show(inn)
