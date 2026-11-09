"""Handing the library to the launchers people actually sit in front of.

LaunchBox, Playnite and ES-DE are where a lot of people play. None of them
speaks a common protocol, and two of the three are Windows .NET applications
whose plugin model is a compiled DLL -- so the durable integration is not a
plugin at all, it is emitting the formats they already read.

That distinction matters. A plugin breaks when the host application changes
its API; a `gamelist.xml` has been read the same way for fifteen years. The
plugins in `contrib/` are a convenience on top of this module, not a
replacement for it -- and if one of them ever stops working, the export is
still there.

Everything here is a pure function from library rows to text, so all of it is
tested. The plugins are not, because .NET cannot be compiled in this
environment, and that difference is stated in `contrib/README.md` rather than
glossed over.
"""

from __future__ import annotations

import json
import logging
import re
import ntpath
from pathlib import PurePosixPath
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
from pathlib import PurePosixPath

log = logging.getLogger(__name__)

#: ROMarr slug -> the platform name each launcher expects.
#:
#: These are not decoration. LaunchBox and Playnite match their metadata by
#: platform *name*, so a game filed under a name they do not recognise imports
#: with no box art, no description and no association with the rest of that
#: system's library -- it looks like the export half-worked, which is harder to
#: diagnose than a clean failure.
LAUNCHBOX_PLATFORMS = {
    "nes": "Nintendo Entertainment System",
    "famicom": "Nintendo Famicom",
    "fds": "Nintendo Famicom Disk System",
    "snes": "Super Nintendo Entertainment System",
    "sfam": "Super Famicom",
    "n64": "Nintendo 64",
    "gb": "Nintendo Game Boy",
    "gbc": "Nintendo Game Boy Color",
    "gba": "Nintendo Game Boy Advance",
    "nds": "Nintendo DS",
    "3ds": "Nintendo 3DS",
    "ngc": "Nintendo GameCube",
    "wii": "Nintendo Wii",
    "genesis-slash-megadrive": "Sega Genesis",
    "sms": "Sega Master System",
    "gamegear": "Sega Game Gear",
    "sega32": "Sega 32X",
    "segacd": "Sega CD",
    "saturn": "Sega Saturn",
    "dc": "Sega Dreamcast",
    "psx": "Sony Playstation",
    "ps2": "Sony Playstation 2",
    "ps3": "Sony Playstation 3",
    "ps4": "Sony Playstation 4",
    "ps5": "Sony Playstation 5",
    "psvita": "Sony Playstation Vita",
    "psp": "Sony PSP",
    "wiiu": "Nintendo Wii U",
    "xbox": "Microsoft Xbox",
    "xbox360": "Microsoft Xbox 360",
    "xboxone": "Microsoft Xbox One",
    "series-x-s": "Microsoft Xbox Series X/S",
    "atari2600": "Atari 2600",
    "atari5200": "Atari 5200",
    "atari7800": "Atari 7800",
    "lynx": "Atari Lynx",
    "jaguar": "Atari Jaguar",
    "atari-jaguar-cd": "Atari Jaguar CD",
    "3do": "3DO Interactive Multiplayer",
    "colecovision": "ColecoVision",
    "intellivision": "Mattel Intellivision",
    "vectrex": "GCE Vectrex",
    "turbografx16--1": "NEC TurboGrafx-16",
    "turbografx-16-slash-pc-engine-cd": "NEC TurboGrafx-CD",
    "supergrafx": "NEC SuperGrafx",
    "pc-fx": "NEC PC-FX",
    "wonderswan": "WonderSwan",
    "wonderswan-color": "WonderSwan Color",
    "neo-geo-pocket": "SNK Neo Geo Pocket",
    "neo-geo-pocket-color": "SNK Neo Geo Pocket Color",
    "neogeoaes": "SNK Neo Geo AES",
    "neogeomvs": "SNK Neo Geo MVS",
    "neo-geo-cd": "SNK Neo Geo CD",
    "virtualboy": "Nintendo Virtual Boy",
    "amiga": "Commodore Amiga",
    "amiga-cd32": "Commodore Amiga CD32",
    "c64": "Commodore 64",
    "c128": "Commodore 128",
    "vic-20": "Commodore VIC-20",
    "acpc": "Amstrad CPC",
    "zxs": "Sinclair ZX Spectrum",
    "msx": "Microsoft MSX",
    "msx2": "Microsoft MSX2",
    "sharp-x68000": "Sharp X68000",
    "dos": "MS-DOS",
    "arcade": "Arcade",
    "philips-cd-i": "Philips CD-i",
    "apple2": "Apple II",
    "atari8bit": "Atari 800",
    "atari-st": "Atari ST",
    "mac": "Apple Mac OS",
    "cpet": "Commodore PET",
    "sinclair-zx81": "Sinclair ZX-81",
    "sg1000": "Sega SG-1000",
    "odyssey-2-slash-videopac-g7000": "Magnavox Odyssey 2",
    # `palm-os` and `trs-80-mc-10` are absent on purpose: LaunchBox has no
    # platform of its own for either, and an invented name would export tiles
    # that its importer silently drops. They fall back to the slug.
}

