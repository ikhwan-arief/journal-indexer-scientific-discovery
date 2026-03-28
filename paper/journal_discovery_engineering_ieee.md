# Field-Aware Abstract-to-Journal Recommendation Under Sparse Metadata: An Interpretable Static Retrieval Approach

## Abstract

Selecting a target journal from an article abstract is an operationally important but infrastructure-sensitive task. Many journal recommendation approaches assume rich article corpora, backend inference, or journal metadata that are not consistently available in lightweight public deployments. This study asks a narrower engineering question: can a static client-side artifact still provide useful and interpretable abstract-to-journal ranking when journal metadata are restricted to title, categories, and subject areas? We present *Journal Discovery*, a browser-executed artifact built from a 29,553-journal snapshot enriched with Web of Science and DOAJ signals. The ranking pipeline combines conservative normalization, weighted lexical overlap, phrase-aware matching, acronym and concept expansion, alignment scoring, and a breadth-aware penalty. An `abstract fit` percentage is exposed as an explanatory signal rather than the primary ranking objective. Validation was performed in two complementary settings and strengthened with fair lexical baselines over the same sparse fields. On a nine-case exact-source benchmark derived from SME and Industry 4.0 abstracts, the default artifact ranking achieved Recall@30 of 0.333 and MRR of 0.121, outperforming `BM25F` on MRR (0.059) and `TF-IDF` cosine (0.012). On a six-case cross-domain DOAJ relevance benchmark, the artifact achieved Relevant Hit@10 of 1.000, Relevant MRR of 0.667, and nDCG@10 of 0.797, while `BM25F` was slightly stronger on cross-domain relevance. The results support a bounded claim: under sparse journal metadata, static journal discovery can provide useful relevance-oriented support, but manually judged evidence is still required for stronger accuracy claims.

**Keywords:** journal recommendation, sparse metadata, information retrieval, decision support, engineering informatics

## 1. Introduction

Choosing a target journal is a recurring engineering decision problem inside the research workflow. It affects publication latency, review fit, revision burden, desk-rejection risk, and the eventual audience that encounters a piece of work. In practice, authors do not decide only between "good" and "bad" journals. They decide under bounded time, imperfect information, heterogeneous indexing systems, and highly uneven metadata quality. A long abstract may describe a method, domain, dataset, and contribution in detail, yet the public journal-side evidence that authors can search quickly is often limited to a short title and a small set of topical labels. That asymmetry is operationally inconvenient for authors, but it is also an engineering problem because it constrains what a deployable recommendation system can realistically compute from public data [1], [2].

The problem is more pressing than a generic inconvenience in literature search. A journal-targeting aid sits at the intersection of discovery, venue selection, and decision support. For publicly hosted scholarly tools, those requirements are constrained by inspectability, infrastructure cost, and data-access limits. Many users do not have stable access to commercial APIs, proprietary corpora, or long-running inference services, so a broadly deployable system has to be designed under resource and transparency constraints from the outset [2], [8].

For researchers, the most immediate benefit of such a tool is practical: it can shorten the first screening stage when authors are trying to identify plausible target journals for submission, especially from an abstract that already summarizes the paper's contribution, method, and domain. A useful recommender can also reduce the chance of sending a manuscript toward journals whose scope is visibly misaligned, surface candidate venues outside the author's habitual reading list, and support early-career or interdisciplinary researchers who may not yet have strong tacit knowledge of journal landscapes. In that sense, the value of the artifact is not limited to ranking quality alone; it also lies in reducing search friction and supporting better publication decisions earlier in the workflow.

There are broader benefits as well. A transparent public journal-discovery tool can be used by supervisors, librarians, research offices, and manuscript-development workshops as a scoped advisory aid rather than as an opaque black box. Because the current artifact ranks abstracts entirely in the browser after the static assets are loaded, it also offers a privacy-relevant advantage for unpublished work: users do not need to send their abstract text to a remote inference service simply to obtain an initial shortlist of candidate venues. These usability, training, and governance benefits strengthen the engineering case for studying lightweight journal recommendation even when its predictive ceiling remains below that of richer server-side systems.

The journal recommendation literature already shows that the task is non-trivial. A recent survey on scholarly recommendation systems frames journal routing as one part of a wider class of academic recommendation problems involving literature, collaborators, venues, and related scholarly objects [1]. Within that landscape, journal recommendation methods have evolved along several lines. One line uses semantic similarity over article metadata or abstracts, often through sentence-transformer or embedding-based matching [3]. Another line combines content evidence with contextual signals such as author profiles, publication trends, or user history [4]. A third line emphasizes transparent web-facing services that expose practical recommendation functionality over open infrastructures, as illustrated by B!SON [5]. More recent content-based models also explore combinations of pretrained transformers and graph neural networks for journal recommendation and academic article classification [21]. These studies demonstrate that recommendation quality can improve when systems exploit richer textual evidence, larger training sets, or more expressive representation learning.

However, those advances do not remove an important translation gap. Much of the literature assumes journal-side or article-side data conditions that are not always available in public, lightweight deployments. Transformer-based recommenders generally rely on substantial training corpora, external embeddings, or richer journal representations than a title and a few subject labels [3], [21]. Hybrid recommenders can benefit from author-profile data, behavioral traces, or citation relations that are unavailable in privacy-sensitive or first-use scenarios [4]. Even open tools such as B!SON are built in contexts where additional scholarly infrastructure, article metadata, or service-side logic can be used [5]. Those approaches are scientifically valuable, but they do not directly answer the question faced by a constrained static deployment: what ranking behavior is still achievable when the only reliable journal-side text consists of `Title`, `Categories`, and `Areas`?

That question matters because the sparse-metadata condition is common. Public journal rankings and directories often expose a title, country, publisher, broad subject labels, quartile indicators, and possibly a website, but not a clean journal-level "aims and scope" text that is consistent across sources. Metadata incompleteness is not a minor nuisance in this setting. Prior work on metadata infrastructure has shown that the structure and availability of metadata materially influence what users can discover, audit, and reuse [7]. Recent work on transparent research evaluation built from public NIH metadata reinforces the same point from another angle: when public metadata are the core artifact substrate, the system's analytical and evaluative scope is bounded by what those public fields can support [8]. In academic research more broadly, online databases and information communication systems influence retrieval efficiency and research productivity, but they also reveal how much scholarly work depends on the quality and accessibility of exposed information structures [22]. For a journal recommender, this means that sparse metadata are not merely an implementation inconvenience; they define the problem formulation itself.

