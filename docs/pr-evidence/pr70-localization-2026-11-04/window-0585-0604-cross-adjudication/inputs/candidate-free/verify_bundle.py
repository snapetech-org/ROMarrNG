#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',type=pathlib.Path,required=True); args=ap.parse_args()
    sums=ROOT/'SHA256SUMS.txt'; rows={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        h,n=line.split('  ',1); p=(ROOT/n).resolve()
        if not p.is_relative_to(ROOT.resolve()) or not p.is_file(): raise SystemExit('FAIL: unsafe/missing bundle file '+n)
        if sha(p)!=h: raise SystemExit('FAIL: bundle checksum '+n)
        rows[n]=h
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p!=sums}
    if set(rows)!=actual: raise SystemExit('FAIL: bundle checksum coverage')
    m=json.loads((ROOT/'bundle-manifest.json').read_text(encoding='utf-8'))
    im=json.loads((ROOT/'candidate-free/input/manifest.json').read_text(encoding='utf-8'))
    if (m['head'],m['tree'],m['window'])!=(im['head'],im['tree'],im['window']): raise SystemExit('FAIL: bundle/input pin mismatch')
    subprocess.run([sys.executable,str(ROOT/'candidate-free/input/verify_input.py'),'--repo',str(args.repo.resolve())],check=True)
    print(json.dumps({'result':'PASS','bundleFiles':len(rows),'head':m['head'],'tree':m['tree'],'sourceCount':m['sourceCount'],'cellCount':m['cellCount'],'callerlessSources':m['callerlessSourceCount'],'callerlessCells':m['callerlessCurrentTargetCellCount'],'directCallerRefs':m['directCallerRefCount'],'priorSelectedSources':m['priorSelectedSourceCount'],'priorHashOnlyHolds':m['priorHoldCellCount'],'priorAppliedCells':m['priorAppliedSelectedCellCount']},sort_keys=True))
if __name__=='__main__': main()
