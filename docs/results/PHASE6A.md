# Phase 6A: VayuSim engine, data integration and API

**Gate: Ready for 6B with caveats.** Urban C (Delhi/Mumbai) and urban F
(Hyderabad) remain **not independently validated**. Phase6B must display an
**unvalidated branch** label for these scenarios before presenting them. This
is a conditional frontend acceptance requirement; **Phase6B has not started**.
See [Independent validation](#independent-validation) for the exact case scope.

The engine, real-data adapters, API and verification map are implemented in
`D:\EnviroInsights-India`. The user's subsequent whole-site presentation request
covers the overview, forecasts, research, library, assistant and simulator pages.
This report separates measured software/scientific checks from predictive validity.
The [Phase 6A audit](#phase-6a-audit) below narrows the original validation claims;
it includes discrepancies beyond the original supplied-sigma concentration checks.
The full Phase 6B frontend is outside this implementation.

## Step 0 outcomes

### Forecast intervals

Existing Run 21 archived-weather evaluation results selected the closest coverage
to nominal among methods no more than five percentage points below it, separately
for each city, horizon and level. The policy is stored on all 147 model versions.
No point model was refitted. At the change, all 3,885 existing rows and their point
values were retained; 19 latest issuance rows had revised bounds. Earlier bounds
remain in provenance and `forecast-intervals-before.json`. Scheduled jobs may add
subsequent rows; 3,885 is the snapshot count, not a permanent database total.

Coverage below is retrospective selection evidence, **not independent validation**
of the selected policy. Fourteen of 42 level choices have no qualifying method;
the closest existing method is retained with an explicit failure flag. If needed,
issued 95% bounds are widened to contain the 80% interval. The archived coverage
table describes each selected family, not an independently rescored combined
nesting policy.

| City | Horizon | 80% method / coverage / gate | 95% method / coverage / gate |
| --- | --- | --- | --- |
| bengaluru | 1 | quantile_lightgbm / 71.20% / FAIL | quantile_lightgbm / 89.13% / FAIL |
| bengaluru | 2 | quantile_lightgbm / 73.37% / FAIL | quantile_lightgbm / 86.96% / FAIL |
| bengaluru | 3 | quantile_lightgbm / 73.37% / FAIL | quantile_lightgbm / 86.41% / FAIL |
| chennai | 1 | quantile_lightgbm / 72.83% / FAIL | quantile_lightgbm / 91.30% / pass |
| chennai | 2 | quantile_lightgbm / 73.91% / FAIL | quantile_lightgbm / 91.30% / pass |
| chennai | 3 | quantile_lightgbm / 74.46% / FAIL | quantile_lightgbm / 94.02% / pass |
| delhi | 1 | quantile_lightgbm / 80.43% / pass | quantile_lightgbm / 96.74% / pass |
| delhi | 2 | quantile_lightgbm / 79.89% / pass | quantile_lightgbm / 96.20% / pass |
| delhi | 3 | quantile_lightgbm / 85.87% / pass | quantile_lightgbm / 97.28% / pass |
| hyderabad | 1 | conformal / 78.26% / pass | conformal / 96.20% / pass |
| hyderabad | 2 | quantile_lightgbm / 78.80% / pass | quantile_lightgbm / 96.20% / pass |
| hyderabad | 3 | quantile_lightgbm / 78.80% / pass | quantile_lightgbm / 95.65% / pass |
| kolkata | 1 | quantile_lightgbm / 80.43% / pass | quantile_lightgbm / 94.02% / pass |
| kolkata | 2 | quantile_lightgbm / 82.61% / pass | quantile_lightgbm / 94.57% / pass |
| kolkata | 3 | quantile_lightgbm / 79.89% / pass | quantile_lightgbm / 95.65% / pass |
| mumbai | 1 | quantile_lightgbm / 82.07% / pass | quantile_lightgbm / 96.20% / pass |
| mumbai | 2 | quantile_lightgbm / 83.15% / pass | quantile_lightgbm / 96.20% / pass |
| mumbai | 3 | conformal / 78.80% / pass | quantile_lightgbm / 95.65% / pass |
| pune | 1 | conformal / 71.20% / FAIL | conformal / 88.59% / FAIL |
| pune | 2 | quantile_lightgbm / 70.65% / FAIL | quantile_lightgbm / 86.41% / FAIL |
| pune | 3 | quantile_lightgbm / 73.91% / FAIL | quantile_lightgbm / 91.30% / pass |

Failures: Bengaluru all three horizons at both levels; Chennai all three at 80%;
Pune all three at 80%, and horizons 1–2 at 95%. Quantile target distributions can
place the separate unchanged point model outside an interval. The API/UI retains
and explains that outcome instead of altering point forecasts or stretching bounds.

### Local language model

Installed RAM was 17,179,869,184 bytes (16 GiB). The requested floor of 60% gives
`[wsl2] memory=9GB` in `C:\Users\Andry\.wslconfig`. The earlier report stated there was no existing file;
that historical absence cannot be independently reconstructed. Docker/WSL were cleanly restarted. The resumed
2026-10-15 measurement gave MemAvailable 6,909,865,984 bytes, exceeding the actual
model 1,929,912,432 bytes plus 3,221,225,472 bytes (3 GiB) headroom.

The capability is **extractive retrieval with verified citations**, not a
certified question-answering assistant. The fix pass now defaults to extractive retrieval and disables the `llm` profile.
The retained experimental opt-in Ollama model is `qwen2.5:3b-instruct`, Q4_K_M, digest
`357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
Model files and Docker's data disk reside on D:. Generation uses temperature 0,
seed 20261010, context 16384, maximum 1600 new tokens, four CPU threads and
keep_alive=0. The provider-only evaluation uses the original 120 frozen questions;
the previous extractive evaluation is preserved.

| Ollama frozen evaluation metric | Actual result |
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

Completed 2026-10-15T15:16:48.629771+00:00; MLflow run `a70d7abfbf0149b8a4a1f78b8dad544b`.

The strict verifier requires a literal supplied `[E#]` alias and exact source
sentences/table rows. Unsupported output becomes a refusal. Do not interpret
high grounding among retained claims as a high answer rate. The frozen forecast
expectations predate the new interval bounds and new interval-policy provenance;
snapshot mismatches must be reported separately from generation correctness.
See the appended provider results in PHASE5. Only 2/80 literature questions
retained an answer, 0/30 available-data questions were answered, and all 10
unanswerable questions were refused. The 100% emitted grounding/citation scores
apply to just two retained sentences/citation uses, not to all 120 questions.

With inference finished and the reranker still resident, the final warm check
measured 5,394,948,096 bytes available against 5,151,137,904 bytes required
(actual model + 3 GiB). This also passes; the margin is small. See `warm-memory-gate.json`.

### Resident reranker and candidate gate

A dedicated single-process Celery inference worker retains the same pinned
float32 cross-encoder (maximum length 1024, batch 2). HTTP embedding requests
release their embedding model; they do not unload the resident reranker.
All 80 frozen literature questions were measured for both candidate counts.

| Metric | Fused 40 | Fused 24 |
| --- | --- | --- |
| recall_at_5 | 0.803125 | 0.809375 |
| recall_at_10 | 0.884375 | 0.903125 |
| hit_at_10 | 0.9 | 0.9125 |
| mrr | 0.6932707917082916 | 0.7010148358585859 |
| seconds | 5.121477811050002 | 2.317789466399995 |

Recall@10 improved by 1.875 percentage points, satisfying the predeclared maximum
one-point drop gate, so 24 is retained. The `seconds` row above is mean
**cache-assisted evaluation** time and is not uncached interactive latency.

| Uncached L001 stage | Before (seconds) | After resident worker (seconds) |
| --- | --- | --- |
| Cold 40 | 80.36799 | 246.86437 |
| Warm 40 | 47.59473 | 156.84292 |
| Embedding request | 10.3666 | 224.39866 |
| Rerank 40 after embedding | 66.5089 | 204.19029 |
| Warm 24 | not measured | 87.96909 |

These actual uncached after timings are slower. They do **not** establish a latency
improvement. They were recorded on different days under different competing CPU
workloads on this laptop. Identical 40 candidate IDs had exactly matching scores;
the 24 subset differed by at most 4.2841e-8. Residence fixes model lifetime and the
24-candidate gate improves the measured retrieval tradeoff; CPU latency remains
a material limitation. Evidence: `reranker-before.json`, `reranker-after.json`,
`rerank-candidate-gate.json`.

## Engine design and references

`apps/vayusim/physics/` imports NumPy only. Geographic projection, population,
weather, Django/database and artifact generation are external adapters.
The current engine version is **gaussian-briggs-1.1.0**.
Point contributions broadcast over receptors and source batches of at most 20;
area midpoint lattices and line midpoint segments conserve total Q and then use
the same superposition. They approximate extended sources, not analytic ISC
area/line integrals. Upwind receptors and the first metre downwind are excluded.

With Q in g/s, the output concentration in µg/m³ is

`C = 10^6 Q/(2π u σy σz) exp(−y²/(2σy²))`
`× [exp(−(z−H)²/(2σz²)) + exp(−(z+H)²/(2σz²))]`.

The default receptor is z=1.5 m. Reflecting images at ±2nL converge elementwise
to a relative contribution below 1e-6. At σz/L≥1.6, the vertical factor becomes
`sqrt(2π) σz/L`, giving a vertically uniform profile. Effective releases above
the lid, or receptors above it, contribute zero and are flagged. Applying an
observed lid also in stable conditions is an educational adaptation; it is not
the unlimited stable mixing assumption of ISC and is not model equivalence.

Briggs σy/σz rural/urban tables are transcribed from
[Brune, PSU METEO532 Table 2.3](https://personal.ems.psu.edu/~brune/m532/m532_theatmosphere.htm).
They are extrapolated with a flag outside the cited 100 m–10 km range. Urban is
the city default. The adjacent class-B worked example conflicts with its own
σy table; coefficients were not tuned to reproduce that inconsistency.

Wind is FROM the supplied meteorological bearing. Wind at the physical release
height is `max(1, u10 (h/10)^p)`. Exponents from
[ISC3 Volume II](https://gaftp.epa.gov/aqmg/SCRAM/models/other/isc3/isc3v2.pdf),
printed p.1-5 Table 1-1, are rural A–F .07/.07/.10/.15/.35/.55 and urban
.15/.15/.20/.25/.30/.30. Low 10 m or release-height wind is flagged.
Release height is not silently clamped to 10 m.

Briggs buoyancy `Fb = g v d²(Ts−Ta)/(4Ts)`, momentum `Fm = v²d²Ta/(4Ts)`,
stable/unstable final and distance-dependent transitional rise and stack-tip
adjustment follow ISC3 printed pp.1-6–1-11, Eqs.1-7–1-29. g=9.80616 m/s²;
stable E/F potential-temperature gradients are .020/.035 K/m. Zero flow or
diameter disables rise. Cold exhaust uses momentum only and is flagged because
dense-gas sinking is not modelled.

Stability is a disclosed approximation: measured-radiation SRDT by day using
[EPA Meteorological Monitoring Guidance](https://www.epa.gov/sites/production/files/2020-10/documents/mmgrma_0.pdf),
Table 6-7 printed p.6-16 (925/675/175 W/m²), and Turner cloud/wind classes at
night. It is **not full Turner**, because cloud ceiling and nighttime delta-T
are unavailable. Daytime classes use measured radiation; an overcast daytime
hour is not overridden using the separate nighttime cloud table.

If BLH is absent, [CDM2 Table 5, printed p.15](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9101EO4F.TXT)
supplies stability ratios. L=1500 m is the Turner Problem 6 illustrative inversion;
Lmin=500 m is an illustrative screening case in
[EPA Screening Procedures, Figure 4-19 printed p.4-62](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=2000F86J.TXT).
Transferred values A2250, B/C/D-day1500, D-night1000, E/F500 m are educational
assumptions, **not Indian climatology, measured BLH or universal EPA defaults**.
Every affected result contains the fallback and citation flags. The three final
real-weather examples below all have warehouse-supplied BLH; none needs this
fallback. Open-Meteo/ERA5 grid-point meteorology is archived model/reanalysis
data, not direct measurements of BLH. The provenance `observed` flag distinguishes
a supplied warehouse value from the illustrative fallback, not an instrument.

## Numerical checks and scope

The [fix pass](#fix-pass) contains the authoritative two tables: passing formula
checks and Briggs-versus-Martin scheme comparisons. Same-formula arithmetic
checks implementation, not independent physical validity. Cimbala PDF p.3 supplies
the Gaussian inputs; Turner physical pages remain **unverified** and excluded
from the validation pass count. The inconsistent Brune class-B paragraph is also
excluded. No end-to-end physical validation is claimed.

All six required Hypothesis properties pass: reflected crosswind mass integral,
crosswind symmetry, Q linearity, source superposition, non-increasing ground
maximum with increased effective release height at identical wind/dispersion,
and zero upwind concentration. The stack-height property explicitly fixes
transport and has z=0/no rise/no lid; it does not claim every coupled plume-rise
configuration is monotonic. Three stored independent scalar-oracle golden fields
pass. Additional tests cover lid mass/uniform mixing, A–F heterogeneous rising
source broadcasting, stability tables, wind profiles, area/line mass conservation,
strict input rejection, synthetic raster count/support, cache uniqueness,
concurrent lazy materialisation and server-computed RAG provenance.

Pre-audit container output: **242 passed, 149 warnings in 39.09 s**. All 41 original
test/support/fixture files are SHA256-identical; all 183 original tests remain.
The frozen question hash and all 32 original Phase 5 result artifacts also match.
Ruff: `All checks passed!`; format: `261 files already formatted`.

## Performance

| Sources | Median ms | Min ms | Max ms | Timed repetitions |
| --- | --- | --- | --- | --- |
| 1 | 6.127 | 5.588 | 7.398 | 20 |
| 20 | 255.313 | 212.995 | 319.776 | 20 |

Measured on Intel Core i5-13420H (8 cores/12 logical processors), 16 GiB RAM,
Windows 11 with the 9 GB WSL2 limit; Python 3.12.15/NumPy 2.5.3 in Linux Docker.
200×200 receptors, float32 result, one warmup before 20 repetitions, one NumPy
thread. This times the pure engine, including buoyant rise, not projection,
population reprojection or response artifacts. The local Qwen evaluation and
normal Docker services were active. The one-source <100 ms target passes;
20-source latency is reported without an invented target. Source broadcasting
increases working memory and does not imply a guaranteed multicity speedup.
Reproduce with `docker compose exec -T web python manage.py verify_vayusim`.

## Real-data integration and three actual examples

Hourly WeatherObservation timestamps are UTC. An IST hour starting 06:30 UTC
uses its 07:00 UTC midpoint observation, which avoids shifting the IST half-hour
offset. Missing required weather is unavailable, not synthetic observations.

WorldPop 2025 counts become geodesic source-cell population densities, warped
by area-weighted rasterio reprojection onto the rotated AEQD grid. A separate
fractional support mask prevents nodata from being extrapolated over missing
areas. Known population counts are retained; unknown population is excluded,
and support area is reported. Reprojection is an approximate finite-cell
method, tested for conservation on known synthetic grids, not a census.

Every demonstration is a **hypothetical 1 g/s source**. All three deliberately
use the same hypothetical 1 g/s
primary PM2.5 point release at 50 m, diameter/velocity 0 (no rise), 293.15 K
(irrelevant at zero flow), urban dispersion, z=1.5 m, 10 km/50 m grid.
These are declared software demonstration assumptions, not measured facilities,
AP-42 defaults or source-apportionment findings. Weather, population and the
computed scenario outputs are real stored runs.

| City / IST hour / ScenarioRun | Class | Peak added µg/m³ | Nearest source–peak m | Population >1 µg/m³ | Population support | Population-weighted increment µg/m³ |
| --- | --- | --- | --- | --- | --- | --- |
| Delhi, 2025-01-15 12:00 IST, #62 | C | 15.641839 | 176.777 | 11,787.141 | 91.306% | 0.025990 |
| Mumbai, 2025-07-15 15:00 IST, #63 | C | 11.536741 | 176.777 | 5,906.777 | 93.905% | 0.029134 |
| Hyderabad, 2025-11-15 20:00 IST, #64 | F | 18.990891 | 725.431 | 66,300.357 | 96.022% | 0.245285 |

| City | u10 m/s | Wind FROM ° | Air K | Shortwave W/m² | Cloud fraction | Warehouse BLH m | Same-hour nearby CPCB readings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Delhi | 3.26 | 126.0 | 285.65 | 501.0 | 0.71 | 815.0 | 33 |
| Mumbai | 4.42 | 227.0 | 300.65 | 296.0 | 1.0 | 460.0 | 25 |
| Hyderabad | 2.06 | 61.0 | 292.45 | 0.0 | 0.0 | 65.0 | 8 |

![Actual stored modelled-increment fields, with explicit hypothetical source assumptions](assets/phase6a-scenarios.png)

Population is modelled and fractional, so table decimals are retained for audit;
the UI rounds people. Population values cover the modelled footprint only and
its known raster support, not an entire city. At fixed weather, source/release
geometry and grid, concentration and peak scale linearly with Q; population
above a fixed concentration threshold does not. Concentrations are hourly increments from these assumed
sources. CPCB/OpenCity-CPCB readings are quality-OK nearby **measured total (all
sources)** within the same IST hour and remain separate; they are never added.
Peak is a 50 m lattice maximum, not a continuous analytical peak. All runs
retain assumptions, exact weather row/source, population SHA, engine version,
input hash, limits and flags. Old engine-version runs are retained.

Delhi 2025-01-15 day mode returned **24/24 available hourly summaries**. Grids
were initially lazy; the first metadata request successfully materialised grid
and contours. All three runs' detail, shared scenario, binary, JSON and PNG
requests returned HTTP 200; each default binary is 160,000 bytes.

## Presets and citations

| Family | Geometry | AP-42 source section | Physical numeric defaults |
| --- | --- | --- | --- |
| Thermal power plant | point | 1.1 Bituminous/subbituminous coal combustion | all null; required |
| Brick kiln cluster | area | 11.3 Brick/structural clay products | all null; required |
| Industrial boiler | point | 1 External combustion; select actual fuel/controls | all null; required |
| Crop-fire field | area | 2.5 Open burning; verify crop/activity/fine fraction | all null; required |
| Road dust resuspension (stable ID `highway`) | line | [13.2.1 January 2011](https://www.epa.gov/sites/default/files/2020-10/documents/13.2.1_paved_roads.pdf), §13.2.1.1 p.13.2.1-1 and §13.2.1.3 p.13.2.1-4 (PDF pp.1,4); excludes exhaust/brake/tire wear | all null; required |

Each preset links to the [EPA AP-42 compilation](https://www.epa.gov/air-emissions-factors-and-quantification/ap-42-compilation-air-emissions-factors-stationary-sources)
and its exact section. No universal, defensible facility emission rate, height,
diameter, exit velocity or temperature was established. Those five fields are
null and required. Activity-based total particulate factors are not silently
converted to instantaneous primary PM2.5 g/s. Area/line geometry and subdivision
counts also require explicit input. No numbers were invented to make a preset
appear complete.

The road preset requires the total segment primary PM2.5 rate in g/s; it does
not accept a g/VKT emission factor or a per-metre rate as that total. The cited
January 2011 road-dust equation excludes exhaust, brake wear and tire wear.
No transferable fleet-specific exhaust factor was established in this audit;
exhaust emissions remain a required independently justified user input for a
separately specified source, not an implied component of this preset.

## Stored evidence and assistant integration

`vayusim_run(run_id)` is a strict whitelisted tool returning stored summary,
engine version, hash and scenario provenance. `/api/rag/explain/` with
`context_type=scenario,payload.run_id` combines that tool with retrieved
literature. Arbitrary client parameters remain unverified context. The separate
five-question VayuSim set checks exact stored values, stability/provenance,
population/support, separation from measured totals and limitations; all five
pass exact citation support with the deterministic extractive provider and
keyword literature retrieval. This is integration evidence, **not a measured
five-question generative LLM quality claim**, and not part of the frozen Phase 5
evaluation. The independent provider results are reported above.

An additional real HTTP request to the default-provider explanation endpoint
returned 200 in 405.516 s using Ollama. Its tool result exactly matched Hyderabad
ScenarioRun 64; the deliberately incorrect client peak 999999 was absent. The
generated explanation omitted valid evidence aliases and was rejected to a
refusal, with no generation or retrieval exception. This proves live routing
and stored-value isolation, **not successful generative explanation quality**.
The complete response is `default-provider-explain.json`.

Lazy materialisation reads the run's canonical input/weather snapshot, not the
editable Scenario record. A regression changes a scenario's emission by 100×
after summary creation and confirms its historical lazy grid still matches
the original peak/hash. This preserves result identity across future edits.

## Whole-site UI and browser verification

The additional requested presentation work gives all six main pages a shared
responsive navigation, typography, green/ivory palette, accessible labels, cards,
empty/loading/error states and explicit dates. Overview cards use actual stored
counts/results. Forecasts show horizon intervals, failed coverage warnings and
actual SHAP contributions. Research shows fixed-panel/all-station distinctions,
intervals and the observed calendar gap. Library search exposes source/licence
and page links. Ask renders safe Markdown plus source links and plaintext audit.
VayuSim supports click/drag placement, cited source families, manual/real weather,
PNG/contours, exposure, measured background and share/download/explain controls.

MapLibre GL JS 5.24.0 and its BSD-3-Clause licence are vendored. The basemap is
OpenStreetMap raster with visible attribution; no paid key, offline bulk fetch
or prefetch. The UI is a one-source verification form; the API supports multiple
sources. Shared one-source scenarios repopulate city, time and source values;
shared multiple-source results are viewable, with edits directed to the API.

Headless Microsoft Edge/Playwright returned HTTP 200 on all six pages at both
1440 px and 390 px, without horizontal overflow or JavaScript errors. Actual
interactions exercised mobile navigation, city selection (three forecast cards),
research mode (seven NCAP cards), AERMOD library filtering, example-question fill,
shared Hyderabad output and an actual map run/overlay. Browser artifacts are in
the verification folder; screenshots are retained under `.tools/phase6a-validation/`.

## Failures found, root causes and corrections

| Failure | Root cause / correction | Measured rerun |
| --- | --- | --- |
| Docker unavailable on resume | Installed Docker Desktop was stopped; start hidden and bring Compose up | Services running/healthy; health 200 |
| Resident reranker lacked Django model registry | Standalone entrypoint needed django.setup() before database result backend | Resident worker requests returned scores matching original |
| Population warp overstated nodata-border support | GDAL excludes nodata from density average; preserve a separate fractional support mask and do not extrapolate | Synthetic count/partial-nodata checks pass; final real exposure recomputed |
| GDAL denormal nodata warning | Zero destination nodata was converted to a tiny sentinel; use NaN nodata and explicit mask | No warning in final reprojection checks |
| New transactional test missing analytics table after original migration test | Original test intentionally restores warehouse-only migration; arrange full leaf schema inside new test | 242 full-suite tests pass; original test unchanged |
| Hypothesis generation timing health check under concurrent inference | CPU contention and Windows bind-mounted cache; put storage in /tmp and briefly pause inference during test, then unpause | Unchanged 53 targeted tests pass, then all242 pass |
| Map repeated-run wait could hang | map.loaded() can be false during tile refresh after load event; cache initial load Promise | Browser map run/share checks pass |
| Shared form showed default city/blank assumptions | Map result was loaded without repopulating controls; restore saved inputs and robust IST datetime | Shared Hyderabad form/output browser check passes |
| Standalone verification helper import error | Script path omitted project PYTHONPATH; invoke with -e PYTHONPATH=/app | Five scenario evidence checks pass |
| Local model refuses most answerable questions | Model output omits required evidence aliases and/or exact supported text; verifier rejects claims | No verifier weakening or synthetic fallback score; completed 120-question results above |

The pre-audit 149 suite warnings were retained, primarily Django 6 URL-scheme deprecation,
NumPy generic timedelta deprecation and statsmodels convergence warnings.
The preexisting netCDF4/NumPy ndarray-size warning, SHAP/matplotlib deprecations
and MLflow type-hint warning also remain. The original baseline log contains
the same warning classes; they were not suppressed or treated as proof of
compatibility outside the tested paths.
`check --deploy --settings=enviroinsights.settings.prod` reports **no issues
(0 silenced)**, so there are no deployment warnings to list or suppress.
Migration drift and OpenAPI validation checks pass.

## Decisions

1. Preserve original tests, gold questions, original extractive artifacts and
   old simulation runs; new outputs have separate directories/version hashes.
2. Keep the requested retrospective interval-selection rule even when no method
   passes; flag the 14 failures and preserve unchanged point forecasts.
3. Adopt 24 candidates on its predefined recall gate; do not claim a latency
   improvement contradicted by uncached measurements.
4. Keep source-specific physical defaults null when citations do not establish
   them. Demonstration source assumptions are explicit and distinct from data.
5. Use the measured-radiation/cloud-table stability hybrid and cited BLH transfer
   anchors with persistent flags rather than claiming unavailable full Turner
   inputs or local climatology.
6. Preserve unknown population support. Report known hourly added exposure;
   do not invent zeros outside the raster or extrapolate counts over nodata.
7. Use local AEQD and bounded source/receptor broadcasting. Performance numbers
   cover the engine only and include actual background laptop CPU contention.
8. Fulfil the later whole-site UI request while leaving Phase 6B's cinematic
   frontend and additional research scope for its own phase.

## Limitations

Primary PM2.5 only: no chemistry, secondary aerosol, deposition or removal.
Flat terrain and uniform steady hourly meteorology; no building downwash beyond
stack-tip. Calm wind, near-field coefficient extrapolation, stable shallow lids,
cold exhaust and extended-source discretisation need caution. No regulatory
assessment or claim of equivalence with AERMOD. Real regulatory work needs
appropriate emissions, meteorological preprocessing and model configuration.
The demonstration has no measured facility inventory. BLH transfer defaults
are illustrative. WorldPop is modelled 2025 population with missing support;
exposure is not daily/annual exposure, dose, health impact or causal attribution.
Partial support, grid resolution and assumed source parameters limit precision.
Reranking/generation are CPU-bound and can take minutes; strict citation support
does not measure semantic correctness or completeness. Existing data gaps,
fixed-panel restrictions, causal limitations and replay labels still apply.
The development server and public local scenario shares are not a production
authentication/hosting deployment.

## Phase 6B API contract

| Endpoint | Contract |
| --- | --- |
| `POST /api/vayusim/run/` | Strict finite JSON, city slug, centre `[lon,lat]`, 1–20 sources, real/manual weather, offset-aware datetime; returns run ID, flags, summary, contours, URLs and cache flag |
| `GET /api/vayusim/runs/<id>/` | Re-open an actual stored run and its provenance |
| `GET /api/vayusim/grid/<id>.bin` | Row-major little-endian float32; default200×200=160000 bytes; `X-Grid-Header` points to metadata |
| `GET /api/vayusim/grid/<id>.json` | Shape, dtype/order, six affine coefficients, AEQD WKT, four lon/lat corners in image order, receptor height, units, label, version/hash, flags, limits and contours |
| `GET /api/vayusim/grid/<id>.png` | Transparent at ≤1 µg/m³, category-colour overlay; hourly increment, **not CPCB AQI** |
| Contours | GeoJSON FeatureCollection in WGS84 lon/lat, thresholds1/15/60/120 plus user values; may be empty; metadata request materialises lazy contours |
| `GET /api/vayusim/scenarios/<slug>/` | Stored inputs and versioned runs for a shared scenario |
| `POST /api/vayusim/day/` | Real weather only, uses the supplied datetime's IST date, 24 entries with availability/reason and summary; grids/contours on demand; **24 independent hours**, not averaged exposure |
| `GET /api/vayusim/presets/` | Five source families, null physical defaults, required inputs and citations |
| `GET /api/vayusim/stations/?city=&datetime=` | Same-hour nearby measured totals; never summed with modelled increment |
| `POST /api/rag/explain/` | `context_type=scenario`, `payload.run_id` selects stored evidence; returns answer, citations, provider and verification |

Affine maps **pixel corners** to east/north metres; sample receptors at
`(column+0.5,row+0.5)`. Wind rotates the grid. PNG corners are top-left,
top-right,bottom-right,bottom-left, with their actual geographic positions;
do not assume an unrotated north-up image. Validate returned shape/resolution.
The frontend must display increment versus measured-total labels, hourly scope,
real/manual weather, actual date and source assumptions, source citations,
population support/unavailability, all flags/limits and replay/provider
verification. Do not animate missing hours as zeros or hide fallback weather.

An older run without a retained grid cannot be silently materialised by a new
engine under its old version label. Its summary stays available; grid requests
return400 with instructions to submit its saved inputs as a new versioned run.

Full commands and measured output are recorded in [VALIDATION](../VALIDATION.md).
Structured local proof files are under `data/results/vayusim/verification/`.
Their final manifest hashes retained files; downloaded scientific source
manifests are under `data/raw/vayusim/`. Re-run the committed verification
command against the retained database/raw assets to reproduce the examples.

## Phase 6A audit

Completed from commit `b5136b2` in `D:\EnviroInsights-India`.
No Phase 6B work, new language-model evaluation, prompt tuning, coefficient
fitting, evaluation-label edits or original-test changes occurred. Structured
measurements are in [PHASE6A_AUDIT_METRICS.json](PHASE6A_AUDIT_METRICS.json).
Every shell command and actual output, including failed attempts, is retained
in [VALIDATION](../VALIDATION.md#phase-6a-audit-command-journal-15-october-2026).

### Decisions

1. Keep 5% sigma and 10% concentration tolerances unchanged. Use independently
   transcribed source values; classify same-formula arithmetic as formula check
   only. A different published parameterisation is not a fitting target.
2. Keep the existing candidate default only when the gain has an evidenced cause
   and the original maximum one-point Recall@10 drop gate holds against both
   fresh K=40 and the historic K=40 baseline. K=32 is diagnostic, not a newly tuned winner.
3. Score each frozen query's 40 pairs freshly once and filter that fixed scored
   set at 24/32/40. This isolates candidate competition without conflating it with
   batch/model differences. Independently time actual uncached 24/32/40 RPCs.
4. Relabel stable ID `highway` as road dust resuspension, because the verified
   January 2011 AP-42 pages exclude exhaust/brake/tire wear. Keep the rate required.
5. At the audit, preserve prompts, provider configuration and frozen labels. The
   later fix-pass decision below supersedes only the provider default. Decline the optional
   larger-model evaluation; this audit needs an accurate status, not model tuning.
6. Back up the current 9GB WSL file. The prior report records no original existed;
   do not claim a nonexistent historical backup. Keep resource and quality gates separate.
7. Fix project-controlled warning causes with explicit URL-form settings and
   accurate model input/return types. Leave upstream warnings visible with reasons;
   do not edit original tests, suppress categories or change frozen estimator settings.
8. Derive API disclosures from retained run inputs. Do not rewrite old numerical
   summaries, hashes or engine versions. Retain original result artifacts separately.

### Textbook audit and corrections to earlier claims

The original mixed pass/fail table is superseded by the [fix pass](#fix-pass).
The 14 rounded sigma references are arithmetic from the same published formulas,
not independently printed numeric observations. Their authoring provenance beyond
the original test docstring remains **unverified**. Cimbala PDF p.3 supplies a
published-input Gaussian formula check. Its Martin sigmas are a separate scheme
from Briggs: their differences exceed 5%/10%, but are not validation errors.
Turner physical pages remain unverified. Brune Table 2.3 agrees with the code;
the adjacent paragraph is the inconsistent reference. All original measured
values remain in the historical audit artifacts, without promoting them to
independent physical validation.

### Highway citation decision

Stable ID `highway` now displays **Road dust resuspension**. The retained
[AP-42 January 2011 §13.2.1](https://www.epa.gov/sites/default/files/2020-10/documents/13.2.1_paved_roads.pdf),
§13.2.1.1 printed p. 13.2.1-1 (PDF p. 1), explicitly separates resuspension from
exhaust, brake wear and tire wear. §13.2.1.3 printed p. 13.2.1-4 (PDF p. 4) gives
the dust equation and separates other vehicle emissions. No applicable generic
India-fleet exhaust factor was established; it remains required if modelled as
a separately justified source. All five physical defaults remain null. The
required emission is total segment primary PM2.5 g/s, not g/VKT or g/s/m.
The preset/API citation table and limitations now state this scope explicitly.

### Reranker comparison and cause

All 80 frozen literature queries were freshly scored without the pair cache,
once over their fused 40. K=24/32/40 use subsets of the same fixed pair scores.
Model revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`, CPU float32,
1024-token limit, batch size 2, four Torch threads and seed 20261010 are unchanged.
RRF k=60 and both first-stage limits of 40 are unchanged. Query vectors were cached.

| K | Recall@5 | Recall@10 | MRR through K | Cold L001 s | Warm L001 s |
| --- | --- | --- | --- | --- | --- |
| 24 | 0.809375000000 | 0.903125000000 | 0.701014835859 | 63.861518 | 31.741508 |
| 32 | 0.803125000000 | 0.884375000000 | 0.700181277056 | 76.974456 | 42.284033 |
| 40 | 0.803125000000 | 0.884375000000 | 0.693270791708 | 102.609534 | 52.454254 |

Cold/warm timings are each one actual uncached L001 RPC per K, in order 40, 32, 24.
The worker was restarted before each cold measurement. Cold refers to the model
process, **not a flushed OS file cache**; warm means the immediately repeated
RPC. Pair caches were bypassed for both. Other normal services remained running.
These are measured samples, not confidence intervals or full-corpus averages.
The full fresh K=40 comparison averaged 63.425801 s/query;
other audit checks and the suite ran during parts of that pass. It is not a
controlled speed comparison with the earlier Phase 6A timings, which remain above.

Historical K=40 ordering restricted to the 24 candidates equals K=24 for 80/80 queries.
Fresh K=40 and K=24
orders each match their historic counterparts for
76/80 and
77/80 respectively;
fresh K=40 candidate sets match for 80/80.
This evidences candidate competition, rather than a resident-model improvement.
The retained pair cache reconstructs 80 historical
orders from 80 queries with complete
cached pairs. Fresh scores differ from those cached values by at most
7.45058059692e-08. Near-tie movement changes some
ordering: 79/80 top-10 orders and
80/80 top-10 sets are exactly unchanged. The precise
floating-point kernel/batching mechanism is **unverified**; measured drift and
individual moved scores/ranks are retained in `reranker-score-drift.json`.
For the actual independent K timing probes the maximum warm-prefix score
difference from 40 is 4.76837158203e-07;
the largest cold/warm difference is 0.
Ties use ascending chunk ID. Exact score ties among the displayed gain/displacer
pairs: `False`. The gain rows and actual pair scores are:

| Query | Known-gold chunk | Rank40 | Rank24 | Fixed pair score | Removed higher-scoring non-gold chunks |
| --- | --- | --- | --- | --- | --- |
| L025 | 50660 | 13 | 10 | 0.073289424181 | 50644 (0.264985233545, rank1), 50681 (0.105676166713, rank10) |
| L072 | 43818 | 14 | 9 | 0.0752021819353 | 43545 (0.604610085487, rank2), 50687 (0.30640399456, rank5), 47410 (0.189759835601, rank9), 43796 (0.180791005492, rank10) |

Loss rows (query, lost known-gold IDs, Recall@10 change): `[('L023', [50659], -0.5)]`.
Two historical gains of 1 and one loss of 0.5 give `(1+1-0.5)/80=0.01875`,
exactly the earlier 1.875-point gain. Non-gold means absent from these incomplete
frozen labels, not independently judged irrelevant. This is a repeated frozen
benchmark audit, not new out-of-sample evidence or a tuning exercise.
Recall@5/10 is measured before the service's evidence filtering. For example,
L025's gained gold is rank 10 with score 0.07328942418, below the existing 0.2
relevance floor and outside the eight retained passages. That recall gain does
not itself establish improved returned evidence or answer quality. The floor
and retained-passage count were not changed.

**Chosen default: 24.** Cause evidenced: `True`.
Fresh40 minus 24 Recall@10=-0.018750000000; historic K=40 minus 24=-0.018750000000,
both compared with the unchanged maximum 0.01 drop gate. K=32 is reported without
selecting a new optimum from this benchmark. Evidence retains every candidate
ID, text SHA, score and per-query metric in `reranker-state.json`.

### Assistant resource and quality status

Installed RAM is 17,179,869,184 bytes (16 GiB); Windows
usable RAM is 16,852,574,208 bytes. These are separate
actual CIM measurements. `.wslconfig` exists at `C:\Users\Andry\.wslconfig`
with `[wsl2] memory=9GB`. The current file is backed up at
`C:\Users\Andry\.wslconfig.phase6a-audit-20261015.bak`; both files have SHA256
`d4f748ea8f222563e1beb8319e62496c62635ce052aa4dd380ee332b73375268`. There was no original backup at audit start.
The prior report records no pre-Phase 6A file existed; that historical absence
cannot be independently reconstructed now. The new file preserves current
settings and is **not** misrepresented as a pre-change original.

The readiness endpoint returned **HTTP 200**, all
checks true. After the full evaluation/tests, with the reranker still resident
and normal services running, MemAvailable was
4,103,503,872 bytes, compared with the installed Qwen
file 1,929,912,432 bytes + 3 GiB headroom =
5,151,137,904 bytes; resource gate=False.
An earlier audit measurement was 5,415,559,168
bytes and passed the same gate. The **final measurement fails**, so memory
eligibility is not a permanent certification. The cause of the lower final
availability is **unverified**; no allocator/kernel change is asserted or tuned.
No larger model was downloaded/evaluated, and no provider/prompt was tuned.

The final description in README, Architecture, this report and the Ask page is
**extractive retrieval with verified citations**. The earlier audit retained the experimental Qwen configuration; the fix pass
now selects extractive by default and stops Ollama, keeping generation opt-in. Its existing 120-question evaluation retained
only 2/80 literature answers, 0/30 available-data answers and refused 10/10
unanswerable questions. Two supported citations do not certify answer quality.
The earlier 0.9 data-snapshot match is not numeric answer correctness. The
answer-quality acceptance gate remains **not passed**; the resource gate does
not change that status.

### Warnings and final tests

Before: 149 warnings, including
2 project-controlled causes. After:
**147 warnings, zero project-originated**, all remaining
warnings upstream. DRF warnings: 0. Original test files are byte-identical.
Source is classified by the implementation that emits the warning, not just
the reported stacklevel callsite; standalone pandas construction reproduces
the 142 datetime warnings without any project import.

| Origin | Category | Exact message | Before | After | Action / reason retained |
| --- | --- | --- | --- | --- | --- |
| Django / project URL-form configuration | RemovedInDjango60Warning | The default scheme will be changed from 'http' to 'https' in Django 6.0. Pass the forms.URLField.assume_scheme argument to silence this warning, or set the FORMS_URLFIELD_ASSUME_HTTPS transitional setting to True to opt into using 'https' as the new default scheme. | 1 | 0 | Fixed with an explicit HTTPS URL form field and admin field overrides; no transitional setting or warning filter. |
| MLflow / project model adapter | UserWarning | Add type hints to the `predict` method to enable data validation and automatic signature inference during model logging. Check https://mlflow.org/docs/latest/model/python_model.html#type-hint-usage-in-pythonmodel for more details. | 1 | 0 | Fixed RegisteredForecaster.predict DataFrame input and ndarray return annotations; no warning filter. |
| SHAP / matplotlib | PendingDeprecationWarning | The set_bad function will be deprecated in a future version. Use cmap.with_extremes(bad=...) or Colormap(bad=...) instead. | 1 | 1 | Pinned SHAP 0.52.0 calls deprecated matplotlib colormap setters at import. No vendored library patch or blanket suppression; retain until compatible upstream upgrade. |
| SHAP / matplotlib | PendingDeprecationWarning | The set_over function will be deprecated in a future version. Use cmap.with_extremes(over=...) or Colormap(over=...) instead. | 1 | 1 | Pinned SHAP 0.52.0 calls deprecated matplotlib colormap setters at import. No vendored library patch or blanket suppression; retain until compatible upstream upgrade. |
| SHAP / matplotlib | PendingDeprecationWarning | The set_under function will be deprecated in a future version. Use cmap.with_extremes(under=...) or Colormap(under=...) instead. | 1 | 1 | Pinned SHAP 0.52.0 calls deprecated matplotlib colormap setters at import. No vendored library patch or blanket suppression; retain until compatible upstream upgrade. |
| netCDF4 / NumPy | RuntimeWarning | numpy.ndarray size changed, may indicate binary incompatibility. Expected 16 from C header, got 96 from PyObject | 1 | 1 | Error-mode trace identifies compiled netCDF4._netCDF4 import. Existing parser tests pass, but full ABI compatibility is unverified; retain visibly pending compatible wheel/rebuild. |
| pandas / NumPy | DeprecationWarning | The 'generic' unit for NumPy timedelta is deprecated, and will raise an error in the future. This includes implicit conversion of bare integers (e.g. `+ 1`). Please use a specific unit instead. | 142 | 142 | Standalone pd.Timedelta(hours=1) reproduces the warning without project imports. Root is pandas 2.3.3 Cython conversion with NumPy 2.5.3. Original tests untouched; dependency upgrade/rebuild deferred, visible and unsuppressed. |
| statsmodels | ConvergenceWarning | Maximum Likelihood optimization failed to converge. Check mle_retvals | 1 | 1 | SARIMAX maximum likelihood does not converge on the original 12-row synthetic state-leakage fixture. The adapter records the convergence flag in tuning metadata. Do not change frozen estimator iterations, edit the fixture or hide the warning. |

An initial URL fix using `FORMS_URLFIELD_ASSUME_HTTPS` exposed its own Django5.2
deprecation (intermediate 148 warnings). It was removed. Explicit URL field
classes/admin overrides choose HTTPS for schemeless curator input and preserve
explicit HTTP, blank/length metadata and stored URLs. MLflow's adapter now has
accurate DataFrame/ndarray hints; this does not claim new automatic schema certification.
No warning suppression was added. Error-mode traces identify pandas Cython and
the compiled netCDF4 extension; ABI compatibility beyond tested paths is unverified.

Final full web-container suite: **249 passed, 147 warnings in 43.62 s**.
Seven added regressions check candidate competition, stable ties, the road-dust
citation/default, source labels/scopes and URL forms. All 242 existing tests and
47 existing test/support/fixture files are unchanged. Ruff check/format, Django
check/deploy, migration drift and strict OpenAPI validation pass in the command journal.
The initial audit baseline attempt hit Hypothesis's generation-speed health
check under host contention; no health checks/assertions were weakened. The
subsequent complete run and final run are retained with their actual conditions.

### Three rerun examples

The verification command returned original runs 62/63/64. Independently recomputed
fields, peak distances and every reported population numeric value match the
retained Phase 6A report. Every example is labelled **hypothetical 1 g/s source**
in this report, README and both run/header API responses. Weather and registered
WorldPop are real archived inputs; the release remains a declared assumption.

| City / run | Source label | Peak added µg/m³ | Peak distance m | Population >1 µg/m³ | Population-weighted mean µg/m³ | Support |
| --- | --- | --- | --- | --- | --- | --- |
| delhi / #62 | hypothetical 1 g/s source | 15.641839027 | 176.776695297 | 11787.140769548 | 0.025989982135 | 0.913056536128 |
| mumbai / #63 | hypothetical 1 g/s source | 11.536741257 | 176.776695297 | 5906.777275623 | 0.029133751121 | 0.939046243713 |
| hyderabad / #64 | hypothetical 1 g/s source | 18.990890503 | 725.430906427 | 66300.357405811 | 0.245285103375 | 0.960219877969 |

At fixed weather, geometry, release parameters and grid, concentration and peak
scale linearly with Q (or a common multiplier on all sources). A fresh 2 g/s
calculation doubled every example peak exactly. Float32 underflow tails differ
by at most 1.40129846432e-45 µg/m³
when scaling before versus after output casting; bitwise equality of all tails
is not claimed. Population above a fixed threshold is nonlinear in Q.
Population values are **for the footprint only**, limited to known raster
support, not citywide exposure, census counts, dose or health impacts.

The extra verification-command benchmark measured median
7.871904 ms for one source and
287.775578 ms for 20, engine only.
Those incidental audit timings do not replace the original measured conditions.

### Frozen identity before and after

Each aggregate SHA256 hashes canonical JSON (`sort_keys=True`, compact separators)
mapping relative filename to the SHA256 of its exact bytes. The 316 Run 7 and 776
Run 21 CSV/JSON files include saved targets, OOF/evaluation labels, split audits,
predictions and metadata. The four evaluation catalogue files additionally cover
the separate VayuSim set. No file or label in these bundles changed.

| Preserved data bundle | Files | SHA256 before | SHA256 after | Identical |
| --- | --- | --- | --- | --- |
| phase3a2 | 316 | c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350 | c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350 | True |
| phase4 | 776 | 35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4 | 35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4 | True |
| phase5 | 4 | 51c3354d68206b082d1f2c240c76c8c230da06ffc23754c2a147e624b6ec0d23 | 51c3354d68206b082d1f2c240c76c8c230da06ffc23754c2a147e624b6ec0d23 | True |
| existing_tests | 47 | a93dc34f7ed9d7469f70a765dad8de26e8eed2b08563458da3563c973451e8a6 | a93dc34f7ed9d7469f70a765dad8de26e8eed2b08563458da3563c973451e8a6 | True |
| protocols | 2 | 11448872580c317d228eeef2f89c54721b34a40cddf124db11b5223b0fb24c17 | 11448872580c317d228eeef2f89c54721b34a40cddf124db11b5223b0fb24c17 | True |

Phase 5 frozen query/relevance file before and after:
`f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4`. It includes the known-gold IDs and frozen data labels.
Individual protocol hashes also match the pre-audit Git blobs:

| Protocol | Before SHA256 (baseline Git blob) | After SHA256 |
| --- | --- | --- |
| docs/results/PHASE3A2_PROTOCOL.json | 09d869e72551b31af0368b0d89a5c91510e8ecd65e6ce53605d33a704b827977 | 09d869e72551b31af0368b0d89a5c91510e8ecd65e6ce53605d33a704b827977 |
| docs/results/PHASE4_PROTOCOL.md | 395b384c7b5324ba4b4e87f87e2cdff30295be1de9a42155c85c707e417aa28c | 395b384c7b5324ba4b4e87f87e2cdff30295be1de9a42155c85c707e417aa28c |
| docs/results/PHASE5_PROTOCOL.md | d4872769cb454c79b83a275a0e3004384ef4ac5394bf633d2ab000cc4e0562a7 | d4872769cb454c79b83a275a0e3004384ef4ac5394bf633d2ab000cc4e0562a7 |

Full per-file maps are retained in `identity-before.json` and `identity-after.json`.
The result manifest hashes the measurement artifacts. The older Phase 6A manifest
describes commit b5136b2 and is retained as historical provenance; its source-code
hashes should be checked against that commit, not later changed documentation.

### Remaining limitations and claim changes

Software regression checks pass; independent Briggs sigma validation within 5%
has **not** been established. Briggs/Martin differences exceed the unchanged
tolerances and are disclosed as scheme comparisons, not validation errors.
No dispersion coefficients or source defaults were
invented to erase them. The road preset means dust resuspension only.
The Qwen quality gate remains failed, its final measured memory gate also fails,
and no new generation is cleared by this audit. The later fix pass now selects
extractive by default and stops Ollama; its local generation profile is opt-in.
CPU retrieval/generation remain slow,
known-gold relevance labels are incomplete, and upstream dependency/ABI warnings
remain visible. Existing primary-PM2.5, steady wind, flat terrain, missing
chemistry/deposition, near-field, BLH-transfer and fractional population-support
limitations still apply. This audit makes no regulatory or predictive-validity
certification and starts no Phase 6B work. No manual installation/restart/action
is required to finish the audit.

## Fix pass

Completed on 16 October 2026 from commit `05ef914` in `D:\EnviroInsights-India`.
The initial checks ran on 15 October; the user interrupted the session, then
resumed it on 16 October. **Phase 6B has not been started.** Structured evidence:
[PHASE6A_FIX_METRICS.json](PHASE6A_FIX_METRICS.json). Commands, failed attempts
and real outputs are in [VALIDATION](../VALIDATION.md#phase-6a-fix-pass-command-journal--15-october-2026).

### Decisions

1. Treat Brune Table 2.3 as the stated equation authority. Correct the fixture's
   reference/classification; keep the paragraph's 210 m as an excluded source
   diagnostic. No coefficient change is justified by the source.
2. Keep sigma 5% and concentration 10% tolerances. Formula checks and scheme
   comparisons answer different questions; report both without counting scheme
   differences or unverified Turner pages as validation passes.
3. Set extractive as the code, example-env and actual local default, including
   when API keys exist. Stop Ollama and clear the default Compose profile, while
   retaining its model and opt-in profile. This explicitly supersedes the earlier
   audit's decision to preserve provider configuration. No prompt, question,
   relevance label or provider generation parameter was tuned.
4. Keep WSL at 9GB. A readable backup of current settings is not a recoverable
   pre-change original. Report the search scope and access limits honestly.
5. Preserve the historical audit artifacts. Freshly recompute all three examples
   even though physics is unchanged, and compare every reported numeric value.
   Keep all 249 tests unchanged and add three focused regressions.

### Brune resolution and code trace

**The worked-example paragraph's numeric reference is wrong relative to its own
table; the code and table transcription agree.** The requested 27.355231%
discrepancy is against the paragraph's 210 m, not Table 2.3's class-B equation.
Source: [Brune METEO532 §2.2.5, Table 2.3 rural row B and the following paragraph](https://personal.ems.psu.edu/~brune/m532/m532_theatmosphere.htm).
This is an **unpaginated HTML source**, so no physical page number is available.
The fresh HTTP 200 source body has SHA256
`86bbdbb9ff24d66b8adaa02daffdd5deb075415960e18c1061ec673c5f28abf0`.

The path was traced as follows:

1. `weather.weather_for()` derives `stability_class`, which `service.compute()`
   passes to `physics.engine.simulate()`. The reference check explicitly supplies
   `B`; a separate synthetic day input (2.5 m/s, 800 W/m², cloud fraction 0.1)
   also derives B. Daytime classification uses EPA Meteorological Monitoring
   Guidance Table 6-7, printed p.6-16; it is the existing disclosed SRDT/night
   cloud hybrid, not a new interpretation of Brune's example meteorology.
2. The API defaults to **urban**; the reference check explicitly selects
   **rural**. `sigmas()` indexes `COEFFICIENTS[environment][stability]` without
   changing the supplied class. Rural B selects `(0.16, 0.0001, 0.12, 0, 0)`.
   Table 2.3 supplies each nonzero coefficient and exponent: sigma-y is
   `0.16*x*(1+0.0001*x)^(-1/2)`; sigma-z is `0.12*x`. The zero pair encodes
   the absence of a sigma-z correction factor, rather than a fitted parameter.
3. The grid's AEQD projection specifies `+units=m`; source/receptor deltas and
   wind rotation preserve metres. The check converts **1 km to 1000 m once**.
   Brune's stated range is `100 m < x < 10000 m`; 1000 m is inside it.
   `sigmas()` floors x at 1 m, which does not affect this case; the engine flags
   out-of-range extrapolation and excludes upwind/first-metre receptors.
4. Evaluation gives sigma-y **152.55401427929476 m**, sigma-z **120 m**.
   Urban B would instead give sigma-y **270.4493615131253 m**. Rural A gives
   **209.7617696340303 m**, resembling the paragraph's 210 m, but the cause of
   the paragraph error and any publisher erratum remain **unverified**.

Code sigma-y before → after: **152.55401427929476 → 152.55401427929476 m**.
Fixture reference focus, paragraph → table: **210 → 152.55401427929476 m**.
The new primary entry is explicitly table-derived; the earlier fixture retained
only the inconsistent paragraph as a diagnostic, rather than a table expectation.
The paragraph's 210/120 m remains visible in an excluded diagnostic. Its
sigma-y disagreement is **27.355231295573923%**. A new regression pins rural B
at 1000 m and distinguishes urban B; no physics module was edited.

### (a) Formula checks

These check code against published equations, including rounded table arithmetic.
They do not establish independent field accuracy. Sigma quantities are metres;
the last row is concentration. There are **15 passing scalar formula checks**:
14 sigma checks in seven pairs plus one supplied-sigma Gaussian check.

| Check | Equation-derived or published-input reference | Computed | Difference % | Tolerance % | Scope / result |
| --- | --- | --- | --- | --- | --- |
| rural/A sigma-y / sigma-z at 1000 m | 209.762 / 200.000 | 209.761770 / 200.000000 | 0.000109823 / 0.000000000 | 5 / 5 | PASS, formula only |
| rural/B sigma-y / sigma-z at 1000 m | 152.554 / 120.000 | 152.554014 / 120.000000 | 0.000009360 / 0.000000000 | 5 / 5 | PASS, formula only |
| rural/D sigma-y / sigma-z at 1000 m | 76.277 / 37.947 | 76.277007 / 37.947332 | 0.000009360 / 0.000874699 | 5 / 5 | PASS, formula only |
| rural/F sigma-y / sigma-z at 1000 m | 38.139 / 12.308 | 38.138504 / 12.307692 | 0.001301634 / 0.002499938 | 5 / 5 | PASS, formula only |
| urban/A sigma-y / sigma-z at 1000 m | 270.449 / 339.411 | 270.449362 / 339.411255 | 0.000133671 / 0.000075121 | 5 / 5 | PASS, formula only |
| urban/D sigma-y / sigma-z at 1000 m | 135.225 / 122.788 | 135.224681 / 122.788123 | 0.000236083 / 0.000099931 | 5 / 5 | PASS, formula only |
| urban/F sigma-y / sigma-z at 1000 m | 92.967 / 50.596 | 92.966968 / 50.596443 | 0.000034399 / 0.000874699 | 5 / 5 | PASS, formula only |
| Cimbala p.3 Gaussian, supplied Martin sigmas (concentration µg/m³) | 149300.000000 | 149314.351448 | 0.009612 | 10 | PASS, formula only |

The Gaussian equation and independent supplied inputs are visible in
[Cimbala ME433 Lesson 06E, physical PDF page 3](https://www.me.psu.edu/cimbala/me433/Lesson_Notes/ME433_Lesson_06_E_Reflecting_Ground.pdf):
Q=110 kg/s (110000 g/s), u=5 m/s, effective H=100 m, x=4850 m, z=y=0,
Martin sigma-y=278.97 m, sigma-z=87.51 m, concentration=149.3 mg/m³
(149300 µg/m³). The retained PDF was visually checked and SHA256-verified:
`ce00801de32bd1b085c8ac86096352cc398f0923b569820e622eef471ae79462`.

### (b) Scheme comparison: Briggs versus Martin

At identical Cimbala p.3 class-D inputs, rural Briggs and the printed Martin
solution differ as below. **These are differences between two dispersion schemes,
not validation errors.** They exceed the unchanged **5% sigma / 10% concentration**
tolerances. No coefficients were fitted to remove the differences. Differences
use `100*abs(Briggs-Martin)/abs(Martin)`; concentration is µg/m³.

| Quantity | Martin / printed lesson | Briggs | Difference % | Tolerance % | Interpretation |
| --- | --- | --- | --- | --- | --- |
| Briggs versus Martin sigma-y | 278.970000 | 318.396657 | 14.132938 | 5 | exceeds; scheme difference |
| Briggs versus Martin sigma-z | 87.510000 | 101.160039 | 15.598262 | 5 | exceeds; scheme difference |
| Briggs versus Martin concentration | 149300.000000 | 133382.771845 | 10.661238 | 10 | exceeds; scheme difference |

**Unverified items, excluded from the validation pass count:** Turner AP26,
Chapter 7 Problem 9 Table 7-4 is available as an
[EPA HTML transcription](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9101GKEZ.TXT),
but its physical source page remains unverified. At z=0/30/150 m the retained
278/285/358 µg/m³ references give computed 274.592426/283.075948/356.331422 µg/m³,
differences 1.225746%/0.675106%/0.466083%. Arithmetic within tolerance does not
verify a physical page. The conflicting Brune paragraph is likewise excluded.
Independent end-to-end physical validity remains unestablished.

### Three city examples: before and after

Fresh fields, distances, exposure summaries and API/header responses reproduce
all archived numbers exactly. Every run/header endpoint returned HTTP 200 and
retained its input hash. All examples are hypothetical 1 g/s sources. None uses
rural B, and all five physics-module byte hashes match before/after.

| City / run / dispersion | Peak before µg/m³ | Peak after µg/m³ | Comparison |
| --- | --- | --- | --- |
| Delhi / #62 / urban C | 15.641839027404785 | 15.641839027404785 | exact match |
| Mumbai / #63 / urban C | 11.536741256713867 | 11.536741256713867 | exact match |
| Hyderabad / #64 / urban F | 18.990890502929688 | 18.990890502929688 | exact match |

Population, source-to-peak distance and weighted increments also match exactly;
their full values are retained in the structured metrics. No example number or
API-doc number needs changing. Engine version remains `gaussian-briggs-1.1.0`.

### Default assistant and running application

Code fallback, `.env.example` and actual `.env` now select `LLM_PROVIDER=extractive`.
Actual/default env values are `OLLAMA_ENABLED=false`, empty `COMPOSE_PROFILES`;
the installed `qwen2.5:3b-instruct` model is retained for opt-in use. Ollama is
stopped, the existing Compose `llm` profile is retained, and normal `compose up`
selects nine services. All nine are running; all five defined service healthchecks
are healthy. The running web container selects `extractive` and lists only that
provider as configured. No language-model generation or frozen-set evaluation ran.

`GET /api/health/` returned **200**, `ok=true`; database, PostGIS 3.6.4,
TimescaleDB 2.30.2, vector 0.8.7, Redis and Celery checks are all true. Production
`manage.py check --deploy` reports **no issues (0 silenced)**. README documents
explicit local opt-in and how to restore the extractive defaults. Existing
Qwen answer-quality and variable memory limitations remain; neither is certified
by infrastructure health.

### WSL configuration and backup inventory

The read-only search covered `C:\Users\Andry` and `D:\`, without traversing
reparse points. It found the current `.wslconfig` and **one readable backup**:

- `C:\Users\Andry\.wslconfig.phase6a-audit-20261015.bak`; created **2026-10-15T15:54:42.370363+00:00**;
  last modified **2026-10-12T10:35:22.988743+00:00** (timestamps UTC).
  SHA256 `d4f748ea8f222563e1beb8319e62496c62635ce052aa4dd380ee332b73375268`, 20 bytes.

Both backup and current file contain exactly:

```ini
[wsl2]
memory=9GB
```

The current file was created/modified 2026-10-12T10:35:22.988743+00:00 and has
the same SHA256. The backup preserves that modification timestamp; its creation
timestamp identifies the later copy. **A pre-change original could not be
recovered.** The earlier report says no file existed, but historical absence
cannot be independently reconstructed from a later backup.
The search recorded 6 inaccessible/invalid/disappearing paths,
including Windows application aliases and protected System Volume Information;
these limits are retained in the local inventory, not presented as a universal
proof that no other backup exists. No setting was changed. Installed capacity
is 17,179,869,184 bytes (16 GiB); `floor(0.60*16)=9` gives the requested **9 GB**
limit. No concrete problem requiring a different value was found in this pass.

### Checks and frozen identities

Full web-container suite: **252 passed, 147 warnings in 55.80 s**
(all 249 baseline tests plus three new regressions). Existing Python test files
are byte-identical. The expressly requested textbook fixture correction is the
only existing fixture changed; frozen evaluation data and labels are untouched.
Ruff: **All checks passed!** Format: **264 files already formatted**.
The warnings retain the earlier audited categories: pandas/NumPy generic
timedelta, SHAP/matplotlib deprecations, compiled ndarray-size warning and
statsmodels nonconvergence; none was suppressed. Django and migration checks
also pass. No new model/provider evaluation or prompt tuning was performed.

| Frozen set | Before SHA256 | After SHA256 | Expected |
| --- | --- | --- | --- |
| Phase 3A.2, 316 files | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` | expected match |
| Phase 4, 776 files | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` | expected match |
| Phase 5 questions/relevance | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` | expected match |

The entire four-file `data/eval` bundle is also unchanged, aggregate
`51c3354d68206b082d1f2c240c76c8c230da06ffc23754c2a147e624b6ec0d23`.
Per-file snapshots are retained locally under `data/results/phase6a-fix/`.

### Failed attempts and resolutions

- Recursive PowerShell WSL inventory hit a filesystem error. A read-only Python
  walk completed with explicit access-error reporting; it found the backup above.
  The first walk was interrupted by the user and was rerun after resume.
- The first standalone physics script invocation lacked `/app` on its import
  path. Rerunning with `PYTHONPATH=/app` completed all reference checks. This was
  an audit-script invocation issue; application imports required no code change.
- Docker was unavailable after the overnight interruption, so the first lint
  attempt could not run. Started installed Docker Desktop in the background,
  restored default Compose services and reran Ruff/full tests successfully.
  PowerShell also decorates Docker's normal stderr progress as NativeCommandError;
  actual Docker exit codes and final service states are recorded in the journal.

Changes: provider fallback and env examples/local defaults; textbook fixture;
three regression tests; README, architecture, data model, this report, structured
metrics and the command journal. Historical artifacts remain separate. Commit
creation/output is recorded by the final Git journal; **no push is performed**.
No manual action is required for the default application. Phase 6B remains unstarted.

## Independent validation

Completed 16 October 2026 from `c154eaa` in `D:\EnviroInsights-India`.
The reproducible command is:

```powershell
docker compose exec -T web python manage.py verify_vayusim_references
```

Hand-transcribed references, their dates and exact printed values are in
`tests/fixtures/vayusim-independent-references.json`. Actual outputs are in
[PHASE6A_INDEPENDENT_METRICS.json](PHASE6A_INDEPENDENT_METRICS.json).
Commands and linked raw web-reader outputs are in [VALIDATION](../VALIDATION.md).

### Decisions

1. Keep every physics module, coefficient, preset, tolerance, existing test and
   existing fixture unchanged. New expectations come from external printed
   values, not the engine or calculations copied from its implementation.
2. Separate an independent **printed numeric case** from equation transcription,
   cross-scheme comparisons and empirical field validation. A published equation
   alone, including a new page citation, cannot clear numeric branch readiness.
3. Use 5% for printed sigma values and 10% for concentrations. Use 10% only for
   an actual manually read chart point; none could be visually verified in this
   run. Turner's author-derived chart inputs are printed numbers in the retained
   fixture, so their diagnostic sigma comparison retains 5%, not a relaxed 10%.
4. Count only the DOE rural-D printed sigma pair at 1000 m as an independent
   numerical case. Keep the Martin and Turner diagnostics visible, including
   failures, but out of matched-scheme independent pass counts. Do not equate
   separate scalar values with separate experiments.
5. Do not manufacture missing urban C/F numeric reference values from equations,
   another class, a rural curve, inaccessible figures or a search snippet.
   Equation coefficients are transcribed separately and tested for all six
   urban classes; they do not qualify as independent numeric sigma references.
6. Use the available web reader for public sources; no separate named WebFetch
   tool was exposed. Perform no shell network downloads. ZIP-only data and
   unsuccessful PDF/chart reads remain explicit access/verification limits.
7. Record **Ready for 6B with caveats**, conditional on the future Phase 6B
   frontend displaying **unvalidated branch** for urban C/F scenarios, including
   all three examples. This is a mandatory future acceptance condition, not a
   claim that the label has already been implemented. Do not start Phase 6B here.

### Source search and accessibility

The repository was searched first: the cached VayuSim sources, research library
and all cached RAG PDFs. Relevant local hits include ISC3, the meteorological
guide, AERMOD formulation and dispersion references inside city reports; no
matched independent urban C/F numeric pair was established from them. Public
search then examined the sources below. Raw requests and returned outputs are
retained separately; inaccessible sources do not contribute reference values.

| Source | Page / table / locator | Access and use |
| --- | --- | --- |
| [Brune METEO532](https://personal.ems.psu.edu/~brune/m532/m532_theatmosphere.htm) | Section 2.2.5, Table 2.3; unpaginated | cached primary lecture table, all rural/urban A-F formulas; equation source, not numeric validation |
| [DOE-HDBK-1224-2018](https://www.energy.gov/documents/doe-hdbk-1224-2018pdf) | printed p.213 / PDF p.228 example after Eq.6-10; Table6-9 p.214 / PDF p.229 | accessible PDF text with page markers; independently printed rural D numeric case |
| [EPA ISC3 Volume II (1995)](https://gaftp.epa.gov/aqmg/SCRAM/models/other/isc3/isc3v2.pdf) | Tables1-3/1-4 p.1-19 / PDF p.32; rural pp.1-14 to1-18 | cached and accessible primary PDF; all urban equations, different rural PG equations |
| [Turner revised 1970](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=9101GKHD.TXT) | Problems4/9, Table7-4; exact physical page unverified | HTML readable; EPA PDF fetch failed; prior numeric transcription excluded from pass count |
| [Turner workbook mirror](https://www.keysolutionsinc.com/references/Turner%20Workbook.pdf) | 92-page metadata detected; needed page not verified | subsequent reads timed out/failed; no verified chart readings |
| [Turner workbook in EPA docket](https://downloads.regulations.gov/EPA-HQ-OAR-2003-0062-0323/attachment_2.pdf) | page unverified | 403 Forbidden |
| [Cimbala ME433 Lesson06E](https://www.me.psu.edu/cimbala/me433/Lesson_Notes/ME433_Lesson_06_E_Reflecting_Ground.pdf) | physical PDF p.3 | cached primary PDF available and SHA verified; remote read failed; Martin scheme comparison only |
| [EPA ISC3 test distribution](https://gaftp.epa.gov/AIR/aqmg/SCRAM/models/other/isc3/iscst.zip) | distribution archive | public directory readable; web reader rejects application/zip; no shell download performed |
| [EPA ISC3 Volume I](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=000031VJ.TXT) | sample TEST-ST run and input/output instructions | HTML readable; PDF fetch failed; no complete matching isolated urban C/F input-output tuple verified |
| [EPA AERMOD sample run](https://gaftp.epa.gov/Air/aqmg/SCRAM/models/preferred/aermod/AERMOD_Sample_Run_Instructions.pdf) | pp.17-21, especially p.20 Section4.3; AppendixA p.31 | readable primary guide; original outputs are in separate sample/test ZIPs; no matched Briggs-only numeric case verified |
| [GENII v2 design Rev3](https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-14584Rev3.pdf) | 338-page metadata detected; needed numeric page unverified | initial PDF identified; follow-up needed-page searches/reads failed; no numerical reference used |
| [DOE-HDBK-1224-2024](https://www.energy.gov/documents/doe-hdbk-1224-2024pdf) | needed numerical page unverified | PDF identified; relevant-page reads failed; no value promoted from search snippets or independent Doxcelerate mirror |

**Formula provenance for all classes:** Brune Table2.3 and DOE Table6-9 on
printed p.214 cover rural/urban A-F. The latter discusses Briggs (1973) with
Griffiths (1994) updates; an original 1973 report page was not independently
verified. ISC3 Tables1-3/1-4, printed p.1-19, explicitly list all six urban
classes, use x in metres and agree with the implemented urban coefficients.
Rural ISC3 instead uses Pasquill-Gifford fits (pp.1-14–1-18), not this engine's
Briggs rural equations. An ISC rural output is therefore not an interchangeable
Briggs reference.

The DOE2018 extracted Table6-9 rural-E `b_y` appears as 0.00001, whereas the
cached Brune table uses 0.0001. That glyph/typographical discrepancy was not
resolved from a visual source page; it is **unverified** and was not used to
change a coefficient or establish an E-case pass. DOE p.214 also explicitly
warns that the urban E/F sigma-z factor 0.00015 found in some references is
incorrect, giving 0.0015 instead. ISC3 p.1-19 and the code use 0.0015. No source
variant was silently substituted or used to tune the engine.

Turner chapter3 describes open-country/rural applicability and urban limitations;
no verified matching Briggs-urban C/F worked case was found. The revised-1970
HTML's Table7-4 is identifiable, but its physical page is still unverified.
The EPA catalogue title of the older cached copy says revised1969 while its
title-page transcription says revised1970; the new record uses the explicitly
revised1970 catalogue entry and preserves that distinction.

EPA's AERMOD guide p.20 Section4.3 explains comparison with the separate original
output files. Those sample outputs and meteorological profiles are not a
single published Briggs-only C/F sigma pair. The ISC ZIP is public but the web
reader returned unsupported `application/zip`; its contents were not inspected.
No exact-input ISC/AERMOD end-to-end numerical match is claimed.
DOE p.341 Table9-6 does print ALOHA concentrations, including urban F, but
the necessary equivalent stack/effective height, receptor and evaporation/
averaging assumptions were not established as a matching VayuSim case. Filling
those gaps with guesses would not be independent validation.

### Validation table

Sigma values are metres; concentrations are µg/m³. Differences are
`100*abs(engine-reference)/abs(reference)`. All rows below come from the actual
new run. **PASS/FAIL tolerance** on a diagnostic is not independent branch
validation. The only eligible case is explicitly marked.

| Point / quantity / method | Source | Reference | Engine | Error % | Tolerance % | Result / scope |
| --- | --- | --- | --- | --- | --- | --- |
| doe-briggs-rural-d-1000m / sigma_y_m / engine sigma | DOE p.213 / PDF228 | 76.300000 | 76.277007 | 0.030135 | 5 | PASS; independent numeric case |
| doe-briggs-rural-d-1000m / sigma_z_m / engine sigma | DOE p.213 / PDF228 | 37.900000 | 37.947332 | 0.124886 | 5 | PASS; independent numeric case |
| cimbala-martin-d-4850m / sigma_y_m / engine sigma | Cimbala PDF3 | 278.970000 | 318.396657 | 14.132938 | 5 | FAIL tolerance; scheme comparison |
| cimbala-martin-d-4850m / sigma_z_m / engine sigma | Cimbala PDF3 | 87.510000 | 101.160039 | 15.598262 | 5 | FAIL tolerance; scheme comparison |
| cimbala-martin-d-4850m / concentration_ugm3 at z=0 m / engine sigma -> Gaussian, prescribed H/u | Cimbala PDF3 | 149300.000000 | 133382.771845 | 10.661238 | 10 | FAIL tolerance; scheme comparison |
| cimbala-martin-d-4850m / concentration_ugm3 at z=0 m / Gaussian only, source-supplied sigmas/H/u | Cimbala PDF3 | 149300.000000 | 149314.351448 | 0.009612 | 10 | PASS; Gaussian formula only |
| turner-pg-b-1000m / sigma_y_m / engine sigma | Turner Table7-4, page unverified | 157.000000 | 152.554014 | 2.831838 | 5 | PASS; page unverified; excluded |
| turner-pg-b-1000m / sigma_z_m / engine sigma | Turner Table7-4, page unverified | 110.000000 | 120.000000 | 9.090909 | 5 | FAIL tolerance; page unverified; excluded |
| turner-pg-b-1000m / concentration_ugm3 at z=0 m / engine sigma -> Gaussian, prescribed H/u | Turner Table7-4, page unverified | 278.000000 | 300.517407 | 8.099787 | 10 | PASS; page unverified; excluded |
| turner-pg-b-1000m / concentration_ugm3 at z=0 m / Gaussian only, source-supplied sigmas/H/u | Turner Table7-4, page unverified | 278.000000 | 274.592426 | 1.225746 | 10 | PASS; page unverified; excluded |
| turner-pg-b-1000m / concentration_ugm3 at z=30 m / engine sigma -> Gaussian, prescribed H/u | Turner Table7-4, page unverified | 285.000000 | 305.609816 | 7.231514 | 10 | PASS; page unverified; excluded |
| turner-pg-b-1000m / concentration_ugm3 at z=30 m / Gaussian only, source-supplied sigmas/H/u | Turner Table7-4, page unverified | 285.000000 | 283.075948 | 0.675106 | 10 | PASS; page unverified; excluded |
| turner-pg-b-1000m / concentration_ugm3 at z=150 m / engine sigma -> Gaussian, prescribed H/u | Turner Table7-4, page unverified | 358.000000 | 342.615072 | 4.297466 | 10 | PASS; page unverified; excluded |
| turner-pg-b-1000m / concentration_ugm3 at z=150 m / Gaussian only, source-supplied sigmas/H/u | Turner Table7-4, page unverified | 358.000000 | 356.331422 | 0.466083 | 10 | PASS; page unverified; excluded |

There is **one independent printed numerical case**, comprising **two passing
scalar sigma comparisons** and zero failing eligible comparisons: rural D at
1000 m. It is **independently validated for these cases only**: sigma-y against
the printed 76.3 m and sigma-z against 37.9 m in DOE p.213. This is independent
reference-case verification, not a field-data validation or evidence of accuracy
for Indian city conditions.

The Cimbala sigma and concentration differences exceed 5%/10%; their cause is
the source's Martin scheme versus this engine's Briggs rural D. They remain
**scheme differences, not coding/validation errors**, and do not justify changing
Briggs. Supplying the lesson's sigmas makes the Gaussian primitive agree within
0.009612%, demonstrating the distinction without validating the dispersion branch.
The Turner B sigma-z diagnostic differs by 9.090909%, exceeding 5%; its P-G chart
parameterisation differs from Briggs and its physical page remains unverified.
Here B is the selected diagnostic branch; its exact source-case classification
has not been verified from a physical page. All Turner inputs/rows remain excluded.
Neither case was tuned or reclassified into an independent pass.

**Concentration scope:** the sigma-to-Gaussian calculations use exactly the
published Q, transport wind, receptor height and effective H. Cimbala prints
physical stack80 m plus rise20 m, giving H100 m, but omits the diameter, exit
velocity and exit/ambient temperatures needed to reproduce that rise through
the engine. It is therefore a complete prescribed-H concentration calculation,
not a verification of the full physical-stack/wind-profile/plume-rise pipeline.
Those missing inputs were not invented. No plume-rise, mixing-lid, population
or empirical full-pipeline validation is established by this run.

### Branch coverage and not-validated list

Six new urban equation-transcription tests cover A–F, specifically C and F,
against ISC3 p.1-19. Two new sigma tests pin the independently printed rural-D
pair. Existing tests and reference fixtures are unchanged.

| Branch / scope | Independent numeric status | Examples affected |
| --- | --- | --- |
| rural D sigmas, x=1000 m | validated for this printed case only | none |
| rural D other distances / full concentration pipeline | not independently validated | none |
| rural A/B/C/E/F | not independently validated; B diagnostics do not qualify | none |
| urban A/B/D/E | equation coverage only; not independently validated | none of these three examples |
| urban C | **not independently validated** | Delhi #62, Mumbai #63 |
| urban F | **not independently validated** | Hyderabad #64 |

There are zero verified chart-read points; chart-only candidates were left
unverified and excluded rather than assigned fabricated coordinates or values.
No printed-number or visual-chart evidence for urban C/F was verified in the
sources successfully accessed. This is a bounded search result, not proof that
no such reference exists anywhere.

### Example claims and gate

All three examples now have the explicit claim **not independently validated for
their urban dispersion branch**. They remain hypothetical 1 g/s educational
scenarios with archived weather and WorldPop support, not observed facilities.
Fresh recomputation reproduced every peak, distance, exposure summary and input
hash exactly. Run/header endpoints all returned200. No number changed.

| Example | Branch | Peak before µg/m³ | Peak after µg/m³ | Claim |
| --- | --- | --- | --- | --- |
| Delhi #62 | urban C | 15.641839027404785 | 15.641839027404785 | not independently validated |
| Mumbai #63 | urban C | 11.536741256713867 | 11.536741256713867 | not independently validated |
| Hyderabad #64 | urban F | 18.990890502929688 | 18.990890502929688 | not independently validated |

**Ready for 6B with caveats** is conditional: the Phase6B frontend must label
urban C/F scenarios **unvalidated branch**, including these three examples, and
retain the educational/no-regulatory-validity caveats. That frontend label is
not implemented or asserted to exist by this task; **Phase6B has not started**.
Equation agreement or a health200 response cannot remove this requirement.

### Software checks, frozen identities and command outcomes

Web-container suite: **260 passed, 147 warnings in 51.74s**;
all 252 existing tests plus two independent-number and six equation-transcription
regressions. Ruff: **All checks passed!** Format: **266 files already formatted**.
Django system and migration checks pass. Warnings remain visible and unsuppressed
in the same upstream categories documented in the fix pass. Current default
provider remains extractive, Ollama disabled; health returned200 with all checks
true. No model/provider evaluation or prompt tuning ran.

| Frozen set | Before SHA256 | After SHA256 | Expected |
| --- | --- | --- | --- |
| Phase3A.2, 316 files | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` | expected match |
| Phase4, 776 files | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` | expected match |
| Phase5 questions/relevance | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` | expected match |

All 50 existing test/support/fixture files also match before and after:
`3ca434500859bf7230fc713bb6c85e1262213b8bb637a090302fa364cddc3fd6`.
All six physics/preset files match before and after:
`60f44bf7573b84522f49d5dc3fba3a2e97483b1995ccd6d2765e429deb815a0e`.
The complete four-file evaluation catalogue remains unchanged as well.

The first local glob search used a literal Windows wildcard path rejected by
`rg`; the subsequent directory search completed. The first Ruff run found one
overlong string in the new command; wrapping that string fixed it, with no
coefficient, tolerance or test changes. Public-read failures are retained in
the source inventory and raw web journal. No scientific mismatch was hidden.
The report helper initially used the Windows default decoder for UTF-8 research
records; explicit UTF-8 completed the journal without duplicating the report.
A cached legacy EPA HTML read needed Windows-1252 decoding; the source bytes
were retained unchanged. Neither decoder issue affected numerical computations.

Files added: the manually transcribed fixture, reproducible management command,
eight regressions, structured result metrics and evidence manifest. README,
architecture, this report and the command journal now state the limited case
result and conditional gate. No Phase6B frontend or engine feature was added.
