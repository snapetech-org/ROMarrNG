#!/usr/bin/env python3
import hashlib, json, subprocess
from pathlib import Path
TASK=Path(__file__).resolve().parents[1]
REPO=Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
HEAD='c3f92c45b4b4f8d79a8caa99417f9970ebc42a26'
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def sha(b): return hashlib.sha256(b).hexdigest()
product=git('rev-parse','HEAD'); parent=git('rev-parse','HEAD^'); tree=git('rev-parse','HEAD^{tree}')
assert parent==HEAD
names=git('diff-tree','--no-commit-id','--name-only','-r',product).splitlines()
assert names==['romarr/ui-labels.json']
raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{product}:romarr/ui-labels.json'])
p=TASK/'application'/'readback-before-commit.json'
d=json.loads(p.read_text(encoding='utf-8'))
assert sha(raw)==d['catalogSha256After']
d.update({'productCommit':product,'productTree':tree,'commitParent':parent,'productCommitNames':names,'productCommitPending':False})
out=TASK/'application'/'readback.json'
out.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'productCommit':product,'productTree':tree,'commitParent':parent,'productCommitNames':names,'catalogSha256':sha(raw),'readback':str(out)},ensure_ascii=False,indent=2))
