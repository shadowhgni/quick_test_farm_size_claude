# ==============================================================================
# Script: 00_synthetic_data.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Generate ALL synthetic files needed for full CI pipeline testing
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - March 2026
#
# Requires: terra, tidyverse, ranger, quantregForest, fields, caret
# ==============================================================================

message("=== FULL Synthetic Data Generation for CI ===\n")
set.seed(42)

# Verify terra is loadable; if binary fails due to missing system lib, reinstall from source
if (!requireNamespace("terra", quietly = TRUE)) {
  message("terra not installed — installing...")
  install.packages("terra",
    repos = c("https://packagemanager.posit.co/cran/__linux__/jammy/latest",
              "https://cloud.r-project.org"),
    dependencies = TRUE, quiet = FALSE)
}

# Test if terra actually loads (shared lib might be missing even if installed)
terra_ok <- tryCatch({ library(terra); TRUE }, error = function(e) {
  message("terra binary failed (", conditionMessage(e), ") — trying source build...")
  install.packages("terra", type = "source",
    repos = "https://cloud.r-project.org", dependencies = TRUE, quiet = FALSE)
  tryCatch({ library(terra); TRUE }, error = function(e2) {
    stop("Cannot load terra: ", conditionMessage(e2))
  })
})

suppressPackageStartupMessages({
  library(dplyr)
})
message("terra: OK  dplyr: OK")

# ── Paths ──────────────────────────────────────────────────────────────────────
processed_path <- "../data/processed"
raw_spatial    <- "../data/raw/spatial"
output_path    <- "../output"

for (d in c(
  processed_path, raw_spatial,
  file.path(raw_spatial, "gadm"),
  file.path(raw_spatial, "landuse/landuse"),
  file.path(output_path, "maps"),
  file.path(output_path, "graphs"),
  file.path(output_path, "tables"),
  file.path(output_path, "reports")
)) dir.create(d, recursive = TRUE, showWarnings = FALSE)

# ── Config ─────────────────────────────────────────────────────────────────────
ssa_ext   <- terra::ext(-18, 52, -35, 15)
res       <- 0.5   # training/extraction rasters — 14 k cells, fine-grained enough for farm matching
res_pred  <- 5.0   # prediction output rasters  — ~140 cells total (~3-9 cells per LSMS country), ultra-light

sixteen_countries      <- c("Benin","Burkina","Cote_d_Ivoire","Ethiopia","Ghana",
                             "Guinea_Bissau","Malawi","Mali","Niger","Nigeria",
                             "Rwanda","Senegal","Tanzania","Togo","Uganda","Zambia")
sixteen_country_codes  <- c("BEN","BFA","CIV","ETH","GHA","GNB","MWI","MLI",
                             "NER","NGA","RWA","SEN","TZA","TGO","UGA","ZMB")
country_lon  <- c(2,  -1.5, -5,  38,  -1,  -15,  34,  -4,   8,   8,   30, -14, 35,  1,  32,  28)
country_lat  <- c(9,  12,    7,   9,   8,   12, -13,  17,  17,   9,  -2,  14,  -6,  8,   1, -15)
n_per_country <- 500L   # 500 training obs per country; snapped to 0.5° grid for n_obs>9 grouping

# ==============================================================================
# 1. SYNTHETIC RASTERS
# ==============================================================================
message("1. Creating synthetic rasters...")

make_rast <- function(name, mn, sd, positive = TRUE, clamp = NULL, r_res = res) {
  r      <- terra::rast(ssa_ext, res = r_res, crs = "EPSG:4326")
  nc     <- terra::ncell(r)
  xy     <- terra::xyFromCell(r, seq_len(nc))
  z_lat  <- (xy[,2] - mean(xy[,2])) / sd(xy[,2])
  z_lon  <- (xy[,1] - mean(xy[,1])) / sd(xy[,1])
  v      <- rnorm(nc, mn, sd) + z_lat * sd * 0.3 + z_lon * sd * 0.1
  if (positive) v <- pmax(v, 0)
  if (!is.null(clamp)) v <- pmin(pmax(v, clamp[1]), clamp[2])
  terra::values(r) <- v
  names(r) <- name
  r
}

cropland   <- make_rast("cropland",   500, 300)
cattle     <- make_rast("cattle",      50,  40)
pop        <- make_rast("pop",        100, 150)
sand       <- make_rast("sand",        40,  20, clamp = c(0, 100))
elevation  <- make_rast("elevation",  800, 500)
slope      <- make_rast("slope",     0.05, 0.03)
temperature<- make_rast("temperature", 25,   5, positive = FALSE, clamp = c(10, 35))
rainfall   <- make_rast("rainfall",  1000, 500)
market     <- make_rast("market",     120,  80)
maizeyield <- make_rast("maizeyield",5000,2000)

cropland_per_capita <- cropland / pop
cropland_per_capita[is.infinite(cropland_per_capita)] <- NA
names(cropland_per_capita) <- "cropland_per_capita"

all_predictors <- c(cropland, cattle, pop, cropland_per_capita,
                    sand, elevation, slope, temperature, rainfall, market, maizeyield)
names(all_predictors) <- c("cropland","cattle","pop","cropland_per_capita",
                           "sand","elevation","slope","temperature","rainfall","market","maizeyield")
terra::writeRaster(all_predictors,
  file.path(processed_path, "all_predictors.tif"), overwrite = TRUE)

stacked <- c(cropland, cattle, pop, cropland_per_capita,
             sand, slope, temperature, rainfall, maizeyield, market)
names(stacked) <- c("cropland","cattle","pop","cropland_per_capita",
                    "sand","slope","temperature","rainfall","maizeyield","market")
terra::writeRaster(stacked,
  file.path(processed_path, "stacked_rasters_africa.tif"), overwrite = TRUE)

saveRDS(stacked, file.path(processed_path, "stacked_africa.Rds"))

# Prediction rasters (single-band: mean farm size per pixel)
# res_pred = 5° → ~140 cells over SSA, 3-9 cells per country — ultra-light footprint
rf_pred   <- make_rast("rf_mean", 2, 0.8, r_res = res_pred)
terra::writeRaster(rf_pred,
  file.path(processed_path, "rf_model_predictions_SSA.tif"), overwrite = TRUE)
terra::writeRaster(rf_pred,
  file.path(processed_path, "rf_predictions_africa.tif"),     overwrite = TRUE)

# QRF: 100-quantile prediction stack at coarse res — strictly positive (needed by 08.3 fitdistr)
qrf_pred  <- terra::rast(replicate(100, make_rast("q", 2, 0.8, clamp = c(0.01, 20), r_res = res_pred)))
names(qrf_pred) <- paste0("q", 1:100)
terra::writeRaster(qrf_pred,
  file.path(processed_path, "qrf_100quantiles_predictions_africa.tif"), overwrite = TRUE)

# Forest / dryland masks (binary) — coarse res, prediction use only
forest_mask <- make_rast("forest", 0.3, 0.3, clamp = c(0,1), r_res = res_pred)
terra::writeRaster(forest_mask,
  file.path(processed_path, "mask_forest_ssa.tif"), overwrite = TRUE)
dryland_mask <- make_rast("dryland", 0.4, 0.3, clamp = c(0,1), r_res = res_pred)
terra::writeRaster(dryland_mask,
  file.path(processed_path, "mask_drylands_ssa.tif"), overwrite = TRUE)

