#!/usr/bin/env python3
"""Build the W585-W604 blind decision packet from the candidate-free inputs."""
import collections
import hashlib
import json
from pathlib import Path

INPUT = Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w585-604-current-candidate-free-20261104/candidate-free/input')
OUT = Path(__file__).resolve().parent
HEAD = '01da053f0e6a47e7184fb86da77f66b7b6719653'
TREE = 'dcb9c1766831e217ffca7fb77068b97c33b9524e'
BRANCH = 'task/localization-translation-review-20261030'
BASE_SHA = 'bcd1eb41b5cdf8202acb5cf8e365e14761b743b5'

PROPOSALS = {
    ('ui.ko-fi.76c38e42cf', 'pt-BR'): (
        'Ko-fi',
        'The caller presents the service name as a standalone brand label. Drop the extra trailing period.',
        'high',
    ),
    ('ui.lynx-header.83b04c6319', 'vi'): (
        'Đầu tệp LYNX',
        '`Tiêu đề` means a title; the caller identifies a ROM file signature header. Use a term for the file header.',
        'high',
    ),
    ('ui.last-ran.2e024dc014', 'ja'): (
        '最終実行',
        'This is a task-table column indicating the most recent execution. `最終実行` labels that directly; `最後のラン` is an unnatural calque.',
        'moderate',
    ),
    ('ui.last-ran.2e024dc014', 'vi'): (
        'Lần chạy gần nhất',
        'This is a task-table heading for the most recent run; the current wording reads like an imperative. Use a noun phrase.',
        'high',
    ),
    ('ui.last-refresh.519ad138a1', 'hi'): (
        'पिछला रीफ़्रेश:',
        'In the error-status label, `पिछला रीफ़्रेश` names the most recent refresh; the current wording shifts toward a fresh check.',
        'moderate',
    ),
    ('ui.last-refresh.519ad138a1', 'vi'): (
        'Lần làm mới gần nhất:',
        'The caller introduces the most recent refresh error; the current wording reads like a verb phrase. Use a noun phrase.',
        'high',
    ),
    ('ui.latest-listed-version-only.1df61faba4', 'id'): (
        'Hanya versi terbaru yang terdaftar',
        'The current word order is unnatural. This phrasing clearly means only the latest listed version.',
        'high',
    ),
    ('ui.latest-listed-version-only.1df61faba4', 'ko'): (
        '목록에 있는 최신 버전만',
        'The source means the latest version in the list, not the version registered most recently. Clarify the list relation.',
        'moderate',
    ),
}
LEFT_REMAINING = {
    'ar': 'المتبقي',
    'de': 'Verbleibend',
    'es': 'Restantes',
    'fr': 'Restants',
    'hi': 'शेष',
    'id': 'Tersisa',
    'ja': '残り',
    'ko': '남은 수',
    'pt-BR': 'Restantes',
    'vi': 'Còn lại',
    'zh-Hans': '剩余',
    'zh-Hant': '剩餘',
}
LEFT_RATIONALE = 'The pinned caller is a numeric progress table with Done and Failed columns; Left means the remaining count, not a direction.'


def load_json(name):
    return json.loads((INPUT / name).read_text(encoding='utf-8'))


