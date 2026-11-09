## Runner policy — owner directive, 2026-11-09

All build, test, scan, package and release jobs require compatible private
ephemeral JIT runners. Hosted runners and fallbacks are prohibited. Preserve
native OS and architecture; unavailable capacity is a provisioning blocker.
Public-fork code requires a disposable VM-backed JIT runner with no secrets,
minimal read access and restricted egress. Never widen trusted runner access.
Preserve active builds and other agents' work; do not restart an active broker.
Before dispatch, verify shared inventory, source routing, deployed broker,
runner-group access and live capacity. A workflow edit alone is not validation.
CodeQL remains disabled under the organization-wide owner directive.

## Upstream source attribution

When ROMarrNG gathers or adapts an idea, report, discussion, patch, rejected
request, issue, or pull request from upstream ROMarr, update
`UPSTREAM_ATTRIBUTION.md` and the user-facing changelog in the same change.
Record the originating upstream URL, the upstream author’s GitHub handle, the
kind of source, and the behavior brought into ROMarrNG. Say that the person
contributed or suggested it to the upstream project and that ROMarrNG
independently adapted, integrated, or verified it. Never imply that the person
contributed directly to, endorsed, or participated in this fork.

Credit closed, unmerged, superseded, and rejected upstream records when their
code or ideas materially informed the fork. Before a release, audit every new
upstream reference in commits, release-note fragments, and changelog entries
for an author link and originating issue, PR, or commit link. Missing source
credit is a release-note defect and must be fixed before publication.

Also record upstream ideas that are planned, referenced, incomplete, rejected,
withdrawn, superseded, not applicable, or not yet reviewed. Put them in a
clearly labelled non-shipped section with an explicit disposition; never imply
that attribution means the behavior is implemented.

