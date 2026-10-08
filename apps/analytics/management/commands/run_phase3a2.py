from django.core.management.base import BaseCommand

from apps.analytics.diagnostic_pipeline import prepare_data
from apps.analytics.revised_deweather import run_revised


class Command(BaseCommand):
    help = "Run Phase 3A2 diagnostics, comparisons and pooled-weather normalisation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-run", type=int, help="Reuse an already completed native-bin diagnostic data run"
        )

    def handle(self, *args, **options):
        data_run = options["data_run"] or prepare_data()
        run = run_revised(data_run)
        self.stdout.write(f"Phase 3A2 model run completed: {run}")
