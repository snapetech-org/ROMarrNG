#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, pathlib, re, shutil

OUT = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-integrated-cross-review-20261105')
CF = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105/candidate-free')
CFI = CF / 'input'
PRI = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105/primary-review')
BLIND = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-independent-blind-20261105/blind-review')
PRIOR = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-third-party-cross-review-20261105')
HEAD = '9714d7cf69c687685b4f65cbd9627a56830bab85'
TREE = 'c8eb66573f10b2390a02df05033f5133425d5e41'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

SPECIAL_NOTES = {
 ('ui.on-this-install.ca75d54e64','ar'): 'The current phrase means only “on this” and omits the software installation; primary and blind both repair it.',
 ('ui.on-this-install.ca75d54e64','fr'): 'This is a heading above route rows scoped to the running installation. The primary “Dans cette installation” fits that scope better than blind “Sur cette installation,” which repeats the current wording.',
 ('ui.on-this-install.ca75d54e64','hi'): 'The software-installation loanword is clearer than the broad/formal word for establishment while retaining the locative relation; primary and blind match.',
 ('ui.on-this-install.ca75d54e64','ko'): 'The current noun phrase omits the locative relation. Both drafts express “in this installation.”',
 ('ui.on-this-install.ca75d54e64','vi'): 'The route table is scoped within the running software installation. Primary “Trong” expresses that scope more naturally than blind/current “Trên.”',
 ('ui.on-this-install.ca75d54e64','zh-Hans'): 'Primary “在此安装中” expresses routes within this installation more directly than blind “此安装实例.”',
 ('ui.on-this-install.ca75d54e64','zh-Hant'): 'Primary “在此安裝中” expresses routes within this installation more directly than blind “此安裝版本,” which shifts toward an installation version.',
 ('ui.open-the-submission.4a863bf1dd','fr'): 'The caller links to the user’s submission for review and posting. “Proposition” means a proposal; primary and blind “soumission” match the linked object.',
 ('ui.openxbl-api-key.90ea47aa7f','zh-Hans'): 'The caller is a password credential field. 密钥 is the standard Simplified Chinese term for a secret/API key; primary and blind match.',
 ('ui.openxbl-api-key.90ea47aa7f','zh-Hant'): 'The caller is a password credential field. 金鑰 is the standard Traditional Chinese term for a secret/API key; primary and blind match.',
}
SOURCE_NOTES = {
 'ui.on-this-day.d011904834':'Games navigation tab for the date-based anniversary view; current labels express “on this day.”',
 'ui.one-game-one-rom.3372b0856c':'Checkbox in collection planning; the label conveys the one-game/one-ROM constraint and preserves ROM.',
 'ui.one-other-dump.6710e50b16':'Summary for exactly one discarded duplicate dump; singular translations preserve the count and object.',
 'ui.one-title-per-line-comments-ranking.8c54c86102':'Modal help for a parser; current and blind text retain the exact comment and title/tab/platform syntax examples.',
 'ui.only-dat-verified-dumps.a372d56f1d':'Peer-sharing scope option; DAT stays exact and the restriction stays limited to DAT-verified dumps.',
 'ui.only-selected-regions.e257690d2c':'Region allowlist checkbox; translations preserve the selected-regions restriction.',
 'ui.only-the-platforms-i-name.a25a55c6dd':'Peer-sharing scope option; translations preserve the first-person list of named platforms.',
 'ui.open-navigation.0ed77fd261':'Accessible label for the navigation toggle; translations describe opening navigation.',
 'ui.open-on-the-indexer.4766c56d0d':'Accessible link label for opening a release on its indexer.',
 'ui.open-on-indexer.202e1ad5f5':'Accessible link label with the {indexer} runtime placeholder preserved.',
 'ui.open-this-invitation-on-my-romarr.b76952fe51':'Invitation button opens the invite on the user’s own ROMarr; the product literal remains intact.',
 'ui.optional-connections-to-the-rest-of.636208f858':'General-settings paragraph: optional connections, credentials kept in the environment file, no secret shown or stored, separate indexer/download-client settings, and opt-in notification/metadata connections.',
 'ui.optional-follow-ups.e3fee9a99c':'Heading for optional follow-up steps in the collection workflow.',
 'ui.optional-message-priority.dbcf318711':'Notification field help says message priority is optional.',
 'ui.optional-apprise-urls-to-notify-one.8ef42d4f02':'Notification field help preserves Apprise and URLs and says one per line or comma-separated.',
}
MANUAL_LITERALS = {
 'ui.one-title-per-line-comments-ranking.8c54c86102':['# comments','Title\u00a0→tab←\u00a0platform'],
 'ui.openxbl-api-key.90ea47aa7f':['OpenXBL','API'],
 'ui.optional-apprise-urls-to-notify-one.8ef42d4f02':['Apprise','URLs'],
}
BLIND_QUALITY_ISSUES = {
 ('ui.optional-connections-to-the-rest-of.636208f858','fr'):
  'Blind-only alternative has a French agreement error: “Connexions facultative” should be “Connexions facultatives.” The pinned current French target uses the correct plural form; primary accepts current. Reject this blind variant if anyone selected it.'
}
MANUAL_CURRENT_CORRECTION_KEYS = {('ui.one-title-per-line-comments-ranking.8c54c86102',l) for l in ['ar','de','es','fr','id','ja','pt-BR','vi','zh-Hans','zh-Hant']}
MANUAL_CURRENT_CORRECTION_KEYS |= {('ui.optional-apprise-urls-to-notify-one.8ef42d4f02',l) for l in ['ar','es','fr','hi','id','ja','ko','vi','zh-Hans','zh-Hant']}
def manual_correction_note(key):
 if key[0]=='ui.one-title-per-line-comments-ranking.8c54c86102':
  extra=' Vietnamese also rewrites the exact “Title →tab← platform” format example; preserve that pinned syntax example too.' if key[1]=='vi' else ''
  return 'The current localized instruction paraphrases the parser comment example instead of preserving the manually pinned literal “# comments”; restore that exact syntax example in a correction.'+extra
 return 'The current target uses “URL” where the blind packet pins exact “URLs” as the source token. Preserve the exact plural acronym and the Apprise product name in a correction.'

