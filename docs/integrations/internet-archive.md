# Internet Archive

ROMarrNG can search Internet Archive software records as an indexer. Results
appear alongside Prowlarr, Torznab and ROM Hub results in Interactive Search
and use the existing Direct HTTP download and import path.

## Configure it

1. Open **Settings → Indexers → Add**.
2. Choose **Internet Archive** and save. No URL or API key is required.
3. Configure **Direct HTTP** under **Settings → Download Clients** with a
   writable download directory.
4. Search for a game. Each result links to its Internet Archive item page; use
   **Grab** to queue the download.

Single-file ROMs and archive files are queued as direct downloads. CUE, GDI,
CCD, MDS and M3U disc sets are downloaded into one staging directory so their
companion files stay together for ROMarr's normal import and DAT checks.

## Search and access

Search uses Archive.org's Advanced Search API to find software items, then
reads each item's public metadata and file list. It matches the requested game
against the item title or an eligible file name. Archive metadata search does
not search every file inside every item, so it cannot discover files whose
item metadata and file names do not identify the game.

ROMarr omits items marked dark, private, no-download or access-restricted, and
filters file entries explicitly marked private. Direct HTTP checks Archive.org's
robots.txt, waits between requests, and stops on an HTTP 403. If Archive.org
does not provide a file to the server, the grab is reported as failed instead
of attempting another access path.
