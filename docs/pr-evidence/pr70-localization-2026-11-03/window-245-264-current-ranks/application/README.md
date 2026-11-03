# ROMarrNG PR #70 W245–W264 application and readback

This packet records the application of 30 cross-audited catalog targets from the exact parent head `e7f8d0dcb11d8d94c8a89c37cb9ab451d72810a6` / tree `016587d26f04d2920a30878236f1933a57e27901`. All 240 cells across the 20 selected source IDs and 12 locales are covered.

Final dispositions: 138 accept-current, 14 corrections, 16 refinements, and 72 caller-path holds. The 72 held cells are kept as caller-path holds rather than translation-level decisions. Two blind corrections at position 259 (pt-BR and zh-Hant) remain deferred under that caller hold; no target was selected for those cells.

`plan-240-cells.jsonl` records the exact parent value, selected target, hashes, selection source, and cross-audit row hash. `readback-240-cells.jsonl` verifies each final value. Readback confirms 240/240 matches, exactly 30 planned target/hash updates, zero changes outside those values and their canonical translation hashes, preserved message/key order and metadata, and all caller-path holds unchanged.

The evidence is machine-assisted and does not establish native-speaker approval or authorize a release.
