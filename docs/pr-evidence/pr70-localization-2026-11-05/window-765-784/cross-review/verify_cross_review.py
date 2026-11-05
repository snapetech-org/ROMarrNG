#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, pathlib, re, subprocess, unicodedata
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-third-party-cross-review-20261105')
BASE=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105')
CF=BASE/'candidate-free'; INPUT=CF/'input'; PRIMARY=BASE/'primary-review'
REPO=pathlib.Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='9714d7cf69c687685b4f65cbd9627a56830bab85'; TREE='c8eb66573f10b2390a02df05033f5133425d5e41'
WINDOW='W765-W784'; LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
EXPECTED={
 ('ui.on-this-install.ca75d54e64','ar'):('correction','في هذا التثبيت'),
 ('ui.on-this-install.ca75d54e64','fr'):('refinement','Dans cette installation'),
 ('ui.on-this-install.ca75d54e64','hi'):('refinement','इस इंस्टॉलेशन पर'),
 ('ui.on-this-install.ca75d54e64','ko'):('correction','이 설치에서'),
 ('ui.on-this-install.ca75d54e64','vi'):('refinement','Trong bản cài đặt này'),
 ('ui.on-this-install.ca75d54e64','zh-Hans'):('refinement','在此安装中'),
 ('ui.on-this-install.ca75d54e64','zh-Hant'):('refinement','在此安裝中'),
 ('ui.open-the-submission.4a863bf1dd','fr'):('correction','Ouvrir la soumission'),
 ('ui.openxbl-api-key.90ea47aa7f','zh-Hans'):('refinement','OpenXBL API 密钥'),
 ('ui.openxbl-api-key.90ea47aa7f','zh-Hant'):('refinement','OpenXBL API 金鑰'),
}
EXTRA={'ui.one-title-per-line-comments-ranking.8c54c86102':['#','→tab←'],'ui.openxbl-api-key.90ea47aa7f':['OpenXBL'],'ui.optional-apprise-urls-to-notify-one.8ef42d4f02':['Apprise']}
def sha(v):
 if isinstance(v,str): v=v.encode('utf-8')
 return hashlib.sha256(v).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def rj(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def key(r): return (r['sourceId'],r['locale'])
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def verify_dir(root):
 root=pathlib.Path(root); sums=root/'SHA256SUMS.txt'; entries={}
 for line in sums.read_text(encoding='utf-8').splitlines():
  if not line: continue
  digest,name=line.split('  ',1); p=(root/name).resolve()
  if name in entries or not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=digest: raise SystemExit('checksum failure: '+str(root/name))
  entries[name]=digest
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sums}
 if actual!=set(entries): raise SystemExit('checksum inventory mismatch: '+str(root))
 m=root/'manifest.json'
 if not m.is_file() and (root/'input/manifest.json').is_file(): m=root/'input/manifest.json'
 if not m.is_file() and (root/'summary.json').is_file(): m=root/'summary.json'
 return {'path':str(root),'checksumListSha256':sha(sums.read_bytes()),'manifestSha256':sha(m.read_bytes()),'fileCount':len(entries)}
