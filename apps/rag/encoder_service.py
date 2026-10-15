"""Embedding RPC; reranking is delegated to its dedicated resident Celery worker."""

import ctypes
import gc
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .encoders import EMBED_MODEL, EMBED_REVISION, RERANK_MODEL, RERANK_REVISION, model_cache

LOCK = threading.RLock()
ACTIVE = {"kind": None, "model": None}


def load_model(kind):
    import torch
    from sentence_transformers import CrossEncoder, SentenceTransformer

    if ACTIVE["kind"] == kind:
        return ACTIVE["model"]
    ACTIVE.update(kind=None, model=None)
    gc.collect()
    ctypes.CDLL("libc.so.6").malloc_trim(0)
    torch.set_num_threads(int(os.environ.get("RAG_CPU_THREADS", "4")))
    torch.manual_seed(20261010)
    precision = os.environ.get("RAG_MODEL_DTYPE", "float32")
    kwargs = {"dtype": precision}
    if kind == "embed":
        model = SentenceTransformer(
            EMBED_MODEL,
            revision=EMBED_REVISION,
            device="cpu",
            cache_folder=str(model_cache()),
            model_kwargs=kwargs,
            local_files_only=True,
        )
        model.max_seq_length = 1024
    else:
        model = CrossEncoder(
            RERANK_MODEL,
            revision=RERANK_REVISION,
            device="cpu",
            cache_folder=str(model_cache()),
            model_kwargs=kwargs,
            local_files_only=True,
            max_length=1024,
            activation_fn=torch.nn.Sigmoid(),
        )
    ACTIVE.update(kind=kind, model=model)
    print(json.dumps({"event": "cpu_model_loaded", "kind": kind, "dtype": precision}), flush=True)
    return model


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body):
        data = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/health":
            return self.respond(404, {"error": "Unknown endpoint"})
        self.respond(
            200,
            {
                "ok": True,
                "loaded": ACTIVE["kind"],
                "embedding_revision": EMBED_REVISION,
                "reranker_revision": RERANK_REVISION,
            },
        )

    def do_POST(self):
        if self.path not in {"/embed", "/rerank"}:
            return self.respond(404, {"error": "Unknown endpoint"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2_000_000:
                raise ValueError("Request body size is invalid")
            payload = json.loads(self.rfile.read(length))
            texts = payload["texts"]
            if (
                not isinstance(texts, list)
                or not 1 <= len(texts) <= 64
                or any(
                    not isinstance(text, str) or not text.strip() or len(text) > 30000
                    for text in texts
                )
            ):
                raise ValueError("Use 1–64 nonempty text strings up to 30000 characters")
            started = time.monotonic()
            with LOCK:
                if self.path == "/embed":
                    model = load_model("embed")
                    vector = model.encode(
                        texts,
                        batch_size=2,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                        convert_to_numpy=True,
                    )
                    result = {"vectors": vector.astype("float32").tolist()}
                    # Release the encoder between requests to preserve LLM headroom.
                    ACTIVE.update(kind=None, model=None)
                    del model
                    gc.collect()
                    ctypes.CDLL("libc.so.6").malloc_trim(0)
                else:
                    question = payload["question"]
                    if not isinstance(question, str) or not 1 <= len(question) <= 2000:
                        raise ValueError("Invalid question")
                    from .tasks import rerank_passages

                    scores = rerank_passages.apply_async(
                        args=[question, texts], queue="rag-rerank"
                    ).get(timeout=900)
                    result = {"scores": scores}
            result["seconds"] = time.monotonic() - started
            self.respond(200, result)
        except (ValueError, KeyError, TypeError) as exc:
            self.respond(400, {"error": str(exc)})
        except Exception as exc:
            print(json.dumps({"event": "inference_error", "error": repr(exc)}), flush=True)
            self.respond(503, {"error": "CPU inference unavailable; inspect model service logs"})


if __name__ == "__main__":
    import django

    django.setup()
    ThreadingHTTPServer(("0.0.0.0", 8090), Handler).serve_forever()
