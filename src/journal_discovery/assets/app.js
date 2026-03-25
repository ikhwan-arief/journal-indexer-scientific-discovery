const DASH_MARK = "—";
const SEARCH_STOP_WORDS = new Set([
  "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "for", "from", "in", "into", "is", "it", "its", "of", "on", "onto",
  "or", "that", "the", "their", "this", "to", "with", "using", "used", "use", "we", "our", "was", "were", "which", "while", "within",
  "without", "can", "may", "than", "then", "these", "those", "there", "here", "where", "when", "whose", "who", "whom", "what", "how",
  "about", "after", "before", "between", "during", "through", "across", "over", "under", "such", "also", "other", "others", "more",
  "most", "some", "many", "much", "each", "any", "all", "both", "either", "neither", "per", "via", "yet", "still",
  "yang", "dan", "atau", "di", "ke", "dari", "untuk", "pada", "dengan", "dalam", "sebagai", "karena", "bahwa", "ini", "itu", "tersebut",
  "adalah", "oleh", "juga", "agar", "antara", "dapat", "tidak", "serta", "para", "kami", "kita", "anda", "mereka", "sebuah", "suatu",
  "terhadap", "melalui", "hingga", "setelah", "sebelum", "tanpa", "secara", "telah", "belum", "yakni", "yaitu", "guna", "maka", "namun",
  "tetapi", "selain", "saat", "ketika", "jika", "bila", "sehingga", "dalamnya", "atas", "bawah", "lebih", "kurang", "masih", "sudah",
  "lagi", "ialah", "yakinkan", "karna", "nya"
]);

const ENGLISH_SUFFIX_RULES = [
  { suffix: "ization", minLength: 8 },
  { suffix: "isation", minLength: 8 },
  { suffix: "ational", minLength: 8 },
  { suffix: "fulness", minLength: 8 },
  { suffix: "ousness", minLength: 8 },
  { suffix: "iveness", minLength: 8 },
  { suffix: "lessly", minLength: 8 },
  { suffix: "ingly", minLength: 6 },
  { suffix: "edly", minLength: 6 },
  { suffix: "ments", minLength: 6 },
  { suffix: "ment", minLength: 6 },
  { suffix: "ation", minLength: 6 },
  { suffix: "ities", minLength: 6 },
  { suffix: "ings", minLength: 5 },
  { suffix: "ness", minLength: 6 },
  { suffix: "ions", minLength: 5 },
  { suffix: "ion", minLength: 5 },
  { suffix: "ers", minLength: 5 },
  { suffix: "ing", minLength: 5 },
  { suffix: "er", minLength: 5 },
  { suffix: "ed", minLength: 4 },
  { suffix: "ly", minLength: 4 },
  { suffix: "es", minLength: 4 },
  { suffix: "s", minLength: 4 },
];

const INDONESIAN_SUFFIX_RULES = [
  { suffix: "kannya", minLength: 8 },
  { suffix: "annya", minLength: 7 },
  { suffix: "kanlah", minLength: 8 },
  { suffix: "kan", minLength: 5 },
  { suffix: "nya", minLength: 5 },
  { suffix: "lah", minLength: 5 },
  { suffix: "kah", minLength: 5 },
  { suffix: "pun", minLength: 5 },
  { suffix: "tah", minLength: 5 },
  { suffix: "an", minLength: 5 },
];

