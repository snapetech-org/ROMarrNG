# Compatibility contract

**Confidence:** high for inspected current adapter shapes and explicitly cited protocol facts; moderate for proposed extension choices; unknown for untested backend/version combinations. A badge saying “supported” must name the operation and tested version. Do not infer emulation support, metadata writeback or scan completion from a healthy HTTP endpoint.

## C1. Capabilities, not product-name assumptions

Each configured adapter exposes a safe capability projection with `supported`, `unsupported`, `unverified` or `temporarily_unavailable`, a reason, observed server/API version and `lastTestedAt`. Separate availability from support: a supported but offline backend is not an unsupported integration. Library health distinguishes endpoint authentication, listing, complete pagination, platform mapping, art access, rescan initiation/status, local path visibility and writeability.

Optional adapter capabilities include `listGames`, `stableIds`, `listSystems`, `pagedSnapshot`, `countPrecision`, `metadataRead`, `metadataRefresh`, `metadataWrite`, `artworkRead`, `rescan`, `rescanStatus`, `localAssetResolution`, `importLayout`, `launchLink`, and file-specific playability. Existing adapters without declarations receive conservative inferred basics from the old protocol, not optimistic advanced support.

| Backend / route | Current starting point | Required work and qualification |
| --- | --- | --- |
| Plain folder | Walks files and emits basic `Game` rows | Explicit single/mixed roots, grouping, durable identity/enrichment, sidecar read support, bounded snapshots, confirmed import layout. Core supported route independent of other services. |
| RomM | Existing client and rich `Game` projection | Pin tested API versions/shapes; normalize source platform IDs/slugs, preserve metadata IDs, test auth expiry/pagination and authenticated covers. Probe rescan capability; a rescan request accepted is not metadata completion. |
| Gaseous | Existing session-based adapter | Qualify POST-list filter shape, cookie lifecycle, IDs, pagination, incomplete metadata and cover auth. No invented writeback endpoint. |
| Retrom | Existing grpc-web adapter | Qualify framing/schema/version, stable IDs, paging and incomplete fields. Graceful unsupported capability if server changes. |
| Gameyfin | Current implementation subclasses FolderLibrary | Describe current support as folder integration. Recheck the current upstream API before adding any native adapter; do not repeat the old code comment as an eternal claim that no API exists. |
| Third-party backend plugins | Existing optional loader and Library protocol | Preserve baseline protocol and confinement; explicit optional capability negotiation; old plugin fixtures remain loadable. Never execute a new plugin merely to browse a catalog. |
| ES-DE / EmulationStation families | Existing export plus folder integration | Qualified format/version profiles and explicit metadata root; do not assume all forks share `gamelist.xml` location or tag semantics. |
| LaunchBox / Playnite | Existing frontend exports and companion integrations | Round-trip IDs/paths safely with fixtures; separate server paths from desktop paths. Do not invoke arbitrary local commands from imported metadata. |
| Batocera, RetroPie, Recalbox, EmuDeck, RetroDECK, Lakka, muOS, ArkOS, Pegasus, Steam ROM Manager | Filesystem/interchange opportunities, not a claim of native API parity | Start from explicit folder/layout profiles and documented exports. Qualify each advertised profile independently. Add a native API only where real, versioned and needed. |

Adapters should return typed errors for auth rejection, endpoint/version mismatch, unsupported operation, timeout, malformed upstream response and partial scan. Strip provider bodies/headers from public errors. Preserve last-good data and provide retry/repair rather than collapsing these to an empty library.

## C2. File, layout and system compatibility

Maintain capability by **system × file/media form × action**. Scan support, hash verification, archive extraction, import and playback differ. Recognizing a format is not permission to unpack it or evidence an emulator can run it.

