rm(list = ls())
# =============================================================================
# agh_05_curate.R — curation rules: recode, convert units, derive, reshape by level
#
# Reads   agh_extract/agh_long_raw.rds, agh_config/{concepts, value_map, unit_map,
#         unit_defaults, tlu_factors}.csv
# Writes  agh_config/value_map.csv   ✋ raw labels -> standard values (new labels appended,
#                                       pre-filled with a suggestion, checked = blank)
#         agh_config/unit_map.csv    ✋ raw units -> factor to the target unit (same logic)
#         agh_curated/agh_long.rds   curated long table (std values, value_num, unit_status)
#         agh_curated/agh_<level>.rds/.csv  hh, plot, plot_crop, plot_input, hh_animal
#         agh_curated/output_dictionary.csv  columns of the level tables
#         agh_curated/qc_*.csv       unmapped labels, unknown units, missing TLU, value summaries
#
# Re-run this step alone after editing value_map / unit_map / tlu_factors.
# =============================================================================

source(file.path(getOption("agh.scripts", "."), "agh_utils.R"))
init_config()

# Plausibility flags on derived values (rows are flagged in qc_flag, never dropped)
qc_limits <- list(
  plot_area_m2_min = 10,        # [assumed]
  plot_area_m2_max = 100 * 1e4, # [assumed] 100 ha
  fertilizer_kg_ha_max = 1000,  # [verified] terminag valid_max of fertilizer_amount
  OM_kg_ha_max = 100000,        # [assumed]
  yield_kg_ha_max = 30000       # [assumed]; terminag's own max (150000) is too loose for a flag
)
flag <- function(...) {
  conds <- list(...)
  map_chr(seq_along(conds[[1]]), \(i) {
    hit <- names(conds)[map_lgl(conds, \(x) isTRUE(x[i]))]
    if (length(hit) == 0) NA_character_ else paste(hit, collapse = "; ")
  })
}

long <- readRDS(agh_path("agh_extract", "agh_long_raw.rds"))
concepts <- read_cfg("concepts.csv")
tm <- load_terminag()
voc <- \(nm) tm$values[[nm]] %||% tibble(name = character())

long <- long |>
  left_join(concepts |> select(concept, kind, level, unit_target, agg), by = "concept") |>
  mutate(raw_n = normalise(coalesce(value_lbl, value_raw)),
         item_n = normalise(item_raw))

# -----------------------------------------------------------------------------
# 1. value_map: suggestions [assumed rules; every suggested row has checked = blank]
# -----------------------------------------------------------------------------
match_vocab <- function(x, vocab, alt = NULL) {
  v  <- normalise(vocab)
  vs <- str_remove_all(v, " ")
  a  <- if (is.null(alt)) NULL else normalise(alt)
  map_chr(x, \(s) {
    if (is.na(s)) return(NA_character_)
    hit <- vocab[v == s | vs == str_remove_all(s, " ")]
    if (length(hit) == 0 && !is.null(a)) hit <- vocab[!is.na(a) & str_detect(a, paste0("(^|;)\\s*", fixed_rx(s), "\\s*(;|$)"))]
    if (length(hit) == 0) {
      s2 <- s |> str_remove_all("\\(.*?\\)") |>
        str_remove_all("\\b(local|improved|hybrid|composite|opv|recycled|other|white|yellow|red|seed|seeds|variety|grain|green|dry|fresh)\\b") |>
        str_squish() |> str_remove("s$")
      hit <- vocab[v == s2 | vs == str_remove_all(s2, " ")]
    }
    hit[1] %||% NA_character_
  })
}
fixed_rx <- \(s) str_replace_all(s, "([.^$|()\\[\\]{}*+?\\\\])", "\\\\\\1")

