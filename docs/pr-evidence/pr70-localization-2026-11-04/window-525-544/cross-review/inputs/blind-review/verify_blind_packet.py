#!/usr/bin/env python3
"""Verify the ROMarrNG PR #70 W525-W544 clean blind review packet."""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEAD = "eda48333438591ecc67f829c50ef2d521f1e7a5e"
TREE = "3db18e56d0c7ac08a564a6baff61eba25f0a01da"
LOCALES = ("ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_text(text: str) -> str:
    return sha(text.encode("utf-8"))


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit("FAIL: " + message)


def verify_manifest(folder: Path, name: str) -> int:
    manifest = folder / name
    entries = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        require(rel not in entries, f"duplicate checksum entry: {rel}")
        path = (folder / rel).resolve()
        require(path.is_relative_to(folder.resolve()), f"checksum path escapes packet: {rel}")
        require(path.is_file() and sha(path.read_bytes()) == digest, f"checksum mismatch: {rel}")
        entries[rel] = digest
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p.resolve() != manifest.resolve()}
    require(set(entries) == actual, "checksum inventory mismatch")
    return len(entries)


def verify_input_checksums(input_dir: Path) -> int:
    return verify_manifest(input_dir, "SHA256SUMS.txt")


def run_input_verifier(input_dir: Path, repo: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(input_dir / "verify_input.py"), "--repo", str(repo)],
        cwd=input_dir,
        check=True,
        text=True,
        capture_output=True,
    )
    value = json.loads(result.stdout.strip().splitlines()[-1])
    require(value.get("result") == "PASS", "candidate-free input verifier failed")
    require(value.get("head") == HEAD and value.get("tree") == TREE, "candidate-free source pin mismatch")
    return value


