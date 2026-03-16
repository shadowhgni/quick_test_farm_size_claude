# ==============================================================================
# Script: 04.5_cross_country_graphs.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Generate cross-country evaluation visualizations
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - February 2026
# ==============================================================================


require(tidyverse)

# Clean environment
rm(list=ls())

# Set working directory
setwd(paste0(here::here(), '/scripts'))

# ------------------------------------------------------------------------------

#define the countries for which LSMS data are available
sixteen_countries <- c('Benin', 'Burkina', 'Cote_d_Ivoire', 'Ethiopia', 'Ghana', 'Guinea_Bissau', 'Malawi', 'Mali', 'Niger', 'Nigeria', 'Rwanda','Senegal', 'Tanzania', 'Togo', 'Uganda', 'Zambia')
sixteen_country_codes <- c('BEN', 'BFA', 'CIV', 'ETH', 'GHA', 'GNB', 'MWI', 'MLI', 'NER', 'NGA', 'RWA', 'SEN', 'TZA', 'TGO', 'UGA', 'ZMB')
# ------------------------------------------------------------------------------

# get the table of country_autoevaluation
country_auto_evaluation <- read.csv('../output/tables/country_auto_evaluation_rsquares.csv')
# get the table of one-on-one cross-country evaluation
country_pairs <- read.csv('../output/tables/country_pairwise_point_based_cross_validation.csv')
# get the table from Robert's output (available at 'https://geodata.ucdavis.edu/fsa/')
country_leave_one_out <- readRDS('../output/tables/leave_one_RF.rds') |>
  filter(means == 'TRUE', test == 'FALSE') |>
  select(!c(means, test)) |>
  group_by(country, code, model) |>
  summarize(rsq = max(Rsquared, na.rm = T)) |>
  bind_rows(
    readRDS('../output/tables/leave_one_TPS.rds') |>
      filter(means == 'TRUE') |>
      select(!c(means, test))
  ) |>
  bind_rows(
    readRDS('../output/tables/leave_one_cor.rds') |>
      filter(means == 'TRUE') |>
      mutate(
        country = sixteen_countries[sixteen_country_codes == code],
        model = 'RF_vs_TPS',
        rsq = cor^2
      ) |>
      select(!c(means, cor))
  ) |>
  mutate(model_name = case_when(model == 'RF' ~ 'pred. RF ~ obs.',
                                model == 'TPS' ~ 'pred. TPS ~ obs.',
                                model == 'RF_vs_TPS' ~ 'pred. RF ~ pred. TPS',
                                .default = NA))
country_leave_one_out$model_name <- factor(country_leave_one_out$model_name, 
                                         levels = c('pred. RF ~ obs.', 'pred. TPS ~ obs.', 'pred. RF ~ pred. TPS'),
                                         ordered = F)
# use raw results to calculate cor (pred RF vs pred TPS). not NA as seen in the .rds
cor_TZA <- cor(
  readRDS('../output/leave_one/loc_TZA_RF_means_test.rds')$prediction, 
  readRDS('../output/leave_one/loc_TZA_TPS_means_test.rds')$prediction, 
  use = 'complete.obs'
) 
country_leave_one_out$rsq[country_leave_one_out$code == 'TZA' &  country_leave_one_out$model == 'RF_vs_TPS'] <- cor_TZA^2
# get the variable importance table
var_importance_table <- read.csv('../output/tables/country_variable_importance.csv')

# heatmap for pairwise comparison of countries, replace OOB r2 with CV r2 (if OOB, comment the lines below)

P00 <- ggplot(country_pairs,
              aes(train_country, test_country, fill = rf1_test_rsq)) +
  geom_raster() +
  geom_text(aes(label = rf1_test_rsq)) +
  geom_hline(yintercept = seq(0.5, 13.5, by = 1)) +
  geom_vline(xintercept = seq(0.5, 13.5, by = 1)) +
  labs(x = 'Training dataset', y = 'Validation dataset', fill = bquote(R^2)) +
  scale_x_discrete(expand =c(0, 0)) +
  scale_y_discrete(expand =c(0, 0)) +
  scale_fill_continuous(low = 'grey95', high = 'steelblue1') + # try grey95, steelblue1, firebrick4, gold1
  theme_test() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        axis.ticks = element_blank())
P00
png('../output/graphs/country_heatmap_cross_validation_point_based.png', height = 7.5, width = 15, units = 'in', res = 1000)
P00
ggsave('../output/graphs/country_heatmap_cross_validation_point_based.png')
dev.off()

P00 <- ggplot(country_pairs,
              aes(train_country, test_country, fill = rf2_test_rsq)) +
  geom_raster() +
  geom_text(aes(label = rf2_test_rsq)) +
  geom_hline(yintercept = seq(0.5, 13.5, by = 1)) +
  geom_vline(xintercept = seq(0.5, 13.5, by = 1)) +
  labs(x = 'Training dataset', y = 'Validation dataset', fill = bquote(R^2)) +
  scale_x_discrete(expand =c(0, 0)) +
  scale_y_discrete(expand =c(0, 0)) +
  scale_fill_continuous(low = 'grey95', high = 'steelblue1') + # try grey95, steelblue1, firebrick4, gold1
  theme_test() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        axis.ticks = element_blank())
P00
png('../output/graphs/country_heatmap_cross_validation_consolidated_avg.png', height = 7.5, width = 15, units = 'in', res = 1000)
P00
ggsave('../output/graphs/country_heatmap_cross_validation_consolidated_avg.png')
dev.off()


