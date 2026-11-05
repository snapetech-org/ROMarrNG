#!/usr/bin/env python3
"""Exact-hash application and complete 240-cell readback for ROMarrNG W705-W724."""

from __future__ import annotations

import collections
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
WINDOW = HERE.parent
REPO = HERE.parents[4]
CF_DIR = WINDOW / "candidate-free" / "input"
CROSS = WINDOW / "cross-review" / "cross-ledger.jsonl"
ROOT_DECISIONS = WINDOW / "root-adjudication" / "root-adjudication-decisions.jsonl"
SELECTED_TARGETS = HERE / "selected-targets.jsonl"
PLAN = HERE / "exact-hash-apply-plan.jsonl"
LEDGER = HERE / "root-final-review-ledger.jsonl"
PREFLIGHT = HERE / "preflight.json"
PINS = HERE / "input-pins.json"
READBACK = HERE / "final-head-readback.jsonl"
SUMMARY = HERE / "application-summary.json"
CATALOG_PATH = "romarr/ui-labels.json"
INPUT_HEAD = "50e3f8a48a800affff8bad367b5c493cc0fdfd62"
INPUT_TREE = "22cd46ff4821fcbbe76b4760a15e22d688b3f548"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

ROOT_FINAL = {
    (709, "ar"): {
        "target": "لا تتوفر أي صيغ للواجهة الأمامية.",
        "proposalSource": "blind",
        "rationale": "The confirmed caller renders this only when the frontend export-format list is empty. The current text says display formats; the blind proposal explicitly names software frontend formats.",
        "confidence": "moderate",
    },
    (709, "fr"): {
        "target": "Aucun format frontend n’est disponible.",
        "proposalSource": "blind",
        "rationale": "The caller concerns frontend export formats. Frontal is ambiguous in French; the blind wording names the technical frontend concept and forms a complete, natural status sentence.",
        "confidence": "moderate",
    },
    (711, "id"): {
        "target": "Tidak ada game yang dikembalikan oleh pustaka.",
        "proposalSource": "primary",
        "rationale": "The empty-state branch appears when the library returns no games. The current wording says the library does not display games; the primary proposal states that no games were returned.",
        "confidence": "moderate",
    },
}


def sha(value: str | bytes) -> str:
    payload = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(payload).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values), encoding="utf-8")


