from __future__ import annotations

import collections
import hashlib
import json
import re
from pathlib import Path

ROOT = Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w206-225-primary-20261103')
INPUT = ROOT / 'clean-input'
OUT = ROOT / 'primary-review'
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


PROTECTED = {
    210: ['DAT', 'ROMarrNG'],
    211: ['DAT', 'DAT_PATH', 'No-Intro', 'Redump'],
    212: ['DAT'],
    214: ['ROM'],
    219: ['JSON', 'patch-catalog.d'],
    220: ['PIN'],
}

# Key: (one-based source position, locale) -> (proposal, class, rationale, confidence)
PROPOSALS = {
    (206, 'ar'): ('أحدث من أحدث إصدار مُدرج', 'correction', 'The current phrase is awkward and does not cleanly express the listed version as the comparison point; this keeps the “newer than the latest listed version” relation.', 'moderate'),
    (206, 'de'): ('Neuer als die neueste aufgeführte Version', 'correction', 'The comparison target needs the definite article in German; the current wording reads like a missing-article fragment.', 'high'),
    (206, 'fr'): ('Plus récent que la dernière version répertoriée', 'refinement', '“Répertoriée” matches a version being listed more precisely than “enregistrée”; the masculine comparison refers to the current item.', 'moderate'),
    (206, 'ko'): ('목록에 표시된 최신 버전보다 더 새로운 버전입니다.', 'correction', 'The current wording repeats “latest” and does not clearly say that this item is a newer version than the latest one listed.', 'moderate'),
    (206, 'pt-BR'): ('Mais recente que a versão mais recente listada', 'correction', 'The current text omits that the comparison version is the latest one listed.', 'moderate'),
    (206, 'vi'): ('Mới hơn phiên bản mới nhất trong danh sách.', 'correction', 'The current text omits the “listed” qualifier, which distinguishes this status from a comparison against any latest version.', 'moderate'),

    (207, 'ar'): ('أحدث إصدار', 'correction', '“إطلاق” means a launch; “إصدار” is the appropriate release/version label for the release-year sort option.', 'moderate'),
    (207, 'de'): ('Neueste Veröffentlichung', 'correction', 'The current phrase uses the English noun “Release” with awkward German inflection; “Veröffentlichung” is clear and idiomatic for this sort label.', 'moderate'),

    (208, 'fr'): ('Les plus récents', 'refinement', 'This is a shelf tab for the newest games, so the plural label fits the collection better than the current singular “Le plus récent”.', 'moderate'),

    (209, 'fr'): ('Aucune jaquette', 'refinement', 'The caller uses this as the placeholder inside a game-cover art area; “jaquette” identifies the game cover more clearly than the broader “couverture”.', 'moderate'),

    (210, 'de'): ('In ROMarrNG ist kein DAT-Katalog geladen.', 'correction', 'The current passive construction says that no catalog is being loaded; the source describes the current state that none is loaded.', 'high'),
    (210, 'fr'): ('Aucun catalogue DAT n’est chargé dans ROMarrNG.', 'correction', 'French requires “n’est” after “Aucun”; the current translation omits the negative particle.', 'high'),
    (210, 'pt-BR'): ('Nenhum catálogo DAT está carregado em ROMarrNG.', 'refinement', '“Está carregado” describes the current loaded state; “é carregado” reads as a general passive process.', 'moderate'),

    (215, 'vi'): ('Không tìm thấy thư viện nào của trình khởi chạy trên máy này.', 'correction', '“Thư viện khởi động” means a startup/boot library; this source means a game launcher’s library.', 'high'),

    (220, 'de'): ('Keine PIN angegeben', 'correction', '“PIN angegeben” is the idiomatic German wording for a missing supplied PIN; the current “PIN gegeben” is awkward.', 'high'),
    (220, 'id'): ('PIN tidak diberikan', 'correction', 'The current word order is unidiomatic Indonesian; this says directly that no PIN was provided.', 'moderate'),
    (220, 'vi'): ('Chưa cung cấp PIN', 'correction', 'The current word order is awkward Vietnamese; this is a natural concise error detail for a PIN that was not supplied.', 'moderate'),

    (222, 'hi'): ('कोई सुरक्षित मानक शीर्षक नहीं', 'correction', 'The current transliteration “कैननिक” is not a natural Hindi rendering of “canonical”; “मानक” conveys the standard/canonical title in this metadata context.', 'moderate'),
    (222, 'ja'): ('安全な正規タイトルがありません', 'refinement', '“正規タイトル” is the standard Japanese term for a canonical title; the current “カノニック” is an awkward transliteration.', 'moderate'),
    (222, 'vi'): ('Không có tiêu đề chuẩn hóa an toàn', 'correction', 'The current “canonic” is an English-like form; “chuẩn hóa” conveys a normalized/canonical title in Vietnamese.', 'moderate'),

    (223, 'de'): ('Für diesen Stapel liegen keine sicheren Umbenennungen vor.', 'correction', 'The current text leaves “Renames” in English and uses “Paket” for “batch”; this uses idiomatic German for safe rename operations in a batch.', 'high'),
    (223, 'es'): ('No hay cambios de nombre seguros listos en este lote.', 'correction', '“Renombrados” is an awkward noun here; “cambios de nombre” clearly describes the ready rename operations.', 'moderate'),
    (223, 'zh-Hans'): ('此批次没有可执行的安全重命名操作。', 'correction', 'The current “包装” means packaging/package, not a batch, and the sentence structure is unnatural; this names safe rename operations for the batch.', 'moderate'),
    (223, 'zh-Hant'): ('此批次沒有可執行的安全重新命名作業。', 'correction', 'The current “包裝” means packaging/package, not a batch, and the sentence structure is unnatural; this names safe rename operations for the batch.', 'moderate'),

    (224, 'ko'): ('그런 친구가 없습니다.', 'refinement', 'The current wording is casual; the polite form better fits a user-facing API error and matches the formal register used by nearby Korean error translations.', 'moderate'),
}

