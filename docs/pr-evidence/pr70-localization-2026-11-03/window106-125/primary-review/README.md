# ROMarrNG PR #70 primary localization review: ordinals 106–125

This scratch-only review packet covers the next sequential window of 20 source IDs from the frozen populated-cell/source queue at PR head 5f0973fb211c24d9b408cdb85c572540a7ab17ff, tree e8668e9c83afa533f8cd6e69e6a7ad96946ed40e. The frozen English source bundle contains 484 messages and 5808 pending direct-locale cells. The earlier primary packet selected its 100 eligible source IDs through ordinal 105; the pinned eligibility audit placed the next eligible sequence at ordinals 106–209. This packet takes ordinals 106–125: 20 IDs × 12 locales = 240 cells.

All 240 current targets are populated, marked draft, and re-attested against the exact current catalog hashes. The review dispositions are: 144 accept current, 15 correction, 9 refinement, and 72 hold. Six source IDs (72 cells) remain held for absent callers or opaque API-rendered text. Their current values are retained without approval. No native-speaker approval is claimed.

One existing held target, Indonesian for the raw gamelist.xml error, changes the filename case. It remains unapproved with the caller hold; the mismatch is recorded in review-completion-checks.json and does not count as an approved-candidate pass.

## Packet files

- selection.json and preflight-attestation.json: pinned source queue, prior primary selection, and initial hash checks.
- source-only-review-input.jsonl: source text and exact-head code references without target values.
- current-target-pins.jsonl: exact current target values and stored/canonical hashes.
- source-structural-baseline.jsonl: per-cell placeholder, markup, and protected-literal baseline.
- manual-decisions.jsonl and primary-review.jsonl: primary judgments, target candidates, rationales, confidence, and structural checks.
- caller-context-reattestation.jsonl and render-path-evidence.jsonl: exact-head evidence for all six held IDs and translation paths.
- exact-head-attestation.json: final PR API head/tree and exact catalog/source/target re-attestation.
- SHA256SUMS.txt: checksums of all packet files other than itself.

No independent reviewer packet contents were read. No repository file or PR was modified; no tests, builds, CI, browser review, or release actions were run.
