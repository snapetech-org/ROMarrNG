import hashlib, json
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w345-364-primary-20261103/input')
OUT = Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w345-364-blind-20261103/blind-review')
MANIFEST = json.loads((INPUT / 'manifest.json').read_text(encoding='utf-8'))
HEAD = MANIFEST['head']
TREE = MANIFEST['tree']

def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# (position, locale): (disposition, target, rationale, confidence)
DECISIONS = {
    (345, 'zh-Hans'): ('correction', '扫描完成', 'The current wording reads as “complete scan”; this is the completed-state label.', 'high'),
    (345, 'hi'): ('refinement', 'स्कैन पूरा हुआ', 'This states that the scan finished more naturally than the current noun phrase.', 'moderate'),
    (345, 'zh-Hant'): ('correction', '掃描完成', 'The current wording reads as “complete scan”; this is the completed-state label.', 'high'),
    (345, 'vi'): ('correction', 'Quét hoàn tất', 'The current value mixes English Scan with Vietnamese and reads like a complete scan rather than a completed state.', 'high'),
    (345, 'id'): ('correction', 'Pemindaian selesai', 'The current value means a complete scan; this is the completed-state label.', 'high'),

    (346, 'es'): ('correction', 'Error al escanear: {error_type}', 'Escaneamiento fallido is uncommon and awkward Spanish for a short error template.', 'high'),
    (346, 'zh-Hans'): ('refinement', '扫描失败：{error_type}', 'Use Chinese full-width punctuation consistently around the dynamic error type.', 'high'),
    (346, 'de'): ('correction', 'Scan fehlgeschlagen: {error_type}', 'Scannen versagt is not idiomatic for this status/error template.', 'high'),
    (346, 'fr'): ('correction', 'Échec de l’analyse : {error_type}', 'Scanner échoué is ungrammatical French; this concise error form fits the toast.', 'high'),
    (346, 'pt-BR'): ('correction', 'Falha ao escanear: {error_type}', 'Escaneamento falhado is unnatural in Brazilian Portuguese.', 'high'),
    (346, 'ar'): ('refinement', 'فشل الفحص: {error_type}', 'Use the concise Arabic failure construction for this error template.', 'moderate'),
    (346, 'ko'): ('refinement', '스캔 실패: {error_type}', 'Remove the nonstandard space before the colon in this compact error label.', 'high'),
    (346, 'zh-Hant'): ('refinement', '掃描失敗：{error_type}', 'Use Chinese full-width punctuation consistently around the dynamic error type.', 'high'),
    (346, 'id'): ('refinement', 'Pemindaian gagal: {error_type}', 'This finite status construction is more natural than the current abstract failure noun.', 'moderate'),

    (347, 'es'): ('refinement', 'El escaneo falló', 'Falló is the ordinary verb for this completed failure status; fracasó is overly dramatic.', 'moderate'),
    (347, 'hi'): ('refinement', 'स्कैन विफल हुआ', 'This is a more natural completed failure-status phrase than the current noun/adjective construction.', 'moderate'),
    (347, 'de'): ('correction', 'Scan fehlgeschlagen', 'Scannen scheitert is present tense; the caller displays a completed failure status.', 'high'),
    (347, 'fr'): ('correction', 'Échec de l’analyse', 'Le scan échoue is present tense and awkward for a completed status label.', 'high'),
    (347, 'ar'): ('refinement', 'فشل الفحص', 'Use the concise failure construction for the completed scan status.', 'moderate'),
    (347, 'vi'): ('correction', 'Quét thất bại', 'The current English Scan should be localized in this Vietnamese status label.', 'high'),
    (347, 'id'): ('correction', 'Pemindaian gagal', 'The current value mixes English scan with Indonesian; this is a natural completed-status phrase.', 'high'),

    (348, 'ja'): ('correction', 'ライブラリをスキャン', '図書館 means a public library; the source is the configured game-file library.', 'high'),
    (348, 'ko'): ('correction', '라이브러리 스캔', 'The current word order is unnatural and 도서관 suggests a public library rather than a game library.', 'high'),
    (348, 'zh-Hant'): ('correction', '掃描媒體庫', '圖書館 means a public library; the glossary defines the user game-file library.', 'high'),
    (348, 'vi'): ('correction', 'Quét thư viện', 'Localize Scan and use the established Vietnamese term for the configured library.', 'high'),
    (348, 'id'): ('correction', 'Pindai pustaka game', 'The current word order is unnatural and can mean “library scan”; the source is an action on the game library.', 'moderate'),

    (349, 'pt-BR'): ('correction', 'A verificação atingiu seu limite de segurança', 'The current verb is present tense and does not express that this scan reached the cap.', 'high'),
    (349, 'vi'): ('correction', 'Quét đã đạt giới hạn an toàn', 'The current English Scan should be localized and the completed-state marker made explicit.', 'high'),
    (349, 'id'): ('correction', 'Pemindaian mencapai batas aman', 'Localize Scan and avoid keamanan, which can imply a security boundary instead of a safety cap.', 'moderate'),

    (350, 'es'): ('correction', 'Escanea el URI o introduce el secreto en cualquier aplicación TOTP. A partir de ahora se pedirán códigos al iniciar sesión; los códigos de respaldo solo se pueden usar una vez.', 'The current sentence omits that codes are requested at sign-in; preserve the one-time backup-code warning.', 'high'),
    (350, 'hi'): ('refinement', 'URI स्कैन करें या किसी भी TOTP ऐप में सीक्रेट दर्ज करें। अब से साइन इन करते समय कोड मांगे जाएंगे; बैकअप कोड केवल एक बार इस्तेमाल किए जा सकते हैं।', 'Clarify that codes are requested at sign-in and use natural Hindi phrasing for the one-time backup codes.', 'moderate'),
    (350, 'de'): ('refinement', 'Scanne den URI oder gib das Geheimnis in einer beliebigen TOTP-App ein. Ab jetzt werden die Codes bei der Anmeldung abgefragt; Backup-Codes können nur einmal verwendet werden.', 'URI-Code is redundant; the revised German keeps the sign-in timing and one-time warning.', 'moderate'),
    (350, 'fr'): ('correction', 'Scannez l’URI ou saisissez le secret dans n’importe quelle application TOTP. À partir de maintenant, les codes seront demandés à la connexion ; les codes de secours ne sont utilisables qu’une seule fois.', 'Correct the article before URI and restore the missing sign-in context while keeping the backup-code limit.', 'high'),
    (350, 'pt-BR'): ('correction', 'Escaneie o URI ou insira o segredo em qualquer aplicativo TOTP. A partir de agora, os códigos serão solicitados ao fazer login; cada código de backup só pode ser usado uma vez.', 'The current note omits the sign-in context and has clipped sentence structure.', 'high'),
    (350, 'ar'): ('correction', 'امسح رمز URI ضوئيًا أو أدخل المفتاح السري في أي تطبيق TOTP. سيُطلب منك إدخال الرموز عند تسجيل الدخول من الآن فصاعدًا؛ ولا يمكن استخدام رموز النسخ الاحتياطي إلا مرة واحدة.', 'Repair the current Arabic grammar and preserve URI, TOTP, sign-in timing, and the one-time backup-code warning.', 'moderate'),
    (350, 'ko'): ('correction', 'URI를 스캔하거나 아무 TOTP 앱에 비밀 키를 입력하세요. 이제부터 로그인할 때 코드를 입력해야 합니다. 백업 코드는 한 번만 사용할 수 있습니다.', 'The current Korean has awkward particles/word order and an unnatural single-use phrase.', 'high'),
    (350, 'vi'): ('correction', 'Quét URI hoặc nhập bí mật vào bất kỳ ứng dụng TOTP nào. Từ nay, mã sẽ được yêu cầu khi đăng nhập; mã dự phòng chỉ dùng được một lần.', 'Kiểm tra means check rather than scan, and the current backup-code sentence does not clearly say only once.', 'high'),
    (350, 'id'): ('correction', 'Pindai URI atau masukkan rahasia ke aplikasi TOTP apa pun. Mulai sekarang, kode akan diminta saat masuk; kode cadangan hanya dapat digunakan sekali.', 'Localize Scan and replace the current awkward “one-one” wording with the one-time-use meaning.', 'high'),

    (351, 'ko'): ('correction', 'ES-DE 게임 목록을 게시하기 전에 이 플랫폼을 스캔하세요.', 'Correct the missing Korean word spacing and express the instruction naturally.', 'high'),
    (351, 'zh-Hant'): ('refinement', '在發布 ES-DE 遊戲清單之前，請先掃描此平台。', 'Use the traditional 遊 character and a natural instruction form; preserve ES-DE.', 'high'),
    (351, 'id'): ('correction', 'Pindai platform ini sebelum menerbitkan daftar game ES-DE.', 'Periksa means inspect/check; the source requires scanning the platform before publishing.', 'high'),

    (352, 'es'): ('correction', 'Escaneando', 'The source is an in-progress state label, not an infinitive command.', 'high'),
    (352, 'zh-Hans'): ('refinement', '扫描中', 'Make the active scanning state explicit rather than using the bare scan noun.', 'high'),
    (352, 'de'): ('correction', 'Wird gescannt', 'Scannen is an infinitive/noun, while this caller displays an in-progress state.', 'high'),
    (352, 'ja'): ('refinement', 'スキャン中', 'Make the in-progress state explicit rather than using only the scan noun.', 'high'),
    (352, 'fr'): ('correction', 'Analyse en cours', 'Scanner is an infinitive; the caller displays an in-progress state.', 'high'),
    (352, 'pt-BR'): ('refinement', 'Escaneando', 'Use the active-state form to match the in-progress status.', 'moderate'),
    (352, 'ar'): ('correction', 'جارٍ الفحص', 'Use an in-progress construction rather than a bare noun for the state label.', 'moderate'),
    (352, 'ko'): ('refinement', '스캔 중', 'Make the in-progress state explicit rather than using only the scan noun.', 'high'),
    (352, 'zh-Hant'): ('refinement', '掃描中', 'Make the active scanning state explicit rather than using the bare scan noun.', 'high'),

    (353, 'zh-Hans'): ('correction', '搜索补丁项目', 'Patch projects are game patch projects; use the localized gaming term instead of leaving patch in English.', 'moderate'),
    (353, 'ja'): ('correction', 'パッチプロジェクトを検索', 'The current Japanese word order is unnatural for “search patch projects.”', 'high'),
    (353, 'pt-BR'): ('correction', 'Pesquisar projetos de patches', 'The current phrase has incorrect Portuguese word order and meaning.', 'high'),
    (353, 'ko'): ('correction', '패치 프로젝트 검색', 'The current Korean word order is unnatural for a search label.', 'high'),
    (353, 'zh-Hant'): ('correction', '搜尋補丁專案', 'Patch projects are game patch projects; use the localized gaming term instead of leaving patch in English.', 'moderate'),

    (354, 'ja'): ('correction', 'プラットフォームを検索', 'The current wording means “search platform”; this placeholder searches for platforms.', 'high'),
    (354, 'fr'): ('correction', 'Rechercher des plateformes', 'The current wording describes search platforms instead of the action “search platforms.”', 'high'),
    (354, 'pt-BR'): ('correction', 'Buscar plataformas', 'The current noun phrase means search platforms rather than asking the user to search for platforms.', 'high'),
    (354, 'ar'): ('correction', 'ابحث عن المنصات', 'Use an action phrase for this platform-filter search placeholder.', 'moderate'),
    (354, 'ko'): ('correction', '플랫폼 검색', 'The current word order describes a search platform, not a platform search action.', 'high'),
    (354, 'zh-Hant'): ('refinement', '搜尋平台', 'Prefer the common traditional-character verb 搜尋 for this search placeholder.', 'high'),
    (354, 'id'): ('correction', 'Cari platform', 'The current noun phrase means a search platform rather than the action to search for platforms.', 'high'),

    (355, 'hi'): ('correction', 'प्लगइन खोजें', 'The current noun order does not express the search action naturally.', 'high'),
    (355, 'de'): ('refinement', 'Plugins suchen', 'Use the ordinary German verb phrase for a search control.', 'high'),
    (355, 'ja'): ('correction', 'プラグインを検索', 'The current Japanese word order is unnatural for a search action.', 'high'),
    (355, 'pt-BR'): ('correction', 'Pesquisar plugins', 'The current noun phrase and capitalization are awkward for a search control.', 'high'),
    (355, 'ko'): ('correction', '플러그인 검색', 'The current Korean word order is unnatural for a search control.', 'high'),
    (355, 'id'): ('correction', 'Cari plugin', 'Use the direct Indonesian search action instead of a noun phrase.', 'high'),

    (356, 'es'): ('correction', 'Buscar en la lista de juegos deseados', 'The current phrase can mean finding the list itself; the task searches within ROMarr’s Wanted games list.', 'moderate'),
    (356, 'zh-Hans'): ('refinement', '搜索待获取游戏列表', 'Clarify that this is a list of wanted games to acquire, not a required generic list.', 'moderate'),
    (356, 'hi'): ('refinement', 'वांछित गेम सूची में खोजें', 'Clarify that the task searches within the Wanted games list.', 'moderate'),
    (356, 'de'): ('correction', 'Wunschliste durchsuchen', 'The current phrase searches for a desired list; the task searches within the Wanted games list.', 'high'),
    (356, 'ja'): ('correction', '欲しいゲームのリストを検索', 'The current wording means a requested list and does not naturally name the list of wanted games.', 'moderate'),
    (356, 'fr'): ('correction', 'Rechercher dans la liste des jeux recherchés', 'The current phrase can mean searching for the list itself; this task searches the Wanted games list.', 'moderate'),
    (356, 'pt-BR'): ('correction', 'Buscar na lista de jogos desejados', 'Clarify that the task searches within the Wanted games list rather than looking for a list.', 'moderate'),
    (356, 'ar'): ('correction', 'ابحث في قائمة الألعاب المطلوبة', 'Clarify that the search occurs within the list of wanted games.', 'moderate'),
    (356, 'ko'): ('correction', '원하는 게임 목록 검색', 'Clarify that the task searches the wanted-games list rather than finding the list itself.', 'moderate'),
    (356, 'zh-Hant'): ('refinement', '搜尋待取得遊戲清單', 'Clarify that this is a list of wanted games to acquire, not a required generic list.', 'moderate'),
    (356, 'vi'): ('correction', 'Tìm trong danh sách trò chơi mong muốn', 'The current wording can mean finding the list itself; this task searches within the Wanted games list.', 'moderate'),
    (356, 'id'): ('correction', 'Telusuri daftar game yang diinginkan', 'Clarify that the task searches within the wanted-games list rather than finding the list itself.', 'moderate'),

    (357, 'de'): ('refinement', 'Diesen Katalog durchsuchen', 'Prefer the natural German action phrase for searching within the current catalog.', 'high'),
    (357, 'fr'): ('refinement', 'Rechercher dans ce catalogue', 'Clarify that the search is within the current catalog.', 'high'),
    (357, 'ar'): ('correction', 'ابحث في هذا الكتالوج', 'The current wording can mean searching for the catalog; the control searches within it.', 'moderate'),
    (357, 'zh-Hant'): ('refinement', '搜尋此目錄', 'Use the traditional-character search verb for the catalog placeholder.', 'high'),

    (358, 'de'): ('correction', 'Titel durchsuchen', 'Suche Titel is unnatural German for this title-search field.', 'high'),
    (358, 'ar'): ('correction', 'ابحث عن العناوين', 'The current phrase is incomplete without the article and does not read naturally as a search prompt.', 'moderate'),
    (358, 'ko'): ('correction', '제목 검색', 'The current 타이틀 phrase is awkward in Korean; 제목 is the natural label for titles.', 'high'),
    (358, 'zh-Hant'): ('refinement', '搜尋標題', 'Prefer the common traditional-character search verb for this placeholder.', 'high'),
    (358, 'id'): ('correction', 'Cari judul', 'Use the direct Indonesian search action instead of the noun-form Pencarian judul.', 'high'),

    (359, 'es'): ('correction', 'Buscados: {searched}; enviados al cliente de descargas: {grabbed}; omitidos durante la espera antes de reintentar: {skipped}', 'The pinned caller counts wanted games and reports a successful handoff to the download client; the current wording implies completed downloads.', 'moderate'),
    (359, 'hi'): ('correction', 'खोजे गए गेम: {searched}; डाउनलोड क्लाइंट को भेजे गए रिलीज़: {grabbed}; पुनः प्रयास की प्रतीक्षा में छोड़े गए: {skipped}', 'The caller counts wanted games/releases, not sources; the current target says sources and completed downloads.', 'moderate'),
    (359, 'de'): ('correction', 'Durchsucht: {searched}; an den Download-Client übergeben: {grabbed}; wegen der Wartezeit vor dem nächsten Versuch übersprungen: {skipped}', 'The caller reports an acquisition handed to the download client, not a completed download.', 'moderate'),
    (359, 'ja'): ('correction', '検索したゲーム数: {searched}、ダウンロードクライアントに渡したリリース数: {grabbed}、再試行の待機中にスキップ: {skipped}', 'The caller counts wanted games and release handoffs; the current wording implies releases were already downloaded.', 'moderate'),
    (359, 'fr'): ('correction', 'Jeux recherchés : {searched} ; éléments remis au client de téléchargement : {grabbed} ; ignorés pendant l’attente avant la nouvelle tentative : {skipped}', 'The caller reports wanted-game searches and handoffs, not completed downloads.', 'moderate'),
    (359, 'pt-BR'): ('correction', 'Jogos pesquisados: {searched}; itens enviados ao cliente de download: {grabbed}; {skipped} ignorados durante a espera antes de tentar novamente', 'The current target implies completed downloads; the caller reports items handed to the download client.', 'moderate'),
    (359, 'ar'): ('correction', 'عدد الألعاب التي جرى البحث عنها: {searched}، والعناصر المرسلة إلى عميل التنزيل: {grabbed}، والمتجاوزة أثناء انتظار إعادة المحاولة: {skipped}', 'The current target implies completed downloads/search actions; the caller reports wanted-game counts and download-client handoffs.', 'moderate'),
    (359, 'ko'): ('correction', '검색한 게임 {searched}개, 다운로드 클라이언트로 보낸 항목 {grabbed}개, 재시도 대기 중 건너뛴 항목 {skipped}개', 'The current target says releases were downloaded; the caller only counts successful handoffs to the download client.', 'moderate'),
    (359, 'vi'): ('correction', 'Đã tìm kiếm {searched} game; đã gửi {grabbed} bản phát hành cho trình tải xuống; bỏ qua {skipped} game trong thời gian chờ thử lại', 'The caller counts wanted games, not sources, and reports release handoffs rather than completed downloads.', 'moderate'),
    (359, 'id'): ('correction', 'Game yang dicari: {searched}; rilis yang dikirim ke klien unduhan: {grabbed}; dilewati selama masa tunggu sebelum mencoba lagi: {skipped}', 'The current target says sources and obtained releases; the caller counts wanted-game searches and handoffs.', 'moderate'),

    (360, 'es'): ('correction', 'Buscados: {searched}; enviados al cliente de descargas: {grabbed}', 'The caller reports a successful handoff to the download client, not a completed download.', 'moderate'),
    (360, 'hi'): ('correction', 'खोजे गए गेम: {searched}; डाउनलोड क्लाइंट को भेजे गए रिलीज़: {grabbed}', 'The caller counts wanted games/releases, not sources or completed downloads.', 'moderate'),
    (360, 'de'): ('correction', 'Durchsucht: {searched}; an den Download-Client übergeben: {grabbed}', 'The caller reports an acquisition handed to the download client, not a completed download.', 'moderate'),
    (360, 'ja'): ('correction', '検索したゲーム数: {searched}、ダウンロードクライアントに渡したリリース数: {grabbed}', 'The caller counts wanted games and release handoffs; the current wording implies completed downloads.', 'moderate'),
    (360, 'fr'): ('correction', 'Jeux recherchés : {searched} ; éléments remis au client de téléchargement : {grabbed}', 'The caller reports wanted-game searches and handoffs, not completed downloads.', 'moderate'),
    (360, 'pt-BR'): ('correction', 'Jogos pesquisados: {searched}; itens enviados ao cliente de download: {grabbed}', 'The caller reports items handed to the download client, not completed downloads.', 'moderate'),
    (360, 'ar'): ('correction', 'عدد الألعاب التي جرى البحث عنها: {searched}، والعناصر المرسلة إلى عميل التنزيل: {grabbed}', 'The caller reports wanted-game counts and download-client handoffs, not completed downloads.', 'moderate'),
    (360, 'ko'): ('correction', '검색한 게임 {searched}개, 다운로드 클라이언트로 보낸 항목 {grabbed}개', 'The caller reports successful handoffs to the download client, not completed downloads.', 'moderate'),
    (360, 'vi'): ('correction', 'Đã tìm kiếm {searched} game; đã gửi {grabbed} bản phát hành cho trình tải xuống', 'The caller counts wanted games and reports release handoffs rather than completed downloads.', 'moderate'),
    (360, 'id'): ('correction', 'Game yang dicari: {searched}; rilis yang dikirim ke klien unduhan: {grabbed}', 'The caller counts wanted-game searches and handoffs, not sources or completed downloads.', 'moderate'),

    (361, 'hi'): ('refinement', 'गुप्त कुंजी: {secret}', 'This label displays a TOTP secret value; गुप्त कुंजी names the secret key more naturally.', 'moderate'),
    (361, 'ko'): ('refinement', '비밀: {secret}', 'Remove the nonstandard space before the colon in this label.', 'high'),

    (362, 'hi'): ('correction', 'ब्लॉक की गई वस्तुएँ देखें', 'Correct the Hindi gender agreement for blocked items.', 'high'),
    (362, 'vi'): ('correction', 'Xem các mục bị chặn', 'The current phrasing means blocking items rather than items that are blocked.', 'high'),

    (363, 'zh-Hans'): ('correction', '查看两者如何互通', 'The context is integration between two applications; the current pronoun sounds like people.', 'moderate'),
    (363, 'ja'): ('refinement', '両者の連携方法を見る', 'Make clear that the link describes how the two applications integrate.', 'moderate'),
    (363, 'ar'): ('refinement', 'تعرّف على كيفية تكامل التطبيقين', 'Name the two applications as the subject instead of an ambiguous pronoun.', 'moderate'),
    (363, 'ko'): ('correction', '두 서비스가 어떻게 연동되는지 확인', 'The current pronoun refers to people; this link describes how the two services integrate.', 'high'),
    (363, 'zh-Hant'): ('correction', '了解兩者如何互通', 'The context is integration between two applications; the current pronoun sounds like people.', 'moderate'),
    (363, 'vi'): ('correction', 'Xem cách hai ứng dụng tích hợp với nhau', 'The current pronoun refers to people; this link describes how the two applications integrate.', 'high'),
    (363, 'id'): ('correction', 'Lihat cara kedua aplikasi terintegrasi', 'Make the two applications explicit instead of using an ambiguous pronoun.', 'moderate'),
}

