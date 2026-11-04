#!/usr/bin/env python3
"""Build W605-W624 candidate-free input from the exact pinned PR head."""
from __future__ import annotations
import collections, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
TASK=OUT.parent
INPUT=OUT/'candidate-free'/'input'
WORKTREE=Path('/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w585-604-apply-20261104')
PREV=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w585-604-current-candidate-free-20261104')
PREV_SOURCE=Path('/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w585-604-current-source')
PREV_INPUT=PREV/'candidate-free'/'input'
W585_APP=WORKTREE/'docs/pr-evidence/pr70-localization-2026-11-04/window-0585-0604-cross-adjudication'
HEAD='872905926887840025ba4c3f17151b96f8d3e6e2'
TREE='d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4'
PREV_HEAD='01da053f0e6a47e7184fb86da77f66b7b6719653'
PREV_TREE='dcb9c1766831e217ffca7fb77068b97c33b9524e'
W585_PRODUCT='d44e61d9960c788412da0fadbb8b67744b70e404'
EVIDENCE_HEAD=HEAD
BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight']
PH=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')

def sha(b):
    if isinstance(b,str): b=b.encode()
    return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def jl(p): return [json.loads(s) for s in Path(p).read_text(encoding='utf-8').splitlines() if s.strip()]
def dumpj(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def dumpl(p,x): Path(p).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in x),encoding='utf-8')
def git(*args): return subprocess.check_output(['git','-C',str(WORKTREE),*args],text=True).strip()
def blob(rel): return git('rev-parse',f'{HEAD}:{rel}')
def file(rel): return WORKTREE/rel
def gh(*args): return json.loads(subprocess.check_output(['gh',*args],text=True,cwd=WORKTREE))

def attestation():
    api=gh('api','repos/snapetech-org/ROMarrNG/pulls/70')
    raw=git('ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head','refs/heads/main')
    refs={line.split('\t')[1]:line.split('\t')[0] for line in raw.splitlines() if line.strip()}
    body=api.get('body') or ''
    result={'result':'PASS','attestedAtUtc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'repository':'snapetech-org/ROMarrNG','pullRequest':70,'pullRequestUrl':api['html_url'],'state':api['state'].upper(),'draft':api['draft'],'merged':api['merged'],'headRefName':api['head']['ref'],'head':api['head']['sha'],'tree':git('rev-parse',f'{HEAD}^{{tree}}'),'branchRefOid':refs.get(f'refs/heads/{BRANCH}'),'pullRefOid':refs.get('refs/pull/70/head'),'baseRefName':api['base']['ref'],'baseApiSha':api['base']['sha'],'baseLiveRefOid':refs.get('refs/heads/main'),'baseApiRefMismatch':api['base']['sha']!=refs.get('refs/heads/main'),'bodySha256':sha(body),'bodyBytes':len(body.encode()),'checksRerun':False}
    if (result['state'],result['draft'],result['merged'],result['headRefName'],result['head'],result['tree'],result['branchRefOid'],result['pullRefOid'],result['baseRefName'])!=('OPEN',True,False,BRANCH,HEAD,TREE,HEAD,HEAD,'main'):
        raise SystemExit('FAIL: live PR API/branch/pull ref alignment: '+repr(result))
    marker='<!-- romarrng-pr70-w585-604-application-20261104 -->'
    if marker not in body or EVIDENCE_HEAD not in body or 'complete W585–W604 evidence packet' not in body:
        raise SystemExit('FAIL: W585 milestone/evidence link missing in current PR body')
    return result

if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all') or git('branch','--show-current'):
    raise SystemExit('FAIL: pinned source worktree is not exact, clean, detached')
if INPUT.exists() and any(INPUT.iterdir()):
    raise SystemExit('FAIL: candidate-free input already contains files')
att_before=attestation()
# Verify W585 candidate-free and completed application packets at their exact source heads.
for d in (PREV_INPUT,W585_APP):
    subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=d,check=True,stdout=subprocess.DEVNULL)
subprocess.run(['python3',str(PREV/'verify_bundle.py'),'--repo',str(PREV_SOURCE)],check=True,stdout=subprocess.DEVNULL)
subprocess.run(['python3',str(W585_APP/'verify_application.py'),'--repo',str(WORKTREE)],check=True,stdout=subprocess.DEVNULL)
prev_manifest=json.loads((PREV_INPUT/'manifest.json').read_text())
summary=json.loads((W585_APP/'application/application-summary.json').read_text())
pins=json.loads((W585_APP/'application/catalog-pins.json').read_text())
if (prev_manifest['head'],prev_manifest['tree'],prev_manifest['window'])!=(PREV_HEAD,PREV_TREE,'W585-W604'):
    raise SystemExit('FAIL: W585 candidate-free pin/window')
if (summary['window'],summary['productCommit'],summary['productParent'],summary['productTree'],summary['readbackCellCount'],summary['changedCellCount'],summary['callerlessHashOnlyHoldCount'])!=('W585-W604',W585_PRODUCT,PREV_HEAD,'2bbb5821bf6beb2b06f689ba0e3c87c6136d42ef',240,22,24):
    raise SystemExit('FAIL: W585 application summary')
