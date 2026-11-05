# ROMarrNG PR #70 localization review — W665–W684

This evidence packet covers source-order positions 665–684 at the exact open PR head `8b7589775c526866e474112b4f4168782b02f881` / tree `fb0ba93172f6832c687e001ce6c0fff08b5a33eb`. The PR base API ref was `bcd1eb41b5cdf8202acb5cf8e365e14761b743b5`; live `main` was `65d8747e3a068473396227bae5e85ddc71c7d4d8`. The base/main mismatch was preserved.

## Review and application

- Candidate-free, primary, blind, and independent cross-review packets each cover all 240 source × locale cells.
- Final dispositions: 139 retain-current values, 29 selected target translations, and 72 callerless hash-only holds.
- Cross-review chose 20 blind proposals, 5 primary proposals, and 4 primary/blind consensus values. Root review checked all 29 against their exact production caller contexts and approved each selected target.
- The application changes 29 locale values in `romarr/ui-labels.json` and refreshes 9 existing canonical translation hashes. Product commit: `38718aa6c60e3366aa67ba5372531b77d6539862`. Translation status/review metadata and catalog key order stay unchanged.
- Root confidence is moderate. No qualified native-speaker approval or headed product-browser acceptance is claimed.

## Packet layout

- `candidate-free/input/` records exact source, catalog, caller, and current-target state.
- `primary-review/` and `blind-review/` contain independent semantic reviews and text-free holds.
- `cross-review/` resolves all 240 cells and binds the proposals to the candidate-free rows.
- `root-adjudication/` records the root disposition of every cell.
- `application/` contains the exact-hash application plan, apply/readback output, and portable verifier.
- `SHA256SUMS.txt` covers every file in this evidence packet; each review subpacket also has its own checksums.

The candidate-free, primary, blind, cross-review, application readback, and checksum verifiers pass. `git diff --check` is clean. No tests, builds, scans, CI dispatches, workflow edits, merge, release, or tag were made for this window.
