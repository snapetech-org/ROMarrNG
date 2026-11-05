#!/usr/bin/env python3
import collections, hashlib, json, re, subprocess
from pathlib import Path
REPO=Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
TASK=Path(__file__).resolve().parents[1]
CF=TASK/'candidate-free/input/candidate-free-cells.jsonl'
ROOT=TASK/'root-adjudication/root-disposition-ledger.jsonl'
HEAD='68c5c9d4ad13ad5d02b9c455f429d8a5149d363d'
TREE='524db27557a65d64343b15c9983f6ac2f92f90c4'
CAT='romarr/ui-labels.json'
OUT=Path(__file__).resolve().parent/'readback-before-commit.json'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def token_ok(source,target,literals):
 pats=[r'\{[^{}]+\}',r'<[^>]+>',r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])']
 return all(collections.Counter(re.findall(p,source))==collections.Counter(re.findall(p,target)) for p in pats) and all(x in target for x in literals)
assert git('rev-parse','HEAD')==HEAD and git('rev-parse','HEAD^{tree}')==TREE
assert git('status','--porcelain=v1','--untracked-files=all')=='','worktree must be clean before application'
cat=REPO/CAT; before=cat.read_bytes()
assert before==subprocess.check_output(['git','-C',str(REPO),'show',f'HEAD:{CAT}'])
data=json.loads(before); canonical=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert before==canonical,'unexpected catalog formatting'
cf={(r['position'],r['locale']):r for r in lines(CF)}
roots=[r for r in lines(ROOT) if r['rootDisposition']=='correction']
assert len(cf)==240 and len(roots)==7
changes=[]
for r in roots:
 c=cf[(r['position'],r['locale'])]
 assert c['sourceId']==r['sourceId'] and c['source']==r['source'] and c['currentTarget']==r['currentTarget']
 assert c['sourceSha256']==r['sourceSha256'] and c['currentTargetSha256']==r['currentTargetSha256'] and c['callerContextSha256']==r['callerContextSha256']
 assert tsha(c['source'])==c['sourceSha256'] and tsha(c['currentTarget'])==c['currentTargetSha256']
 target=r['rootTarget']; assert tsha(target)==r['rootTargetSha256'] and token_ok(c['source'],target,c['sourceProtectedLiterals'])
 entry=data['messages'][r['sourceId']]; old=entry['translations'][r['locale']]
 assert old==c['currentTarget'] and tsha(old)==r['currentTargetSha256']
 entry['translations'][r['locale']]=target
 changes.append({'position':r['position'],'locale':r['locale'],'sourceId':r['sourceId'],'before':old,'beforeSha256':tsha(old),'after':target,'afterSha256':tsha(target),'callerContextSha256':r['callerContextSha256']})
out=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'); cat.write_bytes(out)
result=json.loads(cat.read_text(encoding='utf-8')); olddata=json.loads(before)
assert list(result['messages'])==list(olddata['messages'])
changed=[]
for sid,entry in olddata['messages'].items():
 for locale,old in entry['translations'].items():
  new=result['messages'][sid]['translations'][locale]
  if old!=new: changed.append((sid,locale,old,new))
assert len(changed)==7 and {(x[0],x[1]) for x in changed}=={(r['sourceId'],r['locale']) for r in roots}
assert all(result['messages'][r['sourceId']]['translations'][r['locale']]==r['rootTarget'] for r in roots)
assert all(locale in m['translations'] and m['translations'][locale] for locale in LOCALES for m in result['messages'].values())
readback={'artifact':'ROMarrNG PR #70 W745-W764 product application readback','repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W745-W764','inputHead':HEAD,'inputTree':TREE,'changedCatalogPath':CAT,'changedCellCount':len(changes),'expectedChangedCellCount':7,'catalogKeyOrderPreserved':True,'allOtherCatalogCellsUnchanged':True,'localeCount':12,'messageCountPerLocale':1836,'candidateFreeInputSha256':sha(CF.read_bytes()),'rootDispositionInputSha256':sha(ROOT.read_bytes()),'targetReadback':changes,'catalogSha256After':sha(out),'productDiffNames':[CAT],'qualifiedNativeSpeakerApproval':False,'headedBrowserAcceptance':False,'productCommitPending':True}
OUT.write_text(json.dumps(readback,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','changedCellCount':7,'catalogSha256After':sha(out),'catalogKeyOrderPreserved':True,'allOtherCatalogCellsUnchanged':True,'readback':str(OUT)},ensure_ascii=False,indent=2))