The sparse-metadata condition creates a specific information-retrieval challenge. The query may be long and informative, especially when the user pastes a full abstract. The candidate journal representation, in contrast, may contain only a handful of short topical phrases. This is a form of long-to-short matching in which the richer document is the query and the thinner document is the indexed item. The difficulty is not only vocabulary mismatch. It is also the unequal density of signal: a long abstract contains many generic words about method, contribution, and context, whereas a short journal profile may expose only a few discriminative cues. If the ranking method overweights broad tokens such as `system`, `study`, `analysis`, `public`, or `management`, generalist journals can dominate. If it overreacts to small local overlaps, very narrow but poorly aligned venues can rise for the wrong reason. Sparse matching therefore requires a disciplined balance between recall and specificity [9], [10].

Research in multi-field ranking and short-text analysis provides useful guidance here. Multi-document-field neural ranking studies show that different textual fields should not be treated uniformly because they contribute different kinds of relevance evidence [9]. A journal title is concise and often broad; category and subject-area labels can carry more stable scope cues, even if they are taxonomic rather than descriptive. Document-aware retrieval benchmarks further show that missing context remains a major cause of retrieval error, especially when the query and indexed documents expose different slices of the underlying topic [10]. Short-text classification and clustering studies likewise report instability under weak lexical evidence, vocabulary mismatch, and limited context [11], [12], [13]. For an author-facing journal recommender, this means the ranking logic must protect small amounts of high-value topical evidence instead of letting long abstracts win on generic language volume alone.

Interpretability is equally central. In journal selection, a recommendation is not automatically accepted because it is ranked first. Users typically inspect several results, compare them with their own disciplinary intuition, and ask whether the system surfaced the venue for a defensible reason. Explainable recommender research consistently argues that recommendation quality involves both ranking and justification [14], [15]. This is especially important in high-consequence scholarly decisions, where an opaque rank alone does not help the user determine whether the venue matches the paper's scope, audience, or methodological emphasis. A practical journal recommender therefore needs a readable local signal that users can inspect without mistaking that signal for the whole ranking objective.

There is also a systems-level reason to preserve transparency. Journal recommender systems can be manipulated if the ranking logic is opaque or overly sensitive to superficial evidence [6]. A bounded, inspectable set of matching components is therefore useful not only for explanation but also for auditing, a point reinforced by work on trustworthy and explainable recommendation [15], [19].

The engineering significance of this problem extends beyond journal targeting itself. Scholarly workflows include related routing problems such as reviewer assignment, manuscript triage, and evidence retrieval. Reviewer-assignment research highlights the same recurring bottlenecks of open data scarcity and fragmented scholarly sources [22], while self-hostable tools such as Valsci show the value of deployable and inspectable research-facing artifacts [18]. These adjacent tasks do not solve journal recommendation directly, but they reinforce the relevance of lightweight scholarly decision-support systems.

This manuscript addresses that translation gap by asking a deliberately bounded question. Instead of competing with rich semantic systems on their own assumptions, it evaluates whether a static browser-executed artifact can still produce useful abstract-to-journal ranking when journal-side evidence is intentionally sparse. The artifact studied here, *Journal Discovery*, uses only public journal-side `Title`, `Categories`, and `Areas` fields at ranking time. Its abstract recommender combines weighted lexical overlap, phrase-aware matching, conservative concept expansion, an alignment term that balances matched specificity and coverage, and a breadth-aware penalty that suppresses journals whose exposed scope is much broader than the matched evidence.

The paper does not claim universal journal prediction, semantic understanding comparable to large neural recommenders, or robustness beyond the available evidence. Instead, it makes four narrower and defensible contributions. First, it formalizes a sparse-metadata ranking design intended for static client-side deployment. Second, it separates global ranking from a local explanatory signal by treating `abstract fit` as interpretable output rather than the primary objective. Third, it evaluates the artifact under two complementary validation settings: a strict exact-source benchmark and a broader relevance-oriented benchmark. Fourth, it adds fair `BM25F` and `TF-IDF` baselines over the same sparse fields, together with a prepared manual relevance package, to strengthen the evidentiary basis of the claims.

The central research questions are therefore:

1. Can a static client-side journal discovery artifact provide useful abstract-to-journal relevance ranking when journal metadata are restricted to title, categories, and areas?
2. Does a ranking design that combines lexical, phrase, concept, alignment, and breadth-aware components outperform a sort strategy that prioritizes only local `abstract fit` percentage?
3. How does the current artifact compare with fair lightweight lexical baselines under the same sparse-metadata constraint?
4. What do the current validation results imply about the boundary between useful relevance ranking and exact source-journal retrieval?

These questions are important because a negative answer would imply that meaningful journal recommendation is not realistically achievable without richer metadata or heavier service-side infrastructure. A positive but bounded answer would be equally informative: it would show that practical relevance-oriented support is still possible under strict public-data and deployment constraints, but that the objective must be framed carefully. The rest of the paper follows that bounded framing. Section 2 describes the artifact, ranking formulation, dataset construction, and evaluation design. Section 3 reports current runtime characteristics and benchmark outcomes, including the new `BM25F` and `TF-IDF` comparators. Section 4 interprets the mechanisms behind the observed results, discusses failure modes, and clarifies the present limits of the evidence. Section 5 concludes with the study's engineering implications and the next steps required for stronger claims.

## 2. Methodology

### 2.1. Study design and engineering stance

The study is best understood as an engineering informatics artifact evaluation rather than a purely algorithmic benchmark paper. The artifact already exists as a deployable static website. The research task is therefore not to invent a hypothetical model in isolation, but to formalize, instrument, and evaluate the ranking logic that the deployable artifact actually uses. This distinction matters methodologically. Many recommendation studies report offline models divorced from the practical environment in which users interact with results. Here, the deployment setting is one of the core scientific constraints: browser execution, public hosting, limited runtime payload, inspectable logic, and dependence on public journal metadata.

The overall study design consists of five stages. First, public journal datasets are assembled and aligned into a common profile structure. Second, those profiles are transformed during the build step into static JSON resources optimized for browser retrieval. Third, the runtime scorer executes entirely client-side using only locally loaded shards and profile fields. Fourth, the deployed ranking behavior is evaluated end to end on two benchmark settings that capture different success criteria. Fifth, fair lexical baselines and a manual relevance package are used to contextualize current performance and expose what the present evidence can and cannot support.

The engineering stance of the study is intentionally conservative. The artifact does not use pretrained embeddings, third-party retrieval APIs, user histories, citation networks, or server-side inference. Those design choices are not treated as missing features to apologize for; they are deliberate constraints imposed by the target deployment class. This makes the study narrower than many recommender-system papers, but it also makes the conclusions more operationally meaningful for users who need lightweight, inspectable scholarly tooling.

### 2.2. Dataset construction and artifact build

The current artifact is built from three public data streams. The first is a Scimago Journal Rank snapshot that provides journal titles, quartile indicators, broad subject classification, country, and related bibliometric attributes. The second is a Web of Science subset aligned to the same snapshot. This subset provides a binary enrichment indicating whether the journal appears in the aligned Web of Science data. The third is an optional DOAJ enrichment file that contributes public website, APC, license, and copyright information when available. These sources are combined during the Python build phase into a single journal profile structure used by the static website.

