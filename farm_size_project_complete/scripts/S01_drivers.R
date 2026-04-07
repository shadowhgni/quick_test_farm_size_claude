# ==============================================================================
# Script: S01_drivers.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Supplementary Figure 1 — Spatial distributions of predictor variables
#          9 panels: cattle, pop, sand, slope, temperature, rainfall,
#                    maize yield, market access, cropland (SPAM 2017)
#          + 3 alternative cropland layers (SPAM 2020, ESA 2020, GEOSURVEY 2015)
#
# PRODUCTION inputs:
#   ../data/processed/stacked_rasters_africa.tif  — 10-layer predictor stack
#   <input_path>/landuse/landuse/all_cropland_mask.tif — 6 cropland products
#
# CI: stacked_rasters_africa.tif stub from 00.3_synthetic_data.R
#     all_cropland_mask.tif fallback to duplicated SPAM layer
# Output: ../output/other_illustr/graphs/Suppl.Fig01.png
# ==============================================================================

source("00_report_utils.R")
t0 <- proc.time()[["elapsed"]]
require(tidyverse)
setwd(paste0(here::here(), "/scripts"))
dir.create("../output/other_illustr/graphs", recursive = TRUE, showWarnings = FALSE)

# ── SSA boundary ──────────────────────────────────────────────────────────────
input_path <- "../data/raw/spatial"
country    <- geodata::world(path = input_path, resolution = 5, level = 0)
isocodes   <- geodata::country_codes()
if (!"UNREGION1" %in% names(isocodes)) {
  ssa_i3 <- c("AGO","CMR","CAF","TCD","COD","COG","GAB","GNQ","STP",
               "BWA","LSO","MWI","MOZ","NAM","ZAF","SWZ","ZMB","ZWE",
               "BDI","COM","DJI","ERI","ETH","KEN","MDG","MUS","RWA","SDN","SSD","SOM","TZA","UGA",
               "BEN","BFA","CPV","CIV","GMB","GHA","GIN","GNB","LBR","MLI","MRT","NER","NGA",
               "SEN","SLE","TGO","SDN")
  isocodes_ssa <- subset(isocodes, ISO3 %in% ssa_i3)
} else {
  isocodes_ssa <- subset(isocodes,
    NAME == "Sudan" |
    UNREGION1 %in% c("Middle Africa","Western Africa","Southern Africa","Eastern Africa"))
  isocodes_ssa <- subset(isocodes_ssa,
    !NAME %in% c("Cabo Verde","Comoros","Mauritius","Mayotte","Réunion",
                 "Saint Helena","São Tomé and Príncipe","Seychelles"))
}
ssa <- subset(country, country$GID_0 %in% isocodes_ssa$ISO3)

# ── Palettes ──────────────────────────────────────────────────────────────────
pal  <- colorRampPalette(c("darkred","orange","gold","darkolivegreen3","darkgreen"))
pal3 <- colorRampPalette(c("lightskyblue1","blue4"))
pal4 <- colorRampPalette(c("#A1D99B","#00441B"))
pal5 <- colorRampPalette(c("#FFFFCC","#800026"))
pal7 <- colorRampPalette(c("#C7EAE5","#01665E"))
pal9 <- colorRampPalette(c("#F1605DFF","#FD9567FF","#FEC98DFF","#FCFDBFFF"))

terra::terraOptions(memfrac = 0.5, todisk = TRUE)

# ── Load predictor stack ──────────────────────────────────────────────────────
stacked <- terra::rast("../data/processed/stacked_rasters_africa.tif")
stacked$slope <- 100 * stacked$slope

# ── Load cropland mask (CI fallback: duplicate SPAM layer) ───────────────────
cropland_mask_path <- file.path(input_path, "landuse/landuse/all_cropland_mask.tif")
six_crop_masks <- tryCatch(
  terra::rast(cropland_mask_path),
  error = function(e) {
    message("CI: all_cropland_mask.tif not found — using SPAM stub")
    r <- stacked[["cropland"]]
    r2 <- c(r, r, r)
    names(r2) <- c("SPAM 2020", "ESA 2020", "GEOSURVEY 2015")
    r2
  })

# ── Build tmap list ───────────────────────────────────────────────────────────
tmap::tmap_mode("plot")
tmap::tmap_options(component.autoscale = FALSE, asp = 1)
tmap_list <- list()

