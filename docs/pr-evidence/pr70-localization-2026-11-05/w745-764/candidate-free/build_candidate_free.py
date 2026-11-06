#!/usr/bin/env python3
"""Build candidate-free ROMarrNG PR #70 W745-W764 input at the exact pinned head."""
import argparse, collections, hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

HEAD='68c5c9d4ad13ad5d02b9c455f429d8a5149d363d'; TREE='524db27557a65d64343b15c9983f6ac2f92f90c4'
BRANCH='task/localization-translation-review-20261030'; WINDOW='W745-W764'; PREV_WINDOW='W725-W744'
PREV_HEAD='c3f92c45b4b4f8d79a8caa99417f9970ebc42a26'; PREV_TREE='3f835643e4f557999d533c3e832fc92036d4b01a'
PRODUCT='19038831e63edd53e4aec62f072c6d2eda9245cd'; PRODUCT_TREE='34a5eb65caccaa79070895bbe0c49dc6bb4fec6f'
REPO=Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
PREV_ROOT=REPO/'docs/pr-evidence/pr70-localization-2026-11-05/w725-744'
PREV_CF=PREV_ROOT/'candidate-free'; PREV_INPUT=PREV_CF/'input'; PREV_APP=PREV_ROOT/'application/readback.json'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PLACEHOLDER=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']

def sha(v):
    if isinstance(v,str): v=v.encode('utf-8')
    return hashlib.sha256(v).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def rj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def wj(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def wjl(p,rows): Path(p).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in rows),encoding='utf-8')
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def verify_sums(root):
    root=Path(root); sums={}
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); n=n.removeprefix('./'); path=(root/n).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes())!=h: raise SystemExit('FAIL checksum '+str(path))
        if n in sums: raise SystemExit('FAIL duplicate checksum '+n)
        sums[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root/'SHA256SUMS.txt'}
    if set(sums)!=actual: raise SystemExit(f'FAIL checksum coverage {root}: unlisted={sorted(actual-set(sums))} missing={sorted(set(sums)-actual)}')
    return sums
def protected(s):
    found=[]
    for lit in PROTECTED:
        ok=lit in s if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',s))
        if ok: found.append(lit)
    return sorted(set(found))
