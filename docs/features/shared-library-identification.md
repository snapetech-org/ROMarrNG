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

Set **LIBRARY_PATH=/emulation/roms** and **ROMARR_METADATA_PATH=/emulation/metadata**, or enter those paths in Media Management. Mount the shared metadata folder at the same relative location on each client. The metadata root must be outside the ROM library root. It holds one consolidated catalog per platform, one compact metadata.json sidecar per game, and content-addressed artwork. Sidecar folder names use the canonical title plus a short content hash, so duplicate regional entries do not overwrite each other. Shared catalogs and sidecars are ROMarr's working records; the portable export described below is a versioned exchange format.

## Reuse an existing ES-DE library

On the first scan, ROMarr looks for `gamelist.xml` in the selected platform's ROM folder, its nested `roms/` folder, or the matching platform folder under the configured metadata root. Entries are joined to games by their existing `path`, after resolving that path to a file or game folder inside the configured ROM root. ROMarr imports the ES-DE name, description, release date, genres, rating, and local image. It copies valid local images into shared, content-addressed artwork storage so the metadata remains usable from the other machines mounting that root.

This is a local bootstrap. ROMarr does not fetch an image URL found in XML, and skips paths that point outside either configured root, traverse symlinks, or no longer resolve to an existing game. Gamelists are size and entry bounded; DTD and entity declarations are rejected. The source `gamelist.xml` is not modified by scanning.

Imported details and artwork suppress an online metadata lookup for that game during an ordinary scan. A forced **Refresh metadata** scan can query providers; imported ES-DE fields still take precedence in the merged record. An exact DAT match remains the strongest title source, and a local/provider suggestion still needs manual title confirmation before it can authorize a rename. ROMarr caps online lookups at 200 per scan and continues deferred lookups on later scans.

## Identify, review, organize

1. Open **Library → Identify & Organize** and scan all platforms or one platform at a time.
2. ROMarr hashes files with bounded memory. If a DAT is loaded, an exact checksum match supplies the canonical title. Configured metadata providers can suggest descriptions, release dates, genres, ratings and artwork for other titles.
3. Review the evidence shown beside each result. A provider suggestion or filename-derived match is not treated as verified. Enter a canonical title to confirm an ambiguous or unmatched game.
4. Preview renames. The plan contains only exact DAT matches and manually confirmed titles. It refuses occupied destinations and rechecks each file's content immediately before moving it. Cue, playlist and other referenced disc files are left in place to avoid breaking multi-file sets. The page reviews libraries in batches of 200 records; the API accepts batches from 1 to 500. Apply one batch, then continue to the next. Each batch has its own preview token and is revalidated before any move.
5. Apply the preview to rename files. ROMarr journals every move and exposes a checked undo for the latest batch. A changed file or an occupied original path stops undo.
6. Select one platform and publish its ES-DE gamelist. Existing entries are merged and preserved. The image references point to the shared artwork folder relative to the ROM system directory.

A scan is read only. Provider lookups are capped at 200 per scan to avoid hammering a catalog; run another scan to continue through a larger library. Refresh metadata rechecks cached matches. When a title moves, ROMarr reuses the record keyed by platform and full-file SHA-256, updates its path, and keeps its cached artwork. A library scan itself is capped at 50,000 entries; select a platform and scan again when the safety limit is reached.

## Portable metadata

Open **System → Backup & Export** and choose **ROMarr portable metadata JSON** in the frontend export row. The download is a library snapshot using `org.romarr.library-catalog`, schema version `1`. Each item uses `org.romarr.game-metadata`, schema version `1`. The catalog contains the game's platform and content identity, current relative path, identification evidence, descriptive metadata, artwork location, Switch and multi-disc relationships, and the record update time.

The JSON Schema files are [the game record](../schemas/romarr-game-metadata-v1.schema.json) and [the catalog](../schemas/romarr-library-catalog-v1.schema.json). `identity_id` is the platform slug plus a SHA-256 identity digest. `file.relative_path` is relative to the ROM root; `artwork.path` is relative to the metadata root. For folder-based game packages, the digest identifies the package tree. The export is an exchange/download format; importing it into ROMarr is not currently supported.

The per-game `metadata.json` sidecar uses the same versioned game document. It travels with the shared metadata root and can be consumed without depending on ES-DE's private storage layout. Sidecar paths and portable catalog paths remain relative so that machines can mount the roots at different absolute locations.

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

Files in the same platform folder with explicit Disc 1 / Disc 2, Disk 1 / Disk 2, or CD 1 / CD 2 labels are shown as one likely multi-disc set in Identify & Organize. Local M3U playlists with at least two valid references also form a likely set; CUE, GDI, and TOC references are recorded and shown in the inventory so their linked track files are clear. Manifest parsing is bounded to 1 MiB and 256 local references. URLs, symlinks, and references that leave the platform folder are ignored. Manual title mapping applies to the whole detected set. The underlying files stay separate and are not renamed individually, because an emulator's playlist and disc-switch conventions vary by platform.

