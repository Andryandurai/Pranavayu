# Phase 7: evidence dashboard and final presentation

Finishing pass after `25be37b`. Scientific limitations are retained; this phase
adds presentation and handoff material, not new model evaluation results.

## Decisions

1. Retain Django and the D: checkout. Add a stored-results dashboard; do not
   retrain models, run ingestion, change frozen labels, or change VayuSim physics,
   presets, historical results or example values. Commit locally; do not push.
2. The named dataviz skill was not found in the available skills or local skill
   directories. Use labelled tables, explicit units/cohorts, neutral and warning
   colours with text (never colour alone), source links, light/dark themes and
   responsive cards. No chart is necessary for these audit comparisons.
3. Task 0 expressly authorises an explicit deadline for an intermittent timing
   test. The only identified 6B failure is `test_crosswind_mass_reflection`:
   input generation took 2.10 and 1.76 seconds. Hypothesis 6.169.1's installed
   `record_for_health_check` allows max(1 second, five times deadline) for initial
   input generation. Set this test's explicit deadline to 1000 ms, providing a
   bounded 5-second generation budget for this Windows/WSL environment. Keep its
   30 examples, float domains, integration and numerical assertion unchanged.
   Do not suppress health checks or choose seeds in response to results. Freeze
   all other tests; compare ASTs to prove the deadline is the sole semantic edit.
4. Display historical snapshot counts with dates and source files. An empty fresh
   database must not imply that retained historical results have been rerun.
   Source files are served through a fixed allowlist, never arbitrary file paths.
5. Present Phase 4 negative-skill policies as retrospective failures with a
   persistence recommendation. Verify the actual saved/current issuance policy
   before claiming that fallback is operational. Do not change models or policy
   based on this presentation task.
6. The read-only snapshot contains 16,266,240 concentration rows and 1,238,688
   weather observations: 17,504,928 combined rows. Label the 17.5M total with
   that denominator; quality-flag counts apply to concentration rows only.
7. The requested claim that all nine negative-skill policies "use persistence"
   conflicts with the current stored issuance snapshot: four use persistence;
   five currently use other algorithms. Mark all nine as persistence advised,
   show each current algorithm, and disclose the five gaps. Do not rewrite
   predictions or imply that retrospective fallback has been deployed.
8. No Git remote or remote-tracking branch is configured. The local 6A–6B
   commits exist, but their publication elsewhere cannot be verified. Record
   that uncertainty; perform no push.

## Reliability

Only `tests/test_vayusim_physics.py::test_crosswind_mass_reflection` had a recorded
Phase 6B intermittent failure. Its explicit `deadline=1000` retains a finite
execution limit and increases the installed Hypothesis initial-generation budget
to five seconds. No seed was forced or health check suppressed. The 30 examples,
float domains, integration and numerical assertion are unchanged. AST comparison
against `25be37b` proves that this added keyword is the sole semantic change in
the existing test file; all other original test/fixture bytes are unchanged.

| Full web-container run | Passed | Existing warnings | Seconds | Exit |
| --- | --- | --- | --- | --- |
| 1 | 284 | 147 | 48.62 | 0 |
| 2 | 284 | 147 | 49.98 | 0 |
| 3 | 284 | 147 | 51.57 | 0 |

No intermittent failure occurred in these three runs. They include the original
271 tests plus 13 new dashboard/evidence checks. Original domains/tolerances are
preserved; this is not a guarantee on every machine. The unchanged warnings cover
NumPy/pandas timedelta deprecations, SHAP deprecations, a compiled netCDF4 ABI
warning and a statsmodels fixture convergence warning. None is silenced.
[Exact check record](PHASE7_CHECKS.json).

## Dashboard

`http://127.0.0.1:8000/dashboard/` has six source-linked sections: ingestion,
analytics, forecasting, assistant, VayuSim and testing. It reads only a stored
snapshot; a normal page load performs no database query. All displayed result
cards/tables have a link to the underlying record. Both interval methods appear
for every archived-weather city/horizon, with 14 selected-level failures; nine
negative-skill rows carry persistence advice and current issuance is separate.
The source allowlist returns original bytes as plain text; arbitrary paths are
not accepted. Missing snapshots display an explicit unavailable state.

