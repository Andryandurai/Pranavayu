# Phase 3B: meteorological associations and a PM2.5 proxy for NCAP progress

## Abstract

AnalysisRun **19**, completed 2026-10-10T11:11:16.591907+00:00, uses the corrected
Run 7 designs for 7 cities, with Bengaluru restricted
to its fixed panel. The nested validation and weather-only comparisons below are
daily predictive associations, not causal variance decompositions. Each validated
cohort has 20 actual bootstrap model refits. Old/recent PM2.5
changes are descriptive, with shared pooled weather and refit/block intervals.
NCAP compliance cannot be evaluated because the historic PM10 baseline is absent.
BS-VI attribution and crop-fire results are not estimated.

Weather-only daily held-week R² ranged from 0.3676 to 0.8302 across approved city/era cohorts. The unchanged nested screen passed all observed eras in 3 of 7 main cohorts: lucknow, mumbai, bengaluru. At least one era failed in delhi, hyderabad, kanpur, pune; those failures are retained rather than weakening criteria.

On identical network-comparison dates, Delhi's fixed-panel weather-adjusted
long-run interval spans zero after model-refit uncertainty is included. Only
Delhi and Hyderabad have the eligible years for the requested 2017–2018 proxy;
Hyderabad's older nested validation remains a limitation on its normalised comparison.

## Introduction

Weather and changing station composition can distort comparisons of measured PM2.5.
Grange et al. motivate forest meteorological normalisation; their Swiss PM10 results
do not establish performance here. Shi et al. demonstrate why weather adjustment
and observations around an intervention matter for attribution. This study addresses
meteorological drivers (RQ2) and a labelled PM2.5 proxy (RQ5). It estimates associated
changes across observed eras without assigning a policy effect.

## Data

Concentrations are CPCB historical exports mirrored by XKDR in 2015–2019 and OpenCity
exports in 2024–2025; the audit, URLs and coverage are documented in PHASE3A/PHASE3A2
and DATA_SOURCES. There are no 2020–2023 concentrations, no historical NO2 and no
historic PM10 baseline. Open-Meteo/ERA5 weather uses UTC requests and observed grid
values. Raw inputs remain cached and hash-addressed. Quality-OK station means are
averaged equally within native IST hours; days require 18 hours, months 75% of calendar
days and eligible years 75% of hours and days. Missing observations remain missing.

Fixed panels match exact CPCB site IDs across providers, not provider-specific row
IDs. Presence in both eras does not prove unchanged instruments or historical GPS.
The station/year tables and district/grid audits remain in
data/results/8/.

| City | Matched CPCB site IDs | Main research cohort |
| --- | --- | --- |
| bengaluru | 7 | fixed_panel |
| delhi | 36 | all_stations |
| hyderabad | 6 | all_stations |
| kanpur | 0 | all_stations |
| lucknow | 0 | all_stations |
| mumbai | 9 | all_stations |
| pune | 0 | all_stations |

| City | Cohort | Eligible observed calendar years | Scope |
| --- | --- | --- | --- |
| delhi | fixed_panel | [2015, 2016, 2017, 2018, 2019, 2024, 2025] | validated observed periods |
| delhi | all_stations | [2015, 2016, 2017, 2018, 2019, 2024, 2025] | validated observed periods |
| hyderabad | fixed_panel | [2016, 2017, 2018, 2019, 2024, 2025] | validated observed periods |
| hyderabad | all_stations | [2016, 2017, 2018, 2019, 2024, 2025] | validated observed periods |
| kanpur | fixed_panel | [] | unavailable |
| kanpur | all_stations | [2016, 2017, 2018, 2019] | validated observed periods |
| lucknow | fixed_panel | [] | unavailable |
| lucknow | all_stations | [2015, 2016, 2017, 2018, 2019] | validated observed periods |
| mumbai | fixed_panel | [2024, 2025] | descriptive only |
| mumbai | all_stations | [2015, 2016, 2017, 2019, 2024, 2025] | validated observed periods |
| pune | fixed_panel | [] | unavailable |
| pune | all_stations | [2024, 2025] | validated observed periods |
| bengaluru | fixed_panel | [2016, 2018, 2019, 2024, 2025] | validated observed periods |
| bengaluru | all_stations | [2015, 2016, 2017, 2018, 2019, 2024, 2025] | descriptive only |

Other cities remain descriptive: Ahmedabad, Chennai, Jaipur, Kolkata and Patna.
Bengaluru all-station modelling remains unapproved. Panels without eligible years
or a passing validated model are shown as descriptive/unavailable; they are not
substituted with artificial series.

## Methods

### Stored timestamp repair

The earlier fix was analysis-only. The ingestion layer now decodes hash-approved
OpenCity files' mislabelled +0000 IST wall clocks into UTC and bins quarters in IST.
IngestionRun clock-version markers prevent a second correction. Unverified new
publisher clocks are rejected once canonical ingestion is established.
The idempotent repair shifted 14,787,584 stored readings by −5.5 hours. All
16,266,240 readings remain; before/after value/quality/provenance hash is
767228030051878155. The second run corrected zero rows. Cross-chunk timestamps
are atomically routed by delete/reinsert because Timescale rejects a cross-chunk
UPDATE. Raw values, source assets and original ingestion links are retained.

The first bulk UPDATE failed its Timescale chunk constraint and rolled back.
The paused attempt also rolled back. The final repair is recorded in IngestionRun
87. DataRuns 8 (diagnostic) and 9 (all pollutants) rebuild the stored clock:
all 12 PM2.5 hourly tables match Run 7 to 1e-12; all 12 diagnostic frames
match Run 6 exactly. All 414 Run 7 artifacts and all
15 original test files passed hash verification.

### Design, selection and honest validation

The Phase 3A2 readiness criteria are unchanged: each observed era requires daily
week-CV R² ≥0.5, |NMB| ≤10%, no calendar month with |NMB| >20%, at least 26 observed
weeks and at least 20 OOF days in every calendar month. Thresholds are screening
rules, not universal literature guarantees. The Phase 3B protocol was frozen at
2026-10-08T18:47:04.530980+00:00, before new fitting. Its SHA-256 is
`5c12d51c3ba9320be25d90363f910af10e0e06f38f806b0eefba82221ae0c732`.

Nested CV uses three outer and three inner folds of whole Monday-start IST weeks,
stratified by observed era, with a 24-hour boundary embargo. Outer weeks and their
embargo are excluded from inner training AND inner validation. Each outer fold
selects among the original eight variants using only inner mean era-specific daily
R² on shared dates. The selected full model and its weather-only comparison predict
outer weeks once. Donor/weather predictors have no concentration-gap observations.
The honest number measures the prespecified selection procedure; Run 7's fixed
normalisation design and weights are retained separately for comparability.

