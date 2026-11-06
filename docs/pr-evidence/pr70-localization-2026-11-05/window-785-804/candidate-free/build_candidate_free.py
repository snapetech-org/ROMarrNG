#!/usr/bin/env python3
"""Build candidate-free ROMarrNG PR #70 W785-W804 evidence at a pinned head."""
import argparse, collections, hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

HEAD = 'bbbf84d0d83138a23143f6aa6075415ebcb36d3e'
TREE = 'fbf9ada4b4fd43a288ce498b24990312f0c32f22'
BRANCH = 'task/localization-translation-review-20261030'
WINDOW = 'W785-W804'
PREV_WINDOW = 'W765-W784'
PREV_HEAD = '9714d7cf69c687685b4f65cbd9627a56830bab85'
PREV_TREE = 'c8eb66573f10b2390a02df05033f5133425d5e41'
PRODUCT = '7e101cc0ea5580443d1b3903af084c23fe2134e5'
PRODUCT_TREE = 'd4b2661cd5105d6a18505a7302a13d9295eff39c'
CORRECTION = '2e6fb1d9f5bf5a5dc54f7fb62e562cc2a88d3fae'
CORRECTION_TREE = '6d09b309493b1d8701989c2c773f010709e63539'
REPO = Path(__file__).resolve().parents[5]
PREV = Path(__file__).resolve().parents[1].parent / 'window-765-784' / 'candidate-free'
PREV_INPUT = PREV / 'input'
PREV_APP = REPO / 'docs/pr-evidence/pr70-localization-2026-11-05/window-765-784/application/final-head-readback.jsonl'
PREV_APP_SUMMARY = PREV_APP.parent / 'application-summary.json'
START, END = 785, 804
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PLACEHOLDER = re.compile(r'\{[^{}]+\}')
TAG = re.compile(r'<[^>]+>')
NUMBER = re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED = ['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']

def sha(v):
    if isinstance(v, str): v = v.encode('utf-8')
    return hashlib.sha256(v).hexdigest()
