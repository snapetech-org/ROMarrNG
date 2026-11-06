# ROMarrNG PR #70 localization review — W385–W404

Applied at base head `0afd1d8c150fb96d868394a8d9620371db612185` / tree `0ba717d05c49356d8b1f55ac4a6b8844c161a402` after candidate-free input, primary review, independent blind review, and exact-hash cross-audit of 240 cells across 20 sources and 12 locales. Reconciliation resolved 27 primary/blind disagreements into 211 accept-current cells, 25 corrections, and 4 refinements. Applied 29 exact-hash updates; 211 current values remain unchanged. No new holds were added, and all 288 carried holds remain unchanged.

The source-dispatch code fix in the base head makes 48 previously opaque cells source-bound at positions 392, 396, 398, and 399; all 48 were reviewed by both primary and blind streams. Five updates among those cells were selected: Korean and both Chinese scripts at 392, plus Hindi and Indonesian at 399.

`catalog-readback.jsonl` records all 240 reviewed cells. `catalog-invariants.json` records the full catalog preimage and result hashes, message ID/order preservation, exact 29-cell diff, and hold reattestation. The candidate-free, primary, blind, and cross-audit packets with their ledgers, verifiers, and checksums are retained in the adjacent folders.

Exact-head headed-browser review and qualified native-speaker review remain pending. No tests, builds, scans, CI, workflow changes, merge, release, or tag were made.
