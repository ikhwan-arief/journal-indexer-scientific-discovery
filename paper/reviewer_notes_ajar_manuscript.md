# Reviewer Notes for the AJAR Manuscript

Reviewed file: `paper/Interpretable Field-Aware Retrieval for Abstract-to-Journal Recommendation with Sparse Metadata - AJAR.docx`

Review basis:
- Assessed against the current *African Journal of Applied Research* author-guideline pattern and article presentation style.
- Focused on scientific quality, reporting rigor, coherence, and journal-fit.
- Conducted from direct DOCX text extraction; this is a content review, not a full visual pagination audit.

## Overall assessment

The manuscript is broadly aligned with the journal's expected structure. It already has a structured abstract, a clear applied-research orientation, recent references, explicit limitations, and a reasonably strong discussion of practical and social implications. The topic also fits the journal's interdisciplinary applied-research profile because it addresses a real decision-support problem with a deployable artifact and empirical evaluation.

My recommendation is **major revision before submission**. The main reason is not topic mismatch. The main reason is that several reporting elements still need strengthening before the article will read as a fully defensible applied-research paper for this journal. The most important gaps concern benchmark reproducibility, parameter transparency, explicit in-text figure citation, and one coherence issue in the DOCX disclosure statement.

## Strengths

1. The structured abstract already follows the journal's pattern closely and communicates purpose, method, findings, limitations, and value clearly.
2. The manuscript avoids strong overclaiming better than many recommender-system papers and explicitly acknowledges the limits of sparse metadata.
3. The inclusion of both `BM25F` and `TF-IDF` strengthens the fairness of comparison.
4. The discussion section is applied, readable, and generally well connected to publication-planning use cases.

## Required revisions

### 1. Add explicit in-text figure callouts

Section: multiple sections across the manuscript  
Target paragraph first 5 words:
- `The study also adopts a`
- `This distinction matters theoretically because`
- `The research instrument used for`
- `This score is displayed as`
- `In addition to software verification,`
- `The same reasoning applies to`
- `That combination is where the`

Why this needs revision:  
AJAR's author guideline checklist expects all figures and tables to be cited in the text. The tables are already introduced explicitly, but the figures are mostly inserted without a formal sentence in the running text that tells the reader what the figure contributes.

Suggested sentences to insert:

For Figure 1, add after the paragraph beginning `The study also adopts a`:
`Figure 1 situates the artifact within the broader publication-decision workflow that motivates the study.`

For Figure 2, add after the paragraph beginning `This distinction matters theoretically because`:
`Figure 2 summarizes the conceptual difference between exact-source recovery and graded relevance, which underpins the article's dual evaluation logic.`

For Figure 3, add after the paragraph beginning `The research instrument used for`:
`Figure 3 shows how the public metadata sources are transformed into browser-side assets and how the deployed ranking interface operates without backend inference.`

For Figure 4, add after the paragraph beginning `This score is displayed as`:
`Figure 4 visualizes the interaction among normalization, field-aware matching, phrase handling, concept expansion, and the explanatory fit signal.`

For Figure 5, add after the paragraph beginning `In addition to software verification,`:
`Figure 5 outlines the full evaluation workflow, including the relationship between the two benchmarks, the lexical baselines, and the planned manual-label extension.`

For Figure 6, add after the paragraph beginning `The same reasoning applies to`:
`Figure 6 provides a compact visual comparison of the main benchmark outcomes across the artifact and the lexical baselines.`

For Figure 7, add after the paragraph beginning `That combination is where the`:
`Figure 7 summarizes the main boundary conditions under which sparse-metadata recommendation is most and least reliable.`

### 2. Explain how the ranking weights were chosen

Section: `Research Methods -> Query processing and ranking model`  
Target paragraph first 5 words: `The token term is field-aware.`

Why this needs revision:  
The scoring formula is described clearly, but the article does not state how the weights and coefficients were set. A reviewer will reasonably ask whether these numbers were tuned on the evaluation benchmarks, selected heuristically, or inherited from earlier development. Without that clarification, the separation between system construction and evaluation remains under-explained.

Suggested sentence to add after the paragraph:
`These field weights and coefficients were fixed during pre-benchmark artifact development through heuristic engineering trials and were not optimized on Benchmark A or Benchmark B, so the reported configuration should be interpreted as a transparent deployable setting rather than as a benchmark-tuned optimum.`

### 3. Make Benchmark A reproducible

Section: `Research Methods -> Benchmark A: Exact-source retrieval`  
Target paragraph first 5 words: `Benchmark A contains nine abstract queries`

Why this needs revision:  
The benchmark is described, but the case-selection logic is still too thin for peer review. A reader needs to know how the nine cases were chosen, what exclusion rules were applied, and whether the source journals were confirmed to exist in the evaluated corpus before scoring.

Suggested sentence to add after the paragraph:
`The nine cases were selected by purposive sampling from published PDFs that contained a clearly extractable abstract, an unambiguous source-journal identity, and a source journal present in the evaluated corpus; candidate PDFs that failed any of these conditions were excluded before benchmarking.`

### 4. Clarify exactly how Benchmark B labels were assigned