def canon(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode('utf-8')
def rj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def wj(p,v): Path(p).write_text(json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')
def wjl(p,rows): Path(p).write_text(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',',':'))+'\n' for x in rows), encoding='utf-8')
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args], text=True).strip()
def sums(root):
    root=Path(root); names={}
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); n=n.removeprefix('./'); p=(root/n).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=h or n in names: raise SystemExit('FAIL checksum '+str(p))
        names[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS.txt'}
    if set(names)!=actual: raise SystemExit(f'FAIL checksum coverage {root}: missing={sorted(set(names)-actual)} unlisted={sorted(actual-set(names))}')
    return names
def protected(s):
    found=[]
    for lit in PROTECTED:
        ok=lit in s if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',s))
        if ok: found.append(lit)
    return sorted(set(found))
def tokens(s): return {'placeholders':PLACEHOLDER.findall(s),'markup':TAG.findall(s),'numbers':NUMBER.findall(s),'protectedLiterals':protected(s)}
def token_row(source,target):
    s,t=tokens(source),tokens(target)
    ph=collections.Counter(s['placeholders'])==collections.Counter(t['placeholders'])
    mk=collections.Counter(s['markup'])==collections.Counter(t['markup'])
    sn,tn=collections.Counter(s['numbers']),collections.Counter(t['numbers']); extra=list((tn-sn).elements())
    presentation=bool(re.search(r'\bzero\b',source,re.I) and not s['numbers'] and extra==['0'])
    numeric=not (sn-tn) and (not extra or presentation)
    missing=[x for x in s['protectedLiterals'] if x not in target]
    return {'sourcePlaceholderTokens':s['placeholders'],'currentPlaceholderTokens':t['placeholders'],'placeholderMultisetMatches':ph,'sourceMarkupTags':s['markup'],'currentMarkupTags':t['markup'],'markupMatches':mk,'sourceNumericTokens':s['numbers'],'currentNumericTokens':t['numbers'],'numericTokensPreserved':numeric,'numericPresentationEquivalent':presentation,'sourceProtectedLiterals':s['protectedLiterals'],'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing}
def prod_paths(commit):
    files=subprocess.check_output(['git','-C',str(REPO),'ls-tree','-r','--name-only',commit,'--','romarr'],text=True).splitlines()
    allowed={'.py','.js','.html','.jinja','.jinja2','.css','.ts','.tsx'}; out=[]
    for rel in files:
        p=Path(rel); parts=rel.lower().split('/')
        if p.suffix.lower() not in allowed or any(x in parts for x in ('test','tests','__pycache__')) or p.name.startswith('test_') or p.name.endswith('_test.py'): continue
        out.append(rel)
    return out
def file_tuple(rel,commit):
    raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{rel}'])
    return raw.decode('utf-8','replace'),raw,git('rev-parse',f'{commit}:{rel}')
def match_context(item,files,commit):
    source=item['source']; back=chr(96)
    variants=list(dict.fromkeys([json.dumps(source,ensure_ascii=False),repr(source),'"'+source+'"',"'"+source+"'",back+source+back]))
    callers=[]
    for rel,(text,data,blob) in files.items():
        hits={}
        for lit in variants:
            pos=0
            while True:
                i=text.find(lit,pos)
                if i<0: break
                hits.setdefault(i,'exact quoted source literal'); pos=i+max(1,len(lit))
        pos=0
        while True:
            i=text.find(item['sourceId'],pos)
            if i<0: break
            hits.setdefault(i,'exact source ID reference'); pos=i+len(item['sourceId'])
        for m in re.finditer(r'>[ \t]*'+re.escape(source)+r'[ \t]*<',text): hits.setdefault(m.start(),'exact HTML text node')
        lines=text.splitlines()
        for pos,kind in sorted(hits.items()):
            line=text.count('\n',0,pos)+1
            excerpt=[{'line':n,'text':lines[n-1]} for n in range(max(1,line-3),min(len(lines),line+3)+1)]
            line_text=lines[line-1] if line<=len(lines) else ''
            callers.append({'path':rel,'line':line,'lineText':line_text,'lineSha256':sha(line_text),'excerpt':excerpt,'excerptSha256':sha(canon(excerpt)),'fileSha256':sha(data),'gitBlob':blob,'matchKind':kind})
    callers.sort(key=lambda x:(x['path'],x['line'],x['matchKind']))
    core={'sourceId':item['sourceId'],'source':source,'sourceSha256':item['sourceSha256'],'head':commit,'searchMethod':'exact quoted source literal, source ID, or exact HTML text node in tracked production code under romarr; tests, docs, catalogs, and workflows excluded','productionFilesSearched':len(files),'exactMatchCount':len(callers),'callerless':not callers,'callers':callers}
    return {**core,'contextSha256':sha(canon(core))}
def safe_context(c):
    fields={k:c[k] for k in ('sourceId','sourceSha256','head','searchMethod','productionFilesSearched','exactMatchCount','callerless','contextSha256')}
    fields.update({'sourceTextOmitted':True,'callerTextOmitted':True,'callers':[]} if c['callerless'] else {'source':c['source'],'callers':c['callers']})
    return fields
def live_attestation():
    pr=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/ROMarrNG/pulls/70'],cwd=REPO,text=True))
    commit=json.loads(subprocess.check_output(['gh','api',f'repos/snapetech-org/ROMarrNG/commits/{HEAD}'],cwd=REPO,text=True))
    raw=git('ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head','refs/heads/main')
    refs={z.split('\t')[1]:z.split('\t')[0] for z in raw.splitlines() if z.strip()}
    body=pr.get('body') or ''
    obj={'attestedAtUtc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'repository':'snapetech-org/ROMarrNG','pullRequest':70,'state':pr['state'].upper(),'draft':bool(pr['draft']),'merged':bool(pr['merged']),'headRefName':pr['head']['ref'],'head':pr['head']['sha'],'tree':git('rev-parse',f'{HEAD}^{{tree}}'),'apiCommitTree':commit['commit']['tree']['sha'],'branchRefOid':refs.get('refs/heads/'+BRANCH),'pullRefOid':refs.get('refs/pull/70/head'),'baseRefName':pr['base']['ref'],'baseApiSha':pr['base']['sha'],'baseLiveRefOid':refs.get('refs/heads/main'),'bodySha256':sha(body),'bodyBytes':len(body.encode()),'checksRerun':False}
    want=('OPEN',True,False,BRANCH,HEAD,TREE,TREE,HEAD,HEAD,'main')
    got=(obj['state'],obj['draft'],obj['merged'],obj['headRefName'],obj['head'],obj['tree'],obj['apiCommitTree'],obj['branchRefOid'],obj['pullRefOid'],obj['baseRefName'])
    if want!=got: raise SystemExit('FAIL live PR pin '+repr(got))
    return obj

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); repo=ap.parse_args().repo.resolve()
    if repo!=REPO: raise SystemExit('FAIL wrong worktree')
    out=Path(__file__).resolve().parent; inp=out/'input'
    if any(inp.iterdir()): raise SystemExit('FAIL input directory is not empty')
    if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'): raise SystemExit('FAIL exact head/tree or dirty worktree')
    # Verify predecessor candidate-free artifacts only. No review proposal packet is consulted.
    sums(PREV); sums(PREV_INPUT)
    pm=rj(PREV_INPUT/'manifest.json')
    if (pm.get('head'),pm.get('tree'),pm.get('window'),pm.get('cellCount'),pm.get('resultingActiveHashOnlyHolds'))!=(PREV_HEAD,PREV_TREE,PREV_WINDOW,240,1012): raise SystemExit('FAIL predecessor candidate-free manifest')
    prev_cells=rjl(PREV_INPUT/'candidate-free-cells.jsonl'); old_holds=rjl(PREV_INPUT/'prior-hold-reattestation.jsonl')
    prev_selected=rjl(PREV_INPUT/'selected-sources.jsonl'); old_selections=rjl(PREV_INPUT/'prior-selection-reattestation.jsonl'); old_applied=rjl(PREV_INPUT/'prior-applied-cell-reattestation.jsonl')
    if (len(prev_cells),len(old_holds),len([r for r in prev_cells if r.get('callerless')]),len(prev_selected),len(old_selections),len(old_applied))!=(240,988,24,20,380,144): raise SystemExit('FAIL predecessor row counts')
    if any(k in r for r in prev_cells for k in ('proposedTarget','reviewDecision','decision')): raise SystemExit('FAIL predecessor candidate-free includes decisions')
    app_summary=rj(PREV_APP_SUMMARY); prev_app=rjl(PREV_APP)
    if (app_summary.get('result'),app_summary.get('window'),app_summary.get('inputHead'),app_summary.get('inputTree'),app_summary.get('productCommit'),app_summary.get('productTree'),app_summary.get('rootCells'),app_summary.get('readbackCells'),app_summary.get('changedCatalogCells'))!=('PASS',PREV_WINDOW,PREV_HEAD,PREV_TREE,PRODUCT,PRODUCT_TREE,240,240,10): raise SystemExit('FAIL predecessor application readback summary')
    if len(prev_app)!=240 or git('rev-parse',PRODUCT+'^{tree}')!=PRODUCT_TREE or git('rev-parse',CORRECTION+'^{tree}')!=CORRECTION_TREE or subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',PRODUCT,HEAD],check=False).returncode or subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',CORRECTION,HEAD],check=False).returncode: raise SystemExit('FAIL predecessor product/correction ancestry')
    before=live_attestation()
    catalog_path='romarr/ui-labels.json'; registry_path='romarr/ui-source-messages.json'; snapshot_path='romarr/ui-source-snapshot.json'
    catalog_raw=(repo/catalog_path).read_bytes(); catalog=json.loads(catalog_raw); msgs=catalog['messages']; ids=list(msgs)
    if len(msgs)!=1836: raise SystemExit('FAIL catalog message count')
    prev_order=rjl(PREV_INPUT/'catalog-key-order.jsonl')
    if len(prev_order)!=len(ids) or any(r['sourceId']!=sid for r,sid in zip(prev_order,ids)): raise SystemExit('FAIL catalog key-order continuity')
    product_catalog=json.loads(subprocess.check_output(['git','-C',str(REPO),'show',f'{PRODUCT}:{catalog_path}']))['messages']
    correction_catalog=json.loads(subprocess.check_output(['git','-C',str(REPO),'show',f'{CORRECTION}:{catalog_path}']))['messages']
    if subprocess.run(['git','-C',str(REPO),'diff','--quiet',CORRECTION,HEAD,'--',catalog_path],check=False).returncode: raise SystemExit('FAIL catalog changed after recorded correction commit')
    correction_deltas=[]
    for sid,base_msg in product_catalog.items():
        for loc,base_target in base_msg['translations'].items():
            current_target=msgs[sid]['translations'][loc]; fixed_target=correction_catalog[sid]['translations'][loc]
            if base_target!=current_target:
                if fixed_target!=current_target: raise SystemExit('FAIL post-product correction catalog delta '+sid+'/'+loc)
                correction_deltas.append({'sourceId':sid,'locale':loc,'productTargetSha256':sha(base_target),'currentTargetSha256':sha(current_target)})
    prev_selected_ids={r['sourceId'] for r in prev_selected}
    if len(correction_deltas)!=20 or any(r['sourceId'] not in prev_selected_ids for r in correction_deltas): raise SystemExit('FAIL exact post-product correction cell set')
    correction_keys={(r['sourceId'],r['locale']):r for r in correction_deltas}
    registry_raw=(repo/registry_path).read_bytes(); regdoc=rj(repo/registry_path); regrows=regdoc['messages']; registry={r['id']:r for r in regrows}
    if len(registry)!=len(regrows): raise SystemExit('FAIL duplicate source registry IDs')
    snapshot=rj(repo/snapshot_path)
    if any(snapshot.get(r['id'])!=r['sourceHash'] for r in regrows): raise SystemExit('FAIL source registry/snapshot hash')
    active_rank={sid:i for i,sid in enumerate(sorted(registry),1)}
    cat_order_sha=sha('\n'.join(ids)+'\n'); id_order_sha=sha('\n'.join(sorted(registry))+'\n')
    # Reattest the predecessor selections by exact catalog position and source hash.
    selections=[]; seen=set()
    for row in old_selections+prev_selected:
        sid=row['sourceId']; idx=row.get('catalogZeroBasedIndex',row.get('position')); source=msgs.get(sid,{}).get('source'); h=sha(source) if isinstance(source,str) else None
        want=row.get('currentSourceSha256',row.get('sourceSha256',row.get('priorSourceSha256')))
        if sid in seen or idx is None or idx>=len(ids) or ids[idx]!=sid or h!=want or msgs[sid].get('sourceHash')!=h: raise SystemExit('FAIL prior selection continuity '+sid)
        if sid in registry and registry[sid].get('sourceHash')!=h: raise SystemExit('FAIL prior registry hash '+sid)
        seen.add(sid); selections.append({'priorWindow':row.get('priorWindow',PREV_WINDOW),'catalogZeroBasedIndex':idx,'sourceId':sid,'priorSourceSha256':want,'currentSourceSha256':h,'selectionPositionMatches':True,'sourceHashMatches':True,'registryMembershipAndHashMatch':sid in registry,'priorSelectionEvidenceSha256':row.get('priorSelectionEvidenceSha256',sha(canon(row))),'reattestedAtHead':HEAD})
    if len(selections)!=400: raise SystemExit('FAIL accumulated selection total')
    # Prior active holds are represented by hashes only, including W765 callerless cells.
    hold_rows=[]
    for row in old_holds:
        sid,loc=row['sourceId'],row['locale']; idx=ids.index(sid); msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc]); prior=row.get('priorTargetSha256',row.get('currentTargetSha256'))
        if sh!=row['sourceSha256'] or th!=prior or row.get('catalogZeroBasedIndex') not in (None,idx): raise SystemExit('FAIL prior held cell '+sid+'/'+loc)
        if any(k in row for k in ('source','sourceText','currentTarget','target','targetText','proposedTarget')): raise SystemExit('FAIL prior hold text leak')
        hold_rows.append({'priorWindow':row['window'],'priorPosition':row.get('priorPosition',row.get('position')),'catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'priorTargetSha256':prior,'currentTargetSha256':th,'selectionPositionMatches':True,'targetUnchanged':True,'priorHoldEvidenceSha256':row.get('priorHoldEvidenceSha256',sha(canon(row))),'textOmitted':True,'reattestedAtHead':HEAD})
    prev_callerless=[r for r in prev_cells if r.get('callerless')]
    for row in prev_callerless:
        sid,loc=row['sourceId'],row['locale']; idx=ids.index(sid); msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc])
        if row.get('sourceTextOmitted') is not True or row.get('currentTargetTextOmitted') is not True or idx!=row.get('catalogZeroBasedIndex') or row.get('sourceSha256')!=sh or row.get('currentTargetSha256')!=th: raise SystemExit('FAIL W765 hash-only hold continuity '+sid+'/'+loc)
        hold_rows.append({'priorWindow':PREV_WINDOW,'priorPosition':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'priorTargetSha256':th,'currentTargetSha256':th,'selectionPositionMatches':True,'targetUnchanged':True,'callerlessAtPriorWindow':True,'callerContextSha256':row['callerContextSha256'],'priorHoldEvidenceSha256':sha(canon(row)),'textOmitted':True,'reattestedAtHead':HEAD})
    if len(hold_rows)!=1012 or len({(r['sourceId'],r['locale']) for r in hold_rows})!=1012: raise SystemExit('FAIL active prior hold count/uniqueness')
    # Reattest source/caller hashes for every source that has an active prior hold; text is not emitted.
    production={p:file_tuple(p,HEAD) for p in prod_paths(HEAD)}
    hold_contexts=[]
    for sid in sorted({r['sourceId'] for r in hold_rows}):
        src=msgs[sid]['source']; ctx=match_context({'sourceId':sid,'source':src,'sourceSha256':sha(src)},production,HEAD)
        hold_contexts.append({'sourceId':sid,'sourceSha256':sha(src),'currentCallerless':ctx['callerless'],'exactMatchCount':ctx['exactMatchCount'],'callerContextSha256':ctx['contextSha256'],'heldCellCount':sum(r['sourceId']==sid for r in hold_rows),'sourceTextOmitted':True,'callerTextOmitted':True,'reattestedAtHead':HEAD})
    # Reattest previous selected product cells without carrying target text forward.
    applied=[]
    for row in old_applied:
        sid,loc=row['sourceId'],row['locale']; msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc]); want=row.get('priorSelectedTargetSha256',row.get('currentTargetSha256'))
        if sh!=row['sourceSha256'] or th!=want: raise SystemExit('FAIL old applied target '+sid+'/'+loc)
        applied.append({'priorWindow':row['priorWindow'],'catalogZeroBasedIndex':ids.index(sid),'sourceId':sid,'sourceSha256':sh,'locale':loc,'priorSelectedTargetSha256':want,'currentTargetSha256':th,'targetUnchanged':True,'applicationCommit':row.get('applicationCommit'),'priorAppliedEvidenceSha256':row.get('priorAppliedEvidenceSha256',sha(canon(row))),'textOmitted':True,'reattestedAtHead':HEAD})
    prev_cell_map={(r['sourceId'],r['locale']):r for r in prev_cells}
    current_w765=[]; w765_applied=[]; correction_rows=[]
    for row in prev_app:
        sid,loc=row['sourceId'],row['locale']; key=(sid,loc); prior=prev_cell_map.get(key)
        if prior is None: raise SystemExit('FAIL W765 application cell not in predecessor input '+sid+'/'+loc)
        idx=ids.index(sid); msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc])
        key=(sid,loc); corrected=key in correction_keys
        product_target=product_catalog[sid]['translations'][loc]
        callerless=bool(row.get('callerless'))
        context_hash=row.get('callerContextSha256',prior.get('callerContextSha256'))
        if idx!=row['position'] or row['beforeSha256']!=prior['currentTargetSha256'] or context_hash!=prior['callerContextSha256'] or sha(product_target)!=row['afterSha256'] or sha(correction_catalog[sid]['translations'][loc])!=th or corrected!=(row['afterSha256']!=th): raise SystemExit('FAIL W765 applied readback '+sid+'/'+loc)
        if callerless and (not prior.get('callerless') or row['beforeSha256']!=row['afterSha256']): raise SystemExit('FAIL W765 callerless product readback')
        rb={'priorWindow':PREV_WINDOW,'catalogZeroBasedIndex':idx,'oneBasedPosition':idx+1,'sourceId':sid,'sourceSha256':sh,'locale':loc,'beforeTargetSha256':row['beforeSha256'],'productTargetSha256':row['afterSha256'],'priorTargetSha256':th,'currentTargetSha256':th,'callerContextSha256':context_hash,'matchesPriorProductReadback':True,'targetUnchangedSinceProduct':not corrected,'followupCorrectionCommit':CORRECTION if corrected else None,'callerlessHeld':callerless,'textOmitted':True,'applicationCommit':PRODUCT,'reattestedAtHead':HEAD}
        current_w765.append(rb)
        if row['beforeSha256']!=row['afterSha256']:
            rec={'priorWindow':PREV_WINDOW,'catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'beforeTargetSha256':row['beforeSha256'],'priorSelectedTargetSha256':row['afterSha256'],'currentTargetSha256':th,'targetUnchanged':not corrected,'followupCorrectionCommit':CORRECTION if corrected else None,'applicationCommit':PRODUCT,'priorAppliedEvidenceSha256':sha(canon({k:v for k,v in row.items() if k in ('position','locale','sourceId','beforeSha256','afterSha256','callerContextSha256')})),'textOmitted':True,'reattestedAtHead':HEAD}
            w765_applied.append(rec); applied.append(rec)
        if corrected:
            correction_rows.append({'window':PREV_WINDOW,'catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'productTargetSha256':row['afterSha256'],'currentTargetSha256':th,'correctionCommit':CORRECTION,'correctionTree':CORRECTION_TREE,'targetMatchesCorrectionCommit':True,'textOmitted':True,'reattestedAtHead':HEAD})
    for r in correction_deltas:
        key=(r['sourceId'],r['locale'])
        if key not in prev_cell_map: raise SystemExit('FAIL correction cell outside W765 input')
        if key not in {(x['sourceId'],x['locale']) for x in correction_rows}:
            idx=ids.index(r['sourceId']); msg=msgs[r['sourceId']]
            correction_rows.append({'window':PREV_WINDOW,'catalogZeroBasedIndex':idx,'sourceId':r['sourceId'],'sourceSha256':sha(msg['source']),'locale':r['locale'],'productTargetSha256':r['productTargetSha256'],'currentTargetSha256':r['currentTargetSha256'],'correctionCommit':CORRECTION,'correctionTree':CORRECTION_TREE,'targetMatchesCorrectionCommit':True,'textOmitted':True,'reattestedAtHead':HEAD})
    if len(current_w765)!=240 or len(w765_applied)!=10 or len(applied)!=154 or len(correction_rows)!=20: raise SystemExit('FAIL W765 product readback/apply count')
    # Carry ten full earlier product readbacks and add W765; all are hash-only.
    readbacks={}
    for p in sorted(PREV_INPUT.glob('prior-*-cell-hash-reattestation.jsonl')):
        rows=rjl(p)
        if len(rows)!=240: raise SystemExit('FAIL prior readback count '+p.name)
        label=rows[0]['priorWindow']; now=[]
        for row in rows:
            sid,loc=row['sourceId'],row['locale']; idx=ids.index(sid); msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc]); old=next((row[k] for k in ('priorTargetSha256','currentTargetSha256','actualTargetSha256') if k in row),None)
            if old!=th or row.get('catalogZeroBasedIndex',row.get('position'))!=idx or row.get('sourceSha256') not in (None,sh): raise SystemExit('FAIL prior readback '+label+' '+sid+'/'+loc)
            now.append({'priorWindow':label,'catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'priorTargetSha256':old,'currentTargetSha256':th,'targetUnchanged':True,'textOmitted':True,'reattestedAtHead':HEAD})
        if len({(x['sourceId'],x['locale']) for x in now})!=240: raise SystemExit('FAIL duplicate prior readback '+label)
        readbacks[label]=now
    if len(readbacks)!=10 or PREV_WINDOW in readbacks: raise SystemExit('FAIL prior complete readback set')
    readbacks[PREV_WINDOW]=current_w765
    if len(readbacks)!=11: raise SystemExit('FAIL readback window count')
    # Current source and exact caller inventory for the next twenty catalog positions.
    selected=[]; contexts=[]; cells=[]; mismatch=collections.Counter()
    for idx in range(START,END+1):
        sid=ids[idx]; msg=msgs[sid]; src=msg['source']; sh=sha(src)
        if msg.get('sourceHash')!=sh or sid in registry and registry[sid].get('sourceHash')!=sh: raise SystemExit('FAIL selected catalog/registry hash '+sid)
        selected.append({'position':idx,'catalogZeroBasedIndex':idx,'catalogOneBasedPosition':idx+1,'sourceId':sid,'sourceSha256':sh,'activeSourceRank':active_rank.get(sid),'activeSourceRegistry':sid in registry,'registryLocations':registry.get(sid,{}).get('locations',[]),'source':src})
    old_boundary=[r for r in rjl(PREV_INPUT/'selection-boundary.jsonl') if r.get('catalogZeroBasedIndex')==START and r.get('role')=='catalog-after-selected-end']
    if len(old_boundary)!=1 or (old_boundary[0]['sourceId'],old_boundary[0]['sourceSha256'])!=(selected[0]['sourceId'],selected[0]['sourceSha256']): raise SystemExit('FAIL W785 queue boundary')
    if len({r['sourceId'] for r in selected})!=20 or {r['sourceId'] for r in selected}&seen: raise SystemExit('FAIL selected source overlap')
    for item in selected:
        sid=item['sourceId']; src=item['source']; ctx=match_context({'sourceId':sid,'source':src,'sourceSha256':item['sourceSha256']},production,HEAD); contexts.append(ctx)
        for loc in LOCALES:
            target=msgs[sid].get('translations',{}).get(loc)
            if not isinstance(target,str) or not target: mismatch['missingTarget']+=1; target=''
            cell={'window':WINDOW,'position':item['position'],'catalogZeroBasedIndex':item['catalogZeroBasedIndex'],'catalogOneBasedPosition':item['catalogOneBasedPosition'],'sourceId':sid,'sourceSha256':item['sourceSha256'],'locale':loc,'callerContextSha256':ctx['contextSha256'],'literalCallerCount':ctx['exactMatchCount'],'callerless':ctx['callerless'],'candidateFree':True,'currentTargetSha256':sha(target)}
            if ctx['callerless']:
                cell.update({'cellDisposition':'hold-callerless-hash-only','sourceTextOmitted':True,'currentTargetTextOmitted':True})
            else:
                tok=token_row(src,target)
                mismatch['placeholder']+=not tok['placeholderMultisetMatches']; mismatch['markup']+=not tok['markupMatches']; mismatch['numeric']+=not tok['numericTokensPreserved']; mismatch['numericPresentationDifferences']+=tok['numericPresentationEquivalent']; mismatch['protectedLiteral']+=not tok['protectedLiteralsPreserved']
                cell.update({'source':src,'currentTarget':target,**tok,'catalogTranslationHash':msg.get('translationHashes',{}).get(loc),'translationStatus':msg.get('translationStatus',{}).get(loc)})
            cells.append(cell)
    callerless=sum(c['callerless'] for c in contexts); holdcells=12*callerless
    if len(cells)!=240 or len({(r['sourceId'],r['locale']) for r in cells})!=240: raise SystemExit('FAIL cell count')
    after=live_attestation(); stable=('state','draft','merged','headRefName','head','tree','apiCommitTree','branchRefOid','pullRefOid','baseRefName','baseApiSha','baseLiveRefOid','bodySha256','bodyBytes')
    if any(before[k]!=after[k] for k in stable): raise SystemExit('FAIL live PR changed during extraction')
    if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'): raise SystemExit('FAIL worktree changed during extraction')
    wj(inp/'PR-attestation-before.json',before); wj(inp/'PR-attestation-after.json',after)
    wjl(inp/'catalog-key-order.jsonl',[{'catalogZeroBasedIndex':i,'sourceId':sid,'sourceSha256':sha(msgs[sid]['source'])} for i,sid in enumerate(ids)])
    wj(inp/'catalog-file-pins.json',{'head':HEAD,'tree':TREE,'catalogPath':catalog_path,'catalogSha256':sha(catalog_raw),'catalogGitBlob':git('rev-parse',f'{HEAD}:{catalog_path}'),'catalogMessageCount':len(msgs),'catalogKeyOrderSha256':cat_order_sha,'sourceQueuePath':registry_path,'sourceQueueSha256':sha(registry_raw),'sourceSnapshotPath':snapshot_path,'sourceSnapshotSha256':sha(canon(snapshot)),'activeUniqueSourceIds':len(registry),'sourceIdOrderSha256':id_order_sha})
    source_pins={'head':HEAD,'tree':TREE,'files':[]}; caller_files=set(production)
    for rel in sorted(caller_files|{catalog_path,registry_path,snapshot_path}):
        raw=(repo/rel).read_bytes(); source_pins['files'].append({'path':rel,'fileSha256':sha(raw),'gitBlob':git('rev-parse',f'{HEAD}:{rel}'),'bytes':len(raw)})
    wj(inp/'source-file-pins.json',source_pins)
    redacted=[{k:v for k,v in row.items() if k not in ('source','translations','translation')} for row in regrows]
    wj(inp/'source-registry-redacted.json',{'path':registry_path,'sha256':sha(registry_raw),'snapshotPath':snapshot_path,'snapshotSha256':sha(canon(snapshot)),'activeSourceCount':len(registry),'messages':redacted})
    wj(inp/'source-snapshot-hashes.json',snapshot)
    safe_selected=[{k:v for k,v in row.items() if k!='source'}|({'source':row['source']} if not next(c for c in contexts if c['sourceId']==row['sourceId'])['callerless'] else {'sourceTextOmitted':True}) for row in selected]
    wjl(inp/'selected-sources.jsonl',safe_selected)
    wjl(inp/'selection-boundary.jsonl',[{'position':i,'catalogZeroBasedIndex':i,'sourceId':ids[i],'sourceSha256':sha(msgs[ids[i]]['source']),'role':role,'sourceTextOmitted':True} for i,role in ((784,'catalog-before-selected-start'),(785,'selected-start'),(804,'selected-end'),(805,'catalog-after-selected-end'))])
    wjl(inp/'source-contexts.jsonl',[safe_context(c) for c in contexts]); wjl(inp/'candidate-free-cells.jsonl',cells); wj(inp/'candidate-free-token-summary.json',dict(mismatch))
    wjl(inp/'prior-selection-reattestation.jsonl',selections); wj(inp/'prior-selection-reattestation-summary.json',{'count':len(selections),'allSelectionsMatchCurrentCatalog':True,'head':HEAD,'tree':TREE})
    wjl(inp/'prior-active-holds-hash-only.jsonl',hold_rows); wj(inp/'prior-hold-reattestation-summary.json',{'count':len(hold_rows),'windows':dict(collections.Counter(r['priorWindow'] for r in hold_rows)),'allTargetHashesMatch':True,'changedTargets':0,'textInHoldRows':False,'head':HEAD,'tree':TREE})
    wjl(inp/'prior-hold-context-reattestation.jsonl',hold_contexts)
    wjl(inp/'prior-applied-cell-reattestation.jsonl',applied); wj(inp/'prior-applied-cell-reattestation-summary.json',{'count':len(applied),'allFinalTargetHashesMatch':True,'changedTargets':0,'head':HEAD,'tree':TREE})
    for label,rows in readbacks.items(): wjl(inp/('prior-'+label.lower().replace('-','')+'-cell-hash-reattestation.jsonl'),rows)
    wjl(inp/'w765-current-product-readback-hash-only.jsonl',current_w765); wjl(inp/'w765-applied-target-reattestation.jsonl',w765_applied); wjl(inp/'w765-followup-correction-reattestation.jsonl',correction_rows)
    wj(inp/'prior-window-lineage.json',{'result':'PASS','currentHead':HEAD,'currentTree':TREE,'previousCandidateFreeHead':PREV_HEAD,'previousCandidateFreeTree':PREV_TREE,'previousWindow':PREV_WINDOW,'previousProductCommit':PRODUCT,'previousProductTree':PRODUCT_TREE,'followupCorrectionCommit':CORRECTION,'followupCorrectionTree':CORRECTION_TREE,'followupCorrectionTargetCount':len(correction_rows),'previousSelectionsReattested':len(selections),'previousHeldCellsReattested':len(hold_rows),'previousAppliedCellsReattested':len(applied),'priorFullReadbackWindows':{k:len(v) for k,v in readbacks.items()},'previousCallerlessSources':sum(1 for r in hold_contexts if r['sourceId'] in {x['sourceId'] for x in prev_callerless}),'priorHoldTextIncluded':False,'previousCandidateFreeChecksumsVerified':True,'previousProductReadbackVerified':True,'priorReviewRecommendationsRead':False,'previousManifestSha256':sha((PREV_INPUT/'manifest.json').read_bytes()),'previousInputChecksumListSha256':sha((PREV_INPUT/'SHA256SUMS.txt').read_bytes()),'previousOuterChecksumListSha256':sha((PREV/'SHA256SUMS.txt').read_bytes())})
    wj(inp/'selection.json',{'window':WINDOW,'selectionBasis':'catalog insertion order at exact pinned romarr/ui-labels.json indices 785 through 804 (zero-based)','positions':[START,END],'catalogOneBasedPositions':[START+1,END+1],'sourceCount':20,'localeCount':12,'cellCount':240,'localeOrder':LOCALES,'selectedSources':safe_selected})
    wj(inp/'prior-application-source-pin.json',{'sourceHead':PREV_HEAD,'sourceTree':PREV_TREE,'productCommit':PRODUCT,'productTree':PRODUCT_TREE,'followupCorrectionCommit':CORRECTION,'followupCorrectionTree':CORRECTION_TREE,'currentHead':HEAD,'currentTree':TREE,'productCommitAncestor':True,'correctionCommitAncestor':True,'productCatalogSha256':sha(subprocess.check_output(['git','-C',str(REPO),'show',f'{PRODUCT}:{catalog_path}'])),'correctionCatalogSha256':sha(subprocess.check_output(['git','-C',str(REPO),'show',f'{CORRECTION}:{catalog_path}'])),'currentCatalogSha256':sha(catalog_raw),'applicationReadbackPath':str(PREV_APP),'applicationReadbackSha256':sha(PREV_APP.read_bytes()),'applicationCellCount':len(prev_app),'applicationChangedCellCount':len(w765_applied),'followupCorrectionCellCount':len(correction_rows),'applicationCellHashesReattested':True})
    wj(inp/'input-verification.json',{'result':'PASS','host':'kspld0','worktree':str(REPO),'worktreeCleanAtBuild':True,'head':HEAD,'tree':TREE,'branch':BRANCH,'pullRequest':70,'livePROpenDraftUnmerged':True,'remoteBranchAndPullRefsMatchHead':True,'predecessorCandidateFreeChecksums':'PASS','predecessorHead':PREV_HEAD,'predecessorTree':PREV_TREE,'predecessorWindow':PREV_WINDOW,'nextBoundaryMatchesPredecessor':True,'catalogQueueBoundaryIndex':START})
    manifest={'artifact':'ROMarrNG PR #70 W785-W804 candidate-free exact-head input','repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':BRANCH,'head':HEAD,'tree':TREE,'window':WINDOW,'catalogSelectionZeroBased':[START,END],'catalogSelectionOneBased':[START+1,END+1],'sourceCount':20,'localeCount':12,'cellCount':len(cells),'callerBackedCells':len(cells)-holdcells,'callerlessSourceCount':callerless,'callerlessHashOnlyCells':holdcells,'directCallerReferences':sum(c['exactMatchCount'] for c in contexts),'productionCallerFilesSearched':len(production),'currentTokenMismatchCounts':dict(mismatch),'priorSelectionsReattested':len(selections),'priorActiveHoldsReattested':len(hold_rows),'newWindowHashOnlyHolds':holdcells,'resultingActiveHashOnlyHolds':len(hold_rows)+holdcells,'priorAppliedCellsReattested':len(applied),'priorProductCorrectionCellsReattested':len(correction_rows),'priorProductCorrectionCommit':CORRECTION,'priorFullReadbackWindowCount':len(readbacks),'previousProductCommit':PRODUCT,'previousProductTree':PRODUCT_TREE,'proposedTargetsIncluded':False,'reviewDecisionsIncluded':False,'repoEdited':False,'testsBuildsScansCiRun':False,'nextBoundary':{'continuationIndex':END+1,'oneBasedPosition':END+2,'sourceId':ids[END+1],'sourceSha256':sha(msgs[ids[END+1]]['source'])}}
    wj(inp/'manifest.json',manifest)
    (out/'README.md').write_text(f'''# ROMarrNG PR #70 W785–W804 candidate-free packet

Pinned to the open draft PR head `{HEAD}`, tree `{TREE}`, branch `{BRANCH}`. The packet selects zero-based catalog indices {START}–{END} (one-based positions {START+1}–{END+1}): 20 source keys and 240 cells across 12 locales.

It records {len(cells)-holdcells} caller-backed cells and {holdcells} callerless hash-only cells. Callerless source and target text is omitted. The packet reattests {len(selections)} previous source selections, {len(hold_rows)} active prior hash-only holds, {len(applied)} previously applied target hashes, and {len(readbacks)} complete 240-cell product readback windows. The resulting active hash-only hold count is {len(hold_rows)+holdcells}.

The W765–W784 product commit `{PRODUCT}` / tree `{PRODUCT_TREE}`, its {len(w765_applied)} changed target hashes, and {len(correction_rows)} later hash-only catalog corrections in `{CORRECTION}` / tree `{CORRECTION_TREE}` are reattested against this pinned catalog. The queue boundary agrees with the predecessor candidate-free packet. No translation proposal or decision is included, and no review recommendations were consulted.

No repository, catalog, PR, or workflow files were changed. No tests, builds, scans, or CI were run. Verify with `python3 verify_candidate_free.py --repo {REPO}`.
''',encoding='utf-8')
    inner=sorted(p for p in inp.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (inp/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(inp).as_posix()}\n' for p in inner),encoding='utf-8')
    outer=sorted(p for p in out.rglob('*') if p.is_file() and p!=out/'SHA256SUMS.txt')
    (out/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(out).as_posix()}\n' for p in outer),encoding='utf-8')
    print(json.dumps({'result':'BUILT','head':HEAD,'tree':TREE,'window':WINDOW,'cells':len(cells),'callerBackedCells':len(cells)-holdcells,'callerlessHashOnlyCells':holdcells,'priorActiveHoldsReattested':len(hold_rows),'resultingActiveHolds':len(hold_rows)+holdcells,'priorAppliedCellsReattested':len(applied),'priorProductCorrectionCellsReattested':len(correction_rows),'readbackWindows':len(readbacks),'nextBoundary':manifest['nextBoundary']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
