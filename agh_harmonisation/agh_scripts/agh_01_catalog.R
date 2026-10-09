rm(list = ls())
# =============================================================================
# agh_01_catalog.R — list studies on NADA catalogs and download their DDI codebooks
#
# Reads   agh_config/catalogs.csv
# Writes  agh_meta/study_catalog.csv   one row per study found (server, id, idno, title, country, years)
#         agh_meta/ddi/<server>_<id>.xml  DDI Codebook 2.5 exports (cached; delete to refresh)
#         agh_meta/catalog_log.csv     what worked / failed per server
#
# API facts:
#   [verified] search endpoint <base>/index.php/api/catalog/search, params ps, page,
#              collection, format=json; response $result$found and $result$rows
#              (as used by the CRAN package nadaverse 0.1.0)
#   [verified] DDI export <base>/index.php/metadata/export/<id>/ddi (link on the
#              World Bank and DataFirst study pages)
#   [recall]   row field names (id, idno, title, nation, year_start, year_end); the
#              code keeps whichever of them exist
#   [assumed]  national NADA sites expose the same API; older installations may not,
#              and those servers are logged as failed rather than stopping the run
# =============================================================================

source(file.path(getOption("agh.scripts", "."), "agh_utils.R"))
init_config()

ps_size     <- 100     # rows per API page
max_studies <- 5000    # safety cap per server
pause_sec   <- 0.3     # politeness delay between DDI downloads

ua <- "agh-harmonisation/0.1 (R httr2; research use)"

nada_search <- function(base, collection = NA, keyword = NA) {
  rows <- list(); page <- 1; found <- Inf
  while (length(rows) * ps_size < min(found, max_studies)) {
    req <- httr2::request(paste0(base, "/index.php/api/catalog/search")) |>
      httr2::req_url_query(ps = ps_size, page = page, format = "json") |>
      httr2::req_headers(`User-Agent` = ua, Accept = "application/json") |>
      httr2::req_retry(max_tries = 3) |>
      httr2::req_timeout(60)
    if (!is.na(collection)) req <- httr2::req_url_query(req, collection = collection)
    if (!is.na(keyword))    req <- httr2::req_url_query(req, sk = keyword)
    body <- httr2::req_perform(req) |> httr2::resp_body_string()
    res <- jsonlite::fromJSON(body, simplifyVector = TRUE, flatten = TRUE)$result
    found <- as.numeric(res$found %||% 0)
    if (found == 0 || is.null(res$rows) || length(res$rows) == 0) break
    rows[[page]] <- as_tibble(res$rows) |> mutate(across(everything(), as.character))
    if (nrow(rows[[page]]) < ps_size) break
    page <- page + 1
  }
  bind_rows(rows) |> tidy_rows()
}

tidy_rows <- function(r) {
  if (nrow(r) == 0) return(tibble(id = character(), idno = character(), title = character(),
                                  country = character(), year_start = character(), year_end = character()))
  r |>
    transmute(
      id         = .data[[intersect(c("id", "sid"), names(r))[1]]],
      idno       = if ("idno" %in% names(r)) idno else NA_character_,
      title      = if ("title" %in% names(r)) title else NA_character_,
      country    = if ("nation" %in% names(r)) nation else NA_character_,
      year_start = if ("year_start" %in% names(r)) year_start else NA_character_,
      year_end   = if ("year_end" %in% names(r)) year_end else NA_character_
    )
}

ddi_url <- function(base, id) sprintf("%s/index.php/metadata/export/%s/ddi", base, id)

# DataFirst AGM entries are study pages whose DDI names the national catalog URL
resolve_agm <- function(base, collection) {
  agm <- nada_search(base, collection)
  say("  %s: %d AGM pointer entries", collection, nrow(agm))
  map(seq_len(nrow(agm)), \(i) {
    f <- fetch(ddi_url(base, agm$id[i]), agh_path("agh_meta", "raw", sprintf("agm_%s.xml", agm$id[i])))
    if (is.na(f)) return(NULL)
    txt <- paste(readLines(f, warn = FALSE), collapse = " ")
    urls <- str_extract_all(txt, "https?://[^\"'<> ]+")[[1]] |> unique()
    cat_url <- urls[str_detect(urls, "/catalog") & !str_detect(urls, "datafirst")][1]
    if (is.na(cat_url)) return(NULL)
    tibble(server = paste0("agm_", str_to_lower(word(agm$idno[i], 1, sep = "-"))),
           base_url = str_remove(cat_url, "/(index\\.php/)?catalog.*$"),
           country = agm$country[i], agm_title = agm$title[i])
  }) |> compact() |> list_rbind()
}