| Fixture family | Required behavior |
| --- | --- |
| Cartridge files plus ZIP/7z/RAR | Identify system using scoped evidence; preserve archives where the platform requires it; use existing archive tools with clear optional-tool errors. |
| ISO, BIN/CUE, CHD, CCD/IMG/SUB, MDS/MDF | Group supported descriptors/companions without orphaning tracks; shared extensions stay ambiguous. Unsupported descriptor formats remain explicit, not silently dropped or claimed verified. |
| M3U and multi-disc titles | Validate relative references inside approved roots, detect cycles/missing discs, one logical item with disc completeness and optional per-disc display. |
| Arcade MAME/FBNeo | Preserve archive-as-ROM behavior and parent/clone/BIOS dependencies; a ROMset ZIP is not generic extraction input. Report set/version constraints. |
| PSP PBP/CSO, GameCube/Wii compressed images, other existing compressed forms | Respect current importer/sniffer support per format. Display unsupported conversion/verification independently; do not transcode during a scan. |
| PS3 directory dumps and newer-console packages | Preserve full directory structure and generation-specific metadata; `.pkg` alone is not a platform. Keep existing key/decryption prerequisites and support boundaries visible. |
| Switch base/update/DLC | Preserve TitleDB identity, content kind and version relationships; do not treat filename/version matching as DAT checksum verification. |
| Patches, translations, hacks, homebrew | Preserve base/patch/variant identity and translation/region policy. Unknown-to-DAT is not automatically a bad dump or an excluded game. |
| BIOS/support files | Identify as support assets when evidence exists; exclude from game counts by role, not a fragile filename guess. |
| Unknown extension or unsupported system | Show inventory diagnostics and optional opaque entry where useful; block unsupported acquire/import/play actions explicitly. |

Test mixed and single roots, RomM A/B layouts, nested genre folders, discs in subdirectories, files directly in root, overlapping roots, identical names across platforms, Unicode/NFC/NFD, punctuation, long names, case-sensitive and insensitive storage, hidden directories, symlinks and unreadable files. Exclude importer staging paths and avoid recursive symlink traversal. Root containment must be checked at read/write time, including races; a validated preview does not authorize a later path outside the root.

Cross-container paths use explicit mappings. Retain client-specific completed-download mapping from `library.map_remote_path()`. Display client-reported source path and ROMarrNG destination independently. Detect shared/overlapping destinations and ambiguous routing before dispatch. Windows drive/UNC paths are mapping inputs, not Linux paths that become valid by swapping slashes. Read-only scan mounts must not require write access; import/sidecar export requires its own tested target.

## C3. Metadata and frontend interchange

Reuse existing IGDB/RAWG transports first. Broader provider support is an adapter roadmap with capability/ID/platform mapping/terms/rate-limit fixtures before release; do not make ScreenScraper, TheGamesDB, LaunchBox databases or another provider a mandatory dependency. Local sidecars and metadata already supplied by a backend should work without a cloud account.

Start with read/import of explicitly selected `gamelist.xml` profiles and the application's own versioned JSON interchange; preserve unknown XML tags when round-tripping supported files. Reuse existing LaunchBox XML and Playnite JSON exporters, extend fields only after fixture tests. Map title, description, genre, year/date precision, region/language and art path/ID with provenance. Import external IDs only when their namespace is known. Existing user-edited sidecars are never overwritten by scanning/enrichment.

Path/art references are relative to an explicitly configured ROM/metadata/media root. ES-DE's metadata location can differ from a ROM folder and varies across profiles; do not hard-code a universal sibling-file lookup. Use `defusedxml`, entity/DTD rejection, input/node/depth bounds and root containment. ZIP list bundles and artwork packs get traversal/decompression limits. CSV/JSON imports validate encoding, row caps, schemas and external URLs; export CSV must prevent formula execution when opened in a spreadsheet.

Export is a previewed operation with chosen profile, destination, overwrite/conflict policy and backup. Sanitize path-sensitive names but retain original titles as data. Unchanged resync must be idempotent. No automatic bidirectional loop: source fingerprints and write provenance prevent reading an exported file as a fresh user override forever.

## C4. qBittorrent authentication

Official documentation states that API-key authentication is available from qBittorrent 5.2.0 / WebAPI 2.14.1. It uses `Authorization: Bearer`; API keys do not authenticate `auth/login` or `auth/logout`. A rotated key invalidates the old one. Legacy versions continue to need the existing session path. These are verified protocol facts; the user's actual installed version is unknown. [Source Q1](#primary-sources).

Implementation contract:

