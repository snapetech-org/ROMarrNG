# ROMarrNG PR #70 W445–W464 localization evidence

This bundle contains the sealed candidate-free input, primary review, blind review, third-party cross-audit, and application/readback evidence for 20 source messages × 12 locales (240 cells).

The exact-head cross-audit resolved the 240 cells as 183 accept-current, 8 corrections, 13 refinements, and 36 holds. The application changed exactly 21 values in romarr/ui-labels.json. All 36 held values, 348 carried holds, and 60 carried selections remain unchanged. The rank 453 Hindi correction is applied, rank 453 pt-BR remains current, and the rank 461 pt-BR ROM literal is corrected.

## Bundle layout

- cross-audit/source-packet/: original sealed third-party cross-audit packet, including its embedded candidate-free input, primary and blind reviews, preselection reattestation, source/caller pins, and verifier.
- application/: exact selected-change ledger, pre/post catalog snapshots, 240-cell readback, inherited hold/selection reattestations, catalog commit evidence, PR body update, and portable verifier.

Run python3 docs/pr-evidence/pr70-localization-2026-11-03/window-445-464/verify_window_bundle.py from the repository root. It verifies the complete checksum inventory, the sealed cross-audit packet, and application invariants.

Catalog commit: cece9856c8886ad5f07d2358e9399075da8b5254, parent 81a499b7c022bde61a63dbd8c68c0b1ca39adf26, tree 2b73ed0326786296a08270fd74a4d7f71217265e.

Native-speaker and browser review were not performed. No tests, builds, scans, CI, workflow edits, deploys, merges, releases, or tags were run for this window.
