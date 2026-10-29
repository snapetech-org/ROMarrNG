"""Static localization contracts and the dependency-free browser runtime."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from romarr.ui import (
    UI_AVAILABLE_LOCALES,
    UI_CATALOG,
    UI_LABELS,
    UI_MESSAGES,
    UI_SOURCE_TO_ID,
    link_page,
    login_page,
    page,
    steam_result_page,
)

ROOT = Path(__file__).parents[1]
PLACEHOLDER = re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")


def _message_forms(value: object) -> dict[str, str]:
    if isinstance(value, str):
        return {"other": value}
    assert isinstance(value, dict) and value.get("kind") == "plural"
    assert isinstance(value.get("forms"), dict)
    return value["forms"]


def test_catalog_is_stable_complete_and_marks_unfinished_locales() -> None:
    assert UI_CATALOG["schemaVersion"] == 3
    assert len(UI_CATALOG["locales"]) == 37
    assert len(UI_AVAILABLE_LOCALES) == 15
    assert UI_CATALOG["locales"]["es-419"]["status"] == "inherited"
    assert UI_CATALOG["locales"]["fr-CA"]["status"] == "inherited"
    assert sum(locale["status"] == "planned"
               for locale in UI_CATALOG["locales"].values()) == 22
    assert len(UI_MESSAGES) == len(UI_SOURCE_TO_ID) == len(UI_LABELS)
    assert set(UI_CATALOG["availableLocales"]) == set(UI_AVAILABLE_LOCALES)

    for key, message in UI_MESSAGES.items():
        source = message["source"]
        assert key.startswith("ui.")
        assert UI_SOURCE_TO_ID[source] == key
        assert message["sourceHash"] == hashlib.sha256(source.encode()).hexdigest()
        assert set(UI_LABELS[source]) == set(UI_AVAILABLE_LOCALES) - {"en"}
        translation_status = message["translationStatus"]
        assert not translation_status
        assert not message["translationReview"]
        assert not message["translationHashes"]
        assert all(
            translation_status.get(locale, "unverified") == "unverified"
            for locale in UI_AVAILABLE_LOCALES if locale != "en"
        )
        source_tokens = set(PLACEHOLDER.findall(source))
        for locale, translation in message["translations"].items():
            required = source_tokens
            if isinstance(translation, dict):
                required = source_tokens - {translation["argument"]}
            for form, translated in _message_forms(translation).items():
                assert translated.strip(), (key, locale, form)
                actual = set(PLACEHOLDER.findall(translated))
                assert required <= actual <= source_tokens, (
                    key, locale, form
                )

    snapshot = json.loads((ROOT / "romarr" / "ui-source-snapshot.json").read_text())
    assert snapshot == {key: value["sourceHash"] for key, value in UI_MESSAGES.items()}


def test_language_picker_and_rtl_shell_use_catalogue_metadata() -> None:
    rendered = page()
    selector = re.search(r'<select id="interface-language"[^>]*>(.*?)</select>', rendered, re.S)
    assert selector
    offered = set(re.findall(r'<option value="([^"]+)"', selector.group(1)))
    assert offered == {"system", *UI_AVAILABLE_LOCALES}
    assert 'data-i18n-key="ui.library.' in rendered
    assert "document.documentElement.dir=ROMarrI18n.isRTL(language,UI_CATALOG)?'rtl':'ltr'" in rendered
    assert "[dir=rtl] #rail{transform:translateX(105%)}" in rendered
    assert "data-i18n-key=\"ui.use-browser-settings." in rendered


def test_public_localization_pages_have_safe_script_catalogs() -> None:
    class ScriptParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.scripts: list[str] = []
            self.current: list[str] | None = None

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag.lower() == "script":
                self.current = []

        def handle_data(self, data: str) -> None:
            if self.current is not None:
                self.current.append(data)

        def handle_endtag(self, tag: str) -> None:
            if tag.lower() == "script" and self.current is not None:
                self.scripts.append("".join(self.current))
                self.current = None

    node = shutil.which("node")
    pages = [login_page(claimed=False), link_page(),
             steam_result_page("connected", "sample")]
    assert all(
        'data-i18n-key="ui.use-browser-settings.02d22d3f39"' in rendered
        for rendered in pages
    )
    for rendered in pages:
        parser = ScriptParser()
        parser.feed(rendered)
        assert parser.scripts
        for script in parser.scripts:
            if "const catalog=" in script:
                assert "</script" not in script.lower()
                assert "\\u003c" in script
            if node:
                checked = subprocess.run([node, "--check"], input=script,
                                         text=True, capture_output=True, timeout=15)
                assert checked.returncode == 0, checked.stderr


def test_localization_checker_accepts_repository_catalog() -> None:
    result = subprocess.run(
        ["python", str(ROOT / "scripts" / "check_localizations.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "12 directly translated locales" in result.stdout
    assert "22 locales awaiting translation" in result.stdout


def test_runtime_resolves_canonical_locale_tags_rtl_and_plural_messages() -> None:
    node = shutil.which("node")
    if not node:
        return
    script = r"""
