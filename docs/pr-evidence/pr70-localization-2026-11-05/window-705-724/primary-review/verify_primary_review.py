#!/usr/bin/env python3
"""Verify W705-W724 primary decisions are bound to candidate-free input only."""
from __future__ import annotations
import collections, hashlib, json, re
from pathlib import Path

HEAD="50e3f8a48a800affff8bad367b5c493cc0fdfd62"
TREE="22cd46ff4821fcbbe76b4760a15e22d688b3f548"
WINDOW="W705-W724"
ROOT=Path(__file__).resolve().parent
PACKET=ROOT.parent/"candidate-free"
INPUT=PACKET/"input"
PLACEHOLDER=re.compile(r"\{[^{}]+\}")
TAG=re.compile(r"<[^>]+>")
NUMBER=re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
PROTECTED=["Gaseous","Retrom","SeerrNG","ROMarrNG","ROMarr","ES-DE","No-Intro","Redump","DAT","IGDB","ISO9660","PLAYSTATION","PlayStation","PS2","ROMs","ROM","PC","API","ROMARR_API_KEY","Linksnappy","Moonlight","PIN","NPSSO","NZBHydra2","Newznab","/torznab/api","NZBVortex","HTTPS","NZB","Preferences"]
EXPECTED={
 (709,"fr"):("refinement","Aucun format de frontend disponible."),
 (711,"id"):("correction","Tidak ada game yang dikembalikan oleh pustaka."),
 (709,"zh-Hans"):("correction","没有可用的前端格式。"),
 (709,"zh-Hant"):("correction","沒有可用的前端格式。"),
}
def sha(v):
    if isinstance(v,str):v=v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def rj(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def rjl(p):return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
def fail(msg):raise SystemExit("FAIL "+msg)
def verify_sums(root):
    root=Path(root);sf=root/"SHA256SUMS.txt";listed={}
    for line in sf.read_text(encoding="utf-8").splitlines():
        if not line.strip():continue
        digest,rel=line.split("  ",1);path=(root/rel).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes())!=digest:fail(f"checksum {rel}")
        if rel in listed:fail(f"duplicate checksum {rel}")
        listed[rel]=digest
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p!=sf}
    if set(listed)!=actual:fail(f"checksum coverage {root}")
