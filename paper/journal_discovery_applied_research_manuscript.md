# Interpretable Field-Aware Retrieval for Abstract-to-Journal Recommendation with Sparse Metadata

Author details omitted for review.

## Abstract

Purpose: This study examines whether a browser-executed journal discovery artifact can provide useful support for selecting publication venues when journal-side metadata are restricted to title, categories, and subject areas.

Design/Methodology/Approach: The study applies an engineering informatics artifact-evaluation design to *Journal Discovery*, a static recommendation tool built from a 29,553-journal snapshot enriched with Web of Science and DOAJ signals. The ranking model combines field-aware lexical overlap, phrase-aware matching, bounded concept expansion, an alignment component, and a breadth-aware penalty. The artifact was evaluated with two benchmark settings and compared against fair `BM25F` and `TF-IDF` lexical baselines operating on the same sparse metadata fields.

Findings: On a nine-case exact-source benchmark derived from published SME and Industry 4.0 abstracts, the default artifact reached Recall@30 of 0.333 and mean reciprocal rank of 0.121, outperforming `BM25F` on mean reciprocal rank and `TF-IDF` on both measures. On a six-case cross-domain relevance benchmark built from recent open-access abstracts, the artifact achieved Relevant Hit@10 of 1.000, Relevant mean reciprocal rank of 0.667, and nDCG@10 of 0.797, although `BM25F` remained slightly stronger on broad domain relevance.

Research Limitation/Implication: The exact-source benchmark is small and domain-specific, while the cross-domain benchmark is still profile-guided rather than manually judged. The results therefore support usefulness claims more strongly than universal accuracy claims.

Practical Implication: The artifact can help researchers shortlist plausible target journals from an abstract, reduce early scope-mismatch screening effort, and support manuscript-routing decisions without requiring backend inference or private corpora.

Social Implication: Because ranking occurs locally in the browser, the artifact supports privacy-conscious use for unpublished abstracts and can broaden access to journal discovery support for institutions with limited research infrastructure.

Originality/Value: The study contributes an interpretable, static, and field-aware retrieval design for journal recommendation under severe metadata sparsity and evaluates it against fair lightweight baselines under deployment-realistic conditions.

**Keywords:** venue selection, scholarly discovery, client-side ranking, scope matching, publishing support tools

## Introduction

Selecting an outlet for a manuscript is one of the most consequential decisions in the publication workflow. The decision affects review fit, desk-rejection risk, revision effort, time to publication, and the audience that finally encounters the work. In practice, this decision is often made under pressure and with incomplete information. Researchers may know their own topic well, yet still face uncertainty when deciding which journals are realistically aligned with the scope, method, and contribution of a manuscript. This problem is particularly visible when an abstract already communicates the substance of a paper, but the public metadata attached to candidate journals remain short, broad, and unevenly structured.

The present study treats this issue as an applied research and engineering informatics problem rather than merely as a convenience feature in literature search. For researchers, an abstract-to-journal recommendation tool can serve as a practical aid during the first stage of journal selection. It can reduce the time spent screening obviously unsuitable venues, widen awareness of journals beyond an author's habitual reading list, and support early-career or interdisciplinary researchers who may lack deep tacit knowledge of journal landscapes. A transparent tool can also support supervisors, librarians, research offices, and writing workshops that assist authors in publication planning. If such a tool is lightweight and browser-executed, it can additionally protect unpublished abstracts from being sent to remote inference services.

The broader scholarly recommendation literature shows that recommendation tasks in research are diverse and increasingly important. Scholarly recommendation systems help users identify papers, collaborators, venues, datasets, and related scholarly objects in growing and fragmented information environments (Zhang et al., 2023). At the same time, discovery practices have become distributed across traditional databases, search engines, web-native platforms, and open infrastructures, each with different coverage and metadata limitations (Walters, 2025). Journal selection is one concrete manifestation of that fragmentation because authors often have to combine domain intuition, indexing knowledge, and manual browsing simply to identify a plausible set of candidate outlets.

Problem Statement. Current journal recommendation approaches frequently assume access to richer inputs than many public-facing deployments can reliably obtain. Transformer-based journal recommenders built from article corpora and PubMed metadata can be effective, but they depend on richer text representations and larger upstream data structures than a short journal profile alone can provide (Colangelo et al., 2025). Hybrid recommender systems that use author profiles, publication trends, or context signals can also strengthen ranking quality, yet such inputs are not always available in privacy-sensitive or first-use scenarios (Bayraktar and Kaya, 2023). Even transparent open tools such as B!SON operate within infrastructure conditions that still exceed the constraints of a purely static browser-side artifact (Entrup et al., 2024). More recent content-based work combining graph neural networks and pretrained transformers similarly demonstrates the value of richer representational modeling, but also highlights the reliance on extensive article data and heavier computation (Liu, Castillo-Cara and Garcia-Castro, 2025).

The research gap is therefore not simply "accuracy is still low." The sharper gap is a translation gap between powerful recommendation methods and deployable tools that must operate under sparse, public, and inspectable metadata conditions. In many journal directories and ranking lists, the most stable public journal-side text comprises only the title and a few topical labels. Full aims-and-scope statements, representative article corpora, or structured thematic summaries may be missing, inconsistent, or difficult to harvest at scale. Under those conditions, a long abstract must be matched to a very short journal profile. This creates a difficult long-to-short retrieval problem in which the richer object is the query rather than the indexed item.

The importance of this gap is both practical and scientific. It matters practically because researchers need initial journal shortlists even when they do not have access to proprietary recommendation services. It matters scientifically because sparse metadata define a different problem from the richer recommendation scenarios commonly addressed in journal recommender research. Metadata studies have already shown that the structure and availability of public metadata shape what users can discover and reuse (Linkert et al., 2010). Work on transparent research evaluation built on public metadata reinforces the same point: when public metadata form the analytic substrate, the scope of reliable inference is bounded by the exposed fields themselves (Haupt et al., 2026). In academic research more broadly, online database systems influence retrieval efficiency and research productivity, but their usefulness still depends on the quality and accessibility of available metadata (Yanping and Weiye, 2024).

The present study argues that sparse journal recommendation should be viewed as a field-aware retrieval and decision-support problem. A journal title, a category label, and a subject-area descriptor do not contribute equal forms of evidence. Multi-field ranking studies show that different document fields should not be treated uniformly because they encode different relevance signals (Zamani et al., 2018). Document-aware retrieval benchmarks also show that missing context remains a major source of retrieval error (Wang, Reimers and Gurevych, 2024). Short-text research reaches a similar conclusion from another angle: when context is limited, vocabulary mismatch and weak lexical evidence can destabilize ranking and classification (Alzanin, Azmi and Aboalsamh, 2022; Patel et al., 2022; Tussupov et al., 2025). This means that a sparse journal recommender must protect high-value topic cues and avoid allowing long abstracts to win on generic lexical volume alone.

Explainability is equally important in this context. A journal recommendation is rarely accepted just because it appears at rank one. Users inspect the list and ask why a recommendation was surfaced, whether the logic reflects topical fit, and whether the recommendation is overly broad or only superficially similar. Research on explainable and trustworthy recommender systems consistently shows that usefulness depends not only on ranking but also on whether the user can interpret the recommendation trace (Benleulmi et al., 2025; Sana and Shoaib, 2022). This consideration is especially salient in journal selection because the user is not merely consuming a recommendation; the user is making a publication decision.

The central objective of this study is therefore to evaluate whether a static journal discovery artifact can still provide useful and interpretable abstract-to-journal recommendation under sparse metadata constraints. The study focuses on *Journal Discovery*, a browser-executed artifact that uses only public journal-side `Title`, `Categories`, and `Areas` fields at ranking time. The article investigates whether field-aware scoring, phrase preservation, bounded concept expansion, alignment scoring, and breadth correction can produce useful rankings under those constraints.

Specifically, the study addresses four questions:

