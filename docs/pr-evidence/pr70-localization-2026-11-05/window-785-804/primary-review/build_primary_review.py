#!/usr/bin/env python3
"""Build the W785-W804 primary translation review from the sealed candidate-free input."""
from __future__ import annotations
import hashlib, json, shutil
from collections import Counter
from pathlib import Path

INPUT = Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w785-804-20261105/candidate-free')
OUT = Path(__file__).resolve().parent
PIN_HEAD = 'bbbf84d0d83138a23143f6aa6075415ebcb36d3e'
PIN_TREE = 'fbf9ada4b4fd43a288ce498b24990312f0c32f22'

# Cell-specific reviewed alternatives. All unlisted caller-backed targets retain
# the exact current value after semantic/context review. Callerless rows remain
# text-free holds.
ALTERNATIVES = {
    ('ui.or-as-a-frontend-s-own-format.3a0f4bbdc6', 'vi'): (
        'correction',
        'Hoặc theo định dạng riêng của frontend:',
        'The caller is the export panel, where frontend means a frontend-specific format. The current expands this to a game-library manager; use a concise term closer to the source.'),
    ('ui.pin-from-your-moonlight-client.1a127b3ae9', 'es'): (
        'refinement',
        'PIN de tu cliente Moonlight',
        'The nearby Spanish UI uses informal second-person forms (for example, Organiza and Pégalo); replace the inconsistent formal su with tu.'),
    ('ui.pin-from-your-moonlight-client.1a127b3ae9', 'ko'): (
        'refinement',
        'Moonlight 클라이언트에서 받은 PIN',
        'The current Korean fragment is awkward and uses 당신의, which is uncommon in concise Korean UI copy. This says the PIN is received from the Moonlight client.'),
    ('ui.page-could-not-be-loaded.b4aa008f1c', 'fr'): (
        'refinement',
        'Impossible de charger la page',
        'The source is an error heading shown after the page-loading request fails. The current imperfect construction is less idiomatic as a UI error title; this is concise, standard French error copy.'),
    ('ui.page-could-not-be-loaded.b4aa008f1c', 'pt-BR'): (
        'refinement',
        'Não foi possível carregar a página',
        'The caller renders an error heading after load failure. The current lacks the article and reads less naturally; this is idiomatic Brazilian Portuguese error copy.'),
    ('ui.page-could-not-be-loaded.b4aa008f1c', 'vi'): (
        'correction',
        'Không thể tải trang',
        'The caller renders an error heading after load failure. The current word order is awkward; this is the natural Vietnamese heading.'),
    ('ui.page-could-not-be-loaded.b4aa008f1c', 'zh-Hans'): (
        'refinement',
        '无法加载页面',
        'The caller renders an error heading after load failure. The current 不能加载页面 is understandable but less idiomatic for this UI state.'),
    ('ui.page-could-not-be-loaded.b4aa008f1c', 'zh-Hant'): (
        'refinement',
        '無法載入頁面',
        'The caller renders an error heading after load failure. Use natural Traditional Chinese wording and the common Taiwan/Hong Kong form 載入.'),
    ('ui.page-page-of-pages.240ab6d8dc', 'ko'): (
        'refinement',
        '총 {pages}페이지 중 {page}페이지',
        'Preserves both format placeholders and keeps the page-of-total meaning. 총 is more natural than 전체 in this compact pagination label.'),
    ('ui.paired-clients.388740cbd4', 'es'): (
        'refinement',
        'Clientes emparejados',
        'The caller counts Moonlight clients paired to the host. Emparejados is the standard UI term and aligns with the adjacent Emparejamiento heading better than pareados.'),
    ('ui.pairing.76dfd9f9a3', 'hi'): (
        'correction',
        'युग्मन',
        'This is a section heading for the Moonlight host pairing flow. जोड़ी means a pair/pair of items rather than the pairing process.'),
    ('ui.pairing.76dfd9f9a3', 'id'): (
        'refinement',
        'Penyandingan',
        'This is a section heading for the Moonlight host pairing flow. The current passive Dipasangkan means paired; Penyandingan names the pairing process.'),
    ('ui.paste-it-here.f21b1e24fc', 'de'): (
        'refinement',
        'Fügen Sie es hier ein.',
        'The German interface elsewhere in this window uses formal Sie imperatives (for example, Fügen Sie den Wert zuerst ein); align this field label with that register.'),
    ('ui.paste-it-here.f21b1e24fc', 'fr'): (
        'refinement',
        'Collez-le ici.',
        'The French UI elsewhere in this window uses formal vous imperatives (Collez d’abord la valeur); align the field instruction with that register.'),
    ('ui.paste-it-here.f21b1e24fc', 'pt-BR'): (
        'refinement',
        'Cole aqui.',
        'The next instruction uses the standard você imperative Cole. Align this field instruction with that register rather than the informal Cola.'),
    ('ui.paste-it-here.f21b1e24fc', 'ko'): (
        'refinement',
        '여기에 붙여 넣으세요.',
        'The current nominal form reads like a button label, while the caller uses this as an instruction above the token textarea. Use the polite imperative form, matching the next Korean instruction.'),
}

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def load_jsonl(path: Path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]

