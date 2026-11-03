#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
INPUT=HERE.parent/"../romarrng-pr70-w365-384-candidate-free-20261103/input"
INPUT=INPUT.resolve()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canon(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def readj(path):
    return json.loads(path.read_text(encoding="utf-8"))

def readl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

def check(value,message):
    if not value:
        raise SystemExit("FAIL: "+message)

# Verify the candidate-free input before consuming it.
subprocess.run(["python3",str(INPUT/"verify_input.py")],check=True,stdout=subprocess.PIPE,text=True)
sums={}
for line in (HERE/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    digest,name=line.split("  ",1)
    check(sha((HERE/name).read_bytes())==digest,"review checksum "+name)
    sums[name]=digest
actual_files={p.name for p in HERE.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"}
check(set(sums)==actual_files,"review checksum inventory")
check(not any("blind" in n.lower() for n in sums),"blind material boundary")

input_manifest=readj(INPUT/"manifest.json")
input_attestation=readj(INPUT/"PR-attestation.json")
summary=readj(HERE/"summary.json")
manifest=readj(HERE/"manifest.json")
check(manifest["head"]==summary["head"]==input_manifest["head"]=="d1698b94781c3c84e91faf03c75e8c308dc39c34","exact head")
check(manifest["tree"]==summary["tree"]==input_manifest["tree"]=="3f42d41fe4bbb8edd921ff161e8298ca66038a91","exact tree")
check(input_attestation["headRefOid"]==input_attestation["liveBranchRefOid"]==input_attestation["livePullRefOid"]==summary["head"],"PR head refs")
check(summary["livePRHead"]==summary["liveBranchRef"]==summary["livePullRef"]==summary["head"],"review-time live head refs")
check(sha((INPUT/"SHA256SUMS.txt").read_bytes())==summary["inputChecksumListSha256"]==manifest["inputChecksumListSha256"],"input checksum-list lineage")
check(sha((INPUT/"manifest.json").read_bytes())==summary["inputManifestJsonSha256"]==manifest["inputManifestJsonSha256"],"input manifest lineage")
check(sha((INPUT/"current-target-cells.jsonl").read_bytes())==summary["inputCurrentTargetCellsSha256"],"candidate cell lineage")
check(sha((INPUT/"source-contexts.jsonl").read_bytes())==summary["inputSourceContextsSha256"],"caller context lineage")

inputs=readl(INPUT/"current-target-cells.jsonl")
decisions=readl(HERE/"review-decisions.jsonl")
contexts={r["position"]:r for r in readl(INPUT/"source-contexts.jsonl")}
check(len(inputs)==len(decisions)==summary["cellCount"]==manifest["cellCount"]==240,"cell count")
check([(r["position"],r["locale"]) for r in decisions]==[(r["position"],r["locale"]) for r in inputs],"cell order")
allowed={"accept-current","correction","refinement","hold"}
ph=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
num=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
tag=re.compile(r"</?[A-Za-z][^>]*>")
counts={}
proposal_count=0
for d,c in zip(decisions,inputs):
    pos=d["position"]
    check(d["decision"] in allowed,"disposition")
    counts[d["decision"]]=counts.get(d["decision"],0)+1
    check(d["sourceId"]==c["sourceId"] and d["source"]==c["source"] and d["sourceSha256"]==c["sourceSha256"],"source lineage")
    check(d["locale"]==c["locale"],"locale lineage")
    check(d["currentTarget"]==c["currentTarget"] and d["currentTargetSha256"]==c["currentTargetSha256"] and d["catalogTranslationHash"]==c["catalogTranslationHash"],"current target lineage")
    check(d["callerContextSha256"]==c["callerContextSha256"],"caller context lineage")
    check(d["callerContextAmbiguous"]==contexts[pos]["ambiguousContext"],"ambiguity pin")
    check(d["rationale"] and d["confidence"] in ("high","moderate","low"),"rationale/confidence")
    selected=d["selectedTarget"]
    if d["decision"]=="hold":
        check(selected is None and "proposedTarget" not in d and d["selectedTargetSha256"] is None,"hold has no candidate")
    else:
        check(isinstance(selected,str),"selected target")
        check(sha(selected.encode("utf-8"))==d["selectedTargetSha256"],"selected-target hash")
        check(sorted(ph.findall(c["source"]))==sorted(ph.findall(selected)),"placeholder preservation")
        check(num.findall(c["source"])==num.findall(selected),"number preservation")
        missing=[t for t in c["sourceProtectedLiterals"] if not re.search(r"(?<![A-Za-z0-9])"+re.escape(t)+r"(?![A-Za-z0-9])",selected)]
        check(not missing,"protected literal preservation")
        check(not tag.search(selected),"unexpected markup in translation target")
        check(d["tokenChecks"]["placeholderMultisetPreserved"] and d["tokenChecks"]["numberSequencePreserved"] and d["tokenChecks"]["protectedLiteralsPreserved"],"recorded token checks")
        check(d["markupCheck"]["noUnexpectedMarkup"] and d["markupCheck"]["contextBoundaryPreserved"],"recorded markup check")
    if d["decision"]=="accept-current":
        check(selected==c["currentTarget"] and "proposedTarget" not in d,"accept-current target")
    elif d["decision"] in ("correction","refinement"):
        check(d.get("proposedTarget")==selected and selected!=c["currentTarget"],"proposed target only for updates")
        proposal_count+=1

for decision in allowed:
    counts.setdefault(decision,0)
check(counts==summary["counts"],"summary counts")
check(proposal_count==summary["proposalCount"],"proposal count")
check(counts["accept-current"]+counts["correction"]+counts["refinement"]+counts["hold"]==240,"disposition total")
check(summary["priorHeldCellsReattested"]==summary["priorHeldCellsUnchanged"]==288,"prior holds")
check(input_manifest["priorHoldTargetsUnchanged"] and input_manifest["priorHoldCellCount"]==288,"input prior hold evidence")
rank368=[r for r in decisions if r["position"]==368]
check(len(rank368)==12 and all(r["callerContextAmbiguous"] for r in rank368),"rank 368 caller context")
check(all(r["decision"]!="hold" for r in rank368),"rank 368 shared-key review")
check(summary["ambiguousCallerPositions"]==[368] and summary["ambiguousCallerCells"]==12,"ambiguous caller summary")
check(summary["callerResolutionHoldPositions"]==[] and summary["callerResolutionHoldCells"]==0,"caller hold summary")
check(summary["callerlessSourcePositions"]==[] and summary["callerlessCells"]==0,"callerless summary")
check(summary["blindReviewMaterialsConsultedDuringThisReview"] is False,"review boundary")
check(summary["repositoryOrPrMutatedDuringReview"] is False,"mutation boundary")
check(manifest["decisionLedger"]=="review-decisions.jsonl","manifest ledger reference")
print("PASS: primary W365-W384 ledger covers 240 cells, exact candidate-free source/target/context pins, all token/markup checks, and 288 unchanged prior holds; rank 368 dual-use context reviewed per locale.")
