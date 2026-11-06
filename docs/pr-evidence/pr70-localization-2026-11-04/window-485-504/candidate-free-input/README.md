# ROMarrNG PR #70 W485–W504 candidate-free packet

The candidate-free input is in `input/`. It is pinned to PR #70 head `6eb494d362ae19503b9199cd2c05c0767cddbc0e`, tree `b9450b9c6d22c816551fc8d528e8f03413d04595`, branch `task/localization-translation-review-20261030`.

The input covers catalog insertion indices 485–504, all 12 review locales, and 240 current target cells. It includes exact before/after PR attestations, current source/caller context and catalog pins, and hash-only lineage for 100 earlier selected sources and 444 held cells.

Verify from `input/` with `python3 verify_input.py`. The verifier checks file checksums, current-source/cell pins, lineage reattestations, and the candidate-free boundary.
