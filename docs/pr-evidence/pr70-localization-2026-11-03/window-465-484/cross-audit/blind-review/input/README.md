# ROMarrNG PR #70 W465-W484 candidate-free input

Pinned to PR head 7640720c5e3b1813725cca8d7aa46b5d968bff43, tree bdee162cc11115256df8756f192b19d4337ed1dc, branch task/localization-translation-review-20261030. The packet covers 20 messages at catalog insertion indices 465-484 (one-based positions 466-485) and all 12 review locales (240 current target cells).

Selection follows catalog insertion order in exact-head romarr/ui-labels.json, separately from the active ui-source-messages registry order. The packet includes the full 1,836-row catalog source inventory, 479-entry active source queue/snapshot pins, selected source hashes, exact tracked production source-id/source-text search results, hashed code context excerpts, and pinned translation dispatch mechanics.

Prior selection lineage is reattested for 20 entries each from W445-W464, W425-W444, W405-W424, and W385-W404 (80 total). All 348 carried hold cells plus 36 W445-W464 callerless holds are rechecked by source, catalog position or registry rank, locale, and current target hash (384 total).

This candidate-free packet contains current targets and token/literal checks only. It includes no proposed translations or current-window review decisions. The before/after PR attestation confirms the PR is OPEN/DRAFT and both branch/pull refs remain at the pinned head/tree.

Verify with python3 verify_input.py from this directory.
