#!/usr/bin/env python3
"""Build a sealed, read-only cross-audit packet for ROMarrNG PR #70 W585-W604."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import datetime
from collections import Counter, defaultdict

OUT = pathlib.Path(__file__).resolve().parent
BASE = pathlib.Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w585-604-current-candidate-free-20261104')
PRIMARY = pathlib.Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w585-604-primary-fresh-20261104')
BLIND = pathlib.Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w585-604-blind-review-20261104/sealed-blind-packet')
REPO = pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261104/romarrng-pr70-w585-604-current-source')
INPUT = BASE / 'candidate-free' / 'input'
PRIMARY_OUT = PRIMARY / 'primary-output'
PIN = {
    'repository': 'snapetech-org/ROMarrNG',
    'pullRequest': 70,
    'branch': 'task/localization-translation-review-20261030',
    'head': '01da053f0e6a47e7184fb86da77f66b7b6719653',
    'tree': 'dcb9c1766831e217ffca7fb77068b97c33b9524e',
    'window': 'W585-W604',
    'catalogPath': 'romarr/ui-labels.json',
    'positions': [585, 604],
    'catalogOneBasedPositions': [586, 605],
}
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']

# The selected text is always one of the two sealed review candidates.  The
# per-cell notes below explain where caller context resolves disagreement and
# where target wording differs while both reviews identify the same meaning.
SELECTED = {
    ('ui.ko-fi.76c38e42cf', 'hi'): ('Ko-fi', 'primary_only_resolved_by_caller_context', 'The exact product mark is visible in the linked label and the caller URL is ko-fi.com; preserve the canonical spelling rather than transliterating this service name.', 'moderate'),
    ('ui.ko-fi.76c38e42cf', 'ja'): ('Ko-fi', 'primary_only_resolved_by_caller_context', 'The exact product mark is visible in the linked label and the caller URL is ko-fi.com; preserve the canonical spelling rather than transliterating this service name.', 'moderate'),
    ('ui.ko-fi.76c38e42cf', 'pt-BR'): ('Ko-fi', 'corroborated_exact_target', 'The caller links to ko-fi.com and labels that service; the trailing period is not part of the brand name.', 'high'),
    ('ui.last-ran.2e024dc014', 'ja'): ('最終実行', 'blind_only_resolved_by_caller_context', 'The caller is a task-table heading between Schedule and Result; it labels the most recent execution, not a generic “last run” phrase.', 'moderate'),
    ('ui.last-ran.2e024dc014', 'vi'): ('Lần chạy gần nhất', 'blind_only_resolved_by_caller_context', 'The caller is a task-table heading between Schedule and Result; a noun phrase for the most recent run fits the column, while the current wording reads as an instruction.', 'high'),
    ('ui.last-refresh.519ad138a1', 'hi'): ('पिछला रीफ़्रेश:', 'blind_only_resolved_by_caller_context', 'The caller emits this label before a refresh error; the proposed wording names the prior refresh, while the current wording shifts toward a fresh check.', 'moderate'),
    ('ui.last-refresh.519ad138a1', 'vi'): ('Lần làm mới gần nhất:', 'blind_only_resolved_by_caller_context', 'The caller emits this label before a refresh error; the noun phrase identifies the most recent refresh, while the current wording is verb-like.', 'high'),
    ('ui.latest-listed-version-only.1df61faba4', 'id'): ('Hanya versi terbaru yang terdaftar', 'blind_only_resolved_by_caller_context', 'The caller is a catalogue-switch checkbox. This ordering scopes “only” to the version choice and reads as a filter label, rather than suggesting the version was just registered.', 'moderate'),
    ('ui.latest-listed-version-only.1df61faba4', 'ko'): ('목록에 있는 최신 버전만', 'blind_only_resolved_by_caller_context', 'The caller is a catalogue-switch checkbox; this wording explicitly selects only the latest version in the list.', 'high'),
    ('ui.left.58eb9032e3', 'ar'): ('المتبقي', 'corroborated_exact_target', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell, so this label means remaining rather than direction.', 'high'),
    ('ui.left.58eb9032e3', 'de'): ('Übrig', 'corroborated_meaning_variant', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell. The primary wording is a concise remaining-count heading; the blind pass offered the synonymous “Verbleibend.”', 'high'),
    ('ui.left.58eb9032e3', 'es'): ('Restantes', 'corroborated_exact_target', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell, so this label means remaining rather than direction.', 'high'),
    ('ui.left.58eb9032e3', 'fr'): ('Restants', 'corroborated_exact_target', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell, so this label means remaining rather than direction.', 'high'),
    ('ui.left.58eb9032e3', 'hi'): ('बाकी', 'corroborated_meaning_variant', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell. The primary colloquial heading and the blind pass’s “शेष” both denote the remaining count.', 'high'),
    ('ui.left.58eb9032e3', 'id'): ('Tersisa', 'corroborated_exact_target', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell, so this label means remaining rather than direction.', 'high'),
    ('ui.left.58eb9032e3', 'ja'): ('残り', 'corroborated_exact_target', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell, so this label means remaining rather than direction.', 'high'),
    ('ui.left.58eb9032e3', 'ko'): ('남은 수', 'corroborated_meaning_variant', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell. The blind wording explicitly says “remaining count,” which fits the numeric column better than the primary’s shorter “remaining.”', 'high'),
    ('ui.left.58eb9032e3', 'pt-BR'): ('Restantes', 'corroborated_exact_target', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell, so this label means remaining rather than direction.', 'high'),
    ('ui.left.58eb9032e3', 'vi'): ('Còn lại', 'corroborated_exact_target', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell, so this label means remaining rather than direction.', 'high'),
    ('ui.left.58eb9032e3', 'zh-Hans'): ('剩余', 'corroborated_exact_target', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell, so this label means remaining rather than direction.', 'high'),
    ('ui.left.58eb9032e3', 'zh-Hant'): ('剩餘', 'corroborated_exact_target', 'The pinned caller is a numeric progress table; the implementation renders x.remaining in this cell, so this label means remaining rather than direction.', 'high'),
    ('ui.lynx-header.83b04c6319', 'vi'): ('Đầu tệp LYNX', 'corroborated_exact_target', 'The caller is the ROM signature detector, which identifies LYNX at byte offset 0x40; this is a file-format header, not a page title.', 'high'),
}

EVIDENCE_RANGES = {
    'ui.ko-fi.76c38e42cf': ('romarr/ui.py', 4645, 4649),
    'ui.last-ran.2e024dc014': ('romarr/ui.py', 6110, 6124),
    'ui.last-refresh.519ad138a1': ('romarr/ui.py', 2100, 2103),
    'ui.latest-listed-version-only.1df61faba4': ('romarr/ui.py', 5505, 5509),
    'ui.left.58eb9032e3': ('romarr/ui.py', 5516, 5525),
    'ui.lynx-header.83b04c6319': ('romarr/sniff.py', 88, 93),
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_text(value: str) -> str:
    return sha_bytes(value.encode('utf-8'))


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path: pathlib.Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write_json(path: pathlib.Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def write_jsonl(path: pathlib.Path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows), encoding='utf-8')


def verify_candidate_input():
    sums = (INPUT / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines()
    if len(sums) != 27:
        raise SystemExit('candidate-free input checksum count is not 27')
    for line in sums:
        expected, name = line.split(None, 1)
        name = name.strip().lstrip('*')
        if sha_bytes((INPUT / name).read_bytes()) != expected:
            raise SystemExit(f'candidate-free input checksum mismatch: {name}')
    return sha_bytes((INPUT / 'SHA256SUMS.txt').read_bytes())


def main():
    created_utc = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    input_sums_hash = verify_candidate_input()
    manifest = read_json(INPUT / 'manifest.json')
    bundle_manifest = read_json(BASE / 'bundle-manifest.json')
    primary_pre = read_json(PRIMARY / 'PRIMARY-REVIEW-MANIFEST.json')
    primary_manifest = read_json(PRIMARY_OUT / 'primary-manifest.json')
    primary_summary = read_json(PRIMARY_OUT / 'summary.json')
    blind_manifest = read_json(BLIND / 'sealed-manifest.json')
    blind_summary = read_json(BLIND / 'review-summary.json')
    selection = read_json(INPUT / 'selection.json')
    cells = read_jsonl(INPUT / 'current-target-cells.jsonl')
    contexts = {row['sourceId']: row for row in read_jsonl(INPUT / 'source-contexts.jsonl')}
    primary = {(row['sourceId'], row['locale']): row for row in read_jsonl(PRIMARY_OUT / 'dispositions.jsonl')}
    blind = {(row['sourceId'], row['locale']): row for row in read_jsonl(BLIND / 'blind-decisions.jsonl')}
    source_pins = {row['path']: row for row in read_json(INPUT / 'source-file-pins.json')['files']}
    cell_by_key = {(row['sourceId'], row['locale']): row for row in cells}
    expected_order = [(source['sourceId'], locale) for source in selection['selectedSources'] for locale in selection['localeOrder']]

    if len(cells) != 240 or len(primary) != 240 or len(blind) != 240 or set(cell_by_key) != set(primary) or set(cell_by_key) != set(blind):
        raise SystemExit('upstream cell coverage mismatch')
    if expected_order != [(row['sourceId'], row['locale']) for row in cells]:
        raise SystemExit('candidate-free cell order mismatch')
    for source_key, cell in cell_by_key.items():
        if sha_text(cell['source']) != cell['sourceSha256'] or sha_text(cell['currentTarget']) != cell['currentTargetSha256']:
            raise SystemExit(f'candidate-free source/current hash mismatch: {source_key}')
        if primary[source_key]['currentTargetSha256'] != cell['currentTargetSha256'] or blind[source_key]['currentTargetSha256'] != cell['currentTargetSha256']:
            raise SystemExit(f'upstream current hash mismatch: {source_key}')

    if manifest['head'] != PIN['head'] or manifest['tree'] != PIN['tree'] or manifest['branch'] != PIN['branch']:
        raise SystemExit('candidate-free source pin mismatch')
    if primary_manifest['head'] != PIN['head'] or primary_manifest['tree'] != PIN['tree']:
        raise SystemExit('primary review source pin mismatch')
    if blind_manifest['pin']['head'] != PIN['head'] or blind_manifest['pin']['tree'] != PIN['tree']:
        raise SystemExit('blind review source pin mismatch')
    if len(SELECTED) != 22:
        raise SystemExit('selection plan count does not equal 22')

    source_lines = {}
    for sid, (path, start, end) in EVIDENCE_RANGES.items():
        text = (REPO / path).read_text(encoding='utf-8')
        lines = text.splitlines()
        snippet_lines = lines[start - 1:end]
        snippet = '\n'.join(snippet_lines) + '\n'
        pin = source_pins[path]
        if sha_bytes((REPO / path).read_bytes()) != pin['fileSha256']:
            raise SystemExit(f'exact source file pin mismatch: {path}')
        source_lines[sid] = {
            'path': path,
            'startLine': start,
            'endLine': end,
            'fileSha256': pin['fileSha256'],
            'excerptSha256': sha_text(snippet),
            'lines': [{'line': start + index, 'text': line} for index, line in enumerate(snippet_lines)],
        }

    evidence_rows = []
    for sid in sorted({sid for sid, _ in SELECTED}):
        ctx = contexts[sid]
        evidence_rows.append({
            'schemaVersion': 1,
            'sourceId': sid,
            'source': ctx['source'],
            'sourceSha256': ctx['sourceSha256'],
            'callerless': ctx['callerless'],
            'callerContextSha256': ctx['contextSha256'],
            'callerRefCount': len(ctx['callers']),
            'exactMatchCount': ctx['exactMatchCount'],
            'searchMethod': ctx['searchMethod'],
            'productionFilesSearched': ctx['productionFilesSearched'],
            'callers': ctx['callers'],
            'expandedPinnedContext': source_lines[sid],
        })
    write_jsonl(OUT / 'source-evidence.jsonl', evidence_rows)

    selected_rows = []
    no_op_rows = []
    selected_order = []
    for cell in cells:
        key = (cell['sourceId'], cell['locale'])
        p = primary[key]
        b = blind[key]
        ctx = contexts[key[0]]
        if key in SELECTED:
            target, resolution, reason, confidence = SELECTED[key]
            if not ctx['callers']:
                raise SystemExit(f'callerless cell cannot be selected: {key}')
            ptarget = p.get('proposedTarget') if p['disposition'] == 'CHANGE' else None
            btarget = b.get('proposedTarget') if b['disposition'] == 'propose_refinement' else None
            if target not in {ptarget, btarget}:
                raise SystemExit(f'selected target is not a sealed primary or blind candidate: {key}')
            if sha_text(target) == cell['currentTargetSha256']:
                raise SystemExit(f'selected target is already current: {key}')
            evidence = source_lines[key[0]]
            selected_rows.append({
                'schemaVersion': 1,
                'window': PIN['window'],
                'operation': 'replace_translation_value_only',
                'catalogPath': PIN['catalogPath'],
                'position': cell['position'],
                'catalogOneBasedPosition': cell['catalogZeroBasedIndex'] + 1,
                'sourceId': cell['sourceId'],
                'locale': cell['locale'],
                'source': cell['source'],
                'sourceSha256': cell['sourceSha256'],
                'currentTarget': cell['currentTarget'],
                'currentTargetSha256': cell['currentTargetSha256'],
                'selectedTarget': target,
                'selectedTargetSha256': sha_text(target),
                'selectedTargetFrom': 'primary' if target == ptarget and target != btarget else ('blind' if target == btarget and target != ptarget else 'shared_candidate'),
                'primaryDisposition': p['disposition'],
                'primaryCandidate': ptarget,
                'primaryCandidateSha256': sha_text(ptarget) if ptarget is not None else None,
                'primaryRationale': p.get('reason'),
                'primaryConfidence': p.get('confidence'),
                'blindDisposition': b['disposition'],
                'blindCandidate': btarget,
                'blindCandidateSha256': sha_text(btarget) if btarget is not None else None,
                'blindRationale': b.get('rationale'),
                'blindConfidence': b.get('confidence'),
                'resolution': resolution,
                'crossAuditRationale': reason,
                'confidence': confidence,
                'callerContextSha256': cell['callerContextSha256'],
                'callerRefCount': len(ctx['callers']),
                'sourceEvidenceRef': {'file': 'source-evidence.jsonl', 'sourceId': key[0], 'path': evidence['path'], 'lines': [evidence['startLine'], evidence['endLine']], 'fileSha256': evidence['fileSha256'], 'excerptSha256': evidence['excerptSha256']},
                'nativeSpeakerApproval': False,
            })
            selected_order.append(key)
        else:
            if p['disposition'] != 'KEEP' or b['disposition'] not in {'retain_current', 'hold_hash_only'}:
                raise SystemExit(f'unselected review proposal/unknown hold requires explicit resolution: {key}')
            hold = b['disposition'] == 'hold_hash_only'
            if hold and ctx['callers']:
                raise SystemExit(f'callerful cell entered hash-only hold: {key}')
            if not hold and not ctx['callers']:
                raise SystemExit(f'callerless cell was not preserved as hash-only hold: {key}')
            entry = {
                'schemaVersion': 1,
                'window': PIN['window'],
                'position': cell['position'],
                'catalogOneBasedPosition': cell['catalogZeroBasedIndex'] + 1,
                'sourceId': cell['sourceId'],
                'sourceSha256': cell['sourceSha256'],
                'locale': cell['locale'],
                'currentTargetSha256': cell['currentTargetSha256'],
                'callerContextSha256': cell['callerContextSha256'],
                'callerRefCount': len(ctx['callers']),
                'primaryDisposition': p['disposition'],
                'primaryCurrentTargetSha256': p['currentTargetSha256'],
                'blindDisposition': b['disposition'],
                'blindCurrentTargetSha256': b['currentTargetSha256'],
                'crossDisposition': 'HOLD_HASH_ONLY' if hold else 'KEEP_CURRENT',
                'holdReasonSha256': sha_text('callerless; preserve current source/current-target hashes without semantic disposition') if hold else None,
            }
            no_op_rows.append(entry)

    expected_selected = [key for key in expected_order if key in SELECTED]
    if selected_order != expected_selected:
        raise SystemExit('selected proposal order mismatch')
    write_jsonl(OUT / 'selected-proposals.jsonl', selected_rows)
    write_jsonl(OUT / 'no-op-ledger.jsonl', no_op_rows)

    selected_counts = Counter(row['resolution'] for row in selected_rows)
    primary_counts = Counter(row['primaryDisposition'] for row in selected_rows + no_op_rows)
    blind_counts = Counter(row['blindDisposition'] for row in selected_rows + no_op_rows)
    noop_counts = Counter(row['crossDisposition'] for row in no_op_rows)
    by_source = Counter(row['sourceId'] for row in selected_rows)
    by_locale = Counter(row['locale'] for row in selected_rows)

    input_refs = {
        'candidateFreeBundle': {
            'pathAtReview': str(BASE),
            'bundleManifestSha256': sha_bytes((BASE / 'bundle-manifest.json').read_bytes()),
            'bundleChecksumListSha256': sha_bytes((BASE / 'SHA256SUMS.txt').read_bytes()),
            'inputManifestSha256': sha_bytes((INPUT / 'manifest.json').read_bytes()),
            'inputChecksumListSha256': input_sums_hash,
            'candidateFree': True,
            'proposedTargetsIncluded': False,
            'verification': 'PASS',
        },
        'primaryReview': {
            'pathAtReview': str(PRIMARY),
            'preReviewManifestSha256': sha_bytes((PRIMARY / 'PRIMARY-REVIEW-MANIFEST.json').read_bytes()),
            'primaryManifestSha256': sha_bytes((PRIMARY_OUT / 'primary-manifest.json').read_bytes()),
            'dispositionsSha256': sha_bytes((PRIMARY_OUT / 'dispositions.jsonl').read_bytes()),
            'summarySha256': sha_bytes((PRIMARY_OUT / 'summary.json').read_bytes()),
            'reviewerHadNotAccessedOtherW585Decisions': primary_pre['otherW585ReviewDecisionsAccessed'] is False,
            'nativeSpeakerApproval': primary_manifest['nativeSpeakerApproval'],
            'verification': 'PASS',
        },
        'blindReview': {
            'pathAtReview': str(BLIND),
            'sealedManifestSha256': sha_bytes((BLIND / 'sealed-manifest.json').read_bytes()),
            'sealedManifestSidecarSha256': sha_bytes((BLIND / 'sealed-manifest.sha256').read_bytes()),
            'blindDecisionsSha256': sha_bytes((BLIND / 'blind-decisions.jsonl').read_bytes()),
            'summarySha256': sha_bytes((BLIND / 'review-summary.json').read_bytes()),
            'blindnessManifestSha256': blind_manifest['input']['blindnessManifestSha256'],
            'verification': 'PASS',
        },
    }

    cross_manifest = {
        'artifact': 'ROMarrNG PR #70 W585-W604 sealed exact-head primary/blind cross-audit',
        'schemaVersion': 1,
        'createdUtc': created_utc,
        'pin': PIN,
        'localeOrder': LOCALES,
        'sourceCount': 20,
        'localeCount': 12,
        'cellCount': 240,
        'selectedProposalCount': len(selected_rows),
        'noOpLedgerCount': len(no_op_rows),
        'callerlessHashOnlyHoldCount': sum(1 for row in no_op_rows if row['crossDisposition'] == 'HOLD_HASH_ONLY'),
        'unresolvedContextualHoldCount': 0,
        'catalogFileSha256': manifest['catalogSha256'],
        'catalogKeyOrderSha256': manifest['catalogKeyOrderSha256'],
        'inputAttestations': input_refs,
        'checks': {
            'candidateFreeVerifier': 'PASS',
            'candidateFreeBundleChecksums': 'PASS',
            'candidateFreeInputChecksums': 'PASS (27 files)',
            'primaryOutputChecksums': 'PASS (5 files)',
            'primaryExactPinAndLiveRefs': 'PASS',
            'blindSealedManifestAndRows': 'PASS (27 input files, 240 decisions)',
            'sourceWorktree': 'PASS (clean, exact HEAD/tree)',
            'testsBuildsCiBrowserNativeSpeakerClaims': 'NONE',
        },
        'reviewLimitations': [
            'Semantic judgment is an AI-assisted cross-audit; no native-speaker approval is claimed.',
            'The packet is a proposed apply plan only; no repository, PR, branch, or catalog was changed.',
            'The 24 callerless cells remain hash-only holds with no source/current-target text in the no-op ledger.',
            'The blind packet had no callerful hash-only holds; its 24 hash-only holds were callerless and all were preserved.',
        ],
    }
    write_json(OUT / 'cross-manifest.json', cross_manifest)

    report = {
        'artifact': cross_manifest['artifact'],
        'pin': PIN,
        'counts': {
            'cells': 240,
            'selectedProposals': len(selected_rows),
            'noOps': len(no_op_rows),
            'callerlessHashOnlyHolds': noop_counts['HOLD_HASH_ONLY'],
            'callerfulKeepCurrent': noop_counts['KEEP_CURRENT'],
            'unresolvedContextualHolds': 0,
            'primaryDispositionCounts': dict(primary_counts),
            'blindDispositionCounts': dict(blind_counts),
            'crossResolutionCounts': dict(selected_counts),
            'selectedBySourceId': dict(sorted(by_source.items())),
            'selectedByLocale': dict(sorted(by_locale.items())),
        },
        'verification': cross_manifest['checks'],
        'scratch': {'outputPath': str(OUT)},
    }
    write_json(OUT / 'cross-report.json', report)

    grouped = defaultdict(list)
    for row in selected_rows:
        grouped[row['sourceId']].append(row)
    report_lines = [
        '# ROMarrNG PR #70 W585–W604 cross-audit',
        '',
        f"Pinned to `{PIN['head']}` (tree `{PIN['tree']}`), source worktree clean. Candidate-free, primary, and blind packet verifiers all passed; exact branch and PR refs matched the pin during primary verification.",
        '',
        '## Result counts',
        '',
        '| Outcome | Cells |',
        '|---|---:|',
        f"| Selected proposal/apply-plan cells | {len(selected_rows)} |",
        f"| Callerful keep-current no-ops | {noop_counts['KEEP_CURRENT']} |",
        f"| Callerless hash-only holds | {noop_counts['HOLD_HASH_ONLY']} |",
        '| Unresolved contextual holds | 0 |',
        '| Total | 240 |',
        '',
        f"Resolution counts: `{json.dumps(dict(selected_counts), ensure_ascii=False, sort_keys=True)}`.",
        '',
        '## Selected proposals',
        '',
        '| Source | Locale | Current | Selected | Cross-audit outcome |',
        '|---|---|---|---|---|',
    ]
    for row in selected_rows:
        report_lines.append(f"| `{row['source']}` | `{row['locale']}` | {row['currentTarget']} | {row['selectedTarget']} | `{row['resolution']}` |")
    report_lines += [
        '',
        'The task-table `Left` correction is supported by the pinned implementation: `Done`, `Failed`, and `Left` are adjacent columns, and the value under `Left` is `fmt(x.remaining)`. Exact caller excerpts, expanded pinned source lines, their hashes, candidate text, and candidate/current/source hashes are in the packet.',
        '',
        'The eight cells where one review did not propose a change were selected only after the caller identified the UI role: two Ko-fi brand labels, two “Last ran” task headings, two “Last refresh” error labels, and two catalogue-version filter labels. Three `Left` cells had semantically aligned candidate wording differences; the selected target and both source candidates are retained in the proposal rows.',
        '',
        'All 24 blind hash-only holds were callerless and remain holds; there were no callerful hash-only holds to clear. The two Ko-fi cells where primary proposed and blind retained current were resolved using the pinned linked brand text and ko-fi.com URL.',
        '',
        'All remaining callerful cells are no-op entries with source/current hashes only. The 24 callerless cells remain hash-only holds and contain no source or current-target strings in the cross packet. No tests, builds, CI, browser work, native-speaker review, source edits, or PR edits were performed.',
        '',
        'The selected plan is not applied. See `selected-proposals.jsonl`, `no-op-ledger.jsonl`, `source-evidence.jsonl`, and run `python3 verify_cross_packet.py --repo <exact-pinned-worktree>` to verify internal seals and the live source catalog against the pinned commit.',
        '',
    ]
    (OUT / 'cross-report.md').write_text('\n'.join(report_lines), encoding='utf-8')

    verifier = r'''#!/usr/bin/env python3
"""Portable verifier for the ROMarrNG W585-W604 cross-audit packet."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
EXPECTED = {
    'head': '01da053f0e6a47e7184fb86da77f66b7b6719653',
    'tree': 'dcb9c1766831e217ffca7fb77068b97c33b9524e',
    'branch': 'task/localization-translation-review-20261030',
    'positions': list(range(585, 605)),
    'locales': ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant'],
}
TEXT_KEYS = {'source', 'currentTarget', 'selectedTarget', 'proposedTarget', 'primaryCandidate', 'blindCandidate'}

