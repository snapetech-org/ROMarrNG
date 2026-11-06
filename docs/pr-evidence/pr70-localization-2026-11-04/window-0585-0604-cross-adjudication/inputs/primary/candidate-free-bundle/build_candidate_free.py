#!/usr/bin/env python3
"""Build the W585-W604 candidate-free input from the exact pinned ROMarrNG PR head."""
import collections, hashlib, json, re, subprocess, urllib.parse
from pathlib import Path
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parent
INPUT=OUT/'candidate-free'/'input'
WORKTREE=Path('/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w585-604-current-source')
OLD=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w565-584-primary-20261104')
EXPECTED_HEAD='01da053f0e6a47e7184fb86da77f66b7b6719653'
EXPECTED_TREE='dcb9c1766831e217ffca7fb77068b97c33b9524e'
PRIOR_HEAD='726db9138af2fc716056c7c36a9e842de04265e0'
PRIOR_TREE='6669dc9117dbbbe6587d4183ec5bd0184c87e983'
BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
KNOWN_PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','Moonlight']
PLACEHOLDER_RE=re.compile(r'\{[^{}]+\}')
TAG_RE=re.compile(r'<[^>]+>')
NUMBER_RE=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')

def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def jl(path): return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]
def dumpjson(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def dumplines(path,rows): Path(path).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in rows),encoding='utf-8')
def git(*args): return subprocess.check_output(['git','-C',str(WORKTREE),*args],text=True).strip()
def gitblob(rel): return git('rev-parse',f'{EXPECTED_HEAD}:{rel}')
def current_file(rel): return WORKTREE/rel

# Exact worktree and live PR refs.
if git('rev-parse','HEAD') != EXPECTED_HEAD or git('rev-parse','HEAD^{tree}') != EXPECTED_TREE: raise SystemExit('FAIL: worktree pin changed')
if git('status','--porcelain=v1','--untracked-files=all'): raise SystemExit('FAIL: exact-head worktree is not clean')
if git('branch','--show-current'): raise SystemExit('FAIL: review worktree must remain detached')