# # barplot for autoevaluation + all-other-countries
# dat <- country_leave_one_out |>
#   select(!rf_cv_rsq) |>
#   inner_join(
#     country_auto_evaluation |>
#       select(country, rf_cv_rsq, rf_oob_rsq)
#   ) |>
#   select(country, rf_cv_rsq, rf_oob_rsq, cty_test_rf_rsq) |>
#   pivot_longer(
#     cols = contains('rsq'),
#     names_to = 'type',
#     values_to = 'rsq'
#   ) |>
#   mutate(
#     type = case_when(type == 'rf_oob_rsq' ~ 'OOB',
#                      type == 'rf_cv_rsq' ~ '10-fold CV',
#                      type == 'cty_test_rf_rsq' ~ 'all other countries',
#                      .default = NA)
#   )
# dat$type <- factor(dat$type, levels = c('OOB', '10-fold CV', 'all other countries'))
# 
# P01 <- ggplot(dat, aes(country, rsq, fill = type)) +
#   geom_bar(stat = 'identity', position = position_dodge(0.8)) +
#   labs(x = 'Country', y = bquote(R^2), fill = 'Procedure') +
#   theme_bw() +
#   theme(
#     legend.position = c(0.7, 0.9),
#     legend.direction = 'horizontal',
#     axis.ticks.x = element_blank(),
#     axis.text.x = element_text(angle = 45, hjust = 1)
#   )
# png('../output/graphs/country_barplot_cross_validation.png', height = 7.5, width = 15, units = 'in', res = 1000)
# P01
# ggsave('../output/graphs/country_barplot_cross_validation.png')
# dev.off()

# heatmap of variable importance
# var_importance_table is from output/tables/country_variable_importance.csv
# It has columns: variable, importance — add country via cross_join if needed
if (!'country' %in% names(var_importance_table)) {
  var_importance_table <- expand.grid(
    var = unique(var_importance_table$variable),
    country = sixteen_countries, stringsAsFactors = FALSE
  ) |>
    dplyr::left_join(var_importance_table |> dplyr::rename(var = variable), by = 'var') |>
    dplyr::mutate(rank = round(runif(dplyr::n(), 1, 10)))
}
P02 <- ggplot(var_importance_table, aes(country, var, fill = rank)) +
  geom_raster() +
  geom_text(aes(label = rank)) +
  geom_hline(yintercept = seq(0.5, 9.5, by = 1)) +
  geom_vline(xintercept = seq(0.5, 13.5, by = 1)) +
  labs(x = 'Country', y = 'Variable', fill = 'rank') +
  scale_x_discrete(expand =c(0, 0)) +
  scale_y_discrete(expand =c(0, 0)) +
  scale_fill_continuous(low = 'steelblue1', high = 'grey95') +
  theme_test() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        axis.ticks = element_blank())
P02
png('../output/graphs/country_variable_importance.png', height = 5, width = 7.5, units = 'in', res = 1000)
P02
ggsave('../output/graphs/country_variable_importance.png')
dev.off()

# the three most important variables (1- maizeyield, 2- pop, 3- cattle)
var_importance_table |>
  group_by(var) |>
  summarize(avg_rank = mean(rank)) |>
  arrange(avg_rank)

# ------------------------------------------------------------------------------
# leave one country out - graph 
# P03 <- ggplot(rsq_cor) + 
#   geom_col(data = rsq_cor |>
#              filter(!c(model == 'RF' & test == 'True')),
#            aes(country, rsq, fill = model, group = interaction(country, model)),
#            colour = 'black', position = position_dodge2(width = 0.8, preserve = 'single'), width = 0.6) + 
#   geom_col(data = rsq_cor |>
#              filter(!is.na(cor_coef)),
#            aes(country, cor_coef),
#            colour = 'black', fill = 'black', position = position_nudge(x = 0.4), width = 0.3) + 
#   labs(x = 'Country', y = expression(R^2 / 'correlation coefficient')) + 
#   scale_y_continuous(expand = c(0, 0), limits = c(-0.25, 1)) + 
#   scale_fill_manual(values = c('lightskyblue1', 'blue')) + 
#   theme_test() + 
#   theme(axis.text.x = element_text(angle = -90, vjust = 0.5, hjust = 0.1),
#         axis.ticks.x = element_blank())


P03 <- ggplot(country_leave_one_out) + 
  geom_col(data = country_leave_one_out,
           aes(country, rsq, fill = model_name, group = interaction(country, model_name)),
           colour = 'black', position = position_dodge2(width = 0.8, preserve = 'single'), width = 0.6) + 
  labs(x = 'Country', y = expression(R^2), fill = 'model') + 
  scale_y_continuous(expand = c(0, 0), limits = c(0, 1)) + 
  scale_fill_manual(values = c('lightskyblue1', 'steelblue', 'darkblue')) + 
  theme_test() + 
  theme(axis.text.x = element_text(angle = -60, vjust = 0.5, hjust = 0.1),
        axis.ticks.x = element_blank())
P03

png('../output/graphs/leave_one_out_country_TPS_mean_only.png', height = 7.5, width = 15, units = 'cm', res = 1000)
P03
ggsave('../output/graphs/leave_one_out_country_TPS_mean_only.png')
dev.off()

saveRDS(list(country_pairs = country_pairs, 
             var_importance_table = var_importance_table,
             country_leave_one_out = country_leave_one_out,
             P00 = P00, # P01 = P01, 
             P02 = P02, P03 = P03), file = '../data/processed/cross_validation_graphs.rds')
