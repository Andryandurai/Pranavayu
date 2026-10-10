"""Monthly expanding-window experiments and auditable replay predictions."""

import hashlib
import json
import shutil

import joblib
import numpy as np
import pandas as pd
from django.conf import settings

from apps.analytics.descriptive import season
from apps.analytics.lifecycle import analysis_run
from apps.ingest.models import IngestionRun
from apps.warehouse.models import City

from .data import city_dataset, feature_provenance, rolling_origins, training_segments, write_json
from .estimators import SEED, choose_models, predict
from .explain import top_drivers
from .metrics import aqi_category, conformal_radius, dm_test, scores
from .models import Forecast, ForecastEvaluation, ForecastModelVersion, ForecastWeather
from .tracking import log_experiment, register_model, tracking_client


def interval_predictions(models, quantiles, calibration, rows, history, chosen):
    point = predict(models[chosen], rows, history)
    residual = calibration.y.to_numpy() - predict(models[chosen], calibration, history)
    q80 = conformal_radius(residual, 0.2)
    q95 = conformal_radius(residual, 0.05)
    result = {
        "prediction": point,
        "lower80": np.maximum(0, point - q80),
        "upper80": point + q80,
        "lower95": np.maximum(0, point - q95),
        "upper95": point + q95,
    }
    for lower, upper, alpha in [(0.1, 0.9, 0.2), (0.025, 0.975, 0.05)]:
        cl = predict(quantiles[str(lower)], calibration, history)
        cu = predict(quantiles[str(upper)], calibration, history)
        errors = np.maximum(
            np.minimum(cl, cu) - calibration.y.to_numpy(),
            calibration.y.to_numpy() - np.maximum(cl, cu),
        )
        rank = int(np.ceil((len(errors) + 1) * (1 - alpha)))
        adjustment = max(0, float(np.sort(errors)[rank - 1]))
        lo = predict(quantiles[str(lower)], rows, history)
        hi = predict(quantiles[str(upper)], rows, history)
        label = "80" if alpha == 0.2 else "95"
        result[f"quantile_lower{label}"] = np.maximum(0, np.minimum(lo, hi) - adjustment)
        result[f"quantile_upper{label}"] = np.maximum(lo, hi) + adjustment
    result["quantile_lower95"] = np.minimum(result["quantile_lower95"], result["quantile_lower80"])
    result["quantile_upper95"] = np.maximum(result["quantile_upper95"], result["quantile_upper80"])
    return result, {"radius80": q80, "radius95": q95, "calibration_n": len(residual)}


def save_forecasts(city, horizon, version, frame, drivers, mode="replay"):
    objects = []
    for (_, row), explanation in zip(frame.iterrows(), drivers, strict=True):
        objects.append(
            Forecast(
                city=city,
                issued_for_date=row.issued_for_date.date(),
                target_date=row.target_date.date(),
                horizon=horizon,
                point=float(row.prediction),
                lower80=float(row.lower80),
                upper80=float(row.upper80),
                lower95=float(row.lower95),
                upper95=float(row.upper95),
                aqi_category=aqi_category(row.prediction),
                mode=mode,
                model_version=version,
                top_drivers=explanation,
                feature_provenance=feature_provenance(row, horizon),
            )
        )
    Forecast.objects.bulk_create(objects, ignore_conflicts=True)


