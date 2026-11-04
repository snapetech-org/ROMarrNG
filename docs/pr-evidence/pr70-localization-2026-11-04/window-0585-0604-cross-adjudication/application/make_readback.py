#!/usr/bin/env python3
"""Create exact hash readback for all 240 W585-W604 cells."""
from __future__ import annotations
import argparse
import collections
import copy
import hashlib
import json
import pathlib
import subprocess
import sys

CATALOG = 'romarr/ui-labels.json'
PRE_HEAD = '01da053f0e6a47e7184fb86da77f66b7b6719653'
PRE_TREE = 'dcb9c1766831e217ffca7fb77068b97c33b9524e'
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']
FORBIDDEN_HOLD_FIELDS = {'sourceId', 'source', 'sourceText', 'currentTarget', 'beforeTarget', 'afterTarget', 'proposedTarget', 'selectedTarget', 'rationale'}

def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode('utf-8')).hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def read_jsonl(path):
    rows = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            rows.append((json.loads(raw), sha(raw)))
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=pathlib.Path, required=True)
    parser.add_argument('--cross-packet', type=pathlib.Path, required=True)
    parser.add_argument('--candidate-input', type=pathlib.Path, required=True)
    parser.add_argument('--before-catalog', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    cross = args.cross_packet.resolve()
    candidate = args.candidate_input.resolve()
    before_raw = args.before_catalog.read_bytes()
    before = json.loads(before_raw.decode('utf-8'))
    after_raw = (repo / CATALOG).read_bytes()
    after = json.loads(after_raw.decode('utf-8'))
    manifest = read_json(cross / 'cross-manifest.json')
    cells = {(row['position'], row['locale']): (row, digest) for row, digest in read_jsonl(candidate / 'current-target-cells.jsonl')}
    contexts = {row['sourceId']: row for row, _ in read_jsonl(candidate / 'source-contexts.jsonl')}
    cross_selected = { (row['position'], row['locale']): (row, digest) for row, digest in read_jsonl(cross / 'selected-proposals.jsonl') }
    cross_noops = { (row['position'], row['locale']): (row, digest) for row, digest in read_jsonl(cross / 'no-op-ledger.jsonl') }
    if git(repo, 'rev-parse', 'HEAD') != PRE_HEAD or git(repo, 'rev-parse', 'HEAD^{tree}') != PRE_TREE:
        raise SystemExit('FAIL: pre-product worktree pin changed before commit')
    if sha(before_raw) != manifest['catalogFileSha256']:
        raise SystemExit('FAIL: before catalog hash does not match cross packet')
    if len(cells) != 240 or set(cross_selected) | set(cross_noops) != set(cells) or set(cross_selected) & set(cross_noops):
        raise SystemExit('FAIL: source/cross cell coverage mismatch')

    readback = []
    applied = []
    holds = []
    counts = collections.Counter()
    for key in sorted(cells, key=lambda k: (k[0], LOCALES.index(k[1]))):
        cell, cell_digest = cells[key]
        ctx = contexts[cell['sourceId']]
        selected_entry = cross_selected.get(key)
        noop_entry = cross_noops.get(key)
        source_id = cell['sourceId']
        locale = cell['locale']
        if list(before['messages']).index(source_id) != cell['position']:
            raise SystemExit(f'FAIL: catalog source position mismatch: {source_id}')
        old_source = before['messages'][source_id]['source']
        post_source = after['messages'][source_id]['source']
        if sha(old_source) != cell['sourceSha256'] or old_source != post_source or sha(post_source) != cell['sourceSha256']:
            raise SystemExit(f'FAIL: source hash readback mismatch: {source_id}/{locale}')
        before_target = before['messages'][source_id]['translations'][locale]
        after_target = after['messages'][source_id]['translations'][locale]
        if sha(before_target) != cell['currentTargetSha256']:
            raise SystemExit(f'FAIL: pre-target hash readback mismatch: {source_id}/{locale}')
        record = {
            'schemaVersion': 1,
            'window': 'W585-W604',
            'position': cell['position'],
            'catalogOneBasedPosition': cell['catalogZeroBasedIndex'] + 1,
            'locale': locale,
            'sourceSha256': cell['sourceSha256'],
            'beforeTargetSha256': sha(before_target),
            'afterTargetSha256': sha(after_target),
            'callerContextSha256': cell['callerContextSha256'],
            'callerRefCount': len(ctx['callers']),
            'callerless': not bool(ctx['callers']),
            'candidateFreeCellRowSha256': cell_digest,
            'crossDecisionRowSha256': (selected_entry or noop_entry)[1],
        }
        if selected_entry:
            selected, _ = selected_entry
            if ctx['callerless'] or after_target != selected['selectedTarget'] or sha(after_target) != selected['selectedTargetSha256']:
                raise SystemExit(f'FAIL: selected target not present: {source_id}/{locale}')
            record.update({
                'sourceId': source_id,
                'disposition': 'selected-change',
                'changed': True,
                'selectedTargetSha256': selected['selectedTargetSha256'],
                'crossResolution': selected['resolution'],
            })
            applied.append({
                'position': cell['position'],
                'catalogOneBasedPosition': cell['catalogZeroBasedIndex'] + 1,
                'sourceId': source_id,
                'locale': locale,
                'sourceSha256': cell['sourceSha256'],
                'beforeTargetSha256': sha(before_target),
                'afterTargetSha256': sha(after_target),
                'selectedTargetSha256': selected['selectedTargetSha256'],
                'crossDecisionRowSha256': selected_entry[1],
                'callerContextSha256': cell['callerContextSha256'],
                'crossResolution': selected['resolution'],
            })
            counts['selected-change'] += 1
        else:
            noop, _ = noop_entry
            if after_target != before_target or sha(after_target) != noop['currentTargetSha256']:
                raise SystemExit(f'FAIL: no-op or hold changed: {source_id}/{locale}')
            if noop['crossDisposition'] == 'HOLD_HASH_ONLY':
                if ctx['callers'] or ({'source', 'sourceText', 'currentTarget', 'beforeTarget', 'afterTarget', 'proposedTarget', 'selectedTarget', 'rationale'} & set(noop)):
                    raise SystemExit(f'FAIL: callerless hold has context or source text: {source_id}/{locale}')
                record.update({
                    'disposition': 'hold-hash-only',
                    'changed': False,
                    'holdReasonSha256': noop['holdReasonSha256'],
                })
                # Preserve the callerless hold as hash-only: omit source ID and all source/current/proposal text.
                record.pop('sourceId', None)
                if FORBIDDEN_HOLD_FIELDS & set(record):
                    raise SystemExit('FAIL: hold readback contains text or source ID')
                hold_record = {
                    'position': cell['position'],
                    'catalogOneBasedPosition': cell['catalogZeroBasedIndex'] + 1,
                    'locale': locale,
                    'sourceSha256': cell['sourceSha256'],
                    'currentTargetSha256': cell['currentTargetSha256'],
                    'callerContextSha256': cell['callerContextSha256'],
                    'callerRefCount': 0,
                    'holdReasonSha256': noop['holdReasonSha256'],
                    'candidateFreeCellRowSha256': cell_digest,
                    'crossDecisionRowSha256': noop_entry[1],
                }
                holds.append(hold_record)
                counts['hold-hash-only'] += 1
            else:
                if ctx['callerless'] or noop['crossDisposition'] != 'KEEP_CURRENT':
                    raise SystemExit(f'FAIL: unexpected no-op classification: {source_id}/{locale}')
                record.update({
                    'sourceId': source_id,
                    'disposition': 'keep-current',
                    'changed': False,
                })
                counts['keep-current'] += 1
        readback.append(record)

    if counts != {'selected-change': 22, 'keep-current': 194, 'hold-hash-only': 24}:
        raise SystemExit(f'FAIL: unexpected readback totals: {dict(counts)}')
    if len(readback) != 240 or len(applied) != 22 or len(holds) != 24:
        raise SystemExit('FAIL: exact readback record counts')
    # Verify that the two JSON documents differ only in the 22 selected locale values.
    expected = copy.deepcopy(before)
    cross_rows = read_jsonl(cross / 'selected-proposals.jsonl')
    for selected, _ in cross_rows:
        expected['messages'][selected['sourceId']]['translations'][selected['locale']] = selected['selectedTarget']
    if expected != after or list(before['messages']) != list(after['messages']) or list(before['locales']) != list(after['locales']):
        raise SystemExit('FAIL: post catalog contains changes outside the selected translations')
    for source_id, before_item in before['messages'].items():
        after_item = after['messages'][source_id]
        for field in ('source', 'sourceHash', 'translationHashes', 'translationStatus', 'translationReview'):
            if before_item.get(field) != after_item.get(field):
                raise SystemExit(f'FAIL: translation/source metadata changed: {source_id}/{field}')

    args.output.mkdir(parents=True, exist_ok=True)
    def write_jsonl(name, rows):
        (args.output / name).write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows), encoding='utf-8')
    write_jsonl('application-readback.jsonl', readback)
    write_jsonl('selected-applied.jsonl', applied)
    write_jsonl('holds.jsonl', holds)
    pins = {
        'window': 'W585-W604',
        'preHead': PRE_HEAD,
        'preTree': PRE_TREE,
        'catalogPath': CATALOG,
        'preCatalogSha256': sha(before_raw),
        'postCatalogSha256': sha(after_raw),
        'preCatalogGitBlob': subprocess.check_output(['git','-C',str(repo),'rev-parse',f'{PRE_HEAD}:{CATALOG}'],text=True).strip(),
        'postCatalogGitBlob': subprocess.check_output(['git','-C',str(repo),'hash-object',str(repo / CATALOG)],text=True).strip(),
        'catalogKeyOrderSha256': sha(('\n'.join(before['messages']) + '\n').encode()),
        'catalogMessageCount': len(before['messages']),
        'localeRegistryOrder': list(before['locales']),
        'selectedLocaleOrder': LOCALES,
        'onlyProductPathChanged': CATALOG,
    }
    (args.output / 'catalog-pins.json').write_text(json.dumps(pins,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    summary = {
        'window': 'W585-W604',
        'preHead': PRE_HEAD,
        'preTree': PRE_TREE,
        'productCommit': None,
        'productTree': None,
        'readbackCellCount': len(readback),
        'changedCellCount': counts['selected-change'],
        'keptCurrentCellCount': counts['keep-current'],
        'callerlessHashOnlyHoldCount': counts['hold-hash-only'],
        'noOpCellCount': counts['keep-current'] + counts['hold-hash-only'],
        'nonTargetProductFilesChanged': 0,
        'catalogKeyOrderPreserved': list(before['messages']) == list(after['messages']),
        'localeRegistryOrderPreserved': list(before['locales']) == list(after['locales']),
        'translationMetadataChanged': False,
        'productScope': CATALOG,
        'selectedProposalResolutionCounts': dict(collections.Counter(row['crossResolution'] for row in applied)),
        'sourceAndCurrentTargetHashesGuarded': True,
        'unresolvedContextualHolds': 0,
    }
    (args.output / 'application-summary.json').write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':'READBACK_PASS','counts':dict(counts),'preCatalogSha256':pins['preCatalogSha256'],'postCatalogSha256':pins['postCatalogSha256'],'readbackCells':len(readback),'productScope':CATALOG},sort_keys=True))

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()

if __name__ == '__main__':
    main()
