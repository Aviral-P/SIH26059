from pathlib import Path
import sys
import math

import pandas as pd
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.extract_environment import (
    load_hycom,
    extract_era5,
    extract_hycom,
)


INPUT_FILE = ROOT / "data/catalog/calibration_observations.csv"
COVERAGE_FILE = ROOT / "data/catalog/combined_calibration_coverage.csv"
ERA5_DIR = ROOT / "data/raw/era5/extracted"
OUTPUT_FILE = ROOT / "data/catalog/calibration_dataset.csv"


def find_era5_tiles():
    """
    Find all usable ERA5 NetCDF tiles.

    The downloaded ERA5 files contain:
        u10
        v10
        valid_time
        latitude
        longitude
    """

    files = sorted(ERA5_DIR.rglob("*.nc"))

    if not files:
        raise FileNotFoundError(
            f"No ERA5 NetCDF files found in {ERA5_DIR}"
        )

    tiles = []
    seen = set()

    for path in files:

        try:
            ds = xr.open_dataset(path)

            required = {"u10", "v10"}

            if not required.issubset(ds.data_vars):
                ds.close()
                continue

            if "valid_time" not in ds.coords:
                ds.close()
                continue

            lat_values = np.asarray(
                ds["latitude"].values,
                dtype=float
            )

            lon_values = np.asarray(
                ds["longitude"].values,
                dtype=float
            )

            key = (
                tuple(np.round(lat_values, 8)),
                tuple(np.round(lon_values, 8)),
            )

            if key in seen:
                ds.close()
                continue

            seen.add(key)

            tiles.append(
                {
                    "path": path,
                    "ds": ds,
                    "lat_min": float(lat_values.min()),
                    "lat_max": float(lat_values.max()),
                    "lon_min": float(lon_values.min()),
                    "lon_max": float(lon_values.max()),
                }
            )

            print(
                f"Loaded ERA5 tile: {path.name}"
            )

        except Exception as exc:

            print(
                f"Warning: could not open ERA5 "
                f"{path.name}: {exc}"
            )

    if not tiles:
        raise RuntimeError(
            "No usable ERA5 NetCDF tiles were found."
        )

    print(
        f"Unique ERA5 spatial tiles: {len(tiles)}"
    )

    return tiles


def longitude_in_tile(lon, lon_min, lon_max, tolerance=1e-6):
    """
    Check whether longitude belongs to an ERA5 tile.

    ERA5 uses -180 ... +180 longitude.
    """

    return (
        lon_min - tolerance
        <= lon
        <= lon_max + tolerance
    )


def latitude_in_tile(lat, lat_min, lat_max, tolerance=1e-6):
    """
    Check whether latitude belongs to an ERA5 tile.
    """

    return (
        lat_min - tolerance
        <= lat
        <= lat_max + tolerance
    )


