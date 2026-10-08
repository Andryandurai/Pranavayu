import hashlib
import json
import subprocess
from contextlib import contextmanager
from datetime import date
from importlib.metadata import version
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import AnalysisRun


def code_metadata():
    try:
        commit = subprocess.check_output(
            ["git", "-c", f"safe.directory={settings.BASE_DIR}", "rev-parse", "HEAD"],
            cwd=settings.BASE_DIR,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = ""
    digest = hashlib.sha256()
    for root in ["apps", "enviroinsights", "requirements"]:
        for path in sorted((settings.BASE_DIR / root).rglob("*")):
            if path.suffix in {".py", ".in", ".txt"}:
                digest.update(str(path.relative_to(settings.BASE_DIR)).encode())
                digest.update(path.read_bytes())
    packages = ["Django", "numpy", "pandas", "scikit-learn", "scipy", "matplotlib"]
    return commit, {
        "git_state": "versioned" if commit else "no Git repository; commit unavailable",
        "code_sha256": digest.hexdigest(),
        "versions": {p: version(p) for p in packages},
    }


@contextmanager
def analysis_run(name="phase3a", start="2015-01-01", end="2026-10-07", **parameters):
    commit, provenance = code_metadata()
    run = AnalysisRun.objects.create(
        name=name,
        parameters={**parameters, **provenance},
        data_start=date.fromisoformat(start),
        data_end=date.fromisoformat(end),
        git_commit=commit,
        started_at=timezone.now(),
    )
    output = Path(settings.BASE_DIR) / "data" / "results" / str(run.pk)
    output.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"event": "analysis_started", "run": run.pk, "name": name}), flush=True)
    try:
        yield run, output
    except BaseException as exc:
        run.status = "failed"
        run.error_message = f"{type(exc).__name__}: {exc}"
        raise
    else:
        run.status = "success"
    finally:
        run.finished_at = timezone.now()
        run.save()
        files = []
        for path in sorted(output.rglob("*")):
            if path.is_file() and path.name != "manifest.json":
                with path.open("rb") as handle:
                    digest = hashlib.file_digest(handle, "sha256").hexdigest()
                files.append(
                    {
                        "path": path.relative_to(output).as_posix(),
                        "bytes": path.stat().st_size,
                        "sha256": digest,
                    }
                )
        manifest = {
            "run": run.pk,
            "name": run.name,
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat(),
            "data_window": [str(run.data_start), str(run.data_end)],
            "git_commit": run.git_commit,
            "parameters": run.parameters,
            "files": files,
            "error_message": run.error_message,
        }
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(
            json.dumps({"event": "analysis_finished", "run": run.pk, "status": run.status}),
            flush=True,
        )
