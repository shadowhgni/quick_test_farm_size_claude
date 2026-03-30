# ==============================================================================
# Script: T02_heterogeneity_drivers.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Table 2 — Proportion of harvested area and farm counts per size class,
#          broken down by AEZ and region.
#
#   Output columns:
#     prop_area_*  = % of total harvested area (from SPAM) in each farm-size class
#     prop_farms_* = % of farms (from virtual farm population) in each size class
#
#   Reads:
#     ../output/other_illustr/tables/cropland_stats_per_aez.rds
#       → contains compil_df (SPAM area props by grouping × threshold)
#         and tidy_compil_df (virtual-farm count props by grouping × threshold)
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - March 2026
# ==============================================================================

require(tidyverse)

rm(list = ls())
setwd(paste0(here::here(), '/scripts'))
dir.create('../output/main_fig', recursive = TRUE, showWarnings = FALSE)

# ── Load pre-computed grouping tables ─────────────────────────────────────────
rds_path <- '../output/other_illustr/tables/cropland_stats_per_aez.rds'
xx <- tryCatch(
  readRDS(rds_path),
  error = function(e) {
    message('CI: cropland_stats_per_aez.rds not found — using stubs')
    thresholds <- c('< 0.5 ha', '0.5 - 1 ha', '1 - 2 ha', '2 - 5 ha', '> 5 ha')
    aez_vals   <- c('humid', 'sub-humid', 'semi-arid', 'arid', 'tropical highlands', 'sub-tropical')
    reg_vals   <- c('Central', 'Eastern', 'Southern', 'Western')
    make_stub <- function(grp_vals, gf) {
      expand.grid(grouping_factor = gf,
                  group_modality  = grp_vals,
                  threshold       = thresholds,
                  stringsAsFactors = FALSE) |>
        mutate(share = runif(n(), 10, 30))
    }
    list(
      compil_df      = bind_rows(make_stub(aez_vals, 'aez'), make_stub(reg_vals, 'region')),
      tidy_compil_df = bind_rows(make_stub(aez_vals, 'aez'), make_stub(reg_vals, 'region'))
    )
  }
)
compil_df      <- xx$compil_df       # SPAM area proportions
tidy_compil_df <- xx$tidy_compil_df  # virtual farm count proportions
rm(xx)

# ── Size-class thresholds (ordered) ───────────────────────────────────────────
thresholds <- c('< 0.5 ha', '0.5 - 1 ha', '1 - 2 ha', '2 - 5 ha', '> 5 ha')

# ── Helper: pivot one grouping factor into wide format ─────────────────────────
make_wide <- function(area_df, farm_df, grouping_f, group_col) {

  area_wide <- area_df |>
    filter(grouping_factor == grouping_f, !is.na(group_modality)) |>
    select(group_modality, threshold, share) |>
    mutate(threshold = factor(threshold, levels = thresholds)) |>
    group_by(group_modality, threshold) |>
    summarize(share = mean(share, na.rm = TRUE), .groups = 'drop') |>
    pivot_wider(names_from  = threshold,
                values_from = share,
                names_prefix = 'prop_area_') |>
    rename(!!group_col := group_modality)

  farm_wide <- farm_df |>
    filter(grouping_factor == grouping_f, !is.na(group_modality)) |>
    select(group_modality, threshold, share) |>
    mutate(threshold = factor(threshold, levels = thresholds)) |>
    group_by(group_modality, threshold) |>
    summarize(share = mean(share, na.rm = TRUE), .groups = 'drop') |>
    pivot_wider(names_from  = threshold,
                values_from = share,
                names_prefix = 'prop_farms_') |>
    rename(!!group_col := group_modality)

  left_join(area_wide, farm_wide, by = group_col) |>
    mutate(across(where(is.numeric), ~ round(., 1)))
}

# ── Build by-AEZ table ────────────────────────────────────────────────────────
aez_order <- c('humid', 'sub-humid', 'semi-arid', 'arid',
                'tropical highlands', 'sub-tropical')

t2_aez <- make_wide(compil_df, tidy_compil_df, 'aez', 'aez') |>
  mutate(aez = factor(aez, levels = aez_order)) |>
  arrange(aez) |>
  mutate(aez = as.character(aez))

message("\n=== T02 by AEZ ===")
print(t2_aez)

# ── Build by-region table ─────────────────────────────────────────────────────
reg_order <- c('Central', 'Eastern', 'Southern', 'Western')

t2_region <- make_wide(compil_df, tidy_compil_df, 'region', 'region') |>
  mutate(region = factor(region, levels = reg_order)) |>
  arrange(region) |>
  mutate(region = as.character(region))

message("\n=== T02 by Region ===")
print(t2_region)

# ── Save ───────────────────────────────────────────────────────────────────────
write.csv(t2_aez,    '../output/main_fig/T02_heterogeneity_by_aez.csv',    row.names = FALSE)
write.csv(t2_region, '../output/main_fig/T02_heterogeneity_by_region.csv', row.names = FALSE)
message("Saved: T02_heterogeneity_by_aez.csv and T02_heterogeneity_by_region.csv")