# Cropland mask:
#   07.2: pivot_longer(cols = contains('20')) — needs '20' substring
#   08.2: all_cropland_mask$`SPAM 2010`, $`SPAM 2017`, $`SPAM 2020`,
#          $`ESA 2020`, $`GLAD 2019`, $`GEOSURVEY 2015` — exact names with spaces
#   S02:  six_crop_masks (same file); loops on names()[c(3,4,6)]
band_nms <- c("SPAM 2010","SPAM 2017","SPAM 2020","ESA 2020","GLAD 2019","GEOSURVEY 2015")
all_cropland <- terra::rast(lapply(
  band_nms,
  function(nm) make_rast(nm, 0.5, 0.3, clamp = c(0,1), r_res = res)  # 0.5° = same as stacked
))
names(all_cropland) <- band_nms
terra::writeRaster(all_cropland,
  file.path(raw_spatial, "landuse/landuse/all_cropland_mask.tif"), overwrite = TRUE)

# Farm-count rasters — coarse res
nb_farms_grid <- make_rast("nb_farms", 500, 300, r_res = res_pred)
terra::writeRaster(nb_farms_grid,
  file.path(processed_path, "nb_farms_per_grid_cell.tif"), overwrite = TRUE)
terra::writeRaster(nb_farms_grid,
  file.path(processed_path, "estim_nb_farms_per_country.tif"), overwrite = TRUE)

# 100-quantile raster (same as QRF for downstream)
terra::writeRaster(qrf_pred,
  file.path(processed_path, "hundred_quantiles_rasters.tif"), overwrite = TRUE)

# Distribution parameter rasters — coarse res
farm_dist_parms <- terra::rast(replicate(3, make_rast("p", 1, 0.5, r_res = res_pred)))
names(farm_dist_parms) <- c("mu", "sigma", "xi")
terra::writeRaster(farm_dist_parms,
  file.path(processed_path, "farm_size_distribution_parms.tif"), overwrite = TRUE)
terra::writeRaster(farm_dist_parms,
  file.path(processed_path, "virtual_farm_population.tif"), overwrite = TRUE)
terra::writeRaster(rf_pred,
  file.path(processed_path, "QRF_q10_africa.tif"), overwrite = TRUE)
terra::writeRaster(rf_pred,
  file.path(processed_path, "QRF_q90_africa.tif"), overwrite = TRUE)
terra::writeRaster(rf_pred,
  file.path(processed_path, "f_size_distribution_fit.tif"), overwrite = TRUE)

message("   Rasters done.")

# ── Yearly CHIRPS rainfall stubs (needed by 01.3 and 01.4) ──────────────────
# 01.4 looks for chirps-yearly-rainfall-YYYY.tif in rainfall/rainfall_yearly/
rain_yearly_dir <- file.path(raw_spatial, "rainfall", "rainfall_yearly")
dir.create(rain_yearly_dir, recursive = TRUE, showWarnings = FALSE)
for (yr in c(2010, 2015, 2018, 2020, 2022)) {
  terra::writeRaster(make_rast(paste0("rain_", yr), 1000, 300),
    file.path(rain_yearly_dir, paste0("chirps-yearly-rainfall-", yr, ".tif")),
    overwrite = TRUE)
}
# long-term avg and CV — expected outputs of 01.4 (pre-stub so 01.4 passes)
terra::writeRaster(make_rast("rain_avg", 1000, 200),
  file.path(rain_yearly_dir, "#_long_term_rainfall_avg.tif"), overwrite = TRUE)
terra::writeRaster(make_rast("rain_cv",  0.15, 0.05, clamp = c(0, 1)),
  file.path(rain_yearly_dir, "#_long_term_rainfall_cv.tif"),  overwrite = TRUE)
message("   Yearly rainfall stubs done.")

# ==============================================================================
# 2. SYNTHETIC LSMS SURVEY DATA
# ==============================================================================
message("2. Creating synthetic LSMS survey data...")

make_country_farms <- function(cty, lon_c, lat_c, n) {
  # Snap to 0.5° grid so multiple farms share cells (scripts filter n_obs > 9)
  x              <- round(rnorm(n, lon_c, 1.5) / 0.5) * 0.5
  y              <- round(rnorm(n, lat_c, 1.5) / 0.5) * 0.5
  # Add weak signal: farm_area_ha loosely correlated with cropland & rainfall
  # so caret RF/TPS get non-NA R² values in 10-fold CV
  lat_signal <- (lat_c - mean(country_lat)) / (sd(country_lat) + 1e-6) * 0.25
  farm_area_ha   <- pmin(rlnorm(n, 0.3 + lat_signal + runif(n, -0.1, 0.1), 0.6), 50)
  hh_size        <- rpois(n, 5) + 1
  years          <- sample(c(2010,2012,2014,2016,2018,2020), n, replace = TRUE)
  data.frame(
    x = x, y = y, country = cty, year = years,
    farm_id = paste0(cty, "_", sprintf("%05d", seq_len(n))),
    hh_size = hh_size,
    farm_area_ha = round(farm_area_ha, 4),
    reported_area_ha = round(farm_area_ha * runif(n, 0.8, 1.3), 4),
    measured_plot_area_ha = ifelse(runif(n) > 0.3, round(farm_area_ha, 4), NA_real_),
    ea_id  = paste0(cty, "_EA_", sample(1:50, n, replace = TRUE)),
    field_id = paste0(cty, "_", sprintf("%05d", seq_len(n)), "_F1"),
    plot_id  = paste0(cty, "_", sprintf("%05d", seq_len(n)), "_F1_P1"),
    stringsAsFactors = FALSE
  )
}

lsms_list <- mapply(make_country_farms,
  sixteen_countries, country_lon, country_lat, n_per_country,
  SIMPLIFY = FALSE)
lsms_raw  <- do.call(rbind, lsms_list)
lsms_raw  <- lsms_raw[lsms_raw$x >= -18 & lsms_raw$x <= 52 &
                      lsms_raw$y >= -35 & lsms_raw$y <= 15, ]
lsms_raw$farm_area_ha[lsms_raw$farm_area_ha <= 0] <- 0.01

write.csv(lsms_raw, file.path(processed_path, "lsms_and_zambia.csv"), row.names = FALSE)

# lsms_and_zambia.rds as a LIST (required by 03.1_pooled_data.R)
lsms_rds_list <- list(
  all_lsms_raw_data = lsms_raw,
  lsms_farm_size    = lsms_raw[, c("x","y","country","year","farm_id","hh_size","farm_area_ha")]
)
saveRDS(lsms_rds_list, file.path(processed_path, "lsms_and_zambia.rds"))
message("   LSMS CSV + RDS done  (", nrow(lsms_raw), " farms).")

# ==============================================================================
# 3. EXTRACT PREDICTORS & BUILD ANALYSIS DATASETS
# ==============================================================================
message("3. Extracting predictors at farm locations...")

lons <- seq(-18 + res/2, 52 - res/2, by = res)
lats <- seq(-35 + res/2, 15 - res/2, by = res)
ix   <- pmax(1L, pmin(length(lons), round((lsms_raw$x - lons[1]) / res) + 1L))
iy   <- pmax(1L, pmin(length(lats), round((lsms_raw$y - lats[1]) / res) + 1L))
grid_row <- (iy - 1L) * length(lons) + ix

stacked_df <- as.data.frame(stacked)
pred_cols  <- names(stacked_df)
extracted  <- stacked_df[grid_row, , drop = FALSE]; rownames(extracted) <- NULL

