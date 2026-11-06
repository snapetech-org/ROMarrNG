# ROMarrNG PR #70 W285–W304 root cross-audit

Root reconciled 240 cells across 20 source IDs and 12 locales, pinned to head 363601fd2597f0fb97adff97554e651c2bea2d99 and tree 1f8ada1746f53796e2b4a8f43f9a0075150aa5d7.

- Primary review: 171 accept-current, 26 corrections, 19 refinements, 24 caller-path holds.
- Independent blind review: 142 retain, 74 revise, 24 caller-path holds.
- Root reconciliation: 132 accept-current, 79 corrections, 5 refinements, 24 holds; 84 exact target changes.
- The holds at ranks 286 and 304 remain unchanged in all 12 locales.
- Exact targets and rationales are in cross-audit-ledger.jsonl and selected-changes.jsonl. root-application-authorization.json authorizes only those 84 exact target/hash changes.
- The withdrawn earlier blind packet is excluded. The independent blind packet in this directory is review-v2.
- Native-speaker approval and exact-head product browser review are not established. No tests, builds, scans, CI, workflow changes, merge, release, or tag were made.

## Selected changes by rank

- 285: Published {entries} ES-DE entries and {covers} shared covers. — 8 locale cells
- 287: Read ROM hashes from the library for netplay — 12 locale cells
- 288: Read {seen} entries and found {added} with a hash. Netplay can match those. The other {without} are catalogued entries your library has never scanned off a disk, so there is nothing to match them on. {confirmed} matched a No-Intro or Redump dump and are marked verified. — 2 locale cells
- 289: Read {seen} entries and found {added} with a hash. Netplay can match those. The other {without} are catalogued entries your library has never scanned off a disk, so there is nothing to match them on. None matched a DAT, so all are unverified -- check the DAT directory under Settings. — 1 locale cells
- 291: Reading your library in the background. This page does not have to stay open. — 7 locale cells
- 292: Ready to scan — 6 locale cells
- 293: Recommended · IGDB popular — 11 locale cells
- 294: Refresh metadata — 6 locale cells
- 295: Rejected the API key — 4 locale cells
- 296: Release Profile — 5 locale cells
- 298: Released — 12 locale cells
- 299: Remove path mapping for {path} — 2 locale cells
- 300: Remove platform folder mapping for {folder} — 3 locale cells
- 301: Remove this path mapping — 4 locale cells
- 303: Rename batch applied. — 1 locale cells

## Packet contents

candidate-free-input/ contains the source and current catalog snapshot.
primary-review/ contains the primary ledger.
blind-review/ contains the separate candidate-free blind ledger.
cross-audit-ledger.jsonl contains all 240 reconciled decisions.
selected-changes.jsonl contains exact selected target values and hashes.
pinned-state-verification.json records the live PR and ref check.
verify_cross_audit.py and SHA256SUMS.txt verify the packet.
