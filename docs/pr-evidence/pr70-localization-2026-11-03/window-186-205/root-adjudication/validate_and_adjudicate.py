#!/usr/bin/env python3
"""Validate sealed W186-W205 evidence and produce root adjudication."""
import collections, hashlib, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261103/romarrng-pr70-w166-apply-20261103')
BASE = pathlib.Path('/mnt/disks/scratch/task-scratch')
INPUT = BASE/'romarrng-pr70-w186-205-primary-20261103/input'
PRIMARY = BASE/'romarrng-pr70-w186-205-primary-20261103/primary-private'
BLIND = BASE/'romarrng-pr70-w186-205-independent-blind-20261103'
CROSS = BASE/'romarrng-pr70-w186-205-third-party-cross-audit-20261103'
OUT = BASE/'romarrng-pr70-w186-205-application-20261103'
EXPECTED_HEAD='55ee760ea9600f71cc27cba35e098a082445dac8'
EXPECTED_TREE='dbc192813f6347f4307ff8417d505624958eb321'
LOCALES=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']

def jread(p): return json.loads(p.read_text(encoding='utf-8'))
def jlines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(v): return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def git(*args, binary=False):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=not binary)
def verify_manifest(directory):
    subprocess.check_call(['sha256sum','-c','SHA256SUMS.txt'],cwd=directory,stdout=subprocess.DEVNULL)
    man=jread(directory/'manifest.json')
    for f in man.get('files',[]):
        raw=(directory/f['name']).read_bytes()
        assert len(raw)==f['bytes'], (directory,f['name'],'bytes')
        assert sha(raw)==f['sha256'], (directory,f['name'],'sha')
    return sha((directory/'manifest.json').read_bytes())

# Live pins and worktree state.
assert git('rev-parse','HEAD').strip()==EXPECTED_HEAD
assert git('rev-parse','HEAD^{tree}').strip()==EXPECTED_TREE
assert not git('status','--porcelain','--untracked-files=all').strip(), 'exact-head worktree not clean before application'
assert git('branch','--show-current').strip()=='codex/romarr-pr70-w166-apply-20261103'
head= jread(INPUT/'head-and-file-pins.json')
assert head['head']==EXPECTED_HEAD and head['tree']==EXPECTED_TREE
assert head['headRefName']=='task/localization-translation-review-20261030'

input_manifest=jread(INPUT/'manifest.json')
input_manifest_hash=sha((INPUT/'manifest.json').read_bytes())
assert input_manifest['sealed'] and input_manifest['head']==EXPECTED_HEAD and input_manifest['tree']==EXPECTED_TREE
assert input_manifest['inputRows']==240 and input_manifest['window']=={'firstSourceOrdinal':186,'lastSourceOrdinal':205,'sourceCount':20,'locales':LOCALES,'cellCount':240}
manifest_hashes={
 'input':verify_manifest(INPUT),
 'primary':verify_manifest(PRIMARY),
 'blind':verify_manifest(BLIND),
 'cross':verify_manifest(CROSS),
}
assert manifest_hashes['input']==input_manifest_hash
assert jread(PRIMARY/'manifest.json')['inputManifestSha256']==input_manifest_hash
assert jread(PRIMARY/'manifest.json')['inputReviewSha256']==sha((INPUT/'review-input.jsonl').read_bytes())
assert jread(BLIND/'input-attestation.json')['manifestSha256']==input_manifest_hash
assert jread(BLIND/'input-attestation.json')['inputReviewSha256']==sha((INPUT/'review-input.jsonl').read_bytes())
assert jread(CROSS/'input-attestation.json')['candidateFreeInput']['manifestSha256']==input_manifest_hash

# All 56 input file pins match the immutable head by Git blob, byte count, and SHA256.
file_pin_results=[]
for path,pin in head['filePins'].items():
    raw=git('show',f'{EXPECTED_HEAD}:{path}',binary=True)
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert blob==pin['gitBlob'], (path,'blob')
    assert len(raw)==pin['bytes'], (path,'size')
    assert sha(raw)==pin['sha256'], (path,'sha256')
    file_pin_results.append({'path':path,'gitBlob':blob,'bytes':len(raw),'sha256':sha(raw),'matched':True})
assert len(file_pin_results)==56

