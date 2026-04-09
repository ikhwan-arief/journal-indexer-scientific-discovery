# Journal Discovery

Journal Discovery is a static journal discovery website designed for public hosting on GitHub Pages.

## Current implementation

- Uses Python during the build step only.
- Reads the active Scimago Journal Rank snapshot from `data/raw/scimagojr.csv`.
- Reads the active WoS subset from `data/raw/scimagojr_wos.csv`.
- Reads the active SINTA snapshot from `data/raw/sinta.csv`.
- Optionally reads DOAJ enrichment from `data/raw/doaj.csv`.
- Generates a public static site into `docs/`.
- Writes a lightweight `docs/data/home.json` for homepage metadata plus a `docs/data/search-manifest.json`, `docs/data/profile-index.json`, and sharded `docs/data/search-chunks/` files for on-demand search and profile loading, with title-prefix shard hints so title searches can fetch fewer chunks first.
- Uses a search-first homepage: the result area stays empty on first load and only shows journal cards after a user submits a query.
- Provides a large abstract input on the front page so users can paste an article abstract and search for matching journals inline.
- Can optionally rerank abstract-search shortlists through an external LLM API while keeping the current client-side lexical scorer as the first-stage retriever and fallback path.
- Shows the `SJR Best Quartile` on a single runtime-loaded journal profile page keyed by stable `sourceid` values.
- Exposes a search page for abstract, keyword, title, URL fragment, country, index filter, accreditation filter, quartile filter, and abstract-fit result sorting.
- Applies lightweight NLP preprocessing to abstract and keyword search: normalization, tokenization, stop-word removal (English + Indonesian), and conservative stemming.
- Scores abstract matching from the journal `Title`, `Categories`, `Areas`, and `Subject Area` fields when available, with generic abstract terms weighted below specific topical terms plus phrase-aware matching and conservative acronym/synonym expansion for recurring SME, AI, and digital-transformation concepts.
- Shows `Categories`, `Areas`, and `SINTA Subject Area` when available on journal profile pages and search result profile cards.
- Uses SINTA only for non-metric metadata such as accreditation, subject area, affiliation, and profile links. SINTA numeric metrics and Garuda flags are intentionally not exposed to users.
- Fills journal website, APC status, license, and copyright fields from DOAJ when a journal matches by ISSN or unique exact title.

## SINTA data at a glance

- `data/raw/sinta.csv` is now a required build input.
- The build tries to merge SINTA rows into existing Scimago journal records by exact ISSN first, then by unique exact normalized title.
- SINTA rows that do not match Scimago are still published as standalone journal records with runtime IDs in the form `sinta-<profile_id>`.
- User-facing SINTA fields are limited to non-metric metadata: accreditation, subject area, affiliation, SINTA profile link, and SINTA-backed website fallback.
- SINTA numeric metrics and Garuda flags are intentionally excluded from public search payloads and UI to avoid mixed quality signals.

## Profile page model

- Journal detail pages are no longer generated as one folder per journal under `docs/journals/`.
- The app now serves a single profile page at `docs/journal/index.html`.
- Journal links use a stable runtime identifier. Scimago-backed records keep the Scimago `Sourceid`, for example `journal/?sourceid=12345`, while SINTA-only records use `journal/?sourceid=sinta-<profile_id>`.
- When the raw Scimago snapshot is replaced and rebuilt, the profile page continues to resolve records from the latest generated dataset without requiring per-journal page generation.
- Existing legacy links of the form `journals/<slug>/` are redirected through `docs/404.html` to the new runtime profile URL on GitHub Pages.

## Safe dataset refresh

- Use `python scripts/update_source_data.py --scimago /path/to/scimagojr.csv --wos /path/to/scimagojr_wos.csv --sinta /path/to/sinta.csv` to replace the active raw datasets, rebuild the site, validate the output, and run the browser smoke test in one command.
- Add `--doaj /path/to/doaj.csv` when you also want to replace the enrichment snapshot in the same run.
- The script backs up the current raw data first and restores it automatically if build, validation, or smoke testing fails.
- The GitHub Pages workflow now uses the same guarded script, so local refreshes and CI refreshes follow one orchestration path.

