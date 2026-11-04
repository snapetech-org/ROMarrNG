#!/usr/bin/env python3
"""Build the independent W445-W464 primary review from candidate-free evidence only."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import re
import subprocess

OUT = Path(__file__).resolve().parent
IN = Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w465-484-candidate-free-20261103/input")
HEAD = "7640720c5e3b1813725cca8d7aa46b5d968bff43"
TREE = "bdee162cc11115256df8756f192b19d4337ed1dc"
BRANCH = "task/localization-translation-review-20261030"
REPO = "snapetech-org/ROMarrNG"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
TOKEN_RE = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
PROTECTED = ["ROMarr", "GG Requestz", "RomM", "ROMm", "ES-DE", "gamelist.xml", "1G1R", "Battle.net", "No-Intro", "Redump", "RetroArch", "Steam", "EA", "Epic", "ROM", "Hub", "DAT"]

PROPOSALS = {
    (475, "id"): ("correction", "Halaman GG Requestz", "The exact caller renders this as a status-row label. In Indonesian, the category noun precedes the service name; this order reads naturally as “GG Requestz page.”"),
    (475, "zh-Hans"): ("refinement", "GG Requestz 页面", "The exact caller labels the reachability row. The existing spaced form 页 次 splits one compound; 页面 is the natural Simplified Chinese word for page."),
    (475, "zh-Hant"): ("refinement", "GG Requestz 頁面", "The exact caller labels the reachability row. The existing spaced form 頁 次 splits one compound; 頁面 is the natural Traditional Chinese word for page."),
    (476, "de"): ("correction", "GG Requestz-Anfragen", "The caller is the webhook setup heading for requests sent from GG Requestz. Anfragen describes user requests more clearly than Anträge, which suggests formal applications."),
    (476, "id"): ("correction", "Permintaan GG Requestz", "The caller is the heading for inbound GG Requestz requests. Indonesian places the noun before its service modifier; the current order is awkward."),
    (479, "de"): ("refinement", "GOG-Benutzername", "The caller is a text-input label for a public GOG profile name. The hyphen forms the conventional German compound for a brand plus field label."),
    (479, "id"): ("refinement", "Nama pengguna GOG", "The caller labels a text field for the public GOG profile name. Indonesian places the field noun phrase before the service name."),
    (479, "pt-BR"): ("correction", "Nome de usuário do GOG", "The caller labels the public GOG profile-name input. This is the natural Brazilian Portuguese noun phrase; the current brand-first order is awkward."),
    (483, "hi"): ("correction", "0x1c पर GameCube डिस्क सिग्नेचर", "The exact caller reports the GameCube disc signature found at byte offset 0x1c. “सिग्नेचर” names that technical marker more clearly than the current transliterated “मैजिक.”"),
    (483, "id"): ("correction", "Tanda pengenal cakram GameCube pada 0x1c", "The exact caller reports a binary disc marker at offset 0x1c. “Tanda pengenal” describes the signature clearly; the current “nilai magic” wording is an awkward mixed-language calque."),
}

HOLD_POSITIONS = {
    470: "No active source-registry entry and no exact source-ID or complete source-text occurrence exists in pinned production code. The catalog entry has no evidenced live translation caller; keep its current targets held.",
    471: "No active source-registry entry and no exact source-ID or complete source-text occurrence exists in pinned production code. The catalog entry has no evidenced live translation caller; keep its current targets held.",
    473: "No active source-registry entry and no exact source-ID or complete source-text occurrence exists in pinned production code. The catalog entry has no evidenced live translation caller; keep its current targets held.",
    474: "No active source-registry entry and no exact source-ID or complete source-text occurrence exists in pinned production code. Keep all locales held. The Japanese and Korean current targets render the source words “three hours” as the semantically equivalent digit 3; with no live caller, do not select a change.",
    477: "No active source-registry entry and no exact source-ID or complete source-text occurrence exists in pinned production code. The nearby status template contains similar explanatory text as raw HTML split across lines, without this catalog key, so it does not establish a catalog-backed caller; keep the entry held.",
}

POSITION_CONTEXT = {
    465: "Exact ID-bound help text above the indexer results table; it summarizes found releases, matches, and rejected-result reasons.",
    466: "Discover facet label used for the by-franchise tab and empty-result copy; neighboring facets are Genre and Company.",
    467: "Friday abbreviation in the compact weekday header for the calendar.",
    468: "Hub navigation label and the heading of the page for sharing a library with peers.",
    469: "AllDebrid API-key help text describing accepted magnet and infohash inputs.",
    470: "No active registry entry or exact production caller was found for this debrid-link help string.",
    471: "No active registry entry or exact production caller was found for this Offcloud account help string.",
    472: "Premiumize API-key help text describing accepted magnet and .torrent URL inputs.",
    473: "No active registry entry or exact production caller was found for this Real-Debrid help string.",
    474: "No active registry entry or exact production caller was found for this TorBox expiry/link help string.",
    475: "Status-table row label for the configured GG Requestz front-end page; caller states that it checks reachability only.",
    476: "Heading for the GG Requestz incoming-request webhook setup; the caller comment says the service pushes requests to ROMarr.",
    477: "No exact catalog ID or complete source-text caller was found; similar raw template text is not bound to this catalog entry.",
    478: "List-source option for a public GOG profile; caller says no credential is needed.",
    479: "Text-input label for the public GOG profile name.",
    480: "Generic Game label; the exact text occurs broadly in production code, where it denotes a game as an entity.",
    481: "Table header pairing the game with evidence in the ROM-validation results.",
    482: "Moonlight setup status heading for the host that streams a desktop emulator.",
    483: "Sniffed disc-format result describing the GameCube signature at byte offset 0x1c.",
    484: "Generic Games collection/page label; the exact text occurs in several game-list and library contexts.",
}
EXTRA_LITERALS = {475: ["GG Requestz"], 476: ["GG Requestz"], 479: ["GOG"], 483: ["GameCube"]}

def sha(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

def protected_terms(text):
    return sorted([term for term in PROTECTED if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text)], key=lambda term: text.find(term))

def compact_ref(ref):
    keys = ("path", "lineStart", "lineEnd", "role", "anchor", "contextSha256", "fileSha256", "gitBlob")
    return {key: ref[key] for key in keys if key in ref}

def capture_pr():
    view = json.loads(subprocess.check_output([
        "gh", "pr", "view", "70", "--repo", REPO, "--json",
        "state,isDraft,headRefName,headRefOid,baseRefName,baseRefOid,url"
    ], text=True))
    remote = f"https://github.com/{REPO}.git"
    branch_ref = subprocess.check_output(["git", "ls-remote", remote, f"refs/heads/{BRANCH}"], text=True).split()[0]
    pull_ref = subprocess.check_output(["git", "ls-remote", remote, "refs/pull/70/head"], text=True).split()[0]
    tree = subprocess.check_output([
        "gh", "api", f"repos/{REPO}/git/commits/{view['headRefOid']}", "--jq", ".tree.sha"
    ], text=True).strip()
    result = {
        "observedUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository": REPO,
        "pullRequest": 70,
        "url": view["url"],
        "state": view["state"],
        "isDraft": view["isDraft"],
        "branch": view["headRefName"],
        "baseBranch": view["baseRefName"],
        "baseHead": view["baseRefOid"],
        "head": view["headRefOid"],
        "tree": tree,
        "liveBranchRef": branch_ref,
        "livePullRef": pull_ref,
        "matchesPinnedHeadTree": view["headRefOid"] == HEAD and tree == TREE,
        "matchesBothRemoteRefs": branch_ref == HEAD and pull_ref == HEAD,
    }
    if not (result["state"] == "OPEN" and result["isDraft"] is True and result["branch"] == BRANCH and result["matchesPinnedHeadTree"] and result["matchesBothRemoteRefs"]):
        raise SystemExit("live PR/branch/pull refs drifted from the pinned OPEN/DRAFT head/tree")
    return result

def main():
    existing = {path.name for path in OUT.iterdir()} if OUT.exists() else set()
    if existing - {"build_primary.py"}:
        raise SystemExit(f"refusing to overwrite nonempty primary packet: {OUT}")
    if not OUT.exists():
        OUT.mkdir(parents=True)
    input_verify = subprocess.run(["python3", str(IN / "verify_input.py")], cwd=IN, capture_output=True, text=True)
    if input_verify.returncode:
        raise SystemExit("candidate-free input verifier failed:\n" + input_verify.stdout + input_verify.stderr)
    manifest_input = read_json(IN / "manifest.json")
    sources = {row["position"]: row for row in read_jsonl(IN / "source-inventory-selection.jsonl")}
    contexts = {row["position"]: row for row in read_jsonl(IN / "source-contexts.jsonl")}
    cells = read_jsonl(IN / "current-target-cells.jsonl")
    if manifest_input["head"] != HEAD or manifest_input["tree"] != TREE or manifest_input["window"] != "W465-W484":
        raise SystemExit("candidate-free input pin mismatch")
    if manifest_input["proposedTargetsIncluded"] or manifest_input["reviewDecisionsIncluded"]:
        raise SystemExit("candidate-free boundary violated")
    if len(cells) != 240 or len(sources) != 20 or len(contexts) != 20:
        raise SystemExit("candidate-free input coverage mismatch")
    if not all(row["sourceMatchesCurrentCatalog"] and row["selectionPositionMatches"] and row["targetUnchanged"] for row in read_jsonl(IN / "prior-hold-reattestation.jsonl")):
        raise SystemExit("carried hold reattestation failed")

    before = capture_pr()
    ledger = []
    for cell in cells:
        pos, locale = cell["position"], cell["locale"]
        if locale not in LOCALES:
            raise SystemExit(f"unexpected locale {locale}")
        source = sources[pos]
        context = contexts[pos]
        if cell["sourceId"] != source["sourceId"] or cell["sourceSha256"] != source["sourceSha256"]:
            raise SystemExit(f"source mismatch {pos}/{locale}")
        source_tokens = TOKEN_RE.findall(cell["source"])
        current_tokens = TOKEN_RE.findall(cell["currentTarget"])
        source_numbers = NUMBER_RE.findall(cell["source"])
        current_numbers = NUMBER_RE.findall(cell["currentTarget"])
        source_literals = protected_terms(cell["source"])
        current_literals = [term for term in source_literals if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", cell["currentTarget"])]
        if source_tokens != cell["sourcePlaceholderTokens"] or current_tokens != cell["currentPlaceholderTokens"] or sorted(source_tokens) != sorted(current_tokens):
            raise SystemExit(f"baseline placeholder mismatch {pos}/{locale}")
        if source_numbers != cell["sourceNumericTokens"] or current_numbers != cell["currentNumericTokens"]:
            raise SystemExit(f"baseline numeric inventory mismatch {pos}/{locale}")
        if source_literals != cell["sourceProtectedLiterals"] or current_literals != cell["currentProtectedLiterals"]:
            raise SystemExit(f"baseline literal inventory mismatch {pos}/{locale}")

        decision = PROPOSALS.get((pos, locale))
        if pos in HOLD_POSITIONS:
            disposition, proposal = "hold", None
            rationale = HOLD_POSITIONS[pos]
        elif decision:
            disposition, proposal, rationale = decision
        else:
            disposition, proposal = "accept-current", None
            rationale = f"The current wording conveys the source in the exact pinned caller context ({POSITION_CONTEXT[pos]}). The candidate-free source and caller hashes match; placeholders, numeric tokens, and protected literals are preserved."

        selected = cell["currentTarget"] if disposition == "accept-current" else (proposal if disposition in ("correction", "refinement") else None)
        selected_tokens = TOKEN_RE.findall(selected) if selected is not None else None
        selected_numbers = NUMBER_RE.findall(selected) if selected is not None else None
        selected_literals = protected_terms(selected) if selected is not None else None
        placeholder_ok = selected_tokens is not None and sorted(source_tokens) == sorted(selected_tokens)
        numeric_ok = selected_numbers is not None and source_numbers == selected_numbers
        literal_ok = selected_literals is not None and all(term in selected_literals for term in source_literals)
        if selected is not None and not placeholder_ok:
            raise SystemExit(f"selected placeholder check failed {pos}/{locale}")
        if selected is not None and not numeric_ok:
            raise SystemExit(f"selected numeric check failed {pos}/{locale}")
        if selected is not None and not literal_ok:
            raise SystemExit(f"selected protected-literal check failed {pos}/{locale}")

        extra_terms = EXTRA_LITERALS.get(pos, [])
        current_extra_ok = all(re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", cell["currentTarget"]) for term in extra_terms)
        selected_extra_ok = selected is not None and all(re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", selected) for term in extra_terms)
        if selected is not None and not selected_extra_ok:
            raise SystemExit(f"named product literal check failed {pos}/{locale}")

        refs = [compact_ref(ref) for ref in context["callerContextRefs"]]
        if pos not in HOLD_POSITIONS and not refs:
            raise SystemExit(f"missing exact caller context {pos}/{locale}")
        token_checks = {
            "sourcePlaceholderTokens": source_tokens,
            "currentPlaceholderTokens": current_tokens,
            "selectedPlaceholderTokens": selected_tokens,
            "selectedPlaceholderMultisetMatches": bool(placeholder_ok),
            "sourceNumericTokens": source_numbers,
            "currentNumericTokens": current_numbers,
            "selectedNumericTokens": selected_numbers,
            "selectedNumericTokensExactMatch": bool(numeric_ok),
            "semanticNumericReview": None,
            "sourceProtectedLiterals": source_literals,
            "currentProtectedLiterals": current_literals,
            "selectedProtectedLiterals": selected_literals,
            "selectedProtectedLiteralsPreserved": bool(literal_ok),
            "additionalNamedTerms": extra_terms,
            "currentAdditionalNamedTermsPreserved": bool(current_extra_ok),
            "selectedAdditionalNamedTermsPreserved": bool(selected_extra_ok),
        }
        ledger.append({
            "position": pos,
            "catalogZeroBasedIndex": cell["catalogZeroBasedIndex"],
            "catalogOneBasedPosition": cell["catalogOneBasedPosition"],
            "sourceId": cell["sourceId"],
            "locale": locale,
            "source": cell["source"],
            "sourceSha256": cell["sourceSha256"],
            "currentTarget": cell["currentTarget"],
            "currentTargetSha256": cell["currentTargetSha256"],
            "catalogTranslationHash": cell["catalogTranslationHash"],
            "inputCallerContextSha256": cell["callerContextSha256"],
            "selectedCallerContextRefs": refs,
            "activeSourceRegistry": source["activeSourceRegistry"],
            "activeSourceRank": source["activeSourceRank"],
            "reviewedContext": POSITION_CONTEXT[pos],
            "disposition": disposition,
            "proposedTarget": proposal,
            "proposedTargetSha256": sha(proposal) if proposal is not None else None,
            "selectedTarget": selected,
            "selectedTargetSha256": sha(selected) if selected is not None else None,
            "rationale": rationale,
            "tokenAndLiteralChecks": token_checks,
        })

    expected = [(pos, locale) for pos in range(465, 485) for locale in LOCALES]
    if [(row["position"], row["locale"]) for row in ledger] != expected:
        raise SystemExit("ledger coverage/order mismatch")
    (OUT / "PR-attestation-before.json").write_text(json.dumps(before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "primary-ledger.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in ledger), encoding="utf-8")

    counts = collections.Counter(row["disposition"] for row in ledger)
    hold_positions = sorted(HOLD_POSITIONS)
    proposals = [row for row in ledger if row["proposedTarget"] is not None]
    selected_rows = [row for row in ledger if row["selectedTarget"] is not None]
    selected_placeholder_mismatches = sum(not row["tokenAndLiteralChecks"]["selectedPlaceholderMultisetMatches"] for row in selected_rows)
    selected_numeric_mismatches = sum(not row["tokenAndLiteralChecks"]["selectedNumericTokensExactMatch"] for row in selected_rows)
    selected_literal_mismatches = sum(not row["tokenAndLiteralChecks"]["selectedProtectedLiteralsPreserved"] for row in selected_rows)
    if selected_placeholder_mismatches or selected_numeric_mismatches or selected_literal_mismatches:
        raise SystemExit("selected token/literal audit has a mismatch")
    contexts_available = sum(bool(row["callerContextRefs"]) for row in contexts.values())
    held_cells = [row for row in ledger if row["disposition"] == "hold"]
    previous_holds = read_jsonl(IN / "prior-hold-reattestation.jsonl")
    prior_selections = read_jsonl(IN / "prior-selection-reattestation.jsonl")
    after = capture_pr()
    if before["head"] != after["head"] or before["tree"] != after["tree"]:
        raise SystemExit("PR moved during primary review")
    (OUT / "PR-attestation-after.json").write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "artifact": "ROMarrNG PR #70 W465-W484 primary review",
        "reviewerRole": "independent primary reviewer; candidate-free input only",
        "repository": REPO,
        "pullRequest": 70,
        "branch": BRANCH,
        "head": HEAD,
        "tree": TREE,
        "candidateFreeInputPath": str(IN),
        "candidateFreeInputManifestSha256": sha((IN / "manifest.json").read_bytes()),
        "candidateFreeInputChecksumsSha256": sha((IN / "SHA256SUMS.txt").read_bytes()),
        "candidateFreeInputVerified": True,
        "primaryProposalsReadBeforeReview": False,
        "blindReviewOutputInspected": False,
        "sourceCount": 20,
        "localeCount": 12,
        "cellCount": len(ledger),
        "dispositions": dict(sorted(counts.items())),
        "proposedCellCount": len(proposals),
        "newHolds": len(held_cells),
        "holdPositions": hold_positions,
        "holdFindings": {str(pos): HOLD_POSITIONS[pos] for pos in hold_positions},
        "priorLineageSelectionsReattested": len(prior_selections),
        "priorHoldCellsReattested": len(previous_holds),
        "sourceContextAvailable": contexts_available,
        "callerlessCellCount": len(held_cells),
        "callerlessHoldFinding": "All 12 cells at each of positions 470, 471, 473, 474, and 477 remain held because no exact catalog-backed production caller is established. The Japanese and Korean rank-474 current values render “three” as the equivalent digit 3, but remain unselected under that callerless hold.",
        "currentProtectedLiteralMismatches": manifest_input["currentTargetProtectedLiteralMismatches"],
        "currentTargetNumericMismatches": manifest_input["currentTargetNumericMismatches"],
        "numericMismatchCellsHeld": [
            {"position": row["position"], "locale": row["locale"], "sourceNumbers": row["sourceNumericTokens"], "currentNumbers": row["currentNumericTokens"], "holdReason": HOLD_POSITIONS[row["position"]]}
            for row in cells if row["sourceNumericTokens"] != row["currentNumericTokens"]
        ],
        "placeholderMismatchesInSelectedTargets": selected_placeholder_mismatches,
        "numericExactMismatchesAfterSemanticReview": selected_numeric_mismatches,
        "protectedLiteralMismatchesInSelectedTargets": selected_literal_mismatches,
        "nativeSpeakerReview": "not performed; this primary machine review does not establish native-speaker approval",
        "browserReview": "not performed",
        "createdUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    readme = f"""# ROMarrNG PR #70 W445-W464 primary review

