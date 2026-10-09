"""Read-only research outputs, explicitly separated from official NCAP assessment."""

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AnalysisRun, CityMetric


def research_run(request):
    class Query(serializers.Serializer):
        run = serializers.IntegerField(min_value=1, required=False)

    query = Query(data=request.query_params)
    query.is_valid(raise_exception=True)
    rows = AnalysisRun.objects.filter(name="phase3b", status="success")
    if "run" in query.validated_data:
        rows = rows.filter(pk=query.validated_data["run"])
    run = rows.first()
    if run is None:
        raise NotFound("No completed Phase 3B research run")
    return run


class RQ2View(APIView):
    @extend_schema(parameters=[OpenApiParameter("run", type=int)], responses=OpenApiTypes.OBJECT)
    def get(self, request, slug):
        run = research_run(request)
        metric = CityMetric.objects.filter(run=run, city__slug=slug, name="rq2").first()
        if metric is None:
            raise NotFound("No research result for this city")
        return Response(dict(run=run.pk, city=slug, **metric.result))


class ResearchListView(APIView):
    metric_name = "comparisons"

    @extend_schema(parameters=[OpenApiParameter("run", type=int)], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        run = research_run(request)
        return Response(
            dict(
                run=run.pk,
                label="PM2.5 proxy for NCAP progress"
                if self.metric_name == "ncap"
                else "Weather-adjusted descriptive comparisons",
                is_official_compliance_result=False,
                official_compliance_assessment="not assessed",
                results=list(
                    CityMetric.objects.filter(run=run, name=self.metric_name)
                    .order_by("city__slug")
                    .values("city__slug", "result")
                ),
            )
        )


class NCAPView(ResearchListView):
    metric_name = "ncap"


class ComparisonsView(ResearchListView):
    metric_name = "comparisons"
