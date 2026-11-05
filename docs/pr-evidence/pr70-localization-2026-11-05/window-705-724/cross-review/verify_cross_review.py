#!/usr/bin/env python3
import argparse, collections, hashlib, json, subprocess, sys
from pathlib import Path

OUT=Path(__file__).resolve().parent
BASE=Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w705-724-20261105")
INPUT=BASE/"candidate-free"/"input"
PRIMARY=BASE/"primary-review"
BLIND=Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w705-724-blind-review-20261105")
DEFAULT_REPO=Path("/home/keith/Documents/code/.task-worktrees/localization-20261105/romarrng-w685")
HEAD="50e3f8a48a800affff8bad367b5c493cc0fdfd62"
TREE="22cd46ff4821fcbbe76b4760a15e22d688b3f548"
EXPECTED={
 (709,"ar"):"لا تتوفر أي صيغ للواجهة الأمامية.",
 (709,"fr"):"Aucun format frontend n’est disponible.",
 (709,"zh-Hans"):"没有可用的前端格式。",
 (709,"zh-Hant"):"沒有可用的前端格式。",
 (711,"id"):"Tidak ada game yang dikembalikan oleh pustaka.",
}
FLAGS={(709,"ar"),(709,"fr"),(711,"id")}

def sha(x):
 if isinstance(x,str): x=x.encode("utf-8")
 return hashlib.sha256(x).hexdigest()

