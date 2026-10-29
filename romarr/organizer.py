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

import requests

from .dat import UNKNOWN, VERIFIED, header_size
from .metadata import clean_title
from .platforms import PLATFORMS, resolve
from .titled import base_tid_of, validate_switch_rom

log = logging.getLogger(__name__)

MAX_SCAN_FILES = 50_000
MAX_DIRECTORY_FILES = 10_000
MAX_CATALOG_BYTES = 128 * 1024 * 1024
MAX_ART_BYTES = 15 * 1024 * 1024
MAX_PROVIDER_LOOKUPS_PER_SCAN = 200
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
            item["disc_group"] = {**disc, "members": []}
            grouped[group_id] = item
            output.append(item)
        item = grouped[group_id]
        item["disc_group"]["members"].append({
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
        except OSError:
            return None
        if child is None:
            return None
        current = child
    return current if current.is_file() else None


def _scan_paths(root: Path, metadata_root: Path, only_platform: str = ""):
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
        platform = resolve(relative.parts[0]) if relative.parts else None
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
        payload = {
            "schema_version": 1,
            "identity_id": identity_id,
            "sidecar_path": relative,
            "platform": slug,
            "title": str(record.get("canonical_title") or record.get("title") or ""),
            "relative_path": str(record.get("relative_path") or ""),
            "confidence": str(record.get("confidence") or ""),
            "match_details": str(record.get("match_details") or ""),
            "dat": str(record.get("dat") or ""),
            "dat_status": str(record.get("dat_status") or UNKNOWN),
            "metadata": record.get("metadata") or {},
            "switch": record.get("switch") or {},
            "disc_group": record.get("disc_group") or {},
            "artwork_path": str(record.get("cover_path") or ""),
            "updated_at": str(record.get("updated_at") or _now()),
        }
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
                "switch_outdated": 0, "truncated": False, "force": bool(force),
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
                  "unmatched": 0, "switch_outdated": 0}
        by_platform: dict[str, dict[str, dict]] = {}
        errors = []
        truncated = False
        provider_lookups = 0
        seen_identities: dict[str, set[str]] = {}
        failed_paths: dict[str, set[str]] = {}
        try:
            paths = []
            for platform, path, _ in _scan_paths(root, meta_root, selected):
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

                relative = path.relative_to(root.resolve(strict=True)).as_posix()
                try:
                    identity_hash, hashes, _, members = _identity(path, platform)
                    identity_id = f"{slug}:{identity_hash}"
                    cached = existing[slug].get(identity_id, {})
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
                    metadata = dict(cached.get("metadata") or {})
                    lookup_attempted = bool(cached.get("lookup_attempted")) and not force
                    lookup_deferred = False
                    if manual:
                        confidence = "manual"
                        title = str(cached.get("canonical_title") or cached.get("title") or "")
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
                            metadata = dict(info)
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
                            metadata = dict(cached.get("metadata") or {})

                    if not manual and dat_match.status == VERIFIED and dat_match.game:
                        confidence = "dat_verified"
                        title = str(dat_match.game)
                    elif not manual and switch.get("matched_by_name"):
                        title = switch_title or title or clean_title(path.name)
                        confidence = "ambiguous_name"
                    elif (not manual
                          and switch.get("catalog_status") == "verified"):
                        title = switch_title or title or clean_title(path.name)
                        confidence = "title_id_catalog"

                    previous_cover = str(cached.get("cover_path") or "")
                    cover_path = previous_cover
                    cover_url = str(
                        (info.get("cover_url") if isinstance(info, dict) else "")
                        or metadata.get("cover_url") or "")
                    if not manual and cover_url and (force or not previous_cover
                            or not (meta_root / previous_cover).is_file()):
                        art_dir = meta_root / slug / "artwork"
                        art_stem = art_dir / identity_hash
                        cover_path = _download_art(cover_url, art_stem, meta_root.resolve(strict=True))

                    if confidence == "dat_verified":
                        totals["verified"] += 1
                    elif confidence == "title_id_catalog":
                        totals["catalogued"] += 1
                    elif confidence in ("provider_suggestion", "ambiguous_name"):
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
        base = self.rom_root.expanduser().resolve(strict=True) / slug
        if str(self.service.store.settings.get("library_layout") or "").lower() in (
                "nested", "romm_b", "b"):
            base = base / "roms"
        return base / component

    def rename_plan(self, platform: str = "") -> dict:
        if self.metadata_root is None:
            raise ValueError("Set a shared metadata root before making a rename plan.")
        root = self.rom_root.expanduser().resolve(strict=True)
        if platform and resolve(platform) is None:
            raise ValueError("Select a supported platform.")
        requested = resolve(platform).slug if platform else ""
        source = self.records(requested, limit=500, offset=0)
        all_rows = source["items"]
        # Fetch complete platform catalogs for planning; the UI only pages the
        # review table, while plans must never silently omit files.
        if source["total"] > len(all_rows):
            all_rows = self.records(requested, limit=500, offset=0)["items"]
            # Plans with more than 500 entries are intentionally refused below.
        if source["total"] > 500:
            return {"error": "This plan exceeds 500 entries. Select one platform to preview and apply safely.",
                    "operations": [], "blocked": [], "plan_id": ""}
        operations, blocked = [], []
        destinations = set()
        for row in all_rows:
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
        payload = {"operations": operations, "blocked": blocked}
        plan_id = _sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        return {"plan_id": plan_id, **payload}

    def apply_rename_plan(self, plan_id: str, platform: str = "") -> dict:
        if not re.fullmatch(r"[a-f0-9]{64}", str(plan_id or "")):
            raise ValueError("Invalid plan token.")
        plan = self.rename_plan(platform)
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
        nested = str(self.service.store.settings.get("library_layout") or "").lower() in (
            "nested", "romm_b", "b")
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
            platform_root = root / slug / ("roms" if nested else "")
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
                "title": row.get("canonical_title") or row.get("title") or path.stem,
                "platform": slug,
                "filename": frontend_path,
                "path": str(path),
                "region": "",
                "verified": "verified" if row.get("confidence") == "dat_verified" else "",
                "desc": metadata.get("summary") or "",
                "released": metadata.get("released") or "",
                "genres": metadata.get("genres") or [],
                "rating": metadata.get("rating") or 0,
                "metadata_source": metadata.get("source") or "",
                "cover_path": art,
                "cover_url": "",
                "matched_by": row.get("confidence") or "",
                "switch": switch,
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
        base = root / resolved.slug
        if str(self.service.store.settings.get("library_layout") or "").lower() in (
                "nested", "romm_b", "b"):
            base = base / "roms"
        target = base / "gamelist.xml"
        if not _within(root, target) or not _no_symlink_path(root, base):
            raise ValueError("The ES-DE gamelist path is unsafe.")
        from .frontends import to_gamelist
        generated = ET.fromstring(to_gamelist(rows).encode("utf-8"))
        existing_games = {}
        if target.exists():
            if target.is_symlink() or not target.is_file():
                raise ValueError("Existing gamelist.xml is not a regular file.")
            try:
                current = ET.fromstring(target.read_bytes())
                for game in current.findall("game"):
                    path = (game.findtext("path") or "").replace("\\", "/")
                    if path:
                        existing_games[os.path.normcase(path).casefold()] = game
            except Exception as exc:
                raise ValueError("Existing gamelist.xml is invalid; it was left untouched.") from exc
        output = ET.Element("gameList")
        used = set()
        for new_game in generated.findall("game"):
            key = os.path.normcase((new_game.findtext("path") or "").replace("\\", "/")).casefold()
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
        _atomic_bytes(target, pretty, root)
        return {"written": True, "path": str(target), "games": len(rows),
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
