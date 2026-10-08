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
[Huang et al. EPA HERO record](https://hero.epa.gov/reference/7696632/) reports
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

## Actual diagnostics/results

No new model scores were inspected at the protocol freeze. During diagnostics,
independent same-site XKDR hourly records demonstrated that the seven recent
OpenCity exports retain IST wall-clock values under `+0000` labels. See
[the clock proof](PHASE3A2_CLOCK_PROOF.json): 93-168 matched hours per city,
maximum difference 0.005 ug/m3 from independent-source rounding. This evidence,
rather than model performance, determines the -5.5 hour conversion in derived
analysis timestamps. Raw files and warehouse rows remain unchanged. The literal
UTC interpretation is preserved in diagnostic run 4; provisional model run 5
was interrupted and marked failed before final results. Readiness criteria and
the prespecified variant list remain unchanged. Corrected results follow after
the run completes.
