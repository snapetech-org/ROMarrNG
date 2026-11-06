#!/usr/bin/env python3
"""Verify the sealed ROMarrNG W785-W804 integrated cross-review packet."""
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CF=ROOT.parent/'candidate-free'
PR=ROOT.parent/'primary-review'
BL=ROOT.parent/'blind-review'
HEAD='bbbf84d0d83138a23143f6aa6075415ebcb36d3e'
TREE='fbf9ada4b4fd43a288ce498b24990312f0c32f22'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PH=re.compile(r'\{[^{}]+\}')
TAG=re.compile(r'</?[A-Za-z][^>]*>')
NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')

def sha(x):
    if isinstance(x,str): x=x.encode('utf-8')
    return hashlib.sha256(x).hexdigest()
def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def rj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def need(cond,msg):
    if not cond: raise ValueError(msg)

def verify_sum_list(root, sum_path):
    root=Path(root).resolve(); listed={}
    for line in Path(sum_path).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,name=line.split(None,1)
        name=name.lstrip('* ').removeprefix('./')
        p=(root/name).resolve()
        need(p.is_relative_to(root) and p.is_file(),'checksum path '+name)
        need(sha(p.read_bytes())==digest,'checksum mismatch '+name)
        need(name not in listed,'duplicate checksum '+name)
        listed[name]=digest
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.resolve()!=Path(sum_path).resolve()}
    need(set(listed)==actual,'checksum coverage '+str(root))
    return listed

def token_audit(source,target,protected):
    sp,tp=PH.findall(source),PH.findall(target)
    sm,tm=TAG.findall(source),TAG.findall(target)
    sn,tn=NUM.findall(source),NUM.findall(target)
    missing=[x for x in protected if x not in target]
    return {
      'sourcePlaceholders':sp,'targetPlaceholders':tp,'placeholdersMatch':collections.Counter(sp)==collections.Counter(tp),
      'sourceMarkup':sm,'targetMarkup':tm,'markupMatches':collections.Counter(sm)==collections.Counter(tm),
      'sourceNumbers':sn,'targetNumbers':tn,'numbersMatch':collections.Counter(sn)==collections.Counter(tn),
      'sourceProtectedLiterals':protected,'missingProtectedLiterals':missing,'protectedLiteralsMatch':not missing,
    }

