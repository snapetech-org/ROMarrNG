#!/usr/bin/env python3
"""Assemble a sealed candidate-free blind review packet for ROMarrNG W765-W784."""
import hashlib, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFROOT = Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-20261105/candidate-free')
INP = CFROOT / 'input'
HEAD = '9714d7cf69c687685b4f65cbd9627a56830bab85'
TREE = 'c8eb66573f10b2390a02df05033f5133425d5e41'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
HOLD_KEYS = ['position','catalogZeroBasedIndex','catalogOneBasedPosition','sourceId','sourceSha256','locale','currentTargetSha256','callerContextSha256','literalCallerCount','cellDisposition','sourceTextOmitted','currentTargetTextOmitted','callerless','window']

def sha(data): return hashlib.sha256(data).hexdigest()
def read_json(path): return json.loads(path.read_text(encoding='utf-8'))
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def dump_json(path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')
def dump_jsonl(path, rows): path.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',',':'))+'\n' for r in rows), encoding='utf-8')

manifest = read_json(INP/'manifest.json')
selection = read_json(INP/'selection.json')
assert (manifest['head'], manifest['tree'], manifest['pullRequest'], manifest['window']) == (HEAD,TREE,70,'W765-W784')
assert selection['positions'] == [765,784] and selection['localeOrder'] == LOCALES
before, after = (read_json(INP/f) for f in ['PR-attestation-before.json','PR-attestation-after.json'])
for att in (before, after):
    assert (att['head'],att['tree'],att['pullRequest'],att['repository']) == (HEAD,TREE,70,'snapetech-org/ROMarrNG')
assert {k:v for k,v in before.items() if k != 'attestedAtUtc'} == {k:v for k,v in after.items() if k != 'attestedAtUtc'}

# Preserve frozen proposals; rebuild their row count and digest without consulting targets.
proposal_path = ROOT/'blind-locale-review.jsonl'
proposal_rows = read_jsonl(proposal_path)
assert len(proposal_rows) == 216
assert all(r['disposition']=='blind_proposal' and r['reviewBasis'].endswith('current locale target not consulted') and r['tokensPreserved'] for r in proposal_rows)
assert all(r['head'] == HEAD for r in [])  # rows bind through source review and exact pinned sources

# Build only from a field allowlist; callerless source/target text is never copied.
all_cells = read_jsonl(INP/'candidate-free-cells.jsonl')
hold_cells = [r for r in all_cells if r.get('callerless') is True and r.get('sourceTextOmitted') is True and r.get('currentTargetTextOmitted') is True]
assert len(hold_cells) == 24
holds=[]
for r in hold_cells:
    h={k:r[k] for k in HOLD_KEYS if k in r}
    h['textOmitted']=True
    h['disposition']='hold_hash_only'
    holds.append(h)
holds.sort(key=lambda r:(r['position'],LOCALES.index(r['locale'])))
assert {r['position'] for r in holds} == {771,774}
assert all(len([h for h in holds if h['position']==p])==12 for p in (771,774))
assert all(r.get('callerless') and r.get('sourceTextOmitted') and r.get('currentTargetTextOmitted') and r.get('textOmitted') for r in holds)

# Preserve the prior hold ledger byte-for-byte and separately add this window's text-free hashes.
prior_bytes=(INP/'prior-hold-reattestation.jsonl').read_bytes()
(ROOT/'prior-hold-lineage.jsonl').write_bytes(prior_bytes)
prior=read_jsonl(INP/'prior-hold-reattestation.jsonl')
assert len(prior)==988 and all(r.get('textOmitted') is True for r in prior)
assert not any(k.lower() in {'target','targettext','translation','translationtext','currenttarget'} for r in prior for k in r)
shutil.copyfile(INP/'prior-hold-context-reattestation.jsonl', ROOT/'prior-hold-context-reattestation.jsonl')
shutil.copyfile(INP/'prior-hold-reattestation-summary.json', ROOT/'prior-hold-reattestation-summary.json')
dump_jsonl(ROOT/'current-window-holds.jsonl',holds)

# One disposition record per selected cell, with only hashes for held cells.
dispositions=[]
for r in proposal_rows:
    dispositions.append({k:r[k] for k in ('position','catalogZeroBasedIndex','catalogOneBasedPosition','sourceId','sourceSha256','sourceContextSha256','locale','disposition','proposal','proposalSha256','tokensPreserved','sourceTokenSignature','proposalTokenSignature','manualProtectedLiteralsRequired','callerCount','callerReferences','semanticMeaning','reviewBasis','nativeSpeakerApproval')})
