#!/usr/bin/env python3
"""Verify the sealed ROMarrNG PR #70 W805-W824 primary review packet."""
import argparse, collections, hashlib, json, re, subprocess, sys
from pathlib import Path

PIN_HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'; PIN_TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
WINDOW='W805-W824'; START=805; END=824
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']
PLACEHOLDER=re.compile(r'\{[^{}]+\}'); TAG=re.compile(r'<[^>]+>'); NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')
PROTECTED=['Gaseous','Retrom','SeerrNG','ROMarrNG','ROMarr','ES-DE','No-Intro','Redump','DAT','IGDB','ISO9660','PLAYSTATION','PlayStation','PS2','ROMs','ROM','PC','API','ROMARR_API_KEY','Linksnappy','Moonlight','PIN','NPSSO','NZBHydra2','Newznab','/torznab/api','NZBVortex','HTTPS','NZB','Preferences']

def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def read_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def read_jsonl(p): return [json.loads(s) for s in Path(p).read_text(encoding='utf-8').splitlines() if s.strip()]
def protected(s):
    out=[]
    for lit in PROTECTED:
        ok=lit in s if lit.startswith('/') else bool(re.search(r'(?<![A-Za-z0-9])'+re.escape(lit)+r'(?![A-Za-z0-9])',s))
        if ok: out.append(lit)
    return sorted(set(out))
def token_audit(source,target):
    sph=PLACEHOLDER.findall(source); tph=PLACEHOLDER.findall(target); sm=TAG.findall(source); tm=TAG.findall(target)
    sn=NUMBER.findall(source); tn=NUMBER.findall(target); sp=protected(source); tp=protected(target); missing=[x for x in sp if x not in target]
    return {'sourcePlaceholderTokens':sph,'currentTargetPlaceholderTokens':tph,'proposedPlaceholderTokens':tph,'placeholderMultisetMatches':collections.Counter(sph)==collections.Counter(tph),'sourceMarkupTags':sm,'currentMarkupTags':tm,'proposedMarkupTags':tm,'markupMultisetMatches':collections.Counter(sm)==collections.Counter(tm),'sourceNumericTokens':sn,'currentNumericTokens':tn,'proposedNumericTokens':tn,'numericTokensPreserved':collections.Counter(sn)==collections.Counter(tn),'sourceProtectedLiterals':sp,'currentProtectedLiterals':tp,'proposedProtectedLiterals':tp,'missingProtectedLiterals':missing,'protectedLiteralsPreserved':not missing}
