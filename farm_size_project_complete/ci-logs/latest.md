# CI Run Log
Run: 23143406356  Commit: 8385f8d36f685a183314b2f2b62856b970c4dc63  Time: Mon Mar 16 12:52:02 UTC 2026

## Raw Output
```

======================================================================
FARM SIZE PREDICTION - FULL SEQUENTIAL PIPELINE TEST
======================================================================
Started: 2026-03-16 12:25:01.191827

Scripts dir: /home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/scripts

----------------------------------------------------------------------
PHASE 0: Synthetic Data Generation
----------------------------------------------------------------------
[00_synthetic_data.R] === FULL Synthetic Data Generation for CI ===
[00_synthetic_data.R] 
[00_synthetic_data.R] terra 1.8.93
[00_synthetic_data.R] terra: OK  dplyr: OK
[00_synthetic_data.R] 1. Creating synthetic rasters...
[00_synthetic_data.R]    Rasters done.
[00_synthetic_data.R]    Yearly rainfall stubs done.
[00_synthetic_data.R] 2. Creating synthetic LSMS survey data...
[00_synthetic_data.R]    LSMS CSV + RDS done  (7029 farms).
[00_synthetic_data.R] 3. Extracting predictors at farm locations...
[00_synthetic_data.R]    Analysis datasets done  (4177 farms in 95th trim).
[00_synthetic_data.R] 4. Creating synthetic GADM boundaries...
[00_synthetic_data.R]    GADM boundaries done.
[00_synthetic_data.R] 5. Creating output table stubs...
[00_synthetic_data.R]    Output stubs done.
[00_synthetic_data.R] 6. Creating processed data stubs...
[00_synthetic_data.R]    RF model stub done.
[00_synthetic_data.R]    AEZ stub written (6 classes, spatially structured).
[00_synthetic_data.R]    Processed stubs done.
[00_synthetic_data.R] 6b. Creating Sarah Lowder xlsx stubs...
[00_synthetic_data.R]    Sarah Lowder xlsx stubs done.
[00_synthetic_data.R] 7. Creating figure stubs...
[00_synthetic_data.R]    Figure stubs done.
[00_synthetic_data.R] 8b. Creating leave-one stubs for 04.5 / 04.6...
[00_synthetic_data.R]    Leave-one stubs done (character means/test, TPS test-only).
[00_synthetic_data.R] 9. Creating country-year raw files...
[00_synthetic_data.R] 
[00_synthetic_data.R] ======================================================================
[00_synthetic_data.R] SYNTHETIC DATA GENERATION COMPLETE
[00_synthetic_data.R] ======================================================================
[00_synthetic_data.R]   Farms generated:   7029
[00_synthetic_data.R]   After 95th trim:   4177
[00_synthetic_data.R]   Countries:         16
[00_synthetic_data.R]   Raster layers:     11
[00_synthetic_data.R]   Training res:      0.5° (~56 km) — 14000 cells/layer
[00_synthetic_data.R]   Prediction res:    5° (~555 km) — 140 cells/layer (~3-9 per country)
[00_synthetic_data.R]   QRF stack cells:   140 cells × 100 quantiles = 14000 values
[00_synthetic_data.R]   Prediction stubs:  6 Python + RF + QRF rasters
[00_synthetic_data.R]   Output stubs:      15
[00_synthetic_data.R]   Processed files:   137
  ✓ PASS  00_synthetic_data                              (  6.6s)  
----------------------------------------------------------------------
PHASE 1: Install/Download Scripts (skipped in CI)
----------------------------------------------------------------------
  ✓ PASS  00_install_packages.R                          (  0.0s)  SKIPPED (download/SLURM/data-only script)
  ✓ PASS  00_download_spatial_data.R                     (  0.0s)  SKIPPED (download/SLURM/data-only script)
  ✓ PASS  01.2_chirps_summarize.R                        (  0.0s)  SKIPPED (download/SLURM/data-only script)
  ✓ PASS  02.1_compile_LSMS.R                            (  0.0s)  SKIPPED (download/SLURM/data-only script)
  ✓ PASS  05.2_RF_optimization_summary.R                 (  0.0s)  SKIPPED (download/SLURM/data-only script)
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
[01.1_chirps_download.R]   Processed data: 111
[01.1_chirps_download.R]   Output tables:  9
[01.1_chirps_download.R] 
[01.1_chirps_download.R] Data summary:
[01.1_chirps_download.R]   Total farms:    4291
[01.1_chirps_download.R]   Countries:      16
[01.1_chirps_download.R]   Farm size range:0.1-21.18ha
[01.1_chirps_download.R]   Median farm:    1.33ha
[01.1_chirps_download.R] 
[01.1_chirps_download.R] Finished: 2026-03-16 12:25:09.799851
[01.1_chirps_download.R] ======================================================================
  ✓ PASS  01.1_chirps_download.R                         (  1.9s)  
[01.3_chirps_trends.R] Loading required package: terra
[01.3_chirps_trends.R] terra 1.8.93
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
  ✓ PASS  01.3_chirps_trends.R                           (  3.8s)  
[01.4_prepare_spatial_layers.R] Loading required package: terra
[01.4_prepare_spatial_layers.R] terra 1.8.93
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
[01.4_prepare_spatial_layers.R]   Min:    396
[01.4_prepare_spatial_layers.R]   Median: 1002.6
[01.4_prepare_spatial_layers.R]   Max:    1581.1
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R] Rainfall CV:
[01.4_prepare_spatial_layers.R]   Min:    0.028
[01.4_prepare_spatial_layers.R]   Median: 0.276
[01.4_prepare_spatial_layers.R]   Max:    1.126
[01.4_prepare_spatial_layers.R] 
[01.4_prepare_spatial_layers.R]   % area with high variability (CV > 0.3): 41.9%
  ✓ PASS  01.4_prepare_spatial_layers.R                  (  3.2s)  
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
[03.2_correlation_drivers.R]   Downloaded: Senegal (level 4)
[03.2_correlation_drivers.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_TZA_3_pk.rds'
[03.2_correlation_drivers.R] Content type 'unknown' length 11426758 bytes (10.9 MB)
[03.2_correlation_drivers.R] ==================================================
[03.2_correlation_drivers.R] downloaded 10.9 MB
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R]   Downloaded: Tanzania (level 3)
[03.2_correlation_drivers.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_TGO_3_pk.rds'
[03.2_correlation_drivers.R] Content type 'unknown' length 490980 bytes (479 KB)
[03.2_correlation_drivers.R] ==================================================
[03.2_correlation_drivers.R] downloaded 479 KB
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R]   Downloaded: Togo (level 3)
[03.2_correlation_drivers.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_UGA_4_pk.rds'
[03.2_correlation_drivers.R] Content type 'unknown' length 13445867 bytes (12.8 MB)
[03.2_correlation_drivers.R] ==================================================
[03.2_correlation_drivers.R] downloaded 12.8 MB
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R]   Downloaded: Uganda (level 4)
[03.2_correlation_drivers.R]   Downloaded: Zambia (level 2)
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
[03.2_correlation_drivers.R] Error: [$<-] replacement has 4308 rows, data has 4283
[03.2_correlation_drivers.R] Execution halted
  ✗ FAIL  03.2_correlation_drivers.R                     ( 21.9s)  Exit code: 1
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
[03.3_descriptive_stats.R] Observations: 3645
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
[03.3_descriptive_stats.R]   market: r = 0.062
[03.3_descriptive_stats.R]   slope: r = 0.025
[03.3_descriptive_stats.R]   temperature: r = 0.008
[03.3_descriptive_stats.R]   pop: r = 0.008
[03.3_descriptive_stats.R]   maizeyield: r = 0.006
[03.3_descriptive_stats.R]   rainfall: r = -0.005
[03.3_descriptive_stats.R]   cropland_per_capita: r = -0.008
[03.3_descriptive_stats.R]   cropland: r = -0.025
[03.3_descriptive_stats.R]   cattle: r = -0.028
[03.3_descriptive_stats.R]   sand: r = -0.029
[03.3_descriptive_stats.R] 
[03.3_descriptive_stats.R] === Analysis Complete ===
  ✓ PASS  03.3_descriptive_stats.R                       ( 18.6s)  
----------------------------------------------------------------------
PHASE 4: ML Model Training (04.x)
----------------------------------------------------------------------
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
[04.1_comparing_ML_algorithms.R] Saved: ../output/tables/summary_descriptive_stats_survey.csv
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
[04.2_RF_within_country.R]     c("cropland", "cattle", "pop", "cropland_per_capita", "sand", 
[04.2_RF_within_country.R]         "slope", "temperature", "rainfall", "market", "maizeyield")]))
[04.2_RF_within_country.R]                                                 
[04.2_RF_within_country.R]  Number of Observations:                238     
[04.2_RF_within_country.R]  Number of parameters in the null space 13      
[04.2_RF_within_country.R]  Parameters for fixed spatial drift     3       
[04.2_RF_within_country.R]  Model degrees of freedom:              13      
[04.2_RF_within_country.R]  Residual degrees of freedom:           225     
[04.2_RF_within_country.R]  GCV estimate for tau:                  0.9743  
[04.2_RF_within_country.R]  MLE for tau:                           0.9474  
[04.2_RF_within_country.R]  MLE for sigma:                         3.55e-07
[04.2_RF_within_country.R]  lambda                                 2500000 
[04.2_RF_within_country.R]  User supplied sigma                    NA      
[04.2_RF_within_country.R]  User supplied tau^2                    NA      
[04.2_RF_within_country.R] Summary of estimates: 
[04.2_RF_within_country.R]             lambda      trA    GCV    tauHat -lnLike Prof converge
[04.2_RF_within_country.R] GCV        2527941 13.00097 1.0042 0.9743431     313.4134       NA
[04.2_RF_within_country.R] GCV.model       NA       NA     NA        NA           NA       NA
[04.2_RF_within_country.R] GCV.one    2527941 13.00097 1.0042 0.9743431           NA       NA
[04.2_RF_within_country.R] RMSE            NA       NA     NA        NA           NA       NA
[04.2_RF_within_country.R] pure error      NA       NA     NA        NA           NA       NA
[04.2_RF_within_country.R] REML       2527941 13.00097 1.0042 0.9743431     313.4134       NA
[04.2_RF_within_country.R] [1] "calculated_70-30_r2 = 0.07"
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
[04.2_RF_within_country.R] Time difference of 43.28516 secs
[04.2_RF_within_country.R] Error: object 'results_Benin' not found
[04.2_RF_within_country.R] Execution halted
  ✗ FAIL  04.2_RF_within_country.R                       ( 47.1s)  Exit code: 1
[04.3_RF_between_countries.R] [1] "--------------------Rwanda---------------------------"
[04.3_RF_between_countries.R] data frame with 0 columns and 0 rows
[04.3_RF_between_countries.R] [1] "--------------------Senegal---------------------------"
[04.3_RF_between_countries.R] data frame with 0 columns and 0 rows
[04.3_RF_between_countries.R] [1] "--------------------Tanzania---------------------------"
[04.3_RF_between_countries.R] data frame with 0 columns and 0 rows
[04.3_RF_between_countries.R] [1] "--------------------Togo---------------------------"
[04.3_RF_between_countries.R] data frame with 0 columns and 0 rows
[04.3_RF_between_countries.R] [1] "--------------------Uganda---------------------------"
[04.3_RF_between_countries.R] data frame with 0 columns and 0 rows
[04.3_RF_between_countries.R] [1] "--------------------Zambia---------------------------"
[04.3_RF_between_countries.R] data frame with 0 columns and 0 rows
[04.3_RF_between_countries.R] Time difference of 1.2412 secs
[04.3_RF_between_countries.R] Error in `pivot_longer()`:
[04.3_RF_between_countries.R] ! Can't select columns that don't exist.
[04.3_RF_between_countries.R] ✖ Column `rf_cv_rsq` doesn't exist.
[04.3_RF_between_countries.R] Backtrace:
[04.3_RF_between_countries.R]      ▆
[04.3_RF_between_countries.R]   1. ├─dplyr::mutate(...)
[04.3_RF_between_countries.R]   2. ├─tidyr::pivot_longer(...)
[04.3_RF_between_countries.R]   3. ├─tidyr:::pivot_longer.data.frame(...)
[04.3_RF_between_countries.R]   4. │ └─tidyr::build_longer_spec(...)
[04.3_RF_between_countries.R]   5. │   └─tidyselect::eval_select(...)
[04.3_RF_between_countries.R]   6. │     └─tidyselect:::eval_select_impl(...)
[04.3_RF_between_countries.R]   7. │       ├─tidyselect:::with_subscript_errors(...)
[04.3_RF_between_countries.R]   8. │       │ └─base::withCallingHandlers(...)
[04.3_RF_between_countries.R]   9. │       └─tidyselect:::vars_select_eval(...)
[04.3_RF_between_countries.R]  10. │         └─tidyselect:::walk_data_tree(expr, data_mask, context_mask)
[04.3_RF_between_countries.R]  11. │           └─tidyselect:::eval_c(expr, data_mask, context_mask)
[04.3_RF_between_countries.R]  12. │             └─tidyselect:::reduce_sels(node, data_mask, context_mask, init = init)
[04.3_RF_between_countries.R]  13. │               └─tidyselect:::walk_data_tree(new, data_mask, context_mask)
[04.3_RF_between_countries.R]  14. │                 └─tidyselect:::as_indices_sel_impl(...)
[04.3_RF_between_countries.R]  15. │                   └─tidyselect:::as_indices_impl(...)
[04.3_RF_between_countries.R]  16. │                     └─tidyselect:::chr_as_locations(x, vars, call = call, arg = arg)
[04.3_RF_between_countries.R]  17. │                       └─vctrs::vec_as_location(...)
[04.3_RF_between_countries.R]  18. └─vctrs (local) `<fn>`()
[04.3_RF_between_countries.R]  19.   └─vctrs:::stop_subscript_oob(...)
[04.3_RF_between_countries.R]  20.     └─vctrs:::stop_subscript(...)
[04.3_RF_between_countries.R]  21.       └─rlang::abort(...)
[04.3_RF_between_countries.R] Execution halted
  ✗ FAIL  04.3_RF_between_countries.R                    (  5.2s)  Exit code: 1
[04.4_RF_model_evaluation.R] 1 Nigeria          0.09       0.01             0        -0.1         0.18
[04.4_RF_model_evaluation.R]   rf3_test_rsq cor_tps1_rf3 cor_rf1_rf3 tps2_test_rsq rf2_cv_rsq rf2_cv_rsq_sd
[04.4_RF_model_evaluation.R] 1            0            0           0          0.09          0             0
[04.4_RF_model_evaluation.R]   rf2_oob_rsq rf2_test_rsq rf4_test_rsq cor_tps2_rf4 cor_rf2_rf4
[04.4_RF_model_evaluation.R] 1        -0.1         0.19            0            0           0
[04.4_RF_model_evaluation.R] [1] "--------------------Rwanda---------------------------"
[04.4_RF_model_evaluation.R] Warning: 
[04.4_RF_model_evaluation.R] Grid searches over lambda (nugget and sill variances) with  minima at the endpoints: 
[04.4_RF_model_evaluation.R]   (GCV) Generalized Cross-Validation 
[04.4_RF_model_evaluation.R]    minimum at  right endpoint  lambda  =  2021880 (eff. df= 13.00099 )
[04.4_RF_model_evaluation.R] Warning: 
[04.4_RF_model_evaluation.R] Grid searches over lambda (nugget and sill variances) with  minima at the endpoints: 
[04.4_RF_model_evaluation.R]   (GCV) Generalized Cross-Validation 
[04.4_RF_model_evaluation.R]    minimum at  right endpoint  lambda  =  2021880 (eff. df= 13.00099 )
[04.4_RF_model_evaluation.R]   country tps1_test_rsq rf1_cv_rsq rf1_cv_rsq_sd rf1_oob_rsq rf1_test_rsq
[04.4_RF_model_evaluation.R] 1  Rwanda          0.05          0             0       -0.22         0.13
[04.4_RF_model_evaluation.R]   rf3_test_rsq cor_tps1_rf3 cor_rf1_rf3 tps2_test_rsq rf2_cv_rsq rf2_cv_rsq_sd
[04.4_RF_model_evaluation.R] 1            0            0           0          0.05          0             0
[04.4_RF_model_evaluation.R]   rf2_oob_rsq rf2_test_rsq rf4_test_rsq cor_tps2_rf4 cor_rf2_rf4
[04.4_RF_model_evaluation.R] 1       -0.22         0.13            0            0           0
[04.4_RF_model_evaluation.R] [1] "--------------------Senegal---------------------------"
[04.4_RF_model_evaluation.R]   country tps1_test_rsq rf1_cv_rsq rf1_cv_rsq_sd rf1_oob_rsq rf1_test_rsq
[04.4_RF_model_evaluation.R] 1 Senegal          0.13       0.01             0       -0.09         0.17
[04.4_RF_model_evaluation.R]   rf3_test_rsq cor_tps1_rf3 cor_rf1_rf3 tps2_test_rsq rf2_cv_rsq rf2_cv_rsq_sd
[04.4_RF_model_evaluation.R] 1            0            0           0          0.13       0.01             0
[04.4_RF_model_evaluation.R]   rf2_oob_rsq rf2_test_rsq rf4_test_rsq cor_tps2_rf4 cor_rf2_rf4
[04.4_RF_model_evaluation.R] 1       -0.08         0.17            0            0           0
[04.4_RF_model_evaluation.R] [1] "--------------------Tanzania---------------------------"
[04.4_RF_model_evaluation.R] 
[04.4_RF_model_evaluation.R] 
[04.4_RF_model_evaluation.R]  *** caught segfault ***
[04.4_RF_model_evaluation.R] address (nil), cause 'memory not mapped'
[04.4_RF_model_evaluation.R] 
[04.4_RF_model_evaluation.R]  *** caught segfault ***
[04.4_RF_model_evaluation.R] address 0x1a88, cause 'memory not mapped'
[04.4_RF_model_evaluation.R] Error: no more error handlers available (recursive errors?); invoking 'abort' restart
[04.4_RF_model_evaluation.R] Error in value[[2L]] : no index specified
[04.4_RF_model_evaluation.R] Fatal error: error during cleanup
[04.4_RF_model_evaluation.R] 
[04.4_RF_model_evaluation.R] Segmentation fault (core dumped)
  ✗ FAIL  04.4_RF_model_evaluation.R                     (604.5s)  Exit code: 124
[04.5_cross_country_graphs.R] Error in gzfile(file, "rb") : invalid 'description' argument
[04.5_cross_country_graphs.R] Calls: summarize -> sapply -> lapply -> FUN -> readRDS -> gzfile
[04.5_cross_country_graphs.R] Execution halted
  ✗ FAIL  04.5_cross_country_graphs.R                    (  0.2s)  Exit code: 1
[04.6_discrepancy_analysis.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[04.6_discrepancy_analysis.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[04.6_discrepancy_analysis.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[04.6_discrepancy_analysis.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[04.6_discrepancy_analysis.R] ✔ purrr     1.2.1     
[04.6_discrepancy_analysis.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[04.6_discrepancy_analysis.R] ✖ dplyr::filter() masks stats::filter()
[04.6_discrepancy_analysis.R] ✖ dplyr::lag()    masks stats::lag()
[04.6_discrepancy_analysis.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[04.6_discrepancy_analysis.R] `summarise()` has regrouped the output.
[04.6_discrepancy_analysis.R] ℹ Summaries were computed grouped by country, code, and model.
[04.6_discrepancy_analysis.R] ℹ Output is grouped by country and code.
[04.6_discrepancy_analysis.R] ℹ Use `summarise(.groups = "drop_last")` to silence this message.
[04.6_discrepancy_analysis.R] ℹ Use `summarise(.by = c(country, code, model))` for per-operation grouping
[04.6_discrepancy_analysis.R]   (`?dplyr::dplyr_by`) instead.
[04.6_discrepancy_analysis.R] Saving 15 x 7.5 in image
[04.6_discrepancy_analysis.R] pdf 
[04.6_discrepancy_analysis.R]   2 
[04.6_discrepancy_analysis.R] Saving 15 x 7.5 in image
[04.6_discrepancy_analysis.R] pdf 
[04.6_discrepancy_analysis.R]   2 
[04.6_discrepancy_analysis.R] Saving 7.5 x 5 in image
[04.6_discrepancy_analysis.R] pdf 
[04.6_discrepancy_analysis.R]   2 
[04.6_discrepancy_analysis.R] # A tibble: 10 × 2
[04.6_discrepancy_analysis.R]    var                 avg_rank
[04.6_discrepancy_analysis.R]    <chr>                  <dbl>
[04.6_discrepancy_analysis.R]  1 rainfall                4.56
[04.6_discrepancy_analysis.R]  2 temperature             4.56
[04.6_discrepancy_analysis.R]  3 market                  4.75
[04.6_discrepancy_analysis.R]  4 cattle                  4.81
[04.6_discrepancy_analysis.R]  5 maizeyield              5.12
[04.6_discrepancy_analysis.R]  6 cropland                5.38
[04.6_discrepancy_analysis.R]  7 slope                   5.62
[04.6_discrepancy_analysis.R]  8 pop                     6.38
[04.6_discrepancy_analysis.R]  9 sand                    6.69
[04.6_discrepancy_analysis.R] 10 cropland_per_capita     7.12
[04.6_discrepancy_analysis.R] Saving 5.91 x 2.95 in image
[04.6_discrepancy_analysis.R] pdf 
[04.6_discrepancy_analysis.R]   2 
  ✓ PASS  04.6_discrepancy_analysis.R                    ( 14.9s)  
Warning message:
In system2("Rscript", c("--vanilla", shQuote(tmp)), stdout = log_file,  :
  command ''Rscript' --vanilla '/tmp/RtmpEwn731/file19e057be1a9a.R' > '/tmp/RtmpEwn731/file19e02750615.log' 2>&1' timed out after 600s
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
  ✓ PASS  05.1_RF_optimization.R                         (  3.9s)  
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
  ✓ PASS  06.1_quantile_RF.R                             (  3.3s)  
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
[06.3_prediction_maps.R] Loading required package: lattice
[06.3_prediction_maps.R] 
[06.3_prediction_maps.R] Attaching package: ‘caret’
[06.3_prediction_maps.R] 
[06.3_prediction_maps.R] The following object is masked from ‘package:purrr’:
[06.3_prediction_maps.R] 
[06.3_prediction_maps.R]     lift
[06.3_prediction_maps.R] 
[06.3_prediction_maps.R] Time difference of 17.37324 secs
[06.3_prediction_maps.R] Error in na.fail.default(list(farm_area_ha = c(1.5913, 2.0783, 0.2898,  : 
[06.3_prediction_maps.R]   missing values in object
[06.3_prediction_maps.R] Calls: <Anonymous> ... model.frame.default -> <Anonymous> -> na.fail.default
[06.3_prediction_maps.R] Execution halted
  ✗ FAIL  06.3_prediction_maps.R                         (128.8s)  Exit code: 1
[06.4_cropland_sensitivity.R]  Mean   :2.1380  
[06.4_cropland_sensitivity.R]  3rd Qu.:2.6113  
[06.4_cropland_sensitivity.R]  Max.   :4.2277  
[06.4_cropland_sensitivity.R] null device 
[06.4_cropland_sensitivity.R]           1 
[06.4_cropland_sensitivity.R] null device 
[06.4_cropland_sensitivity.R]           1 
[06.4_cropland_sensitivity.R] Error in `annotate()`:
[06.4_cropland_sensitivity.R] ! Problem while setting up geom aesthetics.
[06.4_cropland_sensitivity.R] ℹ Error occurred in the 5th layer.
[06.4_cropland_sensitivity.R] Caused by error in `list_sizes()`:
[06.4_cropland_sensitivity.R] ! `x$label` must be a vector, not a call.
[06.4_cropland_sensitivity.R] ℹ Read our FAQ about scalar types (`?vctrs::faq_error_scalar_type`) to learn more.
[06.4_cropland_sensitivity.R] Backtrace:
[06.4_cropland_sensitivity.R]      ▆
[06.4_cropland_sensitivity.R]   1. ├─base (local) `<fn>`(x)
[06.4_cropland_sensitivity.R]   2. ├─ggplot2 (local) `print.ggplot2::ggplot`(x)
[06.4_cropland_sensitivity.R]   3. │ ├─ggplot2::ggplot_build(x)
[06.4_cropland_sensitivity.R]   4. │ └─ggplot2 (local) `ggplot_build.ggplot2::ggplot`(x)
[06.4_cropland_sensitivity.R]   5. │   └─ggplot2:::by_layer(...)
[06.4_cropland_sensitivity.R]   6. │     ├─rlang::try_fetch(...)
[06.4_cropland_sensitivity.R]   7. │     │ ├─base::tryCatch(...)
[06.4_cropland_sensitivity.R]   8. │     │ │ └─base (local) tryCatchList(expr, classes, parentenv, handlers)
[06.4_cropland_sensitivity.R]   9. │     │ │   └─base (local) tryCatchOne(expr, names, parentenv, handlers[[1L]])
[06.4_cropland_sensitivity.R]  10. │     │ │     └─base (local) doTryCatch(return(expr), name, parentenv, handler)
[06.4_cropland_sensitivity.R]  11. │     │ └─base::withCallingHandlers(...)
[06.4_cropland_sensitivity.R]  12. │     └─ggplot2 (local) f(l = layers[[i]], d = data[[i]])
[06.4_cropland_sensitivity.R]  13. │       └─l$compute_geom_2(d, theme = plot@theme)
[06.4_cropland_sensitivity.R]  14. │         └─ggplot2 (local) compute_geom_2(..., self = self)
[06.4_cropland_sensitivity.R]  15. │           └─self$geom$use_defaults(...)
[06.4_cropland_sensitivity.R]  16. │             └─ggplot2 (local) use_defaults(..., self = self)
[06.4_cropland_sensitivity.R]  17. │               └─ggplot2:::check_aesthetics(new_params, nrow(data))
[06.4_cropland_sensitivity.R]  18. │                 └─vctrs::list_sizes(x)
[06.4_cropland_sensitivity.R]  19. └─vctrs:::stop_scalar_type(`<fn>`(R^2 == 0), "x$label", `<env>`)
[06.4_cropland_sensitivity.R]  20.   └─vctrs:::stop_vctrs(...)
[06.4_cropland_sensitivity.R]  21.     └─rlang::abort(message, class = c(class, "vctrs_error"), ..., call = call)
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] Removed 3508 rows containing non-finite outside the scale range
[06.4_cropland_sensitivity.R] (`stat_density2d_filled()`). 
[06.4_cropland_sensitivity.R] Execution halted
  ✗ FAIL  06.4_cropland_sensitivity.R                    (  7.7s)  Exit code: 1
----------------------------------------------------------------------
PHASE 7: Predictions & Validation (07.x – 10.x)
----------------------------------------------------------------------
[07.2_QRF_distribution_eval.R] 13 GLW2010   2   Zimbabwe        0.753
[07.2_QRF_distribution_eval.R] 14 GLW2010   4   South Sudan     0.571
[07.2_QRF_distribution_eval.R] 15 GLW2010   5   Burkina Faso    0.788
[07.2_QRF_distribution_eval.R] 16 GLW2010   6   Congo           0.380
[07.2_QRF_distribution_eval.R] 17 GLW2010   7   Mali            1.46 
[07.2_QRF_distribution_eval.R] 18 GLW2010   8   Namibia         3.45 
[07.2_QRF_distribution_eval.R] 19 GLW2010   9   Sudan           2.01 
[07.2_QRF_distribution_eval.R] 20 GLW2010  10   Botswana        0    
[07.2_QRF_distribution_eval.R] # A tibble: 20 × 4
[07.2_QRF_distribution_eval.R]    source    rank NAME_0                   cropland
[07.2_QRF_distribution_eval.R]    <chr>    <dbl> <fct>                       <dbl>
[07.2_QRF_distribution_eval.R]  1 SPAM2017     1 Zimbabwe                    0.343
[07.2_QRF_distribution_eval.R]  2 SPAM2017     2 South Sudan                 0.657
[07.2_QRF_distribution_eval.R]  3 SPAM2017     3 Botswana                    0    
[07.2_QRF_distribution_eval.R]  4 SPAM2017     4 Zambia                      0.586
[07.2_QRF_distribution_eval.R]  5 SPAM2017     5 South Africa                2.76 
[07.2_QRF_distribution_eval.R]  6 SPAM2017     6 Burkina Faso                0.354
[07.2_QRF_distribution_eval.R]  7 SPAM2017     7 Congo                       0.305
[07.2_QRF_distribution_eval.R]  8 SPAM2017     8 Central African Republic    1.41 
[07.2_QRF_distribution_eval.R]  9 SPAM2017     9 Cameroon                    1.45 
[07.2_QRF_distribution_eval.R] 10 SPAM2017    10 Liberia                     0.901
[07.2_QRF_distribution_eval.R] 11 SPAM2020     1 Zimbabwe                    0.336
[07.2_QRF_distribution_eval.R] 12 SPAM2020     2 Cameroon                    2.42 
[07.2_QRF_distribution_eval.R] 13 SPAM2020     3 Congo                       0.738
[07.2_QRF_distribution_eval.R] 14 SPAM2020     4 Botswana                    0.181
[07.2_QRF_distribution_eval.R] 15 SPAM2020     5 Burkina Faso                0.848
[07.2_QRF_distribution_eval.R] 16 SPAM2020     6 Mali                        1.57 
[07.2_QRF_distribution_eval.R] 17 SPAM2020     7 Ethiopia                    2.99 
[07.2_QRF_distribution_eval.R] 18 SPAM2020     8 South Sudan                 0.300
[07.2_QRF_distribution_eval.R] 19 SPAM2020     9 Namibia                     1.44 
[07.2_QRF_distribution_eval.R] 20 SPAM2020    10 Nigeria                     1.08 
[07.2_QRF_distribution_eval.R] Saving 7.87 x 5.91 in image
[07.2_QRF_distribution_eval.R] pdf 
[07.2_QRF_distribution_eval.R]   2 
[07.2_QRF_distribution_eval.R] Saving 7.87 x 5.91 in image
[07.2_QRF_distribution_eval.R] pdf 
[07.2_QRF_distribution_eval.R]   2 
[07.2_QRF_distribution_eval.R] Saving 7.87 x 5.91 in image
[07.2_QRF_distribution_eval.R] pdf 
[07.2_QRF_distribution_eval.R]   2 
  ✓ PASS  07.2_QRF_distribution_eval.R                   ( 18.0s)  
[08.1_predictions_by_country.R]   [1] -1.0000000  0.3329033  0.5204920  0.6303369  0.7092858  0.8125987
[08.1_predictions_by_country.R]   [7]  0.9345316  1.0352998  1.2641242  1.2756853  1.3840717  1.4628808
[08.1_predictions_by_country.R]  [13]  1.4897225  1.5006390  1.5173109  1.5281886  1.6268759  1.6426536
[08.1_predictions_by_country.R]  [19]  1.6515175  1.6568389  1.6743498  1.6932995  1.7520846  1.7564539
[08.1_predictions_by_country.R]  [25]  1.7787949  1.7833016  1.8008497  1.8031616  1.8119439  1.8167387
[08.1_predictions_by_country.R]  [31]  1.8261924  1.8531245  1.8861794  1.9632238  1.9641868  1.9707963
[08.1_predictions_by_country.R]  [37]  1.9961449  1.9971387  2.0219920  2.0349009  2.0365214  2.0789893
[08.1_predictions_by_country.R]  [43]  2.0969374  2.0985281  2.1350496  2.1622748  2.1706924  2.1750808
[08.1_predictions_by_country.R]  [49]  2.1991148  2.2166212  2.2305787  2.2330987  2.2576973  2.3186827
[08.1_predictions_by_country.R]  [55]  2.3235319  2.3731201  2.4588671  2.5072017  2.5075345  2.5097332
[08.1_predictions_by_country.R]  [61]  2.5328591  2.5410175  2.5702715  2.5738025  2.5981207  2.6020203
[08.1_predictions_by_country.R]  [67]  2.6044431  2.6163867  2.6176991  2.6234400  2.6439867  2.7144947
[08.1_predictions_by_country.R]  [73]  2.7268758  2.7403102  2.7995422  2.8116975  2.8249874  2.8945100
[08.1_predictions_by_country.R]  [79]  2.9150684  2.9831769  3.0009320  3.0193627  3.0519392  3.0571475
[08.1_predictions_by_country.R]  [85]  3.0631099  3.0825624  3.0833473  3.1108673  3.1506848  3.1541016
[08.1_predictions_by_country.R]  [91]  3.1633291  3.1648471  3.2103829  3.3047647  3.4034150  3.6264617
[08.1_predictions_by_country.R]  [97]  3.6291726  3.6648860  3.6676855  4.0160298  4.3282161  4.7610377
[08.1_predictions_by_country.R] [1] "---------- nrow = 4920630------------"
[08.1_predictions_by_country.R] [1] ""
[08.1_predictions_by_country.R] [1] "expected boundaries of quantiles"
[08.1_predictions_by_country.R]   [1] -1.0000000  0.3419589  0.7332430  0.8183026  0.9564528  0.9957287
[08.1_predictions_by_country.R]   [7]  1.0826693  1.1488191  1.2304757  1.2448906  1.2480789  1.3232446
[08.1_predictions_by_country.R]  [13]  1.3750026  1.3801091  1.3945788  1.4878749  1.5113866  1.5790272
[08.1_predictions_by_country.R]  [19]  1.6891283  1.7053522  1.7142278  1.7148504  1.7497913  1.7792515
[08.1_predictions_by_country.R]  [25]  1.7795640  1.8259100  1.8315619  1.8362800  1.8743161  1.9018198
[08.1_predictions_by_country.R]  [31]  1.9251773  1.9380887  1.9756371  1.9776126  1.9786361  1.9873054
[08.1_predictions_by_country.R]  [37]  2.0108166  2.0366809  2.0457921  2.0720625  2.0794806  2.0929141
[08.1_predictions_by_country.R]  [43]  2.1030793  2.1075559  2.1103323  2.1250074  2.1318607  2.1619043
[08.1_predictions_by_country.R]  [49]  2.1653593  2.1675806  2.1909637  2.1931002  2.1936705  2.2607400
[08.1_predictions_by_country.R]  [55]  2.2810118  2.2860096  2.2945507  2.3122020  2.3271933  2.3393838
[08.1_predictions_by_country.R]  [61]  2.4060307  2.4213860  2.4299707  2.4555941  2.4964967  2.4982872
[08.1_predictions_by_country.R]  [67]  2.5281951  2.5628884  2.5656080  2.5916486  2.6018295  2.6290982
[08.1_predictions_by_country.R]  [73]  2.6344650  2.6627462  2.8070226  2.8643601  2.9243696  2.9317882
[08.1_predictions_by_country.R]  [79]  2.9419887  2.9797049  3.0127821  3.0307026  3.0730197  3.0906594
[08.1_predictions_by_country.R]  [85]  3.1123416  3.1261213  3.1552899  3.1646888  3.1953101  3.2704012
[08.1_predictions_by_country.R]  [91]  3.2830002  3.3254509  3.4067619  3.5168085  3.5248332  3.5585871
[08.1_predictions_by_country.R]  [97]  3.6258936  3.8444095  3.8464122  4.0823288  4.1515765  4.5667342
[08.1_predictions_by_country.R] 
[08.1_predictions_by_country.R] [1] ""
[08.1_predictions_by_country.R] Execution halted
  ✗ FAIL  08.1_predictions_by_country.R                  (600.0s)  Exit code: 124
[08.2_generate_virtual_farms.R] Loading required package: tidyverse
[08.2_generate_virtual_farms.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[08.2_generate_virtual_farms.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[08.2_generate_virtual_farms.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[08.2_generate_virtual_farms.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[08.2_generate_virtual_farms.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[08.2_generate_virtual_farms.R] ✔ purrr     1.2.1     
[08.2_generate_virtual_farms.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[08.2_generate_virtual_farms.R] ✖ dplyr::filter() masks stats::filter()
[08.2_generate_virtual_farms.R] ✖ dplyr::lag()    masks stats::lag()
[08.2_generate_virtual_farms.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[08.2_generate_virtual_farms.R] Error: [rast] number of rows and/or columns do not match
[08.2_generate_virtual_farms.R] Execution halted
  ✗ FAIL  08.2_generate_virtual_farms.R                  (  7.4s)  Exit code: 1
[08.3_farm_size_classes.R] [1] "rsquare_linear = 0.0038"
[08.3_farm_size_classes.R] [1] "rsquare_linear_fixed = 0.0031"
[08.3_farm_size_classes.R] [1] "rsquare_fix_truncated_max = 0.003"
[08.3_farm_size_classes.R] [1] "rsquare_trun_logn = 0.0053"
[08.3_farm_size_classes.R] [1] "------------- row 127----------------"
[08.3_farm_size_classes.R] [1] "rsquare_linear = 0.0249"
[08.3_farm_size_classes.R] [1] "rsquare_linear_fixed = 0.0265"
[08.3_farm_size_classes.R] [1] "rsquare_fix_truncated_max = 0.0259"
[08.3_farm_size_classes.R] [1] "rsquare_trun_logn = 0.0286"
[08.3_farm_size_classes.R] [1] "------------- row 128----------------"
[08.3_farm_size_classes.R] [1] "rsquare_linear = 0.001"
[08.3_farm_size_classes.R] [1] "rsquare_linear_fixed = 0.0013"
[08.3_farm_size_classes.R] [1] "rsquare_fix_truncated_max = 0.0012"
[08.3_farm_size_classes.R] [1] "rsquare_trun_logn = 8e-04"
[08.3_farm_size_classes.R]           used  (Mb) gc trigger  (Mb) max used  (Mb)
[08.3_farm_size_classes.R] Ncells 1961725 104.8    3712147 198.3  2846530 152.1
[08.3_farm_size_classes.R] Vcells 4061660  31.0    8388608  64.0  8348885  63.7
[08.3_farm_size_classes.R] Error in `summarize()`:
[08.3_farm_size_classes.R] ℹ In argument: `nb_farms_below = n()/nb_farms`.
[08.3_farm_size_classes.R] ℹ In group 1: `x = -15.5`, `y = -27.5`.
[08.3_farm_size_classes.R] Caused by error:
[08.3_farm_size_classes.R] ! `nb_farms_below` must be size 1, not 85.
[08.3_farm_size_classes.R] ℹ To return more or less than 1 row per group, use `reframe()`.
[08.3_farm_size_classes.R] Backtrace:
[08.3_farm_size_classes.R]      ▆
[08.3_farm_size_classes.R]   1. ├─base::sapply(c(0.5, 1, 2), map_at_threshold)
[08.3_farm_size_classes.R]   2. │ └─base::lapply(X = X, FUN = FUN, ...)
[08.3_farm_size_classes.R]   3. │   └─global FUN(X[[i]], ...)
[08.3_farm_size_classes.R]   4. │     ├─dplyr::summarize(...)
[08.3_farm_size_classes.R]   5. │     └─dplyr:::summarise.grouped_df(...)
[08.3_farm_size_classes.R]   6. │       └─dplyr:::summarise_cols(.data, dplyr_quosures(...), by, "summarise")
[08.3_farm_size_classes.R]   7. │         └─base::withCallingHandlers(...)
[08.3_farm_size_classes.R]   8. ├─dplyr:::dplyr_internal_error(...)
[08.3_farm_size_classes.R]   9. │ └─rlang::abort(class = c(class, "dplyr:::internal_error"), dplyr_error_data = data)
[08.3_farm_size_classes.R]  10. │   └─rlang:::signal_abort(cnd, .file)
[08.3_farm_size_classes.R]  11. │     └─base::signalCondition(cnd)
[08.3_farm_size_classes.R]  12. └─dplyr (local) `<fn>`(`<dpl:::__>`)
[08.3_farm_size_classes.R]  13.   └─dplyr (local) handler(cnd)
[08.3_farm_size_classes.R]  14.     └─rlang::abort(message, class = error_class, parent = parent, call = error_call)
[08.3_farm_size_classes.R] Execution halted
  ✗ FAIL  08.3_farm_size_classes.R                       (  6.9s)  Exit code: 1
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
[09.1_AEZ_characterization.R] Error: unexpected end of input
[09.1_AEZ_characterization.R] Execution halted
  ✗ FAIL  09.1_AEZ_characterization.R                    (  4.0s)  Exit code: 1
[10.1_prepare_validation_data.R] Loading required package: tidyverse
[10.1_prepare_validation_data.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[10.1_prepare_validation_data.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[10.1_prepare_validation_data.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[10.1_prepare_validation_data.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[10.1_prepare_validation_data.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[10.1_prepare_validation_data.R] ✔ purrr     1.2.1     
[10.1_prepare_validation_data.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[10.1_prepare_validation_data.R] ✖ dplyr::filter() masks stats::filter()
[10.1_prepare_validation_data.R] ✖ dplyr::lag()    masks stats::lag()
[10.1_prepare_validation_data.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[10.1_prepare_validation_data.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[10.1_prepare_validation_data.R] Ncells 1781317 95.2    2846530 152.1  2846530 152.1
[10.1_prepare_validation_data.R] Vcells 2496402 19.1    8388608  64.0  4243639  32.4
[10.1_prepare_validation_data.R]    Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
[10.1_prepare_validation_data.R]   0.010   1.579   2.040   2.040   2.501   4.852 
[10.1_prepare_validation_data.R] NULL
[10.1_prepare_validation_data.R] # A tibble: 6 × 7
[10.1_prepare_validation_data.R]   aez                  avg   med   std  gini tot_cropland    nb
[10.1_prepare_validation_data.R]   <fct>              <dbl> <dbl> <dbl> <dbl>        <dbl> <int>
[10.1_prepare_validation_data.R] 1 humid               2.13  2.12 0.661 0.175       36737. 17277
[10.1_prepare_validation_data.R] 2 sub-humid           2.05  2.03 0.675 0.186       28078. 13722
[10.1_prepare_validation_data.R] 3 semi-arid           2.22  2.24 0.677 0.172       22957. 10340
[10.1_prepare_validation_data.R] 4 arid                2.30  2.28 0.622 0.153       11903.  5186
[10.1_prepare_validation_data.R] 5 tropical highlands  2.09  2.11 0.677 0.183       14372.  6880
[10.1_prepare_validation_data.R] 6 sub-tropical        1.76  1.77 0.655 0.209       32812. 18593
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez, avg, med, std, gini, tot_cropland, nb)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez, avg, med, std, gini, tot_cropland, nb)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez, avg, med, std, gini, tot_cropland, nb)`
[10.1_prepare_validation_data.R] Error: [rast] cannot open this file as a SpatRaster: /home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/data/raw/spatial/spam/spam2017
[10.1_prepare_validation_data.R] In addition: Warning message:
[10.1_prepare_validation_data.R] `/home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/data/raw/spatial/spam/spam2017' not recognized as a supported file format. (GDAL error 4) 
[10.1_prepare_validation_data.R] Execution halted
  ✗ FAIL  10.1_prepare_validation_data.R                 (  4.4s)  Exit code: 1
[10.2_external_validation.R] Loading required package: tidyverse
[10.2_external_validation.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[10.2_external_validation.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[10.2_external_validation.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[10.2_external_validation.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[10.2_external_validation.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[10.2_external_validation.R] ✔ purrr     1.2.1     
[10.2_external_validation.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[10.2_external_validation.R] ✖ dplyr::filter() masks stats::filter()
[10.2_external_validation.R] ✖ dplyr::lag()    masks stats::lag()
[10.2_external_validation.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[10.2_external_validation.R] [1] "LC_CTYPE=en_US.UTF-8;LC_NUMERIC=C;LC_TIME=en_US.UTF-8;LC_COLLATE=en_US.UTF-8;LC_MONETARY=en_US.UTF-8;LC_MESSAGES=C.UTF-8;LC_PAPER=C.UTF-8;LC_NAME=C;LC_ADDRESS=C;LC_TELEPHONE=C;LC_MEASUREMENT=C.UTF-8;LC_IDENTIFICATION=C"
[10.2_external_validation.R] Here is the list of valid country names 
[10.2_external_validation.R] Angola;Burundi;Benin;Burkina Faso;Botswana;Central African Republic;Côte d'Ivoire;Cameroon;Democratic Republic of the Congo;Congo;Djibouti;Eritrea;Ethiopia;Gabon;Ghana;Guinea;Gambia;Guinea-Bissau;Equatorial Guinea;Kenya;Liberia;Lesotho;Madagascar;Mali;Mozambique;Mauritania;Malawi;Namibia;Niger;Nigeria;Rwanda;Sudan;Senegal;Sierra Leone;Somalia;South Sudan;Eswatini;Chad;Togo;Tanzania;Uganda;South Africa;Zambia;Zimbabwe[1] "Important notice: In case, you would like to include Burkina, Cote_d_Ivoire and/or Guinea_Bissau in the validation countries,\n      make sure you manually duplicate the related folders in input_path and rename the new folders using the actual GADM names.\n      Besides some countries are shown to lack enough prediction data: Equatorial Guinea, Lesotho. Please skip them"
[10.2_external_validation.R] [1] "------------------------------------------------"
[10.2_external_validation.R] [1] "The following countries are not eligible"
[10.2_external_validation.R] [1] "Djibouti"          "Equatorial Guinea" "Lesotho"          
[10.2_external_validation.R] [1] "------------------------------------------------"
[10.2_external_validation.R] [1] "------------ Angola---------------"
[10.2_external_validation.R] Error: [vect] file does not exist: NA
[10.2_external_validation.R] Execution halted
  ✗ FAIL  10.2_external_validation.R                     (  4.0s)  Exit code: 1
Warning message:
In system2("Rscript", c("--vanilla", shQuote(tmp)), stdout = log_file,  :
  command ''Rscript' --vanilla '/tmp/RtmpEwn731/file19e03bf4d2d8.R' > '/tmp/RtmpEwn731/file19e037fce82c.log' 2>&1' timed out after 600s
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
[F01_main_figure1.R] Error: unexpected ',' in "                                            area = list(c(70, 35, 380, 565)),"
[F01_main_figure1.R] Execution halted
  ✗ FAIL  F01_main_figure1.R                             (  3.9s)  Exit code: 1
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
[F02_main_figure2.R] Ncells 1787586 95.5    2818547 150.6  2818547 150.6
[F02_main_figure2.R] Vcells 2518879 19.3    8388608  64.0  4311848  32.9
[F02_main_figure2.R] Error in h(simpleError(msg, call)) : 
[F02_main_figure2.R]   error in evaluating the argument 'x' in selecting a method for function 'plot': [subset] invalid name(s)
[F02_main_figure2.R] Calls: <Anonymous> -> $ -> subset -> subset -> .local -> error
[F02_main_figure2.R] Execution halted
  ✗ FAIL  F02_main_figure2.R                             (  4.1s)  Exit code: 1
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
[F03_main_figure3.R] Ncells 1787589 95.5    2818547 150.6  2818547 150.6
[F03_main_figure3.R] Vcells 2518880 19.3    8388608  64.0  4311848  32.9
[F03_main_figure3.R] null device 
[F03_main_figure3.R]           1 
[F03_main_figure3.R] Error in loadNamespace(x) : there is no package called ‘magick’
[F03_main_figure3.R] Calls: loadNamespace -> withRestarts -> withOneRestart -> doWithOneRestart
[F03_main_figure3.R] Execution halted
  ✗ FAIL  F03_main_figure3.R                             (  7.7s)  Exit code: 1
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
[S01_drivers.R] Warning messages:
[S01_drivers.R] 1: In strheight(title, cex = title.cex, font = title.font, units = "user") :
[S01_drivers.R]   font metrics unknown for character 0xa
[S01_drivers.R] 2: In strwidth(title, units = "user", cex = title.cex, font = title.font) :
[S01_drivers.R]   font metrics unknown for character 0xa
[S01_drivers.R] 3: In text.default(x, y, ...) : font metrics unknown for character 0xa
[S01_drivers.R] 4: In text.default(x, y, ...) : font metrics unknown for character 0xa
[S01_drivers.R] null device 
[S01_drivers.R]           1 
  ✓ PASS  S01_drivers.R                                  (  1.4s)  
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
[S02_cropland_uncertainty.R] Ncells 1787601 95.5    2818547 150.6  2818547 150.6
[S02_cropland_uncertainty.R] Vcells 2518793 19.3    8388608  64.0  4311848  32.9
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
[S02_cropland_uncertainty.R] Error in if (comp$labels_select[k]) { : 
[S02_cropland_uncertainty.R]   missing value where TRUE/FALSE needed
[S02_cropland_uncertainty.R] Calls: <Anonymous> ... tmapGridCompHeight -> tmapGridCompHeight.tm_legend_portrait
[S02_cropland_uncertainty.R] Execution halted
  ✗ FAIL  S02_cropland_uncertainty.R                     (  9.7s)  Exit code: 1
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
[S03_aggregate_vs_disaggregate.R] Ncells 1788244 95.6    2818547 150.6  2818547 150.6
[S03_aggregate_vs_disaggregate.R] Vcells 2519880 19.3    8388608  64.0  4311848  32.9
[S03_aggregate_vs_disaggregate.R] Error in loadNamespace(x) : there is no package called ‘magick’
[S03_aggregate_vs_disaggregate.R] Calls: loadNamespace -> withRestarts -> withOneRestart -> doWithOneRestart
[S03_aggregate_vs_disaggregate.R] Execution halted
  ✗ FAIL  S03_aggregate_vs_disaggregate.R                ( 23.0s)  Exit code: 1
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
[S04_RF_hyperparameters.R] Ncells 1788244 95.6    2818547 150.6  2818547 150.6
[S04_RF_hyperparameters.R] Vcells 2519880 19.3    8388608  64.0  4311848  32.9
[S04_RF_hyperparameters.R] Error in `filter()`:
[S04_RF_hyperparameters.R] ℹ In argument: ``%in%`(...)`.
[S04_RF_hyperparameters.R] Caused by error:
[S04_RF_hyperparameters.R] ! object 'gadm_0' not found
[S04_RF_hyperparameters.R] Backtrace:
[S04_RF_hyperparameters.R]      ▆
[S04_RF_hyperparameters.R]   1. ├─dplyr::bind_rows(...)
[S04_RF_hyperparameters.R]   2. │ └─rlang::list2(...)
[S04_RF_hyperparameters.R]   3. ├─dplyr::reframe(...)
[S04_RF_hyperparameters.R]   4. ├─dplyr::reframe(...)
[S04_RF_hyperparameters.R]   5. ├─dplyr::group_by(...)
[S04_RF_hyperparameters.R]   6. ├─dplyr::filter(...)
[S04_RF_hyperparameters.R]   7. ├─dplyr:::filter.data.frame(...)
[S04_RF_hyperparameters.R]   8. │ └─dplyr:::filter_impl(...)
[S04_RF_hyperparameters.R]   9. │   └─dplyr:::filter_rows(...)
[S04_RF_hyperparameters.R]  10. │     └─dplyr:::filter_eval(...)
[S04_RF_hyperparameters.R]  11. │       ├─base::withCallingHandlers(...)
[S04_RF_hyperparameters.R]  12. │       └─mask$eval_all_filter(dots_expanded, invert, env_filter)
[S04_RF_hyperparameters.R]  13. │         └─dplyr (local) eval()
[S04_RF_hyperparameters.R]  14. ├─paste0(country, ".", gadm_0) %in% ...
[S04_RF_hyperparameters.R]  15. ├─base::paste0(country, ".", gadm_0)
[S04_RF_hyperparameters.R]  16. └─base::.handleSimpleError(...)
[S04_RF_hyperparameters.R]  17.   └─dplyr (local) h(simpleError(msg, call))
[S04_RF_hyperparameters.R]  18.     └─rlang::abort(message, class = error_class, parent = parent, call = error_call)
[S04_RF_hyperparameters.R] Execution halted
  ✗ FAIL  S04_RF_hyperparameters.R                       (  8.0s)  Exit code: 1
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
[S05_RF_unseen_performance.R] 1: Removed 13 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_ribbon()`). 
[S05_RF_unseen_performance.R] 2: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_line()`). 
[S05_RF_unseen_performance.R] 3: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_point()`). 
[S05_RF_unseen_performance.R] 4: Removed 13 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_ribbon()`). 
[S05_RF_unseen_performance.R] 5: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_line()`). 
[S05_RF_unseen_performance.R] 6: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_point()`). 
[S05_RF_unseen_performance.R] Warning messages:
[S05_RF_unseen_performance.R] 1: Removed 13 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_ribbon()`). 
[S05_RF_unseen_performance.R] 2: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_line()`). 
[S05_RF_unseen_performance.R] 3: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_point()`). 
[S05_RF_unseen_performance.R] 4: Removed 13 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_ribbon()`). 
[S05_RF_unseen_performance.R] 5: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_line()`). 
[S05_RF_unseen_performance.R] 6: Removed 2 rows containing missing values or values outside the scale range
[S05_RF_unseen_performance.R] (`geom_point()`). 
  ✓ PASS  S05_RF_unseen_performance.R                    (  5.3s)  
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
[S06_size_class_comparison.R] Ncells 1788244 95.6    2818547 150.6  2818547 150.6
[S06_size_class_comparison.R] Vcells 2519880 19.3    8388608  64.0  4311848  32.9
[S06_size_class_comparison.R] Joining with `by = join_by(train_country)`
[S06_size_class_comparison.R] Joining with `by = join_by(test_country)`
  ✓ PASS  S06_size_class_comparison.R                    (  5.5s)  
