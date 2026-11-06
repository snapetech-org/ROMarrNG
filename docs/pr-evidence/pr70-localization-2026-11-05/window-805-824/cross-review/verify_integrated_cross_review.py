from __future__ import annotations
import collections, hashlib, json, re
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=Path('/mnt/disks/scratch/task-scratch')
CFROOT=ROOT/'romarrng-pr70-w805-824-candidate-free-20261105'
CF=CFROOT/'input'
PR=ROOT/'romarrng-pr70-w805-824-primary-review-20261105'
BL=ROOT/'romarrng-pr70-w805-824-independent-blind-20261105'
HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'
TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
WIN='W805-W824'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
CONSENSUS={(809,'ar'),(809,'id'),(818,'ar'),(819,'es')}
PRIMARY_OVERLAP={(806,'ar'),(807,'ar'),(814,'pt-BR')}
BLIND_OVERLAP={(809,'hi')}
PRIMARY_ONLY_ACCEPT={(806,'zh-Hant'),(807,'zh-Hant'),(819,'de'),(819,'ko')}
PRIMARY_ONLY_REJECT={(824,'es')}
BLIND_ONLY_ACCEPT={(812,'hi')}
BLIND_ONLY_REJECT={(816,'zh-Hans'),(816,'zh-Hant'),(818,'zh-Hans'),(818,'zh-Hant')}
LOW_HOLDS={(805,'ar'),(805,'fr'),(806,'fr'),(807,'fr'),(807,'ko'),(820,'de'),(821,'de'),(821,'es'),(821,'fr'),(821,'pt-BR')}

def fail(msg): raise SystemExit('FAIL: '+msg)
def sha(data): return hashlib.sha256(data).hexdigest()
def tsha(text): return sha(text.encode('utf-8'))
def jread(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def jlread(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]

def verify_sums(root,sumfile):
    root=Path(root).resolve(); sumfile=Path(sumfile).resolve()
    listed={}
    for line in sumfile.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        digest,name=line.split(None,1)
        name=name.lstrip('* ').removeprefix('./')
        p=(root/name).resolve()
        if not p.is_relative_to(root) or not p.is_file(): fail('unsafe/missing checksum path '+name)
        if name in listed: fail('duplicate checksum path '+name)
        if sha(p.read_bytes())!=digest: fail('checksum mismatch '+name)
        listed[name]=digest
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.resolve()!=sumfile}
    if set(listed)!=actual: fail('checksum coverage mismatch '+str(root))
    return listed

def verify_input_inventory():
    inventory=jread(OUT/'input-packet-checksums.json')
    expected_roots={'candidate-free':CFROOT,'primary':PR,'independent-blind':BL}
    if {x['name'] for x in inventory['inputs']}!=set(expected_roots): fail('input roots')
    observed={}
    for item in inventory['inputs']:
        name=item['name']; root=expected_roots[name].resolve()
        if Path(item['root']).resolve()!=root: fail('input root pin '+name)
        files=item['files']
        if len(files)!=item['fileCount'] or len({x['path'] for x in files})!=len(files): fail('input inventory count '+name)
        names=set()
        for entry in files:
            rel=entry['path']; p=(root/rel).resolve()
            if not p.is_relative_to(root) or not p.is_file(): fail('input inventory path '+name+'/'+rel)
            data=p.read_bytes()
            if sha(data)!=entry['sha256'] or len(data)!=entry['byteCount']: fail('input inventory digest '+name+'/'+rel)
            names.add(rel); observed[name+'/'+rel]=entry['sha256']
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        if names!=actual: fail('incomplete input inventory '+name)
    return observed

