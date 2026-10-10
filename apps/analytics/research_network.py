"""Side-by-side network comparisons on exactly the same supported dates."""

from pathlib import Path

import numpy as np
import pandas as pd

from .model_diagnostics import scores
from .research_stats import season_labels
from .research_uncertainty import comparison_intervals


def matched_network_comparisons(child, seed=20261009):
    results = child.results
    cohorts = {key: row for key, row in results["cohorts"].items() if "nested_validation" in row}
    if len(cohorts) < 2:
        return dict(status="unavailable", reason="Both network models must pass Run 7 readiness")
    root = Path("data/results") / str(child.pk)
    frames = {
        key: pd.read_csv(root / f"{row['artifacts_prefix']}_nested_oof.csv")
        for key, row in cohorts.items()
    }
    common = set.intersection(*(set(frame.date) for frame in frames.values()))
    years = sorted(set(pd.to_datetime(sorted(common)).year))
    old = [year for year in years if 2015 <= year <= 2019]
    recent = [year for year in years if 2024 <= year <= 2025]
    result = dict(status="matched supported dates", days=len(common), years=years, cohorts={})
    for cohort, row in cohorts.items():
        prefix = row["artifacts_prefix"]
        raw = pd.read_csv(root / f"{prefix}_raw_daily.csv")
        norm = pd.read_csv(root / f"{prefix}_deweathered_daily.csv")
        raw = raw[raw.date.isin(common)]
        norm = norm[norm.date.isin(common)]
        oof = frames[cohort][frames[cohort].date.isin(common)].copy()
        dates = pd.read_csv(root / f"{prefix}_refit_00_daily.csv").date
        values = np.load(root / f"{prefix}_refit_draws.npz")["values"]
        result["cohorts"][cohort] = dict(
            long_run=comparison_intervals(raw, norm, dates, values, oof, old, recent, seed=seed)
            if old and recent
            else dict(status="unavailable", reason="One era absent"),
            ncap_proxy=comparison_intervals(raw, norm, dates, values, oof, [2017, 2018], seed=seed),
        )
    return result


def seasonal_validation(child):
    root = Path("data/results") / str(child.pk)
    result = []
    for cohort, record in child.results["cohorts"].items():
        if "nested_validation" not in record:
            continue
        rows = pd.read_csv(root / f"{record['artifacts_prefix']}_nested_oof.csv")
        rows["season"] = season_labels(pd.to_datetime(rows.date))
        for (period, season), group in rows.groupby(["period", "season"]):
            for name, column in [
                ("full_rf", "prediction"),
                ("weather_rf", "weather_prediction"),
                ("weather_gam", "gam_prediction"),
            ]:
                result.append(
                    dict(
                        cohort=cohort,
                        period=period,
                        season=season,
                        model=name,
                        **scores(group.value, group[column]),
                    )
                )
    return result
