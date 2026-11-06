#!/usr/bin/env python3
from __future__ import annotations
import collections,hashlib,json,pathlib,re,sys
OUT=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-integrated-cross-review-20261105')
CF=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105/candidate-free')
CFI=CF/'input'; PRI=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105/primary-review')
BLIND=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-independent-blind-20261105/blind-review')
PRIOR=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-third-party-cross-review-20261105')
HEAD='9714d7cf69c687685b4f65cbd9627a56830bab85'; TREE='c8eb66573f10b2390a02df05033f5133425d5e41'
MANUAL={
 'ui.one-title-per-line-comments-ranking.8c54c86102':['# comments','Title\u00a0→tab←\u00a0platform'],
 'ui.openxbl-api-key.90ea47aa7f':['OpenXBL','API'],
 'ui.optional-apprise-urls-to-notify-one.8ef42d4f02':['Apprise','URLs'],
}
MANUAL_CURRENT_CORRECTION_KEYS={('ui.one-title-per-line-comments-ranking.8c54c86102',l) for l in ['ar','de','es','fr','id','ja','pt-BR','vi','zh-Hans','zh-Hant']}
MANUAL_CURRENT_CORRECTION_KEYS|={('ui.optional-apprise-urls-to-notify-one.8ef42d4f02',l) for l in ['ar','es','fr','hi','id','ja','ko','vi','zh-Hans','zh-Hant']}
def sha(v):
 if isinstance(v,str):v=v.encode('utf-8')
 return hashlib.sha256(v).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def load(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def rows(p):return [json.loads(x) for x in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def key(x):return (x.get('sourceId'),x.get('locale'))
def verify_dir(root):
 root=pathlib.Path(root); sums=root/'SHA256SUMS.txt'; listed={}
 for line in sums.read_text(encoding='utf-8').splitlines():
  if not line:continue
  digest,name=line.split('  ',1); p=(root/name).resolve()
  if name in listed or not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=digest:raise SystemExit('checksum failure '+str(root/name))
  listed[name]=digest
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sums}
 if actual!=set(listed):raise SystemExit('checksum inventory mismatch '+str(root))
 mp=root/'manifest.json'
 return {'path':str(root),'checksumListSha256':sha(sums.read_bytes()),'manifestSha256':sha(mp.read_bytes()) if mp.is_file() else None,'fileCount':len(listed)}
def token_audit(src,tgt,row,manual):
 required=collections.Counter(row.get('sourceProtectedLiterals') or []); required.update({t for t in manual if t not in required})
 nums=lambda s:collections.Counter(re.findall(r'\d+',s))
 ph=lambda s:collections.Counter(re.findall(r'\{[^{}]+\}',s))
 tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
 bad={t:{'want':n,'got':tgt.count(t)} for t,n in required.items() if tgt.count(t)!=n}
 return not bad and not bool(nums(src)-nums(tgt)) and ph(src)==ph(tgt) and tags(src)==tags(tgt)
def main():
 out_pin=verify_dir(OUT)
 cf_outer=verify_dir(CF); cf_inner=verify_dir(CFI); pri=verify_dir(PRI); blind=verify_dir(BLIND); prior=verify_dir(PRIOR)
 pins=load(OUT/'input-pins.json'); manifest=load(OUT/'manifest.json'); summary=load(OUT/'summary.json')
 if (manifest.get('head'),manifest.get('tree'),manifest.get('cellCount'),manifest.get('callerReferenceCount'))!=(HEAD,TREE,240,23):raise SystemExit('output manifest pin/count failure')
 if (pins.get('head'),pins.get('tree'))!=(HEAD,TREE):raise SystemExit('output input pin mismatch')
 for n,actual in [('candidateFree',cf_outer),('candidateFreeInner',cf_inner),('primary',pri),('independentBlind',blind),('priorCrossAuditOnly',prior)]:
  src=pins.get(n,{})
  if (src.get('checksumListSha256'),src.get('fileCount'),src.get('manifestSha256'))!=(actual['checksumListSha256'],actual['fileCount'],actual.get('manifestSha256')):raise SystemExit('input checksum binding mismatch '+n)
 cm=load(CFI/'manifest.json'); ps=load(PRI/'summary.json'); bs=load(BLIND/'review-summary.json')
 if sha((OUT/'candidate-free-manifest.json').read_bytes())!=sha((CFI/'manifest.json').read_bytes()):raise SystemExit('candidate-free manifest copy mismatch')
 copies={
  'candidate-free-SHA256SUMS.txt':CF/'SHA256SUMS.txt','candidate-free-input-SHA256SUMS.txt':CFI/'SHA256SUMS.txt',
  'candidate-free-cells.jsonl':CFI/'candidate-free-cells.jsonl','candidate-free-source-contexts.jsonl':CFI/'source-contexts.jsonl',
  'primary-SHA256SUMS.txt':PRI/'SHA256SUMS.txt','primary-ledger.jsonl':PRI/'ledger.jsonl','primary-proposals.jsonl':PRI/'proposals.jsonl','primary-holds-hash-only.jsonl':PRI/'holds.jsonl',
  'blind-SHA256SUMS.txt':BLIND/'SHA256SUMS.txt','blind-locale-review.jsonl':BLIND/'blind-locale-review.jsonl','blind-dispositions.jsonl':BLIND/'dispositions.jsonl',
  'blind-current-window-holds-hash-only.jsonl':BLIND/'current-window-holds.jsonl','blind-prior-active-holds-hash-only.jsonl':BLIND/'prior-hold-lineage.jsonl',
  'prior-cross-SHA256SUMS.txt':PRIOR/'SHA256SUMS.txt','prior-cross-ledger-audit-only.jsonl':PRIOR/'cross-ledger.jsonl','prior-cross-selected-changes-audit-only.jsonl':PRIOR/'selected-changes.jsonl'}
 for n,src in copies.items():
  if (OUT/n).read_bytes()!=src.read_bytes():raise SystemExit('copied input mismatch '+n)
 if (cm.get('head'),cm.get('tree'),cm.get('cellCount'),cm.get('callerBackedCells'),cm.get('callerlessHashOnlyCells'))!=(HEAD,TREE,240,216,24):raise SystemExit('candidate-free source pin/count failure')
 if (ps.get('head'),ps.get('tree'),ps.get('cellCount'))!=(HEAD,TREE,240):raise SystemExit('primary pin/count failure')
 if (bs.get('head'),bs.get('tree'),bs.get('cellCount'),bs.get('callerReferences'))!=(HEAD,TREE,240,23):raise SystemExit('blind pin/count failure')
 cf=rows(OUT/'candidate-free-cells.jsonl'); pl=rows(OUT/'primary-ledger.jsonl'); props=rows(OUT/'primary-proposals.jsonl'); holds=rows(OUT/'primary-holds-hash-only.jsonl')
 br=rows(OUT/'blind-locale-review.jsonl'); bd=rows(OUT/'blind-dispositions.jsonl'); bh=rows(OUT/'blind-current-window-holds-hash-only.jsonl')
 cross=rows(OUT/'integrated-cross-ledger.jsonl'); old=rows(OUT/'prior-cross-ledger-audit-only.jsonl'); oldsel=rows(OUT/'prior-cross-selected-changes-audit-only.jsonl')
 ctx=rows(OUT/'candidate-free-source-contexts.jsonl'); priorholds=rows(OUT/'candidate-free-prior-active-holds-hash-only.jsonl'); bprior=rows(OUT/'blind-prior-active-holds-hash-only.jsonl')
 if (len(cf),len(pl),len(props),len(holds),len(br),len(bd),len(bh),len(cross),len(ctx),len(priorholds),len(bprior),len(old),len(oldsel))!=(240,240,10,24,216,240,24,240,20,988,988,240,10):raise SystemExit('row count mismatch')
 if (OUT/'candidate-free-source-contexts.jsonl').read_bytes()!=(CFI/'source-contexts.jsonl').read_bytes():raise SystemExit('caller evidence copy mismatch')
 if (OUT/'candidate-free-prior-active-holds-hash-only.jsonl').read_bytes()!=(BLIND/'prior-hold-lineage.jsonl').read_bytes():raise SystemExit('prior hold hash lineage mismatch')
 maps=lambda xs:{key(x):x for x in xs}
 cfm,plm,prm,hm,brm,bdm,crossm,oldm,oldsm=map(maps,(cf,pl,props,holds,br,bd,cross,old,oldsel))
 if set(hm)!=set(maps(bh)):raise SystemExit('primary and blind current hold identity mismatch')
 if any(len(m)!=want for m,want in ((cfm,240),(plm,240),(prm,10),(hm,24),(brm,216),(bdm,240),(crossm,240),(oldm,240),(oldsm,10))):raise SystemExit('duplicate cell key')
 if cfm.keys()!=plm.keys() or cfm.keys()!=bdm.keys() or cfm.keys()!=crossm.keys() or cfm.keys()!=oldm.keys():raise SystemExit('cell coverage mismatch')
 if [(r['sourceId'],r['locale']) for r in cross]!=[(r['sourceId'],r['locale']) for r in cf]:raise SystemExit('cross ledger order differs from candidate-free order')
 ctxm={r['sourceId']:r for r in ctx}
 caller_count=sum(len(x.get('callers',[])) for x in ctx)
 if len(ctxm)!=20 or caller_count!=23:raise SystemExit('source/caller reference count mismatch')
 for x in ctx:
  if x.get('head')!=HEAD:raise SystemExit('caller source head mismatch')
 for k,b in brm.items():
  c=cfm[k]; context=ctxm[k[0]]
  if b.get('sourceContextSha256')!=context.get('contextSha256') or b.get('sourceSha256')!=c.get('sourceSha256') or c.get('callerContextSha256')!=context.get('contextSha256'):raise SystemExit('blind caller/source pin mismatch '+str(k))
  proj=[{f:r.get(f) for f in ('excerptSha256','fileSha256','gitBlob','line','lineSha256','lineText','matchKind','path')} for r in context.get('callers',[])]
  if b.get('callerReferences')!=proj:raise SystemExit('blind caller-reference mismatch '+str(k))
 counts=collections.Counter(); token_fail=collections.Counter(); agreement=0; quality=0; changed=0
 for c in cf:
  k=key(c); p=plm[k]; d=bdm[k]; x=crossm[k]; oldrow=oldm[k]
  if x.get('candidateFreeRecordSha256')!=sha(canon(c)) or x.get('primaryRecordSha256')!=sha(canon(p)) or x.get('blindDispositionRecordSha256')!=sha(canon(d)):raise SystemExit('record binding mismatch '+str(k))
  if x.get('exactTargetSelected') is not False or x.get('catalogValueApplied') is not False:raise SystemExit('target selected/applied '+str(k))
  if any(n in x for n in ('selectedTarget','chosenTarget','recommendedTarget','rootSelectedTarget')):raise SystemExit('selection field present '+str(k))
  if x.get('crossDisposition')!=oldrow.get('crossDisposition'):changed+=1
  if c.get('callerless'):
   counts['hold-callerless-hash-only']+=1
   if x.get('crossDisposition')!='hold-callerless-hash-only' or any(n in x for n in ('source','currentTarget','primaryProposal','blindProposal')):raise SystemExit('callerless output is not text-free '+str(k))
   if c.get('currentTarget') is not None or not c.get('currentTargetTextOmitted') or x.get('currentTargetSha256')!=c.get('currentTargetSha256'):raise SystemExit('callerless source target hash mismatch '+str(k))
   h=hm[k]
   if d.get('textOmitted') is not True or p.get('currentTargetTextOmitted') is not True:raise SystemExit('callerless input text leak '+str(k))
   if h.get('currentTargetSha256')!=c.get('currentTargetSha256') or h.get('sourceSha256')!=c.get('sourceSha256') or x.get('sourceSha256')!=c.get('sourceSha256'):raise SystemExit('callerless hold hash mismatch '+str(k))
   continue
  src=c.get('source'); cur=c.get('currentTarget'); blind_text=d.get('proposal')
  if x.get('source')!=src or x.get('currentTarget')!=cur or x.get('blindProposal')!=blind_text:raise SystemExit('text binding mismatch '+str(k))
  if sha(src)!=c.get('sourceSha256') or sha(cur)!=c.get('currentTargetSha256') or d.get('proposalSha256')!=sha(blind_text):raise SystemExit('cell hash mismatch '+str(k))
  if p.get('source')!=src or p.get('sourceSha256')!=c.get('sourceSha256') or p.get('currentTargetSha256')!=c.get('currentTargetSha256'):raise SystemExit('primary source/current bind mismatch '+str(k))
  manual=MANUAL.get(k[0],[])
  cur_ok=token_audit(src,cur,c,manual)
  blind_ok=token_audit(src,blind_text,c,manual)
  if not cur_ok:token_fail['current']+=1
  if not blind_ok:token_fail['blind']+=1
  pp=prm.get(k); target=pp.get('proposedTarget') if pp else None
  pri_ok=(target is None or token_audit(src,target,c,manual))
  if target is not None and not pri_ok:token_fail['primary']+=1
  if (not cur_ok and k not in MANUAL_CURRENT_CORRECTION_KEYS) or not blind_ok or not pri_ok:raise SystemExit('unexpected token failure '+str(k))
  if (not cur_ok)!=(k in MANUAL_CURRENT_CORRECTION_KEYS):raise SystemExit('manual literal mismatch set differs '+str(k))
  if x.get('currentTokenAudit',{}).get('pass')!=cur_ok or x.get('blindProposalTokenAudit',{}).get('pass')!=blind_ok or (target is not None and x.get('primaryProposalTokenAudit',{}).get('pass')!=pri_ok):raise SystemExit('cross token audit binding mismatch '+str(k))
  if pp:
   if pp.get('proposedTargetSha256')!=sha(target) or x.get('primaryProposal')!=target or x.get('primaryProposalSha256')!=sha(target):raise SystemExit('primary proposal hash mismatch '+str(k))
   if target==blind_text:agreement+=1
   if x.get('crossDisposition')!=p.get('decision') or x.get('crossDisposition') not in ('correction','refinement') or x.get('rootSelectionChangeRequired') is not False:raise SystemExit('primary proposal disposition mismatch '+str(k))
  elif k in MANUAL_CURRENT_CORRECTION_KEYS:
   if p.get('decision')!='accept-current' or x.get('crossDisposition')!='correction' or x.get('rootSelectionChangeRequired') is not True:raise SystemExit('manual-literal correction advice missing '+str(k))
  elif p.get('decision')!='accept-current' or x.get('crossDisposition')!='accept-current' or x.get('rootSelectionChangeRequired') is not False:raise SystemExit('accept-current mismatch '+str(k))
  if k==('ui.optional-connections-to-the-rest-of.636208f858','fr'):
   if not x.get('blindAlternativeFinding') or 'facultative' not in x['blindAlternativeFinding']:raise SystemExit('blind French agreement finding missing')
   quality+=1
  elif x.get('blindAlternativeFinding') is not None:raise SystemExit('unexpected blind quality finding '+str(k))
  counts[x['crossDisposition']]+=1
 if counts!=collections.Counter({'accept-current':186,'correction':23,'refinement':7,'hold-callerless-hash-only':24}):raise SystemExit('disposition count mismatch '+str(counts))
 if agreement!=6 or quality!=1 or changed!=20 or token_fail!=collections.Counter({'current':20}):raise SystemExit('reconciliation summary mismatch')
 advisories=rows(OUT/'root-change-advisories.jsonl')
 if len(advisories)!=20 or { (r['sourceId'],r['locale']) for r in advisories }!=MANUAL_CURRENT_CORRECTION_KEYS:raise SystemExit('root-change advisory coverage mismatch')
 # Prior cross ledger is a comparison-only audit; its selected values must agree with the ten proposal rows.
 for k,s in oldsm.items():
  p=prm[k]
  if s.get('selectedTarget')!=p.get('proposedTarget'):raise SystemExit('prior cross audit selected-value difference '+str(k))
 if summary.get('changedRootSelectionsRequired')!=20 or summary.get('priorCrossAuditDispositionDifferences')!=20 or summary.get('currentManualLiteralMismatchCells')!=20 or summary.get('crossDispositionCounts')!=dict(counts):raise SystemExit('summary root-change audit mismatch')
 for a in advisories:
  k=(a['sourceId'],a['locale']); row=crossm[k]
  blindrow=brm[k]
  if a.get('currentTarget')!=row.get('currentTarget') or a.get('currentTargetSha256')!=row.get('currentTargetSha256') or a.get('blindProposal')!=row.get('blindProposal') or a.get('blindProposalSha256')!=row.get('blindProposalSha256'):raise SystemExit('root-change advisory values/hashes mismatch '+str(k))
  if a.get('pinnedManualLiterals')!=blindrow.get('manualProtectedLiteralsRequired',[]) or a.get('currentManualLiteralFailures')!=row.get('currentTokenAudit',{}).get('protectedLiteralFailures') or a.get('blindProposalTokenPass') is not True:raise SystemExit('root-change advisory manual-literal evidence mismatch '+str(k))
  if a.get('exactTargetSelected') is not False or a.get('catalogValueApplied') is not False:raise SystemExit('root-change advisory selection state mismatch '+str(k))
 print(json.dumps({'result':'PASS_STATIC_PACKET_RECONCILIATION','head':HEAD,'tree':TREE,'cells':240,'callerReferences':23,'dispositions':dict(counts),'primaryProposalBlindExactTextAgreement':agreement,'blindAlternativeQualityFindings':quality,'currentManualLiteralMismatchCells':token_fail.get('current',0),'proposalTokenFailures':{'primary':token_fail.get('primary',0),'blind':token_fail.get('blind',0)},'priorCrossDecisionDifferences':changed,'rootChangesRequired':len(advisories),'exactTargetSelected':False,'catalogValueApplied':False,'worktreeSourceContentRead':False,'outputChecksumListSha256':out_pin['checksumListSha256']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
