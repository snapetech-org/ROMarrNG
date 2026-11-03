# W305–W324 application evidence

Applied the exact 105 target/hash rows authorized for ROMarrNG PR #70 at the pinned base head/tree recorded below. The window contains 20 source messages × 12 direct locales (240 cells): 105 exact updates and 135 current values retained because no selected update was authorized for those pairs. There are zero holds.

The application readback records every cell, source hash, before/after target hash, disposition, selected rationale where applicable, and a reference to the exact caller snippets in `caller-context.json`. `wanted-label-context.json` records the rank-310 caller and confirms its phrasing uses the same existing localized UI key/state for Wanted in all 12 direct locales.

The two authorization inputs are retained byte-for-byte. Their checksums and the sealed review packet digest references appear in `application-summary.json`; the referenced primary, blind, and cross-audit packet contents were not copied into this application evidence. Browser and native-speaker review remain pending.

No tests, builds, scans, CI, workflow edits, releases, tags, or merges were performed. See `verify_application.py` for the deterministic catalog/readback/checksum verifier.
