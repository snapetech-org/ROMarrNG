#!/usr/bin/env python3
import collections, hashlib, json, re
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent/"primary"
INPUT=ROOT/"input"
PRIMARY=ROOT/"primary-review"
BLIND=OUT.parent/"blind"/"review"
def loadj(p): return json.loads(p.read_text())
def loadl(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(b): return hashlib.sha256(b).hexdigest()
def verify_sums(directory, name):
    for line in (directory/name).read_text().splitlines():
        if not line.strip(): continue
        expected, rel = line.split(None,1); rel=rel.lstrip(" *")
        path=directory/rel
        assert path.is_file(), f"missing checksum target {path}"
        assert sha(path.read_bytes())==expected, f"checksum mismatch {path}"
def main():
    verify_sums(INPUT,"SHA256SUMS.txt")
    verify_sums(ROOT,"SHA256SUMS.txt")
    verify_sums(BLIND,"SHA256SUMS.txt")
    verify_sums(OUT,"SHA256SUMS.txt")
    side=(OUT/"SHA256SUMS.txt.sha256").read_text().split()[0]
    assert sha((OUT/"SHA256SUMS.txt").read_bytes())==side
    summary=loadj(OUT/"summary.json")
    manifest=loadj(INPUT/"manifest.json")
    live=loadj(OUT/"live-reattestation.json")
    assert (live["head"],live["tree"],live["branchRefSha"],live["pullRefSha"])==(manifest["head"],manifest["tree"],manifest["head"],manifest["head"])
    assert live["state"]=="open" and live["draft"] is True and live["baseRef"]=="main"
    cells=loadl(INPUT/"current-target-cells.jsonl")
    P={(x["position"],x["locale"]):x for x in loadl(PRIMARY/"review-decisions.jsonl")}
    B={(x["position"],x["locale"]):x for x in loadl(BLIND/"blind-ledger.jsonl")}
    C={(x["position"],x["locale"]):x for x in cells}
    rows=loadl(OUT/"cross-audit-ledger.jsonl")
    keyed={(x["position"],x["locale"]):x for x in rows}
    expected={(p,l) for p in range(325,345) for l in manifest["locales"]}
    assert len(rows)==240 and len(keyed)==240 and set(keyed)==expected
    for key,row in keyed.items():
        c,p,b=C[key],P[key],B[key]
        assert row["sourceId"]==c["sourceId"] and row["sourceSha256"]==c["sourceSha256"]
        assert row["currentTarget"]==c["currentTarget"] and row["currentTargetSha256"]==c["currentTargetSha256"]
        assert row["primaryTarget"]==p["selectedTarget"] and row["blindTarget"]==b.get("blindTarget")
        assert row["selectedTargetSha256"]==sha(row["selectedTarget"].encode())
        assert row["primaryTargetSha256"]==sha(row["primaryTarget"].encode())
        if row["blindTarget"] is not None: assert row["blindTargetSha256"]==sha(row["blindTarget"].encode())
        source=row["source"]; target=row["selectedTarget"]
        srcph=collections.Counter(re.findall(r"\{[^{}]+\}",source))
        dstph=collections.Counter(re.findall(r"\{[^{}]+\}",target))
        assert srcph==dstph, (key,"placeholder",srcph,dstph)
        for token in row["sourceNumericTokens"]: assert target.count(str(token))>=row["sourceNumericTokens"].count(token), (key,"numeric",token)
        for literal in row["sourceProtectedLiterals"]: assert literal in target, (key,"protected",literal)
        assert re.findall(r"</?[A-Za-z][^>]*>",source)==re.findall(r"</?[A-Za-z][^>]*>",target), (key,"markup")
        assert row["structuralChecks"]=={"placeholdersMatch":True,"numericTokensPreserved":True,"protectedLiteralsPreserved":True,"markupTokensMatch":True}
        if key[0] in (329,330):
            assert row["callerResolutionHold"] and row["crossAuditDisposition"]=="hold" and target==row["currentTarget"]
        else:
            assert not row["callerResolutionHold"] and row["crossAuditDisposition"]!="hold"
    assert sum(x["crossAuditDisposition"]=="hold" for x in rows)==24
    assert sum(not x["proposalTargetAgreement"] and x["position"] not in (329,330) for x in rows)==42
    assert len(loadl(OUT/"disagreements.jsonl"))==42
    changes=loadl(OUT/"selected-changes-proposal.jsonl")
    assert len(changes)==summary["selectedChanges"]
    assert all(x["target"]!=x["currentTarget"] for x in changes)
    assert summary["totalCells"]==240 and summary["mandatoryCallerlessHoldCells"]==24
    assert summary["additionalHolds"]==0 and summary["unresolvedTargetDisagreements"]==0
    for name,expected_hash in summary["outputHashes"].items():
        assert sha((OUT/name).read_bytes())==expected_hash, f"output hash mismatch {name}"
    print(f"PASS: 240 cells; {len(changes)} proposed updates; 24 required callerless holds; 42 disagreements adjudicated; all input/output checksums, pins, targets, and token checks verified.")
if __name__=="__main__": main()
