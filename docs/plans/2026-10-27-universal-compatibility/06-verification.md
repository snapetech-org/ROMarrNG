# Verification, release gates and planning evidence

**Confidence:** high in the recorded local results below; proposed budgets have moderate confidence and require measurement; live compatibility remains unknown until qualified. This file separates tests already run for planning from the tests Luna must add/run for implementation.

## V1. Planning evidence actually obtained

Base: `bd06296a776ffa0ffcfdcd31f051e3f92fd6f07c`, clean clone of `main` before documentation edits. Python 3.12 with repository `requirements.txt`, pytest and PyYAML installed into an isolated environment. No source/application code was modified for these checks. The host's default and primary-runtime Python initially lacked requests; the isolated environment resolved that prerequisite.

Executed:

```bash
python -m pytest tests/test_folder_library.py tests/test_metadata.py \
  tests/test_game_meta.py tests/test_collections.py \
  tests/test_interactive_search.py tests/test_qbittorrent_login.py -q
```

Result: **108 passed in 0.70 seconds**, one existing Authlib deprecation warning. This is a focused baseline, not the full application suite or the future acceptance suite.

Two isolated probes used synthetic filenames/bytes and a temporary Store:

| Probe | Observed result |
| --- | --- |
| Folder root `PS1` containing `Example.chd` | `platform=""`, `platform_slug=""`, `cover=""` |
| Folder root `PS2` containing `Example.iso` | `platform=""`, `platform_slug=""`, `cover=""` |
| Mixed root containing `psx/Another.chd` | `platform="psx"`, `platform_slug=""`, `cover=""` |
| One-item batch whose request returns `ok=false` and a no-release error | `status="done"`, `done=1`, `failed=0`, `percent=100.0` |

The collection probe used `object.__new__(ROMarr)` with only a temporary Store and a deterministic request stub, then called the actual `collection_step()` method. It proves that method's return-value handling; it does not simulate a real downloader. Folder probes exercised the actual `FolderLibrary.games()` implementation. The reporter's production environment was not accessed.

Document checks for this planning PR: verify relative links and code-path references, requirement/packet coverage, Markdown structure, `git diff --check`, repository hygiene and release-note opt-out. Record the final PR/commit and check results in the PR description. No full build or live-provider validation is implied by creating the plan.

## V2. Fixture suite

Keep fixtures synthetic and redistributable: small binary headers/descriptors, invented titles, deterministic hashes, sanitized provider responses and fake HTTP/grpc-web endpoints. No commercial ROM payloads, private tokens, downloaded catalogs of uncertain redistribution status or live indexer credentials.

| Fixture | Variants |
| --- | --- |
| `single_roots` | PS1/PS2 separately mounted; same title in both; explicit system; ambiguous generic folder; root rename; read-only mount |
| `mixed_roots` | Alias names/case/punctuation, nested `roms`, genre folders, overlaps, two libraries with the same display name |
| `disc_sets` | CUE plus multiple BINs, M3U with two discs, duplicate referenced discs, missing track, cycles, absolute/outside-root refs |
| `media_formats` | Existing cartridge/archive/disc/directory formats, arcade ZIP parent/clone/BIOS, Switch content kinds, unsupported/ambiguous packages |
| `identity` | Same remote ID in two backends, same title across systems/regions/editions, backend ID reuse, move with/without hash evidence, Unicode normalization |
| `metadata` | Exact provider ID; wrong-platform/sequel/tied result; no match; missing art; expired credential; 429; timeout; provider ID redirect/removal; user locks |
| `catalog` | DAT with clones/regions; unknown header; version refresh; known/unknown genre; partial pages; repeated cursor; duplicate IDs; sparse filtered pages |
| `search` | Same candidates for both entry points; mixed direct/Prowlarr/Hub sources; reject/accept/ties; no URL/client/destination; all-source and partial failure |
| `jobs` | Crash before/after durable writes, expired lease, concurrent workers, pause/cancel races, lost network response, duplicate commit, disk full |
| `legacy_state` | Older JSON only; masked credentials; duplicate title notes; corrupt/unreadable files; legacy lists/batches; current SeerrNG requests; newer unknown DB schema |

