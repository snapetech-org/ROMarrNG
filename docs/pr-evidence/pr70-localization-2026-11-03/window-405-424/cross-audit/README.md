# ROMarrNG PR #70 W405-W424 blind/primary cross-audit

The blind-only packet was sealed and verified before the primary packet was opened. This reconciliation uses the candidate-free input, blind packet, and primary packet, all pinned to PR head c146189f29db8fbd77d68dff0c33a0ab59a6b601 / tree 3db10f8b87577edd1167e4489524e6afbb50d556.

All 240 source/locale cells reconcile on exact source and current-target hashes. The 288 carried holds remain unchanged. The primary’s 48 new holds at positions 405, 407, 408, and 416 are independently confirmed from the pinned caller and dispatch excerpts. There are 12 disposition/target disagreements: 11 target differences and one same-target taxonomy difference. The exact resolutions and rationales are in disagreement-resolutions.jsonl.

The final plan contains replace/no-op/hold for each cell. It records expected current hashes and selected target hashes; it was not applied to the repository or PR.

Verify with python3 verify-cross-audit.py. Pass --candidate-free, --primary, and --blind if the packet directories move. The verifier checks all three upstream packet seals, runs their verifiers when their pinned input path is available, and independently validates this reconciliation and plan. It accepts explicit packet paths when moved.
