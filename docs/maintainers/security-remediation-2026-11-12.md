# Container CVE remediation — 2026-11-12

This report records the published-image remediation across `0.14.20` and
`0.14.21`. No live deployment or account was changed.

## Baseline

Trivy 0.76.2 scans of the published `0.14.19` standard and browser images on
AMD64 and ARM64 each found one CRITICAL and 127 HIGH Debian package findings,
plus five HIGH Python findings. The Python report included `setuptools` 70.3.0,
`msgpack` 1.1.2 and `urllib3` 2.7.0. The images used the pinned
`python:3.14-slim` digest built from Python 3.14.10 on 2026-11-05.

## Published remediation

### v0.14.20

The release refreshed signed Debian and Debian Security snapshots to
`20261113T000000Z`, updated the Python packaging tools, and consolidated
Playwright and matching Chromium into the standard image. It retired the
separate browser image, aliases and Unraid template. It also pinned
`actions/setup-dotnet` to the immutable v6.1.0 commit, whose upstream security
release includes updated bundled npm dependencies.

The release was published at
[v0.14.20](https://github.com/snapetech-org/ROMarrNG/releases/tag/v0.14.20),
commit `b2301bd5840b53276e66b4511e46e853269953d9`, with a successful
[release workflow](https://github.com/snapetech-org/ROMarrNG/actions/runs/43340184374).
The standard image digest was
`sha256:859eb936357a31e417076d28fa8c90272638604f712aaf1e7d57d0fa7fca61f0`.

Post-release scans of both standard-image architectures found one CRITICAL and
146 HIGH findings (56 distinct CVEs). The fixable Debian findings were two
`zlib1g` advisories, CVE-2026-76844 and CVE-2026-85091. Trivy also reported
CVE-2025-47273 against `setuptools` 70.3.0; follow-up investigation below
identified that record as pip's embedded vendored-dependency BOM, not the
installed setuptools package.

### v0.14.21

The follow-up moved the final runtime to a clean, pinned Debian Trixie image,
upgraded its Debian packages from the signed snapshot, and copied in the
patched Python runtime. It fixes the two `zlib1g` findings and avoids retaining
packages from the old Python base-image layers. The published runtime imports
setuptools 84.2.1.

Commit `b7d69daaf2e4df33ca28c601aad42c675e1da2af` is on `main` and tagged
`v0.14.21`. The [main CI run](https://github.com/snapetech-org/ROMarrNG/actions/runs/43346064379)
and [release workflow](https://github.com/snapetech-org/ROMarrNG/actions/runs/43347169336)
both passed. The [GitHub release](https://github.com/snapetech-org/ROMarrNG/releases/tag/v0.14.21)
was published on 2026-11-13 UTC. The multi-architecture image digest is
`sha256:f83b9554fcc45da0aa14e28ef65a760fe2e29ebb971fb68ee43ee97e312a1d00`
(AMD64 manifest `sha256:2c6246846dbab815fb61eddab8e04aaf08bc7230387734a5d1b1bd5147a81540`,
ARM64 manifest `sha256:8636868e31e94d15707f5557bf58a26fe2c95e3926d44567bb3b72266d8b9c59`).
The release workflow verified the `latest`, `main`, `master` and `stable` aliases
against the versioned image.

## Published v0.14.21 image scans

Trivy 0.76.2 scanned the published AMD64 and ARM64 manifests with the
vulnerability database refreshed on 2026-11-13. The unfiltered scans each
reported one CRITICAL and 144 HIGH findings (54 distinct CVEs). The additional
HIGH result was CVE-2025-47273, attached to setuptools 70.3.0 in
`pip/_vendor/bom.cdx.json`. Inside both images, `import setuptools` resolves to
84.2.1; the separate GitHub image SBOM also lists 84.2.1. Trivy's investigation
of this same pip BOM finding explains that pip vendors `pkg_resources`, not the
vulnerable setuptools code, and documents excluding that BOM file for image
scans: [Trivy discussion #11031](https://github.com/aquasecurity/trivy/discussions/11031).

The corresponding scans with
`--skip-files '**/pip/_vendor/bom.cdx.json'` each found one CRITICAL and 143
HIGH findings (53 distinct CVEs), all from Debian packages. None had a Trivy
fixed version. This is the remaining image backlog; the current Trixie
snapshot has no reported fix available for these findings. Debian's tracker
marks Trixie vulnerable for
[CVE-2026-6653 in libxml2](https://security-tracker.debian.org/tracker/CVE-2026-6653)
and lists no DSA for Trixie. The image uses the latest packages available from
the pinned signed snapshot; the scan does not claim that all reported CVEs are
fixed.

The source Trivy scan and Semgrep security review passed with zero findings.
Hosted AMD64 and ARM64 tests, Windows frontend contracts, packaged acquisition
proofs, dependency review, release-note validation and native image health
checks passed. CodeQL remains disabled under the owner directive.

## Retained evidence

Scan reports, source-scan logs and Trivy cache are retained on `kspld0` at
`/mnt/disks/scratch/romarrng-cve-20261112-audit1/`.
