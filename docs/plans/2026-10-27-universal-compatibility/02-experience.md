# Product experience

These are target behaviors, not descriptions of features already shipped. Terminology must stay consistent across the UI, API errors, install guide and translations.

## 1. Explain the product through the task

Use a concise introduction: “Organize the ROMs you have, discover games for your systems, and automate finding and filing the ones you want.” Explain that playing depends on a compatible frontend/emulator; show actual supported routes when a game is opened.

After the existing password/claim screen, open the existing Get Started surface with three task choices: **Organize my games**, **Find games to add**, and **Connect an existing library**. They set helpful defaults, not exclusive application modes. Ask **Which systems interest you?** next, before exposing the long configuration surface. Systems can be searched by name or alias, selected in groups and changed later. Skip and All systems are first-class choices.

Preserve environment-derived and existing saved values, showing their origin. Persist only small preferences in existing settings: interest slugs, task intent, experience level and setup progress version. Compute readiness from current capability checks, not a permanently checked onboarding box. A lost provider credential makes its task incomplete again. Reopening Get Started resumes the same flow. Old installs do not get a blocking wizard.

| Task | Core steps | Optional follow-ups |
| --- | --- | --- |
| Organize my games | Pick systems → add folder(s) with root interpretation → preview scan → browse results | Enable metadata enrichment; import local artwork; verify against DATs; connect a player |
| Find games to add | Pick systems → browse catalog or enter a title → review search results → configure only the missing acquisition prerequisites → choose destination → submit | Automated Wanted searches, lists, stricter quality policy, browser sources |
| Connect an existing library | Select backend → enter existing endpoint/auth → test → inspect returned systems and capabilities → browse | ROMarrNG metadata overlays; backend rescan; acquisition destination and path mapping |

An operator can browse a catalog without a downloader. A read-only external backend can be a library without a locally mounted import path. A folder scan can succeed without credentials. Each task explains what is missing only when that capability is required.

## 2. Present a small initial navigation surface

Initial primary destinations: **Games**, **Discover**, **Wanted**, **Activity**, and **Settings**. Add New/Search remain easily reached from Games/Discover and keep old deep links. Collections and Lists sit together under Discover with distinct explanations. System tools, plugins, peers/netplay and ecosystem details remain under an expandable Advanced/Tools area. Existing users keep access and can choose the full navigation view.

Changing interests filters recommendations and selectors to “Interested systems” by default. Always offer **All supported systems**. Games includes owned systems even when not selected. An “Other systems in your library” count makes this visible. Interest preferences never become an authorization rule, an acquisition allowlist or a filter on SeerrNG's authoritative platform endpoint.

Group system selection by console/handheld/computer/arcade, then family/manufacturer where useful. Generation is an optional view with “Not applicable / uncategorized”; it is not a canonical identity and must not impose console generations on computers or arcade sets. Search aliases, show counts, retain the query and group state, and avoid a page containing hundreds of expanded descriptions.

## 3. Add a folder without making its structure a guessing game

The Library editor must distinguish these fields:

| Field | Meaning |
| --- | --- |
| Scan root | Existing path inside the ROMarrNG runtime; it may be mounted read-only. |
| Root mode | **One system**, **Folders by system**, or legacy layout pending review. |
| System for this root | Required for One system; e.g. `psx` for a path called `/roms/PS1`. |
| Folder-to-system mapping | For mixed roots, explicit path prefixes/aliases; preview unmatched or conflicting folders. |
| Import destination / layout | Separate writable target and layout, when acquisition is enabled. “Use scan root” is an explicit choice with a preview. |
| Route these acquired systems here | Existing `platforms` routing semantics; do not reinterpret this list as scan metadata. |

Preview reports readable files, grouped games/media sets, resolved systems, conflicts, excluded/unsupported files, source limitations and any overlap with another configured root. Preview is bounded and visibly partial when necessary. It never moves, renames, converts or extracts the collection. A suggestion based on root basename, such as `PS1`, may prefill a field but needs confirmation before becoming a saved scan/import rule.

Examples that must work:

- `/roms/PS1/Game.chd` with that folder selected as One system → `psx`.
- `/roms/PS2/Game.iso` with that folder selected as One system → `ps2`.
- `/roms/psx/Game.chd` and `/roms/ps2/Game.iso` under a mixed root → two canonical systems.
- `/roms/psx/roms/Game.chd` → recognized nested layout, without treating `roms` as the game or system.
- A folder called `Favorites` containing unknown `.iso` files → Unknown until mapped or identified; never automatically PS1 because it is the first claimant.
- A one-system scan root reused for imports → target `Game.chd` in that root, not a silently appended `psx/psx` directory. Existing mixed-root targets retain their previous layout.

