#!/usr/bin/env python3
"""Build an independent primary semantic review from the sealed candidate-free input only."""
from __future__ import annotations
import collections, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

HEAD = "c3f92c45b4b4f8d79a8caa99417f9970ebc42a26"
TREE = "3f835643e4f557999d533c3e832fc92036d4b01a"
WINDOW = "W725-W744"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
HERE = Path(__file__).resolve().parent
PACKET = HERE.parent / "candidate-free"
INPUT = PACKET / "input"
ROOT = HERE
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
TAG = re.compile(r"<[^>]+>")
NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
PROTECTED = ["Gaseous", "Retrom", "SeerrNG", "ROMarrNG", "ROMarr", "ES-DE", "No-Intro", "Redump", "DAT", "IGDB", "ISO9660", "PLAYSTATION", "PlayStation", "PS2", "ROMs", "ROM", "PC", "API", "ROMARR_API_KEY", "Linksnappy", "Moonlight", "PIN", "NPSSO", "NZBHydra2", "Newznab", "/torznab/api", "NZBVortex", "HTTPS", "NZB", "Preferences"]

# Primary judgments authored from the sealed candidate-free source/current text and caller context only.
DECISIONS = {
    (728, "de"): {"decision": "refinement", "confidence": "moderate", "proposedTarget": "Derzeit wird kein Set beschafft.", "rationale": "In ROMarr, acquisition covers finding and fetching a game set. The current 'erworben' can suggest a purchase; 'beschafft' keeps the broader acquisition meaning."},
    (734, "ko"): {"decision": "refinement", "confidence": "moderate", "proposedTarget": "미발표", "rationale": "The UI uses this for an upcoming game's release date. The current '미정' says the date is undecided; '미발표' says it has not been announced, matching the English."},
    (735, "de"): {"decision": "correction", "confidence": "high", "proposedTarget": "Nicht verfügbar", "rationale": "This is a standalone status after an icon. German capitalizes the first word of the displayed status."},
    (740, "ar"): {"decision": "correction", "confidence": "high", "proposedTarget": "ملاحظات", "rationale": "The current Arabic means footnotes. In the ES-DE metadata field, 'Notes' means general notes; 'ملاحظات' is the direct UI label."},
    (743, "de"): {"decision": "refinement", "confidence": "moderate", "proposedTarget": "Keine Spiele mit einem zukünftigen Erscheinungsdatum.", "rationale": "This empty state appears in the upcoming-games view. 'Termine' suggests appointments; this wording identifies games with a future release date."},
}

def sha(v):
    if isinstance(v, str): v = v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()
def canon(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
def rj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
def wj(p, v):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
def wjl(p, rows):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for x in rows), encoding="utf-8")
def tokens(s):
    def prot(v):
        out=[]
        for x in PROTECTED:
            found=x in v if x.startswith("/") else bool(re.search(r"(?<![A-Za-z0-9])"+re.escape(x)+r"(?![A-Za-z0-9])",v))
            if found: out.append(x)
        return sorted(set(out))
    return {"placeholders":PLACEHOLDER.findall(s),"markup":TAG.findall(s),"numbers":NUMBER.findall(s),"protectedLiterals":prot(s)}
def token_check(source,target):
    a,b=tokens(source),tokens(target)
    return {"source":a,"target":b,"matches":a==b}
def write_sums(root):
    root=Path(root); target=root/"SHA256SUMS.txt"
    files=sorted(p for p in root.rglob("*") if p.is_file() and p!=target)
    target.write_text("".join(f"{sha(p.read_bytes())}  {p.relative_to(root).as_posix()}\n" for p in files),encoding="utf-8")
