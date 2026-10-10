import json

from django.core.management.base import BaseCommand

from apps.forecast.operations import issue_forecasts


class Command(BaseCommand):
    help = "Issue forecasts; replay latest archived day when fresh keyed OpenAQ is absent."

    def add_arguments(self, parser):
        parser.add_argument("--replay-date")
        parser.add_argument("--cities", nargs="+")

    def handle(self, **options):
        result = issue_forecasts(options["replay_date"], options["cities"])
        self.stdout.write(json.dumps(result, indent=2))
