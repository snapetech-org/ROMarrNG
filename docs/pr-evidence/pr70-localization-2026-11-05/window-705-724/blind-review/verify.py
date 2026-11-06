#!/usr/bin/env python3
"""Portable verifier for ROMarrNG W705-W724 blind review."""
import argparse, hashlib, json, sys
from collections import Counter
from pathlib import Path

HEAD='50e3f8a48a800affff8bad367b5c493cc0fdfd62'
TREE='22cd46ff4821fcbbe76b4760a15e22d688b3f548'

def db(b): return hashlib.sha256(b).hexdigest()
def dt(s): return db(s.encode('utf-8'))
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def dobj(o): return db(canon(o))
def readj(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def refs(ctx): return [{k:c.get(k) for k in ('path','line','gitBlob','fileSha256','lineSha256','excerptSha256')} for c in ctx['callers']]
def binding(pos,loc,source,target,ctx,callers): return dobj({'position':pos,'locale':loc,'sourceSha256':source,'currentTargetSha256':target,'callerContextSha256':ctx,'callerHashesSha256':callers})
def verify(package, inputs):
    sums=package/'SHA256SUMS.txt'; seal=package/'seal.sha256'
    if db(sums.read_bytes()) != seal.read_text(encoding='ascii').strip().split()[0]: raise ValueError('seal does not match checksum index')
    for line in sums.read_text(encoding='ascii').splitlines():
        if not line.strip(): continue
        expected,name=line.split(None,1); name=name.strip().lstrip('*')
        if Path(name).name!=name: raise ValueError('nonportable checksum name')
        if db((package/name).read_bytes())!=expected: raise ValueError('checksum mismatch: '+name)
    summary=json.loads((package/'summary.json').read_text(encoding='utf-8'))
    if summary['exactPrHead']!=HEAD or summary['exactPrTree']!=TREE: raise ValueError('exact product pin mismatch')
    cellfile=inputs/'candidate-free-cells.jsonl'; ctxfile=inputs/'source-contexts.jsonl'
    input_hashes={'candidate-free-cells.jsonl':db(cellfile.read_bytes()),'source-contexts.jsonl':db(ctxfile.read_bytes())}
    if summary['inputSha256']!=input_hashes: raise ValueError('candidate-free input hash mismatch')
    cells=readj(cellfile); contexts=readj(ctxfile); reviews=readj(package/'review.jsonl')
    visible_context={x['sourceId']:x for x in contexts if not x.get('callerless',False)}
    if len(cells)!=240 or len(reviews)!=240: raise ValueError('record count mismatch')
    counts=Counter(); callerless=0
    for cell,rec in zip(cells,reviews):
        for key in ('position','locale','sourceSha256','currentTargetSha256','callerContextSha256'):
            if rec.get(key)!=cell.get(key): raise ValueError(f'cell pin mismatch {cell.get("position")}/{cell.get("locale")}/{key}')
        if bool(rec.get('callerless'))!=bool(cell.get('callerless')): raise ValueError('callerless mismatch')
        decision=rec.get('decision')
        if decision not in ('accept','correction','refinement','hold'): raise ValueError('unknown decision')
        counts[decision]+=1
        if decision in ('correction','refinement') and not rec.get('replacementText'): raise ValueError('proposal lacks text')
        if decision in ('accept','hold') and rec.get('replacementText') is not None: raise ValueError('unexpected replacement')
        if cell.get('callerless'):
            callerless+=1
            if decision!='hold' or rec.get('callerHashes')!=[]: raise ValueError('callerless cell not hash-only hold')
            if any(k in rec for k in ('sourceId','sourceText','currentTargetText','integrityChecks','replacementIntegrityChecks')): raise ValueError('callerless text leaked')
            if rec.get('callerHashesSha256')!=dobj([]): raise ValueError('empty caller hash digest mismatch')
            if rec.get('bindingSha256')!=binding(rec['position'],rec['locale'],rec['sourceSha256'],rec['currentTargetSha256'],rec['callerContextSha256'],rec['callerHashesSha256']): raise ValueError('callerless binding mismatch')
            continue
        source,target=cell['source'],cell['currentTarget']
        if dt(source)!=cell['sourceSha256'] or dt(target)!=cell['currentTargetSha256']: raise ValueError('source/target digest mismatch')
        if rec.get('sourceId')!=cell['sourceId'] or rec.get('sourceText')!=source or rec.get('currentTargetText')!=target: raise ValueError('visible text mismatch')
        ctx=visible_context.get(cell['sourceId'])
        if not ctx or ctx.get('head')!=HEAD or ctx.get('contextSha256')!=cell['callerContextSha256']: raise ValueError('caller-context binding mismatch')
        ch=refs(ctx); chs=dobj(ch)
        if rec.get('callerHashes')!=ch or rec.get('callerHashesSha256')!=chs: raise ValueError('caller ref mismatch')
        if rec.get('bindingSha256')!=binding(rec['position'],rec['locale'],rec['sourceSha256'],rec['currentTargetSha256'],rec['callerContextSha256'],chs): raise ValueError('visible binding mismatch')
        checks=rec.get('integrityChecks') or {}
        if not all(checks.get(k,{}).get('match') is True for k in ('placeholders','numbers','markupTags','protectedLiterals')): raise ValueError('current integrity mismatch')
        if decision in ('correction','refinement'):
            rc=rec.get('replacementIntegrityChecks') or {}
            if not all(rc.get(k,{}).get('match') is True for k in ('placeholders','numbers','markupTags','protectedLiterals')): raise ValueError('replacement integrity mismatch')
            if dt(rec['replacementText'])==dt(target): raise ValueError('proposal is an exact no-op')
    if callerless!=48 or counts!=Counter({'hold':48,'accept':188,'correction':4}): raise ValueError(f'count mismatch: {counts}, callerless={callerless}')
    if summary['decisions']!=dict(counts): raise ValueError('summary decision count mismatch')
    if summary['qualifiedNativeSpeakerApprovalClaimed'] is not False: raise ValueError('unsupported approval claim')
    print(json.dumps({'result':'PASS','records':len(reviews),'visible':len(reviews)-callerless,'callerlessHashOnlyHolds':callerless,'decisions':dict(counts),'exactPrHead':HEAD,'exactPrTree':TREE},ensure_ascii=False,sort_keys=True))

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,default=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w705-724-20261105/candidate-free/input'));p.add_argument('--package',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args()
    try: verify(a.package.resolve(),a.inputs.resolve())
    except Exception as e: print('VERIFY FAILED: '+str(e),file=sys.stderr);return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