## Known data constraints

- Scimago data does not include the public journal website URL.
- Scimago data does not include APC, license, or author copyright information.
- SINTA data is used only for accreditation and descriptive metadata, not for user-facing numeric quality metrics.
- Those fields remain `Not available` when the current DOAJ snapshot has no matching record.
- Journal website priority is DOAJ first, then SINTA website, then the internal journal profile page when no external website exists in the dataset.

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

To emit frontend config for the optional LLM rerank API, set these environment variables before the build when needed:

```bash
export LLM_API_BASE_URL="https://api.example.com"
export LLM_TIMEOUT_MS="8000"
export LLM_ABSTRACT_MATCH_ENABLED="true"
python scripts/build_site.py
```

When `LLM_API_BASE_URL` points to `localhost` or `127.0.0.1` and `LLM_TIMEOUT_MS` is not set, the build now defaults to `60000` ms to better accommodate local Ollama-style inference.

1. Open `docs/index.html` in a browser for a quick local check.

## Browser smoke test

Use the smoke test to verify that the homepage stays idle on first load, homepage search renders results only after submit, stop-word-only homepage queries stay idle, the advanced search page stays idle on first load, scope-only changes do not trigger shard loading, title-scoped queries only fetch the expected shard files, deep-linked index and accreditation filters load correctly, merged Indonesia records show accreditation badges, SINTA-only profiles resolve correctly, abstract searches render match insight cards, and the optional LLM rerank path succeeds, falls back cleanly, and skips short abstracts.

## Optional LLM API

The external rerank service lives under `src/journal_discovery_llm_api/` and exposes `POST /v1/abstract-match`.

Install its runtime dependencies:

```bash
python -m pip install -r requirements-api.txt
```

Run locally:

```bash
uvicorn journal_discovery_llm_api.app:app --host 127.0.0.1 --port 8000 --app-dir src
```

For local Ollama testing, this baseline has been the most stable on a full `candidate_depth=50` rerank workload:

```bash
export LLM_PROVIDER_KIND="openai_compatible"
export LLM_PROVIDER_BASE_URL="http://127.0.0.1:11434/v1"
export LLM_PROVIDER_API_KEY="ollama"
export LLM_PROVIDER_MODEL="qwen2.5:1.5b"
uvicorn journal_discovery_llm_api.app:app --host 127.0.0.1 --port 8000 --app-dir src
```

When `LLM_PROVIDER_BASE_URL` is local and `LLM_PROVIDER_TIMEOUT_SECONDS` is not set, the API now defaults to `120` seconds instead of `30` seconds.

Container deployment notes for the API are in `deployment/llm_api/README.md`.

## Render Deployment

If you have a Render account, that is the recommended way to run the LLM API for a public deployment.

The repo now includes `render.yaml` plus a Render-ready Dockerfile for the LLM API:

- [render.yaml](/Users/ikhwanarief/Documents/GitHub%20Repositories/Journal_Discovery/render.yaml)
- [Dockerfile](/Users/ikhwanarief/Documents/GitHub%20Repositories/Journal_Discovery/deployment/llm_api/Dockerfile)

High-level flow:

1. Create a Render Web Service from this repository.
2. Let Render read `render.yaml`.
3. Fill in `LLM_PROVIDER_API_KEY` in Render.
   The bundled `render.yaml` already defaults to OpenRouter's `https://openrouter.ai/api/v1` endpoint and `openrouter/free`.
4. After Render gives you a public `onrender.com` URL, set GitHub repo variables:
   - `LLM_API_BASE_URL=https://your-service.onrender.com`
   - `LLM_ABSTRACT_MATCH_ENABLED=true`
5. Trigger a Pages deploy.

This keeps the API key server-side on Render and removes the need for user-supplied browser keys.

Notes for Render free:

- the backend health check is `https://your-service.onrender.com/healthz`
- `https://your-service.onrender.com/` is now a small status page, not the main app UI
- the first request after idle time can be slower because Render free may cold-start the service
- the frontend retries cold-start failures automatically before falling back to lexical ranking
- the public GitHub Pages build uses a smaller default LLM shortlist on `onrender.com` to keep reranking within the browser timeout budget

## GitHub-Only Online Bridge

If you do not have a permanent public host for the LLM API, you can temporarily power the GitHub Pages site from your local machine by combining:

- the local FastAPI rerank service
- an `ngrok` HTTPS tunnel
- GitHub repository variables
- the manual Pages refresh workflow

Use:

```bash
scripts/start_online_llm_bridge.sh
```

That script:

- starts the local LLM API with `qwen2.5:1.5b`
- opens a public `ngrok` HTTPS tunnel
- updates `LLM_API_BASE_URL`, `LLM_TIMEOUT_MS`, and `LLM_ABSTRACT_MATCH_ENABLED` in the GitHub repository
- triggers `Manual Refresh and Deploy Journal Discovery`

To turn it off again and restore the public site to lexical-only fallback:

```bash
scripts/stop_online_llm_bridge.sh
```

Important caveat: this GitHub-only bridge works only while your local machine, local API, and `ngrok` tunnel stay online.

## Local benchmark

Use `./.venv/bin/python scripts/benchmark_abstract_matching.py` to run a small abstract-matching benchmark against article PDFs in `~/Documents/Disertasi/refs`.

Use `--refs-dir /path/to/refs` when your dissertation PDF folder lives elsewhere.

Use `./.venv/bin/python scripts/benchmark_doaj_relevance.py` to run a DOAJ-based relevance benchmark that samples recent article abstracts across several broad domains without storing an API key in the repository. This benchmark reports relevance-oriented metrics such as `Hit@5`, `MRR`, and `nDCG@10`, and keeps exact source-journal retrieval as a secondary signal only.

Add `--llm-rerank-url http://127.0.0.1:8000 --candidate-depth 50 --llm-timeout-ms 60000` to either benchmark when you want to evaluate the LLM-assisted shortlist reranker through the browser app flow against a local Ollama server.

Use `./.venv/bin/python scripts/benchmark_sparse_baselines.py --max-rank 30` to compare two fair lexical baselines on the same sparse journal metadata fields:

- `BM25F` over `Title`, `Categories`, and `Areas`
- `TF-IDF` cosine over the same fields

Use `./.venv/bin/python scripts/export_manual_relevance_template.py --output paper/manual_relevance_benchmark_template.csv` to export a manual-label template that merges candidate journals proposed by the current app, the optional LLM-assisted app ranking, `BM25F`, and `TF-IDF`. The rubric for turning that CSV into a graded-relevance benchmark is documented in `paper/manual_relevance_protocol.md`.

## Generated data validation

Use the generated data validator to confirm that `home.json`, `search-manifest.json`, and all sharded search payloads are structurally consistent before opening a browser.

```bash
python scripts/validate_generated_data.py
```

The validator checks that the lightweight homepage metadata matches the generated search summary, every manifest shard exists, every profile index entry points to the correct chunk, title-prefix chunk mappings stay consistent with the records inside each shard, the manifest country list matches the generated search dataset, `scopus_indexed` stays explicit, SINTA source IDs use the `sinta-...` format, and forbidden SINTA metric fields are not exposed publicly.

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

The script serves `docs/` locally in a headless browser, confirms that the homepage does not render default journal results on idle load, confirms that homepage abstract submit renders result cards, confirms that stop-word-only homepage queries do not fetch shards, confirms that changing only the advanced-search scope still does not fetch shards, checks that title searches only fetch the shard files listed in `docs/data/search-manifest.json` for the relevant title prefix, verifies that deep-linked index and accreditation filters load the full shard set, confirms that merged Indonesia results show accreditation badges, confirms that abstract-scoped search renders the match insight UI, verifies that merged Indonesia and SINTA-only profiles expose the expected non-metric status details, and verifies that a journal profile link resolves through the single dynamic profile page.

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
