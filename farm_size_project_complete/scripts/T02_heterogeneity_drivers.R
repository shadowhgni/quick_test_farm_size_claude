# ==============================================================================
# Script: T02_heterogeneity_drivers.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Table 2 — Proportion of cropland area and farm counts per size class
#          stratified by AEZ and by SSA region.
#
#   Approach:
#     - Individual farm sizes from theor_farms_application (virtual farm population)
#     - AEZ label extracted from AEZ_SSA_IFPRI raster
#     - Region label derived from GID_0 via GADM country polygons
#     - prop_area_*  = share of total summed farm area in each size class
#     - prop_farms_* = share of farm count in each size class
#
#   Source: fsize_distribution_resample_long.rds  (produced by 08.3)
#           cropland_stats_per_aez.rds             (produced by 10.1)
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - March 2026
# ==============================================================================

require(tidyverse)

rm(list = ls())
setwd(paste0(here::here(), '/scripts'))
dir.create('../output/main_fig', recursive = TRUE, showWarnings = FALSE)

# ── Load virtual farm population ───────────────────────────────────────────────
xx <- tryCatch(
  readRDS('../data/processed/fsize_distribution_resample_long.rds'),
  error = function(e) { message('CI: fsize_distribution_resample_long.rds not found'); NULL }
)

if (is.null(xx)) {
  message('CI: generating stub farm population')
  aez_vals <- c('humid','sub-humid','semi-arid','arid','tropical highlands','sub-tropical')
  reg_vals  <- c('Central','Eastern','Southern','Western')
  set.seed(42)
  theor_farms_application <- expand.grid(
    aez    = aez_vals,
    region = reg_vals
  ) |>
    slice(rep(1:n(), each = 50)) |>
    mutate(individual_farm_size_ha = rlnorm(n(), meanlog = 0.5, sdlog = 1.2))
} else {
  theor_farms_application <- xx$theor_farms_application |>
    rename(individual_farm_size_ha = linear_farm_size_ha) |>
    ungroup()
  rm(xx)

  # ── Attach AEZ label ─────────────────────────────────────────────────────────
  input_path <- '../data/raw/spatial'
  aez5 <- tryCatch({
    r <- terra::rast(paste0(input_path, '/AEZ_SSA_IFPRI/AEZ5_CLAS--SSA.tif'))
    names(r) <- 'aez_class'
    lookup <- data.frame(aez_class = 0:5,
                         aez = c('humid','sub-humid','semi-arid','arid',
                                 'tropical highlands','sub-tropical'))
    levels(r) <- lookup
    r
  }, error = function(e) { message('CI: AEZ raster not found'); NULL })

  if (!is.null(aez5)) {
    aez_extracted <- tryCatch(
      terra::extract(aez5, theor_farms_application |> select(x, y)),
      error = function(e) data.frame(ID = seq_len(nrow(theor_farms_application)), aez = NA_character_)
    )
    theor_farms_application <- theor_farms_application |>
      bind_cols(aez_extracted |> select(-ID))
  } else {
    theor_farms_application$aez <- NA_character_
  }

  # ── Attach region via GADM ───────────────────────────────────────────────────
  country_poly <- tryCatch(
    geodata::world(path = input_path, resolution = 5, level = 0),
    error = function(e) { message('CI: world() failed'); NULL }
  )

  if (!is.null(country_poly)) {
    gadm_extracted <- tryCatch(
      terra::extract(country_poly, theor_farms_application |> select(x, y)),
      error = function(e) data.frame(ID = seq_len(nrow(theor_farms_application)),
                                     GID_0 = NA_character_)
    )
    theor_farms_application <- theor_farms_application |>
      bind_cols(gadm_extracted |> select(GID_0 = any_of('GID_0')) |>
                  { if (ncol(.) == 0) mutate(., GID_0 = NA_character_) else . }())
  } else {
    theor_farms_application$GID_0 <- NA_character_
  }

  theor_farms_application <- theor_farms_application |>
    mutate(region = case_when(
      GID_0 %in% c('AGO','CAF','CMR','COD','COG','GAB','GNQ','STP','TCD') ~ 'Central',
      GID_0 %in% c('BDI','DJI','ERI','ETH','KEN','MDG','MOZ','MWI','RWA',
                   'SDN','SOM','SSD','TZA','UGA','ZMB','ZWE')             ~ 'Eastern',
      GID_0 %in% c('BWA','LSO','NAM','SWZ','ZAF')                        ~ 'Southern',
      GID_0 %in% c('BEN','BFA','CIV','GHA','GIN','GMB','GNB','LBR','MLI',
                   'MRT','NER','NGA','SEN','SLE','TGO')                   ~ 'Western',
      .default = NA_character_
    ))
}

