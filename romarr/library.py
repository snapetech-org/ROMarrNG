"""Getting a finished download into RomM's library.

RomM reads a directory tree: `<library>/<platform-slug>/<rom file>`. Nothing
more clever than that is required, which is why this module is small — but the
details it does handle are the ones that silently corrupt a library:

  * archives (game releases are usually zipped or 7z'd, not bare ROMs)
  * choosing the ROM among the readmes and box art
  * never overwriting an existing ROM without being told to
  * never writing outside the library root, even if an archive contains
    `../../etc/passwd` — a real and old attack against every extractor
"""

from __future__ import annotations

import logging
import io
from contextlib import nullcontext
import os
import re
import shutil
import subprocess
import tempfile
import threading
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .dat import BAD_DUMP, UNKNOWN, VERIFIED, Match, hash_bytes, hash_file, hash_stream, rom_matches
from .safe_files import atomic_file, atomic_directory, parent_fd, source_file
from .limits import Budget, limit, preflight_zip
from .platforms import Platform
from .selection import pick_all_rom_sets, pick_rom_set

log = logging.getLogger(__name__)

#: Formats a finished download arrives in.
#:
#: `.zip` was the whole list, which was survivable while only cartridges were
#: supported. It is not survivable now: the live library's disc platforms are
#: overwhelmingly `.7z` -- 2,621 PlayStation entries, 2,409 PS2, 1,470 Wii --
#: and an importer that cannot open the format the content ships in supports
#: the platform on paper only.
ARCHIVE_SUFFIXES = (".zip", ".7z", ".rar")

#: Handled by the standard library, with no tool to install.
_STDLIB_ARCHIVES = (".zip",)


def _bsdtar() -> str | None:
    """A libarchive `bsdtar`, which reads 7z, rar and zip uniformly.

    `RommStreamServer` already reaches for exactly this and for the same
    reason, so this is a second user of a proven choice rather than a new
    dependency. Windows ships it as `tar.exe`; Alpine needs
    `libarchive-tools`, which the Dockerfile installs.

    GNU tar is explicitly rejected. It answers to the same name on most Linux
    systems and cannot read a 7z, so accepting it on name alone would turn a
    missing dependency into a corrupt-archive error pointing at the download.

    Every `PATH` entry is searched rather than the first hit per name, because
    a machine with both is the normal case, not a corner: Windows ships
    libarchive as `System32\\tar.exe` while Git for Windows puts GNU tar
    earlier on the same `PATH`, and a Linux box with `libarchive-tools`
    installed alongside GNU tar looks identical. Stopping at the first binary
    called `tar` finds the one that cannot do the job and concludes the job
    cannot be done.
    """
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        for name in ("bsdtar", "tar"):
            path = shutil.which(name, path=directory)
            if path and _is_libarchive(path):
                return path
    return None


