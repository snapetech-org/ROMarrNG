# ROMarrNG PR #70 W245–W264 candidate-free input

This packet is pinned to open draft PR #70 at e7f8d0dcb11d8d94c8a89c37cb9ab451d72810a6, tree 016587d26f04d2920a30878236f1933a57e27901. It contains current source, current target values and hashes, exact caller/runtime contexts, structural/source metadata pins, and live PR attestation for 20 active source IDs × 12 direct locales (240 cells).

## Why the current window starts at 245

The sealed W226–W245 packet selected old ranks 226–245 from 480 unique IDs. Its old rank 242 was the orphan no-comma DAT source ui.or-load-no-intro-redump-dats-under.22540d7871, which the later PR update retired from active metadata and the catalog. The comma-prefixed phrase remains rank 241. Removing the orphan shifts old rank 243 (Organize a library you already have) to current rank 242, old rank 245 (Overwrite an existing file) to current rank 244, and the prior packet's unreviewed old boundary rank 246 (Owned check unavailable) to current rank 245. The active source index now has 479 unique IDs, so ranks 245–264 are the next 20 eligible IDs.

The latest PR body records caller-follow-up review for positions 226, 232, 237, and 241. The prior W226 window and caller-follow-up checksum manifests were revalidated; results and hashes are in PR-attestation.json.

## Caller and localization evidence

Every source-index line is treated as a hint. source-contexts.jsonl pins exact current production caller spans and adjacent context by file SHA-256, Git blob, line hashes, and context hashes. localization-runtime-context.json pins stable-key, template, automatic text-node, MutationObserver, accessible-name, and opaque-API rendering paths. caller-location-reconciliation.jsonl records source-index coordinates that differ from current caller spans.

All 240 current target values and exact translation hash entries are pinned in current-target-cells.jsonl. These are existing catalog values; the packet contains no proposed translations, semantic verdicts, or candidate targets. caller-resolution-holds.jsonl records 72 cells at positions 248–249 and 256–259 whose current caller has no safe localization path or whose exact source is not user-visible.

Machine review is not qualified native-speaker approval. Exact-head headed-browser review is not established by this source-only packet.
