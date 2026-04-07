/*
Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id)
Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
*/

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

const ABSTRACT_TITLE_WEIGHT = 10;
const ABSTRACT_CATEGORY_WEIGHT = 42;
const ABSTRACT_AREA_WEIGHT = 30;
const ABSTRACT_SUBJECT_AREA_WEIGHT = 34;
const ABSTRACT_TITLE_PHRASE_WEIGHT = 24;
const ABSTRACT_CATEGORY_PHRASE_WEIGHT = 38;
const ABSTRACT_AREA_PHRASE_WEIGHT = 30;
const ABSTRACT_SUBJECT_AREA_PHRASE_WEIGHT = 32;
const ABSTRACT_TITLE_CONCEPT_WEIGHT = 16;
const ABSTRACT_CATEGORY_CONCEPT_WEIGHT = 24;
const ABSTRACT_AREA_CONCEPT_WEIGHT = 20;
const ABSTRACT_SUBJECT_AREA_CONCEPT_WEIGHT = 22;
const ABSTRACT_DETAIL_BONUS = 12;
const ABSTRACT_PHRASE_DETAIL_BONUS = 10;
const ABSTRACT_CONCEPT_DETAIL_BONUS = 8;
const ABSTRACT_FIELD_COVERAGE_BONUS = 8;
const ABSTRACT_PHRASE_LIMIT = 60;
const ABSTRACT_RECORD_PHRASE_LIMIT = 18;
const ABSTRACT_LOW_SIGNAL_TOKEN_WEIGHT = 0.25;
const ABSTRACT_TOKEN_SIGNAL_REFERENCE = 60;
const ABSTRACT_TOKEN_SIGNAL_MIN = 0.6;
const ABSTRACT_TOKEN_SIGNAL_MAX = 1.8;
const DEFAULT_LLM_TIMEOUT_MS = 8000;
const LLM_ABSTRACT_MIN_CHARS = 200;
const LLM_ABSTRACT_MIN_MEANINGFUL_TOKENS = 15;
const LLM_RERANK_CANDIDATE_LIMIT = 50;
const LLM_QUERY_CHAR_LIMIT = 3000;
const LLM_TITLE_CHAR_LIMIT = 240;
const LLM_CATEGORY_CHAR_LIMIT = 480;
const LLM_AREA_CHAR_LIMIT = 420;
const LLM_SUBJECT_AREA_CHAR_LIMIT = 240;
const LLM_PROVIDER_STORAGE_PREFIX = "jd.llmBrowserDirect";
const LLM_PROVIDER_ALLOWED_MATCHED_FIELDS = new Set(["title", "categories", "areas", "subject_area"]);
const ABSTRACT_LOW_SIGNAL_TERMS = [
  "study", "work", "research", "result", "method", "analysis", "data", "model", "system", "approach",
  "performance", "program", "strategy", "design", "evaluation", "practice", "management", "policy",
  "development", "science", "engineering", "health", "public", "clinical", "care", "knowledge",
  "communication", "process", "review"
];
const ABSTRACT_CONCEPT_ALIASES = [
  { concept: "artificial_intelligence", label: "artificial intelligence", aliases: ["artificial intelligence", "ai"] },
  { concept: "generative_artificial_intelligence", label: "generative artificial intelligence", aliases: ["generative artificial intelligence", "generative ai", "genai"] },
  { concept: "large_language_model", label: "large language model", aliases: ["large language model", "large language models", "llm", "llms"] },
  { concept: "machine_learning", label: "machine learning", aliases: ["machine learning", "ml"] },
  { concept: "deep_learning", label: "deep learning", aliases: ["deep learning"] },
  { concept: "digital_transformation", label: "digital transformation", aliases: ["digital transformation", "digitalisation", "digitalization", "digitisation", "digitization"] },
  {
    concept: "small_medium_enterprise",
    label: "small and medium enterprises",
    aliases: [
      "small and medium sized enterprises",
      "small and medium sized enterprise",
      "small and medium enterprises",
      "small and medium enterprise",
      "small medium enterprises",
      "small medium enterprise",
      "smes",
      "sme",
      "msmes",
      "msme",
      "ukm",
      "umkm"
    ],
  },
  { concept: "industry_4_0", label: "industry 4.0", aliases: ["industry 4 0", "industry4 0", "industry4.0", "industrie 4 0"] },
  { concept: "internet_of_things", label: "internet of things", aliases: ["internet of things", "iot"] },
  { concept: "supply_chain", label: "supply chain", aliases: ["supply chain", "supply chains"] },
  { concept: "resource_based_view", label: "resource based view", aliases: ["resource based view", "resource based theory", "rbv"] },
  { concept: "knowledge_based_view", label: "knowledge based view", aliases: ["knowledge based view", "kbv"] },
  { concept: "dynamic_capability", label: "dynamic capabilities", aliases: ["dynamic capabilities", "dynamic capability", "dynamic managerial capabilities"] },
  { concept: "knowledge_management", label: "knowledge management", aliases: ["knowledge management", "knowledge sharing", "knowledge integration"] },
  { concept: "business_intelligence", label: "business intelligence", aliases: ["business intelligence"] },
  { concept: "big_data_analytics", label: "big data analytics", aliases: ["big data analytics", "business analytics", "data analytics"] },
  { concept: "financial_management", label: "financial management", aliases: ["financial management", "financial diagnostics"] },
  { concept: "decision_support", label: "decision support", aliases: ["decision support", "decision making", "decision-making"] },
  { concept: "competitive_advantage", label: "competitive advantage", aliases: ["competitive advantage", "sustainable competitive advantage"] },
  { concept: "green_innovation", label: "green innovation", aliases: ["green innovation", "environmental innovation"] },
  { concept: "e_commerce", label: "e-commerce", aliases: ["e commerce", "ecommerce"] },
];

let abstractTokenDocumentCounts = new Map();
let abstractTokenDocumentCountKey = "";

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

const ABSTRACT_CONCEPT_RULES = ABSTRACT_CONCEPT_ALIASES.map((entry) => ({
  token: `concept_${entry.concept}`,
  label: entry.label,
  aliases: entry.aliases.map((alias) => normalizeText(alias)).filter(Boolean),
}));
const ABSTRACT_CONCEPT_LABELS = new Map(ABSTRACT_CONCEPT_RULES.map((entry) => [entry.token, entry.label]));

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

const ABSTRACT_LOW_SIGNAL_TOKENS = new Set(ABSTRACT_LOW_SIGNAL_TERMS.map((token) => stemToken(token)));

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

function orderedSearchTokens(value, options = {}) {
  const { removeStopWords = true, minLength = 3, applyStemming = true } = options;
  const normalized = normalizeText(value);
  if (!normalized) {
    return [];
  }

  const processed = [];
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
    processed.push(token);
  }

  return processed;
}

function extractConceptTokens(value) {
  const normalized = normalizeText(value);
  if (!normalized) {
    return [];
  }

  const padded = ` ${normalized} `;
  const matches = [];
  for (const rule of ABSTRACT_CONCEPT_RULES) {
    if (rule.aliases.some((alias) => padded.includes(` ${alias} `))) {
      matches.push(rule.token);
    }
  }
  return matches;
}

function extractPhraseTokens(value, options = {}) {
  const { maxPhrases = ABSTRACT_PHRASE_LIMIT } = options;
  const orderedTokens = orderedSearchTokens(value);
  if (!orderedTokens.length || maxPhrases <= 0) {
    return [];
  }

  const phraseEntries = [];
  for (const size of [3, 2]) {
    for (let index = 0; index <= orderedTokens.length - size; index += 1) {
      const slice = orderedTokens.slice(index, index + size);
      if (slice.length !== size || slice.some((token) => ABSTRACT_LOW_SIGNAL_TOKENS.has(token))) {
        continue;
      }
      const phrase = `phrase_${slice.join("_")}`;
      const specificity = slice.reduce((total, token) => total + Math.min(token.length, 12), 0) + (size * 6);
      phraseEntries.push({ phrase, specificity, position: index });
    }
  }

  phraseEntries.sort((left, right) => {
    if (right.specificity !== left.specificity) return right.specificity - left.specificity;
    return left.position - right.position;
  });

  const phrases = [];
  const seen = new Set();
  for (const entry of phraseEntries) {
    if (seen.has(entry.phrase)) {
      continue;
    }
    seen.add(entry.phrase);
    phrases.push(entry.phrase);
    if (phrases.length >= maxPhrases) {
      break;
    }
  }
  return phrases;
}

function displayAbstractSignal(signal) {
  if (!signal) {
    return signal;
  }
  if (signal.startsWith("concept_")) {
    return ABSTRACT_CONCEPT_LABELS.get(signal) || signal.slice(8).replaceAll("_", " ");
  }
  if (signal.startsWith("phrase_")) {
    return signal.slice(7).replaceAll("_", " ");
  }
  return signal;
}