Weather-only RFs remove trend, calendar and period-indicator features, retaining
the inner-selected weather support/model grouping. Separate-era intercepts mean
pooled overall R² is not a weather explanation of changes between eras: period-specific
R² is the headline. The within-period combined R² uses summed within-era SST.
All paired scores share daily OOF support; folds choosing BLH can drop unsupported
early-2024 days. Daily-target and hourly-aggregated variants use the stated complete-case
rules. Fold-specific designs, held weeks, support and scores are retained in CSV/JSON.

### Normalisation and uncertainty

Both eras use the SAME pooled joint observed reference weather from 2015–2019 and
2024–2025, including weather without concentration targets. Day-of-year, hour and
weekday are resampled jointly with weather; only explicit local trend and period
indicator are held. This adjusts seasonal/calendar information as well as weather,
and cannot isolate a purely physical meteorological change. Local trend is held
within each era and never bridges 2020–2023. Each cohort uses 20 actual forest refits
on whole observed IST weeks resampled with replacement within year/era (boundary
weeks contain their observed year fragments), with fixed structure and seeds.
Both eras and the two networks share each refit's 300 joint weather donors.
The existing Run 7 normalised series provides the point estimate; 500 mixture
draws combine refitted normalisations, equal-year resampling, contiguous seven-day
observed calendar blocks and centred nested OOF residuals. Gaps end a block.
Raw intervals use observed-value blocks, with no artificial model uncertainty.
Normalised intervals include actual refit spread and donor Monte Carlo variability;
they remain conditional on model structure and station-panel definition.

Old/recent comparisons use matched raw/normalised/nested-OOF dates. Annual means
are weighted equally across eligible years. The NCAP proxy requires BOTH calendar
2017 and 2018 and BOTH 2024 and 2025. This is different from NCAP's official fiscal-year
2017–18 PM10 baseline. Unsupported years are reported unavailable.

### Driver explanations and GAM cross-check

Exact tree-path-dependent TreeSHAP uses 30 complete days per era/season, all valid
hours of sampled days for hourly models, and an additivity check. Signed hourly
attributions are averaged per day BEFORE taking mean absolute magnitudes. Circular
wind sine/cosine contributions are grouped; neither one is an independent physical
driver. These conditional allocations are sensitive to correlated weather/calendar
predictors and are not causal effects or an additive partition of R².

ALE uses 12 empirical quantile bins; wind direction rotates sine and cosine together
over 12 angular sectors and corrects circular closure when all sectors have support.
Empty/constant bins stay unestimated. Gaussian statsmodels GAMs use cubic B-splines,
df=6 and alpha=10, training-only scaling and knots with a fixed five-standard-deviation
support extension. No penalty tuning follows results. Their weather-only daily CV
uses the same outer weeks and a flat boundary extension beyond this support, preserving
the actual observations; per-feature clipping counts are recorded. Run 11's Delhi
GAM failed on 115.4 mm held-out daily rain before this implementation guard.
GAM/forest ALE shape agreement is a rank correlation on
shared supported ranges; an hourly forest versus daily GAM is a frequency-different
cross-check. Calendar omission and interactions can explain disagreements.

Seasons are winter October–February, pre-monsoon March–May and monsoon June–September.
Only Lucknow's frozen selected forest retains BLH. Other cities have no validated
BLH effect estimate; this is not evidence that its physical effect is zero. The
weather-null tables document the missing first half of 2024 BLH and other missing values.

Monthly normalised trends are Theil–Sen slopes on actual calendar month coordinates,
with classic and seasonal Mann–Kendall tests per era. MK p values are nominal:
serial dependence, selection and multiple comparisons prevent a causal or definitive
significance interpretation. They are not a trend across the observation gap.

## Results

### RQ2: predictive meteorological associations

Weather-only daily held-week R² ranged from 0.3676 to 0.8302 across approved city/era cohorts. The unchanged nested screen passed all observed eras in 3 of 7 main cohorts: lucknow, mumbai, bengaluru. At least one era failed in delhi, hyderabad, kanpur, pune; those failures are retained rather than weakening criteria.

| City | Cohort | Era | Run 7 week R² | Nested R² | Weather RF R² | Weather GAM R² | Days | NMB % | Worst month |NMB| % | Frozen gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| delhi | fixed_panel | old | 0.6605 | 0.6709 | 0.6260 | 0.5168 | 1812 | -0.6781 | 5.0315 | pass |
| delhi | fixed_panel | recent | 0.7594 | 0.7285 | 0.6833 | 0.5692 | 647 | 8.6314 | 36.0077 | fail |
| delhi | all_stations | old | 0.6605 | 0.7018 | 0.6256 | 0.5196 | 1812 | -0.5612 | 7.7952 | pass |
| delhi | all_stations | recent | 0.7607 | 0.7140 | 0.6877 | 0.5710 | 689 | 7.8491 | 32.5045 | fail |
| hyderabad | fixed_panel | old | 0.5170 | 0.2540 | 0.4387 | 0.4250 | 1420 | 3.0343 | 49.5754 | fail |
| hyderabad | fixed_panel | recent | 0.7150 | 0.7093 | 0.6782 | 0.6793 | 731 | 3.1804 | 10.9311 | pass |
| hyderabad | all_stations | old | 0.5170 | 0.4913 | 0.4456 | 0.4331 | 1420 | 2.1820 | 13.7542 | fail |
| hyderabad | all_stations | recent | 0.6896 | 0.6796 | 0.6541 | 0.6610 | 731 | 0.6773 | 5.7149 | pass |
| kanpur | fixed_panel | unavailable | unavailable | unavailable | unavailable | unavailable | — | unavailable | unavailable | unavailable |
| kanpur | all_stations | old | 0.6382 | 0.5634 | 0.5102 | 0.4931 | 1287 | 3.4454 | 20.8674 | fail |
| lucknow | fixed_panel | unavailable | unavailable | unavailable | unavailable | unavailable | — | unavailable | unavailable | unavailable |
| lucknow | all_stations | old | 0.6550 | 0.6723 | 0.5972 | 0.5197 | 1651 | 1.0127 | 13.4184 | pass |
| mumbai | fixed_panel | unavailable | unavailable | unavailable | unavailable | unavailable | — | unavailable | unavailable | descriptive only |
| mumbai | all_stations | old | 0.6018 | 0.5678 | 0.4453 | 0.4240 | 1379 | -2.2567 | 11.6332 | pass |
| mumbai | all_stations | recent | 0.7600 | 0.7420 | 0.7368 | 0.6577 | 731 | 5.5129 | 18.0945 | pass |
| pune | fixed_panel | unavailable | unavailable | unavailable | unavailable | unavailable | — | unavailable | unavailable | unavailable |
| pune | all_stations | recent | 0.8412 | 0.8479 | 0.8302 | 0.8251 | 626 | 0.7298 | 20.4888 | fail |
| bengaluru | fixed_panel | old | 0.5254 | 0.5090 | 0.3676 | 0.3694 | 977 | 2.0666 | 14.3468 | pass |
| bengaluru | fixed_panel | recent | 0.6641 | 0.6894 | 0.6633 | 0.6515 | 731 | 1.2082 | 7.4129 | pass |
| bengaluru | all_stations | old | 0.3501 | unavailable | unavailable | unavailable | — | unavailable | unavailable | descriptive only |
| bengaluru | all_stations | recent | 0.6603 | unavailable | unavailable | unavailable | — | unavailable | unavailable | descriptive only |

