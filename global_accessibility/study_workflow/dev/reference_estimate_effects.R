#!/usr/bin/env Rscript
# estimate_effects.R - effect estimation of the study "accessibility change, land-use change and crop
# yields in Sub-Saharan Africa" (Phase 3, Gate C). Called by access_effects_v01.py (stage estimate):
#   Rscript estimate_effects.R <panels folder> <output folder> [config.json]
#
# Inputs (written by stage panels), one row per unit x year (x crop for yields):
#   e1_cells.parquet    E1/E1b: 30" cells (sampled), outcomes conv_share, loss_share, newcrop_share
#   e2a_admin.parquet   E2a: admin unit x crop x season, outcome log_yield
#   e2b_ea.parquet      E2b: LSMS enumeration area x crop, outcome log_yield
#   e3_longdiff.parquet E3: unit x epoch, long differences d_<outcome> and d_access__<spec>
# Treatment columns per specification <spec> = <version>_<layer> (e.g. roadonly_cities_11):
#   g__<spec>        first year of an access gain (0 = never), cohort for staggered DiD
#   gburst__<spec>   same, for events attributed to mapping bursts (placebo; 0 otherwise)
#   dose__<spec>     access gain = -(log travel time change) from the year before the event to the
#                    last year (0 for never-treated), for the continuous design
#   band__<spec>     spatial bands: 1 treated (0-5 km of a new road), 0 control (10-30 km), NA excluded
# Common columns: id (integer unit id), year, region (region x year fixed effects), lat, lon, w (weight),
#   w_cem (coarsened exact matching weight of never-treated controls; NA = unmatched).
#
# Outputs: estimates.csv (every coefficient), gate_c.csv (Gate C per dataset x outcome x crop),
#   sessionInfo.txt. Every model that fails is logged in estimates.csv with its error, never dropped.

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(readr)
  library(purrr)
  library(tibble)
  library(stringr)
})

args <- commandArgs(trailingOnly = TRUE)
panels_dir <- if (length(args) >= 1) args[[1]] else "ae_results/panels"
out_dir <- if (length(args) >= 2) args[[2]] else "ae_results/estimates"
cfg_file <- if (length(args) >= 3) args[[3]] else NA_character_
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# defaults (approved 2026-10-27); config.json from the Python script overrides them
cfg <- list(
  primary_spec = "roadonly_cities_11",
  specs = c("roadonly_cities_11", "total_cities_11", "roadonly_cities_12", "roadonly_ports_5"),
  min_e = -5L, max_e = 5L,
  conley_km = 50, conley_km_alt = c(25, 100),
  bh_q = 0.10,
  gate_pre_p = 0.10, gate_pre_ratio = 1 / 3, gate_placebo_ratio = 0.5, gate_placebo_p = 0.05,
  bootstrap_iters = 999L,
  seed = 20261028L,
  max_units_cs = 200000L,
  composite_shift = 0.05, gate_v_r = 0.3, gate_v_min_n = 30L, gate_v_r_sensor = 0.8
)
if (!is.na(cfg_file) && file.exists(cfg_file)) {
  user <- jsonlite::fromJSON(cfg_file)
  cfg[names(user)] <- user
}
set.seed(cfg$seed)

have <- function(pkg) requireNamespace(pkg, quietly = TRUE)
for (pkg in c("fixest", "did", "nanoparquet", "jsonlite")) {
  if (!have(pkg)) stop("R package '", pkg, "' is missing: install.packages('", pkg, "')")
}

log_msg <- function(...) {
  cat(format(Sys.time(), "[%Y-%m-%d %H:%M:%S] "), ..., "\n", sep = "")
}

read_panel <- function(name) {
  f <- file.path(panels_dir, paste0(name, ".parquet"))
  if (!file.exists(f)) {
    log_msg(name, ": not found, skipped")
    return(NULL)
  }
  nanoparquet::read_parquet(f) |> as_tibble()
}

