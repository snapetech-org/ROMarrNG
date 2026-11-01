# ROMarrNG PR #70: public dynamic-message locale switching

## Review evidence

An independent static review was pinned to PR head `81b5ec7b104b4274da2c476b74c2f11e76658e55`, tree `c185f8e264fe4889061a7ac779c557585e8eb25d`.

The review found that the login/setup failure handler wrote translated text into the alert and submit button without retaining the source message or template values. The public language picker therefore could not re-render an already visible error after a locale change. The invalid-invitation page had the same issue because it translated the error before inserting it into the DOM.

## Change

- `messageInfo` now preserves the original source and interpolation values alongside the rendered text.
- The login alert records its source template and values so the existing public i18n runtime can rerender it. Raw, unmapped server details clear those markers and retain their existing opaque-text handling.
- The submit button keeps a localization key for its action and the pending `Working…` state.
- The invalid-invitation page inserts source English with `data-i18n` markers instead of inserting already translated text, then applies the current locale immediately. The invitation form does the same for its marked dynamic copy.

The count and HTTP status values remain interpolation values; the source template is retained so the runtime can apply its existing placeholder isolation and direction handling.

## Validation and remaining review

The source diff was inspected and `git diff --check` passed. No tests, builds, CI, or browser review were run. Exact-head headed-browser review and qualified native-speaker review remain separate acceptance items.
