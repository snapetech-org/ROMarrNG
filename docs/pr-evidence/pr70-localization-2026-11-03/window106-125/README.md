# ROMarrNG PR #70 localization review: W106–W125

This packet reviews 20 pinned source IDs across 12 direct locales (240 cells) at exact PR input head `5f0973fb211c24d9b408cdb85c572540a7ab17ff`, tree `e8668e9c83afa533f8cd6e69e6a7ad96946ed40e`.

The primary packet and clean independent screen are preserved with their exact-head inputs. The initial independent reviewer opened the primary README before recognizing that it contained aggregate dispositions, so that review was discarded. A sanitized input-only packet was rebuilt and the replacement reviewer used only `clean-input/`. The replacement reviewer saw older aggregate summaries in the PR body, but no W106–W125 decisions, proposals, or same-window counts. See `process-note.txt` and `independent-crossreview/review-manifest.json`.

The clean independent screen recorded 184 accept-current, 8 refine, and 48 hold-context decisions. The primary screen recorded 144 accept-current, 15 corrections, 9 refinements, and 72 holds. Final root adjudication accepts 148 current values, applies 33 corrections and 11 refinements, and retains 48 holds. Forty-four catalog cells changed across the 20-ID window and 12 source IDs. The held IDs are source ordinals 111, 121, 123, and 124; each lacks verified production context or complete surrounding sentence structure.

Two complete source messages were held in the initial primary review because their catalog values were not used by the live UI path: the publish error at ordinal 110 and folder-package rename reason at ordinal 120. Exact local organizer routes emit these fixed app-owned messages. `romarr/ui.py` now maps only the two explicit stable catalog keys at organizer error and rename-preview reason call sites. Other values continue through `apiMessageMarkup`, retaining escaped opaque display and `lang=und dir=auto` handling. Catalog IDs and English source strings did not change.

Translation status remains `draft`; this machine-assisted review is not native-speaker approval. No build, test, CI dispatch, workflow edit, merge, release, or tag was performed.

An independent code review found no material safety issue in the exact-key mapping. It recorded the narrow exact-string collision edge in `independent-code-review.md`.


## Full-sentence EmuDeck supplement

A separate primary review, strict-blind independent review, third-pass adjudication, and root recheck cover the three adjacent EmuDeck path nodes across 12 locales (36 cells). This resolves the sentence around the inline Emulation/roms and Emulation literals. The supplement changes 32 cells and retains four current values. Twelve cells overlap source ordinal 119 and are now updated in the main root ledger and 44-cell window apply plan; the other 20 changes cover two additional source IDs. The combined reviewed scope is 264 unique locale/source cells with 64 catalog changes across 14 source IDs. Durable input and review packets, hashes, final assembled sentences, an exact apply plan, and readback are in sentence-supplement-emu-deck/.

The German final node was refined at root from the third-pass candidate to make the shared-metadata location phrase read naturally with the following path literal. The assembled sentence retains both inline literals in order. This is machine-assisted review, not native-speaker approval or a production UI render review.
