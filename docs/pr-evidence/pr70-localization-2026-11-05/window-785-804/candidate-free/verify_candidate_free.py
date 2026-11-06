#!/usr/bin/env python3
"""Verify sealed ROMarrNG PR #70 W785-W804 candidate-free evidence."""
import collections, json, pathlib, subprocess, sys
sys.dont_write_bytecode=True
import build_candidate_free as b

ROOT=pathlib.Path(__file__).resolve().parent; INP=ROOT/'input'; REPO=b.REPO
def fail(m): print('FAIL:',m); sys.exit(1)
def need(x,m):
    if not x: fail(m)
def main():
    outer=b.sums(ROOT); inner=b.sums(INP)
    need(b.git('rev-parse',f'{b.HEAD}^{{tree}}')==b.TREE,'pinned Git object tree')
    m=b.rj(INP/'manifest.json'); need((m.get('head'),m.get('tree'),m.get('window'),m.get('cellCount'))==(b.HEAD,b.TREE,b.WINDOW,240),'manifest pin/window')
    need(m.get('proposedTargetsIncluded') is False and m.get('reviewDecisionsIncluded') is False,'candidate-free manifest flags')
    before=b.rj(INP/'PR-attestation-before.json'); after=b.rj(INP/'PR-attestation-after.json')
    stable=('state','draft','merged','headRefName','head','tree','apiCommitTree','branchRefOid','pullRefOid','baseRefName','baseApiSha','baseLiveRefOid','bodySha256','bodyBytes')
    need(all(before.get(k)==after.get(k) for k in stable),'PR attestation continuity')
    need((after.get('head'),after.get('tree'),after.get('apiCommitTree'),after.get('branchRefOid'),after.get('pullRefOid'))==(b.HEAD,b.TREE,b.TREE,b.HEAD,b.HEAD),'recorded PR/head/ref pin')
    b.sums(b.PREV); b.sums(b.PREV_INPUT)
    pm=b.rj(b.PREV_INPUT/'manifest.json')
    need((pm.get('head'),pm.get('tree'),pm.get('window'),pm.get('resultingActiveHashOnlyHolds'))==(b.PREV_HEAD,b.PREV_TREE,b.PREV_WINDOW,1012),'predecessor candidate-free pin/holds')
    boundary=[r for r in b.rjl(b.PREV_INPUT/'selection-boundary.jsonl') if r.get('catalogZeroBasedIndex')==b.START and r.get('role')=='catalog-after-selected-end']
    need(len(boundary)==1,'predecessor boundary row')
    cells=b.rjl(INP/'candidate-free-cells.jsonl'); selected=b.rjl(INP/'selected-sources.jsonl'); contexts=b.rjl(INP/'source-contexts.jsonl')
    need((len(cells),len(selected),len(contexts))==(240,20,20),'current window evidence counts')
    locales=b.LOCALES; need(m.get('sourceCount')==20 and m.get('localeCount')==12,'manifest dimensions')
    catalog=json.loads(subprocess.check_output(['git','-C',str(REPO),'show',f'{b.HEAD}:romarr/ui-labels.json']))['messages']; ids=list(catalog)
    need(len(ids)==1836 and list(range(b.START,b.END+1))==[r['catalogZeroBasedIndex'] for r in selected],'catalog selection sequence')
    need((selected[0]['sourceId'],selected[0]['sourceSha256'])==(boundary[0]['sourceId'],boundary[0]['sourceSha256']),'W785 boundary continuity')
    need([(r['catalogZeroBasedIndex'],r['locale']) for r in cells]==[(i,l) for i in range(b.START,b.END+1) for l in locales],'cell ordering')
    production={p:b.file_tuple(p,b.HEAD) for p in b.prod_paths(b.HEAD)}
    ctx_by={r['sourceId']:r for r in contexts}; need(len(ctx_by)==20,'unique context sources')
    selected_by={r['sourceId']:r for r in selected}
    for sid,s in selected_by.items():
        idx=s['catalogZeroBasedIndex']; msg=catalog[sid]; source=msg['source']; sh=b.sha(source); rec=ctx_by[sid]
        need(ids[idx]==sid and sh==s['sourceSha256'] and msg.get('sourceHash')==sh,'selected source hash/position '+sid)
        actual=b.match_context({'sourceId':sid,'source':source,'sourceSha256':sh},production,b.HEAD)
        need(rec.get('contextSha256')==actual['contextSha256'] and rec.get('exactMatchCount')==actual['exactMatchCount'] and rec.get('callerless')==actual['callerless'],'caller context binding '+sid)
        if actual['callerless']:
            need(rec.get('sourceTextOmitted') is True and rec.get('callerTextOmitted') is True and not rec.get('callers'),'callerless context text leak '+sid)
            need(s.get('sourceTextOmitted') is True and 'source' not in s,'callerless selected source text leak '+sid)
        else:
            need(rec.get('source')==source and rec.get('callers')==actual['callers'],'caller evidence differs '+sid)
            need(s.get('source')==source,'selected source text '+sid)
    mismatch=collections.Counter(); callerless=[]
    forbidden={'proposedTarget','reviewDecision','decision','proposal','reviewerDecision'}
    for row in cells:
        need(not (forbidden & set(row)),'decision/proposal field in candidate-free cell')
        i,loc,sid=row['catalogZeroBasedIndex'],row['locale'],row['sourceId']; msg=catalog[sid]
        need(ids[i]==sid and b.sha(msg['source'])==row['sourceSha256'],'cell source pin '+sid+'/'+loc)
        need(row['callerContextSha256']==ctx_by[sid]['contextSha256'] and row['literalCallerCount']==ctx_by[sid]['exactMatchCount'],'cell caller binding '+sid+'/'+loc)
        need(b.sha(msg['translations'][loc])==row['currentTargetSha256'],'cell current target hash '+sid+'/'+loc)
        if row.get('callerless'):
            callerless.append(row)
            need(row.get('cellDisposition')=='hold-callerless-hash-only' and row.get('sourceTextOmitted') is True and row.get('currentTargetTextOmitted') is True,'callerless disposition')
            need(not any(k in row for k in ('source','currentTarget','proposedTarget')),'callerless text leak')
        else:
            source,target=msg['source'],msg['translations'][loc]
            need(row.get('source')==source and row.get('currentTarget')==target,'caller-backed text')
            tok=b.token_row(source,target)
            for k,v in tok.items(): need(row.get(k)==v,'token evidence mismatch '+sid+'/'+loc+'/'+k)
            mismatch['placeholder']+=not tok['placeholderMultisetMatches']; mismatch['markup']+=not tok['markupMatches']; mismatch['numeric']+=not tok['numericTokensPreserved']; mismatch['numericPresentationDifferences']+=tok['numericPresentationEquivalent']; mismatch['protectedLiteral']+=not tok['protectedLiteralsPreserved']
    need(m.get('callerlessHashOnlyCells')==len(callerless) and m.get('callerBackedCells')==240-len(callerless),'caller coverage counts')
    need(dict(mismatch)==b.rj(INP/'candidate-free-token-summary.json'),'token summary')
    need(sum(not x.get('callerless') for x in contexts)==m.get('callerBackedCells')//12,'caller-backed source count')
    # Reattest all prior hold rows as hashes only against the pinned current catalog.
    holds=b.rjl(INP/'prior-active-holds-hash-only.jsonl'); need(len(holds)==1012,'prior hold count')
    need(len({(r['sourceId'],r['locale']) for r in holds})==1012,'prior hold uniqueness')
    for r in holds:
        sid,loc=r['sourceId'],r['locale']; idx=r['catalogZeroBasedIndex']; msg=catalog[sid]
        need(not any(k in r for k in ('source','sourceText','currentTarget','target','targetText','proposedTarget')) and r.get('textOmitted') is True,'prior hold text leak')
        need(ids[idx]==sid and b.sha(msg['source'])==r['sourceSha256'] and b.sha(msg['translations'][loc])==r['currentTargetSha256']==r['priorTargetSha256'],'prior hold hash '+sid+'/'+loc)
    # Reattest prior source positions and applied target cells.
    sels=b.rjl(INP/'prior-selection-reattestation.jsonl'); need(len(sels)==400 and len({x['sourceId'] for x in sels})==400,'prior source selection lineage')
    for r in sels:
        sid,idx=r['sourceId'],r['catalogZeroBasedIndex']; msg=catalog[sid]
        need(ids[idx]==sid and b.sha(msg['source'])==r['currentSourceSha256']==r['priorSourceSha256'],'prior selected source hash '+sid)
    applied=b.rjl(INP/'prior-applied-cell-reattestation.jsonl'); need(len(applied)==154 and len({(x['sourceId'],x['locale']) for x in applied})==154,'prior applied target count')
    for r in applied:
        sid,loc=r['sourceId'],r['locale']; msg=catalog[sid]
        need(r.get('textOmitted') is True and b.sha(msg['source'])==r['sourceSha256'] and b.sha(msg['translations'][loc])==r['currentTargetSha256']==r['priorSelectedTargetSha256'],'prior applied target hash '+sid+'/'+loc)
    windows=[]
    for p in sorted(INP.glob('prior-*-cell-hash-reattestation.jsonl')):
        rows=b.rjl(p); need(len(rows)==240,'prior readback row count '+p.name); windows.append(rows[0]['priorWindow'])
        for r in rows:
            sid,loc=r['sourceId'],r['locale']; msg=catalog[sid]
            need(r.get('textOmitted') is True and b.sha(msg['translations'][loc])==r['currentTargetSha256']==r['priorTargetSha256'],'prior readback hash '+r['priorWindow']+'/'+sid+'/'+loc)
    need(len(windows)==11 and len(set(windows))==11 and b.PREV_WINDOW in windows,'complete historical readbacks')
    prev_h=b.rjl(INP/'prior-hold-context-reattestation.jsonl')
    need(len(prev_h)==len({r['sourceId'] for r in holds}),'prior hold caller context count')
    need(all(r.get('sourceTextOmitted') is True and r.get('callerTextOmitted') is True for r in prev_h),'prior hold context text leak')
    pin=b.rj(INP/'catalog-file-pins.json'); need(pin.get('head')==b.HEAD and pin.get('tree')==b.TREE and pin.get('catalogSha256')==b.sha(subprocess.check_output(['git','-C',str(REPO),'show',f'{b.HEAD}:romarr/ui-labels.json'])),'catalog pin')
    for r in b.rj(INP/'source-file-pins.json')['files']:
        raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{b.HEAD}:{r["path"]}'])
        need(b.sha(raw)==r['fileSha256'] and b.git('rev-parse',f'{b.HEAD}:{r["path"]}')==r['gitBlob'],'source file pin '+r['path'])
    need(m.get('nextBoundary',{}).get('sourceId')==ids[b.END+1] and m.get('nextBoundary',{}).get('sourceSha256')==b.sha(catalog[ids[b.END+1]]['source']),'next boundary')
    print(json.dumps({'result':'PASS','host':'kspld0','head':b.HEAD,'tree':b.TREE,'window':b.WINDOW,'cells':len(cells),'callerBackedCells':m['callerBackedCells'],'callerlessHashOnlyCells':len(callerless),'priorActiveHolds':len(holds),'resultingActiveHolds':m['resultingActiveHashOnlyHolds'],'priorAppliedCells':len(applied),'readbackWindows':len(windows),'tokenMismatches':dict(mismatch),'nextBoundary':m['nextBoundary'],'candidateFreeOnly':True,'pinnedGitObject':True,'outerAndInnerChecksums':'PASS'},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
