#!/usr/bin/env python3
import hashlib,json,pathlib,re,subprocess
O=pathlib.Path(__file__).resolve().parent; W=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-pr70-head-review-20261101'); P=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-semantic-review-08689f3e'); B=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-semantic-next-window-a1278acd-20261101')
H='a1278acda1cea823443d7d6b712ed6ace8a99694'; T='1e8a8d4fb191490a20bc443fb2b7bf24f05fa294'; K='ui.at.b1d6b91b67'; L=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def h(b): return hashlib.sha256(b).hexdigest()
def f(p): return h(p.read_bytes())
assert subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip()==H and subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD^{tree}'],text=True).strip()==T and not subprocess.check_output(['git','-C',str(W),'status','--porcelain'],text=True).strip()
E={'romarr/ui-labels.json':'639d2449119ea25c1f76ccd09b05bffbb87da0373dac8bbe9dcee9547ef499a2','romarr/ui-source-messages.json':'ba11bdfa7f8a282dea83d7367e1156ce716ad79aabafbdd72b7e887df647bec5','romarr/ui.py':'028e05f27f1fad6137494c85b1fa8847512a2d11db37c9fa44c4b611a2e797ad'}; assert {k:f(W/k) for k in E}==E
R=[json.loads(x) for x in (O/'review-input.jsonl').read_text().splitlines()]; D=[json.loads(x) for x in (O/'review-decisions.jsonl').read_text().splitlines()]; assert len(R)==len(D)==12 and [r['locale'] for r in R]==L
M=json.loads((W/'romarr/ui-labels.json').read_text())['messages']; assert len(M['ui.requests-per-pass.74961b68a5']['translations'])==len(M['ui.at.b1d6b91b67']['translations'])==12
for r,d in zip(R,D):
 l=r['locale']; assert r['atCell']['target']==M[K]['translations'][l] and r['perPassCell']['target']==M['ui.per-pass.7a11c39217']['translations'][l] and r['currentNumericLabelCell']['target']==M['ui.requests-per-pass.74961b68a5']['translations'][l]
 assert r['atCell']['targetRawUtf8Sha256']==h(r['atCell']['target'].encode()) and r['currentNumericLabelCell']['targetRawUtf8Sha256']==h(r['currentNumericLabelCell']['target'].encode())
 assert d['locale']==l and d['atCellDisposition']=='not_referenced_by_current_ui_source' and d['currentNumericLabelDisposition']=='accepted_unchanged'
U=(W/'romarr/ui.py').read_bytes(); lines=U.splitlines(keepends=True); assert h(b''.join(lines[5551:5558]))==R[0]['sourceContext']['sha256']
unc=[json.loads(x) for x in (P/'uncertain-cells.jsonl').read_text().splitlines() if json.loads(x).get('sourceId')==K]; assert len(unc)==12 and {x['locale'] for x in unc}==set(L)
adj=[json.loads(x) for x in (P/'moderate-uncertain-adjudication.jsonl').read_text().splitlines() if json.loads(x).get('sourceId')==K]; assert len(adj)==12
prev=json.loads((B/'manifest.json').read_text()); assert prev['reviewedHead']==H and prev['window']['cells']==12
for line in (B/'SHA256SUMS.txt').read_text().splitlines():
 q,n=line.split('  ',1); assert f(B/n)==q
for line in (O/'SHA256SUMS.txt').read_text().splitlines():
 q,n=line.split('  ',1); assert f(O/n)==q,n
print('verified exact head, frozen hashes, 12-locale inputs/decisions, prior overlap, and artifact checksums')
