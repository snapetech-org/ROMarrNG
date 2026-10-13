---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---

Local validation snapshots exclude extensionless credentials and files in credential-named folders while retaining token-named source code. The trusted launcher pins sandbox mounts before hiding host paths; task logs are capped at 16 MiB, and receipts stay tied to the workflow attempt that produced them.
