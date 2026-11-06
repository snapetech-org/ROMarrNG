# ROMarrNG PR #70 W265–W284 candidate-free input

Pinned to the open draft PR at head `c135c4729582817273c946891186ab4ea87467b5` / tree `32c07150396335a5832b5664fc1e0225d7cebdc1`. The packet covers 20 active source IDs and 240 current target cells across 12 locales.

Selection uses current one-based ranks 265–284 among 479 unique active source IDs sorted lexicographically by source ID. Boundary records include rank 264 (`Project`) and rank 285 (`Published {entries} ES-DE entries and {covers} shared covers.`). Source IDs, source hashes, the source snapshot, locale files, caller files and exact caller contexts are pinned. Source-index locations that no longer match the current code are separately reconciled.

Positions 269–282 (168 cells) are held because their dynamic metadata-provider and Prowlarr diagnostics are returned as raw API strings and rendered via `apiMessageMarkup` without explicit source-template metadata. Dynamic provider names, operation/needs values, exception types and HTTP status codes remain opaque. No targets are selected for held cells.

The packet contains no proposed translations or semantic decisions. Placeholder integrity, stable IDs, current values, ordered locale definitions and source/caller hashes are recorded for independent primary and blind review. Machine review does not establish native-speaker approval.
