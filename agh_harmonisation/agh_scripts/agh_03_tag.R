rm(list = ls())
# =============================================================================
# agh_03_tag.R — tag every dictionary variable with candidate concepts
#
# Reads   agh_meta/dictionary.rds, agh_config/concepts.csv
# Writes  agh_meta/candidates.csv          all candidate (variable, concept) pairs
#         agh_meta/coverage_by_study.csv   concept x study counts, ALL codebooks
#                                          (registered or catalog-only)
#         agh_meta/concept_check.csv       concept targets vs terminag
#         agh_config/source_map.csv        ✋ curation template (first run only)
#         agh_meta/source_map_new.csv      candidates not yet in your source_map
#
# Keyword tagging gives false positives and misses; it proposes, you decide
# (column keep in source_map.csv). Repeated columns (crop_1, crop_2, ...) are
# collapsed to one candidate with a suggested var_regex.
# =============================================================================

source(file.path(getOption("agh.scripts", "."), "agh_utils.R"))
init_config()

dictionary <- readRDS(agh_path("agh_meta", "dictionary.rds"))
concepts <- read_cfg("concepts.csv")

dup <- concepts |> count(concept) |> filter(n > 1)
if (nrow(dup) > 0) agh_halt("Duplicated concepts in agh_config/concepts.csv: ", paste(dup$concept, collapse = ", "))
bad <- concepts |> filter(is.na(pattern) | is.na(kind) | is.na(level))
if (nrow(bad) > 0) agh_halt("agh_config/concepts.csv rows missing pattern/kind/level: ", paste(bad$concept, collapse = ", "))

dictionary <- dictionary |>
  mutate(txt  = normalise(paste(var, coalesce(label, ""), coalesce(question, ""))),
         ftxt = normalise(paste(coalesce(file, ""), coalesce(file_desc, ""))))

# Optional conditions are skipped when NA (never passed to str_detect as a pattern)
tag <- function(dict, rules) {
  pmap(rules |> select(concept, pattern, also, exclude, file_hint), \(concept, pattern, also, exclude, file_hint) {
    hit <- str_detect(dict$txt, pattern)
    if (!is.na(also))    hit <- hit & str_detect(dict$txt, also)
    if (!is.na(exclude)) hit <- hit & !str_detect(dict$txt, exclude)
    out <- dict[which(hit), ]
    out$concept <- rep(concept, nrow(out))
    out$in_hint_file <- if (is.na(file_hint)) rep(NA, nrow(out)) else str_detect(out$ftxt, file_hint)
    out
  }) |> list_rbind()
}

say("Tagging %s variables against %d concepts ...", format(nrow(dictionary), big.mark = ","), nrow(concepts))
free_mem()
tagged <- tag(dictionary, concepts) |>
  left_join(concepts |> select(concept, kind, level, unit_of, domain, terminag), by = "concept") |>
  mutate(n_concepts = n_distinct(concept), .by = c(dict_id, file, var))

# Collapse repeated siblings to one row per stem
cands <- tagged |>
  mutate(rep_group = n_siblings > 1 & str_detect(var_stem, "#"),
         var_key = if_else(rep_group, var_stem, var)) |>
  summarise(
    var       = first(var),
    var_regex = if_else(first(rep_group),
                        paste0("^", str_replace(first(var_stem), "#", "(\\\\d+)"), "$"), NA_character_),
    n_repeats = n(),
    label     = first(label), question = first(question), file_desc = first(file_desc),
    n_concepts = max(n_concepts), in_hint_file = any(in_hint_file),
    .by = c(dict_id, source_id, registered, program, country, year, study, file,
            var_key, concept, kind, level, unit_of, domain, terminag)
  ) |>
  select(-var_key) |>
  mutate(n_in_file = n(), .by = c(dict_id, file, concept))

# one value-label summary per variable: some codebooks have two different files with the
# same name (e.g. one per survey round), whose variables then share (dict_id, file, var)
vl_text <- dictionary |>
  select(dict_id, file, var, value_labels) |>
  filter(!map_lgl(value_labels, is.null)) |>
  mutate(values = map_chr(value_labels, \(v) str_trunc(paste(v$value, v$value_label, sep = "=", collapse = "; "), 200))) |>
  distinct(dict_id, file, var, .keep_all = TRUE) |>
  select(-value_labels)

cands <- cands |> left_join(vl_text, by = c("dict_id", "file", "var"), relationship = "many-to-one") |>
  arrange(dict_id, file, factor(concept, levels = concepts$concept))
write_csv(cands, agh_path("agh_meta", "candidates.csv"), na = "")

