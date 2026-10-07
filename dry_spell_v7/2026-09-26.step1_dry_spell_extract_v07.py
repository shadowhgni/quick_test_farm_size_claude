#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v7 STEP 1 - CHIRPS daily -> fixed grid -> every dry spell (replaces step1 + step1.2)
====================================================================================

What it does
------------
1. Builds ONE regular 0.05 deg grid for the region and MOSAICS every per-country
   CHIRPS NetCDF (chirps_data_cache/chirps_ISO_1981_2025.nc) that intersects it.
   Each cell is processed once, whatever the number of country boxes covering it
   (no "first country wins", no country list that can forget MRT/SSD).
2. Writes the mosaic into a disk cache (uint16, 0.01 mm, exact for the 1 mm
   threshold; 65535 = no data). No-data (-9999, _FillValue, negatives) is masked;
   it is NEVER turned into 0 mm. Only valid values are written, so an overlapping
   file can never overwrite real data with no-data.
3. For every cell, on the continuous 1981-2025 series (no cut at 31 Dec):
     - all spells of >= STEP1_MIN_SPELL days with rain < 1 mm  (missing days break spells)
     - missing-day count, mean annual rain,
     - bimodality ratio A2/A1 of the mean annual cycle (Liebmann et al. 2012).
   NO length filter (the old ">60 days" filter removed spells overlapping the season).

