# ROMarrNG PR #70 W425–W444 primary review

This packet contains the independent primary review of all 240 locale cells for catalog positions 425–444. It was built from the candidate-free input only; no blind-review materials or proposals were opened. The live PR, branch and pull refs were reattested before and after review.

- Repository / PR: `snapetech-org/ROMarrNG` #70, OPEN/DRAFT
- Branch: `task/localization-translation-review-20261030`
- Reviewed head/tree: `7681ea470ee0f387cd3a1a5be0541979d9cd06f6` / `f8b34f29814233cb10dd9d608d5a69ce539b9f6d`
- Candidate-free input: `/home/keith/Documents/code/task-scratch/romarrng-pr70-w425-444-candidate-free-20261103/input`
- Candidate-free manifest SHA-256: `03462891dbf9a5a173cb7800583c18c888a0bde28879a83659b46cbb886d69c2`
- Candidate-free SHA256SUMS SHA-256: `0c4a48dc4766ccf845e703b7b8a3356210819c6c4e92ebc8a12f355711684746`

## Review result

- 240 cells reviewed: 181 accept-current, 9 corrections, 38 refinements, and 12 holds.
- The 12 holds are position 440 (`Fern accent`) in all locales. The candidate-free source/caller evidence has no active source registration or exact production source/caller occurrence for this string.
- The two position-439 Chinese numeric scanner findings were reviewed semantically. `百` means one hundred in both Simplified and Traditional Chinese and preserves the source magnitude 100; both current translations are accepted.
- Selected targets pass placeholder and protected-literal checks. Numeric checks pass exactly except for the two reviewed Chinese naturalizations above.
- Prior selection lineage (40 sources) and all 336 carried hold cells were reattested by the input packet verifier.

The ledger records current and proposed target hashes, exact caller-context references, per-cell rationale, token/literal checks and numeric adjudication. Browser review and qualified native-speaker review were not performed; this primary machine review does not claim either approval.

Run `python3 verify_primary.py` in this directory to validate coverage, evidence links, selected-target checks, packet hashes and the candidate-free input verifier. `SHA256SUMS.txt` seals the packet files; `manifest.json` records their hashes and the pinned inputs.

No repository, catalog, PR, test, build, or CI changes were made.
