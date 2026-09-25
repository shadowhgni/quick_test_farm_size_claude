# global_accessibility_v2.py — travel time to cities and ports, two reference years

**Use `global_accessibility_v2.py`** (version 2.0.3). It is version 1 (`global_accessibility.py`, kept
for reference) plus a sensitivity analysis of the governance factor K and of the African
border-crossing delay (stage `sensitivity`, see below).

One stand-alone Python file (Python ≥ 3.11; written for 3.13). It installs the Python
packages it is missing, downloads all inputs, and produces for a start and an end year:

- travel time to cities (12 layers) and ports (5 layers) on the 30″ (~1 km) grid of
  Nelson et al. (2019), plus a 10 km "light" version;
- the change between the two years;
- a comparison with Nelson et al. (2019) and a validation against a free routing engine;
- a `methods/` folder with every input, parameter and version needed for a paper.

Intermediate files are deleted at the end; only `RESULTS_DIR` is kept.

## Run it

Edit the configuration block at the top of the script (years, folders, speeds,
penalties), then, in a terminal or a Jupyter cell:

```bash
python global_accessibility_v2.py --dry-run     # grid size, workers, memory, OSM downloads
python global_accessibility_v2.py               # full run (resumable: rerun after a crash)
```

Useful options: `--start 2015 --end 2026`, `--bbox W S E N` (regional run),
`--stages download,grids` (run part of the chain), `--max-workers N`, `--no-cleanup`,
`--no-ml`, `--no-weiss`, `--no-routing`, `--no-sensitivity`, `--sens-design oat|full`, `--routing-cities N`, `--work-dir`, `--results-dir`.

### If something goes wrong at start-up or while planning downloads

- **PROJ** (`ERROR 1: PROJ: ... Open of /opt/conda/share/proj failed`, or unknown EPSG codes):
  at start-up the script tests the PROJ setting as it is, then without `PROJ_DATA`/`PROJ_LIB`,
  then every `proj.db` folder shipped with the installed packages or the environment. It keeps
  the first one that works with no PROJ error and prints `[bootstrap] PROJ data: ...`. To force
  a folder, set `GA_PROJ_DATA=/path/to/folder/with/proj.db`.
- **Geofabrik**: snapshots are found from each folder's directory listing (about 50 requests,
  cached for 7 days in `WORK_DIR/downloads/geofabrik_listing`), not by probing each file.
  Network errors, HTTP 429 and 5xx are retried with backoff; if the server stays unreachable, or
  if more than half of the regions have no extract, the script stops with a message instead of
  building maps without roads. Check `curl -I https://download.geofabrik.de/africa/` from the
  node, wait, and rerun.

No container tools are needed. Missing packages are installed with
`pip install --target WORK_DIR/pylib`, so no administrator rights are required.

## Pipeline

