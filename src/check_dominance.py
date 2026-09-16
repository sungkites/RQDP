from check import BASE,OUT
from dominance import Dominance
from robust import explicit
import random,itertools,json,time

def main():
 rng=random.Random(914217);paths=0;t=time.perf_counter()
 for trial in range(240):
  n=rng.randint(2,5);J=rng.randint(1,3)
  omega=[v for v in itertools.product([0,1],repeat=J) if rng.random()<0.8] or [(0,)*J]
  ds=[tuple(i for i in range(len(omega)) if rng.randrange(2)) or (0,) for _ in range(n)]
  cs=[rng.randint(1,4) for _ in range(n)];ks=[rng.randint(1,n) for _ in range(J)];r=rng.randint(0,3)
  opt,nw,_=explicit(ds,cs,omega,ks,r);e=Dominance(ds,cs,omega,ks,r,time_limit=60)
  assert e.plan(e.start)[0][0]==opt,(trial,ds,cs,omega,ks,r,opt)
  for ww in itertools.product(range(len(omega)),repeat=n):
   if sum(o not in d for o,d in zip(ww,ds))<=r:
    result=e.trace(ww);truth=tuple(int(sum(omega[o][j] for o in ww)>=k) for j,k in enumerate(ks))
    assert result['answer']==truth and result['cost']<=opt,(trial,result,truth,opt)
    paths+=1
  if trial%40==0:print('dominance checked',trial,flush=True)
 receipt=dict(models=240,admissible_paths=paths,failures=0,seed=914217,seconds=time.perf_counter()-t)
 (OUT/'dominance_checks.json').write_text(json.dumps(receipt,indent=2));print(receipt)
if __name__=='__main__':main()
