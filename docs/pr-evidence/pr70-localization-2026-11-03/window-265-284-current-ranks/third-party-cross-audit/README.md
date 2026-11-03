# Cross-audit evidence packet

Read-only reconciliation of ROMarrNG PR #70 ranks W265–W284 at exact head/tree. `cross-audit-ledger.jsonl` contains all 240 rows; `summary.json` holds counts and selected targets; `disagreement-and-hold-summary.json` contains disagreement and hold detail; `attestation.json` records scope and limitations; `pinned-state-verification.json` captures the live PR/ref and exact worktree/source-pin verification.

Run `python3 verify_cross_audit_evidence.py` from this directory to verify source packet checksums, row-level input/reviewer lineage, dispositions, holds, target hashes, placeholder integrity, and this packet's checksum list. The verifier is read-only.

The blind review packet explicitly records separate hashes for the candidate manifest JSON and its checksum list. These recommendations are not native-speaker approval or release approval.
