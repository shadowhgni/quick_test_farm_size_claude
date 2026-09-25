# Test report — OSM + Microsoft ML roads merge, Benin and Togo

Date: 2026-09-25. Code: `roads_merge/` (this folder). Original script under test:
`original/Claude_merge_roads_v00.py`.

## 1. What was tested

| Input | Version |
|---|---|
| OSM, t1 | Geofabrik `benin-200101.osm.pbf`, `togo-200101.osm.pbf` (snapshots of 2020-01-01) |
| OSM, t2 | Geofabrik `benin-260901.osm.pbf`, `togo-260901.osm.pbf` (2026-09-01) |
| Microsoft ML roads | drop 2025-04-28, `Western_Africa.zip`, rows `BEN` and `TGO` |

Default settings: buffer 20 m, max overlap 0.5, min ML length 50 m, 100 m raster,
projection EPSG:32631 (UTM 31N).

The run was done on a GitHub Actions `ubuntu-latest` runner (runs #1 and #2 in the
`quick_test_farm_size_claude` repo), because downloads were not permitted in the
development container. Raw outputs: `results_benin_togo/`.

## 2. Results

### 2.1 Correctness and speed versus v00

| Check | Result |
|---|---|
| Offline tests (synthetic data) | 9 / 9 pass |
| ML segments compared | 260,374 (after dropping < 50 m) |
| Keep/drop decisions that differ from v00 | 865 segments (0.33%), 96 km of 68,886 km |
| Mean overlap fraction, new vs v00 | 0.848 vs 0.848 |
| Conflation time | 40 s (new) vs 92 s (v00), ~2.3x faster |
| Other steps | read inputs 23 s; new-road flag 81 s; write gpkg + tif 8 s |

The differences come from sampling every 10 m instead of exact polygon intersection;
they concern short segments near the 50% threshold.

### 2.2 Road network (km)

| | Benin | Togo |
|---|---:|---:|
| OSM 2020-01-01 | 67,827 | 37,146 |
| OSM 2026-09-01 | 72,071 | 52,753 |
| OSM segments flagged new since 2020 | 9,861 | 14,501 |
| Microsoft ML total | 42,694 | 26,192 |
| Microsoft ML kept (not in OSM 2026) | 8,194 (19%) | 3,020 (12%) |
| Merged network | 80,265 | 55,774 |

Per class (`road_length_by_class.csv`), new OSM length is almost all low-class:
track, unclassified and residential. New primary roads: 29 km (Benin), 8 km (Togo).
In Togo, track length almost doubled (5,096 km → 10,126 km).

### 2.3 Sensitivity of the gap-fill to the two settings

ML length kept (`sensitivity_buffer_overlap.csv`):

| buffer | max overlap 0.3 | 0.5 | 0.7 |
|---|---|---|---|
| Benin 10 m | 8,077 | 9,025 | 10,399 |
| Benin 20 m | 7,346 | **8,194** | 9,076 |
| Benin 40 m | 6,314 | 7,344 | 8,164 |
| Togo 10 m | 3,243 | 3,845 | 4,709 |
| Togo 20 m | 2,563 | **3,020** | 3,466 |
| Togo 40 m | 2,052 | 2,533 | 3,016 |

Across the tested range, the gap-fill varies by −23% to +27% around the default in Benin,
and by −32% to +56% in Togo, so Togo is more sensitive to these settings.

### 2.4 Visual checks

`results_benin_togo/qa_*.png`: 10 × 10 km windows around Parakou, Kandi, Kara and
Dapaong. The PNGs from run #2 are titled "Kandi_rural" and "Dapaong_rural", but both
windows are centred on the towns; the labels are fixed in the code and the files renamed.

- ML roads flagged as duplicates sit on OSM roads, as intended.
- The kept ML roads are mostly short street segments inside towns, not long rural links.
- Roads new in OSM since 2020 (blue) are mostly rural tracks around Dapaong, and
  new neighbourhood streets around Kandi.

## 3. Findings to act on

