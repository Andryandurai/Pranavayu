# Phase 5 decisions before evaluation

Phase 4's Step 0 is complete: AnalysisRun 21, migrated forecast tables, real
PHASE4.md, independent verification, and **148 passing tests**. Phase 4's frozen
method is retained. Negative skill and interval undercoverage stay in its report.

## Decisions

- Use real public documents and hash-addressed local copies. Retain failed URLs
  after two attempts; add only discovered official/institutional alternatives.
  An unavailable body has no invented SHA, page, chunk or Document row. The
  library manifest records the unavailable request separately.
- Keep physical PDF page numbers. HTML and Markdown are unpaginated: expose a
  logical page for the text endpoint, but cite their actual section heading,
  explicitly identifying an unpaginated source rather than inventing print pages.
- Use BGE-M3's own tokenizer for section chunks: 500–800 tokens, a 100-token
  overlap, and smaller section tails kept intact. Tables are separate chunks;
  oversize tables retain row/heading context across fragments. OCR uses Tesseract
  for textless PDF pages; neither OCR nor table layout is assumed error-free.
- Use BAAI/bge-m3, revision `5617a9f61b028005a4858fdac845db406aefb181`, normalized
  1024-dimensional dense vectors; PostgreSQL English full-text search; RRF k=60.
  Each first stage returns up to 40 chunks. Rerank the fused top 40 with
  BAAI/bge-reranker-v2-m3, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`,
  and retain 8. Do not fit or tune these models on the evaluation set.
- The host has 15.7 GiB RAM and measured 1.01 GiB free during the handoff;
  Docker is limited to 7.605 GiB. The user's 12 GB free-container condition for
  Ollama is not met. Neither remote API key is configured. **Extractive** is
  therefore the default answer provider; optional provider interfaces remain
  configurable. No local LLM download is required for this run.
- Isolate CPU encoder/reranker inference in one serialized service, loading one
  model at a time with small batches. Cache
  weights under the mounted `data/models/` and cache deterministic query/pair
  computations by model revision and content hash. Measure actual runtime and
  record any precision/runtime fallback before evaluation.

### Runtime correction before evaluation

The CPU exposes AVX2, with no AVX512 FP16/BF16 instructions. Float16 inference
worked but long-passage indexing was slow. Float32 was selected before evaluation:
a two-text roughly 450-word probe took 24.2308 seconds including cold load,
then 3.0209 seconds warm. Norms were within 1.1e-7 of one. Identical positions
were reproducible across the two calls; identical texts at different batch
positions differed at floating-point precision. The client therefore deduplicates
identical input text and caches one vector per content/revision/precision.
Computation caches and stored embedding fingerprints include dtype and sequence
length; float16 and float32 results are not silently mixed.

Parser version 2 corrects overfragmentation detected before freezing questions:
table cells are not prose headings, dominant body size is character-weighted,
and OCR uses text heading rules. pdfplumber page caches are released after each
page to bound memory on long reports. Original bodies and physical page numbers
remain unchanged. This is an incompatible index rebuild, not performance tuning
against evaluation scores. The once-frozen evaluation remains immutable.

### Source-text and scoring corrections before freezing

Parser version 3 rejects single-column grid detections: underlined IIT Kanpur
paragraphs had been falsely rendered as table rows, separating subscripts from
their chemical symbols. Existing version-2 documents without any such detection
have identical parser output and receive a recorded compatibility upgrade;
affected sources are reparsed. Cached vectors for unchanged text are reused.
The three affected authored questions are retained, with source text restored
rather than replacing them with easier questions. No evaluation has run yet.

Answer number correctness matches numeric values to their displayed field in
frozen actual data-tool cells. Report expected-number recall, emitted-number
precision, exact numeric cells and available-data answer coverage separately.
Unavailable-data cases require abstention and have no invented numerical target.
Scientific range/footnote brackets remain original text; internal evidence
citations use explicit E-number aliases. Each cited claim still requires exact
source text and numeric support. Final citation auditing matches the actual
emitted reference labels and re-reads the stored source rows.

Before the first benchmark, the emitted-citation audit was corrected for several
retrieved chunks sharing one human page/section label. Every associated reference
must have valid document/hash/page/retrieval identity, and a claim must occur
exactly in at least one cited chunk for that label. The regression checks both
valid same-page claims and an invalid identity. Questions, gold IDs, relevance
thresholds and retrieval designs are unchanged.

- Use validated named data tools. Raw analysis values cite their actual data run;
  normalised values cite their model run; research/forecast results cite their
  own successful AnalysisRun and model version. Never relabel raw Run 9 as Run 19.
  Missing periods, coverage gates, network scope, replay and retrospective skill
  remain explicit. No raw SQL is accepted from a question or provider.
- Generate from retrieved/tool evidence only. Verify citation identity, numeric
  support and sentence support; remove unsupported sentences and refuse when
  no relevant evidence remains. Numeric agreement alone does not prove entailment.
  Extractive answers preserve source sentences and data-tool values.
- Author at least 80 literature questions from the actual parsed passages, with
  gold document/page/section/chunk IDs; freeze 30 database-derived expectations
  and 10 unanswerable questions. Compare retrieval with identical questions and
  filters; report recall at 5/10 and MRR. Report answer metrics separately from
  retrieval; do not change questions/thresholds in response to poor scores.

Sources: [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3),
[reranker model card](https://huggingface.co/BAAI/bge-reranker-v2-m3),
[Sentence Transformers inference documentation](https://sbert.net/docs/sentence_transformer/usage/efficiency.html).
