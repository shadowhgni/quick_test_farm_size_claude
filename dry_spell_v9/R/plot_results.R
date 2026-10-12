#!/usr/bin/env Rscript
# =============================================================================
# plot_results.R - R back-up of the step 5 figures (v9_05_spell_stats.py)
# =============================================================================
#
# Redraws, from the files step 5 writes (no Python needed):
#   * one map per GeoTIFF in <dir>/cog/ (per-cell medians, P(>= 1 spell), ...)  -> map_<layer>.png
#   * the probability density functions by zone and by latitude band, from hist_by_zone.csv and
#     hist_by_latitude.csv (season-level 1-day histograms - the PDFs cannot be rebuilt from the
#     per-cell rasters, which only hold medians)                                  -> pdf_<metric>.png
#   * the latitude profile from summary_by_latitude.csv                          -> latitude_profile.png
# Optionally (--tif_dir) a map of every GeoTIFF of another folder, e.g. step03/diagnostics.
# The Python figures are not touched; these go to <dir>/png_R/ (or --out).
#
# Usage (from the working folder of run_all.py):
#   Rscript R/plot_results.R --dir dryspell_v9/ssa/base/step05/ssa \
#       --boundaries dryspell_v9_data/boundaries/ne_50m_admin_0_countries.gpkg
#   Rscript R/plot_results.R --dir dryspell_v9/ssa/base/step05/SEN --tif_dir dryspell_v9/ssa/base/step03/diagnostics
#
# Options: --out DIR, --pdf_lat_band 2 (degrees per PDF curve), --smooth 3 (Gaussian sd, days; 0 = raw),
#          --font sans (e.g. Avenir when installed), --dpi 170
# Packages: ggplot2 dplyr tidyr readr purrr stringr (tidyverse core), terra, sf (boundaries only).
# Colours: CIMMYT / CGIAR branding (CLAUDE.md at the repository root).
# =============================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(tidyr)
  library(readr)
  library(purrr)
  library(stringr)
})

# ---- arguments -------------------------------------------------------------------------------
args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(name, default = NULL) {
  i <- match(paste0("--", name), args)
  if (is.na(i) || i == length(args)) default else args[i + 1]
}
dir_in <- get_arg("dir")
if (is.null(dir_in) || !dir.exists(dir_in)) {
  stop("--dir <step05 output folder> is required, e.g. dryspell_v9/ssa/base/step05/ssa", call. = FALSE)
}
dir_out <- get_arg("out", file.path(dir_in, "png_R"))
bnd_file <- get_arg("boundaries")
tif_dir <- get_arg("tif_dir")
pdf_band <- as.numeric(get_arg("pdf_lat_band", "2"))
smooth_days <- as.numeric(get_arg("smooth", "3"))
font <- get_arg("font", "sans")
dpi <- as.numeric(get_arg("dpi", "170"))
dir.create(dir_out, showWarnings = FALSE, recursive = TRUE)

# ---- brand style -----------------------------------------------------------------------------
brand <- c(green = "#77bd42", yellow = "#ffbf50", brown = "#704b0f", light_blue = "#8ec1cb",
           teal = "#326670", grey = "#54565b", olive = "#dddaa4", orange = "#f29657", sage = "#acb7ac",
           taupe = "#b6a9a3")
series <- unname(brand[c("teal", "orange", "brown", "green")])   # fixed order, colour-blind checked
ink <- brand[["grey"]]
grid_col <- "#e4e5e3"
ramps <- list(
  brand_teal = c("#f1f7f8", brand[["light_blue"]], brand[["teal"]], "#1b3a40"),
  brand_risk = c("#fff6e4", brand[["yellow"]], brand[["orange"]], brand[["brown"]]),
  brand_green = c("#f2f8ec", brand[["green"]], "#3f6e1f")
)
teal_ordinal <- c("#8ec1cb", "#6fa7b2", "#548f9b", "#3f7984", "#326670", "#28545c", "#1d4249")

theme_brand <- function() {
  theme_minimal(base_size = 9, base_family = font) +
    theme(text = element_text(colour = ink), axis.text = element_text(colour = "#7d7f84"),
          panel.grid = element_line(colour = grid_col, linewidth = 0.3),
          plot.title = element_text(hjust = 0, size = 10), plot.title.position = "plot",
          legend.key.height = unit(0.5, "cm"), plot.background = element_rect(fill = "white", colour = NA))
}

