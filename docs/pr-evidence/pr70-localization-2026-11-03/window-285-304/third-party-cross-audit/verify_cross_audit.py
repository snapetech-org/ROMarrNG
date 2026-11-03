#!/usr/bin/env python3
import hashlib,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def digest(b): return hashlib.sha256(b).hexdigest()
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x]
def key(x): return (x["position"],x["sourceId"],x["locale"])
def manifest(folder,name):
    for line in (folder/name).read_text(encoding="utf-8").splitlines():
        if line.strip():
            want,rel=line.split("  ",1)
            assert digest((folder/rel).read_bytes())==want,(folder/rel)
manifest(ROOT/"candidate-free-input","SHA256SUMS.txt")
manifest(ROOT/"primary-review","SHA256SUMS.txt")
manifest(ROOT/"blind-review","SHA256SUMS.txt")
I=jl(ROOT/"candidate-free-input/current-target-cells.jsonl")
P=jl(ROOT/"primary-review/primary-decisions.jsonl")
B=jl(ROOT/"blind-review/ledger.jsonl")
C=jl(ROOT/"cross-audit-ledger.jsonl")
S=jl(ROOT/"selected-changes.jsonl")
maps=[{key(x):x for x in a} for a in [I,P,B,C]]
im,pm,bm,cm=maps
assert all(len(x)==240 for x in maps)
assert set(im)==set(pm)==set(bm)==set(cm)
att=json.loads((ROOT/"blind-review/attestation.json").read_text(encoding="utf-8"))
assert att["packetHead"]=="363601fd2597f0fb97adff97554e651c2bea2d99" and att["packetTree"]=="1f8ada1746f53796e2b4a8f43f9a0075150aa5d7"
for k,i in im.items():
    p,b,c=pm[k],bm[k],cm[k]
    assert i["head"]==p["head"]==c["head"]=="363601fd2597f0fb97adff97554e651c2bea2d99"
    assert i["tree"]==p["tree"]==c["tree"]=="1f8ada1746f53796e2b4a8f43f9a0075150aa5d7"
    assert i["currentTarget"]==p["currentTarget"]==b["currentTarget"]==c["currentTarget"]
    assert i["currentTargetSha256"]==p["currentTargetSha256"]==b["currentTargetSha256"]==hashlib.sha256(i["currentTarget"].encode()).hexdigest()
    assert c["rootTargetSha256"]==hashlib.sha256(c["rootTarget"].encode()).hexdigest()
    assert Counter(re.findall(r"[{]([^{}]+)[}]",c["rootTarget"]))==Counter(i.get("sourcePlaceholders",[]))
    assert c["placeholderMultisetMatches"] is True
    assert all(v in c["rootTarget"] for v in (b.get("protectedLiterals") or []))
    if c["rootDisposition"]=="hold": assert c["position"] in {286,304} and c["rootTarget"]==c["currentTarget"]
expect=[x for x in C if x["rootTarget"]!=x["currentTarget"]]
assert len(expect)==len(S)==84
assert {(x["position"],x["sourceId"],x["locale"],x["rootTarget"],x["rootTargetSha256"]) for x in expect}=={(x["position"],x["sourceId"],x["locale"],x["target"],x["targetSha256"]) for x in S}
counts=Counter(x["rootDisposition"] for x in C)
assert counts["hold"]==24 and sum(x["position"]==286 and x["rootDisposition"]=="hold" for x in C)==12 and sum(x["position"]==304 and x["rootDisposition"]=="hold" for x in C)==12
auth=json.loads((ROOT/"root-application-authorization.json").read_text(encoding="utf-8"))
assert auth["applicationApproved"] is True and auth["selectedChangeCount"]==84
assert auth["selectedChangesSha256"]==digest((ROOT/"selected-changes.jsonl").read_bytes())
assert auth["reviewedPackets"]["crossAuditLedgerSha256"]==digest((ROOT/"cross-audit-ledger.jsonl").read_bytes())
print(json.dumps({"result":"PASS","cells":240,"selected":84,"holds":24,"rootDispositions":dict(counts),"nestedChecksums":"PASS","placeholdersAndProtectedLiterals":"PASS"},ensure_ascii=False,indent=2))
