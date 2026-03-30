# CI Run Log
Run: 23732134129  Commit: e7267801d9717952c0c2215aaf319a15c3b314c8  Time: Mon Mar 30 07:04:44 UTC 2026

## Raw Output
```

======================================================================
FARM SIZE PREDICTION - FULL SEQUENTIAL PIPELINE TEST
======================================================================
Started: 2026-03-30 07:04:35.591011

Scripts dir: /home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/scripts

----------------------------------------------------------------------
PHASE 0: Synthetic Data Generation
----------------------------------------------------------------------
[00_synthetic_data.R] === FULL Synthetic Data Generation for CI ===
[00_synthetic_data.R] 
[00_synthetic_data.R] terra 1.9.11
[00_synthetic_data.R] terra: OK  dplyr: OK
[00_synthetic_data.R] 1. Creating synthetic rasters...
[00_synthetic_data.R]    Rasters done.
[00_synthetic_data.R]    Yearly rainfall stubs done.
[00_synthetic_data.R] 2. Creating synthetic LSMS survey data...
[00_synthetic_data.R]    LSMS CSV + RDS done  (7001 farms).
[00_synthetic_data.R] 3. Extracting predictors at farm locations...
[00_synthetic_data.R]    Analysis datasets done  (4132 farms in 95th trim).
[00_synthetic_data.R] 4. Creating synthetic GADM boundaries...
[00_synthetic_data.R]    GADM boundaries done.
[00_synthetic_data.R] 5. Creating output table stubs...
[00_synthetic_data.R]    Output stubs done.
[00_synthetic_data.R] 6. Creating processed data stubs...
[00_synthetic_data.R]    RF model stub done.
[00_synthetic_data.R]    AEZ stub written (6 classes, spatially structured).
[00_synthetic_data.R]    SPAM stubs written (spam2010, spam2017 × _H/_P/_V × 8 crops).
[00_synthetic_data.R]    back_transf rasters written.
[00_synthetic_data.R]    Processed stubs done.
[00_synthetic_data.R] 6b. Creating Sarah Lowder xlsx stubs...
[00_synthetic_data.R]    mmc3 done (22 countries, total farms range 2e+05–1.4e+07)
[00_synthetic_data.R] There were 15 warnings (use warnings() to see them)
[00_synthetic_data.R]    mmc5 done (44 rows = 22 countries × F+A)
[00_synthetic_data.R]    mmc7 done (88 rows = 22 countries × 4 decades)
[00_synthetic_data.R] 7. Creating figure stubs...
[00_synthetic_data.R]    Figure stubs done.
[00_synthetic_data.R] 8b. Creating leave-one stubs for 04.5 / 04.6...
[00_synthetic_data.R] Error in gzfile(file, mode) : cannot open the connection
[00_synthetic_data.R] Calls: saveRDS -> saveRDS -> gzfile
[00_synthetic_data.R] In addition: Warning message:
[00_synthetic_data.R] In gzfile(file, mode) :
[00_synthetic_data.R]   cannot open compressed file '../output/tables/leave_one_RF.rds', probable reason 'No such file or directory'
[00_synthetic_data.R] Execution halted
  ✗ FAIL  00_synthetic_data                              (  8.7s)  Exit code: 1

FATAL: synthetic data generation failed — cannot continue.
```

## Pipeline Report
# Farm Size Prediction — Full Pipeline CI Report

**Generated:** 2026-03-30 01:30:19 UTC
**R Version:** R version 4.3.3 (2024-02-29)

## Summary

| Metric | Value |
|--------|-------|
| Total Scripts  | 44 |
| Passed         | 41 |
| Failed         | 3 |
| Total Time     | 439.4s |

## Per-Script Results

