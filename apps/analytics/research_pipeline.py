"""Observed-only Phase 3B research, preserving the frozen Run 7 designs."""

import gc
import hashlib
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from apps.warehouse.models import City

from .aggregation import aggregate_daily, aggregate_monthly
from .lifecycle import analysis_run
from .model_diagnostics import period_labels, readiness
from .models import AnalysisRun, CityCoverage, CityMetric
from .research_context import pm10_context
from .research_explain import explain_models
from .research_models import nested_validation, week_partition
from .research_stats import trend_test
from .research_uncertainty import bootstrap_normalisations, comparison_intervals
from .revised_deweather import eligible_frame, panel_coverage

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def annual_summary(frame):
    daily = aggregate_daily(
        frame, pd.Timestamp("2015-01-01").date(), pd.Timestamp("2025-12-31").date()
    )
    result = []
    for year, group in daily.groupby(pd.to_datetime(daily.date).dt.year):
        observed = group.value.dropna()
        if not len(observed):
            continue
        result.append(
            dict(
                year=int(year),
                valid_days=len(observed),
                mean=float(observed.mean()),
                maximum=float(observed.max()),
                days_above_60=int((observed > 60).sum()),
            )
        )
    return daily.dropna(subset=["value"]), result


def comparison_plot(city, cohorts, output):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    for ax, (first, last) in zip(axes, [(2015, 2019), (2024, 2025)], strict=True):
        for cohort, data in cohorts.items():
            for label, frame in [("raw", data.get("raw")), ("normalised", data.get("normalised"))]:
                if frame is None:
                    continue
                group = frame[pd.to_datetime(frame.date).dt.year.between(first, last)].copy()
                monthly = aggregate_monthly(
                    group,
                    pd.Timestamp(f"{first}-01-01").date(),
                    pd.Timestamp(f"{last}-12-31").date(),
                )
                ax.plot(pd.to_datetime(monthly.date), monthly.value, label=f"{cohort} {label}")
        ax.set_xlim(pd.Timestamp(f"{first}-01-01"), pd.Timestamp(f"{last}-12-31"))
        ax.set_ylabel("PM2.5 (ug/m3)")
        ax.set_title(f"{city.name}, {first}–{last}")
        ax.legend(fontsize=8)
    fig.tight_layout()
    for extension in ["png", "svg"]:
        fig.savefig(output / f"{city.slug}_network_comparison.{extension}", dpi=150)
    plt.close(fig)


