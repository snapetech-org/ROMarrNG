# ROMarrNG localization W685–W704

This delivery covers catalog insertion positions 685–704 across 12 direct locales (20 messages, 240 cells) at review input PR head 43d2858744ef20cd58462643fed534ac61d2ffad / tree 73e8f50d65cb611def996b01bab0b00628b65860. The catalog change is commit a26feabfcae338207fae3d9c682425ab9c0d4226.

## Review and application

Candidate-free extraction found 228 caller-backed cells and 12 callerless cells. Primary review recorded 226 accept-current, one correction, one refinement and 12 hash-only holds. Independent blind review recorded 221 accept, five corrections, two refinements and 12 hash-only holds. Cross-review and root adjudication selected seven target changes (five corrections, two refinements), retained 221 current values and kept the 12 callerless values as text-free holds.

The product commit changes only seven translation cells in romarr/ui-labels.json. Post-commit readback confirms all seven targets, unchanged key order, and unchanged non-target values. All 12 direct locale catalogs retain 1,836 populated message entries.

The candidate-free, primary, blind, cross-review, root-adjudication and product-readback packets include their local checksums and verifiers. Run python3 verify_window.py --repo /path/to/ROMarrNG for the combined review and readback attestation. Individual packet checks can be rerun with:
- python3 candidate-free/verify_candidate_free.py
- python3 primary-review/verify_primary_review.py
- python3 blind-review/verify.py --inputs candidate-free/input --package blind-review

No build, test, scan, CI dispatch, workflow edit, deployment, merge, release, tag or qualified native-speaker approval is claimed. Exact-head headed-browser acceptance remains separately pending.

## Checksum note

The primary-review task-scratch packet contained one checksum entry for an untracked Python bytecode cache file. That cache remains preserved in task scratch and is omitted from the Git evidence copy. The copied primary-review checksum index drops only that absent cache entry; all review ledgers and other file hashes are unchanged.
