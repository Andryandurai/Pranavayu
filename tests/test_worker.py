import uuid

import pytest
from celery.contrib.testing.worker import start_worker

from apps.core.tasks import ping
from apps.ingest.models import IngestionRun
from enviroinsights.celery import app
from tests.factories import DataSourceFactory


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
def test_real_worker_executes_task_and_persists_success():
    source = DataSourceFactory()
    queue = f"phase1-test-{uuid.uuid4().hex}"
    assert not app.conf.task_always_eager
    # A real Celery worker consumes Redis messages against the isolated test DB.
    # A dedicated queue prevents the Compose worker consuming this test's task.
    with start_worker(
        app, pool="solo", queues=[queue], perform_ping_check=False, shutdown_timeout=30
    ):
        result = ping.apply_async(kwargs={"source_slug": source.slug}, queue=queue)
        payload = result.get(timeout=30)
    run = IngestionRun.objects.get(pk=payload["run_id"])
    assert run.status == "success"
    assert run.task_name == "core.tasks.ping"
    assert run.finished_at >= run.started_at
    assert run.rows_fetched == run.rows_inserted == run.rows_flagged == 0
