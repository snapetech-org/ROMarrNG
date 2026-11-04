#!/usr/bin/env python3
"""Verify ROMarrNG PR #70 W485-W504 primary semantic review packet."""
from pathlib import Path
import collections
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
HEAD = "6eb494d362ae19503b9199cd2c05c0767cddbc0e"
TREE = "b9450b9c6d22c816551fc8d528e8f03413d04595"
BRANCH = "task/localization-translation-review-20261030"
WINDOW = "W485-W504"
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

def j(path):
    return json.loads(path.read_text(encoding="utf-8"))

def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def protected(text):
    return [term for term in PROTECTED if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text)]

# Checksum inventory covers every packet file except itself.
checksum_rows = {}
for line in (HERE / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    match = re.fullmatch(r"([0-9a-f]{64})  ([^/][^\n]*)", line)
    need(match is not None, "malformed checksum row")
    digest, name = match.groups()
    need(name not in checksum_rows and Path(name).name == name, "duplicate or unsafe checksum path")
    checksum_rows[name] = digest
actual = {p.name for p in HERE.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt"}
need(set(checksum_rows) == actual, "checksum file inventory")
for name, digest in checksum_rows.items():
    need(sha((HERE / name).read_bytes()) == digest, "checksum " + name)

manifest = j(HERE / "manifest.json")
summary = j(HERE / "summary.json")
provenance = j(HERE / "provenance.json")
need(manifest["head"] == HEAD and manifest["tree"] == TREE and manifest["branch"] == BRANCH and manifest["window"] == WINDOW, "manifest pinned refs")
need(manifest["sourceCount"] == 20 and manifest["localeCount"] == 12 and manifest["cellCount"] == 240, "manifest cell coverage")
need(manifest["priorSelectedSourceCount"] == 100 and manifest["priorHoldCellCount"] == 444, "manifest prior lineage counts")
need(summary["candidateFreeInputVerified"] is True and summary["primaryProposalsReadBeforeReview"] is False, "review boundary provenance")
need(summary["head"] == HEAD and summary["tree"] == TREE and summary["cellCount"] == 240, "summary pins")
need(summary["candidateFreeInputManifestSha256"] == manifest["candidateFreeInputManifestSha256"], "summary/input manifest hash")
need(provenance["candidateFreeInputHead"] == HEAD and provenance["candidateFreeInputTree"] == TREE, "input provenance refs")
need(provenance["candidateFreeInputManifestSha256"] == manifest["candidateFreeInputManifestSha256"], "provenance input manifest hash")
need(manifest["dispositions"] == summary["dispositions"] and manifest["proposedCellCount"] == summary["proposedCellCount"] and manifest["newHoldCellCount"] == summary["newHolds"], "manifest summary counts")
need(sha((HERE/"primary-ledger.jsonl").read_bytes()) == manifest["primaryLedgerSha256"], "primary ledger manifest hash")
need(sha((HERE/"summary.json").read_bytes()) == manifest["summarySha256"], "summary manifest hash")
need(sha((HERE/"prior-selection-reattestation.jsonl").read_bytes()) == manifest["priorSelectionReattestationSha256"], "prior selection manifest hash")
need(sha((HERE/"prior-hold-reattestation.jsonl").read_bytes()) == manifest["priorHoldReattestationSha256"], "prior hold manifest hash")

input_path = Path(provenance["candidateFreeInputPath"])
need(sha((HERE / "candidate-free-manifest.json").read_bytes()) == manifest["candidateFreeInputManifestSha256"], "copied candidate-free manifest hash")
for name in ("PR-attestation.json", "PR-attestation-before.json", "PR-attestation-after.json"):
    need(sha((HERE / ("candidate-free-" + name)).read_bytes()) == provenance["candidateFreeAttestationFiles"][name], "copied candidate-free attestation hash " + name)
if input_path.is_dir():
    sums = {}
    for line in (input_path / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        sums[name] = digest
    need(all(sha((input_path/name).read_bytes()) == digest for name, digest in sums.items()), "candidate-free input checksum verification")
    need(sha((input_path/"manifest.json").read_bytes()) == manifest["candidateFreeInputManifestSha256"], "candidate-free input manifest pin")
    need(sha((input_path/"SHA256SUMS.txt").read_bytes()) == manifest["candidateFreeInputChecksumListSha256"], "candidate-free input checksum-list pin")
    verified = subprocess.run([sys.executable, str(input_path/"verify_input.py")], capture_output=True, text=True)
    need(verified.returncode == 0, "candidate-free input verifier: " + verified.stdout + verified.stderr)
    for name in ("prior-selection-reattestation.jsonl", "prior-hold-reattestation.jsonl"):
        need((HERE/name).read_bytes() == (input_path/name).read_bytes(), "exact copied prior reattestation " + name)
    for name in ("manifest.json", "PR-attestation.json", "PR-attestation-before.json", "PR-attestation-after.json"):
        need((HERE/("candidate-free-"+name)).read_bytes() == (input_path/name).read_bytes(), "exact copied candidate-free input file " + name)

ledger = jl(HERE / "primary-ledger.jsonl")
need(len(ledger) == 240, "primary ledger row count")
need([(r["position"], r["locale"]) for r in ledger] == [(pos, loc) for pos in range(485, 505) for loc in LOCALES], "primary ledger cell order")
counts = collections.Counter(r["disposition"] for r in ledger)
need(dict(counts) == summary["dispositions"], "summary disposition counts")
need(dict(counts) == {"accept-current": 201, "correction": 14, "refinement": 1, "hold": 24}, "expected primary disposition totals")
need(counts["correction"] + counts["refinement"] == summary["proposedCellCount"] == 15, "proposed cell count")
need(counts["hold"] == summary["newHolds"] == 24, "current hold count")
need(summary["placeholderMismatchesInSelectedTargets"] == summary["numericMismatchesInSelectedTargets"] == summary["protectedLiteralMismatchesInSelectedTargets"] == 0, "selected target token/literal summary")
locale_counts={}
for locale in LOCALES:
    locale_counts[locale]=dict(collections.Counter(r["disposition"] for r in ledger if r["locale"]==locale))
need(locale_counts == summary["localeDispositionCounts"], "locale disposition summary")
need(sorted({r["position"] for r in ledger if r["disposition"] == "hold"}) == [493, 502], "callerless hold positions")

if input_path.is_dir():
    input_cells = jl(input_path / "current-target-cells.jsonl")
    input_contexts = {r["sourceId"]: r for r in jl(input_path / "source-contexts.jsonl")}
    need(len(input_cells) == len(ledger), "candidate-free input cell count")
    for r, source in zip(ledger, input_cells):
        for key in ("position", "catalogZeroBasedIndex", "catalogOneBasedPosition", "sourceId", "source", "sourceSha256", "locale", "currentTarget", "currentTargetSha256", "catalogTranslationHash"):
            need(r[key] == source[key], "candidate-free input binding " + key + " at " + str(r.get("position")))
        ctx = input_contexts[r["sourceId"]]
        need(r["inputCallerContextSha256"] == ctx["callerContextSha256"], "caller context hash binding")
        expected_refs = [{k: ref[k] for k in ("path", "lineStart", "lineEnd", "contextSha256", "fileSha256", "gitBlob", "role", "anchor")} for ref in ctx["callerContextRefs"]]
        need(r["callerContextRefs"] == expected_refs, "caller context reference binding")
        need(r["sourceIdExactMatchCount"] == ctx["sourceIdExactMatchCount"] and r["sourceTextExactMatchCount"] == ctx["sourceTextExactMatchCount"], "caller search count binding")

for row in ledger:
    need(row["window"] == WINDOW and row["catalogZeroBasedIndex"] == row["position"] and row["catalogOneBasedPosition"] == row["position"] + 1, "cell catalog position")
    need(sha(row["source"]) == row["sourceSha256"], "cell source hash")
    need(sha(row["currentTarget"]) == row["currentTargetSha256"], "cell current target hash")
    need(sha(canon(row["currentTarget"])) == row["catalogTranslationHash"], "cell catalog translation hash")
    need(row["confidence"] in {"high", "moderate", "low", "unknown"}, "confidence label")
    need(row["disposition"] in {"accept-current", "correction", "refinement", "hold"}, "disposition label")
    prop = row["proposedTarget"]
    selected = row["selectedTarget"]
    if selected is not None:
        need(sha(selected) == row["selectedTargetSha256"], "selected target hash")
    if row["disposition"] == "accept-current":
        need(prop is None and selected == row["currentTarget"] and row["selectedTargetOrigin"] == "current", "accept-current target")
    elif row["disposition"] in {"correction", "refinement"}:
        need(isinstance(prop, str) and selected == prop and row["selectedTargetOrigin"] == "primary-review", "selected proposal target")
        need(sha(prop) == row["proposedTargetSha256"] == row["selectedTargetSha256"], "proposal target hashes")
    else:
        need(prop is None and selected is None and row["selectedTargetOrigin"] == "held", "held target boundary")
        need(row["sourceIdExactMatchCount"] == row["sourceTextExactMatchCount"] == 0 and row["callerContextRefs"] == [], "callerless hold evidence")
    checks = row["tokenAndLiteralChecks"]
    source_tokens = TOKEN_RE.findall(row["source"])
    current_tokens = TOKEN_RE.findall(row["currentTarget"])
    source_nums = NUMBER_RE.findall(row["source"])
    current_nums = NUMBER_RE.findall(row["currentTarget"])
    source_lits = protected(row["source"])
    need(checks["sourcePlaceholderTokens"] == source_tokens and checks["currentPlaceholderTokens"] == current_tokens, "token inventory")
    need(checks["currentPlaceholderMultisetMatches"] == (sorted(source_tokens) == sorted(current_tokens)), "current token preservation")
    need(checks["sourceNumericTokens"] == source_nums and checks["currentNumericTokens"] == current_nums, "numeric token inventory")
    need(checks["currentNumericTokensPreserved"] == (source_nums == current_nums), "current numeric preservation")
    need(checks["sourceProtectedLiterals"] == source_lits, "protected literal inventory")
    if selected is not None:
        selected_tokens = TOKEN_RE.findall(selected)
        selected_nums = NUMBER_RE.findall(selected)
        selected_lits = [term for term in source_lits if re.search(r"(?<![A-Za-z0-9])"+re.escape(term)+r"(?![A-Za-z0-9])", selected)]
        need(checks["selectedPlaceholderTokens"] == selected_tokens and checks["selectedPlaceholderMultisetMatches"] == (sorted(source_tokens) == sorted(selected_tokens)), "selected token preservation")
        need(checks["selectedNumericTokens"] == selected_nums and checks["selectedNumericTokensPreserved"] == (source_nums == selected_nums), "selected numeric preservation")
        need(checks["selectedProtectedLiterals"] == selected_lits and checks["missingSelectedProtectedLiterals"] == [t for t in source_lits if t not in selected_lits], "selected protected literals")
        need(checks["selectedProtectedLiteralsPreserved"] == (not [t for t in source_lits if t not in selected_lits]), "selected protected literal preservation")

prior_selection = jl(HERE / "prior-selection-reattestation.jsonl")
prior_holds = jl(HERE / "prior-hold-reattestation.jsonl")
need(len(prior_selection) == 100 and len(prior_holds) == 444, "prior reattestation record counts")
need(len({r["sourceId"] for r in prior_selection}) == 100, "unique prior selected sources")
need(all(r["selectionUnchanged"] and r["sourceHashMatches"] and r["registryMembershipAndHashMatch"] for r in prior_selection), "prior selected source reattestation flags")
need(all(r["sourceMatchesCurrentCatalog"] and r["selectionPositionMatches"] and r["targetUnchanged"] for r in prior_holds), "prior hold reattestation flags")
need(provenance["priorSelectedSourceReattestationCount"] == 100 and provenance["priorHoldReattestationCount"] == 444, "provenance reattestation counts")
need(sha((HERE/"prior-selection-reattestation.jsonl").read_bytes()) == provenance["priorSelectedSourceReattestationSha256"], "prior selection file hash")
need(sha((HERE/"prior-hold-reattestation.jsonl").read_bytes()) == provenance["priorHoldReattestationSha256"], "prior hold file hash")
need(summary["priorSelectedSourceCount"] == 100 and summary["priorHoldCellCount"] == 444 and summary["priorSelectionsUnchanged"] and summary["priorHoldTargetsUnchanged"], "summary prior lineage")

print("PASS primary W485-W504: 240 reviewed cells; 201 accept-current, 14 corrections, 1 refinement, 24 callerless holds; selected targets preserve placeholders, numbers, and protected literals; exact 100 selected-source and 444 hold reattestations; checksums and candidate-free input pins pass.")