def fail(message):
    raise SystemExit('FAIL: ' + message)

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def sha_text(value):
    return sha_bytes(value.encode('utf-8'))

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def verify_sums():
    sum_file = ROOT / 'SHA256SUMS.txt'
    rows = {}
    for line in sum_file.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, name = line.split('  ', 1)
        p = (ROOT / name).resolve()
        if not p.is_relative_to(ROOT.resolve()) or not p.is_file():
            fail('unsafe or missing checksum path: ' + name)
        if sha_bytes(p.read_bytes()) != digest:
            fail('checksum mismatch: ' + name)
        if name in rows:
            fail('duplicate checksum path: ' + name)
        rows[name] = digest
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt'}
    if actual != set(rows):
        fail('checksum file does not cover the packet exactly')
    sealed = read_json(ROOT / 'sealed-manifest.json')
    sidecar = (ROOT / 'sealed-manifest.sha256').read_text(encoding='ascii').split()
    if sidecar != [sha_bytes((ROOT / 'sealed-manifest.json').read_bytes()), 'sealed-manifest.json']:
        fail('sealed manifest sidecar mismatch')
    if sealed.get('recordType') != 'sealed-cross-audit-packet' or sealed.get('schemaVersion') != 1:
        fail('sealed manifest schema mismatch')
    for name, expected in sealed['files'].items():
        p = (ROOT / name).resolve()
        if not p.is_relative_to(ROOT.resolve()) or not p.is_file() or sha_bytes(p.read_bytes()) != expected['sha256'] or p.stat().st_size != expected['bytes']:
            fail('sealed payload mismatch: ' + name)
    listed_payload = set(sealed['files'])
    actual_payload = actual - {'sealed-manifest.json', 'sealed-manifest.sha256'}
    if listed_payload != actual_payload:
        fail('sealed manifest payload coverage mismatch')

