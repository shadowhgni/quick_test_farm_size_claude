# ==============================================================================
# Script: 02.3_measured_vs_reported.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Analyze agreement between GPS-measured and farmer-reported plot sizes
#
# Authors: Deo, Joao, Robert, Fred 
# Documentation: Claude (Anthropic) - February 2026
#
# Description:
#   This script quantifies the relationship between GPS-measured and
#   farmer-reported plot areas to understand measurement accuracy and
#   inform the farm size calculation methodology.
#
# Inputs:
#   - ../data/processed/lsms_and_zambia.rds (from 02.2)
#
# Outputs:
#   - Console output: measurement statistics
#
# Key Statistics:
#   - Percentage of plots with GPS measurements
#   - Correlation between reported and measured areas
#   - Standard deviation of reporting error ratio
#
# Dependencies:
#   - tidyverse: Data manipulation
#
# Usage:
#   # Requires 02.2 to be run first
#   source("02.3_measured_vs_reported.R")
#
# Notes:
#   - This is a diagnostic script for understanding data quality
#   - Results inform the measurement preference in 02.2
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. SETUP
# ------------------------------------------------------------------------------
# Load packages
require(tidyverse)

# Set working directory
setwd(paste0(here::here(), '/scripts'))

# Clean environment
rm(list = ls())

# Paths
input_path <- '../data/raw/spatial'
processed_path <- '../data/processed'

# ------------------------------------------------------------------------------
# 2. LOAD DATA
# ------------------------------------------------------------------------------
message("=== Loading LSMS data ===")

xx <- readRDS(file.path(processed_path, 'lsms_and_zambia.rds'))

# Join raw plot data with farm-level data
all_lsms_raw_data <- xx$all_lsms_raw_data |>
  inner_join(xx$lsms_farm_size, by = c("x", "y", "country", "year", "farm_id", "hh_size"))

message("Total plots: ", nrow(all_lsms_raw_data))

# ------------------------------------------------------------------------------
# 3. CALCULATE MEASUREMENT STATISTICS
# ------------------------------------------------------------------------------
message("\n=== Measurement Statistics ===")

# Percentage of plots that were GPS-measured
n_total <- nrow(all_lsms_raw_data)
n_measured <- all_lsms_raw_data |>
  select(measured_plot_area_ha) |>
  na.omit() |>
  nrow()

pct_measured <- round(100 * n_measured / n_total, 1)

message("Plots with GPS measurement: ", n_measured, " / ", n_total, 
        " (", pct_measured, "%)")

# ------------------------------------------------------------------------------
# 4. CORRELATION ANALYSIS
# ------------------------------------------------------------------------------
message("\n=== Correlation Analysis ===")

# Filter to plots with both reported and measured values
# Exclude outliers (reported > 100 ha)
comparison_data <- all_lsms_raw_data |>
  filter(
    !is.na(reported_area_ha),
    !is.na(measured_plot_area_ha),
    reported_area_ha <= 100
  )

message("Plots with both values (reported ≤ 100 ha): ", nrow(comparison_data))

# Pearson correlation
r_sq <- round(
  cor(comparison_data$reported_area_ha, 
      comparison_data$measured_plot_area_ha, 
      use = 'complete.obs'),
  3
)

message("Correlation (r): ", r_sq)
message("R-squared: ", round(r_sq^2, 3))

# ------------------------------------------------------------------------------
# 5. REPORTING ERROR ANALYSIS
# ------------------------------------------------------------------------------
message("\n=== Reporting Error Analysis ===")

# Ratio of reported to measured (>1 = overreporting, <1 = underreporting)
comparison_data <- comparison_data |>
  mutate(
    ratio = reported_area_ha / measured_plot_area_ha
  ) |>
  filter(is.finite(ratio))

mean_ratio <- round(mean(comparison_data$ratio, na.rm = TRUE), 2)
median_ratio <- round(median(comparison_data$ratio, na.rm = TRUE), 2)
sd_ratio <- round(sd(comparison_data$ratio, na.rm = TRUE), 2)

message("Reported/Measured ratio:")
message("  Mean:   ", mean_ratio)
message("  Median: ", median_ratio)
message("  SD:     ", sd_ratio)

# Interpretation
if (median_ratio > 1) {
  message("\n  Interpretation: Farmers tend to OVERREPORT plot sizes")
} else if (median_ratio < 1) {
  message("\n  Interpretation: Farmers tend to UNDERREPORT plot sizes")
} else {
  message("\n  Interpretation: No systematic bias in reporting")
}

# ------------------------------------------------------------------------------
# 6. BY-COUNTRY BREAKDOWN
# ------------------------------------------------------------------------------
message("\n=== By-Country Breakdown ===")

country_stats <- all_lsms_raw_data |>
  filter(!is.na(measured_plot_area_ha)) |>
  group_by(country) |>
  summarize(
    n_measured = n(),
    pct_measured = round(100 * n() / sum(!is.na(reported_area_ha)), 1),
    .groups = 'drop'
  ) |>
  arrange(desc(n_measured))

print(country_stats, n = 20)

# ------------------------------------------------------------------------------
# 7. SUMMARY
# ------------------------------------------------------------------------------
message("\n", paste(rep("=", 50), collapse = ""))
message("SUMMARY")
message(paste(rep("=", 50), collapse = ""))
message("• ", pct_measured, "% of plots have GPS measurements")
message("• Correlation between reported and measured: r = ", r_sq)
message("• Median reporting ratio: ", median_ratio, 
        " (", ifelse(median_ratio > 1, "overreporting", "underreporting"), ")")
message("• SD of reporting ratio: ", sd_ratio, 
        " (higher = more variable reporting)")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
