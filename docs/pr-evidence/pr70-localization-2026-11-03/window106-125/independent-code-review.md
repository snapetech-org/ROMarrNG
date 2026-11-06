# Independent code review: organizer API localization

Reviewer inspected the ROMarr `romarr/ui.py` diff in the W106–W125 application worktree after the mapping change and before commit. Review scope was `organizerApiMessageMarkup`, the organizer `messageApi` wrapper, and the rename-preview operation and blocked-reason cells.

Result: no material safety finding (moderate confidence). `stableLocalizationKey` performs an exact source/key lookup, then the helper requires the result to match one of two explicit catalog IDs before translating. Unmatched and dynamic strings continue through `apiMessageMarkup`, which escapes the original text and renders it with `lang="und"` and `dir="auto"`. The helper's optional explicit-template route remains separately key, placeholder, and source-kind allowlisted. Paths, identifiers, provider text, peer values, and unmatched reasons keep their opaque rendering.

The reviewer noted one edge: an API value exactly equal to either allowlisted source string will also localize. This requires an exact full-string collision; it does not match prefixes, substrings, or interpolated dynamic values.

The review was read-only. No tests were run.

A separate contextual copy finding corrected the German “Game media” instruction from informal `setze` to formal `setzen Sie`, matching the surrounding `Sie` imperatives. The initial helper review also found that coercing arbitrary values with `String()` could throw on a hostile object; the helper was changed to pass non-string values directly to the existing type-guarded `apiMessageMarkup` before source lookup. A second independent read-only review then confirmed the non-string type guard and unchanged three-call-site behavior. It found that source or catalog-ID matches remain exact and escaped, and that non-string, unmatched, path, provider, and peer values retain the prior opaque fallback. The only key-collision edge is an arbitrary dynamic string exactly equal to one of the two allowlisted source strings or IDs; it renders fixed escaped copy without interpolation.
