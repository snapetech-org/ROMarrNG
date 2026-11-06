#!/usr/bin/env python3
from pathlib import Path
import collections, hashlib, json, re, subprocess, sys
R=Path(__file__).resolve().parent
BASE='d5ba7f1f268501f45227388c46d5f938ed0c9191'
BASE_TREE='2f8ce1af963b315108f668fc31c94ca90ecd1351'
LATEST='81a499b7c022bde61a63dbd8c68c0b1ca39adf26'
LATEST_TREE='1b075e050610771fc5651d1a4ca95d7c7b4b8e46'
BRANCH='task/localization-translation-review-20261030'
REPO='snapetech-org/ROMarrNG'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PROTECTED=['ROMarr','GG Requestz','RomM','ROMm','ES-DE','gamelist.xml','1G1R','Battle.net','No-Intro','Redump','RetroArch','Steam','EA','Epic','ROM','Hub','DAT']
EXTRA={452:['Flashpoint'],453:['Flood'],458:['ROMarrNG'],461:['EmuDeck']}
TOKEN=re.compile(r'\{[A-Za-z][A-Za-z0-9_]*\}')
NUMBER=re.compile(r'(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])')
def fail(s): raise SystemExit('FAIL: '+s)
def ok(x,s):
    if not x: fail(s)
def sha(b): return hashlib.sha256(b).hexdigest()
def j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def protected(t):
    found=[x for x in PROTECTED if re.search(r'(?<![A-Za-z0-9])'+re.escape(x)+r'(?![A-Za-z0-9])',t)]
    return sorted(found,key=lambda x:t.find(x))
def check_sums(folder, fname='SHA256SUMS.txt', strict=False):
    folder=Path(folder); table={}
    for line in (folder/fname).read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1); ok(n not in table,'duplicate checksum '+n); table[n]=h
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p != folder/fname and not (folder==R and p==folder/"SHA256SUMS.txt.sha256")}
    ok((set(table)==actual) if strict else (set(table)<=actual),'checksum inventory '+str(folder))
    for n,h in table.items(): ok(sha((folder/n).read_bytes())==h,'checksum '+str(folder/n))
    return len(table)
# Root checksums and sidecar.
root_count=check_sums(R,strict=True)
side=(R/'SHA256SUMS.txt.sha256').read_text(encoding='utf-8').strip().split()
ok(side[0]==sha((R/'SHA256SUMS.txt').read_bytes()) and side[-1]=='SHA256SUMS.txt','root checksum sidecar')
manifest=j(R/'packet-manifest.json')
ok(manifest['repository']==REPO and manifest['pullRequest']==70 and manifest['window']=='W445-W464','root identity')
ok(manifest['candidateFreeHead']==BASE and manifest['candidateFreeTree']==BASE_TREE and manifest['latestAttestedHead']==LATEST and manifest['latestAttestedTree']==LATEST_TREE,'root exact pins')
listed={x['path']:x for x in manifest['files']}
nonmanifest={p.relative_to(R).as_posix() for p in R.rglob('*') if p.is_file() and p not in (R/'packet-manifest.json',R/'SHA256SUMS.txt',R/'SHA256SUMS.txt.sha256')}
ok(set(listed)==nonmanifest,'packet manifest inventory')
for n,v in listed.items(): ok(sha((R/n).read_bytes())==v['sha256'] and (R/n).stat().st_size==v['sizeBytes'],'packet manifest pin '+n)
# Preserved nested packet checksums and verifiers.
cf=R/'romarrng-pr70-w445-464-candidate-free-20261103'/'input'
pd=R/'primary-review'; bd=R/'blind-review'; rd=R/'preselection-reattestation'
cf_n=check_sums(cf)
p_n=check_sums(pd); b_n=check_sums(bd); r_n=check_sums(rd)
# Check sidecar for the preselection packet.
rs=(rd/'SHA256SUMS.txt.sha256').read_text().split()
ok(rs[0]==sha((rd/'SHA256SUMS.txt').read_bytes()),'preselection sidecar')
for cmd,cwd,label in [
 (['python3',str(cf/'verify_input.py')],cf,'candidate-free'),
 (['python3',str(pd/'verify_primary.py')],pd,'primary'),
 (['python3',str(bd/'verify_blind_review.py')],bd,'blind'),
 (['python3',str(rd/'verify_reattestation.py')],rd,'preselection reattestation')]:
    v=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
    ok(v.returncode==0,label+' verifier: '+v.stdout+v.stderr)
