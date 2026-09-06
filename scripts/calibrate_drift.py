from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear
from pyproj import Geod


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "catalog" / "calibration_dataset.csv"

COEFFICIENT_FILE = ROOT / "data" / "catalog" / "calibrated_coefficients.csv"
EVALUATION_FILE = ROOT / "data" / "catalog" / "calibrated_evaluation.csv"
SUMMARY_FILE = ROOT / "data" / "catalog" / "calibrated_summary.csv"


# Existing prototype coefficients
BASELINE_ALPHA = 0.85
BASELINE_BETA = 0.015

GEOD = Geod(ellps="WGS84")


def destination(lat, lon, u, v, hours):
    """
    Propagate an iceberg using eastward velocity u and
    northward velocity v for the given duration.
    """

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
    """
    Great-circle distance between two coordinates in km.
    """

    _, _, distance_m = GEOD.inv(
        lon1,
        lat1,
        lon2,
        lat2
    )

    return distance_m / 1000.0


def predict_row(row, alpha, beta):
    """
    Predict 24h iceberg position using:

        u_ice = alpha * u_ocean + beta * u_wind
        v_ice = alpha * v_ocean + beta * v_wind
    """

    u = (
        alpha * row["ocean_u"]
        + beta * row["wind_u"]
    )

    v = (
        alpha * row["ocean_v"]
        + beta * row["wind_v"]
    )

    return destination(
        row["start_latitude"],
        row["start_longitude"],
        u,
        v,
        row["duration_hours"]
    )


def evaluate_model(df, alpha, beta):
    errors = []

    for _, row in df.iterrows():

        pred_lat, pred_lon = predict_row(
            row,
            alpha,
            beta
        )

        error = geodesic_error(
            pred_lat,
            pred_lon,
            row["observed_latitude"],
            row["observed_longitude"]
        )

        errors.append(error)

    return np.asarray(errors)


def calculate_metrics(errors):
    return {
        "mean_error_km": float(np.mean(errors)),
        "median_error_km": float(np.median(errors)),
        "rmse_km": float(np.sqrt(np.mean(errors ** 2))),
        "p90_error_km": float(np.percentile(errors, 90)),
        "max_error_km": float(np.max(errors)),
    }


def fit_coefficients(df):
    """
    Constrained least-squares fit:

        observed_u = alpha * ocean_u + beta * wind_u
        observed_v = alpha * ocean_v + beta * wind_v

    Constraints:

        alpha >= 0
        beta >= 0
    """

    A = np.vstack([
        np.column_stack([
            df["ocean_u"].values,
            df["wind_u"].values
        ]),
        np.column_stack([
            df["ocean_v"].values,
            df["wind_v"].values
        ])
    ])

    y = np.concatenate([
        df["observed_u"].values,
        df["observed_v"].values
    ])

    result = lsq_linear(
        A,
        y,
        bounds=(0, np.inf),
        method="trf"
    )

    alpha = float(result.x[0])
    beta = float(result.x[1])

    return alpha, beta, result