At the time of the present manuscript, the generated dataset contains 29,553 journals. All 29,553 are part of the Scopus-oriented parent snapshot used by the artifact. Of these, 17,799 are marked as Web of Science indexed and 8,544 carry DOAJ enrichment. Quartile information is available for all profiles in the current snapshot. The homepage and search interface additionally expose publisher, country, and indexing flags where present, but the abstract recommender itself deliberately restricts topical scoring to the three journal-side textual fields `Title`, `Categories`, and `Areas`.

The build pipeline is designed for public static hosting. Instead of producing one large monolithic search file, it emits several small public assets and a sharded search corpus. The homepage shell uses a 341 B summary file and a 3.9 KB manifest. Profile lookup relies on a 1.44 MB index. Search data are partitioned into 15 JSON shards totaling 20.55 MB. Title-scoped searching is further narrowed through 30 title-prefix buckets so that title search does not require loading the same data path used by broader abstract or metadata search. This structure supports low-friction deployment on GitHub Pages and similar static hosts without requiring a database, application server, or authenticated runtime API.

From an engineering standpoint, the data layout itself is part of the method rather than an implementation footnote. A journal recommender that claims to be lightweight must expose evidence that its deployment profile is genuinely bounded. The current artifact satisfies that requirement in three ways. First, all search and ranking logic runs in the browser after build time. Second, search payload is loaded on demand rather than preloaded wholesale. Third, the same data structure supports both human-facing exploration and automated benchmark execution, which reduces the distance between the evaluated artifact and the deployed one.

Table 1 summarizes the current dataset and search-profile snapshot used in the manuscript.

| Item | Value |
| --- | ---: |
| Total journals | 29,553 |
| Scopus journals | 29,553 |
| Web of Science journals | 17,799 |
| DOAJ-enriched journals | 8,544 |
| Journals with quartile information | 29,553 |
| Journals without public website in current snapshot | 21,009 |
| Countries represented in manifest | 120 |
| Search shard files | 15 |
| Total search-shard payload | 20.55 MB |
| Mean shard size | 1.37 MB |
| Max shard size | 1.46 MB |
| Manifest title-prefix buckets | 30 |

**[Figure 1 placeholder]**
**Caption:** Static client-side journal discovery pipeline from public journal snapshots to on-demand browser ranking.
**Nano Banana prompt:** Create a clean systems diagram on a pure white background with no title or header. Use crisp black and dark-gray English labels. Show six connected modules with thin arrows: `Scimago snapshot`, `WoS subset`, `DOAJ enrichment`, `Python build step`, `Sharded public JSON data`, and `Browser-side search and profile loading`. Under the sharded-data module, show `home.json`, `search-manifest.json`, `profile-index.json`, and `search-chunks`. Add two small callouts below the browser module: `No backend inference` and `On-demand shard loading`. Use minimal flat vector styling and balanced spacing.

### 2.3. Query preprocessing under sparse-metadata constraints

The runtime abstract recommender receives a user-supplied abstract and transforms it into a constrained query representation. The system lowercases text, removes punctuation, applies English and Indonesian stop-word filtering, and performs conservative suffix stripping. The core design choice is to avoid over-normalization. Under sparse metadata, aggressive stemming or broad synonym replacement can erase the few discriminative cues recoverable from short journal fields.

Three signal types are preserved: informative tokens, repeated two- to four-token phrases, and a bounded concept layer for recurring acronyms and near-equivalent expressions such as `AI`, `LLM`, `SME`, and `IoT`. The system also down-weights generic high-frequency terms like `study`, `system`, `analysis`, and `management` so that long abstracts do not dominate on methodological language alone. The goal is a middle path between naive bag-of-words overlap and opaque semantic expansion.

### 2.4. Sparse-metadata scoring formulation

The abstract recommender scores each journal profile `i` against a query `q` using a weighted additive formulation with a corrective penalty:

`S(i,q) = S_token + S_phrase + S_concept + S_detail + S_alignment - P_breadth`

This form is intentionally explicit. Each term corresponds to a signal class that can be inspected, tuned, and explained independently. The aim is not to claim theoretical optimality, but to make the ranking mechanism analytically legible.

#### 2.4.1. Field-aware token scoring

The token term uses field-specific weights because the three journal-side text fields do not carry the same kind of evidence. In the current implementation, title token matches receive weight 10, category token matches 42, and area token matches 30. The intuition is pragmatic: titles are concise but often broad, while categories and areas are usually more stable scope indicators. Low-signal tokens remain in the query, but with reduced influence.

#### 2.4.2. Phrase-aware matching

Phrase handling is central to the scorer because many journal-scope descriptors are expressed as compact multiword units. Examples include `decision support`, `digital transformation`, `supply chain`, `knowledge management`, `autonomous systems`, and `financial management`. A token-only scorer can see the individual words, but it cannot distinguish between a true topical phrase and a coincidental co-occurrence. Phrase-aware matching rewards cases where the journal profile and the query share the phrase structure itself.

The artifact extracts repeated and meaningful two- to four-token phrases from both the query and journal fields. In sparse metadata, this matters because a short label such as `industrial engineering` should count for more than separate scattered token matches. Phrase scoring therefore acts as a specificity booster.

#### 2.4.3. Conservative concept aliases

The concept term supplies limited alias expansion for recurring technical expressions and acronyms. The alias inventory is intentionally small and interpretable. It reduces obvious vocabulary mismatch without introducing the topic drift that can occur when a broader embedding model or external thesaurus is applied indiscriminately.

#### 2.4.4. Specific-detail bonuses

The detail term rewards specific matched evidence that would otherwise be diluted inside the larger additive score. When the query and journal overlap on uncommon or phrase-level topic indicators, the scorer adds discrete bonuses.

#### 2.4.5. Alignment term

The alignment term combines two intuitions: journals should be rewarded when their exposed specific metadata are tightly aligned with the matched query evidence, and they should also be rewarded when they cover a meaningful portion of the query's informative content. The current implementation computes:

`Alignment = round(80 * precision + 35 * recall)`

where precision and recall are not document-level metrics over all tokens, but bounded ratios over informative matched signal. Precision is interpreted as the proportion of journal-specific topical weight that is actually supported by the query. Recall is interpreted as the proportion of the query's informative signal that is covered by the journal profile. The weights favor precision because sparse journal metadata should not be rewarded for vague similarity. However, recall is still preserved so that journals with broader but genuinely relevant coverage are not unduly penalized.

This term helps distinguish between narrow local matches with poor overall coverage and broad journals that accumulate weak generic overlap. By mixing precision and recall over informative signal, it favors profiles that are both specific and meaningfully connected to the abstract.

#### 2.4.6. Breadth-aware penalty

The breadth penalty is the main corrective mechanism against broad-journal inflation:

