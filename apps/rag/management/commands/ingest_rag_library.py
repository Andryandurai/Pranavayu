import json

from django.core.management.base import BaseCommand

from apps.rag.ingestion import ingest
from apps.rag.models import Document


class Command(BaseCommand):
    help = "Parse/embed downloaded real documents, resuming pending batches after interruption."

    def add_arguments(self, parser):
        parser.add_argument("--ids", nargs="+", type=int)
        parser.add_argument("--parse-only", action="store_true")
        parser.add_argument("--enqueue", action="store_true")

    def handle(self, **options):
        documents = Document.objects.order_by("pk")
        if options["ids"]:
            documents = documents.filter(pk__in=options["ids"])
        for document in documents:
            try:
                if options["enqueue"]:
                    from apps.rag.tasks import ingest_document

                    task = ingest_document.delay(document.pk)
                    result = {"document": document.pk, "task": task.id}
                else:
                    result = ingest(document.pk, embed=not options["parse_only"])
            except Exception as exc:
                result = {"document": document.pk, "status": "failed", "error": str(exc)}
            self.stdout.write(json.dumps(result))
