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

    direct_locales = {
        code for code in UI_AVAILABLE_LOCALES
        if code != "en" and UI_CATALOG["locales"][code]["status"] == "available"
    }
    inherited = {"es-419": "es", "fr-CA": "fr"}
    for key, message in UI_MESSAGES.items():
        source = message["source"]
        assert key.startswith("ui.")
        assert UI_SOURCE_TO_ID[source] == key
        assert message["sourceHash"] == hashlib.sha256(source.encode()).hexdigest()
        pending = set(message.get("translationPending", []))
        assert pending <= direct_locales
        assert set(message["translations"]) - {"en"} == direct_locales - pending
        expected_labels = direct_locales - pending
        expected_labels.update(
            locale for locale, parent in inherited.items() if parent not in pending
        )
        assert set(UI_LABELS[source]) == expected_labels
        translation_status = message["translationStatus"]
        assert not translation_status
        assert not message["translationReview"]
        assert not message["translationHashes"]
        assert all(
            translation_status.get(locale, "unverified") == "unverified"
            for locale in direct_locales - pending
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
    assert "source-only fallbacks: 452 messages / 5,424 locale cells" in result.stdout


def test_source_bundle_freezes_only_pending_english_sources() -> None:
    spec = importlib.util.spec_from_file_location(
        "romarr_localization_review", ROOT / "scripts" / "localization_review.py"
    )
    assert spec and spec.loader
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)

    bundle = review.export_source_bundle(
        UI_CATALOG,
        "cedcbb66443891d0702954be5733fa6749f12155",
        "f" * 40,
    )
    assert bundle["messageCount"] == 452
    assert bundle["directPendingCells"] == 5_424
    assert re.fullmatch(r"[0-9a-f]{64}", bundle["manifestHash"])
    assert all("translation" not in row for row in bundle["messages"])
    assert all(
        set(row["translationPending"]) == {
            code for code in UI_CATALOG["availableLocales"]
            if code != "en" and UI_CATALOG["locales"][code]["status"] == "available"
        }
        for row in bundle["messages"]
    )