# one row per coefficient; failures are kept with their message
result_row <- function(..., estimate = NA_real_, se = NA_real_, p = NA_real_, n = NA_integer_,
                       error = NA_character_) {
  tibble(..., estimate = as.numeric(estimate)[1], se = as.numeric(se)[1], p = as.numeric(p)[1],
         n = as.integer(n)[1], error = error)
}

safely_run <- function(expr_fun, meta) {
  out <- tryCatch(expr_fun(), error = function(e) e)
  if (inherits(out, "error")) {
    out <- do.call(result_row, c(meta, list(term = "overall", error = conditionMessage(out))))
  }
  # crop is NA for the cell panel and may come back as logical or integer: one type for bind_rows
  out |> mutate(crop = as.character(crop))
}

# --- Callaway and Sant'Anna (did::att_gt), never-treated or not-yet-treated controls ---------------
cs_estimate <- function(d, yname, gname, control, meta, weights = "w") {
  d <- d |>
    filter(!is.na(.data[[yname]]), !is.na(.data[[gname]]), .data[[gname]] >= 0)
  if (!is.null(weights)) d <- d |> filter(!is.na(.data[[weights]]))
  units <- unique(d$id)
  if (length(units) > cfg$max_units_cs) {
    # keep every treated unit and a random draw of controls (recorded seed), weights rescaled
    treated <- unique(d$id[d[[gname]] > 0])
    ctrl <- setdiff(units, treated)
    keep_ctrl <- sample(ctrl, max(0, cfg$max_units_cs - length(treated)))
    d <- d |> filter(id %in% c(treated, keep_ctrl))
  }
  n_treated <- dplyr::n_distinct(d$id[d[[gname]] > 0])
  if (n_treated == 0) stop("no treated units")
  att <- did::att_gt(
    yname = yname, tname = "year", idname = "id", gname = gname, data = as.data.frame(d),
    control_group = control, weightsname = weights, panel = TRUE,
    allow_unbalanced_panel = TRUE, base_period = "varying", est_method = "reg",
    bstrap = TRUE, biters = cfg$bootstrap_iters, clustervars = "id", print_details = FALSE
  )
  dyn <- did::aggte(att, type = "dynamic", min_e = cfg$min_e, max_e = cfg$max_e, na.rm = TRUE)
  simple <- did::aggte(att, type = "simple", na.rm = TRUE)
  # Wald pre-test of did (valid with the default varying base period)
  pre_p <- if (!is.null(att$Wpval)) as.numeric(att$Wpval)[1] else NA_real_
  dyn_rows <- tibble(
    term = paste0("e", dyn$egt), estimate = as.numeric(dyn$att.egt), se = as.numeric(dyn$se.egt)
  ) |>
    mutate(p = 2 * stats::pnorm(-abs(estimate / se)))
  bind_rows(
    do.call(result_row, c(meta, list(term = "overall", estimate = simple$overall.att,
                                     se = simple$overall.se,
                                     p = 2 * stats::pnorm(-abs(simple$overall.att / simple$overall.se)),
                                     n = dplyr::n_distinct(d$id)))),
    do.call(result_row, c(meta, list(term = "pretest_wald", estimate = NA_real_, p = pre_p,
                                     n = n_treated))),
    dyn_rows |> mutate(!!!meta, n = n_treated, error = NA_character_)
  )
}

