# Phase 3A2: diagnostic and method correction protocol

Frozen before any new model evaluation: 2026-10-08T16:29:51.054711+00:00. Baseline is AnalysisRun 2.
Old results remain stored.

## Exact Phase 3A holdout before changes

The code sorted eligible complete-case hourly rows by UTC timestamp, chose row
int(0.8 * n), trained only rows strictly earlier than that timestamp minus seven
days, and tested rows at or after it. The intervening seven days were excluded.
Training included all earlier eligible years, including early recent-era data
where available. This was a terminal chronological holdout, not random-week
interpolation CV or a pure old-to-recent transfer test. BLH nulls removed
January-June 2024 before splitting. All dates below are exact stored/computed UTC.

| City | Train start | Train end | Test start | Test end | Train hours | Test hours |
| --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | 2017-12-31T18:30:00+00:00 | 2019-07-30T11:30:00+00:00 | 2019-08-07T03:30:00+00:00 | 2019-12-31T17:30:00+00:00 | 12891 | 3262 |
| bengaluru | 2015-03-20T05:30:00+00:00 | 2024-10-07T17:30:00+00:00 | 2024-10-14T18:30:00+00:00 | 2025-12-31T17:30:00+00:00 | 42357 | 10632 |
| chennai | 2016-01-02T07:30:00+00:00 | 2024-11-25T17:30:00+00:00 | 2024-12-02T18:30:00+00:00 | 2025-12-31T17:30:00+00:00 | 37654 | 9456 |
| delhi | 2014-12-31T23:30:00+00:00 | 2024-09-07T21:30:00+00:00 | 2024-09-14T22:30:00+00:00 | 2025-12-31T17:30:00+00:00 | 45224 | 11348 |
| hyderabad | 2015-12-31T18:30:00+00:00 | 2024-11-23T16:30:00+00:00 | 2024-11-30T17:30:00+00:00 | 2025-12-31T17:30:00+00:00 | 37848 | 9505 |
| jaipur | 2017-12-31T18:30:00+00:00 | 2019-07-31T18:30:00+00:00 | 2019-08-07T19:30:00+00:00 | 2019-12-31T17:30:00+00:00 | 13838 | 3502 |
| kanpur | 2015-12-31T18:30:00+00:00 | 2019-03-16T07:30:00+00:00 | 2019-03-24T16:30:00+00:00 | 2019-12-31T16:30:00+00:00 | 25473 | 6402 |
| kolkata | 2018-12-31T18:30:00+00:00 | 2025-06-24T23:30:00+00:00 | 2025-07-02T00:30:00+00:00 | 2025-12-31T17:30:00+00:00 | 17373 | 4386 |
| lucknow | 2015-03-18T10:30:00+00:00 | 2019-01-25T04:30:00+00:00 | 2019-02-01T05:30:00+00:00 | 2019-12-31T17:30:00+00:00 | 31836 | 8001 |
| mumbai | 2014-12-31T23:30:00+00:00 | 2024-12-02T06:30:00+00:00 | 2024-12-09T07:30:00+00:00 | 2025-12-31T17:30:00+00:00 | 37025 | 9299 |
| patna | 2017-12-31T18:30:00+00:00 | 2019-07-27T13:30:00+00:00 | 2019-08-03T14:30:00+00:00 | 2019-12-31T17:30:00+00:00 | 13380 | 3387 |
| pune | 2024-06-30T23:30:00+00:00 | 2025-09-05T22:30:00+00:00 | 2025-09-12T23:30:00+00:00 | 2025-12-31T17:30:00+00:00 | 10368 | 2635 |

## Frozen readiness criteria

Use five-fold random whole-IST-week CV within each observed period, with a 24-hour
training embargo at held-week boundaries. Score periods separately on valid daily
means; hourly OOF predictions require 18 valid predicted hours per day. Every
available period must satisfy daily R2 >= 0.5, absolute normalised mean bias <= 10%,
and absolute NMB <= 20% in every calendar month. Require 26 distinct observed weeks
and 20 validated days in each calendar month per period. Insufficient support
is unavailable/fail, not a waived criterion. Random splits show fit quality;
cross-period transfer in both directions shows extrapolation and never gates readiness.

NMB = 100 * sum(predicted - observed) / sum(observed). Monthly gates use period
and month-of-year; diagnostics also show each year-month and season. The R2 gate
requires explaining half the withheld daily variance. Monthly gates prevent annual
bias cancellation. These project screens cannot guarantee scientific reliability.

