# ROMarrNG PR #70 File noun/action context split

At baseline head `9b56b5fde40daf59aa61a7ce2d14e6bf7b37bf9d`, the same catalog message `File` was used for a filename column and the “Acquire → Verify → File → Scan → Play” workflow step. The filename translations were action verbs in several locales.

This milestone changes only those 12 `File` cells to file nouns, adds the reviewed 12-locale `Add to library` message (`ui.add-to-library.2bf9ea0e46`), localizes the pipeline step, and adds its source hash to `ui-source-snapshot.json`. All affected cells remain draft with no recorded native review.

Evidence:

- `primary/`: exact-head primary review, input packet, source/caller pins, and checksums.
- `cross-review/`: independent per-locale cross-review, exact-head pins, and checksums.
- `application/`: exact-hash apply plan, 24-cell readback, unchanged-entry/source-snapshot verification, resulting file hashes, and application checksums.

No tests, builds, scans, CI, browser review, workflow edits, merge, release, or tag were performed for this milestone. Native-speaker review remains outstanding.

The catalog migrator was inspected during application. At this head it also inserts 141 unrelated pending source-manifest rows; those generated outputs were restored. The committed change preserves the original 1,836 catalog entries, changes the reviewed `File` row, and adds only the new `Add to library` row. Static JSON, source hash, caller, and 24-cell readback checks pass. Project test/build/CI workflows were not run.
