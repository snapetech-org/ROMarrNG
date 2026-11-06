# ROMarrNG PR #70 exact-head public setup browser review

Reviewed ROMarrNG commit `8e3820252b0c362e18e421b3a73e7ff1478d32a0` (tree `0d29024efd7e5e886926a83d95f57c472f327db9`) in headed Chrome on the dedicated Agentic VM at 1920×1024.

The `/login` route displayed the unclaimed public password setup page. I switched through all 12 target locales and the English fallback. The translated labels, form controls, submit button, and setup notice fit the viewport without visible clipping or overlap. Arabic displayed right-aligned RTL content; the other inspected locales displayed readable left-to-right layouts. The selector was returned to Arabic, its prior setting.

The password fields remained blank. I did not submit the form, create an account, or save settings. This is a visual review of the public setup page only; it does not cover authenticated routes or establish native-speaker approval.

## Captures

Each screenshot is cropped to the app viewport to omit browser chrome.

| Locale | Screenshot |
| --- | --- |
| English fallback | `screenshots/setup-en.png` |
| Arabic | `screenshots/setup-ar.png` |
| German | `screenshots/setup-de.png` |
| Spanish | `screenshots/setup-es.png` |
| Hindi | `screenshots/setup-hi.png` |
| Indonesian | `screenshots/setup-id.png` |
| French | `screenshots/setup-fr.png` |
| Japanese | `screenshots/setup-ja.png` |
| Korean | `screenshots/setup-ko.png` |
| Brazilian Portuguese | `screenshots/setup-pt-BR.png` |
| Vietnamese | `screenshots/setup-vi.png` |
| Simplified Chinese | `screenshots/setup-zh-Hans.png` |
| Traditional Chinese | `screenshots/setup-zh-Hant.png` |

`manifest.json` records the review scope and exact head. `SHA256SUMS` covers the README, manifest, and screenshots.