`P_breadth = round(max(0, journal_specific_weight - matched_specific_weight) * 4)`

If a journal profile contains much more specific topical weight than the overlap actually covers, the unmatched remainder contributes to a penalty. This discourages broad umbrella journals from outranking narrower but better-aligned venues simply because they mention more things.

**[Figure 2 placeholder]**
**Caption:** Sparse-metadata scoring logic used by the abstract recommender.
**Nano Banana prompt:** Create a white-background technical flow diagram with clear English labels and no title or header. Show one input box labeled `Article abstract query`, then `Normalization`, `Stop-word removal`, and `Conservative stemming`. Branch into `Token matches`, `Phrase matches`, and `Concept aliases`. On the right, show `Title`, `Categories`, and `Areas`. Use arrows to a scoring block labeled `Weighted field scoring + detail bonus + alignment score - breadth penalty`. End with `Ranking score` and `Abstract fit percentage`. Add a small note: `Fit is explanatory, not the primary ranking objective`.

### 2.5. Interpretable abstract-fit signal

In addition to the main ranking score, the artifact computes an `abstract fit` percentage:

`Fit(i,q) = clamp(0, 100, round((0.7 * precision + 0.3 * recall) * 100 + coverage_bonus))`

This signal is shown to users on result cards, not used as the primary default sort. A fit score answers, "Why does this result look locally related to my query?" The main ranker answers the harder question, "Which journals should appear first when multiple forms of evidence compete?" The weighting toward precision reflects that explanatory role, while recall and coverage_bonus prevent very narrow overlaps from looking falsely decisive.

### 2.6. Evaluation design

The artifact is not evaluated with one benchmark only because exact-source recovery and graded relevance answer different scientific questions. A strict benchmark can underestimate usefulness, whereas a loose relevance benchmark can overestimate it. The study therefore uses two complementary settings.

#### 2.6.1. Benchmark A: exact-source retrieval

Benchmark A is a strict exact-source benchmark built from nine published article PDFs drawn from an external dissertation reference collection. The selected articles focus on SME digital transformation, Industry 4.0, AI adoption in small industrial firms, and related manufacturing-management themes. Each case contributes one abstract query. The label is the actual journal that published the source article. Success is counted only when that journal appears in the ranked list. Metrics are Recall@1, Recall@5, Recall@10, Recall@30, and mean reciprocal rank (MRR).

This benchmark is intentionally harsh. It treats all non-source journals as failures even if they are topically suitable. That harshness is a feature, not a defect, because it reveals how difficult exact venue recovery becomes when the journal-side representation is sparse. At the same time, Benchmark A alone would be insufficient because it can understate the practical usefulness of the artifact for authors who are open to several legitimate venues.

#### 2.6.2. Benchmark B: profile-guided cross-domain relevance

Benchmark B is a six-case cross-domain relevance benchmark built from recent open-access DOAJ articles. The six seed profiles are AI and machine learning, operations and supply chain, public and community health, environment and sustainability, agriculture and food systems, and finance and financial management. Each case is selected from an abstract that passes profile-specific signal checks. Journal results are then assigned structured relevance grades through a profile-guided automatic rubric: `3` for exact source-journal match, `2` for strong domain relevance, `1` for partial or weak relevance, and `0` for irrelevant results.

This benchmark is not presented as a human gold standard. It is a structured diagnostic designed to ask whether the ranked list is broadly useful across several domains when exact source-journal identity is not the only criterion. Metrics are Relevant Hit@5, Relevant Hit@10, Relevant MRR, nDCG@10, and exact-source Recall@10 as a secondary signal.

Together, the two benchmarks locate the artifact's current operating range: exact-source retrieval remains hard, but useful relevance ranking may still be achievable.

### 2.7. Fair lexical baselines

To avoid the weak-comparator problem, the study includes two baselines that operate on exactly the same journal-side textual fields as the artifact. No baseline is given access to richer metadata, hidden corpora, or external neural representations. This fairness constraint is essential because comparing a sparse public-data artifact to a richer semantic model with additional inputs would confound the evaluation.

The first baseline is `BM25F`, a fielded BM25 formulation over `Title`, `Categories`, and `Areas`, with field-specific weighting and per-field length normalization. `BM25F` is a strong and appropriate comparator because it is a well-established lexical ranking strategy for multi-field documents and can benefit from the same field structure that the artifact uses [9].

The second baseline is a weighted `TF-IDF` cosine scorer over the same fields and tokenization pipeline. `TF-IDF` serves as a simpler lexical comparator. It helps reveal whether the artifact's gains, if any, are due merely to weighted lexical overlap or whether phrase handling, concept expansion, alignment, and breadth correction add something beyond a basic sparse vector baseline.

By constraining all three methods to the same field inputs, the study creates a comparison that is scientifically narrower but more interpretable. If the artifact outperforms those baselines, it does so because of ranking logic rather than richer data. If it does not, the results remain informative because they indicate where classical fielded retrieval is still sufficient.

### 2.8. Manual relevance package for the next validation stage

The current DOAJ benchmark remains heuristic because its domain relevance labels are assigned through a structured automatic rubric rather than by manual expert judgment. To address this evidence gap, the repository now includes a manual relevance package. The exported CSV file `paper/manual_relevance_benchmark_template.csv` contains the union of candidate journals proposed by the current artifact, `BM25F`, and `TF-IDF` across the six seed cases. In its current form, it contains 136 candidate-judgment rows across cases `MR-01` to `MR-06`.

The companion protocol file `paper/manual_relevance_protocol.md` defines a four-level judgment scheme:

1. `3` for the exact source journal or a clearly exact scope-equivalent match.
2. `2` for a strong topical and methodological fit.
3. `1` for partial or broad fit.
4. `0` for not relevant.

This package is not counted as completed evidence in the present paper. It is reported because stronger claims will require manually judged cases with a defensible protocol rather than more heuristic examples alone.

**[Figure 3 placeholder]**
**Caption:** Evaluation design combining exact-source retrieval, cross-domain relevance, baselines, and manual-label preparation.
**Nano Banana prompt:** Create a white-background evaluation workflow diagram with clean English labels and no title or header. Show two branches from `Evaluation protocol`: `Benchmark A: exact-source PDF abstracts` and `Benchmark B: cross-domain DOAJ abstracts`. Under both, show `App default ranking`, `BM25F baseline`, and `TF-IDF baseline`. Under the DOAJ branch, add `Manual relevance labeling template` feeding into `Future gold-label benchmark`. Use thin arrows, flat boxes, and a restrained academic visual style.

### 2.9. Verification and reproducibility

The repository distinguishes implementation verification from task-level validation. Build, data-validation, smoke-test, baseline-benchmark, and benchmark-export scripts confirm that the static assets are generated correctly and that the reported results arise from the same deployable logic used in the browser.

## 3. Results

### 3.1. Runtime artifact profile