# ---- what each layer / metric is (same as v9_05_spell_stats.py) ------------------------------
maps <- tribble(
  ~layer, ~title, ~unit, ~ramp, ~vmin, ~vmax,
  "n_spells_median", "Median number of dry spells per season", "spells / season", "brand_risk", 0, NA,
  "n_spells_mean", "Mean number of dry spells per season", "spells / season", "brand_risk", 0, NA,
  "p_ge1", "P(at least one dry spell in the season)", "probability", "brand_teal", 0, 1,
  "p_ge2", "P(two or more dry spells in the season)", "probability", "brand_teal", 0, 1,
  "spell_len_median", "Median duration of the dry spells of a season", "days", "brand_risk", NA, NA,
  "first_start_median", "Median start of the 1st dry spell", "days after onset", "brand_teal", 0, NA,
  "first_len_median", "Median duration of the 1st dry spell", "days", "brand_risk", NA, NA,
  "last_start_median", "Median start of the last dry spell (seasons with >= 2)", "days after onset", "brand_teal", 0, NA,
  "last_len_median", "Median duration of the last dry spell (seasons with >= 2)", "days", "brand_risk", NA, NA,
  "longest_start_median", "Median start of the longest dry spell", "days after onset", "brand_teal", 0, NA,
  "longest_len_median", "Median duration of the longest dry spell", "days", "brand_risk", NA, NA,
  "dry_frac_median", "Median share of the season in dry spells", "fraction", "brand_risk", 0, NA
)
metrics <- tribble(
  ~metric, ~label, ~unit, ~width,
  "n_spells", "Number of dry spells per season", "spells", 1,
  "spell_len", "Median duration of the dry spells of the season", "days", 0.5,
  "first_start", "Start of the 1st dry spell", "days after onset", 1,
  "first_len", "Duration of the 1st dry spell", "days", 1,
  "last_start", "Start of the last dry spell (seasons with >= 2)", "days after onset", 1,
  "last_len", "Duration of the last dry spell (seasons with >= 2)", "days", 1,
  "longest_start", "Start of the longest dry spell", "days after onset", 1,
  "longest_len", "Duration of the longest dry spell", "days", 1,
  "dry_frac", "Share of the season in dry spells", "fraction", 0.01
)

bnd <- NULL
if (!is.null(bnd_file) && file.exists(bnd_file)) {
  bnd <- sf::st_read(bnd_file, quiet = TRUE)
}

# ---- maps from GeoTIFFs ----------------------------------------------------------------------
plot_tif <- function(f, title, unit, ramp, vmin = NA, vmax = NA, out_png) {
  r <- terra::rast(f)
  df <- terra::as.data.frame(r, xy = TRUE, na.rm = FALSE)     # full grid: regular spacing for geom_raster
  names(df)[3] <- "value"
  df <- df |> mutate(x = round(x, 5), y = round(y, 5))     # exact cell centres for geom_raster
  n_valid <- sum(is.finite(df$value))
  if (n_valid == 0) return(invisible(NULL))
  ex <- as.vector(terra::ext(r))
  p <- ggplot(df, aes(x, y, fill = value)) +
    geom_raster() +
    scale_fill_gradientn(colours = ramps[[ramp]], limits = c(vmin, vmax), oob = scales::squish, name = unit,
                         na.value = "transparent") +
    labs(title = title, x = "longitude", y = "latitude",
         caption = sprintf("valid pixels: %s", formatC(n_valid, big.mark = ",", format = "d"))) +
    theme_brand()
  if (!is.null(bnd)) {
    p <- p + geom_sf(data = bnd, fill = NA, colour = ink, linewidth = 0.2, inherit.aes = FALSE)
  }
  p <- p + coord_sf(xlim = ex[c("xmin", "xmax")], ylim = ex[c("ymin", "ymax")], expand = FALSE)
  asp <- (ex[["ymax"]] - ex[["ymin"]]) / (ex[["xmax"]] - ex[["xmin"]])
  ggsave(out_png, p, width = 9, height = max(3.5, 9 * asp + 1), dpi = dpi, bg = "white")
}

cog <- file.path(dir_in, "cog")
if (dir.exists(cog)) {
  for (i in seq_len(nrow(maps))) {
    f <- file.path(cog, paste0(maps$layer[i], ".tif"))
    if (file.exists(f)) {
      plot_tif(f, maps$title[i], maps$unit[i], maps$ramp[i], maps$vmin[i], maps$vmax[i],
               file.path(dir_out, paste0("map_", maps$layer[i], ".png")))
    }
  }
  message("maps written from ", cog)
}
if (!is.null(tif_dir) && dir.exists(tif_dir)) {
  for (f in list.files(tif_dir, pattern = "\\.tif$", full.names = TRUE)) {
    nm <- tools::file_path_sans_ext(basename(f))
    plot_tif(f, str_replace_all(nm, "_", " "), "", "brand_risk", out_png = file.path(dir_out, paste0("map_", nm, ".png")))
  }
  message("maps written from ", tif_dir)
}

