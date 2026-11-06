#!/usr/bin/env python3
"""Portable verifier for ROMarrNG PR #70 W485-W504 review/application evidence."""
import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

WINDOW = Path(__file__).resolve().parent
APP = WINDOW / "application"
E = APP / "evidence"
CANDIDATE = WINDOW / "candidate-free-input" / "input"
PRIMARY = WINDOW / "primary-review"
BLIND = WINDOW / "blind-review" / "output"
CROSS = WINDOW / "cross-audit"
PARENT = "6eb494d362ae19503b9199cd2c05c0767cddbc0e"
PARENT_TREE = "b9450b9c6d22c816551fc8d528e8f03413d04595"
CATALOG_COMMIT = "a662c3620e9b5df35092c9d302846b776638f462"
CATALOG_TREE = "a42bc330d836ccebea940366d3fd766dbd710e2d"
CATALOG_PATH = "romarr/ui-labels.json"

def need(ok, message):
    if not ok:
        raise SystemExit("FAIL: " + message)

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

def verify_sums(directory):
    checksum_file = directory / "SHA256SUMS.txt"
    expected = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        need(match is not None, "malformed checksum line in " + str(checksum_file))
        digest, name = match.groups()
        rel = Path(name)
        need(not rel.is_absolute() and ".." not in rel.parts and name not in expected,
             "unsafe or duplicate checksum entry")
        expected[name] = digest
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*")
              if p.is_file() and p != checksum_file}
    need(actual == set(expected), "checksum inventory mismatch in " + str(directory))
    for name, digest in expected.items():
        need(sha((directory / name).read_bytes()) == digest, "checksum mismatch: " + str(directory / name))
    return len(expected)

