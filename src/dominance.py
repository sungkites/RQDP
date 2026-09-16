"""Residual quotient strengthened by minimax feedback dominance.

For the same projected vector, an in-candidate feedback leaves a larger allowed
set than an out-of-candidate feedback. Optimal remaining worst cost is monotone
in that set. Only the former is needed in the adversarial maximization. Actual
feedback still updates the ORIGINAL omission indicator in Kernel.trace.
"""
from kernel import Kernel

class Dominance(Kernel):
 def __init__(self,*args,**kwargs):
  kwargs['mode']='residual'
  super().__init__(*args,**kwargs)
 def signature(self,t,active,positive):
  d,c=self.types[t];minimum={}
  for o,v in enumerate(self.omega):
   delta=int(o not in d)
   if delta and not positive:continue
   projected=tuple(v[j] for j in active)
   minimum[projected]=min(minimum.get(projected,1),delta)
  return c,tuple(sorted(minimum.items()))
 def normalize(self,state):
  ns,z,r=state
  # Under a full unresolved workload and positive radius there is no new
  # quotient beyond the initial type partition; avoid normalization overhead.
  if r>0 and r<=sum(ns) and all(x>=0 for x in z):
   if all(a<k<=b for (a,b),k in zip(self.bounds(state),self.k)):return state
  return super().normalize(state)
 def value(self,state):
  self.guard()
  if self.certain(state):return 0,-1
  self.expanded+=1
  if self.expanded>self.limit:raise RuntimeError('state limit')
  ns,z,r=state;active=tuple(j for j,x in enumerate(z) if x>=0)
  acts=sorted((t for t,n in enumerate(ns) if n),key=lambda t:(self.types[t][1],t))
  best=(sum(n*c for n,(d,c) in zip(ns,self.types)),acts[0])
  for t in acts:
   c=self.types[t][1];nn=list(ns);nn[t]-=1;nn=tuple(nn);children=set()
   for projected,delta in self.signature(t,active,r>0)[1]:
    zz=list(z)
    for j,v in zip(active,projected):zz[j]=min(self.k[j],zz[j]+v)
    children.add(self.normalize((nn,tuple(zz),r-delta)))
   children=sorted(children,key=lambda ch:(self.certain(ch),-ch[2],ch))
   worst=0
   for ch in children:
    worst=max(worst,self.value(ch)[0])
    if c+worst>=best[0]:break
   else:
    if (c+worst,t)<best:best=c+worst,t
  return best
