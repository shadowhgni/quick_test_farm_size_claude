#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v8 STEP 2 - dry spells, rainfall regime and MAJOR-season onset/demise from CHIRPS
================================================================================

Reads the CHIRPS cache of v8_01_download.py, one block of grid rows per worker, and for
every cell:

1. Dry spells: every run of >= 5 days with rain < 1 mm on the continuous 1981-2025 series
   (a missing day breaks a spell; spells touching a missing day are flagged 'censored').
2. Rainfall regime, from the daily mean annual cycle (1981-2024) smoothed by a 31-day
   circular moving average:
     driest day t_dry = minimum of the smoothed cycle;
     peaks = local maxima >= 25 % of the annual maximum, >= 45 days apart;
     with two peaks, the mid-season trough is the minimum between them on the side that does
     NOT contain t_dry; ratio = trough / smaller peak.
       ratio <= 0.80 -> bimodal, 0.80-0.95 -> transition, otherwise (or one peak) unimodal.
     Cells with mean annual rain < 150 mm are arid (no season).
3. Season window (fixed day-of-year range, the same every year):
     unimodal, transition:  t_dry -> t_dry + 365 d. In a transition cell the mid-season dip keeps
                            >= 80 % of the smaller peak's rain: it does not separate two seasons,
                            so the major season is the whole season and the dip stays inside it
                            (a dry spell during the dip is a risk the analysis must count).
     bimodal:               two sub-seasons, t_dry -> trough and trough -> next t_dry;
                            the MAJOR season = the one with the larger climatological rainfall
                            (MAJOR_SEASON_RULE = "first" in v8_common.py: always the first one).
4. Onset and demise for every year inside that window, RADS method (Liebmann & Marengo
   2001; Bombardi et al. 2019): S(t) = cumulative sum of (rain - reference), the reference
   being the climatological mean daily rain OVER THE WINDOW (= the annual mean for a 365-day
   window, i.e. exactly RADS; the sub-season mean for a bimodal major season).
     onset  = day after the minimum of S;   demise = day of the maximum of S after the onset.
   An onset on the first day of the window (no dry-to-wet change inside it) is rejected.
   Missing days add 0. A season is valid when both exist, 30 <= length <= 330 days and the
   window has rainfall data on >= 95 % of its days. The season year = calendar year of onset.