The runtime footprint reported in Table 1 confirms that the artifact is genuinely static in deployment terms. The shell needed to start the homepage is tiny, the manifest is small, and the main searchable corpus is partitioned into on-demand shards. This profile does not by itself prove excellent latency on all network conditions, but it does establish that the system avoids a major class of infrastructure dependencies: there is no server-side ranking service, no authenticated runtime API, and no backend inference model waiting behind the interface. That deployment property is substantively relevant to the paper because the study's engineering claim concerns usefulness under public lightweight constraints, not just abstract ranking quality.

The shard design also shifts complexity toward the offline build step rather than a continuous service. For institutions or individual users who need a public-facing recommendation aid without maintaining a custom backend, that trade-off is attractive even before ranking performance is considered. It also means that user abstracts can be ranked locally in the browser rather than being forwarded to a remote inference service, which can matter in environments where privacy, procurement, or infrastructure approvals slow down the adoption of more centralized scholarly tools.

### 3.2. Validation settings and comparison frame

Table 2 summarizes the two benchmark settings used in the present manuscript.

| Benchmark | Query source | Cases | Label type | Primary metrics |
| --- | --- | ---: | --- | --- |
| A. Exact-source retrieval | Published PDF abstracts from dissertation reference set | 9 | Source journal identity | Recall@k, MRR |
| B. Cross-domain relevance | Recent DOAJ open-access article abstracts | 6 | Profile-guided graded relevance (0-3) | Hit@k, MRR, nDCG@10 |

The comparison frame contains four methods: the default artifact ranker, the same artifact sorted by `fit_desc`, `BM25F`, and `TF-IDF` cosine. This allows the study to compare global ranking against local explanation and custom sparse-metadata scoring against strong lightweight lexical retrieval.

### 3.3. Exact-source benchmark outcomes

Table 3 reports the exact-source benchmark results.

| Method | R@1 | R@5 | R@10 | R@30 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| App default | 0.111 | 0.111 | 0.111 | 0.333 | 0.121 |
| App `fit_desc` | 0.000 | 0.111 | 0.111 | 0.111 | 0.028 |
| `BM25F` | 0.000 | 0.111 | 0.222 | 0.333 | 0.059 |
| `TF-IDF` cosine | 0.000 | 0.000 | 0.000 | 0.222 | 0.012 |

Three observations matter. Exact-source recovery is difficult for all methods, so the task should not be framed as strong journal prediction under the current metadata regime. The default artifact ranker is materially better than `fit_desc`, which shows that the explanatory fit score should not replace the global ranking objective. `BM25F` remains competitive, tying the artifact on Recall@30 while lagging on MRR, which means the artifact tends to place successful cases earlier when it succeeds.

The weak performance of `TF-IDF` clarifies the role of fielded weighting. `TF-IDF` retrieves no source journal in the top 10 and only 0.222 Recall@30 overall. This suggests that naive lexical similarity is not enough in the present sparse-metadata setting. Length normalization, field distinction, and more selective signal treatment matter even before phrase and breadth corrections are considered.

### 3.4. Cross-domain relevance outcomes

Table 4 reports the cross-domain relevance benchmark.

| Method | Relevant Hit@5 | Relevant Hit@10 | Relevant MRR | nDCG@10 | Exact-source Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| App default | 0.833 | 1.000 | 0.667 | 0.797 | 0.167 |
| App `fit_desc` | 0.333 | 0.667 | 0.375 | 0.458 | 0.000 |
| `BM25F` | 1.000 | 1.000 | 0.694 | 0.828 | 0.000* |
| `TF-IDF` cosine | 0.500 | 0.833 | 0.563 | 0.758 | 0.000* |

\* Baselines were evaluated to rank depth 30. Their exact-source Recall@30 on the cross-domain benchmark was 0.167.

The cross-domain picture differs from the exact-source benchmark in an important way. The default artifact remains strong, reaching Relevant Hit@10 of 1.000 and nDCG@10 of 0.797, but `BM25F` slightly exceeds it on both Relevant MRR and nDCG@10. This result is scientifically valuable because it prevents overclaim. The artifact does not uniformly dominate classical fielded lexical ranking. Instead, it appears to be stronger where source-journal recovery requires more selective topical handling, while `BM25F` remains highly effective for broader relevance ranking.

Once again, `fit_desc` performs noticeably worse. Its Relevant Hit@10 of 0.667 and nDCG@10 of 0.458 show that prioritizing the local fit percentage damages the overall relevance ordering even when the benchmark is more forgiving than exact-source recovery. That outcome is consistent with the design rationale described in Section 2.5: the fit signal is locally intelligible, but it is not a suitable surrogate for the main ranking objective.

`TF-IDF` performs better here than it did in Benchmark A, but it still trails both the default artifact and `BM25F`. This is consistent with the idea that cross-domain relevance is easier to satisfy through broader lexical alignment than exact-source venue recovery is. Even so, the gap between `TF-IDF` and `BM25F` suggests that field-aware lexical ranking remains important.

### 3.5. Objective-wise interpretation of the two benchmarks

Tables 3 and 4 show that no single method should be declared "best" without specifying the objective. The artifact is stronger on early exact-source recovery, whereas `BM25F` is slightly stronger on broader relevance ranking. This is not a nuisance result; it shows that phrase handling, concept matching, and breadth correction add value under one objective, while classical fielded lexical retrieval remains highly competitive under another.

### 3.6. Representative successes and errors

In Benchmark A, the strongest exact-source success is *Management Systems in Production Engineering*, retrieved at rank 1 from a long abstract concerning Industry 4.0 adoption in metal-product manufacturing SMEs. This case aligns well with the scorer's strengths. The abstract contains several specific industrial-management phrases, and the target journal's exposed profile provides sufficient aligned topical cues for the phrase and alignment components to matter. This is a good example of what sparse metadata can still support when query specificity is high and journal metadata are not excessively generic.

Two other source journals entered the top 30 but not the top 10: *International Journal of Information Management Data Insights* at rank 21 and *Journal of Industrial Engineering and Management* at rank 27. These cases are also revealing. The system was not "blind" to the source journals; it surfaced them, but only after more general or adjacent journals claimed earlier ranks. This suggests that the remaining failure is often not absolute retrieval failure, but rank competition against broader or better-exposed venues.

The remaining six exact-source cases were not retrieved within the top 30. Inspection of those misses indicates a recurring pattern: the source journal title and sparse taxonomic fields do not expose enough unique scope information to win against broader journals that share generic methodological or topical vocabulary. In such cases, the bottleneck is not only scoring logic. It is also representational insufficiency in the available public metadata.

Benchmark B shows a more favorable use case. In operations and supply chain and in public and community health, strong domain-relevant journals appear at rank 1. In finance and financial management, the exact source journal *Financial Innovation* appears at rank 4 while other relevant finance journals occupy the earlier ranks. This is why a strict exact-source metric understates practical value: a ranked list can still be useful even when the original venue is not first.

