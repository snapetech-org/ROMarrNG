#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import subprocess

PRODUCT="63224167b0f89978a68977a7996bd06724d06129"
BASE="eda48333438591ecc67f829c50ef2d521f1e7a5e"
TREE="4b419d70c07b90d30290b4478e56c8393dfe2161"
CATALOG="romarr/ui-labels.json"
EVIDENCE="docs/pr-evidence/pr70-localization-2026-11-04/window-525-544"

def abort(message): raise SystemExit("VERIFICATION FAILED: "+message)
def run(args,cwd=None): return subprocess.check_output(args,cwd=cwd,text=True).strip()
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def git_bytes(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args])
def sha(data): return hashlib.sha256(data).hexdigest()
def read_json(path): return json.loads(path.read_text(encoding="utf-8"))
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def key(row): return (int(row["position"]),row["locale"])

parser=argparse.ArgumentParser()
parser.add_argument("--repo",required=True,help="worktree containing the product and evidence commits")
parser.add_argument("--input-repo",required=True,help="clean worktree pinned to the reviewed input head")
args=parser.parse_args()
repo=pathlib.Path(args.repo).resolve()
input_repo=pathlib.Path(args.input_repo).resolve()
root=repo/EVIDENCE
app=root/"application"
cross=root/"cross-review"
run(["sha256sum","-c","SHA256SUMS.txt"],cwd=root)
run(["sha256sum","-c","SHA256SUMS.txt"],cwd=app)
if git(repo,"rev-parse",PRODUCT)!=PRODUCT or git(repo,"rev-parse",PRODUCT+"^")!=BASE or git(repo,"rev-parse",PRODUCT+"^{tree}")!=TREE:
    abort("product commit, parent, or tree mismatch")
paths=git(repo,"diff-tree","--no-commit-id","--name-only","-r",PRODUCT).splitlines()
if paths != [CATALOG] or any(x.startswith(".github/workflows/") for x in paths):
    abort("product commit changed an unexpected path")
subprocess.run(["python3",str(cross/"verify_cross.py"),"--repo",str(input_repo)],check=True)
raw=git_bytes(repo,"show",PRODUCT+":"+CATALOG)
if sha(raw)!=read_json(app/"catalog-preimage.json")["postSha256"]:
    abort("catalog postimage SHA mismatch")
if git(repo,"rev-parse",PRODUCT+":"+CATALOG)!=read_json(app/"catalog-preimage.json")["postGitBlob"]:
    abort("catalog postimage Git blob mismatch")
if (repo/CATALOG).read_bytes()!=raw:
    abort("worktree catalog differs from product commit")
before=json.loads(git_bytes(repo,"show",BASE+":"+CATALOG).decode("utf-8"))
after=json.loads(raw.decode("utf-8"))
pin=read_json(cross/"inputs/candidate-free/input/catalog-file-pins.json")
if sha(git_bytes(repo,"show",BASE+":"+CATALOG))!=pin["catalogSha256"]:
    abort("base catalog differs from candidate-free pin")
if list(before["messages"])!=list(after["messages"]):
    abort("catalog message key order changed")
for sid,entry in before["messages"].items():
    if list(entry["translations"])!=list(after["messages"][sid]["translations"]):
        abort("locale order changed for "+sid)
    for locale,value in entry["translations"].items():
        if (sid,locale) not in {(x["sourceId"],x["locale"]) for x in read_jsonl(cross/"selected-changes.jsonl")} and after["messages"][sid]["translations"][locale]!=value:
            abort("unselected translation changed")
    for field,value in entry.items():
        if field not in ("translations","translationHashes") and after["messages"][sid].get(field)!=value:
            abort("catalog metadata changed for "+sid+"/"+field)
summary=read_json(app/"application-summary.json")
preimage=read_json(app/"catalog-preimage.json")
changes=read_jsonl(app/"selected-update-ledger.jsonl")
cross_changes=read_jsonl(cross/"selected-changes.jsonl")
ledger=read_jsonl(cross/"cross-ledger.jsonl")
current=read_jsonl(cross/"inputs/candidate-free/input/current-target-cells.jsonl")
readback=read_jsonl(app/"application-readback.jsonl")
prior_holds=read_jsonl(cross/"prior-holds-preserved.jsonl")
prior_applied=read_jsonl(cross/"inputs/candidate-free/input/prior-applied-cell-reattestation.jsonl")
prior_selected=read_jsonl(cross/"inputs/candidate-free/input/prior-selection-reattestation.jsonl")
if len(changes)!=18 or len(cross_changes)!=18 or len(ledger)!=240 or len(current)!=240 or len(readback)!=240:
    abort("application/cross readback row counts mismatch")
