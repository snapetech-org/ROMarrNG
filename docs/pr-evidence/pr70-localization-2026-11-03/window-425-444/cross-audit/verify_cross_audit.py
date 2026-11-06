#!/usr/bin/env python3
import collections, hashlib, json, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED_HEAD='7681ea470ee0f387cd3a1a5be0541979d9cd06f6'
EXPECTED_TREE='f8b34f29814233cb10dd9d608d5a69ce539b9f6d'
ALLOWED={'accept-current','correction','refinement','hold'}

def sha(b): return hashlib.sha256(b).hexdigest()
def htext(s): return sha(s.encode('utf-8'))
def jsonfile(p): return json.loads(p.read_text())
def readjl(p): return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
def verify_sumfile(folder, name='SHA256SUMS.txt', require_complete=True):
    sums=folder/name
    expected={}
    for line in sums.read_text().splitlines():
        if not line.strip(): continue
        digest,rel=line.split('  ',1)
        rel=rel.removeprefix("./")
        expected[rel]=digest
    for rel,digest in expected.items():
        p=folder/rel
        if not p.is_file() or sha(p.read_bytes())!=digest: raise SystemExit(f'checksum mismatch: {p}')
    actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p!=sums}
    if set(expected)-actual: raise SystemExit(f'checksum inventory missing entries in {folder}: {sorted(set(expected)-actual)}')
    if require_complete and actual!=set(expected): raise SystemExit(f'checksum inventory mismatch in {folder}: unlisted={sorted(actual-set(expected))}')
    return len(expected)