### 3.7. Failure-mode summary

Table 5 summarizes the main failure patterns observed in the current artifact.

| Failure pattern | Observed effect | Likely cause under sparse metadata | Implication |
| --- | --- | --- | --- |
| Broad management or AI journals outrank narrower source journals | Source journal missing from top 30 | Generic cross-domain terms remain competitive when source-journal metadata are short | Stronger lexical specificity or richer journal-side metadata would help |
| Sustainability and production journals under-ranked | Relevant but not exact journals dominate top ranks | Source journal titles do not expose enough distinctive scope cues | Category and area text alone may be insufficient for exact venue recovery |
| `fit_desc` promotes locally narrow matches | Relevance metrics drop in both benchmarks | Local overlap percentage ignores broader ranking balance | Keep fit as explanation, not main rank objective |
| Exact-source metric remains harsh | Useful alternatives are counted as failures | Multiple journals may be legitimately relevant for one abstract | Exact-source retrieval should be complemented by graded relevance |

These failure patterns are not random errors. They follow directly from the interaction between long abstracts, sparse journal metadata, and the ranking objective. When metadata specificity is low, broad journals are naturally advantaged because they expose more chances for overlap. When query specificity is high and the journal profile contains a compatible compact descriptor, the artifact performs much better. The failure map in Figure 6 formalizes this intuition visually.

### 3.8. Manual relevance benchmark package

The repository now includes a manual benchmark package designed to upgrade the heuristic DOAJ relevance benchmark into a manually judged gold-label benchmark in the next iteration. The exported file merges candidate pools from the current artifact, `BM25F`, and `TF-IDF` across six seed cases. In its current state, the template contains 136 candidate rows. This is not yet an additional performance result, but it is still a meaningful research output because it closes an important methodological gap between development diagnostics and publishable evaluation protocol.

The manual package also clarifies the present study's evidentiary boundary. The current paper can claim useful relevance-oriented behavior and a fair lexical comparison, but not full robustness under a completed human-labeled benchmark.

**[Figure 4 placeholder]**
**Caption:** Quantitative comparison of the current artifact, `fit_desc`, `BM25F`, and `TF-IDF` across the two benchmarks.
**Nano Banana prompt:** Create a clean white-background scientific figure with no title or header. Use two grouped bar charts. Left chart: `Exact-source benchmark` with `R@30` and `MRR` across `App default`, `App fit`, `BM25F`, and `TF-IDF`. Right chart: `Cross-domain relevance benchmark` with `Hit@10`, `MRR`, and `nDCG@10` across the same methods. Use a restrained palette such as charcoal, muted blue, teal, and light gray, with large clear labels.

**[Figure 5 placeholder]**
**Caption:** Manual relevance labeling workflow and rubric for the benchmark package.
**Nano Banana prompt:** Create a white-background process figure with no title or header and clear English labels. Show five boxes left to right: `Seed abstract case`, `Candidate pool from App + BM25F + TF-IDF`, `Manual judgment sheet`, `Grade assignment (0-3)`, and `Gold-label benchmark metrics`. Beneath the grading box, add four chips: `3 exact source`, `2 strong fit`, `1 partial fit`, `0 not relevant`. Keep the design minimal and high-contrast.

## 4. Discussion

### 4.1. What the current evidence actually supports

The results support a narrow but meaningful engineering conclusion: with only `Title`, `Categories`, and `Areas` available on the journal side, a static client-side artifact can still provide useful abstract-to-journal ranking. That usefulness is stronger for relevance-oriented discovery than for exact source-journal recovery, and it depends on disciplined handling of sparse signal. The current evidence does not support stronger claims such as universal journal prediction, semantic superiority over richer recommender architectures, or robustness across arbitrary domains. That limitation is not accidental. It follows from both the sparse metadata regime and the still-limited benchmark scale.

The responsible reading is therefore that the artifact works as a transparent relevance-ranking aid under constrained conditions, not that it solves journal recommendation in a general sense.

### 4.2. Why the artifact helps on exact-source recovery

The artifact's relative strength on the exact-source benchmark appears to come from the interplay of phrase handling, concept normalization, and breadth correction. Exact-source recovery under sparse metadata is often defeated by journals that share broad vocabulary with the query. A standard lexical baseline can accumulate evidence from general topical tokens, especially when the query abstract is long. The artifact partially resists that effect in three ways.

First, phrase-aware matching preserves compact topical descriptors. A journal whose sparse profile contains a coherent phrase such as `industrial engineering`, `decision support`, or `production systems` receives more concentrated credit than it would under token-only matching. Second, bounded concept expansion reduces obvious vocabulary mismatch without introducing a large latent semantic space that might pull in unrelated venues. Third, the breadth penalty reduces the advantage of journals whose profiles mention many generic domains but do not actually align with the specific content of the query.

These mechanisms are not enough to make exact-source recovery easy, but they are enough to explain why the artifact outperforms `BM25F` on MRR in Benchmark A. In practical terms, when the artifact succeeds, it tends to succeed earlier in the ranking because it is less willing to let broad journals crowd out narrower but more specifically aligned profiles.

### 4.3. Why BM25F remains highly competitive

The strong cross-domain performance of `BM25F` is equally important. It shows that the artifact's custom logic is not automatically better than classical fielded lexical retrieval. Under broader relevance objectives, `BM25F` benefits from being a strong general-purpose lexical ranker with length normalization and field structure. When the evaluation target is "retrieve relevant journals for the domain" rather than "recover the original source venue," that generality appears to be an advantage rather than a liability.

This result shows that the baseline choice is fair and that the artifact's additional heuristics are not universally beneficial. Their value appears conditional: they help more when exact-source recovery depends on selective topical cues, but less when broader domain relevance is sufficient.

### 4.4. Why fit-descending sorting is a bad default

The underperformance of `fit_desc` is one of the clearest results in the paper. It demonstrates a common interface pitfall in recommendation tools: a locally interpretable metric can be mistaken for the appropriate global rank objective. Users naturally like percentages. A high `abstract fit` looks understandable and actionable. But the results show that sorting by that percentage degrades both exact-source and cross-domain performance.

The mechanism is straightforward. The fit score is designed to represent local overlap between the abstract and a journal profile. That makes it explanation-friendly. However, local overlap is not the same as global suitability. A journal can show a very high local fit on one narrow phrase or one tightly matched area while still being a poor overall target compared with another journal whose overlap is slightly less concentrated but much more balanced. When `fit_desc` becomes the sort criterion, the ranker favors those narrow local maxima and suppresses the broader evidence integration built into the default scorer.

This separation between explanation and optimization is worth emphasizing beyond this particular artifact. Many scholarly decision-support systems expose confidence scores, similarity percentages, or recommendation strengths. The present results provide an engineering caution: such signals are valuable for user interpretation, but they should not be promoted to the primary objective unless their behavior under ranking evaluation is explicitly validated.