Section: `Research Methods -> Benchmark B: Cross-domain relevance benchmark`  
Target paragraph first 5 words: `Each case is graded with`

Why this needs revision:  
The rubric categories are stated, but the article does not yet explain how a journal was assigned label `2` rather than `1` in operational terms. Because Benchmark B is central to the paper's applied usefulness claim, the labeling logic needs one more sentence of procedural clarity.

Suggested sentence to add after the rubric:
`For the present benchmark, labels were assigned deterministically from the published profile rubric: label 2 required direct alignment between the journal's exposed scope signals and the dominant topic-application combination of the abstract, label 1 indicated only partial topical overlap, and these judgments should be interpreted as development-stage relevance labels rather than expert gold-standard ratings.`

### 5. Report the baseline configuration more precisely

Section: `Research Methods -> Baselines`  
Target paragraph first 5 words: `Two fair lexical baselines were`

Why this needs revision:  
The baselines are appropriate, but the manuscript still does not disclose enough implementation detail for close replication. A strong reviewer will want to know whether `BM25F` and `TF-IDF` shared the same preprocessing, field weighting, and normalization assumptions.

Suggested sentence to add after the paragraph beginning `Baseline fairness was treated as`:
`Both baselines used the same tokenization and stop-word pipeline as the artifact, while field contributions were constrained to the same three journal-side fields so that performance differences reflected ranking logic rather than unequal access to metadata.`

### 6. Make the non-superiority claim even more explicit in the conclusion

Section: `Conclusion`  
Target paragraph first 5 words: `The contribution of the study`

Why this needs revision:  
The discussion is reasonably balanced, but the conclusion still needs one sharper sentence stating that the artifact is not the strongest method for every evaluation goal. This will help the paper read as more scientifically disciplined and better aligned with AJAR's expectation of clear applied interpretation.

Suggested sentence to add after the paragraph:
`Taken together, the evidence supports positioning the artifact as an interpretable shortlist-generation aid that is strongest on exact-source prioritization and deployment realism, while `BM25F` remains the stronger lexical option for broad cross-domain relevance.`

### 7. Improve coherence between the theory section and the literature review

Section: between `Theories Underpinning Study` and `Literature Review`  
Target paragraph first 5 words: `Recent journal recommendation studies can`

Why this needs revision:  
The manuscript is generally coherent, but the transition from theoretical framing to empirical literature review is abrupt. A short bridging sentence will make the argumentative flow smoother, especially for readers outside information retrieval.

Suggested sentence to insert immediately before the paragraph:
`Whereas the previous section defined the conceptual lenses used in the study, the following review examines how recent empirical work on journal recommendation, sparse-text retrieval, and explainable recommendation informs the present artifact.`

### 8. Correct the AI disclosure in the DOCX to match the stated author position

Section: `AI Disclosure`  
Target paragraph first 5 words: `Artificial intelligence tools were used`

Why this needs revision:  
The DOCX currently states that AI was used for `image generation based on texts`, while the latest author instruction and manuscript source indicate that AI use should be limited to data analytics and language refinement. This is a coherence and disclosure-accuracy issue and should be corrected before submission.

Suggested replacement paragraph:
`Artificial intelligence tools were used only to support data analytics and language refinement during the preparation of the manuscript. All research design decisions, data selection, benchmark interpretation, methodological validation, and final writing judgments were reviewed and approved by the authors. No AI tool was used as an autonomous author or as a substitute for human responsibility over the study's claims.`

## Optional but worthwhile revisions

### 9. Add one sentence connecting the strongest exact-source case to the scoring logic

Section: `Results -> Exact-source benchmark results`  
Target paragraph first 5 words: `The strongest exact-source success is`

Why this would help:  
This paragraph reports the strongest case, but it could do more analytic work by stating why that case was recoverable. A short explanatory sentence would strengthen the bridge from results to mechanism.

Suggested sentence to add after the paragraph:
`This case appears to be recoverable because the abstract preserves several highly specific manufacturing and systems-oriented phrases that also survive in the journal-side scope signals, allowing the field-aware scorer to exploit specificity rather than generic domain overlap.`

### 10. Make the practical scope of the tool slightly narrower and more precise

Section: `Discussion -> Practical implication`  
Target paragraph first 5 words: `The practical implication is supported`

Why this would help:  
The practical contribution is real, but the sentence can be made even more precise by emphasizing that the tool supports early-stage routing rather than final submission choice. That wording will reduce the chance of being read as overstating decision automation.

Suggested replacement sentence for the final sentence of the paragraph:
`The artifact should therefore be positioned as an early-stage routing and shortlisting aid rather than as an automated journal-selection mechanism.`

## Bottom-line reviewer recommendation

The paper is **promising and broadly journal-compatible**, but it still needs targeted revision before submission. The most important improvements are: explicit figure citation, better reproducibility detail in both benchmarks, clearer provenance for scoring parameters, stronger replication detail for the baselines, and correction of the DOCX disclosure inconsistency. If those issues are fixed, the manuscript will read as substantially more rigorous and coherent for an AJAR-style applied-research audience.