inp=jlines(INPUT/'review-input.jsonl')
prim=jlines(PRIMARY/'review-decisions.jsonl')
blind=jlines(BLIND/'blind-ledger.jsonl')
cross=jlines(CROSS/'cross-audit.jsonl')
structures=jlines(INPUT/'source-structure.jsonl')
contexts=jlines(INPUT/'source-context.jsonl')
assert [len(x) for x in (inp,prim,blind,cross)]==[240,240,240,240]
key=lambda r:(r['id'],r['locale'])
ims={key(r):r for r in inp}; pms={key(r):r for r in prim}; bms={key(r):r for r in blind}; cms={key(r):r for r in cross}
assert len(ims)==len(pms)==len(bms)==len(cms)==240
assert ims.keys()==pms.keys()==bms.keys()==cms.keys()
sm={r['sourceOrdinal']:r for r in structures}; xm={r['sourceOrdinal']:r for r in contexts}
assert len(sm)==20 and len(xm)==20

def check_literals(source,candidate,structure):
    required=set(structure.get('sourceBundlePlaceholders',[]))|set(structure.get('sourceRegexPlaceholders',[]))
    actual=set(re.findall(r'\{([^{}]+)\}',candidate))
    if required != actual: return False, 'placeholder mismatch', sorted(required), sorted(actual)
    for literal in set(structure.get('sourceProtectedLiterals',[]))|set(structure.get('sourceVersionLiterals',[]))|set(structure.get('sourceMarkupTags',[])):
        if literal and literal in source and literal not in candidate:
            return False, 'protected literal missing: '+literal, sorted(required), sorted(actual)
    return True,'',sorted(required),sorted(actual)

counts=collections.Counter(); primary_counts=collections.Counter(); blind_counts=collections.Counter(); changed=[]; ledger=[]; disputed=[]
for k,row in ims.items():
    p=pms[k]; b=bms[k]; c=cms[k]; ca=c['crossAudit']; s=sm[row['sourceOrdinal']]; ctx=xm[row['sourceOrdinal']]
    assert (p['sourceOrdinal'],p['source'],p['sourceSha256'],p['currentTarget'],p['currentTargetSha256'])==(row['sourceOrdinal'],row['source'],row['sourceSha256'],row['currentTarget'],row['currentTargetSha256']), k
    assert (b['sourceOrdinal'],b['source'],b['sourceSha256'],b['currentTarget'],b['currentTargetSha256'])==(row['sourceOrdinal'],row['source'],row['sourceSha256'],row['currentTarget'],row['currentTargetSha256']), k
    assert (c['sourceOrdinal'],c['source'],c['sourceSha256'],c['currentTarget'],c['currentTargetSha256'])==(row['sourceOrdinal'],row['source'],row['sourceSha256'],row['currentTarget'],row['currentTargetSha256']), k
    assert sha(row['source'].encode())==row['sourceSha256']==s['sourceSha256']==ctx['sourceSha256']
    assert canon(row['currentTarget'])==row['currentTargetSha256']==row['storedTranslationHash']
    assert row['translationStatus']=='draft' and p['translationStatus']=='draft' and b['translationStatus']=='draft'
    assert c['integrity']['sourcePinMatched'] and c['integrity']['currentTargetPinMatched'] and c['integrity']['placeholderSetPreserved'] and c['integrity']['protectedLiteralsPreserved']
    assert p['placeholderCheck']['passed'] and p['protectedLiteralCheck']['passed']
    assert b['integrityChecks']['placeholderSetPreserved'] and b['integrityChecks']['protectedLiteralsPreserved']
    assert row['callerExists'] and row['sourceContextResolved'] and p['callerExists'] and b['callerExists']
    primary_counts[p['outcome']]+=1; blind_counts[b['review']['decision']]+=1
    disposition=ca['decision']
    assert c['callerResolved'] is (disposition != 'hold'), k
    if disposition=='accept-current':
        assert ca['selectedTarget']==row['currentTarget'] and ca['source']=='current'
        target=row['currentTarget']; selected_hash=row['currentTargetSha256']; winner='current'
        reason=ca['rationale']
    elif disposition=='hold':
        assert ca['selectedTarget'] is None and ca['source']=='none'
        target=row['currentTarget']; selected_hash=row['currentTargetSha256']; winner='held-current'
        reason=ca['rationale']
    else:
        assert disposition in ('correction','refinement')
        target=ca['selectedTarget']; selected_hash=ca['selectedTargetSha256']; winner=ca['source']; reason=ca['rationale']
        assert target is not None and selected_hash==canon(target)
        ok, why, required, actual=check_literals(row['source'],target,s)
        assert ok, (k,why,required,actual)
        assert p['placeholderCheck']['passed'] and p['protectedLiteralCheck']['passed']
        changed.append(k)
    if c['agreement'] in ('different-proposals','primary-only-proposal','blind-only-proposal'):
        disputed.append({'sourceOrdinal':row['sourceOrdinal'],'id':row['id'],'locale':row['locale'],'primaryDecision':p['outcome'],'primaryCandidate':p.get('suggestedTarget'),'blindDecision':b['review']['decision'],'blindCandidate':b['review'].get('candidateTarget'),'rootDisposition':disposition,'winner':target,'winnerSource':winner,'rationale':reason})
    counts[disposition]+=1
    ledger.append({
      'sourceOrdinal':row['sourceOrdinal'],'id':row['id'],'locale':row['locale'],
      'source':row['source'],'sourceSha256':row['sourceSha256'],
      'currentTarget':row['currentTarget'],'currentTargetSha256':row['currentTargetSha256'],
      'storedTranslationHash':row['storedTranslationHash'],'translationStatus':'draft',
      'primary':{'disposition':p['outcome'],'confidence':p.get('confidence'),'candidate':p.get('suggestedTarget'),'candidateSha256':p.get('suggestedTargetSha256'),'rationale':p['rationale']},
      'blind':{'disposition':b['review']['decision'],'confidence':b['review'].get('confidence'),'candidate':b['review'].get('candidateTarget'),'candidateSha256':b['review'].get('candidateTargetSha256'),'rationale':b['review'].get('rationale')},
      'crossAudit':{'agreement':c.get('agreement'),'winnerSource':winner,'rationale':reason},
      'rootDisposition':disposition,'adjudicatedTarget':target,'adjudicatedTargetSha256':selected_hash,
      'caller':{'resolved':c['callerResolved'],'reason':c['callerReason'],'sourceContextEntrySha256':b['callerEvidence']['sourceContextEntrySha256'],'references':b['callerEvidence']['references']},
      'structureChecks':{'placeholderParity':True,'protectedLiteralsPreserved':True},
      'rootRationale':(('Retain current: ' if disposition=='accept-current' else 'Preserve caller-context hold: ' if disposition=='hold' else f"Ratify {winner} winner as {disposition}: ")+reason)
    })

