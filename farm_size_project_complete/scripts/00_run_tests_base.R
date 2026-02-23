# ==============================================================================
# Script: 00_run_all_tests.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Run all scripts with synthetic data and validate outputs
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - February 2026
#
# Description:
#   This script orchestrates the complete test suite:
#   1. Generates synthetic data
#   2. Runs each script in the pipeline
#   3. Validates outputs
#   4. Generates a test report
#
# Usage:
#   Rscript scripts/00_run_all_tests.R
#   # Or in R:
#   source("scripts/00_run_all_tests.R")
#
# Exit Codes:
#   0 - All tests passed
#   1 - One or more tests failed
# ==============================================================================

# ------------------------------------------------------------------------------
# SETUP
# ------------------------------------------------------------------------------
message("\n")
message(paste(rep("=", 70), collapse = ""))
message("FARM SIZE PREDICTION - AUTOMATED TEST SUITE")
message(paste(rep("=", 70), collapse = ""))
message("Started: ", Sys.time())
message("")

# Track test results
test_results <- list()
start_time <- Sys.time()

#' Run a script and track results
#' @param script_name Name of script file
#' @param description Description of what script does
#' @return TRUE if passed, FALSE if failed
run_test <- function(script_name, description) {
  message("\n--- Testing: ", script_name, " ---")
  message("Description: ", description)
  
  script_start <- Sys.time()
  
  result <- tryCatch({
    source(script_name, local = new.env())
    TRUE
  }, error = function(e) {
    message("ERROR: ", e$message)
    FALSE
  }, warning = function(w) {
    message("WARNING: ", w$message)
    TRUE  # Warnings don't fail the test
  })
  
  elapsed <- round(difftime(Sys.time(), script_start, units = "secs"), 1)
  
  if (result) {
    message("✓ PASSED (", elapsed, "s)")
  } else {
    message("✗ FAILED (", elapsed, "s)")
  }
  
  test_results[[script_name]] <<- list(
    passed = result,
    time = elapsed,
    description = description
  )
  
  return(result)
}

#' Validate that a file exists and has content
#' @param filepath Path to file
#' @param min_size Minimum file size in bytes
#' @return TRUE if valid
validate_file <- function(filepath, min_size = 100) {
  if (!file.exists(filepath)) {
    message("  ✗ Missing: ", filepath)
    return(FALSE)
  }
  
  size <- file.info(filepath)$size
  if (size < min_size) {
    message("  ✗ Too small (", size, " bytes): ", filepath)
    return(FALSE)
  }
  
  message("  ✓ ", basename(filepath), " (", format(size, big.mark = ","), " bytes)")
  return(TRUE)
}

# ------------------------------------------------------------------------------
# SET WORKING DIRECTORY
# ------------------------------------------------------------------------------
# Handle different execution contexts
if (interactive()) {
  # Running in RStudio or R console
  if (file.exists("scripts/00_synthetic_data.R")) {
    setwd("scripts")
  }
} else {
  # Running via Rscript
  args <- commandArgs(trailingOnly = FALSE)
  script_path <- sub("--file=", "", args[grep("--file=", args)])
  if (length(script_path) > 0) {
    setwd(dirname(script_path))
  }
}

message("Working directory: ", getwd())

# ------------------------------------------------------------------------------
# PHASE 1: GENERATE SYNTHETIC DATA
# ------------------------------------------------------------------------------
message("\n")
message(paste(rep("-", 70), collapse = ""))
message("PHASE 1: SYNTHETIC DATA GENERATION")
message(paste(rep("-", 70), collapse = ""))

run_test("00_synthetic_data.R", "Generate synthetic spatial and survey data")

# Validate synthetic data
message("\nValidating synthetic data files...")
synthetic_files <- c(
  "../data/processed/all_predictors.tif",
  "../data/processed/stacked_rasters_africa.tif",
  "../data/processed/lsms_and_zambia.csv",
  "../data/processed/lsms_trimmed_95th_africa.rds",
  "../data/processed/lsms_spatial.csv"
)

for (f in synthetic_files) {
  validate_file(f)
}

# ------------------------------------------------------------------------------
# PHASE 2: TEST DATA PROCESSING SCRIPTS
# ------------------------------------------------------------------------------
message("\n")
message(paste(rep("-", 70), collapse = ""))
message("PHASE 2: DATA PROCESSING SCRIPTS")
message(paste(rep("-", 70), collapse = ""))

# Test 03.2: Correlation analysis
run_test("03.2_correlation_drivers.R", "Analyze predictor correlations")

# Test 03.3: Descriptive statistics
run_test("03.3_descriptive_stats.R", "Generate descriptive statistics table")

# Validate outputs
message("\nValidating output files...")
output_files <- c(
  "../output/graphs/drivers_correlation_matrix.png",
  "../output/tables/summary_descriptive_stats_survey.csv"
)

for (f in output_files) {
  validate_file(f)
}

# ------------------------------------------------------------------------------
# PHASE 3: DATA INTEGRITY CHECKS
# ------------------------------------------------------------------------------
message("\n")
message(paste(rep("-", 70), collapse = ""))
message("PHASE 3: DATA INTEGRITY CHECKS")
message(paste(rep("-", 70), collapse = ""))

