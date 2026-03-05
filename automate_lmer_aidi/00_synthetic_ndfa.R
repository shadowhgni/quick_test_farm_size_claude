# =============================================================================
# Synthetic data generator — CI testing of select_ndfa_model.R
#
# Produces a fake version of:
#   2026-03-02.intermediate_soybean_df.rds
# saved to the directory given by NDFA_DATA_DIR (default: ../data/processed).
#
# Data properties mirror the real Malawi soybean BNF dataset:
#   • n = 90  (complete cases after na.omit in select_ndfa_model.R)
#   • final_ndfa_grass strictly in (0.05, 0.95) — Beta-distributed
#   • Nested spatial hierarchy: 2 provinces > 4 districts > 8 wards > 16 villages
#   • All predictor columns present with realistic ranges and correlations
#
# This script is called by the CI workflow before select_ndfa_model.R.
# =============================================================================

set.seed(42)
n <- 90

# -- Spatial hierarchy -------------------------------------------------------
provinces <- paste0("prov_", 1:2)
districts <- paste0("dist_", 1:4)
wards     <- paste0("ward_", 1:8)
villages  <- paste0("vill_", 1:16)

province <- sample(provinces, n, replace = TRUE)
district <- paste0(province, "_", sample(1:2, n, replace = TRUE))
ward     <- paste0(district, "_", sample(1:2, n, replace = TRUE))
village  <- paste0(ward,     "_", sample(1:2, n, replace = TRUE))

# -- Continuous predictors ---------------------------------------------------
aridity_index       <- runif(n, 0.3, 1.8)   # higher = wetter
chirps_cum_rain_mm  <- aridity_index * 400 + rnorm(n, 0, 80)  # correlated
agera5_avg_tmin     <- rnorm(n, 14, 3)
agera5_cum_srad_mj  <- rnorm(n, 1500, 200)
agera5_cum_rh09     <- runif(n, 40, 90)

soil_phos           <- exp(rnorm(n, 2.5, 0.6))   # right-skewed, mg/kg
soil_ECEC           <- runif(n, 2, 18)
soil_pH             <- rnorm(n, 6.0, 0.6)
sand_content_perc   <- runif(n, 15, 70)
C_Soil              <- runif(n, 0.5, 3.0)
N_Soil              <- C_Soil / runif(n, 8, 14)   # C:N ratio 8–14

plant_density_per_ha <- rnorm(n, 280000, 60000) |> pmax(80000)
planting_date        <- sample(310:360, n, replace = TRUE)  # day of year
crop_duration        <- sample(90:130, n, replace = TRUE)   # days
main_soya_field_ha   <- exp(rnorm(n, 0.1, 0.7)) |> pmax(0.05)
leg_importance_perc  <- runif(n, 5, 80)

# -- Factor predictors -------------------------------------------------------
inoculant_use   <- factor(sample(c("No", "Yes"), n, replace = TRUE,
                                 prob = c(0.55, 0.45)),
                           levels = c("No", "Yes"))
seed_type       <- factor(sample(c("improved", "local", "certified"), n,
                                 replace = TRUE, prob = c(0.5, 0.35, 0.15)))
farmer_gender   <- factor(sample(c("male", "female"), n, replace = TRUE,
                                 prob = c(0.62, 0.38)))
fertilizer_use  <- factor(sample(c("No", "Yes"), n, replace = TRUE))
weeding_mode    <- factor(sample(c("hand", "herbicide", "both"), n,
                                 replace = TRUE, prob = c(0.6, 0.25, 0.15)))
previous_crop_2 <- factor(sample(c("maize", "groundnut", "other"), n,
                                 replace = TRUE, prob = c(0.5, 0.3, 0.2)))

# -- Response: final_ndfa_grass ----------------------------------------------
# Generate on logit scale so Beta bounds are naturally respected.
# Main drivers: inoculant (+), aridity (-), plant density (+), soil_phos (+).
logit_mu <- -0.5 +
  0.6  * (inoculant_use == "Yes") +
  -0.4 * scale(aridity_index)[, 1] +
  0.3  * scale(plant_density_per_ha)[, 1] +
  0.2  * scale(soil_phos)[, 1] +
  0.1  * scale(N_Soil)[, 1] +
  # Spatial random effects
  rnorm(n, 0, 0.3) +   # village-level noise
  rnorm(n, 0, 0.15)    # residual

# Convert to (0,1) via logistic, then clip to (0.05, 0.95) for Beta stability
prob_mu <- plogis(logit_mu)
final_ndfa_grass <- pmax(pmin(prob_mu + rnorm(n, 0, 0.06), 0.95), 0.05)

# -- Assemble and save -------------------------------------------------------
dat00 <- data.frame(
  country              = "malawi",
  final_ndfa_grass,
  farmer_gender,
  main_soya_field_ha,
  leg_importance_perc,
  province, district, ward, village,
  C_Soil, N_Soil, soil_pH, soil_ECEC, sand_content_perc, soil_phos,
  chirps_cum_rain_mm, aridity_index, agera5_avg_tmin,
  agera5_cum_srad_mj, agera5_cum_rh09,
  planting_date, crop_duration, plant_density_per_ha,
  seed_type, inoculant_use, fertilizer_use, weeding_mode,
  previous_crop_2,
  # Extra columns present in the real data (selected-out by select_ndfa_model.R)
  C_N_Soil             = C_Soil / N_Soil,
  N_Soybean            = rnorm(n, 4.5, 0.6),
  soil_OC              = C_Soil * 1.72,
  agera5_avg_tmax      = agera5_avg_tmin + runif(n, 8, 14),
  soya_dm_biom_kg_ha   = exp(rnorm(n, 7.5, 0.5)),
  land_prep_implement  = factor(sample(c("oxen", "hand", "tractor"), n,
                                       replace = TRUE, prob = c(0.5, 0.35, 0.15))),
  planting_method      = factor(sample(c("manual", "machine"), n,
                                       replace = TRUE, prob = c(0.85, 0.15))),
  weed_mgt             = factor(sample(c("none", "partial", "full"), n,
                                       replace = TRUE))
)

out_dir <- Sys.getenv("NDFA_DATA_DIR",
                      unset = file.path("..", "data", "processed"))
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

out_file <- file.path(out_dir, "2026-03-02.intermediate_soybean_df.rds")
saveRDS(dat00, out_file)

cat("Synthetic dataset saved:\n  ", out_file, "\n")
cat("  n =", nrow(dat00), " | final_ndfa_grass range: [",
    round(min(dat00$final_ndfa_grass), 3), ",",
    round(max(dat00$final_ndfa_grass), 3), "]\n")
cat("  Malawi rows:", sum(dat00$country == "malawi"), "\n")
