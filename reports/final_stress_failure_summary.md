# Final Stress and Failure Assessment

## Overall result

The leave-one-iceberg-out evaluation contains 49 held-out
24-hour iceberg drift pairs.

| Metric | Persistence | Original Physics | Calibrated |
|---|---:|---:|---:|
| Mean error (km) | 7.335 | 13.061 | 7.300 |
| RMSE (km) | 9.181 | 15.682 | 8.565 |

The calibrated model achieves 6.71% RMSE skill relative to
persistence.

It wins on 27 of 49 individual pairs
(55.10%).

## Iceberg-level robustness

The calibration was evaluated using leave-one-iceberg-out validation.
Therefore, each iceberg's coefficients were estimated without using that
iceberg's observations.

| iceberg_id   |   pairs |   persistence_mean_km |   calibrated_mean_km |   persistence_rmse_km |   calibrated_rmse_km |   calibrated_wins |   mean_skill_pct |   rmse_skill_pct |   win_rate_pct |
|:-------------|--------:|----------------------:|---------------------:|----------------------:|---------------------:|------------------:|-----------------:|-----------------:|---------------:|
| a78          |       7 |                 6.268 |                5.125 |                 7.472 |                6.276 |                 6 |           18.233 |           16.008 |         85.714 |
| b09i         |       7 |                 6.172 |                6.641 |                 6.215 |                6.952 |                 3 |           -7.592 |          -11.855 |         42.857 |
| b16          |       7 |                 2.105 |                5.852 |                 4.041 |                6.516 |                 0 |         -177.997 |          -61.239 |          0.000 |
| d21b         |       7 |                12.181 |               10.350 |                14.429 |               11.992 |                 6 |           15.036 |           16.889 |         85.714 |
| d29a         |       7 |                 9.582 |                9.275 |                10.727 |               10.894 |                 5 |            3.201 |           -1.560 |         71.429 |
| d29c         |       7 |                 7.363 |                5.890 |                 9.768 |                7.200 |                 5 |           20.009 |           26.294 |         71.429 |
| d31          |       7 |                 7.675 |                7.971 |                 7.785 |                8.307 |                 2 |           -3.848 |           -6.704 |         28.571 |

## Largest calibrated errors

The calibrated error distribution has:

- Mean: 7.300 km
- Median: 6.360 km
- P90: 12.940 km
- Maximum: 21.589 km
- Errors above 10 km: 10
- Errors above 15 km: 4
- Errors above 20 km: 1

## Uncertainty assessment


The existing ensemble uncertainty mechanism produced a mean uncertainty
radius of 0.400 km.

Its empirical coverage was only 2.04% for the
nominal 90% radius.

The correlation between uncertainty radius and actual held-out error was
-0.0159.

Therefore, the current uncertainty estimate is considered
**under-dispersed and not calibrated for operational confidence claims**.


A sensitivity analysis tested velocity-noise values up to
0.030 m/s. The highest observed coverage among the tested
values was 48.98%.

This sensitivity analysis is diagnostic only and does not justify selecting
a production noise value.


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
