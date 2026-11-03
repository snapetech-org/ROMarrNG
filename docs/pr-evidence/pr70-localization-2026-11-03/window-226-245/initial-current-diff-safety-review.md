# ROMarrNG PR #70 W226–W245 current-diff review

## Scope and pins

Read-only review of `/mnt/disks/scratch/task-worktrees/localization-20261103/romarrng-pr70-w226-review-20261103` at base `1ab8fd8b171afbfe43cd6998cde920f9f9b12b0c`, tree `c65a2206c95cd13b3eca5174aca2e4c812eff8bc`. The current uncommitted diff SHA-256 is `6a8a9ae3a0cdfcecca381659de0caa99d27c7871a6665ccb6e4323d8a3303a62`.

Changed files: `docs/localization-roadmap.md`, `romarr/app.py`, `romarr/ui-labels.json`, `romarr/ui-source-messages.json`, `romarr/ui-source-snapshot.json`, and `romarr/ui.py`. Worktree status was limited to those files.

| File | Base blob | Current worktree blob | Current SHA-256 |
| --- | --- | --- | --- |
| `docs/localization-roadmap.md` | `c8995e67c866613aa6b814e378733ed019497421` | `a6a8a74b7c0c9b59add2dbb3204af59403262eef` | `8ea837231f48d8784528582e9da43bb8db3c734e317dacf3f93582fce5485991` |
| `romarr/app.py` | `1a6067d98a1e5c2c54c5af7c70a7f6cfeecedee5` | `cde31ad0d32ebc9c728eea7f4b4b37e26ebf53dd` | `74d72bae792a9b07db6336758f742ee1506bd9f34cebd22ee3dc3bdd3d6b8510` |
| `romarr/ui-labels.json` | `fa5d406b6391d49b55da4f227c19b131f001fa23` | `9e6bd2e81ff0a5088d5a3962c5b267004ead5a8c` | `6ba159bf5f585c3992e1fa7a322f7e777e9b0dd3a00ab6f010384ced5d628844` |
| `romarr/ui-source-messages.json` | `ea4ff095d4c9d60c175987926b852dddd1f6aa85` | `1ff109820b393cbf4a0218e65565eae4ef893414` | `99925b7fd08c105f9a9644a24538c3badd7bdbafe9f5d74ac618bf1383cbc026` |
| `romarr/ui-source-snapshot.json` | `c6e8f3f93cb8784a25422526730b3c21f3f000a4` | `398ea2e11cca406eb7f108ac40a44a6c495badb2` | `c91b6c00b23cb073ab4f9c85a3932ed92d9c3418ba3c6b1b12522bec6fa88fe3` |
| `romarr/ui.py` | `0cf909e3ef20a02ddc3e804666d32d2cfc67a4b7` | `942188bd88620f7777c67f81494f91c704d47031` | `ccdd49dfee8083f71d56fef13d010236e9e028d92fd1f015c9afdfbbfcc704ef` |

## Review result

The catalog edits are in scope against the checksum-verified cross-audit ledger (`cross-audit-ledger.jsonl` SHA-256 `f9101aad1efb9f550759e6af3c01ac875b427bec66e0ec99be5107bcc7e97b59`; its manifest passed `sha256sum -c`). Exactly 31 translation cells changed to the ledger's selected targets; all 31 target hashes match the catalog's canonical JSON hash format. None of the 26 held cells changed in translation, translation hash, status, or review metadata. The Arabic position-227 cell remains unchanged, preserving `ID`. The only other catalog/source-index change is the audited retirement of the orphan position-242 key from the active catalog, source index, and source snapshot; historical bundles were untouched. No translation edits were found outside the 240 audited cells. Roadmap totals agree with the current catalog: 1,836 messages, 22,032 targets across twelve direct locales, and 5,856 draft cells.

The no-title path attaches only the fixed local `ui.no-title` key with empty values; the friend-shelf UI passes it through the local allowlist. Netplay exact status `missing` discards remote detail and template and substitutes ROMarr's fixed local message; the UI renders a template even with empty detail. Other peer detail stays escaped plain text. These paths do not grant remote copy template authority.

Facet option localization now translates only explicit mapped labels. It keeps the escaped option value intact, stores the raw count separately, and formats that count on language refresh. `ownLabel` uses an own-property check for source/origin maps, and the output goes through `textContent` or HTML escaping. Current counts are bounded by the 250,000-row library cap and remain within exact JavaScript integer range.

## Remaining finding

**Low-severity conditional label bug:** `romarr/ui.py:3620` still uses `SOURCE_LABEL[k] || k` in the Stats source breakdown, despite the new safe `ownLabel` helper at line 1948. Current source production is restricted by `classify_provenance` to `local`, `archive`, `flashpoint`, or `cloud`, so no present producer reaches an inherited key. The facet code explicitly allows future source values; if such a value is `constructor`, `toString`, or `__proto__`, the Stats label resolves to an inherited function/object string instead of the opaque key. Counts remain intact and the bar escapes its label, so this is not an XSS path. Reuse `ownLabel(SOURCE_LABEL,k) ?? k` there for consistent opaque-value handling.

## Limitations

No repository or PR edits, tests, builds, CI, or web actions were performed. The cross-audit artifacts are evidence for the approved target set; this review does not claim native-speaker approval.
