#!/usr/bin/env python3
"""
global_accessibility_v2.py - travel time to cities and ports for two reference years
====================================================================================

Version 2.0: adds a sensitivity analysis of the governance factor K and of the
African border-crossing delay (stage "sensitivity"). Everything else as version 1.

Stand-alone script (one file, Python >= 3.11, tested with 3.13). It installs any
missing Python package itself, downloads every input, builds friction surfaces and
travel-time layers for a start and an end year on the 30 arc-second grid of
Nelson et al. (2019), compares them with Nelson et al. (2019), writes Cloud
Optimized GeoTIFFs (1 km and 10 km), global PNG maps and a folder with everything
needed for the Methods section, then deletes the intermediate files.

Usage (from a terminal or a Jupyter cell with "!"):
    python global_accessibility_v2.py                     # full global run
    python global_accessibility_v2.py --dry-run           # plan: downloads, memory, workers
    python global_accessibility_v2.py --bbox -1 5.5 4.5 13.5 --start 2015 --end 2026
    python global_accessibility_v2.py --stages download   # one stage (others resume later)

Stages (each resumes where it stopped; completed stages are skipped):
    download -> grids -> roads -> friction -> traveltime -> outputs -> compare -> validate
    -> sensitivity -> cleanup

Layers (as Nelson et al. 2019, figshare 10.6084/m9.figshare.7638134):
    cities_1..9   travel time to settlements of one population class only
    cities_10     >= 20,000     cities_11  >= 50,000 (to 50 M)     cities_12  >= 5,000
    ports_1..4    Large, Medium, Small, Very small (World Port Index)     ports_5  any
"""
from __future__ import annotations

__version__ = "2.0.5"

# =============================================================================
# CONFIGURATION - edit here (command-line options override a few of these)
# =============================================================================
START_YEAR = 2015               # first reference year (2015 = year of Nelson et al. 2019)
END_YEAR = 2026                 # second reference year
WORK_DIR = "./ga_work"          # downloads and intermediate files (deleted at the end)
RESULTS_DIR = "./ga_results"    # everything kept
BBOX = None                     # None = Nelson extent (-180, -60, 180, 85); or (W, S, E, N)
RES_ARCSEC = 30                 # 30" ~ 1 km, the grid of Nelson et al. (2019)
LIGHT_FACTOR = 10               # 10 x 30" = 300" ~ 10 km "light" version
CLEANUP = True                  # delete WORK_DIR at the end, only if every stage succeeded (results are kept)
KEEP_DOWNLOADS = False          # keep WORK_DIR/downloads when cleaning up

# --- roads (km/h by OSM highway class; paved_if_missing=False -> unpaved factor
#     applies when the surface tag is absent) -------------------------------------
SPEED_TABLE = {
    #  highway:        (km/h, paved_if_missing)
    "motorway": (100, True), "trunk": (80, True), "primary": (70, True),
    "secondary": (55, True), "tertiary": (40, False), "unclassified": (30, False),
    "residential": (25, False), "motorway_link": (60, True), "trunk_link": (50, True),
    "primary_link": (45, True), "secondary_link": (40, True), "tertiary_link": (30, False),
    "service": (20, False), "track": (15, False), "living_street": (15, False),
}
UNPAVED_SURFACES = {"unpaved", "dirt", "gravel", "ground", "earth", "sand", "compacted",
                    "mud", "fine_gravel", "grass", "laterite"}
UNPAVED_FACTOR = 0.7
INCLUDE_ML_ROADS = True         # Microsoft ML road detections, end year only (undated)
ML_SPEED = 15.0                 # km/h, treated as tracks
ML_DROP = "2025.04.28"
ML_FILES = ["World.zip"]        # e.g. ["Western_Africa.zip"] for a regional run

# --- off-road walking speed (km/h, flat ground) by ESA WorldCover 2021 class ------
LANDCOVER_SPEED = {10: 2.5, 20: 3.0, 30: 4.0, 40: 4.0, 50: 5.0, 60: 3.0, 70: 1.0,
                   80: 0.0,      # permanent water: impassable unless a road crosses
                   90: 1.5, 95: 1.0, 100: 3.0}
TOBLER_K = 3.5                  # walking speed factor exp(-3.5 * tan(slope))
LC_SUBSAMPLE = 5                # land cover read at RES/5 (~185 m): majority class + water share
WATER_ROAD_MAX_PCT = 90         # a road on a cell >= 90% water is dropped unless it is an OSM
                                # bridge / causeway / ford (Microsoft roads: always dropped)
DEM_OVERSAMPLE = 5              # slope computed at RES/5 (~180 m) then averaged

# --- corruption penalty (World Bank WGI "Control of Corruption", score 0-100) ------
#     c = 1 - score/100; road speed x (1 - K * c); border delay / (1 - K * c_mean)
CORRUPTION_K = 0.10
WGI_INDICATOR = "GOV_WGI_CC.SC"

# --- sensitivity analysis of K and of the border delay (stage "sensitivity") -------
SENSITIVITY = True
SENS_K = [0.0, 0.05, 0.10, 0.20]            # governance factor values
SENS_DELAY_MIN = [0.0, 15.0, 30.0, 60.0]    # border-crossing delay values (minutes)
SENS_DESIGN = "oat"             # "oat": vary one parameter at a time around the baseline
                                # (7 scenarios); "full": all combinations (16 scenarios)
SENS_LAYERS = ["cities_11", "ports_5"]      # layers recomputed for each scenario

# --- border crossings: only between two African countries, only at official
#     checkpoints (major roads crossing a land border) -----------------------------
BORDER_DELAY_MIN = 15.0
BORDER_CONTINENTS = {"Africa"}
CHECKPOINT_CLASSES = {"motorway", "trunk", "primary", "secondary",
                      "motorway_link", "trunk_link", "primary_link", "secondary_link"}

# --- destinations -------------------------------------------------------------
CITY_LAYERS = {  # layer: (population >=, population <)   (Nelson et al. 2019)
    1: (5e6, 5e7), 2: (1e6, 5e6), 3: (5e5, 1e6), 4: (2e5, 5e5), 5: (1e5, 2e5),
    6: (5e4, 1e5), 7: (2e4, 5e4), 8: (1e4, 2e4), 9: (5e3, 1e4),
    10: (2e4, 1.1e8), 11: (5e4, 5e7), 12: (5e3, 1.1e8)}
PORT_LAYERS = {1: {"Large"}, 2: {"Medium"}, 3: {"Small"}, 4: {"Very Small"}, 5: None}
HEADLINE_LAYER = "cities_11"    # >= 50,000 inhabitants
URBAN_CODES = (21, 22, 23, 30)  # GHS-SMOD urban clusters and centres
PORT_SNAP_KM = 5.0              # move ports on water to the nearest land cell

# --- comparison with Nelson et al. (2019), latest figshare version ----------------
NELSON_COMPARE = True
NELSON_ARTICLE = 7638134        # figshare article (v3 is cited by R geodata; v4 = same rasters)
NELSON_LAYERS = None            # None = all 17; or e.g. ["cities_11", "ports_5"]

# --- 2015 roads completed with the Weiss et al. (2018) 2015 friction surface ------
#     (OSM + Google roads; Malaria Atlas Project, CC BY 4.0). A cell gets a 2015 road if
#     OSM 2015 has none there, Weiss 2015 shows a transport network (>= WEISS_NETWORK_KMH)
#     and OSM END_YEAR has a road there (this excludes Weiss rivers, sea lanes, railways).
WEISS2015_AUGMENT = True        # used only when START_YEAR == 2015
OSM_MAX_MISSING_REGIONS = 0     # regions allowed to have no extract at all (they get no roads)
OSM_SNAPSHOT_MAX_LAG = 1        # years: a region with no 1 January snapshot of the year (e.g. Russia
                                # before 2016) uses the next available one, at most this much later
WEISS_NETWORK_KMH = 10.0
WEISS_WCS = ("https://data.malariaatlas.org/geoserver/Accessibility/ows?service=WCS&version=2.0.1"
             "&request=GetCoverage&coverageId=Accessibility__201501_Global_Travel_Speed_Friction_Surface"
             "&format=image/geotiff&subset=Lat({s},{n})&subset=Long({w},{e})")
WEISS_TILE_DEG = 10             # download in 10 x 10 degree tiles
COMPLETE_TILE_DEG = 2           # tiles for "where OSM 2015 data exist" (Weiss validation tiles)
COMPLETE_MIN = 0.8              # OSM 2015 road cells / Weiss network cells, before completion
COMPLETE_MIN_CELLS = 50         # tiles with fewer Weiss network cells are not assessed

# --- validation of the end year against a free routing engine (OSRM, OSM car) ---
ROUTING_VALIDATION = True
NETWORK_CHECK = True            # test every download server before starting (--skip-network-check)
ROUTING_SERVERS = ["https://router.project-osrm.org",            # demo server, 1 req/s,
                   "https://routing.openstreetmap.de/routed-car"]  # FOSSGIS, 1 req/s
ROUTING_PROFILE = "driving"
ROUTING_MIN_INTERVAL_S = 1.1    # both servers ask for at most 1 request per second
ROUTING_CITIES = 250            # settlements >= ROUTING_MIN_POP sampled (by continent)
ROUTING_MIN_POP = 5e4
ROUTING_ORIGINS_PER_CITY = 10   # origins per city, population-weighted
ROUTING_RADIUS_KM = (10, 150)   # great-circle distance of origins from the city
ROUTING_MAX_SNAP_M = 1000       # drop pairs where OSRM moved a point further than this

# --- resources (None = detect) --------------------------------------------------
MAX_WORKERS = None              # cap on processes
MEMORY_FRACTION = 0.75          # share of available RAM the script may plan for
DOWNLOAD_WORKERS = 4            # parallel downloads per host (be polite to Geofabrik)
REMOTE_READ_THREADS = 24        # threads reading WorldCover / DEM tiles over HTTP
USER_AGENT = "global-accessibility-script/1.0 (research use)"

# =============================================================================
# End of configuration
# =============================================================================

import argparse
import concurrent.futures as cf
import datetime as dt
import gzip
import hashlib
import importlib
import importlib.metadata
import importlib.util
import io
import json
import math
import multiprocessing as mp
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import zipfile
from pathlib import Path

REQUIRED = {  # import name: (pip name, minimum version)
    "numpy": ("numpy", "1.26"), "pandas": ("pandas", "2.0"),
    "geopandas": ("geopandas", "1.0"), "pyogrio": ("pyogrio", "0.9"),
    "shapely": ("shapely", "2.0"), "rasterio": ("rasterio", "1.4"),
    "pyproj": ("pyproj", "3.6"), "scipy": ("scipy", "1.11"), "numba": ("numba", "0.60"),
    "psutil": ("psutil", "5.9"), "matplotlib": ("matplotlib", "3.8"),
    "requests": ("requests", "2.28"), "pyarrow": ("pyarrow", "14"),
}


def _version_ok(dist, minimum):
    try:
        have = importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return False
    num = lambda v: tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    return num(have) >= num(minimum)


def bootstrap(work_dir):
    """Install missing or outdated packages into WORK_DIR/pylib (no admin rights needed)."""
    lib = Path(work_dir).resolve() / "pylib"
    if lib.exists() and str(lib) not in sys.path:
        sys.path.insert(0, str(lib))
        importlib.invalidate_caches()
    need = [f"{pip}>={v}" for mod, (pip, v) in REQUIRED.items()
            if importlib.util.find_spec(mod) is None or not _version_ok(pip, v)]
    if need:
        print(f"[bootstrap] installing into {lib}: {' '.join(need)}", flush=True)
        lib.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet",
                               "--upgrade", "--target", str(lib), *need])
        if str(lib) not in sys.path:
            sys.path.insert(0, str(lib))
        importlib.invalidate_caches()


def _early_work_dir():
    if os.environ.get("GA_WORK_DIR"):
        return os.environ["GA_WORK_DIR"]
    for i, a in enumerate(sys.argv):
        if a == "--work-dir" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith("--work-dir="):
            return a.split("=", 1)[1]
    return WORK_DIR


_WD = Path(_early_work_dir()).resolve()
(_WD / "tmp").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("NUMBA_CACHE_DIR", str(_WD / "numba_cache"))
os.environ.setdefault("CPL_TMPDIR", str(_WD / "tmp"))          # GDAL temp (not /tmp)
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.TIF")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "6")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "3")
os.environ.setdefault("GDAL_HTTP_USERAGENT", USER_AGENT)
os.environ.setdefault("OSM_COMPRESS_NODES", "YES")
os.environ.setdefault("OSM_MAX_TMPFILE_SIZE", "1024")
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
bootstrap(_WD)

_PROJ_TEST = r"""
import os, tempfile
import numpy, pandas, geopandas as gpd, pyogrio, rasterio, shapely   # same order as the script
from rasterio.crs import CRS
from rasterio.warp import transform
assert CRS.from_epsg(4326).to_epsg() == 4326
transform(CRS.from_epsg(4326), CRS.from_string("ESRI:54009"), [10.0], [10.0])
f = os.path.join(tempfile.mkdtemp(dir=os.environ.get("CPL_TMPDIR")), "t.gpkg")
gpd.GeoDataFrame(geometry=[shapely.Point(0, 0)], crs=4326).to_file(f)
assert gpd.read_file(f).crs.to_epsg() == 4326
"""


def _proj_dirs():
    """Folders holding a proj.db: those shipped with the Python packages (any site-packages,
    including ~/.local), then the environment's own share/proj."""
    dirs = []
    for sp in dict.fromkeys(p for p in sys.path if p and Path(p).is_dir()):
        for pat in ("rasterio/proj_data", "pyogrio/proj_data", "fiona/proj_data", "pyproj/proj_dir/share/proj"):
            dirs.append(Path(sp) / pat)
    for pre in (os.environ.get("CONDA_PREFIX"), sys.prefix, sys.base_prefix):
        if pre:
            dirs.append(Path(pre) / "share" / "proj")
    return [d for d in dict.fromkeys(dirs) if (d / "proj.db").is_file()]


def fix_proj_data():
    """Make sure GDAL/PROJ find a usable proj.db before the geospatial libraries are imported.

    Conda activation scripts, other packages (e.g. a user-installed fiona) or a module
    system can leave PROJ_DATA / PROJ_LIB pointing to a missing or incompatible database
    ("PROJ: proj_create_from_database: Open of /opt/conda/share/proj failed"), which breaks
    or silently degrades coordinate-system lookups. Each candidate setting is tested in a
    subprocess that imports the libraries in the same order as this script: first the
    environment as it is, then without the variables (pip wheels then use their bundled
    data), then each proj.db folder found. A candidate counts only if it works AND PROJ
    prints no error. GA_PROJ_DATA=<folder> forces a folder.
    """
    keys = ("PROJ_DATA", "PROJ_LIB")
    old = {k: os.environ[k] for k in keys if os.environ.get(k)}
    base = {k: v for k, v in os.environ.items() if k not in keys}
    if os.environ.get("GA_PROJ_DATA"):
        cands = [("GA_PROJ_DATA", {k: os.environ["GA_PROJ_DATA"] for k in keys})]
    else:
        cands = [("as set", None), ("unset", {})] + [(str(d), {k: str(d) for k in keys}) for d in _proj_dirs()]
    pypath = os.pathsep.join([p for p in sys.path if p] + [os.environ.get("PYTHONPATH", "")]).strip(os.pathsep)
    tried, usable = [], None                   # tried: (label, returncode, PROJ error or "")
    for label, c in cands:
        env = {**(os.environ.copy() if c is None else {**base, **c}), "PYTHONPATH": pypath}   # sees pylib
        r = subprocess.run([sys.executable, "-c", _PROJ_TEST], env=env, capture_output=True, text=True)
        noise = [ln.strip() for ln in r.stderr.splitlines() if "PROJ" in ln and "ERROR" in ln.upper()]
        last = (noise or r.stderr.strip().splitlines() or [""])[-1][:200]
        tried.append((label, r.returncode, last if (noise or r.returncode) else ""))
        if r.returncode == 0 and (not noise or usable is None):
            usable = (label, c, noise[-1][:200] if noise else "")
            if not noise:
                break                            # works and PROJ is silent
    if usable is None:
        raise SystemExit("No working PROJ database (proj.db) was found, so coordinate systems cannot be read.\n"
                         + "\n".join(f"  {l}: {'works' if rc == 0 else 'fails'} {e}" for l, rc, e in tried)
                         + "\nSet GA_PROJ_DATA to a folder containing proj.db (find / -name proj.db) and rerun.")
    label, c, still = usable
    if c is not None:
        for k in keys:
            os.environ.pop(k, None)
        os.environ.update(c)
    print(f"[bootstrap] PROJ data: {label}" + (f" (environment had {old})" if old else "")
          + (f"; tried first: {[t[0] for t in tried[:-1]]}" if len(tried) > 1 else "")
          + (f"; WARNING, PROJ still reports: {still}" if still else ""), flush=True)


fix_proj_data()

import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402
import geopandas as gpd                               # noqa: E402
import pyogrio                                        # noqa: E402
import psutil                                         # noqa: E402
import rasterio                                       # noqa: E402
import rasterio.shutil                                # noqa: E402
import requests                                       # noqa: E402
import shapely                                        # noqa: E402
from numba import njit                                # noqa: E402
from rasterio.enums import Resampling                 # noqa: E402
from rasterio.features import rasterize               # noqa: E402
from rasterio.transform import from_origin            # noqa: E402
from rasterio.warp import reproject, transform_bounds  # noqa: E402
from rasterio.windows import Window, from_bounds      # noqa: E402
from scipy import ndimage                             # noqa: E402
from shapely.geometry import box, shape               # noqa: E402

