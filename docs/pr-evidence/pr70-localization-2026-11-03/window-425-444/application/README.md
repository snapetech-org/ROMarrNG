# ROMarrNG PR #70 W425–W444 application evidence

Applied the 46 selected exact-hash corrections/refinements from the sealed third-party cross-audit to `romarr/ui-labels.json` on the existing PR branch.

- Commit: `d5ba7f1f268501f45227388c46d5f938ed0c9191`; tree: `2f8ce1af963b315108f668fc31c94ca90ecd1351`; parent: pinned pre-apply head `7681ea470ee0f387cd3a1a5be0541979d9cd06f6`.
- Exactly one file changed, with 46 replacements: 17 corrections and 29 refinements. The worktree was clean after push.
- Readback covers all 240 cells in W425–W444. Key order, locale order, and every non-target catalog value were preserved. All 336 inherited held cells and 40 prior selected sources were verified unchanged.
- PR #70 remains OPEN/DRAFT. Both the branch and pull refs point to the pushed head. The PR body contains one exact-head W425–W444 marker; before/after bodies are included.
- The original cross-audit packet and 46-row selected ledger are referenced and hashed in the evidence. The packet retains the W440 dynamic caller evidence and leaves all 12 accepted current labels unchanged.
- No tests, builds, scans, CI, merge, release, or tag actions were run.

Run `python3 verify_apply.py` from this directory for offline verification of checksums, the 46 exact selected target hashes, 240-cell catalog readback, key/order and non-target preservation, inherited hold/selection preservation, commit metadata, pushed refs, PR state, and body marker count.
