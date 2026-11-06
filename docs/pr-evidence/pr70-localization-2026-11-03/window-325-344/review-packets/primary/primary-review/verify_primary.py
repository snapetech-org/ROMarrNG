#!/usr/bin/env python3
import json, hashlib
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
INPUT=BASE/"input"
def sha(b): return hashlib.sha256(b).hexdigest()
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
cells=jl(INPUT/"current-target-cells.jsonl")
decisions=jl(HERE/"review-decisions.jsonl")
assert len(cells)==240 and len(decisions)==240
by={(int(c["position"]),c["locale"]):c for c in cells}
assert len(by)==240
contexts={int(x["position"]):x for x in jl(INPUT/"source-contexts.jsonl")}
seen=set()
for d in decisions:
    key=(int(d["position"]),d["locale"])
    assert key in by and key not in seen
    seen.add(key); c=by[key]; ctx=contexts[key[0]]
    assert d["callerResolutionHold"] is bool(ctx["callerResolutionHold"])
    expected_evidence=[{"path":r["path"],"lineStart":r["lineStart"],"lineEnd":r["lineEnd"],"contextSha256":r["contextSha256"],"fileSha256":r["fileSha256"],"gitBlob":r["gitBlob"]} for r in ctx.get("callerContextRefs",[])]
    assert d["callerEvidence"]==expected_evidence
    assert d["sourceId"]==c["sourceId"] and d["source"]==c["source"]
    assert d["sourceSha256"]==c["sourceSha256"]
    assert d["callerContextSha256"]==c["callerContextSha256"]
    assert d["currentTarget"]==c["currentTarget"]
    assert d["currentTargetSha256"]==c["currentTargetSha256"]
    assert d["selectedTargetSha256"]==sha(d["selectedTarget"].encode())
    assert d["decision"] in {"correction","refinement","accept-current","hold"}
    assert d["rationale"].strip()
    if d["decision"] in {"accept-current","hold"}:
        assert d["selectedTarget"]==c["currentTarget"]
    if d["decision"]=="hold":
        assert int(d["position"]) in {329,330}
        assert d["callerResolutionHold"] is True
        assert ctx["callerResolutionHold"] is True
    else:
        assert not d["callerResolutionHold"]
    assert sorted(d["placeholders"])==sorted(c["placeholderTokens"])
    assert d["sourceNumericTokens"]==c["sourceNumericTokens"]
    assert d["sourceProtectedLiterals"]==c["sourceProtectedLiterals"]
    target=d["selectedTarget"]
    for token in c["placeholderTokens"]:
        assert token in target,(key,"placeholder",token)
    for token in c["sourceNumericTokens"]:
        assert token in target,(key,"numeric",token)
    for literal in c["sourceProtectedLiterals"]:
        assert literal in target,(key,"protected literal",literal)
assert seen==set(by)
counts=Counter(d["decision"] for d in decisions)
assert counts==Counter({"correction":43,"refinement":14,"accept-current":159,"hold":24}),counts
assert all(sum(1 for d in decisions if d["position"]==p and d["decision"]=="hold")==12 for p in (329,330))
summary=json.loads((HERE/"summary.json").read_text())
assert summary["counts"]==dict(sorted(counts.items()))
assert summary["selectedCount"]==57 and summary["cellCount"]==240
assert sha((INPUT/"manifest.json").read_bytes())==summary["inputManifestJsonSha256"]
assert sha((INPUT/"SHA256SUMS.txt").read_bytes())==summary["inputChecksumListSha256"]
de=next(d for d in decisions if d["position"]==343 and d["locale"]=="de")
assert "Ubisoft Connect" in de["selectedTarget"]
assert "Ubisoft-Connect" not in de["selectedTarget"]
print("PASS: primary review reattaches to candidate-free input; 240 cells; 57 selected (43 corrections, 14 refinements); 159 accepted; 24 callerless holds; token and protected-literal checks pass.")
