#!/usr/bin/env python3
import collections, hashlib, json
from pathlib import Path

TASK = Path(__file__).resolve().parent
CF = TASK.parent/'candidate-free'/'input'
CROSS = TASK.parent/'cross-review'
PR = TASK.parent/'primary-review'
BL = TASK.parent/'blind-review'
HEAD = 'bbbf84d0d83138a23143f6aa6075415ebcb36d3e'
TREE = 'fbf9ada4b4fd43a288ce498b24990312f0c32f22'

CORRECTIONS = {
    (787, 'vi'), (792, 'ko'), (793, 'fr'), (793, 'vi'),
    (797, 'hi'), (797, 'id'), (799, 'vi'), (801, 'zh-Hans'), (801, 'zh-Hant')
}

def sha(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def rationale(row):
    p, loc = row['position'], row['locale']
    if p == 787:
        return "The caller presents an alternative export format; the existing Vietnamese adds an export action and a game-library manager not present in the source."
    if p == 790:
        return "This appears after a failed owned-games lookup in the game catalog; naming the games the user owns makes the unavailable check clear without changing its meaning."
    if p == 792 and loc == 'es':
        return "Nearby Spanish onboarding copy uses informal second person, so tu matches the established voice."
    if p == 792 and loc == 'ko':
        return "The caller requests the PIN supplied by Moonlight; 받은 makes the source relation clear in Korean."
    if p == 793:
        return "The caller renders this heading in the failed page-load catch; use a concise, natural error heading for the locale."
    if p == 794:
        return "The pagination caller supplies the current page and total; 총 preserves the total count and placeholder order concisely."
    if p == 796:
        return "The caller counts Moonlight clients paired with this host; emparejados is the natural software-pairing term."
    if p == 797 and loc == 'hi':
        return "The caller uses this as the device-pairing section heading. पेयरिंग names the process rather than a pair object; this remains low confidence pending native Hindi review."
    if p == 797 and loc == 'id':
        return "The caller uses this as a section heading for the pairing process; Penyandingan names the process instead of a passive paired state."
    if p == 799:
        return "The field is a private-tracker passkey credential; Khóa truy cập is clearer than a generic key-code label."
    if p == 801 and loc in ('zh-Hans', 'zh-Hant'):
        return "The caller labels a token textarea; use the locale's standard UI verb for pasting rather than a generic stick verb."
    if p == 801:
        return "The caller labels a textarea instruction; use a polite instruction form consistent with nearby copy in this locale."
    raise ValueError((p, loc))

def write_sums(root):
    files = sorted(p for p in root.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt')
    (root/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(root).as_posix()}\n' for p in files), encoding='utf-8')

def main():
    cf_rows = rows(CF/'candidate-free-cells.jsonl')
    cross_rows = rows(CROSS/'integrated-cross-review-ledger.jsonl')
    assert len(cf_rows) == len(cross_rows) == 240
    cmap = {(r['position'], r['locale']): r for r in cf_rows}
    assert len(cmap) == 240
    out, selected = [], []
    counts = collections.Counter()
    for x in cross_rows:
        key = (x['position'], x['locale'])
        c = cmap[key]
        assert x['sourceSha256'] == c['sourceSha256']
        assert x['currentTargetSha256'] == c['currentTargetSha256']
        assert x['callerContextSha256'] == c['callerContextSha256']
        assert x['integratedTargetSha256'] == c['currentTargetSha256'] or x['integratedDecision'] == 'adopt_proposal'
        rec = {
            'schemaVersion': 1,
            'reviewStage': 'root-adjudication',
            'exactHead': HEAD,
            'exactTree': TREE,
            'position': x['position'],
            'catalogZeroBasedIndex': x['catalogZeroBasedIndex'],
            'catalogOneBasedPosition': x['catalogOneBasedPosition'],
            'locale': x['locale'],
            'sourceSha256': x['sourceSha256'],
            'currentTargetSha256': x['currentTargetSha256'],
            'callerContextSha256': x['callerContextSha256'],
            'primaryDisposition': x['primaryDisposition'],
            'blindDecision': x['blindDecision'],
            'integratedDecision': x['integratedDecision'],
            'integratedTargetSource': x['integratedTargetSource'],
            'integratedTargetSha256': x['integratedTargetSha256'],
            'confidence': x.get('confidence', 'moderate'),
            'nativeSpeakerApproval': False,
        }
        if c.get('callerless'):
            assert x['integratedDecision'] == 'hold_hash_only'
            assert 'source' not in c and 'currentTarget' not in c
            assert x.get('callerless') is True
            rec.update({
                'callerless': True,
                'rootDisposition': 'hold-hash-only',
                'rootTarget': None,
                'rootTargetSha256': None,
                'sourceTextIncluded': False,
                'currentTargetTextIncluded': False,
                'rationale': 'No production caller is pinned; preserve the text-free hash-only hold.'
            })
        else:
            assert x.get('callerless') is False
            rec.update({
                'callerless': False,
                'sourceId': c['sourceId'],
                'source': c['source'],
                'currentTarget': c['currentTarget'],
                'sourceTextIncluded': True,
                'currentTargetTextIncluded': True,
            })
            if x['integratedDecision'] == 'adopt_proposal':
                assert key in CORRECTIONS or x['position'] in (790,792,793,794,796,797,799,801)
                target = x['integratedTarget']
                disposition = 'correction' if key in CORRECTIONS else 'refinement'
                assert target != c['currentTarget']
                assert sha(target) == x['integratedTargetSha256']
                assert x['tokenAudit']['placeholdersMatch']
                assert x['tokenAudit']['markupMatches']
                assert x['tokenAudit']['numbersMatch']
                assert x['tokenAudit']['protectedLiteralsMatch']
                why = rationale(x)
                rec.update({
                    'rootDisposition': disposition,
                    'rootTarget': target,
                    'rootTargetSha256': sha(target),
                    'crossRecommendationSha256': x['integratedTargetSha256'],
                    'rationale': why,
                })
                selected.append({
                    'position': x['position'],
                    'locale': x['locale'],
                    'sourceId': c['sourceId'],
                    'source': c['source'],
                    'sourceSha256': c['sourceSha256'],
                    'currentTarget': c['currentTarget'],
                    'currentTargetSha256': c['currentTargetSha256'],
                    'rootTarget': target,
                    'rootTargetSha256': sha(target),
                    'rootDisposition': disposition,
                    'callerContextSha256': c['callerContextSha256'],
                    'primaryDisposition': x['primaryDisposition'],
                    'blindDecision': x['blindDecision'],
                    'integratedDecision': x['integratedDecision'],
                    'integratedTargetSource': x['integratedTargetSource'],
                    'crossRecommendationSha256': x['integratedTargetSha256'],
                    'rationale': why,
                    'confidence': 'low' if (x['position'],x['locale']) == (797,'hi') else x.get('confidence','moderate'),
                    'nativeSpeakerApproval': False,
                })
                if (x['position'],x['locale']) == (797,'hi'):
                    rec['confidence'] = 'low'
            else:
                assert x['integratedDecision'] == 'retain_current'
                assert x['integratedTarget'] == c['currentTarget']
                rec.update({
                    'rootDisposition': 'accept-current',
                    'rootTarget': c['currentTarget'],
                    'rootTargetSha256': c['currentTargetSha256'],
                    'rationale': 'Retain the exact-head translation; candidate-free caller context and both language reviews found no material issue.'
                })
        counts[rec['rootDisposition']] += 1
        out.append(rec)
    assert counts == {'accept-current':161,'refinement':22,'correction':9,'hold-hash-only':48}, counts
    assert len(selected) == 31
    (TASK/'root-disposition-ledger.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in out),encoding='utf-8')
    (TASK/'selected-targets.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in selected),encoding='utf-8')
    att = {
        'artifact':'ROMarrNG PR #70 W785-W804 root adjudication input attestation',
        'repository':'snapetech-org/ROMarrNG',
        'pullRequest':70,
        'window':'W785-W804',
        'exactHead':HEAD,
        'exactTree':TREE,
        'cellCount':240,
        'selectedTargetCount':31,
        'candidateFreeCellsSha256':sha((CF/'candidate-free-cells.jsonl').read_bytes()),
        'candidateFreeInputChecksumListSha256':sha((CF/'SHA256SUMS.txt').read_bytes()),
        'primaryLedgerSha256':sha((PR/'primary-review-ledger.jsonl').read_bytes()),
        'blindLedgerSha256':sha((BL/'blind-review-ledger.jsonl').read_bytes()),
        'integratedCrossLedgerSha256':sha((CROSS/'integrated-cross-review-ledger.jsonl').read_bytes()),
        'integratedCrossChecksumListSha256':sha((CROSS/'SHA256SUMS.txt').read_bytes()),
        'priorActiveHoldsCount':1012,
        'newCallerlessHashOnlyHolds':48,
        'resultingActiveHashOnlyHolds':1060,
        'nativeSpeakerApproval':False,
        'headedApplicationReviewPerformed':False,
        'catalogsEdited':False,
    }
    (TASK/'input-attestation.json').write_text(json.dumps(att,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary = {
        'artifact':'ROMarrNG PR #70 W785-W804 root adjudication',
        'repository':'snapetech-org/ROMarrNG',
        'pullRequest':70,
        'window':'W785-W804',
        'exactHead':HEAD,
        'exactTree':TREE,
        'cellCount':240,
        'rootDispositionCounts':dict(counts),
        'selectedTargetCount':len(selected),
        'selectedCorrectionCount':counts['correction'],
        'selectedRefinementCount':counts['refinement'],
        'callerlessHashOnlyHolds':counts['hold-hash-only'],
        'resultingActiveHashOnlyHolds':1060,
        'applicationPerformed':False,
        'nativeSpeakerApproval':False,
        'headedBrowserReviewPerformed':False,
        'lowConfidenceSelections':[{'position':797,'locale':'hi','sourceId':'ui.pairing.76dfd9f9a3'}],
        'confidence':'moderate',
        'rootAdjudicationPerformed':True,
    }
    (TASK/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (TASK/'README.md').write_text(
        '# ROMarrNG W785-W804 root adjudication\n\n'
        'Root adjudication is pinned to the exact product head and tree recorded below. It adopts the integrated cross-review target for 31 caller-backed cells, retains 161 current translations, and preserves 48 callerless hash-only holds. The 31 selected changes comprise 9 corrections and 22 refinements. All 1,012 predecessor holds remain unchanged, bringing the active total to 1,060.\n\n'
        'Hindi Pairing is low confidence and still needs native Hindi review. No native-speaker approval or application browser review is claimed. The selected targets are authorized for catalog application after exact-hash readback.\n\n'
        'Run python3 build_root_adjudication.py to regenerate the ledger from the sealed candidate-free, primary, blind, and integrated cross packets at the recorded paths. The script verifies exact hashes, caller contexts, protected content, and category totals before writing outputs.\n',
        encoding='utf-8')
    write_sums(TASK)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