1. Can a static client-side journal discovery artifact provide useful abstract-to-journal ranking when journal metadata are restricted to title, categories, and subject areas?
2. Does a field-aware ranking design outperform a simple sort strategy based only on local abstract-fit percentage?
3. How does the artifact compare with fair `BM25F` and `TF-IDF` lexical baselines operating on the same sparse fields?
4. What do the current results imply about the boundary between useful relevance ranking and exact source-journal recovery?

The study contributes an interpretable and deployment-aware retrieval design, a realistic comparative evaluation against strong lightweight baselines, and a prepared path toward manual gold-label benchmarking. The article is written as an applied research contribution because its value lies not only in a ranking formula but also in demonstrating what level of journal-selection support remains achievable under public-data and lightweight-deployment constraints.

The study also adopts a deliberately conservative epistemic stance. It does not equate journal recommendation with final journal selection, nor does it assume that a ranked output can replace editorial due diligence, disciplinary judgment, or manual inspection of scope, review policies, and indexing status. Instead, the artifact is positioned as an early-stage decision-support instrument. This framing is important because it affects what counts as success. In one sense, success can mean recovering the exact journal that originally published an abstract. In another, and often more practical, sense, success can mean surfacing a compact set of credible and relevant journals that help the author move efficiently into deeper screening. The present article treats both senses of success as legitimate but analytically distinct, and this distinction guides the later evaluation strategy.

**[Figure 1 placeholder]**
**Caption:** Applied research framing of sparse-metadata journal recommendation as a publication-decision support workflow.
**Nano Banana prompt:** Create a clean white-background conceptual workflow figure with no title or header. Use highly legible English labels only. Show five left-to-right stages connected by thin arrows: `Manuscript abstract`, `Sparse public journal metadata`, `Field-aware retrieval artifact`, `Ranked shortlist of candidate journals`, and `Human publication decision`. Add small note boxes beneath the last two stages labeled `Interpretability support` and `Manual scope verification`. Use a restrained academic style with dark text, subtle muted blue-gray accents, and balanced spacing.

## Theories Underpinning Study

### Fielded information retrieval under sparse evidence

The first theoretical foundation of the study is fielded information retrieval. In fielded retrieval, different parts of a document contribute different evidential roles to the final ranking. This principle is especially relevant for sparse journal profiles because the title, category labels, and subject areas are not interchangeable. A title may be concise but broad, while categories and subject areas often function as taxonomic signals rather than descriptive prose. Neural ranking work on multiple document fields established that field structure should be respected rather than flattened into one uniform text stream (Zamani et al., 2018). Even when the present artifact does not adopt neural ranking, the same principle remains theoretically useful.

This foundation implies that sparse journal recommendation should not be approached as an undifferentiated bag-of-words task. If all journal-side fields are merged and scored uniformly, broad titles and generic labels can dominate the ranking. A field-aware approach is therefore more defensible because it acknowledges that the three available text sources provide different types of topical evidence.

### Explainable recommendation and human judgment

The second theoretical foundation is explainable recommendation. Explainability matters in recommendation systems because users need to understand why a recommendation has been surfaced and whether it is safe to rely on it (Benleulmi et al., 2025; Sana and Shoaib, 2022). In journal selection, the human user remains the final evaluator. The system does not make the submission decision; it supports the decision. This makes local interpretability especially valuable. A recommendation trace that communicates overlapping scope cues, rather than merely returning a rank, is more consistent with human-centered decision support.

This theoretical perspective informs the separation between the main ranking score and the displayed `abstract fit` percentage. The fit percentage functions as an explanatory local signal, while the overall ranking score integrates broader evidence. The distinction is theoretically grounded in the idea that explanation and optimization are related but not identical functions in a recommender system.

### Applied decision support under bounded infrastructure

The third foundation is the theory of practical decision support under bounded infrastructure. Decision-support systems can create value even when their predictive power is lower than that of heavier alternatives, provided that they are transparent, deployable, and aligned with the user's real task. Learning-to-rank has already been applied in computer-aided clinical decision support to improve prioritization rather than binary classification (Miyachi, Ishii and Torigoe, 2023). Search-centered profiling tools likewise demonstrate that simple ranking logic can still be operationally useful when aligned to concrete user workflows (Hernandez, Hernandez and Bueno, 2025). Self-hostable scholarly tools such as Valsci make a similar case for bounded complexity in research-facing systems (Edelman and Skolnick, 2025).

This perspective is important because the contribution of the present artifact is not only algorithmic. It is also infrastructural. The artifact is designed to operate without backend inference, private corpora, or continuous service dependencies. That makes the study theoretically relevant to lightweight decision-support research rather than only to high-resource recommendation research.

### Construct validity in journal-fit evaluation

The fourth theoretical concern underlying the study is construct validity. Journal recommendation can be operationalized in at least two ways, and the choice has direct implications for evaluation. The first is exact venue recovery, in which the source journal of a known abstract is treated as the sole correct answer. The second is graded relevance, in which several journals may be acceptable matches if they align with the scope and contribution of the abstract. Neither construct is inherently superior; they simply answer different questions. Exact-source evaluation is stricter and easier to score, but it can understate the practical usefulness of a recommendation list because publishing is not always a single-journal problem. Graded relevance is more aligned with real author workflows, but it requires either expert judgment or a carefully designed rubric.

This distinction matters theoretically because the artifact is intended for decision support rather than automatic classification. An author deciding where to submit a manuscript is usually satisfied if the system reveals several plausible candidates near the top of the list. Yet scholarly evaluation becomes too permissive if any broad domain match is counted as success. The present study therefore adopts a dual evaluation logic to preserve construct validity. Exact-source recovery tests whether the artifact can recover the original venue under severe metadata constraints. Relevance-oriented evaluation tests whether the ranked list remains useful when judged as a shortlist rather than a single-label prediction. This dual framing is central to the article's rigor because it prevents the system from being evaluated only on the metric most favorable to it.

**[Figure 2 placeholder]**
**Caption:** Conceptual distinction between exact-source recovery and graded relevance in journal recommendation evaluation.
**Nano Banana prompt:** Create a white-background analytical diagram with no title or header and very clear English labels. Show one input box labeled `Abstract query` feeding into two parallel evaluation branches. The left branch should end with `Exact source journal recovered?` and metric labels `Recall@k` and `MRR`. The right branch should end with `Useful shortlist returned?` and metric labels `Hit@k` and `nDCG`. Add a small note at the bottom: `Different evaluation constructs answer different research questions`. Use thin lines, flat boxes, black text, and subtle muted accent colors only.

## Literature Review

### Journal recommendation studies

Recent journal recommendation studies can be grouped into at least three broad streams. The first stream emphasizes semantic similarity between manuscripts and journals, often using embeddings or sentence transformers. For example, Colangelo et al. (2025) examine sentence-transformer models for automated journal recommendation using PubMed metadata, showing that semantic models can strengthen venue matching when suitable metadata are available. The second stream uses hybrid architectures that combine content similarity with contextual signals. Bayraktar and Kaya (2023) propose a journal recommendation approach that integrates semantic similarity with author profile and trend analysis, illustrating the value of richer contextual information. The third stream emphasizes transparency and openness in journal discovery interfaces. Entrup et al. (2024) compare search methods in the open-access journal recommendation tool B!SON and show the practical value of open scholarly infrastructure for venue recommendation.

These streams establish that journal recommendation is already a recognized scholarly problem. However, they also reveal the key limitation for the present study: most existing approaches assume richer article-side corpora, richer journal-side metadata, or supporting infrastructure that exceeds the constraints of a static public artifact. Even when the user-facing interface is simple, the upstream data and model assumptions are often not.

### Sparse-text retrieval and short-text matching

Sparse journal recommendation is also linked to the literature on short-text matching and retrieval under limited context. Wang, Reimers and Gurevych (2024) show through the DAPR benchmark that document-aware retrieval errors often arise when important context is absent. Short-text classification studies similarly show that weak lexical evidence and vocabulary mismatch remain important obstacles, even under more advanced feature-processing settings (Alzanin, Azmi and Aboalsamh, 2022; Patel et al., 2022). Tussupov et al. (2025) further demonstrate that clustering and classification over short texts remain sensitive to sparse signal and representation choice.

