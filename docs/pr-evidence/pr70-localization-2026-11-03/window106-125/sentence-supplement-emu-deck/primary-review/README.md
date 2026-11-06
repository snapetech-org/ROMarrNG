# Primary EmuDeck sentence review

This directory contains the sealed primary review of the complete EmuDeck help sentence, assembled across its three localized text nodes and two inline path literals. Decisions and proposed targets are cell-level.

## Files

- `primary-decisions.jsonl`: one JSON object per locale/source-ID cell, including the disposition, confidence, rationale, exact proposed target where changed, and the input source/current hashes.
- `review-summary.json`: exact manifest pins, source sentence, inline literals, assembled current translations, counts, and validation status.
- `SHA256SUMS.txt`: checksums for the other three output files.

The input packet checksums and every raw source/current-target hash were verified. The review used only the supplied packet; no repository files were edited, and no tests, builds, or CI runs were performed.
