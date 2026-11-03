# ROMarrNG PR #70 W226–W245 primary/blind cross-audit

## Pins and evidence

The candidate-free packet and both review packets passed their checksum manifests. All 240 source/locale cells in primary and blind ledgers match candidate-free source IDs, source hashes, current targets, target hashes, catalog hashes/blobs, and exact head/tree pins. Live PR #70 is OPEN/draft on `task/localization-translation-review-20261030`; both the branch ref and pull ref resolve to `1ab8fd8b171afbfe43cd6998cde920f9f9b12b0c`. Tree: `c65a2206c95cd13b3eca5174aca2e4c812eff8bc`.

The exact uncommitted worktree diff is SHA-256 `fe626fe75602d505a6e3e51234edea26dc1a85d467eeb6d9810d00eda67587e8` (saved as `worktree.diff`); the worktree remains changed only in `romarr/app.py`, `romarr/federation.py`, and `romarr/ui.py`.

## Reconciliation

- Both reviews cover 240 cells and agree on all 48 original caller holds and 154 accept-current cells. Four proposal cells have identical targets. There are 34 divergent recommendations requiring adjudication; the per-cell ledger records the complete reconciliation.
- Position 226’s new local error template is narrowly allowlisted, has no interpolation values, and falls back to escaped opaque API text. The 12 translations can proceed.
- Position 232 remains held: `detail_template` is created locally but dropped by `netplay_invite`. Forward it only for the local RomM missing verdict; never forward a peer-provided template.
- Position 237 remains held: the new translation path deletes option counts when `applyTranslatedLabel` replaces option text. It also performs exact-source localization lookup on unformatted external values, creating an exact-collision risk. Preserve and reformat counts; translate only explicitly app-authored option labels.
- Position 242 is an orphaned active catalog/source-metadata entry. Its recorded line is stale; the active production call is the distinct comma-prefixed position-241 source. Recommend removing the no-comma key from active metadata/catalog/current snapshot, preserving historical bundles, and recomputing source-window boundaries.
- One integrity discrepancy: primary proposes Arabic position 227 without the literal `ID`; blind marks `ID` protected and accepts current. The primary’s protected-literal check did not inspect its proposed target. Do not apply that candidate without explicit adjudication.
- Blind’s Simplified and Traditional Chinese position-239 recommendations are clause fragments, not complete-cell translations. A safe refinement must preserve the rest of the paragraph; full-cell candidates are recorded in the reconciliation ledger.

No repo/PR changes, tests, builds, or CI were performed. Recommendations are machine-assisted, not native-speaker approvals.
