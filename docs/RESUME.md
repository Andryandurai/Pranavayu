# Resume lines grounded in the project record

- Built a GeoDjango/PostgreSQL air-quality warehouse with a dated **17.5M combined
  concentration/weather-row** snapshot and provenance-aware quality flags; traced
  and repaired a source-specific **5½-hour** timestamp error while preserving
  frozen earlier evaluations.
- Audited weather normalisation and station-network sensitivity; reported Delhi's
  fixed-panel change of **−17.59 µg/m³** with refit interval **[−35.07, +1.66]**
  as inconclusive, and exposed Hyderabad's cohort-dependent **0 versus 53**
  exceedance days.
- Implemented rolling daily PM2.5 forecasting: Delhi next-day RMSE improved
  **12.6%** against persistence in the saved backtest; disclosed **nine** losing
  policies, the incomplete operational fallback and **14** interval-level
  coverage failures.
- Built extractive retrieval with verified citations across **29 documents and
  7,194 chunks**, reaching **80.31% recall@5** on frozen literature questions;
  exact-support checks do not establish complete answer quality, and the opt-in
  local generator failed its quality gate.
- Built a NumPy source-dispersion interface with retained **200×200** grids and
  cached hourly playback; Delhi day preparation measured **2.742 s** with no
  further grid/overlay requests during scrubbing. Urban C/F lack independent
  numeric-case support; sources are hypothetical.

## Likely interview questions

| Bullet | Question to prepare | Where the answer is |
| --- | --- | --- |
| Warehouse | What counts as a row, and how did you distinguish a clock bug from a physical lag? | [Write-up §2](results/WRITEUP.md#2-data-and-quality-control), [snapshot](results/PHASE7_DATA.json) |
| Analytics | Why is a negative estimate inconclusive, and why do station cohorts change exceedances? | [Write-up §3](results/WRITEUP.md#3-analytics-findings), [Phase 3B](results/PHASE3B.md) |
| Forecasts | How was leakage controlled, what lost to persistence, and is fallback actually enforced? | [Write-up §4](results/WRITEUP.md#4-forecasting-results), [protocol](results/PHASE4_PROTOCOL.md) |
| Retrieval | What is recall's denominator, and why do citation matches differ from useful answers? | [Write-up §5](results/WRITEUP.md#5-the-research-assistant), [Phase 5](results/PHASE5.md) |
| VayuSim | What does an equation check establish, and what does cached browser timing exclude? | [Write-up §6](results/WRITEUP.md#6-vayusim-equations-and-scope), [Phase 6B](results/PHASE6B.md) |

Use the snapshot/evaluation dates when discussing these numbers. Do not imply
that missing credentialed sources were ingested or that external hosting was
completed. The final test-count record is in [Phase 7](results/PHASE7.md).
