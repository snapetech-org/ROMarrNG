# ROMarrNG W765-W784 exact-hash follow-up application

This guarded follow-up inserts 20 root-selected corrections into romarr/ui-labels.json. It starts from the first application commit 7e101cc0ea5580443d1b3903af084c23fe2134e5; the current evidence head at application time is ec6319e012ee0043be853ee313ff7cbf36e51af1.

Run preflight and application with:
python3 apply_and_verify_followup.py --repo /path/to/ROMarrNG --preflight
python3 apply_and_verify_followup.py --repo /path/to/ROMarrNG --apply

The apply mode requires the exact clean evidence head/tree and exact pre-application catalog blob. It preserves catalog formatting and key order. Verify the final 240-cell ledger with:
python3 apply_and_verify_followup.py --repo /path/to/ROMarrNG --verify-after

Product commit `2e6fb1d9f5bf5a5dc54f7fb62e562cc2a88d3fae` has tree `6d09b309493b1d8701989c2c773f010709e63539` and catalog SHA-256 `1a204f6f4a5162daa9c9c0eda9d8bfc08636c393360a1cedc38459ced3a728ce`; these values are pinned in `product-pin.json`. Post-commit `--verify-after` passed at that exact head, confirming all 240 cells and preserving the 24 callerless values as hash-only. The original 10-cell application remains in the sibling `../application/` packet.