[S07_distribution_parameters.R] Warning message:
[S07_distribution_parameters.R] In geom_text(data = inner_join(div_table, distinct(select(comp_fsize_classes_nb,  :
[S07_distribution_parameters.R]   Ignoring unknown parameters: `inherits.aes`
[S07_distribution_parameters.R] Warning message:
[S07_distribution_parameters.R] `position_dodge()` requires non-overlapping x intervals. 
[S07_distribution_parameters.R] Joining with `by = join_by(NAME_0, GID_0)`
[S07_distribution_parameters.R] Joining with `by = join_by(NAME_0, GID_0)`
[S07_distribution_parameters.R] Warning message:
[S07_distribution_parameters.R] In geom_text(data = inner_join(div_table, distinct(select(comp_fsize_classes_ha,  :
[S07_distribution_parameters.R]   Ignoring unknown parameters: `inherits.aes`
[S07_distribution_parameters.R] Error in `geom_text()`:
[S07_distribution_parameters.R] ! Problem while computing aesthetics.
[S07_distribution_parameters.R] ℹ Error occurred in the 3rd layer.
[S07_distribution_parameters.R] Caused by error:
[S07_distribution_parameters.R] ! object 'divergence_ha' not found
[S07_distribution_parameters.R] Backtrace:
[S07_distribution_parameters.R]      ▆
[S07_distribution_parameters.R]   1. ├─base (local) `<fn>`(x)
[S07_distribution_parameters.R]   2. ├─ggplot2 (local) `print.ggplot2::ggplot`(x)
[S07_distribution_parameters.R]   3. │ ├─ggplot2::ggplot_build(x)
[S07_distribution_parameters.R]   4. │ └─ggplot2 (local) `ggplot_build.ggplot2::ggplot`(x)
[S07_distribution_parameters.R]   5. │   └─ggplot2:::by_layer(...)
[S07_distribution_parameters.R]   6. │     ├─rlang::try_fetch(...)
[S07_distribution_parameters.R]   7. │     │ ├─base::tryCatch(...)
[S07_distribution_parameters.R]   8. │     │ │ └─base (local) tryCatchList(expr, classes, parentenv, handlers)
[S07_distribution_parameters.R]   9. │     │ │   └─base (local) tryCatchOne(expr, names, parentenv, handlers[[1L]])
[S07_distribution_parameters.R]  10. │     │ │     └─base (local) doTryCatch(return(expr), name, parentenv, handler)
[S07_distribution_parameters.R]  11. │     │ └─base::withCallingHandlers(...)
[S07_distribution_parameters.R]  12. │     └─ggplot2 (local) f(l = layers[[i]], d = data[[i]])
[S07_distribution_parameters.R]  13. │       └─l$compute_aesthetics(d, plot)
[S07_distribution_parameters.R]  14. │         └─ggplot2 (local) compute_aesthetics(..., self = self)
[S07_distribution_parameters.R]  15. │           └─ggplot2:::eval_aesthetics(aesthetics, data)
[S07_distribution_parameters.R]  16. │             └─base::lapply(aesthetics, eval_tidy, data = data, env = env)
[S07_distribution_parameters.R]  17. │               └─rlang (local) FUN(X[[i]], ...)
[S07_distribution_parameters.R]  18. └─base::.handleSimpleError(...)
[S07_distribution_parameters.R]  19.   └─rlang (local) h(simpleError(msg, call))
[S07_distribution_parameters.R]  20.     └─handlers[[1L]](cnd)
[S07_distribution_parameters.R]  21.       └─cli::cli_abort(...)
[S07_distribution_parameters.R]  22.         └─rlang::abort(...)
[S07_distribution_parameters.R] Execution halted
  ✗ FAIL  S07_distribution_parameters.R                  (  4.7s)  Exit code: 1
[S08_variable_importance.R] Loading required package: tidyverse
[S08_variable_importance.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[S08_variable_importance.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
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
[S08_variable_importance.R] Ncells 1787604 95.5    2818547 150.6  2818547 150.6
[S08_variable_importance.R] Vcells 2518794 19.3    8388608  64.0  4311848  32.9
[S08_variable_importance.R] Error in (function (classes, fdef, mtable)  : 
[S08_variable_importance.R]   unable to find an inherited method for function ‘crs’ for signature ‘"grouped_df"’
[S08_variable_importance.R] Calls: <Anonymous> -> <Anonymous>
[S08_variable_importance.R] Execution halted
  ✗ FAIL  S08_variable_importance.R                      (  4.3s)  Exit code: 1
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
[T01_area_production_tables.R] Loading required package: patchwork
[T01_area_production_tables.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[T01_area_production_tables.R] Ncells 1787589 95.5    2818547 150.6  2818547 150.6
[T01_area_production_tables.R] Vcells 2518880 19.3    8388608  64.0  4311848  32.9
[T01_area_production_tables.R] Joining with `by = join_by(country)`
  ✓ PASS  T01_area_production_tables.R                   (  5.3s)  
[T02_heterogeneity_drivers.R] Loading required package: tidyverse
[T02_heterogeneity_drivers.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[T02_heterogeneity_drivers.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[T02_heterogeneity_drivers.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[T02_heterogeneity_drivers.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[T02_heterogeneity_drivers.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[T02_heterogeneity_drivers.R] ✔ purrr     1.2.1     
[T02_heterogeneity_drivers.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[T02_heterogeneity_drivers.R] ✖ dplyr::filter() masks stats::filter()
[T02_heterogeneity_drivers.R] ✖ dplyr::lag()    masks stats::lag()
[T02_heterogeneity_drivers.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[T02_heterogeneity_drivers.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[T02_heterogeneity_drivers.R] Ncells 1793427 95.8    2846530 152.1  2846530 152.1
[T02_heterogeneity_drivers.R] Vcells 3044110 23.3    8388608  64.0  5061307  38.7
[T02_heterogeneity_drivers.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[T02_heterogeneity_drivers.R] Ncells 1806954 96.6    2846530 152.1  2846530 152.1
[T02_heterogeneity_drivers.R] Vcells 3185459 24.4    8388608  64.0  5061307  38.7
[T02_heterogeneity_drivers.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[T02_heterogeneity_drivers.R] Ncells 1826262 97.6    2846530 152.1  2846530 152.1
[T02_heterogeneity_drivers.R] Vcells 3512266 26.8    8388608  64.0  6296443  48.1
[T02_heterogeneity_drivers.R] Error: [rast] cannot open this file as a SpatRaster: /home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/data/raw/spatial/spam/spam2017
[T02_heterogeneity_drivers.R] In addition: Warning message:
[T02_heterogeneity_drivers.R] `/home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/data/raw/spatial/spam/spam2017' not recognized as a supported file format. (GDAL error 4) 
[T02_heterogeneity_drivers.R] Execution halted
  ✗ FAIL  T02_heterogeneity_drivers.R                    ( 13.3s)  Exit code: 1

======================================================================
TEST SUMMARY
======================================================================

  Stat   Script                                          Time(s)  Note
  ------------------------------------------------------------------------
  ✓ PASS  00_synthetic_data                                 6.6    
  ✓ PASS  00_install_packages.R                             0.0    SKIPPED (download/SLURM/data-only script)
  ✓ PASS  00_download_spatial_data.R                        0.0    SKIPPED (download/SLURM/data-only script)
  ✓ PASS  01.2_chirps_summarize.R                           0.0    SKIPPED (download/SLURM/data-only script)
  ✓ PASS  02.1_compile_LSMS.R                               0.0    SKIPPED (download/SLURM/data-only script)
  ✓ PASS  05.2_RF_optimization_summary.R                    0.0    SKIPPED (download/SLURM/data-only script)
  ✓ PASS  01.1_chirps_download.R                            1.9    
  ✓ PASS  01.3_chirps_trends.R                              3.8    
  ✓ PASS  01.4_prepare_spatial_layers.R                     3.2    
  ✓ PASS  02.2_harmonize_farm_area.R                        3.8    
  ✓ PASS  02.3_measured_vs_reported.R                       2.1    
  ✓ PASS  03.1_pooled_data.R                                1.2    
  ✗ FAIL  03.2_correlation_drivers.R                       21.9    Exit code: 1
  ✓ PASS  03.3_descriptive_stats.R                         18.6    
  ✓ PASS  04.1_comparing_ML_algorithms.R                    1.3    
  ✗ FAIL  04.2_RF_within_country.R                         47.1    Exit code: 1
  ✗ FAIL  04.3_RF_between_countries.R                       5.2    Exit code: 1
  ✗ FAIL  04.4_RF_model_evaluation.R                      604.5    Exit code: 124
  ✗ FAIL  04.5_cross_country_graphs.R                       0.2    Exit code: 1
  ✓ PASS  04.6_discrepancy_analysis.R                      14.9    
  ✓ PASS  05.1_RF_optimization.R                            3.9    
  ✓ PASS  05.3_RF_robustness.R                              0.2    
  ✓ PASS  06.1_quantile_RF.R                                3.3    
  ✗ FAIL  06.3_prediction_maps.R                          128.8    Exit code: 1
  ✗ FAIL  06.4_cropland_sensitivity.R                       7.7    Exit code: 1
  ✓ PASS  07.2_QRF_distribution_eval.R                     18.0    
  ✗ FAIL  08.1_predictions_by_country.R                   600.0    Exit code: 124
  ✗ FAIL  08.2_generate_virtual_farms.R                     7.4    Exit code: 1
  ✗ FAIL  08.3_farm_size_classes.R                          6.9    Exit code: 1
  ✗ FAIL  09.1_AEZ_characterization.R                       4.0    Exit code: 1
  ✗ FAIL  10.1_prepare_validation_data.R                    4.4    Exit code: 1
  ✗ FAIL  10.2_external_validation.R                        4.0    Exit code: 1
  ✗ FAIL  F01_main_figure1.R                                3.9    Exit code: 1
  ✗ FAIL  F02_main_figure2.R                                4.1    Exit code: 1
  ✗ FAIL  F03_main_figure3.R                                7.7    Exit code: 1
  ✓ PASS  S01_drivers.R                                     1.4    
  ✗ FAIL  S02_cropland_uncertainty.R                        9.7    Exit code: 1
  ✗ FAIL  S03_aggregate_vs_disaggregate.R                  23.0    Exit code: 1
  ✗ FAIL  S04_RF_hyperparameters.R                          8.0    Exit code: 1
  ✓ PASS  S05_RF_unseen_performance.R                       5.3    
  ✓ PASS  S06_size_class_comparison.R                       5.5    
  ✗ FAIL  S07_distribution_parameters.R                     4.7    Exit code: 1
  ✗ FAIL  S08_variable_importance.R                         4.3    Exit code: 1
  ✓ PASS  T01_area_production_tables.R                      5.3    
  ✗ FAIL  T02_heterogeneity_drivers.R                      13.3    Exit code: 1

======================================================================
Total: 45   Passed: 23   Failed: 22   Time: 1621s

Report: ../output/reports/full_pipeline_test_report.md

❌ CORE PIPELINE FAILING (9/22 core scripts passed)
```

## Pipeline Report
# Farm Size Prediction — Full Pipeline CI Report

**Generated:** 2026-03-16 12:52:02 UTC
**R Version:** R version 4.3.3 (2024-02-29)

## Summary

| Metric | Value |
|--------|-------|
| Total Scripts  | 45 |
| Passed         | 23 |
| Failed         | 22 |
| Total Time     | 1621.4s |

## Per-Script Results

| Phase | Script | Status | Time | Note |
|-------|--------|--------|------|------|
| 00 | `00_synthetic_data` | ✅ PASS | 6.6s |  |
| 00 | `00_install_packages.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/data-only script) |
| 00 | `00_download_spatial_data.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/data-only script) |
| 01.2 | `01.2_chirps_summarize.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/data-only script) |
| 02.1 | `02.1_compile_LSMS.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/data-only script) |
| 05.2 | `05.2_RF_optimization_summary.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/data-only script) |
| 01.1 | `01.1_chirps_download.R` | ✅ PASS | 1.9s |  |
| 01.3 | `01.3_chirps_trends.R` | ✅ PASS | 3.8s |  |
| 01.4 | `01.4_prepare_spatial_layers.R` | ✅ PASS | 3.2s |  |
| 02.2 | `02.2_harmonize_farm_area.R` | ✅ PASS | 3.8s |  |
| 02.3 | `02.3_measured_vs_reported.R` | ✅ PASS | 2.1s |  |
| 03.1 | `03.1_pooled_data.R` | ✅ PASS | 1.2s |  |
| 03.2 | `03.2_correlation_drivers.R` | ❌ FAIL | 21.9s | Exit code: 1 |
| 03.3 | `03.3_descriptive_stats.R` | ✅ PASS | 18.6s |  |
| 04.1 | `04.1_comparing_ML_algorithms.R` | ✅ PASS | 1.3s |  |
| 04.2 | `04.2_RF_within_country.R` | ❌ FAIL | 47.1s | Exit code: 1 |
| 04.3 | `04.3_RF_between_countries.R` | ❌ FAIL | 5.2s | Exit code: 1 |
| 04.4 | `04.4_RF_model_evaluation.R` | ❌ FAIL | 604.5s | Exit code: 124 |
| 04.5 | `04.5_cross_country_graphs.R` | ❌ FAIL | 0.2s | Exit code: 1 |
| 04.6 | `04.6_discrepancy_analysis.R` | ✅ PASS | 14.9s |  |
| 05.1 | `05.1_RF_optimization.R` | ✅ PASS | 3.9s |  |
| 05.3 | `05.3_RF_robustness.R` | ✅ PASS | 0.2s |  |
| 06.1 | `06.1_quantile_RF.R` | ✅ PASS | 3.3s |  |
| 06.3 | `06.3_prediction_maps.R` | ❌ FAIL | 128.8s | Exit code: 1 |
| 06.4 | `06.4_cropland_sensitivity.R` | ❌ FAIL | 7.7s | Exit code: 1 |
| 07.2 | `07.2_QRF_distribution_eval.R` | ✅ PASS | 18s |  |
| 08.1 | `08.1_predictions_by_country.R` | ❌ FAIL | 600s | Exit code: 124 |
| 08.2 | `08.2_generate_virtual_farms.R` | ❌ FAIL | 7.4s | Exit code: 1 |
| 08.3 | `08.3_farm_size_classes.R` | ❌ FAIL | 6.9s | Exit code: 1 |
| 09.1 | `09.1_AEZ_characterization.R` | ❌ FAIL | 4s | Exit code: 1 |
| 10.1 | `10.1_prepare_validation_data.R` | ❌ FAIL | 4.4s | Exit code: 1 |
| 10.2 | `10.2_external_validation.R` | ❌ FAIL | 4s | Exit code: 1 |
| F01 | `F01_main_figure1.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| F02 | `F02_main_figure2.R` | ❌ FAIL | 4.1s | Exit code: 1 |
| F03 | `F03_main_figure3.R` | ❌ FAIL | 7.7s | Exit code: 1 |
| S01 | `S01_drivers.R` | ✅ PASS | 1.4s |  |
| S02 | `S02_cropland_uncertainty.R` | ❌ FAIL | 9.7s | Exit code: 1 |
| S03 | `S03_aggregate_vs_disaggregate.R` | ❌ FAIL | 23s | Exit code: 1 |
| S04 | `S04_RF_hyperparameters.R` | ❌ FAIL | 8s | Exit code: 1 |
| S05 | `S05_RF_unseen_performance.R` | ✅ PASS | 5.3s |  |
| S06 | `S06_size_class_comparison.R` | ✅ PASS | 5.5s |  |
| S07 | `S07_distribution_parameters.R` | ❌ FAIL | 4.7s | Exit code: 1 |
| S08 | `S08_variable_importance.R` | ❌ FAIL | 4.3s | Exit code: 1 |
| T01 | `T01_area_production_tables.R` | ✅ PASS | 5.3s |  |
| T02 | `T02_heterogeneity_drivers.R` | ❌ FAIL | 13.3s | Exit code: 1 |