The relevance of this literature to journal discovery is direct. A long abstract contains abundant lexical material, but the journal-side profile may still be short, broad, and taxonomic. This is not the same as matching two full abstracts or two full documents. The retrieval challenge is structurally asymmetric. That asymmetry supports the need for phrase-aware and field-aware handling rather than naïve lexical overlap alone.

### Explainability, trust, and applied recommendation

A separate but equally relevant line of literature concerns explainability and trust. Benleulmi et al. (2025) review explainable recommender systems and argue that high-quality recommendation increasingly requires interpretable reasoning, not only accurate ranking. Sana and Shoaib (2022) reach a compatible conclusion from a trustworthy recommendation perspective. Ren et al. (2026) show in a domain-specific scientific recommendation setting that knowledge-guided explainable recommendation can improve usability when repositories are fragmented and heterogeneous. Yang (2025) similarly shows that recommendation quality over constrained resource descriptions depends on the interaction between ranking logic and the structure of exposed metadata.

These studies strengthen the relevance of explainability for the present artifact. Journal recommendation is not a fully automated decision problem. Users must judge fit, appropriateness, and plausibility. Therefore, local explanatory cues and transparent ranking behavior are central to the usefulness of the artifact.

### Gaps in the reviewed literature

Taken together, the reviewed literature reveals three specific gaps relevant to this study. First, there remains a method gap: many journal recommendation studies rely on richer metadata or infrastructure than a static artifact can assume. Second, there is an evidence gap: lightweight static tools are less often evaluated against strong baselines under the same sparse metadata constraints. Third, there is a translation gap: the literature offers limited insight into what journal-selection support remains feasible when recommendation must be public-data based, browser-executed, and locally inspectable.

The present study addresses those gaps by evaluating a sparse-metadata artifact under deployment-realistic constraints and by comparing it against fair lexical baselines that use the same available fields.

### Public infrastructure, evaluation realism, and open scholarly workflows

Another issue that emerges across the reviewed literature is the relationship between recommendation quality and the practical conditions of scholarly infrastructure. Many academic recommendation studies report promising performance under carefully curated datasets, but fewer show what remains feasible when the system has to operate on public metadata alone, under open deployment, and without privileged access to large proprietary corpora. This is not a trivial omission. Researchers in low-resource settings, smaller institutions, and interdisciplinary teams often have to make publication decisions under exactly these constrained conditions. A recommendation tool that presupposes expensive infrastructure may be scientifically interesting but operationally inaccessible to the users who need it most.

This infrastructure issue also affects evaluation realism. A system may appear strong in offline experiments while relying on data structures that are unavailable in real public use. Conversely, a lightweight public-data tool may appear weaker in raw accuracy but more valuable in actual deployment because it is transparent, reproducible, and easy to adopt. The present study therefore reads the literature not only for model ideas but also for evidence about which parts of journal recommendation remain stable under realistic constraints. B!SON is especially relevant here because it demonstrates the value of transparency and openness in venue recommendation, even though its infrastructure assumptions still differ from those of a static browser-only artifact (Entrup et al., 2024). Work on reviewer assignment is also instructive because it shows that scholarly routing tasks repeatedly confront fragmented data, incomplete metadata, and the need for explainable support (Ribeiro, Sizo and Reis, 2026).

This review perspective leads to one of the article's key methodological positions: recommendation research should be evaluated not only by predictive performance but also by data realism and deployment realism. For the present artifact, that means the scientific question is not merely whether a better rank can be produced, but whether a useful, inspectable, and resource-efficient ranking can be produced from the kinds of public journal metadata that many researchers can actually access. In this sense, the study's originality lies partly in making the deployment constraint analytically central rather than treating it as a background limitation.

## Research Methods

### Research design

The study uses an engineering informatics artifact-evaluation design. The object of study is an already functioning static web artifact rather than a hypothetical model tested only offline. The methodological aim is to formalize, instrument, and evaluate the ranking logic that the deployed artifact actually uses. This design is appropriate because the study is concerned with both retrieval behavior and deployment realism.

The unit of analysis is the ranked journal list produced for a single abstract query. Each benchmark case therefore represents one decision-support episode in which the system receives a full abstract and returns an ordered set of candidate journals. This unit of analysis is appropriate because it corresponds to how the artifact is actually used. The study does not treat isolated token matches, phrase matches, or individual journals as independent statistical observations. Instead, it treats each query-to-ranked-list interaction as the meaningful analytic event. This choice is methodologically important because the small number of benchmark cases would otherwise invite invalid pseudo-replication if lower-level units were counted as independent samples.

### Analytic corpus and data sources

The analytic corpus consists of 29,553 journal profiles generated from three public data streams. The first is a Scimago Journal Rank snapshot used as the core journal list. The second is a Web of Science subset aligned to the same snapshot. The third is an optional DOAJ enrichment file that contributes public journal websites, APC status, copyright information, and licensing where available. The final artifact marks 17,799 journals as Web of Science indexed and 8,544 as DOAJ-enriched.

The runtime topical scorer uses only three journal-side textual fields:

1. `Title`
2. `Categories`
3. `Areas`

Other metadata fields are displayed in the interface but are not used in topical recommendation ranking. This design preserves a strict sparse-metadata condition during evaluation.

The retention of this strict condition serves two purposes. First, it ensures that the article answers a coherent research question. If richer journal-side text were selectively introduced for some methods but not others, the comparison would become a data comparison rather than a ranking comparison. Second, it keeps the artifact aligned with its intended use scenario, namely public journal discovery when the most reliable available text is limited to a title and taxonomic descriptors. In methodological terms, the sparse-metadata constraint is therefore not a weakness to be engineered away during evaluation; it is the defining boundary of the experiment.

### Artifact architecture and research instrument

The artifact is deployed as a static website. The build process transforms the aligned data into several browser-consumable JSON resources, including a homepage summary, a search manifest, a profile index, and sharded search data. The current search corpus is partitioned into 15 JSON shards totaling 20.55 MB. The homepage summary file is 341 B, the manifest is 3.9 KB, and the profile index is 1.44 MB. Title-scoped search is further narrowed using 30 title-prefix buckets.

The research instrument used for evaluation is therefore the deployed ranking logic itself, executed through the artifact's browser-side search flow and associated benchmark harnesses. This approach avoids a common mismatch in recommender studies where the evaluated offline scorer differs from the production logic that users encounter.

**[Figure 3 placeholder]**
**Caption:** Static artifact architecture and data flow from public metadata snapshots to browser-side ranking.
**Nano Banana prompt:** Create a clean white-background systems diagram with no title or header. Use crisp English labels only. Show six connected modules: `Scimago snapshot`, `WoS subset`, `DOAJ enrichment`, `Build pipeline`, `Sharded JSON search data`, and `Browser-side ranking interface`. Under the sharded-data module, include small sub-boxes labeled `home.json`, `search manifest`, `profile index`, and `search shards`. Add two small callouts below the interface module: `No backend inference` and `Local abstract ranking`. Use a restrained scientific visual style with balanced spacing and subtle muted blue-gray accents.

This design decision improves ecological validity. Authors who use journal recommendation tools interact with deployed interfaces, not isolated ranking modules. By evaluating the artifact through its browser-side logic, the study ensures that preprocessing, shard loading, field weighting, and result ordering are all tested in the same operational chain that would be experienced by an end user. This also limits the temptation to tune an offline scorer in ways that are difficult to sustain in the deployed system.

### Query processing and ranking model

The abstract recommender receives a user-supplied abstract and applies lowercasing, punctuation removal, English and Indonesian stop-word filtering, and conservative suffix stripping. The system preserves three signal types: informative tokens, repeated two- to four-token phrases, and a bounded concept layer for recurring acronyms and near-equivalent technical expressions.

