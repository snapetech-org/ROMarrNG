import json, pathlib, hashlib, shutil, collections, re
OUT=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path('/mnt/disks/scratch/task-scratch')
CFROOT=ROOT/'romarrng-pr70-w805-824-candidate-free-20261105'
CF=CFROOT/'input'
PR=ROOT/'romarrng-pr70-w805-824-primary-review-20261105'
BL=ROOT/'romarrng-pr70-w805-824-independent-blind-20261105'
HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'
TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
WIN='W805-W824'

def jread(p): return json.loads(p.read_text(encoding='utf-8'))
def jlread(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(data): return hashlib.sha256(data).hexdigest()
def tsha(text): return sha(text.encode('utf-8'))
def writej(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def writejl(name,rows): (OUT/name).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in rows),encoding='utf-8')

# Cell keys are zero-based catalog index plus locale.
CONSENSUS={(809,'ar'),(809,'id'),(818,'ar'),(819,'es')}
PRIMARY_OVERLAP={(806,'ar'),(807,'ar'),(814,'pt-BR')}
BLIND_OVERLAP={(809,'hi')}
PRIMARY_ONLY_ACCEPT={(806,'zh-Hant'),(807,'zh-Hant'),(819,'de'),(819,'ko')}
PRIMARY_ONLY_REJECT={(824,'es')}
BLIND_ONLY_ACCEPT={(812,'hi')}
BLIND_ONLY_REJECT={(816,'zh-Hans'),(816,'zh-Hant'),(818,'zh-Hans'),(818,'zh-Hant')}
LOW_LANGUAGE_HOLDS={
 (805,'ar'):'The proposed Arabic loanword for patch is low confidence. Current wording is consistent with the cross-reviewed modifications wording for the catalogue and page; retain it pending native terminology review.',
 (805,'fr'):'The French choice between correctifs and the borrowed ROM-patch term patches is uncertain in this catalogue context; retain the current target pending native review.',
 (806,'fr'):'The French choice between correctifs and Patchs for a ROM-patch navigation label is uncertain; retain the current target pending native review.',
 (807,'fr'):'The French choice between correctifs and Patchs for the ROM-patch page heading is uncertain; retain the current target pending native review.',
 (807,'ko'):'The Korean wording for ROM hacks (current 핵 versus proposed 개조) is uncertain in this product context; retain the current target pending native review.',
 (820,'de'):'The onboarding caller supports both Route and Weg for this setup path; the low-confidence alternative is held pending native review.',
 (821,'de'):'The caller indicates a planned DAT-backed set, but the low-confidence expansion to a game collection is not clearly preferable to the current concise Set.',
 (821,'es'):'The caller indicates a planned DAT-backed set, but the low-confidence expansion to a game collection is not clearly preferable to the current concise conjunto.',
 (821,'fr'):'The caller indicates a planned DAT-backed set, but the low-confidence expansion to a game collection is not clearly preferable to the current concise ensemble.',
 (821,'pt-BR'):'The caller indicates a planned DAT-backed set, but the low-confidence expansion to a game collection is not clearly preferable to the current concise conjunto.',
}
def caller_refs(ctx):
    return [{'path':x['path'],'line':x['line'],'matchKind':x['matchKind'],
      'lineSha256':x['lineSha256'],'excerptSha256':x['excerptSha256'],'fileSha256':x['fileSha256'],'gitBlob':x['gitBlob']} for x in ctx['callers']]

