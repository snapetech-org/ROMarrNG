# ROMarrNG PR #70 — first 100 selected source IDs

Review and application are pinned to PR head
6db0b917343fc9fb605f8a4ecfbf9b4c21cebd1b, tree
bfb778ba77849174a4670a70883c812183506b43. The reviewed set covers 100
selected source IDs (catalog positions 0–99; source ordinals 1–105), or 1,200
cells across 12 locales.

## Review

The primary review recorded 547 accept-current, 159 corrections, 86
refinements, and 408 holds. Independent review recorded 688 accept-current,
48 corrections, 56 refinements, and the same 408 holds. Root adjudication
resolved all 224 primary/independent differences and finalized 554
accept-current, 181 corrections, 57 refinements, and 408 holds. The holds
remain across 34 IDs where exact caller/render evidence was insufficient.

All 238 correction/refinement targets were reattested against the exact source
and catalog values, canonical hashes, locale, translation status, and source
fingerprint. The repository's canonical hash is SHA-256 over compact UTF-8
JSON serialization of the string scalar (ensure_ascii=False,
sort_keys=True, separators=(',', ':')), as implemented by
scripts/localization_review.py.

## Apply and validation

The 238 reviewed replacements and their translationHashes are applied to
romarr/ui-labels.json. Readback confirms every planned value and stored hash,
the catalog retains all 1,837 message IDs and each message's existing translation, status, and hash key sets,
and git diff --check passes. The primary, sealed independent review, root
adjudication, exact-hash apply plan, and readback records are retained here.
Nested packets retain their own checksums; archive-level manifests cover the
copied files.

No tests, builds, scans, CI dispatches, or application browser review were run
for this milestone. Exact-head deployment is unavailable. Qualified
native-speaker approval is not established; machine review is not a substitute.
