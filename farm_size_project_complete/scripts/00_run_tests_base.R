# ==============================================================================
# Script: 00_run_tests_base.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Lightweight CI test suite using BASE R ONLY
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - March 2026
#
# Description:
#   Validates outputs produced by 00_synthetic_data_base.R.
#   Zero external package dependencies - uses only base R.
#
# Exit Codes:
#   0 - All tests passed
#   1 - One or more tests failed
# ==============================================================================

message("\n", paste(rep("=", 70), collapse = ""))
message("FARM SIZE PREDICTION - BASE R TEST SUITE")
message(paste(rep("=", 70), collapse = ""))
message("Started: ", Sys.time(), "\n")

test_results <- list()
start_time   <- Sys.time()

# ------------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------------

record <- function(name, passed, description, elapsed = 0) {
  status <- if (passed) "\u2713 PASS" else "\u2717 FAIL"
  message(sprintf("  %s  %-45s (%ss)", status, name, round(elapsed, 1)))
  test_results[[name]] <<- list(passed = passed, time = elapsed,
                                description = description)
}

validate_file <- function(path, min_bytes = 100) {
  if (!file.exists(path)) {
    message("    \u2717 Missing: ", path)
    return(FALSE)
  }
  sz <- file.info(path)$size
  if (sz < min_bytes) {
    message("    \u2717 Too small (", sz, " bytes): ", path)
    return(FALSE)
  }
  message("    \u2713 ", basename(path), " (", format(sz, big.mark = ","), " bytes)")
  TRUE
}

# ------------------------------------------------------------------------------
# SET WORKING DIRECTORY
# ------------------------------------------------------------------------------
if (!interactive()) {
  args        <- commandArgs(trailingOnly = FALSE)
  script_path <- sub("--file=", "", args[grep("--file=", args)])
  if (length(script_path) > 0 && nchar(script_path) > 0)
    setwd(dirname(normalizePath(script_path)))
}
message("Working directory: ", getwd(), "\n")

# ------------------------------------------------------------------------------
# TEST 1: SYNTHETIC DATA FILES EXIST
# ------------------------------------------------------------------------------
message(paste(rep("-", 70), collapse = ""))
message("TEST 1: Required output files exist")
message(paste(rep("-", 70), collapse = ""))

t_start <- Sys.time()
required_files <- c(
  "../data/processed/raster_grid_africa.rds",
  "../data/processed/lsms_and_zambia.csv",
  "../data/processed/lsms_trimmed_95th_africa.rds",
  "../data/processed/lsms_trimmed_99th_africa.rds",
  "../data/processed/lsms_spatial.csv",
  "../data/processed/lsms_spatial_africa.Rds"
)
all_present <- all(sapply(required_files, validate_file))
record("file_existence", all_present, "Required output files present",
       difftime(Sys.time(), t_start, units = "secs"))

# ------------------------------------------------------------------------------
# TEST 2: LSMS DATA INTEGRITY
# ------------------------------------------------------------------------------
message(paste(rep("-", 70), collapse = ""))
message("TEST 2: LSMS data integrity")
message(paste(rep("-", 70), collapse = ""))

t_start <- Sys.time()
passed <- tryCatch({
  lsms <- readRDS("../data/processed/lsms_trimmed_95th_africa.rds")

  required_cols <- c("x", "y", "country", "year", "farm_id", "farm_area_ha",
                     "cropland", "cattle", "pop", "temperature", "rainfall")
  missing <- setdiff(required_cols, names(lsms))
  if (length(missing) > 0) stop("Missing columns: ", paste(missing, collapse = ", "))
  message("    \u2713 All required columns present (", ncol(lsms), " total)")

  stopifnot("Farm areas must be positive"        = all(lsms$farm_area_ha > 0))
  message("    \u2713 All farm areas positive")

  stopifnot("Longitudes in valid range"          = all(lsms$x >= -180 & lsms$x <= 180))
  stopifnot("Latitudes in valid range"           = all(lsms$y >=  -90 & lsms$y <=  90))
  message("    \u2713 Coordinates in valid range")

  stopifnot("Multiple countries required"        = length(unique(lsms$country)) >= 5)
  message("    \u2713 Countries present: ", length(unique(lsms$country)))

  stopifnot("Minimum farm count"                 = nrow(lsms) >= 100)
  message("    \u2713 Farm count: ", format(nrow(lsms), big.mark = ","))

  TRUE
}, error = function(e) { message("    \u2717 ", e$message); FALSE })
record("lsms_integrity", passed, "LSMS data integrity checks",
       difftime(Sys.time(), t_start, units = "secs"))

