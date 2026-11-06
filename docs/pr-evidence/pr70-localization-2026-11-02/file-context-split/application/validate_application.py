#!/usr/bin/env python3
"""Read-only exact-hash/readback validation for the ROMarr File split."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
EVIDENCE=ROOT/'docs/pr-evidence/pr70-localization-2026-11-02/file-context-split'
PRIMARY=EVIDENCE/'primary/primary-review.json'
CROSS=EVIDENCE/'cross-review/cross-review.json'
PLAN=EVIDENCE/'application/exact-hash-apply-plan.json'
READBACK=EVIDENCE/'application/application-readback.jsonl'
BASE='9b56b5fde40daf59aa61a7ce2d14e6bf7b37bf9d'
FILE_ID='ui.file.50009ce1da'; ACTION_ID='ui.add-to-library.2bf9ea0e46'
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def thash(x): return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')))
def show(path): return subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=ROOT)
primary=json.loads(PRIMARY.read_text()); cross=json.loads(CROSS.read_text()); plan=json.loads(PLAN.read_text())
base_cat=json.loads(show('romarr/ui-labels.json')); cur_cat=json.loads((ROOT/'romarr/ui-labels.json').read_text())
base_snap=json.loads(show('romarr/ui-source-snapshot.json')); cur_snap=json.loads((ROOT/'romarr/ui-source-snapshot.json').read_text())
base_ui=show('romarr/ui.py').decode(); cur_ui=(ROOT/'romarr/ui.py').read_text()
assert set(cur_cat['messages'])==set(base_cat['messages'])|{ACTION_ID}
assert len(base_cat['messages'])==1836 and len(cur_cat['messages'])==1837
assert list(cur_cat['messages'])==list(cur_snap)
assert set(cur_snap)==set(base_snap)|{ACTION_ID}
for key,value in base_cat.items():
 if key!='messages': assert cur_cat[key]==value, f'catalog metadata changed: {key}'
for mid,entry in base_cat['messages'].items():
 if mid==FILE_ID: continue
 assert cur_cat['messages'][mid]==entry, f'unrelated message changed: {mid}'
file_before=base_cat['messages'][FILE_ID]; file_after=cur_cat['messages'][FILE_ID]
assert file_after['source']==file_before['source']=='File'
assert file_after['sourceHash']==file_before['sourceHash']
assert set(file_after['translations'])==set(file_before['translations'])==set(LOCALES)
expected_nouns={x['locale']:x['target'] for x in primary['fileNounTargets']}
expected_actions={x['locale']:x['target'] for x in primary['addToLibraryTargets']}
for locale in LOCALES:
 assert file_after['translations'][locale]==expected_nouns[locale]
 assert file_after['translationStatus'][locale]=='draft'
 assert file_after['translationHashes'][locale]==thash(expected_nouns[locale])
 assert file_after['translationReview']=={}
entry=cur_cat['messages'][ACTION_ID]
assert entry['source']=='Add to library' and entry['sourceHash']==sha('Add to library')
assert entry['translations']==expected_actions
assert set(entry['translations'])==set(entry['translationHashes'])==set(entry['translationStatus'])==set(LOCALES)
assert all(entry['translationStatus'][l]=='draft' for l in LOCALES) and entry['translationReview']=={}
for l in LOCALES: assert entry['translationHashes'][l]==thash(expected_actions[l])
assert all(cur_snap[k]==v for k,v in base_snap.items())
assert cur_snap[ACTION_ID]==sha('Add to library')
old="'<b>Acquire</b> → <b>Verify</b> → <b>File</b> → <b>Scan</b> → <b>Play</b><br>'"
new="'<b>Acquire</b> → <b>Verify</b> → <b>'+interfaceMarkup('ui.add-to-library.2bf9ea0e46')+'</b> → <b>Scan</b> → <b>Play</b><br>'"
assert base_ui.count(old)==1 and cur_ui==base_ui.replace(old,new,1)
read=[json.loads(x) for x in READBACK.read_text().splitlines() if x]
assert len(read)==24
for x in read:
 e=cur_cat['messages'][x['messageId']]
 assert e['translations'][x['locale']]==x['target']
 assert x['targetRawSha256']==sha(x['target']) and x['targetCatalogSha256']==thash(x['target'])
assert len(plan['operations'])==24
report={'baselineHead':BASE,'catalogKeysBefore':1836,'catalogKeysAfter':1837,'newMessageId':ACTION_ID,'readbackCells':len(read),'fileNounTargets':12,'actionTargets':12,'exactUnrelatedCatalogEntriesPreserved':True,'sourceSnapshotPreservesAllOldEntries':True,'sourcePipelineReplacementExact':True,'draftStatusesPreserved':True,'nativeReviewEntriesCreated':False,'evidencePlanOperations':len(plan['operations']),'workflowsChanged':False,'testsBuildsCiRun':False,'validationKind':'read-only exact-hash, JSON, source-snapshot, caller, and unchanged-entry verification'}
(EVIDENCE/'application/application-validation.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
