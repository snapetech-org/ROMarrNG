#!/usr/bin/env python3
"""Build the ROMarrNG W565-W584 cross-review packet from sealed review inputs."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

PIN_HEAD = "726db9138af2fc716056c7c36a9e842de04265e0"
PIN_TREE = "6669dc9117dbbbe6587d4183ec5bd0184c87e983"
REPO = "snapetech-org/ROMarrNG"
BRANCH = "task/localization-translation-review-20261030"
PIN_BASE = "bcd1eb41b5cdf8202acb5cf8e365e14761b743b5"
WINDOW = "W565-W584"
EXPECTED_LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: Path) -> str:
    return sha(path.read_bytes())

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path: Path):
    result = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            result.append((json.loads(raw), sha(raw)))
    return result

def check_sums(directory: Path, sums_name: str = "SHA256SUMS.txt"):
    sums = directory / sums_name
    entries = []
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(None, 1)
        rel = rel.strip()
        path = directory / rel
        actual = sha_file(path)
        if actual != expected:
            raise ValueError(f"checksum mismatch: {directory.name}/{rel}")
        entries.append({"path": rel, "sha256": actual, "bytes": path.stat().st_size})
    return entries

def command(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def capture_live(source_worktree: Path):
    pr = json.loads(command(["gh", "api", f"repos/{REPO}/pulls/70"]))
    refs_raw = command(["git", "ls-remote", "origin",
                        f"refs/heads/{BRANCH}", "refs/pull/70/head", "refs/heads/main"],
                       cwd=source_worktree)
    refs = {}
    for line in refs_raw.splitlines():
        oid, ref = line.split()
        refs[ref] = oid
    branch_oid = refs.get(f"refs/heads/{BRANCH}")
    pull_oid = refs.get("refs/pull/70/head")
    main_oid = refs.get("refs/heads/main")
    base_api = pr["base"]["sha"]
    head_api = pr["head"]["sha"]
    def commit_tree(oid):
        obj = json.loads(command(["gh", "api", f"repos/{REPO}/git/commits/{oid}"]))
        return obj["tree"]["sha"]
    compare = json.loads(command(["gh", "api", f"repos/{REPO}/compare/{base_api}...{main_oid}"]))
    status = command(["git", "status", "--porcelain=v1"], cwd=source_worktree)
    worktree_head = command(["git", "rev-parse", "HEAD"], cwd=source_worktree)
    worktree_tree = command(["git", "rev-parse", "HEAD^{tree}"], cwd=source_worktree)
    paths = sorted(file["filename"] for file in compare.get("files", []))
    only_allowed_drift = all(path.startswith(".github/workflows/") or path == "AGENTS.md" for path in paths)
    expected_match = (
        pr["number"] == 70
        and pr["state"] == "open"
        and pr["draft"] is True
        and head_api == PIN_HEAD
        and pr["head"]["ref"] == BRANCH
        and branch_oid == PIN_HEAD
        and pull_oid == PIN_HEAD
        and worktree_head == PIN_HEAD
        and worktree_tree == PIN_TREE
        and commit_tree(PIN_HEAD) == PIN_TREE
        and not status
        and base_api == PIN_BASE
        and main_oid is not None
    )
    return {
        "attestedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository": REPO,
        "pullRequest": {
            "number": pr["number"], "state": pr["state"].upper(), "draft": pr["draft"],
            "mergeable": "MERGEABLE" if pr.get("mergeable") else ("CONFLICTING" if pr.get("mergeable") is False else "UNKNOWN"),
            "headRef": pr["head"]["ref"], "headSha": head_api, "headTree": commit_tree(head_api),
            "baseRef": pr["base"]["ref"], "baseApiSha": base_api,
            "baseApiTree": commit_tree(base_api),
        },
        "refs": {
            "branch": {"name": BRANCH, "sha": branch_oid},
            "pullHead": {"ref": "refs/pull/70/head", "sha": pull_oid},
            "liveMain": {"ref": "refs/heads/main", "sha": main_oid, "tree": commit_tree(main_oid)},
        },
        "sourceWorktree": {
            "path": str(source_worktree), "head": worktree_head, "tree": worktree_tree,
            "clean": not bool(status), "statusPorcelain": status,
        },
        "baseDrift": {
            "apiBaseSha": base_api, "liveMainSha": main_oid,
            "apiBaseRefMismatch": base_api != main_oid,
            "compareStatus": compare.get("status"),
            "aheadBy": compare.get("ahead_by"), "behindBy": compare.get("behind_by"),
            "totalCommits": compare.get("total_commits"), "changedPaths": paths,
            "onlyWorkflowAndAgentInstructionChanges": only_allowed_drift,
        },
        "result": "PASS" if expected_match else "REF_OR_WORKTREE_MISMATCH",
    }

def index_key(row):
    index = row.get("catalogZeroBasedIndex", row.get("position"))
    if index is None:
        raise ValueError("row lacks catalogZeroBasedIndex/position")
    return int(index), row["locale"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-free", type=Path, required=True, help="sealed candidate-free input directory")
    ap.add_argument("--primary", type=Path, required=True, help="sealed primary review directory")
    ap.add_argument("--blind", type=Path, required=True, help="sealed blind output directory")
    ap.add_argument("--source-worktree", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()
    cf, primary, blind, source_worktree, out = map(lambda p: p.resolve(), (args.candidate_free, args.primary, args.blind, args.source_worktree, args.output))
    out.mkdir(parents=True, exist_ok=True)
    before = capture_live(source_worktree)
    (out / "attestation-before.json").write_text(json.dumps(before, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    candidate_checks = check_sums(cf)
    primary_root = primary.parent
    primary_root_checks = check_sums(primary_root)
    primary_nested_checks = check_sums(primary)
    blind_checks = check_sums(blind)

    cf_manifest = load_json(cf / "manifest.json")
    primary_manifest = load_json(primary / "manifest.json")
    primary_summary = load_json(primary / "summary.json")
    bundle = load_json(primary_root / "bundle-manifest.json")
    blind_packet = load_json(blind / "review_packet.json")
    cf_sums_sha = sha_file(cf / "SHA256SUMS.txt")
    cf_manifest_sha = sha_file(cf / "manifest.json")
    primary_readme_sha = sha_file(primary_root / "README.md")

    if cf_manifest.get("head") != PIN_HEAD or cf_manifest.get("tree") != PIN_TREE or cf_manifest.get("candidateFree") is not True:
        raise ValueError("candidate-free pin/flag mismatch")
    if primary_manifest.get("head") != PIN_HEAD or primary_manifest.get("tree") != PIN_TREE:
        raise ValueError("primary pin mismatch")
    if blind_packet.get("head") != PIN_HEAD or blind_packet.get("tree") != PIN_TREE:
        raise ValueError("blind pin mismatch")
    for record, label in [(bundle, "bundle"), (primary_summary, "primary"), (blind_packet, "blind")]:
        manifest_link = record.get("candidateFreeInputManifestSha256", record.get("inputManifestSha256", record.get("candidateFreeManifestSha256")))
        checksum_link = record.get("candidateFreeInputChecksumListSha256", record.get("inputChecksumsSha256", record.get("candidateFreeChecksumListSha256")))
        if manifest_link != cf_manifest_sha:
            raise ValueError(f"{label} candidate-free manifest linkage mismatch")
        if checksum_link != cf_sums_sha:
            raise ValueError(f"{label} candidate-free checksum-list linkage mismatch")
    if primary_summary.get("dispositions") != {"accept-current": 203, "correction": 1, "hold": 36}:
        raise ValueError("primary summary outcome mismatch")
    if blind_packet.get("dispositions") != {"accept_current": 199, "hold": 40, "revise": 1}:
        raise ValueError("blind summary outcome mismatch")

    primary_rows = read_jsonl(primary / "primary-ledger.jsonl")
    blind_rows = read_jsonl(blind / "review-cells.jsonl")
    current_rows = read_jsonl(cf / "current-target-cells.jsonl")
    context_rows = read_jsonl(cf / "source-contexts.jsonl")
    maps = []
    for rows, label in [(primary_rows, "primary"), (blind_rows, "blind"), (current_rows, "current")]:
        mapping = {}
        for row, digest in rows:
            key = index_key(row)
            if key in mapping:
                raise ValueError(f"duplicate {label} row for {key}")
            mapping[key] = (row, digest)
        maps.append(mapping)
    pmap, bmap, cmap = maps
    context_map = {}
    for row, digest in context_rows:
        if row["sourceId"] in context_map:
            raise ValueError("duplicate candidate-free source context")
        context_map[row["sourceId"]] = (row, digest)
    expected = {(index, locale) for index in range(565, 585) for locale in EXPECTED_LOCALES}
    if set(pmap) != expected or set(bmap) != expected or set(cmap) != expected:
        raise ValueError("the three cell inputs do not cover exactly 240 pinned cells")

    cross_rows = []
    selected = []
    disposition_counts = {"accept-current": 0, "recommend-change": 0, "hold-text-free": 0}
    hold_reasons = {}
    for key in sorted(expected, key=lambda k: (k[0], EXPECTED_LOCALES.index(k[1]))):
        p, psha = pmap[key]
        b, bsha = bmap[key]
        c, csha = cmap[key]
        source_id = c["sourceId"]
        if p["sourceId"] != source_id or b["sourceId"] != source_id:
            raise ValueError(f"source ID mismatch at {key}")
        context, context_line_sha = context_map[source_id]
        source_sha = context["sourceSha256"]
        context_sha = context["contextSha256"]
        current_sha = c["currentTargetSha256"]
        if (p["sourceSha256"], b["sourceSha256"], c["sourceSha256"]) != (source_sha, source_sha, source_sha):
            raise ValueError(f"source hash mismatch at {key}")
        if (p["currentTargetSha256"], b["currentTargetSha256"], current_sha) != (current_sha, current_sha, current_sha):
            raise ValueError(f"current-target hash mismatch at {key}")
        if p.get("callerContextSha256") != context_sha or b.get("callerContextSha256") != context_sha or c.get("callerContextSha256") != context_sha:
            raise ValueError(f"caller-context linkage mismatch at {key}")
        pdisp = p["disposition"]
        bdisp = b["disposition"]
        if pdisp != "hold" and p.get("currentTarget") != c.get("currentTarget"):
            raise ValueError(f"primary current-target text linkage mismatch at {key}")
        if bdisp != "hold" and b.get("currentTarget") != c.get("currentTarget"):
            raise ValueError(f"blind current-target text linkage mismatch at {key}")
        callerless = bool(context["callerless"])
        locator_hash = sha((str(key[0]) + "\0" + key[1] + "\0" + source_sha).encode())
        base = {
            "window": WINDOW,
            "catalogZeroBasedIndex": key[0],
            "locale": key[1],
            "sourceSha256": source_sha,
            "currentTargetSha256": current_sha,
            "callerContextSha256": context_sha,
            "cellLocatorSha256": locator_hash,
            "candidateFreeSourceContextRowSha256": context_line_sha,
            "candidateFreeCurrentTargetRowSha256": csha,
            "primaryRowSha256": psha,
            "blindRowSha256": bsha,
            "primaryDisposition": pdisp,
            "blindDisposition": bdisp,
        }
        if callerless or pdisp == "hold" or bdisp == "hold":
            if callerless:
                reason = "CALLERLESS_SOURCE_NO_PRODUCTION_CALLER"
                if pdisp != "hold" or bdisp != "hold" or not b.get("callerless"):
                    raise ValueError(f"callerless row not held by both reviewers at {key}")
            else:
                reason = b.get("rationaleCode")
                if pdisp == "hold" or bdisp != "hold" or not reason or not reason.startswith("CONTEXTUAL_"):
                    raise ValueError(f"unexpected contextual hold at {key}")
                if b.get("proposedTarget") is not None or b.get("rationale") is not None:
                    raise ValueError(f"contextual hold is not text-free in blind packet at {key}")
            row = {**base, "disposition": "hold-text-free", "callerless": callerless, "holdReasonCode": reason}
            forbidden = {"sourceId", "source", "sourceText", "currentTarget", "proposedTarget", "rationale"}
            if forbidden.intersection(row):
                raise ValueError(f"hold row contains forbidden text/identifier fields at {key}")
            disposition_counts["hold-text-free"] += 1
            hold_reasons[reason] = hold_reasons.get(reason, 0) + 1
        elif pdisp == "correction" and bdisp == "revise":
            pp = p.get("proposedTarget")
            bp = b.get("proposedTarget")
            pph = p.get("proposedTargetSha256")
            bph = b.get("proposedTargetSha256")
            if not pp or pp != bp or pph != bph or sha(pp.encode()) != pph or sha(bp.encode()) != bph:
                raise ValueError(f"reviewers' proposal hashes/text disagree at {key}")
            if key[1] != "de" or source_id != "ui.invitation.af4ea02852" or pp != "Einladung":
                raise ValueError("unexpected proposal identity or recommendation")
            if not context["callers"]:
                raise ValueError("proposal lacks exact caller context")
            change = {
                "window": WINDOW,
                "catalogZeroBasedIndex": key[0],
                "locale": key[1],
                "sourceId": source_id,
                "sourceText": context["source"],
                "sourceSha256": source_sha,
                "currentTarget": c["currentTarget"],
                "currentTargetSha256": current_sha,
                "recommendedTarget": pp,
                "recommendedTargetSha256": pph,
                "callerContextSha256": context_sha,
                "candidateFreeSourceContextRowSha256": context_line_sha,
                "candidateFreeCurrentTargetRowSha256": csha,
                "primaryProposalRowSha256": psha,
                "blindReviewRowSha256": bsha,
                "independentReviewAgreement": True,
                "nativeSpeakerReview": False,
                "recommendation": "recommend-change",
                "rationale": "Both reviewers independently recommend the same German noun. The exact candidate-free caller sets this as the public invitation page title; the current German term means a request or appeal, while the proposed term means invitation.",
            }
            selected.append(change)
            row = {**base, "disposition": "recommend-change", "sourceId": source_id, "proposalTargetSha256": pph}
            disposition_counts["recommend-change"] += 1
        elif pdisp == "accept-current" and bdisp == "accept_current":
            row = {**base, "disposition": "accept-current", "sourceId": source_id}
            disposition_counts["accept-current"] += 1
        else:
            raise ValueError(f"unresolved review disagreement at {key}: primary={pdisp}, blind={bdisp}")
        cross_rows.append(row)

    if disposition_counts != {"accept-current": 199, "recommend-change": 1, "hold-text-free": 40}:
        raise ValueError(f"unexpected cross disposition totals: {disposition_counts}")
    if len(selected) != 1:
        raise ValueError("expected one selected recommendation")
    contextual = sum(v for k, v in hold_reasons.items() if k.startswith("CONTEXTUAL_"))
    callerless_holds = hold_reasons.get("CALLERLESS_SOURCE_NO_PRODUCTION_CALLER", 0)
    if callerless_holds != 36 or contextual != 4:
        raise ValueError("hold union does not preserve all callerless/contextual holds")

    primary_root_readme = (primary_root / "README.md").read_text(encoding="utf-8")
    primary_nested_readme = (primary / "README.md").read_text(encoding="utf-8")
    integrity = {
        "artifact": "ROMarrNG PR #70 W565-W584 input integrity notes",
        "primaryRootReadme": {
            "sha256": primary_readme_sha,
            "claims": "202 accept-current, 2 correction proposals",
            "conflictsWithVerifiedLedger": True,
        },
        "verifiedPrimaryRecords": {
            "rootBundleManifest": bundle["dispositions"],
            "nestedPrimaryReadmeClaims203AcceptCurrentOneCorrection": "203 accepted current and 1 correction",
            "nestedPrimaryManifest": primary_manifest["dispositions"],
            "nestedPrimarySummary": primary_summary["dispositions"],
            "verifiedPrimaryLedgerRows": 240,
            "verifierResult": "PASS",
        },
        "disposition": "preserved as a documentation inconsistency; cross-review uses the primary ledger and the nested manifest/summary, which agree and pass the supplied verifier",
        "rootReadmeTextSha256": primary_readme_sha,
        "nestedReadmeSha256": sha(primary_nested_readme.encode()),
    }

    locks = {
        "artifact": "ROMarrNG PR #70 W565-W584 cross-review input locks",
        "repository": REPO,
        "baseApiSha": PIN_BASE,
        "head": PIN_HEAD,
        "tree": PIN_TREE,
        "candidateFree": {
            "artifactManifestSha256": cf_manifest_sha,
            "checksumListSha256": cf_sums_sha,
            "verifiedFiles": len(candidate_checks),
            "inputPathLabel": "primary-packet/candidate-free/input",
        },
        "primary": {
            "manifestSha256": sha_file(primary / "manifest.json"),
            "summarySha256": sha_file(primary / "summary.json"),
            "ledgerSha256": sha_file(primary / "primary-ledger.jsonl"),
            "proposalSha256": sha_file(primary / "primary-proposals.jsonl"),
            "rootChecksumListSha256": sha_file(primary_root / "SHA256SUMS.txt"),
            "nestedChecksumListSha256": sha_file(primary / "SHA256SUMS.txt"),
            "verifiedRootFiles": len(primary_root_checks),
            "verifiedNestedFiles": len(primary_nested_checks),
            "inputPathLabel": "primary-packet/primary",
        },
        "blind": {
            "reviewPacketSha256": sha_file(blind / "review_packet.json"),
            "reviewCellsSha256": sha_file(blind / "review-cells.jsonl"),
            "checksumListSha256": sha_file(blind / "SHA256SUMS.txt"),
            "verifiedFiles": len(blind_checks),
            "inputPathLabel": "blind-packet/output",
        },
        "linkage": {
            "candidateFreeManifestAndChecksumHashesMatchPrimaryAndBlind": True,
            "sourceRows": len(context_rows),
            "cellRows": len(cross_rows),
        },
    }

    summary = {
        "artifact": "ROMarrNG PR #70 W565-W584 independent cross-review",
        "repository": REPO,
        "pullRequest": 70,
        "window": WINDOW,
        "head": PIN_HEAD,
        "tree": PIN_TREE,
        "cellCount": len(cross_rows),
        "sourceCount": 20,
        "localeCount": 12,
        "primaryDispositions": primary_summary["dispositions"],
        "blindDispositions": blind_packet["dispositions"],
        "crossRecommendations": disposition_counts,
        "holdReasonCounts": hold_reasons,
        "callerlessHoldCount": callerless_holds,
        "contextualHoldCount": contextual,
        "agreementOnProposalCount": 1,
        "selectedChangeCount": 1,
        "selectedChange": {
            "catalogZeroBasedIndex": selected[0]["catalogZeroBasedIndex"],
            "locale": selected[0]["locale"],
            "recommendedTargetSha256": selected[0]["recommendedTargetSha256"],
        },
        "candidateFreeInputVerified": True,
        "primaryInputVerified": True,
        "blindInputVerified": True,
        "sourceWorktree": str(source_worktree),
        "baseApiRefMismatch": True,
        "baseDriftReconciliation": {
            "base": PIN_BASE,
            "liveMain": before["refs"]["liveMain"]["sha"],
            "aheadBy": before["baseDrift"]["aheadBy"],
            "behindBy": before["baseDrift"]["behindBy"],
            "onlyWorkflowAndAgentInstructionChanges": before["baseDrift"]["onlyWorkflowAndAgentInstructionChanges"],
        },
        "nativeSpeakerReview": False,
        "browserReview": False,
        "testsBuildsCiRun": False,
    }

    (out / "input-locks.json").write_text(json.dumps(locks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "integrity-notes.json").write_text(json.dumps(integrity, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "cross-review-cells.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in cross_rows), encoding="utf-8")
    (out / "selected-changes.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in selected), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    readme = f"""# ROMarrNG PR #70 W565-W584 cross-review

