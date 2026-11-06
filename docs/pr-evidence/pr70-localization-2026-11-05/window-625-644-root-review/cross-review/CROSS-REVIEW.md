# ROMarrNG PR #70 W625-W644 cross-review

## Review boundary

This cross-review uses the candidate-free packet and the exact pinned worktree at `5860fce5d546a772b1df995f8f6321c083ed7d5d` / `561835895972a62e9d3b1f2bfe9bcba01187eb98`. All packet checksum lists passed. The candidate-free and primary verifiers passed against the detached, clean pinned worktree. The blind seal is `SEALED`; its input manifests and payload hashes, blind ledger and summary hashes/byte counts, and 240-row count match. No live browser or PR-state claim is made.

## Reconciliation

All 240 cells across 20 sources and 12 locales join exactly across the candidate-free cells, primary dispositions, and sealed blind ledger. Source-text, current-target, caller-context, caller-reference, and token inventories were recomputed or reconciled for every cell. All current-cell placeholder, markup, numeric, and generic protected-literal checks pass. All 24 primary proposals also pass those token checks and preserve the exact provider/product literals present in their source.

Catalog key order is unchanged: 1,836 catalog keys; `catalogKeyOrderSha256` `40c18afaf80695667f7022e59141a2793799fde35527d608eedb30f8ef4ad055`. The selected IDs match source inventory indices 625 through 644 (zero-based), positions 626 through 645 (one-based), in the pinned order.

The primary proposes 24 changes: **625→es,zh-Hans,zh-Hant; 626→ar,de,es,fr,hi,id,ja,ko,pt-BR,zh-Hans,zh-Hant; 628→ar; 629→ar,hi,ja; 634→es,fr,hi,pt-BR; 638→ar; 639→vi** (zero-based positions). The cross-tab with the blind ledger is:

| Primary | Blind keep | Blind revise | Blind hold | Total |
|---|---:|---:|---:|---:|
| Change | 7 | 2 | 15 | 24 |
| Keep | 170 | 1 | 45 | 216 |
| Total | 177 | 3 | 60 | 240 |

Cross-adjudication retains **177 keep, 3 revise, 60 hold**. The two primary changes at position 629 (Arabic and Hindi) align with blind revise. Add the blind Spanish revise at position 638, which the primary marked keep. Do not adopt the seven primary changes that the blind review kept; the proposals are wording or terminology refinements without a material semantic error established by the pinned callers.

## Callerless mappings

The blind holds all 60 cells across five sources. The pinned caller search found zero exact production callers for each source among 51 tracked production files; the main comparison also marks all five callerless. The primary proposes 15 changes across two of those sources: 11 at position 626 for the Prowlarr message and four at position 634 for the download-path mapping. **Keep all 60 on hold; no callerless exception meets the source-and-caller-independent standard.**

- Position 626: “Managed in Prowlarr, shown here read-only…” refers to “them,” “there,” and “this list” without establishing the object or runtime surface. Several target languages require number, gender, or register choices the exact source does not settle.
- Position 627: “Management” is a one-word heading and does not establish whether it labels a page, settings area, or action.
- Position 634: the long path-mapping instruction is mostly self-contained, but it cites the exact “All download clients” UI control and client/scope behavior. The Spanish, French, and Portuguese proposals depend on the control’s localized label; the Hindi grammar adjustment does not establish where this orphaned mapping appears.
- Position 636: the RomM folder-layout instruction references specific structures, path placeholders, and the Libraries page without an exact caller.
- Position 644: “Messages” is a one-word heading whose referent is unresolved.

The primary changes at positions 626 and 634 remain holds. Preserve every blind hold unless an exact production caller is established or the source’s caller-independent meaning fully resolves the ambiguity.

## Revise findings

- **Position 629, Arabic and Hindi:** The current translations blur or shift the source statement that the Management API and indexer feeds are checked separately. The pinned caller places it in Prowlarr diagnostics and confirms those are distinct checks.
- **Position 638, Spanish:** The pinned caller is the “Media” column in a platform table whose cells display platform media types. The current “contenido multimedia” reads as multimedia content and changes the category.

## Evidence files

- `cell-reconciliation.jsonl` contains all 240 exact joins, source/current/caller hashes, token-audit hashes and fields, primary proposal text/hashes, blind decisions, and cross-adjudication.
- `cross-review-summary.json` contains packet verification results, the 24-cell primary list, the decision matrix, callerless-source evidence, and token/order checks.
