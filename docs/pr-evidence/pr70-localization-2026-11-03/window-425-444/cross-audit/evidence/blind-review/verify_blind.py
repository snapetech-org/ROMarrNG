#!/usr/bin/env python3
import hashlib, json, re, sys
from pathlib import Path
root=Path(__file__).resolve().parent

def sha(b): return hashlib.sha256(b).hexdigest()
def check(ok,msg):
    if not ok: raise SystemExit('FAIL '+msg)
# Verify all sealed file checksums except the checksum manifest itself.
sums={}
for line in (root/'SHA256SUMS.txt').read_text().splitlines():
    if not line.strip(): continue
    digest,name=line.split('  ',1); sums[name]=digest
    p=root/name
    check(p.is_file(),f'missing {name}')
    check(sha(p.read_bytes())==digest,f'checksum mismatch {name}')
check('SHA256SUMS.txt' not in sums,'checksum file must not self-hash')
# Verify the embedded candidate-free source packet.
inp=root/'evidence'/'candidate-free-input'
input_sums={}
for line in (inp/'SHA256SUMS.txt').read_text().splitlines():
    digest,name=line.split('  ',1); input_sums[name]=digest
    p=inp/name
    check(p.is_file() and sha(p.read_bytes())==digest,f'candidate-free checksum mismatch {name}')
manifest=json.loads((root/'manifest.json').read_text())
check(manifest['head']=='7681ea470ee0f387cd3a1a5be0541979d9cd06f6','pinned head')
check(manifest['tree']=='f8b34f29814233cb10dd9d608d5a69ce539b9f6d','pinned tree')
check(manifest['branch']=='task/localization-translation-review-20261030','pinned branch')
check(sha((inp/'SHA256SUMS.txt').read_bytes())==manifest['candidateFreeInputChecksumListSha256'],'candidate-free checksum-list hash')
check(manifest['sourceCount']==20 and manifest['localeCount']==12 and manifest['cellCount']==240,'window dimensions')
source={}
for line in (inp/'current-target-cells.jsonl').read_text().splitlines():
    d=json.loads(line); source[(d['position'],d['locale'])]=d
ledger=[json.loads(x) for x in (root/'cell-review.jsonl').read_text().splitlines()]
check(len(ledger)==240,'ledger row count')
seen=set(); counts={}
for d in ledger:
    k=(d['position'],d['locale']); check(k not in seen,'duplicate cell'); seen.add(k)
    check(k in source,'unexpected cell')
    baseline=source[k]
    for field,src in [('sourceId','sourceId'),('source','source'),('sourceSha256','sourceSha256'),('currentTarget','currentTarget'),('currentTargetSha256','currentTargetSha256'),('callerContextSha256','callerContextSha256')]:
        check(d[field]==baseline[src],f'{field} mismatch {k}')
    check(sha(d['currentTarget'].encode())==d['currentTargetSha256'],f'current hash {k}')
    disp=d['disposition']; counts[disp]=counts.get(disp,0)+1
    check(disp in ('accept-current','correction','refinement','hold'),f'bad disposition {k}')
    if disp=='accept-current': check(d['proposedTarget'] is None and d['proposedTargetSha256'] is None,f'accept has proposal {k}')
    if d['proposedTarget'] is not None:
        check(sha(d['proposedTarget'].encode())==d['proposedTargetSha256'],f'proposal hash {k}')
    ph=d['placeholderCheck']; check(ph['currentMatches'] and ph['proposedMatches'],f'placeholder mismatch {k}')
    lit=d['protectedLiteralCheck']; check(lit['currentPreserved'] and lit['proposedPreserved'],f'protected literal mismatch {k}')
check(seen==set(source),'ledger coverage')
check(counts==manifest['decisionCounts'], 'decision counts')
check(counts=={'accept-current':214,'correction':17,'refinement':9},'expected blind decision counts')
changes=[d for d in ledger if d['proposedTarget'] is not None]
summary=json.loads((root/'change-summary.json').read_text())
check(summary['changeCount']==len(changes)==26,'change summary count')
check([(d['position'],d['locale'],d['currentTargetSha256'],d['proposedTargetSha256']) for d in summary['changes']]==[(d['position'],d['locale'],d['currentTargetSha256'],d['proposedTargetSha256']) for d in changes],'change summary hashes')
check(counts.get('hold',0)==0,'unexpected current-window hold')
# Both Chinese top-100 variants are semantic equivalents; all other digits match literally.
for locale, phrase in [('zh-Hans','百大榜单文章'),('zh-Hant','百大榜單文章')]:
    d=next(x for x in ledger if x['position']==439 and x['locale']==locale)
    check(d['disposition']=='accept-current' and phrase in d['currentTarget'] and d['numericReview']['mismatchResolution'],'top-100 disposition')
# Carried hold evidence must remain exactly the embedded candidate-free evidence and unchanged by target hash.
prior=(root/'evidence'/'prior-hold-reattestation.jsonl').read_bytes()
check(prior==(inp/'prior-hold-reattestation.jsonl').read_bytes(),'carried hold evidence copy')
holds=[json.loads(x) for x in prior.decode().splitlines()]
check(len(holds)==336,'carried hold count')
check(all(x['targetUnchanged'] and x['priorTargetSha256']==x['currentTargetSha256'] and x['reattestedAtHead']==manifest['head'] for x in holds),'carried holds changed')
sel=(root/'evidence'/'prior-selection-reattestation.jsonl').read_bytes()
check(sel==(inp/'prior-selection-reattestation.jsonl').read_bytes(),'prior selection evidence copy')
check(len(sel.decode().splitlines())==40,'prior selection count')
# Context evidence is copied byte-for-byte and each source row points to that exact context hash.
check((root/'evidence'/'source-contexts.jsonl').read_bytes()==(inp/'source-contexts.jsonl').read_bytes(),'caller context copy')
check((root/'evidence'/'dispatch-mechanics.json').read_bytes()==(inp/'dispatch-mechanics.json').read_bytes(),'dispatch evidence copy')
att=json.loads((root/'live-pr-attestation.json').read_text())
for stage in ('observedBefore','observedAfter'):
    o=att[stage]
    check(isinstance(o,dict),f'missing live ref observation {stage}')
    check(o['state']=='OPEN' and o['isDraft'] is True and o['headRefName']==manifest['branch'] and o['baseRefName']=='main' and o['baseRefOid']=='bcd1eb41b5cdf8202acb5cf8e365e14761b743b5' and o['headRefOid']==manifest['head'] and o['headTree']==manifest['tree'] and o['liveBranchRefOid']==manifest['head'] and o['livePullRefOid']==manifest['head'] and o['readOnlyCheckoutWorktreeClean'] is True,f'live PR pin {stage}')
print('PASS blind W425-W444: 240 exact-hash cells; decisions '+json.dumps(counts,sort_keys=True)+'; 336 carried holds and 40 prior selections reattested; placeholders/protected literals valid; numeric-100 equivalence documented; source/caller evidence and checksums pass; live PR OPEN/DRAFT refs pinned before/after.')