def test_source_coverage_guard_detects_authored_copy_and_exempt_values() -> None:
    spec = importlib.util.spec_from_file_location(
        "romarr_ui_source_coverage", ROOT / "scripts" / "check_ui_source_coverage.py"
    )
    assert spec and spec.loader
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)

    with tempfile.TemporaryDirectory() as directory:
        temp_root = Path(directory)
        ui_path = temp_root / "ui.py"
        manifest_path = temp_root / "manifest.json"
        guard.ROOT = temp_root
        guard.UI_PATH = ui_path
        guard.MANIFEST_PATH = manifest_path
        app_path = temp_root / "app.py"
        guard.APP_PATH = app_path
        manifest_path.write_text(json.dumps({"messages": []}), encoding="utf-8")
        app_path.write_text(
            'class ROMarr:\n'
            '    def search_missing(self):\n'
            '        return {"message": "Uncatalogued task result"}\n'
            '    def list_sync(self):\n'
            '        return {"message": provider_exception}\n',
            encoding="utf-8",
        )
        catalog = {
            "availableLocales": ["en", "es"],
            "locales": {"es": {"status": "available"}},
            "messages": {},
        }

        ui_path.write_text(
            '<p>Uncatalogued fixed message</p>\n'
            '<span lang="und">Fixed authored fallback text</span>\n'
            '<select><option>Unmarked source label</option></select>\n'
            '<span lang="und">${esc(provider_detail)}</span>'
            '<code>downloaded_media</code>\n',
            encoding="utf-8",
        )
        errors = guard.coverage_errors(catalog)
        assert any("Uncatalogued fixed message" in error for error in errors)
        assert any("Fixed authored fallback text" in error for error in errors)
        assert any("Unmarked source label" in error for error in errors)
        assert any("Uncatalogued task result" in error for error in errors)
        assert not any("provider_detail" in error for error in errors)
        assert not any("provider_exception" in error for error in errors)
        assert not any("downloaded_media" in error for error in errors)

        ui_path.write_text(
            "appMessageMarkup('Uncatalogued UI error fallback');\n"
            "interfaceTemplateMarkup('Uncatalogued HTTP {status}.',{status:code});\n"
            "message(result.message||'Uncatalogued organizer result.',false);\n",
            encoding="utf-8",
        )
        errors = guard.coverage_errors(catalog)
        assert any("Uncatalogued UI error fallback" in error for error in errors)
        assert any("Uncatalogued HTTP {status}." in error for error in errors)
        assert any("Uncatalogued organizer result." in error for error in errors)

        ui_path.write_text(
            '<p>Unmarked source label</p>\n'
            '<select><option>Unmarked source label</option></select>',
            encoding="utf-8",
        )
        app_path.write_text(
            'class ROMarr:\n'
            '    def list_sync(self):\n'
            '        return {"message": provider_exception}\n',
            encoding="utf-8",
        )
        source = "Unmarked source label"
        message_id = guard._stable_id(source)
        catalog["messages"] = {message_id: {"source": source}}
        manifest_path.write_text(json.dumps({"messages": []}), encoding="utf-8")
        errors = guard.coverage_errors(catalog)
        assert not any("missing from the catalog" in error for error in errors)
        assert any("select option bypasses localization" in error for error in errors)

        inline_app = temp_root / "romarr" / "app.py"
        inline_app.parent.mkdir(parents=True)
        inline_app.write_text(
            'if route.path == "/api/v1/metadataprovider/test":\n'
            '    return {"ok": False}\n',
            encoding="utf-8",
        )
        guard.VISIBLE_MESSAGE_METHODS = {}
        ui_path.write_text("", encoding="utf-8")
        errors = guard.coverage_errors(catalog)
        assert any("UI message coverage routes changed" in error for error in errors)
        assert any("UI message coverage fields changed" in error for error in errors)