def load_jsonl(name):
    return [json.loads(line) for line in (INPUT / name).read_text(encoding='utf-8').splitlines() if line.strip()]


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def verify_input_checksums():
    for line in (INPUT / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        expected, name = line.split(None, 1)
        name = name.strip().lstrip('*')
        actual = hashlib.sha256((INPUT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f'input checksum mismatch: {name}')


def main():
    verify_input_checksums()
    selection = load_json('selection.json')
    contexts = {r['sourceId']: r for r in load_jsonl('source-contexts.jsonl')}
    cells = load_jsonl('current-target-cells.jsonl')
    cell_map = {(r['sourceId'], r['locale']): r for r in cells}
    rows = []
    proposal_counts = collections.Counter()
    hold_sources = set()
    retain_count = 0
    hold_count = 0

    for source in selection['selectedSources']:
        sid = source['sourceId']
        context = contexts[sid]
        callers = context.get('callers', [])
        for locale in selection['localeOrder']:
            cell = cell_map[(sid, locale)]
            key = (sid, locale)
            row = {
                'schemaVersion': 1,
                'catalogPosition': source['position'],
                'catalogOneBasedPosition': source['catalogOneBasedPosition'],
                'sourceId': sid,
                'locale': locale,
                'sourceSha256': source['sourceSha256'],
                'currentTargetSha256': cell['currentTargetSha256'],
                'callerContextSha256': cell['callerContextSha256'],
                'callerRefCount': len(callers),
                'callerless': not bool(callers),
            }
            if not callers:
                row.update({
                    'disposition': 'hold_hash_only',
                    'confidence': 'high',
                    'rationale': 'Callerless source; preserve as a hash-only hold per task instruction.',
                })
                hold_count += 1
                hold_sources.add(sid)
            elif sid == 'ui.left.58eb9032e3':
                target = LEFT_REMAINING[locale]
                row.update({
                    'disposition': 'propose_refinement',
                    'proposedTarget': target,
                    'proposedTargetSha256': digest(target),
                    'confidence': 'high',
                    'rationale': LEFT_RATIONALE,
                })
                proposal_counts[sid] += 1
            elif key in PROPOSALS:
                target, rationale, confidence = PROPOSALS[key]
                row.update({
                    'disposition': 'propose_refinement',
                    'proposedTarget': target,
                    'proposedTargetSha256': digest(target),
                    'confidence': confidence,
                    'rationale': rationale,
                })
                proposal_counts[sid] += 1
            else:
                row.update({
                    'disposition': 'retain_current',
                    'confidence': 'moderate',
                    'rationale': 'No definite semantic correction identified from the pinned caller context.',
                })
                retain_count += 1
            rows.append(row)

    assert len(rows) == 240
    assert retain_count == 196 and hold_count == 24
    assert sum(proposal_counts.values()) == 20
    OUT.joinpath('blind-decisions.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows), encoding='utf-8')

    summary = {
        'schemaVersion': 1,
        'review': 'ROMarrNG PR #70 W585-W604 strict blind semantic review',
        'reviewedUtc': '2026-11-04T18:09:56Z',
        'pin': {
            'repository': 'snapetech-org/ROMarrNG',
            'pullRequest': 70,
            'state': 'open',
            'draft': True,
            'head': HEAD,
            'tree': TREE,
            'branch': BRANCH,
            'pullRef': 'refs/pull/70/head',
            'baseRef': 'main',
            'baseSha': BASE_SHA,
            'postReviewReattestation': 'pass; API, branch ref, pull ref, and worktree head/tree matched the pin after review',
        },
        'input': {
            'path': str(INPUT),
            'verifier': 'PASS',
            'cellCount': 240,
            'sourceCount': 20,
            'localeCount': 12,
            'localeOrder': selection['localeOrder'],
            'inputSha256SumsSha256': hashlib.sha256((INPUT / 'SHA256SUMS.txt').read_bytes()).hexdigest(),
            'blindnessManifestSha256': hashlib.sha256((OUT.parent / 'blindness-manifest.json').read_bytes()).hexdigest(),
            'candidateFreeInputVerifierResult': {
                'callerlessCells': 24,
                'callerlessSources': 2,
                'directCallerRefs': 37,
                'tokenMismatches': {'markup': 0, 'missingTarget': 0, 'numeric': 0, 'numericPresentationDifferences': 0, 'placeholder': 0, 'protectedLiteral': 0},
            },
        },
        'coverage': {
            'sourcesWithPinnedCallerContextReviewed': 18,
            'pinnedDirectCallerReferencesConsulted': 37,
            'callerlessSources': sorted(hold_sources),
            'callerlessHashOnlyHoldCells': hold_count,
        },
        'dispositions': {
            'proposeRefinement': sum(proposal_counts.values()),
            'retainCurrent': retain_count,
            'holdHashOnly': hold_count,
            'total': len(rows),
            'proposalCountsBySourceId': dict(sorted(proposal_counts.items())),
        },
        'limitations': {
            'overallConfidence': 'moderate',
            'nativeSpeakerApproval': False,
            'note': 'This is an independent model-assisted semantic pass, not native-speaker approval. Retain-current means no definite correction was identified from the supplied pinned context.',
        },
        'mutations': {
            'repositoryEdits': 0,
            'pullRequestEdits': 0,
            'testsBuildsOrCI': 0,
            'workflowEdits': 0,
            'mergeReleaseOrTag': 0,
        },
    }
    OUT.joinpath('review-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    packet_files = ['build_blind_packet.py', 'blind-decisions.jsonl', 'review-summary.json', 'verify_blind_packet.py']
    file_hashes = {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in packet_files}
    sealed = {
        'schemaVersion': 1,
        'recordType': 'sealed-blind-review-packet',
        'sealedUtc': '2026-11-04T18:12:29Z',
        'pin': {'repository': 'snapetech-org/ROMarrNG', 'pullRequest': 70, 'head': HEAD, 'tree': TREE, 'branch': BRANCH, 'pullRef': 'refs/pull/70/head'},
        'input': {'sha256sumsFileSha256': hashlib.sha256((INPUT / 'SHA256SUMS.txt').read_bytes()).hexdigest(), 'blindnessManifestSha256': hashlib.sha256((OUT.parent / 'blindness-manifest.json').read_bytes()).hexdigest(), 'verifiedInputFileCount': len((INPUT / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines())},
        'files': file_hashes,
    }
    manifest_bytes = (json.dumps(sealed, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')
    OUT.joinpath('sealed-manifest.json').write_bytes(manifest_bytes)
    OUT.joinpath('sealed-manifest.sha256').write_text(hashlib.sha256(manifest_bytes).hexdigest() + '  sealed-manifest.json\n', encoding='ascii')
    print(json.dumps({'rows': len(rows), 'proposals': sum(proposal_counts.values()), 'retains': retain_count, 'hashOnlyHolds': hold_count, 'proposalCountsBySourceId': dict(proposal_counts)}, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
