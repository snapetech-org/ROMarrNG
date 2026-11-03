# ROMarrNG PR #70 localization review and application — W425–W444

This repository evidence window contains the sealed candidate-free input, primary review, independent blind review, third-party cross-audit, and application evidence for 20 catalog entries × 12 locales (240 cells). The reviewed translation application is commit `d5ba7f1f268501f45227388c46d5f938ed0c9191`, tree `2f8ce1af963b315108f668fc31c94ca90ecd1351`, based on exact reviewed head `7681ea470ee0f387cd3a1a5be0541979d9cd06f6` / tree `f8b34f29814233cb10dd9d608d5a69ce539b9f6d`.

Final cross-audit dispositions are **194 accept-current, 17 corrections, 29 refinements, and no holds**. The application changed exactly 46 target values in `romarr/ui-labels.json` (17 corrections, 29 refinements). All 336 carried holds and 40 prior selected sources remain unchanged. Every one of the 12 W440 current labels was accepted after the sealed cross-audit verified exact source registration and caller mapping; the current wording was retained. The two Chinese `100`→`百` readings have explicit semantic numeric review.

## Packet contents

- `candidate-free-input/`: original frozen input packet and manifest.
- `primary-review/`: original primary ledger, packet manifest, and verifier.
- `independent-review/`: original blind ledger, embedded candidate-free evidence, manifest, and verifier.
- `cross-audit/`: original sealed third-party ledger and embedded review evidence.
- `application/`: original sealed 46-change application packet, readback, before/after catalog snapshots, and verifier.
- `verify_primary_portable.py`: companion to the unchanged primary verifier with only the candidate-free and primary packet paths made relative to this bundle.
- `verify_window_bundle.py`: verifies the bundle and runs each contained review/application verifier.

From the repository root, run:

```sh
python3 docs/pr-evidence/pr70-localization-2026-11-03/window-425-444/verify_window_bundle.py
```

The packet preserves the original manifests and checksum files. The primary portable companion is separate so it does not alter the sealed primary packet. This is machine-assisted contextual review; no native-speaker approval is claimed. Qualified native-speaker review and exact-head product-browser acceptance remain pending. No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were performed for this window.
