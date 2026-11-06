#!/usr/bin/env python3
"""Verify a sealed ROMarrNG W785-W804 primary translation review packet."""
from __future__ import annotations
import argparse, collections, hashlib, json, re, subprocess, sys
from pathlib import Path

PIN_HEAD='bbbf84d0d83138a23143f6aa6075415ebcb36d3e'
PIN_TREE='fbf9ada4b4fd43a288ce498b24990312f0c32f22'
INPUT_DEFAULT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w785-804-20261105/candidate-free')
OUT=Path(__file__).resolve().parent

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def read_json(p): return json.loads(p.read_text(encoding='utf-8'))
def read_jsonl(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def run(args, cwd=None):
    p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(f"command failed {args!r}: {p.stderr.strip()}")
    return p.stdout.strip()
def checksum_list(path):
    run(['sha256sum','-c',path.name],cwd=path.parent)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path)
    ap.add_argument('--candidate-free',type=Path,default=INPUT_DEFAULT)
    a=ap.parse_args()
    inp=a.candidate_free.resolve()
    checksum_list(inp/'SHA256SUMS.txt')
    checksum_list(inp/'input/SHA256SUMS.txt')
    rows=read_jsonl(inp/'input/candidate-free-cells.jsonl')
    contexts={d['sourceId']:d for d in read_jsonl(inp/'input/source-contexts.jsonl')}
    im=read_json(inp/'input/manifest.json')
    sm=read_json(OUT/'summary.json')
    if (im['head'],im['tree']) != (PIN_HEAD,PIN_TREE): raise ValueError('candidate-free pin mismatch')
    if (sm['head'],sm['tree']) != (PIN_HEAD,PIN_TREE): raise ValueError('output pin mismatch')
    if sm['candidateFreeSha256SumsListSha256'] != sha_bytes((inp/'SHA256SUMS.txt').read_bytes()): raise ValueError('candidate-free checksum-list hash mismatch')
    if len(rows)!=240 or len({(r['sourceId'],r['locale']) for r in rows})!=240: raise ValueError('candidate-free rows incomplete or duplicated')
    ledger=read_jsonl(OUT/'primary-review-ledger.jsonl')
    if len(ledger)!=240 or len({(r['sourceId'],r['locale']) for r in ledger})!=240: raise ValueError('ledger rows incomplete or duplicated')
    bykey={(r['sourceId'],r['locale']):r for r in ledger}
    sourcebykey={(r['sourceId'],r['locale']):r for r in rows}
    if set(bykey)!=set(sourcebykey): raise ValueError('ledger/source cell coverage mismatch')
    counts=collections.Counter()
    new_holds=[]
    for key,base in sourcebykey.items():
        e=bykey[key]
        if e['sourceId']!=base['sourceId'] or e['locale']!=base['locale'] or e['position']!=base['position']: raise ValueError(f'identity mismatch {key}')
        if (e['sourceSha256'],e['currentTargetSha256'],e['callerContextSha256']) != (base['sourceSha256'],base['currentTargetSha256'],base['callerContextSha256']): raise ValueError(f'source/current/context hash mismatch {key}')
        if e.get('candidateFree') is not True or e.get('nativeSpeakerApproval') is not False: raise ValueError(f'review provenance mismatch {key}')
        counts[e['disposition']]+=1
        if base['callerless']:
            if e['disposition']!='hold_hash_only' or e.get('callerless') is not True: raise ValueError(f'callerless disposition mismatch {key}')
            prohibited={'source','currentTarget','proposedTarget','sourceText','currentText','targetText'}
            if prohibited.intersection(e): raise ValueError(f'callerless text leaked {key}')
            new_holds.append(e)
            continue
        if e.get('callerless') is not False: raise ValueError(f'caller-backed row mislabeled {key}')
        if (e.get('source'),e.get('currentTarget')) != (base['source'],base['currentTarget']): raise ValueError(f'caller-backed source/current text mismatch {key}')
        if sha_bytes(e['proposedTarget'].encode('utf-8')) != e['proposedTargetSha256']: raise ValueError(f'proposal hash mismatch {key}')
        if e['disposition']=='accept_current' and e['proposedTarget']!=base['currentTarget']: raise ValueError(f'accepted current differs from current target {key}')
        if e['disposition'] in ('correction','refinement') and e['proposedTarget']==base['currentTarget']: raise ValueError(f'change disposition has no change {key}')
        if e['callerReferenceCount']!=contexts[base['sourceId']]['exactMatchCount']: raise ValueError(f'caller count mismatch {key}')
        expected=[{'path':c['path'],'line':c['line'],'matchKind':c['matchKind'],'lineSha256':c['lineSha256'],'fileSha256':c['fileSha256'],'gitBlob':c['gitBlob']} for c in contexts[base['sourceId']]['callers']]
        if e['callerReferences']!=expected: raise ValueError(f'caller refs mismatch {key}')
        source_ph=re.findall(r'\{[^{}]+\}',base['source'])
        target_ph=re.findall(r'\{[^{}]+\}',e['proposedTarget'])
        if collections.Counter(source_ph)!=collections.Counter(target_ph): raise ValueError(f'placeholder fidelity mismatch {key}')
        if e['sourcePlaceholderTokens']!=base['sourcePlaceholderTokens']: raise ValueError(f'placeholder source pin mismatch {key}')
        for lit in base['sourceProtectedLiterals']:
            if lit not in e['proposedTarget']: raise ValueError(f'protected literal missing {key}: {lit}')
        tags=re.findall(r'</?[A-Za-z][^>]*>',e['proposedTarget'])
        if collections.Counter(tags)!=collections.Counter(base['sourceMarkupTags']): raise ValueError(f'markup token fidelity mismatch {key}')
        if e['sourceMarkupTags']!=base['sourceMarkupTags']: raise ValueError(f'markup source pin mismatch {key}')
    if counts != collections.Counter({'accept_current':176,'correction':3,'refinement':13,'hold_hash_only':48}): raise ValueError(f'disposition counts mismatch: {counts}')
    if sm['dispositions']!=dict(sorted(counts.items())): raise ValueError('summary disposition counts mismatch')
    if len(new_holds)!=48 or sm['priorActiveHashOnlyHoldsCopied']!=1012 or sm['resultingActiveHashOnlyHolds']!=1060: raise ValueError('hold continuity mismatch')
    prior_in=(inp/'input/prior-active-holds-hash-only.jsonl').read_bytes()
    prior_out=(OUT/'prior-active-holds-hash-only.jsonl').read_bytes()
    if prior_in!=prior_out: raise ValueError('prior hold ledger was altered')
    for line in prior_out.decode('utf-8').splitlines():
        if not line.strip(): continue
        d=json.loads(line)
        if any(k in d for k in ('source','currentTarget','proposedTarget','target','translation')): raise ValueError('prior hold text is not hash-only')
    if a.repo:
        repo=a.repo.resolve()
        head=run(['git','rev-parse','HEAD'],cwd=repo)
        tree=run(['git','rev-parse','HEAD^{tree}'],cwd=repo)
        status=run(['git','status','--porcelain=v1'],cwd=repo)
        if (head,tree)!=(PIN_HEAD,PIN_TREE): raise ValueError('worktree pin mismatch')
        if status: raise ValueError('worktree is not clean')
    print(json.dumps({'result':'PASS','head':PIN_HEAD,'tree':PIN_TREE,'cells':len(ledger),'callerBackedCells':192,'callerlessHashOnlyCells':48,'dispositions':dict(sorted(counts.items())),'priorActiveHolds':1012,'resultingActiveHolds':1060,'nativeSpeakerApproval':False,'candidateFreeChecksums':'PASS','priorHoldsByteIdentical':True,'worktreeCleanAndPinned':bool(a.repo)},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'FAIL: {e}',file=sys.stderr)
        sys.exit(1)