# Exact current packet identities and signed head attestation.
im=j(cf/'manifest.json'); pm=j(pd/'manifest.json'); bm=j(bd/'manifest.json'); ha=j(rd/'head-reattestation.json'); ba=j(bd/'latest-head-reattestation.json')
ok(im['head']==BASE and im['tree']==BASE_TREE and im['window']=='W445-W464','candidate input pin')
ok(pm['head']==BASE and pm['tree']==BASE_TREE and pm['window']=='W445-W464','primary pin')
ok(bm['head']==LATEST and bm['tree']==LATEST_TREE and 'W445-W464' in bm['purpose'],'blind latest pin')
ok(ha['candidateFreePrimaryBaseHead']==BASE and ha['candidateFreePrimaryBaseTree']==BASE_TREE and ha['latestLiveHead']==LATEST and ha['latestLiveTree']==LATEST_TREE,'preselection head attestation')
ok(ha['reattestationResult']=='PASS' and ha['allChangesConfinedToNewW425W444Evidence'] is True,'preselection result')
ok(len(ha['relevantGitPins'])==10 and all(x['rawBytesMatch'] and x['pinnedShaMatches'] and x['pinnedBlobMatches'] and x['latestShaMatches'] and x['latestBlobMatches'] and x['baseSha256']==x['latestSha256'] and x['baseGitBlob']==x['latestGitBlob'] for x in ha['relevantGitPins']),'relevant source pins')
ok(ba['result']=='PASS' and ba['latestHead']==LATEST and ba['latestTree']==LATEST_TREE and ba['canRelyOnD5CandidateFreeSourceCellInputAtLatestHead'],'blind latest attestation')
ok(ba['sourceCatalogCallerFilesChecked']==9 and ba['sourceDefinitionsChecked']==20 and ba['currentTargetCellsChecked']==240 and ba['callerContextLinesChecked']==319 and ba['uniqueCallerEvidenceLinesChecked']==237 and ba['sourceDefinitionChanges']==0 and ba['currentTargetChanges']==0 and ba['callerLineChanges']==0,'blind source/caller preimage attestation')
actual=j(R/'actual-git-object-reattestation.json')
ok(actual['result']=='PASS' and actual['candidateFreeHead']==BASE and actual['candidateFreeTree']==BASE_TREE and actual['latestHead']==LATEST and actual['latestTree']==LATEST_TREE,'actual Git object reattestation identity')
ok(actual['relevantGitPinsComparedAtBothCommits']==10 and actual['latestPinnedFileComparisonsRecomputed']==9 and actual['sourceDefinitionsAndCurrentTargetPreimagesRecomputed']==240 and actual['callerLineComparisonsRecomputedAtBothCommits']==319 and actual['sourceCatalogCallerDrift'] is False,'actual Git object reattestation counts')
for ap,hp in zip(actual['relevantPins'],ha['relevantGitPins']):
    ok(ap['path']==hp['path'] and ap['unchanged'] and ap['base']['matchesPinnedRawBytes'] and ap['latest']['matchesPinnedRawBytes'] and ap['base']['sha256']==hp['baseSha256'] and ap['latest']['sha256']==hp['latestSha256'] and ap['base']['gitBlob']==hp['baseGitBlob'] and ap['latest']['gitBlob']==hp['latestGitBlob'],'actual Git object pin '+ap['path'])