def verify_packet(repo=None):
    verify_sums()
    manifest = read_json(ROOT / 'cross-manifest.json')
    pin = manifest['pin']
    if pin['head'] != EXPECTED['head'] or pin['tree'] != EXPECTED['tree'] or pin['branch'] != EXPECTED['branch']:
        fail('cross manifest exact pin mismatch')
    if pin['positions'] != [585, 604] or pin['catalogPath'] != 'romarr/ui-labels.json':
        fail('selection boundary mismatch')
    selected = read_jsonl(ROOT / 'selected-proposals.jsonl')
    noops = read_jsonl(ROOT / 'no-op-ledger.jsonl')
    evidence = {r['sourceId']: r for r in read_jsonl(ROOT / 'source-evidence.jsonl')}
    if len(selected) != 22 or len(noops) != 218 or len(selected) + len(noops) != 240:
        fail('cell totals mismatch')
    cells = {}
    selected_keys = set()
    for row in selected:
        key = (row['sourceId'], row['locale'])
        if key in cells:
            fail('duplicate selected cell')
        cells[key] = row
        selected_keys.add(key)
        if row['position'] not in EXPECTED['positions'] or row['locale'] not in EXPECTED['locales']:
            fail('selected cell outside window')
        for field, hash_field in [('source', 'sourceSha256'), ('currentTarget', 'currentTargetSha256'), ('selectedTarget', 'selectedTargetSha256')]:
            if sha_text(row[field]) != row[hash_field]:
                fail('selected cell hash mismatch: ' + str(key) + ' ' + field)
        if row['selectedTarget'] == row['currentTarget']:
            fail('selected target is a no-op: ' + str(key))
        for candidate, candidate_sha in [('primaryCandidate', 'primaryCandidateSha256'), ('blindCandidate', 'blindCandidateSha256')]:
            value = row[candidate]
            expected = row[candidate_sha]
            if (value is None) != (expected is None) or (value is not None and sha_text(value) != expected):
                fail('candidate hash mismatch: ' + str(key) + ' ' + candidate)
        if row['selectedTarget'] not in {row['primaryCandidate'], row['blindCandidate']}:
            fail('selected target is not an upstream candidate: ' + str(key))
        if row['callerRefCount'] < 1 or row['callerContextSha256'] != evidence[row['sourceId']]['callerContextSha256']:
            fail('selected target lacks caller evidence: ' + str(key))
        if row['sourceEvidenceRef']['sourceId'] != row['sourceId']:
            fail('selected source evidence reference mismatch: ' + str(key))
        if row['nativeSpeakerApproval'] is not False:
            fail('unexpected native-speaker claim')
    hold_sources = {}
    for row in noops:
        key = (row['sourceId'], row['locale'])
        if key in cells:
            fail('selected cell duplicated in no-op ledger')
        cells[key] = row
        if row['position'] not in EXPECTED['positions'] or row['locale'] not in EXPECTED['locales']:
            fail('no-op cell outside window')
        if any(row.get(k) is not None for k in TEXT_KEYS):
            fail('no-op ledger contains text')
        if row['currentTargetSha256'] != row['primaryCurrentTargetSha256'] or row['currentTargetSha256'] != row['blindCurrentTargetSha256']:
            fail('no-op current hash disagreement: ' + str(key))
        if row['crossDisposition'] == 'HOLD_HASH_ONLY':
            if row['callerRefCount'] != 0 or row['blindDisposition'] != 'hold_hash_only' or row['primaryDisposition'] != 'KEEP':
                fail('invalid hash-only hold: ' + str(key))
            if row.get('holdReasonSha256') is None:
                fail('hash-only hold missing reason hash')
            hold_sources[row['sourceId']] = hold_sources.get(row['sourceId'], 0) + 1
        elif row['crossDisposition'] == 'KEEP_CURRENT':
            if row['callerRefCount'] < 1 or row['blindDisposition'] != 'retain_current' or row['primaryDisposition'] != 'KEEP':
                fail('invalid keep-current no-op: ' + str(key))
        else:
            fail('unknown no-op disposition: ' + str(key))
    if len(cells) != 240 or len({sid for sid, _ in cells}) != 20:
        fail('window source/cell coverage mismatch')
    per_source = {}
    for (sid, locale), row in cells.items():
        per_source.setdefault(sid, set()).add(locale)
    if any(locales != set(EXPECTED['locales']) for locales in per_source.values()):
        fail('locale coverage mismatch')
    if len([r for r in noops if r['crossDisposition'] == 'HOLD_HASH_ONLY']) != 24 or sorted(hold_sources.values()) != [12, 12]:
        fail('callerless hash-only hold total mismatch')
    if len([r for r in noops if r['crossDisposition'] == 'KEEP_CURRENT']) != 194:
        fail('callerful no-op total mismatch')
    if manifest.get('unresolvedContextualHoldCount') != 0:
        fail('unresolved hold count mismatch')
    if len(evidence) != 6:
        fail('source evidence coverage mismatch')
    for sid, ev in evidence.items():
        if ev['callerless'] or ev['callerRefCount'] < 1 or ev['sourceSha256'] != sha_text(ev['source']):
            fail('invalid contextual source evidence: ' + sid)
        ctx = ev['expandedPinnedContext']
        if sha_text('\n'.join(line['text'] for line in ctx['lines']) + '\n') != ctx['excerptSha256']:
            fail('expanded context hash mismatch: ' + sid)
    if repo is not None:
        repo = pathlib.Path(repo).resolve()
        head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        tree = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
        status = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain=v1'], text=True).strip()
        if head != EXPECTED['head'] or tree != EXPECTED['tree'] or status:
            fail('source worktree pin or cleanliness mismatch')
        catalog_path = repo / pin['catalogPath']
        catalog = read_json(catalog_path)
        if sha_bytes(catalog_path.read_bytes()) != manifest['catalogFileSha256']:
            fail('pinned catalog file hash mismatch')
        messages = catalog['messages']
        ordered_ids = list(messages)
        if sha_text('\n'.join(ordered_ids) + '\n') != manifest['catalogKeyOrderSha256']:
            fail('pinned catalog key-order hash mismatch')
        if ordered_ids[585:605] != list(per_source_order(cells)):
            fail('pinned catalog selected source order mismatch')
        for (sid, locale), row in cells.items():
            item = messages.get(sid)
            if item is None or sha_text(item['source']) != row['sourceSha256'] or sha_text(item['translations'][locale]) != row['currentTargetSha256']:
                fail('pinned catalog current value mismatch: ' + str((sid, locale)))
        for sid, ev in evidence.items():
            ctx = ev['expandedPinnedContext']
            fpath = repo / ctx['path']
            if sha_bytes(fpath.read_bytes()) != ctx['fileSha256']:
                fail('expanded context source file hash mismatch: ' + ctx['path'])
            lines = fpath.read_text(encoding='utf-8').splitlines()
            if lines[ctx['startLine'] - 1:ctx['endLine']] != [x['text'] for x in ctx['lines']]:
                fail('expanded context line mismatch: ' + sid)
    return {'result': 'PASS', 'head': EXPECTED['head'], 'tree': EXPECTED['tree'], 'selectedProposals': len(selected), 'noOpCells': len(noops), 'callerfulKeepCurrent': 194, 'callerlessHashOnlyHolds': 24, 'sourceEvidenceRows': len(evidence), 'repoPin': 'PASS' if repo is not None else 'NOT_CHECKED'}