function normalizeText(value) {
  return (value || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function uniqueTokens(tokens) {
  const seen = new Set();
  const values = [];
  for (const token of tokens) {
    if (!token || seen.has(token)) {
      continue;
    }
    seen.add(token);
    values.push(token);
  }
  return values;
}

function searchPrefix(value) {
  const normalized = normalizeText(value);
  return normalized ? normalized[0] : "#";
}

function isPreciseScope(scope) {
  return scope === "title" || scope === "publisher" || scope === "url";
}

function stemToken(token) {
  if (!token || token.length < 3) {
    return token;
  }

  let current = token;

  if (current.endsWith("ies") && current.length >= 5) {
    current = `${current.slice(0, -3)}y`;
  } else if (current.endsWith("ied") && current.length >= 5) {
    current = `${current.slice(0, -3)}y`;
  }

  for (const rule of INDONESIAN_SUFFIX_RULES) {
    if (current.length >= rule.minLength && current.endsWith(rule.suffix)) {
      current = current.slice(0, -rule.suffix.length);
      break;
    }
  }

  for (const rule of ENGLISH_SUFFIX_RULES) {
    if (current.length >= rule.minLength && current.endsWith(rule.suffix)) {
      current = current.slice(0, -rule.suffix.length);
      break;
    }
  }

  return current.length >= 3 ? current : token;
}

function tokenizeSearchText(value, options = {}) {
  const { removeStopWords = true, minLength = 3, applyStemming = true } = options;
  const normalized = normalizeText(value);
  if (!normalized) {
    return [];
  }

  const processed = [];
  const seen = new Set();
  for (const rawToken of normalized.split(" ")) {
    if (!rawToken) {
      continue;
    }
    const token = applyStemming ? stemToken(rawToken) : rawToken;
    if (!token || token.length < minLength) {
      continue;
    }
    if (removeStopWords && (SEARCH_STOP_WORDS.has(rawToken) || SEARCH_STOP_WORDS.has(token))) {
      continue;
    }
    if (seen.has(token)) {
      continue;
    }
    seen.add(token);
    processed.push(token);
  }

  return processed;
}

function buildProcessedQuery(rawValue, scope) {
  const normalized = normalizeText(rawValue);
  const literalTokens = normalized ? normalized.split(" ").filter(Boolean) : [];
  const tokens = tokenizeSearchText(rawValue);
  const allTokensAreInsignificant = literalTokens.length > 0 && literalTokens.every((token) => {
    const stemmed = stemToken(token);
    return token.length < 3 || SEARCH_STOP_WORDS.has(token) || SEARCH_STOP_WORDS.has(stemmed);
  });
  const canUseLiteralOnly = isPreciseScope(scope) && normalized.length >= 2 && !allTokensAreInsignificant;

  return {
    raw: rawValue || "",
    normalized,
    literalTokens,
    tokens,
    hasRawQuery: Boolean(normalized),
    hasMeaningfulTokens: tokens.length > 0,
    canUseLiteralOnly,
    shouldLoad: tokens.length > 0 || canUseLiteralOnly,
  };
}

function mergeTokenLists(...lists) {
  return uniqueTokens(lists.flat().filter(Boolean));
}

function tokenMatches(tokenSet, tokens) {
  const matched = [];
  for (const token of tokens) {
    if (tokenSet.has(token)) {
      matched.push(token);
    }
  }
  return matched;
}

function tokenScore(tokenSet, tokens, weight) {
  return tokenMatches(tokenSet, tokens).length * weight;
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

function withVersion(relativePath, versionTag) {
  if (!relativePath || !versionTag) {
    return relativePath;
  }
  if (/[?&]v=/.test(relativePath)) {
    return relativePath;
  }
  const separator = relativePath.includes("?") ? "&" : "?";
  return `${relativePath}${separator}v=${encodeURIComponent(versionTag)}`;
}

function blurPaginationFocus() {
  const activeElement = document.activeElement;
  if (!(activeElement instanceof HTMLElement)) {
    return;
  }
  if (activeElement.tagName === "BUTTON" || activeElement.closest(".pagination-list")) {
    activeElement.blur();
  }
}

function scrollElementToViewportTop(element, behavior = "auto") {
  if (!element) {
    return false;
  }
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const targetTop = Math.max(0, Math.round(window.scrollY + element.getBoundingClientRect().top));
  window.scrollTo({ top: targetTop, behavior: prefersReducedMotion ? "auto" : behavior });
  return true;
}

function scheduleScrollToTop(getTarget) {
  blurPaginationFocus();

  const attemptScroll = (behavior = "auto") => {
    const target = getTarget();
    return scrollElementToViewportTop(target, behavior);
  };

  window.requestAnimationFrame(() => {
    attemptScroll("smooth");
    [120, 320, 650, 1000].forEach((delay) => {
      window.setTimeout(() => attemptScroll("auto"), delay);
    });
  });
}

function safeText(value, fallback = "Not available") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function quartilePriority(value) {
  if (value === "Q1") return 4;
  if (value === "Q2") return 3;
  if (value === "Q3") return 2;
  if (value === "Q4") return 1;
  return 0;
}

function journalMetricValue(record) {
  return Number(record.sjr_value || 0);
}

function journalHIndexValue(record) {
  return Number(record.h_index || 0);
}

function createBadge(text, className) {
  const badge = document.createElement("span");
  badge.className = `label ${className}`;
  badge.textContent = text;
  return badge;
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

function buildProfilePath(record) {
  const sourceid = encodeURIComponent(String(record?.sourceid || ""));
  return sourceid ? `journal/?sourceid=${sourceid}` : "journal/";
}

function prepareRecords(records) {
  for (const record of records) {
    if (record._preparedSearch) {
      continue;
    }

    record.scopus_indexed = record.scopus_indexed !== false;
    record.profile_path = buildProfilePath(record);

    const labels = ["Scopus"];
    if (record.wos_indexed) labels.push("WoS");
    if (record.doaj_indexed) labels.push("DOAJ");
    record.index_summary = labels.join(", ");

    record.normalized_title = normalizeText(record.title || "");
    record.normalized_publisher = normalizeText(record.publisher || "");
    record.normalized_country = normalizeText(record.country || "");
    record.normalized_url = normalizeText(record.journal_url || "");
    record.normalized_categories = normalizeText(record.categories || "");
    record.normalized_areas = normalizeText(record.areas || "");
    record.normalized_index_summary = normalizeText(record.index_summary);
    record.normalized_issns = normalizeText((record.issns || []).join(" "));
    record.topic_text = normalizeText(`${record.categories || ""} ${record.areas || ""}`);
    record.sjr_value = Number(record.sjr_value || 0);
    record.h_index = Number(record.h_index || 0);
    record.search_text = [
      record.normalized_title,
      record.normalized_publisher,
      record.normalized_country,
      record.normalized_url,
      record.normalized_index_summary,
      record.normalized_categories,
      record.normalized_areas,
      record.normalized_issns,
    ].filter(Boolean).join(" ");

    record.title_tokens = tokenizeSearchText(record.title || "");
    record.publisher_tokens = tokenizeSearchText(record.publisher || "");
    record.country_tokens = tokenizeSearchText(record.country || "");
    record.url_tokens = tokenizeSearchText(record.journal_url || "");
    record.category_tokens = tokenizeSearchText(record.categories || "");
    record.area_tokens = tokenizeSearchText(record.areas || "");
    record.index_tokens = tokenizeSearchText(record.index_summary);
    record.issn_tokens = tokenizeSearchText((record.issns || []).join(" "), { removeStopWords: false, applyStemming: false });
    record.topic_tokens = mergeTokenLists(record.category_tokens, record.area_tokens);
    record.search_tokens = mergeTokenLists(
      record.title_tokens,
      record.publisher_tokens,
      record.country_tokens,
      record.url_tokens,
      record.category_tokens,
      record.area_tokens,
      record.index_tokens,
      record.issn_tokens
    );

    record.title_token_set = new Set(record.title_tokens);
    record.publisher_token_set = new Set(record.publisher_tokens);
    record.country_token_set = new Set(record.country_tokens);
    record.url_token_set = new Set(record.url_tokens);
    record.category_token_set = new Set(record.category_tokens);
    record.area_token_set = new Set(record.area_tokens);
    record.topic_token_set = new Set(record.topic_tokens);
    record.search_token_set = new Set(record.search_tokens);
    record.issn_token_set = new Set(record.issn_tokens);
    record._preparedSearch = true;
  }
}

function literalMatchScore(text, query) {
  if (!text || !query) {
    return 0;
  }
  if (text === query) {
    return 140;
  }
  if (text.startsWith(query)) {
    return 100;
  }
  if (text.includes(query)) {
    return 70;
  }
  return 0;
}

function fuzzyScore(text, query) {
  const literalScore = literalMatchScore(text, query);
  if (literalScore > 0) {
    return literalScore;
  }
  if (!text || !query) {
    return 0;
  }
  let cursor = 0;
  for (const char of query) {
    cursor = text.indexOf(char, cursor);
    if (cursor === -1) {
      return 0;
    }
    cursor += 1;
  }
  return query.length >= 4 ? 18 : 10;
}

function matchScope(record, scope) {
  if (scope === "abstract") return record.topic_text || "";
  if (scope === "title") return record.normalized_title || "";
  if (scope === "publisher") return record.normalized_publisher || "";
  if (scope === "url") return record.normalized_url || "";
  return record.search_text || "";
}

function matchScopeTokenSet(record, scope) {
  if (scope === "abstract") return record.topic_token_set || new Set();
  if (scope === "title") return record.title_token_set || new Set();
  if (scope === "publisher") return record.publisher_token_set || new Set();
  if (scope === "url") return record.url_token_set || new Set();
  return record.search_token_set || new Set();
}

function abstractScore(record, query) {
  if (!query.hasMeaningfulTokens) {
    return 0;
  }

  const categoryMatches = tokenMatches(record.category_token_set, query.tokens);
  const areaMatches = tokenMatches(record.area_token_set, query.tokens);
  const matchedTerms = mergeTokenLists(categoryMatches, areaMatches);
  if (!matchedTerms.length) {
    return 0;
  }

  let score = 0;
  score += categoryMatches.length * 26;
  score += areaMatches.length * 18;
  score += Math.round((matchedTerms.length / query.tokens.length) * 90);
  score += literalMatchScore(record.topic_text, query.normalized) > 0 ? 12 : 0;
  return score;
}

function abstractInsight(record, query) {
  if (!query.hasMeaningfulTokens) {
    return null;
  }

  const matchedInCategories = tokenMatches(record.category_token_set, query.tokens);
  const matchedInAreas = tokenMatches(record.area_token_set, query.tokens);
  const matchedTerms = mergeTokenLists(matchedInCategories, matchedInAreas);

  if (!matchedTerms.length) {
    return null;
  }

  const fields = [];
  if (matchedInCategories.length) fields.push("Categories");
  if (matchedInAreas.length) fields.push("Areas");

  return {
    terms: matchedTerms.slice(0, 8),
    fields,
  };
}

function allScopeScore(record, query) {
  if (!query.hasMeaningfulTokens && !query.normalized) {
    return 0;
  }

  const matchedTerms = mergeTokenLists(
    tokenMatches(record.title_token_set, query.tokens),
    tokenMatches(record.category_token_set, query.tokens),
    tokenMatches(record.area_token_set, query.tokens),
    tokenMatches(record.publisher_token_set, query.tokens),
    tokenMatches(record.country_token_set, query.tokens),
    tokenMatches(record.url_token_set, query.tokens),
    tokenMatches(record.issn_token_set, query.tokens)
  );

  let score = 0;
  score += literalMatchScore(record.normalized_title, query.normalized);
  score += Math.round(literalMatchScore(record.normalized_publisher, query.normalized) * 0.7);
  score += Math.round(literalMatchScore(record.normalized_url, query.normalized) * 0.7);
  score += Math.round(literalMatchScore(record.search_text, query.normalized) * 0.45);
  score += tokenScore(record.title_token_set, query.tokens, 24);
  score += tokenScore(record.category_token_set, query.tokens, 18);
  score += tokenScore(record.area_token_set, query.tokens, 15);
  score += tokenScore(record.publisher_token_set, query.tokens, 12);
  score += tokenScore(record.country_token_set, query.tokens, 8);
  score += tokenScore(record.url_token_set, query.tokens, 10);
  score += tokenScore(record.issn_token_set, query.tokens, 14);

  if (matchedTerms.length) {
    score += Math.round((matchedTerms.length / query.tokens.length) * 55);
  }

  return score;
}

function preciseScopeScore(record, query, scope) {
  if (!query.normalized) {
    return 0;
  }

  const haystack = matchScope(record, scope);
  if (!haystack) {
    return 0;
  }

  let score = fuzzyScore(haystack, query.normalized);
  if (query.hasMeaningfulTokens) {
    score += tokenScore(matchScopeTokenSet(record, scope), query.tokens, 12);
  }
  return score;
}

function scoreRecord(record, query, scope) {
  if (!query.hasRawQuery) {
    return 1;
  }
  if (scope === "abstract") {
    return abstractScore(record, query);
  }
  if (scope === "all") {
    return allScopeScore(record, query);
  }
  return preciseScopeScore(record, query, scope);
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

function createResultSummary(record) {
  const wrapper = document.createElement("div");
  wrapper.className = "result-summary";

  const summaryItems = [
    `Publisher: ${safeText(record.publisher)}`,
    `Country: ${safeText(record.country)}`,
    `Best quartile: ${safeText(record.sjr_best_quartile, DASH_MARK)}`,
  ];

  if (record.sjr_display) {
    summaryItems.push(`SJR: ${record.sjr_display}`);
  }
  if (record.h_index) {
    summaryItems.push(`H-index: ${record.h_index}`);
  }

  if (record.index_summary) {
    summaryItems.push(`Indexed in: ${record.index_summary}`);
  }

  wrapper.textContent = summaryItems.join(" • ");
  return wrapper;
}

function createSearchActions(record, siteRoot) {
  const wrapper = document.createElement("div");
  wrapper.className = "search-card-actions";

  const profileLink = document.createElement("a");
  profileLink.className = "table-action-link";
  profileLink.href = joinRelative(siteRoot, record.profile_path);
  profileLink.textContent = "Open profile";
  profileLink.title = `Open the profile page for ${record.title}`;
  wrapper.appendChild(profileLink);

  if (record.journal_url) {
    const websiteLink = document.createElement("a");
    websiteLink.className = "button button-secondary";
    websiteLink.href = record.journal_url;
    websiteLink.target = "_blank";
    websiteLink.rel = "noopener noreferrer";
    websiteLink.textContent = "Visit journal website";
    wrapper.appendChild(websiteLink);
  }

  return wrapper;
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

function buildNavigationDetailItem(label, href, linkText, titleText) {
  const wrapper = document.createElement("div");
  wrapper.className = "detail-item";

  const name = document.createElement("div");
  name.className = "field-name";
  name.textContent = label;
  wrapper.appendChild(name);

  const field = document.createElement("div");
  field.className = "field-value";

  if (href) {
    const link = document.createElement("a");
    link.href = href;
    link.textContent = linkText;
    if (titleText) {
      link.title = titleText;
    }
    field.appendChild(link);
  } else {
    field.textContent = safeText(null);
    field.classList.add("field-value-muted");
  }

  wrapper.appendChild(field);
  return wrapper;
}

function setMetaContent(selector, value) {
  const element = document.querySelector(selector);
  if (element) {
    element.setAttribute("content", value);
  }
}

function updateProfileMetadata(record) {
  const description = `${record.title} journal profile with indexing labels, publisher, country, ISSN, website availability, APC status, license, and SJR best quartile.`;
  document.title = `${record.title} | Journal Discovery`;
  setMetaContent('meta[name="description"]', description);
  setMetaContent('meta[property="og:title"]', record.title);
  setMetaContent('meta[property="og:description"]', description);
}

function createEmptyState(titleText, bodyText) {
  const empty = document.createElement("div");
  empty.className = "empty-state";

  const title = document.createElement("strong");
  title.textContent = titleText;
  empty.appendChild(title);

  const body = document.createElement("span");
  body.textContent = bodyText;
  empty.appendChild(body);

  return empty;
}

function renderProfileEmptyState(titleText, bodyText) {
  const root = document.querySelector("#profile-root");
  if (!root) {
    return;
  }

  root.replaceChildren();

  const section = document.createElement("section");
  section.className = "section";
  const shell = document.createElement("div");
  shell.className = "shell";
  shell.appendChild(createEmptyState(titleText, bodyText));
  section.appendChild(shell);
  root.appendChild(section);

  const footerMeta = document.querySelector("#profile-footer-meta");
  if (footerMeta) {
    footerMeta.textContent = "Load a journal profile to view source and rank details.";
  }
}

function renderProfilePage(record, siteRoot) {
  const root = document.querySelector("#profile-root");
  if (!root) {
    return;
  }

  root.replaceChildren();
  updateProfileMetadata(record);

  const searchUrl = `${joinRelative(siteRoot, "search/")}?q=${encodeURIComponent(record.title)}&scope=title`;

  const heroSection = document.createElement("section");
  heroSection.className = "profile-hero";
  const heroShell = document.createElement("div");
  heroShell.className = "shell";

  const breadcrumbs = document.createElement("div");
  breadcrumbs.className = "breadcrumbs";
  const breadcrumbHome = document.createElement("a");
  breadcrumbHome.href = joinRelative(siteRoot, "");
  breadcrumbHome.textContent = "Home";
  breadcrumbs.appendChild(breadcrumbHome);
  breadcrumbs.appendChild(document.createTextNode(" / "));
  const breadcrumbSearch = document.createElement("a");
  breadcrumbSearch.href = joinRelative(siteRoot, "search/");
  breadcrumbSearch.textContent = "Search";
  breadcrumbs.appendChild(breadcrumbSearch);
  breadcrumbs.appendChild(document.createTextNode(" / "));
  const breadcrumbCurrent = document.createElement("span");
  breadcrumbCurrent.textContent = record.title;
  breadcrumbs.appendChild(breadcrumbCurrent);
  heroShell.appendChild(breadcrumbs);

  const heroPanel = document.createElement("div");
  heroPanel.className = "hero-panel";
  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = "Journal profile";
  heroPanel.appendChild(eyebrow);
  const title = document.createElement("h1");
  title.textContent = record.title;
  heroPanel.appendChild(title);
  const copy = document.createElement("p");
  copy.className = "profile-copy";
  copy.textContent = "This page brings together journal details, indexing labels, and access information when available.";
  heroPanel.appendChild(copy);
  heroPanel.appendChild(createLabelRow(record));

  const heroLinks = document.createElement("div");
  heroLinks.className = "profile-links";
  const similarLink = document.createElement("a");
  similarLink.className = "button button-secondary";
  similarLink.href = searchUrl;
  similarLink.textContent = "Search similar journals";
  heroLinks.appendChild(similarLink);
  const homeLink = document.createElement("a");
  homeLink.className = "button button-primary";
  homeLink.href = joinRelative(siteRoot, "");
  homeLink.textContent = "Back to home";
  heroLinks.appendChild(homeLink);
  heroPanel.appendChild(heroLinks);

  heroShell.appendChild(heroPanel);
  heroSection.appendChild(heroShell);
  root.appendChild(heroSection);

  const section = document.createElement("section");
  section.className = "section";
  const shell = document.createElement("div");
  shell.className = "shell";
  const card = document.createElement("div");
  card.className = "profile-card";
  const layout = document.createElement("div");
  layout.className = "profile-layout";

  const main = document.createElement("div");
  main.className = "profile-main detail-grid";
  main.appendChild(buildDetailItem("Website", record.journal_url, siteRoot, true));
  main.appendChild(buildDetailItem("Publisher", record.publisher));
  main.appendChild(buildDetailItem("Country", record.country));
  main.appendChild(buildDetailItem("Region", record.region));
  main.appendChild(buildDetailItem("Indexed In", record.index_summary));
  main.appendChild(buildDetailItem("Best SJR Quartile", record.sjr_best_quartile));
  main.appendChild(buildDetailItem("Directory Quartile Label", record.sjr_quartile));
  main.appendChild(buildDetailItem("APC Status", record.apc_status));
  main.appendChild(buildDetailItem("License", record.license));
  main.appendChild(buildDetailItem("Author Holds Copyright", record.author_holds_copyright));
  main.appendChild(buildDetailItem("ISSN", (record.issns || []).join(", ")));
  main.appendChild(buildDetailItem("Coverage", record.coverage));
  main.appendChild(buildDetailItem("Categories", record.categories));
  main.appendChild(buildDetailItem("Areas", record.areas));
  main.appendChild(buildDetailItem("Open Access", record.open_access));
  main.appendChild(buildDetailItem("Open Access Diamond", record.open_access_diamond));
  layout.appendChild(main);

  const side = document.createElement("aside");
  side.className = "profile-side detail-grid";
  side.appendChild(buildDetailItem("Source ID", record.sourceid));
  side.appendChild(buildNavigationDetailItem("Search", searchUrl, "Search similar journals", `Search journals similar to ${record.title}`));
  side.appendChild(buildNavigationDetailItem("Navigation", joinRelative(siteRoot, ""), "Back to home", "Return to the search homepage"));
  side.appendChild(buildDetailItem("Data note", "Website, APC, license, and copyright details are shown when available."));
  layout.appendChild(side);

  card.appendChild(layout);
  shell.appendChild(card);
  section.appendChild(shell);
  root.appendChild(section);
}

async function renderDynamicProfile(profileIndex, siteRoot) {
  const params = new URLSearchParams(window.location.search);
  const sourceid = params.get("sourceid") || "";
  const versionTag = profileIndex.summary?.generated_at || "";

  if (!sourceid) {
    renderProfileEmptyState(
      "Journal profile not specified.",
      "Open a journal profile from the search results or journal links to load its details."
    );
    return;
  }

  const chunkPath = profileIndex.sourceid_to_chunk?.[sourceid];
  if (!chunkPath) {
    renderProfileEmptyState(
      "Journal profile not found.",
      "This source ID is not present in the current generated dataset."
    );
    return;
  }

  const response = await fetch(joinRelative(siteRoot, withVersion(chunkPath, versionTag)), { credentials: "same-origin" });
  if (!response.ok) {
    throw new Error(`Failed to load journal profile data: ${response.status}`);
  }

  const payload = await response.json();
  const records = payload.records || [];
  prepareRecords(records);
  const record = records.find((item) => String(item.sourceid || "") === sourceid);

  if (!record) {
    renderProfileEmptyState(
      "Journal profile not found.",
      "The current dataset does not contain a matching record in the expected chunk."
    );
    return;
  }

  renderProfilePage(record, siteRoot);
}

function renderSearchExperience(manifest, siteRoot, pageMode) {
  const form = document.querySelector("#search-form");
  const results = document.querySelector("#search-results");
  const resultsCount = document.querySelector("#results-count");
  const resultsSummary = document.querySelector("#results-summary");
  const resultsSection = document.querySelector("#results-section");
  const topPaginationInfo = document.querySelector("#search-pagination-top-info");
  const topPaginationList = document.querySelector("#search-pagination-top-list");
  const paginationInfo = document.querySelector("#search-pagination-info");
  const paginationList = document.querySelector("#search-pagination-list");
  const queryInput = document.querySelector("#q");
  const scopeField = document.querySelector("#scope");
  const indexSelect = document.querySelector("#index-filter");
  const quartileSelect = document.querySelector("#quartile-filter");
  const countrySelect = document.querySelector("#country-filter");

  if (!form || !results || !resultsCount || !queryInput || !scopeField) {
    return;
  }

  const perPage = 10;
  const chunkPaths = manifest.chunk_paths || [];
  const titlePrefixChunks = manifest.title_prefix_chunks || {};
  const versionTag = manifest.summary?.generated_at || "";
  const totalProfiles = Number(manifest.summary?.total_journals || 0).toLocaleString("en-US");
  const loadedChunkMap = new Map();
  const loadingChunkMap = new Map();
  const paginationRegions = [
    { info: topPaginationInfo, list: topPaginationList },
    { info: paginationInfo, list: paginationList },
  ];
  let records = [];
  let page = 1;

  if (resultsSummary) {
    resultsSummary.textContent = `${totalProfiles} journal profiles ready`;
  }

  if (countrySelect) {
    for (const country of manifest.countries || []) {
      const option = document.createElement("option");
      option.value = country;
      option.textContent = country;
      countrySelect.appendChild(option);
    }
  }

  const params = new URLSearchParams(window.location.search);
  queryInput.value = params.get("q") || "";
  scopeField.value = params.get("scope") || (pageMode === "home" ? "abstract" : "all");
  if (indexSelect) indexSelect.value = params.get("index") || "all";
  if (quartileSelect) quartileSelect.value = params.get("quartile") || "all";
  if (countrySelect) countrySelect.value = params.get("country") || "all";
  page = Math.max(1, Number.parseInt(params.get("page") || "1", 10) || 1);

  function currentScope() {
    return scopeField.value || (pageMode === "home" ? "abstract" : "all");
  }

  function currentState() {
    const scope = currentScope();
    const query = buildProcessedQuery(queryInput.value, scope);
    const indexFilter = indexSelect?.value || "all";
    const quartileFilter = quartileSelect?.value || "all";
    const countryFilter = countrySelect?.value || "all";
    const hasFilters = indexFilter !== "all" || quartileFilter !== "all" || countryFilter !== "all";

    return {
      scope,
      query,
      indexFilter,
      quartileFilter,
      countryFilter,
      hasFilters,
      shouldLoad: hasFilters || query.shouldLoad,
      shouldShowPrompt: !hasFilters && !query.hasRawQuery,
      shouldShowNlpHelp: !hasFilters && query.hasRawQuery && !query.shouldLoad,
    };
  }

  function getPreferredChunkPaths(state) {
    if (state.scope === "title" && state.query.normalized) {
      return titlePrefixChunks[searchPrefix(state.query.normalized)] || chunkPaths;
    }
    return chunkPaths;
  }

  function mergeLoadedRecords() {
    records = Array.from(loadedChunkMap.values()).flat();
    return records;
  }

  function searchScrollTarget() {
    return results.querySelector(".search-card") || results.firstElementChild || results;
  }

  function setResultsSectionVisible(visible) {
    if (!resultsSection || pageMode !== "home") {
      return;
    }
    resultsSection.hidden = !visible;
  }

  function resetPaginationUi() {
    for (const region of paginationRegions) {
      if (region.info) {
        region.info.textContent = "";
      }
      if (region.list) {
        region.list.replaceChildren();
      }
    }
  }

  function renderPaginationUi(totalPages, onPageChange) {
    const buttons = [];
    buttons.push({ label: "Prev", page: page - 1, disabled: page === 1 });
    const startPage = Math.max(1, page - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    for (let index = startPage; index <= endPage; index += 1) {
      buttons.push({ label: String(index), page: index, current: index === page });
    }
    buttons.push({ label: "Next", page: page + 1, disabled: page === totalPages });

    for (const region of paginationRegions) {
      if (region.info) {
        region.info.textContent = `Page ${page} of ${totalPages}`;
      }
      if (!region.list) {
        continue;
      }
      region.list.replaceChildren();
      for (const item of buttons) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = item.label;
        button.disabled = Boolean(item.disabled);
        if (item.current) button.setAttribute("aria-current", "page");
        button.addEventListener("click", () => onPageChange(item.page));
        region.list.appendChild(button);
      }
    }
  }

  function renderEmptyResults(titleText, bodyText) {
    results.replaceChildren(createEmptyState(titleText, bodyText));
    resetPaginationUi();
  }

  function renderPrompt() {
    setResultsSectionVisible(false);
    resultsCount.textContent = `${totalProfiles} journal profiles ready.`;
    if (pageMode === "home") {
      renderEmptyResults(
        "Enter an abstract or keyword query",
        "Search results will appear here after you submit an abstract or keyword query from the form above."
      );
      return;
    }
    renderEmptyResults(
      "Start your search",
      "Search by abstract, keyword, title, publisher, country, or URL fragment."
    );
  }

  function renderNlpHelp() {
    setResultsSectionVisible(true);
    resultsCount.textContent = `Add more specific terms to search ${totalProfiles} journal profiles.`;
    renderEmptyResults(
      "Enter more specific search terms",
      "The current query only contains stop words or very short tokens. Add topic-specific words before searching again."
    );
  }

  function renderLoadingState() {
    setResultsSectionVisible(true);
    resultsCount.textContent = `Preparing matches from ${totalProfiles} journal profiles.`;
    results.replaceChildren(createEmptyState("Preparing search results", "Matching journal profiles are being loaded."));
    resetPaginationUi();
  }

  async function ensureRecordsLoaded(state) {
    const preferredChunkPaths = getPreferredChunkPaths(state);
    const pendingChunkPaths = preferredChunkPaths.filter((chunkPath) => !loadedChunkMap.has(chunkPath));

    if (!pendingChunkPaths.length) {
      return mergeLoadedRecords();
    }

    if (!loadedChunkMap.size) {
      renderLoadingState();
    }

    const fetchPromises = pendingChunkPaths.map((chunkPath) => {
      if (loadingChunkMap.has(chunkPath)) {
        return loadingChunkMap.get(chunkPath);
      }

      const fetchPromise = fetch(joinRelative(siteRoot, withVersion(chunkPath, versionTag)), { credentials: "same-origin" })
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

  function applyFilters(state) {
    const matched = [];
    const useQuery = state.query.shouldLoad;
    for (const record of records) {
      if (state.indexFilter === "wos" && !record.wos_indexed) continue;
      if (state.indexFilter === "doaj" && !record.doaj_indexed) continue;
      if (state.indexFilter === "scopus" && !record.scopus_indexed) continue;
      if (state.quartileFilter !== "all" && record.sjr_best_quartile !== state.quartileFilter) continue;
      if (state.countryFilter !== "all" && record.country !== state.countryFilter) continue;

      const score = useQuery ? scoreRecord(record, state.query, state.scope) : 1;
      if (!useQuery || score > 0) {
        matched.push({ score, record });
      }
    }

    matched.sort((left, right) => {
      const leftMetric = journalMetricValue(left.record);
      const rightMetric = journalMetricValue(right.record);
      if (rightMetric !== leftMetric) return rightMetric - leftMetric;

      const leftHIndex = journalHIndexValue(left.record);
      const rightHIndex = journalHIndexValue(right.record);
      if (rightHIndex !== leftHIndex) return rightHIndex - leftHIndex;

      if (right.score !== left.score) return right.score - left.score;
      const quartileGap = quartilePriority(right.record.sjr_best_quartile) - quartilePriority(left.record.sjr_best_quartile);
      if (quartileGap !== 0) return quartileGap;
      if (left.record.rank !== right.record.rank) return left.record.rank - right.record.rank;
      return left.record.title.localeCompare(right.record.title);
    });
    return matched;
  }

  function syncUrl(state) {
    const nextParams = new URLSearchParams();
    const rawQuery = queryInput.value.trim();

    if (rawQuery) {
      nextParams.set("q", rawQuery);
    }
    if (rawQuery && state.scope !== (pageMode === "home" ? "abstract" : "all")) {
      nextParams.set("scope", state.scope);
    }
    if (pageMode === "search") {
      if (state.indexFilter !== "all") nextParams.set("index", state.indexFilter);
      if (state.quartileFilter !== "all") nextParams.set("quartile", state.quartileFilter);
      if (state.countryFilter !== "all") nextParams.set("country", state.countryFilter);
    }
    if (page > 1 && (rawQuery || state.hasFilters)) {
      nextParams.set("page", String(page));
    }

    const nextUrl = `${window.location.pathname}${nextParams.toString() ? `?${nextParams}` : ""}`;
    window.history.replaceState({}, "", nextUrl);
  }

  function renderPage(state, shouldScroll = false) {
    setResultsSectionVisible(true);
    const filtered = applyFilters(state);
    const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
    if (page > totalPages) {
      page = totalPages;
    }
    const start = (page - 1) * perPage;
    const pageItems = filtered.slice(start, start + perPage);

    results.replaceChildren();
    resultsCount.textContent = `${filtered.length.toLocaleString("en-US")} matches found.`;

    if (!pageItems.length) {
      const bodyText = pageMode === "home"
        ? "Try a more specific abstract or keyword, or open advanced search for title and filter options."
        : "Try broader keywords, switch the search scope, or remove one of the filters.";
      results.appendChild(createEmptyState("No journals matched your query.", bodyText));
      resetPaginationUi();
      return;
    }

    for (const entry of pageItems) {
      const { record, score } = entry;
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
      meta.textContent = `Rank ${safeText(record.rank, "-")}`;
      article.appendChild(meta);

      article.appendChild(createResultSummary(record));

      if (state.scope === "abstract") {
        const insight = abstractInsight(record, state.query);
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
      layout.appendChild(main);

      const side = document.createElement("aside");
      side.className = "profile-side detail-grid";
      side.appendChild(buildDetailItem("Best SJR Quartile", record.sjr_best_quartile));
      side.appendChild(buildDetailItem("Author Holds Copyright", record.author_holds_copyright));
      side.appendChild(buildDetailItem("ISSN", (record.issns || []).join(", ")));
      layout.appendChild(side);

      article.appendChild(layout);
      article.appendChild(createSearchActions(record, siteRoot));
      results.appendChild(article);
    }

    renderPaginationUi(totalPages, (nextPage) => {
      page = nextPage;
      const nextState = currentState();
      syncUrl(nextState);
      renderPage(nextState, true);
    });

    if (shouldScroll) {
      scheduleScrollToTop(searchScrollTarget);
    }
  }

  async function loadAndRenderPage(shouldScroll = false) {
    const state = currentState();
    if (state.shouldShowPrompt) {
      page = 1;
      syncUrl(state);
      renderPrompt();
      return;
    }
    if (state.shouldShowNlpHelp) {
      page = 1;
      syncUrl(state);
      renderNlpHelp();
      return;
    }
    if (!state.shouldLoad) {
      page = 1;
      syncUrl(state);
      renderPrompt();
      return;
    }

    await ensureRecordsLoaded(state);
    syncUrl(state);
    renderPage(state, shouldScroll);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    page = 1;
    loadAndRenderPage().catch((error) => {
      throw error;
    });
  });

  for (const element of [scopeField, indexSelect, quartileSelect, countrySelect].filter(Boolean)) {
    element.addEventListener("change", () => {
      page = 1;
      loadAndRenderPage().catch((error) => {
        throw error;
      });
    });
  }

  loadAndRenderPage().catch((error) => {
    throw error;
  });
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

  if (page === "home" || page === "search") {
    renderSearchExperience(payload, siteRoot, page);
  }
  if (page === "profile") {
    await renderDynamicProfile(payload, siteRoot);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  init().catch((error) => {
    const target = document.querySelector("#app-error") || document.querySelector("main");
    if (target) {
      const box = createEmptyState("The discovery interface could not load.", error.message);
      target.prepend(box);
    }
  });
});
