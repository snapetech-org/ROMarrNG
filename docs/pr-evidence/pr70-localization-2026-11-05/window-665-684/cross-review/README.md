# ROMarrNG PR #70 W665–W684 cross-review

This packet independently adjudicates all 240 locale cells from the candidate-free input, primary review, and blind review. The 20 selected source IDs are bound to catalog positions 665–684 in the exact pinned PR tree.

## Pins

- PR: [snapetech-org/ROMarrNG#70](https://github.com/snapetech-org/ROMarrNG/pull/70), open draft
- Branch: `task/localization-translation-review-20261030`
- PR head/tree: `8b7589775c526866e474112b4f4168782b02f881` / `fb0ba93172f6832c687e001ce6c0fff08b5a33eb`
- PR API base: `bcd1eb41b5cdf8202acb5cf8e365e14761b743b5`
- Live main/tree at entry and exit: `65d8747e3a068473396227bae5e85ddc71c7d4d8` / `73a05379aa80fa629f69286338139247d2bfd849`
- The PR API base does not equal live main. That mismatch is recorded in both attestations and the manifest; no review input was rebound to main.

## Review result

- 240 cells: 139 accept current, 29 selected proposal wording, and 72 callerless hash-only holds.
- Selected wording: 20 blind, 5 primary, and 4 identical primary/blind consensus targets.
- One proposed Vietnamese wording for “Needs the Label plugin…” was rejected because it says “needs review” and drops both the plugin dependency and disabled-plugin behavior.
- All candidate/current/source and caller hashes reconcile to the exact candidate-free row. All 72 callerless rows omit source, current-target, candidate, and final-target text.
- The aggregate numeric and protected-literal alerts are retained and manually reviewed; see `summary.json` and per-cell notes in `cross-ledger.jsonl`.

## Files

- `cross-ledger.jsonl`: one final adjudication per cell, including lane evidence, proposal alternatives, final exact wording, confidence, rationale, and token status. Callerless rows are hash-only.
- `input-reconciliation.jsonl`: all 240 source/current/caller and lane record hash bindings; text is omitted.
- `exact-head-before.json`, `exact-head-after.json`: live PR, branch, base, main, and local worktree attestations.
- `manifest.json`, `summary.json`: scope, counts, pins, input digests, token findings, and limitations.
- `verify_cross_review.py`, `SHA256SUMS.txt`: portable offline packet verifier and checksums.

## Verify

From this directory:

```sh
python3 verify_cross_review.py
```

To also recheck the exact pinned worktree:

```sh
python3 verify_cross_review.py --repo /mnt/disks/scratch/task-worktrees/localization-20261105/romarrng-pr70-w665-684-pinned
```

The verifier reads the sibling `candidate-free/input`, `primary-review`, and `blind-review` folders, validates their checksum lists and all 240 row bindings, checks text-free holds, proposal provenance, target hashes, and packet checksums. It does not run tests, builds, scans, CI, or modify repository/PR files.
