#!/usr/bin/env python3
from pathlib import Path
import collections,hashlib,json,subprocess
E=Path(__file__).resolve().parent
REPO=E.parents[3]
BASE='d1698b94781c3c84e91faf03c75e8c308dc39c34'
TREE='3f42d41fe4bbb8edd921ff161e8298ca66038a91'
BRANCH='task/localization-translation-review-20261030'
def run(args,cwd=None): return subprocess.check_output(args,cwd=cwd or REPO,text=True).strip()
def sha(b): return hashlib.sha256(b).hexdigest()
def translation_hash(v):
 return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
assert run(['git','rev-parse','HEAD'])==BASE and run(['git','rev-parse','HEAD^{tree}'])==TREE
pr=json.loads(run(['gh','api','repos/snapetech-org/romarrng/pulls/70']))
assert (pr['state'],pr['draft'],pr['head']['sha'],pr['head']['ref'],pr['base']['ref'])==('open',True,BASE,BRANCH,'main')
refs=run(['git','ls-remote','https://github.com/snapetech-org/romarrng.git',f'refs/heads/{BRANCH}','refs/pull/70/head'])
refmap={x.split()[1]:x.split()[0] for x in refs.splitlines()}
assert refmap=={f'refs/heads/{BRANCH}':BASE,'refs/pull/70/head':BASE}
status=run(['git','status','--porcelain','--untracked-files=all']).splitlines()
status_paths=[x[2:].strip() for x in status]
assert all(p.startswith('docs/pr-evidence/pr70-localization-2026-11-03/') for p in status_paths),status
plan=json.loads((E/'apply-plan.json').read_text())
assert plan['baseHead']==BASE and plan['baseTree']==TREE
assert plan['changedCells']==115 and len(plan['updates'])==115
catalog=REPO/'romarr/ui-labels.json'
raw=subprocess.check_output(['git','show',f'{BASE}:romarr/ui-labels.json'],cwd=REPO)
assert sha(raw)==plan['catalogFileSha256']
baseline=json.loads(raw.decode('utf-8'))
assert raw.decode('utf-8')==json.dumps(baseline,ensure_ascii=False,indent=2)+'\n'
current=json.loads(catalog.read_text(encoding='utf-8'))
assert current==baseline
expected=json.loads(raw.decode('utf-8'))
allrows=plan['allCellReadbackPlan']
assert len(allrows)==240
for row in allrows:
 sid=row['sourceId'];loc=row['locale'];entry=expected['messages'][sid]
 assert entry['translations'][loc]==row['currentTarget']
 assert sha(entry['translations'][loc].encode())==row['currentTargetSha256']
 assert translation_hash(entry['translations'][loc])==row['catalogTranslationHash']
 assert entry['translationStatus'][loc]==row['translationStatus']
 if row['changed']:
  entry['translations'][loc]=row['selectedTarget']
  entry['translationHashes'][loc]=translation_hash(row['selectedTarget'])
  assert entry['translationHashes'][loc]==translation_hash(row['selectedTarget'])
for row in allrows:
 entry=expected['messages'][row['sourceId']]
 assert entry['translations'][row['locale']]==row['selectedTarget']
 assert entry['translationHashes'][row['locale']]==translation_hash(row['selectedTarget'])
prior=[json.loads(x) for x in (E/'candidate-free-input/prior-hold-reattestation.jsonl').read_text().splitlines() if x]
assert len(prior)==288
for h in prior:
 value=expected['messages'][h['sourceId']]['translations'][h['locale']]
 assert sha(value.encode())==h['currentTargetSha256']==h['priorCurrentTargetSha256']
assert expected.keys()==baseline.keys() and list(expected)==list(baseline)
assert expected['messages'].keys()==baseline['messages'].keys()
for sid,before in baseline['messages'].items():
 after=expected['messages'][sid]
 if sid not in {x['sourceId'] for x in allrows}:
  assert after==before
 for field in before:
  if field=='translations':
   for loc,v in before[field].items():
    changed=next((x for x in allrows if x['sourceId']==sid and x['locale']==loc and x['changed']),None)
    assert after[field][loc]==(changed['selectedTarget'] if changed else v)
  elif field=='translationHashes':
   for loc,v in before[field].items():
    changed=next((x for x in allrows if x['sourceId']==sid and x['locale']==loc and x['changed']),None)
    assert after[field][loc]==(translation_hash(changed['selectedTarget']) if changed else v)
  else:
   assert after[field]==before[field],(sid,field,'non-target metadata changed')
catalog.write_text(json.dumps(expected,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
result={'schemaVersion':1,'status':'applied-uncommitted','repository':'snapetech-org/romarrng','pullRequest':70,'branch':BRANCH,'reviewedBaseHead':BASE,'reviewedBaseTree':TREE,'cells':240,'decisions':plan['decisionCounts'],'crossAuditResolutions':plan['crossAuditResolutionCounts'],'changedCells':115,'updatedCatalogFiles':1,'catalogFileSha256':sha(catalog.read_bytes()),'nonTargetChanges':0,'translationHashMetadataUpdated':115,'catalogKeyOrderPreserved':True,'priorHoldsPreserved':288,'newHolds':0,'rank368CellsReviewed':12,'workflowFilesTouched':False,'testsBuildsScansCi':'not run'}
(E/'application-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pass':True,'cells':240,'updates':115,'priorHoldsPreserved':288,'nonTargetChanges':0,'file':'romarr/ui-labels.json'},indent=2))
