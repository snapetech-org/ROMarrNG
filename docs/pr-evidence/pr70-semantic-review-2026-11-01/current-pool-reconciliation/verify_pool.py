#!/usr/bin/env python3
"""Read-only exact-target-hash reconciliation for ROMarrNG PR #70."""
import collections, hashlib, json, subprocess
from pathlib import Path

ROOT=Path('/mnt/disks/scratch/task-worktrees/localization-20261030')
WT=ROOT/'romarrng-pr70-head-review-20261101'
OLD=ROOT/'romarrng-semantic-review-08689f3e'
NEW=ROOT/'romarrng-semantic-review-79b144e3-20261101'
FOLLOW=ROOT/'romarrng-held-followup-54f1-artifacts-20261101'
PHRASE=ROOT/'romarrng-semantic-next-window-a1278acd-20261101'
HEAD='a1278acda1cea823443d7d6b712ed6ace8a99694'
TREE='1e8a8d4fb191490a20bc443fb2b7bf24f05fa294'
EXPECTED={
 'romarr/ui-labels.json':'639d2449119ea25c1f76ccd09b05bffbb87da0373dac8bbe9dcee9547ef499a2',
 'romarr/ui-source-messages.json':'ba11bdfa7f8a282dea83d7367e1156ce716ad79aabafbdd72b7e887df647bec5',
 'romarr/ui.py':'028e05f27f1fad6137494c85b1fa8847512a2d11db37c9fa44c4b611a2e797ad',
}
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def sha(data): return hashlib.sha256(data).hexdigest()
def sha_file(path): return sha(Path(path).read_bytes())
def canonical_sha(value):
 return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))
def value_hashes(value):
 out={canonical_sha(value)}
 if isinstance(value,str): out.add(sha(value.encode('utf-8')))
 return out
def read_jsonl(path):
 return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line]

git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip()
git_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=WT,text=True).strip()
if (git_head,git_tree)!=(HEAD,TREE): raise SystemExit(f'head/tree changed: {git_head} {git_tree}')
tracked_status=subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=no'],cwd=WT,text=True).strip()
if tracked_status: raise SystemExit(f'tracked worktree changes present: {tracked_status}')
untracked=[line[3:] for line in subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=WT,text=True).splitlines() if line.startswith('?? ')]
file_hashes={rel:sha_file(WT/rel) for rel in EXPECTED}
if file_hashes!=EXPECTED: raise SystemExit(f'frozen file hash mismatch: {file_hashes}')
cat=json.loads((WT/'romarr/ui-labels.json').read_text(encoding='utf-8'))
current={}
for sid,entry in cat['messages'].items():
 for locale in LOCALES:
  value=entry.get('translations',{}).get(locale)
  if value is not None: current[f'{locale}:{sid}']=value
if len(cat['messages'])!=1833 or len(current)!=21996: raise SystemExit('unexpected catalog dimensions')

# Exact old populated-cell review, plus the recorded exact suggested replacement hashes.
old_review=read_jsonl(OLD/'reviewed-cells.jsonl')
old_by_cell={row['cellId']:row for row in old_review}
old_corrections=collections.defaultdict(set)
for row in read_jsonl(OLD/'findings.jsonl'):
 old_corrections[row['cellId']].add(canonical_sha(row['suggestedTarget']))
for row in read_jsonl(OLD/'moderate-uncertain-adjudication.jsonl'):
 if row.get('recommendedWording') is not None:
  old_corrections[row['cellId']].add(canonical_sha(row['recommendedWording']))

# New populated translations: exact reviewed draft (accepted) or exact proposed target.
new_by_cell=collections.defaultdict(list)
new_rows=read_jsonl(NEW/'romarr-missing-cell-review-5808-2026-11-01.jsonl')
for row in new_rows: new_by_cell[f"{row['locale']}:{row['id']}"].append(row)

# Later 54f1 exact suggestions: all 21 held-cell corrections were applied per final summary;
# 17/24 companion suggestions were applied and 7 retained current wording.
held_rows=read_jsonl(FOLLOW/'held-correction-review-54f1.jsonl')
companion_rows=read_jsonl(FOLLOW/'companion-adjudication-54f1.jsonl')
summary=json.loads((FOLLOW/'final-application-summary-54f1.json').read_text(encoding='utf-8'))
if len(held_rows)!=21 or summary['heldCorrectionsApplied']!=21: raise SystemExit('held-cell application count mismatch')
applied_companions=[row for row in companion_rows if row.get('applied')]
if len(companion_rows)!=24 or len(applied_companions)!=17 or summary['companionApplied']!=17: raise SystemExit('companion application count mismatch')
followup=collections.defaultdict(set)
for row in held_rows: followup[f"{row['locale']}:{row['id']}"].add(row['suggestionSha256'])
for row in applied_companions: followup[f"{row['locale']}:{row['id']}"].add(row['suggestionSha256'])

