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
       --aez path/to/003_afr-aez_09.zip                                       # sowing date x crop x cycle
```

- Use the same `--region` for every step. Outputs go to `dryspell_v7/<region>/step*/`.
- Step 1 writes a rainfall cache of about 16 GB for `study`. If a worker runs out of memory, lower `--workers`.

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
- **Results:** small results (CSV tables, logs, PNGs) are committed to `ci_results/`. The NetCDF and Parquet outputs are uploaded as a run artifact instead.
