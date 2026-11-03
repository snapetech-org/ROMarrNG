#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent

def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def j(n): return json.loads((HERE/n).read_text(encoding="utf-8"))
def l(n): return [json.loads(x) for x in (HERE/n).read_text(encoding="utf-8").splitlines() if x]
def ok(v,m):
 if not v: raise SystemExit("FAIL: "+m)
sums={}
for line in (HERE/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
 d,n=line.split("  ",1); ok(sha((HERE/n).read_bytes())==d,"checksum "+n); sums[n]=d
actual={p.name for p in HERE.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt"}
ok(set(sums)==actual,"checksum inventory")
m=j("manifest.json"); a=j("PR-attestation.json"); p=j("catalog-file-pins.json"); sel=j("selection.json")
head="c146189f29db8fbd77d68dff0c33a0ab59a6b601"; tree="3db10f8b87577edd1167e4489524e6afbb50d556"
ids=["ui.enter-the-romarr-url-reachable-from.b7fbd08882","ui.enter-the-passphrase-used-to-encrypt.5eb0ff3860","ui.epic-ea-and-battle-net.119e20a9dc","ui.error.54a0e8c17e","ui.errors-only.30767c1658","ui.event.4e1f49a9c8","ui.events.8d14f6e72d","ui.every-enabled-plugin-that-declares-c.b262b12d91","ui.every-platform-can-be-downloaded.25abe82cf6","ui.every-release-your-indexers-returned.76d5936486","ui.everything.75304cf77d","ui.everything-in-my-library.3afc676d80","ui.evidence.03867aea70","ui.exact-dat-checksum-match.91363b80af","ui.exclude-rom-hacks.3141be8d5f","ui.exclude-beta-versions.019e343517","ui.exclude-demos.3e268c6803","ui.exclude-prototypes.4406b5a3cc","ui.exclude-unlicensed-roms.25bdf9372a","ui.exclude-published-dumps-only.138f24d77b"]
locales=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
ok((m["head"],m["tree"])==(head,tree),"exact head/tree")
ok(a["headRefOid"]==a["liveBranchRefOid"]==a["livePullRefOid"]==head and a["headTree"]==tree,"live PR/branch/pull refs")
ok(a["state"]=="OPEN" and a["isDraft"] and a["headRefName"]==m["branch"],"PR state/branch")
ok(m["candidateFree"] and not m["proposedTargetsIncluded"] and not m["reviewDecisionsIncluded"],"candidate-free boundary")
queue=j("source-queue.json")["messages"]; ids_sorted=sorted(x["id"] for x in queue)
ok(len(queue)==479 and len(set(ids_sorted))==479,"active source registry count/uniqueness")
ok(sha(("\n".join(ids_sorted)+"\n").encode())==m["sourceIdOrderSha256"]==p["sourceIdOrderSha256"],"active source ID-order hash")
ok(sha((HERE/"source-queue.json").read_bytes())==m["sourceQueueSha256"]==p["sourceQueueSha256"],"source queue hash")
ok(sha(canon(j("source-snapshot.json")))==m["sourceSnapshotSha256"]==p["sourceSnapshotSha256"] and len(j("source-snapshot.json"))==479,"source snapshot pin")
inventory=l("catalog-source-inventory.jsonl")
ok(len(inventory)==1836 and [x["catalogOneBasedPosition"] for x in inventory]==list(range(1,1837)),"catalog source inventory coverage/order")
ok(sha(("\n".join(x["sourceId"] for x in inventory)+"\n").encode())==m["catalogKeyOrderSha256"],"catalog key insertion-order hash")
ok([(x["sourceId"],x["source"],x["sourceSha256"]) for x in inventory[405:425]]==[(x["sourceId"],x["source"],x["sourceSha256"]) for x in l("source-inventory-selection.jsonl")],"catalog source slice lineage")
ok(len(j("catalog-insertion-queue.json"))==20,"catalog insertion queue coverage")
selected=l("source-inventory-selection.jsonl"); contexts=l("source-contexts.jsonl"); cells=l("current-target-cells.jsonl")
ok(len(selected)==len(contexts)==20 and len(cells)==240,"W405-W424 coverage")
ok([x["position"] for x in selected]==list(range(405,425)) and [x["sourceId"] for x in selected]==ids,"exact requested order")
ok([x["catalogZeroBasedIndex"] for x in selected]==list(range(405,425)) and [x["catalogOneBasedPosition"] for x in selected]==list(range(406,426)),"catalog insertion ordinals")
ok(sel["selectedSources"]==selected,"selection file consistency")
ctx={x["sourceId"]:x for x in contexts}; sel_by={x["sourceId"]:x for x in selected}; ph=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}"); nums=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
for c in cells:
 x=ctx[c["sourceId"]]; src=sel_by[c["sourceId"]]
 ok(c["callerContextSha256"]==x["callerContextSha256"],"cell caller-context pin")
 ok(c["source"]==src["source"] and c["sourceSha256"]==src["sourceSha256"],"cell source lineage")
 ok(sha(c["currentTarget"].encode())==c["currentTargetSha256"],"current target hash")
 ok(sha(canon(c["currentTarget"]))==c["catalogTranslationHash"],"catalog target hash")
 ok(sorted(ph.findall(c["source"]))==sorted(c["sourcePlaceholderTokens"]) and sorted(ph.findall(c["currentTarget"]))==sorted(c["currentPlaceholderTokens"]) and c["placeholderMultisetMatches"],"placeholder integrity")
 ok(nums.findall(c["source"])==c["sourceNumericTokens"] and nums.findall(c["currentTarget"])==c["currentNumericTokens"] and c["numericTokensPreserved"],"numeric token integrity")
 ok(not c["missingProtectedLiterals"] and c["protectedLiteralsPreserved"],"protected literal integrity")
 ok(not any(k in c for k in ("decision","proposal","replacement","selectedTarget")),"candidate-free cell fields")
for x in contexts:
 ok(sha(canon(x["callerContextRefs"]))==x["callerContextSha256"],"caller aggregate hash")
 for r in x["callerContextRefs"]:
  ok(r["lineStart"]<=r["lineEnd"] and len(r["contextLines"])==r["lineEnd"]-r["lineStart"]+1,"caller excerpt range")
  body={"path":r["path"],"lineStart":r["lineStart"],"lineEnd":r["lineEnd"],"contextLines":r["contextLines"]}
  ok(sha(canon(body))==r["contextSha256"] and r["fileSha256"] and r["gitBlob"],"caller excerpt hash/file pin")
  ok(r["anchor"] in "\n".join(z["text"] for z in r["contextLines"]),"caller context contains declared anchor")
  ok(r["fileSha256"]==p["callerSourceFilePins"][r["path"]]["fileSha256"] and r["gitBlob"]==p["callerSourceFilePins"][r["path"]]["gitBlob"],"caller file pin matches catalog pins")
mechanics=j("dispatch-mechanics.json")["evidence"]
for r in mechanics:
 body={"path":r["path"],"lineStart":r["lineStart"],"lineEnd":r["lineEnd"],"contextLines":r["contextLines"]}
 ok(sha(canon(body))==r["contextSha256"],"dispatch excerpt hash")
 ok(r["anchor"] in "\n".join(z["text"] for z in r["contextLines"]),"dispatch context contains declared anchor")
 ok(r["fileSha256"]==p["callerSourceFilePins"][r["path"]]["fileSha256"] and r["gitBlob"]==p["callerSourceFilePins"][r["path"]]["gitBlob"],"dispatch file pins")
ok([x["position"] for x in contexts if x["callerResolution"]=="translation-dispatch-gap"]==[405,407,416],"dispatch gap positions")
ok([x["position"] for x in contexts if x["callerResolution"]=="callerless"]==[408],"callerless position")
ok([x["position"] for x in contexts if x["ambiguousCaller"]]==[],"ambiguous caller positions")
search=j("caller-search-audit.json")
ok(search["queries"][0]["literal"]=="ui.error.54a0e8c17e" and search["queries"][0]["matchCount"]==0,"callerless Error exact-key search")
holds=l("prior-hold-reattestation.jsonl")
ok(len(holds)==288 and all(x["targetUnchanged"] and x["sourceMatchesCurrentCatalog"] and x["priorPositionMatches"] and x["priorSourceMatches"] for x in holds),"288 carried holds unchanged")
ok(len(l("prior-window-reattestation.jsonl"))==20 and all(x["matchesCurrentCatalogAndRegistry"] for x in l("prior-window-reattestation.jsonl")),"prior W385-W404 source selection reattested")
for f,k in [("current-target-placeholder-mismatches.json","currentTargetPlaceholderMismatches"),("current-target-numeric-mismatches.json","currentTargetNumericMismatches"),("current-target-protected-literal-mismatches.json","currentTargetProtectedLiteralMismatches")]: ok(j(f)["mismatchCount"]==m[k]==0,"mismatch report "+f)
ok(m["priorHoldCellCount"]==288 and m["priorHoldTargetsUnchanged"],"hold summary")
ok(m["currentReviewHoldPositions"]==[405,407,408,416] and m["currentReviewHoldCells"]==48,"current hold coverage")
print("PASS candidate-free W405-W424: exact PR/head/tree refs; catalog slice and 240 cells; 20 live source-context records; current active-registry metadata; 288 carried holds unchanged; 20 prior selected sources reattested; placeholder/numeric/protected literals clean; candidate-free boundary and checksums.")
