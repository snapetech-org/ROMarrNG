# ROMarrNG PR #70 localization review and application: W765–W784

This packet preserves the original exact-head candidate-free source/caller audit, primary review, blind review, third-party cross-review, initial root adjudication, and two sequential exact-hash applications for the 240 cells at source positions 765–784. The original cross-review accepted 20 current translations that a later integrated independent blind/cross pass found were missing required `# comments` or `URLs` literals. Those original files remain as audit history; the final decisions and post-commit readback are in [`follow-up-20/`](follow-up-20/README.md).

## Pins and result

- Review head/tree: `9714d7cf69c687685b4f65cbd9627a56830bab85` / `c8eb66573f10b2390a02df05033f5133425d5e41`.
- Initial product commit/tree: `7e101cc0ea5580443d1b3903af084c23fe2134e5` / `d4b2661cd5105d6a18505a7302a13d9295eff39c`.
- Final product commit/tree: `2e6fb1d9f5bf5a5dc54f7fb62e562cc2a88d3fae` / `6d09b309493b1d8701989c2c773f010709e63539`.
- Final changes: 30 catalog targets across the window, including 20 follow-up corrections; 186 cells retain current wording, 23 are corrections, seven are refinements, and 24 callerless cells remain text-free hash-only holds.
- Integrated cross-review disposition: 186 accept-current, 23 corrections, 7 refinements, and 24 holds. The original 10 selected values remain supported; the follow-up corrects 20 omitted literals.
- Active hash-only holds: 988 prior + 24 new = 1,012.
- Catalog order and all non-target values were preserved. All 240 final cells were read back by exact target hash; the 24 callerless values remain unexposed in review/readback evidence.
- Next queue boundary: index 785 / position 786, `ui.optional-overrides-the-webhook-s-dis.4116a5e8e4`.

Machine semantic review is complete for this window after the follow-up. Qualified native-speaker approval and current-head headed-browser acceptance remain separate and are not claimed here. No tests, builds, scans, CI dispatches, workflow changes, releases, tags, or merges were performed.

## Evidence structure

- `candidate-free/`: source, caller, catalog, and prior-hold pins without translation proposals.
- `primary-review/`: sealed primary judgments and token audit.
- `cross-review/`: independent third-party reconciliation against the candidate-free and primary packets.
- `root-adjudication/`: complete 240-cell root ledger and ten manual decisions.
- `application/`: exact-hash apply plan, application script, and full readback.
- `follow-up-20/`: independent integrated cross-review, blind packet, French finding erratum, 20-cell root supplement, product pin, and final 240-cell post-commit verification.

Re-run the candidate-free, primary, and cross-review verifiers from their respective directories at their pinned input head. Run the post-application readback with `application/apply_and_readback.py --verify-after`. Nested packet checksum lists plus this directory's `SHA256SUMS.txt` cover the retained evidence.
