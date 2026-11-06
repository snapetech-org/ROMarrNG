# ROMarrNG PR #70 W445–W464 application evidence

The cross-audit selected 21 target changes (8 corrections, 13 refinements) from 240 reviewed source/locale cells. The catalog commit is cece9856c8886ad5f07d2358e9399075da8b5254, parent 81a499b7c022bde61a63dbd8c68c0b1ca39adf26, tree 2b73ed0326786296a08270fd74a4d7f71217265e.

The pre- and post-apply catalog snapshots bracket the one-file catalog commit. The readback ledger records all 240 current and selected target hashes. It verifies 36 held cells, 348 carried holds, and 60 carried prior selections unchanged. Only romarr/ui-labels.json changed in the catalog commit.

Run python3 verify_apply.py in this directory. The verifier reads the sealed cross-audit packet from ../cross-audit/source-packet, checks snapshots, selected preimages and target hashes, all-cell readback, inherited holds/selections, commit pins, PR state, and the PR body section. Native-speaker and browser review were not performed; no tests, builds, scans, CI, workflow changes, merge, release, or tag were run for this window.
