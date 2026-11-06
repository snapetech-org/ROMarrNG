from __future__ import annotations
import collections, datetime, hashlib, json, re, subprocess
from pathlib import Path

ROOT=Path('/mnt/disks/scratch/task-scratch')
INPUT=ROOT/'romarrng-pr70-w245-264-candidate-free-20261103/input'
PRIMARY=ROOT/'romarrng-pr70-w245-264-primary-20261103'
BLIND=ROOT/'romarrng-pr70-w245-264-independent-blind-20261103'
OUT=ROOT/'romarrng-pr70-w245-264-cross-audit-20261103'
HEAD='e7f8d0dcb11d8d94c8a89c37cb9ab451d72810a6'
TREE='016587d26f04d2920a30878236f1933a57e27901'
BRANCH='task/localization-translation-review-20261030'
assert OUT.exists() and OUT.is_dir()

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_text(s:str)->str:return sha_bytes(s.encode('utf-8'))
def canonical(s:str)->str:return json.dumps(s,ensure_ascii=False,separators=(',',':'))
def canonical_hash(s:str)->str:return sha_text(canonical(s))
def jline(x)->str:return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def verify_manifest(directory:Path)->None:
    proc=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=directory,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if proc.returncode: raise RuntimeError(f'checksum failure {directory}:\n{proc.stdout}')

for d in (INPUT,PRIMARY,BLIND): verify_manifest(d)
pr=json.loads(subprocess.check_output(['gh','api','repos/snapetech-org/ROMarrNG/pulls/70'],text=True))
assert pr['state']=='open' and pr['draft'] is True and pr['head']['ref']==BRANCH and pr['head']['sha']==HEAD
remote=subprocess.check_output(['git','-C','/home/keith/Documents/code/ROMarrNG','ls-remote','origin',f'refs/heads/{BRANCH}','refs/pull/70/head'],text=True)
refs={line.split()[1]:line.split()[0] for line in remote.splitlines()}
assert refs[f'refs/heads/{BRANCH}']==HEAD and refs['refs/pull/70/head']==HEAD,refs

manifest=json.loads((INPUT/'manifest.json').read_text(encoding='utf-8'))
prim_summary=json.loads((PRIMARY/'summary.json').read_text(encoding='utf-8'))
blind_summary=json.loads((BLIND/'summary.json').read_text(encoding='utf-8'))
assert manifest['head']==prim_summary['head']==blind_summary['head']==HEAD
assert manifest['tree']==prim_summary['tree']==blind_summary['tree']==TREE
assert manifest['cellCount']==prim_summary['cellCount']==blind_summary['cellCount']==240
assert manifest['candidateFreeInputOnly'] is True
assert prim_summary['sourceIndexLocationMismatches']==16

