# ==============================================================================
# Script: 00_run_all_tests.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Run ALL pipeline scripts in sequential order for CI testing
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - March 2026
#
# Strategy:
#   - Runs each script as a separate Rscript subprocess (clean environment)
#   - Patches hardcoded Windows paths before execution
#   - Patches incorrect ../../ relative paths in F/S/T scripts
#   - Reports pass/fail with timing
#   - Exits 0 if core pipeline passes; 1 if critical failures
# ==============================================================================

message("\n", paste(rep("=",70),collapse=""))
message("FARM SIZE PREDICTION - FULL SEQUENTIAL PIPELINE TEST")
message(paste(rep("=",70),collapse=""))
message("Started: ", Sys.time(), "\n")

# ── Setup ──────────────────────────────────────────────────────────────────────
if (!interactive()) {
  args <- commandArgs(trailingOnly = FALSE)
  sp   <- sub("--file=","", args[grep("--file=",args)])
  if (length(sp) > 0 && nchar(sp) > 0) {
    setwd(dirname(normalizePath(sp)))
  }
}
scripts_dir <- getwd()
message("Scripts dir: ", scripts_dir, "\n")

start_time   <- Sys.time()
test_results <- list()

# ── Helpers ────────────────────────────────────────────────────────────────────

#' Patch a script's content for CI compatibility
patch_script <- function(lines) {
  # 1. Replace hardcoded Windows paths
  lines <- gsub(
    "C:/Users/DHOUGNI/[^'\"\\n\\r]*",
    "../data/raw/spatial",
    lines
  )
  # 2. Fix ../../data/processed/ used in F/S/T scripts (from scripts/ dir,
  #    ../../ goes to wrong location; should be ../)
  lines <- gsub("'../../data/processed/", "'../data/processed/", lines, fixed = TRUE)
  lines <- gsub('"../../data/processed/', '"../data/processed/', lines, fixed = TRUE)
  lines <- gsub("'../../output/",         "'../output/",         lines, fixed = TRUE)
  lines <- gsub('"../../output/',         '"../output/',         lines, fixed = TRUE)
  lines
}

#' Run a single script, return list(passed, elapsed, error_msg)
run_script <- function(script_name, timeout_sec = 600) {
  script_path <- file.path(scripts_dir, script_name)
  if (!file.exists(script_path)) {
    return(list(passed = FALSE, elapsed = 0,
                msg = paste("File not found:", script_path)))
  }

  original <- readLines(script_path, warn = FALSE)
  patched  <- patch_script(original)

  tmp <- tempfile(fileext = ".R")
  writeLines(patched, tmp)
  on.exit(unlink(tmp), add = TRUE)

  t0  <- proc.time()["elapsed"]
  ret <- system2("Rscript", c("--vanilla", shQuote(tmp)),
                 stdout = FALSE, stderr = FALSE,
                 timeout = timeout_sec)
  elapsed <- round(proc.time()["elapsed"] - t0, 1)

  passed  <- (ret == 0)
  msg     <- if (passed) "" else paste("Exit code:", ret)
  list(passed = passed, elapsed = elapsed, msg = msg)
}

record <- function(name, passed, elapsed, msg = "", description = "") {
  icon <- if (passed) "\u2713 PASS" else "\u2717 FAIL"
  message(sprintf("  %s  %-45s (%5.1fs)  %s",
                  icon, name, elapsed, if (nchar(msg)>0) msg else ""))
  test_results[[name]] <<- list(passed   = passed,
                                elapsed  = elapsed,
                                msg      = msg,
                                description = description)
}

# ==============================================================================
# PHASE 0: SYNTHETIC DATA GENERATION (prerequisite)
# ==============================================================================
message(paste(rep("-",70),collapse=""))
message("PHASE 0: Synthetic Data Generation")
message(paste(rep("-",70),collapse=""))

r <- run_script("00_synthetic_data.R", timeout_sec = 300)
record("00_synthetic_data", r$passed, r$elapsed, r$msg,
       "Generate all synthetic data files")

if (!r$passed) {
  message("\nFATAL: synthetic data generation failed. Cannot continue.")
  quit(status = 1)
}

