#!/usr/bin/env python3
"""Portable exact-hash verifier for ROMarrNG PR #70 W525-W544 candidate-free input."""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, re, subprocess, sys
HERE=pathlib.Path(__file__).resolve().parent
HEAD='eda48333438591ecc67f829c50ef2d521f1e7a5e'
TREE='3db18e56d0c7ac08a564a6baff61eba25f0a01da'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
FORBIDDEN={'proposedTarget','proposedTargetSha256','selectedTarget','selectedTargetSha256','disposition','rationale','primaryDisposition','blindDisposition','decision'}
HOLD_TEXT={'source','sourceText','currentTarget','target','targetText','proposedTarget','selectedTarget','finalTarget'}
PH=re.compile(r'\{[^{}]+\}')
TAG=re.compile(r'<[^>]+>')
NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
def fail(m): raise SystemExit('FAIL: '+m)
def need(v,m):
    if not v: fail(m)
def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def j(n): return json.loads((HERE/n).read_text(encoding='utf-8'))
def jl(n): return [json.loads(x) for x in (HERE/n).read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])
def check_safe(x,where='input'):
    if isinstance(x,dict):
        bad=FORBIDDEN.intersection(x)
        need(not bad,f'candidate decisions/proposals present in {where}: {sorted(bad)}')
        for k,v in x.items(): check_safe(v,where+'.'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x): check_safe(v,f'{where}[{i}]')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=pathlib.Path,required=True,help='Git clone containing the pinned PR head and prior application commits')
    args=ap.parse_args(); repo=args.repo.resolve()
    need(repo.is_dir(),'repo path missing')
    manifest=j('manifest.json')
    need(manifest['candidateFree'] is True and manifest['proposedTargetsIncluded'] is False and manifest['reviewDecisionsIncluded'] is False,'candidate-free manifest flags')
    need((manifest['head'],manifest['tree'],manifest['window'])==(HEAD,TREE,'W525-W544'),'exact pin/window mismatch')
    need(manifest['sourceCount']==20 and manifest['localeCount']==12 and manifest['cellCount']==240,'manifest coverage mismatch')
    need(manifest['locales']==LOCALES,'locale order mismatch')
    # Verify file checksums and the exact input inventory.
    checks={}
    for raw in (HERE/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not raw.strip(): continue
        h,n=raw.split('  ',1); checks[n]=h
        p=(HERE/n).resolve()
        need(p.is_relative_to(HERE.resolve()) and p.is_file(),'unsafe/missing checksum path '+n)
        need(sha(p.read_bytes())==h,'input checksum mismatch: '+n)
    actual={p.name for p in HERE.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(set(checks)==actual,'checksum file coverage mismatch')
    files={row['path']:row for row in manifest['files']}
    need(set(files)==actual-{'manifest.json'},'input manifest inventory mismatch')
    for name,row in files.items():
        b=(HERE/name).read_bytes()
        need(len(b)==row['bytes'] and sha(b)==row['sha256'],'input manifest file mismatch: '+name)
    for n in actual:
        if n.endswith('.jsonl'): check_safe(jl(n),n)
        elif n.endswith('.json'): check_safe(j(n),n)
    need(git(repo,'rev-parse',HEAD).decode().strip()==HEAD,'pinned head commit missing')
    need(git(repo,'show','-s','--format=%T',HEAD).decode().strip()==TREE,'pinned head tree mismatch')
    need(git(repo,'rev-parse','b248261d5aaa33ec7247023b85d666ed7fc89309').decode().strip()=='b248261d5aaa33ec7247023b85d666ed7fc89309','prior W505 product commit missing')
    source_path='romarr/ui-labels.json'
    raw_catalog=git(repo,'show',f'{HEAD}:{source_path}')
    catalog_doc=json.loads(raw_catalog); messages=catalog_doc['messages']
    need(sha(raw_catalog)==manifest['catalogSha256'],'pinned catalog content hash mismatch')
    need(git(repo,'rev-parse',f'{HEAD}:{source_path}').decode().strip()==j('catalog-file-pins.json')['catalogGitBlob'],'pinned catalog blob mismatch')
    # Exact 1,836-message source registry/order and translation snapshot.
    inventory=jl('catalog-source-inventory.jsonl'); selected=jl('source-inventory-selection.jsonl')
    need(len(inventory)==1836 and list(messages)==[x['sourceId'] for x in inventory],'full catalog inventory/order mismatch')
    ids=list(messages)
    order_sha=sha('\n'.join(ids)+'\n')
    need(order_sha==manifest['catalogKeyOrderSha256']==j('catalog-file-pins.json')['catalogKeyOrderSha256'],'catalog key order hash mismatch')
    need([x['catalogZeroBasedIndex'] for x in inventory]==list(range(1836)),'catalog source index order mismatch')
    for i,row in enumerate(inventory):
        message=messages[row['sourceId']]; source=message['source']
        need(row['catalogZeroBasedIndex']==i and row['catalogOneBasedPosition']==i+1,'catalog source position mismatch')
        need(row['source']==source and row['sourceSha256']==sha(source)==message.get('sourceHash'),'catalog source text/hash mismatch '+row['sourceId'])
    need(len(selected)==20 and [x['catalogZeroBasedIndex'] for x in selected]==list(range(525,545)),'selected source positions')
    need(len({x['sourceId'] for x in selected})==20 and [x['sourceId'] for x in selected]==ids[525:545],'selected source IDs differ from catalog positions')
    boundary=jl('selection-boundary.jsonl')
    need([(x['catalogZeroBasedIndex'],x['role']) for x in boundary]==[(524,'catalog-before-selected-start'),(525,'selected-start'),(544,'selected-end'),(545,'catalog-after-selected-end')],'selection boundary mismatch')
    # Verify active registry and complete source/caller/runtime pins.
    registry_doc=j('source-queue.json'); registry=registry_doc['messages']
    registry_by={x['id']:x for x in registry}
    active_rank={sid:i+1 for i,sid in enumerate(sorted(registry_by))}
    need(len(registry)==479 and len(registry_by)==479 and manifest['activeUniqueSourceIdCount']==479,'active source registry count')
    snapshot=j('source-snapshot.json')
    need(snapshot=={x['id']:x['sourceHash'] for x in registry},'source snapshot/registry mismatch')
    need(sha(canon(snapshot))==manifest['sourceSnapshotSha256'],'source snapshot hash mismatch')
    need(sha('\n'.join(sorted(registry_by))+'\n')==manifest['sourceIdOrderSha256'],'source registry order hash mismatch')
    pins=j('source-file-pins.json')
    need(pins['head']==HEAD and pins['tree']==TREE,'source file pin header mismatch')
    pin_by={x['path']:x for x in pins['files']}
    need(len(pin_by)==len(pins['files']),'duplicate source file pins')
    for rel,pin in pin_by.items():
        b=git(repo,'show',f'{HEAD}:{rel}')
        need(len(b)==pin['bytes'] and sha(b)==pin['fileSha256'],'source/caller file hash mismatch '+rel)
        need(git(repo,'rev-parse',f'{HEAD}:{rel}').decode().strip()==pin['gitBlob'],'source/caller file blob mismatch '+rel)
    catalog_pins=j('catalog-file-pins.json')
    need(catalog_pins['commit']==HEAD and catalog_pins['tree']==TREE and catalog_pins['catalogPath']==source_path,'catalog file pin header')
    need(catalog_pins['catalogMessageCount']==1836 and catalog_pins['activeUniqueSourceIds']==479,'catalog/registry pin counts')
    need(catalog_pins['sourceSnapshotSha256']==sha(canon(snapshot)) and catalog_pins['sourceQueueSha256']==sha(git(repo,'show',f'{HEAD}:romarr/ui-source-messages.json')),'registry/snapshot content pins')
    # Verify exact caller evidence and exact context excerpts from the pinned source files.
    contexts=jl('source-contexts.jsonl'); caller_audit=j('caller-search-audit.json')
    need(len(contexts)==20 and {x['sourceId'] for x in contexts}=={x['sourceId'] for x in selected},'caller context coverage')
    need(caller_audit['head']==HEAD and caller_audit['tree']==TREE and caller_audit['queryCount']==20,'caller search audit pin')
    ctx={x['sourceId']:x for x in contexts}
    for c in contexts:
        core={k:v for k,v in c.items() if k!='contextSha256'}
        need(sha(canon(core))==c['contextSha256'],'caller context hash mismatch '+c['sourceId'])
        need(c['source']==messages[c['sourceId']]['source'] and c['sourceSha256']==sha(c['source']),'caller source hash mismatch '+c['sourceId'])
        need(c['callerless']==(len(c['callers'])==0) and c['exactMatchCount']==len(c['callers']),'callerless/count mismatch '+c['sourceId'])
        for ref in c['callers']:
            rel=ref['path']; need(rel in pin_by,'caller source file missing from pins '+rel)
            text=git(repo,'show',f'{HEAD}:{rel}').decode('utf-8'); lines=text.splitlines()
            line_no=ref['line']; need(1<=line_no<=len(lines),'caller line out of range '+rel)
            line_text=lines[line_no-1]
            lo=max(1,line_no-3); hi=min(len(lines),line_no+3)
            excerpt=[{'line':i,'text':lines[i-1]} for i in range(lo,hi+1)]
            need(line_text==ref['lineText'] and sha(line_text)==ref['lineSha256'],'caller line text/hash mismatch '+rel)
            need(excerpt==ref['excerpt'] and sha(canon(excerpt))==ref['excerptSha256'],'caller excerpt mismatch '+rel)
            need(pin_by[rel]['fileSha256']==ref['fileSha256'] and pin_by[rel]['gitBlob']==ref['gitBlob'],'caller file pin mismatch '+rel)
    # Exact 240-cell current target inventory and token/protected-literal checks.
    cells=jl('current-target-cells.jsonl')
    need(len(cells)==240 and len({(x['sourceId'],x['locale']) for x in cells})==240,'current target cell count/uniqueness')
    cellmap={(x['sourceId'],x['locale']):x for x in cells}
    need(set(cellmap)=={(x['sourceId'],loc) for x in selected for loc in LOCALES},'current target coverage')
    for c in cells:
        sid,loc=c['sourceId'],c['locale']; message=messages[sid]; source=message['source']; target=message.get('translations',{}).get(loc)
        need(isinstance(target,str) and c['currentTarget']==target and c['currentTargetSha256']==sha(target),'catalog target value/hash mismatch '+sid+'/'+loc)
        need(c['source']==source and c['sourceSha256']==sha(source),'cell source mismatch '+sid+'/'+loc)
        need(c['callerContextSha256']==ctx[sid]['contextSha256'] and c['containsCandidate'] is False,'cell caller/candidate marker mismatch '+sid+'/'+loc)
        expected_refs=[{k:r[k] for k in ('path','line','lineSha256','excerptSha256','fileSha256','gitBlob')} for r in ctx[sid]['callers']]
        need(c['callerRefs']==expected_refs,'cell caller reference mismatch '+sid+'/'+loc)
        need(collections.Counter(PH.findall(source))==collections.Counter(c['sourcePlaceholderTokens'])==collections.Counter(PH.findall(target))==collections.Counter(c['currentPlaceholderTokens']),'placeholder mismatch '+sid+'/'+loc)
        need(collections.Counter(TAG.findall(source))==collections.Counter(c['sourceMarkupTags'])==collections.Counter(TAG.findall(target))==collections.Counter(c['currentMarkupTags']),'markup mismatch '+sid+'/'+loc)
        src_nums=collections.Counter(NUM.findall(source)); tgt_nums=collections.Counter(NUM.findall(target))
        need(src_nums==collections.Counter(c['sourceNumericTokens']) and tgt_nums==collections.Counter(c['currentNumericTokens']),'numeric evidence mismatch '+sid+'/'+loc)
        extras=list((tgt_nums-src_nums).elements())
        zero_equiv=bool(c.get('numericPresentationEquivalent')) and c.get('sourceNumericWords')==['Zero'] and not src_nums and extras==['0']
        need(not (src_nums-tgt_nums) and (not extras or zero_equiv) and c['numericTokensPreserved'] is True,'numeric token mismatch '+sid+'/'+loc)
        need(all(t in target for t in c['sourceProtectedLiterals']) and c['protectedLiteralsPreserved'] is True and not c['missingProtectedLiterals'],'protected literal mismatch '+sid+'/'+loc)
        need(c['catalogTranslationHash']==message.get('translationHashes',{}).get(loc),'translation hash metadata mismatch '+sid+'/'+loc)
    mismatch=j('current-target-token-mismatches.json')
    need(mismatch=={'placeholder':0,'markup':0,'numeric':0,'numericPresentationDifferences':0,'protectedLiteral':0,'missingTarget':0},'token mismatch summary')
    # Historical selected source IDs, held cells, and W505 applied cell hashes remain hash-only and exact.
    prior=jl('prior-selection-reattestation.jsonl'); holds=jl('prior-hold-reattestation.jsonl'); applied=jl('prior-applied-cell-reattestation.jsonl')
    need(len(prior)==140 and len({x['sourceId'] for x in prior})==140,'prior selection count/uniqueness')
    for row in prior:
        sid=row['sourceId']; idx=row['catalogZeroBasedIndex']
        need(0<=idx<1836 and ids[idx]==sid and sha(messages[sid]['source'])==row['priorSourceSha256']==row['currentSourceSha256'],'prior selection source/position mismatch '+sid)
        need(row['selectionPositionMatches'] is True and row['sourceHashMatches'] is True,'prior source reattestation status '+sid)
        need(isinstance(row['registryMembershipAndHashMatch'],bool),'prior registry lineage status type '+sid)
    need(len(holds)==540 and len({(x['sourceId'],x['locale']) for x in holds})==540,'prior hold count/uniqueness')
    for h in holds:
        need(not (HOLD_TEXT & set(h)),'prior hold contains source/target text')
        sid,loc=h['sourceId'],h['locale']; idx=h['position']
        need(sid in messages and loc in LOCALES and h['sourceSha256']==sha(messages[sid]['source']),'prior hold source/locale mismatch')
        need(sha(messages[sid]['translations'][loc])==h['priorTargetSha256']==h['currentTargetSha256'],'prior held target hash changed '+sid+'/'+loc)
        need(h['sourceMatchesCurrentCatalog'] and h['selectionPositionMatches'] and h['targetUnchanged'] and h['reattestedAtHead']==HEAD,'prior hold reattestation status')
        if 'catalog insertion index' in h['selectionPositionBasis']:
            need(idx==ids.index(sid),'prior hold catalog position mismatch '+sid)
        else:
            need(idx==active_rank.get(sid),'prior hold active registry position mismatch '+sid)
    need(len(applied)==28 and len({(x['sourceId'],x['locale']) for x in applied})==28,'prior applied-cell count/uniqueness')
    for x in applied:
        sid,loc=x['sourceId'],x['locale']
        need(x['priorWindow']=='W505-W524' and x['applicationCommit']=='b248261d5aaa33ec7247023b85d666ed7fc89309','prior applied cell provenance')
        need(x['catalogZeroBasedIndex']==ids.index(sid) and x['sourceSha256']==sha(messages[sid]['source']),'prior applied source/position hash')
        need(sha(messages[sid]['translations'][loc])==x['priorSelectedTargetSha256']==x['currentTargetSha256'],'prior selected target changed '+sid+'/'+loc)
        need(x['targetUnchanged'] is True and x['reattestedAtHead']==HEAD,'prior applied target status')
    prior_summary=j('prior-selection-reattestation-summary.json'); hold_summary=j('prior-hold-reattestation-summary.json'); app_summary=j('prior-applied-cell-reattestation-summary.json')
    need(prior_summary['reattestedSelectedSourceCount']==140 and prior_summary['allPriorSelectionsMatchCurrentCatalogAndRegistry'] is True,'prior selection summary')
    need(hold_summary['reattestedCellCount']==540 and hold_summary['currentTargetChangedCells']==0,'prior hold summary')
    need(app_summary['reattestedCellCount']==28 and app_summary['changedCells']==0 and app_summary['allSelectedTargetHashesMatchCurrentCatalog'] is True,'prior applied summary')
    continuity=j('continuity-reattestation.json')
    need(continuity['result']=='PASS' and continuity['priorWindow']=='W505-W524' and continuity['currentHead']==HEAD and continuity['currentTree']==TREE,'prior continuity pin')
    need(continuity['priorSelectedSourceCount']==140 and continuity['priorHoldCellCount']==540 and continuity['priorAppliedCells']==28 and continuity['priorAppliedCellsChanged']==0,'prior continuity counts')
    need(continuity['sourceRegistrySha256']==manifest['sourceQueueSha256'] and continuity['sourceSnapshotSha256']==manifest['sourceSnapshotSha256'] and continuity['sourceIdOrderSha256']==manifest['sourceIdOrderSha256'],'prior registry continuity hash mismatch')
    att=j('PR-attestation-before.json')
    need(att['result']=='PASS' and att['state']=='OPEN' and att['draft'] is True and att['merged'] is False,'live PR state attestation')
    need(att['headRefName']=='task/localization-translation-review-20261030' and att['head']==HEAD and att['tree']==TREE and att['branchRefOid']==HEAD and att['pullRefOid']==HEAD,'live PR head/pull ref attestation')
    need(att['baseRefName']=='main' and att['baseApiSha']=='bcd1eb41b5cdf8202acb5cf8e365e14761b743b5' and att['baseLiveRefOid']=='65d8747e3a068473396227bae5e85ddc71c7d4d8' and att['baseApiRefMismatch'] is True,'base API/live-ref discrepancy attestation')
    merge=git(repo,'show','-s','--format=%P',att['pullMergeRefOid']).decode().strip().split()
    need(merge==[att['pullMergeFirstParent'],HEAD] and merge[0]==att['baseLiveRefOid'],'PR merge ref parent attestation')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'sourceCount':20,'cellCount':240,'localeCount':12,'callerlessSources':sum(x['callerless'] for x in contexts),'priorSelectedSources':len(prior),'priorHashOnlyHoldCells':len(holds),'priorAppliedCells':len(applied),'tokenMismatches':mismatch,'baseApiRefMismatch':att['baseApiRefMismatch']},ensure_ascii=False,sort_keys=True))
if __name__=='__main__': main()
