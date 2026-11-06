#!/usr/bin/env python3
"""Apply only the root-adjudicated W645-W664 catalog cells at an exact PR head."""
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path
HEAD='9f8832f67195323955172dd4c3c40e29cbabb5da'
TREE='d6066baa3d03d3b4c6034e5af061fc4bc278b0f9'
def sha(b): return hashlib.sha256(b).hexdigest()
def sth(s): return sha(s.encode('utf-8'))
def translation_hash(value): return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def fail(message): raise SystemExit('FAIL: '+message)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    repo=args.repo.resolve();plan=json.loads(args.plan.read_text(encoding='utf-8'))
    if git(repo,'rev-parse','HEAD')!=HEAD or git(repo,'rev-parse','HEAD^{tree}')!=TREE: fail('exact input HEAD/tree mismatch')
    if git(repo,'status','--porcelain=v1'): fail('worktree not clean before apply')
    if plan.get('sourcePin')!={'head':HEAD,'tree':TREE} or len(plan.get('changes',[]))!=15: fail('plan source or change count mismatch')
    path='romarr/ui-labels.json';catalog_path=repo/path;raw=catalog_path.read_bytes();catalog=json.loads(raw)
    pin=plan['catalogs'][0]
    if sha(raw)!=pin['preimageSha256']: fail('catalog preimage hash mismatch')
    if len(catalog['messages'])!=pin['messageCount']: fail('message count mismatch')
    keys=list(catalog['messages'])
    key_order=sha((json.dumps(keys,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode())
    if key_order!=pin['applicationMessageKeyOrderSha256']: fail('message key order mismatch')
    if raw!=(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode(): fail('catalog serialization mismatch')
    before=json.loads(raw);seen=set();updates=0
    for change in plan['changes']:
        cell=(change['sourceId'],change['locale'])
        if cell in seen: fail('duplicate selected cell')
        seen.add(cell)
        if change['path']!=path: fail('unexpected catalog path')
        if sth(change['finalTarget'])!=change['finalTargetSha256']: fail('final target hash mismatch')
        message=catalog['messages'].get(change['sourceId'])
        if not message or message.get('source')!=change['sourceText'] or message.get('sourceHash')!=change['sourceSha256']: fail('source binding mismatch '+str(cell))
        current=message['translations'].get(change['locale'])
        if current!=change['currentTarget'] or sth(current)!=change['currentTargetSha256']: fail('current target mismatch '+str(cell))
        message['translations'][change['locale']]=change['finalTarget']
    for update in plan['translationHashUpdates']:
        message=catalog['messages'][update['sourceId']];locale=update['locale']
        if message.get('translationStatus',{}).get(locale)!=update['status']: fail('translation status drift '+str((update['sourceId'],locale)))
        if message.get('translationHashes',{}).get(locale)!=update['expectedOldHash']: fail('translationHash preimage mismatch '+str((update['sourceId'],locale)))
        if update['newHash']!=translation_hash(catalog['messages'][update['sourceId']]['translations'][locale]): fail('translationHash postimage not target hash')
        message['translationHashes'][locale]=update['newHash'];updates+=1
    if len(seen)!=15 or updates!=10: fail('selection count mismatch')
    if list(catalog['messages'])!=list(before['messages']): fail('message key order changed')
    # Retain every catalog field except the 15 approved translation cells and 10 matching hash fingerprints.
    expected=json.loads(raw)
    for change in plan['changes']:
        expected['messages'][change['sourceId']]['translations'][change['locale']]=change['finalTarget']
    for update in plan['translationHashUpdates']:
        expected['messages'][update['sourceId']]['translationHashes'][update['locale']]=update['newHash']
    if catalog!=expected: fail('unexpected catalog metadata or non-target changes')
    output=(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode()
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.w645-664-',suffix='.tmp',dir=catalog_path.parent,delete=False) as file:
            file.write(output);file.flush();os.fsync(file.fileno());temporary=file.name
        os.replace(temporary,catalog_path)
    finally:
        if temporary and os.path.exists(temporary): os.unlink(temporary)
    if catalog_path.read_bytes()!=output: fail('catalog postimage mismatch')
    if git(repo,'diff','--name-only').splitlines()!=[path]: fail('working tree changed outside catalog')
    result={'result':'PASS','sourcePin':plan['sourcePin'],'selectedCells':len(seen),'translationHashUpdates':updates,
      'changedPaths':[path],'catalogPreimageSha256':sha(raw),'catalogPostimageSha256':sha(output),
      'applicationMessageKeyOrderSha256':key_order,'translationStatusChanges':0,'translationReviewMetadataChanges':0,'workflowChanges':0}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
if __name__=='__main__':main()
