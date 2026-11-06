#!/usr/bin/env python3
"""Read back all 240 reviewed cells and catalog invariants after application."""
import argparse, hashlib, json, subprocess
from pathlib import Path

def sha(b): return hashlib.sha256(b).hexdigest()
def textsha(s): return sha(s.encode("utf-8"))
def value_hash(v): return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8"))
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def rows(p): return [json.loads(s) for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--repo",type=Path,required=True); ap.add_argument("--plan",type=Path,required=True); ap.add_argument("--candidate-free",type=Path,required=True); ap.add_argument("--root-ledger",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
 repo=a.repo.resolve(); plan=json.loads(a.plan.read_text(encoding="utf-8")); pin=plan["sourcePin"]
 if git(repo,"rev-parse","HEAD")!=pin["head"] or git(repo,"rev-parse","HEAD^{tree}")!=pin["tree"]: raise SystemExit("exact source HEAD/tree changed before commit")
 path="romarr/ui-labels.json"; old=json.loads(subprocess.check_output(["git","-C",str(repo),"show",f"{pin['head']}:{path}"])); new=json.loads((repo/path).read_text(encoding="utf-8"))
 if list(old["messages"])!=list(new["messages"]): raise SystemExit("catalog key membership/order changed")
 changes={(x["sourceId"],x["locale"]):x for x in plan["changes"]}; updates={(x["sourceId"],x["locale"]):x for x in plan["translationHashUpdates"]}
 deltas=[]
 for sid,before in old["messages"].items():
  after=new["messages"][sid]
  for field in before:
   if field not in ("translations","translationHashes") and before[field]!=after.get(field): raise SystemExit(f"unexpected metadata change: {sid}/{field}")
  for locale in set(before["translations"])|set(after["translations"]):
   ov=before["translations"].get(locale); nv=after["translations"].get(locale); expected=changes.get((sid,locale))
   if expected:
    if ov!=expected["currentTarget"] or textsha(ov)!=expected["currentTargetSha256"] or nv!=expected["finalTarget"] or textsha(nv)!=expected["finalTargetSha256"]: raise SystemExit(f"target readback mismatch: {sid}/{locale}")
    deltas.append((sid,locale,"translation"))
   elif ov!=nv: raise SystemExit(f"non-target translation changed: {sid}/{locale}")
  for locale in set(before.get("translationHashes",{}))|set(after.get("translationHashes",{})):
   ov=before.get("translationHashes",{}).get(locale); nv=after.get("translationHashes",{}).get(locale); expected=updates.get((sid,locale))
   if expected:
    if ov!=expected["expectedOldHash"] or nv!=expected["newHash"] or nv!=value_hash(after["translations"][locale]): raise SystemExit(f"translationHash mismatch: {sid}/{locale}")
    if before.get("translationStatus",{}).get(locale)!=after.get("translationStatus",{}).get(locale) or before.get("translationReview",{}).get(locale)!=after.get("translationReview",{}).get(locale): raise SystemExit(f"review metadata changed: {sid}/{locale}")
    deltas.append((sid,locale,"translationHash"))
   elif ov!=nv: raise SystemExit(f"non-target translationHash changed: {sid}/{locale}")
 cells=rows(a.candidate_free); ledger=rows(a.root_ledger)
 if len(cells)!=240 or len(ledger)!=240: raise SystemExit("review/readback coverage mismatch")
 rb=[]
 for row in cells:
  key=(row["sourceId"],row["locale"]); actual=new["messages"][row["sourceId"]]["translations"][row["locale"]]; selected=changes.get(key)
  expected_hash=selected["finalTargetSha256"] if selected else row["currentTargetSha256"]
  if textsha(actual)!=expected_hash: raise SystemExit(f"240-cell readback hash mismatch: {row['position']}/{row['locale']}")
  rb.append({"position":row["position"],"sourceId":row["sourceId"],"locale":row["locale"],"expectedTargetSha256":expected_hash,"actualTargetSha256":textsha(actual),"rootDisposition":"apply-selected" if selected else "accept-current" if not row["callerless"] else "text-free-hold"})
 result={"result":"PASS","sourcePin":pin,"readbackCellCount":len(rb),"dispositionCounts":plan["rootDispositionCounts"],"appliedTargetCells":len(changes),"updatedTranslationHashCells":len(updates),"translationStatusChanges":0,"translationReviewMetadataChanges":0,"catalogMessageCount":len(new["messages"]),"messageKeyOrderUnchanged":True,"catalogPostimageSha256":sha((repo/path).read_bytes()),"changedPaths":[path],"readback":rb}
 if len([d for d in deltas if d[2]=="translation"])!=29 or len([d for d in deltas if d[2]=="translationHash"])!=9: raise SystemExit("catalog delta count mismatch")
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({k:v for k,v in result.items() if k!="readback"},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
