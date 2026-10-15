"""Repeat retrieval diagnostics without changing frozen questions or labels."""

import hashlib
import json
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.rag.encoders import RERANK_REVISION, CPUModels, computation_revision
from apps.rag.evaluation import load_evaluation
from apps.rag.library import atomic_json
from apps.rag.models import Document
from apps.rag.retrieval import retrieve


def scored_subset(candidates, scores, gold, count):
    """Hold pair scores constant while varying the RRF candidate cutoff."""
    selected = sorted(
        zip(candidates[:count], scores[:count], strict=True),
        key=lambda row: (-row[1], row[0]["chunk_id"]),
    )
    ids = [row[0]["chunk_id"] for row in selected]
    return {
        "ids": ids,
        "recall_at_5": len(gold.intersection(ids[:5])) / len(gold),
        "recall_at_10": len(gold.intersection(ids[:10])) / len(gold),
        "mrr": next((1 / i for i, pk in enumerate(ids, 1) if pk in gold), 0),
    }


class Command(BaseCommand):
    help = "Audit K=24/32/40 with shared fresh scores; time uncached cold/warm RPC separately."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="data/results/phase6a-audit")
        parser.add_argument("--timing-k", type=int, choices=[24, 32, 40])

    def handle(self, **options):
        folder = Path(settings.BASE_DIR) / options["output"]
        folder.mkdir(parents=True, exist_ok=True)
        records, freeze = load_evaluation(Path(settings.BASE_DIR) / "data/eval/rag_eval.jsonl")
        records = [r for r in records if r["type"] == "literature"]
        models = CPUModels()
        identity = {
            "evaluation_sha256": freeze["sha256"],
            "computation_revision": computation_revision(RERANK_REVISION),
            "batch_size": 2,
            "seed": 20261010,
            "cpu_threads": 4,
            "corpus": list(
                Document.objects.filter(status="ready").order_by("pk").values("pk", "sha256")
            ),
        }
        if count := options["timing_k"]:
            candidates = retrieve(records[0]["question"], mode="hybrid", limit=count)
            rows = []
            for state in ("cold", "warm"):
                self.stdout.write(
                    json.dumps({"event": "timing_started", "k": count, "state": state})
                )
                self.stdout.flush()
                started = time.perf_counter()
                result = models.request(
                    "/rerank",
                    {"question": records[0]["question"], "texts": [r["text"] for r in candidates]},
                )
                rows.append(
                    {
                        "state": state,
                        "seconds": time.perf_counter() - started,
                        "server_seconds": result["seconds"],
                        "scores": result["scores"],
                    }
                )
                self.stdout.write(json.dumps({k: v for k, v in rows[-1].items() if k != "scores"}))
                self.stdout.flush()
            atomic_json(
                folder / f"reranker-timing-{count}.json",
                {
                    "identity": identity,
                    "k": count,
                    "query_id": records[0]["id"],
                    "candidate_ids": [r["chunk_id"] for r in candidates],
                    "rows": rows,
                    "note": (
                        "Worker restarted immediately before this command. Cold model load, "
                        "not cold OS disk cache. Both RPCs bypass pair score cache; "
                        "query embedding is cached."
                    ),
                },
            )
            return

        state_path = folder / "reranker-state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text())
            if state["identity"] != identity:
                raise CommandError("Cannot resume across changed corpus/evaluation/configuration")
        else:
            state = {"identity": identity, "rows": []}
            atomic_json(state_path, state)
        completed = {r["id"] for r in state["rows"]}
        for record in records:
            if record["id"] in completed:
                continue
            started = time.perf_counter()
            candidates = retrieve(record["question"], mode="hybrid", limit=40)
            result = models.request(
                "/rerank",
                {"question": record["question"], "texts": [r["text"] for r in candidates]},
            )
            scores = result["scores"]
            gold = set(record["gold_chunk_ids"])
            row = {
                "id": record["id"],
                "gold": sorted(gold),
                "fused_ids": [r["chunk_id"] for r in candidates],
                "text_sha256": [hashlib.sha256(r["text"].encode()).hexdigest() for r in candidates],
                "scores": scores,
                "seconds": time.perf_counter() - started,
                "server_seconds": result["seconds"],
                "k": {str(k): scored_subset(candidates, scores, gold, k) for k in (24, 32, 40)},
            }
            state["rows"].append(row)
            atomic_json(state_path, state)
            self.stdout.write(
                json.dumps(
                    {
                        "event": "fresh_query_complete",
                        "id": record["id"],
                        "seconds": row["seconds"],
                        "done": len(state["rows"]),
                        "total": len(records),
                    }
                )
            )
            self.stdout.flush()
        metrics = {
            str(k): {
                metric: sum(r["k"][str(k)][metric] for r in state["rows"]) / len(records)
                for metric in ("recall_at_5", "recall_at_10", "mrr")
            }
            for k in (24, 32, 40)
        }
        result = {
            "identity": identity,
            "questions": len(records),
            "metrics": metrics,
            "fresh_40_mean_seconds": sum(r["seconds"] for r in state["rows"]) / len(records),
            "note": (
                "Every query freshly scored all 40 once without pair cache. K subsets share "
                "these fixed scores to isolate candidate competition; MRR is through K."
            ),
        }
        atomic_json(folder / "reranker-metrics.json", result)
        self.stdout.write(json.dumps(result))
