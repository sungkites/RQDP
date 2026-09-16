"""Natural-candidate baseline comparisons under a shared feedback model."""
from pathlib import Path
import json
from workloads import groups
from robust_baselines import Finite, model

def main():
    out=Path(__file__).resolve().parent.parent/'results/runs'
    out.mkdir(parents=True,exist_ok=True)
    dest=out/'baselines.jsonl'
    with dest.open('w',encoding='utf-8') as stream:
        for meta,omega,records in groups():
            if meta['size'] not in [4,8]:continue
            n=len(records)
            for regime in (['U','H'] if n==4 else ['U']):
                costs=[1 if regime=='U' else r['cost_h'] for r in records]
                args=model([r['domain'] for r in records],costs,omega,[(n+1)//2]*2,1)
                for method in ['ig','ec2','pairs','asr','minimax_rollout','minimax_exact']:
                    engine=Finite(*args)
                    stats,_=engine.evaluate(method)
                    row=meta|dict(regime=regime,condition='natural',radius=1,method=method)|stats
                    stream.write(json.dumps(row)+'\n')
            if meta['group']%20==0:print(meta,flush=True)
if __name__=='__main__':main()
