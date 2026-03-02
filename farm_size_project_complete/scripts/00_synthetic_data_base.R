# ==============================================================================
# Script: 00_synthetic_data_base.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Generate synthetic data for CI/CD testing using BASE R ONLY
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - March 2026
#
# Description:
#   TRUE BASE R version - zero external package dependencies.
#   Generates the same logical data structures as 00_synthetic_data.R but
#   stores raster layers as RDS data frames instead of .tif files so that
#   terra / Rcpp are not required at all.
#
# Output Files:
#   - ../data/processed/lsms_and_zambia.csv
#   - ../data/processed/lsms_trimmed_95th_africa.rds
#   - ../data/processed/lsms_trimmed_99th_africa.rds
#   - ../data/processed/lsms_untrimmed_africa.rds
#   - ../data/processed/lsms_spatial.csv
#   - ../data/processed/lsms_spatial_africa.Rds
#   - ../data/processed/raster_grid_africa.rds  (grid + predictor values as df)
# ==============================================================================

message("=== Synthetic Data Generation Framework ===")
message("Creating test data for CI/CD pipeline (base R only)...\n")

set.seed(42)

# ------------------------------------------------------------------------------
# 1. CONFIGURATION
# ------------------------------------------------------------------------------

# SSA approximate extent
lon_min <- -18; lon_max <- 52
lat_min <- -35; lat_max <- 15
res      <- 0.5   # degrees

n_farms  <- 5000

lsms_countries <- c(
  "Ethiopia", "Malawi", "Nigeria", "Tanzania", "Uganda", "Zambia",
  "Ghana", "Niger", "Mali", "Burkina", "Senegal", "Benin",
  "Togo", "Rwanda", "Cote_d_Ivoire", "Guinea_Bissau"
)

country_coords <- data.frame(
  country = lsms_countries,
  lon = c(38, 34,  8, 35, 32, 28, -1,  8, -4, -1.5, -14,  2,  1, 30, -5, -15),
  lat = c( 9,-13,  9, -6,  1,-15,  8, 17, 17,   12,  14,  9,  8, -2,  7,  12),
  stringsAsFactors = FALSE
)

# ------------------------------------------------------------------------------
# 2. CREATE DIRECTORY STRUCTURE
# ------------------------------------------------------------------------------
message("Creating directory structure...")

dirs <- c(
  "../data/processed",
  "../output/reports",
  "../output/tables",
  "../output/graphs"
)

for (d in dirs) {
  if (!dir.exists(d)) {
    dir.create(d, recursive = TRUE)
    message("  Created: ", d)
  }
}

# ------------------------------------------------------------------------------
# 3. GENERATE SYNTHETIC RASTER GRID (as data frame, no terra)
# ------------------------------------------------------------------------------
message("\nGenerating synthetic raster grid...")

lons <- seq(lon_min + res/2, lon_max - res/2, by = res)
lats <- seq(lat_min + res/2, lat_max - res/2, by = res)
grid <- expand.grid(x = lons, y = lats)

n_cells <- nrow(grid)

# Spatial gradient helper
lat_z <- (grid$y - mean(grid$y)) / sd(grid$y)
lon_z <- (grid$x - mean(grid$x)) / sd(grid$x)

make_layer <- function(mean_val, sd_val, positive = TRUE) {
  v <- rnorm(n_cells, mean_val, sd_val) + lat_z * sd_val * 0.3 + lon_z * sd_val * 0.1
  if (positive) v <- pmax(v, 0)
  v
}

grid$cropland            <- make_layer(500,  300)
grid$cattle              <- make_layer( 50,   40)
grid$pop                 <- make_layer(100,  150)
grid$sand                <- pmin(pmax(make_layer(40, 20), 0), 100)
grid$elevation           <- make_layer(800,  500)
grid$slope               <- make_layer(0.05, 0.03)
grid$temperature         <- pmin(pmax(make_layer(25, 5, positive = FALSE), 10), 35)
grid$rainfall            <- make_layer(1000, 500)
grid$market              <- make_layer(120,   80)
grid$maizeyield          <- make_layer(5000, 2000)
grid$cropland_per_capita <- ifelse(grid$pop > 0, grid$cropland / grid$pop, NA)

saveRDS(grid, "../data/processed/raster_grid_africa.rds")
message("  Saved: raster_grid_africa.rds (", n_cells, " grid cells, ",
        ncol(grid) - 2, " predictor layers)")

# ------------------------------------------------------------------------------
# 4. GENERATE SYNTHETIC LSMS SURVEY DATA
# ------------------------------------------------------------------------------
message("\nGenerating synthetic LSMS survey data...")

farms_per_country <- ceiling(n_farms / length(lsms_countries))

generate_country_farms <- function(country, n, lon_c, lat_c) {
  x            <- rnorm(n, lon_c, 2)
  y            <- rnorm(n, lat_c, 2)
  farm_area_ha <- pmin(rlnorm(n, meanlog = 0.3, sdlog = 0.8), 50)
  hh_size      <- rpois(n, lambda = 5) + 1
  years        <- sample(c(2010, 2012, 2014, 2016, 2018, 2020), n, replace = TRUE)
  data.frame(
    x            = x,
    y            = y,
    country      = country,
    year         = years,
    farm_id      = paste0(country, "_", sprintf("%05d", seq_len(n))),
    hh_size      = hh_size,
    farm_area_ha = round(farm_area_ha, 4),
    stringsAsFactors = FALSE
  )
}

