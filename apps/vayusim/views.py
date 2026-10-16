from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from apps.warehouse.models import City

from .models import Scenario, ScenarioRun
from .serializers import RunSerializer
from .service import run_response

EXAMPLE_HASHES = (
    "492de71df7303cc0f71468f5acc9f74fd53c6cf9a818bb0bc511e2fd1a0ed4c4",
    "bf7cda428744e8aab1e69de374b9838f9ce05742e41be720348fb3c2b79238ca",
    "c2807c34a76bc3e9a5d6e6bf9b1ed5fe2cb9e308ebd539e6dc033eb070808e84",
)


def retained_spec(run):
    fields = RunSerializer().fields
    return {
        "name": run.scenario.name,
        **{key: value for key, value in run.inputs.items() if key in fields},
    }


class SimulatorPage(TemplateView):
    template_name = "vayusim/cinematic.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cities"] = [
            {"slug": city.slug, "name": city.name, "location": [city.location.x, city.location.y]}
            for city in City.objects.order_by("name")
        ]
        examples = ScenarioRun.objects.select_related("scenario__city").filter(
            inputs_hash__in=EXAMPLE_HASHES
        )
        context["examples"] = [
            {"city": run.scenario.city.name, "inputs": retained_spec(run), **run_response(run)}
            for run in sorted(examples, key=lambda run: EXAMPLE_HASHES.index(run.inputs_hash))
        ]
        selected = None
        if self.request.GET.get("scenario"):
            scenario = get_object_or_404(Scenario, share_slug=self.request.GET["scenario"])
            selected = scenario.runs.select_related("scenario__city").order_by("-id").first()
        elif self.request.GET.get("run"):
            try:
                run_id = int(self.request.GET["run"])
            except ValueError:
                run_id = -1
            selected = get_object_or_404(
                ScenarioRun.objects.select_related("scenario__city"), pk=run_id
            )
        elif context["examples"]:
            selected = examples.order_by("id").first()
        context["initial_run"] = (
            {
                "city": selected.scenario.city.name,
                "inputs": retained_spec(selected),
                **run_response(selected),
            }
            if selected
            else None
        )
        return context