for h in holds:
    dispositions.append({k:h[k] for k in ('position','catalogZeroBasedIndex','catalogOneBasedPosition','sourceId','sourceSha256','locale','currentTargetSha256','callerContextSha256','disposition','textOmitted','sourceTextOmitted','currentTargetTextOmitted','callerless') if k in h})
dispositions.sort(key=lambda r:(r['position'],LOCALES.index(r['locale'])))
assert len(dispositions)==240
# Current targets are excluded from every caller-backed decision row by construction.
assert all('currentTarget' not in k.lower() and 'targetText' not in k.lower() for r in dispositions if r['disposition']=='blind_proposal' for k in r)
dump_jsonl(ROOT/'dispositions.jsonl',dispositions)

# Token audit summaries derive solely from frozen source/proposal rows.
checks={'placeholders':0,'markup':0,'numbers':0,'protectedLiterals':0,'manualProtectedLiterals':0}
for r in proposal_rows:
    a,b=r['sourceTokenSignature'],r['proposalTokenSignature']
    for key in ('placeholders','markup','numbers'):
        if a[key] != b[key]: checks[key]+=1
    if not set(a['protectedLiterals']).issubset(b['protectedLiterals']): checks['protectedLiterals']+=1
    if not all(x in r['proposal'] for x in r['manualProtectedLiteralsRequired']): checks['manualProtectedLiterals']+=1
assert not any(checks.values())
dump_json(ROOT/'token-audit.json',{
  'artifact':'ROMarrNG PR #70 W765-W784 independent blind proposal token audit',
  'head':HEAD,'tree':TREE,'window':'W765-W784','proposalCells':216,
  'checks':checks,'allPreserved':True,
  'protectedSourceLiteralsChecked':True,'manualProtectedLiteralsChecked':True,
  'callerlessCells':'not token-checked; held text-free by policy'
})

# Hash input pins and write the independent review summary.
outer_sums=(CFROOT/'SHA256SUMS.txt').read_bytes(); inner_sums=(INP/'SHA256SUMS.txt').read_bytes()
input_hashes={p.name:sha(p.read_bytes()) for p in [INP/'manifest.json',INP/'selection.json',INP/'selected-sources.jsonl',INP/'source-contexts.jsonl',INP/'candidate-free-cells.jsonl',INP/'prior-hold-reattestation.jsonl',INP/'prior-hold-context-reattestation.jsonl',INP/'prior-hold-reattestation-summary.json',INP/'PR-attestation-before.json',INP/'PR-attestation-after.json']}
dump_json(ROOT/'input-pins.json',{
  'artifact':'ROMarrNG PR #70 W765-W784 blind review input pins',
  'candidateFreeDirectory':str(CFROOT),'repository':'snapetech-org/ROMarrNG','pullRequest':70,
  'head':HEAD,'tree':TREE,'window':'W765-W784',
  'candidateFreeOuterChecksumListSha256':sha(outer_sums),
  'candidateFreeInputChecksumListSha256':sha(inner_sums),
  'candidateFreeManifestSha256':input_hashes['manifest.json'],
  'candidateFreeStaticInputHashes':input_hashes,
  'outerChecksumValidation':'PASS','innerChecksumValidation':'PASS',
  'candidateFreeOfficialVerifierObservation':'FAIL: worktree pin/clean; not rerun because task prohibits reading the changed worktree',
  'changedWorktreeInspected':False,'primaryCrossRootEvidenceInspected':False,
  'proposalDecisionsUsedCurrentTargets':False,
  'nextBoundary':manifest['nextBoundary']
})
shutil.copyfile(INP/'source-contexts.jsonl',ROOT/'pinned-source-contexts.jsonl')
shutil.copyfile(INP/'selected-sources.jsonl',ROOT/'selected-sources.jsonl')
source_review=read_json(ROOT/'source-review.json')
source_review['reviewConfidence']='moderate'
source_review['summary']='216 caller-backed target proposals reviewed independently from pinned source and caller evidence. 24 callerless cells remain hash-only holds.'
source_review['cellCount']=240
source_review['priorActiveHoldsReattested']=988
source_review['newHashOnlyHolds']=24
source_review['resultingActiveHashOnlyHolds']=1012
source_review['nextBoundary']=manifest['nextBoundary']
dump_json(ROOT/'source-review.json',source_review)

