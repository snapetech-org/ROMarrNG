#!/usr/bin/env python3
"""Guard fixed ROMarr UI source text and registered app-message templates.

This deliberately checks authored HTML text and stable source messages. User,
provider, library, protocol, path, and exception payloads remain opaque unless
an explicit source template places that value inside a translated wrapper.
"""
from __future__ import annotations

import hashlib
import html
import ast
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "romarr" / "ui.py"
APP_PATH = ROOT / "romarr" / "app.py"
CATALOG_PATH = ROOT / "romarr" / "ui-labels.json"
MANIFEST_PATH = ROOT / "romarr" / "ui-source-messages.json"
DIRECT_CATEGORIES = {
    "ui", "ui-template", "ui-attribute", "ui-select", "ui-format-label",
    "ui-status", "ui-status-template", "ui-error", "ui-error-template",
    "api-error", "provider-diagnostic", "provider-diagnostic-template",
    "library-status-template", "task-label", "task-result",
    "task-result-template", "ecosystem-copy",
}
TAG_TEXT_PATTERN = re.compile(
    r"<(?P<tag>/?[A-Za-z][A-Za-z0-9:-]*)(?P<attrs>[^<>]*)>"
    r"(?P<text>[^<>]+)<",
    re.S,
)
OPTION_PATTERN = re.compile(r"<option\b(?P<attrs>[^>]*)>(?P<text>[^<>]+)</option>", re.S)
IGNORE_RAW_TEXT = {
    "ROM", "arr", "SeerrNG", "JSON", "CSV", "DAT",
    '{item["nativeName"]}', "{language_options}", "{badge}", "{THEME_BOOT}",
    "{_nav_html()}", "{oidc_error}", "{PUBLIC_I18N_JS}", "{LINK_JS}",
}
OPAQUE_CODE_TEXT = {"de, en", "downloaded_media", "PS2 Games", "JSON", "CSV", "DAT"}
# Literal placeholders that are examples, IDs, or user-entered values. These
# stay exactly as authored even when their surrounding form is localized.
OPAQUE_ATTRIBUTES = {
    "https://github.com/you/rom-hub-your-plugin",
    "https://github.com/you/your-plugin",
    "https://example.org/top-100.txt",
    "76561198000000000",
    "steamcommunity.com/dev/apikey",
    "from ca.account.sony.com/api/authz/v3/ssocookie",
    "itch.io/user/settings/api-keys",
    "https://their-server.example/link#i=…",
    "K7RM-9TFQ",
    "https://romm.their-server.com",
    "snes, n64",
    "e.g. PS2 Games",
    "https://romarr.example.com",
    "http://romarr:6868",
    "usa,world,europe,japan",
    "/downloads/roms",
    "000000",
    "http://192.168.1.20:7878",
}
ATTRIBUTE_PATTERN = re.compile(r"(?<![\w-])(placeholder|aria-label|title)=\"([^\"]+)\"")
TEXT_CONTENT_PATTERN = re.compile(r"\.textContent\s*=\s*(['\"])((?:\\.|(?!\1).)*?)\1", re.S)
DYNAMIC_MARKERS = ("${", "{", "esc(", "translate", "data-i18n")
OPAQUE_TEXT_CONTENT = {"REQUEST_WEBHOOK_URL="}
TASK_RESULT_METHODS = {
    "_auto_import_summary", "search_missing", "rss_sync",
    "retire_dead_downloads", "list_sync", "check_update",
    "start_hash_seed", "run_command",
}
TASK_PLACEHOLDER_ALIASES = {
    "VERSION": "version",
    "added": "count",
    "counted": "games",
    "library_count": "count",
    "known": "count",
    "unknown": "count",
    "grabbed_count": "grabbed",
    "ok": "imported",
}


def _looks_like_source_code(value: str) -> bool:
    return bool(
        re.search(r"['\"`]\s*\)?\s*\+|\+\s*['\"`]", value)
        or re.search(r"(?:^|[;{}])\s*(?:const|let|var|return|async|function)\b", value)
        or re.search(r"\b(?:interfaceMarkup|interfaceTemplateMarkup|appMessageMarkup|esc|fmt|JSON|URLSearchParams)\s*[.(]", value)
        or re.search(r"\b(?:if|else|for|while)\s*\(?", value)
        or re.search(r"\bfor\s+\w+\s+in\b|\bout\.append\s*\(", value)
        or re.search(r"[\"']\s*(?:data-|style=|aria-label=)|\b(?:data-i18n|data-plat)=", value)
        or re.search(r"(?:\)|\w|\])\s*\?", value)
        or any(token in value for token in (
            "${", "=>", "===", "!==", "JSON.stringify", "`", "page.innerHTML",
            "language_options =", "UI_SOURCE_TO_ID", "_theme_control_html",
            "_public_language_picker", "metadata.genres", "status.error",
            "resultsMarkup", "detail_markup", "innerHTML=", "innerHTML =",
            "metadata.summary?", "batch.has_more?", "python scripts/", "<your API key>",
        ))
        or "{" in value or "}" in value
        or value.startswith("--")
    )


