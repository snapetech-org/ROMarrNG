#!/usr/bin/env python3
import argparse, collections, hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
HEAD="8b7589775c526866e474112b4f4168782b02f881"
TREE="fb0ba93172f6832c687e001ce6c0fff08b5a33eb"
def sha(b): return hashlib.sha256(b).hexdigest()
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--candidate-free',default=str(ROOT.parent/'candidate-free/input/candidate-free-cells.jsonl'))
    ap.add_argument('--source-contexts',default=str(ROOT.parent/'candidate-free/input/source-contexts.jsonl'))
    args=ap.parse_args()
    sums=ROOT/'SHA256SUMS.txt'
    for line in sums.read_text(encoding='utf-8').splitlines():
        expected,name=line.split('  ',1); path=ROOT/name
        if not path.is_file() or sha(path.read_bytes())!=expected: raise SystemExit('FAIL checksum: '+name)
    ledger=jl(ROOT/'ledger.jsonl'); proposals=jl(ROOT/'proposals.jsonl'); holds=jl(ROOT/'holds.jsonl')
    if (len(ledger),len(proposals),len(holds))!=(240,24,72): raise SystemExit('FAIL record counts')
    if any(r.get('exactHead')!=HEAD or r.get('exactTree')!=TREE for r in ledger): raise SystemExit('FAIL ledger pins')
    ids=[r.get('cellId') or r.get('cellIdSha256') for r in ledger]
    if len(set(ids))!=240: raise SystemExit('FAIL duplicate cell identities')
    if collections.Counter(r['decision'] for r in ledger)!=collections.Counter({'accept-current':144,'correction':5,'refinement':19,'hold-hash-only':72}): raise SystemExit('FAIL decision totals')
    changed={(r['cellId'],r['proposedTarget']) for r in proposals}
    if changed!={(r['cellId'],r['proposedTarget']) for r in ledger if r['decision'] in ('correction','refinement')}: raise SystemExit('FAIL proposal/ledger set')
    for r in ledger:
        if r['decision'] in ('correction','refinement'):
            if r['proposedTarget']==r['currentTarget'] or sha(r['proposedTarget'].encode())!=r['proposedTargetSha256']: raise SystemExit('FAIL proposal target hash/no-op')
            if not r.get('proposedTargetTokenChecks') or not all(r['proposedTargetTokenChecks'].values()): raise SystemExit('FAIL proposed token checks')
        elif r['decision']=='accept-current' and 'proposedTarget' in r: raise SystemExit('FAIL proposal on accepted cell')
    forbidden={'sourceId','sourceText','currentTarget','locale','sourcePosition','catalogZeroBasedIndex','catalogOneBasedPosition'}
    for r in holds:
        if r.get('decision')!='hold-hash-only' or forbidden.intersection(r): raise SystemExit('FAIL hold text/identity disclosure')
        if any(k not in r for k in ('cellIdSha256','sourceSha256','currentTargetSha256','candidateFreeRowSha256')): raise SystemExit('FAIL incomplete hash-only hold')
    for name in ('exact-head-before.json','exact-head-after.json'):
        a=json.loads((ROOT/name).read_text())
        if a.get('headRefOid')!=HEAD or a.get('apiCommitSha')!=HEAD or a.get('apiCommitTree')!=TREE or a.get('branchRefOid')!=HEAD or a.get('pullRefOid')!=HEAD: raise SystemExit('FAIL '+name)
    inp=pathlib.Path(args.candidate_free)
    if inp.is_file():
        lines=inp.read_bytes().splitlines(); inputs=[json.loads(x) for x in lines]
        by={sha((r['sourceId']+'::'+r['locale']).encode()):(r,sha(line)) for line,r in zip(lines,inputs)}
        if len(by)!=240: raise SystemExit('FAIL candidate-free input count')
        for r in ledger:
            key=r.get('cellIdSha256') or sha(r['cellId'].encode()); pair=by.get(key)
            if not pair or pair[1]!=r['candidateFreeRowSha256']: raise SystemExit('FAIL candidate-free row binding')
            source,_=pair
            if r['decision']=='hold-hash-only':
                if not source['callerless'] or not source.get('sourceTextOmitted') or not source.get('currentTargetTextOmitted'): raise SystemExit('FAIL hold disposition')
                if source['sourceSha256']!=r['sourceSha256'] or source['currentTargetSha256']!=r['currentTargetSha256']: raise SystemExit('FAIL hold hashes')
            else:
                if source['callerless'] or r['sourceId']!=source['sourceId'] or r['locale']!=source['locale'] or r['sourceText']!=source['source'] or r['sourceTextSha256']!=source['sourceSha256'] or r['sourcePosition']!=source['position'] or r['currentTarget']!=source['currentTarget'] or r['currentTargetSha256']!=source['currentTargetSha256'] or r['callerContextSha256']!=source['callerContextSha256']: raise SystemExit('FAIL source/current/caller binding')
                if sha(r['sourceText'].encode())!=r['sourceTextSha256'] or sha(r['currentTarget'].encode())!=r['currentTargetSha256']: raise SystemExit('FAIL source/current text digest')
        contexts=pathlib.Path(args.source_contexts)
        if contexts.is_file():
            ctx={r['sourceId']:r for r in jl(contexts)}
            for r in ledger:
                if r['decision'] in ('accept-current','correction','refinement'):
                    c=ctx.get(r['sourceId'])
                    if not c or c['sourceSha256']!=r['sourceTextSha256'] or c['contextSha256']!=r['callerContextSha256']: raise SystemExit('FAIL caller-context binding')
            print('candidate-free rows and caller-context bindings PASS')
        else: print('caller-context bindings NOT CHECKED (supply --source-contexts)')
    else: print('candidate-free bindings NOT CHECKED (supply --candidate-free)')
    print('blind packet PASS: 240 cells, 24 proposals, 72 text-free hash holds; checksums and exact-head attestations verified')
if __name__=='__main__': main()
