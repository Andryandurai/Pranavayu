# Phase 4: daily PM2.5 forecasting

AnalysisRun **21**. Primary cities: Hyderabad, Mumbai and Bengaluru's
seven-site fixed panel. Secondary: Delhi, Pune, Chennai and Kolkata. No RAG,
simulator or dashboard is built. Kanpur, Lucknow, Ahmedabad, Jaipur and Patna
are excluded because their concentration archive has no recent targets.

## Data and leakage rules

Raw 2024–2025 concentration inputs come from canonical Run 8, with equal-station
hourly means and at least 18 IST hours for each daily target. Fixed-panel inputs
are raw measurements, not deweathered values. Hashes are in input_provenance.json.

Forecasts target t+1/t+2/t+3 at end-of-day t IST. PM lags, rolling means and
night/day summaries stop at t. Calendar features are known dates. Target weather
uses explicit GFS Global lead offsets from Open-Meteo's Previous Runs archive;
the requested Historical Forecast endpoint was probed and excluded from headline
features because it stitches near-valid-time forecasts. Offsets are h+1 days
with a 12-hour publication allowance. The bound is tested against issue-end.
Exact historical run/publication logs are unavailable: these bounds rely on the
documented lead semantics and a latency assumption. Provider outages cannot be
reconstructed. Historical concentration publication times are also unavailable;
the backtest assumes day-t observations were available at issue-end.

BLH is excluded because lead-offset archive values are null; it is never filled
from the stitched series or ERA5. Wind direction uses sine/cosine, precipitation
is a daily sum, cloud cover a fraction and wind speed m/s. Hourly UTC forecast
points are assigned to native IST dates; overlapping download windows retain
complete days across the half-hour timezone boundary.
Hourly accumulated rain assigned by its UTC valid-time midpoint approximates
the IST-day boundary within half an hour; it is a weather predictor, not a
claimed exact station precipitation integral.

## Archived forecast coverage

| City | Horizon | First target | Last target | 2024–25 days | Jul–Dec 2025 days / 184 | BLH days |
| --- | --- | --- | --- | --- | --- | --- |
| hyderabad | 1 | 2024-01-21 | 2025-12-31 | 711 | 184 | 0 |
| hyderabad | 2 | 2024-01-22 | 2025-12-31 | 710 | 184 | 0 |
| hyderabad | 3 | 2024-01-23 | 2025-12-31 | 709 | 184 | 0 |
| mumbai | 1 | 2024-01-21 | 2025-12-31 | 711 | 184 | 0 |
| mumbai | 2 | 2024-01-22 | 2025-12-31 | 710 | 184 | 0 |
| mumbai | 3 | 2024-01-23 | 2025-12-31 | 709 | 184 | 0 |
| bengaluru | 1 | 2024-01-21 | 2025-12-31 | 711 | 184 | 0 |
| bengaluru | 2 | 2024-01-22 | 2025-12-31 | 710 | 184 | 0 |
| bengaluru | 3 | 2024-01-23 | 2025-12-31 | 709 | 184 | 0 |
| delhi | 1 | 2024-01-21 | 2025-12-31 | 711 | 184 | 0 |
| delhi | 2 | 2024-01-22 | 2025-12-31 | 710 | 184 | 0 |
| delhi | 3 | 2024-01-23 | 2025-12-31 | 709 | 184 | 0 |
| pune | 1 | 2024-01-21 | 2025-12-31 | 711 | 184 | 0 |
| pune | 2 | 2024-01-22 | 2025-12-31 | 710 | 184 | 0 |
| pune | 3 | 2024-01-23 | 2025-12-31 | 709 | 184 | 0 |
| chennai | 1 | 2024-01-21 | 2025-12-31 | 711 | 184 | 0 |
| chennai | 2 | 2024-01-22 | 2025-12-31 | 710 | 184 | 0 |
| chennai | 3 | 2024-01-23 | 2025-12-31 | 709 | 184 | 0 |
| kolkata | 1 | 2024-01-21 | 2025-12-31 | 711 | 184 | 0 |
| kolkata | 2 | 2024-01-22 | 2025-12-31 | 710 | 184 | 0 |
| kolkata | 3 | 2024-01-23 | 2025-12-31 | 709 | 184 | 0 |

