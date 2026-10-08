"""Deterministic validation and pooled-reference normalisation, without database I/O."""

from datetime import timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split

from .deweather import WEATHER

IST = "Asia/Kolkata"


def period_labels(times):
    years = pd.to_datetime(times, utc=True).dt.tz_convert(IST).dt.year
    return np.where(
        years.between(2015, 2019), "old", np.where(years.between(2024, 2025), "recent", "gap")
    )


def week_labels(times):
    local = pd.to_datetime(times, utc=True).dt.tz_convert(IST).dt.tz_localize(None)
    return (local.dt.normalize() - pd.to_timedelta(local.dt.weekday, unit="D")).dt.strftime(
        "%Y-%m-%d"
    )


def week_folds(times, n_folds=5, seed=42, embargo_hours=24):
    """Assign whole Monday-start IST weeks within each era, with a boundary embargo."""
    times = pd.Series(pd.to_datetime(times, utc=True)).reset_index(drop=True)
    weeks = week_labels(times)
    periods = period_labels(times)
    if (periods == "gap").any():
        raise ValueError("CV cannot include the concentration gap")
    assignment = np.full(len(times), -1, dtype=int)
    rng = np.random.default_rng(seed)
    for period in sorted(set(periods)):
        unique = np.array(sorted(set(weeks[periods == period])))
        if len(unique) < n_folds:
            raise ValueError("Too few observed weeks for blocked CV")
        rng.shuffle(unique)
        lookup = {week: i % n_folds for i, week in enumerate(unique)}
        for i in np.flatnonzero(periods == period):
            assignment[i] = lookup[weeks.iloc[i]]
    for fold in range(n_folds):
        test = assignment == fold
        train = ~test
        if embargo_hours:
            for week in sorted(set(weeks[test])):
                first = pd.Timestamp(week, tz=IST).tz_convert("UTC").to_pydatetime()
                last = first + timedelta(days=7)
                train &= ~(
                    (times >= first - timedelta(hours=embargo_hours))
                    & (times < last + timedelta(hours=embargo_hours))
                ).to_numpy()
        yield np.flatnonzero(train), np.flatnonzero(test)


def lag_correlations(pm, wind, max_lag=12, minimum_pairs=48):
    """Pearson r(PM[t], wind[t+lag]); shift timestamps, never bridge missing rows."""
    records = []
    pm = pm.dropna().sort_index()
    wind = wind.dropna().sort_index()
    for lag in range(-max_lag, max_lag + 1):
        shifted = wind.copy()
        shifted.index = pd.to_datetime(shifted.index.asi8 - lag * 3600 * 1_000_000_000, utc=True)
        pairs = pd.concat([pm.rename("pm"), shifted.rename("wind")], axis=1).dropna()
        enough = len(pairs) >= minimum_pairs and pairs.pm.std() > 0 and pairs.wind.std() > 0
        records.append(
            dict(
                lag_hours=lag,
                correlation=float(pairs.pm.corr(pairs.wind)) if enough else None,
                pairs=len(pairs),
            )
        )
    return pd.DataFrame(records)


def weather_daily(frame):
    """Observed weather only; each daily variable requires 18 finite hourly reports."""
    rows = frame.copy()
    time = pd.to_datetime(rows.observed_at, utc=True).dt.tz_convert(IST)
    rows["date"] = time.dt.date
    rows["wind_sin"] = np.sin(np.deg2rad(rows.wind_dir_deg))
    rows["wind_cos"] = np.cos(np.deg2rad(rows.wind_dir_deg))
    values = []
    for day, group in rows.groupby("date", sort=True):
        item = {"observed_at": pd.Timestamp(day, tz=IST).tz_convert("UTC")}
        for feature in WEATHER:
            valid = group[feature].dropna()
            item[feature] = (
                float(valid.sum() if feature == "precipitation_mm" else valid.mean())
                if len(valid) >= 18
                else None
            )
        if group.wind_dir_deg.notna().sum() >= 18:
            item["wind_dir_deg"] = float(
                np.rad2deg(np.arctan2(group.wind_sin.mean(), group.wind_cos.mean())) % 360
            )
        values.append(item)
    return pd.DataFrame(values)


def target_rows(hourly, weather, target="hourly"):
    if target == "hourly":
        return hourly.copy()
    rows = hourly.copy()
    rows["date"] = pd.to_datetime(rows.observed_at, utc=True).dt.tz_convert(IST).dt.date
    grouped = rows.groupby("date").agg(value=("value", "mean"), hours=("value", "count"))
    grouped = grouped[grouped.hours >= 18].reset_index()
    grouped["observed_at"] = pd.to_datetime(grouped.date).dt.tz_localize(IST).dt.tz_convert("UTC")
    return grouped.rename(columns={"hours": "valid_count"})[
        ["observed_at", "value", "valid_count"]
    ].merge(weather_daily(weather), on="observed_at", how="left")


