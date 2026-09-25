# accessibility_update — updating travel-time maps for new roads (Benin + Togo)

Updates accessibility (travel time to cities and ports) between two dates by
rebuilding the road network, the friction surface and the travel time for each
date, then comparing them. Tested on Benin and Togo, 2020-01-01 vs 2026-09-01,
with per-town results for nine Beninese communes.

```
accessibility_update/
├── scripts/                     all code
│   ├── merge_roads.py           OSM + Microsoft ML roads, new/gone roads between dates
│   ├── friction.py              friction maps (min/m) for two dates
│   ├── traveltime.py            travel time to cities / ports by size class
│   ├── run_roads_benin_togo.py      step 1  ─┐
│   ├── run_friction_benin_togo.py   step 2   │ Benin + Togo drivers,
│   ├── run_traveltime_benin_togo.py step 3   │ run in this order
│   ├── run_towns_benin.py           step 4  ─┘
│   ├── requirements.txt
│   ├── tests/                   offline tests on synthetic data (pytest)
│   └── original/                the first script (v00), kept unchanged
├── config/
│   ├── speed_table.csv          road speed by OSM class (+ unpaved rule)
│   └── landcover_speed.csv      off-road walking speed by WorldCover class
├── results/                     small outputs, committed (CSV, PNG, logs)
│   ├── roads/  friction/  traveltime/  towns/
├── docs/roaddetections_images/  figures from microsoft/RoadDetections
├── REPORT.md                    test results and local installation guide
├── data/                        inputs (downloaded, not committed)
└── output/                      large rasters / GeoPackages (not committed)
```

## Pipeline

| Step | Script | What it does | Results |
|---|---|---|---|
| 1 | `run_roads_benin_togo.py` → `merge_roads.py` | reads OSM 2020 and 2026, flags new and gone roads, adds Microsoft roads not already in OSM, compares with v00, sensitivity of the gap-fill | `results/roads/` |
| 2 | `run_friction_benin_togo.py` → `friction.py` | 100 m friction for 2020, 2026 and 2026 + ML roads | `results/friction/` |
| 3 | `run_traveltime_benin_togo.py` → `traveltime.py` | travel time to cities ≥ 50k / ≥ 5k and to ports, 4 scenarios | `results/traveltime/` |
| 4 | `run_towns_benin.py` | the above summarised per commune for 9 towns, with maps | `results/towns/` |

Run everything from `accessibility_update/`:

```bash
pip install -r scripts/requirements.txt
python -m pytest scripts/tests -q                 # offline, ~15 s
# download the inputs into data/ (see REPORT.md, section 4.2), then:
python scripts/run_roads_benin_togo.py
python scripts/run_friction_benin_togo.py
python scripts/run_traveltime_benin_togo.py
python scripts/run_towns_benin.py
```

`.github/workflows/accessibility.yml` does the same on GitHub Actions (downloads,
steps 1–4, commits `results/`). It runs on pushes that change `scripts/` or `config/`,
or by hand ("Run workflow").

## Inputs (checked 2026-09-25)

| Input | Source | Used in |
|---|---|---|
| OSM snapshots | Geofabrik yearly extracts, e.g. `https://download.geofabrik.de/africa/benin-200101.osm.pbf`; outlines `benin.poly`, `togo.poly` | 1, 2 |
| Microsoft ML roads | drop 2025-04-28, `https://usaminedroads.z19.web.core.windows.net/drops/2025.04.28/Western_Africa.zip` (ODbL) | 1, 2 |
| Land cover | ESA WorldCover 2021 v200, 3° tiles on `esa-worldcover.s3.eu-central-1.amazonaws.com` (read remotely) | 2 |
| Elevation | Copernicus GLO-30, 1° tiles on `copernicus-dem-30m.s3.amazonaws.com` (read remotely) | 2 |
| Settlements, population | GHSL R2023A, GHS-SMOD and GHS-POP, 1 km, epochs 2020 and 2025 (`jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/`) | 3, 4 |
| Ports | World Port Index (NGA Pub. 150), `UpdatedPub150.csv` | 3 |
| Communes | geoBoundaries gbOpen BEN ADM2 (77 communes, public domain) | 4 |

## Methods

### Roads (`merge_roads.py`)

- OSM `highway` lines are read with GDAL's OSM driver; several extracts are merged and
  de-duplicated on `osm_id`. Speeds come from `config/speed_table.csv`; the unpaved factor
  (×0.7) applies when `surface` is unpaved, or when it is missing and the class is marked
  `paved_if_missing = no`.
- A Microsoft road is "already in OSM" if more than 50% of its length lies within 20 m of an
  OSM road (sampled every 10 m); the others are added as `ml_detected` at 15 km/h.
- A 2026 OSM road is "new" if it has no 2020 counterpart by the same rule, and a 2020 road
  is "gone" if it has no 2026 counterpart. Matching is by geometry, not `osm_id`, because
  ways get split and re-drawn.

