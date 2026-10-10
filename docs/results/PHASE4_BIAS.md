# Delhi and Pune bias investigation before forecasting

This analysis uses saved Phase 3B outer-fold predictions and raw Run 8 station
support. It makes no new model fit and does not use Phase 4 scores.

## Delhi

| Month | OOF days | Observed | Predicted | Bias µg/m³ | NMB % |
| --- | --- | --- | --- | --- | --- |
| 1 | 48 | 184.2674 | 189.5105 | 5.2431 | 2.8454 |
| 2 | 50 | 102.4819 | 135.7932 | 33.3113 | 32.5045 |
| 3 | 48 | 70.1414 | 92.1373 | 21.9960 | 31.3595 |
| 4 | 53 | 74.7567 | 86.8829 | 12.1261 | 16.2208 |
| 5 | 62 | 78.8693 | 79.7617 | 0.8924 | 1.1315 |
| 6 | 60 | 53.7993 | 64.0179 | 10.2186 | 18.9939 |
| 7 | 62 | 34.2784 | 44.9968 | 10.7184 | 31.2686 |
| 8 | 62 | 30.1357 | 34.3375 | 4.2018 | 13.9429 |
| 9 | 60 | 38.5813 | 44.2524 | 5.6710 | 14.6989 |
| 10 | 62 | 110.1581 | 113.4823 | 3.3242 | 3.0176 |
| 11 | 60 | 233.2320 | 226.5963 | -6.6357 | -2.8451 |
| 12 | 62 | 192.2501 | 192.5184 | 0.2682 | 0.1395 |

Missing recent OOF days: 42. Monthly counts
and inner-selected design/station support are retained in the diagnostic CSVs.

2024-02: 22 OOF days, bias 21.3172 µg/m³, NMB 19.6591%, mean contributing stations 34.9318.
2025-02: 28 OOF days, bias 42.7352 µg/m³, NMB 43.6942%, mean contributing stations 36.8557.

## Pune

| Month | OOF days | Observed | Predicted | Bias µg/m³ | NMB % |
| --- | --- | --- | --- | --- | --- |
| 1 | 41 | 60.6453 | 61.7217 | 1.0764 | 1.7748 |
| 2 | 43 | 58.3168 | 56.5666 | -1.7502 | -3.0012 |
| 3 | 41 | 49.3584 | 49.4822 | 0.1238 | 0.2508 |
| 4 | 46 | 37.7241 | 38.1544 | 0.4303 | 1.1406 |
| 5 | 36 | 24.5465 | 29.5758 | 5.0293 | 20.4888 |
| 6 | 51 | 20.3718 | 21.8453 | 1.4735 | 7.2330 |
| 7 | 62 | 17.3006 | 16.2933 | -1.0073 | -5.8224 |
| 8 | 62 | 16.7114 | 17.9821 | 1.2707 | 7.6038 |
| 9 | 60 | 17.0215 | 18.7151 | 1.6936 | 9.9497 |
| 10 | 62 | 34.1084 | 36.1873 | 2.0789 | 6.0950 |
| 11 | 60 | 61.3714 | 62.8942 | 1.5228 | 2.4813 |
| 12 | 62 | 75.6380 | 69.0111 | -6.6269 | -8.7614 |

Missing recent OOF days: 105. Monthly counts
and inner-selected design/station support are retained in the diagnostic CSVs.

2024-05: 5 OOF days, bias -0.5972 µg/m³, NMB -1.7799%, mean contributing stations 4.1917.
2025-05: 31 OOF days, bias 5.9368 µg/m³, NMB 25.7069%, mean contributing stations 6.4462.

Delhi's pooled weather/calendar model overpredicts recent low-pollution months;
the saved design switches between a pooled no-trend daily forest and a BLH
hourly forest. Old-period concentrations enter those pooled fits. This is
consistent with cross-era level/season mixing and regression toward the mean,
but the saved diagnostics do not identify a unique causal mechanism. The BLH
fold excludes early-2024 days. The error is not evidence of a new timestamp
offset: the canonical clock was already independently verified in Phase 3B.

Pune's failing May bias is a modest absolute overprediction relative to a low
observed mean. BLH-selected folds omit early-2024 support, and the 2024/2025
month-specific CSV distinguishes support from annual bias cancellation. Published
network composition varies; station counts alone cannot attribute the error.

The forecasting remedy is recent-only raw data, lagged PM, target-date calendar,
issue-safe forecast weather and monthly temporal selection/calibration. Forecast
bias must still be measured; this investigation does not promise it will vanish.