for (i in names(stacked)[c(2, 3, 5:10, 1)]) {
  my_range <- switch(i,
    cropland           = c(0, 5000),
    cattle             = c(0, 3000),
    pop                = c(0, 400),
    cropland_per_capita= c(0, 1000),
    sand               = c(0, 90),
    slope              = c(0, 3),
    temperature        = c(15, 40),
    rainfall           = c(0, 2000),
    maizeyield         = c(0, 15000),
    market             = c(0, 1000),
    c(0, 1000))

  my_tag <- switch(i,
    cropland = "I)", cattle = "A)", pop = "B)",
    sand = "C)", slope = "D)", temperature = "E)",
    rainfall = "F)", maizeyield = "G)", market = "H)",
    "?)")

  my_col <- switch(i,
    cropland            = pal4(10),
    cattle              = pal5(10),
    pop                 = pal7(10),
    cropland_per_capita = pal3(10),
    sand                = rev(pal(10)),
    slope               = rev(pal(10)),
    temperature         = rev(pal9(10)),
    rainfall            = pal3(10),
    maizeyield          = pal(10),
    market              = rev(pal(10)),
    pal(10))

  p <- tmap::tm_shape(stacked[[i]]) +
    tmap::tm_raster(
      col.scale = tmap::tm_scale_continuous(
        values = my_col, limits = my_range,
        outliers.trunc = c(TRUE, TRUE), labels = my_range),
      col.legend = tmap::tm_legend(
        title = "", frame = FALSE, text.size = 1,
        title.size = 0.01, title.align = "left")) +
    tmap::tm_shape(sf::st_as_sf(ssa)) +
    tmap::tm_borders(col = "black", lwd = 0.5) +
    tmap::tm_graticules(
      x = seq(-20, 60, by = 10), y = seq(-40, 20, by = 10),
      col = "gray70", lwd = 0.3, alpha = 0.7,
      labels.size = 0.6, labels.col = "gray50") +
    tmap::tm_layout(
      frame = FALSE, bg.color = "azure",
      legend.position = c(0, 0.7), legend.frame = FALSE,
      legend.bg.color = "transparent", legend.frame.lwd = 0,
      legend.width = 4.2, legend.height = 9) +
    tmap::tm_credits(my_tag,
      position = tmap::tm_pos_in("right", "top"), size = 1.5)

  tmap_list[[i]] <- p
}

# ── Alternative cropland layers ───────────────────────────────────────────────
for (i in names(six_crop_masks)[
    pmin(c(3, 4, 6), terra::nlyr(six_crop_masks))]) {
  my_tag <- switch(i,
    "SPAM 2020" = "J)", "ESA 2020" = "K)",
    "GEOSURVEY 2015" = "L)", "?)")

  p <- tmap::tm_shape(six_crop_masks[[i]]) +
    tmap::tm_raster(
      col.scale = tmap::tm_scale_continuous(
        values = pal4(10), limits = c(0, 5000),
        outliers.trunc = c(TRUE, TRUE), labels = c(0, 5000)),
      col.legend = tmap::tm_legend(
        title = "", frame = FALSE, text.size = 1,
        title.size = 0.01, title.align = "left")) +
    tmap::tm_shape(sf::st_as_sf(ssa)) +
    tmap::tm_borders(col = "black", lwd = 0.5) +
    tmap::tm_graticules(
      x = seq(-20, 60, by = 10), y = seq(-40, 20, by = 10),
      col = "gray70", lwd = 0.3, alpha = 0.7,
      labels.size = 0.6, labels.col = "gray50") +
    tmap::tm_layout(
      frame = FALSE, bg.color = "azure",
      legend.position = c(0, 0.7), legend.frame = FALSE,
      legend.bg.color = "transparent", legend.frame.lwd = 0,
      legend.width = 4.2, legend.height = 9) +
    tmap::tm_credits(my_tag,
      position = tmap::tm_pos_in("right", "top"), size = 1.5)

  tmap_list[[i]] <- p
}

# ── Save ──────────────────────────────────────────────────────────────────────
combined_plot <- tmap::tmap_arrange(tmap_list, ncol = 4)
tmap::tmap_save(combined_plot, "../output/other_illustr/graphs/Suppl.Fig01.png",
                width = 10, height = 7, units = "in", dpi = 150)

# ── Report ────────────────────────────────────────────────────────────────────
elapsed <- proc.time()[["elapsed"]] - t0
write_report(
  "S01_drivers.R",
  "Supp Fig 1: spatial distributions of predictor variables (9 predictors + 3 cropland layers)",
  inputs  = list("Stacked rasters" = "../data/processed/stacked_rasters_africa.tif"),
  outputs = list("PNG" = "../output/other_illustr/graphs/Suppl.Fig01.png"),
  elapsed_sec = elapsed)
message("S01_drivers.R done in ", round(elapsed, 1), "s")
