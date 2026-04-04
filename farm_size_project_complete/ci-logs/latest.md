# CI Run Log
Run: 23978831223  Commit: 005a716100bc2a8c9e207c20fc795496b2ce77b1  Time: Sat Apr  4 12:29:48 UTC 2026

## Raw Output
```

======================================================================
FARM SIZE PREDICTION - FULL SEQUENTIAL PIPELINE TEST
======================================================================
Started: 2026-04-04 12:27:03.388192

Scripts dir: /home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/scripts

----------------------------------------------------------------------
PHASE 0: Synthetic Data Generation
----------------------------------------------------------------------
[00_synthetic_data.R]    Rasters done.
[00_synthetic_data.R]    Yearly rainfall stubs done.
[00_synthetic_data.R] 2. Creating synthetic LSMS survey data...
[00_synthetic_data.R]    LSMS CSV + RDS done  (6987 farms).
[00_synthetic_data.R] 3. Extracting predictors at farm locations...
[00_synthetic_data.R]    Analysis datasets done  (4137 farms in 95th trim).
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
[00_synthetic_data.R]    Leave-one stubs done (character means/test, TPS test-only).
[00_synthetic_data.R] 9. Creating country-year raw files...
[00_synthetic_data.R] 
[00_synthetic_data.R] ======================================================================
[00_synthetic_data.R] SYNTHETIC DATA GENERATION COMPLETE
[00_synthetic_data.R] ======================================================================
[00_synthetic_data.R]   Farms generated:   6987
[00_synthetic_data.R]   After 95th trim:   4137
[00_synthetic_data.R]   Countries:         16
[00_synthetic_data.R]   Raster layers:     11
[00_synthetic_data.R]   Training res:      0.5° (~56 km) — 14000 cells/layer
[00_synthetic_data.R]   Prediction res:    5° (~555 km) — 140 cells/layer (~3-9 per country)
[00_synthetic_data.R]   QRF stack cells:   140 cells × 100 quantiles = 14000 values
[00_synthetic_data.R]   Prediction stubs:  6 Python + RF + QRF rasters
[00_synthetic_data.R]   Output stubs:      0
[00_synthetic_data.R]   Processed files:   143
  ✓ PASS  00_synthetic_data                              (  7.8s)  
----------------------------------------------------------------------
PHASE 1: Install/Download Scripts (skipped in CI)
----------------------------------------------------------------------
  ✓ PASS  00_install_packages.R                          (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  00_download_spatial_data.R                     (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  01.2_chirps_summarize.R                        (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  02.1_compile_LSMS.R                            (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  05.2_RF_optimization_summary.R                 (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  08.1_predictions_by_country.R                  (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  04.4_RF_model_evaluation.R                     (  0.0s)  SKIPPED (download/SLURM/timeout script)
----------------------------------------------------------------------
PHASE 2: Raw Data Compilation (01.x – 02.x)
----------------------------------------------------------------------
[01.1_chirps_download.R] [1/6] Creating directory structure...
[01.1_chirps_download.R]   Created 20 directories
[01.1_chirps_download.R] 
[01.1_chirps_download.R] [2/6] Setting configuration...
[01.1_chirps_download.R]   Countries: 16
[01.1_chirps_download.R]   Target farms: 5000
[01.1_chirps_download.R] 
[01.1_chirps_download.R] [3/6] Generating synthetic spatial predictor grid...
[01.1_chirps_download.R]   Grid points: 2000
[01.1_chirps_download.R]   Predictors: 13
[01.1_chirps_download.R]   Saved: cattle-glw2010/ (ML predictor)
[01.1_chirps_download.R]   Saved: cattle-du2025/ (Figure 3)
[01.1_chirps_download.R] 
[01.1_chirps_download.R] [4/6] Generating synthetic LSMS farm data...
[01.1_chirps_download.R]   Generated 4291 synthetic farms
[01.1_chirps_download.R]   Countries: 16
[01.1_chirps_download.R] 
[01.1_chirps_download.R] [5/6] Creating analysis-ready datasets...
[01.1_chirps_download.R]   Extracting predictor values at farm locations...
[01.1_chirps_download.R]   Trimmed datasets: 95th (4070), 99th (4236)
[01.1_chirps_download.R] 
[01.1_chirps_download.R] [6/6] Generating descriptive statistics...
[01.1_chirps_download.R] 
[01.1_chirps_download.R] 
[01.1_chirps_download.R] ======================================================================
[01.1_chirps_download.R] SYNTHETIC DATA GENERATION COMPLETE
[01.1_chirps_download.R] ======================================================================
[01.1_chirps_download.R] 
[01.1_chirps_download.R] Generated files:
[01.1_chirps_download.R]   Processed data: 115
[01.1_chirps_download.R]   Output tables:  0
[01.1_chirps_download.R] 
[01.1_chirps_download.R] Data summary:
[01.1_chirps_download.R]   Total farms:    4291
[01.1_chirps_download.R]   Countries:      16
[01.1_chirps_download.R]   Farm size range:0.1-21.18ha
[01.1_chirps_download.R]   Median farm:    1.33ha
[01.1_chirps_download.R] 
[01.1_chirps_download.R] Finished: 2026-04-04 12:27:13.200346
[01.1_chirps_download.R] ======================================================================
  ✓ PASS  01.1_chirps_download.R                         (  1.8s)  
[01.3_chirps_trends.R] Loading required package: terra
[01.3_chirps_trends.R] terra 1.9.11
[01.3_chirps_trends.R] Loading required package: geodata
[01.3_chirps_trends.R] === Loading SSA boundaries ===
[01.3_chirps_trends.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm3.6/gadm36_adm0_r5_pk.rds'
[01.3_chirps_trends.R] Content type 'unknown' length 711937 bytes (695 KB)
[01.3_chirps_trends.R] ==================================================
[01.3_chirps_trends.R] downloaded 695 KB
[01.3_chirps_trends.R] 
[01.3_chirps_trends.R] SSA countries loaded: 44
[01.3_chirps_trends.R] Created: ../data/raw/spatial/rainfall/rainfall_monthly
[01.3_chirps_trends.R] 
[01.3_chirps_trends.R] === Processing CHIRPS data ===
[01.3_chirps_trends.R] CI: No CHIRPS tifs found — skipping 01.3
  ✓ PASS  01.3_chirps_trends.R                           (  3.5s)  
[01.4_prepare_spatial_layers.R] Loading required package: terra
[01.4_prepare_spatial_layers.R] terra 1.9.11
[01.4_prepare_spatial_layers.R] === Loading yearly rainfall data ===
[01.4_prepare_spatial_layers.R] Found 5 yearly rasters
[01.4_prepare_spatial_layers.R] Loaded raster stack with 5 layers
[01.4_prepare_spatial_layers.R] Years: NA to NA
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R] === Calculating long-term statistics ===
[01.4_prepare_spatial_layers.R] Calculating mean...
[01.4_prepare_spatial_layers.R] Calculating standard deviation...
[01.4_prepare_spatial_layers.R] Calculating coefficient of variation...
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R] === Generating preview plots ===
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R] === Saving outputs ===
[01.4_prepare_spatial_layers.R] Saved: ../data/raw/spatial/rainfall/rainfall_yearly/#_long_term_rainfall_avg.tif
[01.4_prepare_spatial_layers.R] Saved: ../data/raw/spatial/rainfall/rainfall_yearly/#_long_term_rainfall_cv.tif
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R] === Summary Statistics ===
[01.4_prepare_spatial_layers.R] Mean Annual Rainfall (mm):
[01.4_prepare_spatial_layers.R]   Min:    443.1
[01.4_prepare_spatial_layers.R]   Median: 1000.3
[01.4_prepare_spatial_layers.R]   Max:    1596.8
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R] Rainfall CV:
[01.4_prepare_spatial_layers.R]   Min:    0.019
[01.4_prepare_spatial_layers.R]   Median: 0.276
[01.4_prepare_spatial_layers.R]   Max:    1.077
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R]   % area with high variability (CV > 0.3): 41.8%
  ✓ PASS  01.4_prepare_spatial_layers.R                  (  3.1s)  
[02.2_harmonize_farm_area.R] Loading required package: tidyverse
[02.2_harmonize_farm_area.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[02.2_harmonize_farm_area.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[02.2_harmonize_farm_area.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[02.2_harmonize_farm_area.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[02.2_harmonize_farm_area.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[02.2_harmonize_farm_area.R] ✔ purrr     1.2.1     
[02.2_harmonize_farm_area.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[02.2_harmonize_farm_area.R] ✖ dplyr::filter() masks stats::filter()
[02.2_harmonize_farm_area.R] ✖ dplyr::lag()    masks stats::lag()
[02.2_harmonize_farm_area.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[02.2_harmonize_farm_area.R] 
[02.2_harmonize_farm_area.R] ======================================================================
[02.2_harmonize_farm_area.R] PROCESSING: ETHIOPIA
[02.2_harmonize_farm_area.R] ======================================================================
[02.2_harmonize_farm_area.R] 
[02.2_harmonize_farm_area.R] --- Ethiopia 2018 ---
[02.2_harmonize_farm_area.R]   WARNING: Ethiopia 2018 data not found
[02.2_harmonize_farm_area.R] 
[02.2_harmonize_farm_area.R] ======================================================================
[02.2_harmonize_farm_area.R] LSMS COMPILATION COMPLETE
[02.2_harmonize_farm_area.R] ======================================================================
  ✓ PASS  02.2_harmonize_farm_area.R                     (  3.8s)  
[02.3_measured_vs_reported.R] 
[02.3_measured_vs_reported.R] === Calculating harmonized plot area ===
[02.3_measured_vs_reported.R] 
[02.3_measured_vs_reported.R] === Aggregating to farm level ===
[02.3_measured_vs_reported.R] Farms excluded (missing plot data): 0
[02.3_measured_vs_reported.R] Farms with complete data: 4291
[02.3_measured_vs_reported.R] Farms with ALL plots measured: 3024 (70.5% of total)
[02.3_measured_vs_reported.R] 
[02.3_measured_vs_reported.R] === Integrating Zambia RALS data ===
[02.3_measured_vs_reported.R] WARNING: Zambia RALS file not found
[02.3_measured_vs_reported.R] Total farms (LSMS + Zambia): 4291
[02.3_measured_vs_reported.R] 
[02.3_measured_vs_reported.R] === Summary Statistics ===
[02.3_measured_vs_reported.R] # A tibble: 16 × 5
[02.3_measured_vs_reported.R]    country       n_farms median_ha mean_ha sd_ha
[02.3_measured_vs_reported.R]    <chr>           <int>     <dbl>   <dbl> <dbl>
[02.3_measured_vs_reported.R]  1 Benin             313      1.22    1.69  1.5 
[02.3_measured_vs_reported.R]  2 Burkina           288      1.38    1.85  1.83
[02.3_measured_vs_reported.R]  3 Cote_d_Ivoire     313      1.39    1.76  1.29
[02.3_measured_vs_reported.R]  4 Ethiopia          313      1.4     1.88  1.82
[02.3_measured_vs_reported.R]  5 Ghana             313      1.33    1.74  1.55
[02.3_measured_vs_reported.R]  6 Guinea_Bissau     272      1.34    1.86  1.87
[02.3_measured_vs_reported.R]  7 Malawi            313      1.39    1.91  1.87
[02.3_measured_vs_reported.R]  8 Mali               46      1.35    2.03  1.87
[02.3_measured_vs_reported.R]  9 Niger              38      1.14    1.42  0.91
[02.3_measured_vs_reported.R] 10 Nigeria           313      1.41    2.12  2.32
[02.3_measured_vs_reported.R] 11 Rwanda            313      1.47    1.97  1.73
[02.3_measured_vs_reported.R] 12 Senegal           205      1.44    1.86  1.55
[02.3_measured_vs_reported.R] 13 Tanzania          313      1.24    1.7   1.61
[02.3_measured_vs_reported.R] 14 Togo              312      1.35    1.72  1.34
[02.3_measured_vs_reported.R] 15 Uganda            313      1.17    1.78  1.62
[02.3_measured_vs_reported.R] 16 Zambia            313      1.25    1.75  1.67
[02.3_measured_vs_reported.R] 
[02.3_measured_vs_reported.R] === Saving outputs ===
[02.3_measured_vs_reported.R] Saved: lsms_number_of_farms_all_inclusive.csv
[02.3_measured_vs_reported.R] Saved: lsms_raw_data.csv
[02.3_measured_vs_reported.R] Saved: lsms_and_zambia.csv
[02.3_measured_vs_reported.R] Saved: lsms_and_zambia.rds
[02.3_measured_vs_reported.R] 
[02.3_measured_vs_reported.R] === Processing Complete ===
  ✓ PASS  02.3_measured_vs_reported.R                    (  2.1s)  
----------------------------------------------------------------------
PHASE 3: Analysis Preparation (03.x)
----------------------------------------------------------------------
[03.1_pooled_data.R] Plots with both values (reported ≤ 100 ha): 3024
[03.1_pooled_data.R] Correlation (r): 0.986
[03.1_pooled_data.R] R-squared: 0.972
[03.1_pooled_data.R] 
[03.1_pooled_data.R] === Reporting Error Analysis ===
[03.1_pooled_data.R] Reported/Measured ratio:
[03.1_pooled_data.R]   Mean:   1
[03.1_pooled_data.R]   Median: 1
[03.1_pooled_data.R]   SD:     0.12
[03.1_pooled_data.R] 
[03.1_pooled_data.R]   Interpretation: No systematic bias in reporting
[03.1_pooled_data.R] 
[03.1_pooled_data.R] === By-Country Breakdown ===
[03.1_pooled_data.R] # A tibble: 16 × 3
[03.1_pooled_data.R]    country       n_measured pct_measured
[03.1_pooled_data.R]    <chr>              <int>        <dbl>
[03.1_pooled_data.R]  1 Tanzania             237          100
[03.1_pooled_data.R]  2 Benin                234          100
[03.1_pooled_data.R]  3 Ethiopia             231          100
[03.1_pooled_data.R]  4 Malawi               223          100
[03.1_pooled_data.R]  5 Zambia               223          100
[03.1_pooled_data.R]  6 Cote_d_Ivoire        220          100
[03.1_pooled_data.R]  7 Ghana                217          100
[03.1_pooled_data.R]  8 Nigeria              216          100
[03.1_pooled_data.R]  9 Rwanda               214          100
[03.1_pooled_data.R] 10 Togo                 213          100
[03.1_pooled_data.R] 11 Uganda               207          100
[03.1_pooled_data.R] 12 Burkina              202          100
[03.1_pooled_data.R] 13 Guinea_Bissau        195          100
[03.1_pooled_data.R] 14 Senegal              137          100
[03.1_pooled_data.R] 15 Mali                  28          100
[03.1_pooled_data.R] 16 Niger                 27          100
[03.1_pooled_data.R] 
[03.1_pooled_data.R] ==================================================
[03.1_pooled_data.R] SUMMARY
[03.1_pooled_data.R] ==================================================
[03.1_pooled_data.R] • 70.5% of plots have GPS measurements
[03.1_pooled_data.R] • Correlation between reported and measured: r = 0.986
[03.1_pooled_data.R] • Median reporting ratio: 1 (underreporting)
[03.1_pooled_data.R] • SD of reporting ratio: 0.12 (higher = more variable reporting)
  ✓ PASS  03.1_pooled_data.R                             (  1.2s)  
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Loading predictor layers ===
[03.2_correlation_drivers.R] Predictor layers: cropland, cattle, pop, cropland_per_capita, sand, elevation, slope, temperature, rainfall, market, maizeyield
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Loading LSMS data ===
[03.2_correlation_drivers.R] Initial farms: 4291
[03.2_correlation_drivers.R] After year filter (>2007): 4291
[03.2_correlation_drivers.R] Excluding small waves: 
[03.2_correlation_drivers.R] # A tibble: 3 × 3
[03.2_correlation_drivers.R]   country  year n_farms
[03.2_correlation_drivers.R]   <chr>   <int>   <int>
[03.2_correlation_drivers.R] 1 Mali     2014       3
[03.2_correlation_drivers.R] 2 Niger    2014       1
[03.2_correlation_drivers.R] 3 Niger    2016       4
[03.2_correlation_drivers.R] After sample size filter: 4283
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Assigning administrative divisions ===
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Removing conflict-affected areas ===
[03.2_correlation_drivers.R] Removed 0 farms from conflict areas
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Trimming outliers by region ===
[03.2_correlation_drivers.R] Untrimmed: 4283 farms
[03.2_correlation_drivers.R] 99th percentile trim: 3976 farms
[03.2_correlation_drivers.R] 95th percentile trim: 3881 farms
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Creating data distribution map ===
[03.2_correlation_drivers.R] null device 
[03.2_correlation_drivers.R]           1 
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Creating predictor stack ===
[03.2_correlation_drivers.R] Saved: stacked_rasters_africa.tif
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Extracting predictors at farm locations ===
[03.2_correlation_drivers.R] Saved: lsms_untrimmed_africa.rds (4283 farms)
[03.2_correlation_drivers.R] Saved: lsms_trimmed_99th_africa.rds (3976 farms)
[03.2_correlation_drivers.R] Saved: lsms_trimmed_95th_africa.rds (3881 farms)
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Processing Complete ===
[03.2_correlation_drivers.R] Final dataset: 3206 farms with complete predictor data
  ✓ PASS  03.2_correlation_drivers.R                     ( 36.3s)  
[03.3_descriptive_stats.R] Loading required package: tidyverse
[03.3_descriptive_stats.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[03.3_descriptive_stats.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[03.3_descriptive_stats.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[03.3_descriptive_stats.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[03.3_descriptive_stats.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[03.3_descriptive_stats.R] ✔ purrr     1.2.1     
[03.3_descriptive_stats.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[03.3_descriptive_stats.R] ✖ dplyr::filter() masks stats::filter()
[03.3_descriptive_stats.R] ✖ dplyr::lag()    masks stats::lag()
[03.3_descriptive_stats.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[03.3_descriptive_stats.R] Loading required package: GGally
[03.3_descriptive_stats.R] === Loading LSMS data ===
[03.3_descriptive_stats.R] Observations: 3206
[03.3_descriptive_stats.R] Variables: 11 predictors + target
[03.3_descriptive_stats.R] 
[03.3_descriptive_stats.R] === Creating correlation matrix ===
[03.3_descriptive_stats.R] null device 
[03.3_descriptive_stats.R]           1 
[03.3_descriptive_stats.R] Saved: drivers_correlation_matrix.png
[03.3_descriptive_stats.R] 
[03.3_descriptive_stats.R] === Correlation Summary ===
[03.3_descriptive_stats.R] 
[03.3_descriptive_stats.R] Correlations with farm_area_ha:
[03.3_descriptive_stats.R]   sand: r = 0.014
[03.3_descriptive_stats.R]   rainfall: r = 0.014
[03.3_descriptive_stats.R]   pop: r = 0.013
[03.3_descriptive_stats.R]   maizeyield: r = 0.012
[03.3_descriptive_stats.R]   market: r = 0.006
[03.3_descriptive_stats.R]   cattle: r = 0
[03.3_descriptive_stats.R]   slope: r = -0.001
[03.3_descriptive_stats.R]   cropland_per_capita: r = -0.008
[03.3_descriptive_stats.R]   temperature: r = -0.013
[03.3_descriptive_stats.R]   cropland: r = -0.02
[03.3_descriptive_stats.R] 
[03.3_descriptive_stats.R] === Analysis Complete ===
  ✓ PASS  03.3_descriptive_stats.R                       ( 18.1s)  
----------------------------------------------------------------------
PHASE 4: ML Model Training (04.x)
----------------------------------------------------------------------
[04.1_comparing_ML_algorithms.R] 
[04.1_comparing_ML_algorithms.R] === Creating summary table ===
[04.1_comparing_ML_algorithms.R] 
[04.1_comparing_ML_algorithms.R] === Summary Statistics ===
[04.1_comparing_ML_algorithms.R] # A tibble: 17 × 10
[04.1_comparing_ML_algorithms.R]    country    n_waves period n_obs prct_below_0.5 prct_below_1   q10   med   avg
[04.1_comparing_ML_algorithms.R]    <chr>        <int> <chr>  <int>          <dbl>        <dbl> <dbl> <dbl> <dbl>
[04.1_comparing_ML_algorithms.R]  1 Benin            6 2010-…   313           9.58         40.3  0.51  1.22  1.69
[04.1_comparing_ML_algorithms.R]  2 Burkina          6 2010-…   288          11.5          35.4  0.5   1.38  1.85
[04.1_comparing_ML_algorithms.R]  3 Cote_d_Iv…       6 2010-…   313           9.9          31.6  0.51  1.39  1.76
[04.1_comparing_ML_algorithms.R]  4 Ethiopia         6 2010-…   313          11.5          37.4  0.44  1.4   1.88
[04.1_comparing_ML_algorithms.R]  5 Ghana            6 2010-…   313          10.5          36.7  0.49  1.33  1.74
[04.1_comparing_ML_algorithms.R]  6 Guinea_Bi…       6 2010-…   272          10.7          35.7  0.5   1.34  1.86
[04.1_comparing_ML_algorithms.R]  7 Malawi           6 2010-…   313           9.58         34.5  0.52  1.39  1.91
[04.1_comparing_ML_algorithms.R]  8 Mali             6 2010-…    46          10.9          26.1  0.51  1.35  2.03
[04.1_comparing_ML_algorithms.R]  9 Niger            6 2010-…    38          10.5          34.2  0.5   1.14  1.42
[04.1_comparing_ML_algorithms.R] 10 Nigeria          6 2010-…   313           8.63         35.5  0.53  1.41  2.12
[04.1_comparing_ML_algorithms.R] 11 Rwanda           6 2010-…   313          12.1          34.5  0.45  1.47  1.97
[04.1_comparing_ML_algorithms.R] 12 Senegal          6 2010-…   205           8.78         32.7  0.54  1.44  1.86
[04.1_comparing_ML_algorithms.R] 13 Tanzania         6 2010-…   313          12.8          39.3  0.44  1.24  1.7 
[04.1_comparing_ML_algorithms.R] 14 Togo             6 2010-…   312          10.3          33.3  0.49  1.35  1.72
[04.1_comparing_ML_algorithms.R] 15 Uganda           6 2010-…   313          12.1          39.6  0.46  1.17  1.78
[04.1_comparing_ML_algorithms.R] 16 Zambia           6 2010-…   313          10.9          36.4  0.43  1.25  1.75
[04.1_comparing_ML_algorithms.R] 17 TOTAL           96 2010-…  4291          10.7          35.9  0.49  1.32  1.83
[04.1_comparing_ML_algorithms.R] # ℹ 1 more variable: q90 <dbl>
[04.1_comparing_ML_algorithms.R] 
[04.1_comparing_ML_algorithms.R] === Key Findings ===
[04.1_comparing_ML_algorithms.R] Total observations: 4,291
[04.1_comparing_ML_algorithms.R] Total survey waves: 96
[04.1_comparing_ML_algorithms.R] Period covered: 2010-2020
[04.1_comparing_ML_algorithms.R] 
[04.1_comparing_ML_algorithms.R] Farm size distribution:
[04.1_comparing_ML_algorithms.R]   10th percentile: 0.49 ha
[04.1_comparing_ML_algorithms.R]   Median: 1.32 ha
[04.1_comparing_ML_algorithms.R]   Mean: 1.83 ha
[04.1_comparing_ML_algorithms.R]   90th percentile: 3.71 ha
[04.1_comparing_ML_algorithms.R] 
[04.1_comparing_ML_algorithms.R] Small farms:
[04.1_comparing_ML_algorithms.R]   < 0.5 ha: 10.67%
[04.1_comparing_ML_algorithms.R]   < 1.0 ha: 35.89%
  ✓ PASS  04.1_comparing_ML_algorithms.R                 (  1.3s)  
[04.2_RF_within_country.R] fields::Tps(x = with(my_lsms_cty, cbind(x, y)), Y = my_lsms_cty[, 
[04.2_RF_within_country.R]     "farm_area_ha"], lon.lat = T, Z = as.matrix(my_lsms_cty[, 
[04.2_RF_within_country.R]     c("cropland", "cattle", "pop", "cropland_per_capita", "sand", 
[04.2_RF_within_country.R]         "slope", "temperature", "rainfall", "market", "maizeyield")]))
[04.2_RF_within_country.R]                                                  
[04.2_RF_within_country.R]  Number of Observations:                216      
[04.2_RF_within_country.R]  Number of parameters in the null space 13       
[04.2_RF_within_country.R]  Parameters for fixed spatial drift     3        
[04.2_RF_within_country.R]  Model degrees of freedom:              13       
[04.2_RF_within_country.R]  Residual degrees of freedom:           203      
[04.2_RF_within_country.R]  GCV estimate for tau:                  1.051    
[04.2_RF_within_country.R]  MLE for tau:                           1.019    
[04.2_RF_within_country.R]  MLE for sigma:                         3.754e-07
[04.2_RF_within_country.R]  lambda                                 2800000  
[04.2_RF_within_country.R]  User supplied sigma                    NA       
[04.2_RF_within_country.R]  User supplied tau^2                    NA       
[04.2_RF_within_country.R] Summary of estimates: 
[04.2_RF_within_country.R]             lambda      trA      GCV   tauHat -lnLike Prof converge
[04.2_RF_within_country.R] GCV        2764213 13.00106 1.174795 1.050754     298.0952       NA
[04.2_RF_within_country.R] GCV.model       NA       NA       NA       NA           NA       NA
[04.2_RF_within_country.R] GCV.one    2764213 13.00106 1.174795 1.050754           NA       NA
[04.2_RF_within_country.R] RMSE            NA       NA       NA       NA           NA       NA
[04.2_RF_within_country.R] pure error      NA       NA       NA       NA           NA       NA
[04.2_RF_within_country.R] REML       2764213 13.00106 1.174795 1.050754     298.0952       NA
[04.2_RF_within_country.R] [1] "calculated_70-30_r2 = 0.03"
[04.2_RF_within_country.R] [1] "CV_r2 = NA"
[04.2_RF_within_country.R] [1] "TPS_rsq_with_covariate = NA"
[04.2_RF_within_country.R] [1] NA
[04.2_RF_within_country.R] Something is wrong; all the RMSE metric values are missing:
[04.2_RF_within_country.R]       RMSE        Rsquared        MAE     
[04.2_RF_within_country.R]  Min.   : NA   Min.   : NA   Min.   : NA  
[04.2_RF_within_country.R]  1st Qu.: NA   1st Qu.: NA   1st Qu.: NA  
[04.2_RF_within_country.R]  Median : NA   Median : NA   Median : NA  
[04.2_RF_within_country.R]  Mean   :NaN   Mean   :NaN   Mean   :NaN  
[04.2_RF_within_country.R]  3rd Qu.: NA   3rd Qu.: NA   3rd Qu.: NA  
[04.2_RF_within_country.R]  Max.   : NA   Max.   : NA   Max.   : NA  
[04.2_RF_within_country.R]  NA's   :108   NA's   :108   NA's   :108  
[04.2_RF_within_country.R] CI-SKIP Zambia: Stopping
[04.2_RF_within_country.R] There were 50 or more warnings (use warnings() to see the first 50)
[04.2_RF_within_country.R] Time difference of 44.43993 secs
  ✓ PASS  04.2_RF_within_country.R                       ( 48.3s)  
```

