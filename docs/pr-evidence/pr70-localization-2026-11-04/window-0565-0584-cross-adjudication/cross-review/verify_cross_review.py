#!/usr/bin/env python3
"""Verify the portable ROMarrNG W565-W584 cross-review and its sealed-input linkage."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

PIN_HEAD = "726db9138af2fc716056c7c36a9e842de04265e0"
PIN_TREE = "6669dc9117dbbbe6587d4183ec5bd0184c87e983"
WINDOW = "W565-W584"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
HOLD_CODES = {
    "CALLERLESS_SOURCE_NO_PRODUCTION_CALLER",
    "CONTEXTUAL_DYNAMIC_ARABIC_NUMBER_AGREEMENT",
    "CONTEXTUAL_ARABIC_COUNT_DUAL_PLURAL",
}
FORBIDDEN_HOLD_FIELDS = {
    "sourceId", "source", "sourceText", "currentTarget", "proposedTarget",
    "rationale", "proposalTargetSha256", "recommendedTarget",
}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path: Path):
    rows = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            rows.append((json.loads(raw), sha(raw)))
    return rows

def check_sums(directory: Path):
    for line in (directory / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(None, 1)
        actual = sha((directory / rel.strip()).read_bytes())
        if actual != expected:
            raise ValueError(f"input checksum mismatch: {directory}/{rel.strip()}")

def keyed(path: Path):
    result = {}
    for row, digest in read_jsonl(path):
        index = row.get("catalogZeroBasedIndex", row.get("position"))
        key = (int(index), row["locale"])
        if key in result:
            raise ValueError(f"duplicate row for {key} in {path.name}")
        result[key] = (row, digest)
    return result

def verify_packet_files(root: Path):
    listed = {}
    for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(None, 1)
        rel = rel.strip()
        listed[rel] = expected
        if sha((root / rel).read_bytes()) != expected:
            raise ValueError(f"packet checksum mismatch: {rel}")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"}
    if set(listed) != actual:
        raise ValueError("packet checksum list does not cover exactly all packet files")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-free", type=Path, required=True)
    ap.add_argument("--primary", type=Path, required=True)
    ap.add_argument("--blind", type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent
    cf, primary, blind = (p.resolve() for p in (args.candidate_free, args.primary, args.blind))
    verify_packet_files(root)
    for d in (cf, primary.parent, primary, blind):
        check_sums(d)

    locks = load_json(root / "input-locks.json")
    summary = load_json(root / "summary.json")
    integrity = load_json(root / "integrity-notes.json")
    before = load_json(root / "attestation-before.json")
    after = load_json(root / "attestation-after.json")
    if summary["head"] != PIN_HEAD or summary["tree"] != PIN_TREE:
        raise ValueError("cross summary pin mismatch")
    if before["result"] != "PASS" or after["result"] != "PASS":
        raise ValueError("live attestation did not pass")
    for snapshot in (before, after):
        if snapshot["pullRequest"]["headSha"] != PIN_HEAD or snapshot["pullRequest"]["headTree"] != PIN_TREE:
            raise ValueError("PR API head/tree mismatch")
        if snapshot["refs"]["branch"]["sha"] != PIN_HEAD or snapshot["refs"]["pullHead"]["sha"] != PIN_HEAD:
            raise ValueError("branch/pull head ref mismatch")
        if not snapshot["sourceWorktree"]["clean"] or snapshot["sourceWorktree"]["head"] != PIN_HEAD:
            raise ValueError("source worktree mismatch")
        if snapshot["pullRequest"]["state"] != "OPEN" or not snapshot["pullRequest"]["draft"]:
            raise ValueError("PR is not open/draft")
        if snapshot["baseDrift"]["apiBaseRefMismatch"] is not True:
            raise ValueError("recorded base/API mismatch unexpectedly absent")
        if not snapshot["baseDrift"]["onlyWorkflowAndAgentInstructionChanges"]:
            raise ValueError("base drift includes an unapproved path")
    if before["refs"]["liveMain"]["sha"] != after["refs"]["liveMain"]["sha"] or before["baseDrift"] != after["baseDrift"]:
        raise ValueError("live main/base drift changed during review")
    if (before["pullRequest"]["baseApiSha"], after["pullRequest"]["baseApiSha"]) != (locks.get("baseApiSha", before["pullRequest"]["baseApiSha"]), locks.get("baseApiSha", before["pullRequest"]["baseApiSha"])):
        raise ValueError("attestation base API linkage mismatch")

    cf_manifest = load_json(cf / "manifest.json")
    primary_root = primary.parent
    bundle = load_json(primary_root / "bundle-manifest.json")
    pmanifest = load_json(primary / "manifest.json")
    psummary = load_json(primary / "summary.json")
    bpacket = load_json(blind / "review_packet.json")
    expected_cf_manifest = sha((cf / "manifest.json").read_bytes())
    expected_cf_checksums = sha((cf / "SHA256SUMS.txt").read_bytes())
    if (cf_manifest["head"], cf_manifest["tree"], cf_manifest["candidateFree"]) != (PIN_HEAD, PIN_TREE, True):
        raise ValueError("candidate-free pin/flag mismatch")
    if locks["candidateFree"]["artifactManifestSha256"] != expected_cf_manifest or locks["candidateFree"]["checksumListSha256"] != expected_cf_checksums:
        raise ValueError("candidate-free lock mismatch")
    for record, manifest_field, sums_field in [
        (bundle, "candidateFreeManifestSha256", "candidateFreeChecksumListSha256"),
        (psummary, "candidateFreeInputManifestSha256", "candidateFreeInputChecksumListSha256"),
        (bpacket, "inputManifestSha256", "inputChecksumsSha256"),
    ]:
        if record[manifest_field] != expected_cf_manifest or record[sums_field] != expected_cf_checksums:
            raise ValueError("candidate-free linkage mismatch in a review packet")
    if (pmanifest["head"], pmanifest["tree"]) != (PIN_HEAD, PIN_TREE) or (bpacket["head"], bpacket["tree"]) != (PIN_HEAD, PIN_TREE):
        raise ValueError("review packet pin mismatch")
    if sha((primary / "primary-ledger.jsonl").read_bytes()) != locks["primary"]["ledgerSha256"]:
        raise ValueError("primary ledger lock mismatch")
    if sha((blind / "review-cells.jsonl").read_bytes()) != locks["blind"]["reviewCellsSha256"]:
        raise ValueError("blind decisions lock mismatch")
    if sha((primary_root / "README.md").read_bytes()) != integrity["primaryRootReadme"]["sha256"]:
        raise ValueError("primary root README evidence hash mismatch")
    if "202 accept-current, 2 correction proposals" not in (primary_root / "README.md").read_text(encoding="utf-8"):
        raise ValueError("primary root README discrepancy no longer matches captured note")
    if psummary["dispositions"] != {"accept-current": 203, "correction": 1, "hold": 36}:
        raise ValueError("primary counts are inconsistent")
    if bpacket["dispositions"] != {"accept_current": 199, "hold": 40, "revise": 1}:
        raise ValueError("blind counts are inconsistent")

    source_context = {}
    for row, digest in read_jsonl(cf / "source-contexts.jsonl"):
        source_context[row["sourceId"]] = (row, digest)
    pmap = keyed(primary / "primary-ledger.jsonl")
    bmap = keyed(blind / "review-cells.jsonl")
    cmap = keyed(cf / "current-target-cells.jsonl")
    cross = keyed(root / "cross-review-cells.jsonl")
    keys = {(i, locale) for i in range(565, 585) for locale in LOCALES}
    if any(set(m) != keys for m in (pmap, bmap, cmap, cross)):
        raise ValueError("expected exactly 240 rows in each linked cell set")
    selected_rows = [json.loads(line) for line in (root / "selected-changes.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(selected_rows) != 1:
        raise ValueError("expected one selected recommendation")
    selected = selected_rows[0]
    counts = {"accept-current": 0, "recommend-change": 0, "hold-text-free": 0}
    hold_codes = {}
    for key in sorted(keys, key=lambda k: (k[0], LOCALES.index(k[1]))):
        p, psha = pmap[key]
        b, bsha = bmap[key]
        c, csha = cmap[key]
        x, _ = cross[key]
        source_id = c["sourceId"]
        ctx, ctxsha = source_context[source_id]
        source_sha = ctx["sourceSha256"]
        caller_sha = ctx["contextSha256"]
        current_sha = c["currentTargetSha256"]
        locator_sha = sha((str(key[0]) + "\0" + key[1] + "\0" + source_sha).encode())
        expected_links = {
            "sourceSha256": source_sha,
            "currentTargetSha256": current_sha,
            "callerContextSha256": caller_sha,
            "cellLocatorSha256": locator_sha,
            "candidateFreeSourceContextRowSha256": ctxsha,
            "candidateFreeCurrentTargetRowSha256": csha,
            "primaryRowSha256": psha,
            "blindRowSha256": bsha,
            "primaryDisposition": p["disposition"],
            "blindDisposition": b["disposition"],
        }
        if any(x.get(name) != value for name, value in expected_links.items()):
            raise ValueError(f"exact hash linkage mismatch at {key}")
        callerless = bool(ctx["callerless"])
        if callerless or p["disposition"] == "hold" or b["disposition"] == "hold":
            if x.get("disposition") != "hold-text-free":
                raise ValueError(f"hold not preserved at {key}")
            if FORBIDDEN_HOLD_FIELDS.intersection(x):
                raise ValueError(f"held cell contains text or identifier fields at {key}")
            if x.get("callerless") is not callerless:
                raise ValueError(f"callerless flag mismatch at {key}")
            reason = x.get("holdReasonCode")
            if reason not in HOLD_CODES:
                raise ValueError(f"unexpected hold reason at {key}")
            if callerless:
                if p["disposition"] != "hold" or b["disposition"] != "hold" or reason != "CALLERLESS_SOURCE_NO_PRODUCTION_CALLER":
                    raise ValueError(f"callerless hold not preserved by both reviewers at {key}")
            else:
                if p["disposition"] != "accept-current" or b["disposition"] != "hold" or reason != b.get("rationaleCode"):
                    raise ValueError(f"contextual hold disagreement incorrect at {key}")
                if b.get("proposedTarget") is not None or b.get("rationale") is not None:
                    raise ValueError(f"blind contextual hold is not text-free at {key}")
            counts["hold-text-free"] += 1
            hold_codes[reason] = hold_codes.get(reason, 0) + 1
        elif p["disposition"] == "correction" and b["disposition"] == "revise":
            if x.get("disposition") != "recommend-change" or x.get("sourceId") != source_id:
                raise ValueError(f"proposal cross-disposition mismatch at {key}")
            if selected["sourceId"] != source_id or selected["locale"] != key[1] or selected["catalogZeroBasedIndex"] != key[0]:
                raise ValueError("selected proposal identity mismatch")
            for record in (p, b):
                proposed = record["proposedTarget"]
                proposed_sha = record["proposedTargetSha256"]
                if proposed != selected["recommendedTarget"] or proposed_sha != selected["recommendedTargetSha256"] or sha(proposed.encode()) != proposed_sha:
                    raise ValueError("primary/blind recommendation text/hash mismatch")
            if selected["sourceText"] != ctx["source"] or selected["sourceSha256"] != source_sha:
                raise ValueError("proposal source linkage mismatch")
            if selected["currentTarget"] != c["currentTarget"] or selected["currentTargetSha256"] != current_sha:
                raise ValueError("proposal current-target linkage mismatch")
            if selected["callerContextSha256"] != caller_sha or selected["recommendedTarget"] != "Einladung":
                raise ValueError("proposal caller or semantic recommendation mismatch")
            if x.get("proposalTargetSha256") != selected["recommendedTargetSha256"]:
                raise ValueError("proposal cross-row target hash mismatch")
            counts["recommend-change"] += 1
        elif p["disposition"] == "accept-current" and b["disposition"] == "accept_current":
            if x.get("disposition") != "accept-current" or x.get("sourceId") != source_id:
                raise ValueError(f"accept-current mismatch at {key}")
            counts["accept-current"] += 1
        else:
            raise ValueError(f"unresolved review disagreement at {key}")
    expected_counts = {"accept-current": 199, "recommend-change": 1, "hold-text-free": 40}
    if counts != expected_counts or summary["crossRecommendations"] != expected_counts:
        raise ValueError(f"cross totals mismatch: {counts}")
    if hold_codes != summary["holdReasonCounts"] or hold_codes.get("CALLERLESS_SOURCE_NO_PRODUCTION_CALLER") != 36:
        raise ValueError("hold totals/hash-only reconciliation mismatch")
    if sum(v for k, v in hold_codes.items() if k.startswith("CONTEXTUAL_")) != 4:
        raise ValueError("expected four contextual hash-only holds")
    print(json.dumps({"result":"PASS","cells":240,"recommendations":counts,"holdReasonCounts":hold_codes,"inputLinkage":"PASS","packetChecksums":"PASS"}, ensure_ascii=False))

if __name__ == "__main__":
    main()

