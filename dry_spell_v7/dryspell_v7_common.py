#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dryspell_v7_common.py
=====================
Shared configuration and helpers for the v7 dry-spell pipeline:

  step1  2026-09-26.step1_dry_spell_extract_v07.py   CHIRPS -> fixed grid -> all dry spells
  step2  2026-09-26.step2_dry_spell_seasons_v07.py   RADS seasons x spells -> per-season + per-cell stats
  step3  2026-09-26.step3_bbox_zoning_v07.py         bbox masks + k-means zones (GeoTIFF / GPKG / PNG)

Keep this file in the same folder as the three scripts.

Design choices that fix the v6 problems
---------------------------------------
* ONE fixed 0.05 deg grid for the whole region; the per-country CHIRPS files are
  mosaicked onto it (no "first country wins" de-duplication, no country list that
  can forget MRT/SSD).
* CHIRPS no-data (-9999 / _FillValue / negative) is masked to NaN; NaN is never
  treated as a dry day. Missing days break spells.
* Spells are extracted on the continuous 1981-2025 daily series (no cut at 31 Dec).
* No length filter before the season clipping (the old ">60 days" filter is gone).
* Seasons use the full RADS onset/demise dates (year is kept), and RADS arrays are
  transposed by dimension NAME (lat, lon) - never assumed.