def features(frame, config, original=False):
    if original:
        from .deweather import design_matrix

        return design_matrix(frame)
    rows = frame.copy().reset_index(drop=True)
    time = pd.to_datetime(rows.observed_at, utc=True)
    local = time.dt.tz_convert(IST)
    period = period_labels(time)
    if (period == "gap").any():
        raise ValueError("Model targets must be in observed eras")
    x = pd.DataFrame(index=rows.index)
    if config["trend"]:
        origin = pd.Series(pd.Timestamp("2015-01-01", tz=IST), index=rows.index)
        if not original:
            origin.loc[period == "recent"] = pd.Timestamp("2024-01-01", tz=IST)
        x["trend"] = (time - origin.dt.tz_convert("UTC")).dt.total_seconds() / 86400
    for feature in WEATHER:
        if feature == "boundary_layer_height_m" and not config["blh"]:
            continue
        if feature != "wind_dir_deg":
            x[feature] = rows[feature]
    x["wind_sin"] = np.sin(np.deg2rad(rows.wind_dir_deg))
    x["wind_cos"] = np.cos(np.deg2rad(rows.wind_dir_deg))
    x["doy_sin"] = np.sin(2 * np.pi * local.dt.dayofyear / 365.25)
    x["doy_cos"] = np.cos(2 * np.pi * local.dt.dayofyear / 365.25)
    if config["target"] == "hourly":
        x["hour_sin"] = np.sin(2 * np.pi * local.dt.hour / 24)
        x["hour_cos"] = np.cos(2 * np.pi * local.dt.hour / 24)
    x["weekday"] = local.dt.weekday
    if config["periods"] == "pooled" and not original:
        x["period"] = (period == "recent").astype(int)
    complete = np.isfinite(x.to_numpy(dtype=float)).all(axis=1)
    if "value" in rows:
        complete &= np.isfinite(rows.value.to_numpy(dtype=float))
    return rows.loc[complete].reset_index(drop=True), x.loc[complete].reset_index(drop=True).astype(
        np.float32
    )


def forest(seed=42, n_trees=100):
    return RandomForestRegressor(
        n_estimators=n_trees,
        max_depth=12,
        min_samples_leaf=12,
        max_features=0.7,
        random_state=seed,
        n_jobs=1,
    )


def fit_predict(x, y, periods, train, test, config, seed=42, n_trees=100):
    prediction = np.full(len(test), np.nan)
    groups = sorted(set(periods[test])) if config["periods"] == "separate" else [None]
    for group in groups:
        training = train if group is None else train[periods[train] == group]
        selected = np.arange(len(test)) if group is None else np.flatnonzero(periods[test] == group)
        if len(training) < 24:
            continue
        model = forest(seed, n_trees).fit(x[training], y[training])
        prediction[selected] = model.predict(x[test[selected]])
    return prediction


def daily_predictions(rows, prediction, target):
    output = pd.DataFrame(
        dict(observed_at=rows.observed_at, value=rows.value, prediction=prediction)
    )
    output["date"] = pd.to_datetime(output.observed_at, utc=True).dt.tz_convert(IST).dt.date
    output = output.dropna(subset=["prediction"])
    if target == "hourly":
        output = (
            output.groupby("date")
            .agg(
                value=("value", "mean"),
                prediction=("prediction", "mean"),
                hours=("prediction", "count"),
            )
            .reset_index()
        )
        output = output[output.hours >= 18]
    else:
        output = output[["date", "value", "prediction"]]
    output["observed_at"] = pd.to_datetime(output.date).dt.tz_localize(IST).dt.tz_convert("UTC")
    output["period"] = period_labels(output.observed_at)
    return output.reset_index(drop=True)


def scores(actual, predicted):
    a, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    valid = np.isfinite(a) & np.isfinite(p)
    a, p = a[valid], p[valid]
    if len(a) < 2:
        return {"n": len(a), "r2": None, "rmse": None, "bias": None, "nmb_percent": None}
    return dict(
        n=len(a),
        r2=float(r2_score(a, p)),
        rmse=float(root_mean_squared_error(a, p)),
        bias=float((p - a).mean()),
        nmb_percent=float(100 * (p - a).sum() / a.sum()),
    )


