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

suppressPackageStartupMessages({
  library(terra)
  library(tidyverse)
})

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
res       <- 0.5

sixteen_countries      <- c("Benin","Burkina","Cote_d_Ivoire","Ethiopia","Ghana",
                             "Guinea_Bissau","Malawi","Mali","Niger","Nigeria",
                             "Rwanda","Senegal","Tanzania","Togo","Uganda","Zambia")
sixteen_country_codes  <- c("BEN","BFA","CIV","ETH","GHA","GNB","MWI","MLI",
                             "NER","NGA","RWA","SEN","TZA","TGO","UGA","ZMB")
country_lon  <- c(2,  -1.5, -5,  38,  -1,  -15,  34,  -4,   8,   8,   30, -14, 35,  1,  32,  28)
country_lat  <- c(9,  12,    7,   9,   8,   12, -13,  17,  17,   9,  -2,  14,  -6,  8,   1, -15)
n_per_country <- 1000   # ≥700 to pass the small-wave filter

# ==============================================================================
# 1. SYNTHETIC RASTERS
# ==============================================================================
message("1. Creating synthetic rasters...")

make_rast <- function(name, mn, sd, positive = TRUE, clamp = NULL) {
  r      <- terra::rast(ssa_ext, res = res, crs = "EPSG:4326")
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
rf_pred   <- make_rast("rf_mean", 2, 0.8)
terra::writeRaster(rf_pred,
  file.path(processed_path, "rf_model_predictions_SSA.tif"), overwrite = TRUE)
terra::writeRaster(rf_pred,
  file.path(processed_path, "rf_predictions_africa.tif"),     overwrite = TRUE)

# QRF: 100-quantile prediction stack
qrf_pred  <- terra::rast(replicate(100, make_rast("q", 2, 1.5)))
names(qrf_pred) <- paste0("q", 1:100)
terra::writeRaster(qrf_pred,
  file.path(processed_path, "qrf_100quantiles_predictions_africa.tif"), overwrite = TRUE)

# Forest / dryland masks (binary)
forest_mask <- make_rast("forest", 0.3, 0.3, clamp = c(0,1))
terra::writeRaster(forest_mask,
  file.path(processed_path, "mask_forest_ssa.tif"), overwrite = TRUE)
dryland_mask <- make_rast("dryland", 0.4, 0.3, clamp = c(0,1))
terra::writeRaster(dryland_mask,
  file.path(processed_path, "mask_drylands_ssa.tif"), overwrite = TRUE)

# Cropland mask (all cropland sources combined)
all_cropland <- make_rast("cropland_mask", 0.5, 0.3, clamp = c(0,1))
terra::writeRaster(all_cropland,
  file.path(raw_spatial, "landuse/landuse/all_cropland_mask.tif"), overwrite = TRUE)

# Farm-count rasters
nb_farms_grid <- make_rast("nb_farms", 500, 300)
terra::writeRaster(nb_farms_grid,
  file.path(processed_path, "nb_farms_per_grid_cell.tif"), overwrite = TRUE)
terra::writeRaster(nb_farms_grid,
  file.path(processed_path, "estim_nb_farms_per_country.tif"), overwrite = TRUE)

# 100-quantile raster (same as QRF for downstream)
terra::writeRaster(qrf_pred,
  file.path(processed_path, "hundred_quantiles_rasters.tif"), overwrite = TRUE)

# Distribution parameter rasters
farm_dist_parms <- terra::rast(replicate(3, make_rast("p", 1, 0.5)))
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

# ==============================================================================
# 2. SYNTHETIC LSMS SURVEY DATA
# ==============================================================================
message("2. Creating synthetic LSMS survey data...")

make_country_farms <- function(cty, lon_c, lat_c, n) {
  x              <- rnorm(n, lon_c, 1.5)
  y              <- rnorm(n, lat_c, 1.5)
  farm_area_ha   <- pmin(rlnorm(n, 0.3, 0.8), 50)
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
  lsms_farm_size    = lsms_raw |>
    select(x, y, country, year, farm_id, hh_size, farm_area_ha)
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
  v <- do.call(rbind, polys)
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

sixteen_count_distr <- do.call(rbind, gadm_list)

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
wide <- as.data.frame(
  cbind(model = model_names,
        setNames(replicate(16, round(runif(10, 0.2, 0.7), 2), simplify = FALSE),
                 sixteen_countries)))
write.csv(wide,  file.path(output_path, "tables/comparison_ML_models_per_country.csv"), row.names = FALSE)
saveRDS(wide,    file.path(output_path, "tables/comparison_ML_models_per_country.rds"))

gadm_rsq <- data.frame(
  country = rep(sixteen_countries, each = 4),
  gadm_1  = paste0(rep(sixteen_countries, each = 4), "_Reg", 1:4),
  rf_cv_rsq = round(runif(64, 0.2, 0.6), 2),
  gadm_test_rf_rsq = round(runif(64, 0.15, 0.55), 2)
)
write.csv(gadm_rsq, file.path(output_path, "tables/gadm_1__point_based_cross_validation.csv"), row.names = FALSE)

cty_auto <- data.frame(country = sixteen_countries,
  rsq = round(runif(16, 0.2, 0.7), 2))
write.csv(cty_auto, file.path(output_path, "tables/country_auto_evaluation_rsquares.csv"), row.names = FALSE)

pairwise <- expand.grid(train = sixteen_countries, test = sixteen_countries) |>
  mutate(rsq = round(runif(n(), 0.1, 0.7), 2))
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

# RF optimisation table (used by 06.1)
rf_optim <- data.frame(
  filename = paste0("rf_optim_", 1:20, ".rds"),
  mbucket  = 1:20,
  rsq      = round(runif(20, 0.3, 0.7), 3),
  mtry     = sample(2:6, 20, replace = TRUE),
  min.node.size = sample(3:10, 20, replace = TRUE)
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

# fsize_distribution_resample_long.rds (used by 08.3, 09.1, 10.1)
theor_farms <- lsms_ml |>
  select(x, y, country, farm_area_ha) |>
  mutate(q10 = farm_area_ha * 0.5, q50 = farm_area_ha, q90 = farm_area_ha * 1.8,
         pred_mean = farm_area_ha * runif(n(), 0.8, 1.2))
theor_farms_application <- theor_farms
saveRDS(list(theor_farms = theor_farms, theor_farms_application = theor_farms_application),
  file.path(processed_path, "fsize_distribution_resample_long.rds"))

# summarized_farm_area_ha_per_class_vs_sarah.rds (used by 09.1, S07)
summary_classes <- data.frame(
  size_class = c("<0.5","0.5-1","1-2","2-5","5-10",">10"),
  n_farms    = round(runif(6, 1e4, 5e5)),
  area_ha    = round(runif(6, 1e5, 1e7))
)
saveRDS(summary_classes, file.path(processed_path, "summarized_farm_area_ha_per_class_vs_sarah.rds"))

# cross_validation_graphs.rds (used by S06, T01)
cv_graphs <- list(
  country_results = data.frame(country = sixteen_countries,
    rsq = round(runif(16, 0.2, 0.7), 2)),
  summary = data.frame(model = model_names, mean_rsq = round(runif(10, 0.3, 0.6), 2))
)
saveRDS(cv_graphs, file.path(processed_path, "cross_validation_graphs.rds"))

# RF model .rdata (used by 05.2, 06.3 save targets — pre-create stubs)
# This is a trained ranger model stub
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

# point_and_unconsolidated_means file (used by 04.6)
pairwise$target  <- pairwise$test
pairwise$rsq_tps <- round(runif(nrow(pairwise), 0.1, 0.6), 2)
write.csv(pairwise,
  file.path(processed_path, "point_and_unconsolidated_means_models_TPS_RF_leave_one_out.csv"),
  row.names = FALSE)

message("   Processed stubs done.")

# ==============================================================================
# 7. FIGURE-SCRIPT STUBS  (fig2c.rds, fig.1a, fig.2a/b)
# ==============================================================================
message("7. Creating figure stubs...")

# fig2c.rds (used by F03)
fig2c <- data.frame(x = rnorm(200), y = rnorm(200), country = sample(sixteen_countries, 200, TRUE))
saveRDS(fig2c, "fig2c.rds")

# fig.1a, fig.2a, fig.2b (terra rasters used by F02, F03)
terra::writeRaster(rf_pred, "fig.1a_nb_of_farm_per_grid_cell.tif", overwrite = TRUE)
terra::writeRaster(rf_pred, "fig.2a_quantile_10_fsizes.tif",       overwrite = TRUE)
terra::writeRaster(rf_pred, "fig.2b_quantile_90_fsizes.tif",       overwrite = TRUE)

# Python prediction stubs (used by 07.2)
for (nm in c("Python_SPAM2010_rf_predictions_africa",
             "Python_SPAM2017_rf_predictions_africa",
             "Python_SPAM2020_rf_predictions_africa",
             "Python_Geosurvey2015_rf_predictions_africa",
             "Python_potapov_rf_predictions_africa",
             "Python_ESA2021_rf_predictions_africa")) {
  terra::writeRaster(rf_pred, file.path(processed_path, paste0(nm, ".tif")), overwrite = TRUE)
}

# S01_drivers specific file
fig3_s01 <- list(data = data.frame(x = 1:10, y = runif(10)))
saveRDS(fig3_s01, "2026-01-24.CHINA_croplands_per_crop_per_aez.rds")

# Supppl.Fig06 used by S07
div_table <- data.frame(var = pred_cols, divergence = runif(length(pred_cols)))
saveRDS(div_table, "Suppl.Fig06_divergence_table.rds")

message("   Figure stubs done.")

# ==============================================================================
# 8b. LEAVE-ONE STUBS for 04.5_cross_country_graphs.R
# ==============================================================================
message("8b. Creating leave-one stubs for 04.5...")

leave_one_dir <- file.path(output_path, "leave_one")
dir.create(leave_one_dir, recursive = TRUE, showWarnings = FALSE)

for (cty in sixteen_countries) {
  code <- sixteen_country_codes[match(cty, sixteen_countries)]
  n_pts <- 50L
  dummy_pred <- rnorm(n_pts)
  dummy_res  <- data.frame(country = cty, code = code, model = "RF",
                           means = FALSE, test = FALSE,
                           rsq = round(runif(1, 0.2, 0.6), 3))
  # RF leave-one: training on rest, test on country
  saveRDS(list(prediction = dummy_pred, results = dummy_res),
          file.path(leave_one_dir, paste0("loc_", code, "_RF_all_test.rds")))
  # TPS: evaluated on country only
  saveRDS(list(prediction = dummy_pred,
               results = data.frame(country = cty, code = code, model = "TPS",
                                    means = FALSE, test = TRUE,
                                    rsq = round(runif(1, 0.2, 0.6), 3))),
          file.path(leave_one_dir, paste0("loc_", code, "_TPS_all_test.rds")))
}

# Pre-save the summary outputs that 04.5's summarize() would produce
loo_rf  <- data.frame(country = sixteen_countries, code = sixteen_country_codes,
                      model = "RF", means = FALSE, test = FALSE,
                      rsq = round(runif(16, 0.2, 0.6), 3))
loo_tps <- data.frame(country = sixteen_countries, code = sixteen_country_codes,
                      model = "TPS", means = FALSE, test = TRUE,
                      rsq = round(runif(16, 0.2, 0.6), 3))
loo_cor <- data.frame(code = sixteen_country_codes, means = FALSE,
                      cor = round(runif(16, 0.5, 0.9), 3))

saveRDS(loo_rf,  file.path(output_path, "tables/leave_one_RF.rds"))
saveRDS(loo_tps, file.path(output_path, "tables/leave_one_TPS.rds"))
saveRDS(loo_cor, file.path(output_path, "tables/leave_one_cor.rds"))
saveRDS(loo_rf,  file.path(output_path, "leave_one_RF.rds"))
saveRDS(loo_tps, file.path(output_path, "leave_one_TPS.rds"))
saveRDS(loo_cor, file.path(output_path, "leave_one_cor.rds"))
message("   Leave-one stubs done  (", nrow(loo_rf), " countries × 2 models).")

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
message("  Prediction stubs:  6 Python + RF + QRF rasters")
message("  Output stubs:      ", length(list.files(file.path(output_path,"tables"))))
message("  Processed files:   ", length(list.files(processed_path)))
