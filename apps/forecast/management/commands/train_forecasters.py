from django.core.management.base import BaseCommand

from apps.forecast.pipeline import train_forecasters


class Command(BaseCommand):
    help = "Run prespecified monthly rolling-origin forecasting experiments."

    def add_arguments(self, parser):
        parser.add_argument("--cities", nargs="+")

    def handle(self, **options):
        run = train_forecasters(options["cities"])
        self.stdout.write(f"AnalysisRun {run.pk}: {run.status}")
