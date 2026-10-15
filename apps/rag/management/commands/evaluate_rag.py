import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.rag.evaluation import evaluate, evaluate_provider


class Command(BaseCommand):
    help = "Evaluate unchanged frozen questions with real CPU retrieval and available providers."

    def add_arguments(self, parser):
        parser.add_argument("--input", default="data/eval/rag_eval.jsonl")
        parser.add_argument("--output", default="data/results/rag-phase5")
        parser.add_argument(
            "--provider",
            choices=["ollama", "extractive", "openai", "anthropic"],
            help="Evaluate only this provider, without repeating retrieval experiments",
        )

    def handle(self, **options):
        if options["provider"]:
            result = evaluate_provider(
                Path(options["input"]), Path(options["output"]), options["provider"]
            )
        else:
            result = evaluate(Path(options["input"]), Path(options["output"]))
        self.stdout.write(
            json.dumps({key: result[key] for key in ("retrieval", "answers", "mlflow_run_id")})
        )
