from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

CALIBRATION_FILE = (
    ROOT / "data" / "catalog" / "calibration_dataset.csv"
)

LOIO_FILE = (
    ROOT / "data" / "catalog" /
    "leave_one_iceberg_out_evaluation.csv"
)

OUTPUT_FILE = (
    ROOT / "data" / "catalog" /
    "environmental_regime_analysis.csv"
)

SUMMARY_FILE = (
    ROOT / "data" / "catalog" /
    "environmental_regime_summary.csv"
)


def add_regimes(df):
    df = df.copy()

    # =========================================================
    # BASIC ENVIRONMENTAL QUANTITIES
    # =========================================================

    df["ocean_speed_ms"] = np.sqrt(
        df["ocean_u"] ** 2 +
        df["ocean_v"] ** 2
    )

    df["wind_speed_ms"] = np.sqrt(
        df["wind_u"] ** 2 +
        df["wind_v"] ** 2
    )

    # =========================================================
    # OCEAN / WIND DIRECTIONAL ALIGNMENT
    #
    # +1 = same direction
    #  0 = perpendicular
    # -1 = opposite direction
    # =========================================================

    denominator = (
        df["ocean_speed_ms"] *
        df["wind_speed_ms"]
    )

    dot_product = (
        df["ocean_u"] * df["wind_u"] +
        df["ocean_v"] * df["wind_v"]
    )

    df["ocean_wind_alignment"] = np.where(
        denominator > 0,
        dot_product / denominator,
        np.nan
    )

    df["ocean_wind_alignment"] = (
        df["ocean_wind_alignment"]
        .clip(-1, 1)
    )

    # =========================================================
    # LOIO-SPECIFIC CALIBRATED CONTRIBUTIONS
    #
    # IMPORTANT:
    # alpha and beta come from the LOIO evaluation file.
    # They were learned WITHOUT the held-out iceberg.
    # =========================================================

    df["ocean_contribution_ms"] = (
        df["alpha"] *
        df["ocean_speed_ms"]
    )

    df["wind_contribution_ms"] = (
        df["beta"] *
        df["wind_speed_ms"]
    )

    # =========================================================
    # CALIBRATED FORCING VECTOR
    # =========================================================

    df["calibrated_forcing_u"] = (
        df["alpha"] * df["ocean_u"] +
        df["beta"] * df["wind_u"]
    )

    df["calibrated_forcing_v"] = (
        df["alpha"] * df["ocean_v"] +
        df["beta"] * df["wind_v"]
    )

    df["calibrated_forcing_speed_ms"] = np.sqrt(
        df["calibrated_forcing_u"] ** 2 +
        df["calibrated_forcing_v"] ** 2
    )

    # =========================================================
    # POST-HOC OUTCOME
    #
    # These are evaluation results, NOT prediction inputs.
    # =========================================================

    df["skill_vs_persistence"] = np.where(
        df["persistence_error_km"] > 0,
        1.0 -
        (
            df["calibrated_error_km"] /
            df["persistence_error_km"]
        ),
        np.nan
    )

    df["calibrated_better_than_persistence"] = (
        df["calibrated_error_km"] <
        df["persistence_error_km"]
    )

    # =========================================================
    # OCEAN SPEED REGIMES
    # =========================================================

    df["ocean_speed_regime"] = pd.cut(
        df["ocean_speed_ms"],
        bins=[
            -np.inf,
            0.05,
            0.10,
            0.20,
            np.inf
        ],
        labels=[
            "weak (<0.05 m/s)",
            "moderate (0.05-0.10 m/s)",
            "strong (0.10-0.20 m/s)",
            "very strong (>0.20 m/s)"
        ]
    )

    # =========================================================
    # WIND SPEED REGIMES
    # =========================================================

    df["wind_speed_regime"] = pd.cut(
        df["wind_speed_ms"],
        bins=[
            -np.inf,
            3.0,
            6.0,
            10.0,
            np.inf
        ],
        labels=[
            "low (<3 m/s)",
            "moderate (3-6 m/s)",
            "strong (6-10 m/s)",
            "very strong (>10 m/s)"
        ]
    )

    # =========================================================
    # OCEAN / WIND ALIGNMENT REGIMES
    # =========================================================

    df["alignment_regime"] = pd.cut(
        df["ocean_wind_alignment"],
        bins=[
            -1.0001,
            -0.33,
            0.33,
            1.0001
        ],
        labels=[
            "opposing",
            "weak/perpendicular",
            "aligned"
        ]
    )

    # =========================================================
    # CALIBRATED FORCING REGIMES
    # =========================================================

    df["forcing_regime"] = pd.cut(
        df["calibrated_forcing_speed_ms"],
        bins=[
            -np.inf,
            0.03,
            0.06,
            0.10,
            np.inf
        ],
        labels=[
            "weak (<0.03 m/s)",
            "moderate (0.03-0.06 m/s)",
            "strong (0.06-0.10 m/s)",
            "very strong (>0.10 m/s)"
        ]
    )

    return df


