# Farm Size Prediction — Full Pipeline CI Report

**Generated:** 2026-04-04 15:23:28 UTC
**R Version:** R version 4.3.3 (2024-02-29)

## Summary

| Metric | Value |
|--------|-------|
| Total Scripts  | 46 |
| Passed         | 45 |
| Failed         | 1 |
| Total Time     | 424.2s |

## Per-Script Results

| Phase | Script | Status | Time | Note |
|-------|--------|--------|------|------|
| 00 | `00_synthetic_data` | ✅ PASS | 9.5s |  |
| 00 | `00_install_packages.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 00 | `00_download_spatial_data.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.2 | `01.2_chirps_summarize.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 02.1 | `02.1_compile_LSMS.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 05.2 | `05.2_RF_optimization_summary.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 08.1 | `08.1_predictions_by_country.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 04.4 | `04.4_RF_model_evaluation.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.1 | `01.1_chirps_download.R` | ✅ PASS | 1.8s |  |
| 01.3 | `01.3_chirps_trends.R` | ✅ PASS | 4.3s |  |
| 01.4 | `01.4_prepare_spatial_layers.R` | ✅ PASS | 3.1s |  |
| 02.2 | `02.2_harmonize_farm_area.R` | ✅ PASS | 3.8s |  |
| 02.3 | `02.3_measured_vs_reported.R` | ✅ PASS | 2s |  |
| 03.1 | `03.1_pooled_data.R` | ✅ PASS | 4.3s |  |
| 03.2 | `03.2_correlation_drivers.R` | ✅ PASS | 1.4s |  |
| 03.3 | `03.3_descriptive_stats.R` | ✅ PASS | 1.6s |  |
| 04.1 | `04.1_comparing_ML_algorithms.R` | ✅ PASS | 13s |  |
| 04.2 | `04.2_RF_within_country.R` | ✅ PASS | 2.7s |  |
| 04.3 | `04.3_RF_between_countries.R` | ✅ PASS | 24.3s |  |
| 04.5 | `04.5_cross_country_graphs.R` | ✅ PASS | 65.3s |  |
| 05.1 | `05.1_RF_optimization.R` | ✅ PASS | 3.7s |  |
| 05.3 | `05.3_RF_robustness.R` | ✅ PASS | 0.2s |  |
| 06.1 | `06.1_basic_RF_model.py` | ✅ PASS | 2.3s |  |
| 06.2 | `06.2_quantile_RF.py` | ✅ PASS | 3.1s |  |
| 06.1 | `06.1_quantile_RF.R` | ✅ PASS | 3.2s |  |
| 06.3 | `06.3_prediction_maps.R` | ✅ PASS | 5.3s |  |
| 06.4 | `06.4_cropland_sensitivity.R` | ✅ PASS | 15.7s |  |
| 07.2 | `07.2_QRF_distribution_eval.R` | ✅ PASS | 18.1s |  |
| 08.2 | `08.2_generate_virtual_farms.R` | ✅ PASS | 40.6s |  |
| 08.3 | `08.3_farm_size_classes.R` | ✅ PASS | 63.6s |  |
| 09.1 | `09.1_AEZ_characterization.R` | ✅ PASS | 9.6s |  |
| 10.1 | `10.1_prepare_validation_data.R` | ✅ PASS | 18.7s |  |
| 10.2 | `10.2_external_validation.R` | ✅ PASS | 9.6s |  |
| F01 | `F01_main_figure1.R` | ✅ PASS | 5s |  |
| F02 | `F02_main_figure2.R` | ✅ PASS | 4.5s |  |
| F03 | `F03_main_figure3.R` | ✅ PASS | 1.5s |  |
| S01 | `S01_drivers.R` | ✅ PASS | 1.4s |  |
| S02 | `S02_cropland_uncertainty.R` | ✅ PASS | 11.2s |  |
| S03 | `S03_aggregate_vs_disaggregate.R` | ✅ PASS | 34.1s |  |
| S04 | `S04_RF_hyperparameters.R` | ✅ PASS | 7.9s |  |
| S05 | `S05_RF_unseen_performance.R` | ✅ PASS | 5.2s |  |
| S06 | `S06_size_class_comparison.R` | ✅ PASS | 4.9s |  |
| S07 | `S07_distribution_parameters.R` | ✅ PASS | 5.5s |  |
| S08 | `S08_variable_importance.R` | ❌ FAIL | 8.8s | Exit code: 1 |
| T01 | `T01_area_production_tables.R` | ✅ PASS | 1.2s |  |
| T02 | `T02_heterogeneity_drivers.R` | ✅ PASS | 1.2s |  |
