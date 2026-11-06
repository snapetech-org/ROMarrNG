#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, unicodedata
from pathlib import Path

P=Path(__file__).resolve().parent
PACKET=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-w805-824-candidate-free-20261105')
INPUT=PACKET/'input'; PREDECESSOR=PACKET/'predecessor'
HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'; TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
OUTER_SUMS_SHA='cf34d5b87ae6e06aa09152a09a87da51025c40e47ed2e18d2237c666e912b8ba'

def fail(s): raise SystemExit('FAIL: '+s)
def sha(b): return hashlib.sha256(b).hexdigest()
def tsha(s): return sha(s.encode('utf-8'))
def canon(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def verify_dir(root, checksum_file):
    listed={}
    for line in checksum_file.read_text(encoding='utf-8').splitlines():
        h,n=line.split('  ',1)
        if n in listed or not (root/n).is_file() or sha((root/n).read_bytes())!=h: fail('checksum '+n)
        listed[n]=h
    actual={x.relative_to(root).as_posix() for x in root.rglob('*') if x.is_file() and x.relative_to(root)!=checksum_file.relative_to(root)}
    if actual!=set(listed): fail('checksum inventory '+str(root))
    return listed
def token_audit(source,target,protected):
    ph=lambda s:collections.Counter(re.findall(r'\{[A-Za-z_][A-Za-z0-9_]*\}',s))
    tags=lambda s:collections.Counter(re.findall(r'</?[A-Za-z][^>]*>',s))
    nums=lambda s:[''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t) for t in re.findall(r'\d+',s)]
    sp,tp=ph(source),ph(target); st,tt=tags(source),tags(target); sn,tn=nums(source),nums(target)
    protected=list(protected or [])
    return {'placeholders':{'source':sorted(sp.elements()),'target':sorted(tp.elements()),'matches':sp==tp},
      'markup':{'source':sorted(st.elements()),'target':sorted(tt.elements()),'matches':st==tt},
      'numbers':{'source':sn,'target':tn,'sourcePreserved':all(tn.count(x)>=n for x,n in collections.Counter(sn).items())},
      'protectedLiterals':{'source':protected,'missing':[x for x in protected if x not in target]}}