def verify(input_dir: Path, repo: Path) -> dict:
    packet_manifest_count = verify_manifest(ROOT, "SHA256SUMS.txt")
    input_manifest_count = verify_input_checksums(input_dir)
    input_manifest = read_json(input_dir / "manifest.json")
    require(input_manifest["candidateFree"] is True, "input is not marked candidate-free")
    require(input_manifest["proposedTargetsIncluded"] is False and input_manifest["reviewDecisionsIncluded"] is False,
            "candidate-free input contains proposals or review decisions")
    input_result = run_input_verifier(input_dir, repo)
    recorded_input = read_json(ROOT / "input-verification-results.json")
    require(recorded_input.get("result") == "PASS" and recorded_input.get("head") == HEAD, "recorded candidate-free result")

    worktree_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    worktree_tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True).strip()
    worktree_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip()
    require(worktree_head == HEAD and worktree_tree == TREE and worktree_status == "", "source worktree is not clean at pin")

    before = read_json(ROOT / "PR-attestation-before.json")
    after = read_json(ROOT / "PR-attestation-after.json")
    for att in (before, after):
        require(att["pullRequest"] == 70 and att["state"] == "OPEN" and att["draft"] is True and att["merged"] is False,
                "PR state/draft attestation")
        require(att["head"] == HEAD and att["tree"] == TREE and att["headTreeMatchesPin"], "PR head/tree attestation")
        require(att["branchAndPullRefsMatchApi"] is True, "PR branch/pull ref attestation")
        require(att["branchRefOid"] == HEAD and att["pullRefOid"] == HEAD and att["branchApiHead"] == HEAD,
                "PR refs do not match pinned head")

    selection = read_json(input_dir / "selection.json")
    source_rows = selection["selectedSources"]
    current_rows = read_jsonl(input_dir / "current-target-cells.jsonl")
    context_rows = read_jsonl(input_dir / "source-contexts.jsonl")
    decisions = read_jsonl(ROOT / "blind-decisions.jsonl")
    require(len(source_rows) == 20 and len(context_rows) == 20 and len(current_rows) == len(decisions) == 240,
            "review cell inventory")
    require(tuple(selection["localeOrder"]) == LOCALES, "locale order mismatch")
    source_by_id = {r["sourceId"]: r for r in source_rows}
    context_by_id = {r["sourceId"]: r for r in context_rows}
    cell_by_key = {(r["position"], r["locale"]): r for r in current_rows}
    decision_by_key = {(r["position"], r["locale"]): r for r in decisions}
    require(len(cell_by_key) == len(decision_by_key) == 240, "duplicate cell key")
    require(set(cell_by_key) == set(decision_by_key), "blind decisions do not cover exact candidate-free cell set")

    counts = collections.Counter()
    revisions_by_locale = collections.Counter()
    for key, cell in cell_by_key.items():
        row = decision_by_key[key]
        source = source_by_id[cell["sourceId"]]
        context = context_by_id[cell["sourceId"]]
        require(cell["containsCandidate"] is False, "candidate contamination in input cell")
        require(row["sourceId"] == cell["sourceId"] == source["sourceId"], "source ID linkage")
        require(row["source"] == cell["source"] == source["source"], "source text linkage")
        require(row["sourceSha256"] == cell["sourceSha256"] == source["sourceSha256"], "source hash linkage")
        require(row["sourceIdSha256"] == sha_text(cell["sourceId"]), "source ID hash")
        require(row["catalogZeroBasedIndex"] == cell["catalogZeroBasedIndex"] == cell["position"], "catalog position linkage")
        require(row["callerContextSha256"] == cell["callerContextSha256"] == context["contextSha256"], "caller context hash")
        expected_refs = [{'path': x['path'], 'line': x['line'], 'lineSha256': x['lineSha256'], 'excerptSha256': x['excerptSha256']} for x in cell['callerRefs']]
        require(row["callerRefs"] == expected_refs, "caller references linkage")
        require(row["callerlessSource"] == bool(context.get("callerless", False)), "callerless source flag")
        require(row["currentTarget"] == cell["currentTarget"], "current target linkage")
        require(row["currentTargetSha256"] == cell["currentTargetSha256"] == sha_text(cell["currentTarget"]), "current target hash")
        require(row["decision"] in ("accept-current", "revise"), "unknown blind decision")
        reviewed = row["reviewedTarget"]
        require(isinstance(reviewed, str) and reviewed, "reviewed target missing")
        require(row["reviewedTargetSha256"] == sha_text(reviewed), "reviewed target hash")
        require(isinstance(row["rationale"], str) and row["rationale"].strip(), "cell rationale missing")
        if row["decision"] == "accept-current":
            require(row["proposalTarget"] is None and row["proposalTargetSha256"] is None, "accept-current unexpectedly proposes a change")
            require(reviewed == cell["currentTarget"] and row["reviewedTargetSha256"] == cell["currentTargetSha256"], "accepted target is not current")
        else:
            require(row["proposalTarget"] == reviewed and row["proposalTargetSha256"] == row["reviewedTargetSha256"], "revision proposal linkage")
            require(reviewed != cell["currentTarget"], "revision does not change current target")
            revisions_by_locale[row["locale"]] += 1
        ta = row["tokenAssessment"]
        require(ta["placeholdersPreserved"] and ta["markupPreserved"] and ta["numericTokensPreserved"] and ta["protectedLiteralsPreserved"],
                "proposal token/protected literal assessment")
        source_ph = sorted(cell["sourcePlaceholderTokens"])
        target_ph = sorted(re.findall(r"\{[^{}]+\}", reviewed))
        source_tags = sorted(cell["sourceMarkupTags"])
        target_tags = sorted(re.findall(r"</?[A-Za-z][^>]*>", reviewed))
        source_nums = sorted(cell["sourceNumericTokens"])
        target_nums = sorted(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?%?", reviewed))
        require(source_ph == target_ph and source_tags == target_tags and source_nums == target_nums, "actual proposal token parity")
        require(all(lit in reviewed for lit in cell["sourceProtectedLiterals"]), "actual proposal protected literal parity")
        counts[row["decision"]] += 1

    require(counts == {"accept-current": 222, "revise": 18}, f"decision counts: {counts}")
    require(sum(revisions_by_locale.values()) == 18, "revision count by locale")

    prior_files = {
        "prior-hold-reattestation-hash-only.jsonl": "prior-hold-reattestation.jsonl",
        "prior-applied-cell-reattestation-hash-only.jsonl": "prior-applied-cell-reattestation.jsonl",
        "prior-selection-reattestation-hash-only.jsonl": "prior-selection-reattestation.jsonl",
    }
    for output_name, input_name in prior_files.items():
        require((ROOT / output_name).read_bytes() == (input_dir / input_name).read_bytes(), f"prior hash-only lineage changed: {output_name}")
    prior_holds = read_jsonl(ROOT / "prior-hold-reattestation-hash-only.jsonl")
    prior_applied = read_jsonl(ROOT / "prior-applied-cell-reattestation-hash-only.jsonl")
    prior_selected = read_jsonl(ROOT / "prior-selection-reattestation-hash-only.jsonl")
    require(len(prior_holds) == 540 and len(prior_applied) == 28 and len(prior_selected) == 140, "prior hash-only lineage counts")
    forbidden = {"source", "sourceText", "currentTarget", "selectedTarget", "target", "translation"}
    require(not any(forbidden.intersection(row) for row in prior_holds), "prior hold sidecar contains text")

    protected = read_json(ROOT / "protected-literal-assessments.json")
    require(protected["cellCount"] == 240 and protected["proposalTokenMismatches"] == 0 and protected["protectedLiteralProposalMismatches"] == 0,
            "protected literal summary")
    manifest = read_json(ROOT / "manifest.json")
    require(manifest["head"] == HEAD and manifest["tree"] == TREE and manifest["cellCount"] == 240,
            "blind packet manifest pin/count")
    require(manifest["acceptCurrentCount"] == 222 and manifest["reviseCount"] == 18 and manifest["newHoldCount"] == 0,
            "blind packet manifest counts")
    require(manifest["candidateFreeInputManifestSha256"] == sha((input_dir / "SHA256SUMS.txt").read_bytes()), "input checksum manifest linkage")

    recorded = read_json(ROOT / "verification-results.json")
    require(recorded["candidateFreeInputVerifier"]["result"] == "PASS", "recorded input verifier result")
    require(recorded["blindCellCount"] == 240 and recorded["acceptCurrentCount"] == 222 and recorded["reviseCount"] == 18,
            "recorded blind counts")
    return {
        "result": "PASS", "repository": "snapetech-org/ROMarrNG", "pullRequest": 70,
        "head": HEAD, "tree": TREE, "window": "W525-W544", "cells": 240,
        "acceptCurrent": 222, "revise": 18, "holds": 0,
        "revisionsByLocale": dict(sorted(revisions_by_locale.items())),
        "priorHoldHashes": len(prior_holds), "priorAppliedCellHashes": len(prior_applied),
        "priorSelectionHashes": len(prior_selected), "inputVerifier": input_result["result"],
        "inputChecksums": input_manifest_count, "packetChecksums": packet_manifest_count,
        "PRBeforeAndAfter": "OPEN/DRAFT at exact pinned head; branch/pull refs match API"
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="candidate-free input directory")
    parser.add_argument("--repo", type=Path, required=True, help="clean exact-head source worktree")
    args = parser.parse_args()
    print(json.dumps(verify(args.input, args.repo), ensure_ascii=False, sort_keys=True))
