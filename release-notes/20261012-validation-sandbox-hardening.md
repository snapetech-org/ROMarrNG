---
category: security
audience: operators
area: ci-security
action: none
breaking: false
---

Validation snapshots omit extensionless authentication, token, credential, and secret files while retaining source code with those names. The trusted validation launcher pins sandbox mount sources through inherited file descriptors before masking host paths. Task output streams to a bounded log with a visible truncation marker, and validation receipt artifacts are scoped to their workflow attempt.
