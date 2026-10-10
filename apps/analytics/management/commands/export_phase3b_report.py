from django.core.management.base import BaseCommand

from apps.analytics.research_report import export_research_report


class Command(BaseCommand):
    help = "Export the Phase 3B paper and summary tables from a successful research run."

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True)

    def handle(self, *args, **options):
        self.stdout.write(export_research_report(options["run"]))