#: ES-DE reads a directory per system, named by its own short slug.
ESDE_FOLDERS = {
    "genesis-slash-megadrive": "megadrive",
    "turbografx16--1": "tg16",
    "turbografx-16-slash-pc-engine-cd": "pcenginecd",
    "neo-geo-pocket": "ngp",
    "neo-geo-pocket-color": "ngpc",
    "neogeoaes": "neogeo",
    "neogeomvs": "neogeo",
    "neo-geo-cd": "neogeocd",
    "atari-jaguar-cd": "atarijaguarcd",
    "jaguar": "atarijaguar",
    "philips-cd-i": "cdimono1",
    "sharp-x68000": "x68000",
    "vic-20": "vic20",
    "3do": "3do",
    "sfam": "snes",
    "famicom": "nes",
}


def launchbox_platform(slug: str) -> str:
    """LaunchBox's name for a platform, or the slug when it has none."""
    return LAUNCHBOX_PLATFORMS.get(str(slug or "").lower(), str(slug or ""))


def esde_folder(slug: str) -> str:
    return ESDE_FOLDERS.get(str(slug or "").lower(), str(slug or ""))


def _pretty(root: ET.Element) -> str:
    raw = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8") \
        .decode("utf-8")


def to_launchbox(rows: list[dict]) -> str:
    """A LaunchBox platform XML.

    LaunchBox stores one file per platform under `Data/Platforms/`, and its
    importer reads the same shape. `ApplicationPath` is what it launches, so a
    row with no path is skipped rather than written as an entry that cannot
    start -- a dead tile is worse than a missing one, because it looks like a
    working library until somebody clicks it.
    """
    root = ET.Element("LaunchBox")
    written = 0
    for row in rows:
        path = str(row.get("path") or "").strip()
        if not path:
            continue
        game = ET.SubElement(root, "Game")
        ET.SubElement(game, "ApplicationPath").text = path
        ET.SubElement(game, "Title").text = str(row.get("title") or "")
        ET.SubElement(game, "Platform").text = launchbox_platform(
            row.get("platform"))
        ET.SubElement(game, "ID").text = str(row.get("id") or "")
        if row.get("region"):
            ET.SubElement(game, "Region").text = str(row["region"])
        notes = str(row.get("notes") or "")
        details = []
        if row.get("desc"):
            details.append(str(row["desc"]))
        if row.get("released"):
            details.append(f"Released: {row['released']}")
        if row.get("genres"):
            details.append("Genres: " + ", ".join(map(str, row["genres"])))
        if row.get("matched_by"):
            details.append("ROMarr match: " + str(row["matched_by"]))
        if details:
            notes = "\n".join(part for part in (notes, *details) if part)
        if notes:
            ET.SubElement(game, "Notes").text = notes
        if row.get("desc"):
            ET.SubElement(game, "Overview").text = str(row["desc"])
        if row.get("released"):
            ET.SubElement(game, "ReleaseDate").text = str(row["released"])
        if row.get("genres"):
            ET.SubElement(game, "Genres").text = ", ".join(
                str(value) for value in row["genres"] if str(value))
        if row.get("cover"):
            ET.SubElement(game, "FrontImage").text = str(row["cover"])
        # ROMarr knows something LaunchBox has no field for: whether the file
        # verified against a DAT. It goes in Notes rather than being dropped,
        # because it is the most useful thing in the row.
        if row.get("verified"):
            existing = game.find("Notes")
            note = f"ROMarr: {row['verified']}"
            if existing is None:
                ET.SubElement(game, "Notes").text = note
            else:
                existing.text = f"{existing.text}\n{note}"
        written += 1
    log.info("LaunchBox export: %d of %d rows had a path", written, len(rows))
    return _pretty(root)