## 4. Games is an actionable collection

Default sort is canonical system then title, with a stable ID tie-breaker. Offer library, system, genre, year, region, identification state, artwork state, local/catalogued presence and personal status filters. Library identity is independent of source provenance. Show clear unknown buckets and metadata coverage; a genre filter applies only where genre is known.

Use bounded pagination/virtualized presentation; “show more” must advance the cursor/page rather than repeatedly requesting an ever-larger first page that hits the current 500 limit. Totals state their unit: logical titles, copies/media sets or files. Two backends exposing the same file remain separate occurrences with an optional combined title view. Distinct PS1/PS2 editions and region/disc variants never disappear through title-only deduplication.

The scan banner distinguishes scanning, partial, complete, interrupted, stale and failed. If a backend is down, keep its previous snapshot visible with a warning. Do not convert an outage into zero games, “missing” status or a new download recommendation.

Every tile has a readable fallback title/system when art is absent and a concise status when repair is possible. Clicking it opens a routable detail view so refresh/back/bookmarks work. That view contains:

- Cover, title, canonical system, source library and metadata provenance.
- Description, genres and release date with precision/source; do not invent January 1 for year-only dates.
- Copies, regions, revisions, media/disc set, verification and presence state, without equating a provider match to a checksum verification.
- **Refresh metadata**, **Identify / fix match**, **Set system**, and **Change artwork**, where allowed.
- Existing played/playing/shelved state, rating and notes, preserved through corrections and refreshes.
- **Play / Open in frontend** only for a valid actual-file route; otherwise a specific missing prerequisite and setup action. “Download only” remains a valid answer.
- Relevant activity, current acquisition state and a source-library link when the backend supports it.

Bulk actions use a selection bar with exact scope: this page, explicit items, or all matches in a pinned query snapshot. Refresh metadata can target missing metadata, missing artwork, failed items or all unlocked fields. A destructive override is a separate named action with a preview. Editing identification does not rename source files.

## 5. Metadata has visible progress and reversible decisions

Saving a provider offers **Test connection** and **Fill missing metadata for these libraries**. In guided setup, enabling enrichment authorizes that bounded initial job and future new-item enrichment for the selected libraries. Existing installations are prompted to enable it; an upgrade never starts an unbounded scrape automatically. Saving/rotating credentials alone does not overwrite metadata or locked matches.

Default refresh fills missing/stale unlocked fields. Forced re-identification is separate from refreshing a known provider entity ID. Preserve good existing art during a transient download/provider failure. Failed jobs expose a reason and a specific retry; there is no silent loop on invalid credentials or no-match responses.

Candidate review displays title, system, edition/year, provider and why it matched. A confidence level is understandable evidence, not a numerical probability pretending to be calibrated. Low-confidence or tied matches wait for review. Selection is persisted by provider ID and locks identity unless the operator explicitly changes it. A DAT-derived title can still select the wrong metadata entry; the interface must not call that provider match “exact by DAT.”

Local metadata/artwork imports have previewed provenance and configurable precedence. Backend data stays backend-owned; ROMarrNG applies an overlay by default. Writing metadata back to RomM or another library is a separate opt-in capability, never an implicit effect of Refresh.

## 6. Search makes the difference between found and usable explicit

Rename the main action descriptively: **Search releases**, **Add to Wanted**, or **Search & grab best**, depending on intent. Do not claim a metadata catalog lookup searches releases. A platform must be explicitly selected/confirmed before acquisition; avoid preselecting the first unrelated platform.

| Outcome | User-facing result | Next action |
| --- | --- | --- |
| No sources configured | Release search needs a source | Configure indexer/source |
| Sources answered, zero results | No releases returned for this title/system | Edit query, save to Wanted |
| Some/all sources failed | Partial results / search unavailable, with named safe error codes | Repair source, retry failed sources |
| Results exist, none accepted | N found; N rejected, grouped by reason | Inspect the same results / change policy deliberately |
| Accepted release, no usable client | Found, cannot download using this protocol | Configure/test client |
| Accepted but import destination unavailable | Found, destination needs repair | Repair confirmed mapping/path |
| Dispatch succeeded | Sent to client; download/import pending | Open Activity |
| Dispatch outcome uncertain | Client may have accepted it; reconciling | Open Activity; do not blind retry |

