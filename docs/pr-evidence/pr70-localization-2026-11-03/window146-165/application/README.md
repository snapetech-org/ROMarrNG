# W146–W165 catalog application

The script applies the exact 60 `correction` and `refinement` targets in `../adjudication/ratified-ledger.jsonl` to `romarr/ui-labels.json`. It pins the base PR head/tree, checks all 240 source/current hashes and caller file hashes/lines, verifies placeholders and protected literals, and re-reads all 240 locale cells after writing. The 12 ordinal-160 cells have no caller and remain held and unchanged.

From the repository root, reproduce the application at the pinned base with:

```sh
python3 docs/pr-evidence/pr70-localization-2026-11-03/window146-165/application/apply.py --apply
```

After applying, a plain invocation verifies the exact readback without changing the catalog:

```sh
python3 docs/pr-evidence/pr70-localization-2026-11-03/window146-165/application/apply.py
```

`apply-plan.json` pins the before/after catalog hashes and each changed source/current/final target. `apply-readback.jsonl` records the observed value, raw target hash, canonical `translationHashes` content hash, status, and caller pins for every cell. `apply-summary.json` records structural and hold-gate checks.

All changed targets remain `draft`. This is a machine review and does not establish native-speaker approval. No tests, builds, scans, CI dispatches, browser review, workflow changes, merge, tag, or release are part of this application.
