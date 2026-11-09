# ROMarrNG 0.14.19 release qualification

[ROMarrNG v0.14.19](https://github.com/snapetech-org/ROMarrNG/releases/tag/v0.14.19)
was published on 2026-11-09 at 20:03:25 UTC from
`0233888da3528f05a8b713ecb0438fcf96584911`. The standard and browser images
support AMD64 and ARM64. Both release-note messages were accepted through the
new ROMarrNG Discord webhook.

## Hosted delivery evidence

The [hosted release run](https://github.com/snapetech-org/ROMarrNG/actions/runs/42684261392)
completed all **18 build and validation jobs successfully**, including:

- Native AMD64: 2,489 tests and 102 subtests passed, five capability skips,
  one external-network case deselected.
- Native ARM64: 2,489 tests and 102 subtests passed, five capability skips,
  one external-network case deselected.
- Windows frontend contracts, enforcing Semgrep and Trivy scans, release-note
  coverage, all four native packaged-acquisition proofs, standard/browser image
  boot checks, publication with SBOM/provenance, and stable alias verification.

After those jobs passed, the publication-only job remained in the hosted queue.
It was cancelled to prevent duplicate publication/announcement, and the same
prepared changelog and live alias checks were used to finalize the GitHub Release
and Discord delivery directly. The run's overall cancellation status describes
that stopped finalizer; no native build or validation gate was waived.

The [legacy Unraid alias sync](https://github.com/snapetech-org/ROMarrNG/actions/runs/42688088893)
also passed both jobs. Organization and legacy rolling aliases point to:

- Standard: `sha256:9ad187c55989917d8b415aacf516d787bca4e1724b49a7cd8ef606b4ee1b6f1d`
- Browser: `sha256:c13f049e0922b2f14f84a1c0491ead69b496a400718280d9a73b4adbb99e4b39`

Pull `ghcr.io/snapetech-org/romarrng:0.14.19` or
`ghcr.io/snapetech-org/romarrng:0.14.19-browser`.

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
  The initial local run excluded runner-policy tests; the final hosted suites include them.
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
The credential is stored as a repository secret and is absent from repository
files and logs. The two-part release announcement was delivered after publication.

Local evidence is retained under `/tmp/romarrng-maint-20261109` and
`/tmp/romarrng-hosted-release-20261109` on kspld0.
Temporary test environments are removed after their consumers exit; logs and
the prepared release body are retained. The hosted delivery evidence above records the final native image qualification.
