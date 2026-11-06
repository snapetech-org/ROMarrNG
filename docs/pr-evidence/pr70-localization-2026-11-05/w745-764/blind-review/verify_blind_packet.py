#!/usr/bin/env python3
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

INPUT = Path("/mnt/disks/scratch/task-scratch/romarrng-pr70-w745-764-20261105/candidate-free")
OUT = Path(__file__).resolve().parent
HEAD = "68c5c9d4ad13ad5d02b9c455f429d8a5149d363d"
TREE = "524db27557a65d64343b15c9983f6ac2f92f90c4"
EXPECTED_OUTPUTS = {
    "README.md",
    "blind-ledger.jsonl",
    "candidate-free-manifest.json",
    "candidate-free-verification.json",
    "input-SHA256SUMS.txt",
    "prior-active-holds-hash-only.jsonl",
    "prior-hold-summary.json",
    "summary.json",
    "verify_blind_packet.py",
    "SHA256SUMS.txt",
}
EXPECTED_CORRECTIONS = {
    ("ui.nothing-matches.965b516df3", "de"): "Keine Treffer",
    ("ui.nothing-matches.965b516df3", "hi"): "कोई परिणाम नहीं मिला",
    ("ui.nothing-matches.965b516df3", "ko"): "일치하는 항목이 없습니다",
    ("ui.nothing-matches.965b516df3", "pt-BR"): "Nenhum resultado encontrado.",
    ("ui.nothing-matches.965b516df3", "vi"): "Không có kết quả phù hợp",
    ("ui.nothing-missing.ec939b22fd", "hi"): "कुछ भी गायब नहीं है।",
}
TEXT_FIELDS = {
    "source", "target", "currentTarget", "translation", "proposal",
    "proposedTarget", "sourceText", "targetText"
}

def fail(message):
    raise SystemExit("FAIL: " + message)

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def sha_text(value):
    return sha_bytes(value.encode("utf-8"))

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

def checksum_map(folder, sums_path):
    result = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            digest, relative = line.split("  ", 1)
        except ValueError:
            fail(str(sums_path) + ": malformed checksum line")
        if relative.startswith("/") or ".." in Path(relative).parts:
            fail(str(sums_path) + ": unsafe checksum path")
        if relative in result:
            fail(str(sums_path) + ": duplicate checksum path " + relative)
        path = folder / relative
        if not path.is_file() or sha_bytes(path.read_bytes()) != digest:
            fail(str(sums_path) + ": checksum mismatch " + relative)
        result[relative] = digest
    actual = {
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if path.is_file() and path != sums_path
    }
    if actual != set(result):
        fail(str(sums_path) + ": checksum coverage mismatch")
    return result

def token_list(value):
    return sorted(re.findall(r"\{[^{}]+\}", value))

def caller_refs(context):
    return [
        {
            "file": caller["path"],
            "line": caller["line"],
            "lineSha256": caller["lineSha256"],
            "excerptSha256": caller["excerptSha256"],
            "matchKind": caller["matchKind"],
        }
        for caller in context.get("callers", [])
    ]