# --- Sun and Abraham (fixest::sunab) with region x year effects and Conley errors -----------------
sa_estimate <- function(d, yname, gname, meta, conley_km = cfg$conley_km) {
  d <- d |>
    filter(!is.na(.data[[yname]]), !is.na(.data[[gname]]), .data[[gname]] >= 0) |>
    mutate(cohort = if_else(.data[[gname]] > 0, .data[[gname]], 10000L))
  fml <- stats::as.formula(paste0(yname, " ~ sunab(cohort, year) | id + region^year"))
  m <- fixest::feols(fml, data = d, weights = ~w, vcov = fixest::conley(cutoff = conley_km),
                     notes = FALSE, warn = FALSE)
  agg <- aggregate(m, agg = "ATT")
  ct <- fixest::coeftable(m)
  rel <- tibble(term = rownames(ct), estimate = ct[, 1], se = ct[, 2], p = ct[, 4]) |>
    mutate(term = str_replace(term, "^year::", "e")) |>
    filter(str_detect(term, "^e-?\\d+$"))
  bind_rows(
    do.call(result_row, c(meta, list(term = "overall", estimate = agg[1, 1], se = agg[1, 2],
                                     p = agg[1, 4], n = stats::nobs(m)))),
    rel |> mutate(!!!meta, n = stats::nobs(m), error = NA_character_)
  )
}

# --- two-way fixed effects, for comparison only (biased with staggered timing) --------------------
twfe_estimate <- function(d, yname, gname, meta, dose = NULL) {
  d <- d |>
    filter(!is.na(.data[[yname]]), !is.na(.data[[gname]]), .data[[gname]] >= 0) |>
    mutate(post = as.integer(.data[[gname]] > 0 & year >= .data[[gname]]))
  rhs <- if (is.null(dose)) "post" else "post_dose"
  if (!is.null(dose)) d <- d |> mutate(post_dose = post * .data[[dose]])
  m <- fixest::feols(stats::as.formula(paste0(yname, " ~ ", rhs, " | id + region^year")), data = d,
                     weights = ~w, vcov = fixest::conley(cutoff = cfg$conley_km),
                     notes = FALSE, warn = FALSE)
  ct <- fixest::coeftable(m)
  do.call(result_row, c(meta, list(term = "overall", estimate = ct[1, 1], se = ct[1, 2],
                                   p = ct[1, 4], n = stats::nobs(m))))
}

# --- continuous dose: Callaway, Goodman-Bacon and Sant'Anna (contdid) when available ---------------
dose_estimate <- function(d, yname, gname, dname, meta) {
  if (!have("contdid")) stop("package contdid not installed (continuous design skipped)")
  # contdid wants a time-invariant dose, 0 for the never-treated (as dose__<spec> is built)
  res <- contdid::cont_did(
    yname = yname, tname = "year", idname = "id", gname = gname, dname = dname,
    # treated units need a positive dose (an access gain); others are left out of this design
    data = as.data.frame(d |> filter(!is.na(.data[[yname]]), .data[[gname]] >= 0, !is.na(.data[[dname]]),
                                     .data[[gname]] == 0 | .data[[dname]] > 0)),
    target_parameter = "slope", aggregation = "dose", treatment_type = "continuous",
    control_group = "notyettreated", biters = cfg$bootstrap_iters
  )
  s <- summary(res)
  est <- if (!is.null(res$overall_acrt)) res$overall_acrt else NA_real_
  se <- if (!is.null(res$overall_acrt_se)) res$overall_acrt_se else NA_real_
  do.call(result_row, c(meta, list(term = "overall_acrt", estimate = est, se = se,
                                   p = 2 * stats::pnorm(-abs(est / se)),
                                   n = dplyr::n_distinct(d$id))))
}

# --- long differences (E3): d_outcome on access gain, region effects, Conley errors ---------------
ld_estimate <- function(d, yname, xname, meta, conley_km = cfg$conley_km) {
  covs <- intersect(c("d_rain", "d_logpop", "d_conflict"), names(d)) |>
    Filter(f = \(v) any(!is.na(d[[v]])))     # pooled files: all-NA columns for datasets without them
  rhs <- paste(c(xname, covs), collapse = " + ")
  m <- fixest::feols(stats::as.formula(paste0(yname, " ~ ", rhs, " | region^epoch")), data = d,
                     weights = ~w, vcov = fixest::conley(cutoff = conley_km),
                     notes = FALSE, warn = FALSE)
  ct <- fixest::coeftable(m)
  do.call(result_row, c(meta, list(term = "overall", estimate = ct[xname, 1], se = ct[xname, 2],
                                   p = ct[xname, 4], n = stats::nobs(m))))
}

