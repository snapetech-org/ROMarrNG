from pathlib import Path
import hashlib, json

ROOT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w645-664-20261105')
REPO=Path('/mnt/disks/scratch/task-worktrees/localization-20261105/romarrng-pr70-w645-664-pinned')
OUT=ROOT/'application'
CF=ROOT/'candidate-free/candidate-free/input'
LEDGER=ROOT/'root-adjudication/root-disposition-ledger.jsonl'
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path): return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(b): return hashlib.sha256(b).hexdigest()
def sth(s): return sha(s.encode('utf-8'))
def translation_hash(value): return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))

head='9f8832f67195323955172dd4c3c40e29cbabb5da'
tree='d6066baa3d03d3b4c6034e5af061fc4bc278b0f9'
if __import__('subprocess').check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()!=head: raise SystemExit('worktree HEAD mismatch')
if __import__('subprocess').check_output(['git','-C',str(REPO),'rev-parse','HEAD^{tree}'],text=True).strip()!=tree: raise SystemExit('worktree tree mismatch')
if __import__('subprocess').check_output(['git','-C',str(REPO),'status','--porcelain=v1'],text=True).strip(): raise SystemExit('worktree is not clean')
raw=(REPO/'romarr/ui-labels.json').read_bytes(); catalog=load(REPO/'romarr/ui-labels.json')
message_keys=list(catalog['messages'])
message_key_order_sha=sha((json.dumps(message_keys,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode())
cf_cells={(x['position'],x['locale']):x for x in rows(CF/'current-target-cells.jsonl')}
ledger=rows(LEDGER)
changes=[];hash_updates=[]
for item in ledger:
    if item['rootDisposition'] not in ('correction','refinement'): continue
    cell=cf_cells[(item['position'],item['locale'])]
    message=catalog['messages'][item['sourceId']]
    locale=item['locale']; current=message['translations'][locale]
    if current!=cell['currentTarget'] or sth(current)!=item['currentTargetSha256']: raise SystemExit(f'current target drift at {item["position"]}/{locale}')
    final=item['rootTarget']
    change={'position':item['position'],'locale':locale,'sourceId':item['sourceId'],
      'path':'romarr/ui-labels.json','sourceText':cell['source'],'sourceSha256':item['sourceSha256'],
      'callerContextSha256':item['callerContextSha256'],'currentTarget':current,
      'currentTargetSha256':item['currentTargetSha256'],'finalTarget':final,
      'finalTargetSha256':item['rootTargetSha256'],'rootDisposition':item['rootDisposition'],
      'rootRationale':item['rootRationale'],'storedTranslationStatus':message.get('translationStatus',{}).get(locale),
      'storedTranslationHash':message.get('translationHashes',{}).get(locale)}
    changes.append(change)
    if locale in message.get('translationStatus',{}):
        if message['translationStatus'][locale]!='draft': raise SystemExit(f'unexpected non-draft status at {item["position"]}/{locale}')
        if message['translationHashes'].get(locale)!=translation_hash(current): raise SystemExit(f'current translationHash mismatch at {item["position"]}/{locale}')
        hash_updates.append({'position':item['position'],'locale':locale,'sourceId':item['sourceId'],
          'expectedOldHash':message['translationHashes'][locale],'newHash':translation_hash(final),'status':'draft'})
if len(changes)!=15 or len(hash_updates)!=10: raise SystemExit('unexpected change or translationHash count')
file_pins=load(CF/'catalog-file-pins.json')
plan={'artifact':'ROMarrNG PR #70 W645-W664 exact-hash application plan',
  'repository':'snapetech-org/ROMarrNG','pullRequest':70,
  'branch':'task/localization-translation-review-20261030',
  'sourcePin':{'head':head,'tree':tree},'window':'W645-W664',
  'candidateCells':240,'rootDispositionCounts':load(ROOT/'root-adjudication/summary.json')['rootDispositionCounts'],
  'callerlessHolds':96,'nativeSpeakerApproval':False,'browserReviewAtThisHead':False,
  'workflowChanges':False,'catalogs':[{'path':'romarr/ui-labels.json','preimageSha256':sha(raw),
    'messageCount':len(catalog['messages']),'candidateFreeCatalogKeyOrderSha256':file_pins['catalogKeyOrderSha256'],
    'applicationMessageKeyOrderSha256':message_key_order_sha}],
  'changes':changes,'translationHashUpdates':hash_updates,
  'translationStatusChanges':0,'translationReviewMetadataChanges':0}
(OUT/'root-application-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'plan':str(OUT/'root-application-plan.json'),'selectedCells':len(changes),
  'translationHashUpdates':len(hash_updates),'preimageSha256':sha(raw),'messageKeyOrderSha256':message_key_order_sha},ensure_ascii=False,indent=2))
