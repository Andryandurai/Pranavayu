from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.analytics.models import AnalysisRun
from apps.forecast.pipeline import evaluate_run


class Command(BaseCommand):
    help = "Recompute metrics from saved rolling-origin predictions without refitting."

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int)

    def handle(self, **options):
        runs = AnalysisRun.objects.filter(name="phase4", status="success")
        run = (
            runs.filter(pk=options["run"]).first()
            if options["run"]
            else runs.order_by("-pk").first()
        )
        if run is None:
            raise CommandError("No completed Phase 4 run")
        result = evaluate_run(run, settings.BASE_DIR / "data" / "results" / str(run.pk))
        self.stdout.write(
            f"Run {run.pk}: {len(result['evaluations'])} city/horizon/weather evaluations"
        )
