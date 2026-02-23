# ==============================================================================
# Script: 00_synthetic_data.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Generate synthetic data for testing all scripts without real data
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - February 2026
#
# Description:
#   This script generates synthetic spatial and survey data that mimics the
#   structure of real LSMS and spatial predictor data. It enables:
#   1. Testing script logic without requiring large data downloads
#   2. CI/CD pipeline testing in GitHub Actions
#   3. Demonstration of workflow to new users
#
# Usage:
#   source("00_synthetic_data.R")
#   # All synthetic data will be created in ../data/
#
# Output Files:
#   - ../data/raw/spatial/spam/spam2017_cropland_ssa.tif
#   - ../data/raw/spatial/rainfall/rainfall_yearly/#_long_term_rainfall_avg.tif
#   - ../data/raw/spatial/cattle-density/2010_cattle_density_ssa.tif
#   - ../data/raw/spatial/population/2020_population_density_ssa.tif
#   - ../data/processed/all_predictors.tif
#   - ../data/processed/lsms_and_zambia.csv
#   - ../data/processed/lsms_trimmed_95th_africa.rds
#   - ../data/processed/stacked_rasters_africa.tif
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. SETUP
# ------------------------------------------------------------------------------
message("=== Synthetic Data Generation Framework ===")
message("Creating test data for CI/CD pipeline...\n")

# Load packages (with fallback for missing packages)
required_packages <- c("terra", "tidyverse")
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org", quiet = TRUE)
  }
  library(pkg, character.only = TRUE)
}

# Set seed for reproducibility
set.seed(42)

# ------------------------------------------------------------------------------
# 2. CONFIGURATION
# ------------------------------------------------------------------------------
# SSA approximate extent
ssa_extent <- terra::ext(-18, 52, -35, 15)

# Raster resolution (coarse for speed)
res <- 0.5  # ~55 km at equator

# Number of synthetic farms
n_farms <- 5000

# Countries with LSMS data
lsms_countries <- c(
  "Ethiopia", "Malawi", "Nigeria", "Tanzania", "Uganda", "Zambia",
  "Ghana", "Niger", "Mali", "Burkina", "Senegal", "Benin", 
  "Togo", "Rwanda", "Cote_d_Ivoire", "Guinea_Bissau"
)

# Country centroids (approximate)
country_coords <- data.frame(
  country = lsms_countries,
  lon = c(38, 34, 8, 35, 32, 28, -1, 8, -4, -1.5, -14, 2, 1, 30, -5, -15),
  lat = c(9, -13, 9, -6, 1, -15, 8, 17, 17, 12, 14, 9, 8, -2, 7, 12),
  stringsAsFactors = FALSE
)

# ------------------------------------------------------------------------------
# 3. CREATE DIRECTORY STRUCTURE
# ------------------------------------------------------------------------------
message("Creating directory structure...")

dirs <- c(
  "../data/raw/spatial/gadm",
  "../data/raw/spatial/spam/spam2010",
  "../data/raw/spatial/spam/spam2017",
  "../data/raw/spatial/spam/spam2020",
  "../data/raw/spatial/landuse",
  "../data/raw/spatial/cattle-density",
  "../data/raw/spatial/population",
  "../data/raw/spatial/soil_world",
  "../data/raw/spatial/wc2.1_30s",
  "../data/raw/spatial/temperature",
  "../data/raw/spatial/rainfall/rainfall_yearly",
  "../data/raw/spatial/rainfall/rainfall_monthly",
  "../data/raw/spatial/travel",
  "../data/raw/spatial/maize_water_lim_yield",
  "../data/raw/spatial/livestock-du2025",
  "../data/raw/web_scrapped/survey_data",
  "../data/raw/web_scrapped/faostat",
  "../data/processed",
  "../output/maps",
  "../output/graphs",
  "../output/tables/main",
  "../output/tables/supplementary",
  "../output/figures/main",
  "../output/figures/supplementary",
  "../output/reports"
)

for (d in dirs) {
  if (!dir.exists(d)) {
    dir.create(d, recursive = TRUE)
    message("  Created: ", d)
  }
}

# ------------------------------------------------------------------------------
# 4. GENERATE SYNTHETIC RASTER LAYERS
# ------------------------------------------------------------------------------
message("\nGenerating synthetic raster layers...")

