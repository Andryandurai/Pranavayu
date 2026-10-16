# EnviroInsights-India: useful results, visible limits

## 1. Question and scope

EnviroInsights-India investigates what a public-data air-quality archive can
support, rather than treating every implemented model as a successful scientific
answer. The project combines a spatial and time-series warehouse, retrospective
weather analysis, daily forecasts, document retrieval and an educational source
dispersion interface. Each component has a different evidential standard. A
database can preserve provenance without making its inputs representative; a
test can check an equation without establishing its predictive performance.
The [phase reports](PHASE7.md) retain those distinctions.

**RQ1, the effect of BS-VI, is not answered.** The concentration archive lacks
the intervention-era observations and historical NO2 needed for attribution.
The old/recent comparison is not a substitute for a design that separates fuel
standards from lockdowns, station changes and other interventions. A regression
coefficient across that gap would not repair the missing identification.

**RQ2, meteorological associations with PM2.5, is partly answered.** Within
observed periods, screened models describe predictive weather associations for
supported city/cohort combinations. They do not identify causal weather effects,
recover an emissions inventory or guarantee transfer between eras. Some monthly
bias screens still fail. **RQ3, transported agricultural-fire influence, is not
answered:** no credentialed FIRMS detection sample was ingested. These statuses
follow the [Phase 3B limitations](PHASE3B.md), not the existence of corresponding
software adapters.

The additional PM2.5 proxy for NCAP progress is descriptive. It is not official
compliance: the required historical PM10 baseline is absent. Forecasting and
retrieval are separate engineering experiments. The final dashboard links each
figure to a record so that a reader can inspect the cohort, dates and denominator
before deciding what a headline means.

## 2. Data and quality control

The retained Phase 7 snapshot contains 17,504,928 combined observation rows:
16,266,240 concentration records and 1,238,688 weather observations. Counting
both as “17.5 million pollution measurements” would be misleading. Concentration
records include 2,950,728 missing rows, 13,214,169 OK rows, 99,583 stuck candidates
and 1,760 PM2.5-greater-than-PM10 flags. These are stored labels, not proof of
instrument calibration. The [dated snapshot](PHASE7_DATA.json) records source
ranges and mutually exclusive counts.

Historical PM2.5 uses the public XKDR alternative to inaccessible original
Princeton bodies. Recent concentrations use OpenCity exports attributed to the
relevant monitoring boards. Older dimensionless AQI matrices are retained as
assets but excluded from concentration loading. Public Open-Meteo supplies
city-grid weather. Datameet boundaries and WorldPop support spatial context;
neither establishes that the station network is a population sample. OpenAQ,
FIRMS and CDS paths were skipped without credentials. Their adapters and tests
are not live ingestion evidence. [Data-source notes](../DATA_SOURCES.md) preserve
licence/access declarations and the failed requests.

The denominator matters beyond the weather/pollution distinction. Concentration
rows span station, pollutant and observation time; multiple pollutants at one
site do not represent independent locations or unique city-hours. Stored missing
records also count as rows. Aggregation and completeness rules, rather than the
warehouse's size, determine the daily targets used in analysis. UTC ranges can
begin on the previous calendar date while representing a local midnight in
India. The snapshot preserves the explicit offsets instead of silently changing
their labels for a larger-looking coverage claim.

A major defect was a **5½-hour timestamp error**. Specific recent OpenCity files
labelled their timestamps as UTC while recording IST wall clocks. Same physical
station overlaps, publisher-quarter comparisons and diurnal alignment diagnostics
revealed that the literal offset interpretation displaced concentrations from
weather. The correction was source-specific: it did not reinterpret every
offset-labelled input. Phase 3B applied the canonical repair once and preserved
measurement values, flags and ingestion links. Earlier derived evaluations stayed
frozen, so the corrected run could be compared with its predecessor.

