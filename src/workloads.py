"""Load identifier-free predicate inputs using deterministic batch order."""
from pathlib import Path
import json
DATA=Path(__file__).resolve().parent.parent/'data'
def groups(sizes=(4,8,16)):
 for dataset in ['flights','assets','hospital','beers']:
  path=DATA/(dataset+'_predicates.json')
  if not path.exists():continue
  data=json.loads(path.read_text())
  omega=[tuple(v) for v in data['omega']]
  for collection in data['collections']:
   records=[dict(r,domain=tuple(r['domain'])) for r in collection['records']]
   for size in sizes:
    for pos in range(0,len(records)-size+1,size):
     yield dict(dataset=dataset,kind=collection['kind'],size=size,group=pos//size,remainder=len(records)%size),omega,records[pos:pos+size]
