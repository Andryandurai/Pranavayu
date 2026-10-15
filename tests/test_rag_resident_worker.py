import numpy as np


def test_reranker_worker_reuses_the_model_and_keeps_scores_finite(monkeypatch):
    from apps.rag import reranker_worker as worker

    built = []

    class Model:
        def predict(self, pairs, **kwargs):
            assert kwargs["batch_size"] == 2
            return np.arange(len(pairs), dtype="float32") / 10

    def build():
        built.append(True)
        return Model()

    worker.load_reranker.cache_clear()
    monkeypatch.setattr(worker, "_build_model", build)
    try:
        assert worker.score_passages("question", ["a", "b"]) == worker.score_passages(
            "question", ["a", "b"]
        )
        assert len(built) == 1
    finally:
        worker.load_reranker.cache_clear()
