from pathlib import Path
from typing import List, Dict

import numpy as np
import xarray as xr
from pyproj import Transformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

NSIDC_DIR = PROJECT_ROOT / "data" / "raw" / "nsidc_validation"

TRANSFORMER = Transformer.from_crs(
    "EPSG:3412",
    "EPSG:4326",
    always_xy=True,
)


def _find_file(date: str) -> Path:
    path = (
        NSIDC_DIR
        / f"NSIDC0051_SEAICE_PS_S25km_{date}_v2.0.nc"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"NSIDC file not found: {path}"
        )

    return path


def get_sea_ice(
    date: str,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
) -> List[Dict[str, float]]:
    """
    Extract valid NSIDC-0051 sea-ice concentration cells
    inside a requested geographic bounding box.

    Concentration is returned in the range [0, 1].
    """

    file_path = _find_file(date)

    with xr.open_dataset(file_path) as ds:

        ice = ds["F17_ICECON"]

        # Remove the time dimension if present.
        if "time" in ice.dims:
            ice = ice.isel(time=0)

        values = ice.values

        # NSIDC special values:
        # 251 = pole hole
        # 252 = land mask
        # 253 = unused
        # 254 = coast
        valid = np.isfinite(values) & (values >= 0) & (values <= 1)

        y = ds["y"].values
        x = ds["x"].values

        xx, yy = np.meshgrid(x, y)

        valid &= np.isfinite(xx) & np.isfinite(yy)

        # Convert grid cell centers from EPSG:3412
        # to geographic longitude/latitude.
        lon, lat = TRANSFORMER.transform(xx, yy)

        geographic_mask = (
            valid
            & (lat >= min_lat)
            & (lat <= max_lat)
            & (lon >= min_lon)
            & (lon <= max_lon)
        )

        rows, cols = np.where(geographic_mask)

        cells: List[Dict[str, float]] = []

        for row, col in zip(rows, cols):
            cells.append(
                {
                    "latitude": float(lat[row, col]),
                    "longitude": float(lon[row, col]),
                    "concentration": float(values[row, col]),
                }
            )

    return cells
