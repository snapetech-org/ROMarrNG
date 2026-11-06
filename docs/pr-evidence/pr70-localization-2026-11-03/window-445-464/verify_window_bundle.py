#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def fail(x):raise SystemExit("FAIL: "+x)
sums={}
for line in (ROOT/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 if line.strip():
  d,p=line.split("  ",1)
  if p in sums:fail("duplicate checksum "+p)
  sums[p]=d
actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p!=ROOT/"SHA256SUMS.txt"}
if actual!=set(sums):fail("bundle checksum inventory mismatch")
for p,d in sums.items():
 if sha((ROOT/p).read_bytes())!=d:fail("bundle checksum mismatch "+p)
m=json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))
records={x["path"]:x for x in m["files"]}
if set(records)!=actual-{"manifest.json"}:fail("bundle manifest inventory mismatch")
for p,x in records.items():
 raw=(ROOT/p).read_bytes()
 if len(raw)!=x["sizeBytes"] or sha(raw)!=x["sha256"]:fail("bundle manifest mismatch "+p)
checks=[(ROOT/"cross-audit"/"source-packet",["python3","verify_cross_audit.py"]),(ROOT/"application",["python3","verify_apply.py"])]
for folder,cmd in checks:
 r=subprocess.run(cmd,cwd=folder,text=True,capture_output=True)
 if r.returncode:fail("sub-verifier failed at "+str(folder)+": "+r.stdout+r.stderr)
print(json.dumps({"status":"PASS","bundleFiles":len(sums),"manifestFiles":len(records),"crossAudit":"PASS","application":"PASS","reviewedCells":240,"selectedChanges":21},indent=2))
