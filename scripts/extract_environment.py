from pathlib import Path
import glob

import numpy as np
import pandas as pd
import xarray as xr


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

HYCOM_DIR = PROJECT_ROOT / "data" / "raw" / "hycom"
ERA5_DIR = PROJECT_ROOT / "data" / "raw" / "era5"


# ============================================================
# HELPERS
# ============================================================

def _to_float(value):
    return float(np.asarray(value).squeeze())


def _normalize_datetime(value):
    return pd.to_datetime(value)


def _find_variable(dataset, candidates):
    for name in candidates:
        if name in dataset.data_vars:
            return name
    return None


# ============================================================
# LONGITUDE HELPERS
# ============================================================

def _longitude_to_hycom(longitude):
    """
    Convert project longitude (-180..180)
    to HYCOM longitude (0..360).
    """
    converted = float(longitude) % 360.0

    if np.isclose(converted, 360.0):
        converted = 0.0

    return converted


def _longitude_from_360(longitude):
    """
    Convert 0..360 longitude to -180..180.
    """
    converted = ((float(longitude) + 180.0) % 360.0) - 180.0

    if np.isclose(converted, -180.0):
        converted = 180.0

    return converted


# ============================================================
# HYCOM FILE DISCOVERY
# ============================================================

def _find_hycom_files(year):
    pattern = str(
        HYCOM_DIR / f"uv3z_{year}*.nc4"
    )

    return sorted(
        glob.glob(pattern),
        key=lambda p: Path(p).name.lower()
    )


# ============================================================
# HYCOM
# ============================================================

def load_hycom(
    date_str,
    latitude,
    longitude
):
    """
    Extract nearest HYCOM ocean current.

    HYCOM longitude is handled as 0..360.
    """

    target_time = _normalize_datetime(date_str)

    latitude = float(latitude)
    longitude = float(longitude)

    year = target_time.year

    files = _find_hycom_files(year)

    if not files:
        raise FileNotFoundError(
            f"No HYCOM files found for year {year} "
            f"in {HYCOM_DIR}"
        )

    # --------------------------------------------------------
    # Convert longitude
    # --------------------------------------------------------

    hycom_longitude = _longitude_to_hycom(
        longitude
    )

    # --------------------------------------------------------
    # Find globally nearest time
    # --------------------------------------------------------

    best_file = None
    best_time = None
    best_difference = None

    for file_path in files:

        ds = None

        try:
            ds = xr.open_dataset(file_path)

            if "time" not in ds.coords:
                continue

            times = pd.to_datetime(
                ds["time"].values
            )

            if len(times) == 0:
                continue

            differences = np.abs(
                times - target_time
            )

            index = int(
                np.argmin(differences)
            )

            candidate_time = times[index]

            candidate_difference = abs(
                candidate_time - target_time
            )

            if (
                best_difference is None
                or candidate_difference < best_difference
            ):
                best_file = file_path
                best_time = candidate_time
                best_difference = candidate_difference

        except Exception:
            pass

        finally:
            if ds is not None:
                try:
                    ds.close()
                except Exception:
                    pass

    if best_file is None or best_time is None:
        raise FileNotFoundError(
            f"No usable HYCOM timestamp found for "
            f"{target_time}"
        )

    # --------------------------------------------------------
    # Open selected file
    # --------------------------------------------------------

    ds = None

    try:

        ds = xr.open_dataset(
            best_file
        )

        selected = ds.sel(
            time=np.datetime64(
                best_time.to_datetime64()
            ),
            method="nearest"
        )

        # ----------------------------------------------------
        # Surface layer
        # ----------------------------------------------------

        if "depth" in selected.dims:
            selected = selected.isel(
                depth=0
            )

        # ----------------------------------------------------
        # Coordinates
        # ----------------------------------------------------

        if "lat" not in selected.coords:
            raise ValueError(
                "HYCOM latitude coordinate not found."
            )

        if "lon" not in selected.coords:
            raise ValueError(
                "HYCOM longitude coordinate not found."
            )

        # ----------------------------------------------------
        # Spatial selection
        # ----------------------------------------------------

        selected = selected.sel(
            lat=latitude,
            lon=hycom_longitude,
            method="nearest"
        )

        # ----------------------------------------------------
        # Variables
        # ----------------------------------------------------

        u_name = _find_variable(
            selected,
            [
                "water_u",
                "u",
                "uo",
                "water_u_velocity",
                "U",
            ]
        )

        v_name = _find_variable(
            selected,
            [
                "water_v",
                "v",
                "vo",
                "water_v_velocity",
                "V",
            ]
        )

        if u_name is None or v_name is None:
            raise ValueError(
                "Could not identify HYCOM U/V variables. "
                f"Available: {list(selected.data_vars)}"
            )

        ocean_u = _to_float(
            selected[u_name].values
        )

        ocean_v = _to_float(
            selected[v_name].values
        )

        if not np.isfinite(ocean_u):
            raise ValueError(
                "HYCOM U is not finite."
            )

        if not np.isfinite(ocean_v):
            raise ValueError(
                "HYCOM V is not finite."
            )

        ocean_speed = float(
            np.hypot(
                ocean_u,
                ocean_v
            )
        )

        selected_time = pd.to_datetime(
            selected["time"].values
        )

        selected_lat = _to_float(
            selected["lat"].values
        )

        selected_hycom_lon = _to_float(
            selected["lon"].values
        )

        selected_project_lon = (
            _longitude_from_360(
                selected_hycom_lon
            )
        )

        time_difference_hours = (
            abs(
                selected_time - target_time
            ).total_seconds()
            / 3600.0
        )

        return {
            "u": ocean_u,
            "v": ocean_v,
            "speed": ocean_speed,

            "source_file": Path(
                best_file
            ).name,

            "requested_time": str(
                target_time
            ),

            "selected_time": str(
                selected_time
            ),

            "time_difference_hours": float(
                time_difference_hours
            ),

            "requested_latitude": latitude,

            "requested_longitude": longitude,

            "hycom_longitude": hycom_longitude,

            "latitude": selected_lat,

            "longitude": selected_project_lon,

            "hycom_longitude_selected":
                selected_hycom_lon,

            "data_gap_warning":
                time_difference_hours > 24.0,
        }

    finally:

        if ds is not None:
            try:
                ds.close()
            except Exception:
                pass


