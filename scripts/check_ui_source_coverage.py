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
    "task-result-template", "ecosystem-copy", "ui-help-template",
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
VISIBLE_MESSAGE_METHODS = {
    "romarr/app.py": {
        "test_indexer", "test_client", "test_library", "collection_plan",
        "index_hashes_from_library", "friend_want", "audit_library",
        "scan_launchers", "connect_launchers", "claim_invitation", "adopt",
        "_friend", "_call_friend", "_romm_friend_rows", "friend_shelf",
        "netplay_invite", "claim_invitation",
    },
    "romarr/organizer.py": {
        "_scan", "start_scan", "records", "map_record", "rename_plan",
        "apply_rename_plan", "undo_last", "publish_esde",
    },
    "romarr/playability.py": {"submit_pin"},
    "romarr/hub.py": {"plugins", "fetch"},
    "romarr/titled.py": {"validate_switch_rom"},
    "romarr/notify.py": {"send_test"},
    "romarr/catalogue.py": {"check_source", "problems"},
    "romarr/federation.py": {
        "parse_invite_link", "redeem", "accept", "add_romm", "netplay_answer",
    },
    "romarr/indexers.py": {"diagnose"},
    "romarr/downloaders.py": {"_run"},
}
VISIBLE_INLINE_MESSAGE_ROUTES = {
    "romarr/app.py": {
        "/api/v1/importlist/preview": {"error"},
        "/api/v1/hashes": {"detail"},
        "/api/v1/metadataprovider/test": {"message"},
        "/api/v1/connection/test": {"message"},
        "/api/v1/totp/enroll": {"note"},
        "/api/v1/peer/invite": {"note", "warning"},
        "/api/v1/peer/redeem": {"error"},
        "/api/v1/peer/romm": {"error"},
        "/api/v1/peer/accept": {"error"},
        "/api/v1/peer/policy": {"error"},
        "/api/v1/hub/source/check": {"reason"},
        "/api/v1/hub/submit": {"problems"},
    },
}
VISIBLE_LITERAL_MESSAGE_SOURCES = {
    "romarr/app.py": {
        "IGDB catalog is not configured",
        "IGDB catalog request failed",
        "No DAT catalog is loaded in ROMarrNG",
        "library is still loading",
    },
    "romarr/ui.py": {"Catalog could not be loaded", "library ownership is unavailable"},
}
VISIBLE_MESSAGE_FIELDS = {
    "error", "message", "detail", "warning", "note", "reason", "match_details",
    "match_details_source", "details",
}
VISIBLE_EXCEPTION_METHODS = {
    "romarr/organizer.py": {
        "start_scan", "map_record", "rename_plan", "apply_rename_plan",
        "undo_last", "publish_esde",
    },
    "romarr/federation.py": {
        "parse_invite_link", "redeem", "accept", "add_romm",
    },
    "romarr/hub.py": {"fetch"},
}
JS_LABEL_MAPS = ("confidenceLabel", "head", "accessLabels")
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
    text = next((part for part in parts if re.search(r"[A-Za-z]{2,}", part)), "")
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
    anchors = _source_anchor_tokens(source)
    # Placeholder-only wrappers (for example "{error_type}: {detail}") have
    # no literal word to anchor. Their explicit line location is the source
    # evidence, while the coverage pass below validates the source template.
    return not anchors or all(token.casefold() in context for token in anchors)


