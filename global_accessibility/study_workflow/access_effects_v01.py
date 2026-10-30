#!/usr/bin/env python3
"""
access_effects_v01.py - data pipeline of the study "accessibility change, land-use change and
crop yields in Sub-Saharan Africa" (study_design/Study_design_access_landuse_yields.md)
==========================================================================================

Builds every analysis table of the study design from the travel-time store written by
global_accessibility_v3.py (one or more runs) and from open land-use, yield and covariate data,
then runs the estimation script (estimate_effects.R) and evaluates the gates.

Stand-alone script (Python >= 3.11), same conventions as global_accessibility_v3.py: it installs
missing Python packages into WORK_DIR/pylib, every stage is resumable, a dry run prints the plan,
and --check-access tests every server first. Run it from the JupyterLab terminal:
    python access_effects_v01.py --check-access     # every server reachable?
    python access_effects_v01.py --dry-run          # inputs found, tiles, disk, memory
    python access_effects_v01.py                    # all stages (rerun the same command after a crash)
    python access_effects_v01.py --stages treatment,landuse

Stages (each resumes where it stopped; completed stages are skipped):
    treatment  access level, events and doses per 30" cell (Phase 0) from the travel-time store
    landuse    forest at baseline, annual tree-cover loss, cropland and conversion per cell (Phase 1)
    covariates rainfall, conflict, population, slope, land cover per cell and year
    projects   externally dated road projects (AidData GeoGCDF v3) as cells with completion years
    gate_t     Gate T per zone: share of access events inside mapping bursts, agreement with
               dated projects (imagery confirmation is not implemented: see the README)
    admin      admin-unit panel (HarvestStat) with cropland- and population-weighted treatment (E2a)
    lsms       LSMS-ISA enumeration-area panel (E2b) from the author's zip files (sources.csv)
    panels     analysis files: E1 cell-year panel (sampled), E2a, E2b, E3 long differences
    estimate   estimate_effects.R (staggered DiD, continuous dose, long differences, placebos)
    gate_c     Gate C table from the estimates; Benjamini-Hochberg across crops and outcomes

Unit of analysis for land use: the 30 arc-second cell of the travel-time grid (~0.93 km at the
equator; the design calls it the 0.01 degree cell). Work is split into 10 x 10 degree tiles.
"""
from __future__ import annotations

__version__ = "0.1.0"

# =============================================================================
# CONFIGURATION - edit here (command-line options override a few of these)
# =============================================================================
# --- inputs from global_accessibility_v3.py ------------------------------------------
GA_RESULTS = ["./ga_results"]   # one or more RESULTS_DIR of global_accessibility_v3.py. A year present in
                                # several runs is read from the first run listed (put the annual run first,
                                # the 2015/2020/2025 run second for the long-term level)
WORK_DIR = "./ae_work"          # downloads and intermediate files
RESULTS_DIR = "./ae_results"    # analysis tables, estimates, gates, logs (kept)
ANALYSIS_BBOX = (-18.0, -35.0, 52.0, 25.0)   # W, S, E, N: Sub-Saharan Africa and its margins
TILE_DEG = 10                   # work unit: 10 x 10 degree tiles aligned on multiples of 10 (as Hansen GFC)
SSA_EXCLUDE = {"DZA", "EGY", "LBY", "MAR", "TUN", "ESH", "SDN"}
                                # African countries outside Sub-Saharan Africa (UN M49 Northern Africa,
                                # recalled; Sudan is in Northern Africa in M49). Remove "SDN" to keep Sudan

# --- treatment (Phase 0; defaults approved 2026-10-27) --------------------------------
TREAT_LAYERS = ["cities_11", "cities_12", "ports_5"]   # cities_11 primary
TREAT_VERSIONS = ["roadonly", "total"]                 # road-only primary
EVENT_REL = 0.20                # access event: travel time falls by >= 20% ...
EVENT_ABS_MIN = 15.0            # ... and by >= 15 minutes, relative to the year before ...
EVENT_PERSIST_YEARS = 2         # ... and stays below that level for >= 2 years
TT_CAP_MIN = 2880.0             # travel times above 2 days (and unreachable cells) are set to 2 days
EVENT_YEAR_SHIFT = -1           # OSM cut on 1 January y shows roads mapped up to the end of y-1:
                                # the event year is y-1 (the "year the change was mapped")
BURST_WINDOW_KM = 10.0          # a cell's access event is attributed to the road changes within this
BURST_SHARE_PLACEBO = 0.5       # distance; >= 50% of them inside mapping bursts -> "burst" event (placebo)
BAND_TREATED_KM = 5.0           # spatial bands: treated within 5 km of a new or faster road cell of the
BAND_CONTROL_KM = (10.0, 30.0)  # event year; controls (never-treated) 10-30 km away; 5-10 km excluded
BAND_MAX_KM = 40.0              # distances are computed up to this (sensitivity 0-3 / 15-40 km)
LONG_EPOCHS = [(2015, 2020), (2020, 2025), (2015, 2025)]   # E3; a missing year uses the nearest one
                                                           # within LONG_EPOCH_TOL years
LONG_EPOCH_TOL = 1

# --- land use (Phase 1) -------------------------------------------------------------
HANSEN_VERSION = "GFC-2025-v1.13"   # Hansen/UMD Global Forest Change (loss 2001-2025; CC BY 4.0). v1.13 reprocessed
                                    # loss from 2011 on: check the series around 2011 (or use "GFC-2024-v1.12")
HANSEN_URL = "https://storage.googleapis.com/earthenginepartners-hansen/{v}/Hansen_{v}_{layer}_{tile}.tif"
HANSEN_LAST_LOSS = 25               # last loss year in the version (25 = 2025)
FOREST_THRESHOLD = 30               # forest = tree cover 2000 >= 30% (primary) ...
FOREST_THRESHOLD_ALT = 10           # ... and >= 10% (sensitivity)
CROPLAND_SOURCE = "gaced30"         # "gaced30": GACED30 annual 2000-2024, 30 m (Zenodo 10.5281/zenodo.18199675;
                                    #   CC BY 4.0), downloadable by script. "glad_annual": GLAD annual cropland
                                    #   2015-2024 (the design's primary), from local tiles in GLAD_ANNUAL_DIR/<year>/
                                    #   (no scriptable download was found: export from Earth Engine
                                    #   projects/glad/Cropland_Annual_2015_2024)
GACED30_URL = "https://zenodo.org/api/records/18199675/files/{name}/content"
GLAD_ANNUAL_DIR = None
CROPLAND_YEARS = range(2014, 2025)  # cropland years read (conversion needs the year before each loss year)
STABLE_CROP_FROM = 2015             # stable cropland = cropland in every year from 2015 (yield weights, design)
CONVERSION_WINDOW = 2               # conversion: loss in t, not cropland in t-1, cropland in one of t..t+2
LANDUSE_STRIP_ROWS = 1000           # Hansen rows read at a time (0.25 degree)
LANDUSE_TASK_GB = 6

# --- covariates -----------------------------------------------------------------------
COV_YEARS = list(range(2001, 2025))
CHIRPS_ANNUAL_URL = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/annual/africa/tifs/chirps-v3.0.{y}.tif"
RAIN_BASELINE = (2001, 2014)        # mean annual rainfall before the treatment window (matching)
CONFLICT_SOURCE = "ucdp"            # "ucdp": UCDP GED (open, CC BY 4.0). "acled": ACLED (credentials from the
                                    # environment variables ACLED_USERNAME / ACLED_PASSWORD; experimental: the
                                    # API paging and country names were not tested), UCDP GED if it fails
UCDP_GED_URL = "https://ucdp.uu.se/downloads/ged/ged261-csv.zip"
ACLED_TOKEN_URL = "https://acleddata.com/oauth/token"
ACLED_READ_URL = "https://acleddata.com/api/acled/read"
CONFLICT_BLOCK_DEG = 0.1            # conflict events counted per 0.1 degree block and year

# --- dated road projects and Gate T ----------------------------------------------------
GCDF_URL = ("https://github.com/aiddata/gcdf-geospatial-data/releases/download/v3.0.1/"
            "all_combined_global.gpkg.zip")
PROJECT_BUFFER_KM = 2.0             # cells within 2 km of a dated project geometry
GATE_T_DATE_TOL = 1                 # OSM event year within +-1 year of the project completion
GATE_T_MAX_BURST = 0.5              # Gate T: <= 50% of event cells inside mapping bursts (approved default)

# --- admin yields (E2a) ----------------------------------------------------------------
HARVESTSTAT_CSV_URL = ("https://raw.githubusercontent.com/HarvestStat/HarvestStat-Africa/main/public/"
                       "hvstat_africa_data_v1.2.csv")
HARVESTSTAT_GPKG_URL = ("https://raw.githubusercontent.com/HarvestStat/HarvestStat-Africa/main/public/"
                        "hvstat_africa_boundary_v1.2.gpkg")
ADMIN_WEIGHT = "cropland"           # unit treatment weighted by cropland ("population": alternative)

# --- LSMS-ISA enumeration areas (E2b) ---------------------------------------------------
LSMS_SOURCES = "./sources.csv"      # the author's registry (source_id, program, country, year, data_path, ...);
LSMS_DIR = "./lsms"                 # zip files are looked up by file name anywhere under LSMS_DIR (Windows paths
                                    # in sources.csv are not used)
LSMS_HP_URL = "https://zenodo.org/api/records/15774761/files/{f}/content"
                                    # LSMS-ISA harmonised panel v2.0 (Bentze & Wollburg; Zenodo says CC0, the paper
                                    # says CC BY-NC-ND 4.0: do not redistribute the files)
LSMS_WAVE_YEARS = {                 # harvest (agricultural) year of each panel wave: first calendar year of the survey.
    # INFERRED from the survey years of each country (not read from the panel documentation): check them
    "Ethiopia": {1: 2011, 2: 2013, 3: 2015, 4: 2018, 5: 2021},
    "Malawi": {1: 2010, 2: 2013, 3: 2016, 4: 2019},
    "Nigeria": {1: 2010, 2: 2012, 3: 2015, 4: 2018, 5: 2023},
    "Tanzania": {1: 2008, 2: 2010, 3: 2012, 4: 2014, 5: 2019},
    "Uganda": {1: 2009, 2: 2010, 3: 2011, 4: 2013, 5: 2015, 7: 2018, 8: 2019},
    "Niger": {1: 2011, 2: 2014},
    "Mali": {1: 2014, 2: 2017},
}
CROPMIX_MIN_REPORT = 2 / 3          # E2e admin: a crop is in a unit's fixed set if reported in >= 2/3 of its years
EA_RADIUS_KM = 5.0                  # EA treatment: cropland-weighted access of the cells within 5 km of the point
EA_MIN_HH = 5                       # EA x crop x season kept with >= 5 households ...
EA_MIN_PLOTS = 8                    # ... and >= 8 plots (approved defaults)

# --- panels and estimation ------------------------------------------------------------
PRIMARY_SPEC = "roadonly_cities_11"
ESTIMATE_SPECS = ["roadonly_cities_11", "total_cities_11", "roadonly_cities_12", "roadonly_ports_5"]
E1_FOREST_MIN_KM2 = 0.05            # E1 cells: >= 0.05 km2 of forest in 2000 (~6% of a cell)
E1_SAMPLE_TREATED = 150000          # sampled cells (stratified by tile, with sampling weights)
E1_SAMPLE_CONTROL = 150000
MATCH_SMD_MAX = 0.1                 # matching balance criterion (approved default)
EVENT_WINDOW = (-5, 5)
CONLEY_KM = 50
BH_Q = 0.10
BOOTSTRAP_ITERS = 999
MAX_UNITS_CS = 200000
COMPOSITE_SHIFT = 0.05             # revision 2 drafts (to approve): crop-share shift that labels yield/vigour
GATE_V_R = 0.3                     # results "composite"; Gate V within-unit anomaly correlation, minimum
GATE_V_MIN_N = 30                  # unit-seasons per zone, and MODIS-HLS season-metric correlation
GATE_V_R_SENSOR = 0.8
RSCRIPT = "Rscript"                 # or the full path of Rscript

# --- resources (None = detect) --------------------------------------------------
MAX_WORKERS = None
MEMORY_FRACTION = 0.6
DOWNLOAD_WORKERS = 4
USER_AGENT = "access-effects-workflow/0.1 (research use)"
SEED = 20261028                 # every random draw (samples, placebo roads) uses this seed

# =============================================================================
# End of configuration
# =============================================================================

import argparse
import concurrent.futures as cf
import datetime as dt
import importlib
import importlib.metadata
import importlib.util
import json
import math
import multiprocessing as mp
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from pathlib import Path

REQUIRED = {  # import name: (pip name, minimum version)
    "numpy": ("numpy", "1.26"), "pandas": ("pandas", "2.0"),
    "geopandas": ("geopandas", "1.0"), "pyogrio": ("pyogrio", "0.9"),
    "shapely": ("shapely", "2.0"), "rasterio": ("rasterio", "1.4"),
    "pyproj": ("pyproj", "3.6"), "scipy": ("scipy", "1.11"),
    "psutil": ("psutil", "5.9"), "requests": ("requests", "2.28"), "pyarrow": ("pyarrow", "14"),
    "pyreadstat": ("pyreadstat", "1.2"),       # LSMS Stata files
}


def _version_ok(dist, minimum):
    try:
        have = importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return False
    num = lambda v: tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    return num(have) >= num(minimum)


def bootstrap(work_dir):
    """Install missing packages into WORK_DIR/pylib (no admin rights needed).

    pylib goes at the END of sys.path, so the environment's own numpy, pandas, GDAL stack always win
    (a second numpy in front of them breaks compiled packages such as rasterio). Missing packages are
    installed without their dependencies first; only a package that then fails to import is installed
    again with its dependencies. Outdated packages are reported, not shadowed."""
    lib = Path(work_dir).resolve() / "pylib"
    if lib.exists() and str(lib) not in sys.path:
        sys.path.append(str(lib))
        importlib.invalidate_caches()
    missing = [(mod, pip, v) for mod, (pip, v) in REQUIRED.items() if importlib.util.find_spec(mod) is None]
    old = [f"{pip} (needs >= {v})" for mod, (pip, v) in REQUIRED.items()
           if importlib.util.find_spec(mod) is not None and not _version_ok(pip, v)]
    if old:
        print(f"[bootstrap] WARNING: older than tested: {', '.join(old)}", flush=True)
    if not missing:
        return
    print(f"[bootstrap] installing into {lib}: {' '.join(p for _, p, _ in missing)}", flush=True)
    lib.mkdir(parents=True, exist_ok=True)
    pip = [sys.executable, "-m", "pip", "install", "--quiet", "--target", str(lib)]
    subprocess.check_call(pip + ["--no-deps"] + [f"{p}>={v}" for _, p, v in missing])
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([p for p in sys.path if p] + [str(lib)])}
    for mod, p, v in missing:
        for _ in range(15):          # add the dependencies the import reports missing, one at a time
            r = subprocess.run([sys.executable, "-c", f"import {mod}"], env=env, capture_output=True, text=True)
            if r.returncode == 0:
                break
            m = re.search(r"No module named '([\w.]+)'", r.stderr)
            if not m:
                subprocess.check_call(pip + ["--upgrade", f"{p}>={v}"])     # last resort: with dependencies
                break
            try:
                subprocess.check_call(pip + ["--no-deps", m.group(1).split(".")[0]])
            except subprocess.CalledProcessError:   # module name is not a pip name
                subprocess.check_call(pip + ["--upgrade", f"{p}>={v}"])
                break
    if str(lib) not in sys.path:
        sys.path.append(str(lib))
    importlib.invalidate_caches()


