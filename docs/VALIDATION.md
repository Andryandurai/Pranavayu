# Phase 1 live verification

Recorded 7 October 2026 (Asia/Kolkata). **All nine verification steps passed.**
All project commands and edits now use **D:\EnviroInsights-India**. No Phase 2
features were added, and all ten test source files are unchanged by SHA-256 comparison.

## Environment

| Component | Actual verified state |
| --- | --- |
| Active checkout and /app bind mount | D:\EnviroInsights-India |
| Docker Desktop / Engine / Compose | 4.94.0 / 29.8.2 / v5.5.1 |
| Engine context / container mode | desktop-linux / OSType: linux |
| WSL | 3.0.1.0; docker-desktop uses WSL 2 |
| Registered Docker WSL VM | D:\DockerDesktopData\main\ext4.vhdx; WSL registry BasePath points to D: |
| Image, container and volume data disk | D:\DockerDesktopData\disk\docker_data.vhdx |
| Docker compatibility paths | Original AppData wsl\main and wsl\disk directories are junctions to D: |
| Docker CLI temporary files | D:\EnviroInsights-India\.tools\temp, scoped by the PowerShell wrapper |
| Python / Django | 3.12.15 / 5.2.18 in Linux containers |
| PostgreSQL | 16.15 (Ubuntu 16.15-1.pgdg22.04+2) |
| PostgreSQL host / container endpoints | 127.0.0.1:5433 / db:5432 |
| Redis host / container endpoints | 127.0.0.1:6380 / redis:6379 |
| Web / Flower | http://localhost:8000/ / http://localhost:5555/ |

Docker's large VM/data storage and the active checkout are physically on D:.
Docker Desktop's Windows executable and Windows-managed settings/registry metadata
remain in their normal Windows locations. The old C: checkout is retained as a
backup while the client still has it open; it is not serving the containers.

The original space-containing path parsed correctly. Relocation followed the user's
request, not a quoting failure. The project copy was verified against the original:
100 source/environment files had matching SHA-256 hashes before later D: edits.
Docker was stopped before relocation. WSL's own --manage --move command moved its
registered VM; the separate offline data disk was copied and hash-verified before
source removal and creation of compatibility junctions. Docker restarted successfully,
and hello-world passed again from the relocated engine.

## Nine verification steps

| Step | Result | Command and key real output |
| --- | --- | --- |
| 1. Build and services | PASS | docker compose up -d --build; docker compose ps: db and redis healthy; web, worker, beat and flower running |
| 2. Migrations | PASS | docker compose exec -T web python manage.py migrate --noinput: all migrations OK, including core.0001_extensions, rag.0001_initial, warehouse.0001_initial and warehouse.0002_hypertables |
| 3. Seed twice | PASS | seed_reference executed twice: State=10, City=12, Pollutant=7, DataSource=12; second run created no new rows and all reference primary keys were identical |
| 4. Extension versions | PASS | SELECT extname, extversion FROM pg_extension: postgis 3.6.4, timescaledb 2.30.2, vector 0.8.7 |
| 5. Hypertables | PASS | timescaledb_information.hypertables contains warehouse_reading, warehouse_weatherobservation and warehouse_firedetection |
| 6. Health | PASS | Real host GET /api/health/: HTTP 200; top-level ok=true and every database/extension/Redis/Celery check true. PowerShell wrapper health check also passed |
| 7. Real worker task | PASS | scripts/dev.ps1 verify-worker: Worker executed core.tasks.ping: run=1, status=success, rows=0; persisted row confirmed by SQL |
| 8. Full pytest suite | PASS | scripts/dev.ps1 test: checks passed; No changes detected; pytest --ds=enviroinsights.settings.test: 37 passed in 17.00s |
| 9. Ruff and production checks | PASS | scripts/dev.ps1 lint: All checks passed; 79 files already formatted. check --deploy --settings=enviroinsights.settings.prod: System check identified no issues (0 silenced), zero warnings |

All six services remained running after the tests. Main-database Reading,
WeatherObservation and FireDetection counts were rechecked and are all zero.
The worker demonstration records a zero-row infrastructure probe, not a measurement.
Tests use a disposable PostgreSQL database and real Redis/Celery, including a dedicated
worker queue. No synthetic readings were written to the development database.
OpenAPI generation was additionally validated with --validate --fail-on-warn (exit 0).

## Real output excerpts

```text
Engine=29.8.2 OSType=linux Containers=0
Hello from Docker!
This message shows that your installation appears to be working correctly.

       extname       | extversion
---------------------+------------
 plpgsql             | 1.0
 postgis             | 3.6.4
 timescaledb         | 2.30.2
 timescaledb_toolkit  | 1.26.0
 vector              | 0.8.7
(5 rows)

       hypertable_name
------------------------------
 warehouse_firedetection
 warehouse_reading
 warehouse_weatherobservation
(3 rows)

Second seed counts: {'State': 10, 'City': 12, 'Pollutant': 7, 'DataSource': 12}
Second seed created no new rows; reference primary keys are identical.

Worker executed core.tasks.ping: run=1, status=success, rows=0
 id |    task_name    | status  | rows_fetched | rows_inserted | rows_flagged
----+-----------------+---------+--------------+---------------+-------------
  1 | core.tasks.ping | success |            0 |             0 |            0
(1 row)

platform linux -- Python 3.12.15, pytest-9.1.1
settings: enviroinsights.settings.test (from option)
collected 37 items
============================= 37 passed in 17.00s ==============================

All checks passed!
79 files already formatted
System check identified no issues (0 silenced).

 readings | weather | fires
----------+---------+-------
        0 |       0 |     0
(1 row)
```

Actual host HTTP status: **200**. Response:

```json
{
  "ok": true,
  "checks": {
    "database": {"ok": true},
    "extensions": {
      "postgis": {"ok": true, "version": "3.6.4"},
      "timescaledb": {"ok": true, "version": "2.30.2"},
      "vector": {"ok": true, "version": "0.8.7"}
    },
    "redis": {"ok": true},
    "celery": {"ok": true}
  }
}
```

## Failures, root causes, fixes and reruns

1. Docker was initially absent. The user installed Docker Desktop with WSL 2.
   Its CLI was still absent from the old shell PATH, so commands and the wrapper
   resolved the actual per-user installation. Real version, info and hello-world passed.
