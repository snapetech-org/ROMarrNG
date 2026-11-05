#!/usr/bin/env python3
"""Create the fresh W645-W664 primary semantic review from sealed input only."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HEAD = "9f8832f67195323955172dd4c3c40e29cbabb5da"
TREE = "d6066baa3d03d3b4c6034e5af061fc4bc278b0f9"
WINDOW = "W645-W664"
LOCALES = ["ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt-BR", "vi", "zh-Hans", "zh-Hant"]
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
TAG = re.compile(r"<[^>]+>")
NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
PROTECTED = ["Gaseous", "Retrom", "SeerrNG", "ROMarrNG", "ROMarr", "ES-DE", "No-Intro", "Redump", "DAT", "IGDB", "ISO9660", "PLAYSTATION", "PlayStation", "PS2", "ROMs", "ROM", "PC", "API", "ROMARR_API_KEY", "Linksnappy", "Moonlight", "PIN", "NPSSO", "NZBHydra2", "Newznab", "/torznab/api", "NZBVortex", "HTTPS", "NZB", "Preferences"]

CHANGES = {
    ("ui.moonlight-host.52839edd11", "hi"): {
        "target": "Moonlight होस्ट",
        "changeType": "correction",
        "rationale": "The caller identifies a configured host machine. मेजबान suggests a person hosting something; the common technical loanword होस्ट fits this network host label.",
    },
    ("ui.missing.6be36ca49e", "id"): {
        "target": "Tidak ditemukan",
        "changeType": "correction",
        "rationale": "The pinned callers use this for titles absent from the available game set. Tidak ada means none/there is no, which mislabels a nonzero missing count; Tidak ditemukan means not found.",
    },
    ("ui.missing.6be36ca49e", "ja"): {
        "target": "未所持",
        "changeType": "correction",
        "rationale": "The Wanted navigation entry and missing-title count identify games not present in the local collection. 不足 means insufficiency or shortage; 未所持 clearly labels titles not owned/available in the collection.",
    },
    ("ui.multi-disc-set-is-grouped-for-metada.86db33ad47", "ar"): {
        "target": "تُجمَّع المجموعة متعددة الأقراص لأغراض البيانات الوصفية، وتبقى ملفات الأقراص الخاصة بها معًا",
        "changeType": "correction",
        "rationale": "The organizer reason says a multi-disc title is grouped while its disc files stay together. The current metadata phrase الميتا البيانات is unnatural; البيانات الوصفية is the standard term.",
    },
    ("ui.multi-disc-set-is-grouped-for-metada.86db33ad47", "es"): {
        "target": "El conjunto multidisco se agrupa para gestionar los metadatos; sus archivos de disco permanecen juntos",
        "changeType": "refinement",
        "rationale": "The exact caller describes one multi-disc title set. Multidisco is the natural Spanish compound, and para gestionar los metadatos expresses why the set is grouped.",
    },
    ("ui.multi-disc-set-is-grouped-for-metada.86db33ad47", "de"): {
        "target": "Ein Multi-Disc-Set wird für Metadaten gruppiert; seine Disc-Dateien bleiben zusammen",
        "changeType": "correction",
        "rationale": "The current sentence omits the German article before the subject and uses Diskdateien for game-disc files. Ein Multi-Disc-Set and Disc-Dateien make the sentence grammatical and preserve the game-media meaning.",
    },
    ("ui.multi-disc-set-is-grouped-for-metada.86db33ad47", "hi"): {
        "target": "मल्टी-डिस्क सेट को मेटाडेटा के लिए एक समूह में रखा जाता है; उसकी डिस्क फ़ाइलें साथ रहती हैं",
        "changeType": "correction",
        "rationale": "The current phrase समूह किया जाता है is ungrammatical here. The replacement clearly says the set is kept as a group for metadata and its disc files remain together.",
    },
    ("ui.multi-disc-set-is-grouped-for-metada.86db33ad47", "id"): {
        "target": "Set multi-disk dikelompokkan untuk keperluan metadata; berkas-berkas disknya tetap bersama",
        "changeType": "correction",
        "rationale": "The source says the set is grouped. The current dikumpulkan means collected; dikelompokkan states the grouping relationship, and keperluan metadata reads naturally as the purpose.",
    },
    ("ui.multi-disc-set-is-grouped-for-metada.86db33ad47", "ko"): {
        "target": "다중 디스크 세트는 메타데이터를 위해 그룹화되며 디스크 파일은 함께 유지됩니다",
        "changeType": "refinement",
        "rationale": "The meaning is already present, but standard Korean spells 메타데이터 as one compound word rather than 메타 데이터.",
    },
    ("ui.multi-disc-set-is-grouped-for-metada.86db33ad47", "pt-BR"): {
        "target": "O conjunto de vários discos é agrupado para fins de metadados; os arquivos de disco permanecem juntos",
        "changeType": "refinement",
        "rationale": "The source describes why the set is grouped. Para fins de metadados expresses that purpose more naturally than para os metadados.",
    },
    ("ui.my-library.fbc3b89e6a", "pt-BR"): {
        "target": "Minha biblioteca",
        "changeType": "correction",
        "rationale": "This is a compact mode button label. The current trailing full stop is unnecessary UI punctuation.",
    },
    ("ui.my-library.fbc3b89e6a", "ar"): {
        "target": "مكتبتي",
        "changeType": "correction",
        "rationale": "In Arabic, مكتبي means my office/desk; the feminine noun for library takes the suffix as مكتبتي. This is the exact My library tab for the user's game collection.",
    },
}


def sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


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
    numeric_presentation = bool(re.search(r"\bzero\b", source, re.I) and not source_tokens["numbers"] and extra == ["0"])
    numeric_ok = not (source_numbers - target_numbers) and (not extra or numeric_presentation)
    missing_protected = [literal for literal in source_tokens["protectedLiterals"] if literal not in target]
    return {"sourcePlaceholderTokens":source_tokens["placeholders"], "targetPlaceholderTokens":target_tokens["placeholders"], "placeholdersPreserved":collections.Counter(source_tokens["placeholders"]) == collections.Counter(target_tokens["placeholders"]), "sourceMarkupTags":source_tokens["markup"], "targetMarkupTags":target_tokens["markup"], "markupPreserved":collections.Counter(source_tokens["markup"]) == collections.Counter(target_tokens["markup"]), "sourceNumericTokens":source_tokens["numbers"], "targetNumericTokens":target_tokens["numbers"], "numericTokensPreserved":numeric_ok, "numericPresentationEquivalent":numeric_presentation, "sourceProtectedLiterals":source_tokens["protectedLiterals"], "missingProtectedLiterals":missing_protected, "protectedLiteralsPreserved":not missing_protected}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    root = Path(__file__).resolve().parent
    candidate_bundle = root / "candidate-free-bundle"
    candidate_verify = candidate_bundle / "verify_bundle.py"
    verified = subprocess.check_output([sys.executable, str(candidate_verify), "--repo", str(repo)], text=True)
    candidate_result = json.loads(verified)
    if candidate_result.get("result") != "PASS":
        raise SystemExit("FAIL candidate-free input verification")
    input_dir = candidate_bundle / "candidate-free" / "input"
    input_manifest_raw = (input_dir / "manifest.json").read_bytes()
    input_manifest = json.loads(input_manifest_raw)
    cells = [json.loads(line) for line in (input_dir / "current-target-cells.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    contexts = [json.loads(line) for line in (input_dir / "source-contexts.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    context_by_id = {row["sourceId"]:row for row in contexts}
    if input_manifest.get("head") != HEAD or input_manifest.get("tree") != TREE or len(cells) != 240:
        raise SystemExit("FAIL candidate-free input identity/count")

    dispositions = []
    hash_holds = []
    counts = collections.Counter()
    changes_by_locale = collections.Counter()
    changes_by_position = collections.Counter()
    changes_by_type = collections.Counter()
    for cell in cells:
        source_id, locale = cell["sourceId"], cell["locale"]
        context = context_by_id[source_id]
        if cell["callerContextSha256"] != context["contextSha256"]:
            raise SystemExit(f"FAIL source/context binding: {source_id}/{locale}")
        if context["callerless"]:
            hold = {"window":WINDOW, "position":cell["position"], "catalogZeroBasedIndex":cell["catalogZeroBasedIndex"], "sourceId":source_id, "sourceSha256":cell["sourceSha256"], "locale":locale, "currentTargetSha256":cell["currentTargetSha256"], "callerContextSha256":context["contextSha256"], "callerCount":0, "disposition":"hold-callerless-hash-only", "sourceTextOmitted":True, "targetTextOmitted":True, "holdReasonSha256":sha("no exact production caller context; preserve current value pending caller evidence"), "candidateFreeInputManifestSha256":sha(input_manifest_raw)}
            if any(key in hold for key in ("source", "sourceText", "currentTarget", "target", "targetText", "proposedTarget", "selectedTarget", "finalTarget")):
                raise SystemExit("FAIL callerless hold contains text")
            hash_holds.append(hold)
            counts["HOLD"] += 1
            continue

        key = (source_id, locale)
        proposal = CHANGES.get(key)
        target = proposal["target"] if proposal else cell["currentTarget"]
        token_checks = token_report(cell["source"], target)
        if not all(token_checks[name] for name in ("placeholdersPreserved", "markupPreserved", "numericTokensPreserved", "protectedLiteralsPreserved")):
            raise SystemExit(f"FAIL proposed/current target token integrity: {source_id}/{locale}")
        decision = {"window":WINDOW, "position":cell["position"], "catalogZeroBasedIndex":cell["catalogZeroBasedIndex"], "sourceId":source_id, "source":cell["source"], "sourceSha256":cell["sourceSha256"], "locale":locale, "currentTarget":cell["currentTarget"], "currentTargetSha256":cell["currentTargetSha256"], "callerContextSha256":context["contextSha256"], "callerCount":context["exactMatchCount"], "callerRefHashesSha256":sha(canonical(cell["callerRefs"])), "disposition":"CHANGE" if proposal else "KEEP", "currentTargetTokenChecks":token_report(cell["source"], cell["currentTarget"]), "reviewedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if proposal:
            decision.update({"changeType":proposal["changeType"], "proposedTarget":target, "proposedTargetSha256":sha(target), "proposedTargetTokenChecks":token_checks, "rationale":proposal["rationale"]})
            counts["CHANGE"] += 1
            changes_by_locale[locale] += 1
            changes_by_position[str(cell["position"])] += 1
            changes_by_type[proposal["changeType"]] += 1
        else:
            decision["rationale"] = "Retain: the current wording preserves the source meaning in the exact pinned production caller context."
            if source_id == "ui.more-player-options.20bb9a4a10":
                decision["rationale"] = "Retain: the nearby play-device setup copy and the pinned #ecosystem link show that this names additional ways to play through clients or player software."
            if source_id == "ui.missing.6be36ca49e":
                decision["rationale"] = "Retain: in the Wanted entry and missing-title count, this locale's current label identifies titles absent from the available collection."
            if source_id == "ui.mon.f40d7f51f6":
                decision["rationale"] = "Retain: the caller uses this as a compact weekday heading; the locale value is a standard short weekday label or its single-character equivalent."
            counts["KEEP"] += 1
        dispositions.append(decision)

    if (len(dispositions), len(hash_holds), len(dispositions) + len(hash_holds), counts["CHANGE"], counts["KEEP"], counts["HOLD"]) != (144, 96, 240, len(CHANGES), 144 - len(CHANGES), 96):
        raise SystemExit("FAIL primary decision/hold coverage")
    if set(CHANGES) != {(row["sourceId"], row["locale"]) for row in dispositions if row["disposition"] == "CHANGE"}:
        raise SystemExit("FAIL primary change map coverage")

    output = root / "primary-output"
    if output.exists() and any(output.iterdir()):
        raise SystemExit("FAIL primary output already exists")
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "dispositions.jsonl", dispositions)
    write_jsonl(output / "hash-only-holds.jsonl", hash_holds)
    summary = {"artifact":"ROMarrNG PR #70 W645-W664 primary semantic review summary", "head":HEAD, "tree":TREE, "window":WINDOW, "sourceCount":20, "localeCount":12, "cellCount":240, "dispositionCounts":{"CHANGE":counts["CHANGE"], "KEEP":counts["KEEP"], "HOLD":counts["HOLD"]}, "proposedChangeCount":counts["CHANGE"], "proposedChangeCountsByLocale":dict(sorted(changes_by_locale.items())), "proposedChangeCountsByPosition":dict(sorted(changes_by_position.items(), key=lambda row:int(row[0]))), "changeTypes":dict(sorted(changes_by_type.items())), "hashOnlyHoldCount":len(hash_holds), "hashOnlyHoldFile":"hash-only-holds.jsonl", "callerCoverage":{"sourcesWithCallers":sum(not row["callerless"] for row in contexts), "callerlessSources":sum(row["callerless"] for row in contexts), "callerlessCells":len(hash_holds), "proposedChangesWithCallerContext":sum(row["disposition"] == "CHANGE" and row["callerCount"] > 0 for row in dispositions), "proposedChangesWithoutCallerContext":0}, "blindness":{"blindOutputInspected":False, "crossReviewOutputInspected":False, "otherW645ReviewDecisionsAccessed":False, "priorW645PrimaryDecisionsReused":False, "candidateFreeInputManifestSha256":sha(input_manifest_raw)}, "catalogSha256":input_manifest["catalogSha256"], "catalogKeyOrderSha256":input_manifest["catalogKeyOrderSha256"], "sourceQueueSha256":input_manifest["sourceQueueSha256"], "sourceSnapshotSha256":input_manifest["sourceSnapshotSha256"], "reviewedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"), "limitations":["AI semantic review; no native-speaker approval.", "96 callerless cells are retained as hash-only holds with source and target text omitted.", "Independent blind review and cross-adjudication remain pending."]}
    write_json(output / "summary.json", summary)
    output_files = []
    for path in sorted(p for p in output.iterdir() if p.is_file()):
        output_files.append({"path":path.name, "sha256":sha(path.read_bytes()), "bytes":path.stat().st_size})
    write_json(output / "primary-manifest.json", {"artifact":"W645-W664 primary semantic review output", "head":HEAD, "tree":TREE, "window":WINDOW, "cellCount":240, "sourceCount":20, "localeCount":12, "dispositionCounts":summary["dispositionCounts"], "proposedChangeCount":counts["CHANGE"], "hashOnlyHoldCount":len(hash_holds), "candidateFreeInputManifestSha256":sha(input_manifest_raw), "files":output_files})
    primary_manifest_hash = sha((input_dir / "manifest.json").read_bytes())
    write_json(root / "PRIMARY-REVIEW-MANIFEST.json", {"artifact":"ROMarrNG PR #70 W645-W664 primary review packet", "head":HEAD, "tree":TREE, "window":WINDOW, "candidateFreeInputManifestSha256":primary_manifest_hash, "candidateFreeVerifier":"PASS", "candidateFreeBundle":"candidate-free-bundle", "primaryDecisionCount":len(dispositions), "callerlessHashOnlyHoldCount":len(hash_holds), "proposedChangeCount":counts["CHANGE"], "blindReviewUsed":False, "crossReviewUsed":False, "applyPerformed":False, "createdUtc":datetime.now(timezone.utc).isoformat(timespec="seconds")})
    (root / "README.md").write_text(f"""# ROMarrNG PR #70 W645–W664 primary semantic review

Fresh primary review bound to PR head `{HEAD}`, tree `{TREE}`. It covers 240 catalog cells across 20 source strings. Review began after the sealed candidate-free packet passed its portable verifier.

The primary ledger contains {counts['CHANGE']} proposed corrections or refinements and {counts['KEEP']} keep decisions for the 144 cells with exact production callers. The other 96 cells belong to 8 callerless source IDs and are retained as hash-only holds; their source and target text are omitted from the hold ledger. Every decision binds the exact source hash, current target hash, caller-context hash, and token checks.

No W645–W664 blind or cross-review output was consulted, and no prior W645 primary decision was reused. Native-speaker approval is not claimed. Independent blind review, cross-adjudication, and any application remain pending.

Verify with `python3 verify_primary.py --repo /path/to/the-exact-9f8832f-ROMarrNG-worktree` from this directory.
""", encoding="utf-8")
    print(json.dumps({"result":"PRIMARY_REVIEW_BUILT", "head":HEAD, "tree":TREE, "window":WINDOW, "dispositions":len(dispositions), "holds":len(hash_holds), "counts":summary["dispositionCounts"], "changesByLocale":dict(sorted(changes_by_locale.items())), "candidateFreeInputManifestSha256":primary_manifest_hash}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