Coverage counts require all 24 weather hours and non-null required variables.
They are separate from usable PM/lag target support. Raw assets preserve original
responses, download URL, SHA256, lead settings, licence and IngestionRun links.

## Evaluation design

The frozen [protocol](PHASE4_PROTOCOL.md) specifies expanding monthly origins,
a purged 60-day tuning segment and a separate latest 60-day calibration segment.
Only training-window tuning selects parameters and the algorithm. Scalers,
imputers and holiday/lag inputs are audited. SARIMAX filters only labels whose
target date has arrived by t; future target labels are masked. No shuffle occurs.
The latest six target calendar months are evaluated on common real/ideal support.
Monthly origins and omitted support are in split_audit.json and input_provenance.json.

Point models are persistence, seven-day mean, training-month climatology, direct-
horizon exogenous SARIMAX, LightGBM and a small regularised PyTorch LSTM. LSTM
is selectable only if tuning RMSE beats LightGBM. Diagnostic LSTM scores remain
visible when rejected. Quantile LightGBM is evaluated separately for intervals.
The issued policy may change its algorithm monthly; the evaluation itself never
selects a model from held-out scores. RMSE skill is 1−RMSE/RMSE_persistence.

## Model comparisons

RMSE in µg/m³; `policy` is the training-selected issued prediction. A model with
negative skill loses to persistence. The complete MAE, category accuracy, bias,
event counts and DM scores for every model are in model_comparison.csv.

| City | Horizon | n | Persistence | Mean7 | Climatology | SARIMAX | LightGBM | LSTM diagnostic | Policy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bengaluru | 1 | 184 | 5.747 | 8.123 | 9.933 | 5.646 | 6.339 | 5.992 | 5.945 |
| bengaluru | 2 | 184 | 8.484 | 8.777 | 9.933 | 8.083 | 6.808 | 7.218 | 7.870 |
| bengaluru | 3 | 184 | 9.814 | 9.044 | 9.933 | 8.620 | 7.034 | 7.194 | 9.971 |
| chennai | 1 | 184 | 11.444 | 13.793 | 17.423 | 10.089 | 10.869 | 10.652 | 12.353 |
| chennai | 2 | 184 | 15.635 | 14.766 | 17.423 | 12.901 | 13.594 | 13.461 | 14.820 |
| chennai | 3 | 184 | 17.823 | 15.104 | 17.423 | 15.091 | 14.464 | 15.285 | 13.302 |
| delhi | 1 | 184 | 33.668 | 40.755 | 48.917 | 30.110 | 34.249 | 29.248 | 29.417 |
| delhi | 2 | 184 | 47.760 | 44.146 | 48.917 | 41.350 | 42.398 | 39.190 | 43.858 |
| delhi | 3 | 184 | 53.316 | 45.737 | 48.917 | 44.684 | 41.070 | 40.791 | 44.841 |
| hyderabad | 1 | 184 | 3.828 | 5.631 | 8.045 | 3.475 | 4.083 | 4.170 | 3.656 |
| hyderabad | 2 | 184 | 5.650 | 6.174 | 8.045 | 4.953 | 5.911 | 5.160 | 5.122 |
| hyderabad | 3 | 184 | 6.902 | 6.531 | 8.045 | 5.634 | 7.015 | 5.621 | 5.634 |
| kolkata | 1 | 184 | 10.174 | 14.634 | 17.898 | 9.417 | 10.333 | 10.140 | 10.159 |
| kolkata | 2 | 184 | 14.903 | 16.027 | 17.898 | 13.325 | 12.856 | 12.677 | 12.683 |
| kolkata | 3 | 184 | 17.150 | 16.842 | 17.898 | 14.967 | 13.759 | 12.808 | 15.456 |
| mumbai | 1 | 184 | 7.055 | 11.891 | 14.807 | 7.155 | 7.337 | 8.004 | 10.729 |
| mumbai | 2 | 184 | 11.030 | 13.325 | 14.807 | 10.483 | 9.745 | 10.129 | 12.802 |
| mumbai | 3 | 184 | 13.431 | 14.342 | 14.807 | 10.813 | 12.418 | 10.800 | 14.488 |
| pune | 1 | 184 | 7.991 | 11.688 | 20.421 | 7.115 | 10.901 | 9.053 | 10.414 |
| pune | 2 | 184 | 11.479 | 13.016 | 20.421 | 11.032 | 13.600 | 11.065 | 13.616 |
| pune | 3 | 184 | 12.987 | 13.939 | 20.421 | 12.459 | 14.355 | 11.925 | 14.468 |

