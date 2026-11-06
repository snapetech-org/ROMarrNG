# ROMarrNG PR #70 W146-W165 primary review

This primary review is pinned to PR head db895a97e9871952a0b952e1d119e32e06cf168d and tree f1edf8319eb3dbd29ac5fe1e279216c5b96ecc6a. It is based only on the frozen clean input packet at ../input/; its input review SHA-256 is d649bb321a80fbbf28bf3aae88266db04f4f3e839a4c0f33ab4f84d24d26c83d.

The ledger contains one decision for each of 240 cells (20 source IDs × 12 locales). Every row records the current target hash, exact source and caller reference, placeholder parity, protected-literal parity, and a reason. Corrections and refinements include a suggested target and its canonical hash, in this private packet only.

Ordinal 160 (ui.integration-guide.6cfa2d0314, lowercase integration guide) has no current production-code caller in the pinned code search. All 12 cells are hold-context; the current values are retained without a linguistic decision or replacement suggestion pending resolution of a render path. The case-distinct lists navigation title is a different message ID.

The review records 64 proposed target changes (42 corrections, 22 refinements) and 164 accept-current cells. These are primary machine review decisions, not native-speaker approvals. No repository, PR, workflow, or browser session was changed or used; no tests, builds, scans, CI, releases, or tags were run.

Verify SHA256SUMS.txt before consuming the packet. The clean input packet is separate and remains candidate-free.