### 4.5. Relationship to richer semantic systems

The manuscript's positioning relative to richer semantic recommenders is now easier to state clearly. Recent journal recommendation work using sentence-transformer models over PubMed metadata [3] and transformer-plus-graph architectures for content-based journal recommendation [21] demonstrates that richer text representations and large training datasets can improve recommendation quality. Hybrid systems that incorporate author profiles or trend information [4] offer another path to stronger context modeling. The present artifact does not compete on that ground. It intentionally avoids those assumptions because the target deployment class is static, inspectable, and public-data dependent.

This distinction matters because semantic recommenders and sparse lexical artifacts solve related but not identical engineering problems. A service with stable server-side inference, domain-specific training data, and rich article corpora may reasonably optimize for predictive strength. A static browser-executed tool must instead optimize a broader bundle of constraints: transparency, no-backend deployment, bounded payload, and reliance on public metadata. The relevant comparison is therefore not "Can the artifact beat all semantic systems?" but "What level of usefulness remains achievable under this stricter resource model?"

The current results suggest that usefulness remains meaningful, but bounded. That is a positive result for the artifact class even if it is not a victory over richer models. In fact, the juxtaposition with richer recommenders may strengthen the paper because it clarifies the design space: some recommendation gains come from richer data and models, while others can still be achieved through disciplined sparse-metadata engineering.

### 4.6. Broader scholarly infrastructure implications

The artifact also speaks to a broader issue in scholarly informatics: useful research-facing tools often have to operate over incomplete, uneven, and partly public infrastructures. The importance of metadata availability has long been recognized [7], and recent work on public-metadata evaluation and academic database systems continues to show that research workflows depend strongly on exposed information structures [8], [22]. The current artifact extends that lesson to venue recommendation. Journal discovery quality is not only an algorithm problem; it is also a metadata and infrastructure problem.

If the journal-side representation remains sparse, even strong ranking logic will eventually hit an accuracy ceiling. Better public journal metadata would likely improve performance even without a radical change in the ranking model. Adjacent scholarly systems reinforce this interpretation: reviewer-assignment research faces similar open-data limits [22], knowledge-guided explainable recommenders show the value of explicit recommendation traces [19], recent recommendation over sparse public resources confirms that user-facing quality depends on the interaction between constrained descriptors and ranking logic [20], and context-aware retrieval systems illustrate the additional infrastructure cost of richer multimodal processing [23]. The artifact studied here occupies a different point on that spectrum: less expressive, but more deployable and inspectable.

### 4.7. Engineering relevance of deployability

The static deployment profile should not be treated as a secondary convenience. In engineering informatics, an artifact that can be deployed and inspected with minimal infrastructure has value even if its predictive ceiling is lower than that of a heavyweight system. Learning-to-rank decision support [16], search-centered profiling systems [17], and self-hostable scholarly tools [18] all point in the same direction: bounded complexity can be a legitimate design objective when interpretability and operational simplicity matter. For the present artifact, that value is practical as well as architectural. The tool can help researchers shortlist target journals, help supervisors or research-support units guide manuscript routing discussions, and let users explore candidate venues for unpublished abstracts without depending on a remote inference endpoint.

### 4.8. Limitations

Several limitations must be stated clearly.

1. The exact-source benchmark is small and domain-specific. With only nine cases concentrated in SME, Industry 4.0, and AI-adoption topics, it cannot support broad generalization.
2. The cross-domain relevance benchmark is still profile-guided rather than manually judged. It is therefore better interpreted as a structured diagnostic than as a definitive gold standard.
3. The current manuscript includes fair lexical baselines, but it does not yet include a completed ablation study with frozen manual judgments. As a result, the added value of each scorer component is inferred mechanistically rather than proven with component-by-component final metrics.
4. Journal-side metadata remain sparse. Missing `aims and scope`, article-title histories, and richer subject descriptions impose an upper bound on achievable accuracy regardless of ranking logic.
5. The artifact currently operates in English-oriented preprocessing with selected Indonesian stop-word support. Cross-lingual or multilingual journal discovery has not yet been validated.

These limitations define the present scientific boundary of the paper.

### 4.9. Next research steps

The most important next step is to complete the manual benchmark package and report inter-rater agreement. The second is to retain `BM25F` as a permanent comparator. The third is to incorporate richer but still public journal-side text, if available, such as aims-and-scope descriptions. Only after those steps would a stronger ablation study become fully meaningful.

**[Figure 6 placeholder]**
**Caption:** Failure-mode map of sparse-metadata journal recommendation under the current artifact and lexical baselines.
**Nano Banana prompt:** Create a clean white-background analytical diagram with no title or header. Show a 2x2 matrix with horizontal axis `Metadata specificity` from `low` to `high` and vertical axis `Query specificity` from `low` to `high`. Place short labels inside quadrants such as `Broad journals dominate`, `Useful relevance ranking`, `Exact-source recovery becomes possible`, and `Vocabulary mismatch risk`. Add small callout tags: `App default stronger on exact-source`, `BM25F competitive on cross-domain relevance`, `TF-IDF weakest overall`.

## 5. Conclusion

This paper evaluated a static engineering informatics artifact for abstract-based journal discovery under sparse public metadata. The artifact uses only journal-side `Title`, `Categories`, and `Areas` fields at ranking time, but strengthens them with weighted lexical overlap, phrase-aware matching, conservative concept expansion, an alignment term, and a breadth-aware penalty. It also exposes an interpretable `abstract fit` percentage while keeping that value separate from the main ranking objective.

The evidence supports three main conclusions. First, useful relevance-oriented journal discovery is still possible under sparse metadata and no-backend constraints. The cross-domain benchmark shows that the artifact can consistently surface relevant journals within the early ranks. Second, the distinction between local explanation and global ranking is not cosmetic. Sorting directly by the fit percentage harms both exact-source and cross-domain performance, which validates the design choice to keep fit as explanation rather than as the default objective. Third, fair lexical baselines matter. `BM25F` remains highly competitive and slightly stronger on the broader relevance benchmark, while the artifact is stronger on the small domain-specific exact-source benchmark. This means the artifact's value is conditional and should be described that way.

The resulting claim is therefore bounded but meaningful. Under sparse journal metadata, a static browser-executed artifact can provide transparent and operationally useful journal ranking support without backend inference, opaque APIs, or rich private corpora. In practical terms, that means researchers can use the tool to identify candidate target journals for publication, reduce early scope-mismatch screening effort, and obtain a defensible shortlist before moving to deeper manual inspection of aims, review policies, and indexing. The same artifact can also support supervisory review, research-office advising, and privacy-conscious exploratory use for unpublished abstracts because ranking occurs locally in the browser. However, exact source-journal recovery remains modest, and the present evidence does not justify broader accuracy claims until a manually judged gold-label benchmark is completed. In engineering terms, the artifact is best understood as a deployable, inspectable journal discovery aid that occupies a useful middle ground between trivial lexical search and heavyweight semantic recommendation systems. It also demonstrates a practical infrastructure point: author-facing recommendation can remain publicly deployable, locally inspectable, and methodologically accountable even for everyday academic use when the available journal-side evidence is sparse.

