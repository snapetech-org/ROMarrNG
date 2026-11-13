# Container CVE remediation — 2026-11-12

This release consolidates browser downloads into the standard image and
addresses findings in the published `0.14.19` standard and browser images. It
retires the separate browser image, aliases and Unraid template. No live
deployment or account was changed.

## Baseline

Trivy 0.76.2 scanned the published AMD64 and ARM64 standard and browser images
with the vulnerability database refreshed on 2026-11-13. Each image had one
CRITICAL and 127 HIGH Debian package findings, plus five HIGH Python package
advisories. The Python findings were in bundled `setuptools` 70.3.0,
`msgpack` 1.1.2 and `urllib3` 2.7.0. The published Python base manifest was
still the pinned `python:3.14-slim` digest, built from Python 3.14.10 on
2026-11-05, so refreshing the Debian package snapshot and Python tooling was
the available remediation in this change.

Debian's [Trixie libxml2 tracker](https://security-tracker.debian.org/tracker/source-package/libxml2)
listed the critical CVE-2026-6653 and several high-severity libxml2 advisories
without a stable fix at review time. Other Debian package rows also lacked a
fixed version. The Trivy image reports are retained on `kspld0` at
`/mnt/disks/scratch/romarrng-cve-20261112-audit1/`.

## Changes

- Move the signed Debian and Debian Security snapshots to
  `20261113T000000Z`.
- Bundle the pinned Playwright 1.62.0 client and matching Chromium in the
  standard image. Browser downloads use the same image and Unraid template as
  the rest of the application; an external browser server remains optional.
- Hash-lock pip 26.3 and setuptools 84.2.1 in the builder and final image. The
  final-layer install replaces vulnerable versions inherited from the
  unchanged Python base image.
- Pin `actions/setup-dotnet` to the immutable v6.1.0 commit. Its upstream
  [security release](https://github.com/actions/setup-dotnet/releases/tag/v6.1.0)
  includes updated bundled npm dependencies.
- Update the application and Home Assistant add-on version to 0.14.20.

The source Trivy scan and Semgrep scan passed locally with zero findings. A
direct Trivy scan of the new hash-locked runtime tooling reported zero HIGH or
CRITICAL advisories. Hosted native builds, release gates, and scans of the
published 0.14.20 images are recorded below after completion.

## Release verification

Pending hosted validation and post-publication AMD64/ARM64 image scans.
