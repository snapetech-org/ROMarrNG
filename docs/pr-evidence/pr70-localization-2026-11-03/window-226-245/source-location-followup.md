# ROMarrNG PR #70 W226–W245 source-location follow-up

At base `5f40792de016b9f811993caa27da2f6ae4a3aed6` / tree `3f9bb89c82985a743744f38de66252323735bdd4`, exact source inspection found two stale location hints in `romarr/ui-source-messages.json` for messages reviewed in W226–W245:

- `ui.no-title.8cb9a5c65b`: moved the source location from `romarr/app.py:4640` to the active `"no title"` error literal at `romarr/app.py:4793`.
- `ui.on-disk-plays-now.325a11ceda`: moved the source location from unrelated `romarr/ui.py:1828` to the active option-label literal at `romarr/ui.py:2068`.

The exact source IDs and source hashes are unchanged. These are metadata-only caller-location corrections; no catalog target or runtime behavior changed. Source context and exact current-head hashes are included in the next candidate-free caller follow-up packet.