animal_rules <- c(
  "calf|calves|veau|velle"                          = "cattle:calf",
  "heifer|genisse|taurillon|young bull|steer"       = "cattle:young",
  "\\bcows?\\b|\\bbulls?\\b|\\box(en)?\\b|cattle|bovin|boeuf|vache|zebu|\\bgado\\b|taureau" = "cattle",
  "goat|chevre|caprin|cabri|cabra|bouc"             = "goat",
  "sheep|\\brams?\\b|\\bewes?\\b|lamb|mouton|ovin|brebis|belier|ovelha" = "sheep",
  "guinea ?fowl|pintade"                            = "guinea fowl",
  "turkey|dinde|dindon"                             = "turkey",
  "duck|canard|pato"                                = "duck",
  "goose|geese|\\boie\\b"                           = "goose",
  "pigeon|\\bdoves?\\b"                             = "pigeon",
  "chicken|\\bhens?\\b|cock|rooster|layer|broiler|poulet|\\bpoules?\\b|\\bcoq|galinha|frango" = "chicken",
  "poultry|volaille|aves"                           = "poultry",
  "\\bpigs?\\b|swine|\\bporcs?\\b|\\bsows?\\b|piglet|\\bboars?\\b|porco|truie" = "pig",
  "donkey|\\bass(es)?\\b|\\banes?\\b|burro|jument|asinin" = "donkey",
  "\\bmules?\\b|mulet"                              = "mule",
  "horse|cheval|chevaux|\\bmares?\\b|stallion|cavalo" = "horse",
  "camel|chameau|dromad"                            = "camel",
  "rabbit|lapin|coelho"                             = "rabbit",
  "buffalo|buffle"                                  = "buffalo")

first_rule <- function(x, rules) {
  map_chr(x, \(s) { if (is.na(s)) return(NA_character_)
    hit <- names(rules)[str_detect(s, names(rules))]; if (length(hit)) rules[[hit[1]]] else NA_character_ })
}

land_use_rules <- c(
  "fallow|jachere|pousio|idle|resting|left uncultivated" = "fallow",
  "rent(ed)? out|lent out|loue a|given out|sharecropped out" = "rented_out",
  "pasture|graz|paturage|parcours|pastagem"   = "pasture",
  "forest|woodlot|\\btrees?\\b|bois|foret|plantation forestiere" = "forest",
  "cultivat|\\bcrops?\\b|cropped|planted|annual|perennial|cultive|culture|cultivo|garden|orchard" = "cropland",
  "residen|house|building|habitation"          = "residential")
tenure_rules <- c(
  "sharecrop|metayage"                         = "sharecropped",
  "rent|lease|\\bloue|location|fermage|arrend" = "rented_in",
  "borrow|free of charge|for free|\\bprete|emprest" = "borrowed",
  "inherit|herit|customary|allocated|granted|chief|lineage|family land|coutum" = "owned_customary",
  "purchas|bought|achat|achet|compra"           = "owned_purchased",
  "communal|community|collecti"                 = "communal")
sex_rules <- c("female|femme|feminin|mulher|\\bf\\b" = "female", "male|homme|masculin|homem|\\bm\\b" = "male")
om_rules <- c("vermicompost" = "vermicompost", "compost" = "compost",
              "poultry|chicken|hen" = "poultry manure", "dung|manure|fumier|kraal|fumure animale|estrume" = "farmyard manure",
              "residue|stover|straw|paille|residu" = "crop residue", "mulch|paillage" = "mulch", "ash|cendre" = "wood ashes")
fert_rules <- c("\\burea\\b|uree" = "urea", "\\bdap\\b|diammonium" = "DAP", "\\bcan\\b|calcium ammonium nitrate" = "CAN",
                "\\bssp\\b|single super" = "SSP", "\\btsp\\b|triple super" = "TSP", "\\bmap\\b|monoammonium" = "MAP",
                "\\bkcl\\b|muriate|potash" = "KCl", "sulphate of ammonia|ammonium sulfate|ammonium sulphate|\\bsa\\b" = "AS",
                "npk|n p k|\\d+ \\d+ \\d+|23 21 0|chitowe|compound d|\\bd compound" = "NPK")

suggest <- function(concept, raw_n, kind) {
  case_when(
    kind == "lgl"               ~ as.character(as_lgl(raw_n)),
    concept == "animal"         ~ first_rule(raw_n, animal_rules),
    concept %in% c("crop", "previous_crop") ~ match_vocab(raw_n, voc("crop")$name, voc("crop")[["altname"]]),
    concept == "OM_type"        ~ coalesce(match_vocab(raw_n, voc("OM")$name), first_rule(raw_n, om_rules)),
    concept == "fertilizer_type"~ coalesce(match_vocab(raw_n, voc("fertilizer_type")$name), first_rule(raw_n, fert_rules)),
    concept == "land_use"       ~ first_rule(raw_n, land_use_rules),
    concept == "land_tenure"    ~ first_rule(raw_n, tenure_rules),
    concept == "head_sex"       ~ first_rule(raw_n, sex_rules),
    .default = raw_n            # other categorical concepts: keep the label as is
  )
}