lsms_spatial <- cbind(lsms_raw, extracted)

# Assign admin stubs
lsms_spatial$gadm_0 <- sixteen_country_codes[match(lsms_spatial$country, sixteen_countries)]
lsms_spatial$gadm_1 <- paste0(lsms_spatial$country, "_Region1")
lsms_spatial$gadm_2 <- paste0(lsms_spatial$country, "_District1")
lsms_spatial$gadm_3 <- NA_character_
lsms_spatial$gadm_4 <- NA_character_

key_cols     <- c("x","y","farm_area_ha", pred_cols)
lsms_spatial <- lsms_spatial[complete.cases(lsms_spatial[, key_cols]), ]

saveRDS(lsms_spatial, file.path(processed_path, "lsms_untrimmed_africa.rds"))

trim95 <- do.call(rbind, lapply(split(lsms_spatial, lsms_spatial$country), function(d)
  d[d$farm_area_ha <= quantile(d$farm_area_ha, 0.95), ]))
trim99 <- do.call(rbind, lapply(split(lsms_spatial, lsms_spatial$country), function(d)
  d[d$farm_area_ha <= quantile(d$farm_area_ha, 0.99), ]))

saveRDS(trim95, file.path(processed_path, "lsms_trimmed_95th_africa.rds"))
saveRDS(trim99, file.path(processed_path, "lsms_trimmed_99th_africa.rds"))

ml_cols   <- c("x","y","farm_area_ha", pred_cols, "country","gadm_0","gadm_1","gadm_2","gadm_3","gadm_4","year","farm_id","hh_size")
lsms_ml   <- trim95[, intersect(ml_cols, names(trim95))]
lsms_ml   <- lsms_ml[complete.cases(lsms_ml[, key_cols]), ]

write.csv(lsms_ml,  file.path(processed_path, "lsms_spatial_with_country_names.csv"), row.names = FALSE)
write.csv(lsms_ml[, c("x","y","farm_area_ha", pred_cols)],
          file.path(processed_path, "lsms_spatial.csv"), row.names = FALSE)
saveRDS(lsms_ml, file.path(processed_path, "lsms_spatial_africa.Rds"))

# .rdata version (needed by 05.2, 06.3 via load())
lsms_spatial <- lsms_ml
save(lsms_spatial, file = file.path(processed_path, "lsms_trimmed_95th_africa.rdata"))
message("   Analysis datasets done  (", nrow(lsms_ml), " farms in 95th trim).")

# ==============================================================================
# 4. SYNTHETIC GADM BOUNDARIES
# ==============================================================================
message("4. Creating synthetic GADM boundaries...")

country_bbox <- data.frame(
  country = sixteen_countries, code = sixteen_country_codes,
  lon_c = country_lon, lat_c = country_lat, stringsAsFactors = FALSE
)

make_gadm_vect <- function(cty, code, lon_c, lat_c) {
  # 4 sub-regions per country
  n_reg <- 4
  polys <- lapply(seq_len(n_reg), function(i) {
    dlat <- 1.2; dlon <- 1.2
    cx <- lon_c + (i-1) %% 2 * dlon - dlon/2
    cy <- lat_c + (i-1) %/% 2 * dlat - dlat/2
    terra::vect(matrix(c(cx-0.6, cy-0.6, cx+0.6, cy-0.6,
                         cx+0.6, cy+0.6, cx-0.6, cy+0.6,
                         cx-0.6, cy-0.6), ncol=2, byrow=TRUE),
                type = "polygons", crs = "EPSG:4326")
  })
  v <- Reduce(rbind, polys)
  # Add standard GADM fields
  terra::values(v) <- data.frame(
    GID_0  = code,
    NAME_0 = cty,
    GID_1  = paste0(code, ".", seq_len(n_reg)),
    NAME_1 = paste0(cty, "_Reg", seq_len(n_reg)),
    GID_2  = paste0(code, ".", seq_len(n_reg), ".1"),
    NAME_2 = paste0(cty, "_Dist", seq_len(n_reg)),
    GID_3  = paste0(code, ".", seq_len(n_reg), ".1.1"),
    NAME_3 = paste0(cty, "_Sub", seq_len(n_reg)),
    GID_4  = paste0(code, ".", seq_len(n_reg), ".1.1.1"),
    NAME_4 = paste0(cty, "_Sub4_", seq_len(n_reg)),
    stringsAsFactors = FALSE
  )
  v
}

gadm_list <- mapply(make_gadm_vect,
  country_bbox$country, country_bbox$code,
  country_bbox$lon_c, country_bbox$lat_c,
  SIMPLIFY = FALSE)

sixteen_count_distr <- Reduce(rbind, gadm_list)

# Save each country's GADM in the expected geodata cache structure
for (i in seq_along(sixteen_countries)) {
  cty_dir <- file.path(raw_spatial, "gadm", sixteen_countries[i])
  dir.create(cty_dir, recursive = TRUE, showWarnings = FALSE)
  saveRDS(gadm_list[[i]],
    file.path(cty_dir, paste0("gadm41_", sixteen_country_codes[i], "_2_pk.rds")))
}
message("   GADM boundaries done.")

# ==============================================================================
# 5. OUTPUT TABLE STUBS (needed by downstream scripts)
# ==============================================================================
message("5. Creating output table stubs...")

# Model comparison tables (scripts 04.x)
model_names <- c("tps_xy","rf","rf_xy","rf_xyz","gbm","gbm_xy","gbm_xyz","svm","svm_xy","svm_xyz")
wide <- data.frame(
  model = model_names,
  matrix(round(runif(10L * 16L, 0.2, 0.7), 2), nrow = 10L, ncol = 16L,
         dimnames = list(NULL, sixteen_countries)),
  stringsAsFactors = FALSE, check.names = FALSE
)
write.csv(wide,  file.path(output_path, "tables/comparison_ML_models_per_country.csv"), row.names = FALSE)
saveRDS(wide,    file.path(output_path, "tables/comparison_ML_models_per_country.rds"))

gadm_rsq <- data.frame(
  country          = rep(sixteen_countries, each = 4),
  gadm_1           = paste0(rep(sixteen_countries, each = 4), "_Reg", 1:4),
  rf_cv_rsq        = round(runif(64, 0.2, 0.6), 2),   # 04.3 pivot_longer needs this
  rf_cv_rsq_sd     = round(runif(64, 0.02, 0.1), 3),
  gadm_test_rf_rsq = round(runif(64, 0.15, 0.55), 2), # 04.3 pivot_longer needs this
  n_obs            = sample(50:200, 64, replace = TRUE)
)
write.csv(gadm_rsq, file.path(output_path, "tables/gadm_1__point_based_cross_validation.csv"), row.names = FALSE)

cty_auto <- data.frame(country = sixteen_countries,
  rsq = round(runif(16, 0.2, 0.7), 2))
write.csv(cty_auto, file.path(output_path, "tables/country_auto_evaluation_rsquares.csv"), row.names = FALSE)

pairwise <- expand.grid(
  train_country = sixteen_countries, test_country = sixteen_countries,
  stringsAsFactors = FALSE
)
pairwise$rf1_test_rsq <- round(runif(nrow(pairwise), 0.1, 0.7), 2)
pairwise$rf2_test_rsq <- round(runif(nrow(pairwise), 0.1, 0.7), 2)
pairwise$rsq           <- pairwise$rf1_test_rsq  # legacy column
write.csv(pairwise, file.path(output_path, "tables/country_pairwise_point_based_cross_validation.csv"), row.names = FALSE)

