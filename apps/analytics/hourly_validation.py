"""Supplement daily-target selections with their prespecified hourly counterpart."""

import json
import time
from pathlib import Path

from django.conf import settings
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits

from apps.warehouse.models import City

from .lifecycle import code_metadata
from .model_diagnostics import evaluate
from .models import AnalysisRun, CityCoverage
from .revised_deweather import eligible_frame, json_result


def supplement_hourly(run_id, watch=False):
    import pandas as pd

    run = AnalysisRun.objects.get(pk=run_id, name="phase3a2")
    output = Path(settings.BASE_DIR) / "data/results" / str(run_id)
    data = output.parent / str(run.parameters["data_run"])
    commit, metadata = code_metadata()
    results = []
    pending = list(City.objects.order_by("slug"))
    while pending:
        progress = False
        for city in list(pending):
            path = output / f"{city.slug}_revised_model.json"
            if not path.exists():
                continue
            try:
                selected = json.loads(path.read_text())
            except json.JSONDecodeError:
                # A watched producer may still be writing its result file.
                continue
            config = selected["selected_design"]
            if config["target"] == "hourly":
                result = dict(
                    city=city.slug,
                    config=config,
                    random=selected["random"],
                    weeks=selected["week_cv"],
                    transfer=selected["transfer"],
                    note="Selected hourly model; reuse actual completed evaluations",
                )
            else:
                name = config["name"].replace("daily_", "hourly_", 1)
                config = next(
                    v for v in run.parameters["protocol"]["variants"] if v["name"] == name
                )
                full = pd.read_pickle(data / f"{city.slug}_hourly.pkl")
                weather = pd.read_pickle(data / f"{city.slug}_weather.pkl")
                coverage = list(
                    CityCoverage.objects.filter(run_id=run_id, city=city).values("year", "eligible")
                )
                frame = eligible_frame(full, coverage)
                with threadpool_limits(limits=1):
                    random, transfer = Parallel(n_jobs=2, prefer="threads")(
                        delayed(evaluate)(frame, weather, config, scheme=scheme)
                        for scheme in ["random", "transfer"]
                    )
                weeks = json.loads((output / f"{city.slug}_{name}_cv.json").read_text())
                result = dict(
                    city=city.slug,
                    config=config,
                    random=json_result(random),
                    weeks=weeks,
                    transfer=json_result(transfer),
                    note="Hourly counterpart from frozen eight-variant list; descriptive only",
                )
            (output / f"{city.slug}_hourly_validation.json").write_text(
                json.dumps(result, indent=2)
            )
            results.append(result)
            pending.remove(city)
            progress = True
            print(
                json.dumps(
                    dict(
                        event="hourly_validation_finished",
                        city=city.slug,
                        random_r2=result["random"]["native"]["r2"],
                        week_r2=result["weeks"]["native"]["r2"],
                    )
                ),
                flush=True,
            )
        if pending and not progress:
            run.refresh_from_db()
            if run.status == "failed" or not watch or run.status == "success":
                raise RuntimeError(f"Incomplete city results for run {run_id}: {run.status}")
            time.sleep(5)
    payload = dict(
        run=run_id,
        supplement_revision=dict(git_commit=commit, **metadata),
        note="No model selection, readiness thresholds or final normalisation changed",
        cities=sorted(results, key=lambda r: r["city"]),
    )
    (output / "D4_corrected_hourly_validation.json").write_text(json.dumps(payload, indent=2))
    return payload
