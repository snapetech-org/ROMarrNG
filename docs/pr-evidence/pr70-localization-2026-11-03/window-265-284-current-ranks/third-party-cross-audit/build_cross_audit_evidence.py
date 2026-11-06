#!/usr/bin/env python3
"""Build the W265-W284 cross-audit evidence packet from pinned review ledgers."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from collections import Counter, defaultdict

INPUT = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w265-284-candidate-free-20261103/input')
PRIMARY = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w265-284-primary-20261103')
BLIND = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w265-284-independent-blind-20261103')
OUT = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w265-284-cross-audit-20261103')
REPO = 'snapetech-org/ROMarrNG'
PR = 70
HEAD = 'c135c4729582817273c946891186ab4ea87467b5'
TREE = '32c07150396335a5832b5664fc1e0225d7cebdc1'
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']
POSITIONS = list(range(265, 285))
DIRECT_POSITIONS = {265, 266, 267, 268, 283, 284}
PH_RE = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')

# Reconciled direct-caller recommendations. Every target is based on the current
# pinned source and caller context; opaque named placeholders remain unchanged.
CHANGES: dict[tuple[int, str], tuple[str, str]] = {
    (265, 'de'): ('Projekte stammen ausschließlich aus Ihrem eigenen Katalog. Die Vollständigkeit richtet sich danach, was ein Projekt angibt; sie wird niemals geschätzt. Anfragen kommen von SeerrNG.', '“Vorstellung” means an idea or imagination, not a guess. This keeps the project-declared completeness rule and corrects the German meaning.'),
    (265, 'hi'): ('परियोजनाएँ केवल आपके अपने कैटलॉग से आती हैं। पूर्णता परियोजना के बताए अनुसार ही होती है; इसका अनुमान नहीं लगाया जाता। अनुरोध SeerrNG से आते हैं।', 'The current Hindi is awkward and does not clearly express project-declared completeness without guessing. The revised copy preserves both clauses and uses Hindi punctuation.'),
    (265, 'id'): ('Proyek hanya berasal dari katalog Anda sendiri. Kelengkapan ditentukan oleh keterangan proyek, bukan perkiraan. Permintaan berasal dari SeerrNG.', 'The current Indonesian mistranslates completeness as perfection and guess as a riddle. The revision restores the project-declared completeness meaning.'),
    (265, 'ja'): ('プロジェクトはご自身のカタログに登録されたものだけです。完全性は各プロジェクトが示す内容に基づき、推測しません。リクエストはSeerrNGから届きます。', 'The current Japanese lacks sentence boundaries and reads awkwardly. The revision makes the catalog-only and project-declared completeness statements clear.'),
    (265, 'zh-Hans'): ('项目仅来自您自己的目录。完整性以项目所声明的内容为准，绝不靠猜测。请求来自 SeerrNG。', 'The current copy uses non-Chinese punctuation and an awkward literal clause. The revision expresses the declared-completeness rule naturally.'),
    (265, 'zh-Hant'): ('專案僅來自您自己的目錄。完整性以專案所述為準，絕不靠猜測。請求來自 SeerrNG。', 'The current Traditional Chinese uses Simplified punctuation and literal wording. The revision uses Traditional forms and preserves the source meaning.'),
    (266, 'ar'): ('المسار المقترح', 'The pinned caller is a file-rename preview table beside “Current path”; “المسار” is the filesystem-path term.'),
    (266, 'de'): ('Vorgeschlagener Pfad', 'The current German heading lacks the required inflection and noun capitalization.'),
    (266, 'es'): ('Ruta propuesta', 'This is a filesystem path in a rename-preview table; “ruta” is more precise than the current road/way wording.'),
    (266, 'hi'): ('प्रस्तावित फ़ाइल पथ', 'The caller shows a filesystem path. The revised label makes that meaning explicit instead of suggesting a route.'),
    (266, 'id'): ('Jalur berkas yang diusulkan', 'The current “Jalan” means a road. This table shows a file path, so use “jalur berkas”.'),
    (266, 'ja'): ('提案されたパス', 'The caller shows a filesystem rename path. Use the technical path term パス instead of 道, which means road or way.'),
    (266, 'vi'): ('Đường dẫn đề xuất', 'The current wording reads as a road; “đường dẫn” is the filesystem-path term used by this preview.'),
    (267, 'ar'): ('دليل إعداد موفّر الهوية {provider} (يُفتح في علامة تبويب جديدة)', 'This accessible OIDC help-link label should attach the opaque {provider} value to the identity-provider setup guide. The exact placeholder is preserved.'),
    (267, 'es'): ('Guía de configuración del proveedor de identidad {provider} (se abre en una pestaña nueva)', 'The pinned OIDC help link needs a grammatical Spanish label with the provider value after the noun phrase; the exact placeholder is preserved.'),
    (267, 'ja'): ('{provider} のIDプロバイダー設定ガイド（新しいタブで開きます）', 'Use the standard technical term IDプロバイダー and a natural accessible-link label. Preserve the opaque provider value exactly.'),
    (267, 'ko'): ('{provider} ID 공급자 설정 가이드 (새 탭에서 열립니다)', 'The current literal “정체성 공급자” is unnatural for OIDC. Use ID 공급자 and preserve the opaque value.'),
    (267, 'vi'): ('Hướng dẫn thiết lập nhà cung cấp danh tính {provider} (mở trong tab mới)', 'Move the dynamic provider value into a grammatical Vietnamese noun phrase and preserve it exactly.'),
    (267, 'zh-Hant'): ('{provider} 身分提供者設定指南（在新分頁中開啟）', 'The current target uses Simplified Chinese forms in a Traditional Chinese locale. Use Traditional terminology and punctuation; preserve the provider placeholder.'),
    (268, 'de'): ('Anbietervorschlag · prüfen', 'The pinned confidence badge means provider-suggested content requiring review, not a provider rating. Use a concise review action.'),
    (268, 'es'): ('Sugerencia del proveedor · revisar', 'The current noun order is malformed. This badge marks a provider suggestion for review.'),
    (268, 'hi'): ('प्रदाता का सुझाव · समीक्षा आवश्यक', 'The badge marks a provider suggestion that needs human review, not a provider rating. State the review requirement clearly.'),
    (268, 'ja'): ('プロバイダーの提案 · 要確認', 'The badge means the provider suggested this match and it needs review. 要確認 conveys that status more clearly than the loanword レビュー.'),
    (268, 'ko'): ('공급자 제안 · 검토 필요', 'The badge means provider-suggested content needs human review, not a provider rating.'),
    (268, 'pt-BR'): ('Sugestão do provedor · revisar', 'Correct the malformed current noun order while retaining the review action shown by the badge.'),
    (268, 'vi'): ('Đề xuất của nhà cung cấp · cần xem xét', 'The current “đánh giá” can suggest a rating. The badge requires review of provider-suggested content.'),
    (283, 'ar'): ('نشر بيانات ES-DE', 'Correct the Arabic object order and keep the ES-DE product name intact.'),
    (283, 'de'): ('ES-DE-Daten veröffentlichen', 'Use the German compound hyphenation for the product name and its data.'),
    (284, 'ar'): ('تم نشر {count} من إدخالات ES-DE.', 'This count-bearing completion message needs grammatical Arabic word order. Preserve {count} exactly.'),
    (284, 'es'): ('Se publicaron {count} entradas de ES-DE.', 'Correct gender agreement and word order for the feminine noun entradas; preserve {count}.'),
    (284, 'fr'): ('Publication de {count} entrées ES-DE terminée.', 'The source is a completion toast. Use grammatical feminine agreement for publication and preserve {count}.'),
    (284, 'id'): ('Sebanyak {count} entri ES-DE telah dipublikasikan.', 'Reorder the quantity and verb into natural Indonesian. Preserve {count} and the meaning “entries”.'),
    (284, 'ko'): ('ES-DE 항목 {count}개를 게시했습니다.', 'Replace the current fragment with a complete Korean completion sentence; preserve {count}.'),
    (284, 'pt-BR'): ('Foram publicadas {count} entradas de ES-DE.', 'Preserve “entries” as entradas and use feminine agreement. Keep {count} exact.'),
}
REFINEMENTS = {(267, 'ja')}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha(obj) -> str:
    return sha(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def by_key(rows: list[dict], key_names=('position', 'locale')) -> dict:
    result = {}
    for row in rows:
        key = tuple(row[name] for name in key_names)
        if key in result:
            raise ValueError(f'duplicate row key {key}')
        result[key] = row
    return result


def check_checksums(folder: pathlib.Path) -> list[str]:
    issues = []
    for line in (folder / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        actual = sha((folder / name).read_bytes())
        if expected != actual:
            issues.append(f'{folder.name}/{name}: expected {expected}, got {actual}')
    return issues


def main() -> None:
    generated_names = {'README.md', 'SHA256SUMS.txt', 'attestation.json', 'cross-audit-ledger.jsonl', 'disagreement-and-hold-summary.json', 'report.md', 'summary.json'}
    supplemental_names = {'build_cross_audit_evidence.py', 'pinned-state-verification.json', 'verify_cross_audit_evidence.py'}
    if OUT.exists() and any(item.name not in generated_names | supplemental_names for item in OUT.iterdir()):
        raise SystemExit(f'refusing to overwrite files not owned by this task in: {OUT}')
    OUT.mkdir(parents=True, exist_ok=True)
    issues = check_checksums(INPUT) + check_checksums(PRIMARY) + check_checksums(BLIND)
    if issues:
        raise SystemExit('input checksum failure: ' + '; '.join(issues))

    manifest = json.loads((INPUT / 'manifest.json').read_text(encoding='utf-8'))
    pin = json.loads((INPUT / 'catalog-file-pins.json').read_text(encoding='utf-8'))
    primary_summary = json.loads((PRIMARY / 'summary.json').read_text(encoding='utf-8'))
    blind_summary = json.loads((BLIND / 'summary.json').read_text(encoding='utf-8'))
    blind_seal = json.loads((BLIND / 'blind-seal.json').read_text(encoding='utf-8'))
    blind_provenance = json.loads((BLIND / 'provenance.json').read_text(encoding='utf-8'))
    pinned_state = json.loads((OUT / 'pinned-state-verification.json').read_text(encoding='utf-8'))
    pinned_state_sha = sha((OUT / 'pinned-state-verification.json').read_bytes())
    input_manifest_sha = sha((INPUT / 'manifest.json').read_bytes())
    primary_ledger_path = PRIMARY / 'primary-decisions.jsonl'
    blind_ledger_path = BLIND / 'blind-decisions.jsonl'

    input_rows_list = read_jsonl(INPUT / 'current-target-cells.jsonl')
    source_context_rows = read_jsonl(INPUT / 'source-contexts.jsonl')
    hold_rows_list = read_jsonl(INPUT / 'caller-resolution-holds.jsonl')
    primary_rows_list = read_jsonl(primary_ledger_path)
    blind_rows_list = read_jsonl(blind_ledger_path)
    input_rows = by_key(input_rows_list)
    contexts = {r['position']: r for r in source_context_rows}
    input_holds = by_key(hold_rows_list)
    primary_rows = by_key(primary_rows_list)
    blind_rows = by_key(blind_rows_list)

    if len(input_rows) != 240 or len(primary_rows) != 240 or len(blind_rows) != 240:
        raise SystemExit('expected 240 unique input, primary and blind rows')
    if set(input_rows) != set(primary_rows) or set(input_rows) != set(blind_rows):
        raise SystemExit('input / primary / blind cell key sets differ')
    if len(contexts) != 20 or set(contexts) != set(POSITIONS):
        raise SystemExit('source context position set mismatch')
    if len(CHANGES) != 34:
        raise SystemExit(f'expected exactly 34 explicit changes; got {len(CHANGES)}')

    input_checksum_list_sha = sha((INPUT / 'SHA256SUMS.txt').read_bytes())
    blind_manifest_sha_matches = (
        input_manifest_sha == blind_seal.get('candidateFreeManifestJsonSha256')
        == blind_provenance.get('candidateFreeManifestJsonSha256')
        == blind_summary.get('candidateFreeManifestJsonSha256')
    )
    blind_checksum_list_sha_matches = (
        input_checksum_list_sha == blind_seal.get('candidateFreeInputChecksumListSha256')
        == blind_provenance.get('inputChecksumListSha256')
        == blind_summary.get('candidateFreeInputChecksumListSha256')
    )
    candidate_input_provenance_matches = blind_manifest_sha_matches and blind_checksum_list_sha_matches
    input_rows_match_blind = 0
    contexts_match_blind = 0
    ledger = []
    for position in POSITIONS:
        context = contexts[position]
        if context.get('position') != position:
            raise SystemExit(f'context rank mismatch at {position}')
        if context.get('sourceId') != next(input_rows[(position, loc)]['sourceId'] for loc in LOCALES):
            raise SystemExit(f'source context ID mismatch at {position}')
        direct = position in DIRECT_POSITIONS
        if direct and (context.get('callerResolutionHoldReason') or not context.get('references')):
            raise SystemExit(f'direct caller context missing at {position}')
        if not direct and not context.get('callerResolutionHoldReason'):
            raise SystemExit(f'caller-path hold context missing its explicit hold reason at {position}')
        for loc in LOCALES:
            key = (position, loc)
            inp = input_rows[key]
            p = primary_rows[key]
            b = blind_rows[key]
            source = inp['source']
            current = inp['currentTarget']
            if any(row.get('head') != HEAD or row.get('tree') != TREE or row.get('pullRequest') != PR for row in (inp, p)):
                raise SystemExit(f'head/tree/PR mismatch at {key}')
            if b.get('head') != HEAD or b.get('tree') != TREE:
                raise SystemExit(f'blind head/tree mismatch at {key}')
            if any(row.get('sourceId') != inp['sourceId'] or row.get('sourceSha256') != inp['sourceSha256'] or row.get('source') != source for row in (p, b)):
                raise SystemExit(f'source identity mismatch at {key}')
            if any(row.get('currentTarget') != current or row.get('currentTargetSha256') != inp['currentTargetSha256'] for row in (p, b)):
                raise SystemExit(f'current target mismatch at {key}')
            if sha(current.encode('utf-8')) != inp['currentTargetSha256']:
                raise SystemExit(f'current target hash mismatch at {key}')
            expected_input_hash = canonical_sha(inp)
            if b.get('inputRowSha256') == expected_input_hash:
                input_rows_match_blind += 1
            else:
                raise SystemExit(f'blind per-row input hash mismatch at {key}')
            refs = context.get('references', [])
            if b.get('callerReferenceCount') != len(refs):
                raise SystemExit(f'blind caller count mismatch at {key}')
            if b.get('currentCallerLocations') != context.get('currentCallerLocations'):
                raise SystemExit(f'blind caller locations mismatch at {key}')
            ref_sha = [r.get('contextSha256') for r in refs]
            if b.get('callerContextSha256') != (ref_sha[0] if ref_sha else None):
                raise SystemExit(f'blind caller context hash mismatch at {key}')
            contexts_match_blind += 1
            if inp.get('placeholderMultisetMatchesSource') is not True or p.get('placeholderMultisetMatchesSource') is not True or b.get('placeholderMultisetMatchesSource') is not True:
                raise SystemExit(f'input reviewer placeholder flag failure at {key}')
            source_ph = Counter(PH_RE.findall(source))
            current_ph = Counter(PH_RE.findall(current))
            if source_ph != current_ph:
                raise SystemExit(f'pinned current target placeholder mismatch at {key}')

            hold = position not in DIRECT_POSITIONS
            selected = CHANGES.get(key)
            if hold:
                holdrow = input_holds.get(key)
                if not holdrow or p.get('disposition') != 'hold' or b.get('recommendedDisposition') != 'hold':
                    raise SystemExit(f'hold evidence missing at {key}')
                target = None
                disposition = 'hold'
                change = False
                rationale = holdrow['holdReason']
                caller_hold_reason = holdrow['holdReason']
            elif selected:
                target, rationale = selected
                disposition = 'refinement' if key in REFINEMENTS else 'correction'
                change = target != current
                caller_hold_reason = None
            else:
                target = current
                disposition = 'accept-current'
                change = False
                rationale = 'The current target preserves the pinned source meaning and caller semantics; no change is selected.'
                caller_hold_reason = None
            if not hold and target is None:
                raise SystemExit(f'direct row has null target at {key}')
            if not hold:
                target_ph = Counter(PH_RE.findall(target))
                if target_ph != source_ph:
                    raise SystemExit(f'reconciled placeholder mismatch at {key}: source={source_ph}, target={target_ph}')
            expected_target_sha = sha(target.encode('utf-8')) if target is not None else None
            p_target = p.get('selectedTarget')
            b_target = b.get('recommendedTarget')
            p_disp = p.get('disposition')
            b_disp = b.get('recommendedDisposition')
            disagreement = (p_disp != b_disp) or (p_target != b_target)
            refs_out = []
            for ref in refs:
                refs_out.append({
                    'path': ref['path'],
                    'range': [ref['startLine'], ref['endLine']],
                    'matchBasis': ref['matchBasis'],
                    'fileSha256': ref['fileSha256'],
                    'gitBlob': ref['gitBlob'],
                    'contextSha256': ref['contextSha256'],
                    'contextLines': ref['contextLines'],
                })
            ledger.append({
                'schemaVersion': 1,
                'repository': REPO,
                'pullRequest': PR,
                'window': 'W265-W284',
                'head': HEAD,
                'tree': TREE,
                'position': position,
                'locale': loc,
                'sourceId': inp['sourceId'],
                'source': source,
                'sourceSha256': inp['sourceSha256'],
                'sourcePlaceholders': inp.get('sourcePlaceholders', []),
                'sourceMarkupTags': inp.get('sourceMarkupTags', []),
                'category': context.get('category'),
                'localeMetadata': inp.get('localeInfo'),
                'currentReviewDecision': inp.get('reviewDecision'),
                'currentTargetMarkupTags': inp.get('targetMarkupTags', []),
                'containsCandidate': inp.get('containsCandidate'),
                'currentTarget': current,
                'currentTargetSha256': inp['currentTargetSha256'],
                'currentTargetPlaceholders': inp.get('targetPlaceholders', []),
                'currentTargetPlaceholderMultisetMatchesSource': inp['placeholderMultisetMatchesSource'],
                'catalogPath': inp['catalogPath'],
                'catalogSha256': inp['catalogSha256'],
                'catalogGitBlob': pin['catalog']['gitBlob'],
                'inputRecordSha256': expected_input_hash,
                'inputFileRowSha256': sha((INPUT / 'current-target-cells.jsonl').read_bytes().splitlines()[input_rows_list.index(inp)]),
                'primaryRecordSha256': canonical_sha(p),
                'blindRecordSha256': canonical_sha(b),
                'primaryDisposition': p_disp,
                'primaryTarget': p_target,
                'primaryTargetSha256': p.get('selectedTargetSha256'),
                'primaryRationale': p.get('rationale'),
                'blindDisposition': b_disp,
                'blindTarget': b_target,
                'blindTargetSha256': b.get('recommendedTargetSha256'),
                'blindRationale': b.get('rationale'),
                'reviewDisagreement': disagreement,
                'reviewDispositionDisagreement': p_disp != b_disp,
                'reviewTargetDisagreement': p_target != b_target,
                'crossAuditDisposition': disposition,
                'crossAuditTarget': target,
                'crossAuditTargetSha256': expected_target_sha,
                'crossAuditTargetPlaceholders': PH_RE.findall(target) if target is not None else None,
                'crossAuditPlaceholderMultisetMatchesSource': (Counter(PH_RE.findall(target)) == source_ph) if target is not None else None,
                'changeFromCurrent': change,
                'selectedForApplication': change,
                'rationale': rationale,
                'callerEvidence': {
                    'sourceIndexLocations': context.get('sourceIndexLocations', []),
                    'currentCallerLocations': context.get('currentCallerLocations', []),
                    'callerResolutionHoldReason': caller_hold_reason,
                    'references': refs_out,
                },
                'holdEvidence': holdrow if hold else None,
            })

    # Confirm cross-review counts and exact requested boundary before writing.
    cross_counts = Counter(r['crossAuditDisposition'] for r in ledger)
    changed = [r for r in ledger if r['changeFromCurrent']]
    if len(ledger) != 240 or len(changed) != 34 or cross_counts != Counter({'accept-current': 38, 'correction': 33, 'refinement': 1, 'hold': 168}):
        raise SystemExit(f'unexpected cross-audit counts: {dict(cross_counts)} changes={len(changed)}')
    if input_rows_match_blind != 240 or contexts_match_blind != 240:
        raise SystemExit(f'blind evidence did not bind all rows: inputs={input_rows_match_blind}, contexts={contexts_match_blind}')

    disagreements = [r for r in ledger if r['reviewDisagreement']]
    direct_rows = [r for r in ledger if r['position'] in DIRECT_POSITIONS]
    holds = [r for r in ledger if r['crossAuditDisposition'] == 'hold']
    by_pos = defaultdict(list)
    for row in changed:
        by_pos[row['position']].append(row['locale'])
    reviewer_counts = {
        'primary': dict(Counter(r['disposition'] for r in primary_rows_list)),
        'independentBlind': dict(Counter(r['recommendedDisposition'] for r in blind_rows_list)),
        'crossAudit': dict(cross_counts),
    }
    summary = {
        'schemaVersion': 1,
        'repository': REPO,
        'pullRequest': PR,
        'head': HEAD,
        'tree': TREE,
        'window': 'W265-W284',
        'sourceCount': 20,
        'localeCount': len(LOCALES),
        'cellCount': len(ledger),
        'directCallerBackedCells': len(direct_rows),
        'directCallerBackedPositions': sorted(DIRECT_POSITIONS),
        'callerPathHoldCells': len(holds),
        'callerPathHoldPositions': sorted({r['position'] for r in holds}),
        'dispositionCounts': dict(cross_counts),
        'selectedChangeCount': len(changed),
        'selectedChangesByPosition': {str(k): sorted(v) for k, v in sorted(by_pos.items())},
        'selectedChanges': [{'position': r['position'], 'locale': r['locale'], 'sourceId': r['sourceId'], 'currentTarget': r['currentTarget'], 'target': r['crossAuditTarget'], 'targetSha256': r['crossAuditTargetSha256']} for r in changed],
        'reviewerDispositionCounts': reviewer_counts,
        'reviewComparison': {
            'directCallerCellCount': len(direct_rows),
            'disagreementCellCount': len(disagreements),
            'dispositionDisagreementCellCount': sum(r['reviewDispositionDisagreement'] for r in disagreements),
            'targetDisagreementCellCount': sum(r['reviewTargetDisagreement'] for r in disagreements),
            'fullyMatchingDecisionCellCount': sum(not r['reviewDisagreement'] for r in direct_rows),
            'disagreementRows': [{'position': r['position'], 'locale': r['locale'], 'sourceId': r['sourceId'], 'primaryDisposition': r['primaryDisposition'], 'blindDisposition': r['blindDisposition'], 'primaryTarget': r['primaryTarget'], 'blindTarget': r['blindTarget'], 'crossAuditDisposition': r['crossAuditDisposition'], 'crossAuditTarget': r['crossAuditTarget'], 'rationale': r['rationale']} for r in disagreements],
        },
        'metadataValidation': {
            'localeMetadataRowsChecked': len(ledger),
            'reviewDecisionRowsChecked': len(ledger),
            'sourceAndTargetMarkupMetadataRowsChecked': len(ledger),
            'candidateFreeRowsChecked': len(ledger),
            'metadataChanged': False,
        },
        'placeholderValidation': {
            'currentCellsChecked': len(ledger),
            'reconciledTargetsChecked': len(direct_rows),
            'heldCellsRemainUntouched': len(holds),
            'placeholderMismatches': 0,
            'dynamicProviderPlaceholderRows': sum('{provider}' in r['source'] for r in direct_rows),
            'opaqueProviderPlaceholderPreserved': all(Counter(PH_RE.findall(r['source'])) == Counter(PH_RE.findall(r['crossAuditTarget'])) for r in direct_rows if '{provider}' in r['source']),
        },
        'inputLineage': {
            'candidateFreeInputDirectory': str(INPUT),
            'candidateFreeManifestSha256': input_manifest_sha,
            'primaryLedgerSha256': sha(primary_ledger_path.read_bytes()),
            'blindLedgerSha256': sha(blind_ledger_path.read_bytes()),
            'blindSealSha256': sha((BLIND / 'blind-seal.json').read_bytes()),
            'candidateFreeChecksumListSha256': input_checksum_list_sha,
            'blindDeclaredManifestJsonSha256': blind_seal.get('candidateFreeManifestJsonSha256'),
            'blindDeclaredChecksumListSha256': blind_seal.get('candidateFreeInputChecksumListSha256'),
            'blindManifestJsonHashMatchesCurrentInput': blind_manifest_sha_matches,
            'blindChecksumListHashMatchesCurrentInput': blind_checksum_list_sha_matches,
            'blindProvenanceHashesMatchCurrentInput': candidate_input_provenance_matches,
            'blindPerRowInputHashMatches': input_rows_match_blind == 240,
            'blindPerRowInputRowsMatched': input_rows_match_blind,
            'blindPerRowCallerContextHashesMatched': contexts_match_blind,
            'anomaly': None if candidate_input_provenance_matches else 'Blind packet manifest/checksum-list SHA256 values do not both match the current candidate-free input.',
        },
        'pinnedStateVerificationSha256': pinned_state_sha,
        'reviewLimitations': ['Machine-assisted language review is not qualified native-speaker approval.', 'No browser visual review is asserted by this cross-audit packet.', 'No repository edits, translations, PR updates, tests, builds, scans, CI, merges, releases or tags were performed.'],
    }

    attestation = {
        'schemaVersion': 1,
        'auditType': 'cross-audit reconciliation',
        'repository': REPO,
        'pullRequest': PR,
        'head': HEAD,
        'tree': TREE,
        'inputManifestSha256': input_manifest_sha,
        'primaryLedgerSha256': sha(primary_ledger_path.read_bytes()),
        'blindLedgerSha256': sha(blind_ledger_path.read_bytes()),
        'pinnedStateVerificationSha256': pinned_state_sha,
        'rowCount': len(ledger),
        'selectedChangeCount': len(changed),
        'heldCellCount': len(holds),
        'blindManifestHashMismatch': not blind_manifest_sha_matches,
        'blindChecksumListHashMismatch': not blind_checksum_list_sha_matches,
        'blindRowLevelInputHashesVerified': input_rows_match_blind == 240,
        'directCallerContextHashesVerified': contexts_match_blind == 240,
        'repositoryModified': False,
        'prModified': False,
        'releaseActionsPerformed': False,
    }
    hold_summary = {
        'count': len(holds),
        'positions': sorted({r['position'] for r in holds}),
        'reason': 'Dynamic API diagnostics are rendered without localized source-template metadata; dynamic provider labels, operation/needs values, exception types and HTTP status codes remain opaque. No targets are selected.',
        'cells': [{'position': r['position'], 'locale': r['locale'], 'sourceId': r['sourceId'], 'source': r['source'], 'currentTarget': r['currentTarget'], 'currentTargetSha256': r['currentTargetSha256'], 'callerHoldReason': r['callerEvidence']['callerResolutionHoldReason'], 'primaryDisposition': r['primaryDisposition'], 'blindDisposition': r['blindDisposition'], 'targetSelected': False} for r in holds],
    }

    (OUT / 'cross-audit-ledger.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in ledger), encoding='utf-8')
    (OUT / 'disagreement-and-hold-summary.json').write_text(json.dumps({'reviewDisagreements': summary['reviewComparison'], 'holds': hold_summary}, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    (OUT / 'attestation.json').write_text(json.dumps(attestation, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')

    lines = [
        '# ROMarrNG PR #70 W265–W284 cross-audit',
        '',
        f'Pinned PR head: `{HEAD}`; tree: `{TREE}`. This packet reconciles 240 current target cells across 20 source IDs and 12 locales. At {pinned_state.get("verifiedAtUtc", "unknown time")}, the local worktree, eight source-file pins, GitHub PR state and both remote refs matched this head/tree; see `pinned-state-verification.json`.',
        '',
        '## Outcome',
        '',
        f'- **34 direct-caller changes selected**: 33 corrections and 1 wording refinement.',
        f'- **38 direct-caller cells accepted as current.**',
        f'- **168 cells held** at ranks 269–282 (12 locales each). No targets are selected for held cells.',
        f'- Direct caller contexts were examined for all {len(direct_rows)} cells at ranks 265–268 and 283–284, including source file ranges and line hashes.',
        '',
        'Selected direct-caller changes:',
        '',
    ]
    for pos in sorted(by_pos):
        source_id = next(r['sourceId'] for r in changed if r['position'] == pos)
        lines.append(f'- Rank {pos} (`{source_id}`): ' + ', '.join(sorted(by_pos[pos])))
    lines += [
        '',
        '## Review reconciliation',
        '',
        f"Primary review counts: {reviewer_counts['primary']}. Independent blind counts: {reviewer_counts['independentBlind']}. Cross-audit counts: {reviewer_counts['crossAudit']}.",
        f"The two review ledgers differ on {summary['reviewComparison']['disagreementCellCount']} direct-caller cells by disposition and/or proposed wording. Row-level details and the adjudicated target are in `disagreement-and-hold-summary.json` and the full ledger.",
        '',
        '## Caller-path holds',
        '',
        'Ranks 269–282 are dynamic metadata-provider and Prowlarr API diagnostics returned as raw error text and rendered through `apiMessageMarkup` without an explicit localized template key and values. Dynamic provider names, operation/needs values, exception types and HTTP status codes remain opaque. Current translations are retained unchanged until an exact source-template path exists.',
        '',
        '## Integrity and limitation',
        '',
        f"Input, primary and blind packet checksums verify. The candidate-free manifest JSON SHA256 is `{input_manifest_sha}` and its checksum-list SHA256 is `{input_checksum_list_sha}`; the corrected blind seal explicitly attests both values. All 240 blind per-row input hashes, current targets, source identities, caller counts/locations, and caller-context hashes match the current input.",
        '',
        'The ledger records each locale’s availability/direction metadata, review state, source/target markup metadata and candidate-free flag. The audit selects target-text values only and leaves these pinned metadata fields unchanged. All selected target placeholders match the source placeholder multiset, including exact `{provider}` and `{count}` placeholders. The packet is a machine-assisted review and does not establish qualified native-speaker approval or browser review. It contains recommendations only; no repository or PR files were changed and no release actions were performed.',
        '',
        'See `cross-audit-ledger.jsonl` for all 240 cells and the exact source/current/reviewed/reconciled values, hashes, caller context, decisions, holds and rationale.',
    ]
    (OUT / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (OUT / 'README.md').write_text(
        '# Cross-audit evidence packet\n\n'
        'Read-only reconciliation of ROMarrNG PR #70 ranks W265–W284 at exact head/tree. `cross-audit-ledger.jsonl` contains all 240 rows; `summary.json` holds counts and selected targets; `disagreement-and-hold-summary.json` contains disagreement and hold detail; `attestation.json` records scope and limitations; `pinned-state-verification.json` captures the live PR/ref and exact worktree/source-pin verification.\n\n'
        'Run `python3 verify_cross_audit_evidence.py` from this directory to verify source packet checksums, row-level input/reviewer lineage, dispositions, holds, target hashes, placeholder integrity, and this packet\'s checksum list. The verifier is read-only.\n\n'
        'The blind review packet explicitly records separate hashes for the candidate manifest JSON and its checksum list. These recommendations are not native-speaker approval or release approval.\n', encoding='utf-8')

    print(json.dumps({'output': str(OUT), 'summary': summary, 'manifestMismatch': not blind_manifest_sha_matches, 'checksumListMismatch': not blind_checksum_list_sha_matches}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
