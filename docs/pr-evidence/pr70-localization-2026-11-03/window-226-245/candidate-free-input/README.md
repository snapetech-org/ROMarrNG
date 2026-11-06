# ROMarrNG PR #70 W226–W245 candidate-free input

This exact-head packet contains 20 source messages and 240 current target cells across 12 direct available locales. The open draft PR, remote branch, pull ref, and clean detached worktree are pinned to head `1ab8fd8b171afbfe43cd6998cde920f9f9b12b0c` and tree `c65a2206c95cd13b3eca5174aca2e4c812eff8bc`.

Selection uses one-based positions 226–245 in the 480 unique active source IDs, sorted lexicographically by ID. The source index has 482 records; duplicate IDs were merged and locations unioned. Exact source text/hash and source snapshot hash were checked against `romarr/ui-labels.json` for every selected message. `selection-boundary.jsonl` records rank 225, each selected position, and rank 246.

Current production caller references and adjacent context are pinned by file hash and Git blob. The source-index locations are retained separately from the current-head callsites. The localization runtime context records the automatic text-node path and the select-option exclusion.

## Holds

- Position 226: the API error has no `error_template`, and the UI sends it through `toastAppMessage` / opaque `apiMessageMarkup`; the separate capture skip reason is not a localized UI string.
- Position 232: the federation detail is passed to `apiMessageMarkup` without a detail template, so it remains opaque English.
- Position 237: the source appears in a select-option formatter without an option translation marker; select descendants are excluded from automatic text-node translation.
- Position 242: no distinct caller for the exact no-comma source was found; the only near match is the comma-prefixed position 241 phrase.

The rank-239 source-index line is stale, but its active concatenated settings help string was resolved at `romarr/ui.py:4444–4447`; see `caller-location-reconciliation.jsonl`.

This packet contains only source/current values and pins. It contains no proposed translations, semantic verdicts, or candidate targets. Machine review is not native-speaker approval.