# --- run every design for one dataset -------------------------------------------------------------
run_dataset <- function(d, dataset, outcomes, by_crop = FALSE) {
  if (is.null(d)) return(tibble())
  groups <- if (by_crop) sort(unique(d$crop)) else NA_character_
  specs <- intersect(cfg$specs, str_remove(grep("^g__", names(d), value = TRUE), "^g__"))
  map_dfr(groups, function(cr) {
    dd <- if (by_crop) d |> filter(crop == cr) else d
    present <- outcomes[outcomes %in% names(dd)]
    present <- present[vapply(present, \(y) any(!is.na(dd[[y]])), logical(1))]
    map_dfr(present, function(y) {
      map_dfr(specs, function(sp) {
        g <- paste0("g__", sp)
        base <- list(dataset = dataset, outcome = y, crop = cr, spec = sp)
        primary <- sp == cfg$primary_spec
        log_msg(dataset, " ", y, " ", cr, " ", sp)
        rows <- list(
          safely_run(\() cs_estimate(dd, y, g, "notyettreated",
                                     c(base, estimator = "cs", control = "notyettreated")),
                     c(base, estimator = "cs", control = "notyettreated")),
          safely_run(\() cs_estimate(dd, y, g, "nevertreated",
                                     c(base, estimator = "cs", control = "nevertreated")),
                     c(base, estimator = "cs", control = "nevertreated"))
        )
        if (primary) {
          if ("w_cem" %in% names(dd)) {
            rows <- c(rows, list(safely_run(\() cs_estimate(dd, y, g, "nevertreated",
                                                            c(base, estimator = "cs", control = "matched"),
                                                            weights = "w_cem"),
                                            c(base, estimator = "cs", control = "matched"))))
          }
          band <- paste0("band__", sp)
          if (band %in% names(dd)) {
            db <- dd |> filter(!is.na(.data[[band]])) |>
              mutate(gband = if_else(.data[[band]] == 1L, .data[[g]], 0L))
            rows <- c(rows, list(safely_run(\() cs_estimate(db, y, "gband", "nevertreated",
                                                            c(base, estimator = "cs", control = "bands")),
                                            c(base, estimator = "cs", control = "bands"))))
          }
          gb <- paste0("gburst__", sp)
          if (gb %in% names(dd)) {
            dp <- dd |> filter(.data[[g]] == 0L | .data[[gb]] > 0L) |>
              mutate(gplacebo = .data[[gb]])
            rows <- c(rows, list(safely_run(\() cs_estimate(dp, y, "gplacebo", "nevertreated",
                                                            c(base, estimator = "cs_placebo_burst",
                                                              control = "nevertreated")),
                                            c(base, estimator = "cs_placebo_burst", control = "nevertreated"))))
          }
          rows <- c(rows, list(
            safely_run(\() sa_estimate(dd, y, g, c(base, estimator = "sunab", control = "nevertreated")),
                       c(base, estimator = "sunab", control = "nevertreated")),
            safely_run(\() twfe_estimate(dd, y, g, c(base, estimator = "twfe", control = "all")),
                       c(base, estimator = "twfe", control = "all"))
          ))
          dn <- paste0("dose__", sp)
          if (dn %in% names(dd)) {
            rows <- c(rows, list(
              safely_run(\() dose_estimate(dd, y, g, dn, c(base, estimator = "contdid", control = "notyettreated")),
                         c(base, estimator = "contdid", control = "notyettreated")),
              safely_run(\() twfe_estimate(dd, y, g, c(base, estimator = "twfe_dose", control = "all"), dose = dn),
                         c(base, estimator = "twfe_dose", control = "all"))
            ))
          }
        }
        bind_rows(rows)
      })
    })
  })
}

