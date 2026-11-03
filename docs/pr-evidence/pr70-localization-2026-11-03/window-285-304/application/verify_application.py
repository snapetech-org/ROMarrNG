#!/usr/bin/env python3
"""Read-only verifier for the W285-W304 catalog application and retained evidence."""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys

EVIDENCE = pathlib.Path(__file__).resolve().parents[1]
APPLICATION = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path(__file__).resolve().parents[5]
PACKET = EVIDENCE / 'third-party-cross-audit'
INPUT = PACKET / 'candidate-free-input'
EXPECTED_PARENT = '363601fd2597f0fb97adff97554e651c2bea2d99'
EXPECTED_PARENT_TREE = '1f8ada1746f53796e2b4a8f43f9a0075150aa5d7'
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


def check(condition, message: str):
    if not condition:
        raise AssertionError(message)


def verify_manifest(folder: pathlib.Path, *, excluded: set[str] | None = None, include_all: bool = False):
    sums_path = folder / 'SHA256SUMS.txt'
    entries = {}
    for line in sums_path.read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        check(name not in entries, f'duplicate checksum entry {folder}/{name}')
        path = folder / name
        check(path.is_file() and digest(path.read_bytes()) == expected, f'checksum mismatch {folder}/{name}')
        entries[name] = expected
    if include_all:
        excluded = excluded or set()
        actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.relative_to(folder).as_posix() not in excluded}
        check(set(entries) == actual, f'checksum inventory mismatch in {folder}')
    return entries


