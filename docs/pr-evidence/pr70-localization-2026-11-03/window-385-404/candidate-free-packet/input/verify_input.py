#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, re
HERE=Path(__file__).resolve().parent

def sha(data): return hashlib.sha256(data).hexdigest()
def canon(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def readj(name): return json.loads((HERE/name).read_text(encoding="utf-8"))
def readl(name): return [json.loads(x) for x in (HERE/name).read_text(encoding="utf-8").splitlines() if x]
def check(ok,msg):
    if not ok: raise SystemExit("FAIL: "+msg)

sums={}
for line in (HERE/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    digest,name=line.split("  ",1)
    check(sha((HERE/name).read_bytes())==digest,"checksum "+name)
    sums[name]=digest
actual={p.name for p in HERE.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"}
check(set(sums)==actual,"checksum inventory")
check(not any("blind" in n.lower() or "primary" in n.lower() or "cross-audit" in n.lower() for n in sums),"candidate-free boundary filenames")
m=readj("manifest.json"); att=readj("PR-attestation.json"); pins=readj("catalog-file-pins.json")
head="0afd1d8c150fb96d868394a8d9620371db612185"; tree="0ba717d05c49356d8b1f55ac4a6b8844c161a402"
check(m["head"]==head and m["tree"]==tree,"exact head/tree")
check(att["headRefOid"]==att["liveBranchRefOid"]==att["livePullRefOid"]==head,"live PR/branch/pull refs")
check(att["headTree"]==tree and att["state"]=="OPEN" and att["isDraft"] and att["headRefName"]==m["branch"],"PR state/branch/tree")
check(m["candidateFree"] and not m["proposedTargetsIncluded"] and not m["reviewDecisionsIncluded"],"candidate-free manifest")
check(m["candidateFreeBasisHead"]=="8a15dd1c3487d17e62d78a1b80222b7eb6033c6b" and m["candidateFreeBasisTree"]=="452cda96454624cfa7068b9925d15e821d4828f7","candidate-free predecessor basis")
check(m["candidateFreeBasisInputChecksumListSha256"]=="e2fda3d29b058a085d6b599e28ceed4d95c23727bd014ad987fa72b276929409","predecessor packet seal pin")
queue_obj=readj("source-queue.json"); queue=queue_obj["messages"]; ids=sorted(r["id"] for r in queue)
check(len(queue)==479 and len(set(ids))==479,"active queue size/unique IDs")
check(sha(("\n".join(ids)+"\n").encode())==m["sourceIdOrderSha256"],"source ID sort/rank hash")
check(sha((HERE/"source-queue.json").read_bytes())==m["sourceQueueSha256"]==pins["sourceQueueSha256"],"source queue hash")
check(pins["commit"]==head and pins["tree"]==tree and pins["catalogSha256"]==m["catalogSha256"] and pins["catalogKeyOrderSha256"]==m["catalogKeyOrderSha256"],"catalog pins")
check(len(readj("source-snapshot.json"))==479 and sha(canon(readj("source-snapshot.json")))==m["sourceSnapshotSha256"]==pins["sourceSnapshotSha256"],"source snapshot pin")
selected=readl("source-inventory-selection.jsonl"); contexts=readl("source-contexts.jsonl"); cells=readl("current-target-cells.jsonl")
check(len(selected)==len(contexts)==20 and len(cells)==240,"W385-W404 coverage")
check([r["position"] for r in selected]==list(range(385,405)),"source rank order")
check([(r["position"],r["sourceId"],r["sourceSha256"]) for r in selected]==[(r["position"],r["sourceId"],r["sourceSha256"]) for r in contexts],"source/context order")
check([r["position"] for r in cells]==[p for p in range(385,405) for _ in m["locales"]],"cell rank order")
check([r["locale"] for r in cells[:12]]==m["locales"],"locale order")
by_id={r["id"]:r for r in queue}; rank={sid:i for i,sid in enumerate(ids,1)}
for row in selected:
    src=by_id[row["sourceId"]]
    check(src["source"]==row["source"] and src["sourceHash"]==row["sourceSha256"] and rank[row["sourceId"]]==row["position"],"selected source lineage/rank")
ctx={r["sourceId"]:r for r in contexts}; ph=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}"); nums=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
for row in cells:
    c=ctx[row["sourceId"]]
    check(row["callerContextSha256"]==c["callerContextSha256"],"cell caller context")
    check(sha(row["currentTarget"].encode())==row["currentTargetSha256"],"current target raw hash")
    check(sha(canon(row["currentTarget"]))==row["catalogTranslationHash"],"current catalog translation hash")
    source_ph=ph.findall(row["source"]); target_ph=ph.findall(row["currentTarget"])
    check(sorted(source_ph)==sorted(row["currentPlaceholderTokens"]) and row["placeholderMultisetMatches"]==(sorted(source_ph)==sorted(target_ph)),"placeholder verification")
    check(row["numericTokensPreserved"]==(nums.findall(row["source"])==nums.findall(row["currentTarget"])),"numeric token verification")
    check(row["protectedLiteralsPreserved"]==(not row["missingProtectedLiterals"]),"protected literal verification")
    check(row["position"] in range(385,405),"cell rank")
    check(not any(k in row for k in ("decision","selectedTarget","proposal","replacement")),"no candidate/review fields")
for c in contexts:
    refs=c["callerContextRefs"]
    check(sha(json.dumps(refs,ensure_ascii=False,separators=(",",":")).encode())==c["callerContextSha256"],"caller context aggregate hash")
    for ref in refs:
        check(ref["lineStart"]<=ref["lineEnd"] and len(ref["contextLines"])==ref["lineEnd"]-ref["lineStart"]+1,"caller excerpt range")
        check(sha(canon({"path":ref["path"],"lineStart":ref["lineStart"],"lineEnd":ref["lineEnd"],"contextLines":ref["contextLines"]}))==ref["contextSha256"],"caller excerpt hash")
        check(ref["fileSha256"] and ref["gitBlob"],"caller file pins")
    check(c["callerResolutionHold"] is False and c["sourceId"] in {r["sourceId"] for r in selected},"caller resolution/source membership")
gaps=sorted(c["position"] for c in contexts if c["translationDispatchGap"])
check(gaps==m["translationDispatchGapPositions"]==[] and m["translationDispatchGapCells"]==0,"no remaining dispatch gaps")
new_positions=[392,396,398,399]
check(m["newlyRenderableDispatchPositions"]==new_positions and m["newlyRenderableDispatchCells"]==48 and m["previouslyOpaqueDispatchCellsNowRenderable"]==48,"newly renderable scope")
by_pos={c["position"]:c for c in contexts}
for pos in [396,398,399]:
    c=by_pos[pos]; combined="\n".join(line["text"] for ref in c["callerContextRefs"] for line in ref["contextLines"])
    source=c["source"]; sid=c["sourceId"]
    check(sid in combined and "detail_source_id" in combined and "moonlightApiMessageMarkup(" in combined,"fixed local source ID route at "+str(pos))
    check("message&&message.source===value" in combined and "?interfaceMarkup(sourceId):apiMessageMarkup(value)" in combined,"exact catalog-source guard and opaque fallback at "+str(pos))
    fragments={396:["Submitted. The host does not report whether the ","appears in the paired list."],398:["Sunshine has no endpoint that lists waiting clients ","then type the PIN it shows."],399:["Sunshine refused it: no Moonlight ","pairing on your client first."]}[pos]
    check(all(fragment in combined for fragment in fragments),"fixed source text is pinned at "+str(pos))
c=by_pos[392]; combined="\n".join(line["text"] for ref in c["callerContextRefs"] for line in ref["contextLines"])
check(c["sourceId"] in combined and "ORGANIZER_API_MESSAGE_KEYS" in combined and "stableLocalizationKey(value)" in combined,"organizer exact-key source route")
check("?interfaceMarkup(key):apiMessageMarkup(value,template)" in combined,"organizer opaque fallback")
check(m["callerlessSourcePositions"]==[] and m["callerlessCells"]==0 and m["ambiguousCallerPositions"]==[] and m["ambiguousCallerCells"]==0,"caller resolution")
holds=readl("prior-hold-reattestation.jsonl")
check(len(holds)==288 and all(r["targetUnchanged"] and r["sourceMatchesCurrentQueue"] and r["positionMatchesCurrentQueue"] for r in holds),"288 predecessor holds reattested")
check(m["priorHoldTargetsUnchanged"] and m["priorHoldCellCount"]==288,"predecessor hold summary")
prior=readl("prior-window-reattestation.jsonl")
check(len(prior)==20 and all(r["matchesCurrentQueue"] for r in prior) and m["priorWindowReattested"],"W365-W384 predecessor selection reattested")
for filename,key in [("current-target-placeholder-mismatches.json","currentTargetPlaceholderMismatches"),("current-target-numeric-mismatches.json","currentTargetNumericMismatches"),("current-target-protected-literal-mismatches.json","currentTargetProtectedLiteralMismatches")]:
    report=readj(filename); check(report["mismatchCount"]==m[key]==len(report["mismatches"]),"mismatch report "+filename)
check(m["currentTargetPlaceholderMismatches"]==m["currentTargetNumericMismatches"]==m["currentTargetProtectedLiteralMismatches"]==0,"token/number/protected literal status")
print("PASS: rebased candidate-free W385-W404 packet; exact live head/tree attestation; 240 cells; 20 source/caller contexts; exact source-bound routes for four newly renderable positions (48 cells); 288 predecessor holds unchanged; token, numeric, protected-literal checks clean; no proposals or review decisions.")
