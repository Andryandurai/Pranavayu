# EnviroInsights-India

Phase6A adds **VayuSim**, an educational, source-specific Gaussian dispersion
engine with archived weather, WorldPop2025 exposure, saved scenarios and a
verification map. The website now has consistent desktop/mobile navigation:
[Overview](http://localhost:8000/), [Forecasts](http://localhost:8000/forecasts/),
[Research](http://localhost:8000/research/), [Library](http://localhost:8000/library/),
[Ask](http://localhost:8000/ask/) and [VayuSim](http://localhost:8000/simulator/).
Read [the Phase6A report](docs/results/PHASE6A.md) for actual verification and
limitations. Forecast cards show archived replay dates; research comparisons
do not establish causation or official NCAP compliance.

VayuSim inputs are explicit scenario assumptions, not measured facility
inventories. All five source-family presets require emission rate, release
height, diameter, exit velocity and temperature where no defensible universal
default was established. Real weather uses the UTC midpoint of the selected
IST hour. Station totals stay separate from the modelled increment. The
population calculation is **hourly added exposure**, with fractional raster
support; missing population is not extrapolated across unknown area.

The default grid is10km×10km at50m, with an AEQD CRS and a wind-rotated affine.
`POST /api/vayusim/run/` returns summary, GeoJSON contours and binary/header/PNG
URLs. `POST /api/vayusim/day/` uses a timezone-aware datetime to select an IST
date and returns24 independent hourly summaries; missing hours remain
unavailable, and grids are materialised on their first request. Share scenarios
through `/simulator/?scenario=<slug>`. Explain uses a stored `run_id`; arbitrary
client numbers never become verified evidence.

The Windows test wrapper and Makefile force test settings, extractive answering
and a `/tmp` Hypothesis cache, so enabling the local language model cannot make
tests call it. Tests retain the real PostgreSQL and Celery integration. On this
machine the measured memory gate enabled Qwen2.5:3b-instruct; source-model caches
and all project data remain on D:. The assistant can take minutes on CPU and
retains refusal, citation and replay limitations.

Phase 5 adds the [cited research assistant](#phase-5-cited-research-assistant),
available at [Ask](http://localhost:8000/ask/). It uses real document passages
and recorded project results, with extractive answers available without API keys.

Phase 4 forecasting commands run from `D:\EnviroInsights-India` in the web
container. Forecasts are daily city PM2.5, issued at end-of-day IST for t+1–t+3.
They explicitly use replay mode until an OpenAQ key and fresh complete-day
observations are available. Bengaluru uses its seven-site fixed panel.

```powershell
.\scripts\dev.ps1 up
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 manage fetch_historical_forecasts
.\scripts\dev.ps1 manage train_forecasters
.\scripts\dev.ps1 manage evaluate_forecasters
.\scripts\dev.ps1 manage issue_forecasts
.\scripts\dev.ps1 manage issue_forecasts --replay-date 2025-12-31
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
```

Read the frozen [forecast protocol](docs/results/PHASE4_PROTOCOL.md) and
[Delhi/Pune bias investigation](docs/results/PHASE4_BIAS.md). After training,
`export_phase4_report --run <id>` exports `docs/results/PHASE4.md` and actual
figures/tables under `data/results/<id>/`. Evaluation scores come from saved
monthly rolling predictions, with observed-weather perfect-prognosis kept separate.
Forecast versions and predictions reference their AnalysisRun and MLflow run.
The MLflow service is available at `http://localhost:5000`; SQLite metadata and
artifacts persist in `data/mlflow/` on D: and are ignored by Git.

The completed [Phase 4 report](docs/results/PHASE4.md) uses AnalysisRun 21:
7,728 real/ideal prediction rows, 147 registered versions and 148 passing tests.
Nine city/horizon issued policies lose to persistence. Empirical intervals often
undercover; read the measured tables before interpreting uncertainty or skill.

Read-only endpoints are `/api/forecast/<city>/latest/`,
`/api/forecast/<city>/history/?start=YYYY-MM-DD&end=YYYY-MM-DD` (inclusive target
dates, at most 366 days), and `/api/forecast/<city>/evaluation/`. Latest/history
include replay/live mode, three horizons, bounds, PM2.5 category, model version
and top five conditional SHAP drivers. The category is the PM2.5 subindex,
not overall CPCB AQI. Evaluation never serves perfect-prognosis as headline skill.

The daily PM refresh runs at 23:35 IST and requests ten days of readings through
the current instant. Public forecast weather is refreshed at 23:40 IST; issuance
runs at 00:10 IST for the latest completed day. Absent a key, fresh issue-time
readings, complete lag inputs or weather, it replays the latest archived day.
Only readings ingested before that day's cutoff enter live inputs. Saved training
calibration radii are retained when issuing forecasts. Bengaluru additionally
requires verified source station IDs matching its fixed panel; a provider's
different station IDs do not establish that correspondence.
Add `OPENAQ_API_KEY` only to ignored `.env`
and recreate containers to enable keyed ingestion. Historical publication delays,
missing forecast BLH, station changes and seasonal interval calibration remain
limitations; see the protocol and generated report before using predictions.

The active Windows checkout is `D:\EnviroInsights-India`. Docker's registered WSL
VM is at `D:\DockerDesktopData\main`, and its image/container/volume data disk is
at `D:\DockerDesktopData\disk`. Compatibility junctions at the former Docker
AppData paths preserve Docker Desktop's expected locations. Run project commands
from the D: checkout, and reopen that folder in the editor when switching workspaces.

A Django foundation for research on India's air quality. Phase 1 provides a spatial
reference catalogue, time-series storage, document metadata, curator admin,
read-only API, and background-task infrastructure. Phase 2 loads traceable public
observations. Phase 3A audits quality, builds analysis datasets and reports descriptive
statistics and meteorological normalisation. Synthetic measurements belong only in tests.

Requires Docker Engine/Desktop with **Linux containers**, Docker Compose v2, and GNU
Make, or the included PowerShell wrapper on Windows. Python 3.12 and GeoDjango's native
libraries are installed inside the application image. On Windows, use Docker Desktop
with the WSL 2 backend and Linux containers. Reserve several GB for the database image.

## Quick start

```sh
git clone <your-repository-url> enviroinsights-india
cd enviroinsights-india
cp .env.example .env
# Edit .env: set a random DJANGO_SECRET_KEY, POSTGRES_PASSWORD,
# the matching URL-encoded password in DATABASE_URL, and FLOWER_BASIC_AUTH.
make up
make migrate
make seed
make superuser
make health
make verify-worker
```

Generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
The example values must be replaced. `.env`, media, local tools and caches are ignored.
Worker, Beat and Flower wait for migrations for up to five minutes and restart if
they time out. The web server supports autoreload. `make down` preserves data volumes.
Use one Beat instance to avoid duplicate scheduled tasks; Phase 1 installs no ingestion schedules.

The seed creates seven pollutant definitions, twelve sources, twelve cities and ten
parent states. Running it again updates published pollutant/source metadata and
preserves curated city data. It creates no stations, readings, weather, fires or PDFs.
See [reference provenance](docs/REFERENCE_DATA.md) for units and averaging periods.

| Service | URL / connection |
| --- | --- |
| Home placeholder | http://localhost:8000/ |
| Curator admin | http://localhost:8000/admin/ |
| Infrastructure health | http://localhost:8000/api/health/ |
| Swagger UI | http://localhost:8000/api/docs/ |
| OpenAPI schema | http://localhost:8000/api/schema/ |
| City / station GeoJSON | http://localhost:8000/api/cities/ and /api/stations/ |
| Pollutants | http://localhost:8000/api/pollutants/ |
| Flower, with configured Basic authentication | http://localhost:5555/ |
| PostgreSQL 16 | localhost:5433, credentials from `.env` |
| Redis | localhost:6380 |

Published ports bind to loopback. All container connections use service names `db`
and `redis`. Host port changes do not change container URLs. Set
`DJANGO_CSRF_TRUSTED_ORIGINS` to match a changed browser web port.
The default `POSTGRES_PORT=5433` leaves a native Windows PostgreSQL service on 5432
running. Compose's `DATABASE_URL` stays at `db:5432`. Any separate host application
must use `127.0.0.1:5433` with the matching credentials; run this project's tests
inside the web container.
Similarly, `REDIS_PORT=6380` coexists with a native Redis service on 6379. Container
Redis/broker URLs continue to use `redis:6379`; host applications use port 6380.

## Verification

```sh
make lint          # ruff check and format check
make schema        # OpenAPI validation; warnings fail
make test          # checks, migration drift, full pytest suite on a fresh test DB
make health        # real DB/extensions/Redis/worker probe
make verify-worker # broker task + persisted successful IngestionRun with zero rows
```

Tests use `enviroinsights.settings.test` and PostgreSQL with all three extensions,
never SQLite. The database role must create the isolated `TEST_DATABASE_NAME` and
extensions. Full tests require a running Compose worker for the live health probe
and Redis for a dedicated test worker. That worker consumes a unique queue against
the test DB; the ordinary Compose worker cannot consume test tasks. No integration
test silently skips missing infrastructure. Unit tests alone can be selected with
`pytest -m 'not integration'`, but they do not establish live service readiness.

The suite verifies fresh migrations, PostgreSQL major version, extension versions,
all hypertables and unique indexes, duplicate rejection, reversible hypertable
migration, vector dimensions/cosine ordering, HNSW/full-text indexes, seed
idempotence, GeoJSON, read-only API/admin behavior, bounded admin counts, and a
real broker/worker round trip. GitHub Actions runs the complete Compose sequence.

The database init SQL loads and reports PostGIS, TimescaleDB and vector. Django
extension migrations also run in fresh/test databases, before spatial/vector
tables. To inspect the actual installed versions:

```sh
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT extname, extversion FROM pg_extension ORDER BY extname;"'
```

If any extension fails to load, inspect `docker compose logs db` and the selected
image's installed extensions/preload configuration. Do not replace the stack with
a plain PostgreSQL or a test fake. The HA image's data directory is
`/home/postgres/pgdata/data`, where the named volume is mounted.

## PowerShell without Make

`scripts/dev.ps1` mirrors every Makefile target and runs from the project directory
even when invoked elsewhere. It quotes paths, so a folder name containing spaces
does not require renaming. It also finds standard per-user/all-users Docker Desktop
installations when the current shell's PATH predates installation.

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
# Fill in secret placeholders if this is a newly copied .env.
.\scripts\dev.ps1 up
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 seed
.\scripts\dev.ps1 superuser
.\scripts\dev.ps1 health
.\scripts\dev.ps1 verify-worker
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
.\scripts\dev.ps1 schema
```

Other wrapper targets: `shell`, `logs`, `down`. A failing external command stops
the wrapper and returns a failure; the `test` target runs checks, migration drift
and the entire suite inside `web`, explicitly selecting test settings with `--ds`
so Compose's development environment cannot override pytest's configuration.
Docker command temporary files also stay under the active project's `.tools/temp`.
Native stderr stays visible; the wrapper uses the real exit code so informational
Python/Docker logs do not falsely fail a successful command on PowerShell 5.1.
`down` preserves volumes. Run commands normally;
if PowerShell reports an execution-policy error, use a process-only invocation:
`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 test`.

For host-side Python development,
create a Python 3.12 virtual environment, install `requirements/dev.txt`, install
GDAL/GEOS/PROJ, and change `DATABASE_URL`, `REDIS_URL` and `CELERY_BROKER_URL` to
the loopback ports in that host process's environment. For PostgreSQL that is
`postgis://enviroinsights:<URL-encoded-password>@127.0.0.1:5433/enviroinsights`;
do not replace the Compose `.env` value of `db:5432` with a localhost address.
Optional GIS library paths are documented in `.env.example`.

## Settings and deployment boundary

`base`, `dev`, `prod` and `test` settings are separate. Production requires a long
random secret and enables secure cookies, HTTPS redirect and HSTS. Build with
`--build-arg INSTALL_DEV=false`, run Gunicorn with `enviroinsights.wsgi:application`,
and supply `DJANGO_SETTINGS_MODULE=enviroinsights.settings.prod`. Configure an HTTPS
proxy, static/media serving, backups and a separate least-privilege runtime database
role before deployment. The development Compose database role is a superuser for
extension migrations and disposable test database creation. Use a privileged
migration role separately in production. Only enable `DJANGO_TRUST_PROXY` for a
proxy that strips client-supplied forwarding headers. Compose is a development
stack, not an HA or production deployment.

All Python dependencies, including transitive dependencies, are pinned in
`requirements/base.txt` and `requirements/dev.txt`. `.in` files are the update
inputs; regenerate intentionally with `uv pip compile --python-version 3.12
--universal`. Pre-commit uses the same Ruff version as the development lock.
The database image follows the requested `timescale/timescaledb-ha:pg16` tag; pin
its verified digest before deploying a reproducible production environment.

Read [architecture](docs/ARCHITECTURE.md), [data model and decisions](docs/DATA_MODEL.md)
and [validation record](docs/VALIDATION.md) before Phase 2.

## Phase 2 ingestion

Ingestion, time/units, quality flags and bulk insertion live in `apps/ingest/`.
Public inputs cache under `data/raw/` with SHA256 manifests; keyed pipelines skip
cleanly without credentials. Read [DATA_SOURCES.md](docs/DATA_SOURCES.md) for
licences, verified layouts and gaps.

```powershell
.\scripts\dev.ps1 manage download_sources
.\scripts\dev.ps1 manage ingest_all
.\scripts\dev.ps1 manage data_completeness --output .tools/phase2-validation/completeness.json
.\scripts\dev.ps1 manage backfill_weather --start 2015-01-01 --end 2026-10-03
```

`manage` forwards Django commands/arguments inside `web`. Commands include
`load_cpcb_archive`, `load_opencity`, `load_boundaries`, `register_worldpop`,
`backfill_openaq`, `backfill_firms` and optional `backfill_era5`. `ingest_all`
creates admin-editable OpenAQ hourly, FIRMS six-hourly and weather daily Beat
schedules while preserving curator edits.

Read-only APIs: `/api/readings/?station=&pollutant=&start=&end=`,
`/api/weather/?city=<slug>&start=&end=`, `/api/fires/?bbox=&start=&end=` and
`/api/completeness/`. Observation responses use 100-row cursor pagination, a
31-day maximum and an exclusive end. Supply timestamps with explicit offsets.
Missing stays null. The ingestion coverage measure counts finite values, including
flagged ones; Phase 3A uses the stricter clean-data coverage below.

## Phase 3A audit and analysis

Run from `D:\EnviroInsights-India`; all commands execute inside the containers:

```powershell
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 manage run_phase3a --enqueue
# Individual maintenance steps:
.\scripts\dev.ps1 manage reflag_readings
.\scripts\dev.ps1 manage build_analysis_tables
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
```

`run_phase3a --enqueue` submits the real Celery task and waits for its result.
Omit `--enqueue` to run the same pipeline synchronously inside `web`. The full
local dataset takes approximately 15 minutes. Run one analysis job at a time.
Defaults are 100 RF trees, 300 joint observed donor samples and seed 42. A run
records the local Git revision, code hash, package versions, dates and status.
The task has its own four-hour soft limit rather than ingestion's five-minute limit.

The audit updates only quality flags, uses cached original quarters and verifies
that measurement/provenance fingerprints remain unchanged. Zero flatlines and
equal hourly means with varying quarters no longer trigger stuck. Five unverified
sites are excluded pending official GPS evidence. WorldPop 2025 is registered
as default; the retained 2030 projection is not default.

Versioned materialised tables average quality-OK readings per station/IST hour,
then equally across eligible stations. Daily means require 18 valid hours; monthly
means require 75% of calendar days. Analysis-eligible years require 75% valid hours
and 75% valid days. Weather joins at the UTC timestamp of the local hour's midpoint.
Calendar gaps remain null and never become training observations or predictions.

```python
from apps.analytics.aggregation import analysis_dataframe

df = analysis_dataframe("delhi")  # latest successful Phase 3A run; joined weather
```

Read-only APIs use the latest successful full analysis run, or explicit `?run=<id>`:

- `/api/analytics/coverage/?city=delhi&pollutant=pm25&limit=1000`
- `/api/analytics/city/delhi/summary/`
- `/api/analytics/city/delhi/series/?kind=raw&freq=daily`
- `/api/analytics/city/delhi/series/?kind=deweathered&freq=monthly&start=2024-01-01&end=2026-01-01`

`start` is inclusive and `end` exclusive. Series/coverage use limit/offset
pagination (100 by default, capped at 1000). Invalid options return 400; writes
return 405. All metrics/series link to their `AnalysisRun`; earlier runs remain
available. Standalone maintenance runs do not replace the API's full analysis run.

Actual results, figures, model performance and limitations are in
[docs/results/PHASE3A.md](docs/results/PHASE3A.md). CSVs, fitted models and SVG/PNG
figures are local under `data/results/<run_id>/`; only `manifest.json` is eligible
for Git. The descriptive comparisons are not causal effects. Models use observed,
complete-case hours only and a blocked holdout; they do not forecast or bridge
2020–2023. Phase 3B uses the corrected snapshot described below. Forecasting and
RAG were deferred at the Phase 3A handoff and are covered in the later phase
sections. Simulators and dashboards remain deferred.

## Phase 3A2: corrected deweathering method

Use this method for the audited PM2.5 snapshot. The Phase 3A command above is
retained for legacy comparisons; it uses the old clock interpretation and terminal
holdout. The corrected method does not begin Phase 3B research.

```powershell
# Reconstruct and audit the corrected observed series; note the returned data-run ID.
.\scripts\dev.ps1 manage diagnose_deweathering
# Substitute that ID; note the returned model-run ID.
.\scripts\dev.ps1 manage run_phase3a2 --data-run 6
# Substitute the model-run ID in both commands.
.\scripts\dev.ps1 manage supplement_phase3a2 --run 7
.\scripts\dev.ps1 manage export_phase3a2_report --run 7
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
```

`run_phase3a2` without `--data-run` creates a new diagnostic data run first.
Run one full model job at a time. Fixed seeds, the eight prespecified variants,
readiness criteria and identical pooled reference-weather donors are recorded in
[PHASE3A2_PROTOCOL.json](docs/results/PHASE3A2_PROTOCOL.json). The model grid takes
substantially longer than the legacy single-model run. The hourly supplement is
descriptive and does not change selection, thresholds or normalised values.

Independent same-site comparisons in all seven recent cities establish that the
OpenCity exports' `+0000` labels contain IST wall clocks. The corrected analysis
converts those clocks to UTC, reuses the audited native IST four-quarter means,
and joins UTC weather at IST-hour midpoints. Phase 3B has now moved the verified
fix into ingestion and stored UTC timestamps. Raw CSV labels remain unchanged
for provenance; clock-version markers prevent applying the shift twice.
Archived runs 2 and 7 retain their original versioned results.
`diagnose_deweathering --clock-shift-hours 0` reproduces the literal-UTC sensitivity
case, rebuilding quarter bins across UTC-hour boundaries. It is not the corrected
default. See [PHASE3A2_CLOCK_PROOF.json](docs/results/PHASE3A2_CLOCK_PROOF.json).

Successful full `phase3a2` runs become the analytics API and pandas-helper default;
diagnostic, failed and running jobs do not. Earlier full runs remain addressable
with `?run=2`. Phase 3A2 stores PM2.5 diagnostics and series; use the legacy full
run explicitly for other pollutants and its older descriptive metrics. Read the
[actual diagnostic report](docs/results/PHASE3A2.md) before using normalisation:
passing execution or random-hour fitting does not mean passing readiness, and
its original normalised bootstrap intervals exclude model-refit and network uncertainty.

## Phase 3B: observed-data research

The timestamp repair is an idempotent management command. It retains raw values,
quality flags, original ingestion links and cached publisher files. The bulk repair
uses partition-aware routing when a timestamp crosses a Timescale chunk boundary.
New OpenCity exports require verified clock evidence before canonical ingestion.
The corrected warehouse timestamps are safe for direct UTC reads; forecasting is
not implemented in this phase.

```powershell
.\scripts\dev.ps1 manage correct_stored_clocks
# Existing canonical diagnostic/data snapshots: 8 and 9.
.\scripts\dev.ps1 manage run_phase3b --diagnostic-run 8 --stored-run 9
# Use the completed research-run ID printed by the command.
.\scripts\dev.ps1 manage export_phase3b_report --run <research-run-id>
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
```

If rebuilding snapshots, run `diagnose_deweathering`, then
`rebuild_research_tables --diagnostic-run <new-diagnostic-id>` and use the returned
IDs. The table rebuild checks PM2.5 equivalence against frozen Run 7 and verifies
NCAP reference flags against the retained official library document.

Run one research command at a time. Completed city runs with the same frozen
protocol/data IDs are reused after an interruption. Each city records nested
whole-week validation, a weather-only RF/GAM comparison, 20 actual bootstrap model
refits, seasonal exact SHAP/ALE, monthly trend tests and descriptive comparisons.
Bengaluru uses its fixed panel; unsupported panels and years remain unavailable.
Both eras use the same pooled reference weather. Research outputs include refit
series, sampled-index hashes, CSV tables, models, figures and manifests under
`data/results/<run_id>/`.

Read-only endpoints publish only completed full Phase 3B research runs:

- `/api/analytics/rq2/delhi/`
- `/api/analytics/ncap/`
- `/api/analytics/comparisons/`

They accept `?run=<id>` for a completed research run. Other cities are labelled
descriptive only. NCAP outputs are explicitly a **PM2.5 proxy for NCAP progress**,
with official compliance marked **not assessed**. Missing historic PM10 and the
fiscal/calendar baseline mismatch prevent official compliance conclusions.
Chennai participates as a million-plus city but is outside the non-attainment
classification in the verified CPCB list; its reference flag is corrected.

The paper and actual research results are in
[docs/results/PHASE3B.md](docs/results/PHASE3B.md). Primary reference documents and
their download hashes are catalogued in
[docs/RESEARCH_LIBRARY.md](docs/RESEARCH_LIBRARY.md). Weekly interpolation skill is
not forecasting validation, and weather-adjusted changes do not identify policy
effects. BS-VI attribution needs the missing intervening concentrations; crop-fire
analysis is deferred pending FIRMS data.

## Phase 5: cited research assistant

Open [Ask](http://localhost:8000/ask/) for a minimal question box, provider badge
and clickable source citations. Literature answers quote retrieved evidence;
data answers use eight validated, read-only tools. Missing evidence produces an
explicit refusal. Current forecasts are identified as live or archival replay.
Read [PHASE5.md](docs/results/PHASE5.md) for measured performance and corpus limits.

Verified corpus: 29 actual document bodies (24 public and five internal),
7,194 indexed chunks and four unavailable requests. The full suite passes
183 tests; the frozen 120-question evaluation is logged in MLflow's `rag`
experiment. No generative provider ran on this machine.

```powershell
.\scripts\dev.ps1 up
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 manage download_rag_library
.\scripts\dev.ps1 manage prepare_rag_models
.\scripts\dev.ps1 manage ingest_rag_library
# Submit selected registered documents to the real Celery worker:
.\scripts\dev.ps1 manage ingest_rag_library --enqueue --ids 1
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
```

Public bodies are hash-addressed under `data/raw/rag/`; Git retains only the
manifest and source specifications. Download failures are explicit, not empty
documents. The BGE encoder/reranker weights and deterministic computation caches
persist on D: under `data/models/`. The internal `rag-models` service serializes
CPU inference with one model loaded at a time. Parsing and completed embedding
batches survive an interrupted command. Unchanged content with the same parser
version is a no-op; an incompatible parser fix requires an explicitly versioned
index rebuild. After upgrading ingestion code, restart the Celery worker before
submitting new tasks so it imports the current parser.

Upload and tag a PDF at `/admin/rag/document/add/` to queue ingestion after the
database commit. Existing PDF bodies cannot be replaced; a changed file is a new
SHA256 revision. HTML and Markdown have actual section citations and logical
text pages; PDF citations use physical file pages, not printed-page labels.

`LLM_PROVIDER=auto` selects configured Anthropic, OpenAI, enabled Ollama, then
extractive. Optional remote providers require both their API key and model name
in `.env`; see `.env.example`. Extractive works without keys. This machine does
not meet the requested 12 GB free-container condition for Ollama, so its optional
`llm` profile is disabled. Do not download a local LLM without rechecking memory.

API examples:

```json
POST /api/rag/ask/
{"question":"What was the annual mean PM2.5 in Delhi in 2025?"}

POST /api/rag/explain/
{"context_type":"forecast","payload":{"city":"delhi"}}

POST /api/rag/explain/
{"context_type":"scenario","payload":{"question":"What assumptions does AERMOD use?","scenario_id":"example"}}
```

`ask` accepts optional filters `category`, `year_min`, `year_max`, `city` (seeded
slug). `GET /api/rag/documents/` lists sources and ingestion status;
`GET /api/rag/documents/<id>/page/<n>/` exposes stored page text and provenance.
Explain payloads select evidence; supplied scenario/chart values are not verified
measurements or simulation results. Phase 6 must validate its actual scenario
outputs before using them as numerical evidence. This phase builds no simulator.

The checked-in `data/eval/rag_eval.jsonl` has frozen real-source and database
expectations. `evaluate_rag` resumes saved question/provider results under
`data/results/rag-phase5/` and logs them to MLflow's `rag` experiment. Do not
overwrite frozen questions in response to poor scores. `build_rag_eval` refuses
to overwrite an existing evaluation file; its input is the authored question
catalogue, with exact source excerpts verified against real stored chunks.
