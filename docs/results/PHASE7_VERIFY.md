# Phase 7 persistence-definition verification

Baseline `83be5f4`. **Equivalent on the fixed stored sample**, with matching
code definitions. No retraining, evaluation rerun or original forecast write.
The preceding [basemap fix](MAP_FIX.md) is included in the same local handoff.

## Decisions

1. Compare the actual scored `persistence` column and its producer, not the
   currently selected model's algorithm name. The versioned serving override
   remains `phase4-persistence-v1` with the same nine combinations.
2. Fix three issue dates before the comparison: 2025-07-15, 2025-09-15 and
   2025-12-15. Use those dates for every combination. Retain source paths/hashes
   and full-precision hourly subsets as a new test fixture; do not edit original
   inputs or labels. Absolute tolerance is 1e-10 µg/m³; relative tolerance is zero.
3. Compare both legacy replay resolution and captured issue-time persistence
   provenance. Do not infer equivalence from the labels alone. Also compare
   with the saved CSV prediction column; distinguish CSV float round-trip
   differences from a change in the persistence definition.
4. The definitions agree, so retain them. README, WRITEUP, DEMO, RESUME and the
   prior PHASE7_FIX report do not need a definition correction and remain unchanged.
5. Improve only missing-input presentation: retain HTTP 503 and the original
   explanation, adding a clear leading message. Add an explicit, user-triggered
   read-only serving check to the dashboard. Historical dashboard figures remain
   immutable; no new issuance, fitting or ingestion is triggered by the check.
6. Generate the 503 fixture in a separate process using Django's test client and
   a process-local mocked missing input. Browser interception reuses that actual
   response. Never remove production input files or modify a running-server value.
7. No remote is configured. Do not create one or push. The repository has no
   configured remote backup; a remote is needed for off-device Git backup.
   Separate manual backups have not been verified.

## Phase 4 definition and scored path

