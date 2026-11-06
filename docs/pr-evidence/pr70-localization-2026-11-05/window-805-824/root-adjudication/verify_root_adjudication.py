#!/usr/bin/env python3
"""Verify W805-W824 root adjudication against the portable sealed review packets."""
import argparse, collections, hashlib, json, subprocess, sys
from pathlib import Path

TASK=Path(__file__).resolve().parent; WINDOW_ROOT=TASK.parent
CF=WINDOW_ROOT/'candidate-free'; PR=WINDOW_ROOT/'primary-review'; BL=WINDOW_ROOT/'blind-review'; CROSS=WINDOW_ROOT/'cross-review'
HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'; TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'; CAT='romarr/ui-labels.json'
EXPECTED=collections.Counter({'accept-current':217,'hold-low-confidence-current':10,'correction':6,'refinement':7})

def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def rows(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def verify_sums(root):
    p=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=root,text=True,capture_output=True)
    if p.returncode: raise ValueError(f'checksum failed: {root}: {p.stderr}')
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[5]); a=ap.parse_args(); repo=a.repo.resolve()
    verify_sums(TASK)
    for p in (CF,CF/'input',CF/'predecessor',PR,BL,CROSS): verify_sums(p)
    expected_copies={'candidate-free':CF,'primary':PR,'independent-blind':BL}
    check=json.loads((CROSS/'input-packet-checksums.json').read_text(encoding='utf-8'))
    for item in check['inputs']:
        dest=expected_copies[item['name']]
        if len(item['files'])!=item['fileCount']: raise ValueError('input file-count mismatch')
        for f in item['files']:
            p=dest/f['path']
            if not p.is_file() or p.stat().st_size!=f['byteCount'] or sha(p.read_bytes())!=f['sha256']:
                raise ValueError(f'portable input checksum mismatch {item["name"]}/{f["path"]}')
    if git(repo,'rev-parse',HEAD+'^{tree}')!=TREE: raise ValueError('pinned input tree mismatch')
    catalog_raw=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:{CAT}']); catalog=json.loads(catalog_raw); messages=catalog['messages']; ids=list(messages)
    if sha(catalog_raw)!=json.loads((TASK/'input-attestation.json').read_text())['inputCatalogSha256']: raise ValueError('input catalog hash mismatch')
    cf=rows(CF/'input/candidate-free-cells.jsonl'); contexts={r['sourceId']:r for r in rows(CF/'input/source-contexts.jsonl')}; cross=rows(CROSS/'integrated-cross-review-ledger.jsonl')
    ledger=rows(TASK/'root-disposition-ledger.jsonl'); selected=rows(TASK/'selected-targets.jsonl'); low=rows(TASK/'low-confidence-language-holds.jsonl')
    if (len(cf),len(cross),len(ledger),len(selected),len(low))!=(240,240,240,13,10): raise ValueError('row counts')
    cfm={(r['sourceId'],r['locale']):r for r in cf}; xm={(r['sourceId'],r['locale']):r for r in cross}; lm={(r['sourceId'],r['locale']):r for r in ledger}; sm={(r['sourceId'],r['locale']):r for r in selected}; lowm={(r['sourceId'],r['locale']):r for r in low}
    if not (len(cfm)==len(xm)==len(lm)==240 and len(sm)==13 and len(lowm)==10): raise ValueError('duplicate cell rows')
    if (TASK/'low-confidence-language-holds.jsonl').read_bytes()!=(CROSS/'unresolved-language-holds.jsonl').read_bytes(): raise ValueError('low-confidence hold packet not copied byte-for-byte')
    h1=TASK/'prior-active-holds-hash-only.jsonl'; h2=TASK/'w785-current-window-holds-hash-only.jsonl'
    if h1.read_bytes()!=(CROSS/'prior-active-holds-hash-only.jsonl').read_bytes() or h2.read_bytes()!=(CROSS/'current-window-holds-hash-only.jsonl').read_bytes(): raise ValueError('active hold copies differ from integrated input')
    holds=rows(h1)+rows(h2)
    if len(holds)!=1060 or len({(r['sourceId'],r['locale']) for r in holds})!=1060: raise ValueError('active hold count/uniqueness')
    forbidden={'source','sourceText','currentTarget','target','targetText','proposedTarget','translation','reviewDecision','decision'}
    if any(r.get('textOmitted') is not True or forbidden.intersection(r) for r in holds): raise ValueError('hash-only hold contains text/decision')
    for h in holds:
        m=messages[h['sourceId']]; loc=h['locale']
        if sha(m['source'])!=h['sourceSha256'] or sha(m['translations'][loc])!=h['currentTargetSha256']: raise ValueError('active hold differs from input catalog')
    counts=collections.Counter()
    for key,c in cfm.items():
        x= xm[key]; r=lm[key]; ctx=contexts[key[0]]
        if (r['exactHead'],r['exactTree'])!=(HEAD,TREE): raise ValueError('root row head/tree')
        if (r['sourceSha256'],r['currentTargetSha256'],r['callerContextSha256'])!=(c['sourceSha256'],c['currentTargetSha256'],c['callerContextSha256']): raise ValueError('source/current/context hash mismatch')
        if (r['source'],r['currentTarget'])!=(c['source'],c['currentTarget']): raise ValueError('source/current text mismatch')
        if (r['integratedDecision'],r['integratedTargetSha256'])!=(x['integratedDecision'],x['integratedTargetSha256']): raise ValueError('integrated decision hash mismatch')
        if r['callerless'] is not False or c['callerless'] is not False: raise ValueError('unexpected callerless cell')
        refs=[{'path':q['path'],'line':q['line'],'matchKind':q['matchKind'],'lineSha256':q['lineSha256'],'excerptSha256':q['excerptSha256'],'fileSha256':q['fileSha256'],'gitBlob':q['gitBlob']} for q in ctx['callers']]
        if r['callerReferenceCount']!=ctx['exactMatchCount'] or r['callerReferences']!=refs or r['callerContextSha256']!=ctx['contextSha256']: raise ValueError('caller context reference mismatch')
        if sha(json.dumps(c,ensure_ascii=False,sort_keys=True,separators=(',',':')))!=r['candidateFreeCellRecordSha256']: raise ValueError('candidate-free row hash mismatch')
        if sha(r['rootTarget'])!=r['rootTargetSha256']: raise ValueError('root target hash mismatch')
        counts[r['rootDisposition']]+=1
        if key in sm:
            s=sm[key]
            if r['rootDisposition'] not in ('correction','refinement'): raise ValueError('selected root disposition')
            if r['rootTarget']!=x['integratedTarget'] or r['rootTargetSha256']!=x['integratedTargetSha256'] or s['rootTarget']!=r['rootTarget'] or s['rootTargetSha256']!=r['rootTargetSha256']: raise ValueError('selected root target mismatch')
            if not all(x['tokenAudit'].get(k) for k in ('placeholdersMatch','markupMatches','numbersMatch','protectedLiteralsMatch')): raise ValueError('selected token audit')
        elif key in lowm:
            h=lowm[key]
            if r['rootDisposition']!='hold-low-confidence-current' or r['rootTarget']!=c['currentTarget'] or r['rootTargetSha256']!=c['currentTargetSha256']: raise ValueError('low-confidence hold did not retain current')
            if h['currentTargetSha256']!=r['currentTargetSha256'] or h['integratedTargetSha256']!=r['rootTargetSha256'] or h['heldProposalSha256']!=r['heldProposalSha256']: raise ValueError('low-confidence hold hashes')
        else:
            if r['rootDisposition']!='accept-current' or r['rootTarget']!=c['currentTarget'] or r['rootTargetSha256']!=c['currentTargetSha256']: raise ValueError('current target disposition')
        if r['nativeSpeakerApproval'] is not False: raise ValueError('native-speaker claim')
    if counts!=EXPECTED: raise ValueError(f'root dispositions {counts}')
    if set(sm)&set(lowm) or set(sm)&{(h['sourceId'],h['locale']) for h in holds}: raise ValueError('selected target overlaps hold')
    summary=json.loads((TASK/'summary.json').read_text()); att=json.loads((TASK/'input-attestation.json').read_text()); lineage=json.loads((TASK/'hold-lineage.json').read_text())
    if summary['rootDispositionCounts']!=dict(sorted(counts.items())) or summary['selectedTargetCount']!=13 or summary['lowConfidenceLanguageHolds']!=10: raise ValueError('root summary')
    if att['exactHead']!=HEAD or att['exactTree']!=TREE or att['selectedTargetCount']!=13 or att['lowConfidenceLanguageHoldCount']!=10: raise ValueError('attestation')
    if lineage['totalActiveHashOnlyHoldCount']!=1060 or lineage['byteForByteCopied'] is not True: raise ValueError('hold lineage summary')
    if summary['nativeSpeakerApproval'] is not False or summary['productApplicationPerformed'] is not False: raise ValueError('review scope')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':240,'selectedTargets':13,'dispositions':dict(sorted(counts.items())),'lowConfidenceLanguageHolds':10,'priorActiveHashOnlyHolds':1060,'resultingActiveHashOnlyHolds':1060,'nativeSpeakerApproval':False,'portableInputs':'PASS','checksums':'PASS'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'FAIL: {e}',file=sys.stderr); sys.exit(1)
