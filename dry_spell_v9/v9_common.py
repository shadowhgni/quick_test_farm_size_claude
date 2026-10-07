#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9_common.py - settings loader, fixed codes and helpers of the v9 dry-spell workflow
====================================================================================

  v9_01_download.py         CHIRPS daily, PKU GIMMS NDVI, boundaries, AEZ, Koppen-Geiger
  v9_02_ndvi_phenology.py   NDVI seasons (number, start, end) -> CHIRPS grid
  v9_03_spells_seasons.py   dry spells, regime (rain + NDVI), major-season onset / demise
  v9_04_sowing_risk.py      a country, bbox, polygon or single cell: sowing x crop x cycle risk
  v9_05_aggregate.py        all units -> SSA folder, summaries by AEZ8 / Koppen
  run_all.py                everything, resumable

All tunable settings are in v9_config.py (overridable with a JSON file, see there).
"""

import json
import logging
import os
from pathlib import Path

import numpy as np

import v9_config as _cfg

logger = logging.getLogger("dryspell_v9")

# ---- settings: v9_config.py, then the JSON overrides named by $DRYSPELL_V9_CONFIG ----------
SETTINGS = {k: getattr(_cfg, k) for k in dir(_cfg) if k.isupper()}
CONFIG_FILE = os.environ.get("DRYSPELL_V9_CONFIG")
if CONFIG_FILE:
    with open(CONFIG_FILE) as _f:
        _over = json.load(_f)
    _bad = sorted(set(_over) - set(SETTINGS))
    if _bad:
        raise KeyError(f"{CONFIG_FILE}: unknown settings {_bad} (see v9_config.py)")
    SETTINGS.update(_over)
    if "REGIONS" in _over:
        SETTINGS["REGIONS"] = {k: tuple(v) for k, v in SETTINGS["REGIONS"].items()}
globals().update(SETTINGS)
ORIGIN = np.datetime64(f"{DATA_YEAR_MIN}-01-01", "D")   # day index 0  # noqa: F821


def settings_json():
    """The settings actually in use (for settings_used.json)."""
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in SETTINGS.items()}


# ---- fixed codes (not settings) -------------------------------------------------------------
REGIME_NONE, REGIME_UNI, REGIME_TRANSITION, REGIME_BI = 0, 1, 2, 3
REGIME_LABELS = {0: "no season (arid / no data)", 1: "unimodal", 2: "transition", 3: "bimodal"}

REASON_OK = 0
REASON_NO_CHIRPS = 1          # no rainfall data (ocean / outside CHIRPS)
REASON_MISSING = 2            # too many missing rainfall days
REASON_ARID = 3               # mean annual rain < ARID_MM
REASON_FEW_SEASONS = 4        # too few valid seasons
REASON_LABELS = {0: "ok", 1: "no CHIRPS data", 2: "missing rainfall days", 3: "arid (no season)",
                 4: "too few valid seasons"}

# season reason codes (seasons table)
S_OK = 0
S_NO_ONSET = 1                # cumulative anomaly has no usable minimum inside the window
S_BAD_LENGTH = 2              # season shorter / longer than the limits
S_NO_DATA = 3                 # window not covered by rainfall data
S_CELL_INVALID = 4            # cell without usable rainfall or arid
S_DUPLICATE = 5               # second season with an onset in the same calendar year
S_OUT_OF_PERIOD = 6           # onset outside SEASON_YEAR_MIN..SEASON_YEAR_MAX
S_FALSE_START = 7             # excluded false start (FALSE_START_EXCLUDE)
S_FALSE_DEMISE = 8            # excluded false demise (FALSE_DEMISE_EXCLUDE)
S_LABELS = {0: "ok", 1: "no onset", 2: "bad length", 3: "no rainfall data", 4: "cell invalid",
            5: "duplicate", 6: "out of period", 7: "false start (excluded)", 8: "false demise (excluded)"}

# ---- zones ------------------------------------------------------------------------------------
HARVESTCHOICE_AEZ = {
    101: "Temperate / arid", 102: "Temperate / semiarid", 103: "Temperate / subhumid", 104: "Temperate / humid",
    211: "Subtropic - warm / arid", 212: "Subtropic - warm / semiarid", 213: "Subtropic - warm / subhumid",
    214: "Subtropic - warm / humid", 221: "Subtropic - cool / arid", 222: "Subtropic - cool / semiarid",
    223: "Subtropic - cool / subhumid", 224: "Subtropic - cool / humid",
    311: "Tropic - warm / arid", 312: "Tropic - warm / semiarid", 313: "Tropic - warm / subhumid",
    314: "Tropic - warm / humid", 321: "Tropic - cool / arid", 322: "Tropic - cool / semiarid",
    323: "Tropic - cool / subhumid", 324: "Tropic - cool / humid", 400: "Boreal",
}
AEZ8_LABELS = {1: "Warm / arid", 2: "Warm / semiarid", 3: "Warm / subhumid", 4: "Warm / humid",
               5: "Cool / arid", 6: "Cool / semiarid", 7: "Cool / subhumid", 8: "Cool / humid"}


def aez8_from_code(code):
    """HarvestChoice 3-digit AEZ code -> 8-class code (tens digit 1 = warm, 2 = cool; units = moisture)."""
    code = np.asarray(code)
    warmcool, moist = (code // 10) % 10, code % 10
    ok = (code >= 200) & (code < 400) & np.isin(warmcool, [1, 2]) & (moist >= 1) & (moist <= 4)
    return np.where(ok, (warmcool - 1) * 4 + moist, -1).astype(np.int16)


def koppen_labels(legend_text):
    """legend.txt of Beck et al. (2023) -> {code: 'Aw  Tropical, savannah'}."""
    import re
    out = {}
    for ln in legend_text.splitlines():
        m = re.match(r"\s*(\d+):\s+(\S+)\s+(.+?)\s+\[", ln)
        if m:
            out[int(m.group(1))] = f"{m.group(2)} {m.group(3).strip()}"
    return out


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


def data_dir(*parts):
    return Path(DATA_ROOT).joinpath(*parts)


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
# XARRAY
# =============================================================================

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


def boundaries_file():
    return data_dir("boundaries", "ne_50m_admin_0_countries.gpkg")


def load_boundaries(bbox=None):
    """Country polygons (GeoDataFrame with 'iso_a3') from the data folder, or None."""
    import geopandas as gpd
    f = boundaries_file()
    if not f.exists():
        logger.warning(f"{f} not found - run v8_01_download.py (boundaries)")
        return None
    g = gpd.read_file(f)
    if bbox is not None:
        g = g.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    return g[["iso_a3", "geometry"]]


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
        greys = {REASON_ARID: ("#e6e6e6", REASON_LABELS[REASON_ARID]),
                 REASON_FEW_SEASONS: ("#c8c8c8", REASON_LABELS[REASON_FEW_SEASONS]),
                 REASON_MISSING: ("#b0b0b0", REASON_LABELS[REASON_MISSING])}
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
