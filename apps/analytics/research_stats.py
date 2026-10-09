"""Research statistics with explicit temporal support and reproducible resampling."""

import numpy as np
import pandas as pd
from scipy.stats import norm, theilslopes

from .model_diagnostics import week_labels


def season_labels(dates):
    months = pd.to_datetime(dates).dt.month
    return np.where(
        months.isin([10, 11, 12, 1, 2]),
        "winter",
        np.where(months.isin([3, 4, 5]), "pre_monsoon", "monsoon"),
    )


def trend_test(months):
    rows = months.dropna(subset=["value"]).sort_values("date")
    if len(rows) < 12:
        return dict(status="unavailable", months=len(rows), reason="Fewer than 12 observed months")
    dates = pd.to_datetime(rows.date)
    time = (dates.dt.year * 12 + dates.dt.month).to_numpy(dtype=float)
    y = rows.value.to_numpy(dtype=float)
    slope, _, low, high = theilslopes(y, time)
    s = sum(int(np.sign(y[j] - y[i])) for i in range(len(y)) for j in range(i + 1, len(y)))
    _, ties = np.unique(y, return_counts=True)
    n = len(y)
    variance = (n * (n - 1) * (2 * n + 5) - sum(t * (t - 1) * (2 * t + 5) for t in ties)) / 18
    z = (s - np.sign(s)) / np.sqrt(variance) if variance else 0
    # Seasonal MK compares each calendar month across observed years.
    ss, vv = 0, 0.0
    for month in range(1, 13):
        values = y[dates.dt.month.to_numpy() == month]
        k = len(values)
        ss += sum(int(np.sign(values[j] - values[i])) for i in range(k) for j in range(i + 1, k))
        _, counts = np.unique(values, return_counts=True)
        vv += (k * (k - 1) * (2 * k + 5) - sum(t * (t - 1) * (2 * t + 5) for t in counts)) / 18
    sz = (ss - np.sign(ss)) / np.sqrt(vv) if vv else 0
    return dict(
        status="descriptive",
        months=n,
        slope_per_month=float(slope),
        slope_per_year=float(12 * slope),
        slope_ci95_per_year=[float(12 * low), float(12 * high)],
        mann_kendall_s=s,
        mann_kendall_z=float(z),
        mann_kendall_p=float(2 * norm.sf(abs(z))),
        seasonal_mann_kendall_p=float(2 * norm.sf(abs(sz))) if vv else None,
        caveat=(
            "MK p values assume independent residual ordering; "
            "seasonality/autocorrelation can invalidate nominal significance"
        ),
    )


def week_bootstrap_indices(times, seed):
    weeks = week_labels(pd.Series(times).reset_index(drop=True))
    years = (
        pd.to_datetime(pd.Series(times).reset_index(drop=True), utc=True)
        .dt.tz_convert("Asia/Kolkata")
        .dt.year
    )
    rng = np.random.default_rng(seed)
    positions = []
    for year in sorted(set(years)):
        labels = sorted(set(weeks[years == year]))
        for week in rng.choice(labels, size=len(labels), replace=True):
            positions.extend(np.flatnonzero((weeks == week) & (years == year)))
    return np.asarray(positions, dtype=int)


def grouped_shap(values, columns):
    values = np.asarray(values)
    groups = {}
    for index, column in enumerate(columns):
        label = (
            "wind_direction"
            if column in ["wind_sin", "wind_cos"]
            else (
                "seasonal_calendar"
                if column in ["doy_sin", "doy_cos"]
                else ("hour_calendar" if column in ["hour_sin", "hour_cos"] else column)
            )
        )
        groups.setdefault(label, np.zeros(len(values)))
        groups[label] += values[:, index]
    return pd.DataFrame(groups)


def ale(model, x, feature, bins=12):
    circular = feature == "wind_direction"
    column = None if circular else x.columns.get_loc(feature)
    array = x.to_numpy(dtype=float)
    if circular:
        sine, cosine = x.columns.get_loc("wind_sin"), x.columns.get_loc("wind_cos")
        observed = np.rad2deg(np.arctan2(array[:, sine], array[:, cosine])) % 360
        edges = np.linspace(0, 360, bins + 1)
    else:
        observed = array[:, column]
        edges = np.unique(np.quantile(observed, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:
        return pd.DataFrame(columns=["lower", "upper", "midpoint", "n", "ale"])
    assignment = np.clip(np.searchsorted(edges, observed, side="right") - 1, 0, len(edges) - 2)
    differences, counts = [], []
    for index in range(len(edges) - 1):
        subset = array[assignment == index]
        counts.append(len(subset))
        if not len(subset):
            differences.append(np.nan)
            continue
        low, high = subset.copy(), subset.copy()
        if circular:
            for matrix, angle in [(low, edges[index]), (high, edges[index + 1])]:
                matrix[:, sine], matrix[:, cosine] = (
                    np.sin(np.deg2rad(angle)),
                    np.cos(np.deg2rad(angle)),
                )
        else:
            low[:, column], high[:, column] = edges[index], edges[index + 1]
        differences.append(float((model.predict(high) - model.predict(low)).mean()))
    delta = np.asarray(differences)
    if circular and np.isfinite(delta).all():
        delta -= delta.sum() / len(delta)
    values = np.cumsum(np.nan_to_num(delta)) - np.nan_to_num(delta) / 2
    values -= np.average(values, weights=counts)
    values[np.asarray(counts) == 0] = np.nan
    return pd.DataFrame(
        dict(
            lower=edges[:-1],
            upper=edges[1:],
            midpoint=(edges[:-1] + edges[1:]) / 2,
            n=counts,
            ale=values,
        )
    )
