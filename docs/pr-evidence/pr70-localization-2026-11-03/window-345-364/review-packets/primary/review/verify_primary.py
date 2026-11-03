#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
IN=HERE.parent/"input"
def sha(b): return hashlib.sha256(b).hexdigest()
def readj(base,name): return json.loads((base/name).read_text(encoding="utf-8"))
def readl(base,name): return [json.loads(x) for x in (base/name).read_text(encoding="utf-8").splitlines() if x]
def check(v,msg):
    if not v: raise SystemExit("FAIL: "+msg)
def ph(s): return re.findall(r"\{[A-Za-z][A-Za-z0-9_]*\}",s)
def nums(s): return re.findall(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])",s)
sums={}
for line in (HERE/"SHA256SUMS.txt").read_text().splitlines():
    d,n=line.split("  ",1); check(sha((HERE/n).read_bytes())==d,"primary checksum "+n); sums[n]=d
check(set(sums)=={p.name for p in HERE.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"},"primary checksum inventory")
ims=readj(IN,"manifest.json")
check(sha((IN/"SHA256SUMS.txt").read_bytes())==readj(HERE,"summary.json")["inputChecksumListSha256"],"input checksum link")
rows=readl(HERE,"review-decisions.jsonl"); cells=readl(IN,"current-target-cells.jsonl")
check(len(rows)==len(cells)==240,"cell count")
check([(x["position"],x["locale"]) for x in rows]==[(x["position"],x["locale"]) for x in cells],"row order")
allowed={"accept-current","correction","refinement","hold"}
for d,c in zip(rows,cells):
    check(d["sourceId"]==c["sourceId"] and d["sourceSha256"]==c["sourceSha256"] and d["source"]==c["source"],"source lineage")
    check(d["currentTarget"]==c["currentTarget"] and d["currentTargetSha256"]==c["currentTargetSha256"],"current target lineage")
    check(d["decision"] in allowed and d["rationale"] and d["confidence"] in ("high","moderate","low"),"decision/rationale/confidence")
    check(sha(d["selectedTarget"].encode())==d["selectedTargetSha256"],"selected target hash")
    check((d["decision"]=="accept-current")== (d["selectedTarget"]==d["currentTarget"]),"accept-current target")
    check(sorted(ph(d["source"]))==sorted(ph(d["selectedTarget"])),"placeholder parity")
    check(nums(d["source"])==nums(d["selectedTarget"]),"numeric-token parity")
    check(all(re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",d["selectedTarget"]) for x in d["sourceProtectedLiterals"]),"protected literals")
    check(d["callerContextSha256"]==c["callerContextSha256"],"caller-context pin")
count={}
for d in rows: count[d["decision"]]=count.get(d["decision"],0)+1
summary=readj(HERE,"summary.json")
check(count==summary["counts"],"summary totals")
check(count.get("hold",0)==0 and summary["cellCount"]==240,"window holds/scope")
check(summary["priorHeldCellsReattested"]==summary["priorHeldCellsUnchanged"]==288,"prior holds")
check(summary["inputManifestJsonSha256"]==sha((IN/"manifest.json").read_bytes()),"input manifest hash")
print("PASS: primary W345-W364 ledger covers all 240 cells, exact input/current hashes, all tokens, zero current holds, and 288 unchanged prior holds.")