## Issued-policy skill and statistical comparison

DM compares paired squared-loss forecast sequences using calendar-day Bartlett
HAC through max(7,h−1), the Harvey small-sample correction and a two-sided t test.
P-values are nominal; dependence, model selection and multiple comparisons limit
inference. A significant p-value can favour persistence when skill is negative.

| City | Horizon | RMSE | MAE | Skill | DM p | Category accuracy | Monthly chosen algorithms (days) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bengaluru | 1 | 5.945 | 4.295 | -0.035 | 0.33848 | 0.902 | lstm:62, persistence:60, lightgbm:31, sarimax:31 |
| bengaluru | 2 | 7.870 | 5.737 | 0.072 | 0.32316 | 0.842 | sarimax:94, mean7:31, lstm:30, persistence:29 |
| bengaluru | 3 | 9.971 | 7.096 | -0.016 | 0.80129 | 0.783 | mean7:61, sarimax:61, lstm:34, persistence:28 |
| chennai | 1 | 12.353 | 7.705 | -0.079 | 0.36847 | 0.761 | lightgbm:61, sarimax:32, persistence:31, mean7:30, lstm:30 |
| chennai | 2 | 14.820 | 8.811 | 0.052 | 0.67132 | 0.777 | lightgbm:94, lstm:90 |
| chennai | 3 | 13.302 | 9.137 | 0.254 | 0.13001 | 0.761 | lightgbm:92, lstm:62, persistence:30 |
| delhi | 1 | 29.417 | 18.686 | 0.126 | 0.02845 | 0.717 | lstm:153, lightgbm:31 |
| delhi | 2 | 43.858 | 26.555 | 0.082 | 0.22633 | 0.641 | lstm:94, mean7:59, lightgbm:31 |
| delhi | 3 | 44.841 | 26.360 | 0.159 | 0.06207 | 0.603 | lightgbm:65, lstm:61, mean7:58 |
| hyderabad | 1 | 3.656 | 2.869 | 0.045 | 0.42556 | 0.832 | sarimax:121, lightgbm:32, lstm:31 |
| hyderabad | 2 | 5.122 | 4.054 | 0.093 | 0.21570 | 0.783 | sarimax:121, lightgbm:33, lstm:30 |
| hyderabad | 3 | 5.634 | 4.361 | 0.184 | 0.01440 | 0.761 | sarimax:184 |
| kolkata | 1 | 10.159 | 6.884 | 0.002 | 0.98309 | 0.734 | lightgbm:154, lstm:30 |
| kolkata | 2 | 12.683 | 8.186 | 0.149 | 0.17810 | 0.750 | lstm:151, lightgbm:33 |
| kolkata | 3 | 15.456 | 10.327 | 0.099 | 0.42538 | 0.701 | lstm:123, climatology:31, lightgbm:30 |
| mumbai | 1 | 10.729 | 6.235 | -0.521 | 0.08969 | 0.837 | lightgbm:62, sarimax:31, mean7:31, lstm:30, persistence:30 |
| mumbai | 2 | 12.802 | 8.030 | -0.161 | 0.20692 | 0.815 | sarimax:62, mean7:61, persistence:59, lstm:2 |
| mumbai | 3 | 14.488 | 9.215 | -0.079 | 0.43973 | 0.772 | mean7:91, sarimax:31, lightgbm:31, persistence:28, lstm:3 |
| pune | 1 | 10.414 | 6.196 | -0.303 | 0.17637 | 0.832 | lightgbm:91, sarimax:63, persistence:30 |
| pune | 2 | 13.616 | 8.416 | -0.186 | 0.24650 | 0.793 | lightgbm:120, sarimax:64 |
| pune | 3 | 14.468 | 9.342 | -0.114 | 0.44528 | 0.788 | lightgbm:89, lstm:61, sarimax:34 |