Exact code at [estimators.py:50–51](../../apps/forecast/estimators.py#L50):

```python
if self.name == "persistence":
    return rows.pm_t.to_numpy()
```

`pm_t` is the zero-lag daily value: [data.py:49–50](../../apps/forecast/data.py#L49)
assigns `daily[name] = daily.value.shift(lag)` for names beginning `pm_t` and
lags beginning zero. Its aggregation contract is quoted verbatim at
[aggregation.py:13](../../apps/analytics/aggregation.py#L13):

> Calendar days in IST; 18 distinct valid hour bins, without filling values.

The actual mean is [aggregation.py:25](../../apps/analytics/aggregation.py#L25):

```python
daily = rows.groupby("date").agg(value=("value", "mean"), valid_count=("hour", "nunique"))
```

After dropping null values and averaging within each distinct local hour,
the code averages the valid hourly values within that IST day. It is not a
rolling 24-hour window ending at a request time. At fewer than 18 valid bins,
[line 28](../../apps/analytics/aggregation.py#L28) sets the daily mean to NaN:

```python
daily.loc[daily.valid_count < 18, "value"] = float("nan")
```

[pipeline.py:180](../../apps/forecast/pipeline.py#L180) stores each model's
prediction via `predictions[name] = predict(model, test, rows)`.
[pipeline.py:325](../../apps/forecast/pipeline.py#L325) includes `persistence`
among scored columns, and [line 337](../../apps/forecast/pipeline.py#L337) calls
`score = scores(group, algorithm)`. These are the definition and column used
for the original [Phase 4 comparison](PHASE4.md#model-comparisons).

## Served definition

Exact legacy replay code at [serving.py:54](../../apps/forecast/serving.py#L54):

```python
return raw_daily(hourly)["value"].to_dict()
```

The date lookup at [serving.py:73](../../apps/forecast/serving.py#L73) is:

```python
value = daily.get(pd.Timestamp(forecast.issued_for_date))
```

New issuances first use [serving.py:60](../../apps/forecast/serving.py#L60):

```python
value = forecast.feature_provenance.get("persistence_value")
```

That input is captured directly from the same evaluated feature definition by
[data.py:164](../../apps/forecast/data.py#L164):

```python
"persistence_value": float(row.pm_t),
```

| Field | Phase 4 evaluation | Serving | Comparison |
| --- | --- | --- | --- |
| Carried value | `pm_t`, zero-lag issue-day mean | Captured `pm_t`, or legacy issue-date daily mean | Same |
| Window/timezone | IST calendar day, equal valid-hour weights | Same `raw_daily` function | Same |
| Cohort | Bengaluru fixed panel; other cities all-station inputs | Same retained Run 8 panel/hourly input | Same |
| Issue cutoff | End of day t IST | Stored `issued_for_date` / captured issue-time provenance | Same |
| Horizon | Carry day-t mean to t+1/t+2/t+3 | No horizon shift in lookup | Same |
| Missing issue day | NaN below 18 valid bins; missing PM features excluded | Missing/non-finite input returns 503; no older-day carry | Same unavailable value; explicit serving error |
| Scoring eligibility | Complete lag/weather features and observed target required | Can serve an already stored unscored future target | Different purpose; no claim of equal evaluation support |

[weather.py:30–34](../../apps/forecast/weather.py#L30) defines issue end as the
next IST midnight minus one microsecond, converted to UTC. Historical publication
logs are absent: Phase 4 assumes day-t concentration availability at that cutoff.
This audit does not establish real-time publication availability.

## Stored-data equivalence

Every row below uses issue dates **2025-07-15, 2025-09-15, 2025-12-15**.
There are 27 comparisons across the nine fallback combinations. The regression
fixture contains the actual hourly values used for those dates, preserving
source provenance and the original CSV persistence values. No network input is used.

| City | Horizon | Max served vs recomputed difference, µg/m³ | Max vs saved CSV, µg/m³ |
| --- | --- | --- | --- |
| bengaluru | 1 | 0 | 0 |
| bengaluru | 3 | 0 | 0 |
| chennai | 1 | 0 | 0 |
| mumbai | 1 | 0 | 3.552713678800501e-15 |
| mumbai | 2 | 0 | 3.552713678800501e-15 |
| mumbai | 3 | 0 | 3.552713678800501e-15 |
| pune | 1 | 0 | 1.4210854715202004e-14 |
| pune | 2 | 0 | 1.4210854715202004e-14 |
| pune | 3 | 0 | 1.4210854715202004e-14 |

Result: **equivalent**, absolute tolerance **1e-10 µg/m³**, relative tolerance
**0**. Saved CSV differences are floating-point round trips. This fixed sample
and source inspection do not constitute a new forecast-skill evaluation.

## Missing inputs and browser checks

The leading message is now exactly:

> No forecast: input data missing for this issue date.

It is followed by the preserved explanation: “Issue-day persistence input
unavailable; the losing model is not served.” It appears in the 503 API body,
the dashboard's **Check served forecasts** status and the forecast page's status.
The previous message contained only that latter explanation. Persistence itself
was not changed. A regression case also confirms that a day reduced to 17 valid
hours returns unavailable instead of carrying an earlier day's value.

Real Mumbai persistence and Delhi model responses, plus safe 503 fixtures,
passed at desktop and phone widths without horizontal overflow or JavaScript
errors. Fixtures do not change the live server's data. Screenshots:

| View | Desktop | Phone |
| --- | --- | --- |
| Dashboard, persistence | [1440](phase7-verify-dashboard-mumbai-1440.png) | [390](phase7-verify-dashboard-mumbai-390.png) |
| Dashboard, model | [1440](phase7-verify-dashboard-delhi-1440.png) | [390](phase7-verify-dashboard-delhi-390.png) |
| API, persistence | [1440](phase7-verify-api-mumbai-1440.png) | [390](phase7-verify-api-mumbai-390.png) |
| API, model | [1440](phase7-verify-api-delhi-1440.png) | [390](phase7-verify-api-delhi-390.png) |
| Dashboard, missing input | [1440](phase7-verify-dashboard-missing-1440.png) | [390](phase7-verify-dashboard-missing-390.png) |
| Forecast page, missing input | [1440](phase7-verify-forecasts-missing-1440.png) | [390](phase7-verify-forecasts-missing-390.png) |
| API, missing input | [1440](phase7-verify-api-missing-1440.png) | [390](phase7-verify-api-missing-390.png) |

## Remote, tests and integrity

`git remote -v` produced **no output**. No remote was created and no push was
performed. There is no configured remote repository backup.

Final full web-container suite: **322 passed, 147 warnings in 74.13 s**.
All 310 originals are unchanged; 12 regression cases were added. Ruff reports
`All checks passed!`; formatting reports `280 files already formatted`.

```powershell
docker compose exec -T web python manage.py check --deploy --settings=enviroinsights.settings.prod
```

Actual output: `System check identified no issues (0 silenced).`

| Frozen set | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| Phase 3A.2 | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` |
| Phase 4 | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` |
| Phase 5 question/relevance | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` |

All four Phase 5 files and all 967 Phase 4 artifacts retain their fingerprints.
All 3,948 stored forecasts, 150 model versions and 21 evaluation rows match
their prior database fingerprints. No model, original metric or label changed.

The journal retains initial fixture-host and browser-helper failures and their
corrections. [Machine-readable evidence](PHASE7_VERIFY_METRICS.json) includes
the exact source quotes, comparisons, screenshots and check output. Raw evidence
and final Git output are retained in `data/results/phase7verify/`; final commit
identity is outside the commit to avoid a self-referential hash. A local commit
is needed because the map, missing-input presentation, tests and reports changed.
