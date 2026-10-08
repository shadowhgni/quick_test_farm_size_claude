# =============================================================================
# agh_utils.R — shared helpers for the agricultural harmonisation ETL (agh)
#
# Provenance tags used in comments throughout the workflow:
#   [verified] checked against the source while writing (Oct 2026)
#   [recall]   from training knowledge, not checked; confirm before relying on it
#   [assumed]  a design choice or default you may want to change
# =============================================================================

library(dplyr)
library(tidyr)
library(readr)
library(purrr)
library(stringr)
library(tibble)
library(forcats)
# Other packages, always called as pkg::fun : haven, xml2, httr2, readxl, jsonlite

# -----------------------------------------------------------------------------
# Paths. The project root holds agh_scripts/ and every agh_* folder.
# run_all.R sets options(agh.root = ".."); a step run on its own uses the same
# option, which survives rm(list = ls()).
# -----------------------------------------------------------------------------
agh_root <- function() getOption("agh.root", "..")
agh_path <- function(...) {
  p <- file.path(agh_root(), ...)
  d <- if_else(str_detect(basename(p), "\\.[A-Za-z0-9]{1,5}$"), dirname(p), p)
  for (dd in unique(d)) dir.create(dd, recursive = TRUE, showWarnings = FALSE)
  p
}
script_dir <- function() getOption("agh.scripts", ".")

# Copy any default config file the user does not have yet (never overwrites)
init_config <- function() {
  defaults <- list.files(file.path(script_dir(), "config_defaults"), full.names = TRUE)
  for (f in defaults) {
    dest <- agh_path("agh_config", basename(f))
    if (!file.exists(dest)) {
      file.copy(f, dest)
      message("  created agh_config/", basename(f), " from defaults")
    }
  }
}

# Config CSVs may start with comment lines ("# ..."); only leading ones are
# skipped, so "#" inside values (regex, column stems) is safe.
read_cfg <- function(name, dir = "agh_config") {
  path <- agh_path(dir, name)
  lines <- readLines(path, encoding = "UTF-8", warn = FALSE)
  skip <- which(!str_detect(lines, "^#"))[1] - 1
  read_csv(path, skip = skip, col_types = cols(.default = "c"), show_col_types = FALSE,
           na = c("", "NA")) |>
    mutate(across(everything(), str_trim))
}

# Cached download; delete the cached file to force a refresh
fetch <- function(url, dest, quiet = TRUE) {
  if (!file.exists(dest) || file.size(dest) == 0) {
    ok <- tryCatch({
      utils::download.file(url, dest, mode = "wb", quiet = quiet)
      TRUE
    }, error = \(e) FALSE, warning = \(w) FALSE)
    if (!ok) {
      if (file.exists(dest)) unlink(dest)
      return(NA_character_)
    }
  }
  dest
}

normalise <- function(x) {
  x |> str_to_lower() |> stringi_ascii() |> str_replace_all("[-_/.:()\\[\\]]", " ") |> str_squish()
}
# Accent folding with base R only (é -> e), so French/Portuguese labels match
stringi_ascii <- function(x) {
  out <- iconv(x, from = "UTF-8", to = "ASCII//TRANSLIT", sub = "")
  if_else(is.na(out), x, out)
}

as_lgl <- function(x) {
  y <- normalise(as.character(x))
  case_when(
    y %in% c("1", "yes", "y", "true", "t", "oui", "sim", "si", "ndiyo") ~ TRUE,
    y %in% c("0", "2", "no", "n", "false", "f", "non", "nao", "não", "hapana") ~ FALSE,
    .default = NA
  )
}
num <- function(x) suppressWarnings(as.numeric(x))

# Stem of a repeated column: "crop_name_3" -> "crop_name_#", "s4q2_1" -> "s4q2_#".
# A separator is required, so question codes such as ag_d36 are not stems.
var_stem <- function(x) str_replace(x, "([_.])(\\d{1,2})$", "\\1#")

# -----------------------------------------------------------------------------
# Data files: list and read, inside zips or folders
# -----------------------------------------------------------------------------
data_exts <- "\\.(dta|sav|csv|tsv|txt|xlsx|xls|rds|parquet)$"

