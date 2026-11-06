# ROMarrNG PR #70 localization review: W705–W724

## Exact pins and scope

This window covers 20 ordered source IDs across 12 direct locales: 240 cells. Candidate-free extraction, primary review, blind review, and cross-review are pinned to product head 50e3f8a48a800affff8bad367b5c493cc0fdfd62 / tree 22cd46ff4821fcbbe76b4760a15e22d688b3f548. Product commit 453d9755dc442cde05ebbd4561c4b22d76d6906f / tree 4c51a1ab7d592feb75f250b831b5a6cd4225ccb1 applies the selected catalog values.

The candidate-free packet confirms 1,836 message IDs per locale, 192 caller-backed cells, and 48 callerless cells. Callerless source and target text remains omitted; those cells are retained as hash-only holds.

## Review and root adjudication

Primary review proposed four changes: three corrections and one refinement. Independent blind review proposed four corrections. Cross-review reconciled all 240 cells: five corrections, 187 current translations retained, and all 48 callerless cells kept as text-free holds. Three disagreements were sent to root adjudication.

Root selected the blind proposal for Arabic and French at position 709 because the empty state refers to software frontend export formats. Root selected the primary proposal for Indonesian at position 711 because the caller shows a library result with no returned games. The two Simplified and Traditional Chinese punctuation corrections were independently agreed.

The five changes are: Arabic and French frontend empty-state wording; Simplified and Traditional Chinese removal of the space before the full-width period; and the Indonesian library empty-state wording. Placeholder, markup, number, and protected-literal checks pass for every selected value.

## Application and readback

Product commit 453d9755dc442cde05ebbd4561c4b22d76d6906f changes exactly five translations in romarr/ui-labels.json. Full-catalog readback passes for all 240 reviewed cells: 187 caller-backed values are unchanged, the 48 hash-only holds remain unchanged, message order is preserved, all 12 locales retain 1,836 nonempty messages, and every other catalog value matches the pinned parent.

W665 evidence restoration is complete: all 77 indexed payloads are present and hash-matching. The older W625 missing-stage-file note and W645 stale-checksum warning remain preserved in their original evidence lineage.

The root-adjudication and application directories retain the three final root decisions, five-change exact-hash plan, 240-cell ledger and readback, and reproducible application verifier. The other directories retain the candidate-free, primary, blind, and cross-review evidence.

## Acceptance status

This is machine-assisted multilingual review at moderate confidence. It does not claim qualified native-speaker or headed-browser acceptance. No tests, builds, scans, CI, deployments, workflow changes, merges, releases, or tags were made. PR #70 remains open and draft.