![Daily paired validation](../../data/results/19/weather_validation.png)

The full RF includes temporal information, so its R² is not the weather share.
Weather-only RF R² expresses held-week predictive skill conditional on the observed
era and network. Negative values, if present, are retained. IGP cities (Delhi,
Kanpur, Lucknow) and coastal/southern cities are compared in the same table, without
pooling their concentrations or treating seven selected cities as a regional sample.

| Group | Era | Cities | Median weather-only R² | Median full nested R² |
| --- | --- | --- | --- | --- |
| Coastal/southern | old | 3 | 0.4453 | 0.5090 |
| Coastal/southern | recent | 4 | 0.7001 | 0.7157 |
| Indo-Gangetic plain | old | 3 | 0.5972 | 0.6723 |
| Indo-Gangetic plain | recent | 1 | 0.6877 | 0.7140 |

Group medians are unweighted descriptions of the eligible city/era samples.
The recent IGP group has only Delhi, whereas Kanpur and Lucknow lack recent data;
differences are not a balanced regional comparison.

Driver allocations vary across settings and periods. Delhi's weather SHAP leaders
include temperature, wind and pressure; Lucknow's retained BLH is prominent outside
the monsoon as well as pressure; Mumbai emphasises rain/pressure and older wind
direction; Pune emphasises humidity and wind direction; Bengaluru's fixed panel
shifts from humidity/wind speed in the old period to wind direction/rain recently.
Hyderabad's network change also changes recent driver allocations. These statements
describe the ranked results below, not independent physical causal effects.

| City | Cohort | Era | Season | Top three weather SHAP magnitudes (µg/m³) | Days |
| --- | --- | --- | --- | --- | --- |
| delhi | fixed_panel | old | monsoon | temperature_c: 10.6343; total_cloud_cover: 5.1732; wind_speed_ms: 4.2401 | 30 |
| delhi | fixed_panel | old | pre_monsoon | temperature_c: 4.5097; wind_speed_ms: 3.9814; total_cloud_cover: 2.7978 | 30 |
| delhi | fixed_panel | old | winter | wind_speed_ms: 8.4880; temperature_c: 7.2786; surface_pressure_hpa: 5.6521 | 30 |
| delhi | fixed_panel | recent | monsoon | temperature_c: 11.0393; surface_pressure_hpa: 7.1029; wind_speed_ms: 3.4278 | 30 |
| delhi | fixed_panel | recent | pre_monsoon | temperature_c: 4.6846; relative_humidity: 4.1222; wind_speed_ms: 3.8697 | 30 |
| delhi | fixed_panel | recent | winter | temperature_c: 8.6172; surface_pressure_hpa: 6.8386; wind_speed_ms: 5.2588 | 30 |
| delhi | all_stations | old | monsoon | temperature_c: 10.6343; total_cloud_cover: 5.1732; wind_speed_ms: 4.2401 | 30 |
| delhi | all_stations | old | pre_monsoon | temperature_c: 4.5097; wind_speed_ms: 3.9814; total_cloud_cover: 2.7978 | 30 |
| delhi | all_stations | old | winter | wind_speed_ms: 8.4880; temperature_c: 7.2786; surface_pressure_hpa: 5.6521 | 30 |
| delhi | all_stations | recent | monsoon | temperature_c: 10.0522; surface_pressure_hpa: 7.2363; wind_speed_ms: 3.1602 | 30 |
| delhi | all_stations | recent | pre_monsoon | temperature_c: 4.2855; relative_humidity: 4.0448; wind_speed_ms: 3.7255 | 30 |
| delhi | all_stations | recent | winter | temperature_c: 8.0705; surface_pressure_hpa: 7.1707; wind_speed_ms: 4.9968 | 30 |
| hyderabad | fixed_panel | old | monsoon | wind_speed_ms: 2.9459; surface_pressure_hpa: 2.7753; relative_humidity: 2.3104 | 30 |
| hyderabad | fixed_panel | old | pre_monsoon | relative_humidity: 2.6795; wind_direction: 1.9441; wind_speed_ms: 1.5481 | 30 |
| hyderabad | fixed_panel | old | winter | wind_direction: 3.4425; surface_pressure_hpa: 2.5692; wind_speed_ms: 2.3122 | 30 |
| hyderabad | fixed_panel | recent | monsoon | wind_speed_ms: 3.2647; surface_pressure_hpa: 2.1970; total_cloud_cover: 1.6639 | 30 |
| hyderabad | fixed_panel | recent | pre_monsoon | wind_speed_ms: 2.2624; total_cloud_cover: 2.1961; temperature_c: 1.9470 | 30 |
| hyderabad | fixed_panel | recent | winter | temperature_c: 3.5145; wind_speed_ms: 3.1669; wind_direction: 2.3798 | 30 |
| hyderabad | all_stations | old | monsoon | wind_speed_ms: 2.9459; surface_pressure_hpa: 2.7753; relative_humidity: 2.3104 | 30 |
| hyderabad | all_stations | old | pre_monsoon | relative_humidity: 2.6795; wind_direction: 1.9441; wind_speed_ms: 1.5481 | 30 |
| hyderabad | all_stations | old | winter | wind_direction: 3.4425; surface_pressure_hpa: 2.5692; wind_speed_ms: 2.3122 | 30 |
| hyderabad | all_stations | recent | monsoon | wind_speed_ms: 1.5646; total_cloud_cover: 0.9012; wind_direction: 0.7927 | 30 |
| hyderabad | all_stations | recent | pre_monsoon | total_cloud_cover: 1.1763; wind_speed_ms: 1.1089; wind_direction: 0.7570 | 30 |
| hyderabad | all_stations | recent | winter | wind_speed_ms: 1.6488; wind_direction: 1.2754; temperature_c: 1.1679 | 30 |
| kanpur | all_stations | old | monsoon | surface_pressure_hpa: 7.9004; total_cloud_cover: 5.4133; temperature_c: 4.8743 | 30 |
| kanpur | all_stations | old | pre_monsoon | temperature_c: 4.0116; total_cloud_cover: 3.9445; relative_humidity: 3.6359 | 30 |
| kanpur | all_stations | old | winter | surface_pressure_hpa: 9.1997; wind_speed_ms: 9.1094; temperature_c: 6.0560 | 30 |
| lucknow | all_stations | old | monsoon | surface_pressure_hpa: 4.9703; boundary_layer_height_m: 3.7031; temperature_c: 2.9979 | 30 |
| lucknow | all_stations | old | pre_monsoon | boundary_layer_height_m: 4.6747; surface_pressure_hpa: 3.1157; total_cloud_cover: 2.5963 | 30 |
| lucknow | all_stations | old | winter | boundary_layer_height_m: 8.9846; surface_pressure_hpa: 7.1478; total_cloud_cover: 3.1382 | 30 |
| mumbai | all_stations | old | monsoon | precipitation_mm: 1.8157; wind_direction: 1.7902; surface_pressure_hpa: 1.3660 | 30 |
| mumbai | all_stations | old | pre_monsoon | wind_direction: 1.3620; surface_pressure_hpa: 1.1059; precipitation_mm: 0.6564 | 30 |
| mumbai | all_stations | old | winter | wind_direction: 2.7702; surface_pressure_hpa: 2.2747; precipitation_mm: 1.1224 | 30 |
| mumbai | all_stations | recent | monsoon | precipitation_mm: 4.0654; surface_pressure_hpa: 1.3817; total_cloud_cover: 0.5445 | 30 |
| mumbai | all_stations | recent | pre_monsoon | precipitation_mm: 2.3019; surface_pressure_hpa: 0.9197; total_cloud_cover: 0.5168 | 30 |
| mumbai | all_stations | recent | winter | precipitation_mm: 2.6083; surface_pressure_hpa: 1.6108; total_cloud_cover: 1.0227 | 30 |
| pune | all_stations | recent | monsoon | relative_humidity: 6.5386; precipitation_mm: 2.2575; wind_direction: 2.1503 | 30 |
| pune | all_stations | recent | pre_monsoon | relative_humidity: 6.7161; wind_direction: 3.7549; precipitation_mm: 1.5258 | 30 |
| pune | all_stations | recent | winter | relative_humidity: 7.2308; wind_direction: 4.8149; precipitation_mm: 2.5074 | 30 |
| bengaluru | fixed_panel | old | monsoon | relative_humidity: 10.3442; wind_speed_ms: 3.0355; wind_direction: 1.4993 | 30 |
| bengaluru | fixed_panel | old | pre_monsoon | relative_humidity: 9.0796; wind_speed_ms: 2.9747; wind_direction: 0.7467 | 30 |
| bengaluru | fixed_panel | old | winter | relative_humidity: 7.4494; wind_speed_ms: 2.1426; wind_direction: 1.5125 | 30 |
| bengaluru | fixed_panel | recent | monsoon | wind_direction: 5.8488; precipitation_mm: 2.5955; wind_speed_ms: 0.6877 | 30 |
| bengaluru | fixed_panel | recent | pre_monsoon | wind_direction: 3.6306; precipitation_mm: 3.1539; relative_humidity: 1.4020 | 30 |
| bengaluru | fixed_panel | recent | winter | wind_direction: 4.7374; precipitation_mm: 3.4321; temperature_c: 1.4587 | 30 |

