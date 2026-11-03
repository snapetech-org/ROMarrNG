# ROMarrNG PR #70 W245–W264 third-party cross-audit

Exact PR head `e7f8d0dcb11d8d94c8a89c37cb9ab451d72810a6` / tree `016587d26f04d2920a30878236f1933a57e27901`; branch and pull refs both match the live open draft PR.

## Reconciliation

All three sealed packets passed their checksum manifests. The cross-audit reconciles 240 cells (20 active source IDs × 12 direct locales) against the current catalog, primary semantic ledger, independent blind ledger, and exact current caller/runtime spans. Sixteen stale source-index location hints were reconciled to exact current source spans; none of those old hints is treated as a current caller.

The primary review marks 72 cells as holds because their user-facing localization path is unresolved or the exact source is internal. These are tracked as `hold-caller-path`, separately from translation semantics. The blind reviewer judged 70 of those current targets semantically acceptable and flagged two translation errors at position 259 (pt-BR and zh-Hant); neither receives a selected catalog target until an explicit local-template caller exists. The remaining 168 cells have no caller-path hold and no translation-level hold remains.

Final cross-audit counts: 138 accept-current, 14 corrections, 16 refinements, and 72 caller-path holds. Thirty catalog changes are selected. All selected targets preserve placeholders, markup, numeric tokens, and edge whitespace. Machine review does not establish native-speaker approval; no release approval is granted.

## Selected changes

### Position 245: `Owned check unavailable`

- **de — refinement** `Eigentümercheck nicht verfügbar` → `Abgleich mit dem eigenen Spielebestand nicht verfügbar`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: Eigentümercheck is an awkward compound here. The caller checks whether catalog games are already in the user library; this wording names that inventory check directly.
- **fr — refinement** `Vérification propriétaire inaccessible` → `Vérification des jeux déjà possédés indisponible`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: Vérification propriétaire is not idiomatic French. The caller checks whether games are already in the user library, which this wording states directly.
- **hi — correction** `संपत्ति की जांच उपलब्ध नहीं है` → `लाइब्रेरी में मौजूद गेम की जाँच उपलब्ध नहीं है`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: संपत्ति की जांच means a property check and misses the game-library context. The caller checks which catalog titles are already in the user library.
- **ko — refinement** `소유권 체크 불가능` → `보유 게임을 확인할 수 없습니다`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: 소유권 체크 불가능 is a compressed colloquial loanword phrase. The caller checks which titles the user already has; this states that the check cannot be done.

### Position 247: `Patch catalogue URL (optional)`

- **ar — refinement** `كتالوج التصحيح URL (اختياري)` → `عنوان URL لكتالوج التعديلات (اختياري)`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: The current word order reads as a correction-catalog URL. This reorders the label into a natural Arabic URL-of-catalog phrase while keeping URL and the broader patch-project sense.
- **de — refinement** `Patch Katalog URL (optional)` → `URL des Patch-Katalogs (optional)`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value refinement; the concern remains supported by the exact source meaning and UI context: The current compound leaves URL in an unnatural sequence. The proposal uses standard German compound punctuation and natural genitive order.
- **es — correction** `Catálogo de patches URL (opcional)` → `URL del catálogo de parches (opcional)`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: The current target places URL after the catalog noun phrase, producing an awkward label. The proposal uses natural Spanish order and translates patches.
- **pt-BR — correction** `Catálogo de Patch URL (opcional)` → `URL do catálogo de patches (opcional)`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: The current target places URL after the catalog noun phrase, producing an awkward label. The proposal uses natural Portuguese order and retains the common patches loanword.
- **zh-Hans — refinement** `Patch 目录 URL (可选)` → `补丁目录 URL（可选）`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: The current target leaves Patch in English. 补丁 is the standard Chinese term in this software-catalog context; URL is retained as a familiar technical acronym.
- **zh-Hant — refinement** `Patch 目錄 URL (可選)` → `補丁目錄 URL（可選）`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: The current target leaves Patch in English. 補丁 is the standard Traditional Chinese term in this software-catalog context; URL is retained as a familiar technical acronym.

### Position 250: `Path mapping for {path}`

- **es — correction** `Asignación de rutas para {path}` → `Asignación de ruta para {path}`. The English source and the exact accessibility-name caller describe one path-mapping row, but the current Spanish says “rutas” (plural). The singular target preserves the path placeholder and the one-row meaning.

### Position 251: `Pick one route. You can return here and add the other pieces later.`