def _without_template_expressions(source: str) -> str:
    """Keep static text around JS ${...} expressions for text-node extraction."""
    chunks: list[str] = []
    index = 0
    copied = 0
    while index + 1 < len(source):
        if source[index:index + 2] != "${":
            index += 1
            continue
        depth = 1
        cursor = index + 2
        quote = ""
        escaped = False
        while cursor < len(source) and depth:
            char = source[cursor]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = ""
            elif char in "'\"`":
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            cursor += 1
        chunks.append(source[copied:index])
        chunks.append("<i18n-boundary></i18n-boundary>")
        chunks.append("\n" * source.count("\n", index, cursor))
        copied = cursor
        index = max(cursor, index + 2)
    chunks.append(source[copied:])
    return "".join(chunks)


def _source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _stable_id(source: str) -> str:
    ascii_source = unicodedata.normalize("NFKD", source).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_source.lower()).strip("-")[:36].rstrip("-")
    return f"ui.{slug or 'message'}.{_source_hash(source)[:10]}"


def _source_anchor_tokens(source: str) -> list[str]:
    parts = [html.unescape(part).strip()
             for part in re.split(r"\{[A-Za-z][A-Za-z0-9_]*\}", source)
             if part.strip()]
    text = next((part for part in parts if re.search(r"[A-Za-z]{2,}", part)), source)
    return re.findall(r"[A-Za-z0-9]+", text)[:4]


def _location_has_source(location: str, source: str) -> bool:
    file_name, _, line_text = location.partition(":")
    target = ROOT / file_name
    if not target.is_file():
        return False
    line_match = re.match(r"(\d+)(?:-(\d+))?", line_text)
    if not line_match:
        return False
    start = int(line_match.group(1))
    end = int(line_match.group(2) or start)
    lines = target.read_text(encoding="utf-8").splitlines()
    context = re.sub(
        r"\s+", " ", html.unescape(" ".join(
            lines[max(0, start - 2):min(len(lines), end) + 2]
        ))
    ).casefold()
    return all(token.casefold() in context for token in _source_anchor_tokens(source))


def _raw_ui_text(source: str) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    source = _without_template_expressions(source)
    for match in TAG_TEXT_PATTERN.finditer(source):
        tag = match.group("tag").lower()
        attrs = match.group("attrs")
        value = re.sub(r"\s+", " ", html.unescape(match.group("text"))).strip()
        if tag in {"code", "/code"} and value in OPAQUE_CODE_TEXT:
            continue
        if (not value or len(value) > 480 or value in IGNORE_RAW_TEXT
                or not re.search(r"[A-Za-z]{2}", value)
                or _looks_like_source_code(value)
                or value.startswith(("http://", "https://", "/"))
                or any(token in value for token in (
                    "'+", "${", "esc(", "fmt(", "function", "=>", "join(",
                    "map(", "{html.", "{CSS", "{I18N", "URLSearchParams",
                    "JSON.stringify",
                ))
                or re.search(r"\b(?:Emulation/|metadata/|docs/|patch-catalog|\.json\b|\.d\b|python scripts/|--[a-z]+\b)", value)
                or len(re.findall(r"[A-Za-z]{2,}", value)) < 2):
            continue
        found.setdefault(value, []).append(source.count("\n", 0, match.start("text")) + 1)
    return found


def _lang_und_sources(source: str) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    source = _without_template_expressions(source)
    for match in TAG_TEXT_PATTERN.finditer(source):
        if not re.search(r"\blang\s*=\s*([\"'])und\1", match.group("attrs")):
            continue
        value = re.sub(r"\s+", " ", html.unescape(match.group("text"))).strip()
        if (not value or value in IGNORE_RAW_TEXT or value in OPAQUE_CODE_TEXT
                or any(marker in value for marker in DYNAMIC_MARKERS)
                or _looks_like_source_code(value)
                or not re.search(r"[A-Za-z]{2}", value)
                or len(re.findall(r"[A-Za-z]{2,}", value)) < 2):
            continue
        found.setdefault(value, []).append(source.count("\n", 0, match.start("text")) + 1)
    return found


