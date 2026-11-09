# Upstream source attribution

This ledger publicly credits 48 source records from [BlizzHacker/romarr](https://github.com/BlizzHacker/romarr) that informed, supplied, or were reconciled with behavior in this fork.

The linked people made their reports, suggestions, discussions, or code contributions to the upstream project. This is source credit only: it does not claim that they contributed directly to this fork, endorsed it, or participated in the fork integration. Fork maintainers adapted, integrated, or verified the resulting behavior separately.

This reproduces the complete repository audit in release-facing form. “Existing coverage” includes behavior inherited from upstream; “Implemented/adapted” identifies behavior integrated separately in ROMarrNG.

## Credited ROMarr sources

Each disposition is retained so credit does not overstate what the fork changed.

- [PR #1](https://github.com/BlizzHacker/romarr/pull/1) — “Say which side of the volume mount has to match the download client,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [issue #2](https://github.com/BlizzHacker/romarr/issues/2) — “Proxmox Script Error,” opened upstream by [@Azilroka](https://github.com/Azilroka). Audit disposition: **Existing coverage**.
- [PR #3](https://github.com/BlizzHacker/romarr/pull/3) — “Default to port 6868, because 7878 is Radarr's,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [PR #4](https://github.com/BlizzHacker/romarr/pull/4) — “Stop a path-mapping test failing on another thread's log,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [PR #5](https://github.com/BlizzHacker/romarr/pull/5) — “Every game, every platform: remove the disc-based exclusion,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [PR #6](https://github.com/BlizzHacker/romarr/pull/6) — “Set the standard: authenticate, index anything, and prove the file is right,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [PR #7](https://github.com/BlizzHacker/romarr/pull/7) — “Fix qBittorrent 5.x login and import all ROMs from multi-ROM archives,” opened upstream by [@m3](https://github.com/m3). Audit disposition: **Existing coverage**.
- [issue #8](https://github.com/BlizzHacker/romarr/issues/8) — “Error 401 (Unauthorized) - "Send your key as the X-Api-Key header",” opened upstream by [@AltraumArkhein](https://github.com/AltraumArkhein). Audit disposition: **Existing coverage**.
- [PR #9](https://github.com/BlizzHacker/romarr/pull/9) — “chore: add CodeRabbit configuration,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [issue #10](https://github.com/BlizzHacker/romarr/issues/10) — “Plugins in the docker,” opened upstream by [@bluecalx4](https://github.com/bluecalx4). Audit disposition: **Existing coverage**.
- [issue #11](https://github.com/BlizzHacker/romarr/issues/11) — “Deluge Support,” opened upstream by [@shopsD](https://github.com/shopsD). Audit disposition: **Existing coverage**.
- [PR #12](https://github.com/BlizzHacker/romarr/pull/12) — “Fix ROM Hub confinement in Docker,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [PR #13](https://github.com/BlizzHacker/romarr/pull/13) — “Fix empty plugin catalogue in Docker,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [PR #14](https://github.com/BlizzHacker/romarr/pull/14) — “Fix expired qBittorrent sessions without a ROMarr restart,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [issue #15](https://github.com/BlizzHacker/romarr/issues/15) — “Docker plugin installs fail: missing git and invalid Archive.org v0.4.0 ref,” opened upstream by [@duduke](https://github.com/duduke). Audit disposition: **Existing coverage**.
- [PR #16](https://github.com/BlizzHacker/romarr/pull/16) — “Fix Docker plugin installation failures,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [issue #17](https://github.com/BlizzHacker/romarr/issues/17) — “Inconsistant file permissions between container and host,” opened upstream by [@AbbieGorlovWebster](https://github.com/AbbieGorlovWebster). Audit disposition: **Existing coverage**.
- [issue #18](https://github.com/BlizzHacker/romarr/issues/18) — “No Connection to GGRequestz,” opened upstream by [@AbbieGorlovWebster](https://github.com/AbbieGorlovWebster). Audit disposition: **Existing coverage**.
- [PR #19](https://github.com/BlizzHacker/romarr/pull/19) — “Fix GG Requestz request delivery setup,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [PR #20](https://github.com/BlizzHacker/romarr/pull/20) — “Preserve media bind-mount permissions,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [issue #21](https://github.com/BlizzHacker/romarr/issues/21) — “Zero DATs Loaded,” opened upstream by [@DaFr0n](https://github.com/DaFr0n). Audit disposition: **Existing coverage**.
- [issue #22](https://github.com/BlizzHacker/romarr/issues/22) — “Decompression & validation for non-native files for DAT verification,” opened upstream by [@Ronald-Diemicke](https://github.com/Ronald-Diemicke). Audit disposition: **Existing coverage**.
- [issue #23](https://github.com/BlizzHacker/romarr/issues/23) — “Solution for Switch catalogging?,” opened upstream by [@Ronald-Diemicke](https://github.com/Ronald-Diemicke). Audit disposition: **Implemented/adapted**.
- [issue #24](https://github.com/BlizzHacker/romarr/issues/24) — “interactive search using hub with archive.org,” opened upstream by [@tiagofcp](https://github.com/tiagofcp). Audit disposition: **Implemented/adapted**.
- [issue #25](https://github.com/BlizzHacker/romarr/issues/25) — “Allow removing a title from Wanted without importing it,” opened upstream by [@Jordfoz16](https://github.com/Jordfoz16). Audit disposition: **Existing coverage**.
- [issue #26](https://github.com/BlizzHacker/romarr/issues/26) — “Persist the download queue across restarts,” opened upstream by [@Jordfoz16](https://github.com/Jordfoz16). Audit disposition: **Existing coverage**.
- [issue #27](https://github.com/BlizzHacker/romarr/issues/27) — “Blocklist stalled or failed downloads and grab the next release,” opened upstream by [@Jordfoz16](https://github.com/Jordfoz16). Audit disposition: **Existing coverage**.
- [PR #28](https://github.com/BlizzHacker/romarr/pull/28) — “Persist the queue, allow dropping a request, and retire dead downloads,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [PR #29](https://github.com/BlizzHacker/romarr/pull/29) — “docs: describe failed-download handling, and cut 0.9.0,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [issue #30](https://github.com/BlizzHacker/romarr/issues/30) — “Unable to pull the docker image,” opened upstream by [@Stono](https://github.com/Stono). Audit disposition: **Public manifests verified; fork references correct**.
- [issue #31](https://github.com/BlizzHacker/romarr/issues/31) — “GitHub Container Repository OCI Image is not found,” opened upstream by [@Windows98SE-dev](https://github.com/Windows98SE-dev). Audit disposition: **Public manifests verified; fork references correct**.
- [PR #32](https://github.com/BlizzHacker/romarr/pull/32) — “Changed repo name in docker-compose.yml,” opened upstream by [@Windows98SE-dev](https://github.com/Windows98SE-dev). Audit disposition: **Public manifests verified; fork references correct**.
- [issue #33](https://github.com/BlizzHacker/romarr/issues/33) — “webhooks seem to be broken,” opened upstream by [@Ant1695](https://github.com/Ant1695). Audit disposition: **Implemented/adapted**.
- [issue #34](https://github.com/BlizzHacker/romarr/issues/34) — “1G1R collection planner ignores nested library layout (Structure B),” opened upstream by [@GitHubber1312](https://github.com/GitHubber1312). Audit disposition: **Existing coverage**.
- [issue #35](https://github.com/BlizzHacker/romarr/issues/35) — “pip install playwright doesn't work in the unraid docker container,” opened upstream by [@Ant1695](https://github.com/Ant1695). Audit disposition: **Existing coverage**.
- [PR #36](https://github.com/BlizzHacker/romarr/pull/36) — “fix: Unraid browser edition, working connection tests, nested-library planner,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [issue #37](https://github.com/BlizzHacker/romarr/issues/37) — “Collections: strict region filtering and configurable fan-translation languages,” opened upstream by [@GitHubber1312](https://github.com/GitHubber1312). Audit disposition: **Implemented/adapted**.
- [issue #38](https://github.com/BlizzHacker/romarr/issues/38) — “Completed downloads never import when the torrent name differs from the indexer title (queue matches by name, not hash),” opened upstream by [@STiXzoOR](https://github.com/STiXzoOR). Audit disposition: **Implemented/adapted**.
- [issue #39](https://github.com/BlizzHacker/romarr/issues/39) — “RomM library goes unreadable ~30 min after start: expired token gets HTTP 500 from RomM 5.3.1, re-auth only triggers on 401,” opened upstream by [@STiXzoOR](https://github.com/STiXzoOR). Audit disposition: **Existing coverage**.
- [issue #40](https://github.com/BlizzHacker/romarr/issues/40) — “Expose ROM Hub plugin search in Interactive Search (plugins can be enabled but are never used),” opened upstream by [@LarryGF](https://github.com/LarryGF). Audit disposition: **Implemented/adapted**.
- [issue #41](https://github.com/BlizzHacker/romarr/issues/41) — “hub.py sets ROM_HUB_ALLOW_UNSANDBOXED=1 unconditionally at import,” opened upstream by [@LarryGF](https://github.com/LarryGF). Audit disposition: **Existing coverage**.
- [PR #42](https://github.com/BlizzHacker/romarr/pull/42) — “fix(import): match finished downloads to the queue by id before title,” opened upstream by [@bharvey42](https://github.com/bharvey42). Audit disposition: **Implemented/adapted**.
- [PR #43](https://github.com/BlizzHacker/romarr/pull/43) — “fix(romm): re-authenticate when RomM 5.3.1 reports a dead token as HTTP 500,” opened upstream by [@bharvey42](https://github.com/bharvey42). Audit disposition: **Existing coverage**.
- [PR #44](https://github.com/BlizzHacker/romarr/pull/44) — “fix(hub): stop pinning ROM_HUB_ALLOW_UNSANDBOXED=1 at import,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Existing coverage**.
- [PR #45](https://github.com/BlizzHacker/romarr/pull/45) — “feat(collections): strict region filtering and configurable fan-translation languages,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Implemented/adapted**.
- [PR #46](https://github.com/BlizzHacker/romarr/pull/46) — “feat(hub): expose ROM Hub plugin search in Interactive Search with staged import,” opened upstream by [@BlizzHacker](https://github.com/BlizzHacker). Audit disposition: **Implemented/adapted**.
- [PR #47](https://github.com/BlizzHacker/romarr/pull/47) — “fix(ui): remove stray backslash line-continuations that break the web UI script,” opened upstream by [@p4xel](https://github.com/p4xel). Audit disposition: **Implemented/adapted**.
- [issue #48](https://github.com/BlizzHacker/romarr/issues/48) — “Dashboard is completely non-interactive: invalid JS line-continuation backslashes in ui.py break the inline script,” opened upstream by [@MandoMain](https://github.com/MandoMain). Audit disposition: **Implemented/adapted**.

_Attribution ledger refreshed 2026-11-09; 48 source records._