def train_forecasters(cities=None):
    protocol = settings.BASE_DIR / "docs" / "results" / "PHASE4_PROTOCOL.md"
    digest = hashlib.sha256(protocol.read_bytes()).hexdigest()
    client, experiment = tracking_client()
    with analysis_run(
        "phase4",
        start="2024-01-01",
        end="2025-12-31",
        seed=SEED,
        protocol_sha256=digest,
        baseline=19,
        diagnostic_data_run=8,
    ) as (run, output):
        shutil.copy2(protocol, output / "protocol.md")
        evidence = settings.BASE_DIR / ".tools" / "phase4-validation"
        for path in evidence.glob("*.json"):
            shutil.copy2(path, output / path.name)
        for path in evidence.glob("*bias.csv"):
            shutil.copy2(path, output / path.name)
        if (evidence / "bias").exists():
            shutil.copytree(evidence / "bias", output / "prior_bias", dirs_exist_ok=True)
        all_results = []
        splits = []
        provenance = []
        for slug in cities or settings.FORECAST_CITIES:
            city = City.objects.get(slug=slug)
            for horizon in (1, 2, 3):
                daily, real, ideal, data_provenance = city_dataset(slug, horizon)
                latest = daily[daily.value.notna()].index.max()
                provenance.append(
                    {
                        "city": slug,
                        "horizon": horizon,
                        "raw_valid_days": int(daily.value.notna().sum()),
                        "feature_rows": len(real),
                        "latest_target": str(latest.date()),
                        **data_provenance,
                    }
                )
                for kind, rows in [("archived_forecast", real), ("perfect_prognosis", ideal)]:
                    for month, origin, train, test in rolling_origins(rows, latest):
                        print(
                            json.dumps(
                                {
                                    "event": "forecast_origin",
                                    "run": run.pk,
                                    "city": slug,
                                    "horizon": horizon,
                                    "weather": kind,
                                    "month": month,
                                    "train": len(train),
                                    "test": len(test),
                                }
                            ),
                            flush=True,
                        )
                        fit, tune, final_fit, calibration = training_segments(train, origin)
                        models, quantiles, selection = choose_models(
                            fit, tune, final_fit, rows, horizon
                        )
                        predictions = test.copy()
                        for name, model in models.items():
                            predictions[name] = predict(model, test, rows)
                        interval, calibration_info = interval_predictions(
                            models, quantiles, calibration, test, rows, selection["chosen"]
                        )
                        for key, values in interval.items():
                            predictions[key] = values
                        predictions["city"] = slug
                        predictions["horizon"] = horizon
                        predictions["weather"] = kind
                        predictions["origin_month"] = month
                        predictions["algorithm"] = selection["chosen"]
                        predictions["keep_lstm"] = selection["keep_lstm"]
                        prefix = f"{slug}_h{horizon}_{kind}_{month}"
                        predictions.to_csv(output / f"{prefix}_predictions.csv", index=False)
                        metadata = {
                            "city": slug,
                            "horizon": horizon,
                            "weather": kind,
                            "origin": str(origin.date()),
                            "fit_start": str(fit.index.min().date()),
                            "fit_label_end": str(fit.target_date.max().date()),
                            "tuning_first_issue": str(tune.index.min().date()),
                            "tuning_last_target": str(tune.target_date.max().date()),
                            "final_fit_last_target": str(final_fit.target_date.max().date()),
                            "calibration_first_issue": str(calibration.index.min().date()),
                            "calibration_last_target": str(calibration.target_date.max().date()),
                            "test_first_issue": str(test.index.min().date()),
                            "test_last_target": str(test.target_date.max().date()),
                            "fit_n": len(fit),
                            "tune_n": len(tune),
                            "final_fit_n": len(final_fit),
                            **selection,
                            **calibration_info,
                        }
                        write_json(output / f"{prefix}_selection.json", metadata)
                        mlflow_runs = {}
                        for algorithm in models:
                            metrics = scores(predictions, algorithm)
                            mlflow_runs[algorithm] = log_experiment(
                                client,
                                experiment,
                                {
                                    "analysis_run": run.pk,
                                    "city": slug,
                                    "horizon": horizon,
                                    "weather": kind,
                                    "month": month,
                                    "algorithm": algorithm,
                                    "selected": algorithm == selection["chosen"],
                                },
                                {
                                    "seed": SEED,
                                    "protocol_sha256": digest,
                                    "tuning_rmse": selection["tuning_rmse"][algorithm],
                                    "fit_target_end": str(final_fit.target_date.max().date()),
                                    "selection_settings": selection["settings"].get(algorithm, {}),
                                },
                                metrics,
                                output / f"{prefix}_selection.json",
                            )
                        for alpha, model in quantiles.items():
                            residual = predictions.y.to_numpy() - predict(model, test, rows)
                            a = float(alpha)
                            pinball = float(np.maximum(a * residual, (a - 1) * residual).mean())
                            log_experiment(
                                client,
                                experiment,
                                {
                                    "analysis_run": run.pk,
                                    "city": slug,
                                    "horizon": horizon,
                                    "weather": kind,
                                    "month": month,
                                    "algorithm": "lightgbm_quantile",
                                },
                                {
                                    "alpha": alpha,
                                    "seed": SEED,
                                    "structure": selection["settings"]["lightgbm"],
                                },
                                {"pinball_loss": pinball},
                            )
                        if kind == "archived_forecast":
                            chosen = models[selection["chosen"]]
                            registry, registry_version, uri = register_model(
                                chosen, slug, horizon, mlflow_runs[selection["chosen"]]
                            )
                            bundle = {
                                "model": chosen,
                                "quantiles": quantiles,
                                "calibration": calibration,
                                "background": final_fit.iloc[
                                    np.linspace(
                                        0, len(final_fit) - 1, min(30, len(final_fit))
                                    ).astype(int)
                                ],
                                "chosen": selection["chosen"],
                                "selection": metadata,
                                "horizon": horizon,
                                "city": slug,
                            }
                            path = output / f"{prefix}_model.joblib"
                            joblib.dump(bundle, path)
                            client.log_artifact(
                                mlflow_runs[selection["chosen"]], str(path), "django_bundle"
                            )
                            version = ForecastModelVersion.objects.create(
                                city=city,
                                horizon=horizon,
                                algorithm=selection["chosen"],
                                mlflow_run_id=mlflow_runs[selection["chosen"]],
                                registry_name=registry,
                                registry_version=registry_version,
                                training_start=final_fit.target_date.min().date(),
                                training_end=final_fit.target_date.max().date(),
                                available_from=origin.date(),
                                validation_metrics={"selection": metadata, "mlflow_model_uri": uri},
                                artifact_path=str(path.relative_to(settings.BASE_DIR)),
                                analysis_run=run,
                                cohort=data_provenance["cohort"],
                            )
                            drivers = top_drivers(chosen, test, bundle["background"], rows)
                            save_forecasts(city, horizon, version, predictions, drivers)
                            write_json(output / f"{prefix}_explanations.json", drivers)
                        splits.append(metadata)
                        all_results.append(predictions)
        pd.concat(all_results, ignore_index=True).to_csv(output / "predictions.csv", index=False)
        write_json(output / "split_audit.json", splits)
        write_json(output / "input_provenance.json", provenance)
        # Score only after every prespecified forecast has been produced.
        result = evaluate_run(run, output)
        write_json(output / "phase4_results.json", result)
    return run


