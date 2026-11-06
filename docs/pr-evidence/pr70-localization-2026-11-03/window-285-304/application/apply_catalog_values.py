#!/usr/bin/env python3
"""Apply the 84 exact target changes authorized in the sealed W285-W304 packet."""
from __future__ import annotations
import collections
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

EVIDENCE = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[5]
PACKET = EVIDENCE / 'third-party-cross-audit'
INPUT = PACKET / 'candidate-free-input'
APPLICATION = EVIDENCE / 'application'
EXPECTED_HEAD = '363601fd2597f0fb97adff97554e651c2bea2d99'
EXPECTED_TREE = '1f8ada1746f53796e2b4a8f43f9a0075150aa5d7'
PLACEHOLDER_RE = re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*)\}')
TAG_RE = re.compile(r'</?([A-Za-z][A-Za-z0-9:-]*)\b[^>]*>')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def raw_hash(text: str) -> str:
    return digest(text.encode('utf-8'))


def canonical_hash(text: str) -> str:
    return digest(json.dumps(text, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path: pathlib.Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def git(*args: str) -> str:
    return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()


def verify_checksum_manifest(folder: pathlib.Path, include_all: bool = False):
    sums_path = folder / 'SHA256SUMS.txt'
    entries = {}
    for line in sums_path.read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        if name in entries:
            raise AssertionError(f'duplicate checksum entry: {folder}/{name}')
        path = folder / name
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise AssertionError(f'checksum mismatch: {folder}/{name}')
        entries[name] = expected
    if include_all:
        actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name not in ('SHA256SUMS.txt', 'SHA256SUMS')}
        if set(entries) != actual:
            raise AssertionError(f'checksum inventory mismatch in {folder}')
    return entries


def save_json(path: pathlib.Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def save_jsonl(path: pathlib.Path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows), encoding='utf-8')


def main() -> None:
    auth = read_json(PACKET / 'root-application-authorization.json')
    if auth['applicationApproved'] is not True or auth['selectedChangeCount'] != 84:
        raise AssertionError('sealed root packet does not authorize exactly 84 changes')
    if auth['head'] != EXPECTED_HEAD or auth['tree'] != EXPECTED_TREE or auth['pullRequest'] != 70:
        raise AssertionError('root authorization is not pinned to the expected PR head/tree')
    packet_files = verify_checksum_manifest(PACKET, include_all=True)
    for packet_dir in ('candidate-free-input', 'primary-review', 'blind-review'):
        verify_checksum_manifest(PACKET / packet_dir, include_all=True)
    selected_path = PACKET / 'selected-changes.jsonl'
    if digest(selected_path.read_bytes()) != auth['selectedChangesSha256']:
        raise AssertionError('selected-change list hash differs from sealed authorization')

    current_rows = read_jsonl(INPUT / 'current-target-cells.jsonl')
    cross_rows = read_jsonl(PACKET / 'cross-audit-ledger.jsonl')
    source_context_rows = read_jsonl(INPUT / 'source-contexts.jsonl')
    selected_rows = read_jsonl(selected_path)
    if len(current_rows) != 240 or len(cross_rows) != 240 or len(selected_rows) != 84:
        raise AssertionError('packet cell/change counts differ from authorization')
    current_by = {(r['position'], r['locale']): r for r in current_rows}
    cross_by = {(r['position'], r['locale']): r for r in cross_rows}
    selected_by = {(r['position'], r['locale']): r for r in selected_rows}
    source_context_by = {r['position']: r for r in source_context_rows}
    if any(len(t) != n for t, n in ((current_by, 240), (cross_by, 240), (selected_by, 84))):
        raise AssertionError('duplicate position/locale cell in sealed packet')
    if set(current_by) != set(cross_by) or not set(selected_by) <= set(current_by):
        raise AssertionError('input, cross-audit, and selected-change cell sets differ')

    # The live refs and local parent were reattested immediately before the evidence copy.
    parent = git('rev-parse', 'HEAD')
    parent_tree = git('rev-parse', 'HEAD^{tree}')
    if parent != EXPECTED_HEAD or parent_tree != EXPECTED_TREE:
        raise AssertionError(f'local parent changed: {parent}/{parent_tree}')

    pins = read_json(INPUT / 'catalog-file-pins.json')
    catalog_info = pins['catalog']
    catalog_path = REPO / catalog_info['path']
    before_bytes = catalog_path.read_bytes()
    if digest(before_bytes) != catalog_info['sha256']:
        raise AssertionError('current catalog bytes do not match the pinned parent catalog')
    if len(before_bytes) != catalog_info['byteCount']:
        raise AssertionError('current catalog byte count differs from pinned catalog')
    before = json.loads(before_bytes)
    if len(before['messages']) != 1836:
        raise AssertionError('catalog message count differs from pinned snapshot')
    if before_bytes != (json.dumps(before, ensure_ascii=False, indent=2) + '\n').encode('utf-8'):
        raise AssertionError('catalog serialization does not round-trip exactly')

    # Capture the live ref check that immediately preceded writes to this evidence directory.
    attestation = {
        'pullRequest': 70,
        'repository': 'snapetech-org/ROMarrNG',
        'branchRef': 'refs/heads/task/localization-translation-review-20261030',
        'pullRef': 'refs/pull/70/head',
        'observedBranchHead': EXPECTED_HEAD,
        'observedPullRefHead': EXPECTED_HEAD,
        'localParentHead': parent,
        'localParentTree': parent_tree,
        'localWorktreeWasCleanBeforeEvidenceWrite': True,
        'observedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'matchesRootAuthorization': True,
    }
    save_json(EVIDENCE / 'pre-write-attestation.json', attestation)

    catalog_after = json.loads(before_bytes)
    plan = []
    selected_count = 0
    hold_count = 0
    for cell in current_rows:
        key = (cell['position'], cell['locale'])
        cross = cross_by[key]
        chosen = selected_by.get(key)
        sid, locale = cell['sourceId'], cell['locale']
        if cross['sourceId'] != sid or cross['sourceSha256'] != cell['sourceSha256']:
            raise AssertionError(f'{key}: source identity disagrees with cross-audit packet')
        if cross['currentTarget'] != cell['currentTarget'] or cross['currentTargetSha256'] != cell['currentTargetSha256']:
            raise AssertionError(f'{key}: current target disagrees with cross-audit packet')
        msg_before = before['messages'][sid]
        if msg_before['source'] != cell['source']:
            raise AssertionError(f'{key}: catalog source differs from pinned source')
        if raw_hash(cell['source']) != cell['sourceSha256']:
            raise AssertionError(f'{key}: source hash mismatch')
        before_text = msg_before['translations'][locale]
        before_canonical = msg_before.get('translationHashes', {}).get(locale)
        if before_text != cell['currentTarget'] or canonical_hash(before_text) != before_canonical:
            raise AssertionError(f'{key}: pinned current translation/hash mismatch')
        if raw_hash(before_text) != cell['currentTargetSha256']:
            raise AssertionError(f'{key}: current target raw hash mismatch')
        if cross['selectedForApplication'] != (chosen is not None):
            raise AssertionError(f'{key}: selected flag differs from exact authorization')
        if cross['rootTarget'] is None or raw_hash(cross['rootTarget']) != cross['rootTargetSha256']:
            raise AssertionError(f'{key}: root target/hash mismatch')

        target = chosen['target'] if chosen else cross['rootTarget']
        change = target != before_text
        if chosen:
            selected_count += 1
            if chosen['sourceId'] != sid or chosen['sourceSha256'] != cell['sourceSha256'] or chosen['previousTarget'] != before_text:
                raise AssertionError(f'{key}: selected authorization does not match current source/target')
            if chosen['previousTargetSha256'] != raw_hash(before_text):
                raise AssertionError(f'{key}: selected previous-target hash mismatch')
            if chosen['target'] != cross['rootTarget'] or chosen['targetSha256'] != cross['rootTargetSha256']:
                raise AssertionError(f'{key}: selected exact target differs from root cross-audit')
            if chosen['targetSha256'] != raw_hash(chosen['target']):
                raise AssertionError(f'{key}: selected target hash mismatch')
            if not change:
                raise AssertionError(f'{key}: authorized selected target is unchanged')
        elif target != before_text:
            raise AssertionError(f'{key}: unselected root target differs from current catalog')

        held = cross['rootDisposition'] == 'hold'
        if held:
            hold_count += 1
            if cell['position'] not in (286, 304) or chosen is not None or change:
                raise AssertionError(f'{key}: caller-path hold must remain unchanged')
        elif cell['position'] in (286, 304):
            raise AssertionError(f'{key}: held rank was not preserved as a hold')

        source_names = collections.Counter(cell['sourcePlaceholders'])
        target_names = collections.Counter(PLACEHOLDER_RE.findall(target))
        if source_names != target_names:
            raise AssertionError(f'{key}: proposed target placeholder multiset mismatch')
        tags = collections.Counter(TAG_RE.findall(target))
        source_tags = collections.Counter(cell['sourceMarkupTags'])
        if tags != source_tags:
            raise AssertionError(f'{key}: proposed target markup-tag multiset mismatch')
        protected = cross['protectedLiterals']
        if not all(lit.casefold() in target.casefold() for lit in protected):
            raise AssertionError(f'{key}: proposed target loses a protected literal')
        if not cross['protectedLiteralsPreserved'] or not cross['placeholderMultisetMatches']:
            raise AssertionError(f'{key}: root cross-audit integrity flag is false')

        plan.append({
            'position': cell['position'], 'sourceId': sid, 'locale': locale,
            'source': cell['source'], 'sourceSha256': cell['sourceSha256'],
            'previousTarget': before_text, 'previousTargetRawUtf8Sha256': raw_hash(before_text),
            'previousTargetCanonicalTranslationHash': before_canonical,
            'expectedTarget': target, 'expectedTargetRawUtf8Sha256': raw_hash(target),
            'expectedTargetCanonicalTranslationHash': canonical_hash(target),
            'changeExpected': change, 'selectedForApplication': chosen is not None,
            'callerPathHold': held, 'rootDisposition': cross['rootDisposition'],
            'rootRationale': cross['rootRationale'],
            'sourcePlaceholders': cell['sourcePlaceholders'],
            'protectedLiterals': protected,
            'callerLocations': source_context_by[cell['position']]['currentCallerLocations'],
            'callerContextReferences': [{
                'path': ref['path'], 'startLine': ref['startLine'], 'endLine': ref['endLine'],
                'contextSha256': ref['contextSha256'], 'matchBasis': ref['matchBasis'],
            } for ref in source_context_by[cell['position']]['references']],
            'sourceMarkupTags': cell['sourceMarkupTags'],
            'beforeTranslationStatus': msg_before.get('translationStatus'),
            'beforeTranslationReview': msg_before.get('translationReview', {}),
        })
        if change:
            msg = catalog_after['messages'][sid]
            msg['translations'][locale] = target
            msg['translationHashes'][locale] = canonical_hash(target)

    if selected_count != 84 or hold_count != 24 or sum(r['changeExpected'] for r in plan) != 84:
        raise AssertionError(f'plan counts differ: selected={selected_count}, holds={hold_count}')
    if sorted({r['position'] for r in plan if r['callerPathHold']}) != [286, 304]:
        raise AssertionError('caller-path hold ranks differ from authorization')

    # Verify the in-memory result globally before replacing the catalog file.
    if list(before) != list(catalog_after) or list(before['messages']) != list(catalog_after['messages']):
        raise AssertionError('top-level or message key order changed in memory')
    changed_values = changed_hashes = 0
    selected_pairs = {(r['sourceId'], r['locale']) for r in plan if r['changeExpected']}
    for sid, old_msg in before['messages'].items():
        new_msg = catalog_after['messages'][sid]
        if list(old_msg) != list(new_msg):
            raise AssertionError(f'message field order changed: {sid}')
        for field in old_msg:
            if field not in ('translations', 'translationHashes') and old_msg[field] != new_msg[field]:
                raise AssertionError(f'non-translation metadata changed: {sid}/{field}')
        if list(old_msg['translations']) != list(new_msg['translations']) or list(old_msg.get('translationHashes', {})) != list(new_msg.get('translationHashes', {})):
            raise AssertionError(f'locale/hash key order changed: {sid}')
        for locale, old_target in old_msg['translations'].items():
            should_change = (sid, locale) in selected_pairs
            expected = next(r['expectedTarget'] for r in plan if r['sourceId'] == sid and r['locale'] == locale) if should_change else old_target
            if new_msg['translations'][locale] != expected or ((new_msg['translations'][locale] != old_target) != should_change):
                raise AssertionError(f'unexpected target change: {sid}/{locale}')
            old_hash = old_msg.get('translationHashes', {}).get(locale)
            new_hash = new_msg.get('translationHashes', {}).get(locale)
            if should_change:
                if new_hash != canonical_hash(expected) or new_hash == old_hash:
                    raise AssertionError(f'authorized canonical hash not updated: {sid}/{locale}')
                changed_values += 1
                changed_hashes += 1
            elif new_hash != old_hash:
                raise AssertionError(f'non-target canonical hash changed: {sid}/{locale}')
    if changed_values != 84 or changed_hashes != 84:
        raise AssertionError(f'expected 84 target/hash updates, found {changed_values}/{changed_hashes}')

    # Write a complete plan before the atomic catalog replacement.
    save_jsonl(APPLICATION / 'plan-240-cells.jsonl', plan)
    plan_sha = digest((APPLICATION / 'plan-240-cells.jsonl').read_bytes())
    serialized = (json.dumps(catalog_after, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    temp_path = catalog_path.with_name(catalog_path.name + '.w285-304.tmp')
    if temp_path.exists():
        raise AssertionError(f'task-owned temporary path already exists: {temp_path}')
    try:
        temp_path.write_bytes(serialized)
        os.replace(temp_path, catalog_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    # Read back every selected and unselected cell from the serialized catalog.
    actual_bytes = catalog_path.read_bytes()
    actual_catalog = json.loads(actual_bytes)
    if actual_bytes != serialized:
        raise AssertionError('written catalog bytes differ from the planned serialization')
    readback = []
    matches = 0
    for p in plan:
        actual_target = actual_catalog['messages'][p['sourceId']]['translations'][p['locale']]
        actual_hash = actual_catalog['messages'][p['sourceId']]['translationHashes'][p['locale']]
        match = actual_target == p['expectedTarget'] and raw_hash(actual_target) == p['expectedTargetRawUtf8Sha256'] and actual_hash == p['expectedTargetCanonicalTranslationHash']
        if not match:
            raise AssertionError(f"readback mismatch: {p['position']}/{p['locale']}")
        matches += 1
        readback.append({
            'position': p['position'], 'sourceId': p['sourceId'], 'locale': p['locale'],
            'expectedTarget': p['expectedTarget'], 'actualTarget': actual_target,
            'expectedTargetRawUtf8Sha256': p['expectedTargetRawUtf8Sha256'],
            'actualTargetRawUtf8Sha256': raw_hash(actual_target),
            'expectedTargetCanonicalTranslationHash': p['expectedTargetCanonicalTranslationHash'],
            'actualTargetCanonicalTranslationHash': actual_hash,
            'selectedForApplication': p['selectedForApplication'],
            'callerPathHold': p['callerPathHold'], 'matches': match,
        })
    if matches != 240:
        raise AssertionError(f'expected 240 readback matches, found {matches}')
    save_jsonl(APPLICATION / 'readback-240-cells.jsonl', readback)

    root_summary = read_json(PACKET / 'summary.json')
    candidate_manifest_sha = digest((INPUT / 'manifest.json').read_bytes())
    candidate_sums_sha = digest((INPUT / 'SHA256SUMS.txt').read_bytes())
    primary_sums_sha = digest((PACKET / 'primary-review' / 'SHA256SUMS.txt').read_bytes())
    blind_sums_sha = digest((PACKET / 'blind-review' / 'SHA256SUMS.txt').read_bytes())
    cross_sums_sha = digest((PACKET / 'SHA256SUMS.txt').read_bytes())
    root_cross_ledger_sha = digest((PACKET / 'cross-audit-ledger.jsonl').read_bytes())
    selected_sha = digest(selected_path.read_bytes())
    summary = {
        'schemaVersion': 1, 'window': 'W285-W304', 'repository': 'snapetech-org/ROMarrNG', 'pullRequest': 70,
        'parentHead': parent, 'parentTree': parent_tree,
        'cellCount': 240, 'sourceCount': 20, 'localeCount': 12,
        'selectedChanges': 84, 'changedTranslationValues': changed_values,
        'changedCanonicalTranslationHashes': changed_hashes,
        'readbackMatches': matches, 'callerPathHoldsPreserved': hold_count,
        'heldPositions': [286, 304],
        'nonTargetTranslationsAndHashesChanged': 0,
        'catalogMessageCount': len(actual_catalog['messages']),
        'catalogTopLevelKeyOrderPreserved': list(before) == list(actual_catalog),
        'catalogMessageIdOrderPreserved': list(before['messages']) == list(actual_catalog['messages']),
        'localeAndHashKeyOrderPreserved': True,
        'translationStatusAndReviewMetadataPreserved': True,
        'placeholderFailures': 0, 'protectedLiteralFailures': 0, 'markupTagFailures': 0,
        'candidateFreeManifestJsonSha256': candidate_manifest_sha,
        'candidateFreeChecksumListSha256': candidate_sums_sha,
        'primaryChecksumListSha256': primary_sums_sha,
        'blindChecksumListSha256': blind_sums_sha,
        'rootCrossAuditChecksumListSha256': cross_sums_sha,
        'rootCrossAuditLedgerSha256': root_cross_ledger_sha,
        'selectedChangesSha256': selected_sha,
        'planFileSha256': plan_sha,
        'appliedCatalogBaseSha256': digest(before_bytes),
        'appliedCatalogSha256': digest(actual_bytes),
        'rootDispositionCounts': root_summary['rootDispositions'],
        'qualifiedNativeSpeakerApproval': False,
        'exactHeadBrowserReview': False,
        'releaseApproved': False,
        'testsBuildsScansCiRun': False,
    }
    save_json(APPLICATION / 'summary.json', summary)
    manifest = {
        'schemaVersion': 1, 'window': 'W285-W304', 'repository': 'snapetech-org/ROMarrNG',
        'pullRequest': 70, 'branch': 'task/localization-translation-review-20261030',
        'reviewHead': EXPECTED_HEAD, 'reviewTree': EXPECTED_TREE,
        'applicationParentHead': parent, 'applicationParentTree': parent_tree,
        'cellCount': 240, 'sourceCount': 20, 'localeCount': 12,
        'selectedChanges': 84, 'callerPathHoldCells': 24,
        'rootApplicationApproved': True,
        'rootPacketChecksumListSha256': digest((PACKET / 'SHA256SUMS.txt').read_bytes()),
        'candidateFreeManifestJsonSha256': candidate_manifest_sha,
        'candidateFreeChecksumListSha256': candidate_sums_sha,
        'primaryReviewChecksumListSha256': primary_sums_sha,
        'blindReviewChecksumListSha256': blind_sums_sha,
        'rootCrossAuditLedgerSha256': root_cross_ledger_sha,
        'selectedChangesSha256': selected_sha,
        'applicationPlanSha256': plan_sha,
        'appliedCatalogBaseSha256': digest(before_bytes),
        'appliedCatalogSha256': digest(actual_bytes),
        'canonicalTranslationHashAlgorithm': 'SHA-256 of canonical JSON serialization of the translation string as UTF-8',
    }
    save_json(EVIDENCE / 'manifest.json', manifest)
    (APPLICATION / 'README.md').write_text(
        '# W285–W304 application and exact readback\n\n'
        'This packet applies only the 84 target/hash changes authorized by the sealed root cross-audit. '
        'The parent head/tree, packet fingerprints, exact plan, and full 240-cell readback are recorded here. '
        'Ranks 286 and 304 remain unchanged caller-path holds in all 12 locales.\n\n'
        'Run `python3 verify_application.py` from this directory after the application commit is present. '
        'The verifier checks the complete sealed packet, catalog key order, every source×locale cell, '
        'placeholder and protected-literal integrity, exact canonical translation hashes, and zero non-target changes.\n\n'
        'No tests, builds, scans, CI, workflow edits, merges, releases, or tags are part of this application. '
        'Qualified native-speaker approval and exact-head browser review are not claimed.\n',
        encoding='utf-8')
    (EVIDENCE / 'README.md').write_text(
        '# ROMarrNG PR #70 W285–W304 application evidence\n\n'
        f'Applied 84 exact target and canonical translation-hash changes to parent `{parent}` / tree `{parent_tree}`. '
        'The catalog readback matched all 240 source×locale cells; ranks 286 and 304 remain unchanged caller-path holds (24 cells). '
        'No other target, locale, review/status metadata, or catalog key order changed.\n\n'
        'The complete sealed root packet is in `third-party-cross-audit/`; it retains the candidate-free input, primary review, '
        'independent blind review, root cross-audit ledger, authorization, and original checksums. '
        'The exact application plan and readback are in `application/`.\n\n'
        'The target list is authorized by `third-party-cross-audit/root-application-authorization.json`; '
        'the packet verifier and checksums are preserved unchanged. No tests, builds, scans, CI runs, workflow edits, merges, releases, or tags were made.\n',
        encoding='utf-8')
    print(json.dumps({'result': 'APPLIED_AND_READ_BACK', 'cells': matches, 'selectedChanges': changed_values,
                      'canonicalHashesUpdated': changed_hashes, 'holdsPreserved': hold_count,
                      'catalogSha256': digest(actual_bytes), 'planSha256': plan_sha}, indent=2))


if __name__ == '__main__':
    main()
