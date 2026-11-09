"""Shared configuration validation and credential handling.

Public views, portable backups and settings updates must agree about which
values are credentials. Authentication identity is never replaced by restore.
"""
from __future__ import annotations

import copy
import math
from urllib.parse import parse_qsl, urlsplit

IDENTITY_KEYS = frozenset({
    "_api_key", "_seerrng_api_key", "_password_hash", "_totp_secret",
    "_totp_backup", "_totp_used", "_session_key", "_session_epoch",
    "_organizer_journal_key", "_peers",
})
SECRET_FIELDS = frozenset({
    "password", "api_key", "apikey", "passkey", "token", "secret", "key",
    "api_token", "app_token", "client_secret", "access_token", "refresh_token",
    "npsso", "openxbl_key", "itchio_key", "ea_token", "epic_code",
    "humble_cookie", "battlenet_cookie", "epic_refresh", "cookie", "cookies", "authorization",
})
COLLECTIONS = frozenset({"download_clients", "indexers", "libraries",
                         "connections", "metadata_providers", "import_lists"})


def secret_field(key: str) -> bool:
    key = key.lower()
    return (key in IDENTITY_KEYS or key in SECRET_FIELDS
            or key.endswith(("_password", "_secret", "_token", "_api_key")))


def credential_url(value) -> bool:
    if not isinstance(value, str) or "://" not in value:
        return False
    try:
        parts = urlsplit(value)
        return bool(parts.username or parts.password or any(
            secret_field(k) for k, _ in parse_qsl(parts.query)))
    except ValueError:
        return True


def redact_settings(value, *, mask="********", context="", public=False):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if public and key in IDENTITY_KEYS:
                continue
            sensitive = (secret_field(key) or credential_url(item)
                         or (context == "connections" and key == "url"))
            result[key] = (mask if item else "") if sensitive else redact_settings(
                item, mask=mask, context=key if key in COLLECTIONS else context,
                public=public)
        return result
    if isinstance(value, list):
        return [redact_settings(v, mask=mask, context=context, public=public)
                for v in value]
    return copy.deepcopy(value)


def preserve_masked(new, old, *, context=""):
    """Preserve placeholders, never persist a displayed mask as a credential."""
    if isinstance(new, dict):
        old = old if isinstance(old, dict) else {}
        out = {}
        for key, value in new.items():
            if value == "********" and (secret_field(key) or credential_url(old.get(key))
                    or (context == "connections" and key == "url")):
                out[key] = copy.deepcopy(old.get(key, ""))
            else:
                out[key] = preserve_masked(value, old.get(key),
                    context=key if key in COLLECTIONS else context)
        return out
    if isinstance(new, list):
        previous = old if isinstance(old, list) else []
        by_id = {str(x["id"]): x for x in previous if isinstance(x, dict) and x.get("id")}
        return [preserve_masked(v, by_id.get(str(v.get("id")), {})
                if isinstance(v, dict) else None, context=context) for v in new]
    return copy.deepcopy(new)


def validate_settings(settings: dict, defaults: dict) -> None:
    """Validate the whole candidate before it changes live or durable state."""
    if not isinstance(settings, dict):
        raise ValueError("settings must be an object")
    enums = {"library_layout": {"flat", "nested"},
             "translation_policy": {"exclude", "fill", "prefer", "keep_both"},
             "region_mode": {"prefer", "strict"},
             "protocol": {"torrent", "usenet", "any", "direct", "browser", "hub"}}
    for key, value in settings.items():
        expected = defaults.get(key)
        if key in defaults:
            if isinstance(expected, bool):
                ok = isinstance(value, bool)
            elif isinstance(expected, (float, int)):
                ok = (isinstance(value, (int, float)) and not isinstance(value, bool)
                      and math.isfinite(value) and 0 <= value <= 1_000_000_000)
            else:
                ok = isinstance(value, type(expected))
            if not ok:
                raise ValueError(f"invalid type or range for {key}")
        if key in enums and value not in enums[key]:
            raise ValueError(f"invalid value for {key}")
        if key in COLLECTIONS:
            if not isinstance(value, list) or len(value) > 10000:
                raise ValueError(f"{key} must be a bounded list")
            for row in value:
                if not isinstance(row, dict):
                    raise ValueError(f"{key} entries must be objects")
                for name, field in row.items():
                    if secret_field(name) and not isinstance(field, str):
                        raise ValueError(f"{key}.{name} must be text")
                    if name == "port":
                        if isinstance(field, bool) or not str(field).isdecimal() or not 1 <= int(field) <= 65535:
                            raise ValueError(f"{key}.port must be between 1 and 65535")
                    if isinstance(field, str) and (len(field) > 65536 or "\0" in field):
                        raise ValueError(f"invalid text for {key}.{name}")
                    if name in {"enable", "enabled", "use_ssl"} and not isinstance(field, bool):
                        raise ValueError(f"{key}.{name} must be boolean")
                    if name in {"path", "save_path", "url", "base_url", "type", "name"} and not isinstance(field, str):
                        raise ValueError(f"{key}.{name} must be text")
        if key in {"preferred_regions", "translation_langs"} and not all(isinstance(v, str) for v in value):
            raise ValueError(f"{key} must contain text")
        if key == "platform_folder_mappings" and not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
            raise ValueError("platform_folder_mappings must map text to text")
        if key == "remote_path_mappings":
            if not all(isinstance(row, dict) and all(isinstance(row.get(k, ""), str)
                       for k in ("local", "remote", "client_id")) for row in value):
                raise ValueError("remote_path_mappings must contain path objects")
        if isinstance(value, str) and (len(value) > 65536 or "\0" in value):
            raise ValueError(f"invalid text for {key}")
