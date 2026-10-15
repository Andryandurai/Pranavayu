# Phase 5: evidence-based air-quality research assistant

Exported 2026-10-12T10:01:16.526959+00:00. Evaluation MLflow run `2eb541abd6fe49f688d6a23d477f5227`.

## Phase 4 prerequisite

AnalysisRun 21 was complete and independently verified before this phase: 148 baseline tests, 7,728 predictions, 147 registered versions and 3,885 stored replay forecasts. Its method was retained. The earlier missing operational/report checks were completed and recorded in VALIDATION. Nine issued policies lose to persistence and intervals under-cover; RAG does not change those results.

Current full suite: **183 passing tests**; 20 original test/support files match their baseline SHA256. See VALIDATION for actual command output and warnings.

## Library

29 registered bodies: 24 public downloads and 5 internal Markdown snapshots; 4 unavailable requests; 7194 indexed chunks. 1947 physical PDF pages and 6 logical unpaginated pages. 223 pages used OCR. All 12 seeded city plans were downloaded, including the Kolkata plan in PRANA's West Bengal file.

| Input | Year | Pages | Chunks | Status | Source / note |
| --- | --- | --- | --- | --- | --- |
| Swachh Vayu Diwas: India's Commitment to Clean Air (PIB, 24 September 2024) | 2024 | 11 | 36 | ready | [source](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/sep/doc2024924400701.pdf) |
| National Ambient Air Quality Status & Trends 2019 (includes NAAQS notification) | 2020 | 164 | 1375 | ready | [source](https://cpcb.gov.in/upload/NAAQS_2019.pdf) |
| National Air Quality Index (CPCB technical report) | 2015 | 58 | 197 | ready | [source](https://www.cpcb.gov.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvRklOQUwtUkVQT1JUX0FRSV8ucGRm) |
| Swachh Vayu Survekshan 2023 results | 2023 | 9 | 21 | ready | [source](https://prana.cpcb.gov.in/assets/pdf/Swachh_Vayu_Survekshan_2023_Result.pdf) |
| WHO global air quality guidelines (2021) | 2021 | — | — | unavailable | HTTP 200; ValueError: Both attempts failed for https://iris.who.int/bitstream/handle/10665/345329/9789240034228-eng.pdf?sequence=1%2526isAllowed%3Dy |
| CPCB list of non-attainment and million-plus cities | unknown | 4 | 5 | ready | [source](https://cpcb.gov.in/uploads/Non-Attainment_Cities.pdf) |
| AERMOD Model Formulation, EPA-454/B-26-003 (July 2026) | 2026 | 179 | 333 | ready | [source](https://gaftp.epa.gov/aqmg/SCRAM/models/preferred/aermod/aermod_mfd.pdf) |
| Comprehensive Study on Air Pollution and Green House Gases in Delhi (IIT Kanpur) | 2016 | 334 | 1115 | ready | [source](https://home.iitk.ac.in/~mukesh/Publications/DPCC_2016_SA%20study%20IIT%20Kanpur%20report_Comprehensive%20Study%20on%20Air%20Pollution%20and%20Green%20House%20Gases%20(GHGs)%20in%20Delhi.pdf) |
| Source apportionment and air quality management study: Delhi NCR (TERI-ARAI) | 2018 | 560 | 1843 | ready | [source](https://www.teriin.org/sites/default/files/2018-08/Report_SA_AQM-Delhi-NCR_0.pdf) |
| Restoring Air Quality through Source Apportionment Analysis (Mukesh Sharma, CSE workshop presentation, 4 June 2019) | 2019 | 53 | 188 | ready | [source](https://cdn.cseindia.org/attachments/0.12136100_1560416301_Restoring-Air-Quality-through-Source-Apportionment-Analysis.pdf) |
| Quantifying the influence of agricultural fires in northwest India on urban air pollution in Delhi, India | 2018 | — | — | unavailable | HTTP 200,403,404; ValueError: Both attempts failed for https://acmg.seas.harvard.edu/publications/2018/cusworth_2018_india.pdf |
| Random forest meteorological normalisation models for Swiss PM10 trend analysis | 2018 | 17 | 130 | ready | [source](https://acp.copernicus.org/articles/18/6223/2018/acp-18-6223-2018.pdf) |
| Abrupt but smaller than expected changes in surface air quality attributable to COVID-19 lockdowns | 2021 | 1 logical | 59 | ready | [source](https://pmc.ncbi.nlm.nih.gov/articles/PMC7806219/) |
| COVID-19 lockdowns cause global air pollution declines (Venter et al., preprint) | 2020 | — | — | unavailable | HTTP 403; ValueError: Both attempts failed for https://www.medrxiv.org/content/10.1101/2020.04.10.20060673v1.full.pdf |
| Health and economic impact of air pollution in the states of India: GBD 2019 | 2021 | 14 | 132 | ready | [source](https://www.econ.umd.edu/sites/www.econ.umd.edu/files/pubs/GBD%20India%202019.pdf) |
| Air Pollution and Cigarette Equivalence (Berkeley Earth) | unknown | — | — | unavailable | HTTP 500; ValueError: Both attempts failed for https://berkeleyearth.org/air-pollution-and-cigarette-equivalence/ |
| EnviroInsights-India Phase 3A results (legacy method) | 2026 | 1 logical | 26 | ready | internal snapshot |
| EnviroInsights-India Phase 3A2 results | 2026 | 1 logical | 43 | ready | internal snapshot |
| EnviroInsights-India Phase 3B results | 2026 | 1 logical | 48 | ready | internal snapshot |
| EnviroInsights-India Phase 4 results | 2026 | 1 logical | 30 | ready | internal snapshot |
| EnviroInsights-India data sources and provenance | 2026 | 1 logical | 14 | ready | internal snapshot |
| Ahmedabad clean air action plan (CPCB/PRANA) | unknown | 21 | 32 | ready | [source](https://cpcb.gov.in/Actionplan/Ahmedabad.pdf) |
| Bengaluru clean air action plan (CPCB/PRANA) | unknown | 23 | 19 | ready | [source](https://cpcb.gov.in/Actionplan/Bengaluru.pdf) |
| Delhi clean air action plan (CPCB/PRANA) | unknown | 84 | 134 | ready | [source](https://cpcb.gov.in/Actionplan/Delhi.pdf) |
| Hyderabad clean air action plan (CPCB/PRANA) | unknown | 57 | 149 | ready | [source](https://cpcb.gov.in/Actionplan/Hyderabad.pdf) |
| Jaipur clean air action plan (CPCB/PRANA) | unknown | 10 | 22 | ready | [source](https://cpcb.gov.in/Actionplan/Jaipur.pdf) |
| Kanpur clean air action plan (CPCB/PRANA) | unknown | 10 | 129 | ready | [source](https://cpcb.gov.in/Actionplan/Kanpur.pdf) |
| Lucknow clean air action plan (CPCB/PRANA) | unknown | 10 | 127 | ready | [source](https://cpcb.gov.in/Actionplan/Lucknow.pdf) |
| Mumbai clean air action plan (CPCB/PRANA) | 2019 | 92 | 230 | ready | [source](https://cpcb.gov.in/Actionplan/Mumbai.pdf) |
| Patna clean air action plan (CPCB/PRANA) | unknown | 22 | 53 | ready | [source](https://cpcb.gov.in/Actionplan/Patna.pdf) |
| Pune clean air action plan (Draft / Revised R1) | unknown | 38 | 152 | ready | [source](https://cpcb.gov.in/Actionplan/Pune.pdf) |
| Revised Action Plan for Chennai Urban Agglomeration (October 2021) | 2021 | 137 | 441 | ready | [source](https://www.tnpcb.gov.in/PDF/Information/technical/ActionplanChn.pdf) |
| Comprehensive Air Quality Action Plan for Kolkata (Government of West Bengal; PRANA copy) | unknown | 40 | 111 | ready | [source](https://cpcb.gov.in/Actionplan/West%20Bengal.pdf) |

Bodies and model weights are gitignored. The retained manifest records actual SHA256, bytes, requested/resolved URLs, attempts, retrieval/verification date and licence notes. Failed bodies have no invented hash, page or Document row. Grange and the NCAP city list reuse earlier SHA-verified public copies; their recorded date identifies cache verification/registration.

## Decisions and pipeline

- PyMuPDF physical pages, pdfplumber Markdown tables, Tesseract English OCR, and real HTML/Markdown sections. Parser 3 rejects single-column false tables. Tables are separate evidence. BGE token windows use 100-token overlap; short section tails are retained instead of padding or inventing text.
- Pinned BAAI/bge-m3 dense 1024-vectors and BAAI/bge-reranker-v2-m3. CPU float32, four threads, two-item inference batches, one model resident at a time. Weights and revision/precision/content caches persist under data/models on D:. Database batches and advisory locks permit resume.
- pgvector cosine HNSW plus indexed English full-text search, RRF k=60; rerank the fused top 40 and keep 8. Category/year/city filters apply before ranking. Prespecified relevance floor is 0.2; it was not changed after evaluation.
- Extractive is the provider: neither remote key/model pair is configured. Docker has 7.605 GiB allocated; the required 12 GB free-container condition for Ollama is unmet. No local LLM was pulled. Optional generative interfaces are implemented; OpenAI transport has a mocked Responses test. No remote or local generative provider is certified by live calls.
- Eight validated read-only tools use actual source runs: raw 9, normalisation 7, research 19 and forecast 21/model versions. Missingness, station cohort, eligibility and replay remain explicit. No user SQL is accepted. Explicit data-snapshot URLs were fixed without changing API defaults.
- Every emitted claim uses retrieved/tool evidence. Exact-text and numeric checks remove unsupported claims; missing evidence refuses. Scientific range brackets stay source text. Query stores actual route, retrieval IDs, calls, answer, citations, provider, latency and verification.
- Frozen evaluation has 80 authored literature questions from 12 actual documents, 30 DB-derived data expectations and 10 unanswerable questions. Known-gold judgments are incomplete. No threshold or question was changed in response to a score. Gold chunk IDs address this database snapshot.

Evaluation SHA256: `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4`; built 2026-10-11T01:50:50.548878+00:00. The cold/warm 450-word two-text float32 probes took 24.2308/3.0209 seconds. A two-passage reranker probe took 11.1808 seconds including model switch/load. Answer-phase latency below uses caches populated by retrieval evaluation; it is not cold interactive latency.

Live hardware capture: 13th Gen Intel(R) Core(TM) i5-13420H; 8 cores / 12 logical processors; Docker 29.8.2, linux, Compose 5.5.1. Source and model-cache bind mounts resolve to D:. Two direct uncached encoder calls had maximum vector difference 0.0, shape [2, 1024]; this checks those inputs and does not promise bitwise portability across hardware.

Windows recorded an idle sleep during indexing; its actual timestamps are retained in verification/windows-sleep.json. Batches survived and Docker health returned 200 after wake. The temporary system-required request is **released**; permanent power settings changed: False. See [Windows execution-state documentation](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).

| Chunk kind | Count | Mean BGE tokens | Below 500 | Above 800 |
| --- | --- | --- | --- | --- |
| table | 2930 | 599.26 | 720 | 0 |
| prose | 4264 | 139.12 | 3822 | 0 |

The window target is 500–800 tokens, with smaller section/table tails kept. The measured short-chunk share is substantial: heuristic heading/figure segmentation can reduce context. The corpus is not described as uniformly 500–800-token chunks.

## Retrieval comparison

Recall is the fraction of all known gold chunks retrieved; hit means at least one known gold chunk. MRR searches through 40. All four methods use the same frozen 80 questions.

Query vectors are primed before timed retrieval, so vector/hybrid times exclude query encoding. Hybrid-rerank time includes uncached pair scoring; later answer calls reuse those scores. These timings measure individual benchmark stages under the recorded cache conditions.

| Method | Recall@5 | Recall@10 | Hit@5 | Hit@10 | MRR | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- |
| vector | 60.94% | 69.06% | 62.50% | 71.25% | 0.4596 | 0.070 |
| keyword | 67.81% | 80.31% | 70.00% | 81.25% | 0.5165 | 0.187 |
| hybrid | 71.56% | 80.94% | 73.75% | 83.75% | 0.5985 | 0.213 |
| hybrid_rerank | 80.31% | 88.44% | 82.50% | 90.00% | 0.6933 | 67.481 |

## Answer metrics

| Provider | Questions | Citation accuracy | Numeric recall | Numeric precision | Grounded emitted sentences | Correct refusals | Literature gold source cited |
| --- | --- | --- | --- | --- | --- | --- | --- |
| extractive | 120 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 88.75% |

extractive: 925/925 correct citation uses, 669/669 expected numeric values matched by field, 0 extra numeric values in scored fields. Numeric cell exactness 100.00%; available-data answer rate 100.00% (30 questions). Literature answer rate 100.00%. 0 unsupported draft claims were removed. Mean cached answer time 1.634 s.

Citation/grounding auditing re-reads stored source text and actual tool evidence. It is an exact-text support measure, not independent semantic entailment, scientific truth or complete question-answer accuracy. Empty answers are not assigned perfect grounding. Numeric recall penalises omitted available values; missing-data abstention is tracked separately.

## Ten actual API Q&As

### 1. What was the annual mean PM2.5 in Delhi in 2025?

HTTP 200; Query 1; extractive; 52 ms.

| Field | Value | Citation |
| --- | --- | --- |
| city | delhi | [dataset: city_annual_mean, Delhi, year=2025, run 9] |
| year | 2025 | [dataset: city_annual_mean, Delhi, year=2025, run 9] |
| annual_mean | 96.65482379525307 | [dataset: city_annual_mean, Delhi, year=2025, run 9] |
| partial_observed_mean | None | [dataset: city_annual_mean, Delhi, year=2025, run 9] |
| valid_days | 365 | [dataset: city_annual_mean, Delhi, year=2025, run 9] |
| annual_eligible | True | [dataset: city_annual_mean, Delhi, year=2025, run 9] |
| units | µg/m³ | [dataset: city_annual_mean, Delhi, year=2025, run 9] |
| cohort | all_stations | [dataset: city_annual_mean, Delhi, year=2025, run 9] |
| aggregation | mean of valid equal-station IST daily means; days require 18 hours | [dataset: city_annual_mean, Delhi, year=2025, run 9] |
| status | available | [dataset: city_annual_mean, Delhi, year=2025, run 9] |

- [dataset: city_annual_mean, Delhi, year=2025, run 9](/api/analytics/city/delhi/series/?run=9&kind=raw&freq=daily&start=2025-01-01&end=2026-01-01)

### 2. How many days had PM2.5 above 60 in Hyderabad in 2025?

HTTP 200; Query 2; extractive; 47 ms.

| Field | Value | Citation |
| --- | --- | --- |
| city | hyderabad | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| year | 2025 | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| threshold | 60.0 | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| days_above_threshold | 0 | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| threshold | 60.0 | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| valid_days | 365 | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| units | µg/m³ | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| comparison | strictly greater than | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| cohort | all_stations | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| scope | city daily means, not station maxima | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |
| status | available | [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9] |

- [dataset: exceedance_days, Hyderabad, year=2025, threshold=60.0, run 9](/api/analytics/city/hyderabad/series/?run=9&kind=raw&freq=daily&start=2025-01-01&end=2026-01-01)

### 3. What is the NCAP proxy comparison for Delhi?

HTTP 200; Query 3; extractive; 62 ms.

| Field | Value | Citation |
| --- | --- | --- |
| city | delhi | [dataset: ncap_proxy_comparison, Delhi, run 19] |
| label | PM2.5 proxy for NCAP progress | [dataset: ncap_proxy_comparison, Delhi, run 19] |
| cohort | all_stations | [dataset: ncap_proxy_comparison, Delhi, run 19] |
| is_official_compliance_result | False | [dataset: ncap_proxy_comparison, Delhi, run 19] |
| official_compliance_assessment | not assessed; historic PM10 baseline absent | [dataset: ncap_proxy_comparison, Delhi, run 19] |
| comparison | {"baseline_years": (2017, 2018), "block_days": 7, "normalised": {"baseline_mean": 116.79403608032456, "ci95_difference": (-22.705621926048718, 3.588017219680602), "ci95_percent": (-19.734417564433265, 3.31093035221274), "days": 2501, "difference": -13.504568193120605, "percent_change": -11.562720705903939, "recent_mean": 103.28946788720395, "refits": 20}, "raw": {"baseline_mean": 113.24049119678162, "ci95_difference": (-34.21220238819831, 6.6799805089037), "ci95_percent": (-27.69164764968863, 5.962850324066694), "days": 2501, "difference": -13.695758921676514, "percent_change": -12.094400842784193, "recent_mean": 99.5447322751051, "refits": 0}, "recent_years": (2024, 2025), "samples": 500, "seed": 20261009, "status": "descriptive", "uncertainty": "20 actual week-resampled model refits; shared pooled donors; year/calendar-block draws and centred nested OOF residuals; conditional on selected structure and observed station panel"} | [dataset: ncap_proxy_comparison, Delhi, run 19] |
| nested_readiness | {"passed": false, "periods": ({"bias": -0.6609956562972544, "failures": (), "max_month_abs_nmb": 7.795173656561839, "n": 1812, "nmb_percent": -0.5612190600399123, "passed": true, "period": "old", "r2": 0.701802347334474, "rmse": 43.760252488684046, "weeks": 262}, {"bias": 7.799814299701603, "failures": ("monthly NMB"), "max_month_abs_nmb": 32.50454498460907, "n": 689, "nmb_percent": 7.849089591868262, "passed": false, "period": "recent", "r2": 0.7140127683456524, "rmse": 42.22389527625071, "weeks": 99})} | [dataset: ncap_proxy_comparison, Delhi, run 19] |
| status | available | [dataset: ncap_proxy_comparison, Delhi, run 19] |
| network_matched_long_run_comparisons | {"cohorts": {"all_stations": {"long_run": {"baseline_years": (2015, 2016, 2017, 2018, 2019), "block_days": 7, "normalised": {"baseline_mean": 120.75210833161047, "ci95_difference": (-35.2925084894563, 1.3961557893044154), "ci95_percent": (-26.258943555796893, 1.3416237212003281), "days": 2417, "difference": -18.103617527047206, "percent_change": -14.992382143201091, "recent_mean": 102.64849080456327, "refits": 20}, "raw": {"baseline_mean": 117.7881435009981, "ci95_difference": (-36.708036779113776, 6.973632580317597), "ci95_percent": (-29.272860024908276, 5.9467370441219805), "days": 2417, "difference": -16.0607379081669, "percent_change": -13.63527553011378, "recent_mean": 101.7274055928312, "refits": 0}, "recent_years": (2024, 2025), "samples": 500, "seed": 20261009, "status": "descriptive", "uncertainty": "20 actual week-resampled model refits; shared pooled donors; year/calendar-block draws and centred nested OOF residuals; conditional on selected structure and observed station panel"}, "ncap_proxy": {"baseline_years": (2017, 2018), "block_days": 7, "normalised": {"baseline_mean": 116.79403608032456, "ci95_difference": (-21.90812046799254, 7.274088504341635), "ci95_percent": (-19.177705055964726, 6.857493291911465), "days": 2417, "difference": -14.145545275761293, "percent_change": -12.111530477491812, "recent_mean": 102.64849080456327, "refits": 20}, "raw": {"baseline_mean": 113.24049119678162, "ci95_difference": (-31.452114124349485, 13.633257266857909), "ci95_percent": (-26.454938070583594, 12.96776629577585), "days": 2417, "difference": -11.513085603950415, "percent_change": -10.166933649151838, "recent_mean": 101.7274055928312, "refits": 0}, "recent_years": (2024, 2025), "samples": 500, "seed": 20261009, "status": "descriptive", "uncertainty": "20 actual week-resampled model refits; shared pooled donors; year/calendar-block draws and centred nested OOF residuals; conditional on selected structure and observed station panel"}}, "fixed_panel": {"long_run": {"baseline_years": (2015, 2016, 2017, 2018, 2019), "block_days": 7, "normalised": {"baseline_mean": 120.75210833161047, "ci95_difference": (-35.071142907974696, 1.6623174839119734), "ci95_percent": (-26.128186930340362, 1.5567328594264724), "days": 2417, "difference": -17.591985246475744, "percent_change": -14.56867750761294, "recent_mean": 103.16012308513473, "refits": 20}, "raw": {"baseline_mean": 117.7881435009981, "ci95_difference": (-36.18239667291732, 7.900024982233389), "ci95_percent": (-28.85158666989071, 6.728821298680834), "days": 2417, "difference": -15.395554453086106, "percent_change": -13.070546827113926, "recent_mean": 102.392589047912, "refits": 0}, "recent_years": (2024, 2025), "samples": 500, "seed": 20261009, "status": "descriptive", "uncertainty": "20 actual week-resampled model refits; shared pooled donors; year/calendar-block draws and centred nested OOF residuals; conditional on selected structure and observed station panel"}, "ncap_proxy": {"baseline_years": (2017, 2018), "block_days": 7, "normalised": {"baseline_mean": 116.79403608032456, "ci95_difference": (-20.015238994711364, 7.802783331869133), "ci95_percent": (-17.166010415421685, 7.294065086428322), "days": 2417, "difference": -13.633912995189831, "percent_change": -11.673466773434535, "recent_mean": 103.16012308513473, "refits": 20}, "raw": {"baseline_mean": 113.24049119678162, "ci95_difference": (-30.897255833628098, 14.523912164139354), "ci95_percent": (-25.994625194235063, 13.778529969885806), "days": 2417, "difference": -10.847902148869622, "percent_change": -9.579525869433818, "recent_mean": 102.392589047912, "refits": 0}, "recent_years": (2024, 2025), "samples": 500, "seed": 20261009, "status": "descriptive", "uncertainty": "20 actual week-resampled model refits; shared pooled donors; year/calendar-block draws and centred nested OOF residuals; conditional on selected structure and observed station panel"}}}, "days": 2417, "status": "matched supported dates", "years": (2015, 2016, 2017, 2018, 2019, 2024, 2025)} | [dataset: ncap_proxy_comparison, Delhi, run 19] |

- [dataset: ncap_proxy_comparison, Delhi, run 19](/api/analytics/ncap/?run=19)

### 4. Show the latest replay forecast for Bengaluru.

HTTP 200; Query 4; extractive; 102 ms.

| Field | Value | Citation |
| --- | --- | --- |
| city | bengaluru | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.issued_for_date | 2025-12-31 | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.target_date | 2026-01-01 | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.mode | replay | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.point | 55.83447337962963 | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.lower80 | 45.39305423280423 | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.upper80 | 66.27589252645502 | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.lower95 | 39.23543948412698 | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.upper95 | 72.43350727513229 | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.aqi_category | satisfactory | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.algorithm | persistence | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.model_version | 52 | [dataset: latest_forecast, Bengaluru, run 21] |
| h1.cohort | fixed_panel | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.issued_for_date | 2025-12-31 | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.target_date | 2026-01-02 | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.mode | replay | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.point | 55.83447337962963 | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.lower80 | 39.09583498677249 | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.upper80 | 72.57311177248677 | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.lower95 | 30.470368055555554 | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.upper95 | 81.1985787037037 | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.aqi_category | satisfactory | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.algorithm | persistence | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.model_version | 59 | [dataset: latest_forecast, Bengaluru, run 21] |
| h2.cohort | fixed_panel | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.issued_for_date | 2025-12-31 | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.target_date | 2026-01-03 | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.mode | replay | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.point | 55.83447337962963 | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.lower80 | 37.36883928571428 | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.upper80 | 74.30010747354498 | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.lower95 | 22.055293981481483 | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.upper95 | 89.61365277777777 | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.aqi_category | satisfactory | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.algorithm | persistence | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.model_version | 66 | [dataset: latest_forecast, Bengaluru, run 21] |
| h3.cohort | fixed_panel | [dataset: latest_forecast, Bengaluru, run 21] |
| units | µg/m³ | [dataset: latest_forecast, Bengaluru, run 21] |
| timezone | Asia/Kolkata | [dataset: latest_forecast, Bengaluru, run 21] |
| category_scope | PM2.5 subindex category, not overall AQI | [dataset: latest_forecast, Bengaluru, run 21] |
| interpretation | Replay is archival and is not a current live forecast | [dataset: latest_forecast, Bengaluru, run 21] |

- [dataset: latest_forecast, Bengaluru, run 21](/api/forecast/bengaluru/latest/)

### 5. What is forecast skill for Delhi at horizon 1?

HTTP 200; Query 5; extractive; 51 ms.

| Field | Value | Citation |
| --- | --- | --- |
| city | delhi | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| horizon | 1 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| n | 184 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| dm | {"hac_lag": 7, "loss": "squared", "p_value": 0.0284450930457046, "statistic": -2.2085900774703027} | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| csi | 0.9767441860465116 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| far | 0.0 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| mae | 18.68599823615678 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| pod | 0.9767441860465116 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| hits | 84 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| rmse | 29.41698872585291 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| misses | 2 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| mean_bias | 2.0032173922329415 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| nmb_percent | 1.8918377536721431 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| false_alarms | 0 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| forecast_exceedances | 84 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| observed_exceedances | 86 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| skill_vs_persistence | 0.1262702001595033 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| aqi_category_accuracy | 0.717391304347826 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| intervals | {"80": {"coverage": 0.6847826086956522, "mean_width": 41.45974685634395, "n": 184}, "95": {"coverage": 0.8967391304347826, "mean_width": 77.20351720394808, "n": 184}, "quantile_80": {"coverage": 0.8043478260869565, "mean_width": 66.49470261819421, "n": 184}, "quantile_95": {"coverage": 0.967391304347826, "mean_width": 159.92505044144715, "n": 184}} | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| issued_algorithms | {"lightgbm": 31, "lstm": 153} | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| target_start | 2025-07-01 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| target_end | 2025-12-31 | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| weather | archived_forecast | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| units | µg/m³ | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| status | available | [dataset: forecast_skill, Delhi, horizon=1, run 21] |
| limitations | Retrospective monthly-selected policy; live skill unverified. Negative skill loses to persistence; empirical interval coverage is not a guarantee. | [dataset: forecast_skill, Delhi, horizon=1, run 21] |

- [dataset: forecast_skill, Delhi, horizon=1, run 21](/api/forecast/delhi/evaluation/)

### 6. What are the RQ2 weather drivers in Mumbai in winter?

HTTP 200; Query 6; extractive; 59 ms.

| Field | Value | Citation |
| --- | --- | --- |
| city | mumbai | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| season | winter | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| old.wind_direction | 2.7702076996981204 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| old.surface_pressure_hpa | 2.274715326307587 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| old.precipitation_mm | 1.1223765316453322 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| old.wind_speed_ms | 1.0636428229169668 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| old.relative_humidity | 0.5664870058089841 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| recent.precipitation_mm | 2.6082605246259427 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| recent.surface_pressure_hpa | 1.6108039923265107 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| recent.total_cloud_cover | 1.0226642354691593 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| recent.wind_direction | 1.0182469963998446 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| recent.wind_speed_ms | 0.673457302376795 | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| units | µg/m³ (mean absolute daily SHAP) | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| cohort | all_stations | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| nested_readiness | {"passed": true, "periods": ({"bias": -0.9451901514150836, "failures": (), "max_month_abs_nmb": 11.633161020242127, "n": 1379, "nmb_percent": -2.2566788972925576, "passed": true, "period": "old", "r2": 0.5678358948721738, "rmse": 16.571943196336196, "weeks": 206}, {"bias": 1.8853104465365171, "failures": (), "max_month_abs_nmb": 18.09454675407369, "n": 731, "nmb_percent": 5.512944087871207, "passed": true, "period": "recent", "r2": 0.7419783767813406, "rmse": 9.916234554579272, "weeks": 105})} | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| interpretation | conditional model attribution; not causal effects or a variance partition | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| season_definition | winter October–February; pre-monsoon March–May; monsoon June–September | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |
| status | available | [dataset: rq2_drivers, Mumbai, season=winter, run 19] |

- [dataset: rq2_drivers, Mumbai, season=winter, run 19](/api/analytics/rq2/mumbai/?run=19)

### 7. Show raw monthly PM2.5 in Delhi during 2025.

HTTP 200; Query 7; extractive; 104 ms.

| Field | Value | Citation |
| --- | --- | --- |
| city | delhi | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| start | 2025-01-01 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| end | 2026-01-01 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| kind | raw | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-01-01 | 162.90553777478922 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-02-01 | 97.8052780148887 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-03-01 | 70.19808397292958 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-04-01 | 76.74921238924802 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-05-01 | 66.68624424107384 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-06-01 | 48.70743808842394 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-07-01 | 29.224024008477684 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-08-01 | 32.63851770044427 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-09-01 | 35.23644434137562 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-10-01 | 109.03429712069162 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-11-01 | 215.93379725509539 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| 2025-12-01 | 214.528009330825 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| rows_shown | 12 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| total_rows | 12 | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| kind | raw | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| units | µg/m³ | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| date_semantics | start inclusive, end exclusive; missing values remain null | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| cohort | stored CitySeries default (all stations) | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |
| status | available | [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9] |

- [dataset: city_monthly_series, Delhi, start=2025-01-01, end=2026-01-01, kind=raw, run 9](/api/analytics/city/delhi/series/?run=9&kind=raw&freq=monthly&start=2025-01-01&end=2026-01-01)

### 8. What was the annual mean PM2.5 in Delhi in 2022?

HTTP 200; Query 8; extractive; 95 ms.

Insufficient evidence in the available documents and project data.


### 9. What are AERMOD model assumptions and limitations?

HTTP 200; Query 131; extractive; 85187 ms.

The AMS/EPA Regulatory Model: AERMOD AERMOD is a steady-state plume model in that it assumes that concentrations at all distances during a modeled hour are governed by the temporally averaged meteorology of the hour. [AERMOD Model Formulation, EPA-454/B-26-003 (July 2026), p. 60–61]
Thus, by default, AERMOD will apply stack-tip downwash, gradual plume rise, and buoyancy induced dispersion for a platform source consistent with all other POINT, POINTHOR, and POINTCAP source types. [AERMOD Model Formulation, EPA-454/B-26-003 (July 2026), p. 145–146]

*Report excerpt; the complete actual response is retained in `data/results/rag-phase5/verification/http-complete.json`.*

- [AERMOD Model Formulation, EPA-454/B-26-003 (July 2026), p. 60–61](/api/rag/documents/6/page/60/)
- [AERMOD Model Formulation, EPA-454/B-26-003 (July 2026), p. 145–146](/api/rag/documents/6/page/145/)
- [Comprehensive Study on Air Pollution and Green House Gases in Delhi (IIT Kanpur), p. 302–303](/api/rag/documents/7/page/302/)
- [AERMOD Model Formulation, EPA-454/B-26-003 (July 2026), p. 66–68](/api/rag/documents/6/page/66/)
- [AERMOD Model Formulation, EPA-454/B-26-003 (July 2026), p. 17–18](/api/rag/documents/6/page/17/)
- [AERMOD Model Formulation, EPA-454/B-26-003 (July 2026), p. 61–62](/api/rag/documents/6/page/61/)
- [AERMOD Model Formulation, EPA-454/B-26-003 (July 2026), p. 14–15](/api/rag/documents/6/page/14/)
- [AERMOD Model Formulation, EPA-454/B-26-003 (July 2026), p. 161–163](/api/rag/documents/6/page/161/)

### 10. What measures does Kolkata's clean air action plan propose to control road dust?

HTTP 200; Query 132; extractive; 61204 ms.

WB PWD, and road Implementation of 23-15 Action points Agency Timeline for Financial Outlay responsible _| action (to be finalized after discussion with the implementing agencies) construction material and lenforcement of debris in covered system Imeasures shall be done as per routine lactivities 8.13 Awareness Generation Action points Agency Timeline for Financial Outlay responsible _ | action (to be finalized after discussion with the implementing agencies) 8.13.1 Issue of advisory …

*Report excerpt; the complete actual response is retained in `data/results/rag-phase5/verification/http-complete.json`.*

- [Comprehensive Air Quality Action Plan for Kolkata (Government of West Bengal; PRANA copy), p. 38–40](/api/rag/documents/29/page/38/)
- [Comprehensive Air Quality Action Plan for Kolkata (Government of West Bengal; PRANA copy), p. 21](/api/rag/documents/29/page/21/)
- [Comprehensive Air Quality Action Plan for Kolkata (Government of West Bengal; PRANA copy), p. 18](/api/rag/documents/29/page/18/)
- [Comprehensive Air Quality Action Plan for Kolkata (Government of West Bengal; PRANA copy), p. 21–22](/api/rag/documents/29/page/21/)
- [Comprehensive Air Quality Action Plan for Kolkata (Government of West Bengal; PRANA copy), p. 8–9](/api/rag/documents/29/page/8/)
- [Comprehensive Air Quality Action Plan for Kolkata (Government of West Bengal; PRANA copy), p. 6](/api/rag/documents/29/page/6/)
- [Comprehensive Air Quality Action Plan for Kolkata (Government of West Bengal; PRANA copy), p. 20](/api/rag/documents/29/page/20/)
- [Comprehensive Air Quality Action Plan for Kolkata (Government of West Bengal; PRANA copy), p. 7](/api/rag/documents/29/page/7/)

## Failure analysis and verification

The implementation faults and re-runs are recorded in [PHASE5_IMPLEMENTATION_FIXES.md](PHASE5_IMPLEMENTATION_FIXES.md). The main corrections were source identity/year labels, token-offset bounds, false table/heading detection, CPU precision, explicit snapshot citation URLs, validator error shape, and distinction between evidence IDs and scientific brackets.

Measured retrieval failures remain in retrieval.jsonl:

- vector: 23 questions missed all known gold in the top 10: L005, L013, L015, L019, L021, L022, L023, L025, L026, L028, L029, L033, L037, L046, L050, L051, L055, L056, L061, L062, L066, L071, L072.
- keyword: 15 questions missed all known gold in the top 10: L013, L021, L025, L026, L028, L029, L031, L032, L035, L051, L056, L063, L065, L066, L068.
- hybrid: 13 questions missed all known gold in the top 10: L005, L013, L021, L023, L025, L028, L029, L050, L051, L055, L056, L061, L066.
- hybrid_rerank: 8 questions missed all known gold in the top 10: L013, L025, L028, L029, L051, L056, L071, L072.

Of the hybrid-rerank top-10 misses, 4 had no known gold in the 40 RRF candidates, and 4 had a gold candidate that reranking placed below 10. These are measured pipeline locations of the misses; they do not establish that every non-gold passage is irrelevant. The saved rankings and questions permit inspection without changing the frozen evaluation.

| Missed known gold in top 10 | Question | Location of miss |
| --- | --- | --- |
| L013 | What annual PM2.5 standard is shown in the CPCB report summary? | absent from fused 40 |
| L025 | What condition did Grange generally require of a monitoring record for trend analysis? | reranked below 10 |
| L028 | Which trend estimator did Grange use after meteorological normalisation? | reranked below 10 |
| L029 | How many cities were evaluated in Shi et al. 2021? | absent from fused 40 |
| L051 | Which sampling seasons were used in the IIT Kanpur Delhi study? | absent from fused 40 |
| L056 | What is potassium used to indicate in the IIT Kanpur Delhi study? | absent from fused 40 |
| L071 | At what issue time and horizons are the Phase 4 forecasts defined? | reranked below 10 |
| L072 | Why was boundary-layer height excluded from the forecast predictors? | reranked below 10 |

Literature answers without a known-gold chunk citation: L013, L025, L028, L029, L031, L051, L056, L071, L072.

Answer generation keeps eight passages, while retrieval Recall@10 evaluates ten. A gold passage ranked ninth or tenth can therefore count as a retrieval hit and still be absent from the emitted answer. These measures have different denominators.

Inspection of the complete saved L013 answer illustrates both evaluation limits and usability: the question asks for the CPCB summary, but the answer misses its known-gold summary chunks and mixes general CPCB text with noisy Hyderabad chart OCR. That alternate chart does contain the annual standard value (40 ug/m3), so a known-gold retrieval miss does not prove every alternative passage is irrelevant. Conversely, its exact-text citation support does not establish that the answer is concise, clear or complete. The original full answer, citation identities and rankings remain in answers.jsonl; no question or threshold was changed after this inspection.

Actual execution proofs:

```json
{
  "completed_at": "2026-10-11T05:16:19.273552+00:00",
  "documents": 29,
  "ready_documents": 29,
  "chunks": 7194,
  "embeddings": 7194,
  "pages": 1953,
  "ocr_pages": 223,
  "logical_pages": 6,
  "token_statistics": {
    "mean": 326.527661940506,
    "maximum": 800,
    "minimum": 1,
    "total": 2349040
  },
  "token_bands": {
    "under500": 4542,
    "500to800": 2652,
    "over800": 0
  },
  "token_groups": [
    {
      "metadata__is_table": true,
      "count": 2930,
      "average": 599.261433447099,
      "under500": 720,
      "over800": 0
    },
    {
      "metadata__is_table": false,
      "count": 4264,
      "average": 139.11913696060037,
      "under500": 3822,
      "over800": 0
    }
  ],
  "idempotent_reingestion": {
    "documents": 29,
    "new_chunks": 0,
    "new_vectors": 0,
    "chunk_ids_unchanged": true
  },
  "chunk_source_year_category_consistent": true,
  "extensions": {
    "plpgsql": "1.0",
    "postgis": "3.6.4",
    "timescaledb": "2.30.2",
    "timescaledb_toolkit": "1.26.0",
    "vector": "0.8.7"
  },
  "vector_stats": [
    1024,
    1024,
    0.9999998692963225,
    1.0000001804510361
  ],
  "hnsw_index_explain": "Limit  (cost=395.83..403.80 rows=8 width=965)\n  ->  Index Scan using chunk_embedding_hnsw on rag_documentchunk  (cost=395.83..10484.32 rows=10131 width=965)\n        Order By: (embedding <=> '<1024-dimensional vector omitted>'::vector)",
  "fts_index_explain": "Sort  (cost=317.04..317.51 rows=186 width=989)\n  Sort Key: document_id, chunk_index\n  ->  Bitmap Heap Scan on rag_documentchunk  (cost=21.30..310.03 rows=186 width=989)\n        Recheck Cond: (to_tsvector('english'::regconfig, COALESCE(text, ''::text)) @@ '''aermod'''::tsquery)\n        ->  Bitmap Index Scan on chunk_text_fts_gin  (cost=0.00..21.26 rows=186 width=0)\n              Index Cond: (to_tsvector('english'::regconfig, COALESCE(text, ''::text)) @@ '''aermod'''::tsquery)",
  "index_plan_conditions": "enable_seqscan=off inside local transactions; proves usable indexes, not natural planner choice or speed",
  "original_test_files_checked": 20,
  "original_test_files_changed": [],
  "phase4": {
    "run": 21,
    "status": "success",
    "versions": 147,
    "forecasts": 3885
  },
  "report_display_note": "Vector literal omitted here; final-proof.json retains the complete actual EXPLAIN output."
}
```

## Remaining limitations

- WHO, Cusworth, the Venter preprint and Berkeley Earth remained unavailable after recorded retries and official/institutional searches. They are not simulated with snippets or model memory.
- OCR uses English; small glyphs, Hindi, subscripts, image tables and complex column order can be imperfect. OCR tables retain text without guaranteed cell reconstruction. Native headings are heuristic. One-column prose is preserved; short covers/sections/table tails can be below 500 tokens. No parsed corpus is claimed to be error-free.
- Literature evaluation covers 12 core sources; city-plan retrieval is additionally checked by an actual API example, not comprehensively judged for all 12 plans. Gold judgments are incomplete and this is one authored evaluation set, not a general reliability guarantee.
- Exact quotation can be grounded yet incomplete or irrelevant. No LLM synthesis or independent human semantic grading ran. Remote/local generative providers remain unverified.
- CPU reranking can be slow. Cached evaluation latency understates cold interactive requests. Keyword fallback is explicitly recorded if inference connectivity fails.
- Public source access is not an open reuse licence. IIT Kanpur prints reproduction restrictions; other licences/unknown years remain in metadata. Data comparisons retain station, coverage, causal, uncertainty and replay limitations from Phases 3/4.

## Phase 6 integration

Call POST `/api/rag/explain/` with `context_type` chart, forecast or scenario and a validated `payload` containing city/question and optional scenario_id/parameters. Preserve citations, provider, verification, unavailable-data and replay flags. Supplied client numbers are context rather than verified project results. Scenario explanations currently use documented AERMOD assumptions; Phase 6 must validate actual simulation outputs before treating them as numerical evidence. No simulator or dashboard was built in this phase.


## Phase 6A append: measured local Ollama provider

The original Phase 5 extractive evaluation above and its 32 retained result
artifacts are unchanged. This append records the separately executed provider-only
evaluation after the requested Phase 6A interval and reranker changes. It does
not replace the original metrics, frozen questions or expectations.

Installed RAM was 16 GiB. The requested WSL limit is floor(0.6×16)=9GB.
`.wslconfig` did not exist, so no previous settings needed backup. After the
clean Docker/WSL restart, the measured available container memory was
6,909,865,984 bytes against actual model 1,929,912,432 bytes+3 GiB headroom;
the revised measured gate passes. No 12 GB-free rule is used for this run.

The default is `qwen2.5:3b-instruct` via Ollama, Q4_K_M, digest
`357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
Generation uses temperature 0, seed 20261010, context 16384, maximum 1600 output
tokens, four CPU threads and keep_alive=0. Caches/model weights are on D:.
Retrieval uses the dedicated resident reranker and the accepted 24-candidate
policy. All 80 frozen literature questions were separately checked against 40:
Recall10 .884375→.903125, a 1.875-point improvement, satisfying the prespecified
maximum 1 point drop. This is a retrieval result, not answer accuracy.

The completed evaluation has 80 literature, 30 data and 10 unanswerable questions.
Its frozen SHA256 remains
`f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4`.
The command resumes saved completed answers after user pauses/Docker shutdowns;
it does not regenerate completed questions or mix changed gold files.

```powershell
docker compose exec -T web python manage.py evaluate_rag --provider ollama --output data/results/rag-ollama-phase6a
```

Completed `2026-10-15T15:16:48.629771+00:00`. MLflow experiment `rag`, run `a70d7abfbf0149b8a4a1f78b8dad544b`.

| Metric | Actual result |
| --- | --- |
| questions | 120 |
| citations | 2 |
| citation_accuracy | 1.0 |
| audited_citation_uses | 2 |
| correct_citation_uses | 2 |
| groundedness_before_removal | 0.016666666666666666 |
| groundedness_emitted | 1.0 |
| emitted_sentences | 2 |
| supported_emitted_sentences | 2 |
| claims | 120 |
| supported_claims | 2 |
| removed_claims | 118 |
| number_correctness | 0.0 |
| numeric_precision | None |
| numeric_cell_exactness | 0.0 |
| correct_numeric_values | 0 |
| expected_numeric_values | 669 |
| extra_numeric_values | 0 |
| available_data_questions | 30 |
| missing_data_questions | 0 |
| available_data_answer_rate | 0.0 |
| missing_data_refusal_rate | None |
| displayed_row_exactness | 0.0 |
| correct_data_rows | 0 |
| expected_data_rows | 491 |
| data_questions_exact | 0.9 |
| correct_refusal_rate | 1.0 |
| literature_answer_rate | 0.025 |
| literature_gold_source_citation_rate | 0.025 |
| latency_seconds_mean | 80.76179166666667 |
| generation_fallbacks | 0 |

| Metric | Actual result |
| --- | --- |
| Latency median seconds | 63.62049999999999 |
| Latency minimum seconds | 0.627 |
| Latency maximum seconds | 230.725 |
| Questions with nonempty evidence | 118 |
| Questions with no evidence (generation skipped) | 2 |

Latency is the actual whole answer path, including retrieval/cache behavior,
model loading, CPU contention and brief inference-service pauses during test
verification. It is not an isolated generation benchmark. Empty evidence returns
a refusal without calling generation, even though the configured provider is
recorded as Ollama. Generation fallbacks, if present, remain in the table.

### Answer coverage and strict verification

| Question type | Questions | Refused |
| --- | --- | --- |
| literature | 80 | 78 |
| data | 30 | 30 |
| unanswerable | 10 | 10 |

| Metric | Actual result |
| --- | --- |
| citation_not_in_evidence | 103 |
| sentence_not_supported_verbatim | 15 |

These are the actual outcomes, including poor answer coverage. A supported-claim
rate among retained text must not hide refusals. When no claims/citations remain,
the relevant score is null, not an invented 100%. The model often omitted the
supplied `[E#]` identifier or paraphrased text that the conservative verifier
could not match exactly. The verifier, prompt, questions and thresholds were
not loosened to make this provider pass. Exact-text support is not independent
semantic correctness, relevance or completeness. This append does not claim
that enabling the local model improved answer quality over extraction.

### Frozen data snapshot drift

Phase 6A selected different existing interval families and added interval-policy
provenance. The frozen expected tool snapshots predate these changes. All 3,885
original forecast rows and their point values were rechecked unchanged; 19 latest
issuance rows had revised bounds. Thus some exact frozen tool comparisons can
fail because actual evidence changed, rather than because the generator changed
the stored number. The frozen score above is still reported unchanged.

`data_questions_exact` measures full returned **tool-snapshot** agreement with
the frozen object, not generated-answer accuracy or coverage. Interpret it with
`available_data_answer_rate`, numeric correctness and displayed-row exactness.
An unchanged database tool result can accompany a refused or incorrect answer.

Tool snapshots differ for 3 data questions: D024, D025, D026.

Supplementary comparison with the **actual returned evidence of each answer**, not a replacement gold set:

| Metric | Actual result |
| --- | --- |
| questions_with_expected_tool | 30 |
| missing_expected_tool_ids | [] |
| correct_numeric_values | 0 |
| expected_numeric_values | 669 |
| extra_numeric_values | 0 |
| number_correctness | 0.0 |
| numeric_precision | None |
| numeric_cell_exactness | 0.0 |
| displayed_row_exactness | 0.0 |

Per-question changed JSON paths and supplementary field-level scores are saved
in `data/results/vayusim/verification/provider-supplement.json`. They distinguish
frozen snapshot drift from fidelity to the actual values supplied to the model;
they do not alter original questions/expected values or certify semantic QA.

Provider answers, removal reasons, audit fields and actual tool evidence remain
in `data/results/rag-ollama-phase6a/answers.jsonl`, with final `metrics.json` and
SHA256 manifest. The compact report is [PHASE6A_METRICS.json](PHASE6A_METRICS.json).
The [Phase 6A report](PHASE6A.md) records actual uncached reranker latency,
including the slower after measurements, the scenario tool, UI and limitations.
