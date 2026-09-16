from pathlib import Path
import sys,json,random,itertools,time
BASE=Path(__file__).resolve().parent
from kernel import Kernel
from robust import explicit
OUT=BASE.parent/'results/runs'
OUT.mkdir(parents=True,exist_ok=True)

def main():
 rng=random.Random(913472);paths=0;t=time.perf_counter();ncheck=180
 for trial in range(ncheck):
  n=rng.randint(2,5);J=rng.randint(1,3)
  omega=[v for v in itertools.product([0,1],repeat=J) if rng.random()<0.8]
  if not omega:omega=[(0,)*J]
  ds=[tuple(i for i in range(len(omega)) if rng.randrange(2)) or (0,) for _ in range(n)]
  cs=[rng.randint(1,4) for _ in range(n)];ks=[rng.randint(1,n) for _ in range(J)];r=rng.randint(0,2)
  opt,nw,_=explicit(ds,cs,omega,ks,r)
  for mode in ['identity','static','residual']:
   e=Kernel(ds,cs,omega,ks,r,mode,time_limit=60)
   v=e.plan(e.start)[0][0]
   assert v==opt,(trial,mode,ds,cs,omega,ks,r,v,opt)
   for ww in itertools.product(range(len(omega)),repeat=n):
    if sum(o not in d for o,d in zip(ww,ds))<=r:
     result=e.trace(ww)
     truth=tuple(int(sum(omega[o][j] for o in ww)>=k) for j,k in enumerate(ks))
     assert result['answer']==truth and result['cost']<=opt,(trial,mode,result,truth,opt)
     paths+=1
  if trial%20==0:print('checked',trial,flush=True)
 receipt=dict(models=ncheck,variants=3,admissible_paths=paths,failures=0,seconds=time.perf_counter()-t,seed=913472)
 (OUT/'checks.json').write_text(json.dumps(receipt,indent=2));print(receipt)
if __name__=='__main__':main()