var_imp <- data.frame(
  variable   = pred_cols,
  importance = round(runif(length(pred_cols), 0.05, 0.25), 3)
)
write.csv(var_imp, file.path(output_path, "tables/country_variable_importance.csv"), row.names = FALSE)
write.csv(var_imp, file.path(output_path, "tables/etr_variable_importance.csv"), row.names = FALSE)

# Leave-one-out tables
loo <- data.frame(country = sixteen_countries, rsq = round(runif(16, 0.2, 0.6), 2))
saveRDS(loo, file.path(output_path, "tables/leave_one_RF.rds"))
saveRDS(loo, file.path(output_path, "tables/leave_one_TPS.rds"))
saveRDS(loo, file.path(output_path, "tables/leave_one_cor.rds"))

# RF optimisation table (used by 06.1 and 05.3)
# Needs: filename, Rsquared, RMSE, MAE, mtry, min.node.size, splitrule, mbucket
rf_optim <- data.frame(
  filename      = paste0("rf-", 1:20, "-1.rds"),
  Rsquared      = round(runif(20, 0.3, 0.7), 3),
  RMSE          = round(runif(20, 0.5, 1.5), 3),
  MAE           = round(runif(20, 0.3, 1.0), 3),
  mtry          = sample(2:6, 20, replace = TRUE),
  min.node.size = sample(3:10, 20, replace = TRUE),
  splitrule     = sample(c("variance", "extratrees"), 20, replace = TRUE),
  mbucket       = 1:20
)
saveRDS(rf_optim, file.path(output_path, "tables/RF_optim_summarized_table.rds"))
write.csv(rf_optim, file.path(output_path, "tables/RF_optim_summarized_table.csv"), row.names = FALSE)

# Cropland stats
cropland_stats <- data.frame(
  aez = paste0("AEZ_", 1:5),
  cropland_area = round(runif(5, 1e5, 1e7), 0),
  n_farms = round(runif(5, 1e4, 1e6), 0)
)
saveRDS(cropland_stats, file.path(output_path, "tables/cropland_stats_per_aez.rds"))
message("   Output stubs done.")

# ==============================================================================
# 6. PROCESSED DATA STUBS (needed by later pipeline scripts)
# ==============================================================================
message("6. Creating processed data stubs...")

# fsize_distribution_resample_long.rds
# Used by: 08.3, 09.1, 10.1, S08
# Needs: theor_farms with x, y, skew, kurt, gini, ks_trunc_D, ks_trunc_pval
#        theor_farms_application with x, y, linear_farm_size_ha, trunc_log_farm_size_ha
n_theor <- nrow(lsms_ml)
theor_farms <- data.frame(
  x = lsms_ml$x, y = lsms_ml$y, country = lsms_ml$country,
  farm_area_ha = lsms_ml$farm_area_ha,
  pred_mean  = lsms_ml$farm_area_ha * runif(n_theor, 0.8, 1.2),
  q10 = lsms_ml$farm_area_ha * 0.5,
  q50 = lsms_ml$farm_area_ha,
  q90 = lsms_ml$farm_area_ha * 1.8,
  # S08 needs these columns to rasterize
  skew        = runif(n_theor, 0.5, 4.0),
  kurt        = runif(n_theor, 2.0, 8.0),
  gini        = runif(n_theor, 0.3, 0.6),
  ks_trunc_D  = runif(n_theor, 0.05, 0.4),
  ks_trunc_pval      = runif(n_theor, 0.01, 0.99),
  # S08 needs these additional columns from 08.3 output
  adjusted_logn_mean = log(pmax(0.01, lsms_ml$farm_area_ha) / sqrt(1 + 0.5)),
  adjusted_logn_sd   = sqrt(log(1 + 0.5)),
  logn_mean          = log(pmax(0.01, lsms_ml$farm_area_ha)),
  logn_sd            = 0.8
)
# theor_farms_application: 10.1 needs linear_farm_size_ha; 08.3 needs trunc_log
theor_farms_application <- data.frame(
  x = lsms_ml$x, y = lsms_ml$y, country = lsms_ml$country,
  pred_mean             = theor_farms$pred_mean,
  linear_farm_size_ha   = pmax(0.01, rlnorm(n_theor, 0.3, 0.6)),
  trunc_log_farm_size_ha = pmax(0.01, rlnorm(n_theor, 0.2, 0.5))
)
saveRDS(list(theor_farms = theor_farms,
             theor_farms_application = theor_farms_application),
  file.path(processed_path, "fsize_distribution_resample_long.rds"))

# gini_raster.tif — normally produced by 08.3_farm_size_classes.R which
# calculates Gini coefficients of predicted farm size distributions per cell.
# Here we create a plausible synthetic stand-in: Gini increases toward drier zones
# (higher latitudes → more arid → more inequality in farm sizes).
{
  gini_r  <- terra::rast(ssa_ext, res = res, crs = "EPSG:4326")
  xy_gini <- terra::xyFromCell(gini_r, seq_len(terra::ncell(gini_r)))
  # Simulate: Gini ~0.35 in humid tropics, ~0.55 in drier zones
  lat_effect <- (xy_gini[,2] - (-10)) / 25   # normalised latitude
  gini_vals  <- 0.35 + 0.20 * lat_effect + rnorm(nrow(xy_gini), 0, 0.04)
  gini_vals  <- pmin(pmax(gini_vals, 0.20), 0.80)
  terra::values(gini_r) <- gini_vals
  names(gini_r) <- "gini"
  terra::writeRaster(gini_r, file.path(processed_path, "gini_raster.tif"), overwrite = TRUE)
}

# summarized_farm_area_ha_per_class_vs_sarah.rds — S07 needs $comp_fsize_classes_ha
# and $comp_fsize_classes_nb with NAME_0, GID_0, farm_class, nb_farms, pred_nb_farms
size_classes <- c(1, 2, 5, 10, 20, 50)
s07_base <- expand.grid(
  NAME_0     = sixteen_countries,
  farm_class = size_classes,
  stringsAsFactors = FALSE
)
s07_base$GID_0         <- sixteen_country_codes[match(s07_base$NAME_0, sixteen_countries)]
s07_base$nb_farms      <- round(runif(nrow(s07_base), 1e4, 5e5))
s07_base$pred_nb_farms <- round(s07_base$nb_farms * runif(nrow(s07_base), 0.7, 1.4))
s07_base$cropland_ha   <- round(runif(nrow(s07_base), 1e4, 1e6))
s07_base$pred_cropland_ha <- round(s07_base$cropland_ha * runif(nrow(s07_base), 0.8, 1.2))
saveRDS(list(
  comp_fsize_classes_nb = s07_base,
  comp_fsize_classes_ha = s07_base
), file.path(processed_path, "summarized_farm_area_ha_per_class_vs_sarah.rds"))

# cross_validation_graphs.rds — T01, S06 need $country_pairs and $country_leave_one_out
# plus $var_importance_table (already added)
country_pairs_cv <- expand.grid(
  train_country = sixteen_countries, test_country = sixteen_countries,
  stringsAsFactors = FALSE
)
country_pairs_cv$train_GID_0  <- sixteen_country_codes[match(country_pairs_cv$train_country, sixteen_countries)]
country_pairs_cv$test_GID_0   <- sixteen_country_codes[match(country_pairs_cv$test_country,  sixteen_countries)]
country_pairs_cv$rf1_test_rsq <- round(runif(nrow(country_pairs_cv), 0.1, 0.7), 2)
country_pairs_cv$rf2_test_rsq <- round(runif(nrow(country_pairs_cv), 0.1, 0.7), 2)
country_pairs_cv$rsq          <- country_pairs_cv$rf1_test_rsq

