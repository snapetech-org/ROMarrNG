#!/usr/bin/env python3
"""Portable verifier for the ROMarrNG PR #70 W485-W504 clean blind review."""
from pathlib import Path
import collections
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INPUT = HERE / "candidate-free-input"
HEAD = "6eb494d362ae19503b9199cd2c05c0767cddbc0e"
TREE = "b9450b9c6d22c816551fc8d528e8f03413d04595"
BRANCH = "task/localization-translation-review-20261030"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PROTECTED = ["ROMarr", "GG Requestz", "RomM", "ROMm", "ES-DE", "gamelist.xml", "1G1R", "Battle.net", "No-Intro", "Redump", "RetroArch", "Steam", "EA", "Epic", "ROM", "Hub", "DAT"]
TOKEN_RE = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")

def fail(message):
    raise SystemExit("FAIL: " + message)

def need(value, message):
    if not value:
        fail(message)

def sha(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def readj(path):
    return json.loads(path.read_text(encoding="utf-8"))

def readjl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def protected(text):
    return [term for term in PROTECTED if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text)]

def verify_sums(root, sums_path):
    entries = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        need(match is not None, "malformed checksum row")
        digest, name = match.groups()
        rel = Path(name)
        need(not rel.is_absolute() and ".." not in rel.parts and name not in entries, "unsafe or duplicate checksum path")
        entries[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != sums_path}
    need(set(entries) == actual, "checksum file inventory")
    for name, digest in entries.items():
        need(sha((root / name).read_bytes()) == digest, "checksum " + name)
    return entries

entries = verify_sums(HERE, HERE / "SHA256SUMS.txt")
input_entries = verify_sums(INPUT, INPUT / "SHA256SUMS.txt")
input_verify = subprocess.run([sys.executable, str(INPUT / "verify_input.py")], capture_output=True, text=True)
need(input_verify.returncode == 0, "candidate-free input verifier: " + input_verify.stdout + input_verify.stderr)

manifest = readj(HERE / "manifest.json")
summary = readj(HERE / "summary.json")
provenance = readj(HERE / "provenance.json")
input_manifest = readj(INPUT / "manifest.json")
need(manifest["head"] == HEAD and manifest["tree"] == TREE and manifest["branch"] == BRANCH and manifest["window"] == "W485-W504", "blind manifest refs")
need(input_manifest["head"] == HEAD and input_manifest["tree"] == TREE and input_manifest["window"] == "W485-W504", "candidate-free input pins")
need(manifest["candidateFreeInputManifestSha256"] == sha((INPUT / "manifest.json").read_bytes()), "candidate-free manifest hash")
need(manifest["candidateFreeInputChecksumListSha256"] == sha((INPUT / "SHA256SUMS.txt").read_bytes()), "candidate-free checksum-list hash")
need(summary["candidateFreeInputManifestSha256"] == manifest["candidateFreeInputManifestSha256"], "summary input manifest pin")
need(summary["candidateFreeInputChecksumListSha256"] == manifest["candidateFreeInputChecksumListSha256"], "summary input checksum pin")
need(provenance["candidateFreeInputHead"] == HEAD and provenance["candidateFreeInputTree"] == TREE and provenance["reviewUsedOnlyCopiedCandidateFreeInput"] is True, "blind provenance boundary")
need(manifest["cellCount"] == summary["cellCount"] == 240 and manifest["sourceCount"] == summary["sourceCount"] == 20 and manifest["localeCount"] == summary["localeCount"] == 12, "blind coverage counts")
need(manifest["blindLedgerSha256"] == sha((HERE / "blind-ledger.jsonl").read_bytes()), "blind ledger manifest hash")
need(manifest["summarySha256"] == sha((HERE / "summary.json").read_bytes()), "summary manifest hash")
need(manifest["provenanceSha256"] == sha((HERE / "provenance.json").read_bytes()), "provenance manifest hash")

# The copied input makes source, caller context, and packet-boundary lineage checks portable.
for name in ("prior-selection-reattestation.jsonl", "prior-hold-reattestation.jsonl"):
    need((HERE / name).read_bytes() == (INPUT / name).read_bytes(), "exact prior reattestation copy " + name)
    need(sha((HERE / name).read_bytes()) == manifest["priorReattestationSha256"][name], "prior reattestation manifest hash " + name)
need(len(readjl(INPUT / "prior-selection-reattestation.jsonl")) == 100, "candidate-free prior source count")
need(len(readjl(INPUT / "prior-hold-reattestation.jsonl")) == 444, "candidate-free prior hold count")

selected = readjl(INPUT / "source-inventory-selection.jsonl")
current = readjl(INPUT / "current-target-cells.jsonl")
contexts = {r["sourceId"]: r for r in readjl(INPUT / "source-contexts.jsonl")}
need(len(selected) == 20 and len(current) == 240, "candidate-free input coverage")
ledger = readjl(HERE / "blind-ledger.jsonl")
need(len(ledger) == 240, "blind ledger row count")
need([(r["position"], r["locale"]) for r in ledger] == [(pos, loc) for pos in range(485, 505) for loc in LOCALES], "blind ledger cell order")
counts = collections.Counter(r["blindDisposition"] for r in ledger)
need(dict(counts) == manifest["dispositions"] == summary["dispositions"], "blind disposition counts")
need(dict(counts) == {"accept-current": 201, "correction": 14, "refinement": 1, "hold": 24}, "expected blind disposition totals")
need(counts["correction"] + counts["refinement"] == manifest["proposedCellCount"] == summary["proposedCellCount"] == 15, "proposed cell count")
need(counts["hold"] == manifest["newHoldCellCount"] == summary["newHolds"] == 24, "hold count")
need(sorted({r["position"] for r in ledger if r["blindDisposition"] == "hold"}) == [493, 502], "callerless hold positions")
need(manifest["priorSelectedSourceCount"] == summary["priorSelectedSourceCount"] == 100 and manifest["priorHoldCellCount"] == summary["priorHoldCellCount"] == 444, "prior lineage counts")
need(summary["placeholderMismatchesInSelectedTargets"] == summary["numericMismatchesInSelectedTargets"] == summary["protectedLiteralMismatchesInSelectedTargets"] == 0, "selected target safety summary")
locale_counts = {loc: dict(collections.Counter(r["blindDisposition"] for r in ledger if r["locale"] == loc)) for loc in LOCALES}
need(locale_counts == summary["localeDispositionCounts"], "locale disposition summary")

