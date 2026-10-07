# Dry-spell pipeline v7 (CHIRPS + RADS)

These are Python scripts for the HPC (run from a JupyterLab terminal). Put all `.py` files in one folder and run them from the folder that contains `chirps_data_cache/`. The shared module must keep the name `dryspell_v7_common.py`.

## Inputs

- **CHIRPS:** per-country daily files at `chirps_data_cache/chirps_<ISO3>_1981_2025.nc`.
- **RADS:** `../chirps_africa/africa_RainyAndDry*.<YYYY>.nc` (or `chirps_africa/`). These hold one season per year; cells with two or three rainy seasons are masked.
- **Country boundaries:** `Spatial_data_repository/ne_50m_admin_0_countries.zip`. If this file is missing, the scripts download Natural Earth.
- **AEZ map (optional, step 4):** HarvestChoice/IFPRI "Agro-ecological Zones of Africa", `003_afr-aez_09.zip`, from https://doi.org/10.7910/DVN/HJYYTI (CC BY-NC 3.0).

## Run order

```bash
python 2026-09-26.step1_dry_spell_extract_v07.py --inspect --region study   # check the inputs, writes nothing
python 2026-09-26.step1_dry_spell_extract_v07.py --region study --workers 40 # CHIRPS -> grid -> all dry spells
python 2026-09-26.step2_dry_spell_seasons_v07.py --region study --workers 40 # RADS seasons x dry spells
python 2026-09-26.step3_bbox_zoning_v07.py       --region study              # optional: k-means zones
python 2026-10-06.step4_sowing_date_stage_risk_v07.py --region study --iso3 NGA \
       --aez path/to/003_afr-aez_09.zip                                       # one country
python 2026-10-07.step5_ssa_aggregate_v07.py --region study                # aggregate the countries
```

- Use the same `--region` for every step. Outputs go to `dryspell_v7/<region>/step*/`.
- Step 1 writes a rainfall cache of about 16 GB for `study`. If a worker runs out of memory, lower `--workers`.

## Whole of SSA in one command: `run_all.py`

```bash
# from the folder that holds chirps_data_cache/ (all .py files of this folder next to each other)
nohup python run_all.py --region ssa --workers 40 --country_jobs 4 \
      --aez Spatial_data_repository/003_afr-aez_09.zip > run_all.out 2>&1 &
python run_all.py --region ssa --resume          # continue after a crash or time-out
python run_all.py --region ssa --dry_run         # show what would run
python run_all.py --region ssa --steps 4 5 --countries NGA GHA BFA --resume
```

- **Steps:** runs step 1 and step 2 once for the region, then step 4 for every Sub-Saharan country (50 ISO3 codes, including Somaliland as Natural Earth draws it), then step 5.
- **Step 3** (k-means zoning) only runs with `--steps ... 3`.
- **Per-country isolation:** a country that fails is logged and the run continues. A country with nothing to analyse is marked `skipped` with the reason, e.g. all cells masked as bimodal by RADS, or outside the region.
- **`--resume`** skips what is already done (step 1, step 2, each finished country).
- **AEZ map:** a zipped or ASCII AEZ map is converted to a GeoTIFF once, under `dryspell_v7/<region>/aez/`.
- **Logs:** `dryspell_v7/<region>/run_all.log`, `run_all_status.csv` and `run_all_logs/`.

Output layout:

```
dryspell_v7/<region>/step4/<ISO3>/   one folder per country (status.json, tables, cells_<crop>.nc, png/)
dryspell_v7/<region>/step4/SSA/      all countries together (step 5):
    countries.csv           status of every country
    country_summary.csv     national values of every country (crop x cycle x sowing)
    ssa_summary.csv         SSA pooled, per AEZ and ALL
    ssa_stage_hits.csv      SSA pooled P(longest dry spell hits each stage)
    ssa_cells_<crop>.nc     mosaic of all countries on the 0.05 deg grid
    png/                    SSA stage heatmaps (+ per AEZ), maps, AEZ curves, country comparison
```

SSA values are cell-weighted, so they equal the mean over all SSA cells. `tests/check_step5.py` verifies this against the pooled cell tables.

## Step 4 in short

Step 4 covers sorghum, pearl millet and groundnut, with 70, 90, 110 and 130-day cycles and sowing at RADS onset + 0, 10, 20, 30 and 40 days. For every grid cell it finds the longest dry spell (at least 10 days with < 1 mm) inside the crop cycle and records which phenological stages, and whether the crop's most vulnerable window, that spell overlaps.

- **Impossible to grow:** a cell is flagged when maturity falls more than 10 days after demise (`--grace`) in at least half of its seasons.
- **Stage timings:** set in the `CROPS` block at the top of the script. They are provisional; see CHANGES.md for their sources and status.

See CHANGES.md for the fixes made to steps 1–3.

## Continuous integration (`.github/workflows/dry_spell_v7.yml`)

On every push to `claude/**` that touches this folder, the workflow runs steps 1 → 4 for the Nigeria box (2.5–14.5°E, 4.5–14.5°N) on real data.

- **CHIRPS (real):** CHIRPS v2.0 daily, 1981–2025. `tests/fetch_chirps_cog.py` reads only the Nigeria window of each daily global COG at data.chc.ucsb.edu (a few GB of HTTP range requests; cached between runs). It writes `chirps_NGA_1981_2025.nc` with the same grid and layout as the HPC file.
- **RADS (rebuilt, not the official files):** `tests/make_rads_from_chirps.py` rebuilds RADS-style onset and demise from that CHIRPS, using the first pass of the RADS algorithm on pentads, including the bimodal harmonic mask. The official RADS files are only shared through a Dropbox folder, which CI cannot list.
- **Boundaries and AEZ (real):** Natural Earth boundaries and the HarvestChoice AEZ zip are downloaded.
- **Independent check:** `tests/check_step4.py` recomputes step 4 with plain loops for sampled cells and fails the job on any mismatch.
- **Results:** small results (CSV tables, logs, PNGs) are committed to `ci_results/`. The NetCDF and Parquet outputs are not kept (the account's artifact storage quota is full).
