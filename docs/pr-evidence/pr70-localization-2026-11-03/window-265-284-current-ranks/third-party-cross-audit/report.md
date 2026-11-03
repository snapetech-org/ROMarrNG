# ROMarrNG PR #70 W265–W284 cross-audit

Pinned PR head: `c135c4729582817273c946891186ab4ea87467b5`; tree: `32c07150396335a5832b5664fc1e0225d7cebdc1`. This packet reconciles 240 current target cells across 20 source IDs and 12 locales. At 2026-11-03 10:58:29 UTC, the local worktree, eight source-file pins, GitHub PR state and both remote refs matched this head/tree; see `pinned-state-verification.json`.

## Outcome

- **34 direct-caller changes selected**: 33 corrections and 1 wording refinement.
- **38 direct-caller cells accepted as current.**
- **168 cells held** at ranks 269–282 (12 locales each). No targets are selected for held cells.
- Direct caller contexts were examined for all 72 cells at ranks 265–268 and 283–284, including source file ranges and line hashes.

Selected direct-caller changes:

- Rank 265 (`ui.projects-come-from-your-own-catalogu.82063d8e45`): de, hi, id, ja, zh-Hans, zh-Hant
- Rank 266 (`ui.proposed-path.0e656434e8`): ar, de, es, hi, id, ja, vi
- Rank 267 (`ui.provider-identity-provider-setup-gui.e0aaaa0ccd`): ar, es, ja, ko, vi, zh-Hant
- Rank 268 (`ui.provider-suggestion-review.0111b979ee`): de, es, hi, ja, ko, pt-BR, vi
- Rank 283 (`ui.publish-es-de-data.0e81c10a08`): ar, de
- Rank 284 (`ui.published-count-es-de-entries.8e45db116a`): ar, es, fr, id, ko, pt-BR

## Review reconciliation

Primary review counts: {'accept-current': 41, 'correction': 24, 'refinement': 7, 'hold': 168}. Independent blind counts: {'accept-current': 38, 'correction': 28, 'refinement': 6, 'hold': 168}. Cross-audit counts: {'accept-current': 38, 'correction': 33, 'refinement': 1, 'hold': 168}.
The two review ledgers differ on 24 direct-caller cells by disposition and/or proposed wording. Row-level details and the adjudicated target are in `disagreement-and-hold-summary.json` and the full ledger.

## Caller-path holds

Ranks 269–282 are dynamic metadata-provider and Prowlarr API diagnostics returned as raw error text and rendered through `apiMessageMarkup` without an explicit localized template key and values. Dynamic provider names, operation/needs values, exception types and HTTP status codes remain opaque. Current translations are retained unchanged until an exact source-template path exists.

## Integrity and limitation

Input, primary and blind packet checksums verify. The candidate-free manifest JSON SHA256 is `d8c2d6ce7a0e4c146702cb25d4ba42bbb5eddb813790a4e27a49017f4fc9123d` and its checksum-list SHA256 is `6a9a1ccec32c9598788c46f06a7edeff7211fb22b8e74cf0c777962e8ac67aae`; the corrected blind seal explicitly attests both values. All 240 blind per-row input hashes, current targets, source identities, caller counts/locations, and caller-context hashes match the current input.

The ledger records each locale’s availability/direction metadata, review state, source/target markup metadata and candidate-free flag. The audit selects target-text values only and leaves these pinned metadata fields unchanged. All selected target placeholders match the source placeholder multiset, including exact `{provider}` and `{count}` placeholders. The packet is a machine-assisted review and does not establish qualified native-speaker approval or browser review. It contains recommendations only; no repository or PR files were changed and no release actions were performed.

See `cross-audit-ledger.jsonl` for all 240 cells and the exact source/current/reviewed/reconciled values, hashes, caller context, decisions, holds and rationale.