run_longdiff <- function(d) {
  if (is.null(d)) return(tibble())
  ys <- grep("^d_(?!access)", names(d), value = TRUE, perl = TRUE) |>
    setdiff(c("d_rain", "d_logpop", "d_conflict"))
  specs <- str_remove(grep("^d_access__", names(d), value = TRUE), "^d_access__")
  d |>
    group_split(dataset, crop) |>
    map_dfr(function(dd) {
      ds <- dd$dataset[[1]]
      cr <- dd$crop[[1]]
      map_dfr(ys[vapply(ys, \(y) any(!is.na(dd[[y]])), logical(1))], function(y) {
        map_dfr(specs, function(sp) {
          x <- paste0("d_access__", sp)
          base <- list(dataset = ds, outcome = str_remove(y, "^d_"), crop = cr, spec = sp,
                       estimator = "longdiff", control = "all")
          safely_run(\() ld_estimate(dd |> filter(!is.na(.data[[y]]), !is.na(.data[[x]])), y, x, base),
                     base)
        })
      })
    })
}

# --- Gate C ----------------------------------------------------------------------------------------
gate_c <- function(est) {
  prim <- est |> filter(spec == cfg$primary_spec)
  keys <- prim |> distinct(dataset, outcome, crop)
  pmap_dfr(keys, function(dataset, outcome, crop) {
    sel <- \(e, ctrl, sp = cfg$primary_spec, tm = "overall") {
      est |>
        filter(.data$dataset == !!dataset, .data$outcome == !!outcome,
               (is.na(.data$crop) & is.na(!!crop)) | (.data$crop %in% !!crop),
               .data$spec == sp, .data$estimator == e, .data$control == ctrl, .data$term == tm)
    }
    main <- sel("cs", "notyettreated")
    eff <- if (nrow(main)) main$estimate[[1]] else NA_real_
    pre_p <- sel("cs", "notyettreated", tm = "pretest_wald")$p
    pre <- est |>
      filter(.data$dataset == !!dataset, .data$outcome == !!outcome,
             (is.na(.data$crop) & is.na(!!crop)) | (.data$crop %in% !!crop),
             .data$spec == cfg$primary_spec, .data$estimator == "cs", .data$control == "notyettreated",
             str_detect(.data$term, "^e-\\d+$"), .data$term != "e-1")
    c1 <- length(pre_p) == 1 && isTRUE(pre_p > cfg$gate_pre_p) &&
      all(abs(pre$estimate) < cfg$gate_pre_ratio * abs(eff), na.rm = TRUE)
    plc <- sel("cs_placebo_burst", "nevertreated")
    c2 <- if (nrow(plc) && is.finite(plc$estimate[[1]])) {
      isTRUE(plc$p[[1]] > cfg$gate_placebo_p) && abs(plc$estimate[[1]]) < cfg$gate_placebo_ratio * abs(eff)
    } else {
      NA
    }
    ctrls <- bind_rows(sel("cs", "notyettreated"), sel("cs", "nevertreated"), sel("cs", "matched"),
                       sel("cs", "bands")) |>
      filter(is.finite(estimate))
    # the other treatment version of the primary layer (road-only <-> total)
    other_version <- if (str_starts(cfg$primary_spec, "roadonly_")) {
      str_replace(cfg$primary_spec, "^roadonly_", "total_")
    } else {
      str_replace(cfg$primary_spec, "^total_", "roadonly_")
    }
    alt <- sel("cs", "notyettreated", sp = other_version)
    c3 <- sum(sign(ctrls$estimate) == sign(eff)) >= 2 &&
      (nrow(alt) == 0 || isTRUE(sign(alt$estimate[[1]]) == sign(eff)))
    ld <- est |>
      filter(.data$estimator == "longdiff", .data$outcome == !!outcome,
             (is.na(.data$crop) & is.na(!!crop)) | (.data$crop %in% !!crop),
             .data$spec == cfg$primary_spec, .data$dataset == !!dataset)
    c4 <- if (nrow(ld) && is.finite(ld$estimate[[1]])) isTRUE(sign(ld$estimate[[1]]) == sign(eff)) else NA
    tibble(dataset = dataset, outcome = outcome, crop = crop, effect = eff,
           p = if (nrow(main)) main$p[[1]] else NA_real_,
           c1_pretrends = c1, c2_placebo = c2, c3_controls_versions = c3, c4_longdiff = c4) |>
      mutate(causal = isTRUE(c1) & isTRUE(c2) & isTRUE(c3) & isTRUE(c4),
             label = if_else(causal, "causal (Gate C passed)", "association"))
  }) |>
    mutate(q_bh = stats::p.adjust(p, method = "BH"),
           significant_bh = q_bh <= cfg$bh_q)
}

