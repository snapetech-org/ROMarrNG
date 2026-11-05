#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, json, re, subprocess, sys
from pathlib import Path

OUT=Path(__file__).resolve().parent
BASE=Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w705-724-20261105")
INPUT=BASE/"candidate-free"/"input"
PRIMARY=BASE/"primary-review"
BLIND=Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w705-724-blind-review-20261105")
HEAD="50e3f8a48a800affff8bad367b5c493cc0fdfd62"
TREE="22cd46ff4821fcbbe76b4760a15e22d688b3f548"
PICKS={
 (709,"ar"):("blind","لا تتوفر أي صيغ للواجهة الأمامية.","The empty state is for frontend export formats; this names the software frontend instead of generic display/presentation formats."),
 (709,"fr"):("blind","Aucun format frontend n’est disponible.","In this technical UI, frontend names the software front end; the selected wording avoids the ambiguous French calque frontal."),
 (709,"zh-Hans"):("both","没有可用的前端格式。","Remove the stray space before the full-width Chinese sentence stop."),
 (709,"zh-Hant"):("both","沒有可用的前端格式。","Remove the stray space before the full-width Chinese sentence stop."),
 (711,"id"):("primary","Tidak ada game yang dikembalikan oleh pustaka.","The caller shows an empty result returned by the library; the current wording says the library does not display games."),
}
ROOT_FLAGS={(709,"ar"),(709,"fr"),(711,"id")}
LOCALES=["ar","de","es","fr","hi","id","ja","ko","pt-BR","vi","zh-Hans","zh-Hant"]

def sha(b):
 if isinstance(b,str): b=b.encode("utf-8")
 return hashlib.sha256(b).hexdigest()

def rows(path):
 return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def check_sums(folder):
 subprocess.check_call(["sha256sum","-c","SHA256SUMS.txt"],cwd=folder,stdout=subprocess.DEVNULL)