The main ranking score is defined as:

`S(i,q) = S_token + S_phrase + S_concept + S_detail + S_alignment - P_breadth`

where `i` represents a journal profile and `q` represents the abstract query.

The token term is field-aware. In the current implementation, title matches receive weight 10, category matches 42, and area matches 30. The phrase term rewards coherent multiword overlap, while the concept term adds bounded alias expansion for recurring technical expressions such as `AI`, `LLM`, `SME`, and `IoT`. The detail term adds bonuses for specific matched evidence. The alignment term is computed as:

`Alignment = round(80 * precision + 35 * recall)`

The breadth-aware penalty is computed as:

`P_breadth = round(max(0, journal_specific_weight - matched_specific_weight) * 4)`

This penalty reduces the tendency of broad journals to dominate rankings through generic overlap alone.

### Explanatory fit signal

In addition to the main ranking score, the artifact computes an `abstract fit` percentage:

`Fit(i,q) = clamp(0, 100, round((0.7 * precision + 0.3 * recall) * 100 + coverage_bonus))`

This score is displayed as an explanatory local signal rather than being used as the default sorting objective. The design assumption is that a useful journal recommender should explain local fit without letting that local measure displace the broader ranking objective.

**[Figure 4 placeholder]**
**Caption:** Field-aware sparse-metadata scoring pipeline used by the abstract recommender.
**Nano Banana prompt:** Create a white-background technical flow figure with no title or header and highly legible English labels. Show one input box labeled `Article abstract` flowing into `Normalization`, `Stop-word filtering`, and `Conservative stemming`. Then branch to three match channels labeled `Tokens`, `Phrases`, and `Concept aliases`. On the right, show three journal-field boxes labeled `Title`, `Categories`, and `Areas`. Connect them to a scoring block labeled `Field weights + detail bonus + alignment - breadth penalty`, then end with two outputs labeled `Ranking score` and `Abstract fit`. Use thin arrows, simple flat boxes, dark text, and muted accent colors only.

### Baselines

Two fair lexical baselines were implemented over the same three journal-side fields:

1. `BM25F`, a fielded BM25 baseline with field-specific weighting and length normalization.
2. `TF-IDF` cosine similarity over the same weighted fields and tokenization pipeline.

These baselines are fair because they do not use richer metadata, external corpora, or server-side models.

Baseline fairness was treated as a methodological requirement rather than an optional extra. All methods were given the same journal-side fields and the same broad sparse-data condition. The baselines were not intentionally weakened through poor parameterization or unrealistic input restriction. `BM25F` was included because it is the most relevant strong lexical comparator for fielded sparse documents, while `TF-IDF` was included as a simpler but still meaningful lexical reference point. This is important because claims of artifact superiority become difficult to defend when the baseline is either too weak or evaluated under different data assumptions.

### Benchmark design and sampling

The study uses two benchmark settings.

#### Benchmark A: Exact-source retrieval

Benchmark A contains nine abstract queries extracted from published PDFs in an external dissertation reference collection. The cases focus on SME digital transformation, Industry 4.0, AI adoption in small industrial firms, and adjacent manufacturing-management topics. Each query is matched against the full journal corpus, and success is counted only when the original source journal appears in the ranked results. Metrics are Recall@1, Recall@5, Recall@10, Recall@30, and mean reciprocal rank.

#### Benchmark B: Cross-domain relevance benchmark

Benchmark B contains six recent DOAJ-derived open-access abstracts representing the following profiles:

1. AI and machine learning
2. Operations and supply chain
3. Public and community health
4. Environment and sustainability
5. Agriculture and food systems
6. Finance and financial management

Each case is graded with a four-level profile-guided relevance rubric:

1. `3` = exact source-journal match
2. `2` = strong topical relevance
3. `1` = partial relevance
4. `0` = not relevant

Metrics are Relevant Hit@5, Relevant Hit@10, Relevant mean reciprocal rank, nDCG@10, and exact-source Recall@10 as a secondary signal.

The article does not report inferential significance testing for these benchmarks, and this omission is deliberate. The benchmark sizes are small, the cases are not sampled as independent and identically distributed observations from a known population, and the evaluation is deterministic for a fixed snapshot. Under these conditions, formal null-hypothesis significance testing would create a misleading impression of statistical precision. Instead, the study reports transparent descriptive metrics, cross-benchmark comparison, and case-level interpretation. This choice is methodologically stricter because it avoids overstating certainty where the sample design does not support it.

### Data analysis and verification

The study compares the default artifact ranking, the alternative `fit_desc` artifact sort, `BM25F`, and `TF-IDF`. Result interpretation focuses on both benchmark objectives because exact-source retrieval and graded relevance answer different questions. Verification of the artifact and benchmark workflow was performed through repository build, data-validation, smoke-test, and benchmark scripts so that the reported results remain tied to the actual deployable artifact.

In addition to software verification, the study considered several forms of validity and risk. Construct validity was addressed through the dual benchmark design, which separates exact-source recovery from graded relevance. Internal validity was strengthened by holding the journal-side fields constant across the artifact and the two lexical baselines. Reliability was supported by deterministic scripts that regenerate the same benchmark outputs from the same snapshot. External validity remains limited, and this limitation is acknowledged explicitly: the exact-source benchmark is domain-specific, and the relevance benchmark is still profile-guided rather than manually judged. Ethical and governance considerations were also considered. Because the artifact runs locally in the browser after asset loading, it reduces the need to transmit unpublished manuscript abstracts to a remote inference service. This privacy characteristic does not guarantee confidentiality in all deployment settings, but it is still a meaningful applied advantage compared with systems that require server-side ranking by default.

**[Figure 5 placeholder]**
**Caption:** Evaluation workflow combining exact-source benchmarking, graded relevance benchmarking, lexical baselines, and manual-label preparation.
**Nano Banana prompt:** Create a white-background evaluation workflow diagram with no title or header and clear English labels. Start from a box labeled `Evaluation protocol`, then branch into `Benchmark A exact-source PDFs` and `Benchmark B DOAJ relevance cases`. Under both branches, place three comparator boxes: `Artifact default`, `BM25F`, and `TF-IDF`. Under the DOAJ branch, add another box labeled `Manual relevance template` leading to `Future gold-label benchmark`. Use thin arrows, flat rectangles, black text, and subtle muted accent colors.

## Results

### Artifact profile and analytic corpus

Table 1 summarizes the current artifact snapshot.

Table 1. Dataset and runtime snapshot of the evaluated artifact

| Item | Value |
| --- | ---: |
| Total journals | 29,553 |
| Web of Science indexed journals | 17,799 |
| DOAJ-enriched journals | 8,544 |
| Search shard files | 15 |
| Total search-shard payload | 20.55 MB |
| Homepage metadata file | 341 B |
| Search manifest | 3.9 KB |
| Profile index | 1.44 MB |
| Title-prefix buckets | 30 |

The table shows that the artifact is genuinely lightweight in deployment terms. Ranking occurs after browser-side data loading, without a remote ranking API or backend inference service. This matters because the study evaluates not only ranking behavior, but also a specific deployment model for research support.

### Benchmark summary

Table 2 summarizes the two evaluation settings and clarifies why both are needed for a defensible assessment of the artifact. Benchmark A is designed to test the stricter question of whether the system can recover the original source journal from a full abstract under sparse metadata conditions. Benchmark B addresses a different but equally important practical question, namely whether the system can still return a useful shortlist of topically relevant journals across multiple domains even when exact source-journal recovery is difficult. Reporting both settings side by side is methodologically important because it prevents the artifact from being judged only by the evaluation construct that is most favorable to it.

Table 2. Benchmark design used in the study

| Benchmark | Query source | Cases | Label type | Main metrics |
| --- | --- | ---: | --- | --- |
| A | Published dissertation-reference PDFs | 9 | Exact source journal | Recall@k, mean reciprocal rank |
| B | Recent DOAJ open-access abstracts | 6 | Profile-guided graded relevance | Hit@k, mean reciprocal rank, nDCG@10 |

