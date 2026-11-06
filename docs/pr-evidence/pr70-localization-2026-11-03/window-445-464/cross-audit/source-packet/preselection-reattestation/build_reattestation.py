#!/usr/bin/env python3
from pathlib import Path
from collections import defaultdict
import hashlib,json,subprocess,sys,datetime

OUT=Path(__file__).resolve().parent
SCRATCH=Path('/home/keith/Documents/code/task-scratch')
CF=OUT/'candidate-free-input'
PRIMARY=OUT/'primary-review'
BLIND=OUT/'blind-review-input'
BASE='d5ba7f1f268501f45227388c46d5f938ed0c9191'
BASE_TREE='2f8ce1af963b315108f668fc31c94ca90ecd1351'
HEAD='81a499b7c022bde61a63dbd8c68c0b1ca39adf26'
TREE='1b075e050610771fc5651d1a4ca95d7c7b4b8e46'
BRANCH='task/localization-translation-review-20261030'
REPO_NAME='snapetech-org/ROMarrNG'
REPO=SCRATCH/'romarrng-pr70-w425-444-evidence-copy-20261103/repo'
SOURCE_REPO=SCRATCH/'romarrng-pr70-w445-464-candidate-free-20261103/source-repo'
ORIG_BLIND=SCRATCH/'romarrng-pr70-w445-464-blind-20261103'


