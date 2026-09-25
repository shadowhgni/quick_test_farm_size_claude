# roads_merge — OSM + Microsoft ML road detections, tested on Benin and Togo

Builds the road layer of an accessibility (travel-time-to-city) friction surface:

1. reads OSM roads (current snapshot, plus an optional older one);
2. flags OSM roads that are **new between the two snapshots**;
3. adds [Microsoft ML Road Detections](https://github.com/microsoft/RoadDetections)
   that are not already in OSM (gap-fill);
4. rasterizes road speed (km/h, fastest road wins per cell).

| File | Role |
|---|---|
| `merge_roads.py` | improved pipeline (CLI + importable functions) |
| `speed_table.csv` | speed per OSM class, kept outside the code so it stays fixed across versions |
| `friction.py` | friction maps (min/m) for two dates: road class speeds + land cover × Tobler slope factor |
| `landcover_speed.csv` | off-road walking speed per ESA WorldCover class (placeholders, calibrate) |
| `run_friction_benin_togo.py` | Benin + Togo 2020 / 2026 friction maps and quicklooks |
| `traveltime.py` | travel time (min) to cities / ports by Nelson et al. size class, from friction maps |
| `run_traveltime_benin_togo.py` | Benin + Togo 2020 vs 2026, split into roads / city growth / ML effects |
| `REPORT.md` | Benin + Togo test results and local installation guide |
| `run_benin_togo.py` | Benin + Togo test run: v00 comparison, sensitivity, QA maps |
| `tests/` | offline tests on synthetic data (`pytest roads_merge/tests`) |
| `original/Claude_merge_roads_v00.py` | the script being improved, unchanged |
| `results_benin_togo/` | small outputs committed by CI (`.github/workflows/roads_merge.yml`) |

## Run

```bash
pip install -r roads_merge/requirements.txt
python roads_merge/merge_roads.py \
  --osm-pbf    data/benin-260901.osm.pbf data/togo-260901.osm.pbf \
  --osm-pbf-t1 data/benin-200101.osm.pbf data/togo-200101.osm.pbf \
  --ms-roads   data/Western_Africa.zip \
  --iso3 BEN TGO --out-dir output
# add --template landcover.tif so the output grid matches your land-cover raster
```

Data (checked 2026-09-25):
- OSM: Geofabrik keeps yearly snapshots, e.g.
  `https://download.geofabrik.de/africa/benin-200101.osm.pbf` (2016–2026 for Benin; Togo has 200101 and 260901).
- Microsoft: drop 2025-04-28, region **Western Africa** (306 MB):
  `https://usaminedroads.z19.web.core.windows.net/drops/2025.04.28/Western_Africa.zip`.
  Rows are `ISO3<TAB>GeoJSON Feature`; each feature has a `WidthMeters` property.
  Licence: ODbL.

## What changed relative to v00, and why

| # | v00 | Now | Why it matters |
|---|---|---|---|
| 1 | `MS_ZIP = "Africa-Full.zip"`, one ISO3 | `Western_Africa.zip` (current file name), several ISO3 at once, `WidthMeters` kept | the v00 file name is not in the current README; Benin + Togo in one run; width is usable for QA/speed classes |
| 2 | `pyrosm` | GDAL OSM driver via `pyogrio` (already a geopandas dependency) | one fewer dependency; several extracts read and de-duplicated on `osm_id` (border roads) |
| 3 | unpaved factor only when `surface` is tagged | `paved_if_missing` column in `speed_table.csv` | the chat recommended defaulting rural tertiary-and-below to unpaved, but v00 did not implement it |
| 4 | overlap = per-segment union of OSM buffers | sample points every 10 m + STRtree `dwithin` | same decision rule; ~2x faster in a synthetic benchmark (20 000 ML segments: 14.8 s → 6.8 s), 0.4% of keep/drop decisions differ (short segments) |
| 5 | — | `flag_new_roads()` + `--osm-pbf-t1` | the original question (new roads between two dates) was not handled by v00; matching is by geometry, not `osm_id`, because ways get split/re-drawn |
| 6 | grid origin = road bounds; crashes if bounds have zero height | grid snapped to multiples of `RES_M`; optional `--template` | rasters from two dates now share cell boundaries, so they can be differenced |
| 7 | hard-coded settings | CLI arguments, speed table in CSV | reproducible re-runs for updates |
| 8 | no tests | 9 offline tests + CI run on real Benin/Togo data | |

## Caveats (not fixed by code)

- **"New in OSM" ≠ "new on the ground".** OSM growth in Benin/Togo is dominated by
  mapping campaigns (HOT, Microsoft/Facebook imports). A road flagged new between
  2020 and 2026 may have existed for decades. To date construction you need imagery
  (e.g. check flagged roads against a 2020 and a 2026 Sentinel-2/Planet mosaic)
  or an independent source.
- **Microsoft roads have a single, unknown date** ("freshest available imagery",
  per the RoadDetections README). They cannot be assigned to either timepoint, so
  adding them to a t1 network makes it look more complete than it was.
  For a two-date comparison, compare OSM with OSM only, and use the ML roads
  for the current map.
- **Borders.** Cotonou–Lagos, Lomé–Accra and the Nigerian/Ghanaian/Burkinabe cities near
  the borders matter for travel time. Include neighbouring countries (or at least a
  ~100 km buffer) in the network and destination set, then clip the result.
- **Speeds** remain the largest source of error; calibrate them.
- ML roads (15 km/h) are faster than unpaved OSM tracks (15 × 0.7 = 10.5 km/h), so
  where both overlap in one cell the ML value wins. Adjust `--ml-speed` if you calibrate.

## Friction maps for two dates (`friction.py`)

Speed per 100 m cell, fastest option wins:

- **road cells:** class speed from `speed_table.csv` (unpaved factor included);
- **off-road cells:** land-cover walking speed (`landcover_speed.csv`, flat terrain)
  × Tobler factor `exp(-3.5 × tan(slope))`, slope from Copernicus GLO-30 averaged to
  the grid. Water (WorldCover 80) is impassable unless a road crosses it.

Friction = 60 / (1000 × speed) min/m, the unit of the Malaria Atlas Project surfaces.

```bash
python friction.py \
  --osm-pbf-t1 data/benin-200101.osm.pbf data/togo-200101.osm.pbf \
  --osm-pbf-t2 data/benin-260901.osm.pbf data/togo-260901.osm.pbf \
  --boundary data/benin.poly data/togo.poly \
  --ms-roads data/Western_Africa.zip --iso3 BEN TGO \
  --out-dir output_friction
```

Outputs: `friction_t1.tif`, `friction_t2.tif`, `friction_t2_ml.tif` (with `--ms-roads`),
`speed_change_t2_minus_t1_kmh.tif`, `friction_summary.csv`.

- Land cover: by default ESA WorldCover **2021 for both dates**, so that only roads
  change between the maps. WorldCover 2020 (v100) and 2021 (v200) were made with
  different algorithms, so differencing them mixes real change with method change.
  Pass `--landcover-t1` / `--landcover-t2` to override.
- Tiles are read from the public S3 buckets by default; pass local files with
  `--landcover-t1` and `--dem` to work offline.
- **Updating an existing friction map:** `--base-friction existing.tif` keeps that
  raster's grid and values off-road and burns only the roads of each date into it.
  Roads already in the base map stay; roads absent at t1 cannot be removed.
- Slope at 100 m is gentler than at 30 m, so the Tobler penalty is conservative.
- `landcover_speed.csv` values are placeholders in the 1–5 km/h range; calibrate them.

## Travel time to cities and ports (`traveltime.py`)

Least-cost travel time (8 neighbours, `skimage.graph.MCP_Geometric`) from every cell
to the nearest destination, on the friction rasters from `friction.py`.

| `to` | size | destinations |
|---|---|---|
| city | 1–9 | 5–50 M, 1–5 M, 0.5–1 M, 200–500 k, 100–200 k, 50–100 k, 20–50 k, 10–20 k, 5–10 k inhabitants |
| port | 1–5 | Large, Medium, Small, Very small, Any (World Port Index `Harbor Size`) |

A size means "this class or larger" (city 6 = at least 50,000 inhabitants, the default);
`--exact-class` uses the class alone. Cities are built per date from GHSL R2023A:
8-connected GHS-SMOD urban-cluster / urban-centre cells (codes 21, 22, 23, 30) with
GHS-POP population summed; `--cities` accepts your own layer with a `pop` column instead.

```bash
python traveltime.py \
  --friction output_friction/friction_t1.tif output_friction/friction_t2.tif \
  --labels 2020 2026 \
  --smod data/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V2_0.zip data/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.zip \
  --pop  data/GHS_POP_E2020_GLOBE_R2023A_54009_1000_V1_0.zip  data/GHS_POP_E2025_GLOBE_R2023A_54009_1000_V1_0.zip \
  --ports data/UpdatedPub150.csv \
  --city-sizes 6 7 8 9 --port-sizes 1 5 --out-dir output_tt
```

Outputs per date and layer: `traveltime_<date>_<layer>.tif` (minutes), change rasters
between consecutive dates, `cities_<date>.gpkg`, `ports_<date>.gpkg` and
`traveltime_summary.csv` (population-weighted mean time, share of people within
30/60/120/240 min).

- Destinations are only reachable inside the passable part of the friction grid. With
  a friction map masked to Benin + Togo, Lagos, Accra/Tema and cities in Burkina Faso,
  Niger and Nigeria near the border are not counted. Build the friction surface over a
  wider area (neighbouring OSM extracts, buffered `--boundary`) to include them.
- Ports on a water cell are moved to the nearest passable cell within 5 km.
- GHSL 2025 is a projection made by GHSL, not an observation (my understanding of
  R2023A; check the GHSL documentation).
