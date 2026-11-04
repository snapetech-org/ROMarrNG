#!/usr/bin/env python3
"""Portable readback verifier for ROMarrNG PR #70 W505-W524."""
import argparse
import collections
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WINDOW = ROOT.parent
CROSS = None
EVIDENCE = ROOT / "evidence"
INPUT = None
_TEMP_DIR = None
PIN_HEAD = "e958b4fd0d9ddeac9333afc4c95da348b7f67cff"
PIN_TREE = "402026ba276ec4603d86d659766af836d839de55"
CATALOG = "romarr/ui-labels.json"


def fail(message):
    raise SystemExit("FAIL: " + message)


def need(condition, message):
    if not condition:
        fail(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text_sha(value):
    return sha(value.encode("utf-8"))


def translation_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha(encoded.encode("utf-8"))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def verify_sums(folder, filename):
    manifest = folder / filename
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        need(len(parts) == 2, f"malformed checksum line {manifest}:{number}")
        digest, rel = parts
        rel = rel.strip().lstrip("*")
        path = (folder / rel).resolve()
        need(path.is_relative_to(folder.resolve()), f"checksum path escapes packet: {rel}")
        need(path.is_file() and sha(path.read_bytes()) == digest, f"checksum mismatch: {rel}")


def main():
    global CROSS, INPUT, _TEMP_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT.parents[4], help="ROMarrNG checkout containing the applied catalog")
    args = parser.parse_args()
    repo = args.repo.resolve()

    verify_sums(WINDOW, "SHA256SUMS.txt")
    _TEMP_DIR = tempfile.TemporaryDirectory(prefix="romarrng-w505-524-cross-")
    extract_root = Path(_TEMP_DIR.name).resolve()
    archive_path = WINDOW / "cross-audit.tar.gz"
    need(archive_path.is_file(), "full sealed cross-review archive is missing")
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            member_path = (extract_root / member.name).resolve()
            need(member_path.is_relative_to(extract_root), "cross archive path escapes extraction root")
            need(member.isfile() or member.isdir(), "cross archive contains a non-regular entry")
        archive.extractall(extract_root)
    CROSS = extract_root / "cross-audit"
    need(CROSS.is_dir(), "cross-review archive has no cross-audit directory")
    INPUT = CROSS / "provenance" / "candidate-free-input"
    verify_sums(CROSS, "CHECKSUMS.sha256")
    cross_result = subprocess.check_output([sys.executable, str(CROSS / "verify_cross.py")], text=True)
    cross = json.loads(cross_result)
    need(cross.get("result") == "PASS" and cross.get("head") == PIN_HEAD and cross.get("tree") == PIN_TREE,
         "sealed cross review did not pass at the exact input pin")
    need((cross.get("cells"), cross.get("selectedChanges"), cross.get("holds"), cross.get("retained")) == (240, 28, 72, 140),
         "sealed cross review counts")
    need(cross.get("tokenMismatches") == {"markup": 0, "numeric": 0, "placeholder": 0, "protectedLiteral": 0},
         "cross token verification")

    packet = read_json(INPUT / "manifest.json")
    pins = read_json(INPUT / "catalog-file-pins.json")
    plan = read_json(EVIDENCE / "apply-plan.json")
    summary = read_json(EVIDENCE / "apply-summary.json")
    invariant = read_json(EVIDENCE / "catalog-invariants.json")
    app_commit = read_json(EVIDENCE / "catalog-commit.json")
    need((packet.get("head"), packet.get("tree"), packet.get("window")) == (PIN_HEAD, PIN_TREE, "W505-W524"),
         "candidate-free manifest pin")
    need((pins.get("commit"), pins.get("tree")) == (PIN_HEAD, PIN_TREE), "candidate-free catalog pin")
    need((plan.get("parent"), plan.get("parentTree"), plan.get("window")) == (PIN_HEAD, PIN_TREE, "W505-W524"),
         "apply plan pin")
    need((plan.get("reviewedCells"), plan.get("selectedChanges"), plan.get("holdCells"), plan.get("retainedCurrentCells")) == (240, 28, 72, 140),
         "apply plan counts")
    need(summary.get("result") == "PASS" and summary.get("cellsReadBack") == 240, "apply summary")

    need(git(repo, "rev-parse", f"{PIN_HEAD}^{{tree}}") == PIN_TREE, "pinned input tree is unavailable or changed")
    before_raw = (EVIDENCE / "pre-apply-ui-labels.json").read_bytes()
    after_raw = (EVIDENCE / "post-apply-ui-labels.json").read_bytes()
    baseline_raw = subprocess.check_output(["git", "-C", str(repo), "show", f"{PIN_HEAD}:{CATALOG}"])
    catalog_commit = app_commit.get("commit")
    need(isinstance(catalog_commit, str) and len(catalog_commit) == 40, "catalog commit attestation")
    need(git(repo, "rev-parse", f"{catalog_commit}^") == PIN_HEAD, "catalog commit parent")
    changed_paths = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", catalog_commit).splitlines()
    need(changed_paths == [CATALOG], "catalog commit contains files outside the catalog")
    committed_raw = subprocess.check_output(["git", "-C", str(repo), "show", f"{catalog_commit}:{CATALOG}"])
    actual_raw = (repo / CATALOG).read_bytes()
    need(before_raw == baseline_raw, "pre-apply snapshot differs from exact pinned catalog")
    need(sha(before_raw) == pins["catalogSha256"] == packet["catalogSha256"], "pinned catalog checksum")
    need(after_raw == committed_raw == actual_raw, "post-apply snapshot differs from committed/current catalog")
    need(sha(after_raw) == app_commit.get("catalogSha256") == invariant.get("afterSha256"), "applied catalog checksum")

    before = json.loads(before_raw)
    after = json.loads(after_raw)
    need(before_raw == (json.dumps(before, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), "preimage serialization")
    need(after_raw == (json.dumps(after, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), "postimage serialization")
    need(list(before["messages"]) == list(after["messages"]) and len(after["messages"]) == 1836,
         "catalog IDs, order, or message count changed")
    need(sha("".join(key + "\n" for key in before["messages"]).encode("utf-8")) == pins["catalogKeyOrderSha256"],
         "catalog key-order pin")

    input_cells = read_jsonl(INPUT / "current-target-cells.jsonl")
    cross_rows = read_jsonl(CROSS / "per-cell-ledger.jsonl")
    selected_rows = read_jsonl(CROSS / "selected-changes.jsonl")
    hold_rows = read_jsonl(CROSS / "holds.jsonl")
    readback = read_jsonl(EVIDENCE / "apply-readback.jsonl")
    selected_ledger = read_jsonl(EVIDENCE / "selected-change-ledger.jsonl")
    hash_updates = read_jsonl(EVIDENCE / "translation-hash-updates.jsonl")
    need(len(input_cells) == len(cross_rows) == len(readback) == 240, "240-cell coverage/readback")
    need(len(selected_rows) == len(selected_ledger) == 28 and len(hold_rows) == 72, "selected/hold coverage")
    need(len(hash_updates) == 3, "expected three canonical translation-hash updates")
    key = lambda row: (row["sourceId"], row["locale"])
    imap = {key(row): row for row in input_cells}
    xmap = {key(row): row for row in cross_rows}
    smap = {key(row): row for row in selected_rows}
    hmap = {key(row): row for row in hold_rows}
    rmap = {key(row): row for row in readback}
    need(len(imap) == len(xmap) == len(rmap) == 240 and imap.keys() == xmap.keys() == rmap.keys(), "cell key sets")
    need(len(smap) == 28 and len(hmap) == 72, "selected/hold key sets")

    disposition_counts = collections.Counter(row["finalDisposition"] for row in cross_rows)
    need(disposition_counts == collections.Counter({"hold_callerless": 72, "retain_current": 140, "select_change": 28}),
         "final disposition counts")
    hold_forbidden = {"source", "currentTarget", "selectedTarget", "proposedTarget", "primaryProposedTarget", "blindProposedTarget"}
    for hold in hold_rows:
        need(not (hold_forbidden & set(hold)), f"hold ledger contains translation text: {key(hold)}")

    selected_by_key = {key(row): row for row in selected_ledger}
    need(selected_by_key.keys() == smap.keys(), "selected-change ledger keys")
    updated_cells = set()
    for cell_key, row in xmap.items():
        source_id, locale = cell_key
        current_row = imap[cell_key]
        before_entry = before["messages"][source_id]
        after_entry = after["messages"][source_id]
        need(before_entry["source"] == after_entry["source"] == current_row["source"], f"source text changed: {cell_key}")
        need(before_entry["sourceHash"] == after_entry["sourceHash"] == row["sourceSha256"] == text_sha(before_entry["source"]),
             f"source hash changed: {cell_key}")
        current = before_entry["translations"][locale]
        actual = after_entry["translations"][locale]
        need(text_sha(current) == current_row["currentTargetSha256"] == row["currentTargetSha256"],
             f"current target hash linkage: {cell_key}")
        read = rmap[cell_key]
        need(read["sourceSha256"] == row["sourceSha256"] and read["currentTargetSha256"] == text_sha(current),
             f"readback source/current hash: {cell_key}")
        if row["finalDisposition"] == "hold_callerless":
            need(cell_key in hmap and cell_key not in smap, f"hold linkage: {cell_key}")
            need(row.get("callerless") is True and row.get("callerEvidence") == [], f"callerless proof: {cell_key}")
            need(actual == current and read["targetUnchanged"] is True and read["proposalTextRecorded"] is False,
                 f"text-free hold readback: {cell_key}")
            need(read["disposition"] == "hold_callerless" and read["readbackTargetSha256"] == text_sha(current),
                 f"hold readback: {cell_key}")
        elif row["finalDisposition"] == "retain_current":
            need(cell_key not in smap and actual == current, f"retained value changed: {cell_key}")
            need(read["disposition"] == "retain_current" and read["targetUnchanged"] is True,
                 f"retained readback: {cell_key}")
        else:
            need(row["finalDisposition"] == "select_change" and cell_key in smap, f"invalid selected cell: {cell_key}")
            chosen = smap[cell_key]
            ledger = selected_by_key[cell_key]
            need(chosen["selectedTarget"] == ledger["selectedTarget"] == actual, f"selected target mismatch: {cell_key}")
            need(text_sha(actual) == chosen["selectedTargetSha256"] == row["selectedTargetSha256"],
                 f"selected target hash mismatch: {cell_key}")
            need(ledger["selectedTargetSha256"] == text_sha(actual), f"selected ledger hash: {cell_key}")
            need(read["disposition"] == "select_change" and read["readbackMatchesSelection"] is True
                 and read["readbackTargetSha256"] == text_sha(actual), f"selected readback: {cell_key}")
            updated_cells.add(cell_key)

    need(len(updated_cells) == 28, "catalog selected translation update count")
    hash_update_map = {(row["sourceId"], row["locale"]): row for row in hash_updates}
    need(len(hash_update_map) == 3 and set(hash_update_map) == {k for k in updated_cells if k[1] in before["messages"][k[0]].get("translationHashes", {})},
         "translation hash update keys")
    actual_hash_update_count = 0
    for source_id, old_entry in before["messages"].items():
        new_entry = after["messages"][source_id]
        need(old_entry["source"] == new_entry["source"] and old_entry["sourceHash"] == new_entry["sourceHash"],
             f"message source changed: {source_id}")
        need(list(old_entry["translations"]) == list(new_entry["translations"]), f"locale order changed: {source_id}")
        need(old_entry.get("translationStatus", {}) == new_entry.get("translationStatus", {}), f"status metadata changed: {source_id}")
        need(old_entry.get("translationReview", {}) == new_entry.get("translationReview", {}), f"review metadata changed: {source_id}")
        for field in (set(old_entry) | set(new_entry)) - {"translations", "translationHashes"}:
            need(old_entry.get(field) == new_entry.get(field), f"entry metadata changed: {source_id}/{field}")
        old_hashes = old_entry.get("translationHashes", {})
        new_hashes = new_entry.get("translationHashes", {})
        need(set(old_hashes) == set(new_hashes), f"translation hash keyset changed: {source_id}")
        for locale, old_value in old_entry["translations"].items():
            cell_key = (source_id, locale)
            if cell_key in updated_cells:
                need(new_entry["translations"][locale] != old_value, f"selected update is a no-op: {cell_key}")
                if locale in old_hashes:
                    need(old_hashes[locale] == translation_hash(old_value), f"stale preexisting hash: {cell_key}")
                    expected_hash = translation_hash(new_entry["translations"][locale])
                    need(new_hashes[locale] == expected_hash, f"canonical translation hash: {cell_key}")
                    update = hash_update_map[cell_key]
                    need(update["oldTranslationHash"] == old_hashes[locale]
                         and update["newTranslationHash"] == expected_hash, f"hash update evidence: {cell_key}")
                    actual_hash_update_count += 1
                else:
                    need(locale not in new_hashes, f"unexpected translation hash metadata: {cell_key}")
            else:
                need(new_entry["translations"][locale] == old_value, f"non-selected translation changed: {cell_key}")
                if locale in old_hashes:
                    need(new_hashes[locale] == old_hashes[locale], f"non-selected translation hash changed: {cell_key}")
    need(actual_hash_update_count == 3, "canonical hash update count")

    prior_holds = read_jsonl(INPUT / "prior-hold-reattestation.jsonl")
    prior_selections = read_jsonl(INPUT / "prior-selection-reattestation.jsonl")
    need(len(prior_holds) == 468 and len(prior_selections) == 120, "carried lineage counts")
    need((EVIDENCE / "prior-hold-reattestation.jsonl").read_bytes() == (INPUT / "prior-hold-reattestation.jsonl").read_bytes(),
         "carried hold evidence copy")
    need((EVIDENCE / "prior-selection-reattestation.jsonl").read_bytes() == (INPUT / "prior-selection-reattestation.jsonl").read_bytes(),
         "prior selection evidence copy")
    prior_hold_keys = set()
    for record in prior_holds:
        cell_key = (record["sourceId"], record["locale"])
        prior_hold_keys.add(cell_key)
        for catalog in (before, after):
            value = catalog["messages"][cell_key[0]]["translations"][cell_key[1]]
            need(text_sha(value) == record["currentTargetSha256"], f"carried hold changed: {cell_key}")
    prior_selected_ids = {row["sourceId"] for row in prior_selections}
    need(not {source_id for source_id, _ in updated_cells} & prior_selected_ids, "selected source overlaps prior selected source")
    need(not updated_cells & prior_hold_keys, "selected cell overlaps prior hold")
    for source_id in prior_selected_ids:
        need(before["messages"][source_id]["translations"] == after["messages"][source_id]["translations"],
             f"prior selected translations changed: {source_id}")
        need(before["messages"][source_id].get("translationHashes", {}) == after["messages"][source_id].get("translationHashes", {}),
             f"prior selected hashes changed: {source_id}")

    print(json.dumps({
        "result": "PASS", "window": "W505-W524", "inputHead": PIN_HEAD, "inputTree": PIN_TREE,
        "catalogCommit": catalog_commit, "catalogSha256": sha(after_raw), "cells": 240,
        "selectedChanges": len(updated_cells), "holds": len(hmap), "retained": 140,
        "readback": len(readback), "canonicalTranslationHashesUpdated": actual_hash_update_count,
        "carriedHolds": len(prior_holds), "priorSelectedSources": len(prior_selected_ids),
        "tokenMismatches": cross["tokenMismatches"], "crossReview": cross,
        "crossBundleManifestSha256": sha((CROSS / "manifest.json").read_bytes()),
        "crossBundleChecksumListSha256": sha((CROSS / "CHECKSUMS.sha256").read_bytes())
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
