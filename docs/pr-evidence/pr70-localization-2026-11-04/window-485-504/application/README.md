# Application evidence — ROMarrNG PR #70 W485–W504

Candidate-free parent: `6eb494d362ae19503b9199cd2c05c0767cddbc0e` / tree `b9450b9c6d22c816551fc8d528e8f03413d04595`

Catalog commit: `a662c3620e9b5df35092c9d302846b776638f462` / tree `a42bc330d836ccebea940366d3fd766dbd710e2d`

The exact-hash apply plan changes 15 reviewed values in `romarr/ui-labels.json` (14 corrections and 1 refinement). The 240-cell readback retains 201 current values, all 24 callerless holds, 444 carried holds, and 100 prior selected-source records. The catalog still has 1,836 messages; key order, locale order, source text, translation metadata, and all non-target values are unchanged.

Run `python3 verify_window_bundle.py --repo <ROMarrNG checkout>` from the window directory. It checks all packet checksums and ledgers, source/current/selected hashes, the catalog commit parent and tree, the changed-path scope, the full readback, and carried lineage.

The push-time stable-image policy hook passed. The pre-commit hook was not run because it launches Semgrep; the single catalog commit used an invocation-scoped empty hooks directory. No repository hooks were modified. No tests, builds, scans, or CI were run. Qualified native-speaker and exact-head browser review remain pending.
