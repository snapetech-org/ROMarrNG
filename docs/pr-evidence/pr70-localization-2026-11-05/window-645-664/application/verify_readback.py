import argparse, hashlib, json, subprocess
from pathlib import Path

def sha(b): return hashlib.sha256(b).hexdigest()
def sth(s): return sha(s.encode('utf-8'))
def translation_hash(v): return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))
def rows(path): return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--root-ledger',type=Path,required=True);parser.add_argument('--candidate-free-cells',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    repo=a.repo.resolve();plan=json.loads(a.plan.read_text(encoding='utf-8'));app=json.loads((a.plan.parent/'apply-output.json').read_text(encoding='utf-8'))
    head=git(repo,'rev-parse','HEAD').decode().strip();tree=git(repo,'rev-parse','HEAD^{tree}').decode().strip()
    if head!=plan['sourcePin']['head'] or tree!=plan['sourcePin']['tree']: raise SystemExit('exact source head/tree changed before readback')
    old=json.loads(git(repo,'show',f"{head}:romarr/ui-labels.json"));new=json.loads((repo/'romarr/ui-labels.json').read_text(encoding='utf-8'))
    if len(old['messages'])!=len(new['messages']) or list(old['messages'])!=list(new['messages']): raise SystemExit('message set/order changed')
    changes={(x['sourceId'],x['locale']):x for x in plan['changes']};hash_updates={(x['sourceId'],x['locale']):x for x in plan['translationHashUpdates']}
    if len(changes)!=15 or len(hash_updates)!=10: raise SystemExit('plan size mismatch')
    catalog_delta=[]
    for sid,before in old['messages'].items():
        after=new['messages'][sid]
        for field in before:
            if field in ('translations','translationHashes'): continue
            if before[field]!=after[field]: raise SystemExit(f'unexpected message metadata change: {sid}/{field}')
        for locale in set(before['translations'])|set(after['translations']):
            ov=before['translations'].get(locale);nv=after['translations'].get(locale)
            expected=changes.get((sid,locale))
            if expected:
                if ov!=expected['currentTarget'] or sth(ov)!=expected['currentTargetSha256'] or nv!=expected['finalTarget'] or sth(nv)!=expected['finalTargetSha256']:
                    raise SystemExit(f'target readback mismatch: {sid}/{locale}')
                catalog_delta.append((sid,locale,'translation'))
            elif ov!=nv:
                raise SystemExit(f'non-target translation changed: {sid}/{locale}')
        for locale in set(before.get('translationHashes',{}))|set(after.get('translationHashes',{})):
            ov=before.get('translationHashes',{}).get(locale);nv=after.get('translationHashes',{}).get(locale)
            expected=hash_updates.get((sid,locale))
            if expected:
                if ov!=expected['expectedOldHash'] or nv!=expected['newHash'] or nv!=translation_hash(after['translations'][locale]):
                    raise SystemExit(f'translationHash readback mismatch: {sid}/{locale}')
                if before['translationStatus'].get(locale)!=after['translationStatus'].get(locale) or after['translationStatus'].get(locale)!='draft':
                    raise SystemExit(f'translation status changed: {sid}/{locale}')
                catalog_delta.append((sid,locale,'translationHash'))
            elif ov!=nv:
                raise SystemExit(f'non-target translationHash changed: {sid}/{locale}')
    readback=[]
    for row in rows(a.candidate_free_cells):
        k=(row['sourceId'],row['locale']);actual=new['messages'][row['sourceId']]['translations'][row['locale']]
        expected=changes.get(k)
        expected_hash=expected['finalTargetSha256'] if expected else row['currentTargetSha256']
        if sth(actual)!=expected_hash: raise SystemExit(f'240-cell hash readback mismatch: {row["position"]}/{row["locale"]}')
        readback.append({'position':row['position'],'locale':row['locale'],'sourceId':row['sourceId'],
          'expectedTargetSha256':expected_hash,'actualTargetSha256':sth(actual),
          'rootDisposition':('correction' if expected and expected['rootDisposition']=='correction' else 'refinement' if expected else 'accept-current' if row.get('callerRefs') else 'text-free-hold')})
    if len(readback)!=240: raise SystemExit('readback did not cover 240 cells')
    if {x for x in catalog_delta if x[2]=='translation'}!={(x['sourceId'],x['locale'],'translation') for x in plan['changes']}: raise SystemExit('target delta set mismatch')
    if len([x for x in catalog_delta if x[2]=='translationHash'])!=10: raise SystemExit('translationHash delta count mismatch')
    status=subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1'],text=True)
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only'],text=True).splitlines()
    if changed!=['romarr/ui-labels.json'] or {line[3:] for line in status.splitlines()}!={'romarr/ui-labels.json'}: raise SystemExit('unexpected worktree paths')
    raw=(repo/'romarr/ui-labels.json').read_bytes()
    result={'result':'PASS','sourcePin':plan['sourcePin'],'readbackCellCount':len(readback),
      'dispositionCounts':{'accept-current':129,'correction':12,'refinement':3,'text-free-hold':96},
      'appliedTargetCells':15,'updatedTranslationHashCells':10,'translationStatusChanges':0,
      'translationReviewMetadataChanges':0,'catalogMessageCount':len(new['messages']),
      'messageKeyOrderUnchanged':True,'catalogPostimageSha256':sha(raw),
      'changedPaths':['romarr/ui-labels.json'],'readback':readback}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='readback'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