# Inventory of data files under a path (folder, zip, or single file)
list_data_files <- function(path) {
  if (is.na(path) || !file.exists(path)) return(tibble(container = character(), member = character()))
  if (dir.exists(path)) {
    f <- list.files(path, recursive = TRUE, full.names = TRUE)
    zips <- f[str_detect(str_to_lower(f), "\\.zip$")]
    plain <- f[str_detect(str_to_lower(f), data_exts)]
    bind_rows(tibble(container = plain, member = NA_character_),
              map(zips, list_data_files) |> list_rbind())
  } else if (str_detect(str_to_lower(path), "\\.zip$")) {
    m <- utils::unzip(path, list = TRUE)$Name
    inner_zip <- m[str_detect(str_to_lower(m), "\\.zip$")]
    if (length(inner_zip) > 0) message("  note: ", basename(path), " contains nested zips; extract them first: ",
                                       paste(head(inner_zip, 3), collapse = ", "))
    tibble(container = path, member = m[str_detect(str_to_lower(m), data_exts)])
  } else {
    tibble(container = path, member = NA_character_)
  }
}

file_key <- function(x) x |> basename() |> str_to_lower() |> str_remove(data_exts)

# Read one data file (optionally a zip member), all columns or a selection.
# Labelled (Stata/SPSS) columns come back as two columns: code and "<var>__lbl".
read_any <- function(container, member = NA, cols = NULL) {
  f <- if (is.na(member)) container else read_any_path(container, member)
  ext <- str_to_lower(str_extract(f, "[^.]+$"))
  pick <- \(df) if (is.null(cols)) df else select(df, any_of(cols))
  df <- switch(ext,
    dta  = haven::read_dta(f, col_select = if (is.null(cols)) everything() else any_of(cols)),
    sav  = haven::read_sav(f, col_select = if (is.null(cols)) everything() else any_of(cols)),
    csv  = read_csv(f, col_types = cols(.default = "c"), show_col_types = FALSE) |> pick(),
    tsv  = , txt = read_tsv(f, col_types = cols(.default = "c"), show_col_types = FALSE) |> pick(),
    xlsx = , xls = readxl::read_excel(f, col_types = "text") |> pick(),
    rds  = readRDS(f) |> as_tibble() |> pick(),
    stop("Unsupported file type: ", f)
  )
  split_labelled(df)
}

digest_path <- function(x) {
  # short, filesystem-safe id for a container path
  paste0(str_remove(basename(x), "\\.zip$"), "_", sprintf("%08x", sum(utf8ToInt(x) * seq_along(utf8ToInt(x))) %% .Machine$integer.max))
}

split_labelled <- function(df) {
  lab_cols <- names(df)[map_lgl(df, haven::is.labelled)]
  for (v in lab_cols) {
    df[[paste0(v, "__lbl")]] <- as.character(haven::as_factor(df[[v]], levels = "labels"))
    df[[v]] <- as.character(haven::zap_labels(df[[v]]))
  }
  df |> mutate(across(!ends_with("__lbl"), as.character))
}

# -----------------------------------------------------------------------------
# Dictionary parsers. Each returns one common long format:
#   file, var, label, question, value_labels (tibble list-col: value, value_label)
# -----------------------------------------------------------------------------
dict_cols <- c("file", "var", "label", "question")

node_text <- function(nodes, xpath) {
  xml2::xml_find_first(nodes, xpath) |> xml2::xml_text() |> str_squish()
}

