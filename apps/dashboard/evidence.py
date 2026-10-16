"""Read-only, explicitly allowed project evidence. No warehouse aggregation on page load."""

import json
from pathlib import Path

from django.http import FileResponse, Http404
from django.shortcuts import render

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "snapshot": "docs/results/PHASE7_DATA.json",
    "checks": "docs/results/PHASE7_CHECKS.json",
    "phase3b": "docs/results/PHASE3B.md",
    "phase4": "docs/results/PHASE4.md",
    "phase5": "docs/results/PHASE5.md",
    "phase6a": "docs/results/PHASE6A.md",
    "phase6b": "docs/results/PHASE6B.md",
    "phase7": "docs/results/PHASE7.md",
    "writeup": "docs/results/WRITEUP.md",
    "phase4-json": "data/results/21/phase4_results.json",
    "interval-policy": "data/results/vayusim/verification/forecast-interval-policy.json",
    "paired-network": "data/results/19/paired_network.csv",
    "network-annual": "data/results/19/network_annual.csv",
    "extractive": "data/results/rag-phase5/metrics.json",
    "ollama": "data/results/rag-ollama-phase6a/metrics.json",
    "physics": "docs/results/PHASE6A_INDEPENDENT_METRICS.json",
    "examples": "docs/results/PHASE6B_METRICS.json",
}


def evidence_file(request, key):
    relative = SOURCES.get(key)
    if not relative:
        raise Http404("Unknown evidence identifier")
    path = ROOT / relative
    if not path.is_file():
        raise Http404("Original evidence file is unavailable in this checkout")
    response = FileResponse(path.open("rb"), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'inline; filename="{path.name}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


def evidence_dashboard(request):
    try:
        data = json.loads((ROOT / SOURCES["snapshot"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return render(
            request, "dashboard/evidence.html", {"snapshot_unavailable": True}, status=503
        )
    return render(request, "dashboard/evidence.html", {"record": data})
