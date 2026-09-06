from pathlib import Path
import re

import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]

CALIBRATION_FILE = ROOT / "data/catalog/calibration_observations.csv"
NSIDC_DIR = ROOT / "data/raw/nsidc"
OUTPUT_FILE = ROOT / "data/catalog/nsidc_calibration_audit.csv"

ICECON_VAR = "F17_ICECON"


def build_nsidc_index():
    """
    Build an index:

        YYYYMMDD -> NSIDC NetCDF file

    The date is extracted directly from the filename instead
    of depending on the exact complete filename pattern.
    """

    index = {}

    date_pattern = re.compile(r"_(\d{8})_")

    files = list(NSIDC_DIR.glob("*.nc"))

    print(f"Scanning NSIDC files: {len(files)}")

    for path in files:

        match = date_pattern.search(path.name)

        if not match:
            continue

        date_key = match.group(1)

        # Only accept filenames that look like NSIDC-0051 files.
        if "NSIDC0051" not in path.name:
            continue

        index[date_key] = path

    return index


def get_valid_values(da):
    """Return finite values excluding fill/missing values."""

    values = np.asarray(da.values, dtype=float)

    fill_values = []

    for attr_name in ["_FillValue", "missing_value"]:

        value = da.attrs.get(attr_name)

        if value is not None:

            try:
                fill_values.append(float(value))
            except (TypeError, ValueError):
                pass

    valid = np.isfinite(values)

    for fill in fill_values:
        valid &= ~np.isclose(values, fill)

    return values[valid]


def inspect_concentration_units(da):

    attrs = da.attrs

    return {
        "units": attrs.get("units"),
        "long_name": attrs.get("long_name"),
        "standard_name": attrs.get("standard_name"),
        "scale_factor": attrs.get("scale_factor"),
        "add_offset": attrs.get("add_offset"),
        "fill_value": attrs.get("_FillValue"),
    }


def find_coordinate_names(ds):
    """
    Identify projected x/y coordinate names.

    NSIDC-0051 normally uses projected coordinates.
    """

    x_name = None
    y_name = None

    for candidate in ["x", "xc", "X"]:

        if candidate in ds.coords or candidate in ds.variables:

            x_name = candidate
            break

    for candidate in ["y", "yc", "Y"]:

        if candidate in ds.coords or candidate in ds.variables:

            y_name = candidate
            break

    return x_name, y_name


def sample_nsidc(
    path,
    latitude,
    longitude,
    transformer,
):

    try:

        with xr.open_dataset(path) as ds:

            if ICECON_VAR not in ds.variables:

                return {
                    "available": False,
                    "reason": (
                        f"Missing variable {ICECON_VAR}"
                    ),
                }

            x_name, y_name = find_coordinate_names(ds)

            if x_name is None or y_name is None:

                return {
                    "available": False,
                    "reason": (
                        "Could not identify x/y coordinates"
                    ),
                }

            # Convert geographic coordinates to NSIDC
            # polar stereographic coordinates.
            x, y = transformer.transform(
                longitude,
                latitude,
            )

            point = ds.sel(
                {
                    x_name: x,
                    y_name: y,
                },
                method="nearest",
            )

            icecon = point[ICECON_VAR]

            valid_values = get_valid_values(
                icecon
            )

            if len(valid_values) == 0:

                return {
                    "available": False,
                    "reason": (
                        "Sampled value is missing/fill"
                    ),
                }

            value = float(
                valid_values[0]
            )

            metadata = inspect_concentration_units(
                ds[ICECON_VAR]
            )

            return {
                "available": True,
                "ice_concentration": value,
                "units": metadata["units"],
                "long_name": metadata["long_name"],
                "sample_x": float(
                    point[x_name].values
                ),
                "sample_y": float(
                    point[y_name].values
                ),
            }

    except Exception as exc:

        return {
            "available": False,
            "reason": (
                f"{type(exc).__name__}: {exc}"
            ),
        }


