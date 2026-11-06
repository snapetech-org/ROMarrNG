# ROMarrNG PR #70 primary localization review

This packet reviews the first 100 previously unaudited source IDs in the frozen English-only bundle `localization/source-bundles/20261101-connect-instructions.json`, in bundle order. It contains 1,200 source/locale cells across 12 locales. The selected IDs span source ordinals 1–105; ordinals 31, 32, 34, 40, and 51 were excluded because committed PR evidence already references them. Prior-review evidence contents were not opened; paths were used only to avoid re-reviewing covered IDs.

The review is pinned to PR #70 head `6db0b917343fc9fb605f8a4ecfbf9b4c21cebd1b`, tree `bfb778ba77849174a4670a70883c812183506b43`. `exact-head-attestation.json` records the live PR ref, remote PR head, frozen source bundle, catalogs, current target hashes, caller files, and line checks.

## Review results

- 547 cells: accept the current target.
- 159 cells: propose a correction.
- 86 cells: propose a refinement.
- 408 cells across 34 source IDs: hold the current target without approval because the exact-head caller is absent, ambiguous, dynamically composed without a matching template, or rendered as opaque API text.

Every row records the current and candidate targets, canonical content hashes, rationale, confidence, caller context, and placeholder, protected-literal, and markup checks. No native-speaker approval is claimed. `nativeSpeakerApproval` is `false` in every cell.

## Packet files

- `selection.json` and `preflight-attestation.json`: deterministic slice selection and initial source/target pins.
- `source-only-review-input.jsonl`: English source text, source hashes, source kind, and exact-head caller references; translated values are omitted.
- `current-target-pins.jsonl`: current PR-head targets and hashes, kept separate from the source-only input.
- `source-structural-baseline.jsonl`: source placeholders, markup, and protected-literal baseline for each cell.
- `manual-decisions.jsonl`: primary cell decisions before structural fields are joined.
- `primary-review.jsonl`: complete 1,200-cell ledger.
- `caller-context-reattestation.jsonl` and `render-path-evidence.jsonl`: exact-head evidence for no-caller, dynamic, opaque API, and other held cases, plus the resolved multiline Newznab/Torznab caller.
- `exact-head-attestation.json`: final PR-head, source/target hash, and caller-file attestation.
- `review-completion-checks.json`: coverage and structural check totals.
- `SHA256SUMS.txt`: checksums for packet files other than itself.

## Structural checks

All 1,200 candidate cells preserve the source placeholder set and protected literals. The selected English sources contain no markup tags; current and candidate markup checks match that empty baseline for all 1,200 cells. Any held cell retains its current target as an unapproved value.