### Friction (`friction.py`)

Speed per 100 m cell, fastest option wins:

- **road cells:** class speed from `speed_table.csv`;
- **off-road cells:** land-cover walking speed (`landcover_speed.csv`, flat terrain) ×
  Tobler factor `exp(-3.5 × tan(slope))`, slope from Copernicus GLO-30 averaged to 100 m.
  Water (WorldCover 80) is impassable unless a road crosses it.

Friction = 60 / (1000 × speed) min/m, the unit of the Malaria Atlas Project surfaces.
Both dates use WorldCover 2021, so only roads change (WorldCover 2020 v100 and 2021 v200
use different algorithms). `--base-friction existing.tif` instead burns each date's roads
into an existing friction map, keeping its grid and off-road values.

### Travel time (`traveltime.py`)

Least-cost travel time (8 neighbours, `skimage.graph.MCP_Geometric`) to the nearest
destination of a size class, using the classes of Nelson et al. (2019):

| `to` | size | destinations |
|---|---|---|
| city | 1–9 | 5–50 M, 1–5 M, 0.5–1 M, 200–500 k, 100–200 k, 50–100 k, 20–50 k, 10–20 k, 5–10 k inhabitants |
| port | 1–5 | Large, Medium, Small, Very small, Any (World Port Index `Harbor Size`) |

A size means "this class or larger" (city 6 = at least 50,000 inhabitants, the default);
`--exact-class` uses the class alone. Cities are built per date from GHSL: 8-connected
GHS-SMOD urban-cluster / urban-centre cells (codes 21, 22, 23, 30), population summed from
GHS-POP. `--cities` accepts your own layer with a `pop` column. Ports on water are moved
to the nearest passable cell within 5 km.

The Benin + Togo run uses four scenarios, so each change isolates one factor:

| label | roads | settlements | change from the previous one |
|---|---|---|---|
| `2020` | OSM 2020 | GHSL 2020 | – |
| `2026r` | OSM 2026 | GHSL 2020 | new roads |
| `2026` | OSM 2026 | GHSL 2025 | city growth |
| `2026ml` | OSM 2026 + Microsoft | GHSL 2025 | ML gap-fill |

### Towns (`run_towns_benin.py`)

For Parakou, Kandi, Malanville, Cotonou, Porto-Novo, Comè, Sakété, Natitingou and
Djougou, each commune gets: road km (OSM 2020, 2026, new, gone, ML gap-fill) and density,
population 2020 / 2025, share of cells faster in 2026, and for every scenario and layer the
population-weighted mean travel time and the share of people within 30 / 60 / 120 min.
Outputs: `town_summary.csv`, `town_traveltime.csv` (long format), `overview_city6.png`
and one `map_<town>.png` per town (roads, travel time 2026, change due to new roads).

## Caveats

- **"New in OSM" is not "new on the ground".** OSM growth in Benin and Togo largely comes
  from mapping campaigns; a road flagged new may be decades old. Roads re-drawn more than
  20 m away count as gone + new. Dating construction needs imagery.
- **Roads that disappear from OSM make travel slower,** e.g. tracks retagged as paths
  (not in the speed table). These show as positive travel-time changes.
- **Microsoft roads have no usable date**; they are used for the 2026 map only.
- **Borders.** The friction map is masked to Benin + Togo, so Lagos, Tema / Accra and cities
  in Nigeria, Ghana, Burkina Faso and Niger cannot be reached; travel times near borders
  are too long. Build the friction map over a wider area to fix this.
- **Speeds are not calibrated.** `landcover_speed.csv` holds placeholders (1–5 km/h), and
  road speeds are generic. Calibrate both against observed travel times.
- **GHSL 2025** is, to my understanding, a GHSL projection rather than an observation.
- ML roads (15 km/h) are faster than unpaved OSM tracks (10.5 km/h), so where both fall in
  one cell the ML value wins.

## Changes relative to the first script (v00)

| # | v00 | Now | Why |
|---|---|---|---|
| 1 | `MS_ZIP = "Africa-Full.zip"`, one ISO3 | `Western_Africa.zip`, several ISO3, `WidthMeters` kept | current file name; Benin + Togo in one run |
| 2 | `pyrosm` | GDAL OSM driver via `pyogrio` | one dependency fewer; several extracts, de-duplicated |
| 3 | unpaved factor only when tagged | `paved_if_missing` in `speed_table.csv` | most rural roads have no surface tag |
| 4 | per-segment union of OSM buffers | 10 m sampling + STRtree `dwithin` | same rule, ~2.4x faster on Benin + Togo, 0.33% of decisions differ |
| 5 | — | new / gone roads between two OSM dates | the original question |
| 6 | grid from road bounds; crash on zero height | grid snapped to the resolution; `--template` | rasters of two dates align |
| 7 | hard-coded settings | CLI arguments, CSV tables | reproducible updates |
| 8 | no tests | 28 offline tests + CI run on real data | |
