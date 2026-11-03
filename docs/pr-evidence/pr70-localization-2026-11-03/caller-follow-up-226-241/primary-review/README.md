# ROMarrNG PR #70 exact-caller follow-up primary review

This fresh primary review covers positions 226, 232, 237, and 241 across 12 locales: 48 current target cells. It is pinned to open draft PR #70 at head `e0cb91389334fe534ff44ccfc72cbb2c152a93b4` / tree `3876dd57816aaf75bb8b1a56a75a5045d216c461`. The candidate-free input is `/mnt/disks/scratch/task-scratch/romarrng-pr70-w226-followup-candidate-free-20261103/input`. Its SHA manifest passed, and every source/current-target hash was recomputed.

## Dispositions

- 33 accept-current
- 9 corrections
- 3 refinements
- 3 holds

The nine corrections and three refinements are at position 237 for the localized “On disk (plays now)” filter label, plus two wording refinements at position 241. Holds are position 241 in Hindi, Japanese, and Korean: the source is a fragment emitted before the Collections hyperlink, while natural word order in those languages needs the linked destination before a postposition. The current caller offers no localized continuation point after the link. The current fragment also lacks a complete load/destination relation in those three locales; keep these cells held until the caller can place the link inside the phrase.

Positions 226 (“no title”) and 232 (the fixed local missing-library detail) are accepted in all locales. Exact source shows position 226 uses an allowlisted app-owned error template. Position 232 is rendered only for the fixed `missing` verdict; the app discards peer-authored detail and uses the ROMarr-owned catalog template. Position 237 maps only app-owned `local` and `cloud` option values to translated labels and retains the option count. Position 241 is three text fragments around Metadata and Collections links; its fixed assembly explains the held word-order cases.

All 48 rows include exact current and candidate hashes, caller pins, confidence, rationale, placeholder, markup, numeric-token, whitespace, and protected-literal checks. Structural and protected-literal mismatches: zero. Native-speaker approval is not claimed. The review used only the candidate-free input and exact-head source/runtime evidence; it did not inspect prior W226 ledgers or other translation recommendations.

No repository or PR files were edited. No tests, builds, scans, CI, workflow, browser, merge, release, or tag actions were performed.
