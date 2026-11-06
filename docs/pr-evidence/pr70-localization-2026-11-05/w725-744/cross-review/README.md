# ROMarrNG PR #70 W725–W744 cross-review

Cross-review of all 240 cells at PR head `c3f92c45b4b4f8d79a8caa99417f9970ebc42a26` / tree `3f835643e4f557999d533c3e832fc92036d4b01a`.

- Dispositions: 223 accept current, 2 corrections, 3 refinements, 12 callerless hash-only holds.
- Primary and blind decisions differ on 4 caller-backed cells. Both propose the same Arabic correction for “Notes”; primary alone proposes the other four changes.
- The 12 held cells remain at zero-based catalog index 732 (one-based position 733). No source or target text is included in the cross-review or hold file.
- The blind summary says the callerless source is at index 731. Its 12 review rows, as well as the candidate-free and primary rows, bind to index 732. This summary-only off-by-one is flagged; the held cells were not moved.
- `root-flags.jsonl` records per-key issues and six PR-vs-main context drifts. `lineage-flags.json` preserves the W625 evidence caveat and W645 stale blind checksum-pointer warning, and records the W665 restoration attestation.
- Per-cell comparison: `cross-review.jsonl`. Hash-only hold ledger: `callerless-holds.jsonl`.
- Packet-specific results: `verifier-results.json`. Independent packet verifier: `verify_cross_review.py`.

Caller-backed review used the exact pinned PR contexts. The W625 note remains limited to missing stage files in the old evidence tree despite hash-bound readback; W645's stale top-level blind checksum pointer remains a warning despite passing row-level checks. W665 restoration is attested complete: all 77 indexed payloads are present and hash-matching. The inherited 340 source selections, 952 held cells, 132 applied cells, and eight prior readback windows were reattested unchanged.

No source/catalog edits, tests, builds, CI, native-speaker review, or runtime visual review were performed.
