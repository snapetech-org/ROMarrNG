# ROMarrNG PR #70 localization review — W485–W504

This bundle records candidate-free, primary, independent blind, third-party cross-audit, and catalog application evidence for 20 catalog entries across 12 direct locales (240 cells). The review input is pinned to PR head `6eb494d362ae19503b9199cd2c05c0767cddbc0e`, tree `b9450b9c6d22c816551fc8d528e8f03413d04595`.

## Review result

Primary and blind reviews agree on every disposition and selected value. The cross-audit reconciles 201 accept-current cells, 14 corrections, 1 refinement, and 24 holds, with no proposal conflicts. The holds are the callerless cells at catalog positions 493 and 502 across all 12 locales; no target text or proposal is recorded for those rows in the cross ledger.

The application applies exactly 15 cross-selected values in `romarr/ui-labels.json`: the 12 download-queue status labels, Japanese and Brazilian Portuguese standalone GitHub labels, and the Vietnamese file-header diagnostic. All 240 reviewed cells were read back. The catalog remains at 1,836 messages in the same key and locale order; all non-target values and metadata are unchanged. The 444 carried hold hashes and 100 prior selected source records remain unchanged.

## Evidence layout

- `candidate-free-input/`: exact source, caller, catalog, and current-cell packet.
- `primary-review/` and `blind-review/`: independent ledgers and their verification material.
- `cross-audit/`: 240-cell adjudication ledger, input pins, summary, checksums, and original verifier.
- `application/`: guarded apply plan, selected-change ledger, 240-cell readback, before/after catalog snapshots, lineage reattestation, commit records, checksums, and portable verifier.

Run `python3 verify_window_bundle.py --repo <ROMarrNG checkout>` from this directory to verify packet checksums, pinned review inputs, all 240 reconciled cells, exact catalog changes, the catalog commit, and the evidence files. The original cross-audit verifier was run on its source host, `kspls0`; this portable verifier maps its recorded input paths to the committed packet copies.

## Review limits

Qualified native-speaker approval and exact-head browser acceptance are not claimed. There were zero deployments, check runs, and Actions runs for the post-application catalog commit, so no exact-head UI preview was available. No tests, builds, scans, CI dispatches, workflow edits, merge, release, or tag were performed. PR #70 remains open and draft.