#' Create a synthetic raster with realistic spatial autocorrelation
#' @param name Layer name
#' @param extent Terra extent object
#' @param res Resolution in degrees
#' @param mean_val Mean value for the layer
#' @param sd_val Standard deviation
#' @param positive Force positive values
#' @return SpatRaster
create_synthetic_raster <- function(name, extent, res, mean_val, sd_val, positive = TRUE) {
  # Create base raster
  r <- terra::rast(extent, res = res, crs = "EPSG:4326")
  
  # Generate spatially autocorrelated values using distance-based smoothing
  # Start with random values
  n_cells <- terra::ncell(r)
  values <- rnorm(n_cells, mean = mean_val, sd = sd_val)
  
  # Add spatial pattern (latitude-based gradient + noise)
  coords <- terra::xyFromCell(r, 1:n_cells)
  lat_effect <- (coords[, 2] - mean(coords[, 2])) / sd(coords[, 2]) * sd_val * 0.3
  lon_effect <- (coords[, 1] - mean(coords[, 1])) / sd(coords[, 1]) * sd_val * 0.1
  
  values <- values + lat_effect + lon_effect
  
  if (positive) {
    values <- pmax(values, 0)
  }
  
  terra::values(r) <- values
  names(r) <- name
  
  return(r)
}

# Generate predictor layers
message("  Creating cropland layer...")
cropland <- create_synthetic_raster("cropland", ssa_extent, res, 
                                     mean_val = 500, sd_val = 300)
terra::writeRaster(cropland, "../data/raw/spatial/spam/spam2017_cropland_ssa.tif", 
                   overwrite = TRUE)
terra::writeRaster(cropland, "../data/raw/spatial/spam/cropland_ssa.tif", 
                   overwrite = TRUE)

message("  Creating cattle density layer...")
cattle <- create_synthetic_raster("cattle", ssa_extent, res, 
                                   mean_val = 50, sd_val = 40)
terra::writeRaster(cattle, "../data/raw/spatial/cattle-density/2010_cattle_density_ssa.tif", 
                   overwrite = TRUE)

message("  Creating population density layer...")
pop <- create_synthetic_raster("pop", ssa_extent, res, 
                                mean_val = 100, sd_val = 150)
terra::writeRaster(pop, "../data/raw/spatial/population/2020_population_density_ssa.tif", 
                   overwrite = TRUE)

message("  Creating soil sand content layer...")
sand <- create_synthetic_raster("sand", ssa_extent, res, 
                                 mean_val = 40, sd_val = 20)
sand <- terra::clamp(sand, lower = 0, upper = 100)
terra::writeRaster(sand, "../data/raw/spatial/soil_world/sand_content_0_30cm_ssa.tif", 
                   overwrite = TRUE)

message("  Creating elevation layer...")
elevation <- create_synthetic_raster("elevation", ssa_extent, res, 
                                      mean_val = 800, sd_val = 500)
terra::writeRaster(elevation, "../data/raw/spatial/wc2.1_30s/elevation_ssa.tif", 
                   overwrite = TRUE)

message("  Creating slope layer...")
slope <- create_synthetic_raster("slope", ssa_extent, res, 
                                  mean_val = 0.05, sd_val = 0.03)
terra::writeRaster(slope, "../data/raw/spatial/wc2.1_30s/terrain_slope_ssa.tif", 
                   overwrite = TRUE)

message("  Creating temperature layer...")
temperature <- create_synthetic_raster("temperature", ssa_extent, res, 
                                         mean_val = 25, sd_val = 5, positive = FALSE)
temperature <- terra::clamp(temperature, lower = 10, upper = 35)
terra::writeRaster(temperature, "../data/raw/spatial/temperature/avg_temperature_ssa.tif", 
                   overwrite = TRUE)

message("  Creating rainfall layer...")
rainfall <- create_synthetic_raster("rainfall", ssa_extent, res, 
                                     mean_val = 1000, sd_val = 500)
terra::writeRaster(rainfall, "../data/raw/spatial/rainfall/rainfall_ssa.tif", 
                   overwrite = TRUE)
terra::writeRaster(rainfall, "../data/raw/spatial/rainfall/rainfall_yearly/#_long_term_rainfall_avg.tif", 
                   overwrite = TRUE)

message("  Creating market access layer...")
market <- create_synthetic_raster("market", ssa_extent, res, 
                                   mean_val = 120, sd_val = 80)
terra::writeRaster(market, "../data/raw/spatial/travel/travel_time_to_cities_ssa.tif", 
                   overwrite = TRUE)

