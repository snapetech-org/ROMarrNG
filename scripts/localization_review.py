#!/usr/bin/env python3
"""Export and safely import per-locale human translation reviews."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "romarr" / "ui-labels.json"
PLACEHOLDER = re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")
PLURAL_CATEGORIES = {"zero", "one", "two", "few", "many", "other"}
MAX_REVIEW_BUNDLE_BYTES = 10 * 1024 * 1024
MAX_REVIEWER_LENGTH = 200


def content_hash(value: object) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _translation_forms(source: str, value: object, key: str) -> dict[str, str]:
    source_tokens = set(PLACEHOLDER.findall(source))
    if isinstance(value, str):
        forms = {"other": value}
        required_tokens = source_tokens
    elif (isinstance(value, dict) and value.get("kind") == "plural"
          and isinstance(value.get("forms"), dict)):
        if set(value) - {"kind", "argument", "forms"}:
            raise ValueError(f"{key}: plural value has unsupported fields")
        argument = value.get("argument")
        if not isinstance(argument, str) or argument not in source_tokens:
            raise ValueError(f"{key}: plural argument must be a source placeholder")
        forms = value["forms"]
        if "other" not in forms:
            raise ValueError(f"{key}: plural value needs an other form")
        required_tokens = source_tokens - {argument}
        for category in forms:
            if category not in PLURAL_CATEGORIES and not re.fullmatch(r"=-?\d+", category):
                raise ValueError(f"{key}: unsupported plural form {category!r}")
    else:
        raise ValueError(f"{key}: translation must be text or a plural object")

    for category, text in forms.items():
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{key}/{category}: translation is empty")
        found = set(PLACEHOLDER.findall(text))
        if not required_tokens <= found <= source_tokens:
            raise ValueError(f"{key}/{category}: placeholders differ from the English source")
    return forms


def export_bundle(catalog: dict[str, Any], locale: str,
                  *, include_reviewed: bool = False) -> dict[str, Any]:
    info = catalog.get("locales", {}).get(locale)
    if not info:
        raise ValueError(f"unknown locale: {locale}")
    if locale == catalog.get("baseLocale") or info.get("status") not in {
        "available", "draft", "planned"
    }:
        raise ValueError("review bundles require a direct or planned non-English locale")

    messages = []
    for key, entry in catalog["messages"].items():
        translation = entry.get("translations", {}).get(locale)
        if translation is None and info.get("status") == "available":
            raise ValueError(f"{key}/{locale}: direct locale is missing a translation")
        translation = "" if translation is None else translation
        status = entry.get("translationStatus", {}).get(
            locale, "fallback" if not translation else "unverified"
        )
        if status == "reviewed" and not include_reviewed:
            continue
        messages.append({
            "id": key,
            "source": entry["source"],
            "sourceHash": entry["sourceHash"],
            "translation": copy.deepcopy(translation),
            "translationHash": content_hash(translation),
            "status": status,
        })

    return {
        "bundleVersion": 1,
        "catalogSchemaVersion": catalog.get("schemaVersion"),
        "locale": locale,
        "localeName": info.get("englishName", locale),
        "instructions": [
            "Review the translation in its ROMarr context; do not translate game titles, paths, platform codes, API values, or product names.",
            "Keep every source placeholder. For plural messages, retain the argument and an other form.",
            "Edit only translation. Keep id, source, sourceHash, translationHash, and status unchanged; translationHash fingerprints the text at export time.",
            "Import rejects stale source or translation fingerprints.",
        ],
        "messages": messages,
    }


def apply_review_bundle(catalog: dict[str, Any], bundle: dict[str, Any],
                        reviewer: str, reviewed_at: str) -> tuple[dict[str, Any], int]:
    if not isinstance(bundle, dict):
        raise ValueError("review bundle must be a JSON object")
    if bundle.get("bundleVersion") != 1:
        raise ValueError("unsupported review bundle version")
    if bundle.get("catalogSchemaVersion") != catalog.get("schemaVersion"):
        raise ValueError("review bundle was created for a different catalog schema")
    locale = bundle.get("locale")
    if not isinstance(locale, str):
        raise ValueError("bundle locale must be a language tag")
    info = catalog.get("locales", {}).get(locale)
    if (not info or locale == catalog.get("baseLocale")
            or info.get("status") not in {"available", "draft", "planned"}):
        raise ValueError("bundle locale must be direct or planned and non-English")
    if (not isinstance(reviewer, str) or not reviewer.strip()
            or len(reviewer.strip()) > MAX_REVIEWER_LENGTH):
        raise ValueError(f"reviewer must contain 1 to {MAX_REVIEWER_LENGTH} characters")
    if not isinstance(reviewed_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed_at):
        raise ValueError("reviewed-at must be an ISO date (YYYY-MM-DD)")
    try:
        date.fromisoformat(reviewed_at)
    except ValueError as exc:
        raise ValueError("reviewed-at must be an ISO date (YYYY-MM-DD)") from exc

    entries = bundle.get("messages")
    if not isinstance(entries, list) or not entries:
        raise ValueError("review bundle contains no messages")
    by_id = catalog["messages"]
    seen: set[str] = set()
    reviewed = copy.deepcopy(catalog)
    reviewed_count = 0

    for row in entries:
        if not isinstance(row, dict):
            raise ValueError("each review entry must be an object")
        key = row.get("id")
        if not isinstance(key, str) or key in seen:
            raise ValueError(f"missing or duplicate message ID: {key!r}")
        seen.add(key)
        current = by_id.get(key)
        if current is None:
            raise ValueError(f"{key}: message ID no longer exists")
        current_translation = current.get("translations", {}).get(locale)
        current_translation_for_hash = "" if current_translation is None else current_translation
        current_source = current.get("source")
        if not isinstance(current_source, str):
            raise ValueError(f"{key}: catalog source text is invalid")
        current_source_hash = hashlib.sha256(current_source.encode("utf-8")).hexdigest()
        if row.get("source") != current_source \
                or row.get("sourceHash") != current_source_hash \
                or current.get("sourceHash") != current_source_hash:
            raise ValueError(f"{key}: English source changed or fingerprint is stale")
        if row.get("translationHash") != content_hash(current_translation_for_hash):
            raise ValueError(f"{key}/{locale}: translation changed after export")
        _translation_forms(current["source"], row.get("translation"), key)
        target = reviewed["messages"][key]
        target["translations"][locale] = copy.deepcopy(row["translation"])
        target.setdefault("translationStatus", {})[locale] = "reviewed"
        target.setdefault("translationHashes", {})[locale] = content_hash(row["translation"])
        target.setdefault("translationReview", {})[locale] = {
            "reviewer": reviewer.strip(),
            "reviewedAt": reviewed_at,
        }
        reviewed_count += 1

    all_translated = all(
        locale in entry.get("translations", {})
        for entry in reviewed["messages"].values()
    )
    any_translated = any(
        locale in entry.get("translations", {})
        for entry in reviewed["messages"].values()
    )
    all_reviewed = all_translated and all(
        entry.get("translationStatus", {}).get(locale) == "reviewed"
        for entry in reviewed["messages"].values()
    )
    if info.get("status") in {"planned", "draft"}:
        if all_translated and all_reviewed:
            reviewed["locales"][locale]["status"] = "available"
            reviewed["locales"][locale]["translationReview"] = "reviewed"
            if locale not in reviewed["availableLocales"]:
                reviewed["availableLocales"].append(locale)
        elif any_translated:
            reviewed["locales"][locale]["status"] = "draft"
            reviewed["locales"][locale]["translationReview"] = "draft"
            reviewed["availableLocales"] = [
                code for code in reviewed["availableLocales"] if code != locale
            ]
        else:
            reviewed["locales"][locale]["status"] = "planned"
            reviewed["locales"][locale]["translationReview"] = "not started"
    elif all_translated:
        reviewed["locales"][locale]["status"] = "available"
        reviewed["locales"][locale]["translationReview"] = (
            "reviewed" if all_reviewed else "unverified"
        )
        if locale not in reviewed["availableLocales"]:
            reviewed["availableLocales"].append(locale)
    return reviewed, reviewed_count


def write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="create a review bundle for one locale")
    export.add_argument("--locale", required=True)
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--include-reviewed", action="store_true")
    import_cmd = commands.add_parser("import", help="validate and optionally apply a review bundle")
    import_cmd.add_argument("--bundle", required=True, type=Path)
    import_cmd.add_argument("--reviewer", required=True)
    import_cmd.add_argument("--reviewed-at", required=True)
    import_cmd.add_argument("--apply", action="store_true",
                            help="write the validated changes to the catalog")
    args = parser.parse_args()

    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        if args.command == "export":
            bundle = export_bundle(catalog, args.locale,
                                   include_reviewed=args.include_reviewed)
            write_atomic(args.output, bundle)
            print(f"Exported {len(bundle['messages'])} {args.locale} messages to {args.output}")
            return 0

        if args.bundle.stat().st_size > MAX_REVIEW_BUNDLE_BYTES:
            raise ValueError("review bundle exceeds the 10 MiB size limit")
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        updated, count = apply_review_bundle(
            catalog, bundle, args.reviewer, args.reviewed_at
        )
        if args.apply:
            write_atomic(CATALOG_PATH, updated)
            print(f"Imported and marked {count} {bundle['locale']} messages reviewed.")
        else:
            print(f"Validated {count} {bundle['locale']} messages; re-run with --apply to update the catalog.")
        return 0
    except (OSError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
