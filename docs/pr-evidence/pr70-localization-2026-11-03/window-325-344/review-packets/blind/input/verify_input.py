#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
def readj(n): return json.loads((HERE/n).read_text(encoding="utf-8"))
def readl(n): return [json.loads(x) for x in (HERE/n).read_text(encoding="utf-8").splitlines() if x]
def check(v,msg):
    if not v: raise SystemExit("FAIL: "+msg)
sumrows={}
for line in (HERE/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    digest,name=line.split("  ",1)
    check(sha((HERE/name).read_bytes())==digest,"checksum "+name); sumrows[name]=digest
expected={p.name for p in HERE.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"}
check(set(sumrows)==expected,"checksum file inventory")
manifest=readj("manifest.json"); att=readj("PR-attestation.json"); sel=readj("selection.json")
check(manifest["head"]=="018937dc98d451ddd04d2d0942bca2777ef64dd3" and manifest["tree"]=="c13dc4fc091565318d11a19ad9e851215a5f917e","pinned head/tree")
check(att["headRefOid"]==att["liveBranchRefOid"]==att["livePullRefOid"]==manifest["head"],"PR branch/pull refs")
check(att["headTree"]==manifest["tree"] and att["state"]=="OPEN" and att["isDraft"],"PR attestation")
queue=json.loads((HERE/"source-queue.json").read_text(encoding="utf-8"))["messages"]
ids=sorted(m["id"] for m in queue)
check(len(queue)==479 and len(set(ids))==479,"source queue count/uniqueness")
check(sha(("\n".join(ids)+"\n").encode())==manifest["sourceIdOrderSha256"],"stable-ID order hash")
sources=readl("source-inventory-selection.jsonl"); cells=readl("current-target-cells.jsonl"); contexts=readl("source-contexts.jsonl")
check(len(sources)==20 and len(cells)==240 and len(contexts)==20,"20 sources/240 cells/20 contexts")
check([x["position"] for x in sources]==list(range(325,345)),"source rank coverage")
check([x["position"] for x in contexts]==list(range(325,345)),"context rank coverage")
check([x["position"] for x in sel["selectedSources"]]==list(range(325,345)),"selection rank coverage")
qmap={m["id"]:m for m in sorted(queue,key=lambda m:m["id"])}
for row in sources:
    q=qmap[row["sourceId"]]
    check(q["source"]==row["source"] and q["sourceHash"]==row["sourceSha256"],"selected source queue lineage")
    check(hashlib.sha256(row["source"].encode()).hexdigest()==row["sourceSha256"],"source hash")
prior=readl("prior-window-reattestation.jsonl")
check(len(prior)==20 and all(x["matchesCurrentQueue"] for x in prior),"prior window reattestation")
check([x["position"] for x in prior]==list(range(305,325)),"prior window ranks")
for row in cells:
    check(row["position"] in range(325,345),"cell rank")
    check(hashlib.sha256(row["currentTarget"].encode()).hexdigest()==row["currentTargetSha256"],"target hash")
    check(sorted(row["placeholderTokens"])==sorted(row["currentPlaceholderTokens"]) and row["placeholderMultisetMatches"],"placeholder parity")
    check(row["numericTokensPreserved"],"numeric token preservation")
holds=readl("caller-resolution-holds.jsonl")
check(len(holds)==2 and [x["position"] for x in holds]==[329,330],"callerless hold source count")
check(all(x["callerlessHold"] and x["currentCallerCount"]==0 for x in holds),"callerless hold evidence")
check(sum(x["position"] in (329,330) for x in cells)==24,"callerless hold cell count")
pins=readj("catalog-file-pins.json")
att2=readj("PR-attestation.json")
check(pins["files"]["romarr/ui-labels.json"]["gitBlob"]==att2["catalogGitBlob"],"catalog blob pin")
check(pins["files"]["romarr/ui-source-messages.json"]["gitBlob"]==att2["sourceQueueGitBlob"],"queue blob pin")
check(pins["activeUniqueSourceIds"]==479 and pins["catalogMessageCount"]==1836,"catalog/queue counts")
prot=readj("current-target-protected-literal-mismatches.json")
check(prot["mismatchCount"]==manifest["currentTargetProtectedLiteralMismatches"],"protected mismatch count")
for m in prot["mismatches"]:
    cell=next(x for x in cells if x["position"]==m["position"] and x["locale"]==m["locale"])
    check(cell["missingProtectedLiterals"]==m["missing"],"protected mismatch detail")
check(manifest["sourceCount"]==20 and manifest["cellCount"]==240 and manifest["candidateFree"],"manifest scope")
print("PASS: candidate-free W325-W344 input, exact PR pins, prior selection, 240 cells, protected-literal baseline, placeholders, numeric tokens, and 24 callerless holds.")
