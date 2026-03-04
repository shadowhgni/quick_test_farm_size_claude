# =============================================================================
# Analyse final_ndfa_grass using linear mixed-effects models
#
# Response:    final_ndfa_grass — N derived from atmosphere (NDFA) ratio,
#              estimated by 15N natural abundance (grass reference plant).
#              Malawi 2024, n = 98 on-farm observations.
#
# Random effects: (1 | province / district / ward / village)
#
# Performance metrics
#   R2m    — marginal R² (fixed effects only, Nakagawa & Schielzeth 2013)
#   R2c    — conditional R² (fixed + random effects)
#   R2_LOO — leave-one-out R² on original scale (fixed-effects prediction)
#   RMSE   — root mean squared error (original scale)
#
# Collinearity notes (|r| > 0.50 pairs excluded from same model):
#   Climate cluster: elevation / agera5_cum_rh09 / crop_duration /
#                    chirps_cum_rain_mm / aridity_index / agera5_avg_tmin
#     → representative chosen per AIC sweep: aridity_index
#   Soil texture:  soil_ECEC vs sand_content_perc (r = -0.79) -> use soil_ECEC
#   Soil organic:  C_Soil vs N_Soil (r = +0.94)               -> use N_Soil
#   soil_phos is correlated with aridity_index (r = -0.43)
#     -> kept; VIF reported to confirm tolerance
#
# =============================================================================

suppressPackageStartupMessages({
  library(lme4)      # lmer()
  library(lmerTest)  # Satterthwaite F-tests via anova()
  library(dplyr)     # data manipulation with |>
  library(car)       # vif()
})


# -- 0. Load & prepare --------------------------------------------------------

df <- readRDS("claude_github.rds") |>
  mutate(
    # Scale continuous predictors (mean = 0, sd = 1).
    # Scaling improves convergence and makes beta coefficients comparable.
    pd_s   = scale(plant_density_per_ha)[, 1],  # plants ha-1 (8 NAs)
    phos_s = scale(soil_phos)[, 1],             # available P (Bray)
    ecec_s = scale(soil_ECEC)[, 1],             # effective CEC
    nsoi_s = scale(N_Soil)[, 1],               # soil total N (g kg-1)
    arid_s = scale(aridity_index)[, 1],         # aridity (higher = wetter)
    ph_s   = scale(soil_pH)[, 1],
    sand_s = scale(sand_content_perc)[, 1],
    elev_s = scale(elevation)[, 1],
    rain_s = scale(chirps_cum_rain_mm)[, 1],
    rh09_s = scale(agera5_cum_rh09)[, 1],
    tmin_s = scale(agera5_avg_tmin)[, 1],
    dur_s  = scale(crop_duration)[, 1],

    # Relevel factors so reference category is biologically sensible
    inoculant_use = factor(inoculant_use, levels = c("No",   "Yes")),
    seed_type     = factor(seed_type),
    weed_mgt      = factor(weed_mgt, levels = c("poor", "moderate", "good")),
    farmer_gender = factor(farmer_gender)
  )

# Complete-case dataset (excludes 8 NAs in plant_density_per_ha)
df_pd <- df |> filter(!is.na(pd_s))
cat("Full dataset n =", nrow(df),
    "| Complete cases (with plant_density) n =", nrow(df_pd), "\n\n")


# -- 1. Helper functions ------------------------------------------------------

#' Nakagawa & Schielzeth (2013) R2 without MuMIn
r2_lmer <- function(model) {
  var_fixed  <- var(predict(model, re.form = NA))
  vc         <- as.data.frame(VarCorr(model))
  var_random <- sum(vc$vcov[vc$grp != "Residual"])
  var_resid  <- sigma(model)^2
  total      <- var_fixed + var_random + var_resid
  c(R2m = var_fixed / total,
    R2c = (var_fixed + var_random) / total)
}