def evaluate(frame, weather, config, scheme="weeks", seed=42, n_trees=100, original=False):
    rows, x = features(target_rows(frame, weather, config["target"]), config, original)
    array, y = x.to_numpy(), rows.value.to_numpy()
    periods = period_labels(rows.observed_at)
    prediction = np.full(len(rows), np.nan)
    fold_details = []
    if scheme == "weeks":
        splits = list(week_folds(rows.observed_at, seed=seed))
    elif scheme == "random":
        train, test = train_test_split(
            np.arange(len(rows)), test_size=0.2, random_state=seed, stratify=periods
        )
        splits = [(train, test)]
    elif scheme == "transfer":
        splits = [
            (np.flatnonzero(periods == a), np.flatnonzero(periods == b))
            for a, b in [("old", "recent"), ("recent", "old")]
            if (periods == a).any() and (periods == b).any()
        ]
    else:
        raise ValueError(scheme)
    for fold, (train, test) in enumerate(splits):
        # Period-specific models cannot learn an unseen period. For transfer only,
        # fit the source-period forest and apply it to the other period explicitly.
        fit_config = {**config, "periods": "pooled"} if scheme == "transfer" else config
        prediction[test] = fit_predict(array, y, periods, train, test, fit_config, seed, n_trees)
        fold_details.append(
            dict(
                fold=fold,
                train=len(train),
                test=len(test),
                train_periods=sorted(set(periods[train])),
                test_periods=sorted(set(periods[test])),
            )
        )
    daily = daily_predictions(rows, prediction, config["target"])
    periods_scores = {p: scores(g.value, g.prediction) for p, g in daily.groupby("period")}
    return dict(
        config=config,
        scheme=scheme,
        native=scores(y, prediction),
        native_periods={
            p: scores(y[periods == p], prediction[periods == p]) for p in sorted(set(periods))
        },
        daily=scores(daily.value, daily.prediction),
        periods=periods_scores,
        folds=fold_details,
        rows=rows,
        prediction=prediction,
        daily_rows=daily,
        features=list(x.columns),
    )


def pooled_normalise(model, targets, reference, n_samples=300, seed=42, return_draws=False):
    """One common observed donor draw, fixing only explicit period and local trend."""
    if n_samples < 300:
        raise ValueError("At least 300 pooled reference draws required")
    if list(targets.columns) != list(reference.columns):
        raise ValueError("Target and reference features must match")
    rng = np.random.default_rng(seed)
    donors = reference.to_numpy(dtype=np.float32)[rng.integers(len(reference), size=n_samples)]
    values = targets.to_numpy(dtype=np.float32)
    keys = []
    for name in ["trend", "period"]:
        if name not in targets:
            continue
        column = targets.columns.get_loc(name)
        if name == "trend":
            thresholds = np.unique(
                np.concatenate(
                    [t.tree_.threshold[t.tree_.feature == column] for t in model.estimators_]
                )
            )
            keys.append(np.searchsorted(thresholds, values[:, column], side="left"))
        else:
            keys.append(values[:, column])
    group_keys = np.column_stack(keys) if keys else np.zeros((len(values), 1))
    _, first, inverse = np.unique(group_keys, axis=0, return_index=True, return_inverse=True)
    samples = np.empty((len(first), n_samples))
    for offset in range(0, len(first), 64):
        selected = values[first[offset : offset + 64]]
        scenarios = np.tile(donors, (len(selected), 1))
        for name in ["trend", "period"]:
            if name in targets:
                column = targets.columns.get_loc(name)
                scenarios[:, column] = np.repeat(selected[:, column], n_samples)
        samples[offset : offset + len(selected)] = model.predict(scenarios).reshape(
            len(selected), n_samples
        )
    mean = samples.mean(axis=1)[inverse]
    error = samples.std(axis=1, ddof=1)[inverse] / np.sqrt(n_samples)
    return (mean, error, samples, inverse) if return_draws else (mean, error)


def residual_tables(daily):
    rows = daily.copy()
    times = pd.to_datetime(rows.date)
    rows["month"] = times.dt.month
    rows["year_month"] = times.dt.strftime("%Y-%m")
    rows["season"] = times.dt.month.map(
        {
            1: "winter",
            2: "winter",
            12: "winter",
            3: "pre_monsoon",
            4: "pre_monsoon",
            5: "pre_monsoon",
            6: "monsoon",
            7: "monsoon",
            8: "monsoon",
            9: "monsoon",
            10: "post_monsoon",
            11: "post_monsoon",
        }
    )
    tables = {}
    for name in ["month", "year_month", "season"]:
        tables[name] = [
            {"period": period, name: label, **scores(group.value, group.prediction)}
            for (period, label), group in rows.groupby(["period", name])
        ]
    return tables


def readiness(daily, criteria):
    months = residual_tables(daily)["month"]
    result = []
    for period, group in daily.groupby("period"):
        metric = scores(group.value, group.prediction)
        selected = [r for r in months if r["period"] == period]
        weeks = len(set(week_labels(group.observed_at)))
        failures = []
        if metric["r2"] < criteria["daily_oof_r2_min_each_period"]:
            failures.append("daily R2")
        if abs(metric["nmb_percent"]) > criteria["absolute_nmb_percent_max_each_period"]:
            failures.append("overall NMB")
        if weeks < criteria["minimum_weeks_each_period"]:
            failures.append("week support")
        if len(selected) != 12 or any(
            r["n"] < criteria["minimum_days_month_each_period"] for r in selected
        ):
            failures.append("monthly support")
        if any(
            abs(r["nmb_percent"]) > criteria["absolute_month_nmb_percent_max_each_period"]
            for r in selected
        ):
            failures.append("monthly NMB")
        result.append(
            dict(
                period=period,
                **metric,
                weeks=weeks,
                max_month_abs_nmb=max(abs(r["nmb_percent"]) for r in selected),
                passed=not failures,
                failures=failures,
            )
        )
    return dict(passed=bool(result) and all(r["passed"] for r in result), periods=result)
