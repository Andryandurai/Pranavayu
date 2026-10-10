"""Small prespecified models; every scaler and choice belongs to its origin."""

from datetime import timedelta

import numpy as np
import pandas as pd
import torch
from lightgbm import LGBMRegressor
from scipy.linalg import qr
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX
from torch import nn

from .data import FEATURES

SEED = 20261010
TREE_GRID = [
    {"num_leaves": 7, "max_depth": 3, "min_child_samples": 20},
    {"num_leaves": 15, "max_depth": 4, "min_child_samples": 30},
]


def lightgbm(config, alpha=None):
    return LGBMRegressor(
        **config,
        n_estimators=200,
        learning_rate=0.04,
        reg_lambda=1,
        random_state=SEED,
        n_jobs=1,
        verbosity=-1,
        deterministic=True,
        force_col_wise=True,
        objective="quantile" if alpha is not None else "regression",
        **({"alpha": alpha} if alpha is not None else {}),
    )


class Baseline:
    def __init__(self, name):
        self.name = name

    def fit(self, rows):
        self.month_means = rows.groupby(rows.target_date.dt.month).y.mean().to_dict()
        self.overall = float(rows.y.mean())
        return self

    def predict(self, rows):
        if self.name == "persistence":
            return rows.pm_t.to_numpy()
        if self.name == "mean7":
            return rows.pm_mean7.to_numpy()
        return rows.month.map(self.month_means).fillna(self.overall).to_numpy()


class TreeModel:
    def __init__(self, config, alpha=None):
        self.config = config
        self.model = lightgbm(config, alpha)

    def fit(self, rows):
        self.model.fit(rows[FEATURES], rows.y)
        return self

    def predict(self, rows):
        return np.maximum(0, self.model.predict(rows[FEATURES]))


class SarimaxModel:
    def __init__(self, order, horizon):
        self.order = order
        self.horizon = horizon

    def fit(self, rows):
        self.first = rows.index.min()
        self.imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        x = self.scaler.fit_transform(self.imputer.fit_transform(rows[FEATURES]))
        # Remove constant columns using training support, retaining future values.
        # Rolling mean3 is exactly a combination of the first three PM lags.
        # A training-only rank-revealing QR avoids unidentified exogenous terms.
        _, triangular, pivot = qr(x, mode="economic", pivoting=True)
        diagonal = np.abs(np.diag(triangular))
        rank = int((diagonal > max(float(diagonal.max()), 1) * 1e-10).sum())
        self.usable = np.zeros(x.shape[1], dtype=bool)
        self.usable[pivot[:rank]] = True
        calendar = pd.date_range(self.first, rows.index.max())
        expanded = rows.reindex(calendar)
        exog = self.transform(expanded)
        self.result = SARIMAX(
            expanded.y.to_numpy(),
            exog=exog,
            order=self.order,
            trend="c",
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False, maxiter=75)
        self.converged = bool(self.result.mle_retvals.get("converged"))
        return self

    def transform(self, rows):
        return self.scaler.transform(self.imputer.transform(rows[FEATURES]))[:, self.usable]

    def predict(self, rows, history=None):
        if history is None:
            raise ValueError("SARIMAX needs the issue-time observed history")
        predictions = []
        for issued in rows.index:
            calendar = pd.date_range(self.first, issued)
            past = history.reindex(calendar)
            # Direct-horizon labels at issue s become available on s+h, never earlier.
            y = past.y.to_numpy().copy()
            last_known_issue = pd.Timestamp(issued.date() - timedelta(days=self.horizon))
            y[calendar > last_known_issue] = np.nan
            result = self.result.apply(y, exog=self.transform(past), refit=False)
            predictions.append(
                float(
                    result.get_prediction(
                        start=len(calendar) - 1, end=len(calendar) - 1
                    ).predicted_mean[0]
                )
            )
        return np.maximum(0, np.asarray(predictions))


