import hashlib, json, re
from collections import Counter
from pathlib import Path

root=Path(__file__).parent
input_dir=root/'input'
rows=[json.loads(line) for line in (input_dir/'review-input.jsonl').read_text(encoding='utf-8').splitlines() if line]
locales=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
changes={
 (166,'ar'):('correction','عناصر الخلاصة: {items} من {sources} مصادر؛ العناصر المضافة إلى قائمة التنزيل: {grabbed}','Recast as labeled counts; the current singular verb leaves the counted object implicit and requires awkward number agreement.'),
 (170,'ar'):('refinement','قائمة الألعاب في المكتبة','The visible heading labels a table of game-library entries; “list of games in the library” is clearer than a stock/inventory reading.'),
 (170,'hi'):('refinement','गेम लाइब्रेरी की सूची','Use the ordinary software term for a game library and name the list represented by this screen instead of the mixed “लाइब्रेरी इन्वेंटरी”.'),
 (170,'ja'):('correction','ゲームライブラリ一覧','In this catalog table, インベントリ can mean a game’s item inventory; 一覧 accurately labels the library listing.'),
 (170,'ko'):('correction','게임 라이브러리 목록','인벤토리 can mean an in-game item inventory; 목록 fits the visible library table.'),
 (170,'vi'):('correction','Danh sách trò chơi trong thư viện','Kiểm kê describes taking stock; this heading labels the displayed list of games.'),
 (171,'hi'):('correction','गेम लाइब्रेरी अभी भी लोड हो रही है','पुस्तकालय suggests a physical/book library; in this game app, गेम लाइब्रेरी is the intended software collection.'),
 (176,'es'):('correction','Probablemente un conjunto de varios discos · revisar','Translate the technical phrase and express review as an action; the current label leaves “multi-disc set” in English.'),
 (176,'hi'):('correction','संभवतः कई डिस्क वाला सेट · समीक्षा आवश्यक','Translate the multi-disc term and make clear that the set still needs review.'),
 (176,'de'):('correction','Wahrscheinlich ein Set mit mehreren Discs · prüfen','Replace the English compound and the misleading rating sense of Bewertung with a review/check action.'),
 (176,'ar'):('correction','على الأرجح مجموعة متعددة الأقراص · تحتاج إلى مراجعة','Correct the agreement/plural in متعددة القرص and mark the item as needing review.'),
 (176,'vi'):('correction','Có thể là bộ nhiều đĩa · cần rà soát','Translate the disc-set phrase and use rà soát for an item requiring review; đánh giá suggests rating/evaluation.'),
 (176,'id'):('correction','Kemungkinan set berisi beberapa disk · perlu ditinjau','Translate the English set phrase and use perlu ditinjau; ulasan means a review/review article, not a pending review state.'),
 (178,'id'):('correction','Sinkronisasi daftar (jam)','Fix the inverted noun order and remove spaces inside the parenthetical unit.'),
 (179,'fr'):('correction','Vue en liste','The source labels a display mode paired with Cover view; Voir la liste is an imperative, not the mode name.'),
 (179,'pt-BR'):('refinement','Visualização em lista','Use the standard display-mode phrasing for a toggle paired with cover view.'),
 (179,'id'):('correction','Tampilan daftar','“Daftar pandangan” reads as a list of views; Tampilan daftar names the list display mode.'),
 (181,'zh-Hans'):('refinement','已加载 DAT · 已验证的转储名称','Chinese does not mark plural DAT with English -s; translate dump while preserving the technical DAT label.'),
 (181,'zh-Hant'):('refinement','已載入 DAT · 已驗證的傾印名稱','Traditional Chinese does not mark plural DAT with English -s; 傾印 is a technical rendering of dump.'),
 (182,'es'):('refinement','Cargando el inventario…','Use an active progress phrase for the empty-state loading message; the current noun phrase sounds like a section title.'),
 (182,'hi'):('refinement','गेम लाइब्रेरी की सूची लोड हो रही है…','Align the progress state with the actual game-library list and avoid the physical-library/inventory reading.'),
 (182,'ja'):('correction','ライブラリ一覧を読み込み中…','The state loads a library table; 一覧 is more accurate than the game-item-inventory sense of インベントリ.'),
 (182,'pt-BR'):('refinement','Carregando o inventário…','Use the natural ongoing-state form for a loading placeholder.'),
 (182,'ar'):('correction','جارٍ تحميل قائمة الألعاب في المكتبة…','The loading state is the game-library list; المخزون suggests stock and the current two dots are not a proper ellipsis.'),
 (182,'vi'):('correction','Đang tải danh sách trò chơi trong thư viện…','Kiểm kê means stocktaking; this state loads the game list shown in the library inventory.'),
 (183,'es'):('correction','Registros locales de ES-DE reutilizados: {count}','Use the natural metric-label order and separate the count from the label.'),
 (183,'hi'):('correction','पुनः उपयोग किए गए स्थानीय ES-DE रिकॉर्ड: {count}','Reorder into a grammatical metric label and separate the count.'),
 (183,'de'):('correction','Wiederverwendete lokale ES-DE-Datensätze: {count}','Aufzeichnungen suggests recordings; Datensätze is the appropriate term for reused software records.'),
 (183,'ja'):('correction','再利用したローカル ES-DE レコード: {count}','地元 means geographically local; ローカル is the intended local-data sense, with natural metric-label ordering.'),
 (183,'ko'):('correction','재사용된 로컬 ES-DE 레코드: {count}','현지 means a local area; 로컬 expresses local software data and the count label reads naturally.'),
 (183,'zh-Hant'):('correction','已重用 {count} 筆本機 ES-DE 記錄','本機 expresses local-device data; 當地 is geographically local. The count-classifier order is natural.'),
 (183,'id'):('correction','Entri ES-DE lokal yang digunakan kembali: {count}','Entri is the appropriate database-record sense; rekaman can mean an audio/video recording.'),
 (185,'zh-Hans'):('refinement','查询失败: {error_type}','查询更 specifically describes the provider lookup call than a broad search.'),
 (185,'de'):('correction','Suche fehlgeschlagen: {error_type}','Versagt is not idiomatic for this failed lookup result; fehlgeschlagen is the standard UI wording.'),
 (185,'ar'):('correction','فشل البحث: {error_type}','Use standard Arabic verb-subject order for “lookup failed”.'),
 (185,'ko'):('correction','검색 실패: {error_type}','Remove the space before the colon in Korean UI punctuation.'),
 (185,'zh-Hant'):('correction','查詢失敗：{error_type}','查詢 better expresses the provider lookup operation than 搜索, and the full-width colon matches Traditional Chinese punctuation.'),
}
holds={177:'Source text is split immediately before inline code, and a neighboring catalogued fragment starts the rest of the sentence. Cell-level edits could duplicate or misorder the noun; review the complete sentence with the code span.',184:'No exact-head production caller or rendering path is present for this detail message. The similar dynamic message is bound to ordinal 185 and its error_type placeholder, not this detail string.'}

