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
CORRECTIONS={
 ('ui.nothing-matches.965b516df3','de'):('blind','Keine Treffer','The exact caller renders this in a bold empty-result heading followed by a search prompt. “Keine Treffer” states no matches directly and fits the heading style without a full stop.'),
 ('ui.nothing-matches.965b516df3','hi'):('blind','कोई परिणाम नहीं मिला','The exact caller is an empty plugin-search/category state. The current fragment is incomplete; this says no results were found.'),
 ('ui.nothing-matches.965b516df3','ko'):('blind','일치하는 항목이 없습니다','The exact caller is an empty plugin-search/category state. This gives a complete no-matching-items message; omit sentence punctuation in the bold heading.'),
 ('ui.nothing-matches.965b516df3','pt-BR'):('blind','Nenhum resultado encontrado.','The exact caller is an empty plugin-search/category state. This says no results were found, avoiding the current implication that items do not go together.'),
 ('ui.nothing-matches.965b516df3','vi'):('blind','Không có kết quả phù hợp','The exact caller is an empty plugin-search/category state. The current wording says only “not matched”; this makes the absence of matching results explicit.'),
 ('ui.nothing-missing.ec939b22fd','hi'):('blind','कुछ भी गायब नहीं है।','The exact caller renders this only when the Wanted/missing-items table is empty. This means nothing is missing; the current wording instead suggests nothing remains.'),
 ('ui.on-archive-org.a21e4bd863','de'):('primary','Auf Archive.org','The exact caller labels the count of games hosted on Archive.org, alongside browser, server-streaming, and download-only categories. “Auf” expresses that hosting location; “Über” reads as about/via.'),
}
def sha(b):
 if isinstance(b,str):b=b.encode('utf-8')
 return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def rj(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def rjl(p):return [json.loads(x) for x in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def wj(p,v):p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def wjl(p,rows):p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf-8')
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
def verify_contexts(contexts,cells,blind):
 cellmap={key(r):r for r in cells}; bysource={}
 for c in contexts:
  if c.get('head')!=HEAD or c.get('tree') not in (None,TREE):raise SystemExit('caller context pin '+c.get('sourceId',''))
  bysource[c['sourceId']]=c
 refs=0
 for sid,c in bysource.items():
  associated=[r for r in cells if r['sourceId']==sid]
  if not associated or any(r.get('callerContextSha256')!=c.get('contextSha256') for r in associated):raise SystemExit('cell context hash binding '+sid)
  if c.get('callerless'):
   if c.get('callers') not in (None,[]) or 'source' in c or c.get('sourceTextOmitted') is not True:raise SystemExit('callerless context text leak '+sid)
   continue
  for caller in c.get('callers',[]):
   path=caller['path']; raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:{path}'])
   if sha(raw)!=caller['fileSha256'] or git('rev-parse',f'{HEAD}:{path}')!=caller['gitBlob']:raise SystemExit('source file pin '+path)
   lines=raw.decode('utf-8').splitlines()
   if lines[caller['line']-1]!=caller['lineText']:raise SystemExit('caller line mismatch '+path)
   for e in caller['excerpt']:
    if lines[e['line']-1]!=e['text']:raise SystemExit('caller excerpt mismatch '+path)
   refs+=1
 for b in blind:
  c=bysource[b['sourceId']]
  if b.get('callerless'):
   if b.get('callerEvidence') not in (None,[]):raise SystemExit('blind callerless evidence leak '+b['sourceId'])
   continue
  expected=[{'file':x['path'],'line':x['line'],'lineSha256':x['lineSha256'],'excerptSha256':x['excerptSha256'],'matchKind':x['matchKind']} for x in c.get('callers',[])]
  if b.get('callerEvidence')!=expected:raise SystemExit('blind/caller evidence mismatch '+b['sourceId']+'/'+b['locale'])
 return bysource,refs
def tokens(source,target,source_row):
 ph=lambda s:collections.Counter(re.findall(r'\{[^{}]+\}',s))
 tags=lambda s:collections.Counter(re.findall(r'<[^>]+>',s))
 nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in m) for m in re.findall(r'\d+',s)]
 sp,tp=ph(source),ph(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target)
 protected=source_row.get('sourceProtectedLiterals',[])
 missing=[v for v in protected if v not in target]
 return {'placeholderMultisetMatches':sp==tp,'markupMatches':st==tt,'numericTokensPreserved':all(tn.count(n)>=q for n,q in collections.Counter(sn).items()),'sourceNumericTokens':sn,'targetNumericTokens':tn,'sourceProtectedLiterals':protected,'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing}
def main():
 if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'):raise SystemExit('worktree pin/clean')
 cfpin=verify_dir(CF); inputpin=verify_dir(INPUT); ppin=verify_dir(PRIMARY); bpin=verify_dir(BLIND)
 cm=rj(INPUT/'manifest.json'); ps=rj(PRIMARY/'summary.json'); pm=rj(PRIMARY/'manifest.json'); bs=rj(BLIND/'summary.json')
 if any(x.get('head')!=HEAD or x.get('tree')!=TREE for x in (cm,ps,pm,bs)):raise SystemExit('input pin mismatch')
 if (cm.get('window'),cm.get('cellCount'),cm.get('callerBackedCells'),cm.get('callerlessHashOnlyCells'))!=('W745-W764',240,216,24):raise SystemExit('candidate-free summary pin')
 if (ps.get('window'),ps.get('cellCount'),ps.get('decisionCounts'))!=('W745-W764',240,{'accept-current':211,'correction':4,'refinement':1,'hold-callerless-hash-only':24}):raise SystemExit('primary summary pin')
 if (bs.get('window'),bs.get('cellCount'),bs.get('decisionCounts'))!=('W745-W764',240,{'retain':210,'correction':6,'hold':24}):raise SystemExit('blind summary pin')
 pref=rj(PRIMARY/'input-reference.json')
 if pref.get('candidateFreeManifestSha256')!=sha((INPUT/'manifest.json').read_bytes()) or pref.get('candidateFreeChecksumListSha256')!=sha((CF/'SHA256SUMS.txt').read_bytes()) or pref.get('candidateFreeCellRowsSha256')!=sha((INPUT/'candidate-free-cells.jsonl').read_bytes()):raise SystemExit('primary candidate-free bindings')
 if bs.get('candidateFreeChecksumListSha256')!=sha((CF/'SHA256SUMS.txt').read_bytes()) or bs.get('candidateFreeManifestSha256')!=sha((INPUT/'manifest.json').read_bytes()):raise SystemExit('blind candidate-free bindings')
 if (BLIND/'input-SHA256SUMS.txt').read_bytes()!=(CF/'SHA256SUMS.txt').read_bytes():raise SystemExit('blind candidate-free input sum copy')
 cells=rjl(INPUT/'candidate-free-cells.jsonl'); contexts=rjl(INPUT/'source-contexts.jsonl'); primary=rjl(PRIMARY/'ledger.jsonl'); proposals=rjl(PRIMARY/'proposals.jsonl'); p_holds=rjl(PRIMARY/'holds.jsonl'); blind=rjl(BLIND/'blind-ledger.jsonl')
 if (len(cells),len(contexts),len(primary),len(proposals),len(p_holds),len(blind))!=(240,20,240,5,24,240):raise SystemExit('input row counts')
 order=[(i,l) for i in range(745,765) for l in LOCALES]
 if [(x['catalogZeroBasedIndex'],x['locale']) for x in cells]!=order:raise SystemExit('candidate-free row order')
 maps=[{key(r):r for r in rows} for rows in (cells,primary,blind)]
 if any(len(m)!=240 for m in maps) or not all(maps[0].keys()==m.keys() for m in maps[1:]):raise SystemExit('cell identities')
 pby={key(r):r for r in proposals}; p_hold={key(r):r for r in p_holds}
 if len(pby)!=5 or len(p_hold)!=24:raise SystemExit('proposal/hold identity counts')
 bysource,caller_refs=verify_contexts(contexts,cells,blind)
 out=[]; corrections=[]; counts=collections.Counter(); action_tab=collections.Counter(); revised=0; final_token_failures=0
 for c in cells:
  k=key(c); p=maps[1][k]; b=maps[2][k]; cid=c['sourceId']+'::'+c['locale']
  if any(c.get(f)!=p.get(f) for f in ('sourceId','locale','sourceSha256','currentTargetSha256','callerContextSha256','callerless')):raise SystemExit('primary cell binding '+cid)
  if any(c.get(f)!=b.get(f) for f in ('sourceId','locale','sourceSha256','currentTargetSha256','callerContextSha256','callerless')):raise SystemExit('blind cell binding '+cid)
  if c.get('sourceIdSha256') and sha(c['sourceId'])!=c['sourceIdSha256']:raise SystemExit('source ID hash '+cid)
  if c.get('callerless'):
   phold=p_hold.get(k)
   if not phold or p.get('decision')!='hold-callerless-hash-only' or b.get('action')!='hold':raise SystemExit('callerless hold binding '+cid)
   for row in (c,p,b,phold):
    if any(f in row for f in ('source','currentTarget','proposedTarget','target')):raise SystemExit('callerless wording leak '+cid)
   out.append({'cellId':cid,'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],'position':c['position'],'sourceId':c['sourceId'],'locale':c['locale'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerless':True,'sourceTextOmitted':True,'targetTextOmitted':True,'primaryDecision':'hold-callerless-hash-only','blindAction':'hold','crossDisposition':'hold-callerless-hash-only','confidence':'high'})
   counts['hold-callerless-hash-only']+=1; action_tab['hold|hold']+=1; continue
  if not all(f in c for f in ('source','currentTarget')) or p.get('source')!=c['source'] or p.get('currentTarget')!=c['currentTarget'] or b.get('source')!=c['source'] or b.get('currentTarget')!=c['currentTarget']:raise SystemExit('source/target binding '+cid)
  if sha(c['source'])!=c['sourceSha256'] or sha(c['currentTarget'])!=c['currentTargetSha256']:raise SystemExit('source/target hash '+cid)
  if c.get('callerContextSha256')!=bysource[c['sourceId']].get('contextSha256'):raise SystemExit('caller context binding '+cid)
  pp=pby.get(k); pdecision=p.get('decision')
  if pdecision in ('correction','refinement'):
   if not pp or pp.get('decision')!=pdecision or pp.get('proposedTargetSha256')!=sha(pp.get('proposedTarget','')):raise SystemExit('primary proposal missing/bad '+cid)
  elif pp:raise SystemExit('unexpected primary proposal '+cid)
  bdecision=b.get('action')
  if bdecision=='correction' and not b.get('proposedTarget'):raise SystemExit('blind proposal missing '+cid)
  override=CORRECTIONS.get(k)
  if override:
   selected_from,target,why=override
   if selected_from=='blind' and (bdecision!='correction' or b.get('proposedTarget')!=target):raise SystemExit('blind correction mismatch '+cid)
   if selected_from=='primary' and (not pp or pp.get('proposedTarget')!=target):raise SystemExit('primary correction mismatch '+cid)
   cross='correction'; revised+=1
  else:
   if (pdecision in ('correction','refinement') or bdecision=='correction'):raise SystemExit('unreconciled proposal outside explicit decisions '+cid)
   selected_from='current'; target=c['currentTarget']; cross='accept-current'
   why='The current target adequately conveys the source in its exact pinned caller context; neither review found a material change outside the explicitly reconciled cells.'
  tev=tokens(c['source'],target,c)
  if not all(tev[k2] for k2 in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')):final_token_failures+=1
  primary_action='correction' if pdecision in ('correction','refinement') else 'retain'
  action_tab[f'{primary_action}|{bdecision}']+=1
  row={'cellId':cid,'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],'position':c['position'],'sourceId':c['sourceId'],'locale':c['locale'],'callerless':False,'source':c['source'],'sourceSha256':c['sourceSha256'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'callerCount':c['literalCallerCount'],'catalogTranslationHash':c['catalogTranslationHash'],'candidateFreeRecordSha256':sha(canon(c)),'primaryRecordSha256':sha(canon(p)),'blindRecordSha256':sha(canon(b)),'callerEvidence':b.get('callerEvidence',[]),'primaryDecision':pdecision,'primaryProposal':pp.get('proposedTarget') if pp else None,'primaryRationale':pp.get('rationale') if pp else p.get('rationale'),'blindAction':bdecision,'blindProposal':b.get('proposedTarget'),'blindRationale':b.get('decisionRationale'),'crossDisposition':cross,'selectedFrom':selected_from,'selectedTarget':target,'selectedTargetSha256':sha(target),'tokenEvidence':tev,'crossRationale':why,'confidence':'moderate','reviewOnly':True}
  out.append(row);counts[cross]+=1
  if cross=='correction':corrections.append({'cellId':cid,'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],'sourceId':c['sourceId'],'locale':c['locale'],'source':c['source'],'sourceSha256':c['sourceSha256'],'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],'selectedTarget':target,'selectedTargetSha256':sha(target),'callerContextSha256':c['callerContextSha256'],'selectedFrom':selected_from,'crossRationale':why,'tokenEvidence':tev,'reviewOnly':True})
 if final_token_failures:raise SystemExit('final target token failures '+str(final_token_failures))
 if counts!=collections.Counter({'accept-current':209,'correction':7,'hold-callerless-hash-only':24}) or revised!=7:raise SystemExit('cross disposition count '+str(counts))
 expected={
  ('ui.nothing-matches.965b516df3','de'):'Keine Treffer',
  ('ui.nothing-matches.965b516df3','hi'):'कोई परिणाम नहीं मिला',
  ('ui.nothing-matches.965b516df3','ko'):'일치하는 항목이 없습니다',
  ('ui.nothing-matches.965b516df3','pt-BR'):'Nenhum resultado encontrado.',
  ('ui.nothing-matches.965b516df3','vi'):'Không có kết quả phù hợp',
  ('ui.nothing-missing.ec939b22fd','hi'):'कुछ भी गायब नहीं है।',
  ('ui.on-archive-org.a21e4bd863','de'):'Auf Archive.org'}
 if {key(r):r['selectedTarget'] for r in corrections}!=expected:raise SystemExit('correction output mismatch')
 prior=rjl(INPUT/'prior-hold-reattestation.jsonl')
 if len(prior)!=964 or any(any(f in r for f in ('source','sourceText','currentTarget','target','targetText','proposedTarget')) for r in prior):raise SystemExit('prior hold chain')
 current=[]
 for c in cells:
  if c.get('callerless'):
   current.append({'sourceId':c['sourceId'],'locale':c['locale'],'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'sourceTextOmitted':True,'targetTextOmitted':True})
 if len(current)!=24:raise SystemExit('current hold count')
 boundary=rjl(INPUT/'selection-boundary.jsonl')
 post=next((x for x in boundary if x.get('role')=='catalog-after-selected-end'),None)
 if not post or (post.get('catalogZeroBasedIndex'),post.get('sourceId'),post.get('sourceSha256'))!=(765,'ui.on-this-day.d011904834','d011904834fe28b25d7a9d9043c048b00e2b6f0ebf162498850f2105696195d6'):raise SystemExit('next boundary')
 # Keep the exact original input checksum inventories alongside the cross packet.
 for src,name in ((CF/'SHA256SUMS.txt','candidate-free-SHA256SUMS.txt'),(INPUT/'SHA256SUMS.txt','candidate-free-input-SHA256SUMS.txt'),(PRIMARY/'SHA256SUMS.txt','primary-SHA256SUMS.txt'),(BLIND/'SHA256SUMS.txt','blind-SHA256SUMS.txt')):
  (OUT/name).write_bytes(src.read_bytes())
 wjl(OUT/'cross-ledger.jsonl',out);wjl(OUT/'selected-corrections.jsonl',corrections);wjl(OUT/'prior-active-holds-hash-only.jsonl',prior);wjl(OUT/'current-window-holds-hash-only.jsonl',current);wjl(OUT/'caller-contexts-pinned.jsonl',contexts)
 ip={'schemaVersion':1,'repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W745-W764','catalogZeroBasedIndices':[745,764],'catalogOneBasedPositions':[746,765],'head':HEAD,'tree':TREE,'candidateFree':cfpin,'candidateFreeInput':inputpin,'candidateFreeCellsSha256':sha((INPUT/'candidate-free-cells.jsonl').read_bytes()),'primaryReview':ppin,'primaryManifestSha256':sha((PRIMARY/'manifest.json').read_bytes()),'primaryInputReferenceSha256':sha((PRIMARY/'input-reference.json').read_bytes()),'primaryProposalsSha256':sha((PRIMARY/'proposals.jsonl').read_bytes()),'independentBlind':bpin,'blindLedgerSha256':sha((BLIND/'blind-ledger.jsonl').read_bytes()),'exactCallerFilesRechecked':True,'worktree':str(REPO),'worktreeClean':True,'inputReviewNote':'Independent cross-review reconciled candidate-free current cells with the separately pinned primary and blind ledgers. No prior cross-review packet was used.'}
 wj(OUT/'input-pins.json',ip)
 action_disagreements=sum(v for pair,v in action_tab.items() if pair.split('|',1)[0]!=pair.split('|',1)[1])
 summary={'result':'PASS','artifact':'ROMarrNG PR #70 W745-W764 independent cross-review','repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':'W745-W764','catalogZeroBasedIndices':[745,764],'catalogOneBasedPositions':[746,765],'cells':240,'callerBackedCells':216,'callerlessHashOnlyCells':24,'callerReferences':caller_refs,'primaryDecisionCounts':{'accept-current':211,'correction':4,'refinement':1,'hold-callerless-hash-only':24},'blindActionCounts':{'retain':210,'correction':6,'hold':24},'primaryBlindActionCrossTab':dict(action_tab),'crossDispositionCounts':dict(counts),'independentlyReconciledCells':7,'actionDisagreementCells':action_disagreements,'priorActiveHoldsPreservedHashOnly':964,'newCallerlessHoldsHashOnly':24,'resultingActiveHolds':988,'finalTokenFailures':0,'nextBoundary':{'continuationIndex':765,'oneBasedPosition':766,'sourceId':'ui.on-this-day.d011904834','sourceSha256':'d011904834fe28b25d7a9d9043c048b00e2b6f0ebf162498850f2105696195d6'},'repositoryEdited':False,'catalogsEdited':False,'testsBuildsScansCiRun':False}
 wj(OUT/'summary.json',summary)
 readme=f'''# ROMarrNG PR #70 W745–W764 independent cross-review\n\nPinned to head `{HEAD}`, tree `{TREE}`. This packet reconciles the candidate-free, primary, and independent blind inputs for 240 cells across 12 locales. All three input checksum inventories and verifiers passed; the pinned worktree remained clean.\n\nCross dispositions: 209 accept-current, 7 corrections, and 24 callerless hash-only holds. The corrections cover German, Hindi, Korean, Brazilian Portuguese, and Vietnamese “Nothing matches”; Hindi “Nothing missing”; and German “On Archive.org.” The empty-state caller is a bold heading followed by a search prompt; the Wanted empty state is shown only when no missing items remain; the Archive.org label is a hosting-origin category. The cross review selects the blind wording for the six empty-state corrections and primary wording `Auf Archive.org` for German.\n\nThe packet preserves 964 prior hash-only holds and adds 24 current callerless cells (988 active holds). Callerless ledger rows contain hashes and identifiers only; no source, current target, proposal, or rationale text is included. The next boundary is catalog index 765 / one-based position 766, source `ui.on-this-day.d011904834`.\n\nVerify with `python3 -B verify_cross_review.py`. The recommendations are review-only; no repository/catalog changes or tests, builds, scans, or CI were run.\n'''
 (OUT/'README.md').write_text(readme,encoding='utf-8')
 files={p.relative_to(OUT).as_posix():sha(p.read_bytes()) for p in OUT.rglob('*') if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')}
 manifest={'schemaVersion':1,'artifact':'ROMarrNG PR #70 W745-W764 independent cross-review','repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':'W745-W764','cellCount':240,'crossDispositionCounts':dict(counts),'priorActiveHoldsPreserved':964,'currentCallerlessHolds':24,'resultingActiveHolds':988,'nextBoundary':summary['nextBoundary'],'files':files}
 wj(OUT/'manifest.json',manifest)
 entries=[f'{sha(p.read_bytes())}  {p.relative_to(OUT).as_posix()}' for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt']
 (OUT/'SHA256SUMS.txt').write_text('\n'.join(entries)+'\n',encoding='utf-8')
 print(json.dumps({'result':'SEALED','output':str(OUT),'counts':dict(counts),'corrections':len(corrections),'priorHolds':len(prior),'activeHolds':len(prior)+len(current),'callerReferences':caller_refs,'sha256sumsSha256':sha((OUT/'SHA256SUMS.txt').read_bytes())},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
