#!/usr/bin/env python3
"""Extract a sealed, candidate-free W645-W664 ROMarrNG review input."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HEAD = "9f8832f67195323955172dd4c3c40e29cbabb5da"
TREE = "d6066baa3d03d3b4c6034e5af061fc4bc278b0f9"
BRANCH = "task/localization-translation-review-20261030"
PREV_HEAD = "5860fce5d546a772b1df995f8f6321c083ed7d5d"
PREV_TREE = "561835895972a62e9d3b1f2bfe9bcba01187eb98"
PREV_PRODUCT = "86f6161f3069bb3113f8f7a8a763193f15c4e2bc"
PREV_PRODUCT_TREE = "29b85a61d3ef20b73ec15c5aa08c5a23788d32f8"
WINDOW = "W645-W664"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
TAG = re.compile(r"<[^>]+>")
NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
PROTECTED = [
    "Gaseous", "Retrom", "SeerrNG", "ROMarrNG", "ROMarr", "ES-DE",
    "No-Intro", "Redump", "DAT", "IGDB", "ISO9660", "PLAYSTATION",
    "PlayStation", "PS2", "ROMs", "ROM", "PC", "API", "ROMARR_API_KEY",
    "Linksnappy", "Moonlight", "PIN", "NPSSO", "NZBHydra2", "Newznab",
    "/torznab/api", "NZBVortex", "HTTPS", "NZB", "Preferences",
]
PREV_PACKET = Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w625-644-20261105/candidate-free")
PREV_TASK = PREV_PACKET.parent
PREV_INPUT = PREV_PACKET / "candidate-free" / "input"
PREV_ROOT = PREV_TASK / "root-application"
APP_REL = "docs/pr-evidence/pr70-localization-2026-11-05/window-625-644-root-review"


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


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def verify_sums(root: Path, filename: str = "SHA256SUMS.txt") -> dict[str, str]:
    sums_path = root / filename
    listed: dict[str, str] = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes()) != digest:
            raise SystemExit(f"FAIL checksum mismatch: {name}")
        if name in listed:
            raise SystemExit(f"FAIL duplicate checksum entry: {name}")
        listed[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != sums_path}
    if set(listed) != actual:
        raise SystemExit(f"FAIL checksum coverage mismatch at {root}")
    return listed


def attestation(repo: Path) -> dict:
    pr = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/ROMarrNG/pulls/70"], cwd=repo, text=True))
    raw = git(repo, "ls-remote", "origin", f"refs/heads/{BRANCH}", "refs/pull/70/head", "refs/heads/main")
    refs = {line.split("\t")[1]: line.split("\t")[0] for line in raw.splitlines() if line.strip()}
    body = pr.get("body") or ""
    result = {
        "attestedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repository": "snapetech-org/ROMarrNG",
        "pullRequest": 70,
        "pullRequestUrl": pr["html_url"],
        "state": pr["state"].upper(),
        "draft": bool(pr["draft"]),
        "merged": bool(pr["merged"]),
        "headRefName": pr["head"]["ref"],
        "head": pr["head"]["sha"],
        "tree": git(repo, "rev-parse", f"{HEAD}^{{tree}}"),
        "branchRefOid": refs.get(f"refs/heads/{BRANCH}"),
        "pullRefOid": refs.get("refs/pull/70/head"),
        "baseRefName": pr["base"]["ref"],
        "baseApiSha": pr["base"]["sha"],
        "baseLiveRefOid": refs.get("refs/heads/main"),
        "baseApiRefMismatch": pr["base"]["sha"] != refs.get("refs/heads/main"),
        "bodySha256": sha(body),
        "bodyBytes": len(body.encode("utf-8")),
        "checksRerun": False,
    }
    expected = ("OPEN", True, False, BRANCH, HEAD, TREE, HEAD, HEAD, "main")
    actual = (result["state"], result["draft"], result["merged"], result["headRefName"], result["head"], result["tree"], result["branchRefOid"], result["pullRefOid"], result["baseRefName"])
    if actual != expected:
        raise SystemExit("FAIL PR API / branch / pull ref alignment: " + repr(result))
    if git(repo, "rev-parse", "HEAD") != HEAD or git(repo, "rev-parse", "HEAD^{tree}") != TREE:
        raise SystemExit("FAIL exact source HEAD/tree")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all") or git(repo, "branch", "--show-current"):
        raise SystemExit("FAIL source worktree is dirty or not detached")
    return result


def protected(source: str) -> list[str]:
    found = []
    for literal in PROTECTED:
        if literal.startswith("/"):
            matched = literal in source
        else:
            matched = bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(literal) + r"(?![A-Za-z0-9])", source))
        if matched:
            found.append(literal)
    return sorted(set(found))


def tokens(text: str) -> dict:
    return {"placeholders": PLACEHOLDER.findall(text), "markup": TAG.findall(text), "numbers": NUMBER.findall(text), "protectedLiterals": protected(text)}


def production_paths(repo: Path, commit: str) -> list[str]:
    raw = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", commit, "--", "romarr"], text=True).splitlines()
    allowed = {".py", ".js", ".html", ".jinja", ".jinja2", ".css", ".ts", ".tsx"}
    result = []
    for rel in raw:
        path = Path(rel)
        parts = rel.lower().split("/")
        if path.suffix.lower() not in allowed or any(x in parts for x in ("test", "tests", "__pycache__")) or path.name.startswith("test_") or path.name.endswith("_test.py"):
            continue
        result.append(rel)
    return result


def file_tuple(repo: Path, rel: str, commit: str) -> tuple[str, bytes, str]:
    data = subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{rel}"])
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", "replace")
    blob = subprocess.check_output(["git", "-C", str(repo), "rev-parse", f"{commit}:{rel}"], text=True).strip()
    return text, data, blob


def match_context(item: dict, files: dict[str, tuple[str, bytes, str]], commit: str) -> dict:
    source = item["source"]
    variants = list(dict.fromkeys([json.dumps(source, ensure_ascii=False), repr(source), '"' + source + '"', "'" + source + "'", "`" + source + "`"]))
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
    core = {
        "sourceId": item["sourceId"], "source": source, "sourceSha256": item["sourceSha256"],
        "head": commit,
        "searchMethod": "exact quoted source literal, exact source ID, or exact HTML text-node search in tracked production code under romarr; tests, docs, catalogs, and workflows excluded",
        "productionFilesSearched": len(files), "exactMatchCount": len(callers), "callerless": not callers, "callers": callers,
    }
    return {**core, "contextSha256": sha(canonical(core))}


def current_attested_target(messages: dict, ids: list[str], source_id: str, locale: str) -> tuple[dict, str]:
    message = messages[source_id]
    target = message.get("translations", {}).get(locale)
    if not isinstance(target, str) or not target:
        raise SystemExit(f"FAIL missing target {source_id}/{locale}")
    return message, sha(target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = Path(__file__).resolve().parent
    input_dir = out / "candidate-free" / "input"
    if input_dir.exists() and any(input_dir.iterdir()):
        raise SystemExit("FAIL input directory is not empty")

    api_before = attestation(repo)
    verify_sums(PREV_PACKET)
    verify_sums(PREV_INPUT)
    prev_manifest = read_json(PREV_INPUT / "manifest.json")
    if (prev_manifest.get("head"), prev_manifest.get("tree"), prev_manifest.get("window")) != (PREV_HEAD, PREV_TREE, "W625-W644"):
        raise SystemExit("FAIL previous candidate-free packet pin")
    if (prev_manifest.get("priorSelectedSourceCount"), prev_manifest.get("priorHoldCellCount"), prev_manifest.get("priorAppliedSelectedCellCount")) != (240, 664, 73):
        raise SystemExit("FAIL previous selection/hold/application counts")

    app_dir = repo / APP_REL
    # The committed W625 evidence index references bulky stage JSONL files that
    # were retained in task scratch but not committed into the PR tree. Verify
    # every indexed file that is present and record missing indexed paths; the
    # full application readback is independently pinned by final-head-verification.json.
    indexed = {}
    missing_indexed = []
    for line in (app_dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        rel = name.removeprefix("./")
        path = app_dir / rel
        if path.is_file():
            if sha(path.read_bytes()) != digest:
                raise SystemExit(f"FAIL committed W625 evidence hash mismatch: {rel}")
            indexed[rel] = digest
        else:
            missing_indexed.append(rel)
    tracked_app_files = {line for line in git(repo, "ls-tree", "-r", "--name-only", HEAD, "--", APP_REL).splitlines() if Path(line).name != "SHA256SUMS.txt"}
    for rel in tracked_app_files:
        rel_under_app = rel.removeprefix(APP_REL + "/")
        if rel_under_app not in indexed:
            raise SystemExit(f"FAIL committed W625 evidence file absent from index: {rel_under_app}")
    if not missing_indexed:
        raise SystemExit("FAIL expected PR evidence index to identify retained but uncommitted stage outputs")
    root = app_dir / "root-application"
    plan = read_json(root / "root-application-plan.json")
    final_verification = read_json(root / "final-head-verification.json")
    if plan.get("sourcePin") != {"head": PREV_HEAD, "tree": PREV_TREE}:
        raise SystemExit("FAIL W625 application source pin")
    if (plan.get("window"), plan.get("candidateCells"), len(plan.get("changes", []))) != ("W625-W644", 240, 3):
        raise SystemExit("FAIL W625 application plan shape")
    if (final_verification.get("result"), final_verification.get("head"), final_verification.get("tree"), final_verification.get("observedChangedCells")) != ("PASS", PREV_PRODUCT, PREV_PRODUCT_TREE, 3):
        raise SystemExit("FAIL W625 application readback verifier record")
    if git(repo, "rev-parse", f"{PREV_PRODUCT}^") != PREV_HEAD or git(repo, "rev-parse", f"{PREV_PRODUCT}^{{tree}}") != PREV_PRODUCT_TREE:
        raise SystemExit("FAIL W625 application commit ancestry/tree")
    if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", PREV_PRODUCT, HEAD], check=False).returncode:
        raise SystemExit("FAIL W625 application commit is not in exact PR head history")

    prior_selection = read_jsonl(PREV_INPUT / "prior-selection-reattestation.jsonl")
    w625_selected = read_jsonl(PREV_INPUT / "source-inventory-selection.jsonl")
    prior_holds = read_jsonl(PREV_INPUT / "prior-hold-reattestation.jsonl")
    prior_applied = read_jsonl(PREV_INPUT / "prior-applied-cell-reattestation.jsonl")
    prior_baseline = read_jsonl(PREV_INPUT / "current-target-cells.jsonl")
    w625_readback_path = PREV_ROOT / "final-head-readback.jsonl"
    w625_readback_raw = w625_readback_path.read_bytes()
    w625_readback = [json.loads(line) for line in w625_readback_raw.decode("utf-8").splitlines() if line.strip()]
    if sha(w625_readback_raw) != final_verification.get("readbackSha256"):
        raise SystemExit("FAIL external W625 full readback does not match sealed readback hash")
    if (len(prior_selection), len(w625_selected), len(prior_holds), len(prior_applied), len(prior_baseline), len(w625_readback)) != (240, 20, 664, 73, 240, 240):
        raise SystemExit("FAIL prior lineage or W625 full-window counts")

    catalog_path = "romarr/ui-labels.json"
    catalog_raw = (repo / catalog_path).read_bytes()
    catalog = json.loads(catalog_raw)
    messages = catalog["messages"]
    ids = list(messages)
    if len(messages) != 1836:
        raise SystemExit("FAIL catalog key count")
    registry_path = "romarr/ui-source-messages.json"
    snapshot_path = "romarr/ui-source-snapshot.json"
    registry_raw = (repo / registry_path).read_bytes()
    registry_rows = read_json(repo / registry_path)["messages"]
    registry = {row["id"]: row for row in registry_rows}
    active_rank = {source_id: rank for rank, source_id in enumerate(sorted(registry), 1)}
    source_snapshot = {row["id"]: row["sourceHash"] for row in registry_rows}
    live_snapshot = read_json(repo / snapshot_path)
    if len(registry_rows) != len(registry) or any(live_snapshot.get(k) != v for k, v in source_snapshot.items()):
        raise SystemExit("FAIL registry/snapshot consistency")
    source_snapshot_sha = sha(canonical(source_snapshot))
    source_queue_sha = sha(registry_raw)
    id_order_sha = sha("\n".join(sorted(registry)) + "\n")
    catalog_order_sha = sha("\n".join(ids) + "\n")

    selection_rows = []
    for row in prior_selection:
        source_id = row["sourceId"]
        idx = row["catalogZeroBasedIndex"]
        message = messages.get(source_id)
        if message is None or idx >= len(ids) or ids[idx] != source_id or sha(message["source"]) != row["priorSourceSha256"] or message.get("sourceHash") != sha(message["source"]):
            raise SystemExit(f"FAIL previously selected source drift: {source_id}")
        selection_rows.append({"priorWindow": row["priorWindow"], "position": row.get("position", idx), "catalogZeroBasedIndex": idx, "sourceId": source_id, "priorSourceSha256": row["priorSourceSha256"], "currentSourceSha256": sha(message["source"]), "selectionPositionMatches": True, "sourceHashMatches": True, "registryMembershipAndHashMatch": source_id in registry, "priorSelectionEvidenceSha256": row.get("priorSelectionEvidenceSha256", sha(canonical(row))), "reattestedAtHead": HEAD})
    for row in w625_selected:
        source_id = row["sourceId"]
        idx = row["catalogZeroBasedIndex"]
        message = messages[source_id]
        if idx not in range(625, 645) or ids[idx] != source_id or sha(message["source"]) != row["sourceSha256"]:
            raise SystemExit(f"FAIL W625 selected source drift: {source_id}")
        selection_rows.append({"priorWindow": "W625-W644", "position": idx, "catalogZeroBasedIndex": idx, "sourceId": source_id, "priorSourceSha256": row["sourceSha256"], "currentSourceSha256": sha(message["source"]), "selectionPositionMatches": True, "sourceHashMatches": True, "registryMembershipAndHashMatch": source_id in registry, "priorSelectionEvidenceSha256": sha(canonical(row)), "reattestedAtHead": HEAD})
    if len(selection_rows) != 260 or len({row["sourceId"] for row in selection_rows}) != 260:
        raise SystemExit("FAIL selection lineage count/uniqueness")

    hold_rows = []
    for row in prior_holds:
        source_id, locale = row["sourceId"], row["locale"]
        idx = ids.index(source_id)
        position_basis = row.get("selectionPositionBasis", "")
        position_ok = idx == row["position"] if "catalog insertion index" in position_basis else active_rank.get(source_id) == row["position"]
        message, current_hash = current_attested_target(messages, ids, source_id, locale)
        if sha(message["source"]) != row["sourceSha256"] or current_hash != row["priorTargetSha256"] or not position_ok:
            raise SystemExit(f"FAIL prior held cell changed: {source_id}/{locale}")
        hold_rows.append({"window": row["window"], "position": row["position"], "selectionPositionBasis": position_basis, "catalogZeroBasedIndex": idx, "sourceId": source_id, "sourceSha256": sha(message["source"]), "locale": locale, "priorTargetSha256": row["priorTargetSha256"], "currentTargetSha256": current_hash, "selectionPositionMatches": True, "targetUnchanged": True, "priorHoldEvidenceSha256": row.get("priorHoldEvidenceSha256", sha(canonical(row))), "reattestedAtHead": HEAD})

    baseline_map = {(row["sourceId"], row["locale"]): row for row in prior_baseline}
    w625_contexts = {row["sourceId"]: row for row in read_jsonl(PREV_INPUT / "source-contexts.jsonl")}
    w625_hold_ids = set()
    for row in w625_readback:
        if row.get("rootDisposition") != "hold-callerless-hash-only":
            continue
        source_id, locale, idx = row["sourceId"], row["locale"], row["position"]
        baseline = baseline_map[(source_id, locale)]
        context = w625_contexts[source_id]
        message, current_hash = current_attested_target(messages, ids, source_id, locale)
        if idx not in range(625, 645) or ids[idx] != source_id or not context["callerless"] or row.get("callerContextSha256") != context["contextSha256"]:
            raise SystemExit(f"FAIL W625 callerless hold context/position: {source_id}/{locale}")
        if row.get("sourceSha256") != sha(message["source"]) or row.get("beforeTargetSha256") != baseline["currentTargetSha256"] or current_hash != row["observedAfterSha256"]:
            raise SystemExit(f"FAIL W625 callerless hold hash changed: {source_id}/{locale}")
        if any(key in row for key in ("source", "sourceText", "beforeTarget", "afterTarget", "currentTarget", "target", "targetText", "proposedTarget", "selectedTarget", "finalTarget")):
            raise SystemExit("FAIL previous callerless hold contains text")
        if (source_id, locale) in w625_hold_ids:
            raise SystemExit("FAIL duplicate W625 callerless hold")
        w625_hold_ids.add((source_id, locale))
        hold_rows.append({"window": "W625-W644", "position": idx, "selectionPositionBasis": "catalog insertion index (zero-based)", "catalogZeroBasedIndex": idx, "sourceId": source_id, "sourceSha256": sha(message["source"]), "locale": locale, "priorTargetSha256": current_hash, "currentTargetSha256": current_hash, "selectionPositionMatches": True, "targetUnchanged": True, "callerless": True, "callerContextSha256": context["contextSha256"], "holdReasonSha256": sha("callerless hash-only hold"), "priorHoldEvidenceSha256": sha(canonical(row)), "reattestedAtHead": HEAD})
    if len(w625_hold_ids) != 60 or len(hold_rows) != 724 or len({(row["sourceId"], row["locale"]) for row in hold_rows}) != 724:
        raise SystemExit("FAIL prior hold lineage count/uniqueness")

    applied_rows = []
    for row in prior_applied:
        source_id, locale = row["sourceId"], row["locale"]
        message, current_hash = current_attested_target(messages, ids, source_id, locale)
        if sha(message["source"]) != row["sourceSha256"] or current_hash != row["priorSelectedTargetSha256"] or current_hash != row["currentTargetSha256"]:
            raise SystemExit(f"FAIL prior applied cell changed: {source_id}/{locale}")
        applied_rows.append({"priorWindow": row["priorWindow"], "catalogZeroBasedIndex": ids.index(source_id), "sourceId": source_id, "sourceSha256": sha(message["source"]), "locale": locale, "priorSelectedTargetSha256": current_hash, "currentTargetSha256": current_hash, "targetUnchanged": True, "applicationCommit": row["applicationCommit"], "priorAppliedEvidenceSha256": row.get("priorAppliedEvidenceSha256", sha(canonical(row))), "reattestedAtHead": HEAD})
    w625_changes = {(row["sourceId"], row["locale"]): row for row in plan["changes"]}
    if len(w625_changes) != 3:
        raise SystemExit("FAIL W625 change key uniqueness")
    for key, row in w625_changes.items():
        source_id, locale = key
        idx = row["position"]
        message, current_hash = current_attested_target(messages, ids, source_id, locale)
        baseline = baseline_map[key]
        if idx not in range(625, 645) or ids[idx] != source_id or row["sourceSha256"] != sha(message["source"]) or row["currentTargetSha256"] != baseline["currentTargetSha256"] or row["finalTargetSha256"] != current_hash:
            raise SystemExit(f"FAIL W625 applied cell/hash lineage: {source_id}/{locale}")
        applied_rows.append({"priorWindow": "W625-W644", "catalogZeroBasedIndex": idx, "sourceId": source_id, "sourceSha256": sha(message["source"]), "locale": locale, "priorSelectedTargetSha256": current_hash, "currentTargetSha256": current_hash, "targetUnchanged": True, "applicationCommit": PREV_PRODUCT, "priorAppliedEvidenceSha256": sha(canonical(row)), "beforeTargetSha256": row["currentTargetSha256"], "reattestedAtHead": HEAD})
    if len(applied_rows) != 76 or len({(row["sourceId"], row["locale"]) for row in applied_rows}) != 76:
        raise SystemExit("FAIL applied-cell lineage count/uniqueness")

    def reattest_readback(rows: list[dict], label: str) -> list[dict]:
        if len(rows) != 240:
            raise SystemExit(f"FAIL {label} full-window row count")
        out_rows = []
        for row in rows:
            source_id, locale = row["sourceId"], row["locale"]
            idx = row.get("position", row.get("catalogZeroBasedIndex"))
            message, current_hash = current_attested_target(messages, ids, source_id, locale)
            recorded_hash = row.get("currentTargetSha256", row.get("afterTargetSha256", row.get("observedAfterSha256")))
            recorded_source_hash = row.get("sourceSha256")
            if recorded_source_hash != sha(message["source"]) or recorded_hash != current_hash:
                raise SystemExit(f"FAIL {label} current hash mismatch: {source_id}/{locale}")
            if idx is not None and not (0 <= idx < len(ids) and ids[idx] == source_id):
                raise SystemExit(f"FAIL {label} position mismatch: {source_id}/{locale}")
            out_rows.append({"priorWindow": label, "catalogZeroBasedIndex": ids.index(source_id), "sourceId": source_id, "sourceSha256": sha(message["source"]), "locale": locale, "currentTargetSha256": current_hash, "matchesPriorReadback": True, "reattestedAtHead": HEAD})
        if len({(row["sourceId"], row["locale"]) for row in out_rows}) != 240:
            raise SystemExit(f"FAIL {label} duplicate cell rows")
        return out_rows

    readback_sources = [
        ("W565-W584", read_jsonl(PREV_INPUT / "prior-w565-window-cell-hash-reattestation.jsonl")),
        ("W585-W604", read_jsonl(PREV_INPUT / "prior-w585-window-cell-hash-reattestation.jsonl")),
        ("W605-W624", read_jsonl(PREV_INPUT / "prior-w605-window-cell-hash-reattestation.jsonl")),
    ]
    recent_readbacks = {label: reattest_readback(rows, label) for label, rows in readback_sources}
    w625_reasserted = []
    for row in w625_readback:
        source_id, locale, idx = row["sourceId"], row["locale"], row["position"]
        key = (source_id, locale)
        baseline = baseline_map[key]
        message, current_hash = current_attested_target(messages, ids, source_id, locale)
        context = w625_contexts[source_id]
        if idx not in range(625, 645) or ids[idx] != source_id or row["sourceSha256"] != sha(message["source"]) or row["beforeTargetSha256"] != baseline["currentTargetSha256"] or row["observedAfterSha256"] != current_hash or row["callerContextSha256"] != context["contextSha256"]:
            raise SystemExit(f"FAIL W625 240-cell readback binding: {source_id}/{locale}")
        if bool(row["changed"]) != (key in w625_changes) or (key in w625_hold_ids and row["changed"]):
            raise SystemExit(f"FAIL W625 applied/held readback status: {source_id}/{locale}")
        w625_reasserted.append({"priorWindow": "W625-W644", "catalogZeroBasedIndex": idx, "sourceId": source_id, "sourceSha256": sha(message["source"]), "locale": locale, "beforeTargetSha256": row["beforeTargetSha256"], "currentTargetSha256": current_hash, "applicationChanged": bool(row["changed"]), "callerlessHeld": key in w625_hold_ids, "applicationCommit": PREV_PRODUCT, "callerContextSha256": context["contextSha256"], "matchesPriorApplicationReadback": True, "reattestedAtHead": HEAD})
    if (len(w625_reasserted), sum(row["applicationChanged"] for row in w625_reasserted), sum(row["callerlessHeld"] for row in w625_reasserted)) != (240, 3, 60):
        raise SystemExit("FAIL W625 240-cell readback totals")

    source_queue = read_json(repo / registry_path)
    raw_snapshot = read_json(repo / snapshot_path)
    production_files = {}
    source_paths = production_paths(repo, HEAD)
    for rel in source_paths:
        production_files[rel] = file_tuple(repo, rel, HEAD)
    source_pin_rows = []
    for rel in sorted(set(source_paths) | {catalog_path, registry_path, snapshot_path}):
        data = (repo / rel).read_bytes()
        source_pin_rows.append({"path": rel, "fileSha256": sha(data), "gitBlob": git(repo, "rev-parse", f"{HEAD}:{rel}"), "bytes": len(data)})
    old_source_pins = read_json(PREV_INPUT / "source-file-pins.json").get("files", [])
    old_pin_map = {row["path"]: row for row in old_source_pins}
    for row in source_pin_rows:
        if row["path"] in old_pin_map and row["path"] != catalog_path and (row["fileSha256"] != old_pin_map[row["path"]]["fileSha256"] or row["gitBlob"] != old_pin_map[row["path"]]["gitBlob"]):
            raise SystemExit(f"FAIL production source/caller drift since W625 extraction: {row['path']}")

    selected = []
    for idx in range(645, 665):
        source_id = ids[idx]
        message = messages[source_id]
        source_hash = sha(message["source"])
        if message.get("sourceHash") != source_hash:
            raise SystemExit(f"FAIL sourceHash mismatch at catalog index {idx}: {source_id}")
        selected.append({"position": idx, "catalogZeroBasedIndex": idx, "catalogOneBasedPosition": idx + 1, "sourceId": source_id, "source": message["source"], "sourceSha256": source_hash, "activeSourceRegistry": source_id in registry, "activeSourceRank": active_rank.get(source_id), "registryLocations": registry.get(source_id, {}).get("locations", [])})
    if len(selected) != 20 or len({row["sourceId"] for row in selected}) != 20 or {row["sourceId"] for row in selected} & {row["sourceId"] for row in selection_rows}:
        raise SystemExit("FAIL W645 selection count/overlap")
    contexts = [match_context(row, production_files, HEAD) for row in selected]
    context_by_id = {row["sourceId"]: row for row in contexts}

    selection_boundary = []
    for idx, role in ((644, "catalog-before-selected-start"), (645, "selected-start"), (664, "selected-end"), (665, "catalog-after-selected-end")):
        source_id = ids[idx]
        message = messages[source_id]
        selection_boundary.append({"position": idx, "catalogZeroBasedIndex": idx, "sourceId": source_id, "source": message["source"], "sourceSha256": sha(message["source"]), "role": role})

    cells = []
    mismatch = collections.Counter()
    for item in selected:
        source_id = item["sourceId"]
        message = messages[source_id]
        source_text = message["source"]
        source_tokens = tokens(source_text)
        context = context_by_id[source_id]
        caller_refs = [{"path": row["path"], "line": row["line"], "lineSha256": row["lineSha256"], "excerptSha256": row["excerptSha256"], "fileSha256": row["fileSha256"], "gitBlob": row["gitBlob"], "matchKind": row["matchKind"]} for row in context["callers"]]
        for locale in LOCALES:
            target = message.get("translations", {}).get(locale)
            if not isinstance(target, str) or not target:
                mismatch["missingTarget"] += 1
                target = ""
            target_tokens = tokens(target)
            placeholder_ok = collections.Counter(source_tokens["placeholders"]) == collections.Counter(target_tokens["placeholders"])
            markup_ok = collections.Counter(source_tokens["markup"]) == collections.Counter(target_tokens["markup"])
            source_numbers = collections.Counter(source_tokens["numbers"])
            target_numbers = collections.Counter(target_tokens["numbers"])
            extra_numbers = list((target_numbers - source_numbers).elements())
            numeric_presentation = bool(re.search(r"\bzero\b", source_text, re.I) and not source_tokens["numbers"] and extra_numbers == ["0"])
            numeric_ok = not (source_numbers - target_numbers) and (not extra_numbers or numeric_presentation)
            missing_protected = [literal for literal in source_tokens["protectedLiterals"] if literal not in target]
            mismatch["placeholder"] += not placeholder_ok
            mismatch["markup"] += not markup_ok
            mismatch["numeric"] += not numeric_ok
            mismatch["numericPresentationDifferences"] += numeric_presentation
            mismatch["protectedLiteral"] += bool(missing_protected)
            cells.append({
                "position": item["position"], "catalogZeroBasedIndex": item["catalogZeroBasedIndex"], "catalogOneBasedPosition": item["catalogOneBasedPosition"],
                "sourceId": source_id, "source": source_text, "sourceSha256": item["sourceSha256"], "locale": locale,
                "currentTarget": target, "currentTargetSha256": sha(target),
                "catalogTranslationHash": message.get("translationHashes", {}).get(locale), "translationStatus": message.get("translationStatus", {}).get(locale),
                "callerContextSha256": context["contextSha256"], "callerRefs": caller_refs,
                "sourcePlaceholderTokens": source_tokens["placeholders"], "currentPlaceholderTokens": target_tokens["placeholders"], "placeholderMultisetMatches": placeholder_ok,
                "sourceMarkupTags": source_tokens["markup"], "currentMarkupTags": target_tokens["markup"], "markupMatches": markup_ok,
                "sourceNumericTokens": source_tokens["numbers"], "currentNumericTokens": target_tokens["numbers"], "numericTokensPreserved": numeric_ok,
                "numericPresentationEquivalent": numeric_presentation,
                "sourceProtectedLiterals": source_tokens["protectedLiterals"], "missingProtectedLiterals": missing_protected, "protectedLiteralsPreserved": not missing_protected,
                "containsCandidate": False,
            })
    if len(cells) != 240:
        raise SystemExit("FAIL W645 cell count")

    main_head = api_before["baseLiveRefOid"]
    main_tree = git(repo, "rev-parse", f"{main_head}^{{tree}}")
    main_catalog = json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{main_head}:{catalog_path}"], text=True))["messages"]
    main_files = {rel: file_tuple(repo, rel, main_head) for rel in production_paths(repo, main_head)}
    def caller_sig(context: dict) -> set[tuple]:
        return {(row["path"], row["matchKind"], row["lineText"].strip()) for row in context["callers"]}
    drift_rows = []
    for item, pr_context in zip(selected, contexts):
        main_msg = main_catalog.get(item["sourceId"])
        main_source = main_msg.get("source") if isinstance(main_msg, dict) else None
        main_source_hash = sha(main_source) if isinstance(main_source, str) else None
        if isinstance(main_source, str):
            main_context = match_context({"sourceId": item["sourceId"], "source": main_source, "sourceSha256": main_source_hash}, main_files, main_head)
        else:
            main_context = {"callerless": True, "callers": [], "exactMatchCount": 0}
        new_refs = sorted(caller_sig(main_context) - caller_sig(pr_context))
        removed_refs = sorted(caller_sig(pr_context) - caller_sig(main_context))
        drift_rows.append({"sourceId": item["sourceId"], "prSourceSha256": item["sourceSha256"], "mainSourcePresent": isinstance(main_source, str), "mainSourceSha256": main_source_hash, "sourceSame": main_source_hash == item["sourceSha256"], "prCallerCount": pr_context["exactMatchCount"], "mainCallerCount": main_context["exactMatchCount"], "prCallerless": pr_context["callerless"], "mainCallerless": main_context["callerless"], "newMainCallerSignatures":[{"path": ref[0], "matchKind": ref[1], "lineText": ref[2]} for ref in new_refs], "prOnlyCallerSignatures":[{"path": ref[0], "matchKind": ref[1], "lineText": ref[2]} for ref in removed_refs], "contextDrift": (main_source_hash != item["sourceSha256"] or bool(new_refs) or bool(removed_refs) or pr_context["exactMatchCount"] != main_context["exactMatchCount"])})
    main_drift = {"repository":"snapetech-org/ROMarrNG", "prHead":HEAD, "prTree":TREE, "mainHead":main_head, "mainTree":main_tree, "baseApiSha":api_before["baseApiSha"], "baseApiRefMismatch":api_before["baseApiRefMismatch"], "comparison":"same stable source IDs and exact quoted source/source-ID/HTML text searches over tracked production files under romarr; tests, docs, catalogs, and workflows excluded", "selectedSourceCount":20, "sourcesMissingFromMain":sum(not row["mainSourcePresent"] for row in drift_rows), "sourceTextChanges":sum(not row["sourceSame"] for row in drift_rows), "sourcesWithCallerContextDrift":sum(bool(row["contextDrift"]) for row in drift_rows), "sourcesWithNewMainCallers":sum(bool(row["newMainCallerSignatures"]) for row in drift_rows), "results":drift_rows}

    # Include exact prior hash-only evidence without any translation text.
    input_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out / "verify_input.py", input_dir / "verify_input.py")
    (input_dir / "prior-w625-application-readback.jsonl").write_bytes(w625_readback_raw)
    (input_dir / "prior-w625-application-plan.json").write_bytes((root / "root-application-plan.json").read_bytes())
    (input_dir / "prior-w625-final-head-verification.json").write_bytes((root / "final-head-verification.json").read_bytes())
    write_json(input_dir / "PR-attestation-before.json", api_before)
    write_json(input_dir / "catalog-file-pins.json", {"repository":"snapetech-org/ROMarrNG", "commit":HEAD, "tree":TREE, "catalogPath":catalog_path, "catalogSha256":sha(catalog_raw), "catalogGitBlob":git(repo, "rev-parse", f"{HEAD}:{catalog_path}"), "catalogMessageCount":len(messages), "catalogKeyOrderSha256":catalog_order_sha, "sourceQueuePath":registry_path, "sourceQueueSha256":source_queue_sha, "sourceSnapshotPath":snapshot_path, "sourceSnapshotSha256":source_snapshot_sha, "sourceIdOrderSha256":id_order_sha, "activeUniqueSourceIds":len(registry), "sourceCallerFilePins":{row["path"]:{"fileSha256":row["fileSha256"], "gitBlob":row["gitBlob"]} for row in source_pin_rows}})
    write_json(input_dir / "source-file-pins.json", {"head":HEAD, "tree":TREE, "files":source_pin_rows})
    write_json(input_dir / "source-snapshot.json", raw_snapshot)
    (input_dir / "source-queue.json").write_bytes(registry_raw)
    inventory = []
    for idx, source_id in enumerate(ids):
        message = messages[source_id]
        source_text = message["source"]
        source_tokens = tokens(source_text)
        target_values = message.get("translations", {})
        inventory.append({"catalogZeroBasedIndex":idx, "catalogOneBasedPosition":idx + 1, "sourceId":source_id, "source":source_text, "sourceSha256":sha(source_text), "activeSourceRegistry":source_id in registry, "activeSourceRank":active_rank.get(source_id), "registryLocations":registry.get(source_id, {}).get("locations", []), "sourcePlaceholderTokens":source_tokens["placeholders"], "sourceMarkupTags":source_tokens["markup"], "sourceNumericTokens":source_tokens["numbers"], "sourceProtectedLiterals":source_tokens["protectedLiterals"], "targetHashes":{locale:(sha(target_values[locale]) if isinstance(target_values.get(locale), str) else None) for locale in LOCALES}})
    write_jsonl(input_dir / "catalog-source-inventory.jsonl", inventory)
    write_jsonl(input_dir / "source-inventory-selection.jsonl", selected)
    write_json(input_dir / "selection.json", {"window":WINDOW, "method":"Select catalog message insertion indices 645 through 664 (zero-based) from the exact pinned romarr/ui-labels.json message-key order; the catalog order is distinct from the active source registry sort.", "positions":[645,664], "catalogInsertionPositionsOneBased":[646,665], "sourceCount":20, "localeCount":12, "cellCount":240, "localeOrder":LOCALES, "activeUniqueSourceIds":len(registry), "sourceIdOrderSha256":id_order_sha, "catalogMessageCount":len(messages), "catalogKeyOrderSha256":catalog_order_sha, "selectedSources":selected})
    write_json(input_dir / "registry-order-note.json", {"selectionBasis":"catalog JSON message-key insertion order", "selectedCatalogZeroBasedIndices":[645,664], "activeRegistryCount":len(registry), "selectedIdsInActiveRegistry":sum(row["activeSourceRegistry"] for row in selected), "activeRegistryMatches":[{"sourceId":row["sourceId"], "activeRank":row["activeSourceRank"], "registryLocations":row["registryLocations"]} for row in selected if row["activeSourceRegistry"]], "lineHintCaveat":"Active source registry metadata does not substitute for exact literal caller search and excerpt evidence."})
    write_jsonl(input_dir / "selection-boundary.jsonl", selection_boundary)
    write_jsonl(input_dir / "source-contexts.jsonl", contexts)
    write_json(input_dir / "caller-search-audit.json", {"head":HEAD, "tree":TREE, "queryCount":20, "searchScope":"tracked production source files under romarr; tests, docs, and locale catalogs excluded", "productionFilesSearched":len(production_files), "results":[{"sourceId":row["sourceId"], "sourceSha256":row["sourceSha256"], "matchCount":row["exactMatchCount"], "callerless":row["callerless"], "contextSha256":row["contextSha256"]} for row in contexts]})
    write_jsonl(input_dir / "current-target-cells.jsonl", cells)
    write_json(input_dir / "current-target-token-mismatches.json", dict(mismatch))
    write_json(input_dir / "main-context-drift.json", main_drift)
    write_json(input_dir / "dispatch-mechanics.json", {"head":HEAD, "tree":TREE, "sourceFiles":[row for row in source_pin_rows if row["path"] in ("romarr/i18n_runtime.js", "romarr/ui.py", "romarr/ui-source-messages.json")], "description":"Source ownership and locale dispatch are pinned through exact source file hashes; translation review is limited to the source queue and current catalog cells."})

    write_jsonl(input_dir / "prior-selection-reattestation.jsonl", selection_rows)
    write_json(input_dir / "prior-selection-reattestation-summary.json", {"priorWindows":dict(collections.Counter(row["priorWindow"] for row in selection_rows)), "reattestedSelectedSourceCount":len(selection_rows), "allPriorSelectionsMatchCurrentCatalogAndRegistry":True, "currentHead":HEAD, "currentTree":TREE})
    write_jsonl(input_dir / "prior-hold-reattestation.jsonl", hold_rows)
    write_json(input_dir / "prior-hold-reattestation-summary.json", {"reattestedCellCount":len(hold_rows), "windowCounts":dict(collections.Counter(row["window"] for row in hold_rows)), "allSourcesAndSelectionPositionsMatchCurrentSnapshot":True, "allCurrentTargetHashesMatchPriorHoldEvidence":True, "currentTargetChangedCells":0, "callerlessW625HashOnlyHoldCells":len(w625_hold_ids), "currentHead":HEAD, "currentTree":TREE})
    write_jsonl(input_dir / "prior-applied-cell-reattestation.jsonl", applied_rows)
    write_json(input_dir / "prior-applied-cell-reattestation-summary.json", {"priorWindows":dict(collections.Counter(row["priorWindow"] for row in applied_rows)), "applicationCommits":{"W505-W524":"b248261d5aaa33ec7247023b85d666ed7fc89309", "W525-W544":"63224167b0f89978a68977a7996bd06724d06129", "W545-W564":"2a921d8280487f6d172616719f32e3dced243d83", "W565-W584":"89fcad0d1ecce9610a0c3fc100de814e9e6dc5ac", "W585-W604":"d44e61d9960c788412da0fadbb8b67744b70e404", "W605-W624":"e6e826be77e5057cf88b4bbb49f6ff60f2980c33", "W625-W644":PREV_PRODUCT}, "reattestedCellCount":len(applied_rows), "allSelectedTargetHashesMatchCurrentCatalog":True, "changedCells":0, "currentHead":HEAD, "currentTree":TREE})
    for label, rows in recent_readbacks.items():
        name = label.lower().replace("-", "") + "-cell-hash-reattestation.jsonl"
        write_jsonl(input_dir / name, rows)
    write_jsonl(input_dir / "w625-application-cell-hash-reattestation.jsonl", w625_reasserted)
    write_json(input_dir / "continuity-reattestation.json", {"result":"PASS", "priorWindow":"W625-W644", "priorSourceHead":PREV_HEAD, "priorSourceTree":PREV_TREE, "priorProductCommit":PREV_PRODUCT, "currentHead":HEAD, "currentTree":TREE, "priorCandidateFreePacketChecksumsVerified":True, "priorApplicationEvidenceChecksumsVerified":False, "priorApplicationEvidenceIndexEntryCount":len(indexed) + len(missing_indexed), "priorApplicationEvidenceIndexMissingFromPRTreeCount":len(missing_indexed), "priorTrackedApplicationEvidenceFilesMatched":True, "priorW625FullReadbackSha256MatchedCommittedFinalVerifier":True, "priorW625ApplicationPlanSha256":sha((input_dir / "prior-w625-application-plan.json").read_bytes()), "priorW625FinalVerifierSha256":sha((input_dir / "prior-w625-final-head-verification.json").read_bytes()), "priorSelectedSourceCount":len(selection_rows), "priorHoldCellCount":len(hold_rows), "priorAppliedCellCount":len(applied_rows), "priorSelectedSourceChangedCount":0, "priorHoldCellChangedCount":0, "priorAppliedCellChangedCount":0, "priorW565ReadbackRows":len(recent_readbacks["W565-W584"]), "priorW585ReadbackRows":len(recent_readbacks["W585-W604"]), "priorW605ReadbackRows":len(recent_readbacks["W605-W624"]), "priorW625ReadbackRows":len(w625_reasserted), "priorW625AppliedChanges":sum(row["applicationChanged"] for row in w625_reasserted), "priorW625CallerlessHolds":sum(row["callerlessHeld"] for row in w625_reasserted), "priorW625ReadbackSha256":sha(w625_readback_raw), "currentCatalogSha256":sha(catalog_raw), "sourceSnapshotSha256":source_snapshot_sha, "sourceQueueSha256":source_queue_sha, "sourceIdOrderSha256":id_order_sha, "attestedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds")})

    manifest = {"artifact":"ROMarrNG PR #70 W645-W664 candidate-free input", "repository":"snapetech-org/ROMarrNG", "pullRequest":70, "branch":BRANCH, "baseRefName":"main", "head":HEAD, "tree":TREE, "window":WINDOW, "selectionBasis":"catalog insertion order; exact pinned ui-labels.json message indices 645..664", "sourceCount":20, "localeCount":12, "cellCount":240, "locales":LOCALES, "activeUniqueSourceIdCount":len(registry), "sourceIdOrderSha256":id_order_sha, "catalogMessageCount":len(messages), "catalogPath":catalog_path, "catalogSha256":sha(catalog_raw), "catalogGitBlob":git(repo, "rev-parse", f"{HEAD}:{catalog_path}"), "catalogKeyOrderSha256":catalog_order_sha, "sourceQueuePath":registry_path, "sourceQueueSha256":source_queue_sha, "sourceSnapshotSha256":source_snapshot_sha, "priorSelectedSourceCount":len(selection_rows), "priorSelectionsUnchanged":True, "priorHoldCellCount":len(hold_rows), "priorHoldTargetsUnchanged":True, "priorHoldCellChangedCount":0, "priorAppliedSelectedCellCount":len(applied_rows), "priorAppliedTargetsUnchanged":True, "priorW625ApplicationEvidenceChecksumsVerified":False, "priorW625ApplicationEvidenceIndexMissingFromPRTreeCount":len(missing_indexed), "priorW625FullReadbackSha256":sha(w625_readback_raw), "priorW625FullReadbackSha256MatchedCommittedFinalVerifier":True, "priorW565FullCellHashReadbackCount":len(recent_readbacks["W565-W584"]), "priorW585FullCellHashReadbackCount":len(recent_readbacks["W585-W604"]), "priorW605FullCellHashReadbackCount":len(recent_readbacks["W605-W624"]), "priorW625FullCellHashReadbackCount":len(w625_reasserted), "priorW625ChangedAppliedCellCount":sum(row["applicationChanged"] for row in w625_reasserted), "priorW625CallerlessHoldCellCount":sum(row["callerlessHeld"] for row in w625_reasserted), "currentTargetPlaceholderMismatches":mismatch["placeholder"], "currentTargetMarkupMismatches":mismatch["markup"], "currentTargetNumericMismatches":mismatch["numeric"], "currentTargetNumericPresentationDifferences":mismatch["numericPresentationDifferences"], "currentTargetProtectedLiteralMismatches":mismatch["protectedLiteral"], "currentTargetMissingCells":mismatch["missingTarget"], "callerSearchQueryCount":20, "sourceContextCount":20, "callerlessSourceCount":sum(row["callerless"] for row in contexts), "callerlessCurrentTargetCellCount":12 * sum(row["callerless"] for row in contexts), "directCallerRefCount":sum(row["exactMatchCount"] for row in contexts), "activeRegistrySelectedSourceCount":sum(row["activeSourceRegistry"] for row in selected), "mainHead":main_head, "mainTree":main_tree, "mainSourcesMissing":main_drift["sourcesMissingFromMain"], "mainSourceTextChanges":main_drift["sourceTextChanges"], "mainContextDriftCount":main_drift["sourcesWithCallerContextDrift"], "candidateFree":True, "proposedTargetsIncluded":False, "reviewDecisionsIncluded":False, "createdUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"), "reviewBoundary":f"Fresh exact-head input with catalog-order source selection, current targets, exact source/caller contexts, protected-token checks, same-ID/source/caller comparison against live main, and hash-only reattestation of 260 prior source selections, 724 prior held cells, 76 applied cells, and the W565/W585/W605/W625 readbacks. The exact W625 application plan, final-verifier record, and full readback are included; {len(missing_indexed)} bulky stage files referenced by its historical checksum index were absent from the PR tree and are not claimed as fully verified. No W645-W664 proposal or review decision is included."}
    write_json(input_dir / "manifest.json", manifest)
    api_after = attestation(repo)
    keys = ("state", "draft", "merged", "headRefName", "head", "tree", "branchRefOid", "pullRefOid", "baseRefName", "baseApiSha", "baseLiveRefOid", "bodySha256", "bodyBytes")
    if any(api_before[key] != api_after[key] for key in keys):
        raise SystemExit("FAIL PR/API/head/body changed during candidate-free extraction")
    write_json(input_dir / "PR-attestation-after-candidate-free.json", api_after)
    if git(repo, "rev-parse", "HEAD") != HEAD or git(repo, "rev-parse", "HEAD^{tree}") != TREE or git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise SystemExit("FAIL source worktree changed during candidate-free extraction")
    (out / "README.md").write_text(f"""# ROMarrNG PR #70 W645–W664 candidate-free packet

