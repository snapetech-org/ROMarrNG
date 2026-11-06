#!/usr/bin/env python3
"""Verify the full ROMarrNG W625-W644 application readback."""
import argparse, collections, copy, hashlib, json, subprocess
from pathlib import Path
HEAD='5860fce5d546a772b1df995f8f6321c083ed7d5d'
TREE='561835895972a62e9d3b1f2bfe9bcba01187eb98'
PRODUCT='86f6161f3069bb3113f8f7a8a763193f15c4e2bc'
PRODUCT_TREE='29b85a61d3ef20b73ec15c5aa08c5a23788d32f8'
def sha(b): return hashlib.sha256(b).hexdigest()
def sth(s): return sha(s.encode('utf-8'))
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def readjl(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def fail(s): raise SystemExit('FAIL: '+s)
def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--root-ledger',type=Path,required=True);p.add_argument('--candidate-free',type=Path,required=True);p.add_argument('--cross-review',type=Path,required=True);p.add_argument('--readback',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    repo=a.repo.resolve();plan=json.loads(a.plan.read_text(encoding='utf-8')); ledger=readjl(a.root_ledger); cand=readjl(a.candidate_free); cross=readjl(a.cross_review)
    if git(repo,'rev-parse','HEAD')!=PRODUCT or git(repo,'rev-parse','HEAD^')!=HEAD or git(repo,'rev-parse','HEAD^{tree}')!=PRODUCT_TREE: fail('exact product HEAD, parent, or tree drift')
    if plan['sourcePin']!={'head':HEAD,'tree':TREE} or len(plan['changes'])!=3: fail('plan pin or row count mismatch')
    if len(ledger)!=240 or len(cand)!=240 or len(cross)!=240: fail('full 240-cell matrix incomplete')
    cfm={(x['position'],x['locale']):x for x in cand}; crm={(x['position'],x['locale']):x for x in cross}; ldm={(x['position'],x['locale']):x for x in ledger}
    if len(cfm)!=240 or set(cfm)!=set(crm) or set(cfm)!=set(ldm): fail('cell key sets differ')
    changes={(x['position'],x['locale']):x for x in plan['changes']}
    if len(changes)!=3: fail('duplicate plan cell')
    base_raw=subprocess.check_output(['git','-C',str(repo),'show',f'{HEAD}:romarr/ui-labels.json'])
    base=json.loads(base_raw); live_raw=(repo/'romarr/ui-labels.json').read_bytes(); live=json.loads(live_raw)
    if live_raw!=(json.dumps(live,ensure_ascii=False,indent=2)+'\n').encode(): fail('catalog serialization drift')
    expected=copy.deepcopy(base); readback=[]; count=collections.Counter(); changed=0
    for key in sorted(cfm):
        c=cfm[key]; x=crm[key]; r=ldm[key]; change=changes.get(key)
        if c['sourceId']!=x['sourceId'] or c['sourceSha256']!=x['sourceSha256'] or c['currentTargetSha256']!=x['currentTargetSha256'] or c['callerContextSha256']!=x['callerContextSha256']: fail('source/target/context binding mismatch '+str(key))
        if c['currentTarget']!=x['currentTarget'] or sth(c['currentTarget'])!=c['currentTargetSha256']: fail('candidate target hash mismatch '+str(key))
        if r['sourceId']!=c['sourceId'] or r['sourceSha256']!=c['sourceSha256'] or r['currentTargetSha256']!=c['currentTargetSha256'] or r['callerContextSha256']!=c['callerContextSha256']: fail('root ledger hash mismatch '+str(key))
        target=change['finalTarget'] if change else c['currentTarget']
        msg=live['messages'].get(c['sourceId'])
        if not msg or msg['sourceHash']!=c['sourceSha256']: fail('source catalog binding mismatch '+str(key))
        observed=msg['translations'].get(c['locale'])
        if observed!=target or sth(observed)!=sth(target): fail('cell readback mismatch '+str(key))
        if change:
            if x['crossAdjudication']['decision']!='revise' or change['currentTargetSha256']!=c['currentTargetSha256']: fail('selected correction not cross-supported '+str(key))
            expected['messages'][c['sourceId']]['translations'][c['locale']]=target
            count[change['rootDisposition']]+=1
            changed+=observed!=c['currentTarget']
        elif x['callerless']:
            if not r['callerless'] or r['disposition']!='hold-callerless-hash-only' or 'currentTarget' in r or 'source' in r: fail('callerless hold is not text-free '+str(key))
            if observed!=c['currentTarget']: fail('callerless hold changed '+str(key))
            count['hold-callerless-hash-only']+=1
        else:
            if r['disposition']!='accept-current' or observed!=c['currentTarget']: fail('unselected callerful cell changed '+str(key))
            count['accept-current']+=1
        item={'position':key[0],'locale':key[1],'sourceId':c['sourceId'],'sourceSha256':c['sourceSha256'],'callerContextSha256':c['callerContextSha256'],'beforeTargetSha256':c['currentTargetSha256'],'expectedAfterSha256':sth(target),'observedAfterSha256':sth(observed),'changed':observed!=c['currentTarget'],'rootDisposition':r['disposition']}
        if not x['callerless']:
            item['source']=c['source'];item['beforeTarget']=c['currentTarget'];item['afterTarget']=observed
        readback.append(item)
    if changed!=3: fail('expected exactly three changed cells')
    if live!=expected: fail('non-target catalog content changed')
    if list(base['messages'])!=list(live['messages']): fail('message key order changed')
    if len(live['messages'])!=1836: fail('message count changed')
    changed_paths=set(git(repo,'diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines())
    status=subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1'],text=True).splitlines()
    if changed_paths!={'romarr/ui-labels.json'} or status: fail('product commit paths or working tree unexpected')
    if any(x.startswith('.github/workflows/') for x in changed_paths): fail('workflow changed')
    a.readback.parent.mkdir(parents=True,exist_ok=True)
    a.readback.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in readback),encoding='utf-8')
    result={'result':'PASS','inputHead':HEAD,'inputTree':TREE,'head':PRODUCT,'tree':PRODUCT_TREE,'candidateCells':240,'observedChangedCells':changed,'dispositionCounts':dict(count),'changedPaths':sorted(changed_paths),'messageCount':len(live['messages']),'messageKeyOrderPreserved':True,'nonTargetCatalogContentPreserved':True,'callerlessHoldsTextFree':True,'workflowChanges':0,'readbackSha256':sha(a.readback.read_bytes()),'catalogPostimageSha256':sha(live_raw)}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
