from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
import xarray as xr
from pyproj import Transformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

NSIDC_DIR = PROJECT_ROOT / "data" / "raw" / "nsidc"

TRANSFORMER = Transformer.from_crs(
    "EPSG:3412",
    "EPSG:4326",
    always_xy=True,
)


def _find_file(date: str) -> Tuple[Path, str]:
    """
    Find the best available NSIDC sea-ice file.

    Priority:
        1. Exact daily file
        2. Monthly file for the requested month

    Returns:
        (file_path, source_type)
    """

    date = str(date).strip()

    if len(date) != 8 or not date.isdigit():
        raise ValueError(
            f"Invalid date format: {date}. "
            f"Expected YYYYMMDD."
        )

    year = date[:4]
    month = date[4:6]

    # --------------------------------------------------------
    # 1. Try exact daily file
    # --------------------------------------------------------

    daily_path = (
        NSIDC_DIR
        / f"NSIDC0051_SEAICE_PS_S25km_{date}_v2.0.nc"
    )

    if daily_path.exists():
        return daily_path, "daily"

    # --------------------------------------------------------
    # 2. Fall back to monthly file
    # --------------------------------------------------------

    monthly_path = (
        NSIDC_DIR
        / f"NSIDC0051_SEAICE_PS_S25km_{year}{month}_v2.0.nc"
    )

    if monthly_path.exists():
        return monthly_path, "monthly"

    # --------------------------------------------------------
    # 3. Nothing available
    # --------------------------------------------------------

    raise FileNotFoundError(
        "NSIDC sea-ice data not found. "
        f"Requested date: {date}. "
        f"Checked daily file: {daily_path}. "
        f"Checked monthly file: {monthly_path}."
    )


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

    The function first tries the exact daily NSIDC file.
    If unavailable, it falls back to the monthly NSIDC file
    for the same month.

    Concentration is returned in the range [0, 1].
    """

    file_path, source_type = _find_file(date)

    with xr.open_dataset(file_path) as ds:

        if "F17_ICECON" not in ds:
            raise KeyError(
                f"F17_ICECON variable not found in "
                f"NSIDC file: {file_path}"
            )

        ice = ds["F17_ICECON"]

        # ----------------------------------------------------
        # Handle time dimension
        # ----------------------------------------------------

        if "time" in ice.dims:

            if ice.sizes["time"] > 1:

                # Try to select the requested date if time
                # information is available.
                requested_time = np.datetime64(
                    f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                )

                try:

                    time_values = ds["time"].values

                    differences = np.abs(
                        time_values - requested_time
                    )

                    time_index = int(
                        np.argmin(differences)
                    )

                    ice = ice.isel(
                        time=time_index
                    )

                except Exception:

                    ice = ice.isel(time=0)

            else:

                ice = ice.isel(time=0)

        values = ice.values

        # ----------------------------------------------------
        # NSIDC special values
        #
        # Valid concentration is 0-1.
        # ----------------------------------------------------

        valid = (
            np.isfinite(values)
            & (values >= 0)
            & (values <= 1)
        )

        # ----------------------------------------------------
        # Grid coordinates
        # ----------------------------------------------------

        if "y" not in ds or "x" not in ds:
            raise KeyError(
                f"x/y grid coordinates not found in "
                f"NSIDC file: {file_path}"
            )

        y = ds["y"].values
        x = ds["x"].values

        xx, yy = np.meshgrid(
            x,
            y,
        )

        valid &= (
            np.isfinite(xx)
            & np.isfinite(yy)
        )

        # ----------------------------------------------------
        # Convert EPSG:3412 → latitude/longitude
        # ----------------------------------------------------

        lon, lat = TRANSFORMER.transform(
            xx,
            yy,
        )

        # ----------------------------------------------------
        # Geographic bounding box
        # ----------------------------------------------------

        geographic_mask = (
            valid
            & (lat >= min_lat)
            & (lat <= max_lat)
            & (lon >= min_lon)
            & (lon <= max_lon)
        )

        rows, cols = np.where(
            geographic_mask
        )

        cells: List[Dict[str, float]] = []

        for row, col in zip(rows, cols):

            cells.append(
                {
                    "latitude": float(
                        lat[row, col]
                    ),
                    "longitude": float(
                        lon[row, col]
                    ),
                    "concentration": float(
                        values[row, col]
                    ),
                }
            )

    return cells