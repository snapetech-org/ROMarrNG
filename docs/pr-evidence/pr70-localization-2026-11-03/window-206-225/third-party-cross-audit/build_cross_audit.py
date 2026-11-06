#!/usr/bin/env python3
"""Independent exact-head reconciliation for ROMarrNG PR #70 W206-W225."""
from __future__ import annotations
import collections, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKETS = ROOT / 'source-packets'
INPUT = PACKETS / 'candidate-free-input'
PRIMARY = PACKETS / 'primary-review'
BLIND = PACKETS / 'independent-blind'
EXPECTED = {
    'repo': 'snapetech-org/ROMarrNG',
    'pr': 70,
    'branch': 'task/localization-translation-review-20261030',
    'head': 'bef31ca8a94f21273b11303524d79bd9c5344305',
    'tree': '7616d96ddd3a1bfe8078d43492eb5bea7213f080',
    'window': 'W206-W225',
    'locales': ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant'],
    'positions': list(range(206,226)),
}
PH = re.compile(r'\{[^{}]+\}')
MARKUP = re.compile(r'</?[A-Za-z][^>]*>')

# Where both reviewers proposed different text, this records the third-party selection.
PREFER = {
    (206,'ar'): 'primary',
    (206,'pt-BR'): 'primary',
    (206,'vi'): 'primary',
    (207,'de'): 'primary',
    (207,'vi'): 'blind',
    (208,'ar'): 'blind',
    (208,'es'): 'blind',
    (208,'fr'): 'primary',
    (208,'pt-BR'): 'blind',
    (210,'pt-BR'): 'blind',
    (215,'fr'): 'blind',
    (215,'vi'): 'blind',
    (217,'id'): 'blind',
    (217,'ja'): 'blind',
    (217,'vi'): 'blind',
    (220,'de'): 'primary',
    (220,'id'): 'primary',
    (220,'ko'): 'blind',
    (220,'vi'): 'blind',
    (222,'ja'): 'primary',
    (222,'vi'): 'primary',
    (223,'de'): 'primary',
    (223,'zh-Hans'): 'primary',
    (223,'zh-Hant'): 'primary',
    (224,'ko'): 'primary',
}
CHOICE_NOTES = {
 (206,'ar'): 'Keep the primary diacritic form مُدرج; both proposals preserve the comparison against the latest listed version.',
 (206,'pt-BR'): 'Choose the concise primary wording; both proposals explicitly compare against the latest listed version.',
 (206,'vi'): 'Choose the primary wording trong danh sách; it preserves the source qualifier that the comparison version is listed.',
 (207,'de'): 'Choose Veröffentlichung because this is the release-year sort option; Version could shift the label toward a software version.',
 (207,'vi'): 'Choose the blind noun phrase Bản phát hành mới nhất; the current fragment lacks a clear release noun.',
 (208,'ar'): 'Choose the blind definite superlative as the concise sort-tab label for the newest collection.',
 (208,'es'): 'Choose the blind plural comparative to label the newest games in the library tab.',
 (208,'fr'): 'Choose the primary plural label because this is a tab for a collection of newest games.',
 (208,'pt-BR'): 'Choose the blind plural comparative to label the newest games in the library tab.',
 (210,'pt-BR'): 'Choose no ROMarrNG, which is the more idiomatic Portuguese prepositional phrase for a catalog loaded in the application.',
 (215,'fr'): 'Choose the blind wording: the caller reports no game libraries supplied by a launcher on the machine, so it makes the game-library meaning explicit.',
 (215,'vi'): 'Choose the blind wording because it explicitly identifies game libraries supplied by launchers, avoiding the current startup-library reading.',
 (217,'id'): 'Choose the blind sentence as a natural empty-state message for configured lists.',
 (217,'ja'): 'Choose the blind sentence as a natural empty-state message for configured lists.',
 (217,'vi'): 'Choose the blind sentence as a natural empty-state message for configured lists.',
 (220,'de'): 'Choose the primary concise API error detail; the candidate states that no PIN was supplied.',
 (220,'id'): 'Choose the primary concise error detail; it directly says no PIN was provided.',
 (220,'ko'): 'Choose the blind polite sentence, which gives the missing-PIN detail naturally in a user-facing API response.',
 (220,'vi'): 'Choose the blind wording because it states that no PIN was supplied without the temporal “not yet” implication of Chưa.',
 (222,'ja'): 'Choose the primary wording; it naturally states that no safe canonical title is available.',
 (222,'vi'): 'Choose chuẩn hóa as the closest available rendering of canonical/normalized in this metadata context.',
 (223,'de'): 'Choose the primary wording: no safe renames are ready in this batch; it preserves the source’s readiness sense.',
 (223,'zh-Hans'): 'Choose the primary wording because it explicitly describes safe rename operations ready to execute in this batch.',
 (223,'zh-Hant'): 'Choose the primary wording because it explicitly describes safe rename operations ready to execute in this batch.',
 (224,'ko'): 'Choose the primary exact “no such friend” wording; the blind paraphrase “cannot find the friend” shifts toward a search failure.',
}
HOLD218 = ('The exact callers supply {what} as the English action phrases “browse” and “answer for a date range”. The packet does not establish whether these values are localized before interpolation. The locale grammar depends on that boundary; retain all 12 cells on hold until the interpolation contract is verified or the text is redesigned to avoid the unresolved insertion.')


