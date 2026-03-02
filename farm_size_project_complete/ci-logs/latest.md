# CI Run Log
Run: 22582335087  Commit: 19da22a295c40c2ceae092949e9eb3580f03438b  Time: Mon Mar  2 15:33:23 UTC 2026

## Raw Output
```

======================================================================
FARM SIZE PREDICTION - FULL SEQUENTIAL PIPELINE TEST
======================================================================
Started: 2026-03-02 15:18:59.439917

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
[00_synthetic_data.R] 2. Creating synthetic LSMS survey data...
[00_synthetic_data.R]    LSMS CSV + RDS done  (13871 farms).
[00_synthetic_data.R] 3. Extracting predictors at farm locations...
[00_synthetic_data.R]    Analysis datasets done  (8265 farms in 95th trim).
[00_synthetic_data.R] 4. Creating synthetic GADM boundaries...
[00_synthetic_data.R]    GADM boundaries done.
[00_synthetic_data.R] 5. Creating output table stubs...
[00_synthetic_data.R]    Output stubs done.
[00_synthetic_data.R] 6. Creating processed data stubs...
[00_synthetic_data.R]    RF model stub done.
[00_synthetic_data.R]    Processed stubs done.
[00_synthetic_data.R] 7. Creating figure stubs...
[00_synthetic_data.R]    Figure stubs done.
[00_synthetic_data.R] 8b. Creating leave-one stubs for 04.5...
[00_synthetic_data.R]    Leave-one stubs done  (16 countries × 2 models).
[00_synthetic_data.R] 9. Creating country-year raw files...
[00_synthetic_data.R] 
[00_synthetic_data.R] ======================================================================
[00_synthetic_data.R] SYNTHETIC DATA GENERATION COMPLETE
[00_synthetic_data.R] ======================================================================
[00_synthetic_data.R]   Farms generated:   13871
[00_synthetic_data.R]   After 95th trim:   8265
[00_synthetic_data.R]   Countries:         16
[00_synthetic_data.R]   Raster layers:     11
[00_synthetic_data.R]   Prediction stubs:  6 Python + RF + QRF rasters
[00_synthetic_data.R]   Output stubs:      15
[00_synthetic_data.R]   Processed files:   134
  ✓ PASS  00_synthetic_data                              (  7.0s)  
----------------------------------------------------------------------
PHASE 1: Install/Download Scripts (skipped in CI)
----------------------------------------------------------------------
  ✓ PASS  00_install_packages.R                          (  0.0s)  SKIPPED (install/download script)
  ✓ PASS  00_download_spatial_data.R                     (  0.0s)  SKIPPED (install/download script)
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
[01.1_chirps_download.R] Finished: 2026-03-02 15:19:08.427023
[01.1_chirps_download.R] ======================================================================
  ✓ PASS  01.1_chirps_download.R                         (  1.9s)  
[01.2_chirps_summarize.R] Loading required package: curl
[01.2_chirps_summarize.R] Using libcurl 7.81.0 with OpenSSL/3.0.2
[01.2_chirps_summarize.R] === Generating file list ===
[01.2_chirps_summarize.R] Total files to download: 1584
[01.2_chirps_summarize.R] Created directory: ../data/raw/spatial/rainfall/CHIRPS
[01.2_chirps_summarize.R] 
[01.2_chirps_summarize.R] === Downloading CHIRPS data ===
[01.2_chirps_summarize.R] Already downloaded: 0 files
[01.2_chirps_summarize.R] Downloaded: 50 files...
[01.2_chirps_summarize.R] Downloaded: 100 files...
[01.2_chirps_summarize.R] Downloaded: 150 files...
[01.2_chirps_summarize.R] Downloaded: 200 files...
[01.2_chirps_summarize.R] Downloaded: 250 files...
[01.2_chirps_summarize.R] Downloaded: 300 files...
[01.2_chirps_summarize.R] Downloaded: 350 files...
[01.2_chirps_summarize.R] Downloaded: 400 files...
[01.2_chirps_summarize.R] Downloaded: 450 files...
[01.2_chirps_summarize.R] Downloaded: 500 files...
[01.2_chirps_summarize.R] Downloaded: 550 files...
[01.2_chirps_summarize.R] Downloaded: 600 files...
[01.2_chirps_summarize.R] 
[01.2_chirps_summarize.R] 
[01.2_chirps_summarize.R] Execution halted
  ✗ FAIL  01.2_chirps_summarize.R                        (180.0s)  Exit code: 124
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
[01.3_chirps_trends.R] 
[01.3_chirps_trends.R] Processing year: 1981
[01.3_chirps_trends.R]   Missing: chirps-v2.0.1981.01.1.tif
[01.3_chirps_trends.R]   Missing: chirps-v2.0.1981.01.2.tif
[01.3_chirps_trends.R]   Missing: chirps-v2.0.1981.01.3.tif
[01.3_chirps_trends.R] Error: [writeRaster] there are no cell values
[01.3_chirps_trends.R] Execution halted
  ✗ FAIL  01.3_chirps_trends.R                           (  3.8s)  Exit code: 1
[01.4_prepare_spatial_layers.R] Loading required package: terra
[01.4_prepare_spatial_layers.R] terra 1.8.93
[01.4_prepare_spatial_layers.R] === Loading yearly rainfall data ===
[01.4_prepare_spatial_layers.R] Error: No yearly rainfall files found in: ../data/raw/spatial/rainfall/rainfall_yearly
[01.4_prepare_spatial_layers.R] Execution halted
  ✗ FAIL  01.4_prepare_spatial_layers.R                  (  2.9s)  Exit code: 1
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   South Africa: level 2
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_ZAF_2_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 5579804 bytes (5.3 MB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 5.3 MB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   South Africa: level 3
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_ZAF_3_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 9333773 bytes (8.9 MB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 8.9 MB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   South Africa: level 4
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_ZAF_4_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 29636493 bytes (28.3 MB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 28.3 MB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   South Africa: level 5
[02.1_compile_LSMS.R] gadm41_ZAF_5_pk.rds - this file does not exist
[02.1_compile_LSMS.R]   Zambia: level 1
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_ZMB_1_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 667019 bytes (651 KB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 651 KB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   Zambia: level 2
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_ZMB_2_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 2425218 bytes (2.3 MB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 2.3 MB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   Zambia: level 3
[02.1_compile_LSMS.R] gadm41_ZMB_3_pk.rds - this file does not exist
[02.1_compile_LSMS.R]   Zambia: level 4
[02.1_compile_LSMS.R] gadm41_ZMB_4_pk.rds - this file does not exist
[02.1_compile_LSMS.R]   Zambia: level 5
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R] Execution halted
  ✗ FAIL  02.1_compile_LSMS.R                            (180.0s)  Exit code: 124
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
  ✓ PASS  02.3_measured_vs_reported.R                    (  2.1s)  
Warning messages:
1: In system2("Rscript", c("--vanilla", shQuote(tmp)), stdout = log_file,  :
  command ''Rscript' --vanilla '/tmp/RtmpFjQxV8/file1a104c70657c.R' > '/tmp/RtmpFjQxV8/file1a1051002968.log' 2>&1' timed out after 180s
2: In system2("Rscript", c("--vanilla", shQuote(tmp)), stdout = log_file,  :
  command ''Rscript' --vanilla '/tmp/RtmpFjQxV8/file1a105bfcf398.R' > '/tmp/RtmpFjQxV8/file1a1018b53a02.log' 2>&1' timed out after 180s
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
[03.2_correlation_drivers.R] Loading required package: geodata
[03.2_correlation_drivers.R] === Loading study region ===
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Downloading GADM boundaries ===
[03.2_correlation_drivers.R]   Downloaded: Benin (level 3)
[03.2_correlation_drivers.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_BFA_3_pk.rds'
[03.2_correlation_drivers.R] Content type 'unknown' length 1177963 bytes (1.1 MB)
[03.2_correlation_drivers.R] ==================================================
[03.2_correlation_drivers.R] downloaded 1.1 MB
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R]   Downloaded: Burkina (level 3)
[03.2_correlation_drivers.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_CIV_4_pk.rds'
[03.2_correlation_drivers.R] Content type 'unknown' length 620808 bytes (606 KB)
[03.2_correlation_drivers.R] ==================================================
[03.2_correlation_drivers.R] downloaded 606 KB
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R]   Downloaded: Cote_d_Ivoire (level 4)
[03.2_correlation_drivers.R]   Downloaded: Ethiopia (level 3)
[03.2_correlation_drivers.R]   Downloaded: Ghana (level 2)
[03.2_correlation_drivers.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_GNB_2_pk.rds'
[03.2_correlation_drivers.R] Content type 'unknown' length 329378 bytes (321 KB)
[03.2_correlation_drivers.R] ==================================================
[03.2_correlation_drivers.R] downloaded 321 KB
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R]   Downloaded: Guinea_Bissau (level 2)
[03.2_correlation_drivers.R]   Downloaded: Malawi (level 3)
[03.2_correlation_drivers.R]   Downloaded: Mali (level 4)
[03.2_correlation_drivers.R]   Downloaded: Niger (level 3)
[03.2_correlation_drivers.R]   Downloaded: Nigeria (level 2)
[03.2_correlation_drivers.R]   Downloaded: Rwanda (level 4)
[03.2_correlation_drivers.R]   Downloaded: Senegal (level 4)
[03.2_correlation_drivers.R]   Downloaded: Tanzania (level 3)
[03.2_correlation_drivers.R]   Downloaded: Togo (level 3)
[03.2_correlation_drivers.R]   Downloaded: Uganda (level 4)
[03.2_correlation_drivers.R]   Downloaded: Zambia (level 2)
[03.2_correlation_drivers.R] Error in rbind(deparse.level, ...) : 
[03.2_correlation_drivers.R]   argument "x" is missing, with no default
[03.2_correlation_drivers.R] Calls: do.call -> <Anonymous> -> rbind
[03.2_correlation_drivers.R] Execution halted
  ✗ FAIL  03.2_correlation_drivers.R                     (  8.8s)  Exit code: 1
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
  ✓ PASS  03.3_descriptive_stats.R                       ( 19.7s)  
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
  ✓ PASS  04.1_comparing_ML_algorithms.R                 (  1.4s)  
[04.2_RF_within_country.R] Loading required package: tidyverse
[04.2_RF_within_country.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[04.2_RF_within_country.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[04.2_RF_within_country.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[04.2_RF_within_country.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[04.2_RF_within_country.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[04.2_RF_within_country.R] ✔ purrr     1.2.1     
[04.2_RF_within_country.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[04.2_RF_within_country.R] ✖ dplyr::filter() masks stats::filter()
[04.2_RF_within_country.R] ✖ dplyr::lag()    masks stats::lag()
[04.2_RF_within_country.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[04.2_RF_within_country.R] Error: path does not exist
[04.2_RF_within_country.R] Execution halted
  ✗ FAIL  04.2_RF_within_country.R                       (  3.8s)  Exit code: 1
[04.3_RF_between_countries.R] Loading required package: tidyverse
[04.3_RF_between_countries.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[04.3_RF_between_countries.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[04.3_RF_between_countries.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[04.3_RF_between_countries.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[04.3_RF_between_countries.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[04.3_RF_between_countries.R] ✔ purrr     1.2.1     
[04.3_RF_between_countries.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[04.3_RF_between_countries.R] ✖ dplyr::filter() masks stats::filter()
[04.3_RF_between_countries.R] ✖ dplyr::lag()    masks stats::lag()
[04.3_RF_between_countries.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[04.3_RF_between_countries.R] Error: path does not exist
[04.3_RF_between_countries.R] Execution halted
  ✗ FAIL  04.3_RF_between_countries.R                    (  3.8s)  Exit code: 1
[04.4_RF_model_evaluation.R] Loading required package: tidyverse
[04.4_RF_model_evaluation.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[04.4_RF_model_evaluation.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[04.4_RF_model_evaluation.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[04.4_RF_model_evaluation.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[04.4_RF_model_evaluation.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[04.4_RF_model_evaluation.R] ✔ purrr     1.2.1     
[04.4_RF_model_evaluation.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[04.4_RF_model_evaluation.R] ✖ dplyr::filter() masks stats::filter()
[04.4_RF_model_evaluation.R] ✖ dplyr::lag()    masks stats::lag()
[04.4_RF_model_evaluation.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[04.4_RF_model_evaluation.R] Error: path does not exist
[04.4_RF_model_evaluation.R] Execution halted
  ✗ FAIL  04.4_RF_model_evaluation.R                     (  3.7s)  Exit code: 1
[04.5_cross_country_graphs.R] Error in do.call(rbind, lapply(frf, readRDS)$results) : 
[04.5_cross_country_graphs.R]   second argument must be a list
[04.5_cross_country_graphs.R] Calls: summarize -> do.call
[04.5_cross_country_graphs.R] Execution halted
  ✗ FAIL  04.5_cross_country_graphs.R                    (  0.2s)  Exit code: 1
[04.6_discrepancy_analysis.R] Loading required package: tidyverse
[04.6_discrepancy_analysis.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[04.6_discrepancy_analysis.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[04.6_discrepancy_analysis.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[04.6_discrepancy_analysis.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[04.6_discrepancy_analysis.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[04.6_discrepancy_analysis.R] ✔ purrr     1.2.1     
[04.6_discrepancy_analysis.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[04.6_discrepancy_analysis.R] ✖ dplyr::filter() masks stats::filter()
[04.6_discrepancy_analysis.R] ✖ dplyr::lag()    masks stats::lag()
[04.6_discrepancy_analysis.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[04.6_discrepancy_analysis.R] Error in `summarize()`:
[04.6_discrepancy_analysis.R] ℹ In argument: `rsq = max(Rsquared, na.rm = T)`.
[04.6_discrepancy_analysis.R] Caused by error:
[04.6_discrepancy_analysis.R] ! object 'Rsquared' not found
[04.6_discrepancy_analysis.R] Backtrace:
[04.6_discrepancy_analysis.R]      ▆
[04.6_discrepancy_analysis.R]   1. ├─dplyr::mutate(...)
[04.6_discrepancy_analysis.R]   2. ├─dplyr::bind_rows(...)
[04.6_discrepancy_analysis.R]   3. │ └─rlang::list2(...)
[04.6_discrepancy_analysis.R]   4. ├─dplyr::bind_rows(...)
[04.6_discrepancy_analysis.R]   5. │ └─rlang::list2(...)
[04.6_discrepancy_analysis.R]   6. ├─dplyr::summarize(...)
[04.6_discrepancy_analysis.R]   7. ├─dplyr:::summarise.grouped_df(...)
[04.6_discrepancy_analysis.R]   8. │ └─dplyr:::summarise_cols(.data, dplyr_quosures(...), by, "summarise")
[04.6_discrepancy_analysis.R]   9. │   ├─base::withCallingHandlers(...)
[04.6_discrepancy_analysis.R]  10. │   └─dplyr:::map(quosures, summarise_eval_one, mask = mask)
[04.6_discrepancy_analysis.R]  11. │     └─base::lapply(.x, .f, ...)
[04.6_discrepancy_analysis.R]  12. │       └─dplyr (local) FUN(X[[i]], ...)
[04.6_discrepancy_analysis.R]  13. │         └─mask$eval_all_summarise(quo)
[04.6_discrepancy_analysis.R]  14. │           └─dplyr (local) eval()
[04.6_discrepancy_analysis.R]  15. └─base::.handleSimpleError(...)
[04.6_discrepancy_analysis.R]  16.   └─dplyr (local) h(simpleError(msg, call))
[04.6_discrepancy_analysis.R]  17.     └─dplyr (local) handler(cnd)
[04.6_discrepancy_analysis.R]  18.       └─rlang::abort(message, class = error_class, parent = parent, call = error_call)
[04.6_discrepancy_analysis.R] Execution halted
  ✗ FAIL  04.6_discrepancy_analysis.R                    (  1.2s)  Exit code: 1
----------------------------------------------------------------------
PHASE 5: RF Optimisation (05.x)
----------------------------------------------------------------------
[05.1_RF_optimization.R] [1] "---------- case1 -------------"
[05.1_RF_optimization.R] `geom_smooth()` using formula = 'y ~ x'
[05.1_RF_optimization.R] Error in `annotate()`:
[05.1_RF_optimization.R] ! Problem while setting up geom aesthetics.
[05.1_RF_optimization.R] ℹ Error occurred in the 3rd layer.
[05.1_RF_optimization.R] Caused by error in `list_sizes()`:
[05.1_RF_optimization.R] ! `x$label` must be a vector, not a call.
[05.1_RF_optimization.R] ℹ Read our FAQ about scalar types (`?vctrs::faq_error_scalar_type`) to learn more.
[05.1_RF_optimization.R] Backtrace:
[05.1_RF_optimization.R]      ▆
[05.1_RF_optimization.R]   1. ├─base::print(P01 + P02 + P03)
[05.1_RF_optimization.R]   2. ├─patchwork:::print.patchwork(P01 + P02 + P03)
[05.1_RF_optimization.R]   3. │ └─patchwork:::build_patchwork(plot, plot$layout$guides %||% "auto")
[05.1_RF_optimization.R]   4. │   └─base::lapply(x$plots, plot_table, guides = guides)
[05.1_RF_optimization.R]   5. │     ├─patchwork (local) FUN(X[[i]], ...)
[05.1_RF_optimization.R]   6. │     └─patchwork:::plot_table.ggplot(X[[i]], ...)
[05.1_RF_optimization.R]   7. │       └─ggplot2::ggplotGrob(x)
[05.1_RF_optimization.R]   8. │         ├─ggplot2::ggplot_gtable(ggplot_build(x))
[05.1_RF_optimization.R]   9. │         │ └─ggplot2:::attach_plot_env(data@plot@plot_env)
[05.1_RF_optimization.R]  10. │         │   └─base::options(ggplot2_plot_env = env)
[05.1_RF_optimization.R]  11. │         ├─ggplot2::ggplot_build(x)
[05.1_RF_optimization.R]  12. │         └─ggplot2 (local) `ggplot_build.ggplot2::ggplot`(x)
[05.1_RF_optimization.R]  13. │           └─ggplot2:::by_layer(...)
[05.1_RF_optimization.R]  14. │             ├─rlang::try_fetch(...)
[05.1_RF_optimization.R]  15. │             │ ├─base::tryCatch(...)
[05.1_RF_optimization.R]  16. │             │ │ └─base (local) tryCatchList(expr, classes, parentenv, handlers)
[05.1_RF_optimization.R]  17. │             │ │   └─base (local) tryCatchOne(expr, names, parentenv, handlers[[1L]])
[05.1_RF_optimization.R]  18. │             │ │     └─base (local) doTryCatch(return(expr), name, parentenv, handler)
[05.1_RF_optimization.R]  19. │             │ └─base::withCallingHandlers(...)
[05.1_RF_optimization.R]  20. │             └─ggplot2 (local) f(l = layers[[i]], d = data[[i]])
[05.1_RF_optimization.R]  21. │               └─l$compute_geom_2(d, theme = plot@theme)
[05.1_RF_optimization.R]  22. │                 └─ggplot2 (local) compute_geom_2(..., self = self)
[05.1_RF_optimization.R]  23. │                   └─self$geom$use_defaults(...)
[05.1_RF_optimization.R]  24. │                     └─ggplot2 (local) use_defaults(..., self = self)
[05.1_RF_optimization.R]  25. │                       └─ggplot2:::check_aesthetics(new_params, nrow(data))
[05.1_RF_optimization.R]  26. │                         └─vctrs::list_sizes(x)
[05.1_RF_optimization.R]  27. └─vctrs:::stop_scalar_type(`<fn>`(R^2 == 0.51), "x$label", `<env>`)
[05.1_RF_optimization.R]  28.   └─vctrs:::stop_vctrs(...)
[05.1_RF_optimization.R]  29.     └─rlang::abort(message, class = c(class, "vctrs_error"), ..., call = call)
[05.1_RF_optimization.R] Execution halted
  ✗ FAIL  05.1_RF_optimization.R                         (  2.4s)  Exit code: 1
[05.2_RF_optimization_summary.R] Loading required package: tidyverse
[05.2_RF_optimization_summary.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[05.2_RF_optimization_summary.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[05.2_RF_optimization_summary.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[05.2_RF_optimization_summary.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[05.2_RF_optimization_summary.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[05.2_RF_optimization_summary.R] ✔ purrr     1.2.1     
[05.2_RF_optimization_summary.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[05.2_RF_optimization_summary.R] ✖ dplyr::filter() masks stats::filter()
[05.2_RF_optimization_summary.R] ✖ dplyr::lag()    masks stats::lag()
[05.2_RF_optimization_summary.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[05.2_RF_optimization_summary.R] Error in c(5, 45:55, 60, 100, ) : argument 5 is empty
[05.2_RF_optimization_summary.R] Calls: expand.grid
[05.2_RF_optimization_summary.R] Execution halted
  ✗ FAIL  05.2_RF_optimization_summary.R                 (  5.0s)  Exit code: 1
[05.3_RF_robustness.R] Error in -res$Rsquared : invalid argument to unary operator
[05.3_RF_robustness.R] Calls: [ -> [.data.frame -> order
[05.3_RF_robustness.R] Execution halted
  ✗ FAIL  05.3_RF_robustness.R                           (  0.2s)  Exit code: 1
----------------------------------------------------------------------
PHASE 6: Quantile RF & Prediction Maps (06.x)
----------------------------------------------------------------------
[06.1_quantile_RF.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[06.1_quantile_RF.R] ✖ dplyr::filter() masks stats::filter()
[06.1_quantile_RF.R] ✖ dplyr::lag()    masks stats::lag()
[06.1_quantile_RF.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[06.1_quantile_RF.R] Warning message:
[06.1_quantile_RF.R] There was 1 warning in `mutate()`.
[06.1_quantile_RF.R] ℹ In argument: `mbucket = as.integer(gsub("\\.rds$", "", gsub(".*\\-", "",
[06.1_quantile_RF.R]   filename), ignore.case = T))`.
[06.1_quantile_RF.R] Caused by warning:
[06.1_quantile_RF.R] ! NAs introduced by coercion 
[06.1_quantile_RF.R] Error in `geom_point()`:
[06.1_quantile_RF.R] ! Problem while computing aesthetics.
[06.1_quantile_RF.R] ℹ Error occurred in the 1st layer.
[06.1_quantile_RF.R] Caused by error:
[06.1_quantile_RF.R] ! object 'Rsquared' not found
[06.1_quantile_RF.R] Backtrace:
[06.1_quantile_RF.R]      ▆
[06.1_quantile_RF.R]   1. ├─base (local) `<fn>`(x)
[06.1_quantile_RF.R]   2. ├─ggplot2 (local) `print.ggplot2::ggplot`(x)
[06.1_quantile_RF.R]   3. │ ├─ggplot2::ggplot_build(x)
[06.1_quantile_RF.R]   4. │ └─ggplot2 (local) `ggplot_build.ggplot2::ggplot`(x)
[06.1_quantile_RF.R]   5. │   └─ggplot2:::by_layer(...)
[06.1_quantile_RF.R]   6. │     ├─rlang::try_fetch(...)
[06.1_quantile_RF.R]   7. │     │ ├─base::tryCatch(...)
[06.1_quantile_RF.R]   8. │     │ │ └─base (local) tryCatchList(expr, classes, parentenv, handlers)
[06.1_quantile_RF.R]   9. │     │ │   └─base (local) tryCatchOne(expr, names, parentenv, handlers[[1L]])
[06.1_quantile_RF.R]  10. │     │ │     └─base (local) doTryCatch(return(expr), name, parentenv, handler)
[06.1_quantile_RF.R]  11. │     │ └─base::withCallingHandlers(...)
[06.1_quantile_RF.R]  12. │     └─ggplot2 (local) f(l = layers[[i]], d = data[[i]])
[06.1_quantile_RF.R]  13. │       └─l$compute_aesthetics(d, plot)
[06.1_quantile_RF.R]  14. │         └─ggplot2 (local) compute_aesthetics(..., self = self)
[06.1_quantile_RF.R]  15. │           └─ggplot2:::eval_aesthetics(aesthetics, data)
[06.1_quantile_RF.R]  16. │             └─base::lapply(aesthetics, eval_tidy, data = data, env = env)
[06.1_quantile_RF.R]  17. │               └─rlang (local) FUN(X[[i]], ...)
[06.1_quantile_RF.R]  18. └─base::.handleSimpleError(...)
[06.1_quantile_RF.R]  19.   └─rlang (local) h(simpleError(msg, call))
[06.1_quantile_RF.R]  20.     └─handlers[[1L]](cnd)
[06.1_quantile_RF.R]  21.       └─cli::cli_abort(...)
[06.1_quantile_RF.R]  22.         └─rlang::abort(...)
[06.1_quantile_RF.R] Execution halted
  ✗ FAIL  06.1_quantile_RF.R                             (  1.4s)  Exit code: 1
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
[06.3_prediction_maps.R] There were 26 warnings (use warnings() to see them)
[06.3_prediction_maps.R] Error in save(rf_full_model, file = "../data/processed/2024-11-22.qrf_best_model_with_95th_trimmed_data.rdata") : 
[06.3_prediction_maps.R]   object ‘rf_full_model’ not found
[06.3_prediction_maps.R] Execution halted
  ✗ FAIL  06.3_prediction_maps.R                         (349.7s)  Exit code: 1
[06.4_cropland_sensitivity.R] Loading required package: tidyverse
[06.4_cropland_sensitivity.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[06.4_cropland_sensitivity.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[06.4_cropland_sensitivity.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[06.4_cropland_sensitivity.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[06.4_cropland_sensitivity.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[06.4_cropland_sensitivity.R] ✔ purrr     1.2.1     
[06.4_cropland_sensitivity.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[06.4_cropland_sensitivity.R] ✖ dplyr::filter() masks stats::filter()
[06.4_cropland_sensitivity.R] ✖ dplyr::lag()    masks stats::lag()
[06.4_cropland_sensitivity.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[06.4_cropland_sensitivity.R] Error: path does not exist
[06.4_cropland_sensitivity.R] Execution halted
  ✗ FAIL  06.4_cropland_sensitivity.R                    (  4.0s)  Exit code: 1
----------------------------------------------------------------------
PHASE 7: Predictions & Validation (07.x – 10.x)
----------------------------------------------------------------------
[07.2_QRF_distribution_eval.R] Loading required package: tidyverse
[07.2_QRF_distribution_eval.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[07.2_QRF_distribution_eval.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[07.2_QRF_distribution_eval.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[07.2_QRF_distribution_eval.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[07.2_QRF_distribution_eval.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[07.2_QRF_distribution_eval.R] ✔ purrr     1.2.1     
[07.2_QRF_distribution_eval.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[07.2_QRF_distribution_eval.R] ✖ dplyr::filter() masks stats::filter()
[07.2_QRF_distribution_eval.R] ✖ dplyr::lag()    masks stats::lag()
[07.2_QRF_distribution_eval.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[07.2_QRF_distribution_eval.R] Error: path does not exist
[07.2_QRF_distribution_eval.R] Execution halted
  ✗ FAIL  07.2_QRF_distribution_eval.R                   (  4.0s)  Exit code: 1
[08.1_predictions_by_country.R] Loading required package: tidyverse
[08.1_predictions_by_country.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[08.1_predictions_by_country.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[08.1_predictions_by_country.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[08.1_predictions_by_country.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[08.1_predictions_by_country.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[08.1_predictions_by_country.R] ✔ purrr     1.2.1     
[08.1_predictions_by_country.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[08.1_predictions_by_country.R] ✖ dplyr::filter() masks stats::filter()
[08.1_predictions_by_country.R] ✖ dplyr::lag()    masks stats::lag()
[08.1_predictions_by_country.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[08.1_predictions_by_country.R] Error: path does not exist
[08.1_predictions_by_country.R] Execution halted
  ✗ FAIL  08.1_predictions_by_country.R                  (  4.0s)  Exit code: 1
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
[08.2_generate_virtual_farms.R] Error: path does not exist
[08.2_generate_virtual_farms.R] Execution halted
  ✗ FAIL  08.2_generate_virtual_farms.R                  (  3.9s)  Exit code: 1
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
[08.3_farm_size_classes.R] Error: path does not exist
[08.3_farm_size_classes.R] Execution halted
  ✗ FAIL  08.3_farm_size_classes.R                       (  3.9s)  Exit code: 1
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
[09.1_AEZ_characterization.R] Error: path does not exist
[09.1_AEZ_characterization.R] Execution halted
  ✗ FAIL  09.1_AEZ_characterization.R                    (  3.9s)  Exit code: 1
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
[10.1_prepare_validation_data.R] Error: path does not exist
[10.1_prepare_validation_data.R] Execution halted
  ✗ FAIL  10.1_prepare_validation_data.R                 (  3.9s)  Exit code: 1
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
[10.2_external_validation.R] Error: path does not exist
[10.2_external_validation.R] Execution halted
  ✗ FAIL  10.2_external_validation.R                     (  3.9s)  Exit code: 1
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
[F01_main_figure1.R] Error: path does not exist
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
[F02_main_figure2.R] Error: path does not exist
[F02_main_figure2.R] Execution halted
  ✗ FAIL  F02_main_figure2.R                             (  3.9s)  Exit code: 1
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
[F03_main_figure3.R] Error: path does not exist
[F03_main_figure3.R] Execution halted
  ✗ FAIL  F03_main_figure3.R                             (  3.9s)  Exit code: 1
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
[S01_drivers.R] Error in UseMethod("filter") : 
[S01_drivers.R]   no applicable method for 'filter' applied to an object of class "NULL"
[S01_drivers.R] Calls: filter
[S01_drivers.R] Execution halted
  ✗ FAIL  S01_drivers.R                                  (  1.2s)  Exit code: 1
[S02_cropland_uncertainty.R] Loading required package: tidyverse
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
[S02_cropland_uncertainty.R] Error: path does not exist
[S02_cropland_uncertainty.R] Execution halted
  ✗ FAIL  S02_cropland_uncertainty.R                     (  3.9s)  Exit code: 1
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
[S03_aggregate_vs_disaggregate.R] Error: path does not exist
[S03_aggregate_vs_disaggregate.R] Execution halted
  ✗ FAIL  S03_aggregate_vs_disaggregate.R                (  3.9s)  Exit code: 1
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
[S04_RF_hyperparameters.R] Error: path does not exist
[S04_RF_hyperparameters.R] Execution halted
  ✗ FAIL  S04_RF_hyperparameters.R                       (  3.9s)  Exit code: 1
[S05_RF_unseen_performance.R] Loading required package: tidyverse
[S05_RF_unseen_performance.R] ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
[S05_RF_unseen_performance.R] ✔ dplyr     1.2.0     ✔ readr     2.2.0
[S05_RF_unseen_performance.R] ✔ forcats   1.0.1     ✔ stringr   1.6.0
[S05_RF_unseen_performance.R] ✔ ggplot2   4.0.2     ✔ tibble    3.3.1
[S05_RF_unseen_performance.R] ✔ lubridate 1.9.5     ✔ tidyr     1.3.2
[S05_RF_unseen_performance.R] ✔ purrr     1.2.1     
[S05_RF_unseen_performance.R] ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
[S05_RF_unseen_performance.R] ✖ dplyr::filter() masks stats::filter()
[S05_RF_unseen_performance.R] ✖ dplyr::lag()    masks stats::lag()
[S05_RF_unseen_performance.R] ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors
[S05_RF_unseen_performance.R] Loading required package: patchwork
[S05_RF_unseen_performance.R] Error: path does not exist
[S05_RF_unseen_performance.R] Execution halted
  ✗ FAIL  S05_RF_unseen_performance.R                    (  3.9s)  Exit code: 1
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
[S06_size_class_comparison.R] Error: path does not exist
[S06_size_class_comparison.R] Execution halted
  ✗ FAIL  S06_size_class_comparison.R                    (  3.9s)  Exit code: 1
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
[S07_distribution_parameters.R] Error: path does not exist
[S07_distribution_parameters.R] Execution halted
  ✗ FAIL  S07_distribution_parameters.R                  (  3.9s)  Exit code: 1
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
[S08_variable_importance.R] Error: path does not exist
[S08_variable_importance.R] Execution halted
  ✗ FAIL  S08_variable_importance.R                      (  3.9s)  Exit code: 1
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
[T01_area_production_tables.R] Error: path does not exist
[T01_area_production_tables.R] Execution halted
  ✗ FAIL  T01_area_production_tables.R                   (  3.9s)  Exit code: 1
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
[T02_heterogeneity_drivers.R] Error: path does not exist
[T02_heterogeneity_drivers.R] Execution halted
  ✗ FAIL  T02_heterogeneity_drivers.R                    (  3.9s)  Exit code: 1

======================================================================
TEST SUMMARY
======================================================================

  Stat   Script                                          Time(s)  Note
  ------------------------------------------------------------------------
  ✓ PASS  00_synthetic_data                                 7.0    
  ✓ PASS  00_install_packages.R                             0.0    SKIPPED (install/download script)
  ✓ PASS  00_download_spatial_data.R                        0.0    SKIPPED (install/download script)
  ✓ PASS  01.1_chirps_download.R                            1.9    
  ✗ FAIL  01.2_chirps_summarize.R                         180.0    Exit code: 124
  ✗ FAIL  01.3_chirps_trends.R                              3.8    Exit code: 1
  ✗ FAIL  01.4_prepare_spatial_layers.R                     2.9    Exit code: 1
  ✗ FAIL  02.1_compile_LSMS.R                             180.0    Exit code: 124
  ✓ PASS  02.2_harmonize_farm_area.R                        3.9    
  ✓ PASS  02.3_measured_vs_reported.R                       2.1    
  ✓ PASS  03.1_pooled_data.R                                1.2    
  ✗ FAIL  03.2_correlation_drivers.R                        8.8    Exit code: 1
  ✓ PASS  03.3_descriptive_stats.R                         19.7    
  ✓ PASS  04.1_comparing_ML_algorithms.R                    1.4    
  ✗ FAIL  04.2_RF_within_country.R                          3.8    Exit code: 1
  ✗ FAIL  04.3_RF_between_countries.R                       3.8    Exit code: 1
  ✗ FAIL  04.4_RF_model_evaluation.R                        3.7    Exit code: 1
  ✗ FAIL  04.5_cross_country_graphs.R                       0.2    Exit code: 1
  ✗ FAIL  04.6_discrepancy_analysis.R                       1.2    Exit code: 1
  ✗ FAIL  05.1_RF_optimization.R                            2.4    Exit code: 1
  ✗ FAIL  05.2_RF_optimization_summary.R                    5.0    Exit code: 1
  ✗ FAIL  05.3_RF_robustness.R                              0.2    Exit code: 1
  ✗ FAIL  06.1_quantile_RF.R                                1.4    Exit code: 1
  ✗ FAIL  06.3_prediction_maps.R                          349.7    Exit code: 1
  ✗ FAIL  06.4_cropland_sensitivity.R                       4.0    Exit code: 1
  ✗ FAIL  07.2_QRF_distribution_eval.R                      4.0    Exit code: 1
  ✗ FAIL  08.1_predictions_by_country.R                     4.0    Exit code: 1
  ✗ FAIL  08.2_generate_virtual_farms.R                     3.9    Exit code: 1
  ✗ FAIL  08.3_farm_size_classes.R                          3.9    Exit code: 1
  ✗ FAIL  09.1_AEZ_characterization.R                       3.9    Exit code: 1
  ✗ FAIL  10.1_prepare_validation_data.R                    3.9    Exit code: 1
  ✗ FAIL  10.2_external_validation.R                        3.9    Exit code: 1
  ✗ FAIL  F01_main_figure1.R                                3.9    Exit code: 1
  ✗ FAIL  F02_main_figure2.R                                3.9    Exit code: 1
  ✗ FAIL  F03_main_figure3.R                                3.9    Exit code: 1
  ✗ FAIL  S01_drivers.R                                     1.2    Exit code: 1
  ✗ FAIL  S02_cropland_uncertainty.R                        3.9    Exit code: 1
  ✗ FAIL  S03_aggregate_vs_disaggregate.R                   3.9    Exit code: 1
  ✗ FAIL  S04_RF_hyperparameters.R                          3.9    Exit code: 1
  ✗ FAIL  S05_RF_unseen_performance.R                       3.9    Exit code: 1
  ✗ FAIL  S06_size_class_comparison.R                       3.9    Exit code: 1
  ✗ FAIL  S07_distribution_parameters.R                     3.9    Exit code: 1
  ✗ FAIL  S08_variable_importance.R                         3.9    Exit code: 1
  ✗ FAIL  T01_area_production_tables.R                      3.9    Exit code: 1
  ✗ FAIL  T02_heterogeneity_drivers.R                       3.9    Exit code: 1

======================================================================
Total: 45   Passed: 9   Failed: 36   Time: 864s

Report: ../output/reports/full_pipeline_test_report.md

❌ CORE PIPELINE FAILING (3/22 core scripts passed)
```

