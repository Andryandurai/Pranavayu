import hashlib
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.analytics.lifecycle import code_metadata
from apps.analytics.models import AnalysisRun
from apps.forecast.reporting import export_report


class Command(BaseCommand):
    help = "Export actual saved Phase 4 metrics/figures and refresh this run's manifest."

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True)

    def handle(self, **options):
        run = AnalysisRun.objects.filter(pk=options["run"], name="phase4", status="success").first()
        if run is None:
            raise CommandError("Specify a completed Phase 4 run")
        output = settings.BASE_DIR / "data" / "results" / str(run.pk)
        export_report(run, output)
        commit, metadata = code_metadata()
        run.parameters["report_export"] = {
            "at": timezone.now().isoformat(),
            "git_commit": commit,
            **metadata,
        }
        run.save(update_fields=["parameters", "updated_at"])
        manifest = json.loads((output / "manifest.json").read_text())
        manifest["parameters"] = run.parameters
        manifest["files"] = [
            {
                "path": p.relative_to(output).as_posix(),
                "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            for p in sorted(output.rglob("*"))
            if p.is_file() and p.name != "manifest.json"
        ]
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.stdout.write(
            f"Exported docs/results/PHASE4.md and {len(manifest['files'])} hashed artifacts"
        )