The snapshot counts 17,504,928 combined rows, not that many pollutant measurements.
It preserves Delhi's inconclusive matched-panel interval and Hyderabad's 0/53
cohort contrast. Phase 5 recall/MRR/exact-support scores remain labelled as that
original evaluation. The failed local-generation gate and every hypothetical
urban C/F example warning are visible. [Data and source hashes](PHASE7_DATA.json).

## Documents and claims audit

Produced: rewritten [README](../../README.md), [deployment notes](../DEPLOYMENT.md),
[write-up](WRITEUP.md), [five-minute demo](../DEMO.md) and [five resume bullets](../RESUME.md).
The write-up has **2,507 words**, counted as Unicode words including numerals,
excluding punctuation/markup. The demo plans **5:00**; it does not guarantee
that a cold operation finishes within a presentation slot.

| Old or requested statement | Final statement / reason |
| --- | --- |
| “17.5M rows” without a denominator | 17,504,928 combined observations: 16,266,240 concentration rows plus 1,238,688 weather observations. Quality flags use concentration rows only. |
| All nine losing policies “use persistence” | Nine retrospective losses; persistence advised. Only four of those latest issuances use it; five gaps are disclosed. Code/outputs were not changed to make the claim true. |
| A single forecast success as a general capability | Delhi next-day 12.6% belongs to the saved rolling backtest; negative rows and coverage failures are shown alongside it. |
| High exact-support assistant scores without scope | Original Phase 5 retrieval, citation-use, numeric-cell and refusal denominators are explicit; they do not certify full answer quality. |
| Optional local generation treated as a working answerer | Default extractive path; opt-in local LLM failed, with 2/80 literature and 0/30 available-data answers retained. |
| Historical memory measurement described as “current” | Machine-specific WSL setting and dated audit; a fresh memory check is necessary before experimental generation. |
| “Home placeholder”, Make-oriented setup and older test counts | Current routes, Windows wrapper and the actual repeated Phase 7 check record. |
| Phase 1 no-ingestion-schedules wording in a mature stack | Current stack has Beat; use one scheduler. Fresh seed is distinguished from restoring historical observations. |
| An inaccessible Princeton archive presented as source coverage | Explicit public XKDR PM2.5 alternative; inaccessible originals, historical pollutant gaps and excluded AQI matrices remain visible. |
| Keyed adapters conflated with real ingestion | OpenAQ, NASA FIRMS and CDS were skipped without credentials; no live verification claimed. |
| Negative Delhi estimate without uncertainty | −17.59 with [−35.07, +1.66]; interval spans zero, so direction is inconclusive under the method. |
| Hyderabad zero exceedances read as every station staying low | City daily mean and cohort are explicit; all-station 0 versus fixed-panel 53 is network sensitivity. |
| Formula/scheme comparisons conflated with model performance | Passing formula checks, limited independent rural-D case, beyond-tolerance Briggs–Martin differences, and urban C/F unvalidated branches remain separate. |
| A settings check described as deployed readiness | Production module/output are recorded; TLS, proxy/static serving, recovery and external hosting remain unconfigured. |
| Older phase reports treated as freshly rerun results | Historical reports/files are preserved byte-for-byte. New summaries cite their original records, dates and input hashes. |

## Links, browser checks and deployment

Local document links are checked against actual files. External references used
in the write-up/deployment notes were retrieved successfully with the web reader:
Grange ACP article, Brune Table 2.3, EPA ISC3 PDF, Hypothesis API reference and
Django 5.2 deployment checklist. No inaccessible alternative link was added.
The current web Hypothesis documentation is newer than the installed 6.169.1;
the timing-budget statement comes from the inspected installed source.

Production settings command:

```powershell
docker compose exec -T web python manage.py check --deploy --settings=enviroinsights.settings.prod
```

Actual output:

```text
System check identified no issues (0 silenced).
```

