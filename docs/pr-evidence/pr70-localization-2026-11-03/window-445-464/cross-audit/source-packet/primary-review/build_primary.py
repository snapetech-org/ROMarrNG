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
IN = Path("/home/keith/Documents/code/task-scratch/romarrng-pr70-w445-464-candidate-free-20261103/input")
HEAD = "d5ba7f1f268501f45227388c46d5f938ed0c9191"
TREE = "2f8ce1af963b315108f668fc31c94ca90ecd1351"
BRANCH = "task/localization-translation-review-20261030"
REPO = "snapetech-org/ROMarrNG"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
TOKEN_RE = re.compile(r"\{[A-Za-z][A-Za-z0-9_]*\}")
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?:%?)(?![A-Za-z0-9_])")
PROTECTED = ["ROMarr", "GG Requestz", "RomM", "ROMm", "ES-DE", "gamelist.xml", "1G1R", "Battle.net", "No-Intro", "Redump", "RetroArch", "Steam", "EA", "Epic", "ROM", "Hub", "DAT"]

PROPOSALS = {
    (447, "zh-Hans"): ("refinement", "补缺 — 仅在没有首选地区版本时使用民间翻译版", "The option is specifically for fan translations in 1G1R sets. “译制版” can suggest a dubbed or professionally produced edition; “民间翻译版” clearly identifies a fan-made translation."),
    (447, "zh-Hant"): ("refinement", "填補缺漏 — 僅在沒有偏好地區版本時使用民間翻譯版", "The option is specifically for fan translations in 1G1R sets. “翻譯版” is understandable, while “民間翻譯版” makes the fan-made nature explicit."),
    (448, "id"): ("correction", "Saring permainan", "The exact caller is the accessible label for the games search field. The current target leaves “Filter game” in English; “Saring permainan” gives the action in Indonesian."),
    (451, "ar"): ("correction", "أصلح المشكلات التالية:", "This heading introduces a list of submission validation problems. Naming the following problems is clearer than the current demonstrative alone."),
    (451, "es"): ("refinement", "Corrige los siguientes problemas:", "The caller introduces a list of submission validation problems. The current wording is understandable; naming the problems makes the heading clearer."),
    (451, "fr"): ("correction", "Problèmes à corriger :", "The caller introduces multiple validation problems. The current “ceci” is singular; this heading matches the following list."),
    (451, "pt-BR"): ("correction", "Corrija os seguintes problemas:", "The caller introduces multiple submission validation problems. The current “isso” is singular; this heading matches the following list."),
    (451, "vi"): ("refinement", "Hãy sửa các mục sau:", "The caller introduces a list of validation problems. “Các mục sau” is more precise for the following list than the current vague “những thứ này.”"),
    (451, "zh-Hans"): ("refinement", "请修复以下问题：", "The caller introduces a list of submission validation problems. Naming the following problems makes the heading explicit."),
    (451, "zh-Hant"): ("refinement", "請修復以下問題：", "The caller introduces a list of submission validation problems. Naming the following problems makes the heading explicit."),
    (452, "ar"): ("correction", "Flashpoint (البث عبر الإنترنت)", "This is a source label for streamed Flashpoint content, not a live broadcast. “البث عبر الإنترنت” avoids the live-broadcast implication of the current wording."),
    (453, "pt-BR"): ("correction", "O Flood usa tags em vez de categorias; este campo recebe uma tag.", "The exact caller is helper text under a downloader field labelled “Tag.” “Este é um tag” has a gender mismatch and is less clear than saying the field accepts a tag."),
    (457, "ar"): ("refinement", "متابعة السجل", "The exact caller is a checkbox in the live log viewer that keeps the output scrolled to new entries. This noun phrase is clearer as a control label than the generic imperative."),
    (457, "hi"): ("correction", "नए लॉग तक स्वतः स्क्रॉल करें", "The checkbox controls automatic scrolling to newly appended log lines. The current phrase means “obey/follow” and does not name that behavior."),
    (457, "ja"): ("refinement", "自動スクロール", "The checkbox controls whether the live log output scrolls to the latest entries. This names the visible behavior more clearly than the borrowed social-media term."),
    (457, "ko"): ("refinement", "자동 스크롤", "The checkbox controls whether the live log output scrolls to the latest entries. This names the visible behavior more clearly than the borrowed social-media term."),
    (457, "pt-BR"): ("refinement", "Acompanhar", "The checkbox is a log-viewer control. “Acompanhar” is the natural Portuguese label for following the live output; the current imperative sounds like a direct instruction."),
    (457, "vi"): ("correction", "Theo dõi", "The exact caller is a log-viewer checkbox. “Theo” alone is incomplete here; “Theo dõi” is the standard Vietnamese verb for following or monitoring."),
    (457, "zh-Hans"): ("refinement", "自动滚动", "The checkbox controls automatic scrolling to newly appended log lines. This describes the control more clearly than the generic “跟随.”"),
    (457, "zh-Hant"): ("refinement", "自動捲動", "The checkbox controls automatic scrolling to newly appended log lines. This describes the control more clearly than the generic “跟隨.”"),
    (461, "pt-BR"): ("correction", "Em uma estrutura como a do EmuDeck, defina a raiz da biblioteca de arquivos ROM como a pasta compartilhada", "The exact caller continues with the shared Emulation/roms path. The current “ROMs” fails the protected literal check for the exact acronym ROM; this wording preserves EmuDeck and the exact ROM casing while staying natural."),
}

