#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
def readj(n): return json.loads((HERE/n).read_text(encoding="utf-8"))
def readl(n): return [json.loads(x) for x in (HERE/n).read_text(encoding="utf-8").splitlines() if x]
def chk(v,msg):
    if not v: raise SystemExit("FAIL: "+msg)
sums={}
for line in (HERE/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    digest,name=line.split("  ",1); chk(sha((HERE/name).read_bytes())==digest,"checksum "+name); sums[name]=digest
chk(set(sums)=={p.name for p in HERE.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"},"checksum inventory")
m=readj("manifest.json"); a=readj("PR-attestation.json"); p=readj("catalog-file-pins.json")
chk(m["head"]=="6bef0c74632067906fd07279fa6bd3fd59159a48" and m["tree"]=="4fd79e67f37e4c66d0253199418973d965a3fbd6","exact head/tree")
chk(a["headRefOid"]==a["liveBranchRefOid"]==a["livePullRefOid"]==m["head"],"branch/pull refs")
chk(a["state"]=="OPEN" and a["isDraft"] and a["headTree"]==m["tree"],"PR state/tree")
q=readj("source-queue.json")["messages"]; ids=sorted(x["id"] for x in q)
chk(len(q)==479 and len(set(ids))==479,"queue count/uniqueness")
chk(sha(("\n".join(ids)+"\n").encode())==m["sourceIdOrderSha256"],"stable ID order")
src=readl("source-inventory-selection.jsonl"); ctx=readl("source-contexts.jsonl"); cells=readl("current-target-cells.jsonl")
chk(len(src)==20 and len(ctx)==20 and len(cells)==240,"window coverage")
chk([x["position"] for x in src]==list(range(345,365)),"source ranks")
chk([x["position"] for x in cells]==[i for i in range(345,365) for _ in m["locales"]],"cell order")
qm={x["id"]:x for x in q}
for row in src:
    item=qm[row["sourceId"]]; chk(item["source"]==row["source"] and item["sourceHash"]==row["sourceSha256"],"source lineage")
for row in cells:
    chk(sha(row["currentTarget"].encode())==row["currentTargetSha256"],"current target hash")
    chk(row["placeholderMultisetMatches"] and row["numericTokensPreserved"],"placeholder/numeric parity")
    chk(row["position"] in range(345,365),"target rank")
prior=readl("prior-window-reattestation.jsonl")
chk(len(prior)==20 and all(x["matchesCurrentQueue"] for x in prior),"prior selection reattestation")
hold=readl("prior-hold-reattestation.jsonl")
chk(len(hold)==288 and all(x["targetUnchanged"] and x["sourceMatchesCurrentQueue"] and x["positionMatchesCurrentQueue"] for x in hold),"prior hold carry-forward")
chk(m["priorHoldTargetsUnchanged"] and m["priorHoldCellCount"]==288,"prior hold summary")
chk(m["cellCount"]==240 and m["candidateFree"] and not m["proposedTargetsIncluded"] and not m["reviewDecisionsIncluded"],"candidate-free scope")
chk(readj("current-target-placeholder-mismatches.json")["mismatchCount"]==m["currentTargetPlaceholderMismatches"],"placeholder mismatch count")
chk(readj("current-target-numeric-mismatches.json")["mismatchCount"]==m["currentTargetNumericMismatches"],"numeric mismatch count")
chk(readj("current-target-protected-literal-mismatches.json")["mismatchCount"]==m["currentTargetProtectedLiteralMismatches"],"protected literal count")
chk(p["catalogKeyOrderSha256"]==m["catalogKeyOrderSha256"],"catalog order")
print(f"PASS: W345-W364 candidate-free input; 240 cells; {len(prior)} prior source IDs and {len(hold)} prior hold cells reattested.")
