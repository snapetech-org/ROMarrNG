# W765–W784 catalog application and readback

The exact-hash plan applies ten reviewed values to `romarr/ui-labels.json` from input head `9714d7cf69c687685b4f65cbd9627a56830bab85`. The script preserves JSON formatting and ordering, verifies that only those ten target values changed, and checks the complete 240-cell final ledger, including 24 text-free hash-only holds.

Run `PYTHONDONTWRITEBYTECODE=1 python3 -B apply_and_readback.py --verify-after` from any directory in a checkout that preserves the input commit and contains the resulting catalog. This is an offline evidence verifier; it does not run product tests or builds.
