# global_accessibility_v3.py — travel time to cities and ports for several reference years

**Use `global_accessibility_v3.py`** (version 3.0.1). Compared with version 2 (`global_accessibility_v2.py`,
kept for reference):

- **any number of reference years, processed together** (default 2015, 2020, 2026), with change
  maps for every consecutive pair and first → last;
- **OpenStreetMap from one source for all years**: the OSM full-history planet
  (planet.openstreetmap.org, ~152 GB) is cut at 1 January of each year with
  [osmium-tool](https://osmcode.org/osmium-tool/), which the script installs itself from conda-forge
  (mamba/conda, or micromamba from GitHub) into `WORK_DIR/tools`. Geofabrik snapshots remain an
  option (`--osm-source geofabrik`) where download.geofabrik.de is reachable;
- **every grid kept for reuse** in `RESULTS_DIR/store` (see below), readable with `load_store()`;
- **routing validation per continent** with ~2,000 origin–settlement pairs each (10–300 km,
  spread over distance bands), summarised by continent, distance band and country;
- **comparison with all 17 layers of Nelson et al. (2019)** for every year in the CSV tables;
- the Weiss et al. 2015 road completion is applied to every year from 2015 to before the last year.

One stand-alone Python file (Python ≥ 3.11; written for 3.13). It installs the Python
packages it is missing, downloads all inputs, and produces for each reference year:

- travel time to cities (12 layers) and ports (5 layers) on the 30″ (~1 km) grid of
  Nelson et al. (2019), plus a 10 km "light" version;
- the change between the years;
- a comparison with Nelson et al. (2019) and a validation against a free routing engine;
- a `methods/` folder with every input, parameter and version needed for a paper;
- a `store/` folder with every grid, for other scripts.

Intermediate files are deleted at the end, only once every stage has succeeded; `RESULTS_DIR` is kept.

## Run it

Edit the configuration block at the top of the script (years, folders, speeds, penalties), then,
in a terminal (e.g. the JupyterLab terminal):

```bash
python global_accessibility_v3.py --dry-run     # network check, disk, memory, workers, OSM history file
python global_accessibility_v3.py               # full run (resumable: rerun the same command after a crash)
```

Useful options: `--years 2015 2020 2026`, `--osm-source history|geofabrik`, `--bbox W S E N`
(regional run), `--stages download,grids` (run part of the chain), `--max-workers N`, `--no-cleanup`,
`--no-ml`, `--no-weiss`, `--no-routing`, `--skip-network-check`, `--no-sensitivity`,
`--sens-design oat|full`, `--routing-cities-per-continent N`, `--work-dir`, `--results-dir`.

### OSM history: what happens and what it needs

1. The newest dated `history-YYMMDD.osm.pbf` is downloaded (resumable) and checked against the
   `.md5` file published next to it. `OSM_HISTORY_FILE` can name a file already on disk.
2. For each year, side by side: `osmium time-filter` at `YYYY-01-01T00:00:00Z` (a normal planet of
   that date), `osmium tags-filter w/highway` (roads with their nodes), then `osmium extract` into
   `OSM_TILE_DEG` × `OSM_TILE_DEG` land tiles (complete ways). The temporary planet is deleted as soon
   as the roads are extracted.
3. Stage `roads` reads the tiles in parallel exactly as it read Geofabrik extracts. Road lengths are
   clipped to each tile, so a way crossing a tile edge is counted once.

Disk: ~152 GB for the history file plus one temporary planet per year (~60–90 GB each) at the
peak; the dry run prints the estimate and the free space. The cut takes hours (not yet measured on
the full planet); it is resumable per year (`downloads/osm/<year>/tiles.done`).

### Reusing the results in another script

`RESULTS_DIR/store/` holds every grid as a Cloud Optimized GeoTIFF on the 30″ grid: land cover,
water share, slope, off-road speed, countries, Weiss 2015 speeds, Microsoft roads, population and
settlements per GHSL epoch, and per year the OSM road speed, final road speed, road crossings,
friction and the 17 travel-time layers in full precision (float32 minutes; −9999 = unreachable).
`store/manifest.json` describes each file (year, layer, units, dtype, nodata) and `store/tables/`
has the countries, settlements, corruption, checkpoints and OSM plan tables.

```python
import sys; sys.path.insert(0, "/mnt/users/dhougni/global_accessibility")
from global_accessibility_v3 import load_store      # needs only numpy + rasterio
fr, prof = load_store("ga_results", "friction", 2020)
tt, prof = load_store("ga_results", "traveltime", 2026, "cities_11", bbox=(-1, 5.5, 4.5, 13.5))
```

### If something goes wrong at start-up or while planning downloads

- **No internet, or only some sites allowed** (`[Errno 101] Network is unreachable`): before any
  download (and in `--dry-run`) the script contacts every server it needs, writes
  `WORK_DIR/network_check.csv` and stops within seconds, listing the servers this machine cannot
  reach. It switches to IPv4 by itself when only IPv6 fails. Ask IT to allow HTTPS to the listed
  hosts, or run `--stages download,grids` on a machine with internet using the same `--work-dir`
  (stage `grids` reads WorldCover and the DEM remotely), then rerun on the compute node. The routing
  servers are optional: if they are unreachable, the validation is skipped.
- **Downloads are kept until the run succeeds**: `WORK_DIR` (downloads included) is deleted only
  when every stage has finished. A downloaded file is never fetched again while its size matches
  the size recorded when it was downloaded (`<file>.meta.json`); a damaged file is downloaded again
  and replaced only once the new copy is complete.

- **PROJ** (`ERROR 1: PROJ: ... Open of /opt/conda/share/proj failed`, or unknown EPSG codes):
  at start-up the script tests the PROJ setting as it is, then without `PROJ_DATA`/`PROJ_LIB`,
  then every `proj.db` folder shipped with the installed packages or the environment. It keeps
  the first one that works with no PROJ error and prints `[bootstrap] PROJ data: ...`. To force
  a folder, set `GA_PROJ_DATA=/path/to/folder/with/proj.db`.
- **Geofabrik**: snapshots are found from each folder's directory listing (about 50 requests,
  cached for 7 days in `WORK_DIR/downloads/geofabrik_listing`), not by probing each file.
  Network errors, HTTP 429 and 5xx are retried with backoff; if the server stays unreachable, or
  if any region would have no extract at all (`OSM_MAX_MISSING_REGIONS` = 0), the script stops with a message instead of
  building maps without roads. Check `curl -I https://download.geofabrik.de/africa/` from the
  node, wait, and rerun.

