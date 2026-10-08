#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9 STEP 3 - dry spells, rainfall regime (refined with NDVI), major-season onset / demise
=======================================================================================

Reads the CHIRPS cache (step 1) and the NDVI phenology (step 2), one block of grid rows per
worker. All settings: v9_config.py sections D-H.

1. Dry spells: every run of >= STEP1_MIN_SPELL days with rain < DRY_MM (missing days break spells).
2. Rainfall regime from the 1981-2024 daily mean cycle smoothed over REGIME_SMOOTH_DAYS:
   ratio = mid-season trough / smaller peak; <= BIMODAL_MAX_RATIO bimodal, <= TRANSITION_MAX_RATIO
   transition, otherwise unimodal; mean rain < ARID_MM -> arid.
   REFINED WITH NDVI (REGIME_SOURCE, default "consensus"): a cell is bimodal only when rainfall has a
   trough (ratio <= TRANSITION_MAX_RATIO) AND the vegetation shows two growing seasons; a
   rainfall-bimodal cell with one NDVI season becomes transition (one season). Cells without an
   NDVI signal keep the rainfall regime.
3. Season window: unimodal / transition -> the whole year from the driest day; bimodal -> the
   MAJOR season between the driest day and the mid-season trough (MAJOR_SEASON_RULE).
