# W605–W624 exact-hash application

Product commit `e6e826be77e5057cf88b4bbb49f6ff60f2980c33` applies the two caller-backed cross-review selections in `romarr/ui-labels.json`: Indonesian `ui.live-log.2cfbcb2b85` becomes `Log langsung`; Vietnamese becomes `Nhật ký trực tiếp`. The Arabic proposal remains current. No other translation values or translation metadata changed.

The exact readback covers all 240 cells across 20 messages and 12 locales: 2 applied, 202 retained callerful values, and 36 callerless hash-only holds at positions 618, 620, and 623. The six primary proposals without caller context remain hash-only holds. Prior lineage remains carried: 220 selected sources, 628 holds including 24 prior W585 callerless holds, and 71 applied cells.

The adjacent `candidate-free/`, `primary/`, `blind/`, and `cross/` directories preserve the sealed review chain byte-for-byte. `application/` contains the exact target hash guards, before/after catalog pins, 240-cell readback, hash-only hold ledger, PR/workflow snapshots, and the old PR body prefix used to verify append-only description update.

No tests, builds, scans, or CI runs were performed. The pre-commit Semgrep scan hook was skipped because scans were prohibited; the permitted read-only pre-push image policy ran and passed. No workflow, merge, release, or tag changes were made. No native-speaker approval is claimed.

## Verify

```sh
python3 verify_application.py --repo /path/to/ROMarrNG --live-pr
```
