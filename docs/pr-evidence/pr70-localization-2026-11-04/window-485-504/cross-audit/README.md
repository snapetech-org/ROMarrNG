# ROMarrNG PR #70 W485–W504 third-party cross-audit

The audit compares all 240 locale/source cells against the candidate-free input, primary review, and independent blind review, all pinned to head `6eb494d362ae19503b9199cd2c05c0767cddbc0e` and tree `b9450b9c6d22c816551fc8d528e8f03413d04595`.

The two reviews agree on all 240 dispositions and selected proposals. Cross-review adopts 14 corrections, 1 refinement, and 201 current values. There are no proposal conflicts. Callerless entries at catalog positions 493 and 502 remain held in all 12 locales; the cross ledger stores only current-target hashes for these 24 hold rows and contains no target text.

Independent adjudications cover the standalone Japanese and Brazilian Portuguese “GitHub” labels, the pending “Grabbing…” action in all 12 locales, and the Vietnamese file-header diagnostic at position 501. The selected target and rationale for each reviewed cell are recorded in `cross-ledger.jsonl`.

`input-pins.json` records byte hashes for every file in all three supplied packets, plus the head/tree and input manifest hashes. Run `python3 verify_cross_audit.py` from this directory to check the input pins, 240-cell reconciliation, expected selected targets, hold text-freedom, and output checksums. Qualified native-speaker approval, state-machine behavior validation, and browser acceptance are not claimed.