# Live attestations must be stable and match exact open/draft PR and refs.
live0=j(R/'live-PR-attestation-before.json'); live1=j(R/'live-PR-attestation-after.json')
for label,x in [('before',live0),('after',live1)]:
    ok(x['repository']==REPO and x['pullRequest']==70 and x['state']=='OPEN' and x['isDraft'] is True,label+' PR state')
    ok(x['branch']==BRANCH and x['head']==LATEST and x['tree']==LATEST_TREE,label+' PR pin')
    ok(x['branchRef']==LATEST and x['pullRef']==LATEST,label+' live refs')
    ok(x['baseRefName']=='main' and x['baseRefOid']==ha['prBaseRefOid'],label+' base ref')
    ok(x['baseRefDivergence']['aheadBy']==73 and x['baseRefDivergence']['behindBy']==0 and x['baseRefDivergence']['status']=='ahead','base-ref divergence '+label)
ok(live0['head']==live1['head'] and live0['tree']==live1['tree'] and live0['branchRef']==live1['branchRef'] and live0['pullRef']==live1['pullRef'] and live0['prBodySha256']==live1['prBodySha256'],'live PR stable around seal')
# Verify source pins copied in reattestation match byte and git-blob metadata in the sealed evidence.
for pin in ha['relevantGitPins']:
    p=rd/'pinned-source-blobs'/pin['path']
    ok(p.is_file(),'pinned source blob present '+pin['path'])
    raw=p.read_bytes(); ok(sha(raw)==pin['latestSha256'] and len(raw)==pin['bytes'],'pinned source raw bytes '+pin['path'])
    blob=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    ok(blob==pin['latestGitBlob'],'pinned source git blob '+pin['path'])
# Coverage, exact hashes, target checks, and immutable carried history.
locales=LOCALES
expected=[(p,l) for p in range(445,465) for l in locales]
ledger=jl(R/'cross-audit-ledger.jsonl'); prows=jl(pd/'primary-ledger.jsonl'); brows=jl(bd/'blind-ledger.jsonl'); cells=jl(cf/'current-target-cells.jsonl')
ok(len(ledger)==240 and [(x['position'],x['locale']) for x in ledger]==expected,'cross ledger coverage/order')
ok(len(prows)==240 and len(brows)==240 and len(cells)==240,'input ledger row counts')
cm={(x['position'],x['locale']):x for x in cells}; pm={(x['position'],x['locale']):x for x in prows}; bm={(x['position'],x['locale']):x for x in brows}
sources={x['position']:x for x in jl(cf/'source-inventory-selection.jsonl')}; contexts={x['position']:x for x in jl(cf/'source-contexts.jsonl')}
counts=collections.Counter(); baseline_literal=set()
for x in j(cf/'current-target-protected-literal-mismatches.json')['mismatches']:
    baseline_literal.add((x['position'],x['sourceId'],x['locale']))