def _message_expression(node: ast.AST) -> set[str]:
    """Return fixed text and placeholder templates from one bounded API value."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.JoinedStr):
        def formatted(expression: ast.AST, conversion: int = -1) -> set[str]:
            if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
                return {expression.value}
            if isinstance(expression, (ast.BoolOp, ast.IfExp)):
                branches = (expression.values if isinstance(expression, ast.BoolOp)
                            else (expression.body, expression.orelse))
                return set().union(*(formatted(branch) for branch in branches))
            name: str | None = None
            if isinstance(expression, ast.Name):
                aliases = {
                    "err": "detail", "exc": "detail", "root": "path",
                    "platform_name": "platform", "platform_slug": "platform",
                    "rows": "entries", "indexers": "indexers",
                    "published_media": "covers",
                }
                name = aliases.get(expression.id, expression.id)
            elif (isinstance(expression, ast.Call)
                  and isinstance(expression.func, ast.Name)
                  and expression.func.id == "len" and len(expression.args) == 1):
                target = expression.args[0]
                if isinstance(target, ast.Name) and target.id == "indexers":
                    name = "indexers"
                elif isinstance(target, ast.Name) and target.id == "rows":
                    name = "entries"
                elif isinstance(target, ast.Subscript):
                    name = "launchers" if getattr(target.slice, "value", None) == "counts" else "count"
                else:
                    name = "count"
            elif (isinstance(expression, ast.Call)
                  and isinstance(expression.func, ast.Attribute)
                  and isinstance(expression.func.value, ast.Name)):
                name = (
                    "kind" if expression.func.attr == "get"
                    and expression.func.value.id == "cfg"
                    and expression.args
                    and isinstance(expression.args[0], ast.Constant)
                    and expression.args[0].value == "type"
                    else expression.func.value.id
                )
            elif (isinstance(expression, ast.Call)
                  and isinstance(expression.func, ast.Attribute)
                  and expression.func.attr == "join"
                  and len(expression.args) == 1
                  and isinstance(expression.args[0], ast.Name)):
                name = expression.args[0].id
            elif isinstance(expression, ast.Attribute):
                name = "error_type" if expression.attr == "__name__" else expression.attr
            elif isinstance(expression, ast.Subscript):
                key = expression.slice
                name = ({"state": "state", "total": "games", "url": "url"}.get(
                    key.value, "kind") if isinstance(key, ast.Constant) else "kind")
            if name is None:
                return set()
            # Hub slugs use !r; retain those known identifier quotes while
            # leaving the runtime slug value opaque.
            if conversion == ord("r") and name == "slug":
                return {"'{" + name + "}'"}
            return {"{" + name + "}"}

        variants = [""]
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                variants = [prefix + value.value for prefix in variants]
            elif isinstance(value, ast.FormattedValue):
                choices = formatted(value.value, value.conversion)
                if not choices:
                    return set()
                variants = [prefix + choice for prefix in variants for choice in choices]
            else:
                return set()
        return set(variants)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _message_expression(node.left), _message_expression(node.right)
        return {a + b for a in left for b in right} if left and right else set()
    if isinstance(node, ast.IfExp):
        return _message_expression(node.body) | _message_expression(node.orelse)
    if isinstance(node, ast.BoolOp):
        return set().union(*(_message_expression(value) for value in node.values))
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "str" and len(node.args) == 1):
        return _message_expression(node.args[0])
    return set()


def _visible_api_message_sources() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for relative, names in VISIBLE_MESSAGE_METHODS.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    or node.name not in names:
                continue
            local_sources: dict[str, set[str]] = {}
            for statement in ast.walk(node):
                if isinstance(statement, ast.Assign):
                    targets = statement.targets
                    expression = statement.value
                elif isinstance(statement, ast.AnnAssign):
                    targets = [statement.target]
                    expression = statement.value
                else:
                    continue
                values = _message_expression(expression) if expression is not None else set()
                if values:
                    for target in targets:
                        if isinstance(target, ast.Name):
                            local_sources.setdefault(target.id, set()).update(values)

            def sources_for(expression: ast.AST) -> set[str]:
                if isinstance(expression, ast.Name):
                    return set(local_sources.get(expression.id, ()))
                if isinstance(expression, ast.BoolOp):
                    return set().union(*(sources_for(value) for value in expression.values))
                if isinstance(expression, ast.IfExp):
                    return sources_for(expression.body) | sources_for(expression.orelse)
                return _message_expression(expression)

            for child in ast.walk(node):
                values: set[str] = set()
                if isinstance(child, ast.Dict):
                    for key, value in zip(child.keys, child.values):
                        if (isinstance(key, ast.Constant)
                                and key.value in VISIBLE_MESSAGE_FIELDS):
                            if node.name == "claim_invitation" and key.value == "detail":
                                # The invitation UI replaces this success detail
                                # with its localized message using the peer name.
                                continue
                            values.update(sources_for(value))
                if isinstance(child, ast.Assign):
                    if any(
                        isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and target.slice.value in VISIBLE_MESSAGE_FIELDS
                        for target in child.targets
                    ):
                        values.update(sources_for(child.value))
                if (relative == "romarr/app.py"
                        and node.name in {"_friend", "_call_friend", "_romm_friend_rows"}
                        and isinstance(child, ast.Return)
                        and isinstance(child.value, ast.Tuple)
                        and len(child.value.elts) >= 2):
                    values.update(sources_for(child.value.elts[1]))
                if isinstance(child, ast.Call):
                    for keyword in child.keywords:
                        if keyword.arg in {"error", "reason"}:
                            values.update(sources_for(keyword.value))
                    if (relative == "romarr/catalogue.py" and node.name == "problems"
                            and isinstance(child.func, ast.Attribute)
                            and child.func.attr == "append" and child.args):
                        values.update(sources_for(child.args[0]))
                    if (relative in VISIBLE_EXCEPTION_METHODS
                            and node.name in VISIBLE_EXCEPTION_METHODS[relative]
                            and isinstance(child.func, ast.Name)
                            and child.func.id == "ValueError" and child.args):
                        values.update(sources_for(child.args[0]))
                if (relative == "romarr/notify.py" and node.name == "send_test"
                        and isinstance(child, ast.Return)
                        and isinstance(child.value, ast.Tuple)
                        and len(child.value.elts) == 2):
                    # The shared connection editor displays the message half
                    # of send_test's (ok, message) result. Dynamic notifier
                    # reasons are intentionally opaque; fixed fallback text
                    # and app-authored wrappers are catalog sources.
                        values.update(sources_for(child.value.elts[1]))
                for value in values:
                    normalized = re.sub(r"\s+", " ", value).strip()
                    if normalized:
                        found.setdefault(normalized, []).append(
                            f"{relative}:{getattr(child, 'lineno', 1)}")

    for relative, routes in VISIBLE_INLINE_MESSAGE_ROUTES.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            route_path = _route_path_condition(node.test)
            if route_path not in routes:
                continue
            expected_fields = routes[route_path]
            for child in ast.walk(node):
                if not isinstance(child, ast.Dict):
                    continue
                for key, value in zip(child.keys, child.values):
                    if isinstance(key, ast.Constant) and key.value in expected_fields:
                        for source_text in _message_expression(value):
                            normalized = re.sub(r"\s+", " ", source_text).strip()
                            if normalized:
                                found.setdefault(normalized, []).append(
                                    f"{relative}:{getattr(child, 'lineno', 1)}")
    for relative, expected_sources in VISIBLE_LITERAL_MESSAGE_SOURCES.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for source_text in expected_sources:
                if source_text in line:
                    found.setdefault(source_text, []).append(
                        f"{relative}:{line_number}")
    return found


def _connect_how_template_records() -> tuple[list[tuple[str, str, str]], list[str]]:
    """Collect trusted localized instruction descriptors from connect-source tables."""
    path = ROOT / "romarr" / "connect.py"
    if not path.is_file():
        return [], ["romarr/connect.py is missing"]
    tree = ast.parse(path.read_text(encoding="utf-8"))
    records: list[tuple[str, str, str]] = []
    errors: list[str] = []
    table_names = {"TOKEN_SOURCES", "PASTE_SOURCES"}
    for node in tree.body:
        if (not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict)
                or not any(isinstance(target, ast.Name) and target.id in table_names
                           for target in node.targets)):
            continue
        table = next(target.id for target in node.targets
                     if isinstance(target, ast.Name) and target.id in table_names)
        for entry in node.value.values:
            if not isinstance(entry, ast.Dict):
                continue
            how = next((value for key, value in zip(entry.keys, entry.values)
                        if isinstance(key, ast.Constant) and key.value == "how"), None)
            if how is None:
                continue
            descriptor = next((value for key, value in zip(entry.keys, entry.values)
                               if isinstance(key, ast.Constant)
                               and key.value == "how_template"), None)
            if not isinstance(descriptor, ast.Dict):
                errors.append(
                    f"{table} instruction is missing how_template at "
                    f"romarr/connect.py:{getattr(how, 'lineno', 1)}"
                )
                continue
            fields = {
                key.value: value for key, value in zip(descriptor.keys, descriptor.values)
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            sources = _message_expression(fields.get("source", ast.Constant(None)))
            keys = _message_expression(fields.get("key", ast.Constant(None)))
            if len(sources) != 1 or len(keys) != 1:
                errors.append(
                    f"{table} how_template must have one fixed source and key at "
                    f"romarr/connect.py:{getattr(descriptor, 'lineno', 1)}"
                )
                continue
            source = next(iter(sources))
            values_node = fields.get("values")
            value_names = {
                key.value for key in values_node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            } if isinstance(values_node, ast.Dict) else set()
            values_are_fixed_text = (
                isinstance(values_node, ast.Dict)
                and len(value_names) == len(values_node.keys)
                and all(isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        for value in values_node.values)
            )
            source_names = set(re.findall(
                r"\{([A-Za-z][A-Za-z0-9_]*)\}", source,
            ))
            if not values_are_fixed_text or value_names != source_names:
                errors.append(
                    f"{table} how_template placeholder values differ from its source at "
                    f"romarr/connect.py:{getattr(descriptor, 'lineno', 1)}"
                )
                continue
            records.append((
                source,
                next(iter(keys)),
                f"romarr/connect.py:{getattr(fields.get('source'), 'lineno', 1)}",
            ))
    return records, errors


def _route_path_condition(node: ast.AST) -> str | None:
    if isinstance(node, ast.BoolOp):
        found = {
            route_path for value in node.values
            if (route_path := _route_path_condition(value)) is not None
        }
        return next(iter(found)) if len(found) == 1 else None
    if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
        return None
    if not isinstance(node.ops[0], ast.Eq) or not isinstance(node.comparators[0], ast.Constant):
        return None
    left = node.left
    if (isinstance(left, ast.Attribute) and left.attr == "path"
            and isinstance(left.value, ast.Name) and left.value.id == "route"
            and isinstance(node.comparators[0].value, str)):
        return node.comparators[0].value
    return None


def _visible_message_surface_errors() -> list[str]:
    errors: list[str] = []
    for relative, expected in VISIBLE_MESSAGE_METHODS.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        missing = sorted(expected - found)
        if missing:
            errors.append(
                f"UI message coverage surface changed at {relative}; "
                f"review missing methods: {', '.join(missing)}"
            )
    for relative, expected_routes in VISIBLE_INLINE_MESSAGE_ROUTES.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found_routes = {
            route_path for node in ast.walk(tree) if isinstance(node, ast.If)
            if (route_path := _route_path_condition(node.test)) is not None
        }
        missing_routes = sorted(set(expected_routes) - found_routes)
        if missing_routes:
            errors.append(
                f"UI message coverage routes changed at {relative}; review missing routes: "
                f"{', '.join(missing_routes)}"
            )
        for route_path, expected_fields in expected_routes.items():
            route_nodes = [
                node for node in ast.walk(tree) if isinstance(node, ast.If)
                and _route_path_condition(node.test) == route_path
            ]
            found_fields = {
                key.value for route_node in route_nodes for child in ast.walk(route_node)
                if isinstance(child, ast.Dict)
                for key in child.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            for route_node in route_nodes:
                for child in ast.walk(route_node):
                    if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                        continue
                    targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                    for target in targets:
                        if (isinstance(target, ast.Subscript)
                                and isinstance(target.slice, ast.Constant)
                                and isinstance(target.slice.value, str)):
                            found_fields.add(target.slice.value)
            missing_fields = sorted(expected_fields - found_fields)
            if missing_fields:
                errors.append(
                    f"UI message coverage fields changed at {relative} {route_path}; "
                    f"review missing fields: {', '.join(missing_fields)}"
                )
    for relative, expected_sources in VISIBLE_LITERAL_MESSAGE_SOURCES.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        for message in sorted(expected_sources):
            if message not in source:
                errors.append(
                    f"UI message coverage literal changed at {relative}; "
                    f"review missing source: {message!r}"
                )
    return errors


def _localized_ui_call_sources(source: str) -> dict[str, list[int]]:
    """Find literal messages and stable keys passed into localization sinks."""
    calls = re.compile(
        r"\b(?:interfaceMarkup|interfaceTemplateMarkup|appMessageMarkup|"
        r"toastAppMessage|toastLabel|toastMessage|message|messageTemplate)"
        r"\(\s*(['\"])((?:\\.|(?!\1).)*?)\1",
        re.S,
    )
    fallbacks = re.compile(
        r"\b(?:appMessageMarkup|toastAppMessage|message|line)\([^)]*?\|\|\s*"
        r"(['\"])((?:\\.|(?!\1).)*?)\1",
        re.S,
    )
    found: dict[str, list[int]] = {}
    for pattern in (calls, fallbacks):
        for match in pattern.finditer(source):
            raw = match.group(2)
            try:
                value = ast.literal_eval(match.group(1) + raw + match.group(1))
            except (SyntaxError, ValueError):
                value = raw
            if (not isinstance(value, str) or not value
                    or not re.search(r"[A-Za-z]{2}", value)):
                continue
            found.setdefault(value, []).append(source.count("\n", 0, match.start()) + 1)
    return found


def _runtime_template_covers(source: str, catalog_sources: set[str]) -> bool:
    # appMessageMarkup intentionally reuses these existing templates while
    # keeping the dynamic provider/platform/path detail as an isolated value.
    aliases = {
        "unknown platform: {platform}",
        "search failed: {error}",
    }
    if source in aliases and source in catalog_sources:
        return True
    if source == "repository: {reason}" and "Repository" in catalog_sources:
        # The Hub submission form renders the existing field label separately
        # and runs the reason through appMessageMarkup, preserving known source
        # templates while keeping arbitrary URL details opaque.
        return True
    if (re.fullmatch(r"unknown platform: \{[a-zA-Z_][a-zA-Z0-9_]*\}", source)
            and "unknown platform: {platform}" in catalog_sources):
        return True
    if (re.fullmatch(r"search failed: \{[a-zA-Z_][a-zA-Z0-9_]*\}", source)
            and "search failed: {error}" in catalog_sources):
        return True
    return False


def _js_label_map_sources(source: str) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for name in JS_LABEL_MAPS:
        match = re.search(
            rf"const\s+{re.escape(name)}\s*=\s*\{{(?P<body>.*?)^\s*\}}",
            source, re.S | re.M)
        if not match:
            continue
        for value in re.finditer(r"\b[A-Za-z_][A-Za-z0-9_]*\s*:\s*(['\"])(.*?)\1",
                                 match.group("body"), re.S):
            text = re.sub(r"\s+", " ", html.unescape(value.group(2))).strip()
            if text and re.search(r"[A-Za-z]{2}", text):
                line = source.count("\n", 0, match.start("body") + value.start(2)) + 1
                found.setdefault(text, []).append(line)
    return found


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
    catalog_ids = set(messages)
    for source, lines in _localized_ui_call_sources(ui_source).items():
        if source not in source_to_id and source not in catalog_ids:
            errors.append(
                f"fixed localized UI message is missing from the catalog at "
                f"romarr/ui.py:{lines[0]}: {source!r}"
            )
    for source, lines in _raw_ui_text(ui_source).items():
        if source not in source_to_id:
            errors.append(
                f"raw rendered UI text is missing from the catalog at romarr/ui.py:{lines[0]}: {source!r}"
            )
    for source, lines in _js_label_map_sources(ui_source).items():
        if source not in source_to_id:
            errors.append(
                f"fixed JavaScript label map text is missing from the catalog at romarr/ui.py:{lines[0]}: {source!r}"
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

    for source, locations in _visible_api_message_sources().items():
        if (source not in catalog_sources
                and not _runtime_template_covers(source, catalog_sources)):
            errors.append(
                "fixed UI-consumed API message is missing from the catalog at "
                f"{locations[0]}: {source!r}"
            )
    connect_templates, connect_template_errors = _connect_how_template_records()
    errors.extend(connect_template_errors)
    for source, key, location in connect_templates:
        catalog_key = source_to_id.get(source)
        if catalog_key is None:
            errors.append(
                f"connect-source instruction is missing from the catalog at "
                f"{location}: {source!r}"
            )
        elif key != catalog_key:
            errors.append(
                f"connect-source descriptor key disagrees with the catalog at "
                f"{location}: {key!r} != {catalog_key!r}"
            )
    connect_key_match = re.search(
        r"const\s+CONNECT_HOW_TEMPLATE_KEYS\s*=\s*new Set\(\[(.*?)\]\);",
        ui_source, re.S,
    )
    expected_connect_keys = {key for _, key, _ in connect_templates}
    rendered_connect_keys = (
        set(re.findall(r"['\"](ui\.[a-z0-9-]+\.[0-9a-f]{10})['\"]",
                       connect_key_match.group(1)))
        if connect_key_match else set()
    )
    if not connect_key_match or rendered_connect_keys != expected_connect_keys:
        errors.append(
            "connect-source template allowlist does not match the trusted source descriptors"
        )
    errors.extend(_visible_message_surface_errors())

    # Return-message coverage is intentionally opt-in: only source templates
    # classified for visible UI/API/task output participate. Provider payloads,
    # exception bodies, and protocol-only error dictionaries are not swept into
    # the translation catalog.
    for row in manifest.get("messages", []):
        if row.get("category") not in DIRECT_CATEGORIES:
            errors.append(f"{row.get('id')}: unknown UI source category {row.get('category')!r}")
    return errors
