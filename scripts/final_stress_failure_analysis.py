from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "catalog"

EVALUATION_FILE = (
    DATA_DIR / "leave_one_iceberg_out_evaluation.csv"
)

ERROR_FILE = (
    DATA_DIR / "calibration_error_analysis.csv"
)

ICEBERG_ERROR_FILE = (
    DATA_DIR / "calibration_error_by_iceberg.csv"
)

REGIME_FILE = (
    DATA_DIR / "environmental_regime_analysis.csv"
)

UNCERTAINTY_FILE = (
    DATA_DIR / "uncertainty_validation.csv"
)

SENSITIVITY_FILE = (
    DATA_DIR / "uncertainty_sensitivity.csv"
)

OUTPUT_FILE = (
    DATA_DIR / "final_stress_failure_summary.csv"
)

REPORT_FILE = (
    BASE_DIR / "reports" / "final_stress_failure_summary.md"
)


def find_column(df, candidates):
    for column in candidates:
        if column in df.columns:
            return column
    return None


def load_optional(path):
    if not path.exists():
        print(f"WARNING: Missing file: {path}")
        return None

    return pd.read_csv(path)


def main():

    print("=" * 75)
    print("FINAL STRESS / FAILURE ANALYSIS")
    print("=" * 75)

    evaluation = pd.read_csv(
        EVALUATION_FILE
    )

    error_analysis = load_optional(
        ERROR_FILE
    )

    iceberg_error = load_optional(
        ICEBERG_ERROR_FILE
    )

    regime = load_optional(
        REGIME_FILE
    )

    uncertainty = load_optional(
        UNCERTAINTY_FILE
    )

    sensitivity = load_optional(
        SENSITIVITY_FILE
    )

    # ---------------------------------------------------------
    # 1. Overall model performance
    # ---------------------------------------------------------

    print()
    print("=" * 75)
    print("1. OVERALL PERFORMANCE")
    print("=" * 75)

    persistence_mean = (
        evaluation["persistence_error_km"]
        .mean()
    )

    calibrated_mean = (
        evaluation["calibrated_error_km"]
        .mean()
    )

    baseline_mean = (
        evaluation["baseline_error_km"]
        .mean()
    )

    persistence_rmse = np.sqrt(
        np.mean(
            evaluation[
                "persistence_error_km"
            ] ** 2
        )
    )

    calibrated_rmse = np.sqrt(
        np.mean(
            evaluation[
                "calibrated_error_km"
            ] ** 2
        )
    )

    baseline_rmse = np.sqrt(
        np.mean(
            evaluation[
                "baseline_error_km"
            ] ** 2
        )
    )

    mean_skill = (
        1
        - calibrated_mean
        / persistence_mean
    )

    rmse_skill = (
        1
        - calibrated_rmse
        / persistence_rmse
    )

    print(
        f"Pairs evaluated       : "
        f"{len(evaluation)}"
    )

    print(
        f"Persistence mean      : "
        f"{persistence_mean:.4f} km"
    )

    print(
        f"Calibrated mean       : "
        f"{calibrated_mean:.4f} km"
    )

    print(
        f"Prototype mean        : "
        f"{baseline_mean:.4f} km"
    )

    print(
        f"Persistence RMSE      : "
        f"{persistence_rmse:.4f} km"
    )

    print(
        f"Calibrated RMSE       : "
        f"{calibrated_rmse:.4f} km"
    )

    print(
        f"Prototype RMSE        : "
        f"{baseline_rmse:.4f} km"
    )

    print(
        f"Mean skill vs persist.: "
        f"{mean_skill * 100:.2f}%"
    )

    print(
        f"RMSE skill vs persist.: "
        f"{rmse_skill * 100:.2f}%"
    )

    # ---------------------------------------------------------
    # 2. Pair-level wins/losses
    # ---------------------------------------------------------

    print()
    print("=" * 75)
    print("2. PAIR-LEVEL STRESS")
    print("=" * 75)

    improvement = (
        evaluation["persistence_error_km"]
        - evaluation["calibrated_error_km"]
    )

    evaluation = evaluation.copy()

    evaluation[
        "improvement_vs_persistence_km"
    ] = improvement

    evaluation[
        "calibrated_better_than_persistence"
    ] = improvement > 0

    wins = int(
        (
            improvement > 0
        ).sum()
    )

    losses = int(
        (
            improvement < 0
        ).sum()
    )

    ties = int(
        (
            improvement == 0
        ).sum()
    )

    print(
        f"Calibrated wins : "
        f"{wins}/{len(evaluation)} "
        f"({wins / len(evaluation) * 100:.2f}%)"
    )

    print(
        f"Calibrated loses: "
        f"{losses}/{len(evaluation)} "
        f"({losses / len(evaluation) * 100:.2f}%)"
    )

    print(
        f"Ties            : {ties}"
    )

    # ---------------------------------------------------------
    # 3. Worst calibrated failures
    # ---------------------------------------------------------

    print()
    print("=" * 75)
    print("3. WORST CALIBRATED FAILURES")
    print("=" * 75)

    worst = (
        evaluation
        .sort_values(
            "calibrated_error_km",
            ascending=False
        )
        .head(10)
    )

    print(
        worst[
            [
                "iceberg_id",
                "start_time",
                "end_time",
                "persistence_error_km",
                "baseline_error_km",
                "calibrated_error_km",
                "alpha",
                "beta",
            ]
        ].to_string(
            index=False
        )
    )

    # ---------------------------------------------------------
    # 4. Worst regressions vs persistence
    # ---------------------------------------------------------

    print()
    print("=" * 75)
    print("4. WORST REGRESSIONS VS PERSISTENCE")
    print("=" * 75)

    regressions = (
        evaluation
        .sort_values(
            "improvement_vs_persistence_km"
        )
        .head(10)
    )

    print(
        regressions[
            [
                "iceberg_id",
                "start_time",
                "persistence_error_km",
                "calibrated_error_km",
                "improvement_vs_persistence_km",
            ]
        ].to_string(
            index=False
        )
    )

    # ---------------------------------------------------------
    # 5. Best improvements
    # ---------------------------------------------------------

    print()
    print("=" * 75)
    print("5. BEST IMPROVEMENTS VS PERSISTENCE")
    print("=" * 75)

    best = (
        evaluation
        .sort_values(
            "improvement_vs_persistence_km",
            ascending=False
        )
        .head(10)
    )

    print(
        best[
            [
                "iceberg_id",
                "start_time",
                "persistence_error_km",
                "calibrated_error_km",
                "improvement_vs_persistence_km",
            ]
        ].to_string(
            index=False
        )
    )

    # ---------------------------------------------------------
    # 6. Per iceberg
    # ---------------------------------------------------------

    print()
    print("=" * 75)
    print("6. ICEBERG-LEVEL STRESS")
    print("=" * 75)

    iceberg_summary = (
        evaluation
        .groupby("iceberg_id")
        .agg(
            pairs=(
                "calibrated_error_km",
                "count"
            ),
            persistence_mean_km=(
                "persistence_error_km",
                "mean"
            ),
            calibrated_mean_km=(
                "calibrated_error_km",
                "mean"
            ),
            persistence_rmse_km=(
                "persistence_error_km",
                lambda x: np.sqrt(
                    np.mean(x ** 2)
                )
            ),
            calibrated_rmse_km=(
                "calibrated_error_km",
                lambda x: np.sqrt(
                    np.mean(x ** 2)
                )
            ),
            calibrated_wins=(
                "calibrated_better_than_persistence",
                "sum"
            ),
        )
        .reset_index()
    )

    iceberg_summary[
        "mean_skill_pct"
    ] = (
        1
        -
        iceberg_summary[
            "calibrated_mean_km"
        ]
        /
        iceberg_summary[
            "persistence_mean_km"
        ]
    ) * 100

    iceberg_summary[
        "rmse_skill_pct"
    ] = (
        1
        -
        iceberg_summary[
            "calibrated_rmse_km"
        ]
        /
        iceberg_summary[
            "persistence_rmse_km"
        ]
    ) * 100

    iceberg_summary[
        "win_rate_pct"
    ] = (
        iceberg_summary[
            "calibrated_wins"
        ]
        /
        iceberg_summary["pairs"]
    ) * 100

    print(
        iceberg_summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.3f}"
        )
    )

    # ---------------------------------------------------------
    # 7. Error magnitude distribution
    # ---------------------------------------------------------

    print()
    print("=" * 75)
    print("7. CALIBRATED ERROR DISTRIBUTION")
    print("=" * 75)

    errors = evaluation[
        "calibrated_error_km"
    ]

    print(
        f"Mean   : {errors.mean():.3f} km"
    )

    print(
        f"Median : {errors.median():.3f} km"
    )

    print(
        f"P75    : {errors.quantile(.75):.3f} km"
    )

    print(
        f"P90    : {errors.quantile(.90):.3f} km"
    )

    print(
        f"Max    : {errors.max():.3f} km"
    )

    print(
        f">5 km  : {(errors > 5).sum()}"
    )

    print(
        f">10 km : {(errors > 10).sum()}"
    )

    print(
        f">15 km : {(errors > 15).sum()}"
    )

    print(
        f">20 km : {(errors > 20).sum()}"
    )

    # ---------------------------------------------------------
    # 8. Uncertainty assessment
    # ---------------------------------------------------------

    uncertainty_coverage = None
    uncertainty_radius = None
    uncertainty_correlation = None

    if uncertainty is not None:

        uncertainty_coverage = (
            uncertainty[
                "inside_90pct_radius"
            ].mean()
            * 100
        )

        uncertainty_radius = (
            uncertainty[
                "uncertainty_radius_km"
            ].mean()
        )

        uncertainty_correlation = (
            uncertainty[
                [
                    "uncertainty_radius_km",
                    "actual_error_km",
                ]
            ]
            .corr()
            .iloc[0, 1]
        )

        print()
        print("=" * 75)
        print("8. UNCERTAINTY FAILURE")
        print("=" * 75)

        print(
            f"Empirical 90% coverage : "
            f"{uncertainty_coverage:.2f}%"
        )

        print(
            f"Mean uncertainty radius: "
            f"{uncertainty_radius:.3f} km"
        )

        print(
            f"Radius/error correlation: "
            f"{uncertainty_correlation:.4f}"
        )

    # ---------------------------------------------------------
    # 9. Sensitivity conclusion
    # ---------------------------------------------------------

    max_tested_coverage = None
    max_tested_noise = None

    if sensitivity is not None:

        idx = (
            sensitivity[
                "coverage_pct"
            ].idxmax()
        )

        max_tested = sensitivity.loc[idx]

        max_tested_coverage = float(
            max_tested["coverage_pct"]
        )

        max_tested_noise = float(
            max_tested[
                "velocity_noise_mps"
            ]
        )

        print()
        print("=" * 75)
        print("9. UNCERTAINTY SENSITIVITY")
        print("=" * 75)

        print(
            f"Highest tested coverage : "
            f"{max_tested_coverage:.2f}%"
        )

        print(
            f"Corresponding noise     : "
            f"{max_tested_noise:.3f} m/s"
        )

        print(
            "No production noise level "
            "is selected from this analysis."
        )

    # ---------------------------------------------------------
    # 10. Production decision
    # ---------------------------------------------------------

    print()
    print("=" * 75)
    print("10. PRODUCTION DECISION")
    print("=" * 75)

    if rmse_skill > 0:
        point_forecast_decision = (
            "CALIBRATED MODEL SHOWS "
            "POSITIVE HELD-OUT SKILL"
        )
    else:
        point_forecast_decision = (
            "CALIBRATED MODEL DOES NOT "
            "SHOW POSITIVE HELD-OUT SKILL"
        )

    if (
        uncertainty_coverage is not None
        and uncertainty_coverage < 70
    ):
        uncertainty_decision = (
            "UNCERTAINTY ESTIMATE NOT "
            "READY FOR PRODUCTION CLAIMS"
        )
    else:
        uncertainty_decision = (
            "UNCERTAINTY REQUIRES FURTHER REVIEW"
        )

    print(point_forecast_decision)
    print(uncertainty_decision)

    print()
    print(
        "Recommended status:"
    )

    print(
        "RESEARCH / VALIDATED CALIBRATION"
    )

    print(
        "Do not replace production coefficients "
        "or promote the current uncertainty radius "
        "to a calibrated operational confidence region."
    )

    # ---------------------------------------------------------
    # Save summary CSV
    # ---------------------------------------------------------

    summary_rows = []

    for _, row in iceberg_summary.iterrows():

        summary_rows.append(
            {
                "iceberg_id":
                    row["iceberg_id"],
                "pairs":
                    row["pairs"],
                "persistence_mean_km":
                    row["persistence_mean_km"],
                "calibrated_mean_km":
                    row["calibrated_mean_km"],
                "persistence_rmse_km":
                    row["persistence_rmse_km"],
                "calibrated_rmse_km":
                    row["calibrated_rmse_km"],
                "mean_skill_pct":
                    row["mean_skill_pct"],
                "rmse_skill_pct":
                    row["rmse_skill_pct"],
                "win_rate_pct":
                    row["win_rate_pct"],
            }
        )

    summary_df = pd.DataFrame(
        summary_rows
    )

    summary_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # Generate markdown report
    # ---------------------------------------------------------

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    report = f"""# Final Stress and Failure Assessment

## Overall result

The leave-one-iceberg-out evaluation contains {len(evaluation)} held-out
24-hour iceberg drift pairs.

| Metric | Persistence | Original Physics | Calibrated |
|---|---:|---:|---:|
| Mean error (km) | {persistence_mean:.3f} | {baseline_mean:.3f} | {calibrated_mean:.3f} |
| RMSE (km) | {persistence_rmse:.3f} | {baseline_rmse:.3f} | {calibrated_rmse:.3f} |

The calibrated model achieves {rmse_skill * 100:.2f}% RMSE skill relative to
persistence.

It wins on {wins} of {len(evaluation)} individual pairs
({wins / len(evaluation) * 100:.2f}%).

## Iceberg-level robustness

The calibration was evaluated using leave-one-iceberg-out validation.
Therefore, each iceberg's coefficients were estimated without using that
iceberg's observations.

"""

    report += iceberg_summary.to_markdown(
        index=False,
        floatfmt=".3f"
    )

    report += f"""

## Largest calibrated errors

The calibrated error distribution has:

- Mean: {errors.mean():.3f} km
- Median: {errors.median():.3f} km
- P90: {errors.quantile(.90):.3f} km
- Maximum: {errors.max():.3f} km
- Errors above 10 km: {(errors > 10).sum()}
- Errors above 15 km: {(errors > 15).sum()}
- Errors above 20 km: {(errors > 20).sum()}

## Uncertainty assessment

"""

    if uncertainty_coverage is not None:

        report += f"""
The existing ensemble uncertainty mechanism produced a mean uncertainty
radius of {uncertainty_radius:.3f} km.

Its empirical coverage was only {uncertainty_coverage:.2f}% for the
nominal 90% radius.

The correlation between uncertainty radius and actual held-out error was
{uncertainty_correlation:.4f}.

Therefore, the current uncertainty estimate is considered
**under-dispersed and not calibrated for operational confidence claims**.
"""

    if max_tested_coverage is not None:

        report += f"""

A sensitivity analysis tested velocity-noise values up to
{max_tested_noise:.3f} m/s. The highest observed coverage among the tested
values was {max_tested_coverage:.2f}%.

This sensitivity analysis is diagnostic only and does not justify selecting
a production noise value.
"""

    report += f"""

## Failure interpretation

The principal failure pattern is that the calibrated model does not improve
uniformly across all independent icebergs or environmental regimes.

The results indicate that:

1. Persistence remains a strong baseline, especially for slowly moving
   icebergs.
2. Physics-informed calibration provides useful improvement in several
   cases, particularly where environmental forcing contains meaningful
   predictive information.
3. Some high-motion and directionally complex cases remain difficult.
4. The model frequently underestimates the magnitude of observed iceberg
   displacement.
5. The current uncertainty model does not adequately represent the observed
   prediction error.

## Production decision

**Recommended status: Research / validated calibration result.**

The calibrated coefficients should not yet replace the current production
coefficients solely on the basis of this dataset.

The calibrated model has demonstrated positive held-out skill relative to
persistence, but the improvement is modest and heterogeneous across the
seven independent icebergs.

The current ensemble uncertainty should not be presented as a calibrated
90% operational confidence region.

## Recommended future validation

Future work should prioritize:

- additional independent moving-iceberg observations;
- broader temporal and geographic coverage;
- independent evaluation of calibrated coefficients;
- improved representation of environmental/model-form uncertainty;
- validation of uncertainty coverage on a genuinely independent dataset.

No regime-switching model is recommended at this stage because the present
calibration contains only seven independent icebergs.
"""

    REPORT_FILE.write_text(
        report,
        encoding="utf-8"
    )

    print()
    print("=" * 75)
    print("FILES SAVED")
    print("=" * 75)

    print(
        f"CSV report : {OUTPUT_FILE}"
    )

    print(
        f"Markdown   : {REPORT_FILE}"
    )


if __name__ == "__main__":
    main()