current = [json.loads(line) for line in (INPUT / 'current-target-cells.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
contexts = {d['position']: d for d in (json.loads(line) for line in (INPUT / 'source-contexts.jsonl').read_text(encoding='utf-8').splitlines() if line.strip())}
assert len(current) == 240
assert {(d['position'], d['locale']) for d in current} == {(pos, locale) for pos in range(345, 365) for locale in MANIFEST['locales']}
assert all(pos in range(345,365) and locale in MANIFEST['locales'] for pos,locale in DECISIONS)

ledger=[]
for cell in current:
    key=(cell['position'],cell['locale'])
    disposition,target,rationale,confidence=DECISIONS.get(key,('accept-current',cell['currentTarget'],'Current wording preserves the source meaning in the pinned UI context.', 'moderate'))
    assert target.count('{') == target.count('}')
    if cell['position'] in (346,359,360,361):
        required={'346':['{error_type}'],'359':['{searched}','{grabbed}','{skipped}'],'360':['{searched}','{grabbed}'],'361':['{secret}']}[str(cell['position'])]
        assert sorted(token for token in required if token in target)==sorted(required), (key,target)
    row={
        'schemaVersion':1,
        'repository':MANIFEST['repository'],
        'pullRequest':MANIFEST['pullRequest'],
        'head':HEAD,
        'tree':TREE,
        'window':'W345-W364',
        'position':cell['position'],
        'sourceId':cell['sourceId'],
        'source':cell['source'],
        'sourceSha256':cell['sourceSha256'],
        'locale':cell['locale'],
        'callerContextSha256':cell['callerContextSha256'],
        'productionCallerCount':contexts[cell['position']]['productionCallerCount'],
        'currentTarget':cell['currentTarget'],
        'currentTargetSha256':cell['currentTargetSha256'],
        'blindTarget':target,
        'blindTargetSha256':sha(target),
        'disposition':disposition,
        'confidence':confidence,
        'rationale':rationale,
    }
    ledger.append(row)
assert len(ledger)==240
assert len({(r['position'],r['locale']) for r in ledger})==240
assert sum(r['disposition']=='accept-current' for r in ledger)+sum(r['disposition'] in ('correction','refinement','hold') for r in ledger)==240

with (OUT/'blind-ledger.jsonl').open('w',encoding='utf-8',newline='\n') as f:
    for row in ledger: f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
counts=Counter(r['disposition'] for r in ledger)
by_locale=defaultdict(Counter)
for row in ledger: by_locale[row['locale']][row['disposition']]+=1
changed=[r for r in ledger if r['disposition'] in ('correction','refinement')]
summary={
    'status':'sealed-blind-review',
    'repository':MANIFEST['repository'],'pullRequest':MANIFEST['pullRequest'],'head':HEAD,'tree':TREE,
    'window':'W345-W364','sourceCount':20,'localeCount':12,'cellCount':len(ledger),
    'candidateFreeManifestSha256':hashlib.sha256((INPUT/'manifest.json').read_bytes()).hexdigest(),
    'candidateFreeChecksumsSha256':hashlib.sha256((INPUT/'SHA256SUMS.txt').read_bytes()).hexdigest(),
    'dispositions':dict(counts),
    'changedCellCount':len(changed),
    'changedSourceCount':len({r['position'] for r in changed}),
    'byLocale':{k:dict(v) for k,v in sorted(by_locale.items())},
    'callerlessCellsInWindow':0,
    'priorCallerlessHoldCellsReattested':MANIFEST['priorHoldCellCount'],
    'priorCallerlessHoldHashesPreserved':MANIFEST['priorHoldTargetsUnchanged'],
    'placeholderMismatches':MANIFEST['currentTargetPlaceholderMismatches'],
    'numericMismatches':MANIFEST['currentTargetNumericMismatches'],
    'protectedLiteralMismatches':MANIFEST['currentTargetProtectedLiteralMismatches'],
    'runtimeFollowups':MANIFEST['renderingFollowups'],
    'nativeSpeakerApproval':False,
    'headedBrowserReviewed':False,
    'repositoryOrPullRequestChanged':False,
    'testsBuildsScansCI':False,
    'mergeReleaseTag':False,
    'interpretation':'Blind translation decisions only; apply nothing until independent cross-review and exact-head readback.',
}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme=(
    '# ROMarrNG PR #70 W345-W364 blind review\n\n'
    f'Pinned to candidate-free input at head `{HEAD}` / tree `{TREE}`. The reviewer used only the candidate-free packet at `{INPUT}` and did not inspect primary proposals for this window.\n\n'
    'The ledger contains all 240 target cells, with exact source, caller-context, current-target, and proposed-target hashes. Dispositions are accept-current, correction, or refinement. No callerless hold occurs in this window. All 288 prior callerless hold cells were reattested in the candidate-free packet and remain outside this window; none were altered.\n\n'
    'Runtime follow-ups at ranks 346 and 350 remain: the launcher failure and TOTP enrollment note currently pass through opaque API-message rendering. The catalog review does not fix that code path.\n\n'
    'This is machine semantic review, not native-speaker signoff or headed-browser acceptance. No repository/PR changes, tests, builds, scans, CI, merge, release, or tag actions occurred.\n\n'
    'Files: `blind-ledger.jsonl` contains per-cell decisions; `summary.json` records counts and pins; `build_blind_ledger.py` regenerates the ledger from the pinned candidate-free packet.\n'
)
(OUT/'README.md').write_text(readme,encoding='utf-8')
checks=['README.md','blind-ledger.jsonl','summary.json','build_blind_ledger.py']
with (OUT/'SHA256SUMS.txt').open('w',encoding='utf-8',newline='\n') as f:
    for name in checks:
        f.write(f"{hashlib.sha256((OUT/name).read_bytes()).hexdigest()}  {name}\n")
print(json.dumps({'summary':summary,'output':str(OUT)},ensure_ascii=False,indent=2))
