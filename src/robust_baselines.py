from workloads import groups
from solver import Solver
from functools import lru_cache
from itertools import product
import json,time,hashlib,gc

class Finite(Solver):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.mb=lru_cache(None)(self.mb);self.mr=lru_cache(None)(self.mr);self.ex=lru_cache(None)(self.ex);self.ep=lru_cache(None)(self.ep)
 def mb(self,s):
  if self.pure(s):return 0
  a=self.greedy(s,'pairs')
  return self.costs[a]+max(self.mb(b) for b in self.parts(s,a))
 def mr(self,s):
  return min((self.costs[a]+max(self.mb(b) for b in bs),self.costs[a],a) for a,bs in self.actions(s))[-1]
 def ex(self,s):
  if self.pure(s):return 0,-1
  return min((self.costs[a]+max(self.ex(b)[0] for b in bs),a) for a,bs in self.actions(s))
 def ep(self,s):
  if self.pure(s):return 0,-1
  aa=sorted(self.actions(s),key=lambda ap:(self.costs[ap[0]],ap[0]))
  best=(sum(self.costs[a] for a,bs in aa),aa[0][0])
  for a,bs in aa:
   worst=0;c=self.costs[a]
   for b in sorted(bs,key=lambda b:(self.pure(b),-b.bit_count())):
    worst=max(worst,self.ep(b)[0])
    if c+worst>=best[0]:break
   else:
    if (c+worst,a)<best:best=c+worst,a
  return best
 def action(self,s,p):
  if p=='minimax_rollout':return self.mr(s)
  if p=='minimax_exact':return self.ex(s)[1]
  return super().action(s,p)

def model(ds,cs,omega,ks,r):
 worlds=[w for w in product(range(len(omega)),repeat=len(ds)) if sum(o not in d for o,d in zip(w,ds))<=r]
 labels=[tuple(int(sum(omega[o][j] for o in w)>=k) for j,k in enumerate(ks)) for w in worlds]
 return worlds,labels,cs
