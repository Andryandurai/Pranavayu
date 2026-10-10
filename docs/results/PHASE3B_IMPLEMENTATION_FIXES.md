# Phase 3B implementation corrections

The criteria and model grid in PHASE3B_PROTOCOL.json remain unchanged.
This log records implementation failures; it does not optimise thresholds or model
penalties to improve reported scores.

- The first stored timestamp UPDATE failed when a timestamp crossed a Timescale
  chunk boundary. The transaction rolled back. The repair now atomically routes
  boundary rows through the hypertable parent and updates other rows in place.
  The partition-boundary regression test and the full live repair pass.
- New tests caught NumPy string labels passed to pandas.Timestamp, nonaligned
  year/week bootstrap indexes, and a Series/DatetimeIndex date accessor mismatch.
  Those implementation defects were fixed; original tests were unchanged.
- AnalysisRun 11 failed in the second Delhi outer fold because statsmodels cannot
  evaluate B-splines outside their knot support. An actual held-out daily rainfall
  value of 115.4000015258789 mm exceeded the fixed training-only support (the
  no-BLH recent-period diagnostic upper bound was 70.64478302001953 mm).
  The GAM now uses a **flat boundary extension** outside its existing support.
  This changes only the prediction mapping: observations, weather, knots,
  scaling, df=6, alpha=10, folds, forest choices and readiness criteria are intact.
  Every clipped prediction is counted by feature in the outer-fold metadata.
  A regression test checks finite predictions, boundary equivalence and unchanged
  input values. No outcome-dependent parameter tuning was introduced.
- Pune's successful Run 10 preceded this guard and encountered no spline-domain
  failure. Its results remain versioned with its original code hash. Any subsequent
  run records the new guard's support diagnostics.
- The new boundary regression fixture exposed statsmodels' perfect-separation
  exception on an exact Gaussian linear fit. Gaussian identity-link fitting now
  falls back only for that exception to the same penalised least-squares system
  used by its PIRLS solver. The unchanged fixture checks the actual boundary rule;
  model penalties and nondegenerate fits are unchanged.

The exploratory GAM cross-check must not be treated as independently calibrated
for weather extremes beyond the observed training support.