# ------------------------------------------------------------------------------
# TEST 3: RASTER GRID INTEGRITY
# ------------------------------------------------------------------------------
message(paste(rep("-", 70), collapse = ""))
message("TEST 3: Raster grid integrity")
message(paste(rep("-", 70), collapse = ""))

t_start <- Sys.time()
passed <- tryCatch({
  grid <- readRDS("../data/processed/raster_grid_africa.rds")

  req_cols <- c("x", "y", "cropland", "cattle", "pop", "temperature", "rainfall")
  missing  <- setdiff(req_cols, names(grid))
  if (length(missing) > 0) stop("Missing grid columns: ", paste(missing, collapse = ", "))
  message("    \u2713 All predictor columns present (", ncol(grid) - 2, " predictors)")

  stopifnot("Grid must have rows"       = nrow(grid) > 0)
  message("    \u2713 Grid cells: ", format(nrow(grid), big.mark = ","))

  stopifnot("Lons in SSA range"         = all(grid$x >= -18 & grid$x <= 52))
  stopifnot("Lats in SSA range"         = all(grid$y >= -35 & grid$y <= 15))
  message("    \u2713 Extent within SSA bounds")

  stopifnot("No all-NA predictors"      =
    all(sapply(grid[, setdiff(names(grid), c("x", "y"))], function(v) sum(!is.na(v)) > 0)))
  message("    \u2713 No fully-missing predictor layers")

  TRUE
}, error = function(e) { message("    \u2717 ", e$message); FALSE })
record("grid_integrity", passed, "Raster grid integrity checks",
       difftime(Sys.time(), t_start, units = "secs"))

# ------------------------------------------------------------------------------
# TEST 4: ML-READY DATASET
# ------------------------------------------------------------------------------
message(paste(rep("-", 70), collapse = ""))
message("TEST 4: ML-ready dataset")
message(paste(rep("-", 70), collapse = ""))

t_start <- Sys.time()
passed <- tryCatch({
  ml <- read.csv("../data/processed/lsms_spatial.csv")

  stopifnot("Has rows"                 = nrow(ml) > 0)
  stopifnot("Has farm_area_ha"         = "farm_area_ha" %in% names(ml))
  stopifnot("Has spatial coords"       = all(c("x", "y") %in% names(ml)))
  stopifnot("No NA in farm_area_ha"    = sum(is.na(ml$farm_area_ha)) == 0)

  message("    \u2713 ML dataset: ", format(nrow(ml), big.mark = ","),
          " rows, ", ncol(ml), " columns, 0 NA in response")
  TRUE
}, error = function(e) { message("    \u2717 ", e$message); FALSE })
record("ml_dataset", passed, "ML-ready dataset checks",
       difftime(Sys.time(), t_start, units = "secs"))

# ------------------------------------------------------------------------------
# TEST 5: FARM SIZE DISTRIBUTION SANITY
# ------------------------------------------------------------------------------
message(paste(rep("-", 70), collapse = ""))
message("TEST 5: Farm size distribution sanity")
message(paste(rep("-", 70), collapse = ""))

