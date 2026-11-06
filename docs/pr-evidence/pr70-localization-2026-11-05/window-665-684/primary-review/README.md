# ROMarrNG PR #70 W665–W684 primary review

This is an independent review of the 240 cells in the candidate-free packet at PR head `8b7589775c526866e474112b4f4168782b02f881`, tree `fb0ba93172f6832c687e001ce6c0fff08b5a33eb`.

The review used only `../candidate-free/input/`. No other reviewer’s proposals or decisions were read. `ledger.jsonl` covers all 240 cells. `proposals.jsonl` contains changed targets only. The 72 callerless cells remain unchanged in `holds.jsonl`, with source and current-target text omitted; the ledger uses hash-based IDs for those records.

## Review results

- 168 caller-backed cells received semantic decisions; 72 callerless cells remain hash-only holds.
- Decisions: 153 accept-current, 9 corrections, 6 refinements, 72 hold-hash-only.
- The 15 proposals address the Spanish and Brazilian Portuguese platform toast, Arabic/Japanese/Vietnamese review statuses, Chinese and Korean game-release labels, French release wording, Arabic web-catalog wording, and the Korean Next label.
- The packet’s single numeric alert was reviewed: the values four and two remain intact, with Japanese using the ordinary digit 4 for four.
- The protected-literal alerts concern the English plural form `ROMs` in the netplay explanation. The target languages preserve the base acronym `ROM`, and retain `ROMarr`, `SHA1`, and `Super Mario Kart`; the plural is expressed in local grammar where needed. No change is recommended for that alert.

Confidence is high for 71 cells and moderate for 97 caller-backed cells; the 72 text-free holds have unknown semantic confidence. No native-speaker second review or runtime visual review was performed.

## Verification

Run from any directory:

```sh
python3 /path/to/primary-review/verify_primary_review.py
python3 /path/to/primary-review/verify_primary_review.py --repo /mnt/disks/scratch/task-worktrees/localization-20261105/romarrng-pr70-w665-684-pinned
```

The portable verifier checks the candidate-free input checksums, all 240 source/current/caller bindings, hash-only hold redaction, proposal coverage, target hashes, token preservation, output checksums, and the recorded exact-head attestations. The optional repository argument rechecks the clean detached worktree pin.