def city_research(city_slug, diagnostic_run, stored_run, protocol):
    city = City.objects.get(slug=city_slug)
    inputs = Path("data/results") / str(diagnostic_run)
    baseline = Path("data/results/7")
    selected = json.loads((baseline / f"{city_slug}_revised_model.json").read_text())
    config = selected["selected_design"]
    weather = pd.read_pickle(inputs / f"{city_slug}_weather.pkl")
    coverage = list(
        CityCoverage.objects.filter(run_id=diagnostic_run, city=city).values("year", "eligible")
    )
    full = pd.read_pickle(inputs / f"{city_slug}_hourly.pkl")
    all_frame = eligible_frame(full, coverage)
    panel_path = inputs / f"{city_slug}_panel_hourly.pkl"
    cohorts = {"all_stations": all_frame}
    if panel_path.exists():
        panel = pd.read_pickle(panel_path)
        panel = eligible_frame(
            panel,
            panel_coverage(
                panel, pd.Timestamp("2015-01-01").date(), pd.Timestamp("2025-12-31").date()
            ),
        )
        if not panel.empty:
            cohorts["fixed_panel"] = panel
    with analysis_run(
        name="phase3b-city",
        start="2015-01-01",
        end="2025-12-31",
        city=city_slug,
        diagnostic_run=diagnostic_run,
        stored_run=stored_run,
        baseline_run=7,
        protocol=protocol,
    ) as (run, output):
        result = dict(
            city=city_slug,
            main_cohort="fixed_panel" if city_slug == "bengaluru" else "all_stations",
            selected_design=config,
            cohorts={},
            recent_pm10=pm10_context(stored_run, city),
        )
        plot_data = {}
        # Materialise fold assignments before any new model fitting.
        (output / "outer_weeks.json").write_text(
            json.dumps(
                {cohort: week_partition(frame.observed_at) for cohort, frame in cohorts.items()},
                indent=2,
            )
        )
        for cohort, frame in cohorts.items():
            prefix = city_slug + ("_panel" if cohort == "fixed_panel" else "")
            raw, annual = annual_summary(frame)
            raw.to_csv(output / f"{prefix}_raw_daily.csv", index=False)
            plot_data[cohort] = {"raw": raw}
            gate = (
                selected["readiness"]
                if cohort == "all_stations"
                else selected["fixed_panel"].get("readiness")
            )
            if gate is None or not gate["passed"]:
                result["cohorts"][cohort] = dict(
                    scope="descriptive only",
                    readiness_run7=gate,
                    annual=annual,
                    reason="Cohort has not passed frozen readiness",
                )
                continue
            model_name = (
                "pooled"
                if config["periods"] == "pooled"
                else sorted(set(period_labels(frame.observed_at)))[0]
            )
            if not (baseline / f"{prefix}_{model_name}_forest.joblib").exists():
                result["cohorts"][cohort] = dict(
                    scope="descriptive only",
                    annual=annual,
                    reason="No validated Run 7 model for this panel",
                )
                continue
            print(
                json.dumps(dict(event="research_cohort_started", city=city_slug, cohort=cohort)),
                flush=True,
            )
            combined, metrics, choices = nested_validation(
                frame, weather, protocol, config, city_slug, cohort
            )
            combined.to_csv(output / f"{prefix}_nested_oof.csv", index=False)
            (output / f"{prefix}_nested_cv.json").write_text(
                json.dumps(dict(metrics=metrics, choices=choices), indent=2)
            )
            honest_gate = readiness(combined, protocol["unchanged_readiness"])
            dates, draws = bootstrap_normalisations(
                frame, weather, config, output, prefix, protocol["refits"], protocol["seed"]
            )
            norm = pd.read_csv(baseline / f"{prefix}_deweathered_daily.csv")
            norm["date"] = pd.to_datetime(norm.date).dt.date
            plot_data[cohort]["normalised"] = norm
            long_years = sorted(set(pd.to_datetime(raw.date).dt.year) & set(range(2015, 2020)))
            recent_years = sorted(set(pd.to_datetime(raw.date).dt.year) & {2024, 2025})
            long = (
                comparison_intervals(
                    raw,
                    norm,
                    dates,
                    draws,
                    combined,
                    long_years,
                    recent_years,
                    seed=protocol["seed"],
                )
                if long_years and recent_years
                else dict(status="unavailable", reason="One observed era is absent")
            )
            proxy = comparison_intervals(
                raw, norm, dates, draws, combined, [2017, 2018], seed=protocol["seed"]
            )
            norm.to_csv(output / f"{prefix}_deweathered_daily.csv", index=False)
            months = pd.read_csv(baseline / f"{prefix}_deweathered_monthly.csv")
            months["date"] = pd.to_datetime(months.date).dt.date
            trends = {
                period: trend_test(group)
                for period, group in months.assign(
                    period=np.where(pd.to_datetime(months.date).dt.year >= 2024, "recent", "old")
                ).groupby("period")
            }
            months.to_csv(output / f"{prefix}_deweathered_monthly.csv", index=False)
            explanations = explain_models(
                frame, weather, config, baseline, output, prefix, protocol["seed"]
            )
            result["cohorts"][cohort] = dict(
                scope="validated observed periods",
                readiness_run7=gate,
                nested_readiness=honest_gate,
                nested_validation=metrics,
                choices=choices,
                annual=annual,
                long_run_comparison=long,
                ncap_proxy=proxy,
                trends=trends,
                explanations=explanations,
                refits=protocol["refits"],
                artifacts_prefix=prefix,
            )
            (output / f"{prefix}_research.json").write_text(
                json.dumps(result["cohorts"][cohort], indent=2)
            )
            print(
                json.dumps(
                    dict(
                        event="research_cohort_finished",
                        city=city_slug,
                        cohort=cohort,
                        nested_r2=metrics["nested_full"]["overall"]["r2"],
                    )
                ),
                flush=True,
            )
        if "fixed_panel" not in result["cohorts"]:
            result["cohorts"]["fixed_panel"] = dict(
                scope="unavailable",
                reason=selected["fixed_panel"].get(
                    "reason", "No panel with eligible observed years"
                ),
            )
        comparison_plot(city, plot_data, output)
        (output / "research.json").write_text(json.dumps(result, indent=2))
        run.results = result
    gc.collect()
    return run.pk