t_start <- Sys.time()
passed <- tryCatch({
  lsms <- readRDS("../data/processed/lsms_trimmed_95th_africa.rds")
  med  <- median(lsms$farm_area_ha)
  mx   <- max(lsms$farm_area_ha)

  stopifnot("Median farm size 0.1-10 ha"  = med >= 0.1 && med <= 10)
  stopifnot("Max farm size <= 50 ha"      = mx  <= 50)
  stopifnot("No negative farm areas"      = min(lsms$farm_area_ha) > 0)

  message("    \u2713 Median: ", round(med, 2), " ha")
  message("    \u2713 Max:    ", round(mx,  2), " ha")
  message("    \u2713 Min:    ", round(min(lsms$farm_area_ha), 4), " ha")
  TRUE
}, error = function(e) { message("    \u2717 ", e$message); FALSE })
record("farm_size_distribution", passed, "Farm size distribution sanity",
       difftime(Sys.time(), t_start, units = "secs"))

# ------------------------------------------------------------------------------
# SUMMARY REPORT
# ------------------------------------------------------------------------------
message("\n", paste(rep("=", 70), collapse = ""))
message("TEST SUMMARY")
message(paste(rep("=", 70), collapse = ""))

total_tests  <- length(test_results)
passed_tests <- sum(sapply(test_results, `[[`, "passed"))
failed_tests <- total_tests - passed_tests
total_time   <- round(difftime(Sys.time(), start_time, units = "secs"), 1)

message("")
for (nm in names(test_results)) {
  r      <- test_results[[nm]]
  status <- if (r$passed) "\u2713 PASS" else "\u2717 FAIL"
  message(sprintf("  %s  %-40s (%ss)", status, nm, round(r$time, 1)))
}

message("\nTotal tests: ", total_tests)
message("Passed:      ", passed_tests)
message("Failed:      ", failed_tests)
message("Total time:  ", total_time, "s\n")

# Write markdown report
dir.create("../output/reports", recursive = TRUE, showWarnings = FALSE)
report_path <- "../output/reports/test_report.md"

report_lines <- c(
  "# Farm Size Prediction - CI Test Report",
  "",
  paste0("**Generated:** ", Sys.time()),
  paste0("**R Version:** ", R.version.string),
  paste0("**Platform:** ",  R.version$platform),
  "",
  "## Summary",
  "",
  "| Metric | Value |",
  "|--------|-------|",
  paste0("| Total Tests | ", total_tests,  " |"),
  paste0("| Passed      | ", passed_tests, " |"),
  paste0("| Failed      | ", failed_tests, " |"),
  paste0("| Total Time  | ", total_time,   "s |"),
  "",
  "## Test Results",
  "",
  "| Test | Status | Time | Description |",
  "|------|--------|------|-------------|"
)

for (nm in names(test_results)) {
  r      <- test_results[[nm]]
  status <- if (r$passed) "\u2705 PASS" else "\u274C FAIL"
  report_lines <- c(report_lines,
    paste0("| ", nm, " | ", status, " | ", round(r$time, 1), "s | ", r$description, " |"))
}

# Append data summary if available
if (file.exists("../data/processed/lsms_trimmed_95th_africa.rds")) {
  lsms <- readRDS("../data/processed/lsms_trimmed_95th_africa.rds")
  report_lines <- c(report_lines, "",
    "## Data Summary", "",
    paste0("- **Farms:** ",        format(nrow(lsms), big.mark = ",")),
    paste0("- **Countries:** ",    length(unique(lsms$country))),
    paste0("- **Farm size range:** ", round(min(lsms$farm_area_ha), 2),
           " - ", round(max(lsms$farm_area_ha), 2), " ha"),
    paste0("- **Median farm size:** ", round(median(lsms$farm_area_ha), 2), " ha")
  )
}

writeLines(report_lines, report_path)
message("Test report saved to: ", report_path)

if (failed_tests > 0) {
  message("\n\u274C SOME TESTS FAILED")
  if (!interactive()) quit(status = 1)
} else {
  message("\n\u2705 ALL TESTS PASSED")
  if (!interactive()) quit(status = 0)
}

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