## References

[1] Z. Zhang, K. Roberts, B. G. Patra, T. Cao, H. Wu, A. Yaseen, J. Zhu, and R. Sabharwal, "Scholarly recommendation systems: a literature survey," *Knowledge and Information Systems*, vol. 65, pp. 4433-4478, 2023, doi: 10.1007/s10115-023-01901-x.

[2] W. H. Walters, "Comparing conventional and alternative mechanisms of discovering and accessing the scientific literature," *Proceedings of the National Academy of Sciences of the United States of America*, vol. 122, art. e2503051122, 2025.

[3] M. T. Colangelo, M. Meleti, S. Guizzardi, E. Calciolari, and C. Galli, "A comparative analysis of sentence transformer models for automated journal recommendation using PubMed metadata," *Big Data and Cognitive Computing*, vol. 9, no. 3, art. 67, 2025, doi: 10.3390/bdcc9030067.

[4] M. Y. Bayraktar and M. Kaya, "Author-profile-based journal recommendation for a candidate article: Using hybrid semantic similarity and trend analysis," *IEEE Access*, vol. 11, 2023, doi: 10.1109/ACCESS.2023.3271732.

[5] E. Entrup, A. Eppelin, R. Ewerth, M. Wohlgemuth, A. Hoppe, J. Hartwig, and M. Tullney, "Comparing different search methods for the open access journal recommendation tool B!SON," *International Journal on Digital Libraries*, vol. 25, pp. 505-516, 2024, doi: 10.1007/s00799-023-00372-3.

[6] Z. Gu, Y. Cai, S. Wang, M. Li, J. Qiu, S. Su, X. Du, and Z. Tian, "Adversarial attacks on content-based filtering journal recommender systems," *Computers, Materials & Continua*, vol. 64, no. 3, pp. 1755-1770, 2020.

[7] M. Linkert *et al*., "Metadata matters: access to image data in the real world," *Journal of Cell Biology*, vol. 189, no. 5, pp. 777-782, 2010, doi: 10.1083/jcb.201004104.

[8] F. Haupt, J. F. Senge, H. von Tengg-Kobligk, and W. A. Bosbach, "Enabling transparent research evaluation: A method for historical RCR retrieval using public NIH metadata," *PLoS One*, vol. 21, no. 1, art. e0340697, 2026, doi: 10.1371/journal.pone.0340697.

[9] H. Zamani, B. Mitra, X. Song, N. Craswell, and S. Tiwary, "Neural ranking models with multiple document fields," in *Proceedings of the Eleventh ACM International Conference on Web Search and Data Mining*, 2018, doi: 10.1145/3159652.3159730.

[10] K. Wang, N. Reimers, and I. Gurevych, "DAPR: A benchmark on document-aware passage retrieval," in *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics, Volume 1: Long Papers*, pp. 4313-4330, 2024.

[11] S. M. Alzanin, A. M. Azmi, and H. A. Aboalsamh, "Short text classification for Arabic social media tweets," *Journal of King Saud University - Computer and Information Sciences*, vol. 34, pp. 6595-6604, 2022.

[12] V. Patel, S. Ramanna, K. Kotecha, and R. Walambe, "Short text classification with tolerance-based soft computing method," *Algorithms*, vol. 15, no. 8, art. 267, 2022, doi: 10.3390/a15080267.

[13] J. Tussupov, A. Kassymova, A. Mukhanova, A. Bissengaliyeva, Z. Azhibekova, M. Yessenova, and Z. Abuova, "Analysis of short texts using intelligent clustering methods," *Algorithms*, vol. 18, no. 5, art. 289, 2025, doi: 10.3390/a18050289.

[14] M. Benleulmi, I. Gasmi, N. Azizi, and N. Dey, "Explainable AI and deep learning models for recommender systems: State of the art and challenges," *Journal of Universal Computer Science*, vol. 31, no. 4, pp. 383-421, 2025.

[15] S. Sana and M. Shoaib, "Trustworthy explainable recommendation framework for relevancy," *Computers, Materials & Continua*, 2022, doi: 10.32604/cmc.2022.028046.

[16] Y. Miyachi, O. Ishii, and K. Torigoe, "Design, implementation, and evaluation of the computer-aided clinical decision support system based on learning-to-rank: collaboration between physicians and machine learning in the differential diagnosis process," *BMC Medical Informatics and Decision Making*, vol. 23, art. 26, 2023, doi: 10.1186/s12911-023-02123-5.

[17] R. G. Hernandez, R. L. Hernandez, and N. F. Bueno, "Decision support system on faculty profiling using full-text search algorithm: A tool for evaluating faculty performances," *Journal Europeen des Systemes Automatises*, vol. 58, no. 4, pp. 689-700, 2025, doi: 10.18280/jesa.580403.

[18] B. Edelman and J. Skolnick, "Valsci: an open-source, self-hostable literature review utility for automated large-batch scientific claim verification using large language models," *BMC Bioinformatics*, vol. 26, art. 140, 2025, doi: 10.1186/s12859-025-06159-4.

[19] S. Ren, X. Zheng, J. Zhao, J. Du, Y. Zhang, C. Bi, J. Song, J. Zhang, H. Lang, F. Zhang, and B. Shen, "Knowledge-guided explainable recommendation tool for cancer risk prediction models using retrieval-augmented large language models: Development and validation study," *JMIR Medical Informatics*, art. 78519, 2026.

[20] Y. Yang, "Intelligent recommendation of information resources in university libraries based on fuzzy logic and deep learning," *International Journal of Computational Intelligence Systems*, 2025, doi: 10.1007/s44196-025-00993-3.

[21] J. Liu, M. Castillo-Cara, and R. Garcia-Castro, "On the significance of graph neural networks with pretrained transformers in content-based recommender systems for academic article classification," *Expert Systems*, vol. 42, art. e70073, 2025, doi: 10.1111/exsy.70073.

[22] A. C. Ribeiro, A. Sizo, and L. P. Reis, "Investigating the reviewer assignment problem: A systematic literature review," *Journal of Information Science*, vol. 52, no. 1, pp. 39-59, 2026, doi: 10.1177/01655515231176668.

[23] S. Patil and Z. Aalam, "An AI-enhanced system for context-aware information retrieval and summarization in AI-assisted learning," *SSRG International Journal of Electronics and Communication Engineering*, vol. 12, no. 8, pp. 307-315, 2025, doi: 10.14445/23488549/IJECE-V12I8P127.
