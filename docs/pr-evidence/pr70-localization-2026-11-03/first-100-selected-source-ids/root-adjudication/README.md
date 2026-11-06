# ROMarrNG PR #70 root adjudication: first 100 selected source IDs

This packet adjudicates 1,200 cells across 12 locales at exact PR head `6db0b917343fc9fb605f8a4ecfbf9b4c21cebd1b` / tree `bfb778ba77849174a4670a70883c812183506b43`. The live pull request was verified OPEN and draft at that head; the remote PR ref and exact commit tree matched. The primary packet checksums and sealed blind ledger were verified. Source order, current target values/hashes, caller lines/render references, and locale key sets were reattested from `git show 6db0b917343fc9fb605f8a4ecfbf9b4c21cebd1b:<path>`.

## Root decisions

- 554 accept-current, 181 corrections, 57 refinements, 408 holds across 34 held source IDs.
- All 224 cells where primary and blind review differed in disposition or target are resolved in `adjudication-differences.jsonl`.
- `root-decisions.jsonl` contains all cells, exact current/final target hashes, both review inputs, caller evidence references, rationale, and structural checks.
- `exact-hash-apply-plan.jsonl` contains 238 correction/refinement updates, each pinned to the exact head/tree, current value and canonical hash, stored hash, source hash, new target/hash, catalog field paths, and translation status. This is a plan only; no repository or PR files were changed.
- The 408 holds remain unapproved because exact-head caller/render evidence shows the catalog value is not consumed or its caller remains unresolved. Their current targets are retained unchanged.

## Reattestation and limits

`exact-head-reattestation.json` records zero source/order, current target/hash, locale-key, caller file/line, and render snippet mismatches. The checked-out files were not used for reattestation. Placeholder, protected-literal, version-literal, and markup checks passed for every root target. This is machine-assisted review; no native-speaker approval is claimed. No tests, builds, scans, browser actions, CI, workflow edits, commits, PR updates, or releases were performed.

`manifest.json` pins the verified primary and blind cross-review inputs. `SHA256SUMS.txt` checksums all generated report files except itself.