| City | Cohort | Era | Season | Model | Daily R² | Days |
| --- | --- | --- | --- | --- | --- | --- |
| delhi | all_stations | old | monsoon | full_rf | 0.3071 | 608 |
| delhi | all_stations | old | monsoon | weather_rf | 0.1925 | 608 |
| delhi | all_stations | old | monsoon | weather_gam | -0.5691 | 608 |
| delhi | all_stations | old | pre_monsoon | full_rf | 0.2081 | 457 |
| delhi | all_stations | old | pre_monsoon | weather_rf | -0.0782 | 457 |
| delhi | all_stations | old | pre_monsoon | weather_gam | -0.3406 | 457 |
| delhi | all_stations | old | winter | full_rf | 0.4550 | 747 |
| delhi | all_stations | old | winter | weather_rf | 0.3170 | 747 |
| delhi | all_stations | old | winter | weather_gam | 0.1644 | 747 |
| delhi | all_stations | recent | monsoon | full_rf | -0.1224 | 244 |
| delhi | all_stations | recent | monsoon | weather_rf | -0.4442 | 244 |
| delhi | all_stations | recent | monsoon | weather_gam | -2.2041 | 244 |
| delhi | all_stations | recent | pre_monsoon | full_rf | -0.0719 | 163 |
| delhi | all_stations | recent | pre_monsoon | weather_rf | -0.2895 | 163 |
| delhi | all_stations | recent | pre_monsoon | weather_gam | -1.2595 | 163 |
| delhi | all_stations | recent | winter | full_rf | 0.4489 | 282 |
| delhi | all_stations | recent | winter | weather_rf | 0.4112 | 282 |
| delhi | all_stations | recent | winter | weather_gam | 0.2545 | 282 |
| hyderabad | all_stations | old | monsoon | full_rf | 0.0606 | 471 |
| hyderabad | all_stations | old | monsoon | weather_rf | -0.0202 | 471 |
| hyderabad | all_stations | old | monsoon | weather_gam | -0.0196 | 471 |
| hyderabad | all_stations | old | pre_monsoon | full_rf | 0.3016 | 365 |
| hyderabad | all_stations | old | pre_monsoon | weather_rf | 0.1865 | 365 |
| hyderabad | all_stations | old | pre_monsoon | weather_gam | 0.2085 | 365 |
| hyderabad | all_stations | old | winter | full_rf | 0.3426 | 584 |
| hyderabad | all_stations | old | winter | weather_rf | 0.2922 | 584 |
| hyderabad | all_stations | old | winter | weather_gam | 0.2299 | 584 |
| hyderabad | all_stations | recent | monsoon | full_rf | 0.4810 | 244 |
| hyderabad | all_stations | recent | monsoon | weather_rf | 0.1136 | 244 |
| hyderabad | all_stations | recent | monsoon | weather_gam | 0.2318 | 244 |
| hyderabad | all_stations | recent | pre_monsoon | full_rf | 0.3450 | 184 |
| hyderabad | all_stations | recent | pre_monsoon | weather_rf | 0.2755 | 184 |
| hyderabad | all_stations | recent | pre_monsoon | weather_gam | 0.1928 | 184 |
| hyderabad | all_stations | recent | winter | full_rf | 0.4519 | 303 |
| hyderabad | all_stations | recent | winter | weather_rf | 0.4903 | 303 |
| hyderabad | all_stations | recent | winter | weather_gam | 0.4986 | 303 |
| kanpur | all_stations | old | monsoon | full_rf | 0.0067 | 458 |
| kanpur | all_stations | old | monsoon | weather_rf | 0.0037 | 458 |
| kanpur | all_stations | old | monsoon | weather_gam | -0.6009 | 458 |
| kanpur | all_stations | old | pre_monsoon | full_rf | 0.2213 | 315 |
| kanpur | all_stations | old | pre_monsoon | weather_rf | -0.1098 | 315 |
| kanpur | all_stations | old | pre_monsoon | weather_gam | -0.1533 | 315 |
| kanpur | all_stations | old | winter | full_rf | 0.1912 | 514 |
| kanpur | all_stations | old | winter | weather_rf | 0.1583 | 514 |
| kanpur | all_stations | old | winter | weather_gam | 0.1873 | 514 |
| lucknow | all_stations | old | monsoon | full_rf | 0.2905 | 575 |
| lucknow | all_stations | old | monsoon | weather_rf | 0.1559 | 575 |
| lucknow | all_stations | old | monsoon | weather_gam | -0.0974 | 575 |
| lucknow | all_stations | old | pre_monsoon | full_rf | 0.2579 | 420 |
| lucknow | all_stations | old | pre_monsoon | weather_rf | -0.0713 | 420 |
| lucknow | all_stations | old | pre_monsoon | weather_gam | -0.1614 | 420 |
| lucknow | all_stations | old | winter | full_rf | 0.4272 | 656 |
| lucknow | all_stations | old | winter | weather_rf | 0.3287 | 656 |
| lucknow | all_stations | old | winter | weather_gam | 0.1868 | 656 |
| mumbai | all_stations | old | monsoon | full_rf | 0.4326 | 462 |
| mumbai | all_stations | old | monsoon | weather_rf | -0.1013 | 462 |
| mumbai | all_stations | old | monsoon | weather_gam | -0.1848 | 462 |
| mumbai | all_stations | old | pre_monsoon | full_rf | 0.3920 | 358 |
| mumbai | all_stations | old | pre_monsoon | weather_rf | 0.1928 | 358 |
| mumbai | all_stations | old | pre_monsoon | weather_gam | 0.1047 | 358 |
| mumbai | all_stations | old | winter | full_rf | 0.1862 | 559 |
| mumbai | all_stations | old | winter | weather_rf | 0.0581 | 559 |
| mumbai | all_stations | old | winter | weather_gam | 0.0501 | 559 |
| mumbai | all_stations | recent | monsoon | full_rf | -0.1281 | 244 |
| mumbai | all_stations | recent | monsoon | weather_rf | -1.5919 | 244 |
| mumbai | all_stations | recent | monsoon | weather_gam | -2.5728 | 244 |
| mumbai | all_stations | recent | pre_monsoon | full_rf | 0.3278 | 184 |
| mumbai | all_stations | recent | pre_monsoon | weather_rf | 0.3954 | 184 |
| mumbai | all_stations | recent | pre_monsoon | weather_gam | 0.0316 | 184 |
| mumbai | all_stations | recent | winter | full_rf | 0.3571 | 303 |
| mumbai | all_stations | recent | winter | weather_rf | 0.3964 | 303 |
| mumbai | all_stations | recent | winter | weather_gam | 0.2705 | 303 |
| pune | all_stations | recent | monsoon | full_rf | 0.3362 | 235 |
| pune | all_stations | recent | monsoon | weather_rf | 0.2527 | 235 |
| pune | all_stations | recent | monsoon | weather_gam | -0.0140 | 235 |
| pune | all_stations | recent | pre_monsoon | full_rf | 0.5178 | 123 |
| pune | all_stations | recent | pre_monsoon | weather_rf | 0.4916 | 123 |
| pune | all_stations | recent | pre_monsoon | weather_gam | 0.5956 | 123 |
| pune | all_stations | recent | winter | full_rf | 0.6952 | 268 |
| pune | all_stations | recent | winter | weather_rf | 0.6545 | 268 |
| pune | all_stations | recent | winter | weather_gam | 0.6337 | 268 |
| bengaluru | fixed_panel | old | monsoon | full_rf | -0.1870 | 311 |
| bengaluru | fixed_panel | old | monsoon | weather_rf | -0.1777 | 311 |
| bengaluru | fixed_panel | old | monsoon | weather_gam | -0.3715 | 311 |
| bengaluru | fixed_panel | old | pre_monsoon | full_rf | 0.2509 | 243 |
| bengaluru | fixed_panel | old | pre_monsoon | weather_rf | 0.0458 | 243 |
| bengaluru | fixed_panel | old | pre_monsoon | weather_gam | 0.0383 | 243 |
| bengaluru | fixed_panel | old | winter | full_rf | 0.4154 | 423 |
| bengaluru | fixed_panel | old | winter | weather_rf | 0.1820 | 423 |
| bengaluru | fixed_panel | old | winter | weather_gam | 0.2228 | 423 |
| bengaluru | fixed_panel | recent | monsoon | full_rf | 0.3519 | 244 |
| bengaluru | fixed_panel | recent | monsoon | weather_rf | 0.2715 | 244 |
| bengaluru | fixed_panel | recent | monsoon | weather_gam | 0.2097 | 244 |
| bengaluru | fixed_panel | recent | pre_monsoon | full_rf | 0.5861 | 184 |
| bengaluru | fixed_panel | recent | pre_monsoon | weather_rf | 0.4945 | 184 |
| bengaluru | fixed_panel | recent | pre_monsoon | weather_gam | 0.4200 | 184 |
| bengaluru | fixed_panel | recent | winter | full_rf | 0.4025 | 303 |
| bengaluru | fixed_panel | recent | winter | weather_rf | 0.3793 | 303 |
| bengaluru | fixed_panel | recent | winter | weather_gam | 0.3856 | 303 |

