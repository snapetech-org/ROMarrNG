# ROMarrNG PR #70 W485-W504 candidate-free input

Pinned to PR head 6eb494d362ae19503b9199cd2c05c0767cddbc0e, tree b9450b9c6d22c816551fc8d528e8f03413d04595, branch task/localization-translation-review-20261030. The packet covers 20 messages at catalog insertion indices 485-504 (one-based positions 486-505) and all 12 review locales (240 current target cells).

Selection follows catalog insertion order in exact-head romarr/ui-labels.json, separately from the active ui-source-messages registry order. The packet includes the full catalog source inventory, active source queue/snapshot pins, selected source hashes, exact tracked production source-id/source-text search results, hashed code context excerpts, and pinned translation dispatch mechanics.

Prior selection lineage is reattested for 100 sources: 20 entries from each of W465-W484, W445-W464, W425-W444, W405-W424, and W385-W404. All 384 carried hold cells plus 60 W465-W484 held-cell hashes are rechecked by source, catalog position or registry rank, locale, and current target hash (444 total).

This candidate-free packet contains current targets and token/literal checks only. Prior lineage is represented by hashes and reattested positions/targets. It contains no proposed translations or current-window review decisions. Separate before/after PR attestations confirm OPEN/DRAFT status and matching branch/pull refs at the pinned head/tree.

Verify with python3 verify_input.py from this directory.
