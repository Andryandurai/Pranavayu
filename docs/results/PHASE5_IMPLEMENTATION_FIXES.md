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
