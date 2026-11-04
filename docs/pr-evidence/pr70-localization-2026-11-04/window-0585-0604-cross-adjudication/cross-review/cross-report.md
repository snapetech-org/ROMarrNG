# ROMarrNG PR #70 W585–W604 cross-audit

Pinned to `01da053f0e6a47e7184fb86da77f66b7b6719653` (tree `dcb9c1766831e217ffca7fb77068b97c33b9524e`), source worktree clean. Candidate-free, primary, and blind packet verifiers all passed; exact branch and PR refs matched the pin during primary verification.

## Result counts

| Outcome | Cells |
|---|---:|
| Selected proposal/apply-plan cells | 22 |
| Callerful keep-current no-ops | 194 |
| Callerless hash-only holds | 24 |
| Unresolved contextual holds | 0 |
| Total | 240 |

Resolution counts: `{"blind_only_resolved_by_caller_context": 6, "corroborated_exact_target": 11, "corroborated_meaning_variant": 3, "primary_only_resolved_by_caller_context": 2}`.

## Selected proposals

| Source | Locale | Current | Selected | Cross-audit outcome |
|---|---|---|---|---|
| `Ko-fi` | `hi` | को-फाई | Ko-fi | `primary_only_resolved_by_caller_context` |
| `Ko-fi` | `ja` | コフィ | Ko-fi | `primary_only_resolved_by_caller_context` |
| `Ko-fi` | `pt-BR` | Ko-fi. | Ko-fi | `corroborated_exact_target` |
| `LYNX header` | `vi` | Tiêu đề LYNX | Đầu tệp LYNX | `corroborated_exact_target` |
| `Last ran` | `ja` | 最後のラン | 最終実行 | `blind_only_resolved_by_caller_context` |
| `Last ran` | `vi` | Chạy lần cuối | Lần chạy gần nhất | `blind_only_resolved_by_caller_context` |
| `Last refresh:` | `hi` | पिछली ताज़ा जाँच: | पिछला रीफ़्रेश: | `blind_only_resolved_by_caller_context` |
| `Last refresh:` | `vi` | Làm mới lần cuối: | Lần làm mới gần nhất: | `blind_only_resolved_by_caller_context` |
| `Latest listed version only` | `id` | Versi terbaru saja terdaftar | Hanya versi terbaru yang terdaftar | `blind_only_resolved_by_caller_context` |
| `Latest listed version only` | `ko` | 최신으로 등록된 버전만 | 목록에 있는 최신 버전만 | `blind_only_resolved_by_caller_context` |
| `Left` | `ar` | يسار | المتبقي | `corroborated_exact_target` |
| `Left` | `de` | Links | Übrig | `corroborated_meaning_variant` |
| `Left` | `es` | Izquierda | Restantes | `corroborated_exact_target` |
| `Left` | `fr` | Gauche | Restants | `corroborated_exact_target` |
| `Left` | `hi` | बाएं | बाकी | `corroborated_meaning_variant` |
| `Left` | `id` | Kiri | Tersisa | `corroborated_exact_target` |
| `Left` | `ja` | 左 | 残り | `corroborated_exact_target` |
| `Left` | `ko` | 왼쪽 | 남은 수 | `corroborated_meaning_variant` |
| `Left` | `pt-BR` | Esquerda. | Restantes | `corroborated_exact_target` |
| `Left` | `vi` | Trái | Còn lại | `corroborated_exact_target` |
| `Left` | `zh-Hans` | 左边 | 剩余 | `corroborated_exact_target` |
| `Left` | `zh-Hant` | 左邊 | 剩餘 | `corroborated_exact_target` |

The task-table `Left` correction is supported by the pinned implementation: `Done`, `Failed`, and `Left` are adjacent columns, and the value under `Left` is `fmt(x.remaining)`. Exact caller excerpts, expanded pinned source lines, their hashes, candidate text, and candidate/current/source hashes are in the packet.

The eight cells where one review did not propose a change were selected only after the caller identified the UI role: two Ko-fi brand labels, two “Last ran” task headings, two “Last refresh” error labels, and two catalogue-version filter labels. Three `Left` cells had semantically aligned candidate wording differences; the selected target and both source candidates are retained in the proposal rows.

All 24 blind hash-only holds were callerless and remain holds; there were no callerful hash-only holds to clear. The two Ko-fi cells where primary proposed and blind retained current were resolved using the pinned linked brand text and ko-fi.com URL.

All remaining callerful cells are no-op entries with source/current hashes only. The 24 callerless cells remain hash-only holds and contain no source or current-target strings in the cross packet. No tests, builds, CI, browser work, native-speaker review, source edits, or PR edits were performed.

The selected plan is not applied. See `selected-proposals.jsonl`, `no-op-ledger.jsonl`, `source-evidence.jsonl`, and run `python3 verify_cross_packet.py --repo <exact-pinned-worktree>` to verify internal seals and the live source catalog against the pinned commit.