### Exact-source benchmark results

Table 3 presents the results of Benchmark A.

Table 3. Exact-source benchmark results

| Method | R@1 | R@5 | R@10 | R@30 | Mean reciprocal rank |
| --- | ---: | ---: | ---: | ---: | ---: |
| Artifact default | 0.111 | 0.111 | 0.111 | 0.333 | 0.121 |
| Artifact `fit_desc` | 0.000 | 0.111 | 0.111 | 0.111 | 0.028 |
| `BM25F` | 0.000 | 0.111 | 0.222 | 0.333 | 0.059 |
| `TF-IDF` cosine | 0.000 | 0.000 | 0.000 | 0.222 | 0.012 |

Three results are evident from Table 3. First, exact source-journal recovery remains difficult for all methods under sparse metadata. Second, the default artifact is substantially better than sorting directly by the `abstract fit` percentage. Third, `BM25F` is competitive but still weaker than the default artifact on mean reciprocal rank, which suggests that the artifact places successful cases earlier in the ranking when it succeeds.

The strongest exact-source success is *Management Systems in Production Engineering*, which appears at rank 1 for a long Industry 4.0 and SME-manufacturing abstract. Two additional source journals enter the top 30 but not the top 10: *International Journal of Information Management Data Insights* and *Journal of Industrial Engineering and Management*. The remaining six source journals are not retrieved in the top 30, indicating that exact venue recovery remains a demanding objective under the current metadata regime.

From an applied perspective, these exact-source figures should be read carefully. A Recall@30 of 0.333 does not indicate that the artifact fails two-thirds of the time in any practical sense. It indicates that two-thirds of the benchmark cases do not return the original source journal within the first 30 positions. In a strict benchmarking context, that is counted as failure. In a real author workflow, however, some of those cases may still contain operationally useful journals in the upper ranks. The value of the metric lies in showing that source-venue identity remains difficult to recover when journal-side evidence is sparse. This is why the exact-source benchmark is informative even when its raw scores are modest.

The contrast between the default ranking and `fit_desc` is especially revealing. The two methods operate over the same underlying artifact and differ mainly in the final ordering logic. Yet their performance diverges substantially. This suggests that the explanation-oriented `abstract fit` signal does contain meaningful local information, but that local information does not aggregate into a strong global ranking rule. This finding strengthens the study because it shows that not every intuitively appealing score is a good optimization target.

### Cross-domain relevance results

Table 4 presents the results of Benchmark B and shifts the evaluation focus from source-journal recovery to shortlist usefulness across multiple topical profiles. Whereas Benchmark A asks whether the artifact can recover the exact journal that originally published a comparable abstract, Benchmark B asks whether the ranked output remains practically valuable when judged by graded topical relevance. This table is therefore important for interpreting the artifact as a publication-support tool rather than as a single-label classifier, because in real submission planning several journals may be defensible candidates even when the original source venue is not recovered.

Table 4. Cross-domain relevance benchmark results

| Method | Relevant Hit@5 | Relevant Hit@10 | Relevant mean reciprocal rank | nDCG@10 | Exact-source Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Artifact default | 0.833 | 1.000 | 0.667 | 0.797 | 0.167 |
| Artifact `fit_desc` | 0.333 | 0.667 | 0.375 | 0.458 | 0.000 |
| `BM25F` | 1.000 | 1.000 | 0.694 | 0.828 | 0.000 |
| `TF-IDF` cosine | 0.500 | 0.833 | 0.563 | 0.758 | 0.000 |

The cross-domain results show a different pattern from Benchmark A. The default artifact remains strong, reaching Relevant Hit@10 of 1.000 and nDCG@10 of 0.797, but `BM25F` slightly exceeds it on broad relevance. The result is important because it prevents overstatement: the artifact does not dominate strong fielded lexical retrieval in all settings. Instead, the evidence suggests complementary strengths between the artifact and `BM25F`.

The weakest configuration again is `fit_desc`, confirming that the displayed fit signal is better treated as explanation rather than as the main ranking objective. `TF-IDF` performs better on the broader relevance benchmark than on exact-source retrieval, but it still trails both the default artifact and `BM25F`.

The graded relevance benchmark is also useful for understanding the operational meaning of the artifact. Every one of the six benchmark cases contains at least one relevant journal within the top 10 under the default artifact, and five of the six contain a relevant journal within the top 5. For publication planning, that behavior is significant. It means that the artifact can usually generate a shortlist worth inspecting further, even if it cannot guarantee recovery of the exact venue that originally published a similar article. This is much closer to the real use case of a manuscript-routing aid than a single-label classification objective would be.

The cross-benchmark comparison also clarifies a deeper methodological point. The artifact appears to add most value when the recommendation problem depends on preserving highly specific phrase-level and concept-level signals, as in the exact-source benchmark. `BM25F`, by contrast, appears strongest when the task is to surface broad domain-relevant journals. This suggests that sparse-metadata recommendation may require different scoring emphases depending on whether the user's objective is exploratory discovery or narrow venue targeting. A practical system may eventually need to expose both behaviors in a controlled and interpretable way.

### Failure patterns

Table 5 summarizes the main failure patterns observed across the benchmarks and helps explain why performance remains uneven under sparse metadata constraints. The table should be read not as a list of isolated errors, but as an analytic map of the structural conditions under which ranking quality degrades. This is important because the study aims to identify the boundary of useful recommendation, not merely to report aggregate scores without explaining the mechanisms behind weaker cases.

Table 5. Main failure patterns under sparse metadata

| Failure pattern | Observed effect | Likely cause | Implication |
| --- | --- | --- | --- |
| Broad journals outrank narrower outlets | Source journal absent from top 30 | Generic lexical overlap remains competitive | Stronger specificity cues are needed |
| Narrow exact-source journals are under-ranked | Relevant alternatives dominate top ranks | Sparse journal metadata expose insufficient unique scope cues | Richer public journal-side text would likely help |
| `fit_desc` promotes local maxima | Overall ranking quality declines | Local explanatory fit is not a reliable global sorting objective | Fit should remain explanatory |
| Exact-source scoring treats useful alternatives as failures | Practical usefulness is understated | More than one journal may be plausibly suitable | Exact-source metrics should be complemented by graded relevance |

These results indicate that sparse-metadata journal discovery is not a trivial lexical task. It behaves differently depending on whether the evaluation target is exact venue recovery or relevance-oriented support.

Another important result is the absence of any trivial winner across all evaluation settings. If the artifact had dominated both exact-source recovery and cross-domain relevance, the scientific interpretation would have been simpler but less informative. Instead, the current evidence reveals a more realistic pattern of trade-offs. Specialized sparse-metadata logic appears useful for certain ranking objectives, while strong fielded lexical retrieval remains difficult to displace in others. For applied research, this is a stronger contribution than a single optimistic headline because it identifies where additional engineering complexity pays off and where simpler retrieval remains adequate.

### Practical interpretation of ranking depth

One additional way to read the results is through ranking depth rather than only through metric labels. In author workflows, the first three to ten results usually receive the most attention. A shortlist that becomes useful only at rank 25 or rank 30 is not useless, but it is less operationally efficient than one that surfaces strong candidates earlier. This is why mean reciprocal rank remains important in the present study. It captures not only whether the artifact eventually finds something relevant, but also how soon that relevance becomes visible to the user. The artifact's advantage over `BM25F` on the exact-source benchmark is therefore not a trivial numerical detail; it suggests that the field-aware design helps place successful cases earlier when the journal-side metadata happen to contain sufficiently distinctive cues.