def main():
    outer_count=verify_sumfile(ROOT)
    cf=ROOT/'evidence/candidate-free-input'; primary=ROOT/'evidence/primary-review'; blind=ROOT/'evidence/blind-review'
    cf_count=verify_sumfile(cf,require_complete=False); p_count=verify_sumfile(primary,require_complete=False); b_count=verify_sumfile(blind,require_complete=False)
    for folder,verifier in [(cf,'verify_input.py'),(primary,'verify_primary.py'),(blind,'verify_blind.py')]:
        if not (folder/verifier).is_file(): raise SystemExit(f'missing portable input verifier: {folder/verifier}')
    cm=jsonfile(cf/'manifest.json'); pm=jsonfile(primary/'manifest.json'); bm=jsonfile(blind/'manifest.json'); om=jsonfile(ROOT/'manifest.json')
    for m in [cm,pm,bm,om]:
        if m.get('head')!=EXPECTED_HEAD or m.get('tree')!=EXPECTED_TREE: raise SystemExit('manifest exact-head/tree mismatch')
    rows=readjl(ROOT/'audit-ledger.jsonl')
    inputs=readjl(cf/'current-target-cells.jsonl'); prs=readjl(primary/'primary-ledger.jsonl'); bls=readjl(blind/'cell-review.jsonl')
    k=lambda r:(r['position'],r['locale'])
    I={k(x):x for x in inputs}; P={k(x):x for x in prs}; B={k(x):x for x in bls}; A={k(x):x for x in rows}
    if not (len(I)==len(P)==len(B)==len(A)==240 and I.keys()==P.keys()==B.keys()==A.keys()): raise SystemExit('240-cell coverage/alignment mismatch')
    ph=re.compile(r'\{([A-Za-z][A-Za-z0-9_]*)\}'); nr=re.compile(r'(?<![A-Za-z0-9])\d+(?:[.,]\d+)*(?![A-Za-z0-9])')
    counts=collections.Counter(); nat=0
    for key,row in A.items():
        src=I[key]; p=P[key]; b=B[key]
        for name,obj in [('audit',row),('primary',p),('blind',b)]:
            for field in ['sourceId','sourceSha256','currentTarget','currentTargetSha256']:
                if obj.get(field)!=src.get(field): raise SystemExit(f'{name} input identity mismatch {key} {field}')
        if row['disposition'] not in ALLOWED: raise SystemExit(f'bad disposition {key}')
        if not isinstance(row.get('selectedTarget'),str) or row['selectedTargetSha256']!=htext(row['selectedTarget']): raise SystemExit(f'selected target/hash mismatch {key}')
        checks=row['tokenAndLiteralChecks']
        source_ph=ph.findall(src['source']); target_ph=ph.findall(row['selectedTarget'])
        if collections.Counter(source_ph)!=collections.Counter(target_ph) or not checks['selectedPlaceholderMultisetMatches']: raise SystemExit(f'placeholder mismatch {key}')
        req=src.get('sourceProtectedLiterals',[])
        if checks.get('sourceProtectedLiterals')!=req or any(x not in row['selectedTarget'] for x in req) or not checks.get('selectedProtectedLiteralsPreserved'): raise SystemExit(f'protected literal mismatch {key}')
        source_num=nr.findall(src['source']); target_num=nr.findall(row['selectedTarget'])
        if collections.Counter(source_num)!=collections.Counter(target_num):
            if not (key[0]==439 and key[1] in ('zh-Hans','zh-Hant') and source_num==['100'] and target_num==[] and '百' in row['selectedTarget'] and checks['numericStatus']=='accepted-naturalized-magnitude'):
                raise SystemExit(f'numeric mismatch without adjudication {key}')
            nat+=1
        if row['disposition']=='accept-current' and row['selectedTarget']!=src['currentTarget']: raise SystemExit(f'accept-current target differs from current {key}')
        if key[0]==440 and row['disposition']!='accept-current': raise SystemExit(f'W440 not resolved to accept-current {key}')
        counts[row['disposition']]+=1
    if nat!=2: raise SystemExit(f'expected two Chinese 100-to-百 naturalizations, found {nat}')
    summary=jsonfile(ROOT/'summary.json')
    if summary.get('cellCount')!=240 or summary.get('crossAuditDecisionCounts')!=dict(sorted(counts.items())): raise SystemExit('summary count mismatch')
    if summary.get('currentWindowHoldCount')!=counts.get('hold',0) or summary.get('carriedPriorHoldCount')!=336 or summary.get('carriedPriorSelectedSourceCount')!=40: raise SystemExit('hold/selection lineage count mismatch')
    if summary.get('sourceCatalogDriftCount')!=0: raise SystemExit('source/catalog drift recorded')
    before=jsonfile(ROOT/'live-pr-before.json'); after=jsonfile(ROOT/'live-pr-after.json')
    for snap in [before,after]:
        pr=snap['pr']; refs=snap['refs']
        if pr.get('state')!='OPEN' or pr.get('isDraft') is not True or pr.get('headRefOid')!=EXPECTED_HEAD or snap.get('commitTree')!=EXPECTED_TREE: raise SystemExit('live PR attestation mismatch')
        if refs.get('refs/heads/task/localization-translation-review-20261030')!=EXPECTED_HEAD or refs.get('refs/pull/70/head')!=EXPECTED_HEAD: raise SystemExit('live branch/pull ref mismatch')
    drift=jsonfile(ROOT/'source-catalog-drift-check.json')
    if drift.get('commit')!=EXPECTED_HEAD or drift.get('tree')!=EXPECTED_TREE or drift.get('driftCount')!=0 or not drift.get('allExpectedTreeBlobsMatch') or not drift.get('allRawFileSha256AndGitBlobHashesMatch'): raise SystemExit('source/catalog pin check mismatch')
    we=jsonfile(ROOT/'supplemental-caller-evidence.json')
    if we.get('runtimeCatalogRegistration',{}).get('sourceToIdLookupResult')!='ui.fern-accent.fc8d0ac312' or len(we.get('runtimeCatalogRegistration',{}).get('localeTargets',{}))!=12: raise SystemExit('W440 source registration evidence missing')
    print(json.dumps({'status':'PASS','outerFiles':outer_count,'candidateFreeFiles':cf_count,'primaryFiles':p_count,'blindFiles':b_count,'cells':240,'decisions':dict(sorted(counts.items())),'naturalizedNumericCells':nat,'sourceCatalogPins':drift['pinnedFileCount'],'priorHoldsCarried':336,'priorSelectionsCarried':40},indent=2))
if __name__=='__main__': main()
