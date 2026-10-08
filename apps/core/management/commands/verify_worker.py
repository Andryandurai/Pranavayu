from django.core.management.base import BaseCommand, CommandError

from apps.core.tasks import ping
from apps.ingest.models import IngestionRun


class Command(BaseCommand):
    help = "Dispatch a real broker task and verify the worker's persisted success row."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=float, default=30)

    def handle(self, *args, **options):
        try:
            result = ping.delay().get(timeout=options["timeout"])
            run = IngestionRun.objects.get(pk=result["run_id"], status=IngestionRun.Status.SUCCESS)
        except Exception as exc:
            raise CommandError(
                "Worker verification failed; check seed, migrations and worker logs"
            ) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Worker executed core.tasks.ping: run={run.pk}, status={run.status}, rows=0"
            )
        )