Issued policies failing to beat persistence: bengaluru h1, bengaluru h3, chennai h1, mumbai h1, mumbai h2, mumbai h3, pune h1, pune h2, pune h3.

## CAMS benchmark

Actual CAMS Global archived lead-2/3/4 queries across the seven cities returned null evaluation-period forecasts. Historical valid-time PM2.5 exists, but it cannot replace issued forecasts in a benchmark.
The real historical PM2.5 sample is retained in the archive probes. It is not
converted into an issue-safe benchmark, and no CAMS skill number is fabricated.

## Detection of daily means above 60 µg/m³

Undefined scores have a zero denominator; zero events are not perfect detection.
These are city means, not station maxima or overall air-quality warnings.

| City | Horizon | Observed events | Hits | Misses | False alarms | POD | FAR | CSI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bengaluru | 1 | 2 | 0 | 2 | 2 | 0.000 | 1.000 | 0.000 |
| bengaluru | 2 | 2 | 0 | 2 | 1 | 0.000 | 1.000 | 0.000 |
| bengaluru | 3 | 2 | 0 | 2 | 1 | 0.000 | 1.000 | 0.000 |
| chennai | 1 | 16 | 5 | 11 | 2 | 0.312 | 0.286 | 0.278 |
| chennai | 2 | 16 | 1 | 15 | 0 | 0.062 | 0.000 | 0.062 |
| chennai | 3 | 16 | 0 | 16 | 0 | 0.000 | undefined | 0.000 |
| delhi | 1 | 86 | 84 | 2 | 0 | 0.977 | 0.000 | 0.977 |
| delhi | 2 | 86 | 83 | 3 | 2 | 0.965 | 0.024 | 0.943 |
| delhi | 3 | 86 | 83 | 3 | 2 | 0.965 | 0.024 | 0.943 |
| hyderabad | 1 | 0 | 0 | 0 | 0 | undefined | undefined | undefined |
| hyderabad | 2 | 0 | 0 | 0 | 0 | undefined | undefined | undefined |
| hyderabad | 3 | 0 | 0 | 0 | 0 | undefined | undefined | undefined |
| kolkata | 1 | 65 | 55 | 10 | 2 | 0.846 | 0.035 | 0.821 |
| kolkata | 2 | 65 | 62 | 3 | 3 | 0.954 | 0.046 | 0.912 |
| kolkata | 3 | 65 | 55 | 10 | 4 | 0.846 | 0.068 | 0.797 |
| mumbai | 1 | 28 | 17 | 11 | 11 | 0.607 | 0.393 | 0.436 |
| mumbai | 2 | 28 | 12 | 16 | 13 | 0.429 | 0.520 | 0.293 |
| mumbai | 3 | 28 | 9 | 19 | 15 | 0.321 | 0.625 | 0.209 |
| pune | 1 | 49 | 46 | 3 | 2 | 0.939 | 0.042 | 0.902 |
| pune | 2 | 49 | 44 | 5 | 4 | 0.898 | 0.083 | 0.830 |
| pune | 3 | 49 | 43 | 6 | 3 | 0.878 | 0.065 | 0.827 |

## Prediction intervals

Selected-policy absolute-residual split-conformal radii use finite-sample higher
order statistics. Quantile LightGBM uses a separate calibration correction and
nested 80/95% bounds. Calibration labels are not refitted. Temporal dependence and
season shifts violate exchangeability; report empirical coverage rather than a
distribution-free deployment guarantee. Bounds are nonnegative.

