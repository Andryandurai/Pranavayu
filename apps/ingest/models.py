from django.db import models
from django.db.models import F, Q

from apps.core.models import TimeStampedModel


class DataSource(TimeStampedModel):
    class AccessMethod(models.TextChoices):
        API = "api", "API"
        DOWNLOAD = "download", "Download"
        MANUAL = "manual", "Manual"

    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    url = models.URLField(max_length=500)
    licence = models.TextField(blank=True)
    description = models.TextField(blank=True)
    access_method = models.CharField(max_length=10, choices=AccessMethod, default=AccessMethod.API)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(access_method__in=["api", "download", "manual"]),
                name="source_access_method_valid",
            )
        ]

    def __str__(self):
        return self.name


class IngestionRun(TimeStampedModel):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial"
        SKIPPED = "skipped", "Skipped"

    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="runs")
    task_name = models.CharField(max_length=255)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status, default=Status.RUNNING)
    rows_fetched = models.PositiveBigIntegerField(default=0)
    rows_inserted = models.PositiveBigIntegerField(default=0)
    rows_flagged = models.PositiveBigIntegerField(default=0)
    error_message = models.TextField(blank=True)
    params = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at", "-pk"]
        indexes = [models.Index(fields=["source", "-started_at"], name="run_source_started_idx")]
        constraints = [
            models.CheckConstraint(
                condition=Q(finished_at__isnull=True) | Q(finished_at__gte=F("started_at")),
                name="run_finish_after_start",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["running", "success", "failed", "partial", "skipped"]),
                name="run_status_valid",
            ),
        ]

    def __str__(self):
        return f"{self.source}: {self.task_name} ({self.status})"


class RawAsset(TimeStampedModel):
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="assets")
    ingestion_run = models.ForeignKey(IngestionRun, on_delete=models.PROTECT, related_name="assets")
    path = models.CharField(max_length=1000)
    sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveBigIntegerField()
    download_url = models.URLField(max_length=2000, blank=True)
    licence = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["source_id", "path"]
        constraints = [
            models.UniqueConstraint(fields=["source", "sha256"], name="asset_source_digest_unique")
        ]

    def __str__(self):
        return self.path


class ObservationProvenance(models.Model):
    """Logical composite-key association; no unsupported FK into a hypertable."""

    kind = models.CharField(max_length=10, choices=[("weather", "Weather"), ("fire", "Fire")])
    record_id = models.UUIDField()
    observed_at = models.DateTimeField()
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT)
    ingestion_run = models.ForeignKey(
        IngestionRun, on_delete=models.PROTECT, related_name="observation_provenance"
    )
    asset = models.ForeignKey(RawAsset, on_delete=models.PROTECT, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-observed_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "record_id", "observed_at"], name="observation_provenance_unique"
            )
        ]

    def __str__(self):
        return f"{self.kind}: {self.record_id} @ {self.observed_at}"


class CityDistrictLink(TimeStampedModel):
    city = models.OneToOneField(
        "warehouse.City", on_delete=models.CASCADE, related_name="district_link"
    )
    district = models.ForeignKey(
        "warehouse.District", on_delete=models.PROTECT, related_name="city_links"
    )
    ingestion_run = models.ForeignKey(IngestionRun, on_delete=models.PROTECT)
    asset = models.ForeignKey(RawAsset, on_delete=models.PROTECT)

    class Meta:
        ordering = ["city__name"]

    def __str__(self):
        return f"{self.city}: {self.district}"


class BoundaryProvenance(TimeStampedModel):
    state = models.OneToOneField(
        "warehouse.State",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="boundary_provenance",
    )
    district = models.OneToOneField(
        "warehouse.District",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="boundary_provenance",
    )
    ingestion_run = models.ForeignKey(IngestionRun, on_delete=models.PROTECT)
    asset = models.ForeignKey(RawAsset, on_delete=models.PROTECT)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(state__isnull=False, district__isnull=True)
                    | Q(state__isnull=True, district__isnull=False)
                ),
                name="boundary_exactly_one_target",
            )
        ]

    def __str__(self):
        return f"Boundary {self.state_id or self.district_id}"