# ============================================================
# ERA5 FILE DISCOVERY
# ============================================================

def _find_era5_files():

    return sorted(
        ERA5_DIR.glob("*.nc"),
        key=lambda p: p.name.lower()
    )


# ============================================================
# ERA5 SPATIAL MATCH
# ============================================================

def _era5_spatial_distance(
    latitude,
    longitude,
    lat_min,
    lat_max,
    lon_min,
    lon_max
):
    """
    Distance metric used to select the best ERA5 tile.

    If the point lies inside the tile, distance = 0.

    Otherwise distance is based on how far the point is
    outside the tile bounds.
    """

    if latitude < lat_min:
        lat_gap = lat_min - latitude
    elif latitude > lat_max:
        lat_gap = latitude - lat_max
    else:
        lat_gap = 0.0

    if longitude < lon_min:
        lon_gap = lon_min - longitude
    elif longitude > lon_max:
        lon_gap = longitude - lon_max
    else:
        lon_gap = 0.0

    return float(
        np.hypot(
            lat_gap,
            lon_gap
        )
    )


# ============================================================
# ERA5
# ============================================================

def load_era5(
    date_str,
    latitude,
    longitude
):
    """
    Extract ERA5 10-m wind.

    Important:
    These files use 'valid_time', not 'time'.

    The function first identifies the best spatial ERA5
    tile and then searches its hourly valid_time coordinate.
    """

    target_time = _normalize_datetime(date_str)

    latitude = float(latitude)
    longitude = float(longitude)

    files = _find_era5_files()

    if not files:
        raise FileNotFoundError(
            f"No ERA5 NetCDF files found in {ERA5_DIR}"
        )

    # --------------------------------------------------------
    # FIND BEST SPATIAL TILE
    # --------------------------------------------------------

    spatial_candidates = []

    for file_path in files:

        ds = None

        try:

            ds = xr.open_dataset(
                file_path
            )

            if (
                "latitude" not in ds.coords
                or "longitude" not in ds.coords
            ):
                continue

            lat_values = np.asarray(
                ds["latitude"].values,
                dtype=float
            )

            lon_values = np.asarray(
                ds["longitude"].values,
                dtype=float
            )

            lat_min = float(
                np.nanmin(lat_values)
            )

            lat_max = float(
                np.nanmax(lat_values)
            )

            lon_min = float(
                np.nanmin(lon_values)
            )

            lon_max = float(
                np.nanmax(lon_values)
            )

            distance = _era5_spatial_distance(
                latitude,
                longitude,
                lat_min,
                lat_max,
                lon_min,
                lon_max
            )

            spatial_candidates.append(
                {
                    "file": file_path,
                    "distance": distance,
                    "lat_min": lat_min,
                    "lat_max": lat_max,
                    "lon_min": lon_min,
                    "lon_max": lon_max,
                }
            )

        except Exception:
            pass

        finally:

            if ds is not None:
                try:
                    ds.close()
                except Exception:
                    pass

    if not spatial_candidates:

        raise FileNotFoundError(
            "Could not inspect any ERA5 spatial grids."
        )

    spatial_candidates.sort(
        key=lambda item: item["distance"]
    )

    best_spatial = spatial_candidates[0]

    best_file = best_spatial["file"]

    # --------------------------------------------------------
    # OPEN BEST TILE
    # --------------------------------------------------------

    ds = None

    try:

        ds = xr.open_dataset(
            best_file
        )

        # ----------------------------------------------------
        # TIME COORDINATE
        # ----------------------------------------------------

        if "valid_time" in ds.coords:

            time_name = "valid_time"

        elif "time" in ds.coords:

            time_name = "time"

        else:

            raise ValueError(
                f"No valid time coordinate in "
                f"{Path(best_file).name}"
            )

        times = pd.to_datetime(
            ds[time_name].values
        )

        if len(times) == 0:

            raise ValueError(
                f"ERA5 file "
                f"{Path(best_file).name} "
                f"contains no timestamps."
            )

        # ----------------------------------------------------
        # FIND NEAREST TIME
        # ----------------------------------------------------

        differences = np.abs(
            times - target_time
        )

        time_index = int(
            np.argmin(differences)
        )

        nearest_time = times[
            time_index
        ]

        time_difference_hours = (
            abs(
                nearest_time - target_time
            ).total_seconds()
            / 3600.0
        )

        # ----------------------------------------------------
        # SELECT TIME
        # ----------------------------------------------------

        selected = ds.isel(
            {
                time_name: time_index
            }
        )

        # ----------------------------------------------------
        # SELECT NEAREST LOCATION
        # ----------------------------------------------------

        selected = selected.sel(
            latitude=latitude,
            longitude=longitude,
            method="nearest"
        )

        # ----------------------------------------------------
        # VARIABLES
        # ----------------------------------------------------

        u_name = _find_variable(
            selected,
            [
                "u10",
                "10u",
                "u",
            ]
        )

        v_name = _find_variable(
            selected,
            [
                "v10",
                "10v",
                "v",
            ]
        )

        if u_name is None or v_name is None:

            raise ValueError(
                f"Could not identify ERA5 u10/v10 "
                f"in {Path(best_file).name}. "
                f"Available variables: "
                f"{list(selected.data_vars)}"
            )

        wind_u = _to_float(
            selected[u_name].values
        )

        wind_v = _to_float(
            selected[v_name].values
        )

        if not np.isfinite(wind_u):

            raise ValueError(
                "ERA5 u10 is not finite."
            )

        if not np.isfinite(wind_v):

            raise ValueError(
                "ERA5 v10 is not finite."
            )

        wind_speed = float(
            np.hypot(
                wind_u,
                wind_v
            )
        )

        selected_latitude = _to_float(
            selected["latitude"].values
        )

        selected_longitude = _to_float(
            selected["longitude"].values
        )

        return {
            "u": wind_u,
            "v": wind_v,
            "speed": wind_speed,

            "source": "ERA5",

            "source_file": Path(
                best_file
            ).name,

            "requested_time": str(
                target_time
            ),

            "selected_time": str(
                nearest_time
            ),

            "time_difference_hours": float(
                time_difference_hours
            ),

            "requested_latitude": latitude,

            "requested_longitude": longitude,

            "latitude": selected_latitude,

            "longitude": selected_longitude,

            "tile_lat_min":
                best_spatial["lat_min"],

            "tile_lat_max":
                best_spatial["lat_max"],

            "tile_lon_min":
                best_spatial["lon_min"],

            "tile_lon_max":
                best_spatial["lon_max"],

            "spatial_distance":
                best_spatial["distance"],

            "data_gap_warning":
                time_difference_hours > 24.0,
        }

    finally:

        if ds is not None:
            try:
                ds.close()
            except Exception:
                pass


