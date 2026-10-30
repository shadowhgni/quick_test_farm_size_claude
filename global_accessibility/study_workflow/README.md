# Study workflow: access change, land use and crop yields (v0.2)

This folder implements the study design in `../study_design/Study_design_access_landuse_yields.md`
from the travel-time store of `global_accessibility_v3.py`.

| File | Role |
| --- | --- |
| `access_effects_v01.py` | Data pipeline (Python, one file, resumable stages, same conventions as `global_accessibility_v3.py`) |
| `estimate_effects.R` | Estimation, Gate C, Gate V and the composite label (R; called by stage `estimate`, or run by hand) |
| `ee_ndvi_export.py` | Vegetation-vigour exports from Google Earth Engine for E2d (run on any machine with an Earth Engine account) |
| `dev/` | Tests (`python -m pytest dev -q`) and a panel simulator with a known effect |

## Run on the HPC

1. Finish a `global_accessibility_v3.py` run (stage `store`). For annual treatment, run it with
   `--years 2015 2016 … 2026 --weiss-years none`. The default 2015/2020/2026 run gives the long-term level.
2. Put this folder next to the GA results and set `GA_RESULTS` at the top of `access_effects_v01.py`.
   If you have both an annual run and a three-year run, list the annual run first.
3. Install R and its packages once: `install.packages(c("dplyr", "tidyr", "readr", "purrr", "tibble",
   "stringr", "jsonlite", "fixest", "did", "contdid", "nanoparquet"))`. Without `contdid`, the
   continuous-dose design is skipped.
4. In the JupyterLab terminal, from this folder (no SLURM, no shell scripts):
   ```
   python access_effects_v01.py --check-access
   python access_effects_v01.py --ga-results ../ga_results --dry-run
   nohup python -u access_effects_v01.py --ga-results ../ga_results > study_run.log 2>&1 &
   tail -f study_run.log
   ```

5. **Vegetation vigour (E2d, optional).** On a machine with an Earth Engine account:
   ```
   pip install earthengine-api
   earthengine authenticate
   python ee_ndvi_export.py --project <your-cloud-project> --dry-run      # checks the assets first
   python ee_ndvi_export.py --project <your-cloud-project> --sensor modis --years 2001-2024
   python ee_ndvi_export.py --project <your-cloud-project> --sensor s2 --years 2017-2024
   ```
   Then copy the `vigour_*.tif` files from Google Drive (folder `ae_ndvi`) to `study_workflow/ndvi_exports/`.
   Without them, stage `ndvi` logs that E2d is skipped and the rest runs. **This script has not been run
   against Earth Engine yet** (no account in development): start with `--dry-run`, which checks every asset
   and band name before any export.

Each stage resumes where it stopped. To rerun a stage, delete `ae_work/_done/<stage>`. Results go to
`ae_results/`:

- `tables/` holds Gate T, matching balance, panel summary, access check and the LSMS inventory.
- `panels/` holds the analysis files read by R.
- `estimates/` holds `estimates.csv`, with every coefficient and every failed model with its error, and `gate_c.csv`.
- `logs/` holds the run record, with the configuration and every download.

## Data sources

All of these are read by script without registration. Each was range-tested on 2026-10-28 from the
cloud sandbox (HTTP 206); the HPC must be checked with `check`.

| Use | Source | Notes |
| --- | --- | --- |
| Forest 2000, annual loss | Hansen GFC v1.13 (`GFC-2025-v1.13`, loss 2001–2025) | Loss from 2011 on was reprocessed in v1.13; v1.12 remains available (`HANSEN_VERSION`) |
| Annual cropland | GACED30, 2000–2024, 30 m (Zenodo 10.5281/zenodo.18199675) | **Deviation from the design:** GLAD annual cropland (2015–2024) is the design's primary choice, but no scriptable download was found. Use `CROPLAND_SOURCE = "glad_annual"` with tiles exported from Earth Engine |
| Rainfall | CHIRPS v3.0 annual, Africa | |
| Conflict | UCDP GED 26.1 | ACLED (`CONFLICT_SOURCE = "acled"`, credentials in environment variables) is experimental: its paging and country names were not tested |
| Dated road projects | AidData GeoGCDF v3.0.1 | Road geometry type not verified; the stage logs the geometry types it finds |
| Admin yields | HarvestStat Africa v1.2 (CSV and boundaries, joined on `fnid`) | Rows with `qc_flag` 0 only |
| LSMS-ISA | Harmonised panel v2.0 (Bentze & Wollburg; Zenodo 15774761) | Ethiopia, Malawi, Nigeria, Tanzania, Uganda; main season. Licence: Zenodo says CC0, the paper says CC BY-NC-ND 4.0, so do not redistribute |

## Revision 2 (v0.2, 2026-10-30)

These additions follow revision 2 of the study design. All thresholds marked "to approve" in the design are
configuration constants at the top of `access_effects_v01.py` (`REPL_MIN_LOSS_KM2`, `E2D_*`, `GATE_V_*`,
`COMPOSITE_SHIFT`, `CROPMIX_MIN_REPORT`).

