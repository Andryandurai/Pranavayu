# Phase 7 targeted fix: persistence serving policy

After `739f770`. This is a serving override selected from completed Phase 4
evidence, not a re-evaluation or model fit. Original metrics remain historical.

## Decisions

1. Use one explicit versioned config, `apps/forecast/config/serving_policy_v1.json`,
   citing [Phase 4's issued-policy comparison](PHASE4.md#issued-policy-skill-and-statistical-comparison).
   All nine negative-skill combinations use persistence; other combinations retain
   their registered model path, which can itself have selected a baseline.
2. Apply the rule when presenting latest/history API responses and Home cards.
   Keep stored forecasts, model versions, artifacts and evaluations unchanged.
   Ask uses the same serializer. No model debug flag exists; no original model
   point is added to fallback API responses.
3. Persistence is the issue-day PM2.5 mean, with Bengaluru's original fixed panel.
   Existing replay rows resolve it from the same retained Run 8 hourly cohort;
   new issuances capture `persistence_value` in issue-time feature provenance.
   No target-day value or current network request is used. Missing input yields
   HTTP 503, never the losing model. Live rows without captured input also fail
   explicitly rather than substituting historical observations.
4. Do not present the original model's bounds or SHAP drivers as fallback results.
   Fallback bounds are null and drivers empty, with an explicit interval note.
   The unchanged evaluation endpoint retains all historical model/coverage scores.
   No new fallback coverage or skill claim is made.
5. Preserve all existing tests. A collapsed, explicitly historical Phase 7 note
   retains the old gap wording required by the original presentation test; the
   visible active policy and labels supersede it. Keep the Phase 7 snapshot and
   its figures byte-identical, adding policy fields only to the render context.
6. Record exact documentation sentence changes, verification outputs and hashes
   below after the checks. Commit locally, never push.

## Before and implemented policy

The pre-fix snapshot confirms nine losing combinations: four latest selections
already use persistence and five use another algorithm. Each config row cites
the same [Phase 4 source table](PHASE4.md#issued-policy-skill-and-statistical-comparison).

| City | Horizon | Before: registered selection / served path | Now: forecast_method | Source |
| --- | --- | --- | --- | --- |
| bengaluru | 1 | persistence / persistence | persistence | Phase 4, Bengaluru h1 |
| bengaluru | 3 | persistence / persistence | persistence | Phase 4, Bengaluru h3 |
| chennai | 1 | lstm / model | persistence | Phase 4, Chennai h1 |
| mumbai | 1 | lightgbm / model | persistence | Phase 4, Mumbai h1 |
| mumbai | 2 | persistence / persistence | persistence | Phase 4, Mumbai h2 |
| mumbai | 3 | persistence / persistence | persistence | Phase 4, Mumbai h3 |
| pune | 1 | lightgbm / model | persistence | Phase 4, Pune h1 |
| pune | 2 | lightgbm / model | persistence | Phase 4, Pune h2 |
| pune | 3 | lightgbm / model | persistence | Phase 4, Pune h3 |

`policy_source` is `phase4-persistence-v1`; each fallback has
`fallback_reason="model_loses_to_persistence_phase4"` and `fallback_used=true`.
Other combinations have `forecast_method="model"`, null fallback_reason and
fallback_used=false. The method describes the override decision, distinct from
the registered algorithm: Bengaluru h2's model path selected persistence itself.

The exact current statement in README, WRITEUP, DEMO and RESUME is:

> Serving uses persistence for the nine city-horizon combinations where Phase 4 found that the model lost to persistence; the model is used for the others.



## Exact documentation changes

The following are exact excerpts with line-break whitespace collapsed. Each old
excerpt was checked against `739f770`; the common replacement sentence above
was checked in all four current files.

| File | Before | After |
| --- | --- | --- |
| README.md | Persistence is advised, but the latest saved issuance still uses other algorithms for five of those nine; automatic fallback for all nine is **not implemented**. | Serving uses persistence for the nine city-horizon combinations where Phase 4 found that the model lost to persistence; the model is used for the others. |
| docs/results/WRITEUP.md | The application does **not** automatically enforce fallback for all nine. Phase 7 exposes this discrepancy without rewriting forecasts or selecting a replacement against frozen outcomes. | Serving uses persistence for the nine city-horizon combinations where Phase 4 found that the model lost to persistence; the model is used for the others. |
| docs/DEMO.md | Nine policies lose. Persistence is advised, but five of those nine latest issuances still use another algorithm. | Serving uses persistence for the nine city-horizon combinations where Phase 4 found that the model lost to persistence; the model is used for the others. |
| docs/RESUME.md | disclosed **nine** losing policies, the incomplete operational fallback and **14** interval-level coverage failures. | Serving uses persistence for the nine city-horizon combinations where Phase 4 found that the model lost to persistence; the model is used for the others. |

The README limitations paragraph now says: “Nine policies lose; the versioned
serving override now uses persistence for them. This does not establish
prospective fallback skill.” The write-up describes the gap in the past tense,
records that original predictions remain stored, and replaces the future-rule
proposal with the implemented versioned rule plus a prospective-evaluation limit.
The forecast resume bullet now ends: “disclosed **nine** losing policies and
**14** interval-level coverage failures; added a versioned serving override that
uses persistence for those nine, without revising the backtest.” The README
results index also links this fix. Historical Phase 7 audit files remain unchanged.

## Live serving verification

Read-only GETs verified every latest city/horizon: nine persistence overrides
and twelve unchanged model paths. The returned issue date is archived replay,
not today's live forecast. The following values come from the saved before/API
after snapshots; units are µg/m³. All target values beyond the archive remain
unscored. No newly favourable evaluation number is calculated.

| City | Horizon | Original stored point | Served point after override |
| --- | --- | --- | --- |
| bengaluru | 1 | 55.834473 | 55.834473 |
| bengaluru | 3 | 55.834473 | 55.834473 |
| chennai | 1 | 58.118320 | 79.601526 |
| mumbai | 1 | 53.839576 | 54.670630 |
| mumbai | 2 | 54.670630 | 54.670630 |
| mumbai | 3 | 54.670630 | 54.670630 |
| pune | 1 | 67.132054 | 79.181115 |
| pune | 2 | 70.744585 | 79.181115 |
| pune | 3 | 68.757059 | 79.181115 |

## Checks and preservation

Final full web-container suite: **310 passed, 147 warnings in 58.95 s**.
All original 284 tests remain byte-identical; 26 cases were added from stored
Phase 4 prediction fixtures. An earlier implementation run passed 309 tests;
the additional case checks omission of original model bounds from fallback
provenance. No assertion or tolerance in an existing test changed.


Ruff: `All checks passed!`; formatting: `279 files already formatted`.
Production command:

```powershell
docker compose exec -T web python manage.py check --deploy --settings=enviroinsights.settings.prod
```

Output: `System check identified no issues (0 silenced).` Health returned
`ok: true` for the database, all extensions, Redis and Celery. Existing dependency
and fixture warnings remain unsilenced.

| Frozen set | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| phase3a2 | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` | `c64f5280ed274fe25dd6556028d7e924da6b5c2196c4214f1fc11d7da944c350` |
| phase4 | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` | `35ea23dbb976c1ddf5cb176c6f095d9226063e891bca23ba355087369945b8b4` |
| Phase 5 question/relevance | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` | `f9e6d1eb712a772d4fac98479a98676b54ab9e7fb05219df8a1ecf667ee960b4` |

All four Phase 5 evaluation files match. All 967 Phase 4 artifacts, including
models, figures, predictions and scores, are byte-identical. Database fingerprints
match for all 3,948 stored forecasts, 150 model versions and 21 evaluations.
The 65 pre-existing result/screenshot files other than the explicitly requested
WRITEUP update are unchanged, including the whole Phase 7 data snapshot. This
protects every original numeric value in those records, rather than assuming
an unspecified “183 original numbers” subset. There was no training, model
selection, evaluation rerun, frozen-label edit or historical forecast write.

## Browser checks

Dashboard forecast section, browsable forecast API and Mumbai forecast cards
passed at 1440 and 390 pixels: HTTP 200, visible forecast_method labels, no
horizontal document overflow and no JavaScript errors. The API screenshot shows
the policy fields at the top; fallback cards explicitly mark intervals unavailable.

| Page | Desktop | Phone |
| --- | --- | --- |
| Dashboard | [1440](phase7-fix-dashboard-1440.png) | [390](phase7-fix-dashboard-390.png) |
| Forecast API | [1440](phase7-fix-api-1440.png) | [390](phase7-fix-api-390.png) |
| Forecast cards | [1440](phase7-fix-forecasts-1440.png) | [390](phase7-fix-forecasts-390.png) |

The first network probe overlapped a logged Django development-server reload;
the stable rerun passed. Initial formatting findings and a documentation edit
matcher failure were corrected and retained in the [command journal](../VALIDATION.md).
Browser review also caught JavaScript treating null interval bounds as zero in
the exclusion message; the guard and text now handle absent fallback intervals.

## Handoff and limitations

The policy is post-evaluation and has no independent future-period score.
Fallback intervals are deliberately unavailable; original coverage failures remain
in the archived evaluation. Historical replay requires retained cohort inputs;
a missing issue-day input returns 503. Existing live rows without captured
persistence_value also return 503; new issuance captures that value. No debug
model-output flag was added. Model paths outside the override remain unchanged.

Machine-readable evidence: [PHASE7_FIX_METRICS.json](PHASE7_FIX_METRICS.json).
Raw logs/helpers are retained in `data/results/phase7fix/manifest.json`.
Final Git arguments, actual output and commit identity are retained in
`data/results/phase7fix/final-git.json`, following the existing journal convention
to avoid a self-referential commit hash. Commit locally only; do not push.
