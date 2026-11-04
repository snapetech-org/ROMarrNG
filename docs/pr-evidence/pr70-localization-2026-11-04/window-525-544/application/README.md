# W525-W544 application evidence

This packet records the application of the sealed cross-review decisions to the exact PR #70 input head eda48333438591ecc67f829c50ef2d521f1e7a5e and tree 3db18e56d0c7ac08a564a6baff61eba25f0a01da.

The catalog-only product commit is 63224167b0f89978a68977a7996bd06724d06129. It changes 18 reviewed translation cells in romarr/ui-labels.json. The 240-cell readback retains 210 current values and all 12 callerless position-530 cells; all 540 earlier holds, 28 earlier applied cell hashes, and 140 prior selected sources remain unchanged. Catalog message-key order, locale order, and unrelated metadata are preserved. No translation-hash fields needed updates.

The cross-review packet contains candidate-free, primary, and blind inputs; the per-cell cross decisions; selected changes; hash-only holds; exact PR attestations; checksums; and portable verifiers. The application verifier checks the exact product commit and catalog blob, the full readback, carried lineage, workflow boundary, and cross-review verifier.

At the product commit, PR #70 was open and draft with branch, API, and pull refs aligned. GitHub reported 0 check runs, 0 status contexts, and 0 deployments. The PR API base SHA differs from live main; it was not changed. Browser acceptance and qualified native-speaker signoff are not claimed. No tests, builds, scans, CI jobs, workflow edits, merge, release, or tag were made.

Run python3 verify_application.py --repo /path/to/ROMarrNG --input-repo /path/to/clean/pinned-input-worktree from this directory.
