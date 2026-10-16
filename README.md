# EnviroInsights-India

EnviroInsights-India is a Django research project for inspecting Indian air-quality
observations, weather associations, daily PM2.5 forecasts, cited documents and
educational source-dispersion scenarios. It separates observations, fitted
estimates and evidence that is missing.

Working: a provenance-aware warehouse, stored-results dashboard, retrospective
analytics, archived-replay forecasting, extractive retrieval with verified
citations, and VayuSim. The dated warehouse snapshot contains **17,504,928 combined
rows**: **16,266,240 concentration rows**, including missing/flagged rows, and
**1,238,688 weather observations**. It is not complete national coverage.
[Source](docs/results/PHASE7_DATA.json).

Not established: urban C/F plume performance, causal BS-VI attribution, fire
effects, useful local-LLM answer quality, interval coverage everywhere, or live
forecast operation without fresh keyed observations. Serving uses persistence for the nine city-horizon combinations where Phase 4 found that the model lost to persistence; the model is used for the others. This serving override was added after Phase 7; it does not revise the Phase 4 backtest. [Fix record](docs/results/PHASE7_FIX.md).

## Open the project

| Page | Purpose |
| --- | --- |
| [Dashboard](http://127.0.0.1:8000/dashboard/) | Stored figures, source files and failure flags |
| [Overview](http://127.0.0.1:8000/) | Navigation and dated stored outlooks |
| [Forecasts](http://127.0.0.1:8000/forecasts/) | Replay dates, bounds and model provenance |
| [Research](http://127.0.0.1:8000/research/) | Cohorts, descriptive comparisons and uncertainty |
| [Library](http://127.0.0.1:8000/library/) | Stored documents and source passages |
| [Ask](http://127.0.0.1:8000/ask/) | Extractive retrieval with verified citations |
| [VayuSim](http://127.0.0.1:8000/vayusim/) | Hypothetical increments; urban C/F warnings |
| [Health](http://127.0.0.1:8000/api/health/) | Database/extensions, Redis and Celery |

Each dashboard figure links to a stored evidence file. Original raw bodies, large
results, model weights and the database are not bundled in Git. A fresh checkout
can display the committed dashboard snapshot; historical interactive queries and
saved scenarios require the retained data/database. [Restoration](docs/DEPLOYMENT.md).

## Windows quick start

Use Docker Desktop with **WSL 2 and Linux containers**. Install WSL with
`wsl --install` if absent, enable “Use WSL 2 based engine”, restart when required,
and wait for the engine. Check `docker version`, `docker info` (`OSType: linux`)
and `docker run --rm hello-world`.

Work from `D:\EnviroInsights-India`. The recorded 16 GiB laptop has
`[wsl2] memory=9GB` in `%UserProfile%\.wslconfig`: 60% of memory, rounded down.
That is machine-specific, not proof that a model fits. A pre-change original
configuration could not be recovered. [Audit](docs/results/PHASE6A.md#fix-pass).

```powershell
Set-Location -LiteralPath 'D:\EnviroInsights-India'
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item '.env.example' '.env' }
# Fill the secrets below before starting.
.\scripts\dev.ps1 up
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 seed
.\scripts\dev.ps1 health
.\scripts\dev.ps1 verify-worker
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
```

Set a random `DJANGO_SECRET_KEY` of at least 50 characters, `POSTGRES_PASSWORD`,
the matching URL-encoded password in `DATABASE_URL`, and `FLOWER_BASIC_AUTH`.
Inside Compose the database is **db:5432**; host clients use **127.0.0.1:5433**.
Keep `.env` out of Git. No paid key is required for the default application.
Defaults: `LLM_PROVIDER=extractive`, `OLLAMA_ENABLED=false`, empty
`COMPOSE_PROFILES`. The experimental Ollama `llm` profile is opt-in.

Other wrapper targets: `down`, `logs`, `shell`, `superuser`, `schema`, and
`manage <command>`. `down` preserves volumes; avoid `down -v` on retained data.
The seed creates reference metadata, not observations or model artifacts.
Compose runs a development server. A deployment-settings check is not hosting.

## Data sources and recorded access

These are recorded licence/access declarations; review terms for a different
use. Detailed provenance is in [DATA_SOURCES.md](docs/DATA_SOURCES.md).

| Source | Recorded licence/access | Used | Skipped or limited |
| --- | --- | --- | --- |
| Princeton CPCB / XKDR | CC BY 4.0 metadata; original delivery needs Globus | XKDR historical PM2.5 alternative, 2015–2019 | Original bodies unavailable; other historical pollutants absent |
| OpenCity / CPCB boards | Catalogue “Other (Public Domain)”; retain resource terms | 2024–2025 concentration exports | Older AQI matrices excluded; never inverted to concentrations |
| Open-Meteo / ERA5 | Recorded CC BY 4.0; public non-commercial API | Historical city-grid weather | Not instrument meteorology; null BLH stays explicit |
| Open-Meteo Previous Runs | Public archive, documented lead semantics | GFS lead-offset forecast weather | Stitched near-valid-time history excluded from headline features |
| Datameet | CC BY 4.0 | Census-vintage boundaries | Not a current surveyed boundary guarantee |
| WorldPop | CC BY 4.0; release-specific attribution | Registered 2025 raster | Not a census or citywide health-impact estimate |
| OpenAQ | API key and provider terms | Adapter/tests only | Keyed live ingestion skipped; live forecasting unverified |
| NASA FIRMS | MAP_KEY and product attribution | Adapter/tests only | Keyed retrieval skipped; no fire-effect estimate |
| CDS ERA5 | Token and accepted dataset licence | Adapter/tests only | Keyed retrieval skipped; public Open-Meteo alternative used |
| Research PDFs/plans | Publisher-specific rights | Retained Phase 5 corpus and source passages | Missing downloads recorded; public access is not a blanket reuse licence |

## Limitations, in claim order

1. **VayuSim urban C/F are unvalidated branches.** The Delhi, Mumbai and Hyderabad
   examples use hypothetical 1 g/s releases. Unchanged peaks are 15.641839,
   11.536741 and 18.990891 µg/m³. Primary PM2.5, flat terrain and steady hourly
   conditions apply. These are educational estimates, not regulatory assessments
   or AQI. [Examples](docs/results/PHASE6B_METRICS.json).
2. **Briggs–Martin comparison exceeds tolerance.** Differences of 14.13% in σy,
   15.60% in σz and 10.66% in concentration are scheme differences, not validation
   errors or a passing comparison. Formula checks and the limited rural-D numeric
   case do not establish urban performance. Turner physical pages are unverified.
   [Audit](docs/results/PHASE6A.md#independent-validation).
3. **The assistant is extractive retrieval with verified citations.** Exact-support
   and numeric matching scores are not comprehensive semantic answer-quality
   evidence. The opt-in local LLM failed its quality gate: 2/80 literature answers
   and 0/30 available-data answers retained. [Phase 5](docs/results/PHASE5.md),
   [later provider record](docs/results/PHASE6A.md).
4. **Forecast skill is uneven.** Delhi next-day RMSE improves on persistence by
   12.6% in the rolling backtest. Nine policies lose; the versioned serving override now uses persistence for them. This does not establish prospective fallback skill. Fourteen selected interval levels fail the five-point
   coverage gate. Replay is not live operation, and post-evaluation interval
   selection is not independent evidence. [Phase 4](docs/results/PHASE4.md),
   [coverage](docs/results/PHASE6A.md).
5. **Frozen evaluations are unchanged.** Before/after hashes cover Phase 3A.2,
   Phase 4 and Phase 5. Delhi's fixed-panel difference is −17.59 µg/m³ with refit
   interval [−35.07, +1.66], so direction is inconclusive under this procedure.
   Hyderabad's 0 versus 53 exceedance days depends on cohort. The archive gap
   blocks BS-VI attribution; missing FIRMS data block the fire question.
   [Phase 3B](docs/results/PHASE3B.md).

## Results and handoff

- [Phase 3A](docs/results/PHASE3A.md), [Phase 3A.2](docs/results/PHASE3A2.md),
  [Phase 3B](docs/results/PHASE3B.md).
- [Phase 4](docs/results/PHASE4.md), [protocol](docs/results/PHASE4_PROTOCOL.md),
  [bias investigation](docs/results/PHASE4_BIAS.md).
- [Phase 5](docs/results/PHASE5.md), [Phase 6A](docs/results/PHASE6A.md),
  [Phase 6B](docs/results/PHASE6B.md), [Phase 7](docs/results/PHASE7.md),
  [serving fix](docs/results/PHASE7_FIX.md).
- [Write-up](docs/results/WRITEUP.md), [five-minute demo](docs/DEMO.md),
  [resume lines](docs/RESUME.md), [deployment](docs/DEPLOYMENT.md).
- [Architecture](docs/ARCHITECTURE.md), [data model](docs/DATA_MODEL.md),
  [command journal](docs/VALIDATION.md).

Source repository: [Andryandurai/Pranavayu](https://github.com/Andryandurai/Pranavayu)
(private; GitHub access required). Earlier phase reports retain the remote state
at their audit dates. Git contains the source, tests and committed evidence;
the retained database, large artifacts and local secrets need separate backups.