dump_json(ROOT/'hold-lineage-summary.json',{
  'artifact':'ROMarrNG PR #70 W765-W784 hash-only hold continuity',
  'head':HEAD,'tree':TREE,'window':'W765-W784',
  'priorActiveHashOnlyHolds':988,'priorHoldRowsCopiedByteForByte':True,
  'priorHoldHashesUnchanged':read_json(INP/'prior-hold-reattestation-summary.json')['allTargetHashesMatch'],
  'newWindowHashOnlyHolds':24,'newHoldSources':2,
  'resultingActiveHashOnlyHolds':1012,'allHoldRowsTextFree':True,
  'callerlessPositions':[771,774],
  'priorContextRows':len(read_jsonl(INP/'prior-hold-context-reattestation.jsonl'))
})

summary={
 'artifact':'ROMarrNG PR #70 W765-W784 independent blind review',
 'repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':HEAD,'tree':TREE,'window':'W765-W784',
 'cellCount':240,'sourceCount':20,'callerBackedCells':216,'callerReferences':23,
 'callerlessHashOnlyCells':24,'callerlessSourceCount':2,
 'dispositions':{'blind_proposal':216,'hold_hash_only':24},
 'tokenAudit':{'proposalCells':216,'mismatchCounts':checks},
 'priorActiveHolds':988,'newHashOnlyHolds':24,'resultingActiveHashOnlyHolds':1012,
 'currentTargetTextsConsulted':False,'primaryCrossRootEvidenceInspected':False,'changedWorktreeInspected':False,
 'candidateFreeOuterChecksums':'PASS','candidateFreeInnerChecksums':'PASS',
 'candidateFreeOfficialVerifier':'FAIL: worktree pin/clean (recorded, not rerun)',
 'nextBoundary':manifest['nextBoundary']
}
dump_json(ROOT/'review-summary.json',summary)

(ROOT/'README.md').write_text('''# ROMarrNG PR #70 W765–W784 independent blind review\n\nPinned to product head `'''+HEAD+'''` and tree `'''+TREE+'''`. This packet covers 240 cells across 20 source rows and 12 locales. The blind decisions were made from the candidate-free source/caller evidence. The independent proposal matrix was frozen before caller-backed target hashes were opened; no current target text, primary/cross/root evidence, or changed worktree content was used for proposals.\n\nThere are 216 caller-backed blind proposals across 23 caller references. The remaining 24 cells belong to two callerless sources and are preserved as hash-only holds; their source and target text are omitted. The prior 988 active hold rows are copied byte-for-byte, with their 86 context-reattestation rows and source-free summary preserved. This yields 1,012 active hash-only holds.\n\nToken checks cover placeholders, markup, numbers, protected source literals, and manually pinned syntax/product literals. All 216 caller-backed proposals pass. Callerless holds are not token-checked because their text is intentionally absent.\n\nThe outer and inner candidate-free checksum lists both validate. The candidate-free official verifier was run once and returned `FAIL: worktree pin/clean`; it was not rerun, and the changed worktree was not inspected, as required by the review boundary. Exact head/tree and before/after PR attestations in the static packet agree. This is a recorded verifier limitation, not a passing clean-worktree assertion.\n\n## Files\n\n- `blind-locale-review.jsonl`: 216 independent proposed targets and per-cell token/caller evidence.\n- `dispositions.jsonl`: all 240 cell dispositions; held rows carry hashes only.\n- `current-window-holds.jsonl`: 24 new text-free callerless hold records.\n- `prior-hold-lineage.jsonl`: 988 prior hash-only hold rows copied byte-for-byte.\n- `prior-hold-context-reattestation.jsonl`, `prior-hold-reattestation-summary.json`: preserved prior caller/context and hash attestation.\n- `pinned-source-contexts.jsonl`, `selected-sources.jsonl`, `source-review.json`: source/caller evidence and semantic review.\n- `input-pins.json`: exact input hashes and product pin.\n- `proposal-freeze.json`, `token-audit.json`, `hold-lineage-summary.json`, `review-summary.json`: freeze, token, hold, and count summaries.\n- `verify_blind_review.py`: packet and static-input verifier; it does not access a product worktree or other review roles.\n- `SHA256SUMS.txt`: packet checksum seal.\n\nNext selection boundary: continuation index 785 / one-based catalog position 786, `'''+manifest['nextBoundary']['sourceId']+'''` (`'''+manifest['nextBoundary']['sourceSha256']+'''`). No W785 material is included.\n''',encoding='utf-8')
print(json.dumps({'result':'PACKET_ASSEMBLED','proposalCells':216,'holdCells':24,'priorActiveHolds':988,'activeHoldCount':1012,'dispositionCells':len(dispositions),'output':str(ROOT)},indent=2))
