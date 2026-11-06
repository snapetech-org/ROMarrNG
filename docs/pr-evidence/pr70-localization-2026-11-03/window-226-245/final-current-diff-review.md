# ROMarrNG PR #70 W226–W245 final current-diff review

## Scope and exact pins

This final review covers the complete candidate diff against PR head `1ab8fd8b171afbfe43cd6998cde920f9f9b12b0c` (tree `c65a2206c95cd13b3eca5174aca2e4c812eff8bc`). The candidate worktree diff SHA-256 is `46dd5abba984e37b1c51c1d4ab9462674db6a53ad821021b8f5f8659ab5d32de`. Changed files are the localization roadmap, `romarr/app.py`, `romarr/ui.py`, the active source-message index and source snapshot, and `romarr/ui-labels.json`.

## Review result

The translation application readback matches all 31 cross-audit-selected targets and their hashes. The 26 active held cells retain their prior text, hashes, status, and review metadata. Twelve translations for the orphan no-comma source entry were removed from the active catalog together with that entry's active source metadata and snapshot record; historical source bundles remain untouched. No non-target translation values changed.

The first current-diff review identified a conditional inherited-property lookup in the Stats source breakdown. The current code now uses `ownLabel(SOURCE_LABEL, k) ?? k`, consistent with the facet renderer, which safely preserves unknown source values. The correction was re-attested against final `romarr/ui.py` Git blob `a99731cc16d32a6e7385108d07de057097bda722` (SHA-256 `732486b957967ecde0457be53f8f70bf6675df5c9d7d340bb2c2d963bb23661a`).

The no-title route uses a fixed local allowlisted template. Netplay replaces peer detail for the exact local `missing` verdict with a local template; peer-provided template text is not forwarded. Facet labels translate only explicit app-owned values, keep counts separately, and reformat counts after language changes. Dynamic values remain escaped and opaque.

## Limitations

This is a source and evidence review. It does not establish native-speaker approval or current-head browser acceptance. No tests, builds, scans, CI dispatches, or workflow changes were performed for this window.
