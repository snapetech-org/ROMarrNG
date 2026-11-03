#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess,sys
O=Path(__file__).resolve().parent
I=O/"romarrng-pr70-w365-384-candidate-free-20261103"/"input"
P=O/"romarrng-pr70-w365-384-primary-20261103"/"primary-review"
B=O/"romarrng-pr70-w365-384-blind-review-20261103"
HEAD="d1698b94781c3c84e91faf03c75e8c308dc39c34"; TREE="3f42d41fe4bbb8edd921ff161e8298ca66038a91"
PH=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUM=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
TAG=re.compile(r"</?[A-Za-z][^>]*>")
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else x.encode("utf-8")).hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def ck(ok,msg):
 if not ok: raise SystemExit("FAIL: "+msg)
files={p.relative_to(O).as_posix():p for p in O.rglob("*") if p.is_file() and p.relative_to(O).as_posix()!="SHA256SUMS.txt"}
sums={}
for line in (O/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 d,n=line.split("  ",1); sums[n]=d
ck(set(sums)=={p.relative_to(O).as_posix() for p in O.rglob("*") if p.is_file() and p.relative_to(O).as_posix()!="SHA256SUMS.txt"},"checksum inventory")
for n,d in sums.items(): ck(sha((O/n).read_bytes())==d,"checksum "+n)
m=j(O/"manifest.json")
ck(m["head"]==HEAD and m["tree"]==TREE,"manifest exact head/tree")
for n,x in m["fileHashes"].items():
 ck(n in files and sha(files[n].read_bytes())==x["sha256"] and len(files[n].read_bytes())==x["bytes"],"manifest file pin "+n)
ck(set(m["fileHashes"])==set(files)-{"manifest.json"},"manifest file inventory")
att=j(O/"live-pr-attestation.json")
ck(att["headRefOid"]==att["liveBranchRefOid"]==att["livePullRefOid"]==HEAD and att["headTree"]==TREE and att["state"]=="OPEN","live PR attestation")
subprocess.run([sys.executable,str(I/"verify_input.py")],check=True,capture_output=True,text=True)
subprocess.run([sys.executable,str(P/"verify_primary.py")],check=True,capture_output=True,text=True)
blind_sums={}
for line in (B/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 d,n=line.split("  ",1); blind_sums[n]=d
ck(set(blind_sums)=={x.name for x in B.iterdir() if x.is_file() and x.name!="SHA256SUMS.txt"},"blind checksum inventory")
for n,d in blind_sums.items(): ck(sha((B/n).read_bytes())==d,"blind checksum "+n)
im=j(I/"manifest.json"); pm=j(P/"manifest.json"); bm=j(B/"manifest.json")
ck(im["head"]==pm["head"]==bm["head"]==HEAD and im["tree"]==pm["tree"]==bm["tree"]==TREE,"evidence head/tree")
cells=jl(I/"current-target-cells.jsonl"); contexts=jl(I/"source-contexts.jsonl")
primary=jl(P/"review-decisions.jsonl"); blind=jl(B/"blind-ledger.jsonl")
ledger=jl(O/"resolution-ledger.jsonl"); holds=jl(I/"prior-hold-reattestation.jsonl")
ck(len(cells)==len(primary)==len(blind)==len(ledger)==240,"240 cell coverage")
ck(len(holds)==288 and all(x["targetUnchanged"] and x["sourceMatchesCurrentQueue"] and x["positionMatchesCurrentQueue"] for x in holds),"288 prior holds unchanged")
cm={(x["position"],x["locale"]):x for x in cells}; pm={(x["position"],x["locale"]):x for x in primary}; bm={(x["position"],x["locale"]):x for x in blind}
cx={x["position"]:x for x in contexts}; seen=set(); resolutions=Counter(); dispositions=Counter(); locale_disagreements=Counter()
for r in ledger:
 k=(r["position"],r["locale"]); ck(k in cm and k not in seen,"ledger key "+str(k)); seen.add(k)
 c=cm[k]; p=pm[k]; b=bm[k]
 ck(r["sourceId"]==c["sourceId"]==p["sourceId"]==b["sourceId"] and r["sourceSha256"]==c["sourceSha256"]==p["sourceSha256"]==b["sourceSha256"],"source lineage "+str(k))
 ck(r["currentTarget"]==c["currentTarget"] and r["currentTargetSha256"]==c["currentTargetSha256"],"current target lineage "+str(k))
 ck(r["callerContextSha256"]==c["callerContextSha256"]==p["callerContextSha256"],"caller context lineage "+str(k))
 ck(r["primaryTarget"]==p["selectedTarget"] and r["primaryTargetSha256"]==p["selectedTargetSha256"],"primary value lineage "+str(k))
 ck(r["blindTarget"]==b["proposedTarget"] and r["blindTargetSha256"]==sha(b["proposedTarget"]),"blind value lineage "+str(k))
 ck(r["targetsAgree"]==(p["selectedTarget"]==b["proposedTarget"]),"agreement flag "+str(k))
 ck(r["selectedTargetSha256"]==sha(r["selectedTarget"]),"selected target hash "+str(k))
 ck(r["resolutionRationale"] and r["crossAuditConfidence"]=="moderate" and r["nativeSpeakerApproved"] is False,"adjudication record "+str(k))
 origin=r["resolution"]
 if origin=="agreement": ck(r["selectedTarget"]==p["selectedTarget"]==b["proposedTarget"] and r["targetsAgree"],"agreement selection "+str(k))
 elif origin=="primary_selected": ck(r["selectedTarget"]==p["selectedTarget"] and not r["targetsAgree"],"primary resolution "+str(k))
 elif origin=="blind_selected": ck(r["selectedTarget"]==b["proposedTarget"] and not r["targetsAgree"],"blind resolution "+str(k))
 else: ck(False,"unknown resolution "+str(k))
 ck(r["selectedDisposition"] in ("accept-current","correction","refinement"),"disposition "+str(k))
 if r["selectedDisposition"]=="accept-current": ck(r["selectedTarget"]==c["currentTarget"],"accept-current mismatch "+str(k))
 else: ck(r["selectedTarget"]!=c["currentTarget"],"changed-target disposition "+str(k))
 t=r["selectedTarget"]; phs=sorted(PH.findall(c["source"])); pht=sorted(PH.findall(t)); ns=NUM.findall(c["source"]); nt=NUM.findall(t)
 required=c["sourceProtectedLiterals"]
 missing=[x for x in required if not re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",t)]
 tags=sorted(TAG.findall(t)); checks=r["tokenAndMarkupChecks"]
 ck(phs==pht and checks["placeholderMultisetPreserved"],"placeholder check "+str(k))
 ck(ns==nt and checks["numberSequencePreserved"],"numeric check "+str(k))
 ck(not missing and checks["protectedLiteralsPreserved"],"protected literal check "+str(k))
 ck(not TAG.search(t) and not tags and checks["noUnexpectedMarkup"] and checks["callerMarkupBoundaryPreserved"],"markup check "+str(k))
 ck(checks["sourcePlaceholders"]==phs and checks["selectedPlaceholders"]==pht and checks["sourceNumbers"]==ns and checks["selectedNumbers"]==nt and checks["requiredProtectedLiterals"]==required and checks["missingProtectedLiterals"]==missing,"token evidence "+str(k))
 resolutions[origin]+=1; dispositions[r["selectedDisposition"]]+=1
 if not r["targetsAgree"]: locale_disagreements[k[1]]+=1
ck(seen==set(cm),"ledger completeness")
ck(resolutions==Counter({"agreement":74,"primary_selected":154,"blind_selected":12}),"resolution counts")
ck(sum(locale_disagreements.values())==166,"disagreement count")
s=j(O/"summary.json")
ck(dispositions==Counter(s["selectedDispositionCounts"]),"disposition summary")
ck(len([r for r in ledger if r["position"]==368])==12 and all(r["crossAuditConfidence"]=="moderate" for r in ledger if r["position"]==368),"dual-use position 368 review")
ck(not any(r["selectedDisposition"]=="hold" for r in ledger),"selected-window holds")
ck(s["cellCount"]==240 and s["primaryBlindTargetAgreements"]==74 and s["primaryBlindTargetDisagreements"]==166,"summary counts")
ck(s["priorHoldsReattestedUnchanged"]==288 and s["priorHoldsPreserved"] is True and s["selectedWindowHolds"]==0,"summary holds")
print(json.dumps({"pass":True,"head":HEAD,"tree":TREE,"cells":len(ledger),"agreements":74,"disagreements":166,"resolutionCounts":dict(resolutions),"selectedDispositions":dict(dispositions),"priorHoldsPreserved":288,"selectedWindowHolds":0,"checksumVerifier":"PASS","inputVerifier":"PASS","primaryVerifier":"PASS","blindChecksumVerifier":"PASS"},ensure_ascii=False,indent=2))
