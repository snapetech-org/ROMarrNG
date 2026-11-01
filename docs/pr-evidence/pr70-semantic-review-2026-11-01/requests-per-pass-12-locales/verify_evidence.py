#!/usr/bin/env python3
import hashlib, json, pathlib, subprocess
O=pathlib.Path(__file__).resolve().parent
W=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-pr70-head-review-20261101')
P=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-semantic-review-08689f3e')
N=pathlib.Path('/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-semantic-review-79b144e3-20261101/romarr-missing-cell-review-5808-2026-11-01.jsonl')
H='a1278acda1cea823443d7d6b712ed6ace8a99694'; T='1e8a8d4fb191490a20bc443fb2b7bf24f05fa294'; K='ui.requests-per-pass.74961b68a5'
L=['es','zh-Hans','hi','de','ja','fr','pt-BR','ar','ko','zh-Hant','vi','id']
def h(b): return hashlib.sha256(b).hexdigest()
def f(p): return h(p.read_bytes())
assert subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip()==H
assert subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD^{tree}'],text=True).strip()==T
assert not subprocess.check_output(['git','-C',str(W),'status','--porcelain'],text=True).strip()
E={'romarr/ui-labels.json':'639d2449119ea25c1f76ccd09b05bffbb87da0373dac8bbe9dcee9547ef499a2','romarr/ui-source-messages.json':'ba11bdfa7f8a282dea83d7367e1156ce716ad79aabafbdd72b7e887df647bec5','romarr/ui.py':'028e05f27f1fad6137494c85b1fa8847512a2d11db37c9fa44c4b611a2e797ad'}
assert {k:f(W/k) for k in E}==E
m=json.loads((W/'romarr/ui-labels.json').read_text())['messages'][K]
R=[json.loads(x) for x in (O/'review-input.jsonl').read_text().splitlines()]; D=[json.loads(x) for x in (O/'review-decisions.jsonl').read_text().splitlines()]
assert len(R)==len(D)==12 and [r['locale'] for r in R]==L
for r,d in zip(R,D):
 t=m['translations'][r['locale']]
 assert r['currentTarget']==t and r['source']==m['source'] and r['sourceSha256']==m['sourceHash']
 assert r['currentTargetRawUtf8Sha256']==h(t.encode()) and d['currentTargetRawUtf8Sha256']==r['currentTargetRawUtf8Sha256']
lines=(W/'romarr/ui.py').read_bytes().splitlines(keepends=True); assert h(b''.join(lines[5549:5554]))==R[0]['sourceContext']['sha256']
PM=json.loads((P/'per-pass-phrase-cells-863d4afc-manifest.json').read_text()); PB=(P/'per-pass-phrase-cells-863d4afc.jsonl').read_bytes(); assert h(PB)==PM['newPopulatedCells']['sha256']
old={r['locale']:r for r in map(json.loads,PB.decode().splitlines())}; assert [r['locale'] for r in R if r['currentTarget']!=old[r['locale']]['currentTarget']]==['es','hi']
NR=[json.loads(x) for x in N.read_text().splitlines()]; assert len(NR)==5808 and all(r['id']!=K for r in NR)
for line in (O/'SHA256SUMS.txt').read_text().splitlines():
 digest,name=line.split('  ',1); assert f(O/name)==digest,name
print('verified exact frozen head, file/context hashes, 12 cells and decisions, prior delta, disjointness, and bundle checksums')
