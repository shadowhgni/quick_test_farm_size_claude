# ==============================================================================
# Script: T01_area_production_tables.R
# Project: Farm Size Prediction Across Sub-Saharan Africa
# Purpose: Generate area and production share tables
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) - February 2026
# ==============================================================================


require(tidyverse)

# Clean environment
rm(list=ls())

# Set working directory
setwd(paste0(here::here(), '/scripts'))
dir.create('../output/other_illustr/tables', recursive = TRUE, showWarnings = FALSE)
dir.create('../output/main_fig', recursive = TRUE, showWarnings = FALSE)

# ------------------------------------------------------------------------------
# Preparation for functions and mapping
input_path <- '../data/raw/spatial'
country <- geodata::world(path=input_path, resolution=5, level=0)
isocodes <- geodata::country_codes()
isocodes_ssa <- subset(isocodes, NAME=='Sudan' | UNREGION1=='Middle Africa' | UNREGION1=='Western Africa' | UNREGION1=='Southern Africa' | UNREGION1=='Eastern Africa')
isocodes_ssa <- subset(isocodes_ssa, NAME!='Cabo Verde' & NAME!='Comoros' & NAME!='Mauritius' & NAME!='Mayotte' & NAME!='Réunion' & NAME!='Saint Helena' & NAME!='São Tomé and Príncipe' & NAME!='Seychelles') # keep the mainland + Madagascar only, remove islands
ssa <- subset(country, country$GID_0 %in% isocodes_ssa$ISO3)
ssa_grid <- tryCatch(terra::rast(nrow = 2000, ncol = 2000, ext = floor(terra::ext(ssa))),
  error = function(e) { message('CI: ssa_grid failed'); terra::rast(nrow=100, ncol=100) })
ssa_rast <- tryCatch(terra::rasterize(ssa, ssa_grid, field = 'NAME_0'),
  error = function(e) { message('CI: ssa_rast failed: ', e$message); ssa_grid })
pal <- colorRampPalette(c('darkred', 'orange', 'gold', 'darkolivegreen3', 'darkgreen'))

# ------------------------------------------------------------------------------
#define the countries for which LSMS data are available
sixteen_countries <- c('Benin', 'Burkina', 'Cote_d_Ivoire', 'Ethiopia', 'Ghana', 'Guinea_Bissau', 'Malawi', 'Mali', 'Niger', 'Nigeria', 'Rwanda','Senegal', 'Tanzania', 'Togo', 'Uganda', 'Zambia')
sixteen_country_codes <- c('BEN', 'BFA', 'CIV', 'ETH', 'GHA', 'GNB', 'MWI', 'MLI', 'NER', 'NGA', 'RWA', 'SEN', 'TZA', 'TGO', 'UGA', 'ZMB')
# ------------------------------------------------------------------------------
# Prepare data: load lsms data and stacked (raster of drivers)
lsms_spatial <- readRDS('../data/processed/lsms_trimmed_95th_africa.rds') # this was retrieved from '03.1.pooled_data_for_analysis.r'
stacked <- terra::rast('../data/processed/stacked_rasters_africa.tif')

rf_model_predictions <- terra::rast('../data/processed/rf_model_predictions_SSA.tif')
names(rf_model_predictions) <- 'pred_farm_area_ha'
qrf_model_predictions <- terra::rast('../data/processed/qrf_100quantiles_predictions_africa.tif')
names(qrf_model_predictions) <- paste0('qrf_q', sprintf('%03g', 1:100))
calc_nb_farms <- terra::rast('../data/processed/nb_farms_per_grid_cell.tif')

xx <- readRDS('../data/processed/fsize_distribution_resample_long.rds')
# theor_farms <- xx$theor_farms
theor_farms_application <- ungroup(xx$theor_farms_application); rm(xx)