def token_audit(source,target,protected):
    PH=re.compile(r'\{[^{}]+\}')
    TAG=re.compile(r'</?[A-Za-z][^>]*>')
    NUM=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
    sp,tp=PH.findall(source),PH.findall(target)
    sm,tm=TAG.findall(source),TAG.findall(target)
    sn,tn=NUM.findall(source),NUM.findall(target)
    missing=[x for x in protected if x not in target]
    return {'sourcePlaceholders':sp,'targetPlaceholders':tp,'placeholdersMatch':collections.Counter(sp)==collections.Counter(tp),
      'sourceMarkup':sm,'targetMarkup':tm,'markupMatches':collections.Counter(sm)==collections.Counter(tm),
      'sourceNumbers':sn,'targetNumbers':tn,'numbersMatch':collections.Counter(sn)==collections.Counter(tn),
      'sourceProtectedLiterals':protected,'missingProtectedLiterals':missing,'protectedLiteralsMatch':not missing}

def verify_input_packets():
    inputs=[('candidate-free',CFROOT),('primary',PR),('independent-blind',BL)]
    all_inputs=[]
    for name,root in inputs:
        files=[]
        for f in sorted(p for p in root.rglob('*') if p.is_file()):
            files.append({'path':f.relative_to(root).as_posix(),'sha256':sha(f.read_bytes()),'byteCount':f.stat().st_size})
        all_inputs.append({'name':name,'root':str(root),'fileCount':len(files),'files':files})
    writej('input-packet-checksums.json',{'inputs':all_inputs})
    return all_inputs

candidates=jlread(CF/'candidate-free-cells.jsonl')
contexts=jlread(CF/'source-contexts.jsonl')
primary=jlread(PR/'primary-review-ledger.jsonl')
blind=jlread(BL/'blind-review-ledger.jsonl')
assert len(candidates)==len(primary)==len(blind)==240
assert len(contexts)==20
cm={(x['catalogZeroBasedIndex'],x['locale']):x for x in candidates}
pm={(x['catalogZeroBasedIndex'],x['locale']):x for x in primary}
bm={(x['catalogZeroBasedIndex'],x['locale']):x for x in blind}
ctx={x['sourceId']:x for x in contexts}
assert len(cm)==len(pm)==len(bm)==240 and len(ctx)==20
assert all(x['head']==HEAD for x in contexts) and all((x['head'],x['tree'])==(HEAD,TREE) for x in blind)
assert [(x['catalogZeroBasedIndex'],x['locale']) for x in candidates]==[(i,l) for i in range(805,825) for l in LOCALES]
assert all(x['callerless'] is False for x in candidates)
assert sum(x['disposition'] in ('correction','refinement') for x in primary)==13
assert sum(x['decision']=='revise' for x in blind)==23
assert sum(x['confidence']=='low' and x['decision']=='revise' for x in blind)==13

specific={
 (806,'ar'):'The source identifies a page for translation, hack, and improvement projects. Choose the primary wording التعديلات rather than the low-confidence borrowed loanword; the long heading confirms modifications are the category being described.',
 (807,'ar'):'The page heading explicitly includes translations, hacks, and improvements, so التعديلات preserves the broader category better than التصحيحات; hold the low-confidence borrowed alternative.',
 (806,'zh-Hant'):'The caller is the Library navigation item for ROM translation/hack projects. 補丁 names the software/game patch item more directly than 修補.',
 (807,'zh-Hant'):'The caller names the ROM-patch page and its translation, hack, and improvement projects. 補丁 is the software/game patch noun; retain the other category terms.',
 (809,'ar'):'The caller checks l.path_exists; المسار غير موجود correctly describes a filesystem path that does not exist.',
 (809,'hi'):'The caller checks l.path_exists; choose the blind target पथ मौजूद नहीं है because it states that the filesystem path does not exist.',
 (809,'id'):'The caller checks l.path_exists; Jalur tidak ditemukan uses the filesystem path term and accurately describes the missing path.',
 (812,'hi'):'The action toggles between Pause and Resume in the queue. ठहराएँ describes pausing the queue instead of stopping it.',
 (814,'pt-BR'):'The source appears as explanatory bold copy. Adopt the primary wording without quotation marks; por si só expresses by itself naturally in Brazilian Portuguese.',
 (818,'ar'):'The source is a short instruction above type choices. اختر نوعًا corrects the imperative spelling and indefinite object form.',
 (819,'de'):'The exact caller uses this copy beside setup instructions; the adjacent route instruction uses formal Sie, so choose formal Wählen Sie to keep this prompt consistent.',
 (819,'es'):'The caller substitutes translated Genre, Franchise, or Company labels with different grammatical genders. Removing the fixed masculine article avoids an agreement error.',
 (819,'ko'):'The caller substitutes genre, franchise, or company labels with different object-particle endings. Omitting 을 avoids the mismatch.',
}
generic_current='Both reviewers retain the current wording, and the supplied source/caller context shows no material semantic or technical defect.'
generic_style='The source and caller support the current meaning; the proposed alternative is stylistic without a demonstrated semantic correction, so retain the current target.'