def main():
    out = OUT
    rows = load_jsonl(INPUT/'input/candidate-free-cells.jsonl')
    contexts = {d['sourceId']: d for d in load_jsonl(INPUT/'input/source-contexts.jsonl')}
    sources = {d['sourceId']: d for d in load_jsonl(INPUT/'input/selected-sources.jsonl')}
    manifest = json.loads((INPUT/'input/manifest.json').read_text(encoding='utf-8'))
    if (manifest['head'], manifest['tree']) != (PIN_HEAD, PIN_TREE):
        raise SystemExit('candidate-free manifest pin mismatch')
    if len(rows) != 240 or manifest['callerlessHashOnlyCells'] != 48 or manifest['priorActiveHoldsReattested'] != 1012:
        raise SystemExit('candidate-free coverage/hold count mismatch')
    hold_path = out/'prior-active-holds-hash-only.jsonl'
    shutil.copyfile(INPUT/'input/prior-active-holds-hash-only.jsonl', hold_path)
    if hold_path.read_bytes() != (INPUT/'input/prior-active-holds-hash-only.jsonl').read_bytes():
        raise SystemExit('prior active holds copy changed')

    ledger = []
    counts = Counter()
    for row in rows:
        sid, locale = row['sourceId'], row['locale']
        ctx = contexts[sid]
        if row['callerless']:
            entry = {
                'window': 'W785-W804', 'position': row['position'], 'sourceId': sid,
                'locale': locale, 'callerless': True, 'disposition': 'hold_hash_only',
                'reason': 'No direct production caller is pinned for this source; source and target text stay omitted.',
                'sourceSha256': row['sourceSha256'], 'currentTargetSha256': row['currentTargetSha256'],
                'callerContextSha256': row['callerContextSha256'], 'candidateFree': True,
                'reviewMethod': 'machine review', 'nativeSpeakerApproval': False,
            }
            counts['hold_hash_only'] += 1
        else:
            target = row['currentTarget']
            disposition = 'accept_current'
            rationale = 'The current translation preserves the source meaning in its pinned caller context and reads as suitable UI copy for this locale.'
            decision = ALTERNATIVES.get((sid, locale))
            if decision:
                disposition, target, rationale = decision
            entry = {
                'window': 'W785-W804', 'position': row['position'], 'sourceId': sid,
                'locale': locale, 'callerless': False, 'source': row['source'],
                'sourceSha256': row['sourceSha256'], 'currentTarget': row['currentTarget'],
                'currentTargetSha256': row['currentTargetSha256'], 'proposedTarget': target,
                'proposedTargetSha256': sha(target.encode('utf-8')),
                'callerContextSha256': row['callerContextSha256'],
                'callerReferenceCount': ctx['exactMatchCount'],
                'callerReferences': [
                    {'path': c['path'], 'line': c['line'], 'matchKind': c['matchKind'],
                     'lineSha256': c['lineSha256'], 'fileSha256': c['fileSha256'], 'gitBlob': c['gitBlob']}
                    for c in ctx['callers']
                ],
                'sourcePlaceholderTokens': row['sourcePlaceholderTokens'],
                'proposedPlaceholderTokens': __import__('re').findall(r'\{[^{}]+\}', target),
                'sourceMarkupTags': row['sourceMarkupTags'], 'sourceProtectedLiterals': row['sourceProtectedLiterals'],
                'disposition': disposition, 'rationale': rationale,
                'confidence': 'moderate', 'reviewMethod': 'machine review',
                'nativeSpeakerApproval': False, 'candidateFree': True,
            }
            counts[disposition] += 1
        ledger.append(entry)
    if len(ALTERNATIVES) != sum(1 for e in ledger if e.get('disposition') in ('correction','refinement')):
        raise SystemExit('alternative decision coverage mismatch')
    with (out/'primary-review-ledger.jsonl').open('w',encoding='utf-8',newline='\n') as f:
        for entry in ledger:
            f.write(json.dumps(entry,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')

    input_sums = (INPUT/'SHA256SUMS.txt').read_bytes()
    summary = {
        'artifact':'ROMarrNG PR #70 W785-W804 primary translation review',
        'repository':'snapetech-org/ROMarrNG', 'pullRequest':70, 'window':'W785-W804',
        'head':PIN_HEAD, 'tree':PIN_TREE, 'candidateFreePath':str(INPUT),
        'candidateFreeSha256SumsListSha256':sha(input_sums),
        'cells':len(rows), 'callerBackedCells':192, 'callerlessHashOnlyCells':48,
        'priorActiveHashOnlyHoldsCopied':manifest['priorActiveHoldsReattested'],
        'resultingActiveHashOnlyHolds':manifest['resultingActiveHashOnlyHolds'],
        'dispositions':dict(sorted(counts.items())),
        'correctionOrRefinementCells':counts['correction']+counts['refinement'],
        'alternativeTargets':len(ALTERNATIVES), 'localeCount':manifest['localeCount'],
        'nextBoundary':manifest['nextBoundary'],
        'reviewType':'primary machine translation review from candidate-free caller/source evidence',
        'nativeSpeakerApproval':False,
        'productWorktreeEdited':False, 'catalogValuesApplied':False,
        'testsBuildsScansCiRun':False,
    }
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    readme = f'''# ROMarrNG PR #70 W785–W804 primary translation review\n\nPinned to HEAD `{PIN_HEAD}` / tree `{PIN_TREE}`. The candidate-free input is `{INPUT}`; its outer checksum list SHA256 is `{summary['candidateFreeSha256SumsListSha256']}`.\n\nThe ledger covers 240 source-locale cells: 192 caller-backed cells and 48 callerless rows kept text-free as hash-only holds. The existing 1,012 active prior holds are copied unchanged in `prior-active-holds-hash-only.jsonl`, for 1,060 active hash-only holds total.\n\nDispositions: {counts['accept_current']} accept current, {counts['refinement']} refinements, {counts['correction']} corrections, {counts['hold_hash_only']} hash-only holds. The 16 proposed changes are machine review recommendations; no native-speaker approval is included. All source/current hashes and caller context hashes are pinned per row.\n\nNo repository or catalog files were edited, no values were applied, and no tests/builds/scans/CI were run. Verify with `python3 -B verify_primary_review.py --repo /home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685 --candidate-free {INPUT}`.\n'''
    (out/'README.md').write_text(readme,encoding='utf-8')

if __name__ == '__main__': main()
