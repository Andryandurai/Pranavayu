import hashlib
import re

from django.contrib.gis.gdal import DataSource as GDALSource
from django.contrib.gis.geos import MultiPolygon

from apps.ingest.base import Source, SourceUnavailable
from apps.ingest.models import BoundaryProvenance, CityDistrictLink
from apps.warehouse.models import City, District, State

COMMIT = "b3fbbde595310b397a55d718e0958ce249a4fa1f"
LAYERS = {"states": "States/Admin2", "districts": "Districts/Census_2011/2011_Dist"}
STATE_CODES = {
    "andhra pradesh": "AP",
    "arunachal pradesh": "AR",
    "arunanchal pradesh": "AR",  # Spelling in the Census 2011 district layer.
    "assam": "AS",
    "bihar": "BR",
    "chhattisgarh": "CG",
    "goa": "GA",
    "gujarat": "GJ",
    "haryana": "HR",
    "himachal pradesh": "HP",
    "jammu and kashmir": "JK",
    "jharkhand": "JH",
    "karnataka": "KA",
    "kerala": "KL",
    "madhya pradesh": "MP",
    "maharashtra": "MH",
    "manipur": "MN",
    "meghalaya": "ML",
    "mizoram": "MZ",
    "nagaland": "NL",
    "orissa": "OD",
    "odisha": "OD",
    "punjab": "PB",
    "rajasthan": "RJ",
    "sikkim": "SK",
    "tamil nadu": "TN",
    "telangana": "TS",
    "tripura": "TR",
    "uttar pradesh": "UP",
    "uttarakhand": "UK",
    "west bengal": "WB",
    "delhi": "DL",
    "nct of delhi": "DL",
    "nct delhi": "DL",
    "andaman and nicobar": "AN",
    "andaman and nicobar islands": "AN",
    "andaman and nicobar island": "AN",
    "chandigarh": "CH",
    "dadra and nagar haveli": "DN",
    "dadara and nagar havelli": "DN",
    "daman and diu": "DD",
    "dadra and nagar haveli and daman and diu": "DH",
    "ladakh": "LA",
    "lakshadweep": "LD",
    "puducherry": "PY",
    "pondicherry": "PY",
}


class BoundarySource(Source):
    slug = "datameet-maps"
    name = "Datameet maps"
    url = "https://github.com/datameet/maps"
    licence = (
        "CC BY 4.0; district boundaries are Census 2011, not current administrative geography."
    )

    def download(self, **options):
        for name, stem in LAYERS.items():
            for extension in ("shp", "dbf", "shx", "prj"):
                self.download_asset(
                    f"https://raw.githubusercontent.com/datameet/maps/{COMMIT}/{stem}.{extension}",
                    f"boundaries/{name}/{stem.rsplit('/', 1)[-1]}.{extension}",
                    metadata={"commit": COMMIT, "layer": name, "district_vintage": 2011},
                )

    @staticmethod
    def state(name):
        legacy_key = re.sub(r"[^a-z ]", "", name.lower()).strip()
        key = " ".join(re.sub(r"[^a-z ]", "", name.lower().replace("&", " and ")).split())
        code = STATE_CODES.get(key) or "B" + hashlib.sha256(key.encode()).hexdigest()[:8]
        # Recode references from earlier imports in place, retaining their IDs
        # and geometry. Aliases with an existing canonical state are resolved
        # by the district's national census code below.
        legacy_code = "B" + hashlib.sha256(legacy_key.encode()).hexdigest()[:8]
        if code != legacy_code and not State.objects.filter(code=code).exists():
            legacy = State.objects.filter(code=legacy_code).first()
            if legacy is not None:
                legacy.code = code
                legacy.save(update_fields=["code", "updated_at"])
                return legacy, False
        return State.objects.get_or_create(code=code, defaults={"name": name})

    def load(self, **options):
        district_asset = None
        for kind, stem in LAYERS.items():
            path = self.cache.root / f"boundaries/{kind}/{stem.rsplit('/', 1)[-1]}.shp"
            if not path.exists():
                raise SourceUnavailable(f"Boundary file missing: {path.name}; run download_sources")
            path, asset = self.local_asset(path)
            if kind == "districts":
                district_asset = asset
            layer = GDALSource(str(path))[0]
            self.event("boundary_fields", layer=kind, fields=layer.fields)
            for feature in layer:
                fields = {name.lower(): str(feature[name].value).strip() for name in layer.fields}

                def field(*names, values=fields):
                    return next((values[n] for n in names if values.get(n)), None)

                state_name = field("st_nm", "state_name", "name_1", "state", "st_name")
                if not state_name:
                    raise ValueError(f"Unrecognised state field in {layer.fields}")
                state, created = self.state(state_name)
                geometry = feature.geom
                geometry.transform(4326)
                geos = geometry.geos
                if geos.geom_type == "Polygon":
                    geos = MultiPolygon(geos, srid=4326)
                if not geos.valid:
                    geos = geos.buffer(0)
                    if geos.geom_type == "Polygon":
                        geos = MultiPolygon(geos, srid=4326)
                target = state
                if kind == "districts":
                    name = field("district", "dt_name", "dist_name", "district_n", "name_2")
                    # DT_CEN_CD is only unique within a state; censuscode is
                    # the all-India three-digit Census 2011 district identifier.
                    census_code = field("censuscode", "dtcode11", "dist_code")
                    if not name:
                        raise ValueError(f"Unrecognised district field in {layer.fields}")
                    if census_code:
                        target, created = District.objects.get_or_create(
                            census_code=census_code, defaults={"state": state, "name": name}
                        )
                        if target.state_id != state.pk:
                            target.state = state
                            target.save(update_fields=["state", "updated_at"])
                    else:
                        target, created = District.objects.get_or_create(state=state, name=name)
                    # Historical DN/DD parents have no polygon in the newer
                    # state layer. Their names still originate in this asset.
                    BoundaryProvenance.objects.get_or_create(
                        state=state, defaults={"ingestion_run": self.run, "asset": asset}
                    )
                changed = target.geometry is None or not target.geometry.equals(geos)
                if changed:
                    target.geometry = geos
                    target.save(update_fields=["geometry", "updated_at"])
                BoundaryProvenance.objects.get_or_create(
                    **{kind[:-1]: target}, defaults={"ingestion_run": self.run, "asset": asset}
                )
                self.run.rows_fetched += 1
                self.run.rows_inserted += int(created or changed)
            self.run.save()
        for city in City.objects.all():
            matches = District.objects.filter(geometry__covers=city.location)
            # Historical Telangana districts lie in 2011 Andhra Pradesh: preserve
            # that vintage rather than relabel their parent state retroactively.
            district = matches.order_by("id").first()
            if district is None:
                self.errors.append(f"No Census 2011 district covers {city.name}")
                continue
            _, created = CityDistrictLink.objects.get_or_create(
                city=city,
                defaults={"district": district, "ingestion_run": self.run, "asset": district_asset},
            )
            self.run.rows_inserted += int(created)
            self.event(
                "city_district",
                city=city.slug,
                district=district.name,
                matches=matches.count(),
                historical_state=district.state.name,
            )
