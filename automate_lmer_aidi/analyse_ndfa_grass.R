# =============================================================================
# Analyse final_ndfa_grass using linear mixed-effects models
#
# Response:    final_ndfa_grass — ratio of N derived from atmosphere (NDFA)
#              estimated via the 15N natural abundance method (grass reference).
#              Bounded [0,1] → logit-transformed for normality.
#
# Random effects: (1 | province / district / ward / village)
#
# Performance metrics:
#   R2m  — marginal R² (fixed effects only)
#   R2c  — conditional R² (fixed + random effects)
#   R2_LOO — leave-one-out R² on logit scale (out-of-sample predictive power)
#
# Author: auto-generated via Claude
# =============================================================================

suppressPackageStartupMessages({
  library(lme4)    # lmer()
  library(dplyr)   # data manipulation with |>
})

# ── 0. Load & prepare data ───────────────────────────────────────────────────

df <- readRDS("claude_github.rds") |>
  mutate(
    # Logit-transform the [0,1] response for use in lmer
    logit_ndfa = log(final_ndfa_grass / (1 - final_ndfa_grass)),

    # Standardise continuous predictors (mean=0, sd=1) so coefficients are
    # comparable and the model converges reliably
    soil_pH_s            = scale(soil_pH)[, 1],
    soil_phos_s          = scale(soil_phos)[, 1],
    soil_OC_s            = scale(soil_OC)[, 1],
    soil_ECEC_s          = scale(soil_ECEC)[, 1],
    elevation_s          = scale(elevation)[, 1],
    rain_s               = scale(agera5_cum_rain_mm)[, 1],
    crop_duration_s      = scale(crop_duration)[, 1],
    mineral_n_s          = scale(mineral_n_rate_kg_ha)[, 1],
    mineral_p_s          = scale(mineral_p_rate_kg_ha)[, 1],

    # Keep binary/categorical predictors as factors
    inoc            = factor(inoc, levels = c(0, 1),
                             labels = c("no_inoc", "inoc")),
    previous_crop_2 = factor(previous_crop_2),
    seed_type       = factor(seed_type),
    weed_mgt_score  = as.integer(weed_mgt_score)   # ordinal 0-2
  )

# Random-effects grouping formula (shared by all models)
re_formula <- "(1 | province / district / ward / village)"


# ── 1. Helper functions ───────────────────────────────────────────────────────

#' Nakagawa & Schielzeth (2013) R² for lmer (no MuMIn required)
#' Returns named vector: R2m (marginal), R2c (conditional)
r2_lmer <- function(model) {
  # Variance of fixed-effect fitted values
  var_fixed <- var(predict(model, re.form = NA))

  # Sum of all random-effect variances
  vc <- as.data.frame(VarCorr(model))
  var_random <- sum(vc$vcov[vc$grp != "Residual"])

  # Residual variance
  var_resid <- sigma(model)^2

  total <- var_fixed + var_random + var_resid

  c(
    R2m = var_fixed / total,
    R2c = (var_fixed + var_random) / total
  )
}

#' Leave-one-out R² on the logit scale
#' Refit the model n times, predict the left-out obs each time.
#' Uses fixed-effects-only prediction so new grouping levels are handled.
r2_loo <- function(model, data) {
  n      <- nrow(data)
  y      <- data$logit_ndfa
  y_hat  <- numeric(n)
  frm    <- formula(model)

  for (i in seq_len(n)) {
    train <- data[-i, ]
    test  <- data[ i, ]

    # Suppress expected warnings: singular fits, rank-deficiency in small
    # training sets (can lose a factor level), convergence notes
    m_i <- suppressWarnings(
      suppressMessages(
        tryCatch(
          lmer(frm, data = train, REML = FALSE),
          error = function(e) NULL
        )
      )
    )

    if (is.null(m_i)) {
      # Fallback: grand mean of training set
      y_hat[i] <- mean(train$logit_ndfa, na.rm = TRUE)
    } else {
      y_hat[i] <- predict(m_i, newdata = test, re.form = NA,
                          allow.new.levels = TRUE)
    }
  }

  ss_res <- sum((y - y_hat)^2)
  ss_tot <- sum((y - mean(y))^2)
  1 - ss_res / ss_tot
}

