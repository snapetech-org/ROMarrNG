#!/usr/bin/env python3
"""Build candidate-free ROMarrNG PR #70 W725-W744 source/review input."""
from __future__ import annotations
import argparse, collections, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

HEAD = "c3f92c45b4b4f8d79a8caa99417f9970ebc42a26"
TREE = "3f835643e4f557999d533c3e832fc92036d4b01a"
BRANCH = "task/localization-translation-review-20261030"
PREV_HEAD = "50e3f8a48a800affff8bad367b5c493cc0fdfd62"
PREV_TREE = "22cd46ff4821fcbbe76b4760a15e22d688b3f548"
PREV_PRODUCT = "453d9755dc442cde05ebbd4561c4b22d76d6906f"
PREV_PRODUCT_TREE = "4c51a1ab7d592feb75f250b831b5a6cd4225ccb1"
WINDOW = "W725-W744"
PREV_WINDOW = "W705-W724"
PREV_TASK = Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w705-724-20261105/candidate-free")
PREV_INPUT = PREV_TASK / "input"
PREV_PACKET = PREV_TASK
PREV_APP_SUMMARY = Path("docs/pr-evidence/pr70-localization-2026-11-05/window-705-724/application/application-summary.json")
PREV_FINAL_READBACK = Path("docs/pr-evidence/pr70-localization-2026-11-05/window-705-724/application/final-head-readback.jsonl")
PREV_SELECTED_TARGETS = Path("docs/pr-evidence/pr70-localization-2026-11-05/window-705-724/application/selected-targets.jsonl")
W665_EVIDENCE_REL = Path("docs/pr-evidence/pr70-localization-2026-11-05/window-665-684")
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
TAG = re.compile(r"<[^>]+>")
NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
PROTECTED = ["Gaseous", "Retrom", "SeerrNG", "ROMarrNG", "ROMarr", "ES-DE", "No-Intro", "Redump", "DAT", "IGDB", "ISO9660", "PLAYSTATION", "PlayStation", "PS2", "ROMs", "ROM", "PC", "API", "ROMARR_API_KEY", "Linksnappy", "Moonlight", "PIN", "NPSSO", "NZBHydra2", "Newznab", "/torznab/api", "NZBVortex", "HTTPS", "NZB", "Preferences"]

def sha(v):
    if isinstance(v, str): v = v.encode("utf-8")
    return hashlib.sha256(v).hexdigest()
def canon(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
def rj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def rjl(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
def wj(p, v):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
def wjl(p, rows):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for x in rows), encoding="utf-8")
def git(repo, *args): return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
def verify_sums(root, filename="SHA256SUMS.txt"):
    root = Path(root); sums = root / filename; listed = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        digest, name = line.split("  ", 1); path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes()) != digest: raise SystemExit(f"FAIL checksum {root}/{name}")
        if name in listed: raise SystemExit(f"FAIL duplicate checksum {root}/{name}")
        listed[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != sums}
    if set(listed) != actual: raise SystemExit(f"FAIL checksum coverage {root}: missing={sorted(set(listed)-actual)} unlisted={sorted(actual-set(listed))}")
    return listed
def write_sums(root):
    root = Path(root); target = root / "SHA256SUMS.txt"
    files = sorted(p for p in root.rglob("*") if p.is_file() and p != target)
    target.write_text("".join(f"{sha(p.read_bytes())}  {p.relative_to(root).as_posix()}\n" for p in files), encoding="utf-8")
def protected(s):
    out = []
    for literal in PROTECTED:
        found = literal in s if literal.startswith("/") else bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(literal) + r"(?![A-Za-z0-9])", s))
        if found: out.append(literal)
    return sorted(set(out))
def tokens(s): return {"placeholders": PLACEHOLDER.findall(s), "markup": TAG.findall(s), "numbers": NUMBER.findall(s), "protectedLiterals": protected(s)}
def production_paths(repo, commit):
    raw = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", commit, "--", "romarr"], text=True).splitlines()
    allowed = {".py", ".js", ".html", ".jinja", ".jinja2", ".css", ".ts", ".tsx"}; out = []
    for rel in raw:
        p = Path(rel); parts = rel.lower().split("/")
        if p.suffix.lower() not in allowed or any(x in parts for x in ("test", "tests", "__pycache__")) or p.name.startswith("test_") or p.name.endswith("_test.py"): continue
        out.append(rel)
    return out
def file_tuple(repo, rel, commit):
    raw = subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{rel}"])
    return raw.decode("utf-8", "replace"), raw, git(repo, "rev-parse", f"{commit}:{rel}")
def match_context(item, files, commit):
    source = item["source"]; back = chr(96)
    variants = list(dict.fromkeys([json.dumps(source, ensure_ascii=False), repr(source), '"' + source + '"', "'" + source + "'", back + source + back]))
    callers = []
    for rel, (text, data, blob) in files.items():
        hits = {}
        for literal in variants:
            at = 0
            while True:
                pos = text.find(literal, at)
                if pos < 0: break
                hits.setdefault(pos, "exact quoted source literal"); at = pos + max(1, len(literal))
        at = 0
        while True:
            pos = text.find(item["sourceId"], at)
            if pos < 0: break
            hits.setdefault(pos, "exact source ID reference"); at = pos + len(item["sourceId"])
        for m in re.finditer(r">[ \t]*" + re.escape(source) + r"[ \t]*<", text): hits.setdefault(m.start(), "exact HTML text node")
        lines = text.splitlines()
        for pos, kind in sorted(hits.items()):
            line = text.count("\n", 0, pos) + 1
            excerpt = [{"line": n, "text": lines[n-1]} for n in range(max(1, line-3), min(len(lines), line+3)+1)]
            line_text = lines[line-1] if line <= len(lines) else ""
            callers.append({"path": rel, "line": line, "lineText": line_text, "lineSha256": sha(line_text), "excerpt": excerpt, "excerptSha256": sha(canon(excerpt)), "fileSha256": sha(data), "gitBlob": blob, "matchKind": kind})
    callers.sort(key=lambda x: (x["path"], x["line"], x["matchKind"]))
    core = {"sourceId": item["sourceId"], "source": source, "sourceSha256": item["sourceSha256"], "head": commit, "searchMethod": "exact quoted source literal, exact source ID, or exact HTML text-node search in tracked production code under romarr; tests, docs, catalogs, and workflows excluded", "productionFilesSearched": len(files), "exactMatchCount": len(callers), "callerless": not callers, "callers": callers}
    return {**core, "contextSha256": sha(canon(core))}
def safe_context(c):
    z = {k: c[k] for k in ("sourceId", "sourceSha256", "head", "searchMethod", "productionFilesSearched", "exactMatchCount", "callerless", "contextSha256")}
    if c["callerless"]: z.update({"sourceTextOmitted": True, "callers": []})
    else: z.update({"source": c["source"], "callers": c["callers"]})
    return z
