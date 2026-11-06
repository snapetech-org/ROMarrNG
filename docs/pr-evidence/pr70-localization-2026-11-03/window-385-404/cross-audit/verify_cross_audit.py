#!/usr/bin/env python3
import hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path
p=Path(__file__).resolve().parent;root=Path("/home/keith/Documents/code/task-scratch")
cf=root/"romarrng-pr70-w385-404-rebased-candidate-free-20261103/input";pr=root/"romarrng-pr70-w385-404-rebased-primary-20261103/primary-review";b=root/"romarrng-pr70-w385-404-blind-20261103"
for d,check in ((cf,"verify_input.py"),(pr,"verify-primary-review.py"),(b,"verify_review.py")):
 subprocess.check_call(["sha256sum","-c","SHA256SUMS.txt"],cwd=d,stdout=subprocess.DEVNULL);subprocess.check_call(["python3",check],cwd=d,stdout=subprocess.DEVNULL)
m=json.loads((p/"manifest.json").read_text());s=json.loads((p/"summary.json").read_text());att=json.loads((p/"live-ref-attestation.json").read_text())
assert m["head"]=="0afd1d8c150fb96d868394a8d9620371db612185" and m["tree"]=="0ba717d05c49356d8b1f55ac4a6b8844c161a402"
cfm=json.loads((cf/"manifest.json").read_text());pm=json.loads((pr/"manifest.json").read_text());bm=json.loads((b/"manifest.json").read_text())
for x in (cfm,pm,bm):assert x["head"]==m["head"] and x["tree"]==m["tree"]
assert m["candidateFreeManifestSha256"]==hashlib.sha256((cf/"manifest.json").read_bytes()).hexdigest()
assert m["primaryManifestSha256"]==hashlib.sha256((pr/"manifest.json").read_bytes()).hexdigest() and m["blindManifestSha256"]==hashlib.sha256((b/"manifest.json").read_bytes()).hexdigest()
assert pm["inputManifestSha256"]==m["candidateFreeManifestSha256"] and bm["inputManifestSha256"]==m["candidateFreeManifestSha256"]
assert att["prBefore"]["headRefOid"]==m["head"]==att["prAfter"]["headRefOid"] and att["prBefore"]["state"]==att["prAfter"]["state"]=="OPEN" and att["prBefore"]["isDraft"] is True and att["prAfter"]["isDraft"] is True
assert att["branchRef"]==m["head"] and att["pullRef"]==m["head"] and att["treeBefore"]==m["tree"]==att["treeAfter"]
cells={(r["position"],r["locale"]):r for r in map(json.loads,(cf/"current-target-cells.jsonl").read_text().splitlines())}
contexts={r["position"]:r for r in map(json.loads,(cf/"source-contexts.jsonl").read_text().splitlines())}
primary={(r["position"],r["locale"]):r for r in map(json.loads,(pr/"review-decisions.jsonl").read_text().splitlines())}
pledger={(r["position"],r["locale"]):r for r in map(json.loads,(pr/"review-ledger.jsonl").read_text().splitlines())}
blind={(r["position"],r["locale"]):r for r in map(json.loads,(b/"review-decisions.jsonl").read_text().splitlines())}
rows=[json.loads(x) for x in (p/"cross-audit-ledger.jsonl").read_text().splitlines() if x.strip()]
assert len(cells)==240 and len(contexts)==20 and len(primary)==len(pledger)==len(blind)==len(rows)==240
assert {(r["position"],r["locale"]) for r in rows}==set(cells)
def eff(r,current,isblind=False):return current if r["disposition"]=="accept-current" else (r["proposedTarget"] if isblind else r["target"])
ph=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}");num=re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)?(?![A-Za-z])")
expected_disputes=set()
for r in rows:
 k=(r["position"],r["locale"]);c=cells[k];ctx=contexts[k[0]];x=primary[k];xl=pledger[k];y=blind[k]
 assert r["sourceId"]==c["sourceId"]==ctx["sourceId"] and r["sourceSha256"]==c["sourceSha256"]==ctx["sourceSha256"] and r["callerContextSha256"]==c["callerContextSha256"]==ctx["callerContextSha256"]
 assert r["currentTargetSha256"]==c["currentTargetSha256"]==xl["currentTargetSha256"]==y["currentTargetSha256"]
 assert xl["sourceSha256"]==y["sourceSha256"]==c["sourceSha256"]
 pt=eff(x,c["currentTarget"]);bt=eff(y,c["currentTarget"],True)
 assert r["primaryDisposition"]==x["disposition"] and r["blindDisposition"]==y["disposition"]
 assert r["primaryTargetSha256"]==x["targetSha256"] and r["blindTargetSha256"]==y.get("proposedTargetSha256",y["currentTargetSha256"])
 mismatch=x["disposition"]!=y["disposition"] or pt!=bt
 if mismatch:expected_disputes.add(k)
 else:assert r["reconciledDisposition"]==x["disposition"]==y["disposition"] and r["reconciledTarget"]==pt==bt
 assert hashlib.sha256(r["reconciledTarget"].encode()).hexdigest()==r["reconciledTargetSha256"]
 assert Counter(ph.findall(c["source"]))==Counter(ph.findall(r["reconciledTarget"])) and Counter(num.findall(c["source"]))==Counter(num.findall(r["reconciledTarget"]))
 assert all(lit in r["reconciledTarget"] for lit in c["sourceProtectedLiterals"])
