#!/usr/bin/env python3
import collections, copy, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence'
PIN='7681ea470ee0f387cd3a1a5be0541979d9cd06f6'
PIN_TREE='f8b34f29814233cb10dd9d608d5a69ce539b9f6d'
NEW='d5ba7f1f268501f45227388c46d5f938ed0c9191'
NEW_TREE='2f8ce1af963b315108f668fc31c94ca90ecd1351'
BRANCH='task/localization-translation-review-20261030'
def sha(b): return hashlib.sha256(b).hexdigest()
def htxt(s): return sha(s.encode('utf-8'))
def readj(p): return json.loads(p.read_text())
def readjl(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def verify_sum(folder, root=False):
    sf=folder/'SHA256SUMS.txt'; expected={}
    for line in sf.read_text().splitlines():
        if not line.strip(): continue
        digest,rel=line.split('  ',1); rel=rel.removeprefix('./'); expected[rel]=digest
    for rel,digest in expected.items():
        p=folder/rel
        if not p.is_file() or sha(p.read_bytes())!=digest: raise SystemExit(f'checksum mismatch: {p}')
    actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p!=sf}
    if actual!=set(expected): raise SystemExit(f'checksum inventory mismatch: unlisted={sorted(actual-set(expected))} missing={sorted(set(expected)-actual)}')
    return len(expected)