Independent primary semantic review for PR head {HEAD}, tree {TREE}, branch {BRANCH}. The ledger covers 20 catalog messages × 12 locales (240 cells). It was built from the sealed candidate-free input at {IN}; no blind or cross-review material was inspected.

Disposition counts: {dict(sorted(counts.items()))}. The packet contains {len(proposals)} proposed corrections/refinements and {len(held_cells)} holds at positions {hold_positions}. Prior source-selection lineage ({len(prior_selections)} rows) and all {len(previous_holds)} carried hold cells were reattested against this exact head.

Every selected target preserves the source placeholders, numeric tokens, and protected literals. Callerless entries remain held as described in summary.json. Browser review and native-speaker review were not performed.

Verify with python3 verify_primary.py from this directory.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({
        "head": HEAD,
        "tree": TREE,
        "window": "W465-W484",
        "cells": len(ledger),
        "dispositions": dict(sorted(counts.items())),
        "proposals": len(proposals),
        "newHolds": len(held_cells),
        "priorSelections": len(prior_selections),
        "priorHolds": len(previous_holds),
        "selectedPlaceholderMismatches": selected_placeholder_mismatches,
        "selectedNumericMismatches": selected_numeric_mismatches,
        "selectedProtectedLiteralMismatches": selected_literal_mismatches,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()