## Pipeline Report
# Farm Size Prediction — Full Pipeline CI Report

**Generated:** 2026-04-04 12:18:31 UTC
**R Version:** R version 4.3.3 (2024-02-29)

## Summary

| Metric | Value |
|--------|-------|
| Total Scripts  | 44 |
| Passed         | 43 |
| Failed         | 1 |
| Total Time     | 386.8s |

## Per-Script Results

| Phase | Script | Status | Time | Note |
|-------|--------|--------|------|------|
| 00 | `00_synthetic_data` | ✅ PASS | 7.3s |  |
| 00 | `00_install_packages.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 00 | `00_download_spatial_data.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.2 | `01.2_chirps_summarize.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 02.1 | `02.1_compile_LSMS.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 05.2 | `05.2_RF_optimization_summary.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 08.1 | `08.1_predictions_by_country.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 04.4 | `04.4_RF_model_evaluation.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.1 | `01.1_chirps_download.R` | ✅ PASS | 1.8s |  |
| 01.3 | `01.3_chirps_trends.R` | ✅ PASS | 3.7s |  |
| 01.4 | `01.4_prepare_spatial_layers.R` | ✅ PASS | 3s |  |
| 02.2 | `02.2_harmonize_farm_area.R` | ✅ PASS | 3.6s |  |
| 02.3 | `02.3_measured_vs_reported.R` | ✅ PASS | 1.9s |  |
| 03.1 | `03.1_pooled_data.R` | ✅ PASS | 1.1s |  |
| 03.2 | `03.2_correlation_drivers.R` | ✅ PASS | 43.7s |  |
| 03.3 | `03.3_descriptive_stats.R` | ✅ PASS | 17.7s |  |
| 04.1 | `04.1_comparing_ML_algorithms.R` | ✅ PASS | 1.2s |  |
| 04.2 | `04.2_RF_within_country.R` | ✅ PASS | 44.4s |  |
| 04.3 | `04.3_RF_between_countries.R` | ✅ PASS | 70.4s |  |
| 04.5 | `04.5_cross_country_graphs.R` | ✅ PASS | 0.2s |  |
| 05.1 | `05.1_RF_optimization.R` | ✅ PASS | 3.4s |  |
| 05.3 | `05.3_RF_robustness.R` | ✅ PASS | 0.2s |  |
| 06.1 | `06.1_quantile_RF.R` | ✅ PASS | 2.9s |  |
| 06.3 | `06.3_prediction_maps.R` | ✅ PASS | 4.9s |  |
| 06.4 | `06.4_cropland_sensitivity.R` | ✅ PASS | 13.1s |  |
| 07.2 | `07.2_QRF_distribution_eval.R` | ✅ PASS | 16.7s |  |
| 08.2 | `08.2_generate_virtual_farms.R` | ✅ PASS | 15.2s |  |
| 08.3 | `08.3_farm_size_classes.R` | ❌ FAIL | 7s | Exit code: 1 |
| 09.1 | `09.1_AEZ_characterization.R` | ✅ PASS | 8.6s |  |
| 10.1 | `10.1_prepare_validation_data.R` | ✅ PASS | 15.9s |  |
| 10.2 | `10.2_external_validation.R` | ✅ PASS | 5.5s |  |
| F01 | `F01_main_figure1.R` | ✅ PASS | 4.6s |  |
| F02 | `F02_main_figure2.R` | ✅ PASS | 4.5s |  |
| F03 | `F03_main_figure3.R` | ✅ PASS | 6.9s |  |
| S01 | `S01_drivers.R` | ✅ PASS | 1.5s |  |
| S02 | `S02_cropland_uncertainty.R` | ✅ PASS | 10.4s |  |
| S03 | `S03_aggregate_vs_disaggregate.R` | ✅ PASS | 31.8s |  |
| S04 | `S04_RF_hyperparameters.R` | ✅ PASS | 7.6s |  |
| S05 | `S05_RF_unseen_performance.R` | ✅ PASS | 4.9s |  |
| S06 | `S06_size_class_comparison.R` | ✅ PASS | 4.8s |  |
| S07 | `S07_distribution_parameters.R` | ✅ PASS | 5.1s |  |
| S08 | `S08_variable_importance.R` | ✅ PASS | 8.2s |  |
| T01 | `T01_area_production_tables.R` | ✅ PASS | 1.1s |  |
| T02 | `T02_heterogeneity_drivers.R` | ✅ PASS | 1.1s |  |