Outputs (dryspell_v8/<region>/step02/)
  spells/part_rXXXXX.parquet   row, col, lat, lon, start, end, start_date, end_date, length, censored
  seasons/part_rXXXXX.parquet  row, col, lat, lon, year, onset_date, demise_date, valid, reason,
                               season_len, regime, window_start_doy, window_len
  grid_meta.nc                 valid, reason, mean_annual_mm, regime, trough_ratio, major season,
                               window, n_valid_seasons, onset/demise medians, onset spread
  day_has_data.npy, meta.json, diagnostics/*.png|tif

Usage
-----
  python v8_02_spells_seasons.py --region ci_nga --workers 8
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
import v8_common as C

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger("dryspell_v8")
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


def regime_one(sc, min_rel=C.PEAK_MIN_REL, min_sep=C.PEAK_MIN_SEP):
    """
    sc (365,) smoothed cycle -> dict(regime, ratio, t_dry, trough, start, length, major)
    start/length: the season window in day-of-year (start 0..364, length in days)
    major: 0 unimodal, 1 = sub-season starting at t_dry, 2 = sub-season starting at the trough
    """
    n = sc.shape[0]
    t_dry = int(np.argmin(sc))
    mx = float(sc.max())
    out = dict(regime=C.REGIME_UNI, ratio=1.0, t_dry=t_dry, trough=-1, start=t_dry, length=n, major=0)
    left, right = np.roll(sc, 1), np.roll(sc, -1)
    cand = np.nonzero((sc >= left) & (sc > right) & (sc >= min_rel * mx))[0]
    keep = []
    for i in sorted(cand, key=lambda k: -sc[k]):
        if all(min(abs(i - j), n - abs(i - j)) >= min_sep for j in keep):
            keep.append(int(i))
    if len(keep) < 2:
        return out
    a, b = sorted(keep[:2])
    arc_ab = np.arange(a, b + 1)                            # a -> b
    arc_ba = np.r_[np.arange(b, n), np.arange(0, a + 1)]    # b -> a (wraps)
    other = arc_ba if t_dry in set(arc_ab.tolist()) else arc_ab
    tm = int(other[np.argmin(sc[other])])
    ratio = float(sc[tm] / min(sc[a], sc[b]))
    out["ratio"] = ratio
    if ratio > C.TRANSITION_MAX_RATIO:
        return out
    out["regime"] = C.REGIME_BI if ratio <= C.BIMODAL_MAX_RATIO else C.REGIME_TRANSITION
    out["trough"] = tm
    if out["regime"] == C.REGIME_TRANSITION:
        return out                                          # one season: full-year window
    len1 = (tm - t_dry) % n                                 # t_dry -> trough
    len2 = n - len1                                         # trough -> next t_dry
    idx1 = (t_dry + np.arange(len1)) % n
    idx2 = (tm + np.arange(len2)) % n
    if C.MAJOR_SEASON_RULE == "first" or sc[idx1].sum() >= sc[idx2].sum():
        out.update(start=t_dry, length=int(len1), major=1)
    else:
        out.update(start=tm, length=int(len2), major=2)
    return out


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
    reason[cover < 0.95] = C.S_NO_DATA
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
    ratio = np.full(n, np.nan, np.float32)
    t_dry = np.full(n, -1, np.int16)
    trough = np.full(n, -1, np.int16)
    w_start = np.full(n, -1, np.int16)
    w_len = np.zeros(n, np.int16)
    major = np.full(n, -1, np.int8)
    for c in np.nonzero(usable)[0]:
        r = regime_one(sc[:, c])
        regime[c], ratio[c], t_dry[c], trough[c] = r["regime"], r["ratio"], r["t_dry"], r["trough"]
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
    slen = np.where(ok, de - on + 1, -1)

    # table rows: every valid season + the failed windows that fall inside the period
    keep = (ok | ((year_col >= C.SEASON_YEAR_MIN) & (year_col <= C.SEASON_YEAR_MAX) & (rs != C.S_OUT_OF_PERIOD))).ravel()
    cc, yy = np.divmod(np.arange(n * Y)[keep], Y)
    on_f, de_f = on.ravel()[keep], de.ravel()[keep]
    pq.write_table(pa.table({
        "row": rows[cc], "col": cols[cc],
        "lat": lat[rows[cc]].astype(np.float32), "lon": lon[cols[cc]].astype(np.float32),
        "year": year_col.ravel()[keep].astype(np.int16),
        "onset_date": pa.array(np.where(on_f < 0, 0, on_f + epoch).astype(np.int32), type=pa.date32(),
                               mask=on_f < 0),
        "demise_date": pa.array(np.where(de_f < 0, 0, de_f + epoch).astype(np.int32), type=pa.date32(),
                                mask=de_f < 0),
        "valid": ok.ravel()[keep], "reason": rs.ravel()[keep], "season_len": slen.ravel()[keep].astype(np.int16),
        "regime": regime[cc], "window_start_doy": w_start[cc], "window_len": w_len[cc],
    }), Path(g["season_dir"]) / f"part_r{r0:05d}.parquet", compression="zstd")

    # ---- per-cell season statistics (day of year relative to the window start, then back)
    nv = ok.sum(1)
    rel_on = np.where(ok, (on - doy_to_index(year_col.clip(1900), 0) - w_start[:, None]) % 365, np.nan)
    rel_de = np.where(ok, (de - doy_to_index(year_col.clip(1900), 0) - w_start[:, None]) % 365, np.nan)
    on_med = (np.nanmedian(rel_on, 1) + w_start) % 365
    de_med = (np.nanmedian(rel_de, 1) + w_start) % 365
    on_iqr = np.nanpercentile(rel_on, 75, 1) - np.nanpercentile(rel_on, 25, 1)
    len_med = np.nanmedian(np.where(ok, slen, np.nan), 1)
    res = dict(valid=valid, valid_q=valid_q, n_missing=n_missing, mean_annual=mean_annual,
               regime=regime, ratio=ratio, t_dry=t_dry, trough=trough, w_start=w_start, w_len=w_len,
               major=major, ref_mm_day=ref, n_valid_seasons=nv, onset_doy_median=on_med, demise_doy_median=de_med,
               onset_iqr_days=on_iqr, season_len_median=len_med)
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
    out = C.region_dir(name) / "step02"
    C.setup_logging(out / "step02.log")
    t0 = time.time()
    if not (cdir / "meta.json").exists():
        sys.exit(f"{cdir / 'meta.json'} not found - run v8_01_download.py --region {name} first")
    cm = C.read_json(cdir / "meta.json")
    lon, lat = np.array(cm["lon"]), np.array(cm["lat"])
    has = np.load(cdir / "day_done.npy")
    shape = (cm["n_days"], len(lat), len(lon))
    dates = C.ORIGIN + np.arange(shape[0]).astype("timedelta64[D]")
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    logger.info("=" * 70)
    logger.info(f"v8 STEP2  region={name} grid {len(lon)}x{len(lat)}  days with data {has.sum():,}/{len(has):,}")
    logger.info(f"  bimodal cells: {C.MAJOR_SEASON_RULE} season analysed")
    logger.info(f"  regime: {C.REGIME_SMOOTH_DAYS}-d smoothed cycle {C.CLIM_YEAR_MIN}-{C.CLIM_YEAR_MAX}, bimodal if "
                f"trough/peak <= {C.BIMODAL_MAX_RATIO}, transition <= {C.TRANSITION_MAX_RATIO}; arid < {C.ARID_MM} mm")
    logger.info("=" * 70)
    if has.sum() < 0.9 * len(has):
        logger.warning(f"only {has.sum():,} of {len(has):,} days downloaded - run v8_01_download.py again")

    for sub in ("spells", "seasons"):
        (out / sub).mkdir(parents=True, exist_ok=True)
        for f in (out / sub).glob("part_*.parquet"):
            f.unlink()
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
    reason[(reason == C.REASON_OK) & (grids["n_valid_seasons"] < 5)] = C.REASON_FEW_SEASONS
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
    }, coords={"lat": lat, "lon": lon},
        attrs={"region": name, "bbox": list(bbox), "regime_codes": str(C.REGIME_LABELS),
               "reason_codes": str(C.REASON_LABELS),
               "major_season": "0 one season (unimodal or transition), 1 bimodal: season after the driest point, "
                               "2 bimodal: season after the mid-season trough",
               "doy": "0-based day of year, 29 Feb folded into 28 Feb"})
    ds.to_netcdf(out / "grid_meta.nc")
    np.save(out / "day_has_data.npy", has)
    last = C.index_to_date(np.nonzero(has)[0].max())
    C.write_json(out / "meta.json", {"region": name, "bbox": list(bbox), "n_lon": nlon, "n_lat": nlat,
                                     "origin": str(C.ORIGIN), "n_days": shape[0], "last_day_with_data": str(last),
                                     "chunks": chunks, "n_spells": n_sp, "n_valid_seasons": n_se})

    # diagnostics
    dg = out / "diagnostics"
    bnd = C.load_boundaries(bbox)
    ok = reason == C.REASON_OK
    cat = np.where(regime > 0, regime, np.nan).astype(float)
    C.plot_map(dg / "regime.png", cat, lon, lat, "Rainfall regime (smoothed mean annual cycle 1981-2024)",
               boundaries=bnd, categorical=[(1, "#e3d5b8", "unimodal"), (2, "#7fb3d5", "transition (major season used)"),
                                            (3, "#1f5f8b", "bimodal (major season used)")])
    C.save_geotiff(dg / "regime.tif", regime.astype(np.uint8), lon, lat, nodata=0, dtype="uint8")
    for var, title, cmap, lab, vmin, vmax in [
            ("mean_annual_mm", "Mean annual rainfall (CHIRPS 1981-2024)", "Blues", "mm/yr", 0, None),
            ("trough_ratio", "Mid-season trough / smaller peak (<= 0.80 bimodal, <= 0.95 transition)", "RdBu", "ratio", 0.3, 1.0),
            ("onset_doy_median", "Median onset of the (major) season", "viridis", "day of year (0 = 1 Jan)", None, None),
            ("demise_doy_median", "Median demise of the (major) season", "viridis", "day of year (0 = 1 Jan)", None, None),
            ("season_len_median", "Median length of the (major) season", "Greens", "days", None, None),
            ("onset_iqr_days", "Year-to-year spread of onset (IQR)", "Oranges", "days", 0, None),
            ("n_valid_seasons", "Number of valid seasons 1981-2024", "Greens", "seasons", 0, None)]:
        arr = np.where(ok | (var in ("mean_annual_mm", "trough_ratio")), ds[var].values, np.nan)
        C.save_geotiff(dg / f"{var}.tif", arr.astype(np.float32), lon, lat)
        C.plot_map(dg / f"{var}.png", arr, lon, lat, title, lab, cmap=cmap, vmin=vmin, vmax=vmax,
                   boundaries=bnd, reason=reason)
    for c, lab in C.REGIME_LABELS.items():
        logger.info(f"  regime {lab:<28} {(regime == c).sum():>10,} cells")
    for c, lab in C.REASON_LABELS.items():
        logger.info(f"  cells {lab:<29} {(reason == c).sum():>10,}")
    logger.info(f"STEP2 done in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()
