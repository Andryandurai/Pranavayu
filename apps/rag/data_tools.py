"""Eight validated read-only data tools; all results carry their actual provenance."""

import hashlib
import json
import math

from django.conf import settings
from django.db.models import Avg, Count, Max
from rest_framework import serializers

from apps.analytics.models import AnalysisRun, CityCoverage, CityMetric, CitySeries
from apps.forecast.api import ForecastSerializer, completed_run
from apps.forecast.models import Forecast, ForecastEvaluation
from apps.warehouse.models import City


class StrictParameters(serializers.Serializer):
    city = serializers.CharField(max_length=100)

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"parameters": "Use a parameter object"})
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {"parameters": f"Unknown fields: {', '.join(sorted(unknown))}"}
            )
        if any(
            isinstance(data.get(name), bool) for name in ("year", "horizon", "threshold", "run_id")
        ):
            raise serializers.ValidationError(
                {"parameters": "Numeric parameters cannot be booleans"}
            )
        return super().to_internal_value(data)

    def validate_city(self, value):
        value = value.strip().casefold().replace(" ", "-")
        value = {"new-delhi": "delhi", "bangalore": "bengaluru", "calcutta": "kolkata"}.get(
            value, value
        )
        city = City.objects.filter(slug=value).first()
        if city is None:
            raise serializers.ValidationError("Unknown seeded city")
        return city.slug


class AnnualParameters(StrictParameters):
    year = serializers.IntegerField(min_value=1900, max_value=2100)


class SeriesParameters(StrictParameters):
    start = serializers.DateField()
    end = serializers.DateField()
    kind = serializers.ChoiceField(choices=["raw", "deweathered"], default="raw")

    def validate(self, attrs):
        if not 0 < (attrs["end"] - attrs["start"]).days <= 366 * 15:
            raise serializers.ValidationError(
                "Use an ordered interval up to 15 years; end is exclusive"
            )
        return attrs


