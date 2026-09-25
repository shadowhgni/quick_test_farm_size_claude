# Test report — accessibility update, Benin and Togo (2020 vs 2026)

Date: 2026-09-25. Code: `scripts/`, settings: `config/`, results: `results/` (see README.md).
Original script under test: `scripts/original/Claude_merge_roads_v00.py`.

## 1. What was tested

| Input | Version |
|---|---|
| OSM, t1 | Geofabrik `benin-200101.osm.pbf`, `togo-200101.osm.pbf` (snapshots of 2020-01-01) |
| OSM, t2 | Geofabrik `benin-260901.osm.pbf`, `togo-260901.osm.pbf` (2026-09-01) |
| Microsoft ML roads | drop 2025-04-28, `Western_Africa.zip`, rows `BEN` and `TGO` |

Default settings: buffer 20 m, max overlap 0.5, min ML length 50 m, 100 m raster,
projection EPSG:32631 (UTM 31N).

The runs were done on GitHub Actions `ubuntu-latest` runners in the
`quick_test_farm_size_claude` repo. Road figures are from roads run #3 (repeated
identically in later runs); town figures from run #1 of `accessibility.yml`, because downloads were not permitted in the
development container. Raw outputs: `results/roads/`, `results/friction/`,
`results/traveltime/`, `results/towns/`.

## 2. Results

### 2.1 Correctness and speed versus v00

| Check | Result |
|---|---|
| Offline tests (synthetic data) | 9 / 9 pass |
| ML segments compared | 260,374 (after dropping < 50 m) |
| Keep/drop decisions that differ from v00 | 865 segments (0.33%), 96 km of 68,886 km |
| Mean overlap fraction, new vs v00 | 0.848 vs 0.848 |
| Conflation time | 40 s (new) vs 96 s (v00), ~2.4x faster |
| Other steps | read inputs 25 s; new + gone road flags 154 s; write gpkg + tif 9 s |

The differences come from sampling every 10 m instead of exact polygon intersection;
they concern short segments near the 50% threshold.

### 2.2 Road network (km)

| | Benin | Togo |
|---|---:|---:|
| OSM 2020-01-01 | 67,827 | 37,146 |
| OSM 2026-09-01 | 72,071 | 52,753 |
| Net OSM change | +4,244 | +15,608 |
| OSM segments flagged new since 2020 | 9,861 | 14,501 |
| OSM 2020 segments with no 2026 counterpart ("gone") | 3,784 | 1,189 |
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

`results/roads/qa_*.png`: 10 × 10 km windows around Parakou, Kandi, Kara and
Dapaong (each window is centred on the town).

- ML roads flagged as duplicates sit on OSM roads, as intended.
- The kept ML roads are mostly short street segments inside towns, not long rural links.
- Roads new in OSM since 2020 (blue) are mostly rural tracks around Dapaong, and
  new neighbourhood streets around Kandi.

### 2.5 Friction maps 2020 and 2026 (`friction.py`)

Friction runs #1–#2 (before the workflows were merged into `accessibility.yml`; 274–352 s, tiles read remotely). 100 m grid,
4,441 × 7,256 cells, EPSG:32631, masked to the Geofabrik outlines of Benin and Togo
(slightly buffered, hence 176,597 km² of valid cells). Land cover: ESA WorldCover 2021
for both dates, so only roads differ. Two Copernicus DEM tiles over the sea
(N05 E002, N05 E003) do not exist and were skipped, as expected.

| | 2020 (OSM) | 2026 (OSM) | 2026 (OSM + ML) |
|---|---:|---:|---:|
| Road cells | 1,053,788 | 1,279,894 (+21%) | 1,387,214 (+32%) |
| Cells faster than 2020 | – | 361,556 | 467,806 |
| Cells slower than 2020 | – | 70,846 | 70,550 |
| Mean speed (km/h) | 4.25 | 4.48 | 4.56 |
| Mean friction (min/m) | 0.02061 | 0.02040 (−1.0%) | 0.02030 (−1.5%) |

- About 2% of the area got faster. The mean friction barely moves because most cells
  are off-road; the effect on travel time is concentrated along the new roads and
  has to be measured with a cost-distance run (not done yet).
- The 70,846 slower cells had a road in 2020 and not in 2026 at the same place, or a
  road that was downgraded (class or surface). This matches the "gone" roads in 2.2,
  i.e. mostly roads re-drawn elsewhere or deleted; treat them as map edits, not as
  roads that disappeared on the ground.
