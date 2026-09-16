"""Exploratory bounded candidate-omission model for threshold workloads.

Each verification reveals one record's query-predicate vector. Up to r records
may have a true vector outside their advertised candidate set. Within a type,
records have identical candidate vector sets and costs. Permutation symmetry
permits an exact minimax DP over remaining type counts, not database worlds.
This is an experimental extension, not a claim of established novelty.
"""
from functools import lru_cache
from itertools import product
import time

class Symbolic:
 def __init__(self,domains,costs,omega,thresholds,r,limit=200000,time_limit=10):
  self.omega=tuple(map(tuple,omega));self.k=tuple(thresholds);self.J=len(self.k)
  self.types=tuple(sorted(set((tuple(sorted(d)),c) for d,c in zip(domains,costs))))
  self.record_types=[self.types.index((tuple(sorted(d)),c)) for d,c in zip(domains,costs)]
  self.start=(tuple(self.record_types.count(i) for i in range(len(self.types))), (0,)*self.J,r)
  self.limit=limit;self.expanded=0;self.calls=0;self.deadline=time.perf_counter()+time_limit
  self.bounds=lru_cache(None)(self.bounds);self.transitions=lru_cache(None)(self.transitions)
  self.value=lru_cache(None)(self.value);self.base=lru_cache(None)(self.base);self.roll=lru_cache(None)(self.roll)
 def guard(self):
  self.calls+=1
  if self.calls%512==0 and time.perf_counter()>self.deadline:raise RuntimeError('symbolic time limit reached')
  if self.calls>self.limit*3:raise RuntimeError('symbolic total state limit reached')
 def bounds(self,state):
  ns,z,r=state;lo=list(z);hi=list(z);down=[0]*self.J;up=[0]*self.J
  for n,(d,c) in zip(ns,self.types):
   for j in range(self.J):
    mn=min(self.omega[o][j] for o in d);mx=max(self.omega[o][j] for o in d)
    lo[j]+=n*mn;hi[j]+=n*mx
    if mn>min(o[j] for o in self.omega):down[j]+=n
    if mx<max(o[j] for o in self.omega):up[j]+=n
  return tuple((a-min(r,dd),b+min(r,uu)) for a,b,dd,uu in zip(lo,hi,down,up))
 def certain(self,state):return all(a>=k or b<k for (a,b),k in zip(self.bounds(state),self.k))
 def labels(self,state):
  assert self.certain(state)
  return tuple(int(a>=k) for (a,b),k in zip(self.bounds(state),self.k))
 def transitions(self,state,t):
  ns,z,r=state;d,c=self.types[t];out=[]
  for o,v in enumerate(self.omega):
   extra=int(o not in d)
   if extra>r:continue
   nn=list(ns);nn[t]-=1
   zz=tuple(min(k,a+b) for a,b,k in zip(z,v,self.k))
   out.append((o,(tuple(nn),zz,r-extra)))
  return tuple(out)
 def greedy(self,state):
  # Minimax query-interval width reduction, normalized by inspection cost.
  def uncertainty(st):
   return sum((b-a+1) if a<k<=b else 0 for (a,b),k in zip(self.bounds(st),self.k))
  u=uncertainty(state)
  return max((t for t,n in enumerate(state[0]) if n),key=lambda t:((u-max(uncertainty(ch) for _,ch in self.transitions(state,t)))/self.types[t][1],-self.types[t][1],-t))
 def base(self,state):
  self.guard()
  if self.certain(state):return 0,-1
  t=self.greedy(state)
  return self.types[t][1]+max(self.base(ch)[0] for _,ch in self.transitions(state,t)),t
 def roll(self,state):
  if self.certain(state):return 0,-1
  return min((self.types[t][1]+max(self.base(ch)[0] for _,ch in self.transitions(state,t)),t) for t,n in enumerate(state[0]) if n)
 def value(self,state):
  self.guard()
  if self.certain(state):return 0,-1
  self.expanded+=1
  if self.expanded>self.limit:raise RuntimeError('symbolic state limit reached')
  inc=self.roll(state);best=inc
  for t,n in enumerate(state[0]):
   if not n:continue
   c=self.types[t][1]
   # One necessary inspection in each unresolved child is an admissible bound.
   children=[ch for o,ch in self.transitions(state,t)]
   lb=c+max(0 if self.certain(ch) else min(self.types[j][1] for j,num in enumerate(ch[0]) if num) for ch in children)
   if lb>=best[0]:continue
   v=c+max(self.value(ch)[0] for ch in children)
   if (v,t)<best:best=v,t
  return best
 def trace(self,truth,policy='exact'):
  st=self.start;remaining=set(range(len(truth)));cost=0;steps=0
  while not self.certain(st):
   t=self.value(st)[1] if policy=='exact' else self.roll(st)[1] if policy=='rollout' else self.greedy(st)
   i=min(i for i in remaining if self.record_types[i]==t);remaining.remove(i)
   o=truth[i];children=dict(self.transitions(st,t))
   cost+=self.types[t][1];steps+=1
   if o not in children:return dict(cost=cost,steps=steps,status='support_violation',answer=None)
   st=children[o]
  return dict(cost=cost,steps=steps,status='certified',answer=self.labels(st))

def explicit(domains,costs,omega,ks,r):
 worlds=[w for w in product(range(len(omega)),repeat=len(domains)) if sum(o not in d for o,d in zip(w,domains))<=r]
 labels=[tuple(int(sum(omega[o][j] for o in w)>=k) for j,k in enumerate(ks)) for w in worlds]
 @lru_cache(None)
 def rec(s):
  if len({labels[i] for i in s})==1:return 0
  vals=[]
  for a,c in enumerate(costs):
   ds={}
   for i in s:ds.setdefault(worlds[i][a],[]).append(i)
   if len(ds)>1:vals.append(c+max(rec(tuple(v)) for v in ds.values()))
  return min(vals)
 return rec(tuple(range(len(worlds)))),len(worlds),rec.cache_info().currsize
