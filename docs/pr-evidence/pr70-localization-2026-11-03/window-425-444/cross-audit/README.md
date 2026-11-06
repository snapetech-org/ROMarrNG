# ROMarrNG PR #70 W425–W444 cross-audit

**Confidence: moderate.** The audit is pinned to commit `7681ea470ee0f387cd3a1a5be0541979d9cd06f6` and tree `f8b34f29814233cb10dd9d608d5a69ce539b9f6d`. It independently reconciles all 240 selected catalog cells against the exact-head candidate-free input, primary review, blind review, source/caller contexts, and the runtime localization code. No native-speaker claim is made.

## Scope and live state

- PR #70 remains OPEN and DRAFT on `task/localization-translation-review-20261030` at `7681ea470ee0f387cd3a1a5be0541979d9cd06f6`; the live pull ref and branch ref both match the pinned head. The tree is `f8b34f29814233cb10dd9d608d5a69ce539b9f6d`. Final pre-seal ref/tree recheck: `2026-11-03T19:54:08.986462+00:00`.
- The PR API base is `bcd1eb41b5cdf8202acb5cf8e365e14761b743b5` while live `refs/heads/main` is `bc1dee5df3d0dd88cdfe234f39ccc32f6eb86fe3`. These differ; the GitHub compare record is in `summary.json`. The branch was not rebased or modified.
- The candidate-free, primary, and blind packet checksums and bundled verifiers passed; the detailed command records are in `input-packet-verification.json`.
- All 23 candidate-free source/catalog file pins match the exact commit tree blob IDs, Git blob hashes, and expected file SHA-256 values. Drift count: 0.
- No repository or PR changes, tests, builds, scans, or CI runs were performed.

## Reconciliation

The primary/blind 240-cell comparison has 190 cells with the same disposition and effective target, 9 cells with the same target but different correction/refinement labels, and 41 cells with different effective targets. Every cell has one audited disposition, a selected target and exact SHA-256, per-cell rationale, caller evidence references, and token/literal checks in `audit-ledger.jsonl`.

Cross-audit decision counts: accept-current 194, correction 17, refinement 29. Current-window holds: 0. The inherited 336 prior hold cells and 40 prior selected sources remain reattested unchanged in the bundled candidate-free input and review packets.

## Notable decisions

- **W440 “Fern accent”:** resolved from 12 holds to accept-current. The exact pinned code enumerates the Fern accent, constructs `name + " accent"`, maps that source through `UI_SOURCE_TO_ID`, and attaches the resulting key to both the swatch title and aria-label. The catalog contains the exact W440 key/source, and all 12 locale translations equal the current targets. The source registration/caller snippets and full pinned `ui.py`/catalog files are bundled in `supplemental-caller-evidence.json` and `evidence/pinned-source/`.
- **W439 Chinese magnitude:** the source token `100` is rendered as `百` (one hundred) in `zh-Hans` and `zh-Hant`; both are recorded as accepted naturalizations. All other selected numeric tokens match exactly.
- The cross-audit retained the current Hindi action label for W430 and current Traditional Chinese “訂閱 URL” at W438 because each already works in its caller context; the proposed alternatives were optional wording. It selected the blind Hindi plural correction at W434 based on the exact dashboard counter caller.
- Primary refinements to the explanatory W431 export copy, technical W432 “Extensions” labels, W436 fan-translation language labels, and six W439 long-form examples were retained where they improve clarity or preserve the source. The available code context is bundled; exact-literal caller references absent from the input remain explicitly marked absent.

## Verification

- Selected targets: placeholder mismatches 0; protected-literal mismatches 0; exact numeric-token matches 238; semantically accepted numeric naturalizations 2.
- Run `python3 verify_cross_audit.py` from this directory for offline verification of the bundle checksums, input manifests, 240-cell alignment, selected target hashes, carried lineage, token/literal checks, W440 runtime evidence, source pins, and live-state attestations stored in the packet.
- `SHA256SUMS.txt` seals every packet file except itself. The verifier checks all entries and reports the packet file inventory.