cells=[json.loads(l) for l in (INPUT/'current-target-cells.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
sources={x['position']:x for x in (json.loads(l) for l in (INPUT/'source-contexts.jsonl').read_text(encoding='utf-8').splitlines() if l.strip())}
primary=[json.loads(l) for l in (PRIMARY/'primary-decisions.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
blind=[json.loads(l) for l in (BLIND/'blind-ledger.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
caller_holds=[json.loads(l) for l in (INPUT/'caller-resolution-holds.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
assert len(cells)==len(primary)==len(blind)==240 and len(sources)==20
assert all(x['candidateProposalSeen'] is False and x['proposedTarget'] is None for x in blind), 'blind ledger must remain candidate-free'
K=lambda x:(x['position'],x['locale'])
C={K(x):x for x in cells}; P={K(x):x for x in primary}; B={K(x):x for x in blind}
H={K(x):x for x in caller_holds}
assert set(C)==set(P)==set(B) and len(C)==240
assert len(H)==72

# Two cross-audit additions resolve clear errors independently identified by the
# exact source/caller context but not proposed by the primary reviewer.
EXTRA={
 (250,'es'):{'target':'Asignación de ruta para {path}','disposition':'correction','rationale':'The English source and the exact accessibility-name caller describe one path-mapping row, but the current Spanish says “rutas” (plural). The singular target preserves the path placeholder and the one-row meaning.'},
 (253,'de'):{'target':'Plattform-Ordnernamen','disposition':'correction','rationale':'The current German compound “Plattformfoldernamen” leaves “folder” in English and is awkward. A clear hyphenated German compound accurately names the platform-folder group heading.'},
}
# Keep the source's route metaphor while repairing the Chinese classifier and
# the misleading literal-physical-parts wording, using the independently
# reviewed proposal rather than inventing a new wording.
REJECTED={(261,'id')}
path_positions={248,249,256,257,258,259}
assert {k[0] for k in H}==path_positions

out_rows=[]
final_counts=collections.Counter()
semantic_counts=collections.Counter()
caller_semantic_counts=collections.Counter()
result_counts=collections.Counter()
divergence_counts=collections.Counter()
by_position=collections.defaultdict(collections.Counter)

for key in sorted(C):
    c=C[key]; p=P[key]; b=B[key]; src=sources[c['position']]
    path_hold=key in H
    assert p['head']==b['head']==c['head']==HEAD
    assert p['tree']==b['tree']==c['tree']==TREE
    assert p['currentTarget']==b['currentTarget']==c['currentTarget']
    assert p['currentTargetSha256']==b['currentTargetSha256']==c['currentTargetSha256']
    assert sha_text(c['currentTarget'])==c['currentTargetSha256']
    assert c['translationHashEntryMatchesCanonicalJson'] is True
    assert canonical_hash(c['currentTarget'])==c['currentTargetCanonicalTranslationHash']
    assert p['decision'] in {'accept-current','correction','refinement','hold'}
    assert b['disposition'] in {'accept-current','correction','refinement'}
    assert p['decision']=='hold' if path_hold else p['decision']!='hold'
    assert (p['callerResolutionHold'] is not None)==path_hold and (key in H)==path_hold
    assert b['callerPathHold']==path_hold

    selected=None; selected_from=None; final_disposition=None; semantic_disposition=None
    rationale=''; confidence='moderate'; selected_source_note=None
    if path_hold:
        semantic_disposition=b['disposition']
        final_disposition='hold-caller-path'
        rationale=(f"The pinned runtime/caller evidence blocks catalog changes: {H[key]['holdReason']} "
                   f"The blind semantic disposition ({b['disposition']}) is recorded separately; it does not change this caller-path hold.")
        selected_from='caller-path-hold'
        confidence='high'
    elif key in REJECTED:
        semantic_disposition='accept-current'
        final_disposition='accept-current'
        selected=c['currentTarget']; selected_from='current-target'
        rationale="The current Indonesian “batch” is an established technical term in this file-batch preview context. The proposed “kelompok” is understandable but less specific to a processing batch; retain the current target."
        confidence='moderate'
        selected_source_note='primary refinement not selected after exact UI-context review'
    elif key in EXTRA:
        extra=EXTRA[key]
        semantic_disposition=extra['disposition']; final_disposition=extra['disposition']
        selected=extra['target']; selected_from='cross-audit-candidate'
        rationale=extra['rationale']; confidence='high'
    elif p['decision'] in {'correction','refinement'}:
        selected=p['candidateTarget']
        assert isinstance(selected,str) and selected
        semantic_disposition=p['decision']; final_disposition=p['decision']
        selected_from='primary-candidate'
        rationale=(f"The pinned caller supports the primary's {p['decision']} proposal. "
                   f"The blind reviewer marked the current value {b['disposition']}; the concern remains supported by the exact source meaning and UI context: {p['rationale']}")
        confidence=p['confidence']
        selected_source_note='primary candidate selected after independent cross-audit'
    elif p['decision']=='accept-current' and b['disposition'] in {'correction','refinement'}:
        # All non-path blind-only findings have explicit cross-audit candidates in EXTRA.
        raise AssertionError(f'unmapped blind-only proposal at {key}')
    else:
        semantic_disposition='accept-current'; final_disposition='accept-current'
        selected=c['currentTarget']; selected_from='current-target'
        rationale='Both reviews accept the current target in the pinned caller context; no material omission, reversal, or locale mismatch was found.'
        confidence='moderate'

    if selected is not None:
        assert sha_text(selected)
        selected_raw_sha=sha_text(selected); selected_canonical=canonical_hash(selected)
    else:
        selected_raw_sha=None; selected_canonical=None

    # Validate the selected target structurally against the exact English source.
    # For caller-path holds, no target is selected; validate the unchanged current
    # value to preserve a traceable token result without treating it as applied.
    checked_target=selected if selected is not None else c['currentTarget']
    source_placeholders=re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',c['source'])
    target_placeholders=re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',checked_target)
    source_tags=re.findall(r'</?[A-Za-z][^>]*>',c['source'])
    target_tags=re.findall(r'</?[A-Za-z][^>]*>',checked_target)
    source_nums=re.findall(r'(?<!\w)\d+(?:[.,]\d+)?',c['source'])
    target_nums=re.findall(r'(?<!\w)\d+(?:[.,]\d+)?',checked_target)
    assert collections.Counter(source_placeholders)==collections.Counter(target_placeholders),key
    assert source_tags==target_tags,key
    assert source_nums==target_nums,key
    assert c['source']==c['source'].strip() and checked_target==checked_target.strip(),key
    if selected is not None and p['candidateTarget'] is not None and selected==p['candidateTarget']:
        assert p['candidateTargetRawUtf8Sha256']==sha_text(selected)
        assert p['candidateTargetCanonicalTranslationHash']==canonical_hash(selected)

    source_hold=H.get(key)
    caller_evidence={
        'callerResolution':src['callerResolution'],
        'callerResolutionReason':src['callerResolutionReason'],
        'callerReferenceCount':src['callerReferenceCount'],
        'exactProductionLiteralHits':src['exactProductionLiteralHits'],
        'sourceCallSpans':src['sourceCallSpans'],
        'sourceIndexPointerStatus':src['sourceIndexPointerStatus'],
        'pointerNote':'Current exact-head sourceCallSpans are authoritative. The candidate-free reconciliation identifies stale source-index line hints; those hints are not treated as current callers.'
    }
    row={
      'schemaVersion':1,'recordType':'third-party-cell-reconciliation',
      'repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':'W245-W264',
      'position':c['position'],'sourceId':c['sourceId'],'source':c['source'],'sourceSha256':c['sourceSha256'],
      'sourceKind':c['sourceKind'],'locale':c['locale'],'catalogPath':c['catalogPath'],
      'catalogFileSha256':c['catalogFileSha256'],'catalogGitBlob':c['catalogGitBlob'],
      'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],
      'currentTargetCanonicalTranslationHash':c['currentTargetCanonicalTranslationHash'],
      'primaryReview':{
        'decision':p['decision'],'candidateTarget':p['candidateTarget'],
        'candidateTargetSha256':p['candidateTargetRawUtf8Sha256'],
        'candidateTargetCanonicalTranslationHash':p['candidateTargetCanonicalTranslationHash'],
        'rationale':p['rationale'],'confidence':p['confidence'],
        'callerResolutionHold':p['callerResolutionHold'],
        'integrityChecks':p['integrityChecks']
      },
      'blindReview':{
        'disposition':b['disposition'],'proposedTarget':b['proposedTarget'],
        'proposedTargetSha256':sha_text(b['proposedTarget']) if b['proposedTarget'] is not None else None,
        'rationale':b['rationale'],'confidence':b['confidence'],
        'candidateProposalSeen':b['candidateProposalSeen'],
        'callerPathHold':b['callerPathHold'],
        'placeholderOrderChanged':b['placeholderOrderChanged'],
        'placeholderTokenMultisetMatches':b['placeholderTokenMultisetMatches']
      },
      'callerPathHold':{
        'held':path_hold,
        'holdReason':source_hold['holdReason'] if source_hold else None,
        'kind':'runtime caller path / raw API opacity' if path_hold else None,
        'translationReviewDisposition':semantic_disposition if path_hold else None
      },
      'sourceCallerEvidence':caller_evidence,
      'crossAuditDisposition':final_disposition,
      'crossAuditResult':('caller-path-held-with-separate-translation-review' if path_hold else
                          'cross-audit-added-correction' if key in EXTRA else
                          'primary-proposal-selected' if selected_from=='primary-candidate' else
                          'primary-refinement-declined' if key in REJECTED else
                          'both-reviews-accept-current'),
      'translationReviewDisposition':semantic_disposition,
      'crossAuditRationale':rationale,
      'crossAuditConfidence':confidence,
      'selectedFrom':selected_from,
      'selectedTarget':selected,
      'selectedTargetSha256':selected_raw_sha,
      'selectedTargetCanonicalTranslationHash':selected_canonical,
      'selectedTargetRawUtf8Sha256':selected_raw_sha,
      'deferredBlindCorrection':bool(path_hold and b['disposition'] in {'correction','refinement'}),
      'deferredNote':('A translation-level issue is recorded, but no catalog target is selected while the exact user-facing localization path is unresolved.' if path_hold and b['disposition'] in {'correction','refinement'} else None),
      'structuralReview':{
        'checkedTarget':checked_target,'selectedTargetIsApplied':selected is not None,
        'sourcePlaceholders':source_placeholders,'selectedPlaceholders':target_placeholders,
        'placeholderMultisetParity':collections.Counter(source_placeholders)==collections.Counter(target_placeholders),
        'sourceMarkupTags':source_tags,'selectedMarkupTags':target_tags,'markupSequenceParity':source_tags==target_tags,
        'sourceNumericTokens':source_nums,'selectedNumericTokens':target_nums,'numericTokenParity':source_nums==target_nums,
        'edgeWhitespaceParity':c['source']==c['source'].strip() and checked_target==checked_target.strip(),
        'currentCanonicalTranslationHashVerified':canonical_hash(c['currentTarget'])==c['currentTargetCanonicalTranslationHash'],
        'releaseApproved':False
      },
      'qualifiedLocaleReviewRequiredBeforeRelease':True,
      'nativeSpeakerApproved':False
    }
    out_rows.append(row)
    final_counts[final_disposition]+=1
    semantic_counts[semantic_disposition]+=1
    if path_hold: caller_semantic_counts[semantic_disposition]+=1
    result_counts[row['crossAuditResult']]+=1
    # Separate caller-path status from true semantic disposition agreement.
    if path_hold: divergence_counts['caller-path-axis-separated']+=1
    elif p['decision']==b['disposition']: divergence_counts['exact-semantic-disposition-agreement']+=1
    elif p['decision'] in {'correction','refinement'} and b['disposition'] in {'correction','refinement'}: divergence_counts['both-change-different-severity']+=1
    else: divergence_counts['accept-vs-change']+=1
    by_position[c['position']][final_disposition]+=1

assert len(out_rows)==240
assert final_counts=={'accept-current':138,'correction':14,'refinement':16,'hold-caller-path':72},final_counts
assert caller_semantic_counts=={'accept-current':70,'correction':2},caller_semantic_counts
assert semantic_counts['correction']==16 and semantic_counts['refinement']==16 and semantic_counts['accept-current']==208,semantic_counts
assert sum(1 for r in out_rows if r['selectedTarget'] is not None and r['selectedTarget']!=r['currentTarget'])==30
assert all(r['structuralReview']['placeholderMultisetParity'] and r['structuralReview']['markupSequenceParity'] and r['structuralReview']['numericTokenParity'] and r['structuralReview']['edgeWhitespaceParity'] for r in out_rows)

(OUT/'cross-audit-ledger.jsonl').write_text(''.join(jline(x)+'\n' for x in out_rows),encoding='utf-8')
summary={
 'schemaVersion':1,'repository':'snapetech-org/ROMarrNG','pullRequest':70,'state':'open','draft':True,
 'head':HEAD,'tree':TREE,'branch':BRANCH,'window':'W245-W264','sourceCount':20,'localeCount':12,'cellCount':240,
 'inputChecksumManifestSha256':sha_bytes((INPUT/'SHA256SUMS.txt').read_bytes()),
 'primaryChecksumManifestSha256':sha_bytes((PRIMARY/'SHA256SUMS.txt').read_bytes()),
 'blindChecksumManifestSha256':sha_bytes((BLIND/'SHA256SUMS.txt').read_bytes()),
 'inputChecksums':'pass','primaryChecksums':'pass','blindChecksums':'pass','livePRAndRemoteRefs':'match',
 'finalDispositionCounts':dict(sorted(final_counts.items())),
 'semanticReviewCountsIncludingPathHeldCells':dict(sorted(semantic_counts.items())),
 'callerPathHoldCells':72,'callerPathHoldPositions':[248,249,256,257,258,259],
 'callerPathHeldSemanticCounts':dict(sorted(caller_semantic_counts.items())),
 'translationLevelHoldCount':0,
 'deferredBlindCorrectionsAtCallerPathHolds':[
  {'position':259,'locale':'pt-BR','reason':'Current “não é instalado” describes an installation action rather than the plugin state.'},
  {'position':259,'locale':'zh-Hant','reason':'Current “不安裝” describes not installing rather than the plugin state.'}
 ],
 'selectedCatalogChanges':30,'selectedCorrections':14,'selectedRefinements':16,
 'primaryBlindDispositionRelationshipCounts':dict(sorted(divergence_counts.items())),
 'crossAuditResultCounts':dict(sorted(result_counts.items())),
 'currentSourceIndexHintsReconciled':16,'staleIndexHintsUsedAsCurrentCallerEvidence':0,
 'sourceCurrentCandidateHashFailures':0,'placeholderMarkupNumericWhitespaceFailures':0,
 'qualifiedNativeSpeakerApproval':False,'exactHeadBrowserReview':False,'releaseApproved':False,
 'noRepositoryEdits':True,'noTestsBuildsScansOrCI':True,
 'verifiedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()
}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

changes=[r for r in out_rows if r['crossAuditDisposition'] in {'correction','refinement'}]
changes_by_pos=collections.defaultdict(list)
for r in changes: changes_by_pos[r['position']].append(r)
md=['# ROMarrNG PR #70 W245–W264 third-party cross-audit','',
 f"Exact PR head `{HEAD}` / tree `{TREE}`; branch and pull refs both match the live open draft PR.",'',
 '## Reconciliation','',
 'All three sealed packets passed their checksum manifests. The cross-audit reconciles 240 cells (20 active source IDs × 12 direct locales) against the current catalog, primary semantic ledger, independent blind ledger, and exact current caller/runtime spans. Sixteen stale source-index location hints were reconciled to exact current source spans; none of those old hints is treated as a current caller.','',
 'The primary review marks 72 cells as holds because their user-facing localization path is unresolved or the exact source is internal. These are tracked as `hold-caller-path`, separately from translation semantics. The blind reviewer judged 70 of those current targets semantically acceptable and flagged two translation errors at position 259 (pt-BR and zh-Hant); neither receives a selected catalog target until an explicit local-template caller exists. The remaining 168 cells have no caller-path hold and no translation-level hold remains.','',
 'Final cross-audit counts: 138 accept-current, 14 corrections, 16 refinements, and 72 caller-path holds. Thirty catalog changes are selected. All selected targets preserve placeholders, markup, numeric tokens, and edge whitespace. Machine review does not establish native-speaker approval; no release approval is granted.','',
 '## Selected changes','']
for pos in sorted(changes_by_pos):
 group=changes_by_pos[pos]
 md.append(f"### Position {pos}: `{group[0]['source']}`")
 md.append('')
 for r in group:
  md.append(f"- **{r['locale']} — {r['crossAuditDisposition']}** `{r['currentTarget']}` → `{r['selectedTarget']}`. {r['crossAuditRationale']}")
 md.append('')
md += ['## Caller-path holds','',
 'All 12 locale cells remain held at each position below pending an exact user-facing localized template/path:','',
 '- 248: dynamically returned missing-library-path hint is rendered as opaque raw API text.','- 249: dynamically returned stored-path/fallback diagnostic is rendered as opaque raw API text.','- 256: plugin-fetch detail is rendered as opaque raw API text.','- 257: internal confinement exception is discarded; no exact user-facing caller exists.','- 258: disabled-plugin detail is rendered as opaque raw API text.','- 259: not-installed detail, including dynamic exception text, is rendered as opaque raw API text.','',
 'For position 259, the blind review separately flags pt-BR and zh-Hant wording; selectedTarget remains null under the caller-path hold.','',
 '## Evidence and limits','',
 '- `cross-audit-ledger.jsonl` contains the cell-level primary/blind lineage, current caller evidence, chosen/deferred disposition, selected target and hashes, and structural checks.','- `summary.json` records counts and live head verification.','- Input, primary, and blind packets remain in their separate task-scoped scratch directories and are referenced by SHA-256 checksum-manifest hashes in the summary.','- No repository or PR files were changed; no tests, builds, scans, or CI jobs were run. Exact-head browser acceptance and qualified native-speaker approval remain pending.','']
(OUT/'report.md').write_text('\n'.join(md),encoding='utf-8')
(OUT/'README.md').write_text('''This third-party reconciliation reads only the candidate-free input, primary review, and independent blind review. It is pinned to the exact current draft PR head. The row-level ledger separates caller-path holds from semantic translation decisions and keeps selected targets null for cells blocked by the caller path. See `report.md` for the disposition and rationale summary.\n''',encoding='utf-8')

# The ledger hash is stable metadata. The root checksum manifest covers the
# summary and every other packet file, so it is validated externally and is not
# embedded in the summary (which would create a recursive checksum dependency).
summary['crossAuditLedgerSha256']=sha_bytes((OUT/'cross-audit-ledger.jsonl').read_bytes())
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
(OUT/'SHA256SUMS.txt').write_text(''.join(f'{sha_bytes(p.read_bytes())}  {p.relative_to(OUT).as_posix()}\n' for p in files),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
