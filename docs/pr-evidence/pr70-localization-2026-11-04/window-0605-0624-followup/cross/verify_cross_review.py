#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
HEAD = '872905926887840025ba4c3f17151b96f8d3e6e2'
TREE = 'd7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4'
BRANCH = 'task/localization-translation-review-20261030'
LOCALES = ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CALLERLESS_POSITIONS = {618, 620, 623}
LINEAGE = [
    'prior-selection-reattestation-summary.json', 'prior-selection-reattestation.jsonl',
    'prior-hold-reattestation-summary.json', 'prior-hold-reattestation.jsonl',
    'prior-applied-cell-reattestation-summary.json', 'prior-applied-cell-reattestation.jsonl',
    'prior-window-cell-hash-reattestation.jsonl', 'prior-w565-window-cell-hash-reattestation.jsonl',
    'prior-w585-window-cell-hash-reattestation.jsonl',
]


def sha(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def need(value, message):
    if not value:
        raise SystemExit('FAIL: ' + message)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def check_sums(root, sums_name='SHA256SUMS.txt'):
    sums_path = root / sums_name
    rows = {}
    for line in sums_path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, name = line.split('  ', 1)
        path = (root / name).resolve()
        need(path.is_relative_to(root.resolve()) and path.is_file(), 'unsafe or missing checksum path ' + name)
        need(sha(path.read_bytes()) == digest, 'checksum mismatch ' + name)
        need(name not in rows, 'duplicate checksum path ' + name)
        rows[name] = digest
    actual = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file() and path != sums_path}
    need(set(rows) == actual, 'checksum coverage for ' + str(root))
    return rows


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def verify_live_pr(repo, receipt, check_live):
    snapshot = receipt['liveSnapshot']
    source = snapshot['sourceWorktree']
    need(git(repo, 'rev-parse', 'HEAD') == HEAD, 'source worktree HEAD')
    need(git(repo, 'rev-parse', 'HEAD^{tree}') == TREE, 'source worktree tree')
    need(git(repo, 'status', '--porcelain=v1', '--untracked-files=all') == '', 'source worktree is dirty')
    need(git(repo, 'branch', '--show-current') == '', 'source worktree is not detached')
    remote = git(repo, 'ls-remote', 'origin', f'refs/heads/{BRANCH}', 'refs/pull/70/head', 'refs/pull/70/merge')
    refmap = {line.split('\t')[1]: line.split('\t')[0] for line in remote.splitlines() if line.strip()}
    need(refmap == snapshot['remoteRefs'], 'live remote refs differ from receipt')
    need(source['head'] == HEAD and source['tree'] == TREE and source['clean'] is True and source['detached'] is True, 'source worktree receipt')
    if check_live:
        api = json.loads(subprocess.check_output([
            'gh', 'pr', 'view', '70', '--repo', 'snapetech-org/ROMarrNG',
            '--json', 'number,state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,title,url'
        ], text=True))
        need(api == snapshot['prApi'], 'live PR API differs from receipt')
        need(api['number'] == 70 and api['state'] == 'OPEN' and api['isDraft'] is True, 'PR state/draft')
        need(api['headRefName'] == BRANCH and api['headRefOid'] == HEAD, 'PR API branch/head')