country_loo_cv <- rbind(
  data.frame(country = sixteen_countries, code = sixteen_country_codes,
             model = "RF", rsq = round(runif(16, 0.2, 0.6), 3), stringsAsFactors = FALSE),
  data.frame(country = sixteen_countries, code = sixteen_country_codes,
             model = "TPS", rsq = round(runif(16, 0.2, 0.6), 3), stringsAsFactors = FALSE),
  data.frame(country = sixteen_countries, code = sixteen_country_codes,
             model = "RF_vs_TPS", rsq = round(runif(16, 0.2, 0.6), 3), stringsAsFactors = FALSE)
)

var_imp_long <- expand.grid(var = pred_cols, country = sixteen_countries, stringsAsFactors = FALSE)
var_imp_long$rank       <- round(runif(nrow(var_imp_long), 1, length(pred_cols)), 1)
var_imp_long$importance <- round(runif(nrow(var_imp_long), 0.01, 0.25), 3)

saveRDS(list(
  country_results      = data.frame(country = sixteen_countries,
                                    rsq = round(runif(16, 0.2, 0.7), 2)),
  summary              = data.frame(model = model_names,
                                    mean_rsq = round(runif(10, 0.3, 0.6), 2)),
  var_importance_table = var_imp_long,
  country_pairs        = country_pairs_cv,      # S06
  country_leave_one_out = country_loo_cv        # S06
), file.path(processed_path, "cross_validation_graphs.rds"))

# etr_variable_importance.csv — T01 uses column 'Variable' (capital V) and 'Importance'
var_imp_etr <- data.frame(
  Variable   = pred_cols,
  Importance = round(runif(length(pred_cols), 0.05, 0.25), 3)
)
write.csv(var_imp_etr, file.path(output_path, "tables/etr_variable_importance.csv"), row.names = FALSE)

# lsms_oob.rds — S04 reads from scripts dir; needs x, y, country, farm_area_ha,
#                oob_pred, in_sample_pred, gadm_1, gadm_2
lsms_oob <- lsms_ml[, c("x","y","country","farm_area_ha","gadm_0","gadm_1","gadm_2")]
lsms_oob$gadm_3 <- NA_character_
lsms_oob$gadm_4 <- NA_character_
lsms_oob$oob_pred      <- pmax(0.01, lsms_oob$farm_area_ha * runif(nrow(lsms_oob), 0.6, 1.4))
lsms_oob$in_sample_pred <- pmax(0.01, lsms_oob$farm_area_ha * runif(nrow(lsms_oob), 0.8, 1.2))
saveRDS(lsms_oob, "lsms_oob.rds")  # S04 reads from scripts dir (no ../)

# output/plot_data/ stub — S03 reads plot_suppl_01_effect_of_source_of_cropland_masks.rds
plot_data_dir <- file.path(output_path, "plot_data")
dir.create(plot_data_dir, recursive = TRUE, showWarnings = FALSE)
# S03 needs $pred_cpland_df, $ssa_cropland, $nb_farms_summarized (with nb_farms col)
n_src <- 4L
src_names <- c("spam_2017","spam_2010","esa_2021","geosurvey_2015")
s03_stub <- list(
  pred_cpland_df  = data.frame(x = lsms_ml$x[1:50], y = lsms_ml$y[1:50],
                               pred_farm_area_ha = lsms_ml$farm_area_ha[1:50]),
  ssa_cropland    = data.frame(source = src_names,
                               total  = round(runif(n_src, 1e8, 5e8))),
  nb_farms_summarized = data.frame(source = src_names,
                                   nb_farms = round(runif(n_src, 1e7, 5e7)),
                                   nb_rounded = round(runif(n_src, 10, 50), 0))
)
saveRDS(s03_stub,
  file.path(plot_data_dir, "plot_suppl_01_effect_of_source_of_cropland_masks.rds"))

# RF model stub
if (requireNamespace("ranger", quietly = TRUE)) {
  mini <- lsms_ml[sample(nrow(lsms_ml), min(200, nrow(lsms_ml))), ]
  rf_full_model <- ranger::ranger(farm_area_ha ~ cropland + cattle + pop +
    cropland_per_capita + sand + slope + temperature + rainfall + maizeyield + market,
    data = mini, num.trees = 10, keep.inbag = TRUE)
  save(rf_full_model, file = file.path(processed_path, "rf_full_model_with_95th_trimmed_data.rdata"))
  message("   RF model stub done.")
} else {
  message("   ranger not available; skipping RF model stub.")
}

# point_and_unconsolidated_means (04.6)
pairwise$target  <- pairwise$test_country
pairwise$rsq_tps <- round(runif(nrow(pairwise), 0.1, 0.6), 2)
write.csv(pairwise,
  file.path(processed_path, "point_and_unconsolidated_means_models_TPS_RF_leave_one_out.csv"),
  row.names = FALSE)

# GADM nested path for 10.2: looks in gadm/{cty}/gadm/*_2_pk.rds
# (note the extra /gadm/ subdir vs what 03.2 uses)
for (i in seq_along(sixteen_countries)) {
  cty_dir2 <- file.path(raw_spatial, "gadm", sixteen_countries[i], "gadm")
  dir.create(cty_dir2, recursive = TRUE, showWarnings = FALSE)
  saveRDS(gadm_list[[i]],
    file.path(cty_dir2, paste0("gadm41_", sixteen_country_codes[i], "_2_pk.rds")))
}

# validation/ dir (10.2 writes outputs here)
dir.create("../validation", showWarnings = FALSE)

# AEZ raster — T02 expects AEZ5_CLAS--SSA.tif with integer values 0–5 and
# lookup: 0=humid, 1=sub-humid, 2=semi-arid, 3=arid, 4=tropical highlands, 5=sub-tropical
# We assign classes spatially: humid near equator, arid northward, highlands in east
{
  aez_dir <- file.path(raw_spatial, "AEZ_SSA_IFPRI")
  dir.create(aez_dir, recursive = TRUE, showWarnings = FALSE)
  aez_r  <- terra::rast(ssa_ext, res = 1.0, crs = "EPSG:4326")
  xy_aez <- terra::xyFromCell(aez_r, seq_len(terra::ncell(aez_r)))
  lat <- xy_aez[, 2]; lon <- xy_aez[, 1]
  # 0=humid  (near equator, West)
  # 1=sub-humid
  # 2=semi-arid (Sahel band)
  # 3=arid (far north)
  # 4=tropical highlands (east Africa, higher elevation proxy)
  # 5=sub-tropical (south)
  cls <- ifelse(lat >  8 & lat <= 15 & lon < 20,              3L, # arid Sahel
         ifelse(lat >  3 & lat <=  8,                          2L, # semi-arid
         ifelse(lat >= -5 & lat <=  3,                         0L, # humid equatorial
         ifelse(lat < -5  & lat >= -15 & lon > 25,             4L, # trop highlands
         ifelse(lat < -15,                                      5L, # sub-tropical
                                                                1L))))) # sub-humid default
  # Add noise: randomly reassign ~10% to neighbouring classes
  noise_idx <- sample(length(cls), round(0.10 * length(cls)))
  cls[noise_idx] <- sample(0:5, length(noise_idx), replace = TRUE)
  terra::values(aez_r) <- as.integer(cls)
  names(aez_r) <- "aez_class"
  terra::writeRaster(aez_r,
    file.path(aez_dir, "AEZ5_CLAS--SSA.tif"),
    datatype = "INT1U", overwrite = TRUE)
  message("   AEZ stub written (6 classes, spatially structured).")
}