def _attribute_sources(source: str) -> dict[str, list[tuple[str, int]]]:
    found: dict[str, list[tuple[str, int]]] = {}
    for match in ATTRIBUTE_PATTERN.finditer(source):
        kind, raw = match.groups()
        value = re.sub(r"\s+", " ", html.unescape(raw)).strip()
        if (not value or value in OPAQUE_ATTRIBUTES
                or re.fullmatch(r"ui\.[a-z0-9-]+\.[0-9a-f]{10}", value)
                or any(marker in value for marker in DYNAMIC_MARKERS)
                or "\'+" in value or "+\'" in value or "\n" in raw
                or "http://" in value or "https://" in value):
            continue
        found.setdefault(value, []).append((kind, source.count("\n", 0, match.start()) + 1))
    return found


def _select_option_sources(source: str) -> dict[str, list[tuple[bool, int]]]:
    found: dict[str, list[tuple[bool, int]]] = {}
    for match in OPTION_PATTERN.finditer(source):
        value = re.sub(r"\s+", " ", html.unescape(match.group("text"))).strip()
        attrs = match.group("attrs")
        if (not value or value in {"JSON", "CSV"}
                or any(marker in value for marker in DYNAMIC_MARKERS)
                or _looks_like_source_code(value)
                or not re.search(r"[A-Za-z]{2}", value)):
            continue
        marked = bool(re.search(r"\bdata-i18n(?:-key)?\s*=", attrs))
        found.setdefault(value, []).append((marked, source.count("\n", 0, match.start("text")) + 1))
    return found


def _task_placeholder(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return TASK_PLACEHOLDER_ALIASES.get(node.id, node.id.lower())
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "len" and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)):
        return {"done": "total", "releases": "items"}.get(node.args[0].id)
    if (isinstance(node, ast.Attribute) and node.attr == "__name__"
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "__class__"
            and isinstance(node.value.value, ast.Name)):
        return "error_type"
    return None