# -----------------------------------------------------------------------------
# 1. Expand catalog list (AGM pointers -> national servers)
# -----------------------------------------------------------------------------
cats <- read_cfg("catalogs.csv") |> filter(as_lgl(enabled) %in% TRUE)

agm_rows <- cats |> filter(type == "agm")
national <- map(seq_len(nrow(agm_rows)), \(i) {
  tryCatch(resolve_agm(agm_rows$base_url[i], agm_rows$collection[i]),
           error = \(e) { warning("AGM resolution failed: ", conditionMessage(e)); NULL })
}) |> list_rbind()

if (nrow(national) > 0) {
  say("Resolved national catalogs:"); print(national)
  default_regex <- "agricultur|agri|household|menage|living|panel|lsms|integrated|harmoni|ehcvm|farm|crop|livestock|recensement|enquete"
  cats <- bind_rows(
    cats |> filter(type != "agm"),
    national |> transmute(server, base_url, collection = NA_character_, title_regex = default_regex,
                          type = "nada", enabled = "TRUE", notes = paste("via DataFirst AGM:", agm_title))
  )
}

# -----------------------------------------------------------------------------
# 2. Search each server
# -----------------------------------------------------------------------------
log <- list()
studies <- map(seq_len(nrow(cats)), \(i) {
  s <- cats[i, ]
  say("Searching %s (%s) ...", s$server, s$base_url)
  out <- tryCatch(nada_search(s$base_url, s$collection), error = \(e) e)
  if (inherits(out, "error")) {
    log[[s$server]] <<- tibble(server = s$server, base_url = s$base_url, status = "search_failed",
                               detail = conditionMessage(out), n = 0L)
    return(NULL)
  }
  if (!is.na(s$title_regex) && nrow(out) > 0) {
    out <- out |> filter(str_detect(normalise(title), s$title_regex))
  }
  log[[s$server]] <<- tibble(server = s$server, base_url = s$base_url, status = "ok", detail = NA, n = nrow(out))
  out |> mutate(server = s$server, base_url = s$base_url, .before = 1)
}) |> list_rbind()

write_csv(bind_rows(log), agh_path("agh_meta", "catalog_log.csv"), na = "")
if (is.null(studies) || nrow(studies) == 0) stop("No studies found on any server; see agh_meta/catalog_log.csv")

# -----------------------------------------------------------------------------
# 3. Download DDI codebooks (cached)
# -----------------------------------------------------------------------------
studies <- studies |>
  mutate(ddi_file = agh_path("agh_meta", "ddi", sprintf("%s_%s.xml", server, id)))

todo <- which(!file.exists(studies$ddi_file))
say("Downloading %d DDI codebooks (%d cached) ...", length(todo), nrow(studies) - length(todo))
for (k in seq_along(todo)) {
  i <- todo[k]
  ok <- fetch(ddi_url(studies$base_url[i], studies$id[i]), studies$ddi_file[i])
  if (k %% 25 == 0) say("  %d / %d", k, length(todo))
  Sys.sleep(pause_sec)
}
studies <- studies |> mutate(ddi_ok = file.exists(ddi_file) & file.size(ddi_file) > 500,
                             ddi_file = if_else(ddi_ok, ddi_file, NA_character_))

write_csv(studies, agh_path("agh_meta", "study_catalog.csv"), na = "")
write_csv(bind_rows(log), agh_path("agh_meta", "catalog_log.csv"), na = "")

say("\nStudies per server (DDI downloaded / found):")
print(studies |> summarise(found = n(), ddi = sum(ddi_ok), .by = server))
