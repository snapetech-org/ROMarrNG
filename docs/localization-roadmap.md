# UI localization

## What is available

ROMarr's Python service renders the dashboard and public sign-in, invitation,
and connection pages. The localization catalog contains 1,348 app-owned
messages under stable IDs. English is the source language. Twelve other locales
have direct translations; Latin American Spanish inherits from Spanish, and
Canadian French inherits from French. Missing translations fall back to
English on a message-by-message basis.

| Locale state | Count | Behavior |
| --- | ---: | --- |
| English source | 1 | Always selectable |
| Direct translations | 12 | Selectable; full catalog coverage |
| Regional fallbacks | 2 | Selectable; inherit from `es` or `fr` |
| Draft translations | 0 currently | Hidden; must be complete and reviewed before selection |
| Planned translations | 22 | Registered for formatting and future work; not selectable |

The 37 registered locales are Arabic, Azerbaijani, Bulgarian, Bengali, Czech,
Danish, German, Spanish, Latin American Spanish, Persian, French, Canadian
French, Hebrew, Hindi, Hungarian, Indonesian, Italian, Japanese, Kazakh, Korean,
Malay, Norwegian Bokmål, Dutch, Polish, Portuguese, Brazilian Portuguese,
European Portuguese, Russian, Swedish, Thai, Turkish, Ukrainian, Uzbek,
Vietnamese, Simplified Chinese, and Traditional Chinese. Of these, Arabic,
German, Spanish, French, Hindi, Indonesian, Japanese, Korean, Brazilian
Portuguese, Vietnamese, Simplified Chinese, and Traditional Chinese have direct
translations. The remaining registered locales stay out of the picker until
their translations exist and pass the catalog checks.

The existing translation text was carried over, with targeted corrections for
verified semantic errors in the Arabic folder label and status tooltip, and
Hindi gaming terminology and script contamination. Each message records review
status separately for every direct locale; existing text is `unverified`
because its provenance is unknown. Regional entries are marked `inherited`. A
message can be marked `reviewed` only with a reviewer and review date. A
complete native review and RTL visual review have not been done. This catalog
pass does not certify translation quality or establish RTL signoff. Unverified
is the default and is stored sparsely; regional inheritance comes from the
locale parent table. Fingerprints are stored only for draft or reviewed
overrides, keeping the runtime catalog compact.

## Runtime behavior

`romarr/i18n_runtime.js` is a dependency-free shared runtime for the dashboard
and public pages. It provides:

- Stable message IDs, source-text compatibility lookup, and source snapshots.
- Browser/system language detection, canonical BCP 47 matching, Chinese script
  aliases, Latin American Spanish matching, and regional parent fallback.
- Per-message English fallback, escaped interpolation through text/attribute
  sinks, and Unicode bidi isolation around dynamic values after removing
  embedded directional controls.
- CLDR plural-category selection and locale-aware number rendering for plural
  messages.
- Right-to-left document direction, translated element metadata, and mirrored
  mobile navigation behavior for RTL languages.
- Separate browser-local interface and regional-format preferences, including
  cross-tab synchronization. Regional changes refresh the active view without
  changing the interface language.

User-entered values and external data are not translated: game names, platform
names, paths, usernames, API identifiers, commands, and provider responses keep
their original content. The interface language does not set the metadata
provider language.

## Adding or changing translations

1. Edit `romarr/ui-labels.json`; keep an existing stable ID when changing its
   English source or translation. Add a new key for a genuinely new message.
2. Add new UI copy to the catalog before wiring it into `romarr/ui.py`. Prefer
   `data-i18n-key` and stable IDs in rendering helpers. The runtime still accepts
   source text for dynamic messages during migration.
3. Add translation text for the target locale and keep placeholders intact.
   Mark machine-generated or not-yet-reviewed text as `draft`. Leave the status
   absent (or remove its override) when the origin is unknown; that means
   `unverified`.
   For count-sensitive messages, use the plural object shape (`kind`, `argument`,
   and locale forms) instead of concatenating singular and plural strings.
4. After a native speaker checks the translation in context, set its status to
   `reviewed` and add `translationReview[locale]` with `reviewer` and an ISO
   `reviewedAt` date. Review is tracked per message and locale. The migration
   script preserves evidence when text is unchanged and resets changed copy to
   `unverified`. Stored source and translation fingerprints make this check
   repeatable; changing the English source also clears review status because
   it may change the meaning translators reviewed.
5. Change a locale from `planned` only when its catalog coverage is complete.
   Regional fallback locales must name a selectable parent.
6. Run `python scripts/check_localizations.py` before publishing. It checks
   stable source hashes, source snapshots, locale status, direct coverage,
   inherited coverage, per-message review metadata, placeholders, plural forms,
   and stable IDs referenced by the UI.

### Review bundles

Use `scripts/localization_review.py` to prepare translations for human review
without editing the application catalog by hand. The bundle is plain JSON; the
importer treats it as data and does not execute its contents.

```sh
python scripts/localization_review.py export \
  --locale it --output /tmp/romarr-it-review.json
```

Edit only each row's `translation`. Keep its ID, English source, source hash,
translation hash, and status unchanged. For an existing locale, export includes
strings that have not been marked reviewed; use `--include-reviewed` when
rechecking already-reviewed copy. For a planned locale, the export contains an
empty translation for every message. Fill these in while preserving every
placeholder and, for plural messages, every required form.

Validate the completed file first. Without `--apply`, import checks schema
version, stable message IDs, unchanged source and translation fingerprints,
placeholders, plural forms, reviewer details, and review date without writing
to the catalog:

```sh
python scripts/localization_review.py import \
  --bundle /tmp/romarr-it-review.json \
  --reviewer "Reviewer name" --reviewed-at YYYY-MM-DD
```

After a successful validation, repeat the command with `--apply` to atomically
update `romarr/ui-labels.json`. If the source or an existing translation
changed after export, the import is rejected; export a fresh bundle and carry
over the translation manually. Imports are all-or-nothing, so a malformed row
cannot leave a half-updated catalog.

A planned locale remains hidden while translations are incomplete. Partial
imports mark it as a hidden `draft`; the picker exposes it only when every
message has a translation and every message was explicitly marked `reviewed`.
The reviewer and date fields are an audit record, not credential verification:
only mark a translation reviewed after a human has checked it in context and
confirmed its language quality. These tools do not generate or certify
translations.

Translation guidance and names that should stay unchanged are in the
[localization glossary](localization-glossary.md).

`python scripts/migrate_ui_catalog.py` imports the current source-keyed catalog
into the stable-ID schema. It preserves IDs and unchanged review evidence,
resets metadata for changed or newly added translations to unverified, and
writes source fingerprints, sparse review fingerprints, and the source
snapshot. Run the checker afterward; the migration script does not translate
new text.

## Remaining work

- Review each existing translation with native speakers and record reviewer
  and date by locale and message.
- Translate and review the 22 planned locales before adding them to the picker.
- Expand real plural messages and validate all CLDR categories with reviewers;
  runtime support exists, but most current messages do not need plural forms.
- Perform a browser visual review of Arabic across navigation, modals, forms,
  tables, manual import, and public pages. Arabic direction is active, but that
  review has not established full RTL signoff.
- Consider a separate metadata-language preference only after each provider's
  supported language behavior is confirmed; it is not currently implemented.
