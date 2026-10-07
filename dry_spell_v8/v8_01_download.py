#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v8 STEP 1 - download the inputs (resumable)
===========================================

1. CHIRPS v2.0 daily, 0.05 deg, 1981-2025, for the region bbox. Each day is read from the
   CHC Cloud-Optimized GeoTIFF (only the tiles covering the region, HTTP range requests) and
   written straight into a disk cache:
       dryspell_v8_data/chirps/<region>/rain_u16.dat   uint16, floor(mm * 100), 65535 = no data
       dryspell_v8_data/chirps/<region>/day_done.npy   bool per day (resume)
       dryspell_v8_data/chirps/<region>/meta.json      grid (ascending lat/lon centres), days
   Negative values (-9999, sea) and unreadable days are no data, never 0 mm.
2. Natural Earth 1:50m countries  -> dryspell_v8_data/boundaries/ne_50m_admin_0_countries.gpkg
3. HarvestChoice AEZ Africa (Sebastian 2009, CC BY-NC 3.0) -> dryspell_v8_data/aez/afr_aez09.tif
   (the published ASCII grid is damaged: wrapped rows, 275 values short and binary garbage
   at 3.5-3.8 N; it is parsed tolerantly and everything after the damage is no data).

Re-running continues where it stopped; --retry_missing tries the failed days again.

Usage
-----
  python v8_01_download.py --region ci_nga --threads 32
  python v8_01_download.py --region ssa --threads 48