rows=[]; integrated_hashes=[]; independent_hashes=[]
counts=collections.Counter(); origins=collections.Counter(); resolution_counts=collections.Counter()
held=[]
for c in candidates:
    k=(c['catalogZeroBasedIndex'],c['locale'])
    p,b=pm[k],bm[k]
    context=ctx[c['sourceId']]
    assert c['sourceId']==p['sourceId']==b['sourceId']==context['sourceId']
    assert c['source']==p['source']==b['source']==context['source']
    assert (c['sourceSha256'],c['callerContextSha256'])==(p['sourceSha256'],p['callerContextSha256'])
    assert (c['sourceSha256'],c['callerContextSha256'])==(b['sourceSha256'],b['callerContextSha256'])
    assert c['currentTarget']==p['currentTarget']==b['currentTarget']
    assert c['currentTargetSha256']==p['currentTargetSha256']==b['currentTargetSha256']
    assert context['callerless'] is False
    refs=caller_refs(context)
    assert refs==p['callerReferences']==b['callerReferences']
    assert c['literalCallerCount']>0 and context['exactMatchCount']>0
    blind_target=b['proposedTarget'] if b['decision']=='revise' else c['currentTarget']
    blind_hash=b['proposedTargetSha256'] if b['decision']=='revise' else c['currentTargetSha256']
    assert tsha(blind_target)==blind_hash

    if k in CONSENSUS:
        assert p['disposition'] in ('correction','refinement') and b['decision']=='revise'
        assert p['proposedTarget']==b['proposedTarget']
        origin='consensus'; target=p['proposedTarget']; resolution='overlap_identical_consensus'
        rationale='Primary and blind reviewers select the same wording; the exact source and caller support the correction.'
    elif k in PRIMARY_OVERLAP:
        assert p['disposition'] in ('correction','refinement') and b['decision']=='revise'
        origin='primary'; target=p['proposedTarget']; resolution='divergent_overlap_primary_selected'
        rationale=specific[k]
    elif k in BLIND_OVERLAP:
        assert p['disposition'] in ('correction','refinement') and b['decision']=='revise'
        origin='blind'; target=b['proposedTarget']; resolution='divergent_overlap_blind_selected'
        rationale=specific[k]
    elif k in PRIMARY_ONLY_ACCEPT:
        assert p['disposition'] in ('correction','refinement') and b['decision']=='accept-current'
        origin='primary'; target=p['proposedTarget']; resolution='primary_only_supported'
        rationale=specific[k]
    elif k in PRIMARY_ONLY_REJECT:
        assert p['disposition'] in ('correction','refinement') and b['decision']=='accept-current'
        origin='candidate-current'; target=c['currentTarget']; resolution='primary_only_style_change_rejected'
        rationale='The current Spanish heading already identifies platform folder names. The primary alternative improves phrasing but does not correct a material meaning error.'
    elif k in BLIND_ONLY_ACCEPT:
        assert p['disposition']=='accept_current' and b['decision']=='revise'
        origin='blind'; target=b['proposedTarget']; resolution='blind_only_supported'
        rationale=specific[k]
    elif k in BLIND_ONLY_REJECT:
        assert p['disposition']=='accept_current' and b['decision']=='revise'
        origin='candidate-current'; target=c['currentTarget']; resolution='blind_only_style_change_rejected'
        rationale='The current translation conveys the field/instruction meaning; the blind wording is an optional tone or phrasing change without a material defect.'
    elif k in LOW_LANGUAGE_HOLDS:
        assert p['disposition']=='accept_current' and b['decision']=='revise' and b['confidence']=='low'
        origin='candidate-current'; target=c['currentTarget']; resolution='blind_only_low_confidence_held'
        rationale=LOW_LANGUAGE_HOLDS[k]
    else:
        assert p['disposition']=='accept_current' and b['decision']=='accept-current'
        origin='candidate-current'; target=c['currentTarget']; resolution='both_accept_current'
        rationale=generic_current

    # Explicitly reconcile the entire proposal inventory.
    if p['disposition'] in ('correction','refinement'):
        primary_proposal=p['proposedTarget']; primary_hash=p['proposedTargetSha256']
    else:
        primary_proposal=None; primary_hash=None
    if b['decision']=='revise':
        blind_proposal=b['proposedTarget']; blind_proposal_hash=b['proposedTargetSha256']
    else:
        blind_proposal=None; blind_proposal_hash=None

    audit=token_audit(c['source'],target,c['sourceProtectedLiterals'])
    assert audit['placeholdersMatch'] and audit['markupMatches'] and audit['numbersMatch'] and audit['protectedLiteralsMatch'],(k,audit)
    changed=target!=c['currentTarget']
    row={
      'position':c['position'],'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],
      'catalogOneBasedPosition':c['catalogOneBasedPosition'],'window':WIN,
      'sourceId':c['sourceId'],'locale':c['locale'],'source':c['source'],'sourceSha256':c['sourceSha256'],
      'callerContextSha256':c['callerContextSha256'],'callerReferenceCount':context['exactMatchCount'],
      'callerReferences':refs,'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],
      'primaryDisposition':p['disposition'],'blindDecision':b['decision'],
      'blindTarget':blind_target,'blindTargetSha256':blind_hash,
      'integratedTarget':target,'integratedTargetSha256':tsha(target),
      'integratedDecision':'adopt_proposal' if changed else 'retain_current',
      'integratedTargetSource':origin,'proposalResolution':resolution,'rationale':rationale,
      'tokenAudit':audit,'nativeSpeakerApproval':False,'confidence':'low' if k in LOW_LANGUAGE_HOLDS else 'moderate',
      'callerless':False,'languageHold':k in LOW_LANGUAGE_HOLDS,
    }
    if primary_proposal is not None:
        row['primaryProposedTarget']=primary_proposal
        row['primaryProposedTargetSha256']=primary_hash
    if blind_proposal is not None:
        row['blindProposedTarget']=blind_proposal
        row['blindProposedTargetSha256']=blind_proposal_hash
    if k in LOW_LANGUAGE_HOLDS:
        row['languageHoldReason']=LOW_LANGUAGE_HOLDS[k]
        held.append({'position':c['position'],'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],
          'catalogOneBasedPosition':c['catalogOneBasedPosition'],'sourceId':c['sourceId'],'locale':c['locale'],
          'source':c['source'],'sourceSha256':c['sourceSha256'],'callerContextSha256':c['callerContextSha256'],
          'currentTarget':c['currentTarget'],'currentTargetSha256':c['currentTargetSha256'],
          'heldProposal':b['proposedTarget'],'heldProposalSha256':b['proposedTargetSha256'],
          'integratedTargetSha256':tsha(target),'confidence':'low','reason':LOW_LANGUAGE_HOLDS[k]})
    rows.append(row)
    counts[row['integratedDecision']]+=1
    origins[origin]+=1
    resolution_counts[resolution]+=1
    integrated_hashes.append({'position':c['position'],'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],
      'sourceId':c['sourceId'],'locale':c['locale'],'sourceSha256':c['sourceSha256'],
      'currentTargetSha256':c['currentTargetSha256'],'integratedTargetSha256':tsha(target),
      'integratedDecision':row['integratedDecision'],'integratedTargetSource':origin,
      'callerless':False,'independentBlindTargetSha256':blind_hash})
    independent_hashes.append({'blindTargetSha256':blind_hash,'currentTargetSha256':c['currentTargetSha256'],
      'decision':b['decision'],'locale':c['locale'],'position':c['position'],
      'proposedTargetSha256':blind_proposal_hash,'sourceId':c['sourceId'],'sourceSha256':c['sourceSha256'],
      'window':WIN})