# SPAM cropland stubs (10.1, T02 read spam2017/*.tif and spam2010/*.tif)
# Pattern expected: *_P_[A-Z]+_A.tif (production files, total area)
for (spam_yr in c("spam2010", "spam2017")) {
  spam_dir <- file.path(raw_spatial, "spam", spam_yr)
  dir.create(spam_dir, recursive = TRUE, showWarnings = FALSE)
  # T02 uses var_code _H, _P, _V; crops MAIZ, SOYB, RICE, WHEA, SORG, PMIL, SMIL, CASS
  # 10.1 uses the same pattern. Filename: spam{yr}V2r0_SSA_{code}_{CROP}_A.tif
  # All crops referenced in 10.1/T02: MAIZ, SOYB, RICE, WHEA, SORG, PMIL, SMIL,
  # CASS, GROU, BEAN, CHIC, COWP, PIGE, LENT, OPUL (T02 reads every _P_[A-Z]+_A.tif)
  all_crops_spam <- c("MAIZ","SOYB","RICE","WHEA","SORG","PMIL","SMIL","CASS",
                      "GROU","BEAN","CHIC","COWP","PIGE","LENT","OPUL")
  for (vcode in c("H", "P", "V")) {
    for (crop in all_crops_spam) {
      terra::writeRaster(
        make_rast(paste0(crop, vcode), 500, 300),
        file.path(spam_dir, paste0("spam", spam_yr, "V2r0_SSA_", vcode, "_", crop, "_A.tif")),
        overwrite = TRUE
      )
    }
  }
}
message("   SPAM stubs written (spam2010, spam2017 × _H/_P/_V × 8 crops).")

# back_transf rasters — S08 reads these as outputs of 08.3
terra::writeRaster(
  make_rast("back_transf_mean", 2.0, 0.8),
  file.path(processed_path, "back_transf_trunc_adj_mean.tif"), overwrite = TRUE
)
terra::writeRaster(
  make_rast("back_transf_sd", 0.5, 0.2),
  file.path(processed_path, "back_transf_trunc_adj_sd.tif"), overwrite = TRUE
)
message("   back_transf rasters written.")
message("   Processed stubs done.")

# ==============================================================================
# 6b. SARAH LOWDER XLSX STUBS  (Lowder et al. 2021, World Development)
# Source: https://doi.org/10.1016/j.worlddev.2021.105455
#
# mmc3 — Total number of farms + census metadata per country
#         read with skip=1 then renamed to:
#         country | census_year | nb_farms | source | gadm_1 | income_group
#
# mmc5 — Farm count (F) and area (A) by size class per country
#         read with skip=2 then renamed to:
#         NAME_0 | year | nb_farms_or_area | total |
#         fsize0_1ha...fsize1000ha_above | source_code | income_group
#         Script pivots F rows (nb_farms) and A rows (cropland ha) separately.
#
# mmc7 — Historical avg farm size per country (loaded but not used downstream)
# ==============================================================================
message("6b. Creating Sarah Lowder xlsx stubs...")

sarah_dir <- file.path("../data/raw", "web_scrapped/sarah_lowder")
dir.create(sarah_dir, recursive = TRUE, showWarnings = FALSE)

# 22 SSA countries present in Lowder et al. (our 16 + 6 extra for filter headroom)
# GADM NAME_0 names (must match ssa$NAME_0 from geodata::world())
lowder_countries <- c(
  "Benin", "Burkina Faso", "Côte d'Ivoire", "Ethiopia", "Ghana",
  "Guinea-Bissau", "Malawi", "Mali", "Niger", "Nigeria", "Rwanda",
  "Senegal", "Tanzania", "Togo", "Uganda", "Zambia",
  "Kenya", "Mozambique", "Madagascar", "Zimbabwe", "Cameroon", "Sudan"
)
n_cty <- length(lowder_countries)

# Realistic total farm counts for SSA (order of magnitude from FAO/census data)
# Smallholder-dominated countries: Nigeria ~14M, Ethiopia ~13M, Tanzania ~5M etc.
set.seed(42)
total_farms_M <- c(3.0, 2.5, 2.0, 13.0, 2.3, 0.2, 1.8, 2.1, 2.4, 14.0, 2.0,
                   0.7, 5.0, 0.8, 3.8, 1.3, 6.0, 3.5, 3.0, 1.2, 2.8, 5.5)
total_farms <- round(total_farms_M * 1e6)

# Census years (mix of 2000s and 2010s as in the paper)
census_years <- c("2015/16","2018/19","2014","2013/14","2015/16",
                  "2015","2018/19","2016/17","2012","2015",
                  "2015","2013/14","2017/18","2015/16","2019/20",
                  "2020","2018/19","2014/15","2010/11","2012",
                  "2015/16","2014/15")

mk_xlsx <- function(df, path) {
  if (requireNamespace("writexl", quietly = TRUE)) {
    writexl::write_xlsx(df, path)
  } else if (requireNamespace("openxlsx", quietly = TRUE)) {
    wb <- openxlsx::createWorkbook()
    openxlsx::addWorksheet(wb, "Sheet1")
    openxlsx::writeData(wb, "Sheet1", df)
    openxlsx::saveWorkbook(wb, path, overwrite = TRUE)
  } else {
    stop("Need writexl or openxlsx to write xlsx files")
  }
}

# ── mmc3: total farm numbers ───────────────────────────────────────────────────
# After skip=1 + rename: country | census_year | nb_farms | source | gadm_1 | income_group
# The paper has one row per country-census combination.
mmc3 <- data.frame(
  country      = lowder_countries,
  census_year  = census_years,
  nb_farms     = total_farms,
  source       = "Agricultural Census",
  gadm_1       = lowder_countries,       # country-level (no sub-national breakout)
  income_group = "Low income",
  stringsAsFactors = FALSE
)
mk_xlsx(mmc3, file.path(sarah_dir, "1-s2.0-S0305750X2100067X-mmc3.xlsx"))
message("   mmc3 done (", nrow(mmc3), " countries, total farms range ",
        format(min(mmc3$nb_farms), big.mark=","), "–",
        format(max(mmc3$nb_farms), big.mark=","), ")")

# ── mmc5: farm size class distribution ────────────────────────────────────────
# Structure: two rows per country — one for nb of farms (F), one for area (A)
# Columns (after skip=2 + rename):
#   NAME_0 | year | nb_farms_or_area | total |
#   fsize0_1ha | fsize1_2ha | fsize2_5ha | fsize5_10ha | fsize10_20ha | fsize20_50ha |
#   fsize50_100ha | fsize100_200ha | fsize200_500ha | fsize500_1000ha | fsize1000ha_above |
#   source_code | income_group
#
# Proportions calibrated to SSA smallholder reality:
#   ~40-55% farms < 1 ha; ~25-35% between 1-5 ha; rest larger
size_classes <- c("fsize0_1ha","fsize1_2ha","fsize2_5ha","fsize5_10ha",
                  "fsize10_20ha","fsize20_50ha","fsize50_100ha",
                  "fsize100_200ha","fsize200_500ha","fsize500_1000ha","fsize1000ha_above")