| Stage | What it does |
|---|---|
| `download` | OSM extracts from Geofabrik for 1 January of each year (smallest regions with a snapshot, falling back to parent regions, then to the next year's snapshot, at most `OSM_SNAPSHOT_MAX_LAG` = 1 year later, e.g. Russia 2016 for 2015); Microsoft ML roads; GHSL SMOD + POP (nearest 5-year epoch); World Port Index; Natural Earth countries; World Bank WGI; Copernicus DEM tile list; WorldCover tile list; Nelson et al. layers (latest figshare version, MD5-checked) |
| `grids` | WorldCover 2021 at 30″ (mode, read from COG overviews); mean tan(slope) from Copernicus GLO-90 at ~180 m; countries; African land borders; settlements per GHSL epoch (8-connected urban clusters) and population on the grid |
| `roads` | per OSM extract in parallel: road speeds, burned at 30″ (fastest road per cell), km by class, border checkpoints; Microsoft roads (end year) |
| `friction` | per year: speed = max(road speed × corruption factor, walking speed × Tobler) → minutes per metre; +15 min (× corruption) at African border checkpoints |
| `traveltime` | per year × 17 layers in parallel: multi-source Dijkstra on the lon/lat grid (step lengths depend on latitude; wraps at the dateline) |
| `outputs` | COGs (1 km, 10 km), global PNGs, population-weighted tables, methods folder |
| `compare` | against Nelson et al. (2019), layer by layer; all cells and tiles where OSM 2015 was complete |
| `validate` | end year against OSRM (car, free flow) for sampled origin–city pairs |
| `sensitivity` | K ∈ {0, 0.05, 0.10, 0.20} and border delay ∈ {0, 15, 30, 60} min, one at a time around the baseline (K = 0.10, 15 min; 7 scenarios) or all 16 combinations (`--sens-design full`); headline layers (cities 11, ports 5), both years; population-weighted results by country, continent and domain |
| `cleanup` | deletes the work folder (keeps the installed packages) |

## Parallelism and memory

The script reads the cores and memory it may use, including container cgroup limits.
It plans each parallel stage from a per-task memory estimate plus ~0.35 GB of process
overhead, keeping within 75% of the available memory (`MEMORY_FRACTION`):

| Stage | Per task | Notes |
|---|---|---|
| OSM extracts | 1.5 GB + 7 × .pbf size | largest extracts start first |
| Travel time | ~10 bytes × 752 M cells ≈ 7.8 GB | 34 tasks (2 years × 17 layers); friction is memory-mapped and shared |
| WorldCover / DEM reads | threads (I/O bound) | `REMOTE_READ_THREADS` |
| Downloads | `DOWNLOAD_WORKERS` = 4 | polite to Geofabrik |

Measured: one travel-time layer on a 32 M-cell grid takes ~40 s on one core. On the
752 M-cell global grid only land cells are processed (~25–30%), so expect roughly
5–15 min per layer; with enough memory all 34 layers run at once. Rough needs for a
global run: ~170 GB of OSM downloads (2015 + 2026), 16.5 GB of Microsoft roads, 7.4 GB of
Nelson layers, ~150 GB of intermediate grids on disk, and a peak RAM of
(number of parallel travel-time tasks × ~8 GB) + ~15 GB. Run `--dry-run` on your node for
its own figures.

## Method choices to state in a paper

- **Grid:** WGS84, 30″, −180…180° / −60…85° (as Nelson et al. 2019). The light version
  averages 10 × 10 cells (valid cells only).
- **Roads:** OSM `highway` classes → `SPEED_TABLE`. Unpaved (tagged, or untagged minor
  classes) × 0.7. Fastest road wins in a cell. Microsoft ML roads (undated) are used for
  the end year only, at 15 km/h, in cells with no OSM road.
- **2015 roads completed with Weiss et al. (2018):** OSM in 2015 missed many roads that the
  2015 friction surface of Weiss et al. (OSM + Google roads; Malaria Atlas Project, CC BY 4.0,
  downloaded by WCS) contains. A 30″ cell gets a 2015 road when OSM 2015 has none, the Weiss
  surface is ≥ 10 km/h there, and OSM of the end year has a road there (this excludes the
  rivers, sea lanes and railways in the Weiss surface, and open water). Its speed is
  min(Weiss speed, end-year OSM speed). Done before any travel-time calculation; the number
  of cells added is in `methods/friction_2015.json`. Only for START_YEAR = 2015.
- **Where OSM 2015 data exist:** per 2° tile, completeness = OSM 2015 road cells / Weiss 2015
  network cells that are roads today (before completion). The Nelson comparison is reported
  for all cells and for tiles ≥ 80% complete (`methods/osm2015_completeness_tiles.csv`).
- **Units:** travel times in minutes (uint16, nodata 65535, as Nelson et al.); change in
  minutes (int16); friction in minutes per metre. Units are written into each COG band.
- **Water:** waterways and ferries are not used as travel links (only OSM `highway=*`).
  WorldCover water is impassable. A road on a cell that is ≥ 90% water (share computed from
  WorldCover at ~185 m) is removed unless the OSM way is a bridge, causeway (`bridge=*`),
  ford or embankment; Microsoft roads on such cells are always removed. Counts of removed
  and kept cells are in `methods/friction_<year>.json`. Islands reached only by ferry are
  unreachable from the mainland.
- **Off-road:** WorldCover 2021 walking speeds (`LANDCOVER_SPEED`, placeholders to be
  calibrated) × exp(−3.5 tan slope), for both years. Water is impassable unless a road
  crosses it.
- **Corruption:** World Bank WGI Control of Corruption score (0–100; latest year ≤ the
  reference year; continent median where missing). c = 1 − score/100; road speed ×
  (1 − K·c), K = 0.10. Off-road walking is not penalised.
- **Borders:** only between two African countries (Natural Earth 10 m), only at official
  checkpoints, i.e. motorway/trunk/primary/secondary roads crossing a land border:
  15 min / (1 − K·c̄), c̄ = mean of the two countries. Crossing elsewhere is not
  penalised, so a short walk around a checkpoint can be cheaper than the delay.
- **Destinations:** GHSL R2023A urban clusters (SMOD 21–30, 8-connected, population
  from GHS-POP), nearest epoch to each year; World Port Index harbour size (current
  edition). Layer definitions are those of Nelson et al. (2019): cities 1–9 are single
  classes, 10–12 cumulative; ports 1–4 single classes, 5 any.
- **Cost distance:** 8-neighbour Dijkstra. Step cost = mean friction of the two cells ×
  great-circle step length (east–west = R cos φ Δλ).
- **Validation:** OSRM car profile, free flow (no traffic), current OSM. Its times are a
  lower bound for real trips, and it has no walking segments or border delays.

## Outputs (`RESULTS_DIR`)

```
cog_1km/   traveltime_<year>_1km.tif (17 bands, uint16 min, nodata 65535)
           friction_<year>_1km.tif (min/m), traveltime_change_<end>_minus_<start>_1km.tif (int16)
cog_10km/  the same at 300″
png/       one global map per layer and year, friction, and change maps
tables/    population-weighted travel time by country / continent / globe
nelson_comparison/   per-layer statistics, per-continent means, difference maps, scatter plots
routing_validation/  origin–city pairs, summary by continent, scatter plot, attribution
sensitivity/         scenarios, results by domain / continent / country (vs baseline), figure
methods/   config.json, speed_table.csv, landcover_speed.csv, corruption_<year>.csv,
           checkpoints_<year>.csv, african_borders.gpkg, settlements_<epoch>.csv,
           destinations.csv, road_km_by_extract.csv, osm_plan.json, inputs_manifest.csv,
           nelson2019_figshare.json, software_versions.json, timings.csv, run_log.txt
```

## Sources and licences

OpenStreetMap (ODbL; Geofabrik extracts) · Microsoft Road Detections (ODbL) · ESA
WorldCover 2021 (CC BY 4.0) · Copernicus DEM GLO-90 (Copernicus licence) · GHSL R2023A
(CC BY 4.0) · World Port Index, NGA Pub. 150 · Natural Earth (public domain) · World Bank
WGI (World Bank terms of use) · Nelson, A. et al. (2019) figshare 10.6084/m9.figshare.7638134
(CC BY 4.0) · OSRM demo / FOSSGIS routing servers (OSM data, ODbL; ≤ 1 request/s).
Licences as I understand them; check each provider's terms before publication.