import matplotlib                                     # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402

R_EARTH = 6371007.2
NELSON_EXTENT = (-180.0, -60.0, 180.0, 85.0)
TT_NODATA = 65535
CHANGE_NODATA = -32768
LOG = []

URLS = {
    "geofabrik_index": "https://download.geofabrik.de/index-v1.json",
    "ml": "https://usaminedroads.z19.web.core.windows.net/drops/{drop}/{file}",
    "worldcover_list": "https://esa-worldcover.s3.eu-central-1.amazonaws.com/",
    "worldcover": "https://esa-worldcover.s3.eu-central-1.amazonaws.com/{key}",
    "copdem_list": "https://copernicus-dem-90m.s3.amazonaws.com/tileList.txt",
    "copdem": "https://copernicus-dem-90m.s3.amazonaws.com/{t}/{t}.tif",
    "ghsl_smod": ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_SMOD_GLOBE_R2023A/"
                  "GHS_SMOD_E{y}_GLOBE_R2023A_54009_1000/V2-0/"
                  "GHS_SMOD_E{y}_GLOBE_R2023A_54009_1000_V2_0.zip"),
    "ghsl_pop": ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/"
                 "GHS_POP_E{y}_GLOBE_R2023A_54009_1000/V1-0/"
                 "GHS_POP_E{y}_GLOBE_R2023A_54009_1000_V1_0.zip"),
    "wpi": ("https://msi.nga.mil/api/publications/download?type=view&"
            "key=16920959/SFH00000/UpdatedPub150.csv"),
    "naturalearth": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip",
    "wgi": "https://api.worldbank.org/v2/country/all/indicator/{ind}",
    "nelson": "https://api.figshare.com/v2/articles/{a}",
}
GHSL_EPOCHS = list(range(1975, 2031, 5))


# =============================================================================
# small utilities
# =============================================================================
def log(*a):
    msg = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] " + " ".join(str(x) for x in a)
    print(msg, flush=True)
    LOG.append(msg)


class Timer:
    rows = []

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.t = time.time()
        log(f"--- {self.name} ...")
        return self

    def __exit__(self, *exc):
        s = time.time() - self.t
        Timer.rows.append({"step": self.name, "seconds": round(s, 1),
                           "rss_gb": round(psutil.Process().memory_info().rss / 1e9, 2)})
        log(f"--- {self.name}: {s / 60:.1f} min")


def cpu_count():
    try:
        n = len(os.sched_getaffinity(0))
    except AttributeError:
        n = os.cpu_count() or 1
    try:  # cgroup v2 quota
        q, p = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if q != "max":
            n = min(n, max(1, int(int(q) / int(p))))
    except Exception:
        pass
    return n


