#!/usr/bin/env python3
"""Verify W685-W704 candidate-free, both reviews, root decisions, and product readback."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent
CF=BASE/'candidate-free'/'input'
PRIMARY=BASE/'primary-review'
BLIND=BASE/'blind-review'
CROSS=BASE/'cross-review'; ROOT=BASE/'root-adjudication'; APP=BASE/'application'
HEAD='43d2858744ef20cd58462643fed534ac61d2ffad'
TREE='73e8f50d65cb611def996b01bab0b00628b65860'
PRODUCT='a26feabfcae338207fae3d9c682425ab9c0d4226'
PRODUCT_TREE='b0f61607d03924a6e4bff9acebfe9d1dd7af6e8a'
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_sums(d):
    expected={}
    for line in (d/'SHA256SUMS.txt').read_text(encoding='ascii').splitlines():
        h,n=line.split('  ',1); expected[n]=h
    actual={p.relative_to(d).as_posix():sha(p.read_bytes()) for p in d.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    assert expected==actual,(d,sorted(set(expected)^set(actual)))
def token_ok(source,target,protected):
    pats=[r'\{[^{}]+\}',r'<[^>]+>',r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])']
    return all(collections.Counter(re.findall(p,source))==collections.Counter(re.findall(p,target)) for p in pats) and all(x in target for x in protected)
def verify(repo=None):
    verify_sums(CROSS); verify_sums(ROOT)
    cflines=[x for x in (CF/'candidate-free-cells.jsonl').read_bytes().splitlines() if x.strip()]
    cells=[json.loads(x) for x in cflines]
    rowhash={(r['position'],r['locale']):sha(line) for r,line in zip(cells,cflines)}
    cm={(r['position'],r['locale']):r for r in cells}
    pm={(r['sourcePosition'],r['locale']):r for r in jl(PRIMARY/'ledger.jsonl')}
    bm={(r['position'],r['locale']):r for r in jl(BLIND/'review.jsonl')}
    cross={(r['position'],r['locale']):r for r in jl(CROSS/'cross-review-ledger.jsonl')}
    root=jl(ROOT/'root-disposition-ledger.jsonl')
    targets=jl(ROOT/'selected-targets.jsonl')
    assert len(cm)==len(pm)==len(bm)==len(cross)==len(root)==240
    assert len(targets)==7
    counts=collections.Counter()
    for r in root:
        k=(r['position'],r['locale']); c=cm[k]; p=pm[k]; b=bm[k]; x=cross[k]
        assert r['sourceSha256']==c['sourceSha256'] and r['currentTargetSha256']==c['currentTargetSha256']
        assert r['callerContextSha256']==c['callerContextSha256'] and r['candidateFreeRowSha256']==rowhash[k]
        assert r['primaryDecision']==p['decision'] and r['blindDecision']==b['decision']
        assert r['exactHead']==HEAD and r['exactTree']==TREE
        for item in (p,b):
            assert item.get('sourceTextSha256',item.get('sourceSha256'))==c['sourceSha256']
            assert item.get('currentTargetSha256')==c['currentTargetSha256']
            assert item.get('callerContextSha256')==c['callerContextSha256']
        assert x['sourceSha256']==c['sourceSha256'] and x['currentTargetSha256']==c['currentTargetSha256']
        if c.get('callerless'):
            assert r['rootDisposition']=='hold-hash-only' and r['rootTarget'] is None and r['rootTargetSha256'] is None
            assert not any(key in r for key in ('source','currentTarget','sourceId'))
            assert p['decision']=='hold-hash-only' and b['decision']=='hold'
        else:
            assert r['sourceId']==c['sourceId'] and r['source']==c['source'] and r['currentTarget']==c['currentTarget']
            assert r['rootTarget'] is not None and tsha(r['rootTarget'])==r['rootTargetSha256']
            assert token_ok(c['source'],r['rootTarget'],c['sourceProtectedLiterals'])
            if r['rootDisposition']=='accept-current':
                assert r['rootTarget']==c['currentTarget'] and p['decision']=='accept-current' and b['decision']=='accept'
            else:
                assert r['rootDisposition'] in ('correction','refinement')
                assert b['replacementText']==r['rootTarget']
                if p.get('recommendedTarget') is not None: assert p['recommendedTarget']==r['rootTarget']
        counts[r['rootDisposition']]+=1
    assert counts=={'accept-current':221,'correction':5,'refinement':2,'hold-hash-only':12}
    cs=j(CROSS/'summary.json'); rs=j(ROOT/'summary.json')
    assert cs['rootDispositionCounts']==rs['rootDispositionCounts']==dict(counts)
    assert cs['exactHead']==rs['exactHead']==HEAD and cs['exactTree']==rs['exactTree']==TREE
    assert j(ROOT/'input-attestation.json')['blindCandidateFreePinsMatch'] is True
    app=j(APP/'readback-before-commit.json')
    assert app['productCommit']==PRODUCT and app['productTree']==PRODUCT_TREE and app['commitParent']==HEAD
    assert app['changedCellCount']==7 and app['allOtherCatalogCellsUnchanged'] is True
    if repo:
        repo=Path(repo)
        def git(*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
        assert git('show','-s','--format=%T',PRODUCT)==PRODUCT_TREE
        raw=subprocess.check_output(['git','-C',str(repo),'show',PRODUCT+':romarr/ui-labels.json'])
        assert sha(raw)==app['catalogSha256After']
    return {'result':'PASS','head':HEAD,'tree':TREE,'productCommit':PRODUCT,'rootDispositionCounts':dict(counts),'selectedTargets':7,'candidateFreeRowBindings':240,'primaryAndBlindBindings':240,'callerlessTextRedaction':'PASS','productReadback':'PASS'}
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--repo'); a=p.parse_args()
    print(json.dumps(verify(a.repo),ensure_ascii=False,indent=2))
