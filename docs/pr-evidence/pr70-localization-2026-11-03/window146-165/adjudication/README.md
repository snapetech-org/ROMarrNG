# ROMarrNG W146–W165 ratification notes

This 240-cell adjudication is pinned to PR #70 head db895a97e9871952a0b952e1d119e32e06cf168d and tree f1edf8319eb3dbd29ac5fe1e279216c5b96ecc6a. It combines the frozen current/source/caller input, candidate-free adjudication, and the primary, independent, and root ledgers. Every final target carries source/current/final hashes and an exact caller reference or hold pin. Source hashes use SHA-256 of UTF-8 text; current and final target hashes use the catalog's canonical JSON string encoding (UTF-8, sorted keys, compact separators).

The lowercase integration-guide key at ordinal 160 has no current production-code caller. All 12 locale cells remain hold-context. Each row carries a hold pin to the exact-head source-context record and the separate case-distinct title caller, including its file hash and line.

Context-sensitive ratifications include interval wording for Import check (minutes) based on the auto_import_interval_minutes caller; busy-state language for In a game; the user's game collection meaning for In library; a software-hub rather than physical-center meaning for invalid hub result; and Imported {total} count labels that avoid generic item nouns unsupported by the source.

The candidate-free ledger was sealed before candidate text was read. Aggregate summaries and changed-cell source/hash metadata were visible before sealing, so this packet does not claim strict blinding. Machine review is not native-speaker approval. No repository or PR files were edited during this review phase; the subsequent approved catalog application is documented separately. No tests, builds, scans, CI, browser work, or workflows were run for adjudication.