def _task_template(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        chunks: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                chunks.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                name = _task_placeholder(value.value)
                if name is None:
                    return None
                chunks.append("{" + name + "}")
            else:
                return None
        return "".join(chunks)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _task_template(node.left), _task_template(node.right)
        return None if left is None or right is None else left + right
    if isinstance(node, ast.IfExp):
        # Both variants are authored messages and each needs a stable key.
        return None
    return None


def _task_result_sources(source: str) -> dict[str, list[int]]:
    """Extract fixed task result strings from a narrow set of UI task methods.

    This avoids sweeping general API errors, provider responses, exception
    bodies, or user-entered data. Only returned message/detail fields, direct
    string results, and local message assignments in scheduled task handlers
    participate.
    """
    tree = ast.parse(source)
    found: dict[str, list[int]] = {}

    def add(node: ast.AST) -> None:
        value = _task_template(node)
        if value is None:
            return
        value = value.strip()
        value = re.sub(r"^[,;]\s*", "", value)
        if value:
            line = getattr(node, "lineno", 1)
            found.setdefault(value, []).append(line)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "ROMarr":
            continue
        for method in node.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    or method.name not in TASK_RESULT_METHODS:
                continue
            for child in ast.walk(method):
                if isinstance(child, ast.Return):
                    value = child.value
                    if isinstance(value, ast.Dict):
                        for key, result in zip(value.keys, value.values):
                            if (isinstance(key, ast.Constant)
                                    and key.value in {"message", "detail"}):
                                add(result)
                    elif isinstance(value, (ast.Constant, ast.JoinedStr)):
                        add(value)
                elif isinstance(child, ast.Assign):
                    names = {
                        target.id for target in child.targets
                        if isinstance(target, ast.Name)
                    }
                    if names & {"message", "msg"}:
                        value = child.value
                        if isinstance(value, ast.IfExp):
                            add(value.body)
                            add(value.orelse)
                        else:
                            add(value)
    return found


def _text_content_sources(source: str) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for match in TEXT_CONTENT_PATTERN.finditer(source):
        value = re.sub(r"\s+", " ", html.unescape(match.group(2))).strip()
        if (not value or value in OPAQUE_TEXT_CONTENT
                or any(marker in value for marker in DYNAMIC_MARKERS)
                or not re.search(r"[A-Za-z]{2}", value)):
            continue
        found.setdefault(value, []).append(source.count("\n", 0, match.start()) + 1)
    return found


def coverage_errors(catalog: dict | None = None) -> list[str]:
    errors: list[str] = []
    if catalog is None:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    messages = catalog.get("messages", {})
    source_to_id = {entry.get("source"): key for key, entry in messages.items()}
    locales = catalog.get("locales", {})
    direct = sorted(
        code for code in catalog.get("availableLocales", [])
        if code != "en" and locales.get(code, {}).get("status") == "available"
    )
    manifest_sources: set[str] = set()
    for row in manifest.get("messages", []):
        source = row.get("source")
        if not isinstance(source, str) or not source.strip():
            errors.append("source manifest contains an empty source")
            continue
        if source in manifest_sources:
            errors.append(f"source manifest contains duplicate source: {source!r}")
        manifest_sources.add(source)
        if row.get("id") != _stable_id(source):
            errors.append(f"source manifest ID is stale for {source!r}")
        if row.get("sourceHash") != _source_hash(source):
            errors.append(f"source manifest hash is stale for {source!r}")
        entry = messages.get(row.get("id"))
        if not entry or entry.get("source") != source:
            errors.append(f"source manifest message is missing from catalog: {row.get('id')}")
            continue
        if entry.get("sourceKind") != row.get("category"):
            errors.append(f"{row['id']}: catalog sourceKind disagrees with the source manifest")
        pending = entry.get("translationPending", [])
        expected_pending = row.get("pendingLocales", direct)
        if sorted(expected_pending) != direct:
            errors.append(f"{row['id']}: manifest pendingLocales must name every direct locale")
        if not isinstance(pending, list) or not set(pending) <= set(expected_pending):
            errors.append(f"{row['id']}: catalog pending locales exceed the frozen source bundle")
        if any(code in entry.get("translations", {}) for code in pending):
            errors.append(f"{row['id']}: pending source bundle contains translated locale text")
        for location in row.get("locations", []):
            file_name, _, line_text = location.partition(":")
            target = ROOT / file_name
            if not target.is_file():
                errors.append(f"{row['id']}: source location does not exist: {file_name}")
                continue
            line_match = re.match(r"(\d+)", line_text)
            if line_match and int(line_match.group(1)) > len(target.read_text(encoding="utf-8").splitlines()):
                errors.append(f"{row['id']}: source location is past end of file: {location}")
            elif not _location_has_source(location, source):
                errors.append(
                    f"{row['id']}: source wording is not present near its registered location: {location}"
                )

    ui_source = UI_PATH.read_text(encoding="utf-8")
    for source, lines in _raw_ui_text(ui_source).items():
        if source not in source_to_id:
            errors.append(
                f"raw rendered UI text is missing from the catalog at romarr/ui.py:{lines[0]}: {source!r}"
            )
    for source, lines in _lang_und_sources(ui_source).items():
        errors.append(
            f"fixed authored text bypasses localization under lang=und at romarr/ui.py:{lines[0]}: {source!r}"
        )
    for source, locations in _attribute_sources(ui_source).items():
        if source not in source_to_id:
            kind, line = locations[0]
            errors.append(
                f"raw rendered UI {kind} is missing from the catalog at romarr/ui.py:{line}: {source!r}"
            )
    for source, lines in _text_content_sources(ui_source).items():
        if source not in source_to_id:
            errors.append(
                f"raw UI textContent message is missing from the catalog at romarr/ui.py:{lines[0]}: {source!r}"
            )
    for source, locations in _select_option_sources(ui_source).items():
        if source in source_to_id:
            unmarked = [line for marked, line in locations if not marked]
            if unmarked:
                errors.append(
                    f"select option bypasses localization at romarr/ui.py:{unmarked[0]}: {source!r}"
                )
        else:
            marked, line = locations[0]
            errors.append(
                f"raw rendered select option is missing from the catalog at romarr/ui.py:{line}: {source!r}"
            )

    app_source = APP_PATH.read_text(encoding="utf-8")
    task_sources = _task_result_sources(app_source)
    catalog_sources = set(source_to_id)
    for source, lines in task_sources.items():
        # A fixed suffix is already covered when the complete returned
        # template is cataloged (for example the optional backoff count).
        if (source not in catalog_sources
                and any(source in complete for complete in task_sources
                        if complete != source and complete in catalog_sources)):
            continue
        if source not in source_to_id:
            errors.append(
                f"fixed task result is missing from the catalog at romarr/app.py:{lines[0]}: {source!r}"
            )

    # Return-message coverage is intentionally opt-in: only source templates
    # classified for visible UI/API/task output participate. Provider payloads,
    # exception bodies, and protocol-only error dictionaries are not swept into
    # the translation catalog.
    for row in manifest.get("messages", []):
        if row.get("category") not in DIRECT_CATEGORIES:
            errors.append(f"{row.get('id')}: unknown UI source category {row.get('category')!r}")
    return errors
