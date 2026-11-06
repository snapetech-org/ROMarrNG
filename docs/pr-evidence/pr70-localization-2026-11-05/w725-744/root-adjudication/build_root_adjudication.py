#!/usr/bin/env python3
import collections, hashlib, json
from pathlib import Path
TASK = Path(__file__).resolve().parents[1]
ROOT = TASK / 'root-adjudication'
CF = TASK / 'candidate-free' / 'input'
PRIMARY = TASK / 'primary-review'
BLIND = TASK / 'blind-review'
CROSS = TASK / 'cross-review'
HEAD = 'c3f92c45b4b4f8d79a8caa99417f9970ebc42a26'
TREE = '3f835643e4f557999d533c3e832fc92036d4b01a'
def sha(b): return hashlib.sha256(b).hexdigest()
def textsha(s): return sha(s.encode('utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
# Root adjudication accepted cross-reviewed targets only after checking the exact caller and source context.
selections = {
 (728, 'de'): ('refinement', 'Derzeit wird kein Set beschafft.', 'The pending state is acquisition of a set; “beschafft” covers acquire/find/fetch without implying purchase.'),
 (734, 'ko'): ('refinement', '미발표', 'The caller displays a missing upcoming-game release date; this means not announced rather than undecided.'),
 (735, 'de'): ('correction', 'Nicht verfügbar', 'The caller renders this as a standalone status label, so German sentence-initial capitalization applies.'),
 (740, 'ar'): ('correction', 'ملاحظات', 'All five pinned callers use the general metadata Notes label; the existing Arabic means footnotes/endnotes.'),
 (743, 'de'): ('refinement', 'Keine Spiele mit einem zukünftigen Erscheinungsdatum.', 'The upcoming-games empty state concerns games with future release dates, not appointments or calendar dates.'),
}
cfraw = [x for x in (CF/'candidate-free-cells.jsonl').read_bytes().splitlines() if x.strip()]
cfrows = [json.loads(x) for x in cfraw]
cfmap = {(r['position'], r['locale']): r for r in cfrows}
rowhash = {(r['position'], r['locale']): sha(line) for r, line in zip(cfrows, cfraw)}
primary = {(r['position'], r['locale']): r for r in rows(PRIMARY/'ledger.jsonl')}
blind = {(r['position'], r['locale']): r for r in rows(BLIND/'review-cells.jsonl')}
cross = {(r['position'], r['locale']): r for r in rows(CROSS/'cross-review.jsonl')}
assert len(cfmap) == len(primary) == len(blind) == len(cross) == 240
assert set(cfmap) == set(primary) == set(blind) == set(cross)
assert len(selections) == 5
out = []
selected = []
counts = collections.Counter()
for key in sorted(cfmap):
    c, p, b, x = cfmap[key], primary[key], blind[key], cross[key]
    pos, locale = key
    assert c['sourceSha256'] == x['sourceSha256'] and c['currentTargetSha256'] == x['currentTargetSha256']
    assert c['callerContextSha256'] == x['callerContextSha256']
    assert p['sourceSha256'] == c['sourceSha256'] and p['currentTargetSha256'] == c['currentTargetSha256']
    assert b['sourceSha256'] == c['sourceSha256'] and b['currentTargetSha256'] == c['currentTargetSha256']
    assert b['callerContextSha256'] == c['callerContextSha256']
    rec = {
      'schemaVersion': 1, 'reviewStage': 'root-adjudication', 'exactHead': HEAD, 'exactTree': TREE,
      'position': pos, 'catalogZeroBasedIndex': c['catalogZeroBasedIndex'],
      'catalogOneBasedPosition': c['catalogOneBasedPosition'], 'locale': locale,
      'sourceSha256': c['sourceSha256'], 'currentTargetSha256': c['currentTargetSha256'],
      'callerContextSha256': c['callerContextSha256'], 'candidateFreeRowSha256': rowhash[key],
      'primaryDecision': p['decision'], 'blindDecision': b['decision'],
      'crossDisposition': x['crossDisposition'], 'confidence': 'moderate',
    }
    if c['callerless']:
      assert key not in selections and x['crossDisposition'] == 'hold-callerless-hash-only'
      rec.update({'callerless': True, 'rootDisposition': 'hold-hash-only', 'rootTarget': None, 'rootTargetSha256': None,
                  'sourceTextIncluded': False, 'currentTargetTextIncluded': False,
                  'rationale': 'No production caller is pinned; preserve the text-free hash-only hold.'})
    else:
      rec.update({'callerless': False, 'sourceId': c['sourceId'], 'source': c['source'],
                  'currentTarget': c['currentTarget'], 'sourceTextIncluded': True,
                  'currentTargetTextIncluded': True})
      if key in selections:
        disposition, target, rationale = selections[key]
        assert x['crossDisposition'] == disposition and x['crossRecommendedTarget'] == target
        assert p['decision'] in ('accept-current', disposition)
        assert textsha(target) == x['crossRecommendationSha256']
        rec.update({'rootDisposition': disposition, 'rootTarget': target, 'rootTargetSha256': textsha(target),
                    'crossRecommendationSha256': x['crossRecommendationSha256'], 'rationale': rationale})
        selected.append({
          'position': pos, 'locale': locale, 'sourceId': c['sourceId'], 'source': c['source'],
          'sourceSha256': c['sourceSha256'], 'currentTarget': c['currentTarget'],
          'currentTargetSha256': c['currentTargetSha256'], 'rootTarget': target,
          'rootTargetSha256': textsha(target), 'rootDisposition': disposition,
          'callerContextSha256': c['callerContextSha256'],
          'primaryDecision': p['decision'], 'blindDecision': b['decision'],
          'crossRecommendationSha256': x['crossRecommendationSha256'], 'rationale': rationale,
          'confidence': 'moderate'
        })
      else:
        assert x['crossDisposition'] == 'accept-current'
        rec.update({'rootDisposition': 'accept-current', 'rootTarget': c['currentTarget'],
                    'rootTargetSha256': c['currentTargetSha256'],
                    'rationale': 'Retain the exact-head translation; the caller-bound primary, blind, and cross-review found no material correction.'})
    counts[rec['rootDisposition']] += 1
    out.append(rec)
assert counts == {'accept-current': 223, 'correction': 2, 'refinement': 3, 'hold-hash-only': 12}
assert len(selected) == 5
(ROOT/'root-disposition-ledger.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out),encoding='utf-8')
(ROOT/'selected-targets.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in selected),encoding='utf-8')
input_files = {
 'candidateFreeCellsSha256': sha((CF/'candidate-free-cells.jsonl').read_bytes()),
 'candidateFreeManifestSha256': sha((CF/'manifest.json').read_bytes()),
 'primaryLedgerSha256': sha((PRIMARY/'ledger.jsonl').read_bytes()),
 'blindRowsSha256': sha((BLIND/'review-cells.jsonl').read_bytes()),
 'crossRowsSha256': sha((CROSS/'cross-review.jsonl').read_bytes()),
 'crossLineageFlagsSha256': sha((CROSS/'lineage-flags.json').read_bytes()),
 'crossRootFlagsSha256': sha((CROSS/'root-flags.jsonl').read_bytes()),
}
attestation = {
 'artifact': 'ROMarrNG W725-W744 root adjudication input attestation',
 'repository': 'snapetech-org/ROMarrNG', 'pullRequest': 70, 'window': 'W725-W744',
 'exactHead': HEAD, 'exactTree': TREE, 'cellCount': 240, 'selectedTargetCount': 5,
 'callerlessHashOnlyHolds': 12, 'blindCandidateFreePinsMatch': True,
 'inputs': input_files,
 'blindSummaryPositionDiscrepancy': {'summaryClaimsCatalogZeroBasedIndex': 731,
   'candidateFreePrimaryBlindRowsAndCrossRowsAgreeOnIndex': 732,
   'oneBasedPosition': 733, 'holdCells': 12, 'textRemainsRedacted': True},
 'inheritedLineageCaveatsPreserved': ['W625 missing stage files: readback remains hash-bound; absent files are not claimed verified',
   'W645 stale blind-summary checksum pointer: historical warning retained despite row checks',
   'W665 evidence restoration: 77 indexed payloads attested present and hash-matching'],
 'prVsMainContextDriftPositions': [726, 727, 729, 733, 735, 738],
 'rootAdjudicationPerformed': True, 'catalogsEdited': False, 'applicationPerformed': False,
 'nativeSpeakerApproval': False, 'headedBrowserReviewPerformed': False,
}
(ROOT/'input-attestation.json').write_text(json.dumps(attestation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary = {
 'artifact': 'ROMarrNG W725-W744 root adjudication', 'repository': 'snapetech-org/ROMarrNG',
 'pullRequest': 70, 'window': 'W725-W744', 'exactHead': HEAD, 'exactTree': TREE,
 'cellCount': 240, 'rootDispositionCounts': dict(counts), 'selectedTargetCount': len(selected),
 'selectedCorrectionCount': counts['correction'], 'selectedRefinementCount': counts['refinement'],
 'callerlessHashOnlyHolds': counts['hold-hash-only'], 'applicationPerformed': False,
 'nativeSpeakerApproval': False, 'headedBrowserReviewPerformed': False,
 'confidence': 'moderate', 'rootAdjudicationPerformed': True
}
(ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