assert len(rows)==240 and len(integrated_hashes)==240 and len(independent_hashes)==240
assert counts==collections.Counter({'retain_current':227,'adopt_proposal':13})
assert origins==collections.Counter({'candidate-current':227,'primary':7,'blind':2,'consensus':4})
assert len(held)==10
assert collections.Counter(x['integratedTargetSource'] for x in rows if x['integratedDecision']=='adopt_proposal')==collections.Counter({'primary':7,'blind':2,'consensus':4})

# Preserve the active predecessor holds as two byte-identical source groups.
prior_src=CFROOT/'predecessor/prior-active-holds-hash-only.jsonl'
window_src=CFROOT/'predecessor/w785-current-window-holds-hash-only.jsonl'
shutil.copyfile(prior_src,OUT/'prior-active-holds-hash-only.jsonl')
shutil.copyfile(window_src,OUT/'current-window-holds-hash-only.jsonl')
assert prior_src.read_bytes()==(PR/'predecessor/prior-active-holds-hash-only.jsonl').read_bytes()
assert prior_src.read_bytes()==(BL/'prior-active-holds-hash-only.jsonl').read_bytes()
assert window_src.read_bytes()==(PR/'predecessor/w785-current-window-holds-hash-only.jsonl').read_bytes()
assert window_src.read_bytes()==(BL/'w785-current-window-holds-hash-only.jsonl').read_bytes()
assert len(jlread(prior_src))==1012 and len(jlread(window_src))==48

