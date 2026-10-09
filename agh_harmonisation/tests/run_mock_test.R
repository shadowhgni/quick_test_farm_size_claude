# =============================================================================
# run_mock_test.R — end-to-end test of the agh workflow on mock data
# Usage (from the agh_harmonisation/ folder):  Rscript tests/run_mock_test.R
# Optional: NADA_MOCK_URL=http://127.0.0.1:8765 also tests step 1 against a local
# server serving the files written to <root>/nada (see .github/workflows).
# Checks values computed by hand from the mock inputs.
# =============================================================================
suppressPackageStartupMessages({ library(dplyr); library(readr) })

repo   <- normalizePath(".")
root   <- Sys.getenv("AGH_TEST_ROOT", file.path(tempdir(), "agh_test"))
unlink(root, recursive = TRUE); dir.create(root, recursive = TRUE)
file.copy(file.path(repo, "agh_scripts"), root, recursive = TRUE)
scripts <- file.path(root, "agh_scripts")

source(file.path(repo, "tests", "make_mock.R"))   # uses `root`

dir.create(file.path(root, "agh_config"), showWarnings = FALSE)
write_csv(tibble(
  source_id = c("MWI_MOCK", "RHOMIS_MOCK", "CAROB_MOCK"), program = c("LSMS", "RHoMIS", "carob"),
  country = c("Malawi", "Kenya", "Kenya"), year = c("2019", "2020", "2021"),
  data_path = file.path(root, "data", c("lsms_mock.zip", "rhomis_processed.csv", "carob_mock.csv")),
  dict_path = c("nada:wb:9001", file.path(root, "data", "rhomis_dictionary.csv"), "terminag"),
  dict_format = NA, enabled = "TRUE", notes = "mock"), file.path(root, "agh_config", "sources.csv"), na = "")

run_step <- function(s) {
  message("\n==== ", s, " ====")
  old <- setwd(scripts); on.exit(setwd(old))
  options(agh.root = "..", agh.scripts = ".")
  source(s, local = new.env())
}
edit_cfg <- function(name, fun) {
  f <- file.path(root, "agh_config", name)
  hdr <- readLines(f, n = 1)
  d <- read_csv(f, skip = 1, col_types = cols(.default = "c"), show_col_types = FALSE) |> fun()
  writeLines(hdr, f); write_csv(d, f, append = TRUE, col_names = TRUE, na = "")
}

# ---- optional step 1 against a local mock NADA server ----------------------
nada <- Sys.getenv("NADA_MOCK_URL")
if (nzchar(nada)) {
  cat_file <- file.path(root, "agh_config", "catalogs.csv")
  writeLines(c("server,base_url,collection,title_regex,type,enabled,notes",
               sprintf("mock,%s,lsms,,nada,TRUE,mock", nada),
               sprintf("agmtest,%s/agm,AGM,,agm,TRUE,mock", nada)), cat_file)
  run_step("agh_01_catalog.R")
  sc <- read_csv(file.path(root, "agh_meta", "study_catalog.csv"), show_col_types = FALSE)
  stopifnot("step 1: studies found on mock server" = nrow(sc) == 4,
            "step 1: AGM pointer resolved to a national server" = "agm_rwa" %in% sc$server,
            "step 1: DDI downloaded" = all(sc$ddi_ok))
  # restore the catalog used by the rest of the test
  file.copy(file.path(root, "agh_meta", "ddi", "mock_9001.xml"), file.path(root, "agh_meta", "ddi", "wb_9001.xml"), overwrite = TRUE)
  file.remove(cat_file)
  write_csv(read_csv(file.path(root, "agh_meta", "study_catalog.csv"), show_col_types = FALSE) |>
              filter(server == "mock", id == 9002), file.path(root, "agh_meta", "study_catalog.csv"))
}

# ---- steps 2-3, then the curation a user would do --------------------------
run_step("agh_02_dictionary.R")
run_step("agh_03_tag.R")
stopifnot("step 3: template written" = file.exists(file.path(root, "agh_config", "source_map.csv")))

edit_cfg("source_map.csv", \(m) m |> mutate(
  keep = case_when(
    source_id == "MWI_MOCK" & var %in% c("gardenid", "plotid") & concept == "plot_id" ~ "TRUE",
    source_id == "MWI_MOCK" & var %in% c("ag_d39a", "ag_d40a", "ag_d39c", "ag_d40c", "ag_d39d", "ag_d40d", "ag_d14") ~ "TRUE",
    source_id == "CAROB_MOCK" & var == "plot_id" & concept == "plot_id" ~ "TRUE",
    .default = keep),
  rep = case_when(var %in% c("ag_d39a", "ag_d39c", "ag_d39d") ~ "1",
                  var %in% c("ag_d40a", "ag_d40c", "ag_d40d") ~ "2", .default = rep),
  multiply = if_else(var == "ag_c04c", "4046.8564224", multiply),
  season_fixed = if_else(source_id == "MWI_MOCK" & file %in% c("ag_mod_c", "ag_mod_d", "ag_mod_g"), "rainy", season_fixed)))

run_step("agh_04_extract.R")
run_step("agh_05_curate.R")
edit_cfg("value_map.csv", \(v) v |> mutate(std = case_when(raw == "beans" ~ "common bean", raw == "groundnut cg7" ~ "groundnut", .default = std)))
edit_cfg("unit_map.csv", \(u) u |> mutate(factor = if_else(unit == "50 kg bag", "50", factor)))
run_step("agh_05_curate.R")

# ---- checks (values computed by hand from the mock inputs) -----------------
cur <- \(t) readRDS(file.path(root, "agh_curated", paste0("agh_", t, ".rds")))
near <- \(a, b) isTRUE(abs(a - b) < 1e-3)
p  <- cur("plot");  h <- cur("hh");  pc <- cur("plot_crop")
a1 <- p |> filter(source_id == "MWI_MOCK", hhid == "A1", plot_id == "1_1")
stopifnot(
  "GPS acres -> m2"            = near(a1$plot_area_m2, 1.2 * 4046.8564224),
  "OM kg/ha"                   = near(a1$OM_kg_ha, 200 / (1.2 * 4046.8564224 / 1e4)),
  "two fertilizer applications"= near(a1$fertilizer_amount_kg, 100),
  "fallow from land use"       = isTRUE(p$fallow_flag[p$hhid == "A1" & p$plot_id == "1_2"]),
  "TLU with cattle classes"    = near(h$TLU[h$hhid == "A1"], 5 * 0.7),
  "TLU from wide RHoMIS"       = near(h$TLU[h$hhid == "r1"], 4 * 0.7 + 20 * 0.01),
  "Carob OM rate fallback"     = near(p$OM_kg_ha[p$hhid == "c1" & p$plot_id == "p1"], 5000),
  "bag unit converted"         = near(pc$harvest_kg[pc$hhid == "A2"], 60000),
  "implausible yield flagged"  = grepl("yield_high", pc$qc_flag[pc$hhid == "A2"]),
  "large harvest flagged"      = grepl("harvest_high", pc$qc_flag[pc$hhid == "A2"]),
  "intercrop area not guessed" = all(is.na(pc$crop_area_m2[pc$hhid == "A1"])),
  "crop label recoded"         = "common bean" %in% pc$crop,
  "plots per crop counted"     = all(pc$n_plots_crop_hh[pc$hhid == "c1" & pc$crop == "maize"] == 2),
  "unique hhid not flagged"    = nrow(read_csv(file.path(root, "agh_curated", "qc_hhid_conflicts.csv"), show_col_types = FALSE)) == 0
)
message("\nAll checks passed.")
