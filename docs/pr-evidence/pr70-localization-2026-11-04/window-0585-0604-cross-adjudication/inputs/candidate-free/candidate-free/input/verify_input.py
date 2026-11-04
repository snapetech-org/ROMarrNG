#!/usr/bin/env python3
"""Portable exact-hash verifier for ROMarrNG PR #70 W585-W604 candidate-free input."""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, re, subprocess
HERE=pathlib.Path(__file__).resolve().parent
HEAD='01da053f0e6a47e7184fb86da77f66b7b6719653'
TREE='dcb9c1766831e217ffca7fb77068b97c33b9524e'
BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
FORBIDDEN={'proposedTarget','selectedTarget','disposition','rationale','primaryDisposition','blindDisposition','decision'}
HOLD_TEXT={'source','sourceText','currentTarget','target','targetText','proposedTarget','selectedTarget','finalTarget'}
PH=re.compile(r'\{[^{}]+\}')
TAG=re.compile(r'<[^>]+>')
NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
KNOWN_PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','Moonlight']
def fail(m): raise SystemExit('FAIL: '+m)
def need(v,m):
    if not v: fail(m)
def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def j(name): return json.loads((HERE/name).read_text(encoding='utf-8'))
def jl(name): return [json.loads(x) for x in (HERE/name).read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])
def protected(source):
    found=[]
    for term in KNOWN_PROTECTED:
        if re.search(r'(?<![A-Za-z0-9])'+re.escape(term)+r'(?![A-Za-z0-9])',source): found.append(term)
    if re.search(r'(?<![A-Za-z0-9])DATs?(?![A-Za-z0-9])',source) and 'DAT' not in found: found.append('DAT')
    return sorted(set(found))
def tokens(source):
    nums=NUM.findall(source)
    return {'placeholders':PH.findall(source),'markup':TAG.findall(source),'numbers':nums,'protectedLiterals':protected(source)}
def check_safe(v,where='input'):
    if isinstance(v,dict):
        bad=FORBIDDEN.intersection(v)
        need(not bad,f'current-window decision/proposal fields in {where}: {sorted(bad)}')
        for k,x in v.items(): check_safe(x,where+'.'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v): check_safe(x,f'{where}[{i}]')
def git_tree_paths(repo):
    raw=git(repo,'ls-files','-z','--','romarr').split(b'\0')
    paths=[]
    for b in raw:
        if not b: continue
        rel=b.decode('utf-8'); p=pathlib.Path(rel)
        if p.suffix.lower() not in ('.py','.js','.html','.jinja','.jinja2','.css','.ts','.tsx'): continue
        parts=rel.lower().split('/')
        if 'test' in parts or 'tests' in parts or '__pycache__' in parts or p.name.startswith('test_') or p.name.endswith('_test.py'): continue
        paths.append(rel)
    return sorted(paths)
def re_search_context(item,files):
    src=item['source']; sid=item['sourceId']; matches=[]
    variants=list(dict.fromkeys([json.dumps(src,ensure_ascii=False),repr(src),'"'+src+'"',"'"+src+"'",'`'+src+'`']))
    for rel,(text,b,blob) in files.items():
        occurrences={}; lines=text.splitlines()
        for literal in variants:
            at_from=0
            while True:
                at=text.find(literal,at_from)
                if at<0: break
                occurrences.setdefault(at,'exact quoted source literal'); at_from=at+max(1,len(literal))
        at_from=0
        while True:
            at=text.find(sid,at_from)
            if at<0: break
            occurrences.setdefault(at,'exact source ID reference'); at_from=at+len(sid)
        node_re=re.compile(r'>[ \t]*'+re.escape(src)+r'[ \t]*<')
        for hit in node_re.finditer(text): occurrences.setdefault(hit.start(),'exact HTML text node')
        for at,kind in sorted(occurrences.items()):
            line_no=text.count('\n',0,at)+1; lo=max(1,line_no-3); hi=min(len(lines),line_no+3)
            excerpt=[{'line':i,'text':lines[i-1]} for i in range(lo,hi+1)]
            line_text=lines[line_no-1] if line_no<=len(lines) else ''
            matches.append({'path':rel,'line':line_no,'lineText':line_text,'lineSha256':sha(line_text),'excerpt':excerpt,'excerptSha256':sha(canon(excerpt)),'fileSha256':sha(b),'gitBlob':blob,'matchKind':kind})
    matches.sort(key=lambda x:(x['path'],x['line'],x['matchKind']))
    core={'sourceId':sid,'source':src,'sourceSha256':item['sourceSha256'],'searchMethod':'exact quoted source literal, exact source ID, or exact HTML text-node search in tracked production code; tests/docs/catalog files excluded','productionFilesSearched':len(files),'exactMatchCount':len(matches),'callerless':not matches,'callers':matches}
    return {**core,'contextSha256':sha(canon(core))}