def verify_packet_input_pins():
    pins = read_json(CROSS / "input-pins.json")
    need(pins["repository"] == "snapetech-org/ROMarrNG" and pins["pullRequest"] == 70,
         "cross-audit repository/PR pin")
    need((pins["head"], pins["tree"]) == (PARENT, PARENT_TREE), "cross-audit head/tree pin")
    roots = {
        "candidateFree": CANDIDATE,
        "primary": PRIMARY,
        "independentBlind": BLIND,
    }
    files_checked = 0
    for packet in pins["inputPackets"]:
        name = packet["packet"]
        need(name in roots, "unknown packet name in cross input pins")
        root = roots[name]
        for record in packet["files"]:
            path = root / record["path"]
            raw = path.read_bytes()
            need(len(raw) == record["bytes"] and sha(raw) == record["sha256"],
                 "cross-audit input pin: " + name + "/" + record["path"])
            files_checked += 1
    return files_checked

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=WINDOW.parents[3])
    repo = ap.parse_args().repo.resolve()
    need(git(repo, "rev-parse", PARENT + "^{tree}") == PARENT_TREE, "review parent tree")
    need(git(repo, "rev-parse", CATALOG_COMMIT + "^{tree}") == CATALOG_TREE, "catalog commit tree")
    need(git(repo, "rev-parse", CATALOG_COMMIT + "^") == PARENT, "catalog commit parent")
    need(git(repo, "merge-base", "--is-ancestor", CATALOG_COMMIT, "HEAD") == "", "catalog commit not in checkout ancestry")
    commit = read_json(E / "catalog-commit.json")
    need(commit["parent"] == PARENT and commit["parentTree"] == PARENT_TREE and
         commit["commit"] == CATALOG_COMMIT and commit["tree"] == CATALOG_TREE,
         "catalog commit manifest pin")
    need(commit["changedPaths"] == ["CHANGELOG.md", CATALOG_PATH], "catalog commit path scope")
    need(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", CATALOG_COMMIT).splitlines() ==
         ["CHANGELOG.md", CATALOG_PATH], "actual catalog commit paths")
    need(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", CATALOG_COMMIT, "--", ".github/workflows")
         == "", "workflow files changed")

    input_count = verify_sums(CANDIDATE)
    primary_count = verify_sums(PRIMARY)
    blind_count = verify_sums(BLIND)
    cross_count = verify_sums(CROSS)
    application_count = verify_sums(APP)
    root_count = verify_sums(WINDOW)
    input_pin_count = verify_packet_input_pins()

    for script, cwd in (
        (CANDIDATE / "verify_input.py", CANDIDATE),
        (PRIMARY / "verify_primary.py", PRIMARY),
        (BLIND / "verify_blind.py", BLIND),
    ):
        result = subprocess.check_output(["python3", str(script)], cwd=cwd, text=True)
        need("PASS" in result, "review packet verifier: " + str(script))

    candidate = read_jsonl(CANDIDATE / "current-target-cells.jsonl")
    primary = read_jsonl(PRIMARY / "primary-ledger.jsonl")
    blind = read_jsonl(BLIND / "blind-ledger.jsonl")
    cross = read_jsonl(CROSS / "cross-ledger.jsonl")
    need(len(candidate) == len(primary) == len(blind) == len(cross) == 240, "240-cell coverage")
    cmap = {(r["sourceId"], r["locale"]): r for r in candidate}
    pmap = {(r["sourceId"], r["locale"]): r for r in primary}
    bmap = {(r["sourceId"], r["locale"]): r for r in blind}
    xmap = {(r["sourceId"], r["locale"]): r for r in cross}
    need(set(cmap) == set(pmap) == set(bmap) == set(xmap), "review cell set mismatch")
    counts = collections.Counter(r["crossDisposition"] for r in cross)
    need(counts == {"accept-current": 201, "correction": 14, "refinement": 1, "hold": 24},
         "cross disposition counts")

    pre_raw = (E / "pre-apply-ui-labels.json").read_bytes()
    post_raw = (E / "post-apply-ui-labels.json").read_bytes()
    need(pre_raw == git_bytes(repo, "show", PARENT + ":" + CATALOG_PATH), "parent catalog snapshot")
    need(post_raw == git_bytes(repo, "show", CATALOG_COMMIT + ":" + CATALOG_PATH), "catalog commit snapshot")
    before = json.loads(pre_raw)
    after = json.loads(post_raw)
    need(sha(pre_raw) == read_json(CANDIDATE / "catalog-file-pins.json")["catalogSha256"],
         "candidate-free catalog preimage")
    need(len(before["messages"]) == len(after["messages"]) == 1836, "catalog message count")
    changes = set()
    hold_positions = set()
    for key, row in xmap.items():
        c, p, b = cmap[key], pmap[key], bmap[key]
        sid, locale = key
        cur = before["messages"][sid]["translations"][locale]
        cur_hash = text_sha(cur)
        need(c["currentTarget"] == p["currentTarget"] == b["currentTarget"] == cur,
             "reviewed current value " + str(key))
        need(c["currentTargetSha256"] == p["currentTargetSha256"] == b["currentTargetSha256"] ==
             row["currentTargetSha256"] == cur_hash, "reviewed current hash " + str(key))
        need(row["crossDisposition"] == p["disposition"] == b["blindDisposition"],
             "review disposition " + str(key))
        got = after["messages"][sid]["translations"][locale]
        disposition = row["crossDisposition"]
        if disposition == "hold":
            hold_positions.add(row["position"])
            need("currentTarget" not in row and "selectedTarget" not in row and
                 "proposedTarget" not in row, "cross hold includes target text")
            need(p.get("proposedTarget") is None and b.get("proposedTarget") is None,
                 "held row includes proposal")
            need(got == cur, "held catalog value changed")
        else:
            selected = row["selectedTarget"]
            need(selected == p["selectedTarget"] == b["selectedTarget"], "selected target agreement")
            need(row["selectedTargetSha256"] == p["selectedTargetSha256"] ==
                 b["selectedTargetSha256"] == text_sha(selected), "selected target hash")
            need(got == selected, "catalog readback differs from cross selection")
            if disposition == "accept-current":
                need(selected == cur, "accept-current changed")
            else:
                need(disposition in ("correction", "refinement") and selected != cur,
                     "invalid selected update")
                checks = row["tokenAndLiteralChecks"]
                need(checks["selectedPlaceholderMultisetMatches"] and
                     checks["selectedNumericTokensPreserved"] and
                     checks["selectedProtectedLiteralsPreserved"], "selected token/literal checks")
                changes.add(key)
    need(hold_positions == {493, 502}, "hold position set")
    need(len(changes) == 15, "selected change count")

    actual_diff = {(sid, locale) for sid, entry in before["messages"].items()
                   for locale, value in entry["translations"].items()
                   if after["messages"][sid]["translations"][locale] != value}
    need(actual_diff == changes, "catalog has non-selected translation changes")
    need(list(before) == list(after) and list(before["messages"]) == list(after["messages"]),
         "catalog key order changed")
    need(all(list(before["messages"][sid]["translations"]) ==
             list(after["messages"][sid]["translations"]) for sid in before["messages"]),
         "locale order changed")
    need(all({k: v for k, v in before["messages"][sid].items() if k != "translations"} ==
             {k: v for k, v in after["messages"][sid].items() if k != "translations"}
             for sid in before["messages"]), "source or translation metadata changed")

    prior_holds = read_jsonl(E / "prior-hold-reattestation.jsonl")
    prior_selections = read_jsonl(E / "prior-selection-reattestation.jsonl")
    need(len(prior_holds) == 444 and len(prior_selections) == 100, "lineage counts")
    for row in prior_holds:
        sid, locale = row["sourceId"], row["locale"]
        need(row["targetUnchanged"] is True and row["priorTargetSha256"] == row["currentTargetSha256"],
             "prior hold reattestation")
        for catalog in (before, after):
            value = catalog["messages"][sid]["translations"][locale]
            need(text_sha(value) == row["currentTargetSha256"], "carried hold changed: " + sid + "/" + locale)
    for row in prior_selections:
        sid = row["sourceId"]
        need(row["selectionUnchanged"] and row["sourceHashMatches"] and
             row["registryMembershipAndHashMatch"], "prior selected-source reattestation")
        need(before["messages"][sid]["source"] == after["messages"][sid]["source"] and
             before["messages"][sid]["translations"] == after["messages"][sid]["translations"],
             "prior selected source changed: " + sid)

    readback = read_jsonl(E / "apply-readback.jsonl")
    selected = read_jsonl(E / "selected-change-ledger.jsonl")
    need(len(readback) == 240 and len(selected) == 15, "application ledger counts")
    rbmap = {(r["sourceId"], r["locale"]): r for r in readback}
    need(set(rbmap) == set(xmap), "readback cell set")
    for key, row in xmap.items():
        r = rbmap[key]
        sid, locale = key
        value = after["messages"][sid]["translations"][locale]
        need(r["readbackTargetSha256"] == text_sha(value), "readback target hash " + str(key))
        if row["crossDisposition"] == "hold":
            need(r.get("proposalTextRecorded") is False and r["targetUnchanged"], "hold readback policy")
        else:
            need(r["readbackMatchesSelection"] is True and r["target"] == value,
                 "readback selection " + str(key))
    summary = read_json(E / "apply-summary.json")
    need(summary["result"] == "PASS" and summary["selectedChanges"] == 15 and
         summary["cellsReadBack"] == 240 and summary["holds"] == 24 and
         summary["carriedHoldsPreserved"] == 444 and summary["priorSelectionsPreserved"] == 100,
         "application summary")
    live = read_json(E / "live-pr-after-catalog-apply.json")
    need(live["state"] == "OPEN" and live["draft"] is True and live["head"] == CATALOG_COMMIT and
         live["deploymentsAtHead"] == live["checkRunsAtHead"] == live["actionsRunsAtHead"] == 0,
         "post-catalog PR/deployment snapshot")

    print(json.dumps({
        "result": "PASS", "window": "W485-W504", "cells": 240,
        "dispositions": dict(counts), "selectedChanges": len(changes),
        "holdPositions": sorted(hold_positions), "carriedHolds": len(prior_holds),
        "priorSelections": len(prior_selections), "catalogMessageCount": 1836,
        "catalogCommit": CATALOG_COMMIT, "catalogTree": CATALOG_TREE,
        "crossInputFilesPinned": input_pin_count,
        "checksumFilesVerified": {
            "candidateFree": input_count, "primary": primary_count, "blind": blind_count,
            "cross": cross_count, "application": application_count, "window": root_count
        }
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
