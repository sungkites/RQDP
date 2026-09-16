"""Frozen complete-case comparisons; no outcome-dependent case selection."""
from pathlib import Path
import sys,json,time,gc,hashlib,collections,argparse
BASE=Path(__file__).resolve().parent
from kernel import Kernel
from direct import Direct
from workloads import groups
OUT=BASE.parent/'results/runs'
OUT.mkdir(parents=True,exist_ok=True)

def freeze():
 p=OUT/'protocol.json'
 if p.exists():return
 note=dict(created=time.strftime('%Y-%m-%d %H:%M:%S'),
  status='Exploratory method development on previously inspected inputs; not a fresh statistical holdout',
  hypothesis='Residual query retirement and omission-aware type merging preserve exact minimax cost while reducing search when records share residual signatures.',
  primary='Every natural size4/8 Flights and asset group, U record cost1, omission radius1, two majority thresholds; three serial repeats with rotated order. 465 cases.',
  variants=['V12 Direct','identity: no type compression; implicit allowed states','static: initial type counts','residual: query retirement, residual type merging and deterministic inference at radius0'],
  fairness='The last three variants use exactly the same precomputed extrema, cached bounds, action order, full-audit upper bound and max-branch pruning. No explicit world construction in any variant.',
  timing='Construction of solver from candidate predicate sets plus first optimal action and worst-case cost; excludes parsing, correctness trace and garbage collection.',
  primary_limits='10s,200000 expanded states,600000 calls; failures retained',
  scale='Every full natural group16/32/64/128 reconstructed from size4 inputs, U1,r1,majority; identity/static/residual each once with3s/200000states. Remainders reported.',
  additional='All original size16 groups under U/H hash costs and radius0/1/2; static and residual; one run each,3s. Natural candidates only.',
  correctness='Independent exhaustive minimax and all admissible paths on180 seeded finite models with1..3 queries; all variants. Actual reference paths checked after primary solve.',
  source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.glob('*.py')})
 p.write_text(json.dumps(note,indent=2),encoding='utf-8')

def execute(meta,omega,rr,method,repeat,seconds,regime='U',radius=1):
 ds=[r['domain'] for r in rr];n=len(rr);ks=[(n+1)//2]*2
 cs=[1 if regime=='U' else r['cost_h'] for r in rr]
 gc.collect();tic=time.perf_counter()
 e=Direct(ds,cs,omega,ks,radius,time_limit=seconds) if method=='v12' else Kernel(ds,cs,omega,ks,radius,method,time_limit=seconds)
 row=meta|dict(method=method,repeat=repeat,regime=regime,radius=radius,types=len(e.types))
 try:
  v=e.value(e.start)[0] if method=='v12' else e.plan(e.start)[0][0]
  elapsed=time.perf_counter()-tic
  row.update(status='complete',seconds=elapsed,optimal_worst=v,states=e.expanded,cached_states=e.value.cache_info().currsize)
  e.deadline=time.perf_counter()+10
  truth=[r['truth'] for r in rr];trace=e.trace(truth)
  answer=tuple(int(sum(omega[o][j] for o in truth)>=k) for j,k in enumerate(ks))
  valid=sum(o not in d for o,d in zip(truth,ds))<=radius
  if valid:assert trace['answer']==answer and trace['cost']<=v,(row,trace,answer)
  row.update(reference_trace=trace,assumption_holds=valid)
 except RuntimeError as exc:
  row.update(status='resource_limit',seconds=time.perf_counter()-tic,states=e.expanded,error=str(exc))
 del e
 return row

def run(name,jobs,methods,repeats,seconds,regimes=['U'],radii=[1]):
 dest=OUT/(name+'.jsonl');done=set()
 keys=['dataset','kind','size','group','method','repeat','regime','radius']
 if dest.exists():
  for line in dest.read_text().splitlines():
   row=json.loads(line);done.add(tuple(row[k] for k in keys))
 for ix,(meta,omega,rr) in enumerate(jobs):
  for regime in regimes:
   for radius in radii:
    for repeat in range(repeats):
     order=methods[(ix+repeat)%len(methods):]+methods[:(ix+repeat)%len(methods)]
     for method in order:
      key=tuple((meta|dict(method=method,repeat=repeat,regime=regime,radius=radius))[k] for k in keys)
      if key in done:continue
      row=execute(meta,omega,rr,method,repeat,seconds,regime,radius)
      with dest.open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
  if ix%10==0:print(name,ix,len(jobs),flush=True)

def main(stage):
 freeze()
 if stage=='primary':run('primary',[g for g in groups() if g[0]['size'] in [4,8]],['v12','identity','static','residual'],3,10)
 elif stage=='scale':
  by={}
  for meta,omega,rr in groups():
   if meta['size']==4:by.setdefault((meta['dataset'],meta['kind']),[omega,[]])[1].extend(rr)
  jobs=[]
  for (dataset,kind),(omega,rs) in by.items():
   for size in [16,32,64,128]:
    for pos in range(0,len(rs)-size+1,size):
     jobs.append((dict(dataset=dataset,kind=kind,size=size,group=pos//size,remainder=len(rs)%size),omega,rs[pos:pos+size]))
  run('scale',jobs,['identity','static','residual'],1,3)
 elif stage=='additional':run('additional',[g for g in groups() if g[0]['size']==16],['static','residual'],1,3,['U','H'],[0,1,2])
if __name__=='__main__':main(sys.argv[1])
