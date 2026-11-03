# ROMarrNG PR #70 localization review, W146–W165

This packet applies the 240-cell review for 20 source IDs across 12 locales at the live PR input head `db895a97e9871952a0b952e1d119e32e06cf168d` / tree `f1edf8319eb3dbd29ac5fe1e279216c5b96ecc6a`. The existing PR branch is `task/localization-translation-review-20261030` into `main`; it was open and draft when re-queried. See `live-pr-attestation.json` for the exact PR state, pre-push check status, and workflow trigger inventory.

## Ratification and application

The ratification accepts 168 current values, approves 37 corrections and 23 refinements, and holds 12 cells. The 60 approved changes are applied to `romarr/ui-labels.json`; every other catalog target is retained. The 12 locale cells at ordinal 160 remain held because the lowercase `integration guide` key has no exact-head production-code caller. Its case-distinct title neighbor has its own caller and does not satisfy the gate.

The exact source/current/final hashes, caller refs, caller file hashes and line text, per-cell dispositions, rationales, and comparison votes are in `adjudication/ratified-ledger.jsonl`. The frozen source/current input and all four review inputs are copied into the adjacent packet directories with their source checksums. `adjudication/ratify.py` reproduces the ratified ledger from those inputs and re-attests caller pins against the repository.

`application/apply-plan.json` pins the baseline and resulting catalog file hashes. `application/apply.py` reapplies the 60 approved corrections/refinements from the pinned head or verifies the completed result. `application/apply-readback.jsonl` records exact observed text, raw target hashes, canonical translation hashes, unchanged draft status, and caller pins for all 240 cells. `application/apply-summary.json` records the readback results.

The catalog retains all 1,837 message IDs, source values, locale keys, translation-status keys, and translation-hash keys. All 60 changed cells remain `draft`. The canonical translation hash is SHA-256 of the sorted-key compact JSON serialization of the target string; the readback also records raw UTF-8 target hashes. Placeholder and protected-literal checks passed, and all 348 caller references were re-attested.

## Review integrity and limits

The candidate-free ledger was sealed before any proposed translation text was read. Aggregate summary counts and changed-source/hash metadata were visible before sealing, so this is **not claimed as strict blind review**. The caveat is retained in the candidate-free summary and adjudication manifest. This machine review does not establish native-speaker approval, and this milestone has no headed browser review.

## Workflow and check effects

The live PR diff at the input head contained 30 changed files and no `.github/workflows` files. The checked-in workflows use tag-only push triggers or manual/workflow-run triggers; none listens to ordinary PR-branch pushes or `pull_request` synchronization. The input head had zero status checks. The pushed branch update is not expected to dispatch a workflow; this is rechecked after delivery.

The repository pre-commit hook runs Semgrep. It was skipped for this commit because this task forbids scans and organization policy requires them to run only on private ephemeral JIT. The configured pre-push hook performs read-only image-alias policy checks; no version tag or release is being pushed. No tests, builds, scans, CI dispatches, browser work, workflow edits, merges, tags, or releases were made for this milestone. The PR remains open and draft.

`SHA256SUMS.txt` covers every file in this packet except itself. The root `manifest.json` records the same file checksums and excludes its own hash.