def calculate_regime_metrics(subset):
    persistence = (
        subset["persistence_error_km"]
        .values
    )

    calibrated = (
        subset["calibrated_error_km"]
        .values
    )

    persistence_mean = np.mean(persistence)
    calibrated_mean = np.mean(calibrated)

    persistence_rmse = np.sqrt(
        np.mean(persistence ** 2)
    )

    calibrated_rmse = np.sqrt(
        np.mean(calibrated ** 2)
    )

    if persistence_mean > 0:
        mean_skill = (
            1 -
            calibrated_mean /
            persistence_mean
        )
    else:
        mean_skill = np.nan

    if persistence_rmse > 0:
        rmse_skill = (
            1 -
            calibrated_rmse /
            persistence_rmse
        )
    else:
        rmse_skill = np.nan

    wins = (
        calibrated < persistence
    )

    return {
        "pairs": len(subset),

        "icebergs": subset[
            "test_iceberg"
        ].nunique(),

        "mean_ocean_speed_ms":
            subset["ocean_speed_ms"].mean(),

        "mean_wind_speed_ms":
            subset["wind_speed_ms"].mean(),

        "mean_alignment":
            subset["ocean_wind_alignment"].mean(),

        "mean_ocean_contribution_ms":
            subset["ocean_contribution_ms"].mean(),

        "mean_wind_contribution_ms":
            subset["wind_contribution_ms"].mean(),

        "mean_calibrated_forcing_speed_ms":
            subset[
                "calibrated_forcing_speed_ms"
            ].mean(),

        "persistence_mean_error_km":
            persistence_mean,

        "calibrated_mean_error_km":
            calibrated_mean,

        "persistence_rmse_km":
            persistence_rmse,

        "calibrated_rmse_km":
            calibrated_rmse,

        "mean_skill_vs_persistence":
            mean_skill,

        "rmse_skill_vs_persistence":
            rmse_skill,

        "calibrated_wins":
            int(np.sum(wins)),

        "win_rate":
            float(np.mean(wins))
    }


def summarize_regime(
    df,
    regime_column,
    regime_name
):
    rows = []

    for regime, subset in df.groupby(
        regime_column,
        observed=True
    ):

        if len(subset) == 0:
            continue

        metrics = calculate_regime_metrics(
            subset
        )

        rows.append({
            "regime_type": regime_name,
            "regime": str(regime),
            **metrics
        })

    return rows


