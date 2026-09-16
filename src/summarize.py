"""Summarize archived or fresh primary measurements without dropping failures."""
from pathlib import Path
import argparse, collections, csv, json, statistics

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path(__file__).resolve().parent.parent/'results/paper')
    args=parser.parse_args()
    rows=[json.loads(line) for line in (args.input/'final_primary.jsonl').read_text().splitlines()]
    buckets=collections.defaultdict(list)
    for row in rows:buckets[(row['dataset'],row['size'],row['method'])].append(row)
    output=[]
    for (dataset,size,method),records in sorted(buckets.items()):
        tasks=collections.defaultdict(list)
        for row in records:tasks[(row['kind'],row['group'])].append(row)
        complete=[rs for rs in tasks.values() if all(r['status']=='complete' for r in rs)]
        output.append(dict(dataset=dataset,size=size,method=method,tasks=len(tasks),complete_tasks=len(complete),
            mean_task_median_ms=1000*statistics.mean(statistics.median(r['seconds'] for r in rs) for rs in complete) if complete else None,
            mean_task_median_states=statistics.mean(statistics.median(r['states'] for r in rs) for rs in complete) if complete else None,
            mean_worst_cost=statistics.mean(rs[0]['optimal_worst'] for rs in complete) if complete else None))
    dest=args.input/'primary_summary.csv'
    with dest.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(output[0]));writer.writeheader();writer.writerows(output)
    print(dest)
if __name__=='__main__':main()
