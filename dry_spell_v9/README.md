# Dry-spell risk by sowing date, v9: CHIRPS + NDVI seasons, any target, AEZ8 / Köppen summaries

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
* The crop stage fractions and vulnerable windows are provisional (sources are in `v9_config.py` section I). Groundnut in particular is my own approximation.

## Steps

| Step | Script | What it does | Output |
|---|---|---|---|
| 1 | `v9_01_download.py` | CHIRPS (resumable), NDVI zips (download, crop to region, delete), Natural Earth, HarvestChoice AEZ, Köppen | `dryspell_v9_data/` |
| 2 | `v9_02_ndvi_phenology.py` | NDVI seasons per pixel (0/1/2) and the start/end of each season per year, on the CHIRPS grid | `step02/ndvi_phenology.nc` |
| 3 | `v9_03_spells_seasons.py` | dry spells; regime (rain, then refined with NDVI); window of the major season; onset and demise per year; false start/demise flags; NDVI demise adjustment | `step03/` (spells, seasons, `grid_meta.nc`, diagnostics) |
| 4 | `v9_04_sowing_risk.py` | for one target: feasibility, the longest dry spell inside each crop cycle, which stages it hits, and the vulnerable window | `step04/<name>/` |
| 5 | `v9_05_aggregate.py` | pools every **country** folder of step 4 into `step04/SSA/` (bbox, polygon and point runs are ignored) | `step04/SSA/` |
| 6 | `v9_06_spell_stats.py` | crop-independent dry spells inside each valid season: number, start and duration of the first, last and longest spell, dry share. Maps, probability density functions, and summaries by latitude band and by zone | `step06/<region or target>/` |
| — | `run_all.py` | everything, resumable, with a country loop or a single target | `run_all.log`, `run_all_status.csv` |

New columns and layers in step 3:
* seasons table: `demise_rain_date`, `ndvi_eos_date`, `demise_shift`, `false_start`, `false_demise`, `rain_regime`, `ndvi_n_seasons`;
* `grid_meta.nc`: `rain_regime`, `ndvi_n_seasons`, `false_start_share`, `false_demise_share`, `demise_shift_median`, `ndvi_eos_offset_median` (before clipping), `ndvi_eos_match_share`.

The step 3 log prints how many cells hit the 30-day cap, so you can see whether `DEMISE_SHIFT_MAX` binds.

## Step 6: dry spells inside the season (the v7 maps, plus PDFs)

Settings are in `v9_config.py` section K. The defaults follow v7:
* spells are at least 10 days long (< 1 mm per day);
* the first and last 10 days of the season are ignored;
* days are counted after the onset (onset = day 0);
* the season ends at the **rainfall** demise, because the NDVI-adjusted demise would add the post-rain dry-down. Set `SPELL_STATS_DEMISE = "adjusted"` to use the adjusted demise instead.

| Metric | Defined for | Map (per-cell median) |
|---|---|---|
| number of dry spells per season (plus mean, P(≥1), P(≥2)) | every season | `map_n_spells_median/mean`, `map_p_ge1`, `map_p_ge2` |
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
* `png/latitude_profile.png`: median and interquartile range of every metric against latitude, with the mean added for the two metrics that are mostly 0.

Step 6 runs on the whole region by default (`run_all` does this after step 5). Like step 4, it can also run on `--iso3`, `--bbox`, `--polygon` or `--point`. `tests/check_spell_stats.py` recomputes the spells from the raw CHIRPS cache for sampled cells and checks them against step 6.

## Running

```bash
pip install -r requirements.txt

# whole SSA, one folder per country + SSA aggregate (HPC)
nohup python run_all.py --region ssa --workers 40 --country_jobs 4 > run_all_ssa.out 2>&1 &

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

The CI workflow (`.github/workflows/dry_spell_v9.yml`) runs `run_all.py` on the `ci_nga` box with the real downloads. It then runs the single-target modes, the independent checks in `tests/`, and commits a fingerprint to `reference/ci_nga/`. On the HPC:

```bash
python run_all.py --region ci_nga --countries NGA BEN NER CMR TCD --workers 8
python tests/compare_reference.py --region ci_nga        # PARITY OK = same numbers as CI (1e-6)
```

A difference means different input data, for example a CHIRPS day that failed to download (see `dryspell_v9_data/chirps/ci_nga/meta.json`), different settings, or a different code version.
