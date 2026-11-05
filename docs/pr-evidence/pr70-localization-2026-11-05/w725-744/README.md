# ROMarrNG PR #70 W725–W744 localization review

This window reviews 20 source entries across 12 direct locales (240 cells) at input head `c3f92c45b4b4f8d79a8caa99417f9970ebc42a26` / tree `3f835643e4f557999d533c3e832fc92036d4b01a`.

## Root decisions and application

Candidate-free review found 228 caller-backed cells and 12 callerless cells. Primary review recorded 223 accept-current, two corrections, three refinements, and 12 hash-only holds. Blind review retained 227 values, proposed one correction, and held the same 12 cells as text-free hashes. Cross-review and root adjudication retain 223 current values, select two corrections and three refinements, and preserve the 12 callerless cells as hash-only holds.

The five selected catalog changes are German wording for a pending set acquisition, Korean “not announced” for a missing release date, German standalone-label capitalization, Arabic general “Notes,” and a German upcoming-game empty state that names release dates. The product commit [`19038831e63edd53e4aec62f072c6d2eda9245cd`](https://github.com/snapetech-org/ROMarrNG/commit/19038831e63edd53e4aec62f072c6d2eda9245cd) changes only five cells in `romarr/ui-labels.json`. Exact readback preserves catalog key order and every non-target cell; all 12 locales retain 1,836 nonempty messages.

All 12 callerless holds are at zero-based index 732 (one-based position 733), with source and target text redacted. The blind summary alone says index 731; each blind row and the candidate-free, primary, and cross-review rows bind to index 732. The discrepancy is recorded without moving the holds. Six source/caller contexts drift from current `main`; reviews remain pinned to exact PR callers and preserve those flags. Prior W625 and W645 evidence caveats remain visible, and W665 restoration is attested as 77 of 77 indexed files present and hash-matching.

## Evidence and limits

The candidate-free, primary, blind, cross-review, root-adjudication, and product-readback packets are retained here with checksums. Run `python3 verify_window.py --repo /path/to/ROMarrNG` for the combined offline review/readback verification. This verifies catalog and evidence integrity; it is not a product test suite.

Machine review confidence is moderate. Qualified native-speaker approval and exact-head headed-browser acceptance remain pending. No tests, builds, scans, CI dispatches, workflow changes, deployment, merge, release, or tag are claimed for this window.
