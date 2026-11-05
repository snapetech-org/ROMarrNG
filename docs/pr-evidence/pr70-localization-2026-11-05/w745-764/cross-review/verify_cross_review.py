#!/usr/bin/env python3
from __future__ import annotations
import collections,hashlib,json,pathlib,re,subprocess,unicodedata
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w745-764-cross-review-20261105')
BASE=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w745-764-20261105')
CF=BASE/'candidate-free'; INPUT=CF/'input'; PRIMARY=BASE/'primary-review'
BLIND=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w745-764-independent-blind-20261105')
REPO=pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='68c5c9d4ad13ad5d02b9c455f429d8a5149d363d'; TREE='524db27557a65d64343b15c9983f6ac2f92f90c4'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED={
 ('ui.nothing-matches.965b516df3','de'):'Keine Treffer',
 ('ui.nothing-matches.965b516df3','hi'):'कोई परिणाम नहीं मिला',
 ('ui.nothing-matches.965b516df3','ko'):'일치하는 항목이 없습니다',
 ('ui.nothing-matches.965b516df3','pt-BR'):'Nenhum resultado encontrado.',
 ('ui.nothing-matches.965b516df3','vi'):'Không có kết quả phù hợp',
 ('ui.nothing-missing.ec939b22fd','hi'):'कुछ भी गायब नहीं है।',
 ('ui.on-archive-org.a21e4bd863','de'):'Auf Archive.org',
}
def sha(b):
 if isinstance(b,str):b=b.encode('utf-8')
 return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def rj(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def rjl(p):return [json.loads(x) for x in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def key(r):return (r['sourceId'],r['locale'])
def verify_dir(root):
 root=pathlib.Path(root); sp=root/'SHA256SUMS.txt'; seen={}
 for line in sp.read_text(encoding='utf-8').splitlines():
  if not line:continue
  h,n=line.split('  ',1); p=(root/n).resolve()
  if n in seen or not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=h:raise SystemExit('checksum failed '+str(root/n))
  seen[n]=h
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sp}
 if actual!=set(seen):raise SystemExit('checksum inventory failed '+str(root))
 mp=root/'manifest.json'
 if not mp.is_file() and (root/'input/manifest.json').is_file():mp=root/'input/manifest.json'
 if not mp.is_file() and (root/'summary.json').is_file():mp=root/'summary.json'
 return {'path':str(root),'checksumListSha256':sha(sp.read_bytes()),'manifestSha256':sha(mp.read_bytes()),'fileCount':len(seen)}
def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def tokens(source,target,row):
 ph=lambda s:collections.Counter(re.findall(r'\{[^{}]+\}',s))
 tags=lambda s:collections.Counter(re.findall(r'<[^>]+>',s))
 nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in m) for m in re.findall(r'\d+',s)]
 sn,tn=nums(source),nums(target); missing=[v for v in row.get('sourceProtectedLiterals',[]) if v not in target]
 return {'placeholderMultisetMatches':ph(source)==ph(target),'markupMatches':tags(source)==tags(target),'numericTokensPreserved':all(tn.count(n)>=q for n,q in collections.Counter(sn).items()),'sourceNumericTokens':sn,'targetNumericTokens':tn,'sourceProtectedLiterals':row.get('sourceProtectedLiterals',[]),'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing}
def verify_caller_evidence(contexts,blind):
 by={c['sourceId']:c for c in contexts}; refs=0
 for sid,c in by.items():
  if c.get('head')!=HEAD or c.get('tree') not in (None,TREE):raise SystemExit('context exact head '+sid)
  if c.get('callerless'):
   if c.get('callers') not in (None,[]) or 'source' in c or c.get('sourceTextOmitted') is not True:raise SystemExit('callerless context redaction '+sid)
   continue
  for caller in c.get('callers',[]):
   path=caller['path']; raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:{path}'])
   if sha(raw)!=caller['fileSha256'] or git('rev-parse',f'{HEAD}:{path}')!=caller['gitBlob']:raise SystemExit('caller file hash '+path)
   lines=raw.decode('utf-8').splitlines()
   if lines[caller['line']-1]!=caller['lineText']:raise SystemExit('caller line '+path)
   for e in caller['excerpt']:
    if lines[e['line']-1]!=e['text']:raise SystemExit('caller excerpt '+path)
   refs+=1
 for b in blind:
  c=by[b['sourceId']]
  if b.get('callerless'):
   if b.get('callerEvidence') not in (None,[]):raise SystemExit('blind hold caller text '+b['sourceId'])
   continue
  expected=[{'file':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'excerptSha256':x['excerptSha256'],'matchKind':x['matchKind']} for x in c.get('callers',[])]
  if b.get('callerEvidence')!=expected:raise SystemExit('blind caller binding '+b['sourceId']+'/'+b['locale'])
 return by,refs
def main():
 cfp=verify_dir(CF); cip=verify_dir(INPUT); pp=verify_dir(PRIMARY); bp=verify_dir(BLIND); op=verify_dir(OUT)
 if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'):raise SystemExit('worktree pin/clean')
 pins=rj(OUT/'input-pins.json'); sm=rj(OUT/'summary.json'); manifest=rj(OUT/'manifest.json')
 if (pins.get('head'),pins.get('tree'),pins.get('window'))!=(HEAD,TREE,'W745-W764'):raise SystemExit('output input pin')
 for name,pin in [('candidateFree',cfp),('candidateFreeInput',cip),('primaryReview',pp),('independentBlind',bp)]:
  ob=pins.get(name,{})
  if ob.get('checksumListSha256')!=pin['checksumListSha256'] or ob.get('manifestSha256')!=pin['manifestSha256']:raise SystemExit('input checksum binding '+name)
 if (OUT/'candidate-free-SHA256SUMS.txt').read_bytes()!=(CF/'SHA256SUMS.txt').read_bytes() or (OUT/'candidate-free-input-SHA256SUMS.txt').read_bytes()!=(INPUT/'SHA256SUMS.txt').read_bytes() or (OUT/'primary-SHA256SUMS.txt').read_bytes()!=(PRIMARY/'SHA256SUMS.txt').read_bytes() or (OUT/'blind-SHA256SUMS.txt').read_bytes()!=(BLIND/'SHA256SUMS.txt').read_bytes():raise SystemExit('copied input checksum list')
 cm=rj(INPUT/'manifest.json'); ps=rj(PRIMARY/'summary.json'); bs=rj(BLIND/'summary.json')
 if any(x.get('head')!=HEAD or x.get('tree')!=TREE for x in (cm,ps,bs)):raise SystemExit('input head/tree')
 if (sm.get('result'),sm.get('head'),sm.get('tree'),sm.get('window'),sm.get('cells'))!=('PASS',HEAD,TREE,'W745-W764',240):raise SystemExit('summary pin')
 if (manifest.get('head'),manifest.get('tree'),manifest.get('window'),manifest.get('cellCount'))!=(HEAD,TREE,'W745-W764',240):raise SystemExit('manifest pin')
 cells=rjl(INPUT/'candidate-free-cells.jsonl'); contexts=rjl(INPUT/'source-contexts.jsonl'); pri=rjl(PRIMARY/'ledger.jsonl'); props=rjl(PRIMARY/'proposals.jsonl'); pholds=rjl(PRIMARY/'holds.jsonl'); bli=rjl(BLIND/'blind-ledger.jsonl'); led=rjl(OUT/'cross-ledger.jsonl'); selected=rjl(OUT/'selected-corrections.jsonl')
 if (len(cells),len(contexts),len(pri),len(props),len(pholds),len(bli),len(led),len(selected))!=(240,20,240,5,24,240,240,7):raise SystemExit('row counts')
 expected_order=[(i,l) for i in range(745,765) for l in LOCALES]
 if [(r['catalogZeroBasedIndex'],r['locale']) for r in cells]!=expected_order:raise SystemExit('candidate order')
 maps=[{key(r):r for r in rows} for rows in (cells,pri,bli,led)]
 if any(len(m)!=240 for m in maps) or not all(maps[0].keys()==m.keys() for m in maps[1:]):raise SystemExit('cell identity coverage')
 pby={key(r):r for r in props}; phby={key(r):r for r in pholds}; ctx,refs=verify_caller_evidence(contexts,bli)
 counts=collections.Counter(); action=collections.Counter(); corr=[]; final_fail=0
 for c in cells:
  k=key(c); p=maps[1][k]; b=maps[2][k]; r=maps[3][k]; cid=c['sourceId']+'::'+c['locale']
  for fld in ('sourceId','locale','sourceSha256','currentTargetSha256','callerContextSha256','callerless','catalogZeroBasedIndex'):
   if c.get(fld)!=p.get(fld) or c.get(fld)!=b.get(fld) or c.get(fld)!=r.get(fld):raise SystemExit('row binding '+cid+' '+fld)
  if c.get('callerless'):
   if p.get('decision')!='hold-callerless-hash-only' or b.get('action')!='hold' or r.get('crossDisposition')!='hold-callerless-hash-only':raise SystemExit('callerless decision '+cid)
   if any(f in r for f in ('source','currentTarget','selectedTarget','primaryProposal','blindProposal','crossRationale','primaryRationale','blindRationale')) or not r.get('sourceTextOmitted') or not r.get('targetTextOmitted'):raise SystemExit('cross callerless text leak '+cid)
   if any(f in c for f in ('source','currentTarget')) or any(f in p for f in ('source','currentTarget','proposedTarget')) or any(f in b for f in ('source','currentTarget','proposedTarget')):raise SystemExit('input callerless text leak '+cid)
   counts['hold-callerless-hash-only']+=1;action['hold|hold']+=1;continue
  if r.get('source')!=c.get('source') or r.get('currentTarget')!=c.get('currentTarget') or p.get('source')!=c.get('source') or b.get('source')!=c.get('source') or b.get('currentTarget')!=c.get('currentTarget'):raise SystemExit('caller-backed text binding '+cid)
  if c.get('sourceSha256')!=sha(c['source']) or c.get('currentTargetSha256')!=sha(c['currentTarget']):raise SystemExit('source/current hash '+cid)
  if c.get('callerContextSha256')!=ctx[c['sourceId']].get('contextSha256'):raise SystemExit('caller context hash '+cid)
  if r.get('candidateFreeRecordSha256')!=sha(canon(c)) or r.get('primaryRecordSha256')!=sha(canon(p)) or r.get('blindRecordSha256')!=sha(canon(b)):raise SystemExit('input record hash '+cid)
  po=pby.get(k); override=EXPECTED.get(k)
  if p.get('decision') in ('correction','refinement'):
   if not po or po.get('decision')!=p.get('decision') or po.get('proposedTargetSha256')!=sha(po.get('proposedTarget','')):raise SystemExit('primary proposal binding '+cid)
  elif po:raise SystemExit('unexpected primary proposal '+cid)
  if r.get('primaryProposal')!=(po.get('proposedTarget') if po else None) or r.get('blindProposal')!=b.get('proposedTarget'):raise SystemExit('proposal data binding '+cid)
  if override:
   target=override
   if r.get('crossDisposition')!='correction' or r.get('selectedTarget')!=target or r.get('selectedTargetSha256')!=sha(target):raise SystemExit('cross correction binding '+cid)
   if k in pby and r.get('primaryProposal')!=pby[k].get('proposedTarget') and p.get('decision') in ('correction','refinement'):pass
   if k[1]=='de' and c['sourceId']=='ui.on-archive-org.a21e4bd863':
    if r.get('selectedFrom')!='primary' or p.get('decision')!='correction' or b.get('action')!='retain':raise SystemExit('Archive.org disagreement')
   else:
    if r.get('selectedFrom')!='blind' or b.get('action')!='correction' or b.get('proposedTarget')!=target:raise SystemExit('blind correction selection '+cid)
   corr.append(cid); counts['correction']+=1
  else:
   if r.get('crossDisposition')!='accept-current' or r.get('selectedTarget')!=c.get('currentTarget') or r.get('selectedTargetSha256')!=c.get('currentTargetSha256'):raise SystemExit('current retention '+cid)
   if p.get('decision') not in ('accept-current','hold-callerless-hash-only') or b.get('action')!='retain':raise SystemExit('unresolved reviewer proposal '+cid)
   counts['accept-current']+=1
   target=c['currentTarget']
  target=r['selectedTarget']; ev=tokens(c['source'],target,c)
  if r.get('tokenEvidence')!=ev or not all(ev[n] for n in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')):final_fail+=1
  if override:
   if r.get('selectedFrom')!=('primary' if k==('ui.on-archive-org.a21e4bd863','de') else 'blind'):raise SystemExit('selected reviewer source '+cid)
  paction='correction' if p.get('decision') in ('correction','refinement') else 'retain'
  action[f'{paction}|{b.get("action")}']+=1
 if final_fail:raise SystemExit('final target token failures '+str(final_fail))
 if counts!=collections.Counter({'accept-current':209,'correction':7,'hold-callerless-hash-only':24}):raise SystemExit('cross counts '+str(counts))
 if {key(r):r.get('selectedTarget') for r in selected}!={k:v for k,v in EXPECTED.items()}:raise SystemExit('selected correction set')
 expected_action=collections.Counter({'retain|retain':209,'retain|correction':2,'correction|correction':4,'correction|retain':1,'hold|hold':24})
 if action!=expected_action or sm.get('primaryBlindActionCrossTab')!=dict(action):raise SystemExit('review action cross tab '+str(action))
 if sm.get('actionDisagreementCells')!=3 or sm.get('independentlyReconciledCells')!=7 or sm.get('callerReferences')!=27:raise SystemExit('reconciliation counts')
 prior=rjl(OUT/'prior-active-holds-hash-only.jsonl'); current=rjl(OUT/'current-window-holds-hash-only.jsonl')
 if len(prior)!=964 or len(current)!=24 or sm.get('resultingActiveHolds')!=988:raise SystemExit('hold chain')
 if any(any(f in h for f in ('source','sourceText','currentTarget','target','targetText','proposedTarget')) for h in prior+current):raise SystemExit('hold text leak')
 nb=sm.get('nextBoundary',{})
 if (nb.get('continuationIndex'),nb.get('oneBasedPosition'),nb.get('sourceId'),nb.get('sourceSha256'))!=(765,766,'ui.on-this-day.d011904834','d011904834fe28b25d7a9d9043c048b00e2b6f0ebf162498850f2105696195d6'):raise SystemExit('next boundary')
 files=manifest.get('files',{}); actual={p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')}
 if actual!=set(files):raise SystemExit('output manifest inventory')
 for n,h in files.items():
  if sha((OUT/n).read_bytes())!=h:raise SystemExit('manifest file hash '+n)
 print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':240,'crossDispositionCounts':dict(counts),'selectedCorrections':len(selected),'primaryBlindActionCrossTab':dict(action),'priorActiveHolds':len(prior),'currentHashOnlyHolds':len(current),'resultingActiveHolds':len(prior)+len(current),'exactCallerReferencesVerified':refs,'nextBoundary':nb,'outputFilesVerified':len(files)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
