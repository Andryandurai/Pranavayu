import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.rag.evaluation import build_evaluation


class Command(BaseCommand):
    help = "Freeze authored real-passage questions and actual database expectations once."

    def add_arguments(self, parser):
        parser.add_argument("--authored", default="data/eval/rag_questions.authored.json")
        parser.add_argument("--output", default="data/eval/rag_eval.jsonl")

    def handle(self, **options):
        self.stdout.write(
            json.dumps(build_evaluation(Path(options["authored"]), Path(options["output"])))
        )
