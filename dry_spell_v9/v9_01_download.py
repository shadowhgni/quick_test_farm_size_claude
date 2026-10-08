#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9 STEP 1 - download the inputs (resumable; all open data, no login)
====================================================================

1. CHIRPS v2.0 daily, 0.05 deg, for the region: only the region's tiles of each daily COG,
   written into  dryspell_v9_data/chirps/<region>/rain_u16.dat  (uint16 mm*100, 65535 = no data).
2. PKU GIMMS NDVI v1.2 (Zenodo 8253971; the GIMMS NDVI3g record used by Vrieling et al. 2013):
   one zip per decade (~650 MB each) is downloaded (resumable), every half-month GeoTIFF inside
   is cropped to the region and written into  dryspell_v9_data/ndvi/<region>/ndvi_u16.dat
   (NDVI*1000, 65535 = no data / QC snow-cloud); the zip is deleted afterwards (--keep_zips).
3. Natural Earth countries, HarvestChoice AEZ (damaged ASCII grid read tolerantly), and the
   Koppen-Geiger 1991-2020 map + legend (Beck et al. 2023).

Re-running continues where it stopped (--retry_missing retries failed CHIRPS days).

Usage
-----
  python v9_01_download.py --region ci_nga
  python v9_01_download.py --region ssa --threads 48
