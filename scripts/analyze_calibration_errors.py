from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Geod


ROOT = Path(__file__).resolve().parents[1]

DATASET_FILE = (
    ROOT / "data" / "catalog" / "calibration_dataset.csv"
)

LOIO_FILE = (
    ROOT / "data" / "catalog" /
    "leave_one_iceberg_out_evaluation.csv"
)

OUTPUT_FILE = (
    ROOT / "data" / "catalog" /
    "calibration_error_analysis.csv"
)

ICEBERG_FILE = (
    ROOT / "data" / "catalog" /
    "calibration_error_by_iceberg.csv"
)

WORST_FILE = (
    ROOT / "data" / "catalog" /
    "calibration_worst_cases.csv"
)

GEOD = Geod(ellps="WGS84")


def vector_speed(u, v):
    return np.sqrt(u**2 + v**2)


def vector_direction(u, v):
    """
    Direction clockwise from north.
    """

    return (
        np.degrees(np.arctan2(u, v)) + 360
    ) % 360


def angular_difference(a, b):
    """
    Smallest absolute angular difference in degrees.
    """

    difference = np.abs(a - b)

    return np.minimum(
        difference,
        360 - difference
    )


def destination(lat, lon, u, v, hours):
    speed = vector_speed(u, v)

    if speed == 0:
        return lat, lon

    azimuth = vector_direction(u, v)

    distance_m = speed * hours * 3600.0

    lon2, lat2, _ = GEOD.fwd(
        lon,
        lat,
        azimuth,
        distance_m
    )

    return lat2, lon2


def geodesic_error(lat1, lon1, lat2, lon2):
    _, _, distance_m = GEOD.inv(
        lon1,
        lat1,
        lon2,
        lat2
    )

    return distance_m / 1000.0