2. Earlier PostgreSQL authentication errors reached native PostgreSQL 17 on 5432
   (service postgresql-x64-17, PID 6756). Test settings also supplied an unused-password
   localhost URL before reading .env. Published port is now 5433; container URL remains
   db:5432; the bogus test fallback was removed. Migrations and PostgreSQL 16 tests pass.
3. Native Redis occupied 6379 (service Redis, PID 5316). Its container is now published
   on 6380, with internal broker URLs unchanged. Redis health and worker execution pass.
   Both native Windows database/Redis services were left running.
4. Initial image extraction exhausted C: (measured free space 0 bytes), returned
   unexpected EOF, then Docker API 500. VM/data storage and active project work moved
   to D: with offline-copy verification. Docker restarted; image pull/build and the
   complete Compose stack succeeded.
5. A later BuildKit stream returned rpc Unavailable/EOF; logs reported a session
   health-check connection failure, only one connection allowed. The engine subsequently
   responded normally. Building the web image alone succeeded, then the required
   compose up -d --build rerun succeeded. The deeper cause of the transient transport
   interruption was not established; no application or test code was changed to hide it.
6. The first full test run passed 37 tests but selected development settings from
   Compose's environment. Both runners now explicitly pass --ds=enviroinsights.settings.test.
   The rerun used test settings and passed all 37 tests. SHA-256 comparison confirms all
   10 test source files are unchanged.

No previous project volumes existed at startup, so down -v was unnecessary. Fresh
PostgreSQL/Redis/media volumes were created using the existing matching .env credentials.
Username, password and database-name consistency were checked without printing secrets.
No secret replacements, administrator service stops or Windows restart were needed.

## Files changed

- compose.yaml, .env.example and ignored .env: host ports 5433/6380 while retaining
  db:5432 and redis:6379 inside containers.
- enviroinsights/settings/test.py: remove the misleading localhost fallback.
- Makefile: explicitly select the pytest test settings.
- scripts/dev.ps1: mirror every Make target; handle path quoting, CLI discovery and
  failures; select test settings and put temporary Docker CLI files under the D: checkout.
- README.md: Windows commands, ports, D: locations and explicit test settings.
- docs/VALIDATION.md: replace earlier failed results with this live verification record.

Docker relocation also changed host WSL registration and AppData compatibility junctions.
Application models and migrations were not changed. Tests were not changed.

## Remaining action and Phase 2 readiness

**Phase 1 is verified and ready for Phase 2 work. No technical blocker remains.**
Reopen **D:\EnviroInsights-India** in the client to make its visible workspace match
all current commands, edits and running container mounts. Keep the old C: checkout
as a backup until that workspace switch is complete. No reinstall, admin rights or
Windows restart is currently required.

The production deployment check emitted zero warnings; the running development
Compose services continue using development settings. This is foundation verification,
not a production deployment.

Phase 2 should follow [DATA_MODEL.md](DATA_MODEL.md): specify weather/fire identity
and deduplication, reading correction/provenance policy, timezone/unit normalization,
quality flags and verified source licences before downloading real observations.
No Phase 2 implementation was started during the Phase 1 environment task. The
separately authorized Phase 2 work is recorded below.

## Phase 2 live ingestion verification — 2026-10-08

This section records the separately authorized ingestion task. All commands,
code, cached bodies and reports used **D:\EnviroInsights-India**, mounted at
`/app`. Docker data remains under **D:\DockerDesktopData**. No analytics, ML,
RAG or simulator implementation was added.

The public pipelines completed successfully. Every public source was replayed
against the same cached inputs and inserted **zero** rows. The original Princeton
release could not be delivered without Globus sign-in; the historical rows below
are explicitly the public XKDR PM2.5 compilation. Keyed sources skipped cleanly.

Final database snapshot: `2026-10-08T13:20:08.910093+00:00`. It contains **16,266,240 readings**, **1,236,672 weather calendar rows**, and **0 live fire detections**.

### Environment and executed commands

Actual final environment output:

```text
docker version --format '{{.Client.Version}} / {{.Server.Version}}'
29.8.2 / 29.8.2
docker info --format 'OSType={{.OSType}} ServerVersion={{.ServerVersion}}'
OSType=linux ServerVersion=29.8.2
compose services: db/redis healthy; web/worker/beat/flower running
host: PostgreSQL 5433, Redis 6380, web 8000, Flower 5555
container: db:5432, redis:6379
```

The image was rebuilt for the pinned ingestion dependencies. The new
`ingest.0002_ingestion_provenance` migration applied. The final migration rerun:

```text
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, core, django_celery_beat,
  django_celery_results, ingest, rag, sessions, warehouse
Running migrations:
  No migrations to apply.
Reference seed complete: 7 pollutants, 12 data sources, 12 cities. No measurements.
Reference seed complete: 7 pollutants, 12 data sources, 12 cities. No measurements.
```

Commands executed through the Windows wrapper after fixture checks passed:

```powershell
.\scripts\dev.ps1 manage download_sources
.\scripts\dev.ps1 manage ingest_all
# Repeat the repaired inputs; the corrected all-source pass already replayed
# historical air, weather and population with zero additions.
.\scripts\dev.ps1 manage ingest_all --source opencity
.\scripts\dev.ps1 manage ingest_all --source boundaries
.\scripts\dev.ps1 manage data_completeness --output .tools/phase2-validation/completeness.json
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
.\scripts\dev.ps1 manage check --deploy --settings=enviroinsights.settings.prod
.\scripts\dev.ps1 health
.\scripts\dev.ps1 verify-worker
.\scripts\dev.ps1 manage spectacular --validate --fail-on-warn --file .tools/phase2-validation/schema.yaml
```

Download retries reused verified caches. The complete `download_sources` command
ended successfully (runs 47–51); the corrected complete `ingest_all` command also
ended successfully. The full input replays are below, with exact run IDs.

### Downloaded files and integrity

[PHASE2_FILES.csv](validation/PHASE2_FILES.csv) records **every** cached file's
path, exact size, SHA256, URL, retrieval time and truncated-parent status.
Raw bodies are ignored; adjacent manifests are eligible for version control.
There is no Git repository in this checkout, so no commit is claimed.

| Cache group | Files | Exact bytes | Inputs |
| --- | ---: | ---: | --- |
| datameet-maps | 8 | 27,426,050 | 4 state + 4 district shapefile components |
| cpcb-ccr | 864 | 108,061,831 | 860 CSVs, primary registry, contributed coordinates, DOI metadata, catalogue response |
| opencity | 259 | 1,512,837,796 | 247 CSVs + 12 search catalogues |
| openmeteo | 144 | 82,439,663 | 12 cities × 12 yearly JSONs, including partial 2026 |
| worldpop | 2 | 798,145,552 | GeoTIFF + catalogue metadata |