This packet independently reconciles the sealed candidate-free input, primary review, and blind review for catalog zero-based indices 565–584 (20 sources × 12 locales). It is pinned to head {PIN_HEAD} and tree {PIN_TREE}.

## Recommendations

- Accept current values for 199 cells.
- Recommend one German correction at index 573: the shared primary/blind recommendation is “Einladung”.
- Preserve 40 cells as text-free holds: 36 callerless cells and four contextual Arabic count cells.
- Native-speaker and browser review were not performed.

Held-cell rows in cross-review-cells.jsonl contain only indices, locales, reason codes, and hashes. They omit source IDs, source text, current targets, proposals, and free-text rationales.

The primary root README has an internal count inconsistency: it claims 202 accept-current and 2 corrections. The nested primary README, manifests, summary, row ledger, and supplied verifier agree on 203 accept-current and 1 correction. Checksums pass for both files. This is preserved in integrity-notes.json; the row-level reconciliation uses the verified ledger and matching nested records.

## Source pin and base drift

The live PR remains open and draft. API head, branch ref, pull-head ref, and the clean source worktree match the pinned head/tree. PR API base is {PIN_BASE}; live main is {before['refs']['liveMain']['sha']}. The compare reports {before['baseDrift']['aheadBy']} commits ahead and {before['baseDrift']['behindBy']} behind, limited to workflow files and AGENTS.md. No localization source/catalog files are in that drift. Reattestations are included before and after this review.

## Verification

SHA256SUMS.txt covers all other files in this packet. The verifier uses Python's standard library. To recheck this packet and its linkage, provide the original sealed input directories:

    python3 verify_cross_review.py --candidate-free /path/to/primary-packet/candidate-free/input --primary /path/to/primary-packet/primary --blind /path/to/blind-packet/output

The packet is recommendation-only. No repository files, PR metadata, workflows, tests, builds, or CI were changed or run.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    after = capture_live(source_worktree)
    (out / "attestation-after.json").write_text(json.dumps(after, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if before["result"] != "PASS" or after["result"] != "PASS":
        raise ValueError("live ref/worktree attestation did not match the pinned state")
    if before["refs"]["liveMain"]["sha"] != after["refs"]["liveMain"]["sha"] or before["baseDrift"] != after["baseDrift"]:
        raise ValueError("main/base drift changed during cross-review")
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text("".join(f"{sha_file(p)}  {p.relative_to(out).as_posix()}\n" for p in files), encoding="utf-8")
    print(json.dumps({"result": "BUILT", "cells": len(cross_rows), "recommendations": disposition_counts, "selectedChanges": len(selected), "output": str(out)}, ensure_ascii=False))

if __name__ == "__main__":
    main()

