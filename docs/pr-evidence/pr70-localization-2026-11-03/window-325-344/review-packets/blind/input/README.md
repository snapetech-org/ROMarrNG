# Candidate-free input: ROMarrNG PR #70 W325-W344

Pinned to PR #70 OPEN/DRAFT at branch task/localization-translation-review-20261030, head 018937dc98d451ddd04d2d0942bca2777ef64dd3, tree c13dc4fc091565318d11a19ad9e851215a5f917e. The branch ref and refs/pull/70/head were reattested at this exact commit.

The source queue is romarr/ui-source-messages.json at the pinned head. It contains 479 unique active source IDs. Sorting IDs lexicographically and hashing the newline-terminated ID list reproduces the W305 input source-order hash 96b4c95e6570f15c50053a918e58566481107444f38a64a79a46f8fff33b1b94. The W305-W324 candidate-free selection was reattested against current positions 305-324; ranks 325-344 are the next 20 positions.

The pinned locale catalog is romarr/ui-labels.json. The packet contains only the selected 240 current values and the file/tree hashes for all 12 locales. It contains no proposals or review decisions. Source contexts pin current caller excerpts and source file hashes.

Ranks 329 and 330 are held in all 12 locales. The source queue references romarr/ui.py lines 2228 and 5101, but those current lines are unrelated and the source fragments are absent from the pinned file. These fragments have no verified current caller. All 24 current values are retained unchanged pending direct caller evidence.

Baseline checks: placeholder mismatches 0; numeric mismatches 0; protected-literal mismatches 1 (listed separately).

Run sha256sum -c SHA256SUMS.txt and python3 verify_input.py from this directory to verify the packet.
