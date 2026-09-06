from pathlib import Path
import zipfile
import io
import re

import numpy as np
import pandas as pd
from pyproj import Geod


ROOT = Path(__file__).resolve().parents[1]

BYU_ZIP = (
    ROOT /
    "data/raw/byu/stats_database_v7.1.zip"
)

WINDOWS_FILE = (
    ROOT /
    "data/catalog/selected_calibration_windows.csv"
)

OUTPUT_FILE = (
    ROOT /
    "data/catalog/calibration_observations.csv"
)

GEOD = Geod(ellps="WGS84")


# ============================================================
# Utilities
# ============================================================

def normalize_column(name):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(name).lower()
    )


def find_column(columns, candidates):

    normalized = {
        normalize_column(c): c
        for c in columns
    }

    for candidate in candidates:

        key = normalize_column(candidate)

        if key in normalized:
            return normalized[key]

    return None


def parse_byu_date(value):

    """
    BYU statistical database uses a YYYYDDD-style
    day-of-year representation in its database format.

    Also accepts ordinary datetime-like values.
    """

    if pd.isna(value):
        return pd.NaT

    value = str(value).strip()

    # YYYYDDD
    if re.fullmatch(r"\d{7}", value):

        try:
            year = int(value[:4])
            day = int(value[4:])

            return (
                pd.Timestamp(f"{year}-01-01")
                +
                pd.Timedelta(days=day - 1)
            )

        except Exception:
            pass

    # Normal datetime/date formats
    try:
        return pd.to_datetime(value)
    except Exception:
        return pd.NaT


# ============================================================
# Load BYU
# ============================================================

def load_byu():

    if not BYU_ZIP.exists():

        raise FileNotFoundError(
            f"BYU database not found: {BYU_ZIP}"
        )

    records = []

    with zipfile.ZipFile(BYU_ZIP, "r") as z:

        csv_files = [
            name
            for name in z.namelist()
            if name.lower().endswith(".csv")
        ]

        print(
            f"BYU CSV files found: "
            f"{len(csv_files)}"
        )

        for name in csv_files:

            try:

                with z.open(name) as f:

                    df = pd.read_csv(f)

            except Exception as exc:

                print(
                    f"Skipping {name}: {exc}"
                )
                continue

            if df.empty:
                continue

            date_col = find_column(
                df.columns,
                [
                    "date",
                    "day",
                    "datetime"
                ]
            )

            lat_col = find_column(
                df.columns,
                [
                    "latitude",
                    "lat",
                    "mean_latitude",
                    "meanlat"
                ]
            )

            lon_col = find_column(
                df.columns,
                [
                    "longitude",
                    "lon",
                    "mean_longitude",
                    "meanlon"
                ]
            )

            if not all(
                [
                    date_col,
                    lat_col,
                    lon_col
                ]
            ):

                continue

            iceberg_id = Path(name).stem

            temp = pd.DataFrame({

                "iceberg_id": iceberg_id,

                "timestamp": df[date_col].apply(
                    parse_byu_date
                ),

                "latitude": pd.to_numeric(
                    df[lat_col],
                    errors="coerce"
                ),

                "longitude": pd.to_numeric(
                    df[lon_col],
                    errors="coerce"
                )
            })

            temp = temp.dropna(
                subset=[
                    "timestamp",
                    "latitude",
                    "longitude"
                ]
            )

            records.append(temp)

    if not records:

        raise RuntimeError(
            "No usable BYU position records found."
        )

    result = pd.concat(
        records,
        ignore_index=True
    )

    result = result.sort_values(
        [
            "iceberg_id",
            "timestamp"
        ]
    )

    result = result.drop_duplicates(
        subset=[
            "iceberg_id",
            "timestamp"
        ]
    )

    return result


# ============================================================
# Build 24-hour pairs
# ============================================================

