# Phase 6B: VayuSim frontend

Phase 6B implemented and verified after `b29083f`; committed locally without pushing.
Scientific results and physics remain those of Phase 6A; urban C/F must show
**unvalidated branch**. This work adds presentation and stored artifacts.

## Decisions

1. Work only in `D:\EnviroInsights-India`, retain Django and the existing local
   Compose deployment, commit locally, and do not publish or push.
2. Reuse locally vendored MapLibre GL JS 5.24.0 (BSD-3-Clause) and OSM raster
   tiles with attribution. Use native Canvas for particles and cross-sections;
   add no remote scripts, fonts, analytics, paid keys or dependencies.
3. Use a 100 ms particle redraw budget (10 Hz) and a one-second day playback
   step. Prefetch model grids/headers/PNG overlays into a bounded in-memory browser cache;
   never bulk-prefetch or cache OSM tiles. Measure the resulting render path.
4. Derive `validation_status` from each retained run's environment and stability
   class. Urban C/F is `unvalidated_branch`; all other branches are
   `formula_check_only`. Neither status establishes predictive performance.
5. Preserve the geographic PNG overlay unchanged. Add a separate annotated
   export with the visible branch warning and scientific limits.
6. A single-height horizontal grid cannot supply a vertical profile. Store a
   supplementary along-wind vertical grid computed with the unchanged engine
   from the retained run snapshot. The browser reads only that stored artifact;
   it does not infer vertical concentrations from the horizontal field. Explicit
   artifact creation is separate from its read-only GET. Old numerical summaries
   and binary fields are untouched.
7. Represent source removal by a second stored run with all emission rates zero,
   retaining source geometry, weather, grid and other inputs. Do not add nearby
   measured totals to either field. Comparison is an educational source increment.
8. Cold day timing means a first uncached ScenarioRun computation, not cold OS
   filesystem caches. Use a disclosed benchmark assumption tag to avoid old run
   cache hits without changing source numbers; repeat identical payloads warm.

9. Keep the old geographic overlay endpoint and its pixel registration intact.
   The page's Export image control uses the new annotated endpoint. The export
   contains the field, source rates, hour, engine, peak location, hash, category
   legend and limits; it does not copy a basemap or represent a measurement.
10. The GUI edits the first source and preserves any other sources in a stored
    scenario. Editing multiple geometries remains available through the existing
    API. Source removal sets every retained source rate to zero.
11. Run live browser QA separately from the offline pytest suite. The browser
    uses installed Edge/Playwright 1.64.1 and real local endpoints; only attributed
    OSM tile requests leave the origin. Unit tests use synthetic fixtures/local
    PostgreSQL and do not download data or call external model/weather APIs.
12. Generated weather/forecast ingestion manifests are present as untracked
    files. Leave them untouched and exclude them from the explicit frontend
    commit path list.

## API contract as implemented

| Endpoint | Request / response |
| --- | --- |
| `POST /api/vayusim/run/` | Strict finite JSON: `city`, `centre:[lon,lat]`, 1–20 `sources`, `weather_mode`, offset-aware `datetime`; optional `name`, `weather`, `environment`, `receptor_height`, `grid`, `thresholds`. Returns stored `run_id`, `scenario_slug`, `cached`, input hash/version, class, `validation_status`, flags, runtime, summary, contours and artifact URLs. |
| `GET /api/vayusim/runs/<id>/` | Same stored run response; no new calculation of the summary. |
| `GET /api/vayusim/grid/<id>.bin` | Row-major little-endian float32, default 200×200 = 160,000 bytes. `X-Grid-Header` points to its JSON metadata. |
| `GET /api/vayusim/grid/<id>.json` | Shape, dtype/order, six affine coefficients, AEQD WKT, four geographic image corners, receptor height, units, hash/version, flags, contours, limits, interpretation and `validation_status`. |
| `GET /api/vayusim/grid/<id>.png` | Original registered transparent overlay. Values ≤1 µg/m³ are transparent; category palette is unchanged. This technical raster has no annotation margin. |
| `GET /api/vayusim/scenarios/<slug>/` | Scenario specification plus versioned `runs`; each run has its own status. Top-level status is the latest run's status, or null if no run exists. |
| `POST /api/vayusim/day/` | Same specification, real weather only. Uses the datetime's IST date. Returns 24 entries with offset-aware hour, availability/reason and per-run status/summary/cache flag. Grids and contours materialise on demand. |
| `GET /api/vayusim/presets/` | Five unchanged source families, null parameter defaults, required inputs, scope and citations. |
| `GET /api/vayusim/stations/?city=&datetime=` | Nearby same-hour quality-OK CPCB readings, coordinates, distance and samples; labelled `measured total (all sources)`. Never summed with the field. |
| **New** `GET /api/vayusim/runs/<id>/export.png` | Annotated image download with a visible `UNVALIDATED BRANCH` or `FORMULA CHECK ONLY` header, scientific limits and run metadata. PNG text and `X-Validation-Status` also carry status. |
| **New** `POST /api/vayusim/runs/<id>/section/` | Idempotently creates an atomic stored supplementary vertical grid from the immutable run snapshot, then reads it. Does not change the original summary/grid. |
| **New** `GET /api/vayusim/runs/<id>/section/` | Reads the stored vertical grid only; 404 until created. Includes hash/version/status, origin, wind FROM, `distance_m`, `height_m`, `values_ugm3`, method and limits. |

