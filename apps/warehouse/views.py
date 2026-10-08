from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import City, Pollutant, Station
from .pagination import BoundedGeoJsonPagination
from .serializers import CitySerializer, PollutantSerializer, StationSerializer


class CityViewSet(ReadOnlyModelViewSet):
    queryset = City.objects.select_related("state").all()
    serializer_class = CitySerializer
    pagination_class = BoundedGeoJsonPagination
    search_fields = ["name", "slug", "state__name"]


class StationViewSet(ReadOnlyModelViewSet):
    queryset = Station.objects.select_related("source", "city").all()
    serializer_class = StationSerializer
    pagination_class = BoundedGeoJsonPagination
    search_fields = ["name", "external_id", "city__name"]


class PollutantViewSet(ReadOnlyModelViewSet):
    queryset = Pollutant.objects.all()
    serializer_class = PollutantSerializer
    search_fields = ["code", "display_name"]