def fail(msg: str) -> None:
    raise SystemExit('REFUSED: ' + msg)
def sha(data: bytes|str) -> str:
    return hashlib.sha256(data.encode('utf-8') if isinstance(data,str) else data).hexdigest()
def read_json(path: Path): return json.loads(path.read_text(encoding='utf-8'))
def read_jsonl(path: Path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]
def write_json(path: Path, val): path.write_text(json.dumps(val,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write_jsonl(path: Path, rows): path.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf-8')
def verify_manifest(d: Path) -> int:
    path=d/'SHA256SUMS.txt'; count=0
    for line in path.read_text(encoding='utf-8').splitlines():
        digest, rel=line.split(maxsplit=1); rel=rel.lstrip('*').strip()
        file=d/rel
        if not file.is_file() or sha(file.read_bytes())!=digest: fail(f'packet checksum mismatch {file}')
        count+=1
    return count
def ph(s): return sorted(PH.findall(s))
def markup(s): return sorted(MARKUP.findall(s))
def refpins(refs): return sorted((x['contextSha256'],x['path'],x['startLine'],x['endLine']) for x in refs)

# All three packet checksums are revalidated before reading decisions.
manifest_entries={
 'input': verify_manifest(INPUT),
 'primary': verify_manifest(PRIMARY),
 'blind': verify_manifest(BLIND),
}
im=read_json(INPUT/'manifest.json')
p_summary=read_json(PRIMARY/'summary.json')
b_summary=read_json(BLIND/'summary.json')
if (im['repository'],im['pullRequest'],im['head'],im['tree'],im['window']) != (EXPECTED['repo'],EXPECTED['pr'],EXPECTED['head'],EXPECTED['tree'],EXPECTED['window']): fail('input exact pin mismatch')
for label,s in [('primary',p_summary),('blind',b_summary)]:
    head=s.get('head',s.get('inputHead')); tree=s.get('tree',s.get('inputTree'))
    if s.get('repository')!=EXPECTED['repo'] or s.get('pullRequest')!=EXPECTED['pr'] or head!=EXPECTED['head'] or tree!=EXPECTED['tree'] or s.get('window') not in (EXPECTED['window'],[206,225]):
        fail(f'{label} summary pin mismatch')

# Recheck live draft PR, branch, remote head, and GitHub commit tree.
pr_live=read_json(ROOT/'live-pr.json')
if (pr_live['state'],pr_live['isDraft'],pr_live['baseRefName'],pr_live['headRefName'],pr_live['headRefOid']) != ('OPEN',True,'main',EXPECTED['branch'],EXPECTED['head']): fail('live PR no longer matches expected exact head')
remote=(ROOT/'live-remote-head.txt').read_text().strip().split()
if len(remote)!=2 or remote[0]!=EXPECTED['head'] or remote[1]!=f"refs/heads/{EXPECTED['branch']}": fail('remote branch head mismatch')
tree=(ROOT/'live-pr-tree.txt').read_text().strip()
if tree!=EXPECTED['tree']: fail('live commit tree mismatch')
write_json(ROOT/'live-pr-verification.json',{
 'verification':'passed','repository':EXPECTED['repo'],'pullRequest':EXPECTED['pr'],
 'state':pr_live['state'],'isDraft':pr_live['isDraft'],'baseRefName':pr_live['baseRefName'],
 'headRefName':pr_live['headRefName'],'headRefOid':pr_live['headRefOid'],
 'remoteBranch':EXPECTED['branch'],'remoteBranchHead':remote[0],'tree':tree,
 'candidateFreeInputHead':im['head'],'candidateFreeInputTree':im['tree']})

cells=read_jsonl(INPUT/'current-target-cells.jsonl')
contexts=read_jsonl(INPUT/'source-contexts.jsonl')
primary=read_jsonl(PRIMARY/'primary-decisions.jsonl')
blind=read_jsonl(BLIND/'blind-ledger.jsonl')
if any(len(x)!=240 for x in (cells,primary,blind)): fail('not exactly 240 rows in an input/review packet')
locales=EXPECTED['locales']
key=lambda r:(r['position'],r['locale'])
for name,rows in [('input',cells),('primary',primary),('blind',blind)]:
    if len({key(r) for r in rows})!=240: fail(f'{name} duplicate/missing cells')
ci={key(r):r for r in cells}; pi={key(r):r for r in primary}; bi={key(r):r for r in blind}
ctx={r['position']:r for r in contexts}
if sorted(ctx)!=EXPECTED['positions']: fail('context positions do not match window')
if sorted(set(r['position'] for r in cells))!=EXPECTED['positions']: fail('cell positions do not match window')
if sorted(set(r['locale'] for r in cells),key=locales.index)!=locales: fail('locale roster mismatch')

catalog_pins=read_json(INPUT/'catalog-file-pins.json')['clientCatalog']
if catalog_pins['path']!='romarr/ui-labels.json' or catalog_pins['gitBlob']!='791f41e3c0e9ac3713dd54468ef6125b8f0eabbc': fail('catalog pin does not match packet')
source_counts=collections.Counter(); caller_ref_pins=set()
proposal_p=proposal_b=both_propose=exact_same=different=only_p=only_b=0
same_candidates=[]; disagreements=[]; audit=[]; holds=[]
change_by_locale=collections.Counter(); change_by_position=collections.Counter()
protected_counts=collections.Counter(); placeholder_checks=markup_checks=protected_checks=0

for c in sorted(cells,key=lambda x:(x['position'],locales.index(x['locale']))):
    k=key(c); pos,loc=k; p=pi[k]; b=bi[k]; cx=ctx[pos]
    if pos not in EXPECTED['positions'] or c['repository']!=EXPECTED['repo'] or c['pullRequest']!=EXPECTED['pr'] or c['head']!=EXPECTED['head'] or c['tree']!=EXPECTED['tree'] or c['window']!=EXPECTED['window']: fail(f'input per-cell pin mismatch {k}')
    if c['sourceId']!=cx['sourceId'] or c['source']!=cx['source'] or c['sourceSha256']!=cx['sourceSha256'] or c['sourceCallerCount']!=cx['callerReferenceCount']: fail(f'input/context mismatch {k}')
    if sha(c['source'])!=c['sourceSha256'] or sha(c['currentTarget'])!=c['currentTargetSha256']: fail(f'input source/current hash mismatch {k}')
    if c['catalogPath']!=catalog_pins['path'] or c['catalogGitBlob']!=catalog_pins['gitBlob'] or c['catalogSha256']!=catalog_pins['sha256']: fail(f'catalog pin mismatch {k}')
    for label,r in [('primary',p),('blind',b)]:
        if r['source']!=c['source'] or r['sourceId']!=c['sourceId'] or r['sourceSha256']!=c['sourceSha256'] or r['currentTarget']!=c['currentTarget'] or r['currentTargetSha256']!=c['currentTargetSha256']: fail(f'{label} source/current mismatch {k}')
        if r.get('repository',EXPECTED['repo'])!=EXPECTED['repo'] or r.get('pullRequest',EXPECTED['pr'])!=EXPECTED['pr'] or r.get('head',EXPECTED['head'])!=EXPECTED['head'] or r.get('tree',EXPECTED['tree'])!=EXPECTED['tree'] or r.get('window') not in (EXPECTED['window'],[206,225]): fail(f'{label} row exact pin mismatch {k}')
    refs=cx['references']
    caller_ref_pins.update((x['contextSha256'],x['path'],x['startLine'],x['endLine']) for x in refs)
    input_refs=refpins(refs)
    ppins=sorted((x['contextSha256'],x['path'],x['startLine'],x['endLine']) for x in p['callerContextPins'])
    bpins=refpins(b['callerContext']['references'])
    if ppins!=input_refs or bpins!=input_refs: fail(f'caller context references differ across packets {k}')
    if p['callerContextPins'] and any(x['contextSha256'] not in [y['contextSha256'] for y in refs] for x in p['callerContextPins']): fail(f'primary caller context hash mismatch {k}')
    if b['callerContext']['callerReferenceCount']!=cx['callerReferenceCount']: fail(f'blind caller count mismatch {k}')
    if b['callerContext']['contextRowSha256'] is None: fail(f'blind caller row hash missing {k}')
    source=c['source']; current=c['currentTarget']
    source_ph=ph(source); current_ph=ph(current); source_markup=markup(source); current_markup=markup(current)
    if source_ph!=current_ph or source_markup!=current_markup: fail(f'source/current structural mismatch {k}')
    p_target=p['proposedTarget'] if p['proposalType'] else None
    if p['disposition']=='hold' or p['disposition']=='accept-current': p_target=None
    b_target=b['candidateTarget'] if b['decision'] in ('correction','refinement') else None
    if b['decision'] in ('hold','accept-current'): b_target=None
    if p_target is not None:
        if sha(p_target)!=p['proposedTargetSha256'] or p_target==current: fail(f'primary proposed target hash/no-op mismatch {k}')
    if b_target is not None:
        if sha(b_target)!=b['candidateTargetSha256'] or b['selectedTarget']!=b_target or b_target==current: fail(f'blind candidate hash/selected/no-op mismatch {k}')
    # Placeholder, markup, and protected-literal checks on source/current and both reviewer targets.
    expected_literals=p['protectedLiteralsRequired']
    if expected_literals!=b['integrityChecks']['protectedLiteralsRequired']: fail(f'protected-literal inventories differ {k}')
    if sorted(expected_literals)!=sorted(set(expected_literals)): fail(f'duplicate protected literal declaration {k}')
    for lit in expected_literals:
        if source.count(lit)==0: fail(f'protected literal not in source {k}: {lit}')
        protected_counts[lit]+=1
        for label,target in [('current',current),('primary',p_target if p_target is not None else current),('blind',b_target if b_target is not None else current)]:
            if target.count(lit)!=source.count(lit): fail(f'{label} protected literal count mismatch {k}: {lit}')
        protected_checks+=1
    for label,target in [('current',current),('primary',p_target if p_target is not None else current),('blind',b_target if b_target is not None else current)]:
        if ph(target)!=source_ph: fail(f'{label} placeholder multiset mismatch {k}')
        if markup(target)!=source_markup: fail(f'{label} markup mismatch {k}')
    if sorted(p['placeholderChecks']['expected'])!=source_ph or sorted(p['placeholderChecks']['current'])!=current_ph or sorted(p['placeholderChecks']['reviewTarget'])!=source_ph or not p['placeholderChecks']['reviewTargetExactMultisetMatch']: fail(f'primary placeholder evidence mismatch {k}')
    if sorted(b['integrityChecks']['sourcePlaceholders'])!=sorted(x[1:-1] for x in source_ph) or sorted(b['integrityChecks']['selectedPlaceholders'])!=sorted(x[1:-1] for x in ph(b['selectedTarget'])) or not b['integrityChecks']['placeholderParity']: fail(f'blind placeholder evidence mismatch {k}')
    if b['integrityChecks']['sourceMarkupTags']!=source_markup or b['integrityChecks']['selectedMarkupTags']!=markup(b['selectedTarget']) or not b['integrityChecks']['markupParity']: fail(f'blind markup evidence mismatch {k}')
    placeholder_checks+=1; markup_checks+=1; source_counts[pos]+=1
    proposal_p += p_target is not None
    proposal_b += b_target is not None
    both= p_target is not None and b_target is not None
    both_propose += both
    if both and p_target==b_target: exact_same+=1
    elif both: different+=1
    elif p_target is not None: only_p+=1
    elif b_target is not None: only_b+=1

    p_action = 'hold' if p['disposition']=='hold' else ('propose' if p_target is not None else 'accept-current')
    b_action = 'hold' if b['decision']=='hold' else ('propose' if b_target is not None else 'accept-current')
    if p_action!=b_action or p_target!=b_target:
        disagreements.append({'position':pos,'locale':loc,'sourceId':c['sourceId'],'source':source,'currentTarget':current,
          'primaryAction':p_action,'primaryTarget':p_target,'primaryDisposition':p['disposition'],'primaryRationale':p['rationale'],
          'blindAction':b_action,'blindTarget':b_target,'blindDisposition':b['decision'],'blindRationale':b['rationale'],
          'thirdPartySelected':PREFER.get(k),'selectionRationale':CHOICE_NOTES.get(k)})
    if pos==218:
        if p['disposition']!='hold' or b['decision']!='hold' or p_target is not None or b_target is not None: fail('rank 218 is not held by both reviews')
        disposition='hold'; chosen=None; selected='hold'; rationale=HOLD218; hold_reason=HOLD218
    else:
        if p_target is not None and b_target is not None:
            if p_target==b_target:
                chosen=p_target; selected='primary+blind'
                disposition=(p['proposalType'] if p['proposalType'] else b['decision'])
                rationale='Both independent reviews propose the same target. The exact pinned caller supports this usage; the chosen string passes placeholder, markup, and protected-literal checks.'
            else:
                pref=PREFER.get(k)
                if pref not in ('primary','blind'): fail(f'no explicit adjudication for competing proposals {k}')
                chosen=p_target if pref=='primary' else b_target
                selected=pref
                disposition=p['proposalType'] if pref=='primary' else b['decision']
                rationale=CHOICE_NOTES.get(k) or (p['rationale'] if pref=='primary' else b['rationale'])
        elif p_target is not None:
            chosen=p_target; selected='primary'; disposition=p['proposalType']
            rationale='Select the primary proposal: '+p['rationale']
        elif b_target is not None:
            chosen=b_target; selected='blind'; disposition=b['decision']
            rationale='Select the blind proposal: '+b['rationale']
        else:
            chosen=None; selected='current'; disposition='accept-current'
            rationale='Both reviewers retain the current value. The pinned caller supports its source meaning, and structural/protected-literal checks pass.'
        hold_reason=None
    effective=chosen if chosen is not None else current
    if chosen is not None:
        for lit in expected_literals:
            if chosen.count(lit)!=source.count(lit): fail(f'third-party target protected literal mismatch {k}: {lit}')
        if ph(chosen)!=source_ph or markup(chosen)!=source_markup: fail(f'third-party target structure mismatch {k}')
        change_by_locale[loc]+=1; change_by_position[str(pos)]+=1
    row={
      'window':EXPECTED['window'],'position':pos,'sourceId':c['sourceId'],'source':source,'sourceSha256':c['sourceSha256'],
      'locale':loc,'currentTarget':current,'currentTargetSha256':c['currentTargetSha256'],
      'catalogPath':c['catalogPath'],'catalogGitBlob':c['catalogGitBlob'],'catalogSha256':c['catalogSha256'],
      'callerEvidence':{'referenceCount':cx['callerReferenceCount'],'sourceIndexLocations':cx['sourceIndexLocations'],
          'references':refs,'primaryPinsMatch':True,'blindPinsMatch':True},
      'primaryRecommendation':{'disposition':p['disposition'],'proposalType':p['proposalType'],'proposedTarget':p_target,
          'proposedTargetSha256':p.get('proposedTargetSha256'),'rationale':p['rationale'],'confidence':p['confidence']},
      'blindRecommendation':{'disposition':b['decision'],'candidateTarget':b_target,
          'candidateTargetSha256':b.get('candidateTargetSha256'),'rationale':b['rationale'],'confidence':b['confidence']},
      'crossChecks':{'sourceCurrentPlaceholderTokens':{'source':source_ph,'current':current_ph,'parity':source_ph==current_ph},
          'primaryPlaceholderParity':ph(p_target if p_target is not None else current)==source_ph,
          'blindPlaceholderParity':ph(b_target if b_target is not None else current)==source_ph,
          'sourceCurrentMarkupTags':{'source':source_markup,'current':current_markup,'parity':source_markup==current_markup},
          'primaryMarkupParity':markup(p_target if p_target is not None else current)==source_markup,
          'blindMarkupParity':markup(b_target if b_target is not None else current)==source_markup,
          'protectedLiteralChecks':[{'literal':lit,'sourceOccurrences':source.count(lit),'currentPreserved':current.count(lit)==source.count(lit),
             'primaryPreserved':(p_target if p_target is not None else current).count(lit)==source.count(lit),
             'blindPreserved':(b_target if b_target is not None else current).count(lit)==source.count(lit),
             'thirdPartyPreserved':effective.count(lit)==source.count(lit)} for lit in expected_literals]},
      'thirdPartyRecommendation':{'disposition':disposition,'proposedTarget':chosen,'effectiveTargetIfApplied':effective,
          'selectedFrom':selected,'rationale':rationale,'holdReason':hold_reason,'machineAssisted':True,'nativeSpeakerApproval':False},
    }
    audit.append(row)
    if disposition=='hold': holds.append({'position':pos,'locale':loc,'sourceId':c['sourceId'],'source':source,'currentTarget':current,'holdReason':hold_reason,
       'whatValuesAtPinnedCallers':['browse','answer for a date range'],'callerRefs':refs})

caller_refs_total=len(caller_ref_pins)
if len(audit)!=240 or sum(source_counts.values())!=240 or caller_refs_total!=26: fail('aggregate row/caller count mismatch')
if proposal_p!=25 or proposal_b!=30: fail('proposal counts changed')
if len(holds)!=12 or any(h['position']!=218 for h in holds): fail('unexpected or missing holds')
write_jsonl(ROOT/'cross-audit-ledger.jsonl',audit)
write_jsonl(ROOT/'primary-blind-disagreements.jsonl',disagreements)
write_jsonl(ROOT/'holds.jsonl',holds)
write_json(ROOT/'protected-literal-audit.json',{
 'sourceCellCountsByLiteral':dict(sorted(protected_counts.items())),
 'primaryCandidateViolations':0,'blindCandidateViolations':0,'thirdPartyTargetViolations':0,
 'note':'Exact protected substrings were counted as occurrences so locale suffixes do not create false boundary failures.'})
summary={
 'reviewType':'third-party semantic and structural cross-audit of exact-head ROMarrNG PR #70 W206-W225',
 'repository':EXPECTED['repo'],'pullRequest':EXPECTED['pr'],'pullRequestUrl':'https://github.com/snapetech-org/ROMarrNG/pull/70',
 'state':'OPEN','isDraft':True,'branch':EXPECTED['branch'],'exactHead':EXPECTED['head'],'remoteBranchHead':remote[0],'exactTree':EXPECTED['tree'],
 'window':EXPECTED['window'],'sourceCount':20,'localeCount':12,'cellCount':240,'callerReferencesVerified':caller_refs_total,
 'verifiedManifestEntries':manifest_entries,
 'inputManifestSha256':sha((INPUT/'manifest.json').read_bytes()),'inputChecksumListSha256':sha((INPUT/'SHA256SUMS.txt').read_bytes()),
 'primaryChecksumListSha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),'blindChecksumListSha256':sha((BLIND/'SHA256SUMS.txt').read_bytes()),
 'primaryProposedChangeCells':proposal_p,'blindProposedChangeCells':proposal_b,'bothProposeCells':both_propose,
 'identicalProposalTextCells':exact_same,'differentProposalTextCells':different,'primaryOnlyProposalCells':only_p,'blindOnlyProposalCells':only_b,
 'primaryBlindRecommendationDisagreementRows':len(disagreements),'differentProposalTextCells':different,'thirdPartyRecommendedChanges':sum(change_by_locale.values()),
 'thirdPartyChangesByLocale':dict(change_by_locale),'thirdPartyChangesByPosition':dict(sorted(change_by_position.items(),key=lambda x:int(x[0]))),
 'thirdPartyHolds':len(holds),'holdsByPosition':dict(collections.Counter(str(h['position']) for h in holds)),
 'thirdPartyDispositions':dict(collections.Counter(r['thirdPartyRecommendation']['disposition'] for r in audit)),
 'placeholderCheckCount':placeholder_checks,'markupCheckCount':markup_checks,'protectedLiteralOccurrenceChecks':protected_checks,
 'primaryPlaceholderMismatchCount':0,'blindPlaceholderMismatchCount':0,'thirdPartyPlaceholderMismatchCount':0,
 'primaryMarkupMismatchCount':0,'blindMarkupMismatchCount':0,'thirdPartyMarkupMismatchCount':0,
 'protectedLiteralViolationCount':0,'rank218Boundary':'hold all locales; callers pass English what values, interpolation localization contract is not established',
 'nativeSpeakerApproval':False,'browserAcceptance':False,'repositoryOrPRChanged':False,'testsBuildsScansCIWorkflowOrBrowserWork':False,
 'importantSelectionNotes':{f'{pos}:{loc}':note for (pos,loc),note in CHOICE_NOTES.items()},
}
write_json(ROOT/'cross-audit-summary.json',summary)
print(json.dumps(summary,ensure_ascii=False,indent=2))
