#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9 STEP 6 - dry spells inside the (major) rainy season: maps, PDFs, latitude and zone summaries
=============================================================================================

Independent of the crops (step 4): for every valid season of step 3, the dry spells (< DRY_MM,
missing days break spells) are clipped to the season window
    [onset + SPELL_STATS_EXCLUDE_FIRST, demise - SPELL_STATS_EXCLUDE_LAST]
(demise = rainfall demise or NDVI-adjusted demise, SPELL_STATS_DEMISE) and kept if the clipped
spell lasts >= SPELL_STATS_MIN days. Days are counted after the onset (onset = day 0).

Per season:
  n_spells          number of qualifying spells (0 counts)
  first_start/len   start (days after onset) and duration of the 1st spell     (seasons with >= 1)
  last_start/len    start and duration of the last spell                       (seasons with >= 2)
  longest_start/len start and duration of the longest spell (ties -> earliest)  (seasons with >= 1)
  dry_frac          days in qualifying spells / window length

Per cell (maps, cells_spell_stats.nc, GeoTIFFs): median of each over the seasons where it is
defined (needs >= SPELL_STATS_MIN_COND such seasons), plus p_ge1 / p_ge2 (share of seasons with
>= 1 / >= 2 spells) and mean n_spells.

Pooled over all seasons of all cells of a group (exact, from 1-day histograms):
  by zone (SUMMARY_ZONES or --zones: aez8 / aez / koppen / regime / file) and by latitude band
  (LAT_BAND_DEG); "ALL" = the whole target.
  summary_by_zone.csv, summary_by_latitude.csv   n_cells, n_seasons, n_defined, mean, p10, p25,
                                                 median, p75, p90 per metric
  hist_by_zone.csv, hist_by_latitude.csv         the histograms (to redraw PDFs elsewhere)
  png/pdf_<metric>.png        probability density functions, by zone and by latitude band
  png/latitude_profile.png    median and interquartile range of every metric vs latitude
  png/map_<metric>.png        maps of the per-cell medians

Target: the whole region (default), or --iso3 / --bbox / --polygon / --point as in step 4.
Output: dryspell_v9/<region>/step06/<name>/   (name = region, ISO3 or --name)

  python v9_06_spell_stats.py --region ci_nga
  python v9_06_spell_stats.py --region ssa --iso3 KEN --zones koppen