def publish_research(child_ids, diagnostic_run, stored_run, protocol):
    children = list(
        AnalysisRun.objects.filter(id__in=child_ids, name="phase3b-city", status="success")
    )
    if {r.results["city"] for r in children} != set(protocol["eligible_cities"]):
        raise ValueError("Not all frozen eligible cities have completed research runs")
    source = AnalysisRun.objects.get(pk=stored_run, status="success")
    ncap = {r["city"]: r for r in source.results["ncap"]}
    path = Path("docs/results/PHASE3B_PROTOCOL.json")
    with analysis_run(
        name="phase3b",
        start="2015-01-01",
        end="2025-12-31",
        baseline_run=7,
        data_run=stored_run,
        diagnostic_run=diagnostic_run,
        child_runs=child_ids,
        protocol=protocol,
        protocol_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    ) as (run, output):
        results = {}
        for child in children:
            item = child.results
            city = City.objects.get(slug=item["city"])
            results[city.slug] = item
            for name, payload in [
                ("rq2", item),
                ("comparisons", item),
                (
                    "ncap",
                    dict(
                        label="PM2.5 proxy for NCAP progress",
                        is_official_compliance_result=False,
                        official_compliance_assessment="not assessed",
                        official_status=ncap[city.slug],
                        baseline=(
                            "Calendar 2017 and 2018; differs from official "
                            "fiscal-year 2017–18 PM10 baseline"
                        ),
                        cohorts={
                            key: dict(
                                scope=value["scope"],
                                comparison=value.get("ncap_proxy"),
                                trends=value.get("trends"),
                                annual=value.get("annual"),
                            )
                            for key, value in item["cohorts"].items()
                        },
                        recent_pm10=item["recent_pm10"],
                    ),
                ),
            ]:
                CityMetric.objects.create(run=run, city=city, name=name, result=payload)
        for city in City.objects.exclude(slug__in=protocol["eligible_cities"]):
            payload = dict(
                city=city.slug,
                scope="descriptive only",
                reason="Failed frozen Run 7 readiness",
                main_cohort=None,
                cohorts={},
            )
            CityMetric.objects.create(run=run, city=city, name="rq2", result=payload)
            results[city.slug] = payload
        (output / "phase3b_results.json").write_text(json.dumps(results, indent=2))
        run.results = dict(
            cities=results,
            child_runs=child_ids,
            report="docs/results/PHASE3B.md",
            ncap_label="PM2.5 proxy for NCAP progress",
            is_official_compliance_result=False,
        )
    return run.pk


def run_research(diagnostic_run, stored_run, cities=None, publish=True):
    protocol = json.loads(Path("docs/results/PHASE3B_PROTOCOL.json").read_text())
    selected = cities or protocol["eligible_cities"]
    children = []
    for city in selected:
        if city not in protocol["eligible_cities"]:
            raise ValueError("City outside frozen scope")
        previous = AnalysisRun.objects.filter(
            name="phase3b-city",
            status="success",
            parameters__diagnostic_run=diagnostic_run,
            parameters__stored_run=stored_run,
            parameters__city=city,
            parameters__protocol=protocol,
        ).first()
        children.append(
            previous.pk if previous else city_research(city, diagnostic_run, stored_run, protocol)
        )
    if publish and set(selected) == set(protocol["eligible_cities"]):
        return publish_research(children, diagnostic_run, stored_run, protocol)
    return children
