#!/usr/bin/env python3
from pathlib import Path
import collections
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INPUT = (HERE.parent / "romarrng-pr70-w465-484-candidate-free-20261103" / "input").resolve()
HEAD = "7640720c5e3b1813725cca8d7aa46b5d968bff43"
TREE = "bdee162cc11115256df8756f192b19d4337ed1dc"
BRANCH = "task/localization-translation-review-20261030"
REPO = "snapetech-org/ROMarrNG"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PROTECTED = ["ROMarr", "GG Requestz", "RomM", "ROMm", "ES-DE", "gamelist.xml", "1G1R", "Battle.net", "No-Intro", "Redump", "RetroArch", "Steam", "EA", "Epic", "ROM", "Hub", "DAT"]
TOKEN_RE = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
EXTRA_LITERALS = {475: ["GG Requestz"], 476: ["GG Requestz"], 479: ["GOG"], 483: ["GameCube"]}

def fail(message):
    raise SystemExit("FAIL: " + message)

def ok(value, message):
    if not value:
        fail(message)

def sha(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def j(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def jl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

def protected_terms(text):
    return sorted([term for term in PROTECTED if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text)], key=lambda term: text.find(term))

def compact_ref(ref):
    keys = ("path", "lineStart", "lineEnd", "role", "anchor", "contextSha256", "fileSha256", "gitBlob")
    return {key: ref[key] for key in keys if key in ref}

# Packet checksums cover every top-level file except the checksum list itself.
sums_path = HERE / "SHA256SUMS.txt"
checksum_rows = {}
for line in sums_path.read_text(encoding="utf-8").splitlines():
    digest, name = line.split("  ", 1)
    ok(name not in checksum_rows, "duplicate checksum path " + name)
    checksum_rows[name] = digest
actual = {path.name for path in HERE.iterdir() if path.is_file() and path.name != "SHA256SUMS.txt"}
ok(set(checksum_rows) == actual, "packet checksum inventory")
for name, digest in checksum_rows.items():
    ok(sha((HERE / name).read_bytes()) == digest, "packet checksum " + name)

manifest = j(HERE / "manifest.json")
summary = j(HERE / "summary.json")
ok(manifest["head"] == HEAD and manifest["tree"] == TREE and manifest["branch"] == BRANCH, "exact manifest pin")
ok(manifest["repository"] == REPO and manifest["pullRequest"] == 70 and manifest["window"] == "W465-W484", "manifest identity")
ok(manifest["cellCount"] == 240 and manifest["sourceCount"] == 20 and manifest["localeCount"] == 12, "manifest coverage")
ok(manifest["nativeSpeakerReview"] == "not performed" and manifest["browserReview"] == "not performed", "review limitations")
listed = {row["path"]: row for row in manifest["files"]}
expected_payload = actual - {"manifest.json"}
ok(set(listed) == expected_payload, "manifest file inventory")
for name, row in listed.items():
    ok(row["sha256"] == sha((HERE / name).read_bytes()) and row["sizeBytes"] == (HERE / name).stat().st_size, "manifest file pin " + name)
ok(manifest["candidateFreeInputRelativePath"] == "../romarrng-pr70-w465-484-candidate-free-20261103/input", "relative input path")
ok(INPUT.is_dir(), "candidate-free input exists")
input_verify = subprocess.run(["python3", str(INPUT / "verify_input.py")], cwd=INPUT, capture_output=True, text=True)
ok(input_verify.returncode == 0, "candidate-free verifier: " + input_verify.stdout + input_verify.stderr)
input_manifest = j(INPUT / "manifest.json")
ok(input_manifest["head"] == HEAD and input_manifest["tree"] == TREE and input_manifest["window"] == "W465-W484", "candidate-free exact pin")
ok(input_manifest["candidateFree"] is True and input_manifest["proposedTargetsIncluded"] is False and input_manifest["reviewDecisionsIncluded"] is False, "candidate-free boundary")
ok(sha((INPUT / "manifest.json").read_bytes()) == manifest["candidateFreeInputManifestSha256"], "candidate-free manifest hash")
ok(sha((INPUT / "SHA256SUMS.txt").read_bytes()) == manifest["candidateFreeInputChecksumsSha256"], "candidate-free checksum list hash")

attestations = [j(HERE / "PR-attestation-before.json"), j(HERE / "PR-attestation-after.json")]
for name, record in zip(("before", "after"), attestations):
    ok(record["repository"] == REPO and record["pullRequest"] == 70, name + " PR identity")
    ok(record["state"] == "OPEN" and record["isDraft"] is True, name + " PR state")
    ok(record["branch"] == BRANCH and record["baseBranch"] == "main", name + " PR branch")
    ok(record["head"] == HEAD and record["tree"] == TREE, name + " exact PR head/tree")
    ok(record["liveBranchRef"] == HEAD and record["livePullRef"] == HEAD, name + " remote refs")
    ok(record["matchesPinnedHeadTree"] and record["matchesBothRemoteRefs"], name + " ref attestation")
ok(attestations[0]["head"] == attestations[1]["head"] and attestations[0]["tree"] == attestations[1]["tree"], "PR unchanged across primary review")

sources = {row["position"]: row for row in jl(INPUT / "source-inventory-selection.jsonl")}
contexts = {row["position"]: row for row in jl(INPUT / "source-contexts.jsonl")}
cells = jl(INPUT / "current-target-cells.jsonl")
cell_by_key = {(row["position"], row["locale"]): row for row in cells}
ledger = jl(HERE / "primary-ledger.jsonl")
expected_order = [(pos, locale) for pos in range(465, 485) for locale in LOCALES]
ok([(row["position"], row["locale"]) for row in ledger] == expected_order, "ledger coverage and order")
ok(len(ledger) == 240 and len(cell_by_key) == 240, "ledger/candidate cell counts")
counts = collections.Counter(row["disposition"] for row in ledger)
ok(dict(sorted(counts.items())) == summary["dispositions"] == manifest["dispositions"], "disposition counts")
ok(summary["head"] == HEAD and summary["tree"] == TREE and summary["cellCount"] == 240, "summary pin and coverage")
ok(summary["candidateFreeInputVerified"] is True and summary["primaryProposalsReadBeforeReview"] is False and summary["blindReviewOutputInspected"] is False, "review provenance")
ok(summary["priorLineageSelectionsReattested"] == 80 and summary["priorHoldCellsReattested"] == 384, "prior lineage counts")
ok(summary["sourceContextAvailable"] == 15 and summary["callerlessCellCount"] == 60, "caller context counts")
ok(summary["nativeSpeakerReview"].startswith("not performed") and summary["browserReview"] == "not performed", "review limits")

hold_positions = {470, 471, 473, 474, 477}
ok(set(summary["holdPositions"]) == hold_positions, "held positions")
prior_hold_rows = jl(INPUT / "prior-hold-reattestation.jsonl")
ok(len(prior_hold_rows) == 384 and all(row["sourceMatchesCurrentCatalog"] and row["selectionPositionMatches"] and row["targetUnchanged"] for row in prior_hold_rows), "carried hold reattestation")
prior_selection_rows = jl(INPUT / "prior-selection-reattestation.jsonl")
ok(len(prior_selection_rows) == 80 and all(row["selectionUnchanged"] for row in prior_selection_rows), "prior selection reattestation")

baseline_literal_mismatches = set()
for mismatch in j(INPUT / "current-target-protected-literal-mismatches.json")["mismatches"]:
    baseline_literal_mismatches.add((mismatch["position"], mismatch["sourceId"], mismatch["locale"]))
proposal_count = 0
selected_placeholder_mismatches = 0
selected_numeric_mismatches = 0
selected_literal_mismatches = 0
current_extra_mismatches = 0

for row in ledger:
    key = (row["position"], row["locale"])
    cell = cell_by_key[key]
    source = sources[row["position"]]
    context = contexts[row["position"]]
    ok(row["sourceId"] == source["sourceId"] == cell["sourceId"], "source id lineage " + str(key))
    ok(row["source"] == cell["source"] == source["source"], "source text lineage " + str(key))
    ok(row["sourceSha256"] == cell["sourceSha256"] == source["sourceSha256"] == sha(row["source"]), "source hash " + str(key))
    ok(row["currentTarget"] == cell["currentTarget"] and row["currentTargetSha256"] == cell["currentTargetSha256"] == sha(row["currentTarget"]), "current target hash " + str(key))
    ok(row["catalogTranslationHash"] == cell["catalogTranslationHash"] == sha(canon(row["currentTarget"])), "catalog translation hash " + str(key))
    ok(row["inputCallerContextSha256"] == cell["callerContextSha256"] == context["callerContextSha256"], "caller context hash " + str(key))
    ok(row["selectedCallerContextRefs"] == [compact_ref(ref) for ref in context["callerContextRefs"]], "caller references " + str(key))
    ok(row["activeSourceRegistry"] == source["activeSourceRegistry"] and row["activeSourceRank"] == source["activeSourceRank"], "source registry evidence " + str(key))
    ok(row["rationale"] and row["reviewedContext"], "review rationale " + str(key))

    disposition = row["disposition"]
    if disposition == "hold":
        ok(row["position"] in hold_positions, "hold position " + str(key))
        ok(row["proposedTarget"] is None and row["selectedTarget"] is None, "held target is not adjudicated " + str(key))
        ok(not context["callerContextRefs"], "held cell has no exact caller " + str(key))
        ok(row["proposedTargetSha256"] is None and row["selectedTargetSha256"] is None, "held hashes are null " + str(key))
    else:
        ok(row["position"] not in hold_positions, "nonhold position " + str(key))
        ok(context["callerContextRefs"], "reviewed cell has exact caller " + str(key))
        if disposition == "accept-current":
            ok(row["proposedTarget"] is None and row["selectedTarget"] == row["currentTarget"], "accept-current target " + str(key))
            ok(row["proposedTargetSha256"] is None, "accept-current proposal hash " + str(key))
        elif disposition in ("correction", "refinement"):
            proposal_count += 1
            ok(isinstance(row["proposedTarget"], str) and row["selectedTarget"] == row["proposedTarget"], "proposal target " + str(key))
            ok(row["proposedTargetSha256"] == sha(row["proposedTarget"]), "proposal hash " + str(key))
        else:
            fail("unknown disposition " + disposition)
        ok(row["selectedTargetSha256"] == sha(row["selectedTarget"]), "selected target hash " + str(key))

    checks = row["tokenAndLiteralChecks"]
    source_tokens = TOKEN_RE.findall(row["source"])
    current_tokens = TOKEN_RE.findall(row["currentTarget"])
    source_numbers = NUMBER_RE.findall(row["source"])
    current_numbers = NUMBER_RE.findall(row["currentTarget"])
    source_terms = protected_terms(row["source"])
    current_terms = [term for term in source_terms if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", row["currentTarget"])]
    ok(checks["sourcePlaceholderTokens"] == source_tokens and checks["currentPlaceholderTokens"] == current_tokens, "placeholder inventory " + str(key))
    ok(checks["sourceNumericTokens"] == source_numbers and checks["currentNumericTokens"] == current_numbers, "numeric inventory " + str(key))
    ok(checks["sourceProtectedLiterals"] == source_terms and checks["currentProtectedLiterals"] == current_terms, "protected literal inventory " + str(key))
    if row["selectedTarget"] is None:
        ok(checks["selectedPlaceholderTokens"] is None and checks["selectedNumericTokens"] is None and checks["selectedProtectedLiterals"] is None, "held token selections null " + str(key))
        ok(checks["selectedPlaceholderMultisetMatches"] is False and checks["selectedNumericTokensExactMatch"] is False and checks["selectedProtectedLiteralsPreserved"] is False, "held token flags " + str(key))
    else:
        selected = row["selectedTarget"]
        selected_tokens = TOKEN_RE.findall(selected)
        selected_numbers = NUMBER_RE.findall(selected)
        selected_terms = protected_terms(selected)
        placeholder_ok = sorted(source_tokens) == sorted(selected_tokens)
        numeric_ok = source_numbers == selected_numbers
        literal_ok = all(term in selected_terms for term in source_terms)
        ok(checks["selectedPlaceholderTokens"] == selected_tokens and checks["selectedPlaceholderMultisetMatches"] == placeholder_ok, "selected placeholders " + str(key))
        ok(checks["selectedNumericTokens"] == selected_numbers and checks["selectedNumericTokensExactMatch"] == numeric_ok, "selected numeric tokens " + str(key))
        ok(checks["selectedProtectedLiterals"] == selected_terms and checks["selectedProtectedLiteralsPreserved"] == literal_ok, "selected protected literals " + str(key))
        selected_placeholder_mismatches += not placeholder_ok
        selected_numeric_mismatches += not numeric_ok
        selected_literal_mismatches += not literal_ok
        ok(placeholder_ok and numeric_ok and literal_ok, "selected token/literal preservation " + str(key))

    extra_terms = EXTRA_LITERALS.get(row["position"], [])
    ok(checks["additionalNamedTerms"] == extra_terms, "named product term inventory " + str(key))
    current_extra_ok = all(re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", row["currentTarget"]) for term in extra_terms)
    ok(checks["currentAdditionalNamedTermsPreserved"] == current_extra_ok, "current named product terms " + str(key))
    if extra_terms and not current_extra_ok:
        current_extra_mismatches += 1
    selected_extra_ok = row["selectedTarget"] is not None and all(re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", row["selectedTarget"]) for term in extra_terms)
    ok(checks["selectedAdditionalNamedTermsPreserved"] == selected_extra_ok, "selected named product terms " + str(key))
    if row["selectedTarget"] is not None:
        ok(selected_extra_ok, "selected product literal " + str(key))

ok(counts["hold"] == 60 and counts["accept-current"] == 170 and counts["correction"] == 6 and counts["refinement"] == 4, "expected disposition totals")
ok(proposal_count == 10 and summary["proposedCellCount"] == 10 == manifest["proposedCellCount"], "proposal count")
ok(selected_placeholder_mismatches == selected_numeric_mismatches == selected_literal_mismatches == 0, "selected mismatch totals")
numeric_mismatch_report = j(INPUT / "current-target-numeric-mismatches.json")
numeric_mismatch_rows = numeric_mismatch_report["mismatches"]
ledger_by_key = {(row["position"], row["locale"]): row for row in ledger}
ok(len(numeric_mismatch_rows) == 2 == summary["currentTargetNumericMismatches"], "baseline numeric mismatch count")
ok(all((item["position"] in hold_positions) and ledger_by_key[(item["position"], item["locale"])]["disposition"] == "hold" for item in numeric_mismatch_rows), "baseline numeric mismatches remain held")
ok(summary["placeholderMismatchesInSelectedTargets"] == 0, "placeholder summary")
ok(summary["numericExactMismatchesAfterSemanticReview"] == 0, "numeric summary")
ok([(x["position"],x["locale"],x["sourceNumbers"],x["currentNumbers"]) for x in summary["numericMismatchCellsHeld"]] == [(x["position"],x["locale"],x["sourceTokens"],x["targetTokens"]) for x in numeric_mismatch_rows], "held numeric mismatch evidence")
ok(all(x["position"] == 474 and "three hours" in x["holdReason"] and "digit 3" in x["holdReason"] for x in summary["numericMismatchCellsHeld"]), "held numeric semantic note")
ok(summary["protectedLiteralMismatchesInSelectedTargets"] == 0, "literal summary")
ok(current_extra_mismatches == 0, "current named product literal preservation")
ok(baseline_literal_mismatches == set(), "baseline literal mismatch identity")
held_counter = collections.Counter(row["position"] for row in ledger if row["disposition"] == "hold")
ok(dict(held_counter) == {470: 12, 471: 12, 473: 12, 474: 12, 477: 12}, "held cells per position")

print(
    "PASS primary W465-W484: exact pinned PR/tree; 240 cells; 170 accept-current, "
    "6 corrections, 4 refinements, 60 caller-context holds; 10 proposals; "
    "80 prior selections and 384 carried holds reattested; all selected placeholders, "
    "numeric tokens, protected literals, and named product terms pass; candidate-free input and packet checksums pass."
)

