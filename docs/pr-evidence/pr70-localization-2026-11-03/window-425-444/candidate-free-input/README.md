# ROMarrNG PR #70 W425-W444 candidate-free input

Pinned to PR head 7681ea470ee0f387cd3a1a5be0541979d9cd06f6, tree f8b34f29814233cb10dd9d608d5a69ce539b9f6d, branch task/localization-translation-review-20261030. The packet covers 20 messages at catalog insertion indices 425-444 (one-based positions 426-445) and all 12 review locales (240 current target cells).

Selection follows catalog insertion order in exact-head romarr/ui-labels.json, separately from the active ui-source-messages registry order. The packet includes the full 1,836-row catalog source inventory, 479-entry active source queue/snapshot pins, selected source hashes, exact tracked production source-id/source-text search results, hashed code context excerpts, and pinned translation dispatch mechanics.

Prior selection lineage is reattested for 20 W405-W424 entries and 20 W385-W404 entries. All 288 inherited hold cells and the 48 W405-W424 hold cells are rechecked by source, catalog position, locale, and current target hash (336 total).

This candidate-free packet contains current targets and token/literal checks only. It includes no proposed translations or current-window review decisions. The before/after PR attestation confirms the PR is OPEN/DRAFT and both branch/pull refs remain at the pinned head/tree.

Verify with python3 verify_input.py from this directory.
