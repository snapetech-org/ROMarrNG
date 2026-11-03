# ROMarrNG PR #70 W445-W464 candidate-free input

Pinned to PR head d5ba7f1f268501f45227388c46d5f938ed0c9191, tree 2f8ce1af963b315108f668fc31c94ca90ecd1351, branch task/localization-translation-review-20261030. The packet covers 20 messages at catalog insertion indices 445-464 (one-based positions 446-465) and all 12 review locales (240 current target cells).

Selection follows catalog insertion order in exact-head romarr/ui-labels.json, separately from the active ui-source-messages registry order. The packet includes the full 1,836-row catalog source inventory, 479-entry active source queue/snapshot pins, selected source hashes, exact tracked production source-id/source-text search results, hashed code context excerpts, and pinned translation dispatch mechanics.

Prior selection lineage is reattested for 20 entries each from W425-W444, W405-W424, and W385-W404. All 336 carried hold cells plus the 12 W425-W444 callerless holds are rechecked by source, catalog position or registry rank, locale, and current target hash (348 total).

This candidate-free packet contains current targets and token/literal checks only. It includes no proposed translations or current-window review decisions. The before/after PR attestation confirms the PR is OPEN/DRAFT and both branch/pull refs remain at the pinned head/tree.

Verify with python3 verify_input.py from this directory.
