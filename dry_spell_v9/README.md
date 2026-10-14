# Dry-spell risk by sowing date, v9

v9 now covers two things:
* **Seasons and dry spells** (steps 1-3 and 5): onset and demise from the **downloaded RADS files** (default) or computed from CHIRPS. Statistics of the dry spells inside each season: maps, PDFs, and summaries by latitude and zone.
* **Crop risk** (steps 4 and 6): sowing date × crop × cycle, and which stages the longest dry spell hits.

Each set of choices can run as a **named scenario** next to others, and step 7 maps what changes between them.

## What changed in this version (all settings in `v9_config.py`)

| Change | Settings |
|---|---|
| **Season source.** `"rads"` (default) reads `../chirps_africa/africa_RainyAndDrySeason.pentad.CHIRPS.YYYY.nc`. `"chirps"` computes the seasons from CHIRPS with the RADS method (v8 behaviour). | section G2: `SEASON_SOURCE`, `RADS_FILE_PATTERN` |
| **Seasons that cross the year.** In a RADS file the onset can come before the demise (season inside the year) or after it (the demise belongs to the previous season, e.g. seasons over 31 December). Every onset is paired with the next demise, whichever yearly file holds it, and the season is named by its onset year. The step 3 log reports both orders and the number of seasons crossing 31 December. | `v9_rads.py` |
| **Bimodal cells.** `"major"` (default) analyses the most important season (`MAJOR_SEASON_RULE`); with RADS, cells where RADS has no season (RADS masks two- and three-season cells) get the CHIRPS major season. `"mask"` leaves bimodal cells out entirely. | `BIMODAL_SEASON` |
| **Dry spell length.** A dry spell is at least `DRY_SPELL_MIN_DAYS` (10) days of < `DRY_MM` (1 mm). Steps 4 and 5 use it unless `MIN_SPELL_CROP` / `SPELL_STATS_MIN` are set explicitly. | section D |
| **Spells at the season edges.** By default, spells in the very first and very last 10 days of the season are not counted in step 5. Use 0 to count everything or 20 to drop more. A spell crossing that edge is clipped or dropped. The crop analysis (step 4) has its own setting, 0 by default. | `SPELL_STATS_EXCLUDE_FIRST/_LAST`, `SPELL_STATS_EDGE_POLICY`; `CROP_SPELL_EXCLUDE_FIRST/_LAST`, `CROP_SPELL_EDGE_POLICY` |
| **Steps renumbered.** Dry-spell statistics are now **step 5** (`v9_05_spell_stats.py`, `step05/`); the SSA aggregate of step 4 is now **step 6** (`v9_06_aggregate.py`, `step06/SSA/`). | - |
| **Scenarios.** `run_all.py --scenarios base chirps mask_bimodal excl0 excl20` runs steps 2-6 once per scenario into `dryspell_v9/<region>/<scenario>/`. Downloads are shared. | section L |
| **Step 7: comparison** (`v9_07_compare.py`). It lists the settings that differ and compares onset and rainfall demise season by season (same cell, same year). It draws maps of each key layer per scenario, with difference maps, and gathers the step 5 tables of every scenario into one file. | - |
| **CHIRPS from the v7 cache.** The v7 cache (`dryspell_v7/<region>/cache/`) can replace the download. Its grid is reused and only the days it lacks are downloaded. | `CHIRPS_V7_CACHE`, `CHIRPS_V7_CACHE_MODE` |
| **Download guard.** Step 1 now stops early when the CHIRPS server cannot be read: the first day fails, or more than 90% of the first 300 days fail. It exits with an error when more than 1% of the days are missing, so run_all never runs steps 2-6 on an empty record. Failed days are retried on every rerun (`--skip_failed` to leave them), and the 5 most frequent errors are written at the end of `dryspell_v9_data/download_<region>.log`. | `CHIRPS_MAX_MISSING_SHARE`, `CHIRPS_ABORT_AFTER` |
| **R back-up for the figures.** `R/plot_results.R` redraws the step 5 maps (from the GeoTIFFs), the PDFs (from the histogram CSVs) and the latitude profile. It can also map any folder of GeoTIFFs. | - |

