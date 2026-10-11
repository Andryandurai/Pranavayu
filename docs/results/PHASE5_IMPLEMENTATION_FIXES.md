# Phase 5 implementation checks and corrections

This is a running record of implementation faults found before the frozen
evaluation. It does not replace the final metrics and validation report.

- Auditing actual covers showed that the supplied NAAQS URL contains the
  *National Ambient Air Quality Status & Trends 2019* report with a 2020
  foreword, including standards material. Corrected its title/year and recorded
  this distinction instead of claiming a standalone 2009 notification.
- Recorded the actual July 2026 AERMOD revision, October 2021 Chennai plan,
  September 2019 Mumbai revision, Pune draft status and IIT Kanpur printed
  reproduction restriction. Kept unknown city-plan years null.
- The first encoder probe raced service startup and failed with connection
  refused. The healthy-service re-run returned two identical finite 1024-vector
  outputs with norms 0.9999316553 in 80.349 seconds including initial loading.
- Initial new RAG tests: **20 passed, 2 failed in 12.23 seconds**. The two failures
  found a DRF error-shape bug for boolean numeric parameters: raising a list error
  in `to_internal_value` produced ValueError instead of a validated 400. Changed
  the implementation to a parameter error object; tests retained unchanged.
- Oversize repeated table headers could consume the entire token budget and
  prevent the overlap window advancing. Guarded wide headers and guaranteed
  progress; the original header remains in its first source chunk.
- Removed the secondary SQL ordering from cosine retrieval so PostgreSQL can
  use the HNSW distance ordering. Empty corpora skip inference; model-service
  connection failures explicitly fall back to keyword retrieval and are logged
  in each Query's verification metadata.
- Explain payloads validate city, date order, finite JSON and numeric ranges.
  Client chart/scenario numbers remain context rather than evidence. Monthly
  display tables disclose their 24-row truncation; tool_results retain all rows.
- Real PDFs exposed a final token-offset boundary read beyond the array for
  sections with 701–799 tokens. Fixed the search ceiling and added a 750-token
  regression fixture; original tests were retained.
- Before evaluation, the corpus audit counted 23,508 TERI-ARAI chunks, 20,710
  under 30 tokens: bold table cells had been mistaken for section headings.
  Parser version 2 excludes native table cells from prose, weights the dominant
  body font by characters, limits heading length/punctuation, and uses stricter
  text rules for OCR instead of unreliable inferred font size. Rebuilding this
  incompatible index is explicitly recorded; unchanged input re-ingestion with
  the same parser version remains a no-op. No evaluation was frozen or scored
  with the faulty index. Physical source bodies and SHA256 values are unchanged.
- The evaluator separately audits emitted sentences/citation uses against stored
  chunk text and actual tool evidence, rather than assigning an assumed perfect
  citation score. Data expectations are frozen once, including nulls and scope.
- The AVX2 host has no AVX512 FP16/BF16 instructions. Float16 worked but was slow;
  before evaluation, inference changed to float32. Cache namespaces and stored
  fingerprints include precision and sequence length, so earlier vectors are
  not mixed into the final index. The two-text cold/warm probe measured
  24.2308/3.0209 seconds. Two later direct uncached calls on actual source chunks
  returned identical 1024-vectors at the same batch positions, maximum difference
  0.0; the verification artifact retains timings and unit norms.
- Parser 3 rejects single-column false tables: underlined IIT Kanpur prose had
  moved chemical subscripts into separate cells. Three affected authored
  questions were retained and their source text restored. Output-compatible
  parser-2 sources received a recorded compatibility upgrade; affected sources
  were reparsed before freezing. The parsed corpus is 7,194 chunks, including
  1,115 IIT Kanpur and 1,843 TERI-ARAI chunks. No scored question was replaced.
- PRANA's `WestBengal.pdf` contains the Kolkata-specific government action plan.
  Corrected the source title and city metadata after inspecting the actual body.
  Its ambiguous publication year remains null.
- A final visual inspection of the AQI report's physical page 2 found a signed
  2015 foreword. The October 2014 text refers to its draft launch. Corrected the
  catalogue, manifest, Document year and all 197 chunk year tags to 2015; retained
  the requested 2014 separately. Source bytes, embeddings, chunk IDs and the
  frozen evaluation SHA256 are unchanged. The source-audit artifact records
  the evidence and checks.
- Raw data-tool citations exposed an actual HTTP 404 for successful data snapshot
  Run 9. Analytics now permits explicit successful Phase 3A2 data snapshots while
  preserving its completed full-run default. The regression test passes; all
  seven dataset links in the real HTTP proof returned 200 on rerun.
- Before freezing, numeric scoring was corrected to compare numeric values by
  displayed field, with canonical Decimal representations. It reports recall,
  precision, cell exactness, available-data coverage and missing-data abstention
  separately; it does not treat an empty answer as numerically perfect.
- Scientific confidence intervals and footnotes use brackets in actual source
  text. Internal evidence citations now match explicit E-number aliases, and
  the independent final audit matches actual emitted citation labels. Native
  scientific brackets are preserved rather than treated as invented citations.
- The final audit initially mapped a human page citation to a single chunk.
  Multiple chunks on the same page share that label, so later entries overwrote
  earlier source text and could falsely reject supported claims. It now checks
  all associated references for valid identity and requires exact support in at
  least one cited chunk for that label. A new regression also proves that an
  invalid identity cannot be hidden by another valid chunk. This correction
  precedes the first benchmark; questions and thresholds are unchanged.
- The full container suite first passed as **182 passed, 149 warnings in 56.47s**.
  After adding the same-page audit regression, it reran as **183 passed,
  149 warnings in 71.47s**, retaining all 148 baseline tests and the hashes of all
  20 original test/support files. All 35 new RAG cases pass. No warning was silenced.
