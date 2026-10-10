rm(list = ls())
# =============================================================================
# agh_04_extract.R — read the curated variables from every dataset into ONE long table
#
# Reads   agh_config/sources.csv, agh_config/source_map.csv (keep = TRUE rows),
#         agh_config/concepts.csv, agh_meta/data_inventory.csv
# Writes  agh_extract/agh_long_raw.rds   one row per (record, concept): keys, item, raw value,
#                                        value label, raw unit, multiply
#         agh_extract/extract_log.csv    per file: rows read, variables found / missing
#
# Nothing is converted here (no units, no recoding): step 5 applies curation
# rules, so you can change them without re-reading the data.
#
# Record structure handled
#   - long files (one row per plot, plot-crop, animal ...): keys + values
#   - wide repeats (crop_1..n, livestock_heads_1..n): var_regex with one capture
#     group; columns sharing an index form one record (rep)
#   - side-by-side blocks (fertilizer type/qty/unit of application 1, 2): set rep
#     = 1, 2 ... in source_map; same-rep columns of a row form one record
#   - single-item columns ("number of cattle"): item_fixed = animal:cattle
# =============================================================================

source(file.path(getOption("agh.scripts", "."), "agh_utils.R"))

src <- read_cfg("sources.csv") |> filter(as_lgl(enabled) %in% TRUE | is.na(enabled))
concepts <- read_cfg("concepts.csv")
inventory <- read_csv(agh_path("agh_meta", "data_inventory.csv"), col_types = cols(.default = "c"),
                      show_col_types = FALSE)

smap <- read_cfg("source_map.csv") |>
  filter(as_lgl(keep) %in% TRUE, source_id %in% src$source_id) |>
  left_join(concepts |> select(concept, kind, level, c_unit_of = unit_of), by = "concept")

for (oc in c("var_regex", "rep", "unit_of", "item_fixed", "season_fixed", "multiply", "data_file")) {
  if (!oc %in% names(smap)) smap[[oc]] <- NA_character_
}
smap <- smap |> mutate(unit_of = coalesce(unit_of, c_unit_of), file_match = str_to_lower(coalesce(data_file, file)))

unknown <- smap |> filter(is.na(kind)) |> distinct(concept)
if (nrow(unknown) > 0) agh_halt("Concepts in source_map.csv not in concepts.csv (fix the concept, or add it to concepts.csv): ", paste(unknown$concept, collapse = ", "))
bad_role <- smap |> filter(!role %in% c("key", "item", "value", "unit"))
if (nrow(bad_role) > 0) agh_halt("In source_map.csv, role must be key|item|value|unit; check rows: ",
                             paste(bad_role$source_id, bad_role$var, collapse = "; "))
no_unit_of <- smap |> filter(role == "unit", is.na(unit_of))
if (nrow(no_unit_of) > 0) agh_halt("In source_map.csv, unit rows need unit_of (the concept they qualify): ", paste(no_unit_of$var, collapse = ", "))
if (nrow(smap) == 0) agh_halt("No keep = TRUE rows in source_map.csv for the enabled sources (",
                          paste(src$source_id, collapse = ", "), "). Tick keep = TRUE on the variables to extract ",
                          "(step 3 adds template rows for each newly registered dataset), then run again.")

key_concepts <- c("hhid", "parcel_id", "plot_id", "season")

# Item concept a value concept refers to: the item concept at the same level in
# concepts.csv; if several (OM_type, fertilizer_type), the one sharing the prefix
item_of <- function(value_concepts) {
  ic <- concepts |> filter(kind == "item")
  map_chr(value_concepts, \(v) {
    lv <- concepts$level[concepts$concept == v]
    cand <- ic$concept[ic$level == lv]
    if (length(cand) <= 1) return(cand[1] %||% NA_character_)
    m <- cand[word(cand, 1, sep = "_") == word(v, 1, sep = "_")]
    m[1] %||% NA_character_
  })
}