pairs <- bind_rows(
  long |> filter(!is.na(item_n)) |> count(concept = item_type, raw = item_n, name = "n"),
  long |> filter(kind %in% c("cat", "lgl")) |> count(concept, raw = raw_n, name = "n")
) |> summarise(n = sum(n), .by = c(concept, raw)) |>
  left_join(concepts |> select(concept, kind), by = "concept")

vm_file <- agh_path("agh_config", "value_map.csv")
vm_old <- if (file.exists(vm_file)) read_cfg("value_map.csv") else
  tibble(concept = character(), raw = character(), std = character(), checked = character(), n = character())
vm_new <- pairs |>
  anti_join(vm_old, by = c("concept", "raw")) |>
  mutate(std = suggest(concept, raw, kind), checked = NA_character_, n = as.character(n)) |>
  select(concept, raw, std, checked, n)
vm <- bind_rows(vm_old |> select(any_of(names(vm_new))), vm_new) |> arrange(concept, raw)
voc_all <- c(voc("crop")$name, voc("animal")$name, voc("OM")$name, voc("fertilizer_type")$name)
vm <- vm |> mutate(in_terminag = if_else(concept %in% c("crop", "previous_crop", "animal", "OM_type", "fertilizer_type"),
                                         as.character(word(std, 1, sep = ":") %in% voc_all), ""))
write_template(vm, vm_file, paste("value_map: raw (normalised label) -> std. Edit std, set checked = TRUE when reviewed.",
                                  "animal std may carry a class (cattle:calf) used by tlu_factors. Blank std = keep raw label."))
if (nrow(vm_new) > 0) say("value_map.csv: %d new labels appended with suggestions (checked blank).", nrow(vm_new))

vm_use <- vm |> transmute(concept, raw, std = coalesce(std, raw))

# -----------------------------------------------------------------------------
# 2. unit_map
# -----------------------------------------------------------------------------
udef <- read_cfg("unit_defaults.csv") |> mutate(factor = num(factor))
dim_of <- \(target) case_when(target == "kg" ~ "mass", target %in% c("m2", "ha") ~ "area", .default = NA_character_)
default_factor <- function(unit_n, target) {
  map2_dbl(unit_n, target, \(u, t) {
    d <- udef |> filter(dimension == dim_of(t))
    hit <- d |> filter(str_detect(u %||% "", pattern))
    if (nrow(hit) == 0 || is.na(u)) return(NA_real_)
    f <- hit$factor[1]
    if (t == "ha" && hit$target[1] == "m2") f <- f / 10000
    f
  })
}

upairs <- long |>
  filter(!is.na(unit_raw)) |>
  mutate(unit = normalise(unit_raw)) |>
  count(source_id, concept, unit, unit_target, name = "n")

um_file <- agh_path("agh_config", "unit_map.csv")
um_old <- if (file.exists(um_file)) read_cfg("unit_map.csv") else
  tibble(source_id = character(), concept = character(), item = character(), unit = character(),
         factor = character(), target = character(), checked = character(), n = character())
um_new <- upairs |>
  anti_join(um_old |> filter(is.na(item)), by = c("source_id", "concept", "unit")) |>
  mutate(item = NA_character_, factor = as.character(default_factor(unit, unit_target)),
         target = unit_target, checked = NA_character_, n = as.character(n)) |>
  select(source_id, concept, item, unit, factor, target, checked, n)
um <- bind_rows(um_old, um_new) |> arrange(source_id, concept, unit, item)
write_template(um, um_file, paste("unit_map: factor converts value x factor -> target unit. item (optional) = std item",
                                  "(e.g. maize) for item-specific factors such as LSMS conversion tables; source_id * = all sources."))
if (nrow(um_new) > 0) say("unit_map.csv: %d new units appended (%d with a default factor).",
                          nrow(um_new), sum(!is.na(um_new$factor)))

um_use <- um |> mutate(factor = num(factor))