def select_era5_tile(tiles, lat, lon):
    """
    Select the ERA5 tile containing the requested point.

    If a point lies exactly on a tile boundary, prefer the
    tile whose center is closest to the point.
    """

    candidates = []

    for tile in tiles:

        lat_ok = latitude_in_tile(
            lat,
            tile["lat_min"],
            tile["lat_max"],
        )

        lon_ok = longitude_in_tile(
            lon,
            tile["lon_min"],
            tile["lon_max"],
        )

        if lat_ok and lon_ok:

            center_lat = (
                tile["lat_min"] +
                tile["lat_max"]
            ) / 2.0

            center_lon = (
                tile["lon_min"] +
                tile["lon_max"]
            ) / 2.0

            distance = (
                (lat - center_lat) ** 2
                +
                (lon - center_lon) ** 2
            )

            candidates.append(
                (
                    distance,
                    tile
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[0]
    )

    return candidates[0][1]


def extract_era5_from_tile(
    tile,
    timestamp,
    lat,
    lon,
):
    """
    Extract ERA5 wind from one spatial tile.

    The existing extract_era5() function expects an atmosphere
    dataset containing u10, v10 and optionally t2m.

    The downloaded calibration ERA5 files contain only u10/v10,
    so temperature is handled as unavailable.
    """

    ds = tile["ds"]

    try:

        point = ds.sel(
            valid_time=timestamp,
            latitude=lat,
            longitude=lon,
            method="nearest",
        )

        u10 = float(
            np.asarray(
                point["u10"].values
            ).squeeze()
        )

        v10 = float(
            np.asarray(
                point["v10"].values
            ).squeeze()
        )

    except Exception:

        return {
            "u10": None,
            "v10": None,
            "wind_speed": None,
            "wind_available": False,
            "t2m": None,
            "temperature_available": False,
            "swh": None,
            "wave_available": False,
        }

    wind_available = (
        math.isfinite(u10)
        and math.isfinite(v10)
    )

    if wind_available:

        wind_speed = math.sqrt(
            u10 * u10
            +
            v10 * v10
        )

    else:

        u10 = None
        v10 = None
        wind_speed = None

    return {
        "u10": u10,
        "v10": v10,
        "wind_speed": wind_speed,
        "wind_available": wind_available,
        "t2m": None,
        "temperature_available": False,
        "swh": None,
        "wave_available": False,
    }


def main():

    print("=" * 70)
    print("BUILDING CALIBRATION DATASET")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Calibration observations not found:\n"
            f"{INPUT_FILE}"
        )

    if not COVERAGE_FILE.exists():
        raise FileNotFoundError(
            f"Combined calibration coverage not found:\n"
            f"{COVERAGE_FILE}"
        )

    observations = pd.read_csv(
        INPUT_FILE
    )

    coverage = pd.read_csv(
        COVERAGE_FILE
    )

    observations["start_time"] = pd.to_datetime(
        observations["start_time"]
    )

    observations["end_time"] = pd.to_datetime(
        observations["end_time"]
    )

    coverage["start_time"] = pd.to_datetime(
        coverage["start_time"]
    )

    coverage["end_time"] = pd.to_datetime(
        coverage["end_time"]
    )

    print(
        f"Total BYU pairs:       "
        f"{len(observations)}"
    )

    # ---------------------------------------------------------
    # Select only pairs with both environmental sources
    # ---------------------------------------------------------

    complete = coverage[
        coverage["environment_complete"]
        .astype(bool)
    ].copy()

    print(
        f"Complete pairs:        "
        f"{len(complete)}"
    )

    print(
        f"Complete icebergs:     "
        f"{complete['iceberg_id'].nunique()}"
    )

    keys = [
        "iceberg_id",
        "start_time",
        "end_time",
    ]

    df = observations.merge(
        complete[keys],
        on=keys,
        how="inner",
    )

    print(
        f"Pairs selected:        "
        f"{len(df)}"
    )

    if df.empty:
        raise RuntimeError(
            "No complete calibration pairs were found."
        )

    # ---------------------------------------------------------
    # Load ERA5 tiles
    # ---------------------------------------------------------

    print("\nLoading ERA5 tiles...")

    era5_tiles = find_era5_tiles()

    # ---------------------------------------------------------
    # HYCOM cache
    # ---------------------------------------------------------

    hycom_cache = {}

    rows = []

    # ---------------------------------------------------------
    # Process calibration pairs
    # ---------------------------------------------------------

    for position, (_, row) in enumerate(
        df.iterrows(),
        start=1,
    ):

        iceberg_id = row["iceberg_id"]

        timestamp = pd.Timestamp(
            row["start_time"]
        )

        lat = float(
            row["start_latitude"]
        )

        lon = float(
            row["start_longitude"]
        )

        print(
            f"[{position:3d}/{len(df)}] "
            f"{iceberg_id}: "
            f"{timestamp.date()}",
            end=" "
        )

        try:

            # -------------------------------------------------
            # ERA5
            # -------------------------------------------------

            era5_tile = select_era5_tile(
                era5_tiles,
                lat,
                lon,
            )

            if era5_tile is None:

                print(
                    "ERA5 tile unavailable"
                )

                continue

            era5 = extract_era5_from_tile(
                era5_tile,
                timestamp,
                lat,
                lon,
            )

            if not era5["wind_available"]:

                print(
                    "ERA5 wind unavailable"
                )

                continue

            # -------------------------------------------------
            # HYCOM
            # -------------------------------------------------

            hycom_key = timestamp.strftime(
                "%Y-%m-%d"
            )

            if hycom_key not in hycom_cache:

                hycom_cache[hycom_key] = load_hycom(
                    timestamp
                )

            hycom_ds = hycom_cache[
                hycom_key
            ]

            ocean = extract_hycom(
                hycom_ds,
                timestamp,
                lat,
                lon,
            )

            if not ocean["available"]:

                print(
                    "HYCOM unavailable"
                )

                continue

            # -------------------------------------------------
            # Build output row
            # -------------------------------------------------

            output = row.to_dict()

            output.update(
                {
                    "ocean_u": ocean["u"],
                    "ocean_v": ocean["v"],
                    "ocean_speed": ocean["speed"],

                    "wind_u": era5["u10"],
                    "wind_v": era5["v10"],
                    "wind_speed": era5["wind_speed"],

                    "temperature": era5["t2m"],
                    "wave_height": era5["swh"],
                }
            )

            rows.append(
                output
            )

            print("OK")

        except Exception as exc:

            print(
                f"ERROR: "
                f"{type(exc).__name__}: {exc}"
            )

    # ---------------------------------------------------------
    # Close HYCOM datasets
    # ---------------------------------------------------------

    for ds in hycom_cache.values():

        try:
            ds.close()
        except Exception:
            pass

    # ---------------------------------------------------------
    # Close ERA5 datasets
    # ---------------------------------------------------------

    for tile in era5_tiles:

        try:
            tile["ds"].close()
        except Exception:
            pass

    # ---------------------------------------------------------
    # Build final dataframe
    # ---------------------------------------------------------

    result = pd.DataFrame(
        rows
    )

    if result.empty:

        raise RuntimeError(
            "No calibration rows were successfully built."
        )

    numeric_columns = [
        "observed_u",
        "observed_v",
        "observed_speed",

        "ocean_u",
        "ocean_v",
        "ocean_speed",

        "wind_u",
        "wind_v",
        "wind_speed",

        "temperature",
        "wave_height",
    ]

    for column in numeric_columns:

        if column in result.columns:

            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    # ---------------------------------------------------------
    # Remove rows missing required calibration variables
    # ---------------------------------------------------------

    result = result.dropna(
        subset=[
            "observed_u",
            "observed_v",
            "ocean_u",
            "ocean_v",
            "wind_u",
            "wind_v",
        ]
    )

    # ---------------------------------------------------------
    # Sort
    # ---------------------------------------------------------

    result = result.sort_values(
        [
            "iceberg_id",
            "start_time",
        ]
    ).reset_index(
        drop=True
    )

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("CALIBRATION DATASET COMPLETE")
    print("=" * 70)

    print(
        f"Rows saved:           "
        f"{len(result)}"
    )

    print(
        f"Icebergs represented: "
        f"{result['iceberg_id'].nunique()}"
    )

    print("\nRows by iceberg:")

    print(
        result[
            "iceberg_id"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nRequired calibration columns:")

    required_columns = [
        "iceberg_id",
        "start_time",
        "end_time",
        "start_latitude",
        "start_longitude",
        "observed_latitude",
        "observed_longitude",
        "observed_u",
        "observed_v",
        "ocean_u",
        "ocean_v",
        "wind_u",
        "wind_v",
    ]

    for column in required_columns:

        status = (
            "OK"
            if column in result.columns
            else "MISSING"
        )

        print(
            f"  {column:25s} {status}"
        )

    print(
        f"\nSaved:\n"
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()