_PROJ_TEST = r"""
import os, tempfile
import numpy, pandas, geopandas as gpd, pyogrio, rasterio, shapely   # same order as the script
from rasterio.crs import CRS
from rasterio.warp import transform
assert CRS.from_epsg(4326).to_epsg() == 4326
transform(CRS.from_epsg(4326), CRS.from_string("ESRI:54009"), [10.0], [10.0])
with tempfile.TemporaryDirectory(dir=os.environ.get("CPL_TMPDIR")) as td:
    f = os.path.join(td, "t.gpkg")
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
    prints no error. AE_PROJ_DATA=<folder> forces a folder.
    """
    keys = ("PROJ_DATA", "PROJ_LIB")
    old = {k: os.environ[k] for k in keys if os.environ.get(k)}
    base = {k: v for k, v in os.environ.items() if k not in keys}
    if os.environ.get("AE_PROJ_DATA"):
        cands = [("AE_PROJ_DATA", {k: os.environ["AE_PROJ_DATA"] for k in keys})]
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
                         + "\nSet AE_PROJ_DATA to a folder containing proj.db (find / -name proj.db) and rerun.")
    label, c, still = usable
    if c is not None:
        for k in keys:
            os.environ.pop(k, None)
        os.environ.update(c)
    print(f"[bootstrap] PROJ data: {label}" + (f" (environment had {old})" if old else "")
          + (f"; tried first: {[t[0] for t in tried[:-1]]}" if len(tried) > 1 else "")
          + (f"; WARNING, PROJ still reports: {still}" if still else ""), flush=True)


def _early_work_dir():
    if os.environ.get("AE_WORK_DIR"):
        return os.environ["AE_WORK_DIR"]
    for i, a in enumerate(sys.argv):
        if a == "--work-dir" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith("--work-dir="):
            return a.split("=", 1)[1]
    return WORK_DIR


_WD = Path(_early_work_dir()).resolve()
(_WD / "tmp").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("CPL_TMPDIR", str(_WD / "tmp"))
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.TIF")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "6")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "3")
os.environ.setdefault("GDAL_HTTP_USERAGENT", USER_AGENT)
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
bootstrap(_WD)
fix_proj_data()

import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402
import geopandas as gpd                               # noqa: E402
import psutil                                         # noqa: E402
import pyarrow.parquet as pq                          # noqa: E402
import rasterio                                       # noqa: E402
import requests                                       # noqa: E402
import shapely                                        # noqa: E402
from rasterio.enums import Resampling                 # noqa: E402
from rasterio.features import rasterize               # noqa: E402
from rasterio.transform import from_origin            # noqa: E402
from rasterio.warp import reproject                   # noqa: E402
from rasterio.windows import Window                   # noqa: E402
from scipy import ndimage                             # noqa: E402

R_EARTH = 6371007.2
LOG = []
MANIFEST = []


# =============================================================================
# small utilities (as in global_accessibility_v3.py)
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
    try:
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


class RemoteUnavailable(RuntimeError):
    """A server kept failing: stop instead of guessing."""


def download(url, dest, sess=None, retries=5, headers=None):
    """Resumable download to dest (written as .part, renamed when complete, size recorded in
    .meta.json). A complete file already on disk is kept and never downloaded again."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta = dest.with_name(dest.name + ".meta.json")
    if dest.exists() and dest.stat().st_size > 0:
        m = json.loads(meta.read_text()) if meta.exists() else None
        if m is None or m.get("bytes") == dest.stat().st_size:
            MANIFEST.append({"url": url, "file": dest.name, "bytes": dest.stat().st_size,
                             "downloaded": (m or {}).get("downloaded", "earlier run")})
            return dest
    sess = sess or session()
    tmp = dest.with_name(dest.name + ".part")
    last = None
    for attempt in range(retries):
        try:
            h = dict(headers or {})
            if tmp.exists():
                h["Range"] = f"bytes={tmp.stat().st_size}-"
            with sess.get(url, stream=True, timeout=300, headers=h, allow_redirects=True) as r:
                if r.status_code == 416:
                    break
                if r.status_code in (401, 403, 404):
                    raise RemoteUnavailable(f"HTTP {r.status_code} for {url}")
                r.raise_for_status()
                with open(tmp, "ab" if r.status_code == 206 else "wb") as fh:
                    for chunk in r.iter_content(1 << 22):
                        fh.write(chunk)
            tmp.replace(dest)
            info = {"url": url, "bytes": dest.stat().st_size,
                    "downloaded": dt.datetime.now().isoformat(timespec="seconds")}
            meta.write_text(json.dumps(info))
            MANIFEST.append(info | {"file": dest.name})
            return dest
        except RemoteUnavailable:
            raise
        except Exception as e:
            last = e
            if attempt < retries - 1:
                wait = 5 * 2 ** attempt
                log(f"download retry {attempt + 1}/{retries} {url}: {e!r}; waiting {wait}s")
                time.sleep(wait)
    raise RemoteUnavailable(f"download failed after {retries} attempts: {url}: {last!r}")


def plan_workers(mem_per_task, n_tasks):
    budget = available_memory() * MEMORY_FRACTION
    n = max(1, min(n_tasks, max(1, cpu_count() - 1), int(budget // (mem_per_task + 0.4e9)),
                   MAX_WORKERS or 10**9))
    return n


def run_parallel(fn, jobs, mem_per_task, label):
    """fn(job) for every job in processes (fork), as many as memory and cores allow."""
    if not jobs:
        return []
    n = plan_workers(mem_per_task, len(jobs))
    log(f"{label}: {len(jobs)} tasks on {n} workers (~{mem_per_task / 1e9:.1f} GB each)")
    if n == 1:
        return [fn(j) for j in jobs]
    with cf.ProcessPoolExecutor(n, mp_context=mp.get_context("fork")) as ex:
        return list(ex.map(fn, jobs))


def write_parquet(df, path):
    """Atomic parquet write (a crash never leaves a half file that a resumed run would trust)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)
    return path


# =============================================================================
# grid, tiles and the travel-time store
# =============================================================================
class Grid:
    """Regular lon/lat grid (north-up), as in global_accessibility_v3.py."""

    def __init__(self, west, north, res, width, height):
        self.west, self.north, self.res, self.width, self.height = west, north, res, width, height
        self.east, self.south = west + width * res, north - height * res
        self.transform = from_origin(west, north, res, res)

    @classmethod
    def from_dict(cls, d):
        w, s, e, n = d["bbox"]
        return cls(w, n, d["res_deg"], d["width"], d["height"])

    @property
    def shape(self):
        return (self.height, self.width)

    @property
    def bounds(self):
        return (self.west, self.south, self.east, self.north)

    def window_of(self, bounds):
        """(row0, col0, rows, cols) of lon/lat bounds intersected with the grid, or None."""
        w, s, e, n = bounds
        w, e, s, n = max(w, self.west), min(e, self.east), max(s, self.south), min(n, self.north)
        if w >= e - 1e-9 or s >= n - 1e-9:
            return None
        c0 = int(math.floor((w - self.west) / self.res + 1e-6))
        c1 = int(math.ceil((e - self.west) / self.res - 1e-6))
        r0 = int(math.floor((self.north - n) / self.res + 1e-6))
        r1 = int(math.ceil((self.north - s) / self.res - 1e-6))
        return r0, c0, r1 - r0, c1 - c0

    def cell_area_km2(self, rows):
        """Area (km2) of the cells of the given grid rows (spherical)."""
        rows = np.asarray(rows)
        top = np.radians(self.north - rows * self.res)
        bot = np.radians(self.north - (rows + 1) * self.res)
        return (R_EARTH ** 2 * math.radians(self.res) * (np.sin(top) - np.sin(bot)) / 1e6).astype(np.float32)


def tile_name(w, n):
    return f"{'N' if n >= 0 else 'S'}{abs(n):02d}_{'E' if w >= 0 else 'W'}{abs(w):03d}"


def analysis_tiles(grid, bbox=None, deg=None):
    """10 x 10 degree tiles (aligned on multiples of TILE_DEG) of the analysis area inside the grid:
    [{"tile", "w", "s", "e", "n", "win": (r0, c0, nr, nc)}]."""
    deg = deg or TILE_DEG
    W, S, E, N = bbox or ANALYSIS_BBOX
    out = []
    for n in range(int(math.ceil(N / deg) * deg), int(math.floor(S / deg) * deg), -deg):
        for w in range(int(math.floor(W / deg) * deg), int(math.ceil(E / deg) * deg), deg):
            b = (max(w, W), max(n - deg, S), min(w + deg, E), min(n, N))
            win = grid.window_of(b)
            if win and win[2] > 0 and win[3] > 0:
                out.append({"tile": tile_name(w, n), "w": b[0], "s": b[1], "e": b[2], "n": b[3], "win": win})
    return out


class Store:
    """The grids of one or more global_accessibility_v3.py runs (RESULTS_DIR/store/manifest.json).
    A (name, year, layer) present in several runs is read from the first run listed."""

    def __init__(self, results_dirs):
        self.items, self.grid, self.runs = {}, None, []
        for rd in results_dirs:
            root = Path(rd) / "store"
            mf = root / "manifest.json"
            if not mf.exists():
                raise FileNotFoundError(f"{mf} not found: GA_RESULTS must list RESULTS_DIR folders of "
                                        "global_accessibility_v3.py runs that finished stage store")
            m = json.loads(mf.read_text())
            g = Grid.from_dict(m["grid"])
            if self.grid is None:
                self.grid = g
            elif abs(g.res - self.grid.res) > 1e-12 or abs((g.west - self.grid.west) / g.res % 1) > 1e-6 \
                    or abs((g.north - self.grid.north) / g.res % 1) > 1e-6:
                raise ValueError(f"{rd}: grid {m['grid']} is not on the lattice of {GA_RESULTS[0]}")
            self.runs.append({"dir": str(rd), "script": m.get("script"), "years": m.get("years"), "grid": m["grid"]})
            missing = 0
            for it in m["items"]:
                key = (it["name"], it["year"], it["layer"])
                if not (root / it["file"]).exists():
                    missing += 1                 # listed but removed (e.g. to save space)
                    continue
                self.items.setdefault(key, it | {"path": str(root / it["file"]), "grid": g})
            if missing:
                log(f"store {rd}: {missing} grids listed in the manifest are not on disk (ignored)")

    def years(self, name, layer=None):
        return sorted({k[1] for k in self.items if k[0] == name and k[2] == layer and k[1] is not None})

    def has(self, name, year=None, layer=None):
        return (name, year, layer) in self.items

    def read(self, name, year=None, layer=None, win=None):
        """Array on window win=(r0, c0, nr, nc) of the reference grid (outside a run's own extent:
        NaN for floats, 0 for integers). Float nodata is NaN."""
        it = self.items[(name, year, layer)]
        g = it["grid"]
        r0, c0, nr, nc = win if win else (0, 0, *self.grid.shape)
        # the same window on this run's grid
        dr = int(round((g.north - self.grid.north) / g.res))
        dc = int(round((self.grid.west - g.west) / g.res))
        rr0, cc0 = r0 + dr, c0 + dc
        with rasterio.open(it["path"]) as src:
            a = src.read(1, window=Window(cc0, rr0, nc, nr), boundless=True,
                         fill_value=src.nodata if src.nodata is not None else 0)
            nodata = src.nodata
        if a.dtype.kind == "f":
            a = a.astype(np.float32)
            if nodata is not None:
                a[a == nodata] = np.nan
        return a


def ssa_country_ids(store):
    """Country ids (store tables/countries.csv) of Sub-Saharan Africa."""
    for run in store.runs:
        f = Path(run["dir"]) / "store" / "tables" / "countries.csv"
        if f.exists():
            c = pd.read_csv(f)
            keep = c[(c.CONTINENT == "Africa") & ~c.iso3.isin(SSA_EXCLUDE)]
            return set(keep.cid.astype(int)), c
    raise FileNotFoundError("store tables/countries.csv not found in any GA_RESULTS run")


# =============================================================================
# stage treatment (Phase 0): access level, events and doses per cell
# =============================================================================
def access_events(tt, years, rel=None, abs_min=None, persist=None, direction="gain"):
    """First access event per cell from travel times tt (cells x reference years, minutes).

    gain: tt falls by >= rel (share) and >= abs_min minutes below the previous reference year's level,
    and stays there at every reference year y' with y <= y' < y + persist (with sparse reference years,
    e.g. 2015/2020/2025, at the next reference year instead). "loss" is the mirror image
    (tt rises). Returns (ref_year, checked): ref_year is the first reference year showing the change
    (0 = none); checked is False where fewer later reference years exist than the persistence needs
    (the event is kept, flagged)."""
    rel = EVENT_REL if rel is None else rel
    abs_min = EVENT_ABS_MIN if abs_min is None else abs_min
    persist = EVENT_PERSIST_YEARS if persist is None else persist
    years = np.asarray(years)
    n, T = tt.shape
    ref = np.zeros(n, np.int16)
    checked = np.ones(n, bool)
    for t in range(1, T):
        base = tt[:, t - 1]
        if direction == "gain":
            hold = lambda x: (x <= base * (1 - rel)) & (base - x >= abs_min)
        else:
            hold = lambda x: (x >= base * (1 + rel)) & (x - base >= abs_min)
        ok = hold(tt[:, t])
        later = [k for k in range(t + 1, T) if years[k] < years[t] + persist]
        if not later and persist > 1 and t + 1 < T:
            later = [t + 1]                 # sparse reference years: the next one must still show it
        for k in later:
            ok &= hold(tt[:, k])
        full = persist <= 1 or years[-1] >= years[t] + persist - 1
        new = ok & (ref == 0)
        ref[new] = years[t]
        checked[new] = bool(full)
    return ref, checked


def local_road_change(codes, k):
    """Per cell: number of OSM road-change cells (new or faster) within a (2k+1)^2 window, and the
    share of them inside mapping bursts. codes: road_events array (code +16 = in a burst)."""
    c = codes.astype(np.int16)
    base = c % 16
    chg = ((base == 1) | (base == 2)).astype(np.float32)
    bur = (chg > 0) & (c >= 16)
    size = 2 * k + 1
    n_chg = ndimage.uniform_filter(chg, size, mode="constant") * size * size
    n_bur = ndimage.uniform_filter(bur.astype(np.float32), size, mode="constant") * size * size
    n_chg = np.rint(n_chg).astype(np.int32)
    with np.errstate(invalid="ignore", divide="ignore"):
        share = np.where(n_chg > 0, np.rint(n_bur) / np.maximum(n_chg, 1), np.nan).astype(np.float32)
    return n_chg, share


def distance_to_change(codes, grid, row0, cap_km):
    """Distance (km, capped) from each cell to the nearest OSM road-change cell (new or faster),
    with the east-west spacing of the cell's latitude."""
    base = codes.astype(np.int16) % 16
    chg = (base == 1) | (base == 2)
    out = np.full(codes.shape, cap_km, np.float32)
    if not chg.any():
        return out
    lat = grid.north - (row0 + codes.shape[0] / 2) * grid.res
    dy = grid.res * 111.32
    dx = dy * max(math.cos(math.radians(lat)), 0.05)
    dist = ndimage.distance_transform_edt(~chg, sampling=(dy, dx)).astype(np.float32)
    return np.minimum(dist, cap_km, out=out)


def treatment_plan(store):
    """Reference years and the (version, layer) series available in the store."""
    series = {}
    for ver in TREAT_VERSIONS:
        name = "traveltime_roadonly" if ver == "roadonly" else "traveltime"
        for layer in TREAT_LAYERS:
            ys = store.years(name, layer)
            if len(ys) >= 2:
                series[(ver, layer)] = (name, ys)
    if not series:
        raise RuntimeError("no travel-time series with >= 2 years in GA_RESULTS for "
                           f"{TREAT_VERSIONS} x {TREAT_LAYERS}")
    return series