def refs_for(ctx):
    return [{'path':x['path'],'line':x['line'],'matchKind':x['matchKind'],
      'lineSha256':x['lineSha256'],'excerptSha256':x['excerptSha256'],
      'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in ctx['callers']]

def token_audit(source,target,protected):
    ph=re.compile(r'\{[^{}]+\}')
    tag=re.compile(r'</?[A-Za-z][^>]*>')
    num=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
    sp,tp=ph.findall(source),ph.findall(target)
    sm,tm=tag.findall(source),tag.findall(target)
    sn,tn=num.findall(source),num.findall(target)
    missing=[x for x in protected if x not in target]
    return {'sourcePlaceholders':sp,'targetPlaceholders':tp,'placeholdersMatch':collections.Counter(sp)==collections.Counter(tp),
      'sourceMarkup':sm,'targetMarkup':tm,'markupMatches':collections.Counter(sm)==collections.Counter(tm),
      'sourceNumbers':sn,'targetNumbers':tn,'numbersMatch':collections.Counter(sn)==collections.Counter(tn),
      'sourceProtectedLiterals':protected,'missingProtectedLiterals':missing,'protectedLiteralsMatch':not missing}

def selected(k,c,p,b):
    if k in CONSENSUS:
        if p['proposedTarget']!=b['proposedTarget']: fail('consensus target differs '+str(k))
        return 'consensus',p['proposedTarget'],'overlap_identical_consensus'
    if k in PRIMARY_OVERLAP: return 'primary',p['proposedTarget'],'divergent_overlap_primary_selected'
    if k in BLIND_OVERLAP: return 'blind',b['proposedTarget'],'divergent_overlap_blind_selected'
    if k in PRIMARY_ONLY_ACCEPT: return 'primary',p['proposedTarget'],'primary_only_supported'
    if k in PRIMARY_ONLY_REJECT: return 'candidate-current',c['currentTarget'],'primary_only_style_change_rejected'
    if k in BLIND_ONLY_ACCEPT: return 'blind',b['proposedTarget'],'blind_only_supported'
    if k in BLIND_ONLY_REJECT: return 'candidate-current',c['currentTarget'],'blind_only_style_change_rejected'
    if k in LOW_HOLDS: return 'candidate-current',c['currentTarget'],'blind_only_low_confidence_held'
    if p['disposition']!='accept_current' or b['decision']!='accept-current': fail('unadjudicated proposal '+str(k))
    return 'candidate-current',c['currentTarget'],'both_accept_current'

def main():
    out_sums=verify_sums(OUT,OUT/'SHA256SUMS.txt')
    inputs=verify_input_inventory()
    verify_sums(CFROOT,CFROOT/'SHA256SUMS.txt')
    verify_sums(CF,CF/'SHA256SUMS.txt')
    verify_sums(CFROOT/'predecessor',CFROOT/'predecessor'/'SHA256SUMS.txt')
    verify_sums(PR,PR/'SHA256SUMS.txt')
    verify_sums(BL,BL/'SHA256SUMS.txt')
    cfm=jread(CF/'manifest.json'); psummary=jread(PR/'summary.json')
    bmanifest=jread(BL/'manifest.json'); bsummary=jread(BL/'summary.json')
    if (cfm.get('head'),cfm.get('tree'),cfm.get('window'))!=(HEAD,TREE,WIN): fail('candidate-free pin')
    if (psummary.get('head'),psummary.get('tree'),psummary.get('window'))!=(HEAD,TREE,WIN): fail('primary pin')
    if (bmanifest.get('head'),bmanifest.get('tree'),bmanifest.get('window'))!=(HEAD,TREE,WIN): fail('blind pin')
    if cfm.get('proposedTargetsIncluded') is not False or cfm.get('reviewDecisionsIncluded') is not False: fail('candidate-free content')
    if cfm.get('callerBackedCells')!=240 or cfm.get('callerlessHashOnlyCells')!=0: fail('caller coverage input pin')
    summary=jread(OUT/'summary.json')
    if (summary.get('head'),summary.get('tree'),summary.get('window'))!=(HEAD,TREE,WIN): fail('output pin')
    if summary.get('nativeSpeakerApproval') is not False: fail('native-speaker flag')
    if summary.get('cellCount')!=240: fail('summary cell count')

    candidates=jlread(CF/'candidate-free-cells.jsonl')
    contexts=jlread(CF/'source-contexts.jsonl')
    primary=jlread(PR/'primary-review-ledger.jsonl')
    blind=jlread(BL/'blind-review-ledger.jsonl')
    output=jlread(OUT/'integrated-cross-review-ledger.jsonl')
    target_hashes=jlread(OUT/'integrated-target-hashes.jsonl')
    indep_hashes=jlread(OUT/'independent-target-hashes.jsonl')
    if not (len(candidates)==len(primary)==len(blind)==len(output)==len(target_hashes)==len(indep_hashes)==240): fail('240-row coverage')
    if len(contexts)!=20: fail('source context count')
    cm={(x['catalogZeroBasedIndex'],x['locale']):x for x in candidates}
    pm={(x['catalogZeroBasedIndex'],x['locale']):x for x in primary}
    bm={(x['catalogZeroBasedIndex'],x['locale']):x for x in blind}
    cx={x['sourceId']:x for x in contexts}
    if not (len(cm)==len(pm)==len(bm)==240 and len(cx)==20): fail('duplicate row identity')
    expected_order=[(i,loc) for i in range(805,825) for loc in LOCALES]
    actual_order=[(x['catalogZeroBasedIndex'],x['locale']) for x in output]
    if actual_order!=expected_order: fail('integrated row order')
    counts=collections.Counter(); origins=collections.Counter(); resolutions=collections.Counter()
    token_mismatch=collections.Counter(); held_seen=set(); proposal_counts=collections.Counter()
    derived_integrated=[]; derived_blind=[]
    for c,p,b,r,ih,bh in zip(candidates,primary,blind,output,target_hashes,indep_hashes):
        k=(c['catalogZeroBasedIndex'],c['locale']); sourceid=c['sourceId']; context=cx[sourceid]
        if (r.get('sourceId'),r.get('locale'),r.get('position'),r.get('catalogZeroBasedIndex'),r.get('catalogOneBasedPosition'))!=(sourceid,c['locale'],c['position'],c['catalogZeroBasedIndex'],c['catalogOneBasedPosition']):
            fail('cell identity '+str(k))
        if (r.get('source'),r.get('sourceSha256'),r.get('callerContextSha256'),r.get('currentTarget'),r.get('currentTargetSha256'))!=(c['source'],c['sourceSha256'],c['callerContextSha256'],c['currentTarget'],c['currentTargetSha256']):
            fail('source/current hash pin '+str(k))
        if context.get('callerless') is not False or r.get('callerless') is not False: fail('unexpected callerless row '+str(k))
        if context.get('sourceSha256')!=c['sourceSha256'] or context.get('contextSha256')!=c['callerContextSha256']: fail('source caller context hash '+str(k))
        if r.get('callerReferenceCount')!=context['exactMatchCount'] or r.get('callerReferences')!=refs_for(context): fail('caller references '+str(k))
        if r.get('primaryDisposition')!=p.get('disposition') or r.get('blindDecision')!=b.get('decision'): fail('review disposition pins '+str(k))
        if p.get('source')!=c.get('source') or p.get('currentTarget')!=c.get('currentTarget'): fail('primary input text '+str(k))
        if b.get('source')!=c.get('source') or b.get('currentTarget')!=c.get('currentTarget'): fail('blind input text '+str(k))
        if (r['primaryDisposition'] in ('correction','refinement')):
            if r.get('primaryProposedTarget')!=p.get('proposedTarget') or r.get('primaryProposedTargetSha256')!=p.get('proposedTargetSha256') or tsha(r['primaryProposedTarget'])!=p['proposedTargetSha256']:
                fail('primary proposal exact/hash '+str(k))
            proposal_counts['primary']+=1
        elif any(field in r for field in ('primaryProposedTarget','primaryProposedTargetSha256')):
            fail('unexpected primary proposal '+str(k))
        if r['blindDecision']=='revise':
            if r.get('blindProposedTarget')!=b.get('proposedTarget') or r.get('blindProposedTargetSha256')!=b.get('proposedTargetSha256') or r['blindTarget']!=b['proposedTarget']:
                fail('blind proposal exact/hash '+str(k))
            proposal_counts['blind']+=1
        elif any(field in r for field in ('blindProposedTarget','blindProposedTargetSha256')):
            fail('unexpected blind proposal '+str(k))
        expected_blind=b['proposedTarget'] if b['decision']=='revise' else c['currentTarget']
        expected_blind_hash=b['proposedTargetSha256'] if b['decision']=='revise' else c['currentTargetSha256']
        if r.get('blindTarget')!=expected_blind or r.get('blindTargetSha256')!=expected_blind_hash or tsha(expected_blind)!=expected_blind_hash:
            fail('blind target pin '+str(k))
        origin,target,resolution=selected(k,c,p,b)
        if (r.get('integratedTargetSource'),r.get('integratedTarget'),r.get('proposalResolution'))!=(origin,target,resolution):
            fail('integrated adjudication '+str(k))
        changed=target!=c['currentTarget']
        if r.get('integratedDecision')!=('adopt_proposal' if changed else 'retain_current'): fail('integrated decision '+str(k))
        if r.get('integratedTargetSha256')!=tsha(target): fail('integrated target hash '+str(k))
        hold=k in LOW_HOLDS
        if r.get('languageHold') is not hold or r.get('confidence')!=('low' if hold else 'moderate'): fail('language hold/confidence '+str(k))
        if hold:
            if changed or b['confidence']!='low' or r.get('languageHoldReason')!=r.get('rationale'): fail('held language target/status '+str(k))
            held_seen.add(k)
        audit=token_audit(c['source'],target,c['sourceProtectedLiterals'])
        if r.get('tokenAudit')!=audit: fail('token audit data '+str(k))
        for field,category in [('placeholdersMatch','placeholders'),('markupMatches','markup'),('numbersMatch','numeric'),('protectedLiteralsMatch','protectedLiterals')]:
            if not audit[field]: token_mismatch[category]+=1
        if not all(audit[x] for x in ('placeholdersMatch','markupMatches','numbersMatch','protectedLiteralsMatch')):
            fail('token or protected-literal mismatch '+str(k))
        counts[r['integratedDecision']]+=1; origins[origin]+=1; resolutions[resolution]+=1
        if r['primaryDisposition'] in ('correction','refinement') and r['blindDecision']=='revise': proposal_counts['overlap']+=1
        elif r['primaryDisposition'] in ('correction','refinement'): proposal_counts['primaryOnly']+=1
        elif r['blindDecision']=='revise': proposal_counts['blindOnly']+=1
        derived_integrated.append({'position':c['position'],'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],
          'sourceId':sourceid,'locale':c['locale'],'sourceSha256':c['sourceSha256'],
          'currentTargetSha256':c['currentTargetSha256'],'integratedTargetSha256':tsha(target),
          'integratedDecision':r['integratedDecision'],'integratedTargetSource':origin,
          'callerless':False,'independentBlindTargetSha256':expected_blind_hash})
        derived_blind.append({'blindTargetSha256':expected_blind_hash,'currentTargetSha256':c['currentTargetSha256'],
          'decision':b['decision'],'locale':c['locale'],'position':c['position'],
          'proposedTargetSha256':b.get('proposedTargetSha256') if b['decision']=='revise' else None,
          'sourceId':sourceid,'sourceSha256':c['sourceSha256'],'window':WIN})
        if ih.get('independentBlindTargetSha256')!=expected_blind_hash: fail('independent blind hash in target ledger '+str(k))
    if counts!=collections.Counter({'adopt_proposal':13,'retain_current':227}): fail('integrated actions '+str(counts))
    if origins!=collections.Counter({'candidate-current':227,'primary':7,'blind':2,'consensus':4}): fail('integrated origins '+str(origins))
    if proposal_counts!=collections.Counter({'primary':13,'blind':23,'overlap':8,'primaryOnly':5,'blindOnly':15}): fail('proposal counts '+str(proposal_counts))
    if held_seen!=LOW_HOLDS: fail('unresolved low-confidence cell set')
    if target_hashes!=derived_integrated: fail('integrated target hash ledger')
    if indep_hashes!=derived_blind: fail('independent target hashes')

    # Verify predecessor hold lineage remains byte-identical and text-free.
    prior_src=CFROOT/'predecessor/prior-active-holds-hash-only.jsonl'
    window_src=CFROOT/'predecessor/w785-current-window-holds-hash-only.jsonl'
    if (OUT/'prior-active-holds-hash-only.jsonl').read_bytes()!=prior_src.read_bytes(): fail('prior hold byte copy')
    if (OUT/'current-window-holds-hash-only.jsonl').read_bytes()!=window_src.read_bytes(): fail('W785 hold byte copy')
    if prior_src.read_bytes()!=(PR/'predecessor/prior-active-holds-hash-only.jsonl').read_bytes() or prior_src.read_bytes()!=(BL/'prior-active-holds-hash-only.jsonl').read_bytes():
        fail('prior holds differ across packets')
    if window_src.read_bytes()!=(PR/'predecessor/w785-current-window-holds-hash-only.jsonl').read_bytes() or window_src.read_bytes()!=(BL/'w785-current-window-holds-hash-only.jsonl').read_bytes():
        fail('W785 holds differ across packets')
    prior=jlread(OUT/'prior-active-holds-hash-only.jsonl'); previous_window=jlread(OUT/'current-window-holds-hash-only.jsonl')
    if len(prior)!=1012 or len(previous_window)!=48: fail('predecessor hold counts')
    for row in prior+previous_window:
        if row.get('textOmitted') is not True or any(k in row for k in ('source','sourceText','currentTarget','target','targetText','blindTarget','proposedTarget')):
            fail('hash-only predecessor hold text leak')
    unresolved=jlread(OUT/'unresolved-language-holds.jsonl')
    if {(x['catalogZeroBasedIndex'],x['locale']) for x in unresolved}!=LOW_HOLDS or len(unresolved)!=10:
        fail('unresolved language hold ledger')
    for row in unresolved:
        k=(row['catalogZeroBasedIndex'],row['locale'])
        ledger=next(x for x in output if (x['catalogZeroBasedIndex'],x['locale'])==k)
        if (row['currentTarget'],row['heldProposal'],row['integratedTargetSha256'])!=(ledger['currentTarget'],ledger['blindProposedTarget'],ledger['integratedTargetSha256']):
            fail('unresolved held proposal exact target '+str(k))
    boundary=cfm['nextBoundary']
    if summary.get('nextBoundary')!=boundary or psummary.get('nextBoundary')!=boundary or bsummary.get('nextBoundary')!=boundary:
        fail('next boundary')
    for field,want in [('primaryProposalCells',13),('independentBlindProposalCells',23),('proposalOverlapCells',8),
       ('primaryOnlyProposalCells',5),('blindOnlyProposalCells',15),('uniqueProposalCells',28),
       ('identicalOverlapCells',4),('divergentOverlapCellsResolvedByCrossReview',4),
       ('priorActiveHashOnlyHoldsCopiedByteForByte',1012),('currentW785HashOnlyHoldsCopiedByteForByte',48),
       ('resultingActiveHashOnlyHolds',1060),('newCallerlessHolds',0)]:
        if summary.get(field)!=want: fail('summary '+field)
    print(json.dumps({'result':'PASS','head':HEAD,'tree':TREE,'window':WIN,'cells':240,
      'callerBackedCells':240,'adoptedChanges':counts['adopt_proposal'],'retainedCurrent':counts['retain_current'],
      'lowConfidenceLanguageHolds':len(held_seen),'primaryProposals':proposal_counts['primary'],
      'blindProposals':proposal_counts['blind'],'overlap':proposal_counts['overlap'],
      'primaryOnly':proposal_counts['primaryOnly'],'blindOnly':proposal_counts['blindOnly'],
      'integratedOrigins':dict(sorted(origins.items())),'priorActiveHolds':len(prior),
      'priorW785CurrentHolds':len(previous_window),'resultingActiveHolds':len(prior)+len(previous_window),
      'tokenMismatches':dict(token_mismatch),'inputFileChecksumEntries':len(inputs),
      'outputChecksumEntries':len(out_sums),'outputChecksumListSha256':sha((OUT/'SHA256SUMS.txt').read_bytes()),
      'nextBoundary':boundary,'nativeSpeakerApproval':False},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
