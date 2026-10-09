<div align="center">

# 🌾 agh — Agricultural Harmonisation ETL

**One pipeline to harmonise LSMS, Carob, LCAS, RHoMIS and other farm-household data at household, plot, plot-crop, input and livestock level**

![R](https://img.shields.io/badge/R-%E2%89%A54.3-276DC3?logo=r) ![tidyverse](https://img.shields.io/badge/tidyverse-native%20pipe%20%7C%3E-1A162D) ![vocabulary](https://img.shields.io/badge/vocabulary-terminag-2E7D32) ![licence](https://img.shields.io/badge/licence-GNU%20GPL-blue)

</div>

---

## 📋 Overview

| | |
|---|---|
| **What it does** | Reads any number of datasets and their data dictionaries. It tags variables with harmonised *concepts*, extracts the ones you approve and applies explicit curation rules (recoding, units, TLU, areas, rates). It then writes tidy tables you can subset freely. |
| **What you provide** | For each dataset: a path to the data and a path to its dictionary. Nothing else is mandatory. |
| **Dictionary formats** | DDI Codebook 2.5 (World Bank and national NADA catalogs), XLSForm (LCAS, ODK, SurveyCTO, KoBo), CSV/Excel tables (RHoMIS), terminag (Carob), or labels embedded in `.dta`/`.sav` files. |
| **Data formats** | `.dta`, `.sav`, `.csv`, `.tsv`, `.xlsx`, `.rds`, inside folders or zip files. |
| **Domains covered** | Keys, location and weights, household, land and plot (area, land use, fallow, tenure, irrigation, soil, slope, erosion control), crops (harvest, area share, yield, variety, intercropping), inputs (inorganic fertilizer, organic amendments, herbicide, pesticide), livestock (heads per species → TLU). |
| **Not covered (by design)** | Labour. Its formats differ too much between surveys (per member, per activity, per visit) to curate cheaply. Add concepts later if needed. |

---

## 🚀 Quick Start

```r
# 1. Put the scripts in <project>/agh_scripts/ and set it as working directory
setwd("path/to/AG_HARMONISATION/agh_scripts")

# 2. First run: creates agh_config/ with defaults, harvests codebooks, tags variables,
#    writes agh_config/source_map.csv and STOPS so you can curate it
source("run_all.R")

# 3. Register your datasets in agh_config/sources.csv, curate source_map.csv, re-run
source("run_all.R")

# 4. Subset
source("agh_06_query.R")
agh_get("plot", country = "Malawi", cols = c("plot_area_m2", "OM_kg_ha"), add_hh = "TLU")
```

> ⏱️ The **first harvest** downloads every LSMS codebook (one XML per study), which can take a while. Codebooks are cached. To skip the harvest later, set `run_catalog <- FALSE` in `run_all.R`.

---

## 📁 Folder Architecture

The scripts live in `agh_scripts/`. Every other folder is **created by the scripts** one level up, in the project root (`options(agh.root = "..")` in `run_all.R`).

```
AG_HARMONISATION/                     ← project root (agh.root = ".." seen from agh_scripts/)
│
├── agh_scripts/                      ← YOU KEEP THESE · working directory
│   ├── run_all.R                     # runs steps 1–5 in order
│   ├── agh_utils.R                   # paths, cache, readers, dictionary parsers
│   ├── agh_01_catalog.R              # step 1 · NADA catalogs → DDI codebooks
│   ├── agh_02_dictionary.R           # step 2 · every dictionary → one table
│   ├── agh_03_tag.R                  # step 3 · concepts → candidates, coverage, source_map template
│   ├── agh_04_extract.R              # step 4 · source_map → one long table
│   ├── agh_05_curate.R               # step 5 · curation rules → level tables + QC
│   ├── agh_06_query.R                # helpers to subset the curated tables
│   ├── agh_units_import.R            # propose unit_map rows from a conversion table (LSMS factor files)
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
│   ├── unit_map.csv                  #   raw units → conversion factors
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
│   └── dict_vs_data.csv              #   dictionary files with / without data
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

## ✏️ What You Must Edit

**1. `run_all.R`.** Keep `agh.root = ".."` if the scripts sit in `agh_scripts/` under the project root.

**2. `agh_config/sources.csv`** (created on first run with disabled examples). One row per dataset:

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
| 2 | `agh_02_dictionary.R` | `sources.csv`, codebooks | `dictionary.*`, `data_inventory.csv` | — |
| 3 | `agh_03_tag.R` | `concepts.csv` | `candidates.csv`, `coverage_by_study.csv`, **`source_map.csv`** | ✋ curate `source_map.csv` |
| 4 | `agh_04_extract.R` | `source_map.csv`, data | `agh_long_raw.rds` | — |
| 5 | `agh_05_curate.R` | maps, TLU, defaults | level tables, **`value_map.csv`**, **`unit_map.csv`**, QC | ✋ review the maps, re-run step 5 |

### Step 1: harvesting codebooks

`catalogs.csv` ships with three entries:
- **`wb`**: the World Bank Microdata Library, collection `lsms`.
- **`datafirst`**, type `agm`: the DataFirst *African Government Microdata* collection. **Its entries are pointers, not surveys.** Each one describes a national statistics office catalog (Ghana, Kenya, Nigeria, Rwanda, Botswana, Tanzania). Step 1 reads each pointer's codebook and extracts the national catalog address. It then searches that catalog, keeping only titles that match an agriculture/household regex (editable).
- **`fao`**: disabled by default.

You can add any other NADA catalog as a row.

### Step 3: concepts and the coverage table

`concepts.csv` defines about 50 concepts. Each has:
- regex rules `pattern` / `also` / `exclude`, applied to the lower-cased, accent-folded text "name + label + question", in English and French;
- a `level`, a `kind` (`key`, `item`, `num`, `cat`, `lgl`, `unit`) and a target unit;
- an aggregation rule;
- the matching **terminag** name, checked at run time against the terminag repository.

Edit or add rows freely.

**`coverage_by_study.csv`** counts candidates per concept for *every* harvested codebook, including studies whose data you have not downloaded. Use it to decide which LSMS rounds are worth requesting for livestock, organic amendments or fallow.

### Curating `source_map.csv`

Only rows with `keep = TRUE` are extracted. The template pre-ticks unambiguous rows: one concept for the variable, and one variable for that concept in the file. **Review all of them.**

| column | use |
|---|---|
| `role` | `key` (hhid, parcel_id, plot_id, season), `item` (crop, animal, OM_type, fertilizer_type), `value`, `unit` |
| `var_regex` | wide repeats such as RHoMIS `crop_name_1..n`: one capture group = repeat index (suggested automatically) |
| `rep` | side-by-side blocks, e.g. Malawi fertilizer application 1 (`ag_d39a/c/d`) = `1`, application 2 (`ag_d40a/c/d`) = `2` |
| `item_fixed` | a column about one item only, e.g. `animal:cattle` for "number of cattle owned" |
| `season_fixed` | for files that are one season (e.g. `rainy` for Malawi modules C–H) |
| `multiply` | numeric factor, e.g. `4046.8564224` for GPS areas in acres → m² |
| `data_file` | data file name when it differs from the dictionary's file name (common with XLSForms) |

Several variables mapped to one key are pasted together, e.g. `gardenid` + `plotid` → `1_2`.

> ⚠️ **`hhid` must identify one household within a source.** Surveys often carry several household numbers, and the template proposes all of them. In Malawi IHS2 (2004), `hhid` is numbered *within each enumeration area* (578 values for 11,280 households). The household id is `case_id`, which equals `psu` + the 3-digit `hhid` in every file. Map `case_id` (or `psu` + `hhid` as two key rows). The output column is always called `hhid`. Step 5 checks this: household values that conflict for one `hhid` (two weights, two districts) are listed in `agh_curated/qc_hhid_conflicts.csv` with a warning.

**Items listed without a value are kept.** A crop column with no harvest in the same file (e.g. IHS2 `o08a`–`o08e`, the crops grown on each plot, while the harvest is asked per household in module P) becomes a *presence* record: the plot–crop row exists, with no quantity. A roster that lists every crop with a harvest column is different: there, an empty harvest means the crop was not grown, and nothing is kept.

### Step 5: curation rules

- **`value_map.csv`.** Every new label is appended with a **suggestion** and an empty `checked` column. Suggestions come from:
  - terminag vocabularies (crop, animal, OM, fertilizer_type);
  - rule sets in English, French and Portuguese for species, land use, tenure and sex.

  Species may carry a class (`cattle:calf`), which `tlu_factors.csv` can price separately.
- **`unit_map.csv`.** Generic units (kg, g, tonne, quintal, ha, acre, m²) are pre-filled. **Local units are left blank** (bags, ox carts, heaps); fill them yourself.
  - Optional columns: `item` for crop-specific factors, `region` for factors that differ by region (matched to the household's `adm1` std value), and `basis` for where the factor comes from. The most specific row wins: item + region > item > source > `*`.
  - **`agh_units_import.R`** proposes these rows from a published conversion table, e.g. Malawi IHS5 `ihs_seasonalcropconversion_factor_2020.dta` (region × crop × unit × shelled/unshelled) or `ihs_treeconversion_factor_2020.dta`. Run it after step 5, review the rows (`checked` blank), then re-run step 5:

    ```r
    source("agh_units_import.R")
    agh_import_units("C:/data/lsms/ihs_seasonalcropconversion_factor_2020.dta",
                     sources = "MWI_IHS2_2004", concept = "harvest_qty",
                     region_map = c(central = "centre"),   # table region -> household adm1
                     basis = "IHS5 seasonal-crop factors, collected 2016/2019")
    ```

    It matches crops by words (`local maize` = `MAIZE LOCAL`; several varieties → median, noted), units with spaces ignored (`oxcart` = `OX-CART`) and the shelled/unshelled condition from the unit label. Anything ambiguous is left blank and explained in `agh_meta/unit_import_report.csv`. For example, a "50 kg bag" of maize when the survey did not record whether it was shelled: set `condition_default = "shelled"` (or `"unshelled"`) if you decide, restricted to some crops with `items` (a regex on the std item, e.g. `items = "maize"`), and the choice is written in `basis`. Other tables need their column names: `item_col`, `unit_col`, `factor_col`, `region_col`, `condition_col`.
- **Derived variables:**
  - plot area (GPS first, else reported);
  - fallow flag;
  - OM and fertilizer totals, per type and per ha (falls back to Carob's per-ha rates);
  - crop area and yield (falls back to a reported yield);
  - for each plot–crop row, `n_plots_crop_hh` (plots of the household growing that crop in the season) and `harvest_kg_hh` (the household-level harvest of that crop). Nothing is attributed to a plot; keep `n_plots_crop_hh == 1` to use `harvest_kg_hh` as that plot's harvest;
  - TLU per household;
  - farm, cropland and fallow hectares.
- **QC.**
  - Implausible values are **flagged, not dropped** (`qc_flag` in plot, plot_crop, hh_animal and hh). Limits are in **`agh_config/qc_limits.csv`**: plot area, fertilizer and OM per ha, yield, heads per species and TLU per household. Most are assumptions; revise them like the other maps.
  - `no_harvest_unit_factor` marks a harvest reported in a unit that has no factor yet.
  - The `qc_*.csv` files list unreviewed labels, unknown units, species without a TLU factor and `hhid` conflicts.

Edit the maps and re-run **step 5 only**. Data are not re-read.

### Querying

```r
source("agh_06_query.R")
agh_tables()                                                     # rows per table and source
agh_get("plot_crop", crop = "maize", year_from = 2010, cols = c("harvest_kg", "yield_kg_ha"), complete = TRUE)
agh_get("plot", add_hh = c("TLU", "hh_weight", "latitude", "longitude"))
agh_coverage("plot")                                             # share of non-missing values per source
```

---

## 🗄️ Obtaining the Data

All resources are free. Some require registration.

| resource | how |
|---|---|
| **LSMS / LSMS-ISA microdata** | [microdata.worldbank.org](https://microdata.worldbank.org/index.php/catalog/lsms): create a free account, open a study, go to *Get Microdata*, accept the terms, and download the **Stata** version. Codebooks are harvested automatically (no login). |
| **National catalogs (via DataFirst AGM)** | [DataFirst AGM collection](https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/AGM) lists the national portals. Data access rules are set by each statistics office (often registration plus an application). |
| **RHoMIS** | 2024 release, 54,873 households in 35 countries, CC0 ([CGSpace record](https://cgspace.cgiar.org/items/7dcddcb2-d86c-42a9-ab74-16567944fae2)). The 2019 release is at [doi:10.7910/DVN/9M6EHS](https://doi.org/10.7910/DVN/9M6EHS). Register the processed data file and its variable description file in `sources.csv`. |
| **Carob** | Download the compiled datasets you need (as in the PFP-N workflow) and use `dict_path = terminag`. |
| **LCAS** | Module forms from the [LCAS documentation](https://systems-agronomy.github.io/lcas/). Use the data files' own column names if they differ from the forms (`data_file`). |
| **terminag** | Downloaded automatically from [github.com/controvoc/terminag](https://github.com/controvoc/terminag). |

---

## ✅ What Has Been Tested

Tested in a sandbox (R 4.3.3, dplyr 1.1.4, stringr 1.5.1, haven 2.5.4) on **mock** data:
- an LSMS-like zip of labelled `.dta` files with its DDI;
- a French-labelled EHCVM-like codebook;
- a RHoMIS-like wide file with a CSV dictionary;
- a Carob-like terminag file;
- a local server imitating the NADA search and export endpoints, including an AGM pointer.

Values in the outputs were checked by hand (areas, OM and fertilizer rates, TLU).

| part | status |
|---|---|
| DDI parsing paths | same as the PFP-N workflow, which parsed the real Malawi IHS codebooks on your machine |
| NADA search endpoint and response shape (`result$found`, `result$rows`) | run against the live World Bank catalog: 169 LSMS codebooks harvested |
| National NADA sites (via AGM) | run against DataFirst's AGM pointers: Ghana, Kenya, Botswana and Tanzania catalogs answered (52 codebooks); failures are logged in `catalog_log.csv`, not fatal |
| Concept regexes | run on 5 real LSMS codebooks and the Malawi IHS2 (2004) data. Expect false positives and misses (e.g. IHS2 crops per plot, phrased "in the last cropping season", were missed); that is why `source_map.csv` exists |
| Unit conversion factors from another round | **assumption**: where a round recorded no factors (e.g. Malawi IHS2 2004), factors published with a later round (IHS5: `ihs_seasonalcropconversion_factor_2020`, collected 2016/2019) are applied. `agh_units_import.R` writes this in the `basis` of every row it adds |
| TLU factors | Jahnke (1982), as reported by Rothman-Ostrow et al. (2020), *Front. Vet. Sci.* 7:556788 |

---

## 🤖 Automated Test (GitHub Action)

`.github/workflows/agh-mock-test.yml` runs on every push or pull request that touches `agh_harmonisation/`, and can also be started by hand from the *Actions* tab (GitHub only offers that once the workflow file is on the default branch). It:
1. installs the R packages;
2. checks that every script parses;
3. builds the mock data (`tests/make_mock.R`);
4. starts a local mock NADA server and runs steps 1–5 with the curation a user would do;
5. checks 13 values computed by hand (`tests/run_mock_test.R`), e.g. GPS acres → m², OM kg/ha, two fertilizer applications, TLU with cattle classes, the Carob rate fallback, the yield flag, plots per crop and the hhid uniqueness check.

The outputs are kept as a downloadable artifact of each run. To run the same test locally, from `agh_harmonisation/`: `Rscript tests/run_mock_test.R` (step 1 is skipped unless `NADA_MOCK_URL` is set).

It never touches real microdata or the live catalogs, so it needs no login or secrets. It does need internet access to GitHub: steps 2–5 download terminag (`controvoc/terminag`) for the Carob labels and units, and without it the Carob checks fail.

---

## 📝 Citation

> ✏️ *Add the citation of this workflow (and its DOI, if deposited) here.*

The workflow was developed by D. Hougni (CIMMYT) with assistance from Claude AI (Anthropic, 2026).

## 📄 License

Code under the GNU GPL. Microdata remain subject to each provider's terms of use and are **not** redistributed with this workflow.

## 📞 Contact

* 🏢 **D. Hougni (CIMMYT):** d.hougni@cgiar.org
* 📧 **D. Hougni (Personal):** shadowhgni@yahoo.fr

<div align="center"><i>Last updated: October 2026</i></div>