# Get the AEZ_5
aez5 <- terra::rast(paste0(input_path, '/AEZ_SSA_IFPRI/AEZ5_CLAS--SSA.tif'))
names(aez5) <- 'aez_class'
lookup <- data.frame(aez_class = 0:5, aez = c('humid', 'sub-humid', 'semi-arid', 'arid', 'tropical highlands', 'sub-tropical'))
levels(aez5) <- lookup

gc()
theor_farms_application <- theor_farms_application |>
  rename(individual_farm_size_ha = linear_farm_size_ha) |>
  bind_cols(tryCatch(
    terra::extract(aez5, theor_farms_application |> ungroup() |> select(x, y)),
    error = function(e) {
      message('CI: aez5 extract failed: ', e$message)
      data.frame(ID = seq_len(nrow(theor_farms_application)),
                 aez_class = NA_integer_, aez = NA_character_)
    }))
gc()

theor_app2 <- tryCatch({
  tmp_extract <- tryCatch(
    terra::extract(ssa, theor_farms_application |> ungroup() |> select(x, y)),
    error = function(e) { message('CI: ssa extract: ',e$message)
      data.frame(ID=seq_len(nrow(theor_farms_application)), GID_0=NA_character_, NAME_0=NA_character_) })
  theor_farms_application |>
    { if ('ID' %in% names(.)) dplyr::select(., -ID) else . } |>
    bind_cols(tmp_extract |> dplyr::select(-dplyr::any_of('ID'))) |>
  mutate(region = case_when(GID_0 %in% c('BEN', 'BFA', 'CIV', 'GHA', 'GIN', 'GMB', 'GNB', 'LBR', 'MLI', 'MRT', 'NER', 'NGA', 'SEN', 'SLE', 'TGO') ~ 'Western',
                            GID_0 %in% c('AGO', 'CAF', 'CMR', 'COD', 'COG', 'GNQ', 'GAB', 'TCD') ~ 'Central',
                            GID_0 %in% c('BDI', 'DJI', 'ERI', 'ETH', 'KEN', 'MDG', 'MOZ', 'MWI', 'RWA', 'SDN', 'SOM', 'SSD', 'TZA', 'UGA', 'ZMB', 'ZWE') ~ 'Eastern',
                            GID_0 %in% c('BWA', 'LSO', 'NAM', 'SWZ', 'ZAF') ~ 'Southern',
                            .default = NA)
         ) |>
  ungroup()
}, error = function(e) {
  message('CI: theor_app2 build failed: ', e$message)
  theor_farms_application
})
gc()

# predicted average farm size per grid cell
simpl_aez <- rf_model_predictions |>
  terra::as.data.frame(xy = T) |>
  bind_cols(
    terra::extract(aez5, terra::crds(rf_model_predictions)) ) |>
  filter(!is.na(pred_farm_area_ha), !is.na(aez))