def token_signatures(s):
    def prot(v):
        out=[]
        for x in PROTECTED:
            found=x in v if x.startswith("/") else bool(re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",v))
            if found:out.append(x)
        return sorted(set(out))
    return {"placeholders":PLACEHOLDER.findall(s),"markup":TAG.findall(s),"numbers":NUMBER.findall(s),"protectedLiterals":prot(s)}
def token_compatible(source,target):
    s,t=token_signatures(source),token_signatures(target)
    placeholders=collections.Counter(s["placeholders"])==collections.Counter(t["placeholders"])
    markup=collections.Counter(s["markup"])==collections.Counter(t["markup"])
    sn,tn=collections.Counter(s["numbers"]),collections.Counter(t["numbers"]);extra=list((tn-sn).elements())
    presentation=bool(re.search(r"\bzero\b",source,re.I) and not s["numbers"] and extra==["0"])
    numeric=not (sn-tn) and (not extra or presentation)
    protected=all(x in target for x in s["protectedLiterals"])
    return placeholders and markup and numeric and protected
def main():
    verify_sums(INPUT);verify_sums(ROOT)
    packet=rj(INPUT/"manifest.json");manifest=rj(ROOT/"manifest.json")
    if (packet.get("head"),packet.get("tree"),packet.get("window"),packet.get("candidateFree"))!=(HEAD,TREE,WINDOW,True):fail("candidate-free exact pin")
    if (manifest.get("exactHead"),manifest.get("exactTree"),manifest.get("candidateFreeOnly"),manifest.get("otherReviewOutputsUsed"),manifest.get("textFreeHoldRows"))!=(HEAD,TREE,True,False,True):fail("primary manifest boundary/pin")
    if sha((INPUT/"manifest.json").read_bytes())!=manifest["candidateFreeManifestSha256"] or sha((INPUT/"SHA256SUMS.txt").read_bytes())!=manifest["candidateFreeChecksumIndexSha256"]:fail("candidate-free input manifest/checksum binding")
    cells=rjl(INPUT/"candidate-free-cells.jsonl");ledger=rjl(ROOT/"ledger.jsonl");proposals=rjl(ROOT/"proposals.jsonl");holds=rjl(ROOT/"holds.jsonl")
    if (len(cells),len(ledger),len(proposals),len(holds))!=(240,240,4,48):fail("primary row counts")
    proposal_map={(r["position"],r["locale"]):r for r in proposals}
    if len(proposal_map)!=4:fail("duplicate proposal key")
    hold_map={(r["position"],r["locale"]):r for r in holds}
    if len(hold_map)!=48:fail("duplicate hold key")
    decisions=collections.Counter();confidences=collections.Counter(); proposal_keys=set()
    for source,review in zip(cells,ledger):
        key=(source["position"],source["locale"])
        for field in ("window","position","catalogZeroBasedIndex","sourceId","sourceSha256","locale","currentTargetSha256","callerContextSha256"):
            if source[field]!=review[field]:fail(f"candidate-free binding {key} {field}")
        if review.get("window")!=WINDOW:fail(f"window {key}")
        if source["callerless"]:
            if review.get("decision")!="hold-callerless-hash-only" or review.get("textOmitted") is not True or review.get("confidence")!="unknown":fail(f"callerless hold decision {key}")
            if any(k in review for k in ("source","sourceText","currentTarget","target","targetText","proposedTarget")):fail(f"callerless ledger text leak {key}")
            h=hold_map.get(key)
            if not h or any(k in h for k in ("source","sourceText","currentTarget","target","targetText","proposedTarget")):fail(f"callerless hold artifact leak {key}")
            for field in ("sourceId","sourceSha256","locale","currentTargetSha256","callerContextSha256","decision","textOmitted"):
                if h[field]!=review[field]:fail(f"hold/ledger binding {key} {field}")
            if any(k in source for k in ("source","currentTarget","sourceText","currentTargetText")):fail(f"callerless input text leak {key}")
        else:
            if review.get("source")!=source.get("source") or review.get("currentTarget")!=source.get("currentTarget"):fail(f"caller-backed text binding {key}")
            if sha(review["source"])!=review["sourceSha256"] or sha(review["currentTarget"])!=review["currentTargetSha256"]:fail(f"caller-backed text hash {key}")
            if review.get("literalCallerCount")!=source["literalCallerCount"]:fail(f"caller count binding {key}")
            if review.get("confidence") not in ("high","moderate","low"):fail(f"confidence {key}")
            if review.get("decision") not in ("accept-current","correction","refinement"):fail(f"decision {key}")
            if review.get("decision")=="accept-current":
                if any(k in review for k in ("proposedTarget","proposedTargetSha256")):fail(f"accept-current includes proposal {key}")
            else:
                proposal=proposal_map.get(key)
                if not proposal:fail(f"missing proposal row {key}")
                expected=EXPECTED.get(key)
                if not expected or (review["decision"],review.get("proposedTarget"))!=expected:fail(f"unexpected proposal {key}")
                if proposal.get("proposedTarget")!=review["proposedTarget"] or proposal.get("proposedTargetSha256")!=sha(review["proposedTarget"]):fail(f"proposal target binding {key}")
                if proposal.get("callerContextSha256")!=source["callerContextSha256"] or proposal.get("currentTargetSha256")!=source["currentTargetSha256"]:fail(f"proposal input binding {key}")
                if not token_compatible(source["source"],review["proposedTarget"]):fail(f"proposal token mismatch {key}")
                if review.get("proposalTokenCheck")!="PASS":fail(f"proposal token attestation {key}")
                proposal_keys.add(key)
            if not review.get("rationale"):fail(f"missing rationale {key}")
        decisions[review["decision"]]+=1;confidences[review["confidence"]]+=1
    if proposal_keys!=set(proposal_map):fail("proposal ledger exact coverage")
    if set(hold_map)!={(r["position"],r["locale"]) for r in ledger if r["decision"]=="hold-callerless-hash-only"}:fail("hold ledger exact coverage")
    summary=rj(ROOT/"summary.json")
    if (summary.get("exactHead"),summary.get("exactTree"),summary.get("cellCount"),summary.get("callerBackedCells"),summary.get("callerlessHashOnlyHolds"),summary.get("proposalCount"))!=(HEAD,TREE,240,192,48,4):fail("primary summary coverage")
    if summary.get("decisionCounts")!=dict(sorted(decisions.items())) or manifest.get("decisionCounts")!=dict(sorted(decisions.items())):fail("decision count summary")
    if summary.get("confidenceCounts")!=dict(sorted(confidences.items())):fail("confidence count summary")
    if summary.get("independence")!="The primary review used only the sealed candidate-free input. No blind, cross-review, or other reviewer output was read.":fail("independence declaration")
    lineage=rj(INPUT/"prior-window-lineage.json")
    if lineage.get("w665EvidenceRestoration",{}).get("currentMissingFiles")!=[] or lineage.get("w665EvidenceRestoration",{}).get("currentMismatchedFiles")!=[]:fail("W665 restoration lineage")
    print(json.dumps({"result":"PASS","head":HEAD,"tree":TREE,"cells":len(ledger),"callerlessHashOnlyHolds":len(holds),"proposals":len(proposals),"decisionCounts":dict(sorted(decisions.items())),"candidateFreeOnly":True,"blindOrCrossOutputsRead":False},sort_keys=True))
if __name__=="__main__":main()