d=[json.loads(x) for x in (p/"disagreement-resolutions.jsonl").read_text().splitlines() if x.strip()]
dmap={(x["position"],x["locale"]):x for x in d}
assert len(d)==27 and set(dmap)==expected_disputes
for k,x in dmap.items():
 r=next(y for y in rows if (y["position"],y["locale"])==k)
 assert x["reconciledDisposition"]==r["reconciledDisposition"] and x["reconciledTarget"]==r["reconciledTarget"] and x["reconciledTargetSha256"]==r["reconciledTargetSha256"]
a=[json.loads(x) for x in (p/"apply-plan.jsonl").read_text().splitlines() if x.strip()];n=[json.loads(x) for x in (p/"no-op-plan.jsonl").read_text().splitlines() if x.strip()]
amap={(x["position"],x["locale"]):x for x in a};nmap={(x["position"],x["locale"]):x for x in n}
expected_a={(r["position"],r["locale"]):r for r in rows if r["reconciledTargetSha256"]!=r["currentTargetSha256"]}
expected_n=set(cells)-set(expected_a)
assert set(amap)==set(expected_a) and set(nmap)==expected_n and set(amap).isdisjoint(nmap)
for k,x in amap.items():
 r=expected_a[k];assert x["target"]==r["reconciledTarget"] and x["targetSha256"]==r["reconciledTargetSha256"] and x["expectedCurrentTargetSha256"]==r["currentTargetSha256"] and x["disposition"]==r["reconciledDisposition"]
for k,x in nmap.items():r=next(y for y in rows if (y["position"],y["locale"])==k);assert x["expectedCurrentTargetSha256"]==r["currentTargetSha256"] and x["targetSha256"]==r["currentTargetSha256"]
hcf=[json.loads(x) for x in (cf/"prior-hold-reattestation.jsonl").read_text().splitlines() if x.strip()]
hp=[json.loads(x) for x in (pr/"prior-hold-reattestation.jsonl").read_text().splitlines() if x.strip()]
hb=[json.loads(x) for x in (b/"prior-hold-reattestation.jsonl").read_text().splitlines() if x.strip()]
h=[json.loads(x) for x in (p/"hold-plan.jsonl").read_text().splitlines() if x.strip()]
key=lambda x:(x["window"],x["position"],x["locale"],x["sourceId"],x["sourceSha256"],x["currentTargetSha256"])
assert len(hcf)==len(hp)==len(hb)==len(h)==288 and {key(x) for x in hcf}=={key(x) for x in hp}=={key(x) for x in hb}=={key(x) for x in h}
assert all(x["targetUnchanged"] and x["sourceMatchesCurrentQueue"] and x["positionMatchesCurrentQueue"] and x["currentTargetSha256"]==x["priorCurrentTargetSha256"] for x in hcf+hp+hb)
fc=Counter(x["reconciledDisposition"] for x in rows)
assert dict(sorted(fc.items()))==s["reconciledDispositions"] and len(a)==s["applyCellCount"] and len(n)==s["noOpCellCount"] and len(h)==s["carriedHoldCellCount"]==288
assert len(a)+len(n)==240 and not fc["hold"] and s["disputedCellsResolved"]==27
print(f"PASS: 240 exact-hash reconciliations; {len(d)} disagreements resolved; {len(a)} updates, {len(n)} no-ops; 288 holds preserved")
