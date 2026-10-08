from rest_framework_gis.pagination import GeoJsonPagination


class BoundedGeoJsonPagination(GeoJsonPagination):
    max_page_size = 100

    def get_paginated_response_schema(self, schema):
        response = super().get_paginated_response_schema(schema)
        response["required"] = [
            "features" if field == "results" else field for field in response.get("required", [])
        ] + ["type"]
        return response
