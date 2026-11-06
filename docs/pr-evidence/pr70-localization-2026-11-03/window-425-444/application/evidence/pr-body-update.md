## Latest localization delivery — W405-W424 (2026-11-03)

Applied in commit 7681ea470ee0f387cd3a1a5be0541979d9cd06f6. PR #70 remains open and draft at head 7681ea470ee0f387cd3a1a5be0541979d9cd06f6 / tree f8b34f29814233cb10dd9d608d5a69ce539b9f6d on task/localization-translation-review-20261030.

Primary, independent blind, and cross-audit review reconciled all 240 cells across 20 catalog-insertion entries and 12 locales: 166 accept-current, 20 corrections, 6 refinements, and 48 holds. Applied 26 exact-hash updates to romarr/ui-labels.json; 166 cells are no-ops. All 288 carried holds remain unchanged. The 48 current holds are at positions 405, 407, 408, and 416, where current caller/dispatch evidence does not provide a reliable standalone translation route.

The [W405-W424 evidence packet](https://github.com/snapetech-org/ROMarrNG/tree/7681ea470ee0f387cd3a1a5be0541979d9cd06f6/docs/pr-evidence/pr70-localization-2026-11-03/window-405-424/README.md) includes candidate-free input, primary and blind reviews, the cross-audit, exact-hash apply plan, 240-cell catalog readback, and portable application verifier. Key and locale order, source text and hashes, all non-target values, review metadata, and workflow files are unchanged.

The application verifier, packet checksums, and git diff --check pass. Qualified native-speaker and exact-head browser review are not claimed. No tests, builds, CI, workflow edits, merge, release, or tag were performed.

---

### Earlier follow-up: ROMarr source review status before W385-W404 (2026-11-03)

At the time of this earlier follow-up, PR head was 8a15dd1c3487d17e62d78a1b80222b7eb6033c6b. This documentation-only follow-up clarifies that both localized catalog entries remain marked draft. Code commit 31c3ab295cdc800863f68deff518c38a380d84f4 and application-pin commit 5dfd7341806aa7c83dc3163a6f1d867d8a8906ca remain the source-bound localization change and its exact-head record. The post-push verifier passes; no catalog values changed.

### Source-bound localization fixes: launcher scan and TOTP (2026-11-03)

- Commit 31c3ab295cdc800863f68deff518c38a380d84f4 localizes the exact local launcher-scan error shape using the existing error-type template. Other API/provider text and the network-failure fallback stay opaque.
- The TOTP enrollment note uses its existing catalog entry only when the returned text exactly matches the English source. Any other note stays opaque.
- Both existing keys have matching translation hashes and nonempty values in all 12 target locales; no catalog values or English source IDs changed.
- Commit 5dfd7341806aa7c83dc3163a6f1d867d8a8906ca pins the application evidence. The exact post-push verifier passes. Evidence: docs/pr-evidence/pr70-localization-2026-11-03/romarr-source-bound-localization/.
- Browser and qualified native-speaker review remain outstanding. No tests, builds, scans, CI dispatches, workflow changes, merge, release, or tag occurred.

<!-- w365-cross-audit-20261103 -->
### W365–W384 catalog review — 2026-11-03

Primary, blind, and independent cross-audit reviews reconciled all 240 cells: 125 accept-current, 75 corrections, and 40 refinements. All 166 primary/blind target differences were adjudicated; 154 final targets use the primary choice and 12 use the blind choice. Applied 115 exact-hash updates to romarr/ui-labels.json. All 288 previous holds remain unchanged, and no new holds were added. Rank 368’s twelve shared selection-action cells were reviewed by locale against their caller context.

Catalog application: e3d843b6c190f03ad8e5292bc60bfffb912ab9fe; verification follow-up: 6eb40719ea270bb3cae024d771665e7006a85822. Evidence and exact-head verifier: docs/pr-evidence/pr70-localization-2026-11-03/window-365-384/.

The verifier passes all cell, hash, key-order and token checks. The sealed cross-audit builder was preserved byte-for-byte and has one trailing blank line, the sole git diff --check warning in this bundle. Qualified native-speaker and exact-head headed-browser review remain pending. No tests, builds, scans, CI dispatches, workflow edits, merge, release, or tag were performed.

---

## Localization W345–W364 — catalog and evidence milestone

Applied the cross-audited wording decisions in commit `d1698b94781c3c84e91faf03c75e8c308dc39c34`. The 240-cell readback confirms 144 catalog updates (93 corrections and 51 refinements), 96 retained current translations, and zero holds in this window. All 288 prior callerless holds remain unchanged. The catalog structure, ordering, and all non-target cells are unchanged; translation status remains draft.

The sealed candidate-free input, primary and blind reviews, cross-audit, application plan/readback, and verification scripts are recorded in [`docs/pr-evidence/pr70-localization-2026-11-03/window-345-364/`](https://github.com/snapetech-org/ROMarrNG/tree/d1698b94781c3c84e91faf03c75e8c308dc39c34/docs/pr-evidence/pr70-localization-2026-11-03/window-345-364/).

Ranks 346 and 350 remain separate required runtime-dispatch follow-ups: both are app-authored strings with concrete UI callers, but currently pass through `apiMessageMarkup` as opaque content. This milestone records their text-quality decisions only; a separate source-bound fix is still required to route them through translation. No caller pins or source paths changed. No native-speaker or browser review is claimed.

The evidence verifiers, exact per-cell readback, checksum verification, and `git diff --check` passed. No tests, builds, scans, CI, or workflow changes were made.

---

### Previous PR description (preserved verbatim)

## Localization review — W325–W344

At commit `6bef0c74632067906fd07279fa6bd3fd59159a48`, applied 57 independently reviewed catalog updates across 12 locales (43 corrections and 14 refinements). The 240-cell readback retains 159 existing values and keeps all 24 callerless cells on hold at positions 329–330.

The [review and application evidence](https://github.com/snapetech-org/ROMarrNG/blob/6bef0c74632067906fd07279fa6bd3fd59159a48/docs/pr-evidence/pr70-localization-2026-11-03/window-325-344/README.md) includes candidate-free inputs, separate primary and blind reviews, an independent cross-audit, and a reproducible exact-target verifier. Three cells are flagged for qualified native-speaker follow-up: French at position 339 and Simplified and Traditional Chinese at position 343. No native-speaker signoff or exact-head browser acceptance is claimed; this commit has no deployment and zero check runs.

No tests, builds, scans, CI runs, workflow edits, merges, releases, or tags were performed for this window.

<!-- localization-window-w285-304 -->
### Latest localization delivery — W285–W304 (2026-11-03)

PR #70 remains open and draft at exact head [`9ecde2b300fea97e52846f274fbcae19cff1fcc5`](https://github.com/snapetech-org/ROMarrNG/commit/9ecde2b300fea97e52846f274fbcae19cff1fcc5) / tree `df77009a42ee07366803f7553f6dcab25b62c638` on `task/localization-translation-review-20261030`.

Primary, independent blind, and root cross-audit reviews covered all 240 source×locale cells. Final root dispositions: 132 accept-current, 79 corrections, 5 refinements, and 24 caller-path holds. Applied the 84 exact authorized target values and corresponding canonical `translationHashes`.

Exact readback matched all 240 cells. Exactly 84 target values and 84 canonical translation hashes changed; zero non-target translations or hashes changed. Message IDs and catalog key order, locale order, review/status metadata, placeholders, markup, and protected literals passed verification. The 24 holds at ranks 286 and 304 remain unchanged across all 12 locales because the caller paths do not establish a localizable UI message.

Evidence: [complete W285–W304 packet](https://github.com/snapetech-org/ROMarrNG/tree/9ecde2b300fea97e52846f274fbcae19cff1fcc5/docs/pr-evidence/pr70-localization-2026-11-03/window-285-304/README.md), [root cross-audit report](https://github.com/snapetech-org/ROMarrNG/blob/9ecde2b300fea97e52846f274fbcae19cff1fcc5/docs/pr-evidence/pr70-localization-2026-11-03/window-285-304/third-party-cross-audit/report.md), and [application readback and verifier](https://github.com/snapetech-org/ROMarrNG/tree/9ecde2b300fea97e52846f274fbcae19cff1fcc5/docs/pr-evidence/pr70-localization-2026-11-03/window-285-304/application/).

Catalog SHA-256: `ce7e12ffe1bcf520295dd7edbccf77ca992bb5d481b77d2a4daebd9b492ed690`. Application evidence checksum-list SHA-256: `bd137470e47f89400f11118d36567d983c0542fe649f96d99424b7b9ab4709f1`. Candidate-free manifest JSON SHA-256: `561d10943ebd3aa1f091942b7a83b408c0157e4bd2ae665d44397986d4d45610`; its checksum-list SHA-256: `1047511955ef60dc180a49bdaef7a86452c70e9196fd681174732e98d408f338`. Root cross-audit ledger SHA-256: `1d8dbb94305a008b530a7c0998ee80d11a5f832b8937923d523165c6f01c7944`.

The pre-commit Semgrep scan was not run because this task prohibited scans. The pre-push image-alias and stable-image-tag checks passed. No tests, builds, other scans, CI dispatches, workflow edits, merges, releases, or tags were made. Qualified native-speaker approval and exact-head browser review are not recorded.

<!-- localization-window-w265-284 -->
### Latest delivery — W265–W284 (2026-11-03)

PR #70 remains open and draft at exact head `363601fd2597f0fb97adff97554e651c2bea2d99` / tree `1f8ada1746f53796e2b4a8f43f9a0075150aa5d7` on `task/localization-translation-review-20261030`. The candidate-free, primary, independent blind, and third-party cross-audit reviews cover all 240 cells across 20 source IDs and 12 locales. Final dispositions are 38 accept-current, 33 corrections, 1 refinement, and 168 caller-path holds. The 34 selected target values and their canonical `translationHashes` are applied; translation status remains `draft` and locale/review metadata is unchanged.

Exact readback matched all 240 cells. Exactly 34 selected translation values and 34 matching canonical translation hashes changed; zero non-target translations or hashes changed. Message IDs, catalog order, locale order, metadata, placeholders, and markup remain intact. The 168 holds at ranks 269–282 remain unchanged because dynamic provider/Prowlarr API diagnostics are rendered as raw text without an explicit localized template path. Dynamic names and diagnostic values remain opaque.

Evidence: [complete W265–W284 packet](https://github.com/snapetech-org/ROMarrNG/tree/363601fd2597f0fb97adff97554e651c2bea2d99/docs/pr-evidence/pr70-localization-2026-11-03/window-265-284-current-ranks/README.md), [cross-audit report](https://github.com/snapetech-org/ROMarrNG/blob/363601fd2597f0fb97adff97554e651c2bea2d99/docs/pr-evidence/pr70-localization-2026-11-03/window-265-284-current-ranks/third-party-cross-audit/report.md), and [application readback and verifier](https://github.com/snapetech-org/ROMarrNG/tree/363601fd2597f0fb97adff97554e651c2bea2d99/docs/pr-evidence/pr70-localization-2026-11-03/window-265-284-current-ranks/application/).

Candidate-free manifest JSON SHA-256: `d8c2d6ce7a0e4c146702cb25d4ba42bbb5eddb813790a4e27a49017f4fc9123d`. Candidate-free checksum-list SHA-256: `6a9a1ccec32c9598788c46f06a7edeff7211fb22b8e74cf0c777962e8ac67aae`; the blind evidence records these as distinct fields.

Qualified native-speaker approval is not recorded. No W265–W284 exact-head browser review is claimed; the existing browser evidence predates this commit. The automatic pre-commit Semgrep hook reported 0 findings; that is hook output, not PR validation. No product tests, builds, CI runs, workflows, merges, releases, or tags were performed for this window.

<!-- localization-caller-follow-up-226-241 -->
### Latest caller-bound localization review — positions 226, 232, 237, and 241 (2026-11-03)

PR #70 remains open and draft at exact head [e7f8d0dcb11d8d94c8a89c37cb9ab451d72810a6](https://github.com/snapetech-org/ROMarrNG/commit/e7f8d0dcb11d8d94c8a89c37cb9ab451d72810a6), tree 016587d26f04d2920a30878236f1933a57e27901.

- Primary, independent blind, and third-party cross-audit reviews covered 48 cells: 33 accept-current, 9 corrections, 3 refinements, and 3 holds.
- Applied 12 exact-hash translation changes for positions 237 and 241; the three Hindi, Japanese, and Korean position-241 fragment cells remain unchanged and held. ROMarr translation hashes were recomputed for all 12 updated values.
- All 48 selected outcomes read back with zero mismatches. The 1,836-message catalog and every non-target value remain intact; all 36 protected-literal occurrences passed.
- Input, primary, blind, cross-audit, application plan, readback, and checksums are in [the caller-follow-up evidence packet](https://github.com/snapetech-org/ROMarrNG/blob/e7f8d0dcb11d8d94c8a89c37cb9ab451d72810a6/docs/pr-evidence/pr70-localization-2026-11-03/caller-follow-up-226-241/README.md).
- Machine review does not establish qualified native-speaker approval. Exact-head headed-browser acceptance remains pending because the isolated desktop-pool coordinator is unavailable; this head has no deployment or status checks. No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were performed for this window. Existing pre-push image-alias policy checks passed.

### Current head — W226–W245 and source-location follow-up (2026-11-03)

PR #70 remains open and draft at `e0cb91389334fe534ff44ccfc72cbb2c152a93b4`, tree `3876dd57816aaf75bb8b1a56a75a5045d216c461`, on `task/localization-translation-review-20261030`. The exact-head W226–W245 review covered 240 source/locale cells: 171 accept-current, 17 corrections, 14 refinements, and 26 active holds. The 31 selected target changes and hashes are applied. Twelve translations for the audited orphan no-comma source entry were retired from active metadata and catalog; historical bundles remain intact.

The runtime changes add a fixed local template for the no-title path, localize the exact local netplay `missing` verdict without forwarding peer templates, and translate only explicit app-owned facet labels while preserving and reformatting counts. A final review closed an inherited-property lookup edge case. The latest metadata-only follow-up corrected stale source locations for `ui.no-title.8cb9a5c65b` and `ui.on-disk-plays-now.325a11ceda` to their exact current callers; no catalog target changed in that follow-up.

Evidence: [W226–W245 review packet](https://github.com/snapetech-org/ROMarrNG/blob/e0cb91389334fe534ff44ccfc72cbb2c152a93b4/docs/pr-evidence/pr70-localization-2026-11-03/window-226-245/README.md) and [source-location follow-up](https://github.com/snapetech-org/ROMarrNG/blob/e0cb91389334fe534ff44ccfc72cbb2c152a93b4/docs/pr-evidence/pr70-localization-2026-11-03/window-226-245/source-location-followup.md). The coverage audit at the W226 application head reduced diagnostics from 415 to 400 (13 old locations and two duplicate rows resolved, with none introduced); the next follow-up corrected two further stale locations. Remaining diagnostics are not claimed clean.

Checksum manifests validate. `git diff --check` passed for source and documentation changes, and the pre-push stable-image alias policy passed. The pre-commit Semgrep hook was skipped because scans must run on private ephemeral JIT. No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were made. The branch has no reported checks. Qualified native-speaker approval and exact-head headed-browser acceptance remain outstanding. The isolated Agent Desktop Pool coordinator returned unavailable; no desktop or persistent Agentic VM session was touched.


### Latest delivery — W186–W205 (2026-11-03)

PR #70 remains open and draft at head `bef31ca8a94f21273b11303524d79bd9c5344305`, tree `7616d96ddd3a1bfe8078d43492eb5bea7213f080`, on `task/localization-translation-review-20261030`. This exact-head review covered 240 cells across 20 source IDs and 12 locales. Root adjudication accepted 137 current values, selected 17 corrections and 26 refinements, and retained 60 caller-context holds. The 43 selected values and their matching `translationHashes` are applied in `romarr/ui-labels.json`; every changed cell remains `draft`.

The 60 held cells remain unchanged across ordinals 188, 197, 198, 200, and 201 because exact-head renderer paths return opaque API text or cannot match the catalog substring. Primary, blind, cross-audit, root decisions, exact-hash apply plan, and 240-cell readback are in [the W186–W205 evidence packet](https://github.com/snapetech-org/ROMarrNG/blob/bef31ca8a94f21273b11303524d79bd9c5344305/docs/pr-evidence/pr70-localization-2026-11-03/window-186-205/README.md). All 240 targets and hashes read back with zero mismatches; the ordered 1,837-message key set is unchanged.

Primary review counted 137 accept-current, 23 corrections, 20 refinements, and 60 holds; independent blind review counted 159 accept-current, 13 corrections, 8 refinements, and 60 holds. Cross-audit compared 36 nonmatching recommendation cases. Notable adjudications: French 204 uses wording that preserves “removed you” without changing it to “deleted your account”; Traditional Chinese 202 uses `多人遊戲` with the corrected rationale; Indonesian 194 retains the current compact instruction over a blind-only alternative.

This machine review does not establish native-speaker approval. Qualified native-speaker approval and current-head headed-browser acceptance remain pending. `git diff --check` passed. The local Semgrep hook was bypassed because scans must run on private ephemeral JIT; the push hook confirmed stable image aliases are consistent. No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were made for this milestone.



### Latest delivery — W166–W185 (2026-11-03)

PR #70 remains open and draft at head `55ee760ea9600f71cc27cba35e098a082445dac8`, tree `dbc192813f6347f4307ff8417d505624958eb321`, on `task/localization-translation-review-20261030`. This exact-head review covered 240 cells across 20 source IDs and 12 locales: 175 accept-current, 25 corrections, 16 refinements, and 24 holds. The 41 approved corrections and refinements are applied to `romarr/ui-labels.json`; all 24 held cells remain unchanged across ordinals 177 and 184 because the sentence is split around inline code or no exact caller is pinned.

The candidate-free input, primary and blind reviews, root adjudication, exact-hash apply plan, and 240-cell readback are in [the W166–W185 evidence packet](https://github.com/snapetech-org/ROMarrNG/blob/55ee760ea9600f71cc27cba35e098a082445dac8/docs/pr-evidence/pr70-localization-2026-11-03/window-166-185/README.md). All 240 targets read back with zero mismatches; the ordered 1,837-message catalog key set is unchanged. Changed targets remain `draft`.

Machine review does not establish native-speaker approval. Exact-head browser acceptance is still pending. `git diff --check` passed. The local Semgrep hook was skipped because scans must run on private ephemeral JIT; no tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were made for this milestone.


### Prior milestone — W146–W165 (2026-11-03)

### Prior milestone — W126–W145 (2026-11-03)

PR #70 remains open and draft at head db895a97e9871952a0b952e1d119e32e06cf168d, tree f1edf8319eb3dbd29ac5fe1e279216c5b96ecc6a. The primary, independent, and root-adjudicated review covered 240 cells across 20 source IDs and 12 locales: 182 accept-current, 27 corrections, 31 refinements, and 0 holds. The 58 correction and refinement targets and their canonical translation hashes are applied to `romarr/ui-labels.json`. All affected cells remain `draft`; the catalog retains all 1,837 message IDs and its existing message/key/status/hash structure.

The checksum-backed input, primary, independent, root, adjudication, apply plan, and readback are in [the W126–W145 review record](https://github.com/snapetech-org/ROMarrNG/blob/db895a97e9871952a0b952e1d119e32e06cf168d/docs/pr-evidence/pr70-localization-2026-11-03/window126-145/README.md). This machine review does not establish native-speaker approval. Exact-head browser review remains pending. No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were made for this milestone.



### Prior milestone — first 100 selected source IDs (2026-11-03)

At the first-100 delivery, PR #70 was open and draft at head 5d999ff7667ae4c5642f1f11b63ad9880d19672c, tree 93fcf748c46a4c1cef116c2a4ef06305137ecfe4. The first 100
selected source IDs (1,200 locale cells) received primary review, independent
cross-review, and root adjudication. Root finalized 554 accept-current, 181
corrections, 57 refinements, and 408 holds across 34 IDs. The 238 correction
and refinement values, with their canonical translationHashes, are applied to
romarr/ui-labels.json. All planned values and hashes read back; the catalog
retains all 1,837 message IDs and existing per-message translation/status/hash
key sets.

The primary, blind, root, exact-hash apply, and readback evidence is in
[the first-100 review record](docs/pr-evidence/pr70-localization-2026-11-03/first-100-selected-source-ids/README.md).
The four hundred eight holds remain because exact caller/render evidence is
insufficient for those cells. No exact-head deployment is available for app
browser review; qualified native-speaker approval is not established.
No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or
tags were made for this milestone. The pushed commit has no check runs or
deployment recorded at this update.

The latest W106–W125 follow-up reviewed 240 cells across 12 locales and retained 48 caller-context holds. Final root dispositions are 148 accept-current, 33 corrections, 11 refinements, and 48 holds; 44 exact-hash catalog targets changed in the window. A separate EmuDeck full-sentence supplement reviewed 36 adjacent text-node cells, changed 32 and retained four, including both inline path literals in order. Twelve cells overlap source ordinal 119; 20 additional catalog changes cover two further source IDs. Combined review evidence covers 264 unique cells and 64 changed values across 14 IDs. The German sentence received a final naturalness refinement. The catalog readback preserves all 1,837 message IDs and per-message status/hash structures. Evidence: [W106–W125 and sentence-context review](docs/pr-evidence/pr70-localization-2026-11-03/window106-125/README.md).

This follow-up also wires only two allowlisted, fixed organizer error messages through their source-bound templates; dynamic API values keep escaped opaque rendering. Independent code review found no material safety issue. No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were made for this follow-up. The exact head has no check runs or deployments recorded; qualified native-speaker and current-head deployed browser acceptance remain outstanding.

This PR completes direct catalog parity for the 1,837 ROMarr UI messages in the 12 target locales: Spanish, Simplified Chinese, Hindi, German, Japanese, French, Brazilian Portuguese, Arabic, Korean, Traditional Chinese, Vietnamese, and Indonesian.

- Adds 5,808 previously missing translations, 484 per locale, with source-bound target hashes and per-cell status `draft`.
- Includes 214 earlier high-confidence corrections across 65 existing message IDs, stable source IDs for 10 account-connection instructions, trusted fixed-message descriptors, dynamic-value bidi isolation, and language selectors.
- Wires existing catalog translations into the Get Started page's SeerrNG integration sentence and “Where you actually play” heading. The page now uses locale-aware spacing and sentence punctuation for Japanese and Chinese. This source-only fix is `81b5ec7b` and does not change catalog values.
- Keeps locale availability and English fallback configuration unchanged.
- Retains source templates and values for public login/setup errors and keeps invitation failure text source-bound, so the active locale can rerender those messages and the submit state (`a1278ac`).

- Application/catalog follow-up at `f861b9b7b08cd3fe1012d46d082ef6ec71012074` adds 45 exact-hash reviewed target corrections (40 accepted proposals, 5 refinements); 3 reviewed targets were retained unchanged. Changed targets remain `draft`, with no native-speaker approval recorded.
- Localizes the known library-loading and organizer missing-metadata messages through allowlisted source-bound templates, keeps unknown API text opaque, and uses the existing catalog template for organizer pagination.
- Follow-up commit `d259a92f89657b5c79be3653ed811e2bf8e01c58` wires all four `listsNav` labels through their existing 12-locale catalog messages. The exact-head audit, source finding, and checksums are in [listsNav source-wiring evidence](docs/pr-evidence/pr70-localization-2026-11-02/listsnav-source-wiring/README.md).

## Translation review

The 5,808 draft cells were reviewed against the frozen source bundle at `79b144e38a0d1ab26315c5eea24c9e8a40700e8e`. After exact-hash follow-up at catalog head `d9a6e515ae43e3cb4cdffcb205fe9c0bcaaab97d`, the reconciled result is:

- 2,462 accepted unchanged.
- 3,346 correction targets applied, including all 21 candidates that had previously remained held.
- 17 linked-guide sentence-context corrections applied across 11 locales; 16 were previously accepted fragments, and one refines the already corrected Vietnamese guide title for sentence case.
- 0 held target corrections remain.

All changed cells were source/target-hash checked. The 5,808 targets remain `draft`; no native-speaker approval is recorded. Placeholder, protected-literal, and numeric-token checks passed on the catalog revision. An exact-hash reconciliation at the current catalog head accounts for all 21,996 populated cells: 15,876 unchanged baseline targets, 300 baseline correction targets, 2,462 accepted new targets, 3,308 corrected new targets, 38 54f1 follow-up targets, and 12 current “Requests per pass” targets; no current cell is unaccounted for. A focused a127 review accepted the 12 “Requests per pass” values unchanged. The 12 `ui.at` fragments and paired `ui.per-pass` fragments have no active UI source callsites (see `obsolete-at-crossreview-12-locales/callsite-inventory.json`). Four `ui.at` values (Japanese, Korean, Simplified Chinese, and Traditional Chinese) lack standalone linguistic dispositions because their meaning depended on the obsolete numeric-control construction; they remain unreachable catalog records and do not represent unresolved rendered UI copy. Evidence: `docs/pr-evidence/pr70-semantic-review-2026-11-01/`. The frozen a127 review-pool audit reconciles 21,996/21,996 populated cells, with zero unaccounted cells and zero eligible disjoint keys; it makes no new decisions and does not establish native-speaker approval. The previously populated 16,176-cell snapshot was reviewed cell by cell: 15,876 accepted unchanged, 254 matched earlier high-confidence corrections, and 46 matched follow-up corrections. The separate 12-cell Collection planner phrase has focused Japanese and Arabic RTL browser evidence from the earlier `79b` head.

## Browser and validation status

The headed Chrome review in the isolated Agentic VM was captured against application-code head/tree `f861b9b7b08cd3fe1012d46d082ef6ec71012074` / `eed3d3a0621d35f34f1b263fd9a64734741c7b34`; the current PR head/tree is `d259a92f89657b5c79be3653ed811e2bf8e01c58` / `40d8b8d1dad55642774f5df2e646085f0fecf52b` and adds the listsNav source wiring and review evidence. The new listsNav callers were not covered by that browser review. The browser review covered Identify & Organize in Spanish, Arabic, and Traditional Chinese; the Games loading state in Japanese; and Get Started in Traditional Chinese. The rendered states showed localized organizer pagination and missing-metadata messaging, the localized Japanese library-loading and known configuration messages, and the revised “File” and collection-card translations. The Arabic Identify & Organize screenshot showed the right-to-left layout with the navigation rail on the right. This is focused 1440 × 1000 evidence, not full-app, mobile, or all-locale acceptance. Screenshots and checksums are in [headed runtime review evidence](docs/pr-evidence/pr70-localization-2026-11-02/headed-runtime-review/README.md). The source/callsite cross-review ledger for the 48 browser-finding candidate cells is in the adjacent [translation cross-review packet](docs/pr-evidence/pr70-localization-2026-11-02/headed-runtime-review/cross-review/README.md); it accepted or refined 45 candidates and retained three current values without changing catalogs. Its bundled exact-hash verifier passed against source/catalog head `1adc54cb56dd91731b24e402027476855702f04d` / tree `76792bcafecfb1c9243a1352f638e2f21c0bad0b`, checking 48 rows, placeholders, and three caller/source pins.

The earlier source/catalog patch was reviewed by exact target/source hashes and placeholder checks. The listsNav follow-up manually verified all four exact message-ID calls and passed `git diff --check`; the catalog is unchanged by this source-only fix. The earlier focused catalog structure/parity, exact-hash, placeholder, protected-literal, and numeric-token checks passed on the preceding catalog revision. The full `scripts/check_localizations.py` validator previously reported 359 stale source-location registrations on both the target revision and its unchanged parent; it was not rerun for this milestone.

No tests, builds, scans, or CI jobs were run for this milestone; private-JIT validation remains outstanding. The public login/setup page has since received a headed review in all 12 target locales plus the English fallback; authenticated routes and setup submission were not covered. Whole-app/all-locale and mobile browser review, complete RTL review, and qualified native-speaker review remain outstanding. The PR remains open and draft. No workflow files, merge, release, or tag were changed or created.

Task-scratch evidence on the review host:
- `/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-held-followup-54f1-artifacts-20261101/held-correction-review-54f1.jsonl` (SHA256 `2eb3437d2d0e2aeb70c6a5ea17e2020af3f597c4a9f75ce9442eda1450284c34`)
- `/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-held-followup-54f1-artifacts-20261101/companion-adjudication-54f1.jsonl` (SHA256 `7e578481b50623cf2ee07002023387432000f3c2e7613fd9a836e390c8e4e786`)
- `/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-held-followup-54f1-artifacts-20261101/applied-review-corrections-54f1.json`
- `/mnt/disks/scratch/task-worktrees/localization-20261030/romarrng-held-followup-54f1-artifacts-20261101/focused-catalog-validation-54f1.json`
- `docs/pr70-dynamic-public-message-review-2026-11-01.md` (SHA256 `d0d393cad76c3abce73862cf9ccee41231ba63ae48a56a0134dd2739a4b6c4f2`); changed `romarr/ui.py` SHA256 `028e05f27f1fad6137494c85b1fa8847512a2d11db37c9fa44c4b611a2e797ad`.

## 2026-11-02 exact-head localization follow-up

Applied as two commits from prior PR head `d259a92f89657b5c79be3653ed811e2bf8e01c58`; the PR head after those two commits was `ad091b44c49c82cbd8efb508617743a51dd818dd`.

- Updated all 12 direct-locale values for `ui.import-lists.cdf54991b2` and `ui.seerrng-discovery.f140768191`. Import lists uses the action form in 10 locales; the existing Simplified and Traditional Chinese action labels remain. Hindi SeerrNG discovery invites users to learn about the linked project.
- Added the 12-locale `ui.no-web-api-and-nothing-written-to-a.fefddf8698` message for the static Nintendo import explanation (source SHA-256 `fefddf869833664222ac58789630ae2747f217842f1714d5746f1dcb5157980e`). The UI localizes only this app-owned explanation through `interfaceMarkup`; the separate `Nintendo` label remains escaped, and other reason values remain escaped.
- Updated source manifest and snapshot. The catalog now has 1,836 stable message IDs. All 36 affected direct-locale cells remain `draft`; `es-419` and `fr-CA` inherit their parent values.
- The 36-row cross-review and source context are in [the focused follow-up evidence](docs/pr-evidence/pr70-localization-2026-11-02/nintendo-guidance-follow-up/README.md). The included review ledger SHA-256 is `a509e60ce0c3bdf218a945e99fa6c4191451fcb26254b4a23d7200a9de3ebfb6`. No native-speaker approval is recorded.
- Source/catalog hashes, the full source snapshot, new manifest locations, protected literals, and the renderer call were checked; `git diff --check` passed. No tests, builds, or CI were run for these commits.

The browser screenshots already in this PR predate this follow-up and are not claimed as evidence for this head. At the time of that follow-up, final-head browser review and qualified native-speaker review remained pending. The PR stays draft; no merge, release, or tag was made.


### Current-head headed-browser review attempt — 2026-11-02

An isolated, independent Chrome desktop was acquired through Agent Desktop Pool v2 on kspld0 for this exact head. After Chrome started, a normal navigation attempt to `http://192.168.50.148:15059/#lists` remained pending and did not display the app. The pool documents that browser workspaces block private/LAN egress; no tunnel or alternate browser path was used. At that point, no rendering review was claimed; the successful exact-head Agentic VM review is recorded below.

## Exact-head Agentic VM browser review — 2026-11-02

At PR input head `ad091b44c49c82cbd8efb508617743a51dd818dd` / tree `d7cb63f7f8e4d4fc5c791e89406ce96007c26f40`, a headed Chrome review on the dedicated Agentic VM covered the Arabic Library and General settings routes, plus German and Spanish General settings at 1920×1024. Arabic text and controls stayed right-aligned with the sidebar on the right. German and Spanish returned to left-to-right layout with the sidebar on the left. No visible overlap or clipping appeared in these captures.

Screenshots and SHA-256 manifest: [Agentic VM browser review](docs/pr-evidence/pr70-localization-2026-11-02/agent-vm-browser-review/README.md). Evidence commit: `65a3f8a8feee1b041c8c547250feeae6900337f5`.

At that time, this was a focused desktop review. Populated library rows, narrow/mobile layouts, the other nine locales on those routes, and native-speaker approval were not covered. No settings were saved; no tests, builds, scans, CI, workflows, releases, or tags were changed. The local Semgrep hook was bypassed because scans must run on private ephemeral JIT.


## Current-head integration-guide follow-up

Reviewed 36 cells across three new message IDs at input head `65a3f8a8feee1b041c8c547250feeae6900337f5`. Independent cross-review accepted 35 unchanged values and refined one Indonesian description. The final sentence distinguishes searching/verifying game releases from organizing games. Updated the direct Indonesian target and its `translationHashes` fingerprint; the translation remains draft and no native-speaker review is recorded.

Evidence: [root and independent cross-review, exact apply plan, and readback](https://github.com/snapetech-org/ROMarrNG/blob/c3bcb5fffb28419f82384ad2202686e97227c4f9/docs/pr-evidence/pr70-localization-2026-11-02/current-head-follow-up-20261102/README.md). Commit: `c3bcb5fffb28419f82384ad2202686e97227c4f9`. The current catalog contains 1,836 messages; 144 caller-line records were re-attested, including eight historical location pins verified at their current lines.

At that point, qualified native-speaker approval and current-head browser review remained outstanding; the later public setup review is recorded below. No tests, builds, scans, CI checks, workflow edits, releases, tags, or merges were made. The PR remains open and draft.

## Arabic platform-count plural and number-format follow-up — 2026-11-02

- Corrected the Arabic Library summary for `{cached} cached across {platformCount} platforms` with Arabic zero/one/two/few/many/other forms.
- Updated the plural runtime to parse localized digits and grouping separators with the same regional number locale that formats the caller’s counts, including browser/system locale when no regional preference is set. Plural category selection still follows the UI locale.
- An independent exact-diff review found no material defect. All forms retain `{cached}` and the numeric forms retain `{platformCount}`; the source hash, changed-file hashes, review packet, and exact readback are in [the Arabic plural evidence](docs/pr-evidence/pr70-localization-2026-11-02/arabic-platform-counts/README.md). Commit: `e808f6243a33c597c718e792cbec36a624c6aca3`.
- The push response reported the existing stable-image alias policy as consistent. No GitHub Actions run or PR checks were created; no tests, builds, scans, or CI jobs ran.
- At that point, qualified native-speaker review and current-head browser review remained outstanding; the later public setup review is recorded below. No workflow files changed, and no merge, release, or tag was made. PR #70 remains open and draft.

## Arabic Library headed browser review — current source snapshot

A headed Agentic VM review at 1440×1000 captured the Arabic Library view from PR source commit `e808f6243a33c597c718e792cbec36a624c6aca3`, tree `28f376b9452d907d02ec1d74a17d482f93ba1962`. It found the RTL sidebar and card flow, readable Arabic count summary (36 cached across 3 platforms), intact platform filters, and no visible clipping in that viewport. Screenshot and checksum-backed notes: [browser-review-library-rtl](docs/pr-evidence/pr70-localization-2026-11-02/browser-review-library-rtl/README.md).

The PR head at the time of that review was `9b56b5fde40daf59aa61a7ce2d14e6bf7b37bf9d`, tree `117fb2a8cc208c958ac62d00927cc65defe6530d`. The later File-context split changes application source and catalogs and was not included in that browser session. The current head and latest milestone are recorded below. Mobile behavior, other routes/locales, and qualified native-speaker approval remain open. No tests, builds, scans, or CI jobs ran.


## File heading and Add to library context split — 2026-11-02

At application-code head `8e3820252b0c362e18e421b3a73e7ff1478d32a0` / tree `0d29024efd7e5e886926a83d95f57c472f327db9`, the catalog now distinguishes the `File` filename-table heading from the `Add to library` pipeline action. The 12 existing `File` targets were changed to file nouns, the action received stable message ID `ui.add-to-library.2bf9ea0e46` with 12 reviewed translations, and `romarr/ui-source-snapshot.json` was updated.

Primary review and independent cross-review accepted all 24 target decisions; the Arabic action uses the cross-reviewed unvocalized imperative. The affected cells remain `draft`; no native-speaker approval was recorded. Exact hashes, source/caller pins, and readbacks are in [File context split evidence](https://github.com/snapetech-org/ROMarrNG/blob/8e3820252b0c362e18e421b3a73e7ff1478d32a0/docs/pr-evidence/pr70-localization-2026-11-02/file-context-split/README.md). The catalog now contains 1,837 messages.

No tests, builds, scans, or CI were run for this change. The current-head public setup browser review was completed afterward and is recorded below. Workflow files are unchanged. PR #70 remains open and draft; no merge, release, or tag was made.


## Exact-head public setup browser review — 2026-11-02

The browser review used application-code head `8e3820252b0c362e18e421b3a73e7ff1478d32a0` / tree `0d29024efd7e5e886926a83d95f57c472f327db9`. A documentation-only evidence commit advanced the PR to `6db0b917343fc9fb605f8a4ecfbf9b4c21cebd1b` / tree `bfb778ba77849174a4670a70883c812183506b43`; no application code or catalogs changed after the browser input.

Headed Chrome on the dedicated Agentic VM displayed the public `/login` setup page in all 12 target locales plus the English fallback at 1920×1024. Translated labels, inputs, button, and setup notice showed no visible clipping or overlap. Arabic rendered right-to-left; the other inspected locales rendered left-to-right. The language selector was restored to Arabic.

Both password fields remained blank. The form was not submitted, and no account or settings were created. This is a public setup-page visual review only; authenticated routes, setup submission, full-app/all-locale coverage, mobile behavior, and qualified native-speaker approval remain outstanding. Screenshots and checksums: [exact-head public setup browser evidence](docs/pr-evidence/pr70-localization-2026-11-02/exact-head-public-setup-browser-review/README.md).

No tests, builds, scans, or CI jobs were run for this evidence commit. Workflow files remain unchanged. PR #70 remains open and draft; no merge, release, or tag was made.
## Latest localization delivery — W206–W225

Pushed as 1ab8fd8b171afbfe43cd6998cde920f9f9b12b0c; PR #70 remains open and draft. Primary, blind, and third-party cross-audit review covered 240 cells and 26 pinned caller references. Final dispositions: 194 accept-current, 22 corrections, 12 refinements, and 12 holds. Applied 34 changes in romarr/ui-labels.json and read back all 240 cells. The 1,837-message key set and order remain unchanged; translation status remains draft.

All 12 rank-218 values remain held because the pinned callers pass English “browse” or “answer for a date range” values through {what} without showing whether those values are localized before interpolation. Placeholders, markup, and protected literals passed the recorded review. Evidence: [W206–W225 review packet](https://github.com/snapetech-org/ROMarrNG/tree/1ab8fd8b171afbfe43cd6998cde920f9f9b12b0c/docs/pr-evidence/pr70-localization-2026-11-03/window-206-225/README.md).

Qualified native-speaker approval and exact-head headed-browser acceptance remain outstanding; the isolated browser coordinator is unavailable. No tests, builds, scans, CI dispatches, workflow edits, merges, releases, or tags were made for W206–W225.

### Current-rank localization review: W245–W264

Applied 30 cross-audited translation changes at `535930f31df13b9757ebdad397ba5ae72464573d`; evidence was added at `c135c4729582817273c946891186ab4ea87467b5`. The window covers 240 cells across 20 source IDs and 12 locales: 138 accept-current, 14 corrections, 16 refinements, and 72 caller-path holds.

The 72 caller-path holds are positions 248, 249, and 256–259 across all locales. Two blind translation findings at position 259 (pt-BR and zh-Hant) are recorded separately but remain unapplied until a direct caller resolves the intended state.

Evidence: [complete window packet](https://github.com/snapetech-org/ROMarrNG/tree/c135c4729582817273c946891186ab4ea87467b5/docs/pr-evidence/pr70-localization-2026-11-03/window-245-264-current-ranks/); [cross-audit report](https://github.com/snapetech-org/ROMarrNG/blob/c135c4729582817273c946891186ab4ea87467b5/docs/pr-evidence/pr70-localization-2026-11-03/window-245-264-current-ranks/third-party-cross-audit/report.md). Readback matched all 240 cells, verified exactly 30 target/hash updates, and found zero non-target changes; message IDs, key order, metadata, and caller-path holds are preserved.

Qualified locale approval and exact-head browser review remain outstanding. No tests, builds, scans, or CI runs were performed; no workflow, merge, release, or tag changes were made.

<!-- romarr-pr70-w245-264-cross-audit-ledger-sha256: 088bd6112339a87f0fc5eb56b68d6f4ae9aa06c9aedfcee4849406e293fe0f57 -->

## W305–W324 localization update

- Applied 105 authorized translations across 20 source messages and 12 locales; 135 current values were retained; zero holds.
- Exact readback: 240/240 cells, zero non-target changes, and unchanged ordered catalog structures and keys.
- Evidence: [W305–W324 application evidence](https://github.com/snapetech-org/ROMarrNG/blob/018937dc98d451ddd04d2d0942bca2777ef64dd3/docs/pr-evidence/pr70-localization-2026-11-03/w305-324-application/README.md).
- Commit: `018937dc98d451ddd04d2d0942bca2777ef64dd3`; tree: `c13dc4fc091565318d11a19ad9e851215a5f917e`.
- Browser and native-speaker review remain pending; this PR remains draft.

<!-- localization-window-w385-404 -->
## Localization review: W385–W404

Applied at exact PR head `c146189f29db8fbd77d68dff0c33a0ab59a6b601` after candidate-free input validation, primary review, independent blind review, and exact-hash cross-audit of 240 cells across 20 sources and 12 locales. Reconciliation resolved 27 primary/blind disagreements into 211 accept-current cells, 25 corrections, and 4 refinements. Applied 29 exact-hash updates to `romarr/ui-labels.json`; no new holds were added, and all 288 carried holds remain unchanged.

The source-dispatch fix in the base head made 48 cells at ranks 392, 396, 398, and 399 newly source-bound. Both review streams reviewed all 48; five updates were selected at 392 (Korean and both Chinese scripts) and 399 (Hindi and Indonesian). Evidence and the portable verifier are in [`window-385-404`](docs/pr-evidence/pr70-localization-2026-11-03/window-385-404/).

Exact-head browser review and qualified native-speaker review remain pending. No tests, builds, CI, workflow changes, merge, release, or tag were made.

## W425–W444 localization review

Applied 46 selected exact-hash edits to `romarr/ui-labels.json` (17 corrections and 29 refinements) at commit `d5ba7f1f268501f45227388c46d5f938ed0c9191` with tree `2f8ce1af963b315108f668fc31c94ca90ecd1351`. All 240 cells were reconciled; current targets were retained for the remaining cells, including the 12 “Fern accent” labels after verifying their dynamic theme-swatch title and accessible-label caller. The 336 inherited hold cells and 40 prior selected sources remain unchanged. In the Chinese top-100 example, `百` represents the source magnitude 100.

<!-- ROMARRNG-PR70-W425-W444-APPLIED: d5ba7f1f268501f45227388c46d5f938ed0c9191 -->