def file_sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def raw_sha(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()
def content_hash(value):
    serialized=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
def ph(s): return Counter(re.findall(r'\{([A-Za-z_][A-Za-z0-9_]*)\}',s))
assert len(rows)==240, len(rows)
assert len({(r['sourceOrdinal'],r['locale']) for r in rows})==240
assert set(r['locale'] for r in rows)==set(locales)
ledger=[]
for r in rows:
    n=r['sourceOrdinal']; loc=r['locale']; key=(n,loc)
    assert raw_sha(r['source'])==r['sourceSha256'], (n,loc,'source hash')
    assert content_hash(r['currentTarget'])==r['currentTargetSha256']==r['storedTranslationHash'], (n,loc,'target hash')
    assert ph(r['currentTarget'])==ph(r['source']), (n,loc,'current placeholder mismatch')
    if n in holds:
        status='hold'; proposed=None; rationale=holds[n]
    elif key in changes:
        status,proposed,rationale=changes[key]
    else:
        status='accept-current'; proposed=None; rationale='Current target preserves the source meaning in the pinned UI/runtime context; placeholders and protected technical names are retained.'
    if proposed is not None:
        assert ph(proposed)==ph(r['source']), (n,loc,ph(proposed),ph(r['source']))
        finalhash=content_hash(proposed)
    else:
        finalhash=None
    if status=='accept-current': assert ph(r['currentTarget'])==ph(r['source']), (n,loc,'placeholder mismatch')
    if status=='hold': proposed=None
    ledger.append({
      'sourceOrdinal':n,'id':r['id'],'locale':loc,'source':r['source'],'sourceSha256':r['sourceSha256'],
      'currentTarget':r['currentTarget'],'currentTargetSha256':r['currentTargetSha256'],
      'disposition':status,'proposedTarget':proposed,'proposedTargetSha256':finalhash,'rationale':rationale,
      'callerExists':r['callerExists'],'sourceContextResolved':r['sourceContextResolved'],
      'translationStatus':r['translationStatus']
    })
assert len(changes)==37, len(changes)
assert len(ledger)==240
counts=Counter(x['disposition'] for x in ledger)
assert counts==Counter({'accept-current':179,'correction':28,'refinement':9,'hold':24}),counts
out=root/'blind-review.jsonl'
out.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in ledger),encoding='utf-8')
summary={
 'repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':'5e45ce90babf3cf385fbb9775e70d7e8fcc6a783','tree':'580de0b2db5030101c47a81fbd8a23489e993f75',
 'window':'W166-W185','cellCount':len(ledger),'sourceCount':20,'localeOrder':locales,'dispositions':dict(counts),
 'inputManifestSha256':file_sha(input_dir/'manifest.json'),
 'ledgerSha256':file_sha(out),
 'placeholderCheck':'pass-all-240-current-targets-and-37-proposals',
 'method':'Independent candidate-free review from input/ only; primary-private was not read.',
 'limitations':['Machine review is not qualified native-speaker approval.','Ordinals 177 and 184 remain held in all locales.']
}
(root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme='''# ROMarrNG PR #70 W166–W185 independent blind review\n\nExact PR head: `5e45ce90babf3cf385fbb9775e70d7e8fcc6a783` / tree `580de0b2db5030101c47a81fbd8a23489e993f75`.\n\nThis review used the candidate-free `input/` packet only. The primary-private review was not opened. It covers all 240 cells across source ordinals 166–185 and 12 locales.\n\nDisposition counts: 179 accept-current, 28 corrections, 9 refinements, and 24 holds. Ordinal 177 is held because the UI sentence is split around inline code and a neighboring catalogued fragment. Ordinal 184 is held because no exact-head caller/render path was found; the similarly worded dynamic message belongs to ordinal 185.\n\nAll current source and target hashes were recomputed from input; all 240 current targets and all 37 proposed values preserve the source placeholder set. The full cell ledger is `blind-review.jsonl`; summary and checksums are adjacent.\n\nThis is machine review, not qualified native-speaker approval. No repository or PR was modified. No tests, builds, scans, CI, browser, release, or tag activity occurred.\n'''
(root/'README.md').write_text(readme,encoding='utf-8')
manifest=[]
for p in sorted(root.iterdir()):
    if p.is_file() and p.name not in ('SHA256SUMS.txt','build-review.py'):
        manifest.append(f'{file_sha(p)}  {p.name}')
(root/'SHA256SUMS.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