No container tools are needed. Missing packages are installed with
`pip install --target WORK_DIR/pylib`, so no administrator rights are required.

## Pipeline

| Stage | What it does |
|---|---|
| `download` | OSM: the full-history planet cut at 1 January of each year into road tiles (default), or Geofabrik snapshots (smallest regions with a snapshot, falling back to parent regions, then to the next year's snapshot, at most `OSM_SNAPSHOT_MAX_LAG` = 1 year later, e.g. Russia 2016 for 2015); Microsoft ML roads; GHSL SMOD + POP (nearest 5-year epoch); World Port Index; Natural Earth countries; World Bank WGI; Copernicus DEM tile list; WorldCover tile list; Nelson et al. layers (latest figshare version, MD5-checked) |
| `grids` | WorldCover 2021 at 30″ (mode, read from COG overviews); mean tan(slope) from Copernicus GLO-90 at ~180 m; countries; African land borders; settlements per GHSL epoch (8-connected urban clusters) and population on the grid |
| `roads` | per OSM tile or extract in parallel: road speeds, burned at 30″ (fastest road per cell), km by class, border checkpoints; Microsoft roads (last year) |
| `friction` | per year: speed = max(road speed × corruption factor, walking speed × Tobler) → minutes per metre; +15 min (× corruption) at African border checkpoints |
| `traveltime` | per year × 17 layers in parallel: multi-source Dijkstra on the lon/lat grid (step lengths depend on latitude; wraps at the dateline) |
| `outputs` | COGs (1 km, 10 km) per year and change COGs per pair of years, global PNGs, population-weighted tables, methods folder |
| `store` | every grid as a COG in `store/` with `manifest.json` (for other scripts; `load_store()`) |
| `compare` | every year against Nelson et al. (2019, 2015), all 17 layers: bias, mean absolute difference (also relative to Nelson), median % difference, share within ±30 min, r(log), population-weighted means; all cells and tiles where OSM 2015 was complete |
| `validate` | last year against OSRM (car, free flow): `ROUTING_CITIES_PER_CONTINENT` = 100 settlements ≥ 50,000 per continent × `ROUTING_ORIGINS_PER_CITY` = 20 population-weighted origins spread over 10–50–100–200–300 km bands (~2,000 pairs per continent); summaries by continent, distance band and country (≥ 30 pairs); resumable |
| `sensitivity` | K ∈ {0, 0.05, 0.10, 0.20} and border delay ∈ {0, 15, 30, 60} min, one at a time around the baseline (K = 0.10, 15 min; 7 scenarios) or all 16 combinations (`--sens-design full`); headline layers (cities 11, ports 5), every year; population-weighted results by country, continent and domain |
| `cleanup` | deletes the work folder, only when every stage has succeeded (keeps the installed packages and osmium-tool) |

## Parallelism and memory

The script reads the cores and memory it may use, including container cgroup limits.
It plans each parallel stage from a per-task memory estimate plus ~0.35 GB of process
overhead, keeping within 75% of the available memory (`MEMORY_FRACTION`):

| Stage | Per task | Notes |
|---|---|---|
| OSM extracts | 1.5 GB + 7 × .pbf size | largest extracts start first |
| Travel time | ~10 bytes × 752 M cells ≈ 7.8 GB | 51 tasks (3 years × 17 layers); friction is memory-mapped and shared |
| Store | ~2 GB (thread) | up to 16 threads |
| WorldCover / DEM reads | threads (I/O bound) | `REMOTE_READ_THREADS` |
| Downloads | `DOWNLOAD_WORKERS` = 4 | polite to Geofabrik |

Measured: one travel-time layer on a 32 M-cell grid takes ~40 s on one core. On the
752 M-cell global grid only land cells are processed (~25–30%), so expect roughly
5–15 min per layer. Rough needs for a global run with three years: ~152 GB for the OSM history
file plus one temporary planet per year while cutting, 16.5 GB of Microsoft roads, 7.4 GB of
Nelson layers, ~200 GB of intermediate grids on disk, ~100 GB for `store/`, and a peak RAM of
(number of parallel travel-time tasks × ~8 GB) + ~15 GB. Run `--dry-run` on your node for
its own figures.

## Method choices to state in a paper

- **Grid:** WGS84, 30″, −180…180° / −60…85° (as Nelson et al. 2019). The light version
  averages 10 × 10 cells (valid cells only).
- **Roads:** OSM `highway` classes → `SPEED_TABLE`. Unpaved (tagged, or untagged minor
  classes) × 0.7. Fastest road wins in a cell. Microsoft ML roads (undated) are used for
  the last year only, at 15 km/h, in cells with no OSM road.
- **Roads completed with Weiss et al. (2018):** OSM in 2015 missed many roads that the
  2015 friction surface of Weiss et al. (OSM + Google roads; Malaria Atlas Project, CC BY 4.0,
  downloaded by WCS) contains. A 30″ cell of reference year Y (2015 ≤ Y < last year) gets a road
  when OSM of year Y has none, the Weiss surface is ≥ 10 km/h there, and OSM of the last year has
  a road there (this excludes the rivers, sea lanes and railways in the Weiss surface, and open
  water): a road mapped in 2015 and still there in the last year existed in Y. Its speed is
  min(Weiss speed, last-year OSM speed). Done before any travel-time calculation; the number of
  cells added is in `methods/friction_<year>.json`.
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
           friction_<year>_1km.tif (min/m), traveltime_change_<later>_minus_<earlier>_1km.tif (int16),
           for 2020-2015, 2026-2020 and 2026-2015
cog_10km/  the same at 300″
png/       one global map per layer and year, friction, and change maps
tables/    population-weighted travel time by country / continent / globe
nelson_comparison/   per-layer statistics, per-continent means, difference maps, scatter plots
routing_validation/  origin–city pairs, summaries by continent / distance band / country, scatter plot, attribution
store/     every grid (per year) as COGs + manifest.json + tables/, for other scripts
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
