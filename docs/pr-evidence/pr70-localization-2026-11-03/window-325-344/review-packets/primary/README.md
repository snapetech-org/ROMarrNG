# ROMarrNG PR #70 W325–W344 localization review packet

Exact source pin: open draft PR #70, branch `task/localization-translation-review-20261030`, head `018937dc98d451ddd04d2d0942bca2777ef64dd3`, tree `c13dc4fc091565318d11a19ad9e851215a5f917e`.

The candidate-free input is sealed in `input/`. The independent primary semantic review is in `primary-review/` and was authored without consulting a blind review. The input reattests the prior W305–W324 selection and selects the next positions 325–344 from the stable-ID-sorted active source queue (479 IDs; newline-terminated order hash `96b4c95e6570f15c50053a918e58566481107444f38a64a79a46f8fff33b1b94`).

The primary review covers all 240 locale cells: 43 corrections, 14 refinements, 159 accepted current values, and 24 callerless holds. All 12 values at ranks 329–330 remain unchanged because the pinned queue locations resolve to unrelated current UI code and no active caller is established. The sole input protected-literal discrepancy is German rank 343; its selected target restores exact `Ubisoft Connect` spelling. Placeholder and numeric-token mismatches are zero.

Verification commands (packet-only, not project tests):

- `cd input && sha256sum -c SHA256SUMS.txt && python3 verify_input.py`
- `python3 primary-review/verify_primary.py`
- `sha256sum -c SHA256SUMS.txt` from this packet root

The top-level checksum file seals all files in both `input/` and `primary-review/`, plus this README. `input/SHA256SUMS.txt` separately seals the candidate-free packet.
