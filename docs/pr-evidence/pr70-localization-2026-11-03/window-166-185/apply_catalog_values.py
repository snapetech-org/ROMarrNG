#!/usr/bin/env python3
"""Apply ratified ROMarrNG W166-W185 targets with exact-hash guards."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
EVIDENCE = ROOT / "docs/pr-evidence/pr70-localization-2026-11-03/window-166-185"
INPUT = EVIDENCE / "primary-packet/input"
CATALOG_PATH = "romarr/ui-labels.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha(encoded)


def baseline_bytes() -> bytes:
    return subprocess.check_output(["git", "show", f"HEAD:{CATALOG_PATH}"], cwd=ROOT)


def main() -> None:
    manifest = read_json(INPUT / "manifest.json")
    head_pins = read_json(INPUT / "head-and-file-pins.json")
    plan = read_json(EVIDENCE / "apply-plan.json")
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == manifest["head"]
    assert subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip() == manifest["tree"]
    assert plan["head"] == manifest["head"] == head_pins["head"]
    assert plan["tree"] == manifest["tree"] == head_pins["tree"]
    assert plan["catalogFile"] == CATALOG_PATH
    assert plan["changeCount"] == len(plan["items"]) == 41
    tracked_changes = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True)
    assert not tracked_changes.strip(), f"tracked files changed before apply: {tracked_changes}"

    pin = head_pins["filePins"][CATALOG_PATH]
    raw = baseline_bytes()
    assert sha(raw) == pin["sha256"] == plan["catalogFileSha256"]
    assert subprocess.check_output(["git", "rev-parse", f"HEAD:{CATALOG_PATH}"], cwd=ROOT, text=True).strip() == pin["gitBlob"] == plan["catalogGitBlob"]
    baseline = json.loads(raw)
    assert (json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode("utf-8") == raw
    current = json.loads((ROOT / CATALOG_PATH).read_text(encoding="utf-8"))
    assert list(current) == list(baseline)
    assert list(current["messages"]) == list(baseline["messages"])

    input_rows = read_jsonl(INPUT / "review-input.jsonl")
    ratified = read_jsonl(EVIDENCE / "adjudication/ratified-ledger.jsonl")
    assert len(input_rows) == len(ratified) == 240
    inputs = {(row["id"], row["locale"]): row for row in input_rows}
    ratified_by_key = {(row["id"], row["locale"]): row for row in ratified}
    assert len(inputs) == len(ratified_by_key) == 240 and inputs.keys() == ratified_by_key.keys()

    planned = {(item["id"], item["locale"]): item for item in plan["items"]}
    assert len(planned) == 41
    updates: dict[tuple[str, str], str] = {}
    for key, item in planned.items():
        row = inputs[key]
        decision = ratified_by_key[key]
        assert row["sourceOrdinal"] == item["sourceOrdinal"] == decision["sourceOrdinal"]
        assert row["sourceSha256"] == item["sourceSha256"] == decision["sourceSha256"]
        assert row["currentTarget"] == item["currentTarget"] == decision["currentTarget"]
        assert row["currentTargetSha256"] == item["currentTargetSha256"] == decision["currentTargetSha256"]
        assert item["target"] == decision["adjudicatedTarget"]
        assert item["targetSha256"] == decision["adjudicatedTargetSha256"] == canon(item["target"])
        assert item["adjudicatedDisposition"] == decision["adjudicatedDisposition"]
        assert item["adjudicatedDisposition"] in {"correction", "refinement"}
        assert decision["exactCallerContext"]["callerExists"] is True
        assert decision["structureChecks"]["placeholderParity"] is True
        assert decision["structureChecks"]["protectedLiteralsPreserved"] is True
        assert baseline["messages"][item["id"]]["source"] == row["source"]
        assert canon(row["currentTarget"]) == row["currentTargetSha256"]
        assert baseline["messages"][item["id"]]["translations"][item["locale"]] == item["currentTarget"]
        assert current["messages"][item["id"]]["translations"][item["locale"]] in (item["currentTarget"], item["target"])
        updates[key] = item["target"]

    # Every reviewed cell is exact-head pinned; held cells remain byte-for-byte current.
    readback_rows = []
    mismatches = []
    for key, row in inputs.items():
        decision = ratified_by_key[key]
        disposition = decision["adjudicatedDisposition"]
        if disposition in {"correction", "refinement"}:
            expected = updates[key]
        else:
            expected = row["currentTarget"]
        current_value = current["messages"][row["id"]]["translations"][row["locale"]]
        assert current_value in (row["currentTarget"], expected), f"unexpected prior catalog edit: {key}"
        readback_rows.append({
            "id": row["id"],
            "sourceOrdinal": row["sourceOrdinal"],
            "locale": row["locale"],
            "adjudicatedDisposition": disposition,
            "currentTargetSha256": row["currentTargetSha256"],
            "expected": expected,
            "expectedSha256": canon(expected),
            "actualBeforeApply": current_value,
            "actualBeforeApplySha256": canon(current_value),
            "changed": expected != row["currentTarget"],
        })

    updated = json.loads(raw)
    for (message_id, locale), target in updates.items():
        updated["messages"][message_id]["translations"][locale] = target
    assert list(updated["messages"]) == list(baseline["messages"])
    assert list(updated) == list(baseline)

    for row in readback_rows:
        value = updated["messages"][row["id"]]["translations"][row["locale"]]
        row["actualAfterApply"] = value
        row["actualAfterApplySha256"] = canon(value)
        row["match"] = value == row["expected"] and canon(value) == row["expectedSha256"]
        if not row["match"]:
            mismatches.append(row)
    assert not mismatches, json.dumps(mismatches[:3], ensure_ascii=False)

    payload = (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    destination = ROOT / CATALOG_PATH
    with tempfile.NamedTemporaryFile(prefix=".ui-labels.w166-185-", dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    actual_bytes = destination.read_bytes()
    actual_catalog = json.loads(actual_bytes)
    assert list(actual_catalog["messages"]) == list(baseline["messages"])
    actual_key_hash = sha("\n".join(actual_catalog["messages"]).encode("utf-8"))
    readback = {
        "title": "ROMarrNG PR #70 W166-W185 exact-hash application readback",
        "repository": plan["repository"],
        "pullRequest": plan["pullRequest"],
        "baselineHead": manifest["head"],
        "window": plan["window"],
        "catalogFile": CATALOG_PATH,
        "baselineCatalogSha256": pin["sha256"],
        "finalCatalogSha256": sha(actual_bytes),
        "messageKeyCountBefore": len(baseline["messages"]),
        "messageKeyCountAfter": len(actual_catalog["messages"]),
        "orderedMessageKeysSha256BeforeAndAfter": actual_key_hash,
        "appliedChangeCount": len(updates),
        "verifiedCellCount": len(readback_rows) - len(mismatches),
        "mismatchCount": len(mismatches),
        "rows": readback_rows,
    }
    (EVIDENCE / "readback.json").write_text(json.dumps(readback, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Applied {len(updates)} exact-hash values; verified {len(readback_rows)} cells, zero mismatches.")


if __name__ == "__main__":
    main()
