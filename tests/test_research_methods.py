import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor

from apps.analytics.model_diagnostics import week_labels
from apps.analytics.research_models import split_positions, week_partition
from apps.analytics.research_stats import ale, grouped_shap, trend_test
from apps.analytics.research_uncertainty import bootstrap_normalisations, comparison_intervals


def test_ale_linear_effect_and_daily_signed_shap_aggregation():
    class Linear:
        def predict(self, x):
            return 3 * np.asarray(x)[:, 0]

    x = pd.DataFrame({"temperature_c": np.linspace(-5, 5, 120)})
    curve = ale(Linear(), x, "temperature_c")
    expected = 3 * curve.midpoint
    expected -= np.average(expected, weights=curve.n)
    np.testing.assert_allclose(curve.ale, expected, atol=1e-12)
    import shap

    array = np.column_stack([np.linspace(-1, 1, 80), np.sin(np.arange(80)), np.cos(np.arange(80))])
    model = RandomForestRegressor(n_estimators=5, max_depth=3, random_state=10).fit(
        array, array[:, 0] * 3
    )
    explainer = shap.TreeExplainer(model, feature_perturbation="tree_path_dependent")
    values = explainer.shap_values(array[:4], approximate=False, check_additivity=True)
    grouped = grouped_shap(values, ["temperature_c", "wind_sin", "wind_cos"])
    np.testing.assert_allclose(
        grouped.sum(axis=1) + float(explainer.expected_value[0]),
        model.predict(array[:4]),
        atol=1e-10,
    )
    # Opposite hourly effects cancel in a daily mean; mean absolute hourly SHAP would not.
    opposed = grouped_shap(
        np.array([[1, 2, 3], [-1, -2, -3]]), ["temperature_c", "wind_sin", "wind_cos"]
    )
    assert opposed.mean().abs().sum() == 0


def test_sen_and_mann_kendall_known_monotone_and_ties():
    dates = pd.date_range("2017-01-01", periods=24, freq="MS")
    result = trend_test(pd.DataFrame({"date": dates, "value": np.arange(24) * 2 + 50}))
    assert result["slope_per_year"] == pytest.approx(24)
    assert result["mann_kendall_s"] == 276
    variance = 24 * 23 * 53 / 18
    assert result["mann_kendall_z"] == pytest.approx(275 / np.sqrt(variance))
    assert result["mann_kendall_p"] < 1e-10
    constant = trend_test(pd.DataFrame({"date": dates, "value": 10}))
    assert constant["mann_kendall_s"] == 0
    assert constant["mann_kendall_p"] == 1
    assert constant["slope_per_year"] == 0


def test_gam_extreme_predictor_uses_documented_boundary_extension():
    from apps.analytics.research_models import GAMRegressor

    x = pd.DataFrame({"precipitation_mm": np.linspace(0, 20, 100)})
    model = GAMRegressor().fit(x, x.precipitation_mm.to_numpy() * 2 + 30)
    extreme = pd.DataFrame({"precipitation_mm": [200.0]})
    prediction = model.predict(extreme)
    assert np.isfinite(prediction).all()
    assert model.prediction_support["clipped_rows"] == 1
    boundary = model.bounds[0, 1] * model.scale[0] + model.mean[0]
    np.testing.assert_allclose(prediction, model.predict([[boundary]]))
    assert extreme.precipitation_mm.iloc[0] == 200.0


def test_nested_weeks_and_outer_embargo_are_excluded_from_inner_fits():
    times = pd.Series(pd.date_range("2019-01-01", periods=24 * 120, freq="h", tz="UTC"))
    assignment = week_partition(times)
    outer = {w for w, f in assignment.items() if f == 0}
    allowed = set(assignment) - outer
    inner = week_partition(times[week_labels(times).isin(allowed)])
    held = {w for w, f in inner.items() if f == 0}
    train, test = split_positions(times, held, allowed, outer)
    labels = week_labels(times)
    assert not set(labels.iloc[train]) & set(labels.iloc[test])
    for week in outer:
        first = pd.Timestamp(week, tz="Asia/Kolkata").tz_convert("UTC")
        forbidden = times.between(
            first - pd.Timedelta(hours=24), first + pd.Timedelta(days=8), inclusive="left"
        )
        assert not forbidden.iloc[np.concatenate([train, test])].any()


def test_actual_bootstrap_refit_intervals_are_reproducible(tmp_path):
    rng = np.random.default_rng(4)
    chunks = []
    for year in [2017, 2018, 2024, 2025]:
        local = pd.date_range(f"{year}-01-01", periods=24 * 16, freq="h", tz="Asia/Kolkata")
        chunks.append(pd.Series(local.tz_convert("UTC")))
    times = pd.concat(chunks, ignore_index=True)
    frame = pd.DataFrame({"observed_at": pd.to_datetime(times, utc=True)})
    for column in [
        "temperature_c",
        "relative_humidity",
        "wind_speed_ms",
        "surface_pressure_hpa",
        "precipitation_mm",
        "total_cloud_cover",
        "solar_radiation_wm2",
        "boundary_layer_height_m",
    ]:
        frame[column] = rng.uniform(1, 30, len(frame))
    frame["wind_dir_deg"] = rng.uniform(0, 360, len(frame))
    frame["value"] = 20 + frame.temperature_c + np.where(frame.observed_at.dt.year >= 2024, 5, 0)
    config = dict(target="daily", trend=True, periods="separate", blh=False)
    weather = frame.drop(columns="value")
    dates, draws = bootstrap_normalisations(
        frame, weather, config, tmp_path, "fixture", refits=2, seed=88
    )
    dates2, draws2 = bootstrap_normalisations(
        frame, weather, config, tmp_path, "repeated", refits=2, seed=88
    )
    assert dates.equals(dates2)
    np.testing.assert_array_equal(draws, draws2)
    raw = (
        frame.assign(date=frame.observed_at.dt.tz_convert("Asia/Kolkata").dt.date)
        .groupby("date", as_index=False)
        .value.mean()
    )
    norm = pd.DataFrame({"date": dates, "value": draws.mean(axis=0)})
    oof = raw.copy()
    oof["prediction"] = oof.value + np.sin(np.arange(len(oof)))
    oof["period"] = np.where(pd.to_datetime(oof.date).dt.year >= 2024, "recent", "old")
    first = comparison_intervals(raw, norm, dates, draws, oof, [2017, 2018], samples=30, seed=88)
    second = comparison_intervals(raw, norm, dates2, draws2, oof, [2017, 2018], samples=30, seed=88)
    assert first == second
    assert first["normalised"]["ci95_difference"][1] > first["normalised"]["ci95_difference"][0]
    assert first["normalised"]["refits"] == 2
    missing = comparison_intervals(raw, norm, dates, draws, oof, [2016, 2017], samples=30)
    assert missing["status"] == "unavailable"
