#!/usr/bin/env python3
"""Verify integrity and scope of the sealed W585-W604 blind review packet."""
import collections
import hashlib
import json
from pathlib import Path

INPUT = Path('/home/keith/Documents/code/task-scratch/romarrng-pr70-w585-604-current-candidate-free-20261104/candidate-free/input')
PACKET = Path(__file__).resolve().parent
BLINDNESS = PACKET.parent / 'blindness-manifest.json'
EXPECTED_HEAD = '01da053f0e6a47e7184fb86da77f66b7b6719653'
EXPECTED_TREE = 'dcb9c1766831e217ffca7fb77068b97c33b9524e'
EXPECTED_BRANCH = 'task/localization-translation-review-20261030'


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def require(condition, message):
    if not condition:
        raise SystemExit('FAIL: ' + message)


def verify_input_checksums():
    lines = (INPUT / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines()
    require(len(lines) == 27, 'candidate-free input checksum entry count changed')
    for line in lines:
        expected, name = line.split(None, 1)
        name = name.strip().lstrip('*')
        actual = sha_bytes((INPUT / name).read_bytes())
        require(actual == expected, f'candidate-free input checksum mismatch: {name}')
    return len(lines)


def main():
    input_count = verify_input_checksums()
    manifest_path = PACKET / 'sealed-manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    listed = (PACKET / 'sealed-manifest.sha256').read_text(encoding='ascii').split()
    require(len(listed) == 2 and listed[0] == sha_bytes(manifest_bytes) and listed[1] == 'sealed-manifest.json', 'sealed manifest checksum mismatch')
    manifest = json.loads(manifest_bytes)
    require(manifest['recordType'] == 'sealed-blind-review-packet', 'wrong sealed manifest type')
    require(manifest['pin']['head'] == EXPECTED_HEAD and manifest['pin']['tree'] == EXPECTED_TREE and manifest['pin']['branch'] == EXPECTED_BRANCH, 'sealed manifest pin mismatch')
    require(manifest['input']['verifiedInputFileCount'] == input_count, 'manifest candidate-free input count mismatch')
    require(manifest['input']['sha256sumsFileSha256'] == sha_bytes((INPUT / 'SHA256SUMS.txt').read_bytes()), 'manifest candidate-free checksum file hash mismatch')
    require(manifest['input']['blindnessManifestSha256'] == sha_bytes(BLINDNESS.read_bytes()), 'blindness manifest hash mismatch')
    for name, expected in manifest['files'].items():
        require((PACKET / name).is_file(), f'missing sealed packet file {name}')
        require(sha_bytes((PACKET / name).read_bytes()) == expected, f'sealed packet file checksum mismatch: {name}')

    selection = read_json(INPUT / 'selection.json')
    source_contexts = {r['sourceId']: r for r in read_jsonl(INPUT / 'source-contexts.jsonl')}
    input_cells = read_jsonl(INPUT / 'current-target-cells.jsonl')
    input_map = {(r['sourceId'], r['locale']): r for r in input_cells}
    rows = read_jsonl(PACKET / 'blind-decisions.jsonl')
    expected_order = [(s['sourceId'], locale) for s in selection['selectedSources'] for locale in selection['localeOrder']]
    actual_order = [(r['sourceId'], r['locale']) for r in rows]
    require(len(rows) == 240 and actual_order == expected_order, 'decision rows do not cover the exact 240-cell selection in pinned order')
    require(len(set(actual_order)) == 240, 'duplicate decision cell')

    counts = collections.Counter()
    by_source = collections.Counter()
    for row in rows:
        key = (row['sourceId'], row['locale'])
        cell = input_map[key]
        context = source_contexts[key[0]]
        callers = context.get('callers', [])
        require(row['catalogPosition'] == cell['position'], f'catalog position mismatch: {key}')
        require(row['catalogOneBasedPosition'] == cell['catalogZeroBasedIndex'] + 1, f'one-based position mismatch: {key}')
        require(row['sourceSha256'] == cell['sourceSha256'], f'source hash mismatch: {key}')
        require(row['currentTargetSha256'] == cell['currentTargetSha256'], f'current target hash mismatch: {key}')
        require(row['callerContextSha256'] == cell['callerContextSha256'], f'caller context hash mismatch: {key}')
        require(row['callerRefCount'] == len(callers) and row['callerless'] == (len(callers) == 0), f'caller coverage mismatch: {key}')
        require('source' not in row and 'currentTarget' not in row, f'packet must not copy source/current target text: {key}')
        require(row['confidence'] in {'high', 'moderate', 'low', 'unknown'}, f'invalid confidence: {key}')
        disposition = row['disposition']
        counts[disposition] += 1
        if disposition == 'hold_hash_only':
            require(not callers, f'callerful cell placed in hash-only hold: {key}')
            require('proposedTarget' not in row and 'proposedTargetSha256' not in row, f'hash-only hold contains target text: {key}')
            require(row['currentTargetSha256'] == cell['currentTargetSha256'], f'hash-only hold changed target hash: {key}')
        elif disposition == 'retain_current':
            require(bool(callers), f'callerless cell not preserved as hash-only hold: {key}')
            require('proposedTarget' not in row and 'proposedTargetSha256' not in row, f'retain row contains proposal: {key}')
        elif disposition == 'propose_refinement':
            require(bool(callers), f'callerless source has proposal: {key}')
            target = row.get('proposedTarget')
            require(isinstance(target, str) and target.strip(), f'empty proposed target: {key}')
            require(row.get('proposedTargetSha256') == hashlib.sha256(target.encode('utf-8')).hexdigest(), f'proposed target hash mismatch: {key}')
            require(target != cell['currentTarget'], f'proposal is unchanged: {key}')
            for token in cell.get('sourcePlaceholderTokens', []):
                require(token in target, f'proposal drops placeholder {token}: {key}')
            for token in cell.get('sourceNumericTokens', []):
                require(token in target, f'proposal drops numeric token {token}: {key}')
            for literal in cell.get('sourceProtectedLiterals', []):
                require(literal in target, f'proposal drops protected literal {literal}: {key}')
            for tag in cell.get('sourceMarkupTags', []):
                require(tag in target, f'proposal drops markup token {tag}: {key}')
            by_source[key[0]] += 1
        else:
            require(False, f'unknown disposition {disposition}: {key}')

    require(counts == {'propose_refinement': 20, 'retain_current': 196, 'hold_hash_only': 24}, f'disposition totals mismatch: {dict(counts)}')
    require(by_source == {'ui.ko-fi.76c38e42cf': 1, 'ui.lynx-header.83b04c6319': 1, 'ui.last-ran.2e024dc014': 2, 'ui.last-refresh.519ad138a1': 2, 'ui.latest-listed-version-only.1df61faba4': 2, 'ui.left.58eb9032e3': 12}, f'proposal source totals mismatch: {dict(by_source)}')
    summary = read_json(PACKET / 'review-summary.json')
    require(summary['dispositions']['total'] == 240 and summary['dispositions']['proposeRefinement'] == 20 and summary['dispositions']['retainCurrent'] == 196 and summary['dispositions']['holdHashOnly'] == 24, 'review summary counts mismatch')
    require(summary['coverage']['sourcesWithPinnedCallerContextReviewed'] == 18 and summary['coverage']['pinnedDirectCallerReferencesConsulted'] == 37, 'caller coverage summary mismatch')
    require(summary['limitations']['nativeSpeakerApproval'] is False, 'native-speaker limitation must be explicit')
    print(json.dumps({'result': 'PASS', 'inputFilesVerified': input_count, 'cells': len(rows), 'proposals': counts['propose_refinement'], 'retained': counts['retain_current'], 'hashOnlyHolds': counts['hold_hash_only'], 'callerRefs': 37}, sort_keys=True))


if __name__ == '__main__':
    main()
