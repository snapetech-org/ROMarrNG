#!/usr/bin/env python3
import collections, hashlib, json, re
from pathlib import Path
OUT=Path(__file__).resolve().parent; S=Path('/home/keith/Documents/code/task-scratch')
I=S/'romarrng-pr70-w345-364-primary-20261103'/'input'; P=S/'romarrng-pr70-w345-364-primary-20261103'/'primary-review'; B=S/'romarrng-pr70-w345-364-blind-20261103'/'blind-review'
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sums(d):
 for line in (d/'SHA256SUMS.txt').read_text().splitlines():
  digest,name=line.split('  ',1); assert h(d/name)==digest,(d/name)
def idx(p):
 rows=jl(p); d={(x['position'],x['locale']):x for x in rows}; assert len(d)==len(rows); return d
for folder in (I,P,B,OUT): sums(folder)
m=j(I/'manifest.json'); assert m['head']=='6bef0c74632067906fd07279fa6bd3fd59159a48' and m['tree']=='4fd79e67f37e4c66d0253199418973d965a3fbd6'
assert m['priorHoldCellCount']==288 and m['priorHoldTargetsUnchanged'] and m['translationDispatchGapPositions']==[346,350]
holds=jl(I/'prior-hold-reattestation.jsonl'); assert len(holds)==288 and all(x['targetUnchanged'] and x['currentTargetSha256']==x['priorCurrentTargetSha256'] for x in holds)
C=idx(I/'current-target-cells.jsonl'); PR=idx(P/'review-decisions.jsonl'); BL=idx(B/'blind-ledger.jsonl'); A=idx(OUT/'cross-audit-ledger.jsonl')
assert set(C)==set(PR)==set(BL)==set(A) and len(A)==240
ctx={x['position']:x for x in jl(I/'source-contexts.jsonl')}; ph=re.compile(r'\{[^{}]+\}')
for k,r in A.items():
 c=C[k]; p=PR[k]; b=BL[k]
 assert r['sourceId']==c['sourceId']==p['sourceId']==b['sourceId']==ctx[k[0]]['sourceId']
 assert r['sourceSha256']==c['sourceSha256']==p['sourceSha256']==b['sourceSha256']
 for field,text in [('currentTargetSha256',r['currentTarget']),('primaryTargetSha256',r['primaryTarget']),('blindTargetSha256',r['blindTarget']),('selectedTargetSha256',r['selectedTarget'])]: assert r[field]==hashlib.sha256(text.encode()).hexdigest()
 assert r['selectedTarget'] in (r['currentTarget'],r['primaryTarget'],r['blindTarget'])
 assert r['callerContextSha256']==ctx[k[0]]['callerContextSha256'] and r['callerContextRefs']==ctx[k[0]]['callerContextRefs']
 assert collections.Counter(ph.findall(r['source']))==collections.Counter(ph.findall(r['selectedTarget']))
 assert all(str(x) in r['selectedTarget'] for x in r['sourceNumericTokens']) and all(str(x) in r['selectedTarget'] for x in r['sourceProtectedLiterals'])
 assert all(r['structuralChecks'].values())
assert sum(not x['proposalTargetAgreement'] for x in A.values())==103
assert sum(x['crossAuditResolution']=='shared-target-disposition-adjudicated' for x in A.values())==9
assert sum(x['crossAuditResolution']=='proposal-target-disagreement-adjudicated' for x in A.values())==103
assert sum(x['runtimeDispatchGap'] for x in A.values())==24
s=j(OUT/'cross-audit-summary.json'); c=s['comparison']; assert s['cellCount']==240 and c['targetDisagreementCount']==103 and c['dispositionDisagreementCount']==82 and c['combinedDifferingCellCount']==112
print('PASS: 240 cells and exact candidate/source/context/target hashes verified; input/review/output checksums pass; 288 prior holds unchanged; dispatch gaps 346 and 350 retained.')