Scenarios shipped (add your own in section L, or use `--config my.json` for one-off changes):

| scenario | seasons | bimodal cells | step 5: spells ignored near onset / demise | step 4: same |
|---|---|---|---|---|
| `base` (default) | RADS files | major season | 10 / 10 days | 0 / 0 |
| `chirps` | computed from CHIRPS | major season | 10 / 10 | 0 / 0 |
| `mask_bimodal` | RADS files | masked | 10 / 10 | 0 / 0 |
| `excl0` | RADS files | major season | 0 / 0 (every spell counts) | 0 / 0 |
| `excl20` | RADS files | major season | 20 / 20 | 20 / 20 |
| `rads_no_ndvi` | RADS files, no NDVI demise shift | major season | 10 / 10 | 0 / 0 |
| `chirps_mask_bimodal` | computed from CHIRPS | masked | 10 / 10 | 0 / 0 |

```bash
# HPC, from the folder that has ../chirps_africa/ (RADS_FILE_PATTERN):
python v9_rads.py --region ssa --workers 40                 # check the RADS files: variables, pairing, frozen onsets
nohup python run_all.py --region ssa --scenarios base chirps mask_bimodal excl0 \
      --workers 40 --country_jobs 4 > run_all_v9.out 2>&1 &
# -> dryspell_v9/ssa/<scenario>/step02..step06/ and dryspell_v9/ssa/compare/base_vs_chirps_vs_mask_bimodal_vs_excl0/
python v9_07_compare.py --region ssa --scenarios base excl20       # any other comparison later
Rscript R/plot_results.R --dir dryspell_v9/ssa/base/step05/ssa \
      --boundaries dryspell_v9_data/boundaries/ne_50m_admin_0_countries.gpkg   # R copies of the step 5 figures
```

The output layout changed: `dryspell_v9/<region>/<scenario>/stepNN/` (earlier runs wrote `dryspell_v9/<region>/stepNN/`).

CI cannot reach your RADS files (Dropbox), so it builds RADS-format files from the same CHIRPS with the RADS algorithm (`tests/make_rads_from_chirps.py`). It writes them in both layouts and checks that they pair into the same seasons, together with synthetic seasons crossing 31 December (`tests/check_rads_pairing.py`). This tests the reading and pairing, not the content of your files.

## v9 features

This version builds on v8: it starts from scratch with the same RADS-style onset and demise from CHIRPS, the same major-season rule and the same sowing × crop × cycle analysis. The new parts are:

| v9 change | Where |
|---|---|
| **NDVI (GIMMS 3g lineage) refines bimodality**: a cell is bimodal only if rainfall has a trough **and** NDVI shows two growing seasons (`REGIME_SOURCE`) | steps 2–3, section F/H |
| **Demise readjusted with the NDVI end of season**: the cell's median lag of the NDVI end of season behind the rainfall demise, clipped to 0–30 days (`DEMISE_ADJUST`, `DEMISE_SHIFT_MAX`) | step 3, section H |
| **False start / false demise** (≥ 10 dry days within the first / last 20 days of the season) are always flagged, and can be **excluded** (`FALSE_START_EXCLUDE`, `FALSE_DEMISE_EXCLUDE`, `FALSE_DRY_MODE`) | step 3, section G |
| **Step 4 runs on any target**: a country, a bbox, a polygon (or one feature of it), or a single grid cell. The single-cell run also writes `season_detail.csv` with every season | step 4 |
| **Summaries by HarvestChoice AEZ (8 classes)** or **Köppen–Geiger 1991–2020** (`SUMMARY_ZONES`, or `--zones`) | steps 4–5, section J |
| **All settings live in one file**, `v9_config.py` (sections A–J). JSON overrides via `run_all.py --config` | all |

## Data used, and the honest caveats

