#!/usr/bin/env python3
"""Verify exact W805-W824 product commit, cell readback, and hold lineage."""
import argparse, collections, hashlib, json, subprocess, sys
from pathlib import Path

INPUT_HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'; INPUT_TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
REVIEW_COMMIT='db188b5ded679803b055f2c09c0a97ab00e489cd'; PRODUCT_COMMIT='7bc17e5ae87e67dd69579c44591337b8e7e7927a'
CAT='romarr/ui-labels.json'; LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def rows(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def obj(repo,rev,path): return subprocess.check_output(['git','-C',str(repo),'show',f'{rev}:{path}'])
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); ap.add_argument('--evidence-root',type=Path,required=True); a=ap.parse_args()
    repo=a.repo.resolve(); evidence=a.evidence_root.resolve(); app=Path(__file__).resolve().parent
    pin=json.loads((app/'product-commit.json').read_text()); summary=json.loads((app/'readback.json').read_text()); pre=json.loads((app/'readback-before-commit.json').read_text())
    if (pin['productCommit'],pin['inputHead'],pin['inputTree'],pin['reviewEvidenceCommit'])!=(PRODUCT_COMMIT,INPUT_HEAD,INPUT_TREE,REVIEW_COMMIT): raise ValueError('product/input commit pin')
    if git(repo,'rev-parse',PRODUCT_COMMIT+'^{tree}')!=pin['productTree']: raise ValueError('product tree pin')
    if git(repo,'rev-parse',PRODUCT_COMMIT+'^')!=REVIEW_COMMIT: raise ValueError('product parent is not review evidence commit')
    if git(repo,'rev-parse',INPUT_HEAD+'^{tree}')!=INPUT_TREE: raise ValueError('input head tree pin')
    changed_paths=git(repo,'diff-tree','--no-commit-id','--name-only','-r',PRODUCT_COMMIT).splitlines()
    if changed_paths!=[CAT]: raise ValueError('product commit path set')
    if subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',PRODUCT_COMMIT,git(repo,'rev-parse','HEAD')],check=False).returncode: raise ValueError('product commit is not in current branch history')
    before_raw=obj(repo,INPUT_HEAD,CAT); after_raw=obj(repo,PRODUCT_COMMIT,CAT)
    if sha(after_raw)!=pin['catalogSha256'] or sha(after_raw)!=summary['catalogSha256After'] or sha(after_raw)!=pre['catalogSha256After']: raise ValueError('catalog object hash')
    before=json.loads(before_raw)['messages']; after=json.loads(after_raw)['messages']
    if list(before)!=list(after): raise ValueError('catalog key order changed')
    cf=rows(evidence/'candidate-free/input/candidate-free-cells.jsonl'); selected=rows(evidence/'root-adjudication/selected-targets.jsonl'); low=rows(evidence/'root-adjudication/low-confidence-language-holds.jsonl')
    hb1=evidence/'root-adjudication/prior-active-holds-hash-only.jsonl'; hb2=evidence/'root-adjudication/w785-current-window-holds-hash-only.jsonl'
    cross=evidence/'cross-review'
    if hb1.read_bytes()!=(cross/'prior-active-holds-hash-only.jsonl').read_bytes() or hb2.read_bytes()!=(cross/'current-window-holds-hash-only.jsonl').read_bytes(): raise ValueError('active hash-only hold copies')
    holds=rows(hb1)+rows(hb2); lowm={(r['sourceId'],r['locale']):r for r in low}; sm={(r['sourceId'],r['locale']):r for r in selected}
    readback=rows(app/'readback-240.jsonl'); hold_readback=rows(app/'active-hold-readback-1060.jsonl'); low_readback=rows(app/'low-confidence-hold-readback-10.jsonl')
    if (len(cf),len(selected),len(low),len(readback),len(holds),len(hold_readback),len(low_readback))!=(240,13,10,240,1060,1060,10): raise ValueError('readback row counts')
    cfm={(r['sourceId'],r['locale']):r for r in cf}; rbm={(r['sourceId'],r['locale']):r for r in readback}
    if len(cfm)!=240 or len(rbm)!=240: raise ValueError('duplicate readback rows')
    changed=[]; before_counts={loc:sum(bool(m.get('translations',{}).get(loc)) for m in before.values()) for loc in LOCALES}; after_counts={loc:sum(bool(m.get('translations',{}).get(loc)) for m in after.values()) for loc in LOCALES}
    if before_counts!=after_counts or any(after_counts[l]!=1836 for l in LOCALES): raise ValueError('locale translation completeness changed')
    for key,c in cfm.items():
        sid,loc=key; old=before[sid]['translations'][loc]; new=after[sid]['translations'][loc]; rb=rbm[key]
        if (sha(before[sid]['source']),sha(after[sid]['source']))!=(c['sourceSha256'],c['sourceSha256']): raise ValueError('source hash changed')
        if (rb['sourceId'],rb['sourceSha256'],rb['callerContextSha256'])!=(sid,c['sourceSha256'],c['callerContextSha256']): raise ValueError('readback identity/context')
        if (rb['beforeTargetSha256'],rb['afterTargetSha256'])!=(sha(old),sha(new)): raise ValueError('readback current/after target hashes')
        if key in sm:
            s=sm[key]
            if (old,new)!=(s['currentTarget'],s['rootTarget']) or sha(new)!=s['rootTargetSha256']: raise ValueError('selected target product value')
            if rb['applied'] is not True or rb['rootDisposition']!=s['rootDisposition'] or rb['expectedTargetSha256']!=s['rootTargetSha256']: raise ValueError('selected readback disposition')
            changed.append(key)
        else:
            if old!=new or rb['applied'] is not False or rb['expectedTargetSha256']!=c['currentTargetSha256']: raise ValueError('unselected product cell changed')
            if key in lowm:
                if rb['rootDisposition']!='hold-low-confidence-current' or sha(new)!=lowm[key]['currentTargetSha256']: raise ValueError('low-confidence current was not held')
            elif rb['rootDisposition']!='accept-current': raise ValueError('nonselected disposition')
    if len(changed)!=13 or set(changed)!=set(sm): raise ValueError('changed set does not equal root targets')
    holdrb={(r['sourceId'],r['locale']):r for r in hold_readback}; holdset={(r['sourceId'],r['locale']) for r in holds}
    if len(holdrb)!=1060 or set(holdrb)!=holdset: raise ValueError('active hold readback coverage')
    for h in holds:
        k=(h['sourceId'],h['locale']); row=holdrb[k]; source=before[k[0]]['source']; old=before[k[0]]['translations'][k[1]]; new=after[k[0]]['translations'][k[1]]
        if sha(source)!=h['sourceSha256'] or sha(old)!=h['currentTargetSha256'] or old!=new or row['afterTargetSha256']!=sha(new) or row['unchanged'] is not True or row.get('textOmitted') is not True: raise ValueError('active hash-only hold changed')
    lowrb={(r['sourceId'],r['locale']):r for r in low_readback}
    if set(lowrb)!=set(lowm): raise ValueError('low-confidence hold readback keys')
    for k,h in lowm.items():
        if before[k[0]]['translations'][k[1]]!=after[k[0]]['translations'][k[1]] or lowrb[k]['afterTargetSha256']!=h['currentTargetSha256'] or lowrb[k]['heldProposalSha256']!=h['heldProposalSha256']: raise ValueError('low-confidence target changed')
    if sha((app/'readback-240.jsonl').read_bytes())!=summary['readbackRowsSha256'] or sha((app/'active-hold-readback-1060.jsonl').read_bytes())!=summary['activeHoldReadbackSha256'] or sha((app/'low-confidence-hold-readback-10.jsonl').read_bytes())!=summary['lowConfidenceReadbackSha256']: raise ValueError('readback evidence hashes')
    if summary['changedCellCount']!=13 or summary['readbackCellCount']!=240 or summary['nativeSpeakerApproval'] is not False or summary['headedBrowserReviewPerformed'] is not False: raise ValueError('readback summary')
    print(json.dumps({'result':'PASS','inputHead':INPUT_HEAD,'reviewEvidenceCommit':REVIEW_COMMIT,'productCommit':PRODUCT_COMMIT,'productTree':pin['productTree'],'changedCatalog':CAT,'changedCells':len(changed),'readbackCells':len(readback),'lowConfidenceTargetsRetained':len(low),'activeHashOnlyHoldsUnchanged':len(holds),'allOtherReviewedCellsUnchanged':True,'catalogOrderPreserved':True,'localeCount':12,'nonemptyTranslationCountPerLocale':after_counts,'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False},ensure_ascii=False,indent=2))
if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'FAIL: {e}',file=sys.stderr); sys.exit(1)
