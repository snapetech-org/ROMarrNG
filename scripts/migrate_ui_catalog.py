#!/usr/bin/env python3
"""Migrate ROMarr's English-keyed UI translations to stable catalog IDs.

The migration is lossless. Existing locale values are retained verbatim and
new IDs are assigned once; rerunning the tool preserves IDs and review records.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "romarr" / "ui-labels.json"
SNAPSHOT = ROOT / "romarr" / "ui-source-snapshot.json"

LOCALE_ROWS = [
    ("en", "English", "English", "ltr", "available"),
    ("ar", "Arabic", "العربية", "rtl", "available"),
    ("az", "Azerbaijani", "Azərbaycanca", "ltr", "planned"),
    ("bg", "Bulgarian", "Български", "ltr", "planned"),
    ("bn", "Bengali", "বাংলা", "ltr", "planned"),
    ("cs", "Czech", "Čeština", "ltr", "planned"),
    ("da", "Danish", "Dansk", "ltr", "planned"),
    ("de", "German", "Deutsch", "ltr", "available"),
    ("es", "Spanish", "Español", "ltr", "available"),
    ("es-419", "Latin American Spanish", "Español (Latinoamérica)", "ltr", "inherited"),
    ("fa", "Persian", "فارسی", "rtl", "planned"),
    ("fr", "French", "Français", "ltr", "available"),
    ("fr-CA", "Canadian French", "Français canadien", "ltr", "inherited"),
    ("he", "Hebrew", "עברית", "rtl", "planned"),
    ("hi", "Hindi", "हिन्दी", "ltr", "available"),
    ("hu", "Hungarian", "Magyar", "ltr", "planned"),
    ("id", "Indonesian", "Bahasa Indonesia", "ltr", "available"),
    ("it", "Italian", "Italiano", "ltr", "planned"),
    ("ja", "Japanese", "日本語", "ltr", "available"),
    ("kk", "Kazakh", "Қазақша", "ltr", "planned"),
    ("ko", "Korean", "한국어", "ltr", "available"),
    ("ms", "Malay", "Bahasa Melayu", "ltr", "planned"),
    ("nb", "Norwegian Bokmål", "Norsk bokmål", "ltr", "planned"),
    ("nl", "Dutch", "Nederlands", "ltr", "planned"),
    ("pl", "Polish", "Polski", "ltr", "planned"),
    ("pt", "Portuguese", "Português", "ltr", "planned"),
    ("pt-BR", "Brazilian Portuguese", "Português (Brasil)", "ltr", "available"),
    ("pt-PT", "European Portuguese", "Português (Portugal)", "ltr", "planned"),
    ("ru", "Russian", "Русский", "ltr", "planned"),
    ("sv", "Swedish", "Svenska", "ltr", "planned"),
    ("th", "Thai", "ไทย", "ltr", "planned"),
    ("tr", "Turkish", "Türkçe", "ltr", "planned"),
    ("uk", "Ukrainian", "Українська", "ltr", "planned"),
    ("uz", "Uzbek", "Oʻzbekcha", "ltr", "planned"),
    ("vi", "Vietnamese", "Tiếng Việt", "ltr", "available"),
    ("zh-Hans", "Simplified Chinese", "简体中文", "ltr", "available"),
    ("zh-Hant", "Traditional Chinese", "繁體中文", "ltr", "available"),
]

REGIONAL_PARENTS = {
    "es-419": "es",
    "fr-CA": "fr",
}

ALIASES = {
    "zh": "zh-Hans",
    "zh-CN": "zh-Hans",
    "zh-SG": "zh-Hans",
    "zh-TW": "zh-Hant",
    "zh-HK": "zh-Hant",
    "zh-MO": "zh-Hant",
    "pt": "pt-BR",
    "pt-PT": "pt-BR",
    "es-AR": "es-419",
    "es-BO": "es-419",
    "es-CL": "es-419",
    "es-CO": "es-419",
    "es-CR": "es-419",
    "es-CU": "es-419",
    "es-DO": "es-419",
    "es-EC": "es-419",
    "es-GT": "es-419",
    "es-HN": "es-419",
    "es-MX": "es-419",
    "es-NI": "es-419",
    "es-PA": "es-419",
    "es-PE": "es-419",
    "es-PR": "es-419",
    "es-PY": "es-419",
    "es-SV": "es-419",
    "es-UY": "es-419",
    "es-VE": "es-419",
}

NEW_TRANSLATIONS = {
    "Use browser settings": {
        "es": "Usar la configuración del navegador",
        "zh-Hans": "使用浏览器设置",
        "hi": "ब्राउज़र सेटिंग का उपयोग करें",
        "de": "Browsereinstellungen verwenden",
        "ja": "ブラウザー設定を使用",
        "fr": "Utiliser les paramètres du navigateur",
        "pt-BR": "Usar as configurações do navegador",
        "ar": "استخدام إعدادات المتصفح",
        "ko": "브라우저 설정 사용",
        "zh-Hant": "使用瀏覽器設定",
        "vi": "Dùng cài đặt trình duyệt",
        "id": "Gunakan pengaturan browser",
    },
    "Warm sepia theme": {
        "es": "Tema sepia cálido", "zh-Hans": "暖棕褐色主题",
        "hi": "गर्म सेपिया थीम", "de": "Warmes Sepia-Design",
        "ja": "暖かいセピアテーマ", "fr": "Thème sépia chaud",
        "pt-BR": "Tema sépia quente", "ar": "سمة سيبيا دافئة",
        "ko": "따뜻한 세피아 테마", "zh-Hant": "暖褐色主題",
        "vi": "Chủ đề nâu sepia ấm", "id": "Tema sepia hangat",
    },
    "Sort by": {
        "es": "Ordenar por", "zh-Hans": "排序方式", "hi": "क्रमबद्ध करें",
        "de": "Sortieren nach", "ja": "並べ替え", "fr": "Trier par",
        "pt-BR": "Ordenar por", "ar": "ترتيب حسب", "ko": "정렬 기준",
        "zh-Hant": "排序方式", "vi": "Sắp xếp theo", "id": "Urutkan berdasarkan",
    },
    "Skip to content": {
        "es": "Saltar al contenido", "zh-Hans": "跳到内容", "hi": "मुख्य सामग्री पर जाएँ",
        "de": "Zum Inhalt springen", "ja": "コンテンツへ移動", "fr": "Aller au contenu",
        "pt-BR": "Pular para o conteúdo", "ar": "انتقل إلى المحتوى", "ko": "본문으로 건너뛰기",
        "zh-Hant": "跳至內容", "vi": "Chuyển đến nội dung", "id": "Lewati ke konten",
    },
    "Close navigation": {
        "es": "Cerrar navegación", "zh-Hans": "关闭导航", "hi": "नेविगेशन बंद करें",
        "de": "Navigation schließen", "ja": "ナビゲーションを閉じる", "fr": "Fermer la navigation",
        "pt-BR": "Fechar navegação", "ar": "إغلاق التنقل", "ko": "탐색 닫기",
        "zh-Hant": "關閉導覽", "vi": "Đóng điều hướng", "id": "Tutup navigasi",
    },
    "Open navigation": {
        "es": "Abrir navegación", "zh-Hans": "打开导航", "hi": "नेविगेशन खोलें",
        "de": "Navigation öffnen", "ja": "ナビゲーションを開く", "fr": "Ouvrir la navigation",
        "pt-BR": "Abrir navegação", "ar": "فتح التنقل", "ko": "탐색 열기",
        "zh-Hant": "開啟導覽", "vi": "Mở điều hướng", "id": "Buka navigasi",
    },
    "Menu": {
        "es": "Menú", "zh-Hans": "菜单", "hi": "मेनू", "de": "Menü",
        "ja": "メニュー", "fr": "Menu", "pt-BR": "Menu", "ar": "القائمة",
        "ko": "메뉴", "zh-Hant": "選單", "vi": "Menu", "id": "Menu",
    },
    "Close": {
        "es": "Cerrar", "zh-Hans": "关闭", "hi": "बंद करें", "de": "Schließen",
        "ja": "閉じる", "fr": "Fermer", "pt-BR": "Fechar", "ar": "إغلاق",
        "ko": "닫기", "zh-Hant": "關閉", "vi": "Đóng", "id": "Tutup",
    },
    "Filter games": {
        "es": "Filtrar juegos", "zh-Hans": "筛选游戏", "hi": "गेम फ़िल्टर करें",
        "de": "Spiele filtern", "ja": "ゲームを絞り込む", "fr": "Filtrer les jeux",
        "pt-BR": "Filtrar jogos", "ar": "تصفية الألعاب", "ko": "게임 필터",
        "zh-Hant": "篩選遊戲", "vi": "Lọc trò chơi", "id": "Filter game",
    },
    "Apply {count} safe file renames?": {
        "es": "¿Aplicar {count} cambios de nombre seguros?",
        "zh-Hans": "要应用 {count} 个安全的文件重命名吗？",
        "hi": "क्या {count} सुरक्षित फ़ाइल नाम परिवर्तन लागू करें?",
        "de": "{count} sichere Dateiumbenennungen anwenden?",
        "ja": "安全なファイル名変更を {count} 件適用しますか？",
        "fr": "Appliquer {count} renommages de fichiers sans risque ?",
        "pt-BR": "Aplicar {count} renomeações seguras de arquivos?",
        "ar": "هل تريد تطبيق {count} عملية إعادة تسمية آمنة للملفات؟",
        "ko": "안전한 파일 이름 변경 {count}개를 적용할까요?",
        "zh-Hant": "要套用 {count} 個安全的檔案重新命名嗎？",
        "vi": "Áp dụng {count} thay đổi tên tệp an toàn?",
        "id": "Terapkan {count} penggantian nama file yang aman?",
    },
    "Canonical game title": {
        "es": "Título canónico del juego", "zh-Hans": "游戏标准名称",
        "hi": "गेम का मानक शीर्षक", "de": "Kanonischer Spieltitel",
        "ja": "ゲームの正式タイトル", "fr": "Titre canonique du jeu",
        "pt-BR": "Título canônico do jogo", "ar": "العنوان المعتمد للعبة",
        "ko": "게임 표준 제목", "zh-Hant": "遊戲標準名稱",
        "vi": "Tên chuẩn của trò chơi", "id": "Judul game kanonis",
    },
    "Choose a platform for {game}. Available: {platforms}": {
        "es": "Elige una plataforma para {game}. Disponibles: {platforms}",
        "zh-Hans": "为 {game} 选择平台。可选平台：{platforms}",
        "hi": "{game} के लिए प्लेटफ़ॉर्म चुनें। उपलब्ध: {platforms}",
        "de": "Wähle eine Plattform für {game}. Verfügbar: {platforms}",
        "ja": "{game} のプラットフォームを選択してください。利用可能: {platforms}",
        "fr": "Choisissez une plateforme pour {game}. Disponibles : {platforms}",
        "pt-BR": "Escolha uma plataforma para {game}. Disponíveis: {platforms}",
        "ar": "اختر منصة للعبة {game}. المنصات المتاحة: {platforms}",
        "ko": "{game}의 플랫폼을 선택하세요. 사용 가능: {platforms}",
        "zh-Hant": "為 {game} 選擇平台。可用平台：{platforms}",
        "vi": "Chọn nền tảng cho {game}. Khả dụng: {platforms}",
        "id": "Pilih platform untuk {game}. Tersedia: {platforms}",
    },
    "ES-DE ↗": {code: "ES-DE ↗" for code in (
        "es", "zh-Hans", "hi", "de", "ja", "fr", "pt-BR", "ar",
        "ko", "zh-Hant", "vi", "id")},
    "EmuDeck setup guide ↗": {
        "es": "Guía de configuración de EmuDeck ↗", "zh-Hans": "EmuDeck 设置指南 ↗",
        "hi": "EmuDeck सेटअप गाइड ↗", "de": "EmuDeck-Einrichtungsanleitung ↗",
        "ja": "EmuDeck セットアップガイド ↗", "fr": "Guide de configuration EmuDeck ↗",
        "pt-BR": "Guia de configuração do EmuDeck ↗", "ar": "دليل إعداد EmuDeck ↗",
        "ko": "EmuDeck 설정 가이드 ↗", "zh-Hant": "EmuDeck 設定指南 ↗",
        "vi": "Hướng dẫn thiết lập EmuDeck ↗", "id": "Panduan penyiapan EmuDeck ↗",
    },
    "For an EmuDeck-style layout, set the ROM library root to the shared": {
        "es": "Para una estructura como EmuDeck, configura la raíz de la biblioteca de ROM en la carpeta compartida",
        "zh-Hans": "对于 EmuDeck 风格的目录结构，将 ROM 库根目录设为共享文件夹",
        "hi": "EmuDeck जैसी संरचना के लिए, ROM लाइब्रेरी रूट को साझा फ़ोल्डर पर सेट करें",
        "de": "Bei einer EmuDeck-ähnlichen Struktur legst du das ROM-Bibliotheksverzeichnis auf den gemeinsamen Ordner",
        "ja": "EmuDeck のような構成では、ROM ライブラリのルートを共有フォルダーに設定します",
        "fr": "Pour une arborescence de type EmuDeck, définissez la racine de la bibliothèque ROM sur le dossier partagé",
        "pt-BR": "Em uma estrutura como a do EmuDeck, defina a raiz da biblioteca de ROMs como a pasta compartilhada",
        "ar": "في بنية تشبه EmuDeck، اجعل مجلد مكتبة ROM هو المجلد المشترك",
        "ko": "EmuDeck 방식의 구조에서는 ROM 라이브러리 루트를 공유 폴더로 설정하세요",
        "zh-Hant": "對於 EmuDeck 風格的目錄結構，請將 ROM 媒體庫根目錄設為共用資料夾",
        "vi": "Với cấu trúc kiểu EmuDeck, hãy đặt thư mục gốc thư viện ROM thành thư mục dùng chung",
        "id": "Untuk susunan seperti EmuDeck, atur akar pustaka ROM ke folder bersama",
    },
    "Identify & Organize": {
        "es": "Identificar y organizar", "zh-Hans": "识别与整理",
        "hi": "पहचानें और व्यवस्थित करें", "de": "Identifizieren & organisieren",
        "ja": "識別と整理", "fr": "Identifier et organiser",
        "pt-BR": "Identificar e organizar", "ar": "التعرّف والتنظيم",
        "ko": "식별 및 정리", "zh-Hant": "識別與整理",
        "vi": "Nhận diện và sắp xếp", "id": "Identifikasi & atur",
    },
    "More player options": {
        "es": "Más opciones para jugar", "zh-Hans": "更多游玩方式",
        "hi": "खेलने के और विकल्प", "de": "Weitere Spieloptionen",
        "ja": "ほかのプレイ方法", "fr": "Plus d’options pour jouer",
        "pt-BR": "Mais opções para jogar", "ar": "المزيد من خيارات اللعب",
        "ko": "더 많은 플레이 옵션", "zh-Hant": "更多遊玩方式",
        "vi": "Thêm lựa chọn để chơi", "id": "Opsi bermain lainnya",
    },
    "Request up to 5 titles at a time": {
        "es": "Solicita hasta 5 títulos a la vez", "zh-Hans": "每次最多请求 5 个游戏",
        "hi": "एक बार में अधिकतम 5 शीर्षकों का अनुरोध करें",
        "de": "Fordere höchstens 5 Titel auf einmal an",
        "ja": "一度にリクエストできるのは最大 5 件です",
        "fr": "Demandez jusqu’à 5 titres à la fois",
        "pt-BR": "Solicite até 5 títulos por vez", "ar": "اطلب حتى 5 عناوين في كل مرة",
        "ko": "한 번에 최대 5개 항목까지 요청할 수 있습니다",
        "zh-Hant": "每次最多可要求 5 個遊戲",
        "vi": "Yêu cầu tối đa 5 tựa game mỗi lần",
        "id": "Minta maksimal 5 judul sekaligus",
    },
    "Search and request {count} selected titles now?": {
        "es": "¿Buscar y solicitar ahora los {count} títulos seleccionados?",
        "zh-Hans": "现在搜索并请求所选的 {count} 个游戏吗？",
        "hi": "क्या अभी चुने गए {count} शीर्षकों को खोजकर अनुरोध करें?",
        "de": "Die {count} ausgewählten Titel jetzt suchen und anfordern?",
        "ja": "選択した {count} 件を今すぐ検索してリクエストしますか？",
        "fr": "Rechercher et demander maintenant les {count} titres sélectionnés ?",
        "pt-BR": "Pesquisar e solicitar agora os {count} títulos selecionados?",
        "ar": "هل تريد البحث عن {count} من العناوين المحددة وطلبها الآن؟",
        "ko": "선택한 {count}개 항목을 지금 검색하고 요청할까요?",
        "zh-Hant": "現在搜尋並要求所選的 {count} 個遊戲嗎？",
        "vi": "Tìm và yêu cầu {count} tựa game đã chọn ngay bây giờ?",
        "id": "Cari dan minta {count} judul yang dipilih sekarang?",
    },
    "Select at least one": {
        "es": "Selecciona al menos uno", "zh-Hans": "请至少选择一项",
        "hi": "कम से कम एक चुनें", "de": "Wähle mindestens einen Eintrag aus",
        "ja": "少なくとも 1 件選択してください", "fr": "Sélectionnez-en au moins un",
        "pt-BR": "Selecione pelo menos um", "ar": "اختر عنصرًا واحدًا على الأقل",
        "ko": "하나 이상 선택하세요", "zh-Hant": "請至少選取一項",
        "vi": "Chọn ít nhất một mục", "id": "Pilih setidaknya satu",
    },
    "Set up a play device": {
        "es": "Configura un dispositivo para jugar", "zh-Hans": "设置游戏设备",
        "hi": "खेलने के लिए डिवाइस सेट अप करें", "de": "Ein Spielgerät einrichten",
        "ja": "ゲーム用デバイスを設定", "fr": "Configurer un appareil de jeu",
        "pt-BR": "Configure um dispositivo para jogar", "ar": "إعداد جهاز للعب",
        "ko": "플레이 기기 설정", "zh-Hant": "設定遊戲裝置",
        "vi": "Thiết lập thiết bị chơi game", "id": "Siapkan perangkat untuk bermain",
    },
    "Undo the last ROMarr rename batch? Files changed since then will be left alone.": {
        "es": "¿Deshacer el último lote de cambios de nombre de ROMarr? Los archivos modificados desde entonces se dejarán intactos.",
        "zh-Hans": "要撤销 ROMarr 上次的重命名批次吗？之后发生变化的文件会保持不动。",
        "hi": "क्या ROMarr के फ़ाइल नाम बदलने के पिछले बैच को पूर्ववत करें? उसके बाद बदली फ़ाइलें नहीं छुई जाएँगी।",
        "de": "Letzten ROMarr-Umbenennungslauf rückgängig machen? Seitdem geänderte Dateien bleiben unangetastet.",
        "ja": "ROMarr の最後の一括リネームを元に戻しますか？その後に変更されたファイルには触れません。",
        "fr": "Annuler le dernier lot de renommage ROMarr ? Les fichiers modifiés depuis resteront intacts.",
        "pt-BR": "Desfazer o último lote de renomeação do ROMarr? Arquivos alterados desde então não serão modificados.",
        "ar": "هل تريد التراجع عن آخر دفعة إعادة تسمية في ROMarr؟ ستُترك الملفات التي تغيرت منذ ذلك الحين دون تعديل.",
        "ko": "ROMarr의 마지막 파일 이름 변경 작업을 되돌릴까요? 그 후 변경된 파일은 그대로 둡니다.",
        "zh-Hant": "要復原 ROMarr 上次的重新命名批次嗎？之後變更過的檔案會保持原樣。",
        "vi": "Hoàn tác đợt đổi tên gần nhất của ROMarr? Tệp đã thay đổi kể từ đó sẽ được giữ nguyên.",
        "id": "Batalkan batch penggantian nama terakhir ROMarr? File yang berubah sejak itu akan dibiarkan.",
    },
    "beside it. Add a platform folder mapping in Media Management if your existing folder names differ. Set up the frontend and emulator on each device that will play the games.": {
        "es": "junto a ella. Añade una asignación de carpetas de plataforma en Gestión de medios si tus nombres actuales son distintos. Configura el frontend y el emulador en cada dispositivo donde jugarás.",
        "zh-Hans": "并放在它旁边。如果现有文件夹名称不同，请在媒体管理中添加平台文件夹映射。为每台要运行游戏的设备安装前端和模拟器。",
        "hi": "इसके पास रखें। मौजूदा फ़ोल्डर नाम अलग हों तो Media Management में प्लेटफ़ॉर्म फ़ोल्डर मैपिंग जोड़ें। हर खेलने वाले डिवाइस पर फ्रंटएंड और एमुलेटर सेट अप करें।",
        "de": "daneben. Wenn deine Ordner anders heißen, füge unter Medienverwaltung eine Plattformordner-Zuordnung hinzu. Richte Frontend und Emulator auf jedem Spielgerät ein.",
        "ja": "その隣に置きます。既存のフォルダー名が異なる場合は、メディア管理でプラットフォームフォルダーの対応付けを追加してください。ゲームを遊ぶ各デバイスにフロントエンドとエミュレーターを設定します。",
        "fr": "à côté. Si les noms de dossiers existants diffèrent, ajoutez une correspondance de dossiers de plateforme dans Gestion des médias. Configurez le frontend et l’émulateur sur chaque appareil de jeu.",
        "pt-BR": "ao lado. Se os nomes das pastas existentes forem diferentes, adicione um mapeamento de pasta de plataforma em Gerenciamento de mídia. Configure o frontend e o emulador em cada dispositivo usado para jogar.",
        "ar": "بجوارها. أضف تعيينًا لمجلدات المنصات في إدارة الوسائط إذا اختلفت أسماء مجلداتك الحالية. أعد إعداد الواجهة الأمامية والمحاكي على كل جهاز ستلعب عليه.",
        "ko": "그 옆에 둡니다. 기존 폴더 이름이 다르면 미디어 관리에서 플랫폼 폴더 매핑을 추가하세요. 게임을 실행할 각 기기에 프런트엔드와 에뮬레이터를 설정합니다.",
        "zh-Hant": "並放在它旁邊。如果現有資料夾名稱不同，請在媒體管理中新增平台資料夾對應。為每台要遊玩遊戲的裝置設定前端與模擬器。",
        "vi": "ở bên cạnh. Nếu tên thư mục hiện có khác, hãy thêm ánh xạ thư mục nền tảng trong Quản lý phương tiện. Thiết lập giao diện và trình giả lập trên từng thiết bị chơi game.",
        "id": "di sebelahnya. Tambahkan pemetaan folder platform di Manajemen Media jika nama folder yang ada berbeda. Siapkan frontend dan emulator di setiap perangkat untuk bermain.",
    },
    "folder and keep": {
        "es": "y conserva", "zh-Hans": "并保留", "hi": "और रखें",
        "de": "und behalte", "ja": "にして、次を保管します",
        "fr": "et conservez", "pt-BR": "e mantenha", "ar": "واحتفظ بـ",
        "ko": "로 설정하고 다음 항목을 보관합니다", "zh-Hant": "並保留",
        "vi": "và giữ", "id": "dan simpan",
    },
    "to build a shared inventory from an existing library, or": {
        "es": "para crear un inventario compartido a partir de una biblioteca existente, o",
        "zh-Hans": "，以便从现有库建立共享清单，或",
        "hi": "किसी मौजूदा लाइब्रेरी से साझा सूची बनाने के लिए, या",
        "de": "um aus einer vorhandenen Bibliothek einen gemeinsamen Bestand aufzubauen, oder",
        "ja": "既存ライブラリから共有インベントリを作成するか、",
        "fr": "pour créer un inventaire partagé à partir d’une bibliothèque existante, ou",
        "pt-BR": "para criar um inventário compartilhado a partir de uma biblioteca existente, ou",
        "ar": "لإنشاء قائمة مشتركة من مكتبة موجودة، أو",
        "ko": "기존 라이브러리에서 공유 목록을 만들거나",
        "zh-Hant": "，以便從現有媒體庫建立共用清單，或",
        "vi": "để tạo danh mục dùng chung từ thư viện hiện có, hoặc",
        "id": "untuk membuat inventaris bersama dari pustaka yang sudah ada, atau",
    },
}


def source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def translation_hash(value: object) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def stable_id(source: str) -> str:
    ascii_source = unicodedata.normalize("NFKD", source).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_source.lower()).strip("-")[:36].rstrip("-")
    return f"ui.{slug or 'message'}.{source_hash(source)[:10]}"


def load_legacy() -> tuple[
    dict[str, dict[str, object]], dict[str, str], dict[str, dict[str, object]]
]:
    raw = json.loads(CATALOG.read_text(encoding="utf-8"))
    if raw.get("schemaVersion") in {2, 3}:
        messages = raw["messages"]
        return (
            {message["source"]: message["translations"]
             for message in messages.values()},
            {message["source"]: key for key, message in messages.items()},
            {message["source"]: {
                "sourceHash": message.get("sourceHash"),
                "translationHashes": message.get("translationHashes", {}),
                "translationStatus": message.get("translationStatus", {}),
                "translationReview": message.get("translationReview", {}),
            } for message in messages.values()},
        )
    return raw, {}, {}


def main() -> int:
    if not CATALOG.exists():
        print("romarr/ui-labels.json is missing", file=sys.stderr)
        return 2
    translations, previous_ids, previous_metadata = load_legacy()
    for source, values in NEW_TRANSLATIONS.items():
        translations.setdefault(source, values)

    messages: dict[str, dict[str, object]] = {}
    for source in sorted(translations):
        key = previous_ids.get(source, stable_id(source))
        if key in messages:
            print(f"stable ID collision: {key}", file=sys.stderr)
            return 2
        previous = previous_metadata.get(source, {})
        old_hashes = previous.get("translationHashes", {})
        old_status = previous.get("translationStatus", {})
        old_review = previous.get("translationReview", {})
        source_unchanged = previous.get("sourceHash") == source_hash(source)
        statuses: dict[str, str] = {}
        review_evidence: dict[str, dict[str, str]] = {}
        for locale, value in translations[source].items():
            if locale == "en":
                continue
            unchanged = (
                source_unchanged and isinstance(old_hashes, dict)
                and old_hashes.get(locale) == translation_hash(value)
            )
            prior_status = old_status.get(locale) if isinstance(old_status, dict) else None
            if not unchanged or prior_status not in {"draft", "reviewed"}:
                continue
            evidence = old_review.get(locale) if isinstance(old_review, dict) else None
            if prior_status == "reviewed" and isinstance(evidence, dict) \
                    and evidence.get("reviewer") and evidence.get("reviewedAt"):
                review_evidence[locale] = evidence
            elif prior_status == "reviewed":
                continue
            statuses[locale] = prior_status
        messages[key] = {
            "source": source,
            "sourceHash": source_hash(source),
            "translations": translations[source],
            "translationHashes": {},
            "translationStatus": statuses,
            "translationReview": review_evidence,
        }

    singular = "Connected to {friend}: {count} title with hashes ROMarr can match on."
    plural = "Connected to {friend}: {count} titles with hashes ROMarr can match on."
    singular_values = messages.get(previous_ids.get(singular, stable_id(singular)), {}).get("translations", {})
    if (singular in translations and plural in translations
            and not (isinstance(singular_values.get("en"), dict)
                     and singular_values["en"].get("kind") == "plural")):
        key = previous_ids.get(singular, stable_id(singular))
        forms_by_locale = {
            "en": {
                "=0": "Connected to {friend}: ROMarr found no titles with hashes it can match.",
                "one": "Connected to {friend}: ROMarr can match {count} title with hashes.",
                "other": "Connected to {friend}: ROMarr can match {count} titles with hashes.",
            }
        }
        for locale in translations[singular]:
            singular_text = translations[singular][locale]
            plural_text = translations[plural][locale]
            forms_by_locale[locale] = {
                "=0": plural_text,
                "one": singular_text,
                "other": plural_text,
            }
        messages[key]["translations"]["en"] = {
            "kind": "plural", "argument": "count", "forms": forms_by_locale.pop("en")
        }
        for locale, forms in forms_by_locale.items():
            messages[key]["translations"][locale] = {
                "kind": "plural", "argument": "count", "forms": forms
            }

    for message in messages.values():
        message["translationHashes"] = {
            locale: translation_hash(value)
            for locale, value in message["translations"].items()
            if locale in message["translationStatus"]
        }

    locales = {
        tag: {
            "englishName": english,
            "nativeName": native,
            "direction": direction,
            "status": status,
            "translationReview": (
                "source" if tag == "en" else
                "inherited" if status == "inherited" else
                "unverified" if status == "available" else "not started"
            ),
        }
        for tag, english, native, direction, status in LOCALE_ROWS
    }
    available = [tag for tag, _, _, _, status in LOCALE_ROWS
                 if status in {"available", "inherited"}]
    catalog = {
        "schemaVersion": 3,
        "baseLocale": "en",
        "locales": locales,
        "availableLocales": available,
        "regionalParents": REGIONAL_PARENTS,
        "aliases": ALIASES,
        "rtlLocales": ["ar", "fa", "he"],
        "messages": messages,
    }
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    snapshot = {key: message["sourceHash"] for key, message in messages.items()}
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"Wrote {len(messages)} stable messages; {len(available)} selectable locales; "
          f"{len(locales) - len(available)} locales awaiting translation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