[Grange et al. (2018)](https://acp.copernicus.org/articles/18/6223/2018/acp-18-6223-2018.pdf)
motivates daily RF targets, validation and resampling.
[Roberts et al. (2017)](https://nsojournals.onlinelibrary.wiley.com/doi/10.1111/ecog.02881)
distinguishes blocked interpolation from induced extrapolation.
[EPA evaluation guidance](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P100W5V2.TXT)
motivates NMB and seasonal evaluation. The PM2.5 benchmark discussion in the
[Huang et al. (2021)](https://acp.copernicus.org/articles/21/2725/2021/) reports
10%/20% NMB goal/criterion magnitudes. Our monthly gate and R2 threshold are
explicit project adaptations, not thresholds attributed to Grange.

## Frozen comparison and normalisation plan

D4 evaluates the old hourly predictor structure on random-hour, random-whole-week
and bidirectional cross-period splits. D5 uses eight fixed variants below without
hyperparameter tuning. Select per city using common valid daily dates across all
variants, avoiding a spurious BLH gain from removing half of 2024. Daily selected
models additionally report random-day validation, clearly separated from D4's
required hourly experiment. Pooled models have a period indicator and a trend
reset at each period start, never a continuous trend crossing 2020-2023.

All forests use 100 trees, depth 12, leaf minimum 12, max_features 0.7 and seed 42.
Independent fits may run in parallel but each forest is single-threaded. Thresholds
stay fixed even if no city passes. Readiness shares CV with model selection, so
independent confirmation will still be needed.

Normalisation uses 300 identical joint observed weather/seasonal donor draws from
the pooled weather of both periods per city, holding period/within-period trend
fixed. No target or plot axis is created for 2020-2023. No-trend models can give a
constant normalised level per period; report this explicitly. Conditional bootstrap
intervals use the declared centred residual block approximation and omit model
parameter and structural uncertainty.

```json
{
  "frozen_at": "2026-10-08T16:29:51.054711+00:00",
  "baseline_run": 2,
  "seed": 42,
  "n_trees": 100,
  "max_depth": 12,
  "min_samples_leaf": 12,
  "max_features": 0.7,
  "cv_folds": 5,
  "cv_week_timezone": "Asia/Kolkata",
  "cv_embargo_hours": 24,
  "normalisation_draws": 300,
  "bootstrap_draws": 500,
  "criteria": {
    "daily_oof_r2_min_each_period": 0.5,
    "absolute_nmb_percent_max_each_period": 10,
    "absolute_month_nmb_percent_max_each_period": 20,
    "minimum_days_month_each_period": 20,
    "minimum_weeks_each_period": 26
  },
  "variants": [
    {
      "name": "hourly_trend_pooled_blh",
      "target": "hourly",
      "trend": true,
      "periods": "pooled",
      "blh": true
    },
    {
      "name": "hourly_trend_pooled_no_blh",
      "target": "hourly",
      "trend": true,
      "periods": "pooled",
      "blh": false
    },
    {
      "name": "hourly_no_trend_pooled_no_blh",
      "target": "hourly",
      "trend": false,
      "periods": "pooled",
      "blh": false
    },
    {
      "name": "hourly_trend_separate_no_blh",
      "target": "hourly",
      "trend": true,
      "periods": "separate",
      "blh": false
    },
    {
      "name": "daily_trend_pooled_blh",
      "target": "daily",
      "trend": true,
      "periods": "pooled",
      "blh": true
    },
    {
      "name": "daily_trend_pooled_no_blh",
      "target": "daily",
      "trend": true,
      "periods": "pooled",
      "blh": false
    },
    {
      "name": "daily_no_trend_pooled_no_blh",
      "target": "daily",
      "trend": false,
      "periods": "pooled",
      "blh": false
    },
    {
      "name": "daily_trend_separate_no_blh",
      "target": "daily",
      "trend": true,
      "periods": "separate",
      "blh": false
    }
  ],
  "selection": "Per city, maximum mean period-specific daily OOF R2 on common valid days across eight fixed variants; tie by listed order. Evaluate readiness on all usable selected-design OOF days, regardless of whether it passes.",
  "normalisation": "Identical joint complete observed weather/seasonal donor draws pooled across 2015-2019 and 2024-2025 per city. Hold period and within-period trend fixed; no trend bridges the gap.",
  "normalised_intervals": "500 year/seven-calendar-day block resamples of normalised daily values with centred week-CV daily residuals added for conditional target-variability uncertainty. No model-parameter or station-network uncertainty.",
  "timestamps": "Never choose a source-clock shift to improve scores. Require source or cross-provider evidence. Rebin cached quarters to IST hours without rewriting original observations."
}
```

## Actual diagnostics and results

Model AnalysisRun **7** finished **2026-10-08T18:11:21.452470+00:00**; corrected data run **6**, legacy comparison run **2**. Original and provisional runs are retained. Compute commit `56f471b1f379dcf2163ee7902dc7d3df229488b1`; the immutable protocol JSON hash is `09d869e72551b31af0368b0d89a5c91510e8ecd65e6ce53605d33a704b827977`.

### D1: timestamp alignment

PostgreSQL stores both concentration and weather `observed_at` as timestamp with time zone and the session is UTC. Open-Meteo requests `timezone=UTC`; response `utc_offset_seconds=0` is validated. Historical XKDR `collected_at` is documented as naive IST and is converted to UTC. Recent OpenCity `+0000` labels contain IST wall clocks: physical times were 5.5 hours late. Same-site independent hourly comparisons below establish the correction without using model scores.

| City | Station | Matched hours | Mean absolute difference | Maximum difference |
| --- | --- | --- | --- | --- |
| bengaluru | site_1554 | 168 | 0.000000 | 0.000000 |
| chennai | site_306 | 168 | 0.002436 | 0.005000 |
| delhi | site_1560 | 167 | 0.000000 | 0.000000 |
| hyderabad | site_5597 | 93 | 0.002168 | 0.005000 |
| kolkata | site_5129 | 167 | 0.002520 | 0.005000 |
| mumbai | site_5412 | 165 | 0.002384 | 0.005000 |
| pune | site_5408 | 156 | 0.002452 | 0.005000 |

The publisher repository's UTC-label attachment is supporting context, not independently established lineage for every OpenCity file. The direct value-and-clock matches are the decisive evidence. Independent-source CSVs and hashes are preserved with this run. [XKDR clock documentation](https://github.com/xKDR/Air-Quality-Database/blob/main/docs/PUBLIC_API.md), [publisher processing context](https://github.com/Vonter/india-cpcb-aqi/blob/a58f47848e678c7cea58a69758343d08d0b49915/parse.py#L100-L114).

The original quarter aggregator used UTC bins, then the city builder relabelled their start as an IST hour. This is wrong for literal UTC quarters because IST has a half-hour offset. The literal-UTC reconstruction was retained as sensitivity data run 4. Once the publisher's IST clock is decoded, its four quarter-hour readings form native IST hours directly; those audited stored means can be reused after shifting their derived timestamps. Raw observation times and values remain immutable; consumers of raw warehouse times must apply the documented clock correction, or use the corrected analysis snapshot. Weather joins the native IST-hour midpoint, which is a UTC clock hour.

Lag is Pearson r(PM anomaly at t, wind anomaly at t+lag), calculated on actual timestamp pairs over -12 to +12 hours after removing period/month/IST-hour climatology. PM often anticorrelates with wind, so maximum signed r can be the least-negative boundary value. Both the requested signed maximum and strongest absolute correlation are reported; a nonzero lag alone is not proof of clock error.

| City | Era | Max signed lag/r | Strongest lag/r | r at zero |
| --- | --- | --- | --- | --- |
| ahmedabad | old | -12/-0.085 | -2/-0.152 | -0.139 |
| bengaluru | old | 4/-0.064 | -3/-0.076 | -0.067 |
| bengaluru | recent | 8/-0.123 | -4/-0.162 | -0.157 |
| chennai | old | 12/0.006 | -3/-0.050 | -0.033 |
| chennai | recent | 12/-0.001 | -3/-0.084 | -0.064 |
| delhi | old | 12/-0.091 | -2/-0.188 | -0.181 |
| delhi | recent | 12/-0.090 | -3/-0.206 | -0.194 |
| hyderabad | old | -12/-0.025 | -2/-0.083 | -0.073 |
| hyderabad | recent | 12/-0.157 | -1/-0.227 | -0.223 |
| jaipur | old | 12/0.041 | 12/0.041 | 0.001 |
| kanpur | old | 12/-0.060 | -6/-0.102 | -0.096 |
| kolkata | old | 12/-0.170 | -4/-0.250 | -0.229 |
| kolkata | recent | 12/-0.091 | -3/-0.164 | -0.154 |
| lucknow | old | 12/-0.054 | -12/-0.085 | -0.080 |
| mumbai | old | 9/-0.056 | -1/-0.095 | -0.093 |
| mumbai | recent | 6/-0.107 | -3/-0.134 | -0.125 |
| patna | old | 12/-0.119 | -10/-0.152 | -0.148 |
| pune | recent | 4/-0.036 | -6/-0.062 | -0.048 |

Each city's before/after PM2.5-temperature-BLH diurnal plot and complete lag curve are in the data-run artifacts; BLH-null hours are omitted from BLH averages and wind is available as the fallback. See the figure index below.

### D2: station locations and weather grids

| City | Station records | Inside assigned district | Inside any district | Request distance min km | Request distance max km | ERA5 grid distance max km |
| --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | 1 | 1 | 1 | 3.04 | 3.04 | 9.43 |
| bengaluru | 21 | 21 | 21 | 3.13 | 21.36 | 27.97 |
| chennai | 12 | 3 | 12 | 3.19 | 26.04 | 25.33 |
| delhi | 75 | 9 | 75 | 2.61 | 27.36 | 38.59 |
| hyderabad | 20 | 4 | 20 | 2.74 | 44.26 | 40.81 |
| jaipur | 3 | 3 | 3 | 1.29 | 7.00 | 13.79 |
| kanpur | 1 | 1 | 1 | 2.43 | 2.43 | 7.99 |
| kolkata | 14 | 10 | 14 | 2.81 | 8.14 | 19.52 |
| lucknow | 4 | 4 | 4 | 0.96 | 6.59 | 18.05 |
| mumbai | 40 | 29 | 40 | 1.63 | 20.86 | 29.74 |
| patna | 4 | 4 | 4 | 1.87 | 5.23 | 19.69 |
| pune | 12 | 12 | 12 | 1.31 | 18.69 | 24.55 |

There are **207** provider-specific station records. The complete per-station positions/containment/distance results are in `station_geography.csv`. Assigned district is not a metropolitan-city boundary: Delhi uses New Delhi, Chennai and Hyderabad include neighbouring districts, and Mumbai uses the historical Mumbai district. Out-of-assigned-district locations are reported, not silently relocated or excluded. Existing five unverified-GPS exclusions remain. Returned ERA5 grid points differ from requested city centres; a single point cannot resolve all station meteorology.

### D3: station network changes

| City | 2015 | 2016 | 2017 | 2018 | 2019 | 2024 | 2025 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | 1 | 1 | 1 | 1 | 1 | 0 | 0 |
| bengaluru | 3 | 3 | 3 | 8 | 8 | 11 | 11 |
| chennai | 2 | 2 | 2 | 2 | 3 | 7 | 7 |
| delhi | 9 | 10 | 17 | 36 | 36 | 39 | 39 |
| hyderabad | 2 | 3 | 6 | 6 | 6 | 14 | 14 |
| jaipur | 0 | 0 | 3 | 3 | 3 | 0 | 0 |
| kanpur | 1 | 1 | 1 | 1 | 1 | 0 | 0 |
| kolkata | 0 | 1 | 0 | 2 | 7 | 7 | 7 |
| lucknow | 3 | 3 | 3 | 3 | 3 | 0 | 0 |
| mumbai | 1 | 1 | 1 | 1 | 10 | 28 | 29 |
| patna | 1 | 1 | 1 | 1 | 4 | 0 | 0 |
| pune | 0 | 0 | 0 | 0 | 0 | 8 | 9 |

Counts require a quality-OK PM2.5 station hour; missing or invalid records do not count as contributing. `stations_by_year.csv` lists every physical CPCB ID/name/source/year, contributing hours and first/last timestamps. The fixed panel matches exact CPCB site IDs across providers and requires at least one valid observation in each era; year-level coverage is then enforced before comparing. Presence in both eras does not mean every station reports every day.

| City | Shared physical stations |
| --- | --- |
| ahmedabad | 0 |
| bengaluru | 7 |
| chennai | 3 |
| delhi | 36 |
| hyderabad | 6 |
| jaipur | 0 |
| kanpur | 0 |
| kolkata | 7 |
| lucknow | 0 |
| mumbai | 9 |
| patna | 0 |
| pune | 0 |

### D4: validation design

Phase 3A used the terminal chronological holdout documented above. The following comparisons retain its original predictor structure and original data, changing only the split. (a) is random hourly 80/20; (b) is five random whole-week folds within each observed era, with 24-hour embargo; (c) trains one era and tests the other. Across-gap transfer is diagnostic only and never a readiness gate. Single-era cities have no transfer test.

| City | a: random hourly R2 | b: week hourly R2 | c: old to recent R2 | c: recent to old R2 |
| --- | --- | --- | --- | --- |
| ahmedabad | 0.624 | 0.304 | unavailable | unavailable |
| bengaluru | 0.338 | 0.177 | -0.201 | -0.015 |
| chennai | 0.466 | 0.174 | -0.783 | -0.267 |
| delhi | 0.816 | 0.621 | 0.439 | 0.364 |
| hyderabad | 0.492 | 0.276 | -1.676 | 0.051 |
| jaipur | 0.531 | 0.230 | unavailable | unavailable |
| kanpur | 0.574 | 0.360 | unavailable | unavailable |
| kolkata | 0.872 | 0.734 | 0.095 | 0.288 |
| lucknow | 0.717 | 0.514 | unavailable | unavailable |
| mumbai | 0.637 | 0.425 | 0.137 | 0.158 |
| patna | 0.816 | 0.630 | unavailable | unavailable |
| pune | 0.889 | 0.787 | unavailable | unavailable |

Corrected hourly diagnostics below use the selected hourly model, or its hourly counterpart from the same frozen variant list when selection favours a daily target. These are actual random-hour, week-hour and transfer-hour evaluations on corrected data; they are descriptive and do not change selection or the daily readiness gate.

| City | Hourly design | a hourly R2 | b hourly R2 | c old/recent R2 | c recent/old R2 |
| --- | --- | --- | --- | --- | --- |
| ahmedabad | hourly_trend_pooled_blh | 0.622 | 0.302 | unavailable | unavailable |
| bengaluru | hourly_trend_separate_no_blh | 0.349 | 0.177 | -0.543 | 0.047 |
| chennai | hourly_trend_pooled_no_blh | 0.475 | 0.216 | -2.684 | -0.107 |
| delhi | hourly_trend_separate_no_blh | 0.823 | 0.607 | 0.418 | 0.485 |
| hyderabad | hourly_trend_separate_no_blh | 0.508 | 0.265 | -41.841 | 0.058 |
| jaipur | hourly_trend_pooled_no_blh | 0.531 | 0.219 | unavailable | unavailable |
| kanpur | hourly_trend_pooled_no_blh | 0.569 | 0.331 | unavailable | unavailable |
| kolkata | hourly_trend_separate_no_blh | 0.888 | 0.722 | -13.619 | 0.324 |
| lucknow | hourly_trend_pooled_blh | 0.716 | 0.519 | unavailable | unavailable |
| mumbai | hourly_trend_separate_no_blh | 0.641 | 0.415 | -0.056 | 0.189 |
| patna | hourly_trend_pooled_no_blh | 0.818 | 0.578 | unavailable | unavailable |
| pune | hourly_trend_separate_no_blh | 0.887 | 0.773 | unavailable | unavailable |

### D5: model structure and method decision

Eight prespecified paired variants compare hourly/daily target, BLH inclusion, trend inclusion and separate-era/pooled-period models. Forest parameters were fixed. Selection maximises mean era-specific daily week-CV R2 on the common valid dates of all eight variants. Readiness then uses every valid selected-model OOF day in each era. Selection and gating share CV, so the reported performance is not an untouched final-test estimate. The criteria were frozen before new fits and were not loosened.

| City | hourly_trend_pooled_blh | hourly_trend_pooled_no_blh | hourly_no_trend_pooled_no_blh | hourly_trend_separate_no_blh | daily_trend_pooled_blh | daily_trend_pooled_no_blh | daily_no_trend_pooled_no_blh | daily_trend_separate_no_blh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | 0.372 | 0.316 | 0.254 | 0.324 | 0.326 | 0.325 | 0.298 | 0.311 |
| bengaluru | 0.425 | 0.465 | 0.385 | 0.481 | 0.426 | 0.462 | 0.426 | 0.492 |
| chennai | 0.320 | 0.334 | 0.259 | 0.346 | 0.362 | 0.388 | 0.340 | 0.382 |
| delhi | 0.717 | 0.679 | 0.697 | 0.718 | 0.695 | 0.695 | 0.694 | 0.687 |
| hyderabad | 0.542 | 0.570 | 0.517 | 0.587 | 0.568 | 0.579 | 0.569 | 0.620 |
| jaipur | 0.363 | 0.342 | 0.260 | 0.358 | 0.395 | 0.405 | 0.318 | 0.400 |
| kanpur | 0.603 | 0.568 | 0.508 | 0.570 | 0.632 | 0.638 | 0.585 | 0.638 |
| kolkata | 0.777 | 0.742 | 0.767 | 0.764 | 0.727 | 0.772 | 0.753 | 0.778 |
| lucknow | 0.655 | 0.643 | 0.568 | 0.640 | 0.650 | 0.653 | 0.596 | 0.651 |
| mumbai | 0.643 | 0.677 | 0.609 | 0.708 | 0.682 | 0.685 | 0.653 | 0.689 |
| patna | 0.750 | 0.686 | 0.655 | 0.685 | 0.756 | 0.757 | 0.742 | 0.752 |
| pune | 0.867 | 0.865 | 0.794 | 0.869 | 0.872 | 0.871 | 0.845 | 0.874 |

Weather null counts below use all observed weather in the two reference eras, not just model targets. This distinguishes source missingness from PM coverage. BLH complete-case models lose the first six months of 2024; common-date comparison prevents that drop from being treated as better predictive performance.

| Era | Variable | Hours per city | Nulls per city | Null % |
| --- | --- | --- | --- | --- |
| old | boundary_layer_height_m | 43819 | 0 | 0.00 |
| old | precipitation_mm | 43819 | 0 | 0.00 |
| old | relative_humidity | 43819 | 0 | 0.00 |
| old | solar_radiation_wm2 | 43819 | 0 | 0.00 |
| old | surface_pressure_hpa | 43819 | 0 | 0.00 |
| old | temperature_c | 43819 | 0 | 0.00 |
| old | total_cloud_cover | 43819 | 0 | 0.00 |
| old | wind_dir_deg | 43819 | 0 | 0.00 |
| old | wind_speed_ms | 43819 | 0 | 0.00 |
| recent | boundary_layer_height_m | 17544 | 4368 | 24.90 |
| recent | precipitation_mm | 17544 | 0 | 0.00 |
| recent | relative_humidity | 17544 | 0 | 0.00 |
| recent | solar_radiation_wm2 | 17544 | 0 | 0.00 |
| recent | surface_pressure_hpa | 17544 | 0 | 0.00 |
| recent | temperature_c | 17544 | 0 | 0.00 |
| recent | total_cloud_cover | 17544 | 0 | 0.00 |
| recent | wind_dir_deg | 17544 | 0 | 0.00 |
| recent | wind_speed_ms | 17544 | 0 | 0.00 |

Across the complete cached weather window, including years outside the model eras, null counts are shown separately below. The final provider weather day has nulls in every variable and is outside PM model targets. The first five IST hours of 2015 precede the source's UTC start and have no weather row; absent rows are distinct from null-valued rows. The full per-city weather audit is retained in full_weather_nulls.csv.

| Variable | Stored source hours all cities | Null values | Null % |
| --- | --- | --- | --- |
| boundary_layer_height_m | 1236672 | 52704 | 4.262 |
| precipitation_mm | 1236672 | 288 | 0.023 |
| relative_humidity | 1236672 | 288 | 0.023 |
| solar_radiation_wm2 | 1236672 | 288 | 0.023 |
| surface_pressure_hpa | 1236672 | 288 | 0.023 |
| temperature_c | 1236672 | 288 | 0.023 |
| total_cloud_cover | 1236672 | 288 | 0.023 |
| wind_dir_deg | 1236672 | 288 | 0.023 |
| wind_speed_ms | 1236672 | 288 | 0.023 |

For cross-period normalisation, both eras use the identical joint sample of 300 donor rows from complete observed 2015-2019 plus 2024-2025 weather/calendar features. Period and within-era trend are held fixed; a trend resets at the era boundary and does not bridge 2020-2023. Separate-era forests use the same pooled donors. A no-trend model can produce a constant normalised level within an era because all remaining inputs are resampled; that is reported rather than hidden. Reference distribution weights available hourly/daily rows, not eras equally. No model predictions are generated in the concentration gap.

### Final readiness

R2 below for (b) is daily OOF within each era and drives readiness with bias/support criteria. (a) and (c) are the selected model's native target resolution; daily-target models use random days, so the required random-hour comparison remains in D4. Transfer directions report each destination era separately. Bias is prediction minus observation; NMB is 100 sum(error)/sum(observation).

| City | Design | a native R2 | b daily R2 old/recent | c native R2 old-to-recent/recent-to-old | NMB % old/recent | Worst month abs NMB % | Ready | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | hourly_trend_pooled_blh | 0.622 | 0.372/unavailable | unavailable/unavailable | 3.34/unavailable | 54.56 | FAIL | old: daily R2, monthly NMB |
| bengaluru | daily_trend_separate_no_blh | 0.557 | 0.350/0.660 | -0.100/0.181 | 0.20/0.25 | 7.47 | FAIL | old: daily R2 |
| chennai | daily_trend_pooled_no_blh | 0.457 | 0.267/0.499 | -2.123/-0.368 | -0.11/2.37 | 10.97 | FAIL | old: daily R2; recent: daily R2 |
| delhi | hourly_trend_separate_no_blh | 0.823 | 0.660/0.761 | 0.418/0.485 | 0.78/-0.87 | 13.06 | PASS |  |
| hyderabad | daily_trend_separate_no_blh | 0.805 | 0.517/0.690 | -5.553/0.092 | 0.40/-0.03 | 15.26 | PASS |  |
| jaipur | daily_trend_pooled_no_blh | 0.566 | 0.405/unavailable | unavailable/unavailable | -0.09/unavailable | 12.40 | FAIL | old: daily R2 |
| kanpur | daily_trend_pooled_no_blh | 0.701 | 0.638/unavailable | unavailable/unavailable | -0.57/unavailable | 17.73 | PASS |  |
| kolkata | daily_trend_separate_no_blh | 0.864 | 0.753/0.807 | -12.270/0.360 | 0.85/0.61 | 94.53 | FAIL | old: monthly NMB |
| lucknow | hourly_trend_pooled_blh | 0.716 | 0.655/unavailable | unavailable/unavailable | 1.41/unavailable | 9.43 | PASS |  |
| mumbai | hourly_trend_separate_no_blh | 0.641 | 0.602/0.760 | -0.056/0.189 | 0.40/0.78 | 6.84 | PASS |  |
| patna | daily_trend_pooled_no_blh | 0.797 | 0.757/unavailable | unavailable/unavailable | 0.22/unavailable | 22.20 | FAIL | old: monthly NMB |
| pune | daily_trend_separate_no_blh | 0.871 | unavailable/0.841 | unavailable/unavailable | unavailable/0.70 | 4.52 | PASS |  |

Detailed R2, RMSE, mean bias, NMB, weeks and monthly counts are retained in each city model JSON and residual CSVs, including fixed-panel readiness separately. A passed all-station screen does not certify a fixed-panel model automatically.

### D6: residual seasonality

| City | Era | Worst month | OOF days | Mean bias ug/m3 | NMB % |
| --- | --- | --- | --- | --- | --- |
| ahmedabad | old | 9 | 50 | 17.245 | 54.56 |
| bengaluru | old | 7 | 130 | 1.544 | 7.47 |
| bengaluru | recent | 3 | 62 | -2.778 | -6.50 |
| chennai | old | 8 | 124 | 2.962 | 9.59 |
| chennai | recent | 4 | 60 | 2.140 | 10.97 |
| delhi | old | 3 | 152 | 6.691 | 7.31 |
| delhi | recent | 10 | 62 | -14.385 | -13.06 |
| hyderabad | old | 7 | 117 | -3.455 | -15.26 |
| hyderabad | recent | 12 | 62 | 1.982 | 4.77 |
| jaipur | old | 3 | 62 | 5.465 | 12.40 |
| kanpur | old | 5 | 103 | -18.129 | -17.73 |
| kolkata | old | 9 | 30 | 15.281 | 94.53 |
| kolkata | recent | 5 | 62 | 3.448 | 14.77 |
| lucknow | old | 6 | 128 | 7.809 | 9.43 |
| mumbai | old | 6 | 107 | 1.505 | 6.11 |
| mumbai | recent | 8 | 62 | 0.998 | 6.84 |
| patna | old | 7 | 62 | 8.480 | 22.20 |
| pune | recent | 8 | 62 | 0.756 | 4.52 |

| City | Era | Season | OOF days | Mean bias ug/m3 | NMB % |
| --- | --- | --- | --- | --- | --- |
| ahmedabad | old | monsoon | 222 | 5.009 | 11.45 |
| ahmedabad | old | post_monsoon | 118 | 1.666 | 1.99 |
| ahmedabad | old | pre_monsoon | 153 | 1.537 | 2.06 |
| ahmedabad | old | winter | 162 | -0.373 | -0.45 |
| bengaluru | old | monsoon | 555 | 0.980 | 4.18 |
| bengaluru | old | post_monsoon | 300 | -0.173 | -0.45 |
| bengaluru | old | pre_monsoon | 412 | -0.185 | -0.44 |
| bengaluru | old | winter | 376 | -0.781 | -1.63 |
| bengaluru | recent | monsoon | 244 | 0.487 | 2.39 |
| bengaluru | recent | post_monsoon | 122 | -0.715 | -2.18 |
| bengaluru | recent | pre_monsoon | 184 | -0.105 | -0.31 |
| bengaluru | recent | winter | 181 | 0.238 | 0.59 |
| chennai | old | monsoon | 471 | 0.889 | 2.22 |
| chennai | old | post_monsoon | 238 | -2.480 | -4.86 |
| chennai | old | pre_monsoon | 368 | -1.394 | -2.71 |
| chennai | old | winter | 340 | 1.781 | 3.14 |
| chennai | recent | monsoon | 244 | 0.483 | 2.45 |
| chennai | recent | post_monsoon | 122 | -0.589 | -1.83 |
| chennai | recent | pre_monsoon | 184 | 1.141 | 5.25 |
| chennai | recent | winter | 181 | 1.227 | 3.00 |
| delhi | old | monsoon | 608 | 0.844 | 1.49 |
| delhi | old | post_monsoon | 305 | -1.273 | -0.70 |
| delhi | old | pre_monsoon | 457 | 3.128 | 3.30 |
| delhi | old | winter | 442 | 0.261 | 0.14 |
| delhi | recent | monsoon | 244 | 1.720 | 4.40 |
| delhi | recent | post_monsoon | 122 | -13.171 | -7.72 |
| delhi | recent | pre_monsoon | 184 | 1.237 | 1.64 |
| delhi | recent | winter | 181 | 1.770 | 1.10 |
| hyderabad | old | monsoon | 471 | -0.480 | -2.05 |
| hyderabad | old | post_monsoon | 232 | 1.280 | 2.40 |
| hyderabad | old | pre_monsoon | 365 | 1.336 | 2.88 |
| hyderabad | old | winter | 352 | -0.848 | -1.23 |
| hyderabad | recent | monsoon | 244 | 0.279 | 1.09 |
| hyderabad | recent | post_monsoon | 122 | -1.282 | -3.26 |
| hyderabad | recent | pre_monsoon | 184 | 0.005 | 0.02 |
| hyderabad | recent | winter | 181 | 0.444 | 1.11 |
| jaipur | old | monsoon | 244 | 0.936 | 2.22 |
| jaipur | old | post_monsoon | 122 | -5.385 | -8.05 |
| jaipur | old | pre_monsoon | 184 | 1.704 | 3.21 |
| jaipur | old | winter | 180 | 0.438 | 0.66 |
| kanpur | old | monsoon | 458 | 4.398 | 8.94 |
| kanpur | old | post_monsoon | 186 | -12.729 | -7.06 |
| kanpur | old | pre_monsoon | 315 | -2.463 | -2.49 |
| kanpur | old | winter | 328 | 0.733 | 0.35 |
| kolkata | old | monsoon | 122 | 4.271 | 17.29 |
| kolkata | old | post_monsoon | 61 | 2.283 | 3.16 |
| kolkata | old | pre_monsoon | 92 | -0.256 | -0.49 |
| kolkata | old | winter | 90 | -4.713 | -3.35 |
| kolkata | recent | monsoon | 244 | 0.788 | 3.76 |
| kolkata | recent | post_monsoon | 122 | -1.055 | -1.81 |
| kolkata | recent | pre_monsoon | 184 | 0.709 | 2.06 |
| kolkata | recent | winter | 181 | 0.039 | 0.05 |
| lucknow | old | monsoon | 575 | 2.368 | 4.46 |
| lucknow | old | post_monsoon | 304 | -3.613 | -2.15 |
| lucknow | old | pre_monsoon | 420 | 2.720 | 2.67 |
| lucknow | old | winter | 352 | 3.548 | 1.94 |
| mumbai | old | monsoon | 462 | 0.188 | 0.79 |
| mumbai | old | post_monsoon | 234 | 1.436 | 2.63 |
| mumbai | old | pre_monsoon | 358 | 0.162 | 0.45 |
| mumbai | old | winter | 325 | -0.776 | -1.19 |
| mumbai | recent | monsoon | 244 | 0.395 | 2.47 |
| mumbai | recent | post_monsoon | 122 | -1.281 | -2.67 |
| mumbai | recent | pre_monsoon | 184 | 1.370 | 4.51 |
| mumbai | recent | winter | 181 | 0.013 | 0.02 |
| patna | old | monsoon | 235 | 2.299 | 4.85 |
| patna | old | post_monsoon | 115 | -4.715 | -2.97 |
| patna | old | pre_monsoon | 181 | 0.731 | 0.92 |
| patna | old | winter | 168 | 0.256 | 0.12 |
| pune | recent | monsoon | 244 | 0.447 | 2.46 |
| pune | recent | post_monsoon | 122 | 1.806 | 3.80 |
| pune | recent | pre_monsoon | 184 | 0.188 | 0.51 |
| pune | recent | winter | 181 | -0.913 | -1.45 |

Every city has calendar-month, individual-year-month and season residual CSVs and a residual figure. The frozen monthly gate is checked by month of year within each era; individual year-month tables disclose shorter-lived bias rather than pooling it out of sight. No post-result model tuning was done to erase these failures.

### D7: Hyderabad sanity check

The six-station fixed panel has 365 valid 2025 days, mean 37.805 ug/m3, maximum 77.687 ug/m3 and 53 days above 60. The full network's zero versus the fixed panel's exceedances demonstrates that station composition changes the conclusion. This is a comparison of two aggregation panels, not evidence that every part of the city stays below 60. The source's rounded/limited values remain a separate concern.

Corrected 2025 city series: **365** valid days, daily maximum **53.031 ug/m3**, annual mean **35.021 ug/m3**, **0** days above 60, **365** above 15. This is the equally weighted city daily mean, not the maximum station/hour/quarter. The network includes 14 recent station records, with 6 shared physical stations across eras.

| Station | Raw quarter max | Repeats at max | Integer % | Longest equal quarter run | Daily max after QA | Station days above 60 | Unit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| site_5597 | 147.55 | 3 | 1.1 | 87 | 68.04 | 2 | µg/m³ |
| site_5596 | 545.86 | 3 | 1.1 | 108 | 61.04 | 1 | µg/m³ |
| site_5598 | 628.68 | 1 | 0.9 | 23 | 96.57 | 37 | µg/m³ |
| site_262 | 87.00 | 22 | 100.0 | 20 | 74.16 | 9 | µg/m³ |
| site_5600 | 263.23 | 1 | 0.9 | 4 | 146.81 | 1 | µg/m³ |
| site_5595 | 389.67 | 3 | 1.1 | 19 | 60.22 | 1 | µg/m³ |
| site_5602 | 433.09 | 1 | 1.0 | 3 | 55.18 | 0 | µg/m³ |
| site_294 | 745.00 | 5 | 99.6 | 137 | 136.66 | 29 | µg/m³ |
| site_199 | 88.00 | 14 | 100.0 | 43 | 70.04 | 8 | µg/m³ |
| site_251 | 87.00 | 349 | 100.0 | 16 | 80.27 | 97 | µg/m³ |
| site_298 | 87.00 | 541 | 100.0 | 34 | 82.31 | 131 | µg/m³ |
| site_275 | 87.00 | 274 | 100.0 | 16 | 81.50 | 62 | µg/m³ |
| site_5604 | 134.42 | 1 | 1.0 | 3 | 58.83 | 0 | µg/m³ |
| site_5599 | 52.18 | 1 | 0.9 | 3 | 39.00 | 0 | µg/m³ |

The units are concentration units in the column headers, not AQI. Raw quarter maxima and repeated values are reported before quality screening; station daily maxima use the unchanged quality rules. Shared legacy stations' rounded/limited ranges and long repeated runs are a source-quality concern. The cached inputs establish that these values were published; they do not prove instrument accuracy or rule out publisher/instrument capping. No undocumented inverse conversion or fabricated uncapping is applied. Zero city-average exceedance days is reproducible in this source snapshot, with the station composition and averaging distinction above; it is not independently validated as a citywide exposure claim.

Additional independent checks reproduce first-week 2024 hourly values at four legacy Hyderabad stations (103-167 matched hours, rounding-level differences); no rows were returned for the fifth station in that window. The public mirror returned no January 2025 rows for these sites, so this does not independently certify their 2025 measurements. The paired CSVs and coverage limitations are preserved in hyderabad_independent.json.

### Updated old/recent differences

Normalised series are retained for every city as diagnostic outputs. Where a screen fails, their differences and intervals do not qualify that city or period for Phase 3B use. The fixed-panel gate is separate from the all-station gate.

Values are equally weighted annual means over each series' eligible observed years; differences are recent minus old. Raw intervals use 500 year-and-seven-calendar-day block resamples. Normalised intervals use the frozen conditional construction: normalised daily values plus centred week-CV residuals, then the same resampling. They exclude forest-refit/parameter, donor-weather and station-network uncertainty and must not be interpreted as complete confidence intervals or causal effects. The normalised point estimate is the pure common-reference forest mean. The fixed panel is fitted separately using the selected structure and the same reference donors.

| City | Series | Old mean | Recent mean | Difference ug/m3 | Bootstrap 95% interval |
| --- | --- | --- | --- | --- | --- |
| bengaluru | all_raw | 36.502 | 30.833 | -5.668 | [-11.223, -0.746] |
| bengaluru | all_normalised | 36.815 | 31.344 | -5.472 | [-8.812, -1.997] |
| bengaluru | panel_raw | 40.811 | 28.275 | -12.535 | [-23.185, -4.326] |
| bengaluru | panel_normalised | 39.899 | 28.915 | -10.984 | [-17.211, -5.800] |
| chennai | all_raw | 48.952 | 27.552 | -21.399 | [-27.913, -13.980] |
| chennai | all_normalised | 48.236 | 28.375 | -19.861 | [-24.279, -15.112] |
| chennai | panel_raw | 48.952 | 29.938 | -19.013 | [-23.666, -14.027] |
| chennai | panel_normalised | 48.218 | 30.786 | -17.433 | [-20.306, -14.197] |
| delhi | all_raw | 117.788 | 100.333 | -17.455 | [-35.584, 1.780] |
| delhi | all_normalised | 120.752 | 103.484 | -17.268 | [-30.176, -3.500] |
| delhi | panel_raw | 117.788 | 100.886 | -16.902 | [-35.113, 2.287] |
| delhi | panel_normalised | 120.752 | 103.981 | -16.771 | [-29.548, -3.239] |
| hyderabad | all_raw | 45.555 | 33.271 | -12.284 | [-17.742, -6.967] |
| hyderabad | all_normalised | 45.606 | 33.645 | -11.962 | [-17.903, -7.589] |
| hyderabad | panel_raw | 45.555 | 35.811 | -9.743 | [-15.961, -3.430] |
| hyderabad | panel_normalised | 45.606 | 36.303 | -9.304 | [-15.230, -4.847] |
| kolkata | all_raw | 68.299 | 44.951 | -23.348 | [-39.058, -8.097] |
| kolkata | all_normalised | 69.592 | 45.222 | -24.370 | [-34.908, -14.483] |
| kolkata | panel_raw | 68.299 | 44.951 | -23.348 | [-39.058, -8.097] |
| kolkata | panel_normalised | 69.592 | 45.222 | -24.370 | [-34.908, -14.483] |
| mumbai | all_raw | 41.911 | 34.198 | -7.713 | [-14.983, 0.625] |
| mumbai | all_normalised | 43.234 | 35.425 | -7.808 | [-13.931, -1.275] |

| City | Fixed-panel old/recent OOF R2 | Fixed-panel passes |
| --- | --- | --- |
| bengaluru | 0.525/0.664 | PASS |
| chennai | 0.264/0.361 | FAIL |
| delhi | 0.660/0.759 | PASS |
| hyderabad | 0.517/0.715 | PASS |
| kolkata | 0.753/0.807 | FAIL |

### What was wrong and what remains limited

Confirmed corrections: recent publisher clocks were mislabelled UTC; literal UTC quarter means cannot be relabelled to IST bins; terminal chronological extrapolation was used as a normalisation-readiness test; an absolute trend encoded the unobserved gap; BLH missingness removed January-June 2024; provider-specific station IDs hid common physical panels. The new method uses verified physical clocks, within-era week CV, explicit periods, shared pooled reference weather, complete-case disclosure and matched CPCB panels. A failed criterion remains a failure. Remaining limitations include coarse city weather, district/metropolitan mismatch, network composition, source rounding/repeats, incomplete early-era coverage, lack of untouched selection testing and conditional rather than full model uncertainty.

Cities passing the all-station normalisation screen: **delhi, hyderabad, kanpur, lucknow, mumbai, pune**. Only their observed eligible periods are candidates for Phase 3B; old/recent questions additionally require both eras and an adequate fixed panel. No Phase 3B research question has been started.

### Figures and audit artifacts

Corrected data figures/CSVs: `data/results/6/`. Model comparisons, readiness JSON, fitted forests, residual tables and bootstrap differences: `data/results/7/`. Figure exports include standalone SVG and PNG, backed by the actual CSV/JSON. Every local result artifact is hashed in its manifest.

[Model comparison](../../data/results/7/diagnostics/model_structure_comparison.svg), [validation comparison](../../data/results/7/diagnostics/validation_design_comparison.svg), [station weather points](../../data/results/7/diagnostics/station_weather_points.svg), [station network](../../data/results/7/diagnostics/station_network_years.svg), [Hyderabad](../../data/results/7/diagnostics/hyderabad_sanity.svg).

- ahmedabad: [diurnal alignment](../../data/results/6/ahmedabad_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/ahmedabad_residuals.svg), [normalisation](../../data/results/7/diagnostics/ahmedabad_normalisation.svg).

- bengaluru: [diurnal alignment](../../data/results/6/bengaluru_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/bengaluru_residuals.svg), [normalisation](../../data/results/7/diagnostics/bengaluru_normalisation.svg).

- chennai: [diurnal alignment](../../data/results/6/chennai_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/chennai_residuals.svg), [normalisation](../../data/results/7/diagnostics/chennai_normalisation.svg).

- delhi: [diurnal alignment](../../data/results/6/delhi_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/delhi_residuals.svg), [normalisation](../../data/results/7/diagnostics/delhi_normalisation.svg).

- hyderabad: [diurnal alignment](../../data/results/6/hyderabad_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/hyderabad_residuals.svg), [normalisation](../../data/results/7/diagnostics/hyderabad_normalisation.svg).

- jaipur: [diurnal alignment](../../data/results/6/jaipur_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/jaipur_residuals.svg), [normalisation](../../data/results/7/diagnostics/jaipur_normalisation.svg).

- kanpur: [diurnal alignment](../../data/results/6/kanpur_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/kanpur_residuals.svg), [normalisation](../../data/results/7/diagnostics/kanpur_normalisation.svg).

- kolkata: [diurnal alignment](../../data/results/6/kolkata_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/kolkata_residuals.svg), [normalisation](../../data/results/7/diagnostics/kolkata_normalisation.svg).

- lucknow: [diurnal alignment](../../data/results/6/lucknow_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/lucknow_residuals.svg), [normalisation](../../data/results/7/diagnostics/lucknow_normalisation.svg).

- mumbai: [diurnal alignment](../../data/results/6/mumbai_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/mumbai_residuals.svg), [normalisation](../../data/results/7/diagnostics/mumbai_normalisation.svg).

- patna: [diurnal alignment](../../data/results/6/patna_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/patna_residuals.svg), [normalisation](../../data/results/7/diagnostics/patna_normalisation.svg).

- pune: [diurnal alignment](../../data/results/6/pune_alignment_diurnal.svg), [residuals](../../data/results/7/diagnostics/pune_residuals.svg), [normalisation](../../data/results/7/diagnostics/pune_normalisation.svg).


Warehouse measurement/provenance fingerprint remained unchanged: `{'rows': 16266240, 'order_independent_record_hash': 695864490642684660}`.

### Execution verification

Full container suite: **117 passed, 1 warning in 30.49s**. All original 14 test
files retain their pre-task SHA256. Ruff check and format passed (147 files);
Django checks/migration detection passed, production deploy check had no issues,
and schema validation completed. Health and the live analytics APIs returned
200, with latest run 7 and explicit legacy run 2 both working. Measurement count
and hash, frozen protocol bytes and absence of gap/future predictions were checked.
All result-manifest hashes/file lists were validated. Seeded reference-weather
hashes are recorded in `pooled_reference_audit.json`. Exact stdout is archived in
`data/results/7/verification/`; see [VALIDATION.md](../VALIDATION.md) for failures
and rechecks. The known netCDF4/NumPy warning remains visible.

All-station candidate periods follow the readiness table. Bengaluru's seven-site
fixed panel additionally passes both eras; its all-station old model remains a
failure. Mumbai has no eligible matched panel in both eras. No threshold was
changed to make these distinctions, and no Phase 3B question was investigated.
