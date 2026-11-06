# ROMarrNG source-bound localization fixes

This review is pinned to PR #70 head 6eb40719ea270bb3cae024d771665e7006a85822 and tree 55031e7e234a7035de7682d0b49f2f60882164f6. It wires two existing, translated catalog entries into their exact production callers without changing English source IDs or catalog values.

The local launcher scan caller translates only the exact response shape scan failed: <PythonExceptionClass> from /api/v1/launchers/connect, using the existing ui.scan-failed-error-type.e99ccb8157 template. Other response text, including the network-failure fallback and unrelated API/provider messages, stays opaque through the existing API-message renderer.

The TOTP enrollment caller translates the note only when the returned string exactly matches the local English catalog source for ui.scan-the-uri-or-enter-the-secret-in.612ce1fd46. Any unrecognized d.note continues through the opaque API-message renderer.

The baseline pins the app source, callers, catalog, source snapshot, all 12 translations and translation hashes. No catalog edits are expected. Exact PR refs and the post-push verifier are recorded separately. No tests, builds, scans, CI dispatches, workflow changes, merge, release or tag occurred.

Both catalog entries remain marked draft in translationStatus; this source wiring does not claim qualified native-speaker approval.