"""

import os
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".cog")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "5")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "60")

import argparse
import json
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
import v9_common as C

logger = logging.getLogger("dryspell_v9")
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
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (dryspell_v9)"})
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
# NDVI (PKU GIMMS NDVI v1.2)
# =============================================================================

def fetch_resumable(url, dst, tries=6):
    """HTTP download with resume (Range) and retries."""
    dst = Path(dst)
    tmp = dst.with_suffix(dst.suffix + ".part")
    for attempt in range(tries):
        have = tmp.stat().st_size if tmp.exists() else 0
        hdr = {"User-Agent": "Mozilla/5.0 (dryspell_v9)"}
        if have:
            hdr["Range"] = f"bytes={have}-"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=300) as r:
                mode = "ab" if (have and r.status == 206) else "wb"
                with open(tmp, mode) as f:
                    shutil.copyfileobj(r, f, length=8 << 20)
            tmp.rename(dst)
            return dst
        except Exception as e:                             # noqa: BLE001 - resumed on the next attempt
            logger.warning(f"  {url}: {e} (attempt {attempt + 1}/{tries})")
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"download failed: {url}")


def ndvi_index(name):
    """'..._YYYYMMHH.tif' -> (year, month, half)."""
    m = re.search(r"(\d{4})(\d{2})(0[12])\.tif$", name)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def ndvi_zip_url(period):
    """URL of the zip of one period: looked up in the Zenodo record's file list (names checked),
    falling back to NDVI_ZIP_URL."""
    if "list" not in _ZEN:
        try:
            api = f"https://zenodo.org/api/records/{C.NDVI_ZENODO_RECORD}"
            with urllib.request.urlopen(urllib.request.Request(api, headers={"User-Agent": "dryspell_v9"}),
                                        timeout=60) as r:
                files = json.load(r).get("files", [])
            _ZEN["list"] = {f["key"]: f["links"].get("self") or f["links"].get("download") for f in files}
            logger.info(f"NDVI: Zenodo record {C.NDVI_ZENODO_RECORD} lists {len(files)} files: "
                        f"{sorted(_ZEN['list'])}")
        except Exception as e:                             # noqa: BLE001 - fall back to the template
            logger.warning(f"NDVI: Zenodo file list unavailable ({e}) - using NDVI_ZIP_URL")
            _ZEN["list"] = {}
    hits = [k for k in _ZEN["list"] if k.endswith(".zip") and C.NDVI_PRODUCT in k and period in k]
    if len(hits) == 1:
        return _ZEN["list"][hits[0]]
    if _ZEN["list"]:
        logger.warning(f"NDVI: no unique zip for {C.NDVI_PRODUCT} {period} in the record ({hits}) - using NDVI_ZIP_URL")
    return C.NDVI_ZIP_URL.format(rec=C.NDVI_ZENODO_RECORD, prod=C.NDVI_PRODUCT, period=period)


_ZEN = {}


def download_ndvi(region, bbox, keep_zips=False):
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.windows import from_bounds
    out = C.data_dir("ndvi", region)
    out.mkdir(parents=True, exist_ok=True)
    meta_f, done_f, dat_f = out / "meta.json", out / "period_done.npy", out / "ndvi_u16.dat"
    y0, y1 = C.NDVI_YEAR_MIN, C.NDVI_YEAR_MAX
    n_per = (y1 - y0 + 1) * 24
    done = np.load(done_f) if done_f.exists() else np.zeros(n_per, bool)
    meta = C.read_json(meta_f) if meta_f.exists() else None
    if meta and (meta["bbox"] != list(bbox) or meta["years"] != [y0, y1] or meta["product"] != C.NDVI_PRODUCT):
        sys.exit(f"{out} was built with other settings ({meta['bbox']}, {meta['years']}, {meta['product']}) - "
                 f"delete it or use another region name")
    raw = C.data_dir("ndvi", "zips")
    raw.mkdir(parents=True, exist_ok=True)
    mm = None
    for period in C.NDVI_ZIPS[C.NDVI_PRODUCT]:
        pa, pb = (int(x) for x in period.split("_"))
        if pb < y0 or pa > y1:
            continue
        need = [((y - y0) * 24 + k) for y in range(max(pa, y0), min(pb, y1) + 1) for k in range(24)]
        if all(done[i] for i in need):
            continue
        z = raw / f"PKU_GIMMS_NDVI_{C.NDVI_PRODUCT}_{period}.zip"
        if not z.exists():
            url = ndvi_zip_url(period)
            logger.info(f"NDVI: downloading {url}")
            t0 = time.time()
            fetch_resumable(url, z)
            logger.info(f"  {z.name}: {z.stat().st_size / 1e6:.0f} MB in {(time.time() - t0) / 60:.1f} min")
        with zipfile.ZipFile(z) as zz:
            members = sorted(n for n in zz.namelist() if ndvi_index(n))
        if not members:
            with zipfile.ZipFile(z) as zz:
                sys.exit(f"{z.name}: no *_YYYYMMHH.tif inside (first entries {zz.namelist()[:5]}) - adapt ndvi_index()")
        logger.info(f"  {z.name}: {len(members)} half-monthly files, e.g. {members[0]}")
        if meta is None:                                  # grid from the first file
            with rasterio.open(f"/vsizip/{z}/{members[0]}") as src:
                tr = src.transform
                if src.crs is None or tr.is_identity:      # fall back to the documented global grid
                    tr = from_origin(-180.0, 90.0, 1 / 12, 1 / 12)
                    logger.warning("NDVI GeoTIFF without georeference - assuming global 1/12 deg grid from 180W, 90N")
                win = from_bounds(bbox[0] - 0.25, bbox[1] - 0.25, bbox[2] + 0.25, bbox[3] + 0.25,
                                  transform=tr).round_offsets().round_lengths()
                win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
                wt = rasterio.windows.transform(win, tr)
                logger.info(f"NDVI grid {src.width}x{src.height} bands {src.count} dtype {src.dtypes[0]} -> window {win}")
            nx, ny = int(win.width), int(win.height)
            lon = np.round(wt.c + (np.arange(nx) + 0.5) * wt.a, 6)
            lat = np.round(wt.f + (np.arange(ny) + 0.5) * wt.e, 6)[::-1]
            meta = {"bbox": list(bbox), "years": [y0, y1], "product": C.NDVI_PRODUCT, "n_periods": n_per,
                    "lon": lon.tolist(), "lat": lat.tolist(),
                    "window": [int(win.col_off), int(win.row_off), nx, ny],
                    "transform": list(tr)[:6], "scale": C.NDVI_SCALE, "fill": C.NDVI_FILL}
            C.write_json(meta_f, meta)
        shape = (n_per, len(meta["lat"]), len(meta["lon"]))
        if mm is None:
            mm = np.memmap(dat_f, dtype=np.uint16, mode="r+" if dat_f.exists() else "w+", shape=shape)
            if not done.any():
                mm[:] = C.NDVI_FILL
        win = rasterio.windows.Window(*meta["window"])
        n = 0
        for name in members:
            y, mth, h = ndvi_index(name)
            if not (y0 <= y <= y1):
                continue
            i = (y - y0) * 24 + (mth - 1) * 2 + (h - 1)
            if done[i]:
                continue
            with rasterio.open(f"/vsizip/{z}/{name}") as src:
                nd = src.read(1, window=win)
                if src.count >= 2:
                    qc = src.read(2, window=win)
                    nd = np.where(np.isin(qc, C.NDVI_QC_BAD), C.NDVI_FILL, nd)
            mm[i] = nd[::-1]                               # north-up -> ascending latitude
            done[i] = True
            n += 1
        mm.flush()
        np.save(done_f, done)
        logger.info(f"NDVI {period}: {n} half-months cropped; {done.sum()}/{n_per} done")
        if not keep_zips:
            z.unlink()
    if mm is not None:
        del mm
    logger.info(f"NDVI {region}: {done.sum()}/{n_per} half-months available")


# =============================================================================
# KOPPEN-GEIGER
# =============================================================================

def download_koppen():
    dst = C.data_dir("koppen", f"koppen_{C.KOPPEN_PERIOD}.tif")
    if dst.exists():
        logger.info(f"Koppen-Geiger: {dst} exists")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    z = dst.parent / "koppen_geiger_tif.zip"
    if not z.exists():
        fetch_resumable(C.KOPPEN_URL, z)
    with zipfile.ZipFile(z) as zz:
        names = zz.namelist()
        tif = next(n for n in names if n.endswith(f"{C.KOPPEN_PERIOD}/{C.KOPPEN_FILE}"))
        leg = next(n for n in names if n.lower().endswith("legend.txt"))
        (dst.parent / "legend.txt").write_bytes(zz.read(leg))
        dst.write_bytes(zz.read(tif))
    z.unlink()
    labels = C.koppen_labels((dst.parent / "legend.txt").read_text())
    logger.info(f"Koppen-Geiger: {dst} ({len(labels)} classes in legend.txt)")


# =============================================================================
# MAIN
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="ci_nga", help=f"one of {list(C.REGIONS)} or a name for --bbox")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX"))
    ap.add_argument("--threads", type=int, default=32)
    ap.add_argument("--retry_missing", action="store_true", help="try the CHIRPS days that failed before again")
    ap.add_argument("--keep_zips", action="store_true", help="keep the NDVI zips (~2.5 GB) after cropping")
    ap.add_argument("--only", nargs="+", choices=["chirps", "ndvi", "boundaries", "aez", "koppen"],
                    default=["boundaries", "aez", "koppen", "ndvi", "chirps"])
    a = ap.parse_args()
    name, bbox = C.parse_region(a.region, a.bbox)
    C.setup_logging(C.data_dir("download_" + name + ".log"))
    if "boundaries" in a.only:
        download_boundaries()
    for what, fn in (("aez", download_aez), ("koppen", download_koppen)):
        if what in a.only:
            try:
                fn()
            except Exception as e:                         # noqa: BLE001 - zone maps are optional
                logger.warning(f"{what} download failed ({e}) - summaries will fall back to the rainfall regime")
    if "ndvi" in a.only and C.USE_NDVI:
        download_ndvi(name, bbox, a.keep_zips)
    if "chirps" in a.only:
        download_chirps(name, bbox, a.threads, a.retry_missing)


if __name__ == "__main__":
    main()
