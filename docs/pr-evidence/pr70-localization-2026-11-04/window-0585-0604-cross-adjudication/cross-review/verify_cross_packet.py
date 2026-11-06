#!/usr/bin/env python3
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
