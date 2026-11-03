from pathlib import Path
from collections import Counter
import hashlib, json, re, subprocess, sys
from datetime import datetime, timezone

TASK=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-rebased-primary-20261103')
OUT=TASK/'primary-review'
INPUT=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-rebased-candidate-free-20261103/input')
REPO=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-rebase-20261103/repo')
OLD_PRIMARY=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-primary-review-20261103/primary-review')
OLD_INPUT=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-candidate-free-20261103/input')
OLD_CROSS=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-cross-audit-20261103')
HEAD='0afd1d8c150fb96d868394a8d9620371db612185'
TREE='0ba717d05c49356d8b1f55ac4a6b8844c161a402'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
NEW_POSITIONS=[392,396,398,399]

if OUT.exists() and any(OUT.iterdir()): raise SystemExit(f'Refusing to overwrite {OUT}')
OUT.mkdir(parents=True,exist_ok=True)
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(path): return json.loads(path.read_text(encoding='utf-8'))
def readjl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]
def writej(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def writejl(name,rows): (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def run(args,cwd=None): return subprocess.run(args,cwd=cwd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout.strip()
def verify_dir(path,checksum,verifier):
    run(['sha256sum','-c','SHA256SUMS.txt'],cwd=path)
    return run([sys.executable,verifier],cwd=path)

# Verify all sealed inputs before consulting prior suggestions.
input_verify=run([sys.executable,'verify_input.py'],cwd=INPUT)
assert input_verify.startswith('PASS: rebased candidate-free W385-W404 packet;')
prior_primary_verify=verify_dir(OLD_PRIMARY,'SHA256SUMS.txt','verify-primary-review.py')
prior_cross_verify=verify_dir(OLD_CROSS,'SHA256SUMS.txt','verify_cross_audit.py')
head=run(['git','-C',str(REPO),'rev-parse','HEAD']); tree=run(['git','-C',str(REPO),'rev-parse','HEAD^{tree}'])
status=run(['git','-C',str(REPO),'status','--porcelain=v1'])
assert head==HEAD and tree==TREE and not status

im=readj(INPUT/'manifest.json'); att=readj(INPUT/'PR-attestation.json')
assert im['head']==HEAD and im['tree']==TREE and im['cellCount']==240 and im['newlyRenderableDispatchCells']==48
assert att['headRefOid']==att['liveBranchRefOid']==att['livePullRefOid']==HEAD and att['headTree']==TREE
assert im['candidateFree'] and not im['proposedTargetsIncluded'] and not im['reviewDecisionsIncluded']
old_catalog_sha=readj(OLD_INPUT/'manifest.json')['catalogSha256']
assert im['catalogSha256']==old_catalog_sha

contexts=readjl(INPUT/'source-contexts.jsonl'); cells=readjl(INPUT/'current-target-cells.jsonl')
source_meta={r['position']:r for r in readjl(INPUT/'source-inventory-selection.jsonl')}
ctx_by_pos={r['position']:r for r in contexts}
cell_by_key={(r['position'],r['locale']):r for r in cells}
assert len(contexts)==20 and len(cells)==240
# Independently bind packet excerpts and file pins to the clean exact-head clone.
for ctx in contexts:
    for ref in ctx['callerContextRefs']:
        path=ref['path']; raw=(REPO/path).read_bytes()
        assert sha(raw)==ref['fileSha256']
        assert run(['git','-C',str(REPO),'rev-parse','HEAD:'+path])==ref['gitBlob']
        lines=raw.decode('utf-8').splitlines()
        assert ref['contextLines']==[{'line':i,'text':lines[i-1]} for i in range(ref['lineStart'],ref['lineEnd']+1)]

old_primary_rows=readjl(OLD_PRIMARY/'review-ledger.jsonl')
old_primary_decisions=readjl(OLD_PRIMARY/'review-decisions.jsonl')
old_cross_rows=readjl(OLD_CROSS/'cross-audit-ledger.jsonl')
apply_rows=readjl(OLD_CROSS/'apply-plan.jsonl')
assert len(old_primary_rows)==len(old_cross_rows)==240
primary_by_key={(r['position'],r['locale']):r for r in old_primary_rows}
primary_decision_by_key={(r['position'],r['locale']):r for r in old_primary_decisions}
cross_by_key={(r['position'],r['locale']):r for r in old_cross_rows}
apply_by_key={(r['position'],r['locale']):r for r in apply_rows}
assert len(primary_by_key)==len(cross_by_key)==240
assert len(apply_by_key)==21

# Primary semantic review performed now that exact-ID dispatch is renderable.
new_reviews={
 (392,'ko'):{'disposition':'correction','target':'소스 파일이 없거나 심볼릭 링크입니다.','confidence':'moderate','rationale':'The current verb 사라지거나 suggests that the file disappeared as an event. 없거나 states the source file is missing now, and 심볼릭 링크 gives a clear Korean rendering of symlink.'},
 (392,'zh-Hans'):{'disposition':'correction','target':'源文件不存在或是符号链接。','confidence':'moderate','rationale':'The current Chinese leaves symlink in English. 符号链接 is the standard localized technical term and the sentence directly states that the source file is absent or is a symlink.'},
 (392,'zh-Hant'):{'disposition':'correction','target':'來源檔案不存在或是符號連結。','confidence':'moderate','rationale':'The current value is Simplified Chinese and leaves symlink in English. This Traditional Chinese wording preserves the missing-file or symbolic-link alternatives.'},
 (399,'hi'):{'disposition':'correction','target':'Sunshine ने इसे अस्वीकार कर दिया: कोई Moonlight क्लाइंट पेयरिंग का इंतज़ार नहीं कर रहा है। पहले अपने क्लाइंट पर पेयरिंग शुरू करें।','confidence':'moderate','rationale':'The current target uses जोड़ना (adding) for both waiting to pair and starting pairing. The source requires a pairing action on the client first; पेयरिंग makes that instruction explicit and consistent with neighboring pairing UI.'},
 (399,'id'):{'disposition':'correction','target':'Sunshine menolak: tidak ada klien Moonlight yang menunggu untuk dipasangkan. Mulai proses pemasangan di klien Anda terlebih dahulu.','confidence':'high','rationale':'The current target omits the instruction to start pairing on the client first. This wording states both the missing waiting client and the required client-side pairing action.'},
}

placeholder_re=re.compile(r'\{[A-Za-z][A-Za-z0-9_]*\}')
tag_re=re.compile(r'</?[A-Za-z][^>]*>')
num_re=re.compile(r'(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])')
icu_re=re.compile(r'\{\s*[A-Za-z][A-Za-z0-9_]*\s*,\s*(plural|select|selectordinal)\s*,')

def technical_checks(source,target,cell,position):
    source_ph=placeholder_re.findall(source); target_ph=placeholder_re.findall(target)
    source_tags=tag_re.findall(source); target_tags=tag_re.findall(target)
    source_nums=num_re.findall(source); target_nums=num_re.findall(target)
    source_protected=cell['sourceProtectedLiterals']
    missing=[x for x in source_protected if x not in target]
    expected_surface={396:['PIN'],398:['Sunshine','Moonlight','PIN'],399:['Sunshine','Moonlight']}.get(position,[])
    missing_surface=[x for x in expected_surface if x not in target]
    checks={
      'placeholderMultiset':sorted(source_ph)==sorted(target_ph),
      'markupTokens':sorted(source_tags)==sorted(target_tags),
      'numericTokens':source_nums==target_nums,
      'protectedLiterals':not missing,
      'icuSyntax':bool(icu_re.search(source))==bool(icu_re.search(target)),
      'knownProductAndPairingLiterals':not missing_surface,
      'missingProtectedLiterals':missing,
      'missingSurfaceLiterals':missing_surface,
      'sourcePlaceholderTokens':source_ph,
      'targetPlaceholderTokens':target_ph,
      'sourceNumericTokens':source_nums,
      'targetNumericTokens':target_nums,
      'sourceProtectedLiterals':source_protected,
      'icuPluralCategories':'not present in this selected source' if not icu_re.search(source) else 'preserved',
    }
    checks['allPassed']=all(checks[k] is True for k in ['placeholderMultiset','markupTokens','numericTokens','protectedLiterals','icuSyntax','knownProductAndPairingLiterals'])
    return checks

ledger=[]; decisions=[]; history=[]; token_issues=[]; counts=Counter(); provenance_counts=Counter()
for current in cells:
    key=(current['position'],current['locale']); pos,locale=key
    prior=primary_by_key[key]; cross=cross_by_key[key]; ctx=ctx_by_pos[pos]
    # Reattest each earlier primary and cross-audit record to the unchanged source/current catalog cell.
    assert prior['sourceId']==cross['sourceId']==current['sourceId']
    assert prior['source']==cross['source']==current['source']
    assert prior['sourceSha256']==cross['sourceSha256']==current['sourceSha256']
    assert prior['currentTarget']==cross['currentTarget']==current['currentTarget']
    assert prior['currentTargetSha256']==cross['currentTargetSha256']==current['currentTargetSha256']
    assert prior['catalog']['translationHash']==current['catalogTranslationHash']
    assert prior['disposition']==cross['primaryDisposition']
    assert prior['rationale']==cross['primaryRationale']
    assert prior['dispatchGap']==cross['translationDispatchGap']
    old_decision=primary_decision_by_key.get(key)
    old_primary_target=old_decision['target'] if old_decision else current['currentTarget']
    old_primary_disposition=old_decision['disposition'] if old_decision else prior['disposition']
    assert old_primary_disposition==prior['disposition']
    assert cross['primaryReviewerTarget']==old_primary_target
    assert sha(old_primary_target.encode())==(sha(old_primary_target.encode()))
    if cross['crossAuditDisposition']!='hold':
        assert cross['selectedTargetSha256']==sha(cross['selectedTarget'].encode())
        planned=apply_by_key.get(key)
        if cross['selectedTarget']!=current['currentTarget']:
            assert planned and planned['selectedTarget']==cross['selectedTarget'] and planned['selectedTargetSha256']==cross['selectedTargetSha256']
        else:
            assert planned is None
    else:
        assert key not in apply_by_key and cross['selectedTarget']==current['currentTarget']

    if pos in NEW_POSITIONS:
        assert prior['disposition']=='hold' and cross['crossAuditDisposition']=='hold'
        assert prior['dispatchGap'] is True and cross['translationDispatchGap'] is True
        assert ctx['translationDispatchGap'] is False and ctx['callerResolutionHold'] is False
        review=new_reviews.get(key)
        if review:
            disposition=review['disposition']; target=review['target']; confidence=review['confidence']; rationale=review['rationale']
        else:
            disposition='accept-current'; target=current['currentTarget']; confidence='moderate'
            rationale={
              392:'The target preserves the current missing-source-file or symlink condition. The new exact local source-key route makes this fixed app-owned message translatable; arbitrary API text remains opaque.',
              396:'The target says the PIN was submitted without claiming the host confirmed it, then directs the user to check the paired-client list. This matches the host contract and exact source-bound route.',
              398:'The target preserves the Sunshine API limitation, distinguishes acceptance from knowledge of a waiting client, and instructs the user to start pairing in Moonlight and enter its displayed PIN.',
              399:'The target preserves the refusal and absent waiting Moonlight client, and explicitly instructs the user to start pairing on the client first.',
            }[pos]
        origin='new-primary-semantic-review-after-dispatch-fix'
        previous_disposition='hold'; previous_selected_target=current['currentTarget']
        previous_selected_from='current'; previous_cross_rationale=cross['crossAuditRationale']
    else:
        assert prior['dispatchGap'] is False and cross['translationDispatchGap'] is False
        disposition=cross['crossAuditDisposition']; target=cross['selectedTarget']
        confidence=cross['primaryConfidence']; rationale=cross['crossAuditRationale']
        origin='re-attested-prior-cross-audit-resolution'
        previous_disposition=disposition; previous_selected_target=target; previous_selected_from=cross['selectedFrom']; previous_cross_rationale=cross['crossAuditRationale']

    assert target is not None and isinstance(target,str)
    target_sha=sha(target.encode('utf-8'))
    checks=technical_checks(current['source'],target,current,pos)
    if not checks['allPassed']:
        token_issues.append({'position':pos,'locale':locale,'checks':checks})
    assert checks['allPassed'], f'token/protected literal issue {key}: {checks}'
    if (pos,locale) in new_reviews:
        assert disposition=='correction' and target!=current['currentTarget']
    counts[disposition]+=1; provenance_counts[origin]+=1
    hist={
      'priorPrimaryDisposition':prior['disposition'],
      'priorPrimaryReviewerTarget':old_primary_target,
      'priorPrimaryReviewerTargetSha256':sha(old_primary_target.encode()),
      'priorPrimaryRationale':prior['rationale'],
      'priorPrimaryConfidence':prior['confidence'],
      'priorPrimaryCallerContextSha256':prior['callerEvidence']['callerContextSha256'],
      'priorCrossAuditDisposition':cross['crossAuditDisposition'],
      'priorCrossAuditSelectedTarget':cross['selectedTarget'],
      'priorCrossAuditSelectedTargetSha256':cross['selectedTargetSha256'],
      'priorCrossAuditSelectedFrom':cross['selectedFrom'],
      'priorCrossAuditRationale':cross['crossAuditRationale'],
      'priorCrossAuditProposalComparison':cross['proposalComparison'],
      'priorCrossAuditCallerContextSha256':cross['callerContextSha256'],
      'priorDispatchGap':prior['dispatchGap'],
      'priorHoldIssue':cross['holdIssue'],
      'priorCrossAuditHead':readj(OLD_CROSS/'manifest.json')['head'],
      'priorPrimaryHead':readj(OLD_PRIMARY/'manifest.json')['head'],
    }
    history.append({'position':pos,'locale':locale,'sourceId':current['sourceId'],**hist,'newHead':HEAD,'newCallerContextSha256':ctx['callerContextSha256'],'newDisposition':disposition,'newTargetSha256':target_sha,'carryForward':pos not in NEW_POSITIONS})
    row={
      'position':pos,'locale':locale,'sourceId':current['sourceId'],'source':current['source'],'sourceSha256':current['sourceSha256'],
      'sourceKind':source_meta[pos]['sourceKind'],'translationStatus':current['translationStatus'],
      'currentTarget':current['currentTarget'],'currentTargetSha256':current['currentTargetSha256'],
      'disposition':disposition,'target':target,'targetSha256':target_sha,'confidence':confidence,'rationale':rationale,
      'decisionOrigin':origin,'newlyRenderablePosition':pos in NEW_POSITIONS,
      'previousPrimaryDisposition':prior['disposition'],'previousPrimaryTarget':old_primary_target,
      'previousCrossAuditDisposition':cross['crossAuditDisposition'],'previousCrossAuditSelectedTarget':cross['selectedTarget'],
      'previousCrossAuditSelectedFrom':cross['selectedFrom'],'previousCrossAuditRationale':cross['crossAuditRationale'],
      'priorDispatchGap':prior['dispatchGap'],'dispatchGap':ctx['translationDispatchGap'],
      'callerContextSha256':ctx['callerContextSha256'],'callerContextRefs':ctx['callerContextRefs'],
      'catalogPath':current['catalogPath'],'catalogTranslationHash':current['catalogTranslationHash'],
      'checks':checks,
    }
    ledger.append(row)
    decisions.append({'position':pos,'locale':locale,'sourceId':current['sourceId'],'disposition':disposition,'confidence':confidence,'target':target,'targetSha256':target_sha,'rationale':rationale,'decisionOrigin':origin})

assert sum(counts.values())==240 and len(ledger)==len(decisions)==len(history)==240
assert len(new_reviews)==5 and sum(1 for x in ledger if x['decisionOrigin']=='new-primary-semantic-review-after-dispatch-fix')==48
assert sum(1 for x in ledger if x['newlyRenderablePosition'])==48
assert len(apply_rows)==21
assert Counter(r['disposition'] for r in ledger)==Counter({'accept-current':214,'correction':22,'refinement':4})

# Reattest predecessor holds against the fresh candidate-free packet and preserve the rows byte-for-byte.
hold_bytes=(INPUT/'prior-hold-reattestation.jsonl').read_bytes()
holds=readjl(INPUT/'prior-hold-reattestation.jsonl')
assert len(holds)==288 and all(r['targetUnchanged'] and r['sourceMatchesCurrentQueue'] and r['positionMatchesCurrentQueue'] for r in holds)
(OUT/'prior-hold-reattestation.jsonl').write_bytes(hold_bytes)
writejl('review-ledger.jsonl',ledger); writejl('review-decisions.jsonl',decisions); writejl('prior-decision-reattestation.jsonl',history)
writejl('source-context-evidence.jsonl',contexts)
writej('input-verification.json',{
 'candidateFreeVerifier':'PASS','candidateFreeInputPath':str(INPUT),'candidateFreeInputManifestSha256':sha((INPUT/'manifest.json').read_bytes()),
 'candidateFreeInputChecksumListSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),'head':HEAD,'tree':TREE,'cellCount':len(cells),
 'currentCatalogSha256':im['catalogSha256'],'priorCandidateFreeCatalogSha256':old_catalog_sha,'sameCatalogAsPriorHead':im['catalogSha256']==old_catalog_sha,
 'priorPrimaryVerifier':'PASS','priorPrimarySeal':sha((OLD_PRIMARY/'SHA256SUMS.txt').read_bytes()),
 'priorCrossAuditVerifier':'PASS','priorCrossAuditSeal':sha((OLD_CROSS/'SHA256SUMS.txt').read_bytes()),
 'priorPrimaryRowsReattested':len(old_primary_rows),'priorCrossAuditRowsReattested':len(old_cross_rows),
 'allPriorSourcesAndCurrentTargetsUnchanged':True,'priorResolvedDecisionsCarriedForward':192,'priorDispatchGapHoldsReplacedByNewReview':48,
 'priorHoldsReattested':len(holds),'priorHoldBytesSha256':sha(hold_bytes),'priorHoldsUnchanged':True,
 'sourceContextFilesReattestedAgainstExactHead':sorted({ref['path'] for c in contexts for ref in c['callerContextRefs']}),
 'repositoryStatus':'clean','packetVerificationOnly':True,
})
summary={
 'result':'PASS','head':HEAD,'tree':TREE,'window':'W385-W404','sourceCount':20,'localeCount':12,'cellCount':240,
 'effectiveDecisionCounts':dict(sorted(counts.items())),
 'newSemanticReviewCounts':{'cells':48,'positions':NEW_POSITIONS,'acceptCurrent':43,'corrections':5,'holds':0},
 'newCorrections':[{'position':p,'locale':l,'target':v['target'],'confidence':v['confidence']} for (p,l),v in new_reviews.items()],
 'reconciledPreviousCellsCarriedForward':192,'priorPrimaryRowsReattested':240,'priorCrossAuditRowsReattested':240,
 'priorSelectedWindowDispatchGapHolds':48,'newlyRenderableDispatchCells':48,'remainingDispatchGapCells':0,
 'predecessorHoldsReattestedUnchanged':288,'predecessorHoldSha256':sha(hold_bytes),
 'placeholderMarkupNumericIcuProtectedLiteralMismatches':0,'surfaceLiteralMismatches':0,
 'decisionOrigins':dict(sorted(provenance_counts.items())),
 'priorCrossAuditChangeSetPreserved':{'plannedChangeCount':21,'additionalVietnameseSwitchFamilyRefinement':True,'materialDifferencesAdjudicated':3},
 'nativeSpeakerApproval':'not obtained','browserOrNativeReview':'not performed','repositoryOrPRFilesEdited':False,
 'testsBuildsCiBrowserReleaseOrTagRun':False,
}
writej('summary.json',summary)
manifest={
 'schemaVersion':1,'artifact':'ROMarrNG PR #70 W385-W404 rebased primary semantic review','reviewType':'primary-semantic-rebased','sealed':False,
 'repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':'task/localization-translation-review-20261030','baseRefName':'main',
 'head':HEAD,'tree':TREE,'window':'W385-W404','sourceCount':20,'localeCount':12,'cellCount':240,'localeOrder':LOCALES,
 'inputPath':str(INPUT),'inputManifestSha256':sha((INPUT/'manifest.json').read_bytes()),'inputChecksumListSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),
 'priorPrimaryPath':str(OLD_PRIMARY),'priorPrimaryChecksumListSha256':sha((OLD_PRIMARY/'SHA256SUMS.txt').read_bytes()),
 'priorCrossAuditPath':str(OLD_CROSS),'priorCrossAuditChecksumListSha256':sha((OLD_CROSS/'SHA256SUMS.txt').read_bytes()),
 'previousPrimaryRowsReattested':240,'previousCrossAuditRowsReattested':240,'previousCrossAuditResolvedCellsCarriedForward':192,
 'newlyRenderablePositions':NEW_POSITIONS,'newlyRenderableCells':48,'newlyReviewedCells':48,'remainingDispatchGapPositions':[],'remainingDispatchGapCells':0,
 'priorHoldCellCount':288,'priorHoldTargetsUnchanged':True,'decisionCounts':dict(sorted(counts.items())),
 'nativeSpeakerApproval':'not obtained','candidateFreeVerifier':'PASS','repositoryOrPrFilesEdited':False,
 'files':{},'createdAtUtc':datetime.now(timezone.utc).isoformat(),
}
writej('manifest.json',manifest)
(OUT/'README.md').write_text(
 f'''# ROMarrNG PR #70 W385–W404 rebased primary semantic review\n\nThis primary review is pinned to PR #70 head `{HEAD}` / tree `{TREE}`. The live PR, branch, pull ref, and commit tree were attested in the sealed candidate-free input.\n\nThe candidate-free input contains 240 current locale cells and is sealed separately. All 288 predecessor hold cells reattest unchanged. The candidate-free packet records the new exact source-ID dispatch for positions 392, 396, 398, and 399; those 48 cells are reviewed here for the first time as renderable UI.\n\nThe earlier primary and cross-audit packets were checksum-verified and their packet verifiers passed before their decisions were read. All 240 prior primary rows and all 240 prior cross-audit rows were reattached to the same source IDs, source text/hashes, and current catalog target hashes. The 192 cells outside the resolved dispatch gaps carry forward the previous cross-audit reconciliation, including its 21-item change set, the Japanese unavailable-state adjudication, the Hindi/Indonesian TitleDB wording adjudications, and the Vietnamese Switch-family refinement. The prior 48 holds are superseded by the new semantic review.\n\nFor the newly renderable 48 cells, review yields 43 accept-current decisions and five proposed corrections: Korean, Simplified Chinese, and Traditional Chinese at position 392; Hindi and Indonesian at position 399. Every correction preserves the source meaning and the exact route; arbitrary API text and mismatched source details remain opaque. Placeholder, markup, numeric, ICU-shape, protected-literal, and product/pairing-surface checks pass.\n\nConfidence for the new locale judgments is moderate. This is not native-speaker approval, and browser/native review was not performed. No repository or PR files were edited, and no tests, builds, CI, releases, or tags were run.\n\nRun `sha256sum -c SHA256SUMS.txt` and `python3 verify-primary-review.py` in this directory to verify this packet. The verifier also checks the sealed candidate-free input and the referenced prior review packets.\n''',encoding='utf-8')

# Record exact byte sizes and hashes after all non-checksum files are complete.
filemeta={}
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name!='SHA256SUMS.txt': filemeta[p.name]={'sha256':sha(p.read_bytes()),'byteCount':p.stat().st_size}
manifest['sealed']=True; manifest['files']=filemeta
writej('manifest.json',manifest)
files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt')
(OUT/'SHA256SUMS.txt').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in files),encoding='utf-8')
print(json.dumps({'path':str(OUT),'head':HEAD,'tree':TREE,'cells':len(ledger),'counts':dict(sorted(counts.items())),'newReviewed':48,'newCorrections':len(new_reviews),'holds':len(holds),'sourceFilesReattested':sorted({ref['path'] for c in contexts for ref in c['callerContextRefs']})},ensure_ascii=False,indent=2))