def main():

    print("=" * 75)
    print("ENVIRONMENTAL REGIME ANALYSIS")
    print("=" * 75)

    # =========================================================
    # CHECK FILES
    # =========================================================

    if not CALIBRATION_FILE.exists():
        raise FileNotFoundError(
            f"Calibration dataset not found:\n"
            f"{CALIBRATION_FILE}"
        )

    if not LOIO_FILE.exists():
        raise FileNotFoundError(
            f"LOIO evaluation file not found:\n"
            f"{LOIO_FILE}"
        )

    # =========================================================
    # LOAD DATA
    # =========================================================

    calibration_df = pd.read_csv(
        CALIBRATION_FILE
    )

    loio_df = pd.read_csv(
        LOIO_FILE
    )

    print(
        f"\nCalibration rows: "
        f"{len(calibration_df)}"
    )

    print(
        f"LOIO rows: "
        f"{len(loio_df)}"
    )

    # =========================================================
    # REQUIRED COLUMNS
    #
    # alpha and beta are NOT required from calibration_df.
    # They are already present in loio_df.
    # =========================================================

    environment_columns = [
        "ocean_u",
        "ocean_v",
        "wind_u",
        "wind_v"
    ]

    loio_columns = [
        "test_iceberg",
        "iceberg_id",
        "start_time",
        "end_time",
        "persistence_error_km",
        "calibrated_error_km",
        "alpha",
        "beta"
    ]

    missing_environment = [
        column
        for column in environment_columns
        if column not in calibration_df.columns
    ]

    if missing_environment:
        raise ValueError(
            "Missing environmental columns in "
            "calibration_dataset.csv: "
            + ", ".join(missing_environment)
        )

    missing_loio = [
        column
        for column in loio_columns
        if column not in loio_df.columns
    ]

    if missing_loio:
        raise ValueError(
            "Missing columns in "
            "leave_one_iceberg_out_evaluation.csv: "
            + ", ".join(missing_loio)
        )

    # =========================================================
    # MERGE ENVIRONMENT WITH LOIO RESULTS
    # =========================================================

    merge_columns = [
        "iceberg_id",
        "start_time",
        "end_time"
    ]

    merged = loio_df.merge(
        calibration_df[
            merge_columns +
            environment_columns
        ],
        on=merge_columns,
        how="left",
        validate="one_to_one"
    )

    # =========================================================
    # MERGE VALIDATION
    # =========================================================

    if len(merged) != len(loio_df):
        raise ValueError(
            "Merge changed the number of LOIO rows."
        )

    if merged[environment_columns].isna().any().any():

        missing_counts = (
            merged[
                environment_columns
            ]
            .isna()
            .sum()
        )

        raise ValueError(
            "Missing environmental values after merge:\n"
            f"{missing_counts}"
        )

    if merged[
        ["alpha", "beta"]
    ].isna().any().any():

        raise ValueError(
            "Missing LOIO-specific alpha/beta values."
        )

    print(
        f"Merged rows: {len(merged)}"
    )

    # =========================================================
    # CREATE ENVIRONMENTAL FEATURES
    # =========================================================

    merged = add_regimes(
        merged
    )

    # =========================================================
    # BUILD REGIME SUMMARY
    # =========================================================

    summary_rows = []

    summary_rows.extend(
        summarize_regime(
            merged,
            "ocean_speed_regime",
            "ocean_speed"
        )
    )

    summary_rows.extend(
        summarize_regime(
            merged,
            "wind_speed_regime",
            "wind_speed"
        )
    )

    summary_rows.extend(
        summarize_regime(
            merged,
            "alignment_regime",
            "ocean_wind_alignment"
        )
    )

    summary_rows.extend(
        summarize_regime(
            merged,
            "forcing_regime",
            "calibrated_forcing"
        )
    )

    summary_df = pd.DataFrame(
        summary_rows
    )

    # =========================================================
    # OVERALL ENVIRONMENT
    # =========================================================

    print("\n" + "=" * 75)
    print("OVERALL ENVIRONMENTAL CONDITIONS")
    print("=" * 75)

    print(
        f"\nMean ocean speed        : "
        f"{merged['ocean_speed_ms'].mean():.6f} m/s"
    )

    print(
        f"Mean wind speed         : "
        f"{merged['wind_speed_ms'].mean():.6f} m/s"
    )

    print(
        f"Mean ocean/wind alignment: "
        f"{merged['ocean_wind_alignment'].mean():.6f}"
    )

    print(
        f"Mean ocean contribution : "
        f"{merged['ocean_contribution_ms'].mean():.6f} m/s"
    )

    print(
        f"Mean wind contribution  : "
        f"{merged['wind_contribution_ms'].mean():.6f} m/s"
    )

    print(
        f"Mean calibrated forcing : "
        f"{merged['calibrated_forcing_speed_ms'].mean():.6f} m/s"
    )

    # =========================================================
    # REGIME RESULTS
    # =========================================================

    print("\n" + "=" * 75)
    print("REGIME RESULTS")
    print("=" * 75)

    for regime_type in summary_df[
        "regime_type"
    ].unique():

        subset = summary_df[
            summary_df["regime_type"] ==
            regime_type
        ]

        print("\n" + "-" * 75)
        print(
            regime_type.upper()
        )
        print("-" * 75)

        display_columns = [
            "regime",
            "pairs",
            "icebergs",
            "persistence_mean_error_km",
            "calibrated_mean_error_km",
            "persistence_rmse_km",
            "calibrated_rmse_km",
            "mean_skill_vs_persistence",
            "rmse_skill_vs_persistence",
            "calibrated_wins",
            "win_rate"
        ]

        print(
            subset[
                display_columns
            ].to_string(
                index=False,
                float_format=lambda x:
                    f"{x:.4f}"
            )
        )

    # =========================================================
    # PER-ICEBERG ENVIRONMENT
    # =========================================================

    print("\n" + "=" * 75)
    print("ENVIRONMENT BY HELD-OUT ICEBERG")
    print("=" * 75)

    iceberg_summary = (
        merged
        .groupby("test_iceberg")
        .agg(
            pairs=("test_iceberg", "size"),

            mean_ocean_speed_ms=(
                "ocean_speed_ms",
                "mean"
            ),

            mean_wind_speed_ms=(
                "wind_speed_ms",
                "mean"
            ),

            mean_alignment=(
                "ocean_wind_alignment",
                "mean"
            ),

            mean_ocean_contribution_ms=(
                "ocean_contribution_ms",
                "mean"
            ),

            mean_wind_contribution_ms=(
                "wind_contribution_ms",
                "mean"
            ),

            mean_forcing_speed_ms=(
                "calibrated_forcing_speed_ms",
                "mean"
            ),

            calibrated_mean_error_km=(
                "calibrated_error_km",
                "mean"
            ),

            persistence_mean_error_km=(
                "persistence_error_km",
                "mean"
            )
        )
        .reset_index()
    )

    print(
        iceberg_summary.to_string(
            index=False,
            float_format=lambda x:
                f"{x:.4f}"
        )
    )

    # =========================================================
    # SAVE FULL ROW-LEVEL ANALYSIS
    # =========================================================

    merged.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # =========================================================
    # SAVE REGIME SUMMARY
    # =========================================================

    summary_df.to_csv(
        SUMMARY_FILE,
        index=False
    )

    # =========================================================
    # FINAL MESSAGE
    # =========================================================

    print("\n" + "=" * 75)
    print("ENVIRONMENTAL REGIME ANALYSIS COMPLETE")
    print("=" * 75)

    print("\nSaved:")
    print(
        f"  {OUTPUT_FILE}"
    )

    print(
        f"  {SUMMARY_FILE}"
    )

    print("\nIMPORTANT:")
    print(
        "This analysis is descriptive only."
    )

    print(
        "No regime-switching model or threshold "
        "was trained."
    )

    print(
        "Observed iceberg speed/displacement was "
        "not used as an environmental predictor."
    )

    print(
        "The alpha and beta values used for each "
        "row are the corresponding LOIO fold coefficients."
    )

    print(
        "Each held-out iceberg remained excluded "
        "from its own coefficient fitting."
    )


if __name__ == "__main__":
    main()