- Visual checks (`results/friction/`): the country-wide maps and the
  20 × 20 km zooms around Dapaong and Kandi show the new 2026 roads as expected, and
  the reservoir west of Dapaong as impassable. At 100 m with `all_touched`, roads
  are 1–3 cells wide.
- `landcover_speed.csv` holds placeholder walking speeds, so the absolute friction
  values off-road are not calibrated; the 2020 vs 2026 difference on roads does not
  depend on them.

### 2.6 Travel time to cities and ports (`traveltime.py`)

Run #3 of the friction + travel-time workflow (308 s for 16 cost-distance runs on the
4,441 × 7,256 grid). Population inside the Benin + Togo outlines: 21.0 M (GHS-POP 2020),
23.9 M (2025).

Population-weighted mean travel time (minutes) and share of people within 60 min:

| layer | 2020 | 2026r (new roads) | 2026 (+ city growth) | 2026ml (+ ML roads) |
|---|---:|---:|---:|---:|
| cities ≥ 50k (city6) | 24.6 (83.3%) | 21.5 (86.3%) | 21.4 (86.1%) | 21.1 (86.3%) |
| cities ≥ 5k (city9) | 9.5 (95.8%) | 8.2 (97.2%) | 8.1 (97.1%) | 7.9 (97.4%) |
| any port (port5) | 228.0 (31.7%) | 219.6 (32.4%) | 219.8 (33.0%) | 217.0 (33.4%) |

- New OSM roads account for almost all of the change to cities ≥ 50k (−3.1 min); city
  growth (−0.1) and the Microsoft gap-fill (−0.3) add little at this scale.
- Some areas get slower from the road changes alone, up to +60 min and more
  (`results/traveltime/traveltime_city6_change.png`), e.g. a large patch in north-western
  Benin. These are areas where 2020 roads have no 2026 counterpart. A likely cause is
  tracks deleted or retagged to classes outside the speed table (e.g. `path`); I have not
  checked this against the OSM history.
- Ports: only Cotonou, Lomé and Kpémé are inside the outlines; Lagos, Lekki, Tin Can
  Island and Tema are not reachable with the masked friction map, so port times in the
  east and west are too long.