def _is_libarchive(path: str) -> bool:
    try:
        out = subprocess.run([path, "--version"], capture_output=True,
                             text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return "libarchive" in (out.stdout + out.stderr).lower()


@lru_cache(maxsize=1)
def bsdtar_path() -> str | None:
    """`_bsdtar()`, resolved once. `None` when no usable tool is installed."""
    return _bsdtar()


@dataclass(frozen=True)
class ImportResult:
    ok: bool
    destination: Path | None
    reason: str = ""
    #: What the DAT said about the bytes that actually landed. `unknown` when
    #: no DAT is loaded, which is the default and is not a failure.
    verification: Match = field(default_factory=lambda: Match(UNKNOWN))
    #: What the game is, once a metadata provider has been asked. Empty
    #: when none is configured -- metadata is an enhancement and its
    #: absence must never look like a failed import.
    info: dict = field(default_factory=dict)


def _canonical_component(value: str) -> str:
    """A DAT title as a portable filename component, never as a path."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', " ", str(value or ""))
    name = re.sub(r"\s+", " ", name).strip(" .")[:180].rstrip(" .")
    while name and len(name.encode("utf-8")) > 180:
        name = name[:-1].rstrip(" .")
    if name.casefold() in {"", ".", ".."}:
        return ""
    if re.match(r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$",
                name, re.I):
        name = "_" + name
    return name


def is_safe_name(name: str, root: Path) -> bool:
    """Whether extracting `name` under `root` stays under `root`.

    Applied to every format, not only zip. The check used to live inside the
    zip reader, so adding 7z and rar would have added two formats with no
    zip-slip protection at all -- and the format an attacker chooses is the one
    with the gap.
    """
    normalized = name.replace("\\", "/")
    if (not normalized or normalized.endswith("/") or "\x00" in normalized
            or normalized.startswith("/") or ":" in normalized
            or ".." in normalized.split("/")):
        return False
    root_resolved = root.resolve()
    return (root_resolved / name).resolve().is_relative_to(root_resolved)


def safe_members(archive: zipfile.ZipFile, root: Path) -> list[str]:
    """Archive entries that stay inside `root` when extracted.

    A zip may contain absolute paths or `../` traversal. Extracting those writes
    outside the library -- the classic zip-slip. Anything that does not resolve
    inside root is dropped rather than sanitised, because a release that needs
    sanitising is not one to trust.
    """
    keep = []
    for name in archive.namelist():
        if name.endswith("/"):
            continue
        if is_safe_name(name, root):
            keep.append(name)
        else:
            log.warning("refusing archive entry outside root: %r", name)
    return keep


class _Source:
    """Where the files of a finished download are, and how to get at them.

    Three shapes exist -- a zip, an archive only `bsdtar` can read, and a plain
    file or directory the client already unpacked -- and each answers the same
    three questions. `pick_rom_set` needs `read` to parse a `.cue`, and only
    something that knows the shape can provide it.
    """

    def names(self) -> list[str]:
        raise NotImplementedError

    def read(self, name: str) -> bytes | None:
        raise NotImplementedError

    def copy(self, name: str, destination: Path) -> None:
        raise NotImplementedError

    def hashes(self, name: str) -> dict:
        return hash_bytes(self.read(name), suffix=Path(name).suffix)

    def copy_set(self, members, stage):
        for member, name in members:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            self.copy(member, target)


def _output(destination):
    return nullcontext(destination) if hasattr(destination, "write") else open(destination, "wb")


class _ZipSource(_Source):
    def __init__(self, path: Path):
        self.path = path
        self.budget = Budget()
        self.verification_budget = Budget()
        preflight_zip(path)

    def names(self):
        with zipfile.ZipFile(self.path) as archive:
            names = safe_members(archive, self.path.parent)
            if any(info.file_size > self.budget.member for info in archive.infolist()):
                raise ValueError("archive member exceeds its byte budget")
            if sum(info.file_size for info in archive.infolist()) > self.budget.maximum:
                raise ValueError("archive expansion exceeds its byte budget")
            return names

    def read(self, name):
        output = io.BytesIO()
        with zipfile.ZipFile(self.path) as archive, archive.open(name) as source:
            self.verification_budget.copy(source, output, maximum=limit("ROMARR_MAX_METADATA_BYTES", 1 << 20))
        return output.getvalue()

    def copy(self, name, destination):
        with zipfile.ZipFile(self.path) as archive, archive.open(name) as source, _output(destination) as output:
            self.budget.copy(source, output)

    def hashes(self, name):
        with zipfile.ZipFile(self.path) as archive, archive.open(name) as source:
            info = archive.getinfo(name)
            if info.file_size > self.budget.member:
                raise ValueError("archive member exceeds its byte budget")
            return hash_stream(_BoundedReader(source, self.budget.member, budget=self.verification_budget),
                               suffix=Path(name).suffix, size=info.file_size)


class _BoundedReader:
    def __init__(self, source, maximum, *, budget=None):
        self.source, self.remaining = source, maximum
        self.budget = budget or Budget()
        self.deadline = self.budget.deadline

    def read(self, size=-1):
        if __import__("time").monotonic() > self.deadline:
            raise OSError("archive read exceeded its time budget")
        data = self.source.read(min(self.remaining + 1, size if size >= 0 else self.remaining + 1))
        self.remaining -= len(data)
        self.budget.remaining -= len(data)
        if self.remaining < 0 or self.budget.remaining < 0:
            raise OSError("archive read exceeded its byte budget")
        return data


class _BsdtarSource(_Source):
    def __init__(self, path: Path, tool: str):
        self.path, self.tool = path, tool
        self.budget = Budget()
        self.verification_budget = Budget()

    def _stream(self, args, output, *, maximum=None, budget=None):
        budget = budget or self.verification_budget
        with subprocess.Popen([self.tool, *args], stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL) as process:
            timer = threading.Timer(max(.01, budget.deadline - __import__("time").monotonic()), process.kill)
            timer.daemon = True
            timer.start()
            try:
                size = budget.copy(process.stdout, output, maximum=maximum)
                if process.wait() != 0:
                    raise OSError("archive extraction failed or timed out")
                return size
            finally:
                timer.cancel()
                if process.poll() is None:
                    process.kill()
                    process.wait()

    def names(self):
        out = io.BytesIO()
        self._stream(["-tf", str(self.path)], out, maximum=16 << 20)
        names = [n.strip() for n in out.getvalue().decode("utf-8", "replace").splitlines()
                 if n.strip() and not n.endswith("/")]
        if len(names) > limit("ROMARR_MAX_ARCHIVE_FILES", 10000):
            raise ValueError("archive has too many members")
        return [n for n in names if is_safe_name(n, self.path.parent)]

    def read(self, name):
        out = io.BytesIO()
        self._stream(["-xOf", str(self.path), "--", name], out,
                     maximum=limit("ROMARR_MAX_METADATA_BYTES", 1 << 20))
        return out.getvalue()

    def copy(self, name, destination):
        with _output(destination) as out:
            self._stream(["-xOf", str(self.path), "--", name], out, budget=self.budget)

    def hashes(self, name):
        # Spool with a byte budget to learn copier-header size without buffering
        # an entire ROM in RAM or trusting a platform-specific listing format.
        with tempfile.TemporaryFile() as out:
            size = self._stream(["-xOf", str(self.path), "--", name], out)
            out.seek(0)
            return hash_stream(out, suffix=Path(name).suffix, size=size)


class _PathSource(_Source):
    def __init__(self, path: Path):
        self.path = path
        self.budget = Budget()
        self.verification_budget = Budget()

    def names(self):
        if self.path.is_symlink():
            raise OSError("source cannot be a symlink")
        if self.path.is_file():
            return [self.path.name]
        names = []
        for current, dirs, files in os.walk(self.path, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(current)/d).is_symlink()]
            for name in files:
                path = Path(current)/name
                if not path.is_symlink() and path.is_file():
                    names.append(path.relative_to(self.path).as_posix())
                    if len(names) > limit("ROMARR_MAX_ARCHIVE_FILES", 10000):
                        raise ValueError("source has too many members")
        return names

    def _path(self, name):
        return self.path if self.path.is_file() else self.path / name

    def read(self, name):
        out = io.BytesIO()
        with source_file(self._path(name)) as source:
            self.verification_budget.copy(source, out, maximum=limit("ROMARR_MAX_METADATA_BYTES", 1 << 20))
        return out.getvalue()

    def copy(self, name, destination):
        with source_file(self._path(name)) as source, _output(destination) as output:
            self.budget.copy(source, output)

    def hashes(self, name):
        with source_file(self._path(name)) as source:
            size = os.fstat(source.fileno()).st_size
            return hash_stream(_BoundedReader(source, self.budget.member, budget=self.verification_budget),
                               suffix=Path(name).suffix, size=size)


class MissingArchiveTool(Exception):
    """The download is in a format no installed tool can open."""


def _source_for(download: Path, platform: Platform | None = None) -> _Source:
    # For MAME, FBNeo and DOSBox the archive IS the ROM: the core opens it and
    # expects its internal layout. Looking inside would pick one chip dump out
    # of a romset and import that, which succeeds and leaves an entry no core
    # can load. Treat it as a plain file.
    if (platform is not None and platform.archive_is_the_rom
            and download.is_file()):
        return _PathSource(download)

    suffix = download.suffix.lower()
    if download.is_file() and suffix in _STDLIB_ARCHIVES:
        return _ZipSource(download)
    if download.is_file() and suffix in ARCHIVE_SUFFIXES:
        tool = bsdtar_path()
        if tool is None:
            raise MissingArchiveTool(
                f"{download.name} is a {suffix} archive and bsdtar is not "
                "installed, so its contents cannot be read. Install "
                "libarchive-tools (Debian/Alpine) or use the official ROMarr "
                "image, which ships it.")
        return _BsdtarSource(download, tool)
    return _PathSource(download)


def list_candidates(download: Path) -> list[str]:
    """Every file a completed download offers, looking inside an archive if needed."""
    return _source_for(download).names()


def verify_set(source, members, dats) -> Match:
    """What a DAT says about the files that are about to be imported.

    Verified means **every** member matched. Redump lists each track of a disc
    as its own `<rom>`, so a cue with a good checksum beside a corrupt track
    is not a good import -- and reporting the set on the strength of its first
    member is how that would be missed.

    Read from the source rather than the destination on purpose: it is the
    same bytes, and doing it here means a refusal can happen before anything
    is written.
    """
    if dats is None:
        return Match(UNKNOWN)
    verdicts = []
    computed = []
    for member in members:
        try:
            hashes = source.hashes(member) if hasattr(source, "hashes") else None
            if hashes is None:
                data = source.read(member)
                if data is None:
                    return Match(UNKNOWN, detail=f"could not read {member!r} to verify")
                hashes = hash_bytes(data, suffix=Path(member).suffix)
        except Exception:
            return Match(UNKNOWN, detail=f"could not read {member!r} to verify")
        computed.append(hashes)
        verdicts.append(dats.lookup(**hashes))

    if not verdicts:
        return Match(UNKNOWN)
    bad = next((v for v in verdicts if v.status == BAD_DUMP), None)
    if bad is not None:
        return bad
    if all(v.status == VERIFIED for v in verdicts):
        candidates = {v.game for v in verdicts}
        for dat in getattr(dats, "dats", [dats]):
            for game in candidates:
                entry = dat.games.get(game)
                if entry is None or len(entry.roms) != len(computed):
                    continue
                remaining = list(entry.roms)
                for hashes in computed:
                    match = next((r for r in remaining if rom_matches(r, hashes)), None)
                    if match is None:
                        break
                    remaining.remove(match)
                else:
                    return Match(VERIFIED, game, verdicts[0].rom, dat.name)
        return Match(UNKNOWN, detail="members do not form a complete game in one DAT")
    return Match(UNKNOWN)


#: The two directory layouts RomM understands, and every folder-based
#: frontend after it. Named for what RomM calls them in its own docs so an
#: operator can match this to the setting they already know.
#:
#:   flat  -- <root>/<platform>/<rom>            (RomM "Structure A")
#:   nested -- <root>/<platform>/roms/<rom>      (RomM "Structure B")
#:
#: A translation, when the policy keeps it beside the original, goes one
#: level deeper in a folder RomM treats as a variant rather than a second
#: game. That subfolder is the same in both layouts.
TRANSLATION_SUBDIR = "Translations"


def platform_dir(library_root: Path, platform: "Platform | str", *,
                 layout: str = "flat", translation: bool = False,
                 folder_name: str = "") -> Path:
    """Where a ROM for this platform is filed, under the chosen layout."""
    slug = getattr(platform, "slug", platform)
    name = str(folder_name or slug)
    if (not name or name in (".", "..") or "/" in name or "\\" in name
            or "\x00" in name or name != _canonical_component(name)):
        raise ValueError("platform folder name must be one safe path component")
    base = library_root / name
    if str(layout).lower() in ("nested", "romm_b", "b"):
        base = base / "roms"
    if translation:
        base = base / TRANSLATION_SUBDIR
    return base


def import_rom(download: Path, platform: Platform, library_root: Path, *,
               overwrite: bool = False, dats=None,
               require_verified: bool = False,
               layout: str = "flat", translation: bool = False,
               folder_name: str = "",
               rename: bool = False, switch_index=None,
               route_switch_catalog: bool = False,
               switch_updates_dir: str = "Updates",
               switch_dlc_dir: str = "DLC") -> list[ImportResult]:
    """Place every ROM from a finished download into the library.

    A cartridge zip may hold several games (a 3-in-1 collection, a bundle)
    and every one is imported.  A disc lands as a directory holding every
    file of the set, which is the layout the live library already uses for
    multi-track rips.

    `layout` picks the directory shape (see `platform_dir`); `translation`
    files the set in the platform's Translations subfolder, for the
    keep-both case where a T-En patch sits beside the original dump.
    """
    if not download.exists():
        msg = (
            f"download path does not exist in this container: {download}. "
            "Mount the download client's completed directory at that exact "
            "path, or add a remote path mapping under Settings -> Media "
            "Management.")
        return [ImportResult(False, None, msg)]

    try:
        source = _source_for(download, platform)
        candidates = source.names()
    except (MissingArchiveTool, OSError, ValueError, zipfile.BadZipFile) as exc:
        return [ImportResult(False, None, str(exc))]

    try:
        chosen_sets = pick_all_rom_sets(candidates, platform, read=source.read)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return [ImportResult(False, None, str(exc))]
    if not chosen_sets:
        return [ImportResult(
            False, None,
            f"no {platform.name} ROM found; candidate count: {len(candidates)}.")]

    results: list[ImportResult] = []
    for chosen in chosen_sets:
        verdict = verify_set(source, chosen.members, dats)
        if require_verified and verdict.status != VERIFIED:
            results.append(ImportResult(
                False, None,
                f"refused: {verdict.detail or verdict}",
                verification=verdict))
            continue

        target_dir = platform_dir(library_root, platform,
                                   layout=layout, translation=translation,
                                   folder_name=folder_name)

        if platform.slug == "switch" and route_switch_catalog:
            # TitleDB classifies an ID read from the filename; it does not
            # verify the package header or contents. This routing stays behind
            # an explicit setting and never changes the reported DAT verdict.
            try:
                from .titled import validate_switch_rom
                switch = validate_switch_rom(
                    Path(chosen.primary).name, index=switch_index)
                title = switch.get("title")
                kind = str(getattr(title, "kind", "") or "")
                subdir = (switch_updates_dir if kind == "update" else
                          switch_dlc_dir if kind == "dlc" else "")
                subdir = str(subdir or "").strip()
                if (switch.get("status") == "verified"
                        and kind in ("update", "dlc") and subdir
                        and _canonical_component(subdir) == subdir
                        and "/" not in subdir and "\\" not in subdir):
                    target_dir = target_dir / subdir
            except Exception as exc:
                log.debug("Switch content routing skipped (%s)", type(exc).__name__)

        try:
            with parent_fd(library_root, target_dir / ".check"):
                pass
        except (OSError, ValueError):
            results.append(ImportResult(False, None, "unsafe library directory"))
            continue

        if chosen.preserve_paths:
            results.append(_import_directory_set(
                source, chosen, download, target_dir, library_root,
                overwrite=overwrite, verdict=verdict))
            continue

        if not chosen.is_multi_file:
            original_name = Path(chosen.primary).name
            destination_name = original_name
            if rename and verdict.status == VERIFIED and verdict.game:
                component = _canonical_component(verdict.game)
                if component:
                    destination_name = component + Path(original_name).suffix
            destination = target_dir / destination_name
            if destination_name != original_name and target_dir.is_dir():
                try:
                    collision = next((p for p in target_dir.iterdir()
                                      if p.name.casefold() == destination.name.casefold()
                                      and p.name != original_name), None)
                except OSError:
                    collision = None
                if collision is not None and collision != destination:
                    results.append(ImportResult(
                        False, collision,
                        "canonical DAT name already exists; refusing to overwrite it",
                        verification=verdict))
                    continue
            if destination.exists() and not overwrite:
                results.append(
                    ImportResult(False, destination, "already in the library"))
                continue
            try:
                atomic_file(library_root, destination,
                            lambda output: source.copy(chosen.primary, output),
                            overwrite=overwrite)
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                results.append(ImportResult(False, destination, f"import failed: {exc}"))
                continue
            log.info("imported %s -> %s", chosen.primary, destination)
            results.append(ImportResult(True, destination,
                                        verification=verdict))
            continue

        # A digital set is named after the download, not its primary: every
        # repack's installer is called setup.exe, and a library of
        # directories all named "setup" is a library of nothing.
        set_name = (download.stem if platform.media == "digital"
                    else _set_name(chosen.primary))
        destination = target_dir / set_name
        members, seen = [], set()
        for member in chosen.members:
            name = Path(member.replace("\\", "/")).name
            if not is_safe_name(name, destination) or name.casefold() in seen:
                results.append(ImportResult(False, destination, f"two files in this download are both called {name!r}, or the name is unsafe"))
                break
            seen.add(name.casefold())
            members.append((member, name))
        else:
            try:
                atomic_directory(library_root, destination,
                    lambda stage: source.copy_set(members, stage), overwrite=overwrite)
                results.append(ImportResult(True, destination, verification=verdict))
            except FileExistsError:
                results.append(ImportResult(False, destination, "already in the library"))
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                results.append(ImportResult(False, destination, f"game import failed: {exc}"))

    return results


def _import_directory_set(source, chosen, download, target_dir, library_root,
                          *, overwrite, verdict):
    """Publish a whole game tree only after all files have been copied."""
    root_name = Path(chosen.root.rstrip("/\\")).name if chosen.root else ""
    set_name = root_name or (download.name if download.is_dir() else download.stem)
    destination = target_dir / set_name
    if (not is_safe_name(set_name, target_dir)
            or not destination.resolve().is_relative_to(library_root.resolve())
            or destination.is_symlink()):
        return ImportResult(False, None, "unsafe game directory")
    if destination.exists() and not overwrite:
        return ImportResult(False, destination, "already in the library")
    # Preflight the complete set, including collisions on case-insensitive
    # libraries. Do not leave half a game behind on a rejected member.
    members = []
    seen = set()
    for member in chosen.members:
        name = member.replace("\\", "/")[len(chosen.root):]
        if not is_safe_name(name, destination) or name.casefold() in seen:
            return ImportResult(False, destination, "unsafe or duplicate game file")
        seen.add(name.casefold())
        members.append((member, name))
    try:
        atomic_directory(library_root, destination,
            lambda stage: source.copy_set(members, stage), overwrite=overwrite)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return ImportResult(False, destination, f"game import failed: {exc}")
    return ImportResult(True, destination, verification=verdict)


def _set_name(primary: str) -> str:
    """The directory name a multi-file game gets.

    The primary's stem, because that is the name the sheet carries and the one
    a person recognises. `102 Dalmatians ….gdi` and its five `trackNN.bin`
    files become `102 Dalmatians …/`.
    """
    return Path(primary.replace("\\", "/")).stem


def map_remote_path(path, mappings, client_id=None):
    """Translate a download client's path into one this process can open.

    The client reports paths in ITS filesystem. When it runs in a different
    container the same file has a different path here -- or the volume is not
    mounted at all, which is a mount problem a mapping cannot paper over, and
    the caller finds that out because the translated path still does not exist.

    A mapping with a download-client id applies only to that configured
    client. Client-specific mappings take precedence over shared mappings;
    within either scope the longest matching prefix wins. Entries without an
    id remain shared, preserving existing settings.
    """
    text = str(path)
    best = None
    for entry in mappings or []:
        if not isinstance(entry, dict):
            continue
        mapped_client = str(entry.get("client_id") or "")
        if mapped_client and mapped_client != str(client_id or ""):
            continue
        remote = str(entry.get("remote", "")).rstrip("/\\")
        local = str(entry.get("local", "")).rstrip("/\\")
        if not remote or not local:
            continue
        if text == remote or text.startswith(remote + "/") or text.startswith(remote + "\\"):
            priority = (bool(mapped_client), len(remote))
            if best is None or priority > best[0]:
                best = (priority, remote, local)
    if best is None:
        return _checked(Path(text), text, mapped=False)
    _, remote, local = best
    rest = text[len(remote):].lstrip("/\\")
    return _checked(Path(local) / rest if rest else Path(local), text, mapped=True)


def _checked(result: Path, reported: str, *, mapped: bool) -> Path:
    """Warn, once translation is done, if the result is not openable here.

    This is the only point that knows both paths, and the difference between
    them is the whole diagnosis. Without it the operator sees a download that
    completed and never imported, and nothing that names the container path
    ROMarr actually tried -- which is the one string that makes a wrong volume
    mount obvious.

    A warning rather than a raise: the caller reports the failure per download,
    and one unopenable path must not stop the others importing.
    """
    if not reported or result.exists():
        return result
    if mapped:
        log.warning(
            "download client reported %s, which a remote path mapping turns "
            "into %s -- and that does not exist here. Check the mapping's local "
            "side against what is really mounted.", reported, result)
    else:
        log.warning(
            "download client reported %s, which does not exist here and no "
            "remote path mapping covers it. Mount the client's completed "
            "directory at that exact path, or add a mapping under Settings -> "
            "Media Management.", reported)
    return result
