#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

HEAD = "eda48333438591ecc67f829c50ef2d521f1e7a5e"
TREE = "3db18e56d0c7ac08a564a6baff61eba25f0a01da"
BRANCH = "task/localization-translation-review-20261030"

def abort(message):
    raise SystemExit("VERIFICATION FAILED: " + message)

def run(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def key(row):
    return (int(row["position"]), row["locale"])

parser = argparse.ArgumentParser()
parser.add_argument("--repo", required=True, help="clean source worktree pinned to the reviewed PR head")
args = parser.parse_args()
repo = pathlib.Path(args.repo).resolve()
root = pathlib.Path(__file__).resolve().parent
cf = root / "inputs/candidate-free/input"
pr = root / "inputs/primary-review"
bl = root / "inputs/blind-review"

run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=root)
if run(["git", "-C", str(repo), "rev-parse", "HEAD"]) != HEAD:
    abort("source head mismatch")
if run(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"]) != TREE:
    abort("source tree mismatch")
if run(["git", "-C", str(repo), "status", "--porcelain"]):
    abort("source worktree is not clean")
checks = [
    json.loads(run(["python3", "verify_input.py", "--repo", str(repo)], cwd=cf)),
    json.loads(run(["python3", "verify_primary.py", "--repo", str(repo)], cwd=pr)),
    json.loads(run(["python3", "verify_blind_packet.py", "--input", str(cf), "--repo", str(repo)], cwd=bl)),
]
for directory in (cf, pr, bl):
    run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=directory)
if any(row.get("result") != "PASS" for row in checks):
    abort("a candidate-free, primary, or blind verifier failed")

cross = read_jsonl(root / "cross-ledger.jsonl")
changes = read_jsonl(root / "selected-changes.jsonl")
recs = read_jsonl(root / "proposal-reconciliation.jsonl")
holds = read_jsonl(root / "holds.jsonl")
current = {key(x):x for x in read_jsonl(cf / "current-target-cells.jsonl")}
primary = {key(x):x for x in read_jsonl(pr / "primary-ledger.jsonl")}
blind = {key(x):x for x in read_jsonl(bl / "blind-decisions.jsonl")}
if len(cross) != 240 or len(current) != 240 or len(primary) != 240 or len(blind) != 240:
    abort("expected 240 rows in each full ledger")
if any(len(index) != 240 for index in (current,primary,blind,{key(x):x for x in cross})):
    abort("duplicate cell")
if {key(x) for x in cross} != set(current):
    abort("cross/current cell set mismatch")
cross_map = {key(x):x for x in cross}
if len(changes) != 18 or len(recs) != 18 or len(holds) != 12:
    abort("selected proposal or callerless hold count mismatch")
if any(x["position"] != 530 for x in holds):
    abort("hold set contains an unexpected position")
if any("source" in x or "currentTarget" in x or "selectedTarget" in x for x in holds):
    abort("hold ledger contains source or target text")
if any("source" in x or "currentTarget" in x or "selectedTarget" in x for x in cross if x["crossDecision"] == "hold_callerless"):
    abort("cross hold row contains source or target text")
for row in cross:
    k = key(row)
    c, p, b = current[k], primary[k], blind[k]
    if (c["sourceId"],c["sourceSha256"],c["currentTargetSha256"]) != (p["sourceId"],p["sourceSha256"],p["currentTargetSha256"]):
        abort("primary linkage mismatch at " + str(k))
    if (c["sourceId"],c["sourceSha256"],c["currentTargetSha256"]) != (b["sourceId"],b["sourceSha256"],b["currentTargetSha256"]):
        abort("blind linkage mismatch at " + str(k))
    if row["crossDecision"] == "hold_callerless":
        if k[0] != 530 or p["disposition"] != "hold":
            abort("unexpected hold decision at " + str(k))
        continue
    if row.get("selectedTarget") != row.get("currentTarget") and row.get("selectedTargetSha256") != sha(row["selectedTarget"]):
        abort("selected target hash mismatch at " + str(k))
    if row.get("selectedTarget") == row.get("currentTarget") and row.get("selectedTargetSha256") != row.get("currentTargetSha256"):
        abort("retained current hash mismatch at " + str(k))
for row in changes:
    k = key(row)
    c = current[k]
    if row["beforeTarget"] != c["currentTarget"] or row["beforeSha256"] != c["currentTargetSha256"]:
        abort("selected change preimage mismatch at " + str(k))
    if sha(row["afterTarget"]) != row["afterSha256"] or row["catalogPath"] != "romarr/ui-labels.json":
        abort("selected change target/path mismatch at " + str(k))
    crossrow = cross_map[k]
    if row["afterTarget"] != crossrow["selectedTarget"] or row["afterSha256"] != crossrow["selectedTargetSha256"]:
        abort("selected change differs from cross ledger at " + str(k))
    for flag in ("placeholders","markup","numericTokens","protectedLiterals"):
        if crossrow["tokenSafety"].get(flag) != "PASS":
            abort("token-safety flag missing at " + str(k))
prior = read_jsonl(root/"prior-holds-preserved.jsonl")
prior_cf = cf/"prior-hold-reattestation.jsonl"
prior_blind = bl/"prior-hold-reattestation-hash-only.jsonl"
if len(prior) != 540 or prior_cf.read_bytes() != prior_blind.read_bytes() or prior_cf.read_bytes() != (root/"prior-holds-preserved.jsonl").read_bytes():
    abort("prior hold hash lineage differs")
if any("currentTarget" in row or "target" in row or "source" in row for row in prior):
    abort("prior hold lineage contains source or target text")
prior_applied = read_jsonl(cf/"prior-applied-cell-reattestation.jsonl")
prior_selected = read_jsonl(cf/"prior-selection-reattestation.jsonl")
if len(prior_applied) != 28 or len(prior_selected) != 140:
    abort("prior application/selection lineage count mismatch")
att = read_json(root/"PR-attestation-after.json")
if (att["headRefOid"] != HEAD or att["headTree"] != TREE or att["branchApiSha"] != HEAD or
    att["branchRefSha"] != HEAD or att["pullRefSha"] != HEAD or att["state"] != "OPEN" or not att["isDraft"]):
    abort("PR/ref attestation mismatch")
counts={}
for row in cross:
    counts[row["crossDecision"]]=counts.get(row["crossDecision"],0)+1
expected={"retain_current":210,"select_agreed_proposal":12,"select_primary_proposal":2,
          "select_blind_proposal":4,"hold_callerless":12}
if counts != expected:
    abort("cross decision counts mismatch: " + repr(counts))
print(json.dumps({"result":"PASS","head":HEAD,"tree":TREE,"cells":240,
                  "decisions":counts,"selectedChanges":len(changes),"holds":len(holds),
                  "priorHoldsPreserved":540,"priorAppliedCells":28,"priorSelectedSources":140,
                  "tokenMismatches":0},sort_keys=True))