def to_gamelist(rows: list[dict]) -> str:
    """An ES-DE / EmulationStation `gamelist.xml` for ONE system.

    Modern ES-DE keeps this file in its data tree and expands relative paths
    against ROMDirectory, so organizer rows provide `esde_path` relative to
    the shared library root. Other callers can provide a system-relative
    `filename`. Media tags remain for older EmulationStation forks; ES-DE
    finds modern media by matching files under its configured media root.
    """
    root = ET.Element("gameList")
    for row in rows:
        name = str(row.get("esde_path") or row.get("relative_path") or row.get("locator") or row.get("filename") or row.get("path") or "").strip()
        if not name:
            continue
        normalized = name.replace("\\", "/")
        relative = normalized[2:] if normalized.startswith("./") else normalized
        if (normalized.startswith("/") or not relative
                or any(part in ("", ".", "..") for part in PurePosixPath(relative).parts)):
            continue
        game = ET.SubElement(root, "game")
        ET.SubElement(game, "path").text = f"./{relative}"
        ET.SubElement(game, "name").text = str(row.get("title") or name)
        if row.get("desc"):
            ET.SubElement(game, "desc").text = str(row["desc"])
        if row.get("region"):
            ET.SubElement(game, "region").text = str(row["region"])
        if row.get("cover_path"):
            ET.SubElement(game, "image").text = str(row["cover_path"])
        if row.get("genres"):
            ET.SubElement(game, "genre").text = ", ".join(map(str, row["genres"]))
        if row.get("released"):
            released = str(row["released"])
            match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2}).*", released)
            if match:
                ET.SubElement(game, "releasedate").text = (
                    f"{match.group(1)}{match.group(2)}{match.group(3)}T000000")
        try:
            rating = float(row.get("rating") or 0)
            source = str(row.get("metadata_source") or "").lower()
            maximum = 5.0 if source == "rawg" else 10.0
            if rating > 0:
                ET.SubElement(game, "rating").text = f"{max(0.0, min(1.0, rating / maximum)):.3f}"
        except (TypeError, ValueError):
            pass
    return _pretty(root)


def to_playnite(rows: list[dict]) -> str:
    """JSON for the Playnite extension in `contrib/`.

    Deliberately flat and explicit. The consumer is a PowerShell script, and
    anything that needs a schema to interpret is a script that breaks the
    first time a field is absent.
    """
    return json.dumps({
        "source": "ROMarr",
        "version": 1,
        "games": [
            {
                "name": str(row.get("title") or ""),
                "platform": launchbox_platform(row.get("platform")),
                "romPath": str(row.get("path") or ""),
                "id": str(row.get("id") or ""),
                "verified": str(row.get("verified") or ""),
                "description": str(row.get("desc") or ""),
                "releaseDate": str(row.get("released") or ""),
                "genres": [str(value) for value in (row.get("genres") or [])],
                "rating": float(row.get("rating") or 0),
                "coverPath": str(row.get("cover_path") or ""),
                "matchedBy": str(row.get("matched_by") or ""),
            }
            for row in rows if row.get("path")
        ],
    }, indent=2)


