#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
TASK=OUT.parent
INPUT=OUT/'candidate-free'/'input'
WT=Path('/mnt/disks/scratch/task-worktrees/localization-20261105/romarrng-pr70-w625-644-pinned')
PREV=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w605-624-20261104/candidate-free')
PREV_INPUT=PREV/'candidate-free'/'input'
PREV_SOURCE=Path('/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w585-604-apply-20261104')
APP=WT/'docs/pr-evidence/pr70-localization-2026-11-04/window-0605-0624-followup'
HEAD='5860fce5d546a772b1df995f8f6321c083ed7d5d'
TREE='561835895972a62e9d3b1f2bfe9bcba01187eb98'
PREV_HEAD='872905926887840025ba4c3f17151b96f8d3e6e2'
PREV_TREE='d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4'
PRODUCT='e6e826be77e5057cf88b4bbb49f6ff60f2980c33'
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
def git(*args): return subprocess.check_output(['git','-C',str(WT),*args],text=True).strip()
def gitat(commit,*args): return subprocess.check_output(['git','-C',str(WT),*args],text=True).strip()
def blob(rel): return git('rev-parse',f'{HEAD}:{rel}')
def file(rel): return WT/rel
def api(): return json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/ROMarrNG/pulls/70'],text=True,cwd=WT))
def verify_sums(root,name='SHA256SUMS.txt'):
    listed={}
    for line in (root/name).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); p=(root/n).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=h: raise SystemExit(f'FAIL checksum {root}/{n}')
        if n in listed: raise SystemExit(f'FAIL duplicate checksum {n}')
        listed[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/name}
    if set(listed)!=actual: raise SystemExit(f'FAIL checksum coverage {root}')
    return listed

