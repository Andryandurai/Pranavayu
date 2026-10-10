# Phase 2 data sources

## Phase 4 forecast inputs

The canonical concentration timestamps were repaired in Phase 3B, superseding
the earlier stored-clock caveats below. Phase 4 uses hash-verified raw Run 8
2024–2025 snapshots; it never uses deweathered concentrations as inputs.

Weather comes from [Open-Meteo Previous Runs](https://open-meteo.com/en/docs/previous-runs-api),
explicit GFS Global, UTC, m/s. The related requested
[Historical Forecast endpoint](https://open-meteo.com/en/docs/historical-forecast-api)
was fetched as a diagnostic, but its stitched near-valid-time values do not meet
issue-vintage rules. For horizon h, Phase 4 uses h+1-day offsets and a documented
conservative availability bound with a 12-hour publication margin. This relies
on provider lead semantics and a latency assumption rather than exact archived
publication timestamps. Missing BLH stays null and is excluded from predictors.

`fetch_historical_forecasts` uses the existing RawCache/RawAsset/IngestionRun
framework. Daily ForecastWeather records are distinct from WeatherObservation
and retain request hashes, lead/bound semantics, source asset and run. Cache files
are under `data/raw/forecast/`, with overlapping UTC request windows to retain
whole IST days. Live public weather uses the same source framework and actual
retrieval availability. See [PHASE4_PROTOCOL.md](results/PHASE4_PROTOCOL.md).

A real 2025 CAMS PM2.5 valid-time response was retrieved from the Air Quality API;
the API does not document a retrievable 2025 issue-vintage archive. It is retained
as a source probe and cannot be treated as a leakage-safe forecast benchmark.
OpenAQ remains keyed and unverified live; lack of a key invokes explicit replay.

The active project is `D:\EnviroInsights-India`; containers read it at `/app`.
Inputs live in `data/raw/`. Only adjacent `*.manifest.json` files are eligible
for version control. Manifests record URL, retrieval time, bytes, SHA256,
request digest and provider metadata. Changed requests/responses retain older
inputs under distinct filenames. `RawAsset` records the source/download run.
The active checkout is versioned in Git. Downloaded bodies remain ignored;
only their manifests and implementation/documentation are tracked.

| Source | Account | Licence / attribution | Command |
| --- | --- | --- | --- |
| [Princeton CPCB 2015–2019](https://datacommons.princeton.edu/discovery/catalog/doi-10-34770-60j3-yp02) | Current large-data delivery requires Globus sign-in | DOI metadata: CC BY 4.0; cite Sharma/Mauzerall, DOI 10.34770/60j3-yp02 | `load_cpcb_archive` |
| [XKDR CPCB mirror](https://airquality.xkdr.org/) | Public demo without signup | CC BY 4.0; attribute XKDR Forum and CPCB | `download_sources --source cpcb`, `load_cpcb_archive` |
| [OpenCity Delhi](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports), [Bengaluru](https://data.opencity.in/dataset/bengaluru-hourly-air-quality-reports) and other city catalogues | No | Catalogue: Other (Public Domain); retain resource licence and credit CPCB/boards | `download_sources --source opencity`, `load_opencity` |
| [Open-Meteo ERA5](https://open-meteo.com/en/docs/historical-weather-api) | No for public non-commercial API | CC BY 4.0; credit Open-Meteo, ECMWF and Copernicus; commercial terms differ | `backfill_weather` |
| [Datameet](https://github.com/datameet/maps) | No | CC BY 4.0; boundary vintage/accuracy require review | `download_sources --source boundaries`, `load_boundaries` |
| [WorldPop R2025A](https://hub.worldpop.org/geodata/summary?id=73812) | No | CC BY 4.0; cite DOI 10.5258/SOTON/WP00839 and release statement | `download_sources --source worldpop`, `register_worldpop` |
| [OpenAQ v3](https://docs.openaq.org/) | API key | Original provider licences and OpenAQ terms | `backfill_openaq` |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/area/) | MAP_KEY | NASA data policy; credit FIRMS and instruments | `backfill_firms` |
| [CDS ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) | Personal access token; accepted dataset licence | Copernicus licence; credit ECMWF/C3S | `backfill_era5` |

## Windows commands

```powershell
.\scripts\dev.ps1 manage download_sources
.\scripts\dev.ps1 manage ingest_all
.\scripts\dev.ps1 manage data_completeness --output .tools/phase2-validation/completeness.json
.\scripts\dev.ps1 manage backfill_weather --start 2015-01-01 --end 2026-10-03
.\scripts\dev.ps1 manage configure_ingestion_schedules
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
```

`download_sources --source` accepts `boundaries|cpcb|opencity|weather|worldpop`.
`ingest_all --source` also accepts `openaq|firms|era5`. Each source has its own
run; all are attempted even if one fails. Failed/partial runs return command
failure; missing credentials create clean skipped runs. Backfill dates are
inclusive. Observation API timestamps use inclusive start, exclusive end and a
31-day maximum. Supply explicit offsets. Responses use 100-row cursor pagination.

## CPCB historical archive

The requested catalogue returns a verification page. The documented alternative
[DataSpace record](https://dataspace.princeton.edu/handle/88435/dsp01zw12z843p?mode=full)
also rejects automated access. Accessible
[DOI metadata](https://api.datacite.org/dois/10.34770/60j3-yp02) identifies the release;
the repository distributes the large dataset through
[Globus](https://app.globus.org/file-manager?origin_id=dc43f461-0ca7-4203-848c-33a9fc00a464&origin_path=%2F60j3-yp02%2F).
Catalogue responses and attempted URLs are retained. Original Princeton files
were not downloaded or falsely labelled as loaded.

The alternative uses the publisher's documented public XKDR demo. Its published
demo token is public access information, not a private credential. Queries cap
at 10,000 rows and bulk-file demo access covers only 2024. Download **PM2.5 only
for 2015–2019**, by seeded city/month, recursively splitting capped date windows.
Truncated parent inputs remain auditable and are excluded from loading. This is
a different compilation; other historical pollutants remain a gap.

The loader supports long CSV records with
`station_id,parameter_name,unit,collected_at,value`, and wide CCR-style records
with `From Date`/`Timestamp`/`Datetime` and pollutant columns such as
`PM2.5 (µg/m³)`. Files go in `data/raw/cpcb/princeton/` or `data/raw/cpcb/ccr/`.
An adjacent manifest can supply `metadata.city` and `metadata.station_name`
when absent in an export. Naive timestamps are IST; explicit offsets take precedence.
Unrecognized layouts are not interpreted as concentrations. The unavailable
original Princeton file layout has not been live-validated.

Coordinates come from the actual
[publisher station registry](https://airquality.xkdr.org/v1/stations), matched by
CPCB ID or exact normalized name. Missing/ambiguous coordinates are rejected.
Match existing stations within the same provider by name/location (100 m), or
upsert by provider/site ID. Stations across providers remain distinct, preserving
the station-source/run-source condition. No coordinates are invented.

Five Chennai/Pune sites have no coordinates in the primary registry. The loader
matches their exact station/city names to a public
[contributed 2024 station snapshot](https://huggingface.co/datasets/Zeel/C1/blob/main/station_data.csv),
pinned at revision `1fbf3fa5bebf5195ca095e43c4a9a27a666b944c`. Its raw CSV,
SHA256 and asset ID are retained; run parameters identify each station using it.
Known primary coordinates are preserved. These are published coordinates, not
independently surveyed positions. The compilation declares no licence. Alandur's
published coordinates have an address discrepancy identified in the primary
[Greenpeace station assessment](https://www.greenpeace.org/static/planet4-india-stateless/2024/12/ec05b58e-24-12-05-a4-gpi-beyond-north-india-report-e3.3.pdf); Phase 3 should review
these positions before spatial analysis. No city-centre coordinates are substituted.

## OpenCity

Search CKAN for every seeded city; download all CSVs in matching hourly-report
packages and retain catalogue metadata. Older 2017–2023 exports are monthly
matrices of dimensionless AQI: preserve them as assets but exclude them from
concentration loading. AQI is never turned into fabricated pollutant values.
Recent station CSVs contain 15-minute concentrations.

Aggregate distinct 00/15/30/45 minute slots, requiring at least three nonnegative
finite values. Otherwise retain a missing/negative hour. Duplicates do not meet
the threshold. Raw hourly value is the mean of reported finite slots; original
quarters remain in the raw input. No absent hours are filled. The cached recent
timestamps explicitly say `+0000`, but independent same-site comparisons verified
that these particular exports contain IST wall clocks. Phase 3B's idempotent
canonical-clock repair converts those stored keys to UTC once. Original file
labels remain unchanged; arbitrary offset-labelled inputs are not reinterpreted.

## Weather

Request one city/year, UTC, m/s, explicitly `models=era5`. Locations use Phase 1's
approximate city centres; provenance retains returned grid coordinates. Values
are provider reanalysis, not instrument measurements or locally generated data.
Variables are temperature, RH, dew point, wind speed/direction, pressure, cloud,
precipitation, shortwave radiation and BLH. The current archive **does return
boundary_layer_height**; an actual Delhi sample returned 45 m at 2019-01-01
00:00 UTC. Missing variables stay null. Dew point lives in provenance because the
foundation weather table has no such column. Cloud percent becomes fraction;
pressure hPa, precipitation mm and radiation W/m² are preserved.

The live October 8 capture requested through October 3 using the nominal five-day
lag. The provider returned all-null variables for October 3; the last non-null
weather day was October 2. BLH was also null for January–June 2024 across all
12 cities. Those nulls are retained. Calendar row counts do not imply every
variable is present. A later provider correction requires an explicit correction
policy; conflict-ignore preserves the first published payload, including nulls.

ERA5's documented publication lag is five days; default end is current UTC date
minus five days. Cache JSON, pause between requests and honour 429/5xx retry
headers. Connection/read timeouts are finite. Multi-variable year requests use
more quota than short queries. Public API fair-use/non-commercial terms apply.
Failed years are recorded and can be retried without redownloading cached inputs.

Optional CDS requests use explicit personal-token credentials, city point areas
and daily dates. Combine ZIPs containing separate instantaneous/accumulated
NetCDF files before insertion. Convert Kelvin to Celsius, Pa to hPa, rain metres
to mm and ERA5 one-hour solar J/m² to W/m². Derive wind speed/direction from u/v
and RH from temperature/dew point. CDS remains optional, without a Beat schedule.

## Boundaries and population

Datameet commit `b3fbbde595310b397a55d718e0958ce249a4fa1f` pins
`States/Admin2.{shp,dbf,shx,prj}` and
`Districts/Census_2011/2011_Dist.{shp,dbf,shx,prj}`. GDAL transforms geometry to
WGS84 and repairs invalid polygon topology. `censuscode` is the national district
ID; `DT_CEN_CD` is state-local. Point-in-polygon creates audited city/district
links. Historical Telangana districts keep their 2011 Andhra Pradesh parent.
Boundary vintage is not current administrative truth; multiple matches are logged.
The pinned files contain 36 state features and 641 district features. Normalize
ampersands and published state-name spelling variants before resolving project
codes. Keep the two historical DN/DD parents alongside the newer merged DH
territory: their names have district-file provenance but no invented state
geometry. All 12 city/district links have a single matching polygon.

WorldPop's selected latest available year is **2030**, a **future population
projection** from constrained 100 m R2025A v1 alpha. It is not historical exposure
population. Register digest/path, CRS, dimensions, nodata, origin/scale and
year/product/licence only. Phase 6 must choose an appropriate year and review
release/derived-data licence terms; no population sums/exposures run in Phase 2.

The HTTPS server and the official Southampton public mirror ignored byte Range
requests and transferred slowly. The provider documents a parallel
[anonymous FTP service](https://sdi.worldpop.org/wpdata) with the same file layout.
The loader uses `ftp://ftp.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2030/IND/v1/100m/constrained/ind_pop_2030_CN_100m_R2025A_v1.tif`.
Size and modification time matched HTTPS; a real 1 MiB prefix matched byte for
byte. Resume verifies both the first and last cached segments before transfer,
then verifies final size/source time and writes a SHA256 manifest. No account
or private FTP credentials are used.

## Optional credentials and fire archives

Add optional keys only to ignored `.env`, then recreate app containers:

- `OPENAQ_API_KEY`: [register](https://explore.openaq.org/register). Send as
  `X-API-Key`; discover within 25,000 m of each city. Sensor `/hours` uses current
  v3 `datetime_from`/`datetime_to` parameters and pagination.
- `FIRMS_MAP_KEY`: [request MAP_KEY](https://firms.modaps.eosdis.nasa.gov/api/map_key/).
  `FIRMS_BBOX=73,27,78,33` is configurable. Fetch SNPP/NOAA20 VIIRS and MODIS NRT
  in windows up to five days. UTC detections keep native confidence and FRP MW;
  provenance keeps instrument/version. Existing CSVs under `data/raw/firms/`
  load without a key via `backfill_firms --archives-only`.
- `CDS_API_KEY`, `CDS_API_URL`: [API setup](https://cds.climate.copernicus.eu/how-to-api).
  Accept the ERA5 licence before retrieval. Missing keys log `skipped: no key`,
  create a finished skipped run and make no HTTP call.

No account, key or user download is required for public pipelines. Private keys
are redacted from URLs/manifests/logs and are not version-controlled.

## Tests and caveats

Fixtures contain original CPCB/OpenCity rows, registry objects, Open-Meteo
responses, Delhi boundary geometry and actual NASA API-academy fire rows.
Authenticated OpenAQ/CDS captures require credentials: their contract fixtures
adapt real CPCB/ERA5 values to documented schemas and are explicitly labelled
as adaptations in `tests/fixtures/manifest.json`. They are not live API captures.
External HTTP is mocked with `responses`; existing foundation integration tests
continue checking local Docker PostgreSQL/Redis/Celery.

Pinned netCDF4 1.7.4 emits a NumPy ndarray-size RuntimeWarning with pytest import
ordering. The split-NetCDF reader/units test passes. The
[upstream issue](https://github.com/Unidata/netcdf4-python/issues/1354) records this
warning, including with NumPy 1.x. Report it without adding warning filters;
recheck during dependency upgrades. See [VALIDATION.md](VALIDATION.md) for actual
downloads, failures and coverage. Completeness describes presence, not calibration
or regulatory validity.

## Phase 3A audit and population update

The audit reads the existing SHA256-verified CPCB/OpenCity cache. It makes no new
concentration download, preserves measured/raw values, and uses original quarters
to distinguish equal means from flat input. Positive rounded plateaus remain
screening candidates, not proof of instrument malfunction. Paired PM2.5/PM10
inversions remain diagnostic in canonical units; no cross-instrument correction
is invented. Five contributed GPS positions remain unverified and their sites
are now excluded from city/spatial analysis.

The [official 2025 WorldPop catalogue](https://hub.worldpop.org/geodata/summary?id=73807)
provides a downloadable constrained India 100 m R2025A v1 raster. Its public
[documented FTP service](https://sdi.worldpop.org/wpdata) delivered the actual
778,106,191-byte file without an account. The local raster, SHA256, catalogue,
GDAL metadata and registration are recorded in its raw manifest and `PopulationRaster`.
This 2025 modelled alpha estimate is default; the existing 2030 projection remains
available and nondefault. Read the
[release statement](https://data.worldpop.org/repo/prj/Global_2015_2030/R2025A/doc/Global2_Release_Statement_R2025A_v1.pdf)
before exposure research; it is not a census or an observed headcount.

Provider weather nulls remain NULL. BLH is missing for January–June 2024 across
all cities, plus the final weather day; complete-case normalisation omits these
targets. Concentration gaps in 2020–2023/2026 are not filled. The earlier OpenCity
clock concern was resolved by Phase 3A2's independent same-site verification and
Phase 3B's canonical stored-clock repair, described below.

Official central-government calendar links for all seven Diwali dates, the
Grange/rmweather method, actual flag audit and model results are retained in
[PHASE3A.md](results/PHASE3A.md) and `apps/analytics/descriptive.py` comments.
External HTTP is mocked in the new analytics tests. Existing local PostgreSQL,
Redis and worker integration tests continue unchanged.

## Phase 3A2 source-clock verification

Independent XKDR comparisons establish that the recent OpenCity CPCB wide
exports preserve IST wall clocks while displaying `+0000`. A first-week 2024
same-site comparison in every recent city matches 93–168 hourly means, exactly
or within 0.005 µg/m³ rounding. URLs, input SHA256 and paired records are retained
in [PHASE3A2_CLOCK_PROOF.json](results/PHASE3A2_CLOCK_PROOF.json) and result artifacts.
[XKDR's schema](https://github.com/xKDR/Air-Quality-Database/blob/main/docs/PUBLIC_API.md)
explicitly describes its naive `collected_at` as IST. The related publisher
repository's UTC-label attachment supplies processing context, but direct file
lineage is not established for every OpenCity export; the numeric/time matches
provide the independent evidence. This supersedes the unresolved-clock limitation
above for these cached exports. It does not justify changing arbitrary UTC data.

Phase 3A2 first applied the correction in versioned analytical timestamps.
Phase 3B subsequently repaired 14,787,584 warehouse timestamp keys once in
IngestionRun 87, retaining measurement values, flags and original ingestion links.
Canonical warehouse timestamps can now be joined directly to UTC weather;
applying the shift again is invalid. Cached source files retain their original
labels and hashes. Open-Meteo requests/returned offsets remain UTC. Returned ERA5
grid coordinates are audited alongside requested city points.
Hyderabad's published integer ranges/repeated values and city-versus-station
exceedances are documented without inventing an instrument or uncapping correction.
