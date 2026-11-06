# ROMarrNG PR #70 W405-W424 candidate-free input

This packet is pinned to PR head `c146189f29db8fbd77d68dff0c33a0ab59a6b601`, tree `3db10f8b87577edd1167e4489524e6afbb50d556`, branch `task/localization-translation-review-20261030`. It contains the ordered 20 catalog entries at zero-based catalog insertion indices 405–424 / one-based positions 406–425 and all 12 locale targets (240 cells).

Selection uses the exact ordered IDs supplied for this task and verifies that they equal this catalog insertion slice. It makes no claim that the list is the next 20 entries in the active source registry sort. The pinned active registry contains only four of the selected IDs; its saved caller line hints are recorded but considered nonauthoritative where they disagree with current exact-head source excerpts.

`catalog-source-inventory.jsonl` makes the catalog insertion slice independently reproducible. `source-contexts.jsonl`, `dispatch-mechanics.json`, and `caller-search-audit.json` pin the current caller/dispatch route and explain holds at positions 405, 407, 408, and 416 (48 cells). All 288 carried holds from the prior W385-W404 candidate-free input are reattested against current catalog source and target hashes. The prior W385-W404 active-source selection is also reattested independently.

No proposed translations, review decisions, or primary/blind packet content is included. Verify with `python3 verify_input.py` from this directory.
