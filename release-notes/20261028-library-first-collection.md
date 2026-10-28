---
category: changed
audience: users, operators
area: library
action: none
breaking: false
---
ROMarr can start with the games you already own: map a local folder to its system, browse titles with covers, and discover missing games from DAT or IGDB catalogs. Save a named platform catalog and its filters to return to that browse view later. Catalog selections carry across pages, and ROMarr rechecks ownership before adding selected titles to Wanted. Configure download sources only when you choose to acquire games. Supported qBittorrent versions can use API-key authentication.

Set acquisition batches continue in the background after you close the page. Progress distinguishes requests accepted by a downloader from imports completed. If ROMarr stops while a request is in flight, the title is marked for review and is not retried automatically; check Activity and the download client before choosing to retry.

Folder libraries now build durable scan generations in resumable slices. An interrupted or inaccessible scan keeps the last complete inventory available, and CUE/M3U entries show missing media members instead of appearing complete. SQLite stores scan checkpoints, durable job state and a recoverable Wanted outbox beside the state file; Settings can download a consistent catalog database snapshot. Frontend exports include all verifiable entries and report skipped paths, and metadata imports from ROMarr JSON, LaunchBox, Playnite and ES-DE/EmulationStation can be previewed and conflict-reviewed before they are saved.
