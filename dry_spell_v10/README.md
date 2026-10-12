# Dry-spell risk by sowing date, v10: scenarios (CHIRPS or RADS seasons, dry-spell exclusion windows)

v10 is v9 plus the ability to run **many configurations side by side and see what changes**:

| v10 change | Settings (`v10_config.py`) |
|---|---|
| **Season source**: seasons computed from CHIRPS (v8/v9 method) **or read from the downloaded RADS files** (`../chirps_africa/africa_RainyAndDrySeason.pentad.CHIRPS.YYYY.nc`, as in v7). Cells RADS masks (two or three rainy seasons) are not analysed, or can fall back to the CHIRPS season | section G2: `SEASON_SOURCE`, `RADS_FILE_PATTERN`, `RADS_FALLBACK` |
| **Dry spells near the season edges counted or not**: for the in-season statistics (step 6) and, separately, for the crop analysis (step 4): ignore spells in the first N days after onset and the last N days before demise (0, 10, 20, ...); a spell crossing the edge is clipped or dropped | `SPELL_STATS_EXCLUDE_FIRST/_LAST`, `SPELL_STATS_EDGE_POLICY`; `CROP_SPELL_EXCLUDE_FIRST/_LAST`, `CROP_SPELL_EDGE_POLICY` |
| **Scenarios**: named sets of settings, `run_all.py --scenarios base rads rads_excl0 rads_excl20`. Each runs steps 2-6 into `dryspell_v10/<region>/<scenario>/`; downloads are shared (`dryspell_v9_data/`, so a v9 download is reused) | section L: `SCENARIOS`, `SCENARIO_DEFAULT` |
| **Step 7, comparison** (`v10_07_compare.py`): the settings that differ; onset and demise **season by season** (same cell, same year) between the base and each scenario; maps of every key layer per scenario with difference maps; step 6 tables of all scenarios in one file | - |
| `v10_rads.py --region R` inspects the RADS files alone: variables, grid, how onsets and demises were paired, and **onsets that never change from year to year** (a known problem of the HPC files, e.g. 1 May at Kano) | - |

Scenarios shipped (edit or add your own in section L, or use `--config` for one-off changes):

| scenario | season source | NDVI demise shift | step 6: spells ignored near onset / demise | step 4: idem |
|---|---|---|---|---|
| `base` | CHIRPS | yes | 10 / 10 d | 0 / 0 d |
| `rads` | RADS files | no | 10 / 10 d | 0 / 0 d |
| `rads_excl0` | RADS files | no | 0 / 0 d (every spell counts) | 0 / 0 d |
| `rads_excl20` | RADS files | no | 20 / 20 d | 20 / 20 d |
| `chirps_excl0`, `chirps_excl20` | CHIRPS | yes | 0 / 0, 20 / 20 d | 0 / 0, 20 / 20 d |
| `chirps_no_ndvi` | CHIRPS, regime from rain only | no | 10 / 10 d | 0 / 0 d |

```bash
# HPC: RADS files at ../chirps_africa/ relative to the working folder (RADS_FILE_PATTERN)
python v10_rads.py --region ssa --workers 40                       # check the files first
nohup python run_all.py --region ssa --scenarios base rads rads_excl0 rads_excl20 \
      --workers 40 --country_jobs 4 > run_all_v10.out 2>&1 &
# -> dryspell_v10/ssa/<scenario>/... and dryspell_v10/ssa/compare/base_vs_rads_vs_rads_excl0_vs_rads_excl20/
python v10_07_compare.py --region ssa --scenarios rads rads_excl20   # any other pair later
```

