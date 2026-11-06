# ROMarrNG translation cross-review: browser finding packets

This independent cross-review covers both 24-cell packets at exact source/catalog head `1adc54cb56dd91731b24e402027476855702f04d` / tree `76792bcafecfb1c9243a1352f638e2f21c0bad0b`.

- `runtime-status-candidates.jsonl` SHA-256: `7232e9ae4319aa51ccee525e577920e480580e9574dcedf6236f25859ea2b5d7`.
- `browser-surface-candidates.jsonl` SHA-256: `eaa474643ea2a1ce798facbeae5d81bed6e2b58578cdaead8da2dbabf7f98b9b`.
- Independent decision ledger `crossreview-decisions.jsonl` SHA-256: `e0868118216ff45215d44c80a274f521993dc7c4149246b7f365fcd3999d76d5`.

The runtime-status packet received 19 accepts, two refinements, and three keep-current decisions. The Get Started packet received 21 accepts and three refinements. Across 48 exact source/locale cells, 45 proposed values are accepted or refined and three remain unchanged. All final hashes, source hashes, current catalog values, packet head/tree pins, and the `{where}` placeholder were checked against the exact catalog/source commit. The verifier also checks the pinned caller blobs for `romarr/app.py` and `romarr/ui.py` and the complete evidence checksum list.

The loading message is an in-progress status returned while the game-library cache is unloaded. The “no library configured” message is returned when the configured game-library list is empty. The Get Started process renders `Acquire → Verify → File → Scan → Play`; the adjacent UI copy says ROMarr identifies and files imported folder contents and organizes existing libraries. The “Work toward a complete set” card is explained by its adjacent DAT and collection-progress description. The candidate pointer to the File pipeline is two lines below the actual pipeline at this pinned tree; `source-context.txt` records the exact lines.

Refinements remove spacing before the German ellipsis and Japanese particle in the loading status, avoid redundant wording in the Korean collection title, and use a concise complete-game-set phrase in Simplified and Traditional Chinese. Three clear current game-library error messages (Hindi, Simplified Chinese, Traditional Chinese) remain unchanged.

This pass reviewed the supplied browser findings against exact translation catalog values and source/callsite context. It did not capture new browser screenshots, claim native-speaker approval, or edit ROMarr files. The provided adjacent runtime state was excluded from this packet.

Verification on 2026-11-02 passed against the pinned source/catalog commit and tree above. It checked all 48 rows, including source and target hashes, placeholders, and three caller/source pins; the final dispositions are 40 accept, 5 refine, and 3 keep, with 45 proposed values accepted or refined; this packet made no catalog edits and records no native-speaker approval.

Run the read-only verifier with:

```sh
python3 verify.py --repo /path/to/ROMarrNG
```

`SHA256SUMS.txt` covers every file in this bundle except itself.
