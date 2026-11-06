# ROMarrNG PR #70 W445–W464 exact-head cross-audit

This is a third-party cross-audit of the sealed candidate-free, primary, blind, and preselection-reattestation packets. It is pinned to candidate/primary head `d5ba7f1f268501f45227388c46d5f938ed0c9191` / tree `2f8ce1af963b315108f668fc31c94ca90ecd1351` and independently reattested to live PR head `81a499b7c022bde61a63dbd8c68c0b1ca39adf26` / tree `1b075e050610771fc5651d1a4ca95d7c7b4b8e46`. The PR remained OPEN/DRAFT on `task/localization-translation-review-20261030` with branch and pull refs equal to the live head before and after sealing.

## Result

The 240-cell resolution is **183 accept-current, 8 corrections, 13 refinements, 36 holds**. Each cell in `cross-audit-ledger.jsonl` carries its selected target and UTF-8 SHA-256, exact source/current hashes, caller references, primary and blind decisions, rationale, and recomputed token/protected-literal checks. The 36 cells at ranks 458, 460, and 462 remain held because the exact production caller scan found no source-ID or source-text caller; their selected target/hash records the current text while disposition remains `hold`.

The primary and blind ledgers have 58 reconciliation rows: 36 hold representation differences (primary leaves selected target null while blind records unchanged current text), 21 substantive non-hold target disagreements, and one primary-proposal/blind-selection consensus at rank 452. There are 20 disposition disagreements; rank 457 Hindi has a target disagreement while both reviews label it a correction. The cross-audit adopts the blind Hindi correction at rank 453, accepts the current pt-BR Flood wording at rank 453, and uses the primary ROM-literal correction at rank 461. See `primary-blind-reconciliation.jsonl` for all rows and caller evidence.

All 348 carried holds and 60 prior selections are retained. The baseline protected-literal mismatch at rank 461 pt-BR is corrected in the proposed cross selection. All selected placeholders, numeric tokens, protected literals, and named terms pass. No catalog value was applied. No tests, builds, scans, CI, browser review, or native-speaker review were run or claimed.

## Exact-head reattestation

The W445 candidate/primary packets were prepared at d5ba; the live head advanced to 81a with a docs-only evidence commit. The cross-audit rechecked the ten relevant Git pins, nine pinned source/catalog/caller files, 20 source definitions, 240 current target preimages, and 319 caller-context lines. All remain byte-identical, so no source/catalog/caller drift is detected. The live base is `main` at `bcd1eb41b5cdf8202acb5cf8e365e14761b743b5`; GitHub compare reports the branch ahead by 73 commit(s), behind by 0, with merge base `bcd1eb41b5cdf8202acb5cf8e365e14761b743b5`.

## Packet contents

- `romarrng-pr70-w445-464-candidate-free-20261103/input/`: complete sealed candidate-free input packet and its verifier.
- `primary-review/`: byte-preserved primary packet and verifier.
- `blind-review/`: byte-preserved blind packet, including its live-head source/caller/cell preimage attestation.
- `preselection-reattestation/`: byte-preserved d5ba-to-81a preselection attestation; its sealed “await blind” gate is intentionally unchanged.
- `cross-audit-ledger.jsonl`: all 240 selected decisions.
- `primary-blind-reconciliation.jsonl`: all 58 reconciliation rows.
- `source-pin-attestation.json` and `actual-git-object-reattestation.json` record the independently recomputed d5ba/81a Git pins, 240 catalog preimages, and 319 caller lines; live PR attestations and `reconciliation-summary.json` record the ref checks.
- `verify_cross_audit.py`, root `SHA256SUMS.txt`, and its SHA-256 sidecar.

Run `python3 verify_cross_audit.py` from this directory for offline verification. The verifier also runs each copied input/review/reattestation verifier in its preserved layout.