def main():
    input_sums = INPUT / "SHA256SUMS.txt"
    if not input_sums.is_file():
        fail("candidate-free checksum file is missing")
    if (OUT / "input-SHA256SUMS.txt").read_bytes() != input_sums.read_bytes():
        fail("copied candidate-free checksum list differs")
    checksum_map(INPUT, input_sums)
    output_sum_path = OUT / "SHA256SUMS.txt"
    if not output_sum_path.is_file():
        fail("output checksum file is missing")
    checksum_map(OUT, output_sum_path)

    actual_outputs = {
        path.relative_to(OUT).as_posix()
        for path in OUT.rglob("*")
        if path.is_file()
    }
    if actual_outputs != EXPECTED_OUTPUTS:
        fail("output files differ from the sealed packet inventory")

    manifest = read_json(INPUT / "input/manifest.json")
    copied_manifest = OUT / "candidate-free-manifest.json"
    if copied_manifest.read_bytes() != (INPUT / "input/manifest.json").read_bytes():
        fail("copied candidate-free manifest differs")
    if sha_bytes(copied_manifest.read_bytes()) != manifest["manifestSha256"] if "manifestSha256" in manifest else False:
        fail("candidate-free manifest self-hash mismatch")
    if manifest.get("repository") != "snapetech-org/ROMarrNG" or manifest.get("pullRequest") != 70:
        fail("wrong repository or pull request pin")
    if manifest.get("head") != HEAD or manifest.get("tree") != TREE:
        fail("candidate-free product head/tree mismatch")
    if manifest.get("window") != "W745-W764" or manifest.get("cellCount") != 240:
        fail("candidate-free window or cell count mismatch")
    if manifest.get("callerBackedCells") != 216 or manifest.get("callerlessHashOnlyCells") != 24:
        fail("candidate-free caller-backed/callerless counts mismatch")
    if manifest.get("priorActiveHoldsReattested") != 964 or manifest.get("resultingActiveHashOnlyHolds") != 988:
        fail("candidate-free hold-chain counts mismatch")

    sources = read_jsonl(INPUT / "input/selected-sources.jsonl")
    cells = read_jsonl(INPUT / "input/candidate-free-cells.jsonl")
    contexts = read_jsonl(INPUT / "input/source-contexts.jsonl")
    if len(sources) != 20 or len(cells) != 240:
        fail("candidate-free source/cell count mismatch")
    source_by_id = {row["sourceId"]: row for row in sources}
    context_by_id = {row["sourceId"]: row for row in contexts}
    if len(source_by_id) != 20 or len(context_by_id) != 20:
        fail("candidate-free source/context IDs are duplicated or missing")
    callerless_sources = {
        row["sourceId"] for row in sources if row.get("sourceTextOmitted") is True
    }
    if len(callerless_sources) != 2:
        fail("callerless source count mismatch")

    input_by_key = {}
    for cell in cells:
        key = (cell["sourceId"], cell["locale"])
        if key in input_by_key:
            fail("duplicate candidate-free cell " + repr(key))
        input_by_key[key] = cell
        if cell.get("callerless"):
            if key[0] not in callerless_sources:
                fail("callerless cell has no source-level hold")
            if any(field in cell for field in TEXT_FIELDS):
                fail("candidate-free callerless input contains text")
            if cell.get("currentTargetSha256") is None or cell.get("sourceSha256") is None:
                fail("callerless input is missing a hash pin")
        else:
            source = source_by_id.get(key[0])
            context = context_by_id.get(key[0])
            if source is None or context is None or source.get("sourceTextOmitted"):
                fail("caller-backed cell lacks source/context text")
            if context.get("callerless") or not context.get("callers"):
                fail("caller-backed cell has no pinned production caller")
            if context.get("head") != HEAD or context.get("sourceSha256") != cell["sourceSha256"]:
                fail("source/caller head or source hash mismatch")
            if cell.get("source") != source.get("source") or sha_text(cell["source"]) != cell["sourceSha256"]:
                fail("current source text/hash mismatch")
            if not isinstance(cell.get("currentTarget"), str) or sha_text(cell["currentTarget"]) != cell["currentTargetSha256"]:
                fail("current target text/hash mismatch")
            if context.get("contextSha256") != cell.get("callerContextSha256"):
                fail("caller context fingerprint mismatch")
            if not all(cell.get(flag) is True for flag in (
                "markupMatches", "numericTokensPreserved",
                "placeholderMultisetMatches", "protectedLiteralsPreserved"
            )):
                fail("candidate-free token/literal pin failed")
            if token_list(cell["source"]) != token_list(cell["currentTarget"]):
                fail("candidate-free placeholder token mismatch")

    if len(input_by_key) != 240:
        fail("candidate-free cell-key count mismatch")

    ledger = read_jsonl(OUT / "blind-ledger.jsonl")
    if len(ledger) != 240:
        fail("blind ledger does not contain 240 cells")
    ledger_by_key = {}
    for row in ledger:
        key = (row.get("sourceId"), row.get("locale"))
        if key in ledger_by_key:
            fail("duplicate blind ledger cell " + repr(key))
        ledger_by_key[key] = row
    if set(ledger_by_key) != set(input_by_key):
        fail("blind ledger cell keys differ from candidate-free input")

    for key, source_cell in input_by_key.items():
        row = ledger_by_key[key]
        if row.get("window") != "W745-W764" or row.get("head") != HEAD or row.get("tree") != TREE:
            fail("blind row exact pin mismatch")
        if row.get("sourceSha256") != source_cell["sourceSha256"] or row.get("currentTargetSha256") != source_cell["currentTargetSha256"]:
            fail("blind row source/target hash mismatch")
        if row.get("callerContextSha256") != source_cell["callerContextSha256"]:
            fail("blind row caller-context hash mismatch")
        callerless = bool(source_cell.get("callerless"))
        if row.get("callerless") is not callerless:
            fail("blind row callerless classification mismatch")
        if callerless:
            if row.get("action") != "hold" or row.get("reasonCode") != "callerless-hash-only":
                fail("callerless row is not held hash-only")
            if any(field in row for field in TEXT_FIELDS):
                fail("callerless blind row contains text")
            if row.get("sourceTextOmitted") is not True or row.get("targetTextOmitted") is not True:
                fail("callerless blind row lacks text-omission attestations")
            continue

        source = source_cell["source"]
        target = source_cell["currentTarget"]
        if row.get("source") != source or row.get("currentTarget") != target:
            fail("blind row source/current target differs from candidate-free input")
        context = context_by_id[key[0]]
        if row.get("callerEvidence") != caller_refs(context):
            fail("blind row caller evidence differs from pinned context")
        if row.get("action") == "correction":
            proposed = EXPECTED_CORRECTIONS.get(key)
            if proposed is None or row.get("proposedTarget") != proposed:
                fail("unexpected or changed correction proposal")
            if token_list(source) != token_list(proposed):
                fail("correction proposal placeholder tokens mismatch")
        elif row.get("action") == "retain":
            if key in EXPECTED_CORRECTIONS or "proposedTarget" in row:
                fail("retained row unexpectedly has a correction")
        else:
            fail("caller-backed row has an invalid action")

    observed_corrections = {
        key: row["proposedTarget"]
        for key, row in ledger_by_key.items()
        if row.get("action") == "correction"
    }
    if observed_corrections != EXPECTED_CORRECTIONS:
        fail("correction decision set differs")
    counts = Counter(row["action"] for row in ledger)
    if counts != Counter({"retain": 210, "correction": 6, "hold": 24}):
        fail("blind action counts mismatch")

    prior_input = INPUT / "input/prior-hold-reattestation.jsonl"
    prior_output = OUT / "prior-active-holds-hash-only.jsonl"
    if prior_output.read_bytes() != prior_input.read_bytes():
        fail("prior hold chain differs from candidate-free input")
    prior_holds = read_jsonl(prior_output)
    if len(prior_holds) != 964:
        fail("prior hold count mismatch")
    for row in prior_holds:
        if row.get("textOmitted") is not True:
            fail("prior hold is not text-free")
        if any(field in row for field in TEXT_FIELDS):
            fail("prior hold row contains text")
        if row.get("targetUnchanged") is not True or row.get("currentTargetSha256") != row.get("priorTargetSha256"):
            fail("prior hold target hash changed")
        if row.get("reattestedAtHead") != HEAD:
            fail("prior hold was not reattested at the current head")
        if not row.get("sourceSha256") or not row.get("currentTargetSha256"):
            fail("prior hold hash is missing")

    summary = read_json(OUT / "summary.json")
    if summary.get("head") != HEAD or summary.get("tree") != TREE or summary.get("window") != "W745-W764":
        fail("summary exact pin mismatch")
    if summary.get("cellCount") != 240 or summary.get("callerBackedCellCount") != 216:
        fail("summary cell counts mismatch")
    if summary.get("decisionCounts") != dict(counts):
        fail("summary decision counts mismatch")
    if summary.get("priorActiveHoldsReattested") != 964 or summary.get("resultingActiveHashOnlyHolds") != 988:
        fail("summary hold counts mismatch")
    if summary.get("primaryProposalContentUsed") is not False:
        fail("blind independence attestation missing")
    if summary.get("candidateFreeChecksumListSha256") != sha_bytes(input_sums.read_bytes()):
        fail("summary candidate-free checksum pin mismatch")
    verification = read_json(OUT / "candidate-free-verification.json")
    if verification.get("candidateFreeOnly") is not True or verification.get("candidateFreeVerifierResult") != "PASS":
        fail("candidate-free verifier attestation missing")
    if verification.get("head") != HEAD or verification.get("tree") != TREE or verification.get("worktreeClean") is not True:
        fail("candidate-free worktree verification mismatch")

    print(json.dumps({
        "result": "PASS",
        "head": HEAD,
        "tree": TREE,
        "window": "W745-W764",
        "cells": len(ledger),
        "callerBacked": 216,
        "callerlessHashOnlyHolds": 24,
        "decisionCounts": dict(counts),
        "priorActiveHolds": len(prior_holds),
        "resultingActiveHashOnlyHolds": len(prior_holds) + counts["hold"],
        "primaryProposalContentUsed": False,
        "candidateFreeOnly": True
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