# -----------------------------------------------------------------------------
# 3. Curated long table
# -----------------------------------------------------------------------------
cur <- long |>
  left_join(vm_use |> rename(item_type = concept, item_n = raw, item_std = std), by = c("item_type", "item_n")) |>
  left_join(vm_use |> rename(raw_n = raw, value_std = std), by = c("concept", "raw_n")) |>
  mutate(item_std = coalesce(item_std, item_n), unit = normalise(unit_raw))

# unit factor: item-specific > source-specific > wildcard
f_item <- um_use |> filter(!is.na(item), source_id != "*") |> select(source_id, concept, item_std = item, unit, f1 = factor)
f_src  <- um_use |> filter(is.na(item), source_id != "*") |> select(source_id, concept, unit, f2 = factor)
f_any  <- um_use |> filter(is.na(item), source_id == "*") |> select(concept, unit, f3 = factor) |> distinct(concept, unit, .keep_all = TRUE)

cur <- cur |>
  left_join(f_item, by = c("source_id", "concept", "item_std", "unit")) |>
  left_join(f_src,  by = c("source_id", "concept", "unit")) |>
  left_join(f_any,  by = c("concept", "unit")) |>
  mutate(
    unit_factor = coalesce(f1, f2, f3),
    unit_status = case_when(kind != "num" ~ NA_character_, is.na(unit_raw) ~ "no_unit_var",
                            !is.na(unit_factor) ~ "converted", .default = "unknown_unit"),
    value_num = if_else(kind == "num",
                        num(value_raw) * coalesce(num(multiply), 1) * if_else(is.na(unit_raw), 1, unit_factor),
                        NA_real_),
    value_lgl = if_else(kind == "lgl", as.logical(value_std), NA)
  ) |>
  select(-f1, -f2, -f3)

# -----------------------------------------------------------------------------
# 4. Level tables (wide). Keys: hh < parcel < plot (season) < plot_crop / plot_input; hh_animal
# -----------------------------------------------------------------------------
cur <- cur |> mutate(
  crop       = if_else(level == "plot_crop" & item_type == "crop", item_std, NA_character_),
  animal_raw = if_else(level == "hh_animal", item_std, NA_character_),
  input_type = if_else(level == "plot_input", item_type, NA_character_),
  input      = if_else(level == "plot_input", item_std, NA_character_))

level_keys <- list(
  hh         = c("source_id", "hhid"),
  parcel     = c("source_id", "hhid", "parcel_id"),
  plot       = c("source_id", "hhid", "parcel_id", "plot_id", "season"),
  plot_crop  = c("source_id", "hhid", "parcel_id", "plot_id", "season", "crop"),
  plot_input = c("source_id", "hhid", "parcel_id", "plot_id", "season", "input_type", "input"),
  hh_animal  = c("source_id", "hhid", "animal_raw"))

make_level <- function(lv) {
  keys <- level_keys[[lv]]
  d <- cur |> filter(level == lv, !is.na(hhid))
  if (nrow(d) == 0) return(NULL)
  rule <- concepts |> select(concept, agg)
  d <- d |> left_join(rule |> rename(agg2 = agg), by = "concept") |> mutate(agg2 = coalesce(agg2, "first"))
  nums <- d |> filter(kind == "num") |>
    summarise(v = case_when(first(agg2) == "sum" ~ if (all(is.na(value_num))) NA_real_ else sum(value_num, na.rm = TRUE),
                            first(agg2) == "max" ~ if (all(is.na(value_num))) NA_real_ else max(value_num, na.rm = TRUE),
                            .default = first(value_num[!is.na(value_num)], default = NA_real_)),
              .by = all_of(c(keys, "concept"))) |>
    pivot_wider(names_from = concept, values_from = v)
  lgls <- d |> filter(kind == "lgl") |>
    summarise(v = if (all(is.na(value_lgl))) NA else any(value_lgl, na.rm = TRUE), .by = all_of(c(keys, "concept"))) |>
    pivot_wider(names_from = concept, values_from = v)
  cats <- d |> filter(kind == "cat") |>
    summarise(v = first(value_std[!is.na(value_std)], default = NA_character_), .by = all_of(c(keys, "concept"))) |>
    pivot_wider(names_from = concept, values_from = v)
  base <- d |> distinct(across(all_of(keys)))
  list(nums, lgls, cats) |>
    keep(\(x) ncol(x) > length(keys)) |>
    reduce(\(a, b) left_join(a, b, by = keys), .init = base)
}

