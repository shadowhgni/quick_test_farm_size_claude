#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9 STEP 2 - NDVI growing seasons (number, start, end) on the CHIRPS grid
========================================================================

Data: PKU GIMMS NDVI v1.2 (half-monthly, 1/12 deg; the GIMMS NDVI3g record), cropped to the
region by v9_01_download.py. Approach of Vrieling, de Leeuw & Said (2013, Remote Sens. 5, 982):
the number of growing seasons from the mean annual NDVI profile, and each year's start (SOS) and
end (EOS) of season with a variable threshold inside a search window around each mean peak, which
handles bimodal areas. Parameters are in v9_config.py section H; they follow the paper's
description, not its code (which is not published), and are reported in the outputs.

Per NDVI pixel:
  1. NDVI (no-data and QC snow/cloud = missing) -> linear interpolation of gaps <= NDVI_MAX_GAP
     half-months -> running median of NDVI_SMOOTH half-months.
  2. Mean profile over the years (24 half-months). Peaks: circular local maxima >= NDVI_PEAK_MIN_SEP
     apart; the two highest are kept. A peak is a season when it rises >= NDVI_MIN_AMPLITUDE above
     BOTH troughs around it. 2 seasons -> windows trough-to-trough; 1 season -> the whole year
     from the annual minimum. Mean NDVI < NDVI_MIN_MEAN -> no vegetation signal (0 seasons).
  3. Every year and season, inside its window: peak; SOS = upward crossing of
     min_before + NDVI_SOS_THRESHOLD x (peak - min_before); EOS = downward crossing of
     min_after + NDVI_EOS_THRESHOLD x (peak - min_after); crossings interpolated between the
     half-month mid-dates.
  4. Every CHIRPS 0.05 deg cell takes the NDVI pixel it lies in (NDVI_REGRID = "nearest").

Output: dryspell_v9/<region>/step02/ndvi_phenology.nc
  ndvi_n_seasons (lat, lon)                    0 / 1 / 2
  ndvi_trough_ratio (lat, lon)                 mid-season trough / smaller peak of the mean profile
  sos, eos (year, slot, lat, lon)              day index since 1981-01-01 (-1 = none); slot 0/1 =
                                               the two seasons, ordered by the calendar date of their peak
  ndvi_peak_doy (slot, lat, lon), ndvi_amplitude (slot, lat, lon)
and diagnostics/ndvi_*.png

Usage
-----
  python v9_02_ndvi_phenology.py --region ci_nga --workers 8
