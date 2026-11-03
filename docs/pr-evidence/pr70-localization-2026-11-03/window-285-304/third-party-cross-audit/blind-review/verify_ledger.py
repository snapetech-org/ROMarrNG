#!/usr/bin/env python3
"""Verify this independent review ledger against its candidate-free input packet."""
from __future__ import annotations
import hashlib, json, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w285-304-candidate-free-20261103/input')
EXPECTED_PACKET_SHA256 = '1047511955ef60dc180a49bdaef7a86452c70e9196fd681174732e98d408f338'
EXPECTED_HEAD = '363601fd2597f0fb97adff97554e651c2bea2d99'
EXPECTED_TREE = '1f8ada1746f53796e2b4a8f43f9a0075150aa5d7'
PROTECTED = {
  285: ['ES-DE'],
  287: ['ROM', 'Netplay'],
  288: ['Netplay', 'No-Intro', 'Redump'],
  289: ['Netplay', 'DAT'],
  293: ['IGDB'],
  295: ['API'],
}


def sha_bytes(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()

def sha_text(s: str) -> str:
  return sha_bytes(s.encode('utf-8'))

def read_json(path: Path):
  return json.loads(path.read_text(encoding='utf-8'))

def read_jsonl(path: Path):
  return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def check(condition, message):
  if not condition:
    raise AssertionError(message)

# Verify the source packet itself before using it.
packet_sums_path = INPUT / 'SHA256SUMS.txt'
packet_fingerprint = sha_bytes(packet_sums_path.read_bytes())
check(packet_fingerprint == EXPECTED_PACKET_SHA256, 'input SHA256SUMS.txt fingerprint mismatch')
for line in packet_sums_path.read_text(encoding='utf-8').splitlines():
  expected, name = line.split(None, 1)
  name = name.strip()
  check(sha_bytes((INPUT / name).read_bytes()) == expected, f'input checksum mismatch: {name}')
manifest = read_json(INPUT / 'manifest.json')
check(manifest['candidateFreeInputOnly'] is True, 'input manifest is not candidate-free')
check(manifest['proposedTargetsIncluded'] is False and manifest['reviewDecisionsIncluded'] is False,
      'input packet unexpectedly contains proposals or review decisions')
check(manifest['head'] == EXPECTED_HEAD and manifest['tree'] == EXPECTED_TREE,
      'packet head/tree mismatch')

# Verify output file checksums (the checksum file does not list itself).
output_sums = HERE / 'SHA256SUMS.txt'
check(output_sums.is_file(), 'output SHA256SUMS.txt missing')
for line in output_sums.read_text(encoding='utf-8').splitlines():
  expected, name = line.split(None, 1)
  name = name.strip()
  check(sha_bytes((HERE / name).read_bytes()) == expected, f'output checksum mismatch: {name}')

current_rows = read_jsonl(INPUT / 'current-target-cells.jsonl')
source_rows = {x['position']: x for x in read_jsonl(INPUT / 'source-contexts.jsonl')}
hold_rows = {(x['position'], x['locale']): x for x in read_jsonl(INPUT / 'caller-resolution-holds.jsonl')}
current = {(x['position'], x['locale']): x for x in current_rows}
ledger_rows = read_jsonl(HERE / 'ledger.jsonl')
check(len(current_rows) == 240 and len(ledger_rows) == 240, 'expected exactly 240 packet and ledger cells')
keyset = [(x['position'], x['locale']) for x in ledger_rows]
check(len(set(keyset)) == 240, 'duplicate source×locale cell in ledger')
check(set(keyset) == set(current), 'ledger source×locale coverage differs from packet')

counts = Counter()
for row in ledger_rows:
  key = (row['position'], row['locale'])
  cur = current[key]
  src = source_rows[row['position']]
  check(row['sourceId'] == cur['sourceId'] == src['sourceId'], f'{key}: source ID mismatch')
  check(row['source'] == cur['source'] == src['source'], f'{key}: source text mismatch')
  check(row['sourceSha256'] == cur['sourceSha256'] == src['sourceSha256'], f'{key}: source hash mismatch')
  check(row['currentTarget'] == cur['currentTarget'], f'{key}: current target mismatch')
  check(row['currentTargetSha256'] == cur['currentTargetSha256'] == sha_text(cur['currentTarget']),
        f'{key}: current target hash mismatch')
  check(row['callerLocations'] == src['currentCallerLocations'], f'{key}: caller locations mismatch')
  expected_refs = [{
    'path': r['path'], 'startLine': r['startLine'], 'endLine': r['endLine'],
    'contextSha256': r['contextSha256'], 'fileSha256': r['fileSha256'],
    'gitBlob': r['gitBlob'], 'matchBasis': r['matchBasis'],
  } for r in src['references']]
  check(row['callerContextReferences'] == expected_refs, f'{key}: caller/context references mismatch')
  check(row['sourceContextRef']['sourceSha256'] == src['sourceSha256'], f'{key}: source context hash mismatch')
  check(row['currentTargetCatalogRef']['path'] == cur['catalogPath'], f'{key}: catalog path mismatch')

  if key in hold_rows:
    hold = hold_rows[key]
    counts['hold'] += 1
    check(row['disposition'] == 'hold', f'{key}: required caller-path hold missing')
    check(row['proposedTarget'] is None and row['proposedTargetSha256'] is None,
          f'{key}: hold must not carry a translation proposal')
    check(row['preservedTarget'] == cur['currentTarget'], f'{key}: hold value not preserved')
    check(row['preservedTargetSha256'] == cur['currentTargetSha256'] == sha_text(cur['currentTarget']),
          f'{key}: hold hash mismatch')
    check(row['targetUnchangedFromCurrent'] is True, f'{key}: hold not marked unchanged')
    check(row['holdReason'] == hold['holdReason'], f'{key}: hold reason mismatch')
    check(row['confidence'] in {'high', 'moderate', 'low', 'unknown'}, f'{key}: invalid confidence')
    held_names = Counter(re.findall(r'\{([^{}]+)\}', row['preservedTarget']))
    source_names = Counter(cur['sourcePlaceholders'])
    check(held_names == source_names, f'{key}: held target placeholder multiset mismatch')
    check(row['sourcePlaceholders'] == cur['sourcePlaceholders'], f'{key}: hold source placeholder record mismatch')
    check(row['targetPlaceholders'] == cur['targetPlaceholders'], f'{key}: hold target placeholder record mismatch')
    check(row['placeholderMultisetMatchesSource'] is True, f'{key}: hold placeholder verification flag false')
    held_tags = re.findall(r'</?([A-Za-z][A-Za-z0-9]*)\b[^>]*>', row['preservedTarget'])
    check(Counter(held_tags) == Counter(cur['sourceMarkupTags']), f'{key}: held target markup tag multiset mismatch')
    check(row['sourceMarkupTags'] == cur['sourceMarkupTags'] and row['targetMarkupTags'] == cur['targetMarkupTags'],
          f'{key}: hold markup tag record mismatch')
    check(row['preservedTarget'] == hold['currentTarget'], f'{key}: preserved value differs from hold packet')
  else:
    counts[row['disposition']] += 1
    target = row['proposedTarget']
    check(row['disposition'] in {'retain', 'revise'}, f'{key}: invalid disposition')
    check(isinstance(target, str), f'{key}: localizable cell lacks a proposal')
    check(row['proposedTargetSha256'] == sha_text(target), f'{key}: proposal hash mismatch')
    check(row['preservedTarget'] is None and row['preservedTargetSha256'] is None,
          f'{key}: non-hold cell has hold preservation fields')
    check(row['targetUnchangedFromCurrent'] == (target == cur['currentTarget']),
          f'{key}: unchanged flag mismatch')
    check((row['disposition'] == 'retain') == (target == cur['currentTarget']),
          f'{key}: retain/revise disposition mismatch')
    target_names = Counter(re.findall(r'\{([^{}]+)\}', target))
    source_names = Counter(cur['sourcePlaceholders'])
    check(target_names == source_names, f'{key}: placeholder multiset mismatch: {target_names} != {source_names}')
    check(row['placeholderMultisetMatchesSource'] is True, f'{key}: placeholder verification flag false')
    check(row['targetPlaceholders'] == re.findall(r'\{[^{}]+\}', target), f'{key}: target placeholder record mismatch')
    expected_protected = PROTECTED.get(row['position'], [])
    check(row['protectedLiterals'] == expected_protected, f'{key}: protected literal set mismatch')
    check(all(lit.casefold() in target.casefold() for lit in expected_protected),
          f'{key}: protected literal missing')
    check(row['protectedLiteralsPreserved'] is True, f'{key}: protected literal flag false')
    check(row['sourceMarkupTags'] == cur['sourceMarkupTags'], f'{key}: source markup tags mismatch')
    tags = re.findall(r'</?([A-Za-z][A-Za-z0-9]*)\b[^>]*>', target)
    check(Counter(tags) == Counter(cur['sourceMarkupTags']), f'{key}: markup tag multiset mismatch')
    check(row['targetMarkupTags'] == tags, f'{key}: target markup record mismatch')
    check(row['confidence'] in {'high', 'moderate', 'low', 'unknown'}, f'{key}: invalid confidence')
    check(bool(row['rationale']), f'{key}: rationale missing')

check(counts == Counter({'hold': 24, 'retain': 142, 'revise': 74}), f'unexpected disposition counts: {counts}')
check(sum(counts.values()) == 240, 'disposition count does not sum to 240')
check({p: sum(1 for x in ledger_rows if x['position'] == p) for p in range(285, 305)} == {p:12 for p in range(285,305)},
      'not every rank has exactly 12 locales')
check(sum(1 for x in ledger_rows if x['position'] in (286,304) and x['disposition']=='hold') == 24,
      'caller-path hold ranks do not contain exactly 24 holds')

att = read_json(HERE / 'attestation.json')
check(att['packetHead'] == EXPECTED_HEAD and att['packetTree'] == EXPECTED_TREE, 'output attestation pin mismatch')
check(att['observedRemoteRefs']['refs/pull/70/head'] == EXPECTED_HEAD, 'live PR head mismatch')
check(att['observedRemoteRefs']['refs/heads/task/localization-translation-review-20261030'] == EXPECTED_HEAD,
      'live branch head mismatch')
check(att['observedCommitTree'] == EXPECTED_TREE, 'live tree mismatch')
check(att['checks']['headMatchesPacket'] and att['checks']['treeMatchesPacket'], 'live attestation mismatch')
check(att['checks']['prBodyInspected'] is False, 'PR body inspection must remain false')
check(att['inputPacketSha256'] == EXPECTED_PACKET_SHA256, 'output packet fingerprint mismatch')

print(json.dumps({
  'result': 'PASS', 'packetSha256': packet_fingerprint, 'cells': len(ledger_rows),
  'counts': dict(counts), 'placeholderChecks': 240, 'protectedLiteralChecks': 216,
  'unchangedValuesVerified': counts['retain'] + counts['hold'],
  'liveHead': EXPECTED_HEAD, 'liveTree': EXPECTED_TREE,
}, ensure_ascii=False, indent=2))
