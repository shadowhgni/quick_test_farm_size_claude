rm(list = ls())
# =============================================================================
# agh_02_dictionary.R — one dictionary table from every codebook
#
# Reads   agh_config/sources.csv          your datasets (data_path + dict_path)
#         agh_meta/study_catalog.csv      (optional) studies harvested in step 1
# Writes  agh_meta/dictionary.rds         all variables, with value labels (list-column)
#         agh_meta/dictionary.csv         same, value labels collapsed to text
#         agh_meta/value_labels.csv       long: dict_id, file, var, value, value_label
#         agh_meta/data_inventory.csv     data files found for each registered source
#         agh_meta/dict_vs_data.csv       dictionary files with / without a data file
#
# dict_id is the source_id for registered sources and "<server>_<id>" for
# catalog-only studies (codebook known, microdata not registered yet). The
# catalog-only rows let step 3 report concept coverage before you request data.
# =============================================================================

source(file.path(getOption("agh.scripts", "."), "agh_utils.R"))
init_config()

include_catalog <- TRUE   # also parse every DDI harvested in step 1

detect_format <- function(dict_path) {
  p <- str_to_lower(dict_path)
  case_when(
    str_detect(p, "^nada:")          ~ "ddi",
    p == "terminag"                  ~ "terminag",
    p == "data"                      ~ "data",
    str_detect(p, "\\.xml$")         ~ "ddi",
    str_detect(p, "\\.xlsx?$")       ~ "xlsx_auto",   # xlsform or table, decided by sheets
    str_detect(p, "\\.(csv|tsv)$")   ~ "table",
    dir.exists(dict_path)            ~ "folder",
    .default = NA_character_
  )
}

resolve_nada <- function(spec) {
  parts <- str_split_1(spec, ":")
  f <- agh_path("agh_meta", "ddi", sprintf("%s_%s.xml", parts[2], parts[3]))
  if (!file.exists(f)) {
    cats <- read_cfg("catalogs.csv")
    base <- cats$base_url[cats$server == parts[2]][1]
    if (is.na(base)) stop("Unknown server '", parts[2], "' in ", spec, " (add it to catalogs.csv)")
    f <- fetch(sprintf("%s/index.php/metadata/export/%s/ddi", base, parts[3]), f)
    if (is.na(f)) stop("Could not download ", spec)
  }
  f
}

is_xlsform <- function(path) all(c("survey") %in% str_to_lower(readxl::excel_sheets(path)))

parse_one_dict <- function(path, fmt, inv, terminag_vars) {
  if (fmt == "folder") {
    ff <- list.files(path, pattern = "\\.(xml|xlsx|xls|csv)$", full.names = TRUE, recursive = TRUE)
    return(map(ff, \(f) parse_one_dict(f, detect_format(f), inv, terminag_vars)$dict) |>
             list_rbind() |> (\(d) list(meta = NULL, dict = d))())
  }
  switch(fmt,
    ddi       = parse_ddi(path),
    xlsx_auto = list(meta = NULL, dict = if (is_xlsform(path)) parse_xlsform(path) else parse_table_dict(path)),
    xlsform   = list(meta = NULL, dict = parse_xlsform(path)),
    table     = list(meta = NULL, dict = parse_table_dict(path)),
    data      = list(meta = NULL, dict = map2(inv$container, inv$member, parse_from_data) |> list_rbind()),
    terminag  = list(meta = NULL, dict = map2(inv$container, inv$member, \(c, m) {
                  cols <- names(read_any(c, m) |> select(!ends_with("__lbl")) |> head(0))
                  parse_terminag_dict(terminag_vars, cols, file_key(m %|% c))
                }) |> list_rbind()),
    stop("Unknown dict_format: ", fmt)
  )
}

# -----------------------------------------------------------------------------
# 1. Registered sources
# -----------------------------------------------------------------------------
src <- read_cfg("sources.csv") |>
  filter(as_lgl(enabled) %in% TRUE | is.na(enabled)) |>
  mutate(dict_format = coalesce(dict_format, detect_format(dict_path)))

needs_terminag <- any(src$dict_format == "terminag")
tm <- if (needs_terminag) load_terminag() else list(vars = tibble(name = character(), description = character(), unit = character()))

inventory <- map(seq_len(nrow(src)), \(i) {
  list_data_files(src$data_path[i]) |> mutate(source_id = src$source_id[i], .before = 1)
}) |> list_rbind()
# no registered source yet (first run, catalog only): keep the columns used below
if (nrow(inventory) == 0) inventory <- tibble(source_id = character(), container = character(),
                                              member = character(), file = character())
if (nrow(inventory) > 0) inventory <- inventory |> mutate(file = file_key(coalesce(member, container)))
missing_data <- src |> filter(!source_id %in% inventory$source_id)
if (nrow(missing_data) > 0) warning("No data files found for: ", paste(missing_data$source_id, collapse = ", "),
                                    ". Check data_path (relative paths start from agh_scripts/).")

