from django.core.management.base import BaseCommand

from apps.analytics.aggregation import build_tables
from apps.analytics.audit import exclude_unverified
from apps.analytics.lifecycle import analysis_run


class Command(BaseCommand):
    help = "Refresh city means, weather joins, coverage and daily/monthly means."

    def add_arguments(self, parser):
        parser.add_argument("--start", default="2015-01-01")
        parser.add_argument("--end", default="2026-10-07")

    def handle(self, *args, **options):
        with analysis_run(name="analysis-tables", start=options["start"], end=options["end"]) as (
            run,
            output,
        ):
            exclude_unverified()
            results = build_tables(run, output)
            run.results = {"hourly_rows": results["hourly_rows"]}
        self.stdout.write(f"Analysis tables: run={run.pk} hourly_rows={results['hourly_rows']}")