1. Add `auth_mode` (`session`, `api_key`, explicit existing bypass mode) and secret `api_key` to `QbitConfig`, download-client schema, builders, config validation and connection tests. Missing mode on an old config preserves its current behavior. Do not silently turn a failed credential into anonymous access.
2. Add environment support using the existing prefix: `QBITTORRENT_API_KEY` and, if needed, `QBITTORRENT_AUTH_MODE`. For new env config, an explicit mode wins; a sole key implies API-key mode; ambiguous supplied credentials produce an actionable validation result. Environment-to-stored seeding and direct construction must agree.
3. API-key mode sends Bearer on version, WebAPI-version and torrent calls through one request helper. Skip login/logout and cookie-refresh retries. Never fallback to a password/bypass after a bad key. Rotation updates the session/client atomically and clears obsolete auth state.
4. Session mode retains requests' cookie jar, current 200 `Ok.` and 204 success handling, 200 `Fails.` rejection and one bounded reauthentication. Test cookie attributes/names without assuming the cookie is literally `SID`; do not reconstruct cookies from the URL port.
5. Connection test uses read-only endpoints. Report selected auth mode, authenticated version/API version when observable, category/path capabilities and safe failure. Do not diagnose “old version” from an unauthorized response whose version could not be read. A known older server gets upgrade-or-use-session guidance.
6. Preserve base URL path prefixes, HTTPS verification/custom CA options if supported, timeout/category/save path, completed-file matching and existing excluded-file repair. Check same-origin redirect behavior; no credential forwarding across hosts/schemes. Reverse-proxy Basic auth and backend Bearer may compete for `Authorization`; expose the incompatibility or a separately documented proxy route rather than combining malformed headers.
7. Extend all secret handling: `merge_secrets`, `redact`, safe settings, schema secret type, environment seed, backups/restores, logs, exceptions, diagnostics and UI form redisplay. Omitting/masking a secret preserves it; an explicit clear is distinct. Never put the key in a URL or browser-visible download link.
8. Uncertain POST completion is reconciled before replay. Do not generalize the existing 401/403 session retry into retries after arbitrary timeouts, redirects or 5xx responses.

Qualification matrix: old username/password session; new session; supported API key; invalid/revoked key; known unsupported version; unknown version with auth failure; rotated key; expired cookie; localhost bypass as explicitly configured; prefixed reverse proxy; HTTPS/custom CA; cross-origin redirect; masked edit and backup/restore. Mocked protocol tests are necessary but a live old/new client smoke test is required for the support matrix.

## C5. Provider traffic and network boundaries

