# ROMarrNG PR #70 W345–W364 exact-head cross-audit

This task-scoped packet compares all 240 locale cells from candidate-free input against primary and blind reviews. It adjudicates translation text quality only and changes no repository file, catalog, caller/source pin, or pull request.

## Pins and scope

- PR #70 is open and draft on `task/localization-translation-review-20261030`.
- Exact head/tree: `6bef0c74632067906fd07279fa6bd3fd59159a48` / `4fd79e67f37e4c66d0253199418973d965a3fbd6`.
- W345–W364: 20 source IDs × 12 locales = 240 cells.
- Input: `/home/keith/Documents/code/task-scratch/romarrng-pr70-w345-364-primary-20261103/input`; primary review: `/home/keith/Documents/code/task-scratch/romarrng-pr70-w345-364-primary-20261103/primary-review`; blind review: `/home/keith/Documents/code/task-scratch/romarrng-pr70-w345-364-blind-20261103/blind-review`.
- All 288 prior callerless holds remain reattested unchanged; this window has no callerless cells.

## Comparison

- Target agreement: 137/240; target disagreements: 103.
- Disposition agreement: 158/240; disposition disagreements: 82.
- Combined differences: 112 (73 differ in target and disposition, 30 in target only, 9 in disposition only).
- Each cell has a resolved target, rationale, exact caller-context references, structural checks, and source/catalog/current/primary/blind/selected hashes in `cross-audit-ledger.jsonl`.
- Ranks 359–360 use exact task-loop semantics: searched counts Wanted entries; grabbed counts releases accepted by the download client, not completed downloads.

## Separate runtime follow-ups

Ranks **346** and **350** are app-authored strings with concrete callers, but the UI currently passes them through `apiMessageMarkup` as opaque text. Their catalog decisions remain text-quality review only. A separate source-bound runtime dispatch fix is required before catalog translations can appear in those paths. This audit leaves source and caller pins unchanged.

## Review limits

Confidence is moderate. Native-speaker approval remains pending; the catalog marks translations unverified. This is not headed-browser acceptance. No tests, builds, scans, CI, merge, release, or tag were run or requested.

## Files

- `cross-audit-ledger.jsonl`: 240 full adjudication records.
- `cross-audit-summary.json`: counts, hashes, and follow-ups.
- `live-head-attestation.json`: live pin readback.
- `create_cross_audit.py`: reproducible adjudication packet generator.
- `verify_cross_audit.py`: read-only verifier.
- `SHA256SUMS.txt`: hashes of all other packet files.
