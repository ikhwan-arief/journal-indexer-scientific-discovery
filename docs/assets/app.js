const CHECK_MARK = "✓";
const DASH_MARK = "—";
const ABSTRACT_STOP_WORDS = new Set([
  "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into", "is", "it", "of", "on", "or", "that", "the", "their", "this", "to", "with",
  "using", "used", "use", "we", "our", "was", "were", "which", "while", "within", "without", "can", "may", "than", "then", "these", "those",
  "yang", "dan", "atau", "dari", "untuk", "dengan", "dalam", "pada", "adalah", "oleh", "sebagai", "kami", "kita", "ini", "itu", "terhadap"
]);

function normalizeText(value) {
  return (value || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function searchPrefix(value) {
  const normalized = normalizeText(value);
  return normalized ? normalized[0] : "#";
}

function joinRelative(siteRoot, relativePath) {
  if (!relativePath) {
    return siteRoot || ".";
  }
  if (!siteRoot || siteRoot === ".") {
    return relativePath;
  }
  return `${siteRoot}/${relativePath}`;
}

function safeText(value, fallback = "Tidak tersedia") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function createBadge(text, className) {
  const badge = document.createElement("span");
  badge.className = `label ${className}`;
  badge.textContent = text;
  return badge;
}

function createIndexBadgeRow(record) {
  const wrapper = document.createElement("div");
  wrapper.className = "status-row";
  wrapper.appendChild(createBadge("Scopus", "label-scopus"));
  if (record.wos_indexed) wrapper.appendChild(createBadge("WoS", "label-wos"));
  if (record.doaj_indexed) wrapper.appendChild(createBadge("DOAJ", "label-doaj"));
  return wrapper;
}

function createIndexCell(active) {
  const cell = document.createElement("td");
  const marker = document.createElement("span");
  marker.className = "index-check";
  marker.dataset.active = String(Boolean(active));
  marker.textContent = active ? CHECK_MARK : DASH_MARK;
  cell.appendChild(marker);
  return cell;
}

function createLabelRow(record) {
  const wrapper = document.createElement("div");
  wrapper.className = "label-row";
  if (record.scopus_indexed) wrapper.appendChild(createBadge("Scopus", "label-scopus"));
  if (record.wos_indexed) wrapper.appendChild(createBadge("WoS", "label-wos"));
  if (record.doaj_indexed) wrapper.appendChild(createBadge("DOAJ", "label-doaj"));
  if (record.sjr_best_quartile) wrapper.appendChild(createBadge(record.sjr_best_quartile, "label-quartile"));
  return wrapper;
}

function createTitleLink(record, siteRoot) {
  const link = document.createElement("a");
  const href = record.journal_url || joinRelative(siteRoot, record.profile_path);
  link.href = href;
  link.textContent = record.title;
  if (record.journal_url) {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  }
  return link;
}

function createHomeActionLink(record, siteRoot) {
  const link = document.createElement("a");
  link.className = "table-action-link";
  link.href = joinRelative(siteRoot, record.profile_path);
  link.textContent = "View profile";
  link.title = `Open journal profile for ${record.title}`;
  return link;
}

function prepareRecords(records) {
  for (const record of records) {
    record.scopus_indexed = true;
    record.profile_path = `journals/${record.slug}/`;
    const labels = ["Scopus"];
    if (record.wos_indexed) labels.push("WoS");
    if (record.doaj_indexed) labels.push("DOAJ");
    record.index_summary = labels.join(", ");
    record.normalized_title = normalizeText(record.title || "");
    record.normalized_publisher = normalizeText(record.publisher || "");
    record.normalized_country = normalizeText(record.country || "");
    record.normalized_url = normalizeText(record.journal_url || "");
    record.topic_text = normalizeText(`${record.categories || ""} ${record.areas || ""}`);
    record.normalized_categories = normalizeText(record.categories || "");
    record.normalized_areas = normalizeText(record.areas || "");
    record.search_text = [
      record.normalized_title,
      record.normalized_publisher,
      record.normalized_country,
      record.normalized_url,
      normalizeText(record.index_summary),
      record.normalized_categories,
      record.normalized_areas,
      normalizeText((record.issns || []).join(" "))
    ].filter(Boolean).join(" ");
  }
}

function renderHomePage(records, siteRoot) {
  const tbody = document.querySelector("#journal-table-body");
  const summary = document.querySelector("#home-summary");
  const paginationInfo = document.querySelector("#pagination-info");
  const paginationList = document.querySelector("#pagination-list");
  const perPage = 10;
  let page = 1;
  const totalPages = Math.max(1, Math.ceil(records.length / perPage));

  if (summary) {
    summary.textContent = `${records.length.toLocaleString("en-US")} journals in the current discovery index.`;
  }

  function goToPage(nextPage) {
    page = Math.min(Math.max(nextPage, 1), totalPages);
    const start = (page - 1) * perPage;
    const pageItems = records.slice(start, start + perPage);
    tbody.replaceChildren();

    if (summary) {
      summary.textContent = `Showing ${start + 1}-${start + pageItems.length} of ${records.length.toLocaleString("en-US")} journals.`;
    }

    for (const record of pageItems) {
      const row = document.createElement("tr");

      const titleCell = document.createElement("td");
      const titleWrap = document.createElement("div");
      titleWrap.className = "table-title";
      titleWrap.appendChild(createTitleLink(record, siteRoot));
      titleCell.appendChild(titleWrap);
      row.appendChild(titleCell);

      const publisherCell = document.createElement("td");
      const publisherWrap = document.createElement("div");
      publisherWrap.className = "table-publisher";
      publisherWrap.textContent = safeText(record.publisher, "Not available");
      publisherWrap.title = publisherWrap.textContent;
      const publisherMeta = document.createElement("div");
      publisherMeta.className = "mini-meta";
      publisherMeta.textContent = safeText(record.country, "Country not available");
      publisherMeta.title = publisherMeta.textContent;
      publisherCell.appendChild(publisherWrap);
      publisherCell.appendChild(publisherMeta);
      row.appendChild(publisherCell);

      const topicCell = document.createElement("td");
      const topicWrap = document.createElement("div");
      topicWrap.className = "topic-stack";
      const topicPrimary = document.createElement("div");
      topicPrimary.className = "topic-primary";
      topicPrimary.textContent = safeText(record.areas, "Area not available");
      topicPrimary.title = topicPrimary.textContent;
      const topicSecondary = document.createElement("div");
      topicSecondary.className = "topic-secondary";
      topicSecondary.textContent = safeText(record.categories, "Categories not available");
      topicSecondary.title = topicSecondary.textContent;
      topicWrap.appendChild(topicPrimary);
      topicWrap.appendChild(topicSecondary);
      topicCell.appendChild(topicWrap);
      row.appendChild(topicCell);

      const indexedCell = document.createElement("td");
      indexedCell.appendChild(createIndexBadgeRow(record));
      row.appendChild(indexedCell);

      const quartileCell = document.createElement("td");
      const quartilePill = document.createElement("span");
      quartilePill.className = "pill pill-quartile";
      quartilePill.textContent = safeText(record.sjr_quartile, DASH_MARK);
      quartileCell.appendChild(quartilePill);
      row.appendChild(quartileCell);

      const actionCell = document.createElement("td");
      actionCell.appendChild(createHomeActionLink(record, siteRoot));
      row.appendChild(actionCell);

      tbody.appendChild(row);
    }

    if (paginationInfo) {
      paginationInfo.textContent = `Page ${page} of ${totalPages} · 10 journals per page`;
    }

    if (paginationList) {
      paginationList.replaceChildren();
      const buttons = [];
      buttons.push({ label: "‹ Prev", page: page - 1, disabled: page === 1 });
      const startPage = Math.max(1, page - 2);
      const endPage = Math.min(totalPages, startPage + 4);
      for (let index = startPage; index <= endPage; index += 1) {
        buttons.push({ label: String(index), page: index, current: index === page });
      }
      buttons.push({ label: "Next ›", page: page + 1, disabled: page === totalPages });

      for (const item of buttons) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = item.label;
        button.disabled = Boolean(item.disabled);
        if (item.current) {
          button.setAttribute("aria-current", "page");
        }
        button.addEventListener("click", () => goToPage(item.page));
        paginationList.appendChild(button);
      }
    }
  }

  goToPage(1);
}

function extractAbstractTerms(value) {
  return normalizeText(value)
    .split(" ")
    .filter((token) => token.length >= 3 && !ABSTRACT_STOP_WORDS.has(token));
}

function abstractScore(record, query) {
  const topicText = record.topic_text || "";
  if (!topicText) {
    return 0;
  }
  const terms = extractAbstractTerms(query);
  if (!terms.length) {
    return 0;
  }

  let matchScore = 0;
  const matchedTerms = new Set();
  for (const term of terms) {
    if (topicText.includes(term)) {
      matchedTerms.add(term);
      matchScore += term.length >= 7 ? 10 : 6;
    }
  }

  if (!matchedTerms.size) {
    return 0;
  }

  const coverageBonus = Math.round((matchedTerms.size / terms.length) * 80);
  const categoryBonus = fuzzyScore(topicText, normalizeText(record.categories || "")) > 0 ? 10 : 0;
  return matchScore + coverageBonus + categoryBonus;
}

function abstractInsight(record, query) {
  const terms = extractAbstractTerms(query);
  if (!terms.length) {
    return null;
  }

  const matchedTerms = [];
  const matchedInCategories = [];
  const matchedInAreas = [];
  for (const term of terms) {
    let matched = false;
    if ((record.normalized_categories || "").includes(term)) {
      matchedInCategories.push(term);
      matched = true;
    }
    if ((record.normalized_areas || "").includes(term)) {
      matchedInAreas.push(term);
      matched = true;
    }
    if (matched && !matchedTerms.includes(term)) {
      matchedTerms.push(term);
    }
  }

  if (!matchedTerms.length) {
    return null;
  }

  const fieldParts = [];
  if (matchedInCategories.length) fieldParts.push("Categories");
  if (matchedInAreas.length) fieldParts.push("Areas");

  return {
    terms: matchedTerms.slice(0, 8),
    fields: fieldParts,
  };
}

function createInsightBox(insight, score) {
  const wrapper = document.createElement("div");
  wrapper.className = "match-insight";

  const heading = document.createElement("strong");
  heading.textContent = `Abstract fit score: ${Math.round(score)}`;
  wrapper.appendChild(heading);

  const description = document.createElement("span");
  const fieldLabel = insight.fields.length ? insight.fields.join(" and ") : "journal topics";
  description.textContent = `Matched terms found in ${fieldLabel}: ${insight.terms.join(", ")}.`;
  wrapper.appendChild(description);

  return wrapper;
}

function tokenScore(haystack, tokens) {
  let score = 0;
  for (const token of tokens) {
    if (haystack.includes(token)) {
      score += 8;
    }
  }
  return score;
}

function fuzzyScore(text, query) {
  if (!text || !query) {
    return 0;
  }
  if (text === query) {
    return 120;
  }
  if (text.startsWith(query)) {
    return 80;
  }
  if (text.includes(query)) {
    return 60;
  }
  let cursor = 0;
  for (const char of query) {
    cursor = text.indexOf(char, cursor);
    if (cursor === -1) {
      return 0;
    }
    cursor += 1;
  }
  return 20;
}

function matchScope(record, scope) {
  if (scope === "abstract") return record.topic_text || "";
  if (scope === "title") return record.normalized_title || "";
  if (scope === "publisher") return record.normalized_publisher || "";
  if (scope === "url") return record.normalized_url || "";
  return record.search_text || "";
}

function scoreRecord(record, query, scope) {
  if (!query) {
    return 1;
  }
  if (scope === "abstract") {
    return abstractScore(record, query);
  }
  const haystack = matchScope(record, scope);
  if (!haystack) {
    return 0;
  }
  const tokens = query.split(" ").filter(Boolean);
  return fuzzyScore(haystack, query) + tokenScore(haystack, tokens);
}

function buildDetailItem(label, value, siteRoot, isLink = false) {
  const wrapper = document.createElement("div");
  wrapper.className = "detail-item";
  const name = document.createElement("div");
  name.className = "field-name";
  name.textContent = label;
  wrapper.appendChild(name);
  const field = document.createElement("div");
  field.className = "field-value";
  if (isLink && value) {
    const link = document.createElement("a");
    link.href = value;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = value;
    field.appendChild(link);
  } else {
    field.textContent = safeText(value);
    if (!value) {
      field.classList.add("field-value-muted");
    }
  }
  wrapper.appendChild(field);
  return wrapper;
}

function renderSearchPage(manifest, siteRoot) {
  const form = document.querySelector("#search-form");
  const results = document.querySelector("#search-results");
  const resultsCount = document.querySelector("#results-count");
  const paginationInfo = document.querySelector("#search-pagination-info");
  const paginationList = document.querySelector("#search-pagination-list");
  const queryInput = document.querySelector("#q");
  const scopeSelect = document.querySelector("#scope");
  const indexSelect = document.querySelector("#index-filter");
  const quartileSelect = document.querySelector("#quartile-filter");
  const countrySelect = document.querySelector("#country-filter");
  const perPage = 10;
  const chunkPaths = manifest.chunk_paths || [];
  const titlePrefixChunks = manifest.title_prefix_chunks || {};
  const loadedChunkMap = new Map();
  const loadingChunkMap = new Map();
  let records = [];
  let page = 1;

  (manifest.countries || []).forEach((country) => {
    const option = document.createElement("option");
    option.value = country;
    option.textContent = country;
    countrySelect.appendChild(option);
  });

  const params = new URLSearchParams(window.location.search);
  queryInput.value = params.get("q") || "";
  scopeSelect.value = params.get("scope") || "all";
  indexSelect.value = params.get("index") || "all";
  quartileSelect.value = params.get("quartile") || "all";
  countrySelect.value = params.get("country") || "all";
  page = Number(params.get("page") || "1");

  function shouldLoadDataset() {
    return Boolean(queryInput.value.trim())
      || indexSelect.value !== "all"
      || quartileSelect.value !== "all"
      || countrySelect.value !== "all"
      || page > 1;
  }

  function getPreferredChunkPaths() {
    const query = queryInput.value.trim();
    if (scopeSelect.value === "title" && query) {
      return titlePrefixChunks[searchPrefix(query)] || chunkPaths;
    }
    return chunkPaths;
  }

  function mergeLoadedRecords() {
    records = Array.from(loadedChunkMap.values()).flat();
    return records;
  }

  async function ensureRecordsLoaded() {
    const preferredChunkPaths = getPreferredChunkPaths();
    const pendingChunkPaths = preferredChunkPaths.filter((chunkPath) => !loadedChunkMap.has(chunkPath));

    if (!pendingChunkPaths.length) {
      return mergeLoadedRecords();
    }

    if (!loadedChunkMap.size) {
      const totalProfiles = Number(manifest.summary?.total_journals || 0).toLocaleString("en-US");
      const titleScoped = scopeSelect.value === "title" && queryInput.value.trim();
      resultsCount.textContent = titleScoped
        ? `Loading title-matched shards from ${totalProfiles} journal profiles…`
        : `Loading ${totalProfiles} journal profiles…`;
      const loading = document.createElement("div");
      loading.className = "empty-state";
      const title = document.createElement("strong");
      title.textContent = "Loading search dataset";
      loading.appendChild(title);
      const body = document.createElement("span");
      body.textContent = "The search page is fetching journal shards for filtering and ranking.";
      loading.appendChild(body);
      results.replaceChildren(loading);
    }

    const fetchPromises = pendingChunkPaths.map((chunkPath) => {
      if (loadingChunkMap.has(chunkPath)) {
        return loadingChunkMap.get(chunkPath);
      }

      const fetchPromise = fetch(joinRelative(siteRoot, chunkPath), { credentials: "same-origin" })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`Failed to load search chunk: ${response.status}`);
          }
          const payload = await response.json();
          const chunkRecords = payload.records || [];
          prepareRecords(chunkRecords);
          loadedChunkMap.set(chunkPath, chunkRecords);
          return chunkRecords;
        })
        .finally(() => {
          loadingChunkMap.delete(chunkPath);
        });

      loadingChunkMap.set(chunkPath, fetchPromise);
      return fetchPromise;
    });

    await Promise.all(fetchPromises);
    return mergeLoadedRecords();
  }

  function applyFilters() {
    const rawQuery = queryInput.value;
    const query = normalizeText(rawQuery);
    const scope = scopeSelect.value;
    const indexFilter = indexSelect.value;
    const quartileFilter = quartileSelect.value;
    const countryFilter = countrySelect.value;

    const matched = [];
    for (const record of records) {
      if (indexFilter === "wos" && !record.wos_indexed) continue;
      if (indexFilter === "doaj" && !record.doaj_indexed) continue;
      if (indexFilter === "scopus" && !record.scopus_indexed) continue;
      if (quartileFilter !== "all" && record.sjr_best_quartile !== quartileFilter) continue;
      if (countryFilter !== "all" && record.country !== countryFilter) continue;

      const score = scoreRecord(record, query, scope);
      if (!query || score > 0) {
        matched.push({ score, record, rawQuery, scope });
      }
    }

    matched.sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      if (left.record.rank !== right.record.rank) return left.record.rank - right.record.rank;
      return left.record.title.localeCompare(right.record.title);
    });
    return matched;
  }

  function syncUrl() {
    const nextParams = new URLSearchParams();
    if (queryInput.value.trim()) nextParams.set("q", queryInput.value.trim());
    if (queryInput.value.trim() && scopeSelect.value !== "all") nextParams.set("scope", scopeSelect.value);
    if (indexSelect.value !== "all") nextParams.set("index", indexSelect.value);
    if (quartileSelect.value !== "all") nextParams.set("quartile", quartileSelect.value);
    if (countrySelect.value !== "all") nextParams.set("country", countrySelect.value);
    if (page > 1) nextParams.set("page", String(page));
    const nextUrl = `${window.location.pathname}${nextParams.toString() ? `?${nextParams}` : ""}`;
    window.history.replaceState({}, "", nextUrl);
  }

  function renderPrompt() {
    results.replaceChildren();
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const title = document.createElement("strong");
    title.textContent = "Search dataset is ready on demand.";
    empty.appendChild(title);
    const body = document.createElement("span");
    body.textContent = `Enter a query or change a filter to load ${Number(manifest.summary?.total_journals || 0).toLocaleString("en-US")} journal profiles.`;
    empty.appendChild(body);
    results.appendChild(empty);
    if (resultsCount) {
      resultsCount.textContent = `${Number(manifest.summary?.total_journals || 0).toLocaleString("en-US")} profiles available.`;
    }
    if (paginationInfo) {
      paginationInfo.textContent = "Pagination will appear after the dataset is loaded.";
    }
    if (paginationList) {
      paginationList.replaceChildren();
    }
  }

  function renderPage() {
    const filtered = applyFilters();
    const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
    if (page > totalPages) {
      page = totalPages;
    }
    const start = (page - 1) * perPage;
    const pageItems = filtered.slice(start, start + perPage);

    results.replaceChildren();
    if (resultsCount) {
      resultsCount.textContent = `${filtered.length.toLocaleString("en-US")} matches found.`;
    }

    if (!pageItems.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      const title = document.createElement("strong");
      title.textContent = "No journals match the current query.";
      empty.appendChild(title);
      const body = document.createElement("span");
      body.textContent = "Try broader keywords, switch scope, or remove one of the filters.";
      empty.appendChild(body);
      results.appendChild(empty);
    }

    for (const entry of pageItems) {
      const { record, score, rawQuery, scope } = entry;
      const article = document.createElement("article");
      article.className = "search-card";

      const header = document.createElement("div");
      header.className = "results-header";
      const title = document.createElement("h3");
      const profileLink = document.createElement("a");
      profileLink.href = joinRelative(siteRoot, record.profile_path);
      profileLink.textContent = record.title;
      title.appendChild(profileLink);
      header.appendChild(title);
      header.appendChild(createLabelRow(record));
      article.appendChild(header);

      const meta = document.createElement("p");
      meta.className = "profile-meta";
      meta.textContent = `Rank ${safeText(record.rank, "-")} · Publisher ${safeText(record.publisher)} · Country ${safeText(record.country)}`;
      article.appendChild(meta);

      if (scope === "abstract") {
        const insight = abstractInsight(record, rawQuery);
        if (insight) {
          article.appendChild(createInsightBox(insight, score));
        }
      }

      const layout = document.createElement("div");
      layout.className = "profile-layout";

      const main = document.createElement("div");
      main.className = "profile-main detail-grid";
      main.appendChild(buildDetailItem("Website", record.journal_url, siteRoot, true));
      main.appendChild(buildDetailItem("Categories", record.categories));
      main.appendChild(buildDetailItem("Areas", record.areas));
      main.appendChild(buildDetailItem("APC Status", record.apc_status));
      main.appendChild(buildDetailItem("License", record.license));
      main.appendChild(buildDetailItem("Author Holds Copyright", record.author_holds_copyright));
      main.appendChild(buildDetailItem("SJR Best Quartile", record.sjr_best_quartile));
      layout.appendChild(main);

      const side = document.createElement("aside");
      side.className = "profile-side detail-grid";
      side.appendChild(buildDetailItem("Indexed In", record.index_summary));
      side.appendChild(buildDetailItem("ISSN", (record.issns || []).join(", ")));
      side.appendChild(buildDetailItem("Profile Page", window.location.origin ? `${window.location.origin}${joinRelative(siteRoot, record.profile_path).replace(/^\./, "")}` : joinRelative(siteRoot, record.profile_path)));
      layout.appendChild(side);

      article.appendChild(layout);
      results.appendChild(article);
    }

    if (paginationInfo) {
      paginationInfo.textContent = `Page ${page} of ${totalPages}`;
    }
    if (paginationList) {
      paginationList.replaceChildren();
      const buttons = [];
      buttons.push({ label: "Prev", page: page - 1, disabled: page === 1 });
      const startPage = Math.max(1, page - 2);
      const endPage = Math.min(totalPages, startPage + 4);
      for (let index = startPage; index <= endPage; index += 1) {
        buttons.push({ label: String(index), page: index, current: index === page });
      }
      buttons.push({ label: "Next", page: page + 1, disabled: page === totalPages });
      for (const item of buttons) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = item.label;
        button.disabled = Boolean(item.disabled);
        if (item.current) button.setAttribute("aria-current", "page");
        button.addEventListener("click", () => {
          page = item.page;
          syncUrl();
          renderPage();
        });
        paginationList.appendChild(button);
      }
    }
  }

  async function loadAndRenderPage() {
    if (!shouldLoadDataset()) {
      renderPrompt();
      return;
    }
    await ensureRecordsLoaded();
    renderPage();
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    page = 1;
    syncUrl();
    loadAndRenderPage().catch((error) => {
      throw error;
    });
  });

  for (const element of [scopeSelect, indexSelect, quartileSelect, countrySelect]) {
    element.addEventListener("change", () => {
      page = 1;
      syncUrl();
      loadAndRenderPage().catch((error) => {
        throw error;
      });
    });
  }

  if (shouldLoadDataset()) {
    loadAndRenderPage();
  } else {
    renderPrompt();
  }
}

async function init() {
  const body = document.body;
  const page = body.dataset.page;
  const siteRoot = body.dataset.siteRoot || ".";
  const dataUrl = body.dataset.dataUrl;
  if (!page || !dataUrl) {
    return;
  }

  const response = await fetch(dataUrl, { credentials: "same-origin" });
  if (!response.ok) {
    throw new Error(`Failed to load journal data: ${response.status}`);
  }
  const payload = await response.json();

  if (page === "home") {
    const records = payload.records || [];
    prepareRecords(records);
    renderHomePage(records, siteRoot);
  }
  if (page === "search") {
    renderSearchPage(payload, siteRoot);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  init().catch((error) => {
    const target = document.querySelector("#app-error") || document.querySelector("main");
    if (target) {
      const box = document.createElement("div");
      box.className = "empty-state";
      const title = document.createElement("strong");
      title.textContent = "The discovery interface could not load.";
      box.appendChild(title);
      const body = document.createElement("span");
      body.textContent = error.message;
      box.appendChild(body);
      target.prepend(box);
    }
  });
});
