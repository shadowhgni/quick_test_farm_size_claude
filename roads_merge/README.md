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
