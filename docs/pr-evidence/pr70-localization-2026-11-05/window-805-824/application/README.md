# ROMarrNG W805–W824 product application and readback

Applied the 13 root-selected targets to `romarr/ui-labels.json` in product commit `7bc17e5ae87e67dd69579c44591337b8e7e7927a`, tree `5c20c137424c8fac55850c6b319896241a5761f9`, parented directly to review-evidence commit `db188b5ded679803b055f2c09c0a97ab00e489cd`.

The readback covers all 240 selected source-locale cells. Exactly 13 targets changed; the other 227 current targets are unchanged. The 10 low-confidence wording cells remain at their current values. All 1,060 active hash-only holds were reattested at both the input and product commits and remain unchanged. Catalog key order and all 12 locale catalogs remain intact with 1,836 nonempty message translations per locale.

`readback-240.jsonl` and the hold readbacks are hash-only. Source, current target, selected target, caller context, and rationale details are in the sibling candidate-free and root-adjudication packets. Verify with:

    python3 -B verify_product_readback.py --repo /home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685 --evidence-root /home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685/docs/pr-evidence/pr70-localization-2026-11-05/window-805-824

No tests, builds, scans, CI, browser review, or native-speaker approval are claimed.