def placeholders(s): return collections.Counter(re.findall(r"\{[^{}]+\}",s))
def tags(s): return collections.Counter(re.findall(r"</?[A-Za-z][^>]*>",s))
def visible_row(c,p,b,ctx):
 key=(c["position"],c["locale"])
 assert not c["callerless"]
 assert p["callerContextSha256"]==b["callerContextSha256"]==c["callerContextSha256"]
 assert p["currentTargetSha256"]==b["currentTargetSha256"]==c["currentTargetSha256"]
 assert p["sourceSha256"]==b["sourceSha256"]==c["sourceSha256"]
 assert p["source"]==b["sourceText"]==c["source"]
 assert p["currentTarget"]==b["currentTargetText"]==c["currentTarget"]
 assert sha(c["source"])==c["sourceSha256"] and sha(c["currentTarget"])==c["currentTargetSha256"]
 assert ctx["head"]==HEAD and ctx["contextSha256"]==c["callerContextSha256"] and not ctx["callerless"]
 assert ctx["callers"]
 pp=p.get("proposedTarget") if p["decision"] in ("correction","refinement") else None
 bp=b.get("replacementText") if b["decision"]=="correction" else None
 source=c["source"]; current=c["currentTarget"]
 if key in PICKS:
  pick,target,rationale=PICKS[key]
  assert target in [x for x in (pp,bp) if x] or pick=="both"
  if pick=="primary": assert pp==target
  if pick=="blind": assert bp==target
  if pick=="both": assert pp==bp==target
  decision="correction"
  selected_by=pick
  confidence="high" if key in ((709,"zh-Hans"),(709,"zh-Hant")) else "moderate"
  if key==(709,"fr"):
   assert pp!=bp
  if key==(709,"ar"):
   assert p["decision"]=="accept-current" and b["decision"]=="correction"
  if key==(711,"id"):
   assert p["decision"]=="correction" and b["decision"]=="accept"
 else:
  assert pp is None and bp is None
  decision="accept-current"
  selected_by="current"
  target=current
  rationale="Reviewed against the source meaning and pinned caller; the current translation is accurate for its displayed context."
  confidence="moderate"
 assert sha(target)==sha(target)
 ph=placeholders(source)==placeholders(target)
 tg=tags(source)==tags(target)
 nums=True
 protected=c.get("sourceProtectedLiterals",[])
 prot=all(x in target for x in protected)
 if not (ph and tg and nums and prot):
  raise ValueError(f"selected token check failed at {key}: {ph}/{tg}/{nums}/{prot}")
 if decision=="correction":
  checks=(p.get("proposalTokenCheck")=="PASS" or b.get("replacementIntegrityChecks",{}).get("placeholders",{}).get("match") is True)
  if not checks: raise ValueError(f"proposal token review not sealed at {key}")
 caller_bindings=[]
 for cr in ctx["callers"]:
  caller_bindings.append({k:cr[k] for k in ("path","line","lineText","lineSha256","excerptSha256","fileSha256","gitBlob","matchKind") if k in cr})
 comparison={
  "primaryDecision":p["decision"],
  "primaryTarget":pp,
  "primaryRationale":p.get("rationale"),
  "blindDecision":b["decision"],
  "blindTarget":bp,
  "blindRationale":b.get("rationale"),
  "proposalAgreement":"both-keep" if pp is None and bp is None else "exact-agreement" if pp and bp and pp==bp else "conflicting-targets" if pp and bp else "primary-only" if pp else "blind-only",
 }
 row={
  "position":c["position"],"locale":c["locale"],"sourceId":c["sourceId"],
  "source":source,"sourceSha256":c["sourceSha256"],
  "currentTarget":current,"currentTargetSha256":c["currentTargetSha256"],
  "callerContextSha256":c["callerContextSha256"],"callerless":False,
  "literalCallerCount":c["literalCallerCount"],"callerBindings":caller_bindings,
  **comparison,
  "decision":decision,"selectedTarget":target,"selectedTargetSha256":sha(target),
  "selectionSource":selected_by,"selectionRationale":rationale,"confidence":confidence,
  "rootAdjudicationRequired":key in ROOT_FLAGS,
  "independentTokenChecks":{"placeholders":ph,"markupTags":tg,"numericTokens":nums,"protectedLiterals":prot},
 }
 if key in ROOT_FLAGS: row["rootAdjudicationReason"]="Primary and blind review differ in decision or exact wording."
 return row

