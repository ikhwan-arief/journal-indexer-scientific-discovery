# Changelog

## Unreleased

- Generalized local setup instructions so the repo docs no longer depend on machine-specific paths.
- Added and documented the container deployment guide for non-GitHub-Pages hosting.
- Refined public-facing search copy, including the `Search journal profiles` navigation label.
- Obfuscated the public contact email shown on the site.
- Stabilized the active Scimago source filenames to `data/raw/scimagojr.csv` and `data/raw/scimagojr_wos.csv`.
- Updated build and deployment docs to match the stable Scimago filenames.
- Verified the successful GitHub Pages deployment for the latest `main` changes.
- Added a dedicated `RELEASE_NOTES_v0.4.0.md` summary for the current milestone.
- Updated GitHub Actions to run the guarded dataset refresh workflow instead of duplicating build, validation, and smoke-test orchestration across separate CI steps.
- Added a dedicated manual GitHub Actions workflow for refresh-and-deploy runs so manual dataset refreshes no longer share the same trigger as the default push and pull-request pipeline.

## v0.4.0 - 2026-03-15

- Replaced per-journal generated profile folders with one runtime-loaded profile page at `docs/journal/index.html`.
- Introduced `docs/data/profile-index.json` so profile pages can resolve a journal by stable `sourceid` without loading every shard.
- Updated journal links, sitemap entries, validation, and smoke tests to use `journal/?sourceid=...`.
- Preserved GitHub Pages compatibility while making the profile layer data-driven instead of folder-driven.

## v0.3.0 - 2026-03-15

- Removed the remaining SQLite build step and confirmed the public app no longer depends on any runtime database file.
- Simplified build documentation so the project is described as a Python-to-static-site pipeline.
- Revalidated the generated site after the SQLite cleanup.

## v0.2.0 - 2026-03-15

- Added sharded search payloads under `docs/data/search-chunks/` for on-demand loading.
- Added `docs/data/search-manifest.json` with title-prefix shard hints.
- Added generated-data validation and browser smoke-test coverage for search loading behavior.

## v0.1.0 - 2026-03-15

- Delivered the initial static GitHub Pages journal discovery site.
- Added home browsing, abstract-based matching, index badges, quartile display, and journal detail pages.
- Built the first Scimago, WoS, and DOAJ ingestion flow that generates the `docs/` site output.
