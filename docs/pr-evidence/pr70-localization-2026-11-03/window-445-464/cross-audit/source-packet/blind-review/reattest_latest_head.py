#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys,collections
OUT=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w445-464-blind-20261103')
IN=OUT/'input/candidate-free-input'
REPO='snapetech-org/ROMarrNG'; HEAD='81a499b7c022bde61a63dbd8c68c0b1ca39adf26'; TREE='1b075e050610771fc5651d1a4ca95d7c7b4b8e46'; PARENT='d5ba7f1f268501f45227388c46d5f938ed0c9191'; BRANCH='task/localization-translation-review-20261030'
def sha(b): return hashlib.sha256(b).hexdigest()
def st(s): return sha(s.encode('utf-8'))
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def gh(args): return json.loads(subprocess.check_output(['gh',*args],stderr=subprocess.PIPE))
def raw(path):
 return subprocess.check_output(['gh','api','repos/'+REPO+'/contents/'+path+'?ref='+HEAD,'-H','Accept: application/vnd.github.raw'],stderr=subprocess.PIPE)
def snapshot():
 p=gh(['pr','view','70','-R',REPO,'--json','state,isDraft,baseRefName,baseRefOid,headRefName,headRefOid,url,body'])
 c=gh(['api','repos/'+REPO+'/git/commits/'+p['headRefOid']]); br=gh(['api','repos/'+REPO+'/git/ref/heads/'+BRANCH]); pr=gh(['api','repos/'+REPO+'/git/ref/pull/70/head'])
 b=p.get('body') or ''
 return {'schemaVersion':1,'repository':REPO,'pullRequest':70,'url':p['url'],'state':p['state'].upper(),'isDraft':p['isDraft'],'baseRefName':p['baseRefName'],'baseRefOid':p['baseRefOid'],'headRefName':p['headRefName'],'head':p['headRefOid'],'tree':c['tree']['sha'],'parents':[x['sha'] for x in c['parents']],'commitTitle':c['message'].splitlines()[0],'branchRef':br['object']['sha'],'pullRef':pr['object']['sha'],'prBodySha256':sha(b.encode()),'prBodyBytes':len(b.encode())}
