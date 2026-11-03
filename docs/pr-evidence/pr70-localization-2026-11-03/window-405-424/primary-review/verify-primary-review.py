#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent
DEFAULT_INPUT=HERE.parents[1]/"romarrng-pr70-w405-424-candidate-free-20261103"/"input"
def sha(b):return hashlib.sha256(b).hexdigest()
def j(path):return json.loads(path.read_text(encoding="utf-8"))
def l(path):return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
def ok(x,m):
 if not x: raise SystemExit("FAIL: "+m)
ap=argparse.ArgumentParser(); ap.add_argument("--candidate-free",type=Path,default=DEFAULT_INPUT); args=ap.parse_args(); inp=args.candidate_free.resolve()
sums={}
for line in (HERE/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 d,n=line.split("  ",1); ok(sha((HERE/n).read_bytes())==d,"checksum "+n); sums[n]=d
ok(set(sums)=={p.name for p in HERE.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"},"checksum inventory")
res=subprocess.run([sys.executable,str(inp/"verify_input.py")],capture_output=True,text=True)
ok(res.returncode==0,"candidate-free verifier: "+res.stdout+res.stderr)
meta=j(HERE/"input-verification.json"); m=j(inp/"manifest.json")
ok(meta["candidateFreeInputPath"]==str(inp) and meta["candidateFreeInputManifestSha256"]==sha((inp/"manifest.json").read_bytes()) and meta["candidateFreeInputChecksumListSha256"]==sha((inp/"SHA256SUMS.txt").read_bytes()),"candidate-free input seal")
ok(meta["head"]==m["head"]=="c146189f29db8fbd77d68dff0c33a0ab59a6b601" and meta["tree"]==m["tree"]=="3db10f8b87577edd1167e4489524e6afbb50d556","exact PR head/tree")
ledger=l(HERE/"review-ledger.jsonl"); decisions=l(HERE/"review-decisions.jsonl"); cells=l(inp/"current-target-cells.jsonl")
ok(len(ledger)==len(decisions)==len(cells)==240,"review coverage")
valid={"accept-current","correction","refinement","hold"}; counts={x:0 for x in valid}
ph=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}"); nums=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
for i,(r,c,d) in enumerate(zip(ledger,cells,decisions)):
 ok((r["position"],r["locale"],r["sourceId"],r["sourceSha256"],r["currentTargetSha256"])==(c["position"],c["locale"],c["sourceId"],c["sourceSha256"],c["currentTargetSha256"]),"exact current cell/hash at row "+str(i))
 ok(r["currentTarget"]==c["currentTarget"] and r["callerContextSha256"]==c["callerContextSha256"],"target/context pin at row "+str(i))
 k=r["disposition"]; ok(k in valid,"valid disposition"); counts[k]+=1
 ok(d["disposition"]==k and d["currentTargetSha256"]==r["currentTargetSha256"],"decision ledger agrees")
 proposed=r["proposedTarget"]
 if k in ("accept-current","hold"):
  ok(proposed is None and r["proposedTargetSha256"] is None,"no proposal for accept/hold")
 else:
  ok(isinstance(proposed,str) and proposed!=r["currentTarget"],"changed target proposal")
  ok(sha(proposed.encode())==r["proposedTargetSha256"],"proposal hash")
  ok(sorted(ph.findall(r["source"]))==sorted(ph.findall(proposed))==sorted(r["sourcePlaceholderTokens"]),"proposal placeholders")
  ok(nums.findall(r["source"])==nums.findall(proposed)==r["sourceNumericTokens"],"proposal numeric tokens")
  ok(all(t in proposed for t in r["protectedLiterals"]) and r["proposedProtectedLiteralsPreserved"],"proposal protected literals")
 if k=="hold":ok(r["position"] in [405,407,408,416] and r["proposedTarget"] is None,"exact hold scope")
expected={"accept-current":164,"correction":21,"refinement":7,"hold":48}
ok(counts==expected,"disposition counts "+str(counts))
summary=j(HERE/"summary.json")
ok(summary["dispositionCounts"]==expected and summary["changeCount"]==28 and summary["holdPositions"]==[405,407,408,416],"summary counts")
ok(summary["carriedHoldsUnchanged"] and summary["nativeSpeakerReviewPerformed"] is False and summary["browserReviewPerformed"] is False,"review boundary/hold evidence")
print("PASS primary W405-W424: candidate-free input verifies; 240 exact-hash decisions; 164 accept-current, 21 corrections, 7 refinements, 48 holds; all proposals pass placeholder/numeric/protected-literal checks; carried 288 holds unchanged.")
