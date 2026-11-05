# W745–W764 exact-hash application

`apply_exact_hash_plan.py` applies only the seven root-selected cells after checking the reviewed PR head, source/current-target hashes, caller-context hashes, tokens, and clean starting worktree. `readback-before-commit.json` records all seven before/after values and checks that all other catalog cells and key order remain unchanged. After the catalog milestone commit, `finalize_readback.py` binds the catalog hash to that exact commit and its parent.
