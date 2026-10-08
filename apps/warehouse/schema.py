from drf_spectacular.contrib.rest_framework_gis import GeoFeatureModelListSerializerExtension
from drf_spectacular.plumbing import build_array_type

from .pagination import BoundedGeoJsonPagination


class PaginatedGeoFeatureListExtension(GeoFeatureModelListSerializerExtension):
    """The paginator supplies FeatureCollection; its features must be an array."""

    priority = 1

    def map_serializer(self, auto_schema, direction):
        if isinstance(auto_schema.view.paginator, BoundedGeoJsonPagination):
            component = auto_schema.resolve_serializer(self.target.child, direction)
            return build_array_type(component.ref)
        return super().map_serializer(auto_schema, direction)