## Pipeline Report
# Farm Size Prediction — Full Pipeline CI Report

**Generated:** 2026-03-02 15:33:23 UTC
**R Version:** R version 4.3.3 (2024-02-29)

## Summary

| Metric | Value |
|--------|-------|
| Total Scripts  | 45 |
| Passed         | 9 |
| Failed         | 36 |
| Total Time     | 864.2s |

## Per-Script Results

| Phase | Script | Status | Time | Note |
|-------|--------|--------|------|------|
| 00 | `00_synthetic_data` | ✅ PASS | 7s |  |
| 00 | `00_install_packages.R` | ✅ PASS | 0s | SKIPPED (install/download script) |
| 00 | `00_download_spatial_data.R` | ✅ PASS | 0s | SKIPPED (install/download script) |
| 01.1 | `01.1_chirps_download.R` | ✅ PASS | 1.9s |  |
| 01.2 | `01.2_chirps_summarize.R` | ❌ FAIL | 180s | Exit code: 124 |
| 01.3 | `01.3_chirps_trends.R` | ❌ FAIL | 3.8s | Exit code: 1 |
| 01.4 | `01.4_prepare_spatial_layers.R` | ❌ FAIL | 2.9s | Exit code: 1 |
| 02.1 | `02.1_compile_LSMS.R` | ❌ FAIL | 180s | Exit code: 124 |
| 02.2 | `02.2_harmonize_farm_area.R` | ✅ PASS | 3.9s |  |
| 02.3 | `02.3_measured_vs_reported.R` | ✅ PASS | 2.1s |  |
| 03.1 | `03.1_pooled_data.R` | ✅ PASS | 1.2s |  |
| 03.2 | `03.2_correlation_drivers.R` | ❌ FAIL | 8.8s | Exit code: 1 |
| 03.3 | `03.3_descriptive_stats.R` | ✅ PASS | 19.7s |  |
| 04.1 | `04.1_comparing_ML_algorithms.R` | ✅ PASS | 1.4s |  |
| 04.2 | `04.2_RF_within_country.R` | ❌ FAIL | 3.8s | Exit code: 1 |
| 04.3 | `04.3_RF_between_countries.R` | ❌ FAIL | 3.8s | Exit code: 1 |
| 04.4 | `04.4_RF_model_evaluation.R` | ❌ FAIL | 3.7s | Exit code: 1 |
| 04.5 | `04.5_cross_country_graphs.R` | ❌ FAIL | 0.2s | Exit code: 1 |
| 04.6 | `04.6_discrepancy_analysis.R` | ❌ FAIL | 1.2s | Exit code: 1 |
| 05.1 | `05.1_RF_optimization.R` | ❌ FAIL | 2.4s | Exit code: 1 |
| 05.2 | `05.2_RF_optimization_summary.R` | ❌ FAIL | 5s | Exit code: 1 |
| 05.3 | `05.3_RF_robustness.R` | ❌ FAIL | 0.2s | Exit code: 1 |
| 06.1 | `06.1_quantile_RF.R` | ❌ FAIL | 1.4s | Exit code: 1 |
| 06.3 | `06.3_prediction_maps.R` | ❌ FAIL | 349.7s | Exit code: 1 |
| 06.4 | `06.4_cropland_sensitivity.R` | ❌ FAIL | 4s | Exit code: 1 |
| 07.2 | `07.2_QRF_distribution_eval.R` | ❌ FAIL | 4s | Exit code: 1 |
| 08.1 | `08.1_predictions_by_country.R` | ❌ FAIL | 4s | Exit code: 1 |
| 08.2 | `08.2_generate_virtual_farms.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| 08.3 | `08.3_farm_size_classes.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| 09.1 | `09.1_AEZ_characterization.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| 10.1 | `10.1_prepare_validation_data.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| 10.2 | `10.2_external_validation.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| F01 | `F01_main_figure1.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| F02 | `F02_main_figure2.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| F03 | `F03_main_figure3.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| S01 | `S01_drivers.R` | ❌ FAIL | 1.2s | Exit code: 1 |
| S02 | `S02_cropland_uncertainty.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| S03 | `S03_aggregate_vs_disaggregate.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| S04 | `S04_RF_hyperparameters.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| S05 | `S05_RF_unseen_performance.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| S06 | `S06_size_class_comparison.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| S07 | `S07_distribution_parameters.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| S08 | `S08_variable_importance.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| T01 | `T01_area_production_tables.R` | ❌ FAIL | 3.9s | Exit code: 1 |
| T02 | `T02_heterogeneity_drivers.R` | ❌ FAIL | 3.9s | Exit code: 1 |
