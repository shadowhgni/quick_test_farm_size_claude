# CI Run Log
Run: 23739615408  Commit: 774e0a3b39b4169c72d0b8b425f772ff3871e695  Time: Mon Mar 30 10:23:46 UTC 2026

## Raw Output
```

======================================================================
FARM SIZE PREDICTION - FULL SEQUENTIAL PIPELINE TEST
======================================================================
Started: 2026-03-30 10:17:06.79001

Scripts dir: /home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/scripts

----------------------------------------------------------------------
PHASE 0: Synthetic Data Generation
----------------------------------------------------------------------
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
[00_synthetic_data.R]    Leave-one stubs done (character means/test, TPS test-only).
[00_synthetic_data.R] 9. Creating country-year raw files...
[00_synthetic_data.R] 
[00_synthetic_data.R] ======================================================================
[00_synthetic_data.R] SYNTHETIC DATA GENERATION COMPLETE
[00_synthetic_data.R] ======================================================================
[00_synthetic_data.R]   Farms generated:   7001
[00_synthetic_data.R]   After 95th trim:   4132
[00_synthetic_data.R]   Countries:         16
[00_synthetic_data.R]   Raster layers:     11
[00_synthetic_data.R]   Training res:      0.5° (~56 km) — 14000 cells/layer
[00_synthetic_data.R]   Prediction res:    5° (~555 km) — 140 cells/layer (~3-9 per country)
[00_synthetic_data.R]   QRF stack cells:   140 cells × 100 quantiles = 14000 values
[00_synthetic_data.R]   Prediction stubs:  6 Python + RF + QRF rasters
[00_synthetic_data.R]   Output stubs:      0
[00_synthetic_data.R]   Processed files:   143
  ✓ PASS  00_synthetic_data                              (  7.6s)  
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
[01.1_chirps_download.R] Finished: 2026-03-30 10:17:16.406052
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
  ✓ PASS  01.3_chirps_trends.R                           (  4.1s)  
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
[01.4_prepare_spatial_layers.R]   Min:    438.1
[01.4_prepare_spatial_layers.R]   Median: 999.6
[01.4_prepare_spatial_layers.R]   Max:    1590.6
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R] Rainfall CV:
[01.4_prepare_spatial_layers.R]   Min:    0.019
[01.4_prepare_spatial_layers.R]   Median: 0.276
[01.4_prepare_spatial_layers.R]   Max:    1.086
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R]   % area with high variability (CV > 0.3): 41.7%
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
  ✓ PASS  02.2_harmonize_farm_area.R                     (  3.7s)  
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
  ✓ PASS  02.3_measured_vs_reported.R                    (  2.0s)  
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
  ✓ PASS  03.2_correlation_drivers.R                     ( 44.4s)  
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
  ✓ PASS  03.3_descriptive_stats.R                       ( 17.8s)  
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
  ✓ PASS  04.1_comparing_ML_algorithms.R                 (  1.2s)  
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
[04.2_RF_within_country.R] Time difference of 43.08728 secs
  ✓ PASS  04.2_RF_within_country.R                       ( 46.8s)  
[04.3_RF_between_countries.R] 21  Uganda          Apac      0.01            0             0.69
[04.3_RF_between_countries.R] 22  Uganda        Masaka      0.01            0                1
[04.3_RF_between_countries.R] 23  Uganda       Kayunga      0.02            0             <NA>
[04.3_RF_between_countries.R] 24  Uganda        Kitgum         0            0             <NA>
[04.3_RF_between_countries.R] 25  Uganda        Moroto         0            0             <NA>
[04.3_RF_between_countries.R] 26  Uganda        Kamuli      0.04         0.01                0
[04.3_RF_between_countries.R] 27  Uganda        Luwero         0            0             <NA>
[04.3_RF_between_countries.R] 28  Uganda       Pallisa      0.03         0.01             <NA>
[04.3_RF_between_countries.R] 29  Uganda        Soroti      0.01         0.01             <NA>
[04.3_RF_between_countries.R] 30  Uganda         Hoima      0.04            0             <NA>
[04.3_RF_between_countries.R] 31  Uganda        Bugiri         0            0             <NA>
[04.3_RF_between_countries.R] 32  Uganda        Kabale      0.02            0             <NA>
[04.3_RF_between_countries.R] 33  Uganda Nakapiripirit      0.01            0             <NA>
[04.3_RF_between_countries.R] 34  Uganda         Nebbi      0.04         0.01             <NA>
[04.3_RF_between_countries.R] 35  Uganda        Mayuge      0.01         0.01             <NA>
[04.3_RF_between_countries.R] 36  Uganda         Busia         0            0             <NA>
[04.3_RF_between_countries.R] [1] "--------------------Zambia---------------------------"
[04.3_RF_between_countries.R] [1] "Zambia_Reg3"
[04.3_RF_between_countries.R] [1] "Zambia_Reg4"
[04.3_RF_between_countries.R] [1] "Zambia_Reg1"
[04.3_RF_between_countries.R] [1] "Zambia_Reg2"
[04.3_RF_between_countries.R]   country      gadm_1 rf_cv_rsq rf_cv_rsq_sd gadm_test_rf_rsq
[04.3_RF_between_countries.R] 1  Zambia Zambia_Reg3      0.03            0             0.94
[04.3_RF_between_countries.R] 2  Zambia Zambia_Reg4      0.04            0             0.01
[04.3_RF_between_countries.R] 3  Zambia Zambia_Reg1      0.06         0.01             0.03
[04.3_RF_between_countries.R] 4  Zambia Zambia_Reg2         0            0             0.14
[04.3_RF_between_countries.R] There were 14 warnings (use warnings() to see them)
[04.3_RF_between_countries.R] Time difference of 1.09745 mins
[04.3_RF_between_countries.R] `summarise()` has regrouped the output.
[04.3_RF_between_countries.R] ℹ Summaries were computed grouped by country and type.
[04.3_RF_between_countries.R] ℹ Output is grouped by country.
[04.3_RF_between_countries.R] ℹ Use `summarise(.groups = "drop_last")` to silence this message.
[04.3_RF_between_countries.R] ℹ Use `summarise(.by = c(country, type))` for per-operation grouping
[04.3_RF_between_countries.R]   (`?dplyr::dplyr_by`) instead.
[04.3_RF_between_countries.R] Saving 9.84 x 5.91 in image
[04.3_RF_between_countries.R] null device 
[04.3_RF_between_countries.R]           1 
[04.3_RF_between_countries.R] Warning message:
[04.3_RF_between_countries.R] Removed 1 row containing missing values or values outside the scale range
[04.3_RF_between_countries.R] (`geom_bar()`). 
  ✓ PASS  04.3_RF_between_countries.R                    ( 70.2s)  
  ✓ PASS  04.5_cross_country_graphs.R                    (  0.2s)  
----------------------------------------------------------------------
PHASE 5: RF Optimisation (05.x)
----------------------------------------------------------------------
[05.1_RF_optimization.R] [1] "new_diff is  0.576017273993892"
[05.1_RF_optimization.R] [1] "--------- j = 6 --------"
[05.1_RF_optimization.R] [1] "cor (a, b) =0.426837145431879"
[05.1_RF_optimization.R] [1] "cor (a, c) =0.202669725694547"
[05.1_RF_optimization.R] [1] "cor (b, c) =0.725772266288621"
[05.1_RF_optimization.R] [1] "new_diff is  0.523102540594074"
[05.1_RF_optimization.R] [1] "--------- j = 7 --------"
[05.1_RF_optimization.R] [1] "cor (a, b) =0.426837145431879"
[05.1_RF_optimization.R] [1] "cor (a, c) =0.602492113333214"
[05.1_RF_optimization.R] [1] "cor (b, c) =0.620003666494294"
[05.1_RF_optimization.R] [1] "new_diff is  0.0175115531610801"
[05.1_RF_optimization.R] [1] "--------- j = 8 --------"
[05.1_RF_optimization.R] [1] "cor (a, b) =0.426837145431879"
[05.1_RF_optimization.R] [1] "cor (a, c) =0.322817250072163"
[05.1_RF_optimization.R] [1] "cor (b, c) =0.665482138875679"
[05.1_RF_optimization.R] [1] "new_diff is  0.342664888803516"
[05.1_RF_optimization.R] [1] "--------- j = 9 --------"
[05.1_RF_optimization.R] [1] "cor (a, b) =0.426837145431879"
[05.1_RF_optimization.R] [1] "cor (a, c) =0.0109939096582909"
[05.1_RF_optimization.R] [1] "cor (b, c) =0.739329491901337"
[05.1_RF_optimization.R] [1] "new_diff is  0.728335582243046"
[05.1_RF_optimization.R] [1] "--------- j = 10 --------"
[05.1_RF_optimization.R] [1] "cor (a, b) =0.426837145431879"
[05.1_RF_optimization.R] [1] "cor (a, c) =0.349905772229744"
[05.1_RF_optimization.R] [1] "cor (b, c) =0.682250205545544"
[05.1_RF_optimization.R] [1] "new_diff is  0.3323444333158"
[05.1_RF_optimization.R]          i          j       diff 
[05.1_RF_optimization.R] 18.0000000  9.0000000  0.4939707 
[05.1_RF_optimization.R] [1] "---------- case1 -------------"
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
[05.1_RF_optimization.R] [1] "---------- case2 -------------"
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
[05.1_RF_optimization.R] [1] "---------- case3 -------------"
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
  ✓ PASS  05.1_RF_optimization.R                         (  3.7s)  
[05.3_RF_robustness.R] No RFoptim files - skipping (needs 05.1 outputs)
  ✓ PASS  05.3_RF_robustness.R                           (  0.2s)  
----------------------------------------------------------------------
PHASE 6: Quantile RF & Prediction Maps (06.x)
----------------------------------------------------------------------
[06.1_quantile_RF.R] Loading required package: tidyverse
[06.1_quantile_RF.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[06.1_quantile_RF.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[06.1_quantile_RF.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[06.1_quantile_RF.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[06.1_quantile_RF.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[06.1_quantile_RF.R] ✔ purrr     1.2.1     
[06.1_quantile_RF.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[06.1_quantile_RF.R] ✖ dplyr::filter() masks stats::filter()
[06.1_quantile_RF.R] ✖ dplyr::lag()    masks stats::lag()
[06.1_quantile_RF.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[06.1_quantile_RF.R] `summarise()` has regrouped the output.
[06.1_quantile_RF.R] ℹ Summaries were computed grouped by hyper_parameter, val, and splitrule.
[06.1_quantile_RF.R] ℹ Output is grouped by hyper_parameter and val.
[06.1_quantile_RF.R] ℹ Use `summarise(.groups = "drop_last")` to silence this message.
[06.1_quantile_RF.R] ℹ Use `summarise(.by = c(hyper_parameter, val, splitrule))` for per-operation
[06.1_quantile_RF.R]   grouping (`?dplyr::dplyr_by`) instead.
[06.1_quantile_RF.R] `geom_line()`: Each group consists of only one observation.
[06.1_quantile_RF.R] ℹ Do you need to adjust the group aesthetic?
[06.1_quantile_RF.R] `geom_line()`: Each group consists of only one observation.
[06.1_quantile_RF.R] ℹ Do you need to adjust the group aesthetic?
[06.1_quantile_RF.R] Saving 7.5 x 5 in image
[06.1_quantile_RF.R] `geom_line()`: Each group consists of only one observation.
[06.1_quantile_RF.R] ℹ Do you need to adjust the group aesthetic?
[06.1_quantile_RF.R] pdf 
[06.1_quantile_RF.R]   2 
  ✓ PASS  06.1_quantile_RF.R                             (  3.2s)  
[06.3_prediction_maps.R] Loading required package: tidyverse
[06.3_prediction_maps.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[06.3_prediction_maps.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[06.3_prediction_maps.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[06.3_prediction_maps.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[06.3_prediction_maps.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[06.3_prediction_maps.R] ✔ purrr     1.2.1     
[06.3_prediction_maps.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[06.3_prediction_maps.R] ✖ dplyr::filter() masks stats::filter()
[06.3_prediction_maps.R] ✖ dplyr::lag()    masks stats::lag()
[06.3_prediction_maps.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[06.3_prediction_maps.R] OOB R2 (linear): 0.82
[06.3_prediction_maps.R] Loaded 100-quantile raster (100 bands)
[06.3_prediction_maps.R] Saved: africa_pred_obs.png
[06.3_prediction_maps.R] Saved: africa_log_pred_obs.png
[06.3_prediction_maps.R] Saved: africa_sq_pred_obs.png
[06.3_prediction_maps.R] Warning messages:
[06.3_prediction_maps.R] 1: Removed 1078 rows containing non-finite outside the scale range
[06.3_prediction_maps.R] (`stat_density2d_filled()`). 
[06.3_prediction_maps.R] 2: Removed 1078 rows containing non-finite outside the scale range
[06.3_prediction_maps.R] (`stat_density2d_filled()`). 
[06.3_prediction_maps.R] 3: Removed 1078 rows containing non-finite outside the scale range
[06.3_prediction_maps.R] (`stat_density2d_filled()`). 
[06.3_prediction_maps.R] 06.3_prediction_maps.R complete.
  ✓ PASS  06.3_prediction_maps.R                         (  5.4s)  
[06.4_cropland_sensitivity.R] min value   : 0.2342716 
[06.4_cropland_sensitivity.R] max value   : 4.2276978 
[06.4_cropland_sensitivity.R]     rf_mean      
[06.4_cropland_sensitivity.R]  Min.   :0.2343  
[06.4_cropland_sensitivity.R]  1st Qu.:1.7100  
[06.4_cropland_sensitivity.R]  Median :2.2103  
[06.4_cropland_sensitivity.R]  Mean   :2.1828  
[06.4_cropland_sensitivity.R]  3rd Qu.:2.6240  
[06.4_cropland_sensitivity.R]  Max.   :4.2277  
[06.4_cropland_sensitivity.R] null device 
[06.4_cropland_sensitivity.R]           1 
[06.4_cropland_sensitivity.R] null device 
[06.4_cropland_sensitivity.R]           1 
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] Removed 3452 rows containing non-finite outside the scale range
[06.4_cropland_sensitivity.R] (`stat_density2d_filled()`). 
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] Removed 3452 rows containing non-finite outside the scale range
[06.4_cropland_sensitivity.R] (`stat_density2d_filled()`). 
[06.4_cropland_sensitivity.R] Saving 7.5 x 5 in image
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] Removed 3452 rows containing non-finite outside the scale range
[06.4_cropland_sensitivity.R] (`stat_density2d_filled()`). 
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
[06.4_cropland_sensitivity.R] Saving 7.5 x 5 in image
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] In e1@pntr$arith_rast(e2@pntr, oper, FALSE, opt) :
[06.4_cropland_sensitivity.R]   GDAL Message 1: /tmp/RtmpBRffjs/spat_6c897b861f18_27785_Py3ptIw2UFUXKtt.tif: Metadata exceeding 32000 bytes cannot be written into GeoTIFF. Transferred to PAM instead.
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] In e1@pntr$arith_rast(e2@pntr, oper, FALSE, opt) :
[06.4_cropland_sensitivity.R]   GDAL Message 1: /tmp/RtmpBRffjs/spat_6c892cec423f_27785_8UwxxeZk3QEYL3o.tif: Metadata exceeding 32000 bytes cannot be written into GeoTIFF. Transferred to PAM instead.
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
  ✓ PASS  06.4_cropland_sensitivity.R                    ( 14.5s)  
----------------------------------------------------------------------
PHASE 7: Predictions & Validation (07.x – 10.x)
----------------------------------------------------------------------
[07.2_QRF_distribution_eval.R] 13 GEOSURVEY 2015     3 Mozambique                 116.  
[07.2_QRF_distribution_eval.R] 14 GEOSURVEY 2015     4 Senegal                     22.8 
[07.2_QRF_distribution_eval.R] 15 GEOSURVEY 2015     5 Lesotho                      5.55
[07.2_QRF_distribution_eval.R] 16 GEOSURVEY 2015     6 Sierra Leone                15.5 
[07.2_QRF_distribution_eval.R] 17 GEOSURVEY 2015     7 Eritrea                     11.7 
[07.2_QRF_distribution_eval.R] 18 GEOSURVEY 2015     8 Togo                         9.93
[07.2_QRF_distribution_eval.R] 19 GEOSURVEY 2015     9 Madagascar                  94.6 
[07.2_QRF_distribution_eval.R] 20 GEOSURVEY 2015    10 Burundi                      6.81
[07.2_QRF_distribution_eval.R] # A tibble: 20 × 4
[07.2_QRF_distribution_eval.R]    source     rank NAME_0                   cropland
[07.2_QRF_distribution_eval.R]    <chr>     <dbl> <fct>                       <dbl>
[07.2_QRF_distribution_eval.R]  1 SPAM 2017     1 Central African Republic   118.  
[07.2_QRF_distribution_eval.R]  2 SPAM 2017     2 Mozambique                 126.  
[07.2_QRF_distribution_eval.R]  3 SPAM 2017     3 Nigeria                    181.  
[07.2_QRF_distribution_eval.R]  4 SPAM 2017     4 Sierra Leone                14.9 
[07.2_QRF_distribution_eval.R]  5 SPAM 2017     5 Senegal                     29.1 
[07.2_QRF_distribution_eval.R]  6 SPAM 2017     6 Eritrea                      8.39
[07.2_QRF_distribution_eval.R]  7 SPAM 2017     7 Lesotho                      5.37
[07.2_QRF_distribution_eval.R]  8 SPAM 2017     8 Togo                        11.8 
[07.2_QRF_distribution_eval.R]  9 SPAM 2017     9 Madagascar                 102.  
[07.2_QRF_distribution_eval.R] 10 SPAM 2017    10 Rwanda                       4.70
[07.2_QRF_distribution_eval.R] 11 SPAM 2020     1 Central African Republic   123.  
[07.2_QRF_distribution_eval.R] 12 SPAM 2020     2 Nigeria                    183.  
[07.2_QRF_distribution_eval.R] 13 SPAM 2020     3 Mozambique                 127.  
[07.2_QRF_distribution_eval.R] 14 SPAM 2020     4 Eritrea                     10.2 
[07.2_QRF_distribution_eval.R] 15 SPAM 2020     5 Sierra Leone                16.0 
[07.2_QRF_distribution_eval.R] 16 SPAM 2020     6 Lesotho                      5.38
[07.2_QRF_distribution_eval.R] 17 SPAM 2020     7 Senegal                     21.7 
[07.2_QRF_distribution_eval.R] 18 SPAM 2020     8 Madagascar                  96.8 
[07.2_QRF_distribution_eval.R] 19 SPAM 2020     9 Togo                        10.1 
[07.2_QRF_distribution_eval.R] 20 SPAM 2020    10 Burundi                      6.19
[07.2_QRF_distribution_eval.R] Saving 7.87 x 5.91 in image
[07.2_QRF_distribution_eval.R] pdf 
[07.2_QRF_distribution_eval.R]   2 
[07.2_QRF_distribution_eval.R] Saving 7.87 x 5.91 in image
[07.2_QRF_distribution_eval.R] pdf 
[07.2_QRF_distribution_eval.R]   2 
[07.2_QRF_distribution_eval.R] Saving 7.87 x 5.91 in image
[07.2_QRF_distribution_eval.R] pdf 
[07.2_QRF_distribution_eval.R]   2 
  ✓ PASS  07.2_QRF_distribution_eval.R                   ( 17.6s)  
[08.2_generate_virtual_farms.R] In matrix(as.numeric(xyz), ncol = ncol(xyz), nrow = nrow(xyz)) :
[08.2_generate_virtual_farms.R]   NAs introduced by coercion
[08.2_generate_virtual_farms.R] Saving 5 x 5 in image
[08.2_generate_virtual_farms.R] Warning messages:
[08.2_generate_virtual_farms.R] 1: In scale_y_continuous(expand = c(0.1, 0.1), limits = c(0.1, 24),  :
[08.2_generate_virtual_farms.R]   log-10 transformation introduced infinite values.
[08.2_generate_virtual_farms.R] 2: In scale_y_continuous(expand = c(0.1, 0.1), limits = c(0.1, 24),  :
[08.2_generate_virtual_farms.R]   log-10 transformation introduced infinite values.
[08.2_generate_virtual_farms.R] 3: Removed 21 rows containing missing values or values outside the scale range
[08.2_generate_virtual_farms.R] (`geom_point()`). 
[08.2_generate_virtual_farms.R] 4: Removed 21 rows containing missing values or values outside the scale range
[08.2_generate_virtual_farms.R] (`geom_text()`). 
[08.2_generate_virtual_farms.R] pdf 
[08.2_generate_virtual_farms.R]   2 
[08.2_generate_virtual_farms.R] Saving 5 x 5 in image
[08.2_generate_virtual_farms.R] Warning messages:
[08.2_generate_virtual_farms.R] 1: In scale_y_continuous(expand = c(0.1, 0.1), limits = c(0.1, 24),  :
[08.2_generate_virtual_farms.R]   log-10 transformation introduced infinite values.
[08.2_generate_virtual_farms.R] 2: In scale_y_continuous(expand = c(0.1, 0.1), limits = c(0.1, 24),  :
[08.2_generate_virtual_farms.R]   log-10 transformation introduced infinite values.
[08.2_generate_virtual_farms.R] 3: Removed 21 rows containing missing values or values outside the scale range
[08.2_generate_virtual_farms.R] (`geom_point()`). 
[08.2_generate_virtual_farms.R] 4: Removed 21 rows containing missing values or values outside the scale range
[08.2_generate_virtual_farms.R] (`geom_text()`). 
[08.2_generate_virtual_farms.R] pdf 
[08.2_generate_virtual_farms.R]   2 
[08.2_generate_virtual_farms.R] Saving 5 x 5 in image
[08.2_generate_virtual_farms.R] Warning messages:
[08.2_generate_virtual_farms.R] 1: In scale_y_continuous(expand = c(0.1, 0.1), limits = c(0.1, 24),  :
[08.2_generate_virtual_farms.R]   log-10 transformation introduced infinite values.
[08.2_generate_virtual_farms.R] 2: In scale_y_continuous(expand = c(0.1, 0.1), limits = c(0.1, 24),  :
[08.2_generate_virtual_farms.R]   log-10 transformation introduced infinite values.
[08.2_generate_virtual_farms.R] 3: Removed 21 rows containing missing values or values outside the scale range
[08.2_generate_virtual_farms.R] (`geom_point()`). 
[08.2_generate_virtual_farms.R] 4: Removed 21 rows containing missing values or values outside the scale range
[08.2_generate_virtual_farms.R] (`geom_text()`). 
[08.2_generate_virtual_farms.R] pdf 
[08.2_generate_virtual_farms.R]   2 
[08.2_generate_virtual_farms.R] Joining with `by = join_by(country)`
[08.2_generate_virtual_farms.R] [1] 0.8718922
  ✓ PASS  08.2_generate_virtual_farms.R                  ( 16.0s)  
[08.3_farm_size_classes.R] The first warning was:
[08.3_farm_size_classes.R] ℹ In argument: `ks_D = mapply(...)`.
[08.3_farm_size_classes.R] Caused by warning in `ks.test.default()`:
[08.3_farm_size_classes.R] ! p-value will be approximate in the presence of ties
[08.3_farm_size_classes.R] ℹ Run `dplyr::last_dplyr_warnings()` to see the 7 remaining warnings. 
[08.3_farm_size_classes.R] # A tibble: 16 × 2
[08.3_farm_size_classes.R]    country       ks_p005
[08.3_farm_size_classes.R]    <chr>           <dbl>
[08.3_farm_size_classes.R]  1 Benin            66.7
[08.3_farm_size_classes.R]  2 Burkina          83.3
[08.3_farm_size_classes.R]  3 Cote_d_Ivoire    77.8
[08.3_farm_size_classes.R]  4 Ethiopia         75  
[08.3_farm_size_classes.R]  5 Ghana            55.6
[08.3_farm_size_classes.R]  6 Guinea_Bissau   100  
[08.3_farm_size_classes.R]  7 Malawi           66.7
[08.3_farm_size_classes.R]  8 Mali            100  
[08.3_farm_size_classes.R]  9 Niger            66.7
[08.3_farm_size_classes.R] 10 Nigeria          45.5
[08.3_farm_size_classes.R] 11 Rwanda           57.1
[08.3_farm_size_classes.R] 12 Senegal         100  
[08.3_farm_size_classes.R] 13 Tanzania         62.5
[08.3_farm_size_classes.R] 14 Togo             55.6
[08.3_farm_size_classes.R] 15 Uganda           88.9
[08.3_farm_size_classes.R] 16 Zambia           50  
[08.3_farm_size_classes.R] Joining with `by = join_by(x, y)`
[08.3_farm_size_classes.R] Warning messages:
[08.3_farm_size_classes.R] 1: Unknown or uninitialised column: `logn_mean`. 
[08.3_farm_size_classes.R] 2: Unknown or uninitialised column: `logn_sd`. 
[08.3_farm_size_classes.R] Time difference of 0.06458163 secs
[08.3_farm_size_classes.R] Error in if ((e[1] >= e[2]) || e[3] >= e[4]) { : 
[08.3_farm_size_classes.R]   missing value where TRUE/FALSE needed
[08.3_farm_size_classes.R] Calls: <Anonymous> ... .local -> .rastFromXYZ -> rast -> rast -> .local -> new_rast
[08.3_farm_size_classes.R] In addition: Warning messages:
[08.3_farm_size_classes.R] 1: In min(dx) : no non-missing arguments to min; returning Inf
[08.3_farm_size_classes.R] 2: In min(dy) : no non-missing arguments to min; returning Inf
[08.3_farm_size_classes.R] 3: In min(x) : no non-missing arguments to min; returning Inf
[08.3_farm_size_classes.R] 4: In max(x) : no non-missing arguments to max; returning -Inf
[08.3_farm_size_classes.R] 5: In min(y) : no non-missing arguments to min; returning Inf
[08.3_farm_size_classes.R] 6: In max(y) : no non-missing arguments to max; returning -Inf
[08.3_farm_size_classes.R] Execution halted
  ✗ FAIL  08.3_farm_size_classes.R                       (  4.5s)  Exit code: 1
[09.1_AEZ_characterization.R] Loading required package: tidyverse
[09.1_AEZ_characterization.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[09.1_AEZ_characterization.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[09.1_AEZ_characterization.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[09.1_AEZ_characterization.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[09.1_AEZ_characterization.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[09.1_AEZ_characterization.R] ✔ purrr     1.2.1     
[09.1_AEZ_characterization.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[09.1_AEZ_characterization.R] ✖ dplyr::filter() masks stats::filter()
[09.1_AEZ_characterization.R] ✖ dplyr::lag()    masks stats::lag()
[09.1_AEZ_characterization.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[09.1_AEZ_characterization.R] Joining with `by = join_by(NAME_0, farm_class)`
[09.1_AEZ_characterization.R] Joining with `by = join_by(NAME_0, farm_class)`
[09.1_AEZ_characterization.R] Joining with `by = join_by(NAME_0, farm_class)`
[09.1_AEZ_characterization.R] Joining with `by = join_by(NAME_0, farm_class)`
[09.1_AEZ_characterization.R] Saving 7.5 x 5 in image
[09.1_AEZ_characterization.R] pdf 
[09.1_AEZ_characterization.R]   2 
[09.1_AEZ_characterization.R] Saving 7.5 x 5 in image
[09.1_AEZ_characterization.R] pdf 
[09.1_AEZ_characterization.R]   2 
[09.1_AEZ_characterization.R] Saving 7.5 x 5 in image
[09.1_AEZ_characterization.R] pdf 
[09.1_AEZ_characterization.R]   2 
[09.1_AEZ_characterization.R] Saving 7.5 x 5 in image
[09.1_AEZ_characterization.R] pdf 
[09.1_AEZ_characterization.R]   2 
  ✓ PASS  09.1_AEZ_characterization.R                    (  9.2s)  
[10.1_prepare_validation_data.R] Removed 165 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] pdf 
[10.1_prepare_validation_data.R]   2 
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] Removed 96 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] Removed 96 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] Saving 7.5 x 5 in image
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] Removed 96 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] pdf 
[10.1_prepare_validation_data.R]   2 
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] Removed 165 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] Removed 165 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] Saving 7.5 x 5 in image
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] Removed 165 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] pdf 
[10.1_prepare_validation_data.R]   2 
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] Removed 96 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] Removed 96 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] Saving 7.5 x 5 in image
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] Removed 96 rows containing missing values or values outside the scale range
[10.1_prepare_validation_data.R] (`geom_line()`). 
[10.1_prepare_validation_data.R] pdf 
[10.1_prepare_validation_data.R]   2 
  ✓ PASS  10.1_prepare_validation_data.R                 ( 17.4s)  
[10.2_external_validation.R] $Sudan
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $Senegal
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $`Sierra Leone`
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $Somalia
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $`South Sudan`
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $Eswatini
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $Chad
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $Togo
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $Tanzania
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $Uganda
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $`South Africa`
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $Zambia
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] $Zimbabwe
[10.2_external_validation.R] NULL
[10.2_external_validation.R] 
[10.2_external_validation.R] There were 50 or more warnings (use warnings() to see the first 50)
  ✓ PASS  10.2_external_validation.R                     (  6.3s)  
----------------------------------------------------------------------
PHASE 8: Figures & Supplementary (F/S/T)
----------------------------------------------------------------------
[F01_main_figure1.R] Loading required package: tidyverse
[F01_main_figure1.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[F01_main_figure1.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[F01_main_figure1.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[F01_main_figure1.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[F01_main_figure1.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[F01_main_figure1.R] ✔ purrr     1.2.1     
[F01_main_figure1.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[F01_main_figure1.R] ✖ dplyr::filter() masks stats::filter()
[F01_main_figure1.R] ✖ dplyr::lag()    masks stats::lag()
[F01_main_figure1.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[F01_main_figure1.R] --- Botswana ---
[F01_main_figure1.R] CI: Botswana validation zip missing — using stub
[F01_main_figure1.R] --- Kenya ---
[F01_main_figure1.R] CI: Kenya validation zip missing — using stub
[F01_main_figure1.R] --- Mozambique ---
[F01_main_figure1.R] CI: Mozambique validation zip missing — using stub
[F01_main_figure1.R] --- Zimbabwe ---
[F01_main_figure1.R] CI: Zimbabwe validation zip missing — using stub
[F01_main_figure1.R] CI: fuzzyjoin unavailable — using exact inner_join
[F01_main_figure1.R] CI: F01 filter skipped: 
[F01_main_figure1.R] `summarise()` has regrouped the output.
[F01_main_figure1.R] ℹ Summaries were computed grouped by NAME_0 and NAME_1.
[F01_main_figure1.R] ℹ Output is grouped by NAME_0.
[F01_main_figure1.R] ℹ Use `summarise(.groups = "drop_last")` to silence this message.
[F01_main_figure1.R] ℹ Use `summarise(.by = c(NAME_0, NAME_1))` for per-operation grouping
[F01_main_figure1.R]   (`?dplyr::dplyr_by`) instead.
[F01_main_figure1.R] CI: compare_pred_measured_gadm1 empty — skipping faceted P00
[F01_main_figure1.R] Saving 7.5 x 5 in image
[F01_main_figure1.R] pdf 
[F01_main_figure1.R]   2 
  ✓ PASS  F01_main_figure1.R                             (  4.9s)  
[F02_main_figure2.R] Loading required package: tidyverse
[F02_main_figure2.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[F02_main_figure2.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[F02_main_figure2.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[F02_main_figure2.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[F02_main_figure2.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[F02_main_figure2.R] ✔ purrr     1.2.1     
[F02_main_figure2.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[F02_main_figure2.R] ✖ dplyr::filter() masks stats::filter()
[F02_main_figure2.R] ✖ dplyr::lag()    masks stats::lag()
[F02_main_figure2.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[F02_main_figure2.R] Loading required package: patchwork
[F02_main_figure2.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[F02_main_figure2.R] Ncells 1791132 95.7    2821531 150.7  2821531 150.7
[F02_main_figure2.R] Vcells 2521400 19.3    8388608  64.0  4333385  33.1
[F02_main_figure2.R] New names:
[F02_main_figure2.R] • `` -> `...1`
[F02_main_figure2.R] • `` -> `...2`
[F02_main_figure2.R] null device 
[F02_main_figure2.R]           1 
  ✓ PASS  F02_main_figure2.R                             (  4.7s)  
[F03_main_figure3.R] Loading required package: tidyverse
[F03_main_figure3.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[F03_main_figure3.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[F03_main_figure3.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[F03_main_figure3.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[F03_main_figure3.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[F03_main_figure3.R] ✔ purrr     1.2.1     
[F03_main_figure3.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[F03_main_figure3.R] ✖ dplyr::filter() masks stats::filter()
[F03_main_figure3.R] ✖ dplyr::lag()    masks stats::lag()
[F03_main_figure3.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[F03_main_figure3.R] Loading required package: patchwork
[F03_main_figure3.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[F03_main_figure3.R] Ncells 1791135 95.7    2821528 150.7  2821528 150.7
[F03_main_figure3.R] Vcells 2521401 19.3    8388608  64.0  4333385  33.1
[F03_main_figure3.R] null device 
[F03_main_figure3.R]           1 
[F03_main_figure3.R] Figure saved as PNG: ../output/main_fig/Fig.02.png
  ✓ PASS  F03_main_figure3.R                             (  7.6s)  
[S01_drivers.R] Loading required package: tidyverse
[S01_drivers.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[S01_drivers.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[S01_drivers.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[S01_drivers.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[S01_drivers.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S01_drivers.R] ✔ purrr     1.2.1     
[S01_drivers.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S01_drivers.R] ✖ dplyr::filter() masks stats::filter()
[S01_drivers.R] ✖ dplyr::lag()    masks stats::lag()
[S01_drivers.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S01_drivers.R] null device 
[S01_drivers.R]           1 
  ✓ PASS  S01_drivers.R                                  (  1.5s)  
[S02_cropland_uncertainty.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[S02_cropland_uncertainty.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[S02_cropland_uncertainty.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[S02_cropland_uncertainty.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[S02_cropland_uncertainty.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S02_cropland_uncertainty.R] ✔ purrr     1.2.1     
[S02_cropland_uncertainty.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S02_cropland_uncertainty.R] ✖ dplyr::filter() masks stats::filter()
[S02_cropland_uncertainty.R] ✖ dplyr::lag()    masks stats::lag()
[S02_cropland_uncertainty.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S02_cropland_uncertainty.R] Loading required package: patchwork
[S02_cropland_uncertainty.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[S02_cropland_uncertainty.R] Ncells 1791147 95.7    2821151 150.7  2821151 150.7
[S02_cropland_uncertainty.R] Vcells 2521314 19.3    8388608  64.0  4333324  33.1
[S02_cropland_uncertainty.R] ℹ tmap modes "plot" - "view"
[S02_cropland_uncertainty.R] ℹ toggle with `tmap::ttm()`
[S02_cropland_uncertainty.R] This message is displayed once per session.
[S02_cropland_uncertainty.R] Warning message:
[S02_cropland_uncertainty.R] Calling `case_when()` with size 1 LHS inputs and size >1 RHS inputs was
[S02_cropland_uncertainty.R] deprecated in dplyr 1.2.0.
[S02_cropland_uncertainty.R] ℹ This `case_when()` statement can result in subtle silent bugs and is very inefficient.
[S02_cropland_uncertainty.R] 
[S02_cropland_uncertainty.R]   Please use a series of if statements instead:
[S02_cropland_uncertainty.R] 
[S02_cropland_uncertainty.R]   ```
[S02_cropland_uncertainty.R]   # Previously
[S02_cropland_uncertainty.R]   case_when(scalar_lhs1 ~ rhs1, scalar_lhs2 ~ rhs2, .default = default)
[S02_cropland_uncertainty.R] 
[S02_cropland_uncertainty.R]   # Now
[S02_cropland_uncertainty.R]   if (scalar_lhs1) {
[S02_cropland_uncertainty.R]     rhs1
[S02_cropland_uncertainty.R]   } else if (scalar_lhs2) {
[S02_cropland_uncertainty.R]     rhs2
[S02_cropland_uncertainty.R]   } else {
[S02_cropland_uncertainty.R]     default
[S02_cropland_uncertainty.R]   }
[S02_cropland_uncertainty.R]   ``` 
[S02_cropland_uncertainty.R] Map saved to /home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/output/suppl_fig/Suppl.Fig01.png
[S02_cropland_uncertainty.R] Resolution: 1500 by 1050 pixels
[S02_cropland_uncertainty.R] Size: 10 by 7 inches (150 dpi)
  ✓ PASS  S02_cropland_uncertainty.R                     ( 10.8s)  
[S03_aggregate_vs_disaggregate.R] Loading required package: tidyverse
[S03_aggregate_vs_disaggregate.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[S03_aggregate_vs_disaggregate.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[S03_aggregate_vs_disaggregate.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[S03_aggregate_vs_disaggregate.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[S03_aggregate_vs_disaggregate.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S03_aggregate_vs_disaggregate.R] ✔ purrr     1.2.1     
[S03_aggregate_vs_disaggregate.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S03_aggregate_vs_disaggregate.R] ✖ dplyr::filter() masks stats::filter()
[S03_aggregate_vs_disaggregate.R] ✖ dplyr::lag()    masks stats::lag()
[S03_aggregate_vs_disaggregate.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S03_aggregate_vs_disaggregate.R] Loading required package: patchwork
[S03_aggregate_vs_disaggregate.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[S03_aggregate_vs_disaggregate.R] Ncells 1791790 95.7    2821148 150.7  2821148 150.7
[S03_aggregate_vs_disaggregate.R] Vcells 2522401 19.3    8388608  64.0  4333325  33.1
[S03_aggregate_vs_disaggregate.R] Joining with `by = join_by(source)`
  ✓ PASS  S03_aggregate_vs_disaggregate.R                ( 33.3s)  
[S04_RF_hyperparameters.R] Loading required package: tidyverse
[S04_RF_hyperparameters.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[S04_RF_hyperparameters.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[S04_RF_hyperparameters.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[S04_RF_hyperparameters.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[S04_RF_hyperparameters.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S04_RF_hyperparameters.R] ✔ purrr     1.2.1     
[S04_RF_hyperparameters.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S04_RF_hyperparameters.R] ✖ dplyr::filter() masks stats::filter()
[S04_RF_hyperparameters.R] ✖ dplyr::lag()    masks stats::lag()
[S04_RF_hyperparameters.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S04_RF_hyperparameters.R] Loading required package: patchwork
[S04_RF_hyperparameters.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[S04_RF_hyperparameters.R] Ncells 1791790 95.7    2821531 150.7  2821531 150.7
[S04_RF_hyperparameters.R] Vcells 2522401 19.3    8388608  64.0  4333385  33.1
[S04_RF_hyperparameters.R] Joining with `by = join_by(country, gadm_0)`
[S04_RF_hyperparameters.R] Warning message:
[S04_RF_hyperparameters.R] In text.default(6, 7.5, "Model performance by \naggregation level",  :
[S04_RF_hyperparameters.R]   "line" is not a graphical parameter
[S04_RF_hyperparameters.R] null device 
[S04_RF_hyperparameters.R]           1 
  ✓ PASS  S04_RF_hyperparameters.R                       (  7.8s)  
[S05_RF_unseen_performance.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[S05_RF_unseen_performance.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S05_RF_unseen_performance.R] ✔ purrr     1.2.1     
[S05_RF_unseen_performance.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S05_RF_unseen_performance.R] ✖ dplyr::filter() masks stats::filter()
[S05_RF_unseen_performance.R] ✖ dplyr::lag()    masks stats::lag()
[S05_RF_unseen_performance.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S05_RF_unseen_performance.R] Loading required package: patchwork
[S05_RF_unseen_performance.R] Warning message:
[S05_RF_unseen_performance.R] There was 1 warning in `mutate()`.
[S05_RF_unseen_performance.R] ℹ In argument: `mbucket = as.integer(gsub("*.*mbucket\\-", "", gsub("\\.Rds",
[S05_RF_unseen_performance.R]   "", filename)))`.
[S05_RF_unseen_performance.R] Caused by warning:
[S05_RF_unseen_performance.R] ! NAs introduced by coercion 
[S05_RF_unseen_performance.R] Warning messages:
[S05_RF_unseen_performance.R] 1: Removed 12 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_ribbon()`). 
[S05_RF_unseen_performance.R] 2: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_line()`). 
[S05_RF_unseen_performance.R] 3: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_point()`). 
[S05_RF_unseen_performance.R] 4: Removed 12 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_ribbon()`). 
[S05_RF_unseen_performance.R] 5: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_line()`). 
[S05_RF_unseen_performance.R] 6: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_point()`). 
[S05_RF_unseen_performance.R] Warning messages:
[S05_RF_unseen_performance.R] 1: Removed 12 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_ribbon()`). 
[S05_RF_unseen_performance.R] 2: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_line()`). 
[S05_RF_unseen_performance.R] 3: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_point()`). 
[S05_RF_unseen_performance.R] 4: Removed 12 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_ribbon()`). 
[S05_RF_unseen_performance.R] 5: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_line()`). 
[S05_RF_unseen_performance.R] 6: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_point()`). 
  ✓ PASS  S05_RF_unseen_performance.R                    (  5.2s)  
[S06_size_class_comparison.R] Loading required package: tidyverse
[S06_size_class_comparison.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[S06_size_class_comparison.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[S06_size_class_comparison.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[S06_size_class_comparison.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[S06_size_class_comparison.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S06_size_class_comparison.R] ✔ purrr     1.2.1     
[S06_size_class_comparison.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S06_size_class_comparison.R] ✖ dplyr::filter() masks stats::filter()
[S06_size_class_comparison.R] ✖ dplyr::lag()    masks stats::lag()
[S06_size_class_comparison.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S06_size_class_comparison.R] Loading required package: patchwork
[S06_size_class_comparison.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[S06_size_class_comparison.R] Ncells 1791790 95.7    2821531 150.7  2821531 150.7
[S06_size_class_comparison.R] Vcells 2522401 19.3    8388608  64.0  4333385  33.1
[S06_size_class_comparison.R] Joining with `by = join_by(train_country, train_GID_0)`
[S06_size_class_comparison.R] Joining with `by = join_by(test_country, test_GID_0)`
  ✓ PASS  S06_size_class_comparison.R                    (  5.2s)  
[S07_distribution_parameters.R] Loading required package: tidyverse
[S07_distribution_parameters.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[S07_distribution_parameters.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[S07_distribution_parameters.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[S07_distribution_parameters.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[S07_distribution_parameters.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S07_distribution_parameters.R] ✔ purrr     1.2.1     
[S07_distribution_parameters.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S07_distribution_parameters.R] ✖ dplyr::filter() masks stats::filter()
[S07_distribution_parameters.R] ✖ dplyr::lag()    masks stats::lag()
[S07_distribution_parameters.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S07_distribution_parameters.R] Loading required package: patchwork
[S07_distribution_parameters.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[S07_distribution_parameters.R] Ncells 1791790 95.7    2821531 150.7  2821531 150.7
[S07_distribution_parameters.R] Vcells 2522401 19.3    8388608  64.0  4333385  33.1
[S07_distribution_parameters.R] Joining with `by = join_by(NAME_0)`
[S07_distribution_parameters.R] Joining with `by = join_by(NAME_0, GID_0)`
[S07_distribution_parameters.R] Warning message:
[S07_distribution_parameters.R] In geom_text(data = inner_join(div_table, distinct(select(comp_fsize_classes_nb,  :
[S07_distribution_parameters.R]   Ignoring unknown parameters: `inherits.aes`
[S07_distribution_parameters.R] Warning message:
[S07_distribution_parameters.R] `position_dodge()` requires non-overlapping x intervals. 
[S07_distribution_parameters.R] Joining with `by = join_by(NAME_0)`
[S07_distribution_parameters.R] Joining with `by = join_by(NAME_0, GID_0)`
[S07_distribution_parameters.R] Warning message:
[S07_distribution_parameters.R] In geom_text(data = inner_join(div_table, distinct(select(comp_fsize_classes_ha,  :
[S07_distribution_parameters.R]   Ignoring unknown parameters: `inherits.aes`
[S07_distribution_parameters.R] Warning message:
[S07_distribution_parameters.R] `position_dodge()` requires non-overlapping x intervals. 
[S07_distribution_parameters.R] Warning messages:
[S07_distribution_parameters.R] 1: `position_dodge()` requires non-overlapping x intervals. 
[S07_distribution_parameters.R] 2: `position_dodge()` requires non-overlapping x intervals. 
  ✓ PASS  S07_distribution_parameters.R                  (  5.4s)  
[S08_variable_importance.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[S08_variable_importance.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[S08_variable_importance.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S08_variable_importance.R] ✔ purrr     1.2.1     
[S08_variable_importance.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S08_variable_importance.R] ✖ dplyr::filter() masks stats::filter()
[S08_variable_importance.R] ✖ dplyr::lag()    masks stats::lag()
[S08_variable_importance.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S08_variable_importance.R] Loading required package: patchwork
[S08_variable_importance.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[S08_variable_importance.R] Ncells 1791150 95.7    2821151 150.7  2821151 150.7
[S08_variable_importance.R] Vcells 2521315 19.3    8388608  64.0  4333324  33.1
[S08_variable_importance.R] Warning message:
[S08_variable_importance.R] [rast] CRS do not match 
[S08_variable_importance.R] ℹ tmap modes "plot" - "view"
[S08_variable_importance.R] ℹ toggle with `tmap::ttm()`
[S08_variable_importance.R] This message is displayed once per session.
[S08_variable_importance.R] Warning message:
[S08_variable_importance.R] Calling `case_when()` with size 1 LHS inputs and size >1 RHS inputs was
[S08_variable_importance.R] deprecated in dplyr 1.2.0.
[S08_variable_importance.R] ℹ This `case_when()` statement can result in subtle silent bugs and is very inefficient.
[S08_variable_importance.R] 
[S08_variable_importance.R]   Please use a series of if statements instead:
[S08_variable_importance.R] 
[S08_variable_importance.R]   ```
[S08_variable_importance.R]   # Previously
[S08_variable_importance.R]   case_when(scalar_lhs1 ~ rhs1, scalar_lhs2 ~ rhs2, .default = default)
[S08_variable_importance.R] 
[S08_variable_importance.R]   # Now
[S08_variable_importance.R]   if (scalar_lhs1) {
[S08_variable_importance.R]     rhs1
[S08_variable_importance.R]   } else if (scalar_lhs2) {
[S08_variable_importance.R]     rhs2
[S08_variable_importance.R]   } else {
[S08_variable_importance.R]     default
[S08_variable_importance.R]   }
[S08_variable_importance.R]   ``` 
[S08_variable_importance.R] Map saved to /home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/output/suppl_fig/Suppl.Fig07.png
[S08_variable_importance.R] Resolution: 1050 by 1500 pixels
[S08_variable_importance.R] Size: 7 by 10 inches (150 dpi)
  ✓ PASS  S08_variable_importance.R                      (  8.4s)  
[T01_area_production_tables.R] Loading required package: tidyverse
[T01_area_production_tables.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[T01_area_production_tables.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[T01_area_production_tables.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[T01_area_production_tables.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[T01_area_production_tables.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[T01_area_production_tables.R] ✔ purrr     1.2.1     
[T01_area_production_tables.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[T01_area_production_tables.R] ✖ dplyr::filter() masks stats::filter()
[T01_area_production_tables.R] ✖ dplyr::lag()    masks stats::lag()
[T01_area_production_tables.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[T01_area_production_tables.R] Total observations: 4291
[T01_area_production_tables.R] Countries: 16
[T01_area_production_tables.R] 
[T01_area_production_tables.R] === T01 Survey Summary Statistics ===
[T01_area_production_tables.R] # A tibble: 17 × 10
[T01_area_production_tables.R]    country    n_waves period n_obs prct_below_0.5 prct_below_1   q10   med   avg
[T01_area_production_tables.R]    <chr>        <int> <chr>  <int>          <dbl>        <dbl> <dbl> <dbl> <dbl>
[T01_area_production_tables.R]  1 Benin            6 2010-…   313           9.58         40.3  0.51  1.22  1.69
[T01_area_production_tables.R]  2 Burkina          6 2010-…   288          11.5          35.4  0.5   1.38  1.85
[T01_area_production_tables.R]  3 Cote_d_Iv…       6 2010-…   313           9.9          31.6  0.51  1.39  1.76
[T01_area_production_tables.R]  4 Ethiopia         6 2010-…   313          11.5          37.4  0.44  1.4   1.88
[T01_area_production_tables.R]  5 Ghana            6 2010-…   313          10.5          36.7  0.49  1.33  1.74
[T01_area_production_tables.R]  6 Guinea_Bi…       6 2010-…   272          10.7          35.7  0.5   1.34  1.86
[T01_area_production_tables.R]  7 Malawi           6 2010-…   313           9.58         34.5  0.52  1.39  1.91
[T01_area_production_tables.R]  8 Mali             6 2010-…    46          10.9          26.1  0.51  1.35  2.03
[T01_area_production_tables.R]  9 Niger            6 2010-…    38          10.5          34.2  0.5   1.14  1.42
[T01_area_production_tables.R] 10 Nigeria          6 2010-…   313           8.63         35.5  0.53  1.41  2.12
[T01_area_production_tables.R] 11 Rwanda           6 2010-…   313          12.1          34.5  0.45  1.47  1.97
[T01_area_production_tables.R] 12 Senegal          6 2010-…   205           8.78         32.7  0.54  1.44  1.86
[T01_area_production_tables.R] 13 Tanzania         6 2010-…   313          12.8          39.3  0.44  1.24  1.7 
[T01_area_production_tables.R] 14 Togo             6 2010-…   312          10.3          33.3  0.49  1.35  1.72
[T01_area_production_tables.R] 15 Uganda           6 2010-…   313          12.1          39.6  0.46  1.17  1.78
[T01_area_production_tables.R] 16 Zambia           6 2010-…   313          10.9          36.4  0.43  1.25  1.75
[T01_area_production_tables.R] 17 TOTAL           96 2010-…  4291          10.7          35.9  0.49  1.32  1.83
[T01_area_production_tables.R] # ℹ 1 more variable: q90 <dbl>
[T01_area_production_tables.R] Saved: ../output/main_fig/T01_summary_descriptive_stats_survey.csv
  ✓ PASS  T01_area_production_tables.R                   (  1.2s)  
[T02_heterogeneity_drivers.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[T02_heterogeneity_drivers.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[T02_heterogeneity_drivers.R] ✔ purrr     1.2.1     
[T02_heterogeneity_drivers.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[T02_heterogeneity_drivers.R] ✖ dplyr::filter() masks stats::filter()
[T02_heterogeneity_drivers.R] ✖ dplyr::lag()    masks stats::lag()
[T02_heterogeneity_drivers.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[T02_heterogeneity_drivers.R] 
[T02_heterogeneity_drivers.R] === T02 by AEZ ===
[T02_heterogeneity_drivers.R] # A tibble: 6 × 11
[T02_heterogeneity_drivers.R]   aez       prop_prop_area_< 0.5…¹ prop_prop_area_0.5 -…² prop_prop_area_1 - 2…³
[T02_heterogeneity_drivers.R]   <chr>                      <dbl>                  <dbl>                  <dbl>
[T02_heterogeneity_drivers.R] 1 humid                        1.3                   12.5                   36.7
[T02_heterogeneity_drivers.R] 2 sub-humid                    1.3                   12.1                   38.8
[T02_heterogeneity_drivers.R] 3 semi-arid                    1.1                   11.3                   39.3
[T02_heterogeneity_drivers.R] 4 tropical…                    1.4                   13.5                   37.2
[T02_heterogeneity_drivers.R] 5 sub-trop…                    0.5                   13.9                   31.3
[T02_heterogeneity_drivers.R] 6 <NA>                         1.3                   11.8                   38.4
[T02_heterogeneity_drivers.R] # ℹ abbreviated names: ¹​`prop_prop_area_< 0.5 ha`,
[T02_heterogeneity_drivers.R] #   ²​`prop_prop_area_0.5 - 1 ha`, ³​`prop_prop_area_1 - 2 ha`
[T02_heterogeneity_drivers.R] # ℹ 7 more variables: `prop_prop_area_2 - 5 ha` <dbl>,
[T02_heterogeneity_drivers.R] #   `prop_prop_area_> 5 ha` <dbl>, `prop_prop_farms_< 0.5 ha` <dbl>,
[T02_heterogeneity_drivers.R] #   `prop_prop_farms_0.5 - 1 ha` <dbl>, `prop_prop_farms_1 - 2 ha` <dbl>,
[T02_heterogeneity_drivers.R] #   `prop_prop_farms_2 - 5 ha` <dbl>, `prop_prop_farms_> 5 ha` <dbl>
[T02_heterogeneity_drivers.R] 
[T02_heterogeneity_drivers.R] === T02 by Region ===
[T02_heterogeneity_drivers.R] # A tibble: 4 × 11
[T02_heterogeneity_drivers.R]   region   prop_prop_area_< 0.5 …¹ prop_prop_area_0.5 -…² prop_prop_area_1 - 2…³
[T02_heterogeneity_drivers.R]   <chr>                      <dbl>                  <dbl>                  <dbl>
[T02_heterogeneity_drivers.R] 1 Central                      1.3                   13.5                   29.4
[T02_heterogeneity_drivers.R] 2 Eastern                      1.2                   12.8                   37.6
[T02_heterogeneity_drivers.R] 3 Southern                    NA                     NA                    100  
[T02_heterogeneity_drivers.R] 4 Western                      1.2                   11.5                   38.3
[T02_heterogeneity_drivers.R] # ℹ abbreviated names: ¹​`prop_prop_area_< 0.5 ha`,
[T02_heterogeneity_drivers.R] #   ²​`prop_prop_area_0.5 - 1 ha`, ³​`prop_prop_area_1 - 2 ha`
[T02_heterogeneity_drivers.R] # ℹ 7 more variables: `prop_prop_area_2 - 5 ha` <dbl>,
[T02_heterogeneity_drivers.R] #   `prop_prop_area_> 5 ha` <dbl>, `prop_prop_farms_< 0.5 ha` <dbl>,
[T02_heterogeneity_drivers.R] #   `prop_prop_farms_0.5 - 1 ha` <dbl>, `prop_prop_farms_1 - 2 ha` <dbl>,
[T02_heterogeneity_drivers.R] #   `prop_prop_farms_2 - 5 ha` <dbl>, `prop_prop_farms_> 5 ha` <dbl>
[T02_heterogeneity_drivers.R] Saved T02_heterogeneity_by_aez.csv and T02_heterogeneity_by_region.csv
  ✓ PASS  T02_heterogeneity_drivers.R                    (  1.2s)  

======================================================================
TEST SUMMARY
======================================================================

  Stat   Script                                          Time(s)  Note
  ------------------------------------------------------------------------
  ✓ PASS  00_synthetic_data                                 7.6    
  ✓ PASS  00_install_packages.R                             0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  00_download_spatial_data.R                        0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  01.2_chirps_summarize.R                           0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  02.1_compile_LSMS.R                               0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  05.2_RF_optimization_summary.R                    0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  08.1_predictions_by_country.R                     0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  04.4_RF_model_evaluation.R                        0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  01.1_chirps_download.R                            1.8    
  ✓ PASS  01.3_chirps_trends.R                              4.1    
  ✓ PASS  01.4_prepare_spatial_layers.R                     3.1    
  ✓ PASS  02.2_harmonize_farm_area.R                        3.7    
  ✓ PASS  02.3_measured_vs_reported.R                       2.0    
  ✓ PASS  03.1_pooled_data.R                                1.2    
  ✓ PASS  03.2_correlation_drivers.R                       44.4    
  ✓ PASS  03.3_descriptive_stats.R                         17.8    
  ✓ PASS  04.1_comparing_ML_algorithms.R                    1.2    
  ✓ PASS  04.2_RF_within_country.R                         46.8    
  ✓ PASS  04.3_RF_between_countries.R                      70.2    
  ✓ PASS  04.5_cross_country_graphs.R                       0.2    
  ✓ PASS  05.1_RF_optimization.R                            3.7    
  ✓ PASS  05.3_RF_robustness.R                              0.2    
  ✓ PASS  06.1_quantile_RF.R                                3.2    
  ✓ PASS  06.3_prediction_maps.R                            5.4    
  ✓ PASS  06.4_cropland_sensitivity.R                      14.5    
  ✓ PASS  07.2_QRF_distribution_eval.R                     17.6    
  ✓ PASS  08.2_generate_virtual_farms.R                    16.0    
  ✗ FAIL  08.3_farm_size_classes.R                          4.5    Exit code: 1
  ✓ PASS  09.1_AEZ_characterization.R                       9.2    
  ✓ PASS  10.1_prepare_validation_data.R                   17.4    
  ✓ PASS  10.2_external_validation.R                        6.3    
  ✓ PASS  F01_main_figure1.R                                4.9    
  ✓ PASS  F02_main_figure2.R                                4.7    
  ✓ PASS  F03_main_figure3.R                                7.6    
  ✓ PASS  S01_drivers.R                                     1.5    
  ✓ PASS  S02_cropland_uncertainty.R                       10.8    
  ✓ PASS  S03_aggregate_vs_disaggregate.R                  33.3    
  ✓ PASS  S04_RF_hyperparameters.R                          7.8    
  ✓ PASS  S05_RF_unseen_performance.R                       5.2    
  ✓ PASS  S06_size_class_comparison.R                       5.2    
  ✓ PASS  S07_distribution_parameters.R                     5.4    
  ✓ PASS  S08_variable_importance.R                         8.4    
  ✓ PASS  T01_area_production_tables.R                      1.2    
  ✓ PASS  T02_heterogeneity_drivers.R                       1.2    

======================================================================
Total: 44   Passed: 43   Failed: 1   Time: 400s

Report: ../output/reports/full_pipeline_test_report.md

✅ CORE PIPELINE OK (20/21 core scripts passed = 95%)
```

