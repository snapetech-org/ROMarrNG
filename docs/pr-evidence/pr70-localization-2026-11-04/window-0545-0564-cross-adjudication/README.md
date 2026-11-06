# ROMarrNG PR #70 W545-W564 cross-selected application

- Reviewed head: `ed82a904e85a95a7f350e6f62d8f06139098054b` / tree `73afce4882b42b3284c0dcec9be81be17333232b`. Product commit: `2a921d8280487f6d172616719f32e3dced243d83` / tree `21996ad9dcfcc6535e52920b36d74c8a9357279f`.
- Applied 2 exact cross-selected locale changes to `romarr/ui-labels.json`. The 240-cell readback records 226 keep-current cells, 2 selected changes, and 12 text-free callerless holds at position 561.
- The readback contains only identifiers, context hashes, and source/target hashes; selected target text appears only in `selected-changes.jsonl`. Hold files contain no source or target text.
- All 240 cells preserve placeholder, markup, numeric, and protected-literal tokens. Catalog key order, locale order, source hashes, and translation metadata are unchanged. No other product file changed.
- The pre-application PR base API SHA and live `main` ref differed; the same values were observed after the product push and are recorded with the PR attestations.
- Verify with `python3 verify_application.py --repo /path/to/ROMarrNG` from this directory.