def romarr_game_document(row: dict) -> dict:
    """Return the versioned, frontend-neutral ROMarr game metadata record."""
    identity_id = str(row.get("identity_id") or row.get("id") or "")
    platform = str(row.get("platform") or "")
    digest = str(row.get("content_sha256") or "")
    if not digest and ":" in identity_id:
        digest = identity_id.rsplit(":", 1)[-1]
    metadata = row.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "format": "org.romarr.game-metadata",
        "schema_version": 1,
        "identity_id": identity_id,
        "identity": {"platform": platform, "sha256": digest},
        "game": {
            "title": str(row.get("canonical_title") or row.get("title") or ""),
            "filename": str(row.get("filename") or ""),
            "region": str(row.get("region") or ""),
        },
        "file": {
            "relative_path": str(row.get("relative_path") or row.get("filename") or ""),
            "is_directory": bool(row.get("is_directory", False)),
        },
        "identification": {
            "confidence": str(row.get("confidence") or row.get("matched_by") or ""),
            "details": str(row.get("match_details") or ""),
            "manual_mapping": bool(row.get("manual_mapping", False)),
            "dat": {
                "name": str(row.get("dat") or ""),
                "status": str(row.get("dat_status") or "unknown"),
                "title": str(row.get("dat_game") or ""),
                "hashes": row.get("hashes") or {},
            },
        },
        "metadata": {
            "summary": str(metadata.get("summary") or row.get("desc") or ""),
            "released": str(metadata.get("released") or row.get("released") or ""),
            "genres": list(metadata.get("genres") or row.get("genres") or []),
            "rating": metadata.get("rating", row.get("rating", 0)),
            "source": str(metadata.get("source") or row.get("metadata_source") or ""),
            "notes": str(row.get("notes") or ""),
            "provider_id": str(metadata.get("provider_id") or ""),
            "matched_by": str(metadata.get("matched_by") or ""),
        },
        "source_fields": dict(row.get("source_fields") or {}),
        "artwork": {"url": str(row.get("cover") or ""), "path": str(row.get("metadata_artwork_path")
                                  or row.get("cover_path") or "")},
        "relationships": {
            "switch": row.get("switch") or {},
            "disc_group": row.get("disc_group") or {},
            "manifests": row.get("manifests") or [],
        },
        "updated_at": str(row.get("updated_at") or ""),
    }


def to_romarr_json(rows: list[dict]) -> str:
    """Export the portable ROMarr metadata catalog, not an app-specific view."""
    return json.dumps({
        "format": "org.romarr.library-catalog",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "games": [romarr_game_document(row) for row in rows],
    }, ensure_ascii=False, indent=2)


class FrontendImportError(ValueError):
    """Invalid or unsupported frontend interchange payload."""


MAX_IMPORT_BYTES = 20 * 1024 * 1024
MAX_IMPORT_ROWS = 200_000
MAX_FIELD_LENGTH = 4096


