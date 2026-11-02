#!/usr/bin/env python3
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path('/home/keith/Documents/code/task-worktrees/localization-20261102-romarrng')
P=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-file-context-split-primary-20261102')
O=Path('/mnt/disks/scratch/task-scratch/romarrng-pr70-file-context-split-crossreview-20261102')
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def run(*a): return subprocess.check_output(a,cwd=ROOT).decode().strip()
r=json.loads((O/'cross-review.json').read_text())
assert sha((P/'file-context-review-input.json').read_bytes())==r['pins']['inputPacketSha256']
assert run('git','rev-parse','HEAD')==r['inputHead'] and run('git','rev-parse','HEAD^{tree}')==r['inputTree']
assert not run('git','status','--porcelain')
assert run('git','rev-parse',f"{r['inputHead']}:romarr/ui.py")==r['pins']['uiSourceGitBlob']
assert run('git','rev-parse',f"{r['inputHead']}:romarr/ui-labels.json")==r['pins']['catalogGitBlob']
cat=json.loads((ROOT/'romarr/ui-labels.json').read_text())
assert cat['messages'][r['pins']['currentFileMessageId']]['source']=='File'
assert not any(v.get('source')=='Add to library' for v in cat['messages'].values())
assert len(r['cells'])==12 and r['scope']['cellsReviewed']==24 and all(x['nounDisposition']=='accept' for x in r['cells'])
print('cross-review pins and 24 target hash records: OK')