| City | Horizon | Policy 80% | Policy 95% | Mean width 80 | Mean width 95 | Quantile 80% | Quantile 95% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bengaluru | 1 | 0.614 | 0.859 | 10.215 | 18.585 | 0.712 | 0.891 |
| bengaluru | 2 | 0.658 | 0.842 | 14.284 | 23.927 | 0.734 | 0.870 |
| bengaluru | 3 | 0.614 | 0.772 | 15.699 | 27.491 | 0.734 | 0.864 |
| chennai | 1 | 0.652 | 0.859 | 16.102 | 27.100 | 0.728 | 0.913 |
| chennai | 2 | 0.620 | 0.837 | 16.574 | 30.491 | 0.739 | 0.913 |
| chennai | 3 | 0.630 | 0.908 | 19.772 | 41.614 | 0.745 | 0.940 |
| delhi | 1 | 0.685 | 0.897 | 41.460 | 77.204 | 0.804 | 0.967 |
| delhi | 2 | 0.674 | 0.826 | 55.590 | 97.757 | 0.799 | 0.962 |
| delhi | 3 | 0.728 | 0.902 | 64.087 | 143.293 | 0.859 | 0.973 |
| hyderabad | 1 | 0.783 | 0.962 | 8.456 | 15.153 | 0.826 | 0.984 |
| hyderabad | 2 | 0.761 | 0.929 | 12.046 | 19.745 | 0.788 | 0.962 |
| hyderabad | 3 | 0.750 | 0.924 | 12.715 | 26.922 | 0.788 | 0.957 |
| kolkata | 1 | 0.647 | 0.891 | 15.132 | 28.365 | 0.804 | 0.940 |
| kolkata | 2 | 0.647 | 0.913 | 19.248 | 37.381 | 0.826 | 0.946 |
| kolkata | 3 | 0.728 | 0.880 | 24.965 | 43.641 | 0.799 | 0.957 |
| mumbai | 1 | 0.761 | 0.880 | 12.851 | 28.087 | 0.821 | 0.962 |
| mumbai | 2 | 0.728 | 0.837 | 19.135 | 35.691 | 0.832 | 0.962 |
| mumbai | 3 | 0.788 | 0.842 | 27.390 | 45.643 | 0.826 | 0.957 |
| pune | 1 | 0.712 | 0.886 | 12.786 | 25.068 | 0.712 | 0.826 |
| pune | 2 | 0.701 | 0.853 | 17.409 | 33.446 | 0.707 | 0.864 |
| pune | 3 | 0.701 | 0.875 | 20.055 | 42.406 | 0.739 | 0.913 |

## Month and season errors

All city/horizon month and season scores are in seasonal_errors.csv. Winter is
December–February, pre-monsoon March–May, monsoon June–September and post-monsoon
October–November, reusing the forecasting calendar convention.

