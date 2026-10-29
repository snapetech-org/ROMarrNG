"""Safe local-library identification, metadata caching and explicit organization.

The ROM tree remains the source of truth for game files. A separately mounted
metadata root holds one consolidated catalog per platform plus deduplicated
artwork. Scanning is read-only; file changes require a previewed plan and an
explicit apply, and every applied move is journaled for a checked undo.
"""
from __future__ import annotations

import hashlib
import errno
import hmac
import json
import logging
import os
import re
import shlex
import stat
import shutil
import secrets
import tempfile
import threading
import unicodedata
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from xml.dom import minidom
from xml.parsers import expat

import requests

from .dat import UNKNOWN, VERIFIED, header_size
from .frontends import esde_folder, romarr_game_document
from .metadata import clean_title
from .platforms import PLATFORMS, resolve
from .titled import base_tid_of, validate_switch_rom

log = logging.getLogger(__name__)

MAX_SCAN_FILES = 50_000
MAX_DIRECTORY_FILES = 10_000
MAX_CATALOG_BYTES = 128 * 1024 * 1024
MAX_ART_BYTES = 15 * 1024 * 1024
MAX_PROVIDER_LOOKUPS_PER_SCAN = 200
MAX_GAMELIST_BYTES = 32 * 1024 * 1024
MAX_GAMELIST_GAMES = 100_000
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_MANIFEST_ENTRIES = 256
MAX_PLATFORM_FOLDER_MAPPINGS = 256
RENAME_PLAN_BATCH_SIZE = 200
MAX_RENAME_PLAN_BATCH = 500
ART_HOSTS = frozenset({"images.igdb.com", "media.rawg.io"})
ARCHIVE_EXTENSIONS = frozenset({".zip", ".7z", ".rar"})
_SWITCH_ID = re.compile(r"(?<![0-9a-f])([0-9a-f]{16})(?![0-9a-f])", re.I)
_SWITCH_VERSION = re.compile(r"(?:^|[\s._-])\[?v(\d+)\]?(?=$|[\s._-])", re.I)
_DISC_SUFFIX = re.compile(
    r"(?i)(?:[\s._-]*[\(\[]?\s*(?:disc|disk|cd)\s*0*(\d+)\s*[\)\]]?)"
    r"(?:[\s._-]+(?:\([^)]*\)|\[[^]]*\]))*\s*$")
_DISC_EXTENSIONS = frozenset({".cue", ".gdi", ".chd", ".iso", ".m3u", ".ccd", ".toc"})
_WINDOWS_RESERVED = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.I)
_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_file_hash(path: Path) -> tuple[dict, str]:
    """Hash one regular file in bounded memory, refusing symlinks and races."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    if path.is_symlink():
        raise ValueError("symlinks are not ROM files")
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("not a regular file")
        skip = header_size(path.suffix, before.st_size)
        crc = 0
        md5 = hashlib.md5(usedforsecurity=False)
        sha1 = hashlib.sha1(usedforsecurity=False)
        sha256 = hashlib.sha256()
        content_size = 0
        with os.fdopen(fd, "rb", closefd=False) as handle:
            if skip:
                sha256.update(handle.read(skip))
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                crc = zlib.crc32(block, crc)
                md5.update(block)
                sha1.update(block)
                sha256.update(block)
                content_size += len(block)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("file changed while it was being identified")
        return (
            {"size": content_size, "crc": f"{crc & 0xffffffff:08x}",
             "md5": md5.hexdigest(), "sha1": sha1.hexdigest()},
            sha256.hexdigest(),
        )
    finally:
        os.close(fd)


def _within(root: Path, candidate: Path) -> bool:
    try:
        return candidate.resolve(strict=False).is_relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return False


def _no_symlink_path(root: Path, candidate: Path) -> bool:
    """Reject symlinked descendants, including a pre-existing destination."""
    try:
        base = root.resolve(strict=True)
        rel = candidate.relative_to(root)
        current = base
        for part in rel.parts:
            current = current / part
            if current.is_symlink():
                return False
        return candidate.resolve(strict=False).is_relative_to(base)
    except (OSError, ValueError):
        return False


def _safe_component(value: str) -> str:
    """A portable single filename component; never turns metadata into a path."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = _INVALID_NAME.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    text = text[:180].rstrip(" .")
    while text and len(text.encode("utf-8")) > 180:
        text = text[:-1].rstrip(" .")
    if text in ("", ".", ".."):
        return ""
    if _WINDOWS_RESERVED.match(text):
        text = "_" + text
    return text


def _path_has_symlink(path: Path) -> bool:
    """Reject symlinks in an operator-selected metadata path."""
    normalized = Path(os.path.abspath(str(path)))
    current = Path(normalized.anchor)
    for part in normalized.parts[1:]:
        current = current / part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


def _disc_filename(row: dict) -> tuple[str, int, str] | None:
    """Read conservative Disc/CD numbering from a file name."""
    path = PurePosixPath(str(row.get("relative_path") or ""))
    if path.suffix.lower() not in _DISC_EXTENSIONS:
        return None
    match = _DISC_SUFFIX.search(path.stem)
    if not match:
        return None
    try:
        number = int(match.group(1))
    except ValueError:
        return None
    title = _safe_component(path.stem[:match.start()].strip(" .-_()[]"))
    tags = re.findall(r"[\(\[]([^\)\]]+)", path.stem[match.end(1):])
    variant = re.sub(r"[^a-z0-9]+", "",
                     "".join(sorted(tag.casefold() for tag in tags
                                    if not re.match(r"\s*(?:disc|disk|cd)\b", tag, re.I))))
    return (title, number, variant) if title and 1 <= number <= 99 else None


def _apply_disc_groups(rows: dict[str, dict]) -> set[str]:
    """Group same-folder files with explicit numbered disc labels."""
    changed = set()
    groups: dict[tuple[str, str], list[tuple[int, dict, str]]] = {}
    for identity_id, row in rows.items():
        old = row.pop("disc_group", None)
        if old:
            changed.add(identity_id)
        found = _disc_filename(row)
        if not found:
            continue
        title, number, variant = found
        relative = PurePosixPath(str(row.get("relative_path") or ""))
        parent = relative.parent.as_posix().casefold()
        normalized_title = re.sub(r"[^a-z0-9]+", "", title.casefold())
        key = (parent, normalized_title + ":" + variant)
        groups.setdefault(key, []).append((number, row, title))

    for candidates in groups.values():
        by_number: dict[int, list[tuple[dict, str]]] = {}
        for number, row, title in candidates:
            by_number.setdefault(number, []).append((row, title))
        if len(by_number) < 2:
            continue
        preferred = []
        priority = {".m3u": 0, ".cue": 1, ".gdi": 1, ".ccd": 1,
                    ".toc": 1, ".chd": 2, ".iso": 2}
        for number, options in sorted(by_number.items()):
            options.sort(key=lambda pair: priority.get(
                PurePosixPath(pair[0].get("relative_path", "")).suffix.lower(), 9))
            row, title = options[0]
            preferred.append((number, row, title))
        members = [{
            "identity_id": row.get("identity_id", ""),
            "relative_path": row.get("relative_path", ""),
            "filename": row.get("filename", ""),
            "disc_number": number,
        } for number, row, _ in preferred]
        identities = sorted(str(row.get("identity_id") or "") for _, row, _ in preferred)
        group_id = hashlib.sha256(
            ("\0".join(identities)).encode("utf-8")).hexdigest()[:24]
        mapped_titles = {
            str(row.get("canonical_title") or "")
            for _, row, _ in preferred if row.get("manual_mapping")
        }
        title = (next(iter(mapped_titles)) if len(mapped_titles) == 1
                 and all(row.get("manual_mapping") for _, row, _ in preferred)
                 else preferred[0][2])
        for number, row, _ in preferred:
            identity_id = str(row.get("identity_id") or "")
            row["disc_group"] = {
                "id": group_id, "title": title, "disc_number": number,
                "disc_count": len(preferred), "members": members,
                "match_details": "Grouped from explicit numbered disc filenames; original files stay intact.",
            }
            changed.add(identity_id)
    return changed


def _collapse_disc_groups(rows: list[dict]) -> list[dict]:
    """Present numbered disc files as one reviewable game row."""
    output = []
    grouped: dict[str, dict] = {}
    for original in rows:
        row = dict(original)
        disc = row.get("disc_group")
        group_id = str((disc or {}).get("id") or "")
        if not group_id:
            output.append(row)
            continue
        if group_id not in grouped:
            item = dict(row)
            item["canonical_title"] = str(disc.get("title") or row.get("canonical_title") or "")
            item["title"] = item["canonical_title"]
            item["confidence"] = "multi_disc"
            item["match_details"] = str(disc.get("match_details") or "")
            item["disc_group"] = {
                **disc,
                "members": [dict(member) for member in disc.get("members", [])
                            if isinstance(member, dict)],
            }
            grouped[group_id] = item
            output.append(item)
        item = grouped[group_id]
        is_playlist = str(row.get("relative_path") or "") == str(disc.get("manifest_path") or "")
        existing_members = item["disc_group"]["members"]
        if not is_playlist and not any(
                (member.get("identity_id") and member.get("identity_id") == row.get("identity_id"))
                or (member.get("relative_path") and member.get("relative_path") == row.get("relative_path"))
                for member in existing_members):
            existing_members.append({
                "identity_id": row.get("identity_id", ""),
                "relative_path": row.get("relative_path", ""),
                "filename": row.get("filename", ""),
                "disc_number": (row.get("disc_group") or {}).get("disc_number", 0),
                "confidence": row.get("confidence", ""),
            })
        if not item.get("cover_path") and row.get("cover_path"):
            item["cover_path"] = row["cover_path"]
        metadata = row.get("metadata") or {}
        current = item.get("metadata") or {}
        if metadata.get("summary") and not current.get("summary"):
            item["metadata"] = metadata
    return output


def _apply_manifest_disc_groups(rows: dict[str, dict], root: Path) -> set[str]:
    """Add set-level relationships from bounded, local M3U manifests."""
    changed: set[str] = set()
    by_path = {
        _normalize_catalog_path(str(row.get("relative_path") or "")): row
        for row in rows.values() if row.get("relative_path")
    }
    for identity_id, row in list(rows.items()):
        relative = PurePosixPath(str(row.get("relative_path") or ""))
        manifest = root.joinpath(*relative.parts)
        try:
            platform_root = root / relative.parts[0]
        except IndexError:
            continue
        if manifest.suffix.lower() not in {".m3u", ".cue", ".gdi", ".toc"}:
            continue
        references = _manifest_paths(manifest, root, platform_root)
        if references:
            row["manifests"] = [{"path": relative.as_posix(),
                                 "references": references}]
            changed.add(identity_id)
        elif row.get("manifests"):
            # Do not keep an old playlist relationship after its references
            # have been removed or the manifest becomes unreadable.
            row["manifests"] = []
            changed.add(identity_id)
        if manifest.suffix.lower() != ".m3u" or len(references) < 2:
            continue

        member_rows = []
        members = []
        for number, member_path in enumerate(references, 1):
            member = by_path.get(_normalize_catalog_path(member_path))
            member_identity = str((member or {}).get("identity_id") or "")
            members.append({
                "identity_id": member_identity,
                "relative_path": member_path,
                "filename": PurePosixPath(member_path).name,
                "disc_number": number,
                "confidence": str((member or {}).get("confidence") or ""),
            })
            if member is not None:
                member_rows.append(member)
        group_identity = sorted({identity_id, *[
            str(member.get("identity_id") or "") for member in members
            if member.get("identity_id")
        ]})
        group_id = hashlib.sha256(("\0".join(group_identity) + "\0" +
                                   "\0".join(references)).encode("utf-8")).hexdigest()[:24]
        title = _safe_component(PurePosixPath(row.get("filename") or manifest.name).stem)
        group_rows = [row, *member_rows]
        mapped_titles = {
            str(item.get("canonical_title") or "")
            for item in group_rows if item.get("manual_mapping")
        }
        if (len(mapped_titles) == 1
                and all(item.get("manual_mapping") for item in group_rows)):
            title = next(iter(mapped_titles)) or title
        group = {
            "id": group_id,
            "title": title or str(row.get("canonical_title") or manifest.stem),
            "disc_count": len(references),
            "members": members,
            "manifest_path": relative.as_posix(),
            "manifest_type": "m3u",
            "match_details": "Grouped from a local M3U playlist and its contained disc references; files stay intact.",
        }
        for member_row in group_rows:
            member_row["disc_group"] = dict(group)
            changed.add(str(member_row.get("identity_id") or ""))
    return changed