Pinned to open draft PR head `{HEAD}`, tree `{TREE}`, branch `{BRANCH}`. The selection uses catalog insertion indices 645–664 (one-based positions 646–665): 20 sources and 240 locale cells.

This input re-attests 260 earlier selected source IDs, 724 held cells, 76 applied cells, and the W565/W585/W605/W625 240-cell readbacks. The prior W625–W644 window applied three catalog corrections and retained 60 callerless hash-only holds; all 240 final target hashes match at this head. Its full W625 readback, application plan, and final-verifier record are included and hash-bound. The historical checksum index also references {len(missing_indexed)} bulky stage files absent from the PR tree; the packet does not claim those files were verified.

The packet binds current source and target text, exact source and caller context, protected-token checks, source/catalog hashes, and a same-ID/source/caller comparison against live `main` at `{main_head}`. It contains no W645–W664 proposed target or review decision. API, branch, pull-ref, PR-body, and source-tree attestations matched before and after extraction.

Verify with `python3 verify_bundle.py --repo /path/to/the-exact-9f8832f-ROMarrNG-worktree` from this directory. This semantic packet does not confer native-speaker approval.
""", encoding="utf-8")
    print(json.dumps({"result":"CANDIDATE_FREE_DATA_BUILT", "head":HEAD, "tree":TREE, "mainHead":main_head, "mainTree":main_tree, "window":WINDOW, "selectedSources":len(selected), "cells":len(cells), "callerlessSources":sum(row["callerless"] for row in contexts), "callerlessCells":12 * sum(row["callerless"] for row in contexts), "directCallerRefs":sum(row["exactMatchCount"] for row in contexts), "tokenMismatches":dict(mismatch), "priorSelectedSources":len(selection_rows), "priorHoldCells":len(hold_rows), "priorAppliedCells":len(applied_rows), "priorReadbacks":[len(rows) for rows in recent_readbacks.values()] + [len(w625_reasserted)], "mainContextDrift":{"missing":main_drift["sourcesMissingFromMain"], "sourceChanged":main_drift["sourceTextChanges"], "contextDrift":main_drift["sourcesWithCallerContextDrift"], "newMainCallers":main_drift["sourcesWithNewMainCallers"]}}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