## V3. Required end-to-end acceptance scenarios

Run through actual HTTP routes and the UI, not only direct service calls. Assert visible results, durable state and side effects together. Browser tests use an isolated local server with fake backends; the existing `scripts/prove_pages.py` smoke pattern can be extended, but “the button exists” alone is insufficient.

| ID | Scenario | Pass criteria | Owner packets |
| --- | --- | --- | --- |
| A01 | Fresh claim → organize → PS1/PS2 interests → two single roots | No mandatory indexer/client; correct canonical systems and library filters; helpful next action | R01–R04, R08 |
| A02 | Same roots with no metadata provider | Games remain browsable, no false matched/verified claim, explanatory art state | R04, R06, R08 |
| A03 | Add/test provider and choose Fill missing | Known fixtures receive correct provider IDs/art; bounded job progress; existing games change without re-import | R05/R06/R08 |
| A04 | Restart after partial enrichment, then disconnect provider | Committed results and locks survive; unfinished work resumes safely; good cached art remains | R05/R06 |
| A05 | Wrong-system and tied provider results | No automatic bad match; candidate review repairs the item; personal notes survive correction | R03/R06/R08 |
| A06 | Open game and inspect actual-file playability | Metadata/refresh/match/notes visible; supported route works or specific prerequisite is stated | R08/R14 |
| A07 | Mixed root and renamed duplicate libraries | IDs stay source-scoped, grouping/filtering accurate, no cross-library note/art collision | R03/R04/R08 |
| A08 | Library with more than 120 and more than 500 entries | Browse advances without duplicate first pages; ownership sees all complete inventory; totals use declared units | R04/R08/R10 |
| A09 | Source goes offline or scan truncates | Last-good rows persist; freshness/partial state shown; no blanket missing/acquisition | R04/R10/R11 |
| A10 | Add New vs Interactive Search, identical context | Same candidate set/order/verdicts; failure explains rejection/source/client stage; same snapshot link works | R09 |
| A11 | Interactive Any platform with direct indexers | All enabled capable sources participate; explicit system required before acquisition | R09 |
| A12 | qBittorrent session and supported API key | Correct protocol/auth flow; rotation and expiry handled; no secret leak or fallback after invalid key | R07 |
| A13 | Collections with bad DAT/system selection | Explicit error before batch creation; no silent first-DAT fallback or empty-platform request | R01/R10 |
| A14 | Batch request returns failure, accepted transfer, then import | Each distinct state/count is accurate; no false completed import | R01/R05/R10 |
| A15 | Start/pause/resume/restart/cancel a large set | Works with browser closed; no duplicate dispatch; no queue eviction; late callback cannot restart cancelled work | R05/R10 |
| A16 | PS1 catalog → RPG → missing → selected Wanted | Source/genre coverage visible; unknowns remain unknown; only selected eligible identities enter Wanted | R11/R12 |
| A17 | Select all filtered catalog pages with exclusions; change source/policy | Selection pinned; stale broadening rejected; owned/queued items safely skipped; retries idempotent | R11/R12 |
| A18 | Curated list sync adds/removes/renames entries | Review by default for new policy; legacy automation retained; exclusions persist; no file deletion | R12 |
| A19 | Import/export metadata for two frontend profiles | Correct path/root mapping, IDs/locks preserved, no scan writeback or unsafe XML/path fetch | R13 |
| A20 | Existing SeerrNG v1/v2 clients and scoped provider key | Legacy routes/payloads/keys preserved; admin/detail/art routes not newly accessible; DAT keys unchanged | R03/R09–R12/R14 |
| A21 | Upgrade old state then restore/rollback | Settings, credentials, notes, matches and acquisition identities recover; no duplicate remote action | R05/R15 |
| A22 | Optional Browser unavailable/mismatched version on Unraid | Specific recipe/diagnostic; normal direct/local workflows continue | R14 |
| A23 | Interest changes, keyboard/mobile/RTL, rapid route/filter changes | No lost owned games/automation; accessible controls; stale responses do not overwrite active page | R02/R08 |

