from pathlib import Path
import sys
import math

import pandas as pd
import psycopg2
from pyproj import Geod


ROOT = Path(__file__).resolve().parents[1]

sys.path.append(str(ROOT))


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "antarctic_nav",
    "user": "antarctic",
    "password": "antarctic_dev_password",
}

GEOD = Geod(ellps="WGS84")


def connect_db():
    return psycopg2.connect(**DB_CONFIG)


def get_track_observations(iceberg_id):
    """
    Fetch observations for one real BYU iceberg track.
    """

    query = """
        SELECT
            iceberg_id,
            observed_at,
            latitude,
            longitude,
            displacement_km,
            velocity_angle_deg
        FROM iceberg_trajectories
        WHERE source = 'BYU_STATS_V7.1'
          AND iceberg_id = %s
        ORDER BY observed_at ASC;
    """

    with connect_db() as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params=(iceberg_id,)
        )

    return df


def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Great-circle distance in kilometers.
    """

    _, _, distance_m = GEOD.inv(
        lon1,
        lat1,
        lon2,
        lat2
    )

    return distance_m / 1000.0


def build_validation_pairs(df):
    """
    Build consecutive observation pairs.

    Each pair represents:

        T0 → T1

    and therefore gives us actual observed movement.
    """

    records = []

    for i in range(len(df) - 1):

        current = df.iloc[i]
        next_obs = df.iloc[i + 1]

        t0 = pd.Timestamp(
            current["observed_at"]
        )

        t1 = pd.Timestamp(
            next_obs["observed_at"]
        )

        delta_hours = (
            t1 - t0
        ).total_seconds() / 3600.0

        if delta_hours <= 0:
            continue

        distance_km = calculate_distance(
            current["latitude"],
            current["longitude"],
            next_obs["latitude"],
            next_obs["longitude"]
        )

        records.append({
            "iceberg_id": current["iceberg_id"],

            "t0": t0,
            "t1": t1,

            "lat0": current["latitude"],
            "lon0": current["longitude"],

            "lat1": next_obs["latitude"],
            "lon1": next_obs["longitude"],

            "delta_hours": delta_hours,

            "observed_displacement_km": distance_km
        })

    return pd.DataFrame(records)


def summarize_validation(df):
    """
    Basic statistics describing observed movement.
    """

    if df.empty:
        return {}

    return {
        "pairs": len(df),

        "median_interval_hours":
            df["delta_hours"].median(),

        "mean_interval_hours":
            df["delta_hours"].mean(),

        "median_displacement_km":
            df["observed_displacement_km"].median(),

        "mean_displacement_km":
            df["observed_displacement_km"].mean(),

        "max_displacement_km":
            df["observed_displacement_km"].max()
    }
    
def find_24h_windows(df, tolerance_hours=1):
    """
    Find consecutive observations separated by approximately 24h.
    """

    pairs = build_validation_pairs(df)

    if pairs.empty:
        return pairs

    return pairs[
        (pairs["delta_hours"] >= 24 - tolerance_hours) &
        (pairs["delta_hours"] <= 24 + tolerance_hours)
    ].copy()


def main():

    # Start with a known long BYU track.
    iceberg_id = "b09b"

    print()
    print("=" * 70)
    print("BYU ICEBERG VALIDATION PIPELINE")
    print("=" * 70)

    print()
    print(f"Loading iceberg: {iceberg_id}")

    observations = get_track_observations(
        iceberg_id
    )

    print(
        f"Observations loaded: "
        f"{len(observations)}"
    )

    if observations.empty:
        raise RuntimeError(
            f"No BYU observations found for {iceberg_id}"
        )

    print()
    print("Track:")
    print("-" * 70)

    print(
        f"Start: "
        f"{observations['observed_at'].min()}"
    )

    print(
        f"End:   "
        f"{observations['observed_at'].max()}"
    )

    # ---------------------------------------------------------
    # Build all consecutive observation pairs
    # ---------------------------------------------------------

    print()
    print("Building observation pairs...")

    pairs = build_validation_pairs(
        observations
    )

    print(
        f"Validation pairs: "
        f"{len(pairs)}"
    )

    summary = summarize_validation(
        pairs
    )

    print()
    print("OBSERVED MOVEMENT")
    print("-" * 70)

    for key, value in summary.items():

        if isinstance(value, float):
            print(
                f"{key:30s}: "
                f"{value:.3f}"
            )
        else:
            print(
                f"{key:30s}: "
                f"{value}"
            )

    print()
    print("FIRST 5 VALIDATION PAIRS")
    print("-" * 70)

    print(
        pairs.head(5).to_string(
            index=False
        )
    )

    # ---------------------------------------------------------
    # Find approximately 24-hour validation windows
    # ---------------------------------------------------------

    print()
    print("24-HOUR VALIDATION WINDOWS")
    print("-" * 70)

    windows = find_24h_windows(
        observations,
        tolerance_hours=1
    )

    print(
        f"24h-compatible pairs: "
        f"{len(windows)}"
    )

    if not windows.empty:

        print()
        print(
            windows[
                [
                    "t0",
                    "t1",
                    "lat0",
                    "lon0",
                    "lat1",
                    "lon1",
                    "delta_hours",
                    "observed_displacement_km"
                ]
            ]
            .head(20)
            .to_string(index=False)
        )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()