HOLD_RATIONALE = (
    'The exact callers supply `what` as the English action phrases “browse” and “answer for a date range”. '
    'The packet does not establish whether those inserted values are localized before this sentence is displayed. '
    'The target wording depends on the grammar of `{what}`, so I cannot safely approve or rewrite it without that placeholder-localization contract.'
)

cells = load_jsonl(INPUT / 'current-target-cells.jsonl')
contexts = {row['position']: row for row in load_jsonl(INPUT / 'source-contexts.jsonl')}
input_manifest = json.loads((INPUT / 'manifest.json').read_text(encoding='utf-8'))
input_checksums = (INPUT / 'SHA256SUMS.txt').read_text(encoding='utf-8')
assert sha(input_checksums.encode('utf-8'))
assert len(cells) == 240 and len(contexts) == 20

rows = []
for cell in cells:
    pos = cell['position']
    locale = cell['locale']
    source = cell['source']
    current = cell['currentTarget']
    expected_placeholders = re.findall(r'\{[^{}]+\}', source)
    current_placeholders = re.findall(r'\{[^{}]+\}', current)
    proposed = PROPOSALS.get((pos, locale))
    is_hold = pos == 218

    if is_hold:
        disposition = 'hold'
        proposal = None
        proposal_type = None
        rationale = HOLD_RATIONALE
        confidence = 'low'
    elif proposed:
        proposal, proposal_type, rationale, confidence = proposed
        disposition = 'correction/refinement proposal'
    else:
        disposition = 'accept-current'
        proposal = None
        proposal_type = None
        rationale = 'The current wording conveys the source meaning for the pinned caller context; I found no material semantic or grammar defect. The recorded protected literals and placeholders are preserved.'
        confidence = 'low' if locale in {'ar', 'hi', 'id', 'ko', 'vi', 'zh-Hans', 'zh-Hant'} else 'moderate'

    target_for_check = proposal if proposal is not None else current
    proposal_placeholders = re.findall(r'\{[^{}]+\}', target_for_check)
    required_literals = PROTECTED.get(pos, [])
    literal_checks = [{'literal': literal, 'presentExactly': literal in current} for literal in required_literals]
    proposal_literal_checks = [{'literal': literal, 'presentExactly': literal in target_for_check} for literal in required_literals]
    placeholder_checks = {
        'expected': expected_placeholders,
        'current': current_placeholders,
        'currentExactMultisetMatch': collections.Counter(expected_placeholders) == collections.Counter(current_placeholders),
        'reviewTarget': proposal_placeholders,
        'reviewTargetExactMultisetMatch': collections.Counter(expected_placeholders) == collections.Counter(proposal_placeholders),
    }
    caller_refs = contexts[pos]['references']
    rows.append({
        'schemaVersion': 1,
        'repository': cell['repository'],
        'pullRequest': cell['pullRequest'],
        'window': cell['window'],
        'head': cell['head'],
        'tree': cell['tree'],
        'position': pos,
        'sourceId': cell['sourceId'],
        'source': source,
        'sourceSha256': cell['sourceSha256'],
        'locale': locale,
        'currentTarget': current,
        'currentTargetSha256': cell['currentTargetSha256'],
        'disposition': disposition,
        'proposalType': proposal_type,
        'proposedTarget': proposal,
        'proposedTargetSha256': sha(proposal.encode('utf-8')) if proposal is not None else None,
        'rationale': rationale,
        'confidence': confidence,
        'placeholderChecks': placeholder_checks,
        'protectedLiteralsRequired': required_literals,
        'protectedLiteralChecks': literal_checks,
        'reviewTargetLiteralChecks': proposal_literal_checks,
        'callerContextPins': [{'path': r['path'], 'startLine': r['startLine'], 'endLine': r['endLine'], 'contextSha256': r['contextSha256']} for r in caller_refs],
        'holdEvidence': {
            'whatValuesAtPinnedCallers': ['browse', 'answer for a date range'] if is_hold else [],
            'offerIsComputedFromProviderMetadata': bool(is_hold),
        } if is_hold else None,
    })