def verify_checksums():
    rows={}
    for line in (HERE/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); p=(HERE/n).resolve()
        need(p.is_relative_to(HERE.resolve()) and p.is_file(),'unsafe/missing checksum path '+n)
        need(sha(p.read_bytes())==h,'candidate-free checksum mismatch '+n); rows[n]=h
    actual={p.name for p in HERE.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(set(rows)==actual,'candidate-free checksum coverage')
    files={x['path']:x for x in j('manifest.json')['files']}
    need(set(files)==actual-{'manifest.json'},'candidate-free manifest file inventory')
    for n,x in files.items():
        b=(HERE/n).read_bytes(); need(len(b)==x['bytes'] and sha(b)==x['sha256'],'manifest file hash '+n)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=pathlib.Path,required=True,help='Git worktree containing the pinned PR head and prior application commits')
    repo=ap.parse_args().repo.resolve(); need(repo.is_dir(),'repo path missing')
    need(git(repo,'rev-parse','HEAD').decode().strip()==HEAD and git(repo,'show','-s','--format=%T',HEAD).decode().strip()==TREE,'exact pinned worktree head/tree')
    need(git(repo,'status','--porcelain=v1','--untracked-files=all').decode().strip()=='','exact pinned worktree is dirty')
    need(git(repo,'branch','--show-current').decode().strip()=='','review worktree must be detached')
    verify_checksums()
    manifest=j('manifest.json'); selection=j('selection.json')
    need(manifest['candidateFree'] is True and manifest['proposedTargetsIncluded'] is False and manifest['reviewDecisionsIncluded'] is False,'candidate-free flags')
    need((manifest['head'],manifest['tree'],manifest['window'])==(HEAD,TREE,'W585-W604'),'candidate-free pin/window')
    need((manifest['sourceCount'],manifest['localeCount'],manifest['cellCount'],manifest['locales'])==(20,12,240,LOCALES),'candidate-free scope')
    for name in sorted(x.name for x in HERE.iterdir() if x.is_file() and x.suffix in ('.json','.jsonl')):
        check_safe(jl(name) if name.endswith('.jsonl') else j(name),name)
    need(selection['window']=='W585-W604' and selection['positions']==[585,604] and selection['catalogInsertionPositionsOneBased']==[586,605] and selection['sourceCount']==20 and selection['localeCount']==12 and selection['cellCount']==240,'selection window/count')
    need(selection['localeOrder']==LOCALES,'locale order')
    # Reconstruct the full source catalog and exact ordinal boundary.
    catpath='romarr/ui-labels.json'; catraw=git(repo,'show',f'{HEAD}:{catpath}'); catdoc=json.loads(catraw); messages=catdoc['messages']; ids=list(messages)
    need(len(messages)==1836 and sha(catraw)==manifest['catalogSha256'],'current catalog pin/count')
    cp=j('catalog-file-pins.json'); need(cp['commit']==HEAD and cp['tree']==TREE and cp['catalogPath']==catpath and cp['catalogSha256']==sha(catraw),'catalog pin header')
    need(git(repo,'rev-parse',f'{HEAD}:{catpath}').decode().strip()==cp['catalogGitBlob'],'catalog git blob')
    key_order_sha=sha('\n'.join(ids)+'\n')
    need(key_order_sha==manifest['catalogKeyOrderSha256']==selection['catalogKeyOrderSha256']==cp['catalogKeyOrderSha256'],'catalog insertion order hash')
    inventory=jl('catalog-source-inventory.jsonl')
    need(len(inventory)==1836 and [x['sourceId'] for x in inventory]==ids,'full catalog inventory/order')
    for i,row in enumerate(inventory):
        m=messages[row['sourceId']]; src=m['source']; tok=tokens(src)
        need(row['catalogZeroBasedIndex']==i and row['catalogOneBasedPosition']==i+1 and row['source']==src and row['sourceSha256']==sha(src)==m.get('sourceHash'),'catalog source row '+row['sourceId'])
        need(row['sourcePlaceholderTokens']==tok['placeholders'] and row['sourceMarkupTags']==tok['markup'] and row['sourceNumericTokens']==tok['numbers'] and row['sourceProtectedLiterals']==tok['protectedLiterals'],'catalog source token row '+row['sourceId'])
    selected=jl('source-inventory-selection.jsonl')
    need(len(selected)==20 and [x['catalogZeroBasedIndex'] for x in selected]==list(range(585,605)) and [x['sourceId'] for x in selected]==ids[585:605],'selected source positions/order')
    need(selection['selectedSources']==selected,'selection payload/current source list')
    boundary=jl('selection-boundary.jsonl')
    expected_boundary=[]
    for idx,role in [(584,'catalog-before-selected-start'),(585,'selected-start'),(604,'selected-end'),(605,'catalog-after-selected-end')]:
        sid=ids[idx]; src=messages[sid]['source']; expected_boundary.append({'position':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'source':src,'sourceSha256':sha(src),'role':role})
    need(boundary==expected_boundary,'selection boundary')
    need(selection['sourceIdOrderSha256']==manifest['sourceIdOrderSha256'],'registry order linkage')
    # Registry/source snapshot and exact tracked source file pins.
    registry_path='romarr/ui-source-messages.json'; snapshot_path='romarr/ui-source-snapshot.json'
    registry_raw=git(repo,'show',f'{HEAD}:{registry_path}'); registry=json.loads(registry_raw)['messages']; registry_by={x['id']:x for x in registry}; active_rank={sid:i for i,sid in enumerate(sorted(registry_by),1)}
    snapshot_raw=git(repo,'show',f'{HEAD}:{snapshot_path}'); snapshot=json.loads(snapshot_raw)
    active_snapshot={x['id']:x['sourceHash'] for x in registry}
    full_snapshot={sid:messages[sid]['sourceHash'] for sid in ids}
    need(len(registry)==len(registry_by)==manifest['activeUniqueSourceIdCount']==479 and all(snapshot.get(k)==v for k,v in active_snapshot.items()),'active source registry/snapshot subset')
    need(snapshot==full_snapshot,'complete catalog source snapshot')
    carried_snapshot=j('source-snapshot.json')
    need(carried_snapshot==active_snapshot and sha(canon(carried_snapshot))==manifest['sourceSnapshotSha256']==cp['sourceSnapshotSha256'],'active source snapshot hash')
    need(sha(registry_raw)==manifest['sourceQueueSha256']==cp['sourceQueueSha256'] and sha('\n'.join(sorted(registry_by))+'\n')==manifest['sourceIdOrderSha256'],'source queue/order hash')
    pins=j('source-file-pins.json'); need(pins['head']==HEAD and pins['tree']==TREE,'source file pin header')
    production_paths=git_tree_paths(repo); expected_pins=set(production_paths)|{registry_path,snapshot_path}
    pin_map={x['path']:x for x in pins['files']}; need(len(pin_map)==len(pins['files']) and set(pin_map)==expected_pins,'complete production/runtime file pin inventory')
    files={}
    for rel,pin in pin_map.items():
        b=git(repo,'show',f'{HEAD}:{rel}')
        need(len(b)==pin['bytes'] and sha(b)==pin['fileSha256'] and git(repo,'rev-parse',f'{HEAD}:{rel}').decode().strip()==pin['gitBlob'],'exact file pin '+rel)
        if rel in production_paths:
            try: text=b.decode('utf-8')
            except UnicodeDecodeError: text=b.decode('utf-8','replace')
            files[rel]=(text,b,pin['gitBlob'])
    catpin_files=cp['sourceCallerFilePins']
    need(set(catpin_files)==expected_pins and all(catpin_files[p]['fileSha256']==pin_map[p]['fileSha256'] and catpin_files[p]['gitBlob']==pin_map[p]['gitBlob'] for p in expected_pins),'catalog/source file pin linkage')
    # Independently re-run all exact caller queries and compare complete excerpts.
    contexts=jl('source-contexts.jsonl'); need(len(contexts)==20 and {x['sourceId'] for x in contexts}=={x['sourceId'] for x in selected},'source context coverage')
    ctx={x['sourceId']:x for x in contexts}
    for item in selected:
        c=ctx[item['sourceId']]; expected=re_search_context(item,files)
        need(c==expected,'exact caller set/context mismatch '+item['sourceId'])
    audit=j('caller-search-audit.json')
    need(audit['head']==HEAD and audit['tree']==TREE and audit['queryCount']==20 and audit['productionFilesSearched']==len(files),'caller search audit pin/count')
    need(audit['results']==[{'sourceId':c['sourceId'],'sourceSha256':c['sourceSha256'],'matchCount':c['exactMatchCount'],'callerless':c['callerless'],'contextSha256':c['contextSha256']} for c in contexts],'caller search audit results')
    # Check all 240 current target cells and translation token inventories.
    cells=jl('current-target-cells.jsonl'); need(len(cells)==240 and len({(x['sourceId'],x['locale']) for x in cells})==240,'current-target cell count/uniqueness')
    cmap={(x['sourceId'],x['locale']):x for x in cells}; need(set(cmap)=={(x['sourceId'],l) for x in selected for l in LOCALES},'current-target cell coverage')
    mismatches=collections.Counter();
    for c in cells:
        sid,loc=c['sourceId'],c['locale']; m=messages[sid]; src=m['source']; target=m['translations'][loc]; st=tokens(src); tt=tokens(target)
        need(c['catalogZeroBasedIndex']==ids.index(sid) and c['position']==c['catalogZeroBasedIndex'] and c['source']==src and c['sourceSha256']==sha(src),'current cell source/order '+sid+'/'+loc)
        need(c['currentTarget']==target and c['currentTargetSha256']==sha(target),'current catalog target '+sid+'/'+loc)
        need(c['callerContextSha256']==ctx[sid]['contextSha256'] and c['containsCandidate'] is False,'current cell caller/candidate linkage '+sid+'/'+loc)
        refs=[{k:r[k] for k in ('path','line','lineSha256','excerptSha256','fileSha256','gitBlob')} for r in ctx[sid]['callers']]
        need(c['callerRefs']==refs,'cell exact caller list '+sid+'/'+loc)
        need(c['sourcePlaceholderTokens']==st['placeholders'] and c['currentPlaceholderTokens']==tt['placeholders'] and c['placeholderMultisetMatches'] is True and collections.Counter(st['placeholders'])==collections.Counter(tt['placeholders']),'placeholder token parity '+sid+'/'+loc)
        need(c['sourceMarkupTags']==st['markup'] and c['currentMarkupTags']==tt['markup'] and c['markupMatches'] is True and collections.Counter(st['markup'])==collections.Counter(tt['markup']),'markup token parity '+sid+'/'+loc)
        srcn=collections.Counter(st['numbers']); tgtn=collections.Counter(tt['numbers']); extra=list((tgtn-srcn).elements()); zeroeq=bool(c['numericPresentationEquivalent']) and c['sourceNumericWords']==['Zero'] and not srcn and extra==['0']
        need(c['sourceNumericTokens']==st['numbers'] and c['currentNumericTokens']==tt['numbers'] and c['numericTokensPreserved'] is True and not (srcn-tgtn) and (not extra or zeroeq),'numeric token parity '+sid+'/'+loc)
        need(c['sourceProtectedLiterals']==st['protectedLiterals'] and c['currentProtectedLiterals']==[t for t in st['protectedLiterals'] if t in target] and c['protectedLiteralsPreserved'] is True and not c['missingProtectedLiterals'],'protected literal parity '+sid+'/'+loc)
        need(c['catalogTranslationHash']==m.get('translationHashes',{}).get(loc),'translation-hash metadata '+sid+'/'+loc)
        for n,ok in [('placeholder',c['placeholderMultisetMatches']),('markup',c['markupMatches']),('numeric',c['numericTokensPreserved']),('protectedLiteral',c['protectedLiteralsPreserved'])]: mismatches[n]+=not ok
    mismatch=j('current-target-token-mismatches.json')
    need(mismatch=={'placeholder':mismatches['placeholder'],'markup':mismatches['markup'],'numeric':mismatches['numeric'],'numericPresentationDifferences':sum(x['numericPresentationEquivalent'] for x in cells),'protectedLiteral':mismatches['protectedLiteral'],'missingTarget':0},'token mismatch summary')
    need(manifest['currentTargetMissingCells']==0 and manifest['currentTargetPlaceholderMismatches']==mismatch['placeholder'] and manifest['currentTargetMarkupMismatches']==mismatch['markup'] and manifest['currentTargetNumericMismatches']==mismatch['numeric'] and manifest['currentTargetProtectedLiteralMismatches']==mismatch['protectedLiteral'],'manifest token/count summary')
    # Hash-only prior source selection lineage: ten completed windows through W565-W584.
    prior=jl('prior-selection-reattestation.jsonl'); need(len(prior)==200 and len({x['sourceId'] for x in prior})==200,'prior selected source count/uniqueness')
    expected_prior_counts={'W385-W404':20,'W405-W424':20,'W425-W444':20,'W445-W464':20,'W465-W484':20,'W485-W504':20,'W505-W524':20,'W525-W544':20,'W545-W564':20,'W565-W584':20}
    need(dict(collections.Counter(x['priorWindow'] for x in prior))==expected_prior_counts,'prior selection window distribution')
    for row in prior:
        sid=row['sourceId']; idx=row['catalogZeroBasedIndex']; window=row['priorWindow']
        need(0<=idx<1836 and ids[idx]==sid and sha(messages[sid]['source'])==row['priorSourceSha256']==row['currentSourceSha256'],'prior selection source/position/hash '+sid)
        need(row['selectionPositionMatches'] is True and row['sourceHashMatches'] is True and isinstance(row['registryMembershipAndHashMatch'],bool),'prior selection status '+sid)
        need(re.fullmatch(r'[0-9a-f]{64}',row['priorSelectionEvidenceSha256']) is not None,'prior selection evidence hash '+sid)
        if window in ('W525-W544','W545-W564','W565-W584'):
            lo={'W525-W544':525,'W545-W564':545,'W565-W584':565}[window]; hi=lo+19
            need(lo<=row['position']<=hi and row['position']==idx,window+' selected ordinal '+sid)
        else:
            m=re.fullmatch(r'W(\d+)-W(\d+)',window); need(m is not None and int(m.group(1))<=row['position']<=int(m.group(2)),'prior selection source rank '+sid)
    ps=j('prior-selection-reattestation-summary.json')
    need(ps['reattestedSelectedSourceCount']==200 and ps['allPriorSelectionsMatchCurrentCatalogAndRegistry'] is True and dict(ps['priorWindows'])==expected_prior_counts,'prior selection summary')
    # Hash-only prior holds include the completed W565 cross-review holds.
    holds=jl('prior-hold-reattestation.jsonl'); need(len(holds)==604 and len({(x['sourceId'],x['locale']) for x in holds})==604,'prior hold count/uniqueness')
    expected_hold_counts=dict(j('prior-hold-reattestation-summary.json')['windowCounts']); expected_hold_counts['W525-W544']=12; expected_hold_counts['W545-W564']=12; expected_hold_counts['W565-W584']=40
    need(dict(collections.Counter(x['window'] for x in holds))==expected_hold_counts,'prior hold distribution')
    for h in holds:
        need(not (HOLD_TEXT & set(h)),'prior hold exposes translation text')
        sid,loc=h['sourceId'],h['locale']; idx=ids.index(sid); item=messages[sid]
        need(loc in LOCALES and h['sourceSha256']==sha(item['source']) and h['priorTargetSha256']==h['currentTargetSha256']==sha(item['translations'][loc]),'prior hold hashes '+sid+'/'+loc)
        need(h['sourceMatchesCurrentCatalog'] and h['selectionPositionMatches'] and h['targetUnchanged'] and h['reattestedAtHead']==HEAD,'prior hold reattestation status '+sid+'/'+loc)
        if 'catalog insertion index' in h['selectionPositionBasis']: need(h['position']==idx,'prior hold catalog index '+sid)
        else: need(h['position']==active_rank.get(sid),'prior hold active registry rank '+sid)
    hs=j('prior-hold-reattestation-summary.json')
    need(hs['reattestedCellCount']==604 and hs['currentTargetChangedCells']==0 and hs['allCurrentTargetHashesMatchPriorHoldEvidence'] is True,'prior hold summary')
    w565_history=[h for h in holds if h['window']=='W565-W584']
    need(len(w565_history)==40 and sum(h.get('callerless') is True for h in w565_history)==36 and sum(h.get('callerless') is False for h in w565_history)==4,'W565 historical callerless/contextual hold counts')
    # Full W545 application readback is hash-only, with two applied updates and 12 held cells.
    window_cells=jl('prior-window-cell-hash-reattestation.jsonl'); need(len(window_cells)==240 and len({(x['sourceId'],x['locale']) for x in window_cells})==240,'prior W545 readback count/uniqueness')
    wmap={(x['sourceId'],x['locale']):x for x in window_cells}
    w_holds={(h['sourceId'],h['locale']) for h in holds if h['window']=='W545-W564'}
    need(len(w_holds)==12 and sum(x['applicationChanged'] for x in window_cells)==2 and sum(x['held'] for x in window_cells)==12,'prior W545 update/hold counts')
    for x in window_cells:
        sid,loc=x['sourceId'],x['locale']; idx=ids.index(sid)
        need(x['priorWindow']=='W545-W564' and x['catalogZeroBasedIndex']==idx and 545<=idx<=564 and loc in LOCALES,'prior W545 cell identity')
        need(x['sourceSha256']==sha(messages[sid]['source']) and x['currentTargetSha256']==sha(messages[sid]['translations'][loc]),'prior W545 target/source hash '+sid+'/'+loc)
        need(x['applicationCommit']=='2a921d8280487f6d172616719f32e3dced243d83' and x['targetMatchesApplicationReadback'] is True and x['reattestedAtHead']==HEAD,'prior W545 app provenance '+sid+'/'+loc)
        need(bool(x['held'])==((sid,loc) in w_holds) and (not x['held'] or not x['applicationChanged']),'prior W545 hold preservation '+sid+'/'+loc)
        for field in ('priorCandidateFreeCellEvidenceSha256','applicationReadbackCellEvidenceSha256'):
            need(re.fullmatch(r'[0-9a-f]{64}',x[field]) is not None,'prior W545 evidence row hash '+field)
    # Full W565 application readback and text-free cross holds are reattested at the current head.
    w565_cells=jl('prior-w565-window-cell-hash-reattestation.jsonl'); need(len(w565_cells)==240 and len({(x['sourceId'],x['locale']) for x in w565_cells})==240,'prior W565 readback count/uniqueness')
    w565_map={(x['sourceId'],x['locale']):x for x in w565_cells}
    w565_holds={(h['sourceId'],h['locale']) for h in holds if h['window']=='W565-W584'}
    need(len(w565_holds)==40 and sum(x['applicationChanged'] for x in w565_cells)==1 and sum(x['held'] for x in w565_cells)==40,'prior W565 update/hold counts')
    for x in w565_cells:
        sid,loc=x['sourceId'],x['locale']; idx=ids.index(sid)
        need(x['priorWindow']=='W565-W584' and x['catalogZeroBasedIndex']==idx and 565<=idx<=584 and loc in LOCALES,'prior W565 cell identity')
        need(x['sourceSha256']==sha(messages[sid]['source']) and x['currentTargetSha256']==sha(messages[sid]['translations'][loc]),'prior W565 target/source hash '+sid+'/'+loc)
        need(x['applicationCommit']=='89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac' and x['targetMatchesApplicationReadback'] is True and x['reattestedAtHead']==HEAD,'prior W565 app provenance '+sid+'/'+loc)
        need(bool(x['held'])==((sid,loc) in w565_holds) and (not x['held'] or not x['applicationChanged']),'prior W565 hold preservation '+sid+'/'+loc)
        for field in ('priorCandidateFreeCellEvidenceSha256','applicationReadbackCellEvidenceSha256'):
            need(re.fullmatch(r'[0-9a-f]{64}',x[field]) is not None,'prior W565 evidence row hash '+field)
    # Applied target hashes from W505 through W565 remain unchanged at the current exact head.
    applied=jl('prior-applied-cell-reattestation.jsonl'); need(len(applied)==49 and len({(x['sourceId'],x['locale']) for x in applied})==49,'prior applied cells count/uniqueness')
    need(dict(collections.Counter(x['priorWindow'] for x in applied))=={'W505-W524':28,'W525-W544':18,'W545-W564':2,'W565-W584':1},'prior applied window counts')
    for x in applied:
        sid,loc=x['sourceId'],x['locale']; idx=ids.index(sid)
        need(x['catalogZeroBasedIndex']==idx and loc in LOCALES and x['sourceSha256']==sha(messages[sid]['source']),'prior applied source/position '+sid+'/'+loc)
        need(x['priorSelectedTargetSha256']==x['currentTargetSha256']==sha(messages[sid]['translations'][loc]) and x['targetUnchanged'] is True and x['reattestedAtHead']==HEAD,'prior applied target hash '+sid+'/'+loc)
        if x['priorWindow']=='W545-W564':
            w=wmap[(sid,loc)]; need(w['applicationChanged'] and w['currentTargetSha256']==x['priorSelectedTargetSha256'] and x['applicationCommit']=='2a921d8280487f6d172616719f32e3dced243d83','W545 applied-cell linkage '+sid+'/'+loc)
        elif x['priorWindow']=='W565-W584':
            w=w565_map[(sid,loc)]; need(w['applicationChanged'] and w['currentTargetSha256']==x['priorSelectedTargetSha256'] and x['applicationCommit']=='89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac','W565 applied-cell linkage '+sid+'/'+loc)
        elif x['priorWindow']=='W525-W544':
            need(x['applicationCommit']=='63224167b0f89978a68977a7996bd06724d06129','W525 applied-cell commit '+sid+'/'+loc)
        else: need(x['applicationCommit']=='b248261d5aaa33ec7247023b85d666ed7fc89309','W505 applied-cell commit '+sid+'/'+loc)
        need(re.fullmatch(r'[0-9a-f]{64}',x['priorAppliedEvidenceSha256']) is not None,'prior applied evidence hash '+sid+'/'+loc)
    aps=j('prior-applied-cell-reattestation-summary.json'); need(aps['reattestedCellCount']==49 and aps['changedCells']==0 and aps['allSelectedTargetHashesMatchCurrentCatalog'] is True,'prior application summary')
    # Predecessor lineage, application readbacks, and live PR attestations.
    cont=j('continuity-reattestation.json')
    need(cont['result']=='PASS' and cont['priorWindow']=='W565-W584' and cont['priorHead']=='726db9138af2fc716056c7c36a9e842de04265e0' and cont['priorTree']=='6669dc9117dbbbe6587d4183ec5bd0184c87e983' and cont['currentHead']==HEAD and cont['currentTree']==TREE,'continuity pin')
    need(cont['priorSelectedSourceCount']==200 and cont['priorHoldCellCount']==604 and cont['priorAppliedCells']==49 and cont['priorW545CellReadbackRows']==240 and cont['priorW565CellReadbackRows']==240 and cont['priorW565ProductCommit']=='89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac','continuity counts/link')
    need(cont['priorCandidateFreePacketChecksumsVerified'] is True and cont['priorCrossPacketChecksumsVerified'] is True and cont['priorApplicationEvidenceChecksumsVerified'] is True and cont['priorW565ApplicationSummarySha256']==manifest['priorW565ApplicationSummarySha256'],'prior evidence checksum/link')
    need(manifest['priorW545ProductCommit']=='2a921d8280487f6d172616719f32e3dced243d83' and manifest['priorW545FullCellHashReadbackCount']==240 and manifest['priorW545ChangedAppliedCellCount']==2 and manifest['priorW505ToW545AppliedCellCount']==48,'manifest W545 continuity counts')
    need(manifest['priorW565ProductCommit']=='89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac' and manifest['priorW565FullCellHashReadbackCount']==240 and manifest['priorW565ChangedAppliedCellCount']==1 and manifest['priorW565TextFreeHoldCount']==40,'manifest W565 continuity counts')
    for label in ('before','after-candidate-free'):
        att=j('PR-attestation-'+label+'.json')
        need(att['result']=='PASS' and att['repository']=='snapetech-org/ROMarrNG' and att['pullRequest']==70 and att['state']=='OPEN' and att['draft'] is True and att['merged'] is False,'live PR state '+label)
        need(att['headRefName']==BRANCH and att['head']==HEAD and att['tree']==TREE and att['branchRefOid']==HEAD and att['pullRefOid']==HEAD and att['baseRefName']=='main','PR branch/pull pin '+label)
        need(att['checkRunCount']==len(att['checkRuns']) and att['checksRerun'] is False and att['deploymentCount']==0,'PR checks/deployment readback '+label)
        need(att['baseApiRefMismatch']==(att['baseApiSha']!=att['baseLiveRefOid']),'PR base discrepancy record '+label)
    before=j('PR-attestation-before.json'); after=j('PR-attestation-after-candidate-free.json')
    for field in ('state','draft','merged','headRefName','head','tree','branchRefOid','pullRefOid','baseRefName','baseApiSha','baseLiveRefOid','checkRuns','statusContexts','deploymentCount'):
        need(before.get(field)==after.get(field),'PR/check/deployment changed during extraction: '+field)
    callerless=sum(x['callerless'] for x in contexts)
    need(manifest['callerlessSourceCount']==callerless and manifest['callerlessCurrentTargetCellCount']==callerless*12 and manifest['directCallerRefCount']==sum(x['exactMatchCount'] for x in contexts),'current caller/hold counts')
    need(manifest['sourceCount']==20 and manifest['cellCount']==240 and manifest['priorSelectedSourceCount']==200 and manifest['priorHoldCellCount']==604 and manifest['priorAppliedSelectedCellCount']==49,'manifest final counts')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'sourceCount':20,'cellCount':240,'localeCount':12,'callerlessSources':callerless,'callerlessCells':callerless*12,'directCallerRefs':sum(x['exactMatchCount'] for x in contexts),'priorSelectedSources':len(prior),'priorHashOnlyHolds':len(holds),'priorW545ReadbackCells':len(window_cells),'priorW565ReadbackCells':len(w565_cells),'priorAppliedCells':len(applied),'selectedOrdinals':[585,604],'tokenMismatches':mismatch,'prState':'OPEN/DRAFT','deploymentCount':0},ensure_ascii=False,sort_keys=True))
if __name__=='__main__': main()
