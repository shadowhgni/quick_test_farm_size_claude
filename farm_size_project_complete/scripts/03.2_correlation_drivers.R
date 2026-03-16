# ==============================================================================
# Script: 03.1_pooled_data.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Prepare pooled LSMS dataset with spatial predictors for ML analysis
#
# Authors: Deo, Joao, Robert, Fred 
# Documentation: Claude (Anthropic) - February 2026
#
# Description:
#   This script combines LSMS farm data with spatial predictor layers,
#   assigns administrative divisions, applies quality filters, and creates
#   the final analysis-ready dataset for machine learning models.
#
# Inputs:
#   - ../data/processed/all_predictors.tif (from 01.4)
#   - ../data/processed/lsms_and_zambia.csv (from 02.2)
#   - GADM administrative boundaries (via geodata)
#
# Outputs:
#   - ../data/processed/stacked_rasters_africa.tif (predictor stack for ML)
#   - ../data/processed/lsms_untrimmed_africa.rds (all farms)
#   - ../data/processed/lsms_trimmed_99th_africa.rds (99th percentile trim)
#   - ../data/processed/lsms_trimmed_95th_africa.rds (95th percentile trim)
#   - ../data/processed/lsms_spatial.csv (final ML dataset)
#   - ../output/maps/africa-lsms.png (data distribution map)
#
# Processing Steps:
#   1. Load predictor raster stack
#   2. Load and filter LSMS data (year > 2007, n_farms >= 700)
#   3. Download GADM boundaries for all 16 countries
#   4. Assign GADM administrative divisions to each farm
#   5. Remove conflict-affected areas (Nigeria: Bauchi, Borno, Yobe)
#   6. Trim outliers by region (95th/99th percentile)
#   7. Extract predictor values at farm locations
#   8. Save datasets for ML analysis
#
# Key Filtering Decisions:
#   - Years: 2008-2021 only (excludes Malawi 2004, Uganda 2005)
#   - Sample size: Minimum 700 farms per country-year
#   - Outliers: Trimmed at 95th percentile by GADM_1 region
#   - Conflict zones: Nigeria's Borno, Bauchi, Yobe excluded
#
# Dependencies:
#   - tidyverse: Data manipulation
#   - terra: Raster/vector operations
#   - geodata: GADM boundaries
#
# Usage:
#   # Requires 01.4 and 02.2 to be run first
#   source("03.1_pooled_data.R")
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
require(terra)
require(geodata)

# Paths
input_path <- '../data/raw/spatial'
processed_path <- '../data/processed'
output_path <- '../output'

# ------------------------------------------------------------------------------
# 2. DEFINE STUDY REGION
# ------------------------------------------------------------------------------
message("=== Loading study region ===")

# Load world boundaries
country <- geodata::world(path = input_path, resolution = 5, level = 0)
isocodes <- geodata::country_codes()

# Define Sub-Saharan Africa
isocodes_ssa <- subset(
  isocodes,
  NAME == 'Sudan' |
  UNREGION1 == 'Middle Africa' |
  UNREGION1 == 'Western Africa' |
  UNREGION1 == 'Southern Africa' |
  UNREGION1 == 'Eastern Africa'
)
islands <- c('Cabo Verde', 'Comoros', 'Mauritius', 'Mayotte',
             'Réunion', 'Saint Helena', 'São Tomé and Príncipe', 'Seychelles')
isocodes_ssa <- subset(isocodes_ssa, !(NAME %in% islands))
ssa <- subset(country, country$GID_0 %in% isocodes_ssa$ISO3)

# Countries with LSMS data
sixteen_countries <- c(
  'Benin', 'Burkina', 'Cote_d_Ivoire', 'Ethiopia', 'Ghana', 'Guinea_Bissau',
  'Malawi', 'Mali', 'Niger', 'Nigeria', 'Rwanda', 'Senegal',
  'Tanzania', 'Togo', 'Uganda', 'Zambia'
)
sixteen_country_codes <- c(
  'BEN', 'BFA', 'CIV', 'ETH', 'GHA', 'GNB',
  'MWI', 'MLI', 'NER', 'NGA', 'RWA', 'SEN',
  'TZA', 'TGO', 'UGA', 'ZMB'
)

