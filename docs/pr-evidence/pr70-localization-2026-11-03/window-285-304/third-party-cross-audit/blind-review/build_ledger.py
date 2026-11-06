#!/usr/bin/env python3
"""Build the W285-W304 independent review ledger from candidate-free packet data only."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

INPUT = Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w285-304-candidate-free-20261103/input')
OUT = Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w285-304-independent-blind-20261103/review-v2')
PACKET_SHA256 = '1047511955ef60dc180a49bdaef7a86452c70e9196fd681174732e98d408f338'

# Only independently drafted correction targets are listed here. Unlisted cells
# retain their packet current value after semantic/context review.
REVISIONS = {
  (285, 'ar'): 'نُشر {entries} من مدخلات ES-DE و{covers} من الأغلفة المشتركة.',
  (285, 'de'): 'Es wurden {entries} ES-DE-Einträge und {covers} gemeinsam genutzte Cover veröffentlicht.',
  (285, 'es'): 'Se publicaron {entries} entradas de ES-DE y {covers} portadas compartidas.',
  (285, 'fr'): '{entries} entrées ES-DE et {covers} couvertures partagées ont été publiées.',
  (285, 'hi'): 'ES-DE की {entries} प्रविष्टियाँ और {covers} साझा कवर प्रकाशित किए गए।',
  (285, 'id'): '{entries} entri ES-DE dan {covers} sampul bersama berhasil diterbitkan.',
  (285, 'ja'): 'ES-DE のエントリーを {entries} 件、共有カバーを {covers} 件公開しました。',
  (285, 'ko'): 'ES-DE 항목 {entries}개와 공유 커버 {covers}개를 게시했습니다.',

  (287, 'ar'): 'قراءة تجزئات ROM من المكتبة لاستخدامها في Netplay',
  (287, 'de'): 'ROM-Hashes aus der Bibliothek für Netplay lesen',
  (287, 'es'): 'Leer los hashes de ROM de la biblioteca para Netplay',
  (287, 'fr'): 'Lire les hachages de ROM de la bibliothèque pour Netplay',
  (287, 'hi'): 'Netplay के लिए लाइब्रेरी से ROM हैश पढ़ें',
  (287, 'id'): 'Baca hash ROM dari perpustakaan untuk Netplay',
  (287, 'ja'): 'Netplay 用にライブラリから ROM のハッシュを読み込む',
  (287, 'ko'): 'Netplay를 위해 라이브러리에서 ROM 해시 읽기',
  (287, 'pt-BR'): 'Ler os hashes das ROMs da biblioteca para Netplay',
  (287, 'vi'): 'Đọc mã băm ROM từ thư viện cho Netplay',
  (287, 'zh-Hans'): '从媒体库读取 ROM 哈希值以用于 Netplay',
  (287, 'zh-Hant'): '從媒體庫讀取 ROM 雜湊值以供 Netplay 使用',

  (288, 'ar'): 'قُرئت {seen} إدخالات، وعُثر على تجزئة لدى {added} منها. يستطيع Netplay مطابقة هذه الإدخالات. أما {without} المتبقية فهي إدخالات مدرجة في الفهرس لم تفحصها مكتبتك من قرص قط، لذا لا توجد بيانات لمطابقتها. وكانت {confirmed} منها مطابقةً لملفات No-Intro أو Redump، ووُسِمت بأنها موثّقة.',
  (288, 'ja'): 'ライブラリから {seen} 件のエントリーを読み込み、そのうち {added} 件でハッシュが見つかりました。Netplay でこれらを照合できます。残りの {without} 件はカタログに登録されていますが、ライブラリではそれらをディスクから一度も読み取っておらず、照合するデータがありません。{confirmed} 件は No-Intro または Redump のダンプと一致し、検証済みとしてマークされています。',
  (289, 'ja'): '{seen} 件のエントリーを読み込み、そのうち {added} 件でハッシュが見つかりました。Netplay でこれらを照合できます。残りの {without} 件はカタログに登録されていますが、ライブラリではそれらをディスクから一度も読み取っておらず、照合するデータがありません。DAT と一致したものはなく、すべて未検証です。「設定」で DAT ディレクトリを確認してください。',

  (291, 'ar'): 'تُقرأ مكتبتك في الخلفية. لا يلزم إبقاء هذه الصفحة مفتوحة.',
  (291, 'fr'): 'Lecture de votre bibliothèque en arrière-plan. Vous n’avez pas besoin de laisser cette page ouverte.',
  (291, 'ja'): 'ライブラリをバックグラウンドで読み込んでいます。このページを開いたままにする必要はありません。',
  (291, 'ko'): '라이브러리를 백그라운드에서 읽는 중입니다. 이 페이지를 열어 둘 필요는 없습니다.',
  (291, 'vi'): 'Đang đọc thư viện của bạn trong nền. Bạn không cần giữ trang này mở.',
  (291, 'zh-Hans'): '正在后台读取您的媒体库。您无需保持此页面打开。',
  (291, 'zh-Hant'): '正在背景中讀取您的媒體庫。您不必讓此頁面保持開啟。',

  (293, 'ar'): 'موصى به · شائع على IGDB',
  (293, 'de'): 'Empfohlen · auf IGDB beliebt',
  (293, 'es'): 'Recomendado · popular en IGDB',
  (293, 'fr'): 'Recommandé · populaire sur IGDB',
  (293, 'hi'): 'अनुशंसित · IGDB पर लोकप्रिय',
  (293, 'id'): 'Direkomendasikan · populer di IGDB',
  (293, 'ja'): 'おすすめ · IGDB で人気',
  (293, 'ko'): '추천 · IGDB 인기순',
  (293, 'pt-BR'): 'Recomendado · popular no IGDB',
  (293, 'vi'): 'Đề xuất · phổ biến trên IGDB',
  (293, 'zh-Hans'): '推荐 · IGDB 热门',
  (293, 'zh-Hant'): '推薦 · IGDB 熱門',

  (294, 'fr'): 'Actualiser les métadonnées',
  (294, 'hi'): 'मेटाडेटा रीफ़्रेश करें',
  (294, 'id'): 'Perbarui metadata',
  (294, 'ja'): 'メタデータを更新',
  (294, 'ko'): '메타데이터 새로고침',
  (294, 'vi'): 'Làm mới metadata',

  (295, 'de'): 'API-Schlüssel abgelehnt',
  (295, 'es'): 'La clave de API fue rechazada',
  (295, 'hi'): 'API कुंजी अस्वीकार कर दी गई',
  (295, 'ko'): 'API 키가 거부되었습니다.',

  (296, 'vi'): 'Hồ sơ phát hành',

  (298, 'ar'): 'تاريخ الإصدار',
  (298, 'de'): 'Erscheinungsdatum',
  (298, 'es'): 'Fecha de lanzamiento',
  (298, 'fr'): 'Date de sortie',
  (298, 'hi'): 'रिलीज़ की तारीख',
  (298, 'id'): 'Tanggal rilis',
  (298, 'ja'): '発売日',
  (298, 'ko'): '출시일',
  (298, 'pt-BR'): 'Data de lançamento',
  (298, 'vi'): 'Ngày phát hành',
  (298, 'zh-Hans'): '发行日期',
  (298, 'zh-Hant'): '發行日期',

  (299, 'es'): 'Eliminar el mapeo de la ruta {path}',
  (299, 'hi'): '{path} के लिए पथ मैपिंग हटाएँ',
  (300, 'es'): 'Eliminar la asignación de carpeta de plataforma para {folder}',
  (300, 'ja'): 'プラットフォームフォルダー {folder} のマッピングを削除',
  (300, 'ko'): '플랫폼 폴더 {folder} 매핑 제거',
  (301, 'es'): 'Eliminar esta asignación de ruta',
  (301, 'hi'): 'इस पथ मैपिंग को हटाएँ',
  (301, 'ko'): '이 경로 매핑 제거',
  (301, 'pt-BR'): 'Remover este mapeamento de caminho',
  (303, 'de'): 'Die Umbenennungen wurden angewendet.',
}

PROTECTED = {
  285: ['ES-DE'],
  287: ['ROM', 'Netplay'],
  288: ['Netplay', 'No-Intro', 'Redump'],
  289: ['Netplay', 'DAT'],
  293: ['IGDB'],
  295: ['API'],
}
REASONS = {
  285: 'Reports successful publication and keeps both dynamic counts attached to the correct item types; ES-DE is a format name.',
  287: 'Renders the scheduler task as an action to read ROM hashes from the library for Netplay.',
  288: 'Keeps the four count roles distinct and states that No-Intro/Redump matches are verified.',
  289: 'Keeps the count roles, absence of DAT matches, unverified state, and Settings path explicit.',
  290: 'Presents an in-progress library-loading status and leaves the dynamic library name in {where}.',
  291: 'States that the library read is ongoing in the background and the page may be closed.',
  292: 'Uses a concise readiness label for the scan action.',
  293: 'Makes the sort option mean recommended and popular on IGDB while preserving the service name.',
  294: 'Uses a direct button command for refreshing metadata.',
  295: 'Clearly reports that the provider rejected the API key.',
  296: 'Keeps the setting title focused on the release preference profile described by its caller.',
  297: 'Names the year-based release filter.',
  298: 'The caller uses this heading for game.releaseDate, so the label must name a date rather than a released state.',
  299: 'Names removal of the mapping associated with the dynamic path and preserves {path}.',
  300: 'Names removal of a platform-folder mapping and preserves {folder}.',
  301: 'Forms a clear remove-this-path-mapping action.',
  302: 'Forms a clear remove-this-platform-folder-mapping action.',
  303: 'Confirms that the rename operations were applied.',
}
HIGH_CONFIDENCE = {292, 294, 295, 297, 298}


def sha(s: str) -> str:
  return hashlib.sha256(s.encode('utf-8')).hexdigest()

def load_jsonl(path: Path):
  return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def context_refs(source):
  return [{
    'path': r['path'], 'startLine': r['startLine'], 'endLine': r['endLine'],
    'contextSha256': r['contextSha256'], 'fileSha256': r['fileSha256'],
    'gitBlob': r['gitBlob'], 'matchBasis': r['matchBasis'],
  } for r in source['references']]

sources = {x['position']: x for x in load_jsonl(INPUT / 'source-contexts.jsonl')}
holds = {(x['position'], x['locale']): x for x in load_jsonl(INPUT / 'caller-resolution-holds.jsonl')}
cells = load_jsonl(INPUT / 'current-target-cells.jsonl')
ledger = []
for cell in cells:
  key = (cell['position'], cell['locale'])
  src = sources[cell['position']]
  if key in holds:
    hold = holds[key]
    row = {
      'schemaVersion': 1,
      'window': cell['window'], 'position': cell['position'], 'sourceId': cell['sourceId'],
      'locale': cell['locale'], 'source': cell['source'], 'sourceSha256': cell['sourceSha256'],
      'currentTarget': cell['currentTarget'], 'currentTargetSha256': cell['currentTargetSha256'],
      'disposition': 'hold', 'proposedTarget': None, 'proposedTargetSha256': None,
      'preservedTarget': cell['currentTarget'], 'preservedTargetSha256': cell['currentTargetSha256'],
      'targetUnchangedFromCurrent': True, 'confidence': 'high',
      'rationale': 'Hold: the packet’s exact caller paths show opaque API detail/error text without a localizable display template; preserve this current value pending a connected localized UI path.',
      'holdReason': hold['holdReason'],
      'sourcePlaceholders': cell['sourcePlaceholders'],
      'targetPlaceholders': cell['targetPlaceholders'],
      'placeholderMultisetMatchesSource': cell['placeholderMultisetMatchesSource'],
      'protectedLiterals': [], 'protectedLiteralsPreserved': True,
      'sourceMarkupTags': cell['sourceMarkupTags'], 'targetMarkupTags': cell['targetMarkupTags'],
      'callerLocations': src['currentCallerLocations'],
      'callerContextReferences': context_refs(src),
      'sourceContextRef': {'file': 'source-contexts.jsonl', 'sourceSha256': src['sourceSha256']},
      'currentTargetCatalogRef': {'path': cell['catalogPath'], 'fileSha256': cell['catalogSha256'], 'gitBlob': cell['catalogGitBlob']},
    }
  else:
    target = REVISIONS.get(key, cell['currentTarget'])
    disposition = 'revise' if target != cell['currentTarget'] else 'retain'
    confidence = 'high' if cell['position'] in HIGH_CONFIDENCE else 'moderate'
    row = {
      'schemaVersion': 1,
      'window': cell['window'], 'position': cell['position'], 'sourceId': cell['sourceId'],
      'locale': cell['locale'], 'source': cell['source'], 'sourceSha256': cell['sourceSha256'],
      'currentTarget': cell['currentTarget'], 'currentTargetSha256': cell['currentTargetSha256'],
      'disposition': disposition, 'proposedTarget': target, 'proposedTargetSha256': sha(target),
      'preservedTarget': None, 'preservedTargetSha256': None,
      'targetUnchangedFromCurrent': target == cell['currentTarget'], 'confidence': confidence,
      'rationale': ('Revised: ' if disposition == 'revise' else 'Retained: ') + REASONS[cell['position']],
      'sourcePlaceholders': cell['sourcePlaceholders'],
      'targetPlaceholders': re.findall(r'\{[^{}]+\}', target),
      'placeholderMultisetMatchesSource': sorted(re.findall(r'\{([^{}]+)\}', target)) == sorted(cell['sourcePlaceholders']),
      'protectedLiterals': PROTECTED.get(cell['position'], []),
      'protectedLiteralsPreserved': all(lit.casefold() in target.casefold() for lit in PROTECTED.get(cell['position'], [])),
      'sourceMarkupTags': cell['sourceMarkupTags'],
      'targetMarkupTags': re.findall(r'</?([A-Za-z][A-Za-z0-9]*)\b[^>]*>', target),
      'callerLocations': src['currentCallerLocations'],
      'callerContextReferences': context_refs(src),
      'sourceContextRef': {'file': 'source-contexts.jsonl', 'sourceSha256': src['sourceSha256']},
      'currentTargetCatalogRef': {'path': cell['catalogPath'], 'fileSha256': cell['catalogSha256'], 'gitBlob': cell['catalogGitBlob']},
    }
  ledger.append(row)

OUT.mkdir(parents=True, exist_ok=True)
with (OUT / 'ledger.jsonl').open('w', encoding='utf-8', newline='\n') as f:
  for row in ledger:
    f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')

attestation = {
  'pullRequest': 70,
  'repository': 'snapetech-org/ROMarrNG',
  'packetHead': '363601fd2597f0fb97adff97554e651c2bea2d99',
  'packetTree': '1f8ada1746f53796e2b4a8f43f9a0075150aa5d7',
  'observedRemoteRefs': {
    'refs/pull/70/head': '363601fd2597f0fb97adff97554e651c2bea2d99',
    'refs/heads/task/localization-translation-review-20261030': '363601fd2597f0fb97adff97554e651c2bea2d99',
  },
  'observedCommitTree': '1f8ada1746f53796e2b4a8f43f9a0075150aa5d7',
  'checks': {
    'headMatchesPacket': True, 'treeMatchesPacket': True,
    'method': 'git ls-remote for the PR and head branch refs; read only the tree line from the already-present commit object',
    'prBodyInspected': False,
  },
  'inputPacketSha256': PACKET_SHA256,
}
(OUT / 'attestation.json').write_text(json.dumps(attestation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

counts = {}
for row in ledger:
  counts[row['disposition']] = counts.get(row['disposition'], 0) + 1
locale_counts = {}
for row in ledger:
  locale_counts[row['locale']] = locale_counts.get(row['locale'], 0) + 1
revisions_by_position = {}
for row in ledger:
  if row['disposition'] == 'revise': revisions_by_position[row['position']] = revisions_by_position.get(row['position'], 0) + 1
readme = f'''# ROMarrNG PR #70 W285–W304 independent blind review

This review was drafted only from the candidate-free input packet at `../../romarrng-pr70-w285-304-candidate-free-20261103/input` and the packet-pinned caller/context evidence. It did not inspect primary reviews, withdrawn blind material, cross-audits, prior translation proposals, PR body text, or memory data. The pre-existing `review/` directory was left untouched; this result is in `review-v2/`.

## Live PR attestation

Observed `refs/pull/70/head` and `refs/heads/task/localization-translation-review-20261030` both at `{attestation['observedRemoteRefs']['refs/pull/70/head']}`. The commit tree is `{attestation['observedCommitTree']}`. Both match the packet. The PR body was not inspected.

## Review counts

- Ledger cells: {len(ledger)}
- Hold: {counts.get('hold', 0)} (caller-path holds at ranks 286 and 304)
- Reviewable cells: {counts.get('retain', 0) + counts.get('revise', 0)}
- Retain unchanged: {counts.get('retain', 0)}
- Revised: {counts.get('revise', 0)}
- Revisions by source rank: {', '.join(f'{k}={v}' for k,v in sorted(revisions_by_position.items()))}
- Locale coverage: {', '.join(f'{k}={v}' for k,v in sorted(locale_counts.items()))}

The 24 held cells carry no proposal (`proposedTarget` and its hash are null); their current value and hash are recorded under `preservedTarget` and `preservedTargetSha256`. All other cells have an independent proposal, even when the proposal equals the current value. Confidence is cell-specific (`high` for straightforward labels and the caller-defined date heading; `moderate` for longer or domain-specific strings). It does not imply native-speaker approval.

## Verification

Run `python3 verify_ledger.py` from this directory. It verifies packet checksums, output checksums, 240 unique source×locale cells, source/current-value hashes, hold preservation, proposal hashes, placeholders, protected literals, markup tags, and unchanged-value dispositions.

## Packet fingerprint

`SHA256(SHA256SUMS.txt)` = `{PACKET_SHA256}`
'''
(OUT / 'README.md').write_text(readme, encoding='utf-8')
print(json.dumps({'cells': len(ledger), 'counts': counts, 'revisionsByPosition': revisions_by_position}, ensure_ascii=False, indent=2))