# ---- PDFs from the histograms ----------------------------------------------------------------
gauss_smooth <- function(x, sigma) {
  if (sigma <= 0) return(x)
  h <- ceiling(4 * sigma)
  k <- dnorm(-h:h, sd = sigma)
  k <- k / sum(k)
  y <- stats::filter(c(rep(0, h), x, rep(0, h)), k, sides = 2)
  as.numeric(y[(h + 1):(h + length(x))])
}

density_curve <- function(h, metric) {
  # h: tibble(value, count) for one series -> tibble(value, density)
  w <- metrics$width[metrics$metric == metric]
  unit <- metrics$unit[metrics$metric == metric]
  bins <- tibble(value = round(seq(0, max(h$value), by = w), 4))
  d <- bins |>
    left_join(h |> mutate(value = round(value, 4)), by = "value") |>
    mutate(count = replace_na(count, 0))
  dens <- d$count / (sum(d$count) * w)
  if (metric != "n_spells" && smooth_days > 0) {
    dens <- gauss_smooth(dens, if (str_detect(unit, "day")) smooth_days / w else 2)
  }
  tibble(value = d$value, density = dens)
}

two_panels <- function(p1, p2, file, width = 10.5, height = 3.8) {
  png(file, width = width, height = height, units = "in", res = dpi, bg = "white")
  grid::grid.newpage()
  grid::pushViewport(grid::viewport(layout = grid::grid.layout(1, 2)))
  print(p1, vp = grid::viewport(layout.pos.row = 1, layout.pos.col = 1))
  print(p2, vp = grid::viewport(layout.pos.row = 1, layout.pos.col = 2))
  invisible(dev.off())
}

hz_file <- file.path(dir_in, "hist_by_zone.csv")
hl_file <- file.path(dir_in, "hist_by_latitude.csv")
sz_file <- file.path(dir_in, "summary_by_zone.csv")
if (file.exists(hz_file) && file.exists(hl_file) && file.exists(sz_file)) {
  hz <- read_csv(hz_file, show_col_types = FALSE)
  hl <- read_csv(hl_file, show_col_types = FALSE)
  sz <- read_csv(sz_file, show_col_types = FALSE)
  # the 4 largest zones get the brand series colours; the rest are grouped as "other zones"
  zsize <- sz |>
    filter(metric == "n_spells", zone != "ALL") |>
    arrange(desc(n_seasons))
  top <- head(zsize$zone, length(series))
  zone_cols <- c(setNames(series[seq_along(top)], top), "other zones" = brand[["sage"]], "ALL" = ink)
  # latitude bands of the PDFs: pdf_band degrees
  hl <- hl |>
    mutate(lat_lo = as.numeric(str_extract(latitude_band, "^-?[0-9.]+")),
           band = floor(lat_lo / pdf_band) * pdf_band,
           band_label = sprintf("%g to %g N", band, band + pdf_band))
  bands <- sort(unique(hl$band))
  band_labels <- sprintf("%g to %g N", bands, bands + pdf_band)
  band_cols <- setNames(teal_ordinal[round(seq(1, length(teal_ordinal), length.out = length(bands)))], band_labels)

  for (m in metrics$metric) {
    mrow <- metrics[metrics$metric == m, ]
    hzm <- hz |> filter(metric == m)
    if (nrow(hzm) == 0) next
    zser <- bind_rows(
      hzm |> filter(zone %in% top) |> mutate(series = zone),
      hzm |> filter(!zone %in% top) |> mutate(series = "other zones"),
      hzm |> mutate(series = "ALL")
    ) |>
      group_by(series, value) |>
      summarise(count = sum(count), .groups = "drop")
    lser <- hl |>
      filter(metric == m) |>
      group_by(series = band_label, value) |>
      summarise(count = sum(count), .groups = "drop")
    curves <- function(s) {
      s |>
        group_by(series) |>
        group_modify(~ density_curve(.x, m) |> mutate(n = sum(.x$count))) |>
        ungroup() |>
        mutate(legend = sprintf("%s (n=%s)", series, formatC(n, big.mark = ",", format = "d")))
    }
    cz <- curves(zser)
    cl <- curves(lser)
    tot <- zser |> filter(series == "ALL") |> arrange(value) |> mutate(cum = cumsum(count) / sum(count))
    xmax <- max(tot$value[which(tot$cum >= 0.995)[1]] * 1.05, mrow$width * 3)
    lab_z <- cz |> distinct(series, legend)
    lab_l <- cl |> distinct(series, legend)
    zlev <- intersect(c(top, "other zones", "ALL"), unique(cz$series))
    geom_fun <- if (m == "n_spells") geom_step else geom_line
    p1 <- ggplot(cz, aes(value, density, colour = factor(series, levels = zlev),
                         linewidth = series == "ALL")) +
      geom_fun() +
      scale_colour_manual(values = zone_cols, labels = setNames(lab_z$legend, lab_z$series), name = NULL) +
      scale_linewidth_manual(values = c(`FALSE` = 0.7, `TRUE` = 1.0), guide = "none") +
      coord_cartesian(xlim = c(0, xmax)) +
      labs(title = "by zone", x = mrow$unit,
           y = sprintf("probability density (per %s)", if (m == "n_spells") "spell" else word(mrow$unit, 1))) +
      theme_brand() + theme(legend.position = c(0.98, 0.98), legend.justification = c(1, 1))
    p2 <- ggplot(cl, aes(value, density, colour = factor(series, levels = band_labels))) +
      geom_fun(linewidth = 0.7) +
      scale_colour_manual(values = band_cols, labels = setNames(lab_l$legend, lab_l$series), name = NULL) +
      coord_cartesian(xlim = c(0, xmax)) +
      labs(title = "by latitude band", x = mrow$unit, y = NULL) +
      theme_brand() + theme(legend.position = c(0.98, 0.98), legend.justification = c(1, 1))
    p1 <- p1 + labs(subtitle = mrow$label)
    two_panels(p1, p2, file.path(dir_out, paste0("pdf_", m, ".png")))
  }
  message("PDFs written from ", hz_file, " and ", hl_file)
}

