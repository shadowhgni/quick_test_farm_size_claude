#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9_rads.py - read the downloaded RADS files (SEASON_SOURCE = "rads")
=====================================================================

Files: RADS_FILE_PATTERN, one per year, e.g. ../chirps_africa/africa_RainyAndDrySeason.pentad.CHIRPS.1981.nc
(output of the RADS code of Bombardi et al. 2019 on CHIRPS pentads):

  * onset / demise variables found by name (datetime variables preferred over *_pentad / *_jday),
    transposed by dimension NAME to (lat, lon); extra dimensions (e.g. reference_year) -> first slice;
  * placeholder dates (e.g. 1970-01-01 for "no season") = missing;
  * RADS grid -> region (CHIRPS) grid by nearest cell;
  * in a yearly file the onset may come before the demise (season inside the year) or after it (the
    demise belongs to the season that started the year before; e.g. files holding the onset of the
    season starting in Y+1 and the demise of the season ending in Y, or seasons crossing 31 December).
    So every onset is paired with the EARLIEST demise after it (from the file before, the same file
    or the file after) giving SEASON_LEN_MIN..SEASON_LEN_MAX days, and the season is named by the
    calendar year of its onset; both orders and the cross-year seasons are counted in the log;
  * diagnostic: cells whose onset falls on the same day of year every year (seen in the HPC files,
    e.g. 1 May at Kano), which makes "days after onset" meaningless there.

    python v9_rads.py --region ci_nga        # inspect the files: grid, variables, pairing, onset diagnostics
