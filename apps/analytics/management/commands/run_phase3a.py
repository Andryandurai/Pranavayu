from django.core.management.base import BaseCommand

from apps.analytics.pipeline import run_phase3a


class Command(BaseCommand):
    help = "Audit/reflag, build analysis tables, describe, normalise weather, export/report."

    def add_arguments(self, parser):
        parser.add_argument("--start", default="2015-01-01")
        parser.add_argument("--end", default="2026-10-07")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--n-samples", type=int, default=300)
        parser.add_argument("--n-trees", type=int, default=100)
        parser.add_argument(
            "--enqueue", action="store_true", help="Run through the real Celery worker."
        )

    def handle(self, *args, **options):
        parameters = {k: options[k] for k in ["start", "end", "seed", "n_samples", "n_trees"]}
        if options["enqueue"]:
            from apps.analytics.tasks import run_phase3a_task

            result = run_phase3a_task.delay(**parameters)
            self.stdout.write(f"Queued Phase 3A task {result.id}; waiting for completion")
            run = result.get(timeout=15000)
        else:
            run = run_phase3a(**parameters)
        self.stdout.write(f"Phase 3A completed: AnalysisRun {run}")
