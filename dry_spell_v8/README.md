# Dry-spell workflow v8: from scratch, the same on GitHub and on the HPC

For every Sub-Saharan African country and three crops (sorghum, pearl millet, groundnut) with 70, 90, 110 and 130-day cycles, the workflow asks:

> When the crop is sown at onset + 0, 10, 20, 30 or 40 days, which growth stages does the **longest dry spell** of its cycle hit, and how often does it hit the most drought-vulnerable window?

## What changed from v7

| Problem found in v7 | v8 |
|---|---|
| Inputs prepared by hand: per-country CHIRPS files, and RADS files from Dropbox whose layout puts the onset of Y+1 in file Y, with onsets stuck on 1 May at Kano | `run_all.py` **downloads everything**: CHIRPS v2.0 daily, Natural Earth, HarvestChoice AEZ |
| Season dates taken from external RADS files | **Seasons are computed from CHIRPS with the RADS method** (cumulative rainfall anomaly), with the same code on GitHub and the HPC |
| Bimodality ratio A2/A1 called the short single season of the Sahel "bimodal" (Kano 0.56) and missed the two seasons of south-west Nigeria (Ibadan 0.55, below the 1.0 cut-off) | **Regime from the shape of the annual cycle:** a real trough between two peaks |
| Bimodal south-west treated as one long season, so the August break appeared as a "dry spell inside the season" | **Bimodal cells use only the major season** (the one with more rain). **Transition cells** keep their single season, and the shallow dip stays inside it. |
| No way to tell whether HPC and CI agree | **Parity check:** `tests/compare_reference.py` compares an HPC run of the CI box with the reference committed by CI |

## Run

Needs Python ≥ 3.10 with the packages in `requirements.txt`, and internet access.

```bash
cd /some/work/folder        # inputs go to ./dryspell_v8_data, results to ./dryspell_v8

# 1) parity check first (about 15 min with 8 cores): same box as GitHub CI
python /path/to/dry_spell_v8/run_all.py --region ci_nga --countries NGA BEN NER CMR TCD KEN --workers 8
python /path/to/dry_spell_v8/tests/compare_reference.py --region ci_nga       # -> PARITY OK

# 2) the whole of Sub-Saharan Africa
nohup python /path/to/dry_spell_v8/run_all.py --region ssa --workers 40 --country_jobs 4 > run_all_ssa.out 2>&1 &
python /path/to/dry_spell_v8/run_all.py --region ssa --resume                  # after a crash or time-out
python /path/to/dry_spell_v8/run_all.py --region ssa --dry_run                 # show the plan
```

**Size and time for `ssa`** (my estimates from the grid size, not measured):
- The CHIRPS cache is 1,180 × 1,400 cells × 16,436 days, about 54 GB on disk.
- The download is a few tens of GB of HTTP range requests and takes a few hours. It resumes where it stopped.
- Step 2 needs about 1.5 GB of RAM per worker.

**Restarting:**
- `--resume` skips:
  - step 2, when its outputs are newer than the CHIRPS cache;
  - every country whose `status.json` says `ok` or `skipped`.
- A country that fails is logged and the run continues.
- `--country_jobs 4 --workers 40` runs four countries at a time with ten workers each.

## Steps

| Script | Does | Output |
|---|---|---|
| `v8_01_download.py` | CHIRPS v2.0 daily, 0.05°, 1981–2025: only the region's tiles of each daily global COG at data.chc.ucsb.edu, written into a uint16 cache (65535 = no data; negative or unreadable values are never 0 mm). Also Natural Earth 1:50m countries and the HarvestChoice AEZ map. The AEZ file on Dataverse is damaged: rows wrap over several lines, it holds 275 values fewer than its header says, and there is binary garbage at 3.5–3.8°N. It is read tolerantly, and the damaged part becomes no data. | `dryspell_v8_data/` |
| `v8_02_spells_seasons.py` | Dry spells (≥ 5 days below 1 mm), rainfall regime, major-season onset and demise per year | `dryspell_v8/<region>/step02/` |
| `v8_03_sowing_risk.py` | One country: sowing date × crop × cycle → stages hit by the longest dry spell, "impossible" flag, summaries per AEZ and per regime | `dryspell_v8/<region>/step03/<ISO3>/` |
| `v8_04_aggregate.py` | All countries pooled (cell-weighted), a mosaic NetCDF, and SSA figures | `dryspell_v8/<region>/step03/SSA/` |

## Method: regime and major season (step 2)

1. **Mean annual cycle:** the daily mean annual cycle, 1981–2024, smoothed with a 31-day circular moving average.
2. **Peaks and trough:**
   - Peaks are local maxima that reach at least 25% of the annual maximum and are at least 45 days apart.
   - With two peaks, the mid-season trough is the lowest point between them, on the side away from the driest day.
