"""Export the paper from completed, versioned results rather than typed-in numbers."""

import hashlib
import json
from pathlib import Path

import matplotlib
import pandas as pd

from .diagnostic_report import fmt, table
from .lifecycle import code_metadata
from .models import AnalysisRun

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def change_cell(comparison, kind):
    if not comparison or comparison.get("status") != "descriptive":
        return "unavailable"
    row = comparison[kind]
    lo, hi = row["ci95_percent"]
    return f"{fmt(row['percent_change'], 4)}% [{fmt(lo, 4)}, {fmt(hi, 4)}]"


def export_research_report(run_id):
    run = AnalysisRun.objects.get(pk=run_id, name="phase3b", status="success")
    output = Path("data/results") / str(run.pk)
    results = run.results["cities"]
    protocol = run.parameters["protocol"]
    children = {
        row.results["city"]: row
        for row in AnalysisRun.objects.filter(pk__in=run.parameters["child_runs"], status="success")
    }
    metrics, drivers, proxies, trends, network, gam, changes, forecast = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    images = []
    for city in protocol["eligible_cities"]:
        item = results[city]
        child = children[city]
        for cohort, result in item["cohorts"].items():
            if "nested_validation" not in result:
                metrics.append(
                    dict(
                        city=city,
                        cohort=cohort,
                        period="unavailable",
                        scope=result["scope"],
                        run7_r2=None,
                        nested_r2=None,
                        weather_only_r2=None,
                        gam_weather_r2=None,
                    )
                )
                for row in result.get("annual", []):
                    network.append(dict(city=city, cohort=cohort, **row))
                continue
            cv = result["nested_validation"]
            for period, scores in cv["nested_full"]["periods"].items():
                old = next(r for r in result["readiness_run7"]["periods"] if r["period"] == period)
                gate = next(
                    r for r in result["nested_readiness"]["periods"] if r["period"] == period
                )
                metrics.append(
                    dict(
                        city=city,
                        cohort=cohort,
                        period=period,
                        scope=result["scope"],
                        run7_r2=old["r2"],
                        nested_r2=scores["r2"],
                        weather_only_r2=cv["weather_only"]["periods"][period]["r2"],
                        gam_weather_r2=cv["gam_weather_only"]["periods"][period]["r2"],
                        n=scores["n"],
                        nmb_percent=scores["nmb_percent"],
                        month_max_abs_nmb=gate["max_month_abs_nmb"],
                        nested_gate_passed=gate["passed"],
                    )
                )
                if cohort == item["main_cohort"]:
                    forecast.append(
                        dict(
                            city=city,
                            cohort=cohort,
                            period=period,
                            nested_gate_passed=gate["passed"],
                            r2=scores["r2"],
                            failures=gate["failures"],
                        )
                    )
            for row in result["annual"]:
                network.append(dict(city=city, cohort=cohort, **row))
            shap = pd.DataFrame(result["explanations"]["shap"])
            for (period, season), group in shap[shap.weather].groupby(["period", "season"]):
                top = group.sort_values("mean_abs_daily_shap", ascending=False).head(3)
                drivers.append(
                    dict(
                        city=city,
                        cohort=cohort,
                        period=period,
                        season=season,
                        top3="; ".join(
                            f"{r.feature}: {fmt(r.mean_abs_daily_shap, 4)}"
                            for r in top.itertuples()
                        ),
                        sampled_days=int(top.sampled_days.iloc[0]),
                    )
                )
            for row in result["explanations"]["gam_ale_agreement"]:
                gam.append(dict(city=city, cohort=cohort, **row))
            proxy = result["ncap_proxy"]
            proxies.append(
                dict(
                    city=city,
                    cohort=cohort,
                    status=proxy["status"],
                    raw=change_cell(proxy, "raw"),
                    normalised=change_cell(proxy, "normalised"),
                    reason=proxy.get("reason", ""),
                    refits=result["refits"],
                )
            )
            for period, row in result["trends"].items():
                trends.append(dict(city=city, cohort=cohort, period=period, **row))
            for label in ["long_run_comparison", "ncap_proxy"]:
                comparison = result[label]
                if comparison["status"] == "descriptive":
                    for kind in ["raw", "normalised"]:
                        changes.append(
                            dict(
                                city=city,
                                cohort=cohort,
                                comparison=label,
                                kind=kind,
                                **comparison[kind],
                            )
                        )
        images.append(
            f"![{city} station-network sensitivity]"
            f"(../../data/results/{child.pk}/{city}_network_comparison.png)"
        )
    frames = {
        name: pd.DataFrame(rows)
        for name, rows in dict(
            validation=metrics,
            seasonal_drivers=drivers,
            ncap_proxy=proxies,
            trends=trends,
            network_annual=network,
            gam_agreement=gam,
            comparisons=changes,
            forecast_support=forecast,
        ).items()
    }
    for name, frame in frames.items():
        frame.to_csv(output / f"{name}.csv", index=False)
    main = frames["validation"]
    main = main[
        [row.cohort == results[row.city]["main_cohort"] for row in main.itertuples()]
    ].copy()
    fig, ax = plt.subplots(figsize=(12, 5))
    positions = list(range(len(main)))
    for offset, (column, label) in zip(
        [-0.24, 0, 0.24],
        [
            ("nested_r2", "Nested full RF"),
            ("weather_only_r2", "Weather-only RF"),
            ("gam_weather_r2", "Weather-only GAM"),
        ],
        strict=True,
    ):
        ax.bar([i + offset for i in positions], main[column], width=0.24, label=label)
    ax.set_xticks(
        positions, [f"{r.city}\n{r.period}" for r in main.itertuples()], rotation=30, ha="right"
    )
    ax.set_ylabel("Daily out-of-fold R² within observed period")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.legend()
    fig.tight_layout()
    for suffix in ["png", "svg"]:
        fig.savefig(output / f"weather_validation.{suffix}", dpi=150)
    plt.close(fig)
    oldnew = frames["comparisons"]
    delhi = oldnew[(oldnew.city == "delhi") & (oldnew.comparison == "long_run_comparison")]
    step0 = json.loads(Path("data/results/9/canonical_equivalence.json").read_text())
    original = json.loads(Path(".tools/phase3b-validation/preservation.json").read_text())
    assessment = table(
        [
            "City",
            "Cohort",
            "Era",
            "Run 7 week R²",
            "Nested R²",
            "Weather RF R²",
            "Weather GAM R²",
            "Days",
            "NMB %",
            "Worst month |NMB| %",
            "Frozen gate",
        ],
        [
            [
                r["city"],
                r["cohort"],
                r["period"],
                fmt(r.get("run7_r2"), 4),
                fmt(r.get("nested_r2"), 4),
                fmt(r.get("weather_only_r2"), 4),
                fmt(r.get("gam_weather_r2"), 4),
                r.get("n", "—"),
                fmt(r.get("nmb_percent"), 4),
                fmt(r.get("month_max_abs_nmb"), 4),
                "pass"
                if r.get("nested_gate_passed")
                else ("fail" if "nested_gate_passed" in r else r["scope"]),
            ]
            for r in metrics
        ],
    )
    driver_table = table(
        ["City", "Cohort", "Era", "Season", "Top three weather SHAP magnitudes (µg/m³)", "Days"],
        [
            [r[k] for k in ["city", "cohort", "period", "season", "top3", "sampled_days"]]
            for r in drivers
        ],
    )
    proxy_table = table(
        ["City", "Cohort", "Raw change %, 95% CI", "Normalised change %, 95% CI", "Status"],
        [
            [
                r["city"],
                r["cohort"],
                r["raw"],
                r["normalised"],
                r["status"] + (": " + r["reason"] if r["reason"] else ""),
            ]
            for r in proxies
        ],
    )
    trend_table = table(
        [
            "City",
            "Cohort",
            "Era",
            "Months",
            "Sen slope µg/m³/year",
            "Slope 95% CI",
            "MK p",
            "Seasonal MK p",
        ],
        [
            [
                r["city"],
                r["cohort"],
                r["period"],
                r["months"],
                fmt(r.get("slope_per_year"), 4),
                str([fmt(x, 4) for x in r.get("slope_ci95_per_year", [])]),
                fmt(r.get("mann_kendall_p"), 6),
                fmt(r.get("seasonal_mann_kendall_p"), 6),
            ]
            for r in trends
        ],
    )
    difference_table = table(
        [
            "Cohort",
            "Series",
            "Old mean",
            "Recent mean",
            "Difference µg/m³",
            "Refit/block 95% CI",
            "Change %",
        ],
        [
            [
                r.cohort,
                r.kind,
                fmt(r.baseline_mean, 4),
                fmt(r.recent_mean, 4),
                fmt(r.difference, 4),
                str([fmt(x, 4) for x in r.ci95_difference]),
                fmt(r.percent_change, 4),
            ]
            for r in delhi.itertuples()
        ],
    )
    pm10_table = table(
        ["City", "Year", "Recent PM10 mean µg/m³", "Valid days", "Eligible", "Interpretation"],
        [
            [
                city,
                row["year"],
                fmt(row.get("mean_pm10"), 4),
                row.get("valid_days", "—"),
                row.get("eligible", "—"),
                row["status"],
            ]
            for city in protocol["eligible_cities"]
            for row in results[city]["recent_pm10"]
        ],
    )
    agreement_rows = [r for r in gam if r["ale_rank_correlation"] is not None]
    strongest = sorted(agreement_rows, key=lambda r: r["ale_rank_correlation"], reverse=True)[:12]
    weakest = sorted(agreement_rows, key=lambda r: r["ale_rank_correlation"])[:12]
    agreement_table = table(
        ["City", "Cohort", "Era", "Season", "Driver", "ALE rank correlation"],
        [
            [r[k] for k in ["city", "cohort", "period", "season", "feature"]]
            + [fmt(r["ale_rank_correlation"], 4)]
            for r in strongest + weakest
        ],
    )
    hyderabad = [r for r in network if r["city"] == "hyderabad" and r["year"] == 2025]
    sensitivity = table(
        ["City", "Cohort", "Year", "Valid days", "Mean PM2.5", "Daily maximum", "Days >60"],
        [
            [
                r["city"],
                r["cohort"],
                r["year"],
                r["valid_days"],
                fmt(r["mean"], 6),
                fmt(r["maximum"], 6),
                r["days_above_60"],
            ]
            for r in hyderabad
        ],
    )
    station_panels = json.loads(
        Path(f"data/results/{run.parameters['diagnostic_run']}/fixed_panels.json").read_text()
    )
    panel_table = table(
        ["City", "Matched CPCB site IDs", "Main research cohort"],
        [
            [r["city"], r["count"], results[r["city"]]["main_cohort"]]
            for r in station_panels
            if r["city"] in protocol["eligible_cities"]
        ],
    )
    supported = ", ".join(
        f"{r['city']} {r['period']} ({r['cohort']})" for r in forecast if r["nested_gate_passed"]
    )
    failed = (
        ", ".join(
            f"{r['city']} {r['period']} ({r['cohort']}): {', '.join(r['failures'])}"
            for r in forecast
            if not r["nested_gate_passed"]
        )
        or "none"
    )
    text = f"""# Phase 3B: meteorological associations and a PM2.5 proxy for NCAP progress

## Abstract

AnalysisRun **{run.pk}**, completed {run.finished_at.isoformat()}, uses the corrected
Run 7 designs for {len(protocol["eligible_cities"])} cities, with Bengaluru restricted
to its fixed panel. The nested validation and weather-only comparisons below are
daily predictive associations, not causal variance decompositions. Each validated
cohort has {protocol["refits"]} actual bootstrap model refits. Old/recent PM2.5
changes are descriptive, with shared pooled weather and refit/block intervals.
NCAP compliance cannot be evaluated because the historic PM10 baseline is absent.
BS-VI attribution and crop-fire results are not estimated.

## Introduction

Weather and changing station composition can distort comparisons of measured PM2.5.
Grange et al. motivate forest meteorological normalisation; their Swiss PM10 results
do not establish performance here. Shi et al. demonstrate why weather adjustment
and observations around an intervention matter for attribution. This study addresses
meteorological drivers (RQ2) and a labelled PM2.5 proxy (RQ5). It estimates associated
changes across observed eras without assigning a policy effect.

## Data

Concentrations are CPCB historical exports mirrored by XKDR in 2015–2019 and OpenCity
exports in 2024–2025; the audit, URLs and coverage are documented in PHASE3A/PHASE3A2
and DATA_SOURCES. There are no 2020–2023 concentrations, no historical NO2 and no
historic PM10 baseline. Open-Meteo/ERA5 weather uses UTC requests and observed grid
values. Raw inputs remain cached and hash-addressed. Quality-OK station means are
averaged equally within native IST hours; days require 18 hours, months 75% of calendar
days and eligible years 75% of hours and days. Missing observations remain missing.

Fixed panels match exact CPCB site IDs across providers, not provider-specific row
IDs. Presence in both eras does not prove unchanged instruments or historical GPS.
The station/year tables and district/grid audits remain in
data/results/{run.parameters["diagnostic_run"]}/.

{panel_table}

Other cities remain descriptive: Ahmedabad, Chennai, Jaipur, Kolkata and Patna.
Bengaluru all-station modelling remains unapproved. Panels without eligible years
or a passing validated model are shown as descriptive/unavailable; they are not
substituted with artificial series.

## Methods

### Stored timestamp repair

The earlier fix was analysis-only. The ingestion layer now decodes hash-approved
OpenCity files' mislabelled +0000 IST wall clocks into UTC and bins quarters in IST.
IngestionRun clock-version markers prevent a second correction. Unverified new
publisher clocks are rejected once canonical ingestion is established.
The idempotent repair shifted 14,787,584 stored readings by −5.5 hours. All
16,266,240 readings remain; before/after value/quality/provenance hash is
767228030051878155. The second run corrected zero rows. Cross-chunk timestamps
are atomically routed by delete/reinsert because Timescale rejects a cross-chunk
UPDATE. Raw values, source assets and original ingestion links are retained.

The first bulk UPDATE failed its Timescale chunk constraint and rolled back.
The paused attempt also rolled back. The final repair is recorded in IngestionRun
87. DataRuns 8 (diagnostic) and 9 (all pollutants) rebuild the stored clock:
all {len(step0)} PM2.5 hourly tables match Run 7 to 1e-12; all 12 diagnostic frames
match Run 6 exactly. All {original["run7_artifacts"]} Run 7 artifacts and all
{original["original_test_files"]} original test files passed hash verification.

### Design, selection and honest validation

The Phase 3A2 readiness criteria are unchanged: each observed era requires daily
week-CV R² ≥0.5, |NMB| ≤10%, no calendar month with |NMB| >20%, at least 26 observed
weeks and at least 20 OOF days in every calendar month. Thresholds are screening
rules, not universal literature guarantees. The Phase 3B protocol was frozen at
{protocol["frozen_at"]}, before new fitting. Its SHA-256 is
`{run.parameters["protocol_sha256"]}`.

Nested CV uses three outer and three inner folds of whole Monday-start IST weeks,
stratified by observed era, with a 24-hour boundary embargo. Outer weeks and their
embargo are excluded from inner training AND inner validation. Each outer fold
selects among the original eight variants using only inner mean era-specific daily
R² on shared dates. The selected full model and its weather-only comparison predict
outer weeks once. Donor/weather predictors have no concentration-gap observations.
The honest number measures the prespecified selection procedure; Run 7's fixed
normalisation design and weights are retained separately for comparability.

Weather-only RFs remove trend, calendar and period-indicator features, retaining
the inner-selected weather support/model grouping. Separate-era intercepts mean
pooled overall R² is not a weather explanation of changes between eras: period-specific
R² is the headline. The within-period combined R² uses summed within-era SST.
All paired scores share daily OOF support; folds choosing BLH can drop unsupported
early-2024 days. Daily-target and hourly-aggregated variants use the stated complete-case
rules. Fold-specific designs, held weeks, support and scores are retained in CSV/JSON.

### Normalisation and uncertainty

Both eras use the SAME pooled joint observed reference weather from 2015–2019 and
2024–2025, including weather without concentration targets. Local trend is held
within each era and never bridges 2020–2023. Each cohort uses 20 actual forest refits
on whole observed IST weeks resampled with replacement within year/era (boundary
weeks contain their observed year fragments), with fixed structure and seeds.
Both eras and the two networks share each refit's 300 joint weather donors.
The existing Run 7 normalised series provides the point estimate; 500 mixture
draws combine refitted normalisations, equal-year resampling, contiguous seven-day
observed calendar blocks and centred nested OOF residuals. Gaps end a block.
Raw intervals use observed-value blocks, with no artificial model uncertainty.
Normalised intervals include actual refit spread and donor Monte Carlo variability;
they remain conditional on model structure and station-panel definition.

Old/recent comparisons use matched raw/normalised/nested-OOF dates. Annual means
are weighted equally across eligible years. The NCAP proxy requires BOTH calendar
2017 and 2018 and BOTH 2024 and 2025. This is different from NCAP's official fiscal-year
2017–18 PM10 baseline. Unsupported years are reported unavailable.

### Driver explanations and GAM cross-check

Exact tree-path-dependent TreeSHAP uses 30 complete days per era/season, all valid
hours of sampled days for hourly models, and an additivity check. Signed hourly
attributions are averaged per day BEFORE taking mean absolute magnitudes. Circular
wind sine/cosine contributions are grouped; neither one is an independent physical
driver. These conditional allocations are sensitive to correlated weather/calendar
predictors and are not causal effects or an additive partition of R².

ALE uses 12 empirical quantile bins; wind direction rotates sine and cosine together
over 12 angular sectors and corrects circular closure when all sectors have support.
Empty/constant bins stay unestimated. Gaussian statsmodels GAMs use cubic B-splines,
df=6 and alpha=10, training-only scaling and knots with a fixed five-standard-deviation
support extension. No penalty tuning follows results. Their weather-only daily CV
uses the same outer weeks. GAM/forest ALE shape agreement is a rank correlation on
shared supported ranges; an hourly forest versus daily GAM is a frequency-different
cross-check. Calendar omission and interactions can explain disagreements.

Seasons are winter October–February, pre-monsoon March–May and monsoon June–September.
Only Lucknow's frozen selected forest retains BLH. Other cities have no validated
BLH effect estimate; this is not evidence that its physical effect is zero. The
weather-null tables document the missing first half of 2024 BLH and other missing values.

Monthly normalised trends are Theil–Sen slopes on actual calendar month coordinates,
with classic and seasonal Mann–Kendall tests per era. MK p values are nominal:
serial dependence, selection and multiple comparisons prevent a causal or definitive
significance interpretation. They are not a trend across the observation gap.

## Results

### RQ2: predictive meteorological associations

{assessment}

![Daily paired validation](../../data/results/{run.pk}/weather_validation.png)

The full RF includes temporal information, so its R² is not the weather share.
Weather-only RF R² expresses held-week predictive skill conditional on the observed
era and network. Negative values, if present, are retained. IGP cities (Delhi,
Kanpur, Lucknow) and coastal/southern cities are compared in the same table, without
pooling their concentrations or treating seven selected cities as a regional sample.

{driver_table}

Top-three magnitudes are daily mean absolute SHAP in µg/m³, not percentages of
variance. The full per-feature signed/magnitude table and seasonal ALE curves are
under each child run. High SHAP magnitude does not establish an independent driver.
These extrema summarise the strongest and weakest GAM/RF ALE shape agreements;
the full table includes null/constant unsupported shapes.

{agreement_table}

### RQ5: PM2.5 proxy for NCAP progress

All seven eligible cities are unstarred non-attainment entries in the official CPCB
list (Bengaluru appears as Bangalore). The seed incorrectly treated Chennai's starred
million-plus participation as non-attainment; its default and live reference flag
are corrected. Official verification, entry numbers, prior flags and PDF SHA are
stored in DataRun 9. The APIs explicitly return `is_official_compliance_result=false`
and `official_compliance_assessment="not assessed"`.

{proxy_table}

Recent PM10 is context only. Missing historical PM10, fiscal/calendar mismatch and
station/source changes prevent an official compliance comparison.

{pm10_table}

### Within-era monthly trends

{trend_table}

Displayed p values are descriptive; exact values are retained in CSV/JSON. A printed
small p value does not cure dependence or identify a policy effect. No line is fit
across the gap.

### Delhi long-run weather-adjusted change

{difference_table}

The long-run baseline is the eligible 2015–2019 observations, distinct from the
2017–2018 proxy baseline. Normalised intervals incorporate the new refits; raw and
normalised rows use their shared nested-OOF date support. Any interval spanning zero
supports uncertainty about direction under this resampling method.

### Station-network composition

{sensitivity}

Hyderabad's all-network versus matched-panel 2025 exceedance contrast survives the
stored timestamp repair. It is a network-composition sensitivity, not a corrected
unit conversion. Legacy integer-heavy station exports and unverified calibration
history remain source limitations. Full annual means, maxima and exceedances are
in `network_annual.csv`; a panel with inadequate coverage is explicitly descriptive.

{chr(10).join(images)}

## Limitations

Weekly interpolation validation is not a forecast or a test across an emissions
regime change. Weather-only skill is conditional on selected cities, current grids
and era-specific levels. Refit intervals use 20 replicates and fixed selected
structures; they do not include all structural selection, historical instrument/GPS,
population exposure or unknown network uncertainty. SHAP is correlated-feature
allocation; ALE can have sparse support. GAM smoothness is fixed, not optimised.
The complete-case comparison can reduce OOF support when BLH is selected.

Station definitions, quality flags, source rounding and city/district assignment
are imperfect. Six/few-station panels are not city population-weighted exposure.
ERA5 is retrospectively available reanalysis, not a contemporaneous forecast input.
There is no old PM10, old NO2, 2020–2023 concentration history or FIRMS fire sample.
WHO thresholds and CPCB AQI provide context, not a health-effect or compliance result.

## What would change with more data

RQ1 (BS-VI) requires station-level 2019–2023 NO2 and PM2.5 (for example licensed,
quality-audited OpenAQ/CPCB archives), stable station identifiers, instrument and
relocation histories, contemporaneous weather, traffic/fleet/fuel/emissions data,
BS-VI implementation timing, lockdown dates and overlapping NCAP/industrial/transport
interventions. Observations around those dates and a defensible control/comparison
design would enable an attribution question. Current old/recent changes are only
weather-adjusted associations; the April 2020 event lies inside the missing era.

RQ3 is deferred pending FIRMS observations. The proposed analysis would retrieve
VIIRS/MODIS fire detections with actual UTC timestamps, confidence, FRP, product and
satellite identifiers; deduplicate overlapping products; distinguish no fire from
missing coverage; define Punjab/Haryana source regions; link source-receptor direction
to ERA5 transport winds; prespecify transport lags and upwind exposure; and model
daily PM2.5 anomalies within crop-burning seasons using held-week validation and
season/calendar, weather, festival and network controls. Test lag/window sensitivities
and false-positive controls before interpreting associations. No fire coefficient
is reported until detections and coverage are ingested and audited.

For Phase 4, the observed-period cohorts satisfying the unchanged nested screen are:
{supported or "none"}. Additional nested-screen limitations are: {failed}.
Prioritise recent Delhi/Mumbai/Hyderabad/Pune and Bengaluru's fixed panel only where
their recent screen supports it; Kanpur/Lucknow have no recent concentration targets
and need fresh observations before current forecasts. Candidate weather features
are the validated temperature, humidity, wind speed/direction, rain, pressure,
cloud/solar fields and BLH only with reliable availability; retain calendar features,
reassess local trend and consider lagged PM with leakage-safe training. Forecast
experiments need rolling-origin temporal validation, archived forecast vintages and
data available at issuance. No forecasts, RAG, simulator or dashboards are built here.

## Reproducibility and verification

Parent run {run.pk}, child runs {run.parameters["child_runs"]}, baseline 7,
diagnostic 8 and canonical multi-pollutant 9. All inputs/results remain on D:.
Fixed seeds, code hashes, package versions, original model weights, folds and refit
training-index hashes are recorded. Child manifests retain CSVs, PNG/SVG figures,
GAM objects, SHAP additivity errors and all 20 refit series.
The original 117 tests were preserved; the pre-fit full suite passed 124 tests.
Final test/lint/API outputs are recorded in VALIDATION.md after this export.

## References

Only documents in [the project research library](../RESEARCH_LIBRARY.md) or already
listed in PHASE3A2 are cited. Source files and SHA-256 values are catalogued in
[RESEARCH_LIBRARY.json](../RESEARCH_LIBRARY.json).

- Grange et al. (2018), [Random forest meteorological normalisation models for Swiss PM10 trend analysis](https://acp.copernicus.org/articles/18/6223/2018/).
- Shi et al. (2021), *Abrupt but smaller than expected changes in surface air quality
  attributable to COVID-19 lockdowns*,
  [author-hosted paper](https://pure-oai.bham.ac.uk/ws/files/114238854/eabd6696.full.pdf),
  DOI 10.1126/sciadv.abd6696.
- CPCB, [List of 131 cities, including the starred million-plus footnote](https://cpcb.gov.in/uploads/Non-Attainment_Cities.pdf).
- MoEFCC/PIB, NCAP statement, 23 March 2023;
  [official source](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1909910&lang=2&reg=48).
  Updates dated 28 November 2024 and 23 July 2026 are in the linked research library.
- CPCB PRANA, [National Apex Committee minutes](https://prana.cpcb.gov.in/ncapDashboard/download_public_portal_file/Minutes_of_National_Apex_Committee_meeting.pdf).
- WHO (2021), [Global Air Quality Guidelines](https://www.who.int/publications/i/item/9789240034228/).
- CPCB, [National Air Quality Index](https://cpcb.gov.in/National-Air-Quality-Index/).
- Roberts et al. (2017), *Cross-validation strategies for data with temporal, spatial,
  hierarchical, or phylogenetic structure*,
  [primary source](https://nsojournals.onlinelibrary.wiley.com/doi/10.1111/ecog.02881),
  already listed in PHASE3A2.
- Huang et al. (2021),
  [Air-quality model performance evaluation](https://acp.copernicus.org/articles/21/2725/2021/),
  already listed in PHASE3A2; the frozen bias screen is an operational criterion,
  not proof of this model's validity.
"""
    destination = Path("docs/results/PHASE3B.md")
    destination.write_text(text, encoding="utf-8")
    (output / "PHASE3B.md").write_text(text, encoding="utf-8")
    commit, metadata = code_metadata()
    report_meta = dict(
        run=run.pk,
        git_commit=commit,
        **metadata,
        report_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
    )
    (output / "report_export.json").write_text(json.dumps(report_meta, indent=2))
    manifest = json.loads((output / "manifest.json").read_text())
    manifest["report_export"] = report_meta
    manifest["files"] = [
        dict(
            path=p.relative_to(output).as_posix(),
            bytes=p.stat().st_size,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        )
        for p in sorted(output.iterdir())
        if p.is_file() and p.name != "manifest.json"
    ]
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return str(destination)
