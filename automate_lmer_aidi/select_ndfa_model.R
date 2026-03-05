# =============================================================================
# Select and compare models for final_ndfa_grass — Malawi soybean BNF
#
# Two-phase workflow:
#   Phase 1 — Predictor selection: 5-fold CV with glmmTMB (Beta GLMM) across
#             28 candidate predictor sets (2–10 fixed-effect predictors each).
#             Winner = lowest mean CV RMSE.
#   Phase 2 — Model comparison: 5-fold CV on the winning predictor set,
#             comparing glmmTMB (Beta GLMM), lmerTest (Gaussian LMM), and
#             Random Forest (ranger via caret).
#
# Predictor search informed by:
#   • Raw correlations with final_ndfa_grass (agera5_cum_rh09 r=0.31,
#     elevation 0.30, crop_duration 0.25, soil_phos -0.33, tmin -0.27)
#   • Collinearity analysis in analyse_ndfa_grass.R
#   • M_v2 from analyse_ndfa_grass.R included as benchmark ("prev_best")
#
# Random effects in GLMM / LMM: (1 | province/district/ward/village)
# RF uses same fixed-effect predictors as winner — no extra variables.
#
# Authors: Deo, Joao, Robert, Fred
# Code documentation: Claude (Anthropic) — March 2026
# =============================================================================

suppressPackageStartupMessages({
  library(glmmTMB)    # Beta GLMM
  library(lme4)       # nobars() for RE stripping; lmerTest depends on it
  library(lmerTest)   # Gaussian LMM
  library(caret)      # RF via ranger
  library(dplyr)
  library(rsample)    # vfold_cv
})

# clean environment
rm(list = ls())

# =============================================================================
# CI mode — GitHub Actions sets CI=true automatically.
# Reduced settings keep the job under 30 min without changing any logic.
# =============================================================================
ci_mode <- nchar(Sys.getenv("CI")) > 0
if (ci_mode) {
  cat(">>> CI MODE: reduced folds, predictor sets, and RF trees\n\n")
  N_FOLDS      <- 3L   # 5 in production
  MAX_TRIES    <- 2L   # 5 in production
  RF_TREES     <- 50L  # 500 in production
  RF_TUNE      <- 2L   # 3 in production
  # 8 representative sets spanning the search space — keeps CI under 25 min
  SETS_TO_RUN  <- c("prev_best", "rh09_soil_mgmt", "elev_rh09_mgmt",
                    "rh09_phos_tmin_mgmt", "dur_rh09_soil_mgmt",
                    "parsimonious_rh09", "kitchen_sink", "weed_mgmt_clim")
} else {
  N_FOLDS      <- 5L
  MAX_TRIES    <- 5L
  RF_TREES     <- 500L
  RF_TUNE      <- 3L
  SETS_TO_RUN  <- NULL  # NULL = run all 28
}

# =============================================================================
# 0. Load & prepare data
# =============================================================================

# claude_github.rds lives in the same folder as this script.
# Run from that folder (setwd or Rscript from automate_lmer_aidi/).
dat00 <- readRDS("claude_github.rds")

df <- dat00 |>
  dplyr::select(
    final_ndfa_grass,
    # Farmer / household
    farmer_gender, main_soya_field_ha, leg_importance_perc,
    # Spatial hierarchy (random effects)
    province, district, ward, village,
    # Soil
    C_Soil, N_Soil, soil_pH, soil_ECEC, sand_content_perc, soil_phos,
    # Climate / environment
    chirps_cum_rain_mm, aridity_index, agera5_avg_tmin, agera5_avg_tmax,
    agera5_cum_srad_mj, agera5_cum_rh09, elevation, gdd,
    # Crop management
    planting_date, crop_duration, plant_density_per_ha, seeding_rate_kg_ha,
    seed_type, inoculant_use, fertilizer_use, weeding_mode, weed_mgt,
    planting_method, previous_crop_2, mineral_n_rate_kg_ha
  ) |>
  na.omit()