def main():
    ap = argparse.ArgumentParser(description='Verify ROMarrNG PR #70 W605-W624 cross-review packet.')
    ap.add_argument('--input', type=pathlib.Path, required=True, help='candidate-free input directory')
    ap.add_argument('--primary', type=pathlib.Path, required=True, help='primary review root')
    ap.add_argument('--blind', type=pathlib.Path, required=True, help='independent blind review root')
    ap.add_argument('--repo', type=pathlib.Path, required=True, help='exact pinned source worktree')
    ap.add_argument('--live-pr', action='store_true', help='also compare current GitHub PR API state')
    args = ap.parse_args()
    inp, primary, blind, repo = [p.resolve() for p in (args.input, args.primary, args.blind, args.repo)]

    packet_sums = check_sums(ROOT)
    packet = read_json(ROOT / 'packet-manifest.json')
    listed = {item['path']: item for item in packet['files']}
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*') if path.is_file() and path.name not in ('packet-manifest.json', 'SHA256SUMS.txt')}
    need(set(listed) == actual, 'packet manifest file coverage')
    for name, item in listed.items():
        path = ROOT / name
        need(path.stat().st_size == item['bytes'] and sha(path.read_bytes()) == item['sha256'], 'packet manifest digest ' + name)
    need(packet_sums.get('packet-manifest.json') == sha((ROOT / 'packet-manifest.json').read_bytes()), 'packet manifest checksum')
    need((packet['head'], packet['tree'], packet['window']) == (HEAD, TREE, 'W605-W624'), 'packet pin')

    receipt = read_json(ROOT / 'input-receipt.json')
    need(receipt['candidateFreeInput']['manifestSha256'] == sha((inp / 'manifest.json').read_bytes()), 'input manifest receipt')
    need(receipt['candidateFreeInput']['checksumFileSha256'] == sha((inp / 'SHA256SUMS.txt').read_bytes()), 'input checksum receipt')
    check_sums(inp)
    check_sums(primary)
    check_sums(primary / 'primary-output')
    check_sums(blind)
    need(receipt['primary']['outputManifestSha256'] == sha((primary / 'primary-output' / 'primary-manifest.json').read_bytes()), 'primary manifest receipt')
    need(receipt['blind']['manifestSha256'] == sha((blind / 'packet-manifest.json').read_bytes()), 'blind manifest receipt')
    if args.live_pr:
        verify_live_pr(repo, receipt, True)
    else:
        verify_live_pr(repo, receipt, False)

    # Re-run the three packet verifiers against the same exact source worktree.
    subprocess.run([sys.executable, str(inp.parent.parent / 'verify_bundle.py'), '--repo', str(repo)], check=True)
    subprocess.run([sys.executable, str(primary / 'verify_primary.py'), '--repo', str(repo)], check=True)
    subprocess.run([sys.executable, str(blind / 'verify_packet.py'), '--input', str(inp)], check=True)

    input_cells = read_jsonl(inp / 'current-target-cells.jsonl')
    contexts = {row['sourceId']: row for row in read_jsonl(inp / 'source-contexts.jsonl')}
    primary_rows = read_jsonl(primary / 'primary-output' / 'dispositions.jsonl')
    blind_rows = read_jsonl(blind / 'review.jsonl')
    cross_rows = read_jsonl(ROOT / 'cross-review.jsonl')
    proposals = read_jsonl(ROOT / 'proposal-adjudication.jsonl')
    input_by = {(row['position'], row['locale']): row for row in input_cells}
    primary_by = {(row['sourceId'], row['locale']): row for row in primary_rows}
    blind_by = {(row['position'], row['locale']): row for row in blind_rows}
    cross_by = {(row['position'], row['locale']): row for row in cross_rows}
    need(len(input_by) == len(cross_rows) == 240 and len(cross_by) == 240, '240-cell coverage')
    need(len(primary_rows) == len(blind_rows) == 240, 'upstream 240-cell coverage')
    need([row['locale'] for row in cross_rows[:12]] == LOCALES, 'locale order')

    counts = collections.Counter()
    callerless_rows = []
    for row in cross_rows:
        key = (row['position'], row['locale'])
        need(key in input_by and key in blind_by, 'unknown cross-review cell')
        cell = input_by[key]
        need(row['inputCellCanonicalSha256'] == sha(canon(cell)), 'input cell canonical hash ' + str(key))
        need(row['sourceSha256'] == cell['sourceSha256'] and row['currentTargetSha256'] == cell['currentTargetSha256'] and row['callerContextSha256'] == cell['callerContextSha256'], 'input cell hashes ' + str(key))
        need(row['blindDisposition'] == blind_by[key]['disposition'], 'blind disposition reconciliation ' + str(key))
        primary_row = primary_by[(cell['sourceId'], cell['locale'])]
        need(row['primaryDisposition'] == primary_row['disposition'], 'primary disposition reconciliation ' + str(key))
        counts[row['crossDisposition']] += 1
        is_callerless = row['position'] in CALLERLESS_POSITIONS
        if is_callerless:
            callerless_rows.append(row)
            need(row.get('callerless') is True and row['crossDisposition'] == 'hold_hash_only', 'callerless final hold ' + str(key))
            need(row['blindDisposition'] == 'hold_hash_only', 'callerless blind hold ' + str(key))
            need(not any(name in row for name in ('sourceId','source','currentTarget','sourceContext','callerRefs','proposedTarget','primaryProposedTarget','blindProposedTarget','primaryRationale','crossRationale')), 'callerless text/source leak ' + str(key))
            need(row.get('crossReasonCode') == 'caller_context_unavailable', 'callerless reason code ' + str(key))
            need(contexts[cell['sourceId']]['callerless'] is True, 'candidate-free callerless source ' + str(key))
        else:
            context = contexts[cell['sourceId']]
            need(row.get('callerless') is False and isinstance(row.get('source'), str) and isinstance(row.get('currentTarget'), str), 'callerful row content ' + str(key))
            need(row['sourceId'] == cell['sourceId'] and row['source'] == cell['source'] and row['currentTarget'] == cell['currentTarget'], 'callerful text identity ' + str(key))
            need(row['sourceContext'] == context and context['callerless'] is False, 'exact caller context ' + str(key))
            core = {name: value for name, value in context.items() if name != 'contextSha256'}
            need(sha(canon(core)) == context['contextSha256'] == row['callerContextSha256'], 'caller context digest ' + str(key))
            want_refs = [{'path': ref['path'], 'line': ref['line'], 'lineSha256': ref['lineSha256'], 'excerptSha256': ref['excerptSha256'], 'fileSha256': ref['fileSha256'], 'gitBlob': ref['gitBlob']} for ref in context['callers']]
            need(row['callerRefs'] == want_refs, 'caller references ' + str(key))
            need(row['primaryDisposition'] == primary_row['disposition'], 'callerful primary decision ' + str(key))
            if primary_row['disposition'] == 'CHANGE':
                need(row.get('primaryProposedTarget') == primary_row['proposedTarget'] and row.get('primaryProposedTargetSha256') == sha(primary_row['proposedTarget']), 'primary proposal identity ' + str(key))
            else:
                need('primaryProposedTarget' not in row, 'unexpected primary proposal ' + str(key))
            b = blind_by[key]
            if b['disposition'] == 'propose_clear_improvement':
                need(row.get('blindProposedTarget') == b['proposedTarget'] and row.get('blindProposedTargetSha256') == b['proposedTargetSha256'], 'blind proposal identity ' + str(key))
            else:
                need('blindProposedTarget' not in row, 'unexpected blind proposal ' + str(key))
            if key in ((611, 'id'), (611, 'vi')):
                need(row['crossDisposition'] == 'propose_clear_improvement', 'accepted proposal outcome ' + str(key))
                need(row.get('crossProposedTarget') == row.get('blindProposedTarget'), 'accepted target is not blind candidate ' + str(key))
            else:
                need(row['crossDisposition'] == 'retain_current', 'callerful retain outcome ' + str(key))
                need('crossProposedTarget' not in row, 'unexpected final proposal ' + str(key))

    need(counts == {'retain_current': 202, 'propose_clear_improvement': 2, 'hold_hash_only': 36}, 'cross disposition totals ' + repr(dict(counts)))
    need(len(callerless_rows) == 36, '36 callerless rows')
    need(sum(row['primaryDisposition'] == 'CHANGE' for row in callerless_rows) == 6, 'six callerless primary proposals were held')

    proposal_by = {(row['position'], row['locale']): row for row in proposals}
    candidate_cells = {
        (row['position'], row['locale']) for row in blind_rows if row['disposition'] == 'propose_clear_improvement'
    }
    for row in primary_rows:
        if row['disposition'] == 'CHANGE':
            cell = next(x for x in input_cells if x['sourceId'] == row['sourceId'] and x['locale'] == row['locale'])
            candidate_cells.add((cell['position'], cell['locale']))
    need(set(proposal_by) == candidate_cells and len(proposals) == 9, 'proposal cell coverage')
    proposal_outcomes = collections.Counter()
    for key, item in proposal_by.items():
        cell = input_by[key]
        proposal_outcomes[item['outcome']] += 1
        if key[0] in CALLERLESS_POSITIONS:
            need(item['outcome'] == 'held_hash_only_no_caller_context', 'callerless proposal not held ' + str(key))
            need(not any(name in item for name in ('sourceId','source','currentTarget','sourceContext','proposedTarget','primaryProposedTarget','blindProposedTarget','rationale')), 'callerless proposal text leak ' + str(key))
            need(item['sourceSha256'] == cell['sourceSha256'] and item['currentTargetSha256'] == cell['currentTargetSha256'] and item['callerContextSha256'] == cell['callerContextSha256'], 'callerless proposal hashes ' + str(key))
        else:
            need(item['sourceId'] == cell['sourceId'] and item['source'] == cell['source'] and item['currentTarget'] == cell['currentTarget'], 'proposal cell text ' + str(key))
            need(item['sourceContext'] == contexts[cell['sourceId']], 'proposal context ' + str(key))
            if key == (611, 'ar'):
                need(item['outcome'] == 'rejected_retain_current', 'Arabic proposal review')
            elif key in ((611, 'id'), (611, 'vi')):
                need(item['outcome'] == 'accepted_clear_improvement', 'accepted proposal review ' + str(key))
            else:
                raise SystemExit('FAIL: unexpected callerful proposal ' + str(key))
    need(proposal_outcomes == {'accepted_clear_improvement': 2, 'rejected_retain_current': 1, 'held_hash_only_no_caller_context': 6}, 'proposal outcomes ' + repr(dict(proposal_outcomes)))

    for name in LINEAGE:
        need((ROOT / 'lineage' / name).read_bytes() == (inp / name).read_bytes(), 'lineage byte identity ' + name)
    lineage_summary = read_json(ROOT / 'summary.json')['lineage']
    need(lineage_summary == {'selectedSources': 220, 'holds': 628, 'appliedCells': 71, 'w585CallerlessHolds': 24, 'windowReadbackCells': {'W545-W564': 240, 'W565-W584': 240, 'W585-W604': 240}, 'copiedByteIdentically': LINEAGE}, 'lineage summary')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':240,'callerful':204,'callerlessHashOnly':36,'dispositions':dict(counts),'proposalOutcomes':dict(proposal_outcomes),'lineageFiles':len(LINEAGE),'livePrChecked':bool(args.live_pr)}, sort_keys=True))

if __name__ == '__main__':
    main()
