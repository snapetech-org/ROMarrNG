# ROMarrNG PR #70 W765–W784 primary review

This primary ledger uses the sealed candidate-free packet at `9714d7cf69c687685b4f65cbd9627a56830bab85` / tree `c8eb66573f10b2390a02df05033f5133425d5e41`. It covers 216 caller-backed cells and keeps 24 cells from two callerless sources as text-free hash-only holds. The candidate-free packet reattests 988 active prior holds, 144 applied cells, and ten full readback windows. This window adds 24 callerless holds, for 1,012 active hash-only holds.

Decisions: 206 accept-current, three corrections, seven refinements, and 24 callerless hash-only holds. The ten draft proposals refine “On this install” in seven locales, correct the French submission label, and use standard Simplified and Traditional Chinese API-key terminology. Placeholder, markup, numeric, and protected-literal checks pass for all proposals. Confidence is moderate; native-speaker and headed-browser review were not performed.

Provenance: no W765–W784 recommendation from another reviewer was read. After candidate-free sealed, the W745 primary builder script was consulted only for packet schema. It contains W745-specific hard-coded targets; none were reused as evidence or proposals here.

No repository/catalog files were changed. No tests, builds, scans, or CI were run. Verify with `python3 verify_primary_review.py`.
