#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v7 STEP 2 - RADS seasons x dry spells -> per-season table + per-cell maps
=========================================================================

Fixes relative to v4-v6
-----------------------
* Every (cell, season) is a row, including seasons with ZERO dry spells, so cells
  with no qualifying spell get 0 (not a blank) and medians/probabilities use the
  right denominator (only valid seasons, never 1981-2025 blindly).
* RADS onset/demise are used as full dates (year kept; seasons may cross 31 Dec)
  and RADS arrays are transposed by dimension NAME to (lat, lon).
* RADS values are sanity-checked (missing, order, length, year, overlap,
  rainfall coverage); each rejected season gets a reason code.
* Spells are clipped to the season window [onset+10, demise-10] (EDGE_POLICY),
  and kept if >= MIN_SPELL days after clipping. No pre-filter on raw length.
* Probabilities are unconditional: a season without a spell counts as "no".
* Relative measures use each season's own length.
* Fixed regular grid -> correct GeoTIFF georeferencing; blank pixels carry a reason.

Outputs (dryspell_v7/<region>/step2/)
-------
  seasons/part_rXXXXX.parquet  one row per cell x RADS year (valid + rejected, with reason)
  metrics.nc                   all per-cell layers (+ p_first_le[x], drought_prob[offset])
  cog/*.tif, png/*.png         main layers
  reason_summary.csv, rads_summary.csv

Offsets are days after RADS onset (onset = day 0). With the 10-day exclusion the
earliest possible spell start is day 10.

Usage
-----
  python 2026-09-26.step2_dry_spell_seasons_v07.py --region study --workers 80
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

SENT = np.iinfo(np.int32).min
RADS_PLACEHOLDER_DAYS = 366     # dates more than a year before 1981-01-01 (e.g. 1970-01-01) = missing
_G = {}


# =============================================================================
# RADS
# =============================================================================

def _find_var(ds, keys):
    """First variable whose name contains one of keys; datetime variables are preferred
    (RADS ships onset/demise both as dates and as day-of-year, e.g. onset_jday)."""
    hits = [v for v in ds.data_vars if any(k in v.lower() for k in keys)]
    if not hits:
        raise KeyError(f"no variable matching {keys} in {list(ds.data_vars)}")
    dates = [v for v in hits if np.issubdtype(ds[v].dtype, np.datetime64)]
    return (dates or hits)[0]


def _rads_year(args):
    """Worker: one RADS file -> onset/demise day indices on the region grid."""
    year, path, lon, lat = args
    step = C.regular_step(lon)
    with xr.open_dataset(path) as ds:
        out, info = {}, {"year": year}
        for key, names in (("onset", ("onset",)), ("demise", ("demise", "cessation", "offset", "end"))):
            v = _find_var(ds, names)
            da = ds[v]
            latn, lonn = C.spatial_names(da)
            for d in list(da.dims):
                if d in (latn, lonn):
                    continue
                if da.sizes[d] > 1:
                    info[f"{key}_extra_dim"] = f"{d}={da.sizes[d]} (first taken)"
                da = da.isel({d: 0})
            info[f"{key}_dims"] = str(tuple(da.dims))
            da = da.transpose(latn, lonn)                 # by NAME, never assumed
            vals = da.values
            if not np.issubdtype(vals.dtype, np.datetime64):
                raise TypeError(f"{path.name}:{v} is {vals.dtype}, expected datetime64 "
                                f"(check units attribute / decode_times)")
            ri = C.nearest_index(ds[latn].values, lat, 0.6 * step)
            ci = C.nearest_index(ds[lonn].values, lon, 0.6 * step)
            sub = vals[np.ix_(np.maximum(ri, 0), np.maximum(ci, 0))]
            idx = C.day_index(sub)
            # placeholder dates (e.g. 1970-01-01 written for "no onset") are missing values
            idx[idx < -RADS_PLACEHOLDER_DAYS] = SENT
            idx[ri < 0, :] = SENT
            idx[:, ci < 0] = SENT
            out[key] = idx
            info[f"{key}_grid_miss"] = int((ri < 0).sum() + (ci < 0).sum())
        ok = (out["onset"] != SENT) & (out["demise"] != SENT)
        info["frac_with_dates"] = float(ok.mean())
        if ok.any():
            jan1 = int((np.datetime64(f"{year}-01-01") - C.ORIGIN).astype(int))
            rel = out["onset"][ok] - jan1
            info["onset_rel_jan1_p1_p50_p99"] = [int(np.percentile(rel, q)) for q in (1, 50, 99)]
    return year, out["onset"], out["demise"], info


def _year_of(idx):
    """day index -> calendar year (SENT -> -1)."""
    y = (C.index_to_date(np.where(idx == SENT, 0, idx)).astype("datetime64[Y]").astype(int) + 1970)
    return np.where(idx == SENT, -1, y)


def pair_seasons(on_f, de_f, years_out):
    """
    Re-pair RADS onset and demise dates into seasons.

    RADS files do not all store a season's onset and demise in the same yearly file: in the
    africa_RainyAndDrySeason.pentad.CHIRPS files the file of year Y holds the onset of the
    season starting in Y+1 and the demise of the season ending in Y (the RADS code finds
    demises backwards in time). So every onset (file k) is paired with the EARLIEST demise
    after it, taken from file k-1, k or k+1, that gives a plausible season length; the
    season is then indexed by the calendar year of its onset. Works for both layouts.

    on_f, de_f: (K, ...) day indices by FILE year. Returns onset, demise (Y, ...) by SEASON
    year (years_out), and how many seasons used a demise from file k-1 / k / k+1.
    """
    K = on_f.shape[0]
    best = np.full(on_f.shape, SENT, dtype=np.int32)
    bestlen = np.full(on_f.shape, np.iinfo(np.int32).max, dtype=np.int64)
    used = {}
    src = np.zeros(on_f.shape, dtype=np.int8)
    for shift in (-1, 0, 1):
        D = np.full_like(de_f, SENT)
        if shift < 0:
            D[1:] = de_f[:-1]
        elif shift > 0:
            D[:-1] = de_f[1:]
        else:
            D[:] = de_f
        ln = D.astype(np.int64) - on_f + 1
        ok = ((on_f != SENT) & (D != SENT) & (ln >= C.SEASON_LEN_MIN_SANITY) &
              (ln <= C.SEASON_LEN_MAX_SANITY) & (ln < bestlen))
        best[ok], bestlen[ok], src[ok] = D[ok], ln[ok], shift
    paired = best != SENT
    for shift in (-1, 0, 1):
        used[f"file{shift:+d}"] = int((paired & (src == shift)).sum())
    used["onset_without_demise"] = int(((on_f != SENT) & ~paired).sum())
    Y = len(years_out)
    onset = np.full((Y,) + on_f.shape[1:], SENT, dtype=np.int32)
    demise = np.full_like(onset, SENT)
    yi = _year_of(on_f) - years_out[0]
    m = paired & (yi >= 0) & (yi < Y)
    k, *rest = np.nonzero(m)
    order = np.argsort(-k, kind="stable")                 # assign latest files first, earliest wins
    sel = tuple(r[order] for r in rest)
    onset[(yi[m][order],) + sel] = on_f[m][order]
    demise[(yi[m][order],) + sel] = best[m][order]
    return onset, demise, used


def load_rads(lon, lat, workers):
    files, d = C.find_rads_files()
    # every available file: a season's onset and demise may sit in neighbouring files
    fyears = sorted(y for y in files if C.SEASON_YEAR_MIN - 1 <= y <= C.SEASON_YEAR_MAX + 1)
    years = [y for y in range(C.SEASON_YEAR_MIN, C.SEASON_YEAR_MAX + 1)
             if y in files or y - 1 in files]
    logger.info(f"RADS: {len(fyears)} files {fyears[0]}-{fyears[-1]} from {d}")
    K = len(fyears)
    on_f = np.full((K, len(lat), len(lon)), SENT, dtype=np.int32)
    de_f = np.full_like(on_f, SENT)
    infos = []
    with ProcessPoolExecutor(max_workers=min(workers, K), mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(_rads_year, (y, files[y], lon, lat)) for y in fyears]
        for f in as_completed(futs):
            y, on, de, info = f.result()
            k = fyears.index(y)
            on_f[k], de_f[k] = on, de
            infos.append(info)
    infos = pd.DataFrame(infos).sort_values("year")
    for col in ("onset_dims", "onset_extra_dim", "demise_extra_dim"):
        if col in infos:
            logger.info(f"  RADS {col}: {infos[col].dropna().unique().tolist()}")
    onset, demise, used = pair_seasons(on_f, de_f, np.array(years))
    logger.info(f"  RADS seasons paired (demise taken from the file before / same / after the onset file): "
                f"{used['file-1']:,} / {used['file+0']:,} / {used['file+1']:,}; onsets without a plausible "
                f"demise: {used['onset_without_demise']:,}")
    # onset diagnostics: a real onset varies from year to year
    ok = onset != SENT
    if ok.any():
        d = C.index_to_date(np.where(ok, onset, 0))
        doy = np.where(ok, (d - d.astype("datetime64[Y]")).astype(int) + 1, np.nan).reshape(len(years), -1)
        top = pd.Series(doy[np.isfinite(doy)]).value_counts(normalize=True).head(5)
        logger.info("  RADS onset day-of-year, most frequent: " +
                    ", ".join(f"{int(k)} ({v:.0%})" for k, v in top.items()))
        n_on = np.isfinite(doy).sum(0)
        with np.errstate(invalid="ignore"):
            sd = np.nanstd(doy, axis=0)
        frozen = (n_on >= 5) & (sd < 1)
        logger.info(f"  RADS cells whose onset day-of-year never changes (sd < 1 d, >= 5 seasons): "
                    f"{frozen.sum():,} of {(n_on >= 5).sum():,}")
        if frozen.sum() > 0.2 * max(1, (n_on >= 5).sum()):
            logger.warning("  MANY RADS onsets fall on the same day every year - check the RADS files "
                           "(onset_date / onset_pentad); sowing dates relative to onset are meaningless there")
    return np.array(years), onset, demise, infos


# =============================================================================
# CORE (pure numpy, per chunk)
# =============================================================================

def season_validity(onset, demise, years, has, cell_ok):
    """
    onset, demise: (ncell, Y) day indices (SENT = missing). Returns reason (ncell, Y) uint8.
    """
    ncell, Y = onset.shape
    n_days = len(has)
    reason = np.full((ncell, Y), C.S_OK, dtype=np.uint8)
    miss = (onset == SENT) | (demise == SENT)
    reason[miss] = C.S_NO_RADS
    length = demise.astype(np.int64) - onset + 1
    bad_len = ~miss & ((demise <= onset) | (length < C.SEASON_LEN_MIN_SANITY) |
                       (length > C.SEASON_LEN_MAX_SANITY))
    reason[bad_len & (reason == 0)] = C.S_BAD_LENGTH
    jan1 = np.array([(np.datetime64(f"{y}-01-01") - C.ORIGIN).astype(int) for y in years])
    dec31 = np.array([(np.datetime64(f"{y}-12-31") - C.ORIGIN).astype(int) for y in years])
    bad_year = ~miss & ((onset < jan1 + C.ONSET_EARLIEST_REL) | (onset > dec31))
    reason[bad_year & (reason == 0)] = C.S_BAD_YEAR
    # full rainfall coverage of [onset, demise]
    gaps = np.r_[0, np.cumsum(~has)]
    o = np.clip(onset, 0, n_days - 1)
    e = np.clip(demise, 0, n_days - 1)
    no_data = ~miss & ((onset < 0) | (demise >= n_days) | (gaps[e + 1] - gaps[o] > 0))
    reason[no_data & (reason == 0)] = C.S_NO_DATA
    # overlap / duplicate with the previous accepted season
    last_end = np.full(ncell, -10**9, dtype=np.int64)
    for y in range(Y):
        ok = reason[:, y] == 0
        ov = ok & (onset[:, y] <= last_end)
        reason[ov, y] = C.S_OVERLAP
        acc = ok & ~ov
        last_end[acc] = demise[acc, y]
    reason[(reason == 0) & ~cell_ok[:, None]] = C.S_CELL_INVALID
    return reason


def match_spells(sp_cell, sp_start, sp_end, onset, demise, valid):
    """
    Assign spells to season windows and clip them.
    Returns sid (flat cell*Y+y), clipped offsets (start, end) from onset, clipped length.
    Spells must be sorted by (cell, start) - step1 writes them that way.
    """
    ncell, Y = onset.shape
    ws = onset.astype(np.int64) + C.EXCLUDE_FIRST_DAYS
    we = demise.astype(np.int64) - C.EXCLUDE_LAST_DAYS
    use = valid & (we >= ws)
    cc, yy = np.nonzero(use)                      # sorted by cell, then year (= time)
    if len(cc) == 0 or len(sp_cell) == 0:         # chunk without any usable season / spell
        e = np.zeros(0, dtype=np.int64)
        return e, e, e, e
    BIG = np.int64(1) << 24
    key = cc.astype(np.int64) * BIG + ws[cc, yy]
    order = np.argsort(key, kind="stable")
    cc, yy, key = cc[order], yy[order], key[order]
    q = sp_cell.astype(np.int64) * BIG + sp_end
    last = np.searchsorted(key, q, side="right") - 1
    # A spell can overlap the window of the last season starting before its end AND,
    # rarely, the window of the season before (spell bridging the dry season). Windows
    # never overlap (overlapping seasons are rejected), so two candidates are enough.
    sp_i, win = [], []
    for pos in (last, last - 1):
        ok = pos >= 0
        p = np.where(ok, pos, 0)
        ok &= cc[p] == sp_cell
        ok &= (sp_start <= we[cc[p], yy[p]]) & (sp_end >= ws[cc[p], yy[p]])
        sp_i.append(np.nonzero(ok)[0])
        win.append(p[ok])
    sp_i, win = np.concatenate(sp_i), np.concatenate(win)
    c, y = cc[win], yy[win]
    s0, e0 = sp_start[sp_i], sp_end[sp_i]
    s1 = np.maximum(s0, ws[c, y])
    e1 = np.minimum(e0, we[c, y])
    if C.EDGE_POLICY == "exclude":
        inside = (s0 >= ws[c, y]) & (e0 <= we[c, y])
    else:
        inside = np.ones(len(s1), dtype=bool)
    L = e1 - s1 + 1
    keep = inside & (L >= C.MIN_SPELL)
    c, y, s1, e1, L = c[keep], y[keep], s1[keep], e1[keep], L[keep]
    on = onset[c, y].astype(np.int64)
    sid = c.astype(np.int64) * Y + y
    o = np.lexsort((s1, sid))
    return sid[o], (s1 - on)[o], (e1 - on)[o], L[o]


def season_stats(sid, off_s, L, n_seasons):
    """Per-season aggregates (flat arrays of length n_seasons; NaN where no spell)."""
    n = np.bincount(sid, minlength=n_seasons).astype(np.int32)
    first = np.full(n_seasons, np.nan, dtype=np.float32)
    first_len = np.full_like(first, np.nan)
    last = np.full_like(first, np.nan)
    longest = np.full_like(first, np.nan)
    longest_start = np.full_like(first, np.nan)
    dry_days = np.zeros(n_seasons, dtype=np.float32)
    if len(sid):
        u, i0 = np.unique(sid, return_index=True)
        i1 = np.r_[i0[1:], len(sid)] - 1
        first[u] = off_s[i0]
        first_len[u] = L[i0]
        last[u] = off_s[i1]
        gmax = np.maximum.reduceat(L, i0)
        longest[u] = gmax
        dry_days[u] = np.add.reduceat(L, i0)
        grp = np.repeat(np.arange(len(u)), np.diff(np.r_[i0, len(sid)]))
        is_max = L == gmax[grp]
        uu, j = np.unique(sid[is_max], return_index=True)
        longest_start[uu] = off_s[is_max][j]
    return dict(n=n, first=first, first_len=first_len, last=last,
                longest=longest, longest_start=longest_start, dry_days=dry_days)


def drought_prob_curve(sid, off_s, off_e, valid, window_end_off, M, ncell, Y):
    """P(day d after onset is inside a qualifying dry spell), d = 0..M-1, per cell."""
    diff = np.zeros((ncell * Y, M + 1), dtype=np.int16)
    if len(sid):
        np.add.at(diff, (sid, np.clip(off_s, 0, M)), 1)
        np.add.at(diff, (sid, np.clip(off_e + 1, 0, M)), -1)
    in_sp = np.cumsum(diff[:, :M], axis=1, dtype=np.int16) > 0
    hits = in_sp.reshape(ncell, Y, M).sum(1)
    d = np.arange(M)
    covered = (valid[:, :, None] & (d[None, None, :] >= C.EXCLUDE_FIRST_DAYS)
               & (d[None, None, :] <= window_end_off[:, :, None]))
    cnt = covered.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        prob = np.where(cnt >= C.STEP2_MIN_SEASONS, hits / np.maximum(cnt, 1), np.nan)
    return prob.astype(np.float32)


def cell_metrics(st, valid, season_len, window_len, onset_rel, demise_rel, ncell, Y):
    """Per-cell layers from per-season arrays (all (ncell, Y))."""
    nv = valid.sum(1)
    enough = nv >= C.STEP2_MIN_SEASONS

    def med(a, cond=None):
        m = valid if cond is None else (valid & cond)
        x = np.where(m, a, np.nan)
        r = np.nanmedian(x, axis=1)
        r[~enough] = np.nan
        return r.astype(np.float32)

    def frac(cond):
        with np.errstate(invalid="ignore", divide="ignore"):
            r = (valid & cond).sum(1) / np.maximum(nv, 1)
        r = r.astype(np.float32)
        r[~enough] = np.nan
        return r

    n = st["n"].reshape(ncell, Y).astype(np.float32)
    first = st["first"].reshape(ncell, Y)
    has_sp = n > 0
    out = {
        "n_valid_seasons": nv.astype(np.float32),
        "season_len_median": med(season_len),
        "onset_doy_median": med(onset_rel + 1),       # can be <= 0 if onset in previous year
        "demise_doy_median": med(demise_rel + 1),     # can be > 365 if demise in next year
        "nb_spells_median": med(n),
        "nb_spells_mean": np.where(enough, np.nanmean(np.where(valid, n, np.nan), 1), np.nan).astype(np.float32),
        "p_nb_ge1": frac(n >= 1), "p_nb_ge2": frac(n >= 2), "p_nb_ge3": frac(n >= 3),
        "first_start_median_cond": med(first, has_sp),
        "first_len_median_cond": med(st["first_len"].reshape(ncell, Y), has_sp),
        "last_start_median_cond": med(st["last"].reshape(ncell, Y), has_sp),
        "longest_len_median_cond": med(st["longest"].reshape(ncell, Y), has_sp),
        "longest_start_median_cond": med(st["longest_start"].reshape(ncell, Y), has_sp),
        "dry_frac_median": med(np.where(window_len > 0,
                                        st["dry_days"].reshape(ncell, Y) / np.maximum(window_len, 1), np.nan)),
        "first_start_rel_median_cond": med(first / season_len, has_sp),
    }
    for x in C.X_DAYS:
        out[f"p_first_le_{x}"] = frac(has_sp & (first <= x))
    return out


# =============================================================================
# WORKER
# =============================================================================

def process_rows(r0, r1):
    import pyarrow as pa
    import pyarrow.parquet as pq

    g = _G
    nlon, Y, years = len(g["lon"]), len(g["years"]), g["years"]
    nr = r1 - r0
    ncell = nr * nlon
    onset = g["onset"][:, r0:r1, :].reshape(Y, ncell).T.copy()
    demise = g["demise"][:, r0:r1, :].reshape(Y, ncell).T.copy()
    cell_ok = g["cell_ok"][r0:r1].ravel()

    reason = season_validity(onset, demise, years, g["has"], cell_ok)
    valid = reason == C.S_OK

    part = Path(g["spell_dir"]) / f"part_r{r0:05d}.parquet"
    tbl = pq.read_table(part, columns=["row", "col", "start", "end", "length"])
    sp = {k: tbl[k].to_numpy() for k in tbl.column_names}
    sp_cell = (sp["row"].astype(np.int64) - r0) * nlon + sp["col"]
    keep = (sp_cell >= 0) & (sp_cell < ncell)
    sp_cell, sp_s, sp_e = sp_cell[keep], sp["start"][keep].astype(np.int64), sp["end"][keep].astype(np.int64)
    o = np.lexsort((sp_s, sp_cell))
    sp_cell, sp_s, sp_e = sp_cell[o], sp_s[o], sp_e[o]
    del tbl, sp

    sid, off_s, off_e, L = match_spells(sp_cell, sp_s, sp_e, onset, demise, valid)
    st = season_stats(sid, off_s, L, ncell * Y)

    season_len = (demise.astype(np.int64) - onset + 1).astype(np.float32)
    window_end_off = (demise.astype(np.int64) - onset - C.EXCLUDE_LAST_DAYS)
    window_len = np.maximum(window_end_off - C.EXCLUDE_FIRST_DAYS + 1, 0).astype(np.float32)
    jan1 = np.array([(np.datetime64(f"{y}-01-01") - C.ORIGIN).astype(int) for y in years])
    onset_rel = (onset.astype(np.int64) - jan1[None, :]).astype(np.float32)
    demise_rel = (demise.astype(np.int64) - jan1[None, :]).astype(np.float32)
    bad = onset == SENT
    for a in (season_len, onset_rel, demise_rel, window_len):
        a[bad | (demise == SENT)] = np.nan

    metrics = cell_metrics(st, valid, season_len, window_len, onset_rel, demise_rel, ncell, Y)
    # spell duration median over all clipped spells of the cell
    dur = np.full(ncell, np.nan, dtype=np.float32)
    if len(sid):
        cell_of = sid // Y
        s = pd.Series(L).groupby(cell_of).median()
        dur[s.index.values] = s.values
    dur[metrics["n_valid_seasons"] < C.STEP2_MIN_SEASONS] = np.nan
    metrics["spell_len_median"] = dur

    prob = drought_prob_curve(sid, off_s, off_e, valid, window_end_off, g["max_offset"], ncell, Y)

    # season table
    cc, yy = np.divmod(np.arange(ncell * Y), Y)
    rows = (cc // nlon + r0).astype(np.int16)
    cols = (cc % nlon).astype(np.int16)
    epoch = int((C.ORIGIN - np.datetime64("1970-01-01", "D")).astype(int))
    on_f, de_f = onset.ravel(), demise.ravel()
    tbl = pa.table({
        "row": rows, "col": cols,
        "lat": g["lat"][rows].astype(np.float32), "lon": g["lon"][cols].astype(np.float32),
        "year": years[yy].astype(np.int16),
        "onset_date": pa.array(np.where(on_f == SENT, 0, on_f + epoch).astype(np.int32), type=pa.date32(),
                               mask=on_f == SENT),
        "demise_date": pa.array(np.where(de_f == SENT, 0, de_f + epoch).astype(np.int32), type=pa.date32(),
                                mask=de_f == SENT),
        "season_len": season_len.ravel(), "window_len": window_len.ravel(),
        "reason": reason.ravel(), "valid": valid.ravel(),
        "n_spells": np.where(valid.ravel(), st["n"], -1).astype(np.int16),
        "first_start": st["first"], "first_len": st["first_len"], "last_start": st["last"],
        "longest_len": st["longest"], "longest_start": st["longest_start"],
        "dry_days": np.where(valid.ravel(), st["dry_days"], np.nan).astype(np.float32),
    })
    pq.write_table(tbl, Path(g["season_dir"]) / f"part_r{r0:05d}.parquet", compression="zstd")

    rc = np.bincount(reason.ravel(), minlength=8)
    res = {k: v.reshape(nr, nlon) for k, v in metrics.items()}
    res["_any_rads"] = ((reason != C.S_NO_RADS).any(1)).reshape(nr, nlon)
    gc.collect()
    return r0, r1, res, prob.T.reshape(-1, nr, nlon), rc, len(sid)


# =============================================================================
# MAIN
# =============================================================================

MAP_SPECS = [
    # var, title, colour bar label, cmap, vmin, vmax
    ("n_valid_seasons", "Number of valid RADS seasons", "seasons", "Greens", 0, None),
    ("season_len_median", "Median season length (RADS)", "days", "Greens", None, None),
    ("onset_doy_median", "Median onset (RADS)", "day of year", "Blues", None, None),
    ("nb_spells_median", "Median number of dry spells per season (>=10 d, <1 mm)", "spells/season", "Oranges", 0, None),
    ("nb_spells_mean", "Mean number of dry spells per season", "spells/season", "Oranges", 0, None),
    ("p_nb_ge1", "P(at least one dry spell in the season)", "probability", "Purples", 0, 1),
    ("p_first_le_60", "P(first dry spell starts <= 60 d after onset)", "probability", "Purples", 0, 1),
    ("first_start_median_cond", "Median start of 1st dry spell (seasons with a spell)", "days after onset", "Blues", None, None),
    ("longest_len_median_cond", "Median longest dry spell (seasons with a spell)", "days", "Oranges", None, None),
    ("spell_len_median", "Median dry spell duration", "days", "Oranges", None, None),
    ("dry_frac_median", "Median fraction of season window in dry spells", "fraction", "Oranges", 0, None),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="study")
    ap.add_argument("--bbox", nargs=4, type=float)
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 4))
    a = ap.parse_args()

    name, _ = C.parse_region(a.region, a.bbox)
    s1 = C.region_dir(name) / "step1"
    out = C.region_dir(name) / "step2"
    C.setup_logging(out / "step2.log")
    t0 = time.time()
    meta = C.read_json(s1 / "step1_meta.json")
    with xr.open_dataset(s1 / "grid_meta.nc") as _d:   # closed before forking workers
        gm = _d.load()
    lon, lat = gm.lon.values, gm.lat.values
    has = np.load(s1 / "day_has_data.npy")
    logger.info("=" * 70)
    logger.info(f"v7 STEP2  region={name}  grid {len(lon)}x{len(lat)}  workers={a.workers}")
    logger.info(f"  spells >= {C.MIN_SPELL} d after clipping to [onset+{C.EXCLUDE_FIRST_DAYS}, "
                f"demise-{C.EXCLUDE_LAST_DAYS}], edge policy = {C.EDGE_POLICY}")
    logger.info(f"  seasons {C.SEASON_YEAR_MIN}-{C.SEASON_YEAR_MAX}; rainfall data until {meta['last_day_with_data']}")
    logger.info("=" * 70)

    years, onset, demise, rads_info = load_rads(lon, lat, min(a.workers, 16))
    (out).mkdir(parents=True, exist_ok=True)
    rads_info.to_csv(out / "rads_summary.csv", index=False)

    season_dir = out / "seasons"
    season_dir.mkdir(parents=True, exist_ok=True)
    for f in season_dir.glob("part_*.parquet"):
        f.unlink()
    _G.update(lon=lon, lat=lat, years=years, onset=onset, demise=demise, has=has,
              cell_ok=gm["valid"].values.astype(bool), spell_dir=str(s1 / "spells"),
              season_dir=str(season_dir), max_offset=C.MAX_OFFSET)

    nlat, nlon = len(lat), len(lon)
    layers = {}
    prob = np.full((C.MAX_OFFSET, nlat, nlon), np.nan, dtype=np.float32)
    any_rads = np.zeros((nlat, nlon), dtype=bool)
    rc_total = np.zeros(8, dtype=np.int64)
    chunks = [tuple(c) for c in meta["chunks"]]
    n_sp = 0
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(process_rows, r0, r1) for r0, r1 in chunks]
        for i, f in enumerate(as_completed(futs), 1):
            r0, r1, res, pr, rc, n = f.result()
            for k, v in res.items():
                if k == "_any_rads":
                    any_rads[r0:r1] = v
                    continue
                layers.setdefault(k, np.full((nlat, nlon), np.nan, dtype=np.float32))[r0:r1] = v
            prob[:, r0:r1, :] = pr
            rc_total += rc
            n_sp += n
            if i % 20 == 0 or i == len(chunks):
                logger.info(f"  {i}/{len(chunks)} chunks, {n_sp:,} in-season spells")

    # reason code per pixel
    reason = gm["reason"].values.astype(np.uint8).copy()
    ok_cell = reason == C.REASON_OK
    reason[ok_cell & ~any_rads] = C.REASON_NO_RADS
    reason[ok_cell & any_rads & ~(layers["n_valid_seasons"] >= C.STEP2_MIN_SEASONS)] = C.REASON_FEW_SEASONS

    # peak of drought-probability curve
    allnan = np.all(np.isnan(prob), axis=0)
    peak_off = np.nanargmax(np.where(np.isnan(prob), -1, prob), axis=0).astype(np.float32)
    peak_off[allnan] = np.nan
    layers["drought_prob_peak_offset"] = peak_off
    layers["drought_prob_peak"] = np.where(allnan, np.nan, np.nanmax(prob, axis=0)).astype(np.float32)

    # NetCDF
    data_vars = {k: (("lat", "lon"), v) for k, v in layers.items() if not k.startswith("p_first_le_")}
    data_vars["reason"] = (("lat", "lon"), reason)
    data_vars["bimodal_ratio"] = (("lat", "lon"), gm["bimodal_ratio"].values)
    data_vars["p_first_le"] = (("x_days", "lat", "lon"), np.stack([layers[f"p_first_le_{x}"] for x in C.X_DAYS]))
    data_vars["drought_prob"] = (("offset", "lat", "lon"), prob)
    ds = xr.Dataset(data_vars, coords={"lat": lat, "lon": lon, "x_days": C.X_DAYS,
                                       "offset": np.arange(C.MAX_OFFSET)},
                    attrs={"region": name, "min_spell_days": C.MIN_SPELL, "dry_mm": C.DRY_MM,
                           "exclude_first_days": C.EXCLUDE_FIRST_DAYS, "exclude_last_days": C.EXCLUDE_LAST_DAYS,
                           "edge_policy": C.EDGE_POLICY, "season_years": f"{years[0]}-{years[-1]}",
                           "min_valid_seasons": C.STEP2_MIN_SEASONS,
                           "offset": "days after RADS onset (onset = 0)",
                           "p_first_le": "fraction of valid seasons whose first qualifying spell starts <= x days after onset "
                                         "(seasons without a spell count as no)",
                           "reason_codes": str(C.REASON_LABELS)})
    enc = {v: {"zlib": True, "complevel": 4} for v in ds.data_vars}
    ds.to_netcdf(out / "metrics.nc", encoding=enc)
    logger.info(f"Written {out / 'metrics.nc'}")

    # GeoTIFF + PNG
    bnd = C.load_boundaries(meta["bbox"])
    C.save_geotiff(out / "cog" / "reason.tif", reason, lon, lat, nodata=255, dtype="uint8")
    C.save_geotiff(out / "cog" / "p_first_le.tif", ds["p_first_le"].values, lon, lat,
                   band_names=[f"p_first_le_{x}" for x in C.X_DAYS])
    for var, title, clab, cmap, vmin, vmax in MAP_SPECS + [
            ("drought_prob_peak", "Peak daily drought probability", "probability", "Purples", 0, 1),
            ("drought_prob_peak_offset", "Offset of peak drought probability", "days after onset", "Blues", None, None)]:
        arr = layers[var]
        C.save_geotiff(out / "cog" / f"{var}.tif", arr, lon, lat)
        C.plot_map(out / "png" / f"{var}.png", arr, lon, lat, title, clab, cmap=cmap,
                   vmin=vmin, vmax=vmax, boundaries=bnd, reason=reason)

    # audit tables
    labels = {C.S_OK: "ok", C.S_NO_RADS: "RADS missing", C.S_BAD_LENGTH: "bad length/order",
              C.S_BAD_YEAR: "onset outside year", C.S_NO_DATA: "no rainfall coverage",
              C.S_OVERLAP: "overlap/duplicate", C.S_CELL_INVALID: "cell invalid"}
    pd.DataFrame({"season_reason": [labels.get(i, i) for i in range(8)], "n": rc_total}) \
        .to_csv(out / "season_reason_summary.csv", index=False)
    cnt = pd.Series(reason.ravel()).value_counts().sort_index()
    pd.DataFrame({"reason": [C.REASON_LABELS[i] for i in cnt.index], "pixels": cnt.values}) \
        .to_csv(out / "reason_summary.csv", index=False)
    for i, v in cnt.items():
        logger.info(f"  pixels {C.REASON_LABELS[i]:<28} {v:>10,}")
    for i, v in enumerate(rc_total):
        if v:
            logger.info(f"  seasons {labels.get(i, i):<27} {v:>10,}")
    logger.info(f"STEP2 done in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()
