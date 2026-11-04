# W505–W524 application evidence

This packet records the application of the sealed cross-review decisions to the exact PR #70 input head `e958b4fd0d9ddeac9333afc4c95da348b7f67cff` / tree `402026ba276ec4603d86d659766af836d839de55`.

The catalog-only commit is `b248261d5aaa33ec7247023b85d666ed7fc89309` (tree `08f73a3dec49091e40eef0b006519a6e06c239f4`), with the pinned input as its direct parent. It changes `romarr/ui-labels.json` only. The application updates the 28 exact selected translations and three matching canonical `translationHashes`; it retains all 140 current values, leaves all 72 held cells unchanged, and preserves every other catalog value and metadata field.

The complete preimage and postimage, guarded apply plan, 240-cell readback, selected-cell ledger, hash update ledger, and carried lineage records are under `evidence/`. The readback records no proposal text for callerless holds. The six held source positions are 505, 511, 513, 514, 515, and 523. All 468 carried holds and 120 previously selected source records were re-attested unchanged. The full sealed cross-review bundle is preserved as `../cross-audit.tar.gz` and unpacked to a temporary directory by the verifier.

Run the portable verifier from this directory or the repository root:

```sh
python3 verify_application.py --repo /path/to/ROMarrNG
```

It verifies the committed input and applied catalog blobs, cross bundle checksums and decisions, all 240 readbacks, catalog structure and metadata, the three canonical translation hashes, text-free holds, and carried lineage. The parent `verify_window_bundle.py` also checks the whole packet checksum manifest.

The review is machine-assisted contextual adjudication. It does not claim qualified native-speaker approval or exact-head browser acceptance. No tests, builds, scans, CI jobs, workflow changes, merges, releases, or tags were performed for this application. The local pre-commit scan hook was skipped under the task's no-scan instruction; the pre-push stable-image alias policy passed.