def read(path): return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def check(path): subprocess.check_call(["sha256sum","-c","SHA256SUMS.txt"],cwd=path,stdout=subprocess.DEVNULL)
def fail(msg): raise ValueError(msg)

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo",type=Path,default=DEFAULT_REPO);a=ap.parse_args()
 check(INPUT);check(BASE/"candidate-free");check(PRIMARY);check(BLIND)
 if (OUT/"SHA256SUMS.txt").exists(): check(OUT)
 m=json.loads((INPUT/"manifest.json").read_text());pm=json.loads((PRIMARY/"manifest.json").read_text());bm=json.loads((BLIND/"summary.json").read_text())
 if (m["head"],m["tree"],m["candidateFree"],m["callerlessCellTextIncluded"])!=(HEAD,TREE,True,False): fail("candidate-free pin/boundary")
 if (pm["exactHead"],pm["exactTree"],pm["candidateFreeOnly"],pm["otherReviewOutputsUsed"],pm["textFreeHoldRows"])!=(HEAD,TREE,True,False,True): fail("primary exact pin/boundary")
 if (bm["exactPrHead"],bm["exactPrTree"],bm["records"],bm["callerlessHashOnlyHolds"])!=(HEAD,TREE,240,48): fail("blind exact pin/boundary")
 head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=a.repo,text=True).strip()
 tree=subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=a.repo,text=True).strip()
 status=subprocess.check_output(["git","status","--porcelain"],cwd=a.repo,text=True).strip()
 if (head,tree,status)!=(HEAD,TREE,""): fail(f"repo pin/clean mismatch {head} {tree} {status!r}")
 cells=read(INPUT/"candidate-free-cells.jsonl")
 contexts={x["sourceId"]:x for x in read(INPUT/"source-contexts.jsonl")}
 primary={(x["position"],x["locale"]):x for x in read(PRIMARY/"ledger.jsonl")}
 blind={(x["position"],x["locale"]):x for x in read(BLIND/"review.jsonl")}
 out=read(OUT/"cross-ledger.jsonl")
 if not (len(cells)==len(primary)==len(blind)==len(out)==240): fail("240-cell coverage")
 counts=collections.Counter(); comparisons=collections.Counter(); flagged=[]
 for c,r in zip(cells,out):
  key=(c["position"],c["locale"]);p=primary[key];b=blind[key];ctx=contexts[c["sourceId"]]
  if (r["position"],r["locale"],r["sourceId"])!=key+(c["sourceId"],): fail(f"cell order/id {key}")
  for field in ("sourceSha256","currentTargetSha256","callerContextSha256"):
   if r[field]!=c[field]: fail(f"hash binding {key} {field}")
  if r["callerless"]:
   if not c["callerless"] or r["decision"]!="hold-callerless-hash-only": fail(f"callerless disposition {key}")
   if r["sourceTextOmitted"] is not True or r["currentTargetTextOmitted"] is not True or r["selectedTargetTextOmitted"] is not True: fail(f"callerless omission flags {key}")
   if any(k in r for k in ("source","currentTarget","selectedTarget","callerBindings","primaryTarget","blindTarget","selectionRationale")): fail(f"callerless text leak {key}")
   if p["decision"]!="hold-callerless-hash-only" or b["decision"]!="hold": fail(f"callerless reviewer mapping {key}")
   if r["primaryDecision"]!="hold-callerless-hash-only" or r["blindDecision"]!="hold": fail(f"callerless reviewer labels {key}")
  else:
   if c["callerless"] or r.get("source")!=c["source"] or r.get("currentTarget")!=c["currentTarget"]: fail(f"visible text binding {key}")
   if sha(r["source"])!=r["sourceSha256"] or sha(r["currentTarget"])!=r["currentTargetSha256"]: fail(f"visible digest {key}")
   if r["callerContextSha256"]!=ctx["contextSha256"] or ctx["head"]!=HEAD or ctx["callerless"]: fail(f"caller context {key}")
   expected_callers=[{k:cr[k] for k in ("path","line","lineText","lineSha256","excerptSha256","fileSha256","gitBlob","matchKind") if k in cr} for cr in ctx["callers"]]
   if r["callerBindings"]!=expected_callers: fail(f"caller binding ledger {key}")
   if r["primaryDecision"]!=p["decision"] or r["blindDecision"]!=b["decision"]: fail(f"reviewer decision binding {key}")
   pp=p.get("proposedTarget") if p["decision"] in ("correction","refinement") else None
   bp=b.get("replacementText") if b["decision"]=="correction" else None
   if r["primaryTarget"]!=pp or r["blindTarget"]!=bp: fail(f"proposal binding {key}")
   comp="both-keep" if pp is None and bp is None else "exact-agreement" if pp and bp and pp==bp else "conflicting-targets" if pp and bp else "primary-only" if pp else "blind-only"
   if r["proposalAgreement"]!=comp: fail(f"proposal comparison {key}")
   if key in EXPECTED:
    if r["decision"]!="correction" or r["selectedTarget"]!=EXPECTED[key] or sha(r["selectedTarget"])!=r["selectedTargetSha256"]: fail(f"selected target {key}")
    proposalTargets=[x for x in (pp,bp) if x]
    if r["selectedTarget"] not in proposalTargets: fail(f"target is not a reviewed proposal {key}")
   else:
    if pp is not None or bp is not None or r["decision"]!="accept-current" or r["selectedTarget"]!=c["currentTarget"]: fail(f"unreviewed correction/current acceptance {key}")
   if not all(r["independentTokenChecks"].get(k) is True for k in ("placeholders","markupTags","numericTokens","protectedLiterals")): fail(f"token check {key}")
   if r.get("rootAdjudicationRequired"): flagged.append(key)
  counts[r["decision"]]+=1
  if not r["callerless"]: comparisons[r["proposalAgreement"]]+=1
 if counts!=collections.Counter({"accept-current":187,"correction":5,"hold-callerless-hash-only":48}): fail(f"dispositions {counts}")
 if comparisons!=collections.Counter({"both-keep":187,"exact-agreement":2,"conflicting-targets":1,"blind-only":1,"primary-only":1}): fail(f"proposal comparisons {comparisons}")
 if set(flagged)!=FLAGS: fail(f"root flags {flagged}")
 summary=json.loads((OUT/"summary.json").read_text())
 if summary["crossCounts"]!=dict(sorted(counts.items())) or summary["proposalComparisons"]!=dict(sorted(comparisons.items())) or summary["rootAdjudicationFlagCount"]!=3: fail("summary counts")
 result={"result":"PASS","verifier":"independent-cross-review","head":head,"tree":tree,"cells":len(out),"callerBacked":192,"callerlessHashOnlyHolds":48,"dispositions":dict(counts),"proposalComparisons":dict(comparisons),"rootAdjudicationFlags":sorted([{"position":p,"locale":l} for p,l in flagged],key=lambda x:(x["position"],x["locale"])),"callerlessTextExposed":False}
 (OUT/"verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
 try: main()
 except Exception as e: print("VERIFY FAILED: "+str(e),file=sys.stderr);sys.exit(1)
