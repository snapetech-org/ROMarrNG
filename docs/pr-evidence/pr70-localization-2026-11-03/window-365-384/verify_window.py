#!/usr/bin/env python3
from pathlib import Path
import collections
import hashlib
import json
import subprocess
import sys

E=Path(__file__).resolve().parent
REPO=E.parents[3]
BASE='d1698b94781c3c84e91faf03c75e8c308dc39c34'
TREE='3f42d41fe4bbb8edd921ff161e8298ca66038a91'
BRANCH='task/localization-translation-review-20261030'
MODES={'--precommit','--prepush','--evidence','--postpush'}
mode=sys.argv[1] if len(sys.argv)>1 else '--postpush'
assert mode in MODES,mode

def run(args,cwd=None):
 return subprocess.check_output(args,cwd=cwd or REPO,text=True).strip()

def sha(b):
 return hashlib.sha256(b).hexdigest()

def thash(v):
 encoded=json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
 return sha(encoded.encode('utf-8'))

def rows(path):
 return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def verify_sums(folder,name='SHA256SUMS.txt'):
 for line in (folder/name).read_text(encoding='utf-8').splitlines():
  if line.strip():
   digest,filename=line.split(None,1)
   filename=filename.strip().lstrip('*')
   assert sha((folder/filename).read_bytes())==digest,(folder/filename,'checksum')

