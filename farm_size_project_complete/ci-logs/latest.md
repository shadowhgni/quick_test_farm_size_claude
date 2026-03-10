# CI Run Log
Run: 22895566598  Commit: c827e4a54969668f602a04e1377affbebadee876  Time: Tue Mar 10 09:34:18 UTC 2026

## Raw Output
```

======================================================================
FARM SIZE PREDICTION - FULL SEQUENTIAL PIPELINE TEST
======================================================================
Started: 2026-03-10 09:24:15.486323

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
[00_synthetic_data.R]    Leave-one stubs done  (32 countries × 2 models).
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
  ✓ PASS  00_synthetic_data                              (  7.2s)  
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
[01.1_chirps_download.R] Finished: 2026-03-10 09:24:24.651233
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
[01.2_chirps_summarize.R] Downloaded: 650 files...
[01.2_chirps_summarize.R] Downloaded: 700 files...
[01.2_chirps_summarize.R] Downloaded: 750 files...
[01.2_chirps_summarize.R] Downloaded: 800 files...
[01.2_chirps_summarize.R] Downloaded: 850 files...
[01.2_chirps_summarize.R] Downloaded: 900 files...
[01.2_chirps_summarize.R] Downloaded: 950 files...
[01.2_chirps_summarize.R] Downloaded: 1000 files...
[01.2_chirps_summarize.R] Downloaded: 1050 files...
[01.2_chirps_summarize.R] Downloaded: 1100 files...
[01.2_chirps_summarize.R] Downloaded: 1150 files...
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
  ✗ FAIL  01.3_chirps_trends.R                           (  4.3s)  Exit code: 1
[01.4_prepare_spatial_layers.R] Loading required package: terra
[01.4_prepare_spatial_layers.R] terra 1.8.93
[01.4_prepare_spatial_layers.R] === Loading yearly rainfall data ===
[01.4_prepare_spatial_layers.R] Error: No yearly rainfall files found in: ../data/raw/spatial/rainfall/rainfall_yearly
[01.4_prepare_spatial_layers.R] Execution halted
  ✗ FAIL  01.4_prepare_spatial_layers.R                  (  2.9s)  Exit code: 1
[02.1_compile_LSMS.R] Content type 'unknown' length 3273875 bytes (3.1 MB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 3.1 MB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   Madagascar: level 3
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_MDG_3_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 5350121 bytes (5.1 MB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 5.1 MB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   Madagascar: level 4
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_MDG_4_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 14789348 bytes (14.1 MB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 14.1 MB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   Madagascar: level 5
[02.1_compile_LSMS.R] gadm41_MDG_5_pk.rds - this file does not exist
[02.1_compile_LSMS.R]   Mali: level 1
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_MLI_1_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 203000 bytes (198 KB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 198 KB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   Mali: level 2
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_MLI_2_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 416290 bytes (406 KB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 406 KB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   Mali: level 3
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_MLI_3_pk.rds'
[02.1_compile_LSMS.R] Content type 'unknown' length 805447 bytes (786 KB)
[02.1_compile_LSMS.R] ==================================================
[02.1_compile_LSMS.R] downloaded 786 KB
[02.1_compile_LSMS.R] 
[02.1_compile_LSMS.R]   Mali: level 4
[02.1_compile_LSMS.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_MLI_4_pk.rds'
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
  ✓ PASS  02.3_measured_vs_reported.R                    (  2.2s)  
Warning messages:
1: In system2("Rscript", c("--vanilla", shQuote(tmp)), stdout = log_file,  :
  command ''Rscript' --vanilla '/tmp/RtmpLzOtdt/file19d42c86f29f.R' > '/tmp/RtmpLzOtdt/file19d4234c6655.log' 2>&1' timed out after 180s
2: In system2("Rscript", c("--vanilla", shQuote(tmp)), stdout = log_file,  :
  command ''Rscript' --vanilla '/tmp/RtmpLzOtdt/file19d45832cf2e.R' > '/tmp/RtmpLzOtdt/file19d439a271af.log' 2>&1' timed out after 180s
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
[03.2_correlation_drivers.R]   Downloaded: Togo (level 3)
[03.2_correlation_drivers.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_UGA_4_pk.rds'
[03.2_correlation_drivers.R] Content type 'unknown' length 13445867 bytes (12.8 MB)
[03.2_correlation_drivers.R] ==================================================
[03.2_correlation_drivers.R] downloaded 12.8 MB
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R]   Downloaded: Uganda (level 4)
[03.2_correlation_drivers.R] trying URL 'https://geodata.ucdavis.edu/gadm/gadm4.1/pck/gadm41_ZMB_2_pk.rds'
[03.2_correlation_drivers.R] Content type 'unknown' length 2425218 bytes (2.3 MB)
[03.2_correlation_drivers.R] ==================================================
[03.2_correlation_drivers.R] downloaded 2.3 MB
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R]   Downloaded: Zambia (level 2)
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Loading predictor layers ===
[03.2_correlation_drivers.R] Predictor layers: cropland, cattle, pop, cropland_per_capita, sand, elevation, slope, temperature, rainfall, market, maizeyield
[03.2_correlation_drivers.R] 
[03.2_correlation_drivers.R] === Loading LSMS data ===
[03.2_correlation_drivers.R] Initial farms: 4291
[03.2_correlation_drivers.R] After year filter (>2007): 4291
[03.2_correlation_drivers.R] Excluding small waves: 
[03.2_correlation_drivers.R] # A tibble: 96 × 3
[03.2_correlation_drivers.R]    country  year n_farms
[03.2_correlation_drivers.R]    <chr>   <int>   <int>
[03.2_correlation_drivers.R]  1 Benin    2010      56
[03.2_correlation_drivers.R]  2 Benin    2012      58
[03.2_correlation_drivers.R]  3 Benin    2014      54
[03.2_correlation_drivers.R]  4 Benin    2016      55
[03.2_correlation_drivers.R]  5 Benin    2018      46
[03.2_correlation_drivers.R]  6 Benin    2020      44
[03.2_correlation_drivers.R]  7 Burkina  2010      42
[03.2_correlation_drivers.R]  8 Burkina  2012      48
[03.2_correlation_drivers.R]  9 Burkina  2014      47
[03.2_correlation_drivers.R] 10 Burkina  2016      55
[03.2_correlation_drivers.R] # ℹ 86 more rows
[03.2_correlation_drivers.R] After sample size filter: 0
[03.2_correlation_drivers.R] Error in `$<-.data.frame`(`*tmp*`, farm_id, value = "__") : 
[03.2_correlation_drivers.R]   replacement has 1 row, data has 0
[03.2_correlation_drivers.R] Calls: $<- -> $<-.data.frame
[03.2_correlation_drivers.R] Execution halted
  ✗ FAIL  03.2_correlation_drivers.R                     ( 33.3s)  Exit code: 1
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
  ✓ PASS  03.3_descriptive_stats.R                       ( 19.3s)  
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
[04.2_RF_within_country.R] fields::Tps(x = with(my_lsms_cty, cbind(x, y)), Y = my_lsms_cty[, 
[04.2_RF_within_country.R]     "farm_area_ha"], lon.lat = T, Z = as.matrix(my_lsms_cty[, 
[04.2_RF_within_country.R]     c("cropland", "cattle", "pop", "cropland_per_capita", "sand", 
[04.2_RF_within_country.R]         "slope", "temperature", "rainfall", "market", "maizeyield")]))
[04.2_RF_within_country.R]                                                  
[04.2_RF_within_country.R]  Number of Observations:                277      
[04.2_RF_within_country.R]  Number of parameters in the null space 13       
[04.2_RF_within_country.R]  Parameters for fixed spatial drift     3        
[04.2_RF_within_country.R]  Model degrees of freedom:              13       
[04.2_RF_within_country.R]  Residual degrees of freedom:           264      
[04.2_RF_within_country.R]  GCV estimate for tau:                  0.9513   
[04.2_RF_within_country.R]  MLE for tau:                           0.9287   
[04.2_RF_within_country.R]  MLE for sigma:                         3.489e-07
[04.2_RF_within_country.R]  lambda                                 2500000  
[04.2_RF_within_country.R]  User supplied sigma                    NA       
[04.2_RF_within_country.R]  User supplied tau^2                    NA       
[04.2_RF_within_country.R] Summary of estimates: 
[04.2_RF_within_country.R]             lambda      trA       GCV    tauHat -lnLike Prof converge
[04.2_RF_within_country.R] GCV        2472098 13.00101 0.9495958 0.9513288     361.4279       NA
[04.2_RF_within_country.R] GCV.model       NA       NA        NA        NA           NA       NA
[04.2_RF_within_country.R] GCV.one    2472098 13.00101 0.9495958 0.9513288           NA       NA
[04.2_RF_within_country.R] RMSE            NA       NA        NA        NA           NA       NA
[04.2_RF_within_country.R] pure error      NA       NA        NA        NA           NA       NA
[04.2_RF_within_country.R] REML       2472098 13.00101 0.9495958 0.9513288     361.4279       NA
[04.2_RF_within_country.R] [1] "calculated_70-30_r2 = 0.05"
[04.2_RF_within_country.R] [1] "CV_r2 = NA"
[04.2_RF_within_country.R] [1] "TPS_rsq_with_covariate = NA"
[04.2_RF_within_country.R] [1] NA
[04.2_RF_within_country.R] Something is wrong; all the Rsquared metric values are missing:
[04.2_RF_within_country.R]       RMSE        Rsquared        MAE     
[04.2_RF_within_country.R]  Min.   : NA   Min.   : NA   Min.   : NA  
[04.2_RF_within_country.R]  1st Qu.: NA   1st Qu.: NA   1st Qu.: NA  
[04.2_RF_within_country.R]  Median : NA   Median : NA   Median : NA  
[04.2_RF_within_country.R]  Mean   :NaN   Mean   :NaN   Mean   :NaN  
[04.2_RF_within_country.R]  3rd Qu.: NA   3rd Qu.: NA   3rd Qu.: NA  
[04.2_RF_within_country.R]  Max.   : NA   Max.   : NA   Max.   : NA  
[04.2_RF_within_country.R]  NA's   :108   NA's   :108   NA's   :108  
[04.2_RF_within_country.R] Error: Stopping
[04.2_RF_within_country.R] In addition: There were 50 or more warnings (use warnings() to see the first 50)
[04.2_RF_within_country.R] Execution halted
  ✗ FAIL  04.2_RF_within_country.R                       ( 18.4s)  Exit code: 1
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
[04.3_RF_between_countries.R] Time difference of 1.231978 secs
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
[04.4_RF_model_evaluation.R] `summarise()` has regrouped the output.
[04.4_RF_model_evaluation.R] ℹ Summaries were computed grouped by country, x, and y.
[04.4_RF_model_evaluation.R] ℹ Output is grouped by country and x.
[04.4_RF_model_evaluation.R] ℹ Use `summarise(.groups = "drop_last")` to silence this message.
[04.4_RF_model_evaluation.R] ℹ Use `summarise(.by = c(country, x, y))` for per-operation grouping
[04.4_RF_model_evaluation.R]   (`?dplyr::dplyr_by`) instead.
[04.4_RF_model_evaluation.R] Joining with `by = join_by(x, y, country)`
[04.4_RF_model_evaluation.R] [1] "--------------------Benin---------------------------"
[04.4_RF_model_evaluation.R] Loading required package: lattice
[04.4_RF_model_evaluation.R] 
[04.4_RF_model_evaluation.R] Attaching package: ‘caret’
[04.4_RF_model_evaluation.R] 
[04.4_RF_model_evaluation.R] The following object is masked from ‘package:purrr’:
[04.4_RF_model_evaluation.R] 
[04.4_RF_model_evaluation.R]     lift
[04.4_RF_model_evaluation.R] 
[04.4_RF_model_evaluation.R] Error: Every row has at least one missing value were found
[04.4_RF_model_evaluation.R] Execution halted
  ✗ FAIL  04.4_RF_model_evaluation.R                     (  9.5s)  Exit code: 1
[04.5_cross_country_graphs.R] Error in gzfile(file, "rb") : invalid 'description' argument
[04.5_cross_country_graphs.R] Calls: summarize -> sapply -> lapply -> FUN -> readRDS -> gzfile
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
[04.6_discrepancy_analysis.R] `summarise()` has regrouped the output.
[04.6_discrepancy_analysis.R] ℹ Summaries were computed grouped by country, code, and model.
[04.6_discrepancy_analysis.R] ℹ Output is grouped by country and code.
[04.6_discrepancy_analysis.R] ℹ Use `summarise(.groups = "drop_last")` to silence this message.
[04.6_discrepancy_analysis.R] ℹ Use `summarise(.by = c(country, code, model))` for per-operation grouping
[04.6_discrepancy_analysis.R]   (`?dplyr::dplyr_by`) instead.
[04.6_discrepancy_analysis.R] Error in gzfile(file, "rb") : cannot open the connection
[04.6_discrepancy_analysis.R] Calls: cor -> is.data.frame -> readRDS -> gzfile
[04.6_discrepancy_analysis.R] In addition: Warning message:
[04.6_discrepancy_analysis.R] In gzfile(file, "rb") :
[04.6_discrepancy_analysis.R]   cannot open compressed file '../output/leave_one/loc_TZA_TPS_means_test.rds', probable reason 'No such file or directory'
[04.6_discrepancy_analysis.R] Execution halted
  ✗ FAIL  04.6_discrepancy_analysis.R                    (  1.3s)  Exit code: 1
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
  ✓ PASS  05.1_RF_optimization.R                         (  3.8s)  
```

## Pipeline Report
(report not generated)