def tokens(s): return {'placeholders':PLACEHOLDER.findall(s),'markup':TAG.findall(s),'numbers':NUMBER.findall(s),'protectedLiterals':protected(s)}
def token_rows(source,target):
    s,t=tokens(source),tokens(target); ph=collections.Counter(s['placeholders'])==collections.Counter(t['placeholders']); mk=collections.Counter(s['markup'])==collections.Counter(t['markup'])
    sn,tn=collections.Counter(s['numbers']),collections.Counter(t['numbers']); extra=list((tn-sn).elements()); presentation=bool(re.search(r'\bzero\b',source,re.I) and not s['numbers'] and extra==['0']); numeric=not (sn-tn) and (not extra or presentation)
    missing=[x for x in s['protectedLiterals'] if x not in target]
    return {'sourcePlaceholderTokens':s['placeholders'],'currentPlaceholderTokens':t['placeholders'],'placeholderMultisetMatches':ph,'sourceMarkupTags':s['markup'],'currentMarkupTags':t['markup'],'markupMatches':mk,'sourceNumericTokens':s['numbers'],'currentNumericTokens':t['numbers'],'numericTokensPreserved':numeric,'numericPresentationEquivalent':presentation,'sourceProtectedLiterals':s['protectedLiterals'],'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing}
def production_paths(commit):
    files=subprocess.check_output(['git','-C',str(REPO),'ls-tree','-r','--name-only',commit,'--','romarr'],text=True).splitlines(); allowed={'.py','.js','.html','.jinja','.jinja2','.css','.ts','.tsx'}; out=[]
    for rel in files:
        p=Path(rel); parts=rel.lower().split('/')
        if p.suffix.lower() not in allowed or any(x in parts for x in ('test','tests','__pycache__')) or p.name.startswith('test_') or p.name.endswith('_test.py'): continue
        out.append(rel)
    return out
def file_tuple(rel,commit):
    raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{rel}']); return raw.decode('utf-8','replace'),raw,git('rev-parse',f'{commit}:{rel}')
def match_context(item,files,commit):
    source=item['source']; back=chr(96); variants=list(dict.fromkeys([json.dumps(source,ensure_ascii=False),repr(source),'"'+source+'"',"'"+source+"'",back+source+back])); callers=[]
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
            line=text.count('\n',0,pos)+1; excerpt=[{'line':n,'text':lines[n-1]} for n in range(max(1,line-3),min(len(lines),line+3)+1)]; line_text=lines[line-1] if line<=len(lines) else ''
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
    raw=git('ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head','refs/heads/main'); refs={z.split('\t')[1]:z.split('\t')[0] for z in raw.splitlines() if z.strip()}
    body=pr.get('body') or ''; obj={'attestedAtUtc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'repository':'snapetech-org/ROMarrNG','pullRequest':70,'state':pr['state'].upper(),'draft':bool(pr['draft']),'merged':bool(pr['merged']),'headRefName':pr['head']['ref'],'head':pr['head']['sha'],'tree':git('rev-parse',f'{HEAD}^{{tree}}'),'apiCommitTree':commit['commit']['tree']['sha'],'branchRefOid':refs.get('refs/heads/'+BRANCH),'pullRefOid':refs.get('refs/pull/70/head'),'baseRefName':pr['base']['ref'],'baseApiSha':pr['base']['sha'],'baseLiveRefOid':refs.get('refs/heads/main'),'bodySha256':sha(body),'bodyBytes':len(body.encode()),'checksRerun':False}
    want=('OPEN',True,False,BRANCH,HEAD,TREE,TREE,HEAD,HEAD,'main'); got=(obj['state'],obj['draft'],obj['merged'],obj['headRefName'],obj['head'],obj['tree'],obj['apiCommitTree'],obj['branchRefOid'],obj['pullRefOid'],obj['baseRefName'])
    if want!=got: raise SystemExit('FAIL live PR pin '+repr(got))
    return obj
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); repo=ap.parse_args().repo.resolve()
    if repo!=REPO: raise SystemExit('FAIL wrong worktree')
    out=Path(__file__).resolve().parent; inp=out/'input'
    if any(p.is_file() for p in inp.iterdir()): raise SystemExit('FAIL input directory not empty')
    if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'): raise SystemExit('FAIL exact head/tree or dirty worktree')
    before=live_attestation()
    verify_sums(PREV_ROOT); verify_sums(PREV_CF); verify_sums(PREV_INPUT)
    pm=rj(PREV_INPUT/'manifest.json')
    if (pm.get('head'),pm.get('tree'),pm.get('window'),pm.get('priorSelectedSourceCount'),pm.get('priorHoldCellCount'),pm.get('priorAppliedSelectedCellCount'))!=(PREV_HEAD,PREV_TREE,PREV_WINDOW,340,952,132): raise SystemExit('FAIL W725 predecessor manifest')
    prior_selections=rjl(PREV_INPUT/'prior-selection-reattestation.jsonl'); prev_selected=rjl(PREV_INPUT/'selected-sources.jsonl'); prev_holds=rjl(PREV_INPUT/'prior-hold-reattestation.jsonl'); prev_applied=rjl(PREV_INPUT/'prior-applied-cell-reattestation.jsonl'); prev_cells=rjl(PREV_INPUT/'candidate-free-cells.jsonl')
    if (len(prior_selections),len(prev_selected),len(prev_holds),len(prev_applied),len(prev_cells))!=(340,20,952,132,240): raise SystemExit('FAIL W725 predecessor row counts')
    if any(any(k in row for k in ('proposedTarget','reviewDecision','decision')) for row in prev_cells): raise SystemExit('FAIL W725 candidate-free includes decisions')
    prior_app=rj(PREV_APP)
    if (prior_app.get('window'),prior_app.get('inputHead'),prior_app.get('inputTree'),prior_app.get('productCommit'),prior_app.get('productTree'),prior_app.get('changedCellCount'),prior_app.get('expectedChangedCellCount'))!=(PREV_WINDOW,PREV_HEAD,PREV_TREE,PRODUCT,PRODUCT_TREE,5,5): raise SystemExit('FAIL W725 product readback pin')
    if not prior_app.get('catalogKeyOrderPreserved') or not prior_app.get('allOtherCatalogCellsUnchanged') or not prior_app.get('all12DirectLocalesHave1836NonemptyMessages'): raise SystemExit('FAIL W725 product readback invariants')
    if git('rev-parse',PRODUCT+'^')!=PREV_HEAD or git('rev-parse',PRODUCT+'^{tree}')!=PRODUCT_TREE or subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',PRODUCT,HEAD],check=False).returncode: raise SystemExit('FAIL W725 product ancestry')
    changed=subprocess.check_output(['git','-C',str(REPO),'diff-tree','--no-commit-id','--name-only','-r',PRODUCT],text=True).splitlines()
    if changed!=['romarr/ui-labels.json'] or subprocess.run(['git','-C',str(REPO),'diff','--quiet',PRODUCT,HEAD,'--','romarr/ui-labels.json'],check=False).returncode: raise SystemExit('FAIL post-W725 catalog drift')
    catalog_path='romarr/ui-labels.json'; registry_path='romarr/ui-source-messages.json'; snapshot_path='romarr/ui-source-snapshot.json'
    catalog_raw=(repo/catalog_path).read_bytes(); catalog=json.loads(catalog_raw); msgs=catalog['messages']; ids=list(msgs)
    if len(msgs)!=1836: raise SystemExit('FAIL catalog count')
    old_order=rjl(PREV_INPUT/'catalog-key-order.jsonl')
    if len(old_order)!=len(ids) or any(row['sourceId']!=sid for row,sid in zip(old_order,ids)): raise SystemExit('FAIL catalog key-order continuity')
    registry_raw=(repo/registry_path).read_bytes(); regdoc=rj(repo/registry_path); regrows=regdoc['messages']; registry={r['id']:r for r in regrows}
    if len(registry)!=len(regrows): raise SystemExit('FAIL duplicate source registry IDs')
    snapshot=rj(repo/snapshot_path)
    if any(snapshot.get(r['id'])!=r['sourceHash'] for r in regrows): raise SystemExit('FAIL registry/snapshot hash')
    active_rank={sid:i for i,sid in enumerate(sorted(registry),1)}; id_order_sha=sha('\n'.join(sorted(registry))+'\n'); cat_order_sha=sha('\n'.join(ids)+'\n')
    # Reattest the prior 360 selected source IDs at their exact catalog positions.
    selection_rows=[]; seen=set()
    for row in prior_selections+prev_selected:
        sid=row['sourceId']; idx=row.get('catalogZeroBasedIndex',row.get('position')); msg=msgs.get(sid); old=row.get('currentSourceSha256',row.get('sourceSha256',row.get('priorSourceSha256')))
        if sid in seen or msg is None or idx is None or ids[idx]!=sid or sha(msg['source'])!=old or msg.get('sourceHash')!=old: raise SystemExit('FAIL prior selection continuity '+sid)
        if sid in registry and registry[sid].get('sourceHash')!=old: raise SystemExit('FAIL source registry hash '+sid)
        seen.add(sid); selection_rows.append({'priorWindow':row.get('priorWindow',PREV_WINDOW),'position':row.get('position',idx),'catalogZeroBasedIndex':idx,'sourceId':sid,'priorSourceSha256':old,'currentSourceSha256':old,'selectionPositionMatches':True,'sourceHashMatches':True,'registryMembershipAndHashMatch':sid in registry,'priorSelectionEvidenceSha256':row.get('priorSelectionEvidenceSha256',sha(canon(row))),'reattestedAtHead':HEAD})
    if len(selection_rows)!=360: raise SystemExit('FAIL prior selected source total')
    production={p:file_tuple(p,HEAD) for p in production_paths(HEAD)}
    # Reattest 952 old holds plus the 12 W725 callerless cells. Hold text remains absent.
    hold_rows=[]
    for row in prev_holds:
        sid,loc=row['sourceId'],row['locale']; idx=ids.index(sid); msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc]); expected=row.get('priorTargetSha256',row.get('currentTargetSha256'))
        oldidx=row.get('catalogZeroBasedIndex')
        if sh!=row['sourceSha256'] or th!=expected or oldidx is not None and oldidx!=idx: raise SystemExit('FAIL prior held hash/position '+sid+'/'+loc)
        if any(k in row for k in ('source','sourceText','currentTarget','target','targetText','proposedTarget')): raise SystemExit('FAIL prior hold text')
        hold_rows.append({'window':row['window'],'position':idx,'priorPosition':row.get('priorPosition',row.get('position')),'selectionPositionBasis':row.get('selectionPositionBasis','prior catalog selection'),'catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'priorTargetSha256':expected,'currentTargetSha256':th,'selectionPositionMatches':True,'targetUnchanged':True,'priorHoldEvidenceSha256':row.get('priorHoldEvidenceSha256',sha(canon(row))),'textOmitted':True,'reattestedAtHead':HEAD})
    prev_callerless=[r for r in prev_cells if r.get('callerless')]
    if len(prev_callerless)!=12: raise SystemExit('FAIL W725 callerless predecessor cells')
    for row in prev_callerless:
        sid,loc=row['sourceId'],row['locale']; idx=ids.index(sid); msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc])
        if row.get('sourceTextOmitted') is not True or row.get('currentTargetTextOmitted') is not True or row.get('catalogZeroBasedIndex')!=idx or row.get('sourceSha256')!=sh or row.get('currentTargetSha256')!=th: raise SystemExit('FAIL W725 hash-only hold continuity '+sid+'/'+loc)
        hold_rows.append({'window':PREV_WINDOW,'position':idx,'priorPosition':idx,'selectionPositionBasis':'catalog insertion index','catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'priorTargetSha256':th,'currentTargetSha256':th,'selectionPositionMatches':True,'targetUnchanged':True,'callerless':True,'callerContextSha256':row['callerContextSha256'],'priorHoldEvidenceSha256':sha(canon(row)),'textOmitted':True,'reattestedAtHead':HEAD})
    if len(hold_rows)!=964 or len({(r['sourceId'],r['locale']) for r in hold_rows})!=964: raise SystemExit('FAIL accumulated prior hold count')
    # Reattest prior applied hashes (132 from earlier windows plus five W725 changes).
    applied=[]
    for row in prev_applied:
        sid,loc=row['sourceId'],row['locale']; msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc]); want=row.get('priorSelectedTargetSha256',row.get('currentTargetSha256'))
        if sh!=row['sourceSha256'] or th!=want: raise SystemExit('FAIL prior applied cell '+sid+'/'+loc)
        applied.append({'priorWindow':row['priorWindow'],'catalogZeroBasedIndex':ids.index(sid),'sourceId':sid,'sourceSha256':sh,'locale':loc,'priorSelectedTargetSha256':want,'currentTargetSha256':th,'targetUnchanged':True,'applicationCommit':row.get('applicationCommit'),'priorAppliedEvidenceSha256':row.get('priorAppliedEvidenceSha256',sha(canon(row))),'textOmitted':True,'reattestedAtHead':HEAD})
    target_readback=prior_app['targetReadback']; target_map={}
    for row in target_readback:
        key=(row['sourceId'],row['locale'])
        if key in target_map: raise SystemExit('FAIL duplicate W725 readback target')
        target_map[key]=row
    if len(target_map)!=5: raise SystemExit('FAIL W725 selected application cells')
    prev_cell_map={(r['sourceId'],r['locale']):r for r in prev_cells}
    if len(prev_cell_map)!=240: raise SystemExit('FAIL W725 predecessor cells')
    prev_window_readback=[]
    for key,row in prev_cell_map.items():
        sid,loc=key; idx=ids.index(sid); msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc]); target=target_map.get(key)
        if idx!=row['catalogZeroBasedIndex'] or sh!=row['sourceSha256']: raise SystemExit('FAIL W725 previous source pin '+sid)
        if target:
            if target['position']!=idx or target['beforeSha256']!=row['currentTargetSha256'] or target['afterSha256']!=th or sha(target['before'])!=target['beforeSha256'] or sha(target['after'])!=th or target['callerContextSha256']!=row['callerContextSha256']: raise SystemExit('FAIL W725 applied readback '+sid+'/'+loc)
            applied.append({'priorWindow':PREV_WINDOW,'catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'beforeTargetSha256':target['beforeSha256'],'priorSelectedTargetSha256':th,'currentTargetSha256':th,'targetUnchanged':True,'applicationCommit':PRODUCT,'priorAppliedEvidenceSha256':sha(canon({k:target[k] for k in ('position','locale','sourceId','beforeSha256','afterSha256','callerContextSha256')})),'textOmitted':True,'reattestedAtHead':HEAD})
        elif th!=row['currentTargetSha256']: raise SystemExit('FAIL unexpected W725 changed target '+sid+'/'+loc)
        callerless=bool(row.get('callerless'))
        if callerless and (target or row.get('sourceTextOmitted') is not True or row.get('currentTargetTextOmitted') is not True): raise SystemExit('FAIL W725 callerless text/target leak')
        prev_window_readback.append({'priorWindow':PREV_WINDOW,'position':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'priorTargetSha256':th,'currentTargetSha256':th,'matchesPriorProductReadback':True,'targetUnchanged':True,'textOmitted':True,'callerlessHeld':callerless,'reattestedAtHead':HEAD})
    if set(target_map)!={(r['sourceId'],r['locale']) for r in applied if r.get('priorWindow')==PREV_WINDOW}: raise SystemExit('FAIL W725 application output/selected-target alignment')
    if len(applied)!=137 or len({(r['sourceId'],r['locale']) for r in applied})!=137: raise SystemExit('FAIL accumulated prior applied count')
    readbacks={}
    for path in sorted(PREV_INPUT.glob('prior-*-cell-hash-reattestation.jsonl')):
        old_rows=rjl(path)
        if len(old_rows)!=240: raise SystemExit('FAIL prior readback count '+path.name)
        label=old_rows[0]['priorWindow']; now=[]
        for row in old_rows:
            sid,loc=row['sourceId'],row['locale']; idx=ids.index(sid); msg=msgs[sid]; sh=sha(msg['source']); th=sha(msg['translations'][loc]); oldtarget=next((row[k] for k in ('currentTargetSha256','actualTargetSha256','priorTargetSha256') if k in row),None)
            if row.get('sourceSha256') not in (None,sh) or oldtarget!=th or row.get('catalogZeroBasedIndex',row.get('position'))!=idx: raise SystemExit('FAIL prior readback '+label+' '+sid+'/'+loc)
            now.append({'priorWindow':label,'position':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sh,'locale':loc,'priorTargetSha256':oldtarget,'currentTargetSha256':th,'matchesPriorReadback':True,'targetUnchanged':True,'textOmitted':True,'reattestedAtHead':HEAD})
        if len({(r['sourceId'],r['locale']) for r in now})!=240: raise SystemExit('FAIL readback duplicate '+label)
        readbacks[label]=now
    if len(readbacks)!=8 or PREV_WINDOW in readbacks: raise SystemExit('FAIL prior complete readback window set')
    readbacks[PREV_WINDOW]=prev_window_readback
    if len(readbacks)!=9: raise SystemExit('FAIL complete prior readback windows')
    prior_contexts=[]
    for sid in sorted({r['sourceId'] for r in hold_rows}):
        source=msgs[sid]['source']; ctx=match_context({'sourceId':sid,'source':source,'sourceSha256':sha(source)},production,HEAD)
        prior_contexts.append({'sourceId':sid,'sourceSha256':sha(source),'currentCallerless':ctx['callerless'],'exactMatchCount':ctx['exactMatchCount'],'callerContextSha256':ctx['contextSha256'],'heldCellCount':sum(r['sourceId']==sid for r in hold_rows),'sourceTextOmitted':True,'callerTextOmitted':True})
    # Check historical provenance caveats and W665 restoration remain hash-bound.
    prior_lineage=rj(PREV_INPUT/'prior-window-lineage.json'); w625=prior_lineage.get('w625EvidenceCaveat',{}); w645=prior_lineage.get('w645BlindSummaryPinWarning',{}); w665=prior_lineage.get('w665EvidenceRestoration',{})
    if w625.get('missingFromPriorCommittedPrTree')!=31 or not w625.get('matchesFinalVerifier') or not w645.get('blindChecksumMismatchRecorded') or w645.get('crossReviewResult')!='PASS_WITH_BLIND_SUMMARY_PIN_WARNING' or w665.get('currentEvidenceIndexEntries')!=77 or not w665.get('allCurrentIndexedPayloadsPresentAndHashMatched'): raise SystemExit('FAIL inherited evidence caveat/restoration')
    w665_commit=w665.get('restorationCommit')
    if not w665_commit or subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',w665_commit,HEAD],check=False).returncode: raise SystemExit('FAIL W665 restoration ancestry')
    old_contexts={r['sourceId']:r for r in rjl(PREV_INPUT/'source-contexts.jsonl')}; w725_contexts=[]
    for row in rjl(PREV_INPUT/'selected-sources.jsonl'):
        sid=row['sourceId']; old=old_contexts[sid]; source=msgs[sid]['source']; new=match_context({'sourceId':sid,'source':source,'sourceSha256':sha(source)},production,HEAD)
        sig=lambda c:[(x['path'],x['line'],x['lineSha256'],x['excerptSha256'],x['fileSha256'],x['gitBlob'],x['matchKind']) for x in c['callers']]
        unchanged=old['callerless']==new['callerless'] and old['exactMatchCount']==new['exactMatchCount'] and sig(old)==sig(new)
        w725_contexts.append({'sourceId':sid,'sourceSha256':sha(source),'priorCallerContextSha256':old['contextSha256'],'currentCallerContextSha256':new['contextSha256'],'callerless':new['callerless'],'exactMatchCount':new['exactMatchCount'],'callerSignaturesUnchanged':unchanged,'sourceTextOmitted':True,'callerTextOmitted':new['callerless']})
    catalog_pin={'path':catalog_path,'sha256':sha(catalog_raw),'gitBlob':git('rev-parse',f'{HEAD}:{catalog_path}'),'messageCount':len(msgs),'keyOrderSha256':cat_order_sha}
    source_pins={'head':HEAD,'tree':TREE,'files':[]}
    production_files={p:file_tuple(p,HEAD) for p in production_paths(HEAD)}
    oldpins={r['path']:r for r in rj(PREV_INPUT/'source-file-pins.json')['files']}
    for rel in sorted(set(production_files)|{catalog_path,registry_path,snapshot_path}):
        raw=(repo/rel).read_bytes(); row={'path':rel,'fileSha256':sha(raw),'gitBlob':git('rev-parse',f'{HEAD}:{rel}'),'bytes':len(raw)}
        if rel in oldpins and rel not in {catalog_path,registry_path,snapshot_path} and (row['fileSha256'],row['gitBlob'])!=(oldpins[rel]['fileSha256'],oldpins[rel]['gitBlob']): raise SystemExit('FAIL unexpected source file drift '+rel)
        source_pins['files'].append(row)
    if any(p not in {r['path'] for r in source_pins['files']} for p in oldpins if p not in {catalog_path,registry_path,snapshot_path}): raise SystemExit('FAIL predecessor source file disappeared')
    selected=[]; contexts=[]; cells=[]; mismatch=collections.Counter()
    for idx in range(745,765):
        sid=ids[idx]; msg=msgs[sid]; source=msg['source']; sh=sha(source)
        if msg.get('sourceHash')!=sh or sid in registry and registry[sid].get('sourceHash')!=sh: raise SystemExit('FAIL selected source registry/catalog '+sid)
        selected.append({'position':idx,'catalogZeroBasedIndex':idx,'catalogOneBasedPosition':idx+1,'sourceId':sid,'sourceSha256':sh,'activeSourceRank':active_rank.get(sid),'activeSourceRegistry':sid in registry,'registryLocations':registry.get(sid,{}).get('locations',[]),'source':source})
    if [x['catalogZeroBasedIndex'] for x in selected]!=list(range(745,765)) or len({x['sourceId'] for x in selected})!=20 or {x['sourceId'] for x in selected}&seen: raise SystemExit('FAIL current queue sequence/overlap')
    for item in selected:
        sid=item['sourceId']; source=item['source']; ctx=match_context({'sourceId':sid,'source':source,'sourceSha256':item['sourceSha256']},production,HEAD); contexts.append(ctx)
        for loc in LOCALES:
            target=msgs[sid].get('translations',{}).get(loc)
            if not isinstance(target,str) or not target: mismatch['missingTarget']+=1; target=''
            cell={'window':WINDOW,'position':item['position'],'catalogZeroBasedIndex':item['catalogZeroBasedIndex'],'catalogOneBasedPosition':item['catalogOneBasedPosition'],'sourceId':sid,'sourceSha256':item['sourceSha256'],'locale':loc,'callerContextSha256':ctx['contextSha256'],'literalCallerCount':ctx['exactMatchCount'],'callerless':ctx['callerless'],'candidateFree':True,'currentTargetSha256':sha(target)}
            if ctx['callerless']:
                cell.update({'cellDisposition':'hold-callerless-hash-only','sourceTextOmitted':True,'currentTargetTextOmitted':True})
            else:
                tok=token_rows(source,target)
                mismatch['placeholder']+=not tok['placeholderMultisetMatches']; mismatch['markup']+=not tok['markupMatches']; mismatch['numeric']+=not tok['numericTokensPreserved']; mismatch['numericPresentationDifferences']+=tok['numericPresentationEquivalent']; mismatch['protectedLiteral']+=not tok['protectedLiteralsPreserved']
                cell.update({'source':source,'currentTarget':target,**tok,'catalogTranslationHash':msgs[sid].get('translationHashes',{}).get(loc),'translationStatus':msgs[sid].get('translationStatus',{}).get(loc)})
            cells.append(cell)
    callerless=sum(c['callerless'] for c in contexts); holdcells=12*callerless
    if callerless!=2 or holdcells!=24 or len(cells)!=240: raise SystemExit('FAIL caller coverage/cell count')
    # Capture catalog and PR pins again; no repository writes are performed.
    after=live_attestation(); stable=('state','draft','merged','headRefName','head','tree','apiCommitTree','branchRefOid','pullRefOid','baseRefName','baseApiSha','baseLiveRefOid','bodySha256','bodyBytes')
    if any(before[k]!=after[k] for k in stable): raise SystemExit('FAIL PR/head/body changed during candidate-free extraction')
    if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'): raise SystemExit('FAIL worktree changed')
    inp=out/'input'; wj(inp/'PR-attestation-before.json',before); wj(inp/'PR-attestation-after.json',after)
    wjl(inp/'catalog-key-order.jsonl',[{'catalogZeroBasedIndex':i,'sourceId':sid,'sourceSha256':sha(msgs[sid]['source'])} for i,sid in enumerate(ids)])
    wj(inp/'catalog-file-pins.json',{'head':HEAD,'tree':TREE,'catalogPath':catalog_path,'catalogSha256':sha(catalog_raw),'catalogGitBlob':git('rev-parse',f'{HEAD}:{catalog_path}'),'catalogMessageCount':len(msgs),'catalogKeyOrderSha256':cat_order_sha,'sourceQueuePath':registry_path,'sourceQueueSha256':sha(registry_raw),'sourceSnapshotPath':snapshot_path,'sourceSnapshotSha256':sha(canon(snapshot)),'activeUniqueSourceIds':len(registry),'sourceIdOrderSha256':id_order_sha})
    wj(inp/'source-file-pins.json',source_pins)
    redacted=[]
    for row in regrows: redacted.append({k:v for k,v in row.items() if k not in ('source','translations','translation')})
    wj(inp/'source-registry-redacted.json',{'path':registry_path,'sha256':sha(registry_raw),'snapshotPath':snapshot_path,'snapshotSha256':sha(canon(snapshot)),'activeSourceCount':len(registry),'messages':redacted})
    wj(inp/'source-snapshot-hashes.json',snapshot)
    wjl(inp/'selected-sources.jsonl',[{k:v for k,v in row.items() if k!='source'}|({'source':row['source']} if not next(c for c in contexts if c['sourceId']==row['sourceId'])['callerless'] else {'sourceTextOmitted':True}) for row in selected])
    wjl(inp/'selection-boundary.jsonl',[{'position':i,'catalogZeroBasedIndex':i,'sourceId':ids[i],'sourceSha256':sha(msgs[ids[i]]['source']),'role':role,'sourceTextOmitted':True} for i,role in ((744,'catalog-before-selected-start'),(745,'selected-start'),(764,'selected-end'),(765,'catalog-after-selected-end'))])
    wjl(inp/'source-contexts.jsonl',[safe_context(c) for c in contexts]); wjl(inp/'candidate-free-cells.jsonl',cells); wj(inp/'candidate-free-token-summary.json',dict(mismatch))
    wjl(inp/'prior-selection-reattestation.jsonl',selection_rows); wj(inp/'prior-selection-reattestation-summary.json',{'count':360,'allSelectionsMatchCurrentCatalog':True,'head':HEAD,'tree':TREE})
    wjl(inp/'prior-hold-reattestation.jsonl',hold_rows); wj(inp/'prior-hold-reattestation-summary.json',{'count':964,'windows':dict(collections.Counter(r['window'] for r in hold_rows)),'allTargetHashesMatch':True,'changedTargets':0,'textInHoldRows':False,'head':HEAD,'tree':TREE})
    wjl(inp/'prior-hold-context-reattestation.jsonl',prior_contexts)
    wjl(inp/'prior-applied-cell-reattestation.jsonl',applied); wj(inp/'prior-applied-cell-reattestation-summary.json',{'count':137,'allFinalTargetHashesMatch':True,'changedTargets':0,'head':HEAD,'tree':TREE})
    for label,rows in readbacks.items(): wjl(inp/('prior-'+label.lower().replace('-','')+'-cell-hash-reattestation.jsonl'),rows)
    wjl(inp/'w725-current-product-readback.jsonl',prev_window_readback); wjl(inp/'w725-applied-targets-reattestation.jsonl',[r for r in applied if r.get('priorWindow')==PREV_WINDOW])
    wj(inp/'prior-window-lineage.json',{'result':'PASS','currentHead':HEAD,'currentTree':TREE,'previousCandidateFreeHead':PREV_HEAD,'previousCandidateFreeTree':PREV_TREE,'previousProductCommit':PRODUCT,'previousProductTree':PRODUCT_TREE,'previousSelectionsReattested':360,'previousHeldCellsReattested':964,'previousAppliedCellsReattested':137,'priorFullReadbackWindows':{k:len(v) for k,v in readbacks.items()},'priorNewCallerlessSources':len(prior_contexts),'priorHoldTextIncluded':False,'w625EvidenceCaveat':w625,'w645BlindSummaryPinWarning':w645,'w665EvidenceRestoration':{'restorationCommit':w665_commit,'currentEvidenceIndexEntries':77,'allCurrentIndexedPayloadsPresentAndHashMatched':True},'previousCandidateFreeChecksumsVerified':True,'previousProductReadbackVerified':True,'priorReviewRecommendationsRead':False})
    wj(inp/'selection.json',{'window':WINDOW,'selectionBasis':'catalog insertion order at exact pinned romarr/ui-labels.json indices 745 through 764 (zero-based)','positions':[745,764],'catalogOneBasedPositions':[746,765],'sourceCount':20,'localeCount':12,'cellCount':240,'localeOrder':LOCALES,'selectedSources':[{k:v for k,v in row.items() if k!='source'}|({'source':row['source']} if not next(c for c in contexts if c['sourceId']==row['sourceId'])['callerless'] else {'sourceTextOmitted':True}) for row in selected]})
    wj(inp/'prior-application-source-pin.json',{'sourceHead':PREV_HEAD,'sourceTree':PREV_TREE,'productCommit':PRODUCT,'productTree':PRODUCT_TREE,'currentHead':HEAD,'currentTree':TREE,'productCommitAncestor':True,'currentCatalogSha256':sha(catalog_raw),'applicationReadbackPath':str(PREV_APP),'applicationReadbackSha256':sha(PREV_APP.read_bytes()),'applicationCellCount':5,'applicationCellHashesReattested':True})
    summary={'artifact':'ROMarrNG PR #70 W745-W764 candidate-free exact-head input','repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':BRANCH,'head':HEAD,'tree':TREE,'window':WINDOW,'catalogSelectionZeroBased':[745,764],'catalogSelectionOneBased':[746,765],'sourceCount':20,'localeCount':12,'cellCount':240,'callerBackedCells':216,'callerlessSourceCount':2,'callerlessHashOnlyCells':24,'directCallerReferences':sum(c['exactMatchCount'] for c in contexts),'productionCallerFilesSearched':len(production),'currentTokenMismatchCounts':dict(mismatch),'priorSelectionsReattested':360,'priorActiveHoldsReattested':964,'newWindowHashOnlyHolds':24,'resultingActiveHashOnlyHolds':988,'priorAppliedCellsReattested':137,'priorFullReadbackWindowCount':9,'W725AppliedTargetCount':5,'W725ProductReadbackCells':240,'W625MissingStageFileCaveatPreserved':True,'W645StaleBlindChecksumPointerWarningPreserved':True,'W665EvidenceRestorationAttested':True,'proposedTargetsIncluded':False,'reviewDecisionsIncluded':False,'repoEdited':False,'testsBuildsScansCiRun':False,'nextBoundary':{'continuationIndex':765,'oneBasedPosition':766,'sourceId':ids[765],'sourceSha256':sha(msgs[ids[765]]['source'])}}
    wj(inp/'manifest.json',summary)
    (out/'README.md').write_text(f'''# ROMarrNG PR #70 W745–W764 candidate-free packet

Pinned to open draft PR head `{HEAD}`, tree `{TREE}`, branch `{BRANCH}`. The packet selects zero-based catalog indices 745–764 (one-based positions 746–765): 20 source keys and 240 cells across 12 locales.

There are 216 caller-backed cells and 24 callerless hash-only cells from two sources. Source and target text are omitted for those callerless rows. The packet reattests 360 previous source selections, 964 prior active hold cells, 137 previously applied cells, and nine complete 240-cell product readback windows. Adding this window's 24 callerless holds yields 988 active hash-only holds. Prior W625 missing-stage-file and W645 stale blind-checksum-pointer caveats remain recorded; W665's 77 indexed payloads remain present and hash-matching.

The W725–W744 product commit is pinned at `{PRODUCT}` / tree `{PRODUCT_TREE}` and its five selected target hashes are reattested against current catalog state. No prior recommendation rows were used to review this new window. This packet contains no W745–W764 proposal or decision.

No repository, catalog, PR, or workflow files were changed. No tests, builds, scans, or CI were run. Verify with `python3 verify_candidate_free.py --repo {REPO}`.
''',encoding='utf-8')
    # nested and outer packet manifests/checksums
    inpfiles=sorted(p for p in inp.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (inp/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(inp).as_posix()}\n' for p in inpfiles),encoding='utf-8')
    outerfiles=sorted(p for p in out.rglob('*') if p.is_file() and p!=out/'SHA256SUMS.txt')
    (out/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(out).as_posix()}\n' for p in outerfiles),encoding='utf-8')
    print(json.dumps({'result':'BUILT','head':HEAD,'tree':TREE,'window':WINDOW,'cells':240,'callerBackedCells':216,'callerlessHashOnlyCells':24,'priorActiveHoldsReattested':964,'resultingActiveHolds':988,'priorAppliedCellsReattested':137,'nextBoundary':summary['nextBoundary']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
