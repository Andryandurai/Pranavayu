# Phase 4 forecasting protocol

Frozen before any Phase 4 fitting or evaluation. Baseline: AnalysisRun 19 and
125 passing tests. This protocol is versioned before launching the fit process.

Use raw quality-OK equal-station hourly concentrations in the canonical UTC
clock, aggregated in IST with at least 18 hourly bins per day. Bengaluru uses
Run 8's seven-site fixed panel; other cities use their all-station series. Only
2024–2025 concentrations enter training. Hyderabad, Mumbai and Bengaluru are
primary; Delhi, Pune, Chennai and Kolkata are secondary. Other cities lack recent
targets and are excluded. No normalised concentration is a predictor.

Forecasts are issued at the end of IST day t for daily means on t+1, t+2 and t+3.
Lag/rolling/night predictors end at t. Night means use 00:00–05:59 and
20:00–23:59 of t; the daily max uses t only. Calendar covariates are known dates,
not future measurements. Holidays use the pinned India calendar library; Diwali
uses the previously verified government dates.

Open-Meteo's Historical Forecast API is a stitched near-valid-time series, not
an issue-vintage archive. It is fetched as a source diagnostic but never used
as target-day weather in headline fits. Use the related Previous Runs API,
explicit GFS Global, UTC, m/s, offsets h+1 days for horizon h. Each hourly record
has a conservative availability bound valid_time − (h+1)*24h + 12h; require the
entire target day's bounds to precede issue-end. The API supplies lead-offset
semantics, not actual historical publication logs. The 12-hour allowance is an
assumption exceeding documented typical global compute latency (4–6 hours);
late provider outages are not reconstructible. Different target hours can use
different older model runs. Do not invent exact initialisation/publication times.
Persist bound semantics, lead, source, input hash and ingestion run. BLH is
omitted if the actual lead-offset archive is null. Never replace missing lead
weather with stitched or observed weather. Perfect-prognosis uses observed
target weather separately, explicitly labelled retrospective upper bound.

Evaluate the last six calendar months ending at each city's latest observed
day. Partition by issue calendar month; refit at each month's first scored
issue date, expanding from 2024. Train labels must be available by this date.
Each training window reserves the latest 60 calendar days for calibration and
the preceding 60 for tuning. Purge rows whose target reaches the next segment's
first issue date. Fit scalers, imputers and all model choices on training only.
Use common valid targets across models; export every issue/target and split.
Missing targets/lags remain missing, and omitted days/counts are reported.

Compare persistence, seven-day mean, training-only target-month climatology,
direct-horizon SARIMAX with lag/calendar/forecast exogenous predictors,
LightGBM point and quantile, and a small PyTorch LSTM. SARIMAX orders (1,0,0)
and (1,0,1); LightGBM leaf/depth/leaf-minimum pairs (7,3,20), (15,4,30), fixed
200 trees, learning rate 0.04, regularisation 1. LSTM: preceding seven actual
days' PM, 16 hidden units, dropout 0.2, weight decay 0.01, 80 full-batch epochs,
learning rate 0.01, training-only scaling. Keep LSTM as a selectable candidate
only when its tuning RMSE strictly beats the tuned LightGBM. Pick the issued
algorithm by tuning RMSE including baselines, without looking at outer scores.
Fit 0.025/0.10/0.90/0.975 LightGBM quantiles using the selected tree structure;
report their calibrated intervals alongside the selected algorithm's absolute
residual split-conformal intervals. Do not refit on calibration labels.

SARIMAX removes constant/linearly dependent exogenous columns by training-only
pivoted QR (relative diagonal tolerance 1e-10); the three-day mean is exactly
redundant with its PM lags. Optimisation uses the fixed 75-iteration limit;
convergence flags are retained rather than hiding warnings.

Seed 20261010, one thread per model. Intervals use the finite-sample higher
order statistic ceil((n+1)*(1−alpha)), with nonnegative bounds. Coverage is
empirical, with no exchangeability guarantee for dependent seasonal series.
SHAP top five drivers/feature values are stored for each issued forecast;
tree SHAP for forests, deterministic permutation SHAP for other algorithms.

RMSE skill = 1 − RMSE_model/RMSE_persistence on paired days. Report MAE, category
accuracy, NMB, month/season bias and >60 µg/m³ POD/FAR/CSI with event counts;
undefined zero-denominator scores are null. DM uses squared losses, calendar-day
Bartlett HAC through max(7,h−1), Harvey finite-sample correction and two-sided
t p-values; nominal p-values are not corrected for multiple comparisons and
compare forecast sequences rather than proving algorithm superiority.

CAMS is eligible only with retrievable 2025 issue vintages. A historical
valid-time PM2.5 response alone is insufficient. Otherwise report the archived
vintage limitation and skip the benchmark rather than relabel hindcasts.

Replay can run without credentials. Live mode requires an OpenAQ key and fresh
quality-OK PM on the current completed day; fetched historical readings do not
prove their original publication availability. Retrospective evaluation assumes
day-t readings were available at issue-end and states this limitation. Replay
latest-day predictions after the concentration archive ends are unscored.

References: [archive semantics](https://open-meteo.com/en/docs/historical-forecast-api),
[lead offsets](https://open-meteo.com/en/docs/previous-runs-api),
[run/publication distinction](https://open-meteo.com/en/docs/single-runs-api),
[conformal methods](https://arxiv.org/abs/2107.07511),
[DM/HLN implementation](https://github.com/bank-of-england/forecast_evaluation/blob/main/src/forecast_evaluation/tests/diebold_mariano.py),
[CPCB AQI report](https://www.cpcb.gov.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvRklOQUwtUkVQT1JUX0FRSV8ucGRm).
