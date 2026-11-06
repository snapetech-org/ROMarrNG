# ROMarrNG PR #70 file-context split: primary semantic review

## Result

**Approve with one Arabic action-label refinement** at PR head `9b56b5fde40daf59aa61a7ce2d14e6bf7b37bf9d`, tree `117fb2a8cc208c958ac62d00927cc65defe6530d`.

The review input is pinned by SHA256 `d08b3af50c143fe3e0e997a3c240936df7de30fe86d9e03c23936fe6b968c768`. The live PR is open and draft. The clean local worktree has catalog SHA256 `9c7a40251e51dc9904a3825e6bebc551d9db5313aa98bde62ffdeac32ffd7cd0` and `romarr/ui.py` SHA256 `b110af999efbe7bf22e8a1ee98be8cf6b4dee92f8f3b3fff606b59e38f9f527e`.

The exact caller context is pinned at `romarr/ui.py:5323` (`Acquire → Verify → File → Scan → Play`) and `romarr/ui.py:5987` (a table column whose cells render `x.filename`). I approve all 12 file-noun targets and 11 action targets unchanged. Refine Arabic from `أضِف إلى المكتبة` to the conventional unvocalized UI form `أضف إلى المكتبة`. No targets are held. The Vietnamese noun `Tệp` is accepted as a concise current computing term for file, in place of the older a127 wording `Tập tin`.

## Final reviewed targets

| Locale | File column noun | Add to library action |
|---|---|---|
| Spanish | `Archivo` | `Añadir a la biblioteca` |
| Simplified Chinese | `文件` | `添加到游戏库` |
| Hindi | `फ़ाइल` | `लाइब्रेरी में जोड़ें` |
| German | `Datei` | `Zur Bibliothek hinzufügen` |
| Japanese | `ファイル` | `ライブラリに追加` |
| French | `Fichier` | `Ajouter à la bibliothèque` |
| Brazilian Portuguese | `Arquivo` | `Adicionar à biblioteca` |
| Arabic | `ملف` | `أضف إلى المكتبة` |
| Korean | `파일` | `라이브러리에 추가` |
| Traditional Chinese | `檔案` | `新增至遊戲庫` |
| Vietnamese | `Tệp` | `Thêm vào thư viện` |
| Indonesian | `Berkas` | `Tambahkan ke pustaka` |

`primary-review.json` records each candidate, final target, decision, rationale, compact-JSON catalog target hash, and raw UTF-8 hash. Catalog target hashes follow `ui-labels.json`'s `translationHashes` convention. The report also pins the current catalog's “Library”, “Browse library”, and “A centralized game library…” terminology examples.

The proposed action source is `Add to library`, stable ID `ui.add-to-library.2bf9ea0e46`, source SHA256 `2bf9ea0e469087e8ac427990d72a88c37be1a8b07a5e9cbb961d3df2912d7877`. It is absent from the pinned current catalog, as expected for a proposed split.

## Reproduction and limits

Run the read-only pin and ledger check with:

```sh
python3 /mnt/disks/scratch/task-scratch/romarrng-pr70-file-context-split-primary-20261102/verify_primary_review.py
```

It validates the input checksum, PR/head/tree, clean worktree, source caller lines, current catalog hashes, existing draft status, and final target hashes. It writes only `primary-review.json` in this scratch folder. This is an AI primary semantic review with **moderate confidence**, not native-speaker approval. No browser review, repository edits, tests, builds, or CI were performed.

## Deliverables

- `primary-review.json`: exact reviewed targets, decisions, and hashes.
- `verify_primary_review.py`: read-only verifier and report generator.
- `SHA256SUMS`: checksums for the input packet, README, report, and verifier.