def check_sums(root):
    root=Path(root).resolve(); sums=root/'SHA256SUMS.txt'; listed={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); n=n.removeprefix('./'); p=(root/n).resolve()
        if not p.is_relative_to(root) or not p.is_file() or sha(p.read_bytes())!=h or n in listed: raise SystemExit(f'FAIL checksum {p}')
        listed[n]=h
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=sums}
    if set(listed)!=actual: raise SystemExit('FAIL checksum coverage')
    return listed

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path); ap.add_argument('--candidate-free',type=Path,required=True); a=ap.parse_args()
    out=Path(__file__).resolve().parent; root_sums=check_sums(out); inp=a.candidate_free.resolve()
    for root in (inp,inp/'input',inp/'predecessor'):
        p=subprocess.run(['sha256sum','-c','SHA256SUMS.txt'],cwd=root,text=True,capture_output=True)
        if p.returncode: raise ValueError(f'candidate-free checksums failed: {root}')
    im=read_json(inp/'input/manifest.json'); sm=read_json(out/'summary.json')
    if (im.get('head'),im.get('tree'),im.get('window'))!=(PIN_HEAD,PIN_TREE,WINDOW): raise ValueError('candidate-free input pin mismatch')
    if (sm.get('head'),sm.get('tree'),sm.get('window'))!=(PIN_HEAD,PIN_TREE,WINDOW): raise ValueError('primary summary pin mismatch')
    if sm.get('candidateFreeSha256SumsListSha256')!=sha((inp/'SHA256SUMS.txt').read_bytes()): raise ValueError('candidate-free checksum list hash mismatch')
    base=read_jsonl(inp/'input/candidate-free-cells.jsonl'); contexts={x['sourceId']:x for x in read_jsonl(inp/'input/source-contexts.jsonl')}
    if len(base)!=240 or len({(r['sourceId'],r['locale']) for r in base})!=240: raise ValueError('candidate-free input coverage')
    if [r['catalogZeroBasedIndex'] for r in base[::12]]!=list(range(START,END+1)) or any([r['locale'] for r in base[i:i+12]]!=LOCALES for i in range(0,240,12)): raise ValueError('candidate-free ordering')
    ledger=read_jsonl(out/'primary-review-ledger.jsonl')
    if len(ledger)!=240 or len({(r['sourceId'],r['locale']) for r in ledger})!=240: raise ValueError('primary ledger coverage')
    bykey={(r['sourceId'],r['locale']):r for r in ledger}; baseby={(r['sourceId'],r['locale']):r for r in base}
    if set(bykey)!=set(baseby): raise ValueError('input/review cell set mismatch')
    dispositions=collections.Counter(); changes=0
    for key,b in baseby.items():
        e=bykey[key]; sid,loc=key
        if (e.get('window'),e.get('sourceId'),e.get('locale'),e.get('position'),e.get('catalogZeroBasedIndex'),e.get('catalogOneBasedPosition'))!=(WINDOW,sid,loc,b['position'],b['catalogZeroBasedIndex'],b['catalogOneBasedPosition']): raise ValueError(f'identity mismatch {key}')
        if e.get('candidateFree') is not True or e.get('nativeSpeakerApproval') is not False or e.get('callerless') is not False: raise ValueError(f'provenance/caller status mismatch {key}')
        if (e.get('source'),e.get('currentTarget'),e.get('sourceSha256'),e.get('currentTargetSha256'),e.get('callerContextSha256'))!=(b.get('source'),b.get('currentTarget'),b['sourceSha256'],b['currentTargetSha256'],b['callerContextSha256']): raise ValueError(f'source/current/context mismatch {key}')
        if sha(canon(b))!=e.get('candidateFreeCellRecordSha256'): raise ValueError(f'candidate-free row hash mismatch {key}')
        target=e.get('proposedTarget'); th=sha(target) if isinstance(target,str) else None
        if (th,e.get('proposedTargetSha256'),e.get('selectedTargetSha256'))!=(e.get('proposedTargetSha256'),e.get('proposedTargetSha256'),e.get('proposedTargetSha256')): raise ValueError(f'selected target hash mismatch {key}')
        if e['disposition']=='accept_current' and target!=b['currentTarget']: raise ValueError(f'accept-current target mismatch {key}')
        if e['disposition'] in ('correction','refinement'):
            changes+=1
            if target==b['currentTarget'] or not e.get('rationale'): raise ValueError(f'changed target lacks rationale {key}')
        elif e['disposition']!='accept_current': raise ValueError(f'unknown disposition {key}')
        if e.get('confidence') not in ('high','moderate','low','unknown'): raise ValueError(f'confidence missing {key}')
        if not e.get('rationale') or e.get('reviewMethod')!='primary machine semantic review from candidate-free source and caller evidence': raise ValueError(f'review rationale/method missing {key}')
        ctx=contexts[sid]
        expected_refs=[{'path':c['path'],'line':c['line'],'matchKind':c['matchKind'],'lineSha256':c['lineSha256'],'excerptSha256':c['excerptSha256'],'fileSha256':c['fileSha256'],'gitBlob':c['gitBlob']} for c in ctx['callers']]
        if e.get('callerReferenceCount')!=ctx['exactMatchCount'] or e.get('callerReferences')!=expected_refs: raise ValueError(f'caller references mismatch {key}')
        audit=token_audit(b['source'],target)
        if any(e.get(k)!=v for k,v in audit.items()): raise ValueError(f'token/protected-literal audit mismatch {key}')
        if not (audit['placeholderMultisetMatches'] and audit['markupMultisetMatches'] and audit['numericTokensPreserved'] and audit['protectedLiteralsPreserved']): raise ValueError(f'recommended target breaks protected token {key}')
        dispositions[e['disposition']]+=1
    if changes!=13 or dispositions!=collections.Counter({'accept_current':227,'correction':6,'refinement':7}): raise ValueError(f'dispositions mismatch {dispositions}')
    if sm.get('dispositions')!=dict(sorted(dispositions.items())) or sm.get('alternativeTargets')!=changes: raise ValueError('summary count mismatch')
    if sm.get('nativeSpeakerApproval') is not False or sm.get('blindOrCrossReviewMaterialUsed') is not False: raise ValueError('review scope metadata mismatch')
    # The two active hold source files are byte-identical copies from candidate-free input.
    for n in ('prior-active-holds-hash-only.jsonl','w785-current-window-holds-hash-only.jsonl'):
        if (out/'predecessor'/n).read_bytes()!=(inp/'predecessor'/n).read_bytes(): raise ValueError(f'hold lineage copy mismatch {n}')
    holds=read_jsonl(out/'predecessor/prior-active-holds-hash-only.jsonl')+read_jsonl(out/'predecessor/w785-current-window-holds-hash-only.jsonl')
    if len(holds)!=1060 or len({(r['sourceId'],r['locale']) for r in holds})!=1060: raise ValueError('active prior hold count/uniqueness mismatch')
    forbidden={'source','sourceText','currentTarget','target','targetText','proposedTarget'}
    if any(r.get('textOmitted') is not True or forbidden.intersection(r) for r in holds): raise ValueError('active hold text leak')
    lineage=read_json(out/'hold-lineage.json')
    if lineage.get('activeHashOnlyHoldCount')!=1060 or lineage.get('copiedByteForByte') is not True or lineage.get('resultingActiveHashOnlyHolds')!=1060: raise ValueError('hold lineage summary mismatch')
    if sm.get('priorActiveHashOnlyHoldsCopiedByteForByte')!=1060 or sm.get('resultingActiveHashOnlyHolds')!=1060: raise ValueError('summary hold count mismatch')
    if sm.get('nextBoundary')!=im.get('nextBoundary'): raise ValueError('next boundary mismatch')
    if a.repo:
        repo=a.repo.resolve()
        head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
        tree=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD^{tree}'],text=True).strip()
        status=subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1','--untracked-files=all'],text=True).strip()
        if (head,tree)!=(PIN_HEAD,PIN_TREE) or status: raise ValueError('product worktree pin/cleanliness mismatch')
    print(json.dumps({'result':'PASS','head':PIN_HEAD,'tree':PIN_TREE,'window':WINDOW,'cells':len(ledger),'dispositions':dict(sorted(dispositions.items())),'alternativeTargets':changes,'callerBackedCells':240,'activePriorHashOnlyHoldsCopiedByteForByte':1060,'resultingActiveHashOnlyHolds':1060,'nativeSpeakerApproval':False,'candidateFreeChecksums':'PASS','candidateFreeHoldCopiesIdentical':True,'nextBoundary':sm['nextBoundary'],'checksummedFiles':len(root_sums),'worktreePinnedAndClean':bool(a.repo)},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'FAIL: {e}',file=sys.stderr); sys.exit(1)