def available_memory():
    avail = psutil.virtual_memory().available
    for f, used in (("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),
                    ("/sys/fs/cgroup/memory/memory.limit_in_bytes",
                     "/sys/fs/cgroup/memory/memory.usage_in_bytes")):
        try:
            lim = Path(f).read_text().strip()
            if lim not in ("max", "") and int(lim) < 1 << 60:
                avail = min(avail, int(lim) - int(Path(used).read_text()))
        except Exception:
            pass
    return max(avail, 1 << 30)


def session():
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


MANIFEST = []


def download(url, dest, sess=None, retries=5, record=True):
    """Resumable download; returns dest.

    A file is written as <name>.part and renamed only when complete, with its size, date and
    source recorded in <name>.meta.json. A file already on disk is kept and never downloaded
    again while its size matches that record (files from runs before this record existed are
    trusted as complete, since they were renamed only when complete). A file whose size no
    longer matches is downloaded again, replacing it only once the new copy is complete.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta = dest.with_name(dest.name + ".meta.json")
    if dest.exists() and dest.stat().st_size > 0:
        size = dest.stat().st_size
        m = json.loads(meta.read_text()) if meta.exists() else None
        if m is None or m.get("bytes") == size:
            if m is None:
                meta.write_text(json.dumps({"url": url, "bytes": size, "downloaded": "earlier run"}))
            if record:
                MANIFEST.append({"url": url, "file": dest.name, "bytes": size,
                                 "downloaded": (m or {}).get("downloaded", "earlier run"),
                                 "last_modified": (m or {}).get("last_modified", "")})
            return dest
        log(f"{dest.name}: {size:,} bytes on disk but {m['bytes']:,} when downloaded; downloading it again")
    sess = sess or session()
    tmp = dest.with_name(dest.name + ".part")
    last = None
    for attempt in range(retries):
        try:
            headers = {}
            if tmp.exists():
                headers["Range"] = f"bytes={tmp.stat().st_size}-"
            with sess.get(url, stream=True, timeout=300, headers=headers,
                          allow_redirects=True) as r:
                if r.status_code == 416:
                    break
                r.raise_for_status()
                mode = "ab" if r.status_code == 206 else "wb"
                with open(tmp, mode) as fh:
                    for chunk in r.iter_content(1 << 22):
                        fh.write(chunk)
                lastmod, etag = r.headers.get("Last-Modified", ""), r.headers.get("ETag", "")
            tmp.replace(dest)
            info = {"url": url, "bytes": dest.stat().st_size, "last_modified": lastmod, "etag": etag,
                    "downloaded": dt.datetime.now().isoformat(timespec="seconds")}
            meta.write_text(json.dumps(info))
            if record:
                MANIFEST.append({k: info[k] for k in ("url", "bytes", "downloaded", "last_modified")}
                                | {"file": dest.name})
            return dest
        except Exception as e:
            last = e
            if attempt < retries - 1:
                wait = 5 * 2 ** attempt
                log(f"download retry {attempt + 1}/{retries} {url}: {e!r}; waiting {wait}s")
                time.sleep(wait)
    raise RemoteUnavailable(f"download failed after {retries} attempts: {url}: {last!r}")


class RemoteUnavailable(RuntimeError):
    """A server kept failing (network error, 429 or 5xx): stop instead of guessing."""


def http_request(url, sess, method="HEAD", tries=6, **kw):
    """Response of a HEAD/GET, retrying network errors, 429 and 5xx with backoff (5 s to
    2 min). Any other status (200, 404, ...) is returned as is. Raises RemoteUnavailable."""
    delay, last = 5, None
    for i in range(tries):
        try:
            r = sess.request(method, url, timeout=60, allow_redirects=True, **kw)
            if r.status_code != 429 and r.status_code < 500:
                return r
            last = f"HTTP {r.status_code}"
            wait = r.headers.get("Retry-After", "")
            delay = max(delay, int(wait)) if wait.isdigit() else delay
        except requests.RequestException as e:
            last = repr(e)
        if i < tries - 1:
            time.sleep(delay); delay = min(delay * 2, 120)
    raise RemoteUnavailable(f"{url}: {last} after {tries} attempts")


def head_ok(url, sess):
    """(exists, bytes). A 404/410 means absent; other failures raise RemoteUnavailable."""
    r = http_request(url, sess, "HEAD")
    if r.status_code in (404, 410):
        return False, 0
    if not r.ok:
        raise RemoteUnavailable(f"{url}: HTTP {r.status_code}")
    return True, int(r.headers.get("Content-Length", 0) or 0)


_UNITS = {"": 1, "K": 2**10, "M": 2**20, "G": 2**30, "T": 2**40}


def geofabrik_listing(dir_url, cache_dir, sess, max_age_days=7):
    """{file name: approximate bytes} of the .osm.pbf files in a Geofabrik folder, from its raw
    directory index (one request per folder instead of one per file; cached on disk).
    None if the page is not a raw index (e.g. the site root)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    f = cache_dir / (re.sub(r"[^A-Za-z0-9]+", "_", dir_url).strip("_") + ".json")
    if f.exists() and time.time() - f.stat().st_mtime < max_age_days * 86400:
        return json.loads(f.read_text())["files"]
    r = http_request(dir_url.rstrip("/") + "/", sess, "GET")
    files = None
    if r.ok:
        found = {}
        for line in r.text.splitlines():
            for m in re.finditer(r'href="([^"?#]*?([^"/?#]+\.osm\.pbf))"', line):
                tail = re.sub(r"<[^>]+>", " ", line[m.end():])
                sm = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s+([\d.]+)\s*([KMGT]?)\b", tail)
                found[m.group(2)] = int(float(sm.group(1)) * _UNITS[sm.group(2)]) if sm else 0
        files = found if any(re.search(r"-\d{6}\.osm\.pbf$", n) for n in found) else None   # dated files: a raw index
        f.write_text(json.dumps({"url": dir_url, "files": files}))   # cache successful reads only
    elif r.status_code not in (403, 404):
        raise RemoteUnavailable(f"{dir_url}: HTTP {r.status_code}")
    return files


def sha256(path, limit=200 * 2**20):
    """sha256 of files up to `limit` bytes (larger files: size only)."""
    p = Path(path)
    if p.stat().st_size > limit:
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# =============================================================================
# grid
# =============================================================================
class Grid:
    """Regular lon/lat grid anchored on the (-180, 90) lattice."""

    def __init__(self, bbox, res_deg):
        w, s, e, n = bbox
        eps = 1e-6          # bounds that are already on the lattice must not move a cell
        fl = lambda x: math.floor(x + eps)
        ce = lambda x: math.ceil(x - eps)
        snap = lambda v, f: f((v + 180.0) / res_deg) * res_deg - 180.0
        snapy = lambda v, f: 90.0 - f((90.0 - v) / res_deg) * res_deg
        math_floor, math_ceil = fl, ce
        self.west, self.east = snap(w, math_floor), snap(e, math_ceil)
        self.north, self.south = snapy(n, math_floor), snapy(s, math_ceil)
        self.res = res_deg
        self.width = int(round((self.east - self.west) / res_deg))
        self.height = int(round((self.north - self.south) / res_deg))
        self.transform = from_origin(self.west, self.north, res_deg, res_deg)
        self.wrap = (self.east - self.west) >= 360.0 - 1e-9

    def subgrid(self, r0, c0, nr, nc):
        """Exact window of this grid (no re-snapping)."""
        g = object.__new__(Grid)
        g.res = self.res
        g.west, g.north = self.west + c0 * self.res, self.north - r0 * self.res
        g.east, g.south = g.west + nc * self.res, g.north - nr * self.res
        g.width, g.height = nc, nr
        g.transform = from_origin(g.west, g.north, self.res, self.res)
        g.wrap = False
        return g

    @property
    def shape(self):
        return (self.height, self.width)

    @property
    def bounds(self):
        return (self.west, self.south, self.east, self.north)

    @property
    def size(self):
        return self.height * self.width

    def lat_centres(self):
        return self.north - (np.arange(self.height) + 0.5) * self.res

    def cell_area_m2(self):
        """Area of one cell in each row (m2), spherical."""
        lat_top = np.radians(self.north - np.arange(self.height) * self.res)
        lat_bot = np.radians(self.north - (np.arange(self.height) + 1) * self.res)
        return R_EARTH ** 2 * math.radians(self.res) * (np.sin(lat_top) - np.sin(lat_bot))

    def window_of(self, bounds):
        """(row0, col0, rows, cols) of lon/lat bounds intersected with the grid, or None."""
        w, s, e, n = bounds
        w, e = max(w, self.west), min(e, self.east)
        s, n = max(s, self.south), min(n, self.north)
        if w >= e or s >= n:
            return None
        c0 = int(math.floor((w - self.west) / self.res + 1e-9))
        c1 = int(math.ceil((e - self.west) / self.res - 1e-9))
        r0 = int(math.floor((self.north - n) / self.res + 1e-9))
        r1 = int(math.ceil((self.north - s) / self.res - 1e-9))
        return r0, c0, r1 - r0, c1 - c0

    def sub_transform(self, r0, c0):
        return from_origin(self.west + c0 * self.res, self.north - r0 * self.res,
                           self.res, self.res)

    def to_dict(self):
        return {"bbox": [self.west, self.south, self.east, self.north], "res_deg": self.res,
                "width": self.width, "height": self.height, "wrap": self.wrap}


def memmap(path, grid, dtype, fill=None, mode="w+"):
    path = Path(path)
    if mode == "r":
        return np.load(path, mmap_mode="r")
    a = np.lib.format.open_memmap(path, mode="w+", dtype=dtype, shape=grid.shape)
    if fill is not None:
        a[:] = fill
    return a


def row_chunks(n, size=2000):
    for r in range(0, n, size):
        yield r, min(n, r + size)


# =============================================================================
# budgeted process pool (accounts for per-task memory and process overhead)
# =============================================================================
PROCESS_OVERHEAD = 0.35e9   # interpreter + numpy/GDAL/numba imports per worker (bytes)


def plan_workers(mem_per_task, n_tasks, cap=None):
    budget = available_memory() * MEMORY_FRACTION
    cores = max(1, cpu_count() - 1)
    by_mem = int(budget // (mem_per_task + PROCESS_OVERHEAD))
    n = max(1, min(n_tasks, cores, by_mem, cap or MAX_WORKERS or 10**9))
    return n, budget


def run_budgeted(fn, jobs, mem_of, label, cap=None):
    """Run fn(job) in processes, never planning more memory than the budget.

    jobs are sorted by memory (largest first) so that big tasks do not wait until
    the end; a job is only started when its estimated memory fits in what is left."""
    if not jobs:
        return []
    mems = [mem_of(j) for j in jobs]
    n, budget = plan_workers(max(mems), len(jobs), cap)
    order = sorted(range(len(jobs)), key=lambda i: -mems[i])
    log(f"{label}: {len(jobs)} tasks, up to {n} workers, memory budget {budget / 1e9:.0f} GB, "
        f"largest task ~{max(mems) / 1e9:.1f} GB")
    results = [None] * len(jobs)
    if n == 1:
        for i in order:
            results[i] = fn(jobs[i])
        return results
    ctx = mp.get_context("fork")
    running, used, pending = {}, 0.0, list(order)
    with cf.ProcessPoolExecutor(n, mp_context=ctx) as ex:
        while pending or running:
            while pending and len(running) < n:
                i = pending[0]
                need = mems[i] + PROCESS_OVERHEAD
                if running and used + need > budget:
                    break
                pending.pop(0)
                running[ex.submit(fn, jobs[i])] = (i, need)
                used += need
            done, _ = cf.wait(running, return_when=cf.FIRST_COMPLETED)
            for f in done:
                i, need = running.pop(f)
                used -= need
                results[i] = f.result()
    return results


# =============================================================================
# numba: multi-source least-cost travel time on a lon/lat grid
# =============================================================================
def step_lengths(grid):
    lat = grid.lat_centres()
    dy = R_EARTH * math.radians(grid.res)
    ew = R_EARTH * np.cos(np.radians(lat)) * math.radians(grid.res)
    up = np.empty_like(ew); dn = np.empty_like(ew)
    up[1:] = 0.5 * (ew[1:] + ew[:-1]); up[0] = ew[0]
    dn[:-1] = 0.5 * (ew[:-1] + ew[1:]); dn[-1] = ew[-1]
    return ew, dy, np.hypot(up, dy), np.hypot(dn, dy)


@njit(cache=True)
def _sift_up(heap, pos, dist, k):
    item = heap[k]
    d = dist[item]
    while k > 0:
        parent = (k - 1) >> 1
        p = heap[parent]
        if dist[p] <= d:
            break
        heap[k] = p
        pos[p] = k
        k = parent
    heap[k] = item
    pos[item] = k


@njit(cache=True)
def _sift_down(heap, pos, dist, k, size):
    item = heap[k]
    d = dist[item]
    while True:
        c = 2 * k + 1
        if c >= size:
            break
        if c + 1 < size and dist[heap[c + 1]] < dist[heap[c]]:
            c += 1
        ch = heap[c]
        if dist[ch] >= d:
            break
        heap[k] = ch
        pos[ch] = k
        k = c
    heap[k] = item
    pos[item] = k


@njit(cache=True)
def _dijkstra(ff, H, W, sources, ew, dy, dg_up, dg_dn, wrap, dist):
    """ff: flat friction (min/m, inf = impassable); dist: flat output (minutes)."""
    N = H * W
    pos = np.full(N, -1, dtype=np.int32)          # -1 never queued, -2 settled
    cap = 1 << 22
    heap = np.empty(cap, dtype=np.int32)
    size = 0
    for s in sources:
        if not np.isfinite(ff[s]) or dist[s] == 0.0:
            continue
        dist[s] = 0.0
        if size == cap:
            cap *= 2
            nh = np.empty(cap, dtype=np.int32); nh[:size] = heap[:size]; heap = nh
        heap[size] = s
        pos[s] = size
        size += 1
        _sift_up(heap, pos, dist, size - 1)
    while size > 0:
        u = heap[0]
        size -= 1
        if size > 0:
            heap[0] = heap[size]
            pos[heap[0]] = 0
            _sift_down(heap, pos, dist, 0, size)
        pos[u] = -2
        du = dist[u]
        r = u // W
        c = u - r * W
        fu = ff[u]
        for k in range(8):
            if k == 0:
                rr = r; cc = c + 1; L = ew[r]
            elif k == 1:
                rr = r; cc = c - 1; L = ew[r]
            elif k == 2:
                rr = r - 1; cc = c; L = dy
            elif k == 3:
                rr = r + 1; cc = c; L = dy
            elif k == 4:
                rr = r - 1; cc = c + 1; L = dg_up[r]
            elif k == 5:
                rr = r - 1; cc = c - 1; L = dg_up[r]
            elif k == 6:
                rr = r + 1; cc = c + 1; L = dg_dn[r]
            else:
                rr = r + 1; cc = c - 1; L = dg_dn[r]
            if rr < 0 or rr >= H:
                continue
            if cc < 0 or cc >= W:
                if not wrap:
                    continue
                cc = cc % W
            v = rr * W + cc
            if pos[v] == -2:
                continue
            fv = ff[v]
            if not np.isfinite(fv):
                continue
            nd = du + 0.5 * (fu + fv) * L
            if nd < dist[v]:
                dist[v] = nd
                if pos[v] == -1:
                    if size == cap:
                        cap *= 2
                        nh = np.empty(cap, dtype=np.int32); nh[:size] = heap[:size]; heap = nh
                    heap[size] = v
                    pos[v] = size
                    size += 1
                _sift_up(heap, pos, dist, pos[v])


def travel_time(friction, sources_flat, grid, out=None):
    """Minutes to the nearest source for every cell (inf = unreachable)."""
    if grid.size >= 2**31 - 1:
        raise ValueError("grid too large for 32-bit indices")
    ff = np.ascontiguousarray(friction).reshape(-1)
    dist = np.asarray(out).reshape(-1) if out is not None else np.empty(grid.size, np.float32)
    dist[:] = np.inf
    ew, dy, up, dn = step_lengths(grid)
    _dijkstra(ff, grid.height, grid.width, np.asarray(sources_flat, np.int64),
              ew, dy, up, dn, grid.wrap, dist)
    return dist.reshape(grid.shape)


def warm_up_numba():
    g = Grid((0, 0, 0.1, 0.1), 0.01)
    f = np.full(g.shape, 0.01, np.float32)
    f.setflags(write=False)              # workers read the friction read-only (memory-mapped)
    travel_time(f, [0], g)


# =============================================================================
# stage: download
# =============================================================================
def network_targets(ctx):
    """(url, what it is for, required) for every server the run needs."""
    t = [("https://download.geofabrik.de/", "OSM road extracts (Geofabrik)", True),
         ("https://jeodpp.jrc.ec.europa.eu/", "GHSL settlements and population (JRC)", True),
         (URLS["worldcover_list"], "ESA WorldCover, read remotely in stage grids", True),
         (URLS["copdem_list"], "Copernicus DEM, read remotely in stage grids", True),
         ("https://naciscdn.org/", "Natural Earth countries", True),
         ("https://api.worldbank.org/", "World Bank WGI (corruption)", True),
         ("https://msi.nga.mil/", "World Port Index (NGA)", True)]
    if INCLUDE_ML_ROADS and ML_FILES:
        t.append(("https://usaminedroads.z19.web.core.windows.net/", "Microsoft road detections", True))
    if NELSON_COMPARE:
        t += [("https://api.figshare.com/", "Nelson et al. 2019 (figshare metadata)", True),
              ("https://ndownloader.figshare.com/", "Nelson et al. 2019 (figshare files)", True)]
    if WEISS2015_AUGMENT and ctx["years"][0] == 2015:
        t.append(("https://data.malariaatlas.org/", "Weiss et al. 2015 roads (Malaria Atlas)", True))
    if ROUTING_VALIDATION:
        t += [(u.rstrip("/") + "/", "routing validation (optional)", False) for u in ROUTING_SERVERS]
    return t


def _probe(url, sess):
    """'' if the server answers at all (any HTTP status), else the error."""
    try:
        sess.head(url, timeout=20, allow_redirects=False)
        return ""
    except requests.RequestException as e:
        err = str(e)
        m = re.search(r"\[Errno -?\d+\][^'\")]*|Name or service not known|timed out|SSLError[^'\")]*", err)
        return (m.group(0) if m else type(e).__name__)[:120]


def network_check(ctx, sess):
    """Test every server before starting, so that a node without (full) internet access fails
    in seconds with a clear list instead of after minutes of retries. Falls back to IPv4
    when only IPv6 fails. Optional servers (routing validation) are dropped if unreachable."""
    global ROUTING_SERVERS, ROUTING_VALIDATION
    targets = network_targets(ctx)
    with cf.ThreadPoolExecutor(8) as ex:
        errs = list(ex.map(lambda t: _probe(t[0], sess), targets))
    if any(errs):
        import socket
        import urllib3.util.connection as uc
        orig = uc.allowed_gai_family
        uc.allowed_gai_family = lambda: socket.AF_INET
        retry = [_probe(t[0], sess) if e else "" for t, e in zip(targets, errs)]
        if sum(map(bool, retry)) < sum(map(bool, errs)):
            log("network: some servers fail over IPv6 but answer over IPv4; using IPv4 only")
            errs = retry
        else:
            uc.allowed_gai_family = orig
    rows = [{"url": u, "purpose": w, "required": r, "reachable": not e, "error": e}
            for (u, w, r), e in zip(targets, errs)]
    pd.DataFrame(rows).to_csv(ctx["work"] / "network_check.csv", index=False)
    bad = [x for x in rows if not x["reachable"]]
    for x in bad:
        log(f"network: cannot reach {x['url']} ({x['purpose']}): {x['error']}")
    if not bad:
        log(f"network: all {len(rows)} servers reachable")
    opt_bad = {x["url"] for x in bad if not x["required"]}
    if opt_bad:
        ROUTING_SERVERS = [u for u in ROUTING_SERVERS if u.rstrip("/") + "/" not in opt_bad]
        if not ROUTING_SERVERS:
            ROUTING_VALIDATION = False
            log("network: no routing server reachable; the routing validation is skipped")
    req_bad = [x for x in bad if x["required"]]
    if req_bad:
        raise SystemExit(
            "This machine cannot reach " + str(len(req_bad)) + " server(s) the run needs:\n"
            + "\n".join(f"  {x['url']:<52} {x['purpose']}: {x['error']}" for x in req_bad)
            + "\nThe cluster probably allows only some sites (other sites such as PyPI worked). Either ask "
            "your IT team to allow HTTPS (port 443) to these hosts from this node, or run "
            "`--stages download,grids` on a machine with internet access using the same --work-dir "
            "(e.g. a shared disk), then rerun here: finished stages are skipped. Nothing was deleted. "
            "(--skip-network-check skips this test.)")


def geofabrik_plan(work, grid, years, sess):
    try:
        return _geofabrik_plan(work, grid, years, sess)
    except RemoteUnavailable as e:
        raise SystemExit(f"Geofabrik is not reachable or refuses the requests ({e}). Nothing was "
                         "planned. Check `curl -I https://download.geofabrik.de/africa/` from this "
                         "node, wait (an hour if the server throttles), and rerun.") from None


def _geofabrik_plan(work, grid, years, sess):
    """Per year, the Geofabrik extracts covering the grid: the smallest regions with a
    1 January snapshot of that year (falling back to parent regions when a region did
    not exist yet), and '-latest' for the current year if the snapshot is missing."""
    idx_path = download(URLS["geofabrik_index"], work / "downloads" / "geofabrik-index-v1.json", sess)
    feats = json.loads(Path(idx_path).read_text())["features"]
    props = {f["properties"]["id"]: f["properties"] for f in feats}
    geoms = {f["properties"]["id"]: (shape(f["geometry"]) if f.get("geometry") else None)
             for f in feats}
    parents = {i: p.get("parent") for i, p in props.items()}
    children = {p for p in parents.values() if p}
    area = box(*grid.bounds)
    leaves = [i for i in props if i not in children and geoms[i] is not None
              and geoms[i].intersects(area)]
    today = dt.date.today()
    plan = {}
    listings, listing_lock = {}, threading.Lock()
    for y in years:
        chosen = {}

        def url_for(rid, yy):
            latest = props[rid]["urls"]["pbf"]
            return latest.replace("-latest.osm.pbf", f"-{yy % 100:02d}0101.osm.pbf"), latest

        cache = {}

        def exists(url):
            """(exists, bytes) from the folder listing, or a HEAD where there is none."""
            d, name = url.rsplit("/", 1)
            with listing_lock:
                if d not in listings:
                    listings[d] = geofabrik_listing(d, work / "downloads" / "geofabrik_listing", sess)
            lst = listings[d]
            region = re.sub(r"-(latest|\d{6})\.osm\.pbf$", "", name)
            if lst is not None and any(re.fullmatch(re.escape(region) + r"-\d{6}\.osm\.pbf", n) for n in lst):
                return name in lst, lst.get(name, 0)     # the listing shows this region's snapshots
            return head_ok(url, sess)

        def available(rid, yy):
            if (rid, yy) not in cache:
                u, latest = url_for(rid, yy)
                ok, size = exists(u)
                if not ok and yy >= today.year:
                    ok, size = exists(latest)
                    u = latest if ok else u
                cache[(rid, yy)] = (ok, u, size)
            return cache[(rid, yy)]

        def job(leaf, yy):
            rid = leaf
            while rid:
                ok, u, size = available(rid, yy)
                if ok:
                    return rid, u, size, yy
                rid = parents.get(rid)
            return None

        with cf.ThreadPoolExecutor(DOWNLOAD_WORKERS * 2) as ex:
            found = list(ex.map(lambda lf: job(lf, y), leaves))
        lagged = {}
        for lag in range(1, OSM_SNAPSHOT_MAX_LAG + 1):   # next snapshot for regions without one
            todo = [i for i, f in enumerate(found) if f is None]
            if not todo or y + lag > today.year:
                break
            with cf.ThreadPoolExecutor(DOWNLOAD_WORKERS * 2) as ex:
                for i, f in zip(todo, ex.map(lambda lf: job(lf, y + lag), [leaves[i] for i in todo])):
                    if f:
                        found[i] = f; lagged[leaves[i]] = f"{f[0]}-{(y + lag) % 100:02d}0101"
        missing = [lf for lf, f in zip(leaves, found) if f is None]
        for f in found:
            if f:
                chosen[f[0]] = f
        # drop regions whose ancestor is also chosen (the ancestor contains them)
        def has_chosen_ancestor(rid):
            p = parents.get(rid)
            while p:
                if p in chosen:
                    return True
                p = parents.get(p)
            return False
        chosen = {k: v for k, v in chosen.items() if not has_chosen_ancestor(k)}
        if not chosen or len(missing) > OSM_MAX_MISSING_REGIONS:
            raise SystemExit(f"OSM {y}: no Geofabrik extract found for {len(missing)} of {len(leaves)} regions "
                             f"{missing[:20]}; these would have no roads. Geofabrik has continent snapshots "
                             "since 2014, so this usually means the server was not reachable or refused "
                             "requests: check `curl -I https://download.geofabrik.de/africa/` from this node, "
                             "delete WORK_DIR/downloads/geofabrik_listing, wait, and rerun. To accept the gaps, "
                             "raise OSM_MAX_MISSING_REGIONS in the configuration.")
        for k, v in chosen.items():            # sizes from the listing (2 digits); HEAD where it has none
            if not v[2]:
                chosen[k] = (v[0], v[1], head_ok(v[1], sess)[1], v[3])
        plan[y] = [{"region": k, "url": v[1], "bytes": v[2], "snapshot_year": v[3],
                    "bounds": list(geoms[k].bounds) if geoms[k] else None}
                   for k, v in sorted(chosen.items())]
        log(f"OSM {y}: {len(plan[y])} extracts, {sum(r['bytes'] for r in plan[y]) / 1e9:.1f} GB"
            + (f"; {len(lagged)} regions from a later snapshot: {sorted(set(lagged.values()))}" if lagged else "")
            + (f"; no snapshot for {len(missing)} regions (no roads there): {missing}" if missing else ""))
    return plan


def stage_download(ctx):
    work, sess = ctx["work"], session()
    dl = work / "downloads"
    years = ctx["years"]
    if NETWORK_CHECK:
        network_check(ctx, sess)
    plan = geofabrik_plan(work, ctx["grid"], years, sess)
    (work / "osm_plan.json").write_text(json.dumps(plan, indent=1))

    jobs = []
    for y in years:
        for r in plan[y]:
            jobs.append((r["url"], dl / "osm" / str(y) / Path(r["url"]).name))
    if INCLUDE_ML_ROADS:
        for f in ML_FILES:
            jobs.append((URLS["ml"].format(drop=ML_DROP, file=f), dl / "ml" / f))
    for y in sorted({ctx["epoch"][y] for y in years}):
        jobs.append((URLS["ghsl_smod"].format(y=y), dl / "ghsl" / f"smod_{y}.zip"))
        jobs.append((URLS["ghsl_pop"].format(y=y), dl / "ghsl" / f"pop_{y}.zip"))
    jobs.append((URLS["wpi"], dl / "UpdatedPub150.csv"))
    jobs.append((URLS["naturalearth"], dl / "ne_10m_admin_0_countries.zip"))
    jobs.append((URLS["copdem_list"], dl / "copdem90_tileList.txt"))
    nelson_md5 = {}
    if NELSON_COMPARE:
        base = URLS["nelson"].format(a=NELSON_ARTICLE)
        latest = max(v["version"] for v in sess.get(base + "/versions", timeout=120).json())
        art = sess.get(f"{base}/versions/{latest}", timeout=120).json()
        (dl / "nelson").mkdir(parents=True, exist_ok=True)
        (dl / "nelson" / "article.json").write_text(json.dumps(art, indent=1))
        log(f"Nelson et al. 2019: figshare version {latest}, doi {art.get('doi')}")
        wanted = set(ctx["nelson_layers"])
        for f in art["files"]:
            m = re.match(r"travel_time_to_(cities|ports)_(\d+)\.tif$", f["name"])
            if (m and f"{m[1]}_{m[2]}" in wanted) or f["name"] == "README.txt":
                jobs.append((f["download_url"], dl / "nelson" / f["name"]))
                nelson_md5[f["name"]] = f.get("computed_md5")
    if WEISS2015_AUGMENT and 2015 in years:
        g, t = ctx["grid"], WEISS_TILE_DEG
        for lat in range(int(math.floor(max(g.south, -60) / t) * t), int(math.ceil(min(g.north, 85))), t):
            for lon in range(int(math.floor(g.west / t) * t), int(math.ceil(g.east)), t):
                s_, n_ = max(lat, -60), min(lat + t, 85)
                if s_ >= n_:
                    continue
                jobs.append((WEISS_WCS.format(s=s_, n=n_, w=lon, e=lon + t),
                             dl / "weiss2015" / f"friction2015_{lat:+03d}_{lon:+04d}.tif"))
    total = sum(r["bytes"] for y in years for r in plan[y])
    log(f"downloads: {len(jobs)} files (OSM {total / 1e9:.1f} GB + others)")
    with cf.ThreadPoolExecutor(DOWNLOAD_WORKERS) as ex:
        list(ex.map(lambda j: download(j[0], j[1], session()), jobs))
    for name, md5 in nelson_md5.items():
        h = hashlib.md5()
        with open(dl / "nelson" / name, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                h.update(chunk)
        if md5 and h.hexdigest() != md5:
            (dl / "nelson" / name).unlink()
            raise RuntimeError(f"MD5 mismatch for Nelson file {name}; deleted, rerun to fetch again")

    # World Bank WGI, all years
    wgi = []
    page, pages = 1, 1
    while page <= pages:
        r = sess.get(URLS["wgi"].format(ind=WGI_INDICATOR),
                     params={"source": 3, "format": "json", "per_page": 20000, "page": page},
                     timeout=300).json()
        pages = r[0]["pages"]
        wgi += [{"iso3": x["countryiso3code"], "year": int(x["date"]), "score": x["value"]}
                for x in r[1] if x["value"] is not None and x["countryiso3code"]]
        page += 1
    pd.DataFrame(wgi).to_csv(dl / "wgi_control_of_corruption.csv", index=False)
    MANIFEST.append({"url": URLS["wgi"].format(ind=WGI_INDICATOR) + "?source=3",
                     "file": "wgi_control_of_corruption.csv", "bytes": len(wgi),
                     "downloaded": dt.datetime.now().isoformat(timespec="seconds")})

    # WorldCover 2021 tile list (S3 listing)
    keys, marker = [], ""
    while True:
        r = sess.get(URLS["worldcover_list"], params={"prefix": "v200/2021/map/",
                                                      "marker": marker, "max-keys": 1000},
                     timeout=120)
        ks = re.findall(r"<Key>([^<]+)</Key>", r.text)
        keys += [k for k in ks if k.endswith("_Map.tif")]
        if "<IsTruncated>true</IsTruncated>" not in r.text or not ks:
            break
        marker = ks[-1]
    (dl / "worldcover_2021_tiles.txt").write_text("\n".join(keys))
    log(f"WorldCover 2021: {len(keys)} tiles listed")


# =============================================================================
# stage: grids (year-independent layers + settlements per GHSL epoch)
# =============================================================================
def countries_frame(dl):
    ne = gpd.read_file(f"zip://{dl / 'ne_10m_admin_0_countries.zip'}")
    iso = ne["ISO_A3_EH"].where(~ne["ISO_A3_EH"].isin(["-99", None]), ne["ADM0_A3"])
    ne = ne.assign(iso3=iso.replace({"SDS": "SSD", "KOS": "XKX", "SOL": "SOM", "SAH": "ESH"}))
    ne = ne[ne["CONTINENT"] != "Antarctica"].reset_index(drop=True)
    ne["cid"] = np.arange(1, len(ne) + 1, dtype=np.int16)
    return ne[["cid", "iso3", "ADM0_A3", "NAME", "CONTINENT", "geometry"]]


def african_borders(ne):
    """Land borders shared by two countries of BORDER_CONTINENTS (lines)."""
    af = ne[ne["CONTINENT"].isin(BORDER_CONTINENTS)].reset_index(drop=True)
    rows = []
    tree = shapely.STRtree(af.geometry.values)
    for i, g in enumerate(af.geometry.values):
        for j in tree.query(g, predicate="intersects"):
            if j <= i:
                continue
            inter = shapely.intersection(g.boundary, af.geometry.values[j].boundary)
            lines = [p for p in getattr(inter, "geoms", [inter])
                     if p.geom_type in ("LineString", "MultiLineString") and not p.is_empty]
            if lines:
                rows.append({"iso3_a": af.iso3[i], "iso3_b": af.iso3[j],
                             "geometry": shapely.line_merge(shapely.union_all(lines))})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)


def read_tile_into(url, grid, target, window_bounds, out_rows, out_cols, resampling, dtype):
    try:
        with rasterio.open(url) as src:
            # clip to the dataset (a sub-pixel difference at tile edges is ignored) so
            # GDAL can serve the read from overviews instead of full resolution
            win = from_bounds(*window_bounds, src.transform).intersection(
                Window(0, 0, src.width, src.height))
            a = src.read(1, window=win, out_shape=(out_rows, out_cols), resampling=resampling)
        return a.astype(dtype)
    except Exception as e:
        log(f"tile failed ({e.__class__.__name__}): {url}")
        return None


WORLDCOVER_CLASSES = (10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100)


def block_mode_and_water(a, f, water_class=80):
    """Majority WorldCover class (nodata 0 ignored) and water share (%) of f x f blocks."""
    h, w = a.shape[0] // f, a.shape[1] // f
    b = a[:h * f, :w * f].reshape(h, f, w, f)
    counts = np.stack([(b == c).sum(axis=(1, 3)) for c in WORLDCOVER_CLASSES])
    cls = np.array(WORLDCOVER_CLASSES, np.uint8)
    mode = np.where(counts.sum(0) > 0, cls[counts.argmax(0)], 0).astype(np.uint8)
    wpct = np.round(100 * counts[WORLDCOVER_CLASSES.index(water_class)] / (f * f)).astype(np.uint8)
    return mode, wpct


def landcover_grid(ctx):
    grid, dl, work = ctx["grid"], ctx["dl"], ctx["work"]
    lc = memmap(work / "landcover.npy", grid, np.uint8, fill=0)
    water = memmap(work / "water_pct.npy", grid, np.uint8, fill=0)
    keys = (dl / "worldcover_2021_tiles.txt").read_text().split()
    jobs = []
    for k in keys:
        m = re.search(r"_([NS])(\d{2})([EW])(\d{3})_Map\.tif$", k)
        lat = int(m[2]) * (1 if m[1] == "N" else -1)
        lon = int(m[4]) * (1 if m[3] == "E" else -1)
        w = grid.window_of((lon, lat, lon + 3, lat + 3))
        if w:
            jobs.append((k, w))

    F = LC_SUBSAMPLE

    def job(item):
        k, (r0, c0, nr, nc) = item
        b = (grid.west + c0 * grid.res, grid.north - (r0 + nr) * grid.res,
             grid.west + (c0 + nc) * grid.res, grid.north - r0 * grid.res)
        a = read_tile_into(URLS["worldcover"].format(key=k), grid, None, b, nr * F, nc * F,
                           Resampling.nearest, np.uint8)
        if a is not None:
            mode, wpct = block_mode_and_water(a, F)
            sub = lc[r0:r0 + nr, c0:c0 + nc]
            np.copyto(sub, mode, where=(mode > 0))
            wsub = water[r0:r0 + nr, c0:c0 + nc]
            np.maximum(wsub, wpct, out=wsub)
        return a is not None

    with cf.ThreadPoolExecutor(REMOTE_READ_THREADS) as ex:
        ok = list(ex.map(job, jobs))
    lc.flush(); water.flush()
    log(f"land cover: {sum(ok)}/{len(jobs)} WorldCover tiles read")
    return {"worldcover_tiles": len(jobs), "worldcover_tiles_read": int(sum(ok))}


def slope_grid(ctx):
    """Mean tan(slope) per cell from Copernicus GLO-90, computed at RES/DEM_OVERSAMPLE."""
    grid, dl, work = ctx["grid"], ctx["dl"], ctx["work"]
    tan = memmap(work / "tan_slope.npy", grid, np.float32, fill=0)
    names = (dl / "copdem90_tileList.txt").read_text().split()
    jobs = []
    for t in names:
        m = re.search(r"_([NS])(\d{2})_00_([EW])(\d{3})_00_DEM$", t)
        lat = int(m[2]) * (1 if m[1] == "N" else -1)
        lon = int(m[4]) * (1 if m[3] == "E" else -1)
        w = grid.window_of((lon, lat, lon + 1, lat + 1))
        if w:
            jobs.append((t, lat, w))
    F = DEM_OVERSAMPLE

    def job(item):
        t, lat0, (r0, c0, nr, nc) = item
        b = (grid.west + c0 * grid.res, grid.north - (r0 + nr) * grid.res,
             grid.west + (c0 + nc) * grid.res, grid.north - r0 * grid.res)
        z = read_tile_into(URLS["copdem"].format(t=t), grid, None, b, nr * F, nc * F,
                           Resampling.average, np.float32)
        if z is None:
            return False
        sub = grid.res / F
        lat = b[3] - (np.arange(nr * F) + 0.5) * sub
        dy = R_EARTH * math.radians(sub)
        dx = R_EARTH * np.cos(np.radians(lat)) * math.radians(sub)
        gy, gx = np.gradient(z.astype(np.float64))
        ts = np.hypot(gx / dx[:, None], gy / dy)
        tan[r0:r0 + nr, c0:c0 + nc] = ts.reshape(nr, F, nc, F).mean(axis=(1, 3))
        return True

    with cf.ThreadPoolExecutor(REMOTE_READ_THREADS) as ex:
        ok = list(ex.map(job, jobs))
    tan.flush()
    log(f"slope: {sum(ok)}/{len(jobs)} Copernicus GLO-90 tiles read")
    return {"copdem_tiles": len(jobs), "copdem_tiles_read": int(sum(ok))}


def country_grid(ctx):
    grid, dl, work = ctx["grid"], ctx["dl"], ctx["work"]
    ne = countries_frame(dl)
    cg = memmap(work / "countries.npy", grid, np.int16, fill=0)
    for r0, r1 in row_chunks(grid.height, 4000):
        b = (grid.west, grid.north - r1 * grid.res, grid.east, grid.north - r0 * grid.res)
        sel = ne[ne.intersects(box(*b))]
        if len(sel):
            cg[r0:r1] = rasterize(zip(sel.geometry, sel.cid.astype(int)), out_shape=(r1 - r0, grid.width),
                                  transform=grid.sub_transform(r0, 0), fill=0, dtype="int16")
    cg.flush()
    ne.drop(columns="geometry").to_csv(work / "countries.csv", index=False)
    borders = african_borders(ne)
    borders.to_file(work / "african_borders.gpkg", driver="GPKG")
    log(f"countries: {len(ne)}; African land-border segments: {len(borders)}")


def corruption_table(ctx, year, K=None):
    """Per country: WGI score (latest year <= reference year), c, road-speed factor."""
    dl = ctx["dl"]
    wgi = pd.read_csv(dl / "wgi_control_of_corruption.csv")
    ne = pd.read_csv(ctx["work"] / "countries.csv")
    use = wgi[wgi["year"] <= year]
    if use.empty:
        use = wgi[wgi["year"] == wgi["year"].min()]
    latest = use.sort_values("year").groupby("iso3").tail(1).set_index("iso3")
    t = ne.merge(latest, left_on="iso3", right_index=True, how="left")
    cont_med = t.groupby("CONTINENT")["score"].transform("median")
    t["score_source"] = np.where(t["score"].notna(), "WGI", "continent median")
    t["score"] = t["score"].fillna(cont_med).fillna(t["score"].median())
    t["wgi_year"] = t["year"].astype("Int64")
    t["c"] = (1 - t["score"] / 100).clip(0, 1)
    t["road_speed_factor"] = 1 - (CORRUPTION_K if K is None else K) * t["c"]
    return t[["cid", "iso3", "NAME", "CONTINENT", "wgi_year", "score", "score_source", "c",
              "road_speed_factor"]]


def settlements_epoch(ctx, epoch):
    """Settlement id per grid cell (0 = none) and population per settlement, from GHSL."""
    grid, dl, work = ctx["grid"], ctx["dl"], ctx["work"]
    zp = lambda p: f"/vsizip/{p}/" + next(n for n in zipfile.ZipFile(p).namelist() if n.endswith(".tif"))
    smod, popf = zp(dl / "ghsl" / f"smod_{epoch}.zip"), zp(dl / "ghsl" / f"pop_{epoch}.zip")
    with rasterio.open(smod) as s, rasterio.open(popf) as p:
        assert s.transform == p.transform and s.shape == p.shape
        b = transform_bounds(4326, s.crs, *grid.bounds, densify_pts=51)
        m = 50_000
        win = from_bounds(b[0] - m, b[1] - m, b[2] + m, b[3] + m, s.transform)
        win = win.round_offsets().round_lengths().intersection(Window(0, 0, s.width, s.height))
        codes = s.read(1, window=win)
        people = p.read(1, window=win).astype(np.float32)
        tr, crs = s.window_transform(win), s.crs
    people[people < 0] = 0
    labels, n = ndimage.label(np.isin(codes, URBAN_CODES), structure=np.ones((3, 3)))
    ids = np.arange(1, n + 1)
    pop = ndimage.sum(people, labels, ids) if n else np.array([])
    occupied = labels > 0
    cy, cx = (np.array(ndimage.center_of_mass(occupied, labels, ids)).T
              if n else (np.array([]), np.array([])))
    xs, ys = rasterio.transform.xy(tr, cy, cx) if n else ([], [])
    lon, lat = (rasterio.warp.transform(crs, 4326, xs, ys) if n else ([], []))
    table = pd.DataFrame({"settlement_id": ids, "population": np.round(pop),
                          "lon": np.round(lon, 5), "lat": np.round(lat, 5),
                          "cells_1km": ndimage.sum(occupied, labels, ids) if n else []})
    # settlement id on the lon/lat grid (nearest) and population per cell
    lab = memmap(work / f"settlement_id_{epoch}.npy", grid, np.int32, fill=0)
    reproject(labels.astype(np.int32), lab, src_transform=tr, src_crs=crs,
              dst_transform=grid.transform, dst_crs=4326, resampling=Resampling.nearest,
              src_nodata=0, dst_nodata=0, num_threads=min(16, cpu_count()))
    lab.flush()
    pg = memmap(work / f"population_{epoch}.npy", grid, np.float32, fill=0)
    reproject(people, pg, src_transform=tr, src_crs=crs, dst_transform=grid.transform,
              dst_crs=4326, resampling=Resampling.average, num_threads=min(16, cpu_count()))
    src_area = abs(tr.a * tr.e)
    area = grid.cell_area_m2()
    for r0, r1 in row_chunks(grid.height):
        pg[r0:r1] *= (area[r0:r1] / src_area)[:, None].astype(np.float32)
    pg.flush()
    # cells of a settlement kept even where the nearest-neighbour sampling missed it
    table.to_csv(work / f"settlements_{epoch}.csv", index=False)
    log(f"GHSL {epoch}: {n} settlements, {table.population.sum() / 1e6:.0f} M people in settlements, "
        f"{float(np.asarray(pg).sum(dtype=np.float64)) / 1e9:.2f} bn people on the grid")


def weiss_grid(ctx):
    """Weiss et al. 2015 friction (min/m) -> speed (km/h) on the grid; 0 where missing."""
    grid, dl, work = ctx["grid"], ctx["dl"], ctx["work"]
    sp = memmap(work / "weiss2015_speed.npy", grid, np.float32, fill=0)
    n = 0
    for f in sorted((dl / "weiss2015").glob("*.tif")):
        try:
            src = rasterio.open(f)
        except Exception as e:
            log(f"Weiss tile unreadable ({e.__class__.__name__}): {f.name}")
            continue
        with src:
            w = grid.window_of(tuple(src.bounds))
            if not w:
                continue
            r0, c0, nr, nc = w
            b = (grid.west + c0 * grid.res, grid.north - (r0 + nr) * grid.res,
                 grid.west + (c0 + nc) * grid.res, grid.north - r0 * grid.res)
            win = from_bounds(*b, src.transform).round_offsets().round_lengths()
            a = src.read(1, window=win, boundless=True, fill_value=0, out_shape=(nr, nc)).astype(np.float64)
            ok = np.isfinite(a) & (a > 0) & (a < 1e3)
            v = np.zeros(a.shape, np.float32)
            v[ok] = 60.0 / (1000.0 * a[ok])
            sub = sp[r0:r0 + nr, c0:c0 + nc]
            np.maximum(sub, v, out=sub)
            n += 1
    sp.flush()
    log(f"Weiss et al. 2015 friction: {n} tiles on the grid")
    return {"weiss2015_tiles": n}


def stage_grids(ctx):
    info = {}
    if WEISS2015_AUGMENT and 2015 in ctx["years"] and (ctx["dl"] / "weiss2015").exists():
        with Timer("Weiss et al. 2015 friction surface"):
            info.update(weiss_grid(ctx))
    with Timer("land cover (WorldCover 2021)"):
        info.update(landcover_grid(ctx))
    with Timer("slope (Copernicus GLO-90)"):
        info.update(slope_grid(ctx))
    with Timer("countries and African borders"):
        country_grid(ctx)
    for e in sorted(set(ctx["epoch"].values())):
        with Timer(f"settlements GHSL {e}"):
            settlements_epoch(ctx, e)
    (ctx["work"] / "grids_info.json").write_text(json.dumps(info))


# =============================================================================
# stage: roads (per year, per OSM extract, in parallel)
# =============================================================================
_SURFACE_RE = re.compile(r'"surface"=>"([^"]*)"')
# ways that legitimately cross water
_CROSSING_RE = r'"bridge"=>"(?!no")|"ford"=>"(?:yes|stepping_stones)"|"embankment"=>"yes"'



def road_speed(highway, other_tags):
    base = highway.map({k: v[0] for k, v in SPEED_TABLE.items()}).astype(float)
    paved = highway.map({k: v[1] for k, v in SPEED_TABLE.items()}).fillna(False).astype(bool)
    surf = other_tags.fillna("").str.extract(_SURFACE_RE, expand=False)
    unpaved = surf.isin(UNPAVED_SURFACES) | (surf.isna() & ~paved)
    return base.where(~unpaved, base * UNPAVED_FACTOR), surf


def line_lengths_km(geoms):
    """Great-circle length of each (multi)line, vectorised."""
    coords, idx = shapely.get_coordinates(geoms, return_index=True)
    if len(coords) < 2:
        return np.zeros(len(geoms))
    # break between parts of multilines is small; ignored
    lon, lat = np.radians(coords[:, 0]), np.radians(coords[:, 1])
    same = idx[1:] == idx[:-1]
    dlat, dlon = lat[1:] - lat[:-1], lon[1:] - lon[:-1]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[1:]) * np.cos(lat[:-1]) * np.sin(dlon / 2) ** 2
    seg = 2 * R_EARTH * np.arcsin(np.sqrt(np.clip(a, 0, 1))) / 1000 * same
    return np.bincount(idx[1:], weights=seg, minlength=len(geoms))


def roads_job(job):
    """One OSM extract -> max-speed window, km by class, checkpoint points."""
    pbf, out, grid_d, borders_path = job["pbf"], Path(job["out"]), job["grid"], job["borders"]
    if (out.with_suffix(".done")).exists():
        return json.loads(out.with_suffix(".done").read_text())
    grid = Grid(grid_d["bbox"], grid_d["res_deg"])
    t0 = time.time()
    g = pyogrio.read_dataframe(pbf, layer="lines", columns=["osm_id", "highway", "other_tags"],
                               where="highway IS NOT NULL")
    g = g[g["highway"].isin(list(SPEED_TABLE))]
    stats = {"extract": Path(pbf).name, "segments": int(len(g))}
    if g.empty:
        out.with_suffix(".done").write_text(json.dumps(stats))
        return stats
    g["speed"], _ = road_speed(g["highway"], g["other_tags"])
    g["crossing"] = g["other_tags"].fillna("").str.contains(_CROSSING_RE)
    g = g.drop(columns="other_tags")
    g = g[g.intersects(box(*grid.bounds))]
    km = line_lengths_km(g.geometry.values)
    stats["km_by_class"] = pd.Series(km, index=g["highway"].values).groupby(level=0).sum().round(1).to_dict()
    b = g.total_bounds
    pad = grid.res          # one cell of margin: lines on the box edge must not be clipped away
    w = grid.window_of((b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad))
    if w:
        r0, c0, nr, nc = w
        g = g.sort_values("speed")
        speed = rasterize(zip(g.geometry, g["speed"]), out_shape=(nr, nc),
                          transform=grid.sub_transform(r0, c0), fill=0, all_touched=True,
                          dtype="float32")
        br = g[g["crossing"]]
        bridge = rasterize(((geom, 1) for geom in br.geometry), out_shape=(nr, nc),
                           transform=grid.sub_transform(r0, c0), fill=0, all_touched=True,
                           dtype="uint8") if len(br) else np.zeros((nr, nc), np.uint8)
        np.savez(out, r0=r0, c0=c0, speed=speed, bridge=bridge)
        stats["crossing_segments"] = int(len(br))
        stats["window"] = [int(r0), int(c0), int(nr), int(nc)]
    # official checkpoints: major roads crossing an African land border
    if borders_path and Path(borders_path).exists():
        bd = gpd.read_file(borders_path, bbox=tuple(b))
        big = g[g["highway"].isin(CHECKPOINT_CLASSES)]
        if len(bd) and len(big):
            pts = []
            tree = shapely.STRtree(big.geometry.values)
            for _, row in bd.iterrows():
                for j in tree.query(row.geometry, predicate="intersects"):
                    x = shapely.intersection(row.geometry, big.geometry.values[j])
                    for p in shapely.get_parts(x):
                        if p.geom_type == "Point":
                            pts.append((p.x, p.y, row.iso3_a, row.iso3_b, big.highway.values[j]))
            stats["checkpoints"] = pts
    stats["seconds"] = round(time.time() - t0, 1)
    out.with_suffix(".done").write_text(json.dumps(stats))
    return stats


def ml_batch_job(job):
    """Parse a batch of Microsoft TSV lines and rasterize them (presence) in a window."""
    lines, grid_d = job
    grid = Grid(grid_d["bbox"], grid_d["res_deg"])
    geoms, isos = [], []
    for ln in lines:
        iso, _, gj = ln.partition("\t")
        if not gj:
            continue
        o = json.loads(gj)
        geoms.append(shape(o.get("geometry", o)))
        isos.append(iso)
    if not geoms:
        return None
    arr = np.array(geoms, dtype=object)
    arr = arr[shapely.intersects(arr, box(*grid.bounds))]
    if not len(arr):
        return None
    km = float(line_lengths_km(arr).sum())
    tb = shapely.total_bounds(arr)
    w = grid.window_of((tb[0] - grid.res, tb[1] - grid.res, tb[2] + grid.res, tb[3] + grid.res))
    if not w:
        return None
    r0, c0, nr, nc = w
    a = rasterize(((g, 1) for g in arr), out_shape=(nr, nc), transform=grid.sub_transform(r0, c0),
                  fill=0, all_touched=True, dtype="uint8")
    return r0, c0, a, km, len(arr)


def ml_roads(ctx):
    grid, dl, work = ctx["grid"], ctx["dl"], ctx["work"]
    ml = memmap(work / "ml_roads.npy", grid, np.uint8, fill=0)
    total_km, n_seg = 0.0, 0

    def batches():
        for f in ML_FILES:
            with zipfile.ZipFile(dl / "ml" / f) as z:
                for name in z.namelist():
                    if name.endswith("/"):
                        continue
                    with z.open(name) as fh:
                        buf = []
                        for raw in io.TextIOWrapper(fh, encoding="utf-8"):
                            buf.append(raw.rstrip("\r\n"))
                            if len(buf) >= 50_000:
                                yield (buf, grid.to_dict()); buf = []
                        if buf:
                            yield (buf, grid.to_dict())

    n, _ = plan_workers(1.5e9, 10**6)
    log(f"Microsoft ML roads: {n} workers")

    def merge(res):
        nonlocal total_km, n_seg
        if res is None:
            return
        r0, c0, a, km, k = res
        sub = ml[r0:r0 + a.shape[0], c0:c0 + a.shape[1]]
        np.maximum(sub, a, out=sub)
        total_km += km; n_seg += k

    with cf.ProcessPoolExecutor(n, mp_context=mp.get_context("fork")) as ex:
        inflight = set()
        for b in batches():                 # keep at most 2 batches per worker in memory
            inflight.add(ex.submit(ml_batch_job, b))
            if len(inflight) >= 2 * n:
                done, inflight = cf.wait(inflight, return_when=cf.FIRST_COMPLETED)
                for f in done:
                    merge(f.result())
        for f in cf.as_completed(inflight):
            merge(f.result())
    ml.flush()
    log(f"Microsoft ML roads: {n_seg:,} segments, {total_km:,.0f} km inside the grid")
    return {"ml_segments": n_seg, "ml_km": round(total_km)}


def stage_roads(ctx):
    grid, work, dl = ctx["grid"], ctx["work"], ctx["dl"]
    plan = json.loads((work / "osm_plan.json").read_text())
    cp_rows, km_rows, info = [], [], {}
    for y in ctx["years"]:
        jobs = []
        for r in plan[str(y)]:
            pbf = dl / "osm" / str(y) / Path(r["url"]).name
            jobs.append({"pbf": str(pbf), "out": str(work / "roads" / str(y) / f"{r['region']}.npz"),
                         "grid": grid.to_dict(), "borders": str(work / "african_borders.gpkg"),
                         "bytes": pbf.stat().st_size})
        (work / "roads" / str(y)).mkdir(parents=True, exist_ok=True)
        # GDAL OSM driver + geopandas: ~ 1.5 GB + 7 x the .pbf size (measured on Benin/Togo
        # extracts; conservative), plus the rasterized window
        stats = run_budgeted(roads_job, jobs, lambda j: 1.5e9 + 7 * j["bytes"], f"roads {y}")
        speed = memmap(work / f"road_speed_{y}.npy", grid, np.float32, fill=0)
        bridge = memmap(work / f"road_crossing_{y}.npy", grid, np.uint8, fill=0)
        for j, s in zip(jobs, stats):
            npz = Path(j["out"])
            if npz.exists():
                d = np.load(npz)
                r0, c0, a = int(d["r0"]), int(d["c0"]), d["speed"]
                sub = speed[r0:r0 + a.shape[0], c0:c0 + a.shape[1]]
                np.maximum(sub, a, out=sub)
                bsub = bridge[r0:r0 + a.shape[0], c0:c0 + a.shape[1]]
                np.maximum(bsub, d["bridge"], out=bsub)
            for hw, v in (s.get("km_by_class") or {}).items():
                km_rows.append({"year": y, "extract": s["extract"], "highway": hw, "km": v})
            for p in s.get("checkpoints") or []:
                cp_rows.append({"year": y, "lon": p[0], "lat": p[1], "iso3_a": p[2],
                                "iso3_b": p[3], "highway": p[4]})
        speed.flush(); bridge.flush()
        info[f"osm_extracts_{y}"] = len(jobs)
    if INCLUDE_ML_ROADS:
        with Timer("Microsoft ML roads"):
            info.update(ml_roads(ctx))
    pd.DataFrame(km_rows).to_csv(work / "road_km_by_extract.csv", index=False)
    cp = pd.DataFrame(cp_rows, columns=["year", "lon", "lat", "iso3_a", "iso3_b", "highway"])
    cp.to_csv(work / "checkpoints_raw.csv", index=False)
    (work / "roads_info.json").write_text(json.dumps(info))


# =============================================================================
# stage: friction (per year)
# =============================================================================
def checkpoint_cells(ctx, year, corr, K=None, delay=None):
    """Unique grid cells of official crossings with their delay (minutes)."""
    grid = ctx["grid"]
    cp = pd.read_csv(ctx["work"] / "checkpoints_raw.csv")
    cp = cp[cp["year"] == year]
    if cp.empty:
        return pd.DataFrame(columns=["row", "col", "lon", "lat", "iso3_a", "iso3_b", "delay_min"])
    cp["row"] = ((grid.north - cp["lat"]) / grid.res).astype(int).clip(0, grid.height - 1)
    cp["col"] = ((cp["lon"] - grid.west) / grid.res).astype(int).clip(0, grid.width - 1)
    cp = cp.drop_duplicates(["row", "col"])
    c = corr.drop_duplicates("iso3").set_index("iso3")["c"]
    cmean = (cp["iso3_a"].map(c).fillna(c.median()) + cp["iso3_b"].map(c).fillna(c.median())) / 2
    K = CORRUPTION_K if K is None else K
    delay = BORDER_DELAY_MIN if delay is None else delay
    cp["delay_min"] = delay / (1 - K * cmean)
    return cp


def friction_from_parts(ctx, y, K, delay, out_path):
    """Friction (min/m) = 60 / (1000 max(road x (1 - K c), off-road)); + border delays.
    Used for the baseline and for each sensitivity scenario."""
    grid, work = ctx["grid"], ctx["work"]
    corr = corruption_table(ctx, y, K)
    factor = np.ones(int(max(corr.cid.max(), 0)) + 1, np.float32)
    factor[corr.cid.values] = corr.road_speed_factor.values
    cg = memmap(work / "countries.npy", grid, None, mode="r")
    rfin = memmap(work / f"road_final_{y}.npy", grid, None, mode="r")
    off = memmap(work / "offroad_speed.npy", grid, None, mode="r")
    fr = memmap(out_path, grid, np.float32)
    passable = 0
    for r0, r1 in row_chunks(grid.height):
        sp = np.maximum(np.asarray(rfin[r0:r1]) * factor[cg[r0:r1]], np.asarray(off[r0:r1]))
        f = np.full(sp.shape, np.inf, np.float32)
        ok = sp > 0
        f[ok] = 60.0 / (1000.0 * sp[ok])
        fr[r0:r1] = f
        passable += int(ok.sum())
    cp = checkpoint_cells(ctx, y, corr, K, delay)
    if len(cp) and delay > 0:
        ew, dy, _, _ = step_lengths(grid)
        L = np.sqrt(ew[cp.row.values] * dy)
        cur = fr[cp.row.values, cp.col.values]
        ok = np.isfinite(cur)
        fr[cp.row.values[ok], cp.col.values[ok]] = cur[ok] + (cp.delay_min.values[ok] / L[ok]).astype(np.float32)
    fr.flush()
    return {"passable_cells": passable, "checkpoints": int(len(cp))}, cp


def stage_friction(ctx):
    grid, work = ctx["grid"], ctx["work"]
    lc = memmap(work / "landcover.npy", grid, None, mode="r")
    water = memmap(work / "water_pct.npy", grid, None, mode="r")
    tan = memmap(work / "tan_slope.npy", grid, None, mode="r")
    cg = memmap(work / "countries.npy", grid, None, mode="r")
    ml = memmap(work / "ml_roads.npy", grid, None, mode="r") if INCLUDE_ML_ROADS else None
    lut = np.zeros(256, np.float32)
    for k, v in LANDCOVER_SPEED.items():
        lut[k] = v
    ew, dy, _, _ = step_lengths(grid)
    y_end = ctx["years"][-1]
    augment = WEISS2015_AUGMENT and ctx["years"][0] == 2015 and (work / "weiss2015_speed.npy").exists()
    if augment:
        weiss = memmap(work / "weiss2015_speed.npy", grid, None, mode="r")
        road_end = memmap(work / f"road_speed_{y_end}.npy", grid, None, mode="r")
        cross_end = memmap(work / f"road_crossing_{y_end}.npy", grid, None, mode="r")
        T = int(round(COMPLETE_TILE_DEG / grid.res))
        nti, ntj = -(-grid.height // T), -(-grid.width // T)
        tile_osm = np.zeros((nti, ntj)); tile_weiss = np.zeros((nti, ntj))

    def clean(rs, cross, open_water):
        on_water = (rs > 0) & open_water
        keep = on_water & (cross > 0)
        rs[on_water & ~keep] = 0
        return int((on_water & ~keep).sum()), int(keep.sum())

    for y in ctx["years"]:
        corr = corruption_table(ctx, y)
        corr.to_csv(work / f"corruption_{y}.csv", index=False)
        factor = np.ones(int(max(corr.cid.max(), 0)) + 1, np.float32)
        factor[corr.cid.values] = corr.road_speed_factor.values
        road = memmap(work / f"road_speed_{y}.npy", grid, None, mode="r")
        crossing = memmap(work / f"road_crossing_{y}.npy", grid, None, mode="r")
        # final road speed before the governance factor, and off-road speed: the parts
        # from which friction is built for the baseline and for every sensitivity scenario
        rfin = memmap(work / f"road_final_{y}.npy", grid, np.float32)
        offm = memmap(work / "offroad_speed.npy", grid, np.float32) if y == ctx["years"][0] else None
        stats = {"road_cells": 0, "ml_cells": 0, "passable_cells": 0,
                 "osm_road_cells_dropped_on_water": 0, "osm_road_cells_kept_as_crossings": 0,
                 "ml_road_cells_dropped_on_water": 0, "weiss2015_cells_added": 0}
        use_ml = INCLUDE_ML_ROADS and y == ctx["years"][-1]
        for r0, r1 in row_chunks(grid.height):
            rs = np.array(road[r0:r1])
            open_water = np.asarray(water[r0:r1]) >= WATER_ROAD_MAX_PCT
            dropped, kept = clean(rs, np.asarray(crossing[r0:r1]), open_water)
            on_water = open_water & (np.asarray(road[r0:r1]) > 0)
            stats["osm_road_cells_dropped_on_water"] += dropped
            stats["osm_road_cells_kept_as_crossings"] += kept
            if augment and y == 2015:
                wz = np.asarray(weiss[r0:r1])
                re = np.array(road_end[r0:r1])
                clean(re, np.asarray(cross_end[r0:r1]), open_water)
                # Weiss network cells that are roads today (drops Weiss rivers, sea lanes, rail)
                net = (wz >= WEISS_NETWORK_KMH) & (re > 0) & ~open_water
                # completeness of OSM 2015 on that network, per tile, before completion
                rows = (np.arange(r0, r1) // T)[:, None]
                cols = (np.arange(grid.width) // T)[None, :]
                idx = (np.broadcast_to(rows, rs.shape) * ntj + np.broadcast_to(cols, rs.shape)).ravel()
                tile_osm += np.bincount(idx, ((rs > 0) & net).ravel(), nti * ntj).reshape(nti, ntj)
                tile_weiss += np.bincount(idx, net.ravel(), nti * ntj).reshape(nti, ntj)
                add = (rs == 0) & net
                rs[add] = np.minimum(wz[add], re[add])
                stats["weiss2015_cells_added"] += int(add.sum())
            if use_ml:
                cand = (rs == 0) & (ml[r0:r1] > 0) & ~on_water
                stats["ml_road_cells_dropped_on_water"] += int((cand & open_water).sum())
                add = cand & ~open_water
                rs[add] = ML_SPEED
                stats["ml_cells"] += int(add.sum())
            stats["road_cells"] += int((rs > 0).sum())
            rfin[r0:r1] = rs
            if offm is not None:
                offm[r0:r1] = lut[lc[r0:r1]] * np.exp(-TOBLER_K * tan[r0:r1])
        rfin.flush()
        if offm is not None:
            offm.flush()
        fstats, cp = friction_from_parts(ctx, y, CORRUPTION_K, BORDER_DELAY_MIN,
                                         work / f"friction_{y}.npy")
        stats.update(fstats)
        cp.to_csv(work / f"checkpoints_{y}.csv", index=False)
        (work / f"friction_{y}.json").write_text(json.dumps(stats))
        log(f"friction {y}: {stats}")
        if augment and y == 2015:
            ti, tj = np.meshgrid(np.arange(nti), np.arange(ntj), indexing="ij")
            tiles = pd.DataFrame({
                "tile_row": ti.ravel(), "tile_col": tj.ravel(),
                "west": grid.west + tj.ravel() * T * grid.res,
                "north": grid.north - ti.ravel() * T * grid.res,
                "weiss_network_cells": tile_weiss.ravel(), "osm2015_cells_on_weiss_network": tile_osm.ravel()})
            # weiss_network_cells: Weiss 2015 network cells that are OSM roads in END_YEAR
            tiles["completeness"] = tiles.osm2015_cells_on_weiss_network / tiles.weiss_network_cells.where(tiles.weiss_network_cells > 0)
            tiles["osm2015_complete"] = (tiles.completeness >= COMPLETE_MIN) & \
                (tiles.weiss_network_cells >= COMPLETE_MIN_CELLS)
            tiles.to_csv(work / "osm2015_completeness_tiles.csv", index=False)
            log(f"OSM 2015 completeness: {int(tiles.osm2015_complete.sum())} of "
                f"{int((tiles.weiss_network_cells >= COMPLETE_MIN_CELLS).sum())} assessed "
                f"{COMPLETE_TILE_DEG} deg tiles >= {COMPLETE_MIN:.0%}")


# =============================================================================
# stage: travel time (per year x layer, in parallel)
# =============================================================================
def layer_names():
    return [f"cities_{k}" for k in CITY_LAYERS] + [f"ports_{k}" for k in PORT_LAYERS]


def load_ports(ctx):
    df = pd.read_csv(ctx["dl"] / "UpdatedPub150.csv",
                     usecols=["Main Port Name", "Country Code", "Harbor Size", "Latitude", "Longitude"])
    g = ctx["grid"]
    df = df[df["Longitude"].between(g.west, g.east) & df["Latitude"].between(g.south, g.north)]
    return df.reset_index(drop=True)


def port_cells(ports, grid, fr):
    """Grid cell of each port, moved to the nearest passable cell within PORT_SNAP_KM."""
    rows, cols = [], []
    k = int(math.ceil(PORT_SNAP_KM / (R_EARTH * math.radians(grid.res) / 1000))) + 1
    for lon, lat in zip(ports["Longitude"], ports["Latitude"]):
        r = int((grid.north - lat) / grid.res); c = int((lon - grid.west) / grid.res)
        r0, r1, c0, c1 = max(0, r - k), min(grid.height, r + k + 1), max(0, c - k), min(grid.width, c + k + 1)
        win = np.isfinite(fr[r0:r1, c0:c1])
        if not win.any():
            rows.append(-1); cols.append(-1); continue
        rr, cc = np.nonzero(win)
        lat_c = grid.north - (rr + r0 + 0.5) * grid.res
        dx = (cc + c0 - c) * np.cos(np.radians(lat_c)); dyy = rr + r0 - r
        i = np.argmin(dx ** 2 + dyy ** 2)
        dist_km = math.hypot(dx[i], dyy[i]) * R_EARTH * math.radians(grid.res) / 1000
        if dist_km <= PORT_SNAP_KM:
            rows.append(int(rr[i] + r0)); cols.append(int(cc[i] + c0))
        else:
            rows.append(-1); cols.append(-1)
    return np.array(rows), np.array(cols)


def tt_job(job):
    grid = Grid(job["grid"]["bbox"], job["grid"]["res_deg"])
    out = Path(job["out"])
    done = Path(str(out) + ".done")      # resume, unless the friction grid was rebuilt since
    if out.exists() and done.exists() and done.stat().st_mtime >= Path(job["friction"]).stat().st_mtime:
        return json.loads(done.read_text())
    t0 = time.time()
    fr = np.load(job["friction"], mmap_mode="r")
    src = np.load(job["sources"])
    dist = np.lib.format.open_memmap(out, mode="w+", dtype=np.float32, shape=grid.shape)
    travel_time(np.asarray(fr), src, grid, out=dist)
    dist.flush()
    info = {"year": job["year"], "layer": job["layer"], "sources": int(len(src)),
            "seconds": round(time.time() - t0, 1),
            "peak_rss_gb": round(psutil.Process().memory_info().rss / 1e9, 2)}
    Path(str(out) + ".done").write_text(json.dumps(info))
    return info


def stage_traveltime(ctx):
    grid, work = ctx["grid"], ctx["work"]
    (work / "tt").mkdir(exist_ok=True)
    ports = load_ports(ctx)
    ports["class"] = ports["Harbor Size"].map({"Large": 1, "Medium": 2, "Small": 3,
                                               "Very Small": 4}).fillna(5).astype(int)
    jobs, dest_rows = [], []
    for y in ctx["years"]:
        fr = memmap(work / f"friction_{y}.npy", grid, None, mode="r")
        e = ctx["epoch"][y]
        lab = memmap(work / f"settlement_id_{e}.npy", grid, None, mode="r")
        st = pd.read_csv(work / f"settlements_{e}.csv")
        pr, pc = port_cells(ports, grid, fr)
        for name in layer_names():
            kind, k = name.split("_"); k = int(k)
            if kind == "cities":
                lo, hi = CITY_LAYERS[k]
                ids = st.loc[(st.population >= lo) & (st.population < hi), "settlement_id"].values
                lut = np.zeros(int(st.settlement_id.max()) + 2 if len(st) else 2, bool)
                lut[ids] = True
                srcs = []
                for r0, r1 in row_chunks(grid.height):
                    m = lut[np.asarray(lab[r0:r1])] & np.isfinite(fr[r0:r1])
                    srcs.append(np.flatnonzero(m) + r0 * grid.width)
                src = np.concatenate(srcs)
                n_dest = int(len(ids))
            else:
                sel = np.ones(len(ports), bool) if PORT_LAYERS[k] is None else \
                    ports["Harbor Size"].isin(PORT_LAYERS[k]).to_numpy(copy=True)
                sel = sel & (pr >= 0)          # pandas 3 returns read-only arrays
                src = np.unique(pr[sel].astype(np.int64) * grid.width + pc[sel])
                n_dest = int(sel.sum())
            sp = work / "tt" / f"sources_{y}_{name}.npy"
            np.save(sp, src.astype(np.int64))
            dest_rows.append({"year": y, "layer": name, "destinations": n_dest,
                              "source_cells": int(len(src))})
            jobs.append({"grid": grid.to_dict(), "friction": str(work / f"friction_{y}.npy"),
                         "sources": str(sp), "out": str(work / "tt" / f"tt_{y}_{name}.npy"),
                         "year": y, "layer": name})
    pd.DataFrame(dest_rows).to_csv(work / "destinations.csv", index=False)
    warm_up_numba()
    # per task: dist float32 + pos int32 + heap (<= N int32, typically far less) + sources
    per_task = grid.size * (4 + 4 + 2) + 0.3e9
    info = run_budgeted(tt_job, jobs, lambda j: per_task, "travel time")
    pd.DataFrame(info).to_csv(work / "tt_timings.csv", index=False)


# =============================================================================
# stage: outputs (COGs, PNGs, statistics, methods folder)
# =============================================================================
BAND_DESC = {**{f"cities_{k}": f"cities_{k}: population {int(lo):,} to <{int(hi):,}"
                for k, (lo, hi) in CITY_LAYERS.items()},
             **{f"ports_{k}": f"ports_{k}: " + ("any" if v is None else ", ".join(sorted(v)))
                for k, v in PORT_LAYERS.items()}}


def write_cog(path, grid, bands, dtype, nodata, desc, factor=1, resampling="average",
              tmpdir=None, units=None):
    """bands: list of callables returning a (rows, cols) block for (r0, r1).
    factor > 1 aggregates blocks of factor x factor cells (mean of valid cells)."""
    H, W = grid.height // factor, grid.width // factor
    tr = from_origin(grid.west, grid.north, grid.res * factor, grid.res * factor)
    tmp = Path(tmpdir or path.parent) / (path.stem + ".tmp.tif")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    prof = dict(driver="GTiff", height=H, width=W, count=len(bands), dtype=dtype, crs="EPSG:4326",
                transform=tr, nodata=nodata, tiled=True, blockxsize=512, blockysize=512,
                compress="DEFLATE", predictor=2 if np.dtype(dtype).kind in "iu" else 3,
                BIGTIFF="YES")
    step = 2000 - 2000 % factor
    with rasterio.open(tmp, "w", **prof) as dst:
        if units:
            dst.units = tuple([units] * len(bands))
            dst.update_tags(UNITS=units)
        for b, (get, d) in enumerate(zip(bands, desc), start=1):
            dst.set_band_description(b, d)
            for r0, r1 in row_chunks(grid.height - grid.height % factor, step):
                a = get(r0, r1)
                if factor > 1:
                    a = block_mean(a, factor, nodata, round_=np.dtype(dtype).kind in "iu")
                dst.write(a.astype(dtype), b, window=Window(0, r0 // factor, W, a.shape[0]))
    rasterio.shutil.copy(tmp, path, driver="COG", compress="DEFLATE",
                         predictor="YES" if np.dtype(dtype).kind in "iu" else "FLOATING_POINT",
                         overview_resampling=resampling, BIGTIFF="YES", num_threads="ALL_CPUS")
    tmp.unlink()


def block_mean(a, f, nodata, round_=True):
    h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    x = a[:h, :w].astype(np.float64)
    valid = (x != nodata) & np.isfinite(x)
    x = np.where(valid, x, 0).reshape(h // f, f, w // f, f)
    n = valid.reshape(h // f, f, w // f, f).sum(axis=(1, 3))
    m = x.sum(axis=(1, 3)) / np.maximum(n, 1)
    return np.where(n > 0, np.round(m) if round_ else m, nodata)


def tt_block(work, y, name):
    mm = np.load(work / "tt" / f"tt_{y}_{name}.npy", mmap_mode="r")

    def get(r0, r1):
        a = np.array(mm[r0:r1])
        out = np.full(a.shape, TT_NODATA, np.float64)
        ok = np.isfinite(a)
        out[ok] = np.minimum(np.round(a[ok]), TT_NODATA - 1)
        return out
    return get


def fr_block(work, y):
    mm = np.load(work / f"friction_{y}.npy", mmap_mode="r")

    def get(r0, r1):
        a = np.array(mm[r0:r1], dtype=np.float64)
        a[~np.isfinite(a)] = -9999.0
        return a
    return get


def change_block(work, y0, y1, name):
    a0 = np.load(work / "tt" / f"tt_{y0}_{name}.npy", mmap_mode="r")
    a1 = np.load(work / "tt" / f"tt_{y1}_{name}.npy", mmap_mode="r")

    def get(r0, r1):
        x0, x1 = np.array(a0[r0:r1]), np.array(a1[r0:r1])
        ok = np.isfinite(x0) & np.isfinite(x1)
        out = np.full(x0.shape, CHANGE_NODATA, np.float64)
        out[ok] = np.clip(np.round(x1[ok] - x0[ok]), -32767, 32767)
        return out
    return get


TT_BINS = [0, 15, 30, 60, 120, 240, 480, 960, 1920, 65535]
TT_COLORS = ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5",
             "#08519c", "#08306b"]
CH_BINS = [-32767, -120, -60, -30, -10, -2, 2, 10, 30, 60, 120, 32767]
CH_COLORS = ["#053061", "#2166ac", "#4393c3", "#92c5de", "#d1e5f0", "#e0e0e0", "#fddbc7",
             "#f4a582", "#d6604d", "#b2182b", "#67001f"]


def png_map(path, arr, nodata, title, kind, extent):
    a = np.ma.masked_equal(arr.astype(np.float64), nodata)
    if kind == "tt":
        cmap, norm, label = ListedColormap(TT_COLORS), BoundaryNorm(TT_BINS, 9), "minutes"
        ticks = TT_BINS[:-1]
    elif kind == "change":
        cmap, norm, label = ListedColormap(CH_COLORS), BoundaryNorm(CH_BINS, 11), "change (minutes)"
        ticks = CH_BINS[1:-1]
    else:
        cmap, label = plt.get_cmap("Greys"), "friction (min/m, log10)"
        a = np.ma.log10(np.ma.masked_less_equal(a, 0)); norm = None; ticks = None
    cmap = cmap.with_extremes(bad="#ffffff")
    aspect = (extent[1] - extent[0]) / (extent[3] - extent[2])
    width_in = 18 if aspect > 1.5 else 9          # global ~3600 px wide; regions smaller
    fig, ax = plt.subplots(figsize=(width_in, width_in / aspect * 1.08 + 0.8))
    im = ax.imshow(a, cmap=cmap, norm=norm, extent=extent, interpolation="nearest")
    ax.set_title(title, fontsize=14, loc="left")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, aspect=60)
    cb.set_label(label)
    if ticks:
        cb.set_ticks(ticks)
    fig.savefig(path, dpi=200 if aspect > 1.5 else 150, bbox_inches="tight")
    plt.close(fig)


def summary_tables(ctx):
    """Population-weighted travel time per country, continent and globally."""
    grid, work = ctx["grid"], ctx["work"]
    cg = memmap(work / "countries.npy", grid, None, mode="r")
    ct = pd.read_csv(work / "countries.csv")
    rows = []
    for y in ctx["years"]:
        pop = memmap(work / f"population_{ctx['epoch'][y]}.npy", grid, None, mode="r")
        for name in layer_names():
            mm = np.load(work / "tt" / f"tt_{y}_{name}.npy", mmap_mode="r")
            n = int(ct.cid.max()) + 1
            w = np.zeros(n); wt = np.zeros(n); w60 = np.zeros(n); wun = np.zeros(n)
            for r0, r1 in row_chunks(grid.height):
                t = np.asarray(mm[r0:r1]).ravel(); p = np.asarray(pop[r0:r1]).ravel().astype(np.float64)
                c = np.asarray(cg[r0:r1]).ravel().astype(np.int64)
                ok = np.isfinite(t)
                w += np.bincount(c[ok], p[ok], n); wt += np.bincount(c[ok], p[ok] * t[ok], n)
                w60 += np.bincount(c[ok & (t <= 60)], p[ok & (t <= 60)], n)
                wun += np.bincount(c[~ok], p[~ok], n)
            df = pd.DataFrame({"cid": np.arange(n), "pop": w, "pop_x_tt": wt, "pop_le60": w60,
                               "pop_unreachable": wun})
            df = df.merge(ct[["cid", "iso3", "NAME", "CONTINENT"]], on="cid", how="left")
            df["iso3"] = df["iso3"].fillna("none"); df["CONTINENT"] = df["CONTINENT"].fillna("none")
            df["year"], df["layer"] = y, name
            rows.append(df)
    d = pd.concat(rows)
    def agg(g):
        return pd.Series({"population": g["pop"].sum(),
                          "pop_weighted_mean_min": g["pop_x_tt"].sum() / max(g["pop"].sum(), 1),
                          "share_within_60min": g["pop_le60"].sum() / max(g["pop"].sum(), 1),
                          "pop_unreachable": g["pop_unreachable"].sum()})
    by_country = d.groupby(["year", "layer", "iso3", "NAME", "CONTINENT"]).apply(agg, include_groups=False).reset_index()
    by_cont = d.groupby(["year", "layer", "CONTINENT"]).apply(agg, include_groups=False).reset_index()
    glob = d.groupby(["year", "layer"]).apply(agg, include_groups=False).reset_index()
    return by_country, by_cont, glob


def stage_outputs(ctx):
    grid, work, res = ctx["grid"], ctx["work"], ctx["results"]
    y0, y1 = ctx["years"][0], ctx["years"][-1]
    names = layer_names()
    for sub in ("cog_1km", "cog_10km", "png", "methods", "tables"):
        (res / sub).mkdir(parents=True, exist_ok=True)
    desc = [BAND_DESC[n] for n in names]
    for factor, sub, tag in ((1, "cog_1km", "1km"), (LIGHT_FACTOR, "cog_10km", "10km")):
        for y in ctx["years"]:
            with Timer(f"COG travel time {y} {tag}"):
                write_cog(res / sub / f"traveltime_{y}_{tag}.tif", grid,
                          [tt_block(work, y, n) for n in names], "uint16", TT_NODATA, desc, factor,
                          tmpdir=work / "tmp", units="minutes")
            write_cog(res / sub / f"friction_{y}_{tag}.tif", grid, [fr_block(work, y)], "float32",
                      -9999.0, ["friction (minutes per metre)"], factor, tmpdir=work / "tmp",
                      units="minutes per metre")
        with Timer(f"COG change {tag}"):
            write_cog(res / sub / f"traveltime_change_{y1}_minus_{y0}_{tag}.tif", grid,
                      [change_block(work, y0, y1, n) for n in names], "int16", CHANGE_NODATA,
                      [f"{d} (minutes, {y1} - {y0})" for d in desc], factor, tmpdir=work / "tmp",
                      units="minutes")
    # PNGs from the 10 km COGs
    ext = [grid.west, grid.east, grid.south, grid.north]
    with Timer("PNG maps"):
        for y in ctx["years"]:
            with rasterio.open(res / "cog_10km" / f"traveltime_{y}_10km.tif") as r:
                for b, n in enumerate(names, start=1):
                    png_map(res / "png" / f"traveltime_{y}_{n}.png", r.read(b), TT_NODATA,
                            f"Travel time to {BAND_DESC[n].split(': ', 1)[1]} - {y}", "tt", ext)
            with rasterio.open(res / "cog_10km" / f"friction_{y}_10km.tif") as r:
                png_map(res / "png" / f"friction_{y}.png", r.read(1), -9999.0,
                        f"Friction {y}", "friction", ext)
        with rasterio.open(res / "cog_10km" / f"traveltime_change_{y1}_minus_{y0}_10km.tif") as r:
            for b, n in enumerate(names, start=1):
                png_map(res / "png" / f"change_{y1}_minus_{y0}_{n}.png", r.read(b), CHANGE_NODATA,
                        f"Change in travel time to {BAND_DESC[n].split(': ', 1)[1]}, {y1} - {y0} "
                        "(blue = faster)", "change", ext)
    with Timer("summary tables"):
        bc, bco, gl = summary_tables(ctx)
        bc.to_csv(res / "tables" / "pop_weighted_traveltime_by_country.csv", index=False)
        bco.to_csv(res / "tables" / "pop_weighted_traveltime_by_continent.csv", index=False)
        gl.to_csv(res / "tables" / "pop_weighted_traveltime_global.csv", index=False)
    write_methods(ctx)


def write_methods(ctx):
    work, res, dl = ctx["work"], ctx["results"] / "methods", ctx["dl"]
    res.mkdir(parents=True, exist_ok=True)
    cfg = {k: (sorted(v) if isinstance(v, set) else v) for k, v in globals().items()
           if k.isupper() and not k.startswith("_") and k not in ("URLS", "REQUIRED", "LOG",
                                                                   "MANIFEST", "BAND_DESC")
           and isinstance(v, (int, float, str, list, dict, tuple, set, type(None), bool))}
    cfg.update({"years": ctx["years"], "ghsl_epoch": ctx["epoch"], "grid": ctx["grid"].to_dict(),
                "nelson_layers": ctx["nelson_layers"]})
    (res / "config.json").write_text(json.dumps(cfg, indent=1, default=str))
    pd.DataFrame([{"highway": k, "speed_kmh": v[0], "paved_if_missing": v[1],
                   "unpaved_speed_kmh": v[0] * (1 if v[1] else UNPAVED_FACTOR)}
                  for k, v in SPEED_TABLE.items()]).to_csv(res / "speed_table.csv", index=False)
    pd.DataFrame([{"worldcover_class": k, "walking_speed_kmh_flat": v}
                  for k, v in LANDCOVER_SPEED.items()]).to_csv(res / "landcover_speed.csv", index=False)
    for f in ["osm2015_completeness_tiles.csv", "road_km_by_extract.csv", "destinations.csv", "tt_timings.csv", "osm_plan.json",
              "countries.csv", "grids_info.json", "roads_info.json"] + \
             [f"corruption_{y}.csv" for y in ctx["years"]] + \
             [f"checkpoints_{y}.csv" for y in ctx["years"]] + \
             [f"friction_{y}.json" for y in ctx["years"]] + \
             [f"settlements_{e}.csv" for e in sorted(set(ctx["epoch"].values()))]:
        if (work / f).exists():
            shutil.copy(work / f, res / f)
    if (dl / "nelson" / "article.json").exists():
        art = json.loads((dl / "nelson" / "article.json").read_text())
        (res / "nelson2019_figshare.json").write_text(json.dumps(
            {k: art.get(k) for k in ("title", "doi", "version", "published_date", "modified_date",
                                     "license")} | {"files": [{"name": f["name"], "md5": f.get(
                                         "computed_md5"), "bytes": f["size"]} for f in art["files"]]},
            indent=1, default=str))
    if (work / "african_borders.gpkg").exists():
        shutil.copy(work / "african_borders.gpkg", res / "african_borders.gpkg")
    man = pd.DataFrame(MANIFEST)
    prev = res / "inputs_manifest.csv"
    if prev.exists() and prev.stat().st_size > 1:     # resumed runs add to the earlier manifest
        man = pd.concat([pd.read_csv(prev), man])
    if len(man):
        man.drop_duplicates(["url", "file"], keep="last").to_csv(prev, index=False)
    versions = {"script": f"global_accessibility_v2.py {__version__}",
                "python": sys.version, "platform": platform.platform(),
                **{m: importlib.metadata.version(p) for m, (p, _) in REQUIRED.items()},
                "gdal": rasterio.__gdal_version__, "cpus": cpu_count(),
                "available_memory_gb": round(available_memory() / 1e9, 1)}
    (res / "software_versions.json").write_text(json.dumps(versions, indent=1))
    pd.DataFrame(Timer.rows).to_csv(res / "timings.csv", index=False)
    (res / "run_log.txt").write_text("\n".join(LOG) + "\n")


# =============================================================================
# stage: comparison with Nelson et al. (2019)
# =============================================================================
def relative_stats(acc, a, b):
    """Differences relative to Nelson et al. (reference), in %.

    rel_bias / rel_mad: ratio of sums, sum(ours - Nelson) / sum(Nelson) and
    sum(|ours - Nelson|) / sum(Nelson), i.e. mean difference / Nelson mean (area-weighted,
    one weight per cell) and the same with population weights (pw_). Ratios of sums stay
    defined where Nelson is ~0 min (cells inside cities). median_pct_diff /
    median_abs_pct_diff: per-cell 100 (ours - Nelson) / Nelson over cells with Nelson > 0
    (the statistic Nelson et al. 2019 used against Google Maps), from the random sample.
    """
    pct = lambda x, ref: 100 * x / ref if ref > 0 else np.nan
    k = b > 0
    r = 100 * (a[k] - b[k]) / b[k]
    return {"nelson_mean_min": acc["sum_n"] / acc["n"],
            "rel_bias_pct": pct(acc["sum_d"], acc["sum_n"]),
            "rel_mad_pct": pct(acc["sum_ad"], acc["sum_n"]),
            "pw_rel_bias_pct": pct(acc["pwo"] - acc["pwn"], acc["pwn"]),
            "pw_rel_mad_pct": pct(acc["pwad"], acc["pwn"]),
            "median_pct_diff": float(np.median(r)) if r.size else np.nan,
            "median_abs_pct_diff": float(np.median(np.abs(r))) if r.size else np.nan,
            "pct_sample_cells": int(r.size)}


def stage_compare(ctx):
    if not NELSON_COMPARE:
        return
    grid, work, res, dl = ctx["grid"], ctx["work"], ctx["results"], ctx["dl"]
    out = res / "nelson_comparison"; out.mkdir(parents=True, exist_ok=True)
    y0, y1 = ctx["years"][0], ctx["years"][-1]
    rng = np.random.default_rng(0)
    rows, cont_rows = [], []
    cg = memmap(work / "countries.npy", grid, None, mode="r")
    ct = pd.read_csv(work / "countries.csv").set_index("cid")
    for name in ctx["nelson_layers"]:
        f = dl / "nelson" / f"travel_time_to_{name}.tif"
        if not f.exists():
            continue
        with rasterio.open(f) as src:
            win = from_bounds(*grid.bounds, src.transform).round_offsets().round_lengths()
            nel = src.read(1, window=win, boundless=True, fill_value=65535)[:grid.height, :grid.width]
        tiles_f = work / "osm2015_completeness_tiles.csv"
        subsets = ["all"]
        if tiles_f.exists():
            tl = pd.read_csv(tiles_f)
            T = int(round(COMPLETE_TILE_DEG / grid.res))
            okmask = np.zeros((int(tl.tile_row.max()) + 1, int(tl.tile_col.max()) + 1), bool)
            okmask[tl.tile_row, tl.tile_col] = tl.osm2015_complete.values
            subsets.append("osm2015_complete_tiles")
        for y, subset in [(yy, ss) for yy in (y0, y1) for ss in subsets]:
            ours = np.load(work / "tt" / f"tt_{y}_{name}.npy", mmap_mode="r")
            pop = memmap(work / f"population_{ctx['epoch'][y]}.npy", grid, None, mode="r")
            acc = {"n": 0, "sum_d": 0.0, "sum_ad": 0.0, "le30": 0, "sx": 0.0, "sy": 0.0,
                   "sxx": 0.0, "syy": 0.0, "sxy": 0.0, "pw": 0.0, "pwo": 0.0, "pwn": 0.0,
                   "sum_n": 0.0, "pwad": 0.0}
            samp_o, samp_n = [], []
            cw = {}
            for r0, r1 in row_chunks(grid.height):
                o = np.asarray(ours[r0:r1], np.float64); nn = nel[r0:r1].astype(np.float64)
                ok = np.isfinite(o) & (nn != 65535)
                if subset != "all":
                    ok &= okmask[(np.arange(r0, r1) // T)[:, None], (np.arange(grid.width) // T)[None, :]]
                if not ok.any():
                    continue
                a, b = o[ok], nn[ok]; d = a - b
                p = np.asarray(pop[r0:r1], np.float64)[ok]
                acc["n"] += a.size; acc["sum_d"] += d.sum(); acc["sum_ad"] += np.abs(d).sum()
                acc["sum_n"] += b.sum(); acc["pwad"] += (p * np.abs(d)).sum()
                acc["le30"] += int((np.abs(d) <= 30).sum())
                la, lb = np.log1p(a), np.log1p(b)
                acc["sx"] += la.sum(); acc["sy"] += lb.sum(); acc["sxx"] += (la * la).sum()
                acc["syy"] += (lb * lb).sum(); acc["sxy"] += (la * lb).sum()
                acc["pw"] += p.sum(); acc["pwo"] += (p * a).sum(); acc["pwn"] += (p * b).sum()
                k = rng.random(a.size) < min(1.0, 2e6 / max(grid.size, 1))
                samp_o.append(a[k]); samp_n.append(b[k])
                c = np.asarray(cg[r0:r1])[ok]
                for key, arr in (("pw", p), ("pwo", p * a), ("pwn", p * b)):
                    cw.setdefault(key, []).append(np.bincount(c, arr, int(ct.index.max()) + 1))
            if acc["n"] == 0:          # e.g. no tile where OSM 2015 was complete
                rows.append({"layer": name, "our_year": y, "nelson_year": 2015, "subset": subset,
                             "cells": 0})
                continue
            n = acc["n"]
            cov = acc["sxy"] / n - acc["sx"] * acc["sy"] / n ** 2
            r_log = cov / math.sqrt(max((acc["sxx"] / n - (acc["sx"] / n) ** 2) *
                                        (acc["syy"] / n - (acc["sy"] / n) ** 2), 1e-12))
            rows.append({"layer": name, "our_year": y, "nelson_year": 2015, "subset": subset,
                         "cells": acc["n"],
                         "mean_diff_min": acc["sum_d"] / n, "mean_abs_diff_min": acc["sum_ad"] / n,
                         "share_within_30min": acc["le30"] / n, "pearson_r_log1p": r_log,
                         "pop_weighted_ours_min": acc["pwo"] / max(acc["pw"], 1),
                         "pop_weighted_nelson_min": acc["pwn"] / max(acc["pw"], 1),
                         **relative_stats(acc, np.concatenate(samp_o), np.concatenate(samp_n))})
            if cw:
                tot = {k: np.sum(v, axis=0) for k, v in cw.items()}
                df = pd.DataFrame({"cid": np.arange(len(tot["pw"])), **tot})
                df = df[df.pw > 0].join(ct[["iso3", "CONTINENT"]], on="cid")
                g = df.groupby("CONTINENT")[["pw", "pwo", "pwn"]].sum()
                for cont, rr in g.iterrows():
                    cont_rows.append({"layer": name, "our_year": y, "subset": subset, "continent": cont,
                                      "pop_weighted_ours_min": rr.pwo / rr.pw,
                                      "pop_weighted_nelson_min": rr.pwn / rr.pw})
            if name in (HEADLINE_LAYER, "ports_5") and samp_o and subset == subsets[-1]:
                a, b = np.concatenate(samp_o), np.concatenate(samp_n)
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.hexbin(np.log1p(b), np.log1p(a), gridsize=80, bins="log", cmap="Blues", mincnt=1)
                lim = [0, max(np.log1p(a).max(), np.log1p(b).max())]
                ax.plot(lim, lim, color="#52514e", lw=0.8)
                t = [0, 15, 60, 240, 960, 3840]
                ax.set_xticks(np.log1p(t), t); ax.set_yticks(np.log1p(t), t)
                ax.set_xlabel("Nelson et al. 2019 (2015), minutes"); ax.set_ylabel(f"this study ({y}), minutes")
                ax.set_title(f"{name} ({subset}): {len(a):,} sampled cells")
                fig.savefig(out / f"scatter_{name}_{y}_{subset}.png", dpi=130, bbox_inches="tight"); plt.close(fig)
        if name in (HEADLINE_LAYER, "ports_5"):
            f10 = LIGHT_FACTOR
            o = np.load(work / "tt" / f"tt_{y0}_{name}.npy", mmap_mode="r")
            d = np.full((grid.height // f10, grid.width // f10), CHANGE_NODATA, np.float64)
            for r0, r1 in row_chunks(grid.height - grid.height % f10, 2000 - 2000 % f10):
                a = np.asarray(o[r0:r1], np.float64); b = nel[r0:r1].astype(np.float64)
                x = np.where(np.isfinite(a) & (b != 65535), a - b, CHANGE_NODATA)
                d[r0 // f10:r1 // f10] = block_mean(x, f10, CHANGE_NODATA)
            png_map(out / f"difference_{name}_{y0}_minus_nelson2015.png", d, CHANGE_NODATA,
                    f"{name}: this study ({y0}) - Nelson et al. 2019 (2015), minutes "
                    "(blue = shorter here)", "change",
                    [grid.west, grid.east, grid.south, grid.north])
    pd.DataFrame(rows).to_csv(out / "comparison_by_layer.csv", index=False)
    pd.DataFrame(cont_rows).to_csv(out / "comparison_by_continent.csv", index=False)
    if (dl / "nelson" / "README.txt").exists():
        shutil.copy(dl / "nelson" / "README.txt", out / "nelson2019_README.txt")
    log(f"Nelson comparison: {len(rows)} rows")


# =============================================================================
# stage: validation of the end year against OSRM (free routing engine, OSM car profile)
# =============================================================================
def great_circle_km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R_EARTH / 1000 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


class RateLimited:
    """OSRM table requests, one per ROUTING_MIN_INTERVAL_S, trying each server in turn."""

    def __init__(self):
        self.sess, self.last, self.bad = session(), 0.0, set()

    def table(self, coords, n_src):
        q = ";".join(f"{x:.6f},{y:.6f}" for x, y in coords)
        params = {"sources": ";".join(map(str, range(n_src))),
                  "destinations": str(n_src), "annotations": "duration,distance"}
        for srv in ROUTING_SERVERS:
            if srv in self.bad:
                continue
            wait = self.last + ROUTING_MIN_INTERVAL_S - time.time()
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            try:
                r = self.sess.get(f"{srv}/table/v1/{ROUTING_PROFILE}/{q}", params=params, timeout=60)
                if r.status_code == 429:
                    time.sleep(30)
                    continue
                j = r.json()
                if j.get("code") == "Ok":
                    return j, srv
                log(f"routing {srv}: {j.get('code')} {j.get('message', '')[:80]}")
            except Exception as e:
                log(f"routing {srv} failed: {e!r}")
                self.bad.add(srv) if "Connection" in repr(e) else None
        return None, None


def stage_validate(ctx):
    if not ROUTING_VALIDATION:
        return
    grid, work, res = ctx["grid"], ctx["work"], ctx["results"] / "routing_validation"
    res.mkdir(parents=True, exist_ok=True)
    y = ctx["years"][-1]
    e = ctx["epoch"][y]
    fr = memmap(work / f"friction_{y}.npy", grid, None, mode="r")
    pop = memmap(work / f"population_{e}.npy", grid, None, mode="r")
    cg = memmap(work / "countries.npy", grid, None, mode="r")
    ct = pd.read_csv(work / "countries.csv").set_index("cid")
    st = pd.read_csv(work / f"settlements_{e}.csv")
    st = st[(st.population >= ROUTING_MIN_POP) & st.lon.between(grid.west, grid.east)
            & st.lat.between(grid.south, grid.north)].copy()
    st["row"] = ((grid.north - st.lat) / grid.res).astype(int)
    st["col"] = ((st.lon - grid.west) / grid.res).astype(int)
    st["continent"] = [ct.CONTINENT.get(int(cg[r, c]), "none") for r, c in zip(st.row, st.col)]
    rng = np.random.default_rng(42)
    # stratified by continent, proportional to sqrt(number of cities), at least 5 each
    counts = st.continent.value_counts()
    alloc = np.maximum(5, np.round(ROUTING_CITIES * np.sqrt(counts) / np.sqrt(counts).sum()))
    parts = [g.sample(min(len(g), int(alloc[c])), random_state=1) for c, g in st.groupby("continent")]
    cities = pd.concat(parts).head(ROUTING_CITIES) if parts else st.head(0)
    log(f"routing validation: {len(cities)} cities, up to {ROUTING_ORIGINS_PER_CITY} origins each, "
        f"~{len(cities) * ROUTING_MIN_INTERVAL_S / 60:.0f} min at 1 request/s")
    warm_up_numba()
    osrm, rows = RateLimited(), []
    rmax = ROUTING_RADIUS_KM[1] * 1.1
    for _, cty in cities.iterrows():
        dlat = rmax / 111.2
        dlon = rmax / (111.2 * max(math.cos(math.radians(cty.lat)), 0.05))
        w = grid.window_of((cty.lon - dlon, cty.lat - dlat, cty.lon + dlon, cty.lat + dlat))
        if not w:
            continue
        r0, c0, nr, nc = w
        sub = grid.subgrid(r0, c0, nr, nc)
        f = np.array(fr[r0:r0 + nr, c0:c0 + nc])
        pr, pc = port_cells(pd.DataFrame({"Longitude": [cty.lon], "Latitude": [cty.lat]}), sub, f)
        if pr[0] < 0:
            continue
        t = travel_time(f, [int(pr[0]) * sub.width + int(pc[0])], sub)
        p = np.array(pop[r0:r0 + nr, c0:c0 + nc], np.float64)
        rr, cc = np.nonzero(np.isfinite(t) & (p > 1))
        if not len(rr):
            continue
        lon = sub.west + (cc + 0.5) * sub.res; lat = sub.north - (rr + 0.5) * sub.res
        d = great_circle_km(lon, lat, cty.lon, cty.lat)
        keep = (d >= ROUTING_RADIUS_KM[0]) & (d <= ROUTING_RADIUS_KM[1])
        if keep.sum() == 0:
            continue
        idx = np.flatnonzero(keep)
        w_ = p[rr[idx], cc[idx]]
        pick = rng.choice(idx, size=min(ROUTING_ORIGINS_PER_CITY, len(idx)), replace=False,
                          p=w_ / w_.sum())
        coords = [(lon[i], lat[i]) for i in pick] + [(cty.lon, cty.lat)]
        j, srv = osrm.table(coords, len(pick))
        if j is None:
            continue
        for k, i in enumerate(pick):
            dur = j["durations"][k][0]
            dist = (j.get("distances") or [[None]])[k][0] if j.get("distances") else None
            rows.append({"settlement_id": int(cty.settlement_id), "population": cty.population,
                         "continent": cty.continent, "city_lon": cty.lon, "city_lat": cty.lat,
                         "origin_lon": round(float(lon[i]), 5), "origin_lat": round(float(lat[i]), 5),
                         "great_circle_km": round(float(d[i]), 2),
                         "ours_min": round(float(t[rr[i], cc[i]]), 1),
                         "osrm_min": None if dur is None else round(dur / 60, 1),
                         "osrm_km": None if dist is None else round(dist / 1000, 2),
                         "snap_origin_m": round(j["sources"][k].get("distance", np.nan), 1),
                         "snap_city_m": round(j["destinations"][0].get("distance", np.nan), 1),
                         "server": srv})
    df = pd.DataFrame(rows)
    df.to_csv(res / f"pairs_{y}.csv", index=False)
    if df.empty:
        log("routing validation: no pairs (servers unreachable?)")
        return
    ok = df.osrm_min.notna() & (df.snap_origin_m <= ROUTING_MAX_SNAP_M) & \
        (df.snap_city_m <= ROUTING_MAX_SNAP_M) & (df.osrm_min > 0)
    v = df[ok]

    def stats(g):
        a, b = g.ours_min.values, g.osrm_min.values
        return pd.Series({"pairs": len(g), "median_ours_min": np.median(a),
                          "median_osrm_min": np.median(b),
                          "median_ratio_ours_over_osrm": np.median(a / b),
                          "median_diff_min": np.median(a - b), "mean_abs_diff_min": np.mean(np.abs(a - b)),
                          "share_within_30pct": np.mean(np.abs(a / b - 1) <= 0.3),
                          "pearson_r_log": np.corrcoef(np.log1p(a), np.log1p(b))[0, 1] if len(g) > 2 else np.nan})
    summ = pd.concat([stats(v).to_frame("all").T,
                      v.groupby("continent").apply(stats, include_groups=False)])
    summ.index.name = "group"
    summ.to_csv(res / f"summary_{y}.csv")
    fig, ax = plt.subplots(figsize=(6, 6))
    for i, (c, g) in enumerate(v.groupby("continent")):
        ax.scatter(g.osrm_min, g.ours_min, s=8, alpha=0.6, label=c,
                   color=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300",
                          "#4a3aa7", "#e34948"][i % 8])
    lim = [1, max(v.osrm_min.max(), v.ours_min.max()) * 1.1]
    ax.plot(lim, lim, color="#52514e", lw=0.8)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel(f"OSRM car, free flow (minutes)"); ax.set_ylabel(f"this study, {y} (minutes)")
    ax.set_title(f"{len(v)} origin-city pairs"); ax.legend(fontsize=7, frameon=False)
    fig.savefig(res / f"scatter_{y}.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    (res / "ATTRIBUTION.txt").write_text(
        "Reference travel times: OSRM (Project OSRM demo server and/or FOSSGIS routing.openstreetmap.de),\n"
        "car profile, routing data (c) OpenStreetMap contributors, ODbL. Fix the map: "
        "https://www.openstreetmap.org/fixthemap\n")
    log(f"routing validation: {len(v)} valid pairs of {len(df)}; median ratio ours/OSRM "
        f"{summ.loc['all', 'median_ratio_ours_over_osrm']:.2f}")


# =============================================================================
# stage: sensitivity of the results to K and to the border delay
# =============================================================================
def sens_scenarios():
    if SENS_DESIGN == "full":
        sc = [(k, d) for k in SENS_K for d in SENS_DELAY_MIN]
    else:
        sc = [(k, BORDER_DELAY_MIN) for k in SENS_K] + [(CORRUPTION_K, d) for d in SENS_DELAY_MIN]
    sc.append((CORRUPTION_K, BORDER_DELAY_MIN))
    out = []
    for k, d in sc:
        if (float(k), float(d)) not in out:
            out.append((float(k), float(d)))
    return out


def pw_by_country(ctx, y, tt_path):
    """Population-weighted sums of travel time per country id (0 = no country)."""
    grid, work = ctx["grid"], ctx["work"]
    cg = memmap(work / "countries.npy", grid, None, mode="r")
    pop = memmap(work / f"population_{ctx['epoch'][y]}.npy", grid, None, mode="r")
    mm = np.load(tt_path, mmap_mode="r")
    n = int(np.asarray(cg).max()) + 1
    w = np.zeros(n); wt = np.zeros(n); w60 = np.zeros(n)
    for r0, r1 in row_chunks(grid.height):
        t = np.asarray(mm[r0:r1]).ravel(); p = np.asarray(pop[r0:r1]).ravel().astype(np.float64)
        c = np.asarray(cg[r0:r1]).ravel().astype(np.int64)
        ok = np.isfinite(t)
        w += np.bincount(c[ok], p[ok], n); wt += np.bincount(c[ok], p[ok] * t[ok], n)
        w60 += np.bincount(c[ok & (t <= 60)], p[ok & (t <= 60)], n)
    return pd.DataFrame({"cid": np.arange(n), "pop": w, "pop_x_tt": wt, "pop_le60": w60})


def stage_sensitivity(ctx):
    if not SENSITIVITY:
        return
    grid, work = ctx["grid"], ctx["work"]
    res = ctx["results"] / "sensitivity"
    res.mkdir(parents=True, exist_ok=True)
    sdir = work / "sens"
    sdir.mkdir(exist_ok=True)
    base = (float(CORRUPTION_K), float(BORDER_DELAY_MIN))
    scen = sens_scenarios()
    layers = [l for l in SENS_LAYERS if l in layer_names()]
    tag = lambda k, d: f"K{k:.2f}_D{d:g}"
    log(f"sensitivity: {len(scen)} scenarios ({SENS_DESIGN}) x {len(ctx['years'])} years x "
        f"{len(layers)} layers; baseline K={base[0]}, delay={base[1]} min")
    jobs = []
    for k, d in scen:
        for y in ctx["years"]:
            if (k, d) == base:
                continue
            fpath = sdir / f"friction_{y}_{tag(k, d)}.npy"
            if not fpath.exists():
                friction_from_parts(ctx, y, k, d, fpath)
            for name in layers:
                jobs.append({"grid": grid.to_dict(), "friction": str(fpath),
                             "sources": str(work / "tt" / f"sources_{y}_{name}.npy"),
                             "out": str(sdir / f"tt_{y}_{name}_{tag(k, d)}.npy"),
                             "year": y, "layer": name})
    warm_up_numba()
    per_task = grid.size * (4 + 4 + 2) + 0.3e9
    run_budgeted(tt_job, jobs, lambda j: per_task, "sensitivity travel time")

    ct = pd.read_csv(work / "countries.csv")
    rows = []
    for k, d in scen:
        for y in ctx["years"]:
            for name in layers:
                f = work / "tt" / f"tt_{y}_{name}.npy" if (k, d) == base else \
                    sdir / f"tt_{y}_{name}_{tag(k, d)}.npy"
                df = pw_by_country(ctx, y, f).merge(ct[["cid", "iso3", "NAME", "CONTINENT"]],
                                                    on="cid", how="left")
                df["iso3"] = df["iso3"].fillna("none"); df["CONTINENT"] = df["CONTINENT"].fillna("none")
                df = df.assign(K=k, delay_min=d, year=y, layer=name, baseline=(k, d) == base)
                rows.append(df)
    d = pd.concat(rows)

    def agg(g):
        return pd.Series({"population": g["pop"].sum(),
                          "pop_weighted_mean_min": g["pop_x_tt"].sum() / max(g["pop"].sum(), 1),
                          "share_within_60min": g["pop_le60"].sum() / max(g["pop"].sum(), 1)})
    keys = ["K", "delay_min", "baseline", "layer", "year"]
    out = {"domain": d.groupby(keys).apply(agg, include_groups=False).reset_index(),
           "continent": d.groupby(keys + ["CONTINENT"]).apply(agg, include_groups=False).reset_index(),
           "country": d[d.cid > 0].groupby(keys + ["iso3", "NAME", "CONTINENT"]).apply(agg, include_groups=False).reset_index()}
    ctry = out["country"]
    has_pop = ctry.groupby("iso3")["population"].transform("min") > 0      # drop countries outside the grid
    out["country"] = ctry[has_pop]
    y0, y1 = ctx["years"][0], ctx["years"][-1]
    for level, t in out.items():
        idx = [c for c in t.columns if c not in ("year", "population", "pop_weighted_mean_min",
                                                 "share_within_60min")]
        wide = t.pivot_table(index=idx, columns="year", values="pop_weighted_mean_min").reset_index()
        wide.columns = [f"mean_min_{c}" if isinstance(c, (int, np.integer)) else c for c in wide.columns]
        wide[f"change_{y1}_minus_{y0}_min"] = wide[f"mean_min_{y1}"] - wide[f"mean_min_{y0}"]
        bkeys = [c for c in idx if c not in ("K", "delay_min", "baseline")]
        b = wide[wide.baseline].set_index(bkeys)
        for c in (f"mean_min_{y0}", f"mean_min_{y1}", f"change_{y1}_minus_{y0}_min"):
            wide[c + "_vs_baseline"] = wide[c].values - b.loc[[tuple(r) if len(bkeys) > 1 else r[0]
                                                               for r in wide[bkeys].values], c].values
        t.to_csv(res / f"sensitivity_{level}_long.csv", index=False)
        wide.to_csv(res / f"sensitivity_{level}.csv", index=False)
    pd.DataFrame(scen, columns=["K", "delay_min"]).assign(
        baseline=lambda x: (x.K == base[0]) & (x.delay_min == base[1])).to_csv(res / "scenarios.csv", index=False)

    # figure: domain-level mean travel time against K (delay at baseline) and against
    # the delay (K at baseline), both years, per layer
    dom = out["domain"]
    fig, axes = plt.subplots(len(layers), 2, figsize=(9, 3.2 * len(layers)), squeeze=False,
                             constrained_layout=True, sharey="row")      # same scale: K vs delay comparable
    colors = {y0: "#2a78d6", y1: "#eb6834"}
    for i, name in enumerate(layers):
        for j, (var, fixed, fixval, lab) in enumerate(
                [("K", "delay_min", base[1], "governance factor K"),
                 ("delay_min", "K", base[0], "border delay (minutes)")]):
            ax = axes[i][j]
            sub = dom[(dom.layer == name) & np.isclose(dom[fixed], fixval)].sort_values(var)
            for y in (y0, y1):
                s_ = sub[sub.year == y]
                ax.plot(s_[var], s_.pop_weighted_mean_min, marker="o", ms=5, lw=2,
                        color=colors[y], label=str(y))
            ax.axvline(base[j], color="#9a9a96", lw=0.8, ls="--")
            ax.set_xlabel(lab); ax.set_ylabel(f"{name}: mean travel time (min)")
            ax.grid(color="#e6e6e3", lw=0.5); ax.spines[["top", "right"]].set_visible(False)
            if i == 0 and j == 0:
                ax.legend(frameon=False)
    fig.savefig(res / "sensitivity.png", dpi=160); plt.close(fig)
    for f in sdir.glob("*.npy"):       # scenario grids are large and no longer needed
        f.unlink()
    log(f"sensitivity: {len(scen)} scenarios summarised in {res}")


# =============================================================================
# cleanup, planning, main
# =============================================================================
def stage_cleanup(ctx):
    write_methods(ctx)
    if not CLEANUP:
        log("cleanup skipped (CLEANUP = False)")
        return
    work = ctx["work"]
    pending = [s for s in STAGES if s != "cleanup" and not (work / "_done" / s).exists()]
    if pending:
        log(f"cleanup skipped: stages {pending} have not completed, so downloads and intermediate "
            f"files are kept in {work} and a rerun resumes from them")
        return
    for p in work.iterdir():
        if KEEP_DOWNLOADS and p.name in ("downloads", "pylib"):
            continue
        if p.name == "pylib":        # keep installed packages for the next run
            continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    log(f"intermediate files removed from {work}")


def dry_run(ctx):
    grid = ctx["grid"]
    n_tasks = len(ctx["years"]) * len(layer_names())
    if SENSITIVITY:
        n_sens = (len(sens_scenarios()) - 1) * len(ctx["years"]) * len(SENS_LAYERS)
        log(f"sensitivity: {len(sens_scenarios())} scenarios ({SENS_DESIGN}) -> {n_sens} extra "
            f"travel-time tasks and {(len(sens_scenarios()) - 1) * len(ctx['years'])} extra friction grids "
            f"(~{grid.size * 4 / 1e9:.1f} GB each, deleted after use)")
    per_task = grid.size * 10 + 0.3e9
    n, budget = plan_workers(per_task, n_tasks)
    shared = grid.size * (4 * 3 + 1 * 3 + 2)
    log(f"grid {grid.width} x {grid.height} = {grid.size / 1e6:.0f} M cells ({grid.res * 3600:.0f}\")")
    log(f"cpus {cpu_count()}, available memory {available_memory() / 1e9:.0f} GB, "
        f"planning budget {budget / 1e9:.0f} GB")
    log(f"travel time: {n_tasks} tasks x ~{per_task / 1e9:.1f} GB -> {n} parallel workers")
    log(f"shared grids on disk (memory-mapped): ~{shared / 1e9:.0f} GB; per-year friction "
        f"{grid.size * 4 / 1e9:.1f} GB")
    log(f"disk for results: ~{grid.size * (2 * 17 * 2 + 4 * 2) / 3 / 1e9:.0f} GB (compressed estimate)")
    if NETWORK_CHECK:
        network_check(ctx, session())
    plan = geofabrik_plan(ctx["work"], grid, ctx["years"], session())
    for y, rs in plan.items():
        big = sorted(rs, key=lambda r: -r["bytes"])[:3]
        log(f"OSM {y}: largest extracts {[(r['region'], round(r['bytes'] / 1e9, 2)) for r in big]}")


STAGES = ["download", "grids", "roads", "friction", "traveltime", "outputs", "compare",
          "validate", "sensitivity", "cleanup"]


def nearest_epoch(y):
    return min(GHSL_EPOCHS, key=lambda e: (abs(e - y), -e))


def main(argv=None):
    global START_YEAR, END_YEAR, BBOX, CLEANUP, ML_FILES, NELSON_LAYERS, MAX_WORKERS, INCLUDE_ML_ROADS, WEISS2015_AUGMENT
    global NETWORK_CHECK, ROUTING_CITIES, ROUTING_VALIDATION, SENSITIVITY, SENS_DESIGN
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=int, default=START_YEAR)
    p.add_argument("--end", type=int, default=END_YEAR)
    p.add_argument("--bbox", type=float, nargs=4, metavar=("W", "S", "E", "N"), default=BBOX)
    p.add_argument("--work-dir", default=WORK_DIR)
    p.add_argument("--results-dir", default=RESULTS_DIR)
    p.add_argument("--stages", default=",".join(STAGES))
    p.add_argument("--ml-files", nargs="+", default=ML_FILES)
    p.add_argument("--no-ml", action="store_true")
    p.add_argument("--no-weiss", action="store_true", help="do not complete 2015 roads with Weiss et al. (2018)")
    p.add_argument("--skip-network-check", action="store_true", help="do not test the download servers first")
    p.add_argument("--nelson-layers", nargs="+", default=NELSON_LAYERS)
    p.add_argument("--max-workers", type=int, default=MAX_WORKERS)
    p.add_argument("--no-cleanup", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--routing-cities", type=int, default=ROUTING_CITIES)
    p.add_argument("--no-routing", action="store_true")
    p.add_argument("--no-sensitivity", action="store_true")
    p.add_argument("--sens-design", choices=["oat", "full"], default=SENS_DESIGN)
    a = p.parse_args(argv)
    START_YEAR, END_YEAR, BBOX = a.start, a.end, a.bbox
    ML_FILES, NELSON_LAYERS, MAX_WORKERS = a.ml_files, a.nelson_layers, a.max_workers
    CLEANUP = CLEANUP and not a.no_cleanup
    INCLUDE_ML_ROADS = INCLUDE_ML_ROADS and not a.no_ml
    WEISS2015_AUGMENT = WEISS2015_AUGMENT and not a.no_weiss
    NETWORK_CHECK = NETWORK_CHECK and not a.skip_network_check
    ROUTING_CITIES, ROUTING_VALIDATION = a.routing_cities, ROUTING_VALIDATION and not a.no_routing
    SENSITIVITY, SENS_DESIGN = SENSITIVITY and not a.no_sensitivity, a.sens_design
    if END_YEAR <= START_YEAR:
        raise SystemExit("END_YEAR must be after START_YEAR")
    work, res = Path(a.work_dir).resolve(), Path(a.results_dir).resolve()
    work.mkdir(parents=True, exist_ok=True); res.mkdir(parents=True, exist_ok=True)
    grid = Grid(tuple(BBOX) if BBOX else NELSON_EXTENT, RES_ARCSEC / 3600)
    years = [START_YEAR, END_YEAR]
    ctx = {"work": work, "dl": work / "downloads", "results": res, "grid": grid, "years": years,
           "epoch": {y: nearest_epoch(y) for y in years},
           "nelson_layers": NELSON_LAYERS or layer_names()}
    log(f"global_accessibility v{__version__}: years {years}, GHSL epochs {ctx['epoch']}, grid {grid.to_dict()}")
    log(f"cpus {cpu_count()}, available memory {available_memory() / 1e9:.0f} GB")
    if a.dry_run:
        dry_run(ctx)
        return
    done_dir = work / "_done"; done_dir.mkdir(exist_ok=True)
    want = [s.strip() for s in a.stages.split(",") if s.strip()]
    funcs = {"download": stage_download, "grids": stage_grids, "roads": stage_roads,
             "friction": stage_friction, "traveltime": stage_traveltime,
             "outputs": stage_outputs, "compare": stage_compare, "validate": stage_validate, "sensitivity": stage_sensitivity,
             "cleanup": stage_cleanup}
    for s in STAGES:
        if s not in want:
            continue
        marker = done_dir / s
        if marker.exists() and s != "cleanup":
            log(f"stage {s}: already done (delete {marker} to redo)")
            continue
        with Timer(f"stage {s}"):
            try:
                funcs[s](ctx)
            except RemoteUnavailable as e:
                log(traceback.format_exc())
                write_methods(ctx)
                raise SystemExit(f"stage {s} stopped: a server kept failing ({e}). Nothing was deleted; "
                                 "rerun later to resume.") from None
            except Exception:
                log(traceback.format_exc())
                write_methods(ctx)
                raise
        if s != "cleanup":
            marker.write_text(dt.datetime.now().isoformat())
            write_methods(ctx)
    write_methods(ctx) if "cleanup" not in want else None
    log("finished")


if __name__ == "__main__":
    main()
