# Localization glossary

Use this glossary when translating ROMarr's interface. Prefer the same term
throughout a locale, and choose wording that people who manage emulators and
game libraries will recognize.

| English term | Meaning in ROMarr | Translation guidance |
| --- | --- | --- |
| ROM | A game image or package used by an emulator | Keep `ROM` when it is the familiar local term. Do not translate a game title or filename as a ROM. |
| ROM dump | A copy of game data read from a cartridge or disc | Preserve the distinction between a dump and a game title. |
| Platform | The console, computer, or arcade system a game was released for | Translate as the emulated system or console; it does not mean an operating system here. |
| DAT | A structured catalog of known game files and checksums | Keep `DAT` uppercase. It is a catalog format, not a date. |
| Match / identify | Comparing file content or a title against catalog records | Use wording that does not imply certainty when ROMarr reports a likely match. |
| Hash / checksum | A value calculated from file contents to identify or verify data | Keep the distinction from a title, filename, or platform ID. Preserve names such as `SHA-1`, `SHA-256`, and `CRC32`. |
| Region | The market or release territory associated with a game version | Do not use this to mean the user's geographic location. |
| Revision | A release revision or version of a game | Keep separate from an emulator update, DLC, or translation patch. |
| Homebrew | Software made for a console by independent developers | Use the established local gaming term where one exists. |
| ROM hack | A modified game image | Preserve the sense that it is a modification; it is not necessarily malware or an exploit. |
| Library | The user's configured collection of game files and metadata | Avoid translating this as a public library or catalog source. |
| Metadata | Descriptive information such as title, release date, synopsis, and artwork | It is information about a game, not the game file itself. |
| Sidecar | A metadata file stored alongside or associated with a game | Explain as an accompanying metadata file if there is no natural local technical term. |
| Shared metadata root | A directory shared between ROMarr and client devices | Keep distinct from the ROM library root. |
| EmuDeck / ES-DE | Names of external projects | Preserve spelling and capitalization. |

Keep these names, identifiers, and data unchanged: ROMarr, SeerrNG, Prowlarr,
No-Intro, Redump, IGDB, Steam, EmuDeck, ES-DE, `DAT`, platform codes, filenames,
filesystem paths, usernames, API values, commands, hashes, and placeholders such
as `{game}`, `{count}`, or `{platforms}`. Do not translate user-supplied game
titles or provider responses.

When the English source could reasonably mean more than one thing, consult the
screen or its help text before translating. Preserve uncertainty words such as
“likely,” “possible,” and “unverified”; they describe what ROMarr has actually
established about a file.