def build_pairs(byu, windows):

    pairs = []

    for _, window in windows.iterrows():

        iceberg_id = str(
            window["iceberg_id"]
        )

        start = pd.Timestamp(
            window["start"]
        )

        end = pd.Timestamp(
            window["end"]
        )

        track = byu[
            byu["iceberg_id"]
            .str.lower()
            ==
            iceberg_id.lower()
        ].copy()

        track = track[
            (track["timestamp"] >= start)
            &
            (track["timestamp"] <= end)
        ].sort_values("timestamp")

        if track.empty:

            print(
                f"WARNING: no BYU data for "
                f"{iceberg_id}"
            )

            continue

        track = track.reset_index(
            drop=True
        )

        for i, row in track.iterrows():

            target_time = (
                row["timestamp"]
                +
                pd.Timedelta(hours=24)
            )

            future = track[
                track["timestamp"]
                == target_time
            ]

            if future.empty:
                continue

            target = future.iloc[0]

            start_lon = float(
                row["longitude"]
            )

            start_lat = float(
                row["latitude"]
            )

            end_lon = float(
                target["longitude"]
            )

            end_lat = float(
                target["latitude"]
            )

            azimuth, _, distance = GEOD.inv(
                start_lon,
                start_lat,
                end_lon,
                end_lat
            )

            duration_seconds = 24 * 3600

            distance_m = float(distance)

            # Convert geodesic displacement to
            # east/north velocity components.
            azimuth_rad = np.radians(
                azimuth
            )

            east_displacement_m = (
                distance_m *
                np.sin(azimuth_rad)
            )

            north_displacement_m = (
                distance_m *
                np.cos(azimuth_rad)
            )

            observed_u = (
                east_displacement_m /
                duration_seconds
            )

            observed_v = (
                north_displacement_m /
                duration_seconds
            )

            observed_speed = (
                np.sqrt(
                    observed_u ** 2
                    +
                    observed_v ** 2
                )
            )

            pairs.append({

                "iceberg_id":
                    iceberg_id,

                "start_time":
                    row["timestamp"],

                "end_time":
                    target["timestamp"],

                "start_latitude":
                    start_lat,

                "start_longitude":
                    start_lon,

                "observed_latitude":
                    end_lat,

                "observed_longitude":
                    end_lon,

                "displacement_m":
                    distance_m,

                "displacement_km":
                    distance_m / 1000.0,

                "azimuth_deg":
                    float(azimuth),

                "observed_u":
                    float(observed_u),

                "observed_v":
                    float(observed_v),

                "observed_speed":
                    float(observed_speed),

                "duration_hours":
                    24.0
            })

    return pd.DataFrame(pairs)


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 70)
    print("BUILDING BYU CALIBRATION OBSERVATIONS")
    print("=" * 70)

    print("\nLoading selected windows...")

    windows = pd.read_csv(
        WINDOWS_FILE
    )

    print(
        f"Selected windows: "
        f"{len(windows)}"
    )

    print(
        f"Expected candidate pairs: "
        f"{len(windows) * 7}"
    )

    print("\nLoading BYU database...")

    byu = load_byu()

    print(
        f"BYU observations loaded: "
        f"{len(byu):,}"
    )

    print(
        f"Unique icebergs: "
        f"{byu['iceberg_id'].nunique():,}"
    )

    print(
        f"Date range: "
        f"{byu['timestamp'].min()} "
        f"-> "
        f"{byu['timestamp'].max()}"
    )

    print("\nBuilding 24-hour pairs...")

    pairs = build_pairs(
        byu,
        windows
    )

    if pairs.empty:

        raise RuntimeError(
            "No calibration pairs were generated."
        )

    pairs = pairs.sort_values(
        [
            "iceberg_id",
            "start_time"
        ]
    ).reset_index(
        drop=True
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    pairs.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n" + "=" * 70)
    print("CALIBRATION OBSERVATIONS CREATED")
    print("=" * 70)

    print(
        f"Pairs created: "
        f"{len(pairs)}"
    )

    print(
        f"Icebergs represented: "
        f"{pairs['iceberg_id'].nunique()}"
    )

    print(
        f"Output: "
        f"{OUTPUT_FILE}"
    )

    print("\nPairs per iceberg:")

    print(
        pairs.groupby("iceberg_id")
        .size()
        .to_string()
    )


if __name__ == "__main__":
    main()