def main():

    print("=" * 70)
    print("CALIBRATION ERROR ANALYSIS")
    print("=" * 70)

    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{DATASET_FILE}"
        )

    if not LOIO_FILE.exists():
        raise FileNotFoundError(
            f"LOIO evaluation file not found:\n{LOIO_FILE}"
        )

    df = pd.read_csv(DATASET_FILE)
    loio = pd.read_csv(LOIO_FILE)

    print(f"\nCalibration rows: {len(df)}")
    print(f"LOIO rows: {len(loio)}")

    # =========================================================
    # MERGE ENVIRONMENT + LOIO RESULTS
    # =========================================================

    merge_columns = [
        "iceberg_id",
        "start_time",
        "end_time"
    ]

    analysis = df.merge(
        loio,
        on=merge_columns,
        how="inner",
        validate="one_to_one"
    )

    if len(analysis) != len(df):
        raise ValueError(
            "LOIO results do not match calibration dataset exactly."
        )

    print(f"Merged rows: {len(analysis)}")

    # =========================================================
    # ENVIRONMENTAL SPEEDS
    # =========================================================

    analysis["ocean_speed_mps"] = vector_speed(
        analysis["ocean_u"],
        analysis["ocean_v"]
    )

    analysis["wind_speed_mps"] = vector_speed(
        analysis["wind_u"],
        analysis["wind_v"]
    )

    analysis["observed_speed_mps"] = vector_speed(
        analysis["observed_u"],
        analysis["observed_v"]
    )

    # =========================================================
    # DIRECTIONS
    # =========================================================

    analysis["observed_direction_deg"] = vector_direction(
        analysis["observed_u"],
        analysis["observed_v"]
    )

    # Use the fold-specific alpha/beta from LOIO
    analysis["predicted_u_mps"] = (
        analysis["alpha"]
        * analysis["ocean_u"]
        +
        analysis["beta"]
        * analysis["wind_u"]
    )

    analysis["predicted_v_mps"] = (
        analysis["alpha"]
        * analysis["ocean_v"]
        +
        analysis["beta"]
        * analysis["wind_v"]
    )

    analysis["predicted_speed_mps"] = vector_speed(
        analysis["predicted_u_mps"],
        analysis["predicted_v_mps"]
    )

    analysis["predicted_direction_deg"] = vector_direction(
        analysis["predicted_u_mps"],
        analysis["predicted_v_mps"]
    )

    analysis["direction_error_deg"] = angular_difference(
        analysis["predicted_direction_deg"],
        analysis["observed_direction_deg"]
    )

    # =========================================================
    # SPEED ERROR
    # =========================================================

    analysis["speed_error_mps"] = (
        analysis["predicted_speed_mps"]
        - analysis["observed_speed_mps"]
    )

    analysis["absolute_speed_error_mps"] = np.abs(
        analysis["speed_error_mps"]
    )

    # =========================================================
    # OCEAN / WIND CONTRIBUTIONS
    # =========================================================

    analysis["ocean_contribution_speed_mps"] = (
        analysis["alpha"]
        * analysis["ocean_speed_mps"]
    )

    analysis["wind_contribution_speed_mps"] = (
        analysis["beta"]
        * analysis["wind_speed_mps"]
    )

    # =========================================================
    # MODEL IMPROVEMENT
    # =========================================================

    analysis["improvement_vs_persistence_km"] = (
        analysis["persistence_error_km"]
        -
        analysis["calibrated_error_km"]
    )

    analysis["calibrated_better_than_persistence"] = (
        analysis["calibrated_error_km"]
        <
        analysis["persistence_error_km"]
    )

    analysis["calibrated_better_than_baseline"] = (
        analysis["calibrated_error_km"]
        <
        analysis["baseline_error_km"]
    )

    # =========================================================
    # ENVIRONMENTAL REGIMES
    # =========================================================

    analysis["ocean_speed_regime"] = pd.cut(
        analysis["ocean_speed_mps"],
        bins=[
            -np.inf,
            0.05,
            0.10,
            0.20,
            np.inf
        ],
        labels=[
            "<0.05",
            "0.05-0.10",
            "0.10-0.20",
            ">0.20"
        ]
    )

    analysis["wind_speed_regime"] = pd.cut(
        analysis["wind_speed_mps"],
        bins=[
            -np.inf,
            3,
            6,
            10,
            np.inf
        ],
        labels=[
            "<3",
            "3-6",
            "6-10",
            ">10"
        ]
    )

    analysis["observed_speed_regime"] = pd.cut(
        analysis["observed_speed_mps"],
        bins=[
            -np.inf,
            0.03,
            0.07,
            0.12,
            np.inf
        ],
        labels=[
            "<0.03",
            "0.03-0.07",
            "0.07-0.12",
            ">0.12"
        ]
    )

    # =========================================================
    # OVERALL SUMMARY
    # =========================================================

    print("\n" + "=" * 70)
    print("OVERALL ERROR ANALYSIS")
    print("=" * 70)

    print(
        f"\nMean calibrated error: "
        f"{analysis['calibrated_error_km'].mean():.4f} km"
    )

    print(
        f"Median calibrated error: "
        f"{analysis['calibrated_error_km'].median():.4f} km"
    )

    print(
        f"RMSE calibrated error: "
        f"{np.sqrt(np.mean(analysis['calibrated_error_km'] ** 2)):.4f} km"
    )

    print(
        f"P90 calibrated error: "
        f"{analysis['calibrated_error_km'].quantile(0.90):.4f} km"
    )

    print(
        f"Maximum calibrated error: "
        f"{analysis['calibrated_error_km'].max():.4f} km"
    )

    print(
        f"\nMean observed iceberg speed: "
        f"{analysis['observed_speed_mps'].mean():.5f} m/s"
    )

    print(
        f"Mean ocean speed: "
        f"{analysis['ocean_speed_mps'].mean():.5f} m/s"
    )

    print(
        f"Mean wind speed: "
        f"{analysis['wind_speed_mps'].mean():.5f} m/s"
    )

    # =========================================================
    # WIN / LOSS COUNT
    # =========================================================

    wins = (
        analysis["calibrated_better_than_persistence"]
        .sum()
    )

    losses = len(analysis) - wins

    print("\n" + "-" * 70)
    print("CALIBRATED MODEL VS PERSISTENCE")
    print("-" * 70)

    print(f"Pairs where calibrated model wins : {wins}")
    print(f"Pairs where persistence wins      : {losses}")
    print(
        f"Win percentage                   : "
        f"{wins / len(analysis) * 100:.2f}%"
    )

    # =========================================================
    # PER-ICEBERG ANALYSIS
    # =========================================================

    iceberg_rows = []

    for iceberg_id, group in analysis.groupby(
        "iceberg_id",
        sort=True
    ):

        persistence = group[
            "persistence_error_km"
        ]

        calibrated = group[
            "calibrated_error_km"
        ]

        baseline = group[
            "baseline_error_km"
        ]

        mean_persistence = persistence.mean()
        mean_calibrated = calibrated.mean()

        rmse_persistence = np.sqrt(
            np.mean(persistence ** 2)
        )

        rmse_calibrated = np.sqrt(
            np.mean(calibrated ** 2)
        )

        iceberg_rows.append({
            "iceberg_id": iceberg_id,
            "pairs": len(group),

            "mean_ocean_speed_mps":
                group["ocean_speed_mps"].mean(),

            "mean_wind_speed_mps":
                group["wind_speed_mps"].mean(),

            "mean_observed_speed_mps":
                group["observed_speed_mps"].mean(),

            "persistence_mean_error_km":
                mean_persistence,

            "calibrated_mean_error_km":
                mean_calibrated,

            "baseline_mean_error_km":
                baseline.mean(),

            "persistence_rmse_km":
                rmse_persistence,

            "calibrated_rmse_km":
                rmse_calibrated,

            "mean_skill_vs_persistence":
                1 - (
                    mean_calibrated
                    / mean_persistence
                ),

            "rmse_skill_vs_persistence":
                1 - (
                    rmse_calibrated
                    / rmse_persistence
                ),

            "pairs_calibrated_better":
                group[
                    "calibrated_better_than_persistence"
                ].sum(),

            "pairs_calibrated_worse":
                (
                    ~group[
                        "calibrated_better_than_persistence"
                    ]
                ).sum(),

            "mean_direction_error_deg":
                group["direction_error_deg"].mean(),

            "mean_speed_error_mps":
                group["speed_error_mps"].mean()
        })

    iceberg_df = pd.DataFrame(
        iceberg_rows
    )

    print("\n" + "=" * 70)
    print("PER-ICEBERG ERROR ANALYSIS")
    print("=" * 70)

    print(
        iceberg_df.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # =========================================================
    # ERROR BY OCEAN SPEED
    # =========================================================

    print("\n" + "=" * 70)
    print("ERROR BY OCEAN SPEED")
    print("=" * 70)

    ocean_summary = (
        analysis
        .groupby(
            "ocean_speed_regime",
            observed=True
        )
        .agg(
            pairs=("calibrated_error_km", "size"),
            mean_error_km=(
                "calibrated_error_km",
                "mean"
            ),
            persistence_error_km=(
                "persistence_error_km",
                "mean"
            ),
            ocean_speed_mps=(
                "ocean_speed_mps",
                "mean"
            )
        )
        .reset_index()
    )

    ocean_summary["skill_vs_persistence"] = (
        1
        -
        ocean_summary["mean_error_km"]
        /
        ocean_summary["persistence_error_km"]
    )

    print(
        ocean_summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # =========================================================
    # ERROR BY WIND SPEED
    # =========================================================

    print("\n" + "=" * 70)
    print("ERROR BY WIND SPEED")
    print("=" * 70)

    wind_summary = (
        analysis
        .groupby(
            "wind_speed_regime",
            observed=True
        )
        .agg(
            pairs=("calibrated_error_km", "size"),
            mean_error_km=(
                "calibrated_error_km",
                "mean"
            ),
            persistence_error_km=(
                "persistence_error_km",
                "mean"
            ),
            wind_speed_mps=(
                "wind_speed_mps",
                "mean"
            )
        )
        .reset_index()
    )

    wind_summary["skill_vs_persistence"] = (
        1
        -
        wind_summary["mean_error_km"]
        /
        wind_summary["persistence_error_km"]
    )

    print(
        wind_summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # =========================================================
    # ERROR BY OBSERVED ICEBERG SPEED
    # =========================================================

    print("\n" + "=" * 70)
    print("ERROR BY OBSERVED ICEBERG SPEED")
    print("=" * 70)

    observed_summary = (
        analysis
        .groupby(
            "observed_speed_regime",
            observed=True
        )
        .agg(
            pairs=("calibrated_error_km", "size"),
            mean_error_km=(
                "calibrated_error_km",
                "mean"
            ),
            persistence_error_km=(
                "persistence_error_km",
                "mean"
            ),
            observed_speed_mps=(
                "observed_speed_mps",
                "mean"
            )
        )
        .reset_index()
    )

    observed_summary["skill_vs_persistence"] = (
        1
        -
        observed_summary["mean_error_km"]
        /
        observed_summary["persistence_error_km"]
    )

    print(
        observed_summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # =========================================================
    # DIRECTION AND SPEED ERRORS
    # =========================================================

    print("\n" + "=" * 70)
    print("VECTOR ERROR ANALYSIS")
    print("=" * 70)

    print(
        f"\nMean direction error : "
        f"{analysis['direction_error_deg'].mean():.2f}°"
    )

    print(
        f"Median direction error : "
        f"{analysis['direction_error_deg'].median():.2f}°"
    )

    print(
        f"P90 direction error : "
        f"{analysis['direction_error_deg'].quantile(0.90):.2f}°"
    )

    print(
        f"\nMean speed bias : "
        f"{analysis['speed_error_mps'].mean():.5f} m/s"
    )

    print(
        f"Mean absolute speed error : "
        f"{analysis['absolute_speed_error_mps'].mean():.5f} m/s"
    )

    # =========================================================
    # CONTRIBUTION ANALYSIS
    # =========================================================

    print("\n" + "=" * 70)
    print("OCEAN / WIND CONTRIBUTION")
    print("=" * 70)

    mean_ocean_contribution = (
        analysis["ocean_contribution_speed_mps"].mean()
    )

    mean_wind_contribution = (
        analysis["wind_contribution_speed_mps"].mean()
    )

    print(
        f"\nMean ocean contribution : "
        f"{mean_ocean_contribution:.6f} m/s"
    )

    print(
        f"Mean wind contribution  : "
        f"{mean_wind_contribution:.6f} m/s"
    )

    if mean_ocean_contribution > 0:
        ratio = (
            mean_wind_contribution
            / mean_ocean_contribution
        )

        print(
            f"Wind/Ocean contribution ratio: "
            f"{ratio:.4f}"
        )

    # =========================================================
    # WORST CASES
    # =========================================================

    worst_cases = (
        analysis[
            [
                "iceberg_id",
                "start_time",
                "end_time",
                "ocean_speed_mps",
                "wind_speed_mps",
                "observed_speed_mps",
                "predicted_speed_mps",
                "direction_error_deg",
                "persistence_error_km",
                "baseline_error_km",
                "calibrated_error_km",
                "improvement_vs_persistence_km",
                "alpha",
                "beta"
            ]
        ]
        .sort_values(
            "calibrated_error_km",
            ascending=False
        )
        .head(10)
        .copy()
    )

    print("\n" + "=" * 70)
    print("10 WORST CALIBRATED FORECASTS")
    print("=" * 70)

    print(
        worst_cases.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # =========================================================
    # CORRELATIONS
    # =========================================================

    print("\n" + "=" * 70)
    print("ERROR CORRELATIONS")
    print("=" * 70)

    correlation_columns = [
        "calibrated_error_km",
        "persistence_error_km",
        "ocean_speed_mps",
        "wind_speed_mps",
        "observed_speed_mps",
        "direction_error_deg",
        "absolute_speed_error_mps",
        "improvement_vs_persistence_km"
    ]

    correlations = (
        analysis[correlation_columns]
        .corr()["calibrated_error_km"]
        .sort_values(
            ascending=False
        )
    )

    print(
        correlations.to_string(
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # =========================================================
    # SAVE FULL ANALYSIS
    # =========================================================

    analysis.to_csv(
        OUTPUT_FILE,
        index=False
    )

    iceberg_df.to_csv(
        ICEBERG_FILE,
        index=False
    )

    worst_cases.to_csv(
        WORST_FILE,
        index=False
    )

    print("\n" + "=" * 70)
    print("ERROR ANALYSIS COMPLETE")
    print("=" * 70)

    print("\nSaved:")
    print(f"  {OUTPUT_FILE}")
    print(f"  {ICEBERG_FILE}")
    print(f"  {WORST_FILE}")


if __name__ == "__main__":
    main()