def main():
    outer=verify_dir(PACKET,PACKET/'SHA256SUMS.txt')
    if sha((PACKET/'SHA256SUMS.txt').read_bytes())!=OUTER_SUMS_SHA: fail('outer candidate-free checksum-list digest')
    ins=verify_dir(INPUT,INPUT/'SHA256SUMS.txt'); prevs=verify_dir(PREDECESSOR,PREDECESSOR/'SHA256SUMS.txt')
    outs=verify_dir(P,P/'SHA256SUMS.txt')
    im=readj(INPUT/'manifest.json'); m=readj(P/'manifest.json'); s=readj(P/'summary.json')
    if (im.get('head'),im.get('tree'),im.get('window'),im.get('cellCount'),im.get('sourceCount'),im.get('callerBackedCells'),im.get('callerlessHashOnlyCells'),im.get('priorActiveHashOnlyHoldsReattested'),im.get('resultingActiveHashOnlyHolds'),im.get('reviewDecisionsIncluded'),im.get('proposedTargetsIncluded'))!=(HEAD,TREE,'W805-W824',240,20,240,0,1060,1060,False,False): fail('candidate-free input pin')
    if (m.get('head'),m.get('tree'),m.get('window'),m.get('role'),m.get('cellCount'),m.get('callerBackedCells'))!=(HEAD,TREE,'W805-W824','independent-blind-semantic-review',240,240): fail('blind manifest pin')
    declared={r['path']:r['sha256'] for r in m['files']}
    actual={x.relative_to(P).as_posix():sha(x.read_bytes()) for x in P.rglob('*') if x.is_file() and x.name not in ('manifest.json','SHA256SUMS.txt')}
    if declared!=actual: fail('manifest file hashes')
    cells=readjl(INPUT/'candidate-free-cells.jsonl'); contexts=readjl(INPUT/'source-contexts.jsonl'); ctx={r['sourceId']:r for r in contexts}
    ledger=readjl(P/'blind-review-ledger.jsonl')
    if len(cells)!=240 or len(ledger)!=240 or len(ctx)!=20: fail('cell/context coverage')
    counts=collections.Counter()
    for inp,out in zip(cells,ledger):
        for k in ('position','catalogZeroBasedIndex','catalogOneBasedPosition','sourceId','sourceSha256','locale'):
            if inp.get(k)!=out.get(k): fail('cell identity '+k)
        if (out.get('head'),out.get('tree'))!=(HEAD,TREE): fail('cell product pin')
        if out.get('source')!=inp.get('source') or out.get('currentTarget')!=inp.get('currentTarget'): fail('source/current text mismatch')
        if tsha(out['source'])!=inp['sourceSha256'] or tsha(out['currentTarget'])!=inp['currentTargetSha256'] or out.get('currentTargetSha256')!=inp['currentTargetSha256']: fail('source/current hash mismatch')
        c=ctx[inp['sourceId']]
        refs=[{'path':r['path'],'line':r['line'],'matchKind':r['matchKind'],'fileSha256':r['fileSha256'],'gitBlob':r['gitBlob'],
          'lineSha256':r['lineSha256'],'excerptSha256':r['excerptSha256']} for r in c['callers']]
        if out.get('callerCount')!=c['exactMatchCount'] or out.get('callerContextSha256')!=c['contextSha256'] or out.get('callerReferences')!=refs: fail('caller reference pin')
        if inp.get('callerless') is not False or inp.get('callerCount')==0: fail('unexpected callerless cell')
        if out.get('proposedTargetSha256')!=tsha(out.get('proposedTarget','')): fail('proposal hash')
        audit=token_audit(inp['source'],out['proposedTarget'],inp.get('sourceProtectedLiterals',[]))
        if audit!=out.get('proposedTokenAudit') or sha(canon(audit))!=out.get('proposedTokenAuditSha256'): fail('proposal token audit')
        if not audit['placeholders']['matches'] or not audit['markup']['matches'] or not audit['numbers']['sourcePreserved'] or audit['protectedLiterals']['missing'] or out.get('tokenChecksPass') is not True: fail('token preservation')
        if out.get('decision')=='accept-current':
            if out['proposedTarget']!=inp['currentTarget']: fail('accepted current target mismatch')
        elif out.get('decision')=='revise':
            if out['proposedTarget']==inp['currentTarget'] or not out.get('issueFlags'): fail('revision mismatch/issue flag')
        else: fail('unknown decision')
        if out.get('confidence') not in ('low','moderate'): fail('confidence level')
        counts[out['decision']]+=1
    prior_source=PREDECESSOR/'prior-active-holds-hash-only.jsonl'; w785_source=PREDECESSOR/'w785-current-window-holds-hash-only.jsonl'
    prior_out=P/'prior-active-holds-hash-only.jsonl'; w785_out=P/'w785-current-window-holds-hash-only.jsonl'
    if prior_source.read_bytes()!=prior_out.read_bytes() or w785_source.read_bytes()!=w785_out.read_bytes(): fail('prior holds not copied byte-for-byte')
    prior=readjl(prior_out); w785=readjl(w785_out)
    if len(prior)!=1012 or len(w785)!=48 or len(prior)+len(w785)!=1060: fail('prior hold lineage counts')
    for row in prior+w785:
        if any(k in row for k in ('source','sourceText','target','currentTarget','proposedTarget','before','after')): fail('hold text disclosure')
    provenance=readj(PREDECESSOR/'active-hold-provenance.json')
    if provenance.get('activeHoldCount')!=1060 or provenance.get('uniqueCells')!=1060 or provenance.get('hashOnly') is not True: fail('prior hold provenance')
    att=readj(P/'input-attestation.json')
    if att.get('outerChecksumListSha256')!=OUTER_SUMS_SHA or (att.get('head'),att.get('tree'))!=(HEAD,TREE): fail('input attestation')
    nextb=im['nextBoundary']
    if s.get('nextBoundary')!=nextb: fail('next boundary')
    if (s.get('cellCount'),s.get('callerBackedCells'),s.get('revisedCells'),s.get('acceptedCurrentCells'),s.get('newCallerlessHolds'),s.get('priorActiveHashOnlyHoldsCopiedAndReattested'),s.get('resultingActiveHashOnlyHolds'))!=(240,240,counts['revise'],counts['accept-current'],0,1060,1060): fail('summary counts')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'cells':len(ledger),'revised':counts['revise'],
      'acceptedCurrent':counts['accept-current'],'priorHolds':len(prior)+len(w785),'newHolds':0,
      'confidenceCounts':s['confidenceCounts'],'issueFlagCellCount':s['issueFlagCellCount'],
      'nextBoundary':nextb,'outerInputChecksumEntries':len(outer),'inputChecksumEntries':len(ins),
      'predecessorChecksumEntries':len(prevs),'outputChecksumEntries':len(outs),
      'outputChecksumListSha256':sha((P/'SHA256SUMS.txt').read_bytes())},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
