# ROMarrNG PR #70 W665-W684 blind review

This sealed packet contains an independent semantic review of 240 cells (20 insertion-order source keys × 12 locales) at PR head `8b7589775c526866e474112b4f4168782b02f881`, tree `fb0ba93172f6832c687e001ce6c0fff08b5a33eb`. It uses only candidate-free input and caller context.

`ledger.jsonl` records every cell. `proposals.jsonl` contains 24 defensible corrections/refinements. `holds.jsonl` contains 72 callerless hash-only holds; those rows contain no source key, locale, source text, or current target text. Scanner flags are recorded and judged in context.

Run `python3 verify_blind.py` for portable structure/checksum verification. To bind every row to the candidate-free cell data, run `python3 verify_blind.py --candidate-free ../candidate-free/input/candidate-free-cells.jsonl`. The verifier does not read another review packet or a repository.
