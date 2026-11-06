#!/usr/bin/env python3
"""Apply only the exact cross-selected ROMarrNG W485-W504 catalog rows."""
import argparse
import collections
import copy
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WINDOW = ROOT.parent
REPO_DEFAULT = ROOT.parents[4]
CANDIDATE = WINDOW / "candidate-free-input" / "input"
PRIMARY = WINDOW / "primary-review"
BLIND = WINDOW / "blind-review" / "output"
CROSS = WINDOW / "cross-audit"
EVIDENCE = ROOT / "evidence"
PIN_HEAD = "6eb494d362ae19503b9199cd2c05c0767cddbc0e"
PIN_TREE = "b9450b9c6d22c816551fc8d528e8f03413d04595"
CATALOG_PATH = "romarr/ui-labels.json"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def text_sha(value):
    return sha(value.encode("utf-8"))

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def git_bytes(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])

def need(condition, message):
    if not condition:
        raise SystemExit("REFUSED: " + message)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=REPO_DEFAULT)
    repo = ap.parse_args().repo.resolve()
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    need((head, tree) == (PIN_HEAD, PIN_TREE), "worktree is not the exact candidate-free parent")
    need(not git(repo, "status", "--porcelain", "--", CATALOG_PATH, "CHANGELOG.md").strip(),
         "catalog or changelog has pre-existing changes")
    catalog_file = repo / CATALOG_PATH
    before_raw = catalog_file.read_bytes()
    before = json.loads(before_raw)
    pin = read_json(CANDIDATE / "catalog-file-pins.json")
    need(pin["commit"] == head and pin["tree"] == tree, "candidate-free catalog pin")
    need(pin["catalogSha256"] == sha(before_raw), "catalog preimage hash")
    need(len(before["messages"]) == pin["catalogMessageCount"] == 1836, "catalog key count")
    key_order_hash = sha(("".join(k + "\n" for k in before["messages"])).encode("utf-8"))
    need(key_order_hash == pin["catalogKeyOrderSha256"], "catalog insertion order")
    need(list(before["messages"][next(iter(before["messages"]))]["translations"]) ==
         ["es", "zh-Hans", "hi", "de", "ja", "fr", "pt-BR", "ar", "ko", "zh-Hant", "vi", "id"],
         "locale order")

    candidate = read_jsonl(CANDIDATE / "current-target-cells.jsonl")
    primary = read_jsonl(PRIMARY / "primary-ledger.jsonl")
    blind = read_jsonl(BLIND / "blind-ledger.jsonl")
    cross = read_jsonl(CROSS / "cross-ledger.jsonl")
    need(len(candidate) == len(primary) == len(blind) == len(cross) == 240, "240-cell packet coverage")
    cmap = {(r["sourceId"], r["locale"]): r for r in candidate}
    pmap = {(r["sourceId"], r["locale"]): r for r in primary}
    bmap = {(r["sourceId"], r["locale"]): r for r in blind}
    xmap = {(r["sourceId"], r["locale"]): r for r in cross}
    need(set(cmap) == set(pmap) == set(bmap) == set(xmap), "review cell set mismatch")

    counts = collections.Counter(r["crossDisposition"] for r in cross)
    need(counts == {"accept-current": 201, "correction": 14, "refinement": 1, "hold": 24},
         "cross disposition counts")
    need(all(r.get("head") == PIN_HEAD and r.get("tree") == PIN_TREE for r in cross),
         "cross ledger head/tree pins")

    prior_holds = read_jsonl(CANDIDATE / "prior-hold-reattestation.jsonl")
    prior_selections = read_jsonl(CANDIDATE / "prior-selection-reattestation.jsonl")
    need(len(prior_holds) == 444 and len(prior_selections) == 100, "prior lineage counts")
    need(prior_holds == read_jsonl(PRIMARY / "prior-hold-reattestation.jsonl"),
         "primary carried-hold reattestation differs from candidate-free input")
    need(prior_holds == read_jsonl(BLIND / "prior-hold-reattestation.jsonl"),
         "blind carried-hold reattestation differs from candidate-free input")
    need(prior_selections == read_jsonl(PRIMARY / "prior-selection-reattestation.jsonl"),
         "primary selected-source reattestation differs from candidate-free input")
    need(prior_selections == read_jsonl(BLIND / "prior-selection-reattestation.jsonl"),
         "blind selected-source reattestation differs from candidate-free input")

    after = copy.deepcopy(before)
    selected = []
    readback = []
    hold_positions = set()
    for key, row in sorted(xmap.items(), key=lambda item: (item[1]["position"], item[1]["locale"])):
        c, p, b = cmap[key], pmap[key], bmap[key]
        source_id, locale = key
        entry = before["messages"][source_id]
        current = entry["translations"][locale]
        current_hash = text_sha(current)
        need(entry["source"] == row["source"] == c["source"], f"source text {key}")
        need(entry["sourceHash"] == row["sourceSha256"] == c["sourceSha256"], f"source hash {key}")
        need(current == c["currentTarget"] == p["currentTarget"] == b["currentTarget"],
             f"reviewed current text {key}")
        need(current_hash == row["currentTargetSha256"] == c["currentTargetSha256"] ==
             p["currentTargetSha256"] == b["currentTargetSha256"], f"current target hash {key}")
        disposition = row["crossDisposition"]
        need(disposition == p["disposition"] == b["blindDisposition"], f"review disposition mismatch {key}")
        if disposition == "hold":
            hold_positions.add(row["position"])
            need(row.get("currentTarget") is None and row.get("selectedTarget") is None,
                 f"cross hold contains target text {key}")
            need(p.get("proposedTarget") is None and b.get("proposedTarget") is None,
                 f"held row has a proposal {key}")
            need(row["currentTargetSha256"] == current_hash, f"hold hash {key}")
            readback.append({
                "position": row["position"], "sourceId": source_id, "locale": locale,
                "disposition": disposition, "preApplyTargetSha256": current_hash,
                "readbackTargetSha256": current_hash, "targetUnchanged": True,
                "proposalTextRecorded": False
            })
            continue
        need(row.get("selectedTarget") == p.get("selectedTarget") == b.get("selectedTarget"),
             f"primary/blind/cross target agreement {key}")
        selected_target = row["selectedTarget"]
        selected_hash = text_sha(selected_target)
        need(selected_hash == row["selectedTargetSha256"] == p["selectedTargetSha256"] ==
             b["selectedTargetSha256"], f"selected target hash {key}")
        need(row["currentTarget"] == current and row["currentTargetSha256"] == current_hash,
             f"cross current target {key}")
        if disposition in ("correction", "refinement"):
            need(selected_target != current, f"selected change is a no-op {key}")
            checks = row["tokenAndLiteralChecks"]
            need(checks["selectedPlaceholderMultisetMatches"] and
                 checks["selectedNumericTokensPreserved"] and
                 checks["selectedProtectedLiteralsPreserved"],
                 f"selected token/literal check {key}")
            after["messages"][source_id]["translations"][locale] = selected_target
            selected.append({
                "position": row["position"], "sourceId": source_id, "source": row["source"],
                "sourceSha256": row["sourceSha256"], "locale": locale,
                "disposition": disposition, "oldTargetSha256": current_hash,
                "selectedTarget": selected_target, "selectedTargetSha256": selected_hash,
                "rationale": row["crossRationale"]
            })
        else:
            need(disposition == "accept-current" and selected_target == current,
                 f"current disposition mismatch {key}")
        actual = after["messages"][source_id]["translations"][locale]
        readback.append({
            "position": row["position"], "sourceId": source_id, "locale": locale,
            "disposition": disposition, "preApplyTargetSha256": current_hash,
            "expectedTargetSha256": selected_hash, "readbackTargetSha256": text_sha(actual),
            "readbackMatchesSelection": actual == selected_target,
            "target": actual
        })

    need(len(selected) == 15 and hold_positions == {493, 502}, "selected or held cell inventory")
    before_serialized = (json.dumps(before, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    need(before_serialized == before_raw, "catalog serialization would cause unrelated formatting changes")
    after_raw = (json.dumps(after, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "pre-apply-ui-labels.json").write_bytes(before_raw)
    (EVIDENCE / "post-apply-ui-labels.json").write_bytes(after_raw)
    with (EVIDENCE / "selected-change-ledger.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for item in selected:
            f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    with (EVIDENCE / "apply-readback.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for item in readback:
            f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    (EVIDENCE / "prior-hold-reattestation.jsonl").write_text(
        (CANDIDATE / "prior-hold-reattestation.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    (EVIDENCE / "prior-selection-reattestation.jsonl").write_text(
        (CANDIDATE / "prior-selection-reattestation.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    apply_plan = {
        "window": "W485-W504", "repository": "snapetech-org/ROMarrNG", "pullRequest": 70,
        "parent": head, "parentTree": tree, "catalogPath": CATALOG_PATH,
        "catalogBeforeSha256": sha(before_raw), "selectedChanges": selected,
        "dispositionCounts": dict(counts), "heldPositions": sorted(hold_positions),
        "heldCellCount": len(hold_positions) * 12, "holdProposalTextCells": 0,
        "priorHoldsReattested": len(prior_holds), "priorSelectionsReattested": len(prior_selections)
    }
    (EVIDENCE / "apply-plan.json").write_text(json.dumps(apply_plan, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    catalog_invariants = {
        "catalogPath": CATALOG_PATH, "catalogMessageCount": len(before["messages"]),
        "beforeSha256": sha(before_raw), "afterSha256": sha(after_raw),
        "catalogKeyOrderSha256": key_order_hash,
        "localeOrder": list(before["messages"][next(iter(before["messages"]))]["translations"]),
        "localeOrderUnchanged": all(
            list(before["messages"][sid]["translations"]) == list(after["messages"][sid]["translations"])
            for sid in before["messages"]),
        "sourceAndMetadataUnchanged": all(
            {k: v for k, v in before["messages"][sid].items() if k != "translations"} ==
            {k: v for k, v in after["messages"][sid].items() if k != "translations"}
            for sid in before["messages"]),
        "changedCellCount": len(selected), "changedCells": [
            {"sourceId": x["sourceId"], "locale": x["locale"]} for x in selected
        ],
        "workflowFilesChanged": False
    }
    (EVIDENCE / "catalog-invariants.json").write_text(
        json.dumps(catalog_invariants, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    precheck = {
        "observedImmediatelyBeforeEdit": True, "head": head, "tree": tree,
        "catalogSha256": sha(before_raw), "reviewedCellsChecked": 240,
        "allCurrentTargetHashesMatch": True, "exactHashGuardedSelectedChanges": len(selected),
        "workflowFilesInChangeSet": 0, "checkedAtUTC": datetime.now(timezone.utc).isoformat()
    }
    (EVIDENCE / "pre-apply-checks.json").write_text(
        json.dumps(precheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "result": "PASS", "window": "W485-W504", "cellsReviewed": 240,
        "acceptCurrent": counts["accept-current"], "corrections": counts["correction"],
        "refinements": counts["refinement"], "holds": counts["hold"],
        "selectedChanges": len(selected), "cellsReadBack": len(readback),
        "carriedHoldsPreserved": len(prior_holds), "priorSelectionsPreserved": len(prior_selections),
        "catalogMessageCount": len(after["messages"]), "catalogKeyOrderUnchanged": True,
        "localeOrderUnchanged": catalog_invariants["localeOrderUnchanged"],
        "nonTargetValuesAndMetadataUnchanged": catalog_invariants["sourceAndMetadataUnchanged"],
        "workflowFilesChanged": 0
    }
    (EVIDENCE / "apply-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
    catalog_file.write_bytes(after_raw)
    need(catalog_file.read_bytes() == after_raw, "post-write catalog readback")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
