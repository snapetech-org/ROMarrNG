#!/usr/bin/env python3
"""Apply only the root-adjudicated ROMarrNG W665-W684 targets."""
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path

def sha(b): return hashlib.sha256(b).hexdigest()
def textsha(s): return sha(s.encode("utf-8"))
def value_hash(v): return sha(json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
def git(repo, *args): return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
def fail(s): raise SystemExit("FAIL: " + s)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--repo", type=Path, required=True); ap.add_argument("--plan", type=Path, required=True); ap.add_argument("--output", type=Path, required=True); a=ap.parse_args()
 repo=a.repo.resolve(); plan=json.loads(a.plan.read_text(encoding="utf-8")); pin=plan["sourcePin"]
 if git(repo,"rev-parse","HEAD")!=pin["head"] or git(repo,"rev-parse","HEAD^{tree}")!=pin["tree"]: fail("exact input HEAD/tree mismatch")
 if git(repo,"status","--porcelain=v1","--untracked-files=no"): fail("tracked worktree not clean before apply")
 path="romarr/ui-labels.json"; target=repo/path; raw=target.read_bytes(); cat=json.loads(raw); cp=plan["catalogs"][0]
 if sha(raw)!=cp["preimageSha256"]: fail("catalog preimage hash mismatch")
 if len(cat["messages"])!=cp["messageCount"]: fail("catalog message count mismatch")
 keys=list(cat["messages"]); order=sha((json.dumps(keys,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8"))
 if order!=cp["applicationMessageKeyOrderSha256"]: fail("catalog message key order mismatch")
 if raw!=(json.dumps(cat,ensure_ascii=False,indent=2)+"\n").encode("utf-8"): fail("catalog serialization differs from canonical project format")
 before=json.loads(raw); seen=set()
 for change in plan["changes"]:
  key=(change["sourceId"],change["locale"])
  if key in seen: fail("duplicate selected cell")
  seen.add(key)
  if change["path"]!=path: fail("unexpected catalog path")
  if textsha(change["finalTarget"])!=change["finalTargetSha256"]: fail("final target hash mismatch: "+repr(key))
  msg=cat["messages"].get(change["sourceId"])
  if not msg or msg.get("source")!=change["sourceText"] or msg.get("sourceHash")!=change["sourceSha256"]: fail("source binding mismatch: "+repr(key))
  current=msg["translations"].get(change["locale"])
  if current!=change["currentTarget"] or textsha(current)!=change["currentTargetSha256"]: fail("current target mismatch: "+repr(key))
  msg["translations"][change["locale"]]=change["finalTarget"]
 for update in plan["translationHashUpdates"]:
  msg=cat["messages"][update["sourceId"]]; locale=update["locale"]
  if msg.get("translationHashes",{}).get(locale)!=update["expectedOldHash"]: fail("translationHash preimage mismatch: "+repr((update["sourceId"],locale)))
  if msg.get("translationStatus",{}).get(locale)!=update["status"]: fail("translation status drift: "+repr((update["sourceId"],locale)))
  if value_hash(msg["translations"][locale])!=update["newHash"]: fail("translationHash postimage mismatch: "+repr((update["sourceId"],locale)))
  msg["translationHashes"][locale]=update["newHash"]
 if len(seen)!=29 or len(plan["translationHashUpdates"])!=9: fail("application count mismatch")
 if list(cat["messages"])!=list(before["messages"]): fail("message order changed")
 expected=json.loads(raw)
 for change in plan["changes"]: expected["messages"][change["sourceId"]]["translations"][change["locale"]]=change["finalTarget"]
 for update in plan["translationHashUpdates"]: expected["messages"][update["sourceId"]]["translationHashes"][update["locale"]]=update["newHash"]
 if cat!=expected: fail("unexpected catalog metadata or non-target changes")
 output=(json.dumps(cat,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
 tmp=None
 try:
  with tempfile.NamedTemporaryFile(prefix=".w665-684-",suffix=".tmp",dir=target.parent,delete=False) as f:
   f.write(output); f.flush(); os.fsync(f.fileno()); tmp=f.name
  os.replace(tmp,target)
 finally:
  if tmp and os.path.exists(tmp): os.unlink(tmp)
 if target.read_bytes()!=output: fail("catalog postimage mismatch")
 changed=git(repo,"diff","--name-only").splitlines()
 if changed!=[path]: fail("tracked changes are not limited to the target catalog")
 result={"result":"PASS","sourcePin":pin,"selectedCells":len(seen),"translationHashUpdates":len(plan["translationHashUpdates"]),"changedPaths":[path],"catalogPreimageSha256":sha(raw),"catalogPostimageSha256":sha(output),"messageKeyOrderSha256":order,"translationStatusChanges":0,"translationReviewMetadataChanges":0,"workflowChanges":0}
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(result,ensure_ascii=False,sort_keys=True))
if __name__=="__main__": main()