The deployment example is documentation only. Its YAML was extracted from the
document and passed Compose `config --quiet`; no TLS, proxy, hosting or secret
configuration was applied. All 15 local Markdown anchor targets and local file
links resolve. Commands and outputs, including the initial missing template-library
configuration and its fix, are in [VALIDATION.md](../VALIDATION.md).

### Browser evidence

Headless installed Edge/Playwright checked Dashboard, Overview, Forecasts,
Research, Library, Ask and VayuSim at **1440 and 390 pixels**: all 14 page loads
returned 200, with no JavaScript errors or horizontal overflow. The dashboard
was checked in light and dark themes, all **14 distinct dashboard evidence URLs**
returned 200, and the 14 coverage failures/nine persistence-advice rows remain
visible. Ask's quality-gate limitation and VayuSim's urban warning are visible.
Additional Mumbai and Hyderabad example loads at both widths also returned 200
with visible **unvalidated branch** labels. Only VayuSim requested an external
host, `tile.openstreetmap.org`, for the existing attributed basemap.

The demo actually returned a cited Delhi 2025 annual mean of
96.65482379525307 µg/m³, 365 valid days, run 9. Its Delhi 2020 query returned
“Insufficient evidence in the available documents and project data.” The browser
harness initially omitted that wording from its refusal matcher; the matcher
was corrected and both prompts passed without changing the application answer.
A later focused test command used a nonexistent filename, collected no tests,
and was corrected to the discovered files: **15 passed in 7.30 s**. Ruff and the
deployment check were then rerun successfully. These command mistakes and the
preservation helper's import-path correction are retained in the journal.

There are **24 Phase 7 screenshots** under `docs/results/phase7-*.png`.
Representative views:

- Dashboard [desktop](phase7-dashboard-1440.png), [phone](phase7-dashboard-390.png),
  [dark desktop](phase7-dashboard-dark-1440.png), [dark phone](phase7-dashboard-dark-390.png).
- Assistant limits [desktop](phase7-ask-1440.png), [phone](phase7-ask-390.png);
  actual [cited answer](phase7-demo-answer.png) and [refusal](phase7-demo-refusal.png).
- VayuSim warning [Delhi phone](phase7-vayusim-390.png),
  [Mumbai phone](phase7-vayusim-mumbai-390.png),
  [Hyderabad phone](phase7-vayusim-hyderabad-390.png).

### Frozen identity and unchanged science

| Set | Files | Before SHA-256 | After SHA-256 |
| --- | --- | --- | --- |
| Phase 3A.2 | 316 | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` |
| Phase 4 | 776 | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` |
| Phase 5 question/relevance file | 1 | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` |

All four Phase 5 evaluation files also match their before snapshot. All 38
pre-existing scientific report/screenshot files and all six physics/preset files
are byte-identical to the baseline. The 131 archived Phase 6B artifacts retain
their manifest hashes. Example runs 62–64 retain their original inputs hashes,
every summary value and grid bytes; peaks remain 15.641839027404785,
11.536741256713867 and 18.990890502929688 µg/m³ respectively.

The historical validation journal prefix is retained. Detailed checks and
screenshot identities are in [PHASE7_CHECKS.json](PHASE7_CHECKS.json); the local
raw evidence archive is `data/results/phase7/manifest.json`. Final commit
arguments, actual output, commit ID and tracked-worktree status are retained
locally in `data/results/phase7/final-git.json`, outside the commit to avoid a
self-referential hash. No push is performed.

## Remote and remaining actions

`git remote` and `git branch -r` return no configured remote or remote-tracking
branches. Local history contains Phase 6A `b5136b2`, audit `05ef914`, fix
`c154eaa`, independent references `b29083f`, and Phase 6B `25be37b`. Whether any
were published elsewhere is **unverified**. This task performs no push.
To publish later, the owner must configure the intended remote and push the
reviewed branch. Fresh-machine historical demos need the retained database and
ignored artifacts; external hosting also requires the deployment work listed in
DEPLOYMENT.md. No user action is needed to view this already running local app.