- **Stage `landcover_alt`**, one pass over the Hansen tiles:
  - AFCD splits conversion into annual crops (cropland in GACED30 and AFCD) and tree crops (GACED30 but not AFCD, two consecutive years);
  - GLC_FCS30D v2 adds forest-to-cropland and forest-to-tree-crop transitions with its own dating, plus irrigated and orchard cropland;
  - Masolele 2024 (2020 file, cumulative) classifies the forest lost 2001–2020 by its land use around 2022;
  - JRC TMF transition subtypes cover the humid tropics, to 2025;
  - the Descals oil-palm planting year flags oil palm planted within 5 years of the loss;
  - it also builds the stable rainfed cropland mask for E2d.
- **Stage `cropmix` (E2e):**
  - HarvestStat crop area shares on a fixed crop set per unit: crops reported in at least ⅔ of the unit's years, and only years with all of them;
  - LSMS crop area shares per EA and wave;
  - Shannon diversity and share sold.
- **Stage `ndvi` (E2d):** reads the Earth Engine exports. Panels sample stable-cropland cells: at least 50% stable rainfed cropland, tree cover ≤ 10%, irrigated ≤ 5%.
  - MODIS gives the continuous 2001–2024 series (primary); Sentinel-2 (2017–2024) is the sensor check.
  - Gate V inputs (within-unit NDVI–yield correlation and sensor correlation) go to `panels/gate_v_inputs.csv`.
- **R:**
  - new outcomes for E1 (annual and tree-crop conversion), E1c, E2d and E2e;
  - `gate_v.csv`;
  - the composite label in `gate_c.csv` when access shifts crop shares (BH q ≤ 0.10 and ≥ 5 points).

| Source (revision 2) | Use | Notes |
| --- | --- | --- |
| AFCD 2000–2022 (Zenodo 14920706) | Annual-crop conversion, stable cropland | 23 Africa-wide files, about 1 GB each; only 2014–2022 are downloaded |
| GLC_FCS30D v2 (Zenodo 15063683) | Cross-checks, irrigated and orchard cropland | 8 zips for Africa, tens of GB, read in place |
| Masolele 2024 (Zenodo 11065705) | E1c classes | One file (2020, cumulative), about 550 MB; non-commercial data agreement |
| JRC TMF v1_2025 transition subtypes | E1c cross-check, humid tropics | 10° tiles from the JRC server (no range requests) |
| Descals 2024 oil palm (Zenodo 13379129) | Oil palm planted after loss | 146 MB zip |
| MODIS MOD13Q1, Sentinel-2, GLC_FCS30D, Hansen in Earth Engine | E2d | Via `ee_ndvi_export.py` |

## What is implemented, and what is not

**Implemented** (tested on the regional CI store with synthetic stand-ins for the downloads, and on
simulated panels with a known effect):

- **Phase 0 treatment:** per 30″ cell, it computes:
  - travel-time series per version (road-only, total) and layer;
  - gain and loss events with the approved thresholds;
  - event classes: local, burst (placebo) or remote, from the OSM road events within 10 km;
  - distance to the nearest road change, used for the spatial bands.
- **Phase 1 land use:** forest at baseline (30% and 10%), annual loss, annual cropland, stable cropland,
  conversion (loss in *t*, not cropland in *t*−1, cropland in *t*..*t*+2), and new cropland from other
  vegetation.
- **Covariates:** rainfall per year and conflict events per 0.1° block.
- **Yields:**
  - Admin units: cropland-weighted unit treatment, falling back to population weights.
  - LSMS enumeration areas: displaced EA points, cropland-weighted access within 5 km (equal weights where there is no cropland), ratio-of-sums yields, approved minimum households and plots, mechanism shares. Intercropped plots are kept apart.
- **Panels:**
  - sampled E1 cell panel with sampling weights;
  - coarsened exact matching with a balance table;
  - spatial bands;
  - E3 long differences for cells, admin units and EAs (consecutive survey waves).
- **Estimation:**
  - Callaway–Sant'Anna with not-yet-treated, never-treated, matched and band controls;
  - burst placebo;
  - Sun–Abraham;
  - TWFE, for comparison only;
  - `contdid` continuous dose;
  - long differences with Conley errors (50 km).
  - Gate C (criteria 1–4) and Benjamini–Hochberg control across crops and outcomes.

**Not implemented yet:**

- **Imagery confirmation of road dates** (Valle et al. 2024 method, scored against Slagter et al. 2024).
  Gate T therefore reports only the burst criterion and agreement with dated projects. The confirmed
  share is left empty, and no zone can fully pass Gate T until this is added.
- **Agro-ecological zones:** Gate T is computed per country.
- **EHCVM countries:** only inventoried from `sources.csv`. The 2018 harvest module has no kg
  conversion in the files, and no public conversion table was found.
- **Other covariates:** logging concessions, protected areas, prices, temperature and soils. TMF is
  used only for E1c.
- **Not built:** the optional NDVI→yield model (Gate B), synthetic control for single projects, and the
  least-cost-route instrument.
- **Not yet validated:**
  - **E2d season windows** come from a MODIS climatology per pixel rather than per agro-ecological zone. No
    zone layer is in the workflow yet; the window is still fixed before 2015.
  - **The Earth Engine export** has not been run.

**Checks still owed by the author:**

- **LSMS wave years:** `LSMS_WAVE_YEARS` gives the harvest year of each harmonised-panel wave. It was
  inferred from the survey years, not read from the panel documentation.
- **Uganda and Tanzania coordinates:** missing in the harmonised panel for Uganda from 2013/14 and for
  movers in Tanzania waves 4–5. Those EAs take their coordinates from earlier waves.
- **ACLED:** run once with credentials and compare event counts with UCDP before using ACLED.
