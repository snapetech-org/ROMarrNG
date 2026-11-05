#!/usr/bin/env python3
import hashlib,json,subprocess
from pathlib import Path
TASK=Path(__file__).resolve().parents[1]
REPO=Path('/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685')
INPUT='68c5c9d4ad13ad5d02b9c455f429d8a5149d363d'
CAT='romarr/ui-labels.json'
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
def sha(b): return hashlib.sha256(b).hexdigest()
commit=git('rev-parse','HEAD'); parent=git('rev-parse','HEAD^'); tree=git('rev-parse','HEAD^{tree}')
assert parent==INPUT,(parent,INPUT)
names=git('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines()
assert CAT in names
raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{commit}:{CAT}'])
p=TASK/'application/readback-before-commit.json'; data=json.loads(p.read_text(encoding='utf-8'))
assert sha(raw)==data['catalogSha256After']
data.update({'productCommit':commit,'productTree':tree,'commitParent':parent,'productCommitNames':names,'productCommitPending':False})
out=TASK/'application/readback.json'; out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','productCommit':commit,'productTree':tree,'commitParent':parent,'catalogSha256':sha(raw),'productCommitNames':names,'readback':str(out)},ensure_ascii=False,indent=2))