class ExceedanceParameters(AnnualParameters):
    threshold = serializers.FloatField(min_value=0, max_value=1000)

    def validate_threshold(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Threshold must be finite µg/m³")
        return value


class DriverParameters(StrictParameters):
    season = serializers.ChoiceField(choices=["winter", "pre_monsoon", "monsoon"])


class SkillParameters(StrictParameters):
    horizon = serializers.IntegerField(min_value=1, max_value=3)


def fixed_run(setting, default):
    return AnalysisRun.objects.get(pk=getattr(settings, setting, default), status="success")


def raw_run():
    return fixed_run("RAG_DATA_RUN", 9)


def normalised_run():
    return fixed_run("RAG_NORMALISATION_RUN", 7)


def research_run():
    return fixed_run("RAG_RESEARCH_RUN", 19)


def evidence(tool, parameters, run, values, url, **extra):
    city = City.objects.get(slug=parameters["city"])
    pieces = ["dataset: " + tool, city.name]
    pieces += [f"{name}={value}" for name, value in parameters.items() if name != "city"]
    pieces += [f"run {run.pk}"]
    parameter_hash = hashlib.sha256(
        json.dumps(parameters, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    reference = {
        "id": f"dataset:{tool}:{city.slug}:{run.pk}:{parameter_hash}",
        "kind": "dataset",
        "label": ", ".join(pieces),
        "analysis_run": run.pk,
        "query_parameters": parameters,
        "url": url,
        **extra,
    }
    return {"tool": tool, "parameters": parameters, "values": values, "citation": reference}


def daily_rows(run, city, year):
    return CitySeries.objects.filter(
        run=run,
        city__slug=city,
        pollutant__code="pm25",
        kind="raw",
        frequency="daily",
        date__year=year,
    )


def annual(parameters):
    run = raw_run()
    year, city = parameters["year"], parameters["city"]
    coverage = CityCoverage.objects.filter(
        run=run, city__slug=city, pollutant__code="pm25", year=year
    ).first()
    summary = daily_rows(run, city, year).aggregate(
        mean=Avg("value"), valid_days=Count("value"), maximum=Max("value")
    )
    eligible = bool(coverage and coverage.eligible)
    values = {
        "annual_mean": summary["mean"] if eligible else None,
        "partial_observed_mean": summary["mean"] if not eligible else None,
        "valid_days": summary["valid_days"],
        "annual_eligible": eligible,
        "units": "µg/m³",
        "cohort": "all_stations",
        "aggregation": "mean of valid equal-station IST daily means; days require 18 hours",
        "status": "available" if eligible else "insufficient_annual_coverage",
    }
    return evidence(
        "city_annual_mean",
        parameters,
        run,
        values,
        f"/api/analytics/city/{city}/series/?run={run.pk}&kind=raw&freq=daily"
        f"&start={year}-01-01&end={year + 1}-01-01",
    )


def monthly(parameters):
    run = raw_run() if parameters["kind"] == "raw" else normalised_run()
    city = parameters["city"]
    rows = list(
        CitySeries.objects.filter(
            run=run,
            city__slug=city,
            pollutant__code="pm25",
            kind=parameters["kind"],
            frequency="monthly",
            date__gte=parameters["start"],
            date__lt=parameters["end"],
        )
        .order_by("date")
        .values("date", "value", "valid_count", "expected_count")
    )
    for row in rows:
        row["date"] = row["date"].isoformat()
    values = {
        "series": rows,
        "kind": parameters["kind"],
        "units": "µg/m³",
        "date_semantics": "start inclusive, end exclusive; missing values remain null",
        "cohort": "stored CitySeries default (all stations)",
        "status": "available" if any(row["value"] is not None for row in rows) else "unavailable",
    }
    if parameters["kind"] == "deweathered":
        values["limitation"] = (
            "Run 7 normalisation; consult Phase 3B nested gates. Bengaluru's stored "
            "all-station series is not the approved fixed-panel cohort."
        )
    return evidence(
        "city_monthly_series",
        parameters,
        run,
        values,
        f"/api/analytics/city/{city}/series/?run={run.pk}&kind={parameters['kind']}&freq=monthly"
        f"&start={parameters['start']}&end={parameters['end']}",
    )


def exceedance(parameters):
    run = raw_run()
    rows = daily_rows(run, parameters["city"], parameters["year"])
    valid = rows.filter(value__isnull=False).count()
    count = rows.filter(value__gt=parameters["threshold"]).count() if valid else None
    values = {
        "days_above_threshold": count,
        "threshold": parameters["threshold"],
        "valid_days": valid,
        "units": "µg/m³",
        "comparison": "strictly greater than",
        "cohort": "all_stations",
        "scope": "city daily means, not station maxima",
        "status": "available" if valid else "unavailable",
    }
    return evidence(
        "exceedance_days",
        parameters,
        run,
        values,
        f"/api/analytics/city/{parameters['city']}/series/?run={run.pk}&kind=raw&freq=daily"
        f"&start={parameters['year']}-01-01&end={parameters['year'] + 1}-01-01",
    )


def rq2_metric(run, city):
    return CityMetric.objects.filter(run=run, city__slug=city, name="rq2").first()


def ncap(parameters):
    run = research_run()
    metric = CityMetric.objects.filter(run=run, city__slug=parameters["city"], name="ncap").first()
    rq2 = rq2_metric(run, parameters["city"])
    main = rq2.result["main_cohort"] if rq2 else "all_stations"
    selected = metric.result.get("cohorts", {}).get(main, {}) if metric else {}
    values = {
        "label": "PM2.5 proxy for NCAP progress",
        "cohort": main,
        "is_official_compliance_result": False,
        "official_compliance_assessment": "not assessed; historic PM10 baseline absent",
        "comparison": selected.get("comparison", {"status": "unavailable"}),
        "nested_readiness": rq2.result.get("cohorts", {}).get(main, {}).get("nested_readiness")
        if rq2
        else None,
        "status": "available"
        if selected.get("comparison", {}).get("status") != "unavailable" and selected
        else "unavailable",
    }
    if rq2:
        values["network_matched_long_run_comparisons"] = rq2.result.get(
            "network_matched_comparisons"
        )
    return evidence(
        "ncap_proxy_comparison", parameters, run, values, f"/api/analytics/ncap/?run={run.pk}"
    )


def drivers(parameters):
    run = research_run()
    metric = rq2_metric(run, parameters["city"])
    main = metric.result["main_cohort"] if metric else "all_stations"
    selected = metric.result.get("cohorts", {}).get(main, {}) if metric else {}
    rows = [
        row
        for row in selected.get("explanations", {}).get("shap", [])
        if row["season"] == parameters["season"] and row.get("weather")
    ]
    ranks = []
    for period in sorted(set(row["period"] for row in rows)):
        ranks += sorted(
            [row for row in rows if row["period"] == period],
            key=lambda row: -row["mean_abs_daily_shap"],
        )[:5]
    values = {
        "drivers": ranks,
        "units": "µg/m³ (mean absolute daily SHAP)",
        "cohort": main,
        "nested_readiness": selected.get("nested_readiness"),
        "interpretation": (
            "conditional model attribution; not causal effects or a variance partition"
        ),
        "season_definition": (
            "winter October–February; pre-monsoon March–May; monsoon June–September"
        ),
        "status": "available" if ranks else "unavailable",
    }
    return evidence(
        "rq2_drivers",
        parameters,
        run,
        values,
        f"/api/analytics/rq2/{parameters['city']}/?run={run.pk}",
    )


def latest(parameters):
    run = completed_run()
    rows = Forecast.objects.filter(
        city__slug=parameters["city"], model_version__analysis_run=run
    ).select_related("model_version")
    last = rows.order_by("-issued_for_date").first()
    rows = (
        rows.filter(issued_for_date=last.issued_for_date).order_by("horizon")
        if last
        else rows.none()
    )
    forecasts = list(ForecastSerializer(rows, many=True).data)
    values = {
        "forecasts": forecasts,
        "units": "µg/m³",
        "timezone": "Asia/Kolkata",
        "category_scope": "PM2.5 subindex category, not overall AQI",
        "status": "available" if forecasts else "unavailable",
        "interpretation": "Replay is archival and is not a current live forecast",
    }
    return evidence(
        "latest_forecast",
        parameters,
        run,
        values,
        f"/api/forecast/{parameters['city']}/latest/",
        model_versions=[row["model_version"] for row in forecasts],
    )


def skill(parameters):
    run = completed_run()
    row = ForecastEvaluation.objects.filter(
        analysis_run=run, city__slug=parameters["city"], horizon=parameters["horizon"]
    ).first()
    if row:
        values = {
            "policy": row.result["models"]["prediction"],
            "intervals": row.result["intervals"],
            "issued_algorithms": row.result["issued_algorithms"],
            "target_start": row.result["target_start"],
            "target_end": row.result["target_end"],
            "weather": "archived_forecast",
            "units": "µg/m³",
            "status": "available",
            "limitations": (
                "Retrospective monthly-selected policy; live skill unverified. Negative "
                "skill loses to persistence; empirical interval coverage is not a guarantee."
            ),
        }
    else:
        values = {"status": "unavailable", "reason": "No completed city/horizon evaluation"}
    return evidence(
        "forecast_skill", parameters, run, values, f"/api/forecast/{parameters['city']}/evaluation/"
    )


def coverage(parameters):
    run = raw_run()
    rows = list(
        CityCoverage.objects.filter(run=run, city__slug=parameters["city"], pollutant__code="pm25")
        .order_by("year")
        .values(
            "year",
            "hours_present",
            "hours_expected",
            "valid_days",
            "expected_days",
            "valid_months",
            "eligible",
        )
    )
    return evidence(
        "data_coverage",
        parameters,
        run,
        {
            "coverage": rows,
            "status": "available" if rows else "unavailable",
            "scope": (
                "quality-OK city PM2.5 coverage; presence does not establish instrument calibration"
            ),
        },
        f"/api/analytics/coverage/?run={run.pk}&city={parameters['city']}&pollutant=pm25",
    )


class VayusimParameters(serializers.Serializer):
    run_id = serializers.IntegerField(min_value=1)

    def to_internal_value(self, data):
        if (
            not isinstance(data, dict)
            or set(data) != {"run_id"}
            or isinstance(data.get("run_id"), bool)
        ):
            raise serializers.ValidationError({"parameters": "Use only a positive integer run_id"})
        return super().to_internal_value(data)


def vayusim_run(parameters):
    from django.shortcuts import get_object_or_404

    from apps.vayusim.models import ScenarioRun

    run = get_object_or_404(
        ScenarioRun.objects.select_related("scenario__city"), pk=parameters["run_id"]
    )
    summary = run.summary
    values = {
        "status": "available",
        "label": summary["label"],
        "unit": summary["unit"],
        "peak_ugm3": summary["peak_ugm3"],
        "peak_location": summary["peak_location"],
        "distance_to_peak_m": summary["distance_to_peak_m"],
        "area_above_km2": summary["area_above_km2"],
        "exposure": summary["exposure"],
        "stability_class": run.stability_class,
        "weather_provenance": summary["weather_provenance"],
        "population_provenance": summary["population_provenance"],
        "flags": run.flags,
        "limitations": summary["limitations"],
        "source_assumptions": summary["source_assumptions"],
        "inputs_hash": run.inputs_hash,
        "engine_version": run.engine_version,
    }
    citation = {
        "id": f"dataset:vayusim_run:{run.pk}:{run.inputs_hash[:12]}",
        "kind": "dataset",
        "label": (
            f"VayuSim run {run.pk}, {run.scenario.city.name}, {run.scenario.date_hour.isoformat()}"
        ),
        "scenario_run": run.pk,
        "inputs_hash": run.inputs_hash,
        "engine_version": run.engine_version,
        "query_parameters": parameters,
        "url": f"/api/vayusim/runs/{run.pk}/",
    }
    return {
        "tool": "vayusim_run",
        "parameters": {"city": run.scenario.city.slug, **parameters},
        "values": values,
        "citation": citation,
    }


TOOLS = {
    "vayusim_run": (VayusimParameters, vayusim_run),
    "city_annual_mean": (AnnualParameters, annual),
    "city_monthly_series": (SeriesParameters, monthly),
    "exceedance_days": (ExceedanceParameters, exceedance),
    "ncap_proxy_comparison": (StrictParameters, ncap),
    "rq2_drivers": (DriverParameters, drivers),
    "latest_forecast": (StrictParameters, latest),
    "forecast_skill": (SkillParameters, skill),
    "data_coverage": (StrictParameters, coverage),
}


def call_tool(name, parameters):
    if name not in TOOLS:
        raise serializers.ValidationError("Tool is not whitelisted")
    serializer, handler = TOOLS[name]
    parsed = serializer(data=parameters)
    parsed.is_valid(raise_exception=True)
    result = handler(parsed.validated_data)
    # JSON dates are represented explicitly rather than provider-dependent encodings.
    result["parameters"] = {
        key: value.isoformat() if hasattr(value, "isoformat") else value
        for key, value in result["parameters"].items()
    }
    result["citation"]["query_parameters"] = result["parameters"]
    return result
