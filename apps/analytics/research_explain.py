"""Exact TreeSHAP daily aggregation, physical ALE, and a GAM shape comparison."""

import json

import joblib
import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from threadpoolctl import threadpool_limits

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .model_diagnostics import features, period_labels, target_rows
from .research_models import GAMRegressor, weather_dataset
from .research_stats import ale, grouped_shap, season_labels

CALENDAR = {
    "trend",
    "period",
    "doy_sin",
    "doy_cos",
    "hour_sin",
    "hour_cos",
    "weekday",
    "seasonal_calendar",
    "hour_calendar",
}


def explain_models(frame, weather, config, baseline, output, prefix, seed=20261009):
    import shap

    rows, x = features(target_rows(frame, weather, config["target"]), config)
    periods = period_labels(rows.observed_at)
    dates = rows.observed_at.dt.tz_convert("Asia/Kolkata").dt.date
    seasons = season_labels(pd.Series(dates))
    weather_rows, weather_x, _ = weather_dataset(frame, weather, config)
    wp = period_labels(weather_rows.observed_at)
    ws = season_labels(weather_rows.observed_at.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None))
    summaries, curves, agreements, additivity = [], [], [], []
    rng = np.random.default_rng(seed)
    for period in sorted(set(periods)):
        model_name = period if config["periods"] == "separate" else "pooled"
        model = joblib.load(baseline / f"{prefix}_{model_name}_forest.joblib")
        explainer = shap.TreeExplainer(model, feature_perturbation="tree_path_dependent")
        gmask = (wp == period) if config["periods"] == "separate" else np.ones(len(wp), dtype=bool)
        with threadpool_limits(limits=1):
            gam = GAMRegressor().fit(weather_x.loc[gmask], weather_rows.loc[gmask, "value"])
        joblib.dump(gam, output / f"{prefix}_{period}_weather_gam.joblib", compress=3)
        for season in ["winter", "pre_monsoon", "monsoon"]:
            mask = (periods == period) & (seasons == season)
            available = pd.Series(dates[mask]).value_counts()
            available = available[available >= (18 if config["target"] == "hourly" else 1)]
            chosen = rng.choice(sorted(available.index), min(30, len(available)), replace=False)
            positions = np.flatnonzero(mask & dates.isin(chosen).to_numpy())
            if not len(positions):
                continue
            values = explainer.shap_values(
                x.iloc[positions].to_numpy(), check_additivity=True, approximate=False
            )
            grouped = grouped_shap(values, x.columns)
            grouped["date"] = dates.iloc[positions].to_numpy()
            # Mean signed hourly attribution first; absolute value is taken only per day.
            daily = grouped.groupby("date").mean()
            daily.to_csv(output / f"{prefix}_{period}_{season}_daily_shap.csv")
            expected = float(np.asarray(explainer.expected_value).ravel()[0])
            discrepancy = np.max(
                np.abs(values.sum(axis=1) + expected - model.predict(x.iloc[positions].to_numpy()))
            )
            additivity.append(
                dict(
                    period=period,
                    season=season,
                    max_error=float(discrepancy),
                    sampled_days=len(daily),
                    sampled_rows=len(positions),
                )
            )
            for feature in daily.columns:
                summaries.append(
                    dict(
                        period=period,
                        season=season,
                        feature=feature,
                        weather=feature not in CALENDAR,
                        mean_abs_daily_shap=float(daily[feature].abs().mean()),
                        mean_signed_daily_shap=float(daily[feature].mean()),
                        sampled_days=len(daily),
                    )
                )
            subset = x.loc[mask]
            weather_columns = [
                c for c in x if c not in CALENDAR and c not in ["wind_sin", "wind_cos"]
            ]
            weather_columns.append("wind_direction")
            gsubset = weather_x.loc[(wp == period) & (ws == season)]
            fig, axes = plt.subplots(3, 3, figsize=(13, 10))
            for axis, feature in zip(axes.flat, weather_columns, strict=False):
                rf_curve = ale(model, subset, feature)
                rf_curve["method"] = "random_forest"
                gam_curve = ale(gam, gsubset, feature)
                gam_curve["method"] = "gam_weather_only"
                for curve in [rf_curve, gam_curve]:
                    curve["period"], curve["season"], curve["feature"] = period, season, feature
                    curves.extend(curve.to_dict("records"))
                    axis.plot(
                        curve.midpoint,
                        curve.ale,
                        label=curve.method.iloc[0] if len(curve) else "constant predictor",
                    )
                common = rf_curve.dropna(subset=["ale"])
                other = gam_curve.dropna(subset=["ale"])
                correlation = None
                if len(common) >= 3 and len(other) >= 3:
                    common = common[
                        common.midpoint.between(other.midpoint.min(), other.midpoint.max())
                    ]
                    if len(common) >= 3:
                        interpolated = np.interp(common.midpoint, other.midpoint, other.ale)
                        if common.ale.std() > 1e-8 and interpolated.std() > 1e-8:
                            correlation = float(spearmanr(common.ale, interpolated).statistic)
                agreements.append(
                    dict(
                        period=period,
                        season=season,
                        feature=feature,
                        ale_rank_correlation=correlation,
                    )
                )
                axis.set_title(feature)
                axis.set_ylabel("centred effect (ug/m3)")
                axis.axhline(0, color="grey", linewidth=0.5)
            for axis in list(axes.flat)[len(weather_columns) :]:
                axis.set_visible(False)
            axes.flat[0].legend(fontsize=8)
            fig.suptitle(f"{prefix}: {period}, {season}; associated model effects")
            fig.tight_layout()
            fig.savefig(output / f"{prefix}_{period}_{season}_ale.png", dpi=140)
            fig.savefig(output / f"{prefix}_{period}_{season}_ale.svg")
            plt.close(fig)
            print(f"Explanations {prefix}: {period}/{season}", flush=True)
    pd.DataFrame(summaries).to_csv(output / f"{prefix}_shap_summary.csv", index=False)
    pd.DataFrame(curves).to_csv(output / f"{prefix}_ale.csv", index=False)
    pd.DataFrame(agreements).to_csv(output / f"{prefix}_gam_agreement.csv", index=False)
    result = dict(
        shap=summaries,
        gam_ale_agreement=agreements,
        additivity=additivity,
        boundary_layer_height=(
            "retained"
            if config["blh"]
            else "Not retained by Run 7 selection; no validated BLH effect estimate"
        ),
        interpretation="Conditional model associations; exact path-dependent SHAP "
        "does not identify independent or causal weather effects",
        gam_comparison="Weather-only daily GAM versus validated forest; hourly forests "
        "and daily GAMs differ in target frequency",
    )
    (output / f"{prefix}_explanations.json").write_text(json.dumps(result, indent=2))
    return result
