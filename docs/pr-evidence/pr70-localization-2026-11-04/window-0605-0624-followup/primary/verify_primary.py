#!/usr/bin/env python3
from __future__ import annotations
import argparse,collections,hashlib,json,pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
HEAD='872905926887840025ba4c3f17151b96f8d3e6e2'; TREE='d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4'
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
def sha(b):
    if isinstance(b,str): b=b.encode()
    return hashlib.sha256(b).hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def fail(s): raise SystemExit('FAIL: '+s)
def need(v,s):
    if not v: fail(s)
def sums(root,name):
    d={}
    for line in (root/name).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); p=(root/n).resolve()
        need(p.is_relative_to(root.resolve()) and p.is_file() and sha(p.read_bytes())==h,'checksum '+n)
        need(n not in d,'duplicate checksum '+n); d[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/name}
    need(set(d)==actual,'checksum coverage '+str(root))
    return d
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=pathlib.Path,required=True); a=ap.parse_args(); repo=a.repo.resolve()
    root_sums=sums(ROOT,'SHA256SUMS.txt')
    pre=j(ROOT/'PRIMARY-REVIEW-MANIFEST.json')
    need((pre.get('head'),pre.get('tree'),pre.get('window'))==(HEAD,TREE,'W605-W624'),'primary pre-review pin')
    need(pre.get('otherW605ReviewDecisionsAccessed') is False and pre.get('blindOutputInspected') is False and pre.get('semanticReviewStartedBeforeSeal') is False,'primary/blind separation')
    cf=ROOT/'candidate-free-bundle'
    cfm=j(cf/'bundle-manifest.json'); cfi=j(cf/'candidate-free/input/manifest.json')
    need((cfm.get('head'),cfm.get('tree'),cfm.get('window'))==(HEAD,TREE,'W605-W624'),'copied candidate-free pin')
    need(sha((cf/'bundle-manifest.json').read_bytes())==pre['candidateFreeBundleManifestSha256'],'candidate-free manifest hash')
    need(sha((cf/'SHA256SUMS.txt').read_bytes())==pre['copiedCandidateFreeBundleChecksumListSha256'],'candidate-free checksum-list hash')
    subprocess.run([sys.executable,str(cf/'verify_bundle.py'),'--repo',str(repo)],check=True)
    out=ROOT/'primary-output'; out_sums=sums(out,'SHA256SUMS.txt'); om=j(out/'primary-manifest.json')
    actual_out={p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file() and p!=out/'SHA256SUMS.txt'}
    expected={x['path']:x for x in om['files']}
    need(set(expected)==actual_out-{'primary-manifest.json'},'primary output manifest file set')
    for name,x in expected.items():
        p=out/name; need(p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256'],'primary output manifest hash '+name)
    cells=lines(cf/'candidate-free/input/current-target-cells.jsonl')
    contexts={x['sourceId']:x for x in lines(cf/'candidate-free/input/source-contexts.jsonl')}
    need(len(cells)==240,'candidate-free cell count')
    cmap={(x['sourceId'],x['locale']):x for x in cells}; decisions=lines(out/'dispositions.jsonl')
    need(len(decisions)==240,'primary disposition count')
    seen=set(); counts=collections.Counter(); changed=[]
    for d in decisions:
        key=(d.get('sourceId'),d.get('locale')); need(key in cmap and key not in seen,'unknown/duplicate primary cell'); seen.add(key)
        c=cmap[key]; ctx=contexts[key[0]]
        need((d.get('window'),d.get('position'),d.get('sourceSha256'),d.get('currentTargetSha256'),d.get('callerContextSha256'))==('W605-W624',c['position'],c['sourceSha256'],c['currentTargetSha256'],c['callerContextSha256']),'primary cell/hash identity')
        need(d.get('callerContextAvailable') is (not ctx['callerless']),'caller availability')
        disp=d.get('disposition'); counts[disp]+=1
        if disp=='KEEP':
            need('proposedTarget' not in d and 'reason' not in d,'KEEP carries proposal')
        elif disp=='CHANGE':
            target=d.get('proposedTarget'); source=c['source']
            need(isinstance(target,str) and target,'CHANGE missing proposed target')
            need(collections.Counter(PH.findall(source))==collections.Counter(PH.findall(target)),'proposal placeholder mismatch')
            need(collections.Counter(TAG.findall(source))==collections.Counter(TAG.findall(target)),'proposal markup mismatch')
            need(not (collections.Counter(NUM.findall(source))-collections.Counter(NUM.findall(target))),'proposal numeric token loss')
            for literal in c['sourceProtectedLiterals']:
                need(literal in target,'proposal protected literal loss '+literal)
            changed.append(d)
        elif disp=='HOLD':
            need(not any(k in d for k in ('source','currentTarget','target','proposedTarget','reason')),'HOLD contains text')
        else: fail('unknown disposition '+str(disp))
    need(seen==set(cmap),'primary cell coverage')
    holds=lines(out/'hash-only-holds.jsonl')
    need(len(holds)==counts['HOLD'],'primary hold ledger count')
    summary=j(out/'summary.json')
    need(summary.get('dispositionCounts')==dict(counts),'primary disposition totals')
    need(summary.get('proposedChangeCount')==len(changed),'primary proposal count')
    need(summary.get('sourceCount')==20 and summary.get('localeCount')==12 and summary.get('cellCount')==240,'primary window totals')
    need(summary.get('blindness',{}).get('blindOutputInspected') is False,'blind output inspection attestation')
    need(not any('blind' in p.lower() for p in root_sums),'blind material in packet paths')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'sourceCount':20,'cellCount':240,'dispositionCounts':dict(counts),'proposals':len(changed),'proposalsWithoutCallerContext':summary['callerCoverage']['proposedChangesWithoutCallerContext'],'candidateFreeVerifier':'PASS','checksums':'PASS','blindOutputInspected':False},sort_keys=True))
if __name__=='__main__': main()