if (pins['preHead'],pins['preTree'])!=(PREV_HEAD,PREV_TREE):
    raise SystemExit('FAIL: W585 catalog pre-pin')
if git('rev-parse',f'{W585_PRODUCT}^')!=PREV_HEAD or git('rev-parse',f'{W585_PRODUCT}^{{tree}}')!=summary['productTree'] or git('diff-tree','--no-commit-id','--name-only','-r',W585_PRODUCT).splitlines()!=['romarr/ui-labels.json']:
    raise SystemExit('FAIL: W585 product commit parent/tree/scope')
if git('rev-parse',f'{HEAD}^')!='c310ac5c8acef531841d905c28010ac40011dd43':
    raise SystemExit('FAIL: W585 evidence-completion commit parent')
evidence_root='docs/pr-evidence/pr70-localization-2026-11-04/window-0585-0604-cross-adjudication'
tracked=git('ls-tree','-r','--name-only',HEAD,'--',evidence_root).splitlines()
local=sorted(p.relative_to(WORKTREE/evidence_root).as_posix() for p in (WORKTREE/evidence_root).rglob('*') if p.is_file())
if sorted(p[len(evidence_root)+1:] for p in tracked)!=local or len(local)!=109:
    raise SystemExit('FAIL: W585 full evidence file set is not tracked at final head')

OLD=PREV_INPUT
prior_selection=jl(OLD/'prior-selection-reattestation.jsonl')
w585_selected=jl(OLD/'source-inventory-selection.jsonl')
prior_holds=jl(OLD/'prior-hold-reattestation.jsonl')
prior_applied=jl(OLD/'prior-applied-cell-reattestation.jsonl')
w585_before_cells=jl(OLD/'current-target-cells.jsonl')
w585_readback=jl(W585_APP/'application/application-readback.jsonl')
w585_holds=jl(W585_APP/'application/holds.jsonl')
w585_changed=jl(W585_APP/'application/selected-applied.jsonl')
if tuple(map(len,(prior_selection,w585_selected,prior_holds,prior_applied,w585_before_cells,w585_readback,w585_holds,w585_changed)))!=(200,20,604,49,240,240,24,22):
    raise SystemExit('FAIL: W585 lineage/readback counts')

catalog_path='romarr/ui-labels.json'; catalog_bytes=file(catalog_path).read_bytes(); doc=json.loads(catalog_bytes); messages=doc['messages']; ids=list(messages)
if len(messages)!=1836 or sha('\n'.join(ids)+'\n')!='40c18afaf80695667f7022e59141a2793799fde35527d608eedb30f8ef4ad055':
    raise SystemExit('FAIL: catalog message count/key order')
if sha(catalog_bytes)!=pins['postCatalogSha256'] or blob(catalog_path)!=pins['postCatalogGitBlob']:
    raise SystemExit('FAIL: catalog does not match W585 application readback')
registry_path='romarr/ui-source-messages.json'; snapshot_path='romarr/ui-source-snapshot.json'
registry=json.loads(file(registry_path).read_text())['messages']; reg={r['id']:r for r in registry}
source_snapshot={r['id']:r['sourceHash'] for r in registry}; raw_snapshot=json.loads(file(snapshot_path).read_text())
if len(registry)!=479 or len(reg)!=479 or len(source_snapshot)!=479 or any(raw_snapshot.get(k)!=v for k,v in source_snapshot.items()):
    raise SystemExit('FAIL: source registry/snapshot consistency')
source_snapshot_sha=sha(canon(source_snapshot)); source_queue_sha=sha(file(registry_path).read_bytes()); active_order_sha=sha('\n'.join(sorted(reg))+'\n')
if source_snapshot_sha!=prev_manifest['sourceSnapshotSha256'] or source_queue_sha!=prev_manifest['sourceQueueSha256'] or active_order_sha!=prev_manifest['sourceIdOrderSha256']:
    raise SystemExit('FAIL: source registry/snapshot changed')
active_rank={sid:i for i,sid in enumerate(sorted(reg),1)}

# Reattest all earlier selected source IDs, then append the 20 W585 selections.
selection_rows=[]
for r in prior_selection:
    sid=r['sourceId']; idx=r['catalogZeroBasedIndex']; m=messages.get(sid)
    if m is None or ids[idx]!=sid or sha(m['source'])!=r['priorSourceSha256'] or sha(m['source'])!=r['currentSourceSha256'] or m.get('sourceHash')!=sha(m['source']):
        raise SystemExit('FAIL: historical selected source hash/order changed')
    selection_rows.append({'priorWindow':r['priorWindow'],'position':r.get('position',idx),'catalogZeroBasedIndex':idx,'sourceId':sid,'priorSourceSha256':r['priorSourceSha256'],'currentSourceSha256':sha(m['source']),'selectionPositionMatches':True,'sourceHashMatches':True,'registryMembershipAndHashMatch':(sid in reg)==bool(r.get('registryMembershipAndHashMatch',sid in reg)),'priorSelectionEvidenceSha256':sha(canon(r)),'reattestedAtHead':HEAD})