def main():
    outer=verify_sum(ROOT,root=True)
    manifest=readj(ROOT/'manifest.json')
    if manifest.get('preApplyHead')!=PIN or manifest.get('preApplyTree')!=PIN_TREE or manifest.get('commit')!=NEW or manifest.get('tree')!=NEW_TREE: raise SystemExit('manifest pin mismatch')
    audit=readjl(E/'cross-audit-ledger.jsonl'); selected_file=readjl(E/'selected-change-ledger.jsonl')
    selected=[r for r in audit if r['disposition'] in ('correction','refinement')]
    if len(audit)!=240 or len(selected)!=46 or len(selected_file)!=46: raise SystemExit('audit ledger coverage mismatch')
    if collections.Counter(r['disposition'] for r in selected)!={'correction':17,'refinement':29}: raise SystemExit('selected change decision counts mismatch')
    if {(r['position'],r['locale'],r['selectedTargetSha256']) for r in selected}!={(r['position'],r['locale'],r['selectedTargetSha256']) for r in selected_file}: raise SystemExit('selected ledger mismatch')
    before_raw=(E/'pre-apply-ui-labels.json').read_bytes(); after_raw=(E/'post-apply-ui-labels.json').read_bytes()
    if sha(before_raw)!='d99f6636fefae13497849d8a88046d0bd6bb62c0d906fc030b2cc6946d6cd603': raise SystemExit('baseline catalog pin mismatch')
    before=json.loads(before_raw); after=json.loads(after_raw)
    audit_pin=readj(E/'cross-audit-summary.json')
    expected=copy.deepcopy(before)
    pairset=set()
    for r in selected:
        sid=r['sourceId']; loc=r['locale']; pair=(sid,loc)
        if pair in pairset: raise SystemExit('duplicate selected key/locale')
        pairset.add(pair)
        msg=before['messages'].get(sid)
        if not msg or msg['source']!=r['source'] or msg['translations'].get(loc)!=r['currentTarget']: raise SystemExit(f'baseline selected target mismatch {pair}')
        if htxt(r['selectedTarget'])!=r['selectedTargetSha256'] or htxt(r['currentTarget'])!=r['currentTargetSha256']: raise SystemExit(f'target hash mismatch {pair}')
        chk=r['tokenAndLiteralChecks']
        if not chk['selectedPlaceholderMultisetMatches'] or not chk['selectedProtectedLiteralsPreserved']: raise SystemExit(f'token/literal check failed {pair}')
        expected['messages'][sid]['translations'][loc]=r['selectedTarget']
    if after!=expected: raise SystemExit('catalog contains unexpected or missing changes')
    if list(before.keys())!=list(after.keys()) or list(before['messages'])!=list(after['messages']): raise SystemExit('catalog key order changed')
    if any(list(before['messages'][sid]['translations'])!=list(after['messages'][sid]['translations']) for sid in before['messages']): raise SystemExit('locale key order changed')
    all_keys={(r['sourceId'],r['locale']):r for r in audit}
    for key,r in all_keys.items():
        msg=after['messages'][r['sourceId']]
        if msg['source']!=r['source'] or msg['translations'].get(r['locale'])!=r['selectedTarget'] or htxt(msg['translations'][r['locale']])!=r['selectedTargetSha256']: raise SystemExit(f'240-cell readback mismatch {key}')
    changed=[]
    for sid,bmsg in before['messages'].items():
        for loc,target in bmsg['translations'].items():
            if target!=after['messages'][sid]['translations'][loc]: changed.append((sid,loc))
    if set(changed)!=pairset or len(changed)!=46: raise SystemExit('non-target catalog values changed')
    holds=readjl(E/'prior-hold-reattestation.jsonl'); sels=readjl(E/'prior-selection-reattestation.jsonl')
    if len(holds)!=336 or len(sels)!=40: raise SystemExit('prior lineage record count mismatch')
    for h in holds:
        for cat in [before,after]:
            m=cat['messages'].get(h['sourceId'])
            if not m or htxt(m['translations'][h['locale']])!=h['currentTargetSha256']: raise SystemExit(f'prior hold changed {(h["position"],h["locale"])}')
    for s in sels:
        if before['messages'][s['sourceId']]['source']!=after['messages'][s['sourceId']]['source']: raise SystemExit('prior selected source changed')
        if before['messages'][s['sourceId']]['translations']!=after['messages'][s['sourceId']]['translations']: raise SystemExit('prior selected source translations changed')
    readback=readj(E/'apply-readback.json')
    if readback.get('readbackCellCount')!=240 or readback.get('selectedEditCount')!=46 or readback.get('priorHoldCellsVerifiedUnchanged')!=336 or readback.get('priorSelectedSourcesVerifiedUnchanged')!=40 or readback.get('w440CurrentTargetsReadBack')!=12: raise SystemExit('readback summary mismatch')
    beforepr=readj(E/'live-pr-before-apply.json'); afterpr=readj(E/'live-pr-after-apply.json'); git=readj(E/'git-after-push.json')
    if beforepr['pr']['state']!='OPEN' or not beforepr['pr']['isDraft'] or beforepr['pr']['headRefOid']!=PIN or beforepr['tree']!=PIN_TREE: raise SystemExit('pre-apply PR pin mismatch')
    for snap in [afterpr]:
        if snap['pr']['state']!='OPEN' or not snap['pr']['isDraft'] or snap['pr']['headRefOid']!=NEW or snap['tree']!=NEW_TREE: raise SystemExit('post-apply PR state/head/tree mismatch')
        if snap['refs'].get('refs/heads/'+BRANCH)!=NEW or snap['refs'].get('refs/pull/70/head')!=NEW: raise SystemExit('post-apply branch/pull refs mismatch')
    if git.get('parent')!=PIN or git.get('commit')!=NEW or git.get('tree')!=NEW_TREE or git.get('changedPaths')!=['romarr/ui-labels.json'] or not git.get('localStatusClean'): raise SystemExit('commit evidence mismatch')
    # Match the post-apply catalog to the blob present in the pushed commit tree.
    if git.get('catalogFileSha256')!=sha(after_raw) or git.get('catalogFileBlob')!=git.get('remoteTreePathBlob'): raise SystemExit('pushed catalog blob mismatch')
    marker=git.get('bodyMarker')
    body=(E/'pr-body-after.md').read_text()
    if not marker or body.count(marker)!=1 or git.get('bodyMarkerCount')!=1 or afterpr.get('bodyMarkerCount')!=1: raise SystemExit('PR body marker count mismatch')
    if marker in (E/'pr-body-before.md').read_text(): raise SystemExit('PR body marker existed before update')
    if (E/'translation-catalog.patch').read_bytes()!=(E/'committed-translation-catalog.patch').read_bytes(): raise SystemExit('committed patch differs from applied patch')
    provenance=readj(E/'cross-audit-provenance.json')
    if provenance.get('crossAuditLedgerSha256')!=sha((E/'cross-audit-ledger.jsonl').read_bytes()): raise SystemExit('cross-audit ledger provenance mismatch')
    if provenance.get('crossAuditChecksumListSha256')!=sha((E/'cross-audit-SHA256SUMS.txt').read_bytes()): raise SystemExit('cross-audit checksum-list provenance mismatch')
    crosssums={}
    for line in (E/'cross-audit-SHA256SUMS.txt').read_text().splitlines():
        if line.strip():
            d,p=line.split('  ',1);crosssums[p.removeprefix('./')]=d
    if crosssums.get('audit-ledger.jsonl')!=sha((E/'cross-audit-ledger.jsonl').read_bytes()): raise SystemExit('cross-audit ledger not present in source checksum manifest')
    if crosssums.get('evidence/pinned-source/romarr/ui-labels.json')!=sha(before_raw): raise SystemExit('baseline catalog not present in source checksum manifest')
    print(json.dumps({'status':'PASS','packetFiles':outer,'auditCells':240,'appliedChanges':46,'decisions':{'correction':17,'refinement':29},'catalogChangedValues':len(changed),'priorHoldsVerified':len(holds),'priorSelectionsVerified':len(sels),'w440CurrentTargetsReadBack':12,'commit':NEW,'tree':NEW_TREE,'PRState':'OPEN/DRAFT','bodyMarkerCount':1},indent=2))
if __name__=='__main__': main()
