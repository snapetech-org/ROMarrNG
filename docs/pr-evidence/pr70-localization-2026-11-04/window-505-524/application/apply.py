#!/usr/bin/env python3
"""Apply only the sealed ROMarrNG W505-W524 cross-selected catalog cells."""
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
CROSS = WINDOW / "cross-audit"
INPUT = CROSS / "provenance" / "candidate-free-input"
EVIDENCE = ROOT / "evidence"
CATALOG_PATH = "romarr/ui-labels.json"
PIN_HEAD = "e958b4fd0d9ddeac9333afc4c95da348b7f67cff"
PIN_TREE = "402026ba276ec4603d86d659766af836d839de55"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def text_sha(value):
    return sha(value.encode("utf-8"))

def translation_hash(value):
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha(serialized.encode("utf-8"))

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def git_bytes(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])

def need(condition, message):
    if not condition:
        raise SystemExit("REFUSED: " + message)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=ROOT.parents[4])
    repo = ap.parse_args().repo.resolve()
    need(git(repo, "rev-parse", "HEAD") == PIN_HEAD, "checkout is not the exact PR input head")
    need(git(repo, "rev-parse", "HEAD^{tree}") == PIN_TREE, "checkout is not the exact PR input tree")
    need(not git(repo, "status", "--porcelain", "--", CATALOG_PATH).strip(), "catalog has pre-existing changes")

    cross_result = subprocess.check_output(["python3", str(CROSS / "verify_cross.py")], cwd=CROSS, text=True)
    need('"result": "PASS"' in cross_result, "sealed cross bundle did not pass its verifier")
    packet = read_json(INPUT / "manifest.json")
    pins = read_json(INPUT / "catalog-file-pins.json")
    need((packet["head"], packet["tree"], packet["window"]) == (PIN_HEAD, PIN_TREE, "W505-W524"),
         "candidate-free pin/window")
    need((pins["commit"], pins["tree"]) == (PIN_HEAD, PIN_TREE), "catalog pin head/tree")

    catalog_file = repo / CATALOG_PATH
    before_raw = catalog_file.read_bytes()
    need(sha(before_raw) == pins["catalogSha256"], "catalog preimage hash")
    before = json.loads(before_raw)
    need(len(before["messages"]) == pins["catalogMessageCount"] == 1836, "catalog key count")
    key_order_hash = sha("".join(key + "\n" for key in before["messages"]).encode("utf-8"))
    need(key_order_hash == pins["catalogKeyOrderSha256"], "catalog key insertion order")
    catalog_locale_order = list(before["messages"][next(iter(before["messages"]))]["translations"])

    input_cells = read_jsonl(INPUT / "current-target-cells.jsonl")
    cross_ledger = read_jsonl(CROSS / "per-cell-ledger.jsonl")
    selected = read_jsonl(CROSS / "selected-changes.jsonl")
    holds = read_jsonl(CROSS / "holds.jsonl")
    prior_holds = read_jsonl(INPUT / "prior-hold-reattestation.jsonl")
    prior_selections = read_jsonl(INPUT / "prior-selection-reattestation.jsonl")
    need(len(input_cells) == len(cross_ledger) == 240, "240-cell input/cross coverage")
    cmap = {(x["sourceId"], x["locale"]): x for x in input_cells}
    xmap = {(x["sourceId"], x["locale"]): x for x in cross_ledger}
    smap = {(x["sourceId"], x["locale"]): x for x in selected}
    hmap = {(x["sourceId"], x["locale"]): x for x in holds}
    need(len(cmap) == len(xmap) == 240 and set(cmap) == set(xmap), "cell key set")
    need(len(smap) == 28 and len(hmap) == 72, "selected/hold counts")
    need(len(prior_holds) == 468 and len(prior_selections) == 120, "carried lineage counts")

    # Guard every reviewed current cell, including the 140 retained cells and all text-free holds.
    for key, row in xmap.items():
        c = cmap[key]
        entry = before["messages"][key[0]]
        need(entry["source"] == c["source"], "source text mismatch " + str(key))
        need(entry["sourceHash"] == c["sourceSha256"] and text_sha(entry["source"]) == c["sourceSha256"],
             "source hash mismatch " + str(key))
        current = entry["translations"][key[1]]
        current_hash = text_sha(current)
        need(current_hash == c["currentTargetSha256"] == row["currentTargetSha256"],
             "current target hash mismatch " + str(key))
        need(row["callerContextSha256"] == c["callerContextSha256"], "caller context mismatch " + str(key))
        if row["finalDisposition"] == "hold_callerless":
            need(key in hmap and key not in smap, "hold key linkage " + str(key))
            need(row["callerless"] is True and row["callerEvidence"] == [], "callerless evidence linkage " + str(key))
            need(hmap[key]["currentTargetSha256"] == current_hash, "hold target hash mismatch " + str(key))
            need(not any(field in row for field in ("source", "currentTarget", "selectedTarget", "proposedTarget")),
                 "hold ledger must remain text-free " + str(key))
        elif row["finalDisposition"] == "retain_current":
            need(key not in smap and row["selectedTargetSha256"] == current_hash, "retained cell mismatch " + str(key))
        else:
            need(row["finalDisposition"] == "select_change" and key in smap, "invalid selected cell " + str(key))
            d = smap[key]
            need(text_sha(d["selectedTarget"]) == d["selectedTargetSha256"] == row["selectedTargetSha256"],
                 "selected target hash mismatch " + str(key))
            need(d["currentTargetSha256"] == current_hash and d["callerContextSha256"] == row["callerContextSha256"],
                 "selected current/context linkage " + str(key))

    after = copy.deepcopy(before)
    selected_rows = []
    hash_updates = []
    changed_cells = set()
    for key, item in sorted(smap.items(), key=lambda it: (xmap[it[0]]["position"], it[0][1])):
        source_id, locale = key
        entry = after["messages"][source_id]
        current = entry["translations"][locale]
        selected_target = item["selectedTarget"]
        current_hash = text_sha(current)
        selected_hash = text_sha(selected_target)
        need(current_hash == item["currentTargetSha256"], "apply current hash " + str(key))
        need(selected_hash == item["selectedTargetSha256"], "apply selected hash " + str(key))
        need(selected_target != current, "selected update is a no-op " + str(key))
        hashes = entry.get("translationHashes", {})
        if locale in hashes:
            old_hash = hashes[locale]
            need(old_hash == translation_hash(current), "existing translation hash is stale " + str(key))
            entry["translations"][locale] = selected_target
            entry["translationHashes"][locale] = translation_hash(selected_target)
            hash_updates.append({"sourceId": source_id, "sourceSha256": entry["sourceHash"], "locale": locale,
                                 "oldTranslationHash": old_hash, "newTranslationHash": translation_hash(selected_target)})
        else:
            entry["translations"][locale] = selected_target
        changed_cells.add(key)
        selected_rows.append({"position": item["position"], "sourceId": source_id, "sourceSha256": entry["sourceHash"],
                              "locale": locale, "currentTargetSha256": current_hash,
                              "selectedTarget": selected_target, "selectedTargetSha256": selected_hash,
                              "selectedFrom": item["selectedFrom"], "adjudicationReason": item["adjudicationReason"]})
    need(len(changed_cells) == 28 and len(hash_updates) == 3, "expected 28 target and three existing hash updates")
    need(selected_rows == sorted(selected_rows, key=lambda x: (x["position"], LOCALES.index(x["locale"]))),
         "selected plan ordering")

    # Preserve catalog structure, all untouched translation values, and all metadata except hashes bound to edited cells.
    for sid, old_entry in before["messages"].items():
        new_entry = after["messages"][sid]
        need(old_entry["source"] == new_entry["source"] and old_entry["sourceHash"] == new_entry["sourceHash"],
             "source changed " + sid)
        need(list(old_entry["translations"]) == list(new_entry["translations"]), "locale key order changed " + sid)
        need(old_entry.get("translationStatus", {}) == new_entry.get("translationStatus", {}),
             "translation status changed " + sid)
        need(old_entry.get("translationReview", {}) == new_entry.get("translationReview", {}),
             "translation review metadata changed " + sid)
        for locale, value in old_entry["translations"].items():
            if (sid, locale) not in changed_cells:
                need(new_entry["translations"][locale] == value, "non-selected translation changed " + sid + "/" + locale)
        old_hashes = old_entry.get("translationHashes", {})
        new_hashes = new_entry.get("translationHashes", {})
        for locale, old_hash in old_hashes.items():
            key = (sid, locale)
            if key in changed_cells:
                need(new_hashes[locale] == translation_hash(new_entry["translations"][locale]),
                     "updated translation hash mismatch " + sid + "/" + locale)
            else:
                need(new_hashes[locale] == old_hash, "non-selected translation hash changed " + sid + "/" + locale)
        need(set(new_hashes) == set(old_hashes), "translation hash keys changed " + sid)

    # Prior holds and selected-source records must remain unchanged.
    prior_hold_keys = set()
    for record in prior_holds:
        key = (record["sourceId"], record["locale"])
        prior_hold_keys.add(key)
        for catalog in (before, after):
            need(text_sha(catalog["messages"][key[0]]["translations"][key[1]]) == record["currentTargetSha256"],
                 "carried hold changed " + str(key))
    changed_source_ids = {sid for sid, _ in changed_cells}
    prior_selected_ids = {x["sourceId"] for x in prior_selections}
    need(not changed_source_ids.intersection(prior_selected_ids), "selected source overlaps prior selected-source lineage")
    need(not changed_cells.intersection(prior_hold_keys), "selected cell overlaps carried hold lineage")
    for sid in prior_selected_ids:
        need(before["messages"][sid]["sourceHash"] == after["messages"][sid]["sourceHash"],
             "prior selected source hash changed " + sid)
        need(before["messages"][sid]["translations"] == after["messages"][sid]["translations"],
             "prior selected translations changed " + sid)
        need(before["messages"][sid].get("translationHashes", {}) == after["messages"][sid].get("translationHashes", {}),
             "prior selected translation hashes changed " + sid)

    before_serialized = (json.dumps(before, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    need(before_serialized == before_raw, "catalog serialization would change unrelated formatting")
    after_raw = (json.dumps(after, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    need(list(before["messages"]) == list(after["messages"]), "catalog insertion order changed")
    need(catalog_locale_order == list(after["messages"][next(iter(after["messages"]))]["translations"]),
         "catalog locale order changed")

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "pre-apply-ui-labels.json").write_bytes(before_raw)
    (EVIDENCE / "post-apply-ui-labels.json").write_bytes(after_raw)
    write_jsonl(EVIDENCE / "selected-change-ledger.jsonl", selected_rows)
    write_jsonl(EVIDENCE / "translation-hash-updates.jsonl", hash_updates)
    write_jsonl(EVIDENCE / "prior-hold-reattestation.jsonl", prior_holds)
    write_jsonl(EVIDENCE / "prior-selection-reattestation.jsonl", prior_selections)

    readback = []
    for key, row in sorted(xmap.items(), key=lambda it: (it[1]["position"], LOCALES.index(it[0][1]))):
        current = before["messages"][key[0]]["translations"][key[1]]
        actual = after["messages"][key[0]]["translations"][key[1]]
        current_hash = text_sha(current)
        actual_hash = text_sha(actual)
        if row["finalDisposition"] == "hold_callerless":
            readback.append({"position": row["position"], "sourceId": key[0], "sourceSha256": row["sourceSha256"],
                             "locale": key[1], "disposition": "hold_callerless", "currentTargetSha256": current_hash,
                             "readbackTargetSha256": actual_hash, "targetUnchanged": actual == current,
                             "proposalTextRecorded": False})
        elif row["finalDisposition"] == "retain_current":
            readback.append({"position": row["position"], "sourceId": key[0], "sourceSha256": row["sourceSha256"],
                             "locale": key[1], "disposition": "retain_current", "currentTargetSha256": current_hash,
                             "readbackTargetSha256": actual_hash, "targetUnchanged": actual == current})
        else:
            selected_hash = smap[key]["selectedTargetSha256"]
            readback.append({"position": row["position"], "sourceId": key[0], "sourceSha256": row["sourceSha256"],
                             "locale": key[1], "disposition": "select_change", "currentTargetSha256": current_hash,
                             "selectedTargetSha256": selected_hash, "readbackTargetSha256": actual_hash,
                             "readbackMatchesSelection": actual_hash == selected_hash})
    need(len(readback) == 240, "readback count")
    write_jsonl(EVIDENCE / "apply-readback.jsonl", readback)

    summary = {
        "result": "PASS", "window": "W505-W524", "cellsReviewed": 240,
        "acceptCurrent": 140, "selectedChanges": 28, "holds": 72,
        "cellsReadBack": len(readback), "callerlessSources": 6,
        "carriedHoldsReattested": len(prior_holds), "priorSelectedSourcesReattested": len(prior_selections),
        "catalogMessageCount": 1836, "catalogKeyOrderUnchanged": True, "localeOrderUnchanged": True,
        "translationStatusUnchanged": True, "translationReviewMetadataUnchanged": True,
        "translationHashMetadataUpdates": len(hash_updates), "otherTranslationMetadataUnchanged": True,
        "workflowFilesChanged": 0
    }
    invariants = {
        "catalogPath": CATALOG_PATH, "catalogMessageCount": len(before["messages"]),
        "beforeSha256": sha(before_raw), "afterSha256": sha(after_raw),
        "catalogKeyOrderSha256": key_order_hash, "localeOrder": catalog_locale_order,
        "localeOrderUnchanged": True, "sourceAndSourceHashUnchanged": True,
        "selectedTranslationCellCount": len(changed_cells), "selectedTranslationHashUpdateCount": len(hash_updates),
        "translationStatusUnchanged": True, "translationReviewUnchanged": True,
        "holdCellCount": 72, "holdTranslationTextIncludedInHoldLedger": False,
        "retainedCurrentCellCount": 140, "carriedHoldsUnchanged": len(prior_holds),
        "priorSelectedSourceRecordsUnchanged": len(prior_selections), "workflowFilesChanged": False
    }
    plan = {
        "window": "W505-W524", "repository": "snapetech-org/ROMarrNG", "pullRequest": 70,
        "parent": PIN_HEAD, "parentTree": PIN_TREE, "catalogPath": CATALOG_PATH,
        "catalogBeforeSha256": sha(before_raw), "crossBundleManifestSha256": sha((CROSS / "manifest.json").read_bytes()),
        "sourceCount": 20, "localeCount": 12, "reviewedCells": 240,
        "selectedChanges": len(selected_rows), "selectedTargetHashUpdates": len(hash_updates),
        "holdCells": 72, "retainedCurrentCells": 140, "heldPositions": [505, 511, 513, 514, 515, 523],
        "heldTextInThisPlan": False, "carriedHolds": len(prior_holds), "priorSelectedSources": len(prior_selections)
    }
    checks = {"observedImmediatelyBeforeEdit": True, "head": PIN_HEAD, "tree": PIN_TREE,
              "catalogSha256": sha(before_raw), "crossBundleVerifier": "PASS",
              "reviewedCellsChecked": 240, "selectedCellCount": len(selected_rows),
              "holdCellCount": 72, "retainedCurrentCellCount": 140,
              "exactHashGuardedSelectedChanges": len(selected_rows),
              "translationHashMetadataUpdates": len(hash_updates),
              "workflowFilesInChangeSet": 0, "checkedAtUTC": datetime.now(timezone.utc).isoformat()}
    write_json(EVIDENCE / "apply-plan.json", plan)
    write_json(EVIDENCE / "catalog-invariants.json", invariants)
    write_json(EVIDENCE / "pre-apply-checks.json", checks)
    write_json(EVIDENCE / "apply-summary.json", summary)

    catalog_file.write_bytes(after_raw)
    need(catalog_file.read_bytes() == after_raw, "post-write catalog readback")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