def ghjson(*args): return json.loads(subprocess.check_output(['gh',*args],text=True,cwd=WORKTREE))
def capture_live_attestation():
    org='snapetech-org/ROMarrNG'; pr='70'
    view=ghjson('pr','view',pr,'--repo',org,'--json','state,isDraft,mergeable,headRefName,headRefOid,baseRefName,baseRefOid,url,labels,statusCheckRollup')
    api=ghjson('api',f'repos/{org}/pulls/{pr}')
    tree=ghjson('api',f'repos/{org}/git/commits/{EXPECTED_HEAD}')['tree']['sha']
    refs={}
    for label,ref in [('branch',f'refs/heads/{view["headRefName"]}'),('pull',f'refs/pull/{pr}/head'),('base',f'refs/heads/{view["baseRefName"]}')]:
        out=git('ls-remote','origin',ref); refs[label]=out.split('\t')[0] if out else None
    runs=ghjson('api',f'repos/{org}/commits/{EXPECTED_HEAD}/check-runs')['check_runs']
    status=ghjson('api',f'repos/{org}/commits/{EXPECTED_HEAD}/status')
    deployments=ghjson('api',f'repos/{org}/deployments?ref={urllib.parse.quote(view["headRefName"],safe="")}&sha={EXPECTED_HEAD}&per_page=100')
    att={'result':'PASS','attestedAtUtc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'repository':org,'pullRequest':70,'pullRequestUrl':view['url'],'state':view['state'].upper(),'draft':view['isDraft'],'merged':api['merged'],'mergeable':view.get('mergeable'),'headRefName':view['headRefName'],'head':view['headRefOid'],'tree':tree,'branchRefOid':refs['branch'],'pullRefOid':refs['pull'],'baseRefName':view['baseRefName'],'baseApiSha':api['base']['sha'],'baseLiveRefOid':refs['base'],'baseApiRefMismatch':api['base']['sha']!=refs['base'],'labels':view['labels'],'checkRunCount':len(runs),'checkRuns':[{'name':x.get('name'),'status':x.get('status'),'conclusion':x.get('conclusion')} for x in runs],'statusContexts':status.get('statuses',[]),'deploymentCount':len(deployments),'checksRerun':False}
    if not (att['state']=='OPEN' and att['draft'] is True and att['merged'] is False and att['headRefName']==BRANCH and att['head']==EXPECTED_HEAD and att['tree']==EXPECTED_TREE and att['branchRefOid']==EXPECTED_HEAD and att['pullRefOid']==EXPECTED_HEAD and att['baseRefName']=='main'):
        raise SystemExit('FAIL: live PR/branch/pull ref attestation mismatch: '+repr(att))
    return att

att_before=capture_live_attestation()
OLD_CF=OLD/'candidate-free'/'input'
OLD_SOURCE=Path('/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w565-584-source')
W545_CROSS=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w545-564-cross-20261104')
W545_APP=WORKTREE/'docs/pr-evidence/pr70-localization-2026-11-04/window-0545-0564-cross-adjudication'
W545_CF=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w545-564-primary-20261104/candidate-free/input')
W565_APP=WORKTREE/'docs/pr-evidence/pr70-localization-2026-11-04/window-0565-0584-cross-adjudication'
for d in (OLD_CF,W545_CROSS,W545_APP,W545_CF,W565_APP): subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=d,check=True,stdout=subprocess.DEVNULL)
subprocess.run(['python3',str(OLD_CF/'verify_input.py'),'--repo',str(OLD_SOURCE)],check=True,stdout=subprocess.DEVNULL)
old_manifest=json.loads((OLD_CF/'manifest.json').read_text(encoding='utf-8'))
cross_manifest=json.loads((W545_CROSS/'manifest.json').read_text(encoding='utf-8')); cross_summary=json.loads((W545_CROSS/'summary.json').read_text(encoding='utf-8'))
w545_app_summary=json.loads((W545_APP/'application-summary.json').read_text(encoding='utf-8'))
w565_app_summary=json.loads((W565_APP/'application-summary.json').read_text(encoding='utf-8')); w565_app_manifest=json.loads((W565_APP/'manifest.json').read_text(encoding='utf-8'))
if (old_manifest['head'],old_manifest['tree'],old_manifest['window']) != (PRIOR_HEAD,PRIOR_TREE,'W565-W584'): raise SystemExit('FAIL: prior W565 candidate-free packet pin')
if (cross_manifest['head'],cross_manifest['tree'],cross_manifest['window']) != ('ed82a904e85a95a7f350e6f62d8f06139098054b','73afce4882b42b3284c0dcec9be81be17333232b','W545-W564') or cross_summary['primaryBlindAgreementCount']!=240 or cross_summary['cellCount']!=240: raise SystemExit('FAIL: prior W545 cross packet pin/status')
if (w545_app_summary['window'],w545_app_summary['productCommit'],w545_app_summary['readbackCellCount'],w545_app_summary['changedCellCount']) != ('W545-W564','2a921d8280487f6d172616719f32e3dced243d83',240,2): raise SystemExit('FAIL: prior W545 application readback summary')
if (w565_app_summary['window'],w565_app_summary['productCommit'],w565_app_summary['readbackCellCount'],w565_app_summary['changedCellCount'],w565_app_summary['textFreeHoldCount']) != ('W565-W584','89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac',240,1,40): raise SystemExit('FAIL: current W565 application readback summary')
if (w565_app_manifest['head'],w565_app_manifest['productCommit'],w565_app_manifest['productTree'],w565_app_manifest['window']) != (PRIOR_HEAD,'89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac','919e8da45270e8938db8ca0b1634e38028d147a5','W565-W584'): raise SystemExit('FAIL: W565 application evidence pin')
app_readback=[json.loads(x) for x in (W545_APP/'application-readback.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
W565_APP_READBACK=[json.loads(x) for x in (W565_APP/'application-readback.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
if len(app_readback)!=240 or len(W565_APP_READBACK)!=240: raise SystemExit('FAIL: prior W545/W565 full cell readback')
W545_PRODUCT='2a921d8280487f6d172616719f32e3dced243d83'
W565_PRODUCT='89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac'
W545_CF=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w545-564-primary-20261104/candidate-free/input')
# Current exact-head source manifest.
catalog_path='romarr/ui-labels.json'
messages_doc=json.loads(current_file(catalog_path).read_text(encoding='utf-8'))
messages=messages_doc['messages']
catalog_ids=list(messages)
if len(messages)!=1836: raise SystemExit('FAIL: catalog count changed')
if sha(('\n'.join(catalog_ids)+'\n')) != '40c18afaf80695667f7022e59141a2793799fde35527d608eedb30f8ef4ad055':
    raise SystemExit('FAIL: catalog insertion order changed since W525 packet')
source_registry_path='romarr/ui-source-messages.json'
source_snapshot_path='romarr/ui-source-snapshot.json'
registry_doc=json.loads(current_file(source_registry_path).read_text(encoding='utf-8'))
registry=registry_doc['messages']
raw_source_snapshot=json.loads(current_file(source_snapshot_path).read_text(encoding='utf-8'))
registry_by={r['id']:r for r in registry}
if len(registry_by)!=479 or len(registry)!=479: raise SystemExit('FAIL: active source registry count changed')
source_snapshot={r['id']:r['sourceHash'] for r in registry}
if len(source_snapshot)!=479 or any(raw_source_snapshot.get(k)!=v for k,v in source_snapshot.items()): raise SystemExit('FAIL: active source registry/snapshot mismatch')
if sha(canon(source_snapshot))!=old_manifest['sourceSnapshotSha256']: raise SystemExit('FAIL: source snapshot changed since W565')
if sha(current_file(source_registry_path).read_bytes())!=old_manifest['sourceQueueSha256']: raise SystemExit('FAIL: source queue changed since W565')
active_order_sha=sha('\n'.join(sorted(registry_by))+'\n')
if active_order_sha!=old_manifest['sourceIdOrderSha256']: raise SystemExit('FAIL: active source registry ordering changed since W565')
active_rank={sid:i for i,sid in enumerate(sorted(registry_by),1)}
# Reattest selected IDs, text-free holds, and applied targets through W565-W584.
old_prior=jl(OLD_CF/'prior-selection-reattestation.jsonl'); old_selected=jl(OLD_CF/'source-inventory-selection.jsonl')
if len(old_prior)!=180 or len(old_selected)!=20: raise SystemExit('FAIL: predecessor selected lineage counts')
selection_rows=[]
for row in old_prior:
    idx=row['catalogZeroBasedIndex']; sid=row['sourceId']; item=messages.get(sid)
    if item is None or idx>=len(catalog_ids) or catalog_ids[idx]!=sid: raise SystemExit('FAIL: prior selected source ID/position changed')
    sh=sha(item['source'])
    if sh!=row['priorSourceSha256'] or sh!=row['currentSourceSha256'] or item.get('sourceHash')!=sh: raise SystemExit('FAIL: prior source hash changed')
    selection_rows.append({'priorWindow':row['priorWindow'],'position':row.get('priorWindowPosition',row['position']),'catalogZeroBasedIndex':idx,'sourceId':sid,'priorSourceSha256':row['priorSourceSha256'],'currentSourceSha256':sh,'selectionPositionMatches':True,'sourceHashMatches':True,'registryMembershipAndHashMatch':row.get('registryMembershipAndHashMatch',True) and (sid in registry_by)==(row.get('currentRegistryActive',sid in registry_by)),'priorSelectionEvidenceSha256':sha(canon(row))})
for row in old_selected:
    idx=row['catalogZeroBasedIndex']; sid=row['sourceId']; item=messages.get(sid)
    if item is None or idx not in range(565,585) or catalog_ids[idx]!=sid: raise SystemExit('FAIL: W565 predecessor selected source ID/position changed')
    sh=sha(item['source'])
    if sh!=row['sourceSha256'] or item.get('sourceHash')!=sh: raise SystemExit('FAIL: W565 predecessor source hash changed')
    selection_rows.append({'priorWindow':'W565-W584','position':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'priorSourceSha256':row['sourceSha256'],'currentSourceSha256':sh,'selectionPositionMatches':True,'sourceHashMatches':True,'registryMembershipAndHashMatch':sid in registry_by,'priorSelectionEvidenceSha256':sha(canon(row))})
if len(selection_rows)!=200 or len({x['sourceId'] for x in selection_rows})!=200: raise SystemExit('FAIL: prior selected source count/uniqueness')
old_holds=jl(OLD_CF/'prior-hold-reattestation.jsonl')
if len(old_holds)!=564: raise SystemExit('FAIL: predecessor hold count')
hold_rows=[]
for h in old_holds:
    sid=h['sourceId']; loc=h['locale']; idx=next((i for i,k in enumerate(catalog_ids) if k==sid),None); item=messages.get(sid)
    if item is None or idx is None: raise SystemExit('FAIL: prior hold source missing')
    if sha(item['source'])!=h['sourceSha256'] or sha(item['translations'][loc])!=h['priorTargetSha256']: raise SystemExit('FAIL: prior held target changed')
    rankmatch=(idx==h['position']) if 'catalog insertion index' in h['selectionPositionBasis'] else (active_rank.get(sid)==h['position'])
    if not rankmatch: raise SystemExit('FAIL: prior hold selection position changed')
    hold_rows.append({'window':h['window'],'position':h['position'],'selectionPositionBasis':h['selectionPositionBasis'],'sourceId':sid,'sourceSha256':h['sourceSha256'],'locale':loc,'priorTargetSha256':h['priorTargetSha256'],'currentTargetSha256':sha(item['translations'][loc]),'sourceMatchesCurrentCatalog':True,'selectionPositionMatches':True,'targetUnchanged':True,'priorHoldEvidenceSha256':h['priorHoldEvidenceSha256'],'reattestedAtHead':EXPECTED_HEAD})
W565_HOLD_TEXT={'source','sourceText','currentTarget','target','targetText','proposedTarget','selectedTarget','finalTarget'}
w565_holds=jl(W565_APP/'holds.jsonl')
if len(w565_holds)!=40: raise SystemExit('FAIL: W565 cross-review text-free hold count')
w565_hold_ids=set()
for h in w565_holds:
    if W565_HOLD_TEXT.intersection(h) or 'sourceId' in h: raise SystemExit('FAIL: W565 cross hold exposes source/target text or ID')
    idx=h['catalogZeroBasedIndex']; loc=h['locale']
    if idx not in range(565,585) or loc not in LOCALES: raise SystemExit('FAIL: W565 cross hold source/position changed')
    sid=catalog_ids[idx]; item=messages[sid]; current_hash=sha(item['translations'][loc])
    if sha(item['source'])!=h['sourceSha256'] or current_hash!=h['currentTargetSha256']: raise SystemExit('FAIL: W565 cross held target changed')
    if h.get('disposition')!='hold-text-free' or h.get('window')!='W565-W584': raise SystemExit('FAIL: W565 cross hold disposition/window')
    hold_rows.append({'window':'W565-W584','position':idx,'selectionPositionBasis':'catalog insertion index (zero-based)','sourceId':sid,'sourceSha256':h['sourceSha256'],'locale':loc,'priorTargetSha256':h['currentTargetSha256'],'currentTargetSha256':current_hash,'sourceMatchesCurrentCatalog':True,'selectionPositionMatches':True,'targetUnchanged':True,'callerless':h['callerless'],'holdReasonCode':h['holdReasonCode'],'priorHoldEvidenceSha256':sha(canon(h)),'reattestedAtHead':EXPECTED_HEAD})
    w565_hold_ids.add((sid,loc))
if len(hold_rows)!=604 or len({(x['sourceId'],x['locale']) for x in hold_rows})!=604: raise SystemExit('FAIL: combined historical hold count/uniqueness')
prior_applied_rows=[]; old_applied=jl(OLD_CF/'prior-applied-cell-reattestation.jsonl')
if len(old_applied)!=48: raise SystemExit('FAIL: predecessor applied-cell lineage count')
for x in old_applied:
    sid=x['sourceId']; loc=x['locale']; item=messages.get(sid)
    if item is None or sha(item['source'])!=x['sourceSha256']: raise SystemExit('FAIL: older applied source reattestation')
    current_hash=sha(item['translations'][loc])
    if current_hash!=x['priorSelectedTargetSha256'] or x['currentTargetSha256']!=current_hash: raise SystemExit('FAIL: older applied target hash changed')
    prior_applied_rows.append({'priorWindow':x['priorWindow'],'catalogZeroBasedIndex':catalog_ids.index(sid),'sourceId':sid,'sourceSha256':x['sourceSha256'],'locale':loc,'priorSelectedTargetSha256':x['priorSelectedTargetSha256'],'currentTargetSha256':current_hash,'targetUnchanged':True,'applicationCommit':x['applicationCommit'],'priorAppliedEvidenceSha256':x.get('priorAppliedEvidenceSha256',sha(canon(x))),'reattestedAtHead':EXPECTED_HEAD})
w545_cells=jl(W545_CF/'current-target-cells.jsonl'); w545_cell_map={(x['sourceId'],x['locale']):x for x in w545_cells}
readback_map={(catalog_ids[x['position']],x['locale']):x for x in app_readback}
if len(w545_cell_map)!=240 or len(readback_map)!=240: raise SystemExit('FAIL: W545 candidate/readback coverage')
w545_cell_hash_rows=[]; w545_hold_ids={(h['sourceId'],h['locale']) for h in jl(W545_CROSS/'cross-holds.jsonl')}
for ident,rb in readback_map.items():
    sid,loc=ident; item=messages.get(sid); before=w545_cell_map[ident]
    if item is None or rb['position'] not in range(545,565) or catalog_ids[rb['position']]!=sid: raise SystemExit('FAIL: W545 readback source/position')
    if before['currentTargetSha256']!=rb['beforeTargetSha256']: raise SystemExit('FAIL: W545 readback preimage hash')
    current_hash=sha(item['translations'][loc])
    if current_hash!=rb['afterTargetSha256'] or sha(item['source'])!=rb['sourceSha256'] or rb['sourceSha256']!=before['sourceSha256']: raise SystemExit('FAIL: W545 readback/current hash')
    held=(ident in w545_hold_ids)
    if held != (rb['disposition']=='hold-text-free') or (held and rb['changed']): raise SystemExit('FAIL: W545 hold marker/readback')
    w545_cell_hash_rows.append({'priorWindow':'W545-W564','catalogZeroBasedIndex':rb['position'],'sourceId':sid,'sourceSha256':rb['sourceSha256'],'locale':loc,'beforeTargetSha256':rb['beforeTargetSha256'],'currentTargetSha256':current_hash,'applicationChanged':rb['changed'] is True,'held':held,'applicationCommit':W545_PRODUCT,'targetMatchesApplicationReadback':True,'priorCandidateFreeCellEvidenceSha256':sha(canon(before)),'applicationReadbackCellEvidenceSha256':sha(canon(rb)),'reattestedAtHead':EXPECTED_HEAD})
if len(w545_cell_hash_rows)!=240 or sum(x['applicationChanged'] for x in w545_cell_hash_rows)!=2: raise SystemExit('FAIL: W545 full readback counts')
w565_cells=jl(OLD_CF/'current-target-cells.jsonl'); w565_cell_map={(x['sourceId'],x['locale']):x for x in w565_cells}
w565_readback_map={(catalog_ids[x['catalogZeroBasedIndex']],x['locale']):x for x in W565_APP_READBACK}
if len(w565_cell_map)!=240 or len(w565_readback_map)!=240: raise SystemExit('FAIL: W565 candidate/readback coverage')
w565_cell_hash_rows=[]
for ident,rb in w565_readback_map.items():
    sid,loc=ident; item=messages.get(sid); before=w565_cell_map[ident]
    if item is None or rb['catalogZeroBasedIndex'] not in range(565,585) or catalog_ids[rb['catalogZeroBasedIndex']]!=sid or rb.get('sourceId',sid)!=sid: raise SystemExit('FAIL: W565 readback source/position')
    if before['currentTargetSha256']!=rb['beforeTargetSha256']: raise SystemExit('FAIL: W565 readback preimage hash')
    current_hash=sha(item['translations'][loc])
    if current_hash!=rb['afterTargetSha256'] or sha(item['source'])!=rb['sourceSha256'] or rb['sourceSha256']!=before['sourceSha256']: raise SystemExit('FAIL: W565 readback/current hash')
    held=ident in w565_hold_ids
    if held != (rb['disposition']=='hold-text-free') or (held and rb['changed']): raise SystemExit('FAIL: W565 hold marker/readback')
    w565_cell_hash_rows.append({'priorWindow':'W565-W584','catalogZeroBasedIndex':rb['catalogZeroBasedIndex'],'sourceId':sid,'sourceSha256':rb['sourceSha256'],'locale':loc,'beforeTargetSha256':rb['beforeTargetSha256'],'currentTargetSha256':current_hash,'applicationChanged':rb['changed'] is True,'held':held,'applicationCommit':W565_PRODUCT,'targetMatchesApplicationReadback':True,'reattestedAtHead':EXPECTED_HEAD,'priorCandidateFreeCellEvidenceSha256':sha(canon(before)),'applicationReadbackCellEvidenceSha256':sha(canon(rb))})
    if rb['changed']:
        prior_applied_rows.append({'priorWindow':'W565-W584','catalogZeroBasedIndex':rb['catalogZeroBasedIndex'],'sourceId':sid,'sourceSha256':rb['sourceSha256'],'locale':loc,'priorSelectedTargetSha256':current_hash,'currentTargetSha256':current_hash,'targetUnchanged':True,'applicationCommit':W565_PRODUCT,'priorAppliedEvidenceSha256':sha(canon(rb)),'reattestedAtHead':EXPECTED_HEAD})
if len(w565_cell_hash_rows)!=240 or sum(x['applicationChanged'] for x in w565_cell_hash_rows)!=1 or sum(x['held'] for x in w565_cell_hash_rows)!=40: raise SystemExit('FAIL: W565 full readback counts')
if len(prior_applied_rows)!=49 or len({(x['sourceId'],x['locale']) for x in prior_applied_rows})!=49: raise SystemExit('FAIL: applied-cell reattestation count/uniqueness')
if {x['sourceId'] for x in selection_rows}&set(catalog_ids[585:605]): raise SystemExit('FAIL: new selection overlaps prior selected IDs')
# Source/caller files remain byte-pinned; source/caller files are unchanged from W565 candidate-free input.
old_pins=json.loads((OLD_CF/'catalog-file-pins.json').read_text(encoding='utf-8')); old_caller_pins=old_pins['sourceCallerFilePins']; pin_diffs=[]
for rel,pin in old_caller_pins.items():
    now=sha(current_file(rel).read_bytes())
    if now!=pin['fileSha256'] or gitblob(rel)!=pin['gitBlob']: pin_diffs.append({'path':rel,'priorSha256':pin['fileSha256'],'currentSha256':now,'priorGitBlob':pin['gitBlob'],'currentGitBlob':gitblob(rel),'unexpectedSourceOrCallerChange':True})
if pin_diffs: raise SystemExit('FAIL: source/caller files changed since W565: '+repr([x['path'] for x in pin_diffs]))
current_catalog_hash=sha(current_file(catalog_path).read_bytes()); app_catalog_pins=json.loads((W565_APP/'catalog-pins.json').read_text(encoding='utf-8'))
if current_catalog_hash!=app_catalog_pins['postCatalogSha256'] or gitblob(catalog_path)!=app_catalog_pins['postCatalogGitBlob']: raise SystemExit('FAIL: current catalog does not match W565 application readback')
# Current selected rows, based on exact pinned catalog insertion order.
selected=[]
for idx in range(585,605):
    sid=catalog_ids[idx]; m=messages[sid]; source=m['source']; source_hash=sha(source)
    selected.append({'position':idx,'catalogZeroBasedIndex':idx,'catalogOneBasedPosition':idx+1,'sourceId':sid,'source':source,'sourceSha256':source_hash,'activeSourceRegistry':sid in registry_by,'activeSourceRank':active_rank.get(sid),'registryLocations':registry_by.get(sid,{}).get('locations',[])})
if len(selected)!=20 or len({x['sourceId'] for x in selected})!=20: raise SystemExit('FAIL: W585-W604 selection count')
selected_ids={x['sourceId'] for x in selected}; selection_boundary=[]
for idx,role in [(584,'catalog-before-selected-start'),(585,'selected-start'),(604,'selected-end'),(605,'catalog-after-selected-end')]:
    sid=catalog_ids[idx]; m=messages[sid]; selection_boundary.append({'position':idx,'catalogZeroBasedIndex':idx,'sourceId':sid,'source':m['source'],'sourceSha256':sha(m['source']),'role':role})

# Exact-source search against tracked production code only (tests, docs, and catalogs excluded).
tracked=subprocess.check_output(['git','-C',str(WORKTREE),'ls-files','-z','--','romarr'],text=False).split(b'\0')
source_paths=[]
for raw in tracked:
    if not raw: continue
    rel=raw.decode()
    p=WORKTREE/rel
    if p.suffix.lower() not in ('.py','.js','.html','.jinja','.jinja2','.css','.ts','.tsx'): continue
    parts=rel.lower().split('/')
    if 'test' in parts or 'tests' in parts or '__pycache__' in parts or p.name.startswith('test_') or p.name.endswith('_test.py'): continue
    source_paths.append(rel)
files={}
for rel in source_paths:
    b=current_file(rel).read_bytes()
    try: text=b.decode('utf-8')
    except UnicodeDecodeError: text=b.decode('utf-8','replace')
    files[rel]=(text,b,gitblob(rel))
def source_context(item):
    src=item['source']; matches=[]
    variants=list(dict.fromkeys([json.dumps(src,ensure_ascii=False),repr(src),'"'+src+'"',chr(39)+src+chr(39),'`'+src+'`']))
    # A source ID in a data-i18n/message call is also an exact, source-owned caller.
    id_literal=item['sourceId']
    for rel,(text,b,blob) in files.items():
        occurrences={}
        lines=text.splitlines()
        for literal in variants:
            start=0
            while True:
                at=text.find(literal,start)
                if at<0: break
                occurrences.setdefault(at,'exact quoted source literal')
                start=at+max(1,len(literal))
        start=0
        while True:
            at=text.find(id_literal,start)
            if at<0: break
            occurrences.setdefault(at,'exact source ID reference')
            start=at+len(id_literal)
        # Exact rendered text nodes are common in the embedded UI templates.
        node_re=re.compile(r'>[ \t]*'+re.escape(src)+r'[ \t]*<')
        for hit in node_re.finditer(text):
            occurrences.setdefault(hit.start(),'exact HTML text node')
        for at,kind in sorted(occurrences.items()):
            line_no=text.count('\n',0,at)+1
            lo=max(1,line_no-3); hi=min(len(lines),line_no+3)
            excerpt=[{'line':i,'text':lines[i-1]} for i in range(lo,hi+1)]
            line_text=lines[line_no-1] if line_no<=len(lines) else ''
            matches.append({'path':rel,'line':line_no,'lineText':line_text,'lineSha256':sha(line_text),'excerpt':excerpt,'excerptSha256':sha(canon(excerpt)),'fileSha256':sha(b),'gitBlob':blob,'matchKind':kind})
    matches.sort(key=lambda x:(x['path'],x['line'],x['matchKind']))
    row={'sourceId':item['sourceId'],'source':src,'sourceSha256':item['sourceSha256'],'searchMethod':'exact quoted source literal, exact source ID, or exact HTML text-node search in tracked production code; tests/docs/catalog files excluded','productionFilesSearched':len(files),'exactMatchCount':len(matches),'callerless':not matches,'callers':matches}
    row['contextSha256']=sha(canon(row))
    return row
contexts=[source_context(x) for x in selected]
context_by={x['sourceId']:x for x in contexts}

def protected(source):
    found=[]
    for term in KNOWN_PROTECTED:
        pattern=r'(?<![A-Za-z0-9])'+re.escape(term)+r'(?![A-Za-z0-9])'
        if re.search(pattern,source): found.append(term)
    # Preserve the technical root when English pluralization is attached.
    if re.search(r'(?<![A-Za-z0-9])DATs?(?![A-Za-z0-9])',source) and 'DAT' not in found: found.append('DAT')
    return sorted(set(found))
def tokens(source):
    return {'placeholders':PLACEHOLDER_RE.findall(source),'markup':TAG_RE.findall(source),'numbers':NUMBER_RE.findall(source),'protectedLiterals':protected(source)}

# Build the complete catalog source inventory and all selected current locale cells.
source_inventory=[]
for idx,sid in enumerate(catalog_ids):
    m=messages[sid]; source=m['source']; source_hash=sha(source)
    if m.get('sourceHash')!=source_hash: raise SystemExit('FAIL: catalog sourceHash mismatch: '+sid)
    t=tokens(source)
    source_inventory.append({'catalogZeroBasedIndex':idx,'catalogOneBasedPosition':idx+1,'sourceId':sid,'source':source,'sourceSha256':source_hash,'activeSourceRegistry':sid in registry_by,'activeSourceRank':active_rank.get(sid),'registryLocations':registry_by.get(sid,{}).get('locations',[]),'sourcePlaceholderTokens':t['placeholders'],'sourceMarkupTags':t['markup'],'sourceNumericTokens':t['numbers'],'sourceNumericWords':['Zero'] if re.search(r'\bzero\b',source,re.I) else [],'sourceProtectedLiterals':t['protectedLiterals']})
cells=[]; mismatch_counts={'placeholder':0,'markup':0,'numeric':0,'protectedLiteral':0,'missingTarget':0,'numericPresentationDifferences':0}
for item in selected:
    sid=item['sourceId']; m=messages[sid]; source=m['source']; st=tokens(source); cctx=context_by[sid]
    caller_refs=[{'path':r['path'],'line':r['line'],'lineSha256':r['lineSha256'],'excerptSha256':r['excerptSha256'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob']} for r in cctx['callers']]
    for loc in LOCALES:
        target=m.get('translations',{}).get(loc)
        if not isinstance(target,str):
            mismatch_counts['missingTarget']+=1
            target=''
        tt=tokens(target)
        pm=collections.Counter(st['placeholders'])==collections.Counter(tt['placeholders'])
        mm=collections.Counter(st['markup'])==collections.Counter(tt['markup'])
        source_numeric_words=['Zero'] if re.search(r'\bzero\b',source,re.I) else []
        source_numeric_count=collections.Counter(st['numbers']); target_numeric_count=collections.Counter(tt['numbers'])
        extra_numbers=list((target_numeric_count-source_numeric_count).elements())
        numeric_presentation_equivalent=bool(source_numeric_words and not st['numbers'] and extra_numbers==['0'])
        nm=(not (source_numeric_count-target_numeric_count)) and (not extra_numbers or numeric_presentation_equivalent)
        if numeric_presentation_equivalent: mismatch_counts['numericPresentationDifferences']+=1
        missing=[x for x in st['protectedLiterals'] if x not in target]
        for key,ok in [('placeholder',pm),('markup',mm),('numeric',nm),('protectedLiteral',not missing)]:
            if not ok: mismatch_counts[key]+=1
        cells.append({'position':item['position'],'catalogZeroBasedIndex':item['catalogZeroBasedIndex'],'sourceId':sid,'source':source,'sourceSha256':item['sourceSha256'],'locale':loc,'currentTarget':target,'currentTargetSha256':sha(target),'catalogTranslationHash':m.get('translationHashes',{}).get(loc),'translationStatus':m.get('translationStatus',{}).get(loc),'callerContextSha256':cctx['contextSha256'],'callerRefs':caller_refs,'sourcePlaceholderTokens':st['placeholders'],'currentPlaceholderTokens':tt['placeholders'],'placeholderMultisetMatches':pm,'sourceMarkupTags':st['markup'],'currentMarkupTags':tt['markup'],'markupMatches':mm,'sourceNumericTokens':st['numbers'],'sourceNumericWords':source_numeric_words,'currentNumericTokens':tt['numbers'],'numericTokensPreserved':nm,'numericPresentationEquivalent':numeric_presentation_equivalent,'sourceProtectedLiterals':st['protectedLiterals'],'currentProtectedLiterals':[x for x in st['protectedLiterals'] if x in target],'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing,'containsCandidate':False})

# Pin every source/context file plus current catalog. Source files must remain the same as W525.
file_pins=[]
for rel in sorted(set(source_paths)|{source_registry_path,source_snapshot_path}):
    b=current_file(rel).read_bytes(); file_pins.append({'path':rel,'fileSha256':sha(b),'gitBlob':gitblob(rel),'bytes':len(b)})
catalog_pin={'path':catalog_path,'fileSha256':sha(current_file(catalog_path).read_bytes()),'gitBlob':gitblob(catalog_path),'bytes':len(current_file(catalog_path).read_bytes()),'messageCount':len(messages),'keyOrderSha256':sha('\n'.join(catalog_ids)+'\n')}
current_head=git('rev-parse','HEAD')
current_tree=git('rev-parse','HEAD^{tree}')
now=datetime.now(timezone.utc).isoformat(timespec='seconds')
continuity={'result':'PASS','priorWindow':'W565-W584','priorHead':old_manifest['head'],'priorTree':old_manifest['tree'],'priorProductCommit':W565_PRODUCT,'priorProductTree':w565_app_summary['productTree'],'currentHead':EXPECTED_HEAD,'currentTree':EXPECTED_TREE,'priorCandidateFreePacketChecksumsVerified':True,'priorCrossPacketChecksumsVerified':True,'priorApplicationEvidenceChecksumsVerified':True,'priorSelectedSourceCount':len(selection_rows),'priorSelectedSourceCountUnchanged':len(selection_rows)==200,'priorHoldCellCount':len(hold_rows),'priorHoldCellCountUnchanged':len(hold_rows)==604,'priorHoldChangedCellCount':0,'priorAppliedCells':len(prior_applied_rows),'priorW545CellReadbackRows':len(w545_cell_hash_rows),'priorW545ApplicationSummarySha256':sha((W545_APP/'application-summary.json').read_bytes()),'priorW545ApplicationReadbackSha256':sha((W545_APP/'application-readback.jsonl').read_bytes()),'priorW545ApplicationChecksumListSha256':sha((W545_APP/'SHA256SUMS.txt').read_bytes()),'priorW545CrossPacketChecksumListSha256':sha((W545_CROSS/'SHA256SUMS.txt').read_bytes()),'priorW545CrossPacketManifestSha256':sha((W545_CROSS/'manifest.json').read_bytes()),'priorW545ProductCommit':W545_PRODUCT,'priorW565CandidateFreeManifestSha256':sha((OLD_CF/'manifest.json').read_bytes()),'priorW565CellReadbackRows':len(w565_cell_hash_rows),'priorW565ApplicationSummarySha256':sha((W565_APP/'application-summary.json').read_bytes()),'priorW565ApplicationReadbackSha256':sha((W565_APP/'application-readback.jsonl').read_bytes()),'priorW565ApplicationChecksumListSha256':sha((W565_APP/'SHA256SUMS.txt').read_bytes()),'priorW565CrossHoldLedgerSha256':sha((W565_APP/'holds.jsonl').read_bytes()),'priorW565ProductCommit':W565_PRODUCT,'priorAppliedCellsChanged':0,'historicalSelectionsChanged':0,'historicalHoldsChanged':0,'sourceSnapshotSha256':sha(canon(source_snapshot)),'sourceQueueSha256':sha(current_file(source_registry_path).read_bytes()),'sourceIdOrderSha256':active_order_sha,'currentCatalogSha256':current_catalog_hash,'attestedAtUtc':now}
if current_head!=EXPECTED_HEAD or current_tree!=EXPECTED_TREE: raise SystemExit('FAIL: final worktree pin')
dumpjson(INPUT/'PR-attestation-before.json',att_before)
dumpjson(INPUT/'continuity-reattestation.json',continuity)
dumpjson(INPUT/'catalog-file-pins.json',{'repository':'snapetech-org/ROMarrNG','commit':EXPECTED_HEAD,'tree':EXPECTED_TREE,'baseLocale':'en','activeUniqueSourceIds':len(registry),'catalogMessageCount':len(messages),'catalogPath':catalog_path,'catalogSha256':catalog_pin['fileSha256'],'catalogGitBlob':catalog_pin['gitBlob'],'catalogKeyOrderSha256':catalog_pin['keyOrderSha256'],'sourceQueuePath':source_registry_path,'sourceQueueSha256':sha(current_file(source_registry_path).read_bytes()),'sourceSnapshotPath':source_snapshot_path,'sourceSnapshotSha256':sha(canon(source_snapshot)),'sourceIdOrderSha256':active_order_sha,'sourceCallerFilePins':{x['path']:{'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in file_pins}})
dumpjson(INPUT/'source-file-pins.json',{'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'files':file_pins})
dumplines(INPUT/'prior-applied-cell-reattestation.jsonl',prior_applied_rows)
dumplines(INPUT/'prior-window-cell-hash-reattestation.jsonl',w545_cell_hash_rows)
dumplines(INPUT/'prior-w565-window-cell-hash-reattestation.jsonl',w565_cell_hash_rows)
dumpjson(INPUT/'prior-applied-cell-reattestation-summary.json',{'priorWindows':dict(collections.Counter(x['priorWindow'] for x in prior_applied_rows)),'applicationCommits':{'W505-W524':'b248261d5aaa33ec7247023b85d666ed7fc89309','W525-W544':'63224167b0f89978a68977a7996bd06724d06129','W545-W564':W545_PRODUCT,'W565-W584':W565_PRODUCT},'reattestedCellCount':len(prior_applied_rows),'allSelectedTargetHashesMatchCurrentCatalog':True,'changedCells':0,'currentHead':EXPECTED_HEAD,'currentTree':EXPECTED_TREE})
dumpjson(INPUT/'prior-selection-reattestation-summary.json',{'priorWindows':dict(collections.Counter(x['priorWindow'] for x in selection_rows)),'reattestedSelectedSourceCount':len(selection_rows),'allPriorSelectionsMatchCurrentCatalogAndRegistry':True,'currentHead':EXPECTED_HEAD,'currentTree':EXPECTED_TREE})
dumpjson(INPUT/'prior-hold-reattestation-summary.json',{'reattestedCellCount':len(hold_rows),'windowCounts':dict(collections.Counter(x['window'] for x in hold_rows)),'allSourcesAndSelectionPositionsMatchCurrentSnapshot':True,'allCurrentTargetHashesMatchPriorHoldEvidence':True,'currentTargetChangedCells':0,'currentHead':EXPECTED_HEAD,'currentTree':EXPECTED_TREE})
dumpjson(INPUT/'selection.json',{'window':'W585-W604','method':'Select catalog message insertion indices 585 through 604 (zero-based) from exact pinned ui-labels.json message key order; this differs from active source registry sort.','positions':[585,604],'catalogInsertionPositionsOneBased':[586,605],'sourceCount':20,'localeCount':12,'cellCount':240,'localeOrder':LOCALES,'activeUniqueSourceIds':len(registry),'sourceIdOrderSha256':active_order_sha,'catalogMessageCount':len(messages),'catalogKeyOrderSha256':catalog_pin['keyOrderSha256'],'selectedSources':selected})
dumpjson(INPUT/'registry-order-note.json',{'selectionBasis':'catalog JSON message-key insertion order','selectedCatalogZeroBasedIndices':[585,604],'activeRegistryCount':len(registry),'selectedIdsInActiveRegistry':sum(x['activeSourceRegistry'] for x in selected),'activeRegistryMatches':[{'sourceId':x['sourceId'],'activeRank':x['activeSourceRank'],'registryLocations':x['registryLocations']} for x in selected if x['activeSourceRegistry']],'lineHintCaveat':'Active source registry metadata does not substitute for the exact literal caller search and excerpt evidence.'})
dumpjson(INPUT/'manifest.json',{'artifact':'ROMarrNG PR #70 W585-W604 candidate-free input','repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':BRANCH,'baseRefName':'main','head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'window':'W585-W604','selectionBasis':'catalog insertion order; exact pinned ui-labels.json message indices 585..604','sourceCount':20,'localeCount':12,'cellCount':240,'locales':LOCALES,'activeUniqueSourceIdCount':len(registry),'sourceIdOrderSha256':active_order_sha,'catalogMessageCount':len(messages),'catalogPath':catalog_path,'catalogSha256':catalog_pin['fileSha256'],'catalogKeyOrderSha256':catalog_pin['keyOrderSha256'],'sourceQueuePath':source_registry_path,'sourceQueueSha256':sha(current_file(source_registry_path).read_bytes()),'sourceSnapshotSha256':sha(canon(source_snapshot)),'priorSelectedSourceCount':len(selection_rows),'priorSelectionsUnchanged':True,'priorHoldCellCount':len(hold_rows),'priorHoldTargetsUnchanged':True,'priorHoldCellChangedCount':0,'priorAppliedSelectedCellCount':len(prior_applied_rows),'priorAppliedTargetsUnchanged':True,'currentTargetPlaceholderMismatches':mismatch_counts['placeholder'],'currentTargetMarkupMismatches':mismatch_counts['markup'],'currentTargetNumericMismatches':mismatch_counts['numeric'],'currentTargetNumericPresentationDifferences':mismatch_counts['numericPresentationDifferences'],'currentTargetProtectedLiteralMismatches':mismatch_counts['protectedLiteral'],'currentTargetMissingCells':mismatch_counts['missingTarget'],'callerSearchQueryCount':20,'sourceContextCount':20,'callerlessSourceCount':sum(x['callerless'] for x in contexts),'callerlessCurrentTargetCellCount':12*sum(x['callerless'] for x in contexts),'directCallerRefCount':sum(x['exactMatchCount'] for x in contexts),'activeRegistrySelectedSourceCount':sum(x['activeSourceRegistry'] for x in selected),'candidateFree':True,'proposedTargetsIncluded':False,'reviewDecisionsIncluded':False,'sourceQueueCurrentHead':EXPECTED_HEAD,'priorW545FullCellHashReadbackCount':len(w545_cell_hash_rows),'priorW545ChangedAppliedCellCount':2,'priorW545ApplicationSummarySha256':sha((W545_APP/'application-summary.json').read_bytes()),'priorW545ApplicationReadbackSha256':sha((W545_APP/'application-readback.jsonl').read_bytes()),'priorW545CrossPacketManifestSha256':sha((W545_CROSS/'manifest.json').read_bytes()),'priorW545ProductCommit':W545_PRODUCT,'priorW565FullCellHashReadbackCount':len(w565_cell_hash_rows),'priorW565ChangedAppliedCellCount':1,'priorW565TextFreeHoldCount':len(w565_holds),'priorW565CallerlessHoldCount':w565_app_summary['callerlessHoldCount'],'priorW565ContextualHoldCount':w565_app_summary['contextualHoldCount'],'priorW565ApplicationSummarySha256':sha((W565_APP/'application-summary.json').read_bytes()),'priorW565ApplicationReadbackSha256':sha((W565_APP/'application-readback.jsonl').read_bytes()),'priorW565CrossHoldLedgerSha256':sha((W565_APP/'holds.jsonl').read_bytes()),'priorW565ProductCommit':W565_PRODUCT,'priorW505ToW545AppliedCellCount':48,'priorW565CandidateFreeManifestSha256':sha((OLD_CF/'manifest.json').read_bytes()),'previousWindowContinuityReattestation':'continuity-reattestation.json','createdUtc':now,'reviewBoundary':'Fresh current-head input with exact source/caller context, current targets, token checks, full source inventory, and hash-only historical selection/hold/application reattestation. It contains no proposed targets or current-window review decisions.'})
dumplines(INPUT/'catalog-source-inventory.jsonl',source_inventory)
dumplines(INPUT/'source-inventory-selection.jsonl',selected)
dumplines(INPUT/'selection-boundary.jsonl',selection_boundary)
dumplines(INPUT/'source-contexts.jsonl',contexts)
dumplines(INPUT/'prior-selection-reattestation.jsonl',selection_rows)
dumplines(INPUT/'prior-hold-reattestation.jsonl',hold_rows)
dumplines(INPUT/'current-target-cells.jsonl',cells)
dumpjson(INPUT/'source-snapshot.json',source_snapshot)
# Copy exact pinned source queue, never a prior proposal file.
(INPUT/'source-queue.json').write_bytes(current_file(source_registry_path).read_bytes())
dumpjson(INPUT/'caller-search-audit.json',{'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'queryCount':20,'searchScope':'tracked production source files under romarr; tests, documentation, and locale catalogs excluded','productionFilesSearched':len(files),'results':[{'sourceId':c['sourceId'],'sourceSha256':c['sourceSha256'],'matchCount':c['exactMatchCount'],'callerless':c['callerless'],'contextSha256':c['contextSha256']} for c in contexts]})
dumpjson(INPUT/'current-target-token-mismatches.json',{'placeholder':mismatch_counts['placeholder'],'markup':mismatch_counts['markup'],'numeric':mismatch_counts['numeric'],'numericPresentationDifferences':mismatch_counts['numericPresentationDifferences'],'protectedLiteral':mismatch_counts['protectedLiteral'],'missingTarget':mismatch_counts['missingTarget']})
dumpjson(INPUT/'dispatch-mechanics.json',{'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'sourceFiles':[x for x in file_pins if x['path'] in ('romarr/i18n_runtime.js','romarr/ui.py','romarr/ui-source-messages.json')],'description':'Source string lookup and locale dispatch are pinned through the exact source file hashes; this record is source ownership evidence only.'})
# Context contract and candidate-free README.
att_after=capture_live_attestation()
for field in ('state','draft','merged','headRefName','head','tree','branchRefOid','pullRefOid','baseRefName','baseApiSha','baseLiveRefOid','checkRuns','statusContexts','deploymentCount'):
    if att_after.get(field)!=att_before.get(field): raise SystemExit('FAIL: live PR/check/deployment state changed during candidate extraction: '+field)
dumpjson(INPUT/'PR-attestation-after-candidate-free.json',att_after)
(OUT/'candidate-free'/'README.md').write_text(f"""# ROMarrNG PR #70 W585-W604 current-head candidate-free input

Pinned to OPEN/DRAFT PR head {EXPECTED_HEAD}, tree {EXPECTED_TREE}, branch {BRANCH}. This fresh packet covers catalog insertion positions 585-604 (one-based 586-605), across all 12 review locales, for 240 cells.

The exact current pin is the W565-W584 evidence commit after product commit {W565_PRODUCT}. Prior W565 candidate-free source and selection lineage, cross-review text-free holds, and full application readback were checksum-verified and reattested by source, target, and application hashes. Historical lineage carries 200 selected source IDs, 604 text-free held cells, and 49 applied target cells. This window has {sum(x['callerless'] for x in contexts)} callerless sources ({12*sum(x['callerless'] for x in contexts)} cells).

The input contains current source and target text plus exact caller context for independent review. It contains no proposed targets or current-window decisions. The stale W585 primary packet was not used to produce this input.

Verify with `python3 verify_input.py --repo {WORKTREE}` from `candidate-free/input`.
""",encoding='utf-8')
# Freeze an input file manifest before checksumming the packet.
final_manifest=json.loads((INPUT/'manifest.json').read_text(encoding='utf-8'))
final_manifest['files']=[{'path':x.name,'bytes':len(x.read_bytes()),'sha256':sha(x.read_bytes())} for x in sorted(INPUT.iterdir()) if x.is_file() and x.name not in ('manifest.json','SHA256SUMS.txt')]
dumpjson(INPUT/'manifest.json',final_manifest)
print(json.dumps({'result':'CANDIDATE_FREE_BUILT','head':EXPECTED_HEAD,'tree':EXPECTED_TREE,'selectedSources':len(selected),'cells':len(cells),'callerlessSources':sum(x['callerless'] for x in contexts),'callerlessCells':12*sum(x['callerless'] for x in contexts),'directCallerRefs':sum(x['exactMatchCount'] for x in contexts),'tokenMismatches':mismatch_counts,'priorSelectedSources':len(selection_rows),'priorHoldCells':len(hold_rows),'priorAppliedCells':len(prior_applied_rows),'priorW545ReadbackCells':len(w545_cell_hash_rows),'priorW565ReadbackCells':len(w565_cell_hash_rows),'priorW565ChangedAppliedCells':sum(x['applicationChanged'] for x in w565_cell_hash_rows)},ensure_ascii=False,sort_keys=True))