- **es — correction** `Seleccione una ruta. Puedes volver aquí y agregar las otras piezas más tarde.` → `Elige una ruta. Puedes volver aquí y agregar las otras partes más adelante.`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: The current sentence switches from formal Seleccione to informal Puedes. The proposal keeps the informal address consistent and preserves the choose-and-return instruction.
- **fr — refinement** `Choisissez une route. Vous pouvez revenir ici et ajouter les autres pièces plus tard.` → `Choisissez une route. Vous pourrez revenir ici plus tard pour ajouter les autres éléments.`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: The current pièces suggests physical pieces. The caller is onboarding guidance about adding other setup parts, for which éléments is clearer.
- **hi — refinement** `एक मार्ग चुनें. आप यहां वापस आ सकते हैं और बाद में अन्य टुकड़ों को जोड़ सकते हैं.` → `एक मार्ग चुनें। आप बाद में यहाँ लौटकर बाकी हिस्से जोड़ सकते हैं।`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: The current message is understandable, but uses ASCII punctuation after the first clause. The proposal uses standard Hindi danda punctuation and keeps the same formal guidance.
- **id — refinement** `Pilih satu rute. Anda dapat kembali di sini dan menambahkan potongan-potongan lainnya kemudian.` → `Pilih satu alur. Anda bisa kembali ke sini nanti untuk menambahkan bagian lainnya.`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: Potongan-potongan suggests physical fragments. The caller describes a setup path; alur and bagian lainnya express that flow more naturally.
- **pt-BR — correction** `Escolha uma rota. você pode voltar aqui e adicionar as outras peças mais tarde.` → `Escolha uma rota. Você pode voltar aqui e adicionar as outras partes depois.`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: The current sentence starts the second sentence with lowercase você. The proposal corrects sentence capitalization and preserves the route-and-return instruction.
- **vi — refinement** `Chọn một con đường. bạn có thể trở lại đây và thêm các mảnh khác sau đó.` → `Chọn một hướng đi. Bạn có thể quay lại đây sau để bổ sung các phần còn lại.`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: Con đường is a literal road and mảnh suggests physical fragments. This onboarding sentence is about choosing a setup path and adding remaining parts later.
- **zh-Hans — correction** `选择一个路线. 您可以返回这里并稍后添加其他零件。` → `选择一个方案。您可以稍后再回到这里，添加其他部分。`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: The current 一个路线 has a classifier mismatch, and 零件 means physical components. The proposal uses natural onboarding wording and full-width Chinese punctuation.
- **zh-Hant — correction** `選擇一個路線. 您可以返回這裡並稍後添加其他零件。` → `選擇一個方案。您可以稍後再回到這裡，新增其他部分。`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: The current 一個路線 has a classifier mismatch, and 零件 means physical components. The proposal uses natural onboarding wording and Traditional Chinese punctuation.

### Position 253: `Platform folder names`

- **de — correction** `Plattformfoldernamen` → `Plattform-Ordnernamen`. The current German compound “Plattformfoldernamen” leaves “folder” in English and is awkward. A clear hyphenated German compound accurately names the platform-folder group heading.
- **hi — correction** `मंच फ़ोल्डर नाम` → `प्लेटफ़ॉर्म फ़ोल्डरों के नाम`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value refinement; the concern remains supported by the exact source meaning and UI context: मंच commonly means a stage or platform in the physical sense. In this game-system settings page, प्लेटफ़ॉर्म is the established term for a game platform.

### Position 255: `Playlist:`

- **ar — correction** `قائمة اللعب :` → `قائمة التشغيل:`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: قائمة اللعب is not the usual Arabic term for a playlist, and the space before the colon is incorrect. This is the label for an M3U playlist file.
- **ko — refinement** `플레이리스트 :` → `플레이리스트:`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: The current target has a space before the colon. Removing it follows standard Korean spacing for this compact label.
- **pt-BR — correction** `Lista de jogos:` → `Lista de reprodução:`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: Lista de jogos means a list of games, not a playlist file. The caller labels an M3U playlist path.
- **zh-Hans — correction** `游戏名单:` → `播放列表：`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: 游戏名单 means a roster or game list, not a playlist file. The caller labels an M3U playlist path.
- **zh-Hant — correction** `游戲名單:` → `播放清單：`. The pinned caller supports the primary's correction proposal. The blind reviewer marked the current value correction; the concern remains supported by the exact source meaning and UI context: 游戲名單 uses simplified-character forms and means a game roster, not a playlist file. This uses the Traditional Chinese term for playlist.

### Position 260: `Popular`

- **ar — refinement** `شائع` → `الأكثر شعبية`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: The current adjective شائع is a bare descriptive form. For a discovery shelf of popular titles, الأكثر شعبية is a natural Arabic category label.
- **zh-Hans — refinement** `受欢迎` → `热门`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: 受欢迎 describes being welcomed and is less idiomatic for a catalog shelf of popular titles. 热门 is the conventional category label.
- **zh-Hant — refinement** `受歡迎` → `熱門`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: 受歡迎 describes being welcomed and is less idiomatic for a catalog shelf of popular titles. 熱門 is the conventional category label.

### Position 263: `{processed} / {total} files checked`

- **ar — refinement** `تم التحقق من {processed} من أصل {total} ملفاً` → `الملفات التي تم التحقق منها: {processed} من أصل {total}`. The pinned caller supports the primary's refinement proposal. The blind reviewer marked the current value accept-current; the concern remains supported by the exact source meaning and UI context: The current Arabic appends singular ملفاً after variable counts. The proposal moves the noun before the count so the label remains grammatical for any number.

## Caller-path holds

All 12 locale cells remain held at each position below pending an exact user-facing localized template/path:

- 248: dynamically returned missing-library-path hint is rendered as opaque raw API text.
- 249: dynamically returned stored-path/fallback diagnostic is rendered as opaque raw API text.
- 256: plugin-fetch detail is rendered as opaque raw API text.
- 257: internal confinement exception is discarded; no exact user-facing caller exists.
- 258: disabled-plugin detail is rendered as opaque raw API text.
- 259: not-installed detail, including dynamic exception text, is rendered as opaque raw API text.

For position 259, the blind review separately flags pt-BR and zh-Hant wording; selectedTarget remains null under the caller-path hold.

## Evidence and limits

- `cross-audit-ledger.jsonl` contains the cell-level primary/blind lineage, current caller evidence, chosen/deferred disposition, selected target and hashes, and structural checks.
- `summary.json` records counts and live head verification.
- Input, primary, and blind packets remain in their separate task-scoped scratch directories and are referenced by SHA-256 checksum-manifest hashes in the summary.
- No repository or PR files were changed; no tests, builds, scans, or CI jobs were run. Exact-head browser acceptance and qualified native-speaker approval remain pending.