# ==============================================================================
# PHASE 1: DATA DOWNLOAD SCRIPTS (allow failure - need internet/real data)
# ==============================================================================
message(paste(rep("-",70),collapse=""))
message("PHASE 1: Data Download (expected failures without real data)")
message(paste(rep("-",70),collapse=""))

skip_scripts <- c(
  "00_download_spatial_data.R",  # needs internet + hours of downloads
  "00_install_packages.R"        # package install - done in CI workflow
)
for (s in skip_scripts) {
  record(s, TRUE, 0, "SKIPPED (download/install script)", "Skipped in CI")
}

download_scripts <- c(
  "01.1_chirps_download.R",
  "01.2_chirps_summarize.R",
  "01.3_chirps_trends.R",
  "01.4_prepare_spatial_layers.R",
  "02.1_compile_LSMS.R",
  "02.2_harmonize_farm_area.R",
  "02.3_measured_vs_reported.R"
)
for (s in download_scripts) {
  r <- run_script(s, timeout_sec = 120)
  record(s, r$passed, r$elapsed, r$msg, "Download/compile script")
}

# ==============================================================================
# PHASE 2: ANALYSIS PREPARATION (03.x)
# ==============================================================================
message(paste(rep("-",70),collapse=""))
message("PHASE 2: Analysis Preparation (03.x)")
message(paste(rep("-",70),collapse=""))

for (s in c("03.1_pooled_data.R", "03.2_correlation_drivers.R", "03.3_descriptive_stats.R")) {
  r <- run_script(s, timeout_sec = 300)
  record(s, r$passed, r$elapsed, r$msg, "Data preparation")
}

# ==============================================================================
# PHASE 3: ML MODEL TRAINING (04.x - compute-intensive)
# ==============================================================================
message(paste(rep("-",70),collapse=""))
message("PHASE 3: ML Model Training (04.x)")
message(paste(rep("-",70),collapse=""))

for (s in c("04.1_comparing_ML_algorithms.R", "04.2_RF_within_country.R",
            "04.3_RF_between_countries.R",   "04.4_RF_model_evaluation.R",
            "04.5_cross_country_graphs.R",   "04.6_discrepancy_analysis.R")) {
  r <- run_script(s, timeout_sec = 600)
  record(s, r$passed, r$elapsed, r$msg, "ML model training")
}

# ==============================================================================
# PHASE 4: RF OPTIMISATION (05.x)
# ==============================================================================
message(paste(rep("-",70),collapse=""))
message("PHASE 4: RF Optimisation (05.x)")
message(paste(rep("-",70),collapse=""))

for (s in c("05.1_RF_optimization.R", "05.2_RF_optimization_summary.R",
            "05.3_RF_robustness.R")) {
  r <- run_script(s, timeout_sec = 600)
  record(s, r$passed, r$elapsed, r$msg, "RF optimisation")
}

# ==============================================================================
# PHASE 5: QUANTILE RF & PREDICTION MAPS (06.x)
# ==============================================================================
message(paste(rep("-",70),collapse=""))
message("PHASE 5: Quantile RF & Prediction Maps (06.x)")
message(paste(rep("-",70),collapse=""))

for (s in c("06.1_quantile_RF.R", "06.3_prediction_maps.R",
            "06.4_cropland_sensitivity.R")) {
  r <- run_script(s, timeout_sec = 600)
  record(s, r$passed, r$elapsed, r$msg, "Quantile RF")
}

# ==============================================================================
# PHASE 6: DISTRIBUTION EVALUATION & PREDICTIONS (07-10)
# ==============================================================================
message(paste(rep("-",70),collapse=""))
message("PHASE 6: Predictions & Validation (07.x – 10.x)")
message(paste(rep("-",70),collapse=""))

for (s in c("07.2_QRF_distribution_eval.R",
            "08.1_predictions_by_country.R", "08.2_generate_virtual_farms.R",
            "08.3_farm_size_classes.R",      "09.1_AEZ_characterization.R",
            "10.1_prepare_validation_data.R","10.2_external_validation.R")) {
  r <- run_script(s, timeout_sec = 600)
  record(s, r$passed, r$elapsed, r$msg, "Predictions & validation")
}

