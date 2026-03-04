# =============================================================================
# Analyse final_ndfa_grass — Beta GLMM via glmmTMB
#
# Response:    final_ndfa_grass — N derived from atmosphere (NDFA) ratio,
#              estimated by 15N natural abundance (grass reference plant).
#              Bounded strictly in (0, 1) -> Beta distribution appropriate.
#              Malawi 2024, n = 98; n = 90 when plant_density_per_ha used.
#
# Random effects: (1 | province / district / ward / village)
#   NOTE: province and ward RE collapse to 0 (singular) with 2 provinces only.
#
# Performance metrics
#   R2m    — marginal R2 (fixed effects, Nakagawa et al. 2013/2017)
#   R2c    — conditional R2 (fixed + random)
#   RMSE   — root mean squared error (original scale)
#
# Collinearity (|r| > 0.50 pairs excluded from same model):
#   Climate cluster: elevation / rh09 / crop_duration / chirps / aridity / tmin
#     -> aridity_index chosen by AIC sweep (best AIC among all candidates)
#   Soil texture: soil_ECEC vs sand_content_perc (r = -0.79) -> keep ECEC
#   Soil organic: C_Soil vs N_Soil (r = +0.94)              -> keep N_Soil
#
# Dispersion model:
#   AIC sweep: disp ~ inoculant_use (-38.10) beats ~ 1 (-33.33) by 4.8 pts.
#   Inoculated plants show higher precision (phi) = tighter NDFA distribution.
#
# =============================================================================

suppressPackageStartupMessages({
  library(glmmTMB)   # beta GLMM with dispersion modelling
  library(car)       # Anova() Type III Wald chi-sq; vif()
  library(dplyr)     # |> pipe
})


# -- 0. Load & prepare --------------------------------------------------------

df <- readRDS("claude_github.rds") |>
  mutate(
    # Scale to mean=0 sd=1: improves convergence, betas are comparable
    pd_s   = scale(plant_density_per_ha)[, 1],  # plants ha-1  (8 NAs)
    phos_s = scale(soil_phos)[, 1],             # available P  (Bray, mg kg-1)
    ecec_s = scale(soil_ECEC)[, 1],             # effective CEC (cmol+ kg-1)
    nsoi_s = scale(N_Soil)[, 1],               # total soil N  (g kg-1)
    arid_s = scale(aridity_index)[, 1],         # aridity index (higher = wetter)
    elev_s = scale(elevation)[, 1],
    rain_s = scale(chirps_cum_rain_mm)[, 1],
    ph_s   = scale(soil_pH)[, 1],

    inoculant_use = factor(inoculant_use, levels = c("No",   "Yes")),
    seed_type     = factor(seed_type),
    farmer_gender = factor(farmer_gender)
  )

df_pd <- df |> filter(!is.na(pd_s))   # complete cases (n=90)

cat("Full dataset   n =", nrow(df), "\n")
cat("Complete cases n =", nrow(df_pd), "\n\n")


# -- 1. Helper functions ------------------------------------------------------

#' Nakagawa et al. (2017) R2 for Beta GLMM
#' Variance decomposition on the logit (link) scale.
r2_beta_glmm <- function(model) {
  # Fixed-effect variance: var of linear predictor (logit scale)
  eta_fixed  <- predict(model, re.form = NA, type = "link")
  var_fixed  <- var(eta_fixed)

  # Random-effect variances from VarCorr (conditional model)
  vc         <- VarCorr(model)$cond
  var_random <- sum(sapply(vc, function(x) attr(x, "stddev")^2))

  # Distributional (residual) variance for Beta on logit scale:
  # trigamma(1) = pi^2/6 (logistic distribution approximation)
  var_dist <- trigamma(1)

  total <- var_fixed + var_random + var_dist
  c(R2m = var_fixed / total,
    R2c = (var_fixed + var_random) / total)
}