function buildProcessedQuery(rawValue, scope) {
  const trimmedRaw = (rawValue || "").trim();
  const normalized = normalizeText(rawValue);
  const literalTokens = normalized ? normalized.split(" ").filter(Boolean) : [];
  const tokens = tokenizeSearchText(rawValue);
  const conceptTokens = extractConceptTokens(rawValue);
  const phraseTokens = extractPhraseTokens(rawValue);
  const allTokensAreInsignificant = literalTokens.length > 0 && literalTokens.every((token) => {
    const stemmed = stemToken(token);
    return token.length < 3 || SEARCH_STOP_WORDS.has(token) || SEARCH_STOP_WORDS.has(stemmed);
  });
  const canUseLiteralOnly = isPreciseScope(scope) && normalized.length >= 2 && !allTokensAreInsignificant;
  const hasMeaningfulSignals = tokens.length > 0 || conceptTokens.length > 0 || phraseTokens.length > 0;

  return {
    raw: rawValue || "",
    trimmedRaw,
    rawLength: trimmedRaw.length,
    normalized,
    literalTokens,
    tokens,
    conceptTokens,
    phraseTokens,
    meaningfulTokenCount: tokens.length,
    hasRawQuery: Boolean(normalized),
    hasMeaningfulTokens: hasMeaningfulSignals,
    canUseLiteralOnly,
    shouldLoad: hasMeaningfulSignals || canUseLiteralOnly,
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

function buildAbstractTokenSignals(records) {
  const nextKey = String(records.length);
  if (abstractTokenDocumentCountKey === nextKey) {
    return;
  }

  const counts = new Map();
  for (const record of records) {
    const uniqueRecordTokens = new Set([
      ...(record.abstract_title_tokens || []),
      ...(record.abstract_category_specific_tokens || []),
      ...(record.abstract_area_specific_tokens || []),
      ...(record.abstract_subject_area_specific_tokens || []),
      ...(record.title_phrase_tokens || []),
      ...(record.category_phrase_tokens || []),
      ...(record.area_phrase_tokens || []),
      ...(record.subject_area_phrase_tokens || []),
      ...(record.title_concept_tokens || []),
      ...(record.category_concept_tokens || []),
      ...(record.area_concept_tokens || []),
      ...(record.subject_area_concept_tokens || []),
    ]);
    for (const token of uniqueRecordTokens) {
      counts.set(token, (counts.get(token) || 0) + 1);
    }
  }

  abstractTokenDocumentCounts = counts;
  abstractTokenDocumentCountKey = nextKey;
}

function abstractTokenSignal(token) {
  if (!token) {
    return ABSTRACT_TOKEN_SIGNAL_MIN;
  }
  if (ABSTRACT_LOW_SIGNAL_TOKENS.has(token)) {
    return ABSTRACT_LOW_SIGNAL_TOKEN_WEIGHT;
  }
  const count = abstractTokenDocumentCounts.get(token) || ABSTRACT_TOKEN_SIGNAL_REFERENCE;
  return Math.max(
    ABSTRACT_TOKEN_SIGNAL_MIN,
    Math.min(ABSTRACT_TOKEN_SIGNAL_MAX, Math.sqrt(ABSTRACT_TOKEN_SIGNAL_REFERENCE / count))
  );
}

function weightedAbstractTokenSum(tokens) {
  let total = 0;
  for (const token of tokens || []) {
    total += abstractTokenSignal(token);
  }
  return total;
}

function specificAbstractTokens(tokens) {
  return (tokens || []).filter((token) => !ABSTRACT_LOW_SIGNAL_TOKENS.has(token));
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

function normalizeBoolean(value, fallback = false) {
  if (typeof value === "boolean") {
    return value;
  }
  const normalized = String(value || "").trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no", "off"].includes(normalized)) {
    return false;
  }
  return fallback;
}

function normalizeInteger(value, fallback) {
  const parsed = Number.parseInt(String(value || "").trim(), 10);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return parsed;
}

function trimTrailingSlashes(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function compactWhitespace(value) {
  return String(value || "").split(/\s+/).filter(Boolean).join(" ");
}

function truncateCompactText(value, limit) {
  const compact = compactWhitespace(value);
  if (!compact || compact.length <= limit) {
    return compact;
  }
  return `${compact.slice(0, Math.max(0, limit - 1)).trimEnd()}…`;
}

function clampInteger(value, minimum, maximum, fallback) {
  const parsed = Number.parseInt(String(value ?? "").trim(), 10);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(minimum, Math.min(maximum, parsed));
}

function clampFloat(value, minimum, maximum, fallback) {
  const parsed = Number.parseFloat(String(value ?? "").trim());
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(minimum, Math.min(maximum, parsed));
}

function compactSentence(value) {
  let compact = compactWhitespace(value);
  if (!compact) {
    return "";
  }
  if (compact.length > 220) {
    compact = `${compact.slice(0, 219).trimEnd()}…`;
  }
  if (!/[.!?]$/.test(compact)) {
    compact += ".";
  }
  return compact;
}

function normalizeMatchedFields(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  const matches = [];
  for (const item of value) {
    const field = String(item || "").trim().toLowerCase();
    if (LLM_PROVIDER_ALLOWED_MATCHED_FIELDS.has(field) && !matches.includes(field)) {
      matches.push(field);
    }
  }
  return matches;
}

function readStorageValue(storage, key) {
  try {
    return storage?.getItem(key) || "";
  } catch (error) {
    void error;
    return "";
  }
}

function writeStorageValue(storage, key, value) {
  try {
    if (!storage) {
      return;
    }
    const text = String(value || "");
    if (text) {
      storage.setItem(key, text);
    } else {
      storage.removeItem(key);
    }
  } catch (error) {
    void error;
  }
}

function deleteStorageValue(storage, key) {
  try {
    storage?.removeItem(key);
  } catch (error) {
    void error;
  }
}

function llmProviderEndpoint(baseUrl) {
  const trimmed = trimTrailingSlashes(baseUrl);
  if (!trimmed) {
    return "";
  }
  if (trimmed.endsWith("/v1/chat/completions") || trimmed.endsWith("/chat/completions")) {
    return trimmed;
  }
  if (trimmed.endsWith("/v1")) {
    return `${trimmed}/chat/completions`;
  }
  return `${trimmed}/v1/chat/completions`;
}

function llmAbstractEndpoint(baseUrl) {
  const trimmed = trimTrailingSlashes(baseUrl);
  if (!trimmed) {
    return "";
  }
  if (trimmed.endsWith("/v1/abstract-match")) {
    return trimmed;
  }
  if (trimmed.endsWith("/v1")) {
    return `${trimmed}/abstract-match`;
  }
  return `${trimmed}/v1/abstract-match`;
}

function readStoredLlmBrowserSettings(runtimeConfig) {
  const override = window.__JD_RUNTIME_CONFIG__ || {};
  const rememberKey = normalizeBoolean(
    override.llmBrowserDirectRememberKey,
    normalizeBoolean(readStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.rememberKey`), false)
  );
  const localApiKey = readStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.apiKey`);
  const sessionApiKey = readStorageValue(window.sessionStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.apiKey`);
  const defaultBaseUrl = trimTrailingSlashes(runtimeConfig.llmBrowserDefaultBaseUrl || "");
  const defaultModel = String(runtimeConfig.llmBrowserDefaultModel || "").trim();
  return {
    enabled: normalizeBoolean(
      override.llmBrowserDirectActive,
      normalizeBoolean(readStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.enabled`), false)
    ),
    baseUrl: trimTrailingSlashes(
      override.llmBrowserDirectBaseUrl
      || readStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.baseUrl`)
      || defaultBaseUrl
    ),
    model: String(
      override.llmBrowserDirectModel
      || readStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.model`)
      || defaultModel
    ).trim(),
    apiKey: String(override.llmBrowserDirectApiKey || (rememberKey ? localApiKey : sessionApiKey || localApiKey) || "").trim(),
    rememberKey,
  };
}

function persistLlmBrowserSettings(settings) {
  writeStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.enabled`, settings.enabled ? "true" : "false");
  writeStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.baseUrl`, trimTrailingSlashes(settings.baseUrl || ""));
  writeStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.model`, String(settings.model || "").trim());
  writeStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.rememberKey`, settings.rememberKey ? "true" : "false");
  if (settings.rememberKey) {
    writeStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.apiKey`, String(settings.apiKey || "").trim());
    deleteStorageValue(window.sessionStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.apiKey`);
  } else {
    writeStorageValue(window.sessionStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.apiKey`, String(settings.apiKey || "").trim());
    deleteStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.apiKey`);
  }
}

