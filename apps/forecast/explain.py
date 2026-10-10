import numpy as np
import pandas as pd
import shap

from .data import FEATURES
from .estimators import Baseline, LSTMModel, SarimaxModel, TreeModel, predict


def top_drivers(model, rows, background, history):
    names = FEATURES + ([f"seq_{i}" for i in range(7)] if isinstance(model, LSTMModel) else [])
    if isinstance(model, TreeModel):
        values = shap.TreeExplainer(model.model).shap_values(rows[FEATURES])
    elif isinstance(model, SarimaxModel):
        # The last direct-horizon label is unavailable: current exogenous values
        # affect only the regression term, while the filtered past state is fixed.
        params = dict(zip(model.result.param_names, model.result.params, strict=True))
        betas = np.array([params.get(f"x{i + 1}", 0) for i in range(int(model.usable.sum()))])
        scaled = model.scaler.transform(rows[FEATURES])[:, model.usable]
        ref = model.scaler.transform(background[FEATURES])[:, model.usable].mean(axis=0)
        values = np.zeros((len(rows), len(FEATURES)))
        values[:, model.usable] = (scaled - ref) * betas
    elif isinstance(model, Baseline) and model.name in ("persistence", "mean7"):
        name = "pm_t" if model.name == "persistence" else "pm_mean7"
        values = np.zeros((len(rows), len(FEATURES)))
        values[:, FEATURES.index(name)] = rows[name] - background[name].mean()
    else:
        # Small deterministic permutation SHAP; target date is a known calendar
        # fact, fixed per issue. Sequence features remain explicit for the LSTM.
        values = []
        reference = background[names].iloc[
            np.linspace(0, len(background) - 1, min(20, len(background))).astype(int)
        ]
        for _, row in rows.iterrows():

            def evaluate(array, target_date=row.target_date):
                sample = pd.DataFrame(array, columns=names)
                sample["target_date"] = target_date
                return predict(model, sample, history)

            explainer = shap.Explainer(evaluate, reference, algorithm="permutation", seed=20261010)
            values.append(
                explainer(rows.loc[[row.name], names], max_evals=2 * len(names) + 1).values[0]
            )
        values = np.asarray(values)
    result = []
    for row, contributions in zip(rows.itertuples(), values, strict=True):
        indices = np.argsort(np.abs(contributions))[::-1][:5]
        result.append(
            [
                {
                    "feature": names[int(i)],
                    "value": float(getattr(row, names[int(i)])),
                    "shap_value": float(contributions[i]),
                    "interpretation": "conditional model attribution, not causal",
                }
                for i in indices
            ]
        )
    return result