* **Rainfall**: CHIRPS v2.0 daily (UCSB CHC), Cloud-Optimised GeoTIFFs. Only the region window is downloaded.
* **NDVI**: the paper you pointed to, Vrieling, de Leeuw & Said (2013, *Remote Sens.* 5, 982), derived its growing seasons from **GIMMS NDVI3g** (1981–2011). Their season maps are not published as a download that I could find, and the original NDVI3g files sit behind an Earthdata login. v9 therefore uses **PKU GIMMS NDVI v1.2** (Li et al. 2023; Zenodo record 8253971, CC BY 4.0). This is the consolidated successor of NDVI3g: half-monthly, 1/12°, 1982–2015 for the `AVHRR_solely` product. v9 then re-implements the **approach** of Vrieling et al.: the number of seasons from the mean annual profile, and per year the start and end of season at 50% of the amplitude inside a window around each mean peak. The parameters follow the paper's description, not their code, which was not published. So **v9 does not reproduce their maps exactly**.
* **AEZ (8 classes)**: the CGSpace item (HarvestChoice / IFPRI AEZ for Africa, Sebastian 2009) is the 3-digit HarvestChoice grid. v9 folds it into 8 classes, warm/cool × arid/semiarid/subhumid/humid (`aez8_from_code`). **Known defect:** the published ASCII grid is damaged south of about 3.8°N, so cells there come out as "unassigned". Use `koppen` for countries that reach that far south (Gulf of Guinea coast, Central and East Africa).
* **Köppen–Geiger**: Beck et al. (2023) 1991–2020, 1 km (figshare, CC BY 4.0). The 30 classes carry labels from its `legend.txt`.
* NDVI pixels without a vegetation cycle (towns such as Kano, Lagos and Ibadan, open water, bare soil) take the seasons of the nearest vegetated pixel within `NDVI_FILL_RADIUS` pixels (2 by default, about 18 km); the `ndvi_filled` layer marks them. Without this, the first CI run with real NDVI had all six city sites in the tests on "no signal" pixels.
* Zone maps are put on the 0.05° CHIRPS grid by **majority (mode)** of the source pixels in each cell.
* **Crop stages** (`v9_config.py` section I) give each stage's onset in days after sowing for a reference cultivar. Sorghum (110 days) uses the Vanderlip & Reeves stages with the K-State timings. Pearl millet (92 days) uses the Maiti & Bidinger stages with typical timings. Groundnut (120 days) uses the Boote R stages with typical timings.
  * Stages are rescaled to each cycle length; emergence stays fixed.
  * In sorghum and pearl millet, the time from flowering to maturity changes only as (cycle/reference)^0.6 and the vegetative phase absorbs the rest, because longer cultivars differ mostly in time to flowering.
  * In groundnut, time to first flower (R1) changes as (cycle/reference)^0.3 and pod/seed filling absorbs the rest.
  * The exponents, groundnut emergence at 8 days and the pearl millet stages without day counts (3-leaf to flag leaf) are my assumptions; calibrate them with local trial data. `stage_windows.csv` lists the resulting days for every crop and cycle.

## Steps

| Step | Script | What it does | Output |
|---|---|---|---|
| 1 | `v9_01_download.py` | CHIRPS (resumable), NDVI zips (download, crop to region, delete), Natural Earth, HarvestChoice AEZ, Köppen | `dryspell_v9_data/` |
| 2 | `v9_02_ndvi_phenology.py` | NDVI seasons per pixel (0/1/2) and the start/end of each season per year, on the CHIRPS grid | `step02/ndvi_phenology.nc` |
| 3 | `v9_03_spells_seasons.py` | dry spells; regime (rain, then refined with NDVI); onset and demise per year from the RADS files or computed in the major-season window; bimodal major / mask; false start/demise flags; NDVI demise adjustment | `step03/` (spells, seasons, `grid_meta.nc`, diagnostics) |
| 4 | `v9_04_sowing_risk.py` | for one target: feasibility, the longest dry spell inside each crop cycle, which stages it hits, and the vulnerable window | `step04/<name>/` |
| 5 | `v9_05_spell_stats.py` | crop-independent dry spells inside each valid season: number, start and duration of the first, last and longest spell, dry share. Maps, probability density functions, and summaries by latitude band and by zone | `step05/<region or target>/` |
| 6 | `v9_06_aggregate.py` | pools every **country** folder of step 4 (bbox, polygon and point runs are ignored) | `step06/SSA/` |
| 7 | `v9_07_compare.py` | with two or more scenarios: what changes between them | `dryspell_v9/<region>/compare/<names>/` |
| — | `run_all.py` | everything, resumable, with a country loop or a single target | `run_all.log`, `run_all_status.csv` |