# ------------------------------------------------------------------------------
# 3. DOWNLOAD GADM ADMINISTRATIVE BOUNDARIES
# ------------------------------------------------------------------------------
message("\n=== Downloading GADM boundaries ===")

# Create directories and download GADM data
gadm_configs <- list(
  list(name = 'Benin', code = 'Benin', level = 3),
  list(name = 'Burkina', code = 'Burkina Faso', level = 3),
  list(name = 'Cote_d_Ivoire', code = 'CIV', level = 4),
  list(name = 'Ethiopia', code = 'Ethiopia', level = 3),
  list(name = 'Ghana', code = 'Ghana', level = 2),
  list(name = 'Guinea_Bissau', code = 'GNB', level = 2),
  list(name = 'Malawi', code = 'Malawi', level = 3),
  list(name = 'Mali', code = 'Mali', level = 4),
  list(name = 'Niger', code = 'Niger', level = 3),
  list(name = 'Nigeria', code = 'Nigeria', level = 2),
  list(name = 'Rwanda', code = 'Rwanda', level = 4),
  list(name = 'Senegal', code = 'Senegal', level = 4),
  list(name = 'Tanzania', code = 'Tanzania', level = 3),
  list(name = 'Togo', code = 'Togo', level = 3),
  list(name = 'Uganda', code = 'Uganda', level = 4),
  list(name = 'Zambia', code = 'Zambia', level = 2)
)

gadm_list <- list()
for (cfg in gadm_configs) {
  gadm_dir <- file.path(input_path, 'gadm', cfg$name)
  if (!dir.exists(gadm_dir)) dir.create(gadm_dir, recursive = TRUE)
  
  gadm_list[[cfg$name]] <- geodata::gadm(
    cfg$code, level = cfg$level, path = gadm_dir
  )
  message("  Downloaded: ", cfg$name, " (level ", cfg$level, ")")
}

# Combine all country boundaries
sixteen_count_distr <- Reduce(function(a, b) rbind(a, b), gadm_list)

# ------------------------------------------------------------------------------
# 4. LOAD PREDICTOR STACK
# ------------------------------------------------------------------------------
message("\n=== Loading predictor layers ===")

stacked_00 <- terra::rast(file.path(processed_path, 'all_predictors.tif'))
message("Predictor layers: ", paste(names(stacked_00), collapse = ", "))

# ------------------------------------------------------------------------------
# 5. LOAD AND FILTER LSMS DATA
# ------------------------------------------------------------------------------
message("\n=== Loading LSMS data ===")

lsms_and_zambia <- read.csv(file.path(processed_path, 'lsms_and_zambia.csv'))

# Initial filtering
lsms <- lsms_and_zambia |>
  filter(
    !is.na(farm_area_ha),
    farm_area_ha > 0,
    !is.na(x), !is.na(y),
    !(x == 0 & y == 0)
  )

message("Initial farms: ", nrow(lsms))
lsms_00 <- lsms  # Backup original

# Filter to 2008-2021 (exclude early surveys)
lsms <- lsms |> filter(year > 2007)
message("After year filter (>2007): ", nrow(lsms))

# Remove small survey waves (< 700 farms)
summary_lsms <- lsms |>
  group_by(country, year) |>
  summarize(n_farms = n(), .groups = 'drop')

small_waves <- summary_lsms |> filter(n_farms < 700)
if (nrow(small_waves) > 0) {
  message("Excluding small waves: ")
  print(small_waves)
}

lsms <- lsms |>
  anti_join(small_waves |> select(country, year), by = c("country", "year"))

message("After sample size filter: ", nrow(lsms))

# Create unique farm IDs
lsms <- dplyr::mutate(lsms, farm_id = paste0(country, '_', year, '_', seq_len(dplyr::n())))

# ------------------------------------------------------------------------------
# 6. ASSIGN ADMINISTRATIVE DIVISIONS
# ------------------------------------------------------------------------------
message("\n=== Assigning administrative divisions ===")

