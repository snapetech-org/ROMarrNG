#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, re, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent
TASK=ROOT.parent
HEAD='01da053f0e6a47e7184fb86da77f66b7b6719653'
TREE='dcb9c1766831e217ffca7fb77068b97c33b9524e'
BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def fail(s): raise SystemExit('FAIL: '+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=pathlib.Path,required=True); args=ap.parse_args()
    inp=TASK/'candidate-free-bundle'/'candidate-free'/'input'
    pre=readj(TASK/'PRIMARY-REVIEW-MANIFEST.json')
    im=readj(inp/'manifest.json'); om=readj(ROOT/'primary-manifest.json')
    if (im.get('head'),im.get('tree'),im.get('window'))!=(HEAD,TREE,'W585-W604'): fail('candidate-free pin')
    if (om.get('head'),om.get('tree'),om.get('window'))!=(HEAD,TREE,'W585-W604'): fail('primary output pin')
    if not (pre.get('otherW585ReviewDecisionsAccessed') is False and pre.get('staleW585PrimaryPacketAccessed') is False and pre.get('semanticReviewStartedBeforeSeal') is False): fail('pre-review blindness manifest')
    if not (om.get('otherW585ReviewDecisionsAccessed') is False and om.get('staleW585PrimaryPacketAccessed') is False): fail('primary output blindness attestation')
    # Output checksum coverage and manifest file hashes.
    sums={}
    for n,line in enumerate((ROOT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): continue
        digest,name=line.split('  ',1)
        if name in sums: fail(f'duplicate output checksum line {n}')
        p=(ROOT/name).resolve()
        if not p.is_relative_to(ROOT.resolve()) or not p.is_file() or sha(p.read_bytes())!=digest: fail('output checksum '+name)
        sums[name]=digest
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    if set(sums)!=actual: fail('output checksum coverage')
    expected={f['path']:f for f in om['files']}
    if set(expected)!=(actual-{'primary-manifest.json'}): fail('primary manifest file set')
    for name,f in expected.items():
        p=ROOT/name
        if len(p.read_bytes())!=f['bytes'] or sha(p.read_bytes())!=f['sha256']: fail('primary manifest digest '+name)
    # Reattest the local source worktree and live branch/pull refs.
    repo=args.repo.resolve()
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    tree=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD^{tree}'],text=True).strip()
    status=subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1'],text=True).strip()
    if head!=HEAD or tree!=TREE or status: fail('source worktree pin/cleanliness')
    remote=subprocess.check_output(['git','-C',str(repo),'ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head'],text=True)
    refs={line.split()[1]:line.split()[0] for line in remote.splitlines() if line.strip()}
    if refs.get(f'refs/heads/{BRANCH}')!=HEAD or refs.get('refs/pull/70/head')!=HEAD: fail('live branch/pull ref moved')
    # Validate every disposition against the exact candidate-free cell identity and hashes.
    source_cells=lines(inp/'current-target-cells.jsonl')
    if len(source_cells)!=240: fail('candidate-free input cell count')
    cell_map={(c['sourceId'],c['locale']):c for c in source_cells}
    contexts={c['sourceId']:c for c in lines(inp/'source-contexts.jsonl')}
    decisions=lines(ROOT/'dispositions.jsonl')
    if len(decisions)!=240: fail('disposition row count')
    seen=set(); counts=collections.Counter(); holds=[]
    for d in decisions:
        key=(d.get('sourceId'),d.get('locale'))
        if key in seen or key not in cell_map: fail('duplicate/unknown cell')
        seen.add(key); c=cell_map[key]; ctx=contexts[d['sourceId']]
        if (d.get('position'),d.get('sourceSha256'),d.get('currentTargetSha256'),d.get('callerContextSha256'))!=(c['position'],c['sourceSha256'],c['currentTargetSha256'],c['callerContextSha256']): fail('cell identity/hash mismatch')
        if d.get('callerContextAvailable') is not (not ctx['callerless']): fail('caller context mismatch')
        disposition=d.get('disposition'); counts[disposition]+=1
        if disposition=='KEEP':
            if 'proposedTarget' in d or 'holdReasonSha256' in d: fail('KEEP has proposal/hold fields')
        elif disposition=='CHANGE':
            target=d.get('proposedTarget')
            if not isinstance(target,str) or not target: fail('CHANGE missing proposed target')
            src=c['source']
            ph=lambda x:collections.Counter(re.findall(r'\{[^{}]+\}',x))
            tags=lambda x:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',x))
            if ph(src)!=ph(target) or tags(src)!=tags(target): fail('proposal placeholder/markup mismatch')
        elif disposition=='HOLD':
            if any(k in d for k in ('source','currentTarget','proposedTarget','reason')): fail('hold row contains text')
            if not isinstance(d.get('holdReasonSha256'),str): fail('hold row missing reason hash')
            holds.append(d)
        else: fail('unknown disposition')
    if seen!=set(cell_map): fail('disposition cell set mismatch')
    hold_rows=lines(ROOT/'hash-only-holds.jsonl')
    if len(hold_rows)!=len(holds): fail('hash-only hold count mismatch')
    required={'position','sourceId','sourceSha256','locale','currentTargetSha256','holdReasonSha256'}
    for h in hold_rows:
        if set(h)!=required: fail('hold ledger schema is not hash-only')
    if {tuple(h[k] for k in ('sourceId','locale','currentTargetSha256')) for h in hold_rows}!={tuple(h[k] for k in ('sourceId','locale','currentTargetSha256')) for h in holds}: fail('hold ledger cell mismatch')
    summary=readj(ROOT/'summary.json')
    if summary.get('dispositionCounts')!=dict(counts) or summary.get('hashOnlyHoldCount')!=len(holds): fail('summary disposition totals')
    if summary.get('sourceCount')!=20 or summary.get('localeCount')!=12 or summary.get('cellCount')!=240: fail('summary window counts')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'dispositionRows':len(decisions),'dispositionCounts':dict(counts),'hashOnlyHolds':len(holds),'liveRefs':'PASS','sourceWorktree':'CLEAN'},sort_keys=True))
if __name__=='__main__': main()
