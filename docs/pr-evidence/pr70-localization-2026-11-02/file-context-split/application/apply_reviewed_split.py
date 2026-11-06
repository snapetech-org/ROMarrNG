#!/usr/bin/env python3
"""Apply the exact-hash reviewed ROMarr File noun/action split only."""
import hashlib, json, re, subprocess, unicodedata
from pathlib import Path
ROOT=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-romarrng')
PRIMARY=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-file-context-split-primary-20261102')
CROSS=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-file-context-split-crossreview-20261102')
OUT=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-file-context-split-application-20261102')
HEAD='9b56b5fde40daf59aa61a7ce2d14e6bf7b37bf9d'; TREE='117fb2a8cc208c958ac62d00927cc65defe6530d'
FILE_ID='ui.file.50009ce1da'; ACTION_SOURCE='Add to library'; ACTION_ID='ui.add-to-library.2bf9ea0e46'
UI=ROOT/'romarr/ui.py'; CATALOG=ROOT/'romarr/ui-labels.json'; SNAPSHOT=ROOT/'romarr/ui-source-snapshot.json'
OLD="'<b>Acquire</b> → <b>Verify</b> → <b>File</b> → <b>Scan</b> → <b>Play</b><br>'"
NEW="'<b>Acquire</b> → <b>Verify</b> → <b>'+interfaceMarkup('ui.add-to-library.2bf9ea0e46')+'</b> → <b>Scan</b> → <b>Play</b><br>'"
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode('utf-8')).hexdigest()
def thash(x): return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')))
def run(*args): return subprocess.check_output(args,cwd=ROOT).decode().strip()
def stable_id(s):
 slug=re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip('-')[:36].rstrip('-')
 return f'ui.{slug or "message"}.{sha(s)[:10]}'
OUT.mkdir(parents=True,exist_ok=True)
assert stable_id(ACTION_SOURCE)==ACTION_ID
assert (run('git','rev-parse','HEAD'),run('git','rev-parse','HEAD^{tree}'))==(HEAD,TREE)
assert run('git','status','--porcelain')==''
primary=json.loads((PRIMARY/'primary-review.json').read_text()); cross=json.loads((CROSS/'cross-review.json').read_text())
input_bytes=(PRIMARY/'file-context-review-input.json').read_bytes()
assert sha(input_bytes)==cross['pins']['inputPacketSha256']=='d08b3af50c143fe3e0e997a3c240936df7de30fe86d9e03c23936fe6b968c768'
assert (CROSS/'SHA256SUMS').is_file()
assert cross['inputHead']==HEAD and cross['inputTree']==TREE and cross['dispositions']['holds']==0
assert cross['dispositions']['fileNounsAccepted']==12 and cross['dispositions']['actionTargetsAccepted']==11 and cross['dispositions']['primaryArabicRefinementAccepted']==1
ui_before=UI.read_bytes(); catalog_before=CATALOG.read_bytes(); snapshot_before=SNAPSHOT.read_bytes()
assert sha(ui_before)==cross['pins']['uiSourceFileSha256']=='b110af999efbe7bf22e8a1ee98be8cf6b4dee92f8f3b3fff606b59e38f9f527e'
assert sha(catalog_before)==cross['pins']['catalogFileSha256']=='9c7a40251e51dc9904a3825e6bebc551d9db5313aa98bde62ffdeac32ffd7cd0'
assert run('git','rev-parse',f'{HEAD}:romarr/ui.py')==cross['pins']['uiSourceGitBlob']
assert run('git','rev-parse',f'{HEAD}:romarr/ui-labels.json')==cross['pins']['catalogGitBlob']
assert ui_before.decode().count(OLD)==1
cat=json.loads(catalog_before); snap=json.loads(snapshot_before); msgs=cat['messages']; file=msgs[FILE_ID]
assert file['source']=='File' and file['sourceHash']==sha('File') and file['translationReview']=={}
assert list(snap)==list(msgs) and snap[FILE_ID]==sha('File')
assert ACTION_ID not in msgs and ACTION_ID not in snap and not any(m.get('source')==ACTION_SOURCE for m in msgs.values())
nouns={r['locale']:r['target'] for r in primary['fileNounTargets']}; actions={r['locale']:r['target'] for r in primary['addToLibraryTargets']}
assert set(nouns)==set(actions)==set(LOCALES)
plan={'repository':'snapetech-org/ROMarrNG','pullRequest':70,'inputHead':HEAD,'inputTree':TREE,'inputCatalogSha256':sha(catalog_before),'inputSnapshotSha256':sha(snapshot_before),'inputUiSha256':sha(ui_before),'operations':[],'sourceEdit':{'path':'romarr/ui.py','oldLiteral':OLD,'newLiteral':NEW,'occurrences':1}}
for locale in LOCALES:
 old=file['translations'][locale]; noun=nouns[locale]; action=actions[locale]
 assert thash(noun)==next(r for r in primary['fileNounTargets'] if r['locale']==locale)['catalogTargetSha256']
 assert thash(action)==next(r for r in primary['addToLibraryTargets'] if r['locale']==locale)['catalogTargetSha256']
 plan['operations'].append({'messageId':FILE_ID,'source':'File','locale':locale,'expectedOld':old,'expectedOldRawSha256':sha(old),'target':noun,'targetRawSha256':sha(noun),'targetCatalogSha256':thash(noun),'disposition':'accepted-by-primary-and-independent-cross-review'})
 plan['operations'].append({'messageId':ACTION_ID,'source':ACTION_SOURCE,'locale':locale,'expectedOld':'<absent>','expectedOldRawSha256':None,'target':action,'targetRawSha256':sha(action),'targetCatalogSha256':thash(action),'disposition':'accepted-by-primary-and-independent-cross-review'})
