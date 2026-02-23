# ==============================================================================
# Script: 03.2_correlation_drivers.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Analyze correlations between predictor variables
#
# Author: [Original author]
# Documentation: Claude (Anthropic) - February 2026
#
# Description:
#   This script generates a correlation matrix of all predictor variables
#   to identify potential multicollinearity issues before ML modeling.
#
# Inputs:
#   - ../data/processed/lsms_trimmed_95th_africa.rds (from 03.1)
#
# Outputs:
#   - ../output/graphs/drivers_correlation_matrix.png
#
# Variables Analyzed:
#   - farm_area_ha: Farm size (target variable)
#   - cropland: Total cropland area (ha)
#   - cattle: Cattle density (head/km²)
#   - pop: Population density (persons/km²)
#   - cropland_per_capita: Cropland per person (ha/person)
#   - sand: Soil sand content (%)
#   - slope: Terrain slope (radians)
#   - temperature: Mean annual temperature (°C)
#   - rainfall: Mean annual rainfall (mm)
#   - maizeyield: Water-limited maize yield potential (kg/ha)
#   - market: Travel time to nearest city (minutes)
#
# Dependencies:
#   - tidyverse: Data manipulation
#   - GGally: ggpairs correlation plots
#
# Usage:
#   # Requires 03.1 to be run first
#   source("03.2_correlation_drivers.R")
#
# Notes:
#   - High correlations (|r| > 0.7) may indicate multicollinearity
#   - Random Forest is relatively robust to multicollinearity
#   - Correlations inform variable importance interpretation
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. SETUP
# ------------------------------------------------------------------------------
# Set working directory
setwd(paste0(here::here(), '/scripts'))

# Clean environment
rm(list = ls())

# Load packages
require(tidyverse)
require(GGally)

# Paths
input_path <- '../data/raw/spatial'
processed_path <- '../data/processed'
output_path <- '../output'

# ------------------------------------------------------------------------------
# 2. LOAD DATA
# ------------------------------------------------------------------------------
message("=== Loading LSMS data ===")

lsms_spatial <- readRDS(file.path(processed_path, 'lsms_trimmed_95th_africa.rds'))

# Select variables for correlation analysis
lsms_spatial <- lsms_spatial |>
  select(x, y, country, farm_area_ha, cropland, cattle, pop, cropland_per_capita,
         sand, slope, temperature, rainfall, maizeyield, market) |>
  na.omit()

message("Observations: ", nrow(lsms_spatial))
message("Variables: ", ncol(lsms_spatial) - 3, " predictors + target")

# ------------------------------------------------------------------------------
# 3. CREATE CORRELATION MATRIX
# ------------------------------------------------------------------------------
message("\n=== Creating correlation matrix ===")

# Create pairs plot with correlations
P00 <- lsms_spatial |>
  select(-x, -y, -country) |>
  GGally::ggpairs(
    upper = list(continuous = GGally::wrap("cor", size = 3)),
    diag = list(continuous = GGally::wrap("densityDiag")),
    lower = list(continuous = GGally::wrap("points", alpha = 0.1, size = 0.5))
  ) +
  theme(
    strip.text = element_text(size = 5),
    axis.text = element_text(size = 4)
  )

# Save plot
png(file.path(output_path, 'graphs/drivers_correlation_matrix.png'),
    height = 15, width = 20, units = 'cm', res = 600)
print(P00)
dev.off()

message("Saved: drivers_correlation_matrix.png")

# ------------------------------------------------------------------------------
# 4. PRINT CORRELATION SUMMARY
# ------------------------------------------------------------------------------
message("\n=== Correlation Summary ===")

# Calculate correlation matrix
cor_data <- lsms_spatial |>
  select(-x, -y, -country)

cor_matrix <- cor(cor_data, use = "complete.obs")

# Find high correlations (|r| > 0.5)
high_cors <- which(abs(cor_matrix) > 0.5 & cor_matrix != 1, arr.ind = TRUE)

if (nrow(high_cors) > 0) {
  message("\nVariable pairs with |r| > 0.5:")
  for (i in seq_len(nrow(high_cors))) {
    row_idx <- high_cors[i, 1]
    col_idx <- high_cors[i, 2]
    if (row_idx < col_idx) {  # Avoid duplicates
      var1 <- rownames(cor_matrix)[row_idx]
      var2 <- colnames(cor_matrix)[col_idx]
      r <- round(cor_matrix[row_idx, col_idx], 3)
      message("  ", var1, " <-> ", var2, ": r = ", r)
    }
  }
}

# Correlations with target variable
message("\nCorrelations with farm_area_ha:")
farm_cors <- cor_matrix["farm_area_ha", ]
farm_cors <- farm_cors[names(farm_cors) != "farm_area_ha"]
farm_cors <- sort(farm_cors, decreasing = TRUE)
for (var in names(farm_cors)) {
  message("  ", var, ": r = ", round(farm_cors[var], 3))
}

message("\n=== Analysis Complete ===")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
