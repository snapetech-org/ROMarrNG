# ROMarrNG PR #70 W385–W404 rebased primary semantic review

This primary review is pinned to PR #70 head `0afd1d8c150fb96d868394a8d9620371db612185` / tree `0ba717d05c49356d8b1f55ac4a6b8844c161a402`. The live PR, branch, pull ref, and commit tree were attested in the sealed candidate-free input.

The candidate-free input contains 240 current locale cells and is sealed separately. All 288 predecessor hold cells reattest unchanged. The candidate-free packet records the new exact source-ID dispatch for positions 392, 396, 398, and 399; those 48 cells are reviewed here for the first time as renderable UI.

The earlier primary and cross-audit packets were checksum-verified and their packet verifiers passed before their decisions were read. All 240 prior primary rows and all 240 prior cross-audit rows were reattached to the same source IDs, source text/hashes, and current catalog target hashes. The 192 cells outside the resolved dispatch gaps carry forward the previous cross-audit reconciliation, including its 21-item change set, the Japanese unavailable-state adjudication, the Hindi/Indonesian TitleDB wording adjudications, and the Vietnamese Switch-family refinement. The prior 48 holds are superseded by the new semantic review.

For the newly renderable 48 cells, review yields 43 accept-current decisions and five proposed corrections: Korean, Simplified Chinese, and Traditional Chinese at position 392; Hindi and Indonesian at position 399. Every correction preserves the source meaning and the exact route; arbitrary API text and mismatched source details remain opaque. Placeholder, markup, numeric, ICU-shape, protected-literal, and product/pairing-surface checks pass.

An isolated second look on the same candidate-free inputs agreed with the Korean and Chinese position-392 corrections, accepted all position-396 and position-398 values, and found the Indonesian omission at position 399. Primary review also corrected Hindi 399 because its wording says “adding” rather than pairing, matching the earlier cross-audit hold note. Confidence for the new locale judgments is moderate overall (Indonesian 399 high). This is not native-speaker approval, and browser/native review was not performed. No repository or PR files were edited, and no tests, builds, CI, releases, or tags were run.

Run `sha256sum -c SHA256SUMS.txt` and `python3 verify-primary-review.py` in this directory to verify this packet. The verifier also checks the sealed candidate-free input and the referenced prior review packets.
