"""Small operational snapshot; counts include explicit not-run execution slots."""
import argparse
from collections import defaultdict
from pathlib import Path
import sqlite3

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory',type=Path)
args=parser.parse_args()
with sqlite3.connect(f'file:{args.directory/"run.sqlite3"}?mode=ro',uri=True) as db:
    counts=defaultdict(dict)
    for query,phase,n in db.execute("SELECT query_id,phase,count(*) FROM tasks WHERE state='finished' GROUP BY query_id,phase"):
        counts[query][phase]=n
    active=[key.split('/')[:3] for key, in db.execute("SELECT key FROM tasks WHERE state='running'")]
print('Recorded execution slots:',', '.join(f"{q}={c['execution']}" for q,c in counts.items() if 'execution' in c))
print('Finished warmup tasks:',sum(c.get('warmup',0) for c in counts.values()))
print('Active:',active)