| City | Horizon | Month | n | Bias µg/m³ | NMB % | RMSE |
| --- | --- | --- | --- | --- | --- | --- |
| delhi | 1 | 2025-07 | 31 | 4.767 | 16.311 | 8.170 |
| delhi | 1 | 2025-08 | 31 | -0.046 | -0.139 | 7.532 |
| delhi | 1 | 2025-09 | 30 | 7.819 | 22.189 | 10.190 |
| delhi | 1 | 2025-10 | 31 | 5.224 | 4.791 | 34.642 |
| delhi | 1 | 2025-11 | 30 | 3.629 | 1.681 | 36.105 |
| delhi | 1 | 2025-12 | 31 | -9.134 | -4.258 | 49.506 |
| delhi | 2 | 2025-07 | 31 | 7.885 | 26.981 | 10.680 |
| delhi | 2 | 2025-08 | 31 | 1.731 | 5.303 | 9.963 |
| delhi | 2 | 2025-09 | 30 | 8.978 | 25.480 | 13.842 |
| delhi | 2 | 2025-10 | 31 | 0.015 | 0.014 | 51.870 |
| delhi | 2 | 2025-11 | 30 | -6.445 | -2.985 | 54.949 |
| delhi | 2 | 2025-12 | 31 | -9.621 | -4.485 | 73.524 |
| delhi | 3 | 2025-07 | 31 | 7.260 | 24.842 | 11.616 |
| delhi | 3 | 2025-08 | 31 | -0.038 | -0.115 | 9.881 |
| delhi | 3 | 2025-09 | 30 | 8.263 | 23.450 | 12.569 |
| delhi | 3 | 2025-10 | 31 | 1.341 | 1.230 | 54.372 |
| delhi | 3 | 2025-11 | 30 | -4.948 | -2.292 | 56.128 |
| delhi | 3 | 2025-12 | 31 | -9.589 | -4.470 | 74.460 |
| pune | 1 | 2025-07 | 31 | -0.632 | -3.355 | 3.210 |
| pune | 1 | 2025-08 | 31 | -0.606 | -3.519 | 2.875 |
| pune | 1 | 2025-09 | 30 | 0.216 | 1.297 | 2.700 |
| pune | 1 | 2025-10 | 31 | 2.472 | 7.167 | 8.305 |
| pune | 1 | 2025-11 | 30 | -2.225 | -3.930 | 7.231 |
| pune | 1 | 2025-12 | 31 | -17.954 | -19.164 | 22.327 |
| pune | 2 | 2025-07 | 31 | -2.755 | -14.610 | 4.611 |
| pune | 2 | 2025-08 | 31 | 1.211 | 7.038 | 3.687 |
| pune | 2 | 2025-09 | 30 | 1.356 | 8.136 | 2.989 |
| pune | 2 | 2025-10 | 31 | 3.693 | 10.705 | 15.746 |
| pune | 2 | 2025-11 | 30 | -2.394 | -4.229 | 8.292 |
| pune | 2 | 2025-12 | 31 | -23.448 | -25.029 | 27.247 |
| pune | 3 | 2025-07 | 31 | -3.210 | -17.029 | 5.347 |
| pune | 3 | 2025-08 | 31 | 0.412 | 2.397 | 4.602 |
| pune | 3 | 2025-09 | 30 | 0.279 | 1.676 | 3.970 |
| pune | 3 | 2025-10 | 31 | 2.177 | 6.311 | 19.081 |
| pune | 3 | 2025-11 | 30 | 0.035 | 0.061 | 8.376 |
| pune | 3 | 2025-12 | 31 | -24.088 | -25.712 | 27.302 |

## Delhi and Pune bias findings

The [pre-fit investigation](PHASE4_BIAS.md) reproduces the Phase 3B month failures
from saved outer predictions, including actual station counts, design switches
and missing dates. Delhi's pooled no-trend/BLH models overpredict recent low-PM
months; old-era pooling and regression toward the mean are plausible contributors,
not an established unique cause. Pune's May overprediction is modest in absolute
units but exceeds the unchanged percentage gate because the observed mean is low.

Phase 4 removes old-era targets and introduces observed PM lags with temporal
selection. Its six-month test includes Delhi's July concern but does not include
February/March or Pune's May. It cannot establish that those untested seasonal
biases are fixed. Forecast month errors above are reported without relaxing gates.

## Perfect-prognosis comparison — retrospective upper-bound experiment

Observed target-day ERA5 weather is used only in this separately labelled variant.
It is an optimistic information experiment, not a guaranteed mathematical bound:
finite samples and fitted models can produce worse scores despite ideal information.
Positive gap means the ideal-weather policy had lower RMSE. It is never served
as an operational forecast or used to select headline models.

