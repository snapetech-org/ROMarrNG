# ROMarrNG audit remediation — 2026-11-09

All 44 findings from the 2026-11-09 audit have a code, configuration, or explicit
capability correction in this change. The accepted decision to leave `main`
unprotected is unchanged and is not counted as a defect. No production account,
live library, or deployment was modified during validation.

The original audit examined e8f6b3e (0.14.12). Remediation was developed from b98fe93 (0.14.14), then integrated on
9f03c3d (0.14.18), preserving the concurrent release-pipeline fixes.
The application version remains 0.14.18 until a separate release is prepared;
these changes land on main and do not publish new release tags or containers.
ROM-031 was excluded from the original findings, so numbering skips it.

## Validation and scope

- Clean hash-locked environment: **2,437 tests and 102 subtests passed**, six
  capability-dependent skips and one external-network test deselected. Focused
  exploit regressions, TLS loopback checks, and updater rollback fault injection
  passed. The six local skips were three missing libarchive fixtures, unavailable
  Landlock in this host, a missing optional health-report hook, and no browser.
- Process-lifetime denial of external test networking, including late threads;
  CI additionally executes tests in a network namespace with only loopback.
- Runtime dependency advisory review: no known advisories in the 28 resolved
  indexed packages at review time. ROM Hub is a pinned direct source archive
  and is not covered by package-name advisory matching.
- Semgrep community rules, Trivy dependency/secret/configuration scanning,
  workflow validation, Python compilation, and whitespace checks are release gates.
- Windows frontend contracts passed on windows-2025 (run 42664910034), covering
  actual plugin code with SDK stubs and blocked outbound networking.
- All four standard/browser acquisition proofs passed natively on AMD64 and
  ARM64 at 90d243d (run 42665393974), including signal/truncation denial.
- Native AMD64/ARM64 Docker acquisition/startup and Windows frontend contract
  jobs run in CI. Their execution status is reported with the delivery commit;
  adding a job alone is not evidence that it passed.
- The dependency-review action runs only for pull requests; on other events its
  job completes as a no-op so downstream image gates receive a success result.

The updater tests execute the actual transaction script using temporary release
trees and stubs for systemd, package installation, and download transport. They
cover lookup/pip/configuration/health failures and success. They do not replace
a field upgrade of an actual Proxmox LXC. Desktop proofs use SDK stubs; a real
Playnite/LaunchBox UI and real reverse-proxy deployments were not exercised.
A malicious browser/OS exploit is not ruled out by enabling Chromium's sandbox.
No finite review establishes that all possible vulnerabilities are absent.

## Finding-by-finding closure

“Corrected” describes the repository change and its regression evidence. The
production verification boundaries above remain applicable to every item.

