#!/usr/bin/env python3
"""
Download REAL CHIRPS v2.0 daily rainfall for a bounding box and write it in the same
layout as the HPC per-country files (chirps_<ISO3>_<Y0>_<Y1>.nc: dims time, latitude
(descending), longitude; variable 'rainfall'; -9999 kept where CHIRPS has no data).

Source: Cloud-Optimized GeoTIFFs at
  https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/cogs/p05/YYYY/chirps-v2.0.YYYY.MM.DD.cog
Only the internal tiles covering the box are fetched (HTTP range requests), not the
~8 MB global file. Days that cannot be read after retries are dropped from the time
axis (as in the HPC files, which also have missing days).

  python fetch_chirps_cog.py --bbox 2.5 4.5 14.5 14.5 --iso3 NGA --y0 1981 --y1 2025 --out chirps_data_cache
"""
import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".cog")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "5")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "60")

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds

URL = "/vsicurl/https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/cogs/p05/{y}/chirps-v2.0.{y}.{m:02d}.{d:02d}.cog"


def read_day(day, window, shape):
    url = URL.format(y=day.year, m=day.month, d=day.day)
    for attempt in range(4):
        try:
            with rasterio.open(url) as src:
                a = src.read(1, window=window, boundless=False).astype(np.float32)
            if a.shape != shape:
                raise ValueError(f"window shape {a.shape} != {shape}")
            return day, a
        except Exception as e:                      # noqa: BLE001 - retry on any I/O error
            err = e
            time.sleep(2 * (attempt + 1))
    print(f"  FAILED {day.date()}: {err}", flush=True)
    return day, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("LON0", "LAT0", "LON1", "LAT1"))
    ap.add_argument("--iso3", required=True)
    ap.add_argument("--y0", type=int, default=1981)
    ap.add_argument("--y1", type=int, default=2025)
    ap.add_argument("--out", default="chirps_data_cache")
    ap.add_argument("--threads", type=int, default=32)
    a = ap.parse_args()

    out = Path(a.out) / f"chirps_{a.iso3}_{a.y0}_{a.y1}.nc"
    if out.exists():
        print(f"{out} exists - skipping download")
        return
    days = pd.date_range(f"{a.y0}-01-01", f"{a.y1}-12-31", freq="D")
    d0 = days[0]
    with rasterio.open(URL.format(y=d0.year, m=d0.month, d=d0.day)) as src:
        print(f"COG: {src.width}x{src.height} res {src.res} bounds {src.bounds} nodata {src.nodata} "
              f"blocks {src.block_shapes} crs {src.crs}")
        win = from_bounds(*a.bbox, transform=src.transform).round_offsets().round_lengths()
        tr = src.window_transform(win)
    ny, nx = int(win.height), int(win.width)
    lon = np.round(tr.c + (np.arange(nx) + 0.5) * tr.a, 4)
    lat = np.round(tr.f + (np.arange(ny) + 0.5) * tr.e, 4)        # descending
    print(f"window {win} -> {nx} lon x {ny} lat, lon {lon[0]}..{lon[-1]}, lat {lat[0]}..{lat[-1]}")

    tmp = Path(a.out) / f".{out.name}.f32"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    mm = np.lib.format.open_memmap(tmp, mode="w+", dtype=np.float32, shape=(len(days), ny, nx))
    ok = np.zeros(len(days), dtype=bool)
    t0 = time.time()
    with ThreadPoolExecutor(a.threads) as pool:
        futs = {pool.submit(read_day, d, win, (ny, nx)): i for i, d in enumerate(days)}
        for n, f in enumerate(as_completed(futs), 1):
            i = futs[f]
            _, arr = f.result()
            if arr is not None:
                mm[i] = arr
                ok[i] = True
            if n % 1000 == 0 or n == len(days):
                el = time.time() - t0
                print(f"  {n:,}/{len(days):,} days  ({el / 60:.1f} min, {n / el:.1f} days/s)", flush=True)
    mm.flush()
    print(f"days read: {ok.sum():,} / {len(days):,}  (missing {(~ok).sum()})")
    if ok.sum() < 0.95 * len(days):
        sys.exit("too many days failed - aborting")

    idx = np.nonzero(ok)[0]
    samp = np.asarray(mm[idx[:: max(1, len(idx) // 200)]])
    v = samp[samp > -9000]
    print(f"rain stats (200 sampled days, valid px): mean {v.mean():.2f} mm/d, p99 {np.percentile(v, 99):.1f}, "
          f"max {v.max():.1f}, dry(<1mm) {np.mean(v < 1):.2f}; nodata frac {np.mean(samp <= -9000):.3f}")
    import netCDF4
    epoch = np.datetime64("1981-01-01")
    with netCDF4.Dataset(out, "w") as nc:
        nc.createDimension("time", len(idx))
        nc.createDimension("latitude", ny)
        nc.createDimension("longitude", nx)
        tv = nc.createVariable("time", "i4", ("time",))
        tv.units, tv.calendar = "days since 1981-01-01", "standard"
        tv[:] = (days.values[idx].astype("datetime64[D]") - epoch).astype(int)
        la = nc.createVariable("latitude", "f8", ("latitude",))
        la[:] = lat
        la.units = "degrees_north"
        lo = nc.createVariable("longitude", "f8", ("longitude",))
        lo[:] = lon
        lo.units = "degrees_east"
        r = nc.createVariable("rainfall", "f4", ("time", "latitude", "longitude"), zlib=True, complevel=4,
                              chunksizes=(min(366, len(idx)), ny, nx), fill_value=np.float32(np.nan))
        r.units, r.source, r.country_iso3 = "mm", "CHIRPS v2.0 daily p05 COG (data.chc.ucsb.edu)", a.iso3
        for k in range(0, len(idx), 366):
            r[k:k + 366] = np.asarray(mm[idx[k:k + 366]])
    del mm
    tmp.unlink()
    print(f"written {out} ({out.stat().st_size / 1e6:.0f} MB) in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
