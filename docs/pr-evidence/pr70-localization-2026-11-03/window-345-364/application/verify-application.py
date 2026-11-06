#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
EVIDENCE=HERE.parent
REPO=EVIDENCE.parents[3]
PACKETS=EVIDENCE/'review-packets'
INPUT=PACKETS/'primary'/'input'; PRIMARY=PACKETS/'primary'/'review'
BLIND_INPUT=PACKETS/'blind'/'input'; BLIND=PACKETS/'blind'/'review'
CROSS=PACKETS/'cross-audit'
BASE='6bef0c74632067906fd07279fa6bd3fd59159a48'
BASE_TREE='4fd79e67f37e4c66d0253199418973d965a3fbd6'
CATALOG='romarr/ui-labels.json'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(raw): return hashlib.sha256(raw).hexdigest()
def rawsha(text): return sha(text.encode('utf-8'))
def catalog_hash(value):
    compact=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return rawsha(compact)
def readj(path): return json.loads(path.read_text(encoding='utf-8'))
def readjl(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def git(*args): return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
def git_bytes(*args): return subprocess.check_output(['git',*args],cwd=REPO)
def verify_sums(folder, name='SHA256SUMS.txt'):
    for line in (folder/name).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected,rel=line.split(None,1); rel=rel.lstrip(' *')
        target=folder/rel
        assert target.is_file() and sha(target.read_bytes())==expected,f'checksum mismatch: {target}'
def run_packet(path):
    p=subprocess.run(['python3',str(path)],cwd=REPO,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert p.returncode==0,(path,p.stdout,p.stderr)
    return p.stdout.strip()
def index(rows):
    result={(r['position'],r['locale']):r for r in rows}
    assert len(result)==len(rows)
    return result

# Verify every sealed input/review packet copied into the PR evidence directory.
for d in (INPUT,PRIMARY,BLIND,CROSS): verify_sums(d)
assert {x.name for x in INPUT.iterdir()}=={x.name for x in BLIND_INPUT.iterdir()}
for file in INPUT.iterdir(): assert sha(file.read_bytes())==sha((BLIND_INPUT/file.name).read_bytes()),file.name
input_summary=run_packet(INPUT/'verify_input.py')
primary_summary=run_packet(PRIMARY/'verify_primary.py')
cross_summary_text=run_packet(CROSS/'verify_cross_audit_copied.py')
manifest=readj(INPUT/'manifest.json')
assert manifest['head']==BASE and manifest['tree']==BASE_TREE and manifest['cellCount']==240
assert manifest['candidateFree'] is True and manifest['priorHoldCellCount']==288 and manifest['priorHoldTargetsUnchanged'] is True
assert manifest['translationDispatchGapPositions']==[346,350]

# Verify the exact parent commit and the live PR branch. This works before commit at BASE,
# and after push when this commit is the direct child of BASE and the PR points to it.
head=git('rev-parse','HEAD'); tree=git('rev-parse','HEAD^{tree}')
if head==BASE: assert tree==BASE_TREE
else: assert git('rev-parse','HEAD^')==BASE
live=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/ROMarrNG/pulls/70','--jq','{state:.state,draft:.draft,headRef:.head.ref,head:.head.sha,baseRef:.base.ref,base:.base.sha}'],cwd=REPO,text=True))
branch=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/ROMarrNG/git/ref/heads/task/localization-translation-review-20261030'],cwd=REPO,text=True))
assert live['state']=='open' and live['draft'] is True and live['headRef']=='task/localization-translation-review-20261030' and live['baseRef']=='main'
assert branch['object']['sha']==live['head']
if head==BASE: assert live['head']==BASE
else: assert live['head']==head

current=index(readjl(INPUT/'current-target-cells.jsonl'))
primary=index(readjl(PRIMARY/'review-decisions.jsonl'))
blind=index(readjl(BLIND/'blind-ledger.jsonl'))
cross=index(readjl(CROSS/'cross-audit-ledger.jsonl'))
plan=index(readjl(HERE/'application-plan.jsonl'))
readback=index(readjl(HERE/'application-readback.jsonl'))
assert set(current)==set(primary)==set(blind)==set(cross) and len(cross)==240
assert len(plan)==144 and len(readback)==240 and set(readback)==set(current)

base_bytes=git_bytes('show',f'{BASE}:{CATALOG}')
base_catalog=json.loads(base_bytes.decode('utf-8'))
actual_catalog=readj(REPO/CATALOG)
expected=json.loads(base_bytes.decode('utf-8'))
for key,row in cross.items():
    c=current[key]; p=primary[key]; b=blind[key]
    assert row['sourceId']==c['sourceId']==p['sourceId']==b['sourceId']
    assert row['sourceSha256']==c['sourceSha256']==p['sourceSha256']==b['sourceSha256']
    assert row['currentTarget']==c['currentTarget']==p['currentTarget']==b['currentTarget']
    assert row['callerContextSha256']==c['callerContextSha256']==p['callerContextSha256']==b['callerContextSha256']
    assert row['primaryTarget']==p['selectedTarget'] and row['blindTarget']==b['blindTarget']
    sid=row['sourceId']; loc=row['locale']; entry=base_catalog['messages'][sid]
    assert entry['source']==row['source'] and entry['sourceHash']==row['sourceSha256']
    before=entry['translations'][loc]
    assert before==row['currentTarget'] and rawsha(before)==row['currentTargetSha256']
    assert entry['translationHashes'][loc]==catalog_hash(before)==c['catalogTranslationHash']
    assert entry['translationStatus'][loc]=='draft'
    target=row['selectedTarget']; assert rawsha(target)==row['selectedTargetSha256']
    if target!=before:
        assert key in plan
        pr=plan[key]
        assert pr['target']==target and pr['targetSha256']==row['selectedTargetSha256']
        assert pr['currentTarget']==before and pr['crossAuditDisposition']==row['crossAuditDisposition']
        assert pr['translationHashBefore']==catalog_hash(before) and pr['translationHashAfter']==catalog_hash(target)
        expected['messages'][sid]['translations'][loc]=target
        expected['messages'][sid]['translationHashes'][loc]=catalog_hash(target)
    else:
        assert key not in plan and row['crossAuditDisposition']=='accept-current'
    rb=readback[key]
    after=expected['messages'][sid]['translations'][loc]
    assert rb['sourceId']==sid and rb['source']==row['source'] and rb['sourceSha256']==row['sourceSha256']
    assert rb['currentTarget']==before and rb['target']==after and rb['targetSha256']==rawsha(after)
    assert rb['translationHashBefore']==entry['translationHashes'][loc]
    assert rb['translationHashAfter']==expected['messages'][sid]['translationHashes'][loc]
    assert rb['translationStatusBefore']==rb['translationStatusAfter']=='draft'
    assert rb['disposition']==('update' if after!=before else 'retain')
    assert rb['crossAuditDisposition']==row['crossAuditDisposition']
assert actual_catalog==expected,'catalog has a missing, extra, or non-target translation/hash/metadata change'
assert list(actual_catalog)==list(base_catalog) and list(actual_catalog['messages'])==list(base_catalog['messages'])
for sid,before in base_catalog['messages'].items():
    after=actual_catalog['messages'][sid]
    assert list(after)==list(before),f'message field order changed: {sid}'
    assert list(after['translations'])==list(before['translations']),f'locale order changed: {sid}'
    assert list(after['translationHashes'])==list(before['translationHashes']),f'hash locale order changed: {sid}'
    for field in ('translationStatus','translationReview','translationPending','source','sourceHash','sourceKind'):
        assert after.get(field)==before.get(field),f'{field} changed: {sid}'

# Confirm no previous callerless hold changed in value or canonical hash.
prior=readjl(INPUT/'prior-hold-reattestation.jsonl')
assert len(prior)==288
for row in prior:
    sid=row['sourceId']; loc=row['locale']
    old=base_catalog['messages'][sid]['translations'][loc]
    new=actual_catalog['messages'][sid]['translations'][loc]
    assert rawsha(old)==row['currentTargetSha256']==row['priorCurrentTargetSha256'] and old==new
    assert base_catalog['messages'][sid]['translationHashes'][loc]==actual_catalog['messages'][sid]['translationHashes'][loc]==catalog_hash(old)

assert len(plan)==sum(x['selectedTarget']!=x['currentTarget'] for x in cross.values())==144
assert collections.Counter(x['crossAuditDisposition'] for x in plan.values())=={'correction':93,'refinement':51}
assert sum(x['crossAuditDisposition']=='accept-current' for x in cross.values())==96
assert sum(x['disposition']=='update' for x in readback.values())==144
assert not any(x['crossAuditDisposition']=='hold' for x in cross.values())
assert all(x['runtimeDispatchGap'] and x['runtimeDispatchFollowup']['required'] for k,x in cross.items() if k[0] in (346,350))
assert sum(x['runtimeDispatchGap'] for x in cross.values())==24

summary=readj(HERE/'application-summary.json')
assert summary['parentHead']==BASE and summary['parentTree']==BASE_TREE
assert summary['catalogBeforeSha256']==sha(base_bytes) and summary['catalogAfterSha256']==sha((REPO/CATALOG).read_bytes())
assert summary['selectedUpdates']==144 and summary['updatedTranslationHashes']==144 and summary['nonTargetTranslationChanges']==0 and summary['nonTargetHashChanges']==0
assert summary['exactReadbackCells']==240 and summary['readbackMismatches']==0 and summary['priorCallerlessHoldCellsReattested']==288
assert summary['translationDispatchFollowups'][0]['position']==346 and summary['translationDispatchFollowups'][1]['position']==350
# If committed, restrict the diff to catalog and this evidence folder; workflows and runtime callers stay untouched.
if head!=BASE:
    names=git('diff','--name-only',f'{BASE}..{head}').splitlines()
    assert CATALOG in names and all(x==CATALOG or x.startswith('docs/pr-evidence/pr70-localization-2026-11-03/window-345-364/') for x in names),names
    assert not git('diff','--name-only',f'{BASE}..{head}','--','.github/workflows','romarr/ui.py','romarr/app.py','romarr/organizer.py')
    subprocess.check_call(['git','diff',f'{BASE}..{head}','--check'],cwd=REPO)

print(json.dumps({'verification':'passed','localHead':head,'livePRHead':live['head'],'liveBranchHead':branch['object']['sha'],'window':'W345-W364',
  'readbackCells':240,'updates':144,'retained':96,'priorCallerlessHoldsUnchanged':288,'nonTargetChanges':0,
  'catalogStructureAndOrder':'unchanged','translationHashes':'canonical JSON scalar hashes match all targets',
  'candidateFree':input_summary,'primary':primary_summary,'blind':'checksum list verified','crossAudit':cross_summary_text,
  'dispatchFollowups':[346,350],'testsBuildsScansCI':False,'workflowFilesChanged':False},ensure_ascii=False,indent=2))