tabs <- map(set_names(names(level_keys)), make_level)
ensure <- \(df, cols, type = NA_real_) { for (c in cols) if (!c %in% names(df)) df[[c]] <- type; df }

src_info <- cur |> distinct(source_id, program, country, year)

# ---- hh_animal: species, class, TLU -----------------------------------------
tlu <- read_cfg("tlu_factors.csv") |> mutate(tlu = num(tlu))
hh_animal <- tabs$hh_animal
if (!is.null(hh_animal)) {
  hh_animal <- hh_animal |>
    ensure("heads") |>
    mutate(animal = word(animal_raw, 1, sep = ":"),
           animal_class = if_else(str_detect(animal_raw, ":"), word(animal_raw, 2, sep = ":"), NA_character_)) |>
    left_join(tlu |> select(animal_raw = animal, f_class = tlu), by = "animal_raw") |>
    left_join(tlu |> select(animal, f_species = tlu), by = "animal") |>
    mutate(tlu_factor = coalesce(f_class, f_species), TLU = heads * tlu_factor) |>
    select(-f_class, -f_species) |>
    relocate(animal, animal_class, .after = hhid)
  tlu_missing <- hh_animal |> filter(is.na(tlu_factor), !is.na(heads)) |> count(animal, animal_raw, name = "n_records")
  write_csv(tlu_missing, agh_path("agh_curated", "qc_tlu_missing.csv"), na = "")
}

# ---- plot_input -> plot aggregates ------------------------------------------
plot_in <- tabs$plot_input
plot_agg <- NULL
if (!is.null(plot_in)) {
  plot_in <- plot_in |> ensure(c("OM_amount", "fertilizer_amount"))
  plot_agg <- plot_in |>
    summarise(
      OM_amount_kg = if (all(is.na(OM_amount))) NA_real_ else sum(OM_amount, na.rm = TRUE),
      OM_types = paste(sort(unique(na.omit(input[input_type == "OM_type"]))), collapse = "; ") |> na_if(""),
      fertilizer_amount_kg = if (all(is.na(fertilizer_amount))) NA_real_ else sum(fertilizer_amount, na.rm = TRUE),
      fertilizer_types = paste(sort(unique(na.omit(input[input_type == "fertilizer_type"]))), collapse = "; ") |> na_if(""),
      .by = all_of(level_keys$plot))
}

# ---- plot -------------------------------------------------------------------
plot <- tabs$plot
if (!is.null(plot) || !is.null(plot_agg)) {
  # (explicit if: `a %||% b |> f()` would parse as `(a %||% b) |> f()`)
  if (is.null(plot)) plot <- plot_agg |> select(all_of(level_keys$plot))
  plot <- plot |>
    ensure(c("plot_area_gps", "plot_area_reported")) |>
    ensure(c("land_use", "OM_types", "fertilizer_types"), NA_character_) |>
    ensure(c("fallow", "OM_used", "fertilizer_used"), NA)
  if (!is.null(plot_agg)) plot <- plot |> select(-any_of(setdiff(names(plot_agg), level_keys$plot))) |>
    full_join(plot_agg, by = level_keys$plot)
  plot <- plot |>
    ensure(c("OM_amount_kg", "fertilizer_amount_kg", "OM_rate", "fertilizer_rate")) |>
    mutate(
      plot_area_m2   = coalesce(plot_area_gps, plot_area_reported),
      area_source    = case_when(!is.na(plot_area_gps) ~ "gps", !is.na(plot_area_reported) ~ "reported"),
      fallow_flag    = coalesce(fallow, land_use == "fallow"),
      OM_used_any    = case_when(OM_used %in% TRUE | OM_amount_kg > 0 ~ TRUE,
                                 OM_used %in% FALSE ~ FALSE, .default = NA),
      fertilizer_used_any = case_when(fertilizer_used %in% TRUE | fertilizer_amount_kg > 0 ~ TRUE,
                                      fertilizer_used %in% FALSE ~ FALSE, .default = NA),
      # totals / area where both exist; else a rate recorded directly (Carob, kg/ha)
      OM_kg_ha         = coalesce(OM_amount_kg / (plot_area_m2 / 1e4), OM_rate),
      fertilizer_kg_ha = coalesce(fertilizer_amount_kg / (plot_area_m2 / 1e4), fertilizer_rate),
      OM_used_any      = coalesce(OM_used_any, OM_rate > 0),
      fertilizer_used_any = coalesce(fertilizer_used_any, fertilizer_rate > 0)
    ) |>
    mutate(qc_flag = flag(area_small = plot_area_m2 < qc_limits$plot_area_m2_min,
                          area_large = plot_area_m2 > qc_limits$plot_area_m2_max,
                          fert_high  = fertilizer_kg_ha > qc_limits$fertilizer_kg_ha_max,
                          OM_high    = OM_kg_ha > qc_limits$OM_kg_ha_max))
}