reg_dicts <- map(seq_len(nrow(src)), \(i) {
  s <- src[i, ]
  say("Dictionary for %s (%s)", s$source_id, s$dict_format)
  path <- if (str_detect(s$dict_path, "^nada:")) resolve_nada(s$dict_path) else s$dict_path
  inv <- inventory |> filter(source_id == s$source_id)
  out <- tryCatch(parse_one_dict(path, s$dict_format, inv, tm$vars), error = \(e) {
    warning(s$source_id, ": ", conditionMessage(e)); NULL })
  if (is.null(out) || nrow(out$dict) == 0) return(NULL)
  d <- out$dict
  # a dictionary without file names belongs to the single data file, if there is one
  if (all(is.na(d$file)) && nrow(inv) == 1) d$file <- inv$file
  d |> mutate(dict_id = s$source_id, source_id = s$source_id, program = s$program,
              country = coalesce(s$country, out$meta$country[1] %||% NA_character_),
              year = coalesce(s$year, out$meta$years[1] %||% NA_character_),
              study = out$meta$title[1] %||% s$notes %||% NA_character_,
              registered = TRUE, .before = 1)
}) |> list_rbind()

# -----------------------------------------------------------------------------
# 2. Catalog-only studies (DDI harvested, data not registered)
# -----------------------------------------------------------------------------
cat_dicts <- NULL
cat_file <- agh_path("agh_meta", "study_catalog.csv")
if (include_catalog && file.exists(cat_file)) {
  studies <- read_csv(cat_file, col_types = cols(.default = "c"), show_col_types = FALSE) |>
    filter(!is.na(ddi_file))
  linked <- src$dict_path[str_detect(src$dict_path, "^nada:")] |> str_remove("^nada:") |> str_replace(":", "_")
  studies <- studies |> filter(!paste(server, id, sep = "_") %in% linked)
  say("Parsing %d catalog DDI codebooks ...", nrow(studies))
  cat_dicts <- map(seq_len(nrow(studies)), \(i) {
    s <- studies[i, ]
    out <- tryCatch(parse_ddi(s$ddi_file), error = \(e) NULL)
    if (is.null(out) || nrow(out$dict) == 0) return(NULL)
    out$dict |> mutate(dict_id = paste(s$server, s$id, sep = "_"), source_id = NA_character_,
                       program = s$server, country = s$country,
                       year = paste(unique(na.omit(c(s$year_start, s$year_end))), collapse = "-"),
                       study = s$title, registered = FALSE, .before = 1)
  }) |> list_rbind()
}

dictionary <- bind_rows(reg_dicts, cat_dicts) |> as_tibble()   # list_rbind() of nothing is a data.frame
if (nrow(dictionary) == 0) stop("No dictionary parsed. Check sources.csv (enabled, dict_path) and step 1 output.")

dictionary <- dictionary |>
  mutate(var_stem = var_stem(var)) |>
  mutate(n_siblings = n(), .by = c(dict_id, file, var_stem))

value_labels <- dictionary |>
  select(dict_id, file, var, value_labels) |>
  filter(!map_lgl(value_labels, is.null)) |>
  unnest(value_labels)

dict_flat <- dictionary |>
  left_join(value_labels |> summarise(values = str_trunc(paste(value, value_label, sep = "=", collapse = "; "), 300),
                                      n_values = n(), .by = c(dict_id, file, var)),
            by = c("dict_id", "file", "var")) |>
  select(-value_labels)

# Dictionary files vs data files (registered sources only)
dict_vs_data <- dict_flat |>
  filter(registered) |>
  distinct(source_id, file) |>
  mutate(file_lc = str_to_lower(file)) |>
  full_join(inventory |> distinct(source_id, file_lc = file, container, member),
            by = c("source_id", "file_lc")) |>
  mutate(status = case_when(is.na(file) ~ "data_only", is.na(container) ~ "dictionary_only", .default = "matched"))

saveRDS(dictionary, agh_path("agh_meta", "dictionary.rds"))
write_csv(dict_flat, agh_path("agh_meta", "dictionary.csv"), na = "")
write_csv(value_labels, agh_path("agh_meta", "value_labels.csv"), na = "")
write_csv(inventory, agh_path("agh_meta", "data_inventory.csv"), na = "")
write_csv(dict_vs_data, agh_path("agh_meta", "dict_vs_data.csv"), na = "")

say("\nVariables per dictionary:")
print(dict_flat |> summarise(files = n_distinct(file), vars = n(), .by = c(dict_id, registered, country, year)), n = 50)
say("\nRegistered sources, dictionary vs data files:")
print(count(dict_vs_data, source_id, status) |> pivot_wider(names_from = status, values_from = n, values_fill = 0))