def sha(v):
 if isinstance(v,str): v=v.encode('utf-8')
 return hashlib.sha256(v).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def load(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def rows(p): return [json.loads(line) for line in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if line.strip()]
def ident(r): return (r.get('sourceId'),r.get('locale'))
def verify_sum(root, sums_name='SHA256SUMS.txt'):
 root=pathlib.Path(root); sp=root/sums_name; found={}
 for line in sp.read_text(encoding='utf-8').splitlines():
  if not line: continue
  digest,name=line.split('  ',1)
  p=(root/name).resolve()
  if name in found or not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p.read_bytes())!=digest:
   raise SystemExit(f'checksum failure: {root/name}')
  found[name]=digest
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != sp}
 if actual != set(found): raise SystemExit(f'checksum inventory mismatch: {root}')
 return {'path':str(root),'checksumListSha256':sha(sp.read_bytes()),'manifestSha256':sha((root/'manifest.json').read_bytes()) if (root/'manifest.json').is_file() else None,'fileCount':len(found)}
def callers_projection(source_context):
 result=[]
 for c in source_context.get('callers',[]):
  result.append({k:c.get(k) for k in ('excerptSha256','fileSha256','gitBlob','line','lineSha256','lineText','matchKind','path')})
 return result
def token_audit(source,target,cfrow,manual):
 required=collections.Counter(cfrow.get('sourceProtectedLiterals') or [])
 required.update({t for t in manual if t not in required})
 source_nums=collections.Counter(re.findall(r'\d+',source))
 target_nums=collections.Counter(re.findall(r'\d+',target))
 source_ph=collections.Counter(re.findall(r'\{[^{}]+\}',source))
 target_ph=collections.Counter(re.findall(r'\{[^{}]+\}',target))
 tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
 missing={lit:n-target.count(lit) for lit,n in required.items() if target.count(lit)!=n}
 return {
  'requiredProtectedLiteralCounts':dict(required),
  'actualProtectedLiteralCounts':{lit:target.count(lit) for lit in required},
  'protectedLiteralFailures':missing,
  'sourceNumericTokens':dict(source_nums),'targetNumericTokens':dict(target_nums),
  'numericTokensPreserved':not bool(source_nums-target_nums),
  'sourcePlaceholderTokens':dict(source_ph),'targetPlaceholderTokens':dict(target_ph),
  'placeholdersPreserved':source_ph==target_ph,
  'markupPreserved':tags(source)==tags(target),
  'pass':not missing and not bool(source_nums-target_nums) and source_ph==target_ph and tags(source)==tags(target),
 }
def safe_text(r, field):
 return r.get(field) if not r.get('callerless') else None

