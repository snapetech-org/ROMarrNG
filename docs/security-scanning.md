# Security scanning

Run `./scripts/security-scan-local.sh` to scan this checkout locally. Semgrep Community Edition uses the free `p/default` community rules with metrics disabled; the source stays on the machine. The rule pack is fetched from the public Semgrep Registry when it is missing or refreshed, so the first scan needs network access. For a disconnected run, set `SEMGREP_CONFIG` to a local rules directory and `SEMGREP_OFFLINE=1` after caching the Semgrep package.

Semgrep runs on supported source and security configuration. It defaults to two worker jobs for memory-limited environments; set `SEMGREP_JOBS` to change that. Trivy selects `secret` for source/config, `vuln` when dependency manifests or lockfiles are present, and `misconfig` for container, workflow, Kubernetes, Helm, or Terraform files.

The installed pre-commit hook runs Semgrep on staged source/config files; Trivy runs during full local scans and any configured CI workflow.

Pushes to `main` and pull requests run Semgrep CE 1.184.0 with current
`p/default` rules and Trivy 0.76.2 with current advisory data. Scanner versions
are reviewed explicitly rather than following mutable `latest` tags. Findings
fail by default; Trivy includes unfixed HIGH/CRITICAL vulnerabilities. Scan
artifacts are retained for review. The Semgrep rules and advisory database are
intentionally refreshed so new vulnerabilities can fail an unchanged revision.

`.trivyignore.yaml` contains one path-scoped, expiring configuration exception:
DS-0002 for the two Dockerfiles' root ownership bootstrap. The entrypoint drops
to PUID/PGID, and native image tests verify the running service's UID. No package
vulnerability is waived. Two source-level Semgrep annotations explain the local
health probe's explicit certificate pin and DAT SHA-1's nonsecurity checksum
purpose; integrity authentication uses SHA-256 separately.

`--ci` ignores implicit Trivy scanner settings and loads this explicit exception.
Use `TRIVY_OFFLINE=1` only after databases are cached. Local diagnostic overrides
`SEMGREP_FAIL_ON_FINDINGS=0` and `TRIVY_EXIT_CODE=0` are not used by enforcing CI.
Semgrep's POSIX backend and two workers support restricted runners; scans allow
30 seconds per rule without abandoning the rest of a file after a timeout.
Review scanner errors as well as finding counts before claiming full coverage.

`requirements.txt` mirrors the complete runtime lock so dependency scanners
recognize it. ROM Hub's direct source URL has no advisory package mapping;
review its pinned source and exercise the sandboxed acquisition proofs. Native
AMD64/ARM64 container proofs and Windows frontend contracts complement source
scans. Scanning cannot prove an absence of exploitable defects.
