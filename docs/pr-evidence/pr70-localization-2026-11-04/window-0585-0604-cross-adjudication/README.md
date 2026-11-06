# ROMarrNG PR #70 W585–W604 application evidence

Applied 22 cross-selected translations to romarr/ui-labels.json in product commit d44e61d9960c788412da0fadbb8b67744b70e404 (tree 2bbb5821bf6beb2b06f689ba0e3c87c6136d42ef), whose parent is the exact pinned review head 01da053f0e6a47e7184fb86da77f66b7b6719653 (tree dcb9c1766831e217ffca7fb77068b97c33b9524e). The product commit changes that catalog file only.

The 240-cell readback records 22 selected changes, 194 callerful keep-current cells, and 24 unchanged callerless hash-only holds. All 22 selected target hashes matched the cross-audit apply plan; every no-op/hold current-target hash remained unchanged. The full candidate-free, primary, blind, and cross-audit packets are included with their original checksums. The cross-review packet includes source/caller evidence, the selected change plan, and the hash-only no-op ledger.

verify_application.py verifies the included packet checksums, the cross-review seal, the exact product commit and catalog readback, preservation of the 194 no-ops and 24 callerless holds, and the product-only commit scope:

    python3 verify_application.py --repo /path/to/ROMarrNG

PR #70 was open and draft before and after the product push. The branch and pull refs advanced from the pinned head to the product commit; the prior PR-body prefix hash remained unchanged. The PR body milestone is appended after the separate evidence commit is published. The PR API base SHA bcd1eb41b5cdf8202acb5cf8e365e14761b743b5 differs from live main 65d8747e3a068473396227bae5e85ddc71c7d4d8; the base was left unchanged.

No tests, builds, scans, CI runs, workflow edits, merge, release, or tag were made. The pre-commit security-scan hook was skipped under the no-scan instruction. The read-only pre-push stable-image alias policy hook passed.
