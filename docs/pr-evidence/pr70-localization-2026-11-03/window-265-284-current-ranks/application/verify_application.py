#!/usr/bin/env python3
"""Read-only exact-cell and catalog-structure verifier for W265-W284 application."""
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
CATALOG = 'romarr/ui-labels.json'
PLACEHOLDER_RE = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')
TAG_RE = re.compile(r'</?([A-Za-z][A-Za-z0-9:-]*)(?:\s[^>]*)?/?>')
EXPECTED_HEAD = 'c135c4729582817273c946891186ab4ea87467b5'
EXPECTED_TREE = '32c07150396335a5832b5664fc1e0225d7cebdc1'
EXPECTED_HOLDS = list(range(269, 283))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def raw_hash(text: str) -> str:
    return digest(text.encode('utf-8'))


def canonical_hash(text: str) -> str:
    value = json.dumps(text, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return digest(value.encode('utf-8'))


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path: pathlib.Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def git(repo: pathlib.Path, *args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(repo), *args])


def verify_sums(folder: pathlib.Path, sum_name='SHA256SUMS.txt', include_all=False):
    sums_path = folder / sum_name
    entries = {}
    for line in sums_path.read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        if name in entries:
            raise AssertionError(f'duplicate checksum entry {folder}/{name}')
        path = folder / name
        if not path.is_file():
            raise AssertionError(f'missing checksummed file {path}')
        actual = digest(path.read_bytes())
        if actual != expected:
            raise AssertionError(f'checksum mismatch {path}: {actual} != {expected}')
        entries[name] = expected
    if include_all:
        actual_names = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p != sums_path}
        if set(entries) != actual_names:
            raise AssertionError(f'root checksum inventory mismatch: missing={sorted(actual_names-set(entries))}, extra={sorted(set(entries)-actual_names)}')
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True, type=pathlib.Path)
    parser.add_argument('--base', default=None)
    args = parser.parse_args()
    repo = args.repo.resolve()
    evidence = EVIDENCE.resolve()
    root_manifest = read_json(evidence / 'manifest.json')
    app_summary = read_json(evidence / 'application/summary.json')
    base = args.base or root_manifest['applicationParentHead']
    if base != EXPECTED_HEAD or root_manifest['reviewHead'] != EXPECTED_HEAD or root_manifest['reviewTree'] != EXPECTED_TREE:
        raise AssertionError('application plan is not pinned to the expected review head/tree')
    if root_manifest['applicationParentHead'] != base:
        raise AssertionError('application parent differs from the aggregate evidence manifest')

    root_sums = verify_sums(evidence, sum_name='SHA256SUMS.txt', include_all=True)
    candidate = evidence / 'candidate-free-input'
    primary = evidence / 'primary-review'
    blind = evidence / 'blind-review'
    cross = evidence / 'third-party-cross-audit'
    candidate_sums = verify_sums(candidate)
    primary_sums = verify_sums(primary)
    blind_sums = verify_sums(blind)
    cross_sums = verify_sums(cross)

    candidate_manifest_sha = digest((candidate / 'manifest.json').read_bytes())
    candidate_sums_sha = digest((candidate / 'SHA256SUMS.txt').read_bytes())
    if root_manifest['candidateFreeInputManifestJsonSha256'] != candidate_manifest_sha:
        raise AssertionError('candidate-free manifest JSON SHA256 mismatch')
    if root_manifest['candidateFreeInputChecksumListSha256'] != candidate_sums_sha:
        raise AssertionError('candidate-free checksum-list SHA256 mismatch')
    if root_manifest['blindCandidateFreeManifestJsonSha256'] != candidate_manifest_sha or root_manifest['blindCandidateFreeChecksumListSha256'] != candidate_sums_sha:
        raise AssertionError('blind candidate manifest/checksum-list hashes mismatch')
    blind_seal = read_json(blind / 'blind-seal.json')
    blind_summary = read_json(blind / 'summary.json')
    blind_provenance = read_json(blind / 'provenance.json')
    if any(x.get('candidateFreeManifestJsonSha256') != candidate_manifest_sha for x in (blind_seal, blind_summary, blind_provenance)):
        raise AssertionError('blind candidate manifest JSON hash is not explicit and correct')
    if blind_seal.get('candidateFreeInputChecksumListSha256') != candidate_sums_sha or blind_summary.get('candidateFreeInputChecksumListSha256') != candidate_sums_sha or blind_provenance.get('inputChecksumListSha256') != candidate_sums_sha:
        raise AssertionError('blind candidate checksum-list hash is not explicit and correct')
    if root_manifest['primaryReviewChecksumListSha256'] != digest((primary / 'SHA256SUMS.txt').read_bytes()):
        raise AssertionError('primary packet checksum-list SHA mismatch')
    if root_manifest['blindReviewChecksumListSha256'] != digest((blind / 'SHA256SUMS.txt').read_bytes()):
        raise AssertionError('blind packet checksum-list SHA mismatch')
    if root_manifest['crossAuditPacketChecksumListSha256'] != digest((cross / 'SHA256SUMS.txt').read_bytes()):
        raise AssertionError('cross-audit packet checksum-list SHA mismatch')
    cross_summary = read_json(cross / 'summary.json')
    lineage = cross_summary['inputLineage']
    if lineage['candidateFreeManifestSha256'] != candidate_manifest_sha or lineage['candidateFreeChecksumListSha256'] != candidate_sums_sha:
        raise AssertionError('cross-audit candidate manifest/checksum-list lineage mismatch')
    if lineage['blindProvenanceHashesMatchCurrentInput'] is not True:
        raise AssertionError('cross-audit does not attest corrected blind provenance')

    plan = read_jsonl(evidence / 'application/plan-240-cells.jsonl')
    readback = read_jsonl(evidence / 'application/readback-240-cells.jsonl')
    cross_rows = read_jsonl(cross / 'cross-audit-ledger.jsonl')
    current_rows = read_jsonl(candidate / 'current-target-cells.jsonl')
    primary_rows = read_jsonl(primary / 'primary-decisions.jsonl')
    blind_rows = read_jsonl(blind / 'blind-decisions.jsonl')
    if not (len(plan) == len(readback) == len(cross_rows) == len(current_rows) == len(primary_rows) == len(blind_rows) == 240):
        raise AssertionError('one or more evidence ledgers do not contain 240 rows')

    plan_by_cell = {(r['position'], r['locale']): r for r in plan}
    readback_by_cell = {(r['position'], r['locale']): r for r in readback}
    cross_by_cell = {(r['position'], r['locale']): r for r in cross_rows}
    current_by_cell = {(r['position'], r['locale']): r for r in current_rows}
    primary_by_cell = {(r['position'], r['locale']): r for r in primary_rows}
    blind_by_cell = {(r['position'], r['locale']): r for r in blind_rows}
    for table in (plan_by_cell, readback_by_cell, cross_by_cell, current_by_cell, primary_by_cell, blind_by_cell):
        if len(table) != 240:
            raise AssertionError('duplicate position/locale record in an evidence ledger')
    if set(plan_by_cell) != set(cross_by_cell) or set(plan_by_cell) != set(current_by_cell):
        raise AssertionError('application plan, cross-audit, and input cell inventories differ')

    commit = git(repo, 'rev-parse', base).decode().strip()
    tree = git(repo, 'rev-parse', f'{commit}^{{tree}}').decode().strip()
    if commit != EXPECTED_HEAD or tree != EXPECTED_TREE:
        raise AssertionError(f'base commit/tree mismatch: {commit} / {tree}')
    before = json.loads(git(repo, 'show', f'{commit}:{CATALOG}'))
    after = read_json(repo / CATALOG)
    if root_manifest['appliedCatalogBaseSha256'] != digest(git(repo, 'show', f'{commit}:{CATALOG}')):
        raise AssertionError('base catalog SHA256 mismatch')
    if root_manifest['appliedCatalogSha256'] != digest((repo / CATALOG).read_bytes()):
        raise AssertionError('applied catalog SHA256 mismatch')

    if list(before) != list(after) or list(before['messages']) != list(after['messages']):
        raise AssertionError('top-level or message ID/key order changed')
    for field in before:
        if field != 'messages' and before[field] != after[field]:
            raise AssertionError(f'top-level non-message metadata changed: {field}')

    selected_pairs = {(r['sourceId'], r['locale']) for r in plan if r['changeExpected']}
    if len(selected_pairs) != 34:
        raise AssertionError(f'expected 34 selected target changes, found {len(selected_pairs)}')
    changed_value_count = 0
    changed_hash_count = 0
    matches = 0
    holds = 0
    for key, p in plan_by_cell.items():
        pos, locale = key
        rb = readback_by_cell[key]
        cr = cross_by_cell[key]
        inp = current_by_cell[key]
        sid = p['sourceId']
        bm = before['messages'][sid]
        am = after['messages'][sid]
        if p['source'] != inp['source'] or p['sourceId'] != inp['sourceId'] or bm['source'] != p['source']:
            raise AssertionError(f'source identity mismatch at {key}')
        if bm['translations'][locale] != p['beforeText'] or raw_hash(p['beforeText']) != p['beforeRawUtf8Sha256']:
            raise AssertionError(f'parent translation mismatch at {key}')
        if canonical_hash(p['beforeText']) != p['beforeCanonicalTranslationHash'] or bm.get('translationHashes', {}).get(locale) != p['beforeCanonicalTranslationHash']:
            raise AssertionError(f'parent canonical translation hash mismatch at {key}')
        if cr['crossAuditDisposition'] != p['crossAuditDisposition'] or cr['crossAuditTarget'] != p['crossAuditTarget'] or cr['changeFromCurrent'] != p['changeExpected']:
            raise AssertionError(f'cross-audit decision mismatch at {key}')
        if p['callerPathHold'] != (p['crossAuditDisposition'] == 'hold'):
            raise AssertionError(f'caller hold flag mismatch at {key}')
        expected = p['expectedTarget']
        actual = am['translations'][locale]
        expected_hash = p['expectedTargetCanonicalTranslationHash']
        actual_hash = am.get('translationHashes', {}).get(locale)
        if actual != expected or raw_hash(actual) != p['expectedTargetRawUtf8Sha256'] or canonical_hash(actual) != expected_hash or actual_hash != expected_hash:
            raise AssertionError(f'final target/hash mismatch at {key}')
        if rb['actualTarget'] != actual or rb['expectedTarget'] != expected or rb['actualRawUtf8Sha256'] != raw_hash(actual) or rb['actualCanonicalTranslationHash'] != actual_hash or not rb['matches']:
            raise AssertionError(f'readback row mismatch at {key}')
        if (actual != p['beforeText']) != p['changeExpected'] or rb['changedFromParent'] != p['changeExpected']:
            raise AssertionError(f'unexpected changed-cell state at {key}')
        if collections.Counter(PLACEHOLDER_RE.findall(inp['source'])) != collections.Counter(PLACEHOLDER_RE.findall(actual)):
            raise AssertionError(f'placeholder multiset mismatch at {key}')
        if collections.Counter(TAG_RE.findall(inp['source'])) != collections.Counter(TAG_RE.findall(actual)):
            raise AssertionError(f'markup-tag multiset mismatch at {key}')
        if bm['translationStatus'] != am['translationStatus'] or bm.get('translationReview', {}) != am.get('translationReview', {}):
            raise AssertionError(f'translation review/status metadata changed at {key}')
        if p['callerPathHold']:
            holds += 1
            if actual != p['beforeText'] or actual_hash != p['beforeCanonicalTranslationHash']:
                raise AssertionError(f'caller-path hold changed at {key}')
        if actual != p['beforeText']:
            changed_value_count += 1
        if actual_hash != bm.get('translationHashes', {}).get(locale):
            changed_hash_count += 1
        matches += int(rb['matches'])

    # Verify the catalog globally: only selected translation values and their hashes may differ.
    for sid, bm in before['messages'].items():
        am = after['messages'][sid]
        if list(bm) != list(am):
            raise AssertionError(f'message metadata key order changed at {sid}')
        for field in bm:
            if field not in ('translations', 'translationHashes') and bm[field] != am[field]:
                raise AssertionError(f'message metadata changed at {sid}/{field}')
        if list(bm['translations']) != list(am['translations']) or list(bm.get('translationHashes', {})) != list(am.get('translationHashes', {})):
            raise AssertionError(f'locale translation/hash key order changed at {sid}')
        for locale, before_text in bm['translations'].items():
            should_change = (sid, locale) in selected_pairs
            plan_row = next((r for r in plan if r['sourceId'] == sid and r['locale'] == locale), None)
            expected_text = plan_row['expectedTarget'] if should_change else before_text
            if am['translations'][locale] != expected_text or (am['translations'][locale] != before_text) != should_change:
                raise AssertionError(f'non-selected translation changed at {sid}/{locale}')
            before_hash = bm.get('translationHashes', {}).get(locale)
            after_hash = am.get('translationHashes', {}).get(locale)
            if should_change:
                if after_hash != canonical_hash(expected_text) or after_hash == before_hash:
                    raise AssertionError(f'selected translation hash not updated at {sid}/{locale}')
            elif after_hash != before_hash:
                raise AssertionError(f'non-selected translation hash changed at {sid}/{locale}')
        if sid not in {r['sourceId'] for r in plan} and am != bm:
            raise AssertionError(f'catalog message outside this window changed: {sid}')

    if matches != 240 or changed_value_count != 34 or changed_hash_count != 34 or holds != 168:
        raise AssertionError(f'final count mismatch: matches={matches}, text={changed_value_count}, hashes={changed_hash_count}, holds={holds}')
    if sorted({r['position'] for r in plan if r['callerPathHold']}) != EXPECTED_HOLDS:
        raise AssertionError('held rank set mismatch')
    if app_summary['readbackMatches'] != 240 or app_summary['selectedChanges'] != 34 or app_summary['callerPathHoldsPreserved'] != 168:
        raise AssertionError('application summary counts mismatch')
    if app_summary['candidateFreeManifestJsonSha256'] != candidate_manifest_sha or app_summary['candidateFreeChecksumListSha256'] != candidate_sums_sha:
        raise AssertionError('application summary candidate input hashes mismatch')
    if app_summary['qualifiedNativeSpeakerApproval'] is not False or app_summary['exactHeadBrowserReview'] is not False or app_summary['releaseApproved'] is not False:
        raise AssertionError('application review status is overstated')

    print(json.dumps({
        'result': 'PASS', 'base': commit, 'parentTree': tree, 'cells': matches,
        'selectedTextChanges': changed_value_count, 'updatedCanonicalTranslationHashes': changed_hash_count,
        'callerPathHoldsPreserved': holds, 'messageIdsAndKeyOrderPreserved': True,
        'localeAndReviewMetadataPreserved': True, 'nonSelectedTranslationsChanged': 0,
        'candidateFreeManifestJsonSha256': candidate_manifest_sha,
        'candidateFreeChecksumListSha256': candidate_sums_sha,
        'rootEvidenceFilesVerified': len(root_sums), 'candidateFilesVerified': len(candidate_sums),
        'primaryFilesVerified': len(primary_sums), 'blindFilesVerified': len(blind_sums),
        'crossAuditFilesVerified': len(cross_sums),
    }, indent=2))

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        raise
