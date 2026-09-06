from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear
from pyproj import Geod


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "catalog" / "calibration_dataset.csv"

OUTPUT_FILE = (
    ROOT / "data" / "catalog" /
    "leave_one_iceberg_out_evaluation.csv"
)

SUMMARY_FILE = (
    ROOT / "data" / "catalog" /
    "leave_one_iceberg_out_summary.csv"
)

COEFFICIENT_FILE = (
    ROOT / "data" / "catalog" /
    "leave_one_iceberg_out_coefficients.csv"
)


BASELINE_ALPHA = 0.85
BASELINE_BETA = 0.015

GEOD = Geod(ellps="WGS84")


def destination(lat, lon, u, v, hours):
    speed = np.sqrt(u**2 + v**2)

    if speed == 0:
        return lat, lon

    azimuth = np.degrees(np.arctan2(u, v))
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


def fit_coefficients(train_df):
    """
    Fit:

        observed_u = alpha * ocean_u + beta * wind_u
        observed_v = alpha * ocean_v + beta * wind_v

    subject to:

        alpha >= 0
        beta >= 0
    """

    A = np.vstack([
        np.column_stack([
            train_df["ocean_u"].values,
            train_df["wind_u"].values
        ]),
        np.column_stack([
            train_df["ocean_v"].values,
            train_df["wind_v"].values
        ])
    ])

    y = np.concatenate([
        train_df["observed_u"].values,
        train_df["observed_v"].values
    ])

    result = lsq_linear(
        A,
        y,
        bounds=(0, np.inf),
        method="trf"
    )

    return float(result.x[0]), float(result.x[1])


def model_error(row, alpha, beta):
    u = (
        alpha * row["ocean_u"]
        + beta * row["wind_u"]
    )

    v = (
        alpha * row["ocean_v"]
        + beta * row["wind_v"]
    )

    predicted_lat, predicted_lon = destination(
        row["start_latitude"],
        row["start_longitude"],
        u,
        v,
        row["duration_hours"]
    )

    return geodesic_error(
        predicted_lat,
        predicted_lon,
        row["observed_latitude"],
        row["observed_longitude"]
    )


def persistence_error(row):
    return geodesic_error(
        row["start_latitude"],
        row["start_longitude"],
        row["observed_latitude"],
        row["observed_longitude"]
    )


def calculate_metrics(errors):
    errors = np.asarray(errors)

    return {
        "mean_error_km": float(np.mean(errors)),
        "median_error_km": float(np.median(errors)),
        "rmse_km": float(np.sqrt(np.mean(errors ** 2))),
        "p90_error_km": float(np.percentile(errors, 90)),
        "max_error_km": float(np.max(errors)),
    }


