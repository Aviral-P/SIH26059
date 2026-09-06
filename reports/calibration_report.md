Antarctic Iceberg Drift Calibration Report

1\. Project Objective



This project develops a physics-informed Antarctic iceberg drift prediction system by combining historical iceberg observations with ocean-current and wind forcing. The objective is to improve short-term iceberg trajectory prediction while providing scientifically validated uncertainty estimates.



2\. Data Sources



Source



&#x09;



Purpose









BYU/NIC



&#x09;



Historical iceberg trajectories









HYCOM GOFS 3.1



&#x09;



Ocean currents









ERA5



&#x09;



10 m wind









NSIDC



&#x09;



Sea-ice context and QC



3\. Calibration Dataset



The final calibration dataset contains:



49 calibration pairs



7 unique icebergs



Icebergs used:



a78



b09i



b16



d21b



d29a



d29c



d31



4\. Environmental Coverage



Candidate environmental availability:



Dataset



&#x09;



Available









HYCOM



&#x09;



63 / 105









ERA5



&#x09;



91 / 105









Both



&#x09;



49 / 105



Only complete HYCOM + ERA5 pairs were used for calibration.



5\. Baseline Model



Original coefficients:



α=0.85



β=0.015



Model:



u=αU

ocean

&#x09;​



+βU

wind

&#x09;​



v=αV

ocean

&#x09;​



+βV

wind

&#x09;​



6\. Calibrated Model



Constrained least-squares optimization produced:



α=0.35665



β=0.001163



This indicates iceberg motion is primarily driven by ocean currents, while wind contributes only modestly.



7\. Validation Method



Leave-One-Iceberg-Out (LOIO) validation was used.



For each fold:



one iceberg was completely excluded,



coefficients were fitted using the remaining six,



testing was performed only on the unseen iceberg.



This prevents leakage between training and testing.



8\. Validation Results



Model



&#x09;



RMSE (km)









Persistence



&#x09;



9.181









Original Baseline



&#x09;



15.682









LOIO Calibrated



&#x09;



8.565



Key findings:



RMSE improvement over persistence: 6.71%



Mean error improvement: 0.47%



9\. Trajectory Prediction



The system generates forecasts for:



6 h



12 h



18 h



24 h



30 h



36 h



48 h



D29C serves as the primary demonstration iceberg.



10\. Uncertainty



The empirical 24-hour uncertainty reference is based on held-out LOIO errors.



Horizon



&#x09;



P90 (km)









24 h



&#x09;



12.94



Longer forecast horizons use square-root-of-time scaling.



11\. Stochastic Ensemble



Validation showed:



only 2.04% empirical coverage



mean uncertainty radius: 0.40 km



mean actual error: 4.54 km



Therefore the stochastic ensemble is treated as a diagnostic experiment rather than a calibrated confidence model.



12\. Limitations



only 49 calibration pairs,



only 7 icebergs,



HYCOM historical gaps,



performance varies by iceberg,



uncertainty beyond 24 h uses heuristic scaling,



stochastic ensemble under-covers observed errors.



13\. Future Work



Future improvements include:



additional historical iceberg data,



improved HYCOM temporal coverage,



better uncertainty calibration,



time-varying environmental forecasts,



larger-scale operational validation.



14\. Conclusion



The calibrated physics-informed model successfully improves held-out iceberg drift prediction relative to persistence while maintaining scientifically defensible evaluation through LOIO validation.