Seasonal R² uses all supported outer-fold days rather than the SHAP subsample.
It can be negative within a low-variance season even when annual skill is high.

Top-three magnitudes are daily mean absolute SHAP in µg/m³, not percentages of
variance. The full per-feature signed/magnitude table and seasonal ALE curves are
under each child run. High SHAP magnitude does not establish an independent driver.
These extrema summarise the strongest and weakest GAM/RF ALE shape agreements;
the full table includes null/constant unsupported shapes.

| City | Cohort | Era | Season | Driver | ALE rank correlation |
| --- | --- | --- | --- | --- | --- |
| delhi | fixed_panel | old | pre_monsoon | relative_humidity | 1.0000 |
| delhi | fixed_panel | old | monsoon | total_cloud_cover | 1.0000 |
| delhi | fixed_panel | recent | winter | wind_speed_ms | 1.0000 |
| delhi | fixed_panel | recent | pre_monsoon | wind_speed_ms | 1.0000 |
| delhi | fixed_panel | recent | monsoon | precipitation_mm | 1.0000 |
| delhi | fixed_panel | recent | monsoon | total_cloud_cover | 1.0000 |
| delhi | all_stations | old | pre_monsoon | relative_humidity | 1.0000 |
| delhi | all_stations | old | monsoon | total_cloud_cover | 1.0000 |
| delhi | all_stations | recent | winter | wind_speed_ms | 1.0000 |
| delhi | all_stations | recent | pre_monsoon | wind_speed_ms | 1.0000 |
| delhi | all_stations | recent | monsoon | precipitation_mm | 1.0000 |
| delhi | all_stations | recent | monsoon | solar_radiation_wm2 | 1.0000 |
| hyderabad | all_stations | recent | monsoon | surface_pressure_hpa | -1.0000 |
| lucknow | all_stations | old | pre_monsoon | temperature_c | -1.0000 |
| lucknow | all_stations | old | monsoon | solar_radiation_wm2 | -1.0000 |
| mumbai | all_stations | old | monsoon | solar_radiation_wm2 | -1.0000 |
| mumbai | all_stations | recent | winter | temperature_c | -1.0000 |
| mumbai | all_stations | recent | monsoon | solar_radiation_wm2 | -1.0000 |
| pune | all_stations | recent | pre_monsoon | temperature_c | -1.0000 |
| pune | all_stations | recent | monsoon | temperature_c | -1.0000 |
| bengaluru | fixed_panel | recent | monsoon | temperature_c | -1.0000 |
| delhi | fixed_panel | old | pre_monsoon | surface_pressure_hpa | -1.0000 |
| delhi | all_stations | old | pre_monsoon | surface_pressure_hpa | -1.0000 |
| lucknow | all_stations | old | monsoon | temperature_c | -1.0000 |

