"""CPU model client and deterministic content/revision caches."""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import requests
from django.conf import settings

EMBED_MODEL = "BAAI/bge-m3"
EMBED_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
RERANK_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"


def computation_revision(revision):
    precision = os.environ.get("RAG_MODEL_DTYPE", "float32")
    return f"{revision}:{precision}:maxlen1024"


def model_cache():
    return Path(os.environ.get("HF_HOME", settings.BASE_DIR / "data/models/huggingface")) / "hub"


def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        EMBED_MODEL,
        revision=EMBED_REVISION,
        cache_dir=str(model_cache()),
        local_files_only=True,
    )


def cache_path(kind, value, revision):
    digest = hashlib.sha256(json.dumps([revision, value], ensure_ascii=False).encode()).hexdigest()
    folder = settings.BASE_DIR / "data" / "models" / "computations" / kind
    folder.mkdir(parents=True, exist_ok=True)
    return folder / (digest + ".json")


def save_cache(path, value):
    # Unique temporary names allow concurrent identical queries without corrupting bytes.
    import uuid

    temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


class CPUModels:
    def request(self, endpoint, payload):
        url = os.environ.get("RAG_MODELS_URL", "http://rag-models:8090")
        response = requests.post(url + endpoint, json=payload, timeout=(5, 900))
        response.raise_for_status()
        return response.json()

    def embed(self, texts):
        paths = [
            cache_path("passages", text, computation_revision(EMBED_REVISION)) for text in texts
        ]
        result = [json.loads(path.read_text()) if path.exists() else None for path in paths]
        missing = [i for i, vector in enumerate(result) if vector is None]
        if missing:
            groups = {}
            for i in missing:
                groups.setdefault(str(paths[i]), []).append(i)
            calculated = self.request(
                "/embed", {"texts": [texts[indices[0]] for indices in groups.values()]}
            )["vectors"]
            for indices, vector in zip(groups.values(), calculated, strict=True):
                for i in indices:
                    result[i] = vector
        array = np.asarray(result, dtype=float)
        if array.shape != (len(texts), 1024) or not np.isfinite(array).all():
            raise ValueError("Encoder must return finite 1024-dimensional vectors")
        for i in missing:
            save_cache(paths[i], result[i])
        return array.tolist()

    def embed_query(self, question):
        path = cache_path("query", question, computation_revision(EMBED_REVISION))
        if path.exists():
            return json.loads(path.read_text())
        vector = self.embed([question])[0]
        save_cache(path, vector)
        return vector

    def rerank(self, question, texts):
        paths = [
            cache_path("pairs", [question, text], computation_revision(RERANK_REVISION))
            for text in texts
        ]
        scores = [json.loads(path.read_text()) if path.exists() else None for path in paths]
        missing = [i for i, score in enumerate(scores) if score is None]
        if missing:
            calculated = self.request(
                "/rerank", {"question": question, "texts": [texts[i] for i in missing]}
            )["scores"]
            if len(calculated) != len(missing) or not np.isfinite(calculated).all():
                raise ValueError("Reranker returned invalid scores")
            for i, score in zip(missing, calculated, strict=True):
                scores[i] = float(score)
                save_cache(paths[i], scores[i])
        return scores


def get_models():
    return CPUModels()