Each source requires type, location, total PM2.5 emission g/s, height/diameter m,
exit speed m/s and temperature K. Area sources additionally require width,
length and subdivisions; lines require end location and subdivisions. Manual
weather requires wind at 10 m, wind FROM, temperature K, solar radiation,
cloud fraction and daytime, with optional mixing height. Real weather uses the
warehouse observation at the IST hour midpoint in UTC. No live weather download
is introduced. The original serializer bounds and rejection rules are unchanged.

`validation_status` is `unvalidated_branch` for **urban C/F**, and
`formula_check_only` otherwise. It is derived from the retained environment and
run class, including old runs; it never changes numerical inputs or hashes.
The latter label does not clear any independent predictive-readiness criterion.

Affine coordinates describe pixel corners in east/north metres; samples lie at
column/row + 0.5. Corner order is top-left, top-right, bottom-right, bottom-left
in image coordinates, not necessarily geographic north-up. Contour masks come
from returned WGS84 GeoJSON at 1/15/60/120 µg/m³ plus user thresholds. Browser
particle positions interpolate the projected image corners for display only;
their concentration and category come from binary cells. Shimmer is a display
cue, not simulated transport, time-of-flight or an uncertainty distribution.

The original horizontal field cannot supply height information. The new stored
section uses the unchanged `simulate` function at extra receptor heights. For
the Delhi example this is 61 heights and 101 downwind distances, 0–1000 m and
0–5000 m respectively. All sources contribute; the transect starts at the first
source and uses the stored wind. The browser renders the saved matrix only.
Old engine versions without a saved section are rejected rather than rebuilt
under a different engine.

## Day-mode performance

Measured on this Windows/Docker laptop, with real retained weather/population
and the existing 10 km / 50 m example specifications. One cold and one identical
warm request per city; these are elapsed single trials, not latency percentiles.
The benchmark calls the actual Django endpoint with its test client against the
development database, so HTTP transport is excluded. Browser HTTP loading is
measured separately. No evaluation data were downloaded or regenerated.

| City / example hour IST | Cold seconds / new runs | Warm seconds / cache hits | Available hours |
| --- | --- | --- | --- |
| Delhi / 2025-01-15 12:00 | 5.531973 / 24 | 0.329430 / 24 | 24 |
| Mumbai / 2025-07-15 15:00 | 2.649020 / 24 | 0.266803 / 24 | 24 |
| Hyderabad / 2025-11-15 20:00 | 2.883380 / 24 | 0.311458 / 24 | 24 |

Cold requests use the disclosed assumption tag retained in
`data/results/phase6b/day-benchmark.json`, creating fresh canonical runs without
changing source or weather numbers. No old runs/caches were deleted. Cold timing
includes summary computation; lazy binary/contour materialisation is additional.
Different hours can change stability class and therefore their warning status.

Chosen budget: **100 ms per particle redraw**, at most 10 redraws/second, with a
**1000 ms independent-hour playback interval**. At most 1500 actual above-1
cells are sampled for shimmer; the full original PNG remains underneath.
Two run-prefetch workers retain header, binary data and PNG blob URLs. The
52-field cache revokes evicted image URLs; it never prefetches tiles.

In the final interaction run, all 24 Delhi grids/headers/overlays prefetched in
**2.742 s**. Scrubbing all hours then issued **zero binary, JSON-header or PNG
overlay requests**. Frame-selection wall time was **28–59 ms**. The measured
Canvas particle-draw maximum during that interaction was **6.4 ms**, within the
chosen budget. These timings exclude the asynchronous GPU compositor, tile
availability and station-context requests. They do not establish device-wide
frame rate. Missing hours clear the field/summary and stay unavailable.