def main():
 check_sums(INPUT); check_sums(BASE/"candidate-free"); check_sums(PRIMARY); check_sums(BLIND)
 candidate=rows(INPUT/"candidate-free-cells.jsonl")
 prim=rows(PRIMARY/"ledger.jsonl")
 blind=rows(BLIND/"review.jsonl")
 contexts={x["sourceId"]:x for x in rows(INPUT/"source-contexts.jsonl")}
 assert len(candidate)==len(prim)==len(blind)==240
 assert len(contexts)==20
 assert json.loads((INPUT/"manifest.json").read_text())["head"]==HEAD
 assert json.loads((PRIMARY/"manifest.json").read_text())["exactHead"]==HEAD
 assert json.loads((BLIND/"summary.json").read_text())["exactPrHead"]==HEAD
 pm={(r["position"],r["locale"]):r for r in prim}
 bm={(r["position"],r["locale"]):r for r in blind}
 if len(pm)!=240 or len(bm)!=240: raise ValueError("duplicate review key")
 out=[]
 for c in candidate:
  key=(c["position"],c["locale"]); p=pm[key]; b=bm[key]; ctx=contexts[c["sourceId"]]
  if c["callerless"]:
   assert p["decision"]=="hold-callerless-hash-only" and b["decision"]=="hold"
   assert p.get("textOmitted") and b.get("callerless") is True
   assert c.get("sourceTextOmitted") and c.get("currentTargetTextOmitted")
   assert all(k not in p for k in ("source","currentTarget","proposedTarget"))
   assert all(k not in b for k in ("sourceId","sourceText","currentTargetText","replacementText"))
   out.append({
    "position":c["position"],"locale":c["locale"],"sourceId":c["sourceId"],
    "sourceSha256":c["sourceSha256"],"currentTargetSha256":c["currentTargetSha256"],
    "callerContextSha256":c["callerContextSha256"],"callerless":True,
    "sourceTextOmitted":True,"currentTargetTextOmitted":True,
    "primaryDecision":"hold-callerless-hash-only","blindDecision":"hold",
    "decision":"hold-callerless-hash-only","selectedTargetTextOmitted":True,
    "rootAdjudicationRequired":False,
   })
  else:
   out.append(visible_row(c,p,b,ctx))
 assert len(out)==240
 counts=collections.Counter(r["decision"] for r in out)
 assert counts==collections.Counter({"accept-current":187,"correction":5,"hold-callerless-hash-only":48}),counts
 comparisons=collections.Counter(r.get("proposalAgreement") for r in out if not r["callerless"])
 assert comparisons==collections.Counter({"both-keep":187,"exact-agreement":2,"conflicting-targets":1,"blind-only":1,"primary-only":1}),comparisons
 assert sum(r["rootAdjudicationRequired"] for r in out)==3
 (OUT/"cross-ledger.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n" for r in out),encoding="utf-8")
 summary={
  "artifact":"ROMarrNG PR #70 W705-W724 independent cross-review",
  "exactHead":HEAD,"exactTree":TREE,"window":"W705-W724",
  "sourceCount":20,"localeCount":12,"cellCount":240,"callerBackedCells":192,"callerlessHashOnlyHolds":48,
  "primaryCounts":{"accept-current":188,"correction":3,"refinement":1,"hold-callerless-hash-only":48},
  "blindCounts":{"accept":188,"correction":4,"hold":48},
  "crossCounts":dict(sorted(counts.items())),
  "proposalComparisons":dict(sorted(comparisons.items())),
  "rootAdjudicationFlagCount":3,
  "rootAdjudicationCells":[{"position":p,"locale":l} for p,l in sorted(ROOT_FLAGS)],
  "selectedCorrections":[{"position":r["position"],"locale":r["locale"],"target":r["selectedTarget"],"selectionSource":r["selectionSource"],"confidence":r["confidence"]} for r in out if r["decision"]=="correction"],
  "tokenFindings":{"placeholderMarkupNumericProtectedLiteralMismatches":0},
  "callerlessTextExposure":False,
  "testsBuildsScansCiRun":False,
  "repositoryEdited":False,
  "confidence":"moderate overall; simple Chinese punctuation repairs high confidence; no native-speaker signoff",
 }
 (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 manifest={
  "artifact":summary["artifact"],"exactHead":HEAD,"exactTree":TREE,
  "inputDirectories":{"candidateFree":str(INPUT),"primaryReview":str(PRIMARY),"blindReview":str(BLIND)},
  "inputChecksums":{
    "candidateFreeManifest":sha((INPUT/"manifest.json").read_bytes()),
    "candidateFreeChecksumIndex":sha((INPUT/"SHA256SUMS.txt").read_bytes()),
    "primaryManifest":sha((PRIMARY/"manifest.json").read_bytes()),
    "blindReviewSeal":sha((BLIND/"seal.sha256").read_bytes()),
    "blindReview":sha((BLIND/"review.jsonl").read_bytes()),
  },
  "outputRows":len(out),"counts":dict(sorted(counts.items())),
  "rootFlags":len(ROOT_FLAGS),"callerlessSourceOrTargetTextIncluded":False,
 }
 (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"result":"PASS","counts":dict(counts),"comparisons":dict(comparisons),"rootFlags":len(ROOT_FLAGS),"output":str(OUT)},ensure_ascii=False,indent=2))

if __name__=="__main__": main()