# ---- plot_crop --------------------------------------------------------------
plot_crop <- tabs$plot_crop
if (!is.null(plot_crop)) {
  plot_crop <- plot_crop |>
    ensure(c("harvest_qty", "crop_area_share")) |>
    rename(harvest_kg = harvest_qty) |>
    mutate(crop_area_share = if_else(crop_area_share > 1, crop_area_share / 100, crop_area_share))
  if (!is.null(plot)) {
    plot_crop <- plot_crop |>
      left_join(plot |> select(all_of(level_keys$plot), plot_area_m2), by = level_keys$plot) |>
      mutate(crop_area_m2 = plot_area_m2 * coalesce(crop_area_share, if_else(n() == 1, 1, NA_real_)),
             .by = all_of(level_keys$plot)) |>
      ensure("yield") |>
      mutate(yield_kg_ha = coalesce(harvest_kg / (crop_area_m2 / 1e4), yield),
             yield_source = case_when(!is.na(harvest_kg / (crop_area_m2 / 1e4)) ~ "harvest/area",
                                      !is.na(yield) ~ "reported_yield"),
             qc_flag = flag(yield_high = yield_kg_ha > qc_limits$yield_kg_ha_max,
                            no_harvest_unit_factor = is.na(harvest_kg) & is.na(yield)))
  }
}

# sum that is NA when every value is NA (0 only when some value is known);
# an empty selection (e.g. no fallow plot) is a real 0
sum_na <- function(x) if (length(x) > 0 && all(is.na(x))) NA_real_ else sum(x, na.rm = TRUE)

# ---- hh ---------------------------------------------------------------------
hh <- tabs$hh %||% tibble(source_id = character(), hhid = character())
hh_parts <- list()
if (!is.null(hh_animal)) {
  hh_parts$tlu <- hh_animal |>
    summarise(TLU = sum_na(TLU), TLU_complete = all(!is.na(TLU) | is.na(heads)), .by = c(source_id, hhid))
  hh_parts$heads <- hh_animal |>
    summarise(h = sum(heads, na.rm = TRUE), .by = c(source_id, hhid, animal)) |>
    filter(!is.na(animal)) |>
    pivot_wider(names_from = animal, values_from = h, names_prefix = "heads_", names_repair = "universal")
}
if (!is.null(plot)) {
  cropped <- if (!is.null(plot_crop)) plot_crop |> distinct(across(all_of(level_keys$plot))) |> mutate(has_crop = TRUE) else NULL
  p <- if (is.null(cropped)) plot |> mutate(has_crop = NA) else
    plot |> left_join(cropped, by = level_keys$plot)
  hh_parts$land <- p |>
    mutate(cropped = land_use %in% "cropland" | (is.na(land_use) & has_crop %in% TRUE)) |>
    summarise(n_plots = n_distinct(paste(parcel_id, plot_id)),
              plots_area_ha = sum_na(plot_area_m2) / 1e4,
              cropland_ha   = if (any(!is.na(land_use) | !is.na(has_crop))) sum_na(plot_area_m2[cropped]) / 1e4 else NA_real_,
              fallow_ha     = if (any(!is.na(fallow_flag))) sum_na(plot_area_m2[fallow_flag %in% TRUE]) / 1e4 else NA_real_,
              area_missing_plots = sum(is.na(plot_area_m2)),
              OM_used_any   = if (all(is.na(OM_used_any))) NA else any(OM_used_any, na.rm = TRUE),
              fertilizer_used_any = if (all(is.na(fertilizer_used_any))) NA else any(fertilizer_used_any, na.rm = TRUE),
              .by = c(source_id, hhid))
}
for (part in hh_parts) {
  hh <- hh |> full_join(part, by = c("source_id", "hhid"))
}

