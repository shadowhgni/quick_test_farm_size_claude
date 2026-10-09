rm(list = ls())
# =============================================================================
# run_all.R — agricultural harmonisation ETL (agh)
# Run from agh_scripts/:  setwd(".../agh_scripts"); source("run_all.R")
# =============================================================================

options(agh.root = "..",     # project root, seen from agh_scripts/ (all agh_* folders go there)
        agh.scripts = ".")   # where the scripts are

run_catalog <- TRUE   # step 1 downloads codebooks; cached, so later runs are quick
steps <- c(
  if (run_catalog) "agh_01_catalog.R",  # NADA catalogs -> agh_meta/ddi/*.xml
  "agh_02_dictionary.R",                # every codebook -> agh_meta/dictionary.*
  "agh_03_tag.R",                       # concepts -> candidates, coverage, source_map template
  "agh_04_extract.R",                   # source_map -> agh_extract/agh_long_raw.rds
  "agh_05_curate.R"                     # rules -> agh_curated/agh_<level>.*
)

for (s in steps) {
  message("\n==== ", s, " ====")
  source(file.path(getOption("agh.scripts"), s), local = new.env())
  # Step 3 creates agh_config/source_map.csv on the first run; stop so you can curate it
  if (s == "agh_03_tag.R" && isTRUE(getOption("agh.map_created"))) {
    stop("Curate agh_config/source_map.csv (keep = TRUE rows), then run again.")
  }
}

source(file.path(getOption("agh.scripts"), "agh_06_query.R"))
print(agh_tables())
