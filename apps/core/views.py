from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .health import infrastructure_health
from .serializers import HealthSerializer


class HealthView(APIView):
    authentication_classes = []

    @extend_schema(responses={200: HealthSerializer, 503: HealthSerializer}, tags=["health"])
    def get(self, request):
        report = infrastructure_health()
        return Response(report, status=200 if report["ok"] else 503)
