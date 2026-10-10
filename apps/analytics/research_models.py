"""Nested week validation and GAM cross-checks on observed concentration targets."""

from datetime import timedelta

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits

from .model_diagnostics import (
    daily_predictions,
    features,
    fit_predict,
    period_labels,
    scores,
    target_rows,
    week_labels,
)


def week_partition(times, folds=3, seed=20261009):
    times = pd.Series(times).reset_index(drop=True)
    labels, periods = week_labels(times), period_labels(times)
    rng = np.random.default_rng(seed)
    result = {}
    for period in sorted(set(periods)):
        weeks = np.array(sorted(set(labels[periods == period])))
        rng.shuffle(weeks)
        result.update({str(week): index % folds for index, week in enumerate(weeks)})
    return result


def split_positions(times, held_weeks, allowed=None, forbidden_weeks=()):
    times = pd.Series(times).reset_index(drop=True)
    labels = week_labels(times)
    test = labels.isin(held_weeks).to_numpy()
    train = ~test
    if allowed is not None:
        train &= labels.isin(allowed).to_numpy()
    for week in held_weeks:
        first = pd.Timestamp(week, tz="Asia/Kolkata").tz_convert("UTC").to_pydatetime()
        train &= ~(
            (times >= first - timedelta(hours=24)) & (times < first + timedelta(days=8))
        ).to_numpy()
    for week in forbidden_weeks:
        first = pd.Timestamp(week, tz="Asia/Kolkata").tz_convert("UTC")
        forbidden = (
            (times >= first - timedelta(hours=24)) & (times < first + timedelta(days=8))
        ).to_numpy()
        train &= ~forbidden
        test &= ~forbidden
    return np.flatnonzero(train), np.flatnonzero(test)


def datasets(frame, weather, variants):
    targets = {"hourly": frame, "daily": target_rows(frame, weather, "daily")}
    return {v["name"]: (*features(targets[v["target"]], v), v) for v in variants}


def candidate_oof(data, partitions, allowed=None, forbidden_weeks=()):
    rows, x, config = data
    periods = period_labels(rows.observed_at)
    predictions = np.full(len(rows), np.nan)
    for fold in sorted(set(partitions.values())):
        held = {w for w, f in partitions.items() if f == fold}
        train, test = split_positions(rows.observed_at, held, allowed, forbidden_weeks)
        if len(train) < 24 or not len(test):
            continue
        predictions[test] = fit_predict(
            x.to_numpy(), rows.value.to_numpy(), periods, train, test, config
        )
    return daily_predictions(rows, predictions, config["target"])


def choose_inner(prepared, partitions, allowed, forbidden_weeks):
    trials = Parallel(n_jobs=4, prefer="threads")(
        delayed(candidate_oof)(dataset, partitions, allowed, forbidden_weeks)
        for dataset in prepared.values()
    )
    common = set(trials[0].date)
    for trial in trials[1:]:
        common &= set(trial.date)
    if not common:
        raise ValueError("No shared daily targets in nested training folds")
    quality = []
    for trial in trials:
        trial = trial[trial.date.isin(common)]
        quality.append(
            float(
                np.mean([scores(g.value, g.prediction)["r2"] for _, g in trial.groupby("period")])
            )
        )
    names = list(prepared)
    index = max(range(len(names)), key=lambda i: (quality[i], -i))
    return names[index], dict(zip(names, quality, strict=True))


def weather_dataset(frame, weather, config):
    daily = {**config, "target": "daily"}
    rows, x = features(target_rows(frame, weather, "daily"), daily)
    weather_columns = [
        c
        for c in x
        if c not in {"trend", "period", "doy_sin", "doy_cos", "hour_sin", "hour_cos", "weekday"}
    ]
    return rows, x[weather_columns], daily


class GAMRegressor:
    """Training-only scaling and spline knots; fixed penalty, no outcome tuning."""

    def fit(self, x, y):
        import statsmodels.api as sm
        from statsmodels.gam.api import BSplines, GLMGam

        array = np.asarray(x, dtype=float)
        self.usable = np.ptp(array, axis=0) > 1e-8
        self.mean = array[:, self.usable].mean(axis=0)
        self.scale = array[:, self.usable].std(axis=0)
        self.constant = float(np.mean(y))
        if not self.usable.any():
            self.result = None
            return self
        array = (array[:, self.usable] - self.mean) / self.scale
        # Finite physical support beyond observed training range, without test outcomes.
        bounds = [
            dict(lower_bound=float(a.min() - 5), upper_bound=float(a.max() + 5)) for a in array.T
        ]
        self.bounds = np.asarray([[b["lower_bound"], b["upper_bound"]] for b in bounds])
        self.columns = (
            list(x.columns) if hasattr(x, "columns") else list(range(np.asarray(x).shape[1]))
        )
        smoother = BSplines(
            array, df=[6] * array.shape[1], degree=[3] * array.shape[1], knot_kwds=bounds
        )
        self.result = GLMGam(
            y,
            exog=np.ones((len(y), 1)),
            smoother=smoother,
            alpha=[10] * array.shape[1],
            family=sm.families.Gaussian(),
        ).fit()
        return self

    def predict(self, x):
        array = np.asarray(x, dtype=float)
        if self.result is None:
            return np.repeat(self.constant, len(array))
        array = (array[:, self.usable] - self.mean) / self.scale
        outside = (array < self.bounds[:, 0]) | (array > self.bounds[:, 1])
        self.prediction_support = dict(
            clipped_rows=int(outside.any(axis=1).sum()),
            clipped_features={
                str(self.columns[i]): int(count)
                for i, count in zip(np.flatnonzero(self.usable), outside.sum(axis=0), strict=True)
                if count
            },
            rule="Flat extension outside fixed training spline support; "
            "observed targets and stored weather unchanged",
        )
        array = np.clip(array, self.bounds[:, 0], self.bounds[:, 1])
        return self.result.predict(exog=np.ones((len(array), 1)), exog_smooth=array)


