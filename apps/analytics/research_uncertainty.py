"""Actual forest refits and observed-calendar bootstrap comparison intervals."""

import hashlib
import json
from datetime import timedelta

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits

from .model_diagnostics import (
    daily_predictions,
    features,
    forest,
    period_labels,
    pooled_normalise,
    target_rows,
    weather_daily,
)
from .research_stats import week_bootstrap_indices


def bootstrap_normalisations(frame, weather, config, output, prefix, refits=20, seed=20261009):
    rows, x = features(target_rows(frame, weather, config["target"]), config)
    reference = weather[period_labels(weather.observed_at) != "gap"].copy()
    if config["target"] == "daily":
        reference = weather_daily(reference)
    _, reference_x = features(reference, config)
    periods = period_labels(rows.observed_at)
    groups = sorted(set(periods)) if config["periods"] == "separate" else [None]

    def refit(index):
        local_seed = seed + index
        values = np.empty(len(rows))
        metadata = []
        for group in groups:
            positions = np.arange(len(rows)) if group is None else np.flatnonzero(periods == group)
            boot = week_bootstrap_indices(rows.iloc[positions].observed_at, local_seed)
            train = positions[boot]
            model = forest(local_seed).fit(x.iloc[train].to_numpy(), rows.iloc[train].value)
            values[positions] = pooled_normalise(
                model, x.iloc[positions], reference_x, seed=local_seed
            )[0]
            metadata.append(
                dict(
                    period=group or "pooled",
                    training_rows=len(train),
                    sampled_positions_sha256=hashlib.sha256(train.tobytes()).hexdigest(),
                    parameters=model.get_params(),
                )
            )
        daily = daily_predictions(rows, values, config["target"])
        daily[["date", "prediction"]].rename(columns={"prediction": "value"}).to_csv(
            output / f"{prefix}_refit_{index:02d}_daily.csv", index=False
        )
        print(
            json.dumps(
                dict(
                    event="refit_finished",
                    cohort=prefix,
                    refit=index + 1,
                    total=refits,
                    days=len(daily),
                )
            ),
            flush=True,
        )
        return daily[["date", "prediction"]], dict(
            refit=index,
            seed=local_seed,
            models=metadata,
            reference_rows=len(reference_x),
            donors=300,
        )

    with threadpool_limits(limits=1):
        results = Parallel(n_jobs=2, prefer="threads")(delayed(refit)(i) for i in range(refits))
    dates = results[0][0].date
    for daily, _ in results:
        if not dates.equals(daily.date):
            raise ValueError("Refit dates changed; cannot combine uncertainty draws")
    matrix = np.stack([daily.prediction.to_numpy() for daily, _ in results])
    np.savez_compressed(
        output / f"{prefix}_refit_draws.npz", dates=dates.astype(str).to_numpy(), values=matrix
    )
    (output / f"{prefix}_refit_metadata.json").write_text(
        json.dumps([meta for _, meta in results], indent=2)
    )
    return dates, matrix


def comparison_intervals(
    raw,
    normalised,
    refit_dates,
    refit_values,
    oof,
    baseline_years,
    recent_years=(2024, 2025),
    seed=20261009,
    samples=500,
):
    """Equal-year means; refit-mixture plus calendar blocks and centred OOF residuals."""
    raw = raw.dropna(subset=["value"]).copy()
    normalised = normalised.dropna(subset=["value"]).copy()
    raw["date"] = pd.to_datetime(raw.date).dt.date
    normalised["date"] = pd.to_datetime(normalised.date).dt.date
    required = set(baseline_years) | set(recent_years)
    available = set(pd.to_datetime(raw.date).dt.year)
    if not required.issubset(available):
        return dict(
            status="unavailable",
            reason="Required eligible years are missing",
            required_years=sorted(required),
            available_years=sorted(available),
        )
    oof = oof.copy()
    oof["date"] = pd.to_datetime(oof.date).dt.date
    residual = oof.value - oof.prediction
    residual -= residual.groupby(oof.period).transform("mean")
    error = pd.Series(residual.to_numpy(), index=oof.date)
    normalised = normalised[normalised.date.isin(error.index)].copy()
    draws = pd.DataFrame(refit_values.T, index=pd.DatetimeIndex(pd.to_datetime(refit_dates)).date)
    normalised = normalised[normalised.date.isin(draws.index)].copy()
    if not required.issubset(set(pd.to_datetime(normalised.date).dt.year)):
        return dict(status="unavailable", reason="Normalised OOF support lacks a required year")
    # Match raw and normalised dates so the model and temporal comparisons share support.
    raw = raw[raw.date.isin(normalised.date)].set_index("date").reindex(normalised.date)
    dates = normalised.date.to_numpy()
    years = pd.to_datetime(dates).year.to_numpy()
    y_raw = raw.value.to_numpy()
    y_norm = normalised.value.to_numpy()
    matrix = draws.loc[dates].to_numpy().T + error.loc[dates].to_numpy()[None, :]
    by_year = {year: np.flatnonzero(years == year) for year in sorted(required)}
    blocks = {}
    for year, positions in by_year.items():
        group, previous = [], None
        blocks[year] = []
        for pos in positions:
            if group and (len(group) == 7 or dates[pos] - previous != timedelta(days=1)):
                blocks[year].append(np.asarray(group))
                group = []
            group.append(pos)
            previous = dates[pos]
        if group:
            blocks[year].append(np.asarray(group))
    rng = np.random.default_rng(seed)

    def positions(period):
        selected = []
        for year in rng.choice(period, len(period), replace=True):
            year_blocks = blocks[int(year)]
            chunks = []
            count = 0
            n = len(by_year[int(year)])
            while count < n:
                block = year_blocks[rng.integers(len(year_blocks))]
                chunks.append(block)
                count += len(block)
            selected.append(np.concatenate(chunks)[:n])
        return selected

    def mean(value, period):
        return float(np.mean([value[by_year[year]].mean() for year in period]))

    results = {}
    sample_indices = [
        (positions(baseline_years), positions(recent_years), rng.integers(len(matrix)))
        for _ in range(samples)
    ]
    for label, point_values in [("raw", y_raw), ("normalised", y_norm)]:
        before, after = mean(point_values, baseline_years), mean(point_values, recent_years)
        delta, percent = [], []
        for old, new, refit in sample_indices:
            value = y_raw if label == "raw" else matrix[refit]
            first = np.mean([value[index].mean() for index in old])
            last = np.mean([value[index].mean() for index in new])
            delta.append(last - first)
            percent.append(100 * (last - first) / first)
        results[label] = dict(
            baseline_mean=before,
            recent_mean=after,
            difference=after - before,
            percent_change=100 * (after - before) / before,
            ci95_difference=list(map(float, np.quantile(delta, [0.025, 0.975]))),
            ci95_percent=list(map(float, np.quantile(percent, [0.025, 0.975]))),
            days=len(dates),
            refits=len(matrix) if label == "normalised" else 0,
        )
    return dict(
        status="descriptive",
        baseline_years=list(baseline_years),
        recent_years=list(recent_years),
        samples=samples,
        seed=seed,
        block_days=7,
        raw=results["raw"],
        normalised=results["normalised"],
        uncertainty="20 actual week-resampled model refits; shared pooled donors; "
        "year/calendar-block draws and centred nested OOF residuals; "
        "conditional on selected structure and observed station panel",
    )
