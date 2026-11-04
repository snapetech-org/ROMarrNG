# Application evidence — ROMarrNG PR #70 W465–W484

Catalog parent: 7640720c5e3b1813725cca8d7aa46b5d968bff43 / tree bdee162cc11115256df8756f192b19d4337ed1dc  
Catalog commit: 53361f6c2ca8ad7d35cf844ab7901b91a2ecb06d / tree 36d371b05d28fa75abd89ef34a6af447f501def5

The application changes exactly 12 cross-selected translations in romarr/ui-labels.json (8 corrections and 4 refinements). The 240-cell readback retains 168 accepted values and all 60 callerless holds. All 384 carried hold hashes and 80 prior selected source records were reattested and remain unchanged. Catalog message count and key order, locale key order, translation metadata, and all non-target values are preserved.

The evidence directory includes before/after catalog snapshots, exact selected change rows, a 240-cell readback, the 384-row prior-hold reattestation, the 80-row prior-selection reattestation, pre-apply pins, invariants, and catalog/live-PR commit records. Run python3 application/verify_apply.py --repo . from the repository root. The verifier also checks the complete cross-audit packet and its checksums.

Qualified native-speaker and exact-head browser review remain pending. The cross-audit packet records zero deployments for the exact PR head. No tests, builds, scans, CI, workflow edits, merge, release, or tag were performed.