message("\nChecking LSMS data integrity...")
tryCatch({
  lsms <- readRDS("../data/processed/lsms_trimmed_95th_africa.rds")
  
  # Check structure
  required_cols <- c("x", "y", "country", "year", "farm_id", "farm_area_ha",
                     "cropland", "cattle", "pop", "temperature", "rainfall")
  
  missing_cols <- required_cols[!required_cols %in% names(lsms)]
  if (length(missing_cols) > 0) {
    stop("Missing columns: ", paste(missing_cols, collapse = ", "))
  }
  message("  ✓ All required columns present")
  
  # Check values
  stopifnot("Farm areas must be positive" = all(lsms$farm_area_ha > 0))
  message("  ✓ All farm areas positive")
  
  stopifnot("Coordinates in valid range" = all(lsms$x >= -180 & lsms$x <= 180))
  stopifnot("Coordinates in valid range" = all(lsms$y >= -90 & lsms$y <= 90))
  message("  ✓ Coordinates in valid range")
  
  stopifnot("Multiple countries" = length(unique(lsms$country)) > 5)
  message("  ✓ Multiple countries present (", length(unique(lsms$country)), ")")
  
  test_results[["data_integrity"]] <- list(passed = TRUE, time = 0, 
                                            description = "Data integrity checks")
  message("✓ All integrity checks passed")
  
}, error = function(e) {
  message("✗ Data integrity check failed: ", e$message)
  test_results[["data_integrity"]] <<- list(passed = FALSE, time = 0,
                                             description = "Data integrity checks")
})

# Check raster stack
message("\nChecking raster stack integrity...")
tryCatch({
  stacked <- terra::rast("../data/processed/stacked_rasters_africa.tif")
  
  stopifnot("Has multiple layers" = terra::nlyr(stacked) >= 10)
  message("  ✓ Raster has ", terra::nlyr(stacked), " layers")
  
  stopifnot("CRS is defined" = !is.na(terra::crs(stacked)))
  message("  ✓ CRS is defined")
  
  stopifnot("Has valid extent" = all(is.finite(as.vector(terra::ext(stacked)))))
  message("  ✓ Extent is valid")
  
  test_results[["raster_integrity"]] <- list(passed = TRUE, time = 0,
                                              description = "Raster integrity checks")
  message("✓ Raster integrity checks passed")
  
}, error = function(e) {
  message("✗ Raster integrity check failed: ", e$message)
  test_results[["raster_integrity"]] <<- list(passed = FALSE, time = 0,
                                               description = "Raster integrity checks")
})

# ------------------------------------------------------------------------------
# SUMMARY REPORT
# ------------------------------------------------------------------------------
message("\n")
message(paste(rep("=", 70), collapse = ""))
message("TEST SUMMARY")
message(paste(rep("=", 70), collapse = ""))

total_tests <- length(test_results)
passed_tests <- sum(sapply(test_results, function(x) x$passed))
failed_tests <- total_tests - passed_tests
total_time <- round(difftime(Sys.time(), start_time, units = "secs"), 1)

message("\nResults:")
for (name in names(test_results)) {
  result <- test_results[[name]]
  status <- ifelse(result$passed, "✓ PASS", "✗ FAIL")
  message(sprintf("  %s  %-40s (%ss)", status, name, result$time))
}

message("\n")
message("Total tests: ", total_tests)
message("Passed:      ", passed_tests)
message("Failed:      ", failed_tests)
message("Total time:  ", total_time, "s")
message("")

# Generate markdown report
report_path <- "../output/reports/test_report.md"
dir.create(dirname(report_path), recursive = TRUE, showWarnings = FALSE)

report <- paste0(
  "# Farm Size Prediction - Test Report\n\n",
  "**Generated:** ", Sys.time(), "\n",
  "**R Version:** ", R.version.string, "\n",
  "**Platform:** ", R.version$platform, "\n\n",
  "## Summary\n\n",
  "| Metric | Value |\n",
  "|--------|-------|\n",
  "| Total Tests | ", total_tests, " |\n",
  "| Passed | ", passed_tests, " |\n",
  "| Failed | ", failed_tests, " |\n",
  "| Total Time | ", total_time, "s |\n\n",
  "## Test Results\n\n",
  "| Test | Status | Time | Description |\n",
  "|------|--------|------|-------------|\n"
)

for (name in names(test_results)) {
  result <- test_results[[name]]
  status <- ifelse(result$passed, "✅ PASS", "❌ FAIL")
  report <- paste0(report, "| ", name, " | ", status, " | ", 
                   result$time, "s | ", result$description, " |\n")
}

report <- paste0(report, "\n## Data Summary\n\n")

if (file.exists("../data/processed/lsms_trimmed_95th_africa.rds")) {
  lsms <- readRDS("../data/processed/lsms_trimmed_95th_africa.rds")
  report <- paste0(report,
    "- **Farms:** ", format(nrow(lsms), big.mark = ","), "\n",
    "- **Countries:** ", length(unique(lsms$country)), "\n",
    "- **Farm size range:** ", round(min(lsms$farm_area_ha), 2), 
    " - ", round(max(lsms$farm_area_ha), 2), " ha\n",
    "- **Median farm size:** ", round(median(lsms$farm_area_ha), 2), " ha\n"
  )
}

writeLines(report, report_path)
message("Test report saved to: ", report_path)

# Exit with appropriate code
if (failed_tests > 0) {
  message("\n❌ SOME TESTS FAILED")
  if (!interactive()) quit(status = 1)
} else {
  message("\n✅ ALL TESTS PASSED")
  if (!interactive()) quit(status = 0)
}

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