- Reachable destinations (run #1 of `accessibility.yml`, identical travel times): of the
  cities ≥ 50k in the bounding box, 52 of 105 (2020) and 50 of 102 (2025) lie on the
  passable map; the rest are in Nigeria, Ghana, Burkina Faso or Niger. Ports: 3 of 5
  (Cotonou, Lomé, Kpémé). `settlements_by_class.csv` now lists reachable ones only.

### 2.7 Nine Beninese towns (`run_towns_benin.py`)

Run #1 of `.github/workflows/accessibility.yml`. Each town is summarised over its
commune (geoBoundaries ADM2), so rural parts of large communes (Kandi, Malanville,
Djougou: 3,300–3,900 km²) weigh heavily, while Cotonou and Porto-Novo are almost entirely
built-up. Files: `results/towns/town_summary.csv`, `town_traveltime.csv`,
`overview_city6.png`, `map_<town>.png`.

**Roads and population**

| town | area km² | pop 2020 → 2025 | OSM 2020 km | new | gone | ML added | density 2020 → 2026+ML (km/km²) | cells faster |
|---|---:|---|---:|---:|---:|---:|---|---:|
| Parakou | 473 | 362k → 442k | 1,722 | 282 | 22 | 103 | 3.64 → 4.43 | 5.6% |
| Kandi | 3,489 | 246k → 289k | 1,222 | 366 | 1 | 227 | 0.35 → 0.53 | 1.1% |
| Malanville | 3,261 | 217k → 254k | 1,042 | 256 | 2 | 316 | 0.32 → 0.50 | 1.1% |
| Cotonou | 81 | 808k → 884k | 995 | 54 | 20 | 23 | 12.34 → 13.27 | 24.5% |
| Porto-Novo | 50 | 345k → 385k | 661 | 7 | 10 | 17 | 13.30 → 13.90 | 10.2% |
| Comè | 172 | 92k → 100k | 490 | 12 | 26 | 18 | 2.84 → 2.86 | 2.3% |
| Sakété | 425 | 133k → 151k | 667 | 72 | 8 | 103 | 1.57 → 1.98 | 3.4% |
| Natitingou | 1,356 | 125k → 136k | 772 | 52 | 0 | 60 | 0.57 → 0.65 | 0.9% |
| Djougou | 3,921 | 337k → 396k | 1,446 | 280 | 4 | 209 | 0.37 → 0.49 | 0.8% |

**Population-weighted mean travel time (minutes)**, scenarios as in 2.6:

| town | city ≥ 50k: 2020 | 2026r | 2026 | 2026ml | city ≥ 5k: 2020 → 2026ml | any port: 2020 → 2026ml |
|---|---:|---:|---:|---:|---|---|
| Parakou | 0.6 | 0.5 | 0.5 | 0.5 | 0.6 → 0.5 | 358 → 345 |
| Kandi | 20.5 | 20.2 | 22.2 | 21.9 | 12.8 → 13.5 | 571 → 553 |
| Malanville | 20.3 | 19.1 | 19.5 | 19.0 | 8.3 → 6.6 | 651 → 631 |
| Cotonou | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 → 0.0 | 5 → 5 |
| Porto-Novo | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 → 0.0 | 31 → 29 |
| Comè | 2.1 | 2.1 | 0.4 | 0.4 | 0.5 → 0.4 | 54 → 54 |
| Sakété | 8.9 | 6.8 | 3.8 | 3.4 | 4.4 → 2.4 | 69 → 63 |
| Natitingou | 12.3 | 11.1 | 11.8 | 11.7 | 10.7 → 10.3 | 435 → 433 |
| Djougou | 20.5 | 19.3 | 20.7 | 20.1 | 9.9 → 8.3 | 386 → 383 |

- **Cotonou, Porto-Novo and Parakou** are inside a city ≥ 50k almost everywhere, so their
  times to cities are ~0 and do not change. In Cotonou, 24.5% of cells got faster
  (54 km of new OSM roads in 81 km²), which matters for intra-urban travel but not for
  this indicator.
- **New roads** cut the time to cities ≥ 50k by 1.2–2.1 min in Sakété, Malanville,
  Natitingou and Djougou, and by 0.3 min in Kandi. For ports, the northern towns gain
  13–20 min (Parakou, Kandi, Malanville) on trips of 6–11 h.
- **Sakété** improves the most (8.9 → 3.4 min, 99% → 100% of people within 60 min): new
  roads (−2.1) and GHSL growth (−3.0), consistent with nearby settlements crossing the
  50k threshold between the 2020 and 2025 epochs. **Comè** drops from 2.1 to 0.4 min for
  the same reason (GHSL step only).
- **Kandi and Djougou get slower in the "city growth" step** (+2.0 and +1.4 min). This step
  changes two things at once: the destinations (GHSL 2020 → 2025 settlements) and the
  population weights (GHS-POP 2020 → 2025). An increase can come from either (e.g. faster
  growth in remote parts of the commune, or a settlement falling below the threshold or
  being split). I cannot tell which from the committed outputs; a fifth scenario (2025
  settlements with 2020 weights) would separate them.
- **Roads that got slower:** the Kandi map shows a patch in the north-west up to 30 min
  slower from road changes alone, yet only 1.2 km of Kandi's 2020 roads are "gone". The
  roads there most likely still exist but were downgraded (class or surface tag); I have
  not checked the OSM tags.
- **Microsoft roads** add 17–316 km per commune, most in the large rural communes
  (Malanville 316 km, Kandi 227, Djougou 209), and cut 0.3–0.6 min further there.
- Travel times near the Nigerian border (Malanville, Kandi, Sakété, Porto-Novo) ignore
  Nigerian cities and ports (see 2.6), so they are upper bounds.

## 3. Findings to act on

1. **The "new since 2020" flag over-counts in Benin, much less in Togo.**
   In Benin, 9,861 km is flagged new but net growth is only 4,244 km, and 3,784 km of
   2020 roads have no 2026 counterpart within 20 m. Those "gone" roads were either
   deleted or re-drawn elsewhere (e.g. re-traced on better imagery); if re-drawn, their
   new position is counted as new. So up to ~3,800 km (38%) of Benin's "new" roads may
   be moved roads rather than additions. The outputs cannot separate deleted from
   moved; a visual check of a sample of "gone" segments in QGIS would.
   In Togo, only 1,189 km is gone (8% of the 14,501 km flagged new).
   The accounting does not close exactly (new − gone ≠ net change: 6,078 vs 4,244 km in
   Benin, 13,313 vs 15,608 km in Togo) because the flag is all-or-nothing per segment:
   a way that was extended or partly re-drawn counts as entirely new or entirely
   existing depending on which side of the 50% threshold it falls. Measuring only the
   part of each segment outside the buffer would fix this.
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
git clone https://github.com/shadowhgni/quick_test_farm_size_claude.git
cd quick_test_farm_size_claude
git checkout claude/roaddetections-fork-test-m1plof
cd accessibility_update
conda create -n access -c conda-forge python=3.11 geopandas pyogrio shapely rasterio \
    pyarrow matplotlib scikit-image scipy pytest
conda activate access
```

Or with pip (Python 3.10–3.12). The `pyogrio` and `rasterio` wheels ship their own GDAL,
including the OSM driver used to read `.pbf` files (checked with pyogrio 0.13 / GDAL 3.12.4):

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r scripts/requirements.txt
```

Check the install (no downloads needed, ~15 s):

```bash
python -m pytest scripts/tests -q
```

### 4.2 Download the data (~1.5 GB) into `accessibility_update/data/`

```bash
mkdir -p data && cd data
for c in benin togo; do
  for t in 200101 260901; do
    curl -fLO https://download.geofabrik.de/africa/$c-$t.osm.pbf
  done
  curl -fLO https://download.geofabrik.de/africa/$c.poly
done
curl -fLO https://usaminedroads.z19.web.core.windows.net/drops/2025.04.28/Western_Africa.zip
G=https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL
for y in 2020 2025; do
  curl -fLO $G/GHS_SMOD_GLOBE_R2023A/GHS_SMOD_E${y}_GLOBE_R2023A_54009_1000/V2-0/GHS_SMOD_E${y}_GLOBE_R2023A_54009_1000_V2_0.zip
  curl -fLO $G/GHS_POP_GLOBE_R2023A/GHS_POP_E${y}_GLOBE_R2023A_54009_1000/V1-0/GHS_POP_E${y}_GLOBE_R2023A_54009_1000_V1_0.zip
done
curl -fL -o UpdatedPub150.csv "https://msi.nga.mil/api/publications/download?type=view&key=16920959/SFH00000/UpdatedPub150.csv"
curl -fL -o geoBoundaries-BEN-ADM2.geojson https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/BEN/ADM2/geoBoundaries-BEN-ADM2.geojson
cd ..
```

On Windows PowerShell, replace `curl -fLO URL` with
`Invoke-WebRequest URL -OutFile <file name>`, or download the files in a browser.
Land cover (WorldCover) and elevation (Copernicus) are read over the internet during
step 2; pass local tiles to `friction.py` with `--landcover-t1` and `--dem` to work offline.

### 4.3 Run

The four steps, in order (each reads the previous step's `output/`):

```bash
python scripts/run_roads_benin_togo.py        # -> results/roads/,      output/roads/
python scripts/run_friction_benin_togo.py     # -> results/friction/,   output/friction/
python scripts/run_traveltime_benin_togo.py   # -> results/traveltime/, output/traveltime/
python scripts/run_towns_benin.py             # -> results/towns/
```

For other countries, dates or layers, call the modules directly, e.g.:

```bash
python scripts/merge_roads.py --osm-pbf <t2.pbf ...> --osm-pbf-t1 <t1.pbf ...> \
  --ms-roads data/Western_Africa.zip --iso3 BEN TGO --out-dir output/my_roads
python scripts/friction.py --osm-pbf-t1 <...> --osm-pbf-t2 <...> \
  --boundary data/benin.poly --out-dir output/my_friction   # or --base-friction existing.tif
python scripts/traveltime.py --friction output/my_friction/friction_t1.tif output/my_friction/friction_t2.tif \
  --labels 2020 2026 --smod <smod 2020> <smod 2025> --pop <pop 2020> <pop 2025> \
  --ports data/UpdatedPub150.csv --city-sizes 6 7 8 9 --port-sizes 1 5 --out-dir output/my_tt
```

Open `output/roads/roads_merged.gpkg` (layers `roads` and `osm_t1`) and the GeoTIFFs in
QGIS to review them.

Resources: on the GitHub runner (4 CPU, 16 GB RAM) steps 1–3 take about 6, 5 and 5 min.
Each cost-distance run on the 32 M-cell grid takes ~30 s. I did not measure peak memory.

### 4.4 GitHub Actions (optional)

`.github/workflows/accessibility.yml` installs, runs the tests, downloads the inputs,
runs steps 1–4 and commits `results/` back. It starts on pushes that change
`accessibility_update/scripts/` or `config/`, or by hand ("Run workflow").
GitHub only runs workflows from `.github/workflows/`. On a fork, Actions are disabled
until you enable them in the repository's **Actions** tab.