def gam_prediction(x, y, train, test, return_support=False):
    model = GAMRegressor().fit(x.iloc[train], y[train])
    prediction = model.predict(x.iloc[test])
    support = getattr(model, "prediction_support", dict(clipped_rows=0, clipped_features={}))
    return (prediction, support) if return_support else prediction


def nested_validation(frame, weather, protocol, selected_config, city, cohort):
    prepared = datasets(frame, weather, protocol["variants"])
    outer = week_partition(frame.observed_at, protocol["outer_folds"], protocol["seed"])
    weather_predictions, gam_predictions = [], []
    full_predictions = []
    choices = []
    for fold in range(protocol["outer_folds"]):
        held = {w for w, f in outer.items() if f == fold}
        allowed = set(outer) - held
        inner_times = frame[week_labels(frame.observed_at).isin(allowed)].observed_at
        inner = week_partition(inner_times, protocol["inner_folds"], protocol["seed"] + fold + 1)
        print(f"Nested CV {city}/{cohort}: outer {fold + 1}/{protocol['outer_folds']}", flush=True)
        gam_support = []
        with threadpool_limits(limits=1):
            name, quality = choose_inner(prepared, inner, allowed, held)
            rows, x, config = prepared[name]
            train, test = split_positions(rows.observed_at, held, allowed)
            predicted = np.full(len(rows), np.nan)
            predicted[test] = fit_predict(
                x.to_numpy(),
                rows.value.to_numpy(),
                period_labels(rows.observed_at),
                train,
                test,
                config,
            )
            daily = daily_predictions(rows, predicted, config["target"])
            daily["outer_fold"] = fold
            daily["chosen_design"] = name
            full_predictions.append(daily)
            # The weather comparison inherits only the inner-training choice.
            # No selection from the outer held weeks or the full-sample Run 7 result.
            weather_rows, weather_x, weather_config = weather_dataset(frame, weather, config)
            w_periods = period_labels(weather_rows.observed_at)
            w_predictions = np.full(len(weather_rows), np.nan)
            g_predictions = np.full(len(weather_rows), np.nan)
            wt, ws = split_positions(weather_rows.observed_at, held, allowed)
            w_predictions[ws] = fit_predict(
                weather_x.to_numpy(),
                weather_rows.value.to_numpy(),
                w_periods,
                wt,
                ws,
                weather_config,
            )
            gam_groups = sorted(set(w_periods)) if config["periods"] == "separate" else [None]
            for period in gam_groups:
                gt = wt if period is None else wt[w_periods[wt] == period]
                gs = ws if period is None else ws[w_periods[ws] == period]
                if len(gt) >= 24 and len(gs):
                    g_predictions[gs], support = gam_prediction(
                        weather_x, weather_rows.value.to_numpy(), gt, gs, return_support=True
                    )
                    gam_support.append(dict(period=period or "pooled", **support))
            weather_predictions.append(daily_predictions(weather_rows, w_predictions, "daily"))
            gam_predictions.append(daily_predictions(weather_rows, g_predictions, "daily"))
        choices.append(
            dict(
                outer_fold=fold,
                chosen=name,
                inner_scores=quality,
                held_weeks=sorted(held),
                training_weeks=sorted(allowed),
                gam_prediction_support=gam_support,
            )
        )
    full = pd.concat(full_predictions, ignore_index=True).sort_values("date")
    w = pd.concat(weather_predictions, ignore_index=True).rename(
        columns={"prediction": "weather_prediction"}
    )
    g = pd.concat(gam_predictions, ignore_index=True).rename(
        columns={"prediction": "gam_prediction"}
    )
    combined = full.merge(w[["date", "weather_prediction"]], on="date", how="inner").merge(
        g[["date", "gam_prediction"]], on="date", how="inner"
    )
    result = {}
    for name, column in [
        ("nested_full", "prediction"),
        ("weather_only", "weather_prediction"),
        ("gam_weather_only", "gam_prediction"),
    ]:
        result[name] = dict(
            overall=scores(combined.value, combined[column]),
            within_period_r2=float(
                1
                - np.sum((combined[column] - combined.value) ** 2)
                / np.sum((combined.value - combined.groupby("period").value.transform("mean")) ** 2)
            ),
            periods={
                p: scores(group.value, group[column]) for p, group in combined.groupby("period")
            },
            folds={
                str(f): scores(group.value, group[column])
                for f, group in combined.groupby("outer_fold")
            },
        )
    return combined, result, choices
