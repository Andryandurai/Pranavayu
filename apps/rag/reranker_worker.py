"""Pinned reranker retained in one dedicated Celery worker process."""

import os
from functools import lru_cache

import numpy as np

from .encoders import RERANK_MODEL, RERANK_REVISION, model_cache


def _build_model():
    import torch
    from sentence_transformers import CrossEncoder

    torch.set_num_threads(int(os.environ.get("RAG_CPU_THREADS", "4")))
    torch.manual_seed(20261010)
    return CrossEncoder(
        RERANK_MODEL,
        revision=RERANK_REVISION,
        device="cpu",
        cache_folder=str(model_cache()),
        local_files_only=True,
        max_length=1024,
        model_kwargs={"dtype": os.environ.get("RAG_MODEL_DTYPE", "float32")},
        activation_fn=torch.nn.Sigmoid(),
    )


@lru_cache(maxsize=1)
def load_reranker():
    return _build_model()


def score_passages(question, texts):
    values = load_reranker().predict(
        [(question, text) for text in texts],
        batch_size=2,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    scores = np.asarray(values, dtype="float32").reshape(-1)
    if len(scores) != len(texts) or not np.isfinite(scores).all():
        raise ValueError("Reranker returned invalid scores")
    return scores.tolist()
