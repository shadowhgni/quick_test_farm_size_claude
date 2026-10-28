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

# @@DATA_CONFIG@@

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
import hashlib
import importlib
import importlib.metadata
import importlib.util
import io
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
import pyarrow as pa                                  # noqa: E402
import pyarrow.parquet as pq                          # noqa: E402
import rasterio                                       # noqa: E402
import requests                                       # noqa: E402
import shapely                                        # noqa: E402
from rasterio.enums import Resampling                 # noqa: E402
from rasterio.features import rasterize               # noqa: E402
from rasterio.transform import from_origin            # noqa: E402
from rasterio.warp import reproject                   # noqa: E402
from rasterio.windows import Window, from_bounds      # noqa: E402
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
# driver
# =============================================================================
STAGES = ["treatment", "landuse", "covariates", "projects", "gate_t", "admin", "lsms", "panels",
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
    ctx = make_ctx(a.work_dir, a.results_dir, tuple(a.bbox) if a.bbox else None)
    log(f"access_effects v{__version__}: {len(ctx['tiles'])} tiles, GA runs "
        f"{[r['dir'] for r in ctx['store'].runs]}, cpus {cpu_count()}, memory {available_memory() / 1e9:.0f} GB")
    if a.check_access:
        return check_access(ctx)
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