## Frontend and browser verification

The single Django template at `/vayusim/` (also `/simulator/`) includes a free
OSM map; click, drag, coordinate and keyboard source placement; cited preset
families; manual/archived weather and hour controls; binary-field shimmer;
registered PNG fallback; standard/custom contours; peak/location/distance/class;
all flags including low-wind when present; population above each threshold with
known-support disclosure; four limits in the summary and page footer; two stored
source/source-removed runs; 24-hour scrub/play; separate station context; and
the stored vertical grid. Theme and motion controls are keyboard accessible;
reduced-motion preference disables automatic shimmer. Category names and
numerical boundaries accompany colour; an hourly increment is not AQI.

All three actual examples were opened at **1440 px** and **390 px** width.
All six loads returned HTTP 200 with WebGL maps, zero JavaScript exceptions and
no horizontal page overflow. The phone main gutter is 16 px. Only
`tile.openstreetmap.org` was requested externally. No script CDN, font provider,
analytics or external model/weather endpoint is called. MapLibre **5.24.0** is
the existing local BSD-3-Clause distribution with its retained licence; native
Canvas has no added dependency. No library or tile access requires a paid key.

The visible **unvalidated branch** text was checked on all three example cards,
the current scene, summary, day-status display, all three actual shared scenario
links, cross-section and exported images. It is server-rendered before JavaScript
hydration. API responses and PNG metadata were also checked. No claim of
predictive performance is added. Formula-only day hours receive their own status.

Live browser checks verified Delhi stored runs **62 and 162** for the comparison:
run 162 is the zero-emission field. The difference says **modelled increment from
these sources only**. Actual station totals are separate. Keyboard crosshair
placement and range-slider operation, playback, light mode and forced WebGL
failure with the real PNG all passed. The page offers the annotated export,
not the unannotated technical overlay, as its image download.

Browser QA commands (installed local Edge/Playwright 1.64.1; no installation or
download was needed):

```powershell
node scripts/verify_vayusim_browser.cjs
node scripts/verify_vayusim_interactions.cjs
```

These scripts use the retained example IDs 62/63/64 in this development database.
They use `.tools/ui-preview/node_modules/playwright`; a fresh checkout needs the
same optional browser QA tooling and the retained example data. They are separate
from pytest, which does not call live external services.

| View | Screenshot |
| --- | --- |
| Delhi desktop / phone | [1440 px](phase6b-delhi-1440.png), [390 px](phase6b-delhi-390.png) |
| Mumbai desktop / phone | [1440 px](phase6b-mumbai-1440.png), [390 px](phase6b-mumbai-390.png) |
| Hyderabad desktop / phone | [1440 px](phase6b-hyderabad-1440.png), [390 px](phase6b-hyderabad-390.png) |
| Day mode | [Day](phase6b-day.png) |
| Stored vertical grid | [Cross-section](phase6b-cross-section.png) |
| Light mode | [Light](phase6b-light.png) |
| Forced WebGL fallback | [Phone PNG fallback](phase6b-fallback-phone.png) |

## Failures found and corrected

- A MapLibre capability call used an unavailable helper and incorrectly selected
  fallback. Construct the existing MapLibre Map directly, catching actual context
  failure. Both normal WebGL and forced no-WebGL paths then passed.
- New-run versus database weather JSON had different key order, causing a false
  comparison rejection. Compare key/value content, not JSON string order. The
  same two stored fields then passed source-removal/difference checks.
- Initial binary/header caching still allowed overlay HTTP requests during
  scrubbing. Prefetch retained PNG blobs too; final 24-frame QA observed zero
  grid/header/overlay requests after preparation.
- Review found potential stale fields on unavailable hours and stale comparison
  captions. Missing hours now clear field, metrics, station context and links;
  source-view captions reset on return. No missing concentration becomes zero.
- Shared page forms now use the immutable run snapshot instead of mutable
  Scenario inputs. Regression checks retain environment after a Scenario edit.
  Empty scenarios return a null status instead of an exception.
- Browser harness failures were also retained: Django reload connection races,
  an invalid relative Playwright export URL, too-short health readiness timeout,
  and checking PNG completion before its load event. Corrected QA setup/waits;
  final browser scripts passed. A shell-quoting error during a template update
  changed no file; the update was applied with literal PowerShell strings.