#' Leave-one-out R2 (fixed-effects prediction only)
r2_loo <- function(model, data) {
  n     <- nrow(data)
  y     <- data$final_ndfa_grass
  y_hat <- numeric(n)
  frm   <- formula(model)

  for (i in seq_len(n)) {
    m_i <- suppressWarnings(suppressMessages(
      tryCatch(
        lmer(frm, data = data[-i, ], REML = FALSE),
        error = function(e) NULL
      )
    ))
    y_hat[i] <- if (is.null(m_i)) {
      mean(data$final_ndfa_grass[-i], na.rm = TRUE)
    } else {
      predict(m_i, newdata = data[i, ], re.form = NA,
              allow.new.levels = TRUE)
    }
  }
  ss_res <- sum((y - y_hat)^2)
  ss_tot <- sum((y - mean(y))^2)
  1 - ss_res / ss_tot
}

#' Print full model summary with R2, RMSE, LOO, VIF, and ANOVA table
summarise_model <- function(label, model, data, show_vif = TRUE) {
  r2   <- r2_lmer(model)
  rloo <- r2_loo(model, data)
  rmse <- sqrt(mean(residuals(model)^2))

  cat("\n", strrep("-", 72), "\n", sep = "")
  cat("Model:", label, "\n")
  cat("n =", nrow(data), "\n")
  cat("Formula:", deparse(formula(model)), "\n\n")

  if (isSingular(model))
    cat("  [!] Singular fit - one or more RE variances collapsed to 0\n\n")

  cat(sprintf("  R2m  (marginal)       : %.3f\n", r2["R2m"]))
  cat(sprintf("  R2c  (conditional)    : %.3f\n", r2["R2c"]))
  cat(sprintf("  R2_LOO               : %.3f\n",  rloo))
  cat(sprintf("  RMSE (in-sample)     : %.4f\n",  rmse))
  cat(sprintf("  AIC                  : %.1f\n",  AIC(model)))
  cat(sprintf("  Sigma                : %.4f\n\n", sigma(model)))

  # Satterthwaite F-tests (requires lmerTest model)
  if (inherits(model, "lmerModLmerTest")) {
    cat("ANOVA (Type III, Satterthwaite):\n")
    print(anova(model), digits = 4)
  }

  # Fixed-effect estimates
  cat("\nFixed effects:\n")
  ct <- as.data.frame(coef(summary(model)))
  ct$term <- rownames(ct)
  ct <- ct[, c("term", "Estimate", "Std. Error", "t value")]
  print(ct, digits = 3, row.names = FALSE)

  # VIF (only for models with >= 2 fixed predictors)
  if (show_vif) {
    fef <- length(fixef(model)) - 1L
    if (fef >= 2) {
      cat("\nVIF (> 5 = concern, > 10 = problem):\n")
      tryCatch(print(round(vif(model), 2)),
               error = function(e) cat("  VIF not computable\n"))
    }
  }

  # Random-effect variances
  cat("\nRandom effects:\n")
  print(as.data.frame(VarCorr(model))[, c("grp", "vcov", "sdcor")],
        digits = 4)
}


# -- 2. Fit models ------------------------------------------------------------

# M_user1: replicate user's first model
# (chirps rain, tmin, aridity, sand, pH, seed x inoc, gender)
m_user1 <- lmerTest::lmer(
  final_ndfa_grass ~
    rain_s + tmin_s + arid_s +
    sand_s + ph_s +
    seed_type * inoculant_use + farmer_gender +
    (1 | province / district / ward / village),
  data = df, REML = FALSE
)

# M_user2: replicate user's second model
# (elevation quadratic, chirps quadratic, soil block, plant_density quadratic,
#  seed x inoc, gender)
m_user2 <- lmerTest::lmer(
  final_ndfa_grass ~
    elev_s + I(elev_s^2) +
    rain_s + I(rain_s^2) +
    phos_s + ecec_s + ph_s +
    pd_s   + I(pd_s^2) +
    seed_type * inoculant_use + farmer_gender +
    (1 | province / district / ward / village),
  data = df_pd, REML = FALSE
)

