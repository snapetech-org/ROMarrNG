#!/usr/bin/env python3
"""Apply only root-selected ROMarrNG W805-W824 targets and record exact readback."""
import argparse, collections, hashlib, json, subprocess
from pathlib import Path

INPUT_HEAD='551cccd03e0acdce208ce11f571378c1dcdfb805'
INPUT_TREE='d77f32ac8ec0ab53200d04819869a2e99c6de73c'
REVIEW_HEAD='db188b5ded679803b055f2c09c0a97ab00e489cd'
REVIEW_TREE='3cfcad74a27ffd4a1b91777a5fb37fa9143c1f26'
CAT='romarr/ui-labels.json'
LOCALES=['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']

def sha(b):
    if isinstance(b,str): b=b.encode('utf-8')
    return hashlib.sha256(b).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def jl(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def write_json(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def write_jsonl(p,rows): Path(p).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def git_bytes(repo,rev,path): return subprocess.check_output(['git','-C',str(repo),'show',f'{rev}:{path}'])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=Path,required=True); ap.add_argument('--evidence-root',type=Path,required=True)
    a=ap.parse_args(); repo=a.repo.resolve(); evidence=a.evidence_root.resolve(); out=Path(__file__).resolve().parent
    if git(repo,'rev-parse','HEAD')!=REVIEW_HEAD or git(repo,'rev-parse','HEAD^{tree}')!=REVIEW_TREE: raise SystemExit('FAIL review evidence head/tree')
    if git(repo,'status','--porcelain=v1','--untracked-files=all'): raise SystemExit('FAIL worktree must be clean before application')
    # Verify the portable root decision packet before changing the catalog.
    subprocess.check_call(['python3','-B',str(evidence/'root-adjudication/verify_root_adjudication.py'),'--repo',str(repo)])
    raw_before=git_bytes(repo,INPUT_HEAD,CAT)
    if sha(raw_before)!=json.loads((evidence/'root-adjudication/input-attestation.json').read_text())['inputCatalogSha256']:
        raise SystemExit('FAIL input catalog hash does not match root attestation')
    local_path=repo/CAT
    if local_path.read_bytes()!=git_bytes(repo,REVIEW_HEAD,CAT): raise SystemExit('FAIL current catalog differs from clean review-evidence head')
    if raw_before!=local_path.read_bytes(): raise SystemExit('FAIL product catalog changed since candidate-free input head')
    if raw_before!=(json.dumps(json.loads(raw_before),ensure_ascii=False,indent=2)+'\n').encode('utf-8'):
        raise SystemExit('FAIL catalog serialization roundtrip')
    before=json.loads(raw_before); data=json.loads(raw_before); messages=before['messages']; ids=list(messages)
    nonempty_before={loc:sum(bool(m.get('translations',{}).get(loc)) for m in messages.values()) for loc in LOCALES}
    candidate=jl(evidence/'candidate-free/input/candidate-free-cells.jsonl')
    selected=jl(evidence/'root-adjudication/selected-targets.jsonl')
    low=jl(evidence/'root-adjudication/low-confidence-language-holds.jsonl')
    hold1=jl(evidence/'root-adjudication/prior-active-holds-hash-only.jsonl')
    hold2=jl(evidence/'root-adjudication/w785-current-window-holds-hash-only.jsonl')
    holds=hold1+hold2
    if (len(candidate),len(selected),len(low),len(hold1),len(hold2),len(holds))!=(240,13,10,1012,48,1060): raise SystemExit('FAIL evidence row counts')
    cfm={(r['sourceId'],r['locale']):r for r in candidate}; sm={(r['sourceId'],r['locale']):r for r in selected}; lowm={(r['sourceId'],r['locale']):r for r in low}
    if len(cfm)!=240 or len(sm)!=13 or len(lowm)!=10: raise SystemExit('FAIL duplicate evidence keys')
    active={(r['sourceId'],r['locale']) for r in holds}
    if len(active)!=1060 or set(active)&set(sm): raise SystemExit('FAIL active hold uniqueness or overlap')
    before_hold_hashes={}
    for h in holds:
        sid,loc=h['sourceId'],h['locale']; msg=messages[sid]
        if sha(msg['source'])!=h['sourceSha256'] or sha(msg['translations'][loc])!=h['currentTargetSha256']:
            raise SystemExit(f'FAIL pre-application active hold {sid}/{loc}')
        before_hold_hashes[(sid,loc)]=sha(msg['translations'][loc])
    for key,h in lowm.items():
        c=cfm[key]
        if c['currentTargetSha256']!=h['currentTargetSha256'] or h['integratedTargetSha256']!=h['currentTargetSha256'] or sha(messages[key[0]]['translations'][key[1]])!=h['currentTargetSha256']:
            raise SystemExit(f'FAIL low-confidence current target before apply {key}')
    changes=[]
    for key,r in sm.items():
        c=cfm[key]; msg=data['messages'][key[0]]; loc=key[1]
        if (r['source'],r['currentTarget'])!=(c['source'],c['currentTarget']): raise SystemExit(f'FAIL selected text input {key}')
        if (r['sourceSha256'],r['currentTargetSha256'],r['callerContextSha256'])!=(c['sourceSha256'],c['currentTargetSha256'],c['callerContextSha256']): raise SystemExit(f'FAIL selected provenance {key}')
        if sha(r['rootTarget'])!=r['rootTargetSha256'] or r['rootTargetSha256']!=r['integratedTargetSha256']: raise SystemExit(f'FAIL selected target hash {key}')
        if msg['translations'][loc]!=c['currentTarget'] or sha(msg['translations'][loc])!=c['currentTargetSha256']: raise SystemExit(f'FAIL current target before apply {key}')
        msg['translations'][loc]=r['rootTarget']
        changes.append({'position':r['position'],'catalogZeroBasedIndex':r['catalogZeroBasedIndex'],'catalogOneBasedPosition':r['catalogOneBasedPosition'],'sourceId':r['sourceId'],'locale':loc,'sourceSha256':r['sourceSha256'],'callerContextSha256':r['callerContextSha256'],'beforeTargetSha256':r['currentTargetSha256'],'afterTargetSha256':r['rootTargetSha256'],'rootDisposition':r['rootDisposition'],'integratedTargetSource':r['integratedTargetSource'],'confidence':r['confidence'],'nativeSpeakerApproval':False})
    raw_after=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    local_path.write_bytes(raw_after)
    after=json.loads(local_path.read_text(encoding='utf-8'))
    if list(after['messages'])!=ids: raise SystemExit('FAIL catalog key order changed')
    changed=[]; readback=[]
    for c in candidate:
        sid,loc=c['sourceId'],c['locale']; before_target=before['messages'][sid]['translations'][loc]; after_target=after['messages'][sid]['translations'][loc]; key=(sid,loc); sel=sm.get(key)
        if sel:
            if after_target!=sel['rootTarget']: raise SystemExit(f'FAIL selected target readback {key}')
            changed.append(key)
            disposition=sel['rootDisposition']; expected_hash=sel['rootTargetSha256']
        else:
            if after_target!=before_target: raise SystemExit(f'FAIL unselected catalog cell changed {key}')
            disposition='hold-low-confidence-current' if key in lowm else 'accept-current'
            expected_hash=c['currentTargetSha256']
        readback.append({'position':c['position'],'catalogZeroBasedIndex':c['catalogZeroBasedIndex'],'catalogOneBasedPosition':c['catalogOneBasedPosition'],'sourceId':sid,'locale':loc,'sourceSha256':c['sourceSha256'],'callerContextSha256':c['callerContextSha256'],'beforeTargetSha256':sha(before_target),'afterTargetSha256':sha(after_target),'expectedTargetSha256':expected_hash,'rootDisposition':disposition,'applied':sel is not None,'textOmitted':True})
    if len(changed)!=13 or set(changed)!=set(sm): raise SystemExit('FAIL exact changed cell set')
    if len(after['messages'])!=1836: raise SystemExit('FAIL catalog message count')
    nonempty_after={loc:sum(bool(m.get('translations',{}).get(loc)) for m in after['messages'].values()) for loc in LOCALES}
    if nonempty_after!=nonempty_before or any(nonempty_after[loc]!=1836 for loc in LOCALES):
        raise SystemExit('FAIL locale catalog completeness changed')
    hold_readback=[]
    for h in holds:
        key=(h['sourceId'],h['locale']); msg=after['messages'][key[0]]; after_hash=sha(msg['translations'][key[1]])
        if sha(msg['source'])!=h['sourceSha256'] or after_hash!=before_hold_hashes[key] or after_hash!=h['currentTargetSha256']:
            raise SystemExit(f'FAIL active hold changed after application {key}')
        hold_readback.append({'priorWindow':h.get('priorWindow',h.get('window')),'sourceId':key[0],'locale':key[1],'catalogZeroBasedIndex':ids.index(key[0]),'sourceSha256':h['sourceSha256'],'priorTargetSha256':h['currentTargetSha256'],'beforeTargetSha256':before_hold_hashes[key],'afterTargetSha256':after_hash,'unchanged':True,'textOmitted':True})
    low_readback=[]
    for key,h in lowm.items():
        after_hash=sha(after['messages'][key[0]]['translations'][key[1]])
        if after_hash!=h['currentTargetSha256']: raise SystemExit(f'FAIL low-confidence current changed {key}')
        low_readback.append({'sourceId':key[0],'locale':key[1],'currentTargetSha256':h['currentTargetSha256'],'heldProposalSha256':h['heldProposalSha256'],'afterTargetSha256':after_hash,'unchanged':True,'confidence':'low','textOmitted':True})
    write_jsonl(out/'readback-240.jsonl',readback)
    write_jsonl(out/'active-hold-readback-1060.jsonl',hold_readback)
    write_jsonl(out/'low-confidence-hold-readback-10.jsonl',low_readback)
    write_json(out/'readback-before-commit.json',{'artifact':'ROMarrNG PR #70 W805-W824 product application readback before commit','repository':'snapetech-org/ROMarrNG','pullRequest':70,'window':'W805-W824','inputHead':INPUT_HEAD,'inputTree':INPUT_TREE,'reviewEvidenceCommit':REVIEW_HEAD,'reviewEvidenceTree':REVIEW_TREE,'changedCatalogPath':CAT,'changedCellCount':len(changes),'readbackCellCount':len(readback),'activeHashOnlyHoldsReattested':len(hold_readback),'lowConfidenceCurrentTargetsRetained':len(low_readback),'catalogKeyOrderPreserved':True,'allOtherReviewedCellsUnchanged':True,'all12DirectLocalesHave1836NonemptyMessages':True,'nonemptyTranslationCountPerLocaleBefore':nonempty_before,'nonemptyTranslationCountPerLocaleAfter':nonempty_after,'localeCount':len(LOCALES),'messageCountPerLocale':1836,'candidateFreeCellsSha256':sha((evidence/'candidate-free/input/candidate-free-cells.jsonl').read_bytes()),'rootSelectedTargetsSha256':sha((evidence/'root-adjudication/selected-targets.jsonl').read_bytes()),'activeHoldReadbackSha256':sha((out/'active-hold-readback-1060.jsonl').read_bytes()),'lowConfidenceReadbackSha256':sha((out/'low-confidence-hold-readback-10.jsonl').read_bytes()),'readbackRowsSha256':sha((out/'readback-240.jsonl').read_bytes()),'catalogSha256After':sha(raw_after),'productDiffNames':[CAT],'nativeSpeakerApproval':False,'headedBrowserReviewPerformed':False,'productCommitPending':True})
    print(json.dumps({'result':'APPLIED_AND_READ_BACK','changedCellCount':len(changes),'readbackCellCount':len(readback),'activeHashOnlyHoldsUnchanged':len(hold_readback),'lowConfidenceTargetsUnchanged':len(low_readback),'catalogKeyOrderPreserved':True,'localeCount':len(LOCALES),'messagesPerLocale':1836,'catalogSha256After':sha(raw_after),'worktreeDiff':git(repo,'status','--short')},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
