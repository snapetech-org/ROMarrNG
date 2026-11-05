#!/usr/bin/env python3
"""Portable, offline verification of the W645-W664 candidate-free inputs."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

HEAD = "9f8832f67195323955172dd4c3c40e29cbabb5da"
TREE = "d6066baa3d03d3b4c6034e5af061fc4bc278b0f9"
WINDOW = "W645-W664"
BRANCH = "task/localization-translation-review-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
TAG = re.compile(r"<[^>]+>")
NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
PROTECTED = ["Gaseous", "Retrom", "SeerrNG", "ROMarrNG", "ROMarr", "ES-DE", "No-Intro", "Redump", "DAT", "IGDB", "ISO9660", "PLAYSTATION", "PlayStation", "PS2", "ROMs", "ROM", "PC", "API", "ROMARR_API_KEY", "Linksnappy", "Moonlight", "PIN", "NPSSO", "NZBHydra2", "Newznab", "/torznab/api", "NZBVortex", "HTTPS", "NZB", "Preferences"]


def fail(message: str) -> None:
    raise SystemExit("FAIL: " + message)


def sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def protected(text: str) -> list[str]:
    result = []
    for literal in PROTECTED:
        if literal.startswith("/"):
            matched = literal in text
        else:
            matched = bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(literal) + r"(?![A-Za-z0-9])", text))
        if matched:
            result.append(literal)
    return sorted(set(result))


def tokens(text: str) -> dict:
    return {"placeholders": PLACEHOLDER.findall(text), "markup": TAG.findall(text), "numbers": NUMBER.findall(text), "protectedLiterals": protected(text)}


def production_paths(repo: Path) -> list[str]:
    raw = git(repo, "ls-tree", "-r", "--name-only", HEAD, "--", "romarr").splitlines()
    allowed = {".py", ".js", ".html", ".jinja", ".jinja2", ".css", ".ts", ".tsx"}
    result = []
    for rel in raw:
        path = Path(rel)
        parts = rel.lower().split("/")
        if path.suffix.lower() not in allowed or any(x in parts for x in ("test", "tests", "__pycache__")) or path.name.startswith("test_") or path.name.endswith("_test.py"):
            continue
        result.append(rel)
    return result


def file_tuple(repo: Path, rel: str) -> tuple[str, bytes, str]:
    data = subprocess.check_output(["git", "-C", str(repo), "show", f"{HEAD}:{rel}"])
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", "replace")
    blob = git(repo, "rev-parse", f"{HEAD}:{rel}")
    return text, data, blob


def match_context(item: dict, files: dict[str, tuple[str, bytes, str]]) -> dict:
    source = item["source"]
    variants = [json.dumps(source, ensure_ascii=False), repr(source), '"' + source + '"', "'" + source + "'", "`" + source + "`"]
    variants = list(dict.fromkeys(variants))
    callers = []
    for rel, (text, data, blob) in files.items():
        hits: dict[int, str] = {}
        for literal in variants:
            offset = 0
            while True:
                at = text.find(literal, offset)
                if at < 0:
                    break
                hits.setdefault(at, "exact quoted source literal")
                offset = at + max(1, len(literal))
        offset = 0
        while True:
            at = text.find(item["sourceId"], offset)
            if at < 0:
                break
            hits.setdefault(at, "exact source ID reference")
            offset = at + len(item["sourceId"])
        for found in re.finditer(r">[ \t]*" + re.escape(source) + r"[ \t]*<", text):
            hits.setdefault(found.start(), "exact HTML text node")
        lines = text.splitlines()
        for at, kind in sorted(hits.items()):
            line = text.count("\n", 0, at) + 1
            excerpt = [{"line": n, "text": lines[n - 1]} for n in range(max(1, line - 3), min(len(lines), line + 3) + 1)]
            line_text = lines[line - 1] if line <= len(lines) else ""
            callers.append({"path": rel, "line": line, "lineText": line_text, "lineSha256": sha(line_text), "excerpt": excerpt, "excerptSha256": sha(canonical(excerpt)), "fileSha256": sha(data), "gitBlob": blob, "matchKind": kind})
    callers.sort(key=lambda row: (row["path"], row["line"], row["matchKind"]))
    core = {"sourceId":item["sourceId"], "source":source, "sourceSha256":item["sourceSha256"], "head":HEAD, "searchMethod":"exact quoted source literal, exact source ID, or exact HTML text-node search in tracked production code under romarr; tests, docs, catalogs, and workflows excluded", "productionFilesSearched":len(files), "exactMatchCount":len(callers), "callerless":not callers, "callers":callers}
    return {**core, "contextSha256":sha(canonical(core))}


def check_sums(root: Path) -> None:
    sums = root / "SHA256SUMS.txt"
    listed = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes()) != digest:
            fail("input checksum " + name)
        if name in listed:
            fail("duplicate input checksum " + name)
        listed[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != sums}
    if set(listed) != actual:
        fail("input checksum coverage")


def verify(repo: Path, input_dir: Path) -> dict:
    repo = repo.resolve()
    check_sums(input_dir)
    if git(repo, "rev-parse", "HEAD") != HEAD or git(repo, "rev-parse", "HEAD^{tree}") != TREE:
        fail("repository HEAD/tree pin")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all") or git(repo, "branch", "--show-current"):
        fail("repository must be clean and detached")

    manifest = read_json(input_dir / "manifest.json")
    if (manifest.get("head"), manifest.get("tree"), manifest.get("window"), manifest.get("branch"), manifest.get("candidateFree"), manifest.get("proposedTargetsIncluded"), manifest.get("reviewDecisionsIncluded")) != (HEAD, TREE, WINDOW, BRANCH, True, False, False):
        fail("candidate-free manifest identity")
    before = read_json(input_dir / "PR-attestation-before.json")
    after = read_json(input_dir / "PR-attestation-after-candidate-free.json")
    attested = ("state", "draft", "merged", "headRefName", "head", "tree", "branchRefOid", "pullRefOid", "baseRefName", "baseApiSha", "baseLiveRefOid", "bodySha256", "bodyBytes")
    if any(before.get(key) != after.get(key) for key in attested) or before.get("head") != HEAD or before.get("tree") != TREE or before.get("branchRefOid") != HEAD or before.get("pullRefOid") != HEAD:
        fail("before/after PR ref alignment")

    catalog_path = "romarr/ui-labels.json"
    catalog_raw = (repo / catalog_path).read_bytes()
    catalog = json.loads(catalog_raw)
    messages = catalog.get("messages", {})
    ids = list(messages)
    if len(ids) != 1836 or sha(catalog_raw) != manifest.get("catalogSha256") or git(repo, "rev-parse", f"{HEAD}:{catalog_path}") != manifest.get("catalogGitBlob"):
        fail("catalog hash or message count")
    key_order = sha("\n".join(ids) + "\n")
    if key_order != manifest.get("catalogKeyOrderSha256"):
        fail("catalog insertion order hash")

    registry_path = "romarr/ui-source-messages.json"
    snapshot_path = "romarr/ui-source-snapshot.json"
    registry_raw = (repo / registry_path).read_bytes()
    registry_rows = json.loads(registry_raw)["messages"]
    registry = {row["id"]:row for row in registry_rows}
    active_rank = {source_id: rank for rank, source_id in enumerate(sorted(registry), 1)}
    source_snapshot = {row["id"]:row["sourceHash"] for row in registry_rows}
    live_snapshot = read_json(repo / snapshot_path)
    if len(registry_rows) != len(registry) or any(live_snapshot.get(k) != v for k,v in source_snapshot.items()):
        fail("source registry/snapshot consistency")
    if sha(registry_raw) != manifest.get("sourceQueueSha256") or sha(canonical(source_snapshot)) != manifest.get("sourceSnapshotSha256") or sha("\n".join(sorted(registry)) + "\n") != manifest.get("sourceIdOrderSha256"):
        fail("source queue/snapshot/order hashes")
    if (input_dir / "source-queue.json").read_bytes() != registry_raw or read_json(input_dir / "source-snapshot.json") != live_snapshot:
        fail("pinned source queue/snapshot content")

    file_pins = read_json(input_dir / "source-file-pins.json")["files"]
    expected_paths = set(production_paths(repo)) | {catalog_path, registry_path, snapshot_path}
    if {row["path"] for row in file_pins} != expected_paths:
        fail("source file pin coverage")
    for row in file_pins:
        data = (repo / row["path"]).read_bytes()
        if len(data) != row["bytes"] or sha(data) != row["fileSha256"] or git(repo, "rev-parse", f"{HEAD}:{row['path']}") != row["gitBlob"]:
            fail("source file pin " + row["path"])
    pin_meta = read_json(input_dir / "catalog-file-pins.json")
    if pin_meta.get("catalogSha256") != sha(catalog_raw) or pin_meta.get("sourceQueueSha256") != sha(registry_raw) or pin_meta.get("sourceSnapshotSha256") != sha(canonical(source_snapshot)):
        fail("catalog-file-pins summary")

    inventory = read_jsonl(input_dir / "catalog-source-inventory.jsonl")
    if len(inventory) != len(ids):
        fail("full catalog source inventory count")
    for idx, row in enumerate(inventory):
        source_id = ids[idx]
        message = messages[source_id]
        if row["catalogZeroBasedIndex"] != idx or row["sourceId"] != source_id or row["source"] != message["source"] or row["sourceSha256"] != sha(message["source"]) or row["targetHashes"] != {locale:(sha(message["translations"][locale]) if isinstance(message.get("translations", {}).get(locale), str) else None) for locale in LOCALES}:
            fail("catalog inventory row " + str(idx))

    selection = read_json(input_dir / "selection.json")
    selected = read_jsonl(input_dir / "source-inventory-selection.jsonl")
    if (selection.get("positions"), selection.get("sourceCount"), selection.get("localeCount"), selection.get("cellCount"), len(selected)) != ([645, 664], 20, 12, 240, 20):
        fail("selection range/count")
    for idx, row in zip(range(645, 665), selected):
        source_id = ids[idx]
        message = messages[source_id]
        if row["position"] != idx or row["catalogZeroBasedIndex"] != idx or row["sourceId"] != source_id or row["source"] != message["source"] or row["sourceSha256"] != sha(message["source"]):
            fail("selected source order/hash at " + str(idx))

    files = {rel:file_tuple(repo, rel) for rel in production_paths(repo)}
    contexts = read_jsonl(input_dir / "source-contexts.jsonl")
    if len(contexts) != 20:
        fail("source context count")
    for selected_row, context in zip(selected, contexts):
        expected = match_context(selected_row, files)
        if context != expected:
            fail("exact caller context " + selected_row["sourceId"])
    context_map = {row["sourceId"]:row for row in contexts}

    cells = read_jsonl(input_dir / "current-target-cells.jsonl")
    if len(cells) != 240 or len({(row["sourceId"], row["locale"]) for row in cells}) != 240:
        fail("current target cell count/uniqueness")
    cell_map = {}
    for cell in cells:
        key = (cell["sourceId"], cell["locale"])
        if key in cell_map or cell["locale"] not in LOCALES:
            fail("cell key/locale")
        idx = cell["catalogZeroBasedIndex"]
        message = messages.get(cell["sourceId"])
        context = context_map.get(cell["sourceId"])
        target = message.get("translations", {}).get(cell["locale"]) if message else None
        if idx not in range(645, 665) or ids[idx] != cell["sourceId"] or not isinstance(target, str) or cell["source"] != message["source"] or cell["currentTarget"] != target:
            fail("cell source/target binding " + str(key))
        if cell["sourceSha256"] != sha(message["source"]) or cell["currentTargetSha256"] != sha(target) or cell["callerContextSha256"] != context["contextSha256"] or cell.get("containsCandidate") is not False:
            fail("cell hashes/context/candidate flag " + str(key))
        source_tokens = tokens(message["source"])
        target_tokens = tokens(target)
        if cell["sourcePlaceholderTokens"] != source_tokens["placeholders"] or cell["currentPlaceholderTokens"] != target_tokens["placeholders"] or cell["placeholderMultisetMatches"] != (collections.Counter(source_tokens["placeholders"]) == collections.Counter(target_tokens["placeholders"])):
            fail("cell placeholder audit " + str(key))
        if cell["sourceMarkupTags"] != source_tokens["markup"] or cell["currentMarkupTags"] != target_tokens["markup"] or cell["markupMatches"] != (collections.Counter(source_tokens["markup"]) == collections.Counter(target_tokens["markup"])):
            fail("cell markup audit " + str(key))
        source_numbers = collections.Counter(source_tokens["numbers"])
        target_numbers = collections.Counter(target_tokens["numbers"])
        extra = list((target_numbers - source_numbers).elements())
        numeric_presentation = bool(re.search(r"\bzero\b", message["source"], re.I) and not source_tokens["numbers"] and extra == ["0"])
        numeric_ok = not (source_numbers - target_numbers) and (not extra or numeric_presentation)
        missing_protected = [literal for literal in source_tokens["protectedLiterals"] if literal not in target]
        if cell["numericTokensPreserved"] != numeric_ok or cell["numericPresentationEquivalent"] != numeric_presentation or cell["sourceProtectedLiterals"] != source_tokens["protectedLiterals"] or cell["missingProtectedLiterals"] != missing_protected or cell["protectedLiteralsPreserved"] != (not missing_protected):
            fail("cell number/protected-token audit " + str(key))
        expected_refs = [{"path":r["path"], "line":r["line"], "lineSha256":r["lineSha256"], "excerptSha256":r["excerptSha256"], "fileSha256":r["fileSha256"], "gitBlob":r["gitBlob"], "matchKind":r["matchKind"]} for r in context["callers"]]
        if cell["callerRefs"] != expected_refs:
            fail("cell caller refs " + str(key))
        banned = {"proposedTarget", "selectedTarget", "finalTarget", "reviewDecision", "primaryDecision", "proposal"}
        if banned & set(cell):
            fail("candidate-free cell has a proposal/decision field")
        cell_map[key] = cell
    if any(manifest.get(key) != 0 for key in ("currentTargetPlaceholderMismatches", "currentTargetMarkupMismatches", "currentTargetNumericMismatches", "currentTargetProtectedLiteralMismatches", "currentTargetMissingCells")):
        fail("candidate-free token/missing-cell summary")

    selected_prior = read_jsonl(input_dir / "prior-selection-reattestation.jsonl")
    if len(selected_prior) != 260 or len({row["sourceId"] for row in selected_prior}) != 260:
        fail("prior selected source count")
    for row in selected_prior:
        idx = row["catalogZeroBasedIndex"]
        message = messages.get(row["sourceId"])
        if idx >= len(ids) or ids[idx] != row["sourceId"] or row["currentSourceSha256"] != sha(message["source"]) or row["priorSourceSha256"] != row["currentSourceSha256"]:
            fail("prior selected source reattestation " + row["sourceId"])
    holds = read_jsonl(input_dir / "prior-hold-reattestation.jsonl")
    if len(holds) != 724 or len({(row["sourceId"], row["locale"]) for row in holds}) != 724:
        fail("prior hold count")
    for row in holds:
        idx = row["catalogZeroBasedIndex"]
        message = messages.get(row["sourceId"])
        target = message.get("translations", {}).get(row["locale"]) if message else None
        basis = row.get("selectionPositionBasis", "")
        position_ok = (idx == row["position"]) if "catalog insertion index" in basis else active_rank.get(row["sourceId"]) == row["position"]
        if not isinstance(target, str) or idx >= len(ids) or ids[idx] != row["sourceId"] or row["sourceSha256"] != sha(message["source"]) or row["currentTargetSha256"] != sha(target) or row["priorTargetSha256"] != row["currentTargetSha256"] or not position_ok:
            fail("prior hold reattestation " + row["sourceId"] + "/" + row["locale"])
        if row["window"] == "W625-W644" and (row.get("callerless") is not True or any(key in row for key in ("source", "sourceText", "currentTarget", "target", "targetText", "proposedTarget"))):
            fail("W625 callerless hold is not hash-only")
    applied = read_jsonl(input_dir / "prior-applied-cell-reattestation.jsonl")
    if len(applied) != 76 or len({(row["sourceId"], row["locale"]) for row in applied}) != 76:
        fail("prior applied count")
    for row in applied:
        message = messages.get(row["sourceId"])
        target = message.get("translations", {}).get(row["locale"]) if message else None
        if not isinstance(target, str) or row["sourceSha256"] != sha(message["source"]) or row["currentTargetSha256"] != sha(target) or row["priorSelectedTargetSha256"] != row["currentTargetSha256"]:
            fail("prior applied cell reattestation " + row["sourceId"] + "/" + row["locale"])
    readbacks = [
        ("W565-W584", "w565w584-cell-hash-reattestation.jsonl"),
        ("W585-W604", "w585w604-cell-hash-reattestation.jsonl"),
        ("W605-W624", "w605w624-cell-hash-reattestation.jsonl"),
        ("W625-W644", "w625-application-cell-hash-reattestation.jsonl"),
    ]
    for label, filename in readbacks:
        rows = read_jsonl(input_dir / filename)
        if len(rows) != 240 or len({(row["sourceId"], row["locale"]) for row in rows}) != 240:
            fail(label + " readback count/uniqueness")
        for row in rows:
            message = messages.get(row["sourceId"])
            target = message.get("translations", {}).get(row["locale"]) if message else None
            if not isinstance(target, str) or row["currentTargetSha256"] != sha(target) or row["sourceSha256"] != sha(message["source"]):
                fail(label + " readback hash " + row["sourceId"] + "/" + row["locale"])
    app_rel = "docs/pr-evidence/pr70-localization-2026-11-05/window-625-644-root-review"
    plan_path = input_dir / "prior-w625-application-plan.json"
    final_path = input_dir / "prior-w625-final-head-verification.json"
    readback_path = input_dir / "prior-w625-application-readback.jsonl"
    plan_raw = plan_path.read_bytes()
    final_raw = final_path.read_bytes()
    readback_raw = readback_path.read_bytes()
    tracked_plan = subprocess.check_output(["git", "-C", str(repo), "show", f"{HEAD}:{app_rel}/root-application/root-application-plan.json"])
    tracked_final = subprocess.check_output(["git", "-C", str(repo), "show", f"{HEAD}:{app_rel}/root-application/final-head-verification.json"])
    prior_plan = json.loads(plan_raw)
    prior_final = json.loads(final_raw)
    prior_readback = [json.loads(line) for line in readback_raw.decode("utf-8").splitlines() if line.strip()]
    prior_plan_changes = {(row["sourceId"], row["locale"]):row for row in prior_plan.get("changes", [])}
    if plan_raw != tracked_plan or final_raw != tracked_final or len(prior_plan_changes) != 3:
        fail("W625 application plan/final-verifier must match committed evidence")
    if (prior_plan.get("sourcePin"), prior_plan.get("window"), prior_plan.get("candidateCells"), prior_final.get("result"), prior_final.get("head"), prior_final.get("tree"), prior_final.get("observedChangedCells"), prior_final.get("callerlessHoldsTextFree")) != ({"head":"5860fce5d546a772b1df995f8f6321c083ed7d5d", "tree":"561835895972a62e9d3b1f2bfe9bcba01187eb98"}, "W625-W644", 240, "PASS", "86f6161f3069bb3113f8f7a8a763193f15c4e2bc", "29b85a61d3ef20b73ec15c5aa08c5a23788d32f8", 3, True):
        fail("W625 application plan/final-verifier identity")
    if sha(readback_raw) != prior_final.get("readbackSha256") or len(prior_readback) != 240 or len({(row["sourceId"], row["locale"]) for row in prior_readback}) != 240:
        fail("W625 prior application readback hash/count")
    w625_hash_reattest = read_jsonl(input_dir / "w625-application-cell-hash-reattestation.jsonl")
    w625_hold_keys = set()
    prior_w625_holds = {(row["sourceId"], row["locale"]):row for row in holds if row["window"] == "W625-W644"}
    prior_w625_applied = {(row["sourceId"], row["locale"]):row for row in applied if row["priorWindow"] == "W625-W644"}
    for row in prior_readback:
        key = (row["sourceId"], row["locale"])
        message = messages.get(row["sourceId"])
        current_target = message.get("translations", {}).get(row["locale"]) if message else None
        audit = next((item for item in w625_hash_reattest if (item["sourceId"], item["locale"]) == key), None)
        if audit is None or not isinstance(current_target, str) or row["position"] not in range(625, 645) or ids[row["position"]] != row["sourceId"] or row["sourceSha256"] != sha(message["source"]) or row["observedAfterSha256"] != sha(current_target) or audit["currentTargetSha256"] != sha(current_target) or audit["callerContextSha256"] != row["callerContextSha256"]:
            fail("W625 prior full-readback cell binding " + row["sourceId"] + "/" + row["locale"])
        change = prior_plan_changes.get(key)
        if bool(row["changed"]) != bool(change) or (change is not None and (change["sourceSha256"] != row["sourceSha256"] or change["currentTargetSha256"] != row["beforeTargetSha256"] or change["finalTargetSha256"] != row["observedAfterSha256"])):
            fail("W625 prior applied-cell binding " + row["sourceId"] + "/" + row["locale"])
        if row["rootDisposition"] == "hold-callerless-hash-only":
            w625_hold_keys.add(key)
            if any(name in row for name in ("source", "beforeTarget", "afterTarget")):
                fail("W625 prior callerless hold readback contains text")
            hold_reattestation = prior_w625_holds.get(key)
            if hold_reattestation is None or hold_reattestation.get("callerless") is not True or hold_reattestation.get("currentTargetSha256") != row["observedAfterSha256"] or hold_reattestation.get("callerContextSha256") != row["callerContextSha256"] or hold_reattestation.get("priorHoldEvidenceSha256") != sha(canonical(row)):
                fail("W625 callerless hold reattestation is not bound to full readback")
        if change is not None:
            applied_reattestation = prior_w625_applied.get(key)
            if applied_reattestation is None or applied_reattestation.get("currentTargetSha256") != row["observedAfterSha256"] or applied_reattestation.get("priorAppliedEvidenceSha256") != sha(canonical(change)):
                fail("W625 applied-cell reattestation is not bound to plan")
    if len(w625_hold_keys) != 60:
        fail("W625 prior callerless hold readback count")
    app_index = subprocess.check_output(["git", "-C", str(repo), "show", f"{HEAD}:{app_rel}/SHA256SUMS.txt"], text=True)
    tracked_app = set(git(repo, "ls-tree", "-r", "--name-only", HEAD, "--", app_rel).splitlines())
    missing_index_count = sum(1 for line in app_index.splitlines() if line.strip() and (app_rel + "/" + line.split("  ", 1)[1].removeprefix("./")) not in tracked_app)
    continuity = read_json(input_dir / "continuity-reattestation.json")
    if (continuity.get("result"), continuity.get("priorSelectedSourceCount"), continuity.get("priorHoldCellCount"), continuity.get("priorAppliedCellCount"), continuity.get("priorW625ReadbackRows"), continuity.get("priorW625AppliedChanges"), continuity.get("priorW625CallerlessHolds")) != ("PASS", 260, 724, 76, 240, 3, 60):
        fail("continuity summary")
    if continuity.get("priorApplicationEvidenceChecksumsVerified") is not False or continuity.get("priorTrackedApplicationEvidenceFilesMatched") is not True or continuity.get("priorW625FullReadbackSha256MatchedCommittedFinalVerifier") is not True or continuity.get("priorApplicationEvidenceIndexMissingFromPRTreeCount") != missing_index_count or continuity.get("priorW625ReadbackSha256") != sha(readback_raw):
        fail("W625 application evidence scope/limitation record")
    if manifest.get("priorW625ApplicationEvidenceChecksumsVerified") is not False or manifest.get("priorW625ApplicationEvidenceIndexMissingFromPRTreeCount") != missing_index_count or manifest.get("priorW625FullReadbackSha256") != sha(readback_raw):
        fail("manifest W625 application evidence scope/limitation record")
    return {"result":"PASS", "head":HEAD, "tree":TREE, "sources":20, "cells":240, "callerlessSources":sum(row["callerless"] for row in contexts), "callerlessCells":sum(row["callerless"] for row in contexts) * 12, "directCallerRefs":sum(row["exactMatchCount"] for row in contexts), "priorSelections":len(selected_prior), "priorHolds":len(holds), "priorAppliedCells":len(applied), "currentTargetTokenMismatches":read_json(input_dir / "current-target-token-mismatches.json"), "sourceContextsRecomputed":True, "candidateFree":True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    default_input = Path(__file__).resolve().parent
    if not (default_input / "manifest.json").is_file():
        default_input = default_input / "candidate-free" / "input"
    parser.add_argument("--input", type=Path, default=default_input)
    args = parser.parse_args()
    print(json.dumps(verify(args.repo, args.input.resolve()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
