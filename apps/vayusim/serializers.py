import math

from rest_framework import serializers

from apps.warehouse.models import City


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError(
                {"non_field_errors": "Use an object containing only documented fields"}
            )
        for name, value in data.items():
            if isinstance(self.fields[name], (serializers.FloatField, serializers.IntegerField)):
                if isinstance(value, bool):
                    raise serializers.ValidationError({name: "Use a finite number, not a boolean"})
                try:
                    if not math.isfinite(float(value)):
                        raise ValueError
                except (ValueError, TypeError):
                    raise serializers.ValidationError({name: "Use a finite number"}) from None
        return super().to_internal_value(data)


class Coordinates(serializers.ListField):
    def __init__(self, **kwargs):
        super().__init__(child=serializers.FloatField(), min_length=2, max_length=2, **kwargs)

    def to_internal_value(self, data):
        if not isinstance(data, (list, tuple)) or any(isinstance(x, bool) for x in data):
            raise serializers.ValidationError("Use [longitude, latitude]")
        value = super().to_internal_value(data)
        if (
            not all(math.isfinite(x) for x in value)
            or not -180 <= value[0] <= 180
            or not -85 <= value[1] <= 85
        ):
            raise serializers.ValidationError("Coordinates outside geographic range")
        return value


class SourceSerializer(StrictSerializer):
    type = serializers.ChoiceField(choices=["point", "area", "line"])
    location = Coordinates()
    emission_gs = serializers.FloatField(min_value=0, max_value=100000)
    height_m = serializers.FloatField(min_value=0, max_value=1000)
    diameter_m = serializers.FloatField(min_value=0, max_value=100)
    exit_velocity_ms = serializers.FloatField(min_value=0, max_value=200)
    exit_temperature_k = serializers.FloatField(min_value=150, max_value=2000)
    width_m = serializers.FloatField(min_value=1, max_value=10000, required=False)
    length_m = serializers.FloatField(min_value=1, max_value=10000, required=False)
    end_location = Coordinates(required=False)
    subdivisions = serializers.IntegerField(min_value=1, max_value=20, required=False)
    assumptions = serializers.CharField(
        max_length=1000,
        required=False,
        default="User-supplied scenario assumptions; not measured emissions",
    )

    def validate(self, attrs):
        needed = {
            "point": [],
            "area": ["width_m", "length_m", "subdivisions"],
            "line": ["end_location", "subdivisions"],
        }[attrs["type"]]
        if any(k not in attrs for k in needed):
            raise serializers.ValidationError("Required for this source: " + ", ".join(needed))
        return attrs


class WeatherSerializer(StrictSerializer):
    wind_speed_ms = serializers.FloatField(min_value=0, max_value=100)
    wind_direction_deg = serializers.FloatField(min_value=0, max_value=359.999999)
    temperature_k = serializers.FloatField(min_value=150, max_value=350)
    solar_radiation_wm2 = serializers.FloatField(min_value=0, max_value=1500)
    cloud_fraction = serializers.FloatField(min_value=0, max_value=1)
    mixing_height_m = serializers.FloatField(min_value=2, max_value=10000, required=False)
    daytime = serializers.BooleanField()


class GridSerializer(StrictSerializer):
    width_m = serializers.IntegerField(min_value=1000, max_value=10000, default=10000)
    resolution_m = serializers.IntegerField(min_value=25, max_value=500, default=50)

    def validate(self, attrs):
        if attrs["width_m"] % attrs["resolution_m"]:
            raise serializers.ValidationError("Grid width must be a multiple of resolution")
        return attrs


class RunSerializer(StrictSerializer):
    name = serializers.CharField(max_length=200, default="VayuSim scenario")
    city = serializers.SlugField()
    centre = Coordinates()
    sources = SourceSerializer(many=True, min_length=1, max_length=20)
    weather_mode = serializers.ChoiceField(choices=["manual", "real"])
    datetime = serializers.DateTimeField()
    weather = WeatherSerializer(required=False)
    receptor_height = serializers.FloatField(min_value=0, max_value=100, default=1.5)
    environment = serializers.ChoiceField(choices=["urban", "rural"], default="urban")
    grid = GridSerializer(default=dict)
    thresholds = serializers.ListField(
        child=serializers.FloatField(min_value=0, max_value=10000), max_length=10, default=list
    )

    def validate_city(self, value):
        if not City.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Unknown city")
        return value

    def validate_thresholds(self, value):
        if not all(math.isfinite(x) for x in value):
            raise serializers.ValidationError("Use finite thresholds")
        return sorted(set(value))

    def validate(self, attrs):
        if attrs["weather_mode"] == "manual" and "weather" not in attrs:
            raise serializers.ValidationError("Manual mode requires weather")
        if attrs["weather_mode"] == "real" and "weather" in attrs:
            raise serializers.ValidationError("Real mode cannot override measured weather")
        total = sum(
            s.get("subdivisions", 1) ** (2 if s["type"] == "area" else 1) for s in attrs["sources"]
        )
        if total > 400:
            raise serializers.ValidationError("At most 400 point sub-sources per scenario")
        return attrs