- Two full 271-test attempts passed 270 but triggered Hypothesis's input-generation
  `too_slow` health check: individual float draws consumed 2.10 and 1.76 seconds.
  No numerical assertion failed. The first reported seed passed alone. Briefly
  pausing background inference/scheduling services did not prevent recurrence;
  they were restored in `finally`. A read-only GC observer then ran all **271
  tests successfully in 81.90 seconds**, observing generation-2 pauses up to
  0.544 seconds. It did not reproduce the failed draw or prove its cause. Runtime
  timing/collection sensitivity remains a limitation, not an asserted physics
  defect. No test, threshold, Hypothesis setting, seed policy or physics code was
  changed to suppress the failure.
- Allocation review found that page-input filtering created a full serializer
  for every input key. Create it once per retained specification instead. A
  separate 100-call traced benchmark measured **1.464717 → 0.129322 seconds** and
  peak traced memory **738,499 → 362,062 bytes**. This removes redundant work;
  it is not proof of the cause of the intermittent Hypothesis timeout. The final
  ordinary suite result is recorded below.

## Preservation and final checks

All original 52 test/fixture files and all six physics/preset files are byte
identical to the before snapshot. All 70 prior independent-reference evidence
artifacts and five original scientific code/report files retain their manifest
hashes. Original example input hashes, binary SHA256s and every original summary
value match before/after, including peaks:

| Stored run | City / branch | Peak µg/m³, unchanged | Frontend label |
| --- | --- | --- | --- |
| 62 | Delhi urban C | 15.641839027404785 | unvalidated branch |
| 63 | Mumbai urban C | 11.536741256713867 | unvalidated branch |
| 64 | Hyderabad urban F | 18.990890502929688 | unvalidated branch |

| Frozen set | Before SHA256 = after SHA256 |
| --- | --- |
| Phase 3A.2, 316 files | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` |
| Phase 4, 776 files | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` |
| Phase 5 questions/relevance | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` |

The added offline tests cover status branches, run/header/scenario/PNG metadata,
visible image annotation pixels, immutable page inputs, all example cards and
shared rendering, section creation/read/cache, source-removed zero fields,
unknown IDs, empty scenarios and cached 24-hour day identity. Existing tests
and labels were not edited. Final unmodified web-container suite: **271 passed, 147 warnings in 100.88s**. Ruff and formatting pass; the production deployment check reports **0 issues (0 silenced)**; OpenAPI validation and migration drift checks pass. All nine default Compose services are restored/running and `/api/health/` returns **200**, with every check true. The assistant remains extractive and Ollama remains off. The 147 warnings are the existing NumPy/pandas timedelta, SHAP, compiled netCDF4 ABI and statsmodels fixture convergence warnings; none was silenced. The intermittent Hypothesis wall-clock health-check failures and the passing original-seed replay/observational run remain in the journal; no numerical assertion or health-check setting was altered. Allocation review also removed repeated serializer construction per input key; its separate measured 100-call benchmark is retained in the metrics.

Structured evidence is retained in `data/results/phase6b/`; selected measured
outputs are committed in `PHASE6B_METRICS.json`. Commands, failures and re-runs
are recorded in [VALIDATION.md](../VALIDATION.md). Final Git commands and commit
identity are retained in `data/results/phase6b/final-git.json` to avoid a
self-referential commit hash in the committed report. No push is performed.

## Remaining limitations

Urban C/F retain the scientific limitations of Phase 6A. This frontend does not
resolve independent numeric readiness or establish field predictive performance.
Flat terrain, primary PM2.5 only, no chemistry/deposition, uniform hourly weather,
steady state and near-field source discretisation still apply. Population is
the supported grid footprint, not citywide census exposure or a health estimate.
Measured totals and hourly source increments have different meanings.

Particle movement is display shimmer; day mode switches independent steady
hours, not a moving pollutant mass. Single-trial timings and software-rendered
Edge screenshots are local-device observations, not hardware/browser guarantees.
The cross-section is a new stored receptor grid with its own sampling, not a
measured vertical profile or information recovered from the original 2-D field.
All comparisons remain source-only. No full-site redesign, new physics,
coefficient/preset tuning, inventory inference, paid infrastructure, hosting,
scientific re-evaluation or later research phase is included in this task.

Annotated example exports: [Delhi](phase6b-export-delhi.png), [Mumbai](phase6b-export-mumbai.png), [Hyderabad](phase6b-export-hyderabad.png).
