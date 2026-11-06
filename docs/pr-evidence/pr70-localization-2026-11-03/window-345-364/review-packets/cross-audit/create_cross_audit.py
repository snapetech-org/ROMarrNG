#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

SCRATCH=Path('/home/keith/Documents/code/task-scratch')
INPUT=SCRATCH/'romarrng-pr70-w345-364-primary-20261103'/'input'
PRIMARY=SCRATCH/'romarrng-pr70-w345-364-primary-20261103'/'primary-review'
BLIND=SCRATCH/'romarrng-pr70-w345-364-blind-20261103'/'blind-review'
REPO=SCRATCH/'romarrng-pr70-w325-344-apply-20261103'/'repo'
OUT=Path(__file__).resolve().parent
HEAD='6bef0c74632067906fd07279fa6bd3fd59159a48'
TREE='4fd79e67f37e4c66d0253199418973d965a3fbd6'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def jread(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(data): return hashlib.sha256(data).hexdigest()
def fsha(p): return sha(p.read_bytes())
def run(args): return subprocess.check_output(args,text=True).strip()
def idx(p):
    rows=jl(p); d={(x['position'],x['locale']):x for x in rows}; assert len(d)==len(rows); return d

def verify_sum_file(folder):
    for line in (folder/'SHA256SUMS.txt').read_text().splitlines():
        digest,name=line.split('  ',1); assert fsha(folder/name)==digest,(folder/name)

manifest=jread(INPUT/'manifest.json')
assert manifest['head']==HEAD and manifest['tree']==TREE and manifest['window']=='W345-W364'
assert manifest['cellCount']==240 and manifest['candidateFree'] and not manifest['proposedTargetsIncluded']
assert manifest['priorHoldCellCount']==288 and manifest['priorHoldTargetsUnchanged']
assert manifest['translationDispatchGapPositions']==[346,350]
for folder in (INPUT,PRIMARY,BLIND): verify_sum_file(folder)

# Live exact-head readback and a clean local pinned worktree.
pr=json.loads(run(['gh','api','repos/snapetech-org/ROMarrNG/pulls/70']))
branch=json.loads(run(['gh','api','repos/snapetech-org/ROMarrNG/git/ref/heads/task/localization-translation-review-20261030']))
repo_head=run(['git','-C',str(REPO),'rev-parse','HEAD'])
repo_tree=run(['git','-C',str(REPO),'rev-parse','HEAD^{tree}'])
repo_status=run(['git','-C',str(REPO),'status','--porcelain'])
assert pr['state']=='open' and pr['draft'] is True and pr['head']['sha']==HEAD
assert pr['head']['ref']=='task/localization-translation-review-20261030' and branch['object']['sha']==HEAD
assert repo_head==HEAD and repo_tree==TREE and not repo_status

current=idx(INPUT/'current-target-cells.jsonl')
primary=idx(PRIMARY/'review-decisions.jsonl')
blind=idx(BLIND/'blind-ledger.jsonl')
contexts={x['position']:x for x in jl(INPUT/'source-contexts.jsonl')}
keys=[(p,l) for p in range(345,365) for l in LOCALES]
assert set(current)==set(primary)==set(blind)==set(keys) and len(contexts)==20
holds=jl(INPUT/'prior-hold-reattestation.jsonl')
assert len(holds)==288 and all(x['targetUnchanged'] and x['currentTargetSha256']==x['priorCurrentTargetSha256'] for x in holds)

# Explicit cell-level selection for every target disagreement. The target-equal cases use both reviews.
P=set(); B=set()
def add(dst,pos,locales): dst.update((pos,l) for l in locales)
add(P,346,['es','hi']); add(P,347,['fr','hi'])
add(P,348,['ja','ko','pt-BR','vi','zh-Hant']); add(P,349,['hi','pt-BR'])
add(P,351,['ar','es','pt-BR']); add(P,352,['de','hi','id','zh-Hans','zh-Hant'])
add(P,353,['ar']); add(P,354,['hi'])
add(P,357,['de','es','hi','id','ko','pt-BR','zh-Hans','zh-Hant'])
add(P,359,LOCALES); add(P,360,LOCALES); add(P,362,['de','fr','zh-Hans','zh-Hant'])
add(B,345,['hi']); add(B,346,['zh-Hans','zh-Hant']); add(B,347,['es','vi'])
add(B,349,['id','vi']); add(B,350,['ar','de','es','fr','hi','id','ko','pt-BR','vi'])
add(B,351,['zh-Hant']); add(B,353,['pt-BR']); add(B,354,['zh-Hant'])
add(B,355,['de','pt-BR']); add(B,356,LOCALES); add(B,358,['ar','de','id','zh-Hant'])
add(B,361,['hi']); add(B,362,['hi']); add(B,363,['ar','id','ja','ko','vi','zh-Hans','zh-Hant'])
target_diffs={k for k in keys if primary[k]['selectedTarget']!=blind[k]['blindTarget']}
assert target_diffs==P|B and not(P&B) and len(target_diffs)==103,(len(target_diffs),len(P|B),sorted(target_diffs-(P|B)),sorted((P|B)-target_diffs))

context_reason={
345:'The exact caller is the organizer terminal-state label and announcement; wording should indicate that scanning is complete.',
346:'The exact caller is the local-launcher scan error toast; preserve the failed-scan meaning and the {error_type} placeholder.',
347:'The exact caller is the organizer failed-state label and announcement; use a concise failed state and scan-specific wording.',
348:'The caller is the organizer Scan library button for the configured collection of game files. The glossary defines Library as the user game-file collection, so game-library wording avoids public-library ambiguity.',
349:'The exact caller is the organizer partial-completion state; preserve a safety threshold rather than implying a security boundary.',
350:'The exact caller is the TOTP enrollment note displayed beside the secret, URI, and backup codes; preserve enrollment steps, sign-in prompts, and one-time backup-code use.',
351:'The exact caller is the response to publishing an ES-DE gamelist before scanning the platform; a direct instruction to scan first fits the action and preserves ES-DE.',
352:'The exact caller is the organizer in-progress state; use a progressive form rather than an isolated noun or infinitive.',
353:'The exact caller is the accessible name for the patch-project search field; use a search label and localize Patch.',
354:'The exact caller is the platform-filter placeholder; phrase it as a search action and use the locale’s standard script.',
355:'The exact caller is both the screen-reader label and placeholder for plugin search; choose natural search-field wording.',
356:'The caller is the scheduled MissingGameSearch task, which searches the user’s Wanted queue of desired/missing games. The label should mean searching within that queue, not searching for a list.',
357:'The exact caller is the catalog-query placeholder; make the catalog the search scope rather than the object being searched for.',
358:'The exact caller is the visible label for the catalog title-query input; use a natural search instruction for titles.',
359:'The task-result caller loops over Wanted entries. “Searched” counts those entries; “grabbed” increments only when the request reports success, meaning a release was accepted by the download client. Skipped entries remain in retry backoff. Do not imply downloads have completed.',
360:'The task-result caller loops over Wanted entries. “Searched” counts those entries; “grabbed” increments only when the request reports success, meaning a release was accepted by the download client. Do not imply downloads have completed.',
361:'The exact caller labels the TOTP enrollment secret shown before the URI and backup codes.',
362:'The exact caller is a details summary that reveals blocked rows in the rename preview; a show/view verb and UI-appropriate term for entries fit this control.',
363:'The exact caller is the SeerrNG integration-guide link under text naming ROMarrNG and SeerrNG; explicit app/service references remove the ambiguous pronoun.',
364:'The exact caller is the SeerrNG discovery link in list navigation; preserve the product name and concise link-label meaning.'}
special_reason={
(345,'hi'):'The blind proposal makes the completed state explicit; the current progressive wording can sound ongoing.',
(345,'id'):'Both reviews localize “Scan” and replace the current mixed English-Indonesian state label.',
(346,'es'):'The primary proposal states that the scan failed; the alternative can read as an error occurring during the action.',
(346,'hi'):'The primary proposal is a concise failed-state label rather than a progressive “scanning” form.',
(346,'zh-Hans'):'The blind proposal uses a full-width Chinese colon and preserves the placeholder.',
(346,'zh-Hant'):'The blind proposal uses a full-width Chinese colon and preserves the placeholder.',
(347,'es'):'The blind proposal uses the common technical failure verb instead of the current stronger, less idiomatic “fracasó”.',
(347,'fr'):'The primary proposal is scan-specific; “analyse” can suggest analysis rather than the scan operation.',
(347,'vi'):'The blind proposal translates “Scan” instead of retaining the English source word.',
(348,'pt-BR'):'The primary proposal explicitly says “biblioteca de jogos”, making the game-file collection clear on the button.',
(348,'zh-Hant'):'The primary “遊戲庫” matches the glossary; “媒體庫” broadens the meaning to a media library.',
(349,'id'):'“Batas aman” conveys a safety threshold; “batas keamanan” can suggest a security boundary.',
(349,'pt-BR'):'The primary uses “varredura” for the scan operation rather than “verificação”.',
(349,'vi'):'The blind proposal translates the scan verb instead of leaving English “Scan”.',
(350,'fr'):'The blind proposal has grammatical “l’URI” and explicit sign-in and one-time-use instructions.',
(350,'es'):'The blind proposal uses a direct imperative and specifies when sign-in codes are requested.',
(350,'ko'):'The blind proposal gives direct instructions and clearly says backup codes work once.',
(351,'zh-Hant'):'The blind proposal uses natural Traditional Chinese wording and character forms.',
(352,'de'):'“Scan läuft” is a concise status that clearly indicates an ongoing operation.',
(352,'id'):'“Sedang memindai” marks the scan as currently in progress.',
(352,'pt-BR'):'The shared gerund “Escaneando” indicates an active scan; the current noun does not.',
(353,'pt-BR'):'“Pesquisar projetos de patches” is natural Brazilian Portuguese field wording.',
(354,'zh-Hant'):'“搜尋平台” is the standard Traditional Chinese search verb.',
(355,'de'):'“Plugins suchen” is the natural German search-field label.',
(355,'pt-BR'):'“Pesquisar plugins” is natural Brazilian Portuguese accessible-label wording.',
(358,'ar'):'The blind proposal is a direct search instruction for the visible title-input label.',
(358,'de'):'“Titel durchsuchen” is natural for the title-search input label.',
(358,'id'):'“Cari judul” is a natural action label for the title-search input.',
(358,'zh-Hant'):'The blind proposal uses the Traditional Chinese search verb “搜尋”.',
(361,'hi'):'The blind proposal’s “secret key” clarifies that this value is the TOTP enrollment key.',
(362,'de'):'“Anzeigen” matches a details summary that reveals the blocked rows.',
(362,'hi'):'The blind proposal has correct feminine agreement and a natural word for blocked items.'}

catalog_pin=jread(INPUT/'catalog-file-pins.json')['files']['romarr/ui-labels.json']
ledger=[]
for pos,loc in keys:
    c= current[pos,loc]; p=primary[pos,loc]; b=blind[pos,loc]; ctx=contexts[pos]
    assert c['sourceId']==p['sourceId']==b['sourceId']==ctx['sourceId']
    assert c['sourceSha256']==p['sourceSha256']==b['sourceSha256']==ctx['sourceSha256']
    assert c['currentTarget']==p['currentTarget']==b['currentTarget']
    assert c['currentTargetSha256']==p['currentTargetSha256']==b['currentTargetSha256']
    assert c['callerContextSha256']==p['callerContextSha256']==b['callerContextSha256']==ctx['callerContextSha256']
    pt=p['selectedTarget']; bt=b['blindTarget']; ct=c['currentTarget']
    if pt==bt: selected,origin=pt,'primary+blind'
    elif (pos,loc) in P: selected,origin=pt,'primary'
    elif (pos,loc) in B: selected,origin=bt,'blind'
    else: raise AssertionError(('unresolved',pos,loc))
    if selected==ct: disposition='accept-current'
    elif origin=='primary': disposition=p['decision']
    elif origin=='blind': disposition=b['disposition']
    else: disposition='correction' if 'correction' in (p['decision'],b['disposition']) else 'refinement'
    if (pos,loc) in special_reason: why=special_reason[pos,loc]
    elif pt!=bt: why=('Selected primary wording. ' if origin=='primary' else 'Selected blind wording. ')+context_reason[pos]
    elif selected==ct: why='Both reviews retain the current text. '+context_reason[pos]
    else: why='Both reviews select the same changed text. '+context_reason[pos]
    if pos in (346,350):
        why += ' Text-quality review only: the app-authored message still goes through apiMessageMarkup as opaque text, so a separate source-bound runtime dispatch fix remains required. This audit changes no source, caller, or pin.'
    resolution='proposal-target-disagreement-adjudicated' if pt!=bt else ('shared-target-disposition-adjudicated' if p['decision']!=b['disposition'] else 'independent-review-agreement')
    placeholder=re.compile(r'\{[^{}]+\}')
    checks={
      'markupTokensMatch':collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',c['source']))==collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',selected)),
      'numericTokensPreserved':all(str(x) in selected for x in c['sourceNumericTokens']),
      'placeholdersMatch':collections.Counter(placeholder.findall(c['source']))==collections.Counter(placeholder.findall(selected)),
      'protectedLiteralsPreserved':all(str(x) in selected for x in c['sourceProtectedLiterals'])}
    assert all(checks.values()),(pos,loc,checks,c['sourceProtectedLiterals'],selected)
    assert sha(ct.encode())==c['currentTargetSha256'] and sha(pt.encode())==p['selectedTargetSha256'] and sha(bt.encode())==b['blindTargetSha256']
    follow=None
    if pos==346:
      follow={'required':True,'scope':'Separate source-bound runtime localization fix; this audit changes no source or caller pins.','appSourceRef':'romarr/app.py:5245-5260','uiCallerRef':'romarr/ui.py:2789-2797','opaqueRendererRef':'romarr/ui.py:1042-1049; 1609-1611','dispatch':'toastAppMessage(r.error) -> apiMessageMarkup without an explicit catalog template','catalogDecision':'Text-quality only; current opaque path does not expose catalog translations.'}
    elif pos==350:
      follow={'required':True,'scope':'Separate source-bound runtime localization fix; this audit changes no source or caller pins.','appSourceRef':'romarr/app.py:7503-7518','uiCallerRef':'romarr/ui.py:4551-4560','opaqueRendererRef':'romarr/ui.py:1042-1049','dispatch':'apiMessageMarkup(d.note||\'\') displays this app-authored note as opaque text','catalogDecision':'Text-quality only; current opaque path does not expose catalog translations.'}
    ledger.append({
      'blindDisposition':b['disposition'],'blindRationale':b['rationale'],'blindTarget':bt,'blindTargetSha256':b['blindTargetSha256'],
      'callerContextRefs':ctx['callerContextRefs'],'callerContextSha256':ctx['callerContextSha256'],'callerResolutionHold':ctx['callerResolutionHold'],
      'catalogFileSha256':catalog_pin['sha256'],'catalogGitBlob':catalog_pin['gitBlob'],'catalogPath':c['catalogPath'],'catalogTranslationHash':c['catalogTranslationHash'],
      'confidence':'moderate','crossAuditDisposition':disposition,'crossAuditRationale':why,'crossAuditResolution':resolution,
      'currentTarget':ct,'currentTargetSha256':c['currentTargetSha256'],'locale':loc,'nativeSpeakerReviewSuggested':True,
      'placeholderTokens':c['placeholderTokens'],'position':pos,'primaryDisposition':p['decision'],'primaryRationale':p['rationale'],
      'primaryTarget':pt,'primaryTargetSha256':p['selectedTargetSha256'],'proposalTargetAgreement':pt==bt,
      'runtimeDispatchGap':bool(ctx.get('translationDispatchGap')),'runtimeDispatchFollowup':follow,
      'selectedFrom':origin,'selectedTarget':selected,'selectedTargetSha256':sha(selected.encode()),
      'source':c['source'],'sourceId':c['sourceId'],'sourceNumericTokens':c['sourceNumericTokens'],'sourceProtectedLiterals':c['sourceProtectedLiterals'],
      'sourceSha256':c['sourceSha256'],'structuralChecks':checks,'translationDispatch':ctx['localizationDispatch'],'translationStatus':'draft'})