New columns and layers in step 3:
* seasons table: `demise_rain_date`, `ndvi_eos_date`, `demise_shift`, `false_start`, `false_demise`, `rain_regime`, `ndvi_n_seasons`;
* `grid_meta.nc`: `rain_regime`, `ndvi_n_seasons`, `false_start_share`, `false_demise_share`, `demise_shift_median`, `ndvi_eos_offset_median` (before clipping), `ndvi_eos_match_share`.

The step 3 log prints how many cells hit the 30-day cap, so you can see whether `DEMISE_SHIFT_MAX` binds.

## Step 5: dry spells inside the season (maps, PDFs, latitude profile)

Settings are in `v9_config.py` sections D and K. Defaults:
* spells are at least `DRY_SPELL_MIN_DAYS` = 10 days long (< 1 mm per day);
* spells in the very first and very last 10 days of the season are not counted (`SPELL_STATS_EXCLUDE_FIRST/_LAST`; a spell crossing that edge keeps its part inside, `SPELL_STATS_EDGE_POLICY`);
* days are counted after the onset (onset = day 0);
* the season ends at the **rainfall** demise, because the NDVI-adjusted demise would add the post-rain dry-down. Set `SPELL_STATS_DEMISE = "adjusted"` to use the adjusted demise instead.

| Metric | Defined for | Map (per-cell median) |
|---|---|---|
| number of dry spells per season (plus mean, P(≥1), P(≥2)) | every season | `map_n_spells_median/mean`, `map_p_ge1`, `map_p_ge2` |
| median duration of the season's dry spells | seasons with ≥ 1 spell | `map_spell_len_median` |
| start and duration of the 1st spell | seasons with ≥ 1 spell | `map_first_start_median`, `map_first_len_median` |
| start and duration of the last spell | seasons with ≥ 2 spells | `map_last_start_median`, `map_last_len_median` |
| start and duration of the longest spell (ties go to the earliest) | seasons with ≥ 1 spell | `map_longest_start_median`, `map_longest_len_median` |
| share of the season spent in dry spells | every season | `map_dry_frac_median` |

A cell median needs at least `SPELL_STATS_MIN_COND` (3) seasons where the metric is defined. Every map also has a GeoTIFF (`cog/`) and a layer in `cells_spell_stats.nc`.

Pooled over all seasons of the cells in a group:
* `summary_by_zone.csv` gives the zones of `SUMMARY_ZONES` (AEZ8 by default, or `--zones koppen`), plus "ALL";
* `summary_by_latitude.csv` gives latitude bands of `LAT_BAND_DEG` (1°);
* both have the number of cells, seasons and seasons where the metric is defined, plus the mean, p10, p25, median, p75 and p90. The quantiles are exact, computed from 1-day histograms;
* the histograms themselves are in `hist_by_*.csv`, so you can redraw the PDFs in R or elsewhere.

Figures:
* `png/pdf_<metric>.png`: PDFs by zone (the 4 largest zones, the rest grouped as "other zones") and by `PDF_LAT_BAND_DEG` (2°) latitude bands;
* `png/latitude_profile.png`: median and interquartile range against latitude. Top row: number of dry spells per season (with the mean), then the start of the longest, first and last spell. Bottom row: median duration of a season's dry spells, then the duration of the longest, first and last spell.

Step 5 runs on the whole region by default (`run_all` does this after step 4). Like step 4, it can also run on `--iso3`, `--bbox`, `--polygon` or `--point`. `tests/check_spell_stats.py` recomputes the spells from the raw CHIRPS cache for sampled cells and checks them against step 5.

