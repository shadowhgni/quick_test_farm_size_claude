# Farm Size Prediction — Full Pipeline CI Report

**Generated:** 2026-04-07 07:32:45 UTC
**R Version:** R version 4.3.3 (2024-02-29)

## Summary

| Metric | Value |
|--------|-------|
| Total Scripts  | 46 |
| Passed         | 46 |
| Failed         | 0 |
| Total Time     | 414.6s |

## Per-Script Results

| Phase | Script | Status | Time | Note |
|-------|--------|--------|------|------|
| 00 | `00_synthetic_data` | ✅ PASS | 9.6s |  |
| 00.1 | `00.1_install_packages.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 00.2 | `00.2_download_spatial_data.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.2 | `01.2_chirps_summarize.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 02.1 | `02.1_compile_LSMS.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 05.2 | `05.2_RF_optimization_summary.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 08.1 | `08.1_predictions_by_country.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 04.4 | `04.4_RF_model_evaluation.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.1 | `01.1_chirps_download.R` | ✅ PASS | 1.8s |  |
| 01.3 | `01.3_chirps_trends.R` | ✅ PASS | 4.1s |  |
| 01.4 | `01.4_prepare_spatial_layers.R` | ✅ PASS | 3.2s |  |
| 02.2 | `02.2_harmonize_farm_area.R` | ✅ PASS | 3.8s |  |
| 02.3 | `02.3_measured_vs_reported.R` | ✅ PASS | 2s |  |
| 03.1 | `03.1_pooled_data.R` | ✅ PASS | 4.2s |  |
| 03.2 | `03.2_correlation_drivers.R` | ✅ PASS | 1.8s |  |
| 03.3 | `03.3_descriptive_stats.R` | ✅ PASS | 1.6s |  |
| 04.1 | `04.1_comparing_ML_algorithms.R` | ✅ PASS | 13.1s |  |
| 04.2 | `04.2_RF_within_country.R` | ✅ PASS | 2.7s |  |
| 04.3 | `04.3_RF_between_countries.R` | ✅ PASS | 24s |  |
| 04.5 | `04.5_cross_country_graphs.R` | ✅ PASS | 65.3s |  |
| 05.1 | `05.1_RF_optimization.R` | ✅ PASS | 3.7s |  |
| 05.3 | `05.3_RF_robustness.R` | ✅ PASS | 0.2s |  |
| 06.1 | `06.1_basic_RF_model.py` | ✅ PASS | 2.9s |  |
| 06.2 | `06.2_quantile_RF.py` | ✅ PASS | 1.4s |  |
| 06.1 | `06.1_quantile_RF.R` | ✅ PASS | 3.5s |  |
| 06.3 | `06.3_prediction_maps.R` | ✅ PASS | 5.3s |  |
| 06.4 | `06.4_cropland_sensitivity.R` | ✅ PASS | 16s |  |
| 07.1 | `07.1_QRF_distribution_eval.R` | ✅ PASS | 17.9s |  |
| 08.2 | `08.2_generate_virtual_farms.R` | ✅ PASS | 34.8s |  |
| 08.3 | `08.3_farm_size_classes.R` | ✅ PASS | 63.2s |  |
| 09.1 | `09.1_AEZ_characterization.R` | ✅ PASS | 9.7s |  |
| 10.1 | `10.1_prepare_validation_data.R` | ✅ PASS | 18.8s |  |
| 10.2 | `10.2_external_validation.R` | ✅ PASS | 9.8s |  |
| F01 | `F01_main_figure1.R` | ✅ PASS | 4.8s |  |
| F02 | `F02_main_figure2.R` | ✅ PASS | 4.5s |  |
| F03 | `F03_main_figure3.R` | ✅ PASS | 1.5s |  |
| S01 | `S01_drivers.R` | ✅ PASS | 1.5s |  |
| S02 | `S02_cropland_uncertainty.R` | ✅ PASS | 11.4s |  |
| S03 | `S03_aggregate_vs_disaggregate.R` | ✅ PASS | 33.4s |  |
| S04 | `S04_RF_hyperparameters.R` | ✅ PASS | 7.9s |  |
| S05 | `S05_RF_unseen_performance.R` | ✅ PASS | 5.3s |  |
| S06 | `S06_size_class_comparison.R` | ✅ PASS | 2.4s |  |
| S07 | `S07_distribution_parameters.R` | ✅ PASS | 5.5s |  |
| S08 | `S08_variable_importance.R` | ✅ PASS | 8.9s |  |
| T01 | `T01_area_production_tables.R` | ✅ PASS | 1.2s |  |
| T02 | `T02_heterogeneity_drivers.R` | ✅ PASS | 1.2s |  |