Every acceptance scenario has deterministic offline coverage. Live qualification supplements it for the protocols/formats/deployments that mocks cannot establish.

## V4. Test homes and commands

Use existing modules as regression anchors; add focused behavioral tests near the affected domain. Proposed new tests include `test_inventory_identity.py`, `test_scan_snapshots.py`, `test_enrichment_jobs.py`, `test_artwork_delivery.py`, `test_catalog_store_migrations.py`, `test_catalog_selection.py` and `test_job_recovery.py`. Their names can change; their scenarios cannot disappear.

| Area | Existing regression anchors |
| --- | --- |
| Folder/layout/identity | `test_folder_library.py`, `test_libraries.py`, `test_multi_library.py`, `test_library_filters.py`, `test_library_counts.py`, `test_library_health.py`, `test_scan_headers.py` |
| Media/import | `test_rom_set.py`, `test_multi_rom_import.py`, `test_disc_import.py`, `test_sniff_discs.py`, `test_sniff_archives.py`, `test_recent_consoles.py`, `test_manual_adopt.py` |
| Metadata/details | `test_metadata.py`, `test_igdb_provider.py`, `test_romm_metadata.py`, `test_game_meta.py`, `test_play_routes_api.py`, `test_playability.py` |
| Acquisition/collections | `test_interactive_search.py`, `test_selection.py`, `test_profiles.py`, `test_collections.py`, `test_present_titles.py`, `test_strict_regions.py`, `test_failed_download_handling.py`, `test_import_queue_identity.py` |
| Catalog/lists/contracts | `test_dat_catalog.py`, `test_catalog_contract.py`, `test_seerrng_dat_verification.py`, `test_lists.py`, `test_store_lists.py`, `test_store_connectors.py`, `test_titled.py`, `test_frontends.py` |
| Auth/clients/ops/UI | `test_qbittorrent_login.py`, `test_qbittorrent_excluded_files.py`, `test_every_client.py`, `test_first_run.py`, `test_auth_http.py`, `test_security_claims.py`, `test_ops.py`, `test_openapi.py`, `test_ui_pages.py`, `test_translations_layout.py` |

Representative local commands (use an isolated environment populated from current requirements):

```bash
python -m pytest tests/test_folder_library.py tests/test_multi_library.py \
  tests/test_library_filters.py tests/test_present_titles.py -q
python -m pytest tests/test_metadata.py tests/test_igdb_provider.py \
  tests/test_game_meta.py tests/test_frontends.py -q
python -m pytest tests/test_interactive_search.py tests/test_collections.py \
  tests/test_lists.py tests/test_qbittorrent_login.py -q
python -m pytest tests/test_dat_catalog.py tests/test_catalog_contract.py \
  tests/test_seerrng_dat_verification.py tests/test_auth_http.py -q
python -m pytest tests/ -q
```

The repository's pytest default excludes `network` tests. Do not count deselected or skipped live tests as qualified. Add new behavioral tests to the relevant packet command. Package/build and browser checks run under the existing supported tooling; do not add unrelated dependencies to the base runtime just to run a browser test. GitHub Actions must run on private JIT at the actual candidate revision.

## V5. Fault injection and concurrency

Exercise power/process termination immediately before/after: scan generation publication, job lease, metadata field commit, artwork rename, SQLite outbox commit, strict JSON save, downstream send and downstream acknowledgement. Repeat the operation after restart and inspect identities/counters, not just HTTP success.

Use barriers to force races: duplicate preview commits, two scan starts, import during scan, cancel during a network response, changed manual match while old enrichment finishes, credential rotation during a poll, source removal during a job, and two workers acquiring the same lease. Verify stale workers cannot commit to a newer revision. All lock-held network/file work is a test failure for the new services.

Inject disk-full/permission errors, malformed/corrupt state, incompatible schema, wrong DB volume assumptions, provider 401/403/429/5xx, stalled responses, repeated pagination tokens, oversized catalog/art responses and memory pressure. Preserve the last good snapshot and surface the responsible component. No fixture may silently reset auth, drop a user override, expand an acquisition selection or report unsuccessful persistence as success.