The same figures in R (`R/plot_results.R`, packages ggplot2, dplyr, tidyr, readr, purrr, stringr, terra and sf):
* maps from `cog/*.tif`;
* PDFs from `hist_by_zone.csv` / `hist_by_latitude.csv`. The PDFs need the season-level histograms; the rasters only hold per-cell medians;
* the latitude profile from `summary_by_latitude.csv`.

The R figures go to `<step05 folder>/png_R/`. `--tif_dir <folder>` also maps every GeoTIFF of another folder, for example `step03/diagnostics`.

## Figure style

All figures follow the CIMMYT/CGIAR branding (see `CLAUDE.md`); the definitions are in the BRAND STYLE section of `v9_common.py`:
* **Categorical series:** at most 4 colours, in the colour-blind-checked order teal `#326670`, orange `#f29657`, brown `#704b0f`, green `#77bd42`. Smaller zones are grouped as "other zones" in sage `#acb7ac`.
* **Zone maps:** up to 9 brand colours, with any further classes grouped as "other zones".
* **Colour scales:**
  * `brand_risk` (yellow → orange → brown): dryness, dry spells and hit probabilities;
  * `brand_teal`: probabilities, timing and rainfall;
  * `brand_green`: season length and counts;
  * `brand_div` (orange ↔ teal): ratios and offsets.
* **Text:** dark grey `#54565b`.
* **Font:** Avenir when installed, otherwise Nunito Sans, otherwise DejaVu Sans.

## Running

```bash
pip install -r requirements.txt

# whole SSA, default scenario (RADS seasons), one folder per country + SSA aggregate (HPC)
nohup python run_all.py --region ssa --workers 40 --country_jobs 4 > run_all_ssa.out 2>&1 &
# CHIRPS from the v7 cache instead of downloading:
echo '{"CHIRPS_V7_CACHE": "../dryspell_v7/ssa/cache"}' > v7cache.json
python run_all.py --region ssa --config v7cache.json --steps 1      # copies it, downloads only the missing days

# change settings without editing the code
echo '{"FALSE_START_EXCLUDE": true, "SUMMARY_ZONES": "koppen", "DEMISE_ADJUST": "none", "DEMISE_GRACE": 10}' > alt.json
python run_all.py --region ssa --config alt.json --workers 40      # no --resume after changing settings

# step 4 only, on another target (steps 1-3 done for the region)
python v9_04_sowing_risk.py --region ssa --bbox 7 10.5 9.5 12.5 --name kano_box --zones koppen
python v9_04_sowing_risk.py --region ssa --polygon states.gpkg --polygon_field NAME --polygon_value Kano
python v9_04_sowing_risk.py --region ssa --point 12.0 8.52 --name kano_cell     # + season_detail.csv
python v9_04_sowing_risk.py --region ssa --iso3 GHA --zones my_zones.gpkg --zone_field ZONE
# the same through run_all:
python run_all.py --region ssa --steps 4 --target_point 12.0 8.52 --target_name kano_cell
```

Step 4 outputs per target: `zone_summary.csv` and `zone_stage_hits.csv` (columns `unit`, `zone_scheme`, `zone`, with `zone == "ALL"` for the whole target), `regime_summary.csv`, `cell_summary.parquet`, `cell_stage_hits_<crop>.parquet`, `cells_<crop>.nc`, `stage_windows.csv`, `status.json` and `png/`.

## Same results on GitHub and on the HPC

The CI workflow (`.github/workflows/dry_spell_v9.yml`) runs `run_all.py` on the `ci_nga` box with the real downloads and four scenarios. It then runs the single-target modes and the independent checks in `tests/`, and commits one fingerprint per scenario to `reference/ci_nga/<scenario>/`.

Only the `chirps` scenario can match exactly on the HPC; the RADS scenarios use your real RADS files there and CI's stand-ins on GitHub. On the HPC:

```bash
python run_all.py --region ci_nga --scenarios chirps --countries NGA BEN NER CMR TCD --workers 8
DRYSPELL_V9_SCENARIO=chirps python tests/compare_reference.py --region ci_nga    # PARITY OK = same numbers as CI
```

A difference means different input data, for example a CHIRPS day that failed to download (see `dryspell_v9_data/chirps/ci_nga/meta.json`), different settings, or a different code version.
