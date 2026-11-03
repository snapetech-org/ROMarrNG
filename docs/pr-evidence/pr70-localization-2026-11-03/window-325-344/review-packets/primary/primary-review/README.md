# ROMarrNG PR #70 W325–W344 primary review

Independent primary review of the 240 current locale cells at exact head 018937dc98d451ddd04d2d0942bca2777ef64dd3 and tree c13dc4fc091565318d11a19ad9e851215a5f917e.

The review is derived only from the candidate-free packet at ../input/. It records each source/current target, caller-context hashes, selected target, decision, and row-level rationale. The 24 cells at ranks 329–330 remain held because their queue locations do not establish a current production caller; their current values are unchanged.

## Results

- Corrections: 43
- Refinements: 14
- Accept current: 159
- Callerless holds: 24
- Total cells: 240
- Placeholder mismatches: 0
- Numeric-token mismatches: 0
- Baseline protected-literal mismatches: 1; the German rank 343 correction restores Ubisoft Connect.

verify_primary.py checks the full 240-cell ledger against the candidate-free input, exact review counts, unchanged accepts/holds, target hashes, placeholders, numeric tokens, protected literals, and the callerless ranks. Run it from this directory. The task-root checksum file additionally seals both input and primary-review files.