def main():
    if any(p.is_file() for p in ROOT.iterdir() if p.name not in ("build_primary_review.py", "verify_primary_review.py")):
        raise SystemExit("FAIL primary-review output directory is not empty")
    if any(p.is_file() for p in ROOT.rglob("__pycache__")): raise SystemExit("FAIL unexpected bytecode cache")
    packet_manifest=rj(INPUT/"manifest.json")
    if (packet_manifest.get("head"),packet_manifest.get("tree"),packet_manifest.get("window"),packet_manifest.get("candidateFree"))!=(HEAD,TREE,WINDOW,True): raise SystemExit("FAIL exact candidate-free input pin")
    cells=rjl(INPUT/"candidate-free-cells.jsonl"); contexts={r["sourceId"]:r for r in rjl(INPUT/"source-contexts.jsonl")}
    if len(cells)!=240 or len(contexts)!=20: raise SystemExit("FAIL candidate-free input coverage")
    ledger=[]; proposals=[]; holds=[]; decisions=collections.Counter(); confidences=collections.Counter(); by_locale=collections.Counter(); by_position=collections.Counter()
    for cell in cells:
        sid,loc,pos=cell["sourceId"],cell["locale"],cell["position"]
        if cell["callerless"]:
            row={"window":WINDOW,"position":pos,"catalogZeroBasedIndex":cell["catalogZeroBasedIndex"],"sourceId":sid,"sourceSha256":cell["sourceSha256"],"locale":loc,"currentTargetSha256":cell["currentTargetSha256"],"callerContextSha256":cell["callerContextSha256"],"decision":"hold-callerless-hash-only","confidence":"unknown","rationale":"No exact production caller was found; source and current-target text remain omitted.","textOmitted":True}
            if any(k in cell for k in ("source","currentTarget","sourceText","currentTargetText")): raise SystemExit(f"FAIL callerless input leak {sid}/{loc}")
            holds.append(row); decisions["hold-callerless-hash-only"]+=1; confidences["unknown"]+=1
        else:
            spec=DECISIONS.get((pos,loc),{"decision":"accept-current","confidence":"moderate","rationale":"The current translation preserves the source message in its caller-backed UI context."})
            row={"window":WINDOW,"position":pos,"catalogZeroBasedIndex":cell["catalogZeroBasedIndex"],"catalogOneBasedPosition":cell["catalogOneBasedPosition"],"sourceId":sid,"sourceSha256":cell["sourceSha256"],"locale":loc,"source":cell["source"],"currentTarget":cell["currentTarget"],"currentTargetSha256":cell["currentTargetSha256"],"callerContextSha256":cell["callerContextSha256"],"literalCallerCount":cell["literalCallerCount"],"decision":spec["decision"],"confidence":spec["confidence"],"rationale":spec["rationale"]}
            if sha(row["source"])!=row["sourceSha256"] or sha(row["currentTarget"])!=row["currentTargetSha256"]: raise SystemExit(f"FAIL candidate-free source/current hash {sid}/{loc}")
            if row["decision"] in ("correction","refinement"):
                proposal=spec["proposedTarget"]
                if not isinstance(proposal,str) or not proposal: raise SystemExit(f"FAIL missing proposal {sid}/{loc}")
                check=token_check(row["source"],proposal)
                if not check["matches"]: raise SystemExit(f"FAIL proposal token mismatch {sid}/{loc}: {check}")
                row.update({"proposedTarget":proposal,"proposedTargetSha256":sha(proposal),"proposalTokenCheck":"PASS"})
                proposals.append({k:row[k] for k in ("window","position","catalogZeroBasedIndex","catalogOneBasedPosition","sourceId","sourceSha256","locale","source","currentTarget","currentTargetSha256","proposedTarget","proposedTargetSha256","callerContextSha256","decision","confidence","rationale","proposalTokenCheck")})
            elif row["decision"]!="accept-current": raise SystemExit(f"FAIL unknown decision {row['decision']}")
            decisions[row["decision"]]+=1; confidences[row["confidence"]]+=1; by_locale[loc]+=row["decision"]!="accept-current"; by_position[str(pos)]+=row["decision"]!="accept-current"
        ledger.append(row)
    if len(ledger)!=240 or len(holds)!=12 or len(proposals)!=5: raise SystemExit("FAIL primary review decision coverage")
    reviewed=datetime.now(timezone.utc).isoformat(timespec="seconds")
    wjl(ROOT/"ledger.jsonl",ledger); wjl(ROOT/"proposals.jsonl",proposals); wjl(ROOT/"holds.jsonl",holds)
    token_summary=rj(INPUT/"candidate-free-token-summary.json")
    summary={"artifact":"ROMarrNG PR #70 W725-W744 independent primary semantic review","pullRequest":70,"exactHead":HEAD,"exactTree":TREE,"reviewedAtUtc":reviewed,"cellCount":240,"sourceCount":20,"localeCount":12,"callerBackedCells":sum(not c["callerless"] for c in cells),"callerlessHashOnlyHolds":len(holds),"callerlessSourceCount":sum(c["callerless"] for c in contexts.values()),"decisionCounts":dict(sorted(decisions.items())),"proposalCount":len(proposals),"proposalCountsByLocale":dict(sorted((k,int(v)) for k,v in by_locale.items() if v)),"proposalCountsByPosition":dict(sorted((k,int(v)) for k,v in by_position.items() if v)),"confidenceCounts":dict(sorted(confidences.items())),"tokenAudit":{"candidateFreeReportedCounts":token_summary,"allRecommendedTargetsPassPlaceholderMarkupNumericAndProtectedLiteralChecks":True,"finding":"The candidate-free token audit reports zero placeholder, markup, numeric, numeric-presentation, and protected-literal mismatches."},"hashOnlyHoldPolicy":f"All {len(holds)} callerless cells remain holds and contain hashes, positions, locales, and caller-context hashes only; source and current-target text are omitted.","independence":"The primary review used only the sealed candidate-free input. No blind, cross-review, or other reviewer output was read.","limitations":["No qualified native-speaker second review or runtime visual review was performed.","Callerless cells cannot be semantically assessed without text and remain held."]}
    wj(ROOT/"summary.json",summary)
    input_manifest_sha=sha((INPUT/"manifest.json").read_bytes()); input_sums_sha=sha((INPUT/"SHA256SUMS.txt").read_bytes())
    files={name:sha((ROOT/name).read_bytes()) for name in ("ledger.jsonl","proposals.jsonl","holds.jsonl","summary.json")}
    wj(ROOT/"manifest.json",{"artifact":"primary-review","repository":"snapetech-org/ROMarrNG","pullRequest":70,"exactHead":HEAD,"exactTree":TREE,"branch":"task/localization-translation-review-20261030","candidateFreeInputPath":"../candidate-free/input/","candidateFreeManifestSha256":input_manifest_sha,"candidateFreeChecksumIndexSha256":input_sums_sha,"cellCount":240,"callerBackedCells":sum(not c["callerless"] for c in cells),"hashOnlyHolds":len(holds),"proposalCount":len(proposals),"decisionCounts":dict(sorted(decisions.items())),"candidateFreeOnly":True,"otherReviewOutputsUsed":False,"textFreeHoldRows":True,"allRecommendedTargetsTokenChecked":True,"fileHashes":files,"createdAtUtc":reviewed})
    (ROOT/"README.md").write_text(f"""# ROMarrNG PR #70 W725–W744 primary review

This independent primary review covers catalog insertion indices 725–744 (one-based positions 726–745), all 12 locales, and all 240 cells at PR head `{HEAD}` / tree `{TREE}`.

The review used only the sealed candidate-free packet. It recorded {decisions['accept-current']} accept-current decisions, {decisions['correction']} corrections, {decisions['refinement']} refinements, and {len(holds)} callerless hash-only holds. The {len(proposals)} proposals are bound to their exact candidate-free source/current-target rows and caller-context hashes. All {len(holds)} callerless cells contain hashes and positions only; source and target text are omitted.

The candidate-free audit reports zero placeholder, markup, numeric, numeric-presentation, and protected-literal mismatches. Each proposal passes those token checks. The W665 evidence restoration is recorded in candidate-free lineage as complete; the inherited W625 and W645 caveats remain explicit.

No blind, cross-review, or other reviewer output was read. No qualified native-speaker second review or runtime visual review is claimed. No tests, builds, scans, or CI jobs were run.

Run `python3 verify_primary_review.py` to verify the review packet and its binding to the candidate-free input.
""",encoding="utf-8")
    write_sums(ROOT)
    print(json.dumps({"result":"PRIMARY_REVIEW_BUILT","cells":len(ledger),"holds":len(holds),"proposals":len(proposals),"decisionCounts":dict(sorted(decisions.items())),"confidenceCounts":dict(sorted(confidences.items()))},ensure_ascii=False,sort_keys=True))
if __name__=="__main__": main()
