# ROMarrNG PR #70 Arabic platform-count plural handling

The Arabic Library summary used the singular noun for every count; the headed UI had shown “36 cached across 3 platforms.” This update adds Arabic zero/one/two/few/many/other forms and parses the already formatted `platformCount` using the same regional number locale that produced it. Plural category selection continues to use the UI locale.

The change is pinned to base head `c3bcb5fffb28419f82384ad2202686e97227c4f9` / tree `b7cd0c4948bd8295fc32039072973c13e8ca538a`. The independent exact-diff review found no material defect; it rated runtime/caller confidence high and Arabic wording confidence moderate. Source hash, exact diff hash, catalog readback, changed-file hashes, and review packet are recorded here.

All Arabic plural forms retain `{cached}`; numeric forms also retain `{platformCount}`. Zero/one/two spell the count with Arabic words. No tests, builds, scans, or CI jobs were run. The PR remains open and draft. Focused current-head Arabic Library browser review is recorded at `../browser-review-library-rtl/`; it verifies one desktop viewport and does not replace qualified native-speaker review, which remains outstanding. No workflow changes, merge, release, or tag were made.
