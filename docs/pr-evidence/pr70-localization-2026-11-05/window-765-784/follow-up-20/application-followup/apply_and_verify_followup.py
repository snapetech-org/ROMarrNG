#!/usr/bin/env python3
from __future__ import annotations
import collections
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WINDOW = HERE.parent
APPLY_HEAD = "ec6319e012ee0043be853ee313ff7cbf36e51af1"
APPLY_TREE = "53c33792ee85083d270fe3a914332cf3a9cb5c6e"
BASE_PRODUCT = "7e101cc0ea5580443d1b3903af084c23fe2134e5"
REVIEW_HEAD = "9714d7cf69c687685b4f65cbd9627a56830bab85"
REVIEW_TREE = "c8eb66573f10b2390a02df05033f5133425d5e41"
CATALOG = "romarr/ui-labels.json"
PLAN = HERE / "exact-hash-apply-plan.jsonl"
FINAL = WINDOW / "final-root-adjudication.jsonl"
PRODUCT_PIN = HERE / "product-pin.json"
READBACK = HERE / "readback-240.jsonl"
SUMMARY = HERE / "application-summary.json"
FILE_READBACK = HERE / "catalog-file-readback.json"


def sha(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def replace_lines(text, plan):
    lines = text.splitlines(keepends=True)
    for row in plan:
        sid = row["sourceId"]
        locale = row["locale"]
        marker = f'    {json.dumps(sid, ensure_ascii=False)}: {{'
        starts = [i for i, line in enumerate(lines) if line.rstrip("\n") == marker]
        if len(starts) != 1:
            raise SystemExit(f"source block mismatch {sid}")
        start = starts[0]
        tstarts = [
            i for i in range(start + 1, len(lines))
            if lines[i].rstrip("\n") == '      "translations": {'
        ]
        if not tstarts:
            raise SystemExit(f"translations block missing {sid}")
        tstart = tstarts[0]
        tends = [
            i for i in range(tstart + 1, len(lines))
            if lines[i].rstrip("\n") == "      },"
        ]
        if not tends:
            raise SystemExit(f"translations close missing {sid}")
        tend = tends[0]
        prefix = f'        {json.dumps(locale, ensure_ascii=False)}: '
        hits = [i for i in range(tstart + 1, tend) if lines[i].startswith(prefix)]
        if len(hits) != 1:
            raise SystemExit(f"locale line mismatch {sid}::{locale}")
        i = hits[0]
        line = lines[i]
        ending = "\n" if line.endswith("\n") else ""
        valuepart = line[len(prefix):].rstrip("\n")
        comma = valuepart.endswith(",")
        old = json.loads(valuepart[:-1] if comma else valuepart)
        if old != row["before"] or sha(old) != row["beforeSha256"]:
            raise SystemExit(f"before-value guard failed {sid}::{locale}")
        lines[i] = prefix + json.dumps(row["after"], ensure_ascii=False) + ("," if comma else "") + ending
    return "".join(lines)


def status_clean(repo):
    return git(repo, "status", "--porcelain=v1", "--untracked-files=all").decode().strip() == ""


def main():
    args = sys.argv[1:]
    mode = "apply" if "--apply" in args else "verify" if "--verify-after" in args else "preflight"
    if "--repo" not in args:
        raise SystemExit("usage: apply_and_verify_followup.py --repo PATH [--preflight|--apply|--verify-after]")
    repo = Path(args[args.index("--repo") + 1]).resolve()
    plan = read_jsonl(PLAN)
    final = read_jsonl(FINAL)
    if len(plan) != 20 or len(final) != 240:
        raise SystemExit("plan/final-ledger coverage mismatch")
    if mode != "verify":
        head = git(repo, "rev-parse", "HEAD").decode().strip()
        tree = git(repo, "rev-parse", "HEAD^{tree}").decode().strip()
        if (head, tree) != (APPLY_HEAD, APPLY_TREE):
            raise SystemExit(f"expected clean application pin {APPLY_HEAD}/{APPLY_TREE}, got {head}/{tree}")
        if not status_clean(repo):
            raise SystemExit("application worktree must be clean")

    base_raw = git(repo, "show", f"{BASE_PRODUCT}:{CATALOG}")
    review_raw = git(repo, "show", f"{REVIEW_HEAD}:{CATALOG}")
    path = repo / CATALOG
    raw = path.read_bytes()
    if mode != "verify" and raw != base_raw:
        raise SystemExit("current catalog differs from pinned first product application")
    base = json.loads(base_raw)
    original = json.loads(review_raw)
    current = json.loads(raw)
    if list(base["messages"]) != list(original["messages"]):
        raise SystemExit("message order changed before follow-up")

    for row in plan:
        msg = base["messages"].get(row["sourceId"])
        if not msg or msg.get("sourceHash") != row["sourceSha256"] or sha(msg.get("source", "")) != row["sourceSha256"]:
            raise SystemExit(f"source hash mismatch {row['sourceId']}")
        if msg["translations"].get(row["locale"]) != row["before"]:
            raise SystemExit(f"target differs from plan before value {row['sourceId']}::{row['locale']}")
        if sha(row["after"]) != row["afterSha256"]:
            raise SystemExit(f"selected hash mismatch {row['sourceId']}::{row['locale']}")
        if any(literal not in row["after"] for literal in row["pinnedManualLiterals"]):
            raise SystemExit(f"selected literal missing {row['sourceId']}::{row['locale']}")

    if mode == "preflight":
        result = {
            "result": "PASS",
            "mode": mode,
            "head": APPLY_HEAD,
            "tree": APPLY_TREE,
            "planCells": 20,
            "catalogSha256": sha(base_raw),
            "trackedAndUntrackedWorktreeClean": True,
        }
        (HERE / "preflight.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return

    if mode == "apply":
        updated = replace_lines(raw.decode("utf-8"), plan).encode("utf-8")
        tmp = path.with_suffix(path.suffix + ".w765-784-followup.tmp")
        if tmp.exists():
            raise SystemExit("refusing existing temporary file")
        try:
            tmp.write_bytes(updated)
            parsed = json.loads(tmp.read_text(encoding="utf-8"))
            tmp.replace(path)
        finally:
            if tmp.exists():
                tmp.unlink()
        current_raw = path.read_bytes()
        current = parsed
    else:
        current_raw = raw

    expected = copy.deepcopy(base)
    for row in plan:
        expected["messages"][row["sourceId"]]["translations"][row["locale"]] = row["after"]
    if current != expected:
        raise SystemExit("follow-up changed an unselected value or omitted a selected cell")
    if list(current["messages"]) != list(original["messages"]):
        raise SystemExit("message order changed")

    changes = []
    for sid in original["messages"]:
        original_translations = original["messages"][sid]["translations"]
        current_translations = current["messages"][sid]["translations"]
        for locale, old_value in original_translations.items():
            if current_translations[locale] != old_value:
                changes.append((sid, locale))
    expected_changes = {
        (row["sourceId"], row["locale"])
        for row in final
        if row["rootDisposition"] in {"correction", "refinement"}
    }
    if set(changes) != expected_changes or len(changes) != 30:
        raise SystemExit(f"total review-head changed targets mismatch: {len(changes)} vs 30")

    counts = collections.Counter(row["rootDisposition"] for row in final)
    readback = []
    for row in final:
        sid = row["sourceId"]
        locale = row["locale"]
        got = current["messages"][sid]["translations"][locale]
        if row["callerless"]:
            expected_hash = row.get("afterSha256") or row["beforeSha256"]
            if sha(got) != expected_hash:
                raise SystemExit(f"hash-only hold mismatch {sid}::{locale}")
            readback.append({
                "sourceId": sid, "locale": locale, "callerless": True,
                "disposition": row["rootDisposition"], "beforeSha256": row["beforeSha256"],
                "afterSha256": sha(got), "position": row["position"],
                "oneBasedPosition": row["oneBasedPosition"],
            })
        else:
            if got != row["after"] or sha(got) != row["afterSha256"]:
                raise SystemExit(f"final 240-cell readback mismatch {sid}::{locale}")
            readback.append({
                "sourceId": sid, "locale": locale, "callerless": False,
                "disposition": row["rootDisposition"], "beforeSha256": row["beforeSha256"],
                "after": got, "afterSha256": sha(got), "position": row["position"],
                "oneBasedPosition": row["oneBasedPosition"],
                "callerContextSha256": row["callerContextSha256"],
            })
    if len(readback) != 240 or sum(row["callerless"] for row in readback) != 24:
        raise SystemExit("readback coverage mismatch")
    READBACK.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in readback), encoding="utf-8")
    file_readback = {
        "catalog": CATALOG,
        "catalogSha256BeforeFollowup": sha(base_raw),
        "catalogSha256AfterFollowup": sha(current_raw),
        "keys": len(current["messages"]),
        "keysPreserved": list(base["messages"]) == list(current["messages"]),
        "changedValuesThisFollowup": 20,
        "totalChangedValuesFromReviewHead": 30,
        "onlySelectedValuesChanged": True,
    }
    FILE_READBACK.write_text(json.dumps(file_readback, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "result": "PASS",
        "window": "W765-W784",
        "mode": mode,
        "inputReviewHead": REVIEW_HEAD,
        "inputReviewTree": REVIEW_TREE,
        "baseProductCommit": BASE_PRODUCT,
        "followupPlanCells": 20,
        "finalReadbackCells": 240,
        "callerBackedReadback": 216,
        "hashOnlyReadback": 24,
        "changedValuesThisFollowup": 20,
        "totalChangedValuesFromReviewHead": 30,
        "finalDispositions": dict(counts),
        "priorActiveHolds": 988,
        "activeHoldsAfter": 1012,
        "catalogSha256": sha(current_raw),
        "catalogKeysPreserved": True,
        "onlySelectedValuesChanged": True,
        "nativeSpeakerApproval": False,
    }
    if PRODUCT_PIN.exists():
        pin = json.loads(PRODUCT_PIN.read_text(encoding="utf-8"))
        tree = git(repo, "rev-parse", f'{pin["productCommit"]}^{{tree}}').decode().strip()
        if tree != pin["productTree"] or sha(current_raw) != pin["catalogSha256"]:
            raise SystemExit("final product commit/tree/catalog pin mismatch")
        if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", pin["productCommit"], "HEAD"]).returncode != 0:
            raise SystemExit("follow-up product commit is not an ancestor of HEAD")
        report.update({
            "productCommit": pin["productCommit"],
            "productTree": tree,
            "verificationHead": git(repo, "rev-parse", "HEAD").decode().strip(),
        })
    SUMMARY.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
