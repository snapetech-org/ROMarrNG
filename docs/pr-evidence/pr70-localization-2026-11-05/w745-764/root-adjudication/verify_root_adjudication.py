#!/usr/bin/env python3
import collections, hashlib, json, re
from pathlib import Path
BASE=Path(__file__).resolve().parent
CROSS=BASE.parent/'cross-review'
HEAD='68c5c9d4ad13ad5d02b9c455f429d8a5149d363d'
TREE='524db27557a65d64343b15c9983f6ac2f92f90c4'
def sha(b): return hashlib.sha256(b).hexdigest()
def pairs(p):
 out=[]
 for line in p.read_bytes().splitlines():
  if line.strip(): out.append((json.loads(line),line))
 return out
def sums(d):
 exp={}
 for line in (d/'SHA256SUMS.txt').read_text(encoding='ascii').splitlines():
  h,n=line.split('  ',1); exp[n]=h
 act={p.relative_to(d).as_posix():sha(p.read_bytes()) for p in d.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
 assert exp==act,(d,sorted(set(exp)^set(act)))
def token_ok(s,t,lits):
 for pat in (r'\{[^{}]+\}',r'<[^>]+>',r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])'):
  if collections.Counter(re.findall(pat,s))!=collections.Counter(re.findall(pat,t)): return False
 return all(x in t for x in lits)
def verify():
 sums(BASE); sums(CROSS)
 cp=pairs(CROSS/'cross-ledger.jsonl'); rp=pairs(BASE/'root-disposition-ledger.jsonl'); sel=pairs(BASE/'selected-targets.jsonl')
 assert len(cp)==len(rp)==240 and len(sel)==7
 rm={(x['position'],x['locale']):x for x,_ in rp}; counts=collections.Counter()
 for c,craw in cp:
  r=rm[(c['position'],c['locale'])]
  assert r['exactHead']==HEAD and r['exactTree']==TREE
  for k in ('sourceSha256','currentTargetSha256','callerContextSha256'):
   assert r[k]==c[k],(k,r,c)
  assert r.get('candidateFreeRecordSha256')==c.get('candidateFreeRecordSha256')
  assert r['crossRecordSha256']==sha(craw) and r['primaryDecision']==c['primaryDecision'] and r['blindAction']==c['blindAction']
  counts[r['rootDisposition']]+=1
  if c['callerless']:
   assert r['rootDisposition']=='hold-callerless-hash-only' and r['rootTarget'] is None and r['sourceId'] is None
   assert 'source' not in r and 'currentTarget' not in r
  else:
   assert r['sourceId']==c['sourceId'] and r['source']==c['source'] and r['currentTarget']==c['currentTarget']
   assert r['rootTarget']==c['selectedTarget'] and r['rootTargetSha256']==sha(r['rootTarget'].encode())
   assert token_ok(r['source'],r['rootTarget'],c['tokenEvidence']['sourceProtectedLiterals'])
 assert counts=={'accept-current':209,'correction':7,'hold-callerless-hash-only':24},counts
 return {'result':'PASS','head':HEAD,'tree':TREE,'cells':240,'rootDispositionCounts':dict(counts),'selectedTargets':7,'callerlessTextRedaction':'PASS','crossInputChecksums':'PASS'}
if __name__=='__main__': print(json.dumps(verify(),ensure_ascii=False,indent=2))
