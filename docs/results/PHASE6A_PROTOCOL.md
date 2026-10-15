# Phase 6A decisions and verification protocol

The active checkout is D:\EnviroInsights-India. Preserve all 183 original tests
and the immutable Phase 5 question set. Finish the engine/API verification before
the whole-site presentation work subsequently requested by the user.

## Existing forecast intervals

Select conformal or calibrated quantile LightGBM separately for 80% and 95%,
using completed Run 21 archived-weather coverage: closest to nominal among
methods at least nominal minus 0.05. If neither qualifies, retain the closest
available method with an explicit failure flag. Do not refit point models.
This user-requested selection uses the existing test results; its coverage is
retrospective and is not independent validation of the newly selected policy.
Preserve previous bounds in provenance and an actual pre-issuance snapshot.

## RAG changes

Use installed RAM to calculate the requested WSL limit. The measured 16 GiB
gives memory=9GB. Adopt available container memory >= actual model bytes +
3 GiB headroom. Record measurements and model manifest, not hypothetical sizes.
Use qwen2.5:3b-instruct only after that condition passes and the real model pull
completes. Its frozen evaluation has a separate output directory; preserve
the original extractive results and document any changed forecast data values.

Retain the reranker in a dedicated Celery process with one inference thread;
release the embedding model between requests. Preserve revision, float32,
1024-token limit, batch size and seeds. Evaluate the fused top-24 candidate
experiment on all 80 frozen literature questions. Adopt 24 only if known-gold
Recall@10 falls by no more than 0.01 relative to the original 40-candidate result.
Keep 40 if it fails; do not change the gate after seeing scores. Measure uncached
requests separately from content-cache hits and report cold/warm latency.

## Physics

Keep NumPy physics separate from Django/database and projected-grid adapters.
Use Briggs rural/urban dispersion coefficients, cited power-law wind profiles,
buoyancy/momentum rise and stack-tip corrections. Wind direction is the direction
FROM which wind blows. Source mass is g/s; output is added micrograms/m3.
Ground/lid images converge to relative 1e-6; sigma-z/lid >=1.6 switches to a
uniform vertical profile. Flag plume penetration of the lid and near-source,
low-wind, missing-weather and population-support limitations explicitly.

Textbook Gaussian examples use their published dispersion inputs. Validate the
Briggs parameterisation separately against the cited formula table; do not tune
Briggs to force agreement with a different Pasquill chart parameterisation.
Keep the requested 5% sigma and 10% concentration tolerances. The adjacent PSU
lecture example contains a sigma-y/class inconsistency and is not a calibration
target. Cite the exact physical/printed page or unpaginated table/section.

Real-weather hourly alignment uses the UTC observation at the IST hour midpoint.
Missing BLH needs a cited, disclosed educational fallback; never call it observed.
Reproject WorldPop 2025 counts conservatively and test count conservation on a
synthetic raster. Missing/nodata population remains unavailable rather than zero.
Label exposure hourly and added; do not add measured station totals to the plume.

Presets expose only source-backed defaults. Unbacked physical values stay null
and require input. Example source assumptions and their citations remain distinct
from measured meteorology/population and actual computed scenario results.

## Completion

Verify source examples, all six requested Hypothesis properties, three frozen
golden arrays, raster exposure, cache identity, input rejection and RAG provenance.
Benchmark 200x200 grids and run three real city/hour scenarios and day mode.
Run Ruff, full tests with explicit test settings, migration/schema checks and
real HTTP/UI checks. Record outputs in PHASE6A.md and VALIDATION; commit when
the requested engine, integration and whole-site presentation work is complete.