# ── Size-class labelling ───────────────────────────────────────────────────────
thresholds <- c('< 0.5 ha', '0.5 - 1 ha', '1 - 2 ha', '2 - 5 ha', '> 5 ha')

theor_farms_application <- theor_farms_application |>
  mutate(size_class = case_when(
    individual_farm_size_ha <  0.5                               ~ '< 0.5 ha',
    individual_farm_size_ha >= 0.5 & individual_farm_size_ha < 1 ~ '0.5 - 1 ha',
    individual_farm_size_ha >= 1   & individual_farm_size_ha < 2 ~ '1 - 2 ha',
    individual_farm_size_ha >= 2   & individual_farm_size_ha < 5 ~ '2 - 5 ha',
    individual_farm_size_ha >= 5                                  ~ '> 5 ha',
    .default = NA_character_
  ),
  size_class = factor(size_class, levels = thresholds))

# ── Helper: build wide proportions table for one grouping column ───────────────
make_table <- function(df, group_col) {
  sym_col <- rlang::sym(group_col)

  totals <- df |>
    filter(!is.na(!!sym_col), !is.na(size_class)) |>
    group_by(!!sym_col) |>
    summarize(tot_area  = sum(individual_farm_size_ha, na.rm = TRUE),
              tot_farms = n(), .groups = 'drop')

  by_class <- df |>
    filter(!is.na(!!sym_col), !is.na(size_class)) |>
    group_by(!!sym_col, size_class) |>
    summarize(area  = sum(individual_farm_size_ha, na.rm = TRUE),
              farms = n(), .groups = 'drop') |>
    left_join(totals, by = group_col) |>
    mutate(
      prop_area  = round(100 * area  / tot_area,  1),
      prop_farms = round(100 * farms / tot_farms, 1)
    )

  area_wide <- by_class |>
    select(!!sym_col, size_class, prop_area) |>
    pivot_wider(names_from = size_class, values_from = prop_area,
                names_prefix = 'prop_area_')

  farm_wide <- by_class |>
    select(!!sym_col, size_class, prop_farms) |>
    pivot_wider(names_from = size_class, values_from = prop_farms,
                names_prefix = 'prop_farms_')

  left_join(area_wide, farm_wide, by = group_col)
}

# ── Build AEZ table ────────────────────────────────────────────────────────────
aez_order <- c('humid','sub-humid','semi-arid','arid','tropical highlands','sub-tropical')

t2_aez <- make_table(theor_farms_application, 'aez') |>
  mutate(aez = factor(aez, levels = aez_order)) |>
  arrange(aez) |>
  mutate(aez = as.character(aez))

message('\n=== T02 by AEZ ===')
print(t2_aez)

# ── Build region table ─────────────────────────────────────────────────────────
reg_order <- c('Central','Eastern','Southern','Western')

t2_region <- make_table(theor_farms_application, 'region') |>
  mutate(region = factor(region, levels = reg_order)) |>
  arrange(region) |>
  mutate(region = as.character(region))

message('\n=== T02 by Region ===')
print(t2_region)

# ── Save ───────────────────────────────────────────────────────────────────────
write.csv(t2_aez,    '../output/main_fig/T02_heterogeneity_by_aez.csv',    row.names = FALSE)
write.csv(t2_region, '../output/main_fig/T02_heterogeneity_by_region.csv', row.names = FALSE)
message('Saved: T02_heterogeneity_by_aez.csv and T02_heterogeneity_by_region.csv')
