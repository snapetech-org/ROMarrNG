# Exact-head catalog application

The guarded script verifies the exact PR head, caller/catalog pins, all 240 root decisions, current target hashes, and the single-file catalog schema before changing only translation values and their canonical translationHashes. It then reads back all 240 cells and confirms draft status and message-key order.
