from pathlib import Path
import math
import numpy as np
import pandas as pd
from pyproj import Geod


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data/catalog/calibration_dataset.csv"
OUTPUT_FILE = ROOT / "data/catalog/baseline_evaluation.csv"
SUMMARY_FILE = ROOT / "data/catalog/baseline_summary.csv"

OCEAN_WEIGHT = 0.85
WIND_WEIGHT = 0.015

EARTH = Geod(ellps="WGS84")


def destination(lat, lon, u, v, hours):
    """
    Propagate a position using eastward (u) and northward (v)
    velocity in m/s for the specified number of hours.
    """

    distance = math.sqrt(u ** 2 + v ** 2) * hours * 3600.0

    if distance == 0:
        return lat, lon

    azimuth = math.degrees(math.atan2(u, v))

    lon2, lat2, _ = EARTH.fwd(
        lon,
        lat,
        azimuth,
        distance
    )

    return lat2, lon2


def geodesic_error(lat1, lon1, lat2, lon2):
    """
    Calculate geodesic distance between predicted and observed
    positions in meters.
    """

    _, _, distance = EARTH.inv(
        lon1,
        lat1,
        lon2,
        lat2
    )

    return float(distance)


def calculate_metrics(errors_km):
    """
    Calculate the required error metrics.
    """

    errors = np.asarray(errors_km, dtype=float)

    return {
        "mean_error_km": float(np.mean(errors)),
        "median_error_km": float(np.median(errors)),
        "rmse_km": float(np.sqrt(np.mean(errors ** 2))),
        "p90_error_km": float(np.percentile(errors, 90)),
        "max_error_km": float(np.max(errors)),
    }