"""

import os
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".cog")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "5")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "60")

import argparse
import logging
import re
import shutil
import sys
import threading
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v8_common as C

logger = logging.getLogger("dryspell_v8")
NODATA = 65535
SCALE = 100.0


# =============================================================================
# CHIRPS
# =============================================================================

def cog_url(day):
    return "/vsicurl/" + C.CHIRPS_COG_URL.format(y=day.year, m=day.month, d=day.day)


def chirps_grid(bbox):
    """Window of the global CHIRPS grid covering bbox -> (window, ascending lon, ascending lat)."""
    import rasterio
    from rasterio.windows import from_bounds
    d0 = pd.Timestamp(f"{C.DATA_YEAR_MIN}-01-01")
    with rasterio.open(cog_url(d0)) as src:
        win = from_bounds(*bbox, transform=src.transform).round_offsets().round_lengths()
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        tr = src.window_transform(win)
        logger.info(f"CHIRPS COG {src.width}x{src.height} res {src.res[0]:.6f} -> window {win}")
    nx, ny = int(win.width), int(win.height)
    lon = np.round(tr.c + (np.arange(nx) + 0.5) * tr.a, 4)
    lat_desc = np.round(tr.f + (np.arange(ny) + 0.5) * tr.e, 4)
    return win, lon, lat_desc[::-1]


def encode(a):
    a = np.asarray(a, dtype=np.float32)
    bad = ~np.isfinite(a) | (a < 0) | (a > 2000)
    out = np.floor(np.clip(np.where(bad, 0, a), 0, 655.34) * SCALE).astype(np.uint16)
    out[bad] = NODATA
    return out


def download_chirps(region, bbox, threads, retry_missing=False):
    import rasterio
    out = C.data_dir("chirps", region)
    out.mkdir(parents=True, exist_ok=True)
    meta_f, done_f, dat_f = out / "meta.json", out / "day_done.npy", out / "rain_u16.dat"
    days = pd.date_range(f"{C.DATA_YEAR_MIN}-01-01", f"{C.DATA_YEAR_MAX}-12-31", freq="D")
    if meta_f.exists():
        meta = C.read_json(meta_f)
        if list(meta["bbox"]) != list(bbox):
            sys.exit(f"{out} was built for bbox {meta['bbox']}, not {list(bbox)} - use another region name")
        lon, lat = np.array(meta["lon"]), np.array(meta["lat"])
        win = rasterio.windows.Window(*meta["window"])
    else:
        win, lon, lat = chirps_grid(bbox)
        meta = {"bbox": list(bbox), "lon": lon.tolist(), "lat": lat.tolist(), "n_days": len(days),
                "origin": str(C.ORIGIN), "window": [int(win.col_off), int(win.row_off), int(win.width),
                                                   int(win.height)],
                "source": C.CHIRPS_COG_URL, "nodata": NODATA, "scale": SCALE, "failed_days": []}
    shape = (len(days), len(lat), len(lon))
    if not dat_f.exists():
        logger.info(f"creating {dat_f} {shape} ({np.prod(shape) * 2 / 1e9:.1f} GB)")
        mm = np.memmap(dat_f, dtype=np.uint16, mode="w+", shape=shape)
        for t0 in range(0, shape[0], 366):
            mm[t0:t0 + 366] = NODATA
        mm.flush()
        del mm
    done = np.load(done_f) if done_f.exists() else np.zeros(len(days), bool)
    failed = set(meta.get("failed_days", []))
    todo = [i for i in range(len(days)) if not done[i] and (retry_missing or str(days[i].date()) not in failed)]
    logger.info(f"CHIRPS {region}: {done.sum():,} days cached, {len(todo):,} to download, "
                f"{len(failed)} known failures")
    C.write_json(meta_f, meta)
    if not todo:
        return
    mm = np.memmap(dat_f, dtype=np.uint16, mode="r+", shape=shape)
    lock = threading.Lock()
    t0 = time.time()

    def one(i):
        day = days[i]
        err = None
        for attempt in range(4):
            try:
                with rasterio.open(cog_url(day)) as src:
                    a = src.read(1, window=win)
                if a.shape != shape[1:]:
                    raise ValueError(f"window {a.shape} != {shape[1:]}")
                mm[i] = encode(a)[::-1]                    # north-up -> ascending latitude
                return i, None
            except Exception as e:                         # noqa: BLE001 - retried, then recorded
                err = e
                time.sleep(2 * (attempt + 1))
        return i, str(err)

    n_new = 0
    with ThreadPoolExecutor(threads) as pool:
        futs = [pool.submit(one, i) for i in todo]
        for k, f in enumerate(as_completed(futs), 1):
            i, err = f.result()
            with lock:
                if err is None:
                    done[i] = True
                    n_new += 1
                    failed.discard(str(days[i].date()))
                else:
                    failed.add(str(days[i].date()))
                    logger.warning(f"  {days[i].date()}: {err}")
                if k % 500 == 0 or k == len(todo):
                    mm.flush()
                    np.save(done_f, done)
                    meta["failed_days"] = sorted(failed)
                    C.write_json(meta_f, meta)
                    el = time.time() - t0
                    logger.info(f"  {k:,}/{len(todo):,} days ({el / 60:.1f} min, {k / el:.1f} days/s)")
    mm.flush()
    np.save(done_f, done)
    meta["failed_days"] = sorted(failed)
    C.write_json(meta_f, meta)
    logger.info(f"CHIRPS {region}: {done.sum():,}/{len(days):,} days cached ({n_new:,} new); "
                f"failed {len(failed)}: {sorted(failed)[:10]}{' ...' if len(failed) > 10 else ''}")


# =============================================================================
# BOUNDARIES
# =============================================================================

def fetch(url, dst):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (dryspell_v8)"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)


def download_boundaries():
    import geopandas as gpd
    dst = C.boundaries_file()
    if dst.exists():
        logger.info(f"boundaries: {dst} exists")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for url in C.BOUNDARY_URLS:
        tmp = dst.parent / Path(url).name
        try:
            fetch(url, tmp)
            g = gpd.read_file(tmp)
            break
        except Exception as e:                             # noqa: BLE001 - try the next mirror
            last = e
            logger.warning(f"boundaries: {url} failed ({e})")
    else:
        raise RuntimeError(f"no boundary source worked: {last}")
    cols = {c.upper(): c for c in g.columns}
    iso = g[cols["ISO_A3"]].astype(str)
    if "ADM0_A3" in cols:                                  # Natural Earth writes -99 for a few countries
        iso = np.where(iso == "-99", g[cols["ADM0_A3"]].astype(str), iso)
    g = gpd.GeoDataFrame({"iso_a3": iso, "name": g[cols.get("NAME", cols["ISO_A3"])].astype(str)},
                         geometry=g.geometry, crs=g.crs).to_crs("EPSG:4326")
    g.to_file(dst, driver="GPKG")
    tmp.unlink(missing_ok=True)
    logger.info(f"boundaries: {len(g)} countries -> {dst}")


# =============================================================================
# AEZ
# =============================================================================

def read_ascii_grid(raw):
    """Tolerant ESRI ASCII grid reader -> (array, transform, nodata)."""
    from rasterio.transform import from_origin
    lines = raw.split(b"\n", 6)
    hdr = {}
    for ln in lines[:6]:
        k, v = ln.split()[:2]
        hdr[k.decode().lower()] = float(v)
    nc, nr, cs = int(hdr["ncols"]), int(hdr["nrows"]), hdr["cellsize"]
    x0 = hdr.get("xllcorner", hdr.get("xllcenter", 0) - cs / 2)
    y0 = hdr.get("yllcorner", hdr.get("yllcenter", 0) - cs / 2)
    nod = int(hdr.get("nodata_value", -9999))
    body = lines[6]
    bad = re.search(rb"[^0-9eE+\-.\s]", body)
    if bad:
        cut = max(body.rfind(b" ", 0, bad.start()), body.rfind(b"\n", 0, bad.start()))
        body = body[:max(cut, 0)]
    vals = np.fromstring(body.decode("ascii"), dtype=np.int32, sep=" ")    # any whitespace separates
    n = nr * nc
    if bad:
        logger.warning(f"AEZ grid corrupted from row {vals.size // nc} (lat ~{y0 + (nr - vals.size // nc) * cs:.2f}); "
                       f"the rest is no data")
    elif vals.size != n:
        logger.warning(f"AEZ grid holds {vals.size:,} values, header says {n:,}")
    vals = np.r_[vals, np.full(max(0, n - vals.size), nod, np.int32)][:n]
    return vals.reshape(nr, nc), from_origin(x0, y0 + nr * cs, cs, cs), nod


def download_aez():
    import rasterio
    dst = C.data_dir("aez", "afr_aez09.tif")
    if dst.exists():
        logger.info(f"AEZ: {dst} exists")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    z = dst.parent / "003_afr-aez_09.zip"
    if not z.exists():
        fetch(C.AEZ_URL, z)
    with zipfile.ZipFile(z) as zz:
        name = next(n for n in zz.namelist() if n.lower().endswith(".asc"))
        a, tr, nod = read_ascii_grid(zz.read(name))
    a = np.where((a == nod) | (a <= 0), -1, a).astype(np.int16)
    with rasterio.open(dst, "w", driver="GTiff", height=a.shape[0], width=a.shape[1], count=1, dtype="int16",
                       crs="EPSG:4326", transform=tr, nodata=-1, compress="deflate", tiled=True) as d:
        d.write(a, 1)
    logger.info(f"AEZ: {dst} ({a.shape[1]}x{a.shape[0]}, classes {sorted(set(np.unique(a)) - {-1})})")


# =============================================================================
# MAIN
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ci_nga", help=f"one of {list(C.REGIONS)} or a name for --bbox")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX"))
    ap.add_argument("--threads", type=int, default=32)
    ap.add_argument("--retry_missing", action="store_true", help="try the days that failed before again")
    ap.add_argument("--only", nargs="+", choices=["chirps", "boundaries", "aez"], default=["chirps", "boundaries", "aez"])
    a = ap.parse_args()
    name, bbox = C.parse_region(a.region, a.bbox)
    C.setup_logging(C.data_dir("download_" + name + ".log"))
    if "boundaries" in a.only:
        download_boundaries()
    if "aez" in a.only:
        try:
            download_aez()
        except Exception as e:                             # noqa: BLE001 - AEZ is optional
            logger.warning(f"AEZ download failed ({e}) - step 3 will use the rainfall-band proxy")
    if "chirps" in a.only:
        download_chirps(name, bbox, a.threads, a.retry_missing)


if __name__ == "__main__":
    main()
