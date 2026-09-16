"""Exact minimax inspection with identity, static and residual state quotients.

The residual quotient keeps outcome/omission pairs, so retiring a query never
silently discards evidence about the shared omission allowance. All variants
share bounds, action ordering, memoization and branch-and-bound code.
"""
from functools import lru_cache
import time

class Kernel:
 def __init__(self,domains,costs,omega,thresholds,r,mode='residual',limit=200000,time_limit=10):
  self.omega=tuple(map(tuple,omega));self.k=tuple(thresholds);self.J=len(self.k)
  self.mode=mode;self.limit=limit;self.deadline=time.perf_counter()+time_limit
  self.expanded=0;self.calls=0;self.normalizations=0
  raw=[(tuple(sorted(d)),c) for d,c in zip(domains,costs)]
  self.types=tuple(raw if mode=='identity' else sorted(set(raw)))
  self.record_types=list(range(len(raw))) if mode=='identity' else [self.types.index(x) for x in raw]
  self.start=(tuple(self.record_types.count(t) for t in range(len(self.types))),(0,)*self.J,r)
  omin=tuple(min(v[j] for v in self.omega) for j in range(self.J))
  omax=tuple(max(v[j] for v in self.omega) for j in range(self.J))
  self.ext=[]
  for d,c in self.types:
   lo=tuple(min(self.omega[o][j] for o in d) for j in range(self.J))
   hi=tuple(max(self.omega[o][j] for o in d) for j in range(self.J))
   self.ext.append(tuple((lo[j],hi[j],int(lo[j]>omin[j]),int(hi[j]<omax[j])) for j in range(self.J)))
  self.bounds=lru_cache(None)(self.bounds)
  self.signature=lru_cache(None)(self.signature)
  self.representatives=lru_cache(None)(self.representatives)
  self.normalize=lru_cache(None)(self.normalize)
  self.value=lru_cache(None)(self.value)
 def guard(self):
  self.calls+=1
  if self.calls%128==0 and time.perf_counter()>self.deadline:raise RuntimeError('time limit')
  if self.calls>self.limit*3:raise RuntimeError('call limit')
 def bounds(self,state):
  ns,z,r=state;out=[]
  for j in range(self.J):
   if z[j]<0:out.append((0,0));continue
   low=high=z[j];down=up=0
   for t,n in enumerate(ns):
    if n:
     a,b,d,u=self.ext[t][j];low+=n*a;high+=n*b;down+=n*d;up+=n*u
   out.append((low-min(r,down),high+min(r,up)))
  return tuple(out)
 def certain(self,state):
  return all(z<0 or a>=k or b<k for z,(a,b),k in zip(state[1],self.bounds(state),self.k))
 def signature(self,t,active,positive):
  d,c=self.types[t]
  # Keep BOTH omission classes even when they share a projected outcome.
  pairs=tuple(sorted(set((tuple(v[j] for j in active),int(o not in d)) for o,v in enumerate(self.omega) if positive or o in d)))
  return c,pairs
 def representatives(self,active,positive):
  seen={};reps=[]
  for t in range(len(self.types)):
   sig=self.signature(t,active,positive)
   reps.append(seen.setdefault(sig,t))
  return tuple(reps)
 def normalize(self,state):
  if self.mode!='residual':return state
  self.normalizations+=1
  ns,z,r=state;ns=list(ns);z=list(z)
  while True:
   before=(tuple(ns),tuple(z),r)
   r=min(r,sum(ns))
   for j,(a,b) in enumerate(self.bounds((tuple(ns),tuple(z),r))):
    if z[j]>=0 and (a>=self.k[j] or b<self.k[j]):z[j]=-1
   active=tuple(j for j in range(self.J) if z[j]>=0)
   if not active:return ((0,)*len(ns),(-1,)*self.J,0)
   reps=self.representatives(active,r>0);new=[0]*len(ns)
   for t,n in enumerate(ns):new[reps[t]]+=n
   ns=new
   if r==0:
    for t,n in enumerate(ns):
     if not n:continue
     pairs=self.signature(t,active,False)[1]
     if len(pairs)==1:
      for j,v in zip(active,pairs[0][0]):z[j]=min(self.k[j],z[j]+n*v)
      ns[t]=0
   state=(tuple(ns),tuple(z),r)
   if state==before:return state
 def plan(self,state):
  canonical=self.normalize(state)
  return self.value(canonical),canonical
 def value(self,state):
  self.guard()
  if self.certain(state):return 0,-1
  self.expanded+=1
  if self.expanded>self.limit:raise RuntimeError('state limit')
  ns,z,r=state
  acts=sorted((t for t,n in enumerate(ns) if n),key=lambda t:(self.types[t][1],t))
  best=(sum(n*c for n,(d,c) in zip(ns,self.types)),acts[0])
  for t in acts:
   c=self.types[t][1];children=set()
   nn=list(ns);nn[t]-=1;nn=tuple(nn)
   d=self.types[t][0]
   for o,v in enumerate(self.omega):
    extra=int(o not in d)
    if extra>r:continue
    zz=tuple(-1 if a<0 else min(k,a+b) for a,b,k in zip(z,v,self.k))
    children.add(self.normalize((nn,zz,r-extra)))
   children=sorted(children,key=lambda ch:(self.certain(ch),-ch[2],ch))
   worst=0
   for ch in children:
    worst=max(worst,self.value(ch)[0])
    if c+worst>=best[0]:break
   else:
    if (c+worst,t)<best:best=c+worst,t
  return best
 def trace(self,truth):
  ns=list(self.start[0]);z=[0]*self.J;r=self.start[2]
  remaining=set(range(len(truth)));cost=0;steps=0
  while not self.certain((tuple(ns),tuple(z),r)):
   (bound,t),canonical=self.plan((tuple(ns),tuple(z),r))
   active=tuple(j for j,x in enumerate(canonical[1]) if x>=0)
   if self.mode=='residual':
    sig=self.signature(t,active,canonical[2]>0)
    i=min(i for i in remaining if self.signature(self.record_types[i],active,canonical[2]>0)==sig)
   else:i=min(i for i in remaining if self.record_types[i]==t)
   typ=self.record_types[i];o=truth[i];extra=int(o not in self.types[typ][0])
   remaining.remove(i);ns[typ]-=1;cost+=self.types[typ][1];steps+=1
   if extra>r:return dict(status='support_violation',answer=None,cost=cost,steps=steps)
   r-=extra
   z=[min(k,a+b) for k,a,b in zip(self.k,z,self.omega[o])]
  answer=tuple(int(a>=k) for (a,b),k in zip(self.bounds((tuple(ns),tuple(z),r)),self.k))
  return dict(status='certified',answer=answer,cost=cost,steps=steps)
