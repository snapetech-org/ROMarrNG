#!/usr/bin/env python3
"""Regenerate a read-only primary semantic review ledger for ROMarr #70.

Reads the frozen input packet, current pinned checkout and live PR metadata.
Writes only primary-review.json in this scratch directory.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

OUT = pathlib.Path(__file__).resolve().parent
INPUT = OUT / 'file-context-review-input.json'
INPUT_MANIFEST = OUT / 'manifest.json'
REPO = pathlib.Path('/home/keith/Documents/code/task-worktrees/localization-20261102-romarrng')
OWNER_REPO = 'snapetech-org/ROMarrNG'
LOCALES = ['es', 'zh-Hans', 'hi', 'de', 'ja', 'fr', 'pt-BR', 'ar', 'ko', 'zh-Hant', 'vi', 'id']


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())


def catalog_target_sha(value: str) -> str:
    """ui-labels translationHashes use a compact JSON scalar encoding."""
    return sha_bytes(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def raw_target_sha(value: str) -> str:
    return sha_bytes(value.encode('utf-8'))


def git(*args: str) -> str:
    return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f'PIN/INPUT ERROR: {message}')


packet = json.loads(INPUT.read_text(encoding='utf-8'))
manifest = json.loads(INPUT_MANIFEST.read_text(encoding='utf-8'))
input_sha = sha_file(INPUT)
require(manifest.get('files', {}).get(INPUT.name) == input_sha, 'input packet SHA256 differs from manifest')
require(git('rev-parse', 'HEAD') == packet['head'], 'worktree HEAD differs from packet')
require(git('rev-parse', 'HEAD^{tree}') == packet['tree'], 'worktree tree differs from packet')
require(git('status', '--porcelain=v1', '--untracked-files=all') == '', 'pinned worktree is not clean')

catalog_path = REPO / packet['currentCatalogPath']
ui_path = REPO / 'romarr/ui.py'
require(sha_file(catalog_path) == packet['currentCatalogSha256'], 'current catalog SHA differs from packet')
require(sha_file(ui_path) == packet['currentActionUse']['fileSha256'], 'current ui.py SHA differs from packet')

pr = json.loads(subprocess.check_output(['gh', 'api', f"repos/{OWNER_REPO}/pulls/{packet['pullRequest']}"], text=True))
live = {
    'state': pr.get('state'),
    'draft': pr.get('draft'),
    'head': (pr.get('head') or {}).get('sha'),
    'base': (pr.get('base') or {}).get('ref'),
}
require(live['state'] == packet['state'].lower() and live['draft'] is packet['draft'], 'live PR state/draft differs from packet')
require(live['head'] == packet['head'] and live['base'] == 'main', 'live PR head/base differs from packet')

catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
messages = catalog['messages']
file_key = packet['currentFileKey']
file_entry = messages[file_key]
require(file_entry.get('source') == packet['currentFileSource'], 'current File source differs')
require(file_entry.get('sourceHash') == packet['currentFileSourceHash'], 'current File source hash differs')

pipeline = packet['proposedSourceSplit']
require(sha_bytes(pipeline['pipelineSource'].encode('utf-8')) == pipeline['pipelineSourceSha256'], 'new pipeline source SHA differs')
require(pipeline['pipelineMessageId'].endswith(pipeline['pipelineSourceSha256'][:10]), 'new pipeline key suffix does not match source SHA')
require(pipeline['pipelineMessageId'] not in messages, 'new pipeline key already exists in current catalog')

ui_lines = ui_path.read_text(encoding='utf-8').splitlines()
for row in [packet['currentActionUse'], packet['currentFileColumnUse']]:
    require(row['path'] == 'romarr/ui.py', 'unexpected pinned caller path')
    require(ui_lines[row['line'] - 1].strip() == row['lineText'], f"pinned caller changed at {row['line']}")

old_catalog = json.loads(subprocess.check_output([
    'git', '-C', str(REPO), 'show', 'a1278acda1cea823443d7d6b712ed6ace8a99694:romarr/ui-labels.json'
], text=False))
old_file_translations = old_catalog['messages'][file_key]['translations']

noun_notes = {
    'es': 'Archivo is the standard concise file noun; it fits a table column whose cells contain ROM filenames.',
    'zh-Hans': '文件 is the concise file noun; the filename values make the column meaning clear.',
    'hi': 'फ़ाइल is the familiar concise file noun and fits the filename column.',
    'de': 'Datei is the standard concise file noun for a filename column.',
    'ja': 'ファイル is the common concise file noun; the table values identify it as a filename column.',
    'fr': 'Fichier is the standard concise file noun and works as a filename column heading.',
    'pt-BR': 'Arquivo is the standard concise file noun for a column containing ROM filenames.',
    'ar': 'ملف is a concise file noun; the column values make the filename context clear.',
    'ko': '파일 is the standard concise file noun for this column.',
    'zh-Hant': '檔案 is the concise file noun; the filename values make the column meaning clear.',
    'vi': 'Tệp is the concise, current Vietnamese computing noun for a file; it fits the filename values.',
    'id': 'Berkas is a standard concise file noun and is consistent with the catalog’s pustaka terminology.',
}
action_notes = {
    'es': 'Añadir a la biblioteca is a concise, conventional infinitive action label; biblioteca matches the game-library concept.',
    'zh-Hans': '添加到游戏库 is direct and compact, with 游戏库 making the game-library meaning explicit.',
    'hi': 'लाइब्रेरी में जोड़ें is a clear imperative and retains the established borrowed term for library.',
    'de': 'Zur Bibliothek hinzufügen is a natural, concise task label and preserves the product’s Bibliothek term.',
    'ja': 'ライブラリに追加 is a natural compact action label and uses the familiar game-library term.',
    'fr': 'Ajouter à la bibliothèque is a conventional concise action label and preserves the established term.',
    'pt-BR': 'Adicionar à biblioteca is a natural infinitive action label and matches the product term.',
    'ar': 'أضف إلى المكتبة is the standard unvocalized imperative UI form; the proposed kasra diacritic is unnecessary in this label.',
    'ko': '라이브러리에 추가 is a natural compact action label and retains the familiar library term.',
    'zh-Hant': '新增至遊戲庫 is concise and clearly names the game library as the destination.',
    'vi': 'Thêm vào thư viện is a natural, concise imperative and preserves the catalog’s library term.',
    'id': 'Tambahkan ke pustaka is a natural imperative and matches the catalog’s established pustaka term.',
}

proposals = {row['locale']: row for row in packet['proposals']}
require(set(proposals) == set(LOCALES), 'proposal locale set is incomplete or unexpected')
noun_rows = []
action_rows = []
candidate_accept_count = 0
refinement_count = 0
for locale in LOCALES:
    row = proposals[locale]
    current_value = file_entry['translations'][locale]
    current_hash = catalog_target_sha(current_value)
    require(current_hash == row['currentTargetSha256'], f'{locale}: current value hash differs from packet')
    require(current_hash == file_entry['translationHashes'][locale], f'{locale}: stored current translation hash mismatch')
    require(file_entry['translationStatus'][locale] == 'draft', f'{locale}: current file translation is unexpectedly not draft')
    require(locale not in file_entry.get('translationReview', {}), f'{locale}: unexpected existing review record')

    noun_candidate = row['proposedFileHeader']
    require(noun_candidate == packet['proposedNounTargets'][locale], f'{locale}: proposal noun maps disagree')
    noun_target_sha = catalog_target_sha(noun_candidate)
    baseline_noun = old_file_translations[locale]
    noun_rows.append({
        'locale': locale,
        'target': noun_candidate,
        'catalogTargetSha256': noun_target_sha,
        'rawUtf8Sha256': raw_target_sha(noun_candidate),
        'decision': 'accept',
        'confidence': 'moderate',
        'reviewNote': noun_notes[locale],
        'matchesOldA127Noun': noun_candidate == baseline_noun,
        'oldA127Noun': baseline_noun,
        'oldA127CatalogTargetSha256': catalog_target_sha(baseline_noun),
    })

    action_candidate = row['proposedActionLabel']
    require(action_candidate == packet['proposedActionTargets'][locale], f'{locale}: proposal action maps disagree')
    action_final = 'أضف إلى المكتبة' if locale == 'ar' else action_candidate
    action_decision = 'refine' if action_final != action_candidate else 'accept'
    if action_decision == 'refine':
        refinement_count += 1
    else:
        candidate_accept_count += 1
    action_rows.append({
        'locale': locale,
        'candidate': action_candidate,
        'candidateCatalogTargetSha256': catalog_target_sha(action_candidate),
        'candidateRawUtf8Sha256': raw_target_sha(action_candidate),
        'target': action_final,
        'catalogTargetSha256': catalog_target_sha(action_final),
        'rawUtf8Sha256': raw_target_sha(action_final),
        'decision': action_decision,
        'confidence': 'moderate',
        'reviewNote': action_notes[locale],
    })

require(len(noun_rows) == 12 and len(action_rows) == 12, 'ledger does not contain 24 locale targets')
require(candidate_accept_count == 11 and refinement_count == 1, 'unexpected candidate disposition totals')

terminology_reference_ids = [
    'ui.library.dc20b3d5d2',
    'ui.browse-library.fef7a75748',
    'ui.a-centralized-game-library-and-launc.777c7497a1',
]
terminology_references = []
for message_id in terminology_reference_ids:
    entry = messages[message_id]
    terminology_references.append({
        'messageId': message_id,
        'source': entry['source'],
        'translations': {locale: entry['translations'][locale] for locale in LOCALES},
        'catalogTargetSha256': {locale: catalog_target_sha(entry['translations'][locale]) for locale in LOCALES},
    })

report = {
    'schemaVersion': 1,
    'artifact': 'ROMarrNG PR #70 file-label split primary semantic review',
    'result': 'APPROVE_WITH_ARABIC_ACTION_STYLE_REFINEMENT',
    'reviewConfidence': 'moderate',
    'scope': 'Primary semantic review of 12 File noun/header targets and 12 Add to library action targets.',
    'pins': {
        'repository': packet['repository'],
        'pullRequest': packet['pullRequest'],
        'livePullRequest': live,
        'head': packet['head'],
        'tree': packet['tree'],
        'worktreeClean': True,
        'inputPacket': INPUT.name,
        'inputPacketSha256': input_sha,
        'inputManifestSha256': sha_file(INPUT_MANIFEST),
        'catalogPath': packet['currentCatalogPath'],
        'catalogSha256': sha_file(catalog_path),
        'uiSourcePath': 'romarr/ui.py',
        'uiSourceSha256': sha_file(ui_path),
        'currentFileMessageId': file_key,
        'currentFileSource': packet['currentFileSource'],
        'currentFileSourceSha256': packet['currentFileSourceHash'],
        'currentFileCellState': 'all 12 locales are draft and have no translationReview entries',
        'newActionMessageId': pipeline['pipelineMessageId'],
        'newActionSource': pipeline['pipelineSource'],
        'newActionSourceSha256': pipeline['pipelineSourceSha256'],
        'newActionKeyAbsentAtPinnedHead': True,
        'actionCaller': packet['currentActionUse'],
        'fileHeaderCaller': packet['currentFileColumnUse'],
    },
    'method': {
        'review': 'Independently assessed the two usages in their current UI contexts, locale terminology, concise fit, and exact catalog target hashes.',
        'catalogTargetHashAlgorithm': 'SHA-256 of compact UTF-8 JSON serialization of the string scalar, matching ui-labels.json translationHashes.',
        'rawTargetHashAlgorithm': 'SHA-256 of the target string UTF-8 bytes.',
        'nativeSpeakerApproval': False,
        'browserReview': False,
        'repositoryEdits': False,
        'testsBuildsCi': False,
    },
    'summary': {
        'fileNounTargetsReviewed': len(noun_rows),
        'fileNounTargetsAcceptedAsProposed': len(noun_rows),
        'actionTargetsReviewed': len(action_rows),
        'actionTargetsAcceptedAsProposed': candidate_accept_count,
        'actionTargetsRefined': refinement_count,
        'heldTargets': 0,
        'refinement': {
            'locale': 'ar',
            'from': proposals['ar']['proposedActionLabel'],
            'to': 'أضف إلى المكتبة',
            'reason': 'Remove optional vocalization; unvocalized imperative is the conventional concise UI form.',
        },
        'otherNotableChoice': {
            'locale': 'vi',
            'target': 'Tệp',
            'note': 'Accepted as a concise current computing noun for file; it is shorter than the old a127 wording “Tập tin”.',
        },
    },
    'fileNounTargets': noun_rows,
    'addToLibraryTargets': action_rows,
    'libraryTerminologyReferences': terminology_references,
    'remainingReviewLimit': 'This is an AI primary semantic review, not native-speaker approval; native-speaker review remains outstanding.',
}

(OUT / 'primary-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({
    'result': report['result'],
    'head': packet['head'],
    'tree': packet['tree'],
    'nounTargets': len(noun_rows),
    'actionTargets': len(action_rows),
    'acceptedCandidateActions': candidate_accept_count,
    'refinedActions': refinement_count,
    'held': report['summary']['heldTargets'],
    'catalogSha256': sha_file(catalog_path),
    'inputSha256': input_sha,
}, ensure_ascii=False, indent=2))
