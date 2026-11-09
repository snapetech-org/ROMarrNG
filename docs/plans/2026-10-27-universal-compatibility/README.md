# ROMarrNG: usable first run and universal compatibility

**Status:** implementation in progress in [PR #60](https://github.com/snapetech-org/ROMarrNG/pull/60); source changes are not yet runtime qualified.

**Implementation owner:** Luna.

**Prepared:** 2026-10-27 (America/Regina).

**Inspected base:** `main` at `bd06296a776ffa0ffcfdcd31f051e3f92fd6f07c`.

**Confidence:** high in the reproduced defects and source findings; moderate in the proposed architecture until the performance and migration gates pass; unknown for integrations without recorded runtime evidence.

ROMarrNG should let someone point it at their existing PS1 and PS2 folders, recognize the systems, see useful game details and artwork, discover games they do not own, and choose what to acquire. Every unavailable action should explain the missing prerequisite and offer a direct repair. That first experience must work without learning the entire ecosystem.

The feedback exposes missing connections between features that already exist. Folder scanning, metadata lookup, DAT planning, release search, backend libraries and personal game notes each work in isolation in parts of the code. They do not yet form a reliable collection experience. This plan repairs the immediate failures, then connects those features through explicit identity, persistent enrichment, capability reporting and resumable work.

## Read and execute

1. [Current evidence and requirement traceability](01-current-state.md): distinguish reproduced defects, source findings, user reports and unknowns.
2. [Product experience and flows](02-experience.md): exact behavior for setup, games, platforms, search, collections, lists and the ecosystem.
3. [Architecture, data and API contracts](03-architecture.md): identity, storage, jobs, matching, ownership, pagination and migration.
4. [Compatibility contract](04-compatibility.md): files, backends, qBittorrent, integrations, deployment and security boundaries.
5. [Ordered implementation packets and ledger](05-delivery.md): dependencies, file owners, acceptance gates, rollout and handoff instructions.
6. [Verification and release qualification](06-verification.md): fixtures, regression scenarios, budgets, migration exercises and evidence requirements.

PR #60 now covers folder-to-system mapping, guided task setup, metadata
refresh/correction, source-scoped catalog browsing, selected-to-Wanted flow,
qBittorrent API-key authentication, search-source parity, durable folder scan
generations/media sets, the SQLite job/outbox foundation and reviewable
frontend interchange. The delivery ledger separates implementation evidence
from runtime qualification. Catalog/list snapshots, broader worker migration,
live backend and scale evidence, browser journeys and private-JIT qualification
remain open.

Before this follow-up, focused suites passed 101 tests plus one separate
catalog/Wanted HTTP case. New scan-store and interchange tests are added, but
cannot run in the current offline environment because pytest and requests are
not in its package cache. Direct standard-library smoke checks cover generation
promotion/retention, outbox idempotency, SQLite backup, parser bounds and
metadata rollback. A prior full-suite run was blocked after automatic review
detected an unexpected request to an untrusted external host; see
[verification](06-verification.md) for the exact boundary.

## Product decisions

| Decision | Required outcome |
| --- | --- |
| Support collection management as a first-class entry path | Existing ROMs can be scanned, identified, enriched and browsed without an indexer, downloader, DAT or external library server. Acquisition remains a primary ROMarrNG responsibility. |
| Ask what the operator wants to do and which systems interest them | Use existing Get Started, Settings and status surfaces after the secure claim step; retain Skip, All systems and Advanced access. |
| Treat system interests as presentation preferences | Never hide owned games, alter platform support, re-route files or cancel existing automation merely because an interest was deselected. |
| Give a folder an explicit meaning | Distinguish one-system roots from multi-system roots and distinguish scan mapping from download/import routing. |
| Make metadata a persistent background feature | Automatic enrichment for newly scanned games after it is enabled, visible refresh/re-identify actions, provenance, manual correction and offline persistence. |
| Separate discovery from acquisition | Catalog/list import produces a preview. Creating Wanted entries or starting searches requires the named action and an accurate summary of its effects. |
| Unify release evaluation | Add New and Interactive Search use the same candidate evaluation for the same context; manual override remains explicit. |
| Define compatibility per capability | “Can scan,” “can identify,” “can import,” “can refresh metadata,” and “can play this file” are separate answers. |
| Preserve established integrations | Existing platform slugs, DAT keys, legacy endpoints, SeerrNG contract v2, backend plugin protocol and download/import safeguards remain compatible. |

## Definition of success

- A fresh operator can select PlayStation and PlayStation 2, add two single-system folders, and see correctly separated libraries and systems. Root-level `.chd`/`.iso` ambiguity never determines the system by declaration order.
- A configured and tested metadata provider can enrich existing and future items. A missing cover has a useful state: queued, matching, ambiguous, not found, provider unavailable or artwork failed. A blank tile is not the entire diagnosis.
- A game opens a detail view with metadata, source/variant information, refresh and correction actions, personal notes, and the playback routes actually available for that file.
- Add New reports whether nothing was found, all candidates were rejected, providers failed, or a downloader is missing; it can open the same evaluated results in Interactive Search.
- Collections computes ownership from the complete inventory, handles DAT/system mismatches explicitly, runs without an open browser, and never confuses “request attempted” with “downloaded and imported.”
- A user can browse a source-scoped PS1 catalog, filter known RPG entries, see which titles are present/missing/uncertain, preview a selection and add only chosen eligible titles to Wanted. Coverage and unknown genre remain visible.
- qBittorrent supports documented API-key authentication where available and preserves older username/password sessions.
- Existing installs upgrade without moving ROMs, erasing metadata/notes, changing current automation policy or widening integration credentials.

## Boundaries and assumptions

“Universal” means tolerant formats, stable identities, adapters and honest capability reporting; it does not mean every backend has every feature. No new database server, mandatory cloud service, general plugin framework, frontend framework migration, emulator bundle or browser container is required for the core experience. Use Python's SQLite support for the new large inventory/catalog store; keep existing configuration and acquisition state in the current Store initially.

Keep native PC acquisition in QuestarrNG and request approval/multi-user request policy in SeerrNG. ROMarrNG may expose its existing catalogs in its own UI without duplicating those products. A metadata match is not a verified dump, catalog membership is not ownership, and acquisition support is not an emulation guarantee.

The earlier [setup contract](../../design/setup-experience-contract.md) governs the secure claim and reuse of existing settings. This plan expands its post-claim flow with collection-first tasks and system interests; `R02` updates that contract explicitly. Do not create a second credential/settings store or an unrelated wizard route.

The [private JIT runner directive](../../../AGENTS.md) applies to every GitHub Actions job. Missing runner capacity is a blocker; hosted fallback is not an option. This planning PR does not change CI or merge other work. Open [PR #58](https://github.com/snapetech-org/ROMarrNG/pull/58) overlaps folder-scan caching; open [PR #56](https://github.com/snapetech-org/ROMarrNG/pull/56) concerns runner dispatch. Recheck their status before implementation.

## Planning verification

At the inspected base, isolated probes reproduced blank system/artwork fields for two single-system folder roots and a collection reporting `done=1, failed=0` after a request returned `ok=false`. The six relevant existing test modules passed: **108 tests**, using Python 3.12 in an isolated environment. That was evidence of coverage gaps, not evidence the reported journeys work. Current implementation evidence and remaining gates are recorded in [the verification record](06-verification.md).

No live library, indexer, download client or emulation endpoint has been exercised for the current implementation. A release-note fragment is included; source tests do not qualify live compatibility or private-JIT CI.
