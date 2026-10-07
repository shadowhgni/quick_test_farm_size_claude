#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v7 STEP 4 - country case study: sowing date x crop x cycle -> which stage does the
            LONGEST dry spell of the crop cycle hit?
==================================================================================

For one country (default NGA), every valid grid cell and every valid RADS season:

  sowing day  S = onset + DAY0 + sow        sow in SOW_OFFSETS (0, 10, 20, 30, 40)
  maturity    M = S + cycle - 1             cycle in CYCLES (70, 90, 110, 130 days)
  DAS         days after sowing, sowing day = DAS 0, maturity = DAS cycle-1

  * The crop cycle is FEASIBLE in a season if M <= demise + DEMISE_GRACE and every
    day of [S, M] has rainfall data. A cell is flagged IMPOSSIBLE for a
    (crop, cycle, sow) when fewer than FEASIBLE_MIN_FRAC of its valid seasons are
    feasible (default 0.5 = "the median season is too short").
  * Dry spells (< 1 mm/day, from step1, missing days break spells) are clipped to
    [S, M] and kept if the clipped length >= the crop's minimum (MIN_SPELL_CROP).
  * The longest kept spell of each feasible season (ties -> earliest) is located in
    DAS and compared with
      - every phenological stage of the crop: a stage is HIT if it shares >= 1 day
        with the spell (a spell usually hits several stages, all are counted);
      - the crop's most drought-vulnerable window (one window, DAS start-end).
  * Probabilities are over FEASIBLE seasons and unconditional: a feasible season
    without any qualifying spell counts as "not hit".

Stage timing is given as FRACTIONS OF THE CYCLE (sowing = 0, maturity = 1) and scaled
to each cycle length (see CROPS below for sources and caveats); stage_windows.csv
lists the resulting DAS for every crop x cycle and the phenological stages the
vulnerable window corresponds to.

Spatial summary per AEZ. Recommended free SSA layer: HarvestChoice/IFPRI "Agro-ecological
Zones of Africa" (Sebastian 2009, https://doi.org/10.7910/DVN/HJYYTI, CC BY-NC 3.0); pass
the downloaded 003_afr-aez_09.zip directly to --aez (codes 311-324 etc. are labelled
automatically). Any class raster (+ optional --aez_legend code,label CSV) or a vector file
(--aez_field) also works, e.g. FAO/IIASA GAEZ v4 "Dominant AEZ, 33 classes". The raster is
resampled to the 0.05 deg grid by majority. Without --aez a PROXY based on CHIRPS mean
annual rainfall bands is used and labelled as such - it is not an official AEZ map.

RADS reports ONE rainy season per year and masks cells whose 2nd or 3rd harmonic
explains as much variance as the 1st (bimodal / trimodal regimes), see
https://github.com/rjbombardi/onset_demise_rainy_season (rainyseason.py). Such cells
have no valid season and are reported as "no valid RADS season".

Inputs (from steps 1-2 of the same --region)
  dryspell_v7/<region>/step1/spells/part_*.parquet, grid_meta.nc, day_has_data.npy,
  step1_meta.json;  dryspell_v7/<region>/step2/seasons/part_*.parquet

Outputs (dryspell_v7/<region>/step4_<ISO3>/)
  stage_windows.csv          stages + vulnerable window in DAS per crop x cycle
  cells_<crop>.nc            per-cell layers, dims (cycle, sow, [stage], lat, lon)
  cell_summary.parquet       long table, one row per cell x crop x cycle x sow
  cell_stage_hits.parquet    long table, P(longest spell hits stage) per cell
  aez_summary.csv            per AEZ (+ "ALL") x crop x cycle x sow
  aez_stage_hits.csv         per AEZ (+ "ALL") x crop x cycle x sow x stage
  png/                       heatmaps (stage x sowing), maps, AEZ curves

Usage
-----
  python 2026-10-06.step4_sowing_date_stage_risk_v07.py --region study --iso3 NGA
  python 2026-10-06.step4_sowing_date_stage_risk_v07.py --region study --iso3 NGA \\
         --aez Spatial_data_repository/003_afr-aez_09.zip --day0 1 --grace 10 --workers 32