# -----------------------------------------------------------------------------
# Coverage: which studies document which concepts (codebook level, before data)
# -----------------------------------------------------------------------------
coverage <- cands |>
  count(dict_id, registered, country, year, study, concept) |>
  mutate(concept = factor(concept, levels = concepts$concept)) |>
  arrange(concept) |>
  pivot_wider(names_from = concept, values_from = n, values_fill = 0) |>
  arrange(country, year)
write_csv(coverage, agh_path("agh_meta", "coverage_by_study.csv"), na = "")

# -----------------------------------------------------------------------------
# terminag check
# -----------------------------------------------------------------------------
tm <- load_terminag()
concept_check <- concepts |>
  select(concept, terminag, kind, level) |>
  mutate(in_terminag = if_else(is.na(terminag), NA, terminag %in% tm$vars$name))
write_csv(concept_check, agh_path("agh_meta", "concept_check.csv"), na = "")
nf <- concept_check |> filter(in_terminag %in% FALSE)
if (nrow(nf) > 0) warning("terminag names not found (edit concepts.csv): ", paste(nf$terminag, collapse = ", "))

# -----------------------------------------------------------------------------
# source_map template (registered sources only)
# -----------------------------------------------------------------------------
reg <- cands |> filter(registered)
map_cols <- c("keep", "source_id", "file", "var", "var_regex", "rep", "concept", "role", "unit_of",
              "item_fixed", "season_fixed", "multiply", "data_file",
              "label", "values", "n_concepts", "n_in_file", "in_hint_file", "n_repeats")

template <- reg |>
  mutate(
    role = if_else(kind %in% c("key", "item", "unit"), kind, "value"),
    # [assumed] pre-tick only unambiguous rows: one concept for the variable and one
    # variable for the concept in that file. Everything else waits for you.
    keep = if_else(n_concepts == 1 & n_in_file == 1, "TRUE", NA_character_),
    rep = NA_character_, item_fixed = NA_character_, season_fixed = NA_character_, multiply = NA_character_,
    data_file = NA_character_
  ) |>
  select(all_of(map_cols))

map_file <- agh_path("agh_config", "source_map.csv")
options(agh.map_created = !file.exists(map_file))
if (!file.exists(map_file)) {
  write_template(template, map_file,
    paste("source_map: keep=TRUE rows are extracted. role key|item|value|unit. var_regex: one capture group = repeat index",
          "(wide data like RHoMIS crop_1..n). rep: manual repeat index for side-by-side blocks (type/qty/unit of application 1, 2 ...).",
          "item_fixed e.g. animal:cattle for a column that counts one species only.",
          "season_fixed for files that are one season. multiply: numeric factor (e.g. 4046.856 acres->m2 on GPS area).",
          "data_file: data file name when it differs from the dictionary file. Delete or leave blank rows you do not want."))
  say("\nWrote template agh_config/source_map.csv (%d rows, %d pre-ticked). Curate it, then run step 4.",
      nrow(template), sum(template$keep %in% "TRUE"))
} else {
  existing <- read_cfg("source_map.csv")
  # datasets registered after source_map.csv was written: add their template rows and stop
  # so you can curate them (rows of datasets already in the map are never changed)
  added <- template |> filter(!source_id %in% existing$source_id)
  if (nrow(added) > 0) {
    hdr <- readLines(map_file, n = 1)
    writeLines(hdr, map_file)
    write_csv(bind_rows(existing, added |> mutate(across(everything(), as.character))), map_file,
              append = TRUE, col_names = TRUE, na = "")
    options(agh.map_created = TRUE)
    say("\nAdded %d template rows (%d pre-ticked) to agh_config/source_map.csv for %s. Curate them, then run step 4.",
        nrow(added), sum(added$keep %in% "TRUE"), paste(unique(added$source_id), collapse = ", "))
  }
  new <- template |>
    filter(source_id %in% existing$source_id) |>
    anti_join(existing, by = c("source_id", "file", "var", "concept"))
  write_csv(new, agh_path("agh_meta", "source_map_new.csv"), na = "")
  say("\nsource_map.csv: rows of datasets already curated kept as is. %d new candidate rows for them in agh_meta/source_map_new.csv (copy the ones you want).", nrow(new))
}

say("\nConcept coverage (number of studies with >= 1 candidate):")
print(cands |> distinct(dict_id, registered, concept) |> count(concept, registered) |>
        pivot_wider(names_from = registered, values_from = n, values_fill = 0, names_prefix = "registered_") |>
        arrange(factor(concept, levels = concepts$concept)), n = Inf)
