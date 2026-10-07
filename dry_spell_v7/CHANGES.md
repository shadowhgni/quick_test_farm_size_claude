# dryspell v7 – changes (2026-10-06)

Put all `.py` files in the same folder (e.g. `DCP_climate_characterization/`) and run from there.

## Fixes to steps 1–3

| File | Change | Why |
|---|---|---|
| `dryspell_v7_common.py` | Renamed (was `2026-09-26.dry_spell_common_v07.py`) | Every step runs `import dryspell_v7_common`. The old name cannot be imported. |
| step2 `match_spells` | Returns empty arrays when a row chunk has no usable season | Crashed with `IndexError` when a chunk had dry spells but no valid season (e.g. Saharan rows or rows masked by RADS). Reproduced on synthetic data. |
| step2 `match_spells` | A spell can now be counted in two consecutive season windows | Before, a spell that bridged two windows was counted only in the later one. |
| step2 `_find_var` | Prefers the datetime variable when several names match | RADS stores onset and demise both as dates and as day-of-year (`onset_jday`). If the jday variable came first in the file, step 2 stopped with `TypeError`. |
| step2 `main` | `grid_meta.nc` is closed before worker processes start | Avoids an open NetCDF/HDF5 handle being inherited by the worker processes. |
| step1 `--inspect` | No crash when RADS files are missing | |
| step1 diagnostics | No crash when no country polygon falls in the bbox | |
| all | Usage lines in the docstrings now show the real file names | |

Not changed: the algorithms, the thresholds and the output formats of steps 1–3.

## New: step 4 – sowing date × crop × cycle → which stage the longest dry spell hits

`2026-10-06.step4_sowing_date_stage_risk_v07.py`. It reads the step 1 spells and the step 2 seasons, so steps 1 and 2 must have been run for the same `--region`.

```
python 2026-10-06.step4_sowing_date_stage_risk_v07.py --region study --iso3 NGA
python 2026-10-06.step4_sowing_date_stage_risk_v07.py --region study --iso3 NGA --day0 1 \
       --aez path/to/aez.gpkg --aez_field AEZ --min_spell pearl_millet=12 --workers 32
```

What to check before trusting the numbers:

- **Stage timings** (`CROPS` dict at the top of the script) are fractions of the cycle, scaled linearly to 70, 90, 110 and 130 days.
  - Pearl millet: taken from Maiti & Bidinger 1981, Table 1 (checked).
  - Sorghum: boot timing checked against KSU MF3234. The other stages are recalled from Vanderlip 1972 and were not re-checked.
  - Groundnut: an approximation of my own. Verify it against local data.
- **Minimum spell length**: 10 days for all three crops. I found no source for crop-specific values.
- **AEZ**: use the HarvestChoice/IFPRI "Agro-ecological Zones of Africa" map (Sebastian 2009). It is on Harvard Dataverse at https://doi.org/10.7910/DVN/HJYYTI under a CC BY-NC 3.0 licence (non-commercial use).
  - Download `003_afr-aez_09.zip` (an ESRI ASCII grid, 0.00833° ≈ 1 km) and pass the zip directly: `--aez path/003_afr-aez_09.zip`.
  - Class codes such as 311–314 (Tropic-warm arid → humid) and 321–324 (Tropic-cool) are labelled automatically.
  - The map is resampled to the 0.05° grid by taking the most common class in each cell.
  - **The downloaded `afr_aez09.asc` is damaged** (checked on the file from Dataverse):
    - Its rows wrap over several lines.
    - It holds 275 fewer values than its header says.
    - About 1.8 MB of binary garbage sits at grid rows 4166–4203 (≈ 3.8–3.5°N, in the Gulf of Guinea).

    GDAL refuses to read it ("File short"), so step 4 parses ASCII grids itself. It keeps everything before the first bad byte and treats the rest as no-data, with a warning in the log. Nigeria (north of 4.3°N) lies entirely in the clean part. For a country south of 3.8°N, the map would come out empty; ask IFPRI for a clean copy or use another layer.
  - Another class raster also works, e.g. FAO/IIASA GAEZ v4 "Dominant AEZ, 33 classes". Add `--aez_legend codes.csv` (code,label) for its labels.
  - Without `--aez`, the summary falls back to rainfall bands, labelled as a proxy.
- **Grace period**: the default is now 10 days (`--grace`): maturity may fall up to 10 days after RADS demise. Use `--grace 0` for the strict version. During those days the crop is in the early dry season, so late stages are more likely to be hit.
- **Bimodal areas**: RADS gives one season per year and masks bimodal cells, so they are reported as "no valid RADS season".
