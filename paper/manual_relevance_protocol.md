# Manual Relevance Benchmark Protocol

This protocol accompanies [manual_relevance_benchmark_template.csv](/Users/ikhwanarief/Documents/GitHub%20Repositories/Journal_Discovery/paper/manual_relevance_benchmark_template.csv).

## Purpose

The template is designed to convert the current DOAJ-based development benchmark into a manually judged graded-relevance benchmark suitable for a stronger manuscript submission. Each row represents one candidate journal proposed for a seed article abstract by at least one ranking method:

- the current `Journal Discovery` default ranking,
- the `BM25F` baseline,
- the `TF-IDF` baseline.

The current template contains:

- `6` seed cases (`MR-01` to `MR-06`)
- `136` candidate-judgment rows

## Manual grading rubric

Use `manual_grade` with the following values:

- `3` = exact source journal
- `2` = strongly relevant target journal
  The journal title/categories/areas indicate a clear fit for the article's main problem, method, or disciplinary outlet.
- `1` = partially relevant journal
  The journal is adjacent or broadly related, but not a strong target venue for the article as written.
- `0` = not relevant
  The journal is off-topic, too generic, or mismatched in disciplinary scope.

Use `manual_decision` for a short qualitative label such as:

- `exact`
- `strong-fit`
- `partial-fit`
- `off-target`

Use `manual_notes` for brief rationale, for example:

- `Good topical fit but too broad`
- `Correct domain but method mismatch`
- `Exact venue`
- `General AI journal, weak operations focus`

## Recommended labeling workflow

1. Review one `case_id` at a time.
2. Read the `source_article_title`, `source_journal`, and `abstract`.
3. Inspect the `candidate_journal`.
4. Use `app_default_rank`, `bm25f_rank`, and `tfidf_rank` only as provenance, not as evidence of relevance.
5. Assign `manual_grade`, `manual_decision`, and `manual_notes`.

## Recommended quality controls

For a more defensible benchmark:

1. Use at least two independent raters.
2. Resolve disagreements through adjudication.
3. Report inter-rater agreement before computing final metrics.
4. Freeze the labeled CSV before running the final benchmark metrics reported in the paper.