lsms_list <- mapply(
  generate_country_farms,
  country_coords$country,
  farms_per_country,
  country_coords$lon,
  country_coords$lat,
  SIMPLIFY = FALSE
)
lsms_data <- do.call(rbind, lsms_list)

# Filter to SSA extent
lsms_data <- lsms_data[
  lsms_data$x >= lon_min & lsms_data$x <= lon_max &
  lsms_data$y >= lat_min & lsms_data$y <= lat_max, ]

message("  Generated ", nrow(lsms_data), " synthetic farms across ",
        length(unique(lsms_data$country)), " countries")

write.csv(lsms_data, "../data/processed/lsms_and_zambia.csv", row.names = FALSE)
message("  Saved: lsms_and_zambia.csv")

# ------------------------------------------------------------------------------
# 5. EXTRACT PREDICTOR VALUES AT FARM LOCATIONS (nearest-cell join)
# ------------------------------------------------------------------------------
message("\nExtracting predictor values at farm locations...")

# Index-based nearest-cell lookup (avoids floating-point merge failures)
# Find the closest grid lon/lat index for each farm point
ix <- pmax(1L, pmin(length(lons), round((lsms_data$x - lons[1]) / res) + 1L))
iy <- pmax(1L, pmin(length(lats), round((lsms_data$y - lats[1]) / res) + 1L))
# grid rows are ordered expand.grid(x=lons, y=lats) => row = (iy-1)*length(lons) + ix
grid_row <- (iy - 1L) * length(lons) + ix

pred_cols   <- setdiff(names(grid), c("x", "y"))
extracted   <- grid[grid_row, pred_cols, drop = FALSE]
rownames(extracted) <- NULL
lsms_spatial <- cbind(lsms_data, extracted)

# Add admin stubs
lsms_spatial$gadm_0 <- substr(lsms_spatial$country, 1, 3)
lsms_spatial$gadm_1 <- paste0(lsms_spatial$country, "_Region1")
lsms_spatial$gadm_2 <- paste0(lsms_spatial$country, "_District1")
# Only drop rows where key predictor/coordinate columns are NA
key_cols     <- c("x", "y", "farm_area_ha", pred_cols)
lsms_spatial <- lsms_spatial[complete.cases(lsms_spatial[, key_cols]), ]

# ------------------------------------------------------------------------------
# 6. SAVE ANALYSIS-READY DATASETS
# ------------------------------------------------------------------------------
message("\nSaving analysis-ready datasets...")

saveRDS(lsms_spatial, "../data/processed/lsms_untrimmed_africa.rds")
message("  Saved: lsms_untrimmed_africa.rds")

# 95th percentile trim by country
lsms_trimmed <- do.call(rbind, lapply(
  split(lsms_spatial, lsms_spatial$country),
  function(d) d[d$farm_area_ha <= quantile(d$farm_area_ha, 0.95), ]
))
saveRDS(lsms_trimmed, "../data/processed/lsms_trimmed_95th_africa.rds")
message("  Saved: lsms_trimmed_95th_africa.rds")

# 99th percentile trim
lsms_99 <- do.call(rbind, lapply(
  split(lsms_spatial, lsms_spatial$country),
  function(d) d[d$farm_area_ha <= quantile(d$farm_area_ha, 0.99), ]
))
saveRDS(lsms_99, "../data/processed/lsms_trimmed_99th_africa.rds")
message("  Saved: lsms_trimmed_99th_africa.rds")

# ML-ready flat CSV
predictor_cols <- c("cropland", "cattle", "pop", "cropland_per_capita",
                    "sand", "slope", "temperature", "rainfall", "maizeyield", "market")
lsms_ml <- lsms_trimmed[, c("x", "y", "farm_area_ha", predictor_cols)]
lsms_ml <- lsms_ml[complete.cases(lsms_ml), ]

write.csv(lsms_ml, "../data/processed/lsms_spatial.csv", row.names = FALSE)
saveRDS(lsms_ml,   "../data/processed/lsms_spatial_africa.Rds")
message("  Saved: lsms_spatial.csv + lsms_spatial_africa.Rds")

# Country-year raw files
for (cty in unique(lsms_data$country)) {
  cty_data <- lsms_data[lsms_data$country == cty, ]
  for (yr in unique(cty_data$year)) {
    yr_data  <- cty_data[cty_data$year == yr, ]
    filename <- paste0("../data/processed/", cty, "_", yr, "_raw.csv")
    write.csv(yr_data, filename, row.names = FALSE)
  }
}
message("  Generated raw files for ", length(unique(lsms_data$country)), " countries")

# ------------------------------------------------------------------------------
# 7. SUMMARY
# ------------------------------------------------------------------------------
message("\n", paste(rep("=", 70), collapse = ""))
message("SYNTHETIC DATA GENERATION COMPLETE (base R)")
message(paste(rep("=", 70), collapse = ""))
message("\nKey files:")
message("  raster_grid_africa.rds   - ", n_cells, " grid cells, 11 predictor layers")
message("  lsms_and_zambia.csv      - ", nrow(lsms_data), " farms (raw)")
message("  lsms_trimmed_95th.rds    - ", nrow(lsms_trimmed), " farms (trimmed)")
message("  lsms_spatial.csv         - ", nrow(lsms_ml), " farms (ML-ready)")
message("\nFarm size range:  ",
        round(min(lsms_data$farm_area_ha), 2), " - ",
        round(max(lsms_data$farm_area_ha), 2), " ha")
message("Median farm size: ", round(median(lsms_data$farm_area_ha), 2), " ha")
message("\nReady for pipeline testing!")

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
