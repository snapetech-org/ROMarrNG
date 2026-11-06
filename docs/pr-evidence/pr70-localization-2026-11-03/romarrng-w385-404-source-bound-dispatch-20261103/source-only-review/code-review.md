# ROMarrNG W385–W404 dispatch code review

**Verdict:** At PR #70 head `8a15dd1c3487d17e62d78a1b80222b7eb6033c6b` (tree `452cda96454624cfa7068b9925d15e821d4828f7`), exact source-ID allowlists can route all four fixed, app-owned messages through `interfaceMarkup`. Keep the Moonlight routing branch-specific; a global text matcher would blur local copy with host/API errors.

## Findings

- `romarr/ui.py:817,882–883` resolves a stable source ID and escapes the translated label. `apiMessageMarkup` at `1042–1049` instead escapes unmatched strings in `lang="und"`, so unknown API/provider text remains opaque.
- **392 — `ui.source-file-is-missing-or-is-a-symli.ca704e4514`:** `organizer.py:1848–1849` emits this fixed blocked-plan reason. The rename preview calls `organizerApiMessageMarkup` (`ui.py:5905–5906`); its exact `ORGANIZER_API_MESSAGE_KEYS` allowlist (`5724–5732`) already translates listed local reasons and sends all other values to `apiMessageMarkup`. Minimal change: add this ID to that existing set.
- **396 — `ui.submitted-the-host-does-not-report-w.9ba72a4bcd`:** `MoonlightHost.submit_pin` returns this fixed message on its final accepted-submission branch (`playability.py:1811–1814`). The UI currently passes `r.detail` to `apiMessageMarkup` (`ui.py:4891`).
- **398 — `ui.sunshine-has-no-endpoint-that-lists.06228315a7`:** `MoonlightHost.pairing` returns this fixed capability explanation when `kind != WOLF` (`playability.py:1735–1743`). The same `detail` field carries `str(exc)` on the Wolf API failure path (`1745–1747`), then reaches `apiMessageMarkup` in the status card (`ui.py:4851`). Steam Headless also takes the non-Wolf path, but the source code defines it as running Sunshine’s protocol (`playability.py:1313–1317`); that is not a routing ambiguity.
- **399 — `ui.sunshine-refused-it-no-moonlight-cli.fb8441c69d`:** the fixed message is returned only when Sunshine’s PIN endpoint reports `false` (`playability.py:1802–1807`). The same response field also carries local validation/configuration strings and raw exception text (`1791–1810`), so matching `detail` text globally is unsafe.

## Minimal patch scope (not applied)

1. Add position 392’s ID to `ORGANIZER_API_MESSAGE_KEYS`.
2. Add an optional app-owned detail source ID to the Moonlight status/pin response, set only in the fixed branches for positions 396, 398 and 399. Do not copy an ID from a host/provider response; leave exception and other dynamic details without one.
3. Add a narrow Moonlight ID allowlist/helper in `ui.py`. Require an allowlisted key, a matching `UI_MESSAGES[key]`, and exact equality between its source and the returned detail before calling `interfaceMarkup(key)`. Fall back to `apiMessageMarkup(value)` on any mismatch. Use it only for pairing detail and PIN result rendering.

The only unsafe ambiguity is provenance in the shared `detail` fields. Branch-attached IDs remove it; a generic source-text/template matcher would not. This review did not verify catalog membership or translations. The helper should fall back to opaque rendering if an ID/source pair is absent.

## Evidence and limits

The PR head/tree were checked live. The existing task worktree is at an older commit (`6bef0c74632067906fd07279fa6bd3fd59159a48`); findings use `git show` from the pinned PR commit. The assessment used only app source, rendering code, and caller-context excerpts for these four positions. A broad unscoped search briefly returned docs outside scope; that output was discarded and did not inform these findings. No catalogs, target cells, primary/blind reviews, or translation suggestions were used in the assessment. No repository files were changed; no tests, builds, browser work, or PR actions were performed.