| ID | Audited problem | Correction | Evidence / regression location |
|---|---|---|---|
| ROM-001 | A wrong nonempty API key bypasses TOTP during password login | Require an actually valid administrator API key to bypass interactive TOTP; a wrong nonempty key grants nothing. | romarr/app.py; tests/test_remediation.py |
| ROM-002 | Forward-auth-only installations remain open to first-run claiming | Mark forward-auth deployments claimed before serving setup. | romarr/app.py; test_forward_auth_cannot_be_claimed |
| ROM-003 | Malformed state silently resets security and destroys recoverable state | Fail closed on malformed, unreadable, or invalid existing state; preserve original bytes. | romarr/store.py; tests/test_store.py |
| ROM-004 | Concurrent first-run claims both receive valid administrator sessions | Serialize first-run claims and persist the winning identity before returning a session. | romarr/app.py; test_first_run_claim_is_atomic |
| ROM-005 | Used TOTP recovery codes become valid again after restart | Hash recovery codes and durably consume recovery codes/TOTP counters under a lock. Preserve consumed state after post-publication fsync errors and across concurrent configuration saves. | romarr/totp.py; romarr/durable.py; tests/test_remediation.py |
| ROM-006 | The masked configuration endpoint discloses TOTP and integration secrets | Share recursive credential redaction across configuration views; cover nested provider tokens, TOTP, URL credentials, and webhook URLs. Preserve masked edits. | romarr/settings_security.py; test_config_redacts_all_credentials |
| ROM-007 | Backups labelled as excluding secrets still contain account credentials | Use the same credential classifier for redacted backups; encrypted export remains an intentional credential-bearing operation. | romarr/ops.py; test_portable_backup_is_secret_free |
| ROM-008 | Restoring a redacted backup clears local authentication on the next restart | Preserve local password, keys, TOTP, session and peer identity on every restore. Reject invalid restore schema before committing. | romarr/ops.py; romarr/app.py; tests/test_remediation.py |
| ROM-009 | Persistence failures are swallowed and some queues are not written atomically | Use private atomic writes with file/directory fsync and propagated errors. Serialize the site and Debrid ledgers; reject corrupt existing queues instead of resetting them. | romarr/durable.py; romarr/store.py; romarr/downloaders.py |
| ROM-010 | Invalid settings are persisted before validation and can prevent startup | Validate types/ranges/enums and construct candidate integration/profile configuration before state publication. Preserve previous disk/live settings on failure. | romarr/settings_security.py; romarr/app.py; tests/test_remediation.py |
| ROM-011 | One incomplete TLS handshake blocks the native HTTPS accept loop | Move TLS handshakes into bounded request workers with a short timeout; the accept loop can serve healthy clients concurrently. | romarr/app.py; test_stalled_tls_handshake_cannot_block_other_clients |
| ROM-012 | Invalid TLS configuration silently falls back to plaintext HTTP | Load and validate TLS configuration before opening the listener; missing or invalid certificate/key pairs stop startup. | romarr/app.py; test_invalid_tls_configuration_never_opens_plaintext |
| ROM-013 | State-changing endpoints lack an origin/CSRF boundary for proxy-authenticated browsers | Enforce mutation origin/fetch-site checks and browser CSRF headers, including forward auth. Reject nonempty JSON bodies with non-JSON content types. | romarr/http_security.py; romarr/app.py; tests/test_remediation.py |
| ROM-014 | Native HTTPS password sessions do not automatically receive Secure cookies | Infer Secure cookies from native TLS and trusted proxy HTTPS metadata; ignore untrusted forwarding policy. | romarr/http_security.py; test_native_tls_secure_cookie_and_health_certificate_pin |
| ROM-015 | Debrid-provided names can escape the configured download directory | Validate Debrid directory/member names, reject traversal and symlink sources, and publish within descriptor-confined download roots. | romarr/downloaders.py; romarr/safe_files.py |
| ROM-016 | Single-file and flattened imports follow destination-directory symlinks outside the library | Walk destination parents using directory descriptors and O_NOFOLLOW for all local import layouts. | romarr/safe_files.py; tests/test_remediation.py |
| ROM-017 | Predictable .partial files follow pre-existing symlinks | Replace predictable partial files with private random staging directories and exclusive file creation. | romarr/safe_files.py; romarr/patches.py; tests/test_remediation.py |
| ROM-018 | Direct downloads silently overwrite existing same-name downloads | Give each direct URL its own stable hashed job directory and publish exclusively without overwriting another download. | romarr/downloaders.py; tests/test_site_downloader.py |
| ROM-019 | Interrupted single/flattened imports leave partial final files and poison retries | Stage complete files/game sets and atomically publish with no-replace or exchange operations; errors clean staging while retaining valid prior output. | romarr/safe_files.py; romarr/library.py; test_remediation.py fault-injection cases |
| ROM-020 | Archive expansion and bulk downloads lack enforced resource budgets | Bound actual bytes, member count, ZIP directory allocation, free disk space, and transfer time. Verification shares an aggregate budget across members, independently of the final copy budget; Debrid and Archive.org bulk downloads share an actual-byte budget. Stream archive extraction rather than bulk extraction; reject compressed direct HTTP bodies. | romarr/limits.py; romarr/library.py; romarr/downloaders.py |
| ROM-021 | Reverse UPS patches bypass the output-size safety limit | Validate the effective forward or reverse UPS target size before allocation and bound integer decoding. | romarr/patches.py; test_ups_reverse_output_is_bounded |
| ROM-022 | CRC fallback overrides conflicting SHA-1 and MD5 values | Match the strongest mutually available hash; a stronger hash conflict cannot fall back to CRC verification. | romarr/dat.py; tests/rom_fixtures.py generates real same-size CRC collisions |
| ROM-023 | File size alone is treated as proof that an unknown ROM is a bad dump | Treat size-only matches as UNKNOWN; reserve BAD_DUMP for evidence tied to a known hash/name candidate. | romarr/dat.py; tests/test_dat.py; tests/test_audit.py |
| ROM-024 | A set of files from unrelated games can be labelled one verified game | Require the complete, distinct member set of one DAT game. Reject mixed-game and missing-member sets. | romarr/library.py; tests/test_remediation.py; tests/test_verified_import.py |
| ROM-025 | Untrusted direct-download URLs and redirects can reach internal HTTP services | Pin public HTTP(S) connections to validated DNS addresses, preserve TLS hostname validation, and recheck every redirect. Reject encoded private IPv6 routes and implicit environment proxies. Explicit private-origin exceptions remain narrowly scoped. | romarr/public_http.py; romarr/patches.py; tests/test_remediation.py |
| ROM-026 | Scheduled work and manual Run Now can execute the same job concurrently | Serialize scheduled and manual execution of each job; stop and join scheduler workers during teardown. | romarr/scheduler.py; test_scheduled_and_manual_jobs_are_serialized |
| ROM-027 | The plugin sandbox does not restrict signals to unrelated same-user processes | Deny kill, thread/group queued signals and pidfd_send_signal, including architecture-specific syscall handling. | romarr/plugin_runtime/syscall_guard.py; test_plugin_cannot_signal_parent_or_sibling |
| ROM-028 | Accepted Landlock ABI 1/2 leaves truncation outside the sandbox unrestricted | Require Landlock ABI 3 or newer; reject ABI 1/2 rather than accepting missing truncation protection. | romarr/plugin_runtime/landlock.py; test_old_landlock_abis_fail_closed |
| ROM-029 | Advertised ARMv7 images cannot initialize the required Landlock sandbox | Remove unsupported ARMv7 from image/add-on support. Validate AMD64 and ARM64 on native runners, including packaged sandbox/acquisition proofs. | Dockerfiles; .github/workflows/docker.yml; homeassistant/romarr/config.yaml |
| ROM-030 | Locally launched Chromium explicitly disables its process sandbox | Enable Chromium sandboxing and remove --no-sandbox. There is no automatic unsandboxed browser fallback. | romarr/browser.py; tests/test_new_clients.py |
| ROM-032 | Validation is manual-only and release/dependency review jobs are unreachable | Run tests, acquisition proofs, image validation, scanners, and Windows frontend contracts on push/PR. Put enforcing scanner/dependency gates in the active Docker workflow because legacy scanner workflows are disabled in repository settings. Enable dependency review for real PR events; retain explicit release publication. | .github/workflows; tests/test_workflow_runner_policy.py |
| ROM-033 | Security scans report findings without failing, and omit unfixed vulnerabilities | Make Semgrep findings and Trivy HIGH/CRITICAL findings fail, including unfixed advisories. Keep only documented, narrowly scoped exceptions. | scripts/security-scan-local.sh; .trivyignore.yaml; docs/security-scanning.md |
| ROM-034 | Hosted image builds still require a hardcoded private-network proxy | Retain the hosted-network fix already landed in 0.14.14; no private BuildKit proxy is required. | Upstream repository baseline b98fe93; Docker build workflow |
| ROM-035 | Published builds are not reproducible from the audited source revision alone | Hash-lock all dependency closures and immutable ROM Hub source; pin base image and Debian indexes. Publish saved validated image artifacts rather than rebuilding after checks. | requirements*.lock; Dockerfiles; docker/debian.sources; .github/workflows/docker.yml |
| ROM-036 | Proxmox services run as root with their code and virtual environment writable | Use a dedicated romarr service account, root-owned immutable code/venvs, separate writable state, and constrained systemd write paths. | proxmox/install/configure-service.sh; tests/test_installer.py |
| ROM-037 | The Proxmox updater can restore stale state and leave an incomplete rollback | Stage code and dependencies before stopping; snapshot state only after stop; atomically switch releases and roll back code/venv together without stale-state restoration. Fail closed on release lookup errors. | proxmox/ct/update.sh; tests/test_update_transaction.py runs five isolated failure/success scenarios |
| ROM-038 | Home Assistant metadata still advertises version 0.10.0 | Align the Home Assistant add-on with application version 0.14.18 and supported architectures. | homeassistant/romarr/config.yaml; tests/test_docker_install.py |
| ROM-039 | Tests start background services without teardown or a default network-deny fixture | Disable background startup by default in unit fixtures, close created services, and install a process-lifetime network deny guard before collection. Native CI adds OS network isolation. | tests/conftest.py; tests/network_guard.py; .github/workflows/docker.yml |
| ROM-040 | Administrator sessions cannot be revoked independently and outlive identity-policy changes | Separate session signing from integration keys; persist a revocation epoch; bind sessions to password/security policy. Add revoke/change-password operations and shorten lifetimes. | romarr/auth.py; romarr/app.py; romarr/ui.py |
| ROM-041 | TOTP enrollment activates before confirmation and disable needs no fresh factor | Keep enrollment pending until a current code confirms it. Require fresh factors or the actual master key for enrollment, disable, password changes, revocation, master-key disclosure, and credential-bearing backup export. | romarr/totp.py; romarr/app.py; tests/test_remediation.py |
| ROM-042 | Playnite and LaunchBox sync skip updates and do not deduplicate newly added rows | Upsert by stable ROMarr identity, update metadata/path, and immediately add new entries to the batch lookup. Add repeat-sync and duplicate-batch contracts for both frontends. | contrib/playnite; contrib/launchbox; scripts/test-playnite-sync.ps1; scripts/launchbox_proof |
| ROM-043 | The plugin API advertises uninstall even though it is unimplemented | Remove uninstall from accepted API actions, OpenAPI, and advertised documentation. Install/enable/disable remain supported. | romarr/app.py; romarr/openapi.py; README.md |
| ROM-044 | Health checks use HTTP even when native HTTPS is enabled | Use TLS-aware loopback health checks that authenticate the configured leaf certificate before HTTP, including self-signed certificates. | romarr/healthcheck.py; Dockerfiles; test_native_tls_secure_cookie_and_health_certificate_pin |
| ROM-045 | All users behind one reverse proxy share a pre-authentication rate-limit bucket | Resolve client identity from forwarding chains only when the immediate peer matches configured trusted proxy CIDRs; otherwise use the socket peer. | romarr/http_security.py; tests/test_remediation.py |

