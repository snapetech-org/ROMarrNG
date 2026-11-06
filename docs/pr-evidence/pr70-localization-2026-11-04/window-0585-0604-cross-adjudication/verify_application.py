#!/usr/bin/env python3
"""Verify sealed W585-W604 inputs, exact product commit, holds, and 240-cell readback."""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import pathlib
import subprocess
import sys

CATALOG = 'romarr/ui-labels.json'
BASE_HEAD = '01da053f0e6a47e7184fb86da77f66b7b6719653'
BASE_TREE = 'dcb9c1766831e217ffca7fb77068b97c33b9524e'
LOCALES = ['ar', 'de', 'es', 'fr', 'hi', 'id', 'ja', 'ko', 'pt-BR', 'vi', 'zh-Hans', 'zh-Hant']
POSITIONS = list(range(585, 605))
HOLD_FORBIDDEN = {'sourceId', 'source', 'sourceText', 'currentTarget', 'beforeTarget', 'afterTarget', 'proposedTarget', 'selectedTarget', 'recommendedTarget', 'rationale'}

def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode('utf-8')).hexdigest()

def need(condition, message):
    if not condition:
        raise SystemExit('FAIL: ' + message)

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def read_jsonl(path):
    rows = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            rows.append((json.loads(raw), sha(raw)))
    return rows