def _valid_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", str(value or "").lower()))


def _platform_for_path(root: Path, path: Path):
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    if not relative.parts:
        return None
    return resolve(relative.parts[0])


def _layout_member(directory: Path, layout: str) -> Path | None:
    current = directory
    for part in str(layout or "").replace("\\", "/").split("/"):
        if not part or part in (".", ".."):
            return None
        try:
            child = next((p for p in current.iterdir()
                          if p.name.casefold() == part.casefold()
                          and not p.is_symlink()), None)
        except (OSError, ValueError):
            return None
        if child is None:
            return None
        current = child
    return current if current.is_file() else None


def _platform_folder_mappings(value: object) -> dict[str, object]:
    """Keep explicit folder aliases to one safe path component and platform."""
    if not isinstance(value, dict):
        return {}
    output = {}
    for index, (folder, target) in enumerate(value.items()):
        if index >= MAX_PLATFORM_FOLDER_MAPPINGS:
            break
        name = str(folder or "").strip()
        try:
            name_bytes = len(name.encode("utf-8"))
        except UnicodeEncodeError:
            continue
        if (not name or name_bytes > 180 or name != _safe_component(name)
                or name in (".", "..")
                or any(ord(char) < 32 or ord(char) == 127 for char in name)
                or "/" in name or "\\" in name or "\x00" in name):
            continue
        target = str(target or "").strip()
        if len(target) > 120:
            continue
        platform = resolve(target)
        if platform is not None:
            output[os.path.normcase(name).casefold()] = platform
    return output


def _platform_for_folder(value: str, folder_mappings: dict[str, object] | None = None):
    """Resolve a library's platform directory without guessing ambiguous names."""
    folded = os.path.normcase(str(value or "").strip()).casefold()
    explicit = (folder_mappings or {}).get(folded)
    if explicit is not None:
        return explicit
    direct = next((item for item in PLATFORMS if item.slug.casefold() == folded), None)
    if direct is not None:
        return direct
    esde_matches = [item for item in PLATFORMS
                    if os.path.normcase(esde_folder(item.slug)).casefold() == folded]
    if len(esde_matches) == 1:
        return esde_matches[0]
    if esde_matches:
        return None
    return resolve(value)


def _scan_paths(root: Path, metadata_root: Path, only_platform: str = "",
                 folder_mappings: dict[str, object] | None = None):
    """Walk platform-shaped folders without following symlinks or scanning metadata."""
    root_real = root.resolve(strict=True)
    metadata_real = metadata_root.resolve(strict=False)
    platforms = {p.slug: p for p in PLATFORMS}
    seen = 0
    visited = 0
    truncated = False
    for current, dirs, files in os.walk(root_real, followlinks=False):
        directory = Path(current)
        visited += 1
        if visited > MAX_SCAN_FILES:
            truncated = True
            break
        safe_dirs = []
        for name in sorted(dirs):
            child = directory / name
            try:
                resolved = child.resolve(strict=False)
                if (child.is_symlink() or not resolved.is_relative_to(root_real)
                        or resolved == metadata_real
                        or name.startswith(".romarr-") or name == ".git"):
                    continue
            except (OSError, ValueError):
                continue
            safe_dirs.append(name)
        dirs[:] = safe_dirs

        try:
            relative = directory.relative_to(root_real)
        except ValueError:
            dirs[:] = []
            continue
        platform = (_platform_for_folder(relative.parts[0], folder_mappings)
                    if relative.parts else None)
        if platform is None:
            continue
        if only_platform and platform.slug.casefold() != only_platform.casefold():
            continue

        if platform.directory_layout and all(
                _layout_member(directory, part) for part in platform.directory_layout):
            dirs[:] = []
            seen += 1
            yield platform, directory, None
            if seen >= MAX_SCAN_FILES:
                truncated = True
                break
            continue

        allowed = set(platform.extensions) | set(ARCHIVE_EXTENSIONS)
        if str(getattr(platform, "media", "")).casefold() == "disc":
            # Playlists and cue sheets are useful set metadata even on disc
            # platforms whose acquisition extension list omits the sidecar.
            allowed.update((".m3u", ".cue", ".gdi", ".toc"))
        for name in sorted(files):
            if seen >= MAX_SCAN_FILES:
                truncated = True
                break
            path = directory / name
            try:
                if (path.is_symlink() or not path.is_file()
                        or path.suffix.lower() not in allowed
                        or not _within(root_real, path)):
                    continue
            except OSError:
                continue
            seen += 1
            yield platform, path, None
        if seen >= MAX_SCAN_FILES:
            truncated = True
            break
    return truncated


def _identity(path: Path, platform) -> tuple[str, dict, object, list[str]]:
    """Return stable content identity, DAT evidence, and safe relative members."""
    if path.is_file():
        hashes, sha256 = _stable_file_hash(path)
        members = [path.name]
        dat_match = None
        return sha256, hashes, dat_match, members
    files = []
    for current, dirs, names in os.walk(path, followlinks=False):
        d = Path(current)
        if any((d / name).is_symlink() for name in dirs):
            raise ValueError("game folder contains a symlink")
        dirs[:] = sorted(dirs)
        for name in sorted(names):
            member = d / name
            if member.is_symlink():
                raise ValueError("game folder contains a symlink")
            if not member.is_file():
                continue
            files.append(member)
            if len(files) > MAX_DIRECTORY_FILES:
                raise ValueError("game folder contains too many files to identify safely")
    if not files:
        raise ValueError("game folder is empty")
    digest = hashlib.sha256()
    dat_matches = []
    members = []
    for member in sorted(files, key=lambda p: p.relative_to(path).as_posix().casefold()):
        hashes, sha256 = _stable_file_hash(member)
        rel = member.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8", "surrogateescape"))
        digest.update(b"\0")
        digest.update(sha256.encode("ascii"))
        digest.update(b"\n")
        members.append(rel)
        dat_matches.append((hashes, sha256))
    # Directory packages are catalogued as one identity. The DAT field is only
    # populated when every required layout file has an exact match to one game.
    dat_match = None
    return digest.hexdigest(), {}, dat_match, members