The same reasoning applies to the cross-domain benchmark. A Relevant Hit@10 of 1.000 indicates that every case produced at least one relevant journal in the first ten results, but the difference between a hit at rank 1 and a hit at rank 9 remains meaningful in practice. When authors are exploring potential outlets under time pressure, early-rank visibility reduces cognitive load and supports more efficient manual screening. The metrics reported in the present article should therefore be interpreted as indicators of shortlist usability, not merely abstract ranking statistics. This perspective also helps explain why the artifact's current performance can be useful to authors even though the exact-source benchmark remains modest.

**[Figure 6 placeholder]**
**Caption:** Comparative benchmark performance of the artifact, `fit_desc`, `BM25F`, and `TF-IDF`.
**Nano Banana prompt:** Create a clean white-background scientific chart figure with no title or header. Use two side-by-side grouped bar charts. The left chart is labeled `Exact-source benchmark` and shows `R@30` and `MRR` for `Artifact default`, `Artifact fit`, `BM25F`, and `TF-IDF`. The right chart is labeled `Cross-domain relevance benchmark` and shows `Hit@10`, `MRR`, and `nDCG@10` for the same four methods. Use clear English axis labels, a restrained palette such as charcoal, muted blue, teal, and light gray, and ensure all labels are large enough for publication reproduction.

## Discussion

The results show that a browser-executed journal discovery artifact can remain useful even when restricted to sparse public metadata, but that usefulness must be interpreted carefully. The strongest conclusion is not that the artifact predicts the correct journal in a universal sense. Rather, it can surface a defensible shortlist of relevant venues, which is often the practically important first step in publication planning.

This result is particularly relevant for researchers seeking target journals for publication. A tool of this kind can reduce the initial search burden by rapidly moving from one abstract to a plausible venue shortlist. It can also help authors test whether their own implicit assumptions about journal fit are too narrow or overly influenced by familiar outlets. For early-career researchers, interdisciplinary researchers, and authors entering a new topic area, this support may be especially valuable because journal landscapes are rarely transparent to newcomers.

The evidence also clarifies why the default artifact behaves better than `fit_desc`. The `abstract fit` percentage is locally interpretable and useful for user understanding, but it does not function well as a global ranking objective. When the artifact is sorted directly by fit, narrow local overlaps receive too much emphasis. This aligns with explainable recommendation theory, which distinguishes between explanation and ranking optimization (Benleulmi et al., 2025; Sana and Shoaib, 2022). The present results show that the distinction is not merely conceptual; it materially affects recommendation quality.

The comparison with `BM25F` is equally important. A weaker study could have overstated the artifact's performance by comparing it only with simplistic baselines. The current results show a more nuanced pattern. The artifact performs better on the exact-source benchmark, suggesting that phrase handling, concept normalization, and breadth correction add value when precise scope cues matter. However, `BM25F` remains slightly stronger on broader cross-domain relevance. This means the artifact's contribution is conditional rather than universal. That conditionality should be treated as a scientific insight rather than a weakness because it clarifies when specialized sparse-metadata logic is worth the added complexity.

The findings also support the argument that metadata quality is part of the scientific problem, not a background inconvenience. When the journal-side profile remains limited to a title and a few taxonomic descriptors, even a strong ranking model will eventually encounter an accuracy ceiling. This interpretation is consistent with broader metadata research showing that public information structures constrain discovery and evaluation (Linkert et al., 2010; Haupt et al., 2026). The same point appears in related scholarly routing tasks. Reviewer-assignment research repeatedly encounters bottlenecks caused by data fragmentation and limited open scholarly evidence (Ribeiro, Sizo and Reis, 2026). Recommendation studies over constrained public resources likewise show that user-facing quality depends on the interaction between metadata structure and ranking logic (Yang, 2025).

Another important implication concerns deployment. The artifact's usefulness is not only algorithmic. It is also infrastructural. Because ranking occurs locally in the browser after static data loading, the system can be used for unpublished abstracts without dependence on a remote inference endpoint. This creates a practical privacy advantage for authors who do not want to transmit manuscript abstracts to third-party services. It also means the artifact can be deployed in institutions with limited technical infrastructure, which broadens access to publication-support tools.

The findings are also relevant to supervisory and institutional workflows. The artifact can serve as an advisory tool in manuscript-development meetings, research-office support services, writing clinics, and library-based publishing guidance. In these settings, the tool is not a substitute for expert judgment. Instead, it acts as a structured discovery aid that supports faster discussion around topical fit, indexing, and shortlist quality. That broader applicability strengthens the applied value of the study beyond individual author use.

The study also has implications for how authors conceptualize journal fit. In many publication workflows, fit is treated informally as a combination of topic familiarity and journal prestige cues. The present artifact operationalizes fit more concretely as observable overlap between abstract content and exposed journal scope signals. Even though this operationalization is imperfect, it introduces a discipline that can improve author reflection. Instead of asking only whether a journal is well known or personally familiar, the user is encouraged to ask whether the abstract's main technical and domain cues are actually represented by the journal's public profile. In practice, this can improve the quality of the initial shortlist even when the final decision remains human-led.

At the same time, the study has clear limitations. The exact-source benchmark is small and concentrated in specific application domains. The cross-domain benchmark remains profile-guided rather than manually judged. The artifact also lacks richer journal-side text such as aims-and-scope descriptions and article-title histories, which likely cap exact-source performance. These limitations mean that the present article supports a usefulness claim more strongly than a universal accuracy claim.

Several additional validity threats should also be recognized. First, the source-journal benchmark may contain cases where the original journal was chosen for reasons not fully visible in the abstract, such as audience, editorial history, or prior publication patterns. In such cases, even a stronger metadata-based recommender might not recover the source venue reliably. Second, the profile-guided relevance benchmark uses a structured automatic rubric rather than expert manual judgment. Although this improves consistency, it may also smooth over disciplinary nuances that human judges would detect. Third, the artifact operates on a fixed journal snapshot. Journal coverage, classification, and metadata quality are time-sensitive, which means that the evaluation captures one reliable snapshot rather than a permanently stable population.

### Research limitation and implication

The study's main research limitation is therefore not a software defect, but an evidence boundary. Benchmark A contains only nine exact-source cases and is concentrated in a narrow problem family around SME digitalization, Industry 4.0, and related manufacturing-management themes. Benchmark B broadens the domain range, but its relevance labels are still profile-guided rather than manually adjudicated by subject experts. This means that the present article can defend a usefulness claim more strongly than a universal accuracy claim. The implication is methodological as much as substantive: under sparse public metadata, evaluation must remain explicit about which construct is being tested and how much evidential weight the benchmark can bear.

A further implication is methodological. The repository now contains a manual relevance package designed to strengthen the next evaluation cycle. Completing that package with human judgments and inter-rater agreement would make it possible to test the artifact more rigorously against both `BM25F` and `TF-IDF`, and to evaluate the contribution of each scoring component under a fixed gold-label setting. That next stage should ideally include three improvements. The first is human grading by at least two knowledgeable raters, followed by adjudication and agreement reporting. The second is a broader case pool that covers more disciplinary variation and abstract styles. The third is controlled component ablation so that phrase handling, concept expansion, alignment scoring, and breadth correction can be tested independently under the same labeled benchmark. Without those steps, it would be premature to claim that any one component is definitively responsible for the observed gains. With those steps, however, the artifact could become the basis of a much stronger comparative manuscript on sparse-metadata recommendation.

An equally important methodological implication concerns the relationship between evaluation rigor and deployment realism. Many recommendation studies prioritize predictive strength under curated conditions, whereas many practical tools prioritize ease of deployment without carefully documenting their evaluation assumptions. The present study argues that these two priorities should be treated together. A journal-selection aid should be judged not only by how highly it scores on a benchmark, but also by whether its evidence base matches the constraints under which it will actually be used. In the current case, that means maintaining the sparse public-metadata condition in both the artifact and the baselines, avoiding inferential statistics that the sample design cannot support, and interpreting results in terms of shortlist usefulness as well as strict source recovery. This integrated view of rigor is especially important for applied research because real users interact with deployed systems, not with idealized offline models.

### Practical implication