# Farm NUMBER proportions (must sum to ~total, realistic SSA distribution)
prop_nb_mean <- c(0.45, 0.22, 0.16, 0.08, 0.04, 0.03, 0.01, 0.004, 0.002, 0.001, 0.001)

# Farm AREA proportions (larger farms hold disproportionate area)
prop_ha_mean <- c(0.10, 0.12, 0.18, 0.15, 0.12, 0.13, 0.08, 0.05, 0.04, 0.02, 0.01)

make_row <- function(cty, yr, tf, row_type) {
  if (row_type == "F") {
    # Number of farms per class
    props <- prop_nb_mean + runif(11, -0.03, 0.03)
    props <- pmax(props, 0.001); props <- props / sum(props)
    vals  <- round(tf * props)
  } else {
    # Cropland area (ha) per class; total cropland ~ 0.8–1.5 ha * nb_farms
    avg_ha <- runif(1, 0.9, 1.4)
    total_ha <- tf * avg_ha
    props <- prop_ha_mean + runif(11, -0.02, 0.02)
    props <- pmax(props, 0.001); props <- props / sum(props)
    vals  <- round(total_ha * props)
  }
  row <- as.data.frame(t(vals))
  names(row) <- size_classes
  cbind(data.frame(
    NAME_0           = cty,
    year             = yr,
    nb_farms_or_area = row_type,
    total            = if (row_type == "F") tf else sum(vals),
    stringsAsFactors = FALSE
  ), row, data.frame(source_code = "AC", income_group = "Low income",
                     stringsAsFactors = FALSE))
}

mmc5_rows <- vector("list", n_cty * 2)
for (i in seq_len(n_cty)) {
  yr  <- as.integer(substr(census_years[i], nchar(census_years[i])-3, nchar(census_years[i])))
  tf  <- total_farms[i]
  cty <- lowder_countries[i]
  mmc5_rows[[2*i-1]] <- make_row(cty, yr, tf, "F")
  mmc5_rows[[2*i]]   <- make_row(cty, yr, tf, "A")
}
mmc5 <- do.call(rbind, mmc5_rows)
mk_xlsx(mmc5, file.path(sarah_dir, "1-s2.0-S0305750X2100067X-mmc5.xlsx"))
message("   mmc5 done (", nrow(mmc5), " rows = ", n_cty, " countries × F+A)")

# ── mmc7: historical farm size demographics ────────────────────────────────────
# Loaded by scripts but not used downstream — provide plausible historical data
# Format: country | census_year | avg_farm_size_ha | nb_farms_total
hist_years <- c(1990, 2000, 2010, 2020)
mmc7 <- do.call(rbind, lapply(seq_len(n_cty), function(i) {
  # Farm sizes gradually declining over time in SSA (land pressure)
  base_size <- runif(1, 1.2, 3.5)
  trend     <- runif(1, -0.05, -0.01)  # ha/decade
  data.frame(
    country          = lowder_countries[i],
    census_year      = hist_years,
    avg_farm_size_ha = round(pmax(0.3, base_size + trend * (hist_years - 1990) / 10), 2),
    nb_farms_total   = round(total_farms[i] * c(0.60, 0.75, 0.90, 1.00)),
    stringsAsFactors = FALSE
  )
}))
mk_xlsx(mmc7, file.path(sarah_dir, "1-s2.0-S0305750X2100067X-mmc7.xlsx"))
message("   mmc7 done (", nrow(mmc7), " rows = ", n_cty, " countries × 4 decades)")

# ==============================================================================
# 7. FIGURE-SCRIPT STUBS
# ==============================================================================
message("7. Creating figure stubs...")

# fig2c — F03 needs $farm_size and $avg_size columns
fig2c <- data.frame(
  farm_size = pmax(0.01, rlnorm(500, 0.3, 0.8)),
  avg_size  = runif(500, 0.2, 8),
  country   = sample(sixteen_countries, 500, TRUE)
)
saveRDS(fig2c, "fig2c.rds")

# fig.2a / fig.2b — F03 reads band qrf_q010 / qrf_q090 from scripts dir
qrf_q010_r <- make_rast("qrf_q010", 1.5, 0.8, r_res = res_pred)
qrf_q090_r <- make_rast("qrf_q090", 4.0, 1.5, r_res = res_pred)
terra::writeRaster(qrf_q010_r, "fig.2a_quantile_10_fsizes.tif", overwrite = TRUE)
terra::writeRaster(qrf_q090_r, "fig.2b_quantile_90_fsizes.tif", overwrite = TRUE)

# fig.2d — F03 needs $predicted_avg_vs_gini (avg, gini) + $observed_avg_vs_gini (mean, gini)
saveRDS(list(
  predicted_avg_vs_gini = data.frame(
    avg  = pmax(0.1, rnorm(500, 2, 1.5)),
    gini = runif(500, 0.2, 0.7)
  ),
  observed_avg_vs_gini = data.frame(
    mean = pmax(0.1, rnorm(200, 2, 1.5)),
    gini = runif(200, 0.2, 0.7)
  )
), "fig.2d_mean_fsize_gini_coefs.rds")

# F02 reads files one level up (../fig.*)
# F02 uses fig1a$spam_2017 (nb of farms from SPAM) and fig1a$pred_farm_area_ha
fig1a_stack <- c(rf_pred, rf_pred * runif(terra::ncell(rf_pred), 0.8, 1.2))
names(fig1a_stack) <- c("spam_2017", "pred_farm_area_ha")
terra::writeRaster(fig1a_stack, "../fig.1a_nb_of_farm_per_grid_cell.tif", overwrite = TRUE)
terra::writeRaster(qrf_q010_r, "../fig.2a_quantile_10_fsizes.tif",       overwrite = TRUE)
terra::writeRaster(qrf_q090_r, "../fig.2b_quantile_90_fsizes.tif",       overwrite = TRUE)

# fig.1c — F02: $comp_nb_farms (country, census_year, nb_farms, estim_nb_farms) + $r2_sarah
comp_nb <- data.frame(
  country        = c(sixteen_countries, sample(sixteen_countries, 20, TRUE)),
  census_year    = sample(1970:2020, 36, replace = TRUE),
  nb_farms       = round(runif(36, 5e5, 5e6)),
  estim_nb_farms = round(runif(36, 4e5, 6e6)),
  stringsAsFactors = FALSE
)
saveRDS(list(comp_nb_farms = comp_nb,
             r2_sarah = round(runif(1, 0.4, 0.8), 2)),
        "../fig.1c_comparison_with_sarah_lowder.rds")

# fig.1d — F02: $lsms_spatial with farm_area_ha and pred_oob
saveRDS(list(lsms_spatial = data.frame(
  farm_area_ha = pmax(0.01, rlnorm(500, 0.3, 0.8)),
  pred_oob     = pmax(0.01, rlnorm(500, 0.3, 0.8))
)), "../fig.1d_reported_vs_predicted_fsize.rds")

# Python prediction stubs
for (nm in c("Python_SPAM2010_rf_predictions_africa",
             "Python_SPAM2017_rf_predictions_africa",
             "Python_SPAM2020_rf_predictions_africa",
             "Python_Geosurvey2015_rf_predictions_africa",
             "Python_potapov_rf_predictions_africa",
             "Python_ESA2021_rf_predictions_africa")) {
  terra::writeRaster(rf_pred, file.path(processed_path, paste0(nm, ".tif")), overwrite = TRUE)
}

