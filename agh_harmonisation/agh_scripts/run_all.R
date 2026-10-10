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

# A step may pause the workflow with an instruction (agh_halt: something to curate or fix
# in agh_config/). That is not an error: the instruction is printed and the run ends here.
paused <- NULL
for (s in steps) {
  message("\n==== ", s, " ====")
  paused <- tryCatch({
    source(file.path(getOption("agh.scripts"), s), local = new.env())
    NULL
  }, agh_halt = \(e) conditionMessage(e))
  # Step 3 writes (or adds to) agh_config/source_map.csv for new datasets: curate it first
  if (is.null(paused) && s == "agh_03_tag.R" && isTRUE(getOption("agh.map_created"))) {
    paused <- "Curate agh_config/source_map.csv (tick keep = TRUE on the variables to extract), then run run_all.R again."
  }
  if (!is.null(paused)) break
}

if (!is.null(paused)) {
  message("\n", strrep("-", 72), "\n  Workflow paused after ", s, ": nothing is wrong, you have something to do.\n\n  ",
          paused, "\n", strrep("-", 72))
} else {
  source(file.path(getOption("agh.scripts"), "agh_06_query.R"))
  print(agh_tables())
}