### RQ5: PM2.5 proxy for NCAP progress

All seven eligible cities are unstarred non-attainment entries in the official CPCB
list (Bengaluru appears as Bangalore). The seed incorrectly treated Chennai's starred
million-plus participation as non-attainment; its default and live reference flag
are corrected. Official verification, entry numbers, prior flags and PDF SHA are
stored in DataRun 9. The APIs explicitly return `is_official_compliance_result=false`
and `official_compliance_assessment="not assessed"`.

| City | Cohort | Raw change %, 95% CI | Normalised change %, 95% CI | Status |
| --- | --- | --- | --- | --- |
| delhi | fixed_panel | -9.0092% [-24.8318, 11.9293] | -11.3773% [-16.2762, 4.3523] | descriptive |
| delhi | all_stations | -12.0944% [-27.6916, 5.9629] | -11.5627% [-19.7344, 3.3109] | descriptive |
| hyderabad | fixed_panel | -20.9298% [-32.7877, -9.5977] | -17.3265% [-23.9254, -7.1533] | descriptive |
| hyderabad | all_stations | -26.5393% [-36.2344, -16.8317] | -23.3790% [-29.3164, -15.5945] | descriptive |
| kanpur | all_stations | unavailable | unavailable | unavailable: Required eligible years are missing; available years [2016, 2017, 2018, 2019] |
| lucknow | all_stations | unavailable | unavailable | unavailable: Required eligible years are missing; available years [2015, 2016, 2017, 2018, 2019] |
| mumbai | all_stations | unavailable | unavailable | unavailable: Required eligible years are missing; available years [2015, 2016, 2017, 2019, 2024, 2025] |
| pune | all_stations | unavailable | unavailable | unavailable: Required eligible years are missing; available years [2024, 2025] |
| bengaluru | fixed_panel | unavailable | unavailable | unavailable: Required eligible years are missing; available years [2016, 2018, 2019, 2024, 2025] |

The eligible baseline/recent comparison exists only for Delhi and Hyderabad.
Delhi's raw and normalised proxy intervals span zero. Hyderabad's estimates are
negative under this bootstrap, but its old-era nested failure, especially on the
fixed panel, weakens a model-based progress interpretation. Bengaluru's approved
fixed panel lacks eligible 2017 observations; its failed all-station model is not
used to fill that baseline. Mumbai lacks an eligible 2018; Kanpur and Lucknow lack
recent targets; Pune lacks the historic baseline. Missing comparisons remain missing.

Recent PM10 is context only. Missing historical PM10, fiscal/calendar mismatch and
station/source changes prevent an official compliance comparison.

| City | Year | Recent PM10 mean µg/m³ | Valid days | Eligible | Interpretation |
| --- | --- | --- | --- | --- | --- |
| delhi | 2024 | 211.9545 | 366 | True | recent context only |
| delhi | 2025 | 198.8224 | 365 | True | recent context only |
| hyderabad | 2024 | 75.3756 | 366 | True | recent context only |
| hyderabad | 2025 | 82.4546 | 365 | True | recent context only |
| kanpur | 2024 | unavailable | — | — | unavailable |
| kanpur | 2025 | unavailable | — | — | unavailable |
| lucknow | 2024 | unavailable | — | — | unavailable |
| lucknow | 2025 | unavailable | — | — | unavailable |
| mumbai | 2024 | 86.7870 | 366 | True | recent context only |
| mumbai | 2025 | 88.4832 | 365 | True | recent context only |
| pune | 2024 | 81.0567 | 366 | True | recent context only |
| pune | 2025 | 95.2825 | 365 | True | recent context only |
| bengaluru | 2024 | 70.5750 | 366 | True | recent context only |
| bengaluru | 2025 | 72.7089 | 365 | True | recent context only |

| City | Cohort | Year | PM10 mean | Valid days | Eligible |
| --- | --- | --- | --- | --- | --- |
| delhi | fixed_panel | 2024 | 212.9446 | 366 | True |
| delhi | fixed_panel | 2025 | 199.8469 | 365 | True |
| delhi | all_stations | 2024 | 211.9545 | 366 | True |
| delhi | all_stations | 2025 | 198.8224 | 365 | True |
| hyderabad | fixed_panel | 2024 | 79.5407 | 366 | True |
| hyderabad | fixed_panel | 2025 | 85.9857 | 365 | True |
| hyderabad | all_stations | 2024 | 75.3756 | 366 | True |
| hyderabad | all_stations | 2025 | 82.4546 | 365 | True |
| kanpur | all_stations | 2024 | unavailable | — | — |
| kanpur | all_stations | 2025 | unavailable | — | — |
| lucknow | all_stations | 2024 | unavailable | — | — |
| lucknow | all_stations | 2025 | unavailable | — | — |
| mumbai | fixed_panel | 2024 | 86.3082 | 365 | True |
| mumbai | fixed_panel | 2025 | 86.0691 | 364 | True |
| mumbai | all_stations | 2024 | 86.7870 | 366 | True |
| mumbai | all_stations | 2025 | 88.4832 | 365 | True |
| pune | all_stations | 2024 | 81.0567 | 366 | True |
| pune | all_stations | 2025 | 95.2825 | 365 | True |
| bengaluru | fixed_panel | 2024 | 68.8951 | 366 | True |
| bengaluru | fixed_panel | 2025 | 71.5662 | 365 | True |
| bengaluru | all_stations | 2024 | 70.5750 | 366 | True |
| bengaluru | all_stations | 2025 | 72.7089 | 365 | True |

### Within-era monthly trends

