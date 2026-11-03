# ROMarrNG PR #70 W445-W464 preselection reattestation

Status: exact-head source, catalog, caller, and input reattestation passed. This packet does not contain W445-W464 cross-audit decisions or target selections.

## Live PR and pinned review input

- PR #70 was OPEN and DRAFT on branch `task/localization-translation-review-20261030`.
- Candidate-free and primary review packets are pinned to `d5ba7f1f268501f45227388c46d5f938ed0c9191` / tree `2f8ce1af963b315108f668fc31c94ca90ecd1351`.
- At reattestation, the live branch and pull refs both pointed to `81a499b7c022bde61a63dbd8c68c0b1ca39adf26` / tree `1b075e050610771fc5651d1a4ca95d7c7b4b8e46`. The PR base was `main` at `bcd1eb41b5cdf8202acb5cf8e365e14761b743b5`.
- The PR body contained the W425-W444 README and bundle-verifier links, with its applied marker present once.

## Exact-head reattestation

The candidate-free and primary packet checksum manifests and verifiers passed. All 240 candidate-free current-target cells match the primary ledger and the catalog blob at both heads. The 10 tracked Git pins collected from catalog, caller/source contexts, source-queue, primary, and the preliminary blind inputs have identical raw bytes, SHA-256 values, and Git blob IDs at d5ba and 81a. The record lists all source paths and pin evidence. It includes 29 caller-context references.

The d5ba-to-81a commit added 218 files, all under the W425-W444 evidence directory; no source, catalog, caller, or other application file changed. The candidate-free packet reattests 348 carried hold cells with zero target changes and 60 previously selected sources. Baseline input records zero placeholder mismatches, zero numeric mismatches, and one protected-literal mismatch at position 461 / pt-BR (missing `ROM`). This is preserved as an input observation; this reattestation makes no W445 target decision.

## Blind review status and selection gate

No sealed W445-W464 blind decision ledger was present. The copied blind input contains the same candidate-free packet, plus a preliminary registry-rank extraction. That preliminary extraction has zero source-ID overlap with the catalog-insertion selection and is explicitly excluded from cross-audit use. Do not use it to resolve primary/blind differences. W445-W464 selections remain gated until a sealed blind ledger is available and independently reconciled.

The primary review alone records 183 accept-current, 9 corrections, 12 refinements, and 36 caller-context holds (positions 458, 460, and 462). These are not cross-audit dispositions.

## Verification

Run `python3 verify_reattestation.py` from this directory. The offline verifier checks this bundle's checksums, both original packet manifests, the 240 cell alignment, catalog targets, all 10 included source blobs against their recorded SHA-256 and Git object IDs, carried holds/selections, evidence-only commit scope, PR/ref/body observations, and the blind-review gate. The kspls0-side builder is `build_reattestation.py`; it re-queries live PR/refs and the exact base/latest Git trees.

This packet claims no native-speaker review. No repository or PR changes, tests, builds, scans, CI runs, workflow edits, merges, releases, or tags were performed for W445-W464.