# --- composite label (revision 2): yield and vigour results move with the crop mix -------------------
composite_label <- function(gc_tab, est) {
  if (!nrow(gc_tab)) return(gc_tab)
  mix <- est |>
    filter(str_starts(dataset, "E2e_"), spec == cfg$primary_spec, estimator == "cs",
           control == "notyettreated", term == "overall", str_starts(outcome, "share_"),
           outcome != "share_sold", is.finite(p)) |>
    mutate(q = stats::p.adjust(p, method = "BH"),
           shift = q <= cfg$bh_q & abs(estimate) >= cfg$composite_shift)
  shift_admin <- any(mix$shift[mix$dataset == "E2e_admin"])
  shift_ea <- any(mix$shift[mix$dataset == "E2e_ea"])
  gc_tab |>
    mutate(crop_mix_shift = case_when(
      dataset %in% c("E2a_admin", "E2d_vigour") ~ shift_admin | (dataset == "E2d_vigour" & shift_ea),
      dataset == "E2b_ea" ~ shift_ea,
      TRUE ~ FALSE
    ),
    label = if_else(crop_mix_shift & dataset %in% c("E2a_admin", "E2b_ea", "E2d_vigour"),
                    paste0(label, "; composite (yield + crop mix)"), label))
}

# --- Gate V (revision 2): may the vigour outcome be interpreted? -------------------------------------
gate_v <- function(est, inputs_file) {
  inp <- if (file.exists(inputs_file)) read_csv(inputs_file, show_col_types = FALSE) else tibble()
  sel <- \(ds, out) est |>
    filter(dataset == ds, outcome == out, spec == cfg$primary_spec, estimator == "cs",
           control == "notyettreated", term == "overall")
  main <- sel("E2d_vigour", "ndvi_integral")
  if (!nrow(main) || !is.finite(main$estimate[[1]])) {
    return(tibble(criterion = "all", pass = NA, detail = "no E2d estimate"))
  }
  eff <- main$estimate[[1]]
  c1 <- if (nrow(inp) && "r_within" %in% names(inp)) {
    ok <- inp |> filter(!is.na(r_within), n >= cfg$gate_v_min_n)
    tibble(criterion = "1 anomaly correlation", pass = if (nrow(ok)) all(ok$r_within >= cfg$gate_v_r) else NA,
           detail = paste0(nrow(ok), " zones; min r ", round(min(ok$r_within, Inf), 3)))
  } else {
    tibble(criterion = "1 anomaly correlation", pass = NA, detail = "gate_v_inputs.csv missing")
  }
  yld <- bind_rows(sel("E2a_admin", "log_yield"), sel("E2b_ea", "log_yield")) |> filter(is.finite(estimate))
  c2 <- tibble(criterion = "2 sign agreement with survey yields",
               pass = if (nrow(yld)) all(sign(yld$estimate) == sign(eff)) else NA,
               detail = paste0(nrow(yld), " yield estimates"))
  plc <- bind_rows(sel("E2d_vigour", "ndvi_dry_integral"), sel("E2d_vigour", "ndvi_noncrop_integral"))
  c3 <- tibble(criterion = "3 placebos (dry season, non-cropland)",
               pass = if (nrow(plc)) all(plc$p > 0.05 & abs(plc$estimate) < 0.5 * abs(eff), na.rm = TRUE) else NA,
               detail = paste0(nrow(plc), " placebo estimates"))
  idx <- bind_rows(sel("E2d_vigour", "kndvi_integral"), sel("E2d_vigour", "evi_integral"),
                   sel("E2d_vigour", "ndvi_peak")) |> filter(is.finite(estimate))
  rs <- if (nrow(inp) && "r_sensor" %in% names(inp)) inp$r_sensor[!is.na(inp$r_sensor)] else numeric()
  sens <- if (length(rs)) all(rs >= cfg$gate_v_r_sensor) else NA    # no second sensor: not assessed
  c4 <- tibble(criterion = "4 index and sensor robustness",
               pass = (if (nrow(idx)) all(sign(idx$estimate) == sign(eff)) else NA) & sens,
               detail = paste0(nrow(idx), " alternative indices; sensor r check ", sens))
  out <- bind_rows(c1, c2, c3, c4)
  bind_rows(out, tibble(criterion = "Gate V", pass = all(out$pass %in% TRUE),
                        detail = "E2d interpreted only if every criterion passes"))
}