# ============================================================
# COMBINED ENVIRONMENT
# ============================================================

def extract_environment(
    date_str,
    latitude,
    longitude,
    validation=False
):
    """
    Extract both ocean and atmospheric forcing.

    'validation' is retained for compatibility with
    drift_engine.py.
    """

    target_time = _normalize_datetime(
        date_str
    )

    latitude = float(latitude)
    longitude = float(longitude)

    # --------------------------------------------------------
    # HYCOM
    # --------------------------------------------------------

    ocean = load_hycom(
        target_time,
        latitude,
        longitude
    )

    # --------------------------------------------------------
    # ERA5
    # --------------------------------------------------------

    try:

        wind = load_era5(
            target_time,
            latitude,
            longitude
        )

        wind_available = True

    except Exception as exc:

        wind = {
            "u": 0.0,
            "v": 0.0,
            "speed": 0.0,

            "source": None,
            "source_file": None,

            "requested_time":
                str(target_time),

            "selected_time": None,

            "time_difference_hours": None,

            "requested_latitude":
                latitude,

            "requested_longitude":
                longitude,

            "latitude": latitude,

            "longitude": longitude,

            "tile_lat_min": None,
            "tile_lat_max": None,

            "tile_lon_min": None,
            "tile_lon_max": None,

            "spatial_distance": None,

            "data_gap_warning": True,

            "error": str(exc),
        }

        wind_available = False

    return {

        "time": str(
            target_time
        ),

        "latitude": latitude,

        "longitude": longitude,

        "validation": bool(
            validation
        ),

        "ocean": {
            "u": ocean["u"],
            "v": ocean["v"],
            "speed": ocean["speed"],

            "source_file":
                ocean["source_file"],

            "requested_time":
                ocean["requested_time"],

            "selected_time":
                ocean["selected_time"],

            "time_difference_hours":
                ocean["time_difference_hours"],

            "requested_latitude":
                ocean["requested_latitude"],

            "requested_longitude":
                ocean["requested_longitude"],

            "hycom_longitude":
                ocean["hycom_longitude"],

            "latitude":
                ocean["latitude"],

            "longitude":
                ocean["longitude"],

            "hycom_longitude_selected":
                ocean["hycom_longitude_selected"],

            "data_gap_warning":
                ocean["data_gap_warning"],
        },

        "wind": {
            "u": wind["u"],
            "v": wind["v"],
            "speed": wind["speed"],

            "source":
                wind.get("source"),

            "source_file":
                wind.get("source_file"),

            "requested_time":
                wind["requested_time"],

            "selected_time":
                wind.get("selected_time"),

            "time_difference_hours":
                wind.get("time_difference_hours"),

            "requested_latitude":
                wind.get("requested_latitude"),

            "requested_longitude":
                wind.get("requested_longitude"),

            "latitude":
                wind.get("latitude"),

            "longitude":
                wind.get("longitude"),

            "tile_lat_min":
                wind.get("tile_lat_min"),

            "tile_lat_max":
                wind.get("tile_lat_max"),

            "tile_lon_min":
                wind.get("tile_lon_min"),

            "tile_lon_max":
                wind.get("tile_lon_max"),

            "spatial_distance":
                wind.get("spatial_distance"),

            "data_gap_warning":
                wind.get(
                    "data_gap_warning",
                    False
                ),
        },

        "wind_available":
            bool(wind_available),
    }


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    TEST_TIME = "2023-08-20T00:00:00"
    TEST_LATITUDE = -63.0
    TEST_LONGITUDE = -45.0

    print("=" * 70)
    print("ENVIRONMENT EXTRACTION TEST")
    print("=" * 70)

    print(
        f"Time      : {TEST_TIME}"
    )

    print(
        f"Latitude  : {TEST_LATITUDE}"
    )

    print(
        f"Longitude : {TEST_LONGITUDE}"
    )

    # --------------------------------------------------------
    # HYCOM
    # --------------------------------------------------------

    print()
    print("Testing HYCOM...")
    print("-" * 70)

    ocean = load_hycom(
        TEST_TIME,
        TEST_LATITUDE,
        TEST_LONGITUDE
    )

    print("HYCOM SUCCESS")

    print(
        f"U                     : {ocean['u']}"
    )

    print(
        f"V                     : {ocean['v']}"
    )

    print(
        f"Speed                 : {ocean['speed']}"
    )

    print(
        f"Source file           : {ocean['source_file']}"
    )

    print(
        f"Requested time        : {ocean['requested_time']}"
    )

    print(
        f"Selected time         : {ocean['selected_time']}"
    )

    print(
        f"Time difference (hrs) : "
        f"{ocean['time_difference_hours']}"
    )

    print(
        f"Requested longitude   : "
        f"{ocean['requested_longitude']}"
    )

    print(
        f"HYCOM longitude       : "
        f"{ocean['hycom_longitude']}"
    )

    print(
        f"Selected longitude    : "
        f"{ocean['longitude']}"
    )

    print(
        f"Selected latitude     : "
        f"{ocean['latitude']}"
    )

    print(
        f"Data gap warning      : "
        f"{ocean['data_gap_warning']}"
    )

    # --------------------------------------------------------
    # ERA5
    # --------------------------------------------------------

    print()
    print("Testing ERA5...")
    print("-" * 70)

    wind = load_era5(
        TEST_TIME,
        TEST_LATITUDE,
        TEST_LONGITUDE
    )

    print("ERA5 SUCCESS")

    print(
        f"U                     : {wind['u']}"
    )

    print(
        f"V                     : {wind['v']}"
    )

    print(
        f"Speed                 : {wind['speed']}"
    )

    print(
        f"Source file           : {wind['source_file']}"
    )

    print(
        f"Requested time        : {wind['requested_time']}"
    )

    print(
        f"Selected time         : {wind['selected_time']}"
    )

    print(
        f"Time difference (hrs) : "
        f"{wind['time_difference_hours']}"
    )

    print(
        f"Selected latitude     : "
        f"{wind['latitude']}"
    )

    print(
        f"Selected longitude    : "
        f"{wind['longitude']}"
    )

    print(
        f"ERA5 tile             : "
        f"{wind['tile_lat_min']} to "
        f"{wind['tile_lat_max']} lat, "
        f"{wind['tile_lon_min']} to "
        f"{wind['tile_lon_max']} lon"
    )

    print(
        f"Spatial distance      : "
        f"{wind['spatial_distance']}"
    )

    print(
        f"Data gap warning      : "
        f"{wind['data_gap_warning']}"
    )

    # --------------------------------------------------------
    # COMBINED
    # --------------------------------------------------------

    print()
    print("Testing combined environment...")
    print("-" * 70)

    result = extract_environment(
        TEST_TIME,
        TEST_LATITUDE,
        TEST_LONGITUDE
    )

    print("COMBINED EXTRACTION SUCCESS")

    print()
    print("OCEAN:")
    print(
        f"  U       : {result['ocean']['u']}"
    )
    print(
        f"  V       : {result['ocean']['v']}"
    )
    print(
        f"  Speed   : {result['ocean']['speed']}"
    )

    print()
    print("WIND:")
    print(
        f"  U       : {result['wind']['u']}"
    )
    print(
        f"  V       : {result['wind']['v']}"
    )
    print(
        f"  Speed   : {result['wind']['speed']}"
    )
    print(
        f"  Available: {result['wind_available']}"
    )

    print()
    print("=" * 70)
    print("ALL ENVIRONMENT TESTS PASSED")
    print("=" * 70)