3. **Regime:** with ratio = trough ÷ smaller peak:
   - **bimodal** if ratio ≤ 0.80;
   - **transition** if 0.80 < ratio ≤ 0.95;
   - **unimodal** otherwise.

   Cells with less than 150 mm of rain a year are arid and get no season.

   Calibration on CHIRPS:

   | Class | Sites (ratio) |
   |---|---|
   | bimodal | Lagos 0.33, Ibadan 0.63, Ilorin 0.73 |
   | transition | Port Harcourt 0.81, Enugu 0.88 |
   | unimodal | Makurdi 0.98, Abuja 0.99, Kaduna / Kano / Sokoto / Maiduguri 1.00 (second "peak" is only a shoulder) |
4. **Season window:** a fixed day-of-year range, the same every year.
   - **Unimodal and transition:** from the driest day for 365 days. In a transition cell the mid-season dip keeps at least 80% of the smaller peak's rainfall, so it doesn't separate two seasons. Splitting at that dip gave artificial July onsets in the Benue and Kwara belt in a first test, so the dip stays inside the single season, where a dry spell during it counts as a risk.
   - **Bimodal:** the year is split at the driest day and at the trough. The **major season** is the part with more climatological rainfall. For Ibadan that is the first part (8 January to the 2 August trough).
   - `MAJOR_SEASON_RULE = "first"` in `v8_common.py` always takes the first season instead. With "wettest", a coherent patch in Benue State (about 7–7.7°N, 8.8–9.6°E) and southern Cameroon get their August–November season.
5. **Onset and demise for each year inside the window,** RADS first pass (Liebmann & Marengo 2001; Bombardi et al. 2019):
   - S(t) is the cumulative sum of (daily rain − reference). The reference is the climatological mean daily rain **over the window**: the annual mean for a 365-day window, which is exactly RADS, and the sub-season mean for a bimodal major season.
   - Onset is the day after the minimum of S; demise is the day of the maximum of S after the onset.
   - An onset on the window's first day is rejected, because rain didn't change from dry to wet inside the window.
   - A season is valid when it lasts 30–330 days and its window has rainfall data on ≥ 95% of days.
   - The season year is the calendar year of onset. Seasons with onsets in 1981–2024 are kept.

   Results on the CI box, from CHIRPS (median onset / demise):

   | Site | Regime | Onset | Demise |
   |---|---|---|---|
   | Kano | unimodal | 31 May | 27 Sep |
   | Sokoto | unimodal | 1 Jun | 28 Sep |
   | Abuja | unimodal | 30 Apr | 24 Oct |
   | Makurdi | unimodal | 2 May | 24 Oct |
   | Port Harcourt | transition | 27 Apr | 1 Nov |
   | Enugu | transition | 22 Apr | 28 Oct |
   | Ibadan | bimodal, major season | 4 Apr | 21 Jul |
   | Lagos | bimodal, major season | 30 Apr | 20 Jul |

Differences from the official RADS:
- no B17 second pass;
- no outlier removal: all seasons are kept, and the onset spread is reported as an IQR map;
- bimodal cells are not masked; their major season is used instead.

## Method: sowing risk (step 3)

Unchanged from v7. In short:
- **Sowing and maturity:** the crop is sown at onset + {0, 10, 20, 30, 40} days, and maturity comes after the cycle length.
- **Impossible to grow:** a cell is flagged when maturity falls more than 10 days after demise in more than half of the seasons.
- **Longest dry spell:** the longest spell of ≥ 10 dry days inside the cycle is located against the crop stages and the vulnerable window.
- **Probabilities:** taken over feasible seasons.
- **Stage timings:** the `CROPS` block, provisional, same sources as in v7.

## Parity between GitHub and the HPC

- **What CI runs:** `.github/workflows/dry_spell_v8.yml` runs exactly `run_all.py` on the `ci_nga` box, then checks:
  - `tests/check_seasons.py`: loop re-computation of regime, window, onset and demise, plus site checks;
  - `tests/check_sowing.py` and `tests/check_aggregate.py`.
- **The reference:** CI commits a fingerprint of its results to `reference/ci_nga/` (cell counts per regime and reason, mean onset and demise, national values of every country, pooled values).
- **On the HPC:** after running the same box, `tests/compare_reference.py --region ci_nga` must print `PARITY OK` (tolerance 1e-6).
- **If it doesn't:** the inputs differ, for example a CHIRPS day that failed to download (listed in `dryspell_v8_data/chirps/<region>/meta.json`, retried with `v8_01_download.py --retry_missing`), or the code version differs.