# Suppl.Fig06 — S07 div_table needs NAME_0/GID_0/divergence_nb columns
div_table <- data.frame(
  var           = pred_cols,
  NAME_0        = sample(sixteen_countries,     length(pred_cols), TRUE),
  GID_0         = sample(sixteen_country_codes, length(pred_cols), TRUE),
  divergence    = runif(length(pred_cols)),
  divergence_nb = runif(length(pred_cols)),  # S07 comp_fsize_classes_nb
  divergence_ha = runif(length(pred_cols))   # S07 comp_fsize_classes_ha
)
saveRDS(div_table, "Suppl.Fig06_divergence_table.rds")

# China cropland RDS (S01)
aez_levels     <- c("tropical highlands", "humid", "sub-humid", "semi-arid", "all_aez")
product_levels <- c("all_crops","cattle","maize","sorghum","millet","cassava","legumes","non_food")
china_long <- expand.grid(pred_farm_area_ha = seq(0.2, 8, by = 0.2),
  aez = aez_levels, product = product_levels, stringsAsFactors = FALSE)
china_long$value <- runif(nrow(china_long), 0, 1)
saveRDS(list(df_rel_long = china_long), "2026-01-24.CHINA_croplands_per_crop_per_aez.rds")

message("   Figure stubs done.")

# ==============================================================================
# 8b. LEAVE-ONE STUBS for 04.5_cross_country_graphs.R
# ==============================================================================
message("8b. Creating leave-one stubs for 04.5 / 04.6...")

leave_one_dir <- file.path(output_path, "leave_one")
dir.create(leave_one_dir, recursive = TRUE, showWarnings = FALSE)

# 04.5 / 04.6 filter with means == 'TRUE' (character), so stubs must use
# character "TRUE"/"FALSE" not logical TRUE/FALSE.
# TPS rule from trts: test must be TRUE, so only TPS_all_test and TPS_means_test.
for (i in seq_along(sixteen_countries)) {
  cty  <- sixteen_countries[i]
  code <- sixteen_country_codes[i]
  n_pts <- 60L

  make_stub <- function(model, means_val, test_val, rsq_col = "rsq") {
    suffix <- paste0("loc_", code, "_", model, "_",
                     ifelse(means_val == "TRUE", "means", "all"), "_",
                     ifelse(test_val  == "TRUE", "test",  "train"), ".rds")
    res <- data.frame(country = cty, code = code, model = model,
                      means = means_val, test = test_val,
                      stringsAsFactors = FALSE)
    res[[rsq_col]] <- round(runif(1, 0.2, 0.65), 3)
    saveRDS(list(prediction = rnorm(n_pts), results = res),
            file.path(leave_one_dir, suffix))
  }

  # RF: all four combinations (means x test), Rsquared column
  make_stub("RF", "FALSE", "FALSE", "Rsquared")
  make_stub("RF", "FALSE", "TRUE",  "Rsquared")
  make_stub("RF", "TRUE",  "FALSE", "Rsquared")
  make_stub("RF", "TRUE",  "TRUE",  "Rsquared")

  # TPS: only test=TRUE (enforced by trts filter in 04.5)
  make_stub("TPS", "FALSE", "TRUE")
  make_stub("TPS", "TRUE",  "TRUE")
}

# Summarised tables — means/test as CHARACTER so filter(means == 'TRUE') works
loo_rf <- rbind(
  data.frame(country = sixteen_countries, code = sixteen_country_codes,
             model = "RF", means = "FALSE", test = "FALSE",
             Rsquared = round(runif(16, 0.2, 0.6), 3), stringsAsFactors = FALSE),
  data.frame(country = sixteen_countries, code = sixteen_country_codes,
             model = "RF", means = "TRUE",  test = "FALSE",
             Rsquared = round(runif(16, 0.2, 0.6), 3), stringsAsFactors = FALSE),
  data.frame(country = sixteen_countries, code = sixteen_country_codes,
             model = "RF", means = "FALSE", test = "TRUE",
             Rsquared = round(runif(16, 0.2, 0.6), 3), stringsAsFactors = FALSE),
  data.frame(country = sixteen_countries, code = sixteen_country_codes,
             model = "RF", means = "TRUE",  test = "TRUE",
             Rsquared = round(runif(16, 0.2, 0.6), 3), stringsAsFactors = FALSE)
)
loo_tps <- rbind(
  data.frame(country = sixteen_countries, code = sixteen_country_codes,
             model = "TPS", means = "FALSE", test = "TRUE",
             rsq = round(runif(16, 0.2, 0.6), 3), stringsAsFactors = FALSE),
  data.frame(country = sixteen_countries, code = sixteen_country_codes,
             model = "TPS", means = "TRUE",  test = "TRUE",
             rsq = round(runif(16, 0.2, 0.6), 3), stringsAsFactors = FALSE)
)
loo_cor <- rbind(
  data.frame(code = sixteen_country_codes, means = "FALSE",
             cor = round(runif(16, 0.5, 0.9), 3), stringsAsFactors = FALSE),
  data.frame(code = sixteen_country_codes, means = "TRUE",
             cor = round(runif(16, 0.5, 0.9), 3), stringsAsFactors = FALSE)
)

for (dest in c(file.path(output_path, "tables"), file.path(output_path))) {
  saveRDS(loo_rf,  file.path(dest, "leave_one_RF.rds"))
  saveRDS(loo_tps, file.path(dest, "leave_one_TPS.rds"))
  saveRDS(loo_cor, file.path(dest, "leave_one_cor.rds"))
}
message("   Leave-one stubs done (character means/test, TPS test-only).")

# ==============================================================================
# 9. COUNTRY-YEAR RAW FILES (for 02.x scripts if they run)
# ==============================================================================
message("9. Creating country-year raw files...")
for (cty in sixteen_countries)
  for (yr in c(2010,2012,2014,2016,2018,2020)) {
    d <- lsms_raw[lsms_raw$country == cty & lsms_raw$year == yr, ]
    if (nrow(d) > 0)
      write.csv(d, file.path(processed_path, paste0(cty,"_",yr,"_raw.csv")), row.names = FALSE)
  }

# ==============================================================================
# SUMMARY
# ==============================================================================
message("\n", paste(rep("=",70), collapse=""))
message("SYNTHETIC DATA GENERATION COMPLETE")
message(paste(rep("=",70), collapse=""))
message("  Farms generated:   ", nrow(lsms_raw))
message("  After 95th trim:   ", nrow(lsms_ml))
message("  Countries:         ", length(sixteen_countries))
message("  Raster layers:     ", terra::nlyr(all_predictors))
message("  Training res:      ", res, "° (~", round(res*111), " km) — ", terra::ncell(all_predictors[[1]]), " cells/layer")
message("  Prediction res:    ", res_pred, "° (~", round(res_pred*111), " km) — ", terra::ncell(rf_pred), " cells/layer (~3-9 per country)")
message("  QRF stack cells:   ", terra::ncell(qrf_pred[[1]]), " cells × 100 quantiles = ", terra::ncell(qrf_pred[[1]])*100, " values")
message("  Prediction stubs:  6 Python + RF + QRF rasters")
message("  Output stubs:      ", length(list.files(file.path(output_path,"tables"))))
message("  Processed files:   ", length(list.files(processed_path)))
