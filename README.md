# EnviroInsights-India

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
2020–2023. Phase 3B research, forecasting, RAG, simulators and dashboards are deferred.
