#!/usr/bin/env python3
import collections,hashlib,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
E=ROOT/"evidence"
CROSS=ROOT.parent/"cross-audit"/"source-packet"
HEAD0="81a499b7c022bde61a63dbd8c68c0b1ca39adf26"
TREE0="1b075e050610771fc5651d1a4ca95d7c7b4b8e46"
COMMIT="cece9856c8886ad5f07d2358e9399075da8b5254"
TREE="2b73ed0326786296a08270fd74a4d7f71217265e"
MARKER="<!-- romarrng-pr70-window-445-464 -->"
def sha(b):return hashlib.sha256(b).hexdigest()
def ht(s):return sha(s.encode("utf-8"))
def j(p):return json.loads(p.read_text(encoding="utf-8"))
def jl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def need(x,m):
 if not x:raise SystemExit("FAIL: "+m)
def main():
 m=j(ROOT/"manifest.json"); sf=ROOT/"SHA256SUMS.txt"; sums={}
 for line in sf.read_text(encoding="utf-8").splitlines():
  if line.strip():
   d,p=line.split("  ",1);need(p not in sums,"duplicate checksum");sums[p]=d
 actual={x.relative_to(ROOT).as_posix() for x in ROOT.rglob("*") if x.is_file() and x!=sf}
 need(actual==set(sums),"application checksum inventory")
 for p,d in sums.items():need(sha((ROOT/p).read_bytes())==d,"application checksum "+p)
 records={x["path"]:x for x in m["files"]}
 need(set(records)==actual-{"manifest.json"},"application manifest inventory")
 for p,x in records.items():need((ROOT/p).stat().st_size==x["bytes"] and sha((ROOT/p).read_bytes())==x["sha256"],"application manifest "+p)
 audit=jl(CROSS/"cross-audit-ledger.jsonl");selected=jl(E/"selected-change-ledger.jsonl")
 holds=[x for x in audit if x["disposition"]=="hold"];changes=[x for x in audit if x["disposition"] in ("correction","refinement")]
 need(len(audit)==240 and len(selected)==21 and len(holds)==36,"cross-audit coverage/counts")
 need(collections.Counter(x["disposition"] for x in changes)=={"correction":8,"refinement":13},"change disposition counts")
 need({(x["sourceId"],x["locale"],x["selectedTargetSha256"]) for x in selected}=={(x["sourceId"],x["locale"],x["selectedTargetSha256"]) for x in changes},"selected ledger mismatch")
 before_raw=(E/"pre-apply-ui-labels.json").read_bytes();after_raw=(E/"post-apply-ui-labels.json").read_bytes()
 need(sha(before_raw)==m["preApplyCatalogSha256"] and sha(after_raw)==m["postApplyCatalogSha256"],"catalog snapshot hashes")
 before=json.loads(before_raw);after=json.loads(after_raw);expected=copy.deepcopy(before);keys=set()
 for r in audit:
  sid,loc=r["sourceId"],r["locale"];key=(sid,loc);need(key not in keys,"duplicate cross cell");keys.add(key)
  bm=before["messages"].get(sid);need(bm and bm["source"]==r["source"],"source preimage "+str(key))
  cur=bm["translations"].get(loc);need(cur==r["currentTarget"] and ht(cur)==r["currentTargetSha256"],"current preimage "+str(key))
  need(ht(r["selectedTarget"])==r["selectedTargetSha256"],"selected hash "+str(key))
  if r["disposition"] in ("correction","refinement"):
   chk=r["tokenAndLiteralChecks"]
   need(chk["selectedPlaceholderMultisetMatches"] and chk["selectedNumericTokensExactMatch"] and chk["selectedProtectedLiteralsPreserved"] and chk["selectedAdditionalNamedTermsPreserved"],"selected token/literal check "+str(key))
   expected["messages"][sid]["translations"][loc]=r["selectedTarget"]
 for r in audit:
  val=after["messages"][r["sourceId"]]["translations"][r["locale"]]
  need(val==r["selectedTarget"] and ht(val)==r["selectedTargetSha256"],"240-cell readback "+str((r["sourceId"],r["locale"])))
 need(after==expected,"unexpected catalog changes")
 need(list(before)==list(after) and list(before["messages"])==list(after["messages"]),"catalog key/order change")
 need(all(list(before["messages"][s]["translations"])==list(after["messages"][s]["translations"]) for s in before["messages"]),"locale key/order change")
 diff={(s,l) for s,b in before["messages"].items() for l,v in b["translations"].items() if v!=after["messages"][s]["translations"][l]}
 change_keys={(r["sourceId"],r["locale"]) for r in changes}
 need(diff==change_keys and len(diff)==21,"changed values outside selected set")
 rb=jl(E/"apply-readback.jsonl");need(len(rb)==240,"readback ledger rows")
 amap={(x["sourceId"],x["locale"]):x for x in audit}
 for r in rb:
  key=(r["sourceId"],r["locale"]);x=amap[key]
  need(r["preApplyMatchesCrossAudit"] and r["readbackMatchesCrossSelection"] and r["currentTargetSha256"]==x["currentTargetSha256"] and r["selectedTargetSha256"]==x["selectedTargetSha256"],"readback evidence "+str(key))
 for r in holds:need(before["messages"][r["sourceId"]]["translations"][r["locale"]]==r["currentTarget"]==after["messages"][r["sourceId"]]["translations"][r["locale"]],"held value changed")
 input_dir=CROSS/"romarrng-pr70-w445-464-candidate-free-20261103"/"input"
 ph=jl(E/"prior-hold-reattestation.jsonl");ps=jl(E/"prior-selection-reattestation.jsonl")
 need(len(ph)==348 and len(ps)==60,"prior evidence row count")
 need(ph==jl(input_dir/"prior-hold-reattestation.jsonl") and ps==jl(input_dir/"prior-selection-reattestation.jsonl"),"prior evidence differs from sealed input")
 for r in ph:
  s,l=r["sourceId"],r["locale"];need(r["targetUnchanged"] is True and r["priorTargetSha256"]==r["currentTargetSha256"],"prior hold record")
  for cat in (before,after):need(ht(cat["messages"][s]["translations"][l])==r["currentTargetSha256"],"carried hold changed")
 for r in ps:
  s=r["sourceId"];need(before["messages"][s]["source"]==after["messages"][s]["source"] and before["messages"][s]["translations"]==after["messages"][s]["translations"],"carried selection changed")
 commit=j(E/"catalog-commit.json")
 need(commit["parent"]==HEAD0 and commit["commit"]==COMMIT and commit["tree"]==TREE and commit["changedPaths"]==["romarr/ui-labels.json"] and commit["localStatusClean"],"catalog commit evidence")
 need(commit["catalogFileSha256"]==sha(after_raw),"catalog commit file sha")
 live=j(E/"live-pr-after-catalog-apply.json")
 need(live["state"]=="OPEN" and live["isDraft"] is True and live["head"]==COMMIT and live["tree"]==TREE and live["branchRef"]==COMMIT and live["pullRef"]==COMMIT,"post-apply PR refs/state")
 pre=j(E/"pre-apply-checks.json")
 need(pre["observedImmediatelyBeforeEdit"] is True and pre["head"]==HEAD0 and pre["tree"]==TREE0 and pre["branchRef"]==HEAD0 and pre["pullRef"]==HEAD0 and pre["preimageCellsChecked"]==240,"pre-apply pin evidence")
 body_before=(E/"pr-body-before.md").read_text(encoding="utf-8");section=(E/"pr-body-update.md").read_text(encoding="utf-8").rstrip()
 expected_body=body_before.rstrip()+"\n\n"+section+"\n"
 need((E/"pr-body-after-expected.md").read_text(encoding="utf-8")==expected_body and MARKER not in body_before and section.count(MARKER)==1 and expected_body.count(MARKER)==1,"PR body update evidence")
 need("verify_window_bundle.py" in section and "window-445-464/README.md" in section,"PR body links missing")
 print(json.dumps({"status":"PASS","reviewedCells":240,"selectedChanges":21,"corrections":8,"refinements":13,"heldCellsPreserved":36,"carriedHoldsPreserved":348,"carriedSelectionsPreserved":60,"changedCatalogValues":len(diff),"catalogCommit":COMMIT,"catalogTree":TREE,"catalogPath":"romarr/ui-labels.json","prStage":"OPEN/DRAFT after catalog commit"},indent=2))
if __name__=="__main__":main()