#  loop over "harv_area", "prod", and "value"
all_df <- compil_df <- tibble()
for(var in c('harv_area', 'production', 'value')){
  var_code <- case_when(var == 'harv_area' ~ '_H',
                        var == 'production' ~ '_P',
                        var == 'yield' ~ '_Y',
                        var == 'value' ~ '_V')
  
  each_2017_crop <- terra::rast(paste0(input_path, '/spam/spam2017/', dir(paste0(input_path,'/spam/spam2017'))[grep(paste0(var_code, '_[A-Z]+_A.tif$'), dir(paste0(input_path,'/spam/spam2017')))]) ) # _A is total area (rainfed  + irrigated)
  each_2017_crop <- terra::crop(each_2017_crop, ssa, mask = T)
  names(each_2017_crop) <- paste0(substr(names(each_2017_crop), 20, 23), var_code)
  # Pick Sudan data from SPAM 2010, and merge with SPAM 2017
  if(var != 'value'){
    each_2010_crop <- terra::rast(paste0(input_path, '/spam/spam2010/', dir(paste0(input_path,'/spam/spam2010'))[grep(paste0(var_code, '_[A-Z]+_A.tif$'),  dir(paste0(input_path,'/spam/spam2010')))]) ) 
    names(each_2010_crop) <- paste0(substr(names(each_2010_crop), 20, 23), var_code)
    sudan_rows <- which(terra::values(ssa)[['NAME_0']] == 'Sudan'); if(!length(sudan_rows)) sudan_rows <- 1L
    sudan_mask <- terra::crop(each_2010_crop, ssa[sudan_rows,], mask=TRUE)
    each_crop <- terra::merge(each_2017_crop, sudan_mask); rm(each_2010_crop, each_2017_crop)
    names(each_crop) <- make.unique(names(each_crop))
  } else {each_crop <- each_2017_crop; rm(each_2017_crop)}
  terra::ext(each_crop) <- floor(terra::ext(each_crop))
  
  crop_rel_importance <- each_crop |> 
    terra::as.data.frame() |> 
    summarize(across(everything(), \(x) sum(x, na.rm = TRUE))) |>
    unlist() |>
    sort(decreasing = T)
  
  all_crops <- sum(each_crop, na.rm = T); names(all_crops) <- paste0('all_crops', var_code)
  maize_ssa <- tryCatch(each_crop[[paste0('MAIZ', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('MAIZ',var_code);r})
  sorgh_ssa <- tryCatch(each_crop[[paste0('SORG', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('SORG',var_code);r})
  pmil_ssa <- tryCatch(each_crop[[paste0('PMIL', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('PMIL',var_code);r})
  millet_ssa <- sum(c(each_crop[[paste0('PMIL', var_code)]], each_crop[[paste0('SMIL', var_code)]]), na.rm = T); names(millet_ssa) <- paste0('millet', var_code)
  rice_ssa <- tryCatch(each_crop[[paste0('RICE', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('RICE',var_code);r})
  whea_ssa <- tryCatch(each_crop[[paste0('WHEA', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('WHEA',var_code);r})
  barl_ssa <- tryCatch(each_crop[[paste0('BARL', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('BARL',var_code);r})
  ocer_ssa <- tryCatch(each_crop[[paste0('OCER', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('OCER',var_code);r})
  cere_ssa <- sum(c(maize_ssa, sorgh_ssa, millet_ssa, rice_ssa, whea_ssa, barl_ssa, ocer_ssa), na.rm = T); names(cere_ssa) <- paste0('cere', var_code)
  
  cassa_ssa <- tryCatch(each_crop[[paste0('CASS', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('CASS',var_code);r})
  yams_ssa <- tryCatch(each_crop[[paste0('YAMS', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('YAMS',var_code);r})
  pota_ssa <- tryCatch(each_crop[[paste0('POTA', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('POTA',var_code);r})
  swpo_ssa <- tryCatch(each_crop[[paste0('SWPO', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('SWPO',var_code);r})
  root_ssa <- sum(c(cassa_ssa, yams_ssa, pota_ssa, swpo_ssa), na.rm = T); names(root_ssa) <- paste0('root', var_code)
  
  grou_ssa <- tryCatch(each_crop[[paste0('GROU', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('GROU',var_code);r})
  beans_ssa <- tryCatch(each_crop[[paste0('BEAN', var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;names(r)<-paste0('BEAN',var_code);r})
  
  legm_bands <- c('BEAN','CHIC','COWP','PIGE','LENT','OPUL','SOYB','GROU')
  legm_layers <- lapply(legm_bands, function(b) tryCatch(each_crop[[paste0(b, var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;r}))
  legm_ssa <- Reduce(function(a,b) sum(c(a,b), na.rm=TRUE), legm_layers); names(legm_ssa) <- paste0('legumes', var_code)
  
  nf_bands <- c('SUGC','SUGB','COTT','OFIB','ACOF','RCOF','COCO','TEAS','TOBA')
  nf_layers <- lapply(nf_bands, function(b) tryCatch(each_crop[[paste0(b, var_code)]], error=function(e){r<-each_crop[[1]];terra::values(r)<-0;r}))
  non_food_ssa <- Reduce(function(a,b) sum(c(a,b), na.rm=TRUE), nf_layers); names(non_food_ssa) <- paste0('non_food', var_code)
  
  
  # prepare cattle raster
  # cattle <- stacked$cattle
  # cattle <- terra::extend(cattle, terra::ext(each_crop)) # not just terra::ext(cattle) <- terra::ext(each_crop)
  cattle <- terra::resample(stacked$cattle, each_crop)
  
  if (var == 'harv_area'){
    
    cropland_per_aez <- all_crops |>
      terra::as.data.frame(xy = T) |>
      bind_cols(
        terra::extract(aez5, terra::crds(all_crops))
      )
    
    contrib_aez <- cropland_per_aez |>
      group_by(aez) |>
      summarize(absol = sum(all_crops_H, na.rm = T)) |>
      arrange(desc(absol)) |>
      mutate(rel = absol / sum (absol),
             cumsum = cumsum(rel))
    
    ssa_extract <- tryCatch(
      terra::extract(ssa, select(simpl_aez, c(x, y))),
      error = function(e) {
        message('CI: ssa extract failed, using empty GID_0'); 
        data.frame(ID=seq_len(nrow(simpl_aez)), GID_0=NA_character_, NAME_0=NA_character_)
      })
    major_aez <- simpl_aez |>
      bind_cols(ssa_extract |> dplyr::select(-ID)) |>
      mutate(region = case_when(GID_0 %in% c('BEN', 'BFA', 'CIV', 'GHA', 'GIN', 'GMB', 'GNB', 'LBR', 'MLI', 'MRT', 'NER', 'NGA', 'SEN', 'SLE', 'TGO') ~ 'Western',
                                GID_0 %in% c('AGO', 'CAF', 'CMR', 'COD', 'COG', 'GNQ', 'GAB', 'TCD') ~ 'Central',
                                GID_0 %in% c('BDI', 'DJI', 'ERI', 'ETH', 'KEN', 'MDG', 'MOZ', 'MWI', 'RWA', 'SDN', 'SOM', 'SSD', 'TZA', 'UGA', 'ZMB', 'ZWE') ~ 'Eastern',
                                GID_0 %in% c('BWA', 'LSO', 'NAM', 'SWZ', 'ZAF') ~ 'Southern',
                                .default = NA)) |> 
      inner_join(contrib_aez |>
                   filter(rel > 0.05) |> # exclude AEZ contributing to less than 5% of total cropland
                   select(aez))
    
  } else { print(' ')}
  
  df <- c(cattle, all_crops, 
          maize_ssa, sorgh_ssa,  millet_ssa, rice_ssa, barl_ssa, whea_ssa, ocer_ssa, cere_ssa,
          cassa_ssa, yams_ssa, pota_ssa, swpo_ssa, root_ssa, 
          grou_ssa,  beans_ssa, legm_ssa, 
          non_food_ssa)
  df <- c(rf_model_predictions, terra::resample(df, rf_model_predictions))
  df <- major_aez |>
    inner_join(df |>
                 terra::as.data.frame(xy = T) |>
                 mutate(variable = var,
                        across(ends_with(var_code), ~ replace_na(., 0))) |>
                 na.omit()) |>
    rename_with(~ gsub(var_code, '', .), ends_with(var_code))
  
  all_df <- bind_rows(all_df, df)
}

all_df_absolute <- all_df |> 
  select(!c(x, y, id.y)) |>
  group_by(variable, aez, region, NAME_0, GID_0, pred_farm_area_ha) |>
  summarize(across(everything(), \(x) sum(x, na.rm = TRUE))) |>
  arrange(aez, pred_farm_area_ha)

all_df_abs_long <- all_df_absolute |>
  pivot_longer(!c(variable, aez, region, NAME_0, GID_0, pred_farm_area_ha), names_to = 'product', values_to = 'value') |>
  arrange(variable, aez, region, NAME_0, GID_0, product, pred_farm_area_ha)

all_df_rel_per_aez <- all_df_absolute |> 
  mutate(across( where(is.numeric) & !any_of('pred_farm_area_ha'), ~ cumsum(.)/sum(.)),
         across( where(is.numeric) & !any_of('pred_farm_area_ha'), ~ ifelse(is.nan(.), 0, .)) )

all_df_rel_all_aez <- all_df |> 
  select(!c(x, y, id.y)) |>
  group_by(variable, aez, region, NAME_0, GID_0, pred_farm_area_ha) |>
  summarize(across(everything(), \(x) sum(x, na.rm = TRUE))) |>
  ungroup() |>
  arrange(pred_farm_area_ha) |>
  mutate(across( where(is.numeric) & !any_of('pred_farm_area_ha'), ~ cumsum(.)/sum(.)),
         across( where(is.numeric) & !any_of('pred_farm_area_ha'), ~ ifelse(is.nan(.), 0, .)),
         aez = 'all_aez')

all_df_rel <- all_df_rel_per_aez |>
  bind_rows(all_df_rel_all_aez) |>
  mutate(aez = factor(aez, levels = c('all_aez', 'tropical highlands', 'humid', 'sub-humid', 'semi-arid'))) 

all_df_rel_long <- all_df_rel |>
  pivot_longer(!c(variable, aez, region, NAME_0, GID_0, pred_farm_area_ha), names_to = 'product', values_to = 'value') |>
  arrange(variable, aez, region, NAME_0, GID_0, product, pred_farm_area_ha) |>
  select(variable, aez, region, NAME_0, GID_0, product, pred_farm_area_ha, everything())


# summarize the share of total area/production per country, AEZ, or economic region
for(grouping_f in c('NAME_0', 'region', 'aez')){
  all_df_thresh_long <- all_df_absolute  |>
    mutate(threshold = case_when(pred_farm_area_ha < 0.5 ~ '< 0.5 ha',
                                 pred_farm_area_ha >= 0.5 & pred_farm_area_ha < 1 ~ '0.5 - 1 ha',
                                 pred_farm_area_ha >= 1 & pred_farm_area_ha < 2 ~ '1 - 2 ha',
                                 pred_farm_area_ha >= 2 ~ '> 2 ha',
                                 .default = NA),
           threshold = factor(threshold, levels = c('< 0.5 ha', '0.5 - 1 ha', '1 - 2 ha', '> 2 ha')) ) |>
    pivot_longer(!c(variable, aez, region, NAME_0, GID_0, threshold, pred_farm_area_ha ), names_to = 'product', values_to = 'value') |>
    arrange(variable, aez, region, NAME_0, GID_0, product, threshold, pred_farm_area_ha) |>
    group_by(variable, aez, region, NAME_0, GID_0, product, threshold) |>
    reframe(value = sum(value, na.rm = T))
  
  my_df <- all_df_thresh_long |>
    group_by(variable, .data[[grouping_f]], product, threshold) |>
    reframe(value = sum(value, na.rm = T)) |>
    inner_join(all_df_thresh_long |>
                 group_by(variable, .data[[grouping_f]], product) |>
                 reframe(tot = sum(value, na.rm = T))) |>
    mutate(share = value / tot)
  one_df <- my_df |>
    mutate(grouping_factor = grouping_f) |>
    rename_with(~ gsub(grouping_f, 'group_modality', .), contains(grouping_f)) |>
    select(variable, grouping_factor, group_modality, product, threshold, value, tot, share)
  
  compil_df <- bind_rows(compil_df, one_df); rm(one_df)
  print(head(my_df))
}

summary_df <- compil_df |>
  select(!c(value, tot)) |>
  mutate(share = round(100 * share, 1),
         share = if_else(is.nan(share) | is.na(share), 0, share)) |>
  pivot_wider(names_from = threshold, values_from = share) |>
  filter(!is.na(group_modality)) |>
  arrange(variable,  product, grouping_factor, group_modality) |>
  select(variable,  product, grouping_factor, group_modality, `< 0.5 ha`, everything())

saveRDS(list(all_df_abs_long = all_df_abs_long, compil_df = compil_df, summary_df = summary_df,
             country_all_crops = summary_df |> filter(grouping_factor == 'NAME_0', product == 'all_crops'),
             region_all_crops = summary_df |> filter(grouping_factor == 'region', product == 'all_crops'),
             aez_all_crops = summary_df |> filter(grouping_factor == 'aez', product == 'all_crops')),
        file = '../output/other_illustr/tables/croplands_per_grouping_factor.rds')
write.csv(summary_df |> filter(grouping_factor == 'NAME_0', product == 'all_crops'), '../output/other_illustr/tables/croplands_per_country.csv', row.names = F)
write.csv(summary_df |> filter(grouping_factor == 'region', product == 'all_crops'), '../output/other_illustr/tables/croplands_per_region.csv', row.names = F)
write.csv(summary_df |> filter(grouping_factor == 'aez', product == 'all_crops'), '../output/other_illustr/tables/croplands_per_aez.csv', row.names = F)

# using quantile-based predictions (for harvested area only)
compil_df <- tibble()
for(grouping_f in c('NAME_0', 'region', 'aez')){
  theor_app_thresh_long <- theor_app2  |>
    mutate(threshold = case_when(individual_farm_size_ha < 0.5 ~ '< 0.5 ha',
                                 individual_farm_size_ha >= 0.5 & individual_farm_size_ha < 1 ~ '0.5 - 1 ha',
                                 individual_farm_size_ha >= 1 & individual_farm_size_ha < 2 ~ '1 - 2 ha',
                                 individual_farm_size_ha >= 2 ~ '> 2 ha',
                                 .default = NA),
           threshold = factor(threshold, levels = c('< 0.5 ha', '0.5 - 1 ha', '1 - 2 ha', '> 2 ha')) ) |>
    arrange(aez, region, NAME_0, GID_0, threshold) |>
    group_by(aez, region, NAME_0, GID_0, threshold) |>
    reframe(value = sum(individual_farm_size_ha, na.rm = T))
  
  my_df <- theor_app_thresh_long |>
    group_by(.data[[grouping_f]], threshold) |>
    reframe(value = sum(value, na.rm = T)) |>
    inner_join(theor_app_thresh_long |>
                 group_by(.data[[grouping_f]]) |>
                 reframe(tot = sum(value, na.rm = T))) |>
    mutate(share = value / tot)
  
  one_df <- my_df |>
    mutate(grouping_factor = grouping_f) |>
    rename_with(~ gsub(grouping_f, 'group_modality', .), contains(grouping_f)) |>
    select(grouping_factor, group_modality, threshold, value, tot, share)
  
  compil_df <- bind_rows(compil_df, one_df); rm(one_df)
  print(head(my_df))
}

tidy_compil_df <- compil_df |>
  select(!c(value, tot)) |>
  mutate(share = round(100 * share, 1),
         share = if_else(is.nan(share) | is.na(share), 0, share)) |>
  pivot_wider(names_from = threshold, values_from = share) |>
  filter(!is.na(group_modality)) |>
  arrange(grouping_factor, group_modality) |>
  select(grouping_factor, group_modality, `< 0.5 ha`, everything())

write.csv(tidy_compil_df |> filter(grouping_factor == 'NAME_0'), '../output/other_illustr/tables/theor_croplands_per_country.csv', row.names = F)
write.csv(tidy_compil_df |> filter(grouping_factor == 'region'), '../output/other_illustr/tables/theor_croplands_per_region.csv', row.names = F)
write.csv(tidy_compil_df |> filter(grouping_factor == 'aez'), '../output/other_illustr/tables/theor_croplands_per_aez.csv', row.names = F)
