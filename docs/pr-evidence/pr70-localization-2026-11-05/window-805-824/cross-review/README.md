# ROMarrNG PR #70 W805–W824 integrated cross-review

Pinned head/tree: 551cccd03e0acdce208ce11f571378c1dcdfb805 / d77f32ac8ec0ab53200d04819869a2e99c6de73c.

The integrated ledger covers all 240 caller-backed cells across 12 locales. It records exact source and current target text, their hashes, caller-context hashes and references, primary/blind decisions and proposals, the integrated target, and token audit.

## Reconciliation

- Primary proposals: 13
- Independent blind proposals: 23
- Overlap: 8 (4 identical and 4 differing, resolved against source/caller context)
- Primary-only proposals: 5
- Blind-only proposals: 15
- Unique proposal cells: 28
- Integrated actions: 13 supported target changes; 227 cells retain current wording.
- Ten low-confidence blind-only wording alternatives remain held at current targets. Five other moderate-confidence alternatives are retained as non-material style changes.
- Existing active hash-only holds: 1,012 older holds plus 48 W785 current-window holds copied byte-for-byte; 1,060 remain active. This W805–W824 window adds no callerless holds.

The 10 held cells are listed with exact current and proposed wording in unresolved-language-holds.jsonl: indices 805 ar/fr, 806 fr, 807 fr/ko, 820 de, and 821 de/es/fr/pt-BR.

## Input integrity and verification

Full SHA-256 and byte counts for every file in the three input packets are recorded in input-packet-checksums.json. Candidate-free outer and inner checksum lists, the predecessor checksum list, and primary/blind packet checksums were verified.

Run the integrated verifier with:

    python3 -B verify_integrated_cross_review.py

Verify output checksums with:

    sha256sum -c SHA256SUMS.txt

Confidence: moderate. Selected wording and held alternatives are machine review recommendations, not native-speaker-approved. No product worktree, repository, or PR was modified; no tests, builds, scans, or CI were run.

Next boundary: index 825, position 826 — ui.platform-for-game-available-platform.afd580990f, source SHA-256 afd580990fe9a12282ffeeeefa2d1a2c8b632f05bdd58b08e3c03a27ac91fb08.