def checksum_dir(root, sums_name='SHA256SUMS.txt'):
    root = pathlib.Path(root)
    sums_path = root / sums_name
    listed = {}
    for line_number, line in enumerate(sums_path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        digest, relative = line.split(None, 1)
        relative = relative.strip().lstrip('*')
        path = (root / relative).resolve()
        need(path.is_relative_to(root.resolve()) and path.is_file(), f'unsafe/missing checksum path {root}/{relative}')
        need(sha(path.read_bytes()) == digest, f'checksum mismatch {root}/{relative}')
        need(relative not in listed, f'duplicate checksum path {root}/{relative} at line {line_number}')
        listed[relative] = digest
    actual = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file() and path.relative_to(root).as_posix() != sums_name}
    need(set(listed) == actual, f'checksum coverage mismatch in {root}')
    return listed

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=pathlib.Path, required=True, help='ROMarrNG worktree containing the product/evidence commit')
    args = parser.parse_args()
    repo = args.repo.resolve()
    root = pathlib.Path(__file__).resolve().parent

    checksum_dir(root)
    evidence_manifest = read_json(root / 'manifest.json')
    need(evidence_manifest['artifact'] == 'ROMarrNG PR #70 W585-W604 application evidence', 'evidence artifact identity')
    manifest_files = evidence_manifest['files']
    actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix() not in {'manifest.json', 'SHA256SUMS.txt'}}
    need(set(manifest_files) == actual_files, 'evidence manifest file coverage')
    for relative, record in manifest_files.items():
        path = root / relative
        need(path.stat().st_size == record['bytes'] and sha(path.read_bytes()) == record['sha256'], 'evidence manifest hash ' + relative)

    inputs = root / 'inputs'
    candidate_root = inputs / 'candidate-free'
    candidate = candidate_root / 'candidate-free' / 'input'
    primary_root = inputs / 'primary'
    primary_bundle = primary_root / 'candidate-free-bundle'
    primary_output = primary_root / 'primary-output'
    blind_root = inputs / 'blind'
    blind_packet = blind_root / 'sealed-blind-packet'
    cross_root = root / 'cross-review'

    candidate_outer_sums = checksum_dir(candidate_root)
    candidate_sums = checksum_dir(candidate)
    candidate_manifest = read_json(candidate / 'manifest.json')
    need(candidate_manifest['head'] == BASE_HEAD and candidate_manifest['tree'] == BASE_TREE and candidate_manifest['candidateFree'] is True and candidate_manifest['proposedTargetsIncluded'] is False, 'candidate-free exact pin/scope')
    need(len(candidate_sums) == 27 and candidate_manifest['cellCount'] == 240, 'candidate-free coverage')

    primary_bundle_sums = checksum_dir(primary_bundle)
    primary_output_sums = checksum_dir(primary_output)
    primary_pre = read_json(primary_root / 'PRIMARY-REVIEW-MANIFEST.json')
    primary_manifest = read_json(primary_output / 'primary-manifest.json')
    need(primary_pre['head'] == BASE_HEAD and primary_pre['tree'] == BASE_TREE and primary_pre['candidateFreeBundleChecksumVerification'] == 'PASS', 'primary pre-review pin')
    need(primary_manifest['head'] == BASE_HEAD and primary_manifest['tree'] == BASE_TREE and primary_manifest['nativeSpeakerApproval'] is False, 'primary output pin/limitation')
    need(len(primary_output_sums) == 5 and len(primary_bundle_sums) == 33, 'primary packet checksum coverage')

    blind_seal = read_json(blind_packet / 'sealed-manifest.json')
    sidecar = (blind_packet / 'sealed-manifest.sha256').read_text(encoding='ascii').split()
    need(sidecar == [sha((blind_packet / 'sealed-manifest.json').read_bytes()), 'sealed-manifest.json'], 'blind sealed-manifest sidecar')
    blind_manifest = read_json(blind_root / 'blindness-manifest.json')
    need(blind_seal['pin']['head'] == BASE_HEAD and blind_seal['pin']['tree'] == BASE_TREE, 'blind exact pin')
    need(blind_seal['input']['blindnessManifestSha256'] == sha((blind_root / 'blindness-manifest.json').read_bytes()), 'blindness manifest hash')
    need(blind_seal['input']['sha256sumsFileSha256'] == sha((candidate / 'SHA256SUMS.txt').read_bytes()), 'blind candidate-free input checksum reference')
    need(blind_seal['input']['verifiedInputFileCount'] == 27, 'blind input count')
    for name, record in blind_seal['files'].items():
        path = blind_packet / name
        need(path.is_file() and sha(path.read_bytes()) == record, 'blind packet digest ' + name)
    blind_decisions = read_jsonl(blind_packet / 'blind-decisions.jsonl')
    need(len(blind_decisions) == 240, 'blind decision cell count')

    subprocess.run([sys.executable, str(cross_root / 'verify_cross_packet.py')], check=True, stdout=subprocess.DEVNULL)
    cross_manifest = read_json(cross_root / 'cross-manifest.json')
    need(cross_manifest['pin']['head'] == BASE_HEAD and cross_manifest['pin']['tree'] == BASE_TREE, 'cross-review exact pin')

    input_cells = { (row['position'], row['locale']): (row, digest) for row, digest in read_jsonl(candidate / 'current-target-cells.jsonl') }
    source_contexts = {row['sourceId']: row for row, _ in read_jsonl(candidate / 'source-contexts.jsonl')}
    primary = { (row['position'], row['locale']): (row, digest) for row, digest in read_jsonl(primary_output / 'dispositions.jsonl') }
    blind = { (row['catalogPosition'], row['locale']): (row, digest) for row, digest in blind_decisions }
    selected = { (row['position'], row['locale']): (row, digest) for row, digest in read_jsonl(cross_root / 'selected-proposals.jsonl') }
    noops = { (row['position'], row['locale']): (row, digest) for row, digest in read_jsonl(cross_root / 'no-op-ledger.jsonl') }
    expected_keys = {(position, locale) for position in POSITIONS for locale in LOCALES}
    need(set(input_cells) == set(primary) == set(blind) == set(selected) | set(noops) == expected_keys, 'upstream exact 240-cell coverage')
    need(not (set(selected) & set(noops)) and len(selected) == 22 and len(noops) == 218, 'cross selection/no-op partition')

    for key, (cell, input_digest) in input_cells.items():
        context = source_contexts[cell['sourceId']]
        p, _ = primary[key]
        b, _ = blind[key]
        need(sha(cell['source']) == cell['sourceSha256'] and sha(cell['currentTarget']) == cell['currentTargetSha256'], 'candidate-free row hashes ' + str(key))
        need(p['sourceSha256'] == b['sourceSha256'] == cell['sourceSha256'], 'upstream source hash ' + str(key))
        need(p['currentTargetSha256'] == b['currentTargetSha256'] == cell['currentTargetSha256'], 'upstream target hash ' + str(key))
        need(p['callerContextSha256'] == b['callerContextSha256'] == cell['callerContextSha256'] == context['contextSha256'], 'upstream caller-context hash ' + str(key))
        if key in selected:
            decision, _ = selected[key]
            need(decision['primaryDisposition'] == p['disposition'] and decision['blindDisposition'] == b['disposition'], 'selected review outcome linkage ' + str(key))
            need(decision['selectedTarget'] in {p.get('proposedTarget'), b.get('proposedTarget')}, 'selected proposal source ' + str(key))
        else:
            decision, _ = noops[key]
            need(decision['primaryDisposition'] == p['disposition'] and decision['blindDisposition'] == b['disposition'], 'no-op review outcome linkage ' + str(key))

    application = root / 'application'
    pins = read_json(application / 'catalog-pins.json')
    summary = read_json(application / 'application-summary.json')
    product_record = read_json(application / 'product-commit.json')
    before_att = read_json(application / 'PR-attestation-before.json')
    after_att = read_json(application / 'PR-attestation-after-product.json')
    product = product_record['productCommit']
    product_tree = product_record['productTree']
    need(product_record['parentCommit'] == BASE_HEAD and product_record['productPath'] == CATALOG, 'product commit parent/path')
    need(product == summary['productCommit'] and product_tree == summary['productTree'], 'summary/product commit linkage')
    need(git(repo, 'rev-parse', product) == product and git(repo, 'rev-parse', product + '^{tree}') == product_tree, 'product commit/tree object')
    need(git(repo, 'rev-parse', product + '^') == BASE_HEAD, 'product commit parent exact base')
    need(git(repo, 'merge-base', '--is-ancestor', product, 'HEAD') == '', 'product commit is not on current branch history')
    changed_paths = git(repo, 'diff-tree', '--no-commit-id', '--name-only', '-r', product).splitlines()
    need(changed_paths == [CATALOG], 'product commit changed a non-catalog path')
    pre_raw = subprocess.check_output(['git', '-C', str(repo), 'show', f'{BASE_HEAD}:{CATALOG}'])
    post_raw = subprocess.check_output(['git', '-C', str(repo), 'show', f'{product}:{CATALOG}'])
    need(sha(pre_raw) == pins['preCatalogSha256'] == candidate_manifest['catalogSha256'], 'pre-catalog SHA')
    need(sha(post_raw) == pins['postCatalogSha256'], 'post-catalog SHA')
    pre_catalog = json.loads(pre_raw.decode('utf-8'))
    post_catalog = json.loads(post_raw.decode('utf-8'))
    pre_keys = list(pre_catalog['messages'])
    need(len(pre_keys) == 1836 and list(post_catalog['messages']) == pre_keys, 'catalog count/order')
    need(sha(('\n'.join(pre_keys) + '\n').encode('utf-8')) == pins['catalogKeyOrderSha256'] == candidate_manifest['catalogKeyOrderSha256'], 'catalog key-order SHA')
    need(list(pre_catalog['locales']) == pins['localeRegistryOrder'] == list(post_catalog['locales']), 'locale registry order')

    readback = { (row['position'], row['locale']): (row, digest) for row, digest in read_jsonl(application / 'application-readback.jsonl') }
    applied = { (row['position'], row['locale']): row for row, _ in read_jsonl(application / 'selected-applied.jsonl') }
    holds = read_jsonl(application / 'holds.jsonl')
    need(set(readback) == expected_keys and set(applied) == set(selected) and len(holds) == 24, 'application output coverage')
    hold_rows = {(row['position'], row['locale']): row for row, _ in holds}
    hold_set = set(hold_rows)
    need(len(hold_set) == 24, 'duplicate hold ledger cell')
    counts = collections.Counter()
    for key in sorted(expected_keys):
        cell, input_digest = input_cells[key]
        rb, _ = readback[key]
        context = source_contexts[cell['sourceId']]
        need(rb['sourceSha256'] == cell['sourceSha256'] and rb['beforeTargetSha256'] == cell['currentTargetSha256'], 'readback preimage hash ' + str(key))
        need(rb['candidateFreeCellRowSha256'] == input_digest, 'readback candidate-free row hash ' + str(key))
        expected_cross, cross_digest = selected[key] if key in selected else noops[key]
        need(rb['crossDecisionRowSha256'] == cross_digest, 'readback cross-decision row hash ' + str(key))
        need(rb['callerContextSha256'] == cell['callerContextSha256'] and rb['callerless'] == context['callerless'] and rb['callerRefCount'] == len(context['callers']), 'readback caller coverage ' + str(key))
        sid = cell['sourceId']
        locale = cell['locale']
        before_target = pre_catalog['messages'][sid]['translations'][locale]
        after_target = post_catalog['messages'][sid]['translations'][locale]
        need(sha(pre_catalog['messages'][sid]['source']) == cell['sourceSha256'], 'catalog source hash ' + str(key))
        need(sha(before_target) == cell['currentTargetSha256'] and sha(after_target) == rb['afterTargetSha256'], 'catalog readback hash ' + str(key))
        if key in selected:
            decision, _ = selected[key]
            need(not context['callerless'], 'callerless cell selected')
            need(after_target == decision['selectedTarget'] and sha(after_target) == decision['selectedTargetSha256'], 'selected translation value ' + str(key))
            need(rb.get('sourceId') == sid and rb['disposition'] == 'selected-change' and rb['changed'] is True, 'selected readback identity ' + str(key))
            need(applied[key]['afterTargetSha256'] == sha(after_target) and applied[key]['crossDecisionRowSha256'] == cross_digest, 'applied row link ' + str(key))
            counts['selected-change'] += 1
        else:
            decision, _ = noops[key]
            need(after_target == before_target and rb['beforeTargetSha256'] == rb['afterTargetSha256'] and rb['changed'] is False, 'no-op target changed ' + str(key))
            if decision['crossDisposition'] == 'HOLD_HASH_ONLY':
                need(context['callerless'] and key in hold_set, 'hold lineage or callerless flag ' + str(key))
                need(not (HOLD_FORBIDDEN & set(rb)) and rb['disposition'] == 'hold-hash-only', 'hold readback contains text/identifier ' + str(key))
                need(not (HOLD_FORBIDDEN & set(hold_rows[key])), 'hold ledger contains text/identifier ' + str(key))
                counts['hold-hash-only'] += 1
            else:
                need(not context['callerless'] and rb.get('sourceId') == sid and rb['disposition'] == 'keep-current', 'keep-current readback mismatch ' + str(key))
                counts['keep-current'] += 1
    need(counts == {'selected-change': 22, 'keep-current': 194, 'hold-hash-only': 24}, 'final readback totals')
    need(hold_set == {key for key,(row,_) in noops.items() if row['crossDisposition']=='HOLD_HASH_ONLY'}, 'hold ledger coverage')
    need(summary['readbackCellCount'] == 240 and summary['changedCellCount'] == 22 and summary['keptCurrentCellCount'] == 194 and summary['callerlessHashOnlyHoldCount'] == 24, 'application summary totals')
    need(summary['nonTargetProductFilesChanged'] == 0 and summary['translationMetadataChanged'] is False, 'application scope/metadata summary')

    need(before_att['pullRequest']['headSha'] == BASE_HEAD and before_att['refs']['branchRef'] == BASE_HEAD and before_att['refs']['pullHeadRef'] == BASE_HEAD, 'pre-application API/ref pin')
    need(after_att['pullRequest']['headSha'] == product and after_att['pullRequest']['headTree'] == product_tree, 'post-product PR API head/tree')
    need(after_att['refs']['branchRef'] == product and after_att['refs']['pullHeadRef'] == product, 'post-product live refs')
    need(after_att['pullRequest']['state'] == 'open' and after_att['pullRequest']['draft'] is True, 'post-product PR state')
    need(before_att['pullRequest']['bodySha256'] == after_att['pullRequest']['bodySha256'], 'PR body prefix changed before milestone append')
    need(after_att['baseDrift']['apiBaseRefMismatch'] is True, 'known base API/live-main drift omitted')

    print(json.dumps({
        'result': 'PASS',
        'productCommit': product,
        'productTree': product_tree,
        'cells': 240,
        'selectedChanges': counts['selected-change'],
        'keepCurrent': counts['keep-current'],
        'callerlessHashOnlyHolds': counts['hold-hash-only'],
        'crossPacket': 'PASS',
        'candidateFreeInputs': 'PASS',
        'primaryBlindInputs': 'PASS',
        'repoPinReadback': 'PASS',
        'postProductRefs': 'PASS',
    }, sort_keys=True))

if __name__ == '__main__':
    main()