# Current-head 12-locale window for the adjacent numeric-control phrase.
phrase_rows=read_jsonl(PHRASE/'review-decisions.jsonl')
phrase_hash={f"{row['locale']}:{row['sourceId']}":row['currentTargetRawUtf8Sha256'] for row in phrase_rows}
if len(phrase_rows)!=12: raise SystemExit('unexpected current-head phrase batch size')

counts=collections.Counter(); assigned={}; unmatched=[]
for cell_id,value in current.items():
 hashes=value_hashes(value); group=None
 if cell_id in old_by_cell and old_by_cell[cell_id]['targetSha256'] in hashes:
  group='baseline-current-target'
 elif hashes & old_corrections.get(cell_id,set()):
  group='baseline-correction-target'
 elif any(row['currentDraftSha256'] in hashes for row in new_by_cell.get(cell_id,[])):
  group='new-cells-accepted-unchanged'
 elif any(row['targetSha256'] in hashes for row in new_by_cell.get(cell_id,[])):
  group='new-cells-correction-target'
 elif hashes & followup.get(cell_id,set()):
  group='54f1-followup-correction-target'
 elif cell_id in phrase_hash and phrase_hash[cell_id] in hashes:
  group='a127-current-head-window'
 if group is None: unmatched.append(cell_id)
 else: counts[group]+=1; assigned[cell_id]=group
if unmatched: raise SystemExit('unaccounted current direct-locale cells: '+','.join(unmatched))
expected_counts={
 'baseline-current-target':15876,
 'baseline-correction-target':300,
 'new-cells-accepted-unchanged':2462,
 'new-cells-correction-target':3308,
 '54f1-followup-correction-target':38,
 'a127-current-head-window':12,
}
if dict(counts)!=expected_counts: raise SystemExit(f'coverage counts changed: {dict(counts)}')
if sum(counts.values())!=len(current): raise SystemExit('partition did not cover the complete direct-locale catalog')

# Upstream evidence checksums make this inventory auditable without changing those artifacts.
inputs={}
for path in [OLD/'manifest.json',OLD/'reviewed-cells.jsonl',OLD/'findings.jsonl',OLD/'moderate-uncertain-adjudication.jsonl',
 NEW/'romarr-missing-cell-review-5808-2026-11-01.jsonl',NEW/'romarr-missing-cell-review-summary-2026-11-01.json',
 FOLLOW/'held-correction-review-54f1.jsonl',FOLLOW/'companion-adjudication-54f1.jsonl',FOLLOW/'final-application-summary-54f1.json',
 PHRASE/'manifest.json',PHRASE/'review-decisions.jsonl']:
 inputs[str(path)]=sha_file(path)
result={
 'artifact':'ROMarrNG PR #70 exact-current-hash populated-catalog disposition reconciliation',
 'result':'no eligible new disjoint semantic window at this frozen head',
 'livePrPreflight':{'state':'OPEN','isDraft':True,'head':HEAD,'tree':TREE,'branch':'task/localization-translation-review-20261030'},
 'worktree':{'path':str(WT),'head':git_head,'tree':git_tree,'trackedFilesClean':True,'untrackedPathsAtAudit':untracked,'frozenFileSha256':file_hashes},
 'scope':{'catalogMessages':len(cat['messages']),'directLocales':LOCALES,'directLocaleCells':len(current),'cellsPerLocale':{loc:sum(cid.startswith(loc+':') for cid in current) for loc in LOCALES}},
 'exactCurrentHashPartition':dict(counts),
 'partitionTotal':sum(counts.values()),
 'eligibleUnaccountedCells':0,
 'eligibleSourceKeys':0,
 'unmatchedDirectCellIds':[],
 'evidenceInputSha256':inputs,
 'reviewLimits':{'newReviewDecisionsCreated':0,'catalogOrSourceEdits':False,'prBodyOrBranchEdits':False,'testsBuildsCi':False,'modelCalls':0,'sharedQwenLockAcquired':False,'browserRenderedReviewPerformed':False,'nativeSpeakerReview':'not performed; native validation remains required for the full catalog'},
 'sharedWorktreeNote':'Only tracked inputs are required for this frozen hash audit. The shared review worktree currently contains untracked docs/pr-evidence files from another agent; this task created no files there.',
 'nextAction':'No next disjoint populated-catalog source key exists at this head under the exact-hash exclusion rule. Recompute the pool after any catalog/head change; otherwise a new pass would overlap existing exact-hash dispositions.',
}
print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