IST also begins its hours halfway through UTC hours. Fifteen-minute slots must
therefore be aggregated on the correct local clock, and weather joined at the
local-hour midpoint expressed in UTC. Missing quarters do not become independent
measurements; missing hours do not become zeros. Positive repeated values remain
stuck candidates, while zero alone can reflect a reporting floor. Station-position
uncertainty and source rounding remain limitations after clock repair.

## 3. Analytics findings

The initial normalisation failures led to an audit of clocks, station networks,
weather completeness and validation design. Random hourly splits measure a
different problem from holding out whole weeks, and both differ from transferring
a model across the unobserved era. The later design uses within-period week
blocks and an embargo for interpolation checks. Old and recent periods share
pooled reference weather; an explicit trend is not used to bridge missing years.
The [Phase 3A.2 report](PHASE3A2.md) retains the original readiness criteria and
rejected alternatives.

Meteorological normalisation uses the general resampling idea described by
[Grange et al.](https://acp.copernicus.org/articles/18/6223/2018/), whose paper
concerns Swiss PM10. Its publication does not confer readiness on Indian PM2.5
models. Here, held-week diagnostics and monthly bias remain necessary alongside
fit quality. SHAP allocations describe fitted predictions with correlated inputs;
they are not independent causal effects. GAM/ALE cross-checks likewise depend on
observed support and modelling choices.

The preferred matched-date Delhi fixed-panel normalised difference is
**−17.591985 µg/m³**, with refit/block interval **[−35.071143, +1.662317]**.
The comparison uses 2,417 supported dates and 20 model refits. The interval spans
zero, so a decline is **inconclusive under this procedure**. Reporting only the
negative point estimate would conceal the main inferential qualification. The
interval is conditional on selected structures and observed stations; it does
not include every possible instrument, network or selection uncertainty.
[Matched-network table](PHASE3B.md#delhi-long-run-weather-adjusted-change).

Hyderabad demonstrates why cohort definitions belong beside exceedance counts.
In 2025, the all-station daily city mean exceeds 60 µg/m³ on **0** valid days;
the fixed panel does so on **53**, each over 365 valid days. Their daily maxima
are 53.030602 and 77.686921 µg/m³ respectively. This contrast survives clock
repair. It is network sensitivity, not a reason to replace every zero count
with the panel result, and it says nothing about every station's maximum.
[Station-network record](PHASE3B.md#station-network-composition).

## 4. Forecasting results

Phase 4 predicts daily city PM2.5 at one-, two- and three-day horizons. Features
stop at issue time; training, tuning and calibration windows are separated.
The headline weather input is a documented GFS lead-offset archive, not observed
target-day ERA5. Exact historical publication timestamps are unavailable, so
issue availability also depends on the recorded latency assumption. The
separately labelled perfect-prognosis experiment never becomes headline skill.
[Protocol](PHASE4_PROTOCOL.md).

The saved July–December 2025 evaluation uses 184 targets per city/horizon.
Delhi next-day policy RMSE is **29.417 µg/m³**, against persistence at
**33.668 µg/m³**, approximately **12.6%** improvement. That is a useful result
for this rolling window, not a national or independent-year guarantee. Monthly
selection can choose different algorithms, and diagnostic scores for rejected
models remain visible. A sophisticated model is not entitled to replace a
simple baseline merely because it was trained.

Nine city–horizon policies have negative skill: Bengaluru horizons 1 and 3,
Chennai 1, Mumbai 1–3 and Pune 1–3. Serving uses persistence for the nine city-horizon combinations where Phase 4 found that the model lost to persistence; the model is used for the others.
The Phase 7 audit found that four of these nine latest stored selections used
persistence, while five used other algorithms. This follow-up adds the serving
override without rewriting those stored selections or the backtest.
[Original snapshot](PHASE7_DATA.json), [serving fix](PHASE7_FIX.md).

The fallback now has an explicit versioned rule citing the Phase 4 table; it still
needs prospective evaluation. Original model predictions remain stored for audit
and are not exposed by the serving API. Calling a
retrospective persistence substitution an improved original backtest would mix
selection and evaluation. Persistence copies the issue-day mean, never a target-day
value. Original model intervals and SHAP drivers are omitted from fallback responses:
they do not assess the replacement. The original score table remains unchanged.

Uncertainty is also uneven. Quantile and conformal empirical coverage are
reported separately. The later method-selection audit has **14 failures among
42 nominal-level choices**, using the unchanged five-percentage-point gate.
Choosing the closest method on the same held-out window is post-evaluation
selection, not independent assessment of the resulting policy. Nested issued
bounds may also be widened. Archived replay, changing station composition,
seasonality and missing contemporaneous publication records remain explicit.
[Interval audit](PHASE6A.md#forecast-intervals).

## 5. The research assistant

The default feature is **extractive retrieval with verified citations**. Phase 5
registered 29 document bodies and 7,194 chunks, with physical PDF pages or
explicitly unpaginated sections. Dense pgvector retrieval, lexical full-text
search and reranking provide passages; constrained data tools retrieve stored
project results. Model weights, source hashes, parser versions and Query records
make the path inspectable. Missing evidence can produce a refusal rather than
a fabricated answer.

On the original frozen literature set, hybrid reranking achieved **80.31%
recall@5** and **0.6933 MRR**. The extractive evaluation recorded **925/925
supported citation uses**, **669/669 expected numeric values**, and **10/10
correct refusals**. These are specific exact-support and field-matching checks,
not 925 independent proofs of scientific truth or unrestricted answer quality.
Known-gold judgments are incomplete, and retrieval/answer latency depends on
cache conditions. The figures belong to the original benchmark, not an implied
fresh evaluation of every later configuration. [Phase 5](PHASE5.md).

The subsequent local Qwen/Ollama provider-only evaluation failed its quality
gate. Only **2/80** literature questions retained an answer; **0/30** available
data questions were answered, and **118/120** draft claims were removed. High
support among the two retained claims does not rescue the answer rate. Local
generation is opt-in and off by default. Memory eligibility and model loading
are separate from useful answers. The frozen questions were not rewritten to
improve the score. [Later evaluation](PHASE6A.md#local-language-model).

A demonstration should show both a cited stored-data answer and a refusal for
an unsupported year. The refusal is a limitation expressed honestly, not evidence
that all refusals are desirable. A better future answerer needs independent
semantic assessment and adequate coverage, rather than prompts tuned against
the same frozen questions.

## 6. VayuSim: equations and scope

VayuSim estimates the incremental primary PM2.5 concentration from explicitly
assumed sources. Its NumPy core uses reflected Gaussian dispersion, Briggs
coefficients, wind adjustment and plume rise. Geographic projection, weather
and population adapters are separate. For Q in g/s and output in µg/m³, the
unlimited reflected-ground expression is

`C = 10^6 Q/(2πuσyσz) exp(−y²/(2σy²))`
`× [exp(−(z−H)²/(2σz²)) + exp(−(z+H)²/(2σz²))]`.

The retained implementation adds its documented mixing-lid treatment. Parameter
references include [Brune Table 2.3](https://personal.ems.psu.edu/~brune/m532/m532_theatmosphere.htm)
and [ISC3 Volume II](https://gaftp.epa.gov/aqmg/SCRAM/models/other/isc3/isc3v2.pdf),
including printed pages 1-5 through 1-19 for the relevant wind/rise/dispersion
formulations. Their transcription is distinct from a field comparison. Full
assumptions and equation checks are retained in [Phase 6A](PHASE6A.md).

The audit separates three kinds of evidence. Published-equation checks pass.
A limited independent rural-D sigma pair agrees at its printed distance.
Briggs versus Cimbala's Martin solution differs by **14.13% in σy, 15.60% in
σz and 10.66% in concentration**, exceeding the stated tolerances; those are
scheme differences. Turner physical-page checks remain unverified. Urban
**C and F are unvalidated branches**, including the three displayed examples.
No interface or passing software suite changes that status.

Each example uses a **hypothetical 1 g/s source**, not a measured facility:
Delhi urban C peaks at **15.641839 µg/m³**, Mumbai urban C at **11.536741**,
and Hyderabad urban F at **18.990891**. Their stored inputs, grids and numerical
summaries are unchanged. Population exposure covers supported raster cells in
the modelled footprint, not citywide exposure or health impacts. Nearby CPCB
totals are displayed separately and never added to the plume.

The frontend reads retained binary grids, contours and overlays. Its day mode
switches independent steady hours; particle shimmer is a display cue, not
transport simulation. A vertical section uses a supplementary stored receptor
grid computed with the unchanged engine, not inferred height information from
the original single-height field. Warnings remain visible on shares and exports.
[Frontend and measured timings](PHASE6B.md).

## 7. Negative results and resulting changes

Failures changed the project more than a favourable headline alone would have.
Clock diagnostics led to an audited source-specific repair. Poor normalisation
screens prompted cohort, weather and blocked-validation comparisons instead of
lower thresholds. Inconclusive Delhi uncertainty stayed inconclusive. Missing
FIRMS and intervention-period data prevented unsupported research answers.

Negative forecast skill exposed the need to compare with persistence and to
introduce a versioned serving fallback separately from original issued-policy scores. Undercoverage
remains visible after method selection. The local generator's poor answer rate
led to extractive defaults. Dispersion discrepancies led to narrower formula,
scheme and independent-case labels rather than coefficients adjusted to match
an inconsistent reference. The [claims audit](PHASE7.md) identifies the final
documentation corrections without modifying historical reports.

Phase 6B also recorded intermittent Hypothesis input-generation timing failures.
Phase 7 gives the affected crosswind-mass test a bounded explicit deadline,
with numerical integration, assertions, strategies and example count unchanged.
The installed Hypothesis source explains how the deadline also bounds initial
generation time; its [API reference](https://hypothesis.readthedocs.io/en/latest/reference/api.html)
was checked. Three full suite runs test the cleanup. This is environment timing
configuration, not a relaxation of a physics tolerance or a new scientific result.

Repeated passing runs provide local reliability evidence, not proof that a
timing-sensitive test can never fail on another machine. Similarly, matching
frozen hashes establishes that the evaluated inputs and labels were preserved;
it does not establish that those labels are exhaustive or error-free. The
dashboard serves a committed snapshot and a fixed allowlist of source files,
with an explicit unavailable state when evidence is absent. This keeps a fresh
checkout from pretending it has restored the full research database.

## 8. Limitations and future work

The first priority is better evidence: intervention-era concentrations, stable
station identities and calibration histories for RQ1, and actual fire detections
with coverage and transport controls for RQ3. The [Phase 3B research requirements](PHASE3B.md#what-would-change-with-more-data)
describe the required designs. More rows alone do not establish comparability.

Forecast work needs fresh publication-aware inputs and an untouched future
evaluation period for the new serving fallback. Interval
selection needs assessment beyond the window that selected it. The
[forecast protocol](PHASE4_PROTOCOL.md) is the starting point; the frozen outcomes
must remain historical evidence, not a target for repeated tuning.

Assistant work needs independent answer-quality review, broader relevance
judgments and useful coverage under constrained resources. Dispersion work needs
independent urban C/F numeric cases and eventually field-relevant evidence,
without presenting equation agreement as that evidence. The
[scientific audit](PHASE6A.md#independent-validation) specifies the current scope.

Finally, external hosting requires TLS, secrets, static-file serving, backup
recovery and operational monitoring. The [deployment notes](../DEPLOYMENT.md)
describe what was checked and what remains unconfigured. All reference links
used here were checked locally or through the web reader during Phase 7;
unreachable alternatives were omitted. The project is most useful when its
limits remain as inspectable as its successful checks.