out <- list(hh = hh, plot = plot, plot_crop = plot_crop, plot_input = plot_in, hh_animal = hh_animal) |>
  compact() |>
  map(\(t) t |> left_join(src_info, by = "source_id") |> relocate(program, country, year, .after = source_id))

# -----------------------------------------------------------------------------
# 5. Write outputs + QC
# -----------------------------------------------------------------------------
saveRDS(cur, agh_path("agh_curated", "agh_long.rds"))
iwalk(out, \(t, nm) {
  saveRDS(t, agh_path("agh_curated", paste0("agh_", nm, ".rds")))
  write_csv(t, agh_path("agh_curated", paste0("agh_", nm, ".csv")), na = "")
})

derived_desc <- tribble(
  ~column, ~description, ~unit,
  "plot_area_m2", "GPS area if available, else farmer-reported (converted)", "m2",
  "area_source", "which area was used", "",
  "fallow_flag", "fallow question, else land_use == fallow", "",
  "OM_amount_kg", "organic amendment applied, summed over types", "kg",
  "OM_kg_ha", "OM_amount_kg / plot area, else OM_rate", "kg/ha",
  "fertilizer_amount_kg", "inorganic fertilizer product applied, summed", "kg",
  "fertilizer_kg_ha", "fertilizer_amount_kg / plot area, else fertilizer_rate", "kg/ha",
  "harvest_kg", "harvest converted to kg", "kg",
  "crop_area_m2", "plot area x crop share (sole crop on a one-crop plot)", "m2",
  "yield_kg_ha", "harvest_kg / crop_area_m2, else reported yield (e.g. Carob)", "kg/ha",
  "yield_source", "harvest/area or reported_yield", "",
  "TLU", "sum of heads x TLU factor (tlu_factors.csv)", "TLU",
  "qc_flag", "plausibility flags (limits in qc_limits at the top of agh_05_curate.R); rows are kept", "",
  "TLU_complete", "FALSE when some species had no TLU factor", "",
  "plots_area_ha", "sum of plot areas", "ha",
  "cropland_ha", "area of plots used for crops", "ha",
  "fallow_ha", "area of fallow plots", "ha")
out_dict <- imap(out, \(t, nm) tibble(table = nm, column = names(t))) |> list_rbind() |>
  left_join(concepts |> select(column = concept, description = domain, unit = unit_target, terminag), by = "column") |>
  left_join(derived_desc |> rename(d2 = description, u2 = unit), by = "column") |>
  mutate(description = coalesce(d2, if_else(is.na(description), NA, paste("concept, domain:", description))),
         unit = coalesce(u2, unit)) |>
  select(table, column, description, unit, terminag)
write_csv(out_dict, agh_path("agh_curated", "output_dictionary.csv"), na = "")

qc_values <- cur |> filter(kind == "num") |>
  summarise(n = n(), n_na = sum(is.na(value_num)),
            p01 = quantile(value_num, 0.01, na.rm = TRUE), median = median(value_num, na.rm = TRUE),
            p99 = quantile(value_num, 0.99, na.rm = TRUE), max = suppressWarnings(max(value_num, na.rm = TRUE)),
            unknown_unit = sum(unit_status %in% "unknown_unit"), .by = c(source_id, concept))
write_csv(qc_values, agh_path("agh_curated", "qc_value_summary.csv"), na = "")
write_csv(vm |> filter(is.na(std) | !as_lgl(checked) %in% TRUE), agh_path("agh_curated", "qc_unchecked_labels.csv"), na = "")
write_csv(um |> filter(is.na(factor)), agh_path("agh_curated", "qc_unknown_units.csv"), na = "")

say("\nLevel tables:")
print(imap(out, \(t, nm) tibble(table = nm, rows = nrow(t), cols = ncol(t), sources = n_distinct(t$source_id))) |> list_rbind())
say("Labels without a reviewed std: %d | units without factor: %d", sum(!as_lgl(vm$checked) %in% TRUE), sum(is.na(um$factor)))