The practical implication is supported directly by the benchmark evidence. In Table 4, the default artifact reaches Relevant Hit@10 of 1.000 and Relevant Hit@5 of 0.833, which means that every cross-domain test case yields at least one relevant journal in the first ten results and five of the six cases yield a relevant journal in the first five. For author workflows, this is a meaningful outcome because journal discovery is usually a shortlist-generation task before it becomes a final submission decision. The artifact can therefore help researchers move from a raw abstract to a manageable first set of candidate venues, reducing the time spent screening clearly unsuitable journals and making early routing decisions more systematic.

The practical value is not confined to individual authors. The same shortlist behavior can support supervisors, journal-selection workshops, library publishing services, and research offices that routinely advise authors on scope fit and publication planning. Because the evidence shows that the artifact is more reliable as a shortlist aid than as an exact-source predictor, the most defensible practical claim is that it supports structured early filtering rather than automatic venue selection. That is still a consequential contribution, because many publication delays and poor submission decisions arise during this early filtering stage.

### Social implication

The social implication follows from the artifact's infrastructure model as well as its ranking results. As Table 1 shows, the system is distributed as static browser-consumable assets, with ranking executed locally after loading the shard files rather than through a remote inference service. This design reduces the need to transmit unpublished abstracts to third-party systems and therefore supports a more privacy-conscious form of manuscript exploration. For authors working with not-yet-submitted manuscripts, especially in competitive or confidential research settings, this is a non-trivial operational safeguard.

There is also an access implication. Because the artifact runs without backend inference and uses public metadata, it can be adopted in institutions that lack advanced research-information infrastructure or subscription-based recommendation services. In such settings, the tool can narrow information asymmetries between highly networked researchers and those with less institutional support. There is also a broader implication for research support ecosystems. Publication guidance is often fragmented across supervisors, peers, library services, indexing tools, journal websites, and informal social knowledge. A lightweight recommendation artifact does not replace these resources, but it can improve coordination among them by producing a structured starting point. In institutions where formal publication-support infrastructure is limited, such a system may help narrow the gap between experienced and less experienced researchers by making early journal discovery more systematic. In better-resourced settings, the same tool can function as a complementary screening layer that accelerates advisory workflows. These institutional implications matter because they reinforce the practical value of studying low-infrastructure recommendation artifacts rather than assuming that all useful scholarly recommendation must depend on heavyweight semantic services.

### Originality and value

The originality of the study does not rest on claiming the most accurate recommender overall. Its value lies in defining and evaluating a narrower, but underexplored, problem setting: abstract-to-journal recommendation under severe journal-side metadata sparsity and deployment-realistic constraints. Within that setting, the article contributes four elements in combination. First, it formalizes a field-aware and interpretable ranking design that separates global ranking from the locally displayed `abstract fit` explanation. Second, it evaluates that design against fair `BM25F` and `TF-IDF` baselines that use the same sparse fields rather than richer external corpora. Third, it adopts a dual benchmark logic that distinguishes exact-source recovery from graded shortlist usefulness. Fourth, it keeps the evaluation tied to a deployable browser artifact rather than to an offline-only prototype.

That combination is where the study's value is strongest. The evidence in Tables 3 and 4 shows that the artifact is not universally dominant, but it also shows that specialized sparse-metadata logic can outperform simpler alternatives on exact-source recovery while remaining competitive on broader relevance. This produces a more scientifically useful contribution than a broad but weakly supported superiority claim. Overall, the study contributes to applied research by showing that a lightweight, interpretable, and publicly deployable journal-selection aid can still deliver meaningful decision-support value under severe metadata constraints. That is a narrower contribution than a high-resource semantic recommender would make, but it is also a more deployment-realistic one for many research environments.

**[Figure 7 placeholder]**
**Caption:** Failure-mode and use-case map for sparse-metadata journal recommendation.
**Nano Banana prompt:** Create a white-background analytical diagram with no title or header. Show a 2x2 matrix with horizontal axis `Metadata specificity` from `low` to `high` and vertical axis `Query specificity` from `low` to `high`. Label the quadrants `Broad journals dominate`, `Useful shortlist ranking`, `Exact-source recovery more likely`, and `Vocabulary mismatch risk`. Add small side annotations reading `Artifact default stronger on exact-source` and `BM25F strong on broad relevance`. Use thin lines, black text, and subtle muted blue-gray highlight boxes only.

## Conclusion

This study evaluated an interpretable field-aware retrieval artifact for abstract-to-journal recommendation under sparse metadata conditions. The artifact uses only journal-side `Title`, `Categories`, and `Areas` fields at ranking time, and combines fielded lexical overlap, phrase-aware matching, bounded concept expansion, alignment scoring, and breadth correction. The results show that useful journal-discovery support remains possible even under these severe constraints.

The contribution of the study is threefold. First, it demonstrates that browser-executed, static, and inspectable journal recommendation can support publication-venue shortlisting without backend inference or private corpora. Second, it shows that explanation and ranking should be separated: the local fit signal helps interpretation, but it should not serve as the default sorting objective. Third, it provides a fair comparison against `BM25F` and `TF-IDF`, showing that the artifact adds value in exact-source recovery while `BM25F` remains highly competitive on broad relevance.

The practical implication is clear. Researchers can use the artifact to identify plausible target journals, reduce early scope-mismatch screening effort, and support more efficient publication planning from the abstract stage onward. However, the current evidence also shows that exact source-journal recovery remains modest and that stronger human-labeled benchmarking is still needed before broader accuracy claims can be defended. Future work should therefore focus on manual relevance labeling, richer but still public journal metadata, and component-level ablation under a fixed gold-label benchmark.

## Acknowledgment

The authors acknowledge the value of open scholarly metadata infrastructures and public indexing resources that made the construction and evaluation of the artifact possible. The authors also acknowledge informal academic feedback received during manuscript refinement and internal review of the evaluation logic.

## Conflict of Interest

The authors declare that there is no conflict of interest regarding the publication of this study.

## Funding

This research received no external funding support.

## AI Disclosure

Artificial intelligence tools were used only to support data analytics and language refinement during the preparation of the manuscript. All research design decisions, data selection, benchmark interpretation, methodological validation, and final writing judgments were reviewed and approved by the authors. No AI tool was used as an autonomous author or as a substitute for human responsibility over the study's claims.

## References

Alzanin, S.M., Azmi, A.M. and Aboalsamh, H.A. (2022) 'Short text classification for Arabic social media tweets', *Journal of King Saud University - Computer and Information Sciences*, 34, pp. 6595-6604.

Bayraktar, M.Y. and Kaya, M. (2023) 'Author-profile-based journal recommendation for a candidate article: Using hybrid semantic similarity and trend analysis', *IEEE Access*, 11. Available at: https://doi.org/10.1109/ACCESS.2023.3271732.

Benleulmi, M., Gasmi, I., Azizi, N. and Dey, N. (2025) 'Explainable AI and deep learning models for recommender systems: State of the art and challenges', *Journal of Universal Computer Science*, 31(4), pp. 383-421.

Colangelo, M.T., Meleti, M., Guizzardi, S., Calciolari, E. and Galli, C. (2025) 'A comparative analysis of sentence transformer models for automated journal recommendation using PubMed metadata', *Big Data and Cognitive Computing*, 9(3), art. 67. Available at: https://doi.org/10.3390/bdcc9030067.

Edelman, B. and Skolnick, J. (2025) 'Valsci: an open-source, self-hostable literature review utility for automated large-batch scientific claim verification using large language models', *BMC Bioinformatics*, 26, art. 140. Available at: https://doi.org/10.1186/s12859-025-06159-4.

Entrup, E., Eppelin, A., Ewerth, R., Wohlgemuth, M., Hoppe, A., Hartwig, J. and Tullney, M. (2024) 'Comparing different search methods for the open access journal recommendation tool B!SON', *International Journal on Digital Libraries*, 25, pp. 505-516. Available at: https://doi.org/10.1007/s00799-023-00372-3.

