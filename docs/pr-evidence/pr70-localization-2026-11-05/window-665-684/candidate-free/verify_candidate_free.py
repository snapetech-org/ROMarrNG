#!/usr/bin/env python3
"""Portable verifier for the W665-W684 candidate-free packet."""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

HEAD = "8b7589775c526866e474112b4f4168782b02f881"
TREE = "fb0ba93172f6832c687e001ce6c0fff08b5a33eb"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "input"
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
TAG = re.compile(r"<[^>]+>")
NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
PROTECTED = ["Gaseous", "Retrom", "SeerrNG", "ROMarrNG", "ROMarr", "ES-DE", "No-Intro", "Redump", "DAT", "IGDB", "ISO9660", "PLAYSTATION", "PlayStation", "PS2", "ROMs", "ROM", "PC", "API", "ROMARR_API_KEY", "Linksnappy", "Moonlight", "PIN", "NPSSO", "NZBHydra2", "Newznab", "/torznab/api", "NZBVortex", "HTTPS", "NZB", "Preferences"]

def sha(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

def fail(message):
    raise SystemExit("FAIL " + message)

def verify_sums(root):
    root = Path(root)
    sums_path = root / "SHA256SUMS.txt"
    listed = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        path = (root / rel).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes()) != digest:
            fail(f"checksum {rel}")
        if rel in listed:
            fail(f"duplicate checksum {rel}")
        listed[rel] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != sums_path}
    if set(listed) != actual:
        fail(f"checksum coverage {root}")

def tokens(value):
    protected = []
    for literal in PROTECTED:
        found = literal in value if literal.startswith("/") else bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(literal) + r"(?![A-Za-z0-9])", value))
        if found:
            protected.append(literal)
    return {
        "placeholders": PLACEHOLDER.findall(value),
        "markup": TAG.findall(value),
        "numbers": NUMBER.findall(value),
        "protectedLiterals": sorted(set(protected)),
    }

def verify_context(ctx, source):
    core = {
        "sourceId": ctx["sourceId"], "source": source, "sourceSha256": ctx["sourceSha256"],
        "head": ctx["head"], "searchMethod": ctx["searchMethod"],
        "productionFilesSearched": ctx["productionFilesSearched"],
        "exactMatchCount": ctx["exactMatchCount"], "callerless": ctx["callerless"],
        "callers": ctx["callers"],
    }
    if sha(source) != ctx["sourceSha256"] or sha(canonical(core)) != ctx["contextSha256"]:
        fail(f"caller context hash {ctx['sourceId']}")
    if ctx["callerless"] != (ctx["exactMatchCount"] == 0) or (ctx["callerless"] and ctx["callers"]):
        fail(f"callerless context shape {ctx['sourceId']}")
    if not ctx["callerless"] and len(ctx["callers"]) != ctx["exactMatchCount"]:
        fail(f"caller count {ctx['sourceId']}")

