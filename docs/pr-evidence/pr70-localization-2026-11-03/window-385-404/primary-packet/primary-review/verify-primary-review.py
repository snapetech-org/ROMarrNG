#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parent
INPUT=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-rebased-candidate-free-20261103/input')
OLD_INPUT=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-candidate-free-20261103/input')
OLD_PRIMARY=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-primary-review-20261103/primary-review')
OLD_CROSS=Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w385-404-cross-audit-20261103')
HEAD='0afd1d8c150fb96d868394a8d9620371db612185'; TREE='0ba717d05c49356d8b1f55ac4a6b8844c161a402'
NEW_POSITIONS=[392,396,398,399]
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(path): return json.loads(path.read_text(encoding='utf-8'))
def readjl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]
def check(ok,msg):
    if not ok: raise SystemExit('FAIL: '+msg)
def verify_seal(path):
    entries={}
    for line in (path/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1); check(sha((path/name).read_bytes())==digest,'upstream checksum '+str(path/name)); entries[name]=digest
    actual={p.name for p in path.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
    check(set(entries)==actual,'upstream checksum inventory '+str(path))
    return entries

def verify_packet(path,script):
    r=subprocess.run([sys.executable,script],cwd=path,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    check(r.returncode==0,'upstream verifier '+str(path)+': '+r.stdout+r.stderr)
    return r.stdout

# Verify all seals and the self-contained candidate-free packet first.
checks={}
for line in (ROOT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest,name=line.split('  ',1); check(sha((ROOT/name).read_bytes())==digest,'primary checksum '+name); checks[name]=digest
actual={p.name for p in ROOT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
check(set(checks)==actual,'primary checksum inventory')
input_checks=verify_seal(INPUT); old_primary_checks=verify_seal(OLD_PRIMARY); old_cross_checks=verify_seal(OLD_CROSS)
input_output=verify_packet(INPUT,'verify_input.py')
prior_primary_output=verify_packet(OLD_PRIMARY,'verify-primary-review.py')
prior_cross_output=verify_packet(OLD_CROSS,'verify_cross_audit.py')
check(input_output.startswith('PASS: rebased candidate-free W385-W404 packet;'),'candidate-free verifier result')

m=readj(ROOT/'manifest.json'); iv=readj(ROOT/'input-verification.json'); im=readj(INPUT/'manifest.json'); att=readj(INPUT/'PR-attestation.json'); summary=readj(ROOT/'summary.json')
check(m['sealed'] is True and m['head']==HEAD and m['tree']==TREE and m['window']=='W385-W404','primary exact head/tree/seal')
check(im['head']==HEAD and im['tree']==TREE and att['headRefOid']==att['liveBranchRefOid']==att['livePullRefOid']==HEAD and att['headTree']==TREE,'candidate-free live ref pins')
check(sha((INPUT/'manifest.json').read_bytes())==m['inputManifestSha256']==iv['candidateFreeInputManifestSha256'],'candidate-free manifest hash pin')
check(sha((INPUT/'SHA256SUMS.txt').read_bytes())==m['inputChecksumListSha256']==iv['candidateFreeInputChecksumListSha256'],'candidate-free seal pin')
check(sha((OLD_PRIMARY/'SHA256SUMS.txt').read_bytes())==m['priorPrimaryChecksumListSha256']==iv['priorPrimarySeal'],'prior primary seal pin')
check(sha((OLD_CROSS/'SHA256SUMS.txt').read_bytes())==m['priorCrossAuditChecksumListSha256']==iv['priorCrossAuditSeal'],'prior cross-audit seal pin')
check(im['catalogSha256']==iv['currentCatalogSha256']==iv['priorCandidateFreeCatalogSha256'] and iv['sameCatalogAsPriorHead'],'same catalog at current and prior heads')
check(iv['repositoryStatus']=='clean' and iv['sourceContextFilesReattestedAgainstExactHead']==['romarr/app.py','romarr/connect.py','romarr/organizer.py','romarr/playability.py','romarr/ui.py'],'live source/context reattestation')

ledger=readjl(ROOT/'review-ledger.jsonl'); decisions=readjl(ROOT/'review-decisions.jsonl'); history=readjl(ROOT/'prior-decision-reattestation.jsonl')
source_contexts=readjl(ROOT/'source-context-evidence.jsonl'); current_cells=readjl(INPUT/'current-target-cells.jsonl'); contexts=readjl(INPUT/'source-contexts.jsonl')
prior_primary=readjl(OLD_PRIMARY/'review-ledger.jsonl'); prior_cross=readjl(OLD_CROSS/'cross-audit-ledger.jsonl'); apply_plan=readjl(OLD_CROSS/'apply-plan.jsonl')
check(len(ledger)==len(decisions)==len(history)==len(current_cells)==240,'240 primary decisions/ledger/history/input rows')
check(len(source_contexts)==len(contexts)==20 and source_contexts==contexts,'20 current caller contexts copied exactly')
key=lambda r:(r['position'],r['locale'])
current={key(r):r for r in current_cells}; new={key(r):r for r in ledger}; decision_by_key={key(r):r for r in decisions}; hist_by_key={key(r):r for r in history}
oldp={key(r):r for r in prior_primary}; oldc={key(r):r for r in prior_cross}; plan={key(r):r for r in apply_plan}
check(set(new)==set(current)==set(oldp)==set(oldc)==set(decision_by_key)==set(hist_by_key),'exact complete cell key coverage')
check(set(plan)=={k for k,r in oldc.items() if r['crossAuditDisposition']!='hold' and r['selectedTarget']!=r['currentTarget']},'prior cross-audit 21-item change set')
context_by_pos={x['position']:x for x in contexts}
for k,row in new.items():
    c=current[k]; p=oldp[k]; x=oldc[k]; h=hist_by_key[k]; d=decision_by_key[k]
    check(row['sourceId']==c['sourceId']==p['sourceId']==x['sourceId'] and row['source']==c['source']==p['source']==x['source'],'source lineage '+str(k))
    check(row['sourceSha256']==c['sourceSha256']==p['sourceSha256']==x['sourceSha256'],'source hash '+str(k))
    check(row['currentTarget']==c['currentTarget']==p['currentTarget']==x['currentTarget'],'current target lineage '+str(k))
    check(row['currentTargetSha256']==c['currentTargetSha256']==p['currentTargetSha256']==x['currentTargetSha256'],'current target hash '+str(k))
    check(row['catalogTranslationHash']==c['catalogTranslationHash']==p['catalog']['translationHash'],'catalog cell hash '+str(k))
    check(row['previousPrimaryDisposition']==p['disposition']==x['primaryDisposition'] and row['previousPrimaryDisposition']==h['priorPrimaryDisposition'],'prior primary disposition '+str(k))
    check(row['previousPrimaryTarget']==x['primaryReviewerTarget']==h['priorPrimaryReviewerTarget'],'prior primary target '+str(k))
    check(row['previousCrossAuditDisposition']==x['crossAuditDisposition']==h['priorCrossAuditDisposition'],'prior cross-audit disposition '+str(k))
    check(row['previousCrossAuditSelectedTarget']==x['selectedTarget']==h['priorCrossAuditSelectedTarget'],'prior cross-audit selection '+str(k))
    check(row['callerContextSha256']==contexts[row['position']-385]['callerContextSha256'],'current caller context '+str(k))
    check(row['callerContextRefs']==contexts[row['position']-385]['callerContextRefs'],'current caller excerpts '+str(k))
    check(row['dispatchGap'] is False,'no remaining gap '+str(k))
    check(row['targetSha256']==sha(row['target'].encode()) and d['target']==row['target'] and d['targetSha256']==row['targetSha256'],'final target hash '+str(k))
    if row['position'] not in NEW_POSITIONS:
        check(row['decisionOrigin']=='re-attested-prior-cross-audit-resolution' and h['carryForward'] is True,'carried-forward decision origin '+str(k))
        check(row['disposition']==x['crossAuditDisposition'] and row['target']==x['selectedTarget'],'prior resolution carried exactly '+str(k))
        check(row['previousCrossAuditSelectedFrom']==x['selectedFrom'],'selected-from history '+str(k))
    else:
        check(row['decisionOrigin']=='new-primary-semantic-review-after-dispatch-fix' and row['newlyRenderablePosition'] and h['carryForward'] is False,'new review origin '+str(k))
        check(p['disposition']=='hold' and x['crossAuditDisposition']=='hold' and p['dispatchGap'] is True and x['translationDispatchGap'] is True,'prior hold reattested '+str(k))
        check(context_by_pos[row['position']]['translationDispatchGap'] is False,'new dispatch status '+str(k))
    checks=row['checks']; check(checks['allPassed'] is True,'all technical token checks '+str(k))
    check(all(checks[n] is True for n in ['placeholderMultiset','markupTokens','numericTokens','protectedLiterals','icuSyntax','knownProductAndPairingLiterals']),'token check detail '+str(k))
    check(d['position']==row['position'] and d['locale']==row['locale'] and d['disposition']==row['disposition'] and d['confidence']==row['confidence'],'decision record alignment '+str(k))

corrections={(r['position'],r['locale']):r['target'] for r in ledger if r['decisionOrigin']=='new-primary-semantic-review-after-dispatch-fix' and r['disposition']=='correction'}
expected={(392,'ko'):'소스 파일이 없거나 심볼릭 링크입니다.',(392,'zh-Hans'):'源文件不存在或是符号链接。',(392,'zh-Hant'):'來源檔案不存在或是符號連結。',(399,'hi'):'Sunshine ने इसे अस्वीकार कर दिया: कोई Moonlight क्लाइंट पेयरिंग का इंतज़ार नहीं कर रहा है। पहले अपने क्लाइंट पर पेयरिंग शुरू करें।',(399,'id'):'Sunshine menolak: tidak ada klien Moonlight yang menunggu untuk dipasangkan. Mulai proses pemasangan di klien Anda terlebih dahulu.'}
check(corrections==expected,'five new primary corrections')
new_rows=[r for r in ledger if r['position'] in NEW_POSITIONS]
check(len(new_rows)==48 and sum(r['disposition']=='accept-current' for r in new_rows)==43 and sum(r['disposition']=='correction' for r in new_rows)==5 and not any(r['disposition']=='hold' for r in new_rows),'new semantic review counts')
counts=Counter(r['disposition'] for r in ledger)
check(counts==Counter({'accept-current':214,'correction':22,'refinement':4}),'effective disposition counts')
check(summary['effectiveDecisionCounts']==dict(sorted(counts.items())) and summary['newlyRenderableDispatchCells']==48 and summary['remainingDispatchGapCells']==0,'summary counts')

# Verify the exact dispatch guards through the current sealed caller-context excerpts.
ctx_by_pos={x['position']:x for x in contexts}; context_by_pos=ctx_by_pos
for pos in (396,398,399):
    combined='\n'.join(line['text'] for ref in ctx_by_pos[pos]['callerContextRefs'] for line in ref['contextLines'])
    sid=next(r['sourceId'] for r in ledger if r['position']==pos)
    check(sid in combined and 'detail_source_id' in combined and 'moonlightApiMessageMarkup(' in combined,'fixed source-ID route '+str(pos))
    check('message&&message.source===value' in combined and '?interfaceMarkup(sourceId):apiMessageMarkup(value)' in combined,'exact-source guard/fallback '+str(pos))
combined='\n'.join(line['text'] for ref in ctx_by_pos[392]['callerContextRefs'] for line in ref['contextLines'])
sid=next(r['sourceId'] for r in ledger if r['position']==392)
check(sid in combined and 'ORGANIZER_API_MESSAGE_KEYS' in combined and 'stableLocalizationKey(value)' in combined and '?interfaceMarkup(key):apiMessageMarkup(value,template)' in combined,'organizer allowlist and opaque fallback')

# The 288 predecessor hold rows are copied byte-for-byte.
hold_bytes=(INPUT/'prior-hold-reattestation.jsonl').read_bytes(); copied=(ROOT/'prior-hold-reattestation.jsonl').read_bytes()
check(copied==hold_bytes and len(readjl(ROOT/'prior-hold-reattestation.jsonl'))==288 and sha(copied)==iv['priorHoldBytesSha256']==summary['predecessorHoldSha256'],'288 predecessor holds byte-identical')
check(all(r['targetUnchanged'] and r['sourceMatchesCurrentQueue'] and r['positionMatchesCurrentQueue'] for r in readjl(ROOT/'prior-hold-reattestation.jsonl')),'predecessor hold target/source/rank hashes')
check(m['previousPrimaryRowsReattested']==m['previousCrossAuditRowsReattested']==240 and m['previousCrossAuditResolvedCellsCarriedForward']==192 and m['newlyReviewedCells']==48,'prior review counts')
check(m['priorHoldCellCount']==288 and m['priorHoldTargetsUnchanged'] is True and m['remainingDispatchGapPositions']==[],'manifest reattestation/holds')
check(m['nativeSpeakerApproval']=='not obtained' and summary['nativeSpeakerApproval']=='not obtained','no native-speaker claim')
# Manifest file metadata excludes itself and the checksum list, avoiding a self-hash cycle.
filemeta=m['files']; check(set(filemeta)==actual-{'manifest.json'},'manifest file metadata inventory')
for name,meta in filemeta.items(): check(sha((ROOT/name).read_bytes())==meta['sha256'] and (ROOT/name).stat().st_size==meta['byteCount'],'manifest file metadata '+name)
print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(ledger),'effectiveDispositionCounts':dict(sorted(counts.items())),'priorPrimaryRowsReattested':240,'priorCrossAuditRowsReattested':240,'carriedForward':192,'newlyReviewed':48,'newCorrections':len(corrections),'remainingDispatchGaps':0,'predecessorHoldsUnchanged':288,'tokenMismatches':0,'checksumsVerified':len(checks),'priorPrimaryVerifier':'PASS','priorCrossAuditVerifier':'PASS','candidateFreeVerifier':'PASS','nativeSpeakerApproval':'not obtained'},ensure_ascii=False,indent=2))