function clearPersistedLlmBrowserSettings() {
  deleteStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.enabled`);
  deleteStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.baseUrl`);
  deleteStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.model`);
  deleteStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.rememberKey`);
  deleteStorageValue(window.localStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.apiKey`);
  deleteStorageValue(window.sessionStorage, `${LLM_PROVIDER_STORAGE_PREFIX}.apiKey`);
}

function readRuntimeConfig(body) {
  const override = window.__JD_RUNTIME_CONFIG__ || {};
  const apiBaseUrl = trimTrailingSlashes(override.llmApiBaseUrl || body.dataset.llmApiBaseUrl || "");
  const enabled = normalizeBoolean(
    override.llmAbstractEnabled,
    normalizeBoolean(body.dataset.llmAbstractEnabled, Boolean(apiBaseUrl))
  ) && Boolean(apiBaseUrl);
  const timeoutMs = Math.max(
    1000,
    Math.min(
      60000,
      normalizeInteger(override.llmTimeoutMs, normalizeInteger(body.dataset.llmTimeoutMs, DEFAULT_LLM_TIMEOUT_MS))
    )
  );
  const llmCandidateLimit = Math.max(
    1,
    Math.min(
      LLM_RERANK_CANDIDATE_LIMIT,
      normalizeInteger(override.llmCandidateLimit, normalizeInteger(body.dataset.llmCandidateLimit, LLM_RERANK_CANDIDATE_LIMIT))
    )
  );

  return {
    llmApiBaseUrl: apiBaseUrl,
    llmAbstractEnabled: enabled,
    llmTimeoutMs: timeoutMs,
    llmCandidateLimit,
    llmBrowserDirectEnabled: normalizeBoolean(
      override.llmBrowserDirectEnabled,
      normalizeBoolean(body.dataset.llmBrowserDirectEnabled, false)
    ),
    llmBrowserDefaultBaseUrl: trimTrailingSlashes(
      override.llmBrowserDefaultBaseUrl || body.dataset.llmBrowserDefaultBaseUrl || ""
    ),
    llmBrowserDefaultModel: String(
      override.llmBrowserDefaultModel || body.dataset.llmBrowserDefaultModel || ""
    ).trim(),
  };
}

function hasCompleteLlmBrowserSettings(settings) {
  return Boolean(
    settings
    && settings.enabled
    && trimTrailingSlashes(settings.baseUrl || "")
    && String(settings.model || "").trim()
    && String(settings.apiKey || "").trim()
  );
}

function buildBrowserPromptPayload(queryText, candidates) {
  return {
    task: "Score journal submission fit for an abstract using only topical and scope evidence.",
    query_text: truncateCompactText(queryText, LLM_QUERY_CHAR_LIMIT),
    instructions: [
      "Use only title, categories, areas, and subject_area as evidence.",
      "Ignore prestige, rankings, indexing, accreditation, APC, and publisher reputation.",
      "Use lexical_score only as a tie-break when two journals appear equally aligned.",
      "Return concise one-sentence rationales.",
    ],
    candidates: candidates.map((candidate) => ({
      sourceid: String(candidate.sourceid || ""),
      title: truncateCompactText(candidate.title, LLM_TITLE_CHAR_LIMIT),
      categories: truncateCompactText(candidate.categories, LLM_CATEGORY_CHAR_LIMIT),
      areas: truncateCompactText(candidate.areas, LLM_AREA_CHAR_LIMIT),
      subject_area: truncateCompactText(candidate.subject_area, LLM_SUBJECT_AREA_CHAR_LIMIT),
      lexical_score: Number(candidate.lexical_score || 0).toFixed(4),
    })),
    response_schema: {
      results: [
        {
          sourceid: "candidate sourceid",
          llm_score: "integer 0-100",
          rationale: "one short sentence",
          matched_fields: ["title", "categories", "areas", "subject_area"],
          confidence: "float 0.0-1.0",
        },
      ],
    },
  };
}

function extractProviderMessageContent(payload) {
  const choices = Array.isArray(payload?.choices) ? payload.choices : [];
  if (!choices.length || typeof choices[0] !== "object" || !choices[0]) {
    return "";
  }
  const message = choices[0].message;
  if (!message || typeof message !== "object") {
    return "";
  }
  if (typeof message.content === "string") {
    return message.content;
  }
  if (Array.isArray(message.content)) {
    return message.content
      .map((item) => (item && typeof item === "object" && item.type === "text" ? String(item.text || "") : ""))
      .join("");
  }
  return "";
}

function normalizeBrowserProviderOutput(rawContent, candidates) {
  const candidateMap = new Map(
    candidates.map((candidate) => [
      String(candidate.sourceid || ""),
      {
        sourceid: String(candidate.sourceid || ""),
        title: String(candidate.title || ""),
        lexical_score: Number(candidate.lexical_score || 0),
        llm_score: 0,
        rationale: "",
        matched_fields: [],
        confidence: 0,
      },
    ])
  );

  let payload = null;
  try {
    payload = JSON.parse(String(rawContent || ""));
  } catch (error) {
    return Array.from(candidateMap.values());
  }

  const results = Array.isArray(payload?.results) ? payload.results : [];
  for (const item of results) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const sourceid = String(item.sourceid || "").trim();
    if (!sourceid || !candidateMap.has(sourceid)) {
      continue;
    }
    const current = candidateMap.get(sourceid);
    candidateMap.set(sourceid, {
      sourceid: current.sourceid,
      title: current.title,
      lexical_score: current.lexical_score,
      llm_score: clampInteger(item.llm_score, 0, 100, 0),
      rationale: compactSentence(item.rationale),
      matched_fields: normalizeMatchedFields(item.matched_fields),
      confidence: clampFloat(item.confidence, 0, 1, 0),
    });
  }

  return Array.from(candidateMap.values());
}

function sortProviderScoredCandidates(candidates) {
  return [...candidates].sort((left, right) => {
    if (right.llm_score !== left.llm_score) {
      return right.llm_score - left.llm_score;
    }
    if (right.lexical_score !== left.lexical_score) {
      return right.lexical_score - left.lexical_score;
    }
    const titleGap = String(left.title || "").localeCompare(String(right.title || ""), "en", { sensitivity: "base" });
    if (titleGap !== 0) {
      return titleGap;
    }
    return String(left.sourceid || "").localeCompare(String(right.sourceid || ""), "en", { sensitivity: "base" });
  });
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

function accreditationPriority(value) {
  if (value === "S1") return 6;
  if (value === "S2") return 5;
  if (value === "S3") return 4;
  if (value === "S4") return 3;
  if (value === "S5") return 2;
  if (value === "S6") return 1;
  return 0;
}

function journalMetricValue(record) {
  return Number(record.sjr_value || 0);
}

function journalHIndexValue(record) {
  return Number(record.h_index || 0);
}

function journalRankValue(record) {
  const rank = Number(record.rank);
  return Number.isFinite(rank) && rank > 0 ? rank : Number.POSITIVE_INFINITY;
}

function indexedLabelList(record) {
  const labels = [];
  if (record.scopus_indexed) labels.push("Scopus");
  if (record.wos_indexed) labels.push("WoS");
  if (record.doaj_indexed) labels.push("DOAJ");
  if (record.sinta_url || record.accreditation || record.source_type === "sinta") labels.push("SINTA");
  return labels;
}

function sourceMetaLabel(record) {
  if (record.rank) {
    return `Rank ${record.rank}`;
  }
  if (record.source_type === "sinta") {
    return "SINTA profile";
  }
  return "Journal profile";
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
  if (record.sinta_url || record.accreditation || record.source_type === "sinta") wrapper.appendChild(createBadge("SINTA", "label-sinta"));
  if (record.accreditation) wrapper.appendChild(createBadge(record.accreditation, "label-accreditation"));
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

    record.source_type = record.source_type || "scimago";
    record.scopus_indexed = Boolean(record.scopus_indexed);
    record.wos_indexed = Boolean(record.wos_indexed);
    record.doaj_indexed = Boolean(record.doaj_indexed);
    record.accreditation = accreditationPriority(record.accreditation) > 0 ? record.accreditation : null;
    record.profile_path = buildProfilePath(record);

    const labels = indexedLabelList(record);
    record.index_summary = labels.length ? labels.join(", ") : "";

    record.normalized_title = normalizeText(record.title || "");
    record.normalized_publisher = normalizeText(record.publisher || "");
    record.normalized_country = normalizeText(record.country || "");
    record.normalized_url = normalizeText(record.journal_url || "");
    record.normalized_categories = normalizeText(record.categories || "");
    record.normalized_areas = normalizeText(record.areas || "");
    record.normalized_subject_area = normalizeText(record.subject_area || "");
    record.normalized_index_summary = normalizeText(record.index_summary);
    record.normalized_issns = normalizeText((record.issns || []).join(" "));
    record.topic_text = normalizeText(`${record.categories || ""} ${record.areas || ""} ${record.subject_area || ""}`);
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
      record.normalized_subject_area,
      record.normalized_issns,
    ].filter(Boolean).join(" ");

    record.title_tokens = tokenizeSearchText(record.title || "");
    record.publisher_tokens = tokenizeSearchText(record.publisher || "");
    record.country_tokens = tokenizeSearchText(record.country || "");
    record.url_tokens = tokenizeSearchText(record.journal_url || "");
    record.category_tokens = tokenizeSearchText(record.categories || "");
    record.area_tokens = tokenizeSearchText(record.areas || "");
    record.subject_area_tokens = tokenizeSearchText(record.subject_area || "");
    record.title_phrase_tokens = extractPhraseTokens(record.title || "", { maxPhrases: ABSTRACT_RECORD_PHRASE_LIMIT });
    record.category_phrase_tokens = extractPhraseTokens(record.categories || "", { maxPhrases: ABSTRACT_RECORD_PHRASE_LIMIT });
    record.area_phrase_tokens = extractPhraseTokens(record.areas || "", { maxPhrases: ABSTRACT_RECORD_PHRASE_LIMIT });
    record.subject_area_phrase_tokens = extractPhraseTokens(record.subject_area || "", { maxPhrases: ABSTRACT_RECORD_PHRASE_LIMIT });
    record.title_concept_tokens = extractConceptTokens(record.title || "");
    record.category_concept_tokens = extractConceptTokens(record.categories || "");
    record.area_concept_tokens = extractConceptTokens(record.areas || "");
    record.subject_area_concept_tokens = extractConceptTokens(record.subject_area || "");
    record.index_tokens = tokenizeSearchText(record.index_summary);
    record.issn_tokens = tokenizeSearchText((record.issns || []).join(" "), { removeStopWords: false, applyStemming: false });
    record.abstract_title_tokens = record.title_tokens.filter((token) => !ABSTRACT_LOW_SIGNAL_TOKENS.has(token));
    record.abstract_category_specific_tokens = record.category_tokens.filter((token) => !ABSTRACT_LOW_SIGNAL_TOKENS.has(token));
    record.abstract_area_specific_tokens = record.area_tokens.filter((token) => !ABSTRACT_LOW_SIGNAL_TOKENS.has(token));
    record.abstract_subject_area_specific_tokens = record.subject_area_tokens.filter((token) => !ABSTRACT_LOW_SIGNAL_TOKENS.has(token));
    record.topic_tokens = mergeTokenLists(record.category_tokens, record.area_tokens, record.subject_area_tokens);
    record.search_tokens = mergeTokenLists(
      record.title_tokens,
      record.publisher_tokens,
      record.country_tokens,
      record.url_tokens,
      record.category_tokens,
      record.area_tokens,
      record.subject_area_tokens,
      record.index_tokens,
      record.issn_tokens
    );

    record.title_token_set = new Set(record.title_tokens);
    record.publisher_token_set = new Set(record.publisher_tokens);
    record.country_token_set = new Set(record.country_tokens);
    record.url_token_set = new Set(record.url_tokens);
    record.category_token_set = new Set(record.category_tokens);
    record.area_token_set = new Set(record.area_tokens);
    record.subject_area_token_set = new Set(record.subject_area_tokens);
    record.title_phrase_token_set = new Set(record.title_phrase_tokens);
    record.category_phrase_token_set = new Set(record.category_phrase_tokens);
    record.area_phrase_token_set = new Set(record.area_phrase_tokens);
    record.subject_area_phrase_token_set = new Set(record.subject_area_phrase_tokens);
    record.title_concept_token_set = new Set(record.title_concept_tokens);
    record.category_concept_token_set = new Set(record.category_concept_tokens);
    record.area_concept_token_set = new Set(record.area_concept_tokens);
    record.subject_area_concept_token_set = new Set(record.subject_area_concept_tokens);
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

function abstractMatchSummary(record, query) {
  if (!query.hasMeaningfulTokens) {
    return null;
  }

  const titleMatches = tokenMatches(record.title_token_set, query.tokens);
  const categoryMatches = tokenMatches(record.category_token_set, query.tokens);
  const areaMatches = tokenMatches(record.area_token_set, query.tokens);
  const subjectAreaMatches = tokenMatches(record.subject_area_token_set, query.tokens);
  const titlePhraseMatches = tokenMatches(record.title_phrase_token_set, query.phraseTokens);
  const categoryPhraseMatches = tokenMatches(record.category_phrase_token_set, query.phraseTokens);
  const areaPhraseMatches = tokenMatches(record.area_phrase_token_set, query.phraseTokens);
  const subjectAreaPhraseMatches = tokenMatches(record.subject_area_phrase_token_set, query.phraseTokens);
  const titleConceptMatches = tokenMatches(record.title_concept_token_set, query.conceptTokens);
  const categoryConceptMatches = tokenMatches(record.category_concept_token_set, query.conceptTokens);
  const areaConceptMatches = tokenMatches(record.area_concept_token_set, query.conceptTokens);
  const subjectAreaConceptMatches = tokenMatches(record.subject_area_concept_token_set, query.conceptTokens);
  const matchedTerms = mergeTokenLists(titleMatches, categoryMatches, areaMatches, subjectAreaMatches);
  const matchedPhrases = mergeTokenLists(titlePhraseMatches, categoryPhraseMatches, areaPhraseMatches, subjectAreaPhraseMatches);
  const matchedConcepts = mergeTokenLists(titleConceptMatches, categoryConceptMatches, areaConceptMatches, subjectAreaConceptMatches);
  if (!matchedTerms.length && !matchedPhrases.length && !matchedConcepts.length) {
    return null;
  }

  const specificTitleMatches = specificAbstractTokens(titleMatches);
  const specificCategoryMatches = specificAbstractTokens(categoryMatches);
  const specificAreaMatches = specificAbstractTokens(areaMatches);
  const specificSubjectAreaMatches = specificAbstractTokens(subjectAreaMatches);
  const specificTerms = mergeTokenLists(specificTitleMatches, specificCategoryMatches, specificAreaMatches, specificSubjectAreaMatches);
  const matchedFieldCount = [
    mergeTokenLists(titleMatches, titlePhraseMatches, titleConceptMatches),
    mergeTokenLists(categoryMatches, categoryPhraseMatches, categoryConceptMatches),
    mergeTokenLists(areaMatches, areaPhraseMatches, areaConceptMatches),
    mergeTokenLists(subjectAreaMatches, subjectAreaPhraseMatches, subjectAreaConceptMatches),
  ].filter((matches) => matches.length).length;

  const queryRelevantTokens = mergeTokenLists(
    specificAbstractTokens(query.tokens).filter((token) => abstractTokenDocumentCounts.has(token)),
    query.conceptTokens,
    query.phraseTokens
  );
  const queryRelevantWeight = weightedAbstractTokenSum(queryRelevantTokens);
  const journalSpecificTokens = mergeTokenLists(
    record.abstract_title_tokens,
    record.abstract_category_specific_tokens,
    record.abstract_area_specific_tokens,
    record.abstract_subject_area_specific_tokens,
    record.title_phrase_tokens,
    record.category_phrase_tokens,
    record.area_phrase_tokens,
    record.subject_area_phrase_tokens,
    record.title_concept_tokens,
    record.category_concept_tokens,
    record.area_concept_tokens,
    record.subject_area_concept_tokens
  );
  const journalSpecificWeight = weightedAbstractTokenSum(journalSpecificTokens);
  const matchedSpecificTerms = mergeTokenLists(
    specificTerms.length ? specificTerms : matchedTerms,
    matchedPhrases,
    matchedConcepts
  );
  const matchedSpecificWeight = weightedAbstractTokenSum(matchedSpecificTerms);
  const precision = journalSpecificWeight ? matchedSpecificWeight / journalSpecificWeight : 0;
  const recall = queryRelevantWeight ? matchedSpecificWeight / queryRelevantWeight : 0;
  const titleScore = Math.round(weightedAbstractTokenSum(specificTitleMatches) * ABSTRACT_TITLE_WEIGHT);
  const categoryScore = Math.round(weightedAbstractTokenSum(categoryMatches) * ABSTRACT_CATEGORY_WEIGHT);
  const areaScore = Math.round(weightedAbstractTokenSum(areaMatches) * ABSTRACT_AREA_WEIGHT);
  const subjectAreaScore = Math.round(weightedAbstractTokenSum(subjectAreaMatches) * ABSTRACT_SUBJECT_AREA_WEIGHT);
  const titlePhraseScore = Math.round(weightedAbstractTokenSum(titlePhraseMatches) * ABSTRACT_TITLE_PHRASE_WEIGHT);
  const categoryPhraseScore = Math.round(weightedAbstractTokenSum(categoryPhraseMatches) * ABSTRACT_CATEGORY_PHRASE_WEIGHT);
  const areaPhraseScore = Math.round(weightedAbstractTokenSum(areaPhraseMatches) * ABSTRACT_AREA_PHRASE_WEIGHT);
  const subjectAreaPhraseScore = Math.round(weightedAbstractTokenSum(subjectAreaPhraseMatches) * ABSTRACT_SUBJECT_AREA_PHRASE_WEIGHT);
  const titleConceptScore = Math.round(weightedAbstractTokenSum(titleConceptMatches) * ABSTRACT_TITLE_CONCEPT_WEIGHT);
  const categoryConceptScore = Math.round(weightedAbstractTokenSum(categoryConceptMatches) * ABSTRACT_CATEGORY_CONCEPT_WEIGHT);
  const areaConceptScore = Math.round(weightedAbstractTokenSum(areaConceptMatches) * ABSTRACT_AREA_CONCEPT_WEIGHT);
  const subjectAreaConceptScore = Math.round(weightedAbstractTokenSum(subjectAreaConceptMatches) * ABSTRACT_SUBJECT_AREA_CONCEPT_WEIGHT);
  const detailScore = specificTerms.length * ABSTRACT_DETAIL_BONUS;
  const phraseDetailScore = matchedPhrases.length * ABSTRACT_PHRASE_DETAIL_BONUS;
  const conceptDetailScore = matchedConcepts.length * ABSTRACT_CONCEPT_DETAIL_BONUS;
  const fieldCoverageScore = Math.max(0, matchedFieldCount - 1) * ABSTRACT_FIELD_COVERAGE_BONUS;
  const alignmentScore = Math.round((precision * 80) + (recall * 35));
  const breadthPenalty = Math.round(Math.max(0, journalSpecificWeight - matchedSpecificWeight) * 4);
  const baseScore = titleScore + categoryScore + areaScore + subjectAreaScore + titlePhraseScore + categoryPhraseScore
    + areaPhraseScore + subjectAreaPhraseScore + titleConceptScore + categoryConceptScore + areaConceptScore
    + subjectAreaConceptScore + detailScore + phraseDetailScore + conceptDetailScore + fieldCoverageScore;
  const score = Math.max(1, baseScore + alignmentScore - breadthPenalty);
  const fitPercentage = Math.max(
    0,
    Math.min(100, Math.round(((precision * 0.7) + (recall * 0.3)) * 100 + (Math.max(0, matchedFieldCount - 1) * 5)))
  );

  const fields = [];
  if (mergeTokenLists(titleMatches, titlePhraseMatches, titleConceptMatches).length) fields.push("Title");
  if (mergeTokenLists(categoryMatches, categoryPhraseMatches, categoryConceptMatches).length) fields.push("Categories");
  if (mergeTokenLists(areaMatches, areaPhraseMatches, areaConceptMatches).length) fields.push("Areas");
  if (mergeTokenLists(subjectAreaMatches, subjectAreaPhraseMatches, subjectAreaConceptMatches).length) fields.push("SINTA Subject Area");

  return {
    score,
    fitPercentage,
    terms: uniqueTokens([
      ...(specificTerms.length ? specificTerms : matchedTerms),
      ...matchedPhrases,
      ...matchedConcepts,
    ]).map((term) => displayAbstractSignal(term)).slice(0, 8),
    fields,
  };
}

function abstractScore(record, query) {
  return abstractMatchSummary(record, query)?.score || 0;
}

function allScopeScore(record, query) {
  if (!query.hasMeaningfulTokens && !query.normalized) {
    return 0;
  }

  const matchedTerms = mergeTokenLists(
    tokenMatches(record.title_token_set, query.tokens),
    tokenMatches(record.category_token_set, query.tokens),
    tokenMatches(record.area_token_set, query.tokens),
    tokenMatches(record.subject_area_token_set, query.tokens),
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
  score += tokenScore(record.subject_area_token_set, query.tokens, 16);
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

function createInsightBox(insight, fitPercentage) {
  const wrapper = document.createElement("div");
  wrapper.className = "match-insight";

  const heading = document.createElement("strong");
  heading.textContent = `Abstract fit: ${fitPercentage}%`;
  wrapper.appendChild(heading);

  const description = document.createElement("span");
  const fieldLabel = insight.fields.length ? insight.fields.join(", ") : "journal topics";
  description.textContent = `Matched terms found in ${fieldLabel}: ${insight.terms.join(", ")}.`;
  wrapper.appendChild(description);

  const guidance = document.createElement("span");
  guidance.textContent = "100% means the abstract aligns very strongly with this journal's Title, Categories, Areas, and SINTA Subject Area when available. Generic method words count less than specific topic terms. Compare this percentage within the current search only; it is not a journal quality metric.";
  wrapper.appendChild(guidance);

  return wrapper;
}

function matchedFieldLabel(field) {
  if (field === "title") return "Title";
  if (field === "categories") return "Categories";
  if (field === "areas") return "Areas";
  if (field === "subject_area") return "SINTA Subject Area";
  return field;
}

function createLlmInsightBox(summary) {
  if (!summary || (!summary.rationale && !(summary.matchedFields || []).length)) {
    return null;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "llm-insight";

  const heading = document.createElement("strong");
  heading.textContent = `LLM scope score: ${summary.llmScore}/100`;
  wrapper.appendChild(heading);

  if (summary.rationale) {
    const rationale = document.createElement("span");
    rationale.textContent = summary.rationale;
    wrapper.appendChild(rationale);
  }

  if ((summary.matchedFields || []).length) {
    const fields = document.createElement("span");
    fields.textContent = `Matched fields: ${summary.matchedFields.map(matchedFieldLabel).join(", ")}.`;
    wrapper.appendChild(fields);
  }

  if (typeof summary.confidence === "number" && Number.isFinite(summary.confidence)) {
    const confidence = document.createElement("span");
    confidence.textContent = `Model confidence: ${Math.round(summary.confidence * 100)}%.`;
    wrapper.appendChild(confidence);
  }

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

  if (record.accreditation) {
    summaryItems.push(`Accreditation: ${record.accreditation}`);
  }

  if (record.sjr_display) {
    summaryItems.push(`SJR: ${record.sjr_display}`);
  }
  if (record.h_index) {
    summaryItems.push(`H-index: ${record.h_index}`);
  }

  if (record.index_summary) {
    summaryItems.push(`Indexed in: ${record.index_summary}`);
  }

  if (record.source_type === "sinta" && record.subject_area) {
    summaryItems.push(`Subject area: ${record.subject_area}`);
  }

  wrapper.textContent = summaryItems.join(" • ");
  return wrapper;
}

function shouldShowSintaSubjectArea(record) {
  return record?.source_type === "sinta" && Boolean(record?.subject_area);
}

function normalizeSortOrder(value) {
  return value === "fit_desc" ? "fit_desc" : "default";
}

function abstractFitValue(entry) {
  return entry.abstractSummary?.fitPercentage || 0;
}

function compareMetricPriority(left, right) {
  const accreditationGap = accreditationPriority(right.record.accreditation) - accreditationPriority(left.record.accreditation);
  if (accreditationGap !== 0) return accreditationGap;

  const leftMetric = journalMetricValue(left.record);
  const rightMetric = journalMetricValue(right.record);
  if (rightMetric !== leftMetric) return rightMetric - leftMetric;

  const leftHIndex = journalHIndexValue(left.record);
  const rightHIndex = journalHIndexValue(right.record);
  if (rightHIndex !== leftHIndex) return rightHIndex - leftHIndex;

  const quartileGap = quartilePriority(right.record.sjr_best_quartile) - quartilePriority(left.record.sjr_best_quartile);
  if (quartileGap !== 0) return quartileGap;
  const leftRank = journalRankValue(left.record);
  const rightRank = journalRankValue(right.record);
  if (leftRank !== rightRank) return leftRank - rightRank;
  return left.record.title.localeCompare(right.record.title);
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
  const description = `${record.title} journal profile with indexing labels, accreditation, publisher, country, ISSN, website availability, APC status, license, SINTA metadata, and SJR best quartile.`;
  document.title = `${record.title} | Journal Discovery`;
  setMetaContent('meta[name="description"]', description);
  setMetaContent('meta[property="og:title"]', record.title);
  setMetaContent('meta[property="og:description"]', description);
}

function createAccreditationHighlight(record) {
  if (record.country !== "Indonesia" || !record.accreditation) {
    return null;
  }

  const indexLabels = indexedLabelList(record);
  if (!indexLabels.length) {
    return null;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "status-highlight";

  const heading = document.createElement("strong");
  heading.textContent = "Indonesia accreditation and indexing";
  wrapper.appendChild(heading);

  const body = document.createElement("span");
  body.textContent = `Accredited at ${record.accreditation}. Indexed in ${indexLabels.join(", ")}.`;
  wrapper.appendChild(body);

  return wrapper;
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
  copy.textContent = "This page brings together journal details, accreditation, indexing labels, and access information when available.";
  heroPanel.appendChild(copy);
  heroPanel.appendChild(createLabelRow(record));
  const highlight = createAccreditationHighlight(record);
  if (highlight) {
    heroPanel.appendChild(highlight);
  }

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
  main.appendChild(buildDetailItem("Affiliation", record.affiliation));
  main.appendChild(buildDetailItem("Country", record.country));
  main.appendChild(buildDetailItem("Region", record.region));
  main.appendChild(buildDetailItem("Indexed In", record.index_summary));
  main.appendChild(buildDetailItem("Accreditation", record.accreditation));
  main.appendChild(buildDetailItem("Best SJR Quartile", record.sjr_best_quartile));
  main.appendChild(buildDetailItem("Directory Quartile Label", record.sjr_quartile));
  main.appendChild(buildDetailItem("APC Status", record.apc_status));
  main.appendChild(buildDetailItem("License", record.license));
  main.appendChild(buildDetailItem("Author Holds Copyright", record.author_holds_copyright));
  main.appendChild(buildDetailItem("SINTA Profile", record.sinta_url, siteRoot, true));
  main.appendChild(buildDetailItem("ISSN", (record.issns || []).join(", ")));
  main.appendChild(buildDetailItem("Coverage", record.coverage));
  if (shouldShowSintaSubjectArea(record)) {
    main.appendChild(buildDetailItem("SINTA Subject Area", record.subject_area));
  }
  main.appendChild(buildDetailItem("Categories", record.categories));
  main.appendChild(buildDetailItem("Areas", record.areas));
  main.appendChild(buildDetailItem("Open Access", record.open_access));
  main.appendChild(buildDetailItem("Open Access Diamond", record.open_access_diamond));
  layout.appendChild(main);

  const side = document.createElement("aside");
  side.className = "profile-side detail-grid";
  side.appendChild(buildDetailItem("Source ID", record.sourceid));
  side.appendChild(buildDetailItem("Record Source", record.source_type === "sinta" ? "SINTA" : "Scimago"));
  side.appendChild(buildNavigationDetailItem("Search", searchUrl, "Search similar journals", `Search journals similar to ${record.title}`));
  side.appendChild(buildNavigationDetailItem("Navigation", joinRelative(siteRoot, ""), "Back to home", "Return to the search homepage"));
  side.appendChild(
    buildDetailItem(
      "Data note",
      "Website, accreditation, APC, license, and copyright details are shown when available. SINTA subject area appears only for SINTA-source journals."
    )
  );
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

function renderSearchExperience(manifest, siteRoot, pageMode, runtimeConfig) {
  const form = document.querySelector("#search-form");
  const results = document.querySelector("#search-results");
  const resultsCount = document.querySelector("#results-count");
  const resultsSummary = document.querySelector("#results-summary");
  const resultsSection = document.querySelector("#results-section");
  const rankingStatus = document.querySelector("#ranking-status");
  const topPaginationInfo = document.querySelector("#search-pagination-top-info");
  const topPaginationList = document.querySelector("#search-pagination-top-list");
  const paginationInfo = document.querySelector("#search-pagination-info");
  const paginationList = document.querySelector("#search-pagination-list");
  const queryInput = document.querySelector("#q");
  const scopeField = document.querySelector("#scope");
  const indexSelect = document.querySelector("#index-filter");
  const accreditationSelect = document.querySelector("#accreditation-filter");
  const quartileSelect = document.querySelector("#quartile-filter");
  const countrySelect = document.querySelector("#country-filter");
  const sortSelect = document.querySelector("#sort-order");
  const privacyNote = document.querySelector("#llm-privacy-note");
  const llmBrowserPanel = document.querySelector("#llm-browser-settings");
  const llmBrowserToggle = document.querySelector("#llm-browser-direct-enabled");
  const llmProviderBaseUrlInput = document.querySelector("#llm-provider-base-url");
  const llmProviderModelInput = document.querySelector("#llm-provider-model");
  const llmProviderApiKeyInput = document.querySelector("#llm-provider-api-key");
  const llmProviderRememberInput = document.querySelector("#llm-provider-remember-key");
  const llmProviderApplyButton = document.querySelector("#llm-provider-apply");
  const llmProviderClearButton = document.querySelector("#llm-provider-clear");
  const llmProviderStatus = document.querySelector("#llm-provider-status");

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
  const llmRerankCache = new Map();
  const llmPendingMap = new Map();
  let records = [];
  let page = 1;
  let preparedStateKey = "";
  let preparedEntries = [];
  let preparedRankingStatus = null;
  let activeLoadToken = 0;

  if (resultsSummary) {
    resultsSummary.textContent = `${totalProfiles} journal profiles ready`;
  }

  const initialLlmBrowserSettings = readStoredLlmBrowserSettings(runtimeConfig);

  if (privacyNote) {
    privacyNote.hidden = !(runtimeConfig.llmAbstractEnabled || runtimeConfig.llmBrowserDirectEnabled);
  }

  if (llmBrowserPanel) {
    llmBrowserPanel.hidden = !runtimeConfig.llmBrowserDirectEnabled;
    llmBrowserPanel.open = Boolean(
      runtimeConfig.llmBrowserDirectEnabled
      && (!runtimeConfig.llmAbstractEnabled || initialLlmBrowserSettings.enabled || initialLlmBrowserSettings.baseUrl || initialLlmBrowserSettings.model)
    );
  }

  if (llmBrowserToggle) {
    llmBrowserToggle.checked = Boolean(initialLlmBrowserSettings.enabled);
  }
  if (llmProviderBaseUrlInput) {
    llmProviderBaseUrlInput.value = initialLlmBrowserSettings.baseUrl;
  }
  if (llmProviderModelInput) {
    llmProviderModelInput.value = initialLlmBrowserSettings.model;
  }
  if (llmProviderApiKeyInput) {
    llmProviderApiKeyInput.value = initialLlmBrowserSettings.apiKey;
  }
  if (llmProviderRememberInput) {
    llmProviderRememberInput.checked = Boolean(initialLlmBrowserSettings.rememberKey);
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
  if (accreditationSelect) accreditationSelect.value = params.get("accreditation") || "all";
  if (quartileSelect) quartileSelect.value = params.get("quartile") || "all";
  if (countrySelect) countrySelect.value = params.get("country") || "all";
  if (sortSelect) sortSelect.value = normalizeSortOrder(params.get("sort") || "default");
  if (sortSelect?.value === "fit_desc" && currentScope() !== "abstract" && scopeField.tagName === "SELECT") {
    scopeField.value = "abstract";
  }
  page = Math.max(1, Number.parseInt(params.get("page") || "1", 10) || 1);
  updateLlmBrowserPanelStatus();

  function currentScope() {
    return scopeField.value || (pageMode === "home" ? "abstract" : "all");
  }

  function readCurrentLlmBrowserSettings() {
    return {
      enabled: Boolean(llmBrowserToggle?.checked),
      baseUrl: trimTrailingSlashes(llmProviderBaseUrlInput?.value || ""),
      model: String(llmProviderModelInput?.value || "").trim(),
      apiKey: String(llmProviderApiKeyInput?.value || "").trim(),
      rememberKey: Boolean(llmProviderRememberInput?.checked),
    };
  }

  function applyLlmBrowserStatus(message, tone = "muted") {
    if (!llmProviderStatus) {
      return;
    }
    llmProviderStatus.textContent = message;
    llmProviderStatus.dataset.tone = tone;
  }

  function updateLlmBrowserPanelStatus() {
    if (!runtimeConfig.llmBrowserDirectEnabled) {
      return;
    }
    const settings = readCurrentLlmBrowserSettings();
    if (!settings.enabled) {
      if (runtimeConfig.llmAbstractEnabled && runtimeConfig.llmApiBaseUrl) {
        applyLlmBrowserStatus("This build will use the configured LLM API unless you enable browser-side settings.", "muted");
      } else {
        applyLlmBrowserStatus("Browser-side LLM is off. Enable it and enter your provider settings to rerank abstracts.", "muted");
      }
      return;
    }
    if (!trimTrailingSlashes(settings.baseUrl || "")) {
      applyLlmBrowserStatus("Enter a provider base URL such as https://api.openai.com/v1.", "warn");
      return;
    }
    if (!String(settings.model || "").trim()) {
      applyLlmBrowserStatus("Enter the model name exposed by your provider.", "warn");
      return;
    }
    if (!String(settings.apiKey || "").trim()) {
      applyLlmBrowserStatus("Paste your own API key to enable browser-side reranking.", "warn");
      return;
    }
    applyLlmBrowserStatus("Browser-side LLM is ready. Abstracts and your API key will be sent directly to the provider from this browser.", "ready");
  }

  function currentLlmConfig() {
    const browserSettings = readCurrentLlmBrowserSettings();
    if (runtimeConfig.llmBrowserDirectEnabled && hasCompleteLlmBrowserSettings(browserSettings)) {
      return {
        mode: "browser",
        baseUrl: browserSettings.baseUrl,
        endpoint: llmProviderEndpoint(browserSettings.baseUrl),
        model: browserSettings.model,
        apiKey: browserSettings.apiKey,
        timeoutMs: runtimeConfig.llmTimeoutMs,
        candidateLimit: runtimeConfig.llmCandidateLimit,
      };
    }
    if (runtimeConfig.llmAbstractEnabled && runtimeConfig.llmApiBaseUrl) {
      return {
        mode: "api",
        baseUrl: runtimeConfig.llmApiBaseUrl,
        endpoint: llmAbstractEndpoint(runtimeConfig.llmApiBaseUrl),
        timeoutMs: runtimeConfig.llmTimeoutMs,
        candidateLimit: runtimeConfig.llmCandidateLimit,
      };
    }
    return null;
  }

  function currentStateKey(state) {
    return JSON.stringify({
      query: state.query.normalized,
      scope: state.scope,
      index: state.indexFilter,
      accreditation: state.accreditationFilter,
      quartile: state.quartileFilter,
      country: state.countryFilter,
      sort: state.sortOrder,
      llmMode: state.llmConfig?.mode || "",
      llmBaseUrl: state.llmConfig?.baseUrl || "",
      llmModel: state.llmConfig?.model || "",
      llmTimeoutMs: state.llmConfig?.timeoutMs || runtimeConfig.llmTimeoutMs,
      llmCandidateLimit: state.llmConfig?.candidateLimit || runtimeConfig.llmCandidateLimit,
      versionTag,
    });
  }

  function setRankingStatus(status) {
    if (!rankingStatus) {
      return;
    }
    if (!status) {
      rankingStatus.hidden = true;
      rankingStatus.className = "ranking-status";
      rankingStatus.replaceChildren();
      return;
    }

    rankingStatus.hidden = false;
    rankingStatus.className = `ranking-status ${status.mode === "llm" ? "ranking-status-llm" : "ranking-status-fallback"}`;
    rankingStatus.replaceChildren();

    const title = document.createElement("strong");
    title.textContent = status.label;
    rankingStatus.appendChild(title);

    if (status.detail) {
      const detail = document.createElement("span");
      detail.textContent = status.detail;
      rankingStatus.appendChild(detail);
    }
  }

  function clearPreparedSearchCache() {
    preparedStateKey = "";
    preparedEntries = [];
    preparedRankingStatus = null;
    llmRerankCache.clear();
    llmPendingMap.clear();
  }

  function alignSortWithScope(scope) {
    if (!sortSelect) {
      return "default";
    }

    let sortOrder = normalizeSortOrder(sortSelect.value || "default");
    if (sortOrder === "fit_desc" && scope !== "abstract") {
      sortOrder = "default";
      sortSelect.value = sortOrder;
    }

    sortSelect.title = scope === "abstract" ? "" : "Highest abstract fit applies only to abstract scope.";
    return sortOrder;
  }

  function currentState() {
    const scope = currentScope();
    const query = buildProcessedQuery(queryInput.value, scope);
    const indexFilter = indexSelect?.value || "all";
    const accreditationFilter = accreditationSelect?.value || "all";
    const quartileFilter = quartileSelect?.value || "all";
    const countryFilter = countrySelect?.value || "all";
    const sortOrder = alignSortWithScope(scope);
    const hasFilters = indexFilter !== "all" || accreditationFilter !== "all" || quartileFilter !== "all" || countryFilter !== "all";
    const llmConfig = currentLlmConfig();

    return {
      scope,
      query,
      indexFilter,
      accreditationFilter,
      quartileFilter,
      countryFilter,
      sortOrder,
      llmConfig,
      hasFilters,
      shouldLoad: hasFilters || query.shouldLoad,
      shouldShowPrompt: !hasFilters && !query.hasRawQuery,
      shouldShowNlpHelp: !hasFilters && query.hasRawQuery && !query.shouldLoad,
    };
  }

  function lexicalFallbackStatus(detail) {
    return {
      mode: "fallback",
      label: "Lexical fallback",
      detail,
    };
  }

  function defaultRankingStatus(state) {
    if (state.scope !== "abstract" || !state.query.hasRawQuery) {
      return null;
    }
    if (state.sortOrder === "fit_desc") {
      return lexicalFallbackStatus("Highest abstract fit keeps ranking local and deterministic.");
    }
    if (!state.llmConfig) {
      if (runtimeConfig.llmBrowserDirectEnabled) {
        return lexicalFallbackStatus("Configure browser-side LLM settings or use the local scorer.");
      }
      return lexicalFallbackStatus("LLM API is not configured for this build.");
    }
    if (state.query.rawLength < LLM_ABSTRACT_MIN_CHARS || state.query.meaningfulTokenCount < LLM_ABSTRACT_MIN_MEANINGFUL_TOKENS) {
      return lexicalFallbackStatus(`Abstracts shorter than ${LLM_ABSTRACT_MIN_CHARS} characters or below ${LLM_ABSTRACT_MIN_MEANINGFUL_TOKENS} meaningful tokens use the local scorer.`);
    }
    if (state.llmConfig.mode === "browser") {
      return lexicalFallbackStatus("The local scorer is active while your browser-side LLM shortlist is prepared.");
    }
    return lexicalFallbackStatus("The local scorer is active while the shortlist is prepared.");
  }

  function shouldUseLlmAbstractRanking(state) {
    return (
      state.scope === "abstract"
      && state.sortOrder === "default"
      && state.query.shouldLoad
      && state.query.hasRawQuery
      && Boolean(state.llmConfig)
      && state.query.rawLength >= LLM_ABSTRACT_MIN_CHARS
      && state.query.meaningfulTokenCount >= LLM_ABSTRACT_MIN_MEANINGFUL_TOKENS
    );
  }

  function llmErrorDetail(error, llmConfig, fallbackReason = "The LLM API could not be reached.") {
    if (error?.name === "AbortError") {
      return "The LLM API timed out, so the local scorer was used.";
    }
    if (llmConfig?.mode === "browser" && error?.name === "TypeError") {
      return "The browser could not reach the provider. Check the base URL, API key, and provider CORS policy.";
    }
    const message = String(error?.message || fallbackReason).trim();
    if (!message) {
      return fallbackReason;
    }
    return message;
  }

  async function requestApiAbstractRerank(llmConfig, state, topEntries, controller) {
    const payload = {
      query_text: state.query.trimmedRaw,
      top_n: topEntries.length,
      candidates: topEntries.map((entry) => ({
        sourceid: entry.record.sourceid,
        title: entry.record.title,
        categories: entry.record.categories,
        areas: entry.record.areas,
        subject_area: entry.record.subject_area,
        publisher: entry.record.publisher,
        country: entry.record.country,
        lexical_score: entry.score,
      })),
    };

    const response = await fetch(llmConfig.endpoint, {
      method: "POST",
      credentials: "omit",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = `The LLM API returned status ${response.status}.`;
      try {
        const errorPayload = await response.json();
        if (errorPayload?.detail) {
          detail = String(errorPayload.detail);
        }
      } catch (error) {
        void error;
      }
      throw new Error(detail);
    }

    return response.json();
  }

  async function requestBrowserDirectRerank(llmConfig, state, topEntries, controller) {
    const promptPayload = buildBrowserPromptPayload(
      state.query.trimmedRaw,
      topEntries.map((entry) => ({
        sourceid: entry.record.sourceid,
        title: entry.record.title,
        categories: entry.record.categories,
        areas: entry.record.areas,
        subject_area: entry.record.subject_area,
        lexical_score: entry.score,
      }))
    );

    const response = await fetch(llmConfig.endpoint, {
      method: "POST",
      credentials: "omit",
      headers: {
        "Authorization": `Bearer ${llmConfig.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: llmConfig.model,
        temperature: 0,
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: "You score manuscript abstract fit to journal scope. Return JSON only with a top-level 'results' array keyed by sourceid.",
          },
          {
            role: "user",
            content: JSON.stringify(promptPayload),
          },
        ],
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = `The provider returned status ${response.status}.`;
      try {
        const errorPayload = await response.json();
        const providerMessage = errorPayload?.error?.message || errorPayload?.detail;
        if (providerMessage) {
          detail = String(providerMessage);
        }
      } catch (error) {
        void error;
      }
      throw new Error(detail);
    }

    const providerPayload = await response.json();
    const normalized = normalizeBrowserProviderOutput(
      extractProviderMessageContent(providerPayload),
      topEntries.map((entry) => ({
        sourceid: entry.record.sourceid,
        title: entry.record.title,
        lexical_score: entry.score,
      }))
    );
    const ranked = sortProviderScoredCandidates(normalized).map((item, index) => ({
      sourceid: item.sourceid,
      rank: index + 1,
      llm_score: item.llm_score,
      rationale: item.rationale,
      matched_fields: item.matched_fields,
      confidence: item.confidence,
    }));
    return {
      model: llmConfig.model,
      ranked,
    };
  }

  async function rerankAbstractEntries(state, lexicalEntries) {
    const stateKey = currentStateKey(state);
    if (llmRerankCache.has(stateKey)) {
      return llmRerankCache.get(stateKey);
    }
    if (llmPendingMap.has(stateKey)) {
      return llmPendingMap.get(stateKey);
    }

    const topEntries = lexicalEntries.slice(0, Math.min(state.llmConfig?.candidateLimit || runtimeConfig.llmCandidateLimit, lexicalEntries.length));

    const pending = (async () => {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), state.llmConfig?.timeoutMs || runtimeConfig.llmTimeoutMs);
      try {
        const responsePayload = state.llmConfig?.mode === "browser"
          ? await requestBrowserDirectRerank(state.llmConfig, state, topEntries, controller)
          : await requestApiAbstractRerank(state.llmConfig, state, topEntries, controller);
        const ranked = Array.isArray(responsePayload?.ranked) ? responsePayload.ranked : [];
        const rankedMap = new Map();
        for (const item of ranked) {
          const sourceid = String(item?.sourceid || "");
          if (!sourceid || rankedMap.has(sourceid)) {
            continue;
          }
          const rank = Number.parseInt(String(item.rank || ""), 10);
          const llmScore = Math.max(0, Math.min(100, Number.parseInt(String(item.llm_score || 0), 10) || 0));
          const rationale = String(item.rationale || "").trim();
          const matchedFields = Array.isArray(item.matched_fields)
            ? item.matched_fields.map((field) => String(field || "").trim()).filter(Boolean)
            : [];
          const confidence = Math.max(0, Math.min(1, Number(item.confidence || 0)));
          rankedMap.set(sourceid, {
            rank: Number.isFinite(rank) && rank > 0 ? rank : Number.POSITIVE_INFINITY,
            llmScore,
            rationale,
            matchedFields,
            confidence,
          });
        }

        const rerankedTop = topEntries.map((entry) => {
          const summary = rankedMap.get(String(entry.record.sourceid || ""));
          return {
            ...entry,
            llmSummary: summary || null,
            llmRank: summary?.rank ?? Number.POSITIVE_INFINITY,
            llmScoreValue: summary?.llmScore ?? 0,
          };
        });

        rerankedTop.sort((left, right) => {
          if (left.llmRank !== right.llmRank) {
            return left.llmRank - right.llmRank;
          }
          if (right.llmScoreValue !== left.llmScoreValue) {
            return right.llmScoreValue - left.llmScoreValue;
          }
          if (right.score !== left.score) {
            return right.score - left.score;
          }
          return compareMetricPriority(left, right);
        });

        const mergedEntries = [
          ...rerankedTop,
          ...lexicalEntries.slice(topEntries.length).map((entry) => ({ ...entry, llmSummary: null })),
        ];
        const modelName = String(responsePayload?.model || "").trim();
        return {
          entries: mergedEntries,
          rankingStatus: {
            mode: "llm",
            label: "LLM-assisted ranking",
            detail: `${topEntries.length} shortlisted journals reranked${modelName ? ` via ${modelName}` : ""}.`,
          },
        };
      } catch (error) {
        return {
          entries: lexicalEntries,
          rankingStatus: lexicalFallbackStatus(llmErrorDetail(error, state.llmConfig)),
        };
      } finally {
        window.clearTimeout(timeoutId);
      }
    })();

    llmPendingMap.set(stateKey, pending);
    try {
      const result = await pending;
      llmRerankCache.set(stateKey, result);
      return result;
    } finally {
      llmPendingMap.delete(stateKey);
    }
  }

  async function prepareEntries(state, loadToken) {
    const stateKey = currentStateKey(state);
    if (preparedStateKey === stateKey) {
      return {
        entries: preparedEntries,
        rankingStatus: preparedRankingStatus,
      };
    }

    const lexicalEntries = applyFilters(state);
    let prepared = {
      entries: lexicalEntries,
      rankingStatus: defaultRankingStatus(state),
    };

    if (shouldUseLlmAbstractRanking(state) && lexicalEntries.length) {
      prepared = await rerankAbstractEntries(state, lexicalEntries);
    }

    if (loadToken !== activeLoadToken) {
      return prepared;
    }

    preparedStateKey = stateKey;
    preparedEntries = prepared.entries;
    preparedRankingStatus = prepared.rankingStatus;
    return prepared;
  }

  function getPreferredChunkPaths(state) {
    if (state.scope === "title" && state.query.normalized) {
      return titlePrefixChunks[searchPrefix(state.query.normalized)] || chunkPaths;
    }
    return chunkPaths;
  }

  function mergeLoadedRecords() {
    records = Array.from(loadedChunkMap.values()).flat();
    buildAbstractTokenSignals(records);
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
    clearPreparedSearchCache();
    setResultsSectionVisible(false);
    setRankingStatus(null);
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
    clearPreparedSearchCache();
    setResultsSectionVisible(true);
    setRankingStatus(null);
    resultsCount.textContent = `Add more specific terms to search ${totalProfiles} journal profiles.`;
    renderEmptyResults(
      "Enter more specific search terms",
      "The current query only contains stop words or very short tokens. Add topic-specific words before searching again."
    );
  }

  function renderLoadingState() {
    setResultsSectionVisible(true);
    setRankingStatus(null);
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
      if (state.accreditationFilter !== "all" && record.accreditation !== state.accreditationFilter) continue;
      if (state.quartileFilter !== "all" && record.sjr_best_quartile !== state.quartileFilter) continue;
      if (state.countryFilter !== "all" && record.country !== state.countryFilter) continue;

      const abstractSummary = useQuery && state.scope === "abstract"
        ? abstractMatchSummary(record, state.query)
        : null;
      const score = useQuery
        ? (state.scope === "abstract" ? abstractSummary?.score || 0 : scoreRecord(record, state.query, state.scope))
        : 1;
      if (!useQuery || score > 0) {
        matched.push({ score, record, abstractSummary });
      }
    }

    matched.sort((left, right) => {
      if (useQuery && state.scope === "abstract") {
        if (state.sortOrder === "fit_desc") {
          const fitGap = abstractFitValue(right) - abstractFitValue(left);
          if (fitGap !== 0) return fitGap;
        }
      }

      if (useQuery && right.score !== left.score) {
        return right.score - left.score;
      }

      return compareMetricPriority(left, right);
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
    if (rawQuery && state.scope === "abstract" && state.sortOrder !== "default") {
      nextParams.set("sort", state.sortOrder);
    }
    if (pageMode === "search") {
      if (state.indexFilter !== "all") nextParams.set("index", state.indexFilter);
      if (state.accreditationFilter !== "all") nextParams.set("accreditation", state.accreditationFilter);
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
    const stateKey = currentStateKey(state);
    const filtered = preparedStateKey === stateKey ? preparedEntries : applyFilters(state);
    const status = preparedStateKey === stateKey ? preparedRankingStatus : defaultRankingStatus(state);
    const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
    if (page > totalPages) {
      page = totalPages;
    }
    const start = (page - 1) * perPage;
    const pageItems = filtered.slice(start, start + perPage);

    results.replaceChildren();
    setRankingStatus(status);
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
      const { record, abstractSummary } = entry;
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
      meta.textContent = sourceMetaLabel(record);
      article.appendChild(meta);

      article.appendChild(createResultSummary(record));

      const layout = document.createElement("div");
      layout.className = "profile-layout";

      const main = document.createElement("div");
      main.className = "profile-main detail-grid";
      main.appendChild(buildDetailItem("Website", record.journal_url, siteRoot, true));
      main.appendChild(buildDetailItem("Affiliation", record.affiliation));
      if (shouldShowSintaSubjectArea(record)) {
        main.appendChild(buildDetailItem("SINTA Subject Area", record.subject_area));
      }
      main.appendChild(buildDetailItem("Categories", record.categories));
      main.appendChild(buildDetailItem("Areas", record.areas));
      main.appendChild(buildDetailItem("APC Status", record.apc_status));
      main.appendChild(buildDetailItem("License", record.license));
      layout.appendChild(main);

      const side = document.createElement("aside");
      side.className = "profile-side detail-grid";
      side.appendChild(buildDetailItem("Accreditation", record.accreditation));
      side.appendChild(buildDetailItem("Best SJR Quartile", record.sjr_best_quartile));
      side.appendChild(buildDetailItem("Author Holds Copyright", record.author_holds_copyright));
      side.appendChild(buildDetailItem("ISSN", (record.issns || []).join(", ")));
      if (record.sinta_url) {
        side.appendChild(buildDetailItem("SINTA Profile", record.sinta_url, siteRoot, true));
      }
      if (state.scope === "abstract" && abstractSummary) {
        side.appendChild(createInsightBox(abstractSummary, abstractSummary.fitPercentage));
      }
      if (state.scope === "abstract" && entry.llmSummary) {
        const llmInsight = createLlmInsightBox(entry.llmSummary);
        if (llmInsight) {
          side.appendChild(llmInsight);
        }
      }
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
    activeLoadToken += 1;
    const loadToken = activeLoadToken;
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
    await prepareEntries(state, loadToken);
    if (loadToken !== activeLoadToken) {
      return;
    }
    syncUrl(state);
    renderPage(state, shouldScroll);
  }

  function refreshCurrentSearchAfterLlmSettingsChange() {
    clearPreparedSearchCache();
    updateLlmBrowserPanelStatus();
    const state = currentState();
    if (state.scope === "abstract" && state.query.hasRawQuery && state.shouldLoad) {
      page = 1;
      loadAndRenderPage().catch((error) => {
        throw error;
      });
      return;
    }
    setRankingStatus(defaultRankingStatus(state));
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    page = 1;
    loadAndRenderPage().catch((error) => {
      throw error;
    });
  });

  for (const element of [scopeField, indexSelect, accreditationSelect, quartileSelect, countrySelect].filter(Boolean)) {
    element.addEventListener("change", () => {
      if (element === scopeField && sortSelect && currentScope() !== "abstract") {
        sortSelect.value = "default";
      }
      page = 1;
      loadAndRenderPage().catch((error) => {
        throw error;
      });
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener("change", () => {
      if (sortSelect.value === "fit_desc" && currentScope() !== "abstract" && scopeField.tagName === "SELECT") {
        scopeField.value = "abstract";
      }
      page = 1;
      loadAndRenderPage().catch((error) => {
        throw error;
      });
    });
  }

  for (const element of [llmBrowserToggle, llmProviderBaseUrlInput, llmProviderModelInput, llmProviderApiKeyInput, llmProviderRememberInput].filter(Boolean)) {
    element.addEventListener("input", () => {
      updateLlmBrowserPanelStatus();
    });
    element.addEventListener("change", () => {
      updateLlmBrowserPanelStatus();
    });
  }

  if (llmProviderApplyButton) {
    llmProviderApplyButton.addEventListener("click", () => {
      persistLlmBrowserSettings(readCurrentLlmBrowserSettings());
      refreshCurrentSearchAfterLlmSettingsChange();
    });
  }

  if (llmProviderClearButton) {
    llmProviderClearButton.addEventListener("click", () => {
      clearPersistedLlmBrowserSettings();
      const cleared = {
        enabled: false,
        baseUrl: runtimeConfig.llmBrowserDefaultBaseUrl || "",
        model: runtimeConfig.llmBrowserDefaultModel || "",
        apiKey: "",
        rememberKey: false,
      };
      if (llmBrowserToggle) llmBrowserToggle.checked = false;
      if (llmProviderBaseUrlInput) llmProviderBaseUrlInput.value = cleared.baseUrl;
      if (llmProviderModelInput) llmProviderModelInput.value = cleared.model;
      if (llmProviderApiKeyInput) llmProviderApiKeyInput.value = "";
      if (llmProviderRememberInput) llmProviderRememberInput.checked = false;
      refreshCurrentSearchAfterLlmSettingsChange();
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
  const runtimeConfig = readRuntimeConfig(body);
  if (!page || !dataUrl) {
    return;
  }

  const response = await fetch(dataUrl, { credentials: "same-origin" });
  if (!response.ok) {
    throw new Error(`Failed to load journal data: ${response.status}`);
  }
  const payload = await response.json();

  if (page === "home" || page === "search") {
    renderSearchExperience(payload, siteRoot, page, runtimeConfig);
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