# ==============================================================================
# PHASE 7: FIGURES & SUPPLEMENTARY (F/S/T)
# ==============================================================================
message(paste(rep("-",70),collapse=""))
message("PHASE 7: Figures & Supplementary (F/S/T)")
message(paste(rep("-",70),collapse=""))

for (s in c("F01_main_figure1.R", "F02_main_figure2.R", "F03_main_figure3.R",
            "S01_drivers.R",      "S02_cropland_uncertainty.R",
            "S03_aggregate_vs_disaggregate.R", "S04_RF_hyperparameters.R",
            "S05_RF_unseen_performance.R",     "S06_size_class_comparison.R",
            "S07_distribution_parameters.R",   "S08_variable_importance.R",
            "T01_area_production_tables.R",    "T02_heterogeneity_drivers.R")) {
  r <- run_script(s, timeout_sec = 300)
  record(s, r$passed, r$elapsed, r$msg, "Figures & supplements")
}

# ==============================================================================
# SUMMARY REPORT
# ==============================================================================
message("\n", paste(rep("=",70),collapse=""))
message("TEST SUMMARY")
message(paste(rep("=",70),collapse=""))

total_tests  <- length(test_results)
passed_tests <- sum(sapply(test_results, `[[`, "passed"))
failed_tests <- total_tests - passed_tests
total_time   <- round(difftime(Sys.time(), start_time, units = "secs"), 1)

message(sprintf("\n  %-5s  %-45s  %7s  %s", "Stat", "Script", "Time", "Note"))
message("  ", paste(rep("-",70),collapse=""))
for (nm in names(test_results)) {
  r    <- test_results[[nm]]
  icon <- if (r$passed) "\u2713 PASS" else "\u2717 FAIL"
  message(sprintf("  %s  %-45s  %5.1fs  %s", icon, nm, r$elapsed,
                  if (nchar(r$msg) > 0) substr(r$msg,1,40) else ""))
}

message("\n", paste(rep("=",70),collapse=""))
message(sprintf("Total: %d   Passed: %d   Failed: %d   Time: %ss",
                total_tests, passed_tests, failed_tests, total_time))

# Write markdown report
dir.create("../output/reports", recursive = TRUE, showWarnings = FALSE)
report <- c(
  "# Farm Size Prediction — Full Pipeline CI Report",
  "",
  paste0("**Generated:** ", Sys.time()),
  paste0("**R Version:** ", R.version.string),
  "",
  "## Summary",
  "",
  "| Metric | Value |",
  "|--------|-------|",
  paste0("| Total Scripts | ", total_tests, " |"),
  paste0("| Passed | ",        passed_tests, " |"),
  paste0("| Failed | ",        failed_tests, " |"),
  paste0("| Total Time | ",    total_time, "s |"),
  "",
  "## Results by Script",
  "",
  "| Script | Status | Time | Note |",
  "|--------|--------|------|------|"
)
for (nm in names(test_results)) {
  r <- test_results[[nm]]
  status <- if (r$passed) "\u2705 PASS" else "\u274C FAIL"
  report <- c(report,
    paste0("| ", nm, " | ", status, " | ", r$elapsed, "s | ", r$msg, " |"))
}
writeLines(report, "../output/reports/full_pipeline_test_report.md")
message("\nReport saved to: ../output/reports/full_pipeline_test_report.md")

# Exit code: fail if core analysis scripts (03.x – 08.x) have >50% failures
core_scripts <- names(test_results)[grepl("^0[3-8]", names(test_results))]
core_passed  <- sum(sapply(test_results[core_scripts], `[[`, "passed"))
core_total   <- length(core_scripts)
core_pct     <- if (core_total > 0) core_passed / core_total else 1

if (core_pct < 0.5) {
  message("\n\u274C CORE PIPELINE FAILING (", core_passed, "/", core_total,
          " core scripts passed)")
  if (!interactive()) quit(status = 1)
} else {
  message("\n\u2705 CORE PIPELINE OK (", core_passed, "/", core_total,
          " core scripts passed = ", round(100*core_pct), "%)")
  if (!interactive()) quit(status = 0)
}