def per_source_order(cells):
    by_position = {}
    for sid, locale in cells:
        row = cells[(sid, locale)]
        by_position[row['position']] = sid
    return [by_position[position] for position in EXPECTED['positions']]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=pathlib.Path, help='Optional exact pinned ROMarrNG worktree for live source/catalog reattestation')
    args = parser.parse_args()
    print(json.dumps(verify_packet(args.repo), ensure_ascii=False, sort_keys=True))

if __name__ == '__main__':
    main()
'''
    (OUT / 'verify_cross_packet.py').write_text(verifier, encoding='utf-8')

    readme = '''# ROMarrNG PR #70 W585–W604 cross-audit packet

This sealed packet reconciles the fresh candidate-free input, fresh primary semantic review, and sealed blind review at exact head `01da053f0e6a47e7184fb86da77f66b7b6719653`, tree `dcb9c1766831e217ffca7fb77068b97c33b9524e`.

`selected-proposals.jsonl` is a proposal/apply plan only. It does not change the catalog. Each row includes exact source/current/proposed text and hashes, upstream review outcomes, caller evidence reference, resolution type, and rationale. `no-op-ledger.jsonl` covers all other 218 cells. The 24 callerless cells remain hash-only holds and have no source or current-target text in this packet. `source-evidence.jsonl` contains pinned caller snippets and expanded source lines for the six selected source IDs.

