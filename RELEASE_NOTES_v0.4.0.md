# Release Notes v0.4.0

Release date: 2026-03-15

## Highlights

- Journal profiles now load through one runtime page at `journal/?sourceid=...` instead of thousands of generated per-journal folders.
- Legacy journal URLs continue to work through a generated GitHub Pages fallback redirect.
- The source update workflow is now safer because raw-file replacement, build, validation, and smoke testing can run through one guarded command.

## What changed

### Dynamic profile architecture

- Replaced per-journal output folders under `docs/journals/` with one runtime profile page at `docs/journal/index.html`.
- Added `docs/data/profile-index.json` so a profile page can resolve one `sourceid` to the correct search shard without loading the full dataset.
- Updated home, search, and sitemap links to the stable `sourceid` profile model.

### Compatibility and stability

- Added a generated `docs/404.html` fallback that redirects old `journals/<slug>/` URLs to the new profile route on GitHub Pages.
- Extended smoke coverage so legacy journal URLs are verified alongside the current search and profile flows.

### Safer data refresh workflow

- Added `scripts/update_source_data.py` to replace active raw files, rebuild the site, validate the generated output, and run the browser smoke test in one command.
- Added automatic rollback of raw source files when a refresh fails.
- Made the refresh script safe to rerun even when the provided input file is already the active file in `data/raw/`.
- Added a dedicated manual GitHub Actions refresh workflow so rebuild-and-deploy runs can be triggered explicitly without reusing the default pipeline entrypoint.

## Validation status

- Build completed successfully for 29,553 journals.
- Generated-data validation passed for 15 shard files and 29,553 profile-index entries.
- Browser smoke test passed for idle search, prefix-based shard loading, deep-linked filters, abstract insight rendering, dynamic profile resolution, and legacy URL redirects.

## Upgrade note

- Existing direct links should move to the `journal/?sourceid=...` format where possible.
- Old `journals/<slug>/` links remain supported through the generated fallback redirect and no longer require recreating per-journal directories.
