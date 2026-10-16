# Five-minute demo

Use the retained development database and artifacts. Start with
`scripts/dev.ps1 health`, then open the dashboard, forecasts, Ask and VayuSim
tabs. A fresh reference-only installation cannot reproduce the historical
interactive demo. Keep the local LLM off; do not trigger model downloads or
rerun evaluations during the demonstration. The script below totals **5:00**.

| Time | Show | Say / action |
| --- | --- | --- |
| 0:00–0:40 | `/dashboard/`, limits first | “This is an evidence dashboard. Urban C/F dispersion is an unvalidated branch, the local generator failed its quality gate, and forecast skill varies. Every figure links to a stored file.” Open a source link briefly. |
| 0:40–1:20 | Ingestion and analytics | “17.5M combines concentration and weather rows; flagged or missing records are not all usable measurements. Delhi's −17.59 estimate has an interval spanning zero, so the decline is inconclusive here. Hyderabad's 0 versus 53 exceedances depends on the station cohort.” |
| 1:20–2:10 | Forecast dashboard row, then `/forecasts/?city=delhi` | “The saved Delhi next-day policy improves RMSE by 12.6% against persistence in this backtest. Serving uses persistence for the nine city-horizon combinations where Phase 4 found that the model lost to persistence; the model is used for the others. This override was introduced after the original evaluation; the saved scores have not been recomputed. Fourteen selected interval levels fail their coverage gate. This page shows replay dates, not an unverified live forecast.” Read the displayed target date; do not call it today's forecast. |
| 2:10–3:05 | `/ask/` | Ask: **What was the annual mean PM2.5 in Delhi in 2025?** “This is extractive retrieval with verified citations.” Inspect the actual answer, its units, cohort and linked dataset citation. Do not substitute a memorised value if the answer is unavailable. |
| 3:05–3:35 | Ask refusal | Ask: **What was the annual mean PM2.5 in Delhi in 2020?** Show the actual missing-data response. “The archive lacks this target period. Missing is not zero, and a refusal is better than inventing a number. Exact citation support also does not establish comprehensive answer quality.” |
| 3:35–4:40 | `/vayusim/?run=62` | Keep **unvalidated branch** visible. “This is a hypothetical 1 g/s source, not a measured inventory. The field is a source increment, separate from measured totals. Primary PM2.5, flat terrain and steady hourly weather apply.” Show the stored zero-emission comparison or load the vertical grid; explain its retained inputs. Show the annotated export warning. |
| 4:40–5:00 | Dashboard testing / limitations | “The final test record, frozen hashes and failures are inspectable. Software checks do not establish urban plume performance, causal attribution or deployed reliability. The next work is new evidence and prospective evaluation, not revised frozen labels.” |

If an answer or grid is slow, say “This operation has not completed; here is the
stored evaluation and its timing context.” Use the linked report, clearly labelled
as a stored record. Do not present a screenshot as a fresh successful request.
If a result is negative, name the failure and its consequence: keep persistence
as the baseline, retain an interval failure, or decline an unsupported claim.

The two Ask prompts and visible labels are checked against the actual app during
Phase 7 browser verification; evidence and screenshots are indexed in
[PHASE7.md](results/PHASE7.md). The five-minute schedule is a presentation plan,
not a guarantee of cold local-model latency.
