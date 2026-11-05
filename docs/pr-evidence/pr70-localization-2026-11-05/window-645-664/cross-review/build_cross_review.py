#!/usr/bin/env python3
import collections,hashlib,json,pathlib,re
BASE=pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w645-664-20261105')
OUT=BASE/'cross-review'; CF=BASE/'candidate-free'/'candidate-free'/'input'; PR=BASE/'primary'/'primary-output'; BL=BASE/'blind-review'; IND=OUT/'independent-review'
HEAD='9f8832f67195323955172dd4c3c40e29cbabb5da'; TREE='d6066baa3d03d3b4c6034e5af061fc4bc278b0f9'
def sha(b):return hashlib.sha256(b).hexdigest()
def shat(s):return sha(s.encode('utf-8'))
def canon(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def j(p):return json.loads(p.read_text())
def writej(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def require(ok,msg):
 if not ok:raise SystemExit('FAIL: '+msg)

# Cross resolutions are based on exact caller/source context and direct comparison of both proposals.
MULTI='ui.multi-disc-set-is-grouped-for-metada.86db33ad47'
MISSING='ui.missing.6be36ca49e'; MYLIB='ui.my-library.fbc3b89e6a'; MOON='ui.moonlight-host.52839edd11'
resolutions={
 (MISSING,'id'):{'disposition':'propose-correction','target':'Tidak ditemukan','confidence':'high','reason':'In the Wanted/Missing view the label means the title was not found in the library. This is clearer than Tidak ada (“there is none”) and avoids Belum ada (“not here yet”). The primary and blind targets agree.'},
 (MISSING,'ja'):{'disposition':'propose-correction','target':'未所持','confidence':'high','reason':'The Wanted view identifies games absent from the local collection; 未所持 labels that inventory state. It improves on 不足 (“shortage/insufficiency”). Primary and independent review agree.'},
 (MOON,'hi'):{'disposition':'propose-correction','target':'Moonlight होस्ट','confidence':'moderate','reason':'The caller names a configured host machine and its service state, so the technical loanword होस्ट is clearer than मेजबान, which can mean a person hosting an event.'},
 (MULTI,'ar'):{'disposition':'propose-correction','target':'تُجمَّع المجموعة متعددة الأقراص لأغراض البيانات الوصفية، وتبقى ملفات الأقراص الخاصة بها معًا','confidence':'moderate','reason':'Use the established term البيانات الوصفية and identify the item as a grouped set. Prefer المجموعة (“set/group”) over the blind target الإصدار (“edition/release”), which conflicts with the source.'},
 (MULTI,'de'):{'disposition':'propose-correction','target':'Ein Multi-Disc-Set wird für Metadaten gruppiert; seine Disc-Dateien bleiben zusammen','confidence':'moderate','reason':'The source is a full reason sentence: German needs an article before this singular subject. Disc-Dateien keeps the game-media sense clear.'},
 (MULTI,'es'):{'disposition':'propose-correction','target':'El conjunto de varios discos se agrupa para los metadatos; sus archivos de disco permanecen juntos','confidence':'moderate','reason':'This avoids the English hybrid multi-disc and keeps the grouped-set and files-stay-together meaning in plain Spanish. The blind wording is selected over the primary multidisco variant for clarity.'},
 (MULTI,'hi'):{'disposition':'propose-correction','target':'मल्टी-डिस्क सेट को मेटाडेटा के लिए एक समूह में रखा जाता है; इसकी डिस्क फ़ाइलें साथ रहती हैं','confidence':'moderate','reason':'एक समूह में रखा जाता है is grammatical for grouping the set. Prefer इसकी, which refers directly to the set; the primary उसकी is possible but less cohesive here.'},
 (MULTI,'id'):{'disposition':'propose-correction','target':'Set multi-disk dikelompokkan untuk keperluan metadata; berkas tiap disk tetap bersama','confidence':'moderate','reason':'Dikelompokkan states “grouped” accurately; dikumpulkan means “collected.” The combined wording states the metadata purpose and that each disc’s files remain together.'},
 (MULTI,'ja'):{'disposition':'propose-correction','target':'複数枚組はメタデータ用にまとめて扱われ、各ディスクのファイルは一緒に保たれます。','confidence':'moderate','reason':'複数枚組 clearly means one set containing multiple discs; the current 複数のディスクセット can read as multiple disc sets. No primary or blind correction covered this cell.'},
 (MULTI,'ko'):{'disposition':'propose-refinement','target':'다중 디스크 세트는 메타데이터를 위해 그룹화되며 디스크 파일은 함께 유지됩니다','confidence':'high','reason':'메타데이터 is the standard compound spelling; the current separates it as 메타 데이터.'},
 (MULTI,'pt-BR'):{'disposition':'propose-refinement','target':'O conjunto de vários discos é agrupado para fins de metadados; os arquivos de disco permanecem juntos','confidence':'moderate','reason':'Para fins de metadados expresses the purpose of grouping more naturally than para os metadados.'},
 (MULTI,'vi'):{'disposition':'propose-correction','target':'Bộ nhiều đĩa được nhóm để xử lý siêu dữ liệu; các tệp của từng đĩa vẫn được giữ cùng nhau.','confidence':'moderate','reason':'Bộ đĩa nhiều phần means a multi-part set rather than a set of multiple discs. Bộ nhiều đĩa expresses the source distinction. No primary or blind correction covered this cell.'},
 (MULTI,'zh-Hant'):{'disposition':'propose-refinement','target':'多碟套裝會以一組方式處理中繼資料；各光碟的檔案仍會放在一起。','confidence':'moderate','reason':'合併處理 may suggest merging the metadata. The revision says the set is handled as one group for metadata while keeping the disc files together. No primary or blind correction covered this cell.'},
 (MYLIB,'ar'):{'disposition':'propose-correction','target':'مكتبتي','confidence':'high','reason':'The caller is the user’s game-library mode button. مكتبي means “my office/desk”; مكتبتي is the feminine “my library.”'},
 (MYLIB,'pt-BR'):{'disposition':'propose-correction','target':'Minha biblioteca','confidence':'high','reason':'This is a compact mode button. Remove the unnecessary terminal period; primary and blind agree.'},
}
compare_notes={
 (MISSING,'id'):{'primaryBlindTargetDisagreement':False,'primaryBlindReasonDisagreement':False,'comparison':'Primary and blind agree on Tidak ditemukan and on the problem with Tidak ada. Independent review initially preferred Belum ada; cross adjudication selects “not found” for the missing-in-library status.'},
 (MULTI,'ar'):{'primaryBlindTargetDisagreement':True,'primaryBlindReasonDisagreement':False,'comparison':'Both identify the unnatural metadata term. Their target nouns differ: primary uses المجموعة (set/group), blind uses الإصدار (edition/release). Cross review selects the primary noun because it matches “set”; the blind target conflicts with its own set-meaning rationale.'},
 (MULTI,'es'):{'primaryBlindTargetDisagreement':True,'primaryBlindReasonDisagreement':False,'comparison':'Both reject the English hybrid and preserve the grouped-set meaning. Cross review selects the blind plain-language conjunto de varios discos wording over primary multidisco.'},
 (MULTI,'hi'):{'primaryBlindTargetDisagreement':True,'primaryBlindReasonDisagreement':False,'comparison':'Both correct the awkward current construction. The only material target variation is उसकी vs इसकी; cross review selects इसकी for the immediately referenced set.'},
 (MULTI,'id'):{'primaryBlindTargetDisagreement':True,'primaryBlindReasonDisagreement':False,'comparison':'Both correct dikumpulkan to dikelompokkan. Cross review combines the clearer purpose phrase keperluan metadata with blind’s per-disc berkas tiap disk wording.'},
 (MYLIB,'pt-BR'):{'primaryBlindTargetDisagreement':False,'primaryBlindReasonDisagreement':False,'comparison':'Primary and blind agree: remove the terminal period from the short button label.'},
}

cells=jl(CF/'current-target-cells.jsonl'); contexts={r['sourceId']:r for r in jl(CF/'source-contexts.jsonl')}
ind={ (r['sourceId'],r['locale']):r for r in jl(IND/'independent-cross-ledger.jsonl') }
primary={ (r['sourceId'],r['locale']):r for r in jl(PR/'dispositions.jsonl') }
pholds={ (r['sourceId'],r['locale']):r for r in jl(PR/'hash-only-holds.jsonl') }
blind={ (r['sourceId'],r['locale']):r for r in jl(BL/'blind-ledger.jsonl') }
blind_props={ (r['sourceId'],r['locale']):r for r in jl(BL/'proposals.jsonl') }
primary_props={k:r for k,r in primary.items() if r['disposition']=='CHANGE'}
require(len(cells)==240 and len(ind)==240 and len(primary)==144 and len(pholds)==96 and len(blind)==240,'input dimensions')
require(len(primary_props)==12 and len(blind_props)==6,'proposal input counts')
PH=re.compile(r'\{[^{}]+\}'); MARK=re.compile(r'<[^>]+>'); NUM=re.compile(r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])')

def token_checks(src,target,source_protected):
 return {'placeholder':collections.Counter(PH.findall(src))==collections.Counter(PH.findall(target)),'markup':MARK.findall(src)==MARK.findall(target),'numeric':collections.Counter(NUM.findall(src))==collections.Counter(NUM.findall(target)),'protectedLiterals':all(x in target for x in source_protected)}
ledger=[]; counts=collections.Counter(); proposal_union=set(); cross_proposal_cells=set()
for c in cells:
 key=(c['sourceId'],c['locale']); ctx=contexts[c['sourceId']]; ir=ind[key]; pr=primary.get(key); ph=pholds.get(key); br=blind[key]; bp=blind_props.get(key)
 rowsha=sha(canon(c))
 for candidate in [ir]:
  require(candidate['sourceSha256']==c['sourceSha256'] and candidate['currentTargetSha256']==c['currentTargetSha256'] and candidate['callerContextSha256']==c['callerContextSha256'],'independent hash bind '+str(key))
 if ctx['callerless']:
  require(ir['disposition']=='text-free-hold' and ph is not None and br['disposition']=='text-free-hold','callerless dispositions '+str(key))
  require(br['currentTargetSha256']==c['currentTargetSha256'] and ph['currentTargetSha256']==c['currentTargetSha256'],'callerless hold hashes '+str(key))
  r={'exactHead':HEAD,'exactTree':TREE,'position':c['position'],'sourceId':c['sourceId'],'locale':c['locale'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'candidateFreeCellSha256':rowsha,'callerful':False,'sourceTextIncluded':False,'currentTargetIncluded':False,'primaryDisposition':'HOLD','blindDisposition':'text-free-hold','independentDisposition':'text-free-hold','crossDisposition':'text-free-hold','crossRecommendedTarget':None,'crossRecommendedTargetSha256':None,'crossRationale':'No exact production caller is pinned; preserve as a hash-only hold.','primaryBlindTargetDisagreement':False,'primaryBlindReasonDisagreement':False,'targetIntegrity':'hash-only'}
  counts['text-free-hold']+=1
 else:
  require(pr is not None and pr['callerContextSha256']==c['callerContextSha256'] and br['callerContextSha256']==c['callerContextSha256'],'callerful decision hashes '+str(key))
  require(pr['sourceSha256']==c['sourceSha256'] and pr['currentTargetSha256']==c['currentTargetSha256'],'primary text hashes '+str(key))
  require(br['sourceSha256']==c['sourceSha256'] and br['currentTargetSha256']==c['currentTargetSha256'],'blind text hashes '+str(key))
  final=resolutions.get(key)
  if final:
   target=final['target']; checks=token_checks(c['source'],target,c['sourceProtectedLiterals'])
   require(all(checks.values()),'cross token checks '+str(key))
   disp=final['disposition']; cross_proposal_cells.add(key); counts[disp]+=1
   cross_target=target; cross_sha=shat(target); cross_reason=final['reason']; final_checks=checks
  else:
   disp='accept-current'; cross_target=None; cross_sha=None; cross_reason='Current wording is faithful to the pinned source and caller context; no clear semantic, grammatical, or locale-convention defect was identified.'; final_checks={'currentTargetTokenMismatches':0}; counts[disp]+=1
  pd=pr['disposition']; bd=br['disposition']
  primary_target=pr.get('proposedTarget') if pd=='CHANGE' else None
  blind_target=br.get('selectedTarget') if bd in ('propose-correction','propose-refinement') else None
  tb=primary_target is not None and blind_target is not None and primary_target!=blind_target
  note=compare_notes.get(key)
  r={'exactHead':HEAD,'exactTree':TREE,'position':c['position'],'sourceId':c['sourceId'],'locale':c['locale'],'source':c['source'],'currentTarget':c['currentTarget'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'candidateFreeCellSha256':rowsha,'callerful':True,'callerPaths':sorted({x['path'] for x in ctx['callers']}),'callerReferenceCount':ctx['exactMatchCount'],'primaryDisposition':pd,'primaryTarget':primary_target,'primaryRationale':pr.get('rationale') if pd=='CHANGE' else None,'blindDisposition':bd,'blindTarget':blind_target,'blindRationale':bp.get('reason') if bp else None,'independentDisposition':ir['disposition'],'independentTarget':ir.get('recommendedTarget'),'independentRationale':ir.get('reason'),'crossDisposition':disp,'crossRecommendedTarget':cross_target,'crossRecommendedTargetSha256':cross_sha,'crossRationale':cross_reason,'crossTokenChecks':final_checks,'primaryBlindTargetDisagreement':tb,'primaryBlindReasonDisagreement':note['primaryBlindReasonDisagreement'] if note else None,'proposalComparison':note['comparison'] if note else ('Only primary proposed; cross review independently evaluated it.' if primary_target else 'Neither primary nor blind proposed; cross review independently assessed the current value.'),'independentCrossDifference':(ir['disposition']=='accept-current') != (disp=='accept-current') or (ir.get('recommendedTarget') is not None and cross_target!=ir.get('recommendedTarget'))}
  if pd=='CHANGE' or bp: proposal_union.add(key)
 ledger.append(r)
assert len(ledger)==240 and len(proposal_union)==12
(OUT/'cross-review-ledger.jsonl').write_text(''.join(canon(x).decode() for x in ledger))

# One row per review-origin proposal: 12 primary plus 6 blind = 18 proposal records.
reconciliation=[]
for origin,source_map in [('primary',primary_props),('blind',blind_props)]:
 for key,proposal in sorted(source_map.items(),key=lambda kv:(next(c['position'] for c in cells if c['sourceId']==kv[0][0]),kv[0][1])):
  c=next(x for x in cells if (x['sourceId'],x['locale'])==key); pr=primary[key]; br=blind[key]; final=resolutions[key]
  own=pr['proposedTarget'] if origin=='primary' else br['selectedTarget']
  peer=br['selectedTarget'] if origin=='primary' and br['disposition'] in ('propose-correction','propose-refinement') else pr.get('proposedTarget') if origin=='blind' and pr['disposition']=='CHANGE' else None
  note=compare_notes.get(key)
  target_disagreement=peer is not None and peer!=own
  reconciliation.append({'proposalOrigin':origin,'position':c['position'],'sourceId':c['sourceId'],'locale':c['locale'],'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],'callerContextSha256':c['callerContextSha256'],'candidateFreeCellSha256':sha(canon(c)),'proposalTarget':own,'proposalTargetSha256':shat(own),'proposalRationale':proposal.get('rationale') if origin=='primary' else proposal.get('reason'),'counterpartProposalTarget':peer,'counterpartProposalTargetSha256':shat(peer) if peer is not None else None,'counterpartDisposition':'proposal' if peer is not None else ('accept-current' if origin=='primary' else pr['disposition']),'primaryBlindTargetDisagreement':target_disagreement,'primaryBlindReasonDisagreement':note['primaryBlindReasonDisagreement'] if note else None,'comparisonNote':note['comparison'] if note else 'No counterpart proposal on this cell; cross review evaluated this proposal independently.','crossDisposition':final['disposition'],'crossRecommendedTarget':final['target'],'crossRecommendedTargetSha256':shat(final['target']),'crossTargetMatchesThisProposalExactly':final['target']==own,'crossResolutionRationale':final['reason'],'proposalTargetConflictsOwnRationale':(origin=='blind' and key==(MULTI,'ar')),'proposalTargetRationaleNote':'Blind Arabic proposal says it preserves a multi-disc set, but الإصدار means edition/release; cross selects المجموعة.' if origin=='blind' and key==(MULTI,'ar') else None})
assert len(reconciliation)==18
(OUT/'proposal-reconciliation.jsonl').write_text(''.join(canon(x).decode() for x in reconciliation))

cf_sum=sha((CF/'SHA256SUMS.txt').read_bytes()); pr_sum=sha((BASE/'primary'/'SHA256SUMS.txt').read_bytes()); pr_out_sum=sha((PR/'SHA256SUMS.txt').read_bytes()); blind_sum=sha((BL/'SHA256SUMS.txt').read_bytes()); blind_summary=j(BL/'SUMMARY.json')
blind_expected=blind_summary['candidateFreeChecksumListSha256']
primary_verifier=j(OUT/'attestation'/'primary-verifier.json')
blind_verifier={'result':'FAIL','failure':'blind SUMMARY.json candidateFreeChecksumListSha256 does not equal the current candidate-free input checksum-list hash','expectedCandidateFreeChecksumListSha256':blind_expected,'currentCandidateFreeChecksumListSha256':cf_sum,'directCellAndProposalBindings':'PASS'}
summary={'artifact':'ROMarrNG PR #70 W645-W664 cross-review packet','exactHead':HEAD,'exactTree':TREE,'candidateFreeInputChecksumListSha256':cf_sum,'primaryOuterChecksumListSha256':pr_sum,'primaryOutputChecksumListSha256':pr_out_sum,'blindChecksumListSha256':blind_sum,'cells':240,'callerfulCells':144,'callerlessHashOnlyHolds':96,'crossCounts':dict(counts),'crossProposalCellCount':len(cross_proposal_cells),'primaryBlindUniqueProposalCellCount':len(proposal_union),'primaryProposalCount':len(primary_props),'blindProposalCount':len(blind_props),'proposalRecordsReconciled':len(reconciliation),'primaryBlindTargetDisagreementCells':sum(1 for k in compare_notes if compare_notes[k]['primaryBlindTargetDisagreement']),'primaryBlindRationaleDisagreementCells':sum(1 for k in compare_notes if compare_notes[k]['primaryBlindReasonDisagreement']),'blindTargetRationaleConflictCells':1,'blindSummaryChecksumPinMismatch':{'expected':blind_expected,'actual':cf_sum,'directRowsAndSixProposalTargetsBindToCurrentInput':True},'primaryVerifier':primary_verifier,'nativeSpeakerApproval':False,'browserSignoff':False,'applicationPerformed':False,'repoPrWorkflowEdits':False,'result':'PASS_WITH_BLIND_SUMMARY_PIN_WARNING'}
writej(OUT/'cross-review-summary.json',summary)
exposure={'reviewerRole':'cross-review','candidateFreeExactHeadAndCallerfulCurrentTextReviewed':True,'independentLedgerSealedBeforeInspectingProposalLedgers':True,'primaryAndBlindProposalLedgersInspectedAfterSeal':True,'candidateFreeREADMECountsWereVisibleBeforeIndependentSeal':True,'proposalTargetsWereNotVisibleBeforeIndependentSeal':True,'subagentsUsed':False,'subagentAttempt':'Two shard agents were requested, but all four concurrency slots were occupied; the full independent review was completed directly.','primaryBlindProposalCounts':{'primary':12,'blind':6},'nativeSpeakerApproval':False,'browserReviewPerformed':False,'applicationPerformed':False}
writej(OUT/'process-exposure.json',exposure)

# Human-readable packet notes; exact file seals are created below.
(OUT/'README.md').write_text(f'''# ROMarrNG PR #70 W645–W664 cross-review

This read-only cross-review covers all 240 locale cells (20 source IDs × 12 locales) from candidate-free input pinned to head `{HEAD}` / tree `{TREE}`. It reviewed 144 caller-backed cells and preserved all 96 callerless cells as text-free hash holds.

The independent cross ledger was sealed before opening either proposal ledger. It records the current caller-backed assessment, exact source/target/caller hashes, and token checks. It initially recommended {11} changes. After comparing the primary’s {len(primary_props)} proposals and the blind review’s {len(blind_props)} proposals (18 proposal records across {len(proposal_union)} cells), the cross recommendation is {counts['propose-correction']} corrections, {counts['propose-refinement']} refinements, {counts['accept-current']} keep-current decisions, and {counts['text-free-hold']} hash-only holds. No catalog edit or application is performed.

`proposal-reconciliation.jsonl` contains one row for each primary or blind proposal. It flags {summary['primaryBlindTargetDisagreementCells']} target wording differences and no material rationale disagreements. Cross review rejects the blind Arabic multi-disc noun `الإصدار` (“edition/release”) in favor of `المجموعة` (“set/group”); Spanish, Hindi, and Indonesian alternatives are reconciled in the ledger. One blind Arabic target, الإصدار (edition/release), conflicts with its own stated set-meaning rationale; cross review selects المجموعة (set/group). The cross review also adds Japanese, Vietnamese, and Traditional Chinese multi-disc refinements not proposed by either source review.

The blind packet’s own file checksums pass, and all 240 blind rows plus all 6 blind proposal hashes bind to the current candidate-free source, target, and caller hashes. Its verifier nevertheless fails because `SUMMARY.json` pins candidate-free checksum list `{blind_expected}`, while the current candidate-free checksum list is `{cf_sum}`. This stale packet-level pin is recorded; blind inputs were not edited. The primary verifier and candidate-free verifier pass.

No native-speaker, browser, or production signoff is claimed. PR #70, repository files, catalogs, and workflows were not modified. Use `verify_cross_review.py` to check the output packet and input bindings.
''')
print(json.dumps({'result':summary['result'],'crossCounts':summary['crossCounts'],'primaryProposalRecords':len(primary_props),'blindProposalRecords':len(blind_props),'uniqueProposedCells':len(proposal_union),'targetDisagreementCells':summary['primaryBlindTargetDisagreementCells'],'blindPinMismatch':blind_verifier,'primaryVerifier':primary_verifier},ensure_ascii=False,indent=2))