| City | Horizon | Real-weather policy RMSE | Ideal-weather policy RMSE | Real−ideal gap |
| --- | --- | --- | --- | --- |
| bengaluru | 1 | 5.945 | 5.969 | -0.024 |
| bengaluru | 2 | 7.870 | 7.939 | -0.069 |
| bengaluru | 3 | 9.971 | 8.954 | 1.017 |
| chennai | 1 | 12.353 | 12.712 | -0.358 |
| chennai | 2 | 14.820 | 13.446 | 1.374 |
| chennai | 3 | 13.302 | 15.986 | -2.684 |
| delhi | 1 | 29.417 | 32.028 | -2.611 |
| delhi | 2 | 43.858 | 43.174 | 0.683 |
| delhi | 3 | 44.841 | 42.516 | 2.326 |
| hyderabad | 1 | 3.656 | 3.731 | -0.076 |
| hyderabad | 2 | 5.122 | 4.674 | 0.448 |
| hyderabad | 3 | 5.634 | 5.286 | 0.349 |
| kolkata | 1 | 10.159 | 10.228 | -0.069 |
| kolkata | 2 | 12.683 | 12.755 | -0.073 |
| kolkata | 3 | 15.456 | 16.044 | -0.588 |
| mumbai | 1 | 10.729 | 10.618 | 0.111 |
| mumbai | 2 | 12.802 | 12.677 | 0.125 |
| mumbai | 3 | 14.488 | 14.527 | -0.039 |
| pune | 1 | 10.414 | 11.025 | -0.612 |
| pune | 2 | 13.616 | 12.768 | 0.848 |
| pune | 3 | 14.468 | 13.957 | 0.511 |

## Operations, provenance and limitations

Every origin/model and quantile experiment is logged to the local MLflow service;
chosen city/horizon models are registered. Its database and artifacts live under
data/mlflow/ on D:. Forecast versions retain training dates, inner selection metrics,
MLflow IDs, cohort and AnalysisRun. Each issued forecast stores bounds, category,
mode, model version, top five SHAP drivers/values and feature availability audit.
SHAP describes conditional predictions, not causal effects. Only PM2.5 categories
are forecast; an overall CPCB AQI requires other pollutants. Decimal concentrations
use the continuous boundary extension (≤30, ≤60, ≤90, ≤120, ≤250, then severe).

Daily weather refresh is scheduled before day-end and issuance after midnight IST.
Live mode requires an OpenAQ key, at least 18 fresh current-completed-day hours and
ingestion completed before issue-end. Without this it explicitly replays the latest
archived day. Live mode remains unverified without the user's OpenAQ key; replay
and public live weather are tested. Historical daily source rounding, station-network
changes and missing data remain limitations. Bengaluru's fixed panel does not accept
unmatched new provider IDs. Replay predictions beyond the last observation are unscored.

No tuning or threshold change follows held-out scores. SARIMAX iteration/convergence
flags are retained; inspect them alongside its errors. The last six months provide
only one seasonal cycle, no external year test and no claim of clinical/regulatory
fitness. Model choice may favour a simple baseline, and negative skill is retained.

## Notes for Phase 5 citation support

The future assistant should cite this report, the frozen protocol, prior bias report,
AnalysisRun-specific model_comparison/seasonal_errors/coverage CSVs and input hashes.
Use read-only `/api/forecast/<city>/latest/`, `/history/?start=&end=` (inclusive target
dates), and `/evaluation/`. Always identify city, horizon, issue/target date, cohort,
replay/live mode, model version and weather knowledge. Cite event counts with POD/FAR/CSI
and empirical interval coverage. Never present perfect-prognosis, rejected LSTM,
historical CAMS samples or retrospective best-model scores as live forecast skill.