| City | Cohort | Era | Months | Sen slope µg/m³/year | Slope 95% CI | MK p | Seasonal MK p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delhi | fixed_panel | old | 60 | -5.0713 | ['-5.6094', '-4.5368'] | 2.49268e-16 | 2.55311e-12 |
| delhi | fixed_panel | recent | 24 | -5.8867 | ['-7.9827', '-3.5861'] | 0.000053 | 0.009375 |
| delhi | all_stations | old | 60 | -5.0713 | ['-5.6094', '-4.5368'] | 2.49268e-16 | 2.55311e-12 |
| delhi | all_stations | recent | 24 | -6.5600 | ['-8.8878', '-3.9080'] | 0.000065 | 0.009375 |
| hyderabad | fixed_panel | old | 47 | -2.2467 | ['-3.1795', '-1.4535'] | 1.54386e-10 | 0.000004 |
| hyderabad | fixed_panel | recent | 24 | 0.5534 | ['0.2036', '1.4967'] | 0.000180 | 0.009375 |
| hyderabad | all_stations | old | 47 | -2.2467 | ['-3.1795', '-1.4535'] | 1.54386e-10 | 0.000004 |
| hyderabad | all_stations | recent | 24 | 1.4101 | ['1.2605', '1.5867'] | 3.06176e-09 | 0.001496 |
| kanpur | all_stations | old | 42 | -11.7996 | ['-13.5435', '-10.1331'] | 1.95371e-17 | 7.223e-10 |
| lucknow | all_stations | old | 53 | -3.3448 | ['-4.3494', '-2.2401'] | 4.01852e-09 | 2.35952e-08 |
| mumbai | all_stations | old | 46 | -3.9404 | ['-4.5727', '-2.8928'] | 1.07747e-09 | 4.32733e-07 |
| mumbai | all_stations | recent | 24 | 0.8410 | ['0.2897', '1.9300'] | 0.006858 | 0.043308 |
| pune | all_stations | recent | 24 | 1.1413 | ['0.7382', '1.7164'] | 0.000018 | 0.001496 |
| bengaluru | fixed_panel | old | 29 | -1.0370 | ['-1.6681', '-0.7442'] | 1.72981e-09 | 0.000160 |
| bengaluru | fixed_panel | recent | 24 | -1.3974 | ['-1.6176', '-1.1985'] | 1.34531e-08 | 0.001496 |

Displayed p values are descriptive; exact values are retained in CSV/JSON. A printed
small p value does not cure dependence or identify a policy effect. No line is fit
across the gap.

### Delhi long-run weather-adjusted change

| Cohort | Series | Old mean | Recent mean | Difference µg/m³ | Refit/block 95% CI | Change % |
| --- | --- | --- | --- | --- | --- | --- |
| fixed_panel | raw | 117.7881 | 103.0384 | -14.7497 | ['-35.2200', '7.2548'] | -12.5222 |
| fixed_panel | normalised | 120.7521 | 103.5061 | -17.2460 | ['-32.9462', '1.9778'] | -14.2822 |
| all_stations | raw | 117.7881 | 99.5447 | -18.2434 | ['-37.0500', '0.2248'] | -15.4883 |
| all_stations | normalised | 120.7521 | 103.2895 | -17.4626 | ['-34.6018', '1.2713'] | -14.4616 |

| Cohort | Series | Matched days | Change µg/m³ | Refit/block 95% CI |
| --- | --- | --- | --- | --- |
| fixed_panel | raw | 2417 | -15.3956 | [-36.1824, 7.9000] |
| fixed_panel | normalised | 2417 | -17.5920 | [-35.0711, 1.6623] |
| all_stations | raw | 2417 | -16.0607 | [-36.7080, 6.9736] |
| all_stations | normalised | 2417 | -18.1036 | [-35.2925, 1.3962] |

The first table uses each cohort's own OOF support. The second is the preferred
network comparison: both cohorts use exactly the same supported calendar dates.

The long-run baseline is the eligible 2015–2019 observations, distinct from the
2017–2018 proxy baseline. Normalised intervals incorporate the new refits; raw and
normalised rows use their shared nested-OOF date support. Any interval spanning zero
supports uncertainty about direction under this resampling method.

### Station-network composition

| City | Cohort | Year | Valid days | Mean PM2.5 | Daily maximum | Days >60 |
| --- | --- | --- | --- | --- | --- | --- |
| hyderabad | fixed_panel | 2025 | 365 | 37.804653 | 77.686921 | 53 |
| hyderabad | all_stations | 2025 | 365 | 35.021195 | 53.030602 | 0 |

Hyderabad's all-network versus matched-panel 2025 exceedance contrast survives the
stored timestamp repair. It is a network-composition sensitivity, not a corrected
unit conversion. Legacy integer-heavy station exports and unverified calibration
history remain source limitations. Full annual means, maxima and exceedances are
in `network_annual.csv`; a panel with inadequate coverage is explicitly descriptive.

| City | Cohort | Comparison | Series | Matched days | Change %, 95% CI |
| --- | --- | --- | --- | --- | --- |
| delhi | fixed_panel | long_run | raw | 2417 | -13.0705 [-28.8516, 6.7288] |
| delhi | fixed_panel | long_run | normalised | 2417 | -14.5687 [-26.1282, 1.5567] |
| delhi | fixed_panel | ncap_proxy | raw | 2417 | -9.5795 [-25.9946, 13.7785] |
| delhi | fixed_panel | ncap_proxy | normalised | 2417 | -11.6735 [-17.1660, 7.2941] |
| delhi | all_stations | long_run | raw | 2417 | -13.6353 [-29.2729, 5.9467] |
| delhi | all_stations | long_run | normalised | 2417 | -14.9924 [-26.2589, 1.3416] |
| delhi | all_stations | ncap_proxy | raw | 2417 | -10.1669 [-26.4549, 12.9678] |
| delhi | all_stations | ncap_proxy | normalised | 2417 | -12.1115 [-19.1777, 6.8575] |
| hyderabad | fixed_panel | long_run | raw | 2151 | -21.3882 [-31.8668, -8.1579] |
| hyderabad | fixed_panel | long_run | normalised | 2151 | -20.4003 [-30.3358, -8.5184] |
| hyderabad | fixed_panel | ncap_proxy | raw | 2151 | -20.9298 [-32.7877, -9.5977] |
| hyderabad | fixed_panel | ncap_proxy | normalised | 2151 | -17.3265 [-23.9254, -7.1533] |
| hyderabad | all_stations | long_run | raw | 2151 | -26.9652 [-34.9310, -16.4291] |
| hyderabad | all_stations | long_run | normalised | 2151 | -26.2278 [-35.5524, -15.7937] |
| hyderabad | all_stations | ncap_proxy | raw | 2151 | -26.5393 [-36.2344, -16.8317] |
| hyderabad | all_stations | ncap_proxy | normalised | 2151 | -23.3790 [-29.3164, -15.5945] |