cm={key(x):x for x in current}; xm={key(x):x for x in ledger}; rm={key(x):x for x in readback}
if any(len(x)!=240 for x in (cm,xm,rm)) or set(cm)!=set(xm) or set(cm)!=set(rm):
    abort("duplicate or missing cell")
change_map={key(x):x for x in changes}
if len(change_map)!=18 or set(change_map)!={key(x) for x in cross_changes}:
    abort("selected change set differs from cross decisions")
for k,c in cm.items():
    x=xm[k]; r=rm[k]; value=after["messages"][c["sourceId"]]["translations"][c["locale"]]
    if k[0]==530:
        if x["crossDecision"]!="hold_callerless" or not r.get("held") or r.get("afterValue") is not None:
            abort("callerless hold record mismatch")
        if sha(value.encode("utf-8"))!=c["currentTargetSha256"] or r["afterSha256"]!=c["currentTargetSha256"]:
            abort("callerless held value changed")
        continue
    expected=x["selectedTarget"]
    if value!=expected or sha(value.encode("utf-8"))!=x["selectedTargetSha256"]:
        abort("catalog value differs from selected cross target at "+str(k))
    if r.get("afterValue")!=value or r.get("afterSha256")!=x["selectedTargetSha256"]:
        abort("readback differs from product tree at "+str(k))
    if r.get("changed")!=(k in change_map):
        abort("readback changed flag mismatch at "+str(k))
for row in changes:
    k=key(row); x=xm[k]
    if row["beforeTarget"]!=cm[k]["currentTarget"] or row["beforeSha256"]!=cm[k]["currentTargetSha256"]:
        abort("selected preimage mismatch at "+str(k))
    if row["afterTarget"]!=x["selectedTarget"] or sha(row["afterTarget"].encode("utf-8"))!=row["afterSha256"]:
        abort("selected postimage mismatch at "+str(k))
for row in prior_holds:
    if sha(after["messages"][row["sourceId"]]["translations"][row["locale"]].encode("utf-8"))!=row["currentTargetSha256"]:
        abort("prior hash-only hold changed")
for row in prior_applied:
    if sha(after["messages"][row["sourceId"]]["translations"][row["locale"]].encode("utf-8"))!=row["currentTargetSha256"]:
        abort("prior applied cell changed")
changed_ids={x["sourceId"] for x in changes}
if any(x["sourceId"] in changed_ids for x in prior_selected):
    abort("prior selected source overlaps this application")
if summary["reviewedCells"]!=240 or summary["selectedUpdates"]!=18 or summary["retainedCurrent"]!=210 or summary["newTextFreeHolds"]!=12:
    abort("application summary counts mismatch")
if summary["priorHashOnlyHoldsPreserved"]!=540 or summary["priorAppliedCellsPreserved"]!=28 or summary["priorSelectedSourceRecordsPreserved"]!=140:
    abort("prior lineage counts mismatch")
if summary["tokenMismatches"]!=0 or summary["workflowChanges"]!=0 or summary["translationHashUpdates"]!=0:
    abort("token/workflow/hash-update summary mismatch")
att=read_json(app/"PR-attestation-after-product.json")
if att["headRefOid"]!=PRODUCT or att["branchRefSha"]!=PRODUCT or att["pullRefSha"]!=PRODUCT or att["state"]!="OPEN" or not att["isDraft"]:
    abort("product-head PR refs were not synchronized")
subprocess.run(["git","-C",str(repo),"diff","--check",BASE,PRODUCT],check=True)
print(json.dumps({"result":"PASS","productCommit":PRODUCT,"parent":BASE,"tree":TREE,
 "reviewedCells":240,"selectedUpdates":18,"retainedCurrent":210,"newHolds":12,
 "priorHoldsPreserved":540,"priorAppliedCellsPreserved":28,"priorSelectedSourcesPreserved":140,
 "tokenMismatches":0,"workflowChanges":0},sort_keys=True))
