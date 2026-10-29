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

The existing translation text was carried over without changing its wording.
Its provenance and native-speaker review status are not recorded, so the
catalog marks it `unverified`. A complete native review and RTL visual review
have not been done. ROMarr therefore does not claim translation quality parity
with PlezyNG, even though the catalog and runtime now support a broader locale
workflow.

## Runtime behavior

`romarr/i18n_runtime.js` is a dependency-free shared runtime for the dashboard
and public pages. It provides:

- Stable message IDs, source-text compatibility lookup, and source snapshots.
- Browser/system language detection, canonical BCP 47 matching, Chinese script
  aliases, Latin American Spanish matching, and regional parent fallback.
- Per-message English fallback, escaped interpolation through text/attribute
  sinks, and Unicode bidi isolation around dynamic values.
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
3. Add translation text only for locales with a qualified reviewer. Keep
   placeholders intact. For count-sensitive messages, use the plural object
   shape (`kind`, `argument`, and locale forms) instead of concatenating
   singular and plural strings.
4. Change a locale from `planned` only when its catalog coverage is complete.
   Regional fallback locales must name a selectable parent.
5. Run `python scripts/check_localizations.py` before publishing. It checks
   stable source hashes, source snapshots, locale status, direct coverage,
   inherited coverage, placeholders, plural forms, and stable IDs referenced
   by the UI.

`python scripts/migrate_ui_catalog.py` imports the current source-keyed catalog
into the stable-ID schema. It preserves IDs already present and writes the
source snapshot. Run the checker afterward; the migration script does not
translate new text.

## Remaining work

- Review each existing translation with native speakers and record review
  provenance by locale and message.
- Translate and review the 22 planned locales before adding them to the picker.
- Expand real plural messages and validate all CLDR categories with reviewers;
  runtime support exists, but most current messages do not need plural forms.
- Perform a browser visual review of Arabic across navigation, modals, forms,
  tables, manual import, and public pages. Arabic direction is active, but that
  review has not established full RTL signoff.
- Consider a separate metadata-language preference only after each provider's
  supported language behavior is confirmed; it is not currently implemented.