The paired-network sensitivity additionally intersects the two cohorts' supported
OOF dates and uses those same dates in both raw and normalised comparisons.
This separates a changing network from unequal comparison-date support.

![delhi station-network sensitivity](../../data/results/19/delhi_network_comparison.png)
![hyderabad station-network sensitivity](../../data/results/19/hyderabad_network_comparison.png)
![kanpur station-network sensitivity](../../data/results/19/kanpur_network_comparison.png)
![lucknow station-network sensitivity](../../data/results/19/lucknow_network_comparison.png)
![mumbai station-network sensitivity](../../data/results/19/mumbai_network_comparison.png)
![pune station-network sensitivity](../../data/results/19/pune_network_comparison.png)
![bengaluru station-network sensitivity](../../data/results/19/bengaluru_network_comparison.png)

## Limitations

Weekly interpolation validation is not a forecast or a test across an emissions
regime change. Weather-only skill is conditional on selected cities, current grids
and era-specific levels. Refit intervals use 20 replicates and fixed selected
structures; they do not include all structural selection, historical instrument/GPS,
population exposure or unknown network uncertainty. SHAP is correlated-feature
allocation; ALE can have sparse support. GAM smoothness is fixed, not optimised.
The complete-case comparison can reduce OOF support when BLH is selected.

Station definitions, quality flags, source rounding and city/district assignment
are imperfect. Six/few-station panels are not city population-weighted exposure.
ERA5 is retrospectively available reanalysis, not a contemporaneous forecast input.
There is no old PM10, old NO2, 2020–2023 concentration history or FIRMS fire sample.
WHO thresholds and CPCB AQI provide context, not a health-effect or compliance result.

## What would change with more data

RQ1 (BS-VI) requires station-level 2019–2023 NO2 and PM2.5 (for example licensed,
quality-audited OpenAQ/CPCB archives), stable station identifiers, instrument and
relocation histories, contemporaneous weather, traffic/fleet/fuel/emissions data,
BS-VI implementation timing, lockdown dates and overlapping NCAP/industrial/transport
interventions. Observations around those dates and a defensible control/comparison
design would enable an attribution question. Current old/recent changes are only
weather-adjusted associations; the April 2020 event lies inside the missing era.

RQ3 is deferred pending FIRMS observations. The proposed analysis would retrieve
VIIRS/MODIS fire detections with actual UTC timestamps, confidence, FRP, product and
satellite identifiers; deduplicate overlapping products; distinguish no fire from
missing coverage; define Punjab/Haryana source regions; link source-receptor direction
to ERA5 transport winds; prespecify transport lags and upwind exposure; and model
daily PM2.5 anomalies within crop-burning seasons using held-week validation and
season/calendar, weather, festival and network controls. Test lag/window sensitivities
and false-positive controls before interpreting associations. No fire coefficient
is reported until detections and coverage are ingested and audited.

For Phase 4, the observed-period cohorts satisfying the unchanged nested screen are:
delhi old (all_stations), hyderabad recent (all_stations), lucknow old (all_stations), mumbai old (all_stations), mumbai recent (all_stations), bengaluru old (fixed_panel), bengaluru recent (fixed_panel). Additional nested-screen limitations are: delhi recent (all_stations): monthly NMB, hyderabad old (all_stations): daily R2, kanpur old (all_stations): monthly NMB, pune recent (all_stations): monthly NMB.
Prioritise recent Hyderabad, Mumbai and Bengaluru's fixed panel for initial
forecasting experiments, subject to fresh observations and rolling validation.
Delhi and Pune require investigation of their recent monthly-bias failures first.
Kanpur/Lucknow have no recent concentration targets and need fresh observations
before current forecasts. Candidate weather features
are the validated temperature, humidity, wind speed/direction, rain, pressure,
cloud/solar fields and BLH only with reliable availability; retain calendar features,
reassess local trend and consider lagged PM with leakage-safe training. Forecast
experiments need rolling-origin temporal validation, archived forecast vintages and
data available at issuance. No forecasts, RAG, simulator or dashboards are built here.

## Reproducibility and verification

Parent run 19, child runs [12, 13, 14, 15, 16, 10, 17], baseline 7,
diagnostic 8 and canonical multi-pollutant 9. All inputs/results remain on D:.
Fixed seeds, code hashes, package versions, original model weights, folds and refit
training-index hashes are recorded. Child manifests retain CSVs, PNG/SVG figures,
GAM objects, SHAP additivity errors and all 20 refit series.
The original 117 tests were preserved; the pre-fit full suite passed 124 tests,
and the final full suite passed 125 tests with 16 visible warnings in 20.85 seconds.
Ruff check and formatting pass for 167 files, Django check reports no issues,
no migrations are pending, and OpenAPI validation exits 0 without warnings.
All requested live research APIs and health return HTTP 200. Exact outputs and
hash checks are archived under this run's verification/ directory and VALIDATION.md.

## References

Only documents in [the project research library](../RESEARCH_LIBRARY.md) or already
listed in PHASE3A2 are cited. Source files and SHA-256 values are catalogued in
[RESEARCH_LIBRARY.json](../RESEARCH_LIBRARY.json).

- Grange et al. (2018), [Random forest meteorological normalisation models for Swiss PM10 trend analysis](https://acp.copernicus.org/articles/18/6223/2018/).
- Shi et al. (2021), *Abrupt but smaller than expected changes in surface air quality
  attributable to COVID-19 lockdowns*,
  [author-hosted paper](https://pure-oai.bham.ac.uk/ws/files/114238854/eabd6696.full.pdf),
  DOI 10.1126/sciadv.abd6696.
- CPCB, [List of 131 cities, including the starred million-plus footnote](https://cpcb.gov.in/uploads/Non-Attainment_Cities.pdf).
- MoEFCC/PIB, NCAP statement, 23 March 2023;
  [official source](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1909910&lang=2&reg=48).
  Updates dated 28 November 2024 and 23 July 2026 are in the linked research library.
- CPCB PRANA, [National Apex Committee minutes](https://prana.cpcb.gov.in/ncapDashboard/download_public_portal_file/Minutes_of_National_Apex_Committee_meeting.pdf).
- WHO (2021), [Global Air Quality Guidelines](https://www.who.int/publications/i/item/9789240034228/).
- CPCB, [National Air Quality Index](https://cpcb.gov.in/National-Air-Quality-Index/).
- Roberts et al. (2017), *Cross-validation strategies for data with temporal, spatial,
  hierarchical, or phylogenetic structure*,
  [primary source](https://nsojournals.onlinelibrary.wiley.com/doi/10.1111/ecog.02881),
  already listed in PHASE3A2.
- Huang et al. (2021),
  [Air-quality model performance evaluation](https://acp.copernicus.org/articles/21/2725/2021/),
  already listed in PHASE3A2; the frozen bias screen is an operational criterion,
  not proof of this model's validity.
