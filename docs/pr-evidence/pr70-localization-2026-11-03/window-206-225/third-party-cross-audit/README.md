# ROMarrNG PR #70 W206–W225 third-party cross-audit

## Scope and exact pins

This audit reconciles the candidate-free source/current input with the primary and independent blind reviews for all 240 cells (20 source positions × 12 locales). The live PR and remote branch were checked against the same exact commit and tree:

- Repository/PR: `snapetech-org/ROMarrNG` #70, open draft
- Branch: `task/localization-translation-review-20261030`
- Head: `bef31ca8a94f21273b11303524d79bd9c5344305`
- Tree: `7616d96ddd3a1bfe8078d43492eb5bea7213f080`
- Catalog: `romarr/ui-labels.json`, 1,837 keys per locale
- Pinned production caller references: 26 across 5 files

All three packet checksum manifests passed verification and the source packets are copied under `source-packets/`. Current caller spans and line hashes were used; the input manifest notes that some older source-index locations were stale at this head.

## Review reconciliation

| Measure | Count |
| --- | ---: |
| Cells reviewed | 240 |
| Primary proposed changes | 25 |
| Blind proposed changes | 30 |
| Both proposed a change | 21 |
| Same proposal text | 6 |
| Different proposal text | 15 |
| Primary-only / blind-only proposals | 4 / 9 |
| Rows with different recommendations | 28 |
| Third-party recommended changes | 34 |
| Holds | 12 |

Third-party dispositions: 194 accept-current, 22 corrections, 12 refinements, and 12 holds. Per-locale and per-position counts are in `cross-audit-summary.json`. The 28-row `primary-blind-disagreements.jsonl` includes differing proposal text and one-sided proposals.

The 34 recommendations are supported by the source strings and pinned caller contexts. Selected semantic distinctions include retaining the “listed” qualifier at position 206; using a release/publication term rather than a software-version term for the release-year sort at 207 German; plural tab labels for the newest-games collection at 208; launcher game-library wording at 215; and exact “no such friend” wording at 224 Korean. Every row in `cross-audit-ledger.jsonl` records both reviewers’ decisions, caller references and hashes, the third-party target or hold, rationale, and structural/literal checks.

## Rank 218 hold

All 12 locales remain on hold. Both reviews independently held the cells. The pinned `_gap` callers pass English `{what}` values `browse` and `answer for a date range`; the frozen packet does not establish whether those values are localized before interpolation. Since the surrounding sentence’s grammar depends on the inserted wording, the packet does not support changing or approving the current cells yet. `holds.jsonl` records all callers and exact hold rationale.

## Integrity and limits

All 240 source/current cells and review rows match the packet pins. Placeholder multiset and markup checks pass for source/current and proposed targets. There are 132 protected-literal occurrence checks, covering `DAT`, `DAT_PATH`, `JSON`, `No-Intro`, `PIN`, `ROM`, `ROMarrNG`, `Redump`, and `patch-catalog.d`; the primary, blind, and third-party violation counts are zero. See `protected-literal-audit.json`.

This machine-assisted semantic review is not native-speaker approval or browser acceptance. No repository/PR changes, tests, builds, scans, CI/workflow actions, or browser work were performed. The original packets and generated audit are retained; top-level `SHA256SUMS.txt` covers every file here except itself.
