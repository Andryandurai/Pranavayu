from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class AnalysisRun(TimeStampedModel):
    name = models.CharField(max_length=200)
    parameters = models.JSONField(default=dict)
    data_start = models.DateField()
    data_end = models.DateField()
    git_commit = models.CharField(max_length=40, blank=True)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True)
    status = models.CharField(
        max_length=10,
        default="running",
        choices=[
            ("running", "Running"),
            ("success", "Success"),
            ("partial", "Partial"),
            ("failed", "Failed"),
        ],
    )
    error_message = models.TextField(blank=True)
    results = models.JSONField(default=dict)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(data_end__gte=models.F("data_start")), name="analysis_window_order"
            )
        ]


class StationEligibility(TimeStampedModel):
    station = models.OneToOneField(
        "warehouse.Station", on_delete=models.PROTECT, related_name="analysis_eligibility"
    )
    excluded_from_city = models.BooleanField(default=False)
    excluded_from_spatial = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    evidence = models.JSONField(default=dict)


class PopulationRaster(TimeStampedModel):
    asset = models.OneToOneField("ingest.RawAsset", on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    is_default = models.BooleanField(default=False)
    rationale = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"],
                condition=Q(is_default=True),
                name="one_default_population_raster",
            )
        ]


class ReadingFlagChange(models.Model):
    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE)
    station = models.ForeignKey("warehouse.Station", on_delete=models.PROTECT)
    pollutant = models.ForeignKey("warehouse.Pollutant", on_delete=models.PROTECT)
    observed_at = models.DateTimeField()
    old_flag = models.CharField(max_length=15)
    new_flag = models.CharField(max_length=15)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "station", "pollutant", "observed_at"],
                name="flag_change_run_record_unique",
            )
        ]


class CityHourly(models.Model):
    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE)
    city = models.ForeignKey("warehouse.City", on_delete=models.PROTECT)
    pollutant = models.ForeignKey("warehouse.Pollutant", on_delete=models.PROTECT)
    observed_at = models.DateTimeField()
    value = models.FloatField()
    station_count = models.PositiveIntegerField()
    weather = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "city", "pollutant", "observed_at"], name="city_hour_run_unique"
            )
        ]
        indexes = [
            models.Index(
                fields=["run", "city", "pollutant", "observed_at"], name="analysis_hour_lookup"
            )
        ]


class CityCoverage(models.Model):
    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE)
    city = models.ForeignKey("warehouse.City", on_delete=models.PROTECT)
    pollutant = models.ForeignKey("warehouse.Pollutant", on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    hours_present = models.PositiveIntegerField()
    hours_expected = models.PositiveIntegerField()
    valid_days = models.PositiveIntegerField()
    expected_days = models.PositiveIntegerField()
    valid_months = models.PositiveSmallIntegerField()
    eligible = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "city", "pollutant", "year"], name="coverage_run_city_poll_year"
            )
        ]


class CityMetric(models.Model):
    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE)
    city = models.ForeignKey("warehouse.City", on_delete=models.PROTECT)
    name = models.CharField(max_length=70)
    year = models.PositiveSmallIntegerField(null=True)
    result = models.JSONField(default=dict)

    class Meta:
        indexes = [models.Index(fields=["run", "city", "name"], name="analysis_metric_lookup")]


class CitySeries(models.Model):
    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE)
    city = models.ForeignKey("warehouse.City", on_delete=models.PROTECT)
    pollutant = models.ForeignKey("warehouse.Pollutant", on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=[("raw", "Raw"), ("deweathered", "Deweathered")])
    frequency = models.CharField(max_length=7, choices=[("daily", "Daily"), ("monthly", "Monthly")])
    date = models.DateField()
    value = models.FloatField(null=True)
    valid_count = models.PositiveIntegerField()
    expected_count = models.PositiveIntegerField()
    sampling_se = models.FloatField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "city", "pollutant", "kind", "frequency", "date"],
                name="series_run_city_kind_date",
            )
        ]
        indexes = [
            models.Index(
                fields=["run", "city", "kind", "frequency", "date"], name="analysis_series_lookup"
            )
        ]
