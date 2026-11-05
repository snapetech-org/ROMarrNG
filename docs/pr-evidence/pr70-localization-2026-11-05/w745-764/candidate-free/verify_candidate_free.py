#!/usr/bin/env python3
"""Verify sealed candidate-free ROMarrNG PR #70 W745-W764 evidence."""
import argparse,collections,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent; INPUT=ROOT/'input'; REPO=pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='68c5c9d4ad13ad5d02b9c455f429d8a5149d363d'; TREE='524db27557a65d64343b15c9983f6ac2f92f90c4'; PREV=REPO/'docs/pr-evidence/pr70-localization-2026-11-05/w725-744'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def fail(x): print('FAIL:',x); sys.exit(1)
def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def rj(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def sums(root):
    root=pathlib.Path(root); out={}
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); n=n.removeprefix('./'); p=(root/n).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=h or n in out: fail('checksum '+n)
        out[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS.txt'}
    if set(out)!=actual: fail(f'checksum coverage {root}: missing={sorted(set(out)-actual)} unlisted={sorted(actual-set(out))}')
    return out
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=pathlib.Path,default=REPO); repo=ap.parse_args().repo.resolve()
    if repo!=REPO: fail('worktree path')
    outer=sums(ROOT); inner=sums(INPUT); sums(PREV); sums(PREV/'candidate-free'); sums(PREV/'candidate-free/input')
    m=rj(INPUT/'manifest.json'); s=rj(INPUT/'manifest.json')
    if (s.get('head'),s.get('tree'),s.get('window'),s.get('cellCount'))!=(HEAD,TREE,'W745-W764',240): fail('manifest exact pin/window')
    if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'): fail('worktree pin/clean')
    prior=rj(PREV/'candidate-free/input/manifest.json'); app=rj(PREV/'application/readback.json')
    if (prior.get('head'),prior.get('tree'),prior.get('window'))!=('c3f92c45b4b4f8d79a8caa99417f9970ebc42a26','3f835643e4f557999d533c3e832fc92036d4b01a','W725-W744'): fail('predecessor pin')
    lineage=rj(INPUT/'prior-window-lineage.json')
    if (lineage.get('previousCandidateFreeChecksumsVerified') is not True or lineage.get('previousProductReadbackVerified') is not True or lineage.get('currentHead')!=HEAD or lineage.get('currentTree')!=TREE): fail('prior lineage attestation')
    oldmanifest=prior; oldholds=rjl(PREV/'candidate-free/input/prior-hold-reattestation.jsonl'); oldcurr=rjl(PREV/'candidate-free/input/candidate-free-cells.jsonl')
    if (len(oldholds),len([x for x in oldcurr if x.get('callerless')]),len(rjl(PREV/'candidate-free/input/prior-applied-cell-reattestation.jsonl')))!=(952,12,132): fail('prior W725 chain counts')
    if (app.get('productCommit'),app.get('productTree'),app.get('changedCellCount'),app.get('catalogSha256After'))!=('19038831e63edd53e4aec62f072c6d2eda9245cd','34a5eb65caccaa79070895bbe0c49dc6bb4fec6f',5,rj(INPUT/'catalog-file-pins.json').get('catalogSha256')): fail('W725 application readback')
    cells=rjl(INPUT/'candidate-free-cells.jsonl'); selected=rjl(INPUT/'selected-sources.jsonl'); contexts=rjl(INPUT/'source-contexts.jsonl'); holds=rjl(INPUT/'prior-hold-reattestation.jsonl'); applied=rjl(INPUT/'prior-applied-cell-reattestation.jsonl'); sels=rjl(INPUT/'prior-selection-reattestation.jsonl')
    if (len(cells),len(selected),len(contexts),len(holds),len(applied),len(sels))!=(240,20,20,964,137,360): fail('cell/history coverage')
    if (len({(x['sourceId'],x['locale']) for x in holds}),len({(x['sourceId'],x['locale']) for x in applied}),len({x['sourceId'] for x in sels}))!=(964,137,360): fail('history duplicate keys')
    if not all(x.get('textOmitted') is True for x in holds+applied): fail('prior hash evidence text')
    if any(k in x for x in holds for k in ('source','sourceText','currentTarget','target','targetText','proposedTarget')): fail('hold text leak')
    key=lambda x:(x['catalogZeroBasedIndex'],x['locale']); cmap={key(x):x for x in cells}
    if len(cmap)!=240 or [(x['catalogZeroBasedIndex'],x['locale']) for x in cells]!=[(i,l) for i in range(745,765) for l in LOCALES]: fail('cell ordering')
    catalog=json.loads(subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:romarr/ui-labels.json'],text=False))['messages']; ids=list(catalog)
    if len(ids)!=1836: fail('catalog message count')
    callerless=[]; token_mismatch=collections.Counter()
    for row in cells:
        i,l=row['catalogZeroBasedIndex'],row['locale']; sid=row['sourceId']; msg=catalog[sid]
        if ids[i]!=sid or sha(msg['source'])!=row['sourceSha256'] or sha(msg['translations'][l])!=row['currentTargetSha256']: fail('current cell pin '+sid+'/'+l)
        if row.get('callerless'):
            callerless.append(row)
            if row.get('cellDisposition')!='hold-callerless-hash-only' or any(k in row for k in ('source','currentTarget','proposedTarget')) or row.get('sourceTextOmitted') is not True or row.get('currentTargetTextOmitted') is not True: fail('callerless text/decision leak')
        else:
            if row.get('source')!=msg['source'] or row.get('currentTarget')!=msg['translations'][l]: fail('caller-backed source/target text')
            if not all(row.get(k) for k in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')): token_mismatch['token']+=1
    if len({x['sourceId'] for x in callerless})!=2 or len(callerless)!=24 or sum(not x['callerless'] for x in cells)!=216: fail('callerless counts')
    ctx={x['sourceId']:x for x in contexts}
    if len(ctx)!=20: fail('caller context source count')
    for row in selected:
        sid=row['sourceId']; c=ctx[sid]
        if c.get('contextSha256')!=next(x['callerContextSha256'] for x in cells if x['sourceId']==sid) or c.get('head')!=HEAD or c.get('sourceSha256')!=row['sourceSha256']: fail('context binding '+sid)
        if c.get('callerless'):
            if 'source' in c or c.get('callers') not in (None,[]) or c.get('sourceTextOmitted') is not True: fail('callerless context text leak')
        else:
            if c.get('source')!=catalog[sid]['source'] or not c.get('callers'): fail('caller-backed context')
            for caller in c['callers']:
                raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:{caller["path"]}'])
                blob=git('rev-parse',f'{HEAD}:{caller["path"]}')
                if sha(raw)!=caller['fileSha256'] or blob!=caller['gitBlob']: fail('caller source file pin '+sid)
    for row in holds:
        sid,l=row['sourceId'],row['locale']; i=row['catalogZeroBasedIndex']; msg=catalog[sid]
        if ids[i]!=sid or sha(msg['source'])!=row['sourceSha256'] or sha(msg['translations'][l])!=row['currentTargetSha256'] or row['priorTargetSha256']!=row['currentTargetSha256']: fail('prior hold current hash '+sid+'/'+l)
    for row in applied:
        sid,l=row['sourceId'],row['locale']; msg=catalog[sid]
        if sha(msg['source'])!=row['sourceSha256'] or sha(msg['translations'][l])!=row['currentTargetSha256'] or row['priorSelectedTargetSha256']!=row['currentTargetSha256']: fail('prior applied current hash '+sid+'/'+l)
    windows=[]
    for path in INPUT.glob('prior-*-cell-hash-reattestation.jsonl'):
        rows=rjl(path)
        if len(rows)!=240: fail('prior readback count '+path.name)
        for row in rows:
            sid,l=row['sourceId'],row['locale']; msg=catalog[sid]
            if row.get('currentTargetSha256')!=sha(msg['translations'][l]) or row.get('priorTargetSha256')!=row.get('currentTargetSha256'): fail('prior readback hash '+row['priorWindow']+'/'+sid+'/'+l)
        windows.append(rows[0]['priorWindow'])
    current=rjl(INPUT/'w725-current-product-readback.jsonl')
    if len(windows)!=9 or len(current)!=240 or set(windows)!={'W565-W584','W585-W604','W605-W624','W625-W644','W645-W664','W665-W684','W685-W704','W705-W724','W725-W744'}: fail('full readback windows')
    if any(rj(INPUT/'candidate-free-token-summary.json').values()): fail('candidate-free token mismatch summary')
    if rj(INPUT/'catalog-file-pins.json').get('head')!=HEAD or rj(INPUT/'catalog-file-pins.json').get('tree')!=TREE: fail('catalog pins')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'window':'W745-W764','cells':240,'callerBackedCells':216,'callerlessHashOnlyCells':24,'priorSelections':360,'priorActiveHolds':964,'newHolds':24,'resultingActiveHolds':988,'priorAppliedCells':137,'readbackWindows':9,'candidateFreeOnly':True,'worktreeClean':True},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
