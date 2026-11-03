#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys,re
OUT=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w445-464-blind-20261103')
REPO='snapetech-org/ROMarrNG'; PR=70; HEAD='d5ba7f1f268501f45227388c46d5f938ed0c9191'; TREE='2f8ce1af963b315108f668fc31c94ca90ecd1351'
BRANCH='task/localization-translation-review-20261030'
QUEUE_PATH='docs/pr-evidence/pr70-localization-2026-11-03/romarrng-pr70-w365-384-candidate-free-20261103/input/source-queue.json'
PATHS=[QUEUE_PATH,'romarr/ui-source-messages.json','romarr/ui-labels.json','romarr/ui.py','romarr/i18n_runtime.js']
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(b): return hashlib.sha256(b).hexdigest()
def st(s): return sha(s.encode('utf-8'))
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def gh(args): return json.loads(subprocess.check_output(['gh',*args],stderr=subprocess.PIPE))
def raw(path):
 return subprocess.check_output(['gh','api','repos/'+REPO+'/contents/'+path+'?ref='+HEAD,'-H','Accept: application/vnd.github.raw'],stderr=subprocess.PIPE)
def snapshot():
 p=gh(['pr','view',str(PR),'-R',REPO,'--json','state,isDraft,baseRefName,baseRefOid,headRefName,headRefOid,url,body'])
 c=gh(['api','repos/'+REPO+'/git/commits/'+p['headRefOid']]); br=gh(['api','repos/'+REPO+'/git/ref/heads/'+BRANCH]); pr=gh(['api','repos/'+REPO+'/git/ref/pull/'+str(PR)+'/head'])
 b=p.get('body') or ''
 return {'schemaVersion':1,'repository':REPO,'pullRequest':PR,'url':p['url'],'state':p['state'].upper(),'isDraft':p['isDraft'],'baseRefName':p['baseRefName'],'baseRefOid':p['baseRefOid'],'headRefName':p['headRefName'],'head':p['headRefOid'],'tree':c['tree']['sha'],'parents':[x['sha'] for x in c['parents']],'branchRef':br['object']['sha'],'pullRef':pr['object']['sha'],'prBodySha256':sha(b.encode()),'prBodyBytes':len(b.encode())}