| Phase | Script | Status | Time | Note |
|-------|--------|--------|------|------|
| 00 | `00_synthetic_data` | ✅ PASS | 8.3s |  |
| 00 | `00_install_packages.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 00 | `00_download_spatial_data.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.2 | `01.2_chirps_summarize.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 02.1 | `02.1_compile_LSMS.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 05.2 | `05.2_RF_optimization_summary.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 08.1 | `08.1_predictions_by_country.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 04.4 | `04.4_RF_model_evaluation.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.1 | `01.1_chirps_download.R` | ✅ PASS | 1.9s |  |
| 01.3 | `01.3_chirps_trends.R` | ✅ PASS | 4.4s |  |
| 01.4 | `01.4_prepare_spatial_layers.R` | ✅ PASS | 3.4s |  |
| 02.2 | `02.2_harmonize_farm_area.R` | ✅ PASS | 4.1s |  |
| 02.3 | `02.3_measured_vs_reported.R` | ✅ PASS | 2.2s |  |
| 03.1 | `03.1_pooled_data.R` | ✅ PASS | 1.3s |  |
| 03.2 | `03.2_correlation_drivers.R` | ✅ PASS | 48.4s |  |
| 03.3 | `03.3_descriptive_stats.R` | ✅ PASS | 19.2s |  |
| 04.1 | `04.1_comparing_ML_algorithms.R` | ✅ PASS | 1.4s |  |
| 04.2 | `04.2_RF_within_country.R` | ✅ PASS | 51.2s |  |
| 04.3 | `04.3_RF_between_countries.R` | ✅ PASS | 76s |  |
| 04.5 | `04.5_cross_country_graphs.R` | ✅ PASS | 0.3s |  |
| 05.1 | `05.1_RF_optimization.R` | ✅ PASS | 4s |  |
| 05.3 | `05.3_RF_robustness.R` | ✅ PASS | 0.2s |  |
| 06.1 | `06.1_quantile_RF.R` | ✅ PASS | 3.4s |  |
| 06.3 | `06.3_prediction_maps.R` | ✅ PASS | 5.7s |  |
| 06.4 | `06.4_cropland_sensitivity.R` | ✅ PASS | 14.9s |  |
| 07.2 | `07.2_QRF_distribution_eval.R` | ✅ PASS | 19.4s |  |
| 08.2 | `08.2_generate_virtual_farms.R` | ✅ PASS | 17s |  |
| 08.3 | `08.3_farm_size_classes.R` | ❌ FAIL | 4.8s | Exit code: 1 |
| 09.1 | `09.1_AEZ_characterization.R` | ✅ PASS | 9.8s |  |
| 10.1 | `10.1_prepare_validation_data.R` | ✅ PASS | 18s |  |
| 10.2 | `10.2_external_validation.R` | ✅ PASS | 6.7s |  |
| F01 | `F01_main_figure1.R` | ❌ FAIL | 4.4s | Exit code: 1 |
| F02 | `F02_main_figure2.R` | ✅ PASS | 5.1s |  |
| F03 | `F03_main_figure3.R` | ✅ PASS | 8s |  |
| S01 | `S01_drivers.R` | ✅ PASS | 1.7s |  |
| S02 | `S02_cropland_uncertainty.R` | ✅ PASS | 11.6s |  |
| S03 | `S03_aggregate_vs_disaggregate.R` | ✅ PASS | 36s |  |
| S04 | `S04_RF_hyperparameters.R` | ✅ PASS | 8.3s |  |
| S05 | `S05_RF_unseen_performance.R` | ✅ PASS | 5.5s |  |
| S06 | `S06_size_class_comparison.R` | ✅ PASS | 5.6s |  |
| S07 | `S07_distribution_parameters.R` | ✅ PASS | 5.8s |  |
| S08 | `S08_variable_importance.R` | ✅ PASS | 9.3s |  |
| T01 | `T01_area_production_tables.R` | ✅ PASS | 5.4s |  |
| T02 | `T02_heterogeneity_drivers.R` | ❌ FAIL | 5.9s | Exit code: 1 |