4. Onset / demise per year, RADS method inside the window: S = cumsum(rain - window mean);
   onset = day after min(S) (not the window's first day), demise = day of max(S) after it;
   30 <= length <= 330 days; window covered >= WINDOW_MIN_COVER.
5. False start / false demise (always flagged; excluded when FALSE_*_EXCLUDE): >= FALSE_DRY_DAYS
   dry days (consecutive or in total, FALSE_DRY_MODE) in the first / last FALSE_WINDOW_DAYS days.
6. Demise adjusted with NDVI (DEMISE_ADJUST): the NDVI end of season closest to the rainfall
   demise (within DEMISE_MATCH_WINDOW) gives the vegetation lag; demise + clip(lag, 0,
   DEMISE_SHIFT_MAX), using the cell median lag ("median_offset") or each year's ("per_year").

Outputs (dryspell_v9/<region>/step03/)
  spells/part_rXXXXX.parquet   row, col, lat, lon, start, end, start_date, end_date, length, censored
  seasons/part_rXXXXX.parquet  row, col, lat, lon, year, onset_date, demise_date (adjusted),
                               demise_rain_date, ndvi_eos_date, demise_shift, false_start,
                               false_demise, valid, reason, season_len, regime, rain_regime,
                               ndvi_n_seasons, window_start_doy, window_len
  grid_meta.nc, day_has_data.npy, meta.json, diagnostics/*.png|tif

Usage
-----
  python v9_03_spells_seasons.py --region ci_nga --workers 8
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
import v9_common as C

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger("dryspell_v9")
NODATA = 65535
SCALE = 100.0
_G = {}


# =============================================================================
# CALENDAR
# =============================================================================

def noleap_doy(dates):
    """0..364; 29 Feb shares the index of 28 Feb."""
    t = pd.DatetimeIndex(dates)
    d = t.dayofyear.values - 1
    return np.where(t.is_leap_year & (t.dayofyear > 59), d - 1, d).astype(np.int16)


def doy_to_index(year, doy):
    """Day index (since ORIGIN) of day-of-year `doy` (0..364, no-leap) in `year` (arrays)."""
    year = np.asarray(year)
    doy = np.asarray(doy)
    jan1 = (year.astype("datetime64[Y]").astype("datetime64[D]") - C.ORIGIN).astype(np.int64) \
        if year.dtype.kind == "M" else \
        ((year - 1970).astype("datetime64[Y]").astype("datetime64[D]") - C.ORIGIN).astype(np.int64)
    leap = ((year % 4 == 0) & (year % 100 != 0)) | (year % 400 == 0)
    return jan1 + doy + (leap & (doy >= 59))


# =============================================================================
# REGIME (pure numpy, testable)
# =============================================================================

def smooth_cycle(clim, w=C.REGIME_SMOOTH_DAYS):
    """clim (365, n) -> circular moving average (365, n)."""
    h = w // 2
    ext = np.concatenate([clim[-h:], clim, clim[:h]], 0).astype(np.float64)
    cs = np.cumsum(np.vstack([np.zeros((1,) + ext.shape[1:]), ext]), 0)
    return ((cs[w:] - cs[:-w]) / w)[: clim.shape[0]]


def rain_regime(sc, min_rel=None, min_sep=None):
    """
    sc (365,) smoothed rainfall cycle -> (regime, ratio, t_dry, trough) from rainfall alone.
    trough = -1 when there are not two peaks.
    """
    min_rel = C.PEAK_MIN_REL if min_rel is None else min_rel
    min_sep = C.PEAK_MIN_SEP if min_sep is None else min_sep
    n = sc.shape[0]
    t_dry = int(np.argmin(sc))
    mx = float(sc.max())
    left, right = np.roll(sc, 1), np.roll(sc, -1)
    cand = np.nonzero((sc >= left) & (sc > right) & (sc >= min_rel * mx))[0]
    keep = []
    for i in sorted(cand, key=lambda k: -sc[k]):
        if all(min(abs(i - j), n - abs(i - j)) >= min_sep for j in keep):
            keep.append(int(i))
    if len(keep) < 2:
        return C.REGIME_UNI, 1.0, t_dry, -1
    a, b = sorted(keep[:2])
    arc_ab = np.arange(a, b + 1)                            # a -> b
    arc_ba = np.r_[np.arange(b, n), np.arange(0, a + 1)]    # b -> a (wraps)
    other = arc_ba if t_dry in set(arc_ab.tolist()) else arc_ab
    tm = int(other[np.argmin(sc[other])])
    ratio = float(sc[tm] / min(sc[a], sc[b]))
    if ratio <= C.BIMODAL_MAX_RATIO:
        reg = C.REGIME_BI
    elif ratio <= C.TRANSITION_MAX_RATIO:
        reg = C.REGIME_TRANSITION
    else:
        reg = C.REGIME_UNI
    return reg, ratio, t_dry, tm


def refine_regime(reg, ratio, tm, ndvi_n):
    """Final regime from the rainfall regime and the number of NDVI seasons (REGIME_SOURCE)."""
    if C.REGIME_SOURCE == "rain" or ndvi_n <= 0 or tm < 0:
        return reg
    if C.REGIME_SOURCE == "consensus":
        if ndvi_n == 2 and ratio <= C.TRANSITION_MAX_RATIO:
            return C.REGIME_BI
        return C.REGIME_TRANSITION if reg == C.REGIME_BI else reg
    if C.REGIME_SOURCE == "ndvi":
        if ndvi_n == 2 and ratio < 1.0:
            return C.REGIME_BI
        return C.REGIME_TRANSITION if reg == C.REGIME_BI else reg
    raise ValueError(f"REGIME_SOURCE {C.REGIME_SOURCE!r}")


def season_window(sc, reg, t_dry, tm):
    """(start doy, length, major): whole year for unimodal / transition, major sub-season for bimodal."""
    n = sc.shape[0]
    if reg != C.REGIME_BI:
        return t_dry, n, 0
    len1 = (tm - t_dry) % n                                 # t_dry -> trough
    len2 = n - len1                                         # trough -> next t_dry
    idx1 = (t_dry + np.arange(len1)) % n
    idx2 = (tm + np.arange(len2)) % n
    if C.MAJOR_SEASON_RULE == "first" or sc[idx1].sum() >= sc[idx2].sum():
        return t_dry, int(len1), 1
    return tm, int(len2), 2


def regime_one(sc, ndvi_n=0):
    """sc (365,) -> dict(regime, rain_regime, ratio, t_dry, trough, start, length, major)."""
    reg, ratio, t_dry, tm = rain_regime(sc)
    final = refine_regime(reg, ratio, tm, ndvi_n)
    start, length, major = season_window(sc, final, t_dry, tm)
    return dict(regime=final, rain_regime=reg, ratio=ratio, t_dry=t_dry, trough=tm, start=start,
                length=length, major=major)


def false_flags(X, miss, cols, first_day, T):
    """
    X (T, n) rain*100, miss (T, n); cols (m,), first_day (m,) -> bool (m,): the FALSE_WINDOW_DAYS days
    from first_day contain >= FALSE_DRY_DAYS dry days (FALSE_DRY_MODE "spell" = consecutive).
    """
    W = C.FALSE_WINDOW_DAYS
    idx = first_day[:, None] + np.arange(W)[None, :]
    inside = (idx >= 0) & (idx < T)
    ic = np.clip(idx, 0, T - 1)
    dry = (X[ic, cols[:, None]] < int(round(C.DRY_MM * SCALE))) & ~miss[ic, cols[:, None]] & inside
    if C.FALSE_DRY_MODE == "total":
        return dry.sum(1) >= C.FALSE_DRY_DAYS
    run = np.zeros(len(cols), np.int32)
    best = np.zeros(len(cols), np.int32)
    for k in range(W):
        run = np.where(dry[:, k], run + 1, 0)
        best = np.maximum(best, run)
    return best >= C.FALSE_DRY_DAYS


def seasons_for_window(X, miss, has, rm, s, L, T):
    """
    Onset/demise for one window per cell (vectorised).
    X (T, n) uint16 rain*100, miss (T, n) bool, has (T,) bool, rm (n,) mean daily rain (mm),
    s (n,) window start day index, L (n,) window length. Returns onset, demise (day index,
    -1 if none) and reason codes.
    """
    n = X.shape[1]
    K = int(L.max()) if n else 0
    k = np.arange(K)
    idx = s[:, None] + k[None, :]                           # (n, K)
    inwin = k[None, :] < L[:, None]
    outside = (idx < 0) | (idx >= T)
    idc = np.clip(idx, 0, T - 1)
    cols = np.arange(n)[:, None]
    raw = X[idc, cols].astype(np.float64) / SCALE
    m = miss[idc, cols] | outside
    a = np.where(m | ~inwin, 0.0, raw - rm[:, None])
    S = np.cumsum(a, 1)
    kmin = np.argmin(np.where(inwin, S, np.inf), 1)
    after = inwin & (k[None, :] > kmin[:, None])
    kmax = np.argmax(np.where(after, S, -np.inf), 1)
    has_after = after.any(1)
    reason = np.full(n, C.S_OK, np.uint8)
    cover = (has[idc] & ~outside & inwin).sum(1) / np.maximum(L, 1)
    reason[cover < C.WINDOW_MIN_COVER] = C.S_NO_DATA
    no_onset = (kmin == 0) | (kmin >= L - 1) | ~has_after | (np.take_along_axis(S, kmax[:, None], 1)[:, 0]
                                                <= np.take_along_axis(S, kmin[:, None], 1)[:, 0])
    reason[(reason == C.S_OK) & no_onset] = C.S_NO_ONSET
    onset = s + kmin + 1
    demise = s + kmax
    length = demise - onset + 1
    bad_len = (length < C.SEASON_LEN_MIN) | (length > C.SEASON_LEN_MAX)
    reason[(reason == C.S_OK) & bad_len] = C.S_BAD_LENGTH
    ok = reason == C.S_OK
    return np.where(ok, onset, -1), np.where(ok, demise, -1), reason


# =============================================================================
# WORKER
# =============================================================================

def extract_runs(dry, min_len):
    ncell, T = dry.shape
    pad = np.zeros((ncell, T + 2), dtype=np.int8)
    pad[:, 1:-1] = dry
    d = np.diff(pad, axis=1)
    sc, st = np.nonzero(d == 1)
    ec, et = np.nonzero(d == -1)
    length = et - st
    k = length >= min_len
    return sc[k], st[k], et[k] - 1, length[k]


def process_rows(r0, r1):
    import pyarrow as pa
    import pyarrow.parquet as pq

    g = _G
    mm = np.memmap(g["cache"], dtype=np.uint16, mode="r", shape=g["shape"])
    block = np.asarray(mm[:, r0:r1, :])
    del mm
    T, nr, nlon = block.shape
    n = nr * nlon
    X = block.reshape(T, n)
    del block
    has = g["has"]
    miss = (X == NODATA) | ~has[:, None]
    n_data_days = int(has.sum())
    n_missing = (miss & has[:, None]).sum(0)
    valid = n_missing < n_data_days
    valid_q = valid & (n_missing <= C.MAX_MISSING_FRAC * n_data_days)
    epoch = int((C.ORIGIN - np.datetime64("1970-01-01", "D")).astype(int))
    rows = (np.arange(n) // nlon + r0).astype(np.int16)
    cols = (np.arange(n) % nlon).astype(np.int16)
    lat, lon = g["lat"], g["lon"]

    # ---- 1. dry spells
    thr = int(round(C.DRY_MM * SCALE))
    dry = (X < thr) & ~miss
    dry[:, ~valid] = False
    cell, st, en, ln = extract_runs(np.ascontiguousarray(dry.T), C.STEP1_MIN_SPELL)
    del dry
    before = np.where(st > 0, miss[np.maximum(st - 1, 0), cell], True)
    after = np.where(en < T - 1, miss[np.minimum(en + 1, T - 1), cell], True)
    pq.write_table(pa.table({
        "row": rows[cell], "col": cols[cell],
        "lat": lat[rows[cell]].astype(np.float32), "lon": lon[cols[cell]].astype(np.float32),
        "start": st.astype(np.int32), "end": en.astype(np.int32),
        "start_date": pa.array((st + epoch).astype(np.int32), type=pa.date32()),
        "end_date": pa.array((en + epoch).astype(np.int32), type=pa.date32()),
        "length": ln.astype(np.int32), "censored": before | after,
    }), Path(g["spell_dir"]) / f"part_r{r0:05d}.parquet", compression="zstd")
    n_spells = len(st)
    del cell, st, en, ln, before, after

    # ---- 2. climatology and regime
    doy = g["doy"]
    clim_days = g["clim_days"]
    clim = np.full((365, n), np.nan, np.float32)
    for k in range(365):
        sel = clim_days & (doy == k)
        b = X[sel]
        m = ~miss[sel]
        s_ = np.where(m, b, 0).sum(0, dtype=np.float64) / SCALE
        c_ = m.sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            clim[k] = np.where(c_ > 0, s_ / c_, np.nan)
    mean_daily = np.nanmean(clim, 0)
    mean_annual = mean_daily * 365.0
    fill = np.where(np.isfinite(clim), clim, mean_daily[None, :])
    sc = smooth_cycle(np.nan_to_num(fill))
    usable = valid_q & np.isfinite(mean_annual) & (mean_annual >= C.ARID_MM)
    regime = np.full(n, C.REGIME_NONE, np.int8)
    rain_reg = np.full(n, C.REGIME_NONE, np.int8)
    ndvi_n = g["ndvi_n"][r0:r1].ravel() if g.get("ndvi_n") is not None else np.zeros(n, np.int8)
    ratio = np.full(n, np.nan, np.float32)
    t_dry = np.full(n, -1, np.int16)
    trough = np.full(n, -1, np.int16)
    w_start = np.full(n, -1, np.int16)
    w_len = np.zeros(n, np.int16)
    major = np.full(n, -1, np.int8)
    for c in np.nonzero(usable)[0]:
        r = regime_one(sc[:, c], int(ndvi_n[c]))
        regime[c], ratio[c], t_dry[c], trough[c] = r["regime"], r["ratio"], r["t_dry"], r["trough"]
        rain_reg[c] = r["rain_regime"]
        w_start[c], w_len[c], major[c] = r["start"], r["length"], r["major"]

    # ---- 3. seasons per year (major season window). Windows start one year early so that a
    # window beginning in late December still yields the first season; only seasons whose
    # onset falls in SEASON_YEAR_MIN..MAX are kept (same period for every regime).
    years = np.arange(C.SEASON_YEAR_MIN - 1, C.SEASON_YEAR_MAX + 1)
    Y = len(years)
    on = np.full((n, Y), -1, np.int64)
    de = np.full((n, Y), -1, np.int64)
    rs = np.full((n, Y), C.S_CELL_INVALID, np.uint8)
    cu = np.nonzero(usable)[0]
    # reference of the cumulative anomaly: climatological mean daily rain over each cell's window
    ref = np.full(n, np.nan)
    for c in cu:
        ref[c] = fill[(w_start[c] + np.arange(w_len[c])) % 365, c].mean()
    if len(cu):
        Xu, mu = X[:, cu], miss[:, cu]
        for yi, y in enumerate(years):
            s = doy_to_index(np.full(len(cu), y), w_start[cu].astype(np.int64))
            o, d, r = seasons_for_window(Xu, mu, has, ref[cu], s, w_len[cu].astype(np.int64), T)
            on[cu, yi], de[cu, yi], rs[cu, yi] = o, d, r
        del Xu, mu
    # season year = calendar year of onset; a second onset in the same year is a duplicate
    o_year = np.where(on >= 0, (C.index_to_date(np.maximum(on, 0)).astype("datetime64[Y]").astype(int) + 1970), -1)
    year_col = np.where(on >= 0, o_year, years[None, :])
    dup = np.zeros_like(rs, dtype=bool)
    dup[:, 1:] = (o_year[:, 1:] == o_year[:, :-1]) & (o_year[:, 1:] > 0)
    rs[dup & (rs == C.S_OK)] = C.S_DUPLICATE
    outp = (on >= 0) & ((o_year < C.SEASON_YEAR_MIN) | (o_year > C.SEASON_YEAR_MAX))
    rs[outp & (rs == C.S_OK)] = C.S_OUT_OF_PERIOD
    ok = rs == C.S_OK

    # ---- false start / false demise (flagged always, excluded on request); rainfall demise
    fs = np.zeros_like(ok)
    fd = np.zeros_like(ok)
    ci, yi_ = np.nonzero(ok)
    if len(ci):
        W = C.FALSE_WINDOW_DAYS
        fs[ci, yi_] = false_flags(X, miss, ci, on[ci, yi_], T)
        fd[ci, yi_] = false_flags(X, miss, ci, de[ci, yi_] - W + 1, T)
    if C.FALSE_START_EXCLUDE:
        rs[fs & ok] = C.S_FALSE_START
    if C.FALSE_DEMISE_EXCLUDE:
        rs[fd & ok & (rs == C.S_OK)] = C.S_FALSE_DEMISE
    ok = rs == C.S_OK

    # ---- demise adjusted with the NDVI end of season
    de_rain = de.copy()
    eos_m = np.full(de.shape, -1, np.int64)
    shift = np.zeros(de.shape, np.int64)
    if g.get("eos") is not None and C.DEMISE_ADJUST != "none":
        E = g["eos"][:, :, r0:r1, :].reshape(-1, n).astype(np.int64)          # (years*2, n)
        lo, hi = C.DEMISE_MATCH_WINDOW
        for yi in range(Y):
            cells = np.nonzero(ok[:, yi])[0]
            if not len(cells):
                continue
            d = E[:, cells] - de[cells, yi][None, :]
            d = np.where((E[:, cells] >= 0) & (d >= lo) & (d <= hi), d, 10 ** 6)
            k = np.argmin(np.abs(d), 0)
            best = d[k, np.arange(len(cells))]
            has_m = best < 10 ** 6
            eos_m[cells[has_m], yi] = de[cells[has_m], yi] + best[has_m]
        off = np.where(eos_m >= 0, eos_m - de, np.nan)
        med = np.nanmedian(np.where(ok, off, np.nan), 1)
        med_shift = np.clip(np.nan_to_num(med, nan=0.0), 0, C.DEMISE_SHIFT_MAX)
        if C.DEMISE_ADJUST == "median_offset":
            shift = np.where(ok, np.round(med_shift)[:, None], 0).astype(np.int64)
        elif C.DEMISE_ADJUST == "per_year":
            yr = np.clip(np.nan_to_num(off, nan=np.nan), 0, C.DEMISE_SHIFT_MAX)
            shift = np.where(ok, np.round(np.where(np.isfinite(yr), yr, med_shift[:, None])), 0).astype(np.int64)
        else:
            raise ValueError(f"DEMISE_ADJUST {C.DEMISE_ADJUST!r}")
        de = np.where(ok, de + shift, de)
    slen = np.where(ok, de - on + 1, -1)

    # table rows: every valid season + the failed windows that fall inside the period
    keep = (ok | ((year_col >= C.SEASON_YEAR_MIN) & (year_col <= C.SEASON_YEAR_MAX) & (rs != C.S_OUT_OF_PERIOD))).ravel()
    cc, yy = np.divmod(np.arange(n * Y)[keep], Y)
    on_f, de_f = on.ravel()[keep], de.ravel()[keep]
    dr_f, eo_f = de_rain.ravel()[keep], eos_m.ravel()[keep]

    def date_col(v):
        return pa.array(np.where(v < 0, 0, v + epoch).astype(np.int32), type=pa.date32(), mask=v < 0)

    pq.write_table(pa.table({
        "row": rows[cc], "col": cols[cc],
        "lat": lat[rows[cc]].astype(np.float32), "lon": lon[cols[cc]].astype(np.float32),
        "year": year_col.ravel()[keep].astype(np.int16),
        "onset_date": pa.array(np.where(on_f < 0, 0, on_f + epoch).astype(np.int32), type=pa.date32(),
                               mask=on_f < 0),
        "demise_date": pa.array(np.where(de_f < 0, 0, de_f + epoch).astype(np.int32), type=pa.date32(),
                                mask=de_f < 0),
        "demise_rain_date": date_col(dr_f), "ndvi_eos_date": date_col(eo_f),
        "demise_shift": shift.ravel()[keep].astype(np.int16),
        "false_start": fs.ravel()[keep], "false_demise": fd.ravel()[keep],
        "valid": ok.ravel()[keep], "reason": rs.ravel()[keep], "season_len": slen.ravel()[keep].astype(np.int16),
        "regime": regime[cc], "rain_regime": rain_reg[cc], "ndvi_n_seasons": ndvi_n[cc].astype(np.int8),
        "window_start_doy": w_start[cc], "window_len": w_len[cc],
    }), Path(g["season_dir"]) / f"part_r{r0:05d}.parquet", compression="zstd")

    # ---- per-cell season statistics (day of year relative to the window start, then back)
    nv = ok.sum(1)
    rel_on = np.where(ok, (on - doy_to_index(year_col.clip(1900), 0) - w_start[:, None]) % 365, np.nan)
    rel_de = np.where(ok, (de - doy_to_index(year_col.clip(1900), 0) - w_start[:, None]) % 365, np.nan)
    on_med = (np.nanmedian(rel_on, 1) + w_start) % 365
    de_med = (np.nanmedian(rel_de, 1) + w_start) % 365
    on_iqr = np.nanpercentile(rel_on, 75, 1) - np.nanpercentile(rel_on, 25, 1)
    len_med = np.nanmedian(np.where(ok, slen, np.nan), 1)
    base_ok = (rs == C.S_OK) | (rs == C.S_FALSE_START) | (rs == C.S_FALSE_DEMISE)
    n_base = np.maximum(base_ok.sum(1), 1)
    fs_share = (fs & base_ok).sum(1) / n_base
    fd_share = (fd & base_ok).sum(1) / n_base
    shift_med = np.nanmedian(np.where(ok, shift, np.nan), 1)
    eos_ok = ok & (eos_m >= 0)                          # NDVI end of season matched (before clipping)
    eos_off = np.nanmedian(np.where(eos_ok, eos_m - de_rain, np.nan), 1)
    eos_share = eos_ok.sum(1) / np.maximum(ok.sum(1), 1)
    res = dict(valid=valid, valid_q=valid_q, n_missing=n_missing, mean_annual=mean_annual,
               regime=regime, ratio=ratio, t_dry=t_dry, trough=trough, w_start=w_start, w_len=w_len,
               major=major, ref_mm_day=ref, n_valid_seasons=nv, onset_doy_median=on_med, demise_doy_median=de_med,
               onset_iqr_days=on_iqr, season_len_median=len_med, rain_regime=rain_reg, ndvi_n=ndvi_n,
               false_start_share=fs_share, false_demise_share=fd_share, demise_shift_median=shift_med,
               eos_offset_median=eos_off, eos_match_share=eos_share)
    res = {k: np.asarray(v).reshape(nr, nlon) for k, v in res.items()}
    gc.collect()
    return r0, r1, res, n_spells, int(ok.sum())


# =============================================================================
# MAIN
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ci_nga")
    ap.add_argument("--bbox", nargs=4, type=float)
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 4))
    ap.add_argument("--rows_per_task", type=int, default=C.ROWS_PER_TASK)
    a = ap.parse_args()
    name, bbox = C.parse_region(a.region, a.bbox)
    cdir = C.data_dir("chirps", name)
    out = C.region_dir(name) / "step03"
    C.setup_logging(out / "step03.log")
    t0 = time.time()
    if not (cdir / "meta.json").exists():
        sys.exit(f"{cdir / 'meta.json'} not found - run v9_01_download.py --region {name} first")
    cm = C.read_json(cdir / "meta.json")
    lon, lat = np.array(cm["lon"]), np.array(cm["lat"])
    has = np.load(cdir / "day_done.npy")
    shape = (cm["n_days"], len(lat), len(lon))
    dates = C.ORIGIN + np.arange(shape[0]).astype("timedelta64[D]")
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    logger.info("=" * 70)
    logger.info(f"v9 STEP3  region={name} grid {len(lon)}x{len(lat)}  days with data {has.sum():,}/{len(has):,}")
    logger.info(f"  bimodal cells: {C.MAJOR_SEASON_RULE} season analysed")
    logger.info(f"  regime: {C.REGIME_SMOOTH_DAYS}-d smoothed cycle {C.CLIM_YEAR_MIN}-{C.CLIM_YEAR_MAX}, bimodal if "
                f"trough/peak <= {C.BIMODAL_MAX_RATIO}, transition <= {C.TRANSITION_MAX_RATIO}; arid < {C.ARID_MM} mm")
    logger.info("=" * 70)
    if has.sum() < 0.9 * len(has):
        logger.warning(f"only {has.sum():,} of {len(has):,} days downloaded - run v9_01_download.py again")

    for sub in ("spells", "seasons"):
        (out / sub).mkdir(parents=True, exist_ok=True)
        for f in (out / sub).glob("part_*.parquet"):
            f.unlink()
    # NDVI phenology (step 2) on this grid
    ph = C.region_dir(name) / "step02" / "ndvi_phenology.nc"
    ndvi_n = eos = None
    if C.USE_NDVI:
        if not ph.exists():
            sys.exit(f"{ph} not found - run v9_02_ndvi_phenology.py (or set USE_NDVI = False)")
        with xr.open_dataset(ph) as d:
            if d.sizes["lat"] != len(lat) or d.sizes["lon"] != len(lon):
                sys.exit(f"{ph} is on another grid - rerun v9_02_ndvi_phenology.py")
            ndvi_n = d.ndvi_n_seasons.values.astype(np.int8)
            eos = d.eos.values.astype(np.int32)
        logger.info(f"  NDVI: {(ndvi_n == 2).sum():,} cells with two seasons, {(ndvi_n == 1).sum():,} with one, "
                    f"{(ndvi_n == 0).sum():,} without signal; regime source {C.REGIME_SOURCE}, "
                    f"demise adjustment {C.DEMISE_ADJUST} (max {C.DEMISE_SHIFT_MAX} d)")
    logger.info(f"  false start / demise: >= {C.FALSE_DRY_DAYS} dry days ({C.FALSE_DRY_MODE}) in the first / last "
                f"{C.FALSE_WINDOW_DAYS} d; excluded: start {C.FALSE_START_EXCLUDE}, demise {C.FALSE_DEMISE_EXCLUDE}")
    _G.update(ndvi_n=ndvi_n, eos=eos)
    _G.update(cache=str(cdir / "rain_u16.dat"), shape=shape, has=has, lat=lat, lon=lon,
              doy=noleap_doy(dates), clim_days=has & (years >= C.CLIM_YEAR_MIN) & (years <= C.CLIM_YEAR_MAX),
              spell_dir=str(out / "spells"), season_dir=str(out / "seasons"))
    nlat, nlon = len(lat), len(lon)
    chunks = [(r, min(r + a.rows_per_task, nlat)) for r in range(0, nlat, a.rows_per_task)]
    grids = {}
    n_sp = n_se = 0
    with ProcessPoolExecutor(max_workers=max(1, min(a.workers, len(chunks))),
                             mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(process_rows, r0, r1) for r0, r1 in chunks]
        for i, f in enumerate(as_completed(futs), 1):
            r0, r1, res, ns, nse = f.result()
            for k, v in res.items():
                grids.setdefault(k, np.full((nlat, nlon), np.nan, np.float32))[r0:r1] = v
            n_sp += ns
            n_se += nse
            if i % 20 == 0 or i == len(chunks):
                logger.info(f"  {i}/{len(chunks)} chunks, {n_sp:,} spells, {n_se:,} valid seasons")

    valid, valid_q = grids["valid"].astype(bool), grids["valid_q"].astype(bool)
    regime = grids["regime"].astype(np.int8)
    reason = np.full((nlat, nlon), C.REASON_OK, np.uint8)
    reason[valid & ~valid_q] = C.REASON_MISSING
    reason[~valid] = C.REASON_NO_CHIRPS
    reason[valid_q & (regime == C.REGIME_NONE)] = C.REASON_ARID
    reason[(reason == C.REASON_OK) & (grids["n_valid_seasons"] < C.MIN_VALID_SEASONS)] = C.REASON_FEW_SEASONS
    f32 = lambda k: (("lat", "lon"), grids[k].astype(np.float32))
    ds = xr.Dataset({
        "valid": (("lat", "lon"), valid_q.astype(np.int8)), "reason": (("lat", "lon"), reason),
        "n_missing": (("lat", "lon"), grids["n_missing"].astype(np.int32)),
        "mean_annual_mm": f32("mean_annual"), "regime": (("lat", "lon"), regime),
        "trough_ratio": f32("ratio"), "t_dry_doy": f32("t_dry"), "trough_doy": f32("trough"),
        "window_start_doy": f32("w_start"), "window_len": f32("w_len"), "major_season": f32("major"),
        "reference_mm_day": f32("ref_mm_day"),
        "n_valid_seasons": f32("n_valid_seasons"), "onset_doy_median": f32("onset_doy_median"),
        "demise_doy_median": f32("demise_doy_median"), "onset_iqr_days": f32("onset_iqr_days"),
        "season_len_median": f32("season_len_median"),
        "rain_regime": (("lat", "lon"), grids["rain_regime"].astype(np.int8)),
        "ndvi_n_seasons": (("lat", "lon"), np.nan_to_num(grids["ndvi_n"]).astype(np.int8)),
        "false_start_share": f32("false_start_share"), "false_demise_share": f32("false_demise_share"),
        "demise_shift_median": f32("demise_shift_median"),
        "ndvi_eos_offset_median": f32("eos_offset_median"), "ndvi_eos_match_share": f32("eos_match_share"),
    }, coords={"lat": lat, "lon": lon},
        attrs={"region": name, "bbox": list(bbox), "regime_codes": str(C.REGIME_LABELS),
               "reason_codes": str(C.REASON_LABELS),
               "major_season": "0 one season (unimodal or transition), 1 bimodal: season after the driest point, "
                               "2 bimodal: season after the mid-season trough",
               "doy": "0-based day of year, 29 Feb folded into 28 Feb"})
    ds.to_netcdf(out / "grid_meta.nc")
    np.save(out / "day_has_data.npy", has)
    last = C.index_to_date(np.nonzero(has)[0].max())
    C.write_json(C.region_dir(name) / "settings_used.json", C.settings_json())
    C.write_json(out / "meta.json", {"region": name, "bbox": list(bbox), "n_lon": nlon, "n_lat": nlat,
                                     "origin": str(C.ORIGIN), "n_days": shape[0], "last_day_with_data": str(last),
                                     "chunks": chunks, "n_spells": n_sp, "n_valid_seasons": n_se})

    # diagnostics
    dg = out / "diagnostics"
    bnd = C.load_boundaries(bbox)
    ok = reason == C.REASON_OK
    cat = np.where(regime > 0, regime, np.nan).astype(float)
    C.plot_map(dg / "regime.png", cat, lon, lat, "Rainfall regime (smoothed mean annual cycle 1981-2024)",
               boundaries=bnd, categorical=[(1, C.BRAND["olive"], "unimodal"), (2, C.BRAND["light_blue"], "transition (major season used)"),
                                            (3, C.BRAND["teal"], "bimodal (major season used)")])
    C.save_geotiff(dg / "regime.tif", regime.astype(np.uint8), lon, lat, nodata=0, dtype="uint8")
    for var, title, cmap, lab, vmin, vmax in [
            ("mean_annual_mm", "Mean annual rainfall (CHIRPS 1981-2024)", "brand_teal", "mm/yr", 0, None),
            ("trough_ratio", "Mid-season trough / smaller peak (<= 0.80 bimodal, <= 0.95 transition)", "brand_div", "ratio", 0.3, 1.0),
            ("onset_doy_median", "Median onset of the (major) season", "brand_teal", "day of year (0 = 1 Jan)", None, None),
            ("demise_doy_median", "Median demise of the (major) season", "brand_teal", "day of year (0 = 1 Jan)", None, None),
            ("season_len_median", "Median length of the (major) season", "brand_green", "days", None, None),
            ("onset_iqr_days", "Year-to-year spread of onset (IQR)", "brand_risk", "days", 0, None),
            ("n_valid_seasons", "Number of valid seasons 1981-2024", "brand_green", "seasons", 0, None),
            ("demise_shift_median", "Demise moved later by the NDVI end of season (median)", "brand_teal", "days", 0, None),
            ("ndvi_eos_offset_median", "NDVI end of season - rainfall demise (median, before clipping)", "brand_div",
             "days", C.DEMISE_MATCH_WINDOW[0], C.DEMISE_MATCH_WINDOW[1]),
            ("false_start_share", "Share of seasons with a false start", "brand_risk", "share", 0, None),
            ("false_demise_share", "Share of seasons with a false demise", "brand_risk", "share", 0, None)]:
        arr = np.where(ok | (var in ("mean_annual_mm", "trough_ratio")), ds[var].values, np.nan)
        C.save_geotiff(dg / f"{var}.tif", arr.astype(np.float32), lon, lat)
        C.plot_map(dg / f"{var}.png", arr, lon, lat, title, lab, cmap=cmap, vmin=vmin, vmax=vmax,
                   boundaries=bnd, reason=reason)
    rr = grids["rain_regime"].astype(np.int8)
    for c, lab in C.REGIME_LABELS.items():
        logger.info(f"  regime {lab:<28} {(regime == c).sum():>10,} cells (rainfall alone: {(rr == c).sum():,})")
    for c, lab in C.REASON_LABELS.items():
        logger.info(f"  cells {lab:<29} {(reason == c).sum():>10,}")
    eo = np.where(reason == C.REASON_OK, grids["eos_offset_median"], np.nan)
    if np.isfinite(eo).any():
        q = np.nanpercentile(eo, [10, 50, 90])
        logger.info(f"  NDVI end of season - rainfall demise, cell medians: p10 {q[0]:.0f}, median {q[1]:.0f}, "
                    f"p90 {q[2]:.0f} d; cells clipped to DEMISE_SHIFT_MAX={C.DEMISE_SHIFT_MAX}: "
                    f"{np.nanmean(eo > C.DEMISE_SHIFT_MAX):.1%}, to 0: {np.nanmean(eo < 0):.1%}; "
                    f"seasons matched {np.nanmean(np.where(reason == C.REASON_OK, grids['eos_match_share'], np.nan)):.0%}")
    logger.info(f"STEP3 done in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()
