# ==============================================================================
# Script: 00_run_tests_base.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Run validation tests using only base R
# ==============================================================================

message("\n")
message(paste(rep("=", 70), collapse = ""))
message("FARM SIZE PREDICTION - TEST SUITE (Base R)")
message(paste(rep("=", 70), collapse = ""))
message("Started: ", Sys.time())

test_results <- list()
start_time <- Sys.time()

run_test <- function(name, test_fn) {
  message("\n--- ", name, " ---")
  t0 <- Sys.time()
  
  result <- tryCatch({
    test_fn()
    TRUE
  }, error = function(e) {
    message("  ERROR: ", e$message)
    FALSE
  })
  
  elapsed <- round(difftime(Sys.time(), t0, units = "secs"), 2)
  status <- ifelse(result, "PASS", "FAIL")
  message("  ", status, " (", elapsed, "s)")
  
  test_results[[name]] <<- list(passed = result, time = elapsed)
  return(result)
}

# ------------------------------------------------------------------------------
# TEST 1: Directory structure exists
# ------------------------------------------------------------------------------
run_test("Directory Structure", function() {
  required_dirs <- c(
    "../data/processed",
    "../data/raw/spatial",
    "../output/tables",
    "../output/reports"
  )
  
  for (d in required_dirs) {
    if (!dir.exists(d)) stop(paste("Missing directory:", d))
    message("    ✓ ", d)
  }
})

# ------------------------------------------------------------------------------
# TEST 2: Core data files exist
# ------------------------------------------------------------------------------
run_test("Core Data Files", function() {
  required_files <- c(
    "../data/processed/lsms_and_zambia.csv",
    "../data/processed/lsms_trimmed_95th_africa.rds",
    "../data/processed/lsms_spatial.csv",
    "../data/processed/predictor_grid.csv"
  )
  
  for (f in required_files) {
    if (!file.exists(f)) stop(paste("Missing file:", f))
    size <- file.info(f)$size
    message("    ✓ ", basename(f), " (", format(size, big.mark=","), " bytes)")
  }
})

# ------------------------------------------------------------------------------
# TEST 3: LSMS data integrity
# ------------------------------------------------------------------------------
run_test("LSMS Data Integrity", function() {
  lsms <- read.csv("../data/processed/lsms_and_zambia.csv")
  
  # Check columns
  required_cols <- c("x", "y", "country", "year", "farm_id", "farm_area_ha")
  missing <- required_cols[!required_cols %in% names(lsms)]
  if (length(missing) > 0) stop(paste("Missing columns:", paste(missing, collapse=", ")))
  message("    ✓ All required columns present")
  
  # Check values
  if (any(lsms$farm_area_ha <= 0)) stop("Farm areas must be positive")
  message("    ✓ Farm areas all positive")
  
  if (any(lsms$x < -180 | lsms$x > 180)) stop("Invalid longitude values")
  if (any(lsms$y < -90 | lsms$y > 90)) stop("Invalid latitude values")
  message("    ✓ Coordinates in valid range")
  
  n_countries <- length(unique(lsms$country))
  if (n_countries < 5) stop("Too few countries")
  message("    ✓ ", n_countries, " countries present")
  
  message("    ✓ ", nrow(lsms), " total farms")
})

# ------------------------------------------------------------------------------
# TEST 4: Trimmed dataset integrity
# ------------------------------------------------------------------------------
run_test("Trimmed Dataset", function() {
  lsms_95 <- readRDS("../data/processed/lsms_trimmed_95th_africa.rds")
  lsms_99 <- readRDS("../data/processed/lsms_trimmed_99th_africa.rds")
  
  if (nrow(lsms_95) >= nrow(lsms_99)) stop("95th should have fewer rows than 99th")
  message("    ✓ 95th percentile: ", nrow(lsms_95), " farms")
  message("    ✓ 99th percentile: ", nrow(lsms_99), " farms")
  
  # Check predictor columns exist
  predictors <- c("cropland", "cattle", "pop", "temperature", "rainfall")
  missing <- predictors[!predictors %in% names(lsms_95)]
  if (length(missing) > 0) stop(paste("Missing predictors:", paste(missing, collapse=", ")))
  message("    ✓ All predictor columns present")
})

