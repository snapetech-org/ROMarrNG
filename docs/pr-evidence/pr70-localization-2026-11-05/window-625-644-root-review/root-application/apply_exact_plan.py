#!/usr/bin/env python3
"""Apply only the three root-adjudicated, hash-pinned ROMarrNG cells."""
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path
HEAD='5860fce5d546a772b1df995f8f6321c083ed7d5d'
TREE='561835895972a62e9d3b1f2bfe9bcba01187eb98'
def sha(b): return hashlib.sha256(b).hexdigest()
def sth(s): return sha(s.encode('utf-8'))
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def fail(s): raise SystemExit('FAIL: '+s)
def main():
    p=argparse.ArgumentParser(); p.add_argument('--repo',type=Path,required=True); p.add_argument('--plan',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    repo=a.repo.resolve(); plan=json.loads(a.plan.read_text(encoding='utf-8'))
    if git(repo,'rev-parse','HEAD')!=HEAD or git(repo,'rev-parse','HEAD^{tree}')!=TREE: fail('exact input HEAD/tree mismatch')
    if git(repo,'status','--porcelain=v1'): fail('worktree not clean before apply')
    if plan['sourcePin']!={'head':HEAD,'tree':TREE} or len(plan['changes'])!=3: fail('plan source or change count mismatch')
    path='romarr/ui-labels.json'; raw=(repo/path).read_bytes()
    catalog=json.loads(raw)
    if sha(raw)!=plan['catalogs'][0]['preimageSha256']: fail('catalog preimage hash mismatch')
    if len(catalog['messages'])!=plan['catalogs'][0]['messageCount']: fail('message count mismatch')
    order=hashlib.sha256((json.dumps(list(catalog['messages']),ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
    if order!=plan['catalogs'][0]['messageKeyOrderSha256']: fail('message key order mismatch')
    if raw!=(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode(): fail('catalog serialization mismatch')
    seen=set()
    for c in plan['changes']:
        cell=(c['sourceId'],c['locale'])
        if cell in seen: fail('duplicate selected cell')
        seen.add(cell)
        if c['path']!=path: fail('unexpected target file')
        if sth(c['finalTarget'])!=c['finalTargetSha256']: fail('selected target hash mismatch')
        message=catalog['messages'].get(c['sourceId'])
        if not message or message.get('source')!=c['sourceText'] or message.get('sourceHash')!=c['sourceSha256']: fail('source binding mismatch '+str(cell))
        current=message['translations'].get(c['locale'])
        if current!=c['currentTarget'] or sth(current)!=c['currentTargetSha256']: fail('current target mismatch '+str(cell))
        message['translations'][c['locale']]=c['finalTarget']
    if len(seen)!=3: fail('plan application count mismatch')
    output=(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode()
    temp=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.w625-644-',suffix='.tmp',dir=(repo/path).parent,delete=False) as f:
            f.write(output);f.flush();os.fsync(f.fileno());temp=f.name
        os.replace(temp,repo/path)
    finally:
        if temp and os.path.exists(temp): os.unlink(temp)
    if (repo/path).read_bytes()!=output: fail('postimage write mismatch')
    changed=set(git(repo,'diff','--name-only').splitlines())
    status_text=subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1'],text=True)
    status={line[3:] for line in status_text.splitlines() if len(line)>=4}
    if changed!={path} or status!={path}: fail('working tree is not exactly the selected file')
    result={'result':'PASS','sourcePin':plan['sourcePin'],'selectedCells':3,'changedPaths':[path],'catalogPreimageSha256':sha(raw),'catalogPostimageSha256':sha(output),'catalogKeyOrderSha256':order,'workflowChanges':0}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
