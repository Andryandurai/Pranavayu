import io

import numpy as np
from PIL import Image
from rasterio.features import shapes


def contours(values, grid, thresholds):
    features = []
    for threshold in thresholds:
        mask = (values > threshold).astype(np.uint8)
        for geometry, value in shapes(mask, mask=mask.astype(bool), transform=grid["affine"]):
            if value != 1:
                continue
            rings = [
                [
                    [float(x), float(y)]
                    for x, y in zip(
                        *grid["inverse"].transform([p[0] for p in ring], [p[1] for p in ring]),
                        strict=True,
                    )
                ]
                for ring in geometry["coordinates"]
            ]
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "threshold_ugm3": threshold,
                        "label": "modelled increment from these sources only",
                    },
                    "geometry": {"type": "Polygon", "coordinates": rings},
                }
            )
    return {"type": "FeatureCollection", "features": features}


def overlay_png(values):
    # CPCB PM2.5 subindex concentration boundaries; visual categories ONLY.
    # CPCB National AQI Technical Report Table2.1: 0–30/31–60/61–90/91–120/121–250/>250.
    # These hourly ADDED values are not the required24-hour total used for AQI.
    palette = np.array(
        [
            [0, 176, 80, 170],
            [146, 208, 80, 185],
            [255, 255, 0, 195],
            [255, 153, 0, 205],
            [255, 0, 0, 215],
            [192, 0, 0, 225],
        ],
        dtype=np.uint8,
    )
    pixels = palette[np.searchsorted([30, 60, 90, 120, 250], values, side="left")]
    pixels[values <= 1, 3] = 0
    stream = io.BytesIO()
    Image.fromarray(pixels, mode="RGBA").save(stream, format="PNG")
    return stream.getvalue()
