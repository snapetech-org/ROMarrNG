# ROMarrNG 0.14.19 release qualification

Prepared on 2026-11-09. **Not published or announced.** The application and
Home Assistant versions are 0.14.19, and CHANGELOG.md contains the 11 validated
fragments since v0.14.18. Do not mistake preparation or a draft for image delivery.

## Source review and validation

- Merged PRs #74, #71, #60, #70, #58 and #72. PR #56 was closed as superseded
  by the current pipeline, preserving newer audit fixes and publication gates.
- PR #70 applies 836 corrections to existing catalog cells; its incompatible
  runtime expansion was excluded. See [the disposition](localization-pr70-integration.md)
  and linked immutable original review evidence. No native-speaker approval is claimed.
- Issues #59, #62, #63, #66, #67 and #68 were linked to implementation/docs and
  closed as fixed in source. No claim was made that new images are available.
- Local Python 3.13 hash-locked application suite: **2,482 passed, 102 subtests
  passed, seven capability skips, one external-network case deselected**.
  Runner-policy tests were reserved for private JIT rather than counted as local qualification.
- Focused collection/security suite: 180 passed; follow-up API/UI/export suite:
  226 passed; localization suite: 101 passed; folder/catalog suite: 45 passed.
- Localization checker, JavaScript syntax, all workflow YAML parsing and
  changed-file whitespace checks passed. All 29 published release tags have changelog sections.
- Semgrep scanned 290 targets with zero findings. Enforcing Trivy filesystem
  scanning found zero HIGH/CRITICAL dependency vulnerabilities, unsuppressed
  misconfigurations or secrets. The existing expiring Docker bootstrap exception
  remains limited to DS-0002 for the two Dockerfiles.
- GitHub reports zero open code-scanning and Dependabot alerts. CodeQL default
  setup is `not-configured`, and no CodeQL workflow/action invocation is shipped.
  GitHub retains a dynamic CodeQL workflow record and rejects disabling that
  record with HTTP 422; that record is not evidence of an enabled analysis setup.
  Secret-scanning alerts are unavailable because the service is disabled.

## Private execution blockers

The current owner instruction requires private ephemeral JIT exclusively;
compatible native OS/architecture must be preserved. Hosted fallbacks were
removed, and new runs must queue/block when capacity is unavailable.

1. **Linux ARM64:** broker live telemetry reports no slots on
   `macbookair-linux-arm64`: local APFS has about 22 GiB free against a 40 GiB
   floor, and the required NFS/gamespool workspace is unavailable. Unrelated
   data was not deleted to manufacture capacity.
2. **Windows:** the deployed `windows_jit_policy.py` has no ROMarrNG repository
   entry; runner group 11 has zero ROMarrNG workflow refs. Its native image
   readiness telemetry is also false. The frontend contract workflow remains
   Windows x64 and queues; trusted runner access was not broadened.
3. **Public forks:** caller now pins the corrected, read-only syntax child at
   `37d36cbbbab5926e9708d1747821084f14203ebc`. The live group admits `c50770fc5f92df9b4a8ac0b5e95d20bf0561284a`,
   while deployed broker source expects `75e3db919dfbffa916da0c97d752a5b1a013f919`.
   Those older children reference absent validation-engine files; one also
   contains a hosted fallback. The policy owner must reconcile inventory,
   deployed broker and exact group admission to the new immutable child pin.
4. Automatic private push runs currently queue while the deployed broker
   requires explicit dispatch authorization. Use one current-head private CI
   dispatch after verifying live scope and capacity; rerunning an older run
   does not test a new workflow revision. Preserve other repositories' active jobs.

No broker restart, shared group expansion or other-agent cleanup was performed.

## Resume publication

After the policy owner restores the missing native capacity and reconciles
admission, qualify the final main head on private JIT, including the full
pytest suite with runner-policy checks, Windows frontend contracts, both native
architectures' standard/browser acquisition and startup checks, and security
scans. The publication workflow uses explicit `action=publish`,
`runner_pool=private` and `release_tag=v0.14.19`. Create that tag on the qualified
main revision only, then publish and verify images, aliases and release output.

`DISCORD_RELEASE_WEBHOOK` was changed to the user-provided ROMarrNG channel.
The credential is stored only as a repository secret. Send the release
announcement through the release workflow after publication succeeds.

Local evidence is retained under `/tmp/romarrng-maint-20261109` on kspld0.
Temporary test environments are removed after their consumers exit; logs and
the prepared release body are retained. All application qualification above
is local evidence and does not replace missing private native image validation.
