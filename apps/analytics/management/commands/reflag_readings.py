import json

from django.core.management.base import BaseCommand

from apps.analytics.audit import reflag
from apps.analytics.lifecycle import analysis_run


class Command(BaseCommand):
    help = (
        "Recompute quality flags in place, preserving every measured/raw value and ingestion link."
    )

    def handle(self, *args, **options):
        with analysis_run(name="quality-audit") as (run, output):
            result = reflag(run, output)
            run.results = {
                "changed_rows": result["changed_rows"],
                "before": result["before"]["totals"],
                "after": result["after"]["totals"],
            }
        self.stdout.write(json.dumps({"run": run.pk, **run.results}))