Total: **1,277 files, 2,528,910,892 bytes**. The final audit recomputed every body hash and checked every size: **0 mismatches**. Station registries are shared by both air loaders; physical files are counted once in their cache group.

WorldPop raster: `worldpop/ind_pop_2030_CN_100m_R2025A_v1.tif`; **798,127,525 bytes**; SHA256 `b6c3520df0fefcbf01a75ad7c8de294f5804526f332d0bbe80889b4861eeb3f1`; EPSG:4326; 35,040 × 34,507; one band; nodata −99,999. This is the **2030 constrained R2025A v1 alpha projection**, registered as metadata only.

### Live load totals

These are actual committed totals after the initial loads and repair passes,
not the sum of fetched rows across retries. Flagged totals count the current
warehouse flags, including later promotions to stuck. Air `rows_fetched` counts
input records (OpenCity quarters), while inserted counts are unique hourly
station/pollutant records. Duplicate exports and query-window overlaps do not
create additional measurements. Metadata/reference work is identified separately.

| Source | Status | Files in cache group | Rows fetched by complete load | Committed rows / reference work | Current flagged rows |
| --- | --- | ---: | ---: | ---: | ---: |
| CPCB via XKDR | success; alternative compilation | 864 | 1,490,974 | 1,478,656 readings | 7,421 |
| OpenCity | success | 259 | 59,033,702 quarter records | 14,787,584 hourly readings | 3,057,148 |
| Open-Meteo ERA5 | success | 144 | 1,236,672 | 1,236,672 weather rows | 0 invalid-value records |
| Datameet | success | 8 | 677 features | initial run: 689 geometry/reference/link work units | 0 |
| WorldPop | success | 2 | 1 raster | 1 metadata registration | 0 |
| openaq | skipped: no key | 0 live | 0 | 0 | 0 |
| nasa-firms | skipped: no key | 0 live | 0 | 0 | 0 |
| era5 | skipped: no key | 0 live | 0 | 0 | 0 |

Air repairs retained valid committed batches from partial runs:

```text
run 53 CPCB partial:   fetched=913778   inserted=837780   flagged=6142
run 55 CPCB success:   fetched=1490974  inserted=640876   flagged=1262
run 54 OpenCity partial: fetched=54981367 inserted=13771310 flagged=2687747
run 63 OpenCity success: fetched=59033702 inserted=1016274 flagged=369401
run 56 weather success: fetched=1236672 inserted=1236672 flagged=0
```

CPCB's current 7,421 flagged rows exceed the initial insertion flag counters
by 17 because adjacent-file context later promoted existing rows to stuck;
these promotions are audited in run parameters. Partial/failed runs remain
in the audit history, with their original errors and counts.

### Idempotency proof

The same cached bodies were processed again with the final loaders. Source
replays finished successfully, with both insertion and newly inserted flag
counters zero. No test, mock database or synthetic record supplied these counts.

```text

run 74 datameet-maps: status=success fetched=677 inserted=0 flagged=0 message=

run 62 cpcb-ccr: status=success fetched=1490974 inserted=0 flagged=0 message=

run 69 opencity: status=success fetched=59033702 inserted=0 flagged=0 message=

run 68 openmeteo: status=success fetched=1236672 inserted=0 flagged=0 message=

run 70 worldpop: status=success fetched=1 inserted=0 flagged=0 message=

run 71 openaq: status=skipped fetched=0 inserted=0 flagged=0 message=skipped: no key

run 72 nasa-firms: status=skipped fetched=0 inserted=0 flagged=0 message=skipped: no key

run 73 era5: status=skipped fetched=0 inserted=0 flagged=0 message=skipped: no key

```

### Completeness

[PHASE2_CITY_YEAR_COMPLETENESS.csv](validation/PHASE2_CITY_YEAR_COMPLETENESS.csv)
contains all 144 city/year results, including zeros. The denominator uses IST
calendar hours from 2015-01-01 through 2026-10-07, the last completed local day;
the partial 2026 denominator is 6,720 hours. Non-null nonnegative PM2.5 counts
as present, including finite flagged values. City coverage is the union of
station hours, not average station coverage or validated representative air quality.

Actual command output summary: **23,940 station/pollutant/month entries**, **158,978 station/pollutant/day entries below 18 hours**, and **53 of 144 city-years at least 75% complete**. The full local JSON retains every low-coverage day. [Station-month CSV](validation/PHASE2_STATION_MONTH_COMPLETENESS.csv) records the monthly values.

| City | PM2.5 years with at least 75% of hours |
| --- | --- |
| ahmedabad | 2018 (96.12%), 2019 (93.01%) |
| bengaluru | 2015 (78.09%), 2016 (90.30%), 2017 (95.46%), 2018 (93.41%), 2019 (99.99%), 2024 (99.94%), 2025 (100.00%) |
| chennai | 2016 (91.34%), 2017 (97.95%), 2018 (99.95%), 2019 (99.93%), 2024 (99.94%), 2025 (100.00%) |
| delhi | 2015 (98.33%), 2016 (99.73%), 2017 (100.00%), 2018 (100.00%), 2019 (100.00%), 2024 (99.94%), 2025 (100.00%) |
| hyderabad | 2016 (96.24%), 2017 (99.36%), 2018 (99.95%), 2019 (100.00%), 2024 (99.94%), 2025 (100.00%) |
| jaipur | 2018 (99.91%), 2019 (99.95%) |
| kanpur | 2016 (89.94%), 2017 (87.24%), 2018 (96.30%), 2019 (94.33%) |
| kolkata | 2019 (99.95%), 2024 (99.94%), 2025 (100.00%) |
| lucknow | 2015 (78.20%), 2016 (91.95%), 2017 (89.66%), 2018 (96.85%), 2019 (99.95%) |
| mumbai | 2015 (98.73%), 2016 (95.07%), 2017 (87.58%), 2019 (98.89%), 2024 (99.94%), 2025 (100.00%) |
| patna | 2016 (79.62%), 2018 (96.60%), 2019 (96.68%) |
| pune | 2024 (99.94%), 2025 (100.00%) |

**2020–2023 has no loaded concentration coverage.** Older OpenCity files in
that period are AQI matrices and cannot be converted to concentrations.
Recent concentration exports cover 2024–2025 in seven cities. The five early
IST hours in some 2026 results are the last UTC hours of 2025, not meaningful
2026 monitoring coverage. No 2026 city-year reaches 75%.

