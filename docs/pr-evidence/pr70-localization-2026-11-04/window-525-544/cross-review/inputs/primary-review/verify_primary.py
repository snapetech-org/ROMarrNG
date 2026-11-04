#!/usr/bin/env python3
"""Verify ROMarrNG PR #70 W525-W544 primary decisions against candidate-free inputs."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
INPUT=HERE.parent/'candidate-free'/'input'
HEAD='eda48333438591ecc67f829c50ef2d521f1e7a5e'
TREE='3db18e56d0c7ac08a564a6baff61eba25f0a01da'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}')
TAG=re.compile(r'<[^>]+>')
NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
TEXT_FIELDS={'source','sourceText','currentTarget','target','targetText','proposedTarget','selectedTarget','finalTarget'}
def fail(m): raise SystemExit('FAIL: '+m)
def need(v,m):
    if not v: fail(m)
def sha(v): return hashlib.sha256(v.encode('utf-8') if isinstance(v,str) else v).hexdigest()
def j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def jl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); repo=ap.parse_args().repo.resolve()
    subprocess.run(['python3',str(INPUT/'verify_input.py'),'--repo',str(repo)],check=True,stdout=subprocess.DEVNULL)
    im=j(INPUT/'manifest.json'); need((im['head'],im['tree'],im['window'])==(HEAD,TREE,'W525-W544'),'input pin')
    input_cells=jl(INPUT/'current-target-cells.jsonl'); ib={(x['sourceId'],x['locale']):x for x in input_cells}
    contexts={x['sourceId']:x for x in jl(INPUT/'source-contexts.jsonl')}
    ledger=jl(HERE/'primary-ledger.jsonl'); proposals=jl(HERE/'primary-proposals.jsonl'); holds=jl(HERE/'primary-holds.jsonl')
    need(len(ledger)==240 and len({(x['sourceId'],x['locale']) for x in ledger})==240,'ledger coverage/uniqueness')
    need({(x['sourceId'],x['locale']) for x in ledger}==set(ib),'ledger/input key mapping')
    counts=dict(collections.Counter(x['disposition'] for x in ledger))
    need(counts=={'accept-current':213,'correction':15,'hold':12},'disposition counts')
    pmap={(x['sourceId'],x['locale']):x for x in proposals}; hmap={(x['sourceId'],x['locale']):x for x in holds}
    need(len(proposals)==15 and len(pmap)==15 and len(holds)==12 and len(hmap)==12,'proposal/hold count or duplicate')
    need(set(pmap)=={(x['sourceId'],x['locale']) for x in ledger if x['disposition']=='correction'},'proposal linkage')
    need(set(hmap)=={(x['sourceId'],x['locale']) for x in ledger if x['disposition']=='hold'},'hold linkage')
    for r in ledger:
        k=(r['sourceId'],r['locale']); c=ib[k]; ctx=contexts[r['sourceId']]
        need(r['window']=='W525-W544' and r['catalogZeroBasedIndex']==c['catalogZeroBasedIndex'] and r['catalogOneBasedPosition']==c['catalogZeroBasedIndex']+1,'cell position/window')
        for f in ('sourceId','sourceSha256','locale','currentTargetSha256','callerContextSha256','callerRefs','catalogTranslationHash'):
            need(r.get(f)==c.get(f),'input linkage '+str(k)+' '+f)
        need(r['nativeSpeakerApproval'] is False and r['reviewConfidence'] in ('moderate','high'),'unsupported approval/confidence '+str(k))
        if r['disposition']=='hold':
            need(ctx['callerless'] is True and not ctx['callers'] and r['callerContextAvailable'] is False,'hold caller context '+str(k))
            need(r['position']==530 and r['sourceId']=='ui.import-history.ef9992233a','unexpected callerless hold '+str(k))
            need(not (TEXT_FIELDS & set(r)),'callerless hold row contains source/target text '+str(k))
            need(bool(r.get('callerlessReason')),'hold reason missing '+str(k))
            h=hmap[k]
            need(not (TEXT_FIELDS & set(h)) and h.get('disposition')=='hold','hold artifact contains text or wrong disposition '+str(k))
            for f in ('window','position','sourceId','sourceSha256','locale','currentTargetSha256','callerContextSha256','disposition','callerlessReason'):
                need(h.get(f)==r.get(f),'hold artifact linkage '+str(k)+' '+f)
            need(r.get('callerRefs')==[],'callerless hold has caller refs '+str(k))
            continue
        need(ctx['callerless'] is False and bool(ctx['callers']),'caller-backed non-hold '+str(k))
        need(r.get('source')==c['source'] and r.get('currentTarget')==c['currentTarget'] and sha(r['currentTarget'])==c['currentTargetSha256'],'current/source text/hash linkage '+str(k))
        need(r['placeholderChecks']['source']==c['sourcePlaceholderTokens'] and r['placeholderChecks']['current']==c['currentPlaceholderTokens'] and r['placeholderChecks']['preserved'] is True and c['placeholderMultisetMatches'],'placeholder parity '+str(k))
        need(r['markupChecks']['source']==c['sourceMarkupTags'] and r['markupChecks']['current']==c['currentMarkupTags'] and r['markupChecks']['preserved'] is True and c['markupMatches'],'markup parity '+str(k))
        need(r['numericChecks']['source']==c['sourceNumericTokens'] and r['numericChecks']['current']==c['currentNumericTokens'] and r['numericChecks']['preserved'] is True and c['numericTokensPreserved'],'numeric parity '+str(k))
        need(r['protectedLiteralChecks']['source']==c['sourceProtectedLiterals'] and r['protectedLiteralChecks']['current']==c['currentProtectedLiterals'] and not r['protectedLiteralChecks']['missing'] and r['protectedLiteralChecks']['preserved'] is True and c['protectedLiteralsPreserved'],'protected literal parity '+str(k))
        need(bool(r.get('reviewedContext')) and bool(r.get('rationale')),'missing caller-specific review rationale '+str(k))
        if r['disposition']=='accept-current':
            need(k not in pmap and 'proposedTarget' not in r,'unexpected proposal on accepted row '+str(k))
            continue
        p=pmap[k]
        for f in ('window','position','sourceId','sourceSha256','locale','currentTargetSha256','currentTarget','proposedTarget','proposedTargetSha256','disposition','issueClass','rationale','callerContextSha256'):
            need(p.get(f)==r.get(f),'proposal linkage '+str(k)+' '+f)
        target=r['proposedTarget']; need(isinstance(target,str) and target.strip() and sha(target)==r['proposedTargetSha256'],'proposal target/hash '+str(k))
        need(collections.Counter(PH.findall(c['source']))==collections.Counter(PH.findall(target)),'proposal placeholder mismatch '+str(k))
        need(collections.Counter(TAG.findall(c['source']))==collections.Counter(TAG.findall(target)),'proposal markup mismatch '+str(k))
        need(collections.Counter(NUM.findall(c['source']))==collections.Counter(NUM.findall(target)),'proposal numeric mismatch '+str(k))
        need(all(x in target for x in c['sourceProtectedLiterals']),'proposal protected literal mismatch '+str(k))
        need(all(r['proposalTokenChecks'].values()),'proposal token flags '+str(k))
    s=j(HERE/'summary.json'); prov=j(HERE/'provenance.json')
    need((s['head'],s['tree'],s['cellCount'],s['sourceCount'],s['localeCount'])==(HEAD,TREE,240,20,12),'summary pin/coverage')
    need(s['dispositions']==counts and s['proposedCellCount']==15 and s['newHolds']==12 and s['holdPositions']==[530],'summary decisions')
    need(s['priorSelectedSourceCount']==140 and s['priorHoldCellCount']==540 and s['priorHoldChangedCells']==0 and s['priorAppliedCellCount']==28 and s['priorAppliedCellsChanged']==0,'prior lineage summary')
    need(s['candidateFreeInputManifestSha256']==sha((INPUT/'manifest.json').read_bytes()) and s['candidateFreeInputChecksumListSha256']==sha((INPUT/'SHA256SUMS.txt').read_bytes()),'input provenance hashes')
    need(prov['candidateFreeVerifier']=='PASS' and prov['reviewInputsWereCandidateFree'] is True and prov['blindOrCrossReviewContentConsulted'] is False and prov['nativeSpeakerApproval'] is False and prov['browserReviewClaimed'] is False,'unsupported review provenance')
    need(prov['candidateFreeInputManifestSha256']==s['candidateFreeInputManifestSha256'] and (prov['reviewedHead'],prov['reviewedTree'])==(HEAD,TREE),'provenance pin')
    # Primary file inventory and checksums are both exact.
    manifest=j(HERE/'manifest.json'); need((manifest['head'],manifest['tree'],manifest['window'])==(HEAD,TREE,'W525-W544'),'primary manifest pin')
    listed={x['path']:x for x in manifest['files']}; actual={p.name for p in HERE.iterdir() if p.is_file() and p.name not in {'manifest.json','SHA256SUMS.txt'}}
    need(set(listed)==actual,'primary manifest coverage')
    for n,row in listed.items():
        b=(HERE/n).read_bytes(); need(len(b)==row['bytes'] and sha(b)==row['sha256'],'primary manifest file hash '+n)
    sums={}
    for raw in (HERE/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h,n=raw.split('  ',1); sums[n]=h
    checksum_actual={p.name for p in HERE.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
    need(set(sums)==checksum_actual,'primary checksum coverage')
    for n,h in sums.items(): need(sha((HERE/n).read_bytes())==h,'primary checksum '+n)
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'sourceCount':20,'cellCount':len(ledger),'locales':12,'dispositions':counts,'proposals':len(proposals),'holds':len(holds),'holdPosition':530,'priorSelectedSourceIds':140,'priorHashOnlyHoldCells':540,'priorAppliedCells':28},sort_keys=True))
if __name__=='__main__': main()
