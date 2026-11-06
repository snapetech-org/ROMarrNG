# ROMarrNG PR #70 current-head cross-review

- Exact checkout: head `65a3f8a8feee1b041c8c547250feeae6900337f5`, tree `654f9065dcdd9c7f580df6909071f38278f44d61`.
- Scope: 36 rows across 12 locales and three source IDs.
- Decisions: accept-current 35, correction 0, refine 1, hold 0. Native-speaker signoff remains false.
- The Indonesian integration-guide candidate is refined to the prior sentence-context target ending `mengatur game`. The current `mengarsipkan rilis game` says ROMarr archives releases, while the English distinguishes verifying releases from filing games.
- The 12 no-API explanations and 11 other integration-guide translations match their prior cross-review targets. German and Korean revised service-use sentences remain semantically complete and retain the household-shared request queue.
- Current catalog values, source hashes, current target UTF-8 hashes, catalog translation content hashes, and prior evidence targets/hashes were verified. The four caller source lines for each linked sentence and both no-API caller locations were rechecked in the exact checkout; 8 historical location pins had shifted, but their current source lines were verified.
- `crossreviewTargetSha256` is SHA-256 of the exact UTF-8 target string. `crossreviewCatalogContentHash` uses ROMarr’s JSON-serialized translation hash format. Prior Nintendo hashes use the catalog content-hash format; prior full-sentence root hashes use raw UTF-8 target hashes.
- No repository or PR changes were made. No tests, builds, scans, CI, or releases were run.

`SHA256SUMS` covers `crossreview.jsonl`, `summary.json`, and this README.
