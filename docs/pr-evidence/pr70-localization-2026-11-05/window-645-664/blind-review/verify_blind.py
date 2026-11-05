#!/usr/bin/env python3
"""Verify the independent blind-review packet against candidate-free inputs."""
import hashlib,json,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent; INPUT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w645-664-20261105/candidate-free/candidate-free/input')
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261105/romarrng-pr70-w625-644-pinned')
HEAD='9f8832f67195323955172dd4c3c40e29cbabb5da'; TREE='d6066baa3d03d3b4c6034e5af061fc4bc278b0f9'
sha=lambda x:hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()
def jl(path): return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s]
def sums(path):
 d={}
 for line in (path/'SHA256SUMS.txt').read_text().splitlines():
  h,n=line.split(None,1); n=n.lstrip('* '); assert n not in d; d[n]=h
 actual={x.name for x in path.iterdir() if x.is_file() and x.name!='SHA256SUMS.txt'}
 assert set(d)==actual
 for n,h in d.items(): assert sha((path/n).read_bytes())==h,n
 return d
sums(P); m=json.loads((P/'SUMMARY.json').read_text()); assert (m['head'],m['tree'])==(HEAD,TREE)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==HEAD
assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=REPO,text=True).strip()==TREE
assert subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()==''
inputs={(x['sourceId'],x['locale']):x for x in jl(INPUT/'current-target-cells.jsonl')}
contexts={x['sourceId']:x for x in jl(INPUT/'source-contexts.jsonl')}
rows=jl(P/'blind-ledger.jsonl'); props=jl(P/'proposals.jsonl'); holds=jl(P/'hash-only-holds.jsonl')
assert len(rows)==240 and len(inputs)==240 and len({(x['sourceId'],x['locale']) for x in rows})==240
assert sha((INPUT/'SHA256SUMS.txt').read_bytes())==m['candidateFreeChecksumListSha256']
for x in rows:
 key=(x['sourceId'],x['locale']); c=inputs[key]; ctx=contexts[x['sourceId']]
 assert x['position']==c['position'] and x['sourceSha256']==c['sourceSha256'] and x['callerContextSha256']==c['callerContextSha256']
 if ctx['callerless']:
  assert x['disposition']=='text-free-hold' and x['callerless'] is True
  assert not any(k in x for k in ('source','currentTarget','selectedTarget','callerPaths'))
  assert x['currentTargetSha256']==c['currentTargetSha256']
 else:
  assert x['source']==c['source'] and x['currentTarget']==c['currentTarget'] and x['currentTargetSha256']==c['currentTargetSha256']
  assert x['callerRefCount']==ctx['exactMatchCount'] and x['callerPaths']==sorted({r['path'] for r in ctx['callers']})
  assert x['selectedTargetSha256']==sha(x['selectedTarget'])
  if x['disposition']=='accept-current': assert x['selectedTarget']==x['currentTarget']
  else: assert x['disposition'] in ('propose-correction','propose-refinement') and x['selectedTarget']!=x['currentTarget']
assert len(holds)==96 and all(contexts[x['sourceId']]['callerless'] and inputs[(x['sourceId'],x['locale'])]['currentTargetSha256']==x['currentTargetSha256'] for x in holds)
assert len(props)==m['proposalCount'] and all(x['disposition'] in ('propose-correction','propose-refinement') for x in props)
counts={d:sum(x['disposition']==d for x in rows) for d in ('accept-current','propose-correction','propose-refinement','text-free-hold')}
assert counts==m['counts'] and sum(counts.values())==240
print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(rows),'counts':counts,'proposalCount':len(props),'hashOnlyHolds':len(holds),'checksumsVerified':True,'repoClean':True},ensure_ascii=False,indent=2))