def attestation():
    d=api(); raw=git('ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head','refs/heads/main')
    refs={line.split('\t')[1]:line.split('\t')[0] for line in raw.splitlines() if line.strip()}
    body=d.get('body') or ''
    r={'result':'PASS','attestedAtUtc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'repository':'snapetech-org/ROMarrNG','pullRequest':70,'pullRequestUrl':d['html_url'],'state':d['state'].upper(),'draft':d['draft'],'merged':d['merged'],'headRefName':d['head']['ref'],'head':d['head']['sha'],'tree':git('rev-parse',f'{HEAD}^{{tree}}'),'branchRefOid':refs.get(f'refs/heads/{BRANCH}'),'pullRefOid':refs.get('refs/pull/70/head'),'baseRefName':d['base']['ref'],'baseApiSha':d['base']['sha'],'baseLiveRefOid':refs.get('refs/heads/main'),'baseApiRefMismatch':d['base']['sha']!=refs.get('refs/heads/main'),'bodySha256':sha(body),'bodyBytes':len(body.encode()),'checksRerun':False}
    required=('OPEN',True,False,BRANCH,HEAD,TREE,HEAD,HEAD,'main')
    got=(r['state'],r['draft'],r['merged'],r['headRefName'],r['head'],r['tree'],r['branchRefOid'],r['pullRefOid'],r['baseRefName'])
    if got!=required: raise SystemExit('FAIL live PR API/branch/pull alignment: '+repr(r))
    marker='<!-- romarrng-pr70-window-605-624-application-20261104 -->'
    if marker not in body or HEAD not in body or 'W605–W624 evidence packet' not in body: raise SystemExit('FAIL W605 milestone/evidence missing in PR body')
    return r

if INPUT.exists() and any(INPUT.iterdir()): raise SystemExit('FAIL candidate-free input already exists')
if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all') or git('branch','--show-current'):
    raise SystemExit('FAIL pinned worktree is not exact, clean, detached')
# Historical W605 candidate-free inputs are checked by immutable hashes and the prior pinned tree.
verify_sums(PREV); verify_sums(PREV_INPUT)
if subprocess.check_output(['git','-C',str(PREV_SOURCE),'rev-parse','HEAD'],text=True).strip()!=PREV_HEAD or subprocess.check_output(['git','-C',str(PREV_SOURCE),'rev-parse','HEAD^{tree}'],text=True).strip()!=PREV_TREE:
    raise SystemExit('FAIL previous candidate-free source pin')
if subprocess.check_output(['git','-C',str(PREV_SOURCE),'status','--porcelain=v1','--untracked-files=all'],text=True).strip(): raise SystemExit('FAIL prior source worktree dirty')
# The prior window's complete application evidence is independently sealed and exact-head checked.
verify_sums(APP)
subprocess.run(['python3',str(APP/'verify_application.py'),'--repo',str(WT)],check=True,stdout=subprocess.DEVNULL)
prev_manifest=json.loads((PREV_INPUT/'manifest.json').read_text())
summary=json.loads((APP/'application/application-summary.json').read_text())
pins=json.loads((APP/'application/catalog-pins.json').read_text())
if (prev_manifest['head'],prev_manifest['tree'],prev_manifest['window'])!=(PREV_HEAD,PREV_TREE,'W605-W624'): raise SystemExit('FAIL previous W605 candidate-free pin')
if (summary['productCommit'],summary['baseHead'],summary['productTree'],summary['cellCount'],summary['counts'])!=(PRODUCT,PREV_HEAD,'4e4381181522c863fc8a5916840233ef4ecb5038',240,{'applied':2,'hold_hash_only':36,'retain_current':202,'total':240}): raise SystemExit('FAIL W605 application summary')
if (pins['baseHead'],pins['baseTree'])!=(PREV_HEAD,PREV_TREE): raise SystemExit('FAIL W605 pre-catalog pin')
if git('rev-parse',f'{PRODUCT}^')!=PREV_HEAD or git('rev-parse',f'{PRODUCT}^{{tree}}')!=summary['productTree'] or git('diff-tree','--no-commit-id','--name-only','-r',PRODUCT).splitlines()!=['romarr/ui-labels.json']:
    raise SystemExit('FAIL W605 product commit scope')
if git('rev-parse',f'{HEAD}^')!=PRODUCT: raise SystemExit('FAIL W605 evidence completion parent')
app_tracked=git('ls-tree','-r','--name-only',HEAD,'--','docs/pr-evidence/pr70-localization-2026-11-04/window-0605-0624-followup').splitlines()
app_local=sorted(p.relative_to(APP).as_posix() for p in APP.rglob('*') if p.is_file())
if sorted(p.split('window-0605-0624-followup/',1)[1] for p in app_tracked)!=app_local: raise SystemExit('FAIL W605 evidence file set')

OLD=PREV_INPUT
old_sel=jl(OLD/'prior-selection-reattestation.jsonl'); w605_selected=jl(OLD/'source-inventory-selection.jsonl')
old_holds=jl(OLD/'prior-hold-reattestation.jsonl'); old_applied=jl(OLD/'prior-applied-cell-reattestation.jsonl')
w605_before=jl(OLD/'current-target-cells.jsonl')
w605_readback=jl(APP/'application/application-readback.jsonl'); w605_holds=jl(APP/'application/holds.jsonl'); w605_changed=jl(APP/'application/selected-applied.jsonl')
if tuple(map(len,(old_sel,w605_selected,old_holds,old_applied,w605_before,w605_readback,w605_holds,w605_changed)))!=(220,20,628,71,240,240,36,2):
    raise SystemExit('FAIL W605 lineage/readback counts')

catalog_path='romarr/ui-labels.json'; catalog_bytes=file(catalog_path).read_bytes(); doc=json.loads(catalog_bytes); messages=doc['messages']; ids=list(messages)
if len(messages)!=1836 or sha('\n'.join(ids)+'\n')!=pins['catalogKeyOrderSha256']: raise SystemExit('FAIL catalog message count/order')
if sha(catalog_bytes)!=pins['postCatalogSha256'] or blob(catalog_path)!=pins['postCatalogGitBlob']: raise SystemExit('FAIL catalog does not match W605 application readback')
registry_path='romarr/ui-source-messages.json'; snapshot_path='romarr/ui-source-snapshot.json'
registry=json.loads(file(registry_path).read_text())['messages']; reg={r['id']:r for r in registry}
source_snapshot={r['id']:r['sourceHash'] for r in registry}; raw_snapshot=json.loads(file(snapshot_path).read_text())
if len(registry)!=479 or len(reg)!=479 or any(raw_snapshot.get(k)!=v for k,v in source_snapshot.items()): raise SystemExit('FAIL source registry/snapshot consistency')
source_snapshot_sha=sha(canon(source_snapshot)); source_queue_sha=sha(file(registry_path).read_bytes()); active_order_sha=sha('\n'.join(sorted(reg))+'\n')
if source_snapshot_sha!=prev_manifest['sourceSnapshotSha256'] or source_queue_sha!=prev_manifest['sourceQueueSha256'] or active_order_sha!=prev_manifest['sourceIdOrderSha256']: raise SystemExit('FAIL source registry/snapshot changed since W605 input')
active_rank={sid:i for i,sid in enumerate(sorted(reg),1)}

# Re-attest the prior 220 selected sources and append W605's 20 selected sources.
selection_rows=[]
for r in old_sel:
    sid=r['sourceId']; idx=r['catalogZeroBasedIndex']; m=messages.get(sid)
    if m is None or ids[idx]!=sid or sha(m['source'])!=r['priorSourceSha256'] or sha(m['source'])!=r['currentSourceSha256'] or m.get('sourceHash')!=sha(m['source']): raise SystemExit('FAIL historical selected source changed '+sid)
    selection_rows.append({'priorWindow':r['priorWindow'],'position':r.get('position',idx),'catalogZeroBasedIndex':idx,'sourceId':sid,'priorSourceSha256':r['priorSourceSha256'],'currentSourceSha256':sha(m['source']),'selectionPositionMatches':True,'sourceHashMatches':True,'registryMembershipAndHashMatch':(sid in reg)==bool(r.get('registryMembershipAndHashMatch',sid in reg)),'priorSelectionEvidenceSha256':sha(canon(r)),'reattestedAtHead':HEAD})
for r in w605_selected:
    sid=r['sourceId']; idx=r['catalogZeroBasedIndex']; m=messages[sid]
    if idx not in range(605,625) or ids[idx]!=sid or sha(m['source'])!=r['sourceSha256'] or m.get('sourceHash')!=sha(m['source']): raise SystemExit('FAIL W605 selected source changed '+sid)
    selection_rows.append({'priorWindow':'W605-W624','position':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'priorSourceSha256':r['sourceSha256'],'currentSourceSha256':sha(m['source']),'selectionPositionMatches':True,'sourceHashMatches':True,'registryMembershipAndHashMatch':sid in reg,'priorSelectionEvidenceSha256':sha(canon(r)),'reattestedAtHead':HEAD})
if len(selection_rows)!=240 or len({x['sourceId'] for x in selection_rows})!=240: raise SystemExit('FAIL prior selected source count/uniqueness')

# Re-attest all prior held cells and the W605 hash-only holds.
hold_rows=[]
for h in old_holds:
    sid=h['sourceId']; loc=h['locale']; idx=ids.index(sid); m=messages[sid]; basis=h.get('selectionPositionBasis',''); pos_ok=(idx==h['position']) if 'catalog insertion index' in basis else active_rank.get(sid)==h['position']; cur=sha(m['translations'][loc])
    if sha(m['source'])!=h['sourceSha256'] or cur!=h['priorTargetSha256'] or not pos_ok: raise SystemExit('FAIL prior held source/position/target changed '+sid)
    hold_rows.append({'window':h['window'],'position':h['position'],'selectionPositionBasis':basis,'sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'priorTargetSha256':h['priorTargetSha256'],'currentTargetSha256':cur,'sourceMatchesCurrentCatalog':True,'selectionPositionMatches':True,'targetUnchanged':True,'priorHoldEvidenceSha256':h.get('priorHoldEvidenceSha256',sha(canon(h))),'reattestedAtHead':HEAD})
ctx_by_id={x['sourceId']:x for x in jl(OLD/'source-contexts.jsonl')}; w605_hold_ids=set()
for h in w605_holds:
    idx=h['position']; loc=h['locale']; sid=ids[idx]; m=messages[sid]; ctx=ctx_by_id[sid]
    if idx not in range(605,625) or loc not in LOCALES or sha(m['source'])!=h['sourceSha256'] or sha(m['translations'][loc])!=h['afterTargetSha256'] or h['beforeTargetSha256']!=h['afterTargetSha256'] or not ctx['callerless']:
        raise SystemExit('FAIL W605 hold is not unchanged callerless hash-only')
    if any(k in h for k in ('source','sourceText','currentTarget','target','targetText','proposedTarget','selectedTarget','finalTarget','sourceId')): raise SystemExit('FAIL W605 hold contains translation/source text')
    if (sid,loc) in w605_hold_ids: raise SystemExit('FAIL duplicate W605 hold')
    w605_hold_ids.add((sid,loc)); hold_rows.append({'window':'W605-W624','position':idx,'selectionPositionBasis':'catalog insertion index (zero-based)','sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'priorTargetSha256':h['afterTargetSha256'],'currentTargetSha256':h['afterTargetSha256'],'sourceMatchesCurrentCatalog':True,'selectionPositionMatches':True,'targetUnchanged':True,'callerless':True,'holdReasonSha256':sha('callerless hash-only hold'),'priorHoldEvidenceSha256':sha(canon(h)),'reattestedAtHead':HEAD})
if len(hold_rows)!=664 or len({(x['sourceId'],x['locale']) for x in hold_rows})!=664: raise SystemExit('FAIL prior hold count/uniqueness')

# Re-attest previously applied cell hashes.
applied_rows=[]
for x in old_applied:
    sid=x['sourceId']; loc=x['locale']; m=messages[sid]; cur=sha(m['translations'][loc])
    if sha(m['source'])!=x['sourceSha256'] or cur!=x['priorSelectedTargetSha256'] or cur!=x['currentTargetSha256']: raise SystemExit('FAIL prior applied target changed '+sid)
    applied_rows.append({'priorWindow':x['priorWindow'],'catalogZeroBasedIndex':ids.index(sid),'sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'priorSelectedTargetSha256':cur,'currentTargetSha256':cur,'targetUnchanged':True,'applicationCommit':x['applicationCommit'],'priorAppliedEvidenceSha256':x.get('priorAppliedEvidenceSha256',sha(canon(x))),'reattestedAtHead':HEAD})
before_map={(x['sourceId'],x['locale']):x for x in w605_before}; w605_changed_ids=set()
for x in w605_changed:
    sid=x['sourceId']; loc=x['locale']; idx=x['position']; m=messages[sid]; before=before_map[(sid,loc)]; cur=sha(m['translations'][loc])
    if idx not in range(605,625) or ids[idx]!=sid or before['currentTargetSha256']!=x['beforeTargetSha256'] or sha(m['source'])!=x['sourceSha256'] or cur!=x['afterTargetSha256']: raise SystemExit('FAIL W605 applied target/readback mismatch')
    w605_changed_ids.add((sid,loc)); applied_rows.append({'priorWindow':'W605-W624','catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'priorSelectedTargetSha256':cur,'currentTargetSha256':cur,'targetUnchanged':True,'applicationCommit':PRODUCT,'priorAppliedEvidenceSha256':sha(canon(x)),'beforeTargetSha256':x['beforeTargetSha256'],'reattestedAtHead':HEAD})
if len(w605_changed_ids)!=2 or len(applied_rows)!=73 or len({(x['sourceId'],x['locale']) for x in applied_rows})!=73 or w605_changed_ids & w605_hold_ids: raise SystemExit('FAIL applied-cell lineage')

# Re-attest the most recent three full-window readbacks and W605's exact 240-cell application readback.
def reattest_prior(rows,label):
    if len(rows)!=240: raise SystemExit('FAIL '+label+' readback count')
    out=[]
    for x in rows:
        sid=x['sourceId']; loc=x['locale']; m=messages[sid]; cur=sha(m['translations'][loc])
        if sha(m['source'])!=x['sourceSha256'] or cur!=x['currentTargetSha256']: raise SystemExit('FAIL '+label+' readback hash')
        out.append({**x,'currentTargetSha256':cur,'targetMatchesApplicationReadback':True,'reattestedAtHead':HEAD})
    return out
w545_rows=reattest_prior(jl(OLD/'prior-window-cell-hash-reattestation.jsonl'),'W545-W564')
w565_rows=reattest_prior(jl(OLD/'prior-w565-window-cell-hash-reattestation.jsonl'),'W565-W584')
w585_rows=reattest_prior(jl(OLD/'prior-w585-window-cell-hash-reattestation.jsonl'),'W585-W604')
w605_rows=[]
for rb in w605_readback:
    idx=rb['position']; sid=rb.get('sourceId') or ids[idx]; loc=rb['locale']; m=messages[sid]; before=before_map[(sid,loc)]; cur=sha(m['translations'][loc]); held=(sid,loc) in w605_hold_ids; changed=(sid,loc) in w605_changed_ids
    if idx not in range(605,625) or ids[idx]!=sid or before['currentTargetSha256']!=rb['beforeTargetSha256'] or sha(m['source'])!=rb['sourceSha256'] or cur!=rb['afterTargetSha256'] or bool(rb['changed'])!=changed or (held and rb['changed']): raise SystemExit('FAIL W605 240-cell readback mismatch')
    w605_rows.append({'priorWindow':'W605-W624','catalogZeroBasedIndex':idx,'sourceId':sid,'sourceSha256':sha(m['source']),'locale':loc,'beforeTargetSha256':rb['beforeTargetSha256'],'currentTargetSha256':cur,'applicationChanged':bool(rb['changed']),'held':held,'applicationCommit':PRODUCT,'targetMatchesApplicationReadback':True,'priorCandidateFreeCellEvidenceSha256':sha(canon(before)),'applicationReadbackCellEvidenceSha256':sha(canon(rb)),'reattestedAtHead':HEAD})
if (len(w605_rows),sum(x['applicationChanged'] for x in w605_rows),sum(x['held'] for x in w605_rows))!=(240,2,36): raise SystemExit('FAIL W605 readback totals')

# Pin every production source/caller file from the previous candidate-free inventory.
oldpins=json.loads((OLD/'catalog-file-pins.json').read_text())['sourceCallerFilePins']; file_pins=[]
for rel in sorted(set(oldpins)|{registry_path,snapshot_path}):
    data=file(rel).read_bytes(); cur={'fileSha256':sha(data),'gitBlob':blob(rel)}; file_pins.append({'path':rel,'fileSha256':cur['fileSha256'],'gitBlob':cur['gitBlob'],'bytes':len(data)})
    if rel in oldpins and cur!={'fileSha256':oldpins[rel]['fileSha256'],'gitBlob':oldpins[rel]['gitBlob']}: raise SystemExit('FAIL source/caller pin drift since W605: '+rel)

# Select exactly the next twenty catalog insertion indices (zero-based 625..644).
selected=[]
for idx in range(625,645):
    sid=ids[idx]; m=messages[sid]; sh=sha(m['source'])
    if m.get('sourceHash')!=sh: raise SystemExit('FAIL sourceHash field mismatch: '+sid)
    selected.append({'position':idx,'catalogZeroBasedIndex':idx,'catalogOneBasedPosition':idx+1,'sourceId':sid,'source':m['source'],'sourceSha256':sh,'activeSourceRegistry':sid in reg,'activeSourceRank':active_rank.get(sid),'registryLocations':reg.get(sid,{}).get('locations',[])})
if len(selected)!=20 or len({x['sourceId'] for x in selected})!=20 or {x['sourceId'] for x in selection_rows}&{x['sourceId'] for x in selected}: raise SystemExit('FAIL W625 selection count/overlap')
boundary=[]
for idx,role in ((624,'catalog-before-selected-start'),(625,'selected-start'),(644,'selected-end'),(645,'catalog-after-selected-end')):
    sid=ids[idx]; m=messages[sid]; boundary.append({'position':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'source':m['source'],'sourceSha256':sha(m['source']),'role':role})

# Exact source/caller searches over tracked production files only.
tracked=subprocess.check_output(['git','-C',str(WT),'ls-files','-z','--','romarr']).split(b'\0'); paths=[]
for raw in tracked:
    if not raw: continue
    rel=raw.decode(); p=WT/rel; parts=rel.lower().split('/')
    if p.suffix.lower() not in ('.py','.js','.html','.jinja','.jinja2','.css','.ts','.tsx') or any(x in parts for x in ('test','tests','__pycache__')) or p.name.startswith('test_') or p.name.endswith('_test.py'): continue
    paths.append(rel)
prod_files={}
for rel in paths:
    data=file(rel).read_bytes();
    try: text=data.decode()
    except UnicodeDecodeError: text=data.decode('utf-8','replace')
    prod_files[rel]=(text,data,blob(rel))
def match_context(item,files,commit):
    src=item['source']; sid=item['sourceId']; matches=[]
    variants=list(dict.fromkeys([json.dumps(src,ensure_ascii=False),repr(src),'"'+src+'"',chr(39)+src+chr(39),chr(96)+src+chr(96)]))
    for rel,(txt,data,gb) in files.items():
        occ={}
        for literal in variants:
            start=0
            while True:
                at=txt.find(literal,start)
                if at<0: break
                occ.setdefault(at,'exact quoted source literal'); start=at+max(1,len(literal))
        start=0
        while True:
            at=txt.find(sid,start)
            if at<0: break
            occ.setdefault(at,'exact source ID reference'); start=at+len(sid)
        for hit in re.finditer(r'>[ \t]*'+re.escape(src)+r'[ \t]*<',txt): occ.setdefault(hit.start(),'exact HTML text node')
        lines=txt.splitlines()
        for at,kind in sorted(occ.items()):
            line=txt.count('\n',0,at)+1; lo=max(1,line-3); hi=min(len(lines),line+3); excerpt=[{'line':i,'text':lines[i-1]} for i in range(lo,hi+1)]
            matches.append({'path':rel,'line':line,'lineText':lines[line-1] if line<=len(lines) else '','lineSha256':sha(lines[line-1] if line<=len(lines) else ''),'excerpt':excerpt,'excerptSha256':sha(canon(excerpt)),'fileSha256':sha(data),'gitBlob':gb,'matchKind':kind})
    matches.sort(key=lambda x:(x['path'],x['line'],x['matchKind']))
    core={'sourceId':sid,'source':src,'sourceSha256':item['sourceSha256'],'head':commit,'searchMethod':'exact quoted source literal, exact source ID, or exact HTML text-node search in tracked production code; tests/docs/catalog files excluded','productionFilesSearched':len(files),'exactMatchCount':len(matches),'callerless':not matches,'callers':matches}
    return {**core,'contextSha256':sha(canon(core))}
contexts=[match_context(x,prod_files,HEAD) for x in selected]; ctxmap={x['sourceId']:x for x in contexts}

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
    if m.get('sourceHash')!=sh: raise SystemExit('FAIL sourceHash mismatch: '+sid)
    inventory.append({'catalogZeroBasedIndex':idx,'catalogOneBasedPosition':idx+1,'sourceId':sid,'source':src,'sourceSha256':sh,'activeSourceRegistry':sid in reg,'activeSourceRank':active_rank.get(sid),'registryLocations':reg.get(sid,{}).get('locations',[]),'sourcePlaceholderTokens':t['placeholders'],'sourceMarkupTags':t['markup'],'sourceNumericTokens':t['numbers'],'sourceNumericWords':['Zero'] if re.search(r'\bzero\b',src,re.I) else [],'sourceProtectedLiterals':t['protectedLiterals']})
cells=[]; mismatch={'placeholder':0,'markup':0,'numeric':0,'numericPresentationDifferences':0,'protectedLiteral':0,'missingTarget':0}
for item in selected:
    sid=item['sourceId']; m=messages[sid]; src=m['source']; st=tokens(src); ctx=ctxmap[sid]; refs=[{'path':r['path'],'line':r['line'],'lineSha256':r['lineSha256'],'excerptSha256':r['excerptSha256'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob']} for r in ctx['callers']]
    for loc in LOCALES:
        target=m.get('translations',{}).get(loc)
        if not isinstance(target,str): mismatch['missingTarget']+=1; target=''
        tt=tokens(target); ph_ok=collections.Counter(st['placeholders'])==collections.Counter(tt['placeholders']); tag_ok=collections.Counter(st['markup'])==collections.Counter(tt['markup'])
        srcnums=collections.Counter(st['numbers']); tgtnums=collections.Counter(tt['numbers']); extra=list((tgtnums-srcnums).elements()); numeric_presentation=bool(re.search(r'\bzero\b',src,re.I) and not st['numbers'] and extra==['0']); num_ok=not(srcnums-tgtnums) and (not extra or numeric_presentation)
        missing=[x for x in st['protectedLiterals'] if x not in target]
        mismatch['placeholder']+=not ph_ok; mismatch['markup']+=not tag_ok; mismatch['numeric']+=not num_ok; mismatch['numericPresentationDifferences']+=numeric_presentation; mismatch['protectedLiteral']+=bool(missing)
        cells.append({'position':item['position'],'catalogZeroBasedIndex':item['catalogZeroBasedIndex'],'catalogOneBasedPosition':item['catalogOneBasedPosition'],'sourceId':sid,'source':src,'sourceSha256':item['sourceSha256'],'locale':loc,'currentTarget':target,'currentTargetSha256':sha(target),'catalogTranslationHash':m.get('translationHashes',{}).get(loc),'translationStatus':m.get('translationStatus',{}).get(loc),'callerContextSha256':ctx['contextSha256'],'callerRefs':refs,'sourcePlaceholderTokens':st['placeholders'],'currentPlaceholderTokens':tt['placeholders'],'placeholderMultisetMatches':ph_ok,'sourceMarkupTags':st['markup'],'currentMarkupTags':tt['markup'],'markupMatches':tag_ok,'sourceNumericTokens':st['numbers'],'sourceNumericWords':['Zero'] if re.search(r'\bzero\b',src,re.I) else [],'currentNumericTokens':tt['numbers'],'numericTokensPreserved':num_ok,'numericPresentationEquivalent':numeric_presentation,'sourceProtectedLiterals':st['protectedLiterals'],'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing,'containsCandidate':False})

# Compare exact selected source IDs and caller searches with current upstream main without changing either ref.
main=attestation()['baseLiveRefOid']; main_tree=subprocess.check_output(['git','-C',str(WT),'rev-parse',f'{main}^{{tree}}'],text=True).strip()
main_doc=json.loads(subprocess.check_output(['git','-C',str(WT),'show',f'{main}:romarr/ui-labels.json'],text=True)); main_messages=main_doc.get('messages',{})
main_names=subprocess.check_output(['git','-C',str(WT),'ls-tree','-r','--name-only',main,'--','romarr'],text=True).splitlines(); main_paths=[]
for rel in main_names:
    p=Path(rel); parts=rel.lower().split('/')
    if p.suffix.lower() not in ('.py','.js','.html','.jinja','.jinja2','.css','.ts','.tsx') or any(x in parts for x in ('test','tests','__pycache__')) or p.name.startswith('test_') or p.name.endswith('_test.py'): continue
    main_paths.append(rel)
main_files={}
for rel in main_paths:
    data=subprocess.check_output(['git','-C',str(WT),'show',f'{main}:{rel}'])
    try: txt=data.decode()
    except UnicodeDecodeError: txt=data.decode('utf-8','replace')
    gb=subprocess.check_output(['git','-C',str(WT),'rev-parse',f'{main}:{rel}'],text=True).strip(); main_files[rel]=(txt,data,gb)
def drift_signature(ctx): return {(x['path'],x['matchKind'],x['lineText'].strip()) for x in ctx['callers']}
drift=[]
for item,pc in zip(selected,contexts):
    sid=item['sourceId']; mm=main_messages.get(sid); msrc=mm.get('source') if isinstance(mm,dict) else None; msha=sha(msrc) if isinstance(msrc,str) else None
    mc=match_context({'sourceId':sid,'source':msrc if isinstance(msrc,str) else item['source'],'sourceSha256':msha or item['sourceSha256']},main_files,main) if isinstance(msrc,str) else {'sourceId':sid,'head':main,'callerless':True,'exactMatchCount':0,'callers':[]}
    new=sorted(drift_signature(mc)-drift_signature(pc)); removed=sorted(drift_signature(pc)-drift_signature(mc))
    drift.append({'sourceId':sid,'prSourceSha256':item['sourceSha256'],'mainSourcePresent':isinstance(msrc,str),'mainSourceSha256':msha,'sourceSame':msha==item['sourceSha256'],'prCallerCount':pc['exactMatchCount'],'mainCallerCount':mc['exactMatchCount'],'prCallerless':pc['callerless'],'mainCallerless':mc['callerless'],'newMainCallerSignatures':[{'path':x[0],'matchKind':x[1],'lineText':x[2]} for x in new],'prOnlyCallerSignatures':[{'path':x[0],'matchKind':x[1],'lineText':x[2]} for x in removed],'contextDrift':(msha!=item['sourceSha256'] or new or removed or pc['exactMatchCount']!=mc['exactMatchCount'])})
main_drift={'repository':'snapetech-org/ROMarrNG','prHead':HEAD,'prTree':TREE,'mainHead':main,'mainTree':main_tree,'baseApiSha':api()['base']['sha'],'baseApiRefMismatch':api()['base']['sha']!=main,'comparison':'same stable source IDs and exact quoted source/source-ID/HTML text searches over tracked production files under romarr; tests, docs, catalogs, and workflows excluded','selectedSourceCount':len(selected),'sourcesMissingFromMain':sum(not x['mainSourcePresent'] for x in drift),'sourceTextChanges':sum(not x['sourceSame'] for x in drift),'sourcesWithCallerContextDrift':sum(bool(x['contextDrift']) for x in drift),'sourcesWithNewMainCallers':sum(bool(x['newMainCallerSignatures']) for x in drift),'results':drift}

att_before=attestation()
INPUT.mkdir(parents=True,exist_ok=True)
# Build hash-only historical lineage and candidate-free payloads.
prior_w545=reattest_prior(jl(OLD/'prior-window-cell-hash-reattestation.jsonl'),'W545-W564')
prior_w565=reattest_prior(jl(OLD/'prior-w565-window-cell-hash-reattestation.jsonl'),'W565-W584')
prior_w585=reattest_prior(jl(OLD/'prior-w585-window-cell-hash-reattestation.jsonl'),'W585-W604')
continuity={'result':'PASS','priorWindow':'W605-W624','priorHead':PREV_HEAD,'priorTree':PREV_TREE,'priorProductCommit':PRODUCT,'priorEvidenceHead':HEAD,'currentHead':HEAD,'currentTree':TREE,'priorCandidateFreePacketChecksumsVerified':True,'priorW605ApplicationEvidenceChecksumsVerified':True,'priorSelectedSourceCount':len(selection_rows),'priorSelectedSourceCountUnchanged':True,'priorHoldCellCount':len(hold_rows),'priorHoldCellCountUnchanged':True,'priorHoldChangedCellCount':0,'priorAppliedCellCount':len(applied_rows),'priorAppliedCellCountUnchanged':True,'priorAppliedCellChangedCount':0,'priorW545ReadbackRows':len(prior_w545),'priorW565ReadbackRows':len(prior_w565),'priorW585ReadbackRows':len(prior_w585),'priorW605ReadbackRows':len(w605_rows),'priorW605ChangedAppliedCells':sum(x['applicationChanged'] for x in w605_rows),'priorW605CallerlessHoldCells':sum(x['held'] for x in w605_rows),'priorW605CandidateFreeManifestSha256':sha((PREV_INPUT/'manifest.json').read_bytes()),'priorW605CandidateFreeChecksumListSha256':sha((PREV_INPUT/'SHA256SUMS.txt').read_bytes()),'priorW605ApplicationSummarySha256':sha((APP/'application/application-summary.json').read_bytes()),'priorW605ApplicationReadbackSha256':sha((APP/'application/application-readback.jsonl').read_bytes()),'priorW605ApplicationHoldLedgerSha256':sha((APP/'application/holds.jsonl').read_bytes()),'priorW605SelectedAppliedSha256':sha((APP/'application/selected-applied.jsonl').read_bytes()),'priorW605EvidenceChecksumListSha256':sha((APP/'SHA256SUMS.txt').read_bytes()),'sourceSnapshotSha256':source_snapshot_sha,'sourceQueueSha256':source_queue_sha,'sourceIdOrderSha256':active_order_sha,'currentCatalogSha256':sha(catalog_bytes),'attestedAtUtc':datetime.now(timezone.utc).isoformat(timespec='seconds')}

dumpj(INPUT/'PR-attestation-before.json',att_before)
dumpj(INPUT/'continuity-reattestation.json',continuity)
dumpj(INPUT/'catalog-file-pins.json',{'repository':'snapetech-org/ROMarrNG','commit':HEAD,'tree':TREE,'baseLocale':'en','activeUniqueSourceIds':len(reg),'catalogMessageCount':len(messages),'catalogPath':catalog_path,'catalogSha256':sha(catalog_bytes),'catalogGitBlob':blob(catalog_path),'catalogKeyOrderSha256':sha('\n'.join(ids)+'\n'),'sourceQueuePath':registry_path,'sourceQueueSha256':source_queue_sha,'sourceSnapshotPath':snapshot_path,'sourceSnapshotSha256':source_snapshot_sha,'sourceIdOrderSha256':active_order_sha,'sourceCallerFilePins':{x['path']:{'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in file_pins}})
dumpj(INPUT/'source-file-pins.json',{'head':HEAD,'tree':TREE,'files':file_pins})
dumpl(INPUT/'prior-selection-reattestation.jsonl',selection_rows); dumpl(INPUT/'prior-hold-reattestation.jsonl',hold_rows); dumpl(INPUT/'prior-applied-cell-reattestation.jsonl',applied_rows)
dumpl(INPUT/'prior-window-cell-hash-reattestation.jsonl',prior_w545); dumpl(INPUT/'prior-w565-window-cell-hash-reattestation.jsonl',prior_w565); dumpl(INPUT/'prior-w585-window-cell-hash-reattestation.jsonl',prior_w585); dumpl(INPUT/'prior-w605-window-cell-hash-reattestation.jsonl',w605_rows)
dumpj(INPUT/'prior-selection-reattestation-summary.json',{'priorWindows':dict(collections.Counter(x['priorWindow'] for x in selection_rows)),'reattestedSelectedSourceCount':len(selection_rows),'allPriorSelectionsMatchCurrentCatalogAndRegistry':True,'currentHead':HEAD,'currentTree':TREE})
dumpj(INPUT/'prior-hold-reattestation-summary.json',{'reattestedCellCount':len(hold_rows),'windowCounts':dict(collections.Counter(x['window'] for x in hold_rows)),'allSourcesAndSelectionPositionsMatchCurrentSnapshot':True,'allCurrentTargetHashesMatchPriorHoldEvidence':True,'currentTargetChangedCells':0,'currentHead':HEAD,'currentTree':TREE})
dumpj(INPUT/'prior-applied-cell-reattestation-summary.json',{'priorWindows':dict(collections.Counter(x['priorWindow'] for x in applied_rows)),'applicationCommits':{'W505-W524':'b248261d5aaa33ec7247023b85d666ed7fc89309','W525-W544':'63224167b0f89978a68977a7996bd06724d06129','W545-W564':'2a921d8280487f6d172616719f32e3dced243d83','W565-W584':'89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac','W585-W604':'d44e61d9960c788412da0fadbb8b67744b70e404','W605-W624':PRODUCT},'reattestedCellCount':len(applied_rows),'allSelectedTargetHashesMatchCurrentCatalog':True,'changedCells':0,'currentHead':HEAD,'currentTree':TREE})
dumpj(INPUT/'selection.json',{'window':'W625-W644','method':'Select catalog message insertion indices 625 through 644 (zero-based) from exact pinned ui-labels.json message key order; this differs from active source registry sort.','positions':[625,644],'catalogInsertionPositionsOneBased':[626,645],'sourceCount':20,'localeCount':12,'cellCount':240,'localeOrder':LOCALES,'activeUniqueSourceIds':len(reg),'sourceIdOrderSha256':active_order_sha,'catalogMessageCount':len(messages),'catalogKeyOrderSha256':sha('\n'.join(ids)+'\n'),'selectedSources':selected})
dumpj(INPUT/'registry-order-note.json',{'selectionBasis':'catalog JSON message-key insertion order','selectedCatalogZeroBasedIndices':[625,644],'activeRegistryCount':len(reg),'selectedIdsInActiveRegistry':sum(x['activeSourceRegistry'] for x in selected),'activeRegistryMatches':[{'sourceId':x['sourceId'],'activeRank':x['activeSourceRank'],'registryLocations':x['registryLocations']} for x in selected if x['activeSourceRegistry']],'lineHintCaveat':'Active source registry metadata does not substitute for exact literal caller search and excerpt evidence.'})
dumpl(INPUT/'selection-boundary.jsonl',boundary)
dumpj(INPUT/'source-snapshot.json',source_snapshot); (INPUT/'source-queue.json').write_bytes(file(registry_path).read_bytes())
dumpj(INPUT/'caller-search-audit.json',{'head':HEAD,'tree':TREE,'queryCount':20,'searchScope':'tracked production source files under romarr; tests, documentation, and locale catalogs excluded','productionFilesSearched':len(prod_files),'results':[{'sourceId':c['sourceId'],'sourceSha256':c['sourceSha256'],'matchCount':c['exactMatchCount'],'callerless':c['callerless'],'contextSha256':c['contextSha256']} for c in contexts]})
dumpj(INPUT/'current-target-token-mismatches.json',mismatch); dumpj(INPUT/'main-context-drift.json',main_drift)
dumpl(INPUT/'catalog-source-inventory.jsonl',inventory); dumpl(INPUT/'source-inventory-selection.jsonl',selected); dumpl(INPUT/'source-contexts.jsonl',contexts); dumpl(INPUT/'current-target-cells.jsonl',cells)
dumpj(INPUT/'dispatch-mechanics.json',{'head':HEAD,'tree':TREE,'sourceFiles':[x for x in file_pins if x['path'] in ('romarr/i18n_runtime.js','romarr/ui.py','romarr/ui-source-messages.json')],'description':'Source lookup and locale dispatch are pinned through exact source file hashes; source ownership only.'})
manifest={'artifact':'ROMarrNG PR #70 W625-W644 candidate-free input','repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':BRANCH,'baseRefName':'main','head':HEAD,'tree':TREE,'window':'W625-W644','selectionBasis':'catalog insertion order; exact pinned ui-labels.json message indices 625..644','sourceCount':20,'localeCount':12,'cellCount':240,'locales':LOCALES,'activeUniqueSourceIdCount':len(reg),'sourceIdOrderSha256':active_order_sha,'catalogMessageCount':len(messages),'catalogPath':catalog_path,'catalogSha256':sha(catalog_bytes),'catalogKeyOrderSha256':sha('\n'.join(ids)+'\n'),'sourceQueuePath':registry_path,'sourceQueueSha256':source_queue_sha,'sourceSnapshotSha256':source_snapshot_sha,'priorSelectedSourceCount':len(selection_rows),'priorSelectionsUnchanged':True,'priorHoldCellCount':len(hold_rows),'priorHoldTargetsUnchanged':True,'priorHoldCellChangedCount':0,'priorAppliedSelectedCellCount':len(applied_rows),'priorAppliedTargetsUnchanged':True,'priorW545FullCellHashReadbackCount':len(prior_w545),'priorW565FullCellHashReadbackCount':len(prior_w565),'priorW585FullCellHashReadbackCount':len(prior_w585),'priorW605FullCellHashReadbackCount':len(w605_rows),'priorW605ChangedAppliedCellCount':sum(x['applicationChanged'] for x in w605_rows),'priorW605CallerlessHoldCellCount':sum(x['held'] for x in w605_rows),'currentTargetPlaceholderMismatches':mismatch['placeholder'],'currentTargetMarkupMismatches':mismatch['markup'],'currentTargetNumericMismatches':mismatch['numeric'],'currentTargetNumericPresentationDifferences':mismatch['numericPresentationDifferences'],'currentTargetProtectedLiteralMismatches':mismatch['protectedLiteral'],'currentTargetMissingCells':mismatch['missingTarget'],'callerSearchQueryCount':20,'sourceContextCount':20,'callerlessSourceCount':sum(x['callerless'] for x in contexts),'callerlessCurrentTargetCellCount':12*sum(x['callerless'] for x in contexts),'directCallerRefCount':sum(x['exactMatchCount'] for x in contexts),'activeRegistrySelectedSourceCount':sum(x['activeSourceRegistry'] for x in selected),'mainHead':main,'mainTree':main_tree,'mainSourcesMissing':main_drift['sourcesMissingFromMain'],'mainSourceTextChanges':main_drift['sourceTextChanges'],'mainContextDriftCount':main_drift['sourcesWithCallerContextDrift'],'candidateFree':True,'proposedTargetsIncluded':False,'reviewDecisionsIncluded':False,'createdUtc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'reviewBoundary':'Fresh exact-head input with source inventory, target cells, caller context, token checks, a source/caller comparison against latest main, and hash-only reattestation of all prior selected sources, holds, applied cells, and W545/W565/W585/W605 readbacks. No W625-W644 proposal or decision is included.'}
dumpj(INPUT/'manifest.json',manifest)
# re-attest API/head/body at the end and confirm no tracked/local worktree state moved.
att_after=attestation()
for k in ('state','draft','merged','headRefName','head','tree','branchRefOid','pullRefOid','baseRefName','baseApiSha','baseLiveRefOid','bodySha256','bodyBytes'):
    if att_after[k]!=att_before[k]: raise SystemExit('FAIL live PR/head/body moved during extraction: '+k)
dumpj(INPUT/'PR-attestation-after-candidate-free.json',att_after)
if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'): raise SystemExit('FAIL source worktree changed during candidate-free build')
(OUT/'README.md').write_text(f'''# ROMarrNG PR #70 W625-W644 candidate-free packet\n\nPinned to open draft PR head {HEAD}, tree {TREE}, branch {BRANCH}. This packet covers catalog insertion indices 625-644 (one-based positions 626-645), with 20 sources and 240 locale cells.\n\nPrior W605-W624 application commit: {PRODUCT}. The packet re-attests 240 previously selected source IDs, 664 held cells, 73 applied cells, and the W545/W565/W585/W605 240-cell readbacks. W605-W624 had two catalog changes and 36 unchanged callerless hash-only holds; all prior target hashes match at this head.\n\nThe input contains current source and target text, exact source/caller context, protected-token checks, hash lineage, and a same-ID/source/caller comparison against live main `{main}` (tree `{main_tree}`). It contains no W625-W644 proposal or review decision. The PR API head, branch ref, pull ref, body hash, and source tree remained unchanged during extraction.\n\nThe repository roadmap marks all 22,032 direct target cells as populated, with existing translation provenance generally unknown; this semantic review does not confer native-speaker approval.\n\nVerify with `python3 verify_bundle.py --repo /path/to/the-exact-5860fce-ROMarrNG-worktree` from this directory.\n''',encoding='utf-8')
print(json.dumps({'result':'CANDIDATE_FREE_DATA_BUILT','head':HEAD,'tree':TREE,'mainHead':main,'mainTree':main_tree,'window':'W625-W644','selectedSources':len(selected),'cells':len(cells),'callerlessSources':sum(x['callerless'] for x in contexts),'callerlessCells':12*sum(x['callerless'] for x in contexts),'directCallerRefs':sum(x['exactMatchCount'] for x in contexts),'tokenMismatches':mismatch,'priorSelectedSources':len(selection_rows),'priorHoldCells':len(hold_rows),'priorAppliedCells':len(applied_rows),'priorReadbacks':[len(prior_w545),len(prior_w565),len(prior_w585),len(w605_rows)],'mainContextDrift':{'missing':main_drift['sourcesMissingFromMain'],'sourceChanged':main_drift['sourceTextChanges'],'contextDrift':main_drift['sourcesWithCallerContextDrift'],'newMainCallers':main_drift['sourcesWithNewMainCallers']}},ensure_ascii=False,sort_keys=True))