## Pipeline Report
# Farm Size Prediction — Full Pipeline CI Report

**Generated:** 2026-03-30 10:23:46 UTC
**R Version:** R version 4.3.3 (2024-02-29)

## Summary

| Metric | Value |
|--------|-------|
| Total Scripts  | 44 |
| Passed         | 43 |
| Failed         | 1 |
| Total Time     | 400.1s |

## Per-Script Results

| Phase | Script | Status | Time | Note |
|-------|--------|--------|------|------|
| 00 | `00_synthetic_data` | ✅ PASS | 7.6s |  |
| 00 | `00_install_packages.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 00 | `00_download_spatial_data.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.2 | `01.2_chirps_summarize.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 02.1 | `02.1_compile_LSMS.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 05.2 | `05.2_RF_optimization_summary.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 08.1 | `08.1_predictions_by_country.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 04.4 | `04.4_RF_model_evaluation.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.1 | `01.1_chirps_download.R` | ✅ PASS | 1.8s |  |
| 01.3 | `01.3_chirps_trends.R` | ✅ PASS | 4.1s |  |
| 01.4 | `01.4_prepare_spatial_layers.R` | ✅ PASS | 3.1s |  |
| 02.2 | `02.2_harmonize_farm_area.R` | ✅ PASS | 3.7s |  |
| 02.3 | `02.3_measured_vs_reported.R` | ✅ PASS | 2s |  |
| 03.1 | `03.1_pooled_data.R` | ✅ PASS | 1.2s |  |
| 03.2 | `03.2_correlation_drivers.R` | ✅ PASS | 44.4s |  |
| 03.3 | `03.3_descriptive_stats.R` | ✅ PASS | 17.8s |  |
| 04.1 | `04.1_comparing_ML_algorithms.R` | ✅ PASS | 1.2s |  |
| 04.2 | `04.2_RF_within_country.R` | ✅ PASS | 46.8s |  |
| 04.3 | `04.3_RF_between_countries.R` | ✅ PASS | 70.2s |  |
| 04.5 | `04.5_cross_country_graphs.R` | ✅ PASS | 0.2s |  |
| 05.1 | `05.1_RF_optimization.R` | ✅ PASS | 3.7s |  |
| 05.3 | `05.3_RF_robustness.R` | ✅ PASS | 0.2s |  |
| 06.1 | `06.1_quantile_RF.R` | ✅ PASS | 3.2s |  |
| 06.3 | `06.3_prediction_maps.R` | ✅ PASS | 5.4s |  |
| 06.4 | `06.4_cropland_sensitivity.R` | ✅ PASS | 14.5s |  |
| 07.2 | `07.2_QRF_distribution_eval.R` | ✅ PASS | 17.6s |  |
| 08.2 | `08.2_generate_virtual_farms.R` | ✅ PASS | 16s |  |
| 08.3 | `08.3_farm_size_classes.R` | ❌ FAIL | 4.5s | Exit code: 1 |
| 09.1 | `09.1_AEZ_characterization.R` | ✅ PASS | 9.2s |  |
| 10.1 | `10.1_prepare_validation_data.R` | ✅ PASS | 17.4s |  |
| 10.2 | `10.2_external_validation.R` | ✅ PASS | 6.3s |  |
| F01 | `F01_main_figure1.R` | ✅ PASS | 4.9s |  |
| F02 | `F02_main_figure2.R` | ✅ PASS | 4.7s |  |
| F03 | `F03_main_figure3.R` | ✅ PASS | 7.6s |  |
| S01 | `S01_drivers.R` | ✅ PASS | 1.5s |  |
| S02 | `S02_cropland_uncertainty.R` | ✅ PASS | 10.8s |  |
| S03 | `S03_aggregate_vs_disaggregate.R` | ✅ PASS | 33.3s |  |
| S04 | `S04_RF_hyperparameters.R` | ✅ PASS | 7.8s |  |
| S05 | `S05_RF_unseen_performance.R` | ✅ PASS | 5.2s |  |
| S06 | `S06_size_class_comparison.R` | ✅ PASS | 5.2s |  |
| S07 | `S07_distribution_parameters.R` | ✅ PASS | 5.4s |  |
| S08 | `S08_variable_importance.R` | ✅ PASS | 8.4s |  |
| T01 | `T01_area_production_tables.R` | ✅ PASS | 1.2s |  |
| T02 | `T02_heterogeneity_drivers.R` | ✅ PASS | 1.2s |  |
