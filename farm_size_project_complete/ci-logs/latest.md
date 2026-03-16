# CI Run Log
Run: 23148390870  Commit: 8345414f595ddf52be1d8749616bb726d4a1d9fe  Time: Mon Mar 16 14:39:57 UTC 2026

## Raw Output
```

======================================================================
FARM SIZE PREDICTION - FULL SEQUENTIAL PIPELINE TEST
======================================================================
Started: 2026-03-16 14:22:15.807264

Scripts dir: /home/runner/work/quick_test_farm_size_claude/quick_test_farm_size_claude/farm_size_project_complete/scripts

----------------------------------------------------------------------
PHASE 0: Synthetic Data Generation
----------------------------------------------------------------------
[00_synthetic_data.R] terra 1.8.93
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
[00_synthetic_data.R]   Farms generated:   7001
[00_synthetic_data.R]   After 95th trim:   4132
[00_synthetic_data.R]   Countries:         16
[00_synthetic_data.R]   Raster layers:     11
[00_synthetic_data.R]   Training res:      0.5° (~56 km) — 14000 cells/layer
[00_synthetic_data.R]   Prediction res:    5° (~555 km) — 140 cells/layer (~3-9 per country)
[00_synthetic_data.R]   QRF stack cells:   140 cells × 100 quantiles = 14000 values
[00_synthetic_data.R]   Prediction stubs:  6 Python + RF + QRF rasters
[00_synthetic_data.R]   Output stubs:      15
[00_synthetic_data.R]   Processed files:   139
  ✓ PASS  00_synthetic_data                              (  7.2s)  
----------------------------------------------------------------------
PHASE 1: Install/Download Scripts (skipped in CI)
----------------------------------------------------------------------
  ✓ PASS  00_install_packages.R                          (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  00_download_spatial_data.R                     (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  01.2_chirps_summarize.R                        (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  02.1_compile_LSMS.R                            (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  05.2_RF_optimization_summary.R                 (  0.0s)  SKIPPED (download/SLURM/timeout script)
  ✓ PASS  08.1_predictions_by_country.R                  (  0.0s)  SKIPPED (download/SLURM/timeout script)
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
[01.1_chirps_download.R] Finished: 2026-03-16 14:22:25.048072
[01.1_chirps_download.R] ======================================================================
  ✓ PASS  01.1_chirps_download.R                         (  1.8s)  
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
  ✓ PASS  01.3_chirps_trends.R                           (  4.2s)  
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
  ✓ PASS  02.2_harmonize_farm_area.R                     (  3.9s)  
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
  ✗ FAIL  03.2_correlation_drivers.R                     ( 32.5s)  Exit code: 1
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
  ✓ PASS  03.3_descriptive_stats.R                       ( 19.0s)  
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
[04.2_RF_within_country.R] Time difference of 42.36772 secs
[04.2_RF_within_country.R] Error: object 'results_Benin' not found
[04.2_RF_within_country.R] Execution halted
  ✗ FAIL  04.2_RF_within_country.R                       ( 46.3s)  Exit code: 1
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
[04.3_RF_between_countries.R] Time difference of 1.17379 secs
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
  ✗ FAIL  04.3_RF_between_countries.R                    (  5.0s)  Exit code: 1
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
[04.4_RF_model_evaluation.R]    country tps1_test_rsq rf1_cv_rsq rf1_cv_rsq_sd rf1_oob_rsq rf1_test_rsq
[04.4_RF_model_evaluation.R] 1 Tanzania          0.08       0.01             0       -0.15         0.15
[04.4_RF_model_evaluation.R]   rf3_test_rsq cor_tps1_rf3 cor_rf1_rf3 tps2_test_rsq rf2_cv_rsq rf2_cv_rsq_sd
[04.4_RF_model_evaluation.R] 1            0            0           0          0.08       0.01             0
[04.4_RF_model_evaluation.R]   rf2_oob_rsq rf2_test_rsq rf4_test_rsq cor_tps2_rf4 cor_rf2_rf4
[04.4_RF_model_evaluation.R] 1       -0.15         0.15            0            0           0
[04.4_RF_model_evaluation.R] [1] "--------------------Togo---------------------------"
[04.4_RF_model_evaluation.R] 
[04.4_RF_model_evaluation.R]   country tps1_test_rsq rf1_cv_rsq rf1_cv_rsq_sd rf1_oob_rsq rf1_test_rsq
[04.4_RF_model_evaluation.R] 1    Togo          0.16       0.01             0        0.02         0.28
[04.4_RF_model_evaluation.R]   rf3_test_rsq cor_tps1_rf3 cor_rf1_rf3 tps2_test_rsq rf2_cv_rsq rf2_cv_rsq_sd
[04.4_RF_model_evaluation.R] 1         0.01            0           0          0.16       0.02             0
[04.4_RF_model_evaluation.R]   rf2_oob_rsq rf2_test_rsq rf4_test_rsq cor_tps2_rf4 cor_rf2_rf4
[04.4_RF_model_evaluation.R] 1        0.01         0.29         0.02            0           0
[04.4_RF_model_evaluation.R] [1] "--------------------Uganda---------------------------"
[04.4_RF_model_evaluation.R] Warning: 
[04.4_RF_model_evaluation.R] Grid searches over lambda (nugget and sill variances) with  minima at the endpoints: 
[04.4_RF_model_evaluation.R]   (GCV) Generalized Cross-Validation 
[04.4_RF_model_evaluation.R]    minimum at  right endpoint  lambda  =  2178174 (eff. df= 13.00105 )
[04.4_RF_model_evaluation.R] Warning: 
[04.4_RF_model_evaluation.R] Grid searches over lambda (nugget and sill variances) with  minima at the endpoints: 
[04.4_RF_model_evaluation.R]   (GCV) Generalized Cross-Validation 
[04.4_RF_model_evaluation.R]    minimum at  right endpoint  lambda  =  2178174 (eff. df= 13.00105 )
  ✗ FAIL  04.4_RF_model_evaluation.R                     (620.0s)  Exit code: 124
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
  ✓ PASS  04.6_discrepancy_analysis.R                    ( 14.7s)  
Warning message:
In system2("Rscript", c("--vanilla", shQuote(tmp)), stdout = log_file,  :
  command ''Rscript' --vanilla '/tmp/RtmpyWioBj/file1a915b322051.R' > '/tmp/RtmpyWioBj/file1a919556c72.log' 2>&1' timed out after 600s
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
[06.3_prediction_maps.R] Loading required package: lattice
[06.3_prediction_maps.R] 
[06.3_prediction_maps.R] Attaching package: ‘caret’
[06.3_prediction_maps.R] 
[06.3_prediction_maps.R] The following object is masked from ‘package:purrr’:
[06.3_prediction_maps.R] 
[06.3_prediction_maps.R]     lift
[06.3_prediction_maps.R] 
[06.3_prediction_maps.R] Time difference of 16.6402 secs
[06.3_prediction_maps.R] Error: Every row has at least one missing value were found
[06.3_prediction_maps.R] Execution halted
  ✗ FAIL  06.3_prediction_maps.R                         (125.6s)  Exit code: 1
[06.4_cropland_sensitivity.R] min value   : 0.2342716 
[06.4_cropland_sensitivity.R] max value   : 4.2276978 
[06.4_cropland_sensitivity.R]     rf_mean      
[06.4_cropland_sensitivity.R]  Min.   :0.2343  
[06.4_cropland_sensitivity.R]  1st Qu.:1.6109  
[06.4_cropland_sensitivity.R]  Median :2.2103  
[06.4_cropland_sensitivity.R]  Mean   :2.1768  
[06.4_cropland_sensitivity.R]  3rd Qu.:2.6382  
[06.4_cropland_sensitivity.R]  Max.   :4.2277  
[06.4_cropland_sensitivity.R] null device 
[06.4_cropland_sensitivity.R]           1 
[06.4_cropland_sensitivity.R] null device 
[06.4_cropland_sensitivity.R]           1 
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] Removed 3665 rows containing non-finite outside the scale range
[06.4_cropland_sensitivity.R] (`stat_density2d_filled()`). 
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] Removed 3665 rows containing non-finite outside the scale range
[06.4_cropland_sensitivity.R] (`stat_density2d_filled()`). 
[06.4_cropland_sensitivity.R] Saving 7.5 x 5 in image
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] Removed 3665 rows containing non-finite outside the scale range
[06.4_cropland_sensitivity.R] (`stat_density2d_filled()`). 
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
[06.4_cropland_sensitivity.R] Saving 7.5 x 5 in image
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] In e1@pntr$arith_rast(e2@pntr, oper, FALSE, opt) :
[06.4_cropland_sensitivity.R]   GDAL Message 1: /tmp/Rtmptx9q5I/spat_11f1466a23d68_73492_Py3ptIw2UFUXKtt.tif: Metadata exceeding 32000 bytes cannot be written into GeoTIFF. Transferred to PAM instead.
[06.4_cropland_sensitivity.R] Warning message:
[06.4_cropland_sensitivity.R] In e1@pntr$arith_rast(e2@pntr, oper, FALSE, opt) :
[06.4_cropland_sensitivity.R]   GDAL Message 1: /tmp/Rtmptx9q5I/spat_11f14619aa162_73492_8UwxxeZk3QEYL3o.tif: Metadata exceeding 32000 bytes cannot be written into GeoTIFF. Transferred to PAM instead.
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
[06.4_cropland_sensitivity.R] pdf 
[06.4_cropland_sensitivity.R]   2 
  ✓ PASS  06.4_cropland_sensitivity.R                    ( 14.4s)  
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
  ✓ PASS  07.2_QRF_distribution_eval.R                   ( 17.8s)  
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
  ✗ FAIL  08.2_generate_virtual_farms.R                  (  7.3s)  Exit code: 1
[08.3_farm_size_classes.R] Loading required package: tidyverse
[08.3_farm_size_classes.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[08.3_farm_size_classes.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[08.3_farm_size_classes.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[08.3_farm_size_classes.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[08.3_farm_size_classes.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[08.3_farm_size_classes.R] ✔ purrr     1.2.1     
[08.3_farm_size_classes.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[08.3_farm_size_classes.R] ✖ dplyr::filter() masks stats::filter()
[08.3_farm_size_classes.R] ✖ dplyr::lag()    masks stats::lag()
[08.3_farm_size_classes.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[08.3_farm_size_classes.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[08.3_farm_size_classes.R] Ncells 1780224 95.1    2846527 152.1  2846527 152.1
[08.3_farm_size_classes.R] Vcells 2494331 19.1    8388608  64.0  4243638  32.4
[08.3_farm_size_classes.R] `summarise()` has regrouped the output.
[08.3_farm_size_classes.R] ℹ Summaries were computed grouped by cell and country.
[08.3_farm_size_classes.R] ℹ Output is grouped by cell.
[08.3_farm_size_classes.R] ℹ Use `summarise(.groups = "drop_last")` to silence this message.
[08.3_farm_size_classes.R] ℹ Use `summarise(.by = c(cell, country))` for per-operation grouping
[08.3_farm_size_classes.R]   (`?dplyr::dplyr_by`) instead.
[08.3_farm_size_classes.R] Error: unexpected end of input
[08.3_farm_size_classes.R] Execution halted
  ✗ FAIL  08.3_farm_size_classes.R                       (  4.7s)  Exit code: 1
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
[09.1_AEZ_characterization.R] Warning message:
[09.1_AEZ_characterization.R] The `value` argument of `names<-()` must have the same length as `x` as of
[09.1_AEZ_characterization.R] tibble 3.0.0. 
[09.1_AEZ_characterization.R] Error in `mutate()`:
[09.1_AEZ_characterization.R] ℹ In argument: `NAME_0 = rep(country_list, each = 2)`.
[09.1_AEZ_characterization.R] Caused by error:
[09.1_AEZ_characterization.R] ! `NAME_0` must be size 4 or 1, not 8.
[09.1_AEZ_characterization.R] Backtrace:
[09.1_AEZ_characterization.R]      ▆
[09.1_AEZ_characterization.R]   1. ├─dplyr::mutate(...)
[09.1_AEZ_characterization.R]   2. ├─dplyr:::mutate.data.frame(...)
[09.1_AEZ_characterization.R]   3. │ └─dplyr:::mutate_cols(.data, dplyr_quosures(...), by)
[09.1_AEZ_characterization.R]   4. │   ├─base::withCallingHandlers(...)
[09.1_AEZ_characterization.R]   5. │   └─dplyr:::mutate_col(dots[[i]], data, mask, new_columns)
[09.1_AEZ_characterization.R]   6. │     └─mask$eval_all_mutate(quo)
[09.1_AEZ_characterization.R]   7. │       └─dplyr (local) eval()
[09.1_AEZ_characterization.R]   8. ├─dplyr:::dplyr_internal_error(...)
[09.1_AEZ_characterization.R]   9. │ └─rlang::abort(class = c(class, "dplyr:::internal_error"), dplyr_error_data = data)
[09.1_AEZ_characterization.R]  10. │   └─rlang:::signal_abort(cnd, .file)
[09.1_AEZ_characterization.R]  11. │     └─base::signalCondition(cnd)
[09.1_AEZ_characterization.R]  12. └─dplyr (local) `<fn>`(`<dpl:::__>`)
[09.1_AEZ_characterization.R]  13.   └─rlang::abort(message, class = error_class, parent = parent, call = error_call)
[09.1_AEZ_characterization.R] Execution halted
  ✗ FAIL  09.1_AEZ_characterization.R                    (  4.0s)  Exit code: 1
[10.1_prepare_validation_data.R] ✖ dplyr::filter() masks stats::filter()
[10.1_prepare_validation_data.R] ✖ dplyr::lag()    masks stats::lag()
[10.1_prepare_validation_data.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[10.1_prepare_validation_data.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[10.1_prepare_validation_data.R] Ncells 1781317 95.2    2846527 152.1  2846527 152.1
[10.1_prepare_validation_data.R] Vcells 2496402 19.1    8388608  64.0  4243638  32.4
[10.1_prepare_validation_data.R]    Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
[10.1_prepare_validation_data.R]  0.1399  0.8893  1.3519  1.6226  2.0465 11.9871 
[10.1_prepare_validation_data.R] NULL
[10.1_prepare_validation_data.R] # A tibble: 6 × 7
[10.1_prepare_validation_data.R]   aez                  avg   med   std  gini tot_cropland    nb
[10.1_prepare_validation_data.R]   <fct>              <dbl> <dbl> <dbl> <dbl>        <dbl> <int>
[10.1_prepare_validation_data.R] 1 humid               1.60  1.33  1.00 0.326         895.   560
[10.1_prepare_validation_data.R] 2 sub-humid           1.61  1.39  1.02 0.317         318.   198
[10.1_prepare_validation_data.R] 3 semi-arid           1.64  1.38  1.05 0.323        1702.  1039
[10.1_prepare_validation_data.R] 4 arid                1.61  1.33  1.09 0.340        1932.  1197
[10.1_prepare_validation_data.R] 5 tropical highlands  1.62  1.33  1.12 0.342        1174.   723
[10.1_prepare_validation_data.R] 6 sub-tropical        1.65  1.33  1.09 0.332         683.   415
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez, avg, med, std, gini, tot_cropland, nb)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez, avg, med, std, gini, tot_cropland, nb)`
[10.1_prepare_validation_data.R] Joining with `by = join_by(aez, avg, med, std, gini, tot_cropland, nb)`
[10.1_prepare_validation_data.R] Warning message:
[10.1_prepare_validation_data.R] There was 1 warning in `summarize()`.
[10.1_prepare_validation_data.R] ℹ In argument: `across(everything(), sum, na.rm = T)`.
[10.1_prepare_validation_data.R] Caused by warning:
[10.1_prepare_validation_data.R] ! The `...` argument of `across()` is deprecated as of dplyr 1.1.0.
[10.1_prepare_validation_data.R] Supply arguments directly to `.fns` through an anonymous function instead.
[10.1_prepare_validation_data.R] 
[10.1_prepare_validation_data.R]   # Previously
[10.1_prepare_validation_data.R]   across(a:b, mean, na.rm = TRUE)
[10.1_prepare_validation_data.R] 
[10.1_prepare_validation_data.R]   # Now
[10.1_prepare_validation_data.R]   across(a:b, \(x) mean(x, na.rm = TRUE)) 
[10.1_prepare_validation_data.R]      V6      V7      V1      V8      V5      V4      V2      V3 
[10.1_prepare_validation_data.R] 3789941 3768295 3758403 3755362 3745381 3740470 3727003 3723915 
[10.1_prepare_validation_data.R] Error: [subset] invalid name(s)
[10.1_prepare_validation_data.R] Execution halted
  ✗ FAIL  10.1_prepare_validation_data.R                 (  4.4s)  Exit code: 1
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
[10.2_external_validation.R] CI-SKIP GADM:Angola
[10.2_external_validation.R] [1] "------------ Burundi---------------"
[10.2_external_validation.R] CI-SKIP GADM:Burundi
[10.2_external_validation.R] [1] "------------ Benin---------------"
[10.2_external_validation.R] `summarise()` has regrouped the output.
[10.2_external_validation.R] ℹ Summaries were computed grouped by GID_1 and NAME_1.
[10.2_external_validation.R] ℹ Output is grouped by GID_1.
[10.2_external_validation.R] ℹ Use `summarise(.groups = "drop_last")` to silence this message.
[10.2_external_validation.R] ℹ Use `summarise(.by = c(GID_1, NAME_1))` for per-operation grouping
[10.2_external_validation.R]   (`?dplyr::dplyr_by`) instead.
[10.2_external_validation.R] Joining with `by = join_by(GID_1)`
[10.2_external_validation.R] Error in if ((e[1] >= e[2]) || e[3] >= e[4]) { : 
[10.2_external_validation.R]   missing value where TRUE/FALSE needed
[10.2_external_validation.R] Calls: sapply ... .local -> .rastFromXYZ -> rast -> rast -> .local -> new_rast
[10.2_external_validation.R] In addition: Warning messages:
[10.2_external_validation.R] 1: In min(dx) : no non-missing arguments to min; returning Inf
[10.2_external_validation.R] 2: In min(dy) : no non-missing arguments to min; returning Inf
[10.2_external_validation.R] 3: In min(x) : no non-missing arguments to min; returning Inf
[10.2_external_validation.R] 4: In max(x) : no non-missing arguments to max; returning -Inf
[10.2_external_validation.R] 5: In min(y) : no non-missing arguments to min; returning Inf
[10.2_external_validation.R] 6: In max(y) : no non-missing arguments to max; returning -Inf
[10.2_external_validation.R] Execution halted
  ✗ FAIL  10.2_external_validation.R                     (  4.1s)  Exit code: 1
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
[F01_main_figure1.R] Error in `rename()`:
[F01_main_figure1.R] ! Can't rename columns that don't exist.
[F01_main_figure1.R] ✖ Column `...5` doesn't exist.
[F01_main_figure1.R] Backtrace:
[F01_main_figure1.R]      ▆
[F01_main_figure1.R]   1. ├─dplyr::mutate(...)
[F01_main_figure1.R]   2. ├─dplyr::slice(...)
[F01_main_figure1.R]   3. ├─dplyr::select(...)
[F01_main_figure1.R]   4. ├─dplyr::rename(...)
[F01_main_figure1.R]   5. ├─dplyr:::rename.data.frame(...)
[F01_main_figure1.R]   6. │ └─tidyselect::eval_rename(expr(c(...)), .data)
[F01_main_figure1.R]   7. │   └─tidyselect:::rename_impl(...)
[F01_main_figure1.R]   8. │     └─tidyselect:::eval_select_impl(...)
[F01_main_figure1.R]   9. │       ├─tidyselect:::with_subscript_errors(...)
[F01_main_figure1.R]  10. │       │ └─base::withCallingHandlers(...)
[F01_main_figure1.R]  11. │       └─tidyselect:::vars_select_eval(...)
[F01_main_figure1.R]  12. │         └─tidyselect:::walk_data_tree(expr, data_mask, context_mask)
[F01_main_figure1.R]  13. │           └─tidyselect:::eval_c(expr, data_mask, context_mask)
[F01_main_figure1.R]  14. │             └─tidyselect:::reduce_sels(node, data_mask, context_mask, init = init)
[F01_main_figure1.R]  15. │               └─tidyselect:::walk_data_tree(new, data_mask, context_mask)
[F01_main_figure1.R]  16. │                 └─tidyselect:::as_indices_sel_impl(...)
[F01_main_figure1.R]  17. │                   └─tidyselect:::as_indices_impl(...)
[F01_main_figure1.R]  18. │                     └─tidyselect:::chr_as_locations(x, vars, call = call, arg = arg)
[F01_main_figure1.R]  19. │                       └─vctrs::vec_as_location(...)
[F01_main_figure1.R]  20. └─vctrs (local) `<fn>`()
[F01_main_figure1.R]  21.   └─vctrs:::stop_subscript_oob(...)
[F01_main_figure1.R]  22.     └─vctrs:::stop_subscript(...)
[F01_main_figure1.R]  23.       └─rlang::abort(...)
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
[F02_main_figure2.R] Ncells 1787586 95.5    2818544 150.6  2818544 150.6
[F02_main_figure2.R] Vcells 2518879 19.3    8388608  64.0  4311848  32.9
[F02_main_figure2.R] Error in h(simpleError(msg, call)) : 
[F02_main_figure2.R]   error in evaluating the argument 'x' in selecting a method for function 'plot': [subset] invalid name(s)
[F02_main_figure2.R] Calls: <Anonymous> -> $ -> subset -> subset -> .local -> error
[F02_main_figure2.R] Execution halted
  ✗ FAIL  F02_main_figure2.R                             (  4.0s)  Exit code: 1
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
[F03_main_figure3.R] Ncells 1787589 95.5    2818544 150.6  2818544 150.6
[F03_main_figure3.R] Vcells 2518880 19.3    8388608  64.0  4311848  32.9
[F03_main_figure3.R] null device 
[F03_main_figure3.R]           1 
[F03_main_figure3.R] Error: R: attempt to perform an operation not allowed by the security policy `PDF' @ error/constitute.c/IsCoderAuthorized/426
[F03_main_figure3.R] Execution halted
  ✗ FAIL  F03_main_figure3.R                             (  9.4s)  Exit code: 1
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
  ✓ PASS  S01_drivers.R                                  (  1.3s)  
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
[S02_cropland_uncertainty.R] Ncells 1787601 95.5    2818544 150.6  2818544 150.6
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
[S02_cropland_uncertainty.R] Map saved to Suppl.Fig01.png
[S02_cropland_uncertainty.R] Resolution: 10000 by 7000 pixels
[S02_cropland_uncertainty.R] Size: 10 by 7 inches (1000 dpi)
[S02_cropland_uncertainty.R] Error: R: attempt to perform an operation not allowed by the security policy `PDF' @ error/constitute.c/IsCoderAuthorized/426
[S02_cropland_uncertainty.R] Execution halted
  ✗ FAIL  S02_cropland_uncertainty.R                     ( 15.2s)  Exit code: 1
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
[S03_aggregate_vs_disaggregate.R] Ncells 1788244 95.6    2818544 150.6  2818544 150.6
[S03_aggregate_vs_disaggregate.R] Vcells 2519880 19.3    8388608  64.0  4311848  32.9
[S03_aggregate_vs_disaggregate.R] Joining with `by = join_by(source)`
[S03_aggregate_vs_disaggregate.R] Error: R: cache resources exhausted `' @ error/cache.c/OpenPixelCache/4095
[S03_aggregate_vs_disaggregate.R] Execution halted
  ✗ FAIL  S03_aggregate_vs_disaggregate.R                ( 29.4s)  Exit code: 1
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
[S04_RF_hyperparameters.R] Ncells 1788244 95.6    2818544 150.6  2818544 150.6
[S04_RF_hyperparameters.R] Vcells 2519880 19.3    8388608  64.0  4311848  32.9
[S04_RF_hyperparameters.R] Joining with `by = join_by(country, gadm_0)`
[S04_RF_hyperparameters.R] Warning message:
[S04_RF_hyperparameters.R] In text.default(6, 7.5, "Model performance by \naggregation level",  :
[S04_RF_hyperparameters.R]   "line" is not a graphical parameter
[S04_RF_hyperparameters.R] null device 
[S04_RF_hyperparameters.R]           1 
  ✓ PASS  S04_RF_hyperparameters.R                       (  7.7s)  
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
  ✓ PASS  S05_RF_unseen_performance.R                    (  5.1s)  
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
[S06_size_class_comparison.R] Ncells 1788244 95.6    2818544 150.6  2818544 150.6
[S06_size_class_comparison.R] Vcells 2519880 19.3    8388608  64.0  4311848  32.9
[S06_size_class_comparison.R] Joining with `by = join_by(train_country)`
[S06_size_class_comparison.R] Joining with `by = join_by(test_country)`
  ✓ PASS  S06_size_class_comparison.R                    (  5.1s)  
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
[S07_distribution_parameters.R] Ncells 1788244 95.6    2818544 150.6  2818544 150.6
[S07_distribution_parameters.R] Vcells 2519880 19.3    8388608  64.0  4311848  32.9
[S07_distribution_parameters.R] Joining with `by = join_by(NAME_0, GID_0)`
[S07_distribution_parameters.R] Joining with `by = join_by(NAME_0, GID_0)`
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
[S07_distribution_parameters.R] Warning message:
[S07_distribution_parameters.R] `position_dodge()` requires non-overlapping x intervals. 
[S07_distribution_parameters.R] Warning messages:
[S07_distribution_parameters.R] 1: `position_dodge()` requires non-overlapping x intervals. 
[S07_distribution_parameters.R] 2: `position_dodge()` requires non-overlapping x intervals. 
  ✓ PASS  S07_distribution_parameters.R                  (  5.0s)  
[S08_variable_importance.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S08_variable_importance.R] ✔ purrr     1.2.1     
[S08_variable_importance.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S08_variable_importance.R] ✖ dplyr::filter() masks stats::filter()
[S08_variable_importance.R] ✖ dplyr::lag()    masks stats::lag()
[S08_variable_importance.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S08_variable_importance.R] Loading required package: patchwork
[S08_variable_importance.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[S08_variable_importance.R] Ncells 1787604 95.5    2818544 150.6  2818544 150.6
[S08_variable_importance.R] Vcells 2518794 19.3    8388608  64.0  4311848  32.9
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
[S08_variable_importance.R] Map saved to Suppl.Fig07.png
[S08_variable_importance.R] Resolution: 7000 by 10000 pixels
[S08_variable_importance.R] Size: 7 by 10 inches (1000 dpi)
[S08_variable_importance.R] Error: R: attempt to perform an operation not allowed by the security policy `PDF' @ error/constitute.c/IsCoderAuthorized/426
[S08_variable_importance.R] Execution halted
  ✗ FAIL  S08_variable_importance.R                      ( 12.7s)  Exit code: 1
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
[T01_area_production_tables.R] Ncells 1787589 95.5    2818544 150.6  2818544 150.6
[T01_area_production_tables.R] Vcells 2518880 19.3    8388608  64.0  4311848  32.9
[T01_area_production_tables.R] Joining with `by = join_by(country)`
  ✓ PASS  T01_area_production_tables.R                   (  5.0s)  
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
[T02_heterogeneity_drivers.R] Ncells 1792524 95.8    2846527 152.1  2846527 152.1
[T02_heterogeneity_drivers.R] Vcells 2634879 20.2    8388608  64.0  4243638  32.4
[T02_heterogeneity_drivers.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[T02_heterogeneity_drivers.R] Ncells 1804433 96.4    2846527 152.1  2846527 152.1
[T02_heterogeneity_drivers.R] Vcells 2670818 20.4    8388608  64.0  4243638  32.4
[T02_heterogeneity_drivers.R]           used (Mb) gc trigger  (Mb) max used  (Mb)
[T02_heterogeneity_drivers.R] Ncells 1823924 97.5    2846527 152.1  2846527 152.1
[T02_heterogeneity_drivers.R] Vcells 2726657 20.9    8388608  64.0  4243638  32.4
[T02_heterogeneity_drivers.R] Error in `summarize()`:
[T02_heterogeneity_drivers.R] ! Can't transform a data frame with duplicate names.
[T02_heterogeneity_drivers.R] Backtrace:
[T02_heterogeneity_drivers.R]     ▆
[T02_heterogeneity_drivers.R]  1. ├─base::sort(...)
[T02_heterogeneity_drivers.R]  2. ├─base::unlist(...)
[T02_heterogeneity_drivers.R]  3. ├─dplyr::summarize(...)
[T02_heterogeneity_drivers.R]  4. └─dplyr:::summarise.data.frame(...)
[T02_heterogeneity_drivers.R]  5.   └─dplyr:::summarise_cols(.data, dplyr_quosures(...), by, "summarise")
[T02_heterogeneity_drivers.R]  6.     └─DataMask$new(data, by, verb, error_call = error_call)
[T02_heterogeneity_drivers.R]  7.       └─dplyr (local) initialize(...)
[T02_heterogeneity_drivers.R]  8.         └─rlang::abort(...)
[T02_heterogeneity_drivers.R] Execution halted
  ✗ FAIL  T02_heterogeneity_drivers.R                    (  5.1s)  Exit code: 1

======================================================================
TEST SUMMARY
======================================================================

  Stat   Script                                          Time(s)  Note
  ------------------------------------------------------------------------
  ✓ PASS  00_synthetic_data                                 7.2    
  ✓ PASS  00_install_packages.R                             0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  00_download_spatial_data.R                        0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  01.2_chirps_summarize.R                           0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  02.1_compile_LSMS.R                               0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  05.2_RF_optimization_summary.R                    0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  08.1_predictions_by_country.R                     0.0    SKIPPED (download/SLURM/timeout script)
  ✓ PASS  01.1_chirps_download.R                            1.8    
  ✓ PASS  01.3_chirps_trends.R                              4.2    
  ✓ PASS  01.4_prepare_spatial_layers.R                     3.2    
  ✓ PASS  02.2_harmonize_farm_area.R                        3.9    
  ✓ PASS  02.3_measured_vs_reported.R                       2.0    
  ✓ PASS  03.1_pooled_data.R                                1.2    
  ✗ FAIL  03.2_correlation_drivers.R                       32.5    Exit code: 1
  ✓ PASS  03.3_descriptive_stats.R                         19.0    
  ✓ PASS  04.1_comparing_ML_algorithms.R                    1.3    
  ✗ FAIL  04.2_RF_within_country.R                         46.3    Exit code: 1
  ✗ FAIL  04.3_RF_between_countries.R                       5.0    Exit code: 1
  ✗ FAIL  04.4_RF_model_evaluation.R                      620.0    Exit code: 124
  ✗ FAIL  04.5_cross_country_graphs.R                       0.2    Exit code: 1
  ✓ PASS  04.6_discrepancy_analysis.R                      14.7    
  ✓ PASS  05.1_RF_optimization.R                            3.7    
  ✓ PASS  05.3_RF_robustness.R                              0.2    
  ✓ PASS  06.1_quantile_RF.R                                3.2    
  ✗ FAIL  06.3_prediction_maps.R                          125.6    Exit code: 1
  ✓ PASS  06.4_cropland_sensitivity.R                      14.4    
  ✓ PASS  07.2_QRF_distribution_eval.R                     17.8    
  ✗ FAIL  08.2_generate_virtual_farms.R                     7.3    Exit code: 1
  ✗ FAIL  08.3_farm_size_classes.R                          4.7    Exit code: 1
  ✗ FAIL  09.1_AEZ_characterization.R                       4.0    Exit code: 1
  ✗ FAIL  10.1_prepare_validation_data.R                    4.4    Exit code: 1
  ✗ FAIL  10.2_external_validation.R                        4.1    Exit code: 1
  ✗ FAIL  F01_main_figure1.R                                3.9    Exit code: 1
  ✗ FAIL  F02_main_figure2.R                                4.0    Exit code: 1
  ✗ FAIL  F03_main_figure3.R                                9.4    Exit code: 1
  ✓ PASS  S01_drivers.R                                     1.3    
  ✗ FAIL  S02_cropland_uncertainty.R                       15.2    Exit code: 1
  ✗ FAIL  S03_aggregate_vs_disaggregate.R                  29.4    Exit code: 1
  ✓ PASS  S04_RF_hyperparameters.R                          7.7    
  ✓ PASS  S05_RF_unseen_performance.R                       5.1    
  ✓ PASS  S06_size_class_comparison.R                       5.1    
  ✓ PASS  S07_distribution_parameters.R                     5.0    
  ✗ FAIL  S08_variable_importance.R                        12.7    Exit code: 1
  ✓ PASS  T01_area_production_tables.R                      5.0    
  ✗ FAIL  T02_heterogeneity_drivers.R                       5.1    Exit code: 1

======================================================================
Total: 45   Passed: 27   Failed: 18   Time: 1062s

Report: ../output/reports/full_pipeline_test_report.md

✅ CORE PIPELINE OK (11/22 core scripts passed = 50%)
```

## Pipeline Report
# Farm Size Prediction — Full Pipeline CI Report

**Generated:** 2026-03-16 14:39:57 UTC
**R Version:** R version 4.3.3 (2024-02-29)

## Summary

| Metric | Value |
|--------|-------|
| Total Scripts  | 45 |
| Passed         | 27 |
| Failed         | 18 |
| Total Time     | 1061.5s |

## Per-Script Results

| Phase | Script | Status | Time | Note |
|-------|--------|--------|------|------|
| 00 | `00_synthetic_data` | ✅ PASS | 7.2s |  |
| 00 | `00_install_packages.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 00 | `00_download_spatial_data.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.2 | `01.2_chirps_summarize.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 02.1 | `02.1_compile_LSMS.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 05.2 | `05.2_RF_optimization_summary.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 08.1 | `08.1_predictions_by_country.R` | ✅ PASS | 0s | SKIPPED (download/SLURM/timeout script) |
| 01.1 | `01.1_chirps_download.R` | ✅ PASS | 1.8s |  |
| 01.3 | `01.3_chirps_trends.R` | ✅ PASS | 4.2s |  |
| 01.4 | `01.4_prepare_spatial_layers.R` | ✅ PASS | 3.2s |  |
| 02.2 | `02.2_harmonize_farm_area.R` | ✅ PASS | 3.9s |  |
| 02.3 | `02.3_measured_vs_reported.R` | ✅ PASS | 2s |  |
| 03.1 | `03.1_pooled_data.R` | ✅ PASS | 1.2s |  |
| 03.2 | `03.2_correlation_drivers.R` | ❌ FAIL | 32.5s | Exit code: 1 |
| 03.3 | `03.3_descriptive_stats.R` | ✅ PASS | 19s |  |
| 04.1 | `04.1_comparing_ML_algorithms.R` | ✅ PASS | 1.3s |  |
| 04.2 | `04.2_RF_within_country.R` | ❌ FAIL | 46.3s | Exit code: 1 |
| 04.3 | `04.3_RF_between_countries.R` | ❌ FAIL | 5s | Exit code: 1 |
| 04.4 | `04.4_RF_model_evaluation.R` | ❌ FAIL | 620s | Exit code: 124 |
| 04.5 | `04.5_cross_country_graphs.R` | ❌ FAIL | 0.2s | Exit code: 1 |
| 04.6 | `04.6_discrepancy_analysis.R` | ✅ PASS | 14.7s |  |
| 05.1 | `05.1_RF_optimization.R` | ✅ PASS | 3.7s |  |
| 05.3 | `05.3_RF_robustness.R` | ✅ PASS | 0.2s |  |
| 06.1 | `06.1_quantile_RF.R` | ✅ PASS | 3.2s |  |
| 06.3 | `06.3_prediction_maps.R` | ❌ FAIL | 125.6s | Exit code: 1 |
| 06.4 | `06.4_cropland_sensitivity.R` | ✅ PASS | 14.4s |  |
| 07.2 | `07.2_QRF_distribution_eval.R` | ✅ PASS | 17.8s |  |
| 08.2 | `08.2_generate_virtual_farms.R` | ❌ FAIL | 7.3s | Exit code: 1 |
| 08.3 | `08.3_farm_size_classes.R` | ❌ FAIL | 4.7s | Exit code: 1 |
| 09.1 | `09.1_AEZ_characterization.R` | ❌ FAIL | 4s | Exit code: 1 |
| 10.1 | `10.1_prepare_validation_data.R` | ❌ FAIL | 4.4s | Exit code: 1 |
| 10.2 | `10.2_external_validation.R` | ❌ FAIL | 4.1s | Exit code: 1 |
| F01 | `F01_main_figure1.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| F02 | `F02_main_figure2.R` | ❌ FAIL | 4s | Exit code: 1 |
| F03 | `F03_main_figure3.R` | ❌ FAIL | 9.4s | Exit code: 1 |
| S01 | `S01_drivers.R` | ✅ PASS | 1.3s |  |
| S02 | `S02_cropland_uncertainty.R` | ❌ FAIL | 15.2s | Exit code: 1 |
| S03 | `S03_aggregate_vs_disaggregate.R` | ❌ FAIL | 29.4s | Exit code: 1 |
| S04 | `S04_RF_hyperparameters.R` | ✅ PASS | 7.7s |  |
| S05 | `S05_RF_unseen_performance.R` | ✅ PASS | 5.1s |  |
| S06 | `S06_size_class_comparison.R` | ✅ PASS | 5.1s |  |
| S07 | `S07_distribution_parameters.R` | ✅ PASS | 5s |  |
| S08 | `S08_variable_importance.R` | ❌ FAIL | 12.7s | Exit code: 1 |
| T01 | `T01_area_production_tables.R` | ✅ PASS | 5s |  |
| T02 | `T02_heterogeneity_drivers.R` | ❌ FAIL | 5.1s | Exit code: 1 |
