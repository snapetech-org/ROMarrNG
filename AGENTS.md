## Runner policy — owner directive, 2026-11-09

Use compatible GitHub-hosted runners for build, test, scan, packaging and release
jobs. Preserve native OS and architecture. Private ephemeral JIT is optional
for jobs needing private networks, special hardware/storage, or explicit JIT
validation; missing private capacity does not block compatible hosted execution.

Keep untrusted pull-request code on disposable runners with no secrets and
minimal read permissions. Preserve active builds and other agents' work. Do not
restart brokers or widen trusted runner access. CodeQL remains disabled under
the separate organization-wide owner directive.

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