# ------------------------------------------------------------------------------
# TEST 5: ML dataset ready
# ------------------------------------------------------------------------------
run_test("ML Dataset", function() {
  ml_data <- read.csv("../data/processed/lsms_spatial.csv")
  
  if (nrow(ml_data) < 1000) stop("Too few observations for ML")
  message("    ✓ ", nrow(ml_data), " observations")
  
  if (any(is.na(ml_data))) stop("ML dataset contains NA values")
  message("    ✓ No missing values")
  
  # Check farm_area_ha range
  range_ha <- range(ml_data$farm_area_ha)
  message("    ✓ Farm size range: ", round(range_ha[1], 2), " - ", round(range_ha[2], 2), " ha")
})

# ------------------------------------------------------------------------------
# TEST 6: Output files generated
# ------------------------------------------------------------------------------
run_test("Output Files", function() {
  stats_file <- "../output/tables/summary_descriptive_stats_survey.csv"
  if (!file.exists(stats_file)) stop("Summary stats file missing")
  
  stats <- read.csv(stats_file)
  if (nrow(stats) < 5) stop("Stats table too small")
  message("    ✓ Summary statistics: ", nrow(stats), " rows")
  
  cor_file <- "../output/tables/correlation_matrix.csv"
  if (!file.exists(cor_file)) stop("Correlation matrix missing")
  message("    ✓ Correlation matrix generated")
})

# ------------------------------------------------------------------------------
# TEST 7: Country raw files
# ------------------------------------------------------------------------------
run_test("Country Raw Files", function() {
  raw_files <- list.files("../data/processed", pattern = "_raw\\.csv$")
  if (length(raw_files) < 10) stop("Too few country raw files")
  message("    ✓ ", length(raw_files), " country-year raw files")
  
  # Check one file
  sample_file <- paste0("../data/processed/", raw_files[1])
  sample_data <- read.csv(sample_file)
  if (nrow(sample_data) < 10) stop("Sample file too small")
  message("    ✓ Sample file has ", nrow(sample_data), " rows")
})

# ------------------------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------------------------
message("\n")
message(paste(rep("=", 70), collapse = ""))
message("TEST SUMMARY")
message(paste(rep("=", 70), collapse = ""))

total <- length(test_results)
passed <- sum(sapply(test_results, function(x) x$passed))
failed <- total - passed
total_time <- round(difftime(Sys.time(), start_time, units = "secs"), 1)

message("\nResults:")
for (name in names(test_results)) {
  r <- test_results[[name]]
  status <- ifelse(r$passed, "✓ PASS", "✗ FAIL")
  message("  ", status, "  ", name, " (", r$time, "s)")
}

message("\n")
message("Total:  ", total)
message("Passed: ", passed)
message("Failed: ", failed)
message("Time:   ", total_time, "s")

# Generate report
report <- paste0(
  "# Farm Size Prediction - Test Report\n\n",
  "**Generated:** ", Sys.time(), "\n",
  "**R Version:** ", R.version.string, "\n\n",
  "## Summary\n\n",
  "- Total Tests: ", total, "\n",
  "- Passed: ", passed, "\n", 
  "- Failed: ", failed, "\n",
  "- Time: ", total_time, "s\n\n",
  "## Results\n\n"
)

for (name in names(test_results)) {
  r <- test_results[[name]]
  status <- ifelse(r$passed, "✅", "❌")
  report <- paste0(report, "- ", status, " ", name, " (", r$time, "s)\n")
}

# Add data summary
lsms <- read.csv("../data/processed/lsms_and_zambia.csv")
report <- paste0(report, "\n## Data Summary\n\n",
  "- Farms: ", format(nrow(lsms), big.mark=","), "\n",
  "- Countries: ", length(unique(lsms$country)), "\n",
  "- Farm size median: ", round(median(lsms$farm_area_ha), 2), " ha\n",
  "- Farm size range: ", round(min(lsms$farm_area_ha), 2), " - ",
  round(max(lsms$farm_area_ha), 2), " ha\n"
)

writeLines(report, "../output/reports/test_report.md")
message("\nReport saved: ../output/reports/test_report.md")

if (failed > 0) {
  message("\n❌ SOME TESTS FAILED")
} else {
  message("\n✅ ALL TESTS PASSED")
}