# DDI Codebook 2.5 (World Bank / NADA exports). Element paths are those used in
# the PFP-N workflow, which parsed the Malawi IHS exports on the user's machine.
parse_ddi <- function(path) {
  doc <- xml2::read_xml(path) |> xml2::xml_ns_strip()
  files <- xml2::xml_find_all(doc, "//fileDscr")
  file_tbl <- tibble(
    file_id   = xml2::xml_attr(files, "ID"),
    file      = node_text(files, "./fileTxt/fileName") |> str_remove(data_exts),
    file_desc = node_text(files, "./fileTxt/fileCont")
  )
  vars <- xml2::xml_find_all(doc, "//dataDscr/var")
  if (length(vars) == 0) {
    return(list(meta = ddi_meta(doc), dict = tibble(file = character(), var = character(),
                label = character(), question = character(), file_desc = character(), value_labels = list())))
  }
  cats <- map(vars, \(v) {
    cg <- xml2::xml_find_all(v, "./catgry")
    if (length(cg) == 0) return(NULL)
    tibble(value = node_text(cg, "./catValu"), value_label = node_text(cg, "./labl"))
  })
  dict <- tibble(
    file_id  = xml2::xml_attr(vars, "files") |> word(1),
    var      = xml2::xml_attr(vars, "name"),
    label    = node_text(vars, "./labl"),
    question = node_text(vars, "./qstn/qstnLit"),
    value_labels = cats
  ) |>
    left_join(file_tbl, by = "file_id") |>
    select(file, var, label, question, file_desc, value_labels)
  list(meta = ddi_meta(doc), dict = dict)
}

ddi_meta <- function(doc) {
  tibble(
    title   = node_text(doc, "//stdyDscr/citation/titlStmt/titl"),
    idno    = node_text(doc, "//stdyDscr/citation/titlStmt/IDNo"),
    country = node_text(doc, "//stdyDscr/stdyInfo/sumDscr/nation"),
    years   = paste(unique(na.omit(xml2::xml_text(xml2::xml_find_all(doc, "//stdyDscr/stdyInfo/sumDscr/collDate/@date")) |>
                                 str_sub(1, 4))), collapse = "-")
  )
}

# XLSForm (ODK / SurveyCTO / KoBo, e.g. LCAS module forms)
parse_xlsform <- function(path, file_name = NULL) {
  survey <- readxl::read_excel(path, sheet = "survey", col_types = "text")
  lab_col <- names(survey)[str_detect(str_to_lower(names(survey)), "^label")][1]
  choices <- tryCatch(readxl::read_excel(path, sheet = "choices", col_types = "text"), error = \(e) NULL)
  ch_lab  <- if (!is.null(choices)) names(choices)[str_detect(str_to_lower(names(choices)), "^label")][1] else NA

  sv <- survey |>
    transmute(type = str_squish(type), var = name, label = .data[[lab_col]]) |>
    mutate(
      group = accumulate(seq_along(type), \(acc, i) {
        t <- type[i]
        if (is.na(t)) return(acc)
        if (str_detect(t, "^begin[ _](repeat|group)")) c(acc, var[i])
        else if (str_detect(t, "^end[ _](repeat|group)")) head(acc, -1)
        else acc
      }, .init = character()) |> tail(-1) |> map_chr(\(g) paste(g, collapse = "/")),
      list_name = str_match(type, "^select_(?:one|multiple)\\s+(\\S+)")[, 2]
    ) |>
    filter(!is.na(var), !str_detect(coalesce(type, ""), "^(begin|end)[ _]|^note$|^calculate$"))

  vl <- if (!is.null(choices)) {
    choices |> transmute(list_name, value = name, value_label = .data[[ch_lab]]) |>
      nest(value_labels = c(value, value_label))
  } else tibble(list_name = character(), value_labels = list())

  sv |>
    left_join(vl, by = "list_name") |>
    transmute(file = file_name %||% str_remove(basename(path), "\\.xlsx?$"),
              var, label, question = NA_character_, file_desc = group, value_labels)
}