# M_v1: improved model — collinearity-corrected, extended soil block
#
# Design decisions vs user's models:
#   + aridity_index replaces the collinear climate cluster
#     (elevation r=-0.91 with tmin; agera5_cum_rh09 r=0.96 with crop_duration)
#     aridity_index chosen by AIC sweep (best AIC=-18.4; partial r=+0.255)
#   + N_Soil added (total soil N suppresses BNF; r=-0.169 with NDFA)
#   + weed_mgt added (weed pressure affects soybean growth and N demand)
#   + seed_type x inoculant_use interaction dropped (not significant in user M1/M2)
#   - elevation/chirps/tmin dropped (collinear with aridity_index)
m_v1 <- lmerTest::lmer(
  final_ndfa_grass ~
    pd_s + I(pd_s^2) +         # plant density (non-linear, *** in user M2)
    arid_s +                   # aridity (best single climate representative)
    phos_s + ecec_s + nsoi_s + # soil P, CEC, total N
    inoculant_use +            # rhizobium inoculation (sig. in user M1)
    seed_type +                # seed type
    farmer_gender + weed_mgt + # socio-agronomic factors
    (1 | province / district / ward / village),
  data = df_pd, REML = FALSE
)

# M_v2: trimmed — keep only terms with |t| > 1.0 in M_v1 to reduce overfitting
m_v2 <- lmerTest::lmer(
  final_ndfa_grass ~
    pd_s + I(pd_s^2) +  # *** plant density quadratic
    arid_s +            # aridity (partial r = +0.255 after plant_density)
    phos_s + ecec_s +   # soil P (r = -0.33) and ECEC (r = -0.20)
    inoculant_use +     # rhizobium inoculation (significant)
    farmer_gender +     # marginally significant
    (1 | province / district / ward / village),
  data = df_pd, REML = FALSE
)


# -- 3. Print summaries -------------------------------------------------------

cat("=== NDFA-grass LMM analysis - Malawi 2024 ===\n")
cat("Response: final_ndfa_grass (original [0,1] scale)\n")
cat("RE structure: (1 | province / district / ward / village)\n")

summarise_model("M_user1 - replicate user model 1 (n=98)",  m_user1, df)
summarise_model("M_user2 - replicate user model 2 (n=90)",  m_user2, df_pd)
summarise_model("M_v1    - improved (n=90)",                m_v1,    df_pd)
summarise_model("M_v2    - trimmed  (n=90)",                m_v2,    df_pd)


# -- 4. Comparison table -------------------------------------------------------

cat("\n\n=== COMPARISON TABLE ===\n")

models      <- list(m_user1, m_user2, m_v1, m_v2)
model_names <- c("M_user1 (n=98)", "M_user2 (n=90)",
                 "M_v1_improved (n=90)", "M_v2_trimmed (n=90)")
datasets    <- list(df, df_pd, df_pd, df_pd)

comparison <- do.call(rbind, lapply(seq_along(models), function(i) {
  r2   <- r2_lmer(models[[i]])
  rloo <- r2_loo(models[[i]], datasets[[i]])
  data.frame(
    model    = model_names[i],
    AIC      = round(AIC(models[[i]]), 1),
    R2m      = round(r2["R2m"], 3),
    R2c      = round(r2["R2c"], 3),
    R2_LOO   = round(rloo, 3),
    RMSE     = round(sqrt(mean(residuals(models[[i]])^2)), 4),
    n_params = attr(logLik(models[[i]]), "df"),
    row.names = NULL
  )
}))

print(comparison, row.names = FALSE)

cat("\nNotes:\n")
cat("  R2m/R2c: Nakagawa & Schielzeth (2013), computed without MuMIn.\n")
cat("  R2_LOO: leave-one-out R2 using fixed-effects-only prediction.\n")
cat("  n=90 models exclude 8 NAs in plant_density_per_ha.\n")
cat("  Singular fits expected: only 2 provinces -> province RE = 0.\n")
cat("  aridity_index replaces collinear cluster:\n")
cat("    elevation / chirps_cum_rain_mm / agera5_cum_rh09 / crop_duration.\n")
