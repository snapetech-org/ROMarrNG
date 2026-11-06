#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

APP = Path(__file__).resolve().parent
EVIDENCE = APP.parent
REPO = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=APP, text=True).strip())
PLAN_PATH = APP / "apply-plan.json"
LEDGER_PATH = EVIDENCE / "adjudication" / "ratified-ledger.jsonl"


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_source(value):
    return sha_bytes(value.encode("utf-8"))


def sha_translation(value):
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha_bytes(serialized.encode("utf-8"))


def serialize_catalog(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main():
    parser = argparse.ArgumentParser(description="Apply or verify the pinned W146-W165 catalog review.")
    parser.add_argument("--apply", action="store_true", help="Apply the 60 ratified correction/refinement targets.")
    args = parser.parse_args()

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    ledger = read_jsonl(LEDGER_PATH)
    if sha_bytes(LEDGER_PATH.read_bytes()) != plan["ratifiedLedgerSha256"]:
        raise SystemExit("ratified ledger hash does not match apply plan")
    if git("rev-parse", plan["baseHead"]) != plan["baseHead"]:
        raise SystemExit("pinned base commit is missing from this repository")
    if git("rev-parse", f"{plan['baseHead']}^{{tree}}") != plan["baseTree"]:
        raise SystemExit("pinned base tree does not match the apply plan")

    catalog_path = REPO / plan["catalogPath"]
    baseline_bytes = subprocess.check_output(
        ["git", "show", f"{plan['baseHead']}:{plan['catalogPath']}"], cwd=REPO
    )
    if sha_bytes(baseline_bytes) != plan["catalogSha256Before"]:
        raise SystemExit("base catalog file hash does not match apply plan")
    baseline = json.loads(baseline_bytes)
    baseline_keys = {key: set(value) for key, value in baseline.items() if isinstance(value, dict)}
    expected = copy.deepcopy(baseline)

    changes = {(cell["sourceOrdinal"], cell["locale"]): cell for cell in plan["cells"]}
    if len(changes) != plan["targetChangeCount"] or len(changes) != 60:
        raise SystemExit("apply plan must contain exactly 60 unique target changes")
    held = [row for row in ledger if row["finalDisposition"] == "hold-context"]
    if len(held) != 12 or any(row["sourceOrdinal"] != 160 or row["finalTarget"] is not None for row in held):
        raise SystemExit("ordinal-160 hold gate failed")
    if any(row["sourceOrdinal"] == 160 and row["finalDisposition"] != "hold-context" for row in ledger):
        raise SystemExit("an ordinal-160 cell is not held")

    source_token = __import__("re").compile(r"\{[^{}]+\}")
    verified_refs = 0
    for row in ledger:
        key = (row["sourceOrdinal"], row["locale"])
        if sha_source(row["source"]) != row["sourceSha256"]:
            raise SystemExit(f"source hash mismatch: {key}")
        entry = baseline["messages"].get(row["id"])
        if entry is None or entry.get("source") != row["source"]:
            raise SystemExit(f"pinned source mismatch in base catalog: {key}")
        current = entry["translations"][row["locale"]]
        current_hash = sha_translation(current)
        if current != row["currentTarget"] or current_hash != row["currentTargetSha256"]:
            raise SystemExit(f"pinned current target/hash mismatch: {key}")
        if entry["translationHashes"][row["locale"]] != current_hash:
            raise SystemExit(f"catalog current translationHash mismatch: {key}")
        if entry["translationStatus"][row["locale"]] != "draft":
            raise SystemExit(f"current translation status is not draft: {key}")

        refs = row["callerRefs"]
        if row["callerExists"] != bool(refs):
            raise SystemExit(f"caller presence/ref mismatch: {key}")
        for ref in refs:
            source_file = REPO / ref["path"]
            raw = source_file.read_bytes()
            if sha_bytes(raw) != ref["fileSha256"]:
                raise SystemExit(f"caller file hash mismatch: {key} {ref['path']}")
            lines = raw.decode("utf-8").splitlines()
            if ref["line"] < 1 or ref["line"] > len(lines) or lines[ref["line"] - 1] != ref["lineText"]:
                raise SystemExit(f"caller line mismatch: {key} {ref['path']}:{ref['line']}")
            verified_refs += 1
        if row["finalTarget"] is not None:
            if sha_translation(row["finalTarget"]) != row["finalTargetSha256"]:
                raise SystemExit(f"final target hash mismatch: {key}")
            if sorted(source_token.findall(row["source"])) != sorted(source_token.findall(row["finalTarget"])):
                raise SystemExit(f"placeholder mismatch: {key}")
            if not all(literal in row["finalTarget"] for literal in row["sourceProtectedLiterals"]):
                raise SystemExit(f"protected literal mismatch: {key}")

        planned = changes.get(key)
        if planned:
            if row["finalDisposition"] not in ("correction", "refinement"):
                raise SystemExit(f"planned target has non-change disposition: {key}")
            if planned["id"] != row["id"] or planned["sourceSha256"] != row["sourceSha256"]:
                raise SystemExit(f"plan identity mismatch: {key}")
            if planned["currentTargetSha256"] != row["currentTargetSha256"]:
                raise SystemExit(f"plan current hash mismatch: {key}")
            if planned["finalTarget"] != row["finalTarget"] or planned["finalTargetSha256"] != row["finalTargetSha256"]:
                raise SystemExit(f"plan final target mismatch: {key}")
            target = planned["finalTarget"]
            if sha_source(target) != planned["finalTargetRawSha256"]:
                raise SystemExit(f"final raw target hash mismatch: {key}")
            expected_entry = expected["messages"][row["id"]]
            expected_entry["translations"][row["locale"]] = target
            expected_entry["translationHashes"][row["locale"]] = planned["finalTargetSha256"]
        elif row["finalDisposition"] in ("correction", "refinement"):
            raise SystemExit(f"ratified change is missing from plan: {key}")

    if len(changes) != sum(row["finalDisposition"] in ("correction", "refinement") for row in ledger):
        raise SystemExit("planned changes do not match ratified changed-cell count")
    if list(baseline["messages"]) != list(expected["messages"]):
        raise SystemExit("message IDs or order changed during planning")
    for message_id, entry in baseline["messages"].items():
        after = expected["messages"][message_id]
        for field in ("translationStatus", "translationHashes"):
            if set(entry[field]) != set(after[field]):
                raise SystemExit(f"{field} key set changed: {message_id}")
        if set(entry["translations"]) != set(after["translations"]):
            raise SystemExit(f"translation locale key set changed: {message_id}")
        for locale in entry["translationStatus"]:
            if entry["translationStatus"][locale] != after["translationStatus"][locale]:
                raise SystemExit(f"translation status changed: {message_id}/{locale}")
    expected_bytes = serialize_catalog(expected)
    if sha_bytes(expected_bytes) != plan["catalogSha256After"]:
        raise SystemExit("simulated catalog hash does not match apply plan")

    current_bytes = catalog_path.read_bytes()
    current_hash = sha_bytes(current_bytes)
    if args.apply:
        current_head = git("rev-parse", "HEAD")
        current_tree = git("rev-parse", "HEAD^{tree}")
        if current_hash == plan["catalogSha256Before"]:
            if current_head != plan["baseHead"] or current_tree != plan["baseTree"]:
                raise SystemExit("catalog application must start at the exact pinned PR head/tree")
            atomic_write(catalog_path, expected_bytes)
        elif current_hash != plan["catalogSha256After"]:
            raise SystemExit("catalog is neither the pinned baseline nor the expected applied result")
    elif current_hash != plan["catalogSha256After"]:
        raise SystemExit("catalog readback differs from the expected applied result; pass --apply at the pinned base to apply")

    observed_bytes = catalog_path.read_bytes()
    if sha_bytes(observed_bytes) != plan["catalogSha256After"]:
        raise SystemExit("catalog post-write file hash mismatch")
    observed = json.loads(observed_bytes)
    if list(observed["messages"]) != list(baseline["messages"]):
        raise SystemExit("catalog message IDs/order changed")
    if sha_bytes(baseline_bytes) != plan["catalogSha256Before"]:
        raise SystemExit("baseline catalog changed while verifying")

    readback_rows = []
    dispositions = Counter(row["finalDisposition"] for row in ledger)
    changed_by_locale = Counter()
    for row in ledger:
        entry_before = baseline["messages"][row["id"]]
        entry_after = observed["messages"][row["id"]]
        key = (row["sourceOrdinal"], row["locale"])
        planned = changes.get(key)
        target_after = entry_after["translations"][row["locale"]]
        hash_after = sha_translation(target_after)
        expected_target = planned["finalTarget"] if planned else row["currentTarget"]
        if target_after != expected_target or hash_after != (planned["finalTargetSha256"] if planned else row["currentTargetSha256"]):
            raise SystemExit(f"exact catalog readback mismatch: {key}")
        if entry_after["translationHashes"][row["locale"]] != hash_after:
            raise SystemExit(f"catalog translationHashes readback mismatch: {key}")
        if entry_after["translationStatus"][row["locale"]] != entry_before["translationStatus"][row["locale"]]:
            raise SystemExit(f"translationStatus changed: {key}")
        if planned:
            changed_by_locale[row["locale"]] += 1
        readback_rows.append({
            "sourceOrdinal": row["sourceOrdinal"], "id": row["id"], "locale": row["locale"],
            "sourceSha256": row["sourceSha256"], "currentTarget": row["currentTarget"],
            "currentTranslationHash": row["currentTargetSha256"], "finalDisposition": row["finalDisposition"],
            "targetAfterReadback": target_after, "targetAfterRawSha256": sha_source(target_after),
            "targetAfterTranslationHash": hash_after, "translationStatusBefore": entry_before["translationStatus"][row["locale"]],
            "translationStatusAfter": entry_after["translationStatus"][row["locale"]], "changed": bool(planned),
            "callerExists": row["callerExists"], "callerRefs": row["callerRefs"]
        })

    readback = {
        "repository": plan["repository"], "pullRequest": plan["pullRequest"], "window": plan["window"],
        "inputHead": plan["baseHead"], "inputTree": plan["baseTree"],
        "catalogPath": plan["catalogPath"], "catalogSha256Before": plan["catalogSha256Before"],
        "catalogSha256After": plan["catalogSha256After"], "catalogSha256Observed": sha_bytes(observed_bytes),
        "catalogMessageCountBefore": len(baseline["messages"]), "catalogMessageCountAfter": len(observed["messages"]),
        "reviewedCells": len(ledger), "dispositions": dict(dispositions), "targetChanges": len(changes),
        "targetChangesByLocale": dict(changed_by_locale), "ordinal160HeldCells": len(held),
        "ordinal160NoCaller": all(not row["callerExists"] and not row["callerRefs"] for row in held),
        "callerRefsVerified": verified_refs, "sourceHashesVerified": True,
        "currentTargetsAndHashesPinned": True, "finalTargetHashesVerified": True,
        "finalRawTargetHashesVerified": all(
            sha_source(cell["finalTarget"]) == cell["finalTargetRawSha256"] for cell in plan["cells"]
        ),
        "finalTranslationHashesVerified": True, "placeholderParity": True,
        "protectedLiteralParity": True, "translationStatusesPreserved": True,
        "messageAndKeyStructurePreserved": True, "nativeSpeakerApproval": False,
        "headedBrowserAcceptance": False, "workflowFilesChanged": False,
        "testsBuildsScansCiBrowserOrReleasesRun": False,
        "repositoryOrPrMutationDuringAdjudication": False,
        "metadataExposureCaveat": "Aggregate summary counts and changed-source/hash metadata were visible before the candidate-free ledger was sealed; no proposed translation text was read until after sealing, so strict blinding is not claimed."
    }
    atomic_write(APP / "apply-readback.jsonl", "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in readback_rows).encode("utf-8"))
    atomic_write(APP / "apply-summary.json", (json.dumps(readback, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(readback, ensure_ascii=False))


if __name__ == "__main__":
    main()