assert len(ledger)==240
assert sum(not x['proposalTargetAgreement'] for x in ledger)==103
assert sum(primary[k]['decision']!=blind[k]['disposition'] for k in keys)==82
assert sum(x['crossAuditResolution']=='shared-target-disposition-adjudicated' for x in ledger)==9
assert sum(x['crossAuditResolution']=='proposal-target-disagreement-adjudicated' for x in ledger)==103
assert [x['position'] for x in ledger if x['runtimeDispatchGap']]==[pos for pos in (346,350) for _ in LOCALES]
assert not (OUT/'cross-audit-ledger.jsonl').exists()
space=shutil.disk_usage(SCRATCH); assert space.free>100_000_000

attest={'repository':'snapetech-org/ROMarrNG','pullRequest':70,'state':pr['state'],'draft':pr['draft'],'baseRef':pr['base']['ref'],'headRef':pr['head']['ref'],'pullRequestHeadSha':pr['head']['sha'],'liveBranchRefSha':branch['object']['sha'],'localWorktreeHeadSha':repo_head,'localWorktreeTreeSha':repo_tree,'localWorktreeStatus':'clean','checkedAtUtc':datetime.now(timezone.utc).isoformat(),'evidence':'Live GitHub PR/ref API reads plus exact local worktree head/tree/status; no repository or PR writes.'}
(OUT/'live-head-attestation.json').write_text(json.dumps(attest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'cross-audit-ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in ledger),encoding='utf-8')
(OUT/'README.md').write_text(f'''# ROMarrNG PR #70 W345–W364 exact-head cross-audit

This task-scoped packet compares all 240 locale cells from candidate-free input against primary and blind reviews. It adjudicates translation text quality only and changes no repository file, catalog, caller/source pin, or pull request.

## Pins and scope

- PR #70 is open and draft on `task/localization-translation-review-20261030`.
- Exact head/tree: `{HEAD}` / `{TREE}`.
- W345–W364: 20 source IDs × 12 locales = 240 cells.
- Input: `{INPUT}`; primary review: `{PRIMARY}`; blind review: `{BLIND}`.
- All 288 prior callerless holds remain reattested unchanged; this window has no callerless cells.

## Comparison

- Target agreement: 137/240; target disagreements: 103.
- Disposition agreement: 158/240; disposition disagreements: 82.
- Combined differences: 112 (73 differ in target and disposition, 30 in target only, 9 in disposition only).
- Each cell has a resolved target, rationale, exact caller-context references, structural checks, and source/catalog/current/primary/blind/selected hashes in `cross-audit-ledger.jsonl`.
- Ranks 359–360 use exact task-loop semantics: searched counts Wanted entries; grabbed counts releases accepted by the download client, not completed downloads.

## Separate runtime follow-ups

Ranks **346** and **350** are app-authored strings with concrete callers, but the UI currently passes them through `apiMessageMarkup` as opaque text. Their catalog decisions remain text-quality review only. A separate source-bound runtime dispatch fix is required before catalog translations can appear in those paths. This audit leaves source and caller pins unchanged.

## Review limits

Confidence is moderate. Native-speaker approval remains pending; the catalog marks translations unverified. This is not headed-browser acceptance. No tests, builds, scans, CI, merge, release, or tag were run or requested.

## Files

- `cross-audit-ledger.jsonl`: 240 full adjudication records.
- `cross-audit-summary.json`: counts, hashes, and follow-ups.
- `live-head-attestation.json`: live pin readback.
- `create_cross_audit.py`: reproducible adjudication packet generator.
- `verify_cross_audit.py`: read-only verifier.
- `SHA256SUMS.txt`: hashes of all other packet files.
''',encoding='utf-8')

verifier=r'''#!/usr/bin/env python3
import collections, hashlib, json, re
from pathlib import Path
OUT=Path(__file__).resolve().parent; S=Path('/home/keith/Documents/code/task-scratch')
I=S/'romarrng-pr70-w345-364-primary-20261103'/'input'; P=S/'romarrng-pr70-w345-364-primary-20261103'/'primary-review'; B=S/'romarrng-pr70-w345-364-blind-20261103'/'blind-review'
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def j(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sums(d):
 for line in (d/'SHA256SUMS.txt').read_text().splitlines():
  digest,name=line.split('  ',1); assert h(d/name)==digest,(d/name)
def idx(p):
 rows=jl(p); d={(x['position'],x['locale']):x for x in rows}; assert len(d)==len(rows); return d
for folder in (I,P,B,OUT): sums(folder)
m=j(I/'manifest.json'); assert m['head']=='6bef0c74632067906fd07279fa6bd3fd59159a48' and m['tree']=='4fd79e67f37e4c66d0253199418973d965a3fbd6'
assert m['priorHoldCellCount']==288 and m['priorHoldTargetsUnchanged'] and m['translationDispatchGapPositions']==[346,350]
holds=jl(I/'prior-hold-reattestation.jsonl'); assert len(holds)==288 and all(x['targetUnchanged'] and x['currentTargetSha256']==x['priorCurrentTargetSha256'] for x in holds)
C=idx(I/'current-target-cells.jsonl'); PR=idx(P/'review-decisions.jsonl'); BL=idx(B/'blind-ledger.jsonl'); A=idx(OUT/'cross-audit-ledger.jsonl')
assert set(C)==set(PR)==set(BL)==set(A) and len(A)==240
ctx={x['position']:x for x in jl(I/'source-contexts.jsonl')}; ph=re.compile(r'\{[^{}]+\}')
for k,r in A.items():
 c=C[k]; p=PR[k]; b=BL[k]
 assert r['sourceId']==c['sourceId']==p['sourceId']==b['sourceId']==ctx[k[0]]['sourceId']
 assert r['sourceSha256']==c['sourceSha256']==p['sourceSha256']==b['sourceSha256']
 for field,text in [('currentTargetSha256',r['currentTarget']),('primaryTargetSha256',r['primaryTarget']),('blindTargetSha256',r['blindTarget']),('selectedTargetSha256',r['selectedTarget'])]: assert r[field]==hashlib.sha256(text.encode()).hexdigest()
 assert r['selectedTarget'] in (r['currentTarget'],r['primaryTarget'],r['blindTarget'])
 assert r['callerContextSha256']==ctx[k[0]]['callerContextSha256'] and r['callerContextRefs']==ctx[k[0]]['callerContextRefs']
 assert collections.Counter(ph.findall(r['source']))==collections.Counter(ph.findall(r['selectedTarget']))
 assert all(str(x) in r['selectedTarget'] for x in r['sourceNumericTokens']) and all(str(x) in r['selectedTarget'] for x in r['sourceProtectedLiterals'])
 assert all(r['structuralChecks'].values())
assert sum(not x['proposalTargetAgreement'] for x in A.values())==103
assert sum(x['crossAuditResolution']=='shared-target-disposition-adjudicated' for x in A.values())==9
assert sum(x['crossAuditResolution']=='proposal-target-disagreement-adjudicated' for x in A.values())==103
assert sum(x['runtimeDispatchGap'] for x in A.values())==24
s=j(OUT/'cross-audit-summary.json'); assert s['cellCount']==240 and s['targetDisagreementCount']==103 and s['dispositionDisagreementCount']==82 and s['combinedDifferingCellCount']==112
print('PASS: 240 cells and exact candidate/source/context/target hashes verified; input/review/output checksums pass; 288 prior holds unchanged; dispatch gaps 346 and 350 retained.')
'''
(OUT/'verify_cross_audit.py').write_text(verifier,encoding='utf-8')
(OUT/'create_cross_audit.py').chmod(0o755); (OUT/'verify_cross_audit.py').chmod(0o755)

p_summary=jread(PRIMARY/'summary.json'); b_summary=jread(BLIND/'summary.json')
source_counts=collections.Counter(x['selectedFrom'] for x in ledger)
disp_counts=collections.Counter(x['crossAuditDisposition'] for x in ledger)
by_locale={l:dict(collections.Counter(x['crossAuditDisposition'] for x in ledger if x['locale']==l)) for l in LOCALES}
summary={
 'status':'exact-head-cross-audit-complete','repository':'snapetech-org/ROMarrNG','pullRequest':70,'headSha':HEAD,'treeSha':TREE,'branch':'task/localization-translation-review-20261030','window':'W345-W364','sourceCount':20,'localeCount':12,'cellCount':240,'locales':LOCALES,
 'candidateFreeInput':{'path':str(INPUT),'manifestSha256':fsha(INPUT/'manifest.json'),'checksumListSha256':fsha(INPUT/'SHA256SUMS.txt'),'sourceContextsSha256':fsha(INPUT/'source-contexts.jsonl'),'currentTargetCellsSha256':fsha(INPUT/'current-target-cells.jsonl'),'priorHoldReattestationSha256':fsha(INPUT/'prior-hold-reattestation.jsonl'),'candidateFree':True},
 'primaryReview':{'path':str(PRIMARY),'ledgerSha256':fsha(PRIMARY/'review-decisions.jsonl'),'summarySha256':fsha(PRIMARY/'summary.json'),'checksumListSha256':fsha(PRIMARY/'SHA256SUMS.txt'),'counts':p_summary['counts']},
 'blindReview':{'path':str(BLIND),'ledgerSha256':fsha(BLIND/'blind-ledger.jsonl'),'summarySha256':fsha(BLIND/'summary.json'),'checksumListSha256':fsha(BLIND/'SHA256SUMS.txt'),'counts':b_summary['dispositions']},
 'comparison':{'targetAgreementCount':137,'targetDisagreementCount':103,'dispositionAgreementCount':158,'dispositionDisagreementCount':82,'combinedDifferingCellCount':112,'differingBothTargetAndDisposition':73,'targetOnlyDisagreementCount':30,'dispositionOnlyDisagreementCount':9},
 'crossAudit':{'selectedTargetCount':240,'selectedTargetChangedFromCurrent':sum(x['selectedTarget']!=x['currentTarget'] for x in ledger),'selectedTargetSourceCounts':dict(source_counts),'dispositions':dict(disp_counts),'dispositionsByLocale':by_locale,'nativeSpeakerApproval':False,'nativeSpeakerReviewSuggested':True,'confidence':'moderate'},
 'callerlessHolds':{'cellsInCurrentWindow':0,'priorCallerlessHoldCellsReattested':288,'priorCallerlessHoldTargetsUnchanged':True},
 'translationDispatchFollowups':[{'position':346,'sourceId':contexts[346]['sourceId'],'required':True,'status':'Catalog text-quality only; app-authored launcher error toast currently passes through apiMessageMarkup as opaque text; separate source-bound runtime dispatch fix required.','sourceRef':'romarr/app.py:5245-5260','uiCallerRef':'romarr/ui.py:2789-2797','rendererRef':'romarr/ui.py:1042-1049; 1609-1611'},{'position':350,'sourceId':contexts[350]['sourceId'],'required':True,'status':'Catalog text-quality only; app-authored TOTP note currently passes through apiMessageMarkup as opaque text; separate source-bound runtime dispatch fix required.','sourceRef':'romarr/app.py:7503-7518','uiCallerRef':'romarr/ui.py:4551-4560','rendererRef':'romarr/ui.py:1042-1049'}],
 'liveHeadAttestationSha256':fsha(OUT/'live-head-attestation.json'),
 'operationalScope':{'repositoryOrPullRequestChanged':False,'sourceOrCallerPinsChanged':False,'testsBuildsScansCI':False,'headedBrowserAcceptance':False,'mergeReleaseTag':False,'writtenOnlyToTaskScratch':True,'taskScratchPath':str(OUT),'kspls0FreeBytesBeforeWrite':space.free},
 'outputFiles':{'cross-audit-ledger.jsonl':fsha(OUT/'cross-audit-ledger.jsonl'),'live-head-attestation.json':fsha(OUT/'live-head-attestation.json'),'README.md':fsha(OUT/'README.md'),'create_cross_audit.py':fsha(OUT/'create_cross_audit.py'),'verify_cross_audit.py':fsha(OUT/'verify_cross_audit.py')},'checkedAtUtc':datetime.now(timezone.utc).isoformat()}
(OUT/'cross-audit-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
files=['README.md','create_cross_audit.py','cross-audit-ledger.jsonl','cross-audit-summary.json','live-head-attestation.json','verify_cross_audit.py']
(OUT/'SHA256SUMS.txt').write_text(''.join(f'{fsha(OUT/name)}  {name}\n' for name in files),encoding='utf-8')
subprocess.check_call(['python3',str(OUT/'verify_cross_audit.py')])
print(json.dumps({'output':str(OUT),'ledgerRows':len(ledger),'targetDisagreements':len(target_diffs),'dispositionDisagreements':82,'combinedDifferences':112,'crossAuditDispositions':dict(disp_counts),'selectedFrom':dict(source_counts),'outputBytes':sum(p.stat().st_size for p in OUT.iterdir()),'files':sorted(p.name for p in OUT.iterdir())},ensure_ascii=False,indent=2))
