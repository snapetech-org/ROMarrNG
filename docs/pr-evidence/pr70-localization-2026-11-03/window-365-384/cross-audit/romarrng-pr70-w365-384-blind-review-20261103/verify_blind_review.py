#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys
from collections import Counter
from pathlib import Path
O=Path(__file__).resolve().parent
I=Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w365-384-candidate-free-20261103/blind-input")
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode("utf-8")).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def ph(s): return sorted(set(re.findall(r"\{[^{}]+\}",s)))
def nums(s): return re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?![A-Za-z])",s)
def tags(s): return sorted(re.findall(r"</?[A-Za-z][^>]*>",s))
run=subprocess.run([sys.executable,str(I/"verify_blind_input.py")],capture_output=True,text=True)
assert run.returncode==0,run.stdout+run.stderr
im=j(I/"manifest.json"); m=j(O/"manifest.json")
assert m["inputManifestSha256"]==sha((I/"manifest.json").read_bytes())
assert m["inputChecksumListSha256"]==sha((I/"SHA256SUMS.txt").read_bytes())
assert (m["repository"],m["pullRequest"],m["window"],m["head"],m["tree"])==(im["repository"],im["pullRequest"],im["window"],im["head"],im["tree"])
actual={p.name for p in O.iterdir() if p.is_file()}
mf={x["path"]:x for x in m["files"]}
assert set(mf)==actual-{"manifest.json","SHA256SUMS.txt"}
for n,x in mf.items():
 b=(O/n).read_bytes(); assert len(b)==x["bytes"] and sha(b)==x["sha256"],n
sums={}
for line in (O/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 d,n=line.split(None,1); n=n.strip().lstrip("*"); assert Path(n).name==n; sums[n]=d
assert set(sums)==actual-{"SHA256SUMS.txt"}
for n,d in sums.items(): assert sha((O/n).read_bytes())==d,n
src=jl(I/"translation-prompts.jsonl"); out=jl(O/"blind-ledger.jsonl")
assert len(src)==len(out)==240
a={(x["sourceId"],x["locale"]):x for x in src}; b={}; counts=Counter(); conf=Counter()
assert len(a)==240
for r in out:
 k=(r["sourceId"],r["locale"]); assert k not in b; b[k]=r
 x=a[k]; counts[r["decision"]]+=1; conf[r["confidence"]]+=1
 for field in ("sourceId","source","sourceSha256","sourceKind","locale","language","position","sourcePlaceholderTokens","sourceNumericTokens","sourceProtectedLiterals","callerContextRefs","callerResolutionRationale","ambiguousContext","ambiguityNotes"):
  assert r[field]==x[field],(k,field)
 assert r["decision"] in ("proposal","hold") and r["rationale"]
 if r["decision"]=="proposal":
  assert isinstance(r.get("proposedTarget"),str) and r["proposedTarget"]
  t=r["proposedTarget"]
 else:
  assert "proposedTarget" not in r; t=""
 required=x["sourceProtectedLiterals"]
 phok=ph(x["source"])==ph(t); numok=nums(x["source"])==nums(t); tagok=tags(x["source"])==tags(t)
 missing=[z for z in required if z not in t]
 assert r["tokenAudit"]=={"sourcePlaceholders":ph(x["source"]),"targetPlaceholders":ph(t),"sourceNumbers":nums(x["source"]),"targetNumbers":nums(t),"sourceMarkup":tags(x["source"]),"targetMarkup":tags(t),"requiredProtectedLiterals":required,"preservedProtectedLiterals":[z for z in required if z in t],"missingProtectedLiterals":missing,"checks":{"placeholders":phok,"numeric":numok,"markup":tagok,"protectedLiterals":not missing}}
 assert phok and numok and tagok and not missing,(k,r["tokenAudit"])
assert set(a)==set(b)
assert counts==Counter({"proposal":240})
assert {b[(r["sourceId"],r["locale"])]["position"] for r in src if r["position"]==368}=={368}
amb=[r for r in out if r["position"]==368]
assert len(amb)==12 and all(r["decision"]=="proposal" and r["confidence"]=="moderate" for r in amb)
s=j(O/"summary.json")
assert s["decisionCounts"]==dict(counts) and s["proposalCount"]==240 and s["holdCount"]==0
assert s["ambiguousPosition368"]["cells"]==12 and s["ambiguousPosition368"]["decision"]=="proposal"
assert s["blindInputVerifier"]=="PASS" and s["candidateFreeOrExistingTargetsAccessed"] is False
assert m["decisionCounts"]==dict(counts) and m["proposalCount"]==240
print(json.dumps({"pass":True,"blindInputVerifier":"PASS","checksumVerifier":"PASS","cells":len(out),"decisions":dict(counts),"confidenceCounts":dict(conf),"tokenMismatches":{"placeholder":0,"numeric":0,"markup":0,"protectedLiteral":0},"ambiguousPosition368":"12 action-form proposals; moderate confidence","head":m["head"],"tree":m["tree"]},ensure_ascii=False,indent=2))