message("  Creating maize yield layer...")
maizeyield <- create_synthetic_raster("maizeyield", ssa_extent, res, 
                                       mean_val = 5000, sd_val = 2000)
terra::writeRaster(maizeyield, "../data/raw/spatial/maize_water_lim_yield/maize_yield_ssa.tif", 
                   overwrite = TRUE)

# Cropland per capita
cropland_per_capita <- cropland / pop
cropland_per_capita[is.infinite(cropland_per_capita)] <- NA
names(cropland_per_capita) <- "cropland_per_capita"

# ------------------------------------------------------------------------------
# 5. CREATE STACKED PREDICTOR FILE
# ------------------------------------------------------------------------------
message("\nCreating stacked predictor files...")

all_predictors <- c(cropland, cattle, pop, cropland_per_capita,
                    sand, elevation, slope, temperature, rainfall, market, maizeyield)
names(all_predictors) <- c("cropland", "cattle", "pop", "cropland_per_capita",
                            "sand", "elevation", "slope", "temperature", 
                            "rainfall", "market", "maizeyield")

terra::writeRaster(all_predictors, "../data/processed/all_predictors.tif", overwrite = TRUE)
message("  Saved: all_predictors.tif")

# Stacked rasters for ML (subset)
stacked <- c(cropland, cattle, pop, cropland_per_capita, sand, slope,
             temperature, rainfall, maizeyield, market)
names(stacked) <- c("cropland", "cattle", "pop", "cropland_per_capita",
                     "sand", "slope", "temperature", "rainfall", "maizeyield", "market")

terra::writeRaster(stacked, "../data/processed/stacked_rasters_africa.tif", overwrite = TRUE)
message("  Saved: stacked_rasters_africa.tif")

# ------------------------------------------------------------------------------
# 6. GENERATE SYNTHETIC LSMS DATA
# ------------------------------------------------------------------------------
message("\nGenerating synthetic LSMS survey data...")

#' Generate synthetic farm data for a country
#' @param country Country name
#' @param n Number of farms
#' @param lon_center Country longitude center
#' @param lat_center Country latitude center
#' @return Data frame with farm data
generate_country_farms <- function(country, n, lon_center, lat_center) {
  # Generate locations around country center
  x <- rnorm(n, mean = lon_center, sd = 2)
  y <- rnorm(n, mean = lat_center, sd = 2)
  
  # Generate farm attributes
  # Farm size follows log-normal distribution (realistic)
  farm_area_ha <- rlnorm(n, meanlog = 0.3, sdlog = 0.8)
  farm_area_ha <- pmin(farm_area_ha, 50)  # Cap at 50 ha
  
  # Household size follows Poisson

  hh_size <- rpois(n, lambda = 5) + 1
  
  # Generate years (2008-2021)
  years <- sample(c(2010, 2012, 2014, 2016, 2018, 2020), n, replace = TRUE)
  
  data.frame(
    x = x,
    y = y,
    country = country,
    year = years,
    farm_id = paste0(country, "_", sprintf("%05d", 1:n)),
    hh_size = hh_size,
    farm_area_ha = round(farm_area_ha, 4),
    stringsAsFactors = FALSE
  )
}

# Generate data for all countries
farms_per_country <- ceiling(n_farms / length(lsms_countries))

lsms_data <- purrr::map2_dfr(
  country_coords$country,
  seq_len(nrow(country_coords)),
  function(cty, idx) {
    generate_country_farms(
      cty, 
      farms_per_country, 
      country_coords$lon[idx], 
      country_coords$lat[idx]
    )
  }
)

# Filter to SSA extent
lsms_data <- lsms_data |>
  filter(x >= -18, x <= 52, y >= -35, y <= 15)

message("  Generated ", nrow(lsms_data), " synthetic farms")

# Save raw LSMS data
write.csv(lsms_data, "../data/processed/lsms_and_zambia.csv", row.names = FALSE)
message("  Saved: lsms_and_zambia.csv")

# ------------------------------------------------------------------------------
# 7. CREATE ANALYSIS-READY DATASETS
# ------------------------------------------------------------------------------
message("\nCreating analysis-ready datasets...")

# Extract predictor values at farm locations
coords_df <- lsms_data |> select(x, y)
extracted_values <- terra::extract(stacked, coords_df, ID = FALSE)

