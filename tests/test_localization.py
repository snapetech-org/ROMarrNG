"""Static localization contracts and the dependency-free browser runtime."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

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
    assert UI_CATALOG["schemaVersion"] == 2
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
  isolate:i18n.isolate('a\u202Eb')
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

    def test_runtime(self) -> None:
        test_runtime_resolves_canonical_locale_tags_rtl_and_plural_messages()