def treatment_job(job):
    """One tile -> work/treatment/<tile>.parquet: one row per land cell of Sub-Saharan Africa."""
    out = Path(job["out"])
    if out.exists():
        return {"tile": job["tile"], "cells": pq.read_metadata(out).num_rows}
    store = Store(job["ga_results"])
    grid = store.grid
    r0, c0, nr, nc = job["win"]
    cid = store.read("countries", None, None, job["win"]).astype(np.int32)
    keep = np.isin(cid, list(job["ssa"]))
    if not keep.any():
        write_parquet(pd.DataFrame({"cell": pd.Series([], np.int64)}), out)
        return {"tile": job["tile"], "cells": 0}
    rows, cols = np.nonzero(keep)
    d = {"cell": ((rows + r0).astype(np.int64) * grid.width + cols + c0),
         "row": (rows + r0).astype(np.int32), "col": (cols + c0).astype(np.int32),
         "lon": (grid.west + (cols + c0 + 0.5) * grid.res).astype(np.float32),
         "lat": (grid.north - (rows + r0 + 0.5) * grid.res).astype(np.float32),
         "cid": cid[keep], "area_km2": grid.cell_area_km2(rows + r0)}
    for name in ("tan_slope", "water_pct", "landcover"):
        if store.has(name):
            d[name] = store.read(name, None, None, job["win"])[keep]
    for e in store.years("population"):
        d[f"pop_{e}"] = store.read("population", e, None, job["win"])[keep].astype(np.float32)
    k = max(1, int(round(BURST_WINDOW_KM / (grid.res * 111.32))))
    h = max(k, int(math.ceil(BAND_MAX_KM / (grid.res * 111.32))))      # halo for both windows
    ev_years = store.years("road_events")
    burst_share, n_change = {}, {}
    for y in ev_years:
        # halo of h cells so the windows are complete at tile edges
        codes = store.read("road_events", y, None, (r0 - h, c0 - h, nr + 2 * h, nc + 2 * h))
        n_chg, share = local_road_change(codes, k)
        n_change[y], burst_share[y] = n_chg[h:-h, h:-h][keep], share[h:-h, h:-h][keep]
        d[f"roadchg_{y}"] = n_change[y].astype(np.int16)
        d[f"burstshare_{y}"] = burst_share[y]
        d[f"dnew_{y}"] = distance_to_change(codes, grid, r0 - h, BAND_MAX_KM)[h:-h, h:-h][keep]
    for (ver, layer), (name, ys) in job["series"].items():
        tt = np.stack([store.read(name, y, layer, job["win"])[keep] for y in ys], axis=1)
        tt = np.where(np.isfinite(tt), np.minimum(tt, TT_CAP_MIN), TT_CAP_MIN).astype(np.float32)
        tag = f"{ver}_{layer}"
        for i, y in enumerate(ys):
            d[f"tt_{tag}_{y}"] = tt[:, i]
        for direction, pre in (("gain", "ev"), ("loss", "evloss")):
            ref, checked = access_events(tt, ys, direction=direction)
            d[f"{pre}_{tag}"] = np.where(ref > 0, ref + EVENT_YEAR_SHIFT, 0).astype(np.int16)
            d[f"{pre}chk_{tag}"] = checked
            if direction == "gain":
                # attribution of the event to local road change (OSM events of the same reference year)
                cls = np.zeros(len(ref), np.int8)        # 0 no event, 1 local, 2 local burst, 3 remote
                bs = np.full(len(ref), np.nan, np.float32)
                for y in ev_years:
                    m = ref == y
                    if m.any():
                        bs[m] = burst_share[y][m]
                        local = n_change[y][m] > 0
                        cls[np.flatnonzero(m)[local]] = np.where(bs[m][local] >= BURST_SHARE_PLACEBO, 2, 1)
                        cls[np.flatnonzero(m)[~local]] = 3
                d[f"evclass_{tag}"] = cls
                d[f"evburst_{tag}"] = bs
    df = pd.DataFrame(d)
    write_parquet(df, out)
    return {"tile": job["tile"], "cells": len(df)}


def stage_treatment(ctx):
    store = ctx["store"]
    series = treatment_plan(store)
    ssa, _ = ssa_country_ids(store)
    for (ver, layer), (name, ys) in series.items():
        log(f"treatment {ver} {layer}: years {ys}")
    jobs = [{"tile": t["tile"], "win": t["win"], "ga_results": GA_RESULTS, "ssa": sorted(ssa),
             "series": series, "out": str(ctx["work"] / "treatment" / f"{t['tile']}.parquet")}
            for t in ctx["tiles"]]
    nyears = max(len(ys) for _, ys in series.values())
    mem = 1440 * 1440 * 4 * (len(series) * nyears * 2 + 30)
    res = run_parallel(treatment_job, jobs, mem, "treatment tiles")
    summary = pd.DataFrame(res)
    summary.to_csv(ctx["results"] / "tables" / "treatment_tiles.csv", index=False)
    (ctx["results"] / "tables" / "treatment_series.json").write_text(json.dumps(
        {f"{v}_{l}": {"store_item": n, "years": ys} for (v, l), (n, ys) in series.items()}, indent=1))
    log(f"treatment: {int(summary.cells.sum()):,} cells in {len(summary)} tiles")


# =============================================================================
# stage landuse (Phase 1): forest at baseline, annual loss, cropland and conversion per cell
# =============================================================================
def hansen_url(layer, tile):
    return HANSEN_URL.format(v=HANSEN_VERSION, layer=layer, tile=tile)


def hansen_tile_id(w, n):
    """Hansen tile name of the 10 x 10 degree tile whose north-west corner is (w, n), e.g. 10N_000E."""
    return f"{abs(n):02d}{'N' if n >= 0 else 'S'}_{abs(w):03d}{'E' if w >= 0 else 'W'}"


def gaced_zip_name(lon):
    L = int(math.floor(lon / 6) * 6)
    return f"lon_{L:+04d}_to_{L + 6:+04d}.zip"


def gaced_index(ctx, sess, bounds):
    """{member path: bounds} of the GACED30 3 x 3 degree tiles intersecting bounds (zips downloaded once,
    read in place through /vsizip/)."""
    w, s, e, n = bounds
    idx = {}
    for L in range(int(math.floor(w / 6) * 6), int(math.ceil(e / 6) * 6), 6):
        name = gaced_zip_name(L)
        z = download(GACED30_URL.format(name=name.replace("+", "%2B")), ctx["dl"] / "gaced30" / name, sess)
        cache = z.with_suffix(".index.json")
        if cache.exists():
            members = json.loads(cache.read_text())
        else:
            members = {}
            with zipfile.ZipFile(z) as zf:
                for m in zf.namelist():
                    if m.lower().endswith(".tif"):
                        with rasterio.open(f"/vsizip/{z}/{m}") as src:
                            members[f"/vsizip/{z}/{m}"] = list(src.bounds)
            cache.write_text(json.dumps(members))
        for m, b in members.items():
            if b[0] < e and b[2] > w and b[1] < n and b[3] > s:
                idx[m] = b
    return idx


def cropland_strip(sources, years, transform, shape):
    """Annual cropland (bool, years x rows x cols) of one strip of Hansen pixels, from GACED30 tiles
    ({path: bounds}; band 1 = 2000; 10 = cropland) or local GLAD annual tiles ({year: [files]}, 100 = cropland).
    Each source is opened once and warped only into the columns of the strip it covers."""
    out = np.zeros((len(years), *shape), bool)
    valid = np.zeros(shape, bool)
    res, w, n = transform.a, transform.c, transform.f
    e, s_ = w + shape[1] * res, n - shape[0] * res

    def window(b):
        c0 = max(0, int(math.floor((b[0] - w) / res)))
        c1 = min(shape[1], int(math.ceil((b[2] - w) / res)))
        return (c0, c1) if c1 > c0 else None

    def warp(src, band, c0, c1, nodata, fill):
        a = np.full((shape[0], c1 - c0), fill, np.uint8)
        reproject(rasterio.band(src, band), a, dst_transform=from_origin(w + c0 * res, n, res, res),
                  dst_crs="EPSG:4326", resampling=Resampling.nearest, dst_nodata=nodata, src_nodata=nodata)
        return a

    if CROPLAND_SOURCE == "gaced30":
        for path, b in sources.items():
            if not (b[0] < e and b[2] > w and b[1] < n and b[3] > s_):
                continue
            win = window(b)
            if win is None:
                continue
            c0, c1 = win
            with rasterio.open(path) as src:
                for i, y in enumerate(years):
                    band = y - 2000 + 1
                    if band > src.count:
                        continue
                    a = warp(src, band, c0, c1, 255, 255)
                    out[i, :, c0:c1] |= a == 10
                    valid[:, c0:c1] |= a != 255
    else:   # glad_annual: one folder per year of local tiles
        for i, y in enumerate(years):
            for path in sources.get(y, []):
                with rasterio.open(path) as src:
                    win = window(tuple(src.bounds))
                    if win is None or not (src.bounds.bottom < n and src.bounds.top > s_):
                        continue
                    c0, c1 = win
                    a = warp(src, 1, c0, c1, 0, 0)
                out[i, :, c0:c1] |= a == 100
                valid[:, c0:c1] |= a > 0
    return out, valid


def landuse_job(job):
    """One 10 x 10 degree tile: Hansen pixels (0.00025 deg) assigned to the 30" cell that holds their
    centre, in strips of LANDUSE_STRIP_ROWS rows. Areas are spherical pixel areas."""
    out = Path(job["out"])
    if out.exists():
        return job["tile"]
    cell, rr, cc = tile_cells(job)
    tr0, tc0, tnr, tnc = job["win"]
    gres, gwest, gnorth = job["gres"], job["gwest"], job["gnorth"]
    lut = np.full(tnr * tnc, -1, np.int64)
    lut[rr * tnc + cc] = np.arange(len(cell))
    n = len(cell)
    loss_years = list(range(2001, 2000 + HANSEN_LAST_LOSS + 1))
    crop_years = list(CROPLAND_YEARS)
    acc = {"forest2000_km2": np.zeros(n), "forest10_km2": np.zeros(n), "loss_pre_km2": np.zeros(n),
           "crop_stable_km2": np.zeros(n), "crop_valid_km2": np.zeros(n)}
    for y in loss_years:
        acc[f"loss_km2_{y}"] = np.zeros(n)
        acc[f"loss10_km2_{y}"] = np.zeros(n)
    for y in crop_years:
        acc[f"crop_km2_{y}"] = np.zeros(n)
    conv_years = [y for y in loss_years if y - 1 in crop_years and y in crop_years]
    for y in conv_years:
        acc[f"conv_km2_{y}"] = np.zeros(n)
        acc[f"newcrop_km2_{y}"] = np.zeros(n)
    if n == 0:
        write_parquet(pd.DataFrame({"cell": cell}), out)
        return job["tile"]
    with rasterio.open(job["treecover2000"]) as tcs, rasterio.open(job["lossyear"]) as lys, \
            rasterio.open(job["datamask"]) as dms:
        H, W = tcs.height, tcs.width
        res = tcs.transform.a
        west, north = tcs.transform.c, tcs.transform.f
        lon_c = west + (np.arange(W) + 0.5) * res
        ccol = np.floor((lon_c - gwest) / gres).astype(np.int64) - tc0
        okc = (ccol >= 0) & (ccol < tnc)
        for r in range(0, H, LANDUSE_STRIP_ROWS):
            h = min(LANDUSE_STRIP_ROWS, H - r)
            win = Window(0, r, W, h)
            lat_c = north - (r + np.arange(h) + 0.5) * res
            crow = np.floor((gnorth - lat_c) / gres).astype(np.int64) - tr0
            okr = (crow >= 0) & (crow < tnr)
            if not okr.any():
                continue
            tc = tcs.read(1, window=win)
            ly = lys.read(1, window=win)
            dm = dms.read(1, window=win)
            flat = crow[:, None] * tnc + ccol[None, :]
            ok = okr[:, None] & okc[None, :] & (dm == 1)
            idx = np.where(ok, lut[np.clip(flat, 0, tnr * tnc - 1)], -1)
            sel = idx >= 0
            if not sel.any():
                continue
            top, bot = np.radians(north - (r + np.arange(h)) * res), np.radians(north - (r + np.arange(h) + 1) * res)
            parea = (R_EARTH ** 2 * math.radians(res) * (np.sin(top) - np.sin(bot)) / 1e6)
            area = np.broadcast_to(parea[:, None], (h, W))
            ii, aa = idx[sel], area[sel]
            f30, f10, lys_ = tc[sel] >= FOREST_THRESHOLD, tc[sel] >= FOREST_THRESHOLD_ALT, ly[sel]
            def add(key, m):
                acc[key] += np.bincount(ii[m], weights=aa[m], minlength=n)
            add("forest2000_km2", f30)
            add("forest10_km2", f10)
            add("loss_pre_km2", f30 & (lys_ >= 1) & (lys_ <= 14))
            for y in loss_years:
                add(f"loss_km2_{y}", f30 & (lys_ == y - 2000))
                add(f"loss10_km2_{y}", f10 & (lys_ == y - 2000))
            if crop_years and job["crop_sources"]:
                transform = rasterio.transform.from_origin(west, north - r * res, res, res)
                crop, valid = cropland_strip(job["crop_sources"], crop_years, transform, (h, W))
                cs, vs = crop[:, sel], valid[sel]
                add("crop_valid_km2", vs)
                for i, y in enumerate(crop_years):
                    add(f"crop_km2_{y}", cs[i])
                stable = np.all(cs[[i for i, y in enumerate(crop_years) if y >= STABLE_CROP_FROM]], axis=0) \
                    if any(y >= STABLE_CROP_FROM for y in crop_years) else np.zeros(len(ii), bool)
                add("crop_stable_km2", stable)
                pos = {y: i for i, y in enumerate(crop_years)}
                for y in conv_years:
                    later = [pos[t] for t in range(y, y + CONVERSION_WINDOW + 1) if t in pos]
                    becomes = np.any(cs[later], axis=0)
                    # confirmed conversion: loss in y, not cropland in y-1, cropland in one of y..y+2
                    add(f"conv_km2_{y}", f30 & (lys_ == y - 2000) & ~cs[pos[y - 1]] & becomes)
                    # new cropland from other vegetation: not forest (10%) in 2000, no loss, not cropland in
                    # y-1, cropland in y and the year after (when observed)
                    nxt = cs[pos[y + 1]] if y + 1 in pos else cs[pos[y]]
                    add(f"newcrop_km2_{y}", ~f10 & (lys_ == 0) & ~cs[pos[y - 1]] & cs[pos[y]] & nxt)
    d = {"cell": cell}
    d.update({k: v.astype(np.float32) for k, v in acc.items()})
    # cells without cropland data (outside the cropland tiles, or no tiles at all): NaN, not 0
    nodata = acc["crop_valid_km2"] <= 0
    for k in d:
        if k.startswith(("crop_km2_", "conv_km2_", "newcrop_km2_")) or k == "crop_stable_km2":
            d[k] = np.where(nodata, np.nan, d[k]).astype(np.float32)
    write_parquet(pd.DataFrame(d), out)
    return job["tile"]


def landuse_targets():
    t = [(hansen_url("lossyear", "10N_000E"), f"forest loss (Hansen GFC {HANSEN_VERSION})", True)]
    if CROPLAND_SOURCE == "gaced30":
        t.append((GACED30_URL.format(name=gaced_zip_name(0).replace("+", "%2B")), "annual cropland (GACED30)", True))
    return t


def glad_annual_sources():
    """{year: [GeoTIFF]} of locally stored GLAD annual cropland tiles (GLAD_ANNUAL_DIR/<year>/*.tif)."""
    root = Path(GLAD_ANNUAL_DIR or "")
    if not GLAD_ANNUAL_DIR or not root.exists():
        raise RuntimeError("CROPLAND_SOURCE = 'glad_annual' needs GLAD_ANNUAL_DIR with one folder per year of "
                           "GLAD annual cropland tiles (e.g. exported from Earth Engine "
                           "projects/glad/Cropland_Annual_2015_2024)")
    return {int(p.name): sorted(map(str, p.glob("*.tif"))) for p in root.iterdir() if p.name.isdigit()}


def stage_landuse(ctx):
    sess = session()
    jobs = []
    glad = glad_annual_sources() if CROPLAND_SOURCE == "glad_annual" else None
    for t in ctx["tiles"]:
        tf = ctx["work"] / "treatment" / f"{t['tile']}.parquet"
        if not tf.exists() or pq.read_metadata(tf).num_rows == 0:
            continue
        w, n = int(math.floor(t["w"] / 10) * 10), int(math.ceil(t["n"] / 10) * 10)
        hid = hansen_tile_id(w, n)
        files = {}
        try:
            for layer in ("treecover2000", "lossyear", "datamask"):
                files[layer] = str(download(hansen_url(layer, hid), ctx["dl"] / "hansen" / Path(hansen_url(layer, hid)).name, sess))
        except RemoteUnavailable as e:
            log(f"landuse {t['tile']}: Hansen tile {hid} not available ({str(e)[:120]}); tile skipped")
            continue
        if CROPLAND_SOURCE == "gaced30":
            # a download failure stops the stage (rerun resumes): zero cropland must never be written
            crop_sources = gaced_index(ctx, sess, (t["w"], t["s"], t["e"], t["n"]))
        else:
            crop_sources = glad
        jobs.append({"tile": t["tile"], "win": t["win"], "treatment": str(tf), **files,
                     "crop_sources": crop_sources, "gres": ctx["grid"].res, "gwest": ctx["grid"].west,
                     "gnorth": ctx["grid"].north, "out": str(ctx["work"] / "landuse" / f"{t['tile']}.parquet")})
    run_parallel(landuse_job, jobs, LANDUSE_TASK_GB * 1e9, "land-use tiles")
    return {"tiles": len(jobs), "cropland": CROPLAND_SOURCE}


