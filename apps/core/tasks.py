from celery import shared_task
from django.utils import timezone

from apps.ingest.models import DataSource, IngestionRun


@shared_task(name="core.tasks.ping")
def ping(source_slug="cpcb-ccr"):
    """Record a zero-row infrastructure probe against an existing reference source."""
    source = DataSource.objects.get(slug=source_slug)
    now = timezone.now()
    run = IngestionRun.objects.create(
        source=source,
        task_name="core.tasks.ping",
        started_at=now,
        finished_at=now,
        status=IngestionRun.Status.SUCCESS,
        params={"purpose": "infrastructure_probe"},
    )
    return {"run_id": run.pk, "status": run.status}