by_identity = {(r["position"], r["locale"]): r for r in current}
for row in ledger:
    key = (row["position"], row["locale"])
    source = by_identity[key]
    for field in ("catalogZeroBasedIndex", "catalogOneBasedPosition", "sourceId", "source", "sourceSha256", "currentTarget", "currentTargetSha256", "catalogTranslationHash"):
        need(row[field] == source[field], "candidate-free current cell binding " + field)
    ctx = contexts[row["sourceId"]]
    need(row["callerContextSha256"] == ctx["callerContextSha256"], "caller context hash")
    refs = [{k: ref[k] for k in ("path", "lineStart", "lineEnd", "contextSha256", "fileSha256", "gitBlob", "role", "anchor")} for ref in ctx["callerContextRefs"]]
    need(row["callerContextRefs"] == refs, "caller context reference binding")
    need(row["sourceIdExactMatchCount"] == ctx["sourceIdExactMatchCount"] and row["sourceTextExactMatchCount"] == ctx["sourceTextExactMatchCount"], "caller match counts")
    need(sha(row["source"]) == row["sourceSha256"] and sha(row["currentTarget"]) == row["currentTargetSha256"], "source/current target raw hashes")
    need(sha(canon(row["currentTarget"])) == row["catalogTranslationHash"], "catalog translation hash")
    disposition = row["blindDisposition"]
    proposed = row["proposedTarget"]
    chosen = row["selectedTarget"]
    if disposition == "accept-current":
        need(proposed is None and chosen == row["currentTarget"] and row["selectedTargetOrigin"] == "current", "accept-current target")
    elif disposition in {"correction", "refinement"}:
        need(isinstance(proposed, str) and chosen == proposed and row["selectedTargetOrigin"] == "blind-review", "blind selected target")
        need(sha(proposed) == row["proposedTargetSha256"] == row["selectedTargetSha256"], "blind proposal target hashes")
    else:
        need(proposed is None and chosen is None and row["selectedTargetOrigin"] == "held", "text-free held target")
        need(row["sourceIdExactMatchCount"] == row["sourceTextExactMatchCount"] == 0 and not row["callerContextRefs"], "callerless hold evidence")
    if chosen is not None:
        need(sha(chosen) == row["selectedTargetSha256"], "selected target hash")
    checks = row["tokenAndLiteralChecks"]
    source_tokens, current_tokens = TOKEN_RE.findall(row["source"]), TOKEN_RE.findall(row["currentTarget"])
    source_numbers, current_numbers = NUMBER_RE.findall(row["source"]), NUMBER_RE.findall(row["currentTarget"])
    source_literals = protected(row["source"])
    need(checks["sourcePlaceholderTokens"] == source_tokens and checks["currentPlaceholderTokens"] == current_tokens, "current token inventory")
    need(checks["currentPlaceholderMultisetMatches"] == (sorted(source_tokens) == sorted(current_tokens)), "current token check")
    need(checks["sourceNumericTokens"] == source_numbers and checks["currentNumericTokens"] == current_numbers, "current numeric inventory")
    need(checks["currentNumericTokensPreserved"] == (source_numbers == current_numbers), "current numeric check")
    need(checks["sourceProtectedLiterals"] == source_literals, "source protected literal inventory")
    if chosen is not None:
        chosen_tokens, chosen_numbers = TOKEN_RE.findall(chosen), NUMBER_RE.findall(chosen)
        chosen_literals = [t for t in source_literals if re.search(r"(?<![A-Za-z0-9])"+re.escape(t)+r"(?![A-Za-z0-9])", chosen)]
        need(checks["selectedPlaceholderTokens"] == chosen_tokens and checks["selectedPlaceholderMultisetMatches"] == (sorted(source_tokens) == sorted(chosen_tokens)), "selected placeholder check")
        need(checks["selectedNumericTokens"] == chosen_numbers and checks["selectedNumericTokensPreserved"] == (source_numbers == chosen_numbers), "selected numeric check")
        need(checks["selectedProtectedLiterals"] == chosen_literals and checks["missingSelectedProtectedLiterals"] == [t for t in source_literals if t not in chosen_literals], "selected literal inventory")
        need(checks["selectedProtectedLiteralsPreserved"] == (not [t for t in source_literals if t not in chosen_literals]), "selected literal check")

need(provenance["priorSelectionReattestationCount"] == 100 and provenance["priorHoldReattestationCount"] == 444, "prior reattestation provenance counts")
need(sha((HERE/"prior-selection-reattestation.jsonl").read_bytes()) == provenance["priorSelectionReattestationSha256"], "prior selected source hash")
need(sha((HERE/"prior-hold-reattestation.jsonl").read_bytes()) == provenance["priorHoldReattestationSha256"], "prior held cell hash")

print("PASS clean blind W485-W504: pinned candidate-free input verified; 240 cells independently reviewed; 201 accept-current, 14 corrections, 1 refinement, 24 text-free callerless holds; exact 100/444 input reattestations; nested checksums and target token/literal checks pass.")
