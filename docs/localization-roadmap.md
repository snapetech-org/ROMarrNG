# UI localization roadmap

## Current support

The interface is rendered by the Python service in `romarr/ui.py`. The rail footer provides a browser-local language selector for English and the twelve non-English locales listed below. The English-keyed catalog contains 1,210 app-owned UI strings, including labels, help, empty states, prompts, notifications, dynamic library summaries, and finite download/import statuses. Each locale has a value for every source key and English remains the fallback for a missing value.

The regional-format preference is separate from interface language. Fan-translation settings, ROM names, platform slugs, filenames, paths, DAT values, API data, and other user data remain unchanged.

Arabic sets the document language and direction and uses logical layout rules. Earlier browser review covered the shell at 390px and 1280px. In this follow-up, the Agentic VM visual pass refreshed the Arabic library view at 1280px; page-specific API-backed workflows were outside the preview.

## First-pass locale order

This is a practical rollout order, not a claim about these apps' actual user base. Product-level language analytics are not available. It combines global speaker estimates with online-content usage, and keeps the requested Arabic and Asian-language coverage in the first waves:

1. Spanish (es; es-MX where the product already distinguishes it)
2. Simplified Chinese (zh-Hans / zh-CN)
3. Hindi (hi)
4. German (de)
5. Japanese (ja)
6. French (fr)
7. Brazilian Portuguese (pt-BR)
8. Arabic (ar; requires right-to-left layout support)
9. Korean (ko)
10. Traditional Chinese (zh-Hant / zh-TW)
11. Vietnamese (vi)
12. Indonesian (id)

The World Bank's 2025 report estimates Mandarin Chinese, Hindi, and Spanish at 15%, 7.6%, and 6.9% of the global population respectively; its online-content data also places German, Chinese, and Japanese among the leading languages. [World Bank, Digital Progress and Trends Report 2025](https://documents1.worldbank.org/curated/en/099112525160536089/pdf/P505350-59c98ca8-0803-4f23-b470-17f3dab010ab.pdf). W3Techs tracks website content-language share rather than app users. [W3Techs content-language survey](https://w3techs.com/technologies/cross/content_language/ranking). Reorder this list if maintainers later receive reliable demand signals.

## Translation boundaries and acceptance

Translate interface labels, help, empty states, validation, notifications, dynamic summaries, finite status messages, and errors. Keep media titles, user names, filenames and paths, commands, API identifiers, protocol values, and other user-supplied content unchanged. Use the selected UI language for date, time, number, and plural formatting. Every locale falls back to English for a missing key; catalog review checks key coverage, placeholders, and preserved technical tokens. Arabic sets the document language and direction and uses logical layout properties. The shell and initial empty-library state have had a visual RTL pass at narrow and desktop widths; production API-backed workflows remain outside that preview.

## Implemented

The rail footer offers a browser-local interface-language selector for English plus twelve locales: Spanish, Simplified Chinese, Hindi, German, Japanese, French, Brazilian Portuguese, Arabic, Korean, Traditional Chinese, Vietnamese, and Indonesian. The choice stays in that browser. Theme controls, navigation, page titles, Library filters, request and search workflows, empty states, actions, and finite download/import states use the selected language with per-key English fallback.

The interface catalog has 1,210 source keys translated across all twelve non-English locales. It includes navigation and page copy, actions, help, validation, dynamic summaries, status messages, provider-import and webhook instructions, and toast templates. Translated text and attributes carry language metadata; Arabic sets `lang="ar"` and `dir="rtl"`. Unknown statuses and free-form API or user data remain unchanged. This interface setting does not change ROM translation settings or game metadata.

Regional formatting remains a separate browser-local preference. It formats visible counts, ratings, scores, file sizes, calendar days and months, and date/time values across the Library, search, wanted list, import lists, sync status, History, live logs, blocklist, tasks, Statistics, collections, friends, and calendar views. Date-only values stay on their original calendar day; month-day anniversary dates are formatted without inventing a year, and year labels retain their source value.

Arabic direction, selector accessibility, empty-search validation, and storage-failure fallback were reviewed in source. The current follow-up browser pass refreshed the Arabic library at 1280px. It did not refresh a narrow-screen screenshot or exercise empty-search and storage-failure interactions; production API-backed workflows were outside the preview.
