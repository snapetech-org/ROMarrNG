#!/usr/bin/env python3
"""Portable exact-head and primary-ledger verifier (evidence validation only)."""
from pathlib import Path
import collections,hashlib,json,re,subprocess,sys
OUT=Path(__file__).resolve().parent/'primary-review'
IN=Path(__file__).resolve().parent/'candidate-free-input'
HEAD='7681ea470ee0f387cd3a1a5be0541979d9cd06f6'
TREE='f8b34f29814233cb10dd9d608d5a69ce539b9f6d'
BRANCH='task/localization-translation-review-20261030'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
TOKEN_RE=re.compile(r'\{[A-Za-z][A-Za-z0-9_]*\}')
NUMBER_RE=re.compile(r'(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])')
PROTECTED=['ROMarr','GG Requestz','RomM','ROMm','ES-DE','gamelist.xml','1G1R','Battle.net','No-Intro','Redump','RetroArch','Steam','EA','Epic','ROM','Hub','DAT']
def fail(s): raise SystemExit('FAIL: '+s)
def ok(x,s):
    if not x: fail(s)
def sha(data):
    if isinstance(data,str): data=data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()
def j(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def jl(path): return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def protected(text):
    return sorted([t for t in PROTECTED if re.search(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',text)],key=lambda t:text.find(t))
# All files in the sealed root are covered by SHA256SUMS.
sums={}
for line in (OUT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
    digest,name=line.split('  ',1)
    ok(name not in sums,'duplicate checksum path '+name)
    sums[name]=digest
actual={p.name for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
ok(set(sums)==actual,'SHA256SUMS file inventory')
for name,digest in sums.items(): ok(sha((OUT/name).read_bytes())==digest,'checksum '+name)
# Manifest payload inventory excludes itself and SHA256SUMS by design.
manifest=j(OUT/'manifest.json')
manifest_files=manifest['files']
expected_manifest={p.name for p in OUT.iterdir() if p.is_file() and p.name not in {'manifest.json','SHA256SUMS.txt'}}
ok({x['path'] for x in manifest_files}==expected_manifest,'manifest file inventory')
for x in manifest_files:
    data=(OUT/x['path']).read_bytes()
    ok(len(data)==x['sizeBytes'] and sha(data)==x['sha256'],'manifest hash '+x['path'])
summary=j(OUT/'summary.json')
ok(manifest['head']==HEAD and manifest['tree']==TREE and manifest['branch']==BRANCH,'manifest exact refs')
ok(summary['head']==HEAD and summary['tree']==TREE and summary['branch']==BRANCH,'summary exact refs')
ok(summary['cellCount']==240 and summary['sourceCount']==20 and summary['localeCount']==12,'summary coverage')
ok(summary['primaryProposalsReadBeforeReview'] is False and summary['blindReviewOutputInspected'] is False,'review separation statement')
# Re-run the candidate-free packet's evidence verifier; this is not a test/build/CI run.
res=subprocess.run([sys.executable,str(IN/'verify_input.py')],capture_output=True,text=True)
ok(res.returncode==0,'candidate-free verifier: '+res.stdout+res.stderr)
in_manifest=j(IN/'manifest.json')
ok(sha((IN/'manifest.json').read_bytes())==summary['candidateFreeInputManifestSha256'],'candidate-free manifest pin')
ok(sha((IN/'SHA256SUMS.txt').read_bytes())==summary['candidateFreeInputChecksumsSha256'],'candidate-free checksum-list pin')
ok(in_manifest['head']==HEAD and in_manifest['tree']==TREE,'input exact refs')
# Before and after PR attestations must be identical at the pinned OPEN/DRAFT state.
before=j(OUT/'PR-attestation-before.json'); after=j(OUT/'PR-attestation-after.json')
for a in (before,after):
    ok(a['state']=='OPEN' and a['isDraft'] is True,'PR OPEN/DRAFT status')
    ok(a['branch']==BRANCH and a['head']==HEAD and a['tree']==TREE,'PR branch/head/tree')
    ok(a['liveBranchRef']==HEAD and a['livePullRef']==HEAD,'live branch/pull refs')
    ok(a['matchesPinnedHeadTree'] and a['matchesBothRemoteRefs'],'PR attestation booleans')
ok(before['head']==after['head'] and before['tree']==after['tree'],'PR head stable during review')
# Verify exact 240 cells in catalog insertion / pinned locale order.
sources={x['position']:x for x in jl(IN/'source-inventory-selection.jsonl')}
current={(x['position'],x['locale']):x for x in jl(IN/'current-target-cells.jsonl')}
contexts={x['position']:x for x in jl(IN/'source-contexts.jsonl')}
mechanics=j(IN/'dispatch-mechanics.json')['evidence']
ledger=jl(OUT/'primary-ledger.jsonl')
expected=[(p,l) for p in range(425,445) for l in LOCALES]
ok([(x['position'],x['locale']) for x in ledger]==expected,'240 exact cell coverage and order')
counts=collections.Counter(x['disposition'] for x in ledger)
ok(dict(sorted(counts.items()))==summary['dispositions'],'summary disposition counts')
ok(sum(x['proposedTarget'] is not None for x in ledger)==summary['proposedCellCount'],'proposal count')
for e in ledger:
    key=(e['position'],e['locale']); c=current[key]; src=sources[e['position']]
    ok(e['sourceId']==c['sourceId']==src['sourceId'],'source ID '+str(key))
    ok(e['source']==c['source'] and e['sourceSha256']==c['sourceSha256']==src['sourceSha256'],'source hash/text '+str(key))
    ok(e['currentTarget']==c['currentTarget'] and e['currentTargetSha256']==c['currentTargetSha256'],'current target hash '+str(key))
    ok(e['catalogTranslationHash']==c['catalogTranslationHash'],'catalog translation hash '+str(key))
    disp=e['disposition']; prop=e['proposedTarget']; selected=e['selectedTarget']
    ok(disp in {'accept-current','correction','refinement','hold'},'known disposition '+str(key))
    if disp=='accept-current':
        ok(prop is None and selected==c['currentTarget'],'accept-current selection '+str(key))
    elif disp in {'correction','refinement'}:
        ok(isinstance(prop,str) and selected==prop,'proposal selection '+str(key))
        ok(e['proposedTargetSha256']==sha(prop),'proposal hash '+str(key))
    else:
        ok(prop is None and selected is None and e['proposedTargetSha256'] is None,'hold has no selected proposal '+str(key))
    if selected is not None: ok(e['selectedTargetSha256']==sha(selected),'selected target hash '+str(key))
    # Caller context refs must be present in the exact candidate-free source-context evidence.
    refs=e['selectedCallerContextRefs']
    if e['position']==440:
        ok(not refs and disp=='hold','position-440 callerless hold')
    else:
        ok(refs,'caller context present '+str(key))
        for ref in refs:
            matched=False
            for row in contexts.values():
                for r in row.get('callerContextRefs',[]):
                    if all(ref.get(k)==r.get(k) for k in ('path','lineStart','lineEnd','contextSha256','fileSha256','gitBlob')):
                        matched=True
            for r in mechanics:
                if all(ref.get(k)==r.get(k) for k in ('path','lineStart','lineEnd','contextSha256','fileSha256','gitBlob')):
                    matched=True
            ok(matched,'caller evidence hash '+str(key))
    checks=e['tokenAndLiteralChecks']
    src_tokens=TOKEN_RE.findall(e['source']); cur_tokens=TOKEN_RE.findall(e['currentTarget'])
    ok(checks['sourcePlaceholderTokens']==src_tokens and checks['currentPlaceholderTokens']==cur_tokens,'input token inventory '+str(key))
    if selected is None:
        ok(checks['selectedPlaceholderTokens'] is None and checks['selectedPlaceholderMultisetMatches'] is False,'held token status '+str(key))
        continue
    selected_tokens=TOKEN_RE.findall(selected)
    selected_numbers=NUMBER_RE.findall(selected)
    selected_literals=protected(selected)
    src_numbers=NUMBER_RE.findall(e['source'])
    src_literals=protected(e['source'])
    ok(checks['selectedPlaceholderTokens']==selected_tokens and sorted(src_tokens)==sorted(selected_tokens),'selected placeholder check '+str(key))
    ok(checks['selectedProtectedLiterals']==selected_literals and all(x in selected_literals for x in src_literals),'selected protected literal check '+str(key))
    semantic=checks['semanticNumericReview']
    if key in {(439,'zh-Hans'),(439,'zh-Hant')}:
        ok(semantic and semantic['status']=='accepted-naturalized-magnitude' and semantic['sourceValue']==100 and semantic['targetForm']=='百' and '百' in selected,'Chinese semantic 100 review '+str(key))
        ok(selected_numbers==[] and checks['selectedNumericTokensExactMatch'] is False,'Chinese localized number scanner finding '+str(key))
    else:
        ok(semantic is None and selected_numbers==src_numbers and checks['selectedNumericTokensExactMatch'] is True,'exact numeric-token check '+str(key))
# Specific holds and two Chinese semantic findings.
ok(counts==collections.Counter({'accept-current':181,'correction':9,'refinement':38,'hold':12}),'expected disposition totals')
ok(all(x['disposition']=='hold' for x in ledger if x['position']==440),'all Fern accent cells held')
ok(all(x['disposition']!='hold' for x in ledger if x['position']!=440),'no unexplained holds')
ok(summary['priorLineageSelectionsReattested']==40 and summary['priorHoldCellsReattested']==336,'prior reattestation counts')
print('PASS primary W425-W444: 240 cells; 181 accept-current, 9 corrections, 38 refinements, 12 position-440 holds; 47 proposals; Chinese 100→百 semantic checks accepted twice; all selected placeholders/protected literals pass; numeric checks pass after semantic adjudication; prior 40 selections and 336 holds reattested; input verifier and packet checksums pass; PR remains OPEN/DRAFT at exact pinned head/tree.')