* Every blank pixel carries a reason code (see REASON_* below).
"""

import json
import logging
import re
from pathlib import Path

import numpy as np

logger = logging.getLogger("dryspell_v7")

# =============================================================================
# CONFIGURATION (edit here)
# =============================================================================

# ---- regions (lon_min, lat_min, lon_max, lat_max) -------------------------
REGIONS = {
    # West Africa + Cameroon/Chad/CAR/Sudan/South Sudan (study area)
    "study": (-18.0, 2.0, 38.7, 23.5),
    # Whole SSA extent used by the old scripts
    "ssa": (-18.0, -36.0, 52.0, 28.0),
}

# ---- inputs ----------------------------------------------------------------
# Per-country CHIRPS NetCDF files (all years, daily), e.g. chirps_SEN_1981_2025.nc.
# They are bbox crops of the same Africa grid and overlap; step1 mosaics them.
CHIRPS_COUNTRY_DIR = "chirps_data_cache"
CHIRPS_COUNTRY_REGEX = r"^chirps_([A-Z]{3})_(\d{4})_(\d{4})\.nc$"

RADS_DIRS = ["../chirps_africa", "chirps_africa"]
RADS_GLOB = "africa_RainyAndDry*.nc"

# Country boundaries (plots + optional clipping in step3). Local file first.
BOUNDARY_SOURCES = [
    "Spatial_data_repository/ne_50m_admin_0_countries.zip",
    "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip",
    "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip",
]

# ---- time --------------------------------------------------------------------
ORIGIN = np.datetime64("1981-01-01", "D")   # day index 0
DATA_YEAR_MIN = 1981                         # CHIRPS years read by step1
DATA_YEAR_MAX = 2025                         # (2025 is partial; only used if a season fits)
SEASON_YEAR_MIN = 1981                       # RADS season years analysed by step2
SEASON_YEAR_MAX = 2024                       # 2024 = last complete CHIRPS year

# ---- dry spell definitions --------------------------------------------------
DRY_MM = 1.0              # day is dry if rain < DRY_MM (NaN is NOT dry)
STEP1_MIN_SPELL = 5       # spells stored by step1 (>= 5 d)
MIN_SPELL = 10            # spells analysed by step2 (>= 10 d AFTER clipping)
EXCLUDE_FIRST_DAYS = 10   # season window starts at onset + 10  (onset = day 0)
EXCLUDE_LAST_DAYS = 10    # season window ends   at demise - 10
EDGE_POLICY = "clip"      # "clip": cut spells at the window edges | "exclude": drop them
X_DAYS = [20, 30, 40, 50, 60, 70, 80, 90]   # P(first spell starts <= X days after onset)
MAX_OFFSET = 250          # drought-probability-by-offset curve length (days after onset)

# ---- quality thresholds -----------------------------------------------------
MAX_MISSING_FRAC = 0.005      # cell invalid if > 0.5 % of days are missing
SEASON_LEN_MIN_SANITY = 15    # RADS season shorter than this = invalid season
SEASON_LEN_MAX_SANITY = 330   # longer than this = invalid season
ONSET_EARLIEST_REL = -183     # onset may be up to 183 d before 1 Jan of the RADS year
STEP2_MIN_SEASONS = 3         # step2 maps need >= 3 valid seasons

# ---- bimodality (Liebmann et al. 2012: ratio of 2nd/1st harmonic amplitude) --
BIMODAL_RATIO = 1.0           # >= this -> bimodal (tune by looking at the ratio map)

# ---- step3 (bbox zoning) ----------------------------------------------------
STEP3_MIN_SEASONS = 10
STEP3_MIN_SEASON_LEN = 60     # median season length (days) of the cell
STEP3_CLIP_ISO3 = [           # None -> keep the whole bbox
    "BEN", "BFA", "CIV", "GMB", "GHA", "GIN", "GNB", "LBR", "MLI", "MRT",
    "NER", "NGA", "SEN", "SLE", "TGO",            # West Africa
    "CMR", "TCD", "CAF", "SDN", "SSD",            # + central / Sudan
]
K_NB = 5                      # k for "median nb dry spells / season" zones
K_PROB = 5                    # k for "P(first spell <= X)" zones
K_SCAN = range(2, 11)         # elbow / silhouette diagnostics
SIEVE_PIXELS = 25             # merge zone patches smaller than this (pixels)

# ---- output --------------------------------------------------------------------
OUT_ROOT = "dryspell_v7"
ROWS_PER_TASK = 8             # grid rows per worker task (step1 & step2)

# ---- reason codes (why a pixel is blank) ------------------------------------
REASON_OK = 0
REASON_NO_CHIRPS = 1          # no rainfall data (ocean / outside CHIRPS)
REASON_MISSING = 2            # too many missing rainfall days
REASON_NO_RADS = 3            # RADS has no valid season at all for this cell
REASON_FEW_SEASONS = 4        # fewer than the minimum number of valid seasons
REASON_SHORT_SEASON = 5       # median season too short (step3)
REASON_BIMODAL = 6            # bimodal rainfall regime (step3, hidden for now)
REASON_OUTSIDE = 7            # outside the country clip (step3)
REASON_LABELS = {
    0: "ok", 1: "no CHIRPS data", 2: "missing rainfall days", 3: "no valid RADS season",
    4: "too few valid seasons", 5: "season too short", 6: "bimodal (hidden)",
    7: "outside study countries",
}

# season-level reason codes (step2 season table)
S_OK = 0
S_NO_RADS = 1          # onset or demise missing
S_BAD_LENGTH = 2       # demise <= onset or length outside sanity range
S_BAD_YEAR = 3         # onset far outside the RADS file year
S_NO_DATA = 4          # season not fully covered by rainfall data / year range
S_OVERLAP = 5          # duplicate of / overlaps the previous season
S_CELL_INVALID = 6     # cell has no or too-incomplete rainfall


# =============================================================================
# LOGGING / PATHS
# =============================================================================

def setup_logging(log_file=None):
    fmt = "%(asctime)s [%(processName)s] %(levelname)s - %(message)s"
    handlers = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, mode="a"))
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt="%H:%M:%S",
                        handlers=handlers, force=True)


def region_dir(region):
    return Path(OUT_ROOT) / region


def parse_region(region, bbox):
    """Return (name, bbox) from --region / --bbox CLI values."""
    if bbox:
        b = tuple(float(v) for v in bbox)
        if not (b[0] < b[2] and b[1] < b[3]):
            raise ValueError("--bbox must be lon_min lat_min lon_max lat_max")
        name = region if region not in REGIONS else f"bbox_{b[0]:g}_{b[1]:g}_{b[2]:g}_{b[3]:g}"
        return name, b
    return region, REGIONS[region]


# =============================================================================
# GRID
# =============================================================================

def day_index(dt64):
    """datetime64 -> int day index since ORIGIN (NaT -> -2**31)."""
    d = np.asarray(dt64).astype("datetime64[D]")
    out = (d - ORIGIN).astype(np.int64)
    out[np.isnat(d)] = np.iinfo(np.int32).min
    return out.astype(np.int32)


def index_to_date(idx):
    return ORIGIN + np.asarray(idx).astype("timedelta64[D]")


def regular_step(v):
    d = np.diff(np.asarray(v, dtype=np.float64))
    step = float(np.median(d))
    if not np.allclose(d, step, rtol=0, atol=abs(step) * 1e-3):
        raise ValueError("coordinate vector is not regular")
    return step


def grid_transform(lons, lats):
    """Affine for north-up raster built from ascending pixel-CENTRE vectors."""
    from rasterio.transform import from_origin
    dx = round(regular_step(lons), 8)
    dy = round(regular_step(lats), 8)
    return from_origin(lons.min() - dx / 2, lats.max() + dy / 2, dx, abs(dy))


def nearest_index(src, dst, tol):
    """For every value in dst, index of nearest value in src (any order) or -1."""
    src = np.asarray(src, dtype=np.float64)
    order = np.argsort(src)
    s = src[order]
    pos = np.clip(np.searchsorted(s, dst), 1, len(s) - 1)
    left, right = s[pos - 1], s[pos]
    pick = np.where(np.abs(dst - left) <= np.abs(dst - right), pos - 1, pos)
    idx = order[pick]
    idx[np.abs(src[idx] - dst) > tol] = -1
    return idx


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def find_chirps_country_files(bbox=None):
    """
    List per-country CHIRPS NetCDFs with their extent.
    Returns list of dicts {iso3, path, lon_min, lon_max, lat_min, lat_max, n_time}
    (only files intersecting bbox when given).
    """
    import xarray as xr
    rx = re.compile(CHIRPS_COUNTRY_REGEX)
    out = []
    for f in sorted(Path(CHIRPS_COUNTRY_DIR).glob("chirps_*.nc")):
        m = rx.match(f.name)
        if not m:
            continue
        with xr.open_dataset(f) as ds:
            latn, lonn = spatial_names(ds)
            la, lo = ds[latn].values, ds[lonn].values
            nt = ds.sizes.get("time", 0)
        rec = dict(iso3=m.group(1), path=f, lon_min=float(lo.min()), lon_max=float(lo.max()),
                   lat_min=float(la.min()), lat_max=float(la.max()), n_time=int(nt))
        if bbox is not None and (rec["lon_max"] < bbox[0] or rec["lon_min"] > bbox[2]
                                 or rec["lat_max"] < bbox[1] or rec["lat_min"] > bbox[3]):
            continue
        out.append(rec)
    return out


def find_rads_files():
    for d in RADS_DIRS:
        files = sorted(Path(d).glob(RADS_GLOB))
        if files:
            out = {}
            for f in files:
                m = re.search(r"\.((?:19|20)\d{2})\.nc$", f.name) or re.search(r"((?:19|20)\d{2})", f.name)
                if m:
                    out[int(m.group(1))] = f
            return out, Path(d)
    raise FileNotFoundError(f"No RADS files ({RADS_GLOB}) in {RADS_DIRS}")


def spatial_names(obj):
    """Return (lat_name, lon_name) of an xarray object."""
    names = list(obj.dims) + list(getattr(obj, "coords", {}))
    lat = next((n for n in names if n.lower() in ("lat", "latitude", "y")), None)
    lon = next((n for n in names if n.lower() in ("lon", "longitude", "x")), None)
    if lat is None or lon is None:
        raise KeyError(f"cannot find lat/lon in {names}")
    return lat, lon


# =============================================================================
# GEO OUTPUT
# =============================================================================

def save_geotiff(path, arr, lons, lats, nodata=np.nan, dtype=None, band_names=None):
    """arr: (lat, lon) or (band, lat, lon) with ASCENDING lats; written north-up."""
    import rasterio
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    a = np.asarray(arr)
    if a.ndim == 2:
        a = a[None]
    a = a[:, ::-1, :]                       # ascending lat -> north-up
    dtype = dtype or a.dtype
    profile = dict(driver="GTiff", height=a.shape[1], width=a.shape[2], count=a.shape[0],
                   dtype=dtype, crs="EPSG:4326", transform=grid_transform(lons, lats),
                   compress="deflate", tiled=True, blockxsize=256, blockysize=256,
                   nodata=nodata)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(a.astype(dtype))
        if band_names:
            for i, n in enumerate(band_names, 1):
                dst.set_band_description(i, str(n))


def load_boundaries(bbox=None):
    """Country polygons (GeoDataFrame with 'iso_a3') or None."""
    import geopandas as gpd
    for src in BOUNDARY_SOURCES:
        try:
            if not src.startswith("http") and not Path(src).exists():
                continue
            g = gpd.read_file(src)
            col = next((c for c in ("ISO_A3", "ADM0_A3", "iso_a3", "GID_0") if c in g.columns), None)
            if col is None:
                continue
            g = g.rename(columns={col: "iso_a3"})
            # Natural Earth codes some countries -99 in ISO_A3; ADM0_A3 is safer
            if "ADM0_A3" in g.columns:
                g["iso_a3"] = np.where(g["iso_a3"].astype(str) == "-99", g["ADM0_A3"], g["iso_a3"])
            g = g.to_crs("EPSG:4326")
            if bbox is not None:
                g = g.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
            logger.info(f"Boundaries loaded from {src} ({len(g)} polygons)")
            return g[["iso_a3", "geometry"]]
        except Exception as e:
            logger.warning(f"Boundaries not loaded from {src}: {e}")
    logger.warning("No country boundaries available - maps without borders")
    return None


def plot_map(path, grid, lons, lats, title, clabel="", cmap="Oranges", vmin=None, vmax=None,
             boundaries=None, reason=None, categorical=None):
    """
    Quick-look PNG. NaN pixels are shown in greys by reason code when given.
    categorical: list of (value, colour, label) -> discrete legend instead of colour bar.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    from matplotlib.patches import Patch

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    extent = [lons.min() - 0.025, lons.max() + 0.025, lats.min() - 0.025, lats.max() + 0.025]
    aspect = (extent[3] - extent[2]) / (extent[1] - extent[0])
    fig, ax = plt.subplots(figsize=(12, max(4.0, 12 * aspect + 1.5)))
    ax.set_facecolor("white")

    handles = []
    if reason is not None:
        greys = {REASON_BIMODAL: ("#9e9e9e", REASON_LABELS[REASON_BIMODAL]),
                 REASON_FEW_SEASONS: ("#d0d0d0", "insufficient seasons / no RADS"),
                 REASON_NO_RADS: ("#d0d0d0", None),
                 REASON_SHORT_SEASON: ("#e6e6e6", REASON_LABELS[REASON_SHORT_SEASON]),
                 REASON_MISSING: ("#d0d0d0", None)}
        shown = set()
        for code, (col, lab) in greys.items():
            m = (reason == code) & np.isnan(grid)
            if not m.any():
                continue
            ax.imshow(np.where(m, 1.0, np.nan)[::-1], extent=extent, cmap=ListedColormap([col]),
                      interpolation="nearest")
            if lab and lab not in shown:
                handles.append(Patch(facecolor=col, edgecolor="none", label=lab))
                shown.add(lab)

    if categorical:
        vals = [c[0] for c in categorical]
        cm = ListedColormap([c[1] for c in categorical])
        norm = BoundaryNorm(np.r_[np.array(vals) - 0.5, vals[-1] + 0.5], cm.N)
        ax.imshow(grid[::-1], extent=extent, cmap=cm, norm=norm, interpolation="nearest")
        handles = [Patch(facecolor=c[1], edgecolor="none", label=c[2]) for c in categorical] + handles
    else:
        im = ax.imshow(grid[::-1], extent=extent, cmap=cmap, vmin=vmin, vmax=vmax,
                       interpolation="nearest")
        cb = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02)
        cb.set_label(clabel)
        cb.outline.set_visible(False)

    if boundaries is not None and len(boundaries):
        boundaries.boundary.plot(ax=ax, color="#333333", linewidth=0.4)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    for s in ax.spines.values():
        s.set_color("#999999")
    valid = np.isfinite(grid).sum()
    ax.text(0.01, 0.01, f"valid pixels: {valid:,}", transform=ax.transAxes, fontsize=8,
            color="#555555", va="bottom")
    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0 if categorical is None else 1.01, 1.0),
                  frameon=False, fontsize=8)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)


def read_json(path):
    with open(path) as f:
        return json.load(f)