def attestation(repo):
    pr = json.loads(subprocess.check_output(["gh", "api", "repos/snapetech-org/ROMarrNG/pulls/70"], cwd=repo, text=True))
    cap = json.loads(subprocess.check_output(["gh", "api", f"repos/snapetech-org/ROMarrNG/commits/{HEAD}"], cwd=repo, text=True))
    raw = git(repo, "ls-remote", "origin", f"refs/heads/{BRANCH}", "refs/pull/70/head", "refs/heads/main")
    refs = {x.split("\t")[1]: x.split("\t")[0] for x in raw.splitlines() if x.strip()}
    body = pr.get("body") or ""
    result = {"attestedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "repository": "snapetech-org/ROMarrNG", "pullRequest": 70, "state": pr["state"].upper(), "draft": bool(pr["draft"]), "merged": bool(pr["merged"]), "headRefName": pr["head"]["ref"], "head": pr["head"]["sha"], "tree": git(repo, "rev-parse", f"{HEAD}^{{tree}}"), "apiCommitTree": cap["commit"]["tree"]["sha"], "branchRefOid": refs.get(f"refs/heads/{BRANCH}"), "pullRefOid": refs.get("refs/pull/70/head"), "baseRefName": pr["base"]["ref"], "baseApiSha": pr["base"]["sha"], "baseLiveRefOid": refs.get("refs/heads/main"), "baseApiRefMismatch": pr["base"]["sha"] != refs.get("refs/heads/main"), "bodySha256": sha(body), "bodyBytes": len(body.encode()), "checksRerun": False}
    expected = ("OPEN", True, False, BRANCH, HEAD, TREE, TREE, HEAD, HEAD, "main")
    actual = (result["state"], result["draft"], result["merged"], result["headRefName"], result["head"], result["tree"], result["apiCommitTree"], result["branchRefOid"], result["pullRefOid"], result["baseRefName"])
    if actual != expected: raise SystemExit("FAIL PR/API/branch/pull alignment " + repr(result))
    if git(repo, "rev-parse", "HEAD") != HEAD or git(repo, "rev-parse", "HEAD^{tree}") != TREE: raise SystemExit("FAIL exact source pin")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all") or git(repo, "branch", "--show-current"): raise SystemExit("FAIL source worktree not clean detached")
    return result
def token_rows(source, target):
    s = tokens(source); t = tokens(target)
    ph = collections.Counter(s["placeholders"]) == collections.Counter(t["placeholders"])
    mk = collections.Counter(s["markup"]) == collections.Counter(t["markup"])
    sn, tn = collections.Counter(s["numbers"]), collections.Counter(t["numbers"]); extra = list((tn-sn).elements())
    presentation = bool(re.search(r"\bzero\b", source, re.I) and not s["numbers"] and extra == ["0"])
    numeric = not (sn-tn) and (not extra or presentation)
    missing = [x for x in s["protectedLiterals"] if x not in target]
    return {"sourcePlaceholderTokens": s["placeholders"], "currentPlaceholderTokens": t["placeholders"], "placeholderMultisetMatches": ph, "sourceMarkupTags": s["markup"], "currentMarkupTags": t["markup"], "markupMatches": mk, "sourceNumericTokens": s["numbers"], "currentNumericTokens": t["numbers"], "numericTokensPreserved": numeric, "numericPresentationEquivalent": presentation, "sourceProtectedLiterals": s["protectedLiterals"], "missingProtectedLiterals": missing, "protectedLiteralsPreserved": not missing}
def signature(c): return [(x["path"], x["line"], x["lineSha256"], x["excerptSha256"], x["fileSha256"], x["gitBlob"], x["matchKind"]) for x in c["callers"]]
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repo", type=Path, required=True); repo = ap.parse_args().repo.resolve()
    out = Path(__file__).resolve().parent; inp = out / "input"
    if any(p.is_file() for p in inp.iterdir()): raise SystemExit("FAIL candidate-free input directory is not empty")
    api0 = attestation(repo)
    verify_sums(PREV_PACKET); verify_sums(PREV_INPUT)
    prev_manifest = rj(PREV_INPUT / "manifest.json")
    if (prev_manifest.get("head"), prev_manifest.get("tree"), prev_manifest.get("window")) != (PREV_HEAD, PREV_TREE, PREV_WINDOW): raise SystemExit("FAIL W705 predecessor packet pin")
    if (prev_manifest.get("priorSelectedSourceCount"), prev_manifest.get("priorHoldCellCount"), prev_manifest.get("priorAppliedSelectedCellCount")) != (320, 904, 127): raise SystemExit("FAIL W705 predecessor lineage counts")
    prev_selections = rjl(PREV_INPUT / "prior-selection-reattestation.jsonl")
    prev_selected = rjl(PREV_INPUT / "selected-sources.jsonl")
    prev_holds = rjl(PREV_INPUT / "prior-hold-reattestation.jsonl")
    prev_applied = rjl(PREV_INPUT / "prior-applied-cell-reattestation.jsonl")
    prev_cells = rjl(PREV_INPUT / "candidate-free-cells.jsonl")
    prev_contexts = {x["sourceId"]: x for x in rjl(PREV_INPUT / "source-contexts.jsonl")}
    if (len(prev_selections), len(prev_selected), len(prev_holds), len(prev_applied), len(prev_cells), len(prev_contexts)) != (320, 20, 904, 127, 240, 20): raise SystemExit("FAIL W705 predecessor packet coverage")
    if any(r.get("proposedTarget") is not None or r.get("reviewDecision") is not None for r in prev_cells): raise SystemExit("FAIL W705 candidate-free boundary")

    # Confirm the prior W705 product application from its exact candidate-free input and committed product.
    prior_app = rj(repo / PREV_APP_SUMMARY)
    if (prior_app.get("window"), prior_app.get("inputHead"), prior_app.get("inputTree"), prior_app.get("productHead"), prior_app.get("productTree"), prior_app.get("changedCells")) != (PREV_WINDOW, PREV_HEAD, PREV_TREE, PREV_PRODUCT, PREV_PRODUCT_TREE, 5): raise SystemExit("FAIL W705 application source pin/count")
    if git(repo, "rev-parse", f"{PREV_PRODUCT}^") != PREV_HEAD or git(repo, "rev-parse", f"{PREV_PRODUCT}^{{tree}}") != PREV_PRODUCT_TREE: raise SystemExit("FAIL W705 product ancestry/tree")
    if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", PREV_PRODUCT, HEAD], check=False).returncode: raise SystemExit("FAIL W705 product not in current history")
    if subprocess.check_output(["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", PREV_PRODUCT], text=True).splitlines() != ["romarr/ui-labels.json"]: raise SystemExit("FAIL W705 product changed paths")
    if subprocess.run(["git", "-C", str(repo), "show", "-s", "--format=%s", PREV_HEAD], check=True, text=True, stdout=subprocess.PIPE).stdout.strip() != "docs(i18n): restore ROMarr W665 review payloads [skip ci]": raise SystemExit("FAIL expected W665 restoration commit in predecessor history")

    catalog_path = "romarr/ui-labels.json"; registry_path = "romarr/ui-source-messages.json"; snapshot_path = "romarr/ui-source-snapshot.json"
    catalog_raw = (repo/catalog_path).read_bytes(); catalog = json.loads(catalog_raw); msgs = catalog["messages"]; ids = list(msgs)
    if len(msgs) != 1836: raise SystemExit("FAIL catalog message count")
    registry_raw = (repo/registry_path).read_bytes(); registry_doc = rj(repo/registry_path); registry_rows = registry_doc["messages"]
    registry = {r["id"]: r for r in registry_rows}
    if len(registry) != len(registry_rows): raise SystemExit("FAIL duplicate active registry IDs")
    active_rank = {sid: i for i, sid in enumerate(sorted(registry), 1)}; snapshot = rj(repo/snapshot_path)
    if any(snapshot.get(r["id"]) != r["sourceHash"] for r in registry_rows): raise SystemExit("FAIL registry/snapshot mismatch")
    cat_order_sha = sha("\n".join(ids) + "\n"); id_order_sha = sha("\n".join(sorted(registry)) + "\n")
    source_snapshot_sha = sha(canon(snapshot)); source_queue_sha = sha(registry_raw)

    # Reattest all earlier selections and holds from W705, plus the five W705 applied cells.
    selection_rows = []
    for row in prev_selections + prev_selected:
        sid = row["sourceId"]; idx = row.get("catalogZeroBasedIndex", row.get("position")); msg = msgs.get(sid)
        old_hash = row.get("currentSourceSha256", row.get("sourceSha256", row.get("priorSourceSha256")))
        if msg is None or idx is None or not (0 <= idx < len(ids)) or ids[idx] != sid: raise SystemExit(f"FAIL prior source selection position {sid}")
        cur_hash = sha(msg["source"])
        if cur_hash != old_hash or msg.get("sourceHash") != cur_hash or registry.get(sid, {}).get("sourceHash") not in (None, cur_hash): raise SystemExit(f"FAIL prior source selection hash {sid}")
        selection_rows.append({"priorWindow": row.get("priorWindow", PREV_WINDOW), "position": row.get("position", idx), "catalogZeroBasedIndex": idx, "sourceId": sid, "priorSourceSha256": old_hash, "currentSourceSha256": cur_hash, "selectionPositionMatches": True, "sourceHashMatches": True, "registryMembershipAndHashMatch": sid in registry, "priorSelectionEvidenceSha256": row.get("priorSelectionEvidenceSha256", sha(canon(row))), "reattestedAtHead": HEAD})
    if len(selection_rows) != 340 or len({r["sourceId"] for r in selection_rows}) != 340: raise SystemExit("FAIL total prior source selections")
    prior_position_by_id = {r["sourceId"]: r["catalogZeroBasedIndex"] for r in selection_rows}

    production = {p: file_tuple(repo, p, HEAD) for p in production_paths(repo, HEAD)}
    hold_rows = []
    for row in prev_holds:
        sid, loc = row["sourceId"], row["locale"]; msg = msgs[sid]; idx = ids.index(sid)
        basis = row.get("selectionPositionBasis", "")
        recorded_position = row.get("priorPosition") if row.get("priorPositionRecorded") else row.get("position")
        recorded_catalog_index = row.get("catalogZeroBasedIndex")
        current_position_matches = recorded_catalog_index == idx if recorded_catalog_index is not None else (idx == recorded_position if "catalog insertion index" in basis else prior_position_by_id.get(sid) == idx)
        if row.get("priorPositionRecorded") is False: prior_position_matches = True
        elif recorded_position is None: prior_position_matches = prior_position_by_id.get(sid) == idx
        elif "catalog insertion index" in basis: prior_position_matches = idx == recorded_position
        elif basis: prior_position_matches = active_rank.get(sid) == recorded_position
        else: prior_position_matches = prior_position_by_id.get(sid) == idx
        pos_ok = current_position_matches and prior_position_matches
        source_hash = sha(msg["source"]); target_hash = sha(msg["translations"][loc])
        expected_target = row.get("priorTargetSha256", row.get("currentTargetSha256"))
        if source_hash != row["sourceSha256"] or target_hash != expected_target or not pos_ok: raise SystemExit(f"FAIL prior held cell changed {sid}/{loc}")
        if any(k in row for k in ("source", "sourceText", "currentTarget", "target", "targetText", "proposedTarget")): raise SystemExit("FAIL predecessor hold includes text")
        hold_rows.append({"window": row["window"], "position": idx, "priorPosition": recorded_position, "selectionPositionBasis": basis or "derived from prior source selection", "priorPositionRecorded": recorded_position is not None, "catalogZeroBasedIndex": idx, "sourceId": sid, "sourceSha256": source_hash, "locale": loc, "priorTargetSha256": expected_target, "currentTargetSha256": target_hash, "selectionPositionMatches": True, "targetUnchanged": True, "priorHoldEvidenceSha256": row.get("priorHoldEvidenceSha256", sha(canon(row))), "textOmitted": True, "reattestedAtHead": HEAD})
    prior_hold_contexts = []
    for sid in sorted({r["sourceId"] for r in hold_rows}):
        msg = msgs[sid]; ctx = match_context({"sourceId": sid, "source": msg["source"], "sourceSha256": sha(msg["source"])}, production, HEAD)
        prior_hold_contexts.append({"sourceId": sid, "sourceSha256": sha(msg["source"]), "callerlessAtCurrentHead": ctx["callerless"], "exactMatchCount": ctx["exactMatchCount"], "callerContextSha256": ctx["contextSha256"], "heldCellCount": sum(r["sourceId"] == sid for r in hold_rows), "sourceTextOmitted": True, "callerTextOmitted": True})

    applied_rows = []
    for row in prev_applied:
        sid, loc = row["sourceId"], row["locale"]; msg = msgs[sid]; sh = sha(msg["source"]); th = sha(msg["translations"][loc])
        expected = row.get("priorSelectedTargetSha256", row.get("currentTargetSha256"))
        if sh != row["sourceSha256"] or th != expected: raise SystemExit(f"FAIL previously applied cell changed {sid}/{loc}")
        applied_rows.append({"priorWindow": row["priorWindow"], "catalogZeroBasedIndex": ids.index(sid), "sourceId": sid, "sourceSha256": sh, "locale": loc, "priorSelectedTargetSha256": expected, "currentTargetSha256": th, "targetUnchanged": True, "applicationCommit": row.get("applicationCommit"), "priorAppliedEvidenceSha256": row.get("priorAppliedEvidenceSha256", sha(canon(row))), "textOmitted": True, "reattestedAtHead": HEAD})

    prev_cell_map = {(r["sourceId"], r["locale"]): r for r in prev_cells}
    readback_rows = rjl(repo / PREV_FINAL_READBACK)
    if len(readback_rows) != 240: raise SystemExit("FAIL W705 final readback coverage")
    readback_map = {}
    for row in readback_rows:
        key = (row["sourceId"], row["locale"])
        if key in readback_map or not row.get("matches"): raise SystemExit("FAIL W705 final readback duplicate/failure")
        readback_map[key] = row
    if len(prev_cell_map) != 240 or len(readback_map) != 240: raise SystemExit("FAIL W705 source/readback cell coverage")
    target_rows = rjl(repo / PREV_SELECTED_TARGETS)
    target_map = {}
    for row in target_rows:
        key = (row["sourceId"], row["locale"])
        if key in target_map: raise SystemExit("FAIL duplicate W705 selected target")
        target_map[key] = row
    if len(target_map) != 5: raise SystemExit("FAIL W705 selected target count")
    previous_catalog = json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{PREV_HEAD}:{catalog_path}"]))["messages"]
    product_catalog = json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{PREV_PRODUCT}:{catalog_path}"]))["messages"]
    actual_product_changes = set()
    for sid in previous_catalog:
        for loc in LOCALES:
            if previous_catalog[sid]["translations"][loc] != product_catalog[sid]["translations"][loc]: actual_product_changes.add((sid, loc))
    if actual_product_changes != set(target_map): raise SystemExit("FAIL W705 product diff/selected target cells differ")
    if sha(catalog_raw) != prior_app.get("catalogSha256After"): raise SystemExit("FAIL current catalog differs from W705 postimage")
    if subprocess.run(["git", "-C", str(repo), "diff", "--quiet", PREV_PRODUCT, HEAD, "--", catalog_path], check=False).returncode: raise SystemExit("FAIL catalog changed after W705 product")

    current_w705_readback = []
    w705_hold_keys = set()
    for key, row in prev_cell_map.items():
        sid, loc = key; idx = row["catalogZeroBasedIndex"]; msg = msgs[sid]; rb = readback_map.get(key); target = target_map.get(key)
        if rb is None or idx not in range(705, 725) or ids[idx] != sid or sha(msg["source"]) != row["sourceSha256"]: raise SystemExit(f"FAIL W705 source/readback pin {sid}/{loc}")
        actual = sha(msg["translations"][loc])
        if rb["position"] != idx or rb["actualSha256"] != actual: raise SystemExit(f"FAIL W705 application readback {sid}/{loc}")
        if target:
            if target["position"] != idx or target["sourceSha256"] != row["sourceSha256"] or target["beforeSha256"] != row["currentTargetSha256"] or target["afterSha256"] != actual or rb["expectedSha256"] != actual or sha(target["before"]) != target["beforeSha256"] or sha(target["after"]) != actual or target["callerContextSha256"] != row["callerContextSha256"]: raise SystemExit(f"FAIL W705 selected target readback {sid}/{loc}")
            applied_rows.append({"priorWindow": PREV_WINDOW, "catalogZeroBasedIndex": idx, "sourceId": sid, "sourceSha256": row["sourceSha256"], "locale": loc, "beforeTargetSha256": target["beforeSha256"], "priorSelectedTargetSha256": actual, "currentTargetSha256": actual, "targetUnchanged": True, "applicationCommit": PREV_PRODUCT, "priorAppliedEvidenceSha256": sha(canon(target)), "textOmitted": True, "reattestedAtHead": HEAD})
        elif actual != row["currentTargetSha256"] or rb["expectedSha256"] != rb["actualSha256"]: raise SystemExit(f"FAIL unplanned W705 target change {sid}/{loc}")
        if row["callerless"]:
            if target or any(k in row for k in ("source", "sourceText", "currentTarget", "target", "targetText")): raise SystemExit("FAIL W705 callerless candidate-free text/target leak")
            w705_hold_keys.add(key)
            hold_rows.append({"window": PREV_WINDOW, "position": idx, "selectionPositionBasis": "catalog insertion index in W705-W724", "catalogZeroBasedIndex": idx, "sourceId": sid, "sourceSha256": row["sourceSha256"], "locale": loc, "priorTargetSha256": actual, "currentTargetSha256": actual, "selectionPositionMatches": True, "targetUnchanged": True, "callerless": True, "callerContextSha256": row["callerContextSha256"], "priorHoldEvidenceSha256": sha(canon({k: row[k] for k in ("window", "position", "catalogZeroBasedIndex", "sourceId", "sourceSha256", "locale", "currentTargetSha256", "callerContextSha256")})), "textOmitted": True, "reattestedAtHead": HEAD})
        current_w705_readback.append({"priorWindow": PREV_WINDOW, "position": idx, "catalogZeroBasedIndex": idx, "sourceId": sid, "sourceSha256": row["sourceSha256"], "locale": loc, "priorTargetSha256": actual, "currentTargetSha256": actual, "matchesPriorReadback": True, "targetUnchanged": True, "textOmitted": True, "callerlessHeld": bool(row["callerless"]), "reattestedAtHead": HEAD})
    if len(w705_hold_keys) != sum(r["callerless"] for r in prev_cells) or len(w705_hold_keys) != 48: raise SystemExit("FAIL W705 hash-only hold count")
    if len(applied_rows) != 132: raise SystemExit("FAIL accumulated prior applied count")
    if len(hold_rows) != 952 or len({(r["sourceId"], r["locale"]) for r in hold_rows}) != len(hold_rows): raise SystemExit("FAIL accumulated prior hold count")

    readbacks = {}
    for path in sorted(PREV_INPUT.glob("prior-*-cell-hash-reattestation.jsonl")):
        old_rows = rjl(path)
        if not old_rows: raise SystemExit(f"FAIL empty predecessor readback {path.name}")
        label = old_rows[0]["priorWindow"]
        if len(old_rows) != 240: raise SystemExit(f"FAIL predecessor readback row count {label}")
        current_rows = []
        for row in old_rows:
            sid, loc = row["sourceId"], row["locale"]; msg = msgs[sid]
            sh = sha(msg["source"]); th = sha(msg["translations"][loc])
            recorded = next((row[k] for k in ("currentTargetSha256", "actualTargetSha256", "priorTargetSha256") if k in row), None)
            idx = row.get("position", row.get("catalogZeroBasedIndex"))
            if row.get("sourceSha256") not in (None, sh) or recorded != th or idx is not None and ids[idx] != sid: raise SystemExit(f"FAIL previous readback {label} {sid}/{loc}")
            current_rows.append({"priorWindow": label, "catalogZeroBasedIndex": ids.index(sid), "sourceId": sid, "sourceSha256": sh, "locale": loc, "priorTargetSha256": recorded, "currentTargetSha256": th, "matchesPriorReadback": True, "targetUnchanged": True, "textOmitted": True, "reattestedAtHead": HEAD})
        if len({(r["sourceId"], r["locale"]) for r in current_rows}) != 240: raise SystemExit(f"FAIL previous readback duplicate cells {label}")
        readbacks[label] = current_rows
    if set(readbacks) != {"W565-W584", "W585-W604", "W605-W624", "W625-W644", "W645-W664", "W665-W684", "W685-W704"}: raise SystemExit("FAIL prior seven readback windows")
    readbacks[PREV_WINDOW] = current_w705_readback

    # Retain prior provenance notes, correcting the W665 evidence status using the restoration commit.
    prior_lineage = rj(PREV_INPUT / "prior-window-lineage.json")
    w625 = prior_lineage.get("w625EvidenceCaveat", {})
    w645 = prior_lineage.get("w645BlindSummaryPinWarning", {})
    if w625.get("missingFromPriorCommittedPrTree") != 31 or not w625.get("matchesFinalVerifier"): raise SystemExit("FAIL W625 lineage caveat")
    if not w645.get("blindChecksumMismatchRecorded") or w645.get("crossReviewResult") != "PASS_WITH_BLIND_SUMMARY_PIN_WARNING": raise SystemExit("FAIL W645 lineage warning")
    w665_restoration = prior_lineage.get("w665EvidenceRestoration", {})
    old_w665 = prior_lineage["w665LatestWindow"]
    if w665_restoration.get("restorationCommit") != PREV_HEAD or w665_restoration.get("currentEvidenceIndexEntries") != 77 or not w665_restoration.get("allCurrentIndexedPayloadsPresentAndHashMatched"):
        raise SystemExit("FAIL W665 restoration provenance pin")
    if subprocess.run(["git", "-C", str(repo), "diff", "--quiet", PREV_HEAD, HEAD, "--", W665_EVIDENCE_REL.as_posix()], check=False).returncode:
        raise SystemExit("FAIL W665 evidence changed after its verified restoration")
    w665_index_entries = w665_restoration["currentEvidenceIndexEntries"]
    w665_latest = {k: old_w665[k] for k in ("head", "tree", "productCommit", "productTree", "appliedTargetCells", "holdCells")}
    w665_latest.update({"evidenceIndexEntries": w665_index_entries, "evidenceIndexMissingFiles": 0, "evidenceIndexMismatchedFiles": 0, "evidenceRestoredAtCurrentHead": True, "restorationCommit": w665_restoration["restorationCommit"]})

    # Reattest W705 source/caller signatures after subsequent evidence-only commits.
    w705_context_rows = []
    for row in prev_selected:
        sid = row["sourceId"]; old = prev_contexts[sid]; msg = msgs[sid]
        new = match_context({"sourceId": sid, "source": msg["source"], "sourceSha256": sha(msg["source"])}, production, HEAD)
        if old["callerless"] != new["callerless"] or old["exactMatchCount"] != new["exactMatchCount"] or signature(old) != signature(new): raise SystemExit(f"FAIL W705 caller context drift {sid}")
        w705_context_rows.append({"sourceId": sid, "sourceSha256": sha(msg["source"]), "priorCallerContextSha256": old["contextSha256"], "currentCallerContextSha256": new["contextSha256"], "callerless": new["callerless"], "exactMatchCount": new["exactMatchCount"], "callerSignaturesUnchanged": True, "sourceTextOmitted": True, "callerTextOmitted": new["callerless"]})

    # Pin every tracked production source plus the three source/catalog inputs.
    catalog_path_set = {catalog_path, registry_path, snapshot_path}
    pin_rows = []
    for rel in sorted(set(production) | catalog_path_set):
        raw = (repo / rel).read_bytes(); pin_rows.append({"path": rel, "fileSha256": sha(raw), "gitBlob": git(repo, "rev-parse", f"{HEAD}:{rel}"), "bytes": len(raw)})
    old_pins = {r["path"]: r for r in rj(PREV_INPUT / "source-file-pins.json")["files"]}
    for row in pin_rows:
        if row["path"] in old_pins and row["path"] != catalog_path and (row["fileSha256"], row["gitBlob"]) != (old_pins[row["path"]]["fileSha256"], old_pins[row["path"]]["gitBlob"]): raise SystemExit(f"FAIL production/source file drift since W705: {row['path']}")
    if any(p not in {r["path"] for r in pin_rows} for p in old_pins if p != catalog_path): raise SystemExit("FAIL predecessor source file disappeared")

    selected = []
    for idx in range(725, 745):
        sid = ids[idx]; msg = msgs[sid]; sh = sha(msg["source"])
        if msg.get("sourceHash") != sh: raise SystemExit(f"FAIL source hash at catalog index {idx}")
        selected.append({"position": idx, "catalogZeroBasedIndex": idx, "catalogOneBasedPosition": idx+1, "sourceId": sid, "sourceSha256": sh, "activeSourceRegistry": sid in registry, "activeSourceRank": active_rank.get(sid), "registryLocations": registry.get(sid, {}).get("locations", []), "_source": msg["source"]})
    if len({r["sourceId"] for r in selected}) != 20 or {r["sourceId"] for r in selected} & {r["sourceId"] for r in selection_rows}: raise SystemExit("FAIL W725 selection uniqueness/overlap")
    contexts = [match_context({"sourceId": r["sourceId"], "source": r["_source"], "sourceSha256": r["sourceSha256"]}, production, HEAD) for r in selected]
    ctxmap = {r["sourceId"]: r for r in contexts}
    selected_public = []
    for row in selected:
        item = {k: v for k, v in row.items() if k != "_source"}
        if ctxmap[row["sourceId"]]["callerless"]: item["sourceTextOmitted"] = True
        else: item["source"] = row["_source"]
        selected_public.append(item)
    boundary = []
    for idx, role in ((724, "catalog-before-selected-start"), (725, "selected-start"), (744, "selected-end"), (745, "catalog-after-selected-end")):
        sid = ids[idx]; boundary.append({"position": idx, "catalogZeroBasedIndex": idx, "sourceId": sid, "sourceSha256": sha(msgs[sid]["source"]), "role": role, "sourceTextOmitted": True})

    cells = []; mismatch = collections.Counter()
    for item in selected:
        sid = item["sourceId"]; msg = msgs[sid]; src = msg["source"]; ctx = ctxmap[sid]
        for loc in LOCALES:
            target = msg.get("translations", {}).get(loc)
            if not isinstance(target, str) or not target: mismatch["missingTarget"] += 1; target = ""
            tok = token_rows(src, target)
            mismatch["placeholder"] += not tok["placeholderMultisetMatches"]
            mismatch["markup"] += not tok["markupMatches"]
            mismatch["numeric"] += not tok["numericTokensPreserved"]
            mismatch["numericPresentationDifferences"] += tok["numericPresentationEquivalent"]
            mismatch["protectedLiteral"] += not tok["protectedLiteralsPreserved"]
            cell = {"window": WINDOW, "position": item["position"], "catalogZeroBasedIndex": item["catalogZeroBasedIndex"], "catalogOneBasedPosition": item["catalogOneBasedPosition"], "sourceId": sid, "sourceSha256": item["sourceSha256"], "locale": loc, "callerContextSha256": ctx["contextSha256"], "literalCallerCount": ctx["exactMatchCount"], "callerless": ctx["callerless"], "candidateFree": True, "currentTargetSha256": sha(target)}
            if ctx["callerless"]: cell.update({"cellDisposition": "hold-callerless-hash-only", "sourceTextOmitted": True, "currentTargetTextOmitted": True})
            else: cell.update({"source": src, "currentTarget": target, **tok, "catalogTranslationHash": msg.get("translationHashes", {}).get(loc), "translationStatus": msg.get("translationStatus", {}).get(loc)})
            cells.append(cell)
    if len(cells) != 240: raise SystemExit("FAIL W725 cell count")

    # Compare exact source and caller context against live main.
    main_head = api0["baseLiveRefOid"]
    main_tree = git(repo, "rev-parse", f"{main_head}^{{tree}}")
    main_msgs = json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{main_head}:{catalog_path}"]))["messages"]
    main_files = {p: file_tuple(repo, p, main_head) for p in production_paths(repo, main_head)}
    drift = []
    sig_simple = lambda c: {(r["path"], r["matchKind"], r["lineText"].strip()) for r in c["callers"]}
    for item, pr_ctx in zip(selected, contexts):
        msg = main_msgs.get(item["sourceId"]); source = msg.get("source") if isinstance(msg, dict) else None; source_hash = sha(source) if isinstance(source, str) else None
        main_ctx = match_context({"sourceId": item["sourceId"], "source": source, "sourceSha256": source_hash}, main_files, main_head) if isinstance(source, str) else {"callerless": True, "callers": [], "exactMatchCount": 0}
        added = sorted(sig_simple(main_ctx) - sig_simple(pr_ctx)); removed = sorted(sig_simple(pr_ctx) - sig_simple(main_ctx))
        drift.append({"sourceId": item["sourceId"], "prSourceSha256": item["sourceSha256"], "mainSourcePresent": isinstance(source, str), "mainSourceSha256": source_hash, "sourceSame": source_hash == item["sourceSha256"], "prCallerCount": pr_ctx["exactMatchCount"], "mainCallerCount": main_ctx["exactMatchCount"], "prCallerless": pr_ctx["callerless"], "mainCallerless": main_ctx["callerless"], "newMainCallerSignatures": [{"path": x[0], "matchKind": x[1], "lineText": x[2]} for x in added], "prOnlyCallerSignatures": [{"path": x[0], "matchKind": x[1], "lineText": x[2]} for x in removed], "contextDrift": source_hash != item["sourceSha256"] or bool(added) or bool(removed) or pr_ctx["exactMatchCount"] != main_ctx["exactMatchCount"]})
    main_drift = {"repository": "snapetech-org/ROMarrNG", "prHead": HEAD, "prTree": TREE, "mainHead": main_head, "mainTree": main_tree, "baseApiSha": api0["baseApiSha"], "baseApiRefMismatch": api0["baseApiRefMismatch"], "comparison": "same stable source IDs and exact quoted source/source-ID/HTML text searches over tracked production files under romarr; tests, docs, catalogs, and workflows excluded", "selectedSourceCount": 20, "sourcesMissingFromMain": sum(not r["mainSourcePresent"] for r in drift), "sourceTextChanges": sum(not r["sourceSame"] for r in drift), "sourcesWithCallerContextDrift": sum(r["contextDrift"] for r in drift), "sourcesWithNewMainCallers": sum(bool(r["newMainCallerSignatures"]) for r in drift), "results": drift}

    # Write candidate-free packet. Callerless rows remain hashes/positions/locales only.
    wj(inp/"PR-attestation-before.json", api0)
    wjl(inp/"catalog-key-order.jsonl", [{"catalogZeroBasedIndex": i, "sourceId": sid, "sourceSha256": sha(msgs[sid]["source"])} for i, sid in enumerate(ids)])
    wj(inp/"source-registry-redacted.json", {"sourceQueuePath": registry_path, "sourceQueueSha256": source_queue_sha, "sourceSnapshotPath": snapshot_path, "sourceSnapshotSha256": source_snapshot_sha, "activeSourceCount": len(registry), "messages": [{k: v for k, v in row.items() if k != "source"} for row in registry_rows]})
    wj(inp/"source-snapshot-hashes.json", snapshot)
    wj(inp/"catalog-file-pins.json", {"head": HEAD, "tree": TREE, "catalogPath": catalog_path, "catalogSha256": sha(catalog_raw), "catalogGitBlob": git(repo, "rev-parse", f"{HEAD}:{catalog_path}"), "catalogMessageCount": len(msgs), "catalogKeyOrderSha256": cat_order_sha, "sourceQueuePath": registry_path, "sourceQueueSha256": source_queue_sha, "sourceSnapshotPath": snapshot_path, "sourceSnapshotSha256": source_snapshot_sha, "sourceIdOrderSha256": id_order_sha, "activeUniqueSourceIds": len(registry)})
    wj(inp/"source-file-pins.json", {"head": HEAD, "tree": TREE, "files": pin_rows})
    wjl(inp/"selected-sources.jsonl", selected_public); wjl(inp/"selection-boundary.jsonl", boundary)
    wjl(inp/"source-contexts.jsonl", [safe_context(c) for c in contexts])
    wj(inp/"caller-search-audit.json", {"head": HEAD, "tree": TREE, "queryCount": 20, "searchScope": "tracked production source files under romarr; tests, docs, locale catalogs, and workflows excluded", "productionFilesSearched": len(production), "callerlessSourceCount": sum(c["callerless"] for c in contexts), "callerlessCellCount": 12*sum(c["callerless"] for c in contexts), "results": [{"sourceId": c["sourceId"], "sourceSha256": c["sourceSha256"], "matchCount": c["exactMatchCount"], "callerless": c["callerless"], "contextSha256": c["contextSha256"], "sourceTextOmitted": c["callerless"]} for c in contexts]})
    wjl(inp/"candidate-free-cells.jsonl", cells); wj(inp/"candidate-free-token-summary.json", dict(mismatch)); wj(inp/"main-context-drift.json", main_drift)
    wjl(inp/"prior-selection-reattestation.jsonl", selection_rows); wj(inp/"prior-selection-reattestation-summary.json", {"windows": dict(collections.Counter(r["priorWindow"] for r in selection_rows)), "count": len(selection_rows), "allSelectionsMatchCurrentCatalogAndRegistry": True, "head": HEAD, "tree": TREE})
    wjl(inp/"prior-hold-reattestation.jsonl", hold_rows); wj(inp/"prior-hold-reattestation-summary.json", {"count": len(hold_rows), "windows": dict(collections.Counter(r["window"] for r in hold_rows)), "allTargetHashesMatch": True, "changedTargets": 0, "textInHoldRows": False, "head": HEAD, "tree": TREE})
    wjl(inp/"prior-hold-context-reattestation.jsonl", prior_hold_contexts)
    wjl(inp/"prior-applied-cell-reattestation.jsonl", applied_rows); wj(inp/"prior-applied-cell-reattestation-summary.json", {"count": len(applied_rows), "windows": dict(collections.Counter(r["priorWindow"] for r in applied_rows)), "allFinalTargetHashesMatch": True, "changedTargets": 0, "head": HEAD, "tree": TREE})
    for label, rows in readbacks.items():
        slug = label.lower().replace("-", "")
        wjl(inp / f"prior-{slug}-cell-hash-reattestation.jsonl", rows)
    wjl(inp/"w705-current-context-reattestation.jsonl", w705_context_rows)
    wj(inp/"w705-current-context-reattestation-summary.json", {"head": HEAD, "priorHead": PREV_HEAD, "priorTree": PREV_TREE, "sourceCount": 20, "allCallerSignaturesUnchanged": True})
    wj(inp/"prior-window-lineage.json", {"result": "PASS", "currentHead": HEAD, "currentTree": TREE, "previousCandidateFreeHead": PREV_HEAD, "previousCandidateFreeTree": PREV_TREE, "previousProductCommit": PREV_PRODUCT, "previousProductTree": PREV_PRODUCT_TREE, "previousSourceSelectionsReattested": len(selection_rows), "previousHeldCellsReattested": len(hold_rows), "previousAppliedCellsReattested": len(applied_rows), "previousReadbackWindows": {k: len(v) for k, v in readbacks.items()}, "currentCallerlessStatusCheckedForPriorHeldSources": len(prior_hold_contexts), "priorHoldSourcesWithCurrentCallers": sum(not r["callerlessAtCurrentHead"] for r in prior_hold_contexts), "w705CallerContextsReattested": len(w705_context_rows), "w705CallerContextsUnchanged": all(r["callerSignaturesUnchanged"] for r in w705_context_rows), "w705CallerlessHashOnlyHolds": len(w705_hold_keys), "w705AppliedTargetCells": len(target_map), "w665LatestWindow": w665_latest, "w665EvidenceRestoration": w665_restoration, "w625EvidenceCaveat": w625, "w645BlindSummaryPinWarning": w645, "priorPacketPins": {"candidateFreeManifestSha256": sha((PREV_INPUT/"manifest.json").read_bytes()), "candidateFreeChecksumListSha256": sha((PREV_INPUT/"SHA256SUMS.txt").read_bytes()), "w705ApplicationSummarySha256": sha((repo/PREV_APP_SUMMARY).read_bytes()), "w705FinalReadbackSha256": sha((repo/PREV_FINAL_READBACK).read_bytes()), "w705SelectedTargetsSha256": sha((repo/PREV_SELECTED_TARGETS).read_bytes()), "w705ProductCommit": PREV_PRODUCT, "previousCandidateFreeChecksumsVerified": True}, "previousWindowSelectionCounts": dict(collections.Counter(r["priorWindow"] for r in selection_rows)), "previousWindowHoldCounts": dict(collections.Counter(r["window"] for r in hold_rows)), "previousWindowAppliedCellCounts": dict(collections.Counter(r["priorWindow"] for r in applied_rows)), "callerlessHoldTextIncluded": False, "currentWindowReviewDecisionsIncluded": False, "currentWindowProposalTextIncluded": False})
    wj(inp/"selection.json", {"window": WINDOW, "method": "Select catalog message insertion indices 725 through 744 (zero-based) from the exact pinned romarr/ui-labels.json message-key order.", "positions": [725, 744], "catalogOneBasedPositions": [726, 745], "sourceCount": 20, "localeCount": 12, "cellCount": 240, "localeOrder": LOCALES, "activeUniqueSourceIds": len(registry), "sourceIdOrderSha256": id_order_sha, "catalogMessageCount": len(msgs), "catalogKeyOrderSha256": cat_order_sha, "selectedSources": selected_public})
    wj(inp/"registry-order-note.json", {"selectionBasis": "catalog JSON message-key insertion order", "selectedCatalogZeroBasedIndices": [725, 744], "activeRegistryCount": len(registry), "selectedIdsInActiveRegistry": sum(r["activeSourceRegistry"] for r in selected), "activeRegistryMatches": [{"sourceId": r["sourceId"], "activeRank": r["activeSourceRank"], "registryLocations": r["registryLocations"]} for r in selected if r["activeSourceRegistry"]], "lineHintCaveat": "Active source registry metadata does not substitute for exact literal caller search and excerpt evidence."})
    wj(inp/"prior-application-source-pin.json", {"sourceHead": PREV_HEAD, "sourceTree": PREV_TREE, "productCommit": PREV_PRODUCT, "productTree": PREV_PRODUCT_TREE, "productParent": PREV_HEAD, "currentHead": HEAD, "currentTree": TREE, "productCommitAncestor": True, "currentCatalogPostimageSha256": sha(catalog_raw), "applicationSummaryPath": PREV_APP_SUMMARY.as_posix(), "applicationSummarySha256": sha((repo/PREV_APP_SUMMARY).read_bytes()), "finalReadbackPath": PREV_FINAL_READBACK.as_posix(), "finalReadbackSha256": sha((repo/PREV_FINAL_READBACK).read_bytes()), "selectedTargetsPath": PREV_SELECTED_TARGETS.as_posix(), "selectedTargetsSha256": sha((repo/PREV_SELECTED_TARGETS).read_bytes()), "applicationCellCount": len(target_map), "applicationCellHashesReattested": True})

    api1 = attestation(repo)
    keys = ("state", "draft", "merged", "headRefName", "head", "tree", "apiCommitTree", "branchRefOid", "pullRefOid", "baseRefName", "baseApiSha", "baseLiveRefOid", "bodySha256", "bodyBytes")
    if any(api0[k] != api1[k] for k in keys): raise SystemExit("FAIL PR/API/head/body changed during extraction")
    wj(inp/"PR-attestation-after-candidate-free.json", api1)
    if git(repo, "rev-parse", "HEAD") != HEAD or git(repo, "rev-parse", "HEAD^{tree}") != TREE or git(repo, "status", "--porcelain=v1", "--untracked-files=all"): raise SystemExit("FAIL source worktree changed during extraction")
    manifest = {"artifact": "ROMarrNG PR #70 W725-W744 candidate-free input", "repository": "snapetech-org/ROMarrNG", "pullRequest": 70, "branch": BRANCH, "baseRefName": api0["baseRefName"], "head": HEAD, "tree": TREE, "window": WINDOW, "selectionBasis": "catalog insertion order; exact ui-labels.json indices 725..744", "sourceCount": 20, "localeCount": 12, "cellCount": 240, "locales": LOCALES, "activeUniqueSourceIdCount": len(registry), "sourceIdOrderSha256": id_order_sha, "catalogMessageCount": len(msgs), "catalogPath": catalog_path, "catalogSha256": sha(catalog_raw), "catalogGitBlob": git(repo, "rev-parse", f"{HEAD}:{catalog_path}"), "catalogKeyOrderSha256": cat_order_sha, "sourceQueuePath": registry_path, "sourceQueueSha256": source_queue_sha, "sourceSnapshotSha256": source_snapshot_sha, "priorSelectedSourceCount": len(selection_rows), "priorSelectionsUnchanged": True, "priorHoldCellCount": len(hold_rows), "priorHoldTargetsUnchanged": True, "priorHoldCellChangedCount": 0, "priorAppliedSelectedCellCount": len(applied_rows), "priorAppliedTargetsUnchanged": True, "priorFullWindowReadbackCounts": {k: len(v) for k, v in readbacks.items()}, "priorW625EvidenceIndexMissingFromPrTreeCount": 31, "priorW625ReadbackSha256MatchedFinalVerifier": True, "priorW645BlindSummaryPinWarningPreserved": True, "priorW665EvidenceIndexEntries": w665_index_entries, "priorW665EvidenceIndexMissingFiles": 0, "priorW665EvidenceIndexMismatches": 0, "priorW665EvidenceRestored": True, "callerlessSourceCount": sum(c["callerless"] for c in contexts), "callerlessCurrentTargetCellCount": 12*sum(c["callerless"] for c in contexts), "callerContextCount": len(contexts), "directCallerRefCount": sum(c["exactMatchCount"] for c in contexts), "currentTargetPlaceholderMismatches": mismatch["placeholder"], "currentTargetMarkupMismatches": mismatch["markup"], "currentTargetNumericMismatches": mismatch["numeric"], "currentTargetNumericPresentationDifferences": mismatch["numericPresentationDifferences"], "currentTargetProtectedLiteralMismatches": mismatch["protectedLiteral"], "currentTargetMissingCells": mismatch["missingTarget"], "mainHead": main_head, "mainTree": main_tree, "mainSourcesMissing": main_drift["sourcesMissingFromMain"], "mainSourceTextChanges": main_drift["sourceTextChanges"], "mainContextDriftCount": main_drift["sourcesWithCallerContextDrift"], "candidateFree": True, "proposedTargetsIncluded": False, "reviewDecisionsIncluded": False, "callerlessCellTextIncluded": False, "createdUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "reviewBoundary": "Candidate-free extraction only. Caller-backed cells include exact source/current-target text and caller context hashes; callerless cells remain hash-only with no source or target text. Prior selections, holds, applied targets and eight 240-cell readback windows through W705-W724 are reattested at this exact head. W625 and W645 provenance notes are preserved; W665 evidence payloads previously missing from its index are restored and all 77 current indexed payloads hash-match."}
    wj(inp/"manifest.json", manifest)
    (out/"README.md").write_text(f"""# ROMarrNG PR #70 W725–W744 candidate-free packet

Pinned to open draft PR head `{HEAD}`, tree `{TREE}`, branch `{BRANCH}`. It selects catalog insertion indices 725–744 (one-based positions 726–745): 20 source keys and 240 locale cells across 12 direct locales.

This packet contains source, caller, and current-target text only for caller-backed keys. Its {manifest['callerlessCurrentTargetCellCount']} callerless locale cells are hash-only; source and target text are omitted. It contains no proposal or review decision for W725–W744.

The packet reattests {len(selection_rows)} prior source selections, {len(hold_rows)} held cells, {len(applied_rows)} applied cells, and eight complete 240-cell readback windows through W705–W724. It carries forward the W625 missing-stage-file/readback caveat and W645 stale blind checksum-pointer warning. W665’s prior evidence gap remains verified at the pinned restoration commit and is unchanged in this history: its 77 indexed payloads are all present and hash-matching after the restoration commit; 23 payloads were restored byte-for-byte and the root ledger was reconstructed from the verified cross-review ledger. The carried W665 attestation was preserved without opening its blind-review payloads.

The packet records exact source-file, registry, snapshot, catalog, caller, and live PR pins before and after extraction. No repository, catalog, PR, or workflow files were changed. No tests, builds, scans, or CI were run.

Run `python3 verify_candidate_free.py` for portable packet checks, or add `--repo /path/to/the-exact-head-worktree` to recheck local Git and catalog data.
""", encoding="utf-8")
    write_sums(inp); write_sums(out)
    print(json.dumps({"result": "CANDIDATE_FREE_DATA_BUILT", "head": HEAD, "tree": TREE, "window": WINDOW, "selectedSources": len(selected), "cells": len(cells), "callerlessSources": sum(c["callerless"] for c in contexts), "callerlessCells": 12*sum(c["callerless"] for c in contexts), "directCallerRefs": sum(c["exactMatchCount"] for c in contexts), "tokenMismatches": dict(mismatch), "priorSelectedSources": len(selection_rows), "priorHoldCells": len(hold_rows), "priorAppliedCells": len(applied_rows), "priorReadbackCounts": {k: len(v) for k, v in readbacks.items()}, "w665RestoredPayloads": w665_index_entries, "mainContextDrift": {"missing": main_drift["sourcesMissingFromMain"], "sourceChanged": main_drift["sourceTextChanges"], "contextDrift": main_drift["sourcesWithCallerContextDrift"]}}, ensure_ascii=False, sort_keys=True))
if __name__ == "__main__": main()