def evaluate_run(run, output):
    predictions = pd.read_csv(
        output / "predictions.csv", parse_dates=["issued_for_date", "target_date"]
    )
    evaluations = []
    errors = []
    for (city, horizon, weather), group in predictions.groupby(["city", "horizon", "weather"]):
        algorithms = [
            name
            for name in (
                "persistence",
                "mean7",
                "climatology",
                "sarimax",
                "lightgbm",
                "lstm",
                "prediction",
            )
            if name in group and group[name].notna().all()
        ]
        comparison = {}
        for algorithm in algorithms:
            score = scores(group, algorithm)
            score["dm"] = dm_test(
                group.target_date,
                group.y.to_numpy(),
                group[algorithm].to_numpy(),
                group.persistence.to_numpy(),
                int(horizon),
            )
            comparison[algorithm] = score
        intervals = {}
        for prefix in ("", "quantile_"):
            for coverage in (80, 95):
                lo = group[f"{prefix}lower{coverage}"]
                hi = group[f"{prefix}upper{coverage}"]
                intervals[f"{prefix}{coverage}"] = {
                    "coverage": float(((group.y >= lo) & (group.y <= hi)).mean()),
                    "mean_width": float((hi - lo).mean()),
                    "n": len(group),
                }
        result = {
            "city": city,
            "horizon": int(horizon),
            "weather": weather,
            "models": comparison,
            "intervals": intervals,
            "issued_algorithms": group.algorithm.value_counts().to_dict(),
            "lstm_kept_origins": int(group[group.keep_lstm].origin_month.nunique()),
            "target_start": str(group.target_date.min().date()),
            "target_end": str(group.target_date.max().date()),
        }
        evaluations.append(result)
        group = group.copy()
        group["month"] = group.target_date.dt.strftime("%Y-%m")
        group["season"] = group.target_date.dt.month.map(season)
        for period in ("month", "season"):
            for label, part in group.groupby(period):
                errors.append(
                    {
                        "city": city,
                        "horizon": int(horizon),
                        "weather": weather,
                        "period": period,
                        "label": label,
                        **scores(part),
                    }
                )
    pd.DataFrame(errors).to_csv(output / "seasonal_errors.csv", index=False)
    coverage = []
    for city in settings.FORECAST_CITIES:
        for horizon in (1, 2, 3):
            rows = ForecastWeather.objects.filter(city__slug=city, horizon=horizon, mode="archive")
            dates = list(rows.values_list("target_date", flat=True))
            recent = [d for d in dates if d.year in (2024, 2025)]
            evaluation = [d for d in recent if d >= pd.Timestamp("2025-07-01").date()]
            coverage.append(
                {
                    "city": city,
                    "horizon": horizon,
                    "days_2024_2025": len(recent),
                    "first": str(min(recent)) if recent else None,
                    "last": str(max(recent)) if recent else None,
                    "evaluation_days": len(evaluation),
                    "expected_evaluation_days": 184,
                    "blh_non_null_days": sum(
                        r["boundary_layer_height_m"] is not None
                        for r in rows.values_list("features", flat=True)
                    ),
                }
            )
    result = {
        "run": run.pk,
        "protocol_sha256": run.parameters["protocol_sha256"],
        "evaluations": evaluations,
        "weather_coverage": coverage,
        "excluded_cities": ["ahmedabad", "jaipur", "kanpur", "lucknow", "patna"],
        "cams": {
            "status": "skipped",
            "reason": (
                "Actual CAMS Global archived lead-2/3/4 queries across the seven cities "
                "returned null evaluation-period forecasts. Historical valid-time PM2.5 "
                "exists, but it cannot replace issued forecasts in a benchmark."
            ),
        },
    }
    cams_run = IngestionRun.objects.filter(source__slug="cams-forecast").order_by("-pk").first()
    if cams_run:
        result["cams"]["ingestion_run"] = cams_run.pk
        result["cams"]["coverage"] = cams_run.params.get("coverage", [])
        if any(r["non_null_hours"] for r in result["cams"]["coverage"]):
            raise ValueError(
                "CAMS vintage coverage exists: evaluate it before publishing; do not skip"
            )
    for entry in evaluations:
        if entry["weather"] == "archived_forecast":
            ideal = next(
                e
                for e in evaluations
                if e["city"] == entry["city"]
                and e["horizon"] == entry["horizon"]
                and e["weather"] == "perfect_prognosis"
            )
            entry["perfect_prognosis_gap_rmse"] = (
                entry["models"]["prediction"]["rmse"] - ideal["models"]["prediction"]["rmse"]
            )
            ForecastEvaluation.objects.update_or_create(
                analysis_run=run,
                city=City.objects.get(slug=entry["city"]),
                horizon=entry["horizon"],
                defaults={"result": {**entry, "perfect_prognosis": ideal, "cams": result["cams"]}},
            )
    write_json(output / "phase4_results.json", result)
    return result
