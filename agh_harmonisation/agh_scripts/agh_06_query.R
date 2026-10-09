# =============================================================================
# agh_06_query.R — subset the curated tables AFTER extraction and curation
#
# source() this file, then e.g.
#   agh_tables()                                   # what exists, rows per source
#   agh_get("plot", country = c("Malawi", "Ethiopia"), cols = c("plot_area_m2", "OM_kg_ha"))
#   agh_get("plot_crop", crop = "maize", year_from = 2010, complete = TRUE)
#   agh_get("plot", add_hh = c("TLU", "hh_size", "latitude", "longitude"))
#   agh_coverage("plot")                           # share of non-missing values, per source
# Nothing here changes files; re-run step 5 to change curation rules.
# =============================================================================

source(file.path(getOption("agh.scripts", "."), "agh_utils.R"))

agh_tables <- function() {
  ff <- list.files(agh_path("agh_curated"), pattern = "^agh_(hh|plot|plot_crop|plot_input|hh_animal)\\.rds$", full.names = TRUE)
  map(ff, \(f) { t <- readRDS(f)
    t |> count(source_id, program, country, year, name = "rows") |> mutate(table = str_remove_all(basename(f), "^agh_|\\.rds$"), .before = 1)
  }) |> list_rbind()
}

agh_load <- function(level) readRDS(agh_path("agh_curated", paste0("agh_", level, ".rds")))

#' @param level      hh | plot | plot_crop | plot_input | hh_animal
#' @param cols       columns to keep (keys and source columns are always kept)
#' @param complete   drop rows with any NA in `cols`
#' @param add_hh     household columns joined onto a plot-type table
#' @param ...        extra filters on any column, as name = allowed values (e.g. crop = "maize")
agh_get <- function(level, cols = NULL, country = NULL, program = NULL, source_id = NULL,
                    year_from = NULL, year_to = NULL, complete = FALSE, add_hh = NULL, ...) {
  t <- agh_load(level)
  yr <- num(str_extract(t$year, "\\d{4}"))
  keep <- rep(TRUE, nrow(t))
  if (!is.null(country))   keep <- keep & t$country %in% country
  if (!is.null(program))   keep <- keep & t$program %in% program
  if (!is.null(source_id)) keep <- keep & t$source_id %in% source_id
  if (!is.null(year_from)) keep <- keep & yr >= year_from
  if (!is.null(year_to))   keep <- keep & yr <= year_to
  t <- t[keep %in% TRUE, ]
  for (f in names(list(...))) t <- t[t[[f]] %in% list(...)[[f]], ]
  if (!is.null(add_hh)) {
    hh <- agh_load("hh") |> select(source_id, hhid, any_of(add_hh))
    t <- t |> left_join(hh, by = c("source_id", "hhid"))
    cols <- c(cols, add_hh)
  }
  if (!is.null(cols)) {
    id <- intersect(c("source_id", "program", "country", "year", "hhid", "parcel_id", "plot_id", "season",
                      "crop", "animal", "animal_class", "input_type", "input"), names(t))
    miss <- setdiff(cols, names(t))
    if (length(miss) > 0) warning("Not in ", level, ": ", paste(miss, collapse = ", "))
    t <- t |> select(all_of(id), any_of(cols))
    if (complete) t <- t |> filter(if_all(any_of(cols), \(x) !is.na(x)))
  }
  t
}

agh_coverage <- function(level) {
  agh_load(level) |>
    summarise(across(!any_of(c("program", "country", "year", "hhid", "parcel_id", "plot_id")),
                     \(x) round(mean(!is.na(x)), 2)), rows = n(), .by = source_id) |>
    relocate(rows, .after = source_id)
}