# Initialize GADM columns
lsms$gadm_0 <- lsms$gadm_1 <- lsms$gadm_2 <- lsms$gadm_3 <- lsms$gadm_4 <- NA

# Convert to SpatVector
lsms <- terra::vect(lsms, geom = c('x', 'y'), crs = 'EPSG:4326')

# Extract GADM info
lsms$gadm_0 <- terra::extract(sixteen_count_distr[, 'GID_0'], lsms)$GID_0
lsms$gadm_1 <- terra::extract(sixteen_count_distr[, 'NAME_1'], lsms)$NAME_1
lsms$gadm_2 <- terra::extract(sixteen_count_distr[, 'NAME_2'], lsms)$NAME_2
lsms$gadm_3 <- terra::extract(sixteen_count_distr[, 'NAME_3'], lsms)$NAME_3
lsms$gadm_4 <- terra::extract(sixteen_count_distr[, 'NAME_4'], lsms)$NAME_4

lsms_01 <- lsms  # Backup
terra::writeVector(lsms_01, file.path(processed_path, 'backup_untrimmed_lsms_01_africa.shp'), overwrite = TRUE)

# ------------------------------------------------------------------------------
# 7. REMOVE CONFLICT-AFFECTED AREAS
# ------------------------------------------------------------------------------
message("\n=== Removing conflict-affected areas ===")

# Nigeria: Exclude Boko Haram-affected states (2011-2015)
conflict_states <- c('Bauchi', 'Borno', 'Yobe')
n_before <- length(lsms)
lsms <- lsms[!(lsms$gadm_1 %in% conflict_states)]
n_removed <- n_before - length(lsms)
message("Removed ", n_removed, " farms from conflict areas")

lsms_02 <- lsms  # Backup

# ------------------------------------------------------------------------------
# 8. TRIM OUTLIERS BY REGION
# ------------------------------------------------------------------------------
message("\n=== Trimming outliers by region ===")

# Calculate percentiles by GADM_1 region
lsms_per_region <- terra::as.data.frame(lsms) |>
  group_by(country, gadm_0, gadm_1) |>
  summarize(
    n_farms_years = n(),
    min = min(farm_area_ha, na.rm = TRUE),
    max = max(farm_area_ha, na.rm = TRUE),
    q_05 = quantile(farm_area_ha, 0.05),
    q_95 = quantile(farm_area_ha, 0.95),
    q_01 = quantile(farm_area_ha, 0.01),
    q_99 = quantile(farm_area_ha, 0.99),
    .groups = 'drop'
  ) |>
  arrange(desc(max))

# Join percentiles to data
trim_data <- inner_join(
  lsms_per_region |> select(country, gadm_0, gadm_1, q_95, q_99),
  cbind(terra::as.data.frame(lsms), terra::crds(lsms)),
  by = c("country", "gadm_0", "gadm_1")
)

# Create trimmed datasets
trim_1 <- terra::vect(trim_data, geom = c('x', 'y'), crs = 'EPSG:4326')
trim_1 <- subset(trim_1, trim_1$farm_area_ha > 0)

trim_2 <- subset(trim_1, trim_1$farm_area_ha <= trim_1$q_99)  # 99th percentile
trim_3 <- subset(trim_1, trim_1$farm_area_ha <= trim_1$q_95)  # 95th percentile

message("Untrimmed: ", length(trim_1), " farms")
message("99th percentile trim: ", length(trim_2), " farms")
message("95th percentile trim: ", length(trim_3), " farms")

# ------------------------------------------------------------------------------
# 9. CREATE ANALYSIS MAP
# ------------------------------------------------------------------------------
message("\n=== Creating data distribution map ===")

lsms_colour <- cbind(terra::as.data.frame(lsms), terra::crds(lsms)) |>
  group_by(x, y) |>
  summarize(nb_farms = n(), .groups = 'drop')

pal <- colorRampPalette(c('skyblue1', 'blue4'))(max(lsms_colour$nb_farms))
ea_colours <- pal[lsms_colour$nb_farms]