writejl('integrated-cross-review-ledger.jsonl',rows)
writejl('integrated-target-hashes.jsonl',integrated_hashes)
writejl('independent-target-hashes.jsonl',independent_hashes)
writejl('unresolved-language-holds.jsonl',held)

# Capture full checksums and byte counts for every file in all three input packets.
input_inventory=verify_input_packets()
cfm=jread(CF/'manifest.json'); psummary=jread(PR/'summary.json'); bsummary=jread(BL/'summary.json')
assert (cfm['head'],cfm['tree'],cfm['window'])==(HEAD,TREE,WIN)
assert (psummary['head'],psummary['tree'],psummary['window'])==(HEAD,TREE,WIN)
assert (bsummary['head'],bsummary['tree'],bsummary['window'])==(HEAD,TREE,WIN)
next_boundary=cfm['nextBoundary']
summary={
 'artifact':'ROMarrNG PR #70 W805-W824 integrated cross-review','repository':'snapetech-org/ROMarrNG','pullRequest':70,
 'window':WIN,'head':HEAD,'tree':TREE,'cellCount':240,'localeCount':12,
 'callerBackedCells':240,'callerlessHashOnlyCells':0,
 'primaryProposalCells':13,'independentBlindProposalCells':23,'proposalOverlapCells':8,
 'primaryOnlyProposalCells':5,'blindOnlyProposalCells':15,'uniqueProposalCells':28,
 'identicalOverlapCells':4,'divergentOverlapCellsResolvedByCrossReview':4,
 'proposalOutcomes':{'adoptedCells':13,'lowConfidenceLanguageHolds':10,'unsupportedStyleProposalsRetainedCurrent':5},
 'integratedOrigins':dict(sorted(origins.items())),
 'integratedActions':{'adopt_proposal':13,'retain_current':227},
 'unresolvedLanguageHolds':[{'catalogZeroBasedIndex':x['catalogZeroBasedIndex'],'locale':x['locale'],'sourceId':x['sourceId'],'reason':x['reason']} for x in held],
 'priorActiveHashOnlyHoldsCopiedByteForByte':1012,'currentW785HashOnlyHoldsCopiedByteForByte':48,
 'resultingActiveHashOnlyHolds':1060,'newCallerlessHolds':0,
 'tokenMismatches':{'placeholders':0,'markup':0,'numeric':0,'protectedLiterals':0},
 'confidence':'moderate','nativeSpeakerApproval':False,
 'approvalCaveat':'Selected wording changes and retained low-confidence language holds are machine review results, not native-speaker-approved.',
 'inputVerifierResults':{'candidateFreeOuterChecksums':'PASS','candidateFreeInputChecksums':'PASS',
  'candidateFreePredecessorChecksums':'PASS','primaryReviewVerifier':'PASS (packet-only; no repo argument)',
  'independentBlindVerifier':'PASS (packet-only)'},
 'reviewScope':'Candidate-free, primary, and independent blind packets only; no product worktree, repository, or PR modified; no native-speaker channels inspected.',
 'nextBoundary':next_boundary,'testsBuildsScansCiRun':False,
 'inputPacketFileCounts':{x['name']:x['fileCount'] for x in input_inventory},
}
writej('summary.json',summary)
readme='''# ROMarrNG PR #70 W805–W824 integrated cross-review

Pinned head/tree: 551cccd03e0acdce208ce11f571378c1dcdfb805 / d77f32ac8ec0ab53200d04819869a2e99c6de73c.

The integrated ledger covers all 240 caller-backed cells across 12 locales. It records exact source and current target text, their hashes, caller-context hashes and references, primary/blind decisions and proposals, the integrated target, and token audit.

## Reconciliation

- Primary proposals: 13
- Independent blind proposals: 23
- Overlap: 8 (4 identical and 4 differing, resolved against source/caller context)
- Primary-only proposals: 5
- Blind-only proposals: 15
- Unique proposal cells: 28
- Integrated actions: 13 supported target changes; 227 cells retain current wording.
- Ten low-confidence blind-only wording alternatives remain held at current targets. Five other moderate-confidence alternatives are retained as non-material style changes.
- Existing active hash-only holds: 1,012 older holds plus 48 W785 current-window holds copied byte-for-byte; 1,060 remain active. This W805–W824 window adds no callerless holds.

The 10 held cells are listed with exact current and proposed wording in unresolved-language-holds.jsonl: indices 805 ar/fr, 806 fr, 807 fr/ko, 820 de, and 821 de/es/fr/pt-BR.

## Input integrity and verification

Full SHA-256 and byte counts for every file in the three input packets are recorded in input-packet-checksums.json. Candidate-free outer and inner checksum lists, the predecessor checksum list, and primary/blind packet checksums were verified.

Run the integrated verifier with:

    python3 -B verify_integrated_cross_review.py

Verify output checksums with:

    sha256sum -c SHA256SUMS.txt

Confidence: moderate. Selected wording and held alternatives are machine review recommendations, not native-speaker-approved. No product worktree, repository, or PR was modified; no tests, builds, scans, or CI were run.

Next boundary: index 825, position 826 — ui.platform-for-game-available-platform.afd580990f, source SHA-256 afd580990fe9a12282ffeeeefa2d1a2c8b632f05bdd58b08e3c03a27ac91fb08.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps({'rows':len(rows),'counts':dict(counts),'origins':dict(origins),'proposals':{'primary':13,'blind':23,'overlap':8,'unique':28},'holds':len(held),'inputs':{x['name']:x['fileCount'] for x in input_inventory}},ensure_ascii=False,indent=2))
