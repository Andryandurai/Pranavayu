# Phase 4 implementation and environment fixes

This record distinguishes configuration/implementation failures from honest
forecast performance. No existing test was changed or weakened.

| Failure or finding | Root cause | Fix and observed rerun |
| --- | --- | --- |
| Requested historical weather looked suitable for backtesting | Historical Forecast API stitches near-valid-time runs; it does not establish day-t vintage | Actual Previous Runs probes returned GFS lead-2/3/4 weather. Headline features use those older vintages and audited availability bounds |
| Incomplete IST days at download boundaries | Nonoverlapping UTC windows lose the first half of an IST day | Overlap the first UTC day. IngestionRun 94 inserted 168 missing derived daily forecast-weather rows; repeat Run 96 inserted zero |
| CAMS historical PM2.5 existed, but vintage coverage did not | Valid-time history is distinct from issued forecasts | Actual seven-city lead-2/3/4 evaluation queries returned 93,240 null hours; IngestionRun 97 is explicitly skipped |
| Two new integration fixtures errored | Fixture setup omitted the existing required AnalysisRun.started_at | Supply actual start timestamps in the new fixtures; all assertions retained. Full suite rerun: 145 passed |
| NumPy/pandas date arithmetic emitted new generic-unit deprecations | Pandas arithmetic with the newer NumPy uses an unspecified timedelta unit | Production date offsets now use explicit NumPy units or Python datetimes; no warning filter was added. Existing/new-fixture warnings remain visible |
| SARIMAX exogenous terms were redundant | The three-day mean is an exact linear combination of three PM lags | Training-only pivoted QR removes dependent/constant columns, fixed before real fits; future-label isolation fixture passes |
| MLflow background services consumed unnecessary RAM | New MLflow defaults start multiple job consumers | Disable MLflow job execution; tracking and model registry stay enabled. Daily forecasting still uses Celery |
| Initial fit did not honour single-thread numerical configuration | NumPy OpenBLAS defaulted to 12 threads | Interrupt and retain AnalysisRun 20 (failed, with saved outputs). Set and record BLAS/OpenMP/MKL/NumExpr thread limits before a fresh AnalysisRun 21; forecast method/splits/selection rules unchanged |
| Live issuance could recompute old calibration from incomplete current history | Stateful SARIMAX calibration predictions depended on the operational history window | Retain the saved training radii and preserve measured past labels even where weather features are absent; frozen-state fixture passes |
| Live PM refresh did not include the current day and was not scheduled before cutoff | Date-only end was midnight and daily issuance relied on hourly ingestion alone | Request ten days through the actual current instant; schedule PM at 23:35 IST before weather 23:40 and issuance 00:10; exact bounds and idempotent schedule fixtures pass |
| A fresh current day could still lack required lag/weather inputs | Freshness checked only the latest daily mean | Validate all three horizon feature rows before writing; incomplete live inputs fall back to labelled archival replay. Actual pipeline fixture confirms no partial live rows or duplicates |

Public live weather Celery task `632924ce-4a60-4636-8676-100ad7d6bb56`
completed successfully as IngestionRun 98, inserting 21 daily forecast-weather
records: three horizons for each of seven cities. This verifies public weather,
not keyed live PM ingestion. Final replay, metrics and validation evidence is
added to PHASE4.md and VALIDATION.md after the completed evaluation.

Operational targeted rerun: **5 passed, 101 visible warnings in 12.00s**.
Ruff reports `All checks passed!`; schema validation exits 0 without warnings.