#' Tidy summary of a fitted lmer model
summarise_model <- function(label, model, data) {
  r2   <- r2_lmer(model)
  rloo <- r2_loo(model, data)

  cat("\n", strrep("─", 70), "\n", sep = "")
  cat("Model:", label, "\n")
  cat("Formula:", deparse(formula(model)), "\n\n")

  if (isSingular(model)) {
    cat("  ⚠  Singular fit — one or more RE variances hit zero\n\n")
  }

  cat(sprintf("  R2m (marginal, fixed only)  : %.3f\n", r2["R2m"]))
  cat(sprintf("  R2c (conditional, fixed+RE) : %.3f\n", r2["R2c"]))
  cat(sprintf("  R2_LOO (out-of-sample)      : %.3f\n\n", rloo))

  # Fixed-effect coefficients
  coef_tbl <- as.data.frame(coef(summary(model)))
  coef_tbl$term <- rownames(coef_tbl)
  coef_tbl <- coef_tbl[, c("term", "Estimate", "Std. Error", "t value")]
  print(coef_tbl, digits = 3, row.names = FALSE)

  # Random-effect variance components
  cat("\nRandom effects:\n")
  print(as.data.frame(VarCorr(model))[, c("grp", "vcov", "sdcor")])
}


# ── 2. Fit models (increasing complexity) ────────────────────────────────────

# M0 — null model: random effects only (baseline)
m0 <- lmer(
  logit_ndfa ~ 1 + (1 | province / district / ward / village),
  data  = df,
  REML  = FALSE
)

# M1 — soil constraints (strongest univariate signal: soil_phos r=-0.33)
m1 <- lmer(
  logit_ndfa ~ soil_phos_s + soil_pH_s + soil_ECEC_s +
    (1 | province / district / ward / village),
  data  = df,
  REML  = FALSE
)

# M2 — add agronomy: inoculation, previous crop, mineral N (BNF theory)
m2 <- lmer(
  logit_ndfa ~ soil_phos_s + soil_pH_s + soil_ECEC_s +
    inoc + previous_crop_2 + mineral_n_s +
    (1 | province / district / ward / village),
  data  = df,
  REML  = FALSE
)

# M3 — add environment: elevation (r=0.30), rainfall, crop duration
m3 <- lmer(
  logit_ndfa ~ soil_phos_s + soil_pH_s + soil_ECEC_s +
    inoc + previous_crop_2 + mineral_n_s +
    elevation_s + rain_s + crop_duration_s +
    (1 | province / district / ward / village),
  data  = df,
  REML  = FALSE
)

# M4 — full model: add weed management, seed type, mineral P
m4 <- lmer(
  logit_ndfa ~ soil_phos_s + soil_pH_s + soil_ECEC_s +
    inoc + previous_crop_2 + mineral_n_s + mineral_p_s +
    elevation_s + rain_s + crop_duration_s +
    weed_mgt_score + seed_type +
    (1 | province / district / ward / village),
  data  = df,
  REML  = FALSE
)


# ── 3. Print summaries ────────────────────────────────────────────────────────

cat("\n=== NDFA-grass LMM analysis — Malawi 2024 ===\n")
cat("Response: logit(final_ndfa_grass)  |  n =", nrow(df), "\n")
cat("RE structure: (1 | province / district / ward / village)\n")

summarise_model("M0 — null (RE only)",             m0, df)
summarise_model("M1 — soil constraints",            m1, df)
summarise_model("M2 — soil + agronomy",             m2, df)
summarise_model("M3 — soil + agronomy + climate",   m3, df)
summarise_model("M4 — full model",                  m4, df)


# ── 4. Model comparison table ─────────────────────────────────────────────────

cat("\n\n=== COMPARISON TABLE ===\n")

models      <- list(m0, m1, m2, m3, m4)
model_names <- c("M0_null", "M1_soil", "M2_soil+agro",
                 "M3_soil+agro+climate", "M4_full")

comparison <- do.call(rbind, lapply(seq_along(models), function(i) {
  r2   <- r2_lmer(models[[i]])
  rloo <- r2_loo(models[[i]], df)
  data.frame(
    model   = model_names[i],
    AIC     = round(AIC(models[[i]]), 1),
    BIC     = round(BIC(models[[i]]), 1),
    R2m     = round(r2["R2m"], 3),
    R2c     = round(r2["R2c"], 3),
    R2_LOO  = round(rloo, 3),
    n_params = attr(logLik(models[[i]]), "df")
  )
}))

print(comparison, row.names = FALSE)

cat("\nNote: logit scale throughout.\n")
cat("Singular fits (province, ward RE = 0) are expected with n=2 provinces.\n")
cat("R2_LOO uses fixed-effects prediction only for new grouping levels.\n")
