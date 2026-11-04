#!/usr/bin/env python3
from pathlib import Path
import collections, hashlib, json, re
HERE=Path(__file__).resolve().parent
INPUT=HERE/"input"
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]
HEAD="7640720c5e3b1813725cca8d7aa46b5d968bff43"
TREE="bdee162cc11115256df8756f192b19d4337ed1dc"
TOKEN_RE=re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUMBER_RE=re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
PROTECTED=["ROMarr","GG Requestz","RomM","ROMm","ES-DE","gamelist.xml","1G1R","Battle.net","No-Intro","Redump","RetroArch","Steam","EA","Epic","ROM","Hub","DAT"]
def fail(s): raise SystemExit("FAIL: "+s)
def ok(v,s):
    if not v: fail(s)
def sha(x):
    if isinstance(x,str): x=x.encode()
    return hashlib.sha256(x).hexdigest()
def jsonl(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def jf(p): return json.loads(p.read_text(encoding="utf-8"))
def sums(root,name):
    p=root/name; rows={}
    for line in p.read_text(encoding="utf-8").splitlines():
        h,rel=line.split("  ",1); ok(rel not in rows,"duplicate checksum "+rel); rows[rel]=h
    actual={x.relative_to(root).as_posix() for x in root.rglob("*") if x.is_file() and x!=p}
    ok(actual==set(rows),"checksum inventory "+str(root))
    for rel,h in rows.items(): ok(sha((root/rel).read_bytes())==h,"checksum "+rel)
def protected(t):
    return sorted([x for x in PROTECTED if re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",t)],key=t.find)
sums(HERE,"SHA256SUMS.txt")
sums(INPUT,"SHA256SUMS.txt")
sums(HERE/"six-locale-adjunct","SHA256SUMS.txt")
manifest=jf(HERE/"manifest.json")
ok(manifest["head"]==HEAD and manifest["tree"]==TREE,"pinned head/tree")
ok(manifest["window"]=="W465-W484" and manifest["cellCount"]==240,"manifest scope")
ok(manifest["primaryReviewRead"] is False and manifest["catalogChangesApplied"] is False,"review boundary")
candidate=jf(INPUT/"manifest.json")
ok(candidate["head"]==HEAD and candidate["tree"]==TREE and candidate["cellCount"]==240,"candidate-free pin")
ctxs={r["position"]:r for r in jsonl(INPUT/"source-contexts.jsonl")}
cells={(r["position"],r["locale"]):r for r in jsonl(INPUT/"current-target-cells.jsonl")}
ledger=jsonl(HERE/"blind-ledger.jsonl")
ok(len(ledger)==240,"ledger row count")
lm={(r["position"],r["locale"]):r for r in ledger}
ok(len(lm)==240 and set(lm)==set(cells),"ledger exact scope")
counts=collections.Counter(r["disposition"] for r in ledger)
ok(dict(counts)=={"accept-current":170,"refine":7,"correct":3,"continued-hold":60},"decision counts")
hold_positions={470,471,473,474,477}
holdrows=jsonl(HERE/"continued-holds-hash-only.jsonl")
hm={(r["position"],r["locale"]):r for r in holdrows}
ok(len(hm)==60 and len(holdrows)==60,"hold count")
for key,cell in cells.items():
    row=lm[key]; ctx=ctxs[key[0]]
    ok(row["sourceId"]==cell["sourceId"] and row["sourceSha256"]==cell["sourceSha256"],"source pin "+str(key))
    ok(row["currentTargetSha256"]==cell["currentTargetSha256"]==sha(cell["currentTarget"]),"target hash "+str(key))
    ok(row["callerContextSha256"]==ctx["callerContextSha256"] and row["callerRefCount"]==len(ctx["callerContextRefs"]),"caller pin "+str(key))
    if key[0] in hold_positions:
        ok(row["disposition"]=="continued-hold" and key in hm,"callerless hold "+str(key))
        ok("proposedTarget" not in row and ctx["callerContextRefs"]==[],"hash-only hold "+str(key))
        ok(hm[key]["currentTargetSha256"]==cell["currentTargetSha256"] and "currentTarget" not in hm[key],"hold preimage "+str(key))
    else:
        ok(ctx["callerContextRefs"] and row["disposition"]!="continued-hold","caller-linked decision "+str(key))
    target=row.get("proposedTarget")
    if row["disposition"] in ("refine","correct"):
        ok(isinstance(target,str) and target and row.get("proposedTargetSha256")==sha(target),"proposal hash "+str(key))
        src=cell["source"]
        ok(collections.Counter(TOKEN_RE.findall(src))==collections.Counter(TOKEN_RE.findall(target)),"proposal placeholders "+str(key))
        ok(collections.Counter(NUMBER_RE.findall(src))==collections.Counter(NUMBER_RE.findall(target)),"proposal numbers "+str(key))
        ok(set(protected(src)).issubset(set(protected(target))),"proposal protected literals "+str(key))
        ck=row["checks"]
        ok(ck["proposalPlaceholderMultisetMatches"] and ck["proposalNumericTokensPreserved"] and ck["proposalProtectedLiteralsPreserved"],"proposal checks "+str(key))
    else:
        ok("proposedTarget" not in row and "proposedTargetSha256" not in row,"nonproposal omission "+str(key))
adj=jsonl(HERE/"six-locale-adjunct"/"independent-subset.jsonl")
ok(len(adj)==120 and len({(r["position"],r["locale"]) for r in adj})==120,"adjunct scope")
for a in adj:
    c=cells[(a["position"],a["locale"])]
    ok((a["sourceId"],a["sourceSha256"],a["currentTargetSha256"],a["callerContextSha256"])==(c["sourceId"],c["sourceSha256"],c["currentTargetSha256"],c["callerContextSha256"]),"adjunct preimage")
ph=jsonl(INPUT/"prior-hold-reattestation.jsonl")
ps=jsonl(INPUT/"prior-selection-reattestation.jsonl")
ok(len(ph)==384 and len(ps)==80,"prior lineage counts")
for r in ph+ps:
    ok(not any(k.lower() in ("target","currenttarget","targettext","translation","translatedvalue") for k in r),"prior target field")
summary=jf(HERE/"prior-reattestation-summary.json")
ok(summary["carriedHoldCellCount"]==384 and summary["priorSelectionCount"]==80,"prior summary")
print("PASS offline blind packet: 240 cells; 170 accept-current, 7 refinements, 3 corrections, 60 callerless holds; 384 carried holds and 80 prior selections reattested hash-only; exact source/target/caller preimages, proposal tokens/literals, adjunct scope, and checksums verified.")