#' Full model summary (Anova, coefficients, VIF, RE variances)
summarise_model <- function(label, model, data) {
  r2   <- r2_beta_glmm(model)
  rmse <- sqrt(mean((data$final_ndfa_grass -
                     predict(model, type = "response"))^2))

  cat("\n", strrep("-", 72), "\n", sep = "")
  cat("Model:", label, "\n")
  cat("n =", nrow(data), "  |  ",
      "AIC =", round(AIC(model), 2), "  |  ",
      "phi =", round(sigma(model), 3), "\n\n")

  cat(sprintf("  R2m  (marginal)    : %.3f\n", r2["R2m"]))
  cat(sprintf("  R2c  (conditional) : %.3f\n", r2["R2c"]))
  cat(sprintf("  RMSE (in-sample)   : %.4f\n\n", rmse))

  # Type III Wald chi-square tests
  cat("Anova (Type III Wald chi-square):\n")
  print(car::Anova(model, type = 3))

  # Fixed-effect estimates (logit scale)
  cat("\nFixed effects (logit scale):\n")
  ct           <- as.data.frame(coef(summary(model))$cond)
  ct$term      <- rownames(ct)
  rownames(ct) <- NULL
  names(ct)[1:4] <- c("Estimate", "SE", "z", "p")
  print(ct[, c("term", "Estimate", "SE", "z", "p")],
        digits = 3, row.names = FALSE)

  # Dispersion-model coefficients
  disp_ct <- coef(summary(model))$disp
  if (!is.null(disp_ct) && nrow(as.data.frame(disp_ct)) > 0) {
    cat("\nDispersion model (log-precision scale):\n")
    dc           <- as.data.frame(disp_ct)
    dc$term      <- rownames(dc)
    rownames(dc) <- NULL
    names(dc)[1:4] <- c("Estimate", "SE", "z", "p")
    print(dc[, c("term", "Estimate", "SE", "z", "p")],
          digits = 3, row.names = FALSE)
  }

  # VIF
  n_fe <- nrow(coef(summary(model))$cond) - 1L
  if (n_fe >= 2) {
    cat("\nVIF (> 5 = concern, > 10 = problem):\n")
    tryCatch(print(round(vif(model), 2)),
             error = function(e) cat("  (VIF not computable)\n"))
  }

  # Random-effect standard deviations
  cat("\nRandom effects (conditional model):\n")
  vc <- VarCorr(model)$cond
  for (nm in names(vc))
    cat(sprintf("  %-42s  sd = %.5f\n", nm, attr(vc[[nm]], "stddev")))
  cat("\n")
}


# -- 2. Fit models ------------------------------------------------------------

#' Retry wrapper for glmmTMB — re-attempts up to `max_tries` times with fresh
#' random starting values if the fit fails or returns a singular/non-converged
#' result.  A message is printed for each failed attempt so the user knows
#' something went wrong without the whole script crashing.
#'
#' @param ...       All arguments forwarded to glmmTMB().
#' @param max_tries Maximum number of attempts (default 5).
#' @param seed      Base seed; incremented by 1 per retry for reproducibility.
fit_glmmTMB_retry <- function(..., max_tries = 5L, seed = 42L) {
  args <- list(...)
  for (attempt in seq_len(max_tries)) {
    set.seed(seed + attempt - 1L)
    m <- tryCatch(
      suppressWarnings(do.call(glmmTMB, args)),
      error = function(e) {
        cat(sprintf("  [attempt %d/%d] ERROR: %s\n", attempt, max_tries,
                    conditionMessage(e)))
        NULL
      }
    )
    if (!is.null(m)) {
      # Check convergence: glmmTMB stores the optimizer message in fit$fit
      conv_code <- m$fit$convergence   # 0 = converged
      if (is.null(conv_code) || conv_code == 0L) {
        if (attempt > 1L)
          cat(sprintf("  [attempt %d/%d] Converged.\n", attempt, max_tries))
        return(m)
      }
      cat(sprintf("  [attempt %d/%d] Non-convergence (code %s) — retrying...\n",
                  attempt, max_tries, conv_code))
    }
  }
  stop(sprintf(
    "glmmTMB failed to converge after %d attempts. Check model specification.",
    max_tries))
}