## Upgrade requirements

1. Existing browser sessions are invalidated by the new independent signing key.
   Sign in again. Local sessions last eight hours; OIDC sessions at most one hour.
   Re-enrollment requires a confirmation code, and security actions require fresh
   factors or the administrator API key.
2. Fix malformed state rather than deleting it to regain access. Keep the original
   file for recovery. Portable restores preserve local identity and cannot reset it.
3. Configure trusted reverse-proxy CIDRs accurately. Browser mutation requests
   require the CSRF contract; use header API credentials for automation.
4. Public downloads cannot reach private destinations unless their exact origin
   is explicitly listed in `ROMARR_ACQUISITION_PRIVATE_ORIGINS`. Redirects need
   their own approved origin. Normal configured LAN integrations still work.
5. Review the documented transfer budgets for large discs. Use container/disk
   quotas for browser downloads as well. Imports reject symlink parents and need
   Linux atomic directory operations; use actual directories or bind mounts.
6. ARMv7 is no longer supported. AMD64/ARM64 plugin confinement requires
   Landlock ABI 3+, libseccomp, and bounded tmpfs. Local Chromium must be able to
   start its sandbox; remote browsers need separate isolation and quotas.
7. Proxmox moves state to `/var/lib/romarr` and environment configuration to
   `/etc/romarr/romarr.env`. Give the romarr user access to mounted ROM paths;
   extend systemd write paths explicitly for additional data mounts. Releases and
   their matching virtualenvs stay root-owned under `/opt/romarr/releases`.