assert counts=={'accept-current':137,'correction':17,'refinement':26,'hold':60}, counts
assert primary_counts=={'accept-current':137,'correction':23,'refinement':20,'hold-context':60},primary_counts
assert blind_counts=={'accept-current':159,'correction':13,'refinement':8,'hold':60},blind_counts
assert len(changed)==43
assert all(sum(1 for r in ledger if r['sourceOrdinal']==o and r['rootDisposition']=='hold')==12 for o in (188,197,198,200,201))

OUT.mkdir(parents=True,exist_ok=True)
(OUT/'root-adjudication-ledger.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in ledger),encoding='utf-8')
(OUT/'disputed-cells.json').write_text(json.dumps(disputed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={
 'artifact':'ROMarrNG PR #70 W186-W205 root adjudication input validation',
 'repository':'snapetech-org/ROMarrNG','pullRequest':70,'head':EXPECTED_HEAD,'tree':EXPECTED_TREE,
 'worktreeBranch':git('branch','--show-current').strip(),'worktreeCleanBeforeApplication':True,
 'packetManifestSha256':manifest_hashes,'inputManifestSha256':input_manifest_hash,
 'filePins':{'count':len(file_pin_results),'gitBlobSha256BytesMatches':len(file_pin_results),'mismatches':0},
 'filePinResults':file_pin_results,
 'cells':{'input':len(inp),'primary':len(prim),'blind':len(blind),'crossAudit':len(cross),'unique':len(ims),'mismatches':0},
 'primaryCounts':dict(primary_counts),'blindCounts':dict(blind_counts),'rootCounts':dict(counts),
 'appliedCandidateCount':len(changed),'disputedRecommendationCount':len(disputed),
 'heldOrdinals':[188,197,198,200,201],'heldCellCount':60,
 'placeholderProtectedCandidateChecksPassed':len(changed),
 'nativeSpeakerApproval':False,'automatedTestsBuildsScansCiRun':False,
 'rootDecision':'Ratify every third-party cross-audit recommendation; preserve all exact-head caller-context holds and keep changed cells draft.'
}
(OUT/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('filePinResults',)},ensure_ascii=False,indent=2))
