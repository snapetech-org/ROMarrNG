#!/usr/bin/env python3
"""Portable verifier for the sealed ROMarrNG W685-W704 blind-review artifact."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HEAD = '43d2858744ef20cd58462643fed534ac61d2ffad'
CELL_FILE = 'candidate-free-cells.jsonl'
CONTEXT_FILE = 'source-contexts.jsonl'

def digest_bytes(data): return hashlib.sha256(data).hexdigest()
def digest_text(value): return digest_bytes(value.encode('utf-8'))
def canonical(obj): return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
def digest_obj(obj): return digest_bytes(canonical(obj))
def read_jsonl(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def caller_refs(ctx):
    return [{k: caller.get(k) for k in ('path', 'line', 'gitBlob', 'fileSha256', 'lineSha256', 'excerptSha256')} for caller in ctx['callers']]
def binding(position, locale, source_sha, target_sha, caller_context_sha, caller_hashes_sha):
    return digest_obj({'position': position, 'locale': locale, 'sourceSha256': source_sha, 'currentTargetSha256': target_sha, 'callerContextSha256': caller_context_sha, 'callerHashesSha256': caller_hashes_sha})

def verify(package, input_dir):
    sums_path = package / 'SHA256SUMS.txt'
    seal_path = package / 'seal.sha256'
    expected_seal = seal_path.read_text(encoding='ascii').strip().split()[0]
    if expected_seal != digest_bytes(sums_path.read_bytes()): raise ValueError('seal.sha256 does not match SHA256SUMS.txt')
    for line in sums_path.read_text(encoding='ascii').splitlines():
        if not line.strip(): continue
        expected, name = line.split(None, 1)
        name = name.strip().lstrip('*')
        if Path(name).name != name: raise ValueError('non-portable artifact path in SHA256SUMS.txt')
        if digest_bytes((package / name).read_bytes()) != expected: raise ValueError('artifact checksum mismatch: ' + name)
    summary = json.loads((package / 'summary.json').read_text(encoding='utf-8'))
    if summary['exactPrHead'] != HEAD: raise ValueError('unexpected PR head in summary')
    cells_path, contexts_path = input_dir / CELL_FILE, input_dir / CONTEXT_FILE
    input_hashes = {CELL_FILE: digest_bytes(cells_path.read_bytes()), CONTEXT_FILE: digest_bytes(contexts_path.read_bytes())}
    if input_hashes != summary['inputSha256']: raise ValueError('candidate-free input checksum mismatch')
    cells, contexts = read_jsonl(cells_path), read_jsonl(contexts_path)
    # Callerless context rows are excluded from lookup and their text fields are never read.
    context_by_id = {r['sourceId']: r for r in contexts if not r.get('callerless', False)}
    reviews = read_jsonl(package / 'review.jsonl')
    if len(cells) != len(reviews) or len(cells) != summary['records']: raise ValueError('record count mismatch')
    counts, callerless_count = Counter(), 0
    for cell, record in zip(cells, reviews):
        for key in ('position', 'locale', 'sourceSha256', 'currentTargetSha256', 'callerContextSha256'):
            if record.get(key) != cell.get(key): raise ValueError(f'cell binding mismatch at position {cell.get("position")} locale {cell.get("locale")}: {key}')
        if bool(record.get('callerless')) != bool(cell.get('callerless')): raise ValueError('callerless marker mismatch')
        decision = record.get('decision')
        if decision not in ('accept', 'correction', 'refinement', 'hold'): raise ValueError('invalid decision')
        counts[decision] += 1
        if decision in ('correction', 'refinement') and not record.get('replacementText'): raise ValueError('proposed change lacks exact replacement text')
        if decision in ('accept', 'hold') and record.get('replacementText') is not None: raise ValueError('accept/hold has unintended replacement')
        if cell.get('callerless'):
            callerless_count += 1
            # Never access callerless source/currentTarget/sourceId text.
            if decision != 'hold' or record.get('callerHashes') != []: raise ValueError('callerless cell is not a hash-only hold')
            if any(k in record for k in ('sourceId', 'sourceText', 'currentTargetText', 'integrityChecks', 'replacementIntegrityChecks')): raise ValueError('callerless record includes text')
            if record.get('callerHashesSha256') != digest_obj([]): raise ValueError('callerless caller-hash digest mismatch')
            if record.get('bindingSha256') != binding(record['position'], record['locale'], record['sourceSha256'], record['currentTargetSha256'], record.get('callerContextSha256'), record['callerHashesSha256']): raise ValueError('callerless binding digest mismatch')
            continue
        source, target = cell['source'], cell['currentTarget']
        if digest_text(source) != cell['sourceSha256'] or digest_text(target) != cell['currentTargetSha256']: raise ValueError('candidate-free source/target hash mismatch')
        if record.get('sourceId') != cell['sourceId'] or record.get('sourceText') != source or record.get('currentTargetText') != target: raise ValueError('visible text mismatch')
        ctx = context_by_id.get(cell['sourceId'])
        if ctx is None or ctx.get('head') != HEAD: raise ValueError('missing or wrong-head caller context')
        if ctx.get('sourceSha256') != cell['sourceSha256'] or ctx.get('contextSha256') != cell['callerContextSha256']: raise ValueError('caller context digest mismatch')
        refs = caller_refs(ctx)
        refs_sha = digest_obj(refs)
        if record.get('callerHashes') != refs or record.get('callerHashesSha256') != refs_sha: raise ValueError('caller source hashes mismatch')
        if record.get('bindingSha256') != binding(record['position'], record['locale'], record['sourceSha256'], record['currentTargetSha256'], record['callerContextSha256'], refs_sha): raise ValueError('visible binding digest mismatch')
    if callerless_count != summary['callerlessHashOnlyHolds']: raise ValueError('callerless hold count mismatch')
    if any(counts.get(k, 0) != summary['decisions'].get(k, 0) for k in ('accept', 'correction', 'refinement', 'hold')): raise ValueError('decision counts mismatch')
    print(json.dumps({'verified': True, 'records': len(reviews), 'visible': len(reviews)-callerless_count, 'callerlessHashOnlyHolds': callerless_count, 'decisions': dict(counts), 'exactPrHead': HEAD}, ensure_ascii=False, sort_keys=True))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path, help='candidate-free/input directory')
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent, help='artifact directory (default: this script directory)')
    args = parser.parse_args()
    try: verify(args.package.resolve(), args.inputs.resolve())
    except Exception as exc:
        print('VERIFY FAILED: ' + str(exc), file=sys.stderr)
        return 1
    return 0
if __name__ == '__main__': raise SystemExit(main())
