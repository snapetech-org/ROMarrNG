#!/usr/bin/env python3
"""Verify the W645-W664 primary ledger against its sealed candidate-free input."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HEAD = "9f8832f67195323955172dd4c3c40e29cbabb5da"
TREE = "d6066baa3d03d3b4c6034e5af061fc4bc278b0f9"
WINDOW = "W645-W664"
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


def check_sums(root: Path) -> dict[str, str]:
    sums = root / "SHA256SUMS.txt"
    listed = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path.read_bytes()) != digest:
            fail("checksum " + name)
        if name in listed:
            fail("duplicate checksum " + name)
        listed[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != sums}
    if set(listed) != actual:
        fail("checksum coverage " + str(root))
    return listed


def tokens(text: str) -> dict:
    protected = []
    for literal in PROTECTED:
        matched = literal in text if literal.startswith("/") else bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(literal) + r"(?![A-Za-z0-9])", text))
        if matched:
            protected.append(literal)
    return {"placeholders":PLACEHOLDER.findall(text), "markup":TAG.findall(text), "numbers":NUMBER.findall(text), "protectedLiterals":sorted(set(protected))}


def token_report(source: str, target: str) -> dict:
    source_tokens = tokens(source)
    target_tokens = tokens(target)
    source_numbers = collections.Counter(source_tokens["numbers"])
    target_numbers = collections.Counter(target_tokens["numbers"])
    extra = list((target_numbers - source_numbers).elements())
    presentation = bool(re.search(r"\bzero\b", source, re.I) and not source_tokens["numbers"] and extra == ["0"])
    numeric_ok = not (source_numbers - target_numbers) and (not extra or presentation)
    missing = [value for value in source_tokens["protectedLiterals"] if value not in target]
    return {"sourcePlaceholderTokens":source_tokens["placeholders"], "targetPlaceholderTokens":target_tokens["placeholders"], "placeholdersPreserved":collections.Counter(source_tokens["placeholders"]) == collections.Counter(target_tokens["placeholders"]), "sourceMarkupTags":source_tokens["markup"], "targetMarkupTags":target_tokens["markup"], "markupPreserved":collections.Counter(source_tokens["markup"]) == collections.Counter(target_tokens["markup"]), "sourceNumericTokens":source_tokens["numbers"], "targetNumericTokens":target_tokens["numbers"], "numericTokensPreserved":numeric_ok, "numericPresentationEquivalent":presentation, "sourceProtectedLiterals":source_tokens["protectedLiterals"], "missingProtectedLiterals":missing, "protectedLiteralsPreserved":not missing}


def verify_primary(repo: Path) -> dict:
    repo = repo.resolve()
    root = Path(__file__).resolve().parent
    outer_files = check_sums(root)
    output = root / "primary-output"
    output_files = check_sums(output)
    candidate_bundle = root / "candidate-free-bundle"
    candidate_result = json.loads(subprocess.check_output([sys.executable, str(candidate_bundle / "verify_bundle.py"), "--repo", str(repo)], text=True))
    if candidate_result.get("result") != "PASS":
        fail("copied candidate-free bundle")
    if git(repo, "rev-parse", "HEAD") != HEAD or git(repo, "rev-parse", "HEAD^{tree}") != TREE or git(repo, "status", "--porcelain=v1", "--untracked-files=all") or git(repo, "branch", "--show-current"):
        fail("exact clean detached repository pin")

    input_dir = candidate_bundle / "candidate-free" / "input"
    input_manifest_raw = (input_dir / "manifest.json").read_bytes()
    input_manifest = json.loads(input_manifest_raw)
    input_hash = sha(input_manifest_raw)
    primary_packet = read_json(root / "PRIMARY-REVIEW-MANIFEST.json")
    primary_manifest = read_json(output / "primary-manifest.json")
    summary = read_json(output / "summary.json")
    if (primary_packet.get("head"), primary_packet.get("tree"), primary_packet.get("window"), primary_packet.get("candidateFreeInputManifestSha256"), primary_packet.get("candidateFreeVerifier"), primary_packet.get("blindReviewUsed"), primary_packet.get("crossReviewUsed"), primary_packet.get("applyPerformed")) != (HEAD, TREE, WINDOW, input_hash, "PASS", False, False, False):
        fail("primary packet identity or stage boundary")
    if (primary_manifest.get("head"), primary_manifest.get("tree"), primary_manifest.get("window"), primary_manifest.get("candidateFreeInputManifestSha256")) != (HEAD, TREE, WINDOW, input_hash):
        fail("primary output manifest identity")

    manifest_records = {row["path"]:row for row in primary_manifest.get("files", [])}
    expected_output = {name:digest for name,digest in output_files.items() if name != "primary-manifest.json"}
    if set(manifest_records) != set(expected_output):
        fail("primary manifest output file inventory")
    for name, digest in expected_output.items():
        record = manifest_records[name]
        path = output / name
        if record.get("sha256") != digest or record.get("bytes") != path.stat().st_size:
            fail("primary manifest file record " + name)

    cells = read_jsonl(input_dir / "current-target-cells.jsonl")
    contexts = read_jsonl(input_dir / "source-contexts.jsonl")
    cell_map = {(row["sourceId"], row["locale"]):row for row in cells}
    context_map = {row["sourceId"]:row for row in contexts}
    dispositions = read_jsonl(output / "dispositions.jsonl")
    holds = read_jsonl(output / "hash-only-holds.jsonl")
    if len(cell_map) != 240 or len(dispositions) != 144 or len(holds) != 96:
        fail("decision/hold cardinality")
    keys = [(row["sourceId"], row["locale"]) for row in dispositions + holds]
    if len(set(keys)) != 240 or set(keys) != set(cell_map):
        fail("complete one-decision-per-cell coverage")
    counts = collections.Counter()
    changes_by_locale = collections.Counter()
    changes_by_position = collections.Counter()
    changes_by_type = collections.Counter()
    proposal_keys = {"proposedTarget", "proposedTargetSha256", "proposedTargetTokenChecks"}
    for row in dispositions:
        key = (row["sourceId"], row["locale"])
        cell = cell_map.get(key)
        context = context_map.get(row["sourceId"])
        if cell is None or context is None or context["callerless"] or context["exactMatchCount"] <= 0:
            fail("callerful primary decision required " + str(key))
        if row.get("window") != WINDOW or row.get("position") != cell["position"] or row.get("catalogZeroBasedIndex") != cell["catalogZeroBasedIndex"] or row.get("source") != cell["source"] or row.get("sourceSha256") != cell["sourceSha256"]:
            fail("decision source binding " + str(key))
        if row.get("currentTarget") != cell["currentTarget"] or row.get("currentTargetSha256") != cell["currentTargetSha256"] or row.get("callerContextSha256") != context["contextSha256"] or row.get("callerCount") != context["exactMatchCount"] or row.get("callerRefHashesSha256") != sha(canonical(cell["callerRefs"])):
            fail("decision target/context binding " + str(key))
        current_checks = token_report(row["source"], row["currentTarget"])
        if row.get("currentTargetTokenChecks") != current_checks or not all(current_checks[name] for name in ("placeholdersPreserved", "markupPreserved", "numericTokensPreserved", "protectedLiteralsPreserved")):
            fail("current-target token checks " + str(key))
        banned = {"selectedTarget", "finalTarget", "proposal"}
        if banned & set(row):
            fail("unexpected decision field " + str(key))
        if row.get("disposition") == "KEEP":
            if proposal_keys & set(row):
                fail("KEEP decision contains proposal " + str(key))
            counts["KEEP"] += 1
        elif row.get("disposition") == "CHANGE":
            target = row.get("proposedTarget")
            if not isinstance(target, str) or row.get("proposedTargetSha256") != sha(target):
                fail("proposed target hash " + str(key))
            proposed_checks = token_report(row["source"], target)
            if row.get("proposedTargetTokenChecks") != proposed_checks or not all(proposed_checks[name] for name in ("placeholdersPreserved", "markupPreserved", "numericTokensPreserved", "protectedLiteralsPreserved")):
                fail("proposed-target token checks " + str(key))
            if not row.get("rationale") or not row.get("changeType"):
                fail("change rationale/type " + str(key))
            counts["CHANGE"] += 1
            changes_by_locale[row["locale"]] += 1
            changes_by_position[str(row["position"])] += 1
            changes_by_type[row["changeType"]] += 1
        else:
            fail("unknown primary disposition " + str(key))
    text_fields = {"source", "sourceText", "currentTarget", "target", "targetText", "proposedTarget", "selectedTarget", "finalTarget"}
    for row in holds:
        key = (row["sourceId"], row["locale"])
        cell = cell_map.get(key)
        context = context_map.get(row["sourceId"])
        if cell is None or context is None or not context["callerless"] or context["callers"]:
            fail("hold must bind a callerless context " + str(key))
        if row.get("window") != WINDOW or row.get("position") != cell["position"] or row.get("catalogZeroBasedIndex") != cell["catalogZeroBasedIndex"] or row.get("sourceSha256") != cell["sourceSha256"] or row.get("currentTargetSha256") != cell["currentTargetSha256"] or row.get("callerContextSha256") != context["contextSha256"] or row.get("callerCount") != 0 or row.get("disposition") != "hold-callerless-hash-only":
            fail("hash-only hold binding " + str(key))
        if text_fields & set(row) or row.get("sourceTextOmitted") is not True or row.get("targetTextOmitted") is not True:
            fail("callerless hold contains source or target text")
        counts["HOLD"] += 1

    if summary.get("dispositionCounts") != {"CHANGE":counts["CHANGE"], "KEEP":counts["KEEP"], "HOLD":counts["HOLD"]}:
        fail("summary disposition counts")
    if (summary.get("head"), summary.get("tree"), summary.get("window"), summary.get("cellCount"), summary.get("proposedChangeCount"), summary.get("hashOnlyHoldCount")) != (HEAD, TREE, WINDOW, 240, counts["CHANGE"], 96):
        fail("summary identity/count")
    if summary.get("proposedChangeCountsByLocale") != dict(sorted(changes_by_locale.items())) or summary.get("proposedChangeCountsByPosition") != dict(sorted(changes_by_position.items(), key=lambda row:int(row[0]))) or summary.get("changeTypes") != dict(sorted(changes_by_type.items())):
        fail("summary proposal distribution")
    if summary.get("blindness") != {"blindOutputInspected":False, "crossReviewOutputInspected":False, "otherW645ReviewDecisionsAccessed":False, "priorW645PrimaryDecisionsReused":False, "candidateFreeInputManifestSha256":input_hash}:
        fail("independent primary boundary")
    callerless_sources = sum(row["callerless"] for row in contexts)
    if summary.get("callerCoverage", {}).get("callerlessSources") != callerless_sources or summary.get("callerCoverage", {}).get("callerlessCells") != 96 or summary.get("callerCoverage", {}).get("proposedChangesWithoutCallerContext") != 0:
        fail("caller coverage summary")
    return {"result":"PASS", "head":HEAD, "tree":TREE, "window":WINDOW, "cells":240, "callerfulDecisions":len(dispositions), "counts":dict(counts), "callerlessHashOnlyHolds":len(holds), "candidateFreeVerifier":"PASS", "primaryIndependentOfBlindAndCross":True, "repoClean":True, "primaryFiles":len(outer_files), "outputFiles":len(output_files)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_primary(args.repo), ensure_ascii=False, sort_keys=True))