def verify_repo(repo, manifest, rows, contexts, selected, prior_selection, prior_holds, prior_applied, readbacks):
    repo = repo.resolve()
    git = lambda *args: subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    if git("rev-parse", "HEAD") != HEAD or git("rev-parse", "HEAD^{tree}") != TREE:
        fail("repo pin")
    if git("status", "--porcelain=v1", "--untracked-files=all") or git("branch", "--show-current"):
        fail("repo is not clean and detached")
    catalog_path = "romarr/ui-labels.json"
    catalog_raw = (repo / catalog_path).read_bytes()
    catalog = json.loads(catalog_raw)
    messages = catalog["messages"]
    ids = list(messages)
    if len(ids) != manifest["catalogMessageCount"] or sha(catalog_raw) != manifest["catalogSha256"]:
        fail("catalog file pin")
    if sha("\n".join(ids) + "\n") != manifest["catalogKeyOrderSha256"]:
        fail("catalog order hash")
    order = read_jsonl(INPUT / "catalog-key-order.jsonl")
    if len(order) != len(ids):
        fail("catalog key order count")
    for i, (sid, row) in enumerate(zip(ids, order)):
        if row["catalogZeroBasedIndex"] != i or row["sourceId"] != sid or row["sourceSha256"] != sha(messages[sid]["source"]):
            fail("catalog key order record")
    if sha((repo / "romarr/ui-source-messages.json").read_bytes()) != manifest["sourceQueueSha256"]:
        fail("source registry hash")
    snapshot = read_json(repo / "romarr/ui-source-snapshot.json")
    if sha(canonical(snapshot)) != manifest["sourceSnapshotSha256"]:
        fail("source snapshot hash")
    for pin in read_json(INPUT / "source-file-pins.json")["files"]:
        path = repo / pin["path"]
        if not path.is_file() or sha(path.read_bytes()) != pin["fileSha256"] or git("rev-parse", f"{HEAD}:{pin['path']}") != pin["gitBlob"]:
            fail(f"source file pin {pin['path']}")
    context_map = {row["sourceId"]: row for row in contexts}
    if len(context_map) != 20:
        fail("current source context coverage")
    for sid, ctx in context_map.items():
        verify_context(ctx, ctx.get("source", messages[sid]["source"]))
    for row in selected:
        sid, idx = row["sourceId"], row["catalogZeroBasedIndex"]
        if idx not in range(665, 685) or ids[idx] != sid or sha(messages[sid]["source"]) != row["sourceSha256"]:
            fail(f"selected source {sid}")
        if "source" in row and row["source"] != messages[sid]["source"]:
            fail(f"selected source text {sid}")
        if ("source" not in row) != bool(row.get("sourceTextOmitted")):
            fail(f"selected source redaction {sid}")
    if len(selected) != 20 or len({r["sourceId"] for r in selected}) != 20:
        fail("selected source uniqueness")
    if len(prior_selection) != 280 or len({r["sourceId"] for r in prior_selection}) != 280:
        fail("prior selection count/uniqueness")
    for row in prior_selection:
        sid, idx = row["sourceId"], row["catalogZeroBasedIndex"]
        msg = messages.get(sid)
        if msg is None or idx < 0 or idx >= len(ids) or ids[idx] != sid or sha(msg["source"]) != row["currentSourceSha256"] or row["currentSourceSha256"] != row["priorSourceSha256"]:
            fail(f"prior selected source {sid}")
    for row in rows:
        sid, loc, idx = row["sourceId"], row["locale"], row["catalogZeroBasedIndex"]
        msg = messages[sid]
        if idx not in range(665, 685) or ids[idx] != sid:
            fail(f"current selection index {sid}")
        if sha(msg["source"]) != row["sourceSha256"] or sha(msg["translations"][loc]) != row["currentTargetSha256"]:
            fail(f"current cell hash {sid}/{loc}")
        if row["callerContextSha256"] != context_map[sid]["contextSha256"] or row["callerless"] != context_map[sid]["callerless"]:
            fail(f"current cell context {sid}/{loc}")
        if row["callerless"]:
            if any(k in row for k in ("source", "sourceText", "currentTarget", "target", "targetText", "proposedTarget")):
                fail("callerless cell text leak")
        elif row.get("source") != msg["source"] or row.get("currentTarget") != msg["translations"][loc]:
            fail(f"current cell text {sid}/{loc}")
    for row in prior_holds:
        sid, loc = row["sourceId"], row["locale"]
        msg = messages[sid]
        if sha(msg["source"]) != row["sourceSha256"] or sha(msg["translations"][loc]) != row["currentTargetSha256"] or not row["targetUnchanged"]:
            fail(f"prior hold hash {sid}/{loc}")
    for row in prior_applied:
        sid, loc = row["sourceId"], row["locale"]
        msg = messages[sid]
        if sha(msg["source"]) != row["sourceSha256"] or sha(msg["translations"][loc]) != row["currentTargetSha256"] or not row["targetUnchanged"]:
            fail(f"prior applied hash {sid}/{loc}")
    for window, items in readbacks.items():
        for row in items:
            sid, loc = row["sourceId"], row["locale"]
            msg = messages[sid]
            if sha(msg["source"]) != row["sourceSha256"] or sha(msg["translations"][loc]) != row["currentTargetSha256"]:
                fail(f"prior readback hash {window}/{sid}/{loc}")
    return {"repoPin": "PASS", "repoCleanDetached": True, "catalogCellsRechecked": len(rows), "priorSelectionsRechecked": len(prior_selection), "priorHoldsRechecked": len(prior_holds), "priorAppliedRechecked": len(prior_applied)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args()
    verify_sums(INPUT)
    verify_sums(ROOT)
    manifest = read_json(INPUT / "manifest.json")
    if (manifest.get("head"), manifest.get("tree"), manifest.get("window"), manifest.get("candidateFree")) != (HEAD, TREE, "W665-W684", True):
        fail("manifest exact pin")
    if manifest.get("proposedTargetsIncluded") or manifest.get("reviewDecisionsIncluded") or manifest.get("callerlessCellTextIncluded"):
        fail("candidate-free boundary")
    rows = read_jsonl(INPUT / "candidate-free-cells.jsonl")
    contexts = read_jsonl(INPUT / "source-contexts.jsonl")
    selected = read_jsonl(INPUT / "selected-sources.jsonl")
    prior_selection = read_jsonl(INPUT / "prior-selection-reattestation.jsonl")
    holds = read_jsonl(INPUT / "prior-hold-reattestation.jsonl")
    applied = read_jsonl(INPUT / "prior-applied-cell-reattestation.jsonl")
    if len(rows) != 240 or len(contexts) != 20 or len(selected) != 20:
        fail("current coverage")
    if [(r["catalogZeroBasedIndex"], r["locale"]) for r in rows] != [(i, loc) for i in range(665, 685) for loc in LOCALES]:
        fail("current cell ordering")
    selected_map = {r["sourceId"]: r for r in selected}
    context_map = {r["sourceId"]: r for r in contexts}
    if len(selected_map) != 20 or len(context_map) != 20:
        fail("source ID uniqueness")
    hold_count = 0
    for row in rows:
        sid, loc = row["sourceId"], row["locale"]
        ctx = context_map.get(sid)
        if not ctx or row["callerContextSha256"] != ctx["contextSha256"] or row["callerless"] != ctx["callerless"] or row["literalCallerCount"] != ctx["exactMatchCount"]:
            fail(f"cell/context binding {sid}/{loc}")
        if row.get("candidateFree") is not True or any(k in row for k in ("proposedTarget", "recommendedTarget", "reviewDecision")):
            fail(f"current review content {sid}/{loc}")
        if row["callerless"]:
            hold_count += 1
            if row.get("cellDisposition") != "hold-callerless-hash-only" or any(k in row for k in ("source", "sourceText", "currentTarget", "target", "targetText")):
                fail("callerless cell is not text-free hash-only")
        else:
            if not isinstance(row.get("source"), str) or not isinstance(row.get("currentTarget"), str):
                fail(f"missing caller-backed text {sid}/{loc}")
            if sha(row["source"]) != row["sourceSha256"] or sha(row["currentTarget"]) != row["currentTargetSha256"]:
                fail(f"current text hash {sid}/{loc}")
            source_tokens, target_tokens = tokens(row["source"]), tokens(row["currentTarget"])
            placeholders_ok = collections.Counter(source_tokens["placeholders"]) == collections.Counter(target_tokens["placeholders"])
            markup_ok = collections.Counter(source_tokens["markup"]) == collections.Counter(target_tokens["markup"])
            source_nums, target_nums = collections.Counter(source_tokens["numbers"]), collections.Counter(target_tokens["numbers"])
            extra_nums = list((target_nums - source_nums).elements())
            numeric_presentation = bool(re.search(r"\bzero\b", row["source"], re.I) and not source_tokens["numbers"] and extra_nums == ["0"])
            numeric_ok = not (source_nums - target_nums) and (not extra_nums or numeric_presentation)
            missing_protected = [x for x in source_tokens["protectedLiterals"] if x not in row["currentTarget"]]
            if (row["sourcePlaceholderTokens"], row["currentPlaceholderTokens"], row["placeholderMultisetMatches"]) != (source_tokens["placeholders"], target_tokens["placeholders"], placeholders_ok):
                fail(f"placeholder evidence {sid}/{loc}")
            if (row["sourceMarkupTags"], row["currentMarkupTags"], row["markupMatches"]) != (source_tokens["markup"], target_tokens["markup"], markup_ok):
                fail(f"markup evidence {sid}/{loc}")
            if (row["sourceNumericTokens"], row["currentNumericTokens"], row["numericTokensPreserved"], row["numericPresentationEquivalent"]) != (source_tokens["numbers"], target_tokens["numbers"], numeric_ok, numeric_presentation):
                fail(f"numeric evidence {sid}/{loc}")
            if (row["sourceProtectedLiterals"], row["missingProtectedLiterals"], row["protectedLiteralsPreserved"]) != (source_tokens["protectedLiterals"], missing_protected, not missing_protected):
                fail(f"protected literal evidence {sid}/{loc}")
    if hold_count != manifest["callerlessCurrentTargetCellCount"] or hold_count != 12 * manifest["callerlessSourceCount"]:
        fail("callerless cell count")
    for row in contexts:
        if row["callerless"]:
            if "source" in row or not row.get("sourceTextOmitted") or row.get("callers") != []:
                fail("callerless context text leak")
        elif "source" not in row or len(row["callers"]) != row["exactMatchCount"]:
            fail("caller-backed context")
    for row in selected:
        if row["sourceId"] in context_map and context_map[row["sourceId"]]["callerless"]:
            if "source" in row or not row.get("sourceTextOmitted"):
                fail("callerless selected source text leak")
    if len(prior_selection) != 280 or len({r["sourceId"] for r in prior_selection}) != 280:
        fail("prior selection count")
    if len(holds) != 820 or len(applied) != 91:
        fail("prior hold/application count")
    for row in holds:
        if any(k in row for k in ("source", "sourceText", "currentTarget", "target", "targetText", "proposedTarget")):
            fail("prior hold text leak")
    if any(not row["targetUnchanged"] for row in holds + applied):
        fail("prior target changed flag")
    readbacks = {}
    for path in INPUT.glob("prior-*-cell-hash-reattestation.jsonl"):
        data = read_jsonl(path)
        if data:
            window = data[0]["priorWindow"]
            if len(data) != 240:
                fail(f"readback row count {window}")
            readbacks[window] = data
    if len(readbacks) != 5:
        fail("five prior readback windows")
    lineage = read_json(INPUT / "prior-window-lineage.json")
    if lineage.get("result") != "PASS" or lineage.get("previousSourceSelectionsReattested") != 280 or lineage.get("previousHeldCellsReattested") != 820 or lineage.get("previousAppliedCellsReattested") != 91:
        fail("prior lineage counts")
    if not lineage.get("w645BlindSummaryPinWarning", {}).get("blindChecksumMismatchRecorded") or lineage.get("w625EvidenceCaveat", {}).get("missingFromPriorCommittedPrTree") != 31:
        fail("prior caveat preservation")
    before = read_json(INPUT / "PR-attestation-before.json")
    after = read_json(INPUT / "PR-attestation-after-candidate-free.json")
    for att in (before, after):
        if (att["state"], att["draft"], att["merged"], att["head"], att["tree"], att["apiCommitTree"], att["branchRefOid"], att["pullRefOid"]) != ("OPEN", True, False, HEAD, TREE, TREE, HEAD, HEAD):
            fail("live attestation pin")
    for key in ("head", "tree", "apiCommitTree", "branchRefOid", "pullRefOid", "baseLiveRefOid", "bodySha256", "bodyBytes"):
        if before[key] != after[key]:
            fail("before/after attestation drift")
    repo_result = verify_repo(args.repo, manifest, rows, contexts, selected, prior_selection, holds, applied, readbacks) if args.repo else {"repoPin": "NOT_CHECKED"}
    print(json.dumps({"result": "PASS", "exactHead": HEAD, "exactTree": TREE, "cells": len(rows), "callerlessHashOnlyCells": hold_count, "priorSelections": len(prior_selection), "priorHolds": len(holds), "priorAppliedCells": len(applied), "priorReadbackWindows": len(readbacks), "currentWindowProposalOrReviewFields": False, **repo_result}, sort_keys=True))

if __name__ == "__main__":
    main()