Weather has 103,056 calendar rows per city, 2015-01-01 00:00 UTC through
2026-10-03 23:00 UTC. [Weather coverage CSV](validation/PHASE2_WEATHER_COVERAGE.csv)
checks every raw variable: October 3 has all-null weather (288 rows across
12 cities), so October 2 is the latest non-null weather day in this capture.
BLH additionally lacks January–June 2024 (4,368 hours per city); total BLH
nulls are 52,704. These are actual provider nulls, retained without filling.

### Provenance, extensions, boundaries, API and Celery

Actual SQL/ORM audit:

```text
reading station-source / ingestion-run-source mismatches: 0
weather missing or mismatched source/run provenance: 0
fire missing or mismatched source/run provenance: 0 (no live fire rows)
state/district references lacking provenance: 0 / 0
states: 38 references; 36 geometries; historical DN/DD geometries remain null
district features: 641; audited city/district links: 12
invalid stored state/district geometries: 0 / 0
postgis=3.6.4 timescaledb=2.30.2 vector=0.8.7
hypertables: warehouse_reading, warehouse_weatherobservation, warehouse_firedetection
```

All 12 city points matched exactly one district polygon. Hyderabad retains its
2011 Andhra Pradesh district parent; its seeded present-day city state is Telangana.

| Actual HTTP request | Result | Key output |
| --- | --- | --- |
| `/api/health/` | 200 | all database/extensions/Redis/Celery checks true |
| `/api/readings/`, station 131, PM2.5, two days | 200 | 48 real rows; source/run/raw unit present |
| `/api/weather/?city=delhi`, 2019-01-01 to 2019-01-03 UTC | 200 | 48 real rows, BLH and provenance present |
| Same weather endpoint over seven days | 200 | cursor pages 100 + 68; 168 unique rows |
| `/api/fires/`, bbox 73,27,78,33 | 200 | empty result; missing live key recorded, no fake detections |
| `/api/completeness/`, real station and date range | 200 | monthly/day completeness response |
| Weather range longer than 31 days | 400 | maximum-range validation |
| POST `/api/readings/` | 405 | read-only method enforcement |

The real host-port HTTP captures are in ignored
`.tools/phase2-validation/api-final.json` and `api-pagination.json`.

```text
Worker executed core.tasks.ping: run=65, status=success, rows=0
Registered worker tasks:
core.tasks.ping, ingest.openaq_hourly, ingest.firms_six_hourly, ingest.weather_daily
queued ingest.openaq_hourly: run=66 status=skipped message=skipped: no key
queued ingest.firms_six_hourly: run=67 status=skipped message=skipped: no key
```

The database has enabled admin-editable intervals: OpenAQ 1 hour, FIRMS 6 hours,
Open-Meteo 24 hours. Configuration reruns preserve curator edits. Live private
API access was not attempted without credentials; fixtures test their contracts,
normalization, provenance, retry and conflict-ignore paths.

### Tests, lint and deployment checks

Final actual output from `scripts/dev.ps1 test` inside `web`:

```text
System check identified no issues (0 silenced).
No changes detected
django: version: 5.2.18, settings: enviroinsights.settings.test (from option)
collected 87 items
87 passed, 1 warning in 24.57s
```

SHA256 comparison against the saved foundation baseline: **10 original test
source files checked, zero changed**. All 37 foundation cases still pass; 50
additional cases cover ingestion, units/time, quality, real source samples,
idempotency, provenance, missing keys, API limits, cache integrity, FTP resume,
state aliases and HTTP retries. External source HTTP is mocked in fixture tests;
foundation integration tests still exercise the local real PostgreSQL/Redis/worker.

The unsilenced pytest warning:

```text
RuntimeWarning: numpy.ndarray size changed, may indicate binary incompatibility.
Expected 16 from C header, got 96 from PyObject
```

It occurs with netCDF4 1.7.4/NumPy 2.5.3 import ordering; the actual split-NetCDF
fixture reader passes. The upstream issue and limitations are linked in
DATA_SOURCES.md. No warning filters or test suppressions were added.

```text
ruff check .: All checks passed!
ruff format --check .: 114 files already formatted
python manage.py check --deploy --settings=enviroinsights.settings.prod:
System check identified no issues (0 silenced).
spectacular --validate --fail-on-warn: exit 0, no warnings
```

The production configuration check has **zero warnings**. These commands do
not deploy production; the running Compose stack remains the development stack.

### Failures, root causes, fixes and reruns

1. **Original Princeton delivery unavailable:** the actual catalogue presented
   a challenge, the older DataSpace attempt returned HTTP 401, and DOI metadata
   identified Globus delivery requiring sign-in. Retained the actual response,
   attempted URLs and metadata. Used documented public XKDR access, split
   10,000-row-capped responses recursively, excluded truncated parents from
   loading, and recorded the different product and PM2.5-only scope. Original
   Princeton files and other historical pollutants remain unavailable.
2. **Docker/bind interruption:** earlier downloads received `/app` I/O errors
   when Desktop was unavailable. The underlying shutdown cause was not established.
   Restarted through `docker desktop start --detach`, verified cached bytes,
   retained failed/partial audits and resumed the public downloads. Runs 47–51
   completed successfully. No local database volume was deleted.
3. **WorldPop slow HTTP/no Range support:** the original HTTPS host and official
   Southampton mirror ignored Range requests. The documented anonymous FTP
   service had matching file size/time and a byte-identical real 1 MiB prefix.
   Verified cached first/last segments, resumed 26,214,400 bytes and completed
   the 798,127,525-byte raster. Final full-file SHA256 matches its manifest;
   registration/replay succeeded. Incorrect resume prefixes are fixture-tested.
4. **Wrong city labels in broad CKAN search:** searches returned other cities'
   packages. Restricted each requested city's hourly input to its exact package
   identity. Relocated the earlier 104 mislabeled cached files by actual catalogue
   package, checked D: targets, corrected manifest/asset paths and kept bytes/hashes
   unchanged. Complete download run 49 and load run 63 succeeded. All 12 catalogues
   were searched; seven cities have the matching hourly concentration resources.
5. **Ambiguous station names:** shared aliases such as Pusa, Lodhi and Mumbai
   sites caused partial runs 53/54. Exact CPCB site IDs now take precedence over
   name aliases. Real registry fixtures reproduce the ambiguity. Corrected CPCB
   run 55 added 640,876 missing rows; run 62 replayed all inputs with zero additions.
