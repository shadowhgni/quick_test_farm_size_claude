# =============================================================================
# agh_units_import.R — propose unit_map rows from a published conversion table
#
# Run AFTER step 5 (it reads which units still have no factor), then re-run step 5.
#   source("agh_units_import.R")
#   agh_import_units("C:/data/lsms/ihs_seasonalcropconversion_factor_2020.dta",
#                    sources = "MWI_IHS2_2004", concept = "harvest_qty",
#                    region_map = c(central = "centre"),
#                    basis = "IHS5 seasonal-crop factors (collected 2016/2019)")
#
# Reads   agh_curated/agh_long.rds (units without a factor), agh_config/unit_map.csv,
#         the conversion table (.dta / .csv / .xlsx; Stata labels are used as text)
# Writes  agh_config/unit_map.csv  ✋ proposed item (+ region) rows: checked blank,
#                                     basis says where each factor comes from
#         agh_meta/unit_import_report.csv   every (item, unit) needing a factor and
#                                           why it got one or not
#
# Matching (rules, not guesses: anything ambiguous is left blank and reported)
#   item   all words of the std item are words of the table item ("local maize" =
#          "MAIZE LOCAL"; "groundnut" = the GROUNDNUT varieties). Exact word sets win;
#          several varieties -> their median, noted in basis.
#   unit   same words, spaces ignored ("pail large" = "PAIL (LARGE)", "oxcart" =
#          "OX-CART"); "shelled" / "unshelled" in the label is the condition.
#   condition  label condition, else rows "not applicable", else condition_default
#          if given; a label without condition against shelled AND unshelled rows
#          is ambiguous and left blank.
#   region factors are kept per region; region_map renames table regions to the
#          household adm1 std values (e.g. table "Central" = IHS2 "Centre").
# Assumption written in basis: a table collected in one survey round is applied to
# other rounds of the same country when they did not record their own factors.
# =============================================================================

source(file.path(getOption("agh.scripts", "."), "agh_utils.R"))