## V6. Resource budgets and observability

These are **initial engineering targets, not current measurements**. `R00` records hardware/filesystem/tool versions and baseline; `R05/R15` publish measurements with any justified revision. Count algorithmic work as well as elapsed time so a fast SSD does not hide repeated network walks.

| Workload | Initial target / invariant |
| --- | --- |
| Folder generation | One tree traversal per scan generation; count/page reads do not rewalk; no full-file hashing or remote lookup on ordinary browse. |
| Repeated unchanged scan | Reuse file fingerprints/provider matches; zero repeated enrichment calls for fresh unchanged items. |
| Warm local browse | p95 under 250 ms for 100,000 inventory items plus 250,000 catalog entries on a recorded 2-vCPU/1-GiB local-SSD fixture; measure query plus serialization. |
| Local first useful page | Within 2 seconds once a snapshot exists; cold scanning displays immediate progress rather than waiting for full ingestion. Remote backend scan duration is reported separately. |
| Browser payload/rendering | Bounded pages, initial 120 and maximum 500 where compatible; one visible page rendered at a time; no full catalog embedded in HTML/JSON. |
| Large disk tree | 23,739 ROM items / 177,000 filesystem entries plus a 100,000-item stress case; demonstrate bounded memory and progressive visibility. Source limits are explicit. |
| Memory | No whole-catalog resident copy; target total service RSS below 450 MiB in a 512-MiB constrained core-workflow test. If not met, reduce batch/cache/workers or document a qualified requirement before release. |
| Background isolation | Interactive cached reads remain responsive during scans/enrichment; no unbounded threads or per-item provider requests on UI render. |
| Acquisition admission | Pending bulk targets remain durable outside the capped active queue; saturation delays work visibly without evicting live entries or rejecting unrelated reads. |

Track scan duration/visited/emitted/truncated counts, complete-generation age, unresolved system/match counts, metadata/art coverage, provider latency/errors/rate limits, queue wait, worker leases/retries, outbox uncertainty, browse p50/p95, memory and cache bytes. Use bounded metric labels; game names/IDs/paths are not metric dimensions. Each failure has a correlation ID and safe reason code. Support bundles are operator-generated, redacted and previewable; no automatic external telemetry is required.

## V7. Security and regression invariants

Test source-data HTML/script injection, malformed query syntax, XML entities, archive traversal/bombs, symlink escapes, hostile M3U/CUE references, untrusted URL redirects/DNS targets, huge image dimensions, credential-bearing errors, masked secrets, and cross-scope object access. Preserve private-service connectivity while constraining untrusted outbound URLs as described in Compatibility C5.

SeerrNG/provider/peer credentials must still fail against operator settings, metadata correction, jobs and arbitrary artwork/file APIs. Existing asset delivery tests protect ROM paths. Metadata correction cannot change a file path or launch command. The UI cannot turn a saved catalog query into a broader download request by editing hidden fields; server-side preview validation is authoritative.

## V8. Qualification and release record

For each wave, attach: app commit, schema version, fixture revisions, commands/results, supported backend/API versions, OS/architecture, resource measurements, browser screenshots/traces for the critical journey, migration/restore result and unresolved limitations. Store raw traces as CI artifacts with a retention policy and link a sanitized summary in the PR. Never put credentials or private game inventories in a public artifact.

Release criteria: all applicable A-scenarios pass; full offline suite and packaging gates pass on the intended revision; critical scope/data-loss/false-ownership/duplicate-dispatch defects are closed; compatibility badges correspond to evidence. A backend without live evidence remains **unverified** even if its mock tests pass. Failed private-JIT provisioning is reported as a CI blocker, never solved by hosted fallback.

After rollout, compare unresolved-system count, known metadata/art coverage, failed/uncertain acquisitions and task completion on controlled acceptance installs. Only widen opt-in defaults after confirming identity accuracy and job recovery. Do not use art coverage alone as a success metric: filling every tile with the wrong game's art is a failure.
