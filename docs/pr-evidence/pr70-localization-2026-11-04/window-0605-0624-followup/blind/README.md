# Independent blind review packet — ROMarrNG PR #70 W605–W624

This packet records a separate semantic and grammar review of the candidate-free input bundle. It is pinned to head `872905926887840025ba4c3f17151b96f8d3e6e2` and tree `d7d762d5f3a5dc31bcbdb6c6c45779101ab0bbd4`.

`review.jsonl` has one record per locale cell (240 total). For callerful cells it contains the exact source, current target, caller references, and complete source/caller excerpts with their hashes. The three callerless positions (618, 620, 623) are hash-only across all locales: those rows contain no source or target text and omit the source ID. Prior selection, hold, applied, and window readback lineage files are copied byte-identically under `lineage/`.

Clear proposals:

- Position 611, Indonesian: `Log hidup` → `Log langsung`. The caller says this is a process log tailed live; the current phrase reads literally as a “living log.” Confidence: moderate.
- Position 611, Vietnamese: `Bản ghi trực tiếp` → `Nhật ký trực tiếp`. The caller identifies a live-tailed process log; the current phrase says “live record” without clearly naming a log. Confidence: moderate.

All other callerful cells are retained as clear matches in their exact interface context. No native-speaker approval is claimed. These proposals are review suggestions only; no repository or PR files were changed.

## Verify

Run the self-check and compare every row with the candidate-free input bundle:

```sh
python3 verify_packet.py --input /path/to/candidate-free/input
```

The verifier checks packet hashes, the 240-cell window, all source/target/context hashes, exact source/caller evidence for callerful cells, absence of source/target text in callerless cells, byte-identical prior lineage copies, and the pinned bundle metadata. The standalone packet checks remain useful without the input bundle; supplying `--input` also confirms every cell against the original candidate-free inputs.