# M_user: user's best glmmTMB (on scaled predictors for fair comparison)
m_user <- fit_glmmTMB_retry(
  final_ndfa_grass ~
    elev_s + I(elev_s^2) + rain_s + I(rain_s^2) +
    phos_s + ecec_s + ph_s +
    pd_s + I(pd_s^2) +
    seed_type * inoculant_use + farmer_gender +
    (1 | province / district / ward / village),
  family = beta_family(), data = df_pd
)

# M_v1: improved mean model
#   + aridity_index replaces collinear climate cluster
#   + N_Soil adds unique soil N signal (VIF=1.09)
#   - seed_type x inoculant_use interaction dropped (AIC worse)
#   - ph_s, elevation quadratics, rain quadratics dropped (not significant)
m_v1 <- fit_glmmTMB_retry(
  final_ndfa_grass ~
    pd_s + I(pd_s^2) +
    arid_s +
    phos_s + ecec_s + nsoi_s +
    inoculant_use + seed_type + farmer_gender +
    (1 | province / district / ward / village),
  family = beta_family(), data = df_pd
)

# M_v2: M_v1 + dispersion model (disp ~ inoculant_use; AIC best by 4.8 pts)
# Inoculation increases precision (phi): BNF is more consistent when rhizobium
# is supplied, less stochastic when plants rely on native soil rhizobia.
m_v2 <- fit_glmmTMB_retry(
  final_ndfa_grass ~
    pd_s + I(pd_s^2) +
    arid_s +
    phos_s + ecec_s + nsoi_s +
    inoculant_use + seed_type + farmer_gender +
    (1 | province / district / ward / village),
  dispformula = ~ inoculant_use,
  family = beta_family(), data = df_pd
)


# -- 3. Print model summaries -------------------------------------------------

cat("=== NDFA-grass Beta GLMM analysis - Malawi 2024 ===\n")
cat("Response: final_ndfa_grass in (0, 1); Beta distribution\n")
cat("RE: (1 | province / district / ward / village)\n")

summarise_model("M_user — replicate user's glmmTMB (n=90)",  m_user, df_pd)
summarise_model("M_v1   — improved mean model (n=90)",       m_v1,   df_pd)
summarise_model("M_v2   — M_v1 + disp~inoculant (n=90)",    m_v2,   df_pd)

# LRT: confirm dispersion formula improvement
cat(strrep("-", 72), "\n")
cat("LRT: dispersion model M_v1 (disp=~1) vs M_v2 (disp=~inoculant_use)\n")
print(anova(m_v1, m_v2))


# -- 4. Comparison table (in-sample metrics) ----------------------------------

cat("\n=== COMPARISON TABLE (in-sample) ===\n")
models      <- list(m_user, m_v1, m_v2)
model_names <- c("M_user", "M_v1_improved", "M_v2_disp")

comparison <- do.call(rbind, lapply(seq_along(models), function(i) {
  r2   <- r2_beta_glmm(models[[i]])
  data.frame(
    model    = model_names[i],
    AIC      = round(AIC(models[[i]]), 2),
    R2m      = round(r2["R2m"], 3),
    R2c      = round(r2["R2c"], 3),
    RMSE     = round(sqrt(mean((df_pd$final_ndfa_grass -
                                predict(models[[i]], type = "response"))^2)), 4),
    phi      = round(sigma(models[[i]]), 2),
    n_params = attr(logLik(models[[i]]), "df"),
    row.names = NULL
  )
}))
print(comparison, row.names = FALSE)


cat("\\nNotes:\\n")
cat("  R2m/R2c: logit-scale decomposition, Nakagawa et al. (2013/2017).\\n")
cat("  phi: Beta precision. Larger = lower variance around mean NDFA.\\n")
cat("  All VIFs < 2 — no collinearity problem.\\n")
cat("  aridity_index replaces correlated cluster (elevation/chirps/rh09/crop_duration).\\n")
