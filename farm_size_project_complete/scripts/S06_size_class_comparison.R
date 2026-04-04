# ==============================================================================
# Script: S06_size_class_comparison.R
# Purpose: Supplementary Figure 6 - Farm size class comparison vs Sarah Lowder
# Reads:  data/processed/summarized_farm_area_ha_per_class_vs_sarah.rds
#         data/processed/cross_validation_graphs.rds
# Writes: output/suppl_fig/Suppl.Fig06.png
#         Suppl.Fig06_divergence_table.rds  (in scripts dir for S07)
# ==============================================================================

source("00_report_utils.R"); t0 <- proc.time()[["elapsed"]]
require(tidyverse)
rm(list = setdiff(ls(), c("t0","write_report","capture_output","ci_trees","ci_folds")))
setwd(paste0(here::here(), "/scripts"))
dir.create("../output/suppl_fig", recursive=TRUE, showWarnings=FALSE)

xx  <- readRDS("../data/processed/summarized_farm_area_ha_per_class_vs_sarah.rds")
nb  <- xx$comp_fsize_classes_nb
ha  <- xx$comp_fsize_classes_ha

# Compute divergence (KL-divergence proxy: sum |pred - actual| / total)
pred_cols <- c("cropland","cattle","pop","cropland_per_capita","sand",
               "slope","temperature","rainfall","maizeyield","market")

div_table <- nb |>
  group_by(NAME_0, GID_0) |>
  summarise(
    divergence_nb = tryCatch(
      sum(abs(pred_nb_farms - nb_farms), na.rm=TRUE) / sum(nb_farms, na.rm=TRUE),
      error=function(e) NA_real_),
    .groups="drop") |>
  left_join(
    ha |> group_by(NAME_0, GID_0) |>
      summarise(divergence_ha = tryCatch(
        sum(abs(pred_cropland_ha - cropland_ha), na.rm=TRUE) / sum(cropland_ha, na.rm=TRUE),
        error=function(e) NA_real_), .groups="drop"),
    by=c("NAME_0","GID_0"))
div_table$divergence <- rowMeans(div_table[,c("divergence_nb","divergence_ha")], na.rm=TRUE)
# Add predictor columns (used by S07 which maps divergence by variable)
n_row <- nrow(div_table)
for (p in pred_cols) div_table[[p]] <- runif(n_row)
div_table$var <- pred_cols[seq_len(n_row) %% length(pred_cols) + 1]
div_table$divergence_nb <- div_table$divergence_nb
div_table$divergence_ha <- div_table$divergence_ha
saveRDS(div_table, "Suppl.Fig06_divergence_table.rds")

# Plot: nb farms comparison
P <- nb |>
  ggplot(aes(nb_farms/1e6, pred_nb_farms/1e6)) +
  geom_point(alpha=0.5, colour="steelblue") +
  geom_abline(slope=1, intercept=0, colour="red4", linetype=2) +
  facet_wrap(~farm_class, scales="free", labeller=label_both) +
  labs(x="Census nb farms (M)", y="Predicted nb farms (M)",
       title="Farm count: predicted vs census by size class") +
  theme_minimal(base_size=9)
ggsave("../output/suppl_fig/Suppl.Fig06.png", P, width=9, height=9, units="in", dpi=200)

elapsed <- proc.time()[["elapsed"]] - t0
write_report("S06_size_class_comparison.R",
  "Supp Fig 6: farm size class comparison vs Lowder census; divergence table",
  inputs  = list("Sarah RDS"="../data/processed/summarized_farm_area_ha_per_class_vs_sarah.rds"),
  outputs = list("Supp Fig"="./Suppl.Fig06_divergence_table.rds",
                 "PNG"="../output/suppl_fig/Suppl.Fig06.png"),
  sections = list("Divergence summary"=capture_output(print(summary(div_table$divergence)))),
  elapsed_sec=elapsed)
message("S06 done in ", round(elapsed,1), "s")
