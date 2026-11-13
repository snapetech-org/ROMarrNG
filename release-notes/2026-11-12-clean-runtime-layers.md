---
category: security
audience: operators
area: containers
action: Update to ROMarrNG 0.14.21.
breaking: false
---
The standard image now starts from a clean pinned Debian runtime, installs the latest packages in its pinned Debian snapshot, and copies in the patched Python runtime. This removes vulnerable package remnants from inherited image layers and applies the Debian fixes available for the release.
