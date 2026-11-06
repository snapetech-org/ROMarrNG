#!/usr/bin/env python3
"""Read-only verifier for the ROMarrNG PR #70 W265-W284 audit packet."""
from __future__ import annotations
import collections
from collections import Counter
import hashlib
import json
import pathlib
import re
import subprocess
import sys

OUT = pathlib.Path(__file__).resolve().parent
INPUT = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w265-284-candidate-free-20261103/input')
PRIMARY = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w265-284-primary-20261103')
BLIND = pathlib.Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w265-284-independent-blind-20261103')
EXPECTED_HEAD = 'c135c4729582817273c946891186ab4ea87467b5'
EXPECTED_TREE = '32c07150396335a5832b5664fc1e0225d7cebdc1'
EXPECTED_PR = 70
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']
POSITIONS = list(range(265, 285))
DIRECT_POSITIONS = {265, 266, 267, 268, 283, 284}
PH_RE = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')


def fail(message: str) -> None:
    raise AssertionError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha(obj) -> str:
    return digest(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path: pathlib.Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def keyed(rows):
    result = {}
    for row in rows:
        key = (row['position'], row['locale'])
        if key in result:
            fail(f'duplicate row {key}')
        result[key] = row
    return result


def verify_sums(folder: pathlib.Path, must_match_all_files=False):
    sums = {}
    for line in (folder / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        if name in sums:
            fail(f'duplicate checksum entry {folder}/{name}')
        path = folder / name
        if not path.is_file():
            fail(f'missing checksummed file {path}')
        actual = digest(path.read_bytes())
        if actual != expected:
            fail(f'checksum mismatch {path}: {actual} != {expected}')
        sums[name] = expected
    if must_match_all_files:
        actual_names = {p.name for p in folder.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt'}
        if set(sums) != actual_names:
            fail(f'checksum inventory mismatch: missing={sorted(actual_names-set(sums))}, extra={sorted(set(sums)-actual_names)}')
    return sums


def main():
    # Packet integrity.
    input_sums = verify_sums(INPUT)
    primary_sums = verify_sums(PRIMARY)
    blind_sums = verify_sums(BLIND)
    output_sums = verify_sums(OUT, must_match_all_files=True)
    manifest = read_json(INPUT / 'manifest.json')
    pins = read_json(INPUT / 'catalog-file-pins.json')
    summary = read_json(OUT / 'summary.json')
    attestation = read_json(OUT / 'attestation.json')
    pinned_state = read_json(OUT / 'pinned-state-verification.json')
    primary_summary = read_json(PRIMARY / 'summary.json')
    blind_summary = read_json(BLIND / 'summary.json')
    blind_seal = read_json(BLIND / 'blind-seal.json')
    blind_provenance = read_json(BLIND / 'provenance.json')
    blind_summary = read_json(BLIND / 'summary.json')
    blind_provenance = read_json(BLIND / 'provenance.json')
    ledger = read_jsonl(OUT / 'cross-audit-ledger.jsonl')
    ledger_by_key = keyed(ledger)
    input_lines = (INPUT / 'current-target-cells.jsonl').read_bytes().splitlines()
    input_rows_list = read_jsonl(INPUT / 'current-target-cells.jsonl')
    input_by_key = keyed(input_rows_list)
    input_raw_by_key = {(r['position'], r['locale']): line for r, line in zip(input_rows_list, input_lines)}
    primary_list = read_jsonl(PRIMARY / 'primary-decisions.jsonl')
    primary_by_key = keyed(primary_list)
    blind_list = read_jsonl(BLIND / 'blind-decisions.jsonl')
    blind_by_key = keyed(blind_list)
    context_list = read_jsonl(INPUT / 'source-contexts.jsonl')
    contexts = {r['position']: r for r in context_list}
    hold_list = read_jsonl(INPUT / 'caller-resolution-holds.jsonl')
    holds_by_key = keyed(hold_list)

    if len(ledger) != 240 or set(ledger_by_key) != set(input_by_key) or set(ledger_by_key) != set(primary_by_key) or set(ledger_by_key) != set(blind_by_key):
        fail('ledger/input/primary/blind key inventories do not exactly match 240 cells')
    if len(contexts) != 20 or set(contexts) != set(POSITIONS):
        fail('source-context inventory does not cover ranks 265-284')
    if manifest.get('head') != EXPECTED_HEAD or manifest.get('tree') != EXPECTED_TREE or manifest.get('cellCount') != 240 or manifest.get('sourceCount') != 20 or manifest.get('localeOrder') != LOCALES:
        fail('candidate-free manifest identity or counts mismatch')
    if digest((INPUT / 'manifest.json').read_bytes()) != primary_summary.get('candidateFreeInputManifestSha256'):
        fail('primary review does not attest current input manifest')

    # Pinned source files, exact checkout, source index ranks, and captured live refs.
    worktree = pathlib.Path(manifest['localWorktree'])
    head = subprocess.run(['git', '-C', str(worktree), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(['git', '-C', str(worktree), 'rev-parse', 'HEAD^{tree}'], check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(['git', '-C', str(worktree), 'status', '--porcelain'], check=True, capture_output=True, text=True).stdout.strip()
    if head != EXPECTED_HEAD or tree != EXPECTED_TREE or status:
        fail(f'pinned worktree mismatch or dirty: head={head} tree={tree} status={status!r}')
    pin_files = [pins['catalog'], pins['sourceIndex'], pins['sourceSnapshot'], *pins['callerFiles']]
    for pin in pin_files:
        path = worktree / pin['path']
        data = path.read_bytes()
        blob = subprocess.run(['git', '-C', str(worktree), 'rev-parse', f'{EXPECTED_HEAD}:{pin["path"]}'], check=True, capture_output=True, text=True).stdout.strip()
        if digest(data) != pin['sha256'] or blob != pin['gitBlob'] or len(data) != pin['byteCount'] or len(data.splitlines()) != pin['lineCount']:
            fail(f'pinned file mismatch: {pin["path"]}')
    index = read_json(worktree / pins['sourceIndex']['path'])
    messages = index['messages']
    ids = [r['id'] for r in messages]
    if len(messages) != manifest['activeUniqueSourceIdCount'] or len(set(ids)) != len(ids):
        fail('active source-index count or uniqueness mismatch')
    ordered_messages = sorted(messages, key=lambda r: r['id'])
    for pos in POSITIONS:
        entry = ordered_messages[pos - 1]
        row = input_by_key[(pos, LOCALES[0])]
        if entry['id'] != row['sourceId'] or entry['sourceHash'] != row['sourceSha256'] or entry['source'] != row['source']:
            fail(f'source-index rank mismatch at {pos}')
    boundary = {r['position']: r for r in read_jsonl(INPUT / 'selection-boundary.jsonl')}
    if set(boundary) != {264, *POSITIONS, 285} or boundary[264]['sourceId'] != ordered_messages[263]['id'] or boundary[285]['sourceId'] != ordered_messages[284]['id']:
        fail('selection boundary mismatch')
    if not pinned_state.get('checksPassed') or pinned_state.get('head') != EXPECTED_HEAD or pinned_state.get('tree') != EXPECTED_TREE:
        fail('captured pinned-state verification failed')
    if pinned_state.get('worktreePorcelain') != '' or not all(f['matches'] for f in pinned_state['filePins']):
        fail('captured worktree or source-file pins are not clean')
    if not all(r['matchesExpected'] for r in pinned_state['remoteRefs']) or not pinned_state['pullRequest'].get('openDraft'):
        fail('captured live refs or PR state did not match')

    # Every row is tied to exact input/review records and caller context.
    dispositions = collections.Counter()
    changed = []
    disagreements = []
    direct_count = 0
    blind_row_matches = 0
    blind_context_matches = 0
    for key, row in ledger_by_key.items():
        pos, locale = key
        if pos not in POSITIONS or locale not in LOCALES:
            fail(f'row outside selected rank/locale window: {key}')
        inp = input_by_key[key]
        p = primary_by_key[key]
        b = blind_by_key[key]
        ctx = contexts[pos]
        if row['head'] != EXPECTED_HEAD or row['tree'] != EXPECTED_TREE or row['pullRequest'] != EXPECTED_PR:
            fail(f'cross-audit pin mismatch at {key}')
        if row['sourceId'] != inp['sourceId'] or row['source'] != inp['source'] or row['sourceSha256'] != inp['sourceSha256']:
            fail(f'source identity mismatch at {key}')
        if row['category'] != ctx.get('category') or row['localeMetadata'] != inp.get('localeInfo') or row['currentReviewDecision'] != inp.get('reviewDecision') or row['currentTargetMarkupTags'] != inp.get('targetMarkupTags', []) or row['containsCandidate'] is not False:
            fail(f'locale/catalog metadata mismatch at {key}')
        if row['sourceMarkupTags'] != inp.get('sourceMarkupTags', []):
            fail(f'source markup metadata mismatch at {key}')
        if row['currentTarget'] != inp['currentTarget'] or row['currentTargetSha256'] != inp['currentTargetSha256'] or digest(inp['currentTarget'].encode()) != inp['currentTargetSha256']:
            fail(f'current target mismatch at {key}')
        if row['inputRecordSha256'] != canonical_sha(inp) or row['inputFileRowSha256'] != digest(input_raw_by_key[key]):
            fail(f'input row lineage mismatch at {key}')
        if row['primaryRecordSha256'] != canonical_sha(p) or row['blindRecordSha256'] != canonical_sha(b):
            fail(f'reviewer row lineage mismatch at {key}')
        if row['primaryDisposition'] != p['disposition'] or row['primaryTarget'] != p['selectedTarget'] or row['blindDisposition'] != b['recommendedDisposition'] or row['blindTarget'] != b['recommendedTarget']:
            fail(f'reviewer decision copy mismatch at {key}')
        if row['blindDisposition'] != b['recommendedDisposition'] or b.get('inputRowSha256') != canonical_sha(inp):
            fail(f'blind row did not attest exact input at {key}')
        blind_row_matches += 1
        refs = ctx.get('references', [])
        if b.get('callerReferenceCount') != len(refs) or b.get('currentCallerLocations') != ctx.get('currentCallerLocations') or b.get('callerContextSha256') != (refs[0]['contextSha256'] if refs else None):
            fail(f'blind caller linkage mismatch at {key}')
        blind_context_matches += 1
        if row['callerEvidence']['currentCallerLocations'] != ctx.get('currentCallerLocations') or row['callerEvidence']['sourceIndexLocations'] != ctx.get('sourceIndexLocations'):
            fail(f'caller locations mismatch at {key}')
        expected_refs = [{
            'path': r['path'], 'range': [r['startLine'], r['endLine']], 'matchBasis': r['matchBasis'],
            'fileSha256': r['fileSha256'], 'gitBlob': r['gitBlob'], 'contextSha256': r['contextSha256'],
            'contextLines': r['contextLines'],
        } for r in refs]
        if row['callerEvidence']['references'] != expected_refs:
            fail(f'exact caller context lines mismatch at {key}')
        pin_by_path = {f['path']: f for f in pin_files}
        for ref in expected_refs:
            if ref['path'] not in pin_by_path or ref['fileSha256'] != pin_by_path[ref['path']]['sha256'] or ref['gitBlob'] != pin_by_path[ref['path']]['gitBlob']:
                fail(f'caller file pin mismatch at {key}: {ref["path"]}')
            if any(digest(line['text'].encode()) != line['lineSha256'] for line in ref['contextLines']):
                fail(f'caller context line hash mismatch at {key}')
        if inp['catalogSha256'] != pins['catalog']['sha256'] or row['catalogGitBlob'] != pins['catalog']['gitBlob']:
            fail(f'catalog file pin mismatch at {key}')
        if Counter(PH_RE.findall(inp['source'])) != Counter(PH_RE.findall(inp['currentTarget'])):
            fail(f'current placeholder mismatch at {key}')
        if row['currentTargetPlaceholderMultisetMatchesSource'] is not True:
            fail(f'current placeholder evidence flag mismatch at {key}')
        hold = pos not in DIRECT_POSITIONS
        if hold:
            dispositions[row['crossAuditDisposition']] += 1
            hr = holds_by_key.get(key)
            if not hr or row['crossAuditDisposition'] != 'hold' or row['crossAuditTarget'] is not None or row['changeFromCurrent'] or row['selectedForApplication'] or row['holdEvidence'] != hr:
                fail(f'hold was changed or hold evidence mismatched at {key}')
            if row['callerEvidence']['callerResolutionHoldReason'] != hr['holdReason'] or row['primaryDisposition'] != 'hold' or row['blindDisposition'] != 'hold':
                fail(f'hold reason/reviewer hold mismatch at {key}')
        else:
            direct_count += 1
            target = row['crossAuditTarget']
            if target is None or Counter(PH_RE.findall(inp['source'])) != Counter(PH_RE.findall(target)):
                fail(f'reconciled placeholder mismatch at {key}')
            if digest(target.encode()) != row['crossAuditTargetSha256']:
                fail(f'reconciled target hash mismatch at {key}')
            if row['crossAuditPlaceholderMultisetMatchesSource'] is not True:
                fail(f'reconciled placeholder flag mismatch at {key}')
            if row['changeFromCurrent'] != (target != inp['currentTarget']) or row['selectedForApplication'] != row['changeFromCurrent']:
                fail(f'change selection flag mismatch at {key}')
            if row['crossAuditDisposition'] == 'accept-current' and target != inp['currentTarget']:
                fail(f'accepted current target differs at {key}')
            if row['crossAuditDisposition'] in ('correction', 'refinement') and target == inp['currentTarget']:
                fail(f'change disposition has unchanged text at {key}')
            dispositions[row['crossAuditDisposition']] += 1
        if row['changeFromCurrent']:
            changed.append(row)
        if row['reviewDisagreement'] != (row['primaryDisposition'] != row['blindDisposition'] or row['primaryTarget'] != row['blindTarget']):
            fail(f'reviewer disagreement flag mismatch at {key}')
        if row['reviewDisagreement']:
            disagreements.append(row)

    expected_counts = {'accept-current': 38, 'correction': 33, 'refinement': 1, 'hold': 168}
    if dict(dispositions) != expected_counts or len(changed) != 34 or direct_count != 72 or blind_row_matches != 240 or blind_context_matches != 240:
        fail(f'cross-audit counts mismatch: dispositions={dict(dispositions)}, changed={len(changed)}, direct={direct_count}')
    if len(disagreements) != 24:
        fail(f'expected 24 direct-review disagreements, found {len(disagreements)}')
    if len({r['position'] for r in changed}) != 6:
        fail('selected change rows do not cover six directly caller-backed ranks')
    for pos in POSITIONS:
        actual_locales = {loc for p, loc in ledger_by_key if p == pos}
        if actual_locales != set(LOCALES):
            fail(f'locale coverage mismatch at rank {pos}')

    # Summary/disagreement packet consistency.
    if summary['cellCount'] != 240 or summary['selectedChangeCount'] != 34 or summary['dispositionCounts'] != expected_counts:
        fail('summary counts mismatch')
    if summary.get('metadataValidation') != {'localeMetadataRowsChecked': 240, 'reviewDecisionRowsChecked': 240, 'sourceAndTargetMarkupMetadataRowsChecked': 240, 'candidateFreeRowsChecked': 240, 'metadataChanged': False}:
        fail('metadata validation summary mismatch')
    details = read_json(OUT / 'disagreement-and-hold-summary.json')
    if details['reviewDisagreements']['disagreementCellCount'] != len(disagreements):
        fail('disagreement summary count mismatch')
    expected_disagreement_rows = [{k: r[k] for k in ('position', 'locale', 'sourceId', 'primaryDisposition', 'blindDisposition', 'primaryTarget', 'blindTarget', 'crossAuditDisposition', 'crossAuditTarget', 'rationale')} for r in disagreements]
    if details['reviewDisagreements']['disagreementRows'] != expected_disagreement_rows:
        fail('disagreement row details mismatch')
    expected_hold_cells = [{'position': r['position'], 'locale': r['locale'], 'sourceId': r['sourceId'], 'source': r['source'], 'currentTarget': r['currentTarget'], 'currentTargetSha256': r['currentTargetSha256'], 'callerHoldReason': r['callerEvidence']['callerResolutionHoldReason'], 'primaryDisposition': r['primaryDisposition'], 'blindDisposition': r['blindDisposition'], 'targetSelected': False} for r in ledger if r['crossAuditDisposition'] == 'hold']
    if details['holds']['cells'] != expected_hold_cells:
        fail('hold row details mismatch')
    if len(details['holds']['cells']) != 168 or details['holds']['count'] != 168:
        fail('hold details count mismatch')
    if details['holds']['positions'] != list(range(269, 283)):
        fail('hold positions mismatch')
    manifest_sha = digest((INPUT / 'manifest.json').read_bytes())
    input_sums_sha = digest((INPUT / 'SHA256SUMS.txt').read_bytes())
    if blind_seal.get('candidateFreeManifestJsonSha256') != manifest_sha or blind_provenance.get('candidateFreeManifestJsonSha256') != manifest_sha or blind_summary.get('candidateFreeManifestJsonSha256') != manifest_sha:
        fail('blind candidate manifest JSON SHA256 mismatch')
    if blind_seal.get('candidateFreeInputChecksumListSha256') != input_sums_sha or blind_provenance.get('inputChecksumListSha256') != input_sums_sha or blind_summary.get('candidateFreeInputChecksumListSha256') != input_sums_sha:
        fail('blind candidate checksum-list SHA256 mismatch')
    if summary['inputLineage']['blindManifestJsonHashMatchesCurrentInput'] is not True or summary['inputLineage']['blindChecksumListHashMatchesCurrentInput'] is not True or summary['inputLineage']['blindProvenanceHashesMatchCurrentInput'] is not True:
        fail('cross-audit does not confirm corrected blind provenance')
    if summary['inputLineage']['blindPerRowInputRowsMatched'] != 240 or summary['inputLineage']['blindPerRowCallerContextHashesMatched'] != 240:
        fail('blind row-level evidence is incomplete')
    if summary['inputLineage']['candidateFreeManifestSha256'] != manifest_sha or summary['inputLineage']['candidateFreeChecksumListSha256'] != input_sums_sha:
        fail('candidate-free manifest/checksum-list lineage mismatch')
    if attestation.get('blindManifestHashMismatch') is not False or attestation.get('blindChecksumListHashMismatch') is not False:
        fail('attestation does not confirm corrected blind provenance')
    if attestation.get('repositoryModified') is not False or attestation.get('prModified') is not False or attestation.get('releaseActionsPerformed') is not False:
        fail('scope attestation does not confirm read-only review')
    report_text = (OUT / 'report.md').read_text(encoding='utf-8')
    if 'locale’' not in report_text or 'metadata fields unchanged' not in report_text:
        fail('report omits localized metadata handling')
    if manifest_sha not in report_text or input_sums_sha not in report_text:
        fail('report omits one of the separate candidate manifest/checksum-list hashes')

    print(json.dumps({
        'result': 'PASS',
        'outputChecksumFilesVerified': len(output_sums),
        'inputChecksumFilesVerified': len(input_sums),
        'primaryChecksumFilesVerified': len(primary_sums),
        'blindChecksumFilesVerified': len(blind_sums),
        'cellCount': len(ledger),
        'directCallerCells': direct_count,
        'holds': dispositions['hold'],
        'selectedChanges': len(changed),
        'disagreements': len(disagreements),
        'placeholderMismatches': 0,
        'worktreeHead': head,
        'worktreeTree': tree,
        'worktreeClean': not status,
        'blindManifestJsonHashMatchesCurrentInput': True,
        'blindChecksumListHashMatchesCurrentInput': True,
        'blindRowLevelInputHashesMatched': blind_row_matches,
        'blindCallerContextHashesMatched': blind_context_matches,
    }, indent=2))

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        raise