# Combine with farm data
lsms_spatial <- cbind(
  lsms_data,
  gadm_0 = substr(lsms_data$country, 1, 3),
  gadm_1 = paste0(lsms_data$country, "_Region1"),
  gadm_2 = paste0(lsms_data$country, "_District1"),
  gadm_3 = NA,
  gadm_4 = NA,
  extracted_values
) |>
  na.omit()

# Save different trimmed versions
saveRDS(lsms_spatial, "../data/processed/lsms_untrimmed_africa.rds")
message("  Saved: lsms_untrimmed_africa.rds")

# 95th percentile trim by country
lsms_trimmed <- lsms_spatial |>
  group_by(country) |>
  filter(farm_area_ha <= quantile(farm_area_ha, 0.95)) |>
  ungroup()

saveRDS(lsms_trimmed, "../data/processed/lsms_trimmed_95th_africa.rds")
message("  Saved: lsms_trimmed_95th_africa.rds")

# 99th percentile trim
lsms_99 <- lsms_spatial |>
  group_by(country) |>
  filter(farm_area_ha <= quantile(farm_area_ha, 0.99)) |>
  ungroup()

saveRDS(lsms_99, "../data/processed/lsms_trimmed_99th_africa.rds")
message("  Saved: lsms_trimmed_99th_africa.rds")

# Final ML dataset
lsms_ml <- lsms_trimmed |>
  select(x, y, farm_area_ha, cropland, cattle, pop, cropland_per_capita,
         sand, slope, temperature, rainfall, maizeyield, market) |>
  na.omit()

write.csv(lsms_ml, "../data/processed/lsms_spatial.csv", row.names = FALSE)
saveRDS(lsms_ml, "../data/processed/lsms_spatial_africa.Rds")
message("  Saved: lsms_spatial.csv")

# Save stacked raster as RDS
saveRDS(stacked, "../data/processed/stacked_africa.Rds")

# ------------------------------------------------------------------------------
# 8. GENERATE COUNTRY-SPECIFIC RAW FILES
# ------------------------------------------------------------------------------
message("\nGenerating country-specific raw files...")

# Simulate individual country raw files (as would come from 02.1)
for (cty in unique(lsms_data$country)) {
  cty_data <- lsms_data |> filter(country == cty)
  
  # Add plot-level variables
  cty_raw <- cty_data |>
    mutate(
      ea_id = paste0(cty, "_EA_", sample(1:100, n(), replace = TRUE)),
      field_id = paste0(farm_id, "_F1"),
      plot_id = paste0(field_id, "_P1"),
      reported_area = farm_area_ha * runif(n(), 0.8, 1.2),
      report_unit = "hectare",
      reported_area_ha = reported_area,
      plot_land_use = "Cultivated",
      measured_plot = sample(c("Yes", "No"), n(), replace = TRUE, prob = c(0.7, 0.3)),
      measured_plot_area_ha = ifelse(measured_plot == "Yes", farm_area_ha, NA)
    )
  
  for (yr in unique(cty_raw$year)) {
    yr_data <- cty_raw |> filter(year == yr)
    filename <- paste0("../data/processed/", cty, "_", yr, "_raw.csv")
    write.csv(yr_data, filename, row.names = FALSE)
  }
}
message("  Generated raw files for ", length(unique(lsms_data$country)), " countries")

# ------------------------------------------------------------------------------
# 9. SUMMARY
# ------------------------------------------------------------------------------
message("\n")
message(paste(rep("=", 70), collapse = ""))
message("SYNTHETIC DATA GENERATION COMPLETE")
message(paste(rep("=", 70), collapse = ""))

message("\nGenerated files:")
message("  Raster layers:    ", length(list.files("../data/raw/spatial", 
                                                    pattern = "\\.tif$", recursive = TRUE)), " files")
message("  Processed data:   ", length(list.files("../data/processed", 
                                                    pattern = "\\.(csv|rds|Rds)$")), " files")
message("  Synthetic farms:  ", nrow(lsms_data))
message("  Countries:        ", length(unique(lsms_data$country)))

message("\nData characteristics:")
message("  Farm size range:  ", round(min(lsms_data$farm_area_ha), 2), " - ", 
        round(max(lsms_data$farm_area_ha), 2), " ha")
message("  Farm size median: ", round(median(lsms_data$farm_area_ha), 2), " ha")
message("  Raster extent:    ", paste(round(as.vector(ssa_extent), 1), collapse = ", "))
message("  Raster resolution:", res, " degrees")

message("\nYou can now run the pipeline scripts for testing!")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