6. **Missing coordinates:** five Chennai/Pune sites lacked primary registry GPS.
   Matched exact station/city names to a pinned contributed 2024 snapshot, preserving
   primary coordinates. Run parameters identify the fallback asset and sites.
   OpenCity run 63 added the remaining 1,016,274 rows and succeeded. The contributed
   compilation has no declared licence and its positions are unverified; the
   Alandur address discrepancy is documented. Review these before spatial analysis.
7. **Boundary identity and aliases:** district local numbers are not nationally
   unique, so use `censuscode`. The live layers also differed in ampersands and
   spelling (Arunachal/Arunanchal, Andaman labels, historical territories). Normalize
   those aliases, retain national district IDs, recode import references in place
   and give historical parent names district-asset provenance. Removed only two
   proven empty duplicate references created by our earlier import after verifying
   they had no geometry or city/district references; run 64 records the exact IDs.
   Final audit: zero unprovenanced references; all city links correct; repeat run
   74 inserted zero. GDAL/GEOS reported source polygon self-intersections; buffer(0)
   repaired those polygons before storage rather than suppressing the notice.
8. **Foundation compatibility:** an attempted warehouse-field approach conflicted
   with the reversible hypertable test and Django's composite-key relation limits.
   Kept the warehouse schema unchanged, introduced logical weather/fire provenance
   in `ingest`, and made its migration depend on warehouse 0001. All original
   foundation checks pass with their original source hashes.
9. **Validation implementation:** corrected the newly written exclusive-end test
   setup to include its two intended hours, retaining a separate narrower-window
   assertion; gave the completeness OpenAPI response an explicit object type.
   The new boundary alias check initially mistook Bihar's BR code for an import
   hash; restricted that assertion to the actual nine-character hash pattern.
   These were added ingestion checks, not changes to the original 37 tests.
   Final suite and strict OpenAPI schema validation pass.

### Files added/changed and Phase 3 handoff

- `apps/ingest/{base,http,units,quality,registry,completeness,api,tasks}.py`:
  lifecycle, caching/retry, normalization/flags, bulk insertion, coverage, APIs/schedules.
- `apps/ingest/sources/{air,cpcb_archive,opencity,openmeteo,boundaries,worldpop,openaq,firms,era5}.py`:
  public downloads, real parsers and tested optional credential integrations.
- `apps/ingest/models.py`, `admin.py`, `migrations/0002_ingestion_provenance.py`,
  management command modules: skipped audits, assets/provenance, curator filters,
  source commands, completeness and editable Beat registration.
- `enviroinsights/settings/base.py`, `urls.py`: ingestion settings/logging and API routes.
- `requirements/{base,dev}.{in,txt}`: requests/openpyxl/CDS/NetCDF and fixture tooling,
  with transitive dependencies pinned and installed in the rebuilt image.
- `.env.example`, `.gitignore`, `.dockerignore`, `scripts/dev.ps1`: optional key
  signup links, raw-body exclusion, and the container-backed `manage` target.
- `tests/test_ingest_{units,sources,api}.py`, `tests/fixtures/` and its manifest:
  50 added checks and traceable real/adapted contract samples; original tests unchanged.
- `README.md`, `docs/{ARCHITECTURE,DATA_MODEL,DATA_SOURCES,VALIDATION}.md`,
  `docs/validation/PHASE2_*.csv`, `data/raw/**/*.manifest.json`: commands, design
  decisions, licences/access/gaps, actual validation and full file/coverage inventories.

Phase 3 can start with the verified public ingestion dataset and the recorded
coverage limits. It must account for the 2020–2023/2026 concentration gaps;
historical PM2.5-only alternative; finite flagged values counting as present;
OpenCity's explicit +0000 timestamps; CO in mg/m³; approximate weather city centres;
five contributed station positions/licence uncertainty; historic boundary parents;
BLH/provider-null periods; first-value/provenance conflict policy (including nulls);
and the future 2030 alpha population projection. Separate providers are separate
station identities. Fire product rows are not deduplicated physical fire events.
Valid batches retain their original partial-run links after repairs; a partial
job status does not invalidate every committed row from that run.

No manual download, account, key, administrator step or restart is needed for
the completed public pipeline. Optional OpenAQ/FIRMS/CDS live access remains
unverified until credentials exist; original Princeton delivery still requires
account access. Reopen the D: checkout in the client if its visible workspace
still points at the retained C: backup. No Phase 3 feature was implemented.

## Phase 3A live verification — 8 October 2026

All work uses `D:\EnviroInsights-India` and the existing Compose database. No
warehouse data volume was removed. The baseline 87 tests remain unchanged: all
13 original Python test-file SHA256 values match `.tools/tests-before-phase3a.json`.
The 23 added analytics cases use small fixtures and mock external HTTP; the
existing foundation checks still exercise local PostgreSQL, Redis and Celery.

The first real pipeline ran through Celery as task
`4b1009c3-8ef1-410c-b1e4-cf0629b5d180`, AnalysisRun **1**, and succeeded.
Its CLI returned:

```text
Phase 3A completed: AnalysisRun 1
```

It corrected **12,498** stuck flags, built **1,228,198** city/pollutant/hour rows,
identified **52** eligible PM2.5 city-years, fitted all **12** city forests and
exported **98** initially manifested artifacts. A later file-hash/size check
matched all 98. The count/hash of all 16,266,240 warehouse readings, measured/raw
values, natural keys and original ingestion links remained unchanged:
`{'rows': 16266240, 'order_independent_record_hash': 695864490642684660}`.
Corrections were 12,415 CO,
44 O3, 32 NH3 and 7 PM10 rows; all changed stuck → ok. Most flags were missing
data rather than questionable finite readings. The detailed initial audit and
raw-quarter evidence are preserved under `data/results/1/`.

The initial image lacked Git and the checkout was not versioned. Added Git to
the Docker image, created a local code snapshot (no remote/push), checked staged
files against actual secret values without printing them, and verified that
`.env`, `.tools`, raw bodies and result bodies are excluded; manifests remain
eligible. Revision **2b0f254ce0ddff9751019c1277ca5ac0e7194726** is available
inside the rebuilt containers. Source SHA256 is
`30cdb2ccf89c614e917c88bd7a77dfb60b9985c9fdd05cb8b4c0d1a3eafc5ed0`.
The final repeat run retains the initial measured pre-correction audit, rather
than replacing it with already-corrected repeat-run counts.

