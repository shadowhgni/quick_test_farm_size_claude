<div align="center">

# 🌾 agh — Agricultural Harmonisation ETL

**One pipeline to harmonise LSMS, Carob, LCAS, RHoMIS and other farm-household data at household, plot, plot-crop, input and livestock level**

![R](https://img.shields.io/badge/R-%E2%89%A54.3-276DC3?logo=r) ![vocabulary](https://img.shields.io/badge/vocabulary-terminag-2E7D32) ![licence](https://img.shields.io/badge/licence-GNU%20GPL-blue)

</div>

---

## 📋 Overview

| | |
|---|---|
| **What it does** | Reads any number of datasets and their data dictionaries. It tags variables with harmonised *concepts*, extracts the ones you approve and applies explicit curation rules (recoding, units, TLU, areas, rates, plausibility flags). It then writes tidy tables you can subset freely. |
| **What you provide** | For each dataset: a path to the data and a path to its dictionary. Nothing else is mandatory. |
| **Dictionary formats** | DDI Codebook 2.5 (World Bank and national NADA catalogs, including older Nesstar exports), XLSForm (LCAS, ODK, SurveyCTO, KoBo), CSV/Excel tables (RHoMIS), terminag (Carob), or labels embedded in `.dta`/`.sav` files. |
| **Data formats** | `.dta`, `.sav`, `.csv`, `.tsv`, `.xlsx`, `.rds`, inside folders or zip files. |
| **Domains covered** | Keys, location and weights, household, land and plot (area, land use, fallow, tenure, irrigation, soil, slope, erosion control), crops (harvest, area share, yield, variety, intercropping), inputs (inorganic fertilizer, organic amendments, herbicide, pesticide), livestock (heads per species → TLU). |
| **Not covered (by design)** | Labour. Its formats differ too much between surveys (per member, per activity, per visit) to curate cheaply. Add concepts later if needed. |
| **Tested on** | Mock data (automated, every push) and real data: the live World Bank and national NADA catalogs, and the Malawi IHS2 (2004) microdata. See [What has been tested](#-what-has-been-tested). |

---

## 🧭 How It Works

Retrieval and curation are kept apart. Steps 1–4 only **find and copy** values; they never convert or recode. Every decision that changes a value lives in a CSV map in `agh_config/` that the scripts **propose** and **you review**, as with `source_map` in the PFP-N analytics. Edit a map, re-run step 5, and the tables change; the data are not re-read.

```
 catalogs ──► 1 harvest codebooks ──► 2 one dictionary ──► 3 tag concepts ──► ✋ source_map.csv
                                                                                      │
 your data ───────────────────────────────────────────────────────────► 4 extract (raw values)
                                                                                      │
 ✋ value_map · unit_map · tlu_factors · qc_limits ──────────────────────► 5 curate ──► level tables
                ▲                                                                     │
                └──── agh_units_import.R (proposes unit factors from LSMS tables) ◄──┘
```

---

## 🚀 Quick Start

```r
# 1. Put the scripts in <project>/agh_scripts/ and set it as working directory
setwd("path/to/AG_HARMONISATION/agh_scripts")

# 2. First run: creates agh_config/ with defaults, harvests codebooks, tags variables,
#    writes agh_config/source_map.csv and PAUSES so you can curate it
source("run_all.R")

# 3. Register your datasets in agh_config/sources.csv, curate source_map.csv, re-run
source("run_all.R")

# 4. Review value_map.csv / unit_map.csv / qc_limits.csv; optionally import unit factors
source("agh_units_import.R")
agh_import_units("C:/data/lsms/ihs_seasonalcropconversion_factor_2020.dta",
                 sources = "MWI_IHS2_2004", region_map = c(central = "centre"),
                 basis = "IHS5 seasonal-crop factors, collected 2016/2019")
source("agh_05_curate.R")      # re-run step 5 only

# 5. Subset
source("agh_06_query.R")
agh_get("plot", country = "Malawi", cols = c("plot_area_m2", "OM_kg_ha"), add_hh = "TLU")
```

> ⏱️ The **first harvest** downloads every LSMS codebook (about 220 XML files, 670 MB), which takes a while; codebooks are cached. Parsing them all in step 2 also takes long (see [Known limitations](#-known-limitations)). To skip the harvest later, set `run_catalog <- FALSE` in `run_all.R`.

---

## 📁 Folder Architecture

The scripts live in `agh_scripts/`. Every other folder is **created by the scripts** one level up, in the project root (`options(agh.root = "..")` in `run_all.R`).

```
AG_HARMONISATION/                     ← project root (agh.root = ".." seen from agh_scripts/)
│
├── agh_scripts/                      ← YOU KEEP THESE · working directory
│   ├── run_all.R                     # runs steps 1–5 in order, then lists the tables
│   ├── agh_utils.R                   # paths, cache, readers, dictionary parsers
│   ├── agh_01_catalog.R              # step 1 · NADA catalogs → DDI codebooks
│   ├── agh_02_dictionary.R           # step 2 · every dictionary → one table
│   ├── agh_03_tag.R                  # step 3 · concepts → candidates, coverage, source_map template
│   ├── agh_04_extract.R              # step 4 · source_map → one long table (raw values)
│   ├── agh_05_curate.R               # step 5 · curation rules → level tables + QC
│   ├── agh_06_query.R                # helpers to subset the curated tables
│   ├── agh_units_import.R            # proposes unit_map rows from a conversion table (LSMS factor files)
│   ├── config_defaults/              # copied to agh_config/ on first run (never overwritten)
│   └── README.md
├── tests/                            # mock data + end-to-end test (also run by the GitHub Action)
│
├── agh_config/                       ← ✋ CURATED BY YOU · back it up
│   ├── sources.csv                   #   your datasets: data_path + dict_path
│   ├── catalogs.csv                  #   NADA catalogs to harvest
│   ├── concepts.csv                  #   concept catalogue (patterns, level, kind, unit, aggregation)
│   ├── source_map.csv                #   which variable plays which role (keep = TRUE)
│   ├── value_map.csv                 #   raw labels → standard values (crops, species, land use …)
│   ├── unit_map.csv                  #   raw units → conversion factors (per item / region, with basis)
│   ├── unit_defaults.csv             #   generic units used to pre-fill unit_map
│   ├── tlu_factors.csv               #   TLU per species (and per class, e.g. cattle:calf)
│   └── qc_limits.csv                 #   plausibility limits for qc_flag (flag only, never drop)
│
├── agh_meta/                         ← steps 1–3 (rebuildable)
│   ├── ddi/<server>_<id>.xml         #   harvested codebooks
│   ├── study_catalog.csv             #   every study found, per catalog
│   ├── dictionary.csv / .rds         #   all variables of all codebooks
│   ├── value_labels.csv              #   all value labels
│   ├── candidates.csv                #   variable × concept candidates
│   ├── coverage_by_study.csv         #   ⭐ which study documents which concept
│   ├── data_inventory.csv            #   data files found per registered source
│   ├── dict_vs_data.csv              #   dictionary files with / without data
│   └── unit_import_report.csv        #   what agh_units_import.R matched, and why not
│
├── agh_extract/                      ← step 4 (rebuildable)
│   ├── agh_long_raw.rds              #   raw values, keys, items, units
│   └── extract_log.csv
│
└── agh_curated/                      ← step 5 (rebuildable)
    ├── agh_hh.*  agh_plot.*  agh_plot_crop.*  agh_plot_input.*  agh_hh_animal.*
    ├── agh_long.rds                  #   curated long table
    ├── output_dictionary.csv         #   columns, units, terminag names
    └── qc_*.csv                      #   unchecked labels, unknown units, missing TLU, hhid conflicts, value summaries
```

> ⚠️ **Never delete `agh_config/` without a backup.** It holds every curation decision. Everything else can be rebuilt.

---

## ✏️ What You Edit

| file | when | what |
|---|---|---|
| `run_all.R` | once | `agh.root` (keep `".."` if the scripts sit in `agh_scripts/`), `run_catalog` |
| `sources.csv` | per dataset | one row per dataset (below) |
| `source_map.csv` | after step 3 | tick `keep = TRUE` on the variables to extract; fix roles ([Curating source_map](#curating-source_mapcsv)) |
| `value_map.csv` | after step 5 | check the suggested standard values; set `checked = TRUE` |
| `unit_map.csv` | after step 5 | fill or import local-unit factors; set `checked = TRUE` |
| `tlu_factors.csv`, `qc_limits.csv` | when needed | TLU factors; plausibility limits |
| `concepts.csv`, `catalogs.csv` | rarely | add concepts or catalogs |

**`sources.csv`** (created on first run with disabled examples):

| column | required | meaning |
|---|---|---|
| `source_id` | ✅ | your short name, e.g. `ETH_ESS4_2018` |
| `data_path` | ✅ | folder, zip, or single file. Use full paths with forward slashes (`C:/data/...`); relative paths start from `agh_scripts/`. |
| `dict_path` | ✅ | `nada:<server>:<id>` (a harvested codebook, e.g. `nada:wb:3818`), a `.xml` DDI, an XLSForm `.xlsx`, a folder of forms, a `.csv`/`.xlsx` dictionary (columns `name` + `label`, optional `file`), `terminag`, or `data` |
| `program`, `country`, `year` | | filled from the DDI when blank |
| `dict_format` | | detected when blank |
| `enabled` | | `FALSE` skips the row |

> 💡 Keep LSMS zips **as downloaded**: the scripts read members inside them. Nested zips (a zip inside a zip) must be extracted once by hand. Step 2 tells you if it finds one.

---

## 🔄 Pipeline

| step | script | reads | writes | you act? |
|---|---|---|---|---|
| 1 | `agh_01_catalog.R` | `catalogs.csv` | `agh_meta/ddi/`, `study_catalog.csv` | — |
| 2 | `agh_02_dictionary.R` | `sources.csv`, codebooks | `dictionary.*`, `data_inventory.csv`, `dict_vs_data.csv` | check `dict_vs_data.csv` |
| 3 | `agh_03_tag.R` | `concepts.csv` | `candidates.csv`, `coverage_by_study.csv`, **`source_map.csv`** | ✋ curate `source_map.csv` |
| 4 | `agh_04_extract.R` | `source_map.csv`, data | `agh_long_raw.rds`, `extract_log.csv` | — |
| 5 | `agh_05_curate.R` | maps, TLU, limits | level tables, **`value_map.csv`**, **`unit_map.csv`**, QC | ✋ review the maps, re-run step 5 |
| — | `agh_units_import.R` | a conversion table | proposed rows in **`unit_map.csv`** | ✋ review, re-run step 5 |
| — | `agh_06_query.R` | level tables | — | subset |

> ⏸️ When the workflow needs you (a new `source_map.csv` to curate, nothing ticked yet, a concept missing from `concepts.csv` …), `run_all.R` **pauses**: it prints a framed "Workflow paused after <step>" message with the instruction and ends without an error. Do what it says and run `run_all.R` again. Real errors (a file that cannot be read, a download that fails) still stop with an error.

### Step 1: harvesting codebooks

`catalogs.csv` ships with three entries:
- **`wb`**: the World Bank Microdata Library, collection `lsms`.
- **`datafirst`**, type `agm`: the DataFirst *African Government Microdata* collection. **Its entries are pointers, not surveys.** Each one describes a national statistics office catalog (Ghana, Kenya, Nigeria, Rwanda, Botswana, Tanzania). Step 1 reads each pointer's codebook and extracts the national catalog address. It then searches that catalog, keeping only titles that match an agriculture/household regex (editable).
- **`fao`**: disabled by default.

You can add any other NADA catalog as a row.

### Step 2: one dictionary

Every codebook (registered datasets and catalog-only studies) becomes one table of variables, labels, questions and value labels. **`dict_vs_data.csv`** shows, for each registered dataset, which dictionary files have a data file: all `matched` is what you want. Older World Bank (Nesstar) codebooks name files `sec_a.NSDstat` for data `sec_a.dta`; this is handled.

### Step 3: concepts and the coverage table

`concepts.csv` defines about 50 concepts. Each has:
- regex rules `pattern` / `also` / `exclude`, applied to the lower-cased, accent-folded text "name + label + question", in English and French;
- a `level`, a `kind` (`key`, `item`, `num`, `cat`, `lgl`, `unit`) and a target unit;
- an aggregation rule;
- the matching **terminag** name, checked at run time against the terminag repository.

Edit or add rows freely.

**`coverage_by_study.csv`** counts candidates per concept for *every* harvested codebook, including studies whose data you have not downloaded. Use it to decide which LSMS rounds are worth requesting for livestock, organic amendments or fallow.

### Curating `source_map.csv`

Only rows with `keep = TRUE` are extracted. The template pre-ticks unambiguous rows: one concept for the variable, and one variable for that concept in the file. **Review all of them**, and add rows the tagging missed (copy a row of the same file and change `var`, `concept`, `role`).

| column | use |
|---|---|
| `role` | `key` (hhid, parcel_id, plot_id, season), `item` (crop, animal, OM_type, fertilizer_type), `value`, `unit` |
| `var_regex` | wide repeats such as RHoMIS `crop_name_1..n` or IHS2 `o08a..e`: one capture group = repeat index (suggested automatically) |
| `rep` | side-by-side blocks, e.g. Malawi fertilizer application 1 (`ag_d39a/c/d`) = `1`, application 2 (`ag_d40a/c/d`) = `2` |
| `item_fixed` | a column about one item only, e.g. `animal:cattle` for "number of cattle owned" |
| `season_fixed` | for files that are one season (e.g. `rainy` for Malawi modules C–H) |
| `multiply` | numeric factor, e.g. `4046.8564224` for GPS areas in acres → m² |
| `data_file` | data file name when it differs from the dictionary's file name (common with XLSForms) |

Several variables mapped to one key are pasted together, e.g. `gardenid` + `plotid` → `1_2`.

> ⚠️ **`hhid` must identify one household within a source.** Surveys often carry several household numbers, and the template proposes all of them. In Malawi IHS2 (2004), `hhid` is numbered *within each enumeration area* (578 values for 11,280 households). The household id is `case_id`, which equals `psu` + the 3-digit `hhid` in every file. Map `case_id` (or `psu` + `hhid` as two key rows). The output column is always called `hhid`. Step 5 checks this: household values that conflict for one `hhid` (two weights, two districts) are listed in `agh_curated/qc_hhid_conflicts.csv` with a warning.

**Items listed without a value are kept.** A crop column with no harvest in the same file (e.g. IHS2 `o08a`–`o08e`, the crops grown on each plot, while the harvest is asked per household in module P) becomes a *presence* record: the plot–crop row exists, with no quantity. A roster that lists every crop with a harvest column is different: there, an empty harvest means the crop was not grown, and nothing is kept.

### Step 5: curation rules

**`value_map.csv`.** Every new label is appended with a **suggestion** and an empty `checked` column. Suggestions come from:
- terminag vocabularies (crop, animal, OM, fertilizer_type);
- rule sets in English, French and Portuguese for species, land use, tenure and sex.

Species may carry a class (`cattle:calf`), which `tlu_factors.csv` can price separately.

**`unit_map.csv`.** Generic units (kg, g, tonne, quintal, ha, acre, m²) are pre-filled. **Local units are left blank** (bags, ox carts, pails, heaps): their weight depends on the crop, its condition and the region.

| column | use |
|---|---|
| `item` | factor for one std item only (e.g. `local maize`) |
| `region` | factor for one region only, matched to the household's `adm1` std value |
| `factor`, `target` | value × factor = quantity in the target unit |
| `basis` | where the factor comes from, and any assumption made |
| `checked` | `TRUE` once you reviewed the row |

The most specific row wins: item + region > item > source > `*` (all sources).

**`agh_units_import.R`** proposes item and region rows from a published conversion table. Malawi, for example, ships `ihs_seasonalcropconversion_factor_2020.dta` (region × crop × unit × shelled/unshelled) and `ihs_treeconversion_factor_2020.dta` with IHS5. Ethiopia ships `ET_local_area_unit_conversion.dta` with the ESS. Run it after step 5, review the rows, then re-run step 5:

```r
source("agh_units_import.R")
f <- "C:/data/lsms/ihs_seasonalcropconversion_factor_2020.dta"
b <- "IHS5 seasonal-crop factors, collected 2016/2019"
rm <- c(central = "centre")                    # table region -> your households' adm1
agh_import_units(f, sources = "MWI_IHS2_2004", region_map = rm, basis = b)
# the survey did not record shelled/unshelled: your choice, per crop, written in basis
agh_import_units(f, "MWI_IHS2_2004", region_map = rm, basis = b,
                 items = "^(?!.*(groundnut|rice))", condition_default = "shelled")
agh_import_units(f, "MWI_IHS2_2004", region_map = rm, basis = b,
                 items = "groundnut|rice", condition_default = "unshelled")
```

| rule | detail |
|---|---|
| crops | matched by words: `local maize` = `MAIZE LOCAL`, `bean` = `BEANS`. If only varieties match (`groundnut` → `GROUNDNUT CG7`, `CHALIMBANA` …), their **median** is used and noted in `basis`. |
| units | same words, spaces ignored: `oxcart` = `OX-CART`, `pail large` = `PAIL (LARGE)` |
| condition | taken from the unit label (`oxcart unshelled`); else rows that are "not applicable"; else `condition_default` if you set it. Otherwise the pair is **left blank**. |
| region | kept per region; `region_map` renames table regions to your households' `adm1` values |
| other tables | set `item_col`, `unit_col`, `factor_col`, `region_col`, `condition_col` |

Every pair it could not match is listed with the reason in `agh_meta/unit_import_report.csv` ("item not in table", "unit not in table for this item", "condition not recorded …"). Rows already in `unit_map.csv` are never overwritten.

**`qc_limits.csv`.** Implausible values are **flagged, not dropped** (`qc_flag` in `plot`, `plot_crop`, `hh_animal` and `hh`). Several flags are joined with `; `.

| flag | table | default limit |
|---|---|---|
| `area_small` / `area_large` | plot | < 10 m² / > 100 ha |
| `fert_high`, `OM_high` | plot | > 1,000 / > 100,000 kg/ha |
| `yield_high` | plot_crop | > 30,000 kg/ha |
| `harvest_high` | plot_crop | > 20,000 kg per household (or plot) and crop; add rows per crop (`item`) to refine |
| `heads_high` | hh_animal | per species, e.g. 500 cattle, 200 pigs, 1,000 poultry |
| `TLU_high` | hh | > 100 TLU |
| `no_harvest_unit_factor` | plot_crop | a harvest reported in a unit without a factor yet |

**Derived variables:**
- plot area (GPS first, else reported) and its source;
- fallow flag;
- OM and fertilizer totals, per type and per ha (falls back to Carob's per-ha rates);
- crop area and yield (falls back to a reported yield);
- for each plot–crop row, `n_plots_crop_hh` (plots of the household growing that crop in the season) and `harvest_kg_hh` (the household-level harvest of that crop). **Nothing is attributed to a plot**; keep `n_plots_crop_hh == 1` to use `harvest_kg_hh` as that plot's harvest. Household-level harvest rows (no `plot_id`) carry the same two columns;
- TLU per household, and heads per species;
- farm, cropland and fallow hectares.

The `qc_*.csv` files list unreviewed labels, unknown units, species without a TLU factor, `hhid` conflicts and a summary of every numeric concept.

### Querying

```r
source("agh_06_query.R")
agh_tables()                                                     # rows per table and source
agh_get("plot_crop", crop = "maize", year_from = 2010, cols = c("harvest_kg", "yield_kg_ha"), complete = TRUE)
agh_get("plot_crop", n_plots_crop_hh = 1, cols = c("harvest_kg_hh", "plot_area_m2")) |>
  filter(!is.na(plot_id))                                        # crops grown on a single plot of the household
agh_get("plot", add_hh = c("TLU", "hh_weight", "latitude", "longitude"))
agh_coverage("plot")                                             # share of non-missing values per source
```

---

## ⚖️ Assumptions

Each assumption is also written where it applies (`basis` columns, file headers), so it travels with the data.

| topic | assumption | where to change it |
|---|---|---|
| Unit conversion factors | Where a survey round recorded no conversion factors (e.g. Malawi IHS2 2004), **factors published with a later round are used** (IHS5: collected 2016/2019). | `unit_map.csv` (`basis` of each row) |
| Shelled / unshelled | When a survey did not record the condition, it is a user choice. For Malawi IHS2: all grains **shelled**, except groundnut and rice (**unshelled**). | `condition_default` in `agh_units_import.R`; `unit_map.csv` |
| Crop varieties | A crop without variety (e.g. `groundnut`) takes the **median** factor of the table's varieties. | `unit_map.csv` |
| Plausibility limits | Most limits are judgement calls (`assumed` in `qc_limits.csv`); only the fertilizer limit comes from terminag. Rows are flagged, never dropped. | `qc_limits.csv` |
| TLU | Jahnke (1982) factors, as reported by Rothman-Ostrow et al. (2020), *Front. Vet. Sci.* 7:556788; species without a factor are left unconverted. | `tlu_factors.csv` |
| Household harvest vs plot | A household-level harvest is **not** split across plots. | your analysis (`n_plots_crop_hh`) |
| National NADA sites | Expose the same API as the World Bank catalog; failures are logged, not fatal. | `catalogs.csv` |

---

## ✅ What Has Been Tested

**Automated, on mock data** (every push; see below): an LSMS-like zip of labelled `.dta` files with its DDI, a French-labelled EHCVM-like codebook, a RHoMIS-like wide file with a CSV dictionary, a Carob-like terminag file, and a local server imitating the NADA endpoints, including an AGM pointer. 14 values are checked against hand calculations.

**On real data** (R 4.3.3, dplyr 1.1.4, haven 2.5.4; run locally, data not in the repository):

| part | result |
|---|---|
| Step 1, World Bank catalog | 169 LSMS codebooks harvested from the live site |
| Step 1, national catalogs via DataFirst AGM | Ghana, Kenya, Botswana and Tanzania catalogs answered (52 codebooks) |
| Steps 2–3, 5 real codebooks (Malawi IHS5, Ethiopia ESS4, Burkina Faso EHCVM, Nicaragua EMNV, Mali phone survey) | 14,575 variables, 1,743 candidates; stops for curation as designed |
| Steps 2–6, **Malawi IHS2 (2004) microdata** | 52 data files matched to the codebook; 11,280 households, 20,852 plots, 36,281 crop-on-plot records, 14,016 fertilizer applications, 11,520 household–species rows. Spot checks match the raw data (e.g. 2.5 acres → 10,117 m²) |
| Unit import, IHS5 tables on IHS2 | harvest values in kg: 18% → **88%** (26,860 of 30,584); median household harvest of local maize ≈ 300 kg, groundnut ≈ 85 kg |
| Flags on IHS2 | 4 `heads_high` (e.g. 9,500 pigs, an entry error), 3 `TLU_high`, 15 `harvest_high` |
| `hhid` check | mapping IHS2 `hhid` instead of `case_id` raises the warning (471 conflicting ids; households would have collapsed to 578) |

Real-data runs found and fixed: Nesstar file names (`.NSDstat`), the first run crashing without registered datasets, slow DDI parsing, crops per plot being dropped, and the ambiguous IHS2 household id.

---

## 🚧 Known Limitations

- **Step 2 is slow on a full harvest.** Parsing all ~220 LSMS codebooks (670 MB of XML) takes one to two hours and is not cached between runs. Parse only the studies you need (trim `study_catalog.csv`, or set `include_catalog <- FALSE` in step 2).
- **Concept tagging misses and over-proposes.** On IHS2 it missed the per-plot crops (labels say "in the last cropping season") and proposed harvest given to labourers as harvest. Review `source_map.csv`.
- **Food consumption** is not a concept yet, so food conversion tables (e.g. `ihs_foodconversion_factor_2020.dta`) are not used.
- **Region-specific factors** apply only where the table has the region; other regions stay unconverted (`no_harvest_unit_factor`).

---

## 🗄️ Obtaining the Data

All resources are free. Some require registration.

| resource | how |
|---|---|
| **LSMS / LSMS-ISA microdata** | [microdata.worldbank.org](https://microdata.worldbank.org/index.php/catalog/lsms): create a free account, open a study, go to *Get Microdata*, accept the terms, and download the **Stata** version. Codebooks are harvested automatically (no login). Conversion-factor files (e.g. Malawi IHS5 `ihs_*conversion_factor_2020.dta`, Ethiopia `ET_local_area_unit_conversion.dta`) come with the data. |
| **Survey documentation** | Each study's *Documentation* tab (Basic Information Document, questionnaires, manuals). Check it for conversion factors and for which household id is unique. |
| **National catalogs (via DataFirst AGM)** | [DataFirst AGM collection](https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/AGM) lists the national portals. Data access rules are set by each statistics office (often registration plus an application). |
| **RHoMIS** | 2024 release, 54,873 households in 35 countries, CC0 ([CGSpace record](https://cgspace.cgiar.org/items/7dcddcb2-d86c-42a9-ab74-16567944fae2)). The 2019 release is at [doi:10.7910/DVN/9M6EHS](https://doi.org/10.7910/DVN/9M6EHS). Register the processed data file and its variable description file in `sources.csv`. |
| **Carob** | Download the compiled datasets you need (as in the PFP-N workflow) and use `dict_path = terminag`. |
| **LCAS** | Module forms from the [LCAS documentation](https://systems-agronomy.github.io/lcas/). Use the data files' own column names if they differ from the forms (`data_file`). |
| **terminag** | Downloaded automatically from [github.com/controvoc/terminag](https://github.com/controvoc/terminag). |

---

## 🤖 Automated Test (GitHub Action)

`.github/workflows/agh-mock-test.yml` runs on every push or pull request that touches `agh_harmonisation/`, and can also be started by hand from the *Actions* tab (GitHub only offers that once the workflow file is on the default branch). It:
1. installs the R packages;
2. checks that every script parses;
3. builds the mock data (`tests/make_mock.R`);
4. starts a local mock NADA server and runs steps 1–5 with the curation a user would do;
5. checks 14 values computed by hand (`tests/run_mock_test.R`), e.g. GPS acres → m², OM kg/ha, two fertilizer applications, TLU with cattle classes, the Carob rate fallback, the yield and harvest flags, plots per crop and the hhid uniqueness check.

The outputs are kept as a downloadable artifact of each run. To run the same test locally, from `agh_harmonisation/`: `Rscript tests/run_mock_test.R` (step 1 is skipped unless `NADA_MOCK_URL` is set).

It never touches real microdata or the live catalogs, so it needs no login or secrets. It does need internet access to GitHub: steps 2–5 download terminag (`controvoc/terminag`) for the Carob labels and units, and without it the Carob checks fail.

---

## 📝 Citation

> ✏️ *Add the citation of this workflow (and its DOI, if deposited) here.*

The workflow was developed by D. Hougni (CIMMYT) with assistance from Claude AI (Anthropic, 2026).

## 📄 License

Code under the GNU GPL. Microdata and conversion-factor files remain subject to each provider's terms of use and are **not** redistributed with this workflow.

## 📞 Contact

* 🏢 **D. Hougni (CIMMYT):** d.hougni@cgiar.org
* 📧 **D. Hougni (Personal):** shadowhgni@yahoo.fr

<div align="center"><i>Last updated: October 2026</i></div>
