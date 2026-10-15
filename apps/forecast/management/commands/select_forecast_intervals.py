import json

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.forecast.intervals import choose_interval_policy
from apps.forecast.models import ForecastEvaluation, ForecastModelVersion


class Command(BaseCommand):
    help = "Select interval families from an existing completed evaluation, without refitting"

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True)

    def handle(self, *args, **options):
        results = []
        with transaction.atomic():
            for evaluation in (
                ForecastEvaluation.objects.filter(
                    analysis_run_id=options["run"], analysis_run__status="success"
                )
                .select_related("city")
                .order_by("city__slug", "horizon")
            ):
                policy = choose_interval_policy(evaluation.result)
                policy["source_run"] = options["run"]
                versions = ForecastModelVersion.objects.filter(
                    analysis_run_id=options["run"], city=evaluation.city, horizon=evaluation.horizon
                )
                for version in versions:
                    adopted = (
                        version.interval_policy.get("adopted_at") or timezone.now().isoformat()
                    )
                    version.interval_policy = {**policy, "adopted_at": adopted}
                    version.save(update_fields=["interval_policy"])
                results.append(
                    {
                        "city": evaluation.city.slug,
                        "horizon": evaluation.horizon,
                        "versions": versions.count(),
                        "policy": policy,
                    }
                )
        if not results:
            raise ValueError("No successful archived-weather evaluation exists for that run")
        self.stdout.write(json.dumps(results))