HOLD_POSITIONS = {
    458: "No active source-registry entry and no exact source-ID or source-text occurrence exists in pinned production code. The fragment ends at “with,” so its rendered continuation cannot be established.",
    460: "No active source-registry entry and no exact source-ID or source-text occurrence exists in pinned production code. The fragment ends at “use,” so its rendered continuation cannot be established.",
    462: "The entry is present in the active source registry, but neither its exact source ID nor source text occurs in pinned production code. The registry entry alone does not establish a live caller or whether this row is stale, so the count message remains held.",
}

POSITION_CONTEXT = {
    445: "Organizer match-status label for a title inferred from its filename; the status asks the user to review before renaming.",
    446: "Organizer match-detail status shown when the filename is the only evidence and no catalog match has been verified.",
    447: "Fan-translation policy option for 1G1R collections; fill a gap only if no preferred-region dump exists.",
    448: "Accessible label for the games search field.",
    449: "Placeholder in the games search field.",
    450: "Prefix before the first game title in the request/import result summary.",
    451: "Heading immediately before submission validation problems.",
    452: "Downloader/source label distinguishing Flashpoint content available by streaming.",
    453: "Helper text under the Flood downloader's Tag field.",
    454: "Label for a platform folder-name input in library settings.",
    455: "Organizer safety explanation when a source is a directory; the directory is not renamed.",
    456: "Library setting matching RomM's Structure A or B folder layout.",
    457: "Log-viewer checkbox; when enabled, appended log lines keep the view scrolled to the bottom.",
    458: "No exact source/caller context found in the pinned production code.",
    459: "Catalog-page help sentence linking to SeerrNG for a household catalog and request queue.",
    460: "No exact source/caller context found in the pinned production code.",
    461: "Setup-device instruction for an EmuDeck-style layout; followed by the shared Emulation/roms path.",
    462: "Active registry entry but no exact source-ID or source-text caller found in pinned production code.",
    463: "Request/import result summary showing the number of found titles.",
    464: "Request/import result summary showing found titles and the subset whose platform is unresolved.",
}

EXTRA_LITERALS = {452: ["Flashpoint"], 453: ["Flood"], 458: ["ROMarrNG"], 461: ["EmuDeck"]}

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
    if manifest_input["head"] != HEAD or manifest_input["tree"] != TREE or manifest_input["window"] != "W445-W464":
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
        current_literals = protected_terms(cell["currentTarget"])
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

    expected = [(pos, locale) for pos in range(445, 465) for locale in LOCALES]
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
        "artifact": "ROMarrNG PR #70 W445-W464 primary review",
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
        "callerlessHoldFinding": "All 12 cells at each of positions 458 and 460 remain held because neither source has an active source-registry entry or an exact production caller. All 12 cells at position 462 remain held because the entry is active in the registry but neither its source ID nor text has an exact production-code occurrence.",
        "currentProtectedLiteralMismatches": manifest_input["currentTargetProtectedLiteralMismatches"],
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
        "window": "W445-W464",
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