Gu, Z., Cai, Y., Wang, S., Li, M., Qiu, J., Su, S., Du, X. and Tian, Z. (2020) 'Adversarial attacks on content-based filtering journal recommender systems', *Computers, Materials & Continua*, 64(3), pp. 1755-1770.

Haupt, F., Senge, J.F., von Tengg-Kobligk, H. and Bosbach, W.A. (2026) 'Enabling transparent research evaluation: A method for historical RCR retrieval using public NIH metadata', *PLoS One*, 21(1), art. e0340697. Available at: https://doi.org/10.1371/journal.pone.0340697.

Hernandez, R.G., Hernandez, R.L. and Bueno, N.F. (2025) 'Decision support system on faculty profiling using full-text search algorithm: A tool for evaluating faculty performances', *Journal Europeen des Systemes Automatises*, 58(4), pp. 689-700. Available at: https://doi.org/10.18280/jesa.580403.

Linkert, M., Rueden, C.T., Allan, C., Burel, J.-M., Moore, W., Patterson, A., Loranger, B., Moore, J., Neves, C., Macdonald, D., Tarkowska, A., Sticco, C., Hill, E., Rossner, M., Eliceiri, K.W. and Swedlow, J.R. (2010) 'Metadata matters: access to image data in the real world', *Journal of Cell Biology*, 189(5), pp. 777-782. Available at: https://doi.org/10.1083/jcb.201004104.

Liu, J., Castillo-Cara, M. and Garcia-Castro, R. (2025) 'On the significance of graph neural networks with pretrained transformers in content-based recommender systems for academic article classification', *Expert Systems*, 42, art. e70073. Available at: https://doi.org/10.1111/exsy.70073.

Miyachi, Y., Ishii, O. and Torigoe, K. (2023) 'Design, implementation, and evaluation of the computer-aided clinical decision support system based on learning-to-rank: collaboration between physicians and machine learning in the differential diagnosis process', *BMC Medical Informatics and Decision Making*, 23, art. 26. Available at: https://doi.org/10.1186/s12911-023-02123-5.

Patel, V., Ramanna, S., Kotecha, K. and Walambe, R. (2022) 'Short text classification with tolerance-based soft computing method', *Algorithms*, 15(8), art. 267. Available at: https://doi.org/10.3390/a15080267.

Patil, S. and Aalam, Z. (2025) 'An AI-enhanced system for context-aware information retrieval and summarization in AI-assisted learning', *SSRG International Journal of Electronics and Communication Engineering*, 12(8), pp. 307-315. Available at: https://doi.org/10.14445/23488549/IJECE-V12I8P127.

Ren, S., Zheng, X., Zhao, J., Du, J., Zhang, Y., Bi, C., Song, J., Zhang, J., Lang, H., Zhang, F. and Shen, B. (2026) 'Knowledge-guided explainable recommendation tool for cancer risk prediction models using retrieval-augmented large language models: Development and validation study', *JMIR Medical Informatics*, art. 78519.

Ribeiro, A.C., Sizo, A. and Reis, L.P. (2026) 'Investigating the reviewer assignment problem: A systematic literature review', *Journal of Information Science*, 52(1), pp. 39-59. Available at: https://doi.org/10.1177/01655515231176668.

Sana, S. and Shoaib, M. (2022) 'Trustworthy explainable recommendation framework for relevancy', *Computers, Materials & Continua*. Available at: https://doi.org/10.32604/cmc.2022.028046.

Tussupov, J., Kassymova, A., Mukhanova, A., Bissengaliyeva, A., Azhibekova, Z., Yessenova, M. and Abuova, Z. (2025) 'Analysis of short texts using intelligent clustering methods', *Algorithms*, 18(5), art. 289. Available at: https://doi.org/10.3390/a18050289.

Walters, W.H. (2025) 'Comparing conventional and alternative mechanisms of discovering and accessing the scientific literature', *Proceedings of the National Academy of Sciences of the United States of America*, 122, art. e2503051122.

Wang, K., Reimers, N. and Gurevych, I. (2024) 'DAPR: A benchmark on document-aware passage retrieval', in *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics, Volume 1: Long Papers*, pp. 4313-4330.

Yang, Y. (2025) 'Intelligent recommendation of information resources in university libraries based on fuzzy logic and deep learning', *International Journal of Computational Intelligence Systems*. Available at: https://doi.org/10.1007/s44196-025-00993-3.

Yanping, X. and Weiye, Y. (2024) 'A quantitative evaluation of the application of online database systems and information communication in academic research', *Profesional de la Informacion*, 33(6), e330617. Available at: https://doi.org/10.3145/epi.2024.ene.0617.

Zamani, H., Mitra, B., Song, X., Craswell, N. and Tiwary, S. (2018) 'Neural ranking models with multiple document fields', in *Proceedings of the Eleventh ACM International Conference on Web Search and Data Mining*. Available at: https://doi.org/10.1145/3159652.3159730.

Zhang, Z., Roberts, K., Patra, B.G., Cao, T., Wu, H., Yaseen, A., Zhu, J. and Sabharwal, R. (2023) 'Scholarly recommendation systems: a literature survey', *Knowledge and Information Systems*, 65, pp. 4433-4478. Available at: https://doi.org/10.1007/s10115-023-01901-x.

## Appendix. Glossary of Key Terms

| Term | Explanation |
| --- | --- |
| Abstract-to-journal recommendation | The task of using a manuscript abstract as the main query input to generate a ranked list of candidate journals for possible submission. |
| Abstract fit | A locally displayed percentage in the artifact that summarizes how strongly the abstract overlaps with the journal profile, used as an interpretive cue rather than the default global ranking objective. |
| Alignment scoring | A scoring component that rewards agreement between the specific content emphasized in the abstract and the specific signals exposed by the journal metadata. |
| Benchmark A | The exact-source benchmark in which success is defined as recovering the original journal that published the source abstract within the ranked result list. |
| Benchmark B | The cross-domain relevance benchmark in which success is defined by graded topical usefulness of the returned shortlist rather than by exact source-journal recovery alone. |
| BM25F | A fielded lexical retrieval baseline that extends BM25 by allowing different document fields to contribute with different weights and length-normalization behavior. |
| Breadth-aware penalty | A penalty term used to reduce the tendency of broad journals to rank too highly when their overlap with the abstract is mostly generic rather than specific. |
| Browser-side ranking | A deployment mode in which query processing and ranking occur locally in the user's browser after the static search assets have been loaded. |
| Construct validity | The degree to which the benchmark actually measures the intended evaluation target, such as exact-source recovery versus shortlist usefulness. |
| Deployment realism | The principle that a recommender should be evaluated under the same data and operational constraints that shape its real use in practice. |
| DOAJ enrichment | Supplementary journal metadata from the Directory of Open Access Journals used to enhance the artifact's public journal profiles and benchmarking context. |
| Exact-source retrieval | A strict evaluation construct in which the original publication venue is treated as the single correct answer for a benchmark abstract. |
| Field-aware retrieval | A retrieval design that treats `Title`, `Categories`, and `Areas` as distinct evidence sources rather than collapsing them into one undifferentiated text field. |
| Graded relevance | An evaluation construct in which multiple journals can be counted as useful outcomes if they align with the topic and scope of the abstract to different degrees. |
| Mean reciprocal rank | A ranking metric that gives higher value when the first relevant or correct result appears closer to the top of the ranked list. |
| nDCG@10 | Normalized discounted cumulative gain at rank 10, a metric that rewards highly ranked relevant results while accounting for graded relevance levels. |
| Sparse metadata | A condition in which the journal-side textual evidence is limited to short public fields such as title, categories, and subject areas rather than rich descriptive corpora. |
| TF-IDF cosine similarity | A lexical baseline that represents queries and journal profiles as weighted term vectors and ranks them using cosine similarity. |
| Web of Science subset | The indexed portion of the journal corpus used in the artifact to indicate which journals are linked to the aligned Web of Science snapshot. |
