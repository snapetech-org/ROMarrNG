# Shared library identification

ROMarr can manage an existing ROM folder without making the ROM names the metadata database. Set the existing ROM library root under **Settings → Media Management**, then choose a separate shared metadata root. The same folder path can be exposed to every client machine through your NAS or container mounts.

~~~text
/emulation/
  roms/
    snes/
      Chrono Trigger.sfc
    switch/
      The Legend of Zelda - Tears of the Kingdom [0100...].xci
  metadata/
    snes/
      catalog.json
      artwork/
        <content-sha256>.jpg
      Chrono Trigger--<sha256-prefix>/
        metadata.json
    switch/
      catalog.json
      artwork/
        <content-sha256>.jpg
~~~

Set **LIBRARY_PATH=/emulation/roms** and **ROMARR_METADATA_PATH=/emulation/metadata**, or enter those paths in Media Management. Mount the shared metadata folder at the same relative location on each client. The metadata root must be outside the ROM library root. It holds one consolidated catalog per platform, one compact metadata.json sidecar per game, and content-addressed artwork. Sidecar folder names use the canonical title plus a short content hash, so duplicate regional entries do not overwrite each other.

## Identify, review, organize

1. Open **Library → Identify & Organize** and scan all platforms or one platform at a time.
2. ROMarr hashes files with bounded memory. If a DAT is loaded, an exact checksum match supplies the canonical title. Configured metadata providers can suggest descriptions, release dates, genres, ratings and artwork for other titles.
3. Review the evidence shown beside each result. A provider suggestion or filename-derived match is not treated as verified. Enter a canonical title to confirm an ambiguous or unmatched game.
4. Preview renames. The plan contains only exact DAT matches and manually confirmed titles. It refuses occupied destinations and rechecks each file's content immediately before moving it. Cue, playlist and other referenced disc files are left in place to avoid breaking multi-file sets.
5. Apply the preview to rename files. ROMarr journals every move and exposes a checked undo for the latest batch. A changed file or an occupied original path stops undo.
6. Select one platform and publish its ES-DE gamelist. Existing entries are merged and preserved. The image references point to the shared artwork folder relative to the ROM system directory.

A scan is read only. Provider lookups are capped at 200 per scan to avoid hammering a catalog; run another scan to continue through a larger library. Refresh metadata rechecks cached matches. When a title moves, ROMarr reuses the record keyed by platform and full-file SHA-256, updates its path, and keeps its cached artwork.

## Evidence and Switch versions

| Evidence | Meaning | Rename eligible |
| --- | --- | --- |
| DAT checksum verified | File bytes match a loaded No-Intro or Redump entry | Yes |
| Manually confirmed | The operator confirmed the canonical title | Yes |
| TitleDB ID match | A 16-hex title ID in the filename is present in TitleDB | No, until manually confirmed |
| Provider suggestion | A metadata provider found a likely title | No, until manually confirmed |
| Filename only / ambiguous | No strong match was found | No, until manually confirmed |

For Switch, ROMarr extracts the title ID and optional vNNNNN filename version, then uses TitleDB to classify a likely base title, update or DLC and compare a labeled version with the latest catalog version. An update or DLC can be routed under platform-specific Updates and DLC folders when **Route Switch updates and DLC by TitleDB filename ID** is enabled. Title IDs, version labels and routing do not verify package contents. A manual confirmation is required before a Switch file becomes eligible for a rename.

The Switch catalog groups IDs by their shared base title ID. This identifies a likely family; it does not prove that the package contains the matching update or DLC.

## Frontends and requests

The same cached metadata can feed the existing LaunchBox, ES-DE and Playnite exports. ES-DE data can also be written into each selected platform's gamelist.xml while preserving records that ROMarr does not own. For shared household requests, use [SeerrNG](https://github.com/snapetech-org/seerrng); ROMarr handles acquisition, checksum verification, metadata and filing, while SeerrNG is the user-facing request queue.

Folder-layout differences matter: ROMarr exports ES-DE paths relative to each platform's ROM folder, with artwork paths traversing to the shared metadata mount. If your frontends mount the two roots at different relative locations, point ES-DE to the exported paths or adjust the mounts to preserve that relationship.

Files in the same platform folder with explicit Disc 1 / Disc 2, Disk 1 / Disk 2, or CD 1 / CD 2 labels are shown as one likely multi-disc set in Identify & Organize. Manual title mapping applies to the whole detected set. The underlying files stay separate and are not renamed individually, because an emulator's playlist and disc-switch conventions vary by platform.