Outputs  (dryspell_v7/<region>/step1/)
-------
  spells/part_rXXXXX.parquet  row, col, lat, lon, start, end (day index, inclusive),
                              start_date, end_date, length, censored
  grid_meta.nc                lat, lon, valid, n_missing, mean_annual_mm, bimodal_ratio
  day_has_data.npy            bool per day index
  step1_meta.json             grid, time axis, sources, chunks
  diagnostics/*.tif|png

Usage (JupyterLab terminal on the HPC, from DCP_climate_characterization/)
-----
  python 2026-09-26.step1_dry_spell_extract_v07.py --inspect           # check inputs first
  python 2026-09-26.step1_dry_spell_extract_v07.py --region study --workers 80
  python 2026-09-26.step1_dry_spell_extract_v07.py --region ssa   --workers 80
  python 2026-09-26.step1_dry_spell_extract_v07.py --bbox -18 2 38.7 23.5 --region mybox
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

NODATA_U16 = 65535
SCALE = 100.0          # stored value = floor(mm * 100)

# set in main() before forking
_G = {}


# =============================================================================
# INSPECTION
# =============================================================================

def inspect_inputs(bbox):
    files = C.find_chirps_country_files(bbox)
    logger.info(f"CHIRPS country files intersecting bbox {bbox}: {len(files)}")
    for r in files:
        logger.info(f"  {r['iso3']}  lon {r['lon_min']:8.3f}..{r['lon_max']:8.3f}  "
                    f"lat {r['lat_min']:7.3f}..{r['lat_max']:7.3f}  days {r['n_time']}  {r['path'].name}")
    if files:
        p = min(files, key=lambda r: r["path"].stat().st_size)["path"]
        with xr.open_dataset(p) as ds:
            logger.info(f"\n--- CHIRPS country sample {p}\n{ds}")
            v = _chirps_var(ds)
            logger.info(f"  data var: {v}  attrs: {dict(ds[v].attrs)}")
            logger.info(f"  encoding _FillValue={ds[v].encoding.get('_FillValue')} "
                        f"missing_value={ds[v].encoding.get('missing_value')} dtype={ds[v].encoding.get('dtype')}")
            latn, lonn = C.spatial_names(ds[v])
            logger.info(f"  lat first/last: {ds[latn].values[[0, -1]]}  lon first/last: {ds[lonn].values[[0, -1]]}")
            tname = next(d for d in ds[v].dims if d.lower() == "time")
            logger.info(f"  time: {ds[tname].values[0]} .. {ds[tname].values[-1]}  (n={ds.sizes[tname]})")
            a = ds[v].isel({tname: slice(0, 31)}).values
            logger.info(f"  first 31 days: NaN={np.isnan(a).mean():.3f}  (<0)={np.mean(a < 0):.3f}  "
                        f"min={np.nanmin(a)}  max={np.nanmax(a)}")
    try:
        rads, d = C.find_rads_files()
    except FileNotFoundError as e:
        logger.warning(str(e))
        return
    if not rads:
        logger.warning(f"RADS files found in {d} but no year in their names")
        return
    y = min(rads)
    with xr.open_dataset(rads[y]) as ds:
        logger.info(f"\n--- RADS sample {rads[y]}\n{ds}")
        for v in ds.data_vars:
            logger.info(f"  {v}: dims={ds[v].dims} dtype={ds[v].dtype}")


# =============================================================================
# GRID + CACHE
# =============================================================================

def _chirps_var(ds):
    for v in ds.data_vars:
        dims = [d.lower() for d in ds[v].dims]
        if "time" in dims and len(dims) == 3:
            return v
    raise KeyError(f"no (time, lat, lon) variable in {list(ds.data_vars)}")


def build_grid(files, bbox):
    """
    Regular ascending pixel-centre lon/lat vectors (rounded to 1e-4) covering
    bbox  intersect  union(country file extents), aligned on the CHIRPS grid.
    """
    with xr.open_dataset(files[0]["path"]) as ds:
        latn, lonn = C.spatial_names(ds)
        rlon = np.sort(ds[lonn].values.astype(np.float64))
        rlat = np.sort(ds[latn].values.astype(np.float64))
    step = C.regular_step(rlon)
    if not np.isclose(abs(C.regular_step(rlat)), step, rtol=1e-3):
        raise ValueError("non-square CHIRPS pixels")

    def axis(ref, lo, hi):
        k0 = np.ceil((lo - ref[0]) / step - 1e-6)
        k1 = np.floor((hi - ref[0]) / step + 1e-6)
        return np.round(ref[0] + np.arange(k0, k1 + 1) * step, 4)

    lo_lon = max(bbox[0], min(r["lon_min"] for r in files))
    hi_lon = min(bbox[2], max(r["lon_max"] for r in files))
    lo_lat = max(bbox[1], min(r["lat_min"] for r in files))
    hi_lat = min(bbox[3], max(r["lat_max"] for r in files))
    lon, lat = axis(rlon, lo_lon, hi_lon), axis(rlat, lo_lat, hi_lat)
    C.regular_step(lon)
    C.regular_step(lat)
    return lon, lat


def _encode(vals):
    """float mm (NaN = missing) -> uint16 floor(mm*100); exact for 'x < 1 mm'."""
    v = np.asarray(vals, dtype=np.float32)
    bad = ~np.isfinite(v) | (v < 0) | (v > 2000)
    out = np.floor(np.clip(np.where(bad, 0, v), 0, 655.34) * SCALE).astype(np.uint16)
    out[bad] = NODATA_U16
    return out


def _axis_map(src, grid, tol):
    """
    Map a file coordinate vector onto the grid.
    Returns (file_slice, grid_start, grid_stop, flip) for the contiguous overlap, or None.
    """
    gi = C.nearest_index(grid, np.asarray(src, dtype=np.float64), tol)
    inside = np.where(gi >= 0)[0]
    if len(inside) == 0:
        return None
    f0, f1 = inside.min(), inside.max()
    g = gi[f0:f1 + 1]
    flip = len(g) > 1 and g[0] > g[-1]
    gs = g[::-1] if flip else g
    if not np.array_equal(gs, np.arange(gs[0], gs[0] + len(gs))):
        raise ValueError("file coordinates are not on the CHIRPS grid (gaps / misalignment)")
    return slice(f0, f1 + 1), int(gs[0]), int(gs[-1]) + 1, flip


def _cache_file(args):
    """Worker: mosaic one per-country NetCDF into the memmap (valid values only)."""
    rec, cache_path, shape, lon, lat, t_chunk = args
    tol = 0.3 * C.regular_step(lon)
    mm = np.memmap(cache_path, dtype=np.uint16, mode="r+", shape=shape)
    written, n_valid_cells = set(), 0
    with xr.open_dataset(rec["path"]) as ds:
        v = _chirps_var(ds)
        da = ds[v]
        latn, lonn = C.spatial_names(da)
        tname = next(d for d in da.dims if d.lower() == "time")
        da = da.transpose(tname, latn, lonn)
        my = _axis_map(ds[latn].values, lat, tol)
        mx = _axis_map(ds[lonn].values, lon, tol)
        if my is None or mx is None:
            return rec["iso3"], [], 0
        (fy, gy0, gy1, flipy), (fx, gx0, gx1, flipx) = my, mx
        tidx = C.day_index(ds[tname].values.astype("datetime64[D]"))
        seen = np.zeros((gy1 - gy0, gx1 - gx0), dtype=bool)
        for t0 in range(0, len(tidx), t_chunk):
            tt = tidx[t0:t0 + t_chunk]
            data = da.isel({tname: slice(t0, t0 + len(tt)), latn: fy, lonn: fx}).values
            if flipy:
                data = data[:, ::-1, :]
            if flipx:
                data = data[:, :, ::-1]
            enc = _encode(data)
            del data
            ok_t = (tt >= 0) & (tt < shape[0])
            enc, tt = enc[ok_t], tt[ok_t]
            if len(tt) == 0:
                continue
            m = enc != NODATA_U16
            seen |= m.any(0)
            if np.all(np.diff(tt) == 1):
                view = mm[tt[0]:tt[-1] + 1, gy0:gy1, gx0:gx1]
                view[m] = enc[m]                       # element-wise: never writes no-data
            else:
                for k, t in enumerate(tt):
                    view = mm[t, gy0:gy1, gx0:gx1]
                    view[m[k]] = enc[k][m[k]]
            written.update(tt[m.reshape(len(tt), -1).any(1)].tolist())
        n_valid_cells = int(seen.sum())
    mm.flush()
    del mm
    return rec["iso3"], sorted(written), n_valid_cells


def build_cache(files, lon, lat, cache_dir, n_io, rebuild=False, t_chunk=366):
    cache_dir.mkdir(parents=True, exist_ok=True)
    n_days = int((np.datetime64(f"{C.DATA_YEAR_MAX}-12-31") - C.ORIGIN).astype(int)) + 1
    shape = (n_days, len(lat), len(lon))
    cache_path = cache_dir / "rain_u16.dat"
    info_path = cache_dir / "cache_info.json"
    info = C.read_json(info_path) if info_path.exists() else None
    same_grid = (info is not None and info["shape"] == list(shape)
                 and np.isclose(info["lon0"], lon[0]) and np.isclose(info["lat0"], lat[0]))
    if rebuild or not same_grid or not cache_path.exists():
        logger.info(f"Creating cache {cache_path} shape={shape} "
                    f"({np.prod(shape) * 2 / 1e9:.1f} GB)")
        mm = np.memmap(cache_path, dtype=np.uint16, mode="w+", shape=shape)
        for t0 in range(0, n_days, 366):
            mm[t0:t0 + 366] = NODATA_U16
        mm.flush()
        del mm
        info = {"shape": list(shape), "lon0": float(lon[0]), "lat0": float(lat[0]), "done": {}}
        C.write_json(info_path, info)
    todo = [r for r in files if r["path"].name not in info["done"]]
    logger.info(f"Cache: {len(info['done'])} country files already mosaicked, {len(todo)} to read")
    if todo:
        # biggest files first so the pool stays busy
        todo = sorted(todo, key=lambda r: -r["path"].stat().st_size)
        args = [(r, str(cache_path), shape, lon, lat, t_chunk) for r in todo]
        with ProcessPoolExecutor(max_workers=min(n_io, len(args)),
                                 mp_context=mp.get_context("fork")) as pool:
            futs = {pool.submit(_cache_file, a): a[0] for a in args}
            for f in as_completed(futs):
                r = futs[f]
                try:
                    iso3, written, ncell = f.result()
                    info["done"][r["path"].name] = written
                    C.write_json(info_path, info)
                    logger.info(f"  mosaicked {iso3}: {ncell:,} cells with data, {len(written):,} days")
                except Exception as e:
                    logger.error(f"  FAILED {r['path'].name}: {e}")
    has = np.zeros(n_days, dtype=bool)
    for w in info["done"].values():
        if len(w):
            has[np.asarray(w, dtype=int)] = True
    return cache_path, shape, has


# =============================================================================
# PER-CHUNK PROCESSING
# =============================================================================

def doy_index(n_days):
    d = C.index_to_date(np.arange(n_days))
    doy = (d - d.astype("datetime64[Y]")).astype(int)       # 0..365
    return np.minimum(doy, 364)                               # 31 Dec of leap years -> 364


def harmonic_ratio(clim):
    """clim: (365, ncell). Returns A1, A2, A2/A1."""
    F = np.fft.rfft(clim, axis=0)
    a1 = 2 * np.abs(F[1]) / clim.shape[0]
    a2 = 2 * np.abs(F[2]) / clim.shape[0]
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(a1 > 0, a2 / a1, np.nan)
    return a1, a2, ratio


def extract_runs(dry, min_len):
    """
    dry: (ncell, T) bool. Returns cell, start, end_inclusive, length (numpy int arrays)
    for every run of True of length >= min_len. Vectorised, spells never cross cells.
    """
    ncell, T = dry.shape
    pad = np.zeros((ncell, T + 2), dtype=np.int8)
    pad[:, 1:-1] = dry
    d = np.diff(pad, axis=1)
    sc, st = np.nonzero(d == 1)          # sorted by cell, then time
    ec, et = np.nonzero(d == -1)         # et = first wet day (exclusive end)
    assert len(sc) == len(ec) and np.array_equal(sc, ec)
    length = et - st
    k = length >= min_len
    return sc[k], st[k], et[k] - 1, length[k]


def process_rows(r0, r1):
    """Worker: rows [r0, r1) of the grid."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    g = _G
    mm = np.memmap(g["cache_path"], dtype=np.uint16, mode="r", shape=g["shape"])
    block = np.asarray(mm[:, r0:r1, :])                     # (T, nr, nlon)
    del mm
    T, nr, nlon = block.shape
    block = block.reshape(T, nr * nlon)
    has = g["has"]

    miss = block == NODATA_U16
    n_data_days = int(has.sum())
    n_missing = (miss & has[:, None]).sum(0)
    valid = n_missing < n_data_days                                   # some data at all
    valid_q = valid & (n_missing <= C.MAX_MISSING_FRAC * n_data_days)

    # climatology on days with data
    doy = g["doy"]
    clim = np.full((365, block.shape[1]), np.nan, dtype=np.float32)
    for k in range(365):
        sel = (doy == k) & has
        if not sel.any():
            continue
        b = block[sel]
        m = b != NODATA_U16
        s = np.where(m, b, 0).sum(0, dtype=np.float64) / SCALE
        n = m.sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            clim[k] = np.where(n > 0, s / n, np.nan)
    mean_annual = np.nanmean(clim, axis=0) * 365.25
    clim_f = np.where(np.isfinite(clim), clim, np.nanmean(clim, axis=0, keepdims=True))
    a1, a2, ratio = harmonic_ratio(np.nan_to_num(clim_f))
    ratio[~valid] = np.nan

    thr = int(round(C.DRY_MM * SCALE))
    dry = (block < thr) & ~miss                                         # NaN is never dry
    dry[:, ~valid] = False
    dry_t = np.ascontiguousarray(dry.T)
    del dry
    cell, st, en, ln = extract_runs(dry_t, C.STEP1_MIN_SPELL)
    del dry_t

    # censoring: spell touches the series edge, a missing day or a day without data
    miss_or_nodata = (miss | ~has[:, None])
    before = np.where(st > 0, miss_or_nodata[np.maximum(st - 1, 0), cell], True)
    after = np.where(en < T - 1, miss_or_nodata[np.minimum(en + 1, T - 1), cell], True)
    censored = before | after
    del block, miss, miss_or_nodata

    lr, lc = np.divmod(cell, nlon)
    rows = (lr + r0).astype(np.int16)
    cols = lc.astype(np.int16)
    epoch = int((C.ORIGIN - np.datetime64("1970-01-01", "D")).astype(int))
    tbl = pa.table({
        "row": rows, "col": cols,
        "lat": g["lat"][rows].astype(np.float32), "lon": g["lon"][cols].astype(np.float32),
        "start": st.astype(np.int32), "end": en.astype(np.int32),
        "start_date": pa.array((st + epoch).astype(np.int32), type=pa.date32()),
        "end_date": pa.array((en + epoch).astype(np.int32), type=pa.date32()),
        "length": ln.astype(np.int32), "censored": censored,
    })
    out = Path(g["spell_dir"]) / f"part_r{r0:05d}.parquet"
    pq.write_table(tbl, out, compression="zstd", row_group_size=1_000_000)

    n_sp = np.bincount(cell, minlength=nr * nlon)
    res = dict(valid=valid, valid_q=valid_q, n_missing=n_missing, mean_annual=mean_annual,
               a1=a1, a2=a2, ratio=ratio, n_spells=n_sp)
    res = {k: v.reshape(nr, nlon) for k, v in res.items()}
    gc.collect()
    return r0, r1, res, len(st)


# =============================================================================
# MAIN
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="study", help=f"one of {list(C.REGIONS)} or a name for --bbox")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX"))
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 4))
    ap.add_argument("--io_workers", type=int, default=12, help="country files read in parallel while building the cache")
    ap.add_argument("--rows_per_task", type=int, default=C.ROWS_PER_TASK)
    ap.add_argument("--rebuild_cache", action="store_true")
    ap.add_argument("--inspect", action="store_true", help="print input structure and exit")
    a = ap.parse_args()

    name, bbox = C.parse_region(a.region, a.bbox)
    out = C.region_dir(name) / "step1"
    C.setup_logging(out / "step1.log")
    if a.inspect:
        inspect_inputs(bbox)
        return

    t0 = time.time()
    logger.info("=" * 70)
    logger.info(f"v7 STEP1  region={name} bbox={bbox}  workers={a.workers}")
    logger.info("=" * 70)

    files = C.find_chirps_country_files(bbox)
    if not files:
        sys.exit(f"No chirps_ISO_YYYY_YYYY.nc intersecting {bbox} in {C.CHIRPS_COUNTRY_DIR}")
    logger.info(f"CHIRPS country files intersecting the region ({len(files)}): "
                f"{' '.join(r['iso3'] for r in files)}")

    lon, lat = build_grid(files, bbox)
    logger.info(f"Grid: {len(lon)} lon x {len(lat)} lat, step {C.regular_step(lon):.4f} deg, "
                f"lon {lon[0]}..{lon[-1]}, lat {lat[0]}..{lat[-1]}")

    cache_path, shape, has = build_cache(files, lon, lat, C.region_dir(name) / "cache",
                                         a.io_workers, a.rebuild_cache)
    if not has.any():
        sys.exit("Cache is empty - all country files failed (see errors above)")
    last_day = C.index_to_date(np.where(has)[0].max())
    logger.info(f"Days with data: {has.sum():,} / {len(has):,}  (last day with data: {last_day})")

    spell_dir = out / "spells"
    spell_dir.mkdir(parents=True, exist_ok=True)
    for f in spell_dir.glob("part_*.parquet"):
        f.unlink()

    _G.update(cache_path=str(cache_path), shape=shape, has=has, doy=doy_index(shape[0]),
              lat=lat, lon=lon, spell_dir=str(spell_dir))

    nlat, nlon = len(lat), len(lon)
    grids = {k: np.full((nlat, nlon), np.nan, dtype=np.float32)
             for k in ("valid", "valid_q", "n_missing", "mean_annual", "a1", "a2", "ratio", "n_spells")}
    chunks = [(r, min(r + a.rows_per_task, nlat)) for r in range(0, nlat, a.rows_per_task)]
    logger.info(f"Extracting spells: {len(chunks)} row chunks")
    n_total = 0
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(process_rows, r0, r1) for r0, r1 in chunks]
        for i, f in enumerate(as_completed(futs), 1):
            r0, r1, res, n = f.result()
            for k, v in res.items():
                grids[k][r0:r1] = v
            n_total += n
            if i % 20 == 0 or i == len(chunks):
                logger.info(f"  {i}/{len(chunks)} chunks, {n_total:,} spells")

    valid = grids["valid"].astype(bool)
    valid_q = grids["valid_q"].astype(bool)
    reason = np.full((nlat, nlon), C.REASON_OK, dtype=np.uint8)
    reason[~valid_q] = C.REASON_MISSING
    reason[~valid] = C.REASON_NO_CHIRPS
    bimodal = (grids["ratio"] >= C.BIMODAL_RATIO) & valid

    ds = xr.Dataset(
        {
            "valid": (("lat", "lon"), valid_q.astype(np.int8)),
            "reason": (("lat", "lon"), reason),
            "n_missing": (("lat", "lon"), grids["n_missing"].astype(np.int32)),
            "mean_annual_mm": (("lat", "lon"), grids["mean_annual"]),
            "harm_a1": (("lat", "lon"), grids["a1"]),
            "harm_a2": (("lat", "lon"), grids["a2"]),
            "bimodal_ratio": (("lat", "lon"), grids["ratio"]),
            "bimodal": (("lat", "lon"), bimodal.astype(np.int8)),
            "n_spells_ge5": (("lat", "lon"), grids["n_spells"]),
        },
        coords={"lat": lat, "lon": lon},
        attrs={"region": name, "bbox": list(bbox), "origin": str(C.ORIGIN),
               "dry_mm": C.DRY_MM, "min_spell_days": C.STEP1_MIN_SPELL,
               "bimodal_ratio_threshold": C.BIMODAL_RATIO,
               "note": "bimodal_ratio = A2/A1 of mean annual cycle (Liebmann et al. 2012)"},
    )
    ds.to_netcdf(out / "grid_meta.nc")
    np.save(out / "day_has_data.npy", has)
    C.write_json(out / "step1_meta.json", {
        "region": name, "bbox": bbox, "n_lon": nlon, "n_lat": nlat,
        "lon0": float(lon[0]), "lat0": float(lat[0]), "step": C.regular_step(lon),
        "origin": str(C.ORIGIN), "n_days": shape[0], "last_day_with_data": str(last_day),
        "chunks": chunks, "cache": str(cache_path), "n_spells": n_total,
        "sources": [str(r["path"]) for r in files],
    })

    # diagnostics
    dg = out / "diagnostics"
    bnd = C.load_boundaries(bbox)
    for var, title, cmap, lab in [
        ("mean_annual_mm", "Mean annual rainfall (CHIRPS)", "Blues", "mm/yr"),
        ("bimodal_ratio", f"Bimodality ratio A2/A1 (bimodal if >= {C.BIMODAL_RATIO})", "Purples", "A2/A1"),
        ("n_missing", "Missing rainfall days per cell", "Reds", "days"),
    ]:
        arr = ds[var].values.astype(np.float32)
        arr[~valid] = np.nan
        C.save_geotiff(dg / f"{var}.tif", arr, lon, lat)
        vmax = 2.0 if var == "bimodal_ratio" else None
        C.plot_map(dg / f"{var}.png", arr, lon, lat, title, lab, cmap=cmap, vmax=vmax, boundaries=bnd)
    C.save_geotiff(dg / "reason_step1.tif", reason, lon, lat, nodata=255, dtype="uint8")
    cov = np.where(valid_q, 1.0, np.nan)
    C.plot_map(dg / "chirps_coverage.png", cov, lon, lat,
               "CHIRPS coverage after mosaicking country files (blue = data)", "", cmap="Blues",
               vmin=0, vmax=1.5, boundaries=bnd)
    if bnd is not None and len(bnd):
        from rasterio.features import geometry_mask
        land = geometry_mask(bnd.geometry, out_shape=(nlat, nlon), transform=C.grid_transform(lon, lat),
                             invert=True)[::-1]
        gap = land & ~valid_q
        logger.info(f"land pixels (inside country polygons) WITHOUT usable CHIRPS: {gap.sum():,} "
                    f"of {land.sum():,}  -> see diagnostics/chirps_coverage.png")

    logger.info(f"valid cells: {valid_q.sum():,}  no data: {(~valid).sum():,}  "
                f"too many missing: {(valid & ~valid_q).sum():,}  bimodal: {bimodal.sum():,}")
    logger.info(f"spells >= {C.STEP1_MIN_SPELL} d: {n_total:,}")
    logger.info(f"STEP1 done in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()