cat("Dataset: n =", nrow(df), "\n\n")

# Scale all continuous predictors (mean=0, sd=1).
# Scaling is done on the full dataset — fold subsets inherit the same scale.
df <- df |>
  mutate(
    pd_s    = scale(plant_density_per_ha)[, 1],
    sr_s    = scale(seeding_rate_kg_ha)[, 1],
    arid_s  = scale(aridity_index)[, 1],
    phos_s  = scale(soil_phos)[, 1],
    ecec_s  = scale(soil_ECEC)[, 1],
    nsoi_s  = scale(N_Soil)[, 1],
    csoi_s  = scale(C_Soil)[, 1],
    ph_s    = scale(soil_pH)[, 1],
    sand_s  = scale(sand_content_perc)[, 1],
    rain_s  = scale(chirps_cum_rain_mm)[, 1],
    tmin_s  = scale(agera5_avg_tmin)[, 1],
    tmax_s  = scale(agera5_avg_tmax)[, 1],
    srad_s  = scale(agera5_cum_srad_mj)[, 1],
    rh_s    = scale(agera5_cum_rh09)[, 1],   # r=+0.31 — strongest climate corr
    elev_s  = scale(elevation)[, 1],          # r=+0.30 — not in prior analysis
    gdd_s   = scale(gdd)[, 1],
    pdate_s = scale(planting_date)[, 1],
    dur_s   = scale(crop_duration)[, 1],      # r=+0.25
    fsz_s   = scale(main_soya_field_ha)[, 1],
    leg_s   = scale(leg_importance_perc)[, 1],
    nrate_s = scale(mineral_n_rate_kg_ha)[, 1],
    # Factors
    inoculant_use   = factor(inoculant_use,   levels = c("No", "Yes")),
    seed_type       = factor(seed_type),
    farmer_gender   = factor(farmer_gender),
    previous_crop_2 = factor(previous_crop_2),
    fertilizer_use  = factor(fertilizer_use),
    weeding_mode    = factor(weeding_mode),
    weed_mgt        = factor(weed_mgt),       # good/moderate/poor
    planting_method = factor(planting_method)
  )

RE   <- "(1 | province/district/ward/village)"
MGMT <- "inoculant_use + seed_type + farmer_gender"  # core management block

# =============================================================================
# 1. Define candidate predictor sets (2–10 fixed-effect predictors each)
# =============================================================================
# Organisation:
#   A. Baselines & prior benchmark
#   B. Climate-focused (testing rh09/elevation vs aridity)
#   C. Soil-focused
#   D. Management-focused
#   E. Mixed: climate + soil + management (3–8 vars)
#   F. Parsimonious (2–4 vars)
#   G. Kitchen sink (~10 vars)
# All sets include RE.

