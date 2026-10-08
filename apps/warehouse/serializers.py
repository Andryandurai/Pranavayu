from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import City, Pollutant, Station


class CitySerializer(GeoFeatureModelSerializer):
    class Meta:
        model = City
        geo_field = "location"
        fields = ["id", "name", "slug", "state", "is_ncap_nonattainment", "population", "location"]


class StationSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Station
        geo_field = "location"
        fields = [
            "id",
            "external_id",
            "source",
            "name",
            "city",
            "location",
            "operator",
            "is_active",
            "first_seen",
            "last_seen",
        ]


class PollutantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pollutant
        fields = [
            "id",
            "code",
            "display_name",
            "unit",
            "who_guideline_value",
            "who_averaging_hours",
            "naaqs_24h_value",
        ]