# --- main ------------------------------------------------------------------------------------------
log_msg("estimate_effects.R: panels ", panels_dir, " -> ", out_dir)
e1 <- read_panel("e1_cells")
e2a <- read_panel("e2a_admin")
e2b <- read_panel("e2b_ea")
e3 <- read_panel("e3_longdiff")

e1c <- read_panel("e1c_replacement")
e2d <- read_panel("e2d_vigour")
e2e_admin <- read_panel("e2e_admin")
e2e_ea <- read_panel("e2e_ea")
share_outcomes <- c("share_maize", "share_cassava", "share_rice", "share_sorghum_millet", "share_cash",
                    "share_staples_other", "shannon")
est <- bind_rows(
  run_dataset(e1, "E1_cells", c("conv_share", "conv_annual_share", "conv_tree_share", "newcrop_share",
                                "loss_share")),
  run_dataset(e1c, "E1c_replacement", c("repl_annual", "repl_tree", "repl_pasture", "repl_regrowth",
                                        "repl_other")),
  run_dataset(e2a, "E2a_admin", c("log_yield"), by_crop = TRUE),
  run_dataset(e2b, "E2b_ea", c("log_yield", "log_value_ha"), by_crop = TRUE),
  run_dataset(e2d, "E2d_vigour", c("ndvi_integral", "ndvi_peak", "kndvi_integral", "evi_integral",
                                   "ndvi_dry_integral", "ndvi_noncrop_integral")),
  run_dataset(e2e_admin, "E2e_admin", share_outcomes),
  run_dataset(e2e_ea, "E2e_ea", c(share_outcomes, "share_sold")),
  run_longdiff(e3)
)
write_csv(est, file.path(out_dir, "estimates.csv"), na = "")
gc_tab <- if (nrow(est)) gate_c(est |> filter(estimator != "longdiff" | TRUE)) else tibble()
gc_tab <- composite_label(gc_tab, est)
gv_tab <- gate_v(est, file.path(panels_dir, "gate_v_inputs.csv"))
write_csv(gv_tab, file.path(out_dir, "gate_v.csv"), na = "")
write_csv(gc_tab, file.path(out_dir, "gate_c.csv"), na = "")
writeLines(capture.output(sessionInfo()), file.path(out_dir, "sessionInfo.txt"))
log_msg("estimates: ", nrow(est), " rows; Gate C: ", nrow(gc_tab), " rows")