Actual checks before and after the image rebuild:

```text
PS D:\EnviroInsights-India> .\scripts\dev.ps1 test
System check identified no issues (0 silenced).
No changes detected
collected 110 items
110 passed, 1 warning in 48.78s

RuntimeWarning: numpy.ndarray size changed, may indicate binary incompatibility.
Expected 16 from C header, got 96 from PyObject

PS D:\EnviroInsights-India> .\scripts\dev.ps1 lint
All checks passed!
135 files already formatted

PS D:\EnviroInsights-India> .\scripts\dev.ps1 schema
Schema exit code: 0

PS D:\EnviroInsights-India> docker compose exec -T web python manage.py check --deploy --settings=enviroinsights.settings.prod
System check identified no issues (0 silenced).
```

The known NetCDF/NumPy import warning is not filtered. Production check reported
no warnings. Earlier full-suite execution before the Git image rebuild also
passed all 110 checks in 45.96 seconds. Full local outputs are retained in
`.tools/phase3a-validation/`. New-suite coverage includes completeness boundaries,
equal-station weighting/exclusions, Diwali/exceedances, corrected flags, replay
immutability, deterministic blocked RF fitting, direct-donor equivalence and
read-only/gap-safe APIs. No original test was changed to obtain these results.

Initial live HTTP checks returned 200 for health (every check true), coverage
(144 PM2.5 city-years, 52 eligible), Delhi summary (26 metrics), Delhi raw daily
series for 2025 (365 rows) and deweathered monthly queries inside the gap (zero
rows). Final repeat-run comparisons and API/export validation are recorded below.
Scientific performance and full coverage tables are
in [results/PHASE3A.md](results/PHASE3A.md); successful execution does not imply
reliable weather normalisation for research.

The change from Phase 2's 53 eligible city-years to 52 is explained by Patna 2016:
it has 6,981/8,784 valid hours, but only 257/366 days meet the daily 18-hour rule.
It fails the new ≥75% valid-day requirement. This is a stricter analysis selection,
not deletion or interpolation of historical data.

### Completed repeat run and final checks

Task **a0588198-5fb5-4478-8430-fec71e561947**, AnalysisRun **2**, finished
**successfully**. Database job times are 20:51:29–21:13:21 IST; elapsed
**1,311.729 seconds**. Celery recorded SUCCESS after finishing the manifest.
The repeat changed **zero** flags, inspected **104,660** quarter-backed candidates
(including previously cleared candidates), found the same **129** varying-quarter
candidates, and retained the original measurement/provenance fingerprint. Run 1's
pre-correction baseline remains explicitly linked in Run 2's `flag_audit.json`.
WorldPop registration run 80 succeeded with zero downloads/new observations.

The wrapper initially reported failure because PowerShell 5.1 treated a redirected
Matplotlib INFO message, `generated new fontManager`, as a terminating native
error record. The Celery job itself succeeded. `Invoke-Compose` now leaves stderr
visible and checks the real exit code. A fresh-font-cache management-shell probe
produced that actual INFO message plus deliberate stderr and exited 0; a second
probe exited 7 and the wrapper correctly raised:

```text
Native stderr success probe completed
Deliberate native stderr probe, exit 0
Confirmed: stderr remains visible, wrapper exit 0
Real failure preserved: docker compose exec -T web python manage.py shell --command=import sys; sys.exit(7) failed (exit 7).
```

Figure review found that empty-era panels had Matplotlib's default clock-date
labels. Fixed explicit era boundaries, marked empty panels “No observed series”,
used matched scales per city and distinct city colours, and split annual plots
into the two observed eras. Regenerated only figures/report from the saved real
Run 2 tables/CSVs. Computation revision remains `2b0f254`; export revision is
**7e0adff38a82580bfef799dfa9fde2d867c47065**, recorded with its code SHA256,
reason and actual export times in `AnalysisRun.parameters` and the manifest.
No data value, fitted model or quantitative result changed during this export.

The final verifier checked the actual task result, code/version provenance,
original test hashes, unchanged 16,266,240-row fingerprint, exclusions/default
population, coverage, absence of gap/future modelled rows, pandas export, all
model scores and all recorded artifact hashes/sizes. Actual output:

```text
Validated 103 real HTTP responses, 57 reproduced CSVs and all 12 city model metrics
manifested_files_verified: 99
eligible_pm25_city_years: 52
city_hourly_rows: 1228198
delhi_dataframe_rows: 61118
deweathered_gap_rows: 0
```

CSV/model comparisons passed within numerical tolerance 1e-10; the explanatory
text for an unavailable old/recent comparison was corrected to “At least one
observed era lacks eligible years”. All remaining values match. HTTP checks cover
all 12 cities, both series kinds/frequencies, missing-BLH periods and the gap;
all successful reads returned 200, writes 405, invalid filters 400 and unknown
runs/cities 404. During execution the default API continued to serve successful
Run 1, with incomplete Run 2 returning 404; after completion it served Run 2.

The full suite was rerun after the wrapper/export fixes:

```text
System check identified no issues (0 silenced).
No changes detected
110 passed, 1 warning in 50.62s
All checks passed!
135 files already formatted
```

The same NetCDF/NumPy warning remains visible. Full outputs, the standalone
verification script and `verification.json` are retained with Run 2's artifacts;
its manifest includes supplemental verification evidence. No city passed the
predefined meteorological-normalisation readiness screen. Descriptive datasets
are available, but RF normalisation needs further scientific validation before
Phase 3B relies on it. Phase 3B questions, forecasts, RAG, simulators and dashboards
were not implemented.

## Phase 3A2: corrected deweathering verification (2026-10-08)

All commands ran in the web container from `D:\EnviroInsights-India`.
Corrected diagnostic data run **6** and full model run **7** succeeded. Legacy
run **2**, literal-clock diagnostic run **4**, failed initial diagnostic run **3**
and interrupted provisional model run **5** remain available for the audit.

