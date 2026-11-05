#!/usr/bin/env python3
"""Verify W725-W744 review packets and exact product commit readback."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent
CF=BASE/'candidate-free'/'input'; PRIMARY=BASE/'primary-review'; BLIND=BASE/'blind-review'
CROSS=BASE/'cross-review'; ROOT=BASE/'root-adjudication'; APP=BASE/'application'
HEAD='c3f92c45b4b4f8d79a8caa99417f9970ebc42a26'
TREE='3f835643e4f557999d533c3e832fc92036d4b01a'
PRODUCT='19038831e63edd53e4aec62f072c6d2eda9245cd'
CAT='romarr/ui-labels.json'
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def run_verifier(path, args=()):
    r=subprocess.run(['python3',str(path),*args],cwd=path.parent,capture_output=True,text=True)
    assert r.returncode==0,(path,r.stdout,r.stderr)
    return json.loads(r.stdout)
def verify_sums(directory):
    p=directory/'SHA256SUMS.txt'
    if not p.exists(): return False
    r=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=directory,capture_output=True,text=True)
    assert r.returncode==0,(directory,r.stdout,r.stderr)
    return True
def token_ok(source,target,protected):
    pats=[r'\{[^{}]+\}',r'<[^>]+>',r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])']
    return all(collections.Counter(re.findall(p,source))==collections.Counter(re.findall(p,target)) for p in pats) and all(x in target for x in protected)
def verify(repo, write_results=False):
    repo=Path(repo).resolve()
    for d in (BASE,BASE/'candidate-free',PRIMARY,BLIND,CROSS,ROOT,APP): verify_sums(d)
    cfraw=[x for x in (CF/'candidate-free-cells.jsonl').read_bytes().splitlines() if x.strip()]
    cfs=[json.loads(x) for x in cfraw]
    cm={(r['position'],r['locale']):r for r in cfs}
    rowhash={(r['position'],r['locale']):sha(line) for r,line in zip(cfs,cfraw)}
    pm={(r['position'],r['locale']):r for r in jl(PRIMARY/'ledger.jsonl')}
    bm={(r['position'],r['locale']):r for r in jl(BLIND/'review-cells.jsonl')}
    xm={(r['position'],r['locale']):r for r in jl(CROSS/'cross-review.jsonl')}
    rootrows=jl(ROOT/'root-disposition-ledger.jsonl'); targets=jl(ROOT/'selected-targets.jsonl')
    assert len(cm)==len(pm)==len(bm)==len(xm)==len(rootrows)==240 and len(targets)==5
    counts=collections.Counter()
    for r in rootrows:
        k=(r['position'],r['locale']); c,p,b,x=cm[k],pm[k],bm[k],xm[k]
        assert r['exactHead']==HEAD and r['exactTree']==TREE
        assert r['candidateFreeRowSha256']==rowhash[k]
        assert r['sourceSha256']==c['sourceSha256']==x['sourceSha256']
        assert r['currentTargetSha256']==c['currentTargetSha256']==x['currentTargetSha256']
        assert r['callerContextSha256']==c['callerContextSha256']==x['callerContextSha256']
        assert r['primaryDecision']==p['decision'] and r['blindDecision']==b['decision']
        if c['callerless']:
            assert r['rootDisposition']=='hold-hash-only' and r['rootTarget'] is None
            assert not any(f in r for f in ('source','sourceId','currentTarget'))
            assert r['sourceTextIncluded'] is False and r['currentTargetTextIncluded'] is False
        else:
            assert r['sourceId']==c['sourceId'] and r['source']==c['source']
            assert r['currentTarget']==c['currentTarget']
            assert token_ok(c['source'],r['rootTarget'],c['sourceProtectedLiterals'])
            assert tsha(r['rootTarget'])==r['rootTargetSha256']
            if r['rootDisposition']=='accept-current':
                assert r['rootTarget']==c['currentTarget'] and x['crossDisposition']=='accept-current'
            else:
                assert r['rootDisposition'] in ('correction','refinement')
                assert x['crossRecommendedTarget']==r['rootTarget']
        counts[r['rootDisposition']]+=1
    assert counts=={'accept-current':223,'correction':2,'refinement':3,'hold-hash-only':12}
    att=j(ROOT/'input-attestation.json'); assert att['blindCandidateFreePinsMatch'] is True
    assert att['blindSummaryPositionDiscrepancy']['candidateFreePrimaryBlindRowsAndCrossRowsAgreeOnIndex']==732
    product_parent=git(repo,'rev-parse',PRODUCT+'^')
    assert product_parent==HEAD
    names=git(repo,'diff-tree','--no-commit-id','--name-only','-r',PRODUCT).splitlines()
    assert names==[CAT]
    rb=j(APP/'readback.json')
    assert rb['productCommit']==PRODUCT and rb['commitParent']==HEAD and rb['productCommitNames']==[CAT]
    product_raw=subprocess.check_output(['git','-C',str(repo),'show',f'{PRODUCT}:{CAT}'])
    assert sha(product_raw)==rb['catalogSha256After']
    base_raw=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{CAT}'])
    expected=json.loads(base_raw); actual=json.loads(product_raw)
    for r in targets: expected['messages'][r['sourceId']]['translations'][r['locale']]=r['rootTarget']
    assert (json.dumps(expected,ensure_ascii=False,indent=2)+'\n').encode('utf-8')==product_raw
    assert list(expected['messages'])==list(actual['messages'])
    assert rb['changedCellCount']==5 and rb['allOtherCatalogCellsUnchanged'] is True
    assert rb['catalogKeyOrderPreserved'] is True and rb['all12DirectLocalesHave1836NonemptyMessages'] is True
    if git(repo,'rev-parse','HEAD')!=PRODUCT:
        assert subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',PRODUCT,'HEAD']).returncode==0
    child=j(ROOT/'input-verifier-results.json')
    assert all(child[name]['result']=='PASS' for name in ('candidateFree','primary','blind','cross'))
    assert all(child[name]['head']==HEAD and child[name]['tree']==TREE for name in ('candidateFree','primary','blind','cross'))
    assert child['blind']['worktreeCleanAtInputHead'] is True
    result={'result':'PASS','window':'W725-W744','inputHead':HEAD,'inputTree':TREE,
      'productCommit':PRODUCT,'rootDispositionCounts':dict(counts),'selectedTargets':5,
      'hashOnlyHolds':12,'packetVerifiers':'PASS','productReadback':'PASS',
      'workflowDiff':'none in product commit','nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False,
      'inputVerifierResults':child}
    path=APP/'verification-results.json'; encoded=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if write_results: path.write_text(encoded,encoding='utf-8')
    elif path.exists(): assert path.read_text(encoding='utf-8')==encoded
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--write-results',action='store_true'); a=ap.parse_args()
    print(json.dumps(verify(a.repo,a.write_results),ensure_ascii=False,indent=2))