def git(*args: str) -> str:
    return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--precommit', action='store_true', help='verify worktree state before the application commit')
    args = parser.parse_args()
    # Verify the top-level application evidence and its nested sealed source packet.
    window_sums = verify_manifest(EVIDENCE, excluded={'SHA256SUMS.txt'}, include_all=True)
    root_sums = verify_manifest(PACKET, excluded={
        'SHA256SUMS.txt', 'candidate-free-input/SHA256SUMS.txt',
        'primary-review/SHA256SUMS.txt', 'blind-review/SHA256SUMS.txt',
    }, include_all=True)
    candidate_sums = verify_manifest(PACKET / 'candidate-free-input', excluded={'SHA256SUMS.txt'}, include_all=True)
    primary_sums = verify_manifest(PACKET / 'primary-review', excluded={'SHA256SUMS.txt'}, include_all=True)
    blind_sums = verify_manifest(PACKET / 'blind-review', excluded={'SHA256SUMS.txt'}, include_all=True)
    check(len(root_sums) > 0 and len(candidate_sums) > 0 and len(primary_sums) > 0 and len(blind_sums) > 0,
          'sealed packet checksum set is empty')
    auth = read_json(PACKET / 'root-application-authorization.json')
    check(auth['applicationApproved'] is True and auth['selectedChangeCount'] == 84, 'sealed root authorization invalid')
    check(auth['head'] == EXPECTED_PARENT and auth['tree'] == EXPECTED_PARENT_TREE, 'root packet pin mismatch')
    selected_file = PACKET / 'selected-changes.jsonl'
    check(digest(selected_file.read_bytes()) == auth['selectedChangesSha256'], 'selected-change list hash mismatch')
    selected_rows = read_jsonl(selected_file)
    cross_rows = read_jsonl(PACKET / 'cross-audit-ledger.jsonl')
    current_rows = read_jsonl(INPUT / 'current-target-cells.jsonl')
    source_contexts = {r['position']: r for r in read_jsonl(INPUT / 'source-contexts.jsonl')}
    check(len(selected_rows) == 84 and len(cross_rows) == 240 and len(current_rows) == 240,
          'sealed packet cell or update count mismatch')
    selected_by = {(r['position'], r['locale']): r for r in selected_rows}
    cross_by = {(r['position'], r['locale']): r for r in cross_rows}
    current_by = {(r['position'], r['locale']): r for r in current_rows}
    check(len(selected_by) == 84 and len(cross_by) == 240 and len(current_by) == 240, 'duplicate sealed cell key')

    manifest = read_json(EVIDENCE / 'manifest.json')
    summary = read_json(APPLICATION / 'summary.json')
    check(manifest['applicationParentHead'] == EXPECTED_PARENT and manifest['applicationParentTree'] == EXPECTED_PARENT_TREE,
          'application evidence parent pin mismatch')
    check(manifest['rootApplicationApproved'] is True and manifest['selectedChanges'] == 84, 'application manifest authorization mismatch')
    check(manifest['selectedChangesSha256'] == auth['selectedChangesSha256'], 'manifest selected-change hash mismatch')
    check(summary['selectedChanges'] == 84 and summary['cellCount'] == 240 and summary['callerPathHoldsPreserved'] == 24,
          'application summary counts mismatch')

    catalog_path = pathlib.Path('romarr/ui-labels.json')
    if args.precommit:
        parent = git('rev-parse', 'HEAD')
        head = parent
        parent_tree = git('rev-parse', f'{parent}^{{tree}}')
        final_tree = 'uncommitted worktree content'
        status_lines = subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain=v1'], text=True).splitlines()
        allowed_paths = {'romarr/ui-labels.json', 'docs/pr-evidence/pr70-localization-2026-11-03/window-285-304/'}
        actual_paths = {line[3:] for line in status_lines}
        check(actual_paths <= allowed_paths and 'romarr/ui-labels.json' in actual_paths,
              f'unexpected precommit worktree paths: {sorted(actual_paths)}')
        after_bytes = (REPO / catalog_path).read_bytes()
    else:
        parent = git('rev-parse', 'HEAD^')
        head = git('rev-parse', 'HEAD')
        parent_tree = git('rev-parse', f'{parent}^{{tree}}')
        final_tree = git('rev-parse', f'{head}^{{tree}}')
        check(git('status', '--porcelain=v1') == '', 'worktree is not clean')
        after_bytes = subprocess.check_output(['git', '-C', str(REPO), 'show', f'{head}:{catalog_path.as_posix()}'])
    check(parent == EXPECTED_PARENT and parent_tree == EXPECTED_PARENT_TREE, 'application parent differs from pinned base')
    before_bytes = subprocess.check_output(['git', '-C', str(REPO), 'show', f'{parent}:{catalog_path.as_posix()}'])
    worktree_bytes = (REPO / catalog_path).read_bytes()
    check(after_bytes == worktree_bytes, 'committed/worktree catalog differs')
    check(digest(before_bytes) == manifest['appliedCatalogBaseSha256'], 'parent catalog checksum mismatch')
    check(digest(after_bytes) == manifest['appliedCatalogSha256'] == summary['appliedCatalogSha256'], 'applied catalog checksum mismatch')
    before = json.loads(before_bytes)
    after = json.loads(after_bytes)
    check(list(before) == list(after), 'top-level catalog key order changed')
    check(list(before['messages']) == list(after['messages']), 'catalog message ID order changed')
    check(len(after['messages']) == 1836, 'catalog message count changed')

    plan = read_jsonl(APPLICATION / 'plan-240-cells.jsonl')
    readback = read_jsonl(APPLICATION / 'readback-240-cells.jsonl')
    check(len(plan) == 240 and len(readback) == 240, 'plan or readback does not contain all 240 cells')
    plan_by = {(r['position'], r['locale']): r for r in plan}
    readback_by = {(r['position'], r['locale']): r for r in readback}
    check(len(plan_by) == 240 and len(readback_by) == 240, 'duplicate plan/readback cell')
    check(set(plan_by) == set(current_by) == set(cross_by), 'plan coverage differs from sealed packet')
    selected_pairs = {(r['sourceId'], r['locale']) for r in selected_rows}
    check(len(selected_pairs) == 84, 'authorized selected pair set is not unique')

    changed_values = changed_hashes = hold_count = matches = placeholder_checks = protected_checks = 0
    for key, p in plan_by.items():
        pos, locale = key
        cur = current_by[key]
        cross = cross_by[key]
        selected = selected_by.get(key)
        rb = readback_by[key]
        sid = p['sourceId']
        check(p['sourceId'] == cur['sourceId'] == cross['sourceId'], f'{key}: source ID mismatch')
        check(p['source'] == cur['source'] == cross['source'], f'{key}: source mismatch')
        check(p['sourceSha256'] == cur['sourceSha256'] == cross['sourceSha256'] == raw_hash(p['source']), f'{key}: source hash mismatch')
        check(p['previousTarget'] == cur['currentTarget'] == cross['currentTarget'], f'{key}: previous target mismatch')
        check(p['previousTargetRawUtf8Sha256'] == cur['currentTargetSha256'] == raw_hash(p['previousTarget']), f'{key}: previous raw hash mismatch')
        check(p['callerPathHold'] == (cross['rootDisposition'] == 'hold'), f'{key}: hold flag mismatch')
        check(p['selectedForApplication'] == (selected is not None) == cross['selectedForApplication'], f'{key}: selected flag mismatch')
        check(p['rootDisposition'] == cross['rootDisposition'] and p['rootRationale'] == cross['rootRationale'], f'{key}: root decision mismatch')
        check(p['expectedTarget'] == cross['rootTarget'], f'{key}: target differs from root cross-audit')
        check(p['expectedTargetRawUtf8Sha256'] == cross['rootTargetSha256'] == raw_hash(p['expectedTarget']), f'{key}: root target hash mismatch')
        if selected:
            check(selected['sourceId'] == sid and selected['sourceSha256'] == p['sourceSha256'], f'{key}: selected source mismatch')
            check(selected['previousTarget'] == p['previousTarget'] and selected['previousTargetSha256'] == p['previousTargetRawUtf8Sha256'], f'{key}: selected before state mismatch')
            check(selected['target'] == p['expectedTarget'] and selected['targetSha256'] == p['expectedTargetRawUtf8Sha256'], f'{key}: selected target/hash mismatch')
        else:
            check(p['expectedTarget'] == p['previousTarget'], f'{key}: non-selected target changed')
        check(p['changeExpected'] == (p['expectedTarget'] != p['previousTarget']), f'{key}: change flag mismatch')
        check(p['selectedForApplication'] == p['changeExpected'], f'{key}: selected/change flag mismatch')
        if p['callerPathHold']:
            hold_count += 1
            check(pos in (286, 304) and selected is None and not p['changeExpected'], f'{key}: hold was changed or moved')
            check(p['expectedTarget'] == cur['currentTarget'], f'{key}: held current value not preserved')
        elif pos in (286, 304):
            raise AssertionError(f'{key}: caller-path held rank lacks hold disposition')

        before_msg = before['messages'][sid]
        after_msg = after['messages'][sid]
        check(before_msg['source'] == p['source'] == after_msg['source'], f'{key}: catalog source mismatch')
        check(before_msg['translations'][locale] == p['previousTarget'], f'{key}: catalog parent translation mismatch')
        check(before_msg['translationHashes'][locale] == p['previousTargetCanonicalTranslationHash'] == canonical_hash(p['previousTarget']), f'{key}: parent canonical hash mismatch')
        actual_target = after_msg['translations'][locale]
        actual_hash = after_msg['translationHashes'][locale]
        check(actual_target == p['expectedTarget'] == rb['expectedTarget'] == rb['actualTarget'], f'{key}: readback target mismatch')
        check(raw_hash(actual_target) == p['expectedTargetRawUtf8Sha256'] == rb['actualTargetRawUtf8Sha256'], f'{key}: readback raw hash mismatch')
        check(actual_hash == p['expectedTargetCanonicalTranslationHash'] == rb['actualTargetCanonicalTranslationHash'] == canonical_hash(actual_target), f'{key}: canonical translation hash mismatch')
        check(rb['matches'] is True and rb['selectedForApplication'] == p['selectedForApplication'] and rb['callerPathHold'] == p['callerPathHold'], f'{key}: readback flags mismatch')
        matches += 1

        placeholders = collections.Counter(PLACEHOLDER_RE.findall(actual_target))
        source_placeholders = collections.Counter(cur['sourcePlaceholders'])
        check(placeholders == source_placeholders, f'{key}: placeholder multiset mismatch')
        check(p['sourcePlaceholders'] == cur['sourcePlaceholders'], f'{key}: plan placeholder source mismatch')
        placeholder_checks += 1
        tags = collections.Counter(TAG_RE.findall(actual_target))
        source_tags = collections.Counter(cur['sourceMarkupTags'])
        check(tags == source_tags and p['sourceMarkupTags'] == cur['sourceMarkupTags'], f'{key}: markup tag multiset mismatch')
        protected = cross['protectedLiterals']
        check(p['protectedLiterals'] == protected and all(lit.casefold() in actual_target.casefold() for lit in protected), f'{key}: protected literal mismatch')
        check(cross['protectedLiteralsPreserved'] is True and cross['placeholderMultisetMatches'] is True, f'{key}: cross-audit integrity flag false')
        protected_checks += 1
        context = source_contexts[pos]
        check(p['callerLocations'] == context['currentCallerLocations'], f'{key}: caller location mismatch')

        changed = actual_target != p['previousTarget']
        check(changed == p['changeExpected'], f'{key}: changed/non-changed state mismatch')
        if changed:
            changed_values += 1
            check(actual_hash != before_msg['translationHashes'][locale], f'{key}: changed target hash was not updated')
            changed_hashes += 1

    # Ensure no translations, hashes, or locale/review metadata outside the 84 exact cells changed.
    check(list(before.keys()) == list(after.keys()), 'top-level key order differs')
    for field in before:
        if field != 'messages':
            check(before[field] == after[field], f'top-level metadata changed: {field}')
    for sid, old_msg in before['messages'].items():
        new_msg = after['messages'][sid]
        check(list(old_msg) == list(new_msg), f'message field order changed: {sid}')
        for field in old_msg:
            if field not in ('translations', 'translationHashes'):
                check(old_msg[field] == new_msg[field], f'message metadata changed: {sid}/{field}')
        check(list(old_msg['translations']) == list(new_msg['translations']), f'locale order changed: {sid}')
        check(list(old_msg['translationHashes']) == list(new_msg['translationHashes']), f'hash locale order changed: {sid}')
        for locale, old_target in old_msg['translations'].items():
            should_change = (sid, locale) in selected_pairs
            new_target = new_msg['translations'][locale]
            check((new_target != old_target) == should_change, f'non-target translation changed: {sid}/{locale}')
            old_hash = old_msg.get('translationHashes', {}).get(locale)
            new_hash = new_msg.get('translationHashes', {}).get(locale)
            if should_change:
                check(new_hash == canonical_hash(new_target) and new_hash != old_hash, f'selected canonical hash mismatch: {sid}/{locale}')
            else:
                check(new_hash == old_hash, f'non-target translation hash changed: {sid}/{locale}')
    check(matches == 240 and changed_values == 84 and changed_hashes == 84 and hold_count == 24,
          f'final count mismatch: {matches}/{changed_values}/{changed_hashes}/{hold_count}')
    check(placeholder_checks == 240 and protected_checks == 240, 'not all cells received placeholder/literal checks')
    check({p for p, _ in plan_by if plan_by[(p, 'ar')]['callerPathHold']} == {286, 304}, 'held rank set mismatch')

    check(summary['readbackMatches'] == matches and summary['changedTranslationValues'] == changed_values,
          'application summary readback/change counts mismatch')
    check(summary['changedCanonicalTranslationHashes'] == changed_hashes and summary['nonTargetTranslationsAndHashesChanged'] == 0,
          'application summary target/hash counts mismatch')
    check(summary['placeholderFailures'] == 0 and summary['protectedLiteralFailures'] == 0 and summary['markupTagFailures'] == 0,
          'application summary integrity failure count is nonzero')
    check(summary['qualifiedNativeSpeakerApproval'] is False and summary['exactHeadBrowserReview'] is False and summary['releaseApproved'] is False,
          'application summary overstates review status')

    print(json.dumps({
        'result': 'PASS', 'parentHead': parent, 'parentTree': parent_tree,
        'finalHead': head, 'finalTree': final_tree,
        'cellsReadBack': matches, 'selectedTargetChanges': changed_values,
        'canonicalTranslationHashesUpdated': changed_hashes, 'callerPathHoldsPreserved': hold_count,
        'placeholderChecks': placeholder_checks, 'protectedLiteralChecks': protected_checks,
        'nonTargetTranslationsChanged': 0, 'nonTargetHashesChanged': 0,
        'catalogMessageCount': len(after['messages']), 'messageAndLocaleKeyOrderPreserved': True,
        'catalogSha256': digest(after_bytes), 'windowChecksumEntries': len(window_sums),
        'rootPacketFilesVerified': len(root_sums), 'candidateFilesVerified': len(candidate_sums),
        'primaryFilesVerified': len(primary_sums), 'blindFilesVerified': len(blind_sums),
    }, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        raise
