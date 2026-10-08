import json
import shutil

from .aggregation import build_tables
from .audit import reflag
from .descriptive import describe
from .deweather import run_deweather
from .lifecycle import analysis_run
from .models import AnalysisRun
from .population import register_population
from .reporting import figures, write_report


def retain_initial_audit(run, output, audit):
    """Keep the measured pre-correction baseline alongside an idempotent replay."""
    audit["initial_correction"] = {
        "run": run.pk,
        **{key: audit[key] for key in ["before", "changed_rows", "version"]},
    }
    for previous in AnalysisRun.objects.filter(
        name="phase3a", status="success", id__lt=run.pk
    ).order_by("id"):
        folder = output.parent / str(previous.pk)
        path = folder / "flag_audit.json"
        if not path.exists():
            continue
        prior = json.loads(path.read_text(encoding="utf-8"))
        if (
            prior.get("version") != audit["version"]
            or prior.get("fingerprint_after") != audit["fingerprint_before"]
        ):
            continue
        audit["initial_correction"] = prior.get(
            "initial_correction",
            {
                "run": previous.pk,
                **{key: prior[key] for key in ["before", "changed_rows", "version"]},
            },
        )
        for name in ["raw_flag_examples.json", "precision_audit.json"]:
            if (folder / name).exists():
                shutil.copyfile(folder / name, output / name)
        break
    (output / "flag_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")


def run_phase3a(start="2015-01-01", end="2026-10-07", seed=42, n_samples=300, n_trees=100):
    if n_samples < 300:
        raise ValueError("At least 300 normalisation samples are required")
    with analysis_run(
        start=start,
        end=end,
        seed=seed,
        n_samples=n_samples,
        n_trees=n_trees,
        eligibility="75% valid calendar hours and days; daily18/monthly75%",
        model_validation="chronological80/20 with seven-day purge",
        readiness_screen={
            "r2_min": 0.5,
            "relative_rmse_max": 0.5,
            "absolute_relative_bias_max": 0.1,
            "train_min": 2000,
            "test_min": 1000,
        },
    ) as (run, output):
        audit = reflag(run, output)
        retain_initial_audit(run, output, audit)
        population = register_population()
        tables = build_tables(run, output)
        descriptive = describe(run, output, seed)
        performance = run_deweather(run, output, n_trees, n_samples, seed)
        figures(run, output, descriptive, audit)
        report = write_report(run, output, audit, tables, descriptive, performance, population)
        run.results = {
            "flag_changes": audit["changed_rows"],
            "city_hourly_rows": tables["hourly_rows"],
            "pm25_eligible_city_years": sum(
                r["eligible"] for r in tables["coverage"] if r["pollutant"] == "pm25"
            ),
            "models": performance,
            "report": report,
            "population": population,
        }
    return run.pk
