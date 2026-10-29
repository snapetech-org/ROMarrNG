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
        name = str(row.get("esde_path") or row.get("filename") or row.get("path") or "").strip()
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
            "provider_id": str(metadata.get("provider_id") or ""),
            "matched_by": str(metadata.get("matched_by") or ""),
        },
        "artwork": {"path": str(row.get("metadata_artwork_path")
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


FORMATS = {
    "launchbox": {"label": "LaunchBox", "render": to_launchbox,
                  "content_type": "application/xml; charset=utf-8",
                  "filename": "LaunchBox.xml"},
    "gamelist": {"label": "ES-DE / EmulationStation", "render": to_gamelist,
                 "content_type": "application/xml; charset=utf-8",
                 "filename": "gamelist.xml"},
    "playnite": {"label": "Playnite", "render": to_playnite,
                 "content_type": "application/json; charset=utf-8",
                 "filename": "romarr-playnite.json"},
    "romarr-json": {"label": "ROMarr portable metadata JSON",
                    "render": to_romarr_json,
                    "content_type": "application/json; charset=utf-8",
                    "filename": "romarr-library-catalog.json"},
}
