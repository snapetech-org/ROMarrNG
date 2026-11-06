# Product application and readback

The product change is isolated to romarr/ui-labels.json at input head bbbf84d0d83138a23143f6aa6075415ebcb36d3e. The apply script was run only after the root ledger verifier passed and wrote 31 selected values. It preserved catalog key order, left every unselected cell unchanged, and kept all 12 locale catalogs complete.

The product commit is recorded in product-commit.json. The 240-row readback records hashes for every reviewed cell and omits callerless text. verify_product_readback.py compares the recorded input and product Git objects, the 31 selected target hashes, all other reviewed cells, and catalog completeness.

Run python3 verify_product_readback.py from this directory to recheck the committed product object. No native-speaker approval or headed application-browser review is claimed.