def main():
 if not OUT.is_dir(): raise SystemExit('output directory missing')
 cf_outer=verify_sum(CF)
 cf_inner=verify_sum(CFI)
 pri_pin=verify_sum(PRI)
 blind_pin=verify_sum(BLIND)
 prior_pin=verify_sum(PRIOR)
 cm=load(CFI/'manifest.json'); ps=load(PRI/'summary.json'); pm=load(PRI/'manifest.json')
 bm=load(BLIND/'review-summary.json'); bpins=load(BLIND/'input-pins.json'); bta=load(BLIND/'token-audit.json')
 oldsum=load(PRIOR/'summary.json'); oldman=load(PRIOR/'manifest.json')
 for name,obj in [('candidate-free',cm),('primary',ps),('primary-manifest',pm),('blind',bm),('prior cross',oldsum)]:
  if obj.get('head',obj.get('review_head'))!=HEAD or obj.get('tree',obj.get('review_tree'))!=TREE: raise SystemExit(name+' pin mismatch')
 if (cm.get('cellCount'),cm.get('sourceCount'),cm.get('callerBackedCells'),cm.get('callerlessHashOnlyCells'),cm.get('priorActiveHoldsReattested'),cm.get('resultingActiveHashOnlyHolds'))!=(240,20,216,24,988,1012): raise SystemExit('candidate-free manifest count mismatch')
 if (ps.get('cellCount'),ps.get('callerBackedCells'),ps.get('callerlessHashOnlyCells'),ps.get('priorActiveHoldsReattested'),ps.get('newWindowHashOnlyHolds'),ps.get('resultingActiveHashOnlyHolds'))!=(240,216,24,988,24,1012): raise SystemExit('primary summary count mismatch')
 if (bm.get('cellCount'),bm.get('callerBackedCells'),bm.get('callerReferences'),bm.get('callerlessHashOnlyCells'),bm.get('priorActiveHolds'),bm.get('newHashOnlyHolds'),bm.get('resultingActiveHashOnlyHolds'))!=(240,216,23,24,988,24,1012): raise SystemExit('blind summary count mismatch')
 if (bta.get('proposalCells'),bta.get('checks'))!=(216,{'manualProtectedLiterals':0,'markup':0,'numbers':0,'placeholders':0,'protectedLiterals':0}): raise SystemExit('blind token audit summary mismatch')
 if bpins.get('head')!=HEAD or bpins.get('tree')!=TREE or bpins.get('candidateFreeManifestSha256')!=sha((CFI/'manifest.json').read_bytes()): raise SystemExit('blind input pin binding mismatch')
 if pm.get('candidateFreeManifestSha256')!=sha((CFI/'manifest.json').read_bytes()): raise SystemExit('primary candidate-free binding mismatch')

 cf=rows(CFI/'candidate-free-cells.jsonl'); pl=rows(PRI/'ledger.jsonl'); props=rows(PRI/'proposals.jsonl'); holds=rows(PRI/'holds.jsonl')
 br=rows(BLIND/'blind-locale-review.jsonl'); bd=rows(BLIND/'dispositions.jsonl'); bh=rows(BLIND/'current-window-holds.jsonl')
 contexts=rows(CFI/'source-contexts.jsonl'); prior_holds=rows(CFI/'prior-hold-reattestation.jsonl')
 oldledger=rows(PRIOR/'cross-ledger.jsonl'); oldchanges=rows(PRIOR/'selected-changes.jsonl')
 if (len(cf),len(pl),len(props),len(holds),len(br),len(bd),len(bh),len(contexts),len(prior_holds),len(oldledger),len(oldchanges))!=(240,240,10,24,216,240,24,20,988,240,10): raise SystemExit('input row count mismatch')
 if any(len(m)!=(len(pl) if m is not None else -1) for m in []): pass
 maps=lambda xs: {ident(x):x for x in xs}
 cfm,plm,prm,hm,brm,bdm,oldm=map(maps,(cf,pl,props,holds,br,bd,oldledger))
 if any(len(m)!=expected for m,expected in [(cfm,240),(plm,240),(prm,10),(hm,24),(brm,216),(bdm,240),(oldm,240)]): raise SystemExit('duplicate input identity')
 if cfm.keys()!=plm.keys() or cfm.keys()!=bdm.keys() or cfm.keys()!=oldm.keys(): raise SystemExit('cell coverage differs')
 ctxm={r['sourceId']:r for r in contexts}
 if len(ctxm)!=20: raise SystemExit('source context coverage mismatch')
 if any(r.get('head')!=HEAD for r in contexts): raise SystemExit('source context head mismatch')
 caller_refs=sum(len(r.get('callers',[])) for r in contexts)
 if caller_refs!=23: raise SystemExit('caller reference count mismatch')
 if sum(1 for r in contexts if r.get('callerless'))!=2: raise SystemExit('callerless source count mismatch')
 # The blind packet repeats every pinned caller reference; bind all 23 to candidate-free evidence.
 for source_id,ctx in ctxm.items():
  if ctx.get('sourceSha256') is None and not ctx.get('sourceTextOmitted'): raise SystemExit('missing context source hash '+source_id)
  for c in cf:
   if c['sourceId']==source_id and c.get('callerContextSha256')!=ctx.get('contextSha256'): raise SystemExit('candidate/context hash mismatch '+source_id)
 for key,b in brm.items():
  ctx=ctxm[key[0]]
  if b.get('sourceContextSha256')!=ctx.get('contextSha256') or b.get('callerReferences')!=callers_projection(ctx): raise SystemExit('blind caller reference binding mismatch '+str(key))
  if b.get('sourceSha256')!=ctx.get('sourceSha256'): raise SystemExit('blind source hash mismatch '+str(key))

 current_holds={ident(x):x for x in bh}
 primary_holds={ident(x):x for x in holds}
 if current_holds.keys()!=primary_holds.keys(): raise SystemExit('hash-only hold coverage differs')
 for key,h in current_holds.items():
  c=cfm[key]; p=plm[key]; d=bdm[key]
  if not c.get('callerless') or c.get('currentTarget') is not None or not c.get('currentTargetTextOmitted',False):
   raise SystemExit('candidate-free callerless cell includes text '+str(key))
  if h.get('currentTargetSha256')!=c.get('currentTargetSha256') or h.get('sourceSha256')!=c.get('sourceSha256'):
   raise SystemExit('current hold hash mismatch '+str(key))
  if p.get('currentTargetTextOmitted') is not True or p.get('decision')!='hold-callerless-hash-only': raise SystemExit('primary hold not hash-only '+str(key))
  if d.get('textOmitted') is not True or d.get('disposition')!='hold_hash_only': raise SystemExit('blind hold not hash-only '+str(key))

 previous_active_sha=sha((CFI/'prior-hold-reattestation.jsonl').read_bytes())
 if sha((BLIND/'prior-hold-lineage.jsonl').read_bytes())!=previous_active_sha: raise SystemExit('prior hold lineage differs between candidate-free and blind')
 # Bind the 10 primary proposal cells and verify exact text/hash plus token fidelity.
 if prm.keys()!={(r['sourceId'],r['locale']) for r in props}: raise SystemExit('primary proposal map mismatch')
 out=[]; counts=collections.Counter(); exact_agreement=0; blind_quality_count=0; token_failures=collections.Counter(); decision_changed=0
 for c in cf:
  key=ident(c); source_id,locale=key; p=plm[key]; d=bdm[key]; old=oldm[key]
  base={
   'cellId':f'{source_id}::{locale}','sourceId':source_id,'locale':locale,
   'position':c['position'],'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],
   'sourceSha256':c['sourceSha256'],'callerContextSha256':c['callerContextSha256'],
   'callerless':bool(c.get('callerless')),
   'candidateFreeRecordSha256':sha(canon(c)),
   'primaryRecordSha256':sha(canon(p)),
   'blindDispositionRecordSha256':sha(canon(d)),
   'primaryDecision':p['decision'],'blindDisposition':d['disposition'],
   'crossConfidence':'moderate','nativeSpeakerApproval':False,
   'exactTargetSelected':False,'catalogValueApplied':False,
   'priorCrossDisposition':old.get('crossDisposition'),
  }
  if c.get('callerless'):
   if d.get('proposal') is not None or c.get('source') is not None or c.get('currentTarget') is not None: raise SystemExit('callerless text leak '+str(key))
   base.update({'sourceTextOmitted':True,'currentTargetTextOmitted':True,'currentTargetSha256':c['currentTargetSha256'],
    'crossDisposition':'hold-callerless-hash-only','crossRationale':'No production caller is recorded at the pinned input. Keep source and target text omitted; retain only the cell hashes until caller context exists.'})
   counts['hold-callerless-hash-only']+=1
  else:
   source=c['source']; current=c['currentTarget']; blind=d.get('proposal')
   if source is None or current is None or blind is None: raise SystemExit('caller-backed text missing '+str(key))
   if sha(source)!=c['sourceSha256'] or sha(current)!=c['currentTargetSha256'] or d.get('proposalSha256')!=sha(blind): raise SystemExit('candidate/blind value hash mismatch '+str(key))
   if p.get('source')!=source or p.get('sourceSha256')!=c['sourceSha256'] or p.get('currentTargetSha256')!=c['currentTargetSha256']:
    raise SystemExit('primary source/current hash mismatch '+str(key))
   if brm[key].get('source')!=source or brm[key].get('sourceSha256')!=c['sourceSha256'] or d.get('sourceSha256')!=c['sourceSha256'] or brm[key].get('proposal')!=d.get('proposal'): raise SystemExit('blind source/proposal mismatch '+str(key))
   manual=MANUAL_LITERALS.get(source_id,[])
   cur_audit=token_audit(source,current,c,manual)
   blind_audit=token_audit(source,blind,c,manual)
   primary_proposal=prm.get(key)
   primary_target=primary_proposal.get('proposedTarget') if primary_proposal else None
   primary_audit=token_audit(source,primary_target,c,manual) if primary_target is not None else None
   if not cur_audit['pass']: token_failures['current']+=1
   if not blind_audit['pass']: token_failures['blind']+=1
   if primary_audit and not primary_audit['pass']: token_failures['primary']+=1
   if not cur_audit['pass'] and key not in MANUAL_CURRENT_CORRECTION_KEYS: raise SystemExit('unexpected current token mismatch '+str(key))
   if not blind_audit['pass'] or (primary_audit and not primary_audit['pass']): raise SystemExit('proposal token mismatch '+str(key))
   if (not cur_audit['pass']) != (key in MANUAL_CURRENT_CORRECTION_KEYS): raise SystemExit('expected manual-literal mismatch set differs '+str(key))
   if primary_proposal:
    if primary_proposal.get('sourceSha256')!=c['sourceSha256'] or primary_proposal.get('currentTargetSha256')!=c['currentTargetSha256'] or primary_proposal.get('proposedTargetSha256')!=sha(primary_target): raise SystemExit('primary proposal hash mismatch '+str(key))
    if primary_proposal.get('decision')!=p['decision']: raise SystemExit('primary proposal disposition mismatch '+str(key))
    if primary_target==blind: exact_agreement+=1
   else:
    if p.get('decision')!='accept-current': raise SystemExit('missing primary proposal on non-accept cell '+str(key))
   cross='correction' if key in MANUAL_CURRENT_CORRECTION_KEYS else p['decision']
   if cross not in ('accept-current','correction','refinement'): raise SystemExit('unexpected primary decision '+str(key))
   rationale=manual_correction_note(key) if key in MANUAL_CURRENT_CORRECTION_KEYS else SPECIAL_NOTES.get(key,SOURCE_NOTES.get(source_id,'Pinned caller context and source meaning support the current wording; the independent blind alternative is semantically adequate and token-safe.'))
   finding=BLIND_QUALITY_ISSUES.get(key)
   if finding: blind_quality_count+=1
   base.update({
    'source':source,'currentTarget':current,'currentTargetSha256':c['currentTargetSha256'],
    'primaryProposal':primary_target,'primaryProposalSha256':primary_proposal.get('proposedTargetSha256') if primary_proposal else None,
    'blindProposal':blind,'blindProposalSha256':d.get('proposalSha256'),
    'primaryBlindTextAgreement':('exact' if primary_target is not None and primary_target==blind else ('different-wording-primary-supported' if primary_target is not None else 'not-applicable-primary-accepts-current')),
    'crossDisposition':cross,'crossRationale':rationale,
    'rootSelectionChangeRequired':key in MANUAL_CURRENT_CORRECTION_KEYS,
    'blindAlternativeFinding':finding,
    'currentTokenAudit':cur_audit,'primaryProposalTokenAudit':primary_audit,'blindProposalTokenAudit':blind_audit,
    'blindTokenRecordPass':d.get('tokensPreserved') is True,
   })
   if cross=='accept-current' and p.get('decisionOutputSha256')!=c['currentTargetSha256']: raise SystemExit('accept-current target hash mismatch '+str(key))
   counts[cross]+=1
  if old.get('crossDisposition')!=base['crossDisposition']: decision_changed+=1
  # Carry no machine-selected value into the integrated cross ledger.
  if any(k in base for k in ('selectedTarget','chosenTarget','recommendedTarget','rootSelectedTarget')): raise SystemExit('selection field present')
  out.append(base)
 if counts!=collections.Counter({'accept-current':186,'correction':23,'refinement':7,'hold-callerless-hash-only':24}): raise SystemExit('cross disposition counts mismatch '+str(counts))
 if exact_agreement!=6 or blind_quality_count!=1 or decision_changed!=20 or token_failures!=collections.Counter({'current':20}): raise SystemExit('cross comparison totals mismatch '+str((exact_agreement,blind_quality_count,decision_changed,token_failures)))
 # Audit the prior third-party cross ledger without using it to create any cell decision.
 old_selected={ident(r):r for r in oldchanges}
 if len(old_selected)!=10: raise SystemExit('prior selected-change audit count mismatch')
 for k,x in old_selected.items():
  pr=prm[k]
  if x.get('selectedTarget')!=pr.get('proposedTarget') or x.get('crossDisposition')!=plm[k].get('decision'):
   raise SystemExit('prior cross selected-change audit differs '+str(k))

 # Publish root-change advisories for the 20 prior accept-current rows with exact manual-literal failures.
 adv=[]
 for x in out:
  if x.get('rootSelectionChangeRequired'):
   k=(x['sourceId'],x['locale']); blind_row=brm[k]
   adv.append({'cellId':x['cellId'],'sourceId':x['sourceId'],'locale':x['locale'],'priorCrossDisposition':x['priorCrossDisposition'],'newCrossDisposition':x['crossDisposition'],'currentTarget':x['currentTarget'],'currentTargetSha256':x['currentTargetSha256'],'blindProposal':x['blindProposal'],'blindProposalSha256':x['blindProposalSha256'],'pinnedManualLiterals':blind_row.get('manualProtectedLiteralsRequired',[]),'currentManualLiteralFailures':x['currentTokenAudit']['protectedLiteralFailures'],'blindProposalTokenPass':x['blindProposalTokenAudit']['pass'],'requiredAction':'replace accept-current with a correction review that preserves each pinned manual literal; blind proposal is evidence only and is not selected','exactTargetSelected':False,'catalogValueApplied':False,'rationale':x['crossRationale']})
 (OUT/'root-change-advisories.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in adv),encoding='utf-8')
 if len(adv)!=20: raise SystemExit('root change advisory count mismatch')
 # Copy sealed source/proposal evidence needed to reproduce every binding. Hash-only hold files remain text-free.
 copies={
  'candidate-free-SHA256SUMS.txt':CF/'SHA256SUMS.txt',
  'candidate-free-input-SHA256SUMS.txt':CFI/'SHA256SUMS.txt',
  'candidate-free-manifest.json':CFI/'manifest.json',
  'candidate-free-cells.jsonl':CFI/'candidate-free-cells.jsonl',
  'candidate-free-source-contexts.jsonl':CFI/'source-contexts.jsonl',
  'candidate-free-prior-active-holds-hash-only.jsonl':CFI/'prior-hold-reattestation.jsonl',
  'candidate-free-prior-hold-summary.json':CFI/'prior-hold-reattestation-summary.json',
  'primary-SHA256SUMS.txt':PRI/'SHA256SUMS.txt',
  'primary-manifest.json':PRI/'manifest.json',
  'primary-summary.json':PRI/'summary.json',
  'primary-ledger.jsonl':PRI/'ledger.jsonl',
  'primary-proposals.jsonl':PRI/'proposals.jsonl',
  'primary-holds-hash-only.jsonl':PRI/'holds.jsonl',
  'blind-SHA256SUMS.txt':BLIND/'SHA256SUMS.txt',
  'blind-input-pins.json':BLIND/'input-pins.json',
  'blind-review-summary.json':BLIND/'review-summary.json',
  'blind-locale-review.jsonl':BLIND/'blind-locale-review.jsonl',
  'blind-dispositions.jsonl':BLIND/'dispositions.jsonl',
  'blind-token-audit.json':BLIND/'token-audit.json',
  'blind-current-window-holds-hash-only.jsonl':BLIND/'current-window-holds.jsonl',
  'blind-prior-active-holds-hash-only.jsonl':BLIND/'prior-hold-lineage.jsonl',
  'prior-cross-SHA256SUMS.txt':PRIOR/'SHA256SUMS.txt',
  'prior-cross-manifest.json':PRIOR/'manifest.json',
  'prior-cross-summary.json':PRIOR/'summary.json',
  'prior-cross-ledger-audit-only.jsonl':PRIOR/'cross-ledger.jsonl',
  'prior-cross-selected-changes-audit-only.jsonl':PRIOR/'selected-changes.jsonl',
 }
 for name,src in copies.items(): shutil.copyfile(src,OUT/name)
 (OUT/'integrated-cross-ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in out),encoding='utf-8')
 (OUT/'source-context-index.jsonl').write_text((CFI/'source-contexts.jsonl').read_text(encoding='utf-8'),encoding='utf-8')
 # Explicit comparison table for the 10 proposal-bearing cells, with no chosen value.
 compare=[]
 for key in sorted(prm,key=lambda k:(prm[k]['position'],LOCALES.index(k[1]))):
  pr=prm[key]; d=brm[key]
  compare.append({'sourceId':key[0],'locale':key[1],'primaryDecision':pr['decision'],
   'primaryProposal':pr['proposedTarget'],'primaryProposalSha256':pr['proposedTargetSha256'],
   'blindProposal':d['proposal'],'blindProposalSha256':d['proposalSha256'],
   'textAgreement':('exact' if pr['proposedTarget']==d['proposal'] else 'different-wording'),
   'crossAssessment':'primary draft supported; review-only, no catalog value selected'})
 (OUT/'proposal-reconciliation.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in compare),encoding='utf-8')
 summary={
  'artifact':'ROMarrNG PR #70 W765-W784 integrated independent cross-review',
  'repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W765-W784','head':HEAD,'tree':TREE,
  'cellCount':240,'callerBackedCells':216,'callerReferences':23,'callerlessHashOnlyCells':24,
  'priorActiveHashOnlyHolds':988,'resultingActiveHashOnlyHolds':1012,
  'crossDispositionCounts':dict(counts),'primaryProposalCells':10,'primaryBlindExactTextAgreement':exact_agreement,
  'primaryBlindDifferentWordingButPrimarySupported':10-exact_agreement,
  'blindProposalQualityFindings':blind_quality_count,'currentManualLiteralMismatchCells':token_failures.get('current',0),'blindProposalTokenFailures':token_failures.get('blind',0),'primaryProposalTokenFailures':token_failures.get('primary',0),
  'priorCrossAuditDispositionDifferences':decision_changed,'priorPrimarySelectedTargetDifferences':0,
  'changedRootSelectionsRequired':20,'rootChangeAdvisories':20,
  'changedRootSelectionGroups':{'titleInstructionsMissingPinnedCommentExample':10,'appriseMissingPinnedURLsLiteral':10},
  'conditionalRootChangeNote':'If a root decision selected the blind French long-paragraph alternative, correct plural agreement (“Connexions facultatives”); the pinned current French target is already correct.',
  'exactTargetSelected':False,'catalogValueApplied':False,'repositoryEdited':False,
  'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False,
  'inputChecksums':{'candidateFreeOuter':'PASS','candidateFreeInner':'PASS','primary':'PASS','blind':'PASS','priorCrossAudit':'PASS'},
  'bundledVerifierObservations':{'candidateFree':'FAIL at worktree pin/clean guard','primary':'FAIL via candidate-free worktree pin/clean guard','blind':'PASS'},
  'currentWorktreeSourceContentRead':False,'currentWorktreePinGuardInvokedByBundledInputVerifiers':True,
  'liveExactHeadSourceReread':False,
  'reviewLimit':'Cross ledger binds exact pinned source/caller evidence and hashes across the sealed packets; the changed worktree was not read for source text, and native-speaker review was not performed.',
  'confidence':'moderate','nextBoundary':{'continuationIndex':785,'oneBasedPosition':786,'sourceId':'ui.optional-overrides-the-webhook-s-dis.4116a5e8e4','sourceSha256':'4116a5e8e4222045299ae89f3577810da389c5c65f51cf8a3b097ecf05ef348e'},
  'result':'PASS_STATIC_PACKET_RECONCILIATION_WITH_20_ROOT_CHANGE_ADVISORIES_AND_WORKTREE_GUARD_LIMITATION'
 }
 (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 pins={
  'artifact':'ROMarrNG W765-W784 integrated cross input pins','head':HEAD,'tree':TREE,
  'candidateFree':cf_outer,'candidateFreeInner':cf_inner,'primary':pri_pin,'independentBlind':blind_pin,'priorCrossAuditOnly':prior_pin,
  'candidateFreeManifestSha256':sha((CFI/'manifest.json').read_bytes()),
  'primaryManifestSha256':sha((PRI/'manifest.json').read_bytes()),
  'blindInputPinsSha256':sha((BLIND/'input-pins.json').read_bytes()),
  'candidateFreeCellsSha256':sha((CFI/'candidate-free-cells.jsonl').read_bytes()),
  'candidateFreeSourceContextsSha256':sha((CFI/'source-contexts.jsonl').read_bytes()),
  'primaryLedgerSha256':sha((PRI/'ledger.jsonl').read_bytes()),'primaryProposalsSha256':sha((PRI/'proposals.jsonl').read_bytes()),
  'blindLocaleReviewSha256':sha((BLIND/'blind-locale-review.jsonl').read_bytes()),'blindDispositionsSha256':sha((BLIND/'dispositions.jsonl').read_bytes()),
  'priorCrossLedgerSha256AuditOnly':sha((PRIOR/'cross-ledger.jsonl').read_bytes()),
  'priorSelectedChangesSha256AuditOnly':sha((PRIOR/'selected-changes.jsonl').read_bytes()),
  'priorActiveHoldFileSha256':previous_active_sha,
  'worktreeInspection':'No source/catalog file contents were read. Bundled pin/clean verifiers queried only the worktree pin/clean guard and failed there; this cross verifier uses sealed packets only.'
 }
 (OUT/'input-pins.json').write_text(json.dumps(pins,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 readme=f'''# ROMarrNG PR #70 W765–W784 integrated cross-review

Pinned input: `{HEAD}` / tree `{TREE}`. This packet reconciles 240 cells (216 caller-backed proposals and 24 text-free callerless holds) across 12 locales and binds all 23 caller references across the sealed candidate-free, primary, and blind packets.

Cross dispositions: 186 accept-current, 23 correction, 7 refinement, 24 hash-only hold. The 10 primary proposals remain supported by the independent blind/source-context review; six match the blind text exactly and four use more context-accurate wording. Another 20 current targets previously marked accept-current require correction review because they fail the blind packet’s pinned manual literal checks: 10 omit the exact `# comments` parser example, and 10 use `URL` instead of exact `URLs`. The Vietnamese title instruction also rewrites the exact `Title →tab← platform` example. The blind drafts preserve these exact literals. No catalog target was selected or applied. The packet reattests 988 prior active holds and adds 24 callerless holds, for 1,012 active holds.

One blind-only French alternative for the long optional-connections paragraph has a plural-agreement error (`Connexions facultative`). The pinned current French wording uses the correct plural, so this does not create an additional root change. If that blind variant was selected elsewhere, change that selection to a grammatically correct wording. The 10 previously cross-supported proposed changes remain supported; the 20 manual-literal findings supersede earlier accept-current dispositions.

All packet checksum lists pass, and the independent blind verifier passes. The bundled candidate-free and primary verifiers stop at the worktree pin/clean guard because the input worktree is no longer at the pinned clean state. Per instruction, this cross-review did not read the modified worktree’s source/catalog contents; it binds the exact source/caller hashes and evidence across the sealed packets. Native-speaker approval was not performed.

The prior third-party cross ledger is included as an audit trail only; it was not used to create these dispositions. No repository files were changed and no tests, builds, scans, CI, or browser actions were run.

Run `python3 -B verify_integrated_cross.py` and `sha256sum -c SHA256SUMS.txt` from this directory.
'''
 (OUT/'README.md').write_text(readme,encoding='utf-8')
 # Hash every deliverable except manifest/checksum list; the verifier and builder are included.
 files={p.relative_to(OUT).as_posix():sha(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')}
 manifest={'artifact':'ROMarrNG W765-W784 integrated cross-review','head':HEAD,'tree':TREE,'cellCount':240,'callerReferenceCount':23,'files':files}
 (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 sums=[]
 for p in sorted(OUT.rglob('*')):
  if p.is_file() and p.name!='SHA256SUMS.txt': sums.append(f'{sha(p.read_bytes())}  {p.relative_to(OUT).as_posix()}')
 (OUT/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
 print(json.dumps({'result':'BUILT','output':str(OUT),'dispositions':dict(counts),'proposalTextExactAgreement':exact_agreement,'blindQualityFindings':blind_quality_count,'checksumListSha256':sha((OUT/'SHA256SUMS.txt').read_bytes())},indent=2))
if __name__=='__main__': main()