def sha(b):return hashlib.sha256(b).hexdigest()
def j(p):return json.loads(p.read_text(encoding='utf-8'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def blob(repo,commit,path):return subprocess.check_output(['git','-C',str(repo),'rev-parse',f'{commit}:{path}'],text=True).strip()
def show(repo,commit,path):return subprocess.check_output(['git','-C',str(repo),'show',f'{commit}:{path}'])

def add_pin(pins,path,sha256=None,git_blob=None,source=None):
    if not isinstance(path,str) or not path or path.startswith('/') or '..' in Path(path).parts:
        return
    entry=pins.setdefault(path,{'sources':[],'sha256':set(),'gitBlob':set()})
    if source and source not in entry['sources']:entry['sources'].append(source)
    if sha256:entry['sha256'].add(sha256)
    if git_blob:entry['gitBlob'].add(git_blob)

def scan_refs(obj,pins,source):
    if isinstance(obj,dict):
        if isinstance(obj.get('path'),str) and obj.get('gitBlob'):
            add_pin(pins,obj['path'],obj.get('fileSha256') or obj.get('sha256'),obj.get('gitBlob'),source)
        for v in obj.values():scan_refs(v,pins,source)
    elif isinstance(obj,list):
        for v in obj:scan_refs(v,pins,source)

# Verify all original review packets before reading their pins.
subprocess.check_call(['sha256sum','-c','SHA256SUMS.txt'],cwd=CF,stdout=subprocess.DEVNULL)
subprocess.check_call([sys.executable,'verify_input.py'],cwd=CF,stdout=subprocess.DEVNULL)
subprocess.check_call(['sha256sum','-c','SHA256SUMS.txt'],cwd=PRIMARY,stdout=subprocess.DEVNULL)
subprocess.check_call([sys.executable,'verify_primary_portable.py'],cwd=OUT,stdout=subprocess.DEVNULL)

# Exact-head checks: candidate-free/primary were authored at d5ba; latest live PR is the docs-only child.
pr=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO_NAME}/pulls/70'],text=True))
refs_raw=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head'],text=True)
refs={line.split('\t',1)[1]:line.split('\t',1)[0] for line in refs_raw.splitlines() if '\t' in line}
api_tree=subprocess.check_output(['gh','api',f'repos/{REPO_NAME}/git/commits/{HEAD}','--jq','.tree.sha'],text=True).strip()
if pr['state']!='open' or pr['draft'] is not True or pr['head']['ref']!=BRANCH or pr['head']['sha']!=HEAD:raise SystemExit('live PR not at expected OPEN/DRAFT head')
if api_tree!=TREE or refs!={f'refs/heads/{BRANCH}':HEAD,'refs/pull/70/head':HEAD}:raise SystemExit('latest PR tree or refs differ')
if git(SOURCE_REPO,'rev-parse','HEAD')!=BASE or git(SOURCE_REPO,'rev-parse','HEAD^{tree}')!=BASE_TREE:raise SystemExit('candidate-free source checkout moved')
if git(REPO,'rev-parse','HEAD')!=HEAD or git(REPO,'rev-parse','HEAD^{tree}')!=TREE:raise SystemExit('current checkout is not latest live head/tree')
if git(SOURCE_REPO,'status','--porcelain') or git(REPO,'status','--porcelain'):raise SystemExit('one of the pinned checkouts is dirty')
if git(REPO,'rev-parse','HEAD^')!=BASE:raise SystemExit('latest evidence commit parent differs from candidate-free base')

cf_manifest=j(CF/'manifest.json'); primary_manifest=j(PRIMARY/'manifest.json')
if (cf_manifest['head'],cf_manifest['tree'])!=(BASE,BASE_TREE) or (primary_manifest['head'],primary_manifest['tree'])!=(BASE,BASE_TREE):raise SystemExit('candidate-free or primary manifest pin mismatch')
if sha((CF/'manifest.json').read_bytes())!=primary_manifest['candidateFreeInputManifestSha256'] or sha((CF/'SHA256SUMS.txt').read_bytes())!=primary_manifest['candidateFreeInputChecksumsSha256']:raise SystemExit('primary packet does not pin copied candidate-free packet')

# Capture every tracked source/catalog/caller/input file pin found in candidate-free, primary, and blind-input artifacts.
pins=defaultdict(lambda:{'sources':[],'sha256':set(),'gitBlob':set()})
cf_pins=j(CF/'catalog-file-pins.json')
for path,info in cf_pins.get('callerSourceFilePins',{}).items():add_pin(pins,path,info.get('fileSha256'),info.get('gitBlob'),'candidate-free catalog-file-pins')
qpath=cf_pins.get('sourceQueuePath')
if qpath and qpath in cf_pins.get('callerSourceFilePins',{}):add_pin(pins,qpath,cf_pins.get('sourceQueueSha256'),cf_pins['callerSourceFilePins'][qpath].get('gitBlob'),'candidate-free source queue')
for path in sorted(CF.rglob('*')):
    if not path.is_file() or path.suffix not in ('.json','.jsonl'):continue
    try: data=json.loads(path.read_text()) if path.suffix=='.json' else [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    except Exception:continue
    scan_refs(data,pins,'candidate-free '+path.relative_to(CF).as_posix())
for path in sorted(PRIMARY.rglob('*')):
    if not path.is_file() or path.suffix not in ('.json','.jsonl'):continue
    try:data=json.loads(path.read_text()) if path.suffix=='.json' else [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    except Exception:continue
    scan_refs(data,pins,'primary '+path.relative_to(PRIMARY).as_posix())
prelim=ORIG_BLIND/'evidence/preliminary-registry-rank-extraction/input'
if (prelim/'file-pins.json').is_file():
    fp=j(prelim/'file-pins.json')
    for path,info in fp.get('files',{}).items():
        add_pin(pins,info.get('path',path),info.get('sha256'),info.get('gitBlob'),'blind preliminary file-pins')
    for path in sorted(prelim.rglob('*')):
        if not path.is_file() or path.suffix not in ('.json','.jsonl'):continue
        try:data=json.loads(path.read_text()) if path.suffix=='.json' else [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        except Exception:continue
        scan_refs(data,pins,'blind preliminary '+path.relative_to(prelim).as_posix())

resolved=[]
for path,info in sorted(pins.items()):
    shas=sorted(info['sha256']); blobs=sorted(info['gitBlob'])
    if len(shas)>1 or len(blobs)>1:raise SystemExit(f'conflicting pinned hashes for {path}: sha={shas} blob={blobs}')
    expected_sha=shas[0] if shas else None; expected_blob=blobs[0] if blobs else None
    raw_base=show(SOURCE_REPO,BASE,path); raw_latest=show(REPO,HEAD,path)
    blob_base=blob(SOURCE_REPO,BASE,path); blob_latest=blob(REPO,HEAD,path)
    record={'path':path,'sources':sorted(info['sources']),'bytes':len(raw_base),'pinnedSha256':expected_sha,'pinnedGitBlob':expected_blob,
            'baseSha256':sha(raw_base),'latestSha256':sha(raw_latest),'baseGitBlob':blob_base,'latestGitBlob':blob_latest,
            'rawBytesMatch':raw_base==raw_latest,'pinnedShaMatches':expected_sha is None or sha(raw_base)==expected_sha,
            'pinnedBlobMatches':expected_blob is None or blob_base==expected_blob,
            'latestShaMatches':expected_sha is None or sha(raw_latest)==expected_sha,
            'latestBlobMatches':expected_blob is None or blob_latest==expected_blob}
    if not all(record[k] for k in ('rawBytesMatch','pinnedShaMatches','pinnedBlobMatches','latestShaMatches','latestBlobMatches')):raise SystemExit('relevant source/catalog/input pin drift: '+path)
    resolved.append(record)
if not resolved:raise SystemExit('no relevant Git blob pins were collected')

# Verify current targets against both exact catalog blobs and align candidate-free/primary/blind input copies.
catalog_path='romarr/ui-labels.json'
cat_base=json.loads(show(SOURCE_REPO,BASE,catalog_path));cat_latest=json.loads(show(REPO,HEAD,catalog_path))
if cat_base!=cat_latest:raise SystemExit('catalog JSON changed from base to latest')
rows=jl(CF/'current-target-cells.jsonl'); primary_rows=jl(PRIMARY/'primary-ledger.jsonl')
if len(rows)!=240 or len(primary_rows)!=240:raise SystemExit('candidate-free/primary coverage mismatch')
cf_by={(r['position'],r['locale']):r for r in rows};pr_by={(r['position'],r['locale']):r for r in primary_rows}
if set(cf_by)!=set(pr_by):raise SystemExit('candidate-free/primary cell key mismatch')
for k,c in cf_by.items():
    p=pr_by[k]
    if p['sourceId']!=c['sourceId'] or p['sourceSha256']!=c['sourceSha256'] or p['currentTargetSha256']!=c['currentTargetSha256'] or p['currentTarget']!=c['currentTarget']:raise SystemExit(f'candidate-free/primary data mismatch {k}')
    msg=cat_base['messages'].get(c['sourceId'])
    if not msg or msg.get('source')!=c['source'] or msg.get('translations',{}).get(c['locale'])!=c['currentTarget'] or hashlib.sha256(msg['translations'][c['locale']].encode()).hexdigest()!=c['currentTargetSha256']:raise SystemExit(f'base catalog target mismatch {k}')
    msg2=cat_latest['messages'].get(c['sourceId'])
    if not msg2 or msg2.get('source')!=c['source'] or msg2.get('translations',{}).get(c['locale'])!=c['currentTarget'] or hashlib.sha256(msg2['translations'][c['locale']].encode()).hexdigest()!=c['currentTargetSha256']:raise SystemExit(f'latest catalog target mismatch {k}')
blind_copy=ORIG_BLIND/'input/candidate-free-input'
if not blind_copy.is_dir():raise SystemExit('blind input has no candidate-free source copy')
blind_copy_match=subprocess.run(['diff','-qr',str(CF),str(blind_copy)],capture_output=True,text=True)
if blind_copy_match.returncode!=0:raise SystemExit('blind candidate-free input copy differs from primary/candidate-free source packet')

# Inspect the explicitly preliminary registry-rank extraction separately. It is not a sealed blind review;
# reject it as a substitute if it does not align with the catalog-insertion candidate-free selection.
prelim_rows=jl(prelim/'source-cells.jsonl') if (prelim/'source-cells.jsonl').is_file() else []
cand_sel=jl(CF/'source-inventory-selection.jsonl')
cand_ids={r['position']:r['sourceId'] for r in cand_sel}
prelim_ids={r['position']:r.get('sourceId',r.get('id')) for r in prelim_rows}
prelim_same=sum(cand_ids.get(pos)==prelim_ids.get(pos) for pos in cand_ids.keys() & prelim_ids.keys())
prelim_overlap=len(set(cand_ids.values()) & set(prelim_ids.values()))
final_blind_ledger_candidates=[str(p) for p in ORIG_BLIND.rglob('cell-review.jsonl') if 'preliminary-registry-rank-extraction' not in str(p)]

# Pin packet files and attest no repo source/catalog/caller/input file changed in this docs-only child.
changed=git(REPO,'diff-tree','--no-commit-id','--name-status','-r',BASE,HEAD).splitlines()
change_records=[]
for line in changed:
    status,path=line.split('\t',1)
    change_records.append({'status':status,'path':path})
if any(rec['status']!='A' or not rec['path'].startswith('docs/pr-evidence/pr70-localization-2026-11-03/window-425-444/') for rec in change_records):raise SystemExit('unexpected non-evidence change between d5ba and latest head')

# Final live observation after all reads; fail if the PR/ref changed during the check.
pr_after=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO_NAME}/pulls/70'],text=True))
refs_after_raw=subprocess.check_output(['git','-C',str(REPO),'ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head'],text=True)
refs_after={line.split('\t',1)[1]:line.split('\t',1)[0] for line in refs_after_raw.splitlines() if '\t' in line}
tree_after=subprocess.check_output(['gh','api',f'repos/{REPO_NAME}/git/commits/{HEAD}','--jq','.tree.sha'],text=True).strip()
if pr_after['state']!='open' or pr_after['draft'] is not True or pr_after['head']['sha']!=HEAD or tree_after!=TREE or refs_after!={f'refs/heads/{BRANCH}':HEAD,'refs/pull/70/head':HEAD}:raise SystemExit('live PR/ref changed during head reattestation')
body=pr_after.get('body') or ''
marker='<!-- ROMARRNG-PR70-W425-W444-APPLIED: d5ba7f1f268501f45227388c46d5f938ed0c9191 -->'
section=body.split('## W425–W444 localization review',1)[-1].split(marker,1)[0] if '## W425–W444 localization review' in body else ''
body_evidence={'sha256':sha(body.encode('utf-8')),'appliedMarkerCount':body.count(marker),
               'w425W444ReadmeLinkPresent':'window-425-444/README.md' in section,
               'w425W444VerifierLinkPresent':'window-425-444/verify_window_bundle.py' in section}
if body_evidence['appliedMarkerCount']!=1 or not body_evidence['w425W444ReadmeLinkPresent'] or not body_evidence['w425W444VerifierLinkPresent']:
    raise SystemExit('PR body evidence links/marker are missing or duplicated')

# Store complete independently checkable observations.
prelim_path='evidence/preliminary-registry-rank-extraction/input/source-cells.jsonl'
result={'schemaVersion':1,'artifact':'ROMarrNG PR #70 W445-W464 preselection exact-head reattestation',
'repository':REPO_NAME,'pullRequest':70,'branch':BRANCH,'candidateFreePrimaryBaseHead':BASE,'candidateFreePrimaryBaseTree':BASE_TREE,
'latestLiveHead':HEAD,'latestLiveTree':TREE,'latestParent':git(REPO,'rev-parse','HEAD^'),'liveState':'OPEN','isDraft':True,
'branchAndPullRefsBefore':refs,'branchAndPullRefsAfter':refs_after,'prBaseRefName':pr_after['base']['ref'],'prBaseRefOid':pr_after['base']['sha'],'prBodyEvidenceLinks':body_evidence,
'candidateFreeVerifier':'PASS','primaryVerifier':'PASS','candidateFreeCells':240,'primaryCells':240,'candidateFreePrimaryCurrentTargetsAligned':True,
'blindInputCandidateFreeCopyByteIdentical':True,'blindFinalReviewLedgerAvailable':bool(final_blind_ledger_candidates),
'blindFinalReviewLedgerPaths':final_blind_ledger_candidates,'blindPreliminaryRegistryRankExtraction':{'path':prelim_path,'fileSha256':hashlib.sha256((prelim/'source-cells.jsonl').read_bytes()).hexdigest() if (prelim/'source-cells.jsonl').is_file() else None,'cellRows':len(prelim_rows),'samePositionSourceIdMatches':prelim_same,'sourceIdOverlapCount':prelim_overlap,'useForCrossAudit':False,'reason':'It is labeled preliminary-registry-rank-extraction and does not align with the catalog-insertion candidate-free source set; only the copied candidate-free input is authoritative for the pending blind review.'},
'relevantGitPinCount':len(resolved),'relevantGitPins':resolved,'sourceContextReferenceCount':sum(len(r.get('callerContextRefs',[])) for r in jl(CF/'source-contexts.jsonl')),
'changedPathsBaseToLatest':change_records,'changedPathCount':len(change_records),'allChangesConfinedToNewW425W444Evidence':True,
'catalogStructure':{'catalogPath':catalog_path,'sha256Base':hashlib.sha256(show(SOURCE_REPO,BASE,catalog_path)).hexdigest(),'sha256Latest':hashlib.sha256(show(REPO,HEAD,catalog_path)).hexdigest(),'messageCount':len(cat_base['messages']),'orderedSourceIdsSha256':cf_pins['catalogKeyOrderSha256'],'all240CurrentTargetHashesReattestedAtBothHeads':True},
'reattestationResult':'PASS','selectionGate':'Await a sealed blind decision ledger; do not adjudicate or apply W445-W464 yet.'}
(OUT/'head-reattestation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','relevantGitPinCount':len(resolved),'currentTargetsReattested':240,'sourceContextReferences':result['sourceContextReferenceCount'],'changedPaths':len(change_records),'allChangedPathsAreW425Evidence':True,'blindFinalReviewLedgerAvailable':bool(final_blind_ledger_candidates),'preliminaryBlindSamePositionMatches':prelim_same,'preliminaryBlindSourceIdOverlap':prelim_overlap,'selectionGate':result['selectionGate']},indent=2))