8. The current release installer will reject releases lacking the new lock/service
   contract. Before a containing release is published, explicitly select main
   using `ROMARR_INSTALL_REF=main` or `ROMARR_UPDATE_REF=main`.
9. Plugin uninstall remains unsupported and is no longer advertised. Disabling
   a plugin is supported. This is an explicit capability correction, not an
   implementation of file deletion.

See [installation](INSTALL.md), [security scanning](security-scanning.md), and
[dependency maintenance](dependency-locks.md) for exact configuration and checks.

## Maintainer follow-through

Keep the newly automatic checks green, update the frozen dependency/base/package
inputs deliberately, and re-review the expiring Docker bootstrap scan exception
before 2027-02-09. That exception covers only DS-0002 for the two Dockerfiles;
there is no waived package vulnerability. Branch protection remains an accepted
operator decision. Runtime secrets continue to rely on filesystem permissions;
this change does not claim encryption of active state or multi-user authorization.

## Delivery verification record

Code revision: [`40bf6ff`](https://github.com/snapetech-org/ROMarrNG/commit/40bf6ff4dfa166cc21a14896dd6087d268e5a0ab).
Status observed on 2026-11-09 at 17:52 UTC; later documentation-only commits do
not change the tested application or workflow implementation.

| Check | Observed result |
|---|---|
| Final local full suite | 2,437 passed, 102 subtests passed; six capability skips, one external-network test deselected |
| Final native ARM64 full suite | 2,438 passed, 102 subtests passed; five capability skips, one external-network test deselected |
| Standard image acquisition, AMD64 and ARM64 | Both passed on the final code |
| Browser image acquisition, AMD64 and ARM64 | Both passed on the final code |
| Windows frontend contracts | Passed on the final code |
| Semgrep | Passed on final code; local changed-file scans also had zero findings and zero engine errors |
| Local Trivy filesystem scan | Zero HIGH/CRITICAL dependency, secret, or unsuppressed configuration findings |
| Enforcing negative fixtures | Semgrep and Trivy each returned exit status 1 for deliberately unsafe scratch fixtures |
| Final AMD64 suite, Trivy CI, release-note CI | Queued at this observation; not represented as passed |
| Final image boot/export jobs | Waiting for their prerequisite jobs at this observation |

Track the exact code revision's [Linux checks](https://github.com/snapetech-org/ROMarrNG/actions/runs/42667278471)
and [Windows contracts](https://github.com/snapetech-org/ROMarrNG/actions/runs/42667278944).
The preceding revision's [Linux run](https://github.com/snapetech-org/ROMarrNG/actions/runs/42665393974)
already passed both native full suites, all four acquisition proofs, both
security scans, and both standard-image boot/export jobs. These earlier results
are supplementary evidence, not substitutes for pending checks on the final code.

The remaining local skips concern real libarchive extraction (three fixtures),
Landlock support in this host (covered by native CI), an optional health-report
hook, and a local Chromium installation. The native suite can exercise Landlock.
Desktop SDK stubs and simulated Proxmox system commands remain the limits stated
above. Production upgrades, live accounts, and an actual Chromium hostile-page
exercise were not performed.