const fs=require('node:fs');
require('./romarr/i18n_runtime.js');
const i18n=globalThis.ROMarrI18n;
const catalog=JSON.parse(fs.readFileSync('./romarr/ui-labels.json','utf8'));
const pluralKey=Object.keys(catalog.messages).find(key=>
  catalog.messages[key].source==='Connected to {friend}: {count} title with hashes ROMarr can match on.');
const out={
  fr:i18n.resolveLocale(['fr-CA'],catalog,catalog.availableLocales),
  es:i18n.resolveLocale(['es-MX'],catalog,catalog.availableLocales),
  zh:i18n.resolveLocale(['zh-TW'],catalog,catalog.availableLocales),
  text:i18n.lookup(catalog,'ui.interface-language.8027f432a7','zh-Hans').value,
  inherited:i18n.lookup(catalog,'ui.interface-language.8027f432a7','fr-CA').locale,
  rtl:i18n.isRTL('ar',catalog),
  ltr:i18n.isRTL('fr',catalog),
  zero:i18n.translate(catalog,pluralKey,'fr-CA',{friend:'Nora',count:0},'fr-CA'),
  one:i18n.translate(catalog,pluralKey,'fr-CA',{friend:'Nora',count:1},'fr-CA'),
  many:i18n.translate(catalog,pluralKey,'fr-CA',{friend:'Nora',count:2},'fr-CA'),
  isolate:i18n.isolate('a\u202Eb'),
  controls:i18n.isolate('A\u061cB\u200eC\u200fD\u202aE\u202cF\u2066G\u2069H\u206aI\u206fJ')
};
process.stdout.write(JSON.stringify(out));
"""
    result = subprocess.run([node, "-e", script], cwd=ROOT, text=True,
                            capture_output=True, check=False, timeout=15)
    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["fr"] == "fr-CA"
    assert values["es"] == "es-419"
    assert values["zh"] == "zh-Hant"
    assert values["text"] == "界面语言"
    assert values["inherited"] == "fr"
    assert values["rtl"] and not values["ltr"]
    without_isolates = lambda value: value.replace("\u2068", "").replace("\u2069", "")
    assert "0 titres" in without_isolates(values["zero"])
    assert "1 titre" in without_isolates(values["one"])
    assert "2 titres" in without_isolates(values["many"])
    assert "\u202e" not in values["isolate"]
    controls_without_isolates = values["controls"].replace("\u2068", "").replace("\u2069", "")
    assert controls_without_isolates == "ABCDEFGHIJ"
    assert not re.search(r"[\u061c\u200e\u200f\u202a-\u202e\u2066-\u206f]",
                         controls_without_isolates)


class LocalizationTests(unittest.TestCase):
    """Expose the focused checks to Python's built-in unittest runner."""

    def test_catalog(self) -> None:
        test_catalog_is_stable_complete_and_marks_unfinished_locales()

    def test_picker_and_rtl(self) -> None:
        test_language_picker_and_rtl_shell_use_catalogue_metadata()

    def test_public_pages(self) -> None:
        test_public_localization_pages_have_safe_script_catalogs()

    def test_checker(self) -> None:
        test_localization_checker_accepts_repository_catalog()

    def test_checker_accepts_a_partial_hidden_locale(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "romarr_check_localizations", ROOT / "scripts" / "check_localizations.py"
        )
        assert spec and spec.loader
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)

        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            catalog = json.loads(json.dumps(UI_CATALOG))
            locale = "it"
            key = UI_SOURCE_TO_ID["Use browser settings"]
            entry = catalog["messages"][key]
            entry["translations"][locale] = "Usa le impostazioni del browser"
            entry["translationStatus"][locale] = "draft"
            entry["translationHashes"][locale] = checker.translation_hash(
                entry["translations"][locale]
            )
            catalog["locales"][locale]["status"] = "draft"
            catalog["locales"][locale]["translationReview"] = "draft"

            catalog_path = temp_root / "ui-labels.json"
            snapshot_path = temp_root / "ui-source-snapshot.json"
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False),
                                    encoding="utf-8")
            snapshot_path.write_text(
                (ROOT / "romarr" / "ui-source-snapshot.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            checker.CATALOG_PATH = catalog_path
            checker.SNAPSHOT_PATH = snapshot_path
            checker.UI_PATH = ROOT / "romarr" / "ui.py"
            self.assertEqual(checker.validate(), [])

    def test_runtime(self) -> None:
        test_runtime_resolves_canonical_locale_tags_rtl_and_plural_messages()

    def test_migration_review_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            catalog_path = temp_root / "ui-labels.json"
            snapshot_path = temp_root / "ui-source-snapshot.json"
            catalog = json.loads(json.dumps(UI_CATALOG))
            message = next(
                message for message in catalog["messages"].values()
                if isinstance(message["translations"].get("es"), str)
            )
            source = message["source"]
            key = UI_SOURCE_TO_ID[source]
            message["translationStatus"]["es"] = "reviewed"
            message["translationReview"]["es"] = {
                "reviewer": "QA reviewer",
                "reviewedAt": "2026-10-28",
            }
            serialized = json.dumps(message["translations"]["es"], ensure_ascii=False,
                                    sort_keys=True, separators=(",", ":"))
            message["translationHashes"]["es"] = hashlib.sha256(
                serialized.encode()
            ).hexdigest()
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False),
                                    encoding="utf-8")

            spec = importlib.util.spec_from_file_location(
                "romarr_migrate_ui_catalog", ROOT / "scripts" / "migrate_ui_catalog.py"
            )
            assert spec and spec.loader
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)
            migration.CATALOG = catalog_path
            migration.SNAPSHOT = snapshot_path

            with redirect_stdout(io.StringIO()):
                assert migration.main() == 0
            migrated = json.loads(catalog_path.read_text(encoding="utf-8"))
            preserved = migrated["messages"][key]
            assert preserved["translationStatus"]["es"] == "reviewed"
            assert preserved["translationReview"]["es"]["reviewer"] == "QA reviewer"

            preserved["translations"]["es"] += " (edited)"
            catalog_path.write_text(json.dumps(migrated, ensure_ascii=False),
                                    encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                assert migration.main() == 0
            changed = json.loads(catalog_path.read_text(encoding="utf-8"))["messages"][key]
            assert changed["translationStatus"].get("es", "unverified") == "unverified"
            assert "es" not in changed["translationHashes"]
            assert "es" not in changed["translationReview"]

            changed_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            changed_catalog["messages"][key]["translationStatus"]["es"] = "reviewed"
            changed_catalog["messages"][key]["translationReview"]["es"] = {
                "reviewer": "QA reviewer",
                "reviewedAt": "2026-10-28",
            }
            changed_translation = changed_catalog["messages"][key]["translations"]["es"]
            serialized = json.dumps(changed_translation, ensure_ascii=False,
                                    sort_keys=True, separators=(",", ":"))
            changed_catalog["messages"][key]["translationHashes"]["es"] = (
                hashlib.sha256(serialized.encode()).hexdigest()
            )
            changed_catalog["messages"][key]["source"] = source + " Updated wording."
            catalog_path.write_text(json.dumps(changed_catalog, ensure_ascii=False),
                                    encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                assert migration.main() == 0
            source_changed = json.loads(catalog_path.read_text(encoding="utf-8"))["messages"][key]
            assert source_changed["source"] == source + " Updated wording."
            assert source_changed["translationStatus"].get("es", "unverified") == "unverified"
            assert "es" not in source_changed["translationReview"]

    def test_review_bundle_accepts_edits_and_rejects_stale_content(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "romarr_localization_review", ROOT / "scripts" / "localization_review.py"
        )
        assert spec and spec.loader
        review = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(review)

        catalog = json.loads(json.dumps(UI_CATALOG))
        key = next(
            key for key, entry in catalog["messages"].items()
            if isinstance(entry["translations"].get("es"), str)
        )
        bundle = review.export_bundle(catalog, "es")
        row = next(message for message in bundle["messages"] if message["id"] == key)
        original = catalog["messages"][key]["translations"]["es"]
        row["translation"] = original + " revisado"

        updated, count = review.apply_review_bundle(
            catalog, {**bundle, "messages": [row]}, "Reviewer", "2026-10-29"
        )
        self.assertEqual(count, 1)
        self.assertEqual(catalog["messages"][key]["translations"]["es"], original)
        self.assertEqual(
            updated["messages"][key]["translations"]["es"],
            original + " revisado",
        )
        self.assertEqual(updated["messages"][key]["translationStatus"]["es"], "reviewed")
        self.assertEqual(
            updated["messages"][key]["translationReview"]["es"],
            {"reviewer": "Reviewer", "reviewedAt": "2026-10-29"},
        )

        stale_catalog = json.loads(json.dumps(catalog))
        stale_catalog["messages"][key]["translations"]["es"] += " changed elsewhere"
        with self.assertRaisesRegex(ValueError, "translation changed after export"):
            review.apply_review_bundle(
                stale_catalog, {**bundle, "messages": [row]}, "Reviewer", "2026-10-29"
            )
        self.assertNotIn("it", catalog["messages"][key]["translations"])

        stale_source_catalog = json.loads(json.dumps(catalog))
        source_entry = stale_source_catalog["messages"][key]
        source_entry["source"] += " changed"
        source_entry["sourceHash"] = hashlib.sha256(
            source_entry["source"].encode()
        ).hexdigest()
        with self.assertRaisesRegex(ValueError, "English source changed"):
            review.apply_review_bundle(
                stale_source_catalog, {**bundle, "messages": [row]},
                "Reviewer", "2026-10-29",
            )

        bad_schema = {**bundle, "catalogSchemaVersion": 999, "messages": [row]}
        with self.assertRaisesRegex(ValueError, "different catalog schema"):
            review.apply_review_bundle(catalog, bad_schema, "Reviewer", "2026-10-29")
        with self.assertRaisesRegex(ValueError, "JSON object"):
            review.apply_review_bundle(catalog, [], "Reviewer", "2026-10-29")
        with self.assertRaisesRegex(ValueError, "reviewer must contain"):
            review.apply_review_bundle(
                catalog, {**bundle, "messages": [row]}, "R" * 201, "2026-10-29"
            )
        with self.assertRaisesRegex(ValueError, "ISO date"):
            review.apply_review_bundle(
                catalog, {**bundle, "messages": [row]}, "Reviewer", "2026-02-30"
            )

    def test_planned_locale_stays_hidden_until_every_message_is_reviewed(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "romarr_localization_review_promotion",
            ROOT / "scripts" / "localization_review.py",
        )
        assert spec and spec.loader
        review = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(review)

        def message(source: str) -> dict[str, object]:
            return {
                "source": source,
                "sourceHash": hashlib.sha256(source.encode()).hexdigest(),
                "translations": {},
                "translationHashes": {},
                "translationStatus": {},
                "translationReview": {},
            }

        catalog = {
            "schemaVersion": 3,
            "baseLocale": "en",
            "availableLocales": ["en"],
            "locales": {
                "en": {"status": "available"},
                "it": {"status": "planned", "englishName": "Italian"},
            },
            "messages": {
                "ui.test.0000000001": message("Hello {name}"),
                "ui.test.0000000002": message("Goodbye {name}"),
            },
        }
        first = review.export_bundle(catalog, "it")
        first["messages"] = first["messages"][:1]
        first["messages"][0]["translation"] = "Ciao {name}"
        partial, count = review.apply_review_bundle(
            catalog, first, "Italian reviewer", "2026-10-29"
        )
        self.assertEqual(count, 1)
        self.assertEqual(partial["locales"]["it"]["status"], "draft")
        self.assertNotIn("it", partial["availableLocales"])

        second = review.export_bundle(partial, "it")
        self.assertEqual(len(second["messages"]), 1)
        second["messages"][0]["translation"] = "Arrivederci {name}"
        complete, count = review.apply_review_bundle(
            partial, second, "Italian reviewer", "2026-10-29"
        )
        self.assertEqual(count, 1)
        self.assertEqual(complete["locales"]["it"]["status"], "available")
        self.assertIn("it", complete["availableLocales"])

    def test_review_cli_exports_dry_runs_and_applies_atomically(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "romarr_localization_review_cli",
            ROOT / "scripts" / "localization_review.py",
        )
        assert spec and spec.loader
        review = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(review)

        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            catalog_path = temp_root / "ui-labels.json"
            bundle_path = temp_root / "it-review.json"
            catalog_path.write_text(
                json.dumps(UI_CATALOG, ensure_ascii=False), encoding="utf-8"
            )
            review.CATALOG_PATH = catalog_path

            with patch.object(sys, "argv", [
                "localization_review.py", "export", "--locale", "it",
                "--output", str(bundle_path),
            ]), redirect_stdout(io.StringIO()):
                self.assertEqual(review.main(), 0)
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            self.assertEqual(len(bundle["messages"]), len(UI_MESSAGES))
            bundle["messages"] = bundle["messages"][:1]
            bundle["messages"][0]["translation"] = "Traduzione di prova"
            bundle_path.write_text(json.dumps(bundle, ensure_ascii=False),
                                   encoding="utf-8")
            before = catalog_path.read_bytes()

            with patch.object(sys, "argv", [
                "localization_review.py", "import", "--bundle", str(bundle_path),
                "--reviewer", "CLI test reviewer", "--reviewed-at", "2026-10-29",
            ]), redirect_stdout(io.StringIO()):
                self.assertEqual(review.main(), 0)
            self.assertEqual(catalog_path.read_bytes(), before)

            with patch.object(sys, "argv", [
                "localization_review.py", "import", "--bundle", str(bundle_path),
                "--reviewer", "CLI test reviewer", "--reviewed-at", "2026-10-29",
                "--apply",
            ]), redirect_stdout(io.StringIO()):
                self.assertEqual(review.main(), 0)
            applied = json.loads(catalog_path.read_text(encoding="utf-8"))
            self.assertEqual(applied["locales"]["it"]["status"], "draft")
            self.assertNotIn("it", applied["availableLocales"])
            imported = next(
                item for item in applied["messages"].values()
                if item["translations"].get("it") == "Traduzione di prova"
            )
            self.assertEqual(imported["translationStatus"]["it"], "reviewed")