"""

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import gc
import logging
import multiprocessing as mp
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dryspell_v7_common as C

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger("dryspell_v7")

# =============================================================================
# CONFIGURATION (edit here)
# =============================================================================

SOW_OFFSETS = [0, 10, 20, 30, 40]   # days after DAY0
DAY0 = 0                            # 0: first sowing on the RADS onset day, 1: onset + 1
CYCLES = [70, 90, 110, 130]         # days from sowing to physiological maturity
DEMISE_GRACE = 10                   # maturity may fall up to this many days after RADS demise
                                    # (crop finishing on stored soil water); 0 = strict
FEASIBLE_MIN_FRAC = 0.5             # cell IMPOSSIBLE if fewer feasible seasons than this
MIN_FEASIBLE_SEASONS = 5            # probabilities need >= this many feasible seasons

# Minimum dry spell length (days, < 1 mm) per crop. 10 d for all three by default:
# I found no source giving crop-specific thresholds - edit here or use --min_spell.
MIN_SPELL_CROP = {"sorghum": 10, "pearl_millet": 10, "groundnut": 10}

# Stages: (code, name, start as fraction of the cycle); a stage lasts until the next
# one starts, the last one until maturity. Fractions = DAS / DAS at maturity of the
# reference cultivar, then scaled LINEARLY to 70-130 d cycles. Linear scaling is an
# approximation: in long-cycle / photoperiod-sensitive West African cultivars the
# vegetative phase stretches much more than grain filling. Calibrate with local data.
# Sowing-to-emergence is taken as ~4 days for the reference cultivars.
CROPS = {
    "sorghum": {
        "label": "Sorghum",
        # Vanderlip & Reeves (1972) stages 0-9. Boot = 50-60 d after emergence (KSU
        # MF3234, checked). Other days after emergence (10/20/30/40/50/60/70/85/95)
        # are recalled from Vanderlip (1972) for a ~95-d hybrid, NOT re-checked.
        "stages": [("S0", "emergence", 0.04), ("S1", "3-leaf", 0.14), ("S2", "5-leaf", 0.24),
                   ("S3", "growing point differentiation", 0.34), ("S4", "flag leaf visible", 0.44),
                   ("S5", "boot", 0.55), ("S6", "half-bloom", 0.65), ("S7", "soft dough", 0.75),
                   ("S8", "hard dough", 0.90)],
        # most critical: ~1 week before boot to ~2 weeks after flowering
        # (Kansas State / Arkansas extension guidance)
        "window": (0.47, 0.79),
    },
    "pearl_millet": {
        "label": "Pearl millet",
        # Maiti & Bidinger (1981), ICRISAT Res. Bull. 6, Table 1, early Mil Zongo
        # (West African landrace): stages 0-9 at 0/6/15/28/43/47/53/61/69/75 d after
        # emergence (checked); +4 d sowing-to-emergence -> maturity at 79 DAS.
        "stages": [("P0", "emergence", 0.05), ("P1", "3rd leaf", 0.13), ("P2", "5th leaf", 0.24),
                   ("P3", "panicle initiation", 0.41), ("P4", "flag leaf visible", 0.59),
                   ("P5", "boot", 0.65), ("P6", "50% flowering", 0.72), ("P7", "milk", 0.82),
                   ("P8", "dough", 0.92)],
        # stress at flowering + grain filling reduces main-shoot AND tiller yield;
        # earlier stress is partly compensated by tillers (Mahalakshmi & Bidinger 1985)
        "window": (0.65, 0.92),
    },
    "groundnut": {
        "label": "Groundnut",
        # Boote (1982) R stages. The fractions are MY APPROXIMATION from typical
        # Spanish/Virginia timings, not taken from a single table - verify.
        "stages": [("VE", "emergence", 0.07), ("R1", "beginning bloom", 0.22), ("R2", "beginning peg", 0.30),
                   ("R3", "beginning pod", 0.38), ("R4", "full pod", 0.45), ("R5", "beginning seed", 0.52),
                   ("R6", "full seed", 0.62), ("R7", "beginning maturity", 0.78), ("R8", "harvest maturity", 0.93)],
        # peg-to-pod formation needs most water; stress from start of seed growth to
        # maturity gives the largest seed-yield loss (Nageswara Rao et al. 1985)
        "window": (0.38, 0.78),
    },
}

AEZ_PROXY_BANDS = [   # (upper mm/yr, label) - proxy only, from CHIRPS mean annual rain
    (600, "rain <600 mm (~Sahel)"),
    (1000, "rain 600-1000 mm (~Sudan savanna)"),
    (1300, "rain 1000-1300 mm (~N. Guinea savanna)"),
    (1600, "rain 1300-1600 mm (~S. Guinea / derived savanna)"),
    (np.inf, "rain >1600 mm (~humid forest)"),
]

# HarvestChoice / IFPRI "Agro-ecological Zones of Africa" (Sebastian 2009), Harvard Dataverse
# doi:10.7910/DVN/HJYYTI, CC BY-NC 3.0. ESRI ASCII grid, 0.00833 deg, WorldClim + IIASA LGP.
# Codes from 006_aezlegend_09.txt: hundreds = thermal zone, tens = warm/cool, units = moisture
# (1 arid ... 4 humid).
HARVESTCHOICE_AEZ = {
    101: "Temperate / arid", 102: "Temperate / semiarid", 103: "Temperate / subhumid", 104: "Temperate / humid",
    211: "Subtropic - warm / arid", 212: "Subtropic - warm / semiarid", 213: "Subtropic - warm / subhumid",
    214: "Subtropic - warm / humid", 221: "Subtropic - cool / arid", 222: "Subtropic - cool / semiarid",
    223: "Subtropic - cool / subhumid", 224: "Subtropic - cool / humid",
    311: "Tropic - warm / arid", 312: "Tropic - warm / semiarid", 313: "Tropic - warm / subhumid",
    314: "Tropic - warm / humid", 321: "Tropic - cool / arid", 322: "Tropic - cool / semiarid",
    323: "Tropic - cool / subhumid", 324: "Tropic - cool / humid", 400: "Boreal",
}

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
GREY_IMPOSSIBLE = "#b5b5b5"
GREY_NODATA = "#e3e3e3"

_G = {}


# =============================================================================
# STAGES
# =============================================================================

def stage_das(crop, cycle):
    """[(code, name, das_start, das_end)] and (win_start, win_end) in DAS (inclusive)."""
    spec = CROPS[crop]
    st = spec["stages"]
    starts = [0] + [int(round(f * cycle)) for _, _, f in st]
    codes = ["SOW"] + [c for c, _, _ in st]
    names = ["sowing to emergence"] + [n for _, n, _ in st]
    out = []
    for i in range(len(starts)):
        a = starts[i]
        b = (starts[i + 1] - 1) if i + 1 < len(starts) else cycle - 1
        out.append((codes[i], names[i], a, max(a, b)))
    w0, w1 = spec["window"]
    win = (int(round(w0 * cycle)), min(cycle - 1, int(round(w1 * cycle)) - 1))
    return out, win


def stage_table(crops, cycles):
    rows = []
    for crop in crops:
        for L in cycles:
            stages, (w0, w1) = stage_das(crop, L)
            s_in = [s for s in stages if s[3] >= w0 and s[2] <= w1]
            wlab = f"{s_in[0][0]} ({s_in[0][1]}) -> {s_in[-1][0]} ({s_in[-1][1]})"
            for k, (code, name, a, b) in enumerate(stages):
                rows.append({"crop": crop, "cycle": L, "stage_idx": k, "stage": code, "stage_name": name,
                             "das_start": a, "das_end": b, "length": b - a + 1,
                             "overlaps_window": bool(b >= w0 and a <= w1),
                             "window_das_start": w0, "window_das_end": w1, "window_stages": wlab})
    return pd.DataFrame(rows)


# =============================================================================
# WORKER
# =============================================================================

def _date_to_index(col):
    """pyarrow date32 column -> int64 day index since ORIGIN (null -> SENT)."""
    import pyarrow as pa
    import pyarrow.compute as pc
    epoch = int((C.ORIGIN - np.datetime64("1970-01-01", "D")).astype(int))
    v = pc.fill_null(pc.cast(col, pa.int32()), np.iinfo(np.int32).min).to_numpy().astype(np.int64)
    return np.where(v == np.iinfo(np.int32).min, np.iinfo(np.int64).min, v - epoch)


def _pair_spells(sp_cell, sp_s, sp_e, se_cell, on, span_end):
    """(spell index, season index) for every spell overlapping [onset, span_end] of a season."""
    if len(sp_cell) == 0 or len(on) == 0:
        e = np.zeros(0, dtype=np.int64)
        return e, e
    BIG = np.int64(1) << 24
    key = se_cell * BIG + on                    # seasons sorted by (cell, onset)
    last = np.searchsorted(key, sp_cell * BIG + sp_e, side="right") - 1
    pi, qi = [], []
    for pos in (last, last - 1):                # spans never overlap -> 2 candidates suffice
        ok = pos >= 0
        p = np.where(ok, pos, 0)
        ok &= (se_cell[p] == sp_cell) & (sp_s <= span_end[p]) & (sp_e >= on[p])
        pi.append(np.nonzero(ok)[0])
        qi.append(p[ok])
    return np.concatenate(pi), np.concatenate(qi)


def process_rows(r0, r1):
    import pyarrow.parquet as pq

    g = _G
    nlon = g["nlon"]
    nr = r1 - r0
    ncell = nr * nlon
    mask = g["mask"][r0:r1].ravel()
    crops, cycles, sows = g["crops"], g["cycles"], g["sows"]
    nC, nS = len(cycles), len(sows)

    # ---- seasons (valid only, inside the country)
    t = pq.read_table(Path(g["season_dir"]) / f"part_r{r0:05d}.parquet",
                      columns=["row", "col", "year", "onset_date", "demise_date", "valid"])
    valid = t["valid"].to_numpy().astype(bool)
    se_cell = (t["row"].to_numpy().astype(np.int64) - r0) * nlon + t["col"].to_numpy()
    on = _date_to_index(t["onset_date"])
    de = _date_to_index(t["demise_date"])
    keep = valid & mask[se_cell]
    se_cell, on, de = se_cell[keep], on[keep], de[keep]
    o = np.lexsort((on, se_cell))
    se_cell, on, de = se_cell[o], on[o], de[o]
    n_seasons = np.bincount(se_cell, minlength=ncell)
    del t

    # ---- spells (>= smallest crop minimum, inside the country)
    t = pq.read_table(Path(g["spell_dir"]) / f"part_r{r0:05d}.parquet",
                      columns=["row", "col", "start", "end", "length"])
    sp_cell = (t["row"].to_numpy().astype(np.int64) - r0) * nlon + t["col"].to_numpy()
    sp_s = t["start"].to_numpy().astype(np.int64)
    sp_e = t["end"].to_numpy().astype(np.int64)
    k = (t["length"].to_numpy() >= g["min_spell_all"]) & mask[sp_cell]
    sp_cell, sp_s, sp_e = sp_cell[k], sp_s[k], sp_e[k]
    del t

    span_end = on + g["day0"] + max(sows) + max(cycles) - 1
    pi, qi = _pair_spells(sp_cell, sp_s, sp_e, se_cell, on, span_end)
    ps, pe = sp_s[pi], sp_e[pi]

    gaps = g["gaps"]
    n_days = len(gaps) - 1
    nq = len(on)
    out = {}
    for crop in crops:
        minc = g["min_spell"][crop]
        nst = len(g["stages"][crop][cycles[0]][0])
        r = {
            "p_feasible": np.full((nC, nS, ncell), np.nan, np.float32),
            "impossible": np.zeros((nC, nS, ncell), np.int8),
            "p_spell": np.full((nC, nS, ncell), np.nan, np.float32),
            "p_hit_window": np.full((nC, nS, ncell), np.nan, np.float32),
            "window_overlap_mean": np.full((nC, nS, ncell), np.nan, np.float32),
            "longest_len_median": np.full((nC, nS, ncell), np.nan, np.float32),
            "longest_start_das_median": np.full((nC, nS, ncell), np.nan, np.float32),
            "longest_end_das_median": np.full((nC, nS, ncell), np.nan, np.float32),
            "p_hit_stage": np.full((nC, nS, nst, ncell), np.nan, np.float32),
        }
        for ic, L in enumerate(cycles):
            stages, (w0, w1) = g["stages"][crop][L]
            sa = np.array([s[2] for s in stages])
            sb = np.array([s[3] for s in stages])
            for isw, sw in enumerate(sows):
                S = on + g["day0"] + sw
                M = S + L - 1
                inside = (S >= 0) & (M < n_days)
                Sc, Mc = np.clip(S, 0, n_days - 1), np.clip(M, 0, n_days - 1)
                full = inside & (gaps[Mc + 1] - gaps[Sc] == 0)
                feas = full & (M <= de + g["grace"])
                n_feas = np.bincount(se_cell, weights=feas, minlength=ncell)
                with np.errstate(invalid="ignore", divide="ignore"):
                    pf = np.where(n_seasons > 0, n_feas / np.maximum(n_seasons, 1), np.nan)
                r["p_feasible"][ic, isw] = pf
                r["impossible"][ic, isw] = (n_seasons > 0) & (pf < g["feasible_min_frac"])
                enough = (n_feas >= g["min_feasible_seasons"]) & ~r["impossible"][ic, isw].astype(bool)

                # clip spells to [S, M] of their season, keep >= crop minimum
                cs = np.maximum(ps, S[qi])
                ce = np.minimum(pe, M[qi])
                cl = ce - cs + 1
                kk = (cl >= minc) & feas[qi]
                q_k, cs_k, ce_k, cl_k = qi[kk], cs[kk], ce[kk], cl[kk]
                # longest per season, ties -> earliest
                oo = np.lexsort((cs_k, -cl_k, q_k))
                q_k, cs_k, ce_k, cl_k = q_k[oo], cs_k[oo], ce_k[oo], cl_k[oo]
                first = np.r_[True, q_k[1:] != q_k[:-1]] if len(q_k) else np.zeros(0, bool)
                lq = q_k[first]
                l_s = (cs_k[first] - S[lq])                     # DAS
                l_e = (ce_k[first] - S[lq])
                l_len = cl_k[first]
                lc = se_cell[lq]

                def cnt(w):
                    return np.bincount(lc, weights=w, minlength=ncell)

                def prob(x):
                    with np.errstate(invalid="ignore", divide="ignore"):
                        v = x / np.maximum(n_feas, 1)
                    return np.where(enough, v, np.nan).astype(np.float32)

                r["p_spell"][ic, isw] = prob(cnt(np.ones(len(lq))))
                ov_w = np.maximum(0, np.minimum(l_e, w1) - np.maximum(l_s, w0) + 1)
                r["p_hit_window"][ic, isw] = prob(cnt(ov_w >= 1))
                r["window_overlap_mean"][ic, isw] = prob(cnt(ov_w))     # mean over feasible seasons
                for j in range(len(stages)):
                    ov = np.minimum(l_e, sb[j]) - np.maximum(l_s, sa[j]) + 1
                    r["p_hit_stage"][ic, isw, j] = prob(cnt(ov >= 1))
                if len(lq):
                    df = pd.DataFrame({"c": lc, "len": l_len, "s": l_s, "e": l_e}).groupby("c").median()
                    idx = df.index.to_numpy()
                    for col, name in (("len", "longest_len_median"), ("s", "longest_start_das_median"),
                                      ("e", "longest_end_das_median")):
                        a = r[name][ic, isw]
                        a[idx] = df[col].to_numpy()
                        a[~enough] = np.nan
        out[crop] = {kname: v.reshape(v.shape[:-1] + (nr, nlon)) for kname, v in r.items()}
    gc.collect()
    return r0, r1, out, n_seasons.reshape(nr, nlon), len(pi)


# =============================================================================
# AEZ
# =============================================================================

RASTER_EXT = (".tif", ".tiff", ".asc", ".img", ".nc", ".zip")


def _raster_uri(p):
    """GDAL path for a raster file, or for the first raster inside a .zip."""
    if p.suffix.lower() != ".zip":
        return str(p)
    import zipfile
    with zipfile.ZipFile(p) as z:
        names = [n for n in z.namelist() if n.lower().endswith((".asc", ".tif", ".tiff", ".img"))]
        if not names:                       # e.g. an ESRI ASCII grid saved as .txt
            side = (".prj", ".xml", ".aux", ".ovr", ".lyr", ".dbf", ".shp", ".shx", ".cpg", ".pdf", ".doc", "/")
            names = [n for n in z.namelist() if not n.lower().endswith(side)]
    if not names:
        sys.exit(f"no raster inside {p}")
    return f"zip://{p.resolve()}!{names[0]}"


def _read_legend(path):
    """CSV with columns code,label -> {int: str}."""
    d = pd.read_csv(path)
    return {int(c): str(l) for c, l in zip(d.iloc[:, 0], d.iloc[:, 1])}


def load_aez(path, field, lon, lat, mean_rain, cmask, legend=None):
    """Return (codes int16 grid, {code: label}, source description)."""
    if path is None:
        codes = np.full(mean_rain.shape, -1, np.int16)
        labels = {}
        lo = -np.inf
        for i, (hi, lab) in enumerate(AEZ_PROXY_BANDS):
            codes[(mean_rain >= lo) & (mean_rain < hi)] = i
            labels[i] = lab
            lo = hi
        codes[~cmask] = -1
        return codes, labels, "PROXY: CHIRPS mean annual rainfall bands (not an official AEZ map)"
    p = Path(path)
    if p.suffix.lower() in RASTER_EXT:
        # class raster -> step grid by MAJORITY (mode) of the source pixels in each 0.05 deg cell
        import rasterio
        from rasterio.warp import reproject, Resampling
        uri = _raster_uri(p)
        with rasterio.open(uri) as src:
            band = src.read(1)
            nod = src.nodata
            src_crs = src.crs or "EPSG:4326"          # ESRI .asc often ships without CRS
            dst = np.full((len(lat), len(lon)), -1, dtype=np.int32)
            reproject(band.astype(np.int32), dst, src_transform=src.transform, src_crs=src_crs,
                      src_nodata=(int(nod) if nod is not None and np.isfinite(nod) else -9999),
                      dst_transform=C.grid_transform(lon, lat), dst_crs="EPSG:4326",
                      dst_nodata=-1, resampling=Resampling.mode)
        codes = dst[::-1]                              # north-up -> ascending lat
        codes = np.where(cmask & (codes > 0), codes, -1).astype(np.int16)
        present = [int(c) for c in np.unique(codes) if c >= 0]
        if legend:
            lab = _read_legend(legend)
        elif set(present) <= set(HARVESTCHOICE_AEZ):
            lab = HARVESTCHOICE_AEZ
        else:
            lab = {}
        labels = {c: lab.get(c, f"AEZ {c}") for c in present}
        return codes, labels, f"raster {uri} (majority per cell)"
    import geopandas as gpd
    from rasterio.features import rasterize
    gdf = gpd.read_file(p).to_crs("EPSG:4326")
    if field not in gdf.columns:
        sys.exit(f"--aez_field {field!r} not in {list(gdf.columns)}")
    cats = sorted(gdf[field].dropna().astype(str).unique())
    labels = dict(enumerate(cats))
    inv = {v: k for k, v in labels.items()}
    shapes = [(geom, inv[str(v)]) for geom, v in zip(gdf.geometry, gdf[field]) if v is not None and geom is not None]
    r = rasterize(shapes, out_shape=(len(lat), len(lon)), transform=C.grid_transform(lon, lat),
                  fill=-1, dtype="int16")[::-1]
    return np.where(cmask, r, -1).astype(np.int16), labels, f"vector {p} field {field}"


# =============================================================================
# PLOTS
# =============================================================================

def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def plot_stage_heatmaps(path, crop, st_df, hits, cycles, sows, day0, title_extra):
    """hits: DataFrame (cycle, sow, stage_idx, p) for one AEZ. One panel per cycle."""
    plt = _plt()
    from matplotlib.patches import Rectangle
    n = len(cycles)
    fig, axes = plt.subplots(1, n, figsize=(3.6 * n + 1.2, 3.9), sharey=True)
    axes = np.atleast_1d(axes)
    im = None
    for ax, L in zip(axes, cycles):
        sdf = st_df[(st_df.crop == crop) & (st_df.cycle == L)].sort_values("stage_idx")
        h = hits[hits.cycle == L].pivot(index="sow", columns="stage_idx", values="p") \
            .reindex(index=sows, columns=sdf.stage_idx.tolist())
        im = ax.imshow(h.values, cmap="Oranges", vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        for i in range(h.shape[0]):
            for j in range(h.shape[1]):
                v = h.values[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6,
                            color="white" if v > 0.6 else "#333333")
        win = sdf.overlaps_window.to_numpy()
        if win.any():
            j0, j1 = np.where(win)[0][[0, -1]]
            ax.add_patch(Rectangle((j0 - 0.5, -0.5), j1 - j0 + 1, len(sows), fill=False,
                                   edgecolor="#222222", linewidth=1.4))
        ax.set_xticks(range(len(sdf)))
        ax.set_xticklabels([f"{c}  {a}-{b}" for c, a, b in zip(sdf.stage, sdf.das_start, sdf.das_end)],
                           fontsize=6, rotation=90)
        ax.set_yticks(range(len(sows)))
        ax.set_yticklabels([f"+{day0 + s}" for s in sows], fontsize=7)
        ax.set_title(f"{L}-day cycle", loc="left", fontsize=9)
        ax.set_xlabel("stage (DAS range)", fontsize=7)
        for s in ax.spines.values():
            s.set_visible(False)
    axes[0].set_ylabel("sowing, days after RADS onset", fontsize=8)
    cb = fig.colorbar(im, ax=axes, shrink=0.8, pad=0.01)
    cb.set_label("P(longest dry spell hits stage)", fontsize=8)
    cb.outline.set_visible(False)
    fig.suptitle(f"{CROPS[crop]['label']} - {title_extra}   (box = most vulnerable window)",
                 x=0.01, ha="left", fontsize=10)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_window_maps(path, crop, ds, cycles, sows, day0, lon, lat, bnd, analysed):
    plt = _plt()
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    nC, nS = len(cycles), len(sows)
    extent = [lon.min() - 0.025, lon.max() + 0.025, lat.min() - 0.025, lat.max() + 0.025]
    aspect = (extent[3] - extent[2]) / (extent[1] - extent[0])
    fig, axes = plt.subplots(nC, nS, figsize=(2.6 * nS + 1, 2.6 * nC * aspect + 0.8), squeeze=False)
    im = None
    for ic, L in enumerate(cycles):
        for isw, sw in enumerate(sows):
            ax = axes[ic, isw]
            ax.imshow(np.where(~analysed, 1.0, np.nan)[::-1], extent=extent,
                      cmap=ListedColormap([GREY_NODATA]), interpolation="nearest")
            imp = ds["impossible"].values[ic, isw].astype(bool) & analysed
            ax.imshow(np.where(imp, 1.0, np.nan)[::-1], extent=extent,
                      cmap=ListedColormap([GREY_IMPOSSIBLE]), interpolation="nearest")
            im = ax.imshow(ds["p_hit_window"].values[ic, isw][::-1], extent=extent, cmap="Purples",
                           vmin=0, vmax=1, interpolation="nearest")
            if bnd is not None and len(bnd):
                bnd.boundary.plot(ax=ax, color="#333333", linewidth=0.3)
            ax.set_xlim(extent[:2])
            ax.set_ylim(extent[2:])
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xlabel("")
            ax.set_ylabel("")
            for s in ax.spines.values():
                s.set_visible(False)
            if ic == 0:
                ax.set_title(f"sow onset+{day0 + sw}", fontsize=8)
            if isw == 0:
                ax.set_ylabel(f"{L} d", fontsize=8)
    cb = fig.colorbar(im, ax=axes, shrink=0.6, pad=0.01)
    cb.set_label("P(longest dry spell hits the vulnerable window)", fontsize=8)
    cb.outline.set_visible(False)
    fig.legend(handles=[Patch(facecolor=GREY_IMPOSSIBLE, label="impossible (cycle does not fit the season)"),
                        Patch(facecolor=GREY_NODATA, label="no valid RADS season / no data")],
               loc="lower left", frameon=False, fontsize=7, ncol=2)
    fig.suptitle(f"{CROPS[crop]['label']} - rows: cycle length, columns: sowing date", x=0.01,
                 ha="left", fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_aez_curves(path, crop, summ, cycles, sows, day0, aez_order):
    """P(hit window) vs sowing date, one line per AEZ, one panel per cycle."""
    plt = _plt()
    n = len(cycles)
    fig, axes = plt.subplots(1, n, figsize=(3.0 * n + 2.6, 3.2), sharey=True)
    axes = np.atleast_1d(axes)
    x = [day0 + s for s in sows]
    for ax, L in zip(axes, cycles):
        for k, a in enumerate(aez_order):
            d = summ[(summ.crop == crop) & (summ.cycle == L) & (summ.aez == a)].set_index("sow").reindex(sows)
            col = "#222222" if a == "ALL" else SERIES[k % len(SERIES)]
            ax.plot(x, d["p_hit_window_mean"], color=col, linewidth=2.4 if a == "ALL" else 2,
                    linestyle="--" if a == "ALL" else "-", marker="o", markersize=4,
                    label=a if ax is axes[0] else None)
        ax.set_title(f"{L}-day cycle", loc="left", fontsize=9)
        ax.set_xticks(x)
        ax.set_xlabel("sowing, days after onset", fontsize=8)
        ax.set_ylim(0, 1)
        ax.grid(True, color="#e5e5e5", linewidth=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("P(longest spell hits window)\nmean over possible cells", fontsize=8)
    fig.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=7)
    fig.suptitle(f"{CROPS[crop]['label']} - by AEZ (missing point = all cells impossible)", x=0.01,
                 ha="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =============================================================================
# MAIN
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="study", help="step1/step2 region to read")
    ap.add_argument("--iso3", default="NGA")
    ap.add_argument("--crops", nargs="+", default=list(CROPS), choices=list(CROPS))
    ap.add_argument("--cycles", nargs="+", type=int, default=CYCLES)
    ap.add_argument("--sow", nargs="+", type=int, default=SOW_OFFSETS, help="sowing offsets after DAY0")
    ap.add_argument("--day0", type=int, default=DAY0, choices=[0, 1], help="first sowing = onset + day0")
    ap.add_argument("--grace", type=int, default=DEMISE_GRACE, help="days maturity may exceed demise")
    ap.add_argument("--feasible_min_frac", type=float, default=FEASIBLE_MIN_FRAC)
    ap.add_argument("--min_feasible_seasons", type=int, default=MIN_FEASIBLE_SEASONS)
    ap.add_argument("--min_spell", nargs="*", default=[], metavar="CROP=DAYS",
                    help="override MIN_SPELL_CROP, e.g. pearl_millet=12")
    ap.add_argument("--aez", default=None,
                    help="AEZ class raster (.tif/.asc/.img or a .zip holding one, e.g. HarvestChoice "
                         "003_afr-aez_09.zip) or vector file (.gpkg/.shp/.geojson, see --aez_field)")
    ap.add_argument("--aez_legend", default=None, help="CSV code,label for a raster --aez "
                    "(HarvestChoice codes are labelled automatically)")
    ap.add_argument("--aez_field", default="AEZ", help="attribute with the AEZ name (vector --aez)")
    ap.add_argument("--workers", type=int, default=max(1, min(32, mp.cpu_count() - 4)))
    a = ap.parse_args()

    min_spell = dict(MIN_SPELL_CROP)
    for s in a.min_spell:
        k, v = s.split("=")
        if k not in CROPS:
            sys.exit(f"--min_spell: unknown crop {k}")
        min_spell[k] = int(v)
    if min(min_spell[c] for c in a.crops) < C.STEP1_MIN_SPELL:
        sys.exit(f"minimum spell must be >= {C.STEP1_MIN_SPELL} (step1 only stores spells >= that)")
    cycles, sows = sorted(a.cycles), sorted(a.sow)

    rdir = C.region_dir(a.region)
    s1, s2 = rdir / "step1", rdir / "step2"
    out = rdir / f"step4_{a.iso3}"
    C.setup_logging(out / "step4.log")
    t0 = time.time()
    meta = C.read_json(s1 / "step1_meta.json")
    with xr.open_dataset(s1 / "grid_meta.nc") as d:
        gm = d.load()
    lon, lat = gm.lon.values, gm.lat.values
    has = np.load(s1 / "day_has_data.npy")
    if not (s2 / "seasons").exists():
        sys.exit(f"{s2 / 'seasons'} not found - run step2 first")

    logger.info("=" * 70)
    logger.info(f"v7 STEP4  region={a.region} country={a.iso3} crops={a.crops}")
    logger.info(f"  sowing = onset + {a.day0} + {sows}   cycles = {cycles} d   grace = {a.grace} d")
    logger.info(f"  min spell (d) = { {c: min_spell[c] for c in a.crops} }   impossible if "
                f"P(feasible) < {a.feasible_min_frac}")
    logger.info("=" * 70)

    # ---- country mask on the step1 grid
    bnd_all = C.load_boundaries(meta["bbox"])
    if bnd_all is None:
        sys.exit("country boundaries are required (see BOUNDARY_SOURCES in dryspell_v7_common.py)")
    bnd = bnd_all[bnd_all["iso_a3"] == a.iso3]
    if not len(bnd):
        sys.exit(f"{a.iso3} not found in boundaries")
    from rasterio.features import geometry_mask
    cmask = geometry_mask(bnd.geometry, out_shape=(len(lat), len(lon)),
                          transform=C.grid_transform(lon, lat), invert=True)[::-1]
    cell_ok = gm["valid"].values.astype(bool)
    rows = np.where(cmask.any(1))[0]
    cols = np.where(cmask.any(0))[0]
    if not len(rows):
        sys.exit(f"{a.iso3} does not overlap the {a.region} grid")
    i0, i1, j0, j1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    logger.info(f"  {a.iso3}: {cmask.sum():,} grid cells, {(cmask & cell_ok).sum():,} with usable CHIRPS")

    stages = {c: {L: stage_das(c, L) for L in cycles} for c in a.crops}
    st_df = stage_table(a.crops, cycles)
    out.mkdir(parents=True, exist_ok=True)
    st_df.to_csv(out / "stage_windows.csv", index=False)
    for (c, L), d in st_df.groupby(["crop", "cycle"]):
        r = d.iloc[0]
        logger.info(f"  {c:<13}{L:>4} d: vulnerable window DAS {r.window_das_start}-{r.window_das_end} "
                    f"= {r.window_stages}")

    _G.update(nlon=len(lon), mask=cmask & cell_ok, crops=a.crops, cycles=cycles, sows=sows,
              day0=a.day0, grace=a.grace, feasible_min_frac=a.feasible_min_frac,
              min_feasible_seasons=a.min_feasible_seasons, min_spell=min_spell,
              min_spell_all=min(min_spell[c] for c in a.crops), stages=stages,
              gaps=np.r_[0, np.cumsum(~has)], spell_dir=str(s1 / "spells"), season_dir=str(s2 / "seasons"))

    chunks = [tuple(c) for c in meta["chunks"] if c[1] > i0 and c[0] < i1]
    nlat, nlon = len(lat), len(lon)
    nC, nS = len(cycles), len(sows)
    full = {}
    for c in a.crops:
        nst = len(stages[c][cycles[0]][0])
        full[c] = {k: np.full((nC, nS, nlat, nlon), np.nan, np.float32)
                   for k in ("p_feasible", "p_spell", "p_hit_window", "window_overlap_mean",
                             "longest_len_median", "longest_start_das_median", "longest_end_das_median")}
        full[c]["impossible"] = np.zeros((nC, nS, nlat, nlon), np.int8)
        full[c]["p_hit_stage"] = np.full((nC, nS, nst, nlat, nlon), np.nan, np.float32)
    n_seasons = np.zeros((nlat, nlon), np.int32)
    logger.info(f"Processing {len(chunks)} row chunks")
    n_pairs = 0
    with ProcessPoolExecutor(max_workers=min(a.workers, len(chunks)), mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(process_rows, r0, r1) for r0, r1 in chunks]
        for i, f in enumerate(as_completed(futs), 1):
            r0, r1, res, ns, npair = f.result()
            n_seasons[r0:r1] = ns
            n_pairs += npair
            for c in a.crops:
                for k, v in res[c].items():
                    full[c][k][..., r0:r1, :] = v
            if i % 10 == 0 or i == len(chunks):
                logger.info(f"  {i}/{len(chunks)} chunks")
    logger.info(f"  spell x season pairs examined: {n_pairs:,}")

    # ---- crop to the country box
    sl = (slice(i0, i1), slice(j0, j1))
    lon_c, lat_c = lon[j0:j1], lat[i0:i1]
    cm_c = cmask[sl]
    analysed = cm_c & cell_ok[sl] & (n_seasons[sl] >= a.min_feasible_seasons)
    n_rads = int((cm_c & cell_ok[sl] & (n_seasons[sl] == 0)).sum())
    logger.info(f"  cells analysed: {analysed.sum():,}; no valid RADS season "
                f"(incl. RADS bimodal mask): {n_rads:,}; no usable CHIRPS: {(cm_c & ~cell_ok[sl]).sum():,}")

    mean_rain = gm["mean_annual_mm"].values[sl]
    aez, aez_lab, aez_src = load_aez(a.aez, a.aez_field, lon_c, lat_c, mean_rain, cm_c, a.aez_legend)
    logger.info(f"  AEZ source: {aez_src}")
    for code, lab in aez_lab.items():
        logger.info(f"    {code:>3} {lab:<50} {(analysed & (aez == code)).sum():>8,} analysed cells")

    # ---- NetCDF per crop
    reason = np.full(cm_c.shape, 0, np.uint8)       # 0 ok, 1 outside country, 2 no CHIRPS, 3 no RADS season
    reason[~cm_c] = 1
    reason[cm_c & ~cell_ok[sl]] = 2
    reason[cm_c & cell_ok[sl] & ~analysed] = 3
    sets = {}
    for c in a.crops:
        st0 = stages[c][cycles[0]][0]
        dv = {}
        for k, v in full[c].items():
            v = v[..., i0:i1, j0:j1]
            if k == "p_hit_stage":
                dv[k] = (("cycle", "sow", "stage", "lat", "lon"), v)
            else:
                dv[k] = (("cycle", "sow", "lat", "lon"), v)
        dv["aez"] = (("lat", "lon"), aez)
        dv["reason"] = (("lat", "lon"), reason)
        dv["n_valid_seasons"] = (("lat", "lon"), n_seasons[sl])
        ds = xr.Dataset(dv, coords={"cycle": cycles, "sow": [a.day0 + s for s in sows],
                                    "stage": [s[0] for s in st0], "lat": lat_c, "lon": lon_c},
                        attrs={"crop": c, "country": a.iso3, "min_spell_days": min_spell[c],
                               "dry_mm": C.DRY_MM, "demise_grace": a.grace,
                               "feasible_min_frac": a.feasible_min_frac,
                               "sow": "days after RADS onset", "aez_source": aez_src,
                               "aez_labels": str(aez_lab),
                               "reason": "0 ok, 1 outside country, 2 no usable CHIRPS, 3 no/too few RADS seasons",
                               "note": "probabilities over feasible seasons; longest_* medians over seasons "
                                       "with a qualifying spell"})
        ds.to_netcdf(out / f"cells_{c}.nc", encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
        sets[c] = ds
    logger.info(f"Written cells_<crop>.nc")

    # ---- long tables
    ii, jj = np.nonzero(analysed)
    aez_name = np.array([aez_lab.get(int(x), "unassigned") for x in aez[ii, jj]])
    cell_rows, stage_rows = [], []
    for c in a.crops:
        ds = sets[c]
        stage_codes = list(ds.stage.values)
        for ic, L in enumerate(cycles):
            for isw, sw in enumerate(sows):
                d = {"crop": c, "cycle": L, "sow": a.day0 + sw, "row": ii + i0, "col": jj + j0,
                     "lat": lat_c[ii], "lon": lon_c[jj], "aez": aez_name}
                for k in ("p_feasible", "impossible", "p_spell", "p_hit_window", "window_overlap_mean",
                          "longest_len_median", "longest_start_das_median", "longest_end_das_median"):
                    d[k] = ds[k].values[ic, isw][ii, jj]
                ph = ds["p_hit_stage"].values[ic, isw][:, ii, jj]          # (stage, n)
                with np.errstate(invalid="ignore"):
                    best = np.where(np.all(np.isnan(ph), 0), -1, np.nanargmax(np.where(np.isnan(ph), -1, ph), 0))
                d["most_hit_stage"] = np.where(best >= 0, np.array(stage_codes + [""])[best], "")
                cell_rows.append(pd.DataFrame(d))
                for j, code in enumerate(stage_codes):
                    stage_rows.append(pd.DataFrame({"crop": c, "cycle": L, "sow": a.day0 + sw, "stage_idx": j,
                                                    "stage": code, "row": ii + i0, "col": jj + j0,
                                                    "aez": aez_name, "impossible": d["impossible"],
                                                    "p_hit": ph[j]}))
    cells = pd.concat(cell_rows, ignore_index=True)
    shits = pd.concat(stage_rows, ignore_index=True)
    cells.to_parquet(out / "cell_summary.parquet", index=False)
    shits.to_parquet(out / "cell_stage_hits.parquet", index=False)

    # ---- AEZ summaries (+ national "ALL"); probabilities averaged over POSSIBLE cells
    # (per-cell probabilities are already NaN where the cell is impossible)
    keys = ["crop", "cycle", "sow"]
    agg = dict(n_cells=("impossible", "size"), n_cells_possible=("possible", "sum"),
               pct_cells_impossible=("impossible", "mean"), p_feasible_mean=("p_feasible", "mean"),
               p_spell_mean=("p_spell", "mean"), p_hit_window_mean=("p_hit_window", "mean"),
               window_overlap_days_mean=("window_overlap_mean", "mean"),
               longest_len_median=("longest_len_median", "median"),
               longest_start_das_median=("longest_start_das_median", "median"),
               longest_end_das_median=("longest_end_das_median", "median"))
    cz = cells.assign(possible=(cells.impossible == 0).astype(int))
    summ = pd.concat([cz.groupby(keys + ["aez"]).agg(**agg).reset_index(),
                      cz.groupby(keys).agg(**agg).reset_index().assign(aez="ALL")], ignore_index=True)
    summ["pct_cells_impossible"] *= 100
    sp = shits[shits.impossible == 0]
    sh = pd.concat([sp.groupby(keys + ["aez", "stage_idx", "stage"])["p_hit"].mean().reset_index(),
                    sp.groupby(keys + ["stage_idx", "stage"])["p_hit"].mean().reset_index().assign(aez="ALL")],
                   ignore_index=True).rename(columns={"p_hit": "p"})
    sh = sh.merge(st_df[["crop", "cycle", "stage_idx", "stage_name", "das_start", "das_end", "overlaps_window"]],
                  on=["crop", "cycle", "stage_idx"], how="left")
    top = sh.sort_values("p", ascending=False).groupby(keys + ["aez"]).head(1)
    top = top[keys + ["aez", "stage", "stage_name", "das_start", "das_end", "p"]].rename(
        columns={"stage": "most_hit_stage", "stage_name": "most_hit_stage_name", "das_start": "most_hit_das_start",
                 "das_end": "most_hit_das_end", "p": "most_hit_p"})
    summ = summ.merge(top, on=keys + ["aez"], how="left").merge(
        st_df.groupby(["crop", "cycle"]).first()[["window_das_start", "window_das_end", "window_stages"]].reset_index(),
        on=["crop", "cycle"], how="left")
    summ.to_csv(out / "aez_summary.csv", index=False)
    sh.to_csv(out / "aez_stage_hits.csv", index=False)
    logger.info("Written aez_summary.csv, aez_stage_hits.csv, cell_summary.parquet, cell_stage_hits.parquet")

    # ---- figures
    png = out / "png"
    png.mkdir(exist_ok=True)
    aez_order = [aez_lab[k] for k in sorted(aez_lab)] + ["ALL"]
    aez_order = [x for x in aez_order if x in set(summ.aez)]
    for c in a.crops:
        for az in aez_order:
            h = sh[(sh.crop == c) & (sh.aez == az)].rename(columns={"sow": "sow_abs"})
            h = h.assign(sow=h.sow_abs - a.day0)
            tag = "national" if az == "ALL" else az
            plot_stage_heatmaps(png / f"stage_hits_{c}_{_slug(tag)}.png", c, st_df, h, cycles, sows, a.day0,
                                f"{a.iso3} {tag}: P(longest dry spell >= {min_spell[c]} d hits stage), "
                                f"mean over possible cells")
        plot_window_maps(png / f"map_window_hit_{c}.png", c, sets[c], cycles, sows, a.day0, lon_c, lat_c,
                         bnd, analysed)
        plot_aez_curves(png / f"aez_window_hit_{c}.png", c, summ.assign(sow=summ.sow - a.day0), cycles, sows,
                        a.day0, aez_order)
    aez_plot = np.where(analysed & (aez >= 0), aez, np.nan).astype(float)
    codes = sorted(aez_lab)
    if codes:
        C.plot_map(png / "aez.png", aez_plot, lon_c, lat_c, f"AEZ used for the summary - {aez_src}",
                   boundaries=bnd, categorical=[(k, SERIES[i % len(SERIES)], aez_lab[k]) for i, k in enumerate(codes)])

    # ---- console digest: most hit stage, national
    nat = summ[summ.aez == "ALL"]
    for c in a.crops:
        logger.info(f"--- {c} (national, possible cells) ---")
        for r in nat[nat.crop == c].itertuples():
            logger.info(f"  {r.cycle:>3} d  sow +{r.sow:<3} impossible {r.pct_cells_impossible:5.1f}%  "
                        f"P(hit window) {r.p_hit_window_mean:.2f}  most hit: {r.most_hit_stage} "
                        f"({r.most_hit_stage_name}, DAS {r.most_hit_das_start:.0f}-{r.most_hit_das_end:.0f}) "
                        f"p={r.most_hit_p:.2f}")
    logger.info(f"STEP4 done in {(time.time() - t0) / 60:.1f} min -> {out}")


def _slug(s):
    return "".join(ch if ch.isalnum() else "_" for ch in str(s)).strip("_")[:60]


if __name__ == "__main__":
    main()