# =============================================================================
# raster helpers for stages landuse and covariates
# =============================================================================
def tile_grid(ctx, tile):
    """The analysis grid window of one tile as (transform, shape)."""
    g = ctx["grid"] if isinstance(ctx, dict) else ctx
    r0, c0, nr, nc = tile["win"]
    return from_origin(g.west + c0 * g.res, g.north - r0 * g.res, g.res, g.res), (nr, nc)


def warp_to_tile(src_path, transform, shape, resampling=Resampling.nearest, band=1, dtype=np.float32,
                 nodata_out=np.nan):
    """Read a raster (local path or /vsicurl/ URL) resampled onto a tile of the analysis grid."""
    out = np.full(shape, nodata_out, dtype)
    with rasterio.open(src_path) as src:
        reproject(rasterio.band(src, band), out, dst_transform=transform, dst_crs="EPSG:4326",
                  resampling=resampling, dst_nodata=nodata_out, src_nodata=src.nodata)
    return out


def tile_cells(job):
    """Cells (rows, cols inside the tile) and ids of the treatment table of a tile."""
    t = pd.read_parquet(job["treatment"], columns=["cell", "row", "col"])
    r0, c0, _, _ = job["win"]
    return t["cell"].to_numpy(), t["row"].to_numpy() - r0, t["col"].to_numpy() - c0


