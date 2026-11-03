Clean source/current-value input packet for ROMarrNG PR #70, source ordinals 146-165.
The frozen queue is 20 source IDs × 12 locales = 240 cells in the pinned source-bundle order.
The preceding W126-W145 input selection ends at ordinal 145 and pins 146 as next.
This packet contains only frozen English sources, current locale targets, target hashes, exact-head caller context, and source structure. It contains no proposed translations or primary/independent/root dispositions.
All 20 sources are contiguous and have matching source hashes in the source bundle, catalog, and source snapshot. All 240 current targets are populated, draft, placeholder-compatible, and match their canonical stored translation hashes.
The exact-head caller-context search resolved production context for all 20 source IDs. Caller presence is separate: 19 have production code references; ordinal 160 (ui.integration-guide.6cfa2d0314, lowercase integration guide) has no current production-code caller. Its case-distinct neighbor is the separate title key ui.integration-guide.02a0a9e2c2. The caller-existence gate is therefore false and must not be represented as passed. The parent directed that ordinal 160 remain in the contiguous queue and its 12 cells receive hold-context.
The exact PR head/tree and catalog, source-bundle, source-map, snapshot, glossary, caller files, and preceding selection pins are in head-and-file-pins.json.
Verify SHA256SUMS.txt before review. This packet was created under task scratch only; the exact-head checkout and repository/PR were not edited.
The pinned source-message map provides location hints; current code references were searched and re-resolved against the exact head and are recorded in source-context.jsonl. No translation candidates are included.
