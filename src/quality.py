"""Fixed complete threshold grid; reference used only as oracle/evaluator.
No method tuning or instance selection. Existing finite rules are adaptations.
"""
from pathlib import Path
import sys,json,time,gc,hashlib,collections
ROOT=Path(__file__).resolve().parent.parent
from workloads import groups
from robust_baselines import Finite,model
from dominance import Dominance
from metrics import query_metrics,certification_metrics
OUT=ROOT/'results/runs/quality';OUT.mkdir(parents=True,exist_ok=True)
METHODS=['ig','ec2','pairs','asr','rqdp']

def rqtrace(e,truth):
 ns=list(e.start[0]);z=[0]*e.J;r=e.start[2];left=set(range(len(truth)));path=[]
 while True:
  state=tuple(ns),tuple(z),r
  answers=[1 if a>=k else 0 if b<k else None for (a,b),k in zip(e.bounds(state),e.k)]
  path.append(answers)
  if all(a is not None for a in answers):break
  (_,t),can=e.plan(state);active=tuple(j for j,x in enumerate(can[1]) if x>=0)
  sig=e.signature(t,active,can[2]>0)
  i=min(i for i in left if e.signature(e.record_types[i],active,can[2]>0)==sig)
  typ=e.record_types[i];o=truth[i];extra=int(o not in e.types[typ][0])
  assert extra<=r
  left.remove(i);ns[typ]-=1;r-=extra
  z=[min(k,a+b) for k,a,b in zip(e.k,z,e.omega[o])]
 return path

def finite_trace(e,truth,method):
 s=e.full;path=[]
 while True:
  labs={e.labels[i] for i in e.indices(s)}
  ans=[next(iter(x)) if len(x)==1 else None for x in [set(y[j] for y in labs) for j in range(2)]]
  path.append(ans)
  if all(x is not None for x in ans):break
  a=e.action(s,method)
  s=sum(1<<i for i in e.indices(s) if e.worlds[i][a]==truth[a])
  assert s
 return path

def main():
 protocol=dict(grid='all k=1..4, both query thresholds equal k',size=4,radius=1,cost=1,methods=METHODS,selection='all existing complete size4 batches; no selection by truth or result',aggregation='micro counts across all batch-query-threshold outputs within each dataset',reference='oracle and evaluation only',auc='right-continuous F1 area over cost fraction 0..1',created=time.strftime('%Y-%m-%d %H:%M:%S'))
 (OUT/'quality_protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
 dest=OUT/'quality_paths.jsonl';done=set()
 if dest.exists():
  for l in dest.read_text().splitlines():
   d=json.loads(l);done.add((d['dataset'],d['kind'],d['group'],d['threshold'],d['method']))
 for ix,(meta,omega,rr) in enumerate(g for g in groups() if g[0]['size']==4):
  ds=[r['domain'] for r in rr];truth=[r['truth'] for r in rr]
  assert sum(o not in d for o,d in zip(truth,ds))<=1
  for k in range(1,5):
   labels=[int(sum(omega[o][j] for o in truth)>=k) for j in range(2)]
   args=None
   for method in METHODS:
    key=meta['dataset'],meta['kind'],meta['group'],k,method
    if key in done:continue
    if method=='rqdp':
     e=Dominance(ds,[1]*4,omega,[k]*2,1,time_limit=10);path=rqtrace(e,truth)
    else:
     if args is None:args=model(ds,[1]*4,omega,[k]*2,1)
     e=Finite(*args);path=finite_trace(e,truth,method)
    assert path[-1]==labels
    assert all(a is None or a==b for row in path for a,b in zip(row,labels))
    row=meta|dict(threshold=k,method=method,truth=labels,path=path,cost=len(path)-1)
    with dest.open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
    del e
   gc.collect()
  if ix%30==0:print('quality batches',ix,flush=True)
 aggregate()

def aggregate():
 rows=[json.loads(l) for l in (OUT/'quality_paths.jsonl').read_text().splitlines()];result=[]
 for ds in ['flights','assets']:
  for method in METHODS:
   rr=[r for r in rows if r['dataset']==ds and r['method']==method];curve=[]
   for cost in range(5):
    truth=[];answers=[]
    for r in rr:truth+=r['truth'];answers+=r['path'][min(cost,len(r['path'])-1)]
    m=query_metrics(truth,[int(a==1) for a in answers]);c=certification_metrics(truth,answers)
    # Accuracy after treating abstentions as absent outputs is not certificate accuracy.
    m.pop('accuracy',None)
    curve.append(dict(cost=cost,**m,**c))
   result.append(dict(dataset=ds,method=method,workloads=len(rr),outputs=2*len(rr),mean_observed_cost=sum(r['cost'] for r in rr)/len(rr),f1_cost_auc=sum(c['f1'] for c in curve[:-1])/4,curve=curve))
 (OUT/'quality_summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps([{k:v for k,v in r.items() if k!='curve'} for r in result]),flush=True)
if __name__=='__main__':main()
