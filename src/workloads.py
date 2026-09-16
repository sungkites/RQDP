"""Load identifier-free predicate inputs; preserve the original batch order."""
from pathlib import Path
import json
DATA=Path(__file__).resolve().parent.parent/'data'
def groups():
 for dataset in ['flights','assets']:
  data=json.loads((DATA/(dataset+'_predicates.json')).read_text())
  omega=[tuple(v) for v in data['omega']]
  for collection in data['collections']:
   records=[dict(r,domain=tuple(r['domain'])) for r in collection['records']]
   for size in [4,8,16]:
    for pos in range(0,len(records)-size+1,size):
     yield dict(dataset=dataset,kind=collection['kind'],size=size,group=pos//size,remainder=len(records)%size),omega,records[pos:pos+size]