def jwrite(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def jsonl(p,rows): p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf-8')
if OUT.exists(): raise SystemExit('FAIL: output path exists, preserving it')
before=snapshot()
if (before['state'],before['isDraft'],before['head'],before['tree'],before['branchRef'],before['pullRef'])!=('OPEN',True,HEAD,TREE,HEAD,HEAD): raise SystemExit('FAIL: live PR/head/tree/ref mismatch')
OUT.mkdir(); (OUT/'input').mkdir(); (OUT/'current-head-files').mkdir()
tree=gh(['api','repos/'+REPO+'/git/trees/'+TREE+'?recursive=1'])
if tree.get('sha')!=TREE or tree.get('truncated'): raise SystemExit('FAIL: tree mismatch/truncated')
jwrite(OUT/'input/new-head-tree.json',tree); entries={x['path']:x for x in tree['tree']}
pins={}
for p in PATHS:
 b=raw(p); (OUT/'current-head-files'/p).parent.mkdir(parents=True,exist_ok=True); (OUT/'current-head-files'/p).write_bytes(b)
 e=entries.get(p)
 if not e or e.get('sha')!=blob(b): raise SystemExit('FAIL: file/tree blob mismatch '+p)
 pins[p]={'path':p,'sha256':sha(b),'gitBlob':blob(b),'byteCount':len(b)}
jwrite(OUT/'input/file-pins.json',{'repository':REPO,'pullRequest':PR,'head':HEAD,'tree':TREE,'files':pins})
queue=json.loads((OUT/'current-head-files'/QUEUE_PATH).read_text(encoding='utf-8'))
src=json.loads((OUT/'current-head-files/romarr/ui-source-messages.json').read_text(encoding='utf-8'))
labels=json.loads((OUT/'current-head-files/romarr/ui-labels.json').read_text(encoding='utf-8'))
if len(queue['messages'])<464: raise SystemExit('FAIL: source queue does not contain requested ranks')
source_by_id={x['id']:x for x in src['messages']}
catalog=labels['messages']
selected=queue['messages'][444:464]
if len(selected)!=20: raise SystemExit('FAIL: rank slice incomplete')
sources=[]; cells=[]
for pos,m in enumerate(selected,start=445):
 sid=m['id']; sr=source_by_id.get(sid); rec=catalog.get(sid)
 if sr is None or rec is None: raise SystemExit('FAIL: source/catalog ID missing '+sid)
 if (sr.get('source'),sr.get('sourceHash'))!=(m['source'],m['sourceHash']) or (rec.get('source'),rec.get('sourceHash'))!=(m['source'],m['sourceHash']) or sha(m['source'].encode())!=m['sourceHash']: raise SystemExit('FAIL: current source definition/hash mismatch '+sid)
 if not m.get('locations'): raise SystemExit('FAIL: source missing caller locations '+sid)
 sources.append({'position':pos,'rank':pos,'id':sid,'source':m['source'],'sourceHash':m['sourceHash'],'category':m.get('category'),'locations':m['locations'],'pendingLocales':m.get('pendingLocales',[]),'dynamicPlaceholders':m.get('dynamicPlaceholders',[])})
 tr=rec.get('translations',{})
 for locale in LOCALES:
  value=tr.get(locale)
  canon=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')) if not isinstance(value,str) else value
  cells.append({'position':pos,'locale':locale,'id':sid,'source':m['source'],'sourceHash':m['sourceHash'],'category':m.get('category'),'dynamicPlaceholders':m.get('dynamicPlaceholders',[]),'currentTarget':value,'currentTargetCanonical':canon,'currentTargetSha256':sha(canon.encode('utf-8')),'targetPresent':value is not None,'localePendingInQueue':locale in m.get('pendingLocales',[]),'catalogPath':'romarr/ui-labels.json'})
jsonl(OUT/'input/source-cells.jsonl',sources); jsonl(OUT/'input/current-target-cells.jsonl',cells)
ui=(OUT/'current-head-files/romarr/ui.py').read_text(encoding='utf-8').splitlines()
blocks=[]
for m in sources:
 for loc in m['locations']:
  mm=re.fullmatch(r'(.+):(\d+)(?:-(\d+))?',loc)
  if not mm: raise SystemExit('FAIL: unsupported source location '+loc)
  path,a,b=mm.group(1),int(mm.group(2)),int(mm.group(3) or mm.group(2))
  if path!='romarr/ui.py' or a<1 or b>len(ui): raise SystemExit('FAIL: caller path/line outside pinned source')
  start=max(1,a-3); end=min(len(ui),b+3)
  lines=[{'line':n,'text':ui[n-1],'sha256':sha(ui[n-1].encode())} for n in range(start,end+1)]
  blocks.append({'position':m['position'],'sourceId':m['id'],'path':path,'location':loc,'startLine':start,'endLine':end,'lines':lines})
jsonl(OUT/'input/caller-context-blocks.jsonl',blocks)
jwrite(OUT/'input/pr-attestation-before.json',before)
after=snapshot()
if any(before[k]!=after[k] for k in ('state','isDraft','head','tree','branchRef','pullRef','prBodySha256')): raise SystemExit('FAIL: live PR changed during input extraction')
jwrite(OUT/'input/pr-attestation-after.json',after)
(OUT/'input/README.md').write_text('''# ROMarrNG W445-W464 candidate-blind source/cell inputs\n\nSource queue slice ranks 445-464 was derived from the source-only queue committed at the pinned exact application head. Each source text/hash is independently matched to romarr/ui-source-messages.json and romarr/ui-labels.json at that same head. Current targets are captured without any reviewer proposals. Caller snippets are pinned from romarr/ui.py at source-declared locations. No candidate-free or primary output was opened or read.\n''',encoding='utf-8')
(OUT/'build_blind_review.py').write_text(Path(__file__).read_text(encoding='utf-8'),encoding='utf-8')
files=[]
for p in sorted(x for x in OUT.rglob('*') if x.is_file() and x.name not in ('manifest.json','SHA256SUMS.txt')):
 files.append({'path':p.relative_to(OUT).as_posix(),'sha256':sha(p.read_bytes()),'byteCount':p.stat().st_size})
jwrite(OUT/'input/manifest.json',{'schemaVersion':1,'purpose':'independent blind review source/cell inputs','head':HEAD,'tree':TREE,'files':files})
print(json.dumps({'result':'INPUTS_PASS','head':HEAD,'tree':TREE,'sources':len(sources),'cells':len(cells),'callerBlocks':len(blocks),'locales':LOCALES,'pins':pins,'outputPath':str(OUT)},ensure_ascii=False,indent=2))
