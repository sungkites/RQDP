"""Second, separately frozen extension: feedback dominance plus lazy quotient."""
import json,time,hashlib,sys
import bench
from kernel import Kernel
from dominance import Dominance

def factory(*args,**kw):
 return Dominance(*args[:5],**kw) if args[5]=='dominance' else Kernel(*args,**kw)

def main(stage):
 note=bench.OUT/'dominance_protocol.json'
 if not note.exists():
  note.write_text(json.dumps(dict(created=time.strftime('%Y-%m-%d %H:%M:%S'),
   stage='Additional exploratory algorithm extension after inspecting the first V13 small-case results',
   hypothesis='For identical projected feedback, the smaller remaining omission allowance is dominated in a minimax maximization. Projected candidate sets therefore suffice for merging.',
   methods='identity/static/residual share Kernel. dominance adds feedback dominance and skips redundant normalization while every query remains unresolved.',
   final_primary='All465 size4/8 natural U1 radius1 cases; three serial repeats, rotated order;10s/200000states.',
   final_scale='All140 size16/32/64/128 natural U1 radius1 cases; static/residual/dominance each once;3s/200000states. No concurrently running benchmark or correctness suite.',
   additional='All77 size16 cases, both U and identity-hash H costs, all radii0/1/2, natural candidates; static/residual/dominance;3s/200000states.',
   earlier_scale_note='The initial identity/static/residual scale run overlapped5.5 seconds of a correctness check. It is retained as exploratory; final_scale supplies isolated scale times. Identity resource-limit counts are descriptive only.',
   code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in bench.BASE.glob('*.py')}),indent=2))
 bench.Kernel=factory
 if stage=='primary':bench.run('final_primary',[g for g in bench.groups() if g[0]['size'] in [4,8]],['identity','static','residual','dominance'],3,10)
 elif stage=='scale':
  by={}
  for meta,omega,rr in bench.groups():
   if meta['size']==4:by.setdefault((meta['dataset'],meta['kind']),[omega,[]])[1].extend(rr)
  jobs=[]
  for (dataset,kind),(omega,rs) in by.items():
   for size in [16,32,64,128]:
    for pos in range(0,len(rs)-size+1,size):
     jobs.append((dict(dataset=dataset,kind=kind,size=size,group=pos//size,remainder=len(rs)%size),omega,rs[pos:pos+size]))
  bench.run('final_scale',jobs,['static','residual','dominance'],1,3)
 elif stage=='additional':bench.run('additional',[g for g in bench.groups() if g[0]['size']==16],['static','residual','dominance'],1,3,['U','H'],[0,1,2])
if __name__=='__main__':main(sys.argv[1])
