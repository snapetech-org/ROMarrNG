# ROMarrNG PR #70 — next semantic-review window

This evidence-only pass reviews exactly 12 direct-locale cells for `ui.requests-per-pass.74961b68a5` (“Requests per pass:”) at PR head `a1278acda1cea823443d7d6b712ed6ace8a99694`, tree `1e8a8d4fb191490a20bc443fb2b7bf24f05fa294`. It uses the current checked-out catalog and UI callsite. It makes no repository, catalog, source, or PR-body changes.

## Result

All 12 current targets are accepted unchanged with moderate confidence as an AI semantic review. Placeholder/ICU and dynamic-value checks pass. This is not native-speaker signoff and does not include a fresh rendered-browser review.

| Locale | Cells | Decision |
| --- | ---: | --- |
| es | 1 | accepted unchanged |
| zh-Hans | 1 | accepted unchanged |
| hi | 1 | accepted unchanged |
| de | 1 | accepted unchanged |
| ja | 1 | accepted unchanged |
| fr | 1 | accepted unchanged |
| pt-BR | 1 | accepted unchanged |
| ar | 1 | accepted unchanged |
| ko | 1 | accepted unchanged |
| zh-Hant | 1 | accepted unchanged |
| vi | 1 | accepted unchanged |
| id | 1 | accepted unchanged |

Two values differ from the earlier 863d presence/hash inventory: Spanish now uses “ronda” and Hindi uses “चक्र”. This pass assesses those exact current values.

## Frozen input

- PR: https://github.com/snapetech-org/ROMarrNG/pull/70
- UI callsite: `romarr/ui.py:5550-5554`; the label precedes numeric input `cpp` (minimum 1, maximum 50, default 5) in the Collection planner.
- Whole-file hashes, source-context hash, per-cell raw-target hashes, prior inventory hashes, and exact counts are in `manifest.json` and `SHA256SUMS.txt`.
- Run `python3 verify_evidence.py` on the review host to recheck the frozen checkout and bundle.

## Scope and limits

This window is one source ID × 12 locales. It is disjoint from the prior 5,808-cell missing-cell review. The prior full-populated snapshot review accounts for 16,176 cells (15,876 target-identical at current head and 300 changed targets with correction evidence); the current catalog has 21,996 populated direct cells including this phrase. This bundle does not resolve four older context-dependent `ui.at` cells that remain unresolved in the prior adjudication artifact.

All 12 cells still need native-speaker validation. No native reviewer or browser-rendered review was performed for this window. No tests, builds, scans, or CI were run. The shared local-model lock was held by an active Seerr review, so this pass made no local-model call.

## Files

- `review-input.jsonl`: exact current values and prior-value comparison for each locale.
- `review-decisions.jsonl`: per-cell decisions, rationales, checks, and limitations.
- `source-context.txt`: frozen callsite lines.
- `manifest.json`: PR/head/tree, file hashes, source context, counts, preflight, and limits.
- `verify_evidence.py`: deterministic evidence and checksum verifier.
- `SHA256SUMS.txt`: checksums for all bundle files.
