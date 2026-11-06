# PR #70 Nintendo guidance localization follow-up

This packet supports the exact-head correction work on ROMarrNG PR #70. Translation/caller findings are pinned to the pre-change PR head `d259a92f89657b5c79be3653ed811e2bf8e01c58` / tree `40d8b8d1dad55642774f5df2e646085f0fecf52b`. It contains no screenshots. Existing browser captures are not evidence for the follow-up head.

The 36-row editorial cross-review covers the two existing catalog IDs and the proposed Nintendo explanation in all 12 direct locales. Target values remain `draft`; no row claims native-speaker approval. The new Nintendo source is static app-owned text at `romarr/lists.py:858-861`, exposed by the local schema API (`romarr/app.py:6889-6892`) and rendered in `romarr/ui.py:2749-2757`. The separate `Nintendo` label stays escaped; the fixed explanation is rendered through `interfaceMarkup`.

A browser review of the committed follow-up head and qualified native-speaker review remain pending. No tests, builds, or CI jobs are represented by this packet.

SHA-256: `root-crossreview.jsonl` `a509e60ce0c3bdf218a945e99fa6c4191451fcb26254b4a23d7200a9de3ebfb6`; `source-context.json` `c64982c061bb29e54575acec2dc96f0868ff3f5feb854ddccce3ba0f7dbe3f63`.
