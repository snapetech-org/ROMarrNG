---
category: security
audience: operators
area: validation
action: none
breaking: false
---
Image validation now requires enforcing security scans and pull-request dependency review in the active build workflow, even when legacy standalone scan workflows are disabled. Native acquisition proofs also check that plugins cannot signal the host process or truncate protected state.