predictor_sets <- list(

  # ── A. Baselines & prior benchmark ──────────────────────────────────────
  # Management only
  mgmt_only = paste(MGMT, RE, sep = " + "),

  # M_v2 from analyse_ndfa_grass.R — aridity + phos/ECEC/N_Soil + dens + mgmt
  prev_best = paste(
    "pd_s + I(pd_s^2) + arid_s + phos_s + ecec_s + nsoi_s",
    MGMT, RE, sep = " + "),

  # ── B. Climate-focused ──────────────────────────────────────────────────
  # rh09 alone + mgmt (rh09 r=+0.31, best raw correlate)
  rh09_mgmt = paste("rh_s + inoculant_use + seed_type", RE, sep = " + "),

  # elevation alone + mgmt (elev r=+0.30, never tested before)
  elev_mgmt = paste("elev_s + inoculant_use + seed_type", RE, sep = " + "),

  # rh09 + elevation (complementary: moisture vs altitude)
  elev_rh09_mgmt = paste(
    "elev_s + rh_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # crop_duration (r=+0.25) + mgmt
  dur_mgmt = paste(
    "dur_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # tmin (r=-0.27) + mgmt
  tmin_mgmt = paste(
    "tmin_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # rh09 + tmin (temperature × humidity interaction-free)
  rh09_tmin_mgmt = paste(
    "rh_s + tmin_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # chirps + aridity (from prior analysis — aridity beat chirps individually)
  rain_arid_mgmt = paste(
    "rain_s + arid_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # GDD (growing degree-days) + mgmt
  gdd_mgmt = paste(
    "gdd_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # ── C. Soil-focused ─────────────────────────────────────────────────────
  # phos alone (r=-0.33, best raw soil correlate) + mgmt
  phos_mgmt = paste(
    "phos_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # Full soil block + mgmt
  soil_full_mgmt = paste(
    "phos_s + ecec_s + nsoi_s + ph_s + sand_s",
    MGMT, RE, sep = " + "),

  # Minimal soil (phos + ECEC — best AIC pair from prior analysis) + mgmt
  phos_ecec_mgmt = paste(
    "phos_s + ecec_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # ── D. Management-focused ───────────────────────────────────────────────
  # Weed management quality (categorical) + mgmt
  weed_mgmt = paste(
    "weed_mgt + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # Plant density (quadratic) + mgmt
  dens_mgmt = paste(
    "pd_s + I(pd_s^2) + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # Previous crop + mgmt (legume rotation effect)
  prevcrop_mgmt = paste(
    "previous_crop_2 + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # Planting date + crop duration + mgmt (phenological timing)
  temporal_mgmt = paste(
    "pdate_s + dur_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # N fertilizer rate + mgmt (N suppression of BNF hypothesis)
  nfert_mgmt = paste(
    "nrate_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # ── E. Mixed: climate + soil + management ───────────────────────────────
  # rh09 + phos + tmin + mgmt (top-3 numeric correlates + inoculant)
  rh09_phos_tmin_mgmt = paste(
    "rh_s + phos_s + tmin_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # rh09 + soil block + mgmt (replace aridity with rh09)
  rh09_soil_mgmt = paste(
    "rh_s + phos_s + ecec_s + nsoi_s",
    MGMT, RE, sep = " + "),

  # elevation + rh09 + soil block + mgmt
  elev_rh09_soil_mgmt = paste(
    "elev_s + rh_s + phos_s + ecec_s + nsoi_s",
    MGMT, RE, sep = " + "),

  # crop_duration + rh09 + soil + mgmt (phenology + moisture + soil)
  dur_rh09_soil_mgmt = paste(
    "dur_s + rh_s + phos_s + ecec_s + nsoi_s",
    MGMT, RE, sep = " + "),

  # Weed management + climate + soil + mgmt
  weed_mgmt_clim = paste(
    "weed_mgt + rh_s + phos_s + ecec_s",
    "inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # tmin + crop_duration + phos + mgmt (short, biologically interpretable)
  tmin_dur_phos_mgmt = paste(
    "tmin_s + dur_s + phos_s + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + "),

  # ── F. Parsimonious (2–4 predictors) ────────────────────────────────────
  # rh09 + inoculant (minimal biologically motivated model)
  parsimonious_rh09 = paste(
    "rh_s + inoculant_use", RE, sep = " + "),

  # rh09 + phos + inoculant (3 predictors, top correlates)
  parsimonious_3 = paste(
    "rh_s + phos_s + inoculant_use", RE, sep = " + "),

  # ── G. Kitchen sink (~10 fixed-effect predictors) ───────────────────────
  # Everything that's not collinear with something else
  kitchen_sink = paste(
    "elev_s + rh_s + tmin_s + dur_s",
    "phos_s + ecec_s + nsoi_s + ph_s",
    "weed_mgt + inoculant_use + seed_type + farmer_gender",
    RE, sep = " + ")
)

# =============================================================================
# 2. Helper: glmmTMB retry wrapper
# =============================================================================

fit_glmmTMB_retry <- function(..., max_tries = MAX_TRIES, seed = 42L) {
  args <- list(...)
  for (attempt in seq_len(max_tries)) {
    set.seed(seed + attempt - 1L)
    m <- tryCatch(
      suppressWarnings(do.call(glmmTMB, args)),
      error = function(e) {
        cat(sprintf("    [attempt %d/%d] ERROR: %s\n",
                    attempt, max_tries, conditionMessage(e)))
        NULL
      }
    )
    if (!is.null(m)) {
      conv_code <- m$fit$convergence
      if (is.null(conv_code) || conv_code == 0L) {
        if (attempt > 1L)
          cat(sprintf("    [attempt %d/%d] Converged.\n", attempt, max_tries))
        return(m)
      }
      cat(sprintf("    [attempt %d/%d] Non-convergence (code %s) — retrying...\n",
                  attempt, max_tries, conv_code))
    }
  }
  stop(sprintf("glmmTMB failed after %d attempts.", max_tries))
}

# =============================================================================
# 3. Helper: CV metrics
# =============================================================================

cv_metrics <- function(actual, predicted) {
  ok  <- complete.cases(actual, predicted)
  a   <- actual[ok];  p <- predicted[ok]
  if (length(a) < 2) return(c(R2 = NA, RMSE = NA, RRMSE = NA, MAE = NA))
  sse  <- sum((a - p)^2)
  sst  <- sum((a - mean(a))^2)
  rmse <- sqrt(mean((a - p)^2))
  c(R2    = 1 - sse / sst,
    RMSE  = rmse,
    RRMSE = rmse / mean(a),
    MAE   = mean(abs(a - p)))
}

# =============================================================================
# 4. PHASE 1 — Predictor selection via glmmTMB 5-fold CV
# =============================================================================

cat("=============================================================\n")
cat("PHASE 1: Predictor selection (glmmTMB 5-fold CV)\n")
cat("=============================================================\n\n")

# Filter sets for CI mode (NULL = keep all)
sets_active <- if (!is.null(SETS_TO_RUN)) {
  predictor_sets[names(predictor_sets) %in% SETS_TO_RUN]
} else {
  predictor_sets
}
cat("Running", length(sets_active), "predictor sets with",
    N_FOLDS, "folds each\n\n")

set.seed(123)
folds <- rsample::vfold_cv(df, v = N_FOLDS, strata = "final_ndfa_grass")

selector_results <- lapply(names(sets_active), function(set_name) {

  cat("Predictor set:", set_name, "\n")
  fml <- as.formula(paste("final_ndfa_grass ~", sets_active[[set_name]]))

  fold_rmse <- vapply(seq_len(nrow(folds)), function(i) {
    tr  <- rsample::training(folds$splits[[i]])
    val <- rsample::testing(folds$splits[[i]])
    m   <- tryCatch(
      fit_glmmTMB_retry(formula = fml, data = tr,
                        family = beta_family(), seed = 100L * i),
      error = function(e) NULL
    )
    if (is.null(m)) return(NA_real_)
    preds <- tryCatch(
      pmax(pmin(predict(m, newdata = val, type = "response",
                        allow.new.levels = TRUE), 0.999), 0.001),
      error = function(e) rep(NA_real_, nrow(val))
    )
    cv_metrics(val$final_ndfa_grass, preds)[["RMSE"]]
  }, numeric(1))

  cat(sprintf("  Mean CV RMSE = %.4f  (sd = %.4f)\n\n",
              mean(fold_rmse, na.rm = TRUE),
              sd(fold_rmse,   na.rm = TRUE)))

  data.frame(
    set         = set_name,
    RMSE_mean   = mean(fold_rmse, na.rm = TRUE),
    RMSE_sd     = sd(fold_rmse,   na.rm = TRUE),
    n_folds_ok  = sum(!is.na(fold_rmse))
  )
})

selector_table <- do.call(rbind, selector_results) |>
  arrange(RMSE_mean)

cat("=== Predictor selection summary (sorted by CV RMSE) ===\n")
print(selector_table |> mutate(across(where(is.numeric), ~round(., 4))),
      row.names = FALSE)

best_set <- selector_table$set[1]
cat(sprintf("\n>> Best predictor set: '%s'\n\n", best_set))

# =============================================================================
# 5. PHASE 2 — 3-model comparison on the winning predictor set
# =============================================================================

cat("=============================================================\n")
cat("PHASE 2: 3-model comparison on best predictor set\n")
cat("  Set:", best_set, "\n")
cat("=============================================================\n\n")

best_preds_rhs <- predictor_sets[[best_set]]
glmm_fml  <- as.formula(paste("final_ndfa_grass ~", best_preds_rhs))
lmer_fml  <- glmm_fml   # same formula; lmerTest treats beta as Gaussian

# Columns used by the winning formula (for RF feature matrix.
# lme4::nobars() strips (1|...) RE terms before all.vars() — using
# all.vars() directly on a formula with | causes a parse error.
pred_vars <- all.vars(lme4::nobars(glmm_fml))
pred_vars <- unique(pred_vars[pred_vars != "final_ndfa_grass"])

cat("Fixed-effect predictors passed to RF:\n  ")
cat(paste(pred_vars, collapse = ", "), "\n\n")

set.seed(123)
folds2 <- rsample::vfold_cv(df, v = N_FOLDS, strata = "final_ndfa_grass")

all_preds <- vector("list", nrow(folds2))

for (i in seq_len(nrow(folds2))) {

  cat("--- Fold", i, "of 5 ---\n")
  tr  <- rsample::training(folds2$splits[[i]])
  val <- rsample::testing(folds2$splits[[i]])

  # ---- glmmTMB ----
  cat("  glmmTMB (Beta GLMM)...")
  glmm_pred <- tryCatch({
    m <- fit_glmmTMB_retry(formula = glmm_fml, data = tr,
                           family = beta_family(), seed = 10L * i)
    pmax(pmin(predict(m, newdata = val, type = "response",
                      allow.new.levels = TRUE), 0.999), 0.001)
  }, error = function(e) {
    cat(" ERROR:", conditionMessage(e))
    rep(NA_real_, nrow(val))
  })
  cat(" done.\n")

  # ---- lmerTest ----
  cat("  lmerTest (Gaussian LMM)...")
  lmer_pred <- tryCatch({
    m <- suppressMessages(lmerTest::lmer(lmer_fml, data = tr,
                                         control = lmerControl(
                                           optimizer = "bobyqa",
                                           optCtrl = list(maxfun = 2e5))))
    pmax(pmin(predict(m, newdata = val, allow.new.levels = TRUE), 1), 0)
  }, error = function(e) {
    cat(" ERROR:", conditionMessage(e))
    rep(NA_real_, nrow(val))
  })
  cat(" done.\n")

  # ---- Random Forest ----
  cat("  Random Forest (ranger)...")
  rf_pred <- tryCatch({
    # Use only the fixed-effect columns for a fair feature-matched comparison
    tr_rf  <- tr  |> dplyr::select(final_ndfa_grass, all_of(pred_vars))
    val_rf <- val |> dplyr::select(all_of(pred_vars))

    tc <- caret::trainControl(method = "cv", number = 3, verboseIter = FALSE)
    m  <- caret::train(
      x          = tr_rf |> dplyr::select(-final_ndfa_grass),
      y          = tr_rf$final_ndfa_grass,
      method     = "ranger",
      trControl  = tc,
      tuneLength = RF_TUNE,
      num.trees  = RF_TREES,
      importance = "permutation"
    )
    pmax(pmin(predict(m, newdata = val_rf), 1), 0)
  }, error = function(e) {
    cat(" ERROR:", conditionMessage(e))
    rep(NA_real_, nrow(val))
  })
  cat(" done.\n\n")

  all_preds[[i]] <- data.frame(
    fold         = i,
    actual       = val$final_ndfa_grass,
    glmmTMB_pred = glmm_pred,
    lmerTest_pred = lmer_pred,
    RF_pred      = rf_pred
  )
}

predictions_df <- do.call(rbind, all_preds)

# =============================================================================
# 6. Results — per-fold and overall
# =============================================================================

fold_metrics <- predictions_df |>
  group_by(fold) |>
  summarise(
    glmmTMB_R2    = cv_metrics(actual, glmmTMB_pred)[["R2"]],
    glmmTMB_RMSE  = cv_metrics(actual, glmmTMB_pred)[["RMSE"]],
    glmmTMB_RRMSE = cv_metrics(actual, glmmTMB_pred)[["RRMSE"]],
    glmmTMB_MAE   = cv_metrics(actual, glmmTMB_pred)[["MAE"]],
    lmerTest_R2    = cv_metrics(actual, lmerTest_pred)[["R2"]],
    lmerTest_RMSE  = cv_metrics(actual, lmerTest_pred)[["RMSE"]],
    lmerTest_RRMSE = cv_metrics(actual, lmerTest_pred)[["RRMSE"]],
    lmerTest_MAE   = cv_metrics(actual, lmerTest_pred)[["MAE"]],
    RF_R2    = cv_metrics(actual, RF_pred)[["R2"]],
    RF_RMSE  = cv_metrics(actual, RF_pred)[["RMSE"]],
    RF_RRMSE = cv_metrics(actual, RF_pred)[["RRMSE"]],
    RF_MAE   = cv_metrics(actual, RF_pred)[["MAE"]],
    .groups = "drop"
  )

summarise_across_folds <- function(col_prefix) {
  cols <- paste0(col_prefix, c("_R2", "_RMSE", "_RRMSE", "_MAE"))
  data.frame(
    Model      = col_prefix,
    R2_mean    = mean(fold_metrics[[cols[1]]], na.rm = TRUE),
    R2_sd      = sd(  fold_metrics[[cols[1]]], na.rm = TRUE),
    RMSE_mean  = mean(fold_metrics[[cols[2]]], na.rm = TRUE),
    RMSE_sd    = sd(  fold_metrics[[cols[2]]], na.rm = TRUE),
    RRMSE_mean = mean(fold_metrics[[cols[3]]], na.rm = TRUE),
    MAE_mean   = mean(fold_metrics[[cols[4]]], na.rm = TRUE),
    MAE_sd     = sd(  fold_metrics[[cols[4]]], na.rm = TRUE)
  )
}

overall_metrics <- do.call(
  rbind,
  lapply(c("glmmTMB", "lmerTest", "RF"), summarise_across_folds)
) |>
  arrange(RMSE_mean)

cat("=============================================================\n")
cat("PHASE 2 RESULTS — Best predictor set:", best_set, "\n")
cat("=============================================================\n\n")

cat("--- Overall CV performance (mean ± sd across 5 folds) ---\n")
print(overall_metrics |> mutate(across(where(is.numeric), ~round(., 4))),
      row.names = FALSE)

cat("\n--- Fold-level performance ---\n")
print(fold_metrics |> mutate(across(where(is.numeric), ~round(., 4))),
      row.names = FALSE)

# =============================================================================
# 7. Save results
# =============================================================================

output_date <- format(Sys.Date(), "%Y-%m-%d")
saveRDS(
  list(
    selector_table  = selector_table,
    best_set        = best_set,
    best_predictors = best_preds_rhs,
    overall_metrics = overall_metrics,
    fold_metrics    = fold_metrics,
    predictions     = predictions_df
  ),
  file = paste0(output_date, '.ndfa_model_selection_cv_results.rds')
)
cat("\nResults saved to ",
    output_date, ".ndfa_model_selection_cv_results.rds\n", sep = "")