data_names <- function(container, member) {
  f <- if (is.na(member)) container else read_any_path(container, member)
  ext <- str_to_lower(str_extract(f, "[^.]+$"))
  switch(ext,
    dta = names(haven::read_dta(f, n_max = 0)),
    sav = names(haven::read_sav(f, n_max = 0)),
    xlsx = , xls = names(readxl::read_excel(f, n_max = 0)),
    rds = names(readRDS(f)),
    names(read_csv(f, n_max = 0, show_col_types = FALSE)))
}

extract_file <- function(sid, fmatch, m) {
  inv <- inventory |> filter(source_id == sid, str_to_lower(file) == fmatch)
  if (nrow(inv) == 0) return(list(log = tibble(source_id = sid, file = fmatch, status = "no_data_file")))
  if (nrow(inv) > 1) say("  %s/%s: %d data files share this name; using %s", sid, fmatch, nrow(inv),
                         coalesce(inv$member[1], inv$container[1]))
  inv <- inv[1, ]
  have <- data_names(inv$container, inv$member)

  # expand regex rows to actual columns, with rep index
  m <- m |>
    mutate(cols = pmap(list(var, var_regex, rep), \(v, rx, r) {
      if (is.na(rx)) tibble(col = v, rep = r)
      else { hits <- have[str_detect(have, rx)]
             tibble(col = hits, rep = str_match(hits, rx)[, 2]) }
    })) |>
    select(-rep) |>
    unnest(cols)
  missing <- m |> filter(!col %in% have)
  m <- m |> filter(col %in% have)
  if (nrow(m) == 0) return(list(log = tibble(source_id = sid, file = fmatch, status = "no_mapped_column",
                                             missing = paste(missing$col, collapse = ";"))))

  df <- read_any(inv$container, inv$member, cols = unique(m$col)) |> mutate(.row = row_number())
  lbl <- \(col) if (paste0(col, "__lbl") %in% names(df)) df[[paste0(col, "__lbl")]] else rep(NA_character_, nrow(df))

  # keys: several variables for one key are pasted (e.g. holder + household)
  keys <- tibble(.row = df$.row)
  for (k in key_concepts) {
    kc <- m |> filter(role == "key", concept == k, is.na(rep)) |> pull(col)
    keys[[k]] <- if (length(kc) == 0) NA_character_ else
      do.call(paste, c(map(kc, \(cc) coalesce(df[[cc]], "")), sep = "_"))
  }
  sfix <- m$season_fixed[!is.na(m$season_fixed)][1]
  if (!is.na(sfix)) keys$season <- coalesce(keys$season, sfix)

  # cells: one row per (row, column)
  cell <- \(rows) map(seq_len(nrow(rows)), \(i) {
    r <- rows[i, ]
    tibble(.row = df$.row, rep = r$rep, col = r$col, concept = r$concept,
           value_raw = df[[r$col]], value_lbl = lbl(r$col))
  }) |> list_rbind()

  items <- m |> filter(role == "item")
  vals  <- m |> filter(role == "value")
  units <- m |> filter(role == "unit")

  item_cells <- if (nrow(items) > 0) cell(items) |>
    transmute(.row, rep, item_type = concept, item_raw = coalesce(value_lbl, value_raw), item_col = col) |>
    distinct(.row, rep, item_type, .keep_all = TRUE) else
    tibble(.row = integer(), rep = character(), item_type = character(), item_raw = character(), item_col = character())
  unit_cells <- if (nrow(units) > 0) cell(units) |>
    left_join(units |> distinct(col, unit_of), by = "col") |>
    transmute(.row, rep, concept = unit_of, unit_raw = coalesce(value_lbl, value_raw)) |>
    distinct(.row, rep, concept, .keep_all = TRUE) else
    tibble(.row = integer(), rep = character(), concept = character(), unit_raw = character())

  if (nrow(vals) == 0 && nrow(items) == 0) return(list(log = tibble(source_id = sid, file = fmatch, status = "no_value_rows")))

  v <- if (nrow(vals) == 0) tibble(.row = integer(), rep = character(), col = character(), concept = character(),
                                   value_raw = character(), value_lbl = character(), item_fixed = character(),
                                   multiply = character(), item_type = character()) else cell(vals) |>
    left_join(vals |> distinct(col, concept, item_fixed, multiply), by = c("col", "concept")) |>
    filter(!is.na(value_raw), value_raw != "") |>
    mutate(item_type = item_of(concept))

  # attach items: fixed item first, else the item column(s) of the same row / rep
  # an item / unit column without rep applies to every rep of its row
  join_rep <- function(x, y, by, val) {
    a <- x |> left_join(y, by = c(".row", "rep", by), relationship = "many-to-one")
    y0 <- y |> filter(is.na(rep)) |> select(-rep) |> rename(.fill = all_of(val))
    a |> left_join(y0, by = c(".row", by), relationship = "many-to-one") |>
      mutate("{val}" := coalesce(.data[[val]], .fill)) |> select(-.fill)
  }
  v <- v |>
    join_rep(item_cells |> select(-item_col), "item_type", "item_raw") |>
    mutate(item_raw = if_else(!is.na(item_fixed), word(item_fixed, 2, -1, sep = ":"), item_raw),
           item_type = if_else(!is.na(item_fixed), word(item_fixed, 1, sep = ":"), item_type)) |>
    join_rep(unit_cells, "concept", "unit_raw")

  # items whose type has no value mapped in this file (e.g. crops grown on each plot when the
  # harvest is asked per household in another file) are kept as presence records: concept =
  # item type, no value. Rosters with a value column (harvest per pre-listed crop) are not:
  # there an empty value means the item is absent.
  valued <- unique(item_of(vals$concept))
  presence <- item_cells |>
    filter(!item_type %in% valued, !is.na(item_raw), item_raw != "") |>
    transmute(.row, rep, item_type, item_raw, concept = item_type, col = item_col)
  v <- bind_rows(v, presence)

  out <- v |>
    left_join(keys, by = ".row") |>
    transmute(source_id = sid, file = fmatch, row = .row, rep, hhid, parcel_id, plot_id, season,
              item_type, item_raw, concept, var = col, value_raw, value_lbl, unit_raw, multiply)

  list(data = out, log = tibble(source_id = sid, file = fmatch, status = "ok", rows_read = nrow(df),
                                values = nrow(out), columns = n_distinct(m$col),
                                missing = paste(missing$col, collapse = ";")))
}