"""

import argparse
import logging
import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v9_common as C   # noqa: E402

logger = logging.getLogger("dryspell_v9")
SENT = np.iinfo(np.int32).min


def rads_files():
    """{year: path} of the RADS files that exist for SEASON_YEAR_MIN-1 .. SEASON_YEAR_MAX+1."""
    out = {}
    for y in range(C.SEASON_YEAR_MIN - 1, C.SEASON_YEAR_MAX + 2):
        p = Path(C.RADS_FILE_PATTERN.format(year=y))
        if p.exists():
            out[y] = p
    if not out:
        sys.exit(f"no RADS file found: {C.RADS_FILE_PATTERN.format(year='YYYY')} for years "
                 f"{C.SEASON_YEAR_MIN - 1}-{C.SEASON_YEAR_MAX + 1} (working folder {Path.cwd()}) - set "
                 f"RADS_FILE_PATTERN in v9_config.py section G2")
    return out


def _find_var(ds, keys):
    """First variable whose name contains one of keys; datetime variables preferred."""
    hits = [v for v in ds.data_vars if any(k in v.lower() for k in keys)]
    if not hits:
        raise KeyError(f"no variable matching {keys} in {list(ds.data_vars)}")
    dates = [v for v in hits if np.issubdtype(ds[v].dtype, np.datetime64)]
    return (dates or hits)[0]


def _read_year(args):
    """One RADS file -> onset / demise day indices (SENT = missing) on the region grid."""
    year, path, lon, lat = args
    with xr.open_dataset(path) as ds:
        out, info = {}, {"year": year, "file": path.name}
        for key, names in (("onset", ("onset",)), ("demise", ("demise", "cessation", "offset", "end"))):
            v = _find_var(ds, names)
            da = ds[v]
            latn, lonn = C.spatial_names(da)
            for d in list(da.dims):
                if d not in (latn, lonn):
                    if da.sizes[d] > 1:
                        info[f"{key}_extra_dim"] = f"{d}={da.sizes[d]} (first taken)"
                    da = da.isel({d: 0})
            da = da.transpose(latn, lonn)
            vals = da.values
            if not np.issubdtype(vals.dtype, np.datetime64):
                raise TypeError(f"{path.name}:{v} is {vals.dtype}, expected dates (check its units attribute)")
            rlat, rlon = ds[latn].values, ds[lonn].values
            tol_lat = 0.5 * abs(C.regular_step(rlat)) + 0.5 * abs(C.regular_step(lat)) + 1e-6
            tol_lon = 0.5 * abs(C.regular_step(rlon)) + 0.5 * abs(C.regular_step(lon)) + 1e-6
            ri = C.nearest_index(rlat, lat, tol_lat)
            ci = C.nearest_index(rlon, lon, tol_lon)
            idx = C.day_index(vals[np.ix_(np.maximum(ri, 0), np.maximum(ci, 0))])
            idx[idx < -C.RADS_PLACEHOLDER_DAYS] = SENT
            idx[ri < 0, :] = SENT
            idx[:, ci < 0] = SENT
            out[key] = idx
            info[f"{key}_var"] = v
            info["rads_grid"] = f"{len(rlon)}x{len(rlat)} step {abs(C.regular_step(rlon)):.4f}"
            info["outside_rads_grid"] = int((ri < 0).sum() * len(lon) + (ci < 0).sum() * len(lat))
    info["share_with_onset"] = float((out["onset"] != SENT).mean())
    both = (out["onset"] != SENT) & (out["demise"] != SENT)
    n_both = max(int(both.sum()), 1)
    # within ONE file: onset before demise = season inside the file year; demise before onset = the demise
    # belongs to the season that started earlier - both are re-paired by date below
    info["onset_before_demise"] = round(float((both & (out["onset"] < out["demise"])).sum()) / n_both, 3)
    info["demise_before_onset"] = round(float((both & (out["onset"] > out["demise"])).sum()) / n_both, 3)
    return year, out["onset"], out["demise"], info


def _year_of(idx):
    y = C.index_to_date(np.where(idx == SENT, 0, idx)).astype("datetime64[Y]").astype(int) + 1970
    return np.where(idx == SENT, -1, y)


def pair_seasons(on_f, de_f, years_out):
    """
    on_f, de_f (K, ...): day indices by FILE year. -> onset, demise (Y, ...) by SEASON year (year of
    the onset), and counts of demises taken from the file before / same / after the onset file.
    """
    best = np.full(on_f.shape, SENT, np.int32)
    bestlen = np.full(on_f.shape, np.iinfo(np.int32).max, np.int64)
    src = np.zeros(on_f.shape, np.int8)
    for shift in (-1, 0, 1):
        D = np.full_like(de_f, SENT)
        if shift < 0:
            D[1:] = de_f[:-1]
        elif shift > 0:
            D[:-1] = de_f[1:]
        else:
            D[:] = de_f
        ln = D.astype(np.int64) - on_f + 1
        ok = ((on_f != SENT) & (D != SENT) & (ln >= C.SEASON_LEN_MIN) & (ln <= C.SEASON_LEN_MAX) & (ln < bestlen))
        best[ok], bestlen[ok], src[ok] = D[ok], ln[ok], shift
    paired = best != SENT
    used = {f"file{s:+d}": int((paired & (src == s)).sum()) for s in (-1, 0, 1)}
    used["onset_without_demise"] = int(((on_f != SENT) & ~paired).sum())
    Y = len(years_out)
    onset = np.full((Y,) + on_f.shape[1:], SENT, np.int32)
    demise = np.full_like(onset, SENT)
    yi = _year_of(on_f) - years_out[0]
    m = paired & (yi >= 0) & (yi < Y)
    k, *rest = np.nonzero(m)
    order = np.argsort(-k, kind="stable")                 # latest files first, earliest file wins
    sel = tuple(r[order] for r in rest)
    onset[(yi[m][order],) + sel] = on_f[m][order]
    demise[(yi[m][order],) + sel] = best[m][order]
    return onset, demise, used


def load_rads(lon, lat, workers=8):
    """-> years (SEASON_YEAR_MIN..MAX), onset, demise (Y, nlat, nlon) int32 day indices (SENT = none),
    per-file info DataFrame, diagnostics dict."""
    files = rads_files()
    fyears = sorted(files)
    years = np.arange(C.SEASON_YEAR_MIN, C.SEASON_YEAR_MAX + 1)
    missing = [int(y) for y in years if y not in files and y - 1 not in files]
    logger.info(f"RADS: {len(fyears)} files {fyears[0]}-{fyears[-1]} ({C.RADS_FILE_PATTERN})")
    if missing:
        logger.warning(f"RADS: no file for seasons {missing} - those years have no season")
    K = len(fyears)
    on_f = np.full((K, len(lat), len(lon)), SENT, np.int32)
    de_f = np.full_like(on_f, SENT)
    infos = []
    with ProcessPoolExecutor(max_workers=max(1, min(workers, K)), mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(_read_year, (y, files[y], lon, lat)) for y in fyears]
        for f in as_completed(futs):
            y, on, de, info = f.result()
            on_f[fyears.index(y)], de_f[fyears.index(y)] = on, de
            infos.append(info)
    infos = pd.DataFrame(infos).sort_values("year")
    for col in ("onset_var", "demise_var", "rads_grid", "onset_extra_dim", "demise_extra_dim"):
        if col in infos:
            logger.info(f"  RADS {col}: {infos[col].dropna().unique().tolist()}")
    if "onset_before_demise" in infos:
        logger.info(f"  RADS within-file order (cells with both dates): onset before demise in "
                    f"{infos.onset_before_demise.median():.0%} of cells (median over files), demise before onset in "
                    f"{infos.demise_before_onset.median():.0%} - every onset is re-paired with the next demise")
    onset, demise, used = pair_seasons(on_f, de_f, years)
    logger.info(f"  RADS pairing: demise from the file before / same / after the onset file "
                f"{used['file-1']:,} / {used['file+0']:,} / {used['file+1']:,}; onsets without a plausible "
                f"demise {used['onset_without_demise']:,}")
    diag = {"pairing": used}
    per_year = ((onset != SENT) & (demise != SENT)).reshape(len(years), -1).sum(1)
    if len(per_year) > 2 and per_year[0] < 0.5 * np.median(per_year[1:]):
        logger.warning(f"  RADS: season {years[0]} has {per_year[0]:,} cells vs a median of {int(np.median(per_year[1:])):,} - "
                       f"with the cross-year layout its onsets sit in the file of {years[0] - 1}, which is missing")
    okp = (onset != SENT) & (demise != SENT)
    if okp.any():
        cross = okp & (_year_of(demise) > _year_of(onset))
        diag["cross_year_seasons"] = int(cross.sum())
        logger.info(f"  RADS seasons after pairing: {int(okp.sum()):,}, of which {int(cross.sum()):,} cross 31 December "
                    f"(onset year < demise year; named by the onset year)")
    ok = onset != SENT
    if ok.any():
        d = C.index_to_date(np.where(ok, onset, 0))
        doy = np.where(ok, (d - d.astype("datetime64[Y]")).astype(int), np.nan).reshape(len(years), -1)
        top = pd.Series(doy[np.isfinite(doy)]).value_counts(normalize=True).head(5)
        logger.info("  RADS onset day of year (0 = 1 Jan), most frequent: " +
                    ", ".join(f"{int(k)} ({v:.0%})" for k, v in top.items()))
        n_on = np.isfinite(doy).sum(0)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            sd = np.nanstd(doy, 0)
        frozen = (n_on >= 5) & (sd < 1)
        diag["frozen_onset_cells"] = int(frozen.sum())
        diag["cells_with_5_seasons"] = int((n_on >= 5).sum())
        logger.info(f"  RADS cells whose onset day never changes (sd < 1 d over >= 5 seasons): "
                    f"{frozen.sum():,} of {(n_on >= 5).sum():,}")
        if frozen.sum() > 0.05 * max(1, (n_on >= 5).sum()):
            logger.warning("  many RADS onsets fall on the same day every year - check the files; sowing dates "
                           "relative to onset are meaningless in those cells")
        diag["onset_sd_days"] = np.where(n_on >= 5, sd, np.nan).reshape(len(lat), len(lon)).astype(np.float32)
    return years, onset, demise, infos, diag


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ci_nga")
    ap.add_argument("--bbox", nargs=4, type=float)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    name, bbox = C.parse_region(a.region, a.bbox)
    C.setup_logging()
    cm = C.read_json(C.data_dir("chirps", name, "meta.json"))
    years, on, de, infos, diag = load_rads(np.array(cm["lon"]), np.array(cm["lat"]), a.workers)
    print(infos.to_string(index=False))
    ln = (de.astype(np.int64) - on + 1)[(on != SENT) & (de != SENT)]
    print(f"seasons paired: {len(ln):,}; length median {np.median(ln):.0f} d (p10 {np.percentile(ln, 10):.0f}, "
          f"p90 {np.percentile(ln, 90):.0f})")


if __name__ == "__main__":
    main()