def test_ui_consumed_api_and_organizer_messages_stay_catalogued() -> None:
    spec = importlib.util.spec_from_file_location(
        "romarr_ui_source_coverage", ROOT / "scripts" / "check_ui_source_coverage.py"
    )
    assert spec and spec.loader
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)

    visible_sources = guard._visible_api_message_sources()
    assert "a URL is required" in visible_sources
    assert "Connected, {indexers} indexer(s), {private} private" in visible_sources
    assert "{error_type}: {detail}" in visible_sources
    assert "Unsafe destination or unable to verify source" in visible_sources
    assert "Verified: {display_name}" in visible_sources
    assert "bad dump: the file is the size of a known ROM but its hash does not match. Import anyway only if you know why -- a patch, a hack or a translation will look exactly like this." in visible_sources
    assert "no URL given" in visible_sources
    assert "must be https -- plain http lets anyone on the network choose what code you run" in visible_sources
    assert "no host in the URL" in visible_sources
    assert "that is a host, not a repository" in visible_sources
    assert "{host} is not an allowed source. Allowed: {allowed}. Add it under Settings if you host your own forge." in visible_sources
    assert "repository: {reason}" in visible_sources
    assert "unknown provider" in visible_sources
    assert "lookup failed: {error_type}" in visible_sources
    assert "found Chrono Trigger -- the key works" in visible_sources
    assert "the provider answered but found nothing -- check the key" in visible_sources
    assert "unknown connection type" in visible_sources
    assert "missing required field: {labels}" in visible_sources
    assert "delivery raised {error_type}" in visible_sources
    assert "test notification delivered" in visible_sources
    assert "delivery failed; check the connection settings" in visible_sources
    assert "Title ID found in TitleDB; file bytes are not verified" in visible_sources
    assert "{url} answered HTTP {status_code}" in visible_sources
    assert "IGDB catalog is not configured" in visible_sources
    assert "IGDB catalog request failed" in visible_sources
    assert "No DAT catalog is loaded in ROMarrNG" in visible_sources
    assert "library is still loading" in visible_sources
    assert all(
        any(location.startswith("romarr/app.py:") for location in visible_sources[source])
        for source in (
            "IGDB catalog is not configured",
            "IGDB catalog request failed",
            "No DAT catalog is loaded in ROMarrNG",
            "library is still loading",
        )
    )
    assert "Read {seen} entries and found {added} with a hash. Netplay can match those. The other {without} are catalogued entries your library has never scanned off a disk, so there is nothing to match them on. None matched a DAT, so all are unverified -- check the DAT directory under Settings." in visible_sources
    assert "added from {name}'s shelf" not in visible_sources
    api_added_sources = {
        "Prowlarr feed could not be reached ({error_type}).",
        "Prowlarr feed returned HTTP {status_code}.",
        "Prowlarr feed returned an HTML page instead of an indexer response.",
        "Prowlarr feed returned an indexer error response.",
        "Prowlarr indexer inventory returned HTTP {status_code}.",
        "Prowlarr management API could not be read ({error_type}).",
        "Prowlarr management API returned HTTP {status_code}.",
        "Prowlarr returned an invalid indexer inventory.",
        "Prowlarr returned an invalid system status.",
        "ROM Hub filesystem confinement could not start ({error_type})",
        "ROMarr has not hashed this game yet, so it cannot prove which dump you have. Run an audit of this platform under Tasks and try again.",
        "ROMarr has not hashed this game yet, so it cannot prove which dump you have. Run an audit of {platform} under Tasks and try again.",
        "Read from your library server's own hashes, and upgraded to verified by an audit or a verified import.",
        "You both have this exact dump, but EmulatorJS has no core for {platform} -- you will need a native emulator that can join a room.",
        "could not fetch the list: {error_type}",
        "could not reach {name}: {detail}",
        "could not read {name}: {detail}",
        "invalid hub result: {detail}",
        "no such friend",
        "no such peer",
        "not in this library; the hash identifies exactly which dump to acquire",
        "plugin '{slug}' is disabled",
        "plugin '{slug}' is not installed: {detail}",
        "plugin fetch failed ({error_type})",
        "plugin output escapes the staging directory",
        "the bytes match, but one side has not verified this dump against a DAT",
        "the invitation carried no hash, so the dump cannot be matched -- ROMarr will not start a session it cannot prove",
        "this friend is not confirmed yet -- confirm them before asking their server for anything",
        "this friend's invitation carried no address, so there is nowhere to call. Ask them to set their public URL and send a fresh invitation.",
        "you both have this game and they are different dumps -- netplay would desync within seconds, which usually gets blamed on the connection",
        "{name} answered HTTP {status_code}",
        "{name} refused the credential -- they may have removed you, or not confirmed you yet",
        "{name} sent something that was not JSON",
    }
    assert api_added_sources <= set(visible_sources)

    direct_locales = {
        code for code in UI_AVAILABLE_LOCALES
        if code != "en" and UI_CATALOG["locales"][code]["status"] == "available"
    }
    for source, kind in {
        "a URL is required": "ui-error",
        "Connected, {indexers} indexer(s), {private} private": "ui-status-template",
        "{error_type}: {detail}": "ui-error-template",
        "unknown provider": "ui-error",
        "lookup failed: {error_type}": "ui-error-template",
        "found Chrono Trigger -- the key works": "ui-status",
        "the provider answered but found nothing -- check the key": "ui-error",
        "unknown connection type": "ui-error",
        "missing required field: {labels}": "ui-error-template",
        "delivery raised {error_type}": "ui-error-template",
        "test notification delivered": "ui-status",
        "delivery failed; check the connection settings": "ui-error",
        "Title ID found in TitleDB; file bytes are not verified": "ui-status",
        "{url} answered HTTP {status_code}": "ui-error-template",
        "bad dump: the file is the size of a known ROM but its hash does not match. Import anyway only if you know why -- a patch, a hack or a translation will look exactly like this.": "ui-error",
        "Read {seen} entries and found {added} with a hash. Netplay can match those. The other {without} are catalogued entries your library has never scanned off a disk, so there is nothing to match them on. None matched a DAT, so all are unverified -- check the DAT directory under Settings.": "library-status-template",
        "IGDB catalog is not configured": "api-error",
        "IGDB catalog request failed": "api-error",
        "No DAT catalog is loaded in ROMarrNG": "api-error",
        "library is still loading": "api-error",
        "Catalog could not be loaded": "ui-error",
        "library ownership is unavailable": "ui-error",
        "Owned check unavailable": "ui-status",
        "Title mapping saved. This game is now eligible for a safe rename preview.": "ui-status",
        "Rename batch applied.": "ui-status",
        "Undid {count} rename(s).": "ui-status-template",
        "Choose one platform before publishing its ES-DE gamelist.": "ui-error",
        "Published {count} ES-DE entries.": "ui-status-template",
        "Could not remove this list.": "ui-error",
        "Could not remove this entry.": "ui-error",
        "Could not remove this list (HTTP {status}).": "ui-error-template",
        "Could not remove this entry (HTTP {status}).": "ui-error-template",
        "Prowlarr feed could not be reached ({error_type}).": "provider-diagnostic-template",
        "Prowlarr feed returned HTTP {status_code}.": "provider-diagnostic-template",
        "Prowlarr feed returned an HTML page instead of an indexer response.": "provider-diagnostic",
        "Prowlarr feed returned an indexer error response.": "provider-diagnostic",
        "Prowlarr indexer inventory returned HTTP {status_code}.": "provider-diagnostic-template",
        "Prowlarr management API could not be read ({error_type}).": "provider-diagnostic-template",
        "Prowlarr management API returned HTTP {status_code}.": "provider-diagnostic-template",
        "Prowlarr returned an invalid indexer inventory.": "provider-diagnostic",
        "Prowlarr returned an invalid system status.": "provider-diagnostic",
        "ROM Hub filesystem confinement could not start ({error_type})": "provider-diagnostic-template",
        "ROMarr has not hashed this game yet, so it cannot prove which dump you have. Run an audit of this platform under Tasks and try again.": "ui-status",
        "ROMarr has not hashed this game yet, so it cannot prove which dump you have. Run an audit of {platform} under Tasks and try again.": "ui-status-template",
        "Read from your library server's own hashes, and upgraded to verified by an audit or a verified import.": "ui-status",
        "You both have this exact dump, but EmulatorJS has no core for {platform} -- you will need a native emulator that can join a room.": "ui-status-template",
        "could not fetch the list: {error_type}": "provider-diagnostic-template",
        "could not reach {name}: {detail}": "ui-error-template",
        "could not read {name}: {detail}": "ui-error-template",
        "invalid hub result: {detail}": "provider-diagnostic-template",
        "no such friend": "ui-error",
        "no such peer": "ui-error",
        "not in this library; the hash identifies exactly which dump to acquire": "ui-status",
        "plugin '{slug}' is disabled": "ui-error-template",
        "plugin '{slug}' is not installed: {detail}": "provider-diagnostic-template",
        "plugin fetch failed ({error_type})": "provider-diagnostic-template",
        "plugin output escapes the staging directory": "ui-error",
        "the bytes match, but one side has not verified this dump against a DAT": "ui-status",
        "the invitation carried no hash, so the dump cannot be matched -- ROMarr will not start a session it cannot prove": "ui-status",
        "this friend is not confirmed yet -- confirm them before asking their server for anything": "ui-error",
        "this friend's invitation carried no address, so there is nowhere to call. Ask them to set their public URL and send a fresh invitation.": "ui-error",
        "you both have this game and they are different dumps -- netplay would desync within seconds, which usually gets blamed on the connection": "ui-status",
        "{name} answered HTTP {status_code}": "ui-error-template",
        "{name} refused the credential -- they may have removed you, or not confirmed you yet": "ui-error-template",
        "{name} sent something that was not JSON": "ui-error-template",
    }.items():
        entry = UI_CATALOG["messages"][UI_SOURCE_TO_ID[source]]
        assert entry["sourceKind"] == kind
        assert entry["translations"] == {}
        assert set(entry["translationPending"]) == direct_locales

    source_manifest = json.loads(
        (ROOT / "romarr" / "ui-source-messages.json").read_text()
    )
    source_rows = {row["source"]: row for row in source_manifest["messages"]}
    added_sources = {
        "IGDB catalog is not configured",
        "IGDB catalog request failed",
        "No DAT catalog is loaded in ROMarrNG",
        "library is still loading",
        "Catalog could not be loaded",
        "library ownership is unavailable",
        "Owned check unavailable",
        "Title mapping saved. This game is now eligible for a safe rename preview.",
        "Rename batch applied.",
        "Undid {count} rename(s).",
        "Choose one platform before publishing its ES-DE gamelist.",
        "Published {count} ES-DE entries.",
        "Could not remove this list.",
        "Could not remove this entry.",
        "Could not remove this list (HTTP {status}).",
        "Could not remove this entry (HTTP {status}).",
    }
    assert len(source_manifest["messages"]) == 452
    assert set(source_rows) >= added_sources | api_added_sources
    for source in added_sources | api_added_sources:
        assert set(source_rows[source]["dynamicPlaceholders"]) == set(
            re.findall(r"\{([A-Za-z][A-Za-z0-9_]*)\}", source)
        )

    ui_source = (ROOT / "romarr" / "ui.py").read_text(encoding="utf-8")
    assert "appMessageMarkup(msg)" in ui_source
    assert "line(r.ok, r.message || (r.ok ? 'Connected' : 'Failed'))" in ui_source
    assert "problems.map(submissionProblemMarkup)" in ui_source
    assert "interfaceMarkup('Repository')+': '+appMessageMarkup(repository[1])" in ui_source
    assert "organizerMatchDetailsMarkup(row.match_details,row.confidence,row.match_details_source)" in ui_source
    assert "interfaceMarkup('Owned check unavailable')+': '+appMessageMarkup(ownedError)" in ui_source
    assert "interfaceTemplateMarkup(\n        'Could not remove this list (HTTP {status}).'" in ui_source
    assert "interfaceTemplateMarkup(\n        'Could not remove this entry (HTTP {status}).'" in ui_source
    assert "messageTemplate('Undid {count} rename(s).'" in ui_source
    assert "messageTemplate('Published {count} ES-DE entries.'" in ui_source
    assert "appMessageMarkup(data.error)" in ui_source
    assert "appMessageMarkup(ownedError)" in ui_source
    assert guard._runtime_template_covers("repository: {reason}", set(UI_SOURCE_TO_ID))
    assert guard.coverage_errors(UI_CATALOG) == []

    catalog = json.loads(json.dumps(UI_CATALOG))
    catalog["messages"].pop(UI_SOURCE_TO_ID["a URL is required"])
    errors = guard.coverage_errors(catalog)
    assert any(
        "fixed UI-consumed API message is missing from the catalog"
        in error and "a URL is required" in error
        for error in errors
    )
    catalog = json.loads(json.dumps(UI_CATALOG))
    catalog["messages"].pop(UI_SOURCE_TO_ID["IGDB catalog request failed"])
    errors = guard.coverage_errors(catalog)
    assert any(
        "fixed UI-consumed API message is missing from the catalog"
        in error and "IGDB catalog request failed" in error
        for error in errors
    )


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

    def test_source_bundle(self) -> None:
        test_source_bundle_freezes_only_pending_english_sources()

    def test_source_coverage_guard(self) -> None:
        test_source_coverage_guard_detects_authored_copy_and_exempt_values()

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
