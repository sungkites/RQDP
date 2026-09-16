"""Exact type-count minimax search without recursively evaluating rollout.
Uses full inspection as a feasible bound and stops an action as soon as one
feedback branch meets that bound. This is ordinary branch-and-bound, applied
to the bounded-omission type-count model; no altered verification decisions.
"""
from robust import Symbolic
class Direct(Symbolic):
 def value(self,state):
  self.guard()
  if self.certain(state):return 0,-1
  self.expanded+=1
  if self.expanded>self.limit:raise RuntimeError('symbolic state limit reached')
  ns,z,r=state
  acts=sorted((t for t,n in enumerate(ns) if n),key=lambda t:(self.types[t][1],t))
  best=(sum(n*c for n,(d,c) in zip(ns,self.types)),acts[0])
  for t in acts:
   c=self.types[t][1];children=[ch for _,ch in self.transitions(state,t)]
   # Explore unresolved children first; pruning is based only on valid costs.
   children.sort(key=lambda ch:(self.certain(ch),-ch[2]))
   worst=0
   for ch in children:
    worst=max(worst,self.value(ch)[0])
    if c+worst>=best[0]:break
   else:
    if (c+worst,t)<best:best=c+worst,t
  return best