def token_evidence(source,target,row):
 ph=lambda s:collections.Counter(re.findall(r'\{[^{}]+\}',s))
 tags=lambda s:collections.Counter(re.findall(r'<[^>]+>',s))
 nums=lambda s:collections.Counter([''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in x) for x in re.findall(r'\d+',s)])
 source_nums,target_nums=nums(source),nums(target); protected=list(row.get('sourceProtectedLiterals',[])); additional=EXTRA.get(row['sourceId'],[])
 missing=[x for x in protected+additional if x not in target]
 return {'placeholderMultisetMatches':ph(source)==ph(target),'markupMatches':tags(source)==tags(target),'numericTokensPreserved':not bool(source_nums-target_nums),'sourceNumericTokens':list(source_nums.elements()),'selectedNumericTokens':list(target_nums.elements()),'sourceProtectedLiterals':protected,'additionalProtectedLiterals':additional,'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing}
def main():
 cfpin=verify_dir(CF); inpin=verify_dir(INPUT); ppin=verify_dir(PRIMARY); opin=verify_dir(OUT)
 if git('rev-parse','HEAD')!=HEAD or git('rev-parse','HEAD^{tree}')!=TREE or git('status','--porcelain=v1','--untracked-files=all'): raise SystemExit('worktree pin/clean failure')
 pins=rj(OUT/'input-pins.json'); summary=rj(OUT/'summary.json'); manifest=rj(OUT/'manifest.json')
 if (pins.get('head'),pins.get('tree'),pins.get('window'))!=(HEAD,TREE,WINDOW): raise SystemExit('output pin mismatch')
 for name,pin in [('candidateFree',cfpin),('candidateFreeInput',inpin),('primaryReview',ppin)]:
  q=pins.get(name,{})
  if (q.get('checksumListSha256'),q.get('manifestSha256'))!=(pin['checksumListSha256'],pin['manifestSha256']): raise SystemExit('input checksum binding mismatch: '+name)
 if (OUT/'candidate-free-SHA256SUMS.txt').read_bytes()!=(CF/'SHA256SUMS.txt').read_bytes() or (OUT/'candidate-free-input-SHA256SUMS.txt').read_bytes()!=(INPUT/'SHA256SUMS.txt').read_bytes() or (OUT/'primary-SHA256SUMS.txt').read_bytes()!=(PRIMARY/'SHA256SUMS.txt').read_bytes(): raise SystemExit('copied checksum inventory mismatch')
 cm=rj(INPUT/'manifest.json'); ps=rj(PRIMARY/'summary.json'); pm=rj(PRIMARY/'manifest.json')
 if any(x.get('head')!=HEAD or x.get('tree')!=TREE for x in (cm,ps,pm)): raise SystemExit('input head/tree mismatch')
 if (cm.get('window'),cm.get('cellCount'),cm.get('callerBackedCells'),cm.get('callerlessHashOnlyCells'),cm.get('priorActiveHoldsReattested'),cm.get('newWindowHashOnlyHolds'))!=(WINDOW,240,216,24,988,24): raise SystemExit('candidate-free count mismatch')
 if ps.get('decisionCounts')!={'accept-current':206,'correction':3,'refinement':7,'hold-callerless-hash-only':24}: raise SystemExit('primary count mismatch')
 if (summary.get('result'),summary.get('head'),summary.get('tree'),summary.get('window'),summary.get('cells'))!=('PASS',HEAD,TREE,WINDOW,240): raise SystemExit('cross summary pin mismatch')
 if (manifest.get('head'),manifest.get('tree'),manifest.get('window'),manifest.get('cellCount'))!=(HEAD,TREE,WINDOW,240): raise SystemExit('output manifest pin mismatch')
 for name,digest in manifest.get('files',{}).items():
  p=OUT/name
  if not p.is_file() or sha(p.read_bytes())!=digest: raise SystemExit('output manifest file hash mismatch: '+name)
 actual={p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')}
 if actual!=set(manifest.get('files',{})): raise SystemExit('output manifest inventory mismatch')

 cells=rjl(INPUT/'candidate-free-cells.jsonl'); contexts=rjl(INPUT/'source-contexts.jsonl'); primary=rjl(PRIMARY/'ledger.jsonl'); proposals=rjl(PRIMARY/'proposals.jsonl'); pholds=rjl(PRIMARY/'holds.jsonl')
 cross=rjl(OUT/'cross-ledger.jsonl'); changes=rjl(OUT/'selected-changes.jsonl'); prior=rjl(OUT/'prior-active-holds-hash-only.jsonl'); current=rjl(OUT/'current-window-holds-hash-only.jsonl'); pinned_contexts=rjl(OUT/'caller-contexts-pinned.jsonl')
 if (len(cells),len(contexts),len(primary),len(proposals),len(pholds),len(cross),len(changes),len(prior),len(current))!=(240,20,240,10,24,240,10,988,24): raise SystemExit('row count mismatch')
 if (OUT/'caller-contexts-pinned.jsonl').read_bytes()!=(INPUT/'source-contexts.jsonl').read_bytes(): raise SystemExit('caller context copy mismatch')
 if [(x['catalogZeroBasedIndex'],x['locale']) for x in cells] != [(i,l) for i in range(765,785) for l in LOCALES]: raise SystemExit('candidate-free order mismatch')
 maps=[{key(x):x for x in rs} for rs in (cells,primary,cross)]
 if any(len(m)!=240 for m in maps) or not all(maps[0].keys()==m.keys() for m in maps[1:]): raise SystemExit('cell identity mismatch')
 pmap={key(x):x for x in proposals}; holdmap={key(x):x for x in pholds}; change_map={key(x):x for x in changes}
 contexts_by_source={x['sourceId']:x for x in contexts}; refs=0
 for sid,c in contexts_by_source.items():
  if c.get('head')!=HEAD or c.get('tree') not in (None,TREE): raise SystemExit('caller context pin mismatch: '+sid)
  if c.get('callerless'):
   if c.get('callers') not in (None,[]) or 'source' in c or c.get('sourceTextOmitted') is not True: raise SystemExit('callerless context text leak: '+sid)
   continue
  for caller in c.get('callers',[]):
   raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{HEAD}:{caller["path"]}'])
   if sha(raw)!=caller['fileSha256'] or git('rev-parse',f'{HEAD}:{caller["path"]}')!=caller['gitBlob']: raise SystemExit('caller file pin mismatch: '+caller['path'])
   lines=raw.decode('utf-8').splitlines()
   if lines[caller['line']-1]!=caller['lineText']: raise SystemExit('caller line mismatch: '+caller['path'])
   for e in caller['excerpt']:
    if lines[e['line']-1]!=e['text']: raise SystemExit('caller excerpt mismatch: '+caller['path'])
   refs+=1
 if refs!=summary.get('callerReferences') or refs!=cm.get('directCallerReferences'): raise SystemExit('caller reference count mismatch')

 counts=collections.Counter(); action=collections.Counter(); token_failures=0
 for c in cells:
  k=key(c); p=maps[1][k]; x=maps[2][k]; cid=f'{c["sourceId"]}::{c["locale"]}'
  for field in ('sourceId','locale','sourceSha256','currentTargetSha256','callerContextSha256','callerless','catalogZeroBasedIndex','catalogOneBasedPosition','position'):
   if c.get(field)!=p.get(field) or c.get(field)!=x.get(field): raise SystemExit(f'cell binding mismatch {cid} {field}')
  if x.get('candidateFreeRecordSha256')!=sha(canon(c)) or x.get('primaryRecordSha256')!=sha(canon(p)): raise SystemExit('record hash binding mismatch: '+cid)
  if c.get('callerless'):
   h=holdmap.get(k)
   if not h or p.get('decision')!='hold-callerless-hash-only' or x.get('crossDisposition')!='hold-callerless-hash-only': raise SystemExit('callerless hold decision mismatch: '+cid)
   if any(field in row for row in (c,p,h,x) for field in ('source','currentTarget','proposedTarget','selectedTarget','primaryProposal','crossRationale')): raise SystemExit('callerless text leak: '+cid)
   if not x.get('sourceTextOmitted') or not x.get('targetTextOmitted') or x.get('confidence')!='unknown': raise SystemExit('callerless omission flags mismatch: '+cid)
   if x.get('primaryDecision')!='hold-callerless-hash-only' or x.get('primaryRecordSha256')!=sha(canon(p)): raise SystemExit('callerless ledger binding mismatch: '+cid)
   if k in pmap or k in change_map: raise SystemExit('callerless proposal/change present: '+cid)
   counts['hold-callerless-hash-only']+=1; action['hold-callerless-hash-only|hold-callerless-hash-only']+=1
   continue
  if 'source' not in c or 'currentTarget' not in c or c.get('sourceSha256')!=sha(c['source']) or c.get('currentTargetSha256')!=sha(c['currentTarget']): raise SystemExit('candidate-free text/hash mismatch: '+cid)
  if p.get('source')!=c['source'] or p.get('currentTarget')!=c['currentTarget'] or x.get('source')!=c['source'] or x.get('currentTarget')!=c['currentTarget']: raise SystemExit('caller-backed text mismatch: '+cid)
  if c.get('callerContextSha256')!=contexts_by_source[c['sourceId']].get('contextSha256'): raise SystemExit('caller context hash mismatch: '+cid)
  caller_expected=[{'file':q['path'],'line':q['line'],'lineSha256':q['lineSha256'],'excerptSha256':q['excerptSha256'],'matchKind':q['matchKind']} for q in contexts_by_source[c['sourceId']].get('callers',[])]
  if x.get('callerEvidence')!=caller_expected or x.get('callerCount')!=c.get('literalCallerCount'): raise SystemExit('ledger caller evidence mismatch: '+cid)
  current_ev=token_evidence(c['source'],c['currentTarget'],c)
  if not all(current_ev[k2] for k2 in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')): raise SystemExit('candidate current token failure: '+cid)
  proposal=pmap.get(k)
  expected=EXPECTED.get(k)
  if expected:
   decision,target=expected
   if not proposal or proposal.get('decision')!=decision or proposal.get('proposedTarget')!=target or proposal.get('proposedTargetSha256')!=sha(target): raise SystemExit('expected proposal missing/mismatched: '+cid)
   if p.get('decision')!=decision or x.get('crossDisposition')!=decision or x.get('selectedFrom')!='primary' or x.get('selectedTarget')!=target: raise SystemExit('proposal cross decision mismatch: '+cid)
   if x.get('primaryProposal')!=target or x.get('primaryProposalSha256')!=sha(target): raise SystemExit('proposal ledger mismatch: '+cid)
   if k not in change_map or change_map[k].get('selectedTarget')!=target or change_map[k].get('crossDisposition')!=decision: raise SystemExit('selected changes file mismatch: '+cid)
   token_target=target
  else:
   if proposal is not None or p.get('decision')!='accept-current' or x.get('crossDisposition')!='accept-current' or x.get('selectedFrom')!='current' or x.get('selectedTarget')!=c['currentTarget']: raise SystemExit('current acceptance mismatch: '+cid)
   if x.get('primaryProposal') is not None or k in change_map: raise SystemExit('unexpected proposal or selected change: '+cid)
   token_target=c['currentTarget']
  if x.get('selectedTargetSha256')!=sha(token_target): raise SystemExit('selected target hash mismatch: '+cid)
  ev=token_evidence(c['source'],token_target,c)
  if x.get('tokenEvidence')!=ev or not all(ev[k2] for k2 in ('placeholderMultisetMatches','markupMatches','numericTokensPreserved','protectedLiteralsPreserved')): token_failures+=1
  if not x.get('nativeSpeakerApproval') is False or x.get('confidence')!='moderate' or not x.get('reviewOnly'): raise SystemExit('review qualification mismatch: '+cid)
  counts[x['crossDisposition']]+=1; action[f'{p["decision"]}|{x["crossDisposition"]}']+=1
 if token_failures: raise SystemExit('selected target token failures: '+str(token_failures))
 if {key(x) for x in changes}!=set(EXPECTED): raise SystemExit('selected change set mismatch')
 expected_counts=collections.Counter({'accept-current':206,'correction':3,'refinement':7,'hold-callerless-hash-only':24})
 if counts!=expected_counts or summary.get('crossDispositionCounts')!=dict(counts): raise SystemExit('cross disposition counts mismatch')
 expected_action=collections.Counter({'accept-current|accept-current':206,'correction|correction':3,'refinement|refinement':7,'hold-callerless-hash-only|hold-callerless-hash-only':24})
 if action!=expected_action or summary.get('primaryCrossActionTable')!=dict(action): raise SystemExit('action table mismatch')
 prior_input=rjl(INPUT/'prior-hold-reattestation.jsonl')
 if prior!=prior_input or len(prior)!=988 or any(any(f in r for f in ('source','sourceText','currentTarget','target','targetText','proposedTarget')) for r in prior): raise SystemExit('prior hold chain mismatch/text leak')
 if any(any(f in r for f in ('source','sourceText','currentTarget','target','targetText','proposedTarget')) for r in current): raise SystemExit('current hold text leak')
 if len(current)!=24 or summary.get('priorActiveHoldsPreservedHashOnly')!=988 or summary.get('newCallerlessHoldsHashOnly')!=24 or summary.get('resultingActiveHashOnlyHolds')!=1012: raise SystemExit('active hold counts mismatch')
 boundary={'continuationIndex':785,'oneBasedPosition':786,'sourceId':'ui.optional-overrides-the-webhook-s-dis.4116a5e8e4','sourceSha256':'4116a5e8e4222045299ae89f3577810da389c5c65f51cf8a3b097ecf05ef348e'}
 if summary.get('nextBoundary')!=boundary or manifest.get('nextBoundary')!=boundary: raise SystemExit('next boundary mismatch')
 if summary.get('selectedTokenFailures')!=0 or summary.get('primaryProposalsAccepted')!=10 or summary.get('nativeSpeakerReviewPerformed') is not False: raise SystemExit('summary evidence mismatch')
 print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'window':WINDOW,'cells':len(cross),'crossDispositionCounts':dict(counts),'primaryProposalsAdjudicated':len(changes),'callerReferencesVerified':refs,'priorActiveHolds':len(prior),'currentHashOnlyHolds':len(current),'resultingActiveHolds':len(prior)+len(current),'selectedTokenFailures':token_failures,'nextBoundary':boundary,'outputFilesVerified':opin['fileCount'],'checksumListSha256':opin['checksumListSha256']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