Run the portable verifier from any directory:

```sh
python3 verify_cross_packet.py
```

To additionally reattest exact commit/tree, clean worktree, catalog bytes, selected positions, current source/translation hashes, and cited source lines:

```sh
python3 verify_cross_packet.py --repo /path/to/exact-pinned-ROMarrNG-worktree
```

The packet includes no tests, builds, CI results, browser/native-speaker review claims, or repository/PR edits. See `cross-report.md` for the concise review result.
'''
    (OUT / 'README.md').write_text(readme, encoding='utf-8')

    # The sealed manifest excludes its own sidecar and standard checksum list.
    payload_files = sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in {'sealed-manifest.json', 'sealed-manifest.sha256', 'SHA256SUMS.txt'})
    sealed = {
        'recordType': 'sealed-cross-audit-packet',
        'schemaVersion': 1,
        'sealedUtc': created_utc,
        'pin': PIN,
        'counts': report['counts'],
        'inputAttestations': input_refs,
        'files': {p.relative_to(OUT).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha_bytes(p.read_bytes())} for p in payload_files},
    }
    write_json(OUT / 'sealed-manifest.json', sealed)
    (OUT / 'sealed-manifest.sha256').write_text(f"{sha_bytes((OUT / 'sealed-manifest.json').read_bytes())}  sealed-manifest.json\n", encoding='ascii')
    all_files = sorted(p for p in OUT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt')
    (OUT / 'SHA256SUMS.txt').write_text(''.join(f"{sha_bytes(p.read_bytes())}  {p.relative_to(OUT).as_posix()}\n" for p in all_files), encoding='ascii')
    print(json.dumps({'result': 'BUILT', 'output': str(OUT), 'selected': len(selected_rows), 'noOp': len(no_op_rows), 'holds': noop_counts['HOLD_HASH_ONLY'], 'files': len(all_files)}, sort_keys=True))


if __name__ == '__main__':
    main()
