import json

from django.core.management.base import BaseCommand

from apps.rag.encoders import (
    EMBED_MODEL,
    EMBED_REVISION,
    RERANK_MODEL,
    RERANK_REVISION,
    model_cache,
)


class Command(BaseCommand):
    help = "Resume downloading the pinned CPU encoder/reranker weights into the D: cache."

    def handle(self, **options):
        from huggingface_hub import snapshot_download

        for model, revision in [(EMBED_MODEL, EMBED_REVISION), (RERANK_MODEL, RERANK_REVISION)]:
            path = snapshot_download(
                model,
                revision=revision,
                cache_dir=str(model_cache()),
                max_workers=2,
                allow_patterns=[
                    "*.json",
                    "*.txt",
                    "*.model",
                    "pytorch_model.bin",
                    "model.safetensors",
                ],
            )
            self.stdout.write(json.dumps({"model": model, "revision": revision, "path": path}))