def _load_json(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("metadata catalog path is a symlink")
    if not path.exists():
        return {}
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode)
                or before.st_size > MAX_CATALOG_BYTES):
            raise ValueError("metadata catalog is not a bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            payload = handle.read(MAX_CATALOG_BYTES + 1)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("metadata catalog changed while it was read")
        if len(payload) > MAX_CATALOG_BYTES:
            raise ValueError("metadata catalog is too large")
    finally:
        os.close(fd)
    raw = json.loads(payload.decode("utf-8"))
    return raw if isinstance(raw, dict) else {}


def _read_bounded_file(path: Path, max_bytes: int, allowed_roots: tuple[Path, ...]) -> bytes:
    """Read a small regular local file without following links or leaving roots."""
    if path.is_symlink() or _path_has_symlink(path):
        raise ValueError("local metadata path contains a symlink")
    resolved = path.resolve(strict=True)
    if not any(_within(root, resolved) and _no_symlink_path(root, resolved)
               for root in allowed_roots):
        raise ValueError("local metadata path is outside configured roots")
    fd = os.open(resolved, os.O_RDONLY | getattr(os, "O_BINARY", 0)
                 | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
            raise ValueError("local metadata file is not a bounded regular file")
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(64 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("local metadata file exceeds its size limit")
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("local metadata file changed while it was read")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _normalize_catalog_path(value: str) -> str:
    text = str(value or "").replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    return os.path.normcase(PurePosixPath(text).as_posix()).casefold()


def _resolve_manifest_reference(reference: str, manifest: Path,
                                root: Path, platform_root: Path) -> str | None:
    raw = str(reference or "").strip().strip('"').strip()
    if not raw or "\x00" in raw:
        return None
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc:
        return None
    candidate = Path(raw.replace("\\", os.sep))
    if not candidate.is_absolute():
        candidate = manifest.parent / candidate
    try:
        if candidate.is_symlink() or _path_has_symlink(candidate):
            return None
        resolved = candidate.resolve(strict=True)
        if (not resolved.is_file() or not _within(root, resolved)
                or not _within(platform_root, resolved)
                or not _no_symlink_path(root, resolved)):
            return None
        return resolved.relative_to(root.resolve(strict=True)).as_posix()
    except (OSError, ValueError):
        return None


def _manifest_paths(path: Path, root: Path, platform_root: Path) -> list[str]:
    """Extract local media references from common playlist/track manifests."""
    suffix = path.suffix.lower()
    if suffix not in {".m3u", ".cue", ".gdi", ".toc"}:
        return []
    try:
        payload = _read_bounded_file(path, MAX_MANIFEST_BYTES, (root,))
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = payload.decode("cp1252")
    except (OSError, ValueError):
        return []
    references: list[str] = []
    for line in text.splitlines()[:MAX_MANIFEST_ENTRIES * 4]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        names: list[str] = []
        if suffix == ".m3u":
            names = [stripped]
        elif suffix == ".cue":
            match = re.match(r"(?i)^\s*FILE\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))", line)
            if match:
                names = [next(value for value in match.groups() if value)]
        elif suffix == ".gdi":
            try:
                fields = shlex.split(stripped, posix=True)
            except ValueError:
                fields = []
            if len(fields) >= 5 and fields[0].isdigit():
                names = [fields[4]]
        else:  # TOC files commonly use FILE "name" [format]
            match = re.match(r"(?i)^\s*FILE\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))", line)
            if match:
                names = [next(value for value in match.groups() if value)]
        for name in names:
            relative = _resolve_manifest_reference(name, path, root, platform_root)
            if relative and relative not in references:
                references.append(relative)
                if len(references) >= MAX_MANIFEST_ENTRIES:
                    return references
    return references


def _parse_esde_gamelist(payload: bytes) -> ET.Element:
    """Parse ES-DE XML only after rejecting DTDs and entity declarations.

    The Expat preflight recognizes declarations in the document's declared
    encoding (including UTF-16), which a byte-pattern check alone cannot do.
    Rejecting the document type before building a tree prevents entity
    expansion from consuming unbounded resources.
    """
    parser = expat.ParserCreate()

    def reject_declaration(*_args):
        raise ValueError("DTD and entity declarations are not supported")

    parser.StartDoctypeDeclHandler = reject_declaration
    parser.EntityDeclHandler = reject_declaration
    parser.ExternalEntityRefHandler = lambda *_args: 0
    if hasattr(parser, "SetParamEntityParsing"):
        parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.Parse(payload, True)
    return ET.fromstring(payload)


def _atomic_bytes(path: Path, data: bytes, root: Path) -> None:
    if not _within(root, path) or not _no_symlink_path(root, path):
        raise ValueError("metadata output escapes its configured root")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not _no_symlink_path(root, path.parent):
        raise ValueError("metadata output directory contains a symlink")
    fd, tmp = tempfile.mkstemp(prefix=".romarr-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _atomic_json(path: Path, value: dict, root: Path) -> None:
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    _atomic_bytes(path, data, root)


def _journal_payload(journal: dict) -> bytes:
    body = {key: value for key, value in journal.items() if key != "signature"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _move_file_no_replace(source: Path, target: Path, expected_sha256: str) -> None:
    """Move one regular file without ever replacing a destination.

    Hard links make the normal same-filesystem path atomic. A bounded-memory
    copy into a unique sibling temp file is the fallback for filesystems that
    do not support hard links; publishing that temp with link() still has
    exclusive-create semantics.
    """
    if source.is_symlink() or target.exists() or target.is_symlink():
        raise ValueError("source is a symlink or destination already exists")
    source_fd = os.open(
        source, os.O_RDONLY | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0))
    temporary = None
    published_stat = None
    try:
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("only regular files can be moved by this plan")
        try:
            os.link(source, target, follow_symlinks=False)
            published_stat = target.stat(follow_symlinks=False)
            if (not stat.S_ISREG(published_stat.st_mode)
                    or (published_stat.st_dev, published_stat.st_ino)
                    != (before.st_dev, before.st_ino)):
                raise ValueError("published destination does not match the source")
        except OSError as exc:
            if target.exists() or target.is_symlink():
                raise
            unsupported = {
                errno.EXDEV, errno.EPERM, errno.EACCES, errno.EMLINK,
                getattr(errno, "ENOTSUP", errno.EPERM),
                getattr(errno, "EOPNOTSUPP", errno.EPERM),
            }
            if exc.errno not in unsupported:
                raise
        else:
            if _content_identity(target) != expected_sha256:
                raise ValueError("source content changed during the move")
            current = source.stat(follow_symlinks=False)
            if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise ValueError("source changed during the move")
            source.unlink()
            return

        fd, temporary_name = tempfile.mkstemp(
            prefix=".romarr-move-", suffix=".tmp", dir=str(target.parent))
        temporary = Path(temporary_name)
        with os.fdopen(os.dup(source_fd), "rb") as src, os.fdopen(fd, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        os.chmod(temporary, stat.S_IMODE(before.st_mode))
        os.utime(temporary, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = os.fstat(source_fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("source changed while it was copied")
        if _content_identity(temporary) != expected_sha256:
            raise ValueError("copied content changed during the move")
        os.link(temporary, target, follow_symlinks=False)
        published_stat = target.stat(follow_symlinks=False)
        temporary.unlink()
        temporary = None
        if _content_identity(source) != expected_sha256:
            raise ValueError("source content changed during the move")
        current = source.stat(follow_symlinks=False)
        if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
            raise ValueError("source changed during the move")
        source.unlink()
    except Exception:
        if published_stat is not None:
            try:
                current = target.stat(follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (
                        published_stat.st_dev, published_stat.st_ino):
                    target.unlink()
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
        raise
    finally:
        os.close(source_fd)


def _cover_extension(content_type: str, prefix: bytes) -> str:
    kind = content_type.split(";", 1)[0].strip().lower()
    if prefix.startswith(b"\xff\xd8\xff") and kind in ("image/jpeg", "application/octet-stream"):
        return ".jpg"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n") and kind in ("image/png", "application/octet-stream"):
        return ".png"
    if prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP" and kind in ("image/webp", "application/octet-stream"):
        return ".webp"
    return ""


def _download_art(url: str, destination_stem: Path, metadata_root: Path) -> str:
    """Fetch provider art only from known HTTPS hosts, with no redirects or unbounded body."""
    try:
        parsed = urlsplit(str(url or ""))
        if (parsed.scheme != "https" or parsed.hostname not in ART_HOSTS
                or parsed.username or parsed.password or parsed.port not in (None, 443)
                or not parsed.path or parsed.fragment):
            return ""
        response = requests.get(
            str(url), stream=True, timeout=(4, 15), allow_redirects=False,
            headers={"Accept": "image/jpeg,image/png,image/webp",
                     "User-Agent": "ROMarrNG metadata cache"},
        )
        try:
            if response.status_code != 200:
                return ""
            content_type = response.headers.get("Content-Type", "")
            length = response.headers.get("Content-Length")
            if length and (not length.isdigit() or int(length) > MAX_ART_BYTES):
                return ""
            data = bytearray()
            for block in response.iter_content(64 * 1024):
                if not block:
                    continue
                if len(data) + len(block) > MAX_ART_BYTES:
                    return ""
                data.extend(block)
            extension = _cover_extension(content_type, bytes(data[:16]))
            if not extension:
                return ""
            path = destination_stem.with_suffix(extension)
            _atomic_bytes(path, bytes(data), metadata_root)
            return path.relative_to(metadata_root).as_posix()
        finally:
            response.close()
    except Exception as exc:
        log.debug("artwork cache failed (%s)", type(exc).__name__)
        return ""


class LibraryOrganizer:
    """Background local inventory with persisted, shared metadata and safe plans."""

    def __init__(self, service):
        self.service = service
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._status: dict = {
            "state": "idle", "processed": 0, "total": 0, "error": "",
            "started_at": "", "finished_at": "", "platform": "",
            "verified": 0, "catalogued": 0, "suggested": 0, "unmatched": 0,
            "switch_outdated": 0, "truncated": False,
        }

    @property
    def rom_root(self) -> Path:
        return Path(self.service.library)

    @property
    def metadata_root(self) -> Path | None:
        value = str(self.service.store.settings.get("metadata_path") or "").strip()
        return Path(os.path.abspath(str(Path(value).expanduser()))) if value else None

    def _source_root(self, setting: str, metadata_root: Path,
                     default_relative: str) -> Path | None:
        value = str(self.service.store.settings.get(setting) or "").strip()
        candidate = (Path(value).expanduser() if value else
                     metadata_root / default_relative)
        candidate = Path(os.path.abspath(str(candidate)))
        try:
            if candidate.is_symlink() or _path_has_symlink(candidate):
                return None
            return candidate.resolve(strict=True) if candidate.is_dir() else None
        except (OSError, ValueError):
            return None

    def _esde_gamelist_roots(self, metadata_root: Path) -> list[Path]:
        roots = [self._source_root("esde_gamelists_path", metadata_root,
                                   "esde/gamelists"),
                 self._source_root("", metadata_root, "esde/gamelists")]
        return list(dict.fromkeys(path for path in roots if path is not None))

    def _esde_media_roots(self, metadata_root: Path) -> list[Path]:
        roots = [self._source_root("esde_media_path", metadata_root,
                                   "esde/downloaded_media"),
                 self._source_root("", metadata_root,
                                   "esde/downloaded_media")]
        return list(dict.fromkeys(path for path in roots if path is not None))

    def _platform_root_for_path(self, root: Path, slug: str,
                                relative_path: str = "") -> Path:
        nested = str(self.service.store.settings.get("library_layout") or "").lower() in (
            "nested", "romm_b", "b")
        mappings = _platform_folder_mappings(
            self.service.store.settings.get("platform_folder_mappings"))
        parts = PurePosixPath(str(relative_path or "").replace("\\", "/")).parts
        folder = parts[0] if parts else ""
        platform = _platform_for_folder(folder, mappings) if folder else None
        if not platform or platform.slug != slug:
            folder = self._folder_name_for_platform(slug, root, mappings)
        base = root / folder
        return base / "roms" if nested else base

    def _folder_name_for_platform(self, slug: str, root: Path | None = None,
                                  mappings: dict[str, object] | None = None) -> str:
        mappings = mappings or _platform_folder_mappings(
            self.service.store.settings.get("platform_folder_mappings"))
        if root is not None:
            try:
                matches = [child.name for child in root.iterdir()
                           if child.is_dir() and not child.is_symlink()
                           and (_platform_for_folder(child.name, mappings) is not None)
                           and _platform_for_folder(child.name, mappings).slug == slug]
                if len(matches) == 1:
                    return matches[0]
            except OSError:
                pass
        configured_raw = self.service.store.settings.get("platform_folder_mappings")
        configured_raw = configured_raw if isinstance(configured_raw, dict) else {}
        configured = [name for name, target in configured_raw.items()
                      if isinstance(name, str) and _platform_for_folder(name, mappings)
                      and _platform_for_folder(name, mappings).slug == slug]
        if len(configured) == 1:
            return configured[0]
        return slug

    def _catalog_path(self, platform: str) -> Path:
        if not _valid_slug(platform):
            raise ValueError("unknown platform")
        root = self.metadata_root
        if root is None:
            raise ValueError("shared metadata root is not configured")
        return root / platform.lower() / "catalog.json"

    def _read_catalog(self, platform: str) -> dict:
        root = self.metadata_root
        if root is None:
            return {"schema_version": 1, "platform": platform, "games": []}
        if _path_has_symlink(root):
            raise ValueError("shared metadata root contains a symlink")
        if root.exists():
            root_real = root.resolve(strict=True)
            path = root_real / platform.lower() / "catalog.json"
            if not _no_symlink_path(root_real, path):
                raise ValueError("metadata catalog path contains a symlink or escapes its root")
        else:
            path = self._catalog_path(platform)
        raw = _load_json(path)
        if raw.get("schema_version") != 1:
            return {"schema_version": 1, "platform": platform, "games": []}
        if not isinstance(raw.get("games"), list):
            raw["games"] = []
        return raw

    def _write_catalog(self, platform: str, games: list[dict]) -> None:
        metadata_root = self.metadata_root
        if metadata_root is None:
            raise ValueError("shared metadata root is not configured")
        if _path_has_symlink(metadata_root):
            raise ValueError("shared metadata root contains a symlink")
        root = metadata_root.resolve(strict=True)
        path = root / platform.lower() / "catalog.json"
        payload = {
            "schema_version": 1,
            "platform": platform,
            "updated_at": _now(),
            "games": sorted(games, key=lambda row: (
                str(row.get("canonical_title") or row.get("title") or "").casefold(),
                str(row.get("relative_path") or "").casefold(),
            )),
        }
        _atomic_json(path, payload, root)

    def _esde_catalog_paths(self, slug: str, root: Path, metadata_root: Path,
                            platform_root: Path) -> list[tuple[Path, Path]]:
        """Return modern ES-DE catalogs plus safe legacy per-folder catalogs."""
        candidates: list[tuple[Path, Path]] = []
        system = esde_folder(slug)
        # ES-DE 2.x+ stores gamelists beneath its data directory, separately
        # from the ROM folders. Its path entries are relative to ROMDirectory.
        for gamelists_root in self._esde_gamelist_roots(metadata_root):
            candidates.append((gamelists_root / system / "gamelist.xml", root))
        # Older EmulationStation layouts place the file next to each system.
        candidates.extend((path, path.parent) for path in (
            platform_root / "gamelist.xml",
            platform_root.parent / "gamelist.xml",
            platform_root.parent / "roms" / "gamelist.xml",
            metadata_root / slug / "gamelist.xml"))
        allowed_roots = (root, metadata_root, *self._esde_gamelist_roots(metadata_root))
        seen = set()
        output = []
        for candidate, base in candidates:
            key = os.path.normcase(str(candidate.absolute())).casefold()
            if key in seen or candidate.is_symlink() or not candidate.is_file():
                continue
            if not any(_within(allowed, candidate) for allowed in allowed_roots):
                continue
            if _path_has_symlink(candidate):
                continue
            seen.add(key)
            output.append((candidate, base))
        return output

    def _esde_rom_relative(self, value: str, base: Path, root: Path,
                           platform_root: Path) -> str | None:
        raw = str(value or "").strip()
        if not raw or "\x00" in raw:
            return None
        if raw.upper().startswith("%ROMPATH%"):
            raw = raw[len("%ROMPATH%"):].lstrip("/\\")
            base = root
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc:
            return None
        candidate = Path(raw.replace("\\", os.sep))
        candidates = [candidate] if candidate.is_absolute() else [
            base / candidate, root / candidate, platform_root / candidate]
        for possible in candidates:
            try:
                if possible.is_symlink() or _path_has_symlink(possible):
                    continue
                resolved = possible.resolve(strict=True)
                if (not (resolved.is_file() or resolved.is_dir())
                        or not _within(root, resolved)
                        or not _within(platform_root, resolved)
                        or not _no_symlink_path(root, resolved)):
                    continue
                return resolved.relative_to(root.resolve(strict=True)).as_posix()
            except (OSError, ValueError):
                continue
        return None

    def _esde_asset_path(self, value: str, base: Path, root: Path,
                         metadata_root: Path,
                         allowed_roots: tuple[Path, ...] = ()) -> Path | None:
        raw = str(value or "").strip()
        if not raw or "\x00" in raw:
            return None
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc:
            return None  # A local import never fetches an XML-supplied URL.
        source = Path(raw.replace("\\", os.sep))
        roots = allowed_roots or (root, metadata_root)
        candidates = ([source] if source.is_absolute() else
                      [base / source, metadata_root / source,
                       *(allowed / source for allowed in roots)])
        for candidate in candidates:
            try:
                if candidate.is_symlink() or _path_has_symlink(candidate):
                    continue
                resolved = candidate.resolve(strict=True)
                if (not resolved.is_file()
                        or not any(_within(allowed, resolved)
                                   and _no_symlink_path(allowed, resolved)
                                   for allowed in roots)):
                    continue
                return resolved
            except (OSError, ValueError):
                continue
        return None

    def _esde_media_art(self, slug: str, filename: str, is_directory: bool,
                        media_roots: list[Path]) -> Path | None:
        relative = PurePosixPath(str(filename or "").replace("\\", "/"))
        stem = relative if is_directory else relative.with_suffix("")
        system = esde_folder(slug)
        for media_root in media_roots:
            for extension in (".jpg", ".png", ".webp"):
                candidate = media_root / system / "covers" / (str(stem) + extension)
                try:
                    if (candidate.is_symlink() or _path_has_symlink(candidate)
                            or not candidate.is_file()):
                        continue
                    resolved = candidate.resolve(strict=True)
                    if _within(media_root, resolved) and _no_symlink_path(media_root, resolved):
                        return resolved
                except OSError:
                    continue
        return None

    def _read_esde_metadata(self, slug: str, root: Path,
                            metadata_root: Path,
                            platform_root: Path) -> dict[str, dict]:
        """Read existing local ES-DE gamelists as a bounded metadata source."""
        output: dict[str, dict] = {}
        gamelist_roots = self._esde_gamelist_roots(metadata_root)
        media_roots = self._esde_media_roots(metadata_root)
        allowed_roots = (root, metadata_root, *gamelist_roots, *media_roots)
        for gamelist, rom_base in self._esde_catalog_paths(
                slug, root, metadata_root, platform_root):
            try:
                data = _read_bounded_file(gamelist, MAX_GAMELIST_BYTES, allowed_roots)
                document = _parse_esde_gamelist(data)
                if document.tag.rsplit("}", 1)[-1].casefold() != "gamelist":
                    continue
                entries = [node for node in document
                           if node.tag.rsplit("}", 1)[-1].casefold() == "game"]
                if len(entries) > MAX_GAMELIST_GAMES:
                    raise ValueError("ES-DE gamelist contains too many entries")

                def value(node, name: str, limit: int = 8192) -> str:
                    child = next((item for item in node
                                  if item.tag.rsplit("}", 1)[-1].casefold() == name), None)
                    return str(child.text or "").strip()[:limit] if child is not None else ""

                for node in entries:
                    relative = self._esde_rom_relative(value(node, "path", 4096),
                                                       rom_base, root, platform_root)
                    if not relative:
                        continue
                    key = _normalize_catalog_path(relative)
                    name = value(node, "name", 512)
                    summary = value(node, "desc")
                    released_raw = value(node, "releasedate", 64)
                    release_match = re.match(r"^(\d{4})(\d{2})(\d{2})", released_raw)
                    released = ("-".join(release_match.groups())
                                if release_match else released_raw[:10])
                    genre_raw = value(node, "genre", 1024)
                    genres = list(dict.fromkeys(
                        part.strip()[:80] for part in re.split(r"[,;/|]", genre_raw)
                        if part.strip()))[:32]
                    rating_raw = value(node, "rating", 32)
                    try:
                        rating_value = max(0.0, min(1.0, float(rating_raw or 0)))
                    except ValueError:
                        rating_value = 0.0
                    metadata = {}
                    if summary:
                        metadata["summary"] = summary
                    if released:
                        metadata["released"] = released
                    if genres:
                        metadata["genres"] = genres
                    if rating_raw:
                        # ES-DE rating is normalized to 0..1; ROMarr's common
                        # metadata scale is 0..10.
                        metadata["rating"] = round(rating_value * 10.0, 3)
                    image_source = self._esde_asset_path(
                        value(node, "image", 4096), gamelist.parent,
                        root, metadata_root, allowed_roots)
                    if image_source is None:
                        try:
                            frontend_path = _resolve_relative(root, relative).relative_to(
                                platform_root).as_posix()
                        except (OSError, ValueError):
                            frontend_path = ""
                        image_source = self._esde_media_art(
                            slug, frontend_path,
                            _resolve_relative(root, relative).is_dir(), media_roots)
                    if metadata or image_source:
                        metadata.update({
                            "source": "ES-DE local",
                            "provider_id": "",
                            "matched_by": "existing_gamelist_path",
                        })
                    entry = {
                        "title": name,
                        "metadata": metadata,
                        "image_source": image_source,
                        "source_path": str(gamelist),
                    }
                    # If duplicate gamelists describe one ROM, keep the entry
                    # with more user-curated fields instead of last-writer wins.
                    previous = output.get(key)
                    quality = (len(metadata), bool(name), bool(entry["image_source"]))
                    old_quality = ((len(previous.get("metadata") or {}),
                                    bool(previous.get("title")),
                                    bool(previous.get("image_source")))
                                   if previous else (-1, False, False))
                    if quality > old_quality:
                        output[key] = entry
            except (OSError, ValueError, ET.ParseError, expat.ExpatError,
                    RecursionError) as exc:
                log.info("skipping local ES-DE metadata %s (%s)",
                         gamelist.name, type(exc).__name__)
        return output

    def _cache_local_artwork(self, source: Path | None, slug: str,
                             metadata_root: Path,
                             allowed_roots: tuple[Path, ...] = ()) -> str:
        if source is None:
            return ""
        try:
            roots = allowed_roots or (
                self.rom_root.expanduser().resolve(strict=True),
                metadata_root.resolve(strict=True))
            data = _read_bounded_file(source, MAX_ART_BYTES, roots)
            extension = _cover_extension("application/octet-stream", data[:16])
            if not extension:
                return ""
            digest = _sha256_bytes(data)
            destination = metadata_root / slug / "artwork" / f"{digest}{extension}"
            root = metadata_root.resolve(strict=True)
            if not destination.is_file():
                _atomic_bytes(destination, data, root)
            return destination.relative_to(root).as_posix()
        except (OSError, ValueError):
            return ""

    def _journal_key(self) -> bytes:
        """Use a private local key to authenticate shared undo state."""
        store = self.service.store
        with store._lock:
            value = store.settings.get("_organizer_journal_key")
            if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
                value = secrets.token_hex(32)
                store.settings["_organizer_journal_key"] = value
                store.save()
        return bytes.fromhex(value)

    def _save_journal(self, path: Path, journal: dict, root: Path) -> None:
        journal.pop("signature", None)
        journal["signature"] = hmac.new(
            self._journal_key(), _journal_payload(journal), hashlib.sha256
        ).hexdigest()
        _atomic_json(path, journal, root)

    def _verify_journal(self, journal: dict) -> None:
        signature = journal.get("signature")
        if not isinstance(signature, str) or not re.fullmatch(r"[a-f0-9]{64}", signature):
            raise ValueError("Rename history is unsigned or damaged; refusing to move files.")
        expected = hmac.new(
            self._journal_key(), _journal_payload(journal), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Rename history signature is invalid; refusing to move files.")

    def _write_sidecar(self, record: dict, previous_path: str = "") -> str:
        """Write one portable per-game metadata file alongside the catalog."""
        metadata_root = self.metadata_root
        if metadata_root is None:
            raise ValueError("shared metadata root is not configured")
        if _path_has_symlink(metadata_root):
            raise ValueError("shared metadata root contains a symlink")
        root = metadata_root.resolve(strict=True)
        identity_id = str(record.get("identity_id") or "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}:[a-f0-9]{64}", identity_id):
            raise ValueError("invalid game identity for metadata sidecar")
        slug, digest = identity_id.split(":", 1)
        if resolve(slug) is None or resolve(slug).slug != slug:
            raise ValueError("unknown platform for metadata sidecar")
        title = _safe_component(record.get("canonical_title") or
                                 record.get("filename") or "Unknown game")
        directory = f"{title or 'Unknown game'}--{digest[:12]}"
        path = root / slug / directory / "metadata.json"
        relative = path.relative_to(root).as_posix()
        record["metadata_sidecar"] = relative
        payload = romarr_game_document(record)
        # Preserve the original flat keys for sidecar readers from the first
        # release of this feature while publishing the documented contract.
        payload.update({
            "sidecar_path": relative,
            "platform": slug,
            "title": str(record.get("canonical_title") or record.get("title") or ""),
            "relative_path": str(record.get("relative_path") or ""),
            "confidence": str(record.get("confidence") or ""),
            "match_details": str(record.get("match_details") or ""),
            "dat": str(record.get("dat") or ""),
            "dat_status": str(record.get("dat_status") or UNKNOWN),
            "switch": record.get("switch") or {},
            "disc_group": record.get("disc_group") or {},
            "artwork_path": str(record.get("cover_path") or ""),
        })
        _atomic_json(path, payload, root)
        if previous_path and previous_path != relative:
            try:
                old = _resolve_relative(root, previous_path)
                old_data = _load_json(old)
                if old_data.get("identity_id") == identity_id:
                    old.unlink()
                    try:
                        old.parent.rmdir()
                    except OSError:
                        pass
            except (OSError, ValueError):
                pass
        return relative

    def status(self) -> dict:
        with self._lock:
            return dict(self._status)

    def start_scan(self, *, platform: str = "", force: bool = False) -> dict:
        root = self.rom_root.expanduser()
        metadata_root = self.metadata_root
        if metadata_root is None:
            raise ValueError("Set a shared metadata root under Settings → Media Management first.")
        if _path_has_symlink(metadata_root):
            raise ValueError("Shared metadata root contains a symlink.")
        if not root.is_dir():
            raise ValueError(f"ROM root is not available: {root}")
        root_real = root.resolve(strict=True)
        metadata_real = metadata_root.resolve(strict=False)
        if metadata_real == root_real or metadata_real.is_relative_to(root_real):
            raise ValueError("Choose a shared metadata folder outside the ROM library root.")
        metadata_root.mkdir(parents=True, exist_ok=True)
        if _path_has_symlink(metadata_root) or not metadata_root.is_dir():
            raise ValueError("Shared metadata root is not a directory.")
        selected = str(platform or "").strip().lower()
        if selected and resolve(selected) is None:
            raise ValueError("Select a supported platform or All platforms.")
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {**self._status, "already_running": True}
            self._status = {
                "state": "scanning", "processed": 0, "total": 0, "error": "",
                "started_at": _now(), "finished_at": "", "platform": selected,
                "verified": 0, "catalogued": 0, "suggested": 0, "unmatched": 0,
                "switch_outdated": 0, "local_metadata_imported": 0,
                "truncated": False, "force": bool(force),
            }
            self._thread = threading.Thread(
                target=self._scan, args=(selected, bool(force)),
                name="romarr-library-scan", daemon=True)
            self._thread.start()
            return dict(self._status)

    def _scan(self, selected: str, force: bool) -> None:
        root = self.rom_root.expanduser()
        meta_root = self.metadata_root
        if meta_root is None:
            with self._lock:
                self._status.update(state="failed", finished_at=_now(),
                                    error="Shared metadata root was removed.")
            return
        totals = {"verified": 0, "catalogued": 0, "suggested": 0,
                  "unmatched": 0, "switch_outdated": 0,
                  "local_metadata_imported": 0}
        by_platform: dict[str, dict[str, dict]] = {}
        errors = []
        truncated = False
        provider_lookups = 0
        seen_identities: dict[str, set[str]] = {}
        failed_paths: dict[str, set[str]] = {}
        esde_by_platform: dict[tuple[str, str], dict[str, dict]] = {}
        try:
            root = root.resolve(strict=True)
            meta_root = meta_root.resolve(strict=True)
            local_art_roots = (root, meta_root,
                               *self._esde_media_roots(meta_root),
                               *self._esde_gamelist_roots(meta_root))
            paths = []
            folder_mappings = _platform_folder_mappings(
                self.service.store.settings.get("platform_folder_mappings"))
            for platform, path, _ in _scan_paths(root, meta_root, selected,
                                                  folder_mappings):
                paths.append((platform, path))
                if len(paths) >= MAX_SCAN_FILES:
                    truncated = True
                    break
            if not selected and not paths:
                pass
            with self._lock:
                self._status["total"] = len(paths)
                self._status["truncated"] = truncated
            existing: dict[str, dict[str, dict]] = {}
            for platform, path in paths:
                slug = platform.slug
                if slug not in existing:
                    catalog = self._read_catalog(slug)
                    existing[slug] = {
                        str(row.get("identity_id")): dict(row)
                        for row in catalog.get("games", [])
                        if isinstance(row, dict) and row.get("identity_id")
                    }
                    by_platform[slug] = dict(existing[slug])

                relative = path.relative_to(root).as_posix()
                platform_root = self._platform_root_for_path(root, slug, relative)
                local_key = (slug, str(platform_root))
                if local_key not in esde_by_platform:
                    esde_by_platform[local_key] = self._read_esde_metadata(
                        slug, root, meta_root, platform_root)
                try:
                    identity_hash, hashes, _, members = _identity(path, platform)
                    identity_id = f"{slug}:{identity_hash}"
                    cached = existing[slug].get(identity_id, {})
                    local = esde_by_platform[local_key].get(
                        _normalize_catalog_path(relative), {})
                    is_directory = path.is_dir()

                    dat_match = None
                    try:
                        if not is_directory and self.service.dats:
                            dat_match = self.service.dats.lookup(**hashes)
                    except Exception:
                        dat_match = None

                    if dat_match is None:
                        from .dat import Match
                        dat_match = Match(UNKNOWN)
                    switch_title = ""
                    switch = {}
                    if slug == "switch" and not is_directory:
                        try:
                            result = validate_switch_rom(
                                path.name, index=self.service.ensure_titled())
                            title_obj = result.get("title")
                            tid = _SWITCH_ID.search(path.name)
                            status = str(result.get("status") or "unknown")
                            if tid or title_obj or status == "matched_by_name":
                                title_id = str((getattr(title_obj, "title_id", "")
                                                or (tid.group(1) if tid else "")))
                                switch_kind = str(result.get("kind") or
                                                  getattr(title_obj, "kind", "") or "")
                                base_title_id = base_tid_of(title_id) if title_id else ""
                                title_index = self.service.ensure_titled()
                                base_title_obj = (title_index.lookup_by_id(base_title_id)
                                                  if base_title_id else None)
                                switch_title = str(
                                    getattr(title_obj, "name", "")
                                    or getattr(base_title_obj, "name", "") or "")
                                file_version_match = _SWITCH_VERSION.search(path.stem)
                                file_version = int(file_version_match.group(1)) if file_version_match else None
                                latest = int(result.get("latest_version") or 0)
                                version_state = (
                                    "unlabelled" if switch_kind == "update" and latest > 0
                                    else "not-applicable" if switch_kind in ("base", "dlc")
                                    else "unknown")
                                if (file_version is not None and latest > 0
                                        and switch_kind == "update"):
                                    version_state = ("outdated" if file_version < latest else
                                                     "future" if file_version > latest else "current")
                                switch = {
                                    "title_id": title_id,
                                    "base_title_id": base_title_id,
                                    "base_title": str(getattr(base_title_obj, "name", "") or ""),
                                    "kind": switch_kind,
                                    "catalog_status": status,
                                    "matched_by_name": status == "matched_by_name",
                                    "file_version": file_version,
                                    "latest_version": latest,
                                    "version_status": version_state,
                                    "details": str(result.get("details") or ""),
                                    "bytes_verified": False,
                                }
                                if file_version is not None and version_state == "outdated":
                                    totals["switch_outdated"] += 1
                                if status == "matched_by_name":
                                    confidence = "ambiguous_name"
                                elif status == "verified":
                                    confidence = "title_id_catalog"
                        except Exception as exc:
                            log.debug("Switch catalogue lookup failed (%s)", type(exc).__name__)

                    manual = bool(cached.get("manual_mapping"))
                    info = {}
                    cached_metadata = dict(cached.get("metadata") or {})
                    local_metadata = dict(local.get("metadata") or {})
                    local_title = str(local.get("title") or "")
                    local_has_details = bool(
                        local_metadata.get("summary") or local_metadata.get("released")
                        or local_metadata.get("genres") or local_metadata.get("rating")
                        or local.get("image_source"))
                    metadata = {**cached_metadata, **local_metadata}
                    local_cover = self._cache_local_artwork(
                        local.get("image_source"), slug, meta_root,
                        local_art_roots)
                    if local_title or local_has_details:
                        totals["local_metadata_imported"] += 1
                    lookup_attempted = bool(cached.get("lookup_attempted")) and not force
                    lookup_deferred = False
                    if manual:
                        confidence = "manual"
                        title = str(cached.get("canonical_title") or cached.get("title") or "")
                    elif local_has_details and not force:
                        # Existing ES-DE data is already the result of a user
                        # or scraper pass. Reuse it without making another
                        # provider request; manual confirmation is still
                        # required before a filename can be changed.
                        confidence = "local_metadata"
                        title = (local_title or str(cached.get("canonical_title") or "")
                                 or switch_title or clean_title(path.name))
                        lookup_attempted = True
                    elif lookup_attempted:
                        confidence = str(cached.get("confidence") or "filename_only")
                        title = str(cached.get("canonical_title") or "")
                    else:
                        lookup_deferred = provider_lookups >= MAX_PROVIDER_LOOKUPS_PER_SCAN
                        if not lookup_deferred:
                            verification = dat_match if dat_match.status == VERIFIED else None
                            lookup_name = switch_title or path.name
                            info_obj = self.service.metadata.identify(
                                verification=verification, filename=lookup_name)
                            provider_lookups += 1
                            info = {
                                "title": str(info_obj.title or ""),
                                "summary": str(info_obj.summary or ""),
                                "released": str(info_obj.released or ""),
                                "rating": float(info_obj.rating or 0.0),
                                "genres": list(info_obj.genres or ()),
                                "source": str(info_obj.source or ""),
                                "provider_id": str(getattr(info_obj, "provider_id", "") or ""),
                                "matched_by": str(info_obj.matched_by or ""),
                                "cover_url": str(info_obj.cover_url or ""),
                            }
                            metadata = {**info, **cached_metadata, **local_metadata}
                        if dat_match.status == VERIFIED and dat_match.game:
                            confidence = "dat_verified"
                            title = str(dat_match.game)
                        elif switch.get("title_id"):
                            if switch.get("matched_by_name"):
                                confidence = "ambiguous_name"
                            elif switch.get("catalog_status") == "verified":
                                confidence = "title_id_catalog"
                            elif info.get("title"):
                                confidence = "provider_suggestion"
                            else:
                                confidence = "filename_only"
                            title = switch_title or clean_title(path.name)
                        elif info.get("title"):
                            confidence = "provider_suggestion"
                            title = info["title"]
                        else:
                            confidence = "filename_only"
                            title = clean_title(path.name)
                        if lookup_deferred:
                            # Continue provider lookups on later bounded scans
                            # instead of repeatedly querying the first 200.
                            info = {}
                            metadata = {**cached_metadata, **local_metadata}

                    if not manual and dat_match.status == VERIFIED and dat_match.game:
                        confidence = "dat_verified"
                        title = str(dat_match.game)
                    elif not manual and local_title:
                        confidence = "local_metadata"
                        title = local_title
                    elif not manual and switch.get("matched_by_name"):
                        title = switch_title or title or clean_title(path.name)
                        confidence = "ambiguous_name"
                    elif (not manual
                          and switch.get("catalog_status") == "verified"):
                        title = switch_title or title or clean_title(path.name)
                        confidence = "title_id_catalog"

                    previous_cover = str(cached.get("cover_path") or "")
                    cover_path = local_cover or previous_cover
                    cover_url = str(
                        (info.get("cover_url") if isinstance(info, dict) else "")
                        or metadata.get("cover_url") or "")
                    if not manual and not local_cover and cover_url and (force or not previous_cover
                            or not (meta_root / previous_cover).is_file()):
                        art_dir = meta_root / slug / "artwork"
                        art_stem = art_dir / identity_hash
                        cover_path = _download_art(cover_url, art_stem, meta_root.resolve(strict=True))

                    if confidence == "dat_verified":
                        totals["verified"] += 1
                    elif confidence == "title_id_catalog":
                        totals["catalogued"] += 1
                    elif confidence in ("provider_suggestion", "ambiguous_name", "local_metadata"):
                        totals["suggested"] += 1
                    else:
                        totals["unmatched"] += 1

                    record = {
                        "identity_id": identity_id,
                        "content_sha256": identity_hash,
                        "platform": slug,
                        "relative_path": relative,
                        "filename": path.name,
                        "is_directory": is_directory,
                        "members": members,
                        "title": str(title or ""),
                        "canonical_title": str(title or ""),
                        "suggested_title": (str((info.get("title") or switch_title) if isinstance(info, dict) else switch_title)),
                        "confidence": confidence,
                        "match_details": (
                            str(getattr(dat_match, "game", "") or "Exact DAT checksum match")
                            if confidence == "dat_verified" else
                            str(switch.get("details") or "Title ID found in TitleDB; file bytes are not verified")
                            if confidence == "title_id_catalog" else
                            "Imported from the existing ES-DE gamelist; review before renaming"
                            if confidence == "local_metadata" else
                            "Metadata provider title suggestion; confirm before renaming"
                            if confidence in ("provider_suggestion", "ambiguous_name") else
                            "Filename only; no verified catalog match"
                        ),
                        "dat": str(getattr(dat_match, "dat", "") or ""),
                        "dat_status": str(getattr(dat_match, "status", UNKNOWN) or UNKNOWN),
                        "dat_game": str(getattr(dat_match, "game", "") or ""),
                        "hashes": hashes,
                        "switch": switch,
                        "metadata": metadata,
                        "lookup_attempted": False if lookup_deferred else True,
                        "cover_path": cover_path,
                        "manual_mapping": manual,
                        "manifests": cached.get("manifests") or [],
                        "updated_at": _now(),
                    }
                    record["metadata_sidecar"] = self._write_sidecar(
                        record, str(cached.get("metadata_sidecar") or ""))
                    by_platform[slug][identity_id] = record
                    seen_identities.setdefault(slug, set()).add(identity_id)
                    if (len(by_platform[slug]) % 50 == 0
                            or self.status().get("processed", 0) % 50 == 0):
                        self._write_catalog(slug, list(by_platform[slug].values()))
                except Exception as exc:
                    errors.append(f"{path.name}: {type(exc).__name__}")
                    failed_paths.setdefault(slug, set()).add(relative)
                    log.warning("library identification skipped %s (%s)",
                                path.name, type(exc).__name__)
                finally:
                    with self._lock:
                        self._status["processed"] += 1
                        for key, value in totals.items():
                            self._status[key] = value
            scanned_slugs = ([resolve(selected).slug] if selected and resolve(selected)
                             else [p.slug for p in PLATFORMS])
            if not truncated:
                for slug in scanned_slugs:
                    if slug not in by_platform:
                        catalog = self._read_catalog(slug)
                        by_platform[slug] = {
                            str(row.get("identity_id")): dict(row)
                            for row in catalog.get("games", [])
                            if isinstance(row, dict) and row.get("identity_id")
                        }
                        existing[slug] = dict(by_platform[slug])
                    by_platform[slug] = {
                        identity_id: row for identity_id, row in by_platform[slug].items()
                        if identity_id in seen_identities.get(slug, set())
                        or str(row.get("relative_path") or "")
                        in failed_paths.get(slug, set())
                    }
            for slug, rows in by_platform.items():
                changed_groups = _apply_disc_groups(rows)
                changed_groups.update(_apply_manifest_disc_groups(rows, root))
                for identity_id in changed_groups:
                    row = rows.get(identity_id)
                    if row is not None:
                        previous = str(existing.get(slug, {}).get(
                            identity_id, {}).get("metadata_sidecar") or "")
                        row["metadata_sidecar"] = self._write_sidecar(row, previous)
                self._write_catalog(slug, list(rows.values()))
            with self._lock:
                self._status["state"] = "complete" if not truncated else "partial"
                self._status["finished_at"] = _now()
                self._status["truncated"] = bool(truncated)
                self._status["error"] = "; ".join(errors[:10])
        except Exception as exc:
            log.exception("library identification failed")
            with self._lock:
                self._status["state"] = "failed"
                self._status["finished_at"] = _now()
                self._status["error"] = f"{type(exc).__name__}: {exc}"

    def records(self, platform: str = "", *, review_only: bool = False,
                group_discs: bool = False, limit: int = 200,
                offset: int = 0) -> dict:
        root = self.metadata_root
        if root is None or _path_has_symlink(root) or not root.is_dir():
            return {"items": [], "total": 0, "platforms": [], "error": "metadata root not configured"}
        if platform and resolve(platform) is None:
            return {"items": [], "total": 0, "platforms": [],
                    "error": "unknown platform"}
        slugs = [resolve(platform).slug] if platform else [p.slug for p in PLATFORMS]
        rows = []
        platforms = []
        for slug in slugs:
            try:
                data = self._read_catalog(slug)
            except Exception:
                continue
            games = data.get("games", [])
            if games:
                platforms.append(slug)
            for row in games:
                if not isinstance(row, dict):
                    continue
                rows.append(dict(row))
        if group_discs:
            rows = _collapse_disc_groups(rows)
        if review_only:
            review_confidence = ("provider_suggestion", "ambiguous_name",
                                 "filename_only", "multi_disc")
            rows = [row for row in rows if row.get("confidence") in review_confidence
                    or any(member.get("confidence") in review_confidence
                           for member in (row.get("disc_group") or {}).get("members", []))]
        rows.sort(key=lambda row: (
            str(row.get("platform") or ""),
            str(row.get("canonical_title") or row.get("filename") or "").casefold(),
        ))
        total = len(rows)
        return {"items": rows[max(0, offset):max(0, offset) + max(1, min(limit, MAX_SCAN_FILES))],
                "total": total, "platforms": platforms}

    def map_record(self, identity_id: str, title: str, *, platform: str = "") -> dict:
        title = _safe_component(title)
        if not title or len(title) > 180:
            raise ValueError("Enter a valid canonical game title.")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}:[a-f0-9]{64}", str(identity_id or "")):
            raise ValueError("Invalid game identity.")
        slug, _ = identity_id.split(":", 1)
        resolved = resolve(slug)
        if resolved is None or resolved.slug != slug:
            raise ValueError("Unknown platform identity.")
        if platform and (resolve(platform) is None or resolve(platform).slug != slug):
            raise ValueError("The selected platform does not match this game.")
        catalog = self._read_catalog(slug)
        games = [dict(row) for row in catalog.get("games", [])
                 if isinstance(row, dict)]
        record = next((row for row in games
                       if row.get("identity_id") == identity_id), None)
        if record is None:
            raise ValueError("This game is no longer in the metadata catalog. Scan the library again.")
        group_id = str((record.get("disc_group") or {}).get("id") or "")
        targets = [row for row in games
                   if group_id and (row.get("disc_group") or {}).get("id") == group_id]
        if not targets:
            targets = [record]
        for item in targets:
            item.update({
                "title": title, "canonical_title": title,
                "manual_mapping": True, "confidence": "manual",
                "match_details": "Manually confirmed by the library owner.",
                "updated_at": _now(),
            })
            if item.get("disc_group"):
                item["disc_group"]["title"] = title
            item["metadata_sidecar"] = self._write_sidecar(
                item, str(item.get("metadata_sidecar") or ""))
        self._write_catalog(slug, games)
        return record

    def _switch_target_parent(self, slug: str, kind: str) -> Path | None:
        if (slug != "switch" or kind not in ("update", "dlc")
                or not self.service.store.settings.get("switch_auto_route")):
            return None
        key = "switch_updates_dir" if kind == "update" else "switch_dlc_dir"
        subdir = str(self.service.store.settings.get(key) or "").strip()
        if not subdir:
            return None
        component = _safe_component(subdir)
        if component != subdir or "/" in subdir or "\\" in subdir:
            return None
        root = self.rom_root.expanduser().resolve(strict=True)
        base = root / self._folder_name_for_platform(slug, root)
        if str(self.service.store.settings.get("library_layout") or "").lower() in (
                "nested", "romm_b", "b"):
            base = base / "roms"
        return base / component

    def rename_plan(self, platform: str = "", *, offset: int = 0,
                    limit: int = RENAME_PLAN_BATCH_SIZE) -> dict:
        if self.metadata_root is None:
            raise ValueError("Set a shared metadata root before making a rename plan.")
        root = self.rom_root.expanduser().resolve(strict=True)
        if platform and resolve(platform) is None:
            raise ValueError("Select a supported platform.")
        try:
            offset = max(0, int(offset))
            limit = max(1, min(int(limit), MAX_RENAME_PLAN_BATCH))
        except (TypeError, ValueError):
            raise ValueError("Rename batch offset and limit must be integers.") from None
        requested = resolve(platform).slug if platform else ""
        source = self.records(requested, limit=limit, offset=offset)
        if source.get("error"):
            return {"error": source["error"], "operations": [], "blocked": [],
                    "plan_id": "", "batch": {"offset": offset, "limit": limit,
                                                "total": source.get("total", 0)}}
        all_rows = source["items"]
        total = int(source.get("total", 0))
        next_offset = offset + len(all_rows)
        has_more = next_offset < total
        operations, blocked = [], []
        destinations = set()
        fingerprint = []
        for row in all_rows:
            fingerprint.append({
                "identity_id": str(row.get("identity_id") or ""),
                "relative_path": str(row.get("relative_path") or ""),
                "content_sha256": str(row.get("content_sha256") or ""),
                "canonical_title": str(row.get("canonical_title") or ""),
                "confidence": str(row.get("confidence") or ""),
                "disc_group": str((row.get("disc_group") or {}).get("id") or ""),
            })
            confidence = str(row.get("confidence") or "")
            if confidence not in ("dat_verified", "manual"):
                continue
            slug = str(row.get("platform") or "")
            rel = str(row.get("relative_path") or "")
            try:
                src = _resolve_relative(root, rel)
            except ValueError:
                blocked.append({"identity_id": row.get("identity_id"), "reason": "Unsafe or missing source path"})
                continue
            if src.is_symlink() or not src.exists():
                blocked.append({"identity_id": row.get("identity_id"), "reason": "Source file is missing or is a symlink"})
                continue
            if src.is_file() and _referenced_disc_member(src):
                blocked.append({"identity_id": row.get("identity_id"),
                                "reason": "Disc set member; renaming one file could break its cue or playlist references"})
                continue
            if src.is_dir():
                blocked.append({"identity_id": row.get("identity_id"),
                                "reason": "Folder packages are left intact to preserve their contents and references"})
                continue
            if row.get("disc_group"):
                blocked.append({"identity_id": row.get("identity_id"),
                                "reason": "Multi-disc set is grouped for metadata; its disc files stay together"})
                continue
            title = str(row.get("canonical_title") or "")
            component = _safe_component(title)
            if not component:
                blocked.append({"identity_id": row.get("identity_id"), "reason": "No safe canonical title"})
                continue
            if src.is_dir():
                target_parent = src.parent
                target_name = component
            else:
                target_parent = src.parent
                target_name = component + src.suffix
                switch = row.get("switch") or {}
                kind = str(switch.get("kind") or "")
                routed = self._switch_target_parent(slug, kind)
                if routed is not None and confidence in ("dat_verified", "manual"):
                    target_parent = routed
                    version = switch.get("file_version")
                    if kind == "update" and version is not None:
                        target_name = f"{component} v{int(version)}{src.suffix}"
            target = target_parent / target_name
            try:
                if not _within(root, target) or not _no_symlink_path(root, target_parent):
                    raise ValueError
                target_rel = target.relative_to(root).as_posix()
                source_rel = src.relative_to(root).as_posix()
                if source_rel == target_rel:
                    continue
                key = os.path.normcase(str(target.resolve(strict=False))).casefold()
                if key in destinations:
                    blocked.append({"identity_id": row.get("identity_id"), "reason": "Another planned file has the same destination"})
                    continue
                destinations.add(key)
                if target.exists() or target.is_symlink():
                    blocked.append({"identity_id": row.get("identity_id"), "reason": "Destination already exists; nothing will be overwritten"})
                    continue
                current_hash = _content_identity(src)
                if current_hash != str(row.get("content_sha256") or ""):
                    blocked.append({"identity_id": row.get("identity_id"), "reason": "Content changed since the last scan"})
                    continue
                operations.append({
                    "identity_id": row.get("identity_id"),
                    "platform": slug,
                    "from": source_rel,
                    "to": target_rel,
                    "sha256": current_hash,
                    "reason": ("DAT checksum verified" if confidence == "dat_verified"
                               else "manual mapping confirmed"),
                })
            except (OSError, ValueError):
                blocked.append({"identity_id": row.get("identity_id"), "reason": "Unsafe destination or unable to verify source"})
        payload = {
            "operations": operations,
            "blocked": blocked,
            "fingerprint": fingerprint,
            "batch": {
                "offset": offset, "limit": limit, "total": total,
                "count": len(all_rows), "next_offset": next_offset if has_more else None,
                "has_more": has_more,
            },
        }
        plan_id = _sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        return {"plan_id": plan_id, **payload}

    def apply_rename_plan(self, plan_id: str, platform: str = "", *,
                          offset: int = 0,
                          limit: int = RENAME_PLAN_BATCH_SIZE) -> dict:
        if not re.fullmatch(r"[a-f0-9]{64}", str(plan_id or "")):
            raise ValueError("Invalid plan token.")
        plan = self.rename_plan(platform, offset=offset, limit=limit)
        if plan.get("plan_id") != plan_id:
            raise ValueError("The library changed after this preview. Scan and preview again.")
        operations = plan.get("operations", [])
        if not operations:
            return {"applied": 0, "blocked": plan.get("blocked", []), "message": "There are no safe renames to apply."}
        root = self.rom_root.expanduser().resolve(strict=True)
        metadata_root = self.metadata_root
        if metadata_root is None:
            raise ValueError("Shared metadata root is not configured.")
        if _path_has_symlink(metadata_root):
            raise ValueError("Shared metadata root contains a symlink.")
        metadata_real = metadata_root.resolve(strict=True)
        journal_dir = metadata_real / ".romarr"
        if not _no_symlink_path(metadata_real, journal_dir):
            raise ValueError("Rename journal path contains a symlink.")
        journal_dir.mkdir(parents=True, exist_ok=True)
        journal_path = journal_dir / "rename-journal.json"
        if not _no_symlink_path(metadata_real, journal_path):
            raise ValueError("Rename journal path contains a symlink.")
        journal = _load_json(journal_path)
        if journal:
            self._verify_journal(journal)
        history = journal.get("batches", []) if isinstance(journal.get("batches"), list) else []
        batch = {"id": uuid.uuid4().hex, "plan_id": plan_id, "state": "applying",
                 "created_at": _now(), "operations": [], "error": ""}
        history.append(batch)
        journal["batches"] = history[-20:]
        journal["schema_version"] = 1
        self._save_journal(journal_path, journal, metadata_real)
        moved = []
        try:
            for op in operations:
                src = _resolve_relative(root, op["from"])
                target = _resolve_relative(root, op["to"], allow_missing=True)
                if src.is_symlink() or not src.exists() or target.exists() or target.is_symlink():
                    raise ValueError("A source or destination changed after preview.")
                if not _no_symlink_path(root, src) or not _no_symlink_path(root, target.parent):
                    raise ValueError("A path contains a symlink.")
                if _content_identity(src) != op["sha256"]:
                    raise ValueError("A file changed after preview.")
                batch["pending"] = dict(op)
                self._save_journal(journal_path, journal, metadata_real)
                target.parent.mkdir(parents=True, exist_ok=True)
                if not _no_symlink_path(root, target.parent):
                    raise ValueError("A destination directory contains a symlink.")
                _move_file_no_replace(src, target, op["sha256"])
                applied = {**op, "applied_at": _now()}
                moved.append(applied)
                batch["operations"] = list(moved)
                batch["pending"] = None
                self._save_journal(journal_path, journal, metadata_real)
            self._update_paths({op["from"]: op["to"] for op in moved})
            batch["state"] = "applied"
            batch["finished_at"] = _now()
            self._save_journal(journal_path, journal, metadata_real)
            return {"applied": len(moved), "blocked": plan.get("blocked", []),
                    "batch_id": batch["id"], "message": "Rename plan applied."}
        except Exception as exc:
            rollback_errors = []
            for op in reversed(moved):
                try:
                    current = _resolve_relative(root, op["to"])
                    original = _resolve_relative(root, op["from"], allow_missing=True)
                    if (current.exists() and not original.exists() and not current.is_symlink()
                            and _content_identity(current) == op["sha256"]
                            and _no_symlink_path(root, current)
                            and _no_symlink_path(root, original.parent)):
                        original.parent.mkdir(parents=True, exist_ok=True)
                        _move_file_no_replace(current, original, op["sha256"])
                except Exception as rollback_exc:
                    rollback_errors.append(type(rollback_exc).__name__)
            batch["state"] = "rolled_back" if not rollback_errors else "rollback_incomplete"
            batch["error"] = type(exc).__name__
            batch["rollback_errors"] = rollback_errors
            batch["pending"] = None
            batch["finished_at"] = _now()
            self._save_journal(journal_path, journal, metadata_real)
            raise ValueError(f"Rename failed and was {batch['state']}: {type(exc).__name__}") from exc

    def undo_last(self) -> dict:
        root = self.rom_root.expanduser().resolve(strict=True)
        metadata_root = self.metadata_root
        if metadata_root is None:
            raise ValueError("Shared metadata root is not configured.")
        if _path_has_symlink(metadata_root):
            raise ValueError("Shared metadata root contains a symlink.")
        metadata_real = metadata_root.resolve(strict=True)
        journal_path = metadata_real / ".romarr" / "rename-journal.json"
        if not _no_symlink_path(metadata_real, journal_path):
            raise ValueError("Rename journal path contains a symlink.")
        journal = _load_json(journal_path)
        if journal:
            self._verify_journal(journal)
        batches = journal.get("batches", [])
        batch = next((b for b in reversed(batches)
                      if b.get("state") in ("applied", "applying", "undoing")), None)
        if batch is None:
            raise ValueError("There is no applied rename batch to undo.")
        batch.setdefault("undo_completed", [])
        batch.setdefault("undo_pending", None)
        batch["state"] = "undoing"
        self._save_journal(journal_path, journal, metadata_real)

        # The apply side may have stopped between moving a file and recording
        # it in `operations`. Recover that one explicitly before undoing the
        # completed operations.
        pending = batch.get("pending")
        if isinstance(pending, dict):
            current = _resolve_relative(root, pending["to"], allow_missing=True)
            original = _resolve_relative(root, pending["from"], allow_missing=True)
            if current.exists():
                if (original.exists() or current.is_symlink()
                        or not _no_symlink_path(root, current)
                        or not _no_symlink_path(root, original.parent)
                        or _content_identity(current) != pending.get("sha256")):
                    raise ValueError("Undo stopped at an interrupted move whose paths changed.")
                original.parent.mkdir(parents=True, exist_ok=True)
                _move_file_no_replace(current, original, pending["sha256"])
            elif current.is_symlink() or not original.exists():
                raise ValueError("Undo stopped because an interrupted move is missing from both paths.")
            batch["pending"] = None

        # Recover a prior interrupted undo. A signed marker is written before
        # each reverse move, then cleared only after the move is recorded.
        undo_pending = batch.get("undo_pending")
        if isinstance(undo_pending, dict):
            current = _resolve_relative(root, undo_pending["to"], allow_missing=True)
            original = _resolve_relative(root, undo_pending["from"], allow_missing=True)
            if current.exists() and not original.exists():
                if (current.is_symlink() or not _no_symlink_path(root, current)
                        or not _no_symlink_path(root, original.parent)
                        or _content_identity(current) != undo_pending.get("sha256")):
                    raise ValueError("Undo stopped at an interrupted move whose paths changed.")
                original.parent.mkdir(parents=True, exist_ok=True)
                _move_file_no_replace(current, original, undo_pending["sha256"])
            elif (not original.exists() or current.exists() or current.is_symlink()
                  or original.is_symlink()
                  or not _no_symlink_path(root, original)
                  or _content_identity(original) != undo_pending.get("sha256")):
                raise ValueError("Undo stopped at an interrupted move whose paths changed.")
            if undo_pending not in batch["undo_completed"]:
                batch["undo_completed"].append(undo_pending)
            batch["operations"] = [op for op in batch.get("operations", [])
                                   if op != undo_pending]
            batch["undo_pending"] = None
            self._save_journal(journal_path, journal, metadata_real)

        for op in reversed(list(batch.get("operations", []))):
            current = _resolve_relative(root, op["to"])
            original = _resolve_relative(root, op["from"], allow_missing=True)
            if (not current.exists() or current.is_symlink() or original.exists()
                    or not _no_symlink_path(root, current)
                    or not _no_symlink_path(root, original.parent)
                    or _content_identity(current) != op["sha256"]):
                raise ValueError("Undo stopped because a file changed or its original path is occupied.")
            batch["undo_pending"] = dict(op)
            self._save_journal(journal_path, journal, metadata_real)
            original.parent.mkdir(parents=True, exist_ok=True)
            _move_file_no_replace(current, original, op["sha256"])
            batch["undo_completed"].append(op)
            batch["operations"] = [item for item in batch.get("operations", [])
                                   if item != op]
            batch["undo_pending"] = None
            self._save_journal(journal_path, journal, metadata_real)

        reversed_paths = {
            op["to"]: op["from"] for op in batch.get("undo_completed", [])
            if isinstance(op, dict) and op.get("to") and op.get("from")
        }
        # Update paths before marking the batch complete. If the process stops
        # here, repeating this update is harmless and the journal stays retryable.
        self._update_paths(reversed_paths)
        batch["state"] = "undone"
        batch["undone_at"] = _now()
        self._save_journal(journal_path, journal, metadata_real)
        return {"undone": len(batch["undo_completed"]), "batch_id": batch["id"]}

    def _update_paths(self, changes: dict[str, str]) -> None:
        if not changes:
            return
        for platform in [p.slug for p in PLATFORMS]:
            try:
                catalog = self._read_catalog(platform)
                games = []
                touched = False
                for row in catalog.get("games", []):
                    item = dict(row)
                    if item.get("relative_path") in changes:
                        item["relative_path"] = changes[item["relative_path"]]
                        item["filename"] = PurePosixPath(item["relative_path"]).name
                        item["updated_at"] = _now()
                        item["metadata_sidecar"] = self._write_sidecar(
                            item, str(item.get("metadata_sidecar") or ""))
                        touched = True
                    games.append(item)
                if touched:
                    self._write_catalog(platform, games)
            except Exception as exc:
                log.warning("could not update metadata catalog for %s (%s)",
                            platform, type(exc).__name__)

    def frontend_rows(self, platform: str = "") -> list[dict]:
        if platform and resolve(platform) is None:
            return []
        requested = resolve(platform).slug if platform else ""
        if self.metadata_root is None:
            return []
        result = self.records(requested, limit=MAX_SCAN_FILES, offset=0)
        if result["total"] > MAX_SCAN_FILES:
            return []
        root = self.rom_root.expanduser().resolve(strict=False)
        meta_root = self.metadata_root.resolve(strict=False)
        rows = []
        for row in result["items"]:
            rel = str(row.get("relative_path") or "")
            try:
                path = _resolve_relative(root, rel)
            except ValueError:
                continue
            metadata = row.get("metadata") or {}
            switch = row.get("switch") or {}
            slug = str(row.get("platform") or "")
            platform_root = self._platform_root_for_path(root, slug, rel)
            try:
                frontend_path = path.relative_to(platform_root).as_posix()
            except ValueError:
                continue
            art = ""
            cover = str(row.get("cover_path") or "")
            if cover:
                try:
                    art_path = _resolve_relative(meta_root, cover)
                    art = os.path.relpath(art_path, platform_root).replace(os.sep, "/")
                except ValueError:
                    art = ""
            rows.append({
                "id": row.get("identity_id", ""),
                "identity_id": row.get("identity_id", ""),
                "content_sha256": row.get("content_sha256", ""),
                "title": row.get("canonical_title") or row.get("title") or path.stem,
                "platform": slug,
                "filename": frontend_path,
                # Current ES-DE expands gamelist paths against ROMDirectory,
                # which is the library root above the per-platform folders.
                "esde_path": "./" + PurePosixPath(rel).as_posix(),
                "relative_path": rel,
                "is_directory": bool(row.get("is_directory")),
                "path": str(path),
                "region": "",
                "verified": "verified" if row.get("confidence") == "dat_verified" else "",
                "confidence": row.get("confidence") or "",
                "match_details": row.get("match_details") or "",
                "dat": row.get("dat") or "",
                "dat_status": row.get("dat_status") or UNKNOWN,
                "dat_game": row.get("dat_game") or "",
                "hashes": row.get("hashes") or {},
                "desc": metadata.get("summary") or "",
                "released": metadata.get("released") or "",
                "genres": metadata.get("genres") or [],
                "rating": metadata.get("rating") or 0,
                "metadata_source": metadata.get("source") or "",
                "cover_path": art,
                "metadata_artwork_path": cover,
                "cover_url": "",
                "matched_by": row.get("confidence") or "",
                "switch": switch,
                "disc_group": row.get("disc_group") or {},
                "manifests": row.get("manifests") or [],
                "metadata": metadata,
                "manual_mapping": bool(row.get("manual_mapping")),
                "updated_at": row.get("updated_at") or "",
            })
        return rows

    def artwork(self, identity_id: str) -> tuple[bytes, str]:
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}:[a-f0-9]{64}", str(identity_id or "")):
            raise ValueError("Invalid game identity.")
        slug, _ = identity_id.split(":", 1)
        catalog = self._read_catalog(slug)
        row = next((item for item in catalog.get("games", [])
                    if isinstance(item, dict) and item.get("identity_id") == identity_id), None)
        if row is None or not row.get("cover_path"):
            raise FileNotFoundError("No cached artwork for this game.")
        root = self.metadata_root
        if root is None:
            raise FileNotFoundError("Metadata root is not configured.")
        path = _resolve_relative(root.resolve(strict=True), str(row["cover_path"]))
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ART_BYTES:
            raise FileNotFoundError("Cached artwork is unavailable.")
        data = path.read_bytes()
        extension = path.suffix.lower()
        content_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                        ".png": "image/png", ".webp": "image/webp"}.get(extension, "")
        if not content_type or not _cover_extension(content_type, data[:16]):
            raise ValueError("Cached artwork is not a supported image.")
        return data, content_type

    def publish_esde(self, platform: str) -> dict:
        resolved = resolve(platform)
        if resolved is None:
            raise ValueError("Select a supported platform.")
        rows = self.frontend_rows(resolved.slug)
        if not rows:
            return {"written": False, "message": "Scan this platform before publishing its ES-DE gamelist."}
        root = self.rom_root.expanduser().resolve(strict=True)
        metadata_root = self.metadata_root
        if metadata_root is None or _path_has_symlink(metadata_root):
            raise ValueError("Set a safe shared metadata root before publishing ES-DE data.")
        metadata_root = metadata_root.resolve(strict=True)
        system = esde_folder(resolved.slug)
        esde_root = metadata_root / "esde"
        target = esde_root / "gamelists" / system / "gamelist.xml"
        if not _within(metadata_root, target) or not _no_symlink_path(metadata_root, target):
            raise ValueError("The ES-DE gamelist path is unsafe.")
        physical_root = self._platform_root_for_path(
            root, resolved.slug, str(rows[0].get("relative_path") or ""))
        source_gamelists = self._esde_catalog_paths(
            resolved.slug, root, metadata_root, physical_root)
        allowed_roots = (root, metadata_root,
                         *self._esde_gamelist_roots(metadata_root))
        # Validate every existing source before writing the shared media tree,
        # so a broken XML file cannot leave half of a publish behind.
        existing_games = {}
        existing_files = [(target, root)]
        existing_files.extend(source_gamelists)
        seen_files = set()
        for gamelist, rom_base in existing_files:
            key_file = os.path.normcase(str(gamelist.absolute())).casefold()
            if key_file in seen_files or not gamelist.exists():
                continue
            seen_files.add(key_file)
            try:
                current = _parse_esde_gamelist(_read_bounded_file(
                    gamelist, MAX_GAMELIST_BYTES, allowed_roots))
                if current.tag.rsplit("}", 1)[-1].casefold() != "gamelist":
                    continue
                for game in current:
                    if game.tag.rsplit("}", 1)[-1].casefold() != "game":
                        continue
                    game_path = (game.findtext("path") or "").strip()
                    if not game_path:
                        continue
                    actual = self._esde_rom_relative(
                        game_path, rom_base, root, physical_root)
                    normalized = actual or game_path.removeprefix("./").replace("\\", "/")
                    path_key = os.path.normcase(normalized).casefold()
                    existing_games.setdefault(path_key, game)
            except Exception as exc:
                raise ValueError("Existing gamelist.xml is invalid; it was left untouched.") from exc
        from .frontends import to_gamelist
        generated_rows = []
        artwork_index_path = esde_root / ".romarr-artwork.json"
        try:
            artwork_index = json.loads(_read_bounded_file(
                artwork_index_path, MAX_CATALOG_BYTES, (metadata_root,)).decode("utf-8"))
            if not isinstance(artwork_index, dict):
                artwork_index = {}
        except FileNotFoundError:
            artwork_index = {}
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("The shared ES-DE artwork index is invalid; it was left untouched.") from exc
        managed_art = artwork_index.get("files")
        if not isinstance(managed_art, dict):
            managed_art = {}
        published_media = 0
        for row in rows:
            item = dict(row)
            item["esde_path"] = "./" + PurePosixPath(
                str(row.get("relative_path") or "").replace("\\", "/")).as_posix()
            item["cover_path"] = ""
            artwork_relative = str(row.get("metadata_artwork_path") or "")
            if artwork_relative:
                try:
                    artwork_path = _resolve_relative(metadata_root, artwork_relative)
                    artwork = _read_bounded_file(artwork_path, MAX_ART_BYTES,
                                                 (metadata_root,))
                    extension = _cover_extension("application/octet-stream", artwork[:16])
                    if extension:
                        physical_root = self._platform_root_for_path(
                            root, resolved.slug, str(row.get("relative_path") or ""))
                        frontend_path = _resolve_relative(
                            root, str(row.get("relative_path") or "")).relative_to(
                                physical_root).as_posix()
                        relative = PurePosixPath(frontend_path)
                        stem = relative if row.get("is_directory") else relative.with_suffix("")
                        media_dir = esde_root / "downloaded_media" / system / "covers"
                        destination = media_dir / Path(str(stem) + extension)
                        if (not _within(metadata_root, destination)
                                or not _no_symlink_path(metadata_root, destination)):
                            raise ValueError("The ES-DE media path is unsafe.")
                        target_relative = destination.relative_to(metadata_root).as_posix()
                        candidates = [media_dir / (str(stem) + ext)
                                      for ext in (".jpg", ".png", ".webp")]
                        existing = next((path for path in candidates
                                         if path.exists() or path.is_symlink()), None)
                        reusable = None
                        reusable_hash = ""
                        stale_managed = []
                        if existing is not None:
                            if (existing.is_symlink() or not existing.is_file()
                                    or not _no_symlink_path(metadata_root, existing)):
                                raise ValueError("An existing ES-DE media file is unsafe.")
                            existing_relative = existing.relative_to(metadata_root).as_posix()
                            current = _read_bounded_file(existing, MAX_ART_BYTES,
                                                         (metadata_root,))
                            current_hash = _sha256_bytes(current)
                            if managed_art.get(existing_relative) == current_hash:
                                reusable = existing
                                reusable_hash = current_hash
                                if existing != destination:
                                    stale_managed.append((existing, existing_relative))
                            else:
                                # Preserve artwork someone chose or edited in
                                # ES-DE; ROMarr owns only files it can verify.
                                item["cover_path"] = os.path.relpath(
                                    existing, target.parent).replace(os.sep, "/")
                                managed_art.pop(existing_relative, None)
                        if not item["cover_path"]:
                            if reusable != destination or reusable_hash != _sha256_bytes(artwork):
                                _atomic_bytes(destination, artwork, metadata_root)
                            managed_art[target_relative] = _sha256_bytes(artwork)
                            for old_path, old_relative in stale_managed:
                                try:
                                    old_path.unlink()
                                except OSError:
                                    pass
                                managed_art.pop(old_relative, None)
                            item["cover_path"] = os.path.relpath(
                                destination, target.parent).replace(os.sep, "/")
                            published_media += 1
                except (OSError, ValueError):
                    # A missing or user-modified cover does not block the
                    # portable metadata catalog from being published.
                    pass
            generated_rows.append(item)
        artwork_index = {"schema_version": 1, "files": managed_art}
        _atomic_json(artwork_index_path, artwork_index, metadata_root)
        generated = ET.fromstring(to_gamelist(generated_rows).encode("utf-8"))

        output = ET.Element("gameList")
        used = set()
        for new_game in generated.findall("game"):
            new_path = (new_game.findtext("path") or "").replace("\\", "/")
            key = os.path.normcase(new_path.removeprefix("./")).casefold()
            old = existing_games.get(key)
            if old is not None:
                merged = ET.fromstring(ET.tostring(old, encoding="utf-8"))
                for child in list(new_game):
                    value = child.text or ""
                    previous = merged.find(child.tag)
                    if value or previous is None:
                        if previous is not None:
                            merged.remove(previous)
                        merged.append(ET.fromstring(ET.tostring(child, encoding="utf-8")))
                output.append(merged)
                used.add(key)
            else:
                output.append(new_game)
        for key, old in existing_games.items():
            if key not in used:
                output.append(old)
        raw = ET.tostring(output, encoding="utf-8")
        pretty = minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8")
        _atomic_bytes(target, pretty, metadata_root)
        return {"written": True, "path": str(target), "games": len(rows),
                "media": published_media,
                "message": f"Published {len(rows)} ES-DE entries and {published_media} shared covers.",
                "preserved_existing": max(0, len(existing_games) - len(used))}


def _referenced_disc_member(path: Path) -> bool:
    """Keep cue/playlist-linked disc files together until set-level renaming exists."""
    manifest_suffixes = {".cue", ".gdi", ".m3u", ".ccd", ".toc"}
    if path.suffix.lower() in manifest_suffixes:
        return True
    for directory in (path.parent, path.parent.parent):
        try:
            manifests = [child for child in directory.iterdir()
                         if child.is_file() and not child.is_symlink()
                         and child.suffix.lower() in manifest_suffixes]
        except OSError:
            continue
        for manifest in manifests:
            try:
                if manifest.stat().st_size > 1024 * 1024:
                    continue
                if path.name.casefold() in manifest.read_text(
                        encoding="utf-8", errors="ignore").casefold():
                    return True
            except OSError:
                continue
    return False


def _resolve_relative(root: Path, relative: str, *, allow_missing: bool = False) -> Path:
    posix = PurePosixPath(str(relative or ""))
    if posix.is_absolute() or not posix.parts or any(part in ("", ".", "..") for part in posix.parts):
        raise ValueError("unsafe relative path")
    candidate = root.joinpath(*posix.parts)
    if not _within(root, candidate) or not _no_symlink_path(root, candidate):
        raise ValueError("path escapes root or contains a symlink")
    if not allow_missing and not candidate.exists():
        raise ValueError("path does not exist")
    return candidate


def _content_identity(path: Path) -> str:
    if path.is_file():
        return _stable_file_hash(path)[1]
    if not path.is_dir() or path.is_symlink():
        raise ValueError("not a safe file or directory")
    digest = hashlib.sha256()
    count = 0
    for current, dirs, files in os.walk(path, followlinks=False):
        directory = Path(current)
        if any((directory / name).is_symlink() for name in dirs):
            raise ValueError("game folder contains a symlink")
        dirs[:] = sorted(dirs)
        for name in sorted(files):
            child = directory / name
            if child.is_symlink():
                raise ValueError("game folder contains a symlink")
            if not child.is_file():
                continue
            content = _stable_file_hash(child)[1]
            digest.update(child.relative_to(path).as_posix().encode("utf-8", "surrogateescape"))
            digest.update(b"\0")
            digest.update(content.encode("ascii"))
            digest.update(b"\n")
            count += 1
            if count > MAX_DIRECTORY_FILES:
                raise ValueError("game folder contains too many files to move safely")
    if not count:
        raise ValueError("game folder is empty")
    return digest.hexdigest()