class LSTMModel:
    def fit(self, rows):
        import torch
        from torch import nn

        torch.set_num_threads(1)
        torch.manual_seed(SEED)
        torch.use_deterministic_algorithms(True)
        self.scaler = StandardScaler().fit(rows[FEATURES])
        self.mean = float(rows.y.mean())
        self.scale = max(float(rows.y.std()), 1)
        self.network = TinyLSTM(len(FEATURES))
        x, seq = self.tensors(rows)
        y = torch.tensor(((rows.y.to_numpy() - self.mean) / self.scale).astype("float32"))
        optimizer = torch.optim.Adam(self.network.parameters(), lr=0.01, weight_decay=0.01)
        self.network.train()
        self.losses = []
        for _ in range(80):
            optimizer.zero_grad()
            loss = nn.functional.mse_loss(self.network(seq, x), y)
            loss.backward()
            nn.utils.clip_grad_norm_(self.network.parameters(), 1)
            optimizer.step()
            self.losses.append(float(loss.detach()))
        self.network.eval()
        return self

    def tensors(self, rows):
        import torch

        x = torch.tensor(self.scaler.transform(rows[FEATURES]).astype("float32"))
        seq = rows[[f"seq_{i}" for i in range(6, -1, -1)]].to_numpy()
        seq = torch.tensor(((seq - self.mean) / self.scale).astype("float32")[:, :, None])
        return x, seq

    def predict(self, rows):
        import torch

        x, seq = self.tensors(rows)
        with torch.no_grad():
            return np.maximum(0, self.network(seq, x).numpy() * self.scale + self.mean)


# Top-level network class allows ordinary torch/joblib artifact restoration.
class TinyLSTM(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.lstm = nn.LSTM(1, 16, batch_first=True)
        self.head = nn.Sequential(
            nn.Dropout(0.2), nn.Linear(16 + n_features, 16), nn.ReLU(), nn.Linear(16, 1)
        )

    def forward(self, seq, x):
        encoded, _ = self.lstm(seq)
        return self.head(torch.cat([encoded[:, -1, :], x], dim=1)).squeeze(-1)


def predict(model, rows, history):
    return model.predict(rows, history) if isinstance(model, SarimaxModel) else model.predict(rows)


def choose_models(fit, tune, final_fit, history, horizon):
    def rmse(prediction):
        return float(np.sqrt(np.mean((prediction - tune.y.to_numpy()) ** 2)))

    scores = {}
    settings = {}
    settings["lstm"] = {"hidden_units": 16, "dropout": 0.2, "epochs": 80, "weight_decay": 0.01}
    for name in ("persistence", "mean7", "climatology"):
        scores[name] = rmse(Baseline(name).fit(fit).predict(tune))
    tree_scores = []
    for config in TREE_GRID:
        model = TreeModel(config).fit(fit)
        tree_scores.append(rmse(model.predict(tune)))
    config = TREE_GRID[int(np.argmin(tree_scores))]
    scores["lightgbm"] = min(tree_scores)
    settings["lightgbm"] = {"config": config, "candidate_rmse": tree_scores}
    sarimax_scores = []
    sarimax_errors = []
    orders = [(1, 0, 0), (1, 0, 1)]
    for order in orders:
        try:
            model = SarimaxModel(order, horizon).fit(fit)
            score = rmse(predict(model, tune, history))
            sarimax_scores.append(score if np.isfinite(score) else np.inf)
            sarimax_errors.append({"order": order, "converged": model.converged})
        except (ValueError, np.linalg.LinAlgError) as exc:
            sarimax_scores.append(np.inf)
            sarimax_errors.append({"order": order, "error": str(exc)})
    best = int(np.argmin(sarimax_scores))
    if np.isfinite(sarimax_scores[best]):
        scores["sarimax"] = sarimax_scores[best]
        settings["sarimax"] = {
            "order": orders[best],
            "candidates": sarimax_errors,
            "candidate_rmse": [v if np.isfinite(v) else None for v in sarimax_scores],
        }
    scores["lstm"] = rmse(LSTMModel().fit(fit).predict(tune))
    keep_lstm = scores["lstm"] < scores["lightgbm"]
    selectable = {k: v for k, v in scores.items() if k != "lstm" or keep_lstm}
    chosen = min(selectable, key=selectable.get)
    models = {
        name: Baseline(name).fit(final_fit) for name in ("persistence", "mean7", "climatology")
    }
    models["lightgbm"] = TreeModel(config).fit(final_fit)
    if "sarimax" in scores:
        models["sarimax"] = SarimaxModel(orders[best], horizon).fit(final_fit)
    # Retain predictions only as an explicitly rejected diagnostic if it lost tuning.
    models["lstm"] = LSTMModel().fit(final_fit)
    quantiles = {
        str(alpha): TreeModel(config, alpha).fit(final_fit) for alpha in (0.025, 0.1, 0.9, 0.975)
    }
    return (
        models,
        quantiles,
        {"chosen": chosen, "tuning_rmse": scores, "keep_lstm": keep_lstm, "settings": settings},
    )