jobs <- smap |> distinct(source_id, file_match)
say("Extracting %d files from %d sources ...", nrow(jobs), n_distinct(jobs$source_id))
res <- map(seq_len(nrow(jobs)), \(i) {
  j <- jobs[i, ]
  say("  %s / %s", j$source_id, j$file_match)
  tryCatch(extract_file(j$source_id, j$file_match, smap |> filter(source_id == j$source_id, file_match == j$file_match)),
           error = \(e) list(log = tibble(source_id = j$source_id, file = j$file_match, status = "error",
                                          missing = conditionMessage(e))))
})

long_raw <- map(res, "data") |> compact() |> list_rbind() |>
  left_join(src |> select(source_id, program, country, year), by = "source_id") |>
  relocate(program, country, year, .after = source_id)
xlog <- map(res, "log") |> list_rbind()

no_hh <- long_raw |> filter(is.na(hhid)) |> distinct(source_id, file)
if (nrow(no_hh) > 0) warning("Files without an hhid key (map one, or they cannot be joined): ",
                             paste(no_hh$source_id, no_hh$file, sep = "/", collapse = ", "))

saveRDS(long_raw, agh_path("agh_extract", "agh_long_raw.rds"))
write_csv(xlog, agh_path("agh_extract", "extract_log.csv"), na = "")
say("\nExtracted %s values:", format(nrow(long_raw), big.mark = ","))
print(xlog, n = Inf)