# Generic table dictionary (csv / xlsx): columns detected by name.
# Accepts one row per variable; optional columns file, values/codes.
parse_table_dict <- function(path, file_name = NULL) {
  d <- if (str_detect(str_to_lower(path), "\\.xlsx?$")) readxl::read_excel(path, col_types = "text")
       else read_csv(path, col_types = cols(.default = "c"), show_col_types = FALSE)
  nm <- str_to_lower(names(d))
  pick <- \(pat) names(d)[str_detect(nm, pat)][1]
  c_var  <- pick("^(name|var|variable|variable_name|column|field|varname)$") %|% pick("name|var")
  c_lab  <- pick("^(label|description|definition|desc|variable_label)$") %|% pick("label|descr|defin")
  c_file <- pick("^(file|table|dataset|module|sheet)$")
  c_q    <- pick("question")
  if (is.na(c_var)) stop("Could not find a variable-name column in ", path, ". Rename it to 'name'.")
  tibble(
    file = if (!is.na(c_file)) d[[c_file]] else (file_name %||% NA_character_),
    var = d[[c_var]],
    label = if (!is.na(c_lab)) d[[c_lab]] else NA_character_,
    question = if (!is.na(c_q)) d[[c_q]] else NA_character_,
    file_desc = NA_character_,
    value_labels = list(NULL)
  ) |> filter(!is.na(var))
}
`%|%` <- function(a, b) if (is.na(a)) b else a

# terminag-coded data (e.g. Carob): dictionary = terminag variables table
parse_terminag_dict <- function(terminag_vars, data_cols, file_name) {
  tibble(file = file_name, var = data_cols) |>
    left_join(terminag_vars |> select(var = name, label = description, unit), by = "var") |>
    transmute(file, var, label = if_else(is.na(unit) | unit == "", label, paste0(label, " [", unit, "]")),
              question = NA_character_, file_desc = "terminag", value_labels = list(NULL))
}

# No dictionary: read labels from the data itself (Stata/SPSS carry them)
parse_from_data <- function(container, member = NA) {
  f <- container
  if (!is.na(member)) f <- read_any_path(container, member)
  ext <- str_to_lower(str_extract(f, "[^.]+$"))
  df <- switch(ext,
    dta = haven::read_dta(f, n_max = 0),
    sav = haven::read_sav(f, n_max = 0),
    read_csv(f, n_max = 0, col_types = cols(.default = "c"), show_col_types = FALSE))
  labs <- map_chr(df, \(x) attr(x, "label", exact = TRUE) %||% NA_character_)
  vls  <- map(df, \(x) {
    l <- attr(x, "labels", exact = TRUE)
    if (is.null(l)) NULL else tibble(value = as.character(unname(l)), value_label = names(l))
  })
  tibble(file = file_key(f), var = names(df), label = unname(labs), question = NA_character_,
         file_desc = NA_character_, value_labels = unname(vls))
}

read_any_path <- function(container, member, cache_dir = agh_path("agh_extract", "unzipped")) {
  exdir <- file.path(cache_dir, digest_path(container))
  dest <- file.path(exdir, member)
  if (!file.exists(dest)) utils::unzip(container, files = member, exdir = exdir)
  dest
}

# terminag (variables + values) from the GitHub zip [verified layout:
# variables/variables_<group>.csv, values/values_<name>.csv, branch main]
load_terminag <- function() {
  zip <- fetch("https://github.com/controvoc/terminag/archive/refs/heads/main.zip",
               agh_path("agh_meta", "raw", "terminag-main.zip"))
  if (is.na(zip)) {
    warning("terminag download failed; concept targets will not be checked")
    return(list(vars = tibble(name = character(), description = character(), unit = character()),
                values = list()))
  }
  exdir <- agh_path("agh_meta", "raw", "terminag")
  utils::unzip(zip, exdir = exdir, overwrite = TRUE)
  root <- file.path(exdir, "terminag-main")
  rd <- \(dir) {
    ff <- list.files(file.path(root, dir), pattern = "\\.csv$", full.names = TRUE)
    names(ff) <- basename(ff) |> str_remove(paste0("^", dir, "_")) |> str_remove("\\.csv$")
    map(ff, \(f) read_csv(f, col_types = cols(.default = "c"), show_col_types = FALSE))
  }
  vars <- rd("variables") |> list_rbind(names_to = "group") |> distinct(name, .keep_all = TRUE)
  list(vars = vars, values = rd("values"))
}

# Write csv with a header comment, for config templates
write_template <- function(df, path, header) {
  con <- file(path, "w")
  writeLines(paste0("# ", header), con)
  close(con)
  write_csv(df, path, append = TRUE, col_names = TRUE, na = "")
}

say <- function(...) message(sprintf(...))