def main():

    print("=" * 80)
    print("NSIDC-0051 CALIBRATION CONTEXT / QC AUDIT")
    print("=" * 80)

    # ------------------------------------------------------------
    # CHECK INPUTS
    # ------------------------------------------------------------

    if not CALIBRATION_FILE.exists():

        raise FileNotFoundError(
            f"Calibration file not found:\n"
            f"{CALIBRATION_FILE}"
        )

    if not NSIDC_DIR.exists():

        raise FileNotFoundError(
            f"NSIDC directory not found:\n"
            f"{NSIDC_DIR}"
        )

    # ------------------------------------------------------------
    # LOAD CALIBRATION DATA
    # ------------------------------------------------------------

    df = pd.read_csv(
        CALIBRATION_FILE
    )

    df["start_time"] = pd.to_datetime(
        df["start_time"]
    )

    df["end_time"] = pd.to_datetime(
        df["end_time"]
    )

    print(
        f"\nCalibration pairs: "
        f"{len(df)}"
    )

    print(
        f"Unique icebergs:   "
        f"{df['iceberg_id'].nunique()}"
    )

    # ------------------------------------------------------------
    # BUILD NSIDC INDEX
    # ------------------------------------------------------------

    nsidc_index = build_nsidc_index()

    print(
        f"NSIDC NetCDF files indexed: "
        f"{len(nsidc_index)}"
    )

    if not nsidc_index:

        print(
            "\nERROR: No NSIDC files could "
            "be indexed."
        )

        return

    # ------------------------------------------------------------
    # INDEX TEST
    # ------------------------------------------------------------

    print("\n--- INDEX TEST ---")

    test_dates = [
        "20120419",
        "20230614",
        "20230729",
        "20230804",
    ]

    for date_key in test_dates:

        path = nsidc_index.get(
            date_key
        )

        if path:

            print(
                f"{date_key}: FOUND -> "
                f"{path.name}"
            )

        else:

            print(
                f"{date_key}: NOT FOUND"
            )

    # ------------------------------------------------------------
    # TRANSFORMER
    # ------------------------------------------------------------

    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:3412",
        always_xy=True,
    )

    rows = []

    # ------------------------------------------------------------
    # PROCESS 105 PAIRS
    # ------------------------------------------------------------

    for _, row in df.iterrows():

        for point_type in [
            "start",
            "end",
        ]:

            if point_type == "start":

                timestamp = row[
                    "start_time"
                ]

                latitude = row[
                    "start_latitude"
                ]

                longitude = row[
                    "start_longitude"
                ]

            else:

                timestamp = row[
                    "end_time"
                ]

                latitude = row[
                    "observed_latitude"
                ]

                longitude = row[
                    "observed_longitude"
                ]

            date_key = timestamp.strftime(
                "%Y%m%d"
            )

            path = nsidc_index.get(
                date_key
            )

            result = {
                "iceberg_id": row[
                    "iceberg_id"
                ],

                "pair_start": row[
                    "start_time"
                ],

                "pair_end": row[
                    "end_time"
                ],

                "point_type": point_type,

                "timestamp": timestamp,

                "latitude": latitude,

                "longitude": longitude,

                "nsidc_date": date_key,

                "file_found": (
                    path is not None
                ),

                "available": False,

                "ice_concentration": np.nan,

                "units": None,

                "long_name": None,

                "sample_x": np.nan,

                "sample_y": np.nan,

                "reason": "",
            }

            if path is None:

                result["reason"] = (
                    "No NSIDC file for date"
                )

                rows.append(result)

                continue

            sampled = sample_nsidc(
                path=path,
                latitude=latitude,
                longitude=longitude,
                transformer=transformer,
            )

            result.update(
                sampled
            )

            rows.append(result)

    audit = pd.DataFrame(
        rows
    )

    # ------------------------------------------------------------
    # SAVE RESULT
    # ------------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    audit.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # ------------------------------------------------------------
    # FILE COVERAGE
    # ------------------------------------------------------------

    print("\n--- FILE COVERAGE ---")

    total_points = len(audit)

    files_found = int(
        audit["file_found"].sum()
    )

    usable_points = int(
        audit["available"].sum()
    )

    print(
        f"Expected points:       "
        f"{total_points}"
    )

    print(
        f"NSIDC files available: "
        f"{files_found}"
    )

    print(
        f"Usable samples:        "
        f"{usable_points}"
    )

    if total_points > 0:

        print(
            f"File coverage: "
            f"{files_found / total_points * 100:.1f}%"
        )

        print(
            f"Usable coverage: "
            f"{usable_points / total_points * 100:.1f}%"
        )

    # ------------------------------------------------------------
    # COVERAGE BY ICEBERG
    # ------------------------------------------------------------

    print(
        "\n--- COVERAGE BY ICEBERG ---"
    )

    iceberg_summary = (
        audit
        .groupby("iceberg_id")
        .agg(
            points=(
                "available",
                "size",
            ),

            usable=(
                "available",
                "sum",
            ),
        )
    )

    iceberg_summary[
        "coverage_pct"
    ] = (
        iceberg_summary["usable"]
        / iceberg_summary["points"]
        * 100
    )

    print(
        iceberg_summary.to_string()
    )

    # ------------------------------------------------------------
    # COVERAGE BY YEAR
    # ------------------------------------------------------------

    print(
        "\n--- COVERAGE BY YEAR ---"
    )

    audit["year"] = pd.to_datetime(
        audit["timestamp"]
    ).dt.year

    year_summary = (
        audit
        .groupby("year")
        .agg(
            points=(
                "available",
                "size",
            ),

            usable=(
                "available",
                "sum",
            ),
        )
    )

    year_summary[
        "coverage_pct"
    ] = (
        year_summary["usable"]
        / year_summary["points"]
        * 100
    )

    print(
        year_summary.to_string()
    )

    # ------------------------------------------------------------
    # SEA ICE CONCENTRATION
    # ------------------------------------------------------------

    print(
        "\n--- SEA-ICE CONCENTRATION ---"
    )

    concentration = (
        audit.loc[
            audit["available"],
            "ice_concentration",
        ]
        .dropna()
    )

    if len(concentration) > 0:

        print(
            f"Valid samples: "
            f"{len(concentration)}"
        )

        print(
            f"Minimum:       "
            f"{concentration.min():.4f}"
        )

        print(
            f"Maximum:       "
            f"{concentration.max():.4f}"
        )

        print(
            f"Mean:          "
            f"{concentration.mean():.4f}"
        )

        print(
            f"Median:        "
            f"{concentration.median():.4f}"
        )

        units = (
            audit.loc[
                audit["available"],
                "units",
            ]
            .dropna()
            .astype(str)
            .unique()
        )

        print(
            "Units:         "
            + (
                ", ".join(units)
                if len(units)
                else "not specified"
            )
        )

    else:

        print(
            "No valid sea-ice "
            "concentration samples."
        )

    # ------------------------------------------------------------
    # MISSING / INVALID
    # ------------------------------------------------------------

    print(
        "\n--- MISSING / INVALID REASONS ---"
    )

    missing = audit.loc[
        ~audit["available"],
        "reason",
    ]

    if len(missing) > 0:

        print(
            missing
            .value_counts()
            .to_string()
        )

    else:

        print(
            "No missing or invalid samples."
        )

    # ------------------------------------------------------------
    # SAMPLE VALUES
    # ------------------------------------------------------------

    print(
        "\n--- POINTS WITH SEA-ICE DATA ---"
    )

    available = audit[
        audit["available"]
    ]

    if len(available) > 0:

        print(
            available[
                [
                    "iceberg_id",
                    "point_type",
                    "timestamp",
                    "latitude",
                    "longitude",
                    "ice_concentration",
                    "units",
                ]
            ]
            .head(20)
            .to_string(index=False)
        )

    else:

        print(
            "No usable NSIDC samples."
        )

    # ------------------------------------------------------------
    # FINAL STATUS
    # ------------------------------------------------------------

    print(
        "\n--- FINAL STATUS ---"
    )

    if usable_points == 0:

        print(
            "FAIL: No usable NSIDC samples."
        )

    elif (
        usable_points / total_points
        >= 0.8
    ):

        print(
            "PASS: NSIDC coverage is "
            "sufficient for contextual "
            "analysis."
        )

    else:

        print(
            "PARTIAL: NSIDC coverage is "
            "incomplete. Use it only for "
            "stratified/contextual analysis."
        )

    print(
        "\nSaved audit:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "NSIDC AUDIT COMPLETE"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":
    main()