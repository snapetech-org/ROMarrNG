# ROMarrNG 0.14.19 release qualification

Prepared on 2026-11-09. Publication is now proceeding on GitHub-hosted runners. The application and
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

## Hosted release execution

The owner explicitly restored compatible GitHub-hosted execution on 2026-11-09.
The prior private-only blockers are superseded. Linux AMD64 uses ubuntu-24.04,
Linux ARM64 uses ubuntu-24.04-arm, and frontend contracts use windows-2025.
Windows contracts now gate image publication in the same workflow. Fork syntax
validation uses disposable hosted runners with read-only access and no secrets.
The gVisor-specific optional smoke job retains its private capability route.

Publish with `action=publish`, `runner_pool=public` and
`release_tag=v0.14.19` from main. The workflow retains native tests, security
scans, packaged acquisition proofs, image startup checks and alias verification,
then publishes the GitHub Release and sends the Discord announcement.

`DISCORD_RELEASE_WEBHOOK` was changed to the user-provided ROMarrNG channel.
The credential is stored only as a repository secret. Send the release
announcement through the release workflow after publication succeeds.

Local evidence is retained under `/tmp/romarrng-maint-20261109` on kspld0.
Temporary test environments are removed after their consumers exit; logs and
the prepared release body are retained. All application qualification above
is local evidence and does not replace missing private native image validation.