def verify_root_sums():
 for line in (E/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
  if line.strip():
   digest,filename=line.split(None,1)
   filename=filename.strip().lstrip('*')
   assert sha((E/filename).read_bytes())==digest,(E/filename,'root checksum')

I=E/'candidate-free-input'
P=E/'primary-review'
B=E/'blind-review'
BI=B/'blind-input'
X=E/'cross-audit'
verify_sums(I)
verify_sums(P)
verify_sums(B)
verify_sums(BI)
verify_sums(X)
ALIAS=E.parent/'romarrng-pr70-w365-384-candidate-free-20261103'/'input'
assert ALIAS.is_dir()
for rel in sorted(p.relative_to(I) for p in I.rglob('*') if p.is_file()):
 assert (I/rel).read_bytes()==(ALIAS/rel).read_bytes(),rel
for folder,script in [(I,'verify_input.py'),(ALIAS,'verify_input.py'),(P,'verify_primary.py'),(BI,'verify_blind_input.py'),(B,'verify_blind_review.py'),(X,'verify_cross_audit.py')]:
 subprocess.run([sys.executable,script],cwd=folder,check=True,capture_output=True,text=True)
im=json.loads((I/'manifest.json').read_text())
pm=json.loads((P/'manifest.json').read_text())
bm=json.loads((B/'manifest.json').read_text())
xm=json.loads((X/'manifest.json').read_text())
assert (im['head'],im['tree'])==(BASE,TREE)
assert (pm['head'],pm['tree'])==(BASE,TREE)
assert (bm['head'],bm['tree'])==(BASE,TREE)
assert (xm['head'],xm['tree'])==(BASE,TREE)
plan=json.loads((E/'apply-plan.json').read_text())
assert (plan['baseHead'],plan['baseTree'],plan['reviewedCells'])==(BASE,TREE,240)
cells=rows(I/'current-target-cells.jsonl')
cross=rows(X/'resolution-ledger.jsonl')
allplan=plan['allCellReadbackPlan']
assert len(cells)==len(cross)==len(allplan)==240
key=lambda x:(x['position'],x['locale'])
ci={key(x):x for x in cells}
xi={key(x):x for x in cross}
pi={key(x):x for x in allplan}
assert ci.keys()==xi.keys()==pi.keys()
decisions=collections.Counter(x['selectedDisposition'] for x in cross)
resolutions=collections.Counter(x['resolution'] for x in cross)
assert decisions==collections.Counter({'accept-current':125,'correction':75,'refinement':40})
assert resolutions==collections.Counter({'agreement':74,'primary_selected':154,'blind_selected':12})
assert len(plan['updates'])==115 and sum(x['changed'] for x in allplan)==115
assert plan['priorHoldsExpected']==288 and plan['newHolds']==0
for k,c in ci.items():
 x=xi[k];p=pi[k]
 assert (x['sourceId'],x['source'],x['sourceSha256'],x['currentTarget'],x['currentTargetSha256'],x['callerContextSha256'])==(
   c['sourceId'],c['source'],c['sourceSha256'],c['currentTarget'],c['currentTargetSha256'],c['callerContextSha256'])
 assert p['selectedTarget']==x['selectedTarget']
 assert p['selectedTargetSha256']==sha(p['selectedTarget'].encode())
 assert p['selectedTarget']==c['currentTarget'] if p['selectedDisposition']=='accept-current' else p['selectedTarget']!=c['currentTarget']
 assert p['selectedTargetSha256']==sha(p['selectedTarget'].encode())
assert {k for k,x in pi.items() if x['callerContextAmbiguous']}=={(368,l) for l in ['ar','de','es','fr','hi','id','ja','ko','pt-BR','vi','zh-Hans','zh-Hant']}
catalog_path='romarr/ui-labels.json'
raw=subprocess.check_output(['git','show',f'{BASE}:{catalog_path}'],cwd=REPO)
pins=json.loads((I/'catalog-file-pins.json').read_text())
assert sha(raw)==pins['catalogSha256']==plan['catalogFileSha256']
baseline=json.loads(raw.decode('utf-8'))
assert raw.decode('utf-8')==json.dumps(baseline,ensure_ascii=False,indent=2)+'\n'
current=json.loads((REPO/catalog_path).read_text(encoding='utf-8'))
assert list(current)==list(baseline)
selected={(x['sourceId'],x['locale']):x for x in allplan}
expected=json.loads(raw.decode('utf-8'))
for row in allplan:
 sid=row['sourceId'];loc=row['locale'];entry=expected['messages'][sid]
 assert entry['translations'][loc]==row['currentTarget']
 assert sha(entry['translations'][loc].encode())==row['currentTargetSha256']
 assert thash(entry['translations'][loc])==row['catalogTranslationHash']
 if row['changed']:
  entry['translations'][loc]=row['selectedTarget']
  entry['translationHashes'][loc]=thash(row['selectedTarget'])
for row in allplan:
 entry=expected['messages'][row['sourceId']]
 assert current['messages'][row['sourceId']]['translations'][row['locale']]==row['selectedTarget']
 assert current['messages'][row['sourceId']]['translationHashes'][row['locale']]==thash(row['selectedTarget'])
assert current==expected
prior=rows(I/'prior-hold-reattestation.jsonl')
assert len(prior)==288
for h in prior:
 value=current['messages'][h['sourceId']]['translations'][h['locale']]
 assert sha(value.encode())==h['currentTargetSha256']==h['priorCurrentTargetSha256']
assert list(current)==list(baseline)
for sid,record in baseline['messages'].items():
 assert list(current['messages'][sid])==list(record)
 assert list(current['messages'][sid]['translations'])==list(record['translations'])
 assert list(current['messages'][sid]['translationHashes'])==list(record['translationHashes'])
evidence_prefix='docs/pr-evidence/pr70-localization-2026-11-03/'
allowed={catalog_path}
def allowed_path(path): return path in allowed or path.startswith(evidence_prefix)
diff=set(filter(None,run(['git','diff','--name-only',BASE]).splitlines()))
assert all(allowed_path(p) for p in diff),sorted(diff)
assert not any(p.startswith('.github/workflows/') for p in diff)
check=subprocess.run(['git','-C',str(REPO),'diff','--check',BASE],capture_output=True,text=True)
diff_warnings=(check.stdout+check.stderr).strip().splitlines()
if check.returncode:
 assert len(diff_warnings)==1 and 'cross-audit/build_cross_audit.py:' in diff_warnings[0] and diff_warnings[0].endswith('new blank line at EOF.'),diff_warnings
 diff_check='PASS except sealed cross-audit builder EOF whitespace'
else:
 diff_check='PASS'
status=run(['git','status','--porcelain','--untracked-files=all']).splitlines()
status_paths=[line[2:].strip() for line in status]
assert all(allowed_path(p) for p in status_paths),status
head=run(['git','rev-parse','HEAD']);tree=run(['git','rev-parse','HEAD^{tree}'])
pr=json.loads(run(['gh','api','repos/snapetech-org/romarrng/pulls/70']))
assert (pr['state'],pr['draft'],pr['head']['ref'],pr['base']['ref'])==('open',True,BRANCH,'main')
refs_text=run(['git','ls-remote','https://github.com/snapetech-org/romarrng.git',f'refs/heads/{BRANCH}','refs/pull/70/head'])
refs={line.split()[1]:line.split()[0] for line in refs_text.splitlines() if line.strip()}
remote_branch=refs[f'refs/heads/{BRANCH}'];remote_pr=refs['refs/pull/70/head']
if mode=='--precommit':
 assert head==BASE and tree==TREE
 assert pr['head']['sha']==BASE and remote_branch==remote_pr==BASE
 assert catalog_path in status_paths
elif mode=='--prepush':
 assert run(['git','rev-parse',f'{head}^'])==BASE and not status
 assert pr['head']['sha']==BASE and remote_branch==remote_pr==BASE
elif mode=='--evidence':
 av=json.loads((E/'application-verification.json').read_text())
 assert head==av['applicationCommit'] and pr['head']['sha']==head and remote_branch==remote_pr==head
 assert all(p.startswith(evidence_prefix) for p in status_paths),status
 verify_root_sums()
else:
 assert pr['head']['sha']==head and remote_branch==remote_pr==head and not status
 verify_root_sums()
 av=json.loads((E/'application-verification.json').read_text())
 applied=av['applicationCommit']
 assert applied in run(['git','rev-list',f'{BASE}..{head}']).split()
 assert run(['git','rev-parse',f'{applied}^{{tree}}'])==av['applicationTree']
 assert av['livePullRequestHead']==applied and av['branch']==BRANCH
 assert av['catalogFileSha256']==sha((REPO/catalog_path).read_bytes())
print(json.dumps({'pass':True,'mode':mode,'base':BASE,'head':head,'tree':tree,'cells':240,'decisions':dict(decisions),'crossAuditResolutions':dict(resolutions),'updates':115,'priorHoldsPreserved':288,'newHolds':0,'rank368Reviewed':12,'nonTargetChanges':0,'workflowFilesTouched':False,'diffCheck':diff_check,'pr':'OPEN/DRAFT'},indent=2))
