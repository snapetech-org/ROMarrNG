# ROMarrNG PR #70 W565-W584 cross-selected application

Applied one cross-selected German translation to romarr/ui-labels.json in product commit 89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac. The exact selected value and reviewer hashes are in selected-changes.jsonl. The cross-review packet is copied under cross-review/ with its original verifier and checksums.

The full readback covers 240 cells: 199 keep-current, 1 applied change, and 40 text-free holds (36 callerless and four contextual Arabic count cells). Readback rows include source, pre-target, post-target, caller-context, and input-row hashes. Hold rows omit source IDs and all source/current/proposal text; selected target text appears only in selected-changes.jsonl.

Catalog key order, locale registry order, source strings/hashes, and translation metadata are unchanged. No other product file changed. Placeholder, markup, numeric, and protected-literal parity were checked across all 240 cells; mismatches: zero.

The PR remains open and draft. The PR API base SHA differs from live main; the existing base was left unchanged. Native-speaker review was not performed. No tests, builds, scans, CI, workflow edits, merge, release, or tag were made.

Verify with:

    python3 verify_application.py --repo /path/to/ROMarrNG --candidate-free /path/to/primary-packet/candidate-free/input --primary /path/to/primary-packet/primary --blind /path/to/blind-packet/output