def jwrite(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
before=snapshot()
if (before['state'],before['isDraft'],before['head'],before['tree'],before['parents'],before['branchRef'],before['pullRef'])!=('OPEN',True,HEAD,TREE,[PARENT],HEAD,HEAD): raise SystemExit('STOP: live PR/head/tree/ref expected state changed '+json.dumps(before))
pins=json.loads((IN/'catalog-file-pins.json').read_text())
if pins.get('commit')!=PARENT or pins.get('tree')!='2f8ce1af963b315108f668fc31c94ca90ecd1351': raise SystemExit('STOP: candidate-free input not pinned to requested d5ba state')
pinmap=pins['callerSourceFilePins']
newtree=gh(['api','repos/'+REPO+'/git/trees/'+TREE+'?recursive=1'])
if newtree.get('sha')!=TREE or newtree.get('truncated'): raise SystemExit('STOP: latest tree mismatch/truncated')
jwrite(OUT/'latest-head-tree.json',newtree)
entries={x['path']:x for x in newtree['tree']}
d=(OUT/'latest-head-files'); d.mkdir(exist_ok=True)
file_rows=[]; rawmap={}
for path,pin in sorted(pinmap.items()):
 b=raw(path); q=d/path; q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(b); rawmap[path]=b
 e=entries.get(path); actualblob=blob(b)
 if not e or e.get('type')!='blob' or e.get('sha')!=actualblob: raise SystemExit('STOP: latest tree blob mismatch '+path)
 oldsha=pin.get('fileSha256',pin.get('sha256')); oldblob=pin['gitBlob']
 file_rows.append({'path':path,'d5Sha256':oldsha,'d5GitBlob':oldblob,'latestSha256':sha(b),'latestGitBlob':actualblob,'treeBlob':e['sha'],'byteCount':len(b),'matchesD5Pin':sha(b)==oldsha and actualblob==oldblob})
(OUT/'latest-head-pinned-file-comparison.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in file_rows),encoding='utf-8')
if any(not x['matchesD5Pin'] for x in file_rows): raise SystemExit('STOP: at least one source/catalog/caller file pin changed')
labels=json.loads(rawmap['romarr/ui-labels.json'].decode('utf-8'))
src=json.loads(rawmap['romarr/ui-source-messages.json'].decode('utf-8'))
selected=json.loads((IN/'selection.json').read_text())['selectedSources']
current=[json.loads(x) for x in (IN/'current-target-cells.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
if len(selected)!=20 or len(current)!=240: raise SystemExit('STOP: d5 input coverage mismatch')
sm={x['id']:x for x in src['messages']}
catalog=labels['messages']
cell_rows=[]
for c in current:
 entry=catalog.get(c['sourceId']); now=entry.get('translations',{}).get(c['locale']) if entry else None
 sval=entry.get('source') if entry else None; shash=entry.get('sourceHash') if entry else None
 target=now if isinstance(now,str) else json.dumps(now,ensure_ascii=False,sort_keys=True,separators=(',',':')) if now is not None else None
 targetsha=sha(target.encode()) if target is not None else None
 srow=sm.get(c['sourceId'])
 row={'position':c['position'],'sourceId':c['sourceId'],'locale':c['locale'],'d5CurrentTarget':c['currentTarget'],'d5CurrentTargetSha256':c['currentTargetSha256'],'latestCurrentTarget':target,'latestCurrentTargetSha256':targetsha,'currentTargetMatchesD5':target==c['currentTarget'] and targetsha==c['currentTargetSha256'],'d5Source':c['source'],'latestSource':sval,'d5SourceSha256':c['sourceSha256'],'latestSourceSha256':shash,'sourceMatchesD5':sval==c['source'] and shash==c['sourceSha256'],'activeRegistryEntryPresent':srow is not None,'activeRegistrySourceMatches':srow is None or (srow.get('source')==c['source'] and srow.get('sourceHash')==c['sourceSha256'])}
 cell_rows.append(row)
(OUT/'latest-head-cell-preimage-comparison.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in cell_rows),encoding='utf-8')
changed=[x for x in cell_rows if not x['currentTargetMatchesD5'] or not x['sourceMatchesD5']]
if changed: raise SystemExit('STOP: source/current target cell changed; first='+json.dumps(changed[0],ensure_ascii=False))
# Reattest every exact context line in the sealed d5 source-context input against latest exact-head bytes.
contexts=[json.loads(x) for x in (IN/'source-contexts.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
line_rows=[]; seen=set()
for c in contexts:
 for ref in c.get('callerContextRefs',[]):
  path=ref['path']; lines=rawmap[path].decode('utf-8').splitlines()
  for q in ref.get('contextLines',[]):
   n=q['line']; text=lines[n-1] if 0<n<=len(lines) else None
   line_rows.append({'position':c['position'],'sourceId':c['sourceId'],'path':path,'line':n,'d5Text':q['text'],'latestText':text,'d5LineSha256':sha(q['text'].encode()),'latestLineSha256':sha(text.encode()) if text is not None else None,'match':text==q['text']})
   seen.add((path,n))
(OUT/'latest-head-caller-line-comparison.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in line_rows),encoding='utf-8')
if any(not x['match'] for x in line_rows): raise SystemExit('STOP: caller line changed')
after=snapshot()
if any(before[k]!=after[k] for k in ('state','isDraft','head','tree','parents','branchRef','pullRef','prBodySha256')): raise SystemExit('STOP: live PR changed during reattestation')
jwrite(OUT/'latest-live-pr-before.json',before); jwrite(OUT/'latest-live-pr-after.json',after)
result={'schemaVersion':1,'result':'PASS','candidateInputCommit':PARENT,'candidateInputTree':pins['tree'],'latestHead':HEAD,'latestTree':TREE,'latestParent':PARENT,'latestCommitTitle':after['commitTitle'],'prOpenDraft':True,'branchAndPullRefsMatch':True,'beforeAfterStable':True,'sourceCatalogCallerFilesChecked':len(file_rows),'changedPinnedFiles':[],'sourceDefinitionsChecked':20,'sourceDefinitionChanges':0,'currentTargetCellsChecked':240,'currentTargetChanges':0,'callerContextLinesChecked':len(line_rows),'uniqueCallerEvidenceLinesChecked':len(seen),'callerLineChanges':0,'canRelyOnD5CandidateFreeSourceCellInputAtLatestHead':True}
jwrite(OUT/'latest-head-reattestation.json',result)
print(json.dumps(result,indent=2))
