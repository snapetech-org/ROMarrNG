# W265–W284 application and exact readback

`plan-240-cells.jsonl` records all 240 source/locale cells, the pinned parent translation and canonical translation hash, the cross-audit disposition and exact expected target. It selects 34 updates. The 168 caller-path holds at ranks 269–282 have no selected target and must remain unchanged.

The exact readback confirms all 240 cell values, placeholder integrity, preserved message and locale order, unchanged review/status metadata, and changes limited to the 34 selected translation values and their canonical translation hashes. No tests, builds, scans or CI are part of this structural check.