"""

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import importlib.util
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v9_common as C   # noqa: E402

_spec = importlib.util.spec_from_file_location("step4", HERE / "v9_04_sowing_risk.py")
S4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S4)

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger("dryspell_v9")

# metric: (label, unit, histogram bin width, histogram max, condition)
METRICS = {
    "n_spells": ("Number of dry spells per season", "spells", 1, 40, "all"),
    "spell_len": ("Median duration of the dry spells of the season", "days", 0.5, 400, "ge1"),
    "first_start": ("Start of the 1st dry spell", "days after onset", 1, 400, "ge1"),
    "first_len": ("Duration of the 1st dry spell", "days", 1, 400, "ge1"),
    "last_start": ("Start of the last dry spell (seasons with >= 2)", "days after onset", 1, 400, "ge2"),
    "last_len": ("Duration of the last dry spell (seasons with >= 2)", "days", 1, 400, "ge2"),
    "longest_start": ("Start of the longest dry spell", "days after onset", 1, 400, "ge1"),
    "longest_len": ("Duration of the longest dry spell", "days", 1, 400, "ge1"),
    "dry_frac": ("Share of the season in dry spells", "fraction", 0.01, 1.0, "all"),
}
CAT = C.SERIES                        # brand colours, fixed order (v9_common.py / CLAUDE.md)
OTHER = C.OTHER
BLUE_ORDINAL = C.TEAL_ORDINAL          # latitude bands, south (light) -> north (dark)
INK, INK2, GRID = C.INK, C.INK_SOFT, C.GRID

_G = {}


def nbins(m):
    _, _, w, mx, _ = METRICS[m]
    return int(round(mx / w)) + 1


def to_bin(m, v):
    _, _, w, mx, _ = METRICS[m]
    return np.clip(np.round(np.asarray(v, float) / w), 0, nbins(m) - 1).astype(np.int64)


# =============================================================================
# PER SEASON
# =============================================================================

def season_metrics(sid, s, e, n_seasons, win_len):
    """
    sid, s, e: qualifying clipped spells (season index, start / end as days after onset), sorted by
    (sid, s). -> dict of per-season arrays (NaN where undefined).
    """
    L = e - s + 1
    out = {k: np.full(n_seasons, np.nan) for k in METRICS}
    n = np.bincount(sid, minlength=n_seasons)
    out["n_spells"] = n.astype(float)
    dry = np.bincount(sid, weights=L, minlength=n_seasons)
    out["dry_frac"] = np.where(win_len > 0, dry / np.maximum(win_len, 1), np.nan)
    if len(sid):
        u, i0 = np.unique(sid, return_index=True)
        i1 = np.r_[i0[1:], len(sid)] - 1
        out["first_start"][u], out["first_len"][u] = s[i0], L[i0]
        two = n[u] >= 2
        out["last_start"][u[two]], out["last_len"][u[two]] = s[i1[two]], L[i1[two]]
        o = np.lexsort((s, -L, sid))                       # longest first, ties -> earliest
        first = np.r_[True, sid[o][1:] != sid[o][:-1]]
        k = o[first]
        out["longest_start"][sid[k]], out["longest_len"][sid[k]] = s[k], L[k]
        med = pd.Series(L).groupby(sid).median()          # sid sorted -> groups in u order
        out["spell_len"][med.index.to_numpy()] = med.to_numpy()
    return out


# =============================================================================
# WORKER
# =============================================================================

def process_rows(r0, r1):
    import pyarrow.parquet as pq
    g = _G
    nlon = g["nlon"]
    nr = r1 - r0
    ncell = nr * nlon
    mask = g["mask"][r0:r1].ravel()
    t = pq.read_table(Path(g["season_dir"]) / f"part_r{r0:05d}.parquet",
                      columns=["row", "col", "onset_date", "demise_date", "demise_rain_date", "valid"])
    valid = t["valid"].to_numpy().astype(bool)
    se_cell = (t["row"].to_numpy().astype(np.int64) - r0) * nlon + t["col"].to_numpy()
    on = S4._date_to_index(t["onset_date"])
    de = S4._date_to_index(t["demise_rain_date" if C.SPELL_STATS_DEMISE == "rain" else "demise_date"])
    keep = valid & mask[se_cell]
    se_cell, on, de = se_cell[keep], on[keep], de[keep]
    o = np.lexsort((on, se_cell))
    se_cell, on, de = se_cell[o], on[o], de[o]
    del t
    w0 = on + C.SPELL_STATS_EXCLUDE_FIRST
    w1 = de - C.SPELL_STATS_EXCLUDE_LAST
    win_len = np.maximum(w1 - w0 + 1, 0)

    t = pq.read_table(Path(g["spell_dir"]) / f"part_r{r0:05d}.parquet", columns=["row", "col", "start", "end"])
    sp_cell = (t["row"].to_numpy().astype(np.int64) - r0) * nlon + t["col"].to_numpy()
    sp_s, sp_e = t["start"].to_numpy().astype(np.int64), t["end"].to_numpy().astype(np.int64)
    k = mask[sp_cell]
    sp_cell, sp_s, sp_e = sp_cell[k], sp_s[k], sp_e[k]
    del t
    pi, qi = S4._pair_spells(sp_cell, sp_s, sp_e, se_cell, on, de)
    cs, ce = np.maximum(sp_s[pi], w0[qi]), np.minimum(sp_e[pi], w1[qi])
    ok = ce - cs + 1 >= C.SPELL_STATS_MIN
    sid, s, e = qi[ok], (cs - on[qi])[ok], (ce - on[qi])[ok]
    oo = np.lexsort((s, sid))
    sid, s, e = sid[oo], s[oo], e[oo]
    sm = season_metrics(sid, s, e, len(on), win_len)

    # ---- per cell
    nv = np.bincount(se_cell, minlength=ncell)
    cells = {"n_seasons": nv.astype(np.float32)}
    df = pd.DataFrame({"c": se_cell, **sm})
    med = df.groupby("c").median()
    cnt = df.groupby("c").count()
    for m in METRICS:
        a = np.full(ncell, np.nan, np.float32)
        okc = cnt[m] >= (C.MIN_VALID_SEASONS if METRICS[m][4] == "all" else C.SPELL_STATS_MIN_COND)
        idx = med.index.to_numpy()
        a[idx] = np.where(okc, med[m], np.nan)
        cells[f"{m}_median"] = a
    enough = nv >= C.MIN_VALID_SEASONS
    for kk, thr in (("p_ge1", 1), ("p_ge2", 2)):
        x = np.bincount(se_cell, weights=sm["n_spells"] >= thr, minlength=ncell) / np.maximum(nv, 1)
        cells[kk] = np.where(enough, x, np.nan).astype(np.float32)
    cells["n_spells_mean"] = np.where(enough, np.bincount(se_cell, weights=sm["n_spells"], minlength=ncell)
                                      / np.maximum(nv, 1), np.nan).astype(np.float32)
    # only cells with enough seasons enter the maps and the pooled statistics
    use = enough[se_cell]

    # ---- pooled histograms by group (zone index, latitude band index)
    hist = {}
    for gname in ("zone", "lat"):
        gi = g[f"{gname}_idx"][r0:r1].ravel()[se_cell]
        ng = g[f"n_{gname}"]
        for m in METRICS:
            v = sm[m]
            d = use & np.isfinite(v) & (gi >= 0)
            h = np.zeros((ng, nbins(m)), np.int64)
            np.add.at(h, (gi[d], to_bin(m, v[d])), 1)
            hist[(gname, m)] = h
        hist[(gname, "_seasons")] = np.bincount(gi[use & (gi >= 0)], minlength=ng)
        cg = g[f"{gname}_idx"][r0:r1].ravel()
        hist[(gname, "_cells")] = np.bincount(cg[enough & mask & (cg >= 0)], minlength=ng)
    return r0, r1, {k: v.reshape(nr, nlon) for k, v in cells.items()}, hist, int(len(on)), int(len(sid))


# =============================================================================
# STATISTICS FROM HISTOGRAMS
# =============================================================================

def hist_stats(m, h):
    """Exact quantiles of binned values (1-day bins for days): first bin where the cumulative count
    reaches q x n."""
    _, _, w, _, _ = METRICS[m]
    n = h.sum()
    if n == 0:
        return dict(n_defined=0, mean=np.nan, p10=np.nan, p25=np.nan, median=np.nan, p75=np.nan, p90=np.nan)
    x = np.arange(len(h)) * w
    cum = np.cumsum(h)
    q = {f"p{int(p * 100)}": x[np.searchsorted(cum, p * n)] for p in (0.10, 0.25, 0.75, 0.90)}
    return dict(n_defined=int(n), mean=float((h * x).sum() / n), p10=q["p10"], p25=q["p25"],
                median=x[np.searchsorted(cum, 0.5 * n)], p75=q["p75"], p90=q["p90"])


def summary_table(hist, gname, labels, unit_col):
    rows = []
    groups = list(range(len(labels))) + ["ALL"]
    for gi in groups:
        lab = "ALL" if gi == "ALL" else labels[gi]
        sel = (lambda a: a.sum(0)) if gi == "ALL" else (lambda a, gi=gi: a[gi])
        n_cells, n_seas = int(np.sum(sel(hist[(gname, "_cells")]))), int(np.sum(sel(hist[(gname, "_seasons")])))
        if n_seas == 0:
            continue
        for m in METRICS:
            rows.append({unit_col: lab, "metric": m, "label": METRICS[m][0], "metric_unit": METRICS[m][1],
                         "n_cells": n_cells, "n_seasons": n_seas, **hist_stats(m, sel(hist[(gname, m)]))})
    return pd.DataFrame(rows)


def hist_table(hist, gname, labels, unit_col):
    rows = []
    for m in METRICS:
        h = hist[(gname, m)]
        _, _, w, _, _ = METRICS[m]
        for gi, lab in enumerate(labels):
            nz = np.nonzero(h[gi])[0]
            rows += [{unit_col: lab, "metric": m, "value": round(b * w, 4), "count": int(h[gi, b])} for b in nz]
    return pd.DataFrame(rows)


# =============================================================================
# FIGURES
# =============================================================================

def _plt():
    C.brand_style()
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.titlecolor": INK})
    return plt


def density(m, h):
    """Histogram -> probability density (per unit), lightly smoothed for day metrics."""
    _, _, w, _, _ = METRICS[m]
    n = h.sum()
    if n == 0:
        return None
    d = h / (n * w)
    if m not in ("n_spells",) and C.PDF_SMOOTH_DAYS > 0:
        from scipy.ndimage import gaussian_filter1d
        sigma = C.PDF_SMOOTH_DAYS / w if "day" in METRICS[m][1] else 2.0   # in bins: days, or 0.02 (fraction)
        d = gaussian_filter1d(d.astype(float), sigma, mode="constant")
    return d


def _style(ax):
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def plot_pdfs(png, hist, zone_series, lat_series, title_extra):
    """One figure per metric: PDFs by zone (left) and by latitude band (right)."""
    plt = _plt()
    for m, (label, unit, w, mx, cond) in METRICS.items():
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6), sharey=True)
        xmax = 0
        for ax, (gname, series, ttl) in zip(axes, (("zone", zone_series, "by zone"),
                                                   ("lat", lat_series, "by latitude band"))):
            for lab, idxs, col, lw in series:
                h = hist[(gname, m)][idxs].sum(0) if len(idxs) else None
                d = density(m, h) if h is not None else None
                if d is None:
                    continue
                x = np.arange(len(d)) * w
                nz = np.nonzero(h)[0]
                xmax = max(xmax, x[nz.max()] if len(nz) else 0)
                if m == "n_spells":
                    ax.step(x, d, where="mid", color=col, linewidth=lw, label=f"{lab} (n={h.sum():,})")
                else:
                    ax.plot(x, d, color=col, linewidth=lw, label=f"{lab} (n={h.sum():,})")
            ax.set_title(ttl, loc="left", fontsize=9)
            ax.set_xlabel(unit)
            _style(ax)
            ax.legend(frameon=False, fontsize=6.5, loc="upper right")
        axes[0].set_ylabel(f"probability density (per {'spell' if m == 'n_spells' else unit.split()[0]})")
        ha = hist[("zone", m)].sum(0)
        hi = np.searchsorted(np.cumsum(ha), 0.995 * ha.sum()) * w if ha.sum() else mx
        for ax in axes:
            ax.set_xlim(0, min(mx, max(hi * 1.05, w * 3)))
            ax.set_ylim(bottom=0)
        fig.suptitle(f"{label} - {title_extra}", x=0.01, ha="left", fontsize=10, color=INK)
        fig.tight_layout()
        fig.savefig(png / f"pdf_{m}.png", dpi=C.FIG_DPI, bbox_inches="tight", facecolor="white")
        plt.close(fig)


def plot_latitude_profile(path, lat_summary, title_extra):
    plt = _plt()
    d = lat_summary[lat_summary.latitude_band != "ALL"].copy()
    d["lat"] = d.latitude_band.str.split(" to ").str[0].astype(float) + C.LAT_BAND_DEG / 2
    ms = ["n_spells", "longest_start", "first_start", "last_start",      # top: how many, and when
          "spell_len", "longest_len", "first_len", "last_len"]           # bottom: how long
    fig, axes = plt.subplots(2, 4, figsize=(12, 6.2), sharex=True)
    for ax, m in zip(axes.ravel(), ms):
        x = d[d.metric == m].sort_values("lat")
        ax.fill_between(x.lat, x.p25, x.p75, color=C.BRAND["light_blue"], alpha=0.45, linewidth=0, label="interquartile range")
        ax.plot(x.lat, x["median"], color=C.BRAND["teal"], linewidth=2, marker="o", markersize=3.5, label="median")
        if METRICS[m][4] == "all":                      # mostly zeros: the mean carries the signal
            ax.plot(x.lat, x["mean"], color=C.BRAND["orange"], linewidth=2, marker="o", markersize=3.5, label="mean")
            ax.legend(frameon=False, fontsize=6.5)
        ax.set_title(METRICS[m][0], loc="left", fontsize=8)
        ax.set_ylabel(METRICS[m][1], fontsize=7)
        _style(ax)
    for ax in axes[-1]:
        ax.set_xlabel("latitude (band centre, deg N)")
    axes[0, 0].legend(frameon=False, fontsize=7)
    fig.suptitle(f"Dry spells in the rainy season by latitude - {title_extra}", x=0.01, ha="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=C.FIG_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =============================================================================
# MAIN
# =============================================================================

MAPS = [
    # var, title, colour bar label, cmap, vmin, vmax
    ("n_spells_median", "Median number of dry spells per season", "spells / season", "brand_risk", 0, None),
    ("n_spells_mean", "Mean number of dry spells per season", "spells / season", "brand_risk", 0, None),
    ("p_ge1", "P(at least one dry spell in the season)", "probability", "brand_teal", 0, 1),
    ("p_ge2", "P(two or more dry spells in the season)", "probability", "brand_teal", 0, 1),
    ("spell_len_median", "Median duration of the dry spells of a season (median over seasons)", "days",
     "brand_risk", None, None),
    ("first_start_median", "Median start of the 1st dry spell", "days after onset", "brand_teal", 0, None),
    ("first_len_median", "Median duration of the 1st dry spell", "days", "brand_risk", None, None),
    ("last_start_median", "Median start of the last dry spell (seasons with >= 2)", "days after onset", "brand_teal", 0, None),
    ("last_len_median", "Median duration of the last dry spell (seasons with >= 2)", "days", "brand_risk", None, None),
    ("longest_start_median", "Median start of the longest dry spell", "days after onset", "brand_teal", 0, None),
    ("longest_len_median", "Median duration of the longest dry spell", "days", "brand_risk", None, None),
    ("dry_frac_median", "Median share of the season in dry spells", "fraction", "brand_risk", 0, None),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ci_nga")
    tg = ap.add_mutually_exclusive_group()
    tg.add_argument("--iso3", default=None)
    tg.add_argument("--bbox", nargs=4, type=float, default=None, metavar=("W", "S", "E", "N"))
    tg.add_argument("--polygon", default=None)
    tg.add_argument("--point", nargs=2, type=float, default=None, metavar=("LAT", "LON"))
    ap.add_argument("--polygon_field", default=None)
    ap.add_argument("--polygon_value", default=None)
    ap.add_argument("--name", default=None, help="output folder (default: region name / ISO3 / ...)")
    ap.add_argument("--zones", default=C.SUMMARY_ZONES)
    ap.add_argument("--zone_legend", default=None)
    ap.add_argument("--zone_field", default="zone")
    ap.add_argument("--workers", type=int, default=max(1, min(32, mp.cpu_count() - 4)))
    a = ap.parse_args()

    rdir = C.region_dir(a.region)
    s3 = rdir / "step03"
    whole = not (a.iso3 or a.bbox or a.polygon or a.point)
    name = a.name or (a.region if whole else S4.default_name(a))
    out = rdir / "step06" / name
    C.setup_logging(out / "step06.log")
    t0 = time.time()
    if not (s3 / "seasons").exists():
        sys.exit(f"{s3 / 'seasons'} not found - run v9_03_spells_seasons.py first")
    if C.SPELL_STATS_MIN < C.STEP1_MIN_SPELL:
        sys.exit(f"SPELL_STATS_MIN must be >= STEP1_MIN_SPELL ({C.STEP1_MIN_SPELL})")
    meta = C.read_json(s3 / "meta.json")
    with xr.open_dataset(s3 / "grid_meta.nc") as d:
        gm = d.load()
    lon, lat = gm.lon.values, gm.lat.values
    logger.info("=" * 70)
    logger.info(f"v9 STEP6 dry spells in the season  region={a.region} target={name} zones={a.zones}")
    logger.info(f"  spells >= {C.SPELL_STATS_MIN} d (< {C.DRY_MM} mm), window [onset + {C.SPELL_STATS_EXCLUDE_FIRST}, "
                f"{C.SPELL_STATS_DEMISE} demise - {C.SPELL_STATS_EXCLUDE_LAST}], latitude bands {C.LAT_BAND_DEG} deg")
    logger.info("=" * 70)

    if whole:
        tmask, bnd, target = np.ones((len(lat), len(lon)), bool), C.load_boundaries(meta["bbox"]), {"kind": "region"}
    else:
        tmask, bnd, target = S4.target_mask(a, lon, lat, meta["bbox"])
    cell_ok = gm["reason"].values == C.REASON_OK
    mask = tmask & cell_ok
    if not mask.any():
        C.write_json(out / "status.json", {"unit": name, "target": target, "status": "skipped",
                                           "reason": "no usable cell"})
        sys.exit(3)

    # zones on the whole region grid, latitude bands
    zone, zone_lab, zone_src = S4.load_zones(a.zones, lon, lat, tmask, gm["regime"].values.astype(np.int8),
                                             a.zone_field, a.zone_legend)
    codes = sorted(zone_lab)
    zlabels = [zone_lab[c] for c in codes] + ["unassigned"]
    zi = np.full(zone.shape, -1, np.int32)
    for k, c in enumerate(codes):
        zi[zone == c] = k
    zi[(zone < 0) & tmask] = len(codes)
    b = C.LAT_BAND_DEG
    band_lo = np.floor(lat / b) * b
    bands = np.unique(band_lo[mask.any(1)])
    li_row = np.searchsorted(bands, band_lo)
    li_row = np.where(np.isin(band_lo, bands), li_row, -1)
    li = np.repeat(li_row[:, None], len(lon), 1)
    llabels = [f"{v:g} to {v + b:g}" for v in bands]
    logger.info(f"  zones: {zone_src}; {len(codes)} classes; {len(bands)} latitude bands")

    _G.update(nlon=len(lon), mask=mask, zone_idx=zi, lat_idx=li, n_zone=len(zlabels), n_lat=len(bands),
              spell_dir=str(s3 / "spells"), season_dir=str(s3 / "seasons"))
    rows = np.where(mask.any(1))[0]
    chunks = [tuple(c) for c in meta["chunks"] if c[1] > rows.min() and c[0] <= rows.max()]
    grids, hist = {}, {}
    n_seasons = n_spells = 0
    with ProcessPoolExecutor(max_workers=max(1, min(a.workers, len(chunks))),
                             mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(process_rows, r0, r1) for r0, r1 in chunks]
        for i, f in enumerate(as_completed(futs), 1):
            r0, r1, cells, h, ns, nsp = f.result()
            for k, v in cells.items():
                grids.setdefault(k, np.full((len(lat), len(lon)), np.nan, np.float32))[r0:r1] = v
            for k, v in h.items():
                hist[k] = hist[k] + v if k in hist else v
            n_seasons += ns
            n_spells += nsp
            if i % 20 == 0 or i == len(chunks):
                logger.info(f"  {i}/{len(chunks)} chunks")
    logger.info(f"  {n_seasons:,} valid seasons, {n_spells:,} qualifying spells")

    # ---- per-cell outputs (target box)
    out.mkdir(parents=True, exist_ok=True)
    rr, cc = np.nonzero(tmask)
    sl = (slice(rr.min(), rr.max() + 1), slice(cc.min(), cc.max() + 1))
    lon_c, lat_c = lon[sl[1]], lat[sl[0]]
    inside = tmask[sl]
    dv = {k: (("lat", "lon"), np.where(inside, v[sl], np.nan)) for k, v in grids.items()}
    dv["zone"] = (("lat", "lon"), np.where(inside, zone[sl], -1).astype(np.int16))
    ds = xr.Dataset(dv, coords={"lat": lat_c, "lon": lon_c},
                    attrs={"target": name, "zone_source": zone_src, "zone_labels": str(zone_lab),
                           "spell_min_days": C.SPELL_STATS_MIN, "dry_mm": C.DRY_MM,
                           "window": f"[onset + {C.SPELL_STATS_EXCLUDE_FIRST}, {C.SPELL_STATS_DEMISE} demise - "
                                     f"{C.SPELL_STATS_EXCLUDE_LAST}]", "days": "days after onset (onset = 0)"})
    ds.to_netcdf(out / "cells_spell_stats.nc", encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
    png = out / "png"
    png.mkdir(exist_ok=True)
    (out / "cog").mkdir(exist_ok=True)
    reason = np.where(inside, gm["reason"].values[sl], 255)
    big = inside.sum() >= 4
    for var, title, lab, cmap, vmin, vmax in MAPS:
        arr = ds[var].values.astype(np.float32)
        C.save_geotiff(out / "cog" / f"{var}.tif", arr, lon_c, lat_c)
        if big:
            C.plot_map(png / f"map_{var}.png", arr, lon_c, lat_c, f"{title} - {name}", lab, cmap=cmap,
                       vmin=vmin, vmax=vmax, boundaries=bnd, reason=reason)

    # ---- pooled summaries
    zs = summary_table(hist, "zone", zlabels, "zone")
    zs.insert(0, "zone_scheme", a.zones if a.zones in ("aez8", "aez", "koppen", "regime") else Path(a.zones).name)
    ls_ = summary_table(hist, "lat", llabels, "latitude_band")
    for df in (zs, ls_):
        df.insert(0, "unit", name)
    zs.to_csv(out / "summary_by_zone.csv", index=False)
    ls_.to_csv(out / "summary_by_latitude.csv", index=False)
    hist_table(hist, "zone", zlabels, "zone").to_csv(out / "hist_by_zone.csv", index=False)
    hist_table(hist, "lat", llabels, "latitude_band").to_csv(out / "hist_by_latitude.csv", index=False)

    # ---- PDFs: zones = the 4 largest (brand colours, fixed order by size) + "other"; latitude: PDF_LAT_BAND_DEG bands
    sizes = hist[("zone", "_seasons")]
    order = [k for k in np.argsort(-sizes, kind="stable") if sizes[k] > 0]
    nc = len(CAT)                                     # brand rule: 4 coloured series, the rest grouped
    zser = [(zlabels[k], [k], CAT[i], 1.6) for i, k in enumerate(order[:nc])]
    if len(order) > nc:
        zser.append(("other zones", order[nc:], OTHER, 1.6))
    zser.append(("ALL", list(range(len(zlabels))), INK, 2.2))
    pb = C.PDF_LAT_BAND_DEG
    coarse = np.floor(bands / pb) * pb
    cu = np.unique(coarse)
    ramp = [BLUE_ORDINAL[int(round(j))] for j in np.linspace(0, len(BLUE_ORDINAL) - 1, len(cu))] if len(cu) else []
    lser = [(f"{v:g} to {v + pb:g} N", list(np.nonzero(coarse == v)[0]), ramp[i], 1.6) for i, v in enumerate(cu)]
    plot_pdfs(png, hist, zser, lser, f"{name}, {n_seasons:,} seasons (spells >= {C.SPELL_STATS_MIN} d)")
    if len(bands) >= 2:
        plot_latitude_profile(png / "latitude_profile.png", ls_, name)

    allz = zs[zs.zone == "ALL"].set_index("metric")
    for m in METRICS:
        r = allz.loc[m]
        logger.info(f"  {m:<14} median {r['median']:>6.2f}  IQR {r.p25:>6.2f}-{r.p75:<6.2f}  "
                    f"({r.n_defined:,} of {r.n_seasons:,} seasons)")
    C.write_json(out / "status.json", {"unit": name, "target": target, "status": "ok",
                                       "n_cells": int(mask.sum()), "n_seasons": n_seasons, "n_spells": n_spells,
                                       "zone_source": zone_src, "minutes": round((time.time() - t0) / 60, 2)})
    logger.info(f"STEP6 done in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()