png(file.path(output_path, 'maps/africa-lsms.png'),
    units = 'in', width = 11, height = 5.5, res = 1000)
par(mfrow = c(1, 2), mgp = c(2, 0.5, 0))
terra::plot(ssa, col = 'azure', main = 'LSMS all countries',
            panel.first = grid(col = "gray", lty = 'solid'))
terra::plot(lsms, col = ea_colours, cex = 0.4, axes = FALSE, add = TRUE)
terra::plot(ssa, axes = FALSE, add = TRUE)
boxplot(lsms$farm_area_ha ~ lsms$country, ylim = c(0, 15),
        xlab = '', ylab = 'Farm size (ha)', cex.axis = 0.85)
dev.off()

# ------------------------------------------------------------------------------
# 10. CREATE PREDICTOR STACK FOR ML
# ------------------------------------------------------------------------------
message("\n=== Creating predictor stack ===")

# Select predictors for ML models
stacked <- c(
  stacked_00$cropland,
  stacked_00$cattle,
  stacked_00$pop,
  stacked_00$cropland_per_capita,
  stacked_00$sand,
  stacked_00$slope,
  stacked_00$temperature,
  stacked_00$rainfall,
  stacked_00$maizeyield,
  stacked_00$market
)

terra::writeRaster(stacked, file.path(processed_path, 'stacked_rasters_africa.tif'), overwrite = TRUE)
message("Saved: stacked_rasters_africa.tif")

# ------------------------------------------------------------------------------
# 11. EXTRACT PREDICTORS AND SAVE DATASETS
# ------------------------------------------------------------------------------
message("\n=== Extracting predictors at farm locations ===")

#' Extract predictor values and create analysis dataset
#' @param x SpatVector of farm locations
#' @return Data frame with farm data and predictor values
select_variables <- function(x) {
  lsms_df <- cbind(
    data.frame(x),
    terra::geom(x) |> as.data.frame()
  )
  
  lsms_df <- lsms_df[c('x', 'y', 'country', 'gadm_0', 'gadm_1', 'gadm_2',
                        'gadm_3', 'gadm_4', 'year', 'farm_id', 'farm_area_ha', 'hh_size')]
  
  # Extract predictor values
  lsms_df <- cbind(
    lsms_df,
    terra::extract(stacked, lsms_df |> select(x, y), ID = FALSE)
  )
  
  return(lsms_df)
}

# Create and save datasets
lsms_untrimmed <- select_variables(trim_1)
saveRDS(lsms_untrimmed, file = file.path(processed_path, 'lsms_untrimmed_africa.rds'))
message("Saved: lsms_untrimmed_africa.rds (", nrow(lsms_untrimmed), " farms)")

lsms_99 <- select_variables(trim_2)
saveRDS(lsms_99, file = file.path(processed_path, 'lsms_trimmed_99th_africa.rds'))
message("Saved: lsms_trimmed_99th_africa.rds (", nrow(lsms_99), " farms)")

lsms_95 <- select_variables(trim_3)
saveRDS(lsms_95, file = file.path(processed_path, 'lsms_trimmed_95th_africa.rds'))
message("Saved: lsms_trimmed_95th_africa.rds (", nrow(lsms_95), " farms)")

# Save final ML dataset (95th percentile, predictors only)
lsms_spatial <- lsms_95 |>
  select(x, y, farm_area_ha, cropland, cattle, pop, cropland_per_capita,
         sand, slope, temperature, rainfall, maizeyield, market) |>
  na.omit()

write.csv(lsms_95, file.path(processed_path, 'lsms_spatial_with_country_names.csv'), row.names = FALSE)
write.csv(lsms_spatial |> select(-x, -y), file.path(processed_path, 'lsms_spatial.csv'), row.names = FALSE)
saveRDS(stacked, file = file.path(processed_path, 'stacked_africa.Rds'))
saveRDS(lsms_spatial, file = file.path(processed_path, 'lsms_spatial_africa.Rds'))

message("\n=== Processing Complete ===")
message("Final dataset: ", nrow(lsms_spatial), " farms with complete predictor data")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
