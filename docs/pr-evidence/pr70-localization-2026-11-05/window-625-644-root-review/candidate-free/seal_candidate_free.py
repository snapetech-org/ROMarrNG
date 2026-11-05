#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; INPUT=ROOT/'candidate-free/input'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def sums(root,name):
    rows=[]
    for p in sorted(x for x in root.rglob('*') if x.is_file() and x!=root/name): rows.append(f'{sha(p)}  {p.relative_to(root).as_posix()}')
    (root/name).write_text('\n'.join(rows)+'\n',encoding='utf-8')
m=json.loads((INPUT/'manifest.json').read_text()); m['files']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(INPUT.iterdir()) if p.is_file() and p.name not in ('manifest.json','SHA256SUMS.txt')]; dump(INPUT/'manifest.json',m); sums(INPUT,'SHA256SUMS.txt')
b={'artifact':'ROMarrNG PR #70 W625-W644 candidate-free bundle','repository':m['repository'],'pullRequest':70,'branch':m['branch'],'head':m['head'],'tree':m['tree'],'window':m['window'],'sourceCount':m['sourceCount'],'localeCount':m['localeCount'],'cellCount':m['cellCount'],'callerlessSourceCount':m['callerlessSourceCount'],'callerlessCurrentTargetCellCount':m['callerlessCurrentTargetCellCount'],'directCallerRefCount':m['directCallerRefCount'],'priorSelectedSourceCount':m['priorSelectedSourceCount'],'priorHoldCellCount':m['priorHoldCellCount'],'priorAppliedCellCount':m['priorAppliedSelectedCellCount'],'inputManifestSha256':sha(INPUT/'manifest.json'),'files':sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p not in (ROOT/'bundle-manifest.json',ROOT/'SHA256SUMS.txt'))}; dump(ROOT/'bundle-manifest.json',b); sums(ROOT,'SHA256SUMS.txt')
print(json.dumps({'result':'SEALED','head':m['head'],'tree':m['tree'],'window':m['window'],'sources':m['sourceCount'],'cells':m['cellCount'],'callerlessSources':m['callerlessSourceCount'],'bundleFiles':len(b['files'])+2,'inputManifestSha256':b['inputManifestSha256']},sort_keys=True))
