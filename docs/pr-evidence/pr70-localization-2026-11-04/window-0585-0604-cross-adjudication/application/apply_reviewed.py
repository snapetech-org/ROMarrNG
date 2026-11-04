#!/usr/bin/env python3
"""Apply the sealed W585-W604 selection with exact source/current/target SHA guards."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import pathlib
import re
import subprocess
import sys

CATALOG = 'romarr/ui-labels.json'
EXPECTED_HEAD = '01da053f0e6a47e7184fb86da77f66b7b6719653'
EXPECTED_TREE = 'dcb9c1766831e217ffca7fb77068b97c33b9524e'
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']
POSITIONS = list(range(585, 605))

def sha(value):
    if isinstance(value, str):
        value = value.encode('utf-8')
    return hashlib.sha256(value).hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()

def object_end(text, start):
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return index + 1
    raise SystemExit('FAIL: unterminated JSON object')

def replace_translation(text, row):
    sid = row['sourceId']
    marker = json.dumps(sid, ensure_ascii=False)
    matches = list(re.finditer(re.escape(marker) + r'\s*:\s*\{', text))
    if len(matches) != 1:
        raise SystemExit(f'FAIL: source object is not unique: {sid}')
    obj_start = matches[0].end() - 1
    obj_end = object_end(text, obj_start)
    segment = text[obj_start:obj_end]
    tmarker = re.search(r'"translations"\s*:\s*\{', segment)
    if not tmarker:
        raise SystemExit(f'FAIL: translations object missing: {sid}')
    trans_start = tmarker.end() - 1
    trans_end = object_end(segment, trans_start)
    prefix = segment[:trans_start]
    translations = segment[trans_start:trans_end]
    suffix = segment[trans_end:]
    locale = row['locale']
    old = json.dumps(row['currentTarget'], ensure_ascii=False)
    pattern = re.compile(r'(' + re.escape(json.dumps(locale, ensure_ascii=False)) + r'\s*:\s*)' + re.escape(old))
    found = list(pattern.finditer(translations))
    if len(found) != 1:
        raise SystemExit(f'FAIL: exact current target literal is not unique: {sid}/{locale}')
    updated_translations = pattern.sub(lambda match: match.group(1) + json.dumps(row['selectedTarget'], ensure_ascii=False), translations, count=1)
    return text[:obj_start] + prefix + updated_translations + suffix + text[obj_end:]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=pathlib.Path, required=True)
    parser.add_argument('--cross-packet', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    packet = args.cross_packet.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    subprocess.run([sys.executable, str(packet / 'verify_cross_packet.py')], check=True)
    manifest = read_json(packet / 'cross-manifest.json')
    selected = read_jsonl(packet / 'selected-proposals.jsonl')
    noops = read_jsonl(packet / 'no-op-ledger.jsonl')
    head = git(repo, 'rev-parse', 'HEAD')
    tree = git(repo, 'rev-parse', 'HEAD^{tree}')
    status = git(repo, 'status', '--porcelain=v1')
    if (head, tree) != (EXPECTED_HEAD, EXPECTED_TREE) or status:
        raise SystemExit('FAIL: exact source pin or clean worktree guard')

    path = repo / CATALOG
    before_raw = path.read_bytes()
    before_sha = sha(before_raw)
    if before_sha != manifest['catalogFileSha256']:
        raise SystemExit('FAIL: pinned pre-catalog checksum')
    before = json.loads(before_raw.decode('utf-8'))
    keys = list(before['messages'])
    if sha(('\n'.join(keys) + '\n').encode('utf-8')) != manifest['catalogKeyOrderSha256']:
        raise SystemExit('FAIL: catalog key order hash')
    if len(keys) != 1836 or keys[585:605] != list(dict.fromkeys(row['sourceId'] for row in [next(r for r in selected + noops if r['position'] == pos) for pos in POSITIONS])):
        raise SystemExit('FAIL: catalog window positions/order')
    locale_registry_order = list(before['locales'])
    if not all(locale in before['locales'] for locale in LOCALES):
        raise SystemExit('FAIL: selected locale missing from pinned registry')

    rows_by_key = {}
    for row in selected + noops:
        key = (row['position'], row['locale'])
        if key in rows_by_key:
            raise SystemExit('FAIL: duplicate apply/readback cell')
        rows_by_key[key] = row
    if len(rows_by_key) != 240 or set(pos for pos, _ in rows_by_key) != set(POSITIONS) or set(loc for _, loc in rows_by_key) != set(LOCALES):
        raise SystemExit('FAIL: cross packet cell coverage')

    expected = copy.deepcopy(before)
    for row in selected:
        item = before['messages'].get(row['sourceId'])
        if item is None or keys[row['position']] != row['sourceId']:
            raise SystemExit('FAIL: selected source identity/order: ' + row['sourceId'])
        if item['source'] != row['source'] or sha(item['source']) != row['sourceSha256']:
            raise SystemExit('FAIL: selected source hash: ' + row['sourceId'] + '/' + row['locale'])
        old = item['translations'][row['locale']]
        if old != row['currentTarget'] or sha(old) != row['currentTargetSha256']:
            raise SystemExit('FAIL: exact current-target SHA guard: ' + row['sourceId'] + '/' + row['locale'])
        target = row['selectedTarget']
        if sha(target) != row['selectedTargetSha256'] or target == old:
            raise SystemExit('FAIL: selected-target SHA guard: ' + row['sourceId'] + '/' + row['locale'])
        expected['messages'][row['sourceId']]['translations'][row['locale']] = target

    for row in noops:
        item = before['messages'].get(row['sourceId'])
        if item is None or keys[row['position']] != row['sourceId'] or sha(item['source']) != row['sourceSha256']:
            raise SystemExit('FAIL: no-op source hash/order: ' + row['sourceId'] + '/' + row['locale'])
        old = item['translations'][row['locale']]
        if sha(old) != row['currentTargetSha256']:
            raise SystemExit('FAIL: preserved no-op current-target SHA guard: ' + row['sourceId'] + '/' + row['locale'])

    changed_text = before_raw.decode('utf-8')
    for row in selected:
        changed_text = replace_translation(changed_text, row)
    after_raw = changed_text.encode('utf-8')
    after = json.loads(after_raw.decode('utf-8'))
    if after != expected:
        raise SystemExit('FAIL: byte-level update changed data beyond the 22 selected locale values')
    if list(after['messages']) != keys or list(after['locales']) != locale_registry_order:
        raise SystemExit('FAIL: catalog key or locale registry order changed')
    for row in selected:
        new = after['messages'][row['sourceId']]['translations'][row['locale']]
        if new != row['selectedTarget'] or sha(new) != row['selectedTargetSha256']:
            raise SystemExit('FAIL: selected-target readback: ' + row['sourceId'] + '/' + row['locale'])
    for row in noops:
        new = after['messages'][row['sourceId']]['translations'][row['locale']]
        if sha(new) != row['currentTargetSha256']:
            raise SystemExit('FAIL: no-op/hold changed: ' + row['sourceId'] + '/' + row['locale'])

    # Preserve a before-image for local application evidence, then write only the catalog.
    (output / 'ui-labels-before.json').write_bytes(before_raw)
    path.write_bytes(after_raw)
    actual_raw = path.read_bytes()
    if actual_raw != after_raw or sha(actual_raw) != sha(after_raw):
        raise SystemExit('FAIL: post-write catalog readback')
    result = {
        'result': 'APPLIED_LOCALLY',
        'head': head,
        'tree': tree,
        'catalogPath': CATALOG,
        'preCatalogSha256': before_sha,
        'postCatalogSha256': sha(actual_raw),
        'catalogKeyOrderSha256': sha(('\n'.join(keys) + '\n').encode('utf-8')),
        'localeRegistryOrderPreserved': list(after['locales']) == list(before['locales']),
        'selectedCellCount': len(selected),
        'noOpCellCount': len(noops),
        'callerlessHashOnlyHoldCount': sum(row['crossDisposition'] == 'HOLD_HASH_ONLY' for row in noops),
        'callerfulKeepCurrentCount': sum(row['crossDisposition'] == 'KEEP_CURRENT' for row in noops),
        'onlyProductPathChanged': 'romarr/ui-labels.json',
    }
    (output / 'apply-result.json').write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))

if __name__ == '__main__':
    main()
