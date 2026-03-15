# Journal Discovery

Journal Discovery is a static journal discovery website designed for public hosting on GitHub Pages.

## Current implementation

- Uses Python and SQLite during the build step only.
- Reads Scimago Journal Rank 2024 from `data/raw/scimagojr 2024.csv`.
- Reads the WoS subset from `data/raw/scimagojr 2024_WoS.csv`.
- Optionally reads DOAJ enrichment from `data/raw/doaj.csv`.
- Generates a public static site into `docs/`.
- Writes a lightweight `docs/data/home.json` for the front page plus a `docs/data/search-manifest.json` and sharded `docs/data/search-chunks/` files for on-demand search loading, with title-prefix shard hints so title searches can fetch fewer chunks first.
- Builds a local SQLite database into `build/journal_discovery.db` for validation and future enrichment.
- Shows all journals from Scimago on the front page with 10 journals per page.
- Provides a large abstract input on the front page so users can paste an article abstract and search for matching journals.
- Shows `Scopus`, `WoS`, and `DOAJ` as check symbols in the front-page table.
- Shows the SJR quartile on the front-page table.
- Shows the `SJR Best Quartile` on each journal profile page.
- Exposes a search page for abstract, keyword, title, URL fragment, country, index filter, and quartile filter.
- Scores abstract matching from the journal `Categories` and `Areas` fields in `scimagojr 2024.csv`.
- Shows `Categories` and `Areas` on journal profile pages and on the search result profile cards.
- Fills journal website, APC status, license, and copyright fields from DOAJ when a journal matches by ISSN or unique exact title.

## Known data constraints

- Scimago data does not include the public journal website URL.
- Scimago data does not include APC, license, or author copyright information.
- Those fields remain `Tidak tersedia` when the current DOAJ snapshot has no matching record.
- For now, title links fall back to the internal journal profile page when no external journal website exists in the dataset.

## Build locally

1. Activate the shared virtual environment if needed.
1. Optionally download the latest DOAJ snapshot for enrichment:

```bash
curl -L https://doaj.org/csv -o "data/raw/doaj.csv"
```

1. Run the build script:

```bash
"/Users/ikhwanarief/Documents/GitHub Repositories/.venv/bin/python" scripts/build_site.py
```

1. Open `docs/index.html` in a browser for a quick local check.

## Browser smoke test

Use the smoke test to verify that the search page stays idle on first load, scope-only changes do not trigger shard loading, title-scoped queries only fetch the expected shard files, deep-linked filters load correctly, and abstract searches render match insight cards.

## Generated data validation

Use the generated data validator to confirm that `home.json`, `search-manifest.json`, and all sharded search payloads are structurally consistent before opening a browser.

```bash
"/Users/ikhwanarief/Documents/GitHub Repositories/.venv/bin/python" scripts/validate_generated_data.py
```

The validator checks that the generated journal totals match across the home and search datasets, every manifest shard exists, title-prefix chunk mappings stay consistent with the records inside each shard, and the manifest country list matches the generated search dataset.

1. Install the browser test dependency:

```bash
"/Users/ikhwanarief/Documents/GitHub Repositories/.venv/bin/python" -m pip install -r requirements-dev.txt
```

1. Install Chromium for Playwright once on the machine:

```bash
"/Users/ikhwanarief/Documents/GitHub Repositories/.venv/bin/python" -m playwright install chromium
```

1. Run the smoke test:

```bash
"/Users/ikhwanarief/Documents/GitHub Repositories/.venv/bin/python" scripts/smoke_test_search_loading.py
```

The script serves `docs/` locally in a headless browser, confirms that no shard file is fetched on idle load, confirms that changing only the search scope still does not fetch shards, checks that title searches only fetch the shard files listed in `docs/data/search-manifest.json` for the relevant title prefix, verifies that a deep-linked filter state loads the full shard set, and confirms that an abstract-scoped search renders the match insight UI.

## Deployment

The repository includes a GitHub Actions workflow that:

- runs the Python build and browser smoke test on pull requests,
- downloads the latest DOAJ CSV snapshot,
- runs the Python build,
- validates the generated JSON data,
- installs Chromium and runs the browser smoke test against the generated `docs/` output,
- uploads the generated `docs/` folder as the GitHub Pages artifact,
- deploys the site to GitHub Pages.

On pull requests, the workflow stops after build and smoke-test validation. Artifact upload and GitHub Pages deployment remain limited to `main` pushes and manual workflow runs.

If you know the final public URL, set the repository variable or environment variable `SITE_URL` during build to enable canonical tags and a sitemap.

## Container deployment

If this project will be deployed to a regular server with Docker or Docker Compose instead of GitHub Pages, use the dedicated guide in `deployment/container/README.md`.

That location is intentional because `docs/` is generated site output and is not a stable place for handwritten operational documentation.
