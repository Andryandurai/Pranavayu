from django.core.management.base import BaseCommand

from apps.analytics.diagnostic_report import export_report


class Command(BaseCommand):
    help = "Export measured Phase 3A2 results/figures from a completed run; do not refit models."

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True)

    def handle(self, *args, **options):
        self.stdout.write(str(export_report(options["run"])))