# ---- latitude profile ------------------------------------------------------------------------
sl_file <- file.path(dir_in, "summary_by_latitude.csv")
if (file.exists(sl_file)) {
  order_m <- c("n_spells", "longest_start", "first_start", "last_start",   # top: how many, and when
               "spell_len", "longest_len", "first_len", "last_len")        # bottom: how long
  sl <- read_csv(sl_file, show_col_types = FALSE) |>
    filter(latitude_band != "ALL", metric %in% order_m) |>
    mutate(lat_lo = as.numeric(str_extract(latitude_band, "^-?[0-9.]+")))
  step <- min(diff(sort(unique(sl$lat_lo))), na.rm = TRUE)
  sl <- sl |>
    mutate(lat = lat_lo + ifelse(is.finite(step), step / 2, 0.5),
           panel = factor(sprintf("%s (%s)", label, metric_unit),
                          levels = map_chr(order_m, ~ {
                            r <- sl[sl$metric == .x, ][1, ]
                            sprintf("%s (%s)", r$label, r$metric_unit)
                          })))
  means <- sl |> filter(metric == "n_spells")
  p <- ggplot(sl, aes(lat)) +
    geom_ribbon(aes(ymin = p25, ymax = p75, fill = "interquartile range"), alpha = 0.45) +
    geom_line(aes(y = median, colour = "median"), linewidth = 0.8) +
    geom_point(aes(y = median, colour = "median"), size = 1.1) +
    geom_line(data = means, aes(y = mean, colour = "mean"), linewidth = 0.8) +
    geom_point(data = means, aes(y = mean, colour = "mean"), size = 1.1) +
    facet_wrap(~panel, nrow = 2, scales = "free_y", labeller = label_wrap_gen(32)) +
    scale_fill_manual(values = c("interquartile range" = brand[["light_blue"]]), name = NULL) +
    scale_colour_manual(values = c(median = brand[["teal"]], mean = brand[["orange"]]), name = NULL) +
    labs(title = "Dry spells in the rainy season by latitude", x = "latitude (band centre, deg N)", y = NULL) +
    theme_brand() + theme(legend.position = "bottom", strip.text = element_text(colour = ink, hjust = 0))
  ggsave(file.path(dir_out, "latitude_profile.png"), p, width = 12, height = 6.6, dpi = dpi, bg = "white")
  message("latitude profile written from ", sl_file)
}
message("R figures in ", dir_out)
