#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,re
I=Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
m=json.loads((I/'manifest.json').read_text())
assert (m['repository'],m['pullRequest'],m['window'],m['head'],m['tree'])==('snapetech-org/ROMarrNG',70,'W365-W384','d1698b94781c3c84e91faf03c75e8c308dc39c34','3f42d41fe4bbb8edd921ff161e8298ca66038a91')
rows=[json.loads(x) for x in (I/'translation-prompts.jsonl').read_text().splitlines() if x]
assert len(rows)==240 and len({(x['sourceId'],x['locale']) for x in rows})==240
assert sorted({x['position'] for x in rows})==list(range(365,385))
def scan(x):
 if isinstance(x,dict):
  assert not (set(x)&set(m['forbiddenFieldNames'])),set(x)&set(m['forbiddenFieldNames'])
  for v in x.values(): scan(v)
 elif isinstance(x,list):
  for v in x: scan(v)
for x in rows:
 scan(x)
 assert sha(x['source'].encode())==x['sourceSha256']
 assert x['sourcePlaceholderTokens']==sorted(set(re.findall(r'\{[^{}]+\}',x['source'])))
assert {x['position'] for x in rows if x['ambiguousContext']}=={368}
assert all(len(x['callerContextRefs'])>0 for x in rows)
files={x['path']:x for x in m['files']}
actual={p.name for p in I.iterdir() if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')}
assert set(files)==actual
for n,r in files.items():
 b=(I/n).read_bytes(); assert len(b)==r['bytes'] and sha(b)==r['sha256'],n
sums={}
for line in (I/'SHA256SUMS.txt').read_text().splitlines():
 h,n=line.split(None,1); sums[n.strip()]=h
assert set(sums)=={p.name for p in I.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
for n,h in sums.items(): assert sha((I/n).read_bytes())==h,n
print(json.dumps({'pass':True,'cells':240,'sources':20,'ambiguousPosition':368,'forbiddenFieldsAbsent':True,'head':m['head']}))
