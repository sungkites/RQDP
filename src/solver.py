"""Finite query-verification optimizer with admissible certificate bounds.

Exact search / rollout / certificate covers are established principles. This
module does not claim their invention. All policies see identical candidates,
costs and model weights, and never see the held-out reference state.
"""
from functools import lru_cache
import math,time

class Solver:
 def __init__(self,worlds,labels,costs,weights=None,bound='certificate',limit=200000):
  self.worlds=tuple(map(tuple,worlds));self.labels=tuple(map(tuple,labels));self.costs=tuple(costs)
  self.weights=tuple(weights or [1]*len(worlds));self.n=len(worlds);self.m=len(costs)
  assert self.n and len(set(self.worlds))==self.n and all(c>0 for c in costs)
  assert all(w>0 for w in self.weights)
  self.full=(1<<self.n)-1;self.limit=limit;self.bound_type=bound
  self.am=[];self.lm={};self.expanded=0;self.pruned=0;self.cover_calls=0
  for a in range(self.m):
   d={}
   for i,w in enumerate(self.worlds):d[w[a]]=d.get(w[a],0)|(1<<i)
   self.am.append(tuple(d.values()))
  for i,y in enumerate(self.labels):self.lm[y]=self.lm.get(y,0)|(1<<i)
  for name in ['mass','pure','actions','ig','base','roll_action','roll','lower','solve','cover']:
   setattr(self,name,lru_cache(None)(getattr(self,name)))
 def indices(self,s):
  while s:
   b=s&-s;yield b.bit_length()-1;s^=b
 def mass(self,s):return sum(self.weights[i] for i in self.indices(s))
 def pure(self,s):return sum(bool(s&m) for m in self.lm.values())<=1
 def parts(self,s,a):return tuple(s&m for m in self.am[a] if s&m)
 def actions(self,s):
  # Same feedback partition: cheaper action dominates, at every residual state.
  d={}
  for a,c in enumerate(self.costs):
   pp=tuple(sorted(self.parts(s,a)))
   if len(pp)>1 and (pp not in d or (c,a)<(self.costs[d[pp]],d[pp])):d[pp]=a
  return tuple(sorted(((a,p) for p,a in d.items()),key=lambda z:z[0]))
 def entropy(self,s):
  n=self.mass(s)
  return -sum((k/n)*math.log2(k/n) for m in self.lm.values() if (k:=self.mass(s&m)))
 def ig(self,s):
  n=self.mass(s);h=self.entropy(s)
  return max(self.actions(s),key=lambda ap:(round((h-sum(self.mass(b)/n*self.entropy(b) for b in ap[1]))/self.costs[ap[0]],12),-self.costs[ap[0]],-ap[0]))[0]
 def greedy(self,s,p):
  if p=='ig':return self.ig(s)
  n=self.mass(s);counts=[self.mass(s&m) for m in self.lm.values()]
  def pairs(t):return (self.mass(t)**2-sum(self.mass(t&m)**2 for m in self.lm.values()))//2
  pp=pairs(s)
  def score(ap):
   a,bs=ap;c=self.costs[a]
   if p=='ec2':v=(n*pp-sum(self.mass(b)*pairs(b) for b in bs))/c
   elif p=='pairs':v=(pp-max(pairs(b) for b in bs))/c
   elif p=='asr':
    cover=0
    for b in bs:
     nb=self.mass(b)
     for total,mask in zip(counts,self.lm.values()):
      k=self.mass(b&mask)
      if k and n>total:cover+=k*((n-total)-(nb-k))/(n-total)
    v=(n-max(self.mass(b) for b in bs)+cover)/c
   else:raise ValueError(p)
   return round(v,12),-c,-a
  return max(self.actions(s),key=score)[0]
 def base(self,s,p='ig'):
  if self.pure(s):return 0,0,-1
  a=self.greedy(s,p);v=[self.base(b,p) for b in self.parts(s,a)];c=self.costs[a]
  return c*self.mass(s)+sum(x[0] for x in v),c+max(x[1] for x in v),a
 def roll_action(self,s):
  return min((self.costs[a]*self.mass(s)+sum(self.base(b)[0] for b in bs),self.costs[a]+max(self.base(b)[1] for b in bs),self.costs[a],a) for a,bs in self.actions(s))[-1]
 def roll(self,s):
  if self.pure(s):return 0,0,-1
  a=self.roll_action(s);v=[self.roll(b) for b in self.parts(s,a)];c=self.costs[a]
  return c*self.mass(s)+sum(x[0] for x in v),c+max(x[1] for x in v),a
 def cover(self,constraints):
  """Exact weighted hitting set on differing-field masks. No reference used."""
  self.cover_calls+=1
  if not constraints:return 0
  # Superset constraints are redundant when a subset must already be hit.
  kept=[]
  for d in sorted(set(constraints),key=lambda x:(x.bit_count(),x)):
   if not any(k&d==k for k in kept):kept.append(d)
  pivot=min(kept,key=lambda x:(x.bit_count(),x))
  return min(self.costs[a]+self.cover(tuple(d for d in kept if not (d>>a&1))) for a in self.indices(pivot))
 def lower(self,s):
  if self.pure(s):return 0
  if self.bound_type=='zero':return 0
  if self.bound_type=='one':return self.mass(s)*min(self.costs[a] for a,_ in self.actions(s))
  # Every world's path must separate it from every opposite query answer.
  # Weighted sum of individually optimal certificates lower-bounds every tree.
  inds=tuple(self.indices(s));total=0
  for i in inds:
   constraints=[]
   for j in inds:
    if self.labels[i]!=self.labels[j]:
     mask=sum(1<<a for a in range(self.m) if self.worlds[i][a]!=self.worlds[j][a])
     assert mask;constraints.append(mask)
   total+=self.weights[i]*self.cover(tuple(sorted(set(constraints))))
  return total
 def solve(self,s):
  if self.pure(s):return 0,0,-1
  self.expanded+=1
  if self.expanded>self.limit:raise RuntimeError('node limit exceeded; no optimality claim')
  inc=self.roll(s);best=(inc[0],inc[1],self.costs[inc[2]],inc[2])
  acts=sorted(self.actions(s),key=lambda ap:(ap[0]!=inc[2],self.costs[ap[0]],ap[0]))
  for a,bs in acts:
   c=self.costs[a]
   lb=c*self.mass(s)+sum(self.lower(b) for b in bs)
   # Optimize average cost only; equality can be pruned without losing it.
   if lb>=best[0]:self.pruned+=1;continue
   vv=[self.solve(b) for b in sorted(bs,key=lambda b:-self.mass(b))]
   cand=(c*self.mass(s)+sum(v[0] for v in vv),c+max(v[1] for v in vv),c,a)
   if cand<best:best=cand
  return best[0],best[1],best[3]
 def action(self,s,p):
  if p=='exact':return self.solve(s)[2]
  if p=='rollout':return self.roll_action(s)
  return self.greedy(s,p)
 def evaluate(self,p):
  tic=time.perf_counter();paths=[None]*self.n
  def rec(s,c):
   if self.pure(s):
    for i in self.indices(s):paths[i]=c
    return
   a=self.action(s,p)
   for b in self.parts(s,a):rec(b,c+self.costs[a])
  rec(self.full,0)
  assert all(x is not None for x in paths)
  total=sum(c*w for c,w in zip(paths,self.weights))
  if p=='exact':assert total==self.solve(self.full)[0]
  return dict(mean=total/sum(self.weights),worst=max(paths),seconds=time.perf_counter()-tic,expanded=self.expanded,pruned=self.pruned,cover_calls=self.cover_calls),paths