**View results** opens the same search ID, system, profile, variant/region policy and candidate snapshot used for the automatic decision. If expired, say a new search will run. Interactive Search can show broader or rejected candidates; manual overrides show the overridden rule and still enforce hard path/auth/content boundaries. Fix source omission in the Any-platform branch without equating unqualified scores with qualified ones.

## 7. Collections, catalogs and lists are different tools

Use brief explanations:

- **Catalogs:** what a source knows exists for a system, with its coverage and version.
- **Lists:** a named selection, imported curation or saved filter; membership alone does not download anything.
- **Complete a set:** compare a DAT or other declared set against your inventory under a selected variant policy.

Collections opens with system selection and a compatible source. If no DAT is present, explain how to load one and offer ordinary catalog discovery. Switch TitleDB must not make “DAT available” appear true for PS1. An unknown DAT/system mapping cannot be started; show the ambiguity and require a choice. “One game, one ROM” has a plain-language explanation, visible region preference and expandable variant details.

Set preview shows expected, present, present but unverified, incomplete, missing, unknown because inventory is stale/unavailable, excluded and already queued. Only known-missing eligible entries are selected by the **Select missing** shortcut. Empty or invalid selections have clear outcomes. A saved plan binds source version, chosen variants, policy and inventory revision; changes require an updated preview where they would expand/change the selection.

Execution offers pause, resume, retry failures and cancel remaining work. Closing the tab does not stop it. “Requested,” “downloading,” “imported,” “failed” and “already present” are separate counts. Cancel stops future dispatch; it does not silently remove files or client jobs already accepted.

## 8. The requested PS1 discovery journey

1. Open Discover → Catalogs → PlayStation (`psx`). Choose an installed Redump/DAT snapshot, a supported metadata catalog, or a curated list source.
2. See the source, version/fetch date, region/edition policy, total coverage and metadata coverage. “All PS1 games” means all entries in that declared source/scope, never an unsupported claim of historical completeness.
3. Enrich/link catalog entries to metadata when a provider is available. DAT-only browsing works offline; genre remains unknown until supplied by a source or a reviewed match.
4. Filter **Genre: RPG**, plus region/year/language/edition if supported. Offer **Unknown genre** separately and state how much of the catalog has genre data. Unsupported facets are disabled with an explanation, not rendered as empty truth.
5. Compare against current inventory. Distinguish owned locally, catalogued remotely, incomplete, wanted/queued, missing and uncertain. Show the selected ownership rule (any edition versus the chosen variant/region).
6. Select individual missing games or all eligible matches across pages. Review exact additions, existing Wanted duplicates, owned games, unresolved identity and blocked requests. Preview is server-side and pinned to a snapshot.
7. Choose **Save to list** (no acquisition) or **Add selected to Wanted**. The latter explicitly explains automatic searches under the current Wanted policy. **Search now** is a separate opt-in. The response is idempotent and returns per-item outcomes.
8. If the list will refresh, choose **Review updates** by default. **Automatically monitor new matches** is an explicit optional policy with a scope, exclusions and per-run cap. Removals from a source never delete ROMs or implicitly cancel a user's separate request.

Supported starting sources: existing DAT/TitleDB adapters, the existing IGDB integration, and imported text/CSV/JSON/URL curation with declared system and optional external IDs. Plain numbered lists remain valid. Do not scrape arbitrary “top games” web pages as trusted machine-readable catalogs. Add provider adapters only after capability/terms/version qualification.

## 9. Ecosystem answers “what do I need next?”

Each recommended integration card states purpose, supported systems/files, required connection/mounts, current test result, version/limitations and one setup action. Group by **Find**, **Download**, **Organize**, **Play**, and advanced **Share/Stream**. Tailor suggestions to intent/interests and installed capabilities without automatically installing anything.

For Browser acquisition, diagnose the optional driver, remote server reachability, transport security and client/server version compatibility separately; link a maintained deployment example and update procedure. Ordinary direct downloads and local collection browsing must remain usable. For emulation, evaluate the actual file and host/frontend capabilities; system selection alone is insufficient.

## 10. Accessibility, localization and consistency

All new controls work with keyboard navigation, visible focus, screen-reader labels and non-color status text. Dialogs restore focus, long operations announce progress without flooding live regions, filters preserve history and async responses cannot paint the wrong route. Validate narrow mobile widths and large catalogs. New labels enter `ui-labels.json` and the existing translation pipeline; RTL and regional number/date formatting remain supported. Titles/filenames retain their original script and case; normalization is for matching only.
