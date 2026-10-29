#!/usr/bin/env python3
"""Validate ROMarr's stable-key localization catalog and source references."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "romarr" / "ui-labels.json"
SNAPSHOT_PATH = ROOT / "romarr" / "ui-source-snapshot.json"
UI_PATH = ROOT / "romarr" / "ui.py"
PLACEHOLDER = re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")
STABLE_REFERENCE = re.compile(r"ui\.[a-z0-9-]+\.[0-9a-f]{10}")
LOCALIZATION_CALL = re.compile(
    r"\b(?:interfaceMarkup|interfaceTemplateMarkup|interfaceTitleTemplate|"
    r"toastLabel|toastMessage|confirmMessage|promptMessage|translateLabel)"
    r"\(\s*(['\"`])((?:\\\\.|(?!\1).)*?)\1",
    re.S,
)
LOCALIZATION_ATTRIBUTE = re.compile(
    r"(data-i18n(?:-key|-title|-aria-label|-placeholder|-template|-template-key|"
    r"-title-template|-title-template-key)?)=\"([^\"]+)\""
)


def placeholders(value: str) -> set[str]:
    return set(PLACEHOLDER.findall(value))


def validate() -> list[str]:
    errors: list[str] = []
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if catalog.get("schemaVersion") != 2:
        errors.append("catalog schemaVersion must be 2")
    if catalog.get("baseLocale") != "en":
        errors.append("baseLocale must be en")

    locales = catalog.get("locales", {})
    available = catalog.get("availableLocales", [])
    messages = catalog.get("messages", {})
    if len(locales) != 37:
        errors.append(f"expected 37 registered locales, found {len(locales)}")
    if len(available) != len(set(available)):
        errors.append("availableLocales contains duplicates")
    unknown = set(available) - set(locales)
    if unknown:
        errors.append(f"availableLocales references unknown locales: {sorted(unknown)}")
    for code, locale in locales.items():
        status = locale.get("status")
        if status not in {"available", "inherited", "planned"}:
            errors.append(f"{code}: invalid availability status {status!r}")
        if locale.get("direction") not in {"ltr", "rtl"}:
            errors.append(f"{code}: direction must be ltr or rtl")
        if (code in available) != (status in {"available", "inherited"}):
            errors.append(f"{code}: selectable locale and status disagree")
        if status == "inherited":
            parent = catalog.get("regionalParents", {}).get(code)
            if not parent or parent not in available or parent == code:
                errors.append(f"{code}: inherited locale needs a selectable parent")
        if status == "planned" and code in available:
            errors.append(f"{code}: planned locale must not be selectable")

    rtl_locales = set(catalog.get("rtlLocales", []))
    for code, locale in locales.items():
        expected_rtl = code.split("-", 1)[0] in rtl_locales
        if (locale.get("direction") == "rtl") != expected_rtl:
            errors.append(f"{code}: direction disagrees with rtlLocales")

    seen_sources: set[str] = set()
    current_snapshot: dict[str, str] = {}
    direct_locales = {code for code in available
                      if locales[code]["status"] == "available" and code != "en"}
    for key, message in messages.items():
        source = message.get("source")
        if not isinstance(source, str) or not source.strip():
            errors.append(f"{key}: missing English source")
            continue
        if source in seen_sources:
            errors.append(f"{key}: duplicate English source")
        seen_sources.add(source)
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        current_snapshot[key] = source_hash
        if message.get("sourceHash") != source_hash:
            errors.append(f"{key}: sourceHash does not match source text")
        translations = message.get("translations", {})
        extra_locales = set(translations) - (set(locales) | {"en"})
        if extra_locales:
            errors.append(f"{key}: unknown translation locales {sorted(extra_locales)}")

        for code, value in translations.items():
            if isinstance(value, str):
                values = {"other": value}
                required_placeholders = placeholders(source)
            elif (isinstance(value, dict) and value.get("kind") == "plural"
                  and isinstance(value.get("forms"), dict)):
                forms = value["forms"]
                if not forms.get("other"):
                    errors.append(f"{key}/{code}: plural message needs an other form")
                if not isinstance(value.get("argument"), str) or not value["argument"]:
                    errors.append(f"{key}/{code}: plural message needs an argument")
                values = forms
                if value.get("argument") not in placeholders(source):
                    errors.append(f"{key}/{code}: plural argument is not in source")
                required_placeholders = placeholders(source) - {value.get("argument")}
            else:
                errors.append(f"{key}/{code}: unsupported translation value")
                continue
            for form, translated in values.items():
                if not isinstance(translated, str) or not translated.strip():
                    errors.append(f"{key}/{code}/{form}: translation is empty")
                    continue
                found = placeholders(translated)
                if not required_placeholders <= found <= placeholders(source):
                    errors.append(f"{key}/{code}/{form}: placeholders differ from English")

        for code in direct_locales:
            if code not in translations:
                errors.append(f"{key}: missing direct translation for {code}")
        for code, locale in locales.items():
            if locale["status"] == "planned" and code in translations:
                errors.append(f"{key}: planned locale {code} contains unreviewed text")

    if current_snapshot != snapshot:
        errors.append("source snapshot is stale; run scripts/migrate_ui_catalog.py")
    ui_source = UI_PATH.read_text(encoding="utf-8")
    referenced = set(STABLE_REFERENCE.findall(ui_source))
    missing = referenced - set(messages)
    if missing:
        errors.append(f"ui.py references unknown stable IDs: {sorted(missing)[:12]}")
    source_to_id = {message["source"]: key for key, message in messages.items()}
    for _, literal in LOCALIZATION_CALL.findall(ui_source):
        if literal.startswith("ui."):
            if literal not in messages:
                errors.append(f"localization helper references unknown key {literal}")
        elif literal not in source_to_id:
            errors.append(f"localization helper source is missing from catalog: {literal[:100]!r}")
    for attribute, value in LOCALIZATION_ATTRIBUTE.findall(ui_source):
        # Attribute templates assembled from runtime values are validated by
        # their helper source and placeholder checks instead of this literal pass.
        if any(token in value for token in ("{", "${", "esc(", "+")):
            continue
        if value.startswith("ui."):
            if value not in messages:
                errors.append(f"{attribute} references unknown key {value}")
        elif value not in source_to_id:
            errors.append(f"{attribute} source is missing from catalog: {value[:100]!r}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    locales = catalog["locales"]
    available = catalog["availableLocales"]
    direct = sum(locales[code]["status"] == "available" and code != "en"
                 for code in available)
    inherited = sum(locales[code]["status"] == "inherited" for code in available)
    planned = sum(locale["status"] == "planned" for locale in locales.values())
    print(f"Valid: {len(catalog['messages']):,} stable messages, "
          f"{direct} directly translated locales, {inherited} regional fallbacks, "
          f"{planned} locales awaiting translation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
