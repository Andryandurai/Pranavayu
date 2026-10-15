from datetime import datetime

import mlflow
import numpy as np
import pandas as pd
from django.conf import settings
from mlflow import MlflowClient
from mlflow.entities import Metric, Param


def tracking_client():
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    client = MlflowClient()
    name = "EnviroInsights-India Phase 4"
    experiment = client.get_experiment_by_name(name)
    experiment_id = experiment.experiment_id if experiment else client.create_experiment(name)
    return client, experiment_id


def log_experiment(client, experiment_id, tags, parameters, metrics, artifact=None):
    run = client.create_run(experiment_id, tags={k: str(v) for k, v in tags.items()})
    run_id = run.info.run_id
    client.log_batch(
        run_id,
        metrics=[
            Metric(k, float(v), int(datetime.now().timestamp() * 1000), 0)
            for k, v in metrics.items()
            if isinstance(v, (int, float)) and np.isfinite(v)
        ],
        params=[Param(k, str(v)[:5900]) for k, v in parameters.items()],
    )
    if artifact:
        client.log_artifact(run_id, str(artifact))
    client.set_terminated(run_id, "FINISHED")
    return run_id


class RegisteredForecaster(mlflow.pyfunc.PythonModel):
    """Registry prediction adapter; stateful SARIMAX is served by Django commands."""

    def __init__(self, model):
        self.model = model

    def predict(self, context, model_input: pd.DataFrame, params=None) -> np.ndarray:
        from .estimators import SarimaxModel

        if isinstance(self.model, SarimaxModel):
            raise ValueError("Use issue_forecasts for SARIMAX with audited issue-time history")
        rows = pd.DataFrame(model_input)
        if "target_date" in rows:
            rows["target_date"] = pd.to_datetime(rows.target_date)
        return self.model.predict(rows)


def register_model(model, city, horizon, run_id):
    name = f"pm25-{city}-h{horizon}"
    with mlflow.start_run(run_id=run_id):
        info = mlflow.pyfunc.log_model(
            name="forecaster",
            python_model=RegisteredForecaster(model),
            pip_requirements=[
                "lightgbm==4.7.0",
                "torch==2.14.1+cpu",
                "statsmodels==0.15.0",
                "mlflow==3.17.0",
            ],
            registered_model_name=name,
        )
    client = MlflowClient()
    versions = client.search_model_versions(f"name='{name}'")
    matched = [v for v in versions if v.run_id == run_id]
    version = max(matched, key=lambda v: int(v.version))
    return name, str(version.version), info.model_uri
