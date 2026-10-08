import json

from django.contrib.gis.gdal import GDALRaster
from django.db import transaction

from apps.ingest.sources.worldpop import WorldPopSource

from .models import PopulationRaster


def register_population(year=2025):
    source = WorldPopSource()
    # Provider catalogue: https://hub.worldpop.org/geodata/summary?id=73807
    # Public release: https://data.worldpop.org/repo/prj/Global_2015_2030/R2025A/doc/Global2_Release_Statement_R2025A_v1.pdf
    with source.lifecycle("analytics.population.register", {"year": year}):
        url = source.dataset_url.replace("/2030/", f"/{year}/").replace("_2030_", f"_{year}_")
        relative = source.filename.replace("_2030_", f"_{year}_")
        path = source.cache.root / relative
        if not path.exists():
            path, manifest = source.cache.download_ftp(
                url.replace("https://data.worldpop.org", "ftp://ftp.worldpop.org"),
                relative,
                metadata={
                    "year": year,
                    "projected": year > 2026,
                    "modelled_estimate": True,
                    "product": "R2025A v1 alpha constrained",
                    "doi": "10.5258/SOTON/WP00839",
                    "https_url": url,
                    "catalogue_url": "https://hub.worldpop.org/geodata/summary?id=73807",
                },
            )
        path, asset = source.local_asset(path)
        raster = GDALRaster(str(path))
        asset.metadata.update(
            srid=raster.srs.srid,
            width=raster.width,
            height=raster.height,
            bands=len(raster.bands),
            nodata=raster.bands[0].nodata_value,
        )
        asset.save(update_fields=["metadata", "updated_at"])
        manifest_path = path.with_name(path.name + ".manifest.json")
        manifest = json.loads(manifest_path.read_text())
        manifest["metadata"] = asset.metadata
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        with transaction.atomic():
            PopulationRaster.objects.filter(is_default=True).update(is_default=False)
            PopulationRaster.objects.update_or_create(
                asset=asset,
                defaults={
                    "year": year,
                    "is_default": True,
                    "rationale": (
                        "2025 population estimate nearest the recent observation period; "
                        "not a census or an exposure calculation."
                    ),
                },
            )
            old = source.source.assets.filter(path__contains="_2030_").first()
            if old:
                PopulationRaster.objects.get_or_create(
                    asset=old,
                    defaults={
                        "year": 2030,
                        "is_default": False,
                        "rationale": "Future projection retained; not the analysis default.",
                    },
                )
        source.run.params["asset_id"] = asset.pk
    if source.run.status != "success":
        raise RuntimeError(source.run.error_message)
    return {
        "year": year,
        "asset": asset.pk,
        "path": asset.path,
        "sha256": asset.sha256,
        "bytes": asset.size_bytes,
        "metadata": asset.metadata,
    }