(OUT/'exact-hash-apply-plan.json').write_text(json.dumps(plan,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
# Mutate only the reviewed catalog cells and the source message/caller.
for locale,target in nouns.items(): file['translations'][locale]=target
file['translationStatus']={locale:'draft' for locale in LOCALES}
file['translationHashes']={locale:thash(file['translations'][locale]) for locale in LOCALES}
file['translationReview']={}
new_entry={'source':ACTION_SOURCE,'sourceHash':sha(ACTION_SOURCE),'translations':actions,'translationHashes':{locale:thash(actions[locale]) for locale in LOCALES},'translationStatus':{locale:'draft' for locale in LOCALES},'translationReview':{}}
ordered={}
inserted=False
for key,value in msgs.items():
 if key=='ui.add-to-wanted.4020704bf3':
  ordered[ACTION_ID]=new_entry; inserted=True
 ordered[key]=value
if not inserted: raise RuntimeError('catalog insertion anchor missing')
cat['messages']=ordered
new_ui=ui_before.decode().replace(OLD,NEW,1)
UI.write_text(new_ui,encoding='utf-8')
CATALOG.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Add the generated source hash in the source snapshot at the same nearby catalog position.
new_snap={}
for key,value in snap.items():
 if key=='ui.add-to-wanted.4020704bf3': new_snap[ACTION_ID]=sha(ACTION_SOURCE)
 new_snap[key]=value
SNAPSHOT.write_text(json.dumps(new_snap,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Exact readback of 24 target cells and generated source metadata.
cat2=json.loads(CATALOG.read_text()); snap2=json.loads(SNAPSHOT.read_text()); ui_after=UI.read_bytes()
assert list(cat2['messages'])==list(snap2)
assert snap2[ACTION_ID]==sha(ACTION_SOURCE) and snap2[FILE_ID]==sha('File')
assert NEW in ui_after.decode() and OLD not in ui_after.decode()
readback=[]
for locale in LOCALES:
 for mid,expected in ((FILE_ID,nouns[locale]),(ACTION_ID,actions[locale])):
  e=cat2['messages'][mid]; actual=e['translations'][locale]
  assert actual==expected and e['translationStatus'][locale]=='draft' and e['translationReview']=={}
  assert e['translationHashes'][locale]==thash(expected)
  readback.append({'messageId':mid,'source':e['source'],'locale':locale,'target':actual,'targetRawSha256':sha(actual),'targetCatalogSha256':thash(actual),'translationStatus':'draft','translationReview':{}})
(OUT/'application-readback.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in readback))
summary={'inputHead':HEAD,'inputTree':TREE,'outputTree':None,'changedLocaleCells':24,'changedSourceMessages':1,'newCatalogMessageId':ACTION_ID,'sourceSnapshotEntryAdded':True,'catalogMessageCount':len(cat2['messages']),'existingCatalogMessageCountBefore':1836,'translationStatus':'draft','nativeSpeakerReviewRecorded':False,'projectMigrationGeneratorRun':True,'migrationGeneratorDisposition':'A generator inspection emitted 141 unrelated pending source-manifest rows; those outputs were restored, then the reviewed catalog and snapshot changes were applied directly with the project stable-ID/hash conventions.','outputs':{'uiSourceSha256':sha(ui_after),'catalogSha256':sha(CATALOG.read_bytes()),'snapshotSha256':sha(SNAPSHOT.read_bytes())}}
(OUT/'application-summary.json').write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