CI cannot reach the RADS files (Dropbox), so it builds RADS-format files from the same CHIRPS with the RADS algorithm (`tests/make_rads_from_chirps.py --hpc_layout`, first pass of Bombardi et al.'s code on pentads, bimodal cells masked). They test the reading and pairing code, not the content of your files.

The rest of this README describes the v9 features, unchanged in v10.

## v9 features

This version builds on v8: it starts from scratch with the same RADS-style onset and demise from CHIRPS, the same major-season rule and the same sowing × crop × cycle analysis. The new parts are:

| v10 change | Where |
|---|---|
| **NDVI (GIMMS 3g lineage) refines bimodality**: a cell is bimodal only if rainfall has a trough **and** NDVI shows two growing seasons (`REGIME_SOURCE`) | steps 2–3, section F/H |
| **Demise readjusted with the NDVI end of season**: the cell's median lag of the NDVI end of season behind the rainfall demise, clipped to 0–30 days (`DEMISE_ADJUST`, `DEMISE_SHIFT_MAX`) | step 3, section H |
| **False start / false demise** (≥ 10 dry days within the first / last 20 days of the season) are always flagged, and can be **excluded** (`FALSE_START_EXCLUDE`, `FALSE_DEMISE_EXCLUDE`, `FALSE_DRY_MODE`) | step 3, section G |
| **Step 4 runs on any target**: a country, a bbox, a polygon (or one feature of it), or a single grid cell. The single-cell run also writes `season_detail.csv` with every season | step 4 |
| **Summaries by HarvestChoice AEZ (8 classes)** or **Köppen–Geiger 1991–2020** (`SUMMARY_ZONES`, or `--zones`) | steps 4–5, section J |
| **All settings live in one file**, `v10_config.py` (sections A–J). JSON overrides via `run_all.py --config` | all |

## Data used, and the honest caveats

* **Rainfall**: CHIRPS v2.0 daily (UCSB CHC), Cloud-Optimised GeoTIFFs. Only the region window is downloaded.
* **NDVI**: the paper you pointed to, Vrieling, de Leeuw & Said (2013, *Remote Sens.* 5, 982), derived its growing seasons from **GIMMS NDVI3g** (1981–2011). Their season maps are not published as a download that I could find, and the original NDVI3g files sit behind an Earthdata login. v10 therefore uses **PKU GIMMS NDVI v1.2** (Li et al. 2023; Zenodo record 8253971, CC BY 4.0). This is the consolidated successor of NDVI3g: half-monthly, 1/12°, 1982–2015 for the `AVHRR_solely` product. v10 then re-implements the **approach** of Vrieling et al.: the number of seasons from the mean annual profile, and per year the start and end of season at 50% of the amplitude inside a window around each mean peak. The parameters follow the paper's description, not their code, which was not published. So **v10 does not reproduce their maps exactly**.
* **AEZ (8 classes)**: the CGSpace item (HarvestChoice / IFPRI AEZ for Africa, Sebastian 2009) is the 3-digit HarvestChoice grid. v10 folds it into 8 classes, warm/cool × arid/semiarid/subhumid/humid (`aez8_from_code`). **Known defect:** the published ASCII grid is damaged south of about 3.8°N, so cells there come out as "unassigned". Use `koppen` for countries that reach that far south (Gulf of Guinea coast, Central and East Africa).
* **Köppen–Geiger**: Beck et al. (2023) 1991–2020, 1 km (figshare, CC BY 4.0). The 30 classes carry labels from its `legend.txt`.
* NDVI pixels without a vegetation cycle (towns such as Kano, Lagos and Ibadan, open water, bare soil) take the seasons of the nearest vegetated pixel within `NDVI_FILL_RADIUS` pixels (2 by default, about 18 km); the `ndvi_filled` layer marks them. Without this, the first CI run with real NDVI had all six city sites in the tests on "no signal" pixels.
* Zone maps are put on the 0.05° CHIRPS grid by **majority (mode)** of the source pixels in each cell.
* **Crop stages** (`v10_config.py` section I) give each stage's onset in days after sowing for a reference cultivar. Sorghum (110 days) uses the Vanderlip & Reeves stages with the K-State timings. Pearl millet (92 days) uses the Maiti & Bidinger stages with typical timings. Groundnut (120 days) uses the Boote R stages with typical timings.
  * Stages are rescaled to each cycle length; emergence stays fixed.
  * In sorghum and pearl millet, the time from flowering to maturity changes only as (cycle/reference)^0.6 and the vegetative phase absorbs the rest, because longer cultivars differ mostly in time to flowering.
  * In groundnut, time to first flower (R1) changes as (cycle/reference)^0.3 and pod/seed filling absorbs the rest.
  * The exponents, groundnut emergence at 8 days and the pearl millet stages without day counts (3-leaf to flag leaf) are my assumptions; calibrate them with local trial data. `stage_windows.csv` lists the resulting days for every crop and cycle.

## Steps

| Step | Script | What it does | Output |
|---|---|---|---|
| 1 | `v10_01_download.py` | CHIRPS (resumable), NDVI zips (download, crop to region, delete), Natural Earth, HarvestChoice AEZ, Köppen | `dryspell_v9_data/` |
| 2 | `v10_02_ndvi_phenology.py` | NDVI seasons per pixel (0/1/2) and the start/end of each season per year, on the CHIRPS grid | `step02/ndvi_phenology.nc` |
| 3 | `v10_03_spells_seasons.py` | dry spells; regime (rain, then refined with NDVI); window of the major season; onset and demise per year; false start/demise flags; NDVI demise adjustment | `step03/` (spells, seasons, `grid_meta.nc`, diagnostics) |
| 4 | `v10_04_sowing_risk.py` | for one target: feasibility, the longest dry spell inside each crop cycle, which stages it hits, and the vulnerable window | `step04/<name>/` |
| 5 | `v10_05_aggregate.py` | pools every **country** folder of step 4 into `step04/SSA/` (bbox, polygon and point runs are ignored) | `step04/SSA/` |
| 6 | `v10_06_spell_stats.py` | crop-independent dry spells inside each valid season: number, start and duration of the first, last and longest spell, dry share. Maps, probability density functions, and summaries by latitude band and by zone | `step06/<region or target>/` |
| — | `run_all.py` | everything, resumable, with a country loop or a single target | `run_all.log`, `run_all_status.csv` |

New columns and layers in step 3:
* seasons table: `demise_rain_date`, `ndvi_eos_date`, `demise_shift`, `false_start`, `false_demise`, `rain_regime`, `ndvi_n_seasons`;
* `grid_meta.nc`: `rain_regime`, `ndvi_n_seasons`, `false_start_share`, `false_demise_share`, `demise_shift_median`, `ndvi_eos_offset_median` (before clipping), `ndvi_eos_match_share`.

The step 3 log prints how many cells hit the 30-day cap, so you can see whether `DEMISE_SHIFT_MAX` binds.

## Step 6: dry spells inside the season (the v7 maps, plus PDFs)

Settings are in `v10_config.py` section K. The defaults follow v7:
* spells are at least 10 days long (< 1 mm per day);
* the first and last 10 days of the season are ignored;
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
* `png/pdf_<metric>.png`: PDFs by zone (the 8 largest zones, the rest grouped as "other zones") and by `PDF_LAT_BAND_DEG` (2°) latitude bands;
* `png/latitude_profile.png`: median and interquartile range against latitude. Top row: number of dry spells per season (with the mean), then the start of the longest, first and last spell. Bottom row: median duration of a season's dry spells, then the duration of the longest, first and last spell.

Step 6 runs on the whole region by default (`run_all` does this after step 5). Like step 4, it can also run on `--iso3`, `--bbox`, `--polygon` or `--point`. `tests/check_spell_stats.py` recomputes the spells from the raw CHIRPS cache for sampled cells and checks them against step 6.

## Figure style

All figures follow the CIMMYT/CGIAR branding (see `CLAUDE.md`); the definitions are in the BRAND STYLE section of `v10_common.py`:
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

# whole SSA, one folder per country + SSA aggregate (HPC)
nohup python run_all.py --region ssa --workers 40 --country_jobs 4 > run_all_ssa.out 2>&1 &

# change settings without editing the code
echo '{"FALSE_START_EXCLUDE": true, "SUMMARY_ZONES": "koppen", "DEMISE_ADJUST": "none", "DEMISE_GRACE": 10}' > alt.json
python run_all.py --region ssa --config alt.json --workers 40      # no --resume after changing settings

# step 4 only, on another target (steps 1-3 done for the region)
python v10_04_sowing_risk.py --region ssa --bbox 7 10.5 9.5 12.5 --name kano_box --zones koppen
python v10_04_sowing_risk.py --region ssa --polygon states.gpkg --polygon_field NAME --polygon_value Kano
python v10_04_sowing_risk.py --region ssa --point 12.0 8.52 --name kano_cell     # + season_detail.csv
python v10_04_sowing_risk.py --region ssa --iso3 GHA --zones my_zones.gpkg --zone_field ZONE
# the same through run_all:
python run_all.py --region ssa --steps 4 --target_point 12.0 8.52 --target_name kano_cell
```

Step 4 outputs per target: `zone_summary.csv` and `zone_stage_hits.csv` (columns `unit`, `zone_scheme`, `zone`, with `zone == "ALL"` for the whole target), `regime_summary.csv`, `cell_summary.parquet`, `cell_stage_hits_<crop>.parquet`, `cells_<crop>.nc`, `stage_windows.csv`, `status.json` and `png/`.

## Same results on GitHub and on the HPC

The CI workflow (`.github/workflows/dry_spell_v9.yml`) runs `run_all.py` on the `ci_nga` box with the real downloads. It then runs the single-target modes, the independent checks in `tests/`, and commits a fingerprint to `reference/ci_nga/`. On the HPC:

```bash
python run_all.py --region ci_nga --countries NGA BEN NER CMR TCD --workers 8
python tests/compare_reference.py --region ci_nga        # PARITY OK = same numbers as CI (1e-6)
```

A difference means different input data, for example a CHIRPS day that failed to download (see `dryspell_v9_data/chirps/ci_nga/meta.json`), different settings, or a different code version.
