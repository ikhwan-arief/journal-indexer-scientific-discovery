# Journal Discovery

Journal Discovery is a static journal discovery website designed for public hosting on GitHub Pages.

## Current implementation

- Uses Python during the build step only.
- Reads the active Scimago Journal Rank snapshot from `data/raw/scimagojr.csv`.
- Reads the active WoS subset from `data/raw/scimagojr_wos.csv`.
- Optionally reads DOAJ enrichment from `data/raw/doaj.csv`.
- Generates a public static site into `docs/`.
- Writes a lightweight `docs/data/home.json` for homepage metadata plus a `docs/data/search-manifest.json`, `docs/data/profile-index.json`, and sharded `docs/data/search-chunks/` files for on-demand search and profile loading, with title-prefix shard hints so title searches can fetch fewer chunks first.
- Uses a search-first homepage: the result area stays empty on first load and only shows journal cards after a user submits a query.
- Provides a large abstract input on the front page so users can paste an article abstract and search for matching journals inline.
- Shows the `SJR Best Quartile` on a single runtime-loaded journal profile page keyed by stable `sourceid` values.
- Exposes a search page for abstract, keyword, title, URL fragment, country, index filter, quartile filter, and abstract-fit result sorting.
- Applies lightweight NLP preprocessing to abstract and keyword search: normalization, tokenization, stop-word removal (English + Indonesian), and conservative stemming.
- Scores abstract matching from the journal `Title`, `Categories`, and `Areas` fields in `scimagojr.csv`, with generic abstract terms weighted below specific topical terms plus phrase-aware matching and conservative acronym/synonym expansion for recurring SME, AI, and digital-transformation concepts.
- Shows `Categories` and `Areas` on the journal profile page and on the search result profile cards.
- Fills journal website, APC status, license, and copyright fields from DOAJ when a journal matches by ISSN or unique exact title.

## Profile page model

- Journal detail pages are no longer generated as one folder per journal under `docs/journals/`.
- The app now serves a single profile page at `docs/journal/index.html`.
- Journal links use the stable Scimago `Sourceid` as the runtime identifier, for example `journal/?sourceid=12345`.
- When the raw Scimago snapshot is replaced and rebuilt, the profile page continues to resolve records from the latest generated dataset without requiring per-journal page generation.
- Existing legacy links of the form `journals/<slug>/` are redirected through `docs/404.html` to the new runtime profile URL on GitHub Pages.

## Safe dataset refresh

- Use `python scripts/update_source_data.py --scimago /path/to/scimagojr.csv --wos /path/to/scimagojr_wos.csv` to replace the active raw datasets, rebuild the site, validate the output, and run the browser smoke test in one command.
- Add `--doaj /path/to/doaj.csv` when you also want to replace the enrichment snapshot in the same run.
- The script backs up the current raw data first and restores it automatically if build, validation, or smoke testing fails.
- The GitHub Pages workflow now uses the same guarded script, so local refreshes and CI refreshes follow one orchestration path.

## Known data constraints

- Scimago data does not include the public journal website URL.
- Scimago data does not include APC, license, or author copyright information.
- Those fields remain `Tidak tersedia` when the current DOAJ snapshot has no matching record.
- For now, title links fall back to the internal journal profile page when no external journal website exists in the dataset.

## Build locally

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

1. Confirm the active interpreter if needed:

```bash
python --version
```

1. Optionally download the latest DOAJ snapshot for enrichment:

```bash
curl -L https://doaj.org/csv -o "data/raw/doaj.csv"
```

1. Run the build script:

```bash
python scripts/build_site.py
```

1. Open `docs/index.html` in a browser for a quick local check.

## Browser smoke test

Use the smoke test to verify that the homepage stays idle on first load, homepage search renders results only after submit, stop-word-only homepage queries stay idle, the advanced search page stays idle on first load, scope-only changes do not trigger shard loading, title-scoped queries only fetch the expected shard files, deep-linked filters load correctly, and abstract searches render match insight cards.

## Local benchmark

Use `./.venv/bin/python scripts/benchmark_abstract_matching.py` to run a small abstract-matching benchmark against article PDFs in `~/Documents/Disertasi/refs`.

Use `--refs-dir /path/to/refs` when your dissertation PDF folder lives elsewhere.

Use `./.venv/bin/python scripts/benchmark_doaj_relevance.py` to run a DOAJ-based relevance benchmark that samples recent article abstracts across several broad domains without storing an API key in the repository. This benchmark reports relevance-oriented metrics such as `Hit@5`, `MRR`, and `nDCG@10`, and keeps exact source-journal retrieval as a secondary signal only.

## Generated data validation

Use the generated data validator to confirm that `home.json`, `search-manifest.json`, and all sharded search payloads are structurally consistent before opening a browser.

```bash
python scripts/validate_generated_data.py
```

The validator checks that the lightweight homepage metadata matches the generated search summary, every manifest shard exists, every profile index entry points to the correct chunk, title-prefix chunk mappings stay consistent with the records inside each shard, and the manifest country list matches the generated search dataset.

1. Install the browser test dependency:

```bash
python -m pip install -r requirements-dev.txt
```

1. Install Chromium for Playwright once on the machine:

```bash
python -m playwright install chromium
```

1. Run the smoke test:

```bash
python scripts/smoke_test_search_loading.py
```

The script serves `docs/` locally in a headless browser, confirms that the homepage does not render default journal results on idle load, confirms that homepage abstract submit renders result cards, confirms that stop-word-only homepage queries do not fetch shards, confirms that changing only the advanced-search scope still does not fetch shards, checks that title searches only fetch the shard files listed in `docs/data/search-manifest.json` for the relevant title prefix, verifies that a deep-linked filter state loads the full shard set, confirms that an abstract-scoped search renders the match insight UI, and verifies that a journal profile link resolves through the single dynamic profile page.

## Deployment

The repository includes a GitHub Actions workflow that:

- runs the guarded dataset refresh workflow on pull requests,
- downloads the latest DOAJ CSV snapshot,
- runs `scripts/update_source_data.py` against the active raw snapshots so build, validation, and smoke-test behavior stay aligned with local usage,
- uploads the generated `docs/` folder as the GitHub Pages artifact,
- deploys the site to GitHub Pages.

On pull requests, the workflow stops after build and smoke-test validation. Artifact upload and GitHub Pages deployment remain limited to `main` pushes.

For a manual refresh path, use the dedicated GitHub Actions workflow `Manual Refresh and Deploy Journal Discovery`. It exposes booleans for downloading the latest DOAJ snapshot, keeping or skipping the smoke test, and choosing whether the refreshed `docs/` output should be deployed to GitHub Pages.

If you know the final public URL, set the repository variable or environment variable `SITE_URL` during build to enable canonical tags and a sitemap.

## Container deployment

If this project will be deployed to a regular server with Docker or Docker Compose instead of GitHub Pages, use the dedicated guide in `deployment/container/README.md`.

That location is intentional because `docs/` is generated site output and is not a stable place for handwritten operational documentation.