1. **The "new since 2020" flag over-counts in Benin.** Net OSM growth is 4,244 km, but
   9,861 km is flagged new. So many 2020 roads were deleted, or re-drawn more than
   20 m away (e.g. re-traced on better imagery), and the re-drawn ones count as new.
   From these outputs I cannot say which. The driver now also reports
   `osm_gone_by_t2_km` (2020 roads with no 2026 counterpart); run it again to
   measure this. In Togo, flagged (14,501 km) ≈ net growth (15,608 km).
2. **New in OSM does not mean newly built.** The pattern (tracks and residential, very
   few primary roads, big jumps in one country) fits mapping campaigns better than
   construction. This is an inference; confirming it needs imagery for a sample of the
   flagged roads (e.g. Sentinel-2 2020 vs 2026).
3. **`WidthMeters` is not a physical width.** Its minimum is 8.2 m and its median is
   11.9 m, which is too wide for rural tracks. Use it only as a relative index
   (kept ML roads: median 9.4; dropped: 13.0, so the gap-fills are the narrower roads).
4. **The ML gap-fill is small but not negligible:** +11% (Benin) and +6% (Togo) network
   length at the default setting. It is mostly urban, where it matters less for
   travel time than in rural areas.
5. Still to do before an accessibility map: include neighbouring countries (Lagos,
   Accra, cities in Burkina Faso and Niger near the border), calibrate speeds, and
   pass `--template` so the output grid matches your land-cover raster.

## 4. Deploy on your computer

### 4.1 Install

With conda/mamba (recommended on Windows; brings GDAL with it):

```bash
git clone https://github.com/shadowhgni/RoadDetections.git
cd RoadDetections
git checkout claude/roaddetections-fork-test-m1plof
conda create -n roads -c conda-forge python=3.11 geopandas pyogrio shapely rasterio pyarrow matplotlib pytest
conda activate roads
```

Or with pip (Linux/macOS/Windows, Python 3.10–3.12). The `pyogrio` and `rasterio`
wheels ship their own GDAL, including the OSM driver used to read `.pbf` files
(checked with pyogrio 0.13 / GDAL 3.12.4):

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r roads_merge/requirements.txt
```

Check the install (no downloads needed, ~5 s):

```bash
python -m pytest roads_merge/tests -q
```

### 4.2 Download the data (~700 MB)

```bash
cd roads_merge
mkdir -p data && cd data
for c in benin togo; do
  for t in 200101 260901; do
    curl -fLO https://download.geofabrik.de/africa/$c-$t.osm.pbf
  done
done
curl -fLO https://usaminedroads.z19.web.core.windows.net/drops/2025.04.28/Western_Africa.zip
cd ..
```

On Windows PowerShell, replace `curl -fLO URL` with
`Invoke-WebRequest URL -OutFile <file name>`, or download the files in a browser into
`roads_merge/data/`.

### 4.3 Run

The full Benin + Togo test (reproduces this report; writes `results_benin_togo/` and
`output_benin_togo/`):

```bash
cd roads_merge
python run_benin_togo.py
```

Your own run (any countries, any dates):

```bash
python merge_roads.py \
  --osm-pbf data/benin-260901.osm.pbf data/togo-260901.osm.pbf \
  --osm-pbf-t1 data/benin-200101.osm.pbf data/togo-200101.osm.pbf \
  --ms-roads data/Western_Africa.zip --iso3 BEN TGO \
  --out-dir output                     # optional: --template landcover.tif
```

Outputs: `roads_merged.gpkg` (layer `roads`; columns `source`, `highway`, `speed`,
`new_since_t1`, `osm_overlap`, `width_m`), `road_speed_kmh.tif` and
`road_length_summary.csv`. Open the GeoPackage in QGIS and style it by `source` and
`new_since_t1` to review the result.

Resources: on the GitHub runner (4 CPU, 16 GB RAM) the full test took a few minutes;
most of the time is the v00 comparison and the sensitivity loop in `run_benin_togo.py`,
which `merge_roads.py` does not do. I did not measure peak memory.

### 4.4 GitHub Actions (optional)

`.github/workflows/roads_merge.yml` re-runs the tests and the Benin + Togo run on
every push that changes `roads_merge/`, and commits `results_benin_togo/` back.
GitHub only runs workflows from `.github/workflows/`, not from other folders.
On a fork, Actions are disabled until you enable them in the repository's
**Actions** tab. You do not need the workflow to run anything on your computer.