| Check | Actual result |
| --- | --- |
| Full pytest | 117 passed, 1 warning in 30.49s; all 14 original test files unchanged |
| Ruff | All checks passed; 147 files already formatted |
| Django checks/migrations | No issues (0 silenced); no changes detected |
| Production deploy check | System check identified no issues (0 silenced) |
| Schema | spectacular --validate --fail-on-warn completed successfully |
| Health | HTTP 200; every database/extension/Redis/Celery check true |
| Model grid | All 12 cities, all eight frozen variants; six all-station passes |
| Shared reference | Same seeded 300 joint pooled-weather draws for both eras; hashes stored |
| Measurement preservation | 16,266,240 rows; record hash 695864490642684660 unchanged |
| Frozen protocol | SHA256 09d869e72551b31af0368b0d89a5c91510e8ecd65e6ce53605d33a704b827977 unchanged |
| Gap/future targets | No deweathered series rows in 2020-2023 or 2026 |
| Live API | Latest summary/series/coverage use run 7; explicit run=2 still works |
| Artifact preservation | Runs 2-7 manifests validated against actual bytes and file lists |

The existing netCDF4/NumPy ndarray-size RuntimeWarning remains visible; no warning
filter or test weakening was introduced. The new tests check positive/negative
known lags, whole-week/embargo isolation, pooled-donor reproducibility, correct
IST quarter bins, verified publisher-clock decoding, revised API selection with
legacy access, and interruption failure/manifests.

Real diagnostic findings, a/b/c validation, model ablations, seasonal bias,
readiness and conditional bootstrap intervals are in
[PHASE3A2.md](results/PHASE3A2.md). Passing models do not establish instrument
accuracy or causal effects. All-station readiness passes: Delhi, Hyderabad,
Kanpur, Lucknow, Mumbai and Pune, for their observed eligible periods. Bengaluru
qualifies only on its seven-station fixed panel; its all-station historical
screen fails. Mumbai's matched panel lacks eligible years in both periods.
Kolkata and Patna retain monthly-bias failures despite high overall R2.

Hyderabad 2025 has 0 all-station city-average days above 60 ug/m3 (daily maximum
53.0306); the six-station fixed panel has 53 (maximum 77.6869). Changing station
composition is consequential. Published integer ranges/repeats remain a source
quality limitation and were not fabricated away.

Failures and corrections: the first diagnostic attempt expected a cache-manifest
`bytes` field, while cache metadata uses `size_bytes`; actual file size now comes
from the cached file. Provisional fits were stopped after independent same-site
records proved IST clocks were labelled UTC; the derived -5.5-hour conversion
was then verified in all seven recent cities. A report reader initially failed
on blank Timestamp rows; it now excludes those rows consistently with ingestion.
A final audit initially confused fitted complete-case rows with raw hourly rows:
Delhi has 61,118 raw rows, including five without weather, versus 61,113 fitted
hours. The corrected audit compares the default dataframe directly to run 7.
These corrections changed neither the original tests nor the frozen thresholds.

Exact stdout and proof JSON/CSV/figures are archived under
`data/results/7/verification/` and `data/results/7/diagnostics/`. The manifest
records compute, hourly-supplement and export revisions separately. No Phase 3B
research question has been started.

## Phase 3B live verification — 10 October 2026

Phase 3B is now complete on `D:\EnviroInsights-India`. The successful publication
is **AnalysisRun 19**; city runs are **10, 12, 13, 14, 15, 16 and 17**. Run 11 is
retained as a failed GAM attempt; Run 18 is the preceding publication before
seasonal and matched-network supplements. Run 7 and its 414 artifacts remain
unchanged. This section supersedes the earlier statement that Phase 3B had not
started. The paper is [PHASE3B.md](results/PHASE3B.md).

The stored-clock audit is IngestionRun **87**. It corrected **14,787,584** rows;
the total remained **16,266,240**, with identical value/quality/ingestion-link
hash **767228030051878155** before and after. The repeat command returned:

```text
status: already canonical
corrected_rows: 0
version: opencity-ist-clock-v1
```

DataRun 8 reconstructs diagnostics from canonical storage without a second shift.
Its 12 city hourly frames exactly match Run 6. DataRun 9 rebuilds all pollutant
tables; all 12 PM2.5 hourly series match frozen Run 7 within 1e-12. Cached raw
values and first ingestion links were preserved. The clock tests include a
Timescale chunk-boundary move and real quarter ingestion into native IST bins.

Actual final verification output:

```text
125 passed, 16 warnings in 20.85s
All checks passed!
167 files already formatted
System check identified no issues (0 silenced).
No changes detected
```

OpenAPI generation with `spectacular --validate --fail-on-warn` exited 0 without
warnings. The original 15 test source/support files are unchanged; all original
117 tests are included in the passing suite. The 16 visible warnings comprise
the existing netCDF4/NumPy ndarray-size warning, three SHAP/matplotlib pending
deprecations, and twelve pandas/NumPy generic timedelta deprecations in the new
week-isolation fixture. No warning filter or weakened assertion was introduced.

Live HTTP checks returned:

| Request | HTTP | Key result |
| --- | --- | --- |
| `/api/health/` | 200 | Database, PostGIS 3.6.4, Timescale 2.30.2, vector 0.8.7, Redis and Celery all true |
| `/api/analytics/rq2/delhi/` | 200 | Research run 19; both networks and explicit nested gates |
| `/api/analytics/rq2/bengaluru/` | 200 | Fixed panel is the main cohort; all-station output descriptive only |
| `/api/analytics/rq2/chennai/` | 200 | Descriptive only |
| `/api/analytics/ncap/` | 200 | PM2.5 proxy; official compliance false/not assessed |
| `/api/analytics/comparisons/` | 200 | Run 19 weather-adjusted descriptive comparisons |

The read-only API regression also verifies POST 405 and invalid query 400.
All six compose services are running; db and Redis are healthy. Docker reports
Linux engine **29.8.2**. Host database port remains **5433** and Redis **6380**.

Nine validated Run 7 cohorts have **180 actual refit replicates**, comprising
**300 fitted forests** because separate-era replicates fit two forests. All
cohorts retain 20 refit daily CSVs, parameters, seeds and sampled-index hashes.
The whole-week nested CV, frozen eight-model grid and readiness thresholds are
unchanged. Main-cohort nested gates pass all observed eras only for Lucknow,
Mumbai and Bengaluru's fixed panel. Delhi recent, Hyderabad old, Kanpur old and
Pune recent retain failures; the report does not loosen the criteria.

Meaningful failures and fixes are recorded in
[PHASE3B_IMPLEMENTATION_FIXES.md](results/PHASE3B_IMPLEMENTATION_FIXES.md):

- Cross-chunk bulk UPDATE failed a Timescale constraint and rolled back; the
  atomic partition-aware repair and its boundary test pass.
- The user pause rolled back the unfinished repair; the complete resumed audit
  committed once and reruns change zero rows.