IGDB currently documents four requests per second and at most eight open requests. Reuse the existing shared limiter for discovery, enrichment and catalog ingestion so their combined traffic respects the credential limit; do not allocate a separate full quota to each worker. [Source I1](#primary-sources). Apply provider-specific throttles, bounded concurrent calls, timeout budgets, retry jitter and an identifiable client where required. Rate or credential failures must pause affected work without stalling the whole library.

Separate two outbound trust classes:

- **Configured operator services:** private/LAN library, client, indexer and proxy endpoints are legitimate; validate scheme/origin and keep credentials within that configured boundary.
- **Provider/list/artwork URLs:** untrusted data must not reach loopback, private/link-local/cloud metadata endpoints or arbitrary ports by default. Validate resolution and every redirect, including DNS-rebinding protections at connection time; allow only explicit operator-configured origin exceptions when necessary. Do not globally forbid LAN services to fix SSRF in artwork.

No catalog description/sidecar HTML is rendered unsanitized. Bind every object operation to current authenticated operator/integration scope; opaque IDs are not authorization. SeerrNG's scoped key remains limited to its current prefixes and approved delivery; no private filesystem path, cookie, credential, raw download URL or arbitrary file fetch appears in new catalog/detail/shared DTOs. Admin-only diagnostic paths should still be redacted in exported support bundles. Existing plugin confinement and archive boundaries remain mandatory.

## C6. API and ecosystem compatibility

- Keep SeerrNG request contract v2 and legacy prefix behavior, DAT key derivation, policy selection, exact-system release dates, cancellation/idempotency and scoped asset access. Run the existing contract fixture/tests after identity/ownership work. New operator features must not unconditionally change catalog counts/semantics returned to old clients.
- Keep `/api/platforms` authoritative and complete for importable systems. Add UI taxonomy/interests in a separate projection or additive fields. Never filter integration support according to an operator's interests.
- Reuse actual-file playability rules in `playability.py`, host readiness and existing frontend links. Test format, BIOS/core/host availability and cloud-versus-local status; do not promise that every PS1/PS2 file is playable in a browser.
- Preserve Prowlarr/direct Torznab/Newznab/RSS/Hub source contracts and existing release scoring. Improve diagnostics and fair query budgeting without exposing private download URLs.
- Browser acquisition remains optional. For issue #59, publish a versioned deployment recipe, selected Playwright client/server compatibility policy, endpoint test and upgrade procedure based on qualified versions. Do not bundle a mandatory browser into the base image or claim an arbitrary server/client pair interoperates.
- Respect existing OIDC/session/API-key gates, same-origin protections and auth recovery. Guided setup adds no public configuration route.

## C7. Deployment qualification

| Environment | Required evidence |
| --- | --- |
| Container Linux amd64/arm64 | Base image start, persistent state/SQLite, file access, source-root modes, ordinary acquire/import and safe upgrade/rollback. |
| armv7 image | Same core behavior with bounded memory and working SQLite/dependencies; reduced worker/cache defaults may be needed. No unsupported claim from amd64 tests alone. |
| Unraid | PUID/PGID and mappings, spaces/case, read-only scan versus writable import, restart and explicit Browser optional setup. |
| Docker Compose, LXC, source install, Home Assistant packaging | Existing entry points/environment behavior, data path, optional tools and graceful missing features. Qualify actual available packaging; do not reintroduce removed packages. |
| SMB/NFS ROM storage | Scan interruption, slow traversal, file changes, case/Unicode, no double counting, no destructive “missing” on outage. Keep application database on a qualified persistent state volume. |
| HTTPS/reverse proxy | Path prefix, cookies, authenticated artwork, origin handling, redirects and no mixed-content dependency for covers. |
| Desktop frontends on Windows/macOS/Linux | Explicit exported path mapping/profile and fixture round trips; no claim that the server is installed natively everywhere. |

The matrix records app version, backend version, OS/architecture, protocol, tested operations, date and evidence link. “Implemented” and “runtime-qualified” are separate columns. Unknown combinations get actionable diagnostics and no fabricated green status.

## Primary sources

Reviewed during planning on 2026-10-27; recheck at implementation because protocols and provider limits change.

- **Q1:** [qBittorrent API-key authentication](https://github.com/qbittorrent/qBittorrent/wiki/API-Key-Authentication-%28%E2%89%A5v5.2.0%29), official wiki: version gate, Bearer transport, rotation and endpoint restrictions.
- **Q2:** [qBittorrent WebUI API](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-%28qBittorrent-5.0%29), official wiki: legacy cookie authentication and endpoint conventions. Test against actual supported releases; documentation sections may describe different version ranges.
- **I1:** [IGDB API documentation](https://api-docs.igdb.com/), official documentation: authentication, filters, pagination and rate/concurrency limits. A provider catalog's coverage is not a preservation completeness guarantee.
- **R1:** [RomM backend architecture](https://github.com/rommapp/romm/blob/master/docs/BACKEND_ARCHITECTURE.md), upstream source: version-dependent API and metadata shapes. Use pinned supported release schemas for adapter fixtures, not an unpinned master assumption.
- **E1:** [ES-DE installation and gamelist reference](https://gitlab.com/es-de/emulationstation-de/-/blob/master/INSTALL.md), upstream documentation: use a version-specific profile for interchange and metadata roots. Current full-page extraction was unavailable during planning; format details must be verified against the pinned implementation version in `R13`.
- Existing project contracts: [SeerrNG](../../SEERRNG-INTEGRATION.md), [frontend exports](../../../romarr/frontends.py), [setup](../../design/setup-experience-contract.md), [install](../../INSTALL.md), and [runner policy](../../../AGENTS.md).