assert len(rows) == 240
assert len({(row['sourceId'], row['locale']) for row in rows}) == 240
assert all(row['placeholderChecks']['currentExactMultisetMatch'] for row in rows)
assert all(all(x['presentExactly'] for x in row['protectedLiteralChecks']) for row in rows)
assert all(all(x['presentExactly'] for x in row['reviewTargetLiteralChecks']) for row in rows)

counts = collections.Counter(row['disposition'] for row in rows)
proposal_classes = collections.Counter(row['proposalType'] for row in rows if row['proposedTarget'] is not None)
proposal_rows = [{k: row[k] for k in ['position', 'sourceId', 'locale', 'currentTarget', 'proposedTarget', 'proposalType', 'rationale', 'confidence']} for row in rows if row['proposedTarget'] is not None]
hold_rows = [{k: row[k] for k in ['position', 'sourceId', 'locale', 'currentTarget', 'rationale', 'confidence', 'holdEvidence']} for row in rows if row['disposition'] == 'hold']
input_hashes = {}
for line in input_checksums.splitlines():
    digest, name = line.split('  ', 1)
    input_hashes[name] = digest

summary = {
    'schemaVersion': 1,
    'reviewType': 'primary semantic review',
    'repository': 'snapetech-org/ROMarrNG',
    'pullRequest': 70,
    'window': 'W206-W225',
    'head': input_manifest['head'],
    'tree': input_manifest['tree'],
    'inputPacket': str(INPUT),
    'inputChecksumListSha256': sha(input_checksums.encode('utf-8')),
    'inputFiles': input_hashes,
    'sourceCount': 20,
    'localeCount': 12,
    'cellCount': len(rows),
    'dispositionCounts': dict(counts),
    'proposalClassCounts': dict(proposal_classes),
    'placeholderCheckCount': sum(1 for row in rows if row['placeholderChecks']['currentExactMultisetMatch']),
    'protectedLiteralCheckCount': sum(1 for row in rows if all(x['presentExactly'] for x in row['protectedLiteralChecks'])),
    'proposalCount': len(proposal_rows),
    'proposals': proposal_rows,
    'holdCount': len(hold_rows),
    'holds': hold_rows,
    'nativeSpeakerApproval': False,
    'limitations': [
        'Machine semantic review is not native-speaker approval.',
        'The 12 `what`-placeholder cells for position 218 are held because the pinned callers pass English action phrases and the input packet does not establish whether those inserted values are localized before display.',
    ],
}

OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'primary-decisions.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows), encoding='utf-8')
write_json(OUT / 'summary.json', summary)
readme = f'''# ROMarrNG PR #70 W206–W225 primary semantic review\n\nThis ledger reviews all {len(rows)} current translation cells for 20 source messages in 12 direct available locales. It is pinned to PR head `{input_manifest['head']}` and tree `{input_manifest['tree']}`. The candidate-free input packet is `{INPUT}`; its checksums are recorded in `summary.json`.\n\nEach row records the current value, accept/proposal/hold disposition, rationale, confidence, exact placeholder and protected-literal checks, and caller-context hashes. The only holds are the 12 position-218 cells: exact callers pass English `what` values (“browse” and “answer for a date range”), while this packet does not show whether those values are localized before insertion.\n\nThis is a machine review, not native-speaker approval. No repository or PR files were changed.\n'''
(OUT / 'README.md').write_text(readme, encoding='utf-8')
checks = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != 'SHA256SUMS.txt':
        checks.append(f'{sha(path.read_bytes())}  {path.name}')
(OUT / 'SHA256SUMS.txt').write_text('\n'.join(checks) + '\n', encoding='utf-8')
print(json.dumps({'head': summary['head'], 'tree': summary['tree'], 'cells': len(rows), 'counts': dict(counts), 'proposalClasses': dict(proposal_classes), 'proposalCount': len(proposal_rows), 'holdCount': len(hold_rows), 'output': str(OUT)}, ensure_ascii=False, indent=2))