for r in w585_selected:
    sid=r['sourceId']; idx=r['catalogZeroBasedIndex']; m=messages[sid]
    if idx not in range(585,605) or ids[idx]!=sid or sha(m['source'])!=r['sourceSha256'] or m.get('sourceHash')!=sha(m['source']):
        raise SystemExit('FAIL: W585 selected source hash/order changed')
    selection_rows.append({'priorWindow':'W585-W604','position':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'priorSourceSha256':r['sourceSha256'],'currentSourceSha256':sha(m['source']),'selectionPositionMatches':True,'sourceHashMatches':True,'registryMembershipAndHashMatch':sid in reg,'priorSelectionEvidenceSha256':sha(canon(r)),'reattestedAtHead':HEAD})
if len(selection_rows)!=220 or len({x['sourceId'] for x in selection_rows})!=220:
    raise SystemExit('FAIL: prior selected source count/uniqueness')

# Reattest 604 prior holds and add 24 callerless W585 hash-only holds.
hold_rows=[]
for h in prior_holds:
    sid=h['sourceId']; loc=h['locale']; idx=ids.index(sid); m=messages[sid]; basis=h.get('selectionPositionBasis','')
    pos_ok=(idx==h['position']) if 'catalog insertion index' in basis else active_rank.get(sid)==h['position']
    cur=sha(m['translations'][loc])
    if sha(m['source'])!=h['sourceSha256'] or cur!=h['priorTargetSha256'] or not pos_ok:
        raise SystemExit('FAIL: prior held source/position/current target changed')
    hold_rows.append({'window':h['window'],'position':h['position'],'selectionPositionBasis':basis,'sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'priorTargetSha256':h['priorTargetSha256'],'currentTargetSha256':cur,'sourceMatchesCurrentCatalog':True,'selectionPositionMatches':True,'targetUnchanged':True,'priorHoldEvidenceSha256':h.get('priorHoldEvidenceSha256',sha(canon(h))),'reattestedAtHead':HEAD})
w585_hold_ids=set()
for h in w585_holds:
    if any(k in h for k in ('source','sourceText','currentTarget','target','targetText','proposedTarget','selectedTarget','finalTarget','sourceId')) or h.get('callerRefCount')!=0:
        raise SystemExit('FAIL: W585 hold row is not callerless/hash-only')
    idx=h['position']; loc=h['locale']; sid=ids[idx]; m=messages[sid]
    if idx not in range(585,605) or loc not in LOCALES or sha(m['source'])!=h['sourceSha256'] or sha(m['translations'][loc])!=h['currentTargetSha256']:
        raise SystemExit('FAIL: W585 callerless hold changed')
    if (sid,loc) in w585_hold_ids:
        raise SystemExit('FAIL: duplicate W585 hold')
    w585_hold_ids.add((sid,loc))
    hold_rows.append({'window':'W585-W604','position':idx,'selectionPositionBasis':'catalog insertion index (zero-based)','sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'priorTargetSha256':h['currentTargetSha256'],'currentTargetSha256':h['currentTargetSha256'],'sourceMatchesCurrentCatalog':True,'selectionPositionMatches':True,'targetUnchanged':True,'callerless':True,'holdReasonSha256':h['holdReasonSha256'],'priorHoldEvidenceSha256':sha(canon(h)),'reattestedAtHead':HEAD})
if len(hold_rows)!=628 or len({(x['sourceId'],x['locale']) for x in hold_rows})!=628:
    raise SystemExit('FAIL: prior hold count/uniqueness')

# Reattest 49 previous applications and add 22 W585 selected target changes.
applied_rows=[]
for x in prior_applied:
    sid=x['sourceId']; loc=x['locale']; m=messages[sid]; cur=sha(m['translations'][loc])
    if sha(m['source'])!=x['sourceSha256'] or cur!=x['priorSelectedTargetSha256'] or cur!=x['currentTargetSha256']:
        raise SystemExit('FAIL: historical applied target changed')
    applied_rows.append({'priorWindow':x['priorWindow'],'catalogZeroBasedIndex':ids.index(sid),'sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'priorSelectedTargetSha256':cur,'currentTargetSha256':cur,'targetUnchanged':True,'applicationCommit':x['applicationCommit'],'priorAppliedEvidenceSha256':x.get('priorAppliedEvidenceSha256',sha(canon(x))),'reattestedAtHead':HEAD})
before_map={(x['sourceId'],x['locale']):x for x in w585_before_cells}
w585_changed_ids=set()
for x in w585_changed:
    sid=x['sourceId']; loc=x['locale']; idx=x['position']; m=messages[sid]; before=before_map[(sid,loc)]; cur=sha(m['translations'][loc])
    if idx not in range(585,605) or ids[idx]!=sid or before['currentTargetSha256']!=x['beforeTargetSha256'] or sha(m['source'])!=x['sourceSha256'] or cur!=x['afterTargetSha256']:
        raise SystemExit('FAIL: W585 applied target/readback mismatch')
    w585_changed_ids.add((sid,loc))
    applied_rows.append({'priorWindow':'W585-W604','catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'priorSelectedTargetSha256':cur,'currentTargetSha256':cur,'targetUnchanged':True,'applicationCommit':W585_PRODUCT,'priorAppliedEvidenceSha256':sha(canon(x)),'beforeTargetSha256':x['beforeTargetSha256'],'reattestedAtHead':HEAD})
if len(w585_changed_ids)!=22 or len(applied_rows)!=71 or len({(x['sourceId'],x['locale']) for x in applied_rows})!=71 or w585_changed_ids & w585_hold_ids:
    raise SystemExit('FAIL: applied target lineage count/uniqueness')

# Reattest full previous W545/W565 readbacks and the complete W585 240-cell application readback.
def reattest(rows,win):
    out=[]
    if len(rows)!=240: raise SystemExit('FAIL: '+win+' readback count')
    for x in rows:
        m=messages[x['sourceId']]; loc=x['locale']; cur=sha(m['translations'][loc])
        if sha(m['source'])!=x['sourceSha256'] or cur!=x['currentTargetSha256']:
            raise SystemExit('FAIL: '+win+' current source/target hash')
        out.append({**x,'currentTargetSha256':cur,'targetMatchesApplicationReadback':True,'reattestedAtHead':HEAD})
    return out
w545_rows=reattest(jl(OLD/'prior-window-cell-hash-reattestation.jsonl'),'W545-W564')
w565_rows=reattest(jl(OLD/'prior-w565-window-cell-hash-reattestation.jsonl'),'W565-W584')
w585_rows=[]
for rb in w585_readback:
    idx=rb['position']; sid=rb.get('sourceId') or ids[idx]; loc=rb['locale']; m=messages[sid]; before=before_map[(sid,loc)]; cur=sha(m['translations'][loc])
    if idx not in range(585,605) or ids[idx]!=sid or before['currentTargetSha256']!=rb['beforeTargetSha256'] or sha(m['source'])!=rb['sourceSha256'] or cur!=rb['afterTargetSha256']:
        raise SystemExit('FAIL: W585 240-cell readback mismatch')
    held=(sid,loc) in w585_hold_ids; changed=(sid,loc) in w585_changed_ids
    if held and rb['changed'] or changed!=(rb['changed'] is True):
        raise SystemExit('FAIL: W585 hold/change readback mismatch')
    w585_rows.append({'priorWindow':'W585-W604','catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'beforeTargetSha256':rb['beforeTargetSha256'],'currentTargetSha256':cur,'applicationChanged':bool(rb['changed']),'held':held,'applicationCommit':W585_PRODUCT,'targetMatchesApplicationReadback':True,'priorCandidateFreeCellEvidenceSha256':sha(canon(before)),'applicationReadbackCellEvidenceSha256':sha(canon(rb)),'reattestedAtHead':HEAD})
if (len(w585_rows),sum(x['applicationChanged'] for x in w585_rows),sum(x['held'] for x in w585_rows))!=(240,22,24):
    raise SystemExit('FAIL: W585 readback totals')

# Source/caller files are unchanged from the fresh W585 source snapshot.
oldpins=json.loads((OLD/'catalog-file-pins.json').read_text())['sourceCallerFilePins']
file_pins=[]
for rel in sorted(set(oldpins)|{registry_path,snapshot_path}):
    data=file(rel).read_bytes(); current={'fileSha256':sha(data),'gitBlob':blob(rel)}
    file_pins.append({'path':rel,'fileSha256':current['fileSha256'],'gitBlob':current['gitBlob'],'bytes':len(data)})
    if rel in oldpins and current!={'fileSha256':oldpins[rel]['fileSha256'],'gitBlob':oldpins[rel]['gitBlob']}:
        raise SystemExit('FAIL: source/caller pin drift: '+rel)

# Select the next 20 keys by exact catalog insertion order.
selected=[]
for idx in range(605,625):
    sid=ids[idx]; m=messages[sid]; sh=sha(m['source'])
    if m.get('sourceHash')!=sh: raise SystemExit('FAIL: sourceHash field mismatch')
    selected.append({'position':idx,'catalogZeroBasedIndex':idx,'catalogOneBasedPosition':idx+1,'sourceId':sid,'source':m['source'],'sourceSha256':sh,'activeSourceRegistry':sid in reg,'activeSourceRank':active_rank.get(sid),'registryLocations':reg.get(sid,{}).get('locations',[])})
if len(selected)!=20 or len({x['sourceId'] for x in selected})!=20 or {x['sourceId'] for x in selection_rows}&{x['sourceId'] for x in selected}:
    raise SystemExit('FAIL: W605 selection count/overlap')
boundary=[]
for idx,role in ((604,'catalog-before-selected-start'),(605,'selected-start'),(624,'selected-end'),(625,'catalog-after-selected-end')):
    sid=ids[idx]; m=messages[sid]
    boundary.append({'position':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'source':m['source'],'sourceSha256':sha(m['source']),'role':role})

# Exact-source/caller searches over tracked production source files only.
tracked=subprocess.check_output(['git','-C',str(WORKTREE),'ls-files','-z','--','romarr']).split(b'\0')
paths=[]
for raw in tracked:
    if not raw: continue
    rel=raw.decode(); p=WORKTREE/rel; parts=rel.lower().split('/')
    if p.suffix.lower() not in ('.py','.js','.html','.jinja','.jinja2','.css','.ts','.tsx') or any(x in parts for x in ('test','tests','__pycache__')) or p.name.startswith('test_') or p.name.endswith('_test.py'):
        continue
    paths.append(rel)
files={}
for rel in paths:
    b=file(rel).read_bytes()
    try: text=b.decode()
    except UnicodeDecodeError: text=b.decode('utf-8','replace')
    files[rel]=(text,b,blob(rel))
def context(item):
    src=item['source']; sid=item['sourceId']; matches=[]
    variants=list(dict.fromkeys([json.dumps(src,ensure_ascii=False),repr(src),'"'+src+'"',chr(39)+src+chr(39),chr(96)+src+chr(96)]))
    for rel,(text,b,git_blob) in files.items():
        occ={}; lines=text.splitlines()
        for literal in variants:
            start=0
            while True:
                at=text.find(literal,start)
                if at<0: break
                occ.setdefault(at,'exact quoted source literal'); start=at+max(1,len(literal))
        start=0
        while True:
            at=text.find(sid,start)
            if at<0: break
            occ.setdefault(at,'exact source ID reference'); start=at+len(sid)
        for hit in re.finditer(r'>[ \t]*'+re.escape(src)+r'[ \t]*<',text):
            occ.setdefault(hit.start(),'exact HTML text node')
        for at,kind in sorted(occ.items()):
            line=text.count('\n',0,at)+1; lo=max(1,line-3); hi=min(len(lines),line+3)
            excerpt=[{'line':i,'text':lines[i-1]} for i in range(lo,hi+1)]
            matches.append({'path':rel,'line':line,'lineText':lines[line-1] if line<=len(lines) else '', 'lineSha256':sha(lines[line-1] if line<=len(lines) else ''),'excerpt':excerpt,'excerptSha256':sha(canon(excerpt)),'fileSha256':sha(b),'gitBlob':git_blob,'matchKind':kind})
    matches.sort(key=lambda x:(x['path'],x['line'],x['matchKind']))
    core={'sourceId':sid,'source':src,'sourceSha256':item['sourceSha256'],'searchMethod':'exact quoted source literal, exact source ID, or exact HTML text-node search in tracked production code; tests/docs/catalog files excluded','productionFilesSearched':len(files),'exactMatchCount':len(matches),'callerless':not matches,'callers':matches}
    return {**core,'contextSha256':sha(canon(core))}
contexts=[context(x) for x in selected]; ctxmap={x['sourceId']:x for x in contexts}

def protected(source):
    out=[]
    for t in PROTECTED:
        if re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',source): out.append(t)
    if re.search(r'(?<![A-Za-z0-9])DATs?(?![A-Za-z0-9])',source) and 'DAT' not in out: out.append('DAT')
    return sorted(set(out))
def tokens(s): return {'placeholders':PH.findall(s),'markup':TAG.findall(s),'numbers':NUM.findall(s),'protectedLiterals':protected(s)}

inventory=[]
for idx,sid in enumerate(ids):
    m=messages[sid]; src=m['source']; t=tokens(src); sh=sha(src)
    if m.get('sourceHash')!=sh: raise SystemExit('FAIL: sourceHash mismatch: '+sid)
    inventory.append({'catalogZeroBasedIndex':idx,'catalogOneBasedPosition':idx+1,'sourceId':sid,'source':src,'sourceSha256':sh,'activeSourceRegistry':sid in reg,'activeSourceRank':active_rank.get(sid),'registryLocations':reg.get(sid,{}).get('locations',[]),'sourcePlaceholderTokens':t['placeholders'],'sourceMarkupTags':t['markup'],'sourceNumericTokens':t['numbers'],'sourceNumericWords':['Zero'] if re.search(r'\bzero\b',src,re.I) else [],'sourceProtectedLiterals':t['protectedLiterals']})
cells=[]; mismatch={'placeholder':0,'markup':0,'numeric':0,'numericPresentationDifferences':0,'protectedLiteral':0,'missingTarget':0}
for item in selected:
    sid=item['sourceId']; m=messages[sid]; src=m['source']; st=tokens(src); ctx=ctxmap[sid]
    caller_refs=[{'path':r['path'],'line':r['line'],'lineSha256':r['lineSha256'],'excerptSha256':r['excerptSha256'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob']} for r in ctx['callers']]
    for loc in LOCALES:
        target=m.get('translations',{}).get(loc)
        if not isinstance(target,str): mismatch['missingTarget']+=1; target=''
        tt=tokens(target); ph_ok=collections.Counter(st['placeholders'])==collections.Counter(tt['placeholders']); tag_ok=collections.Counter(st['markup'])==collections.Counter(tt['markup'])
        srcnums=collections.Counter(st['numbers']); tgtnums=collections.Counter(tt['numbers']); extra=list((tgtnums-srcnums).elements())
        numeric_presentation=bool(re.search(r'\bzero\b',src,re.I) and not st['numbers'] and extra==['0'])
        num_ok=not(srcnums-tgtnums) and (not extra or numeric_presentation)
        missing=[x for x in st['protectedLiterals'] if x not in target]
        mismatch['placeholder']+=not ph_ok; mismatch['markup']+=not tag_ok; mismatch['numeric']+=not num_ok; mismatch['numericPresentationDifferences']+=numeric_presentation; mismatch['protectedLiteral']+=bool(missing)
        cells.append({'position':item['position'],'catalogZeroBasedIndex':item['catalogZeroBasedIndex'],'catalogOneBasedPosition':item['catalogOneBasedPosition'],'sourceId':sid,'source':src,'sourceSha256':item['sourceSha256'],'locale':loc,'currentTarget':target,'currentTargetSha256':sha(target),'catalogTranslationHash':m.get('translationHashes',{}).get(loc),'translationStatus':m.get('translationStatus',{}).get(loc),'callerContextSha256':ctx['contextSha256'],'callerRefs':caller_refs,'sourcePlaceholderTokens':st['placeholders'],'currentPlaceholderTokens':tt['placeholders'],'placeholderMultisetMatches':ph_ok,'sourceMarkupTags':st['markup'],'currentMarkupTags':tt['markup'],'markupMatches':tag_ok,'sourceNumericTokens':st['numbers'],'sourceNumericWords':['Zero'] if re.search(r'\bzero\b',src,re.I) else [],'currentNumericTokens':tt['numbers'],'numericTokensPreserved':num_ok,'numericPresentationEquivalent':numeric_presentation,'sourceProtectedLiterals':st['protectedLiterals'],'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing,'containsCandidate':False})

catalog_sha=sha(catalog_bytes)
continuity={'result':'PASS','priorWindow':'W585-W604','priorHead':PREV_HEAD,'priorTree':PREV_TREE,'priorProductCommit':W585_PRODUCT,'priorEvidenceHead':EVIDENCE_HEAD,'currentHead':HEAD,'currentTree':TREE,'priorCandidateFreePacketChecksumsVerified':True,'priorW585ApplicationEvidenceChecksumsVerified':True,'priorSelectedSourceCount':len(selection_rows),'priorSelectedSourceCountUnchanged':True,'priorHoldCellCount':len(hold_rows),'priorHoldCellCountUnchanged':True,'priorHoldChangedCellCount':0,'priorAppliedCellCount':len(applied_rows),'priorAppliedCellCountUnchanged':True,'priorAppliedCellChangedCount':0,'priorW545ReadbackRows':len(w545_rows),'priorW565ReadbackRows':len(w565_rows),'priorW585ReadbackRows':len(w585_rows),'priorW585ChangedAppliedCells':sum(x['applicationChanged'] for x in w585_rows),'priorW585CallerlessHoldCells':sum(x['held'] for x in w585_rows),'priorW585CandidateFreeManifestSha256':sha((PREV_INPUT/'manifest.json').read_bytes()),'priorW585CandidateFreeChecksumListSha256':sha((PREV_INPUT/'SHA256SUMS.txt').read_bytes()),'priorW585ApplicationSummarySha256':sha((W585_APP/'application/application-summary.json').read_bytes()),'priorW585ApplicationReadbackSha256':sha((W585_APP/'application/application-readback.jsonl').read_bytes()),'priorW585ApplicationHoldLedgerSha256':sha((W585_APP/'application/holds.jsonl').read_bytes()),'priorW585SelectedAppliedSha256':sha((W585_APP/'application/selected-applied.jsonl').read_bytes()),'priorW585EvidenceChecksumListSha256':sha((W585_APP/'SHA256SUMS.txt').read_bytes()),'priorW585EvidenceManifestSha256':sha((W585_APP/'manifest.json').read_bytes()),'sourceSnapshotSha256':source_snapshot_sha,'sourceQueueSha256':source_queue_sha,'sourceIdOrderSha256':active_order_sha,'currentCatalogSha256':catalog_sha,'attestedAtUtc':datetime.now(timezone.utc).isoformat(timespec='seconds')}

INPUT.mkdir(parents=True,exist_ok=True)
dumpj(INPUT/'PR-attestation-before.json',att_before)
dumpj(INPUT/'continuity-reattestation.json',continuity)
dumpj(INPUT/'catalog-file-pins.json',{'repository':'snapetech-org/ROMarrNG','commit':HEAD,'tree':TREE,'baseLocale':'en','activeUniqueSourceIds':len(reg),'catalogMessageCount':len(messages),'catalogPath':catalog_path,'catalogSha256':catalog_sha,'catalogGitBlob':blob(catalog_path),'catalogKeyOrderSha256':sha('\n'.join(ids)+'\n'),'sourceQueuePath':registry_path,'sourceQueueSha256':source_queue_sha,'sourceSnapshotPath':snapshot_path,'sourceSnapshotSha256':source_snapshot_sha,'sourceIdOrderSha256':active_order_sha,'sourceCallerFilePins':{x['path']:{'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in file_pins}})
dumpj(INPUT/'source-file-pins.json',{'head':HEAD,'tree':TREE,'files':file_pins})
dumpl(INPUT/'prior-selection-reattestation.jsonl',selection_rows)
dumpl(INPUT/'prior-hold-reattestation.jsonl',hold_rows)
dumpl(INPUT/'prior-applied-cell-reattestation.jsonl',applied_rows)
dumpl(INPUT/'prior-window-cell-hash-reattestation.jsonl',w545_rows)
dumpl(INPUT/'prior-w565-window-cell-hash-reattestation.jsonl',w565_rows)
dumpl(INPUT/'prior-w585-window-cell-hash-reattestation.jsonl',w585_rows)
dumpj(INPUT/'prior-selection-reattestation-summary.json',{'priorWindows':dict(collections.Counter(x['priorWindow'] for x in selection_rows)),'reattestedSelectedSourceCount':len(selection_rows),'allPriorSelectionsMatchCurrentCatalogAndRegistry':True,'currentHead':HEAD,'currentTree':TREE})
dumpj(INPUT/'prior-hold-reattestation-summary.json',{'reattestedCellCount':len(hold_rows),'windowCounts':dict(collections.Counter(x['window'] for x in hold_rows)),'allSourcesAndSelectionPositionsMatchCurrentSnapshot':True,'allCurrentTargetHashesMatchPriorHoldEvidence':True,'currentTargetChangedCells':0,'currentHead':HEAD,'currentTree':TREE})
dumpj(INPUT/'prior-applied-cell-reattestation-summary.json',{'priorWindows':dict(collections.Counter(x['priorWindow'] for x in applied_rows)),'applicationCommits':{'W505-W524':'b248261d5aaa33ec7247023b85d666ed7fc89309','W525-W544':'63224167b0f89978a68977a7996bd06724d06129','W545-W564':'2a921d8280487f6d172616719f32e3dced243d83','W565-W584':'89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac','W585-W604':W585_PRODUCT},'reattestedCellCount':len(applied_rows),'allSelectedTargetHashesMatchCurrentCatalog':True,'changedCells':0,'currentHead':HEAD,'currentTree':TREE})
dumpj(INPUT/'selection.json',{'window':'W605-W624','method':'Select catalog message insertion indices 605 through 624 (zero-based) from exact pinned ui-labels.json message key order; this differs from active source registry sort.','positions':[605,624],'catalogInsertionPositionsOneBased':[606,625],'sourceCount':20,'localeCount':12,'cellCount':240,'localeOrder':LOCALES,'activeUniqueSourceIds':len(reg),'sourceIdOrderSha256':active_order_sha,'catalogMessageCount':len(messages),'catalogKeyOrderSha256':sha('\n'.join(ids)+'\n'),'selectedSources':selected})
dumpj(INPUT/'registry-order-note.json',{'selectionBasis':'catalog JSON message-key insertion order','selectedCatalogZeroBasedIndices':[605,624],'activeRegistryCount':len(reg),'selectedIdsInActiveRegistry':sum(x['activeSourceRegistry'] for x in selected),'activeRegistryMatches':[{'sourceId':x['sourceId'],'activeRank':x['activeSourceRank'],'registryLocations':x['registryLocations']} for x in selected if x['activeSourceRegistry']],'lineHintCaveat':'Active source registry metadata does not substitute for exact literal caller search and excerpt evidence.'})
dumpl(INPUT/'selection-boundary.jsonl',boundary)
dumpj(INPUT/'manifest.json',{'artifact':'ROMarrNG PR #70 W605-W624 candidate-free input','repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':BRANCH,'baseRefName':'main','head':HEAD,'tree':TREE,'window':'W605-W624','selectionBasis':'catalog insertion order; exact pinned ui-labels.json message indices 605..624','sourceCount':20,'localeCount':12,'cellCount':240,'locales':LOCALES,'activeUniqueSourceIdCount':len(reg),'sourceIdOrderSha256':active_order_sha,'catalogMessageCount':len(messages),'catalogPath':catalog_path,'catalogSha256':catalog_sha,'catalogKeyOrderSha256':sha('\n'.join(ids)+'\n'),'sourceQueuePath':registry_path,'sourceQueueSha256':source_queue_sha,'sourceSnapshotSha256':source_snapshot_sha,'priorSelectedSourceCount':len(selection_rows),'priorSelectionsUnchanged':True,'priorHoldCellCount':len(hold_rows),'priorHoldTargetsUnchanged':True,'priorHoldCellChangedCount':0,'priorAppliedSelectedCellCount':len(applied_rows),'priorAppliedTargetsUnchanged':True,'priorW545FullCellHashReadbackCount':len(w545_rows),'priorW565FullCellHashReadbackCount':len(w565_rows),'priorW585FullCellHashReadbackCount':len(w585_rows),'priorW585ChangedAppliedCellCount':sum(x['applicationChanged'] for x in w585_rows),'priorW585CallerlessHoldCellCount':sum(x['held'] for x in w585_rows),'currentTargetPlaceholderMismatches':mismatch['placeholder'],'currentTargetMarkupMismatches':mismatch['markup'],'currentTargetNumericMismatches':mismatch['numeric'],'currentTargetNumericPresentationDifferences':mismatch['numericPresentationDifferences'],'currentTargetProtectedLiteralMismatches':mismatch['protectedLiteral'],'currentTargetMissingCells':mismatch['missingTarget'],'callerSearchQueryCount':20,'sourceContextCount':20,'callerlessSourceCount':sum(x['callerless'] for x in contexts),'callerlessCurrentTargetCellCount':12*sum(x['callerless'] for x in contexts),'directCallerRefCount':sum(x['exactMatchCount'] for x in contexts),'activeRegistrySelectedSourceCount':sum(x['activeSourceRegistry'] for x in selected),'candidateFree':True,'proposedTargetsIncluded':False,'reviewDecisionsIncluded':False,'createdUtc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'reviewBoundary':'Fresh exact-head input with source inventory, target cells, caller context, token checks, and hash-only reattestation of all prior selected sources, holds, applied cells, and W545/W565/W585 readbacks. No current-window proposal or decision is included.'})
dumpj(INPUT/'source-snapshot.json',source_snapshot)
file(INPUT/'source-queue.json').write_bytes(file(registry_path).read_bytes())
dumpj(INPUT/'caller-search-audit.json',{'head':HEAD,'tree':TREE,'queryCount':20,'searchScope':'tracked production source files under romarr; tests, documentation, and locale catalogs excluded','productionFilesSearched':len(files),'results':[{'sourceId':c['sourceId'],'sourceSha256':c['sourceSha256'],'matchCount':c['exactMatchCount'],'callerless':c['callerless'],'contextSha256':c['contextSha256']} for c in contexts]})
dumpj(INPUT/'current-target-token-mismatches.json',mismatch)
dumpl(INPUT/'catalog-source-inventory.jsonl',inventory)
dumpl(INPUT/'source-inventory-selection.jsonl',selected)
dumpl(INPUT/'source-contexts.jsonl',contexts)
dumpl(INPUT/'current-target-cells.jsonl',cells)
dumpj(INPUT/'dispatch-mechanics.json',{'head':HEAD,'tree':TREE,'sourceFiles':[x for x in file_pins if x['path'] in ('romarr/i18n_runtime.js','romarr/ui.py','romarr/ui-source-messages.json')],'description':'Source lookup and locale dispatch are pinned through exact source file hashes; source ownership only.'})
att_after=attestation()
for k in ('state','draft','merged','headRefName','head','tree','branchRefOid','pullRefOid','baseRefName','baseApiSha','baseLiveRefOid','bodySha256','bodyBytes'):
    if att_after[k]!=att_before[k]: raise SystemExit('FAIL: live PR/head/body moved during extraction: '+k)
dumpj(INPUT/'PR-attestation-after-candidate-free.json',att_after)
if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'):
    raise SystemExit('FAIL: source worktree changed during candidate-free build')
(OUT/'README.md').write_text(f"""# ROMarrNG PR #70 W605-W624 candidate-free packet

Pinned to open draft PR head {HEAD}, tree {TREE}, branch {BRANCH}. This packet covers catalog insertion indices 605-624 (one-based positions 606-625), with 20 sources and 240 locale cells.

The prior W585-W604 product commit is {W585_PRODUCT}, and its complete evidence head is {EVIDENCE_HEAD}. Historical reattestation covers 220 selected source IDs, 628 held cells including 24 unchanged callerless W585 cells, 71 applied cells, and three 240-cell readbacks for W545-W564, W565-W584, and W585-W604. The W585 readback includes 22 applied target hashes and 24 callerless holds; all remain unchanged at this head.

The input includes current source and target text, exact source/caller context, protected-token checks, and historical hash lineage. It includes no W605-W624 proposal or review decision. PR API head, branch ref, pull ref, body hash, and source tree remained unchanged during extraction.

Verify with python3 verify_bundle.py --repo /path/to/the-exact-8729059-ROMarrNG-worktree from this directory.
""",encoding='utf-8')
print(json.dumps({'result':'CANDIDATE_FREE_DATA_BUILT','head':HEAD,'tree':TREE,'window':'W605-W624','selectedSources':len(selected),'cells':len(cells),'callerlessSources':sum(x['callerless'] for x in contexts),'callerlessCells':12*sum(x['callerless'] for x in contexts),'directCallerRefs':sum(x['exactMatchCount'] for x in contexts),'tokenMismatches':mismatch,'priorSelectedSources':len(selection_rows),'priorHoldCells':len(hold_rows),'priorAppliedCells':len(applied_rows),'priorW545ReadbackCells':len(w545_rows),'priorW565ReadbackCells':len(w565_rows),'priorW585ReadbackCells':len(w585_rows),'priorW585ChangedAppliedCells':sum(x['applicationChanged'] for x in w585_rows),'priorW585CallerlessHolds':sum(x['held'] for x in w585_rows)},ensure_ascii=False,sort_keys=True))
