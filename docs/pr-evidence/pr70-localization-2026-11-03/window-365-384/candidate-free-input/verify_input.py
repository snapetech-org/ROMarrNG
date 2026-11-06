#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canon(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def readj(name):
    return json.loads((HERE/name).read_text(encoding="utf-8"))

def readl(name):
    return [json.loads(line) for line in (HERE/name).read_text(encoding="utf-8").splitlines() if line]

def check(condition,message):
    if not condition:
        raise SystemExit("FAIL: "+message)

sums={}
for line in (HERE/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    digest,name=line.split("  ",1)
    check(sha((HERE/name).read_bytes())==digest,"checksum "+name)
    sums[name]=digest
actual_files={p.name for p in HERE.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"}
check(set(sums)==actual_files,"checksum inventory")
check(not any("blind" in name.lower() or "primary-review" in name.lower() for name in sums),"review-material boundary")
m=readj("manifest.json")
att=readj("PR-attestation.json")
pins=readj("catalog-file-pins.json")
check(m["head"]=="d1698b94781c3c84e91faf03c75e8c308dc39c34" and m["tree"]=="3f42d41fe4bbb8edd921ff161e8298ca66038a91","exact head/tree")
check(att["headRefOid"]==att["liveBranchRefOid"]==att["livePullRefOid"]==m["head"],"PR ref pins")
check(att["headTree"]==m["tree"] and att["state"]=="OPEN" and att["isDraft"],"PR state/tree")
queue=readj("source-queue.json")["messages"]
ids=sorted(row["id"] for row in queue)
check(len(queue)==479 and len(set(ids))==479,"queue size/uniqueness")
check(sha(("\n".join(ids)+"\n").encode())==m["sourceIdOrderSha256"],"stable source ID ordering")
check(sha((HERE/"source-queue.json").read_bytes())==m["sourceQueueSha256"]==pins["sourceQueueSha256"],"source queue pin")
check(sha((HERE/"catalog-file-pins.json").read_bytes())==sums["catalog-file-pins.json"],"catalog pin checksum")
check(pins["commit"]==m["head"] and pins["tree"]==m["tree"],"catalog commit/tree pin")
selected=readl("source-inventory-selection.jsonl")
contexts=readl("source-contexts.jsonl")
cells=readl("current-target-cells.jsonl")
check(len(selected)==len(contexts)==20 and len(cells)==240,"window coverage")
check([r["position"] for r in selected]==list(range(365,385)),"source ranks")
check([(r["position"],r["sourceId"],r["sourceSha256"]) for r in selected]==[(r["position"],r["sourceId"],r["sourceSha256"]) for r in contexts],"source/context order")
check([r["position"] for r in cells]==[p for p in range(365,385) for _ in m["locales"]],"cell order")
queue_by_id={r["id"]:r for r in queue}
rank_by_id={source_id:i for i,source_id in enumerate(ids,1)}
for row in selected:
    q=queue_by_id[row["sourceId"]]
    check(q["source"]==row["source"] and q["sourceHash"]==row["sourceSha256"],"source lineage")
    check(rank_by_id[row["sourceId"]]==row["position"],"source rank")
ctx_by_id={r["sourceId"]:r for r in contexts}
ph=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
nums=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
for row in cells:
    ctx=ctx_by_id[row["sourceId"]]
    check(row["callerContextSha256"]==ctx["callerContextSha256"],"cell caller-context lineage")
    check(sha(row["currentTarget"].encode("utf-8"))==row["currentTargetSha256"],"target raw hash")
    check(sha(canon(row["currentTarget"]))==row["catalogTranslationHash"],"target canonical catalog hash")
    check(sorted(ph.findall(row["source"]))==sorted(row["currentPlaceholderTokens"]),"placeholder tokens")
    check(row["placeholderMultisetMatches"]==(sorted(ph.findall(row["source"]))==sorted(ph.findall(row["currentTarget"]))),"placeholder status")
    check(row["numericTokensPreserved"]==(nums.findall(row["source"])==nums.findall(row["currentTarget"])),"numeric-token status")
    check(row["protectedLiteralsPreserved"]==(len(row["missingProtectedLiterals"])==0),"protected-literal status")
    check(row["position"] in range(365,385),"window rank")
    for key in ("decision","selectedTarget","proposal","replacement"):
        check(key not in row,"candidate/review key in current cell")
for ctx in contexts:
    refs=ctx["callerContextRefs"]
    check(sha(json.dumps(refs,ensure_ascii=False,separators=(",",":")).encode("utf-8"))==ctx["callerContextSha256"],"caller-context aggregate hash")
    for ref in refs:
        snippet_hash=sha(canon({"path":ref["path"],"lineStart":ref["lineStart"],"lineEnd":ref["lineEnd"],"contextLines":ref["contextLines"]}))
        check(snippet_hash==ref["contextSha256"],"caller snippet hash")
        check(ref["fileSha256"] and ref["gitBlob"],"caller source file pin")
    check(ctx["callerResolutionHold"] is False,"caller hold status")
    check(ctx["sourceId"] in {r["sourceId"] for r in selected},"caller source membership")
check(m["candidateFree"] and not m["proposedTargetsIncluded"] and not m["reviewDecisionsIncluded"],"candidate-free boundary")
check(len(readl("prior-hold-reattestation.jsonl"))==288,"prior hold count")
holds=readl("prior-hold-reattestation.jsonl")
check(all(r["targetUnchanged"] and r["sourceMatchesCurrentQueue"] and r["positionMatchesCurrentQueue"] for r in holds),"prior holds unchanged")
check(m["priorHoldTargetsUnchanged"] and m["priorHoldCellCount"]==288,"prior hold summary")
prior=readl("prior-window-reattestation.jsonl")
check(len(prior)==20 and all(r["matchesCurrentQueue"] for r in prior),"prior window source reattestation")
check(m["priorWindowReattested"],"prior window summary")
check(m["callerlessSourcePositions"]==[] and m["callerlessCells"]==0,"callerless count")
check(m["ambiguousCallerPositions"]==[368] and m["ambiguousCallerCells"]==12,"ambiguous context count")
for filename,key in [
    ("current-target-placeholder-mismatches.json","currentTargetPlaceholderMismatches"),
    ("current-target-numeric-mismatches.json","currentTargetNumericMismatches"),
    ("current-target-protected-literal-mismatches.json","currentTargetProtectedLiteralMismatches"),
]:
    check(readj(filename)["mismatchCount"]==m[key],"mismatch count "+filename)
check(pins["catalogKeyOrderSha256"]==m["catalogKeyOrderSha256"],"catalog key-order pin")
check(sha(canon(readj("source-snapshot.json")))==m["sourceSnapshotSha256"]==pins["sourceSnapshotSha256"],"source snapshot hash")
check(len(cells)==m["cellCount"]==240 and m["sourceCount"]==20 and m["localeCount"]==12,"manifest cell scope")
print("PASS: W365-W384 candidate-free input; exact head/tree; 240 current cells; 288 prior holds unchanged; 20 pinned caller contexts; position 368 marked ambiguous; no callerless source; no review decisions or blind material.")