"""

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
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
import v9_common as C

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger("dryspell_v9")
NP = 24          # half-months per year
_G = {}


# =============================================================================
# CALENDAR
# =============================================================================

def period_mid_days(y0, n_years):
    """Day index (since ORIGIN) of the middle of every half-month, plus one extra year for crossings."""
    out = []
    for y in range(y0, y0 + n_years + 1):
        for m in range(1, 13):
            first = np.datetime64(f"{y}-{m:02d}-01")
            nxt = np.datetime64(f"{y + (m == 12)}-{(m % 12) + 1:02d}-01")
            mid1 = first + np.timedelta64(7, "D")
            mid2 = first + (nxt - first + np.timedelta64(15, "D")) // 2
            out += [(mid1 - C.ORIGIN).astype(int), (mid2 - C.ORIGIN).astype(int)]
    return np.array(out, dtype=np.float64)


# =============================================================================
# PROFILE ANALYSIS (pure numpy, testable)
# =============================================================================

def seasons_from_profile(prof, min_amp=None, min_sep=None):
    """
    prof (24,) mean NDVI profile -> dict(n, peaks, windows [(start, length)], amps, ratio)
    windows are in half-months (start 0..23, length 1..24), trough-to-trough.
    """
    min_amp = C.NDVI_MIN_AMPLITUDE if min_amp is None else min_amp
    min_sep = C.NDVI_PEAK_MIN_SEP if min_sep is None else min_sep
    out = dict(n=0, peaks=[], windows=[], amps=[], ratio=np.nan)
    if not np.isfinite(prof).all() or prof.mean() < C.NDVI_MIN_MEAN:
        return out
    n = NP
    left, right = np.roll(prof, 1), np.roll(prof, -1)
    cand = np.nonzero((prof >= left) & (prof > right))[0]
    keep = []
    for i in sorted(cand, key=lambda k: -prof[k]):
        if all(min(abs(i - j), n - abs(i - j)) >= min_sep for j in keep):
            keep.append(int(i))
    tmin = int(np.argmin(prof))
    if len(keep) >= 2:
        a, b = sorted(keep[:2])
        arc_ab = np.arange(a, b + 1)
        arc_ba = np.r_[np.arange(b, n), np.arange(0, a + 1)]
        t1 = int(arc_ab[np.argmin(prof[arc_ab])])          # trough between a and b
        t2 = int(arc_ba[np.argmin(prof[arc_ba])])          # trough between b and a
        amp_a = prof[a] - max(prof[t1], prof[t2])
        amp_b = prof[b] - max(prof[t1], prof[t2])
        out["ratio"] = float(max(prof[t1], prof[t2]) / min(prof[a], prof[b]))
        if amp_a >= min_amp and amp_b >= min_amp:
            out.update(n=2, peaks=[a, b], amps=[float(amp_a), float(amp_b)],
                       windows=[(t2, (t1 - t2) % n + 1), (t1, (t2 - t1) % n + 1)])
            return out
    pk = int(np.argmax(prof))
    amp = float(prof[pk] - prof[tmin])
    if amp >= min_amp:
        out.update(n=1, peaks=[pk], amps=[amp], windows=[(tmin, n + 1)])
    return out


def crossings(seg, mids, thr_sos, thr_eos):
    """
    seg (m, L) NDVI in each pixel's window, mids (m, L) mid-day of each half-month.
    Returns SOS, EOS day indices (float, NaN = none).
    """
    m, L = seg.shape
    ok = np.isfinite(seg)
    s = np.where(ok, seg, -np.inf)
    ipk = np.argmax(s, 1)
    rows = np.arange(m)
    pk = seg[rows, ipk]
    k = np.arange(L)[None, :]
    before = (k <= ipk[:, None]) & ok
    after = (k >= ipk[:, None]) & ok
    lmin = np.min(np.where(before, seg, np.inf), 1)
    rmin = np.min(np.where(after, seg, np.inf), 1)
    th_s = lmin + thr_sos * (pk - lmin)
    th_e = rmin + thr_eos * (pk - rmin)
    # SOS: last index j < peak with seg[j] < th_s, crossing between j and j+1
    below_s = before & (seg < th_s[:, None]) & (k < ipk[:, None])
    js = np.where(below_s.any(1), L - 1 - np.argmax(below_s[:, ::-1], 1), -1)
    # EOS: first index j > peak with seg[j] < th_e, crossing between j-1 and j
    below_e = after & (seg < th_e[:, None]) & (k > ipk[:, None])
    je = np.where(below_e.any(1), np.argmax(below_e, 1), -1)
    sos = np.full(m, np.nan)
    eos = np.full(m, np.nan)
    v = js >= 0
    if v.any():
        j = js[v]; r = rows[v]
        y0_, y1_ = seg[r, j], seg[r, j + 1]
        f = np.clip((th_s[v] - y0_) / np.where(y1_ != y0_, y1_ - y0_, 1), 0, 1)
        sos[v] = mids[r, j] + f * (mids[r, j + 1] - mids[r, j])
    v = je >= 0
    if v.any():
        j = je[v]; r = rows[v]
        y0_, y1_ = seg[r, j - 1], seg[r, j]
        f = np.clip((y0_ - th_e[v]) / np.where(y0_ != y1_, y0_ - y1_, 1), 0, 1)
        eos[v] = mids[r, j - 1] + f * (mids[r, j] - mids[r, j - 1])
    good = (pk - lmin > 0) & (pk - rmin > 0)
    sos[~good] = np.nan
    eos[~good] = np.nan
    return sos, eos


# =============================================================================
# WORKER
# =============================================================================

def process_rows(r0, r1):
    g = _G
    mm = np.memmap(g["cache"], dtype=np.uint16, mode="r", shape=g["shape"])
    raw = np.asarray(mm[:, r0:r1, :]).astype(np.float32)
    del mm
    P, nr, nx = raw.shape
    n = nr * nx
    x = raw.reshape(P, n)
    x[x == C.NDVI_FILL] = np.nan
    x *= C.NDVI_SCALE
    df = pd.DataFrame(x)
    df = df.interpolate(axis=0, limit=C.NDVI_MAX_GAP, limit_area="inside")
    if C.NDVI_SMOOTH > 1:
        df = df.rolling(C.NDVI_SMOOTH, center=True, min_periods=max(1, C.NDVI_SMOOTH // 2 + 1)).median()
    x = df.values.astype(np.float32)
    del df
    Y = P // NP
    prof = np.nanmean(x[: Y * NP].reshape(Y, NP, n), 0)          # (24, n)
    nseas = np.zeros(n, np.int8)
    ratio = np.full(n, np.nan, np.float32)
    peak = np.full((2, n), -1, np.int16)
    amp = np.full((2, n), np.nan, np.float32)
    wins = np.full((2, 2, n), -1, np.int16)                       # (slot, start/length, n)
    for c in range(n):
        r = seasons_from_profile(prof[:, c])
        nseas[c], ratio[c] = r["n"], r["ratio"]
        order = np.argsort(r["peaks"]) if r["n"] else []
        for slot, k in enumerate(order):
            peak[slot, c] = r["peaks"][k]
            amp[slot, c] = r["amps"][k]
            wins[slot, :, c] = r["windows"][k]
    sos = np.full((Y, 2, n), -1, np.int32)
    eos = np.full((Y, 2, n), -1, np.int32)
    mids_all = g["mids"]
    for slot in range(2):
        cells = np.nonzero(wins[slot, 1] > 0)[0]
        if not len(cells):
            continue
        st, ln = wins[slot, 0, cells].astype(np.int64), wins[slot, 1, cells].astype(np.int64)
        L = int(ln.max())
        k = np.arange(L)
        for yi in range(Y):
            idx = yi * NP + st[:, None] + k[None, :]                # absolute half-month index
            inside = (k[None, :] < ln[:, None]) & (idx < P)
            seg = np.where(inside, x[np.clip(idx, 0, P - 1), cells[:, None]], np.nan)
            mids = mids_all[np.clip(idx, 0, len(mids_all) - 1)]
            s_, e_ = crossings(seg, mids, C.NDVI_SOS_THRESHOLD, C.NDVI_EOS_THRESHOLD)
            sos[yi, slot, cells] = np.where(np.isfinite(s_), np.round(s_), -1)
            eos[yi, slot, cells] = np.where(np.isfinite(e_), np.round(e_), -1)
    res = dict(nseas=nseas.reshape(nr, nx), ratio=ratio.reshape(nr, nx), peak=peak.reshape(2, nr, nx),
               amp=amp.reshape(2, nr, nx), sos=sos.reshape(Y, 2, nr, nx), eos=eos.reshape(Y, 2, nr, nx))
    return r0, r1, res


# =============================================================================
# MAIN
# =============================================================================

def nearest_map(src, dst):
    """Index into ascending regular src centres for every dst coordinate (-1 outside)."""
    step = (src[-1] - src[0]) / (len(src) - 1)
    i = np.floor((dst - (src[0] - step / 2)) / step).astype(int)
    return np.where((i >= 0) & (i < len(src)), i, -1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ci_nga")
    ap.add_argument("--bbox", nargs=4, type=float)
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 4))
    ap.add_argument("--rows_per_task", type=int, default=16)
    a = ap.parse_args()
    name, bbox = C.parse_region(a.region, a.bbox)
    out = C.region_dir(name) / "step02"
    C.setup_logging(out / "step02.log")
    t0 = time.time()
    nd = C.data_dir("ndvi", name)
    if not (nd / "meta.json").exists():
        sys.exit(f"{nd / 'meta.json'} not found - run v9_01_download.py --region {name} (with USE_NDVI = True)")
    nm = C.read_json(nd / "meta.json")
    done = np.load(nd / "period_done.npy")
    lon_n, lat_n = np.array(nm["lon"]), np.array(nm["lat"])
    shape = (nm["n_periods"], len(lat_n), len(lon_n))
    y0, y1 = nm["years"]
    logger.info("=" * 70)
    logger.info(f"v9 STEP2 NDVI  region={name}  {nm['product']} {y0}-{y1}  grid {len(lon_n)}x{len(lat_n)}  "
                f"half-months {done.sum()}/{len(done)}")
    logger.info(f"  min amplitude {C.NDVI_MIN_AMPLITUDE}, peak separation {C.NDVI_PEAK_MIN_SEP} half-months, "
                f"SOS/EOS thresholds {C.NDVI_SOS_THRESHOLD}/{C.NDVI_EOS_THRESHOLD}, gaps <= {C.NDVI_MAX_GAP}, "
                f"median {C.NDVI_SMOOTH}")
    logger.info("=" * 70)
    if done.sum() < 0.9 * len(done):
        logger.warning("fewer than 90 % of the NDVI half-months are available - run v9_01_download.py again")
    _G.update(cache=str(nd / "ndvi_u16.dat"), shape=shape, mids=period_mid_days(y0, y1 - y0 + 1))
    ny, nx = shape[1:]
    Y = shape[0] // NP
    nseas = np.zeros((ny, nx), np.int8)
    ratio = np.full((ny, nx), np.nan, np.float32)
    peak = np.full((2, ny, nx), -1, np.int16)
    amp = np.full((2, ny, nx), np.nan, np.float32)
    sos = np.full((Y, 2, ny, nx), -1, np.int32)
    eos = np.full((Y, 2, ny, nx), -1, np.int32)
    chunks = [(r, min(r + a.rows_per_task, ny)) for r in range(0, ny, a.rows_per_task)]
    with ProcessPoolExecutor(max_workers=max(1, min(a.workers, len(chunks))), mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(process_rows, r0, r1) for r0, r1 in chunks]
        for i, f in enumerate(as_completed(futs), 1):
            r0, r1, res = f.result()
            nseas[r0:r1], ratio[r0:r1] = res["nseas"], res["ratio"]
            peak[:, r0:r1], amp[:, r0:r1] = res["peak"], res["amp"]
            sos[:, :, r0:r1], eos[:, :, r0:r1] = res["sos"], res["eos"]
            if i % 20 == 0 or i == len(chunks):
                logger.info(f"  {i}/{len(chunks)} chunks")

    # ---- to the CHIRPS grid (nearest = the NDVI pixel each cell lies in)
    cm = C.read_json(C.data_dir("chirps", name, "meta.json"))
    lon_c, lat_c = np.array(cm["lon"]), np.array(cm["lat"])
    ii, jj = nearest_map(lat_n, lat_c), nearest_map(lon_n, lon_c)
    I, J = np.meshgrid(np.clip(ii, 0, ny - 1), np.clip(jj, 0, nx - 1), indexing="ij")
    outside = (ii[:, None] < 0) | (jj[None, :] < 0)

    def take(a2, fill):
        v = a2[..., I, J]
        return np.where(outside, fill, v)

    years = np.arange(y0, y0 + Y)
    ds = xr.Dataset({
        "ndvi_n_seasons": (("lat", "lon"), take(nseas, 0).astype(np.int8)),
        "ndvi_trough_ratio": (("lat", "lon"), take(ratio, np.nan).astype(np.float32)),
        "ndvi_peak_doy": (("slot", "lat", "lon"), np.where(take(peak, -1) >= 0, take(peak, -1) * 15.2 + 7, -1).astype(np.int16)),
        "ndvi_amplitude": (("slot", "lat", "lon"), take(amp, np.nan).astype(np.float32)),
        "sos": (("year", "slot", "lat", "lon"), take(sos, -1).astype(np.int32)),
        "eos": (("year", "slot", "lat", "lon"), take(eos, -1).astype(np.int32)),
    }, coords={"year": years, "slot": [0, 1], "lat": lat_c, "lon": lon_c},
        attrs={"source": f"PKU GIMMS NDVI v1.2 {nm['product']} (Zenodo 8253971)", "years": f"{y0}-{y0 + Y - 1}",
               "method": "Vrieling et al. 2013 approach: seasons from the mean profile, variable-threshold SOS/EOS",
               "sos_eos": f"day index since {C.ORIGIN}, -1 = none; 'year' = year in which the search window starts",
               "settings": str({k: C.SETTINGS[k] for k in C.SETTINGS if k.startswith("NDVI")})})
    out.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out / "ndvi_phenology.nc", encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})

    dg = out / "diagnostics"
    bnd = C.load_boundaries(bbox)
    ns = ds.ndvi_n_seasons.values.astype(float)
    C.plot_map(dg / "ndvi_n_seasons.png", np.where(ns > 0, ns, np.nan), lon_c, lat_c,
               f"NDVI growing seasons per year ({nm['product']} {y0}-{y0 + Y - 1})", boundaries=bnd,
               categorical=[(1, "#c9b37e", "one season"), (2, "#2f6f4f", "two seasons")])
    e0 = ds.eos.isel(slot=0).values
    eos_doy = np.full(e0.shape[1:], np.nan)
    with np.errstate(invalid="ignore"):
        d = np.where(e0 >= 0, ((C.ORIGIN + e0.astype("timedelta64[D]")) - (C.ORIGIN + e0.astype("timedelta64[D]")).astype("datetime64[Y]")).astype(int), np.nan)
        eos_doy = np.nanmedian(d, 0)
    C.plot_map(dg / "ndvi_eos_slot0_doy.png", eos_doy, lon_c, lat_c, "Median NDVI end of season (first season)",
               "day of year", cmap="viridis", boundaries=bnd)
    logger.info(f"  NDVI pixels: no signal {(nseas == 0).sum():,}, one season {(nseas == 1).sum():,}, "
                f"two seasons {(nseas == 2).sum():,}")
    logger.info(f"STEP2 NDVI done in {(time.time() - t0) / 60:.1f} min -> {out / 'ndvi_phenology.nc'}")


if __name__ == "__main__":
    main()
