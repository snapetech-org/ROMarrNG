# ROMarrNG PR #70 — `ui.at` numeric-control cross-review

## Current-head finding

PR #70 is still open at `a1278acda1cea823443d7d6b712ed6ace8a99694` (tree `1e8a8d4fb191490a20bc443fb2b7bf24f05fa294`). At this head, the numeric control renders the complete source label `Requests per pass:` immediately before input `cpp` (min 1, max 50, default 5). A repository-wide scan of `romarr/**/*.py` found no `interfaceMarkup('at')` or `interfaceMarkup('per pass')` call; it found one `Requests per pass:` call at `romarr/ui.py:5554`.

The old `ui.at` key remains in the catalog, but its old fragment context is absent at this head. The four former unresolved translations (ja, ko, zh-Hans, zh-Hant) are therefore superseded for the visible numeric control. Their catalog cells remain contextless/unresolved; this review does not mark them linguistically accepted or edit/delete them.

## Cross-review result

| Scope | Count | Result |
| --- | ---: | --- |
| `ui.at.b1d6b91b67` catalog cells | 12 | Not referenced by current UI source; no standalone translation verdict |
| Prior `ui.at` unresolved cells | 4 | No longer part of the current visible control; remain unresolved as catalog rows |
| Current `ui.requests-per-pass.74961b68a5` control label | 12 | Accepted unchanged, moderate confidence |
| Placeholder mismatches | 0 | None |

The exact current full-label translations and code context are in `review-input.jsonl` and `source-context.txt`. Per-locale rationales and status reconciliation are in `review-decisions.jsonl`. All 12 current control labels say how many requests run in each pass/cycle/round and fit the adjacent numeric input.

## Overlap and frozen evidence

This is an intentional cross-review of the 12 `ui.at` rows already present in the older full-catalog review and adjudication. The prior outcomes reconcile to current catalog values: 5 corrections applied, 3 acceptable, 4 unresolved. The earlier adjudication was pinned to older source context; current source/catalog hashes and exact callsites are pinned in `manifest.json`.

The replacement full-label phrase has a separate exact-head 12-cell review at this same PR head. Its manifest and decision hashes are recorded in `manifest.json`; its verifier passed during this cross-review.

## Limits

This is AI semantic review, not native-speaker signoff. No fresh browser-rendered review was performed. The four standalone `ui.at` catalog cells remain unreviewed for out-of-context wording, although the current visible numeric control uses the reviewed full phrase instead. No source, catalog, review ledger, PR body, tests, builds, scans, or CI were changed or run. The shared Qwen model lock was occupied by a Seerr review and was not acquired or contended for.

## Files

- `review-input.jsonl`: exact current fragments, full label, prior dispositions, and hashes.
- `review-decisions.jsonl`: per-locale cross-review outcomes and limitations.
- `source-context.txt`: exact current numeric-control source lines.
- `callsite-inventory.json`: reproducible runtime helper occurrence search.
- `manifest.json`: live head/tree, files, counts, overlap, lock, and limitations.
- `verify_evidence.py`: frozen-input and checksum verifier.
- `SHA256SUMS.txt`: checksums for the evidence files.
