#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=pathlib.Path,required=True); a=ap.parse_args()
    rows={}
    for line in (ROOT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); p=(ROOT/n).resolve()
        if not p.is_relative_to(ROOT.resolve()) or not p.is_file() or sha(p)!=h: raise SystemExit('FAIL: bundle checksum '+n)
        if n in rows: raise SystemExit('FAIL: duplicate checksum '+n)
        rows[n]=h
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p!=ROOT/'SHA256SUMS.txt'}
    if set(rows)!=actual: raise SystemExit('FAIL: bundle checksum coverage')
    m=json.loads((ROOT/'bundle-manifest.json').read_text(encoding='utf-8'))
    im=json.loads((ROOT/'candidate-free/input/manifest.json').read_text(encoding='utf-8'))
    if (m.get('head'),m.get('tree'),m.get('window'))!=(im.get('head'),im.get('tree'),im.get('window')): raise SystemExit('FAIL: bundle/input pin')
    if set(m.get('files',[]))!=actual-{'bundle-manifest.json'}: raise SystemExit('FAIL: bundle file manifest')
    subprocess.run([sys.executable,str(ROOT/'candidate-free/input/verify_input.py'),'--repo',str(a.repo.resolve())],check=True)
    print(json.dumps({'result':'PASS','bundleFiles':len(rows),'head':m['head'],'tree':m['tree'],'window':m['window'],'sources':m['sourceCount'],'cells':m['cellCount'],'priorSelectedSources':m['priorSelectedSourceCount'],'priorHolds':m['priorHoldCellCount'],'priorAppliedCells':m['priorAppliedCellCount']},sort_keys=True))
if __name__=='__main__': main()