def main():
    # Validate every byte of all three input packets and their own checksum lists.
    ix=rj(ROOT/'input-packet-checksums.json')
    need(len(ix['inputs'])==3,'input packet count')
    for item in ix['inputs']:
        base=(ROOT/item['root']).resolve(); entries=item['files']
        need(len(entries)==item['fileCount'],'input file count '+item['name'])
        need(len({x['path'] for x in entries})==len(entries),'duplicate input path '+item['name'])
        for x in entries:
            p=(base/x['path']).resolve()
            need(p.is_relative_to(base) and p.is_file(),'input path '+item['name']+'/'+x['path'])
            need(sha(p.read_bytes())==x['sha256'] and p.stat().st_size==x['byteCount'],'input hash '+item['name']+'/'+x['path'])
    verify_sum_list(CF,CF/'SHA256SUMS.txt')
    verify_sum_list(CF/'input',CF/'input'/'SHA256SUMS.txt')
    verify_sum_list(PR,PR/'SHA256SUMS.txt')
    verify_sum_list(BL,BL/'SHA256SUMS.txt')
    # Validate this output packet's checksums and exact coverage.
    verify_sum_list(ROOT,ROOT/'SHA256SUMS.txt')
    summary=rj(ROOT/'summary.json')
    need((summary['head'],summary['tree'],summary['window'],summary['cellCount'],summary['localeCount'])==(HEAD,TREE,'W785-W804',240,12),'summary pin/count')
    need(summary['nativeSpeakerApproval'] is False,'native approval flag')
    cfin=CF/'input'; pledger=PR/'primary-review-ledger.jsonl'; bledger=BL/'blind-review-ledger.jsonl'
    candidates=rjl(cfin/'candidate-free-cells.jsonl')
    p_rows=rjl(pledger); b_rows=rjl(bledger); out_rows=rjl(ROOT/'integrated-cross-review-ledger.jsonl')
    need((len(candidates),len(p_rows),len(b_rows),len(out_rows))==(240,240,240,240),'row counts')
    cmap={(x['sourceId'],x['locale']):x for x in candidates}
    pmap={(x['sourceId'],x['locale']):x for x in p_rows}
    bmap={(x['sourceId'],x['locale']):x for x in b_rows}
    need(all(len(m)==240 for m in (cmap,pmap,bmap)),'duplicate input row')
    ctx={x['sourceId']:x for x in rjl(cfin/'source-contexts.jsonl')}
    need([(x['catalogZeroBasedIndex'],x['locale']) for x in candidates]==[(i,l) for i in range(785,805) for l in LOCALES],'candidate row order')
    origins=collections.Counter(); proposals=collections.Counter(); token_mismatch=collections.Counter()
    seen=set(); integrated_hashes=[]
    conflicts={
      ('ui.or-as-a-frontend-s-own-format.3a0f4bbdc6','vi'):'primary',
      ('ui.pin-from-your-moonlight-client.1a127b3ae9','ko'):'primary',
      ('ui.pairing.76dfd9f9a3','hi'):'blind',
    }
    for out in out_rows:
        key=(out['sourceId'],out['locale'])
        need(key in cmap and key not in seen,'integrated row missing/duplicate '+str(key)); seen.add(key)
        base,p,b=cmap[key],pmap[key],bmap[key]
        need(out['position']==base['position'] and out['catalogZeroBasedIndex']==base['catalogZeroBasedIndex'] and out['catalogOneBasedPosition']==base['catalogOneBasedPosition'],'row position '+str(key))
        need((out['sourceSha256'],out['callerContextSha256'],out['currentTargetSha256'])==(base['sourceSha256'],base['callerContextSha256'],base['currentTargetSha256']),'source/current/context hash '+str(key))
        need(out['primaryDisposition']==p['disposition'] and out['blindDecision']==b['decision'],'source review decisions '+str(key))
        pc=p['disposition'] in ('correction','refinement'); br=b['decision']=='revise'
        if base['callerless']:
            origins['hold_hash_only']+=1
            need(out['integratedDecision']=='hold_hash_only' and out['integratedTargetSource']=='hash_only_hold' and out.get('callerless') is True and out.get('textOmitted') is True,'hold disposition '+str(key))
            need(not any(k in out for k in ('source','currentTarget','blindTarget','integratedTarget','primaryProposedTarget','blindProposedTarget')),'hold text leak '+str(key))
            need(out['integratedTargetSha256']==base['currentTargetSha256'],'hold target hash '+str(key))
            need(p['disposition']=='hold_hash_only' and b['decision']=='hold-hash-only','upstream hold mismatch '+str(key))
            need(not any(k in base for k in ('source','currentTarget')),'candidate-free hold text '+str(key))
            integrated_hashes.append({'position':out['position'],'catalogZeroBasedIndex':out['catalogZeroBasedIndex'],'sourceId':out['sourceId'],'locale':out['locale'],'sourceSha256':out['sourceSha256'],'currentTargetSha256':out['currentTargetSha256'],'integratedTargetSha256':out['integratedTargetSha256'],'integratedDecision':out['integratedDecision'],'integratedTargetSource':out['integratedTargetSource'],'callerless':True})
            continue
        need(out.get('callerless') is False and out['integratedDecision'] in ('retain_current','adopt_proposal'),'caller-backed status '+str(key))
        need(out['source']==base['source'] and out['currentTarget']==base['currentTarget'] and out['blindTarget']==b['blindTarget'],'caller-backed input text '+str(key))
        need(out['blindTargetSha256']==b['blindTargetSha256'] and sha(out['blindTarget'])==b['blindTargetSha256'],'blind target hash '+str(key))
        expected_refs=[{'path':c['path'],'line':c['line'],'matchKind':c['matchKind'],'lineSha256':c['lineSha256'],'fileSha256':c['fileSha256'],'gitBlob':c['gitBlob']} for c in ctx[key[0]]['callers']]
        need(out['callerReferences']==expected_refs and out['callerReferenceCount']==ctx[key[0]]['exactMatchCount'],'caller evidence '+str(key))
        if pc:
            need(out.get('primaryProposedTarget')==p['proposedTarget'] and out.get('primaryProposedTargetSha256')==p['proposedTargetSha256'],'primary proposal evidence '+str(key))
            need(sha(out['primaryProposedTarget'])==p['proposedTargetSha256'],'primary proposal hash '+str(key))
        else:
            need('primaryProposedTarget' not in out,'spurious primary proposal '+str(key))
        if br:
            need(out.get('blindProposedTarget')==b['blindTarget'] and out.get('blindProposedTargetSha256')==b['blindTargetSha256'],'blind proposal evidence '+str(key))
        else:
            need('blindProposedTarget' not in out,'spurious blind proposal '+str(key))
        if pc and br:
            proposals['overlap']+=1
            if p['proposedTarget']==b['blindTarget']:
                proposals['identicalOverlap']+=1; origin='consensus'; expected=p['proposedTarget']
            else:
                proposals['divergentOverlap']+=1; origin=conflicts.get(key); need(origin in ('primary','blind'),'unresolved divergent overlap '+str(key))
                expected=p['proposedTarget'] if origin=='primary' else b['blindTarget']
        elif pc:
            proposals['primaryOnly']+=1; origin='primary'; expected=p['proposedTarget']
        elif br:
            proposals['blindOnly']+=1; origin='blind'; expected=b['blindTarget']
        else:
            origin='candidate-current'; expected=base['currentTarget']
        need(out['integratedTargetSource']==origin and out['integratedTarget']==expected,'integrated proposal selection '+str(key))
        need(out['integratedTargetSha256']==sha(expected),'integrated target hash '+str(key))
        need(out['integratedDecision']==('retain_current' if origin=='candidate-current' else 'adopt_proposal'),'integrated decision '+str(key))
        origins[origin]+=1
        audit=token_audit(base['source'],expected,base['sourceProtectedLiterals'])
        need(out['tokenAudit']==audit,'token audit mismatch '+str(key))
        for field,category in [('placeholdersMatch','placeholder'),('markupMatches','markup'),('numbersMatch','numeric'),('protectedLiteralsMatch','protectedLiteral')]:
            token_mismatch[category]+=not audit[field]
        need(not any(not audit[k] for k in ('placeholdersMatch','markupMatches','numbersMatch','protectedLiteralsMatch')),'integrated token mismatch '+str(key))
        integrated_hashes.append({'position':out['position'],'catalogZeroBasedIndex':out['catalogZeroBasedIndex'],'sourceId':out['sourceId'],'locale':out['locale'],'sourceSha256':out['sourceSha256'],'currentTargetSha256':out['currentTargetSha256'],'integratedTargetSha256':out['integratedTargetSha256'],'integratedDecision':out['integratedDecision'],'integratedTargetSource':out['integratedTargetSource'],'callerless':False,'independentBlindTargetSha256':out['blindTargetSha256']})
    need(len(seen)==240,'complete integrated coverage')
    need(proposals==collections.Counter({'overlap':13,'primaryOnly':3,'blindOnly':15,'identicalOverlap':10,'divergentOverlap':3}),'proposal reconciliation counts '+str(proposals))
    need(origins==collections.Counter({'blind':16,'candidate-current':161,'consensus':10,'hold_hash_only':48,'primary':5}),'integrated origins '+str(origins))
    # Independent hashes and hash-only ledgers are preserved exactly.
    need((ROOT/'independent-target-hashes.jsonl').read_bytes()==(BL/'independent-target-hashes.jsonl').read_bytes(),'independent target hash ledger copy')
    need((ROOT/'current-window-holds-hash-only.jsonl').read_bytes()==(BL/'current-window-holds-hash-only.jsonl').read_bytes(),'current hold ledger copy')
    need((ROOT/'prior-active-holds-hash-only.jsonl').read_bytes()==(cfin/'prior-active-holds-hash-only.jsonl').read_bytes(),'prior hold ledger copy')
    current_holds=rjl(ROOT/'current-window-holds-hash-only.jsonl')
    need(len(current_holds)==48,'current hold row count')
    for h in current_holds:
        need(not any(k in h for k in ('source','sourceText','currentTarget','target','targetText','blindTarget','proposedTarget')),'current hold text leak')
    prior=rjl(ROOT/'prior-active-holds-hash-only.jsonl')
    need(len(prior)==1012,'prior active hold count')
    for h in prior:
        need(not any(k in h for k in ('source','sourceText','currentTarget','target','targetText','blindTarget','proposedTarget')),'prior hold text leak')
    ih=rjl(ROOT/'integrated-target-hashes.jsonl')
    need(ih==integrated_hashes and len(ih)==240,'integrated target hash ledger')
    # Input-output count claims match.
    summary=rj(ROOT/'summary.json')
    need(summary['primaryProposalCells']==16 and summary['independentBlindProposalCells']==28 and summary['proposalOverlapCells']==13 and summary['primaryOnlyProposalCells']==3 and summary['blindOnlyProposalCells']==15 and summary['uniqueProposalCells']==31,'summary proposal counts')
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'window':'W785-W804','cells':240,'callerBackedCells':192,'callerlessHashOnlyCells':48,'primaryProposals':16,'blindProposals':28,'overlap':13,'primaryOnly':3,'blindOnly':15,'uniqueProposals':31,'integratedOrigins':dict(sorted(origins.items())),'priorActiveHolds':1012,'resultingActiveHolds':1060,'tokenMismatches':dict(token_mismatch),'inputAndOutputChecksums':'PASS','callerlessRowsTextFree':True,'productWorktreeAccessed':False},ensure_ascii=False,indent=2))
if __name__=='__main__':
    main()
