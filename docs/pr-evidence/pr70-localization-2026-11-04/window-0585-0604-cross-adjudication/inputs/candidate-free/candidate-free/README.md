# ROMarrNG PR #70 W585-W604 current-head candidate-free input

Pinned to OPEN/DRAFT PR head 01da053f0e6a47e7184fb86da77f66b7b6719653, tree dcb9c1766831e217ffca7fb77068b97c33b9524e, branch task/localization-translation-review-20261030. This fresh packet covers catalog insertion positions 585-604 (one-based 586-605), across all 12 review locales, for 240 cells.

The exact current pin is the W565-W584 evidence commit after product commit 89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac. Prior W565 candidate-free source and selection lineage, cross-review text-free holds, and full application readback were checksum-verified and reattested by source, target, and application hashes. Historical lineage carries 200 selected source IDs, 604 text-free held cells, and 49 applied target cells. This window has 2 callerless sources (24 cells).

The input contains current source and target text plus exact caller context for independent review. It contains no proposed targets or current-window decisions. The stale W585 primary packet was not used to produce this input.

Verify with `python3 verify_input.py --repo /mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w585-604-current-source` from `candidate-free/input`.