for row in ledger:
    key=(row['position'],row['locale']); c=cm[key]; p=pm[key]; b=bm[key]; src=sources[row['position']]; ctx=contexts[row['position']]
    ok(row['sourceId']==c['sourceId']==src['sourceId'] and row['source']==c['source']==src['source'],'source lineage '+str(key))
    ok(row['sourceSha256']==c['sourceSha256']==src['sourceSha256']==sha(row['source'].encode()),'source hash '+str(key))
    ok(row['currentTarget']==c['currentTarget'] and row['currentTargetSha256']==c['currentTargetSha256']==sha(row['currentTarget'].encode()),'current target '+str(key))
    ok(row['catalogTranslationHash']==c['catalogTranslationHash'],'catalog translation pin '+str(key))
    ok(row['sourceContextSha256']==ctx['callerContextSha256'],'caller context hash '+str(key))
    ok([r['path'] for r in row['callerContextRefs']]==[r['path'] for r in ctx['callerContextRefs']],'caller reference path '+str(key))
    ok(row['primaryDisposition']==p['disposition'] and row['primarySelectedTarget']==p['selectedTarget'] and row['blindDisposition']==b['disposition'] and row['blindSelectedTarget']==b['selectedTarget'],'review lineage '+str(key))
    ok(row['selectedTargetSha256']==sha(row['selectedTarget'].encode()),'selected target hash '+str(key))
    ok(row['disposition'] in ('accept-current','correction','refinement','hold'),'valid disposition '+str(key))
    counts[row['disposition']]+=1
    source_ph=TOKEN.findall(row['source']); selected_ph=TOKEN.findall(row['selectedTarget'])
    source_num=NUMBER.findall(row['source']); selected_num=NUMBER.findall(row['selectedTarget'])
    source_terms=protected(row['source']); selected_terms=protected(row['selectedTarget'])
    ch=row['tokenAndLiteralChecks']
    ok(ch['sourcePlaceholderTokens']==source_ph and ch['selectedPlaceholderTokens']==selected_ph and ch['selectedPlaceholderMultisetMatches']==(collections.Counter(source_ph)==collections.Counter(selected_ph)),'placeholder check '+str(key))
    ok(ch['sourceNumericTokens']==source_num and ch['selectedNumericTokens']==selected_num and ch['selectedNumericTokensExactMatch']==(source_num==selected_num),'numeric check '+str(key))
    ok(ch['sourceProtectedLiterals']==source_terms and ch['selectedProtectedLiterals']==selected_terms and ch['selectedProtectedLiteralsPreserved']==all(t in selected_terms for t in source_terms),'protected literal check '+str(key))
    extra=EXTRA.get(row['position'],[])
    ok(ch['additionalNamedTerms']==extra and ch['selectedAdditionalNamedTermsPreserved']==all(re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',row['selectedTarget']) for t in extra),'named product term check '+str(key))
    if row['disposition']=='accept-current': ok(row['selectedTarget']==row['currentTarget'],'accept-current selection '+str(key))
    if row['disposition']=='hold': ok(row['position'] in (458,460,462) and row['selectedTarget']==row['currentTarget'],'hold stays current '+str(key))
    if row['disposition'] in ('correction','refinement'): ok(row['selectedTarget']!=row['currentTarget'],'changed target classification '+str(key))
ok(dict(sorted(counts.items()))=={'accept-current':183,'correction':8,'hold':36,'refinement':13},'cross disposition totals')
ok(baseline_literal=={(461,sources[461]['sourceId'],'pt-BR')},'baseline protected mismatch identity')
ok(all(row['selectedTarget']!='' for row in ledger),'all selected targets present')
# All held rows remain in exactly the callerless positions; the 348 and 60 history attestations are exact.
held=collections.Counter(x['position'] for x in ledger if x['disposition']=='hold')
ok(dict(held)=={458:12,460:12,462:12},'new held positions')
prior_h=jl(cf/'prior-hold-reattestation.jsonl'); prior_s=jl(cf/'prior-selection-reattestation.jsonl')
ok(len(prior_h)==348 and all(x['sourceMatchesCurrentCatalog'] and x['selectionPositionMatches'] and x['targetUnchanged'] for x in prior_h),'carried prior holds')
ok(len(prior_s)==60 and all(x['selectionUnchanged'] for x in prior_s),'carried prior selections')
# Full primary/blind reconciliation checks.
rec=jl(R/'primary-blind-reconciliation.jsonl'); rs=j(R/'reconciliation-summary.json')
ok(len(rec)==58 and rs['primaryBlindRowReconciliationCount']==58,'reconciliation coverage')
ok(rs['primaryBlindDispositionDisagreements']==20 and rs['rawSelectedTargetDifferencesIncludingHoldEncoding']==57 and rs['nonHoldSelectedTargetDisagreements']==21,'reconciliation disagreement counts')
ok(rs['crossAuditCounts']==dict(sorted(counts.items())) and rs['sourceCatalogCallerDrift'] is False and rs['catalogApplied'] is False,'reconciliation summary')
# Root manifest was counted by root checksum; print concise seal result.
print(json.dumps({'result':'PASS','rootFilesCoveredBySha256':root_count,'candidateFreeFilesChecked':cf_n,'primaryFilesChecked':p_n,'blindFilesChecked':b_n,'preselectionFilesChecked':r_n,'crossCells':len(ledger),'reconciliationRows':len(rec),'crossCounts':dict(sorted(counts.items())),'carriedPriorSelections':len(prior_s),'carriedPriorHolds':len(prior_h),'sourceCatalogCallerDrift':False,'latestLiveHead':LATEST,'latestLiveTree':LATEST_TREE},ensure_ascii=False,indent=2))
