#!/usr/bin/env python3
import collections, hashlib, json
from pathlib import Path

BASE=Path(__file__).resolve().parent
CF=BASE/'candidate-free'/'input'
PRIMARY=BASE/'primary-review'
BLIND=BASE/'blind-review'
OUT=BASE
CROSS=OUT/'cross-review'
ROOT=OUT/'root-adjudication'
HEAD='43d2858744ef20cd58462643fed534ac61d2ffad'
TREE='73e8f50d65cb611def996b01bab0b00628b65860'
def sha(b): return hashlib.sha256(b).hexdigest()
def textsha(s): return sha(s.encode('utf-8'))
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def writej(p,x): p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def writejl(p,x): p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in x),encoding='utf-8')
def sums(d):
    files=sorted(p for p in d.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (d/'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(d).as_posix()}\n' for p in files),encoding='ascii')
def check_sums(d):
    expected={}
    for line in (d/'SHA256SUMS.txt').read_text().splitlines():
        h,n=line.split('  ',1); expected[n]=h
    actual={p.relative_to(d).as_posix():sha(p.read_bytes()) for p in d.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    assert expected==actual,(d, set(expected)^set(actual))
    return sha((d/'SHA256SUMS.txt').read_bytes())

manifest=load(CF/'manifest.json')
ps=load(PRIMARY/'summary.json')
bs=load(BLIND/'summary.json')
assert manifest['head']==ps['exactHead']==bs['exactPrHead']==HEAD
assert manifest['tree']==ps['exactTree']==TREE
assert manifest['cellCount']==ps['cellCount']==bs['records']==240
assert bs['inputSha256']['candidate-free-cells.jsonl']==sha((CF/'candidate-free-cells.jsonl').read_bytes())
assert bs['inputSha256']['source-contexts.jsonl']==sha((CF/'source-contexts.jsonl').read_bytes())
cf_rows=[]
for line in (CF/'candidate-free-cells.jsonl').read_bytes().splitlines():
    if line.strip(): cf_rows.append((json.loads(line),sha(line)))
contexts={r['sourceId']:r for r in rows(CF/'source-contexts.jsonl') if not r.get('callerless')}
primary=rows(PRIMARY/'ledger.jsonl')
blind=rows(BLIND/'review.jsonl')
assert len(cf_rows)==len(primary)==len(blind)==240
key=lambda x:(x['position'],x['locale'])
cmap={key(x):(x,h) for x,h in cf_rows}
pmap={(x['sourcePosition'],x['locale']):x for x in primary}
bmap={(x['position'],x['locale']):x for x in blind}
assert set(cmap)==set(pmap)==set(bmap)
choices={
 (693,'fr'):('correction','Pas de ROMarr sur cet appareil ? Copiez le lien et collez-le dans Amis → J’ai une invitation sur votre propre serveur.','The French invitation page shows a literal navigation route. The current value leaves Friends in English; the matching French UI label is Amis. The blind and primary proposals agree on this exact target; classify it as a correction because the route is currently partly untranslated.'),
 (697,'vi'):('refinement','Không có câu trả lời.','The exact caller uses this as a missing metadata answer fallback. The current phrase can read as a person not answering; this noun phrase states that no answer is available.'),
 (701,'ar'):('correction','لا توجد اتصالات بعد','The exact caller is the empty state for configured notification connections. The existing term can be read as links; this target uses the adjacent feature’s established connections term. Primary and blind proposals match exactly.'),
 (701,'vi'):('correction','Chưa có kết nối nào','The exact caller is an empty list before any notification connection is added. This makes the empty-entry meaning explicit instead of suggesting a connection process has not completed.'),
 (701,'zh-Hans'):('correction','尚未添加任何连接','The exact caller is an empty list before any notification connection is added. This says no connection entries have been added yet.'),
 (701,'zh-Hant'):('correction','尚未新增任何連線','The exact caller is an empty list before any notification connection is added. This says no connection entries have been added yet.'),
 (704,'id'):('refinement','Tidak ada pengindeks langsung yang dikonfigurasi. Pengindeks Prowlarr yang aktif tercantum di bawah.','The exact caller contrasts unconfigured direct indexers with enabled Prowlarr indexers below. This states the configuration condition explicitly while preserving Prowlarr.'),
}
ledger=[]; reconciliations=[]; counts=collections.Counter(); cross_counts=collections.Counter()
for k,(c,rowhash) in sorted(cmap.items()):
    p=pmap[k]; b=bmap[k]
    for name,r in [('primary',p),('blind',b)]:
        if r.get('sourceTextSha256',r.get('sourceSha256')) != c['sourceSha256']: raise ValueError((name,k,'source'))
        if r.get('currentTargetSha256') != c['currentTargetSha256']: raise ValueError((name,k,'target'))
        if r.get('callerContextSha256') != c['callerContextSha256']: raise ValueError((name,k,'caller'))
    callerless=bool(c.get('callerless'))
    item={
      'window':'W685-W704','position':c['position'],'locale':c['locale'],
      'sourceSha256':c['sourceSha256'],'currentTargetSha256':c['currentTargetSha256'],
      'callerContextSha256':c['callerContextSha256'],'candidateFreeRowSha256':rowhash,
      'primaryDecision':p['decision'],'blindDecision':b['decision'],
      'primaryProposalSha256':p.get('recommendedTargetSha256'),
      'blindProposalSha256':textsha(b['replacementText']) if b.get('replacementText') is not None else None,
      'callerlessHashOnlyHold':callerless,'exactHead':HEAD,'exactTree':TREE
    }
    if callerless:
        assert p['decision']=='hold-hash-only' and b['decision']=='hold'
        item.update({'rootDisposition':'hold-hash-only','rootTarget':None,'rootTargetSha256':None,
                     'rationale':'No production caller is attested for this target; retain the hash-only hold without source or target text.'})
        cross_counts['hold-hash-only']+=1
    else:
        ctx=contexts[c['sourceId']]
        assert ctx['contextSha256']==c['callerContextSha256'] and ctx['head']==HEAD and ctx['exactMatchCount']>0
        item.update({'sourceId':c['sourceId'],'source':c['source'],'currentTarget':c['currentTarget'],
                     'callerMatchCount':ctx['exactMatchCount'],'callerPaths':sorted({x['path'] for x in ctx['callers']}),
                     'callerLineNumbers':sorted({x['line'] for x in ctx['callers']})})
        if k in choices:
            disp,target,rationale=choices[k]
            assert b['decision'] in ('correction','refinement') and b['replacementText']==target,(k,b.get('replacementText'),target)
            if p.get('recommendedTarget') is not None: assert p['recommendedTarget']==target,(k,p['recommendedTarget'],target)
            assert textsha(target)==textsha(b['replacementText'])
            item.update({'rootDisposition':disp,'rootTarget':target,'rootTargetSha256':textsha(target),'rationale':rationale})
            cross_counts['selected-change']+=1
            reconciliations.append({k2:item[k2] for k2 in ('position','locale','sourceId','source','currentTarget','sourceSha256','currentTargetSha256','callerContextSha256','candidateFreeRowSha256','primaryDecision','blindDecision','primaryProposalSha256','blindProposalSha256','rootDisposition','rootTarget','rootTargetSha256','rationale','callerPaths','callerLineNumbers','exactHead','exactTree')})
        else:
            assert p['decision']=='accept-current' and b['decision']=='accept'
            item.update({'rootDisposition':'accept-current','rootTarget':c['currentTarget'],'rootTargetSha256':c['currentTargetSha256'],
                         'rationale':'Both independent semantic reviewers accept the current value for the exact pinned caller context.'})
            cross_counts['accept-current']+=1
    counts[item['rootDisposition']]+=1
    ledger.append(item)
assert counts=={'accept-current':221,'correction':5,'refinement':2,'hold-hash-only':12},counts
assert cross_counts=={'accept-current':221,'selected-change':7,'hold-hash-only':12},cross_counts
assert len(reconciliations)==7

primary_proposals={(r['sourcePosition'],r['locale']):r for r in rows(PRIMARY/'proposals.jsonl')}
blind_proposals={(r['position'],r['locale']):r for r in blind if r.get('replacementText') is not None}
assert len(primary_proposals)==2 and len(blind_proposals)==7
assert set(primary_proposals)=={(693,'fr'),(701,'ar')}
assert all(primary_proposals[k]['recommendedTarget']==blind_proposals[k]['replacementText'] for k in primary_proposals)
inputs={
 'repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':'task/localization-translation-review-20261030',
 'exactHead':HEAD,'exactTree':TREE,'window':'W685-W704','cellCount':240,
 'candidateFreeInputManifestSha256':sha((CF/'manifest.json').read_bytes()),
 'candidateFreeChecksumIndexSha256':sha((CF/'SHA256SUMS.txt').read_bytes()),
 'primarySummarySha256':sha((PRIMARY/'summary.json').read_bytes()),
 'primaryChecksumIndexSha256':sha((PRIMARY/'SHA256SUMS.txt').read_bytes()),
 'blindSummarySha256':sha((BLIND/'summary.json').read_bytes()),
 'blindChecksumIndexSha256':sha((BLIND/'SHA256SUMS.txt').read_bytes()),
 'candidateFreeCellsSha256':sha((CF/'candidate-free-cells.jsonl').read_bytes()),
 'sourceContextsSha256':sha((CF/'source-contexts.jsonl').read_bytes()),
 'blindCandidateFreePinsMatch':True,'blindOwnChecksumsVerified':True,
 'primaryReviewCacheEntryOmission':{'file':'primary-review/__pycache__/build_primary_review.cpython-314.pyc','sha256':'4f9375afaad4109799bb71e56a091578821c0ef8138c842bf21fce2a069492fe','committedEvidencePacket':'omitted as interpreter cache artifact','sourceTaskScratchCache':'preserved unchanged','copiedChecksumIndex':'omits only this absent pyc entry'}
}
writej(CROSS/'input-attestation.json',inputs)
writejl(CROSS/'cross-review-ledger.jsonl',ledger)
writejl(CROSS/'proposal-reconciliation.jsonl',reconciliations)
writej(CROSS/'summary.json',{
 'artifact':'ROMarrNG PR #70 W685-W704 cross-review and root selection',
 'repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':inputs['branch'],
 'exactHead':HEAD,'exactTree':TREE,'cellCount':240,'callerBackedCells':228,'hashOnlyHolds':12,
 'crossDispositionCounts':dict(cross_counts),'rootDispositionCounts':dict(counts),
 'primaryProposalCount':2,'blindProposalCount':7,'matchingPrimaryAndBlindTargets':2,
 'blindOnlySelectedProposals':5,'selectedChangeCount':7,'nativeSpeakerApproval':False,
 'headedBrowserReviewPerformed':False,'applicationPerformed':False
})
(CROSS/'README.md').write_text("""# ROMarrNG W685–W704 cross-review

This cross-review covers all 240 cells (20 source messages × 12 locales) at PR #70 product head 43d2858744ef20cd58462643fed534ac61d2ffad / tree 73e8f50d65cb611def996b01bab0b00628b65860. The primary review and independent blind review bind to the exact candidate-free source, current-target and caller-context hashes. The blind packet’s candidate-free file pins match the sealed input, and its own verifier passes.

Disposition: 221 accept-current, 5 corrections, 2 refinements, and 12 callerless hash-only holds. The two primary proposals match the blind proposals exactly (French invitation route at position 693 and Arabic notification-connections empty state at position 701). Five additional blind-only proposals are selected after root review against their exact callers: Vietnamese missing-answer fallback; Vietnamese, Simplified Chinese, and Traditional Chinese connection empty states; and the Indonesian direct-indexer configuration state.

The 12 callerless cells remain text-free holds. The 7 selected targets pass the reviewers’ placeholder, markup, number, and protected-literal checks. One absent pyc cache entry was removed from the copied primary checksum index; the source scratch cache remains intact. This machine/assistant review is not qualified native-speaker approval and does not claim headed-browser acceptance. No catalog application is included in this cross-review packet.
""",encoding='utf-8')
sums(CROSS)

writej(ROOT/'summary.json',{
 'artifact':'ROMarrNG W685-W704 root adjudication',
 'repository':'snapetech-org/ROMarrNG','pullRequest':70,'branch':inputs['branch'],
 'exactHead':HEAD,'exactTree':TREE,'cellCount':240,
 'rootDispositionCounts':dict(counts),'selectedTargets':len(reconciliations),
 'selectedCorrectionCount':5,'selectedRefinementCount':2,
 'callerlessHashOnlyHolds':12,'applicationPerformed':False,
 'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False,
 'independentCrossReviewDisposition':'PASS','result':'ROOT_ADJUDICATION_COMPLETE_APPLICATION_PENDING'
})
writejl(ROOT/'root-disposition-ledger.jsonl',ledger)
writejl(ROOT/'selected-targets.jsonl',reconciliations)
(ROOT/'README.md').write_text("""# ROMarrNG W685–W704 root adjudication

Root adjudication selects seven exact target values after binding the complete primary and independent blind review ledgers to the candidate-free packet. Five are corrections and two are refinements. It retains 221 existing caller-backed translations and 12 callerless values as text-free holds.

The French invitation route and Arabic connections empty-state targets were proposed identically by both reviewers. The five additional blind proposals were checked against the exact callers and selected with the rationales in selected-targets.jsonl. All selected strings pass source-token and protected-literal checks recorded in the primary and blind packets.

This packet pins product head 43d2858744ef20cd58462643fed534ac61d2ffad / tree 73e8f50d65cb611def996b01bab0b00628b65860. It does not establish native-speaker approval or headed-browser acceptance. Product application and readback are recorded separately. The copied primary-review checksum index omits a single absent pyc cache entry; the original task-scratch cache is preserved.
""",encoding='utf-8')
writej(ROOT/'input-attestation.json',inputs)
sums(ROOT)
print(json.dumps({'counts':dict(counts),'crossCounts':dict(cross_counts),'selected':len(reconciliations),'crossChecksum':check_sums(CROSS),'rootChecksum':check_sums(ROOT)},ensure_ascii=False,indent=2))
