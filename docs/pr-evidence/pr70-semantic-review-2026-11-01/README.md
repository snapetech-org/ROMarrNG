# ROMarrNG PR #70 focused semantic review evidence

Both evidence-only windows are pinned to app/source head `a1278acda1cea823443d7d6b712ed6ace8a99694` and tree `1e8a8d4fb191490a20bc443fb2b7bf24f05fa294`.

- `requests-per-pass-12-locales/`: 12 current `Requests per pass:` values accepted unchanged at moderate AI-review confidence. No placeholder mismatches.
- `obsolete-at-crossreview-12-locales/`: reviewed the 12 current `ui.at` catalog cells and the 12 current full-label cells. The fragment key is no longer referenced by current UI source; it has no standalone linguistic verdict. The four formerly uncertain values remain unresolved catalog entries. The current full numeric-control label is accepted unchanged, with no placeholder mismatches.

Both bundles passed their SHA256 and frozen-source verifiers on the review host. Neither provides native-speaker approval or fresh browser rendering. No source, catalog, or shared ledger was modified by these reviews.

## Whole-catalog exact-hash pool reconciliation

`current-pool-reconciliation/` reconciles every populated target value in the frozen a127 app/catalog snapshot against prior exact-hash reviews and applied correction targets. It accounts for 21,996/21,996 cells with zero unaccounted cells and zero eligible disjoint source keys. It makes no new semantic decisions; four old context-dependent cells remain unresolved and native-speaker validation is still required. The bundle and its verifier were checked on the review host.