def main():

    print("=" * 70)
    print("BASELINE DRIFT EVALUATION")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Calibration dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    print(f"\nInput rows: {len(df)}")

    results = []

    for _, row in df.iterrows():

        iceberg_id = row["iceberg_id"]

        start_lat = float(row["start_latitude"])
        start_lon = float(row["start_longitude"])

        observed_lat = float(row["observed_latitude"])
        observed_lon = float(row["observed_longitude"])

        ocean_u = float(row["ocean_u"])
        ocean_v = float(row["ocean_v"])

        wind_u = float(row["wind_u"])
        wind_v = float(row["wind_v"])

        duration_hours = (
            row["end_time"] - row["start_time"]
        ).total_seconds() / 3600.0

        # --------------------------------------------------------
        # Persistence
        # --------------------------------------------------------

        persistence_lat = start_lat
        persistence_lon = start_lon

        persistence_error = geodesic_error(
            persistence_lat,
            persistence_lon,
            observed_lat,
            observed_lon
        )

        # --------------------------------------------------------
        # Existing physics baseline
        # --------------------------------------------------------

        baseline_u = (
            OCEAN_WEIGHT * ocean_u
            + WIND_WEIGHT * wind_u
        )

        baseline_v = (
            OCEAN_WEIGHT * ocean_v
            + WIND_WEIGHT * wind_v
        )

        baseline_lat, baseline_lon = destination(
            start_lat,
            start_lon,
            baseline_u,
            baseline_v,
            duration_hours
        )

        baseline_error = geodesic_error(
            baseline_lat,
            baseline_lon,
            observed_lat,
            observed_lon
        )

        # --------------------------------------------------------
        # Observed displacement
        # --------------------------------------------------------

        observed_displacement = geodesic_error(
            start_lat,
            start_lon,
            observed_lat,
            observed_lon
        )

        results.append({
            "iceberg_id": iceberg_id,
            "start_time": row["start_time"],
            "end_time": row["end_time"],

            "start_latitude": start_lat,
            "start_longitude": start_lon,

            "observed_latitude": observed_lat,
            "observed_longitude": observed_lon,

            "observed_displacement_km":
                observed_displacement / 1000.0,

            "ocean_u": ocean_u,
            "ocean_v": ocean_v,

            "wind_u": wind_u,
            "wind_v": wind_v,

            "baseline_u": baseline_u,
            "baseline_v": baseline_v,

            "persistence_latitude": persistence_lat,
            "persistence_longitude": persistence_lon,

            "baseline_latitude": baseline_lat,
            "baseline_longitude": baseline_lon,

            "persistence_error_km":
                persistence_error / 1000.0,

            "baseline_error_km":
                baseline_error / 1000.0,
        })

    results_df = pd.DataFrame(results)

    # ------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------

    persistence_metrics = calculate_metrics(
        results_df["persistence_error_km"]
    )

    baseline_metrics = calculate_metrics(
        results_df["baseline_error_km"]
    )

    persistence_mean = persistence_metrics["mean_error_km"]
    baseline_mean = baseline_metrics["mean_error_km"]

    persistence_rmse = persistence_metrics["rmse_km"]
    baseline_rmse = baseline_metrics["rmse_km"]

    if persistence_mean > 0:
        mean_skill = (
            1.0
            - baseline_mean / persistence_mean
        )
    else:
        mean_skill = np.nan

    if persistence_rmse > 0:
        rmse_skill = (
            1.0
            - baseline_rmse / persistence_rmse
        )
    else:
        rmse_skill = np.nan

    summary = pd.DataFrame([
        {
            "model": "persistence",
            **persistence_metrics,
            "mean_skill_vs_persistence": 0.0,
            "rmse_skill_vs_persistence": 0.0,
        },
        {
            "model": "baseline_alpha_0.85_beta_0.015",
            **baseline_metrics,
            "mean_skill_vs_persistence": mean_skill,
            "rmse_skill_vs_persistence": rmse_skill,
        },
    ])

    # ------------------------------------------------------------
    # Save
    # ------------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    results_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False
    )

    # ------------------------------------------------------------
    # Print results
    # ------------------------------------------------------------

    print("\n" + "=" * 70)
    print("BASELINE RESULTS")
    print("=" * 70)

    print("\nPersistence:")
    for key, value in persistence_metrics.items():
        print(f"  {key:<25}: {value:.4f}")

    print("\nExisting physics baseline:")
    print(f"  alpha                    : {OCEAN_WEIGHT}")
    print(f"  beta                     : {WIND_WEIGHT}")

    for key, value in baseline_metrics.items():
        print(f"  {key:<25}: {value:.4f}")

    print("\nSkill vs persistence:")
    print(f"  Mean-error skill         : {mean_skill:.4f}")
    print(f"  RMSE skill               : {rmse_skill:.4f}")

    # ------------------------------------------------------------
    # Per-iceberg results
    # ------------------------------------------------------------

    print("\n" + "=" * 70)
    print("PER-ICEBERG PERFORMANCE")
    print("=" * 70)

    iceberg_summary = (
        results_df
        .groupby("iceberg_id")
        .agg(
            pairs=("iceberg_id", "size"),
            persistence_mean_km=(
                "persistence_error_km",
                "mean"
            ),
            baseline_mean_km=(
                "baseline_error_km",
                "mean"
            ),
            persistence_rmse_km=(
                "persistence_error_km",
                lambda x: np.sqrt(np.mean(x ** 2))
            ),
            baseline_rmse_km=(
                "baseline_error_km",
                lambda x: np.sqrt(np.mean(x ** 2))
            ),
        )
        .reset_index()
    )

    iceberg_summary["mean_skill_vs_persistence"] = (
        1.0
        - iceberg_summary["baseline_mean_km"]
        / iceberg_summary["persistence_mean_km"]
    )

    print(
        iceberg_summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    print("\n" + "=" * 70)
    print("FILES SAVED")
    print("=" * 70)

    print(f"\nDetailed results:")
    print(OUTPUT_FILE)

    print(f"\nSummary:")
    print(SUMMARY_FILE)

    print("\n" + "=" * 70)
    print("BASELINE EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()