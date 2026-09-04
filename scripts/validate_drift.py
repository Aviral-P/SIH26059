from pathlib import Path
import sys

import pandas as pd
from pyproj import Geod


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts.drift_engine import (
    predict_position,
    integrated_predict_position,
)


EARTH = Geod(ellps="WGS84")


# ---------------------------------------------------------
# Historical BYU trajectory — d29c
# ---------------------------------------------------------

TRACK = [
    {
        "timestamp": "2023-07-21T00:00:00",
        "lat": -63.314,
        "lon": -47.283,
    },
    {
        "timestamp": "2023-07-22T00:00:00",
        "lat": -63.177,
        "lon": -46.099,
    },
    {
        "timestamp": "2023-07-23T00:00:00",
        "lat": -63.094,
        "lon": -45.991,
    },
    {
        "timestamp": "2023-07-24T00:00:00",
        "lat": -63.040,
        "lon": -45.798,
    },
]


# ---------------------------------------------------------
# Great-circle distance
# ---------------------------------------------------------

def distance_km(lat1, lon1, lat2, lon2):

    _, _, distance_m = EARTH.inv(
        lon1,
        lat1,
        lon2,
        lat2,
    )

    return distance_m / 1000.0


# ---------------------------------------------------------
# Main validation
# ---------------------------------------------------------

def main():

    results = []

    print()
    print("=" * 100)
    print("ANTARCTIC ICEBERG DRIFT — V1 vs V2 HISTORICAL VALIDATION")
    print("=" * 100)

    for i in range(len(TRACK) - 1):

        start = TRACK[i]
        actual = TRACK[i + 1]

        timestamp = pd.Timestamp(
            start["timestamp"]
        )

        print()
        print("=" * 100)

        print(
            f"FORECAST {i + 1}: "
            f"{start['timestamp']} -> "
            f"{actual['timestamp']}"
        )

        print("=" * 100)

        # -------------------------------------------------
        # Persistence baseline
        # -------------------------------------------------

        persistence_error = distance_km(
            start["lat"],
            start["lon"],
            actual["lat"],
            actual["lon"],
        )

        # -------------------------------------------------
        # V1 — snapshot model
        # -------------------------------------------------

        print()
        print("Running V1 snapshot model...")

        v1 = predict_position(
            latitude=start["lat"],
            longitude=start["lon"],
            timestamp=timestamp,
            forecast_hours=24,
            validation=True,
        )

        v1_error = distance_km(
            v1["predicted_latitude"],
            v1["predicted_longitude"],
            actual["lat"],
            actual["lon"],
        )

        # -------------------------------------------------
        # V2 — time-integrated model
        # -------------------------------------------------

        print()
        print("Running V2 integrated model...")

        v2 = integrated_predict_position(
            latitude=start["lat"],
            longitude=start["lon"],
            timestamp=timestamp,
            forecast_hours=24,
            step_hours=6,
            validation=True,
        )

        v2_error = distance_km(
            v2["predicted_latitude"],
            v2["predicted_longitude"],
            actual["lat"],
            actual["lon"],
        )

        # -------------------------------------------------
        # Improvement relative to persistence
        # -------------------------------------------------

        v1_improvement = (
            (persistence_error - v1_error)
            / persistence_error
            * 100
            if persistence_error > 0
            else 0
        )

        v2_improvement = (
            (persistence_error - v2_error)
            / persistence_error
            * 100
            if persistence_error > 0
            else 0
        )

        # -------------------------------------------------
        # V2 improvement over V1
        # -------------------------------------------------

        v2_vs_v1 = (
            (v1_error - v2_error)
            / v1_error
            * 100
            if v1_error > 0
            else 0
        )

        # -------------------------------------------------
        # Print results
        # -------------------------------------------------

        print()
        print("INITIAL POSITION")
        print(
            f"  {start['lat']:.5f}, "
            f"{start['lon']:.5f}"
        )

        print()
        print("ACTUAL POSITION")
        print(
            f"  {actual['lat']:.5f}, "
            f"{actual['lon']:.5f}"
        )

        print()
        print("V1 SNAPSHOT")
        print(
            f"  Predicted: "
            f"{v1['predicted_latitude']:.5f}, "
            f"{v1['predicted_longitude']:.5f}"
        )

        print(
            f"  Error: {v1_error:.3f} km"
        )

        print()
        print("V2 INTEGRATED")
        print(
            f"  Predicted: "
            f"{v2['predicted_latitude']:.5f}, "
            f"{v2['predicted_longitude']:.5f}"
        )

        print(
            f"  Error: {v2_error:.3f} km"
        )

        print()
        print("PERSISTENCE")
        print(
            f"  Error: {persistence_error:.3f} km"
        )

        print()
        print("COMPARISON")
        print("-" * 60)

        print(
            f"  V1 improvement vs persistence : "
            f"{v1_improvement:+.2f}%"
        )

        print(
            f"  V2 improvement vs persistence : "
            f"{v2_improvement:+.2f}%"
        )

        print(
            f"  V2 improvement vs V1          : "
            f"{v2_vs_v1:+.2f}%"
        )

        results.append({
            "forecast": i + 1,
            "start": start["timestamp"],
            "actual": actual["timestamp"],
            "v1_error_km": v1_error,
            "v2_error_km": v2_error,
            "persistence_error_km": persistence_error,
            "v1_improvement_vs_persistence_pct":
                v1_improvement,
            "v2_improvement_vs_persistence_pct":
                v2_improvement,
            "v2_improvement_vs_v1_pct":
                v2_vs_v1,
        })

    # -----------------------------------------------------
    # Aggregate results
    # -----------------------------------------------------

    df = pd.DataFrame(results)

    print()
    print()
    print("=" * 100)
    print("FINAL VALIDATION SUMMARY")
    print("=" * 100)

    print()
    print(
        f"Forecasts evaluated : "
        f"{len(df)}"
    )

    print()
    print(
        f"V1 mean error       : "
        f"{df['v1_error_km'].mean():.3f} km"
    )

    print(
        f"V2 mean error       : "
        f"{df['v2_error_km'].mean():.3f} km"
    )

    print(
        f"Persistence mean    : "
        f"{df['persistence_error_km'].mean():.3f} km"
    )

    print()
    print(
        f"V1 median error     : "
        f"{df['v1_error_km'].median():.3f} km"
    )

    print(
        f"V2 median error     : "
        f"{df['v2_error_km'].median():.3f} km"
    )

    print()
    print(
        f"V1 maximum error    : "
        f"{df['v1_error_km'].max():.3f} km"
    )

    print(
        f"V2 maximum error    : "
        f"{df['v2_error_km'].max():.3f} km"
    )

    print()
    print(
        f"V2 vs V1 improvement: "
        f"{(df['v1_error_km'].mean() - df['v2_error_km'].mean()) / df['v1_error_km'].mean() * 100:+.2f}%"
    )

    print()
    print("-" * 100)

    print(df.to_string(index=False))

    print()
    print("=" * 100)


if __name__ == "__main__":
    main()