References: [Open-Meteo archive](https://open-meteo.com/en/docs/historical-forecast-api),
[Previous Runs](https://open-meteo.com/en/docs/previous-runs-api),
[run/publication semantics](https://open-meteo.com/en/docs/single-runs-api),
[Air Quality API](https://open-meteo.com/en/docs/air-quality-api),
[conformal methods](https://arxiv.org/abs/2107.07511),
[DM/HLN](https://github.com/bank-of-england/forecast_evaluation/blob/main/src/forecast_evaluation/tests/diebold_mariano.py),
[CPCB technical AQI report](https://www.cpcb.gov.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvRklOQUwtUkVQT1JUX0FRSV8ucGRm).


## Additional reproducibility evidence

CAMS: 0 non-null values out of 93240 requested lead-forecast hours; IngestionRun 97.

SARIMAX tuning convergence: 569 of 588 recorded candidates did not converge within the fixed iteration limit. These flags and warnings remain visible; finite predictions do not prove a stable fitted likelihood.

SARIMAX SHAP describes current exogenous terms conditional on the filtered known history; it does not allocate the dynamic past-state contribution. Correlated feature attributions and this conditioning limit interpretation.

Archived weather deliberately uses older leads than the latest live forecast. The deployment weather distribution can differ; live skill is unverified.

The latest registered selections below use inner tuning, not final test scores. Their rolling test score is the full monthly-selected policy above.

| City | Horizon | Latest selected algorithm | Fit label end | Inner RMSE |
| --- | --- | --- | --- | --- |
| bengaluru | 1 | persistence | 2025-10-01 | 2.637 |
| bengaluru | 2 | persistence | 2025-10-01 | 3.696 |
| bengaluru | 3 | persistence | 2025-10-01 | 3.715 |
| chennai | 1 | lstm | 2025-10-01 | 4.260 |
| chennai | 2 | lstm | 2025-10-01 | 4.621 |
| chennai | 3 | lightgbm | 2025-10-01 | 4.615 |
| delhi | 1 | lstm | 2025-10-01 | 8.580 |
| delhi | 2 | mean7 | 2025-10-01 | 9.211 |
| delhi | 3 | mean7 | 2025-10-01 | 9.367 |
| hyderabad | 1 | sarimax | 2025-10-01 | 3.310 |
| hyderabad | 2 | sarimax | 2025-10-01 | 4.136 |
| hyderabad | 3 | sarimax | 2025-10-01 | 4.168 |
| kolkata | 1 | lstm | 2025-10-01 | 3.945 |
| kolkata | 2 | lstm | 2025-10-01 | 4.637 |
| kolkata | 3 | lstm | 2025-10-01 | 4.801 |
| mumbai | 1 | lightgbm | 2025-10-01 | 2.277 |
| mumbai | 2 | persistence | 2025-10-01 | 3.139 |
| mumbai | 3 | persistence | 2025-10-01 | 3.087 |
| pune | 1 | lightgbm | 2025-10-01 | 2.726 |
| pune | 2 | lightgbm | 2025-10-01 | 3.059 |
| pune | 3 | lightgbm | 2025-10-01 | 3.420 |

## Live verification

Compute launch Git revision: `6b3f4b028d0b352b0f29763e8833b4372497f1b1`. Report export provenance
is recorded separately in the manifest; postprocessing does not refit models.

Independent checks covered 7728 prediction rows, 294 purged origins and 147 finished MLflow model versions.
Stored replay forecasts: 3885. All 21 latest/history/evaluation GETs returned HTTP 200; POST and invalid-input checks retained their expected 405/400/404 responses.

All 18 original test/support files retain their baseline hashes. Earlier research artifact hashes and the 16,266,240 measurement/provenance fingerprint are unchanged.

Full suite: `148 passed, 148 warnings in 29.25s`. Warnings remain visible.


## Figures

![Issued-policy skill](../../data/results/21/forecast_skill.png)

[Bengaluru observed/issued forecasts and 95% intervals](../../data/results/21/bengaluru_forecast_evaluation.png)
[Chennai observed/issued forecasts and 95% intervals](../../data/results/21/chennai_forecast_evaluation.png)
[Delhi observed/issued forecasts and 95% intervals](../../data/results/21/delhi_forecast_evaluation.png)
[Hyderabad observed/issued forecasts and 95% intervals](../../data/results/21/hyderabad_forecast_evaluation.png)
[Kolkata observed/issued forecasts and 95% intervals](../../data/results/21/kolkata_forecast_evaluation.png)
[Mumbai observed/issued forecasts and 95% intervals](../../data/results/21/mumbai_forecast_evaluation.png)
[Pune observed/issued forecasts and 95% intervals](../../data/results/21/pune_forecast_evaluation.png)