- New fixtures caught NumPy string labels and bootstrap index/date-accessor
  defects; the implementation was corrected without changing original tests.
- Run 11 failed on a held-out 115.4 mm rainfall value outside GAM spline support.
  A documented flat boundary extension retains observations and records clipping
  counts. The exact Gaussian fixture also exposed statsmodels' separation error;
  its equivalent penalised least-squares fallback passes the unchanged assertions.
- The live RQ2 endpoint initially returned 500 due to duplicate city keyword
  metadata; dictionary merging was fixed, the fixture strengthened, and all live
  GETs above reran successfully.
- Docker's interrupted dependency build failed after the engine connection ended;
  Desktop was started, the build succeeded and all services use the rebuilt image.

On matched network dates, Delhi's fixed-panel long-run normalised change is
**−17.591985246475744 µg/m³**, with refit/block 95% interval
**[−35.071142907974696, 1.6623174839119734]**. The interval includes zero.
The calendar-2017/2018 proxy is unavailable for Bengaluru's fixed panel (2017
ineligible), Mumbai (2018 ineligible), Kanpur/Lucknow (no recent targets), and
Pune (no historical baseline). Missing years remain missing.

Source verification corrected Chennai's non-attainment flag: the official CPCB
PDF marks it as a million-plus participant outside the non-attainment list.
The seven eligible cities are unstarred entries. Recent PM10 is context only.
BS-VI attribution and crop-fire estimates are deferred for the stated missing
data; no forecasts, RAG, simulator or dashboards were implemented.

Exact command logs, HTTP checks, preservation checks and integrity outputs are
archived in `data/results/19/verification/`; manifests retain their hashes.
The long model process's launch revision is recorded separately from per-record
on-disk revisions in `compute_provenance.json`, and report export provenance is
stored separately. The existing scheduled weather ingestion added later 2026
weather cache manifests; frozen 2015–2019/2024–2025 research snapshots are unchanged.

## Phase 4 live verification — 10 October 2026

Phase 4 is complete on `D:\EnviroInsights-India`, as **AnalysisRun 21**.
The full suite baseline for Phase 5 is **148 tests**. All 125 original tests
remain passing; all 18 baseline test/support files retain their hashes.
The actual report is [PHASE4.md](results/PHASE4.md).

```text
148 passed, 148 warnings in 29.25s
System check identified no issues (0 silenced).
No changes detected
All checks passed!
```

Schema validation with `spectacular --validate --fail-on-warn` exits 0 without
warnings. Visible full-suite warnings include SHAP/matplotlib deprecations,
MLflow prediction-signature advice, the existing NumPy/netCDF binary-size warning,
generic timedelta warnings in fixtures, and a synthetic SARIMAX convergence
warning. No warning filter or weaker assertion was introduced.

| Verification | Real result |
| --- | --- |
| Forecast migrations | `forecast.0001_initial` applied; no migration drift |
| Real rolling evaluation | 7728 rows; 21 city/horizons; 294 origins including real/ideal weather |
| Target support | 184/184 days, 2025-07-01 through 2025-12-31, for every city/horizon/weather variant |
| MLflow registry | 147 finished registered versions independently checked |
| Replay default | 21 forecasts issued 2025-12-31; stored rows 3864 → 3885 |
| Replay repeat twice and real Celery task | Still 3885 rows; task `cefba66a-830e-48bb-9d36-cb3169ed6371` succeeded |
| Public live weather | IngestionRun 98 success; 21 rows; task `632924ce-4a60-4636-8676-100ad7d6bb56` |
| Keyed PM refresh | IngestionRun 100 skipped, zero inserts, `skipped: no key`; actual task `bd8e2414-4142-403d-92d1-5143f81c2559` succeeded |
| HTTP | Health 200; 21 forecast GETs 200; POST 405, invalid input 400, unknown city 404 |
| CAMS issued-vintage coverage | 0/93240 non-null hourly forecasts; explicitly skipped |
| Preservation | 16,266,240 readings and fingerprint `767228030051878155` unchanged; Runs 7 and 19 artifact hashes unchanged |

Final commands run inside `web`:

```text
python manage.py evaluate_forecasters --run 21
python manage.py issue_forecasts
python manage.py issue_forecasts --replay-date 2025-12-31  # twice
python .tools/phase4-validation/verify.py --run 21
python manage.py export_phase4_report --run 21
```

The actual source archive reload inserted 168 previously missing IST-boundary
daily rows (IngestionRun 94); the repeat (96) inserted zero. BLH remains null
in lead-offset forecasts. Historical Forecast API near-valid-time weather was
probed and excluded from headline features; GFS Previous Runs lead-2/3/4 inputs
have explicit availability bounds. Perfect-prognosis is separately labelled.

Held-out policies losing to persistence: bengaluru h1, bengaluru h3, chennai h1, mumbai h1, mumbai h2, mumbai h3, pune h1, pune h2, pune h3.
Negative skill and convergence warnings are retained. The report includes every
model, horizon, event denominator, empirical interval coverage and monthly/seasonal
bias. Delhi February/March and Pune May are outside the final six-month test;
their earlier bias cannot be declared fixed by this evaluation.

Missing implementation items completed before Phase 5: PM refresh before cutoff,
all-horizon live-input checks with replay fallback, frozen operational calibration,
measured-label preservation in SARIMAX history, and actual result/figure exports.
The frozen forecast design and held-out selection rules are unchanged. See
[PHASE4_IMPLEMENTATION_FIXES.md](results/PHASE4_IMPLEMENTATION_FIXES.md).

Daily schedules are PM 23:35 IST, weather 23:40 and forecasts 00:10. Without an
OpenAQ key, forecasts remain replay. Bengaluru also requires verified fixed-panel
station correspondence. All seven compose services are running, with db/Redis/
MLflow healthy. Host ports remain database 5433, Redis 6380 and MLflow 5000.

AnalysisRun 20 is retained as failed after its numerical thread configuration
was found inconsistent. Run 21 launched at Git `6b3f4b028d0b352b0f29763e8833b4372497f1b1`;
the report export revision is recorded separately. The protocol SHA256 is
`395b384c7b5324ba4b4e87f87e2cdff30295be1de9a42155c85c707e417aa28c` and all recorded numerical thread pools use one
thread. Exact commands, outputs, HTTP/model checks and prior-failure evidence are
under `data/results/21/verification/`, hashed by the manifest.

Phase 5's queued request begins only after this completed verification.
