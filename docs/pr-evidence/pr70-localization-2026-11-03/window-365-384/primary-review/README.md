# ROMarrNG PR #70 W365-W384 primary semantic review

This primary review covers all 240 current locale cells at exact input head d1698b94781c3c84e91faf03c75e8c308dc39c34 / tree 3f42d41fe4bbb8edd921ff161e8298ca66038a91. It used only the sealed candidate-free input at ../input/; it did not consult or create blind-review material.

Disposition counts: accept-current 134, correction 71, refinement 35, hold 0. The ledger records the current and selected target, exact hashes, rationale, confidence, caller-context hash, placeholder/number/protected-literal checks, and markup-context check for every cell. Proposed targets appear only for corrections and refinements.

Rank 368 is used as the action beside a row checkbox and as the heading for the checkbox column. The primary review distinguished both callsites. Arabic uses an imperative, German an infinitive, Spanish an infinitive action form, and Korean a concise selection noun; the other locale forms already work as a shared selection action/label. The key can safely serve both callsites after these wording adjustments, so no cells at rank 368 are held.

No callerless source was found. The packet’s 288 prior callerless hold cells remain reattested and unchanged. This machine-assisted semantic review does not claim qualified native-speaker approval or headed-browser acceptance. No repository/PR files were changed and no tests/builds/scans/CI were run.

Run sha256sum -c SHA256SUMS.txt and python3 verify_primary.py from this directory. The verifier checks only this review packet and its candidate-free input; it is not a project test.
