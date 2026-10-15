from django.db import models
from django.db.models import F, Q

from apps.core.models import TimeStampedModel


class ForecastWeather(TimeStampedModel):
    """Daily weather from a documented lead archive, distinct from observations."""

    city = models.ForeignKey("warehouse.City", on_delete=models.PROTECT)
    issued_for_date = models.DateField()
    target_date = models.DateField()
    horizon = models.PositiveSmallIntegerField()
    available_by = models.DateTimeField()
    lead_days = models.PositiveSmallIntegerField()
    source = models.ForeignKey("ingest.DataSource", on_delete=models.PROTECT)
    ingestion_run = models.ForeignKey("ingest.IngestionRun", on_delete=models.PROTECT)
    asset = models.ForeignKey("ingest.RawAsset", on_delete=models.PROTECT)
    features = models.JSONField(default=dict)
    provenance = models.JSONField(default=dict)
    hours = models.PositiveSmallIntegerField()
    mode = models.CharField(max_length=10, choices=[("archive", "Archive"), ("live", "Live")])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["city", "issued_for_date", "horizon", "mode"],
                name="forecast_weather_issue_unique",
            ),
            models.CheckConstraint(
                condition=Q(horizon__range=(1, 3)), name="weather_horizon_valid"
            ),
        ]
        indexes = [models.Index(fields=["city", "issued_for_date", "horizon"])]


class ForecastModelVersion(TimeStampedModel):
    city = models.ForeignKey("warehouse.City", on_delete=models.PROTECT)
    horizon = models.PositiveSmallIntegerField()
    algorithm = models.CharField(max_length=40)
    mlflow_run_id = models.CharField(max_length=64)
    registry_name = models.CharField(max_length=100)
    registry_version = models.CharField(max_length=20)
    training_start = models.DateField()
    training_end = models.DateField()
    available_from = models.DateField()
    validation_metrics = models.JSONField(default=dict)
    interval_policy = models.JSONField(default=dict)
    artifact_path = models.CharField(max_length=1000)
    analysis_run = models.ForeignKey("analytics.AnalysisRun", on_delete=models.PROTECT)
    cohort = models.CharField(max_length=30)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(horizon__range=(1, 3)), name="model_horizon_valid"),
            models.CheckConstraint(
                condition=Q(training_end__gte=F("training_start")), name="model_window_valid"
            ),
        ]
        indexes = [models.Index(fields=["city", "horizon", "available_from"])]


class Forecast(TimeStampedModel):
    city = models.ForeignKey("warehouse.City", on_delete=models.PROTECT)
    issued_for_date = models.DateField()
    target_date = models.DateField()
    horizon = models.PositiveSmallIntegerField()
    point = models.FloatField()
    lower80 = models.FloatField()
    upper80 = models.FloatField()
    lower95 = models.FloatField()
    upper95 = models.FloatField()
    aqi_category = models.CharField(max_length=20)
    mode = models.CharField(max_length=10, choices=[("live", "Live"), ("replay", "Replay")])
    model_version = models.ForeignKey(ForecastModelVersion, on_delete=models.PROTECT)
    top_drivers = models.JSONField(default=list)
    feature_provenance = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["city", "issued_for_date", "horizon", "mode", "model_version"],
                name="forecast_version_issue_unique",
            ),
            models.CheckConstraint(
                condition=Q(horizon__range=(1, 3)), name="forecast_horizon_valid"
            ),
            models.CheckConstraint(condition=Q(point__gte=0), name="forecast_point_nonnegative"),
            models.CheckConstraint(
                condition=Q(
                    lower95__lte=F("lower80"), lower80__lte=F("upper80"), upper80__lte=F("upper95")
                ),
                name="forecast_intervals_ordered",
            ),
        ]
        indexes = [models.Index(fields=["city", "-issued_for_date", "horizon"])]


class ForecastEvaluation(TimeStampedModel):
    analysis_run = models.ForeignKey("analytics.AnalysisRun", on_delete=models.PROTECT)
    city = models.ForeignKey("warehouse.City", on_delete=models.PROTECT)
    horizon = models.PositiveSmallIntegerField()
    result = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis_run", "city", "horizon"], name="forecast_evaluation_unique"
            )
        ]