agh_import_units <- function(file, sources, concept = "harvest_qty",
                             item_col = "crop_code", unit_col = "unit_name", factor_col = "conversion",
                             region_col = "region", condition_col = "condition",
                             region_map = NULL, condition_default = NULL, basis = basename(file)) {
  words <- \(x) normalise(x) |> str_remove_all("\\b(other|specify)\\b") |> str_squish() |>
    str_split(" ") |> map(\(w) unique(str_remove(w[w != ""], "(?<=[a-z]{3})s$")))
  squash <- \(x) normalise(x) |> str_remove_all(" ")
  cond_of <- \(x) case_when(str_detect(x, "\\bunshelled\\b") ~ "unshelled", str_detect(x, "\\bshelled\\b") ~ "shelled")

  ext <- str_to_lower(str_extract(file, "[^.]+$"))
  tab <- switch(ext,
    dta = haven::read_dta(file) |> mutate(across(where(haven::is.labelled), \(x) as.character(haven::as_factor(x)))),
    xlsx = , xls = readxl::read_excel(file),
    read_csv(file, show_col_types = FALSE))
  miss <- setdiff(c(item_col, unit_col, factor_col), names(tab))
  if (length(miss) > 0) stop("Not in ", basename(file), ": ", paste(miss, collapse = ", "))
  tab <- tab |>
    transmute(t_item = as.character(.data[[item_col]]),
              t_unit = as.character(.data[[unit_col]]),
              factor = as.numeric(.data[[factor_col]]),
              region = if (!is.null(region_col) && region_col %in% names(tab)) normalise(as.character(.data[[region_col]])) else NA_character_,
              cond   = if (!is.null(condition_col) && condition_col %in% names(tab)) cond_of(normalise(as.character(.data[[condition_col]]))) else NA_character_) |>
    filter(!is.na(factor), factor > 0) |>
    mutate(region = coalesce(unname(region_map[region]), region),
           t_words = words(t_item), t_unit_sq = squash(t_unit))

  # (item, unit) pairs that still have no factor, with their households' regions
  need <- readRDS(agh_path("agh_curated", "agh_long.rds")) |>
    filter(source_id %in% sources, concept == !!concept, unit_status %in% "unknown_unit") |>
    filter(!is.na(item_std)) |>
    count(source_id, item = item_std, unit, name = "n") |>
    mutate(cond = cond_of(unit), unit_base = str_squish(str_remove_all(unit, "\\b(un)?shelled\\b")))

  res <- pmap(need, \(source_id, item, unit, n, cond, unit_base) {
    out <- \(reason, rows = NULL, note = "") tibble(source_id, concept, item, unit, n, reason,
      region = rows$region %||% NA_character_, factor = rows$factor %||% NA_real_, note)
    iw <- words(item)[[1]]
    hit_item <- map_lgl(tab$t_words, \(tw) length(iw) > 0 && all(iw %in% tw))
    if (!any(hit_item)) return(out("item not in table"))
    exact <- hit_item & map_lgl(tab$t_words, \(tw) setequal(iw, tw))
    t <- tab[if (any(exact)) exact else hit_item, ] |> filter(t_unit_sq == squash(unit_base))
    if (nrow(t) == 0) return(out("unit not in table for this item"))
    c_used <- cond
    if (!is.na(cond)) t <- if (any(t$cond %in% c_used)) t |> filter(cond %in% c_used) else t |> filter(is.na(cond))
    else if (any(is.na(t$cond))) t <- t |> filter(is.na(cond))
    else if (!is.null(condition_default)) { c_used <- condition_default; t <- t |> filter(cond == c_used) }
    else return(out("condition not recorded; table has shelled and unshelled"))
    if (nrow(t) == 0) return(out(paste("no", cond, "row for this item and unit")))
    k <- n_distinct(t$t_item)
    rows <- t |> summarise(factor = median(factor), .by = region)
    out("matched", rows, paste0(if (k > 1) sprintf("median of %d varieties; ", k) else "",
                                if (!is.na(c_used)) paste0(c_used, if (is.na(cond)) " (condition_default)" else "", "; ") else ""))
  }) |> list_rbind()

  write_csv(res, agh_path("agh_meta", "unit_import_report.csv"), na = "")
  yrs <- read_cfg("sources.csv") |> select(source_id, year)
  new <- res |>
    filter(reason == "matched") |>
    left_join(yrs, by = "source_id") |>
    transmute(source_id, concept, item, region, unit, factor = as.character(signif(factor, 6)), target = "kg",
              checked = NA_character_, n = as.character(n),
              basis = paste0(basis, "; ", note, "applied to ", coalesce(year, "this source"),
                             " (assumption: factors of another round used where none were recorded)"))

  um_file <- agh_path("agh_config", "unit_map.csv")
  hdr <- readLines(um_file, n = 1)
  um <- read_cfg("unit_map.csv")
  for (c in c("region", "basis")) if (!c %in% names(um)) um[[c]] <- NA_character_
  new <- new |> anti_join(um, by = c("source_id", "concept", "item", "region", "unit"))
  um <- bind_rows(um |> relocate(region, .after = item), new) |> arrange(source_id, concept, unit, item, region)
  writeLines(hdr, um_file)
  write_csv(um, um_file, append = TRUE, col_names = TRUE, na = "")

  say("%s: %d of %d item-unit pairs matched (%d values); %d unit_map rows added (checked blank).",
      basename(file), n_distinct(paste(res$item, res$unit)[res$reason == "matched"]),
      nrow(need), sum(need$n[paste(need$item, need$unit) %in% paste(res$item, res$unit)[res$reason == "matched"]]), nrow(new))
  print(res |> distinct(item, unit, n, reason) |> count(reason, wt = n, name = "values"))
  invisible(res)
}