def safe_relative_locator(value: str, *, source_prefix: str = "") -> str:
    """Normalize a frontend path and refuse traversal or unscoped absolutes."""
    raw = str(value or "").strip().replace("\\", "/")
    if not raw or len(raw) > MAX_FIELD_LENGTH:
        raise FrontendImportError("Each imported game needs a bounded path.")
    drive, _tail = ntpath.splitdrive(raw)
    absolute = raw.startswith("/") or bool(drive)
    if absolute:
        prefix = str(source_prefix or "").strip().replace("\\", "/").rstrip("/")
        prefix_drive, _ = ntpath.splitdrive(prefix)
        if not prefix or (raw != prefix and not raw.startswith(prefix + "/")):
            raise FrontendImportError(
                "Absolute frontend paths require a matching source path prefix.")
        if prefix_drive and raw[:len(prefix)].casefold() != prefix.casefold():
            raise FrontendImportError("The path is outside the supplied source prefix.")
        raw = raw[len(prefix):].lstrip("/")
    parts = [part for part in PurePosixPath(raw).parts if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise FrontendImportError("The imported path escapes its library root.")
    return "/".join(parts)


def _bounded_text(value, *, limit=MAX_FIELD_LENGTH) -> str:
    text = str(value or "").strip()
    text = "".join(ch for ch in text if ch in "\t\n\r" or ord(ch) >= 32)
    if len(text) > limit:
        raise FrontendImportError("An imported field exceeds the supported size.")
    return text


def _bounded_json_value(value, *, depth=0):
    if depth > 5:
        raise FrontendImportError("An unknown source field is nested too deeply.")
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _bounded_text(value, limit=8192)
    if isinstance(value, list):
        if len(value) > 100:
            raise FrontendImportError("An unknown source field has too many values.")
        return [_bounded_json_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > 200:
            raise FrontendImportError("An unknown source field has too many keys.")
        return {_bounded_text(key, limit=128): _bounded_json_value(item, depth=depth + 1)
                for key, item in value.items()}
    raise FrontendImportError("An unknown source field has an unsupported value.")


def _xml_source_fields(node: ET.Element, known: set[str]) -> dict:
    """Keep unrecognized frontend fields as data, with a strict later bound."""
    def value(element, depth=0):
        if depth > 5:
            raise FrontendImportError("An imported XML field is nested too deeply.")
        children = list(element)
        if not children and not element.attrib:
            return element.text or ""
        result = {f"@{key}": item for key, item in element.attrib.items()}
        for child in children:
            item = value(child, depth + 1)
            if child.tag in result:
                previous = result[child.tag]
                result[child.tag] = previous + [item] if isinstance(previous, list) else [previous, item]
            else:
                result[child.tag] = item
        if element.text and element.text.strip():
            result["#text"] = element.text.strip()
        return result

    fields = {}
    for child in list(node):
        if child.tag in known:
            continue
        item = value(child)
        if child.tag in fields:
            previous = fields[child.tag]
            fields[child.tag] = previous + [item] if isinstance(previous, list) else [previous, item]
        else:
            fields[child.tag] = item
    return fields


def _normal_import_row(row: dict, *, source_prefix: str = "") -> dict:
    if not isinstance(row, dict):
        raise FrontendImportError("Each imported game must be an object.")
    platform = _bounded_text(row.get("platform") or row.get("platform_slug"), limit=256)
    title = _bounded_text(row.get("title") or row.get("name"), limit=1024)
    path = row.get("locator") or row.get("relative_path") or row.get("path") \
        or row.get("romPath")
    locator = safe_relative_locator(path, source_prefix=source_prefix)
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    genres = row.get("genres", metadata.get("genres", []))
    if isinstance(genres, str):
        genres = [part.strip() for part in genres.split(",") if part.strip()]
    if not isinstance(genres, list) or len(genres) > 100:
        raise FrontendImportError("Genres must be a bounded list of text values.")
    safe_genres = [_bounded_text(value, limit=128) for value in genres]
    known = {"id", "platform", "platform_slug", "title", "name", "locator",
             "relative_path", "path", "romPath", "metadata", "genres", "desc",
             "description", "released", "releasedate", "rating", "region",
             "cover", "image", "notes", "verified", "source_fields"}
    supplied_source_fields = row.get("source_fields")
    if not isinstance(supplied_source_fields, dict):
        supplied_source_fields = {key: value for key, value in row.items()
                                  if key not in known}
    if len(supplied_source_fields) > 200:
        raise FrontendImportError("Too many unknown source fields.")
    safe_source_fields = {}
    for key, value in supplied_source_fields.items():
        safe_key = _bounded_text(key, limit=128)
        safe_source_fields[safe_key] = _bounded_json_value(value)
    external_id = _bounded_text(row.get("id"), limit=256)
    if external_id and "romarr_external_id" not in safe_source_fields:
        safe_source_fields["romarr_external_id"] = external_id
    if len(json.dumps(safe_source_fields, ensure_ascii=False)) > 65536:
        raise FrontendImportError("Unknown source fields exceed the 64 KiB per-game limit.")
    try:
        rating = float(row.get("rating", metadata.get("rating", 0)) or 0)
    except (TypeError, ValueError):
        rating = 0
    if not 0 <= rating <= 10:
        rating = 0
    return {
        "external_id": external_id,
        "platform": platform,
        "title": title,
        "locator": locator,
        "metadata": {
            "summary": _bounded_text(row.get("desc") or row.get("description")
                                      or metadata.get("description")),
            "released": _bounded_text(row.get("released") or row.get("releasedate")
                                       or metadata.get("released"), limit=64),
            "rating": rating,
            "genres": safe_genres,
            "region": _bounded_text(row.get("region") or metadata.get("region"), limit=128),
            "cover_url": _bounded_text(row.get("cover") or row.get("image")
                                        or metadata.get("cover"), limit=2048),
            "notes": _bounded_text(row.get("notes") or metadata.get("notes")),
        },
        "source_fields": safe_source_fields,
    }


def parse_frontend_import(name: str, payload: str, *,
                          source_prefix: str = "") -> list[dict]:
    """Read a supported frontend export without touching ROM paths or files."""
    profile = str(name or "").strip().lower()
    text = str(payload or "")
    if len(text.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise FrontendImportError("The import exceeds the 20 MiB limit.")
    rows: list[dict]
    if profile in ("romarr-json", "playnite"):
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as err:
            raise FrontendImportError("The JSON export is invalid.") from err
        if profile == "romarr-json":
            if isinstance(doc, dict) and doc.get("format") == "org.romarr.library-catalog":
                if doc.get("schema_version") != 1 or not isinstance(doc.get("games"), list):
                    raise FrontendImportError("Unsupported ROMarr catalog schema.")
                if len(doc["games"]) > MAX_IMPORT_ROWS:
                    raise FrontendImportError("The catalog contains too many games.")
                rows = []
                for game in doc["games"]:
                    if not isinstance(game, dict):
                        raise FrontendImportError("Each catalog game must be an object.")
                    try:
                        rows.append({
                            "id": game.get("identity_id"),
                            "platform": game["identity"]["platform"],
                            "title": game["game"]["title"],
                            "locator": game["file"]["relative_path"],
                            "desc": game["metadata"].get("summary"),
                            "metadata": game["metadata"],
                            "cover": game.get("artwork", {}).get("url"),
                            "source_fields": game.get("source_fields", {}),
                        })
                    except (KeyError, TypeError, AttributeError) as exc:
                        raise FrontendImportError("Malformed ROMarr catalog game.") from exc
                doc = {"format": "romarr.frontend-exchange", "version": 1, "games": rows}
            if (not isinstance(doc, dict)
                    or doc.get("format") != "romarr.frontend-exchange"):
                raise FrontendImportError("This is not a ROMarr frontend exchange file.")
            if doc.get("version") != 1:
                raise FrontendImportError("This ROMarr exchange version is unsupported.")
            rows = doc.get("games") or []
        else:
            if (not isinstance(doc, dict) or doc.get("source") != "ROMarr"):
                raise FrontendImportError("This is not a supported ROMarr Playnite export.")
            if doc.get("version") != 1:
                raise FrontendImportError("This Playnite export version is unsupported.")
            rows = doc.get("games") or []
    elif profile in ("gamelist", "esde", "emulationstation", "launchbox"):
        if re.search(r"<!\s*(DOCTYPE|ENTITY)\b", text, flags=re.IGNORECASE):
            raise FrontendImportError("XML declarations with document types or entities are not accepted.")
        try:
            root = ET.fromstring(text)
        except ET.ParseError as err:
            raise FrontendImportError("The XML export is invalid.") from err
        nodes = list(root.iter())
        if len(nodes) > MAX_IMPORT_ROWS * 12:
            raise FrontendImportError("The XML export contains too many fields.")
        if profile in ("gamelist", "esde", "emulationstation"):
            if root.tag != "gameList":
                raise FrontendImportError("Expected an EmulationStation gameList document.")
            rows = []
            for node in root.findall("game"):
                known = {"path", "name", "platform", "desc", "releasedate",
                         "rating", "region", "genre", "image"}
                rows.append({
                    "title": node.findtext("name") or "",
                    "platform": node.findtext("platform") or "",
                    "locator": node.findtext("path") or "",
                    "desc": node.findtext("desc") or "",
                    "released": node.findtext("releasedate") or "",
                    "rating": node.findtext("rating") or 0,
                    "region": node.findtext("region") or "",
                    "genres": node.findtext("genre") or "",
                    "cover": node.findtext("image") or "",
                    "source_fields": _xml_source_fields(node, known),
                })
        else:
            if root.tag != "LaunchBox":
                raise FrontendImportError("Expected a LaunchBox document.")
            rows = []
            for node in root.findall("Game"):
                known = {"ID", "Title", "Platform", "ApplicationPath",
                         "Overview", "ReleaseDate", "Region", "Genres",
                         "FrontImage", "Notes"}
                rows.append({
                    "id": node.findtext("ID") or "",
                    "title": node.findtext("Title") or "",
                    "platform": node.findtext("Platform") or "",
                    "path": node.findtext("ApplicationPath") or "",
                    "desc": node.findtext("Overview") or "",
                    "released": node.findtext("ReleaseDate") or "",
                    "region": node.findtext("Region") or "",
                    "genres": node.findtext("Genres") or "",
                    "cover": node.findtext("FrontImage") or "",
                    "notes": node.findtext("Notes") or "",
                    "source_fields": _xml_source_fields(node, known),
                })
    else:
        raise FrontendImportError("Supported imports are ROMarr JSON, gamelist.xml and LaunchBox XML.")
    if not isinstance(rows, list) or len(rows) > MAX_IMPORT_ROWS:
        raise FrontendImportError(f"Imports support at most {MAX_IMPORT_ROWS:,} games.")
    normalized = [_normal_import_row(row, source_prefix=source_prefix) for row in rows]
    seen = set()
    for row in normalized:
        if row["locator"] in seen:
            raise FrontendImportError(
                "The frontend file contains duplicate paths; resolve them before importing.")
        seen.add(row["locator"])
    return normalized


FORMATS = {
    "launchbox": {"label": "LaunchBox", "render": to_launchbox,
                  "content_type": "application/xml; charset=utf-8",
                  "filename": "LaunchBox.xml", "version": 1},
    "gamelist": {"label": "ES-DE / EmulationStation", "render": to_gamelist,
                 "content_type": "application/xml; charset=utf-8",
                 "filename": "gamelist.xml", "version": 1},
    "esde": {"label": "ES-DE gamelist.xml", "render": to_gamelist,
             "content_type": "application/xml; charset=utf-8",
             "filename": "gamelist.xml", "version": 1},
    "emulationstation": {"label": "EmulationStation gamelist.xml",
                         "render": to_gamelist,
                         "content_type": "application/xml; charset=utf-8",
                         "filename": "gamelist.xml", "version": 1},
    "playnite": {"label": "Playnite", "render": to_playnite,
                 "content_type": "application/json; charset=utf-8",
                 "filename": "romarr-playnite.json"},
    "romarr-json": {"label": "ROMarr portable metadata JSON",
                    "render": to_romarr_json,
                    "content_type": "application/json; charset=utf-8",
                    "filename": "romarr-library-catalog.json"},
}

IMPORT_FORMATS = {
    "romarr-json": {"label": "ROMarr lossless exchange", "version": 1},
    "gamelist": {"label": "ES-DE / EmulationStation gamelist.xml", "version": 1},
    "playnite": {"label": "Playnite (ROMarr export)", "version": 1},
    "launchbox": {"label": "LaunchBox XML", "version": 1},
}
