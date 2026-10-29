"""Internet Archive software search and safe direct-download manifests.

This speaks Archive.org's public Advanced Search and Metadata APIs, then routes
eligible files through ROMarr's existing Direct HTTP download client. Search
uses Archive.org metadata and advertised file lists; it does not crawl file
payloads or try alternate paths when access is refused.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import threading
import time
from pathlib import PurePosixPath
from urllib.parse import quote

import requests

from .platforms import PLATFORMS
from .selection import Release, title_matches

log = logging.getLogger(__name__)

SEARCH_URL = "https://archive.org/advancedsearch.php"
METADATA_URL = "https://archive.org/metadata/{identifier}"
DOWNLOAD_URL = "https://archive.org/download/{identifier}/{filename}"
DETAILS_URL = "https://archive.org/details/{identifier}"
BUNDLE_PREFIX = "romarr-ia://"

MAX_ITEMS = 8
MAX_FILES = 64
MAX_FILE_BYTES = 128 * 1024 * 1024 * 1024
MAX_BUNDLE_BYTES = 64 * 1024 * 1024 * 1024
_CACHE_TTL = 300
_METADATA_TTL = 900

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}\Z")
_ARCHIVE_EXTENSIONS = {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"}
_DISC_MANIFEST_EXTENSIONS = {".cue", ".gdi", ".ccd", ".mds", ".m3u"}
_DISC_COMPANION_EXTENSIONS = {".bin", ".img", ".iso", ".raw", ".sub", ".mdf"}
_DISC_RELATED_EXTENSIONS = (_DISC_MANIFEST_EXTENSIONS | _DISC_COMPANION_EXTENSIONS
                            | {".chd", ".pbp"})
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _platform_values():
    if isinstance(PLATFORMS, dict):
        return tuple(PLATFORMS.values())
    return tuple(PLATFORMS)


def _normal(value: object) -> str:
    return re.sub(r"[^\w]+", " ", str(value or "").lower()).strip()


def _extensions(platform) -> set[str]:
    out = set()
    for extension in getattr(platform, "extensions", ()):
        value = str(extension).lower()
        if not value.startswith("."):
            value = "." + value
        out.add(value)
    return out


def _platform_for_term(term: str):
    """Find a platform alias only when it appears at the end of a query."""
    normalized = _normal(term)
    found = []
    for platform in _platform_values():
        aliases = (getattr(platform, "name", ""), getattr(platform, "slug", ""),
                   *getattr(platform, "aliases", ()))
        for alias in aliases:
            marker = _normal(alias)
            if marker and (normalized == marker or normalized.endswith(" " + marker)):
                found.append((len(marker), platform, str(alias)))
    if not found:
        return None, str(term or "").strip()
    _, platform, alias = max(found, key=lambda row: row[0])
    pattern = r"(?i)\s+" + re.escape(alias) + r"\s*$"
    game = re.sub(pattern, "", str(term or "")).strip()
    return platform, game or str(term or "").strip()


def _safe_identifier(value: object) -> str:
    identifier = str(value or "").strip()
    if not _IDENTIFIER.fullmatch(identifier):
        raise ValueError("invalid Internet Archive identifier")
    return identifier


def safe_relative_name(value: object) -> str:
    """Return a safe Archive.org path relative to one item, or raise."""
    name = str(value or "")
    if not name or len(name) > 500 or _CONTROL.search(name) or "\\" in name:
        raise ValueError("invalid Internet Archive filename")
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise ValueError("absolute Internet Archive filename")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("unsafe Internet Archive filename")
    return str(PurePosixPath(*parts))


def encode_bundle_url(identifier: str, files: list[dict]) -> str:
    """Encode a validated multi-file item as a private Direct HTTP job URL."""
    identifier = _safe_identifier(identifier)
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("invalid Internet Archive file set")
    members = []
    total = 0
    seen = set()
    for row in files:
        if not isinstance(row, dict):
            raise ValueError("invalid Internet Archive file entry")
        name = safe_relative_name(row.get("name"))
        size = max(0, int(row.get("size") or 0))
        if name in seen:
            raise ValueError("duplicate Internet Archive filename")
        seen.add(name)
        total += size
        members.append({"name": name, "size": size})
    if total > MAX_BUNDLE_BYTES:
        raise ValueError("Internet Archive file set is too large")
    payload = json.dumps(
        {"identifier": identifier, "files": members},
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return BUNDLE_PREFIX + encoded


def decode_bundle_url(value: str) -> dict:
    """Decode and validate an internal bundle URL before it reaches disk."""
    url = str(value or "")
    if not url.startswith(BUNDLE_PREFIX) or len(url) > 100_000:
        raise ValueError("invalid Internet Archive bundle URL")
    encoded = url[len(BUNDLE_PREFIX):]
    try:
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ValueError("invalid Internet Archive bundle data") from err
    if not isinstance(body, dict):
        raise ValueError("invalid Internet Archive bundle data")
    identifier = _safe_identifier(body.get("identifier"))
    files = body.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("invalid Internet Archive file set")
    members = []
    total = 0
    seen = set()
    for row in files:
        if not isinstance(row, dict):
            raise ValueError("invalid Internet Archive file entry")
        name = safe_relative_name(row.get("name"))
        try:
            size = int(row.get("size") or 0)
        except (TypeError, ValueError) as err:
            raise ValueError("invalid Internet Archive file size") from err
        if size < 0:
            raise ValueError("invalid Internet Archive file size")
        if name in seen:
            raise ValueError("duplicate Internet Archive filename")
        seen.add(name)
        total += size
        members.append({"name": name, "size": size})
    if total > MAX_BUNDLE_BYTES:
        raise ValueError("Internet Archive file set is too large")
    return {"identifier": identifier, "files": members}


def archive_download_url(identifier: str, filename: str) -> str:
    identifier = _safe_identifier(identifier)
    name = safe_relative_name(filename)
    return DOWNLOAD_URL.format(
        identifier=quote(identifier, safe=""),
        filename=quote(name, safe="/"),
    )


def is_bundle_url(value: str) -> bool:
    return str(value or "").startswith(BUNDLE_PREFIX)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple)):
        return any(_truthy(item) for item in value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _metadata_values(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item is not None]
    if value is None:
        return []
    return [str(value)]


def _restricted(metadata: dict) -> bool:
    # Archive.org exposes restrictions inconsistently across older items.
    # Only explicit restrictions are refused here; a later HTTP 403 remains a
    # refusal and is handled by the existing Direct HTTP downloader.
    for field in ("is_dark", "nodownload", "access-restricted-item", "private"):
        if _truthy(metadata.get(field)):
            return True
    return False


def _safe_file(row: object) -> dict | None:
    if not isinstance(row, dict):
        return None
    try:
        name = safe_relative_name(row.get("name"))
        size = int(row.get("size") or 0)
    except (TypeError, ValueError):
        return None
    if size <= 0 or size > MAX_FILE_BYTES or _truthy(row.get("private")):
        return None
    ext = PurePosixPath(name).suffix.lower()
    return {"name": name, "size": size, "ext": ext}


def _stem(name: str) -> str:
    return _normal(PurePosixPath(name).stem)


def _same_disc_group(primary: str, other: str) -> bool:
    left, right = _stem(primary), _stem(other)
    if not left or not right:
        return False
    return left == right or left.startswith(right + " ") or right.startswith(left + " ")


def _disc_members(files: list[dict], primary: dict, *, item_matches: bool) -> list[dict]:
    """Keep a cue/gdi/playlist and the image files it needs as one import."""
    candidates = [row for row in files
                  if row["ext"] in _DISC_RELATED_EXTENSIONS]
    selected = [primary]
    for row in candidates:
        if row["name"] != primary["name"] and _same_disc_group(primary["name"], row["name"]):
            selected.append(row)

    # Many Archive.org items are one game per item and use track names such as
    # "Track 01.bin". In that case the item title supplies the grouping. If the
    # item itself is a collection, stay with files that share the game's stem.
    if len(selected) < 2 and item_matches and len(candidates) <= 32:
        selected = list(candidates)
    if len(selected) < 2:
        return []
    selected = sorted({row["name"]: row for row in selected}.values(),
                      key=lambda row: row["name"].lower())
    if len(selected) > MAX_FILES or sum(row["size"] for row in selected) > MAX_BUNDLE_BYTES:
        return []
    return selected


def _platform_from_metadata(file_ext: str, metadata: dict):
    platforms = _platform_values()
    by_extension = [p for p in platforms if file_ext in _extensions(p)]
    if len(by_extension) == 1:
        return by_extension[0]

    # IA subjects are often a string, but older records return a repeated list.
    description = " ".join(
        part
        for key in ("title", "subject", "collection")
        for part in _metadata_values(metadata.get(key))
    )
    normalized = " " + _normal(description) + " "
    matches = []
    for platform in platforms:
        aliases = (getattr(platform, "name", ""), getattr(platform, "slug", ""),
                   *getattr(platform, "aliases", ()))
        for alias in aliases:
            marker = _normal(alias)
            if marker and (" " + marker + " ") in normalized:
                matches.append((len(marker), platform))
    if matches:
        return max(matches, key=lambda row: row[0])[1]
    return None


def _lucene_escape(value: str) -> str:
    return re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r"\\\1", value)


class InternetArchiveIndexer:
    """A metadata-search indexer whose releases use ROMarr's Direct HTTP lane."""

    protocol = "direct"

    def __init__(self, name: str = "Internet Archive",
                 session: requests.Session | None = None, timeout: int = 12):
        self.name = str(name or "Internet Archive")
        self._session = session or requests.Session()
        self._timeout = max(3, int(timeout))
        self._lock = threading.Lock()
        self._search_cache: dict[str, tuple[float, list[dict]]] = {}
        self._metadata_cache: dict[str, tuple[float, dict]] = {}

    def _get_json(self, url: str, *, params: dict | None = None) -> dict:
        response = self._session.get(
            url, params=params, timeout=self._timeout,
            headers={"User-Agent": "ROMarrNG Internet Archive indexer"},
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Internet Archive returned an invalid response")
        return body

    def caps(self) -> bool:
        """A quick read-only check of the public search API."""
        body = self._get_json(SEARCH_URL, params={
            "q": "mediatype:software",
            "fl[]": ["identifier"],
            "rows": 1,
            "page": 1,
            "output": "json",
        })
        response = body.get("response")
        if not isinstance(response, dict) or "numFound" not in response:
            raise ValueError("Internet Archive search returned no result count")
        return True

    def _search_items(self, game: str) -> list[dict]:
        key = _normal(game)
        now = time.monotonic()
        with self._lock:
            cached = self._search_cache.get(key)
            if cached and now - cached[0] < _CACHE_TTL:
                return list(cached[1])

        query = f'mediatype:software AND "{_lucene_escape(game)}"'
        body = self._get_json(SEARCH_URL, params={
            "q": query,
            "fl[]": ["identifier", "title", "description", "subject", "collection", "mediatype"],
            "rows": MAX_ITEMS,
            "page": 1,
            "output": "json",
        })
        response = body.get("response")
        docs = response.get("docs") if isinstance(response, dict) else None
        items = [row for row in docs if isinstance(row, dict)] if isinstance(docs, list) else []
        with self._lock:
            self._search_cache[key] = (now, items)
            while len(self._search_cache) > 128:
                self._search_cache.pop(next(iter(self._search_cache)))
        return items

    def _item_metadata(self, identifier: str) -> dict:
        now = time.monotonic()
        with self._lock:
            cached = self._metadata_cache.get(identifier)
            if cached and now - cached[0] < _METADATA_TTL:
                return cached[1]

        body = self._get_json(METADATA_URL.format(identifier=quote(identifier, safe="")))
        metadata = body.get("metadata")
        files = body.get("files")
        if not isinstance(metadata, dict) or not isinstance(files, list):
            raise ValueError("Internet Archive item has no usable metadata")
        item = {"metadata": metadata, "files": files}
        with self._lock:
            self._metadata_cache[identifier] = (now, item)
            while len(self._metadata_cache) > 256:
                self._metadata_cache.pop(next(iter(self._metadata_cache)))
        return item

    def search(self, term: str, *, limit: int = 100) -> list[Release]:
        platform, game = _platform_for_term(str(term or "").strip())
        if not game:
            return []
        try:
            items = self._search_items(game)
        except (requests.RequestException, ValueError) as err:
            log.warning("Internet Archive search failed: %s", err.__class__.__name__)
            raise

        releases = []
        seen = set()
        for doc in items:
            identifier = str(doc.get("identifier") or "").strip()
            if not _IDENTIFIER.fullmatch(identifier):
                continue
            try:
                item = self._item_metadata(identifier)
            except (requests.RequestException, ValueError) as err:
                log.info("Internet Archive item metadata unavailable for %s: %s",
                         identifier, err.__class__.__name__)
                continue
            metadata = item["metadata"]
            if _restricted(metadata):
                continue
            item_title = str(metadata.get("title") or doc.get("title") or identifier).strip()
            item_matches = title_matches(item_title, game)
            raw_files = [_safe_file(row) for row in item["files"]]
            files = [row for row in raw_files if row is not None]
            allowed_extensions = set().union(*(_extensions(p) for p in _platform_values()))
            allowed_extensions |= _ARCHIVE_EXTENSIONS | _DISC_MANIFEST_EXTENSIONS \
                | _DISC_COMPANION_EXTENSIONS
            disc_member_names = set()
            for candidate in files:
                if candidate["ext"] in _DISC_MANIFEST_EXTENSIONS:
                    disc_member_names.update(
                        row["name"] for row in _disc_members(
                            files, candidate, item_matches=item_matches))
            for file in files:
                ext = file["ext"]
                if file["name"] in disc_member_names and ext not in _DISC_MANIFEST_EXTENSIONS:
                    continue
                if ext not in allowed_extensions:
                    continue
                if platform is not None and ext not in _ARCHIVE_EXTENSIONS \
                        and ext not in _extensions(platform):
                    # Manifest and companion files are admitted below when they
                    # belong to a disc set for this platform.
                    if ext not in _DISC_MANIFEST_EXTENSIONS \
                            and ext not in _DISC_COMPANION_EXTENSIONS:
                        continue
                    if not getattr(platform, "is_disc", False):
                        continue

                filename_matches = title_matches(PurePosixPath(file["name"]).name, game)
                if not item_matches and not filename_matches:
                    continue

                download_url = ""
                members = []
                if file["ext"] in _DISC_MANIFEST_EXTENSIONS:
                    members = _disc_members(files, file, item_matches=item_matches)
                if members:
                    try:
                        download_url = encode_bundle_url(identifier, members)
                    except ValueError:
                        continue
                else:
                    # A cue sheet or playlist without its referenced data files
                    # cannot be imported, so do not offer it as a stand-alone ROM.
                    if file["ext"] in _DISC_MANIFEST_EXTENSIONS:
                        continue
                    try:
                        download_url = archive_download_url(identifier, file["name"])
                    except ValueError:
                        continue

                title = (file["name"] if filename_matches
                         else f"{item_title} - {PurePosixPath(file['name']).name}")
                release_platform = _platform_from_metadata(file["ext"], metadata)
                if (platform is not None and file["ext"] in _extensions(platform)):
                    release_platform = platform
                release_size = sum(member["size"] for member in members) if members else file["size"]
                release = Release(
                    title=title,
                    size=release_size,
                    seeders=0,
                    categories=(1000,),
                    download_url=download_url,
                    protocol="direct",
                    indexer=self.name,
                    info_url=DETAILS_URL.format(
                        identifier=quote(identifier, safe="")),
                    platform_slug=str(getattr(release_platform, "slug", "") or ""),
                )
                if download_url in seen:
                    continue
                seen.add(download_url)
                releases.append(release)
                if len(releases) >= max(1, int(limit)):
                    return releases
        return releases
