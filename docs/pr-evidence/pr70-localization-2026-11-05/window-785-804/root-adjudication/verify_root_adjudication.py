#!/usr/bin/env python3
import collections, hashlib, json
from pathlib import Path

TASK=Path(__file__).resolve().parent
CF=TASK.parent/'candidate-free'/'input'
CROSS=TASK.parent/'cross-review'
HEAD='bbbf84d0d83138a23143f6aa6075415ebcb36d3e'
TREE='fbf9ada4b4fd43a288ce498b24990312f0c32f22'

def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_sums(root):
    listed={}
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,name=line.split('  ',1)
        path=(root/name).resolve()
        assert path.is_relative_to(root.resolve()) and path.is_file()
        assert sha(path.read_bytes())==digest
        assert name not in listed
        listed[name]=digest
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    assert actual==set(listed)
def main():
    verify_sums(TASK)
    cf=rows(CF/'candidate-free-cells.jsonl')
    cross=rows(CROSS/'integrated-cross-review-ledger.jsonl')
    ledger=rows(TASK/'root-disposition-ledger.jsonl')
    selected=rows(TASK/'selected-targets.jsonl')
    assert len(cf)==len(cross)==len(ledger)==240
    assert len(selected)==31
    cm={(r['position'],r['locale']):r for r in cf}
    xm={(r['position'],r['locale']):r for r in cross}
    lm={(r['position'],r['locale']):r for r in ledger}
    sm={(r['position'],r['locale']):r for r in selected}
    assert len(cm)==len(xm)==len(lm)==240 and len(sm)==31
    counts=collections.Counter()
    for key,c in cm.items():
        x,l=xm[key],lm[key]
        assert l['exactHead']==HEAD and l['exactTree']==TREE
        assert (l['sourceSha256'],l['currentTargetSha256'],l['callerContextSha256'])==(c['sourceSha256'],c['currentTargetSha256'],c['callerContextSha256'])
        assert (l['integratedDecision'],l['integratedTargetSha256'])==(x['integratedDecision'],x['integratedTargetSha256'])
        assert l['nativeSpeakerApproval'] is False
        counts[l['rootDisposition']]+=1
        if c.get('callerless'):
            assert l['rootDisposition']=='hold-hash-only' and l['rootTarget'] is None
            assert l['rootTargetSha256'] is None and l['sourceTextIncluded'] is False and l['currentTargetTextIncluded'] is False
            assert 'source' not in l and 'currentTarget' not in l
        elif key in sm:
            s=sm[key]
            assert l['rootDisposition'] in ('correction','refinement')
            assert l['rootTarget']==x['integratedTarget']==s['rootTarget']
            assert sha(l['rootTarget'])==l['rootTargetSha256']==s['rootTargetSha256']==x['integratedTargetSha256']
            assert s['sourceId']==c['sourceId'] and s['sourceSha256']==c['sourceSha256']
            assert s['currentTargetSha256']==c['currentTargetSha256']
            assert s['callerContextSha256']==c['callerContextSha256']
            assert l['rootDisposition']==s['rootDisposition']
            assert x['tokenAudit']['placeholdersMatch'] and x['tokenAudit']['markupMatches'] and x['tokenAudit']['numbersMatch'] and x['tokenAudit']['protectedLiteralsMatch']
        else:
            assert l['rootDisposition']=='accept-current'
            assert l['rootTargetSha256']==c['currentTargetSha256']==x['integratedTargetSha256']
    assert counts=={'accept-current':161,'correction':9,'refinement':22,'hold-hash-only':48}
    att=json.loads((TASK/'input-attestation.json').read_text())
    assert att['exactHead']==HEAD and att['exactTree']==TREE and att['selectedTargetCount']==31
    assert att['candidateFreeCellsSha256']==sha((CF/'candidate-free-cells.jsonl').read_bytes())
    assert att['integratedCrossLedgerSha256']==sha((CROSS/'integrated-cross-review-ledger.jsonl').read_bytes())
    summary=json.loads((TASK/'summary.json').read_text())
    assert summary['nativeSpeakerApproval'] is False and summary['headedBrowserReviewPerformed'] is False
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':240,'selectedTargets':31,'dispositions':dict(counts),'priorActiveHashOnlyHolds':1012,'resultingActiveHashOnlyHolds':1060,'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False,'checksums':'PASS'},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