# =============================================================================
# stage covariates: rainfall (CHIRPS v3), conflict (UCDP GED; ACLED optional)
# =============================================================================
def acled_events(sess, iso_names, years, out):
    """ACLED events (latitude, longitude, year, fatalities) with the OAuth password grant; credentials
    from the environment variables ACLED_USERNAME and ACLED_PASSWORD (never stored)."""
    user, pwd = os.environ.get("ACLED_USERNAME"), os.environ.get("ACLED_PASSWORD")
    if not (user and pwd):
        return None
    r = sess.post(ACLED_TOKEN_URL, data={"username": user, "password": pwd, "grant_type": "password",
                                         "client_id": "acled", "scope": "authenticated"}, timeout=120)
    r.raise_for_status()
    tok = r.json()["access_token"]
    rows, cursor, page, limit = [], 0, 1, 5000
    while True:
        q = {"country": "|".join(iso_names), "year": f"{min(years)}|{max(years)}", "year_where": "BETWEEN",
             "fields": "event_id_cnty|year|latitude|longitude|fatalities|event_type", "limit": limit}
        q.update({"cursor": cursor} if cursor is not None else {"page": page})
        r = sess.get(ACLED_READ_URL, params=q, headers={"Authorization": f"Bearer {tok}"}, timeout=300)
        r.raise_for_status()
        js = r.json()
        data = js.get("data") or []
        rows += data
        if not data or len(data) < limit:
            break
        nxt = js.get("next_cursor")
        if nxt not in (None, "", 0, "0"):
            cursor = nxt                          # cursor paging
        else:
            cursor, page = None, page + 1         # page paging (no cursor in the response)
        if page > 2000:
            raise RuntimeError("ACLED paging did not end after 2000 pages")
    d = pd.DataFrame(rows)
    if not d.empty:
        for c in ("year", "latitude", "longitude", "fatalities"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
    write_parquet(d, out)
    return d


def conflict_events(ctx, sess):
    """Conflict events (lat, lon, year, n) of the study years: ACLED if credentials are set and the
    download works, UCDP GED otherwise (CC BY 4.0)."""
    out = ctx["work"] / "covariates" / "conflict_events.parquet"
    if out.exists():
        return pd.read_parquet(out)
    years = COV_YEARS
    d, source = None, None
    if CONFLICT_SOURCE == "acled":
        try:
            _, countries = ssa_country_ids(ctx["store"])
            # Natural Earth short names -> ACLED country names (the main differences; unverified list)
            fix = {"Dem. Rep. Congo": "Democratic Republic of Congo", "Congo": "Republic of Congo",
                   "S. Sudan": "South Sudan", "Central African Rep.": "Central African Republic",
                   "Eq. Guinea": "Equatorial Guinea", "Côte d'Ivoire": "Ivory Coast",
                   "eSwatini": "eSwatini", "W. Sahara": "Western Sahara", "São Tomé and Principe":
                   "Sao Tome and Principe"}
            names = [fix.get(x, x) for x in countries[countries.CONTINENT == "Africa"].NAME]
            d = acled_events(sess, names, years, ctx["dl"] / "acled_events.parquet")
            source = "ACLED" if d is not None else None
        except Exception as e:
            log(f"ACLED not used ({str(e)[:200]}); conflict from UCDP GED")
            d = None
    if d is None:
        z = download(UCDP_GED_URL, ctx["dl"] / Path(UCDP_GED_URL).name, sess)
        with zipfile.ZipFile(z) as zf:
            name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
            with zf.open(name) as fh:
                d = pd.read_csv(fh, usecols=["year", "latitude", "longitude", "best"], low_memory=False)
        source = "UCDP GED"
    d = d.rename(columns={"best": "fatalities"})
    d = d[d.year.between(min(years), max(years))][["year", "latitude", "longitude"]].dropna()
    write_parquet(d, out)
    (ctx["results"] / "tables" / "conflict_source.txt").write_text(f"{source}\n{len(d)} events\n")
    log(f"conflict: {len(d):,} events from {source}")
    return d


def covariates_job(job):
    out = Path(job["out"])
    if out.exists():
        return job["tile"]
    cell, rr, cc = tile_cells(job)
    d = {"cell": cell}
    if len(cell):
        transform, shape = job["transform"], job["shape"]
        rain = []
        for y, f in job["rain_files"].items():
            a = warp_to_tile(f, transform, shape, Resampling.nearest)
            a[a < 0] = np.nan
            d[f"rain_{y}"] = a[rr, cc].astype(np.float32)
            if y <= RAIN_BASELINE[1] and y >= RAIN_BASELINE[0]:
                rain.append(d[f"rain_{y}"])
        if rain:
            d["rain_mean"] = np.nanmean(np.stack(rain), axis=0).astype(np.float32)
        ev = pd.read_parquet(job["conflict"])
        res, (nr, nc) = job["res"], shape
        w, n = job["west"], job["north"]
        blk = max(1, int(round(CONFLICT_BLOCK_DEG / res)))
        er = np.floor((n - ev.latitude.to_numpy()) / res).astype(np.int64)
        ecn = np.floor((ev.longitude.to_numpy() - w) / res).astype(np.int64)
        ok = (er >= 0) & (er < nr) & (ecn >= 0) & (ecn < nc)
        ev = ev[ok]
        er, ecn = er[ok] // blk, ecn[ok] // blk
        nbr, nbc = -(-nr // blk), -(-nc // blk)
        for y in range(min(COV_YEARS), max(COV_YEARS) + 1):
            m = ev.year.to_numpy() == y
            grid_counts = np.bincount(er[m] * nbc + ecn[m], minlength=nbr * nbc).reshape(nbr, nbc)
            d[f"conflict_{y}"] = grid_counts[rr // blk, cc // blk].astype(np.float32)
    write_parquet(pd.DataFrame(d), out)
    return job["tile"]


def stage_covariates(ctx):
    sess = session()
    rain_files = {}
    for y in COV_YEARS:
        try:
            rain_files[y] = str(download(CHIRPS_ANNUAL_URL.format(y=y), ctx["dl"] / "chirps" / f"chirps-v3.0.{y}.tif", sess))
        except RemoteUnavailable as e:
            log(f"CHIRPS {y}: not available ({str(e)[:120]}); rain_{y} missing")
    conflict_events(ctx, sess)
    jobs = []
    for t in ctx["tiles"]:
        tf = ctx["work"] / "treatment" / f"{t['tile']}.parquet"
        if not tf.exists():
            continue
        transform, shape = tile_grid(ctx, t)
        jobs.append({"tile": t["tile"], "win": t["win"], "treatment": str(tf), "transform": transform,
                     "shape": shape, "rain_files": rain_files, "res": ctx["grid"].res,
                     "west": transform.c, "north": transform.f,
                     "conflict": str(ctx["work"] / "covariates" / "conflict_events.parquet"),
                     "out": str(ctx["work"] / "covariates" / f"{t['tile']}.parquet")})
    run_parallel(covariates_job, jobs, 2e9, "covariate tiles")
    return {"rain_years": sorted(rain_files), "tiles": len(jobs)}


# =============================================================================
# stage projects: externally dated road projects (AidData GeoGCDF v3)
# =============================================================================
def pick_col(cols, *patterns):
    for p in patterns:
        hit = [c for c in cols if re.search(p, c, re.I)]
        if hit:
            return hit[0]
    return None


def road_projects(ctx, sess):
    """Transport projects of GeoGCDF v3 in Africa with an actual completion year: GeoDataFrame
    (project, completion, start, geometry)."""
    out = ctx["work"] / "projects" / "road_projects.gpkg"
    if out.exists():
        return gpd.read_file(out)
    z = download(GCDF_URL, ctx["dl"] / "gcdf" / Path(GCDF_URL).name, sess)
    with zipfile.ZipFile(z) as zf:
        name = [n for n in zf.namelist() if n.lower().endswith((".gpkg", ".geojson"))][0]
        dest = ctx["dl"] / "gcdf" / Path(name).name
        if not dest.exists():
            zf.extract(name, ctx["dl"] / "gcdf")
            (ctx["dl"] / "gcdf" / name).replace(dest)
    g = gpd.read_file(dest)
    cols = list(g.columns)
    sector = pick_col(cols, r"^sector\.?name$", r"sector")
    comp_y = pick_col(cols, r"^completion\.?year$")
    comp_d = pick_col(cols, r"actual.*completion.*date")
    start_d = pick_col(cols, r"actual.*implementation.*start.*date", r"implementation\.?start\.?year")
    iso = pick_col(cols, r"recipient.*iso", r"iso.?3")
    title = pick_col(cols, r"^title$")
    idc = pick_col(cols, r"^id$", r"project.?id")
    log(f"GeoGCDF columns used: id {idc}, sector {sector}, completion {comp_y or comp_d}, start {start_d}, iso {iso}")
    g = g[g[sector].astype(str).str.contains("TRANSPORT", case=False, na=False)]
    if title:
        road = g[title].astype(str).str.contains(r"road|highway|bridge|expressway|route", case=False, na=False)
        g = g[road | g.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    comp = pd.to_numeric(g[comp_y], errors="coerce") if comp_y else \
        pd.to_datetime(g[comp_d], format="%m/%d/%Y", errors="coerce").dt.year
    start = pd.to_datetime(g[start_d], format="%m/%d/%Y", errors="coerce").dt.year if start_d and "date" in start_d.lower() \
        else (pd.to_numeric(g[start_d], errors="coerce") if start_d else np.nan)
    g = gpd.GeoDataFrame({"project": g[idc].astype(str) if idc else g.index.astype(str),
                          "iso3": g[iso] if iso else None, "completion": comp, "start": start,
                          "geom_type": g.geometry.geom_type}, geometry=g.geometry, crs=g.crs or 4326)
    g = g[g.completion.notna()].to_crs(4326)
    w, s, e, n = ctx["bbox"]
    g = g[g.intersects(shapely.box(w, s, e, n))]
    out.parent.mkdir(parents=True, exist_ok=True)
    g.to_file(out)
    g.drop(columns="geometry").to_csv(ctx["results"] / "tables" / "road_projects.csv", index=False)
    log(f"projects: {len(g)} dated transport projects ({g.geom_type.value_counts().to_dict()})")
    return g


def projects_job(job):
    """Cells within PROJECT_BUFFER_KM of a dated road project: earliest completion year and distance."""
    out = Path(job["out"])
    if out.exists():
        return job["tile"]
    cell, rr, cc = tile_cells(job)
    g = gpd.read_file(job["projects"], bbox=job["bounds_halo"])
    d = {"cell": cell, "proj_year": np.zeros(len(cell), np.int16), "proj_km": np.full(len(cell), np.nan, np.float32)}
    if len(cell) and len(g):
        tr0, (nr0, nc0) = job["transform"], job["shape"]
        pad = int(math.ceil(PROJECT_BUFFER_KM / (job["res"] * 111.32 * 0.5))) + 1   # >= buffer at 60 deg
        transform = from_origin(tr0.c - pad * job["res"], tr0.f + pad * job["res"], job["res"], job["res"])
        shape = (nr0 + 2 * pad, nc0 + 2 * pad)
        rr, cc = rr + pad, cc + pad
        best = np.full(shape, 0, np.int16)
        dist_best = np.full(shape, np.inf, np.float32)
        lat = job["north"] - nr0 / 2 * job["res"]
        dy = job["res"] * 111.32
        dx = dy * max(math.cos(math.radians(lat)), 0.05)
        for yr, grp in g.groupby("completion"):
            m = rasterize(((geom, 1) for geom in grp.geometry if geom is not None and not geom.is_empty),
                          out_shape=shape, transform=transform, fill=0, all_touched=True, dtype="uint8")
            if not m.any():
                continue
            dist = ndimage.distance_transform_edt(m == 0, sampling=(dy, dx)).astype(np.float32)
            near = dist <= PROJECT_BUFFER_KM
            take = near & ((best == 0) | (yr < best))
            best[take] = int(yr)
            dist_best = np.where(near, np.minimum(dist_best, dist), dist_best)
        d["proj_year"] = best[rr, cc]
        d["proj_km"] = np.where(np.isfinite(dist_best[rr, cc]), dist_best[rr, cc], np.nan).astype(np.float32)
    write_parquet(pd.DataFrame(d), out)
    return job["tile"]


def stage_projects(ctx):
    sess = session()
    try:
        road_projects(ctx, sess)
    except RemoteUnavailable as e:
        log(f"projects: GeoGCDF v3 not available ({str(e)[:200]}); dated-project checks skipped")
        return {"projects": 0}
    jobs = []
    halo = PROJECT_BUFFER_KM / 111.0 + 0.05
    for t in ctx["tiles"]:
        tf = ctx["work"] / "treatment" / f"{t['tile']}.parquet"
        if not tf.exists():
            continue
        transform, shape = tile_grid(ctx, t)
        jobs.append({"tile": t["tile"], "win": t["win"], "treatment": str(tf), "transform": transform,
                     "shape": shape, "res": ctx["grid"].res, "north": transform.f,
                     "bounds_halo": (t["w"] - halo, t["s"] - halo, t["e"] + halo, t["n"] + halo),
                     "projects": str(ctx["work"] / "projects" / "road_projects.gpkg"),
                     "out": str(ctx["work"] / "projects" / f"{t['tile']}.parquet")})
    run_parallel(projects_job, jobs, 2e9, "project tiles")
    return {"tiles": len(jobs)}


# =============================================================================
# stage gate_t: Gate T per zone (country, or the zones of GATE_T_ZONES)
# =============================================================================
def stage_gate_t(ctx):
    rows = []
    _, countries = ssa_country_ids(ctx["store"])
    iso = dict(zip(countries.cid, countries.iso3))
    for t in ctx["tiles"]:
        tf = ctx["work"] / "treatment" / f"{t['tile']}.parquet"
        if not tf.exists():
            continue
        cols = pq.read_schema(tf).names
        spec = PRIMARY_SPEC if f"ev_{PRIMARY_SPEC}" in cols else (spec_names(cols) or [None])[0]
        if spec is None:
            continue
        d = pd.read_parquet(tf, columns=["cell", "cid", "area_km2", f"ev_{spec}", f"evclass_{spec}"])
        pf = ctx["work"] / "projects" / f"{t['tile']}.parquet"
        if pf.exists():
            d = d.merge(pd.read_parquet(pf), on="cell", how="left")
        d = d[d[f"ev_{spec}"] > 0]
        if d.empty:
            continue
        d["zone"] = d.cid.map(iso)
        d["spec"] = spec
        rows.append(d)
    if not rows:
        log("gate_t: no access events")
        return {"zones": 0}
    d = pd.concat(rows, ignore_index=True)
    spec = d.spec.iloc[0]
    cls = d[f"evclass_{spec}"]
    d["burst"] = cls == 2
    d["remote"] = cls == 3
    near = d.get("proj_year", pd.Series(0, index=d.index)).fillna(0) > 0
    d["near_project"] = near
    d["project_agrees"] = near & ((d[f"ev_{spec}"] - d.get("proj_year", 0)).abs() <= GATE_T_DATE_TOL)
    g = d.groupby("zone").agg(event_cells=("cell", "size"), event_km2=("area_km2", "sum"),
                              share_burst=("burst", "mean"), share_remote=("remote", "mean"),
                              near_project=("near_project", "sum"), project_agrees=("project_agrees", "sum"))
    g["share_project_agrees"] = g.project_agrees / g.near_project.where(g.near_project > 0)
    g["imagery_confirmed_share"] = np.nan        # not implemented (Valle et al. 2024 method): see README
    g["pass_burst"] = g.share_burst <= GATE_T_MAX_BURST
    g["gate_t"] = np.where(g.pass_burst, "burst criterion passed; imagery confirmation not assessed",
                           "failed (burst share): long-term analysis (E3) only")
    g = g.reset_index()
    g.insert(1, "spec", spec)
    g.to_csv(ctx["results"] / "tables" / "gate_t.csv", index=False)
    log(f"gate_t: {len(g)} zones, {int(g.pass_burst.sum())} pass the burst criterion")
    return {"zones": len(g), "pass_burst": int(g.pass_burst.sum())}


# =============================================================================
# stage admin (E2a): HarvestStat Africa yields with unit-level treatment
# =============================================================================
def fetch_github_file(url, dest, sess):
    """Download a file from raw.githubusercontent; if it is a Git LFS pointer, fetch the LFS object."""
    f = download(url, dest, sess)
    with open(f, "rb") as fh:
        head = fh.read(200)
    if head.startswith(b"version https://git-lfs"):
        f.unlink()
        Path(str(f) + ".meta.json").unlink(missing_ok=True)
        media = url.replace("https://raw.githubusercontent.com/", "https://media.githubusercontent.com/media/")
        f = download(media, dest, sess)
    return f


def unit_sums_job(job):
    """Per admin unit and reference year: weighted sums of log1p(travel time), weights, and the weight of
    event cells (all, burst) by event year; over the cells of one tile."""
    t = pd.read_parquet(job["treatment"])
    if t.empty:
        return None
    r0, c0, nr, nc = job["win"]
    units = gpd.read_file(job["units"], bbox=job["bounds"])
    if units.empty:
        return None
    transform, shape = job["transform"], job["shape"]
    uid = rasterize(((geom, int(i)) for geom, i in zip(units.geometry, units.uid)), out_shape=shape,
                    transform=transform, fill=0, dtype="int32")
    t["uid"] = uid[t.row.to_numpy() - r0, t.col.to_numpy() - c0]
    t = t[t.uid > 0]
    if t.empty:
        return None
    lu_f = Path(job["landuse"])
    wcols = {}
    if lu_f.exists():
        lu = pd.read_parquet(lu_f)
        crop = [c for c in lu.columns if c.startswith("crop_km2_")]
        if crop:
            first = sorted(crop)[0]
            t = t.merge(lu[["cell", first]], on="cell", how="left")
            wcols["cropland"] = t[first].fillna(0).to_numpy(np.float64)
    pops = sorted(c for c in t.columns if re.fullmatch(r"pop_\d{4}", c))
    if pops:
        wcols["population"] = t[pops[0]].fillna(0).to_numpy(np.float64)
    out = []
    for wname, w in wcols.items():
        rec = {"uid": t.uid.to_numpy()}
        rec["w"] = w
        for c in t.columns:
            if c.startswith("tt_"):
                rec[f"s_{c}"] = w * np.log1p(t[c].to_numpy(np.float64))
        for sp in spec_names(t.columns):
            ev, cls = t[f"ev_{sp}"].to_numpy(), t.get(f"evclass_{sp}")
            for y in np.unique(ev[ev > 0]):
                rec[f"wev_{sp}_{y}"] = w * (ev == y)
                if cls is not None:
                    rec[f"wburst_{sp}_{y}"] = w * ((ev == y) & (cls.to_numpy() == 2))
        g = pd.DataFrame(rec).groupby("uid").sum()
        g["weight"] = wname
        out.append(g.reset_index())
    return pd.concat(out, ignore_index=True) if out else None


def unit_treatment(sums, weight, fallback=None):
    """Unit-level travel time series, events and doses from the weighted sums of the cells. Units whose
    total `weight` is zero (e.g. no cropland around them) use the `fallback` weight instead."""
    s = sums[sums.weight == weight].groupby("uid").sum(numeric_only=True)
    s = s[s.w > 0]
    used = pd.Series(weight, index=s.index)
    if fallback is not None:
        f = sums[sums.weight == fallback].groupby("uid").sum(numeric_only=True)
        f = f[(f.w > 0) & ~f.index.isin(s.index)]
        s = pd.concat([s, f]).fillna(0)
        used = pd.concat([used, pd.Series(fallback, index=f.index)])
    out = pd.DataFrame(index=s.index)
    out["weight_used"] = used.reindex(s.index).to_numpy()
    specs = sorted({c[5:].rsplit("_", 1)[0] for c in s.columns if c.startswith("s_tt_")})
    for sp in specs:
        ys = sorted(int(c.rsplit("_", 1)[1]) for c in s.columns if c.startswith(f"s_tt_{sp}_"))
        tt = np.column_stack([np.expm1(s[f"s_tt_{sp}_{y}"] / s.w) for y in ys]).astype(np.float32)
        for i, y in enumerate(ys):
            out[f"tt_{sp}_{y}"] = tt[:, i]
        ref, _ = access_events(tt, ys)
        g = np.where(ref > 0, ref + EVENT_YEAR_SHIFT, 0)
        out[f"ev_{sp}"] = g
        # burst placebo: the unit event is a burst event if most of the weight of the unit's event cells
        # of that year lies in cells whose event is attributed to a mapping burst
        burst = np.zeros(len(s), bool)
        for i, y in enumerate(g):
            if y > 0:
                a, b = f"wev_{sp}_{y}", f"wburst_{sp}_{y}"
                if a in s and b in s and s[a].iloc[i] > 0:
                    burst[i] = s[b].iloc[i] / s[a].iloc[i] >= BURST_SHARE_PLACEBO
        out[f"evclass_{sp}"] = np.where(g > 0, np.where(burst, 2, 1), 0)
    return out.reset_index()


def admin_panel(units_tr, hv, units):
    """HarvestStat rows (quality flag 0) joined to the unit treatment: one row per unit x crop x season x
    harvest year, with log yield and the treatment columns of estimate_effects.R."""
    hv = hv[(hv.qc_flag == 0) & (hv["yield"] > 0) & hv.harvest_year.notna()].copy()
    hv = hv.drop(columns=["country_code", "lat", "lon"], errors="ignore")    # taken from the boundary file
    hv = hv.merge(units[["fnid", "uid", "lat", "lon", "country_code"]], on="fnid", how="inner")
    hv = hv.merge(units_tr, on="uid", how="inner")
    hv["crop"] = hv["product"].astype(str)
    hv["unit"] = (hv.fnid.astype(str) + "|" + hv.crop + "|" + hv.season_name.astype(str) + "|"
                  + hv.crop_production_system.astype(str))
    hv["id"] = pd.factorize(hv["unit"])[0] + 1
    hv["year"] = hv.harvest_year.astype(int)
    hv["log_yield"] = np.log(hv["yield"].astype(float))
    hv["region"] = hv.country_code.astype(str)
    hv["w"] = 1.0
    keep = ["id", "unit", "fnid", "crop", "season_name", "year", "log_yield", "area", "production", "region",
            "lat", "lon", "w"]
    out = hv[keep].copy()
    for sp in spec_names(units_tr.columns):
        g, dose = cohort_dose(hv, sp)
        out[f"g__{sp}"] = np.where(hv[f"evclass_{sp}"] == 2, -1, g).astype(np.int32)
        out[f"gburst__{sp}"] = np.where(hv[f"evclass_{sp}"] == 2, g, 0).astype(np.int32)
        out[f"dose__{sp}"] = dose
        first = out.groupby("id").year.transform("min")
        last = out.groupby("id").year.transform("max")
        out.loc[(out[f"g__{sp}"] > 0) & (out[f"g__{sp}"] <= first), f"g__{sp}"] = -1
        for c in (f"g__{sp}", f"gburst__{sp}"):
            out.loc[out[c] > last, c] = 0                   # treated after the series: not yet treated
    return out


def unit_year_treatment(out, d, specs):
    """Treatment columns of estimate_effects.R on a unit-year table `out` (columns id, year), from the
    unit treatment merged into `d` (same rows): cohort (-1 always treated or burst-only, 0 not treated within
    the unit's series), burst placebo cohort and dose."""
    for sp in specs:
        g, dose = cohort_dose(d, sp)
        burst = d[f"evclass_{sp}"].to_numpy() == 2
        out[f"g__{sp}"] = np.where(burst, -1, g).astype(np.int32)
        out[f"gburst__{sp}"] = np.where(burst, g, 0).astype(np.int32)
        out[f"dose__{sp}"] = dose
        first = out.groupby("id").year.transform("min")
        last = out.groupby("id").year.transform("max")
        out.loc[(out[f"g__{sp}"] > 0) & (out[f"g__{sp}"] <= first), f"g__{sp}"] = -1
        for c in (f"g__{sp}", f"gburst__{sp}"):
            out.loc[out[c] > last, c] = 0
    return out


def admin_longdiff(units_tr, hv_panel, units):
    """E3 for admin units: mean log yield over the 3 harvest years ending at each epoch end, differenced,
    against the unit access gain over the epoch."""
    rows = []
    specs = spec_names(units_tr.columns)
    for a, b in LONG_EPOCHS:
        ya = hv_panel[hv_panel.year.between(a - 2, a)].groupby(["unit", "crop"]).log_yield.mean()
        yb = hv_panel[hv_panel.year.between(b - 2, b)].groupby(["unit", "crop"]).log_yield.mean()
        dy = (yb - ya).dropna().rename("d_log_yield").reset_index()
        if dy.empty:
            continue
        dy["fnid"] = dy.unit.str.split("|").str[0]          # unit = fnid|crop|season|system
        dy = dy.merge(units[["fnid", "uid", "lat", "lon", "country_code"]], on="fnid").merge(units_tr, on="uid")
        rec = pd.DataFrame({"dataset": "E2a_admin", "crop": dy.crop, "id": pd.factorize(dy.unit)[0] + 1,
                            "lat": dy.lat, "lon": dy.lon, "region": dy.country_code, "w": 1.0,
                            "epoch": f"{a}-{b}", "d_log_yield": dy.d_log_yield})
        for sp in specs:
            ys = tt_years(units_tr.columns, sp)
            y0, y1 = nearest_year(ys, a, LONG_EPOCH_TOL), nearest_year(ys, b, LONG_EPOCH_TOL)
            if y0 and y1 and y0 < y1:
                rec[f"d_access__{sp}"] = -(np.log1p(dy[f"tt_{sp}_{y1}"]) - np.log1p(dy[f"tt_{sp}_{y0}"])).to_numpy()
        rows.append(rec)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def stage_admin(ctx):
    sess = session()
    work = ctx["work"]
    try:
        csv = fetch_github_file(HARVESTSTAT_CSV_URL, ctx["dl"] / "harveststat" / Path(HARVESTSTAT_CSV_URL).name, sess)
        gpkg = fetch_github_file(HARVESTSTAT_GPKG_URL, ctx["dl"] / "harveststat" / Path(HARVESTSTAT_GPKG_URL).name, sess)
    except RemoteUnavailable as e:
        log(f"admin: HarvestStat not available ({str(e)[:200]}); E2a skipped")
        return {"units": 0}
    units = gpd.read_file(gpkg).to_crs(4326)
    w, s, e, n = ctx["bbox"]
    units = units[units.intersects(shapely.box(w, s, e, n))].reset_index(drop=True)
    units["uid"] = np.arange(1, len(units) + 1, dtype=np.int32)
    pts = units.geometry.representative_point()
    units["lon"], units["lat"] = pts.x.to_numpy(), pts.y.to_numpy()
    uf = work / "admin" / "units.gpkg"
    uf.parent.mkdir(parents=True, exist_ok=True)
    units.to_file(uf)
    jobs = []
    for t in ctx["tiles"]:
        tf = work / "treatment" / f"{t['tile']}.parquet"
        if not tf.exists():
            continue
        transform, shape = tile_grid(ctx, t)
        jobs.append({"tile": t["tile"], "win": t["win"], "treatment": str(tf), "transform": transform,
                     "shape": shape, "bounds": (t["w"], t["s"], t["e"], t["n"]), "units": str(uf),
                     "landuse": str(work / "landuse" / f"{t['tile']}.parquet")})
    parts = [p for p in run_parallel(unit_sums_job, jobs, 3e9, "admin unit sums") if p is not None]
    if not parts:
        log("admin: no HarvestStat unit overlaps the treatment tiles")
        return {"units": 0}
    sums = pd.concat(parts, ignore_index=True).fillna(0)
    weight = ADMIN_WEIGHT if (sums.weight == ADMIN_WEIGHT).any() else sums.weight.iloc[0]
    other = sorted(set(sums.weight) - {weight})
    tr = unit_treatment(sums, weight, fallback=other[0] if other else None)
    for alt in other:
        write_parquet(unit_treatment(sums, alt), work / "admin" / f"unit_treatment_{alt}.parquet")
    write_parquet(tr, work / "admin" / f"unit_treatment_{weight}.parquet")
    hv = pd.read_csv(csv, low_memory=False)
    panel = admin_panel(tr, hv, units)
    write_parquet(panel, work / "panels_parts" / "e2a_admin.parquet")
    ld = admin_longdiff(tr, panel, units)
    if not ld.empty:
        write_parquet(ld, work / "panels_parts" / "e3_admin.parquet")
    log(f"admin: {panel.id.nunique():,} unit-crop-season series, {len(panel):,} rows, weight {weight}")
    return {"series": int(panel.id.nunique()), "rows": len(panel), "weight": weight}


# =============================================================================
# stage lsms (E2b): LSMS-ISA enumeration-area panel
# =============================================================================
# Source for Ethiopia, Malawi, Nigeria, Tanzania, Uganda (and the older Mali / Niger surveys): the
# LSMS-ISA harmonised panel v2.0 (Bentze & Wollburg, World Bank; Scientific Data 2025,
# doi:10.1038/s41597-025-05639-9; Zenodo 10.5281/zenodo.14016543). Main season only (Uganda: both).
# EHCVM 2018/19 and 2021/22 are only inventoried here: the 2018 harvest module has no kg conversion
# in the files, so EHCVM yields need unit conversion factors that were not found (open item).
def lsms_wave_year(country, wave):
    """Agricultural (harvest) year of a harmonised-panel wave: the first calendar year of the survey.
    From the survey years of each wave (LSMS_WAVE_YEARS; inferred, check against the panel's own
    documentation)."""
    key = {k.lower(): k for k in LSMS_WAVE_YEARS}
    iso = {"eth": "ethiopia", "mwi": "malawi", "nga": "nigeria", "tza": "tanzania", "uga": "uganda",
           "ner": "niger", "mli": "mali"}
    c = str(country).strip().lower()
    c = iso.get(c, c)
    hit = next((key[k] for k in key if c.startswith(k)), None)
    return LSMS_WAVE_YEARS[hit].get(int(wave)) if hit else None


def lsms_inventory(ctx):
    """sources.csv rows (enabled) with whether the zip was found under LSMS_DIR."""
    f = Path(LSMS_SOURCES)
    if not f.exists():
        return pd.DataFrame()
    s = pd.read_csv(f, comment="#", skip_blank_lines=True)
    s = s[s.source_id.notna() & (s.program.astype(str).str.upper() == "LSMS")]
    s["enabled"] = s.enabled.astype(str).str.upper().eq("TRUE")
    files = {p.name.lower(): p for p in Path(LSMS_DIR).rglob("*.zip")} if Path(LSMS_DIR).exists() else {}
    s["zip_name"] = s.data_path.astype(str).str.replace("\\", "/").str.split("/").str[-1]
    s["found"] = s.zip_name.str.lower().map(lambda n: str(files[n]) if n in files else "")
    s["family"] = np.where(s.source_id.str.contains("EHCVM"), "EHCVM", "LSMS-ISA")
    return s


def lsms_plan(ctx):
    inv = lsms_inventory(ctx)
    found = int((inv.found != "").sum()) if len(inv) else 0
    return (f"harmonised panel (Zenodo) for ETH, MWI, NGA, TZA, UGA; sources.csv: {len(inv)} LSMS rows, "
            f"{found} zips found under {LSMS_DIR} (EHCVM inventoried only)")


def read_dta(path, columns=None):
    import pyreadstat
    if columns is not None:
        meta = pyreadstat.read_dta(str(path), metadataonly=True)[1]
        columns = [c for c in columns if c in meta.column_names]
    df, _ = pyreadstat.read_dta(str(path), usecols=columns, apply_value_formats=False)
    return df


def lsms_plots(ctx, sess):
    """Plot-crop rows of the harmonised panel with plot attributes: country, wave, year, season, ea,
    household, plot, crop, harvest_kg, crop_area_ha, intercropped, inputs, coordinates."""
    out = ctx["work"] / "lsms" / "plotcrop.parquet"
    if out.exists():
        return pd.read_parquet(out)
    dl = ctx["dl"] / "lsms_hp"
    pc = download(LSMS_HP_URL.format(f="Plotcrop_dataset.dta"), dl / "Plotcrop_dataset.dta", sess)
    pl = download(LSMS_HP_URL.format(f="Plot_dataset.dta"), dl / "Plot_dataset.dta", sess)
    keys = ["country", "wave", "season", "plot_id_obs"]
    c = read_dta(pc, keys + ["household_id_obs", "ea_id_obs", "crop_name", "harvest_kg", "harvest_value_USD",
                             "improved", "lat_modified", "lon_modified", "pw"])
    p = read_dta(pl, keys + ["plot_area_GPS", "intercropped", "nb_seasonal_crop", "inorganic_fertilizer",
                             "total_hired_labor_days", "share_kg_sold", "irrigated", "plot_slope"])
    d = c.merge(p, on=keys, how="left")
    d["year"] = [lsms_wave_year(a, b) for a, b in zip(d.country, d.wave)]
    miss = d[d.year.isna()][["country", "wave"]].drop_duplicates()
    if len(miss):
        log(f"lsms: no harvest year for {miss.to_dict('records')} (LSMS_WAVE_YEARS); rows dropped")
    d = d[d.year.notna()].copy()
    d["year"] = d.year.astype(int)
    # crop area: the whole plot for a single crop; intercropped plots split equally between their crops
    # (the panel has no per-crop share of the plot); intercropped rows are flagged and analysed apart
    n = pd.to_numeric(d.nb_seasonal_crop, errors="coerce").clip(lower=1).fillna(1)
    inter = pd.to_numeric(d.intercropped, errors="coerce").fillna(0) > 0
    d["crop_area_ha"] = np.where(inter, d.plot_area_GPS / n, d.plot_area_GPS)
    d["intercropped"] = inter
    write_parquet(d, out)
    return d


def ea_points(plots):
    """One displaced coordinate per EA (median over its households and waves)."""
    e = plots.dropna(subset=["lat_modified", "lon_modified"]).groupby(["country", "ea_id_obs"]).agg(
        lat=("lat_modified", "median"), lon=("lon_modified", "median")).reset_index()
    e["ea"] = e.country.astype(str) + "|" + e.ea_id_obs.astype(str)
    e["uid"] = np.arange(1, len(e) + 1, dtype=np.int32)
    return e


def ea_aggregate(plots, intercropped=False):
    """EA x crop x year yields: ratio of sums (kg / ha) over the plots, with counts and mechanisms."""
    d = plots[(plots.harvest_kg >= 0) & (plots.crop_area_ha > 0) & (plots.intercropped == intercropped)].copy()
    d["ea"] = d.country.astype(str) + "|" + d.ea_id_obs.astype(str)
    d["hired"] = pd.to_numeric(d.total_hired_labor_days, errors="coerce") > 0
    g = d.groupby(["ea", "country", "crop_name", "year"]).agg(
        kg=("harvest_kg", "sum"), ha=("crop_area_ha", "sum"), n_hh=("household_id_obs", "nunique"),
        n_plots=("plot_id_obs", "nunique"), fert=("inorganic_fertilizer", "mean"), improved=("improved", "mean"),
        hired=("hired", "mean"), sold=("share_kg_sold", "mean"), pw=("pw", "sum")).reset_index()
    g = g[(g.n_hh >= EA_MIN_HH) & (g.n_plots >= EA_MIN_PLOTS)]
    g["log_yield"] = np.log(g.kg / g.ha).replace([-np.inf, np.inf], np.nan)
    # crop-agnostic outcome: value of output per hectare, all crops and plots of the EA
    v = plots[plots.crop_area_ha > 0].assign(ea=lambda x: x.country.astype(str) + "|" + x.ea_id_obs.astype(str))
    vv = v.groupby(["ea", "country", "year"]).agg(usd=("harvest_value_USD", "sum"), ha=("crop_area_ha", "sum"),
                                                  n_hh=("household_id_obs", "nunique")).reset_index()
    vv = vv[vv.n_hh >= EA_MIN_HH]
    vv["log_value_ha"] = np.log(vv.usd / vv.ha).replace([-np.inf, np.inf], np.nan)
    vv["crop_name"] = "ALL"
    return pd.concat([g, vv[["ea", "country", "crop_name", "year", "n_hh", "log_value_ha"]]], ignore_index=True)


def ea_sums_job(job):
    """Weighted sums of log1p(travel time) over the cells within EA_RADIUS_KM of each EA point in one
    tile, with cropland weights (stable cropland km2; 0 where the land-use table is missing) and with
    equal weights; an EA whose disk spans several tiles gets its sums from each of them."""
    from scipy.spatial import cKDTree
    pts = pd.read_parquet(job["points"])
    w, s, e, n = job["bounds"]
    pad = EA_RADIUS_KM / 111.0 + 0.01
    pts = pts[pts.lon.between(w - pad, e + pad) & pts.lat.between(s - pad, n + pad)]
    if pts.empty:
        return None
    t = pd.read_parquet(job["treatment"])
    if t.empty:
        return None
    lu_f = Path(job["landuse"])
    crop = np.zeros(len(t))
    if lu_f.exists():
        lu = pd.read_parquet(lu_f)
        if "crop_stable_km2" in lu:
            crop = t[["cell"]].merge(lu[["cell", "crop_stable_km2"]], on="cell", how="left") \
                .crop_stable_km2.fillna(0).to_numpy(np.float64)
    c0 = math.cos(math.radians((s + n) / 2))
    tree = cKDTree(np.column_stack([t.lon.to_numpy() * c0, t.lat.to_numpy()]))
    hits = tree.query_ball_point(np.column_stack([pts.lon.to_numpy() * c0, pts.lat.to_numpy()]),
                                 EA_RADIUS_KM / 111.32)
    logtt = {c: np.log1p(t[c].to_numpy(np.float64)) for c in t.columns if c.startswith("tt_")}
    evs = {sp: (t[f"ev_{sp}"].to_numpy(), t[f"evclass_{sp}"].to_numpy()) for sp in spec_names(t.columns)}
    rows = []
    for uid, h in zip(pts.uid, hits):
        if not h:
            continue
        h = np.asarray(h)
        for wname, ww in (("cropland", crop[h]), ("equal", np.ones(len(h)))):
            rec = {"uid": uid, "weight": wname, "w": ww.sum()}
            for c, v in logtt.items():
                rec[f"s_{c}"] = float((ww * v[h]).sum())
            for sp, (ev, cls) in evs.items():
                eh, ch = ev[h], cls[h]
                for y in np.unique(eh[eh > 0]):
                    rec[f"wev_{sp}_{y}"] = float((ww * (eh == y)).sum())
                    rec[f"wburst_{sp}_{y}"] = float((ww * ((eh == y) & (ch == 2))).sum())
            rows.append(rec)
    return pd.DataFrame(rows) if rows else None


def ea_panel(agg, pts, tr):
    """EA x crop rows with the treatment columns of estimate_effects.R."""
    d = agg.merge(pts[["ea", "uid", "lat", "lon"]], on="ea").merge(tr, on="uid")
    d["crop"] = d.crop_name.astype(str)
    d["id"] = pd.factorize(d.ea + "|" + d.crop)[0] + 1
    d["region"] = d.country.astype(str)
    d["w"] = d.get("n_plots", pd.Series(1.0, index=d.index)).fillna(1.0).astype(float)
    keep = ["id", "uid", "ea", "country", "crop", "year", "log_yield", "log_value_ha", "n_hh", "n_plots", "fert",
            "improved", "hired", "sold", "region", "lat", "lon", "w"]
    keep += [c for c in d.columns if c.startswith("share_") or c in ("shannon", "n_crops")]
    out = d[[c for c in dict.fromkeys(keep) if c in d]].copy()
    # survey waves are irregular: the cohort is the first survey year at or after the event (DiD needs the
    # cohort among the observed periods); an event after the last wave of the EA is not treated in its panel
    waves = out.groupby("country").year.apply(lambda x: np.sort(x.unique())).to_dict()
    for sp in spec_names(tr.columns):
        g, dose = cohort_dose(d, sp)
        gw = np.array([0 if gi <= 0 else next((int(w) for w in waves[c] if w >= gi), 0)
                       for gi, c in zip(g, out.country)], np.int32)
        burst = d[f"evclass_{sp}"].to_numpy() == 2
        out[f"g__{sp}"] = np.where(burst, -1, gw).astype(np.int32)
        out[f"gburst__{sp}"] = np.where(burst, gw, 0).astype(np.int32)
        out[f"dose__{sp}"] = dose
        first = out.groupby("id").year.transform("min")
        last = out.groupby("id").year.transform("max")
        out.loc[(out[f"g__{sp}"] > 0) & (out[f"g__{sp}"] <= first), f"g__{sp}"] = -1
        for c in (f"g__{sp}", f"gburst__{sp}"):
            out.loc[out[c] > last, c] = 0
    return out


def stage_lsms(ctx):
    inv = lsms_inventory(ctx)
    if len(inv):
        inv.drop(columns=["data_path", "dict_path"], errors="ignore").to_csv(
            ctx["results"] / "tables" / "lsms_inventory.csv", index=False)
    sess = session()
    try:
        plots = lsms_plots(ctx, sess)
    except (RemoteUnavailable, ImportError) as e:
        log(f"lsms: harmonised panel not available ({str(e)[:200]}); E2b skipped")
        return {"ea": 0}
    pts = ea_points(plots)
    pf = ctx["work"] / "lsms" / "ea_points.parquet"
    write_parquet(pts, pf)
    jobs = []
    for t in ctx["tiles"]:
        tf = ctx["work"] / "treatment" / f"{t['tile']}.parquet"
        if tf.exists():
            jobs.append({"tile": t["tile"], "treatment": str(tf), "points": str(pf),
                         "bounds": (t["w"], t["s"], t["e"], t["n"]),
                         "landuse": str(ctx["work"] / "landuse" / f"{t['tile']}.parquet")})
    parts = [p for p in run_parallel(ea_sums_job, jobs, 3e9, "EA treatment") if p is not None]
    if not parts:
        log("lsms: no EA point inside the treatment tiles")
        return {"ea": 0}
    sums = pd.concat(parts, ignore_index=True).fillna(0)
    weight = "cropland"
    tr = unit_treatment(sums, "cropland", fallback="equal")     # equal weights where no cropland around the EA
    write_parquet(tr, ctx["work"] / "lsms" / "ea_treatment.parquet")     # reused by stage cropmix
    agg = ea_aggregate(plots)
    panel = ea_panel(agg, pts, tr)
    write_parquet(panel, ctx["work"] / "panels_parts" / "e2b_ea.parquet")
    inter = ea_panel(ea_aggregate(plots, intercropped=True), pts, tr)
    write_parquet(inter, ctx["work"] / "lsms" / "e2b_ea_intercropped.parquet")
    ld = ea_longdiff(panel, tr)
    if not ld.empty:
        write_parquet(ld, ctx["work"] / "panels_parts" / "e3_ea.parquet")
    log(f"lsms: {panel.ea.nunique():,} EAs, {panel.id.nunique():,} EA-crop series, {len(panel):,} rows "
        f"(weights {weight}); intercropped kept apart ({len(inter):,} rows)")
    return {"ea": int(panel.ea.nunique()), "rows": len(panel), "weight": weight}


def ea_longdiff(panel, tr):
    """E3 for EAs: consecutive-wave differences of log yield of each EA x crop against the access gain
    between the two survey years (reference years nearest to them, within LONG_EPOCH_TOL)."""
    p = panel.sort_values(["id", "year"])
    nxt = p.groupby("id")[["year", "log_yield"]].shift(-1)
    d = p.assign(y1=nxt.year, ly1=nxt.log_yield).dropna(subset=["y1", "ly1", "log_yield"])
    if d.empty:
        return pd.DataFrame()
    out = pd.DataFrame({"dataset": "E2b_ea", "crop": d.crop.to_numpy(), "id": d.id.to_numpy(),
                        "lat": d.lat.to_numpy(), "lon": d.lon.to_numpy(), "region": d.region.to_numpy(),
                        "w": d.w.to_numpy(),
                        "epoch": d.year.astype(int).astype(str).to_numpy() + "-" + d.y1.astype(int).astype(str).to_numpy(),
                        "d_log_yield": (d.ly1 - d.log_yield).to_numpy()})
    trx = tr.set_index("uid")
    for sp in spec_names(tr.columns):
        ys = tt_years(tr.columns, sp)
        vals = []
        for u, y0, y1 in zip(d.uid, d.year, d.y1):
            ya, yb = nearest_year(ys, int(y0), LONG_EPOCH_TOL), nearest_year(ys, int(y1), LONG_EPOCH_TOL)
            if ya is None or yb is None:
                vals.append(np.nan)
            elif ya == yb:
                vals.append(0.0)       # both surveys between the same reference years: no measured change
            else:
                vals.append(-(np.log1p(trx.at[u, f"tt_{sp}_{yb}"]) - np.log1p(trx.at[u, f"tt_{sp}_{ya}"])))
        out[f"d_access__{sp}"] = np.asarray(vals, np.float32)
    return out


# =============================================================================
# stage cropmix (E2e): crop composition per admin unit x year and EA x wave
# =============================================================================
CROP_GROUPS = [  # (group, regex on the lower-case crop name); first match wins; recalled crop vocabularies
    ("maize", r"maize|corn"),
    ("cassava", r"cassava|manioc"),
    ("rice", r"rice|paddy"),
    ("sorghum_millet", r"sorghum|millet"),
    ("cash", r"coffee|cocoa|cacao|tea\b|cotton|tobacco|sugar|cashew|palm|rubber|sesame|vanilla|clove|coconut"),
    ("staples_other", r"wheat|barley|teff|yam|potato|cocoyam|taro|plantain|banana|bean|cowpea|groundnut|"
                      r"peanut|soy|pea\b|peas|lentil|chickpea|pigeon"),
]


def crop_group(names):
    low = pd.Series(names, dtype=object).astype(str).str.lower()
    out = pd.Series("other", index=low.index, dtype=object)
    for g, rx in reversed(CROP_GROUPS):          # reversed + overwrite = first match wins
        out[low.str.contains(rx, regex=True, na=False)] = g
    return out.to_numpy()


def composition(area, unit_cols):
    """Shares by crop group, Shannon diversity and crop count from crop areas (columns unit_cols + crop +
    area): one row per unit."""
    a = area[area.area > 0].copy()
    a["group"] = crop_group(a.crop)
    tot = a.groupby(unit_cols).area.transform("sum")
    a["p"] = a.area / tot
    sh = a.groupby(unit_cols).p.apply(lambda p: float(-(p * np.log(p)).sum())).rename("shannon")
    n = a.groupby(unit_cols).crop.nunique().rename("n_crops")
    g = a.pivot_table(index=unit_cols, columns="group", values="p", aggfunc="sum", fill_value=0.0)
    g.columns = [f"share_{c}" for c in g.columns]
    for grp, _ in CROP_GROUPS + [("other", "")]:
        if f"share_{grp}" not in g:
            g[f"share_{grp}"] = 0.0
    return g.join(sh).join(n).reset_index()


def admin_crop_areas(hv):
    """HarvestStat harvested area per unit x year x crop (seasons and systems summed), on each unit's fixed
    crop set: the crops it reports in >= CROPMIX_MIN_REPORT of its years; years missing any of them dropped."""
    hv = hv[(hv.qc_flag == 0) & (hv.area > 0) & hv.harvest_year.notna()]
    a = hv.groupby(["fnid", "harvest_year", "product"], as_index=False).area.sum() \
        .rename(columns={"harvest_year": "year", "product": "crop"})
    a["year"] = a.year.astype(int)
    ny = a.groupby("fnid").year.nunique().rename("ny")
    rep = a.groupby(["fnid", "crop"]).year.nunique().rename("nrep").reset_index().join(ny, on="fnid")
    fixed = rep[rep.nrep >= CROPMIX_MIN_REPORT * rep.ny][["fnid", "crop"]]
    a = a.merge(fixed, on=["fnid", "crop"])
    need = fixed.groupby("fnid").crop.nunique().rename("need")
    have = a.groupby(["fnid", "year"]).crop.nunique().rename("have").reset_index().join(need, on="fnid")
    full = have[have.have == have.need][["fnid", "year"]]
    return a.merge(full, on=["fnid", "year"])


def stage_cropmix(ctx):
    work, out_parts = ctx["work"], ctx["work"] / "panels_parts"
    info = {}
    # admin units (HarvestStat), with the unit treatment of stage admin
    uf = work / "admin" / "units.gpkg"
    trf = sorted((work / "admin").glob("unit_treatment_*.parquet")) if (work / "admin").exists() else []
    trf = [f for f in trf if f.stem.endswith(ADMIN_WEIGHT)] or trf
    csv = ctx["dl"] / "harveststat" / Path(HARVESTSTAT_CSV_URL).name
    if uf.exists() and trf and csv.exists():
        units = gpd.read_file(uf, ignore_geometry=True)
        tr = pd.read_parquet(trf[0])
        comp = composition(admin_crop_areas(pd.read_csv(csv, low_memory=False)), ["fnid", "year"])
        d = comp.merge(units[["fnid", "uid", "lat", "lon", "country_code"]], on="fnid").merge(tr, on="uid")
        d["id"] = pd.factorize(d.fnid)[0] + 1
        d["region"] = d.country_code.astype(str)
        d["w"] = 1.0
        cols = ["id", "fnid", "year", "region", "lat", "lon", "w", "shannon", "n_crops"] + \
            [c for c in d.columns if c.startswith("share_")]
        panel = unit_year_treatment(d[cols].copy(), d, spec_names(tr.columns))
        write_parquet(panel, out_parts / "e2e_admin.parquet")
        info["admin_units"] = int(panel.id.nunique())
        log(f"cropmix: {panel.id.nunique():,} admin units, {len(panel):,} unit-years")
    else:
        log("cropmix: admin composition skipped (stage admin outputs not found)")
    # enumeration areas (LSMS-ISA harmonised panel), with the EA treatment of stage lsms
    pf, tf, pts_f = work / "lsms" / "plotcrop.parquet", work / "lsms" / "ea_treatment.parquet", work / "lsms" / "ea_points.parquet"
    if pf.exists() and tf.exists() and pts_f.exists():
        plots = pd.read_parquet(pf)
        plots = plots[plots.crop_area_ha > 0].copy()
        plots["ea"] = plots.country.astype(str) + "|" + plots.ea_id_obs.astype(str)
        area = plots.groupby(["ea", "country", "year", "crop_name"], as_index=False).crop_area_ha.sum() \
            .rename(columns={"crop_name": "crop", "crop_area_ha": "area"})
        comp = composition(area, ["ea", "country", "year"])
        hh = plots.groupby(["ea", "year"]).agg(n_hh=("household_id_obs", "nunique"),
                                               share_sold=("share_kg_sold", "mean")).reset_index()
        comp = comp.merge(hh, on=["ea", "year"])
        comp = comp[comp.n_hh >= EA_MIN_HH]
        comp["crop_name"] = "MIX"
        panel = ea_panel(comp, pd.read_parquet(pts_f), pd.read_parquet(tf))
        write_parquet(panel, out_parts / "e2e_ea.parquet")
        info["ea"] = int(panel.ea.nunique())
        log(f"cropmix: {panel.ea.nunique():,} EAs, {len(panel):,} EA-waves")
    else:
        log("cropmix: EA composition skipped (stage lsms outputs not found)")
    return info


# =============================================================================
# stage panels: analysis files for estimate_effects.R
# =============================================================================
def spec_names(cols):
    """Treatment specifications <version>_<layer> present in a treatment table."""
    return [c[3:] for c in cols if c.startswith("ev_")]


def nearest_year(years, y, tol):
    """The available year nearest to y within tol years (ties: the earlier), or None."""
    cand = [v for v in years if abs(v - y) <= tol]
    return min(cand, key=lambda v: (abs(v - y), v)) if cand else None


def tt_years(cols, spec):
    return sorted(int(c.rsplit("_", 1)[1]) for c in cols if c.startswith(f"tt_{spec}_"))


def cohort_dose(t, spec):
    """(g, dose): cohort year (0 = never) and access gain -(log tt change) from the reference year before
    the event to the last reference year (0 for the never-treated), per cell."""
    g = t[f"ev_{spec}"].to_numpy(np.int32)
    ys = tt_years(t.columns, spec)
    last = np.log1p(t[f"tt_{spec}_{ys[-1]}"].to_numpy(np.float64))
    before = np.full(len(t), np.nan)
    for i, y in enumerate(ys[1:], 1):
        m = g == y + EVENT_YEAR_SHIFT
        before[m] = np.log1p(t.loc[m, f"tt_{spec}_{ys[i - 1]}"].to_numpy(np.float64))
    dose = np.where(g > 0, before - last, 0.0)
    return g, dose.astype(np.float32)


def bands(t, spec, g):
    """Spatial-band status: 1 treated (event cell within BAND_TREATED_KM of a road change of its event
    reference year), 0 control (never-treated, nearest road change of every year within BAND_CONTROL_KM),
    NaN otherwise."""
    dcols = sorted(c for c in t.columns if c.startswith("dnew_"))
    out = np.full(len(t), np.nan, np.float32)
    if not dcols:
        return out
    dmin = t[dcols].min(axis=1).to_numpy()
    for c in dcols:
        y = int(c.split("_")[1])
        m = (g == y + EVENT_YEAR_SHIFT) & (t[c].to_numpy() <= BAND_TREATED_KM)
        out[m] = 1
    ctrl = (g == 0) & (dmin >= BAND_CONTROL_KM[0]) & (dmin <= BAND_CONTROL_KM[1])
    out[ctrl] = 0
    return out


def sample_cells(df, treated, n_treated, n_control, rng):
    """Stratified sample of one tile: up to n_treated treated and n_control never-treated cells,
    with sampling weights (inverse inclusion probability)."""
    idx_t, idx_c = np.flatnonzero(treated), np.flatnonzero(~treated)
    pick_t = rng.choice(idx_t, min(n_treated, len(idx_t)), replace=False) if len(idx_t) else idx_t
    pick_c = rng.choice(idx_c, min(n_control, len(idx_c)), replace=False) if len(idx_c) else idx_c
    w = np.concatenate([np.full(len(pick_t), len(idx_t) / max(len(pick_t), 1)),
                        np.full(len(pick_c), len(idx_c) / max(len(pick_c), 1))])
    out = df.iloc[np.concatenate([pick_t, pick_c])].copy()
    out["w"] = w.astype(np.float32)
    return out


def panel_tile_job(job):
    """One tile -> the sampled cells of E1 (wide: one row per cell), from the treatment, land-use and
    covariate tables of the tile."""
    t = pd.read_parquet(job["treatment"])
    if t.empty:
        return None
    lu_f = Path(job["landuse"])
    if not lu_f.exists():
        return None
    t = t.merge(pd.read_parquet(lu_f), on="cell", how="inner")
    cov_f = Path(job["covariates"])
    if cov_f.exists():
        t = t.merge(pd.read_parquet(cov_f), on="cell", how="left")
    t = t[t["forest2000_km2"] >= E1_FOREST_MIN_KM2]
    if t.empty:
        return None
    prim = job["primary"]
    g, _ = cohort_dose(t, prim)
    rng = np.random.default_rng([SEED, job["seed"]])
    s = sample_cells(t.reset_index(drop=True), g > 0, job["n_treated"], job["n_control"], rng)
    s["tile"] = job["tile"]
    return s


def e1_long(s, loss_years):
    """Wide sampled cells -> long cell-year panel of E1 outcomes and treatment columns."""
    specs = spec_names(s.columns)
    base = {"id": s["cell"].to_numpy(np.int64), "lat": s["lat"].to_numpy(), "lon": s["lon"].to_numpy(),
            "region": s["iso3"].to_numpy() if "iso3" in s else s["cid"].astype(str).to_numpy(),
            "w": s["w"].to_numpy(np.float32), "tile": s["tile"].to_numpy()}
    if "w_cem" in s:
        base["w_cem"] = s["w_cem"].to_numpy(np.float32)
    for sp in specs:
        g, dose = cohort_dose(s, sp)
        base[f"g__{sp}"] = g
        base[f"dose__{sp}"] = dose
        cls = s.get(f"evclass_{sp}")
        if cls is not None:
            base[f"gburst__{sp}"] = np.where(cls.to_numpy() == 2, g, 0).astype(np.int32)
            # the burst events are placebo events, not treatment: cells whose only event is a burst
            # leave the treated group of the main design
            base[f"g__{sp}"] = np.where(cls.to_numpy() == 2, -1, g).astype(np.int32)
        base[f"band__{sp}"] = bands(s, sp, g)
    forest = s["forest2000_km2"].to_numpy(np.float64)
    cum = np.zeros(len(s))
    parts = []
    for y in loss_years:
        loss = s.get(f"loss_km2_{y}", pd.Series(np.zeros(len(s)))).to_numpy(np.float64)
        conv = s.get(f"conv_km2_{y}", pd.Series(np.full(len(s), np.nan))).to_numpy(np.float64)
        newc = s.get(f"newcrop_km2_{y}", pd.Series(np.full(len(s), np.nan))).to_numpy(np.float64)
        rem = np.maximum(forest - cum, 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            d = dict(base, year=np.full(len(s), y, np.int32),
                     forest_rem_km2=rem.astype(np.float32),
                     loss_share=np.where(rem > 0, loss / rem, np.nan).astype(np.float32),
                     conv_share=np.where(rem > 0, conv / rem, np.nan).astype(np.float32),
                     newcrop_share=(newc / s["area_km2"].to_numpy()).astype(np.float32))
        if f"rain_{y}" in s:
            d["rain"] = s[f"rain_{y}"].to_numpy(np.float32)
        if f"conflict_{y}" in s:
            d["conflict"] = s[f"conflict_{y}"].to_numpy(np.float32)
        parts.append(pd.DataFrame(d))
        cum += loss
    out = pd.concat(parts, ignore_index=True)
    # cells treated before the first outcome year are always treated: no comparison possible.
    # g = -1 marks cells left out of a specification (estimate_effects.R drops them per specification)
    for sp in specs:
        out.loc[(out[f"g__{sp}"] > 0) & (out[f"g__{sp}"] <= loss_years[0]), f"g__{sp}"] = -1
        for c in (f"g__{sp}", f"gburst__{sp}"):
            if c in out:
                out.loc[out[c] > loss_years[-1], c] = 0     # treated after the window: not yet treated
    return out


def cem_weights(s, treated, cols, bins=5):
    """Coarsened exact matching: strata from quantile bins of cols; controls in strata holding treated
    cells get weight (treated / controls in the stratum) x their sampling weight; unmatched -> NaN."""
    key = np.zeros(len(s), np.int64)
    for c in cols:
        v = s[c].to_numpy(np.float64)
        ok = np.isfinite(v)
        q = np.unique(np.nanquantile(v[ok], np.linspace(0, 1, bins + 1)[1:-1])) if ok.any() else []
        b = np.where(ok, np.searchsorted(q, v, side="right"), bins)
        key = key * (bins + 1) + b
    df = pd.DataFrame({"k": key, "t": treated, "w": s["w"].to_numpy()})
    st = df.groupby("k").agg(nt=("t", "sum"), nc=("t", lambda x: (~x).sum()))
    df = df.join(st, on="k")
    w = np.where(df.t & (df.nc > 0), df.w,
                 np.where(~df.t & (df.nt > 0), df.w * df.nt / np.maximum(df.nc, 1), np.nan))
    return w.astype(np.float32), st


def e3_longdiff(s, epochs, loss_years):
    """Long differences per sampled cell and epoch: access gain -(d log tt) per specification and the
    outcomes summed over the epoch relative to the forest at its start."""
    rows = []
    specs = spec_names(s.columns)
    forest = s["forest2000_km2"].to_numpy(np.float64)
    for a, b in epochs:
        d = {"id": s["cell"].to_numpy(np.int64), "lat": s["lat"].to_numpy(), "lon": s["lon"].to_numpy(),
             "region": s["iso3"].to_numpy() if "iso3" in s else s["cid"].astype(str).to_numpy(),
             "w": s["w"].to_numpy(np.float32), "epoch": f"{a}-{b}"}
        ok_any = False
        for sp in specs:
            ys = tt_years(s.columns, sp)
            ya, yb = nearest_year(ys, a, LONG_EPOCH_TOL), nearest_year(ys, b, LONG_EPOCH_TOL)
            if ya is None or yb is None or ya >= yb:
                continue
            ok_any = True
            d[f"d_access__{sp}"] = -(np.log1p(s[f"tt_{sp}_{yb}"].to_numpy(np.float64))
                                     - np.log1p(s[f"tt_{sp}_{ya}"].to_numpy(np.float64))).astype(np.float32)
        if not ok_any:
            continue
        before = [y for y in loss_years if y <= a]
        during = [y for y in loss_years if a < y <= b]
        if not during:
            continue
        rem = forest - sum(s.get(f"loss_km2_{y}", 0) for y in before)
        rem = np.maximum(np.asarray(rem, np.float64), 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            for name, col in (("loss_share", "loss_km2"), ("conv_share", "conv_km2")):
                tot = sum(s[f"{col}_{y}"].to_numpy(np.float64) for y in during if f"{col}_{y}" in s)
                d[f"d_{name}"] = np.where(rem > 0, np.asarray(tot) / rem, np.nan).astype(np.float32) \
                    if not np.isscalar(tot) else np.full(len(s), np.nan, np.float32)
        ra = [f"rain_{y}" for y in range(a - 2, a + 1) if f"rain_{y}" in s]
        rb = [f"rain_{y}" for y in range(b - 2, b + 1) if f"rain_{y}" in s]
        if ra and rb:
            d["d_rain"] = (s[rb].mean(axis=1) - s[ra].mean(axis=1)).to_numpy(np.float32)
        pa_, pb_ = nearest_year(POP_EPOCHS_IN(s), a, 3), nearest_year(POP_EPOCHS_IN(s), b, 3)
        if pa_ and pb_ and pa_ < pb_:
            d["d_logpop"] = (np.log1p(s[f"pop_{pb_}"]) - np.log1p(s[f"pop_{pa_}"])).to_numpy(np.float32)
        rows.append(pd.DataFrame(d))
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not out.empty:
        out.insert(0, "dataset", "E1_cells")
        out.insert(1, "crop", pd.Series([None] * len(out), dtype=object))
    return out


def POP_EPOCHS_IN(s):
    return sorted(int(c.split("_")[1]) for c in s.columns if re.fullmatch(r"pop_\d{4}", c))


def stage_panels(ctx):
    work, res = ctx["work"], ctx["results"]
    pdir = res / "panels"
    pdir.mkdir(parents=True, exist_ok=True)
    specs_avail = None
    jobs = []
    nt = max(1, E1_SAMPLE_TREATED // max(len(ctx["tiles"]), 1))
    nc = max(1, E1_SAMPLE_CONTROL // max(len(ctx["tiles"]), 1))
    for i, t in enumerate(ctx["tiles"]):
        tf = work / "treatment" / f"{t['tile']}.parquet"
        if not tf.exists():
            continue
        if specs_avail is None:
            specs_avail = spec_names(pq.read_schema(tf).names)
        jobs.append({"tile": t["tile"], "seed": i, "treatment": str(tf),
                     "landuse": str(work / "landuse" / f"{t['tile']}.parquet"),
                     "covariates": str(work / "covariates" / f"{t['tile']}.parquet"),
                     "primary": PRIMARY_SPEC if PRIMARY_SPEC in (specs_avail or []) else (specs_avail or [None])[0],
                     "n_treated": nt, "n_control": nc})
    if not jobs:
        raise RuntimeError("panels: no treatment tables; run stage treatment first")
    parts = [p for p in run_parallel(panel_tile_job, jobs, 3e9, "panel tiles") if p is not None]
    if not parts:
        log("panels: no cell has land-use data with forest at baseline; E1 and E3 cell panels skipped")
        return {"e1_cells": 0}
    s = pd.concat(parts, ignore_index=True)
    _, countries = ssa_country_ids(ctx["store"])
    s["iso3"] = s["cid"].map(dict(zip(countries.cid, countries.iso3))).fillna("NA")
    prim = jobs[0]["primary"]
    if prim != PRIMARY_SPEC:
        log(f"WARNING: {PRIMARY_SPEC} is not in the treatment tables (the travel-time store has no road-only "
            f"layers); the panels use {prim} as primary. Add road-only travel time with "
            "global_accessibility_v3.py >= 3.3 (stage roadonly), then delete ae_work/_done/treatment and rerun")
    g, _ = cohort_dose(s, prim)
    match_cols = [c for c in (f"tt_{prim}_{tt_years(s.columns, prim)[0]}", f"pop_{POP_EPOCHS_IN(s)[0]}"
                              if POP_EPOCHS_IN(s) else None, "tan_slope", "forest2000_km2", "loss_pre_km2",
                              "rain_mean") if c and c in s]
    s["w_cem"], strata = cem_weights(s, g > 0, match_cols)
    balance = smd_table(s, g > 0, match_cols)
    balance.to_csv(res / "tables" / "e1_matching_balance.csv", index=False)
    loss_years = sorted(int(c.rsplit("_", 1)[1]) for c in s.columns if c.startswith("loss_km2_"))
    e1 = e1_long(s, loss_years)
    write_parquet(e1, pdir / "e1_cells.parquet")
    e3 = e3_longdiff(s, LONG_EPOCHS, loss_years)
    for extra in ("e3_admin.parquet", "e3_ea.parquet"):     # long differences of E2a / E2b (stages admin, lsms)
        f = work / "panels_parts" / extra
        if f.exists():
            e3 = pd.concat([e3, pd.read_parquet(f)], ignore_index=True)
    if not e3.empty:
        write_parquet(e3, pdir / "e3_longdiff.parquet")
    for name in ("e2a_admin", "e2b_ea", "e2e_admin", "e2e_ea", "e1c_replacement", "e2d_vigour"):
        f = work / "panels_parts" / f"{name}.parquet"
        if f.exists():
            shutil.copy(f, pdir / f"{name}.parquet")
    info = {"e1_cells": int(e1.id.nunique()), "e1_rows": len(e1), "e3_rows": len(e3), "primary_spec": prim,
            "treated": int((g > 0).sum()), "matching_strata": int(len(strata))}
    (res / "tables" / "panels_summary.json").write_text(json.dumps(info, indent=1))
    log(f"panels: {info}")
    return info


def smd_table(s, treated, cols):
    """Standardised mean differences treated vs controls, before and after the CEM weights."""
    rows = []
    for c in cols:
        v = s[c].to_numpy(np.float64)
        ok = np.isfinite(v)
        t, k = ok & treated, ok & ~treated
        sd = np.sqrt((np.nanvar(v[t]) + np.nanvar(v[k])) / 2) or np.nan
        wc = s["w_cem"].to_numpy(np.float64)
        km = k & np.isfinite(wc)
        tm = t & np.isfinite(wc)
        mt = np.average(v[tm], weights=wc[tm]) if tm.any() else np.nan
        mc = np.average(v[km], weights=wc[km]) if km.any() else np.nan
        rows.append({"variable": c, "smd_raw": (np.nanmean(v[t]) - np.nanmean(v[k])) / sd,
                     "smd_matched": (mt - mc) / sd,
                     "passes": abs((mt - mc) / sd) < MATCH_SMD_MAX if np.isfinite(mt - mc) else False})
    return pd.DataFrame(rows)


# =============================================================================
# stages estimate and gate_c
# =============================================================================
R_PACKAGES = ["dplyr", "tidyr", "readr", "purrr", "tibble", "stringr", "jsonlite", "fixest", "did",
              "nanoparquet", "contdid"]


def find_r_script():
    for p in (Path(__file__).resolve().parent / "estimate_effects.R", Path.cwd() / "estimate_effects.R"):
        if p.exists():
            return p
    return None


def r_missing_packages(rscript):
    code = ("p <- c(" + ",".join(f'"{x}"' for x in R_PACKAGES) + "); "
            "cat(p[!vapply(p, requireNamespace, logical(1), quietly = TRUE)], sep = '\\n')")
    r = subprocess.run([rscript, "-e", code], capture_output=True, text=True, timeout=300)
    return [x for x in r.stdout.split() if x]


def stage_estimate(ctx):
    rscript = shutil.which(RSCRIPT) or (RSCRIPT if Path(RSCRIPT).exists() else None)
    script = find_r_script()
    if rscript is None or script is None:
        raise RuntimeError(f"stage estimate needs Rscript ({RSCRIPT}) and estimate_effects.R next to this "
                           "script; or run it by hand: Rscript estimate_effects.R <RESULTS_DIR>/panels "
                           "<RESULTS_DIR>/estimates")
    miss = r_missing_packages(rscript)
    if miss:
        required = [m for m in miss if m != "contdid"]
        if required:
            raise RuntimeError(f"R packages missing: {required}. In R: install.packages(c("
                               + ", ".join(f'"{m}"' for m in required) + "))")
        log("R package contdid missing: the continuous-dose design is skipped (install.packages('contdid'))")
    out = ctx["results"] / "estimates"
    out.mkdir(parents=True, exist_ok=True)
    prim = PRIMARY_SPEC
    sf = ctx["results"] / "tables" / "panels_summary.json"
    if sf.exists():
        prim = json.loads(sf.read_text()).get("primary_spec") or PRIMARY_SPEC
    if prim != PRIMARY_SPEC:
        log(f"WARNING: primary specification {PRIMARY_SPEC} is not in the panels; {prim} is used instead "
            "(road-only travel time missing from the store? run global_accessibility_v3.py >= 3.3 stage roadonly)")
    specs = [prim] + [x for x in ESTIMATE_SPECS if x != prim]
    cfg = {"primary_spec": prim, "specs": specs, "min_e": EVENT_WINDOW[0],
           "max_e": EVENT_WINDOW[1], "conley_km": CONLEY_KM, "bh_q": BH_Q, "seed": SEED,
           "bootstrap_iters": BOOTSTRAP_ITERS, "max_units_cs": MAX_UNITS_CS,
           "composite_shift": COMPOSITE_SHIFT, "gate_v_r": GATE_V_R, "gate_v_min_n": GATE_V_MIN_N,
           "gate_v_r_sensor": GATE_V_R_SENSOR}
    cf_ = out / "config.json"
    cf_.write_text(json.dumps(cfg, indent=1))
    log(f"estimate: {rscript} {script}")
    with open(out / "estimate_log.txt", "w") as fh:
        r = subprocess.run([rscript, str(script), str(ctx["results"] / "panels"), str(out), str(cf_)],
                           stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        tail = (out / "estimate_log.txt").read_text()[-1500:]
        raise RuntimeError(f"estimate_effects.R failed ({r.returncode}):\n{tail}")
    est = pd.read_csv(out / "estimates.csv")
    failed = est[est.error.notna()] if "error" in est else est.iloc[0:0]
    log(f"estimate: {len(est)} coefficients, {len(failed)} models failed (see estimates.csv, column error)")
    return {"coefficients": len(est), "failed_models": len(failed)}


def stage_gate_c(ctx):
    f = ctx["results"] / "estimates" / "gate_c.csv"
    if not f.exists():
        raise RuntimeError("gate_c.csv not found: run stage estimate first")
    g = pd.read_csv(f)
    if g.empty:
        log("gate_c: no results")
        return {"rows": 0}
    summary = g.groupby("dataset").agg(results=("outcome", "size"), causal=("causal", "sum"),
                                       significant_bh=("significant_bh", "sum")).reset_index()
    summary.to_csv(ctx["results"] / "tables" / "gate_c_summary.csv", index=False)
    log("gate_c:\n" + summary.to_string(index=False))
    return {"rows": len(g), "causal": int(g.causal.sum())}


# =============================================================================
# access check and dry run
# =============================================================================
def access_targets():
    """(url, purpose, required) of every remote resource, one sample file each."""
    y = max(COV_YEARS)
    t = [(CHIRPS_ANNUAL_URL.format(y=y), "rainfall (CHIRPS v3)", True),
         (UCDP_GED_URL, "conflict (UCDP GED)", True),
         (GCDF_URL, "dated road projects (AidData GeoGCDF v3)", False),
         (HARVESTSTAT_CSV_URL, "admin yields (HarvestStat Africa)", False),
         (HARVESTSTAT_GPKG_URL, "admin units (HarvestStat Africa)", False)]
    t += [(u, p, r) for u, p, r in landuse_targets()]
    return t


def probe(url, sess, tries=3):
    """(HTTP status, bytes, error) of the first 2 KB of url; 403/429/5xx and network errors are retried
    (a server answered 403 once and 206 a few seconds later in the tests)."""
    code, n, err = None, 0, ""
    for i in range(tries):
        try:
            r = sess.get(url, headers={"Range": "bytes=0-2047"}, stream=True, timeout=60, allow_redirects=True)
            n = len(next(r.iter_content(2048), b""))
            r.close()
            code, err = r.status_code, ""
            if code in (200, 206):
                break
        except Exception as e:
            code, n, err = None, 0, repr(e)[:200]
        time.sleep(3 * (i + 1))
    return code, n, err


def check_access(ctx):
    sess = session()
    rows = []
    with cf.ThreadPoolExecutor(8) as ex:
        for (url, purpose, req), (code, n, err) in zip(access_targets(), ex.map(lambda t: probe(t[0], sess),
                                                                                   access_targets())):
            ok = code in (200, 206) and n > 0
            rows.append({"purpose": purpose, "required": req, "ok": ok, "http": code, "bytes": n,
                         "url": url, "error": err})
            log(f"{'OK  ' if ok else 'FAIL'} {purpose}: {url} ({code}, {n} bytes) {err}")
    acled = bool(os.environ.get("ACLED_USERNAME") and os.environ.get("ACLED_PASSWORD"))
    log(f"ACLED credentials in the environment: {'yes' if acled else 'no (UCDP GED is used)'}")
    df = pd.DataFrame(rows)
    df.to_csv(ctx["results"] / "tables" / "access_check.csv", index=False)
    bad = df[~df.ok & df.required]
    if len(bad):
        log(f"{len(bad)} required resources are not reachable")
    return df


def dry_run(ctx):
    store = ctx["store"]
    series = treatment_plan(store)
    log(f"GA runs: {json.dumps(store.runs, default=str)}")
    for (v, l), (n, ys) in series.items():
        log(f"treatment series {v} {l}: {ys}")
    log(f"road events (OSM) for reference years: {store.years('road_events')}")
    log(f"tiles: {len(ctx['tiles'])} ({', '.join(t['tile'] for t in ctx['tiles'][:12])}"
        f"{' ...' if len(ctx['tiles']) > 12 else ''})")
    free = shutil.disk_usage(ctx["work"]).free
    log(f"free disk in the work folder: {free / 1e9:,.0f} GB; memory {available_memory() / 1e9:.0f} GB; "
        f"workers for 3 GB tasks: {plan_workers(3e9, len(ctx['tiles']))}")
    rscript = shutil.which(RSCRIPT)
    script = find_r_script()
    log(f"Rscript: {rscript or 'NOT FOUND'}; estimate_effects.R: {script or 'NOT FOUND'}")
    if rscript:
        miss = r_missing_packages(rscript)
        log(f"R packages missing: {miss or 'none'}")
    lsms = lsms_plan(ctx)
    log(f"LSMS: {lsms}")
    for s in STAGES:
        log(f"stage {s}: {'done' if stage_done(ctx, s) else 'to run'}")


# =============================================================================
# driver
# =============================================================================
STAGES = ["treatment", "landuse", "covariates", "projects", "gate_t", "admin", "lsms", "cropmix", "panels",
          "estimate", "gate_c"]


def make_ctx(work, results, bbox=None):
    work, results = Path(work).resolve(), Path(results).resolve()
    for d in (work, results / "tables", results / "logs"):
        d.mkdir(parents=True, exist_ok=True)
    store = Store(GA_RESULTS)
    tiles = analysis_tiles(store.grid, bbox or ANALYSIS_BBOX)
    return {"work": work, "results": results, "dl": work / "downloads", "store": store,
            "grid": store.grid, "tiles": tiles, "bbox": bbox or ANALYSIS_BBOX}


def stage_done(ctx, name):
    return (ctx["work"] / "_done" / name).exists()


def mark_done(ctx, name, info=None):
    (ctx["work"] / "_done").mkdir(parents=True, exist_ok=True)
    (ctx["work"] / "_done" / name).write_text(json.dumps(info or {}, default=str))


def run_stages(ctx, want):
    funcs = {s: globals()[f"stage_{s}"] for s in STAGES}
    for s in STAGES:
        if s not in want:
            continue
        if stage_done(ctx, s):
            log(f"stage {s}: done earlier (delete {ctx['work'] / '_done' / s} to rerun)")
            continue
        with Timer(f"stage {s}"):
            info = funcs[s](ctx)
        mark_done(ctx, s, info)


def write_run_record(ctx, ok, err=None):
    rec = {"script": f"access_effects_v01.py {__version__}", "ok": ok, "error": err,
           "finished": dt.datetime.now().isoformat(timespec="seconds"),
           "ga_runs": ctx["store"].runs if "store" in ctx else None,
           "config": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, str, list, tuple, dict, set, type(None)))
                      and not k.startswith("_")},
           "timings": Timer.rows, "downloads": MANIFEST}
    (ctx["results"] / "logs" / "run_record.json").write_text(json.dumps(rec, indent=1, default=str))
    (ctx["results"] / "logs" / "run_log.txt").write_text("\n".join(LOG) + "\n")


def main(argv=None):
    global GA_RESULTS, MAX_WORKERS
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--ga-results", nargs="+", default=GA_RESULTS)
    p.add_argument("--work-dir", default=WORK_DIR)
    p.add_argument("--results-dir", default=RESULTS_DIR)
    p.add_argument("--bbox", type=float, nargs=4, metavar=("W", "S", "E", "N"), default=None)
    p.add_argument("--stages", default=",".join(STAGES))
    p.add_argument("--max-workers", type=int, default=MAX_WORKERS)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--check-access", action="store_true")
    a = p.parse_args(argv)
    GA_RESULTS, MAX_WORKERS = list(a.ga_results), a.max_workers
    if a.check_access:      # needs no travel-time store: can run while global_accessibility_v3.py still runs
        res = Path(a.results_dir).resolve()
        (res / "tables").mkdir(parents=True, exist_ok=True)
        log(f"access_effects v{__version__}: access check")
        return check_access({"results": res})
    ctx = make_ctx(a.work_dir, a.results_dir, tuple(a.bbox) if a.bbox else None)
    log(f"access_effects v{__version__}: {len(ctx['tiles'])} tiles, GA runs "
        f"{[r['dir'] for r in ctx['store'].runs]}, cpus {cpu_count()}, memory {available_memory() / 1e9:.0f} GB")
    if a.dry_run:
        return dry_run(ctx)
    want = [s.strip() for s in a.stages.split(",") if s.strip()]
    bad = [s for s in want if s not in STAGES]
    if bad:
        raise SystemExit(f"unknown stages {bad}; stages are {STAGES}")
    try:
        run_stages(ctx, want)
        write_run_record(ctx, True)
        log("finished")
    except BaseException as e:
        log("FAILED:", repr(e))
        log(traceback.format_exc())
        write_run_record(ctx, False, repr(e))
        raise


if __name__ == "__main__":
    main()
