#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
PACKETS=HERE.parent
INPUT=PACKETS/'primary'/'input'; BLIND_INPUT=PACKETS/'blind'/'input'
PRIMARY=PACKETS/'primary'/'review'; BLIND=PACKETS/'blind'/'review'; CROSS=HERE

def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(b): return hashlib.sha256(b).hexdigest()
def file_sha(p): return sha(p.read_bytes())
def verify_sums(folder):
    for line in (folder/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1); assert file_sha(folder/name)==digest,(folder/name)
def index(path):
    rows=readjl(path); d={(x['position'],x['locale']):x for x in rows}; assert len(rows)==len(d); return d

for d in (INPUT,PRIMARY,BLIND,CROSS): verify_sums(d)
assert {p.name for p in INPUT.iterdir()}=={p.name for p in BLIND_INPUT.iterdir()}
for p in INPUT.iterdir(): assert file_sha(p)==file_sha(BLIND_INPUT/p.name),p.name
manifest=readj(INPUT/'manifest.json'); psummary=readj(PRIMARY/'summary.json'); bsummary=readj(BLIND/'summary.json'); summary=readj(CROSS/'cross-audit-summary.json')
assert manifest['head']=='6bef0c74632067906fd07279fa6bd3fd59159a48' and manifest['tree']=='4fd79e67f37e4c66d0253199418973d965a3fbd6'
assert manifest['cellCount']==240 and manifest['candidateFree'] and manifest['priorHoldCellCount']==288 and manifest['priorHoldTargetsUnchanged']
assert manifest['translationDispatchGapPositions']==[346,350]
assert summary['candidateFreeInput']['manifestSha256']==file_sha(INPUT/'manifest.json')
assert summary['candidateFreeInput']['checksumListSha256']==file_sha(INPUT/'SHA256SUMS.txt')
assert summary['primaryReview']['ledgerSha256']==file_sha(PRIMARY/'review-decisions.jsonl')
assert summary['blindReview']['ledgerSha256']==file_sha(BLIND/'blind-ledger.jsonl')
current=index(INPUT/'current-target-cells.jsonl'); primary=index(PRIMARY/'review-decisions.jsonl'); blind=index(BLIND/'blind-ledger.jsonl'); cross=index(CROSS/'cross-audit-ledger.jsonl')
assert set(current)==set(primary)==set(blind)==set(cross) and len(cross)==240
contexts={x['position']:x for x in readjl(INPUT/'source-contexts.jsonl')}; ph=re.compile(r'\{[^{}]+\}')
for k,r in cross.items():
    c=current[k]; p=primary[k]; b=blind[k]; ctx=contexts[k[0]]
    assert r['sourceId']==c['sourceId']==p['sourceId']==b['sourceId']==ctx['sourceId']
    assert r['source']==c['source']==p['source']==b['source'] and r['sourceSha256']==c['sourceSha256']==p['sourceSha256']==b['sourceSha256']
    assert r['currentTarget']==c['currentTarget']==p['currentTarget']==b['currentTarget']
    assert r['currentTargetSha256']==c['currentTargetSha256']==p['currentTargetSha256']==b['currentTargetSha256']==sha(r['currentTarget'].encode())
    assert r['callerContextSha256']==ctx['callerContextSha256']==p['callerContextSha256']==b['callerContextSha256']
    assert r['callerContextRefs']==ctx['callerContextRefs']
    assert r['primaryTarget']==p['selectedTarget'] and r['blindTarget']==b['blindTarget']
    assert r['primaryTargetSha256']==sha(r['primaryTarget'].encode()) and r['blindTargetSha256']==sha(r['blindTarget'].encode())
    assert r['selectedTarget'] in (r['currentTarget'],r['primaryTarget'],r['blindTarget'])
    assert r['selectedTargetSha256']==sha(r['selectedTarget'].encode())
    assert collections.Counter(ph.findall(r['source']))==collections.Counter(ph.findall(r['selectedTarget']))
    assert all(str(x) in r['selectedTarget'] for x in r['sourceNumericTokens'])
    assert all(str(x) in r['selectedTarget'] for x in r['sourceProtectedLiterals'])
    assert all(r['structuralChecks'].values()) and not r['callerResolutionHold']
    if k[0] in (346,350): assert r['runtimeDispatchGap'] and r['runtimeDispatchFollowup']['required']
    else: assert not r['runtimeDispatchGap']
prior=readjl(INPUT/'prior-hold-reattestation.jsonl')
assert len(prior)==288 and all(x['targetUnchanged'] and x['currentTargetSha256']==x['priorCurrentTargetSha256'] for x in prior)
assert sum(not x['proposalTargetAgreement'] for x in cross.values())==103
assert sum(primary[k]['decision']!=blind[k]['disposition'] for k in cross)==82
assert sum(x['selectedTarget']!=x['currentTarget'] for x in cross.values())==144
assert summary['comparison']=={'targetAgreementCount':137,'targetDisagreementCount':103,'dispositionAgreementCount':158,'dispositionDisagreementCount':82,'combinedDifferingCellCount':112,'differingBothTargetAndDisposition':73,'targetOnlyDisagreementCount':30,'dispositionOnlyDisagreementCount':9}
assert psummary['cellCount']==240 and bsummary['cellCount']==240
print('PASS: copied candidate-free, primary, blind, and cross-audit evidence; 240 cells, exact target/context hashes, tokens, 288 prior holds, and both runtime follow-ups verified.')
