#!/usr/bin/env python3
import collections, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def sha(v):
    if isinstance(v,str): v=v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()
def canonical_hash(row):
    return sha(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":")))

cross_root=ROOT/"inputs/integrated-cross-review"
blind_root=ROOT/"inputs/independent-blind-review"
cross=read_jsonl(cross_root/"integrated-cross-ledger.jsonl")
advisories=read_jsonl(cross_root/"root-change-advisories.jsonl")
blind=read_jsonl(blind_root/"blind-locale-review.jsonl")
contexts=read_jsonl(cross_root/"candidate-free-source-contexts.jsonl")
prior=read_jsonl(ROOT/"inputs/prior-root-adjudication.jsonl")
decisions=read_jsonl(ROOT/"root-followup-decisions.jsonl")
final=read_jsonl(ROOT/"final-root-adjudication.jsonl")
cross_by={r["cellId"]:r for r in cross}
cross_summary=json.loads((cross_root/"summary.json").read_text(encoding="utf-8"))
blind_by={f'{r["sourceId"]}::{r["locale"]}':r for r in blind}
context_by={r["sourceId"]:r for r in contexts}
advice_by={r["cellId"]:r for r in advisories}
decision_by={r["cellId"]:r for r in decisions}
prior_by={r["sourceId"]+"::"+r["locale"]:r for r in prior}
final_by={r["sourceId"]+"::"+r["locale"]:r for r in final}
assert len(cross)==len(prior)==len(final)==240
assert len(advisories)==len(decisions)==20
assert set(final_by)==set(prior_by)==set(cross_by)
assert len(decision_by)==20
for cell,d in decision_by.items():
    a=advice_by[cell]; c=cross_by[cell]; b=blind_by[cell]; ctx=context_by[d["sourceId"]]
    assert c["crossDisposition"]=="correction" and c["priorCrossDisposition"]=="accept-current"
    assert d["currentTarget"]==a["currentTarget"]==c["currentTarget"]
    assert d["currentTargetSha256"]==a["currentTargetSha256"]==c["currentTargetSha256"]==sha(d["currentTarget"])
    assert d["selectedTargetSha256"]==sha(d["selectedTarget"])
    assert b["proposal"]==a["blindProposal"] and b["proposalSha256"]==d["blindProposalSha256"]
    assert all(lit in d["selectedTarget"] for lit in d["pinnedManualLiterals"])
    assert ctx["sourceSha256"]==d["sourceSha256"] and ctx["contextSha256"]==d["callerContextSha256"]
    assert d["inputHead"]==cross_summary["head"]=="9714d7cf69c687685b4f65cbd9627a56830bab85"
    assert d["inputTree"]==cross_summary["tree"]=="c8eb66573f10b2390a02df05033f5133425d5e41"
    f=final_by[cell]; old=prior_by[cell]
    assert old["rootDisposition"]=="accept-current"
    assert f["rootDisposition"]=="correction" and f["after"]==d["selectedTarget"]
    assert f["afterSha256"]==d["selectedTargetSha256"]
for cell,f in final_by.items():
    assert f["crossDisposition"]==cross_by[cell]["crossDisposition"]
    if cell not in decision_by:
        old=prior_by[cell]
        assert f["rootDisposition"]==old["rootDisposition"]
        if old["callerless"]:
            assert not any(k in f for k in ("source","before","after"))
counts=collections.Counter(r["rootDisposition"] for r in final)
assert counts=={"accept-current":186,"correction":23,"refinement":7,"hold-callerless-hash-only":24},counts
summary=json.loads((ROOT/"summary.json").read_text(encoding="utf-8"))
assert summary["followupDecisionCells"]==20 and summary["totalSelectedChanges"]==30
# Check that the French blind target itself is plural-correct and the erratum rejects only the stale note.
fr="ui.optional-connections-to-the-rest-of.636208f858::fr"
assert "Connexions facultatives" in cross_by[fr]["blindProposal"]
err=json.loads((ROOT/"inputs/cross-finding-erratum/erratum.json").read_text(encoding="utf-8"))
assert err["findingStatus"]=="unsupported-stale-finding" and err["correctRootTreatment"]=="retain-accept-current-no-change"
assert final_by[fr]["rootDisposition"]=="accept-current"
print(json.dumps({"result":"PASS","followupCells":20,"finalCells":240,"finalDispositions":dict(counts),"manualLiteralFailures":0},ensure_ascii=False,indent=2))
