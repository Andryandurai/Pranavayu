"""Export only stored actual forecasts/scores; no model selection during export."""

import json
import re

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from django.conf import settings

from .models import ForecastModelVersion

matplotlib.use("Agg")


def number(value, digits=3):
    return "undefined" if value is None else f"{value:.{digits}f}"


def export_report(run, output):
    result = json.loads((output / "phase4_results.json").read_text())
    real = [e for e in result["evaluations"] if e["weather"] == "archived_forecast"]
    ideal = [e for e in result["evaluations"] if e["weather"] == "perfect_prognosis"]
    errors = pd.read_csv(output / "seasonal_errors.csv")
    comparisons = []
    for entry in result["evaluations"]:
        for model, score in entry["models"].items():
            comparisons.append(
                {
                    "city": entry["city"],
                    "horizon": entry["horizon"],
                    "weather": entry["weather"],
                    "model": model,
                    **{k: v for k, v in score.items() if k != "dm"},
                    "dm_p_value": score["dm"]["p_value"],
                }
            )
    pd.DataFrame(comparisons).to_csv(output / "model_comparison.csv", index=False)
    coverage = pd.DataFrame(result["weather_coverage"])
    coverage.to_csv(output / "archived_weather_coverage.csv", index=False)
    lines = [
        "# Phase 4: daily PM2.5 forecasting",
        "",
        f"AnalysisRun **{run.pk}**. Primary cities: Hyderabad, Mumbai and Bengaluru's",
        "seven-site fixed panel. Secondary: Delhi, Pune, Chennai and Kolkata. No RAG,",
        "simulator or dashboard is built. Kanpur, Lucknow, Ahmedabad, Jaipur and Patna",
        "are excluded because their concentration archive has no recent targets.",
        "",
        "## Data and leakage rules",
        "",
        "Raw 2024–2025 concentration inputs come from canonical Run 8, with equal-station",
        "hourly means and at least 18 IST hours for each daily target. Fixed-panel inputs",
        "are raw measurements, not deweathered values. Hashes are in input_provenance.json.",
        "",
        "Forecasts target t+1/t+2/t+3 at end-of-day t IST. PM lags, rolling means and",
        "night/day summaries stop at t. Calendar features are known dates. Target weather",
        "uses explicit GFS Global lead offsets from Open-Meteo's Previous Runs archive;",
        "the requested Historical Forecast endpoint was probed and excluded from headline",
        "features because it stitches near-valid-time forecasts. Offsets are h+1 days",
        "with a 12-hour publication allowance. The bound is tested against issue-end.",
        "Exact historical run/publication logs are unavailable: these bounds rely on the",
        "documented lead semantics and a latency assumption. Provider outages cannot be",
        "reconstructed. Historical concentration publication times are also unavailable;",
        "the backtest assumes day-t observations were available at issue-end.",
        "",
        "BLH is excluded because lead-offset archive values are null; it is never filled",
        "from the stitched series or ERA5. Wind direction uses sine/cosine, precipitation",
        "is a daily sum, cloud cover a fraction and wind speed m/s. Hourly UTC forecast",
        "points are assigned to native IST dates; overlapping download windows retain",
        "complete days across the half-hour timezone boundary.",
        "Hourly accumulated rain assigned by its UTC valid-time midpoint approximates",
        "the IST-day boundary within half an hour; it is a weather predictor, not a",
        "claimed exact station precipitation integral.",
        "",
        "## Archived forecast coverage",
        "",
        "| City | Horizon | First target | Last target | 2024–25 days | "
        "Jul–Dec 2025 days / 184 | BLH days |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in result["weather_coverage"]:
        lines.append(
            f"| {row['city']} | {row['horizon']} | {row['first']} | {row['last']} "
            f"| {row['days_2024_2025']} | {row['evaluation_days']} | {row['blh_non_null_days']} |"
        )
    lines += [
        "",
        "Coverage counts require all 24 weather hours and non-null required variables.",
        "They are separate from usable PM/lag target support. Raw assets preserve original",
        "responses, download URL, SHA256, lead settings, licence and IngestionRun links.",
        "",
        "## Evaluation design",
        "",
        "The frozen [protocol](PHASE4_PROTOCOL.md) specifies expanding monthly origins,",
        "a purged 60-day tuning segment and a separate latest 60-day calibration segment.",
        "Only training-window tuning selects parameters and the algorithm. Scalers,",
        "imputers and holiday/lag inputs are audited. SARIMAX filters only labels whose",
        "target date has arrived by t; future target labels are masked. No shuffle occurs.",
        "The latest six target calendar months are evaluated on common real/ideal support.",
        "Monthly origins and omitted support are in split_audit.json and input_provenance.json.",
        "",
        "Point models are persistence, seven-day mean, training-month climatology, direct-",
        "horizon exogenous SARIMAX, LightGBM and a small regularised PyTorch LSTM. LSTM",
        "is selectable only if tuning RMSE beats LightGBM. Diagnostic LSTM scores remain",
        "visible when rejected. Quantile LightGBM is evaluated separately for intervals.",
        "The issued policy may change its algorithm monthly; the evaluation itself never",
        "selects a model from held-out scores. RMSE skill is 1−RMSE/RMSE_persistence.",
        "",
        "## Model comparisons",
        "",
        "RMSE in µg/m³; `policy` is the training-selected issued prediction. A model with",
        "negative skill loses to persistence. The complete MAE, category accuracy, bias,",
        "event counts and DM scores for every model are in model_comparison.csv.",
        "",
        "| City | Horizon | n | Persistence | Mean7 | Climatology | SARIMAX | "
        "LightGBM | LSTM diagnostic | Policy |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in real:
        models = e["models"]
        cells = [
            number(models[name]["rmse"]) if name in models else "unavailable"
            for name in (
                "persistence",
                "mean7",
                "climatology",
                "sarimax",
                "lightgbm",
                "lstm",
                "prediction",
            )
        ]
        lines.append(
            f"| {e['city']} | {e['horizon']} | {models['prediction']['n']} | "
            + " | ".join(cells)
            + " |"
        )
    lines += [
        "",
        "## Issued-policy skill and statistical comparison",
        "",
        "DM compares paired squared-loss forecast sequences using calendar-day Bartlett",
        "HAC through max(7,h−1), the Harvey small-sample correction and a two-sided t test.",
        "P-values are nominal; dependence, model selection and multiple comparisons limit",
        "inference. A significant p-value can favour persistence when skill is negative.",
        "",
        "| City | Horizon | RMSE | MAE | Skill | DM p | Category accuracy | "
        "Monthly chosen algorithms (days) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in real:
        s = e["models"]["prediction"]
        algorithms = ", ".join(f"{k}:{v}" for k, v in e["issued_algorithms"].items())
        lines.append(
            f"| {e['city']} | {e['horizon']} | {number(s['rmse'])} | {number(s['mae'])} "
            f"| {number(s['skill_vs_persistence'])} | {number(s['dm']['p_value'], 5)} "
            f"| {number(s['aqi_category_accuracy'])} | {algorithms} |"
        )
    losers = [
        f"{e['city']} h{e['horizon']}"
        for e in real
        if e["models"]["prediction"]["skill_vs_persistence"] <= 0
    ]
    lines += [
        "",
        "Issued policies failing to beat persistence: "
        + (", ".join(losers) if losers else "none on these scored days")
        + ".",
        "",
        "## CAMS benchmark",
        "",
        result["cams"]["reason"],
        "The real historical PM2.5 sample is retained in the archive probes. It is not",
        "converted into an issue-safe benchmark, and no CAMS skill number is fabricated.",
        "",
        "## Detection of daily means above 60 µg/m³",
        "",
        "Undefined scores have a zero denominator; zero events are not perfect detection.",
        "These are city means, not station maxima or overall air-quality warnings.",
        "",
        "| City | Horizon | Observed events | Hits | Misses | False alarms | POD | FAR | CSI |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in real:
        s = e["models"]["prediction"]
        lines.append(
            f"| {e['city']} | {e['horizon']} | {s['observed_exceedances']} | {s['hits']} "
            f"| {s['misses']} | {s['false_alarms']} | {number(s['pod'])} "
            f"| {number(s['far'])} | {number(s['csi'])} |"
        )
    lines += [
        "",
        "## Prediction intervals",
        "",
        "Selected-policy absolute-residual split-conformal radii use finite-sample higher",
        "order statistics. Quantile LightGBM uses a separate calibration correction and",
        "nested 80/95% bounds. Calibration labels are not refitted. Temporal dependence and",
        "season shifts violate exchangeability; report empirical coverage rather than a",
        "distribution-free deployment guarantee. Bounds are nonnegative.",
        "",
        "| City | Horizon | Policy 80% | Policy 95% | Mean width 80 | "
        "Mean width 95 | Quantile 80% | Quantile 95% |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in real:
        i = e["intervals"]
        lines.append(
            f"| {e['city']} | {e['horizon']} | {number(i['80']['coverage'])} "
            f"| {number(i['95']['coverage'])} | {number(i['80']['mean_width'])} "
            f"| {number(i['95']['mean_width'])} | {number(i['quantile_80']['coverage'])} "
            f"| {number(i['quantile_95']['coverage'])} |"
        )
    lines += [
        "",
        "## Month and season errors",
        "",
        "All city/horizon month and season scores are in seasonal_errors.csv. Winter is",
        "December–February, pre-monsoon March–May, monsoon June–September and post-monsoon",
        "October–November, reusing the forecasting calendar convention.",
        "",
        "| City | Horizon | Month | n | Bias µg/m³ | NMB % | RMSE |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in errors[
        (errors.weather == "archived_forecast")
        & (errors.period == "month")
        & (errors.city.isin(["delhi", "pune"]))
    ].itertuples():
        lines.append(
            f"| {r.city} | {r.horizon} | {r.label} | {r.n} | {r.mean_bias:.3f} "
            f"| {r.nmb_percent:.3f} | {r.rmse:.3f} |"
        )
    lines += [
        "",
        "## Delhi and Pune bias findings",
        "",
        "The [pre-fit investigation](PHASE4_BIAS.md) reproduces the Phase 3B month failures",
        "from saved outer predictions, including actual station counts, design switches",
        "and missing dates. Delhi's pooled no-trend/BLH models overpredict recent low-PM",
        "months; old-era pooling and regression toward the mean are plausible contributors,",
        "not an established unique cause. Pune's May overprediction is modest in absolute",
        "units but exceeds the unchanged percentage gate because the observed mean is low.",
        "",
        "Phase 4 removes old-era targets and introduces observed PM lags with temporal",
        "selection. Its six-month test includes Delhi's July concern but does not include",
        "February/March or Pune's May. It cannot establish that those untested seasonal",
        "biases are fixed. Forecast month errors above are reported without relaxing gates.",
        "",
        "## Perfect-prognosis comparison — retrospective upper-bound experiment",
        "",
        "Observed target-day ERA5 weather is used only in this separately labelled variant.",
        "It is an optimistic information experiment, not a guaranteed mathematical bound:",
        "finite samples and fitted models can produce worse scores despite ideal information.",
        "Positive gap means the ideal-weather policy had lower RMSE. It is never served",
        "as an operational forecast or used to select headline models.",
        "",
        "| City | Horizon | Real-weather policy RMSE | "
        "Ideal-weather policy RMSE | Real−ideal gap |",
        "| --- | --- | --- | --- | --- |",
    ]
    for e in real:
        other = next(i for i in ideal if i["city"] == e["city"] and i["horizon"] == e["horizon"])
        lines.append(
            f"| {e['city']} | {e['horizon']} | {number(e['models']['prediction']['rmse'])} "
            f"| {number(other['models']['prediction']['rmse'])} "
            f"| {number(e['perfect_prognosis_gap_rmse'])} |"
        )
    lines += [
        "",
        "## Operations, provenance and limitations",
        "",
        "Every origin/model and quantile experiment is logged to the local MLflow service;",
        "chosen city/horizon models are registered. Its database and artifacts live under",
        "data/mlflow/ on D:. Forecast versions retain training dates, inner selection metrics,",
        "MLflow IDs, cohort and AnalysisRun. Each issued forecast stores bounds, category,",
        "mode, model version, top five SHAP drivers/values and feature availability audit.",
        "SHAP describes conditional predictions, not causal effects. Only PM2.5 categories",
        "are forecast; an overall CPCB AQI requires other pollutants. Decimal concentrations",
        "use the continuous boundary extension (≤30, ≤60, ≤90, ≤120, ≤250, then severe).",
        "",
        "Daily weather refresh is scheduled before day-end and issuance after midnight IST.",
        "Live mode requires an OpenAQ key, at least 18 fresh current-completed-day hours and",
        "ingestion completed before issue-end. Without this it explicitly replays the latest",
        "archived day. Live mode remains unverified without the user's OpenAQ key; replay",
        "and public live weather are tested. Historical daily source rounding, station-network",
        "changes and missing data remain limitations. Bengaluru's fixed panel does not accept",
        "unmatched new provider IDs. Replay predictions beyond the last observation are unscored.",
        "",
        "No tuning or threshold change follows held-out scores. SARIMAX iteration/convergence",
        "flags are retained; inspect them alongside its errors. The last six months provide",
        "only one seasonal cycle, no external year test and no claim of clinical/regulatory",
        "fitness. Model choice may favour a simple baseline, and negative skill is retained.",
        "",
        "## Notes for Phase 5 citation support",
        "",
        "The future assistant should cite this report, the frozen protocol, prior bias report,",
        "AnalysisRun-specific model_comparison/seasonal_errors/coverage CSVs and input hashes.",
        "Use read-only `/api/forecast/<city>/latest/`, `/history/?start=&end=` (inclusive target",
        "dates), and `/evaluation/`. Always identify city, horizon, issue/target date, cohort,",
        "replay/live mode, model version and weather knowledge. Cite event counts with POD/FAR/CSI",
        "and empirical interval coverage. Never present perfect-prognosis, rejected LSTM,",
        "historical CAMS samples or retrospective best-model scores as live forecast skill.",
        "",
        "References: [Open-Meteo archive](https://open-meteo.com/en/docs/historical-forecast-api),",
        "[Previous Runs](https://open-meteo.com/en/docs/previous-runs-api),",
        "[run/publication semantics](https://open-meteo.com/en/docs/single-runs-api),",
        "[Air Quality API](https://open-meteo.com/en/docs/air-quality-api),",
        "[conformal methods](https://arxiv.org/abs/2107.07511),",
        "[DM/HLN](https://github.com/bank-of-england/forecast_evaluation/blob/main/src/forecast_evaluation/tests/diebold_mariano.py),",
        "[CPCB technical AQI report](https://www.cpcb.gov.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvRklOQUwtUkVQT1JUX0FRSV8ucGRm).",
        "",
    ]
    lines += ["", "## Additional reproducibility evidence", ""]
    cams = result["cams"].get("coverage", [])
    if cams:
        lines += [
            f"CAMS: {sum(r['non_null_hours'] for r in cams)} non-null values out of "
            f"{sum(r['hours'] for r in cams)} requested lead-forecast hours; "
            f"IngestionRun {result['cams']['ingestion_run']}.",
            "",
        ]
    splits = json.loads((output / "split_audit.json").read_text())
    trials = [c for s in splits for c in s["settings"].get("sarimax", {}).get("candidates", [])]
    nonconverged = sum(c.get("converged") is False for c in trials)
    lines += [
        f"SARIMAX tuning convergence: {nonconverged} of {len(trials)} recorded candidates "
        "did not converge within the fixed iteration limit. These flags and warnings "
        "remain visible; finite predictions do not prove a stable fitted likelihood.",
        "",
        "SARIMAX SHAP describes current exogenous terms conditional on the filtered "
        "known history; it does not allocate the dynamic past-state contribution. "
        "Correlated feature attributions and this conditioning limit interpretation.",
        "",
        "Archived weather deliberately uses older leads than the latest live forecast. "
        "The deployment weather distribution can differ; live skill is unverified.",
        "",
        "The latest registered selections below use inner tuning, not final test scores. "
        "Their rolling test score is the full monthly-selected policy above.",
        "",
        "| City | Horizon | Latest selected algorithm | Fit label end | Inner RMSE |",
        "| --- | --- | --- | --- | --- |",
    ]
    for city in sorted(set(e["city"] for e in real)):
        for horizon in (1, 2, 3):
            version = (
                ForecastModelVersion.objects.filter(
                    analysis_run=run, city__slug=city, horizon=horizon
                )
                .order_by("-available_from", "-pk")
                .first()
            )
            selection = version.validation_metrics["selection"]
            inner = selection["tuning_rmse"][version.algorithm]
            lines.append(
                f"| {city} | {horizon} | {version.algorithm} "
                f"| {version.training_end} | {inner:.3f} |"
            )
    proof_path = output / "verification" / "independent-verification.json"
    if proof_path.exists():
        proof = json.loads(proof_path.read_text())
        lines += [
            "",
            "## Live verification",
            "",
            f"Compute launch Git revision: `{run.git_commit}`. Report export provenance",
            "is recorded separately in the manifest; postprocessing does not refit models.",
            "",
            f"Independent checks covered {proof['prediction_rows']} prediction rows, "
            f"{proof['monthly_origins']} purged origins and "
            f"{proof['registered_versions_checked']} finished MLflow model versions.",
            f"Stored replay forecasts: {proof['stored_forecasts']}. "
            f"All {len(proof['http'])} latest/history/evaluation GETs returned HTTP 200; "
            "POST and invalid-input checks retained their expected 405/400/404 responses.",
            "",
            f"All {proof['original_test_files_unchanged']} original test/support files "
            "retain their baseline hashes. Earlier research artifact hashes and the "
            f"{proof['warehouse']['rows']:,} measurement/provenance fingerprint are unchanged.",
            "",
        ]
        test_log = output / "verification" / "full-tests-final.log"
        if test_log.exists():
            raw = test_log.read_bytes()
            text = raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8")
            summaries = re.findall(r"\d+ passed[^\r\n]*?in [0-9.]+s", text)
            if summaries:
                lines += [f"Full suite: `{summaries[-1]}`. Warnings remain visible.", ""]
    lines += [
        "",
        "## Figures",
        "",
        f"![Issued-policy skill](../../data/results/{run.pk}/forecast_skill.png)",
        "",
    ]
    for city in sorted(set(e["city"] for e in real)):
        lines.append(
            f"[{city.title()} observed/issued forecasts and 95% intervals]"
            f"(../../data/results/{run.pk}/{city}_forecast_evaluation.png)"
        )
    lines.append("")
    text = "\n".join(lines)
    (settings.BASE_DIR / "docs" / "results" / "PHASE4.md").write_text(text, encoding="utf-8")
    mirror = text.replace("(PHASE4_PROTOCOL.md)", "(protocol.md)")
    mirror = mirror.replace("(PHASE4_BIAS.md)", "(../../../docs/results/PHASE4_BIAS.md)")
    mirror = mirror.replace(f"(../../data/results/{run.pk}/", "(")
    (output / "PHASE4.md").write_text(mirror, encoding="utf-8")
    plot_results(output, real)
    return result


def plot_results(output, evaluations):
    frame = pd.read_csv(output / "predictions.csv", parse_dates=["target_date"])
    real = frame[frame.weather == "archived_forecast"]
    for city, rows in real.groupby("city"):
        fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
        for horizon, ax in zip((1, 2, 3), axes, strict=True):
            part = rows[rows.horizon == horizon].sort_values("target_date")
            ax.plot(part.target_date, part.y, label="Observed", color="black", linewidth=1)
            ax.plot(part.target_date, part.prediction, label="Issued policy", linewidth=1)
            ax.fill_between(
                part.target_date, part.lower95, part.upper95, alpha=0.15, label="95% interval"
            )
            ax.set_ylabel(f"h{horizon} PM2.5\n(µg/m³)")
        axes[0].legend(fontsize=8)
        fig.suptitle(f"{city.title()}: rolling-origin archived-weather forecasts")
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(output / f"{city}_forecast_evaluation.png", dpi=150)
        plt.close(fig)
    cities = sorted(set(e["city"] for e in evaluations))
    matrix = np.array(
        [
            [
                next(
                    e["models"]["prediction"]["skill_vs_persistence"]
                    for e in evaluations
                    if e["city"] == city and e["horizon"] == h
                )
                for h in (1, 2, 3)
            ]
            for city in cities
        ]
    )
    fig, ax = plt.subplots(figsize=(7, 5))
    limit = max(0.05, float(np.abs(matrix).max()))
    im = ax.imshow(matrix, cmap="RdBu", vmin=-limit, vmax=limit)
    ax.set_xticks([0, 1, 2], ["t+1", "t+2", "t+3"])
    ax.set_yticks(range(len(cities)), cities)
    for i in range(len(cities)):
        for j in range(3):
            ax.text(j, i, f"{matrix[i, j]:.3f}", ha="center", va="center")
    fig.colorbar(im, ax=ax, label="1 − RMSE / persistence RMSE")
    ax.set_title("Issued-policy skill\nNegative values lose to persistence")
    fig.tight_layout()
    fig.savefig(output / "forecast_skill.png", dpi=150)
    plt.close(fig)
