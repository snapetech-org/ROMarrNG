# ROMarrNG PR #70 follow-up third-party cross-audit

## Result

Cross-audited all **48 cells** at W226/232/237/241 against the candidate-free packet and the sealed primary and independent blind ledgers. There are **12 divergences**: ten at position 237 and two at position 241. Final decisions are **33 accept-current, 9 correction, 3 refinement, and 3 hold**.

The position-237 candidates resolve the intended status after checking the exact local/cloud option mapping and count renderer. At position 241, I select the Arabic and Indonesian fragment refinements that attach to the following Collections link. I preserve the Hindi, Japanese, and Korean holds because the fixed caller places the localized value before that link and does not provide a place for the required postposition/action. The ledger includes the exact selected target and SHA-256 for every changed cell.

## Integrity and pins

- Repository/PR: `snapetech-org/ROMarrNG`, PR #70; pinned head/tree: `e0cb91389334fe534ff44ccfc72cbb2c152a93b4` / `3876dd57816aaf75bb8b1a56a75a5045d216c461`.
- Candidate-free manifest SHA-256: `857ff470aac96220722ec2c2317bf7c8db3d0b91714a93cee9fed9c3292f915e`; all input checksum entries verified.
- Primary ledger checksum list verified; its ledger SHA-256 is `911edf2e49720833c416093cacea158cb62ce88d3621c18dd8a1a8b3abac6e51`.
- Blind seal verifies its 48-row ledger SHA-256 `46a21c4335cda9e73ab7b558fa83726c30966b9d5e2affb7454b6b6a55a036d7`, candidate-free manifest, and pinned runtime context. All blind checksum entries verified.
- All 48 source, current target, catalog, caller, PR, head, and tree pins matched across the packet and review ledgers. Source/current hashes and caller/runtime context line hashes were recomputed.
- Placeholder, markup, numeric-token, and edge-whitespace checks pass on current and selected targets. The 36 protected-literal occurrences (`No-Intro`, `Redump`, and `DAT` across the 12 position-241 cells) are preserved. The catalog values contain no link markup; the caller inserts the Metadata and Collections links.
- No cell is release-approved by this machine cross-audit; the position-237 language-specific proposals still need qualified locale review.

## Reconciled divergences

The table shows the primary and blind dispositions, final disposition, selected full target, and selected-target SHA-256. Primary proposals are selected for each divergence after the context check.

| Position | Locale | Primary / blind | Final target | Final | SHA-256 |
|---:|---|---|---|---|---|
| 237 | `ar` | correction / HOLD_PLAYABILITY_CLARITY | `على القرص (قابل للعب الآن)` | correction | `43edc5aace8abf1703baa9f57cd8ee57f9adecc4a439076f589e3bce3d41c6d9` |
| 237 | `de` | correction / HOLD_PLAYABILITY_CLARITY | `Auf der Festplatte (sofort spielbar)` | correction | `ef27615286cbf9bc582ea80fee30ce854b0253acf57ab7cea6b76536e8e4a71c` |
| 237 | `es` | correction / HOLD_PLAYABILITY_CLARITY | `En el disco (se puede jugar ahora)` | correction | `60ccbf31dab16a28c28373b5dfdff8c32a60dcef84c5be7839755abe98545302` |
| 237 | `hi` | correction / HOLD_PLAYABILITY_CLARITY | `डिस्क पर (अभी खेला जा सकता है)` | correction | `b9bbd83405233a1633da9001b32fc248209ddbb3457b2179bd3a2e57c34b06ea` |
| 237 | `id` | correction / HOLD_LOCALE_AND_PLAYABILITY_REVIEW | `Di disk (langsung dapat dimainkan)` | correction | `041012882e5c18780566646bf7e1b303befd5dc70dfccc36deadc9b5756270cf` |
| 237 | `ja` | correction / HOLD_PLAYABILITY_CLARITY | `ディスク上（すぐにプレイ可能）` | correction | `29224440fe791f2c2bf7d878314c01e609554f2a4058e79762c7c838ba5e2b8b` |
| 237 | `pt-BR` | refinement / HOLD_PLAYABILITY_CLARITY | `No disco (jogável agora)` | refinement | `f92ba97cd575a17b9ef4c8577fd74de79789b0bb43f9efe08d91fe41a5e2079b` |
| 237 | `vi` | correction / HOLD_PLAYABILITY_CLARITY | `Trên ổ đĩa (có thể chơi ngay)` | correction | `fa8c6f258e7f33529c8cfc1241490e12253bde92f56549b57fc8ee5e53a7c5d9` |
| 237 | `zh-Hans` | correction / HOLD_PLAYABILITY_CLARITY | `在本地磁盘（可立即游玩）` | correction | `6978f2fcac4890c902029a3cf2a19cd6ff577995293047b2eac31bf73f3ecd09` |
| 237 | `zh-Hant` | correction / HOLD_PLAYABILITY_CLARITY | `在本機磁碟（可立即遊玩）` | correction | `dbbfb6b706bb808dcc670c5da0d5884c2ef78acde61da3fa36aa022708cb7903` |
| 241 | `ar` | refinement / SEMANTIC_PASS_FRAGMENT | `، أو حمّل ملفات DAT من No-Intro / Redump ضمن` | refinement | `1dd64889dae98df838302d5e1b13e48bafe5259f83a16e144adfb190e44d6877` |
| 241 | `id` | refinement / SEMANTIC_PASS_FRAGMENT | `, atau muat DAT No-Intro / Redump di` | refinement | `1d940ffb23983a39d321b52ae37947856fdb0f6ecdee8d5045fa8af63c376cf2` |

### Evidence used

- **Position 237:** caller line 2068 maps `local` to “On disk (plays now)” and `cloud` to “Catalogued (needs fetching).” Runtime lines 2027 and 2030 translate the app-owned option label and append the option count separately; line 1251 confirms the same rendering behavior. The target is a local-origin status, so the primary proposals’ “playable now” readings fit the explicit caller, while the existing “playing/play now” wordings can imply an action. The blind review’s playability holds are resolved toward those candidates. Its locale naturalness concern remains a qualified-human-review note.
- **Position 241:** caller line 2465 constructs one paragraph as “Connect … under [Metadata link], or load No-Intro / Redump DATs under [Collections link], to browse a catalog here.” Arabic `ضمن` and Indonesian `di` connect the DAT action to the Collections link better than their current “to” prepositions. The fixed fragment does not allow the link to move inside the translation.
- **Position 241 holds:** Hindi omits the load verb, and Japanese/Korean fragments cannot express the linked destination and action in the fixed before-link position. Both source reviews hold these three cells; the cross-audit preserves those holds pending a caller composition change.
- **Positions 226 and 232:** the packet shows a fixed local no-title error template with no interpolation values, and a fixed local `missing` verdict whose peer-authored detail is discarded. The current translations match those caller meanings; the reviews agree.

## Output files

- `cross-audit-ledger.jsonl` — 48 cell records; SHA-256 `8dabd92989fe4859cd9bb57222af3988f64749b56814f5546f9c05c929aed785`.
- `summary.json` — counts and verified input pins.
- `SEAL.json` — binds this reconciliation ledger to the packet and both review ledgers.
- `report.md` — this report.
- `README.md` and `SHA256SUMS.txt` — artifact guide and checksums.