def main():

    print("=" * 70)
    print("DRIFT COEFFICIENT CALIBRATION")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Calibration dataset not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(f"\nInput rows: {len(df)}")
    print(f"Icebergs: {df['iceberg_id'].nunique()}")

    # ---------------------------------------------------------
    # Fit coefficients
    # ---------------------------------------------------------

    alpha, beta, result = fit_coefficients(df)

    print("\n" + "-" * 70)
    print("CALIBRATED COEFFICIENTS")
    print("-" * 70)

    print(f"alpha = {alpha:.8f}")
    print(f"beta  = {beta:.8f}")

    print(f"\nOptimization success: {result.success}")
    print(f"Optimization status: {result.status}")
    print(f"Cost: {result.cost:.8f}")

    # ---------------------------------------------------------
    # Component-level fit
    # ---------------------------------------------------------

    predicted_u = (
        alpha * df["ocean_u"]
        + beta * df["wind_u"]
    )

    predicted_v = (
        alpha * df["ocean_v"]
        + beta * df["wind_v"]
    )

    u_error = df["observed_u"] - predicted_u
    v_error = df["observed_v"] - predicted_v

    component_rmse = np.sqrt(
        np.mean(
            np.concatenate([
                u_error.values,
                v_error.values
            ]) ** 2
        )
    )

    print("\nComponent velocity RMSE:")
    print(f"{component_rmse:.6f} m/s")

    # ---------------------------------------------------------
    # Evaluate persistence
    # ---------------------------------------------------------

    persistence_errors = []

    for _, row in df.iterrows():

        error = geodesic_error(
            row["start_latitude"],
            row["start_longitude"],
            row["observed_latitude"],
            row["observed_longitude"]
        )

        persistence_errors.append(error)

    persistence_errors = np.asarray(persistence_errors)

    persistence_metrics = calculate_metrics(
        persistence_errors
    )

    # ---------------------------------------------------------
    # Evaluate existing baseline
    # ---------------------------------------------------------

    baseline_errors = evaluate_model(
        df,
        BASELINE_ALPHA,
        BASELINE_BETA
    )

    baseline_metrics = calculate_metrics(
        baseline_errors
    )

    # ---------------------------------------------------------
    # Evaluate calibrated model
    # ---------------------------------------------------------

    calibrated_errors = evaluate_model(
        df,
        alpha,
        beta
    )

    calibrated_metrics = calculate_metrics(
        calibrated_errors
    )

    # ---------------------------------------------------------
    # Skill vs persistence
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Print comparison
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)

    print("\nPersistence:")
    for key, value in persistence_metrics.items():
        print(f"  {key:<22}: {value:.4f}")

    print("\nExisting physics baseline:")
    print(f"  alpha                 : {BASELINE_ALPHA}")
    print(f"  beta                  : {BASELINE_BETA}")

    for key, value in baseline_metrics.items():
        print(f"  {key:<22}: {value:.4f}")

    print("\nCalibrated physics model:")
    print(f"  alpha                 : {alpha:.8f}")
    print(f"  beta                  : {beta:.8f}")

    for key, value in calibrated_metrics.items():
        print(f"  {key:<22}: {value:.4f}")

    print("\nSkill vs persistence:")
    print(
        f"  Mean-error skill      : "
        f"{calibrated_mean_skill:.4f}"
    )

    print(
        f"  RMSE skill            : "
        f"{calibrated_rmse_skill:.4f}"
    )

    # ---------------------------------------------------------
    # Per-iceberg evaluation
    # ---------------------------------------------------------

    rows = []

    for iceberg_id, group in df.groupby("iceberg_id"):

        p_errors = persistence_errors[
            df["iceberg_id"].values == iceberg_id
        ]

        b_errors = baseline_errors[
            df["iceberg_id"].values == iceberg_id
        ]

        c_errors = calibrated_errors[
            df["iceberg_id"].values == iceberg_id
        ]

        p = calculate_metrics(p_errors)
        b = calculate_metrics(b_errors)
        c = calculate_metrics(c_errors)

        rows.append({
            "iceberg_id": iceberg_id,
            "pairs": len(group),

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
                ),
        })

    per_iceberg = pd.DataFrame(rows)

    print("\n" + "=" * 70)
    print("PER-ICEBERG RESULTS")
    print("=" * 70)

    print(
        per_iceberg.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # ---------------------------------------------------------
    # Save coefficients
    # ---------------------------------------------------------

    coefficient_df = pd.DataFrame([{
        "alpha": alpha,
        "beta": beta,
        "baseline_alpha": BASELINE_ALPHA,
        "baseline_beta": BASELINE_BETA,
        "rows_used": len(df),
        "icebergs_used": df["iceberg_id"].nunique(),
        "component_velocity_rmse_mps":
            component_rmse
    }])

    coefficient_df.to_csv(
        COEFFICIENT_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # Save row-level evaluation
    # ---------------------------------------------------------

    evaluation_df = df[
        [
            "iceberg_id",
            "start_time",
            "end_time",
            "start_latitude",
            "start_longitude",
            "observed_latitude",
            "observed_longitude"
        ]
    ].copy()

    evaluation_df[
        "persistence_error_km"
    ] = persistence_errors

    evaluation_df[
        "baseline_error_km"
    ] = baseline_errors

    evaluation_df[
        "calibrated_error_km"
    ] = calibrated_errors

    evaluation_df.to_csv(
        EVALUATION_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # Save summary
    # ---------------------------------------------------------

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
                1 - (
                    baseline_metrics["mean_error_km"]
                    / persistence_metrics["mean_error_km"]
                ),
            "rmse_skill_vs_persistence":
                1 - (
                    baseline_metrics["rmse_km"]
                    / persistence_metrics["rmse_km"]
                )
        },
        {
            "model": "calibrated_all_data",
            "alpha": alpha,
            "beta": beta,
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

    # ---------------------------------------------------------
    # Final message
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("CALIBRATION COMPLETE")
    print("=" * 70)

    print(f"\nSaved:")
    print(f"  {COEFFICIENT_FILE}")
    print(f"  {EVALUATION_FILE}")
    print(f"  {SUMMARY_FILE}")

    print("\nIMPORTANT:")
    print(
        "These coefficients were fitted using all 49 rows."
    )
    print(
        "They are descriptive only and are NOT a held-out"
    )
    print(
        "generalization result."
    )

    print(
        "\nNext step: leave-one-iceberg-out evaluation."
    )


if __name__ == "__main__":
    main()