def git_show(head: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{head}:{path}"], cwd=REPO)


def token_check(source: str, target: str, protected: list[str]) -> bool:
    patterns = [
        r"\{[^{}]+\}",
        r"<[^>]+>",
        r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?(?![A-Za-z0-9])",
    ]
    return all(collections.Counter(re.findall(pattern, source)) == collections.Counter(re.findall(pattern, target)) for pattern in patterns) and all(literal in target for literal in protected)


def main() -> int:
    mode = "verify" if "--verify-only" in sys.argv else "apply" if "--apply" in sys.argv else "preflight"
    cf_manifest = json.loads((CF_DIR / "manifest.json").read_text(encoding="utf-8"))
    cross_rows = read_jsonl(CROSS)
    cross_manifest = json.loads((WINDOW / "cross-review" / "manifest.json").read_text(encoding="utf-8"))
    candidate_rows = read_jsonl(CF_DIR / "candidate-free-cells.jsonl")
    if len(cross_rows) != 240 or len(candidate_rows) != 240:
        raise SystemExit("expected exactly 240 candidate-free and cross-review cells")
    if cf_manifest["head"] != INPUT_HEAD or cf_manifest["tree"] != INPUT_TREE:
        raise SystemExit("candidate-free head/tree mismatch")
    if cross_manifest["exactHead"] != INPUT_HEAD or cross_manifest["exactTree"] != INPUT_TREE:
        raise SystemExit("cross-review manifest does not match the pinned input head/tree")
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if mode != "verify" and current_head != INPUT_HEAD:
        raise SystemExit(f"pre-apply HEAD mismatch: {current_head} != {INPUT_HEAD}")
    # The evidence packet is untracked until its documentation commit; all tracked inputs must remain clean.
    if mode != "verify" and (subprocess.run(["git", "diff", "--quiet"], cwd=REPO).returncode != 0 or subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO).returncode != 0):
        raise SystemExit("tracked worktree/index changes exist before catalog application")

    cf_by_key = {(row["position"], row["locale"]): row for row in candidate_rows}
    cross_by_key = {(row["position"], row["locale"]): row for row in cross_rows}
    if len(cf_by_key) != 240 or len(cross_by_key) != 240:
        raise SystemExit("duplicate cell identities in source evidence")
    if set(cf_by_key) != set(cross_by_key):
        raise SystemExit("candidate-free and cross-review identities differ")

    root_decision_rows = []
    for key, choice in ROOT_FINAL.items():
        cross = cross_by_key[key]
        candidate = cf_by_key[key]
        if not cross.get("rootAdjudicationRequired") or cross.get("callerless"):
            raise SystemExit(f"root decision does not bind to a flagged caller-backed cell: {key}")
        if cross.get("decision") != "correction":
            raise SystemExit(f"cross-review did not identify a correction for root cell {key}")
        expected_proposal = cross.get("blindTarget") if choice["proposalSource"] == "blind" else cross.get("primaryTarget")
        if expected_proposal != choice["target"]:
            raise SystemExit(f"root target differs from selected review proposal for {key}")
        if candidate.get("currentTarget") != cross.get("currentTarget") or candidate.get("currentTargetSha256") != cross.get("currentTargetSha256"):
            raise SystemExit(f"candidate-free/current-cell mismatch for {key}")
        if sha(choice["target"]) != cross["selectedTargetSha256"]:
            raise SystemExit(f"root selected target digest mismatch for {key}")
        if not token_check(candidate["source"], choice["target"], candidate.get("sourceProtectedLiterals", [])):
            raise SystemExit(f"root target token check failed for {key}")
        root_decision_rows.append({
            "position": key[0],
            "locale": key[1],
            "sourceId": cross["sourceId"],
            "source": candidate["source"],
            "sourceSha256": candidate["sourceSha256"],
            "currentTarget": candidate["currentTarget"],
            "currentTargetSha256": candidate["currentTargetSha256"],
            "rootTarget": choice["target"],
            "rootTargetSha256": sha(choice["target"]),
            "proposalSource": choice["proposalSource"],
            "rootRationale": choice["rationale"],
            "rootDisposition": "correction",
            "rootAdjudicationPerformed": True,
            "confidence": choice["confidence"],
            "callerContextSha256": candidate["callerContextSha256"],
        })
    if len(root_decision_rows) != 3:
        raise SystemExit("expected three final root-adjudication decisions")

    final_rows: list[dict[str, Any]] = []
    plan: list[dict[str, Any]] = []
    selected_targets: list[dict[str, Any]] = []
    root_by_key = {(row["position"], row["locale"]): row for row in root_decision_rows}
    for key in sorted(cross_by_key):
        cross = cross_by_key[key]
        candidate = cf_by_key[key]
        callerless = bool(cross.get("callerless"))
        if candidate.get("sourceId") != cross.get("sourceId") or candidate.get("sourceSha256") != cross.get("sourceSha256"):
            raise SystemExit(f"source identity mismatch at {key}")
        source_id = cross["sourceId"]
        locale = cross["locale"]
        before_hash = cross["currentTargetSha256"]
        if callerless:
            if "source" in candidate or "currentTarget" in candidate or "source" in cross or "currentTarget" in cross:
                raise SystemExit(f"callerless text was unexpectedly exposed in evidence at {key}")
            final_target = None
            final_hash = before_hash
            disposition = "hold-callerless-hash-only"
        else:
            source = candidate.get("source")
            before = candidate.get("currentTarget")
            if not isinstance(source, str) or not isinstance(before, str):
                raise SystemExit(f"caller-backed text missing at {key}")
            if sha(source) != candidate["sourceSha256"] or sha(before) != before_hash:
                raise SystemExit(f"candidate-free source/current hash mismatch at {key}")
            if cross.get("source") != source or cross.get("currentTarget") != before:
                raise SystemExit(f"cross-review source/current mismatch at {key}")
            if cross.get("decision") == "correction":
                if key in root_by_key:
                    final_target = root_by_key[key]["rootTarget"]
                    final_hash = root_by_key[key]["rootTargetSha256"]
                    disposition = "correction"
                    rationale = root_by_key[key]["rootRationale"]
                    basis = "root-adjudication"
                    confidence = root_by_key[key]["confidence"]
                else:
                    final_target = cross["selectedTarget"]
                    final_hash = cross["selectedTargetSha256"]
                    disposition = "correction"
                    rationale = cross["selectionRationale"]
                    basis = cross.get("selectionSource")
                    confidence = cross.get("confidence")
                if not token_check(source, final_target, candidate.get("sourceProtectedLiterals", [])):
                    raise SystemExit(f"selected target token check failed at {key}")
                if sha(final_target) != final_hash:
                    raise SystemExit(f"selected target hash mismatch at {key}")
            elif cross.get("decision") == "accept-current":
                final_target = before
                final_hash = before_hash
                disposition = "accept-current"
                rationale = "Cross-review retained the current target."
                basis = None
                confidence = cross.get("confidence")
            else:
                raise SystemExit(f"unsupported caller-backed cross decision at {key}")
        final_row = {
            "position": key[0],
            "locale": locale,
            "sourceId": source_id,
            "sourceSha256": cross.get("sourceSha256"),
            "callerless": callerless,
            "callerContextSha256": cross.get("callerContextSha256"),
            "beforeSha256": before_hash,
            "afterSha256": final_hash,
            "disposition": disposition,
            "rootAdjudicationRequired": bool(cross.get("rootAdjudicationRequired")),
            "rootAdjudicationPerformed": key in root_by_key,
            "selectionBasis": basis if not callerless else None,
            "rationale": rationale if not callerless else "Callerless catalog cell retained as a text-free hash-only hold.",
        }
        if not callerless:
            final_row.update({"source": source, "before": before, "after": final_target})
        final_rows.append(final_row)
        if disposition == "correction":
            edit = {
                "position": key[0],
                "locale": locale,
                "sourceId": source_id,
                "source": source,
                "sourceSha256": cross["sourceSha256"],
                "before": before,
                "beforeSha256": before_hash,
                "after": final_target,
                "afterSha256": final_hash,
                "catalogPath": CATALOG_PATH,
                "selectionBasis": basis,
                "rationale": rationale,
                "confidence": confidence,
                "callerContextSha256": cross.get("callerContextSha256"),
            }
            plan.append(edit)
            selected_targets.append(edit.copy())

    if len(plan) != 5 or sum(r["disposition"] == "hold-callerless-hash-only" for r in final_rows) != 48:
        raise SystemExit("expected 5 exact edits and 48 unchanged hash-only holds")
    pins = {
        "window": "W705-W724",
        "inputHead": INPUT_HEAD,
        "inputTree": INPUT_TREE,
        "catalogPath": CATALOG_PATH,
        "messageCount": 1836,
        "localeCount": 12,
        "reviewedCells": 240,
        "callerBackedCells": 192,
        "callerlessHashOnlyHolds": 48,
        "rootAdjudicationCount": 3,
        "selectedCorrections": len(plan),
        "acceptedCurrent": 187,
        "locales": LOCALES,
    }

    baseline_bytes = git_show(INPUT_HEAD, CATALOG_PATH)
    if sha(baseline_bytes) != cf_manifest["catalogSha256"]:
        raise SystemExit("pinned catalog blob/hash mismatch")
    baseline_data = json.loads(baseline_bytes.decode("utf-8"))
    if (json.dumps(baseline_data, ensure_ascii=False, indent=2) + "\n").encode("utf-8") != baseline_bytes:
        raise SystemExit("catalog JSON serialization differs from canonical two-space form")
    if len(baseline_data["messages"]) != 1836:
        raise SystemExit("pinned source catalog no longer has 1,836 messages")
    expected = copy.deepcopy(baseline_data)
    for row in candidate_rows:
        message = expected["messages"][row["sourceId"]]
        if row["locale"] not in message["translations"]:
            raise SystemExit(f"locale translation absent at {(row['position'], row['locale'])}")
        actual = message["translations"][row["locale"]]
        if row.get("callerless"):
            if sha(actual) != cross_by_key[(row["position"], row["locale"])]["currentTargetSha256"]:
                raise SystemExit(f"callerless current hash mismatch at {(row['position'], row['locale'])}")
        else:
            if actual != row["currentTarget"] or sha(actual) != row["currentTargetSha256"]:
                raise SystemExit(f"caller-backed current-value mismatch at {(row['position'], row['locale'])}")
    for edit in plan:
        translation = expected["messages"][edit["sourceId"]]["translations"]
        if translation[edit["locale"]] != edit["before"] or sha(translation[edit["locale"]]) != edit["beforeSha256"]:
            raise SystemExit(f"exact-hash guard failed at {(edit['position'], edit['locale'])}")
        translation[edit["locale"]] = edit["after"]

    if mode == "verify":
        if read_jsonl(ROOT_DECISIONS) != root_decision_rows or read_jsonl(SELECTED_TARGETS) != selected_targets or read_jsonl(PLAN) != plan or read_jsonl(LEDGER) != final_rows:
            raise SystemExit("recorded root/application decisions differ from regenerated exact inputs")
        actual_bytes = (REPO / CATALOG_PATH).read_bytes()
        expected_bytes = (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if actual_bytes != expected_bytes:
            raise SystemExit("complete catalog readback differs from pinned parent plus exact plan")
        readback = []
        for row in final_rows:
            value = expected["messages"][row["sourceId"]]["translations"][row["locale"]]
            actual_hash = sha(value)
            if actual_hash != row["afterSha256"]:
                raise SystemExit(f"final readback hash mismatch at {(row['position'], row['locale'])}")
            item = {"position": row["position"], "locale": row["locale"], "sourceId": row["sourceId"], "callerless": row["callerless"], "expectedSha256": row["afterSha256"], "actualSha256": actual_hash, "matches": True}
            if not row["callerless"]:
                item.update({"source": row["source"], "actual": value, "disposition": row["disposition"]})
            readback.append(item)
        if len(readback) != 240:
            raise SystemExit("final readback is incomplete")
        write_jsonl(READBACK, readback)
        summary = {
            **pins,
            "result": "PASS",
            "productHead": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
            "productTree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=REPO, text=True).strip(),
            "fullCatalogReadback": True,
            "readbackCellCount": len(readback),
            "changedCells": len(plan),
            "unchangedCallerBackedCells": 187,
            "unchangedHashOnlyHolds": 48,
            "allOtherCatalogCellsUnchanged": True,
            "messageOrderPreserved": True,
            "all12LocalesHave1836NonemptyValues": True,
            "catalogSha256After": sha(actual_bytes),
            "nativeSpeakerApproval": False,
            "headedBrowserReviewPerformed": False,
        }
        SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    write_jsonl(ROOT_DECISIONS, root_decision_rows)
    write_jsonl(SELECTED_TARGETS, selected_targets)
    write_jsonl(PLAN, plan)
    write_jsonl(LEDGER, final_rows)
    PINS.write_text(json.dumps(pins, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preflight = {
        **pins,
        "result": "PASS",
        "catalogBeforeSha256": sha(baseline_bytes),
        "all240CurrentCellsVerified": True,
        "all5ExactHashGuardsPassed": True,
        "all5SelectedTokenChecksPassed": True,
        "writeStartedAfterFullPreflight": True,
    }
    PREFLIGHT.write_text(json.dumps(preflight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if mode == "apply":
        output = (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        (REPO / CATALOG_PATH).write_bytes(output)
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        print("Catalog updated; commit product milestone and rerun with --verify-only.")
    else:
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        print("Preflight passed; no catalog write performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
