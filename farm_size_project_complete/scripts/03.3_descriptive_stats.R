# ==============================================================================
# Script: 03.3_descriptive_stats.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Generate descriptive statistics of LSMS farm size data
#
# Author: [Original author]
# Documentation: Claude (Anthropic) - February 2026
#
# Description:
#   This script calculates summary statistics of farm sizes across all
#   countries and survey waves, producing a publication-ready table.
#
# Inputs:
#   - ../data/processed/lsms_and_zambia.csv (from 02.2)
#
# Outputs:
#   - ../output/tables/summary_descriptive_stats_survey.csv
#
# Statistics Calculated:
#   - Number of survey waves per country
#   - Survey period (first-last year)
#   - Number of observations (farm-years)
#   - Percentage of farms < 0.5 ha (marginal farms)
#   - Percentage of farms < 1 ha (small farms)
#   - 10th, 50th (median), mean, 90th percentile of farm sizes
#
# Dependencies:
#   - tidyverse: Data manipulation
#
# Usage:
#   # Requires 02.2 to be run first
#   source("03.3_descriptive_stats.R")
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
processed_path <- '../data/processed'
output_path <- '../output'

# ------------------------------------------------------------------------------
# 2. LOAD DATA
# ------------------------------------------------------------------------------
message("=== Loading LSMS data ===")

lsms_spatial <- read.csv(file.path(processed_path, 'lsms_and_zambia.csv'))

# Filter to valid farm sizes
my_lsms <- lsms_spatial |>
  select(country, year, farm_area_ha) |>
  filter(farm_area_ha > 0)

message("Total observations: ", nrow(my_lsms))
message("Countries: ", length(unique(my_lsms$country)))

# ------------------------------------------------------------------------------
# 3. CALCULATE STATISTICS BY COUNTRY
# ------------------------------------------------------------------------------
message("\n=== Calculating descriptive statistics ===")

# Number of survey waves per country
nb_waves <- my_lsms |>
  select(country, year) |>
  distinct() |>
  group_by(country) |>
  summarize(
    n_waves = n(),
    period = paste0(min(year), '-', max(year)),
    .groups = 'drop'
  ) |>
  mutate(
    # Format single-year periods
    period = ifelse(
      substr(period, 1, 4) == substr(period, 6, 9),
      substr(period, 1, 4),
      period
    )
  )

# Number of observations per country
nb_obs <- my_lsms |>
  group_by(country) |>
  summarize(n_obs = n(), .groups = 'drop')

# Farms below 0.5 ha (marginal farms)
farms_below_0.5 <- my_lsms |>
  filter(farm_area_ha < 0.5) |>
  group_by(country) |>
  summarize(n_0.5 = n(), .groups = 'drop')

# Farms below 1 ha (small farms)
farms_below_1 <- my_lsms |>
  filter(farm_area_ha < 1) |>
  group_by(country) |>
  summarize(n_1 = n(), .groups = 'drop')

# Farm size distribution
descrip_farm_sizes <- my_lsms |>
  group_by(country) |>
  summarize(
    avg = round(mean(farm_area_ha, na.rm = TRUE), 2),
    med = round(median(farm_area_ha, na.rm = TRUE), 2),
    q10 = round(quantile(farm_area_ha, 0.10, na.rm = TRUE), 2),
    q90 = round(quantile(farm_area_ha, 0.90, na.rm = TRUE), 2),
    .groups = 'drop'
  )

# ------------------------------------------------------------------------------
# 4. COMBINE INTO SUMMARY TABLE
# ------------------------------------------------------------------------------
message("\n=== Creating summary table ===")

table_01 <- nb_waves |>
  inner_join(nb_obs, by = "country") |>
  left_join(farms_below_0.5, by = "country") |>
  left_join(farms_below_1, by = "country") |>
  inner_join(descrip_farm_sizes, by = "country") |>
  mutate(
    n_0.5 = replace_na(n_0.5, 0),
    n_1 = replace_na(n_1, 0),
    prct_below_0.5 = round(100 * n_0.5 / n_obs, 2),
    prct_below_1 = round(100 * n_1 / n_obs, 2)
  )

# Add total row
sum_table01 <- tibble(
  country = 'TOTAL',
  n_waves = sum(table_01$n_waves),
  period = paste0(min(my_lsms$year), '-', max(my_lsms$year)),
  n_obs = sum(table_01$n_obs),
  n_0.5 = sum(table_01$n_0.5),
  n_1 = sum(table_01$n_1),
  prct_below_0.5 = round(100 * sum(table_01$n_0.5) / sum(table_01$n_obs), 2),
  prct_below_1 = round(100 * sum(table_01$n_1) / sum(table_01$n_obs), 2),
  avg = round(mean(my_lsms$farm_area_ha, na.rm = TRUE), 2),
  med = round(median(my_lsms$farm_area_ha, na.rm = TRUE), 2),
  q10 = round(quantile(my_lsms$farm_area_ha, 0.10, na.rm = TRUE), 2),
  q90 = round(quantile(my_lsms$farm_area_ha, 0.90, na.rm = TRUE), 2)
)

# Finalize table
table_01 <- table_01 |>
  bind_rows(sum_table01) |>
  select(country, n_waves, period, n_obs, prct_below_0.5, prct_below_1,
         q10, med, avg, q90)

# ------------------------------------------------------------------------------
# 5. DISPLAY AND SAVE
# ------------------------------------------------------------------------------
message("\n=== Summary Statistics ===")
print(table_01, n = 20)

# Save table
output_file <- file.path(output_path, 'tables/summary_descriptive_stats_survey.csv')
write_csv(table_01, file = output_file)
message("\nSaved: ", output_file)

# ------------------------------------------------------------------------------
# 6. KEY FINDINGS
# ------------------------------------------------------------------------------
message("\n=== Key Findings ===")

total_row <- table_01 |> filter(country == 'TOTAL')

message("Total observations: ", format(total_row$n_obs, big.mark = ","))
message("Total survey waves: ", total_row$n_waves)
message("Period covered: ", total_row$period)
message("")
message("Farm size distribution:")
message("  10th percentile: ", total_row$q10, " ha")
message("  Median: ", total_row$med, " ha")
message("  Mean: ", total_row$avg, " ha")
message("  90th percentile: ", total_row$q90, " ha")
message("")
message("Small farms:")
message("  < 0.5 ha: ", total_row$prct_below_0.5, "%")
message("  < 1.0 ha: ", total_row$prct_below_1, "%")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