def main():

    print("=" * 70)
    print("LEAVE-ONE-ICEBERG-OUT VALIDATION")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Calibration dataset not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    icebergs = sorted(df["iceberg_id"].unique())

    print(f"\nInput rows: {len(df)}")
    print(f"Icebergs: {len(icebergs)}")
    print(f"Iceberg IDs: {', '.join(icebergs)}")

    evaluation_rows = []
    coefficient_rows = []

    # =========================================================
    # LEAVE-ONE-ICEBERG-OUT
    # =========================================================

    for i, test_iceberg in enumerate(icebergs, start=1):

        train_df = df[
            df["iceberg_id"] != test_iceberg
        ].copy()

        test_df = df[
            df["iceberg_id"] == test_iceberg
        ].copy()

        alpha, beta = fit_coefficients(train_df)

        print("\n" + "-" * 70)
        print(
            f"FOLD {i}/{len(icebergs)}"
        )
        print("-" * 70)

        print(f"Test iceberg : {test_iceberg}")
        print(f"Train rows   : {len(train_df)}")
        print(f"Test rows    : {len(test_df)}")
        print(f"Train icebergs: {train_df['iceberg_id'].nunique()}")

        print(f"Learned alpha: {alpha:.8f}")
        print(f"Learned beta : {beta:.8f}")

        # -----------------------------------------------------
        # Store coefficients
        # -----------------------------------------------------

        coefficient_rows.append({
            "test_iceberg": test_iceberg,
            "train_rows": len(train_df),
            "train_icebergs": train_df["iceberg_id"].nunique(),
            "alpha": alpha,
            "beta": beta
        })

        # -----------------------------------------------------
        # Evaluate test iceberg
        # -----------------------------------------------------

        for _, row in test_df.iterrows():

            persistence = persistence_error(row)

            baseline = model_error(
                row,
                BASELINE_ALPHA,
                BASELINE_BETA
            )

            calibrated = model_error(
                row,
                alpha,
                beta
            )

            evaluation_rows.append({
                "test_iceberg": test_iceberg,
                "iceberg_id": row["iceberg_id"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],

                "persistence_error_km": persistence,

                "baseline_error_km": baseline,

                "calibrated_error_km": calibrated,

                "alpha": alpha,
                "beta": beta
            })

    evaluation_df = pd.DataFrame(evaluation_rows)
    coefficient_df = pd.DataFrame(coefficient_rows)

    # =========================================================
    # OVERALL METRICS
    # =========================================================

    persistence_errors = (
        evaluation_df["persistence_error_km"].values
    )

    baseline_errors = (
        evaluation_df["baseline_error_km"].values
    )

    calibrated_errors = (
        evaluation_df["calibrated_error_km"].values
    )

    persistence_metrics = calculate_metrics(
        persistence_errors
    )

    baseline_metrics = calculate_metrics(
        baseline_errors
    )

    calibrated_metrics = calculate_metrics(
        calibrated_errors
    )

    baseline_mean_skill = (
        1
        - baseline_metrics["mean_error_km"]
        / persistence_metrics["mean_error_km"]
    )

    baseline_rmse_skill = (
        1
        - baseline_metrics["rmse_km"]
        / persistence_metrics["rmse_km"]
    )

    calibrated_mean_skill = (
        1
        - calibrated_metrics["mean_error_km"]
        / persistence_metrics["mean_error_km"]
    )

    calibrated_rmse_skill = (
        1
        - calibrated_metrics["rmse_km"]
        / persistence_metrics["rmse_km"]
    )

    # =========================================================
    # PRINT OVERALL RESULTS
    # =========================================================

    print("\n" + "=" * 70)
    print("HELD-OUT OVERALL RESULTS")
    print("=" * 70)

    print("\nPersistence:")

    for key, value in persistence_metrics.items():
        print(f"  {key:<22}: {value:.4f}")

    print("\nExisting physics baseline:")

    print(f"  alpha                 : {BASELINE_ALPHA}")
    print(f"  beta                  : {BASELINE_BETA}")

    for key, value in baseline_metrics.items():
        print(f"  {key:<22}: {value:.4f}")

    print(
        f"  mean skill vs persistence: "
        f"{baseline_mean_skill:.4f}"
    )

    print(
        f"  RMSE skill vs persistence : "
        f"{baseline_rmse_skill:.4f}"
    )

    print("\nLOIO calibrated physics model:")

    for key, value in calibrated_metrics.items():
        print(f"  {key:<22}: {value:.4f}")

    print(
        f"  mean skill vs persistence: "
        f"{calibrated_mean_skill:.4f}"
    )

    print(
        f"  RMSE skill vs persistence : "
        f"{calibrated_rmse_skill:.4f}"
    )

    # =========================================================
    # PER-ICEBERG RESULTS
    # =========================================================

    per_iceberg_rows = []

    for iceberg_id in icebergs:

        subset = evaluation_df[
            evaluation_df["test_iceberg"] == iceberg_id
        ]

        p = calculate_metrics(
            subset["persistence_error_km"].values
        )

        b = calculate_metrics(
            subset["baseline_error_km"].values
        )

        c = calculate_metrics(
            subset["calibrated_error_km"].values
        )

        alpha = subset["alpha"].iloc[0]
        beta = subset["beta"].iloc[0]

        per_iceberg_rows.append({
            "test_iceberg": iceberg_id,
            "pairs": len(subset),

            "alpha": alpha,
            "beta": beta,

            "persistence_mean_error_km":
                p["mean_error_km"],

            "baseline_mean_error_km":
                b["mean_error_km"],

            "calibrated_mean_error_km":
                c["mean_error_km"],

            "persistence_rmse_km":
                p["rmse_km"],

            "baseline_rmse_km":
                b["rmse_km"],

            "calibrated_rmse_km":
                c["rmse_km"],

            "calibrated_mean_skill_vs_persistence":
                1 - (
                    c["mean_error_km"]
                    / p["mean_error_km"]
                ),

            "calibrated_rmse_skill_vs_persistence":
                1 - (
                    c["rmse_km"]
                    / p["rmse_km"]
                )
        })

    per_iceberg_df = pd.DataFrame(
        per_iceberg_rows
    )

    print("\n" + "=" * 70)
    print("HELD-OUT RESULTS BY ICEBERG")
    print("=" * 70)

    print(
        per_iceberg_df.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # =========================================================
    # SAVE RESULTS
    # =========================================================

    evaluation_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    coefficient_df.to_csv(
        COEFFICIENT_FILE,
        index=False
    )

    summary_rows = [
        {
            "model": "persistence",
            "alpha": np.nan,
            "beta": np.nan,
            **persistence_metrics,
            "mean_skill_vs_persistence": 0.0,
            "rmse_skill_vs_persistence": 0.0
        },
        {
            "model": "existing_baseline",
            "alpha": BASELINE_ALPHA,
            "beta": BASELINE_BETA,
            **baseline_metrics,
            "mean_skill_vs_persistence":
                baseline_mean_skill,
            "rmse_skill_vs_persistence":
                baseline_rmse_skill
        },
        {
            "model": "loio_calibrated",
            "alpha": np.nan,
            "beta": np.nan,
            **calibrated_metrics,
            "mean_skill_vs_persistence":
                calibrated_mean_skill,
            "rmse_skill_vs_persistence":
                calibrated_rmse_skill
        }
    ]

    summary_df = pd.DataFrame(summary_rows)

    summary_df.to_csv(
        SUMMARY_FILE,
        index=False
    )

    # =========================================================
    # FINAL INTERPRETATION
    # =========================================================

    print("\n" + "=" * 70)
    print("LOIO VALIDATION COMPLETE")
    print("=" * 70)

    print("\nSaved:")
    print(f"  {OUTPUT_FILE}")
    print(f"  {SUMMARY_FILE}")
    print(f"  {COEFFICIENT_FILE}")

    print("\n" + "-" * 70)
    print("INTERPRETATION")
    print("-" * 70)

    if calibrated_mean_skill > 0:
        print(
            f"LOIO calibrated model improves mean error "
            f"over persistence by "
            f"{calibrated_mean_skill * 100:.2f}%."
        )
    else:
        print(
            f"LOIO calibrated model is worse than persistence "
            f"by "
            f"{abs(calibrated_mean_skill) * 100:.2f}% "
            f"on mean error."
        )

    if calibrated_rmse_skill > 0:
        print(
            f"LOIO calibrated model improves RMSE "
            f"over persistence by "
            f"{calibrated_rmse_skill * 100:.2f}%."
        )
    else:
        print(
            f"LOIO calibrated model is worse than persistence "
            f"by "
            f"{abs(calibrated_rmse_skill) * 100:.2f}% "
            f"on RMSE."
        )

    print("\nIMPORTANT:")
    print(
        "Each test iceberg was excluded completely from "
        "coefficient fitting."
    )

    print(
        "This is the primary held-out generalization test."
    )


if __name__ == "__main__":
    main()