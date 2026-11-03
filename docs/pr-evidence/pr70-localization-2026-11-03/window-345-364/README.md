# ROMarrNG PR #70 W345–W364 application

Applied the exact 144 changed targets selected by the independent exact-head cross-audit. The 240-cell window contains 93 corrections, 51 refinements, and 96 unchanged current values. No cell in this window is on hold; all 288 prior callerless hold cells remain unchanged.

Only selected `translations[locale]` values and matching canonical JSON-content `translationHashes[locale]` fingerprints changed in `romarr/ui-labels.json`. Source messages, translation status, review and pending metadata, catalog keys and ordering, and every non-target translation/hash remain unchanged. Changed translations remain `draft`; no native-speaker approval is claimed.

Candidate-free input, primary review, blind review, and cross-audit packets are retained under `review-packets/`. Their checksums and exact 240-cell application readback are verified by `application/verify-application.py`.

Ranks 346 and 350 remain separate source-bound runtime follow-ups: their catalog wording was reviewed and applied, while the launcher toast and TOTP note still pass through opaque `apiMessageMarkup` paths. No runtime source or caller path changed in this window.

No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were performed. Exact-head headed-browser acceptance and qualified native-speaker approval are not claimed.
