# W385-W404 source-bound dispatch wiring

This evidence is based on PR #70 head 8a15dd1c3487d17e62d78a1b80222b7eb6033c6b, tree 452cda96454624cfa7068b9925d15e821d4828f7. The sealed source-only review is preserved under source-only-review/; its code-review.md SHA-256 is a0fc6cc5ef43f3c6d08e62923d75caef84bd6d196767e1dd2d28a20933d76841.

## Fixed local messages

- Position 392, ui.source-file-is-missing-or-is-a-symli.ca704e4514: “Source file is missing or is a symlink”. Added to the existing organizer fixed-message allowlist.
- Position 396, ui.submitted-the-host-does-not-report-w.9ba72a4bcd: “Submitted. The host does not report whether the PIN was correct -- check that your client now appears in the paired list.” Attached only to the local accepted-submission return.
- Position 398, ui.sunshine-has-no-endpoint-that-lists.06228315a7: “Sunshine has no endpoint that lists waiting clients -- its API can accept a PIN and cannot tell you one is wanted. Start the pairing from your Moonlight client, then type the PIN it shows.” Attached only to the fixed non-Wolf status branch.
- Position 399, ui.sunshine-refused-it-no-moonlight-cli.fb8441c69d: “Sunshine refused it: no Moonlight client is waiting to pair. Start the pairing on your client first.” Attached only when Sunshine returns the fixed false-status result.

The Moonlight renderer accepts only those exact keys and only when UI_MESSAGES[key].source exactly equals the returned detail. Any missing/unknown key or source mismatch uses the opaque API renderer. IDs are attached by ROMarr's fixed source branches, never copied from request, host, or provider data. The existing organizer renderer retains its exact source-to-key lookup and opaque fallback; only position 392's ID was added to its allowlist.

No catalog values were edited. This evidence establishes the source-routing guard, not rendered-language quality. No tests, builds, CI, browser review, release, or tag were run.
