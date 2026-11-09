---
category: fixed
audience: users
area: library
action: none
breaking: false
---
Folder backends without a durable catalog now reuse one scan across counts and shelf pages, avoiding repeated filesystem walks. Explicit rescans refresh the snapshot immediately. Adapted from GalballyJ’s contribution in PR #58, with synchronized cache access and durable scans preserved.
