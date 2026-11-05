# ROMarrNG W765–W784 French proposal finding erratum

Append-only erratum for the sealed integrated cross-review at `/mnt/disks/scratch/task-scratch/romarrng-pr70-w765-784-integrated-cross-review-20261105/`. The original packet is not rewritten; its checksum-list SHA256 remains `45ad89aa23ef002858e25e63f1633ff30e1f2088db3b45b9bc4dd365bb2597e9`.

For `ui.optional-connections-to-the-rest-of.636208f858::fr`, the cross row says the blind proposal contains “Connexions facultative” and should be corrected to “Connexions facultatives.” The sealed blind row actually contains “Connexions facultatives au reste de la pile.” The proposal has the plural `s`; the reported grammar error is unsupported and stale.

Correct treatment: withdraw the blind-proposal rejection. Keep the cross disposition `accept-current` and `rootSelectionChangeRequired: false`. The pinned current French target and the blind proposal both use the grammatical plural. No target is selected or applied by this erratum. This does not change the other 20 manual-literal root-change advisories.

The packet includes the exact cross and blind rows, hashes, and a verifier. It reads only sealed scratch packets and does not access a product worktree or repository.
