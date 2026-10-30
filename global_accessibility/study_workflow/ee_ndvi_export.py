#!/usr/bin/env python3
"""
ee_ndvi_export.py - vegetation vigour on stable rainfed cropland (study estimand E2d), computed in
Google Earth Engine and exported as one GeoTIFF per sensor and year on the 30 arc-second grid of
global_accessibility_v3.py (the grid of access_effects_v01.py).

NOT TESTED against Earth Engine in development (no Earth Engine account there): run --dry-run first; it
checks the login, every asset, the band names and the bucket before any export starts.

Login: a service-account key (JSON) given with --key-file or the environment variable GEE_KEY_FILE (never
printed, never copied; keep it outside this folder with chmod 600). Without a key, the user credentials of
`earthengine authenticate` are used. The service account needs the roles Earth Engine Resource Writer and
Service Usage Consumer on the project, and Storage Object Admin on the bucket.

    pip install earthengine-api google-cloud-storage
    export GEE_KEY_FILE=/mnt/users/dhougni/post-harvest-aidi-field-mgt-XXXXXXXX.json
    python ee_ndvi_export.py --bucket <bucket> --dry-run
    python ee_ndvi_export.py --bucket <bucket> --sensor modis --years 2001-2024
    python ee_ndvi_export.py --bucket <bucket> --sensor s2 --years 2017-2024
    python ee_ndvi_export.py --bucket <bucket> --download ndvi_exports     # when the tasks have finished

Exports go to gs://<bucket>/<prefix>/vigour_<sensor>_<year>*.tif (prefix default "ae_ndvi"; Earth Engine splits
large images into several files), or to Google Drive with --to-drive. Cells without a value hold -9999 (also
written as the GeoTIFF nodata value). --download copies them to NDVI_DIR of access_effects_v01.py (default
./ndvi_exports); stage ndvi can also fetch them itself (NDVI_GCS_BUCKET).

Bands, in this order (VIGOUR_BANDS of access_effects_v01.py):
    1 ndvi_integral          sum over the season months of the monthly mean NDVI
    2 ndvi_peak              highest monthly mean NDVI in the season
    3 kndvi_integral         the same integral for kNDVI = tanh(NDVI^2)
    4 evi_integral           the same integral for EVI
    5 ndvi_dry_integral      mean monthly NDVI outside the season (placebo)
    6 ndvi_noncrop_integral  NDVI integral of the natural vegetation in the cell (placebo)
    7 crop_frac              share of the cell under the stable rainfed cropland mask
    8 n_obs                  valid monthly values in the season
Season months are fixed per pixel from the 2001-2014 MODIS climatology (months whose mean NDVI is at least
halfway between the climatological minimum and maximum), so roads built after 2014 cannot move the window.
The cropland mask (30 m): GLC_FCS30D classes 10/11 (rainfed, herbaceous) in every year 2015-2022, Hansen tree
cover 2000 <= 10%; irrigated (20) and tree/orchard (12) cropland are excluded. access_effects_v01.py adds the
GACED30 and AFCD stable-cropland filter on the cells.
"""
import argparse
import json
import os
import stat
import sys
from pathlib import Path

GRID_RES = 1 / 120                                   # 30 arc-seconds
GRID_TRANSFORM = [GRID_RES, 0, -180.0, 0, -GRID_RES, 85.0]   # origin of the global_accessibility_v3.py grid
SSA_BBOX = (-18.0, -35.0, 52.0, 25.0)
ASSETS = {
    "modis": "MODIS/061/MOD13Q1",
    "s2": "COPERNICUS/S2_SR_HARMONIZED",
    "cloudscore": "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED",
    "glc": "projects/sat-io/open-datasets/GLC-FCS30D/annual",
    "hansen": "UMD/hansen/global_forest_change_2025_v1_13",
}
CLIM_YEARS = (2001, 2014)
CROP_CLASSES = [10, 11]
NATURAL_CLASSES = list(range(51, 93)) + [120, 121, 122, 130]
MASK_YEARS = range(2015, 2023)                       # GLC_FCS30D annual ends in 2022
MAX_TREECOVER = 10
MIN_PIXEL_FRAC = 0.7                                 # a MODIS / 100 m pixel counts as cropland above this share
NODATA = -9999.0                                     # VIGOUR_NODATA of access_effects_v01.py
S2_SCALE = 100                                       # metres at which Sentinel-2 monthly composites are computed


DEFAULT_PROJECT = "post-harvest-aidi-field-mgt"
DEFAULT_PREFIX = "ae_ndvi"


def key_email(key_file):
    """client_email of a service-account key file (the key itself is never printed). Warns when the file
    can be read by other users."""
    key_file = Path(key_file).expanduser()
    if not key_file.exists():
        sys.exit(f"key file not found: {key_file}")
    mode = key_file.stat().st_mode
    if mode & (stat.S_IRGRP | stat.S_IROTH):
        print(f"WARNING: {key_file} is readable by other users; run: chmod 600 {key_file}")
    return json.loads(key_file.read_text())["client_email"], key_file


def ee_init(project, key_file):
    import ee
    if key_file:
        email, kf = key_email(key_file)
        ee.Initialize(credentials=ee.ServiceAccountCredentials(email, str(kf)), project=project)
        print(f"Earth Engine: service account {email}, project {project}")
    else:
        ee.Initialize(project=project)
        print(f"Earth Engine: stored user credentials, project {project}")
    return ee


def gcs_bucket(bucket, project, key_file):
    from google.cloud import storage
    client = storage.Client.from_service_account_json(str(Path(key_file).expanduser()), project=project) \
        if key_file else storage.Client(project=project)
    return client.bucket(bucket)


def download_exports(bucket, prefix, key_file, dest, project=DEFAULT_PROJECT, log=print):
    """Copy gs://bucket/prefix/vigour_*.tif to dest (files already there with the same size are kept)."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    b = gcs_bucket(bucket, project, key_file)
    n = 0
    for blob in b.list_blobs(prefix=f"{prefix.rstrip('/')}/vigour_"):
        if not blob.name.endswith(".tif"):
            continue
        out = dest / Path(blob.name).name
        if out.exists() and out.stat().st_size == blob.size:
            continue
        tmp = out.with_name(out.name + ".part")
        blob.download_to_filename(str(tmp))
        tmp.replace(out)
        n += 1
    log(f"downloaded {n} export files from gs://{bucket}/{prefix} to {dest}")
    return n


def parse_years(text):
    a, _, b = text.partition("-")
    return list(range(int(a), int(b or a) + 1))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--project", default=DEFAULT_PROJECT, help="Google Cloud project registered for Earth Engine")
    p.add_argument("--key-file", default=os.environ.get("GEE_KEY_FILE"),
                   help="service-account key JSON (default: environment variable GEE_KEY_FILE)")
    p.add_argument("--bucket", help="Cloud Storage bucket for the exports")
    p.add_argument("--prefix", default=DEFAULT_PREFIX, help="folder in the bucket (or Drive folder)")
    p.add_argument("--to-drive", action="store_true", help="export to Google Drive instead of Cloud Storage")
    p.add_argument("--sensor", choices=["modis", "s2"], default="modis")
    p.add_argument("--years", default="2001-2024")
    p.add_argument("--bbox", type=float, nargs=4, default=SSA_BBOX, metavar=("W", "S", "E", "N"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--download", metavar="DIR", help="only download finished exports from the bucket to DIR")
    a = p.parse_args(argv)
    if not a.to_drive and not a.bucket:
        sys.exit("give --bucket <name> (Cloud Storage) or --to-drive")
    if a.download and not a.bucket:
        sys.exit("--download reads from Cloud Storage: give --bucket <name>")
    if a.to_drive and a.key_file and not a.download:
        # a service account has its own Drive, which the user cannot open (and often no Drive quota)
        sys.exit("--to-drive with a service-account key would export to the service account's own Drive. "
                 "Use --bucket, or log in as yourself (earthengine authenticate) and pass --key-file ''")
    if a.download:
        download_exports(a.bucket, a.prefix, a.key_file, a.download, a.project)
        return
    ee = ee_init(a.project, a.key_file)
    if not a.to_drive:
        try:
            next(iter(gcs_bucket(a.bucket, a.project, a.key_file).list_blobs(max_results=1)), None)
            print(f"bucket gs://{a.bucket}: reachable")
        except Exception as e:                       # noqa: BLE001 - shown to the user, then stop
            sys.exit(f"bucket gs://{a.bucket} not usable with these credentials: {e}")
    region = ee.Geometry.Rectangle(list(a.bbox), "EPSG:4326", False)

    # --- assets and band names (checked first) --------------------------------------------------
    glc_col = ee.ImageCollection(ASSETS["glc"])
    glc = glc_col.mosaic()
    glc_bands = glc.bandNames().getInfo()
    if len(glc_bands) != 23:
        sys.exit(f"GLC_FCS30D annual: expected 23 bands (2000-2022), found {glc_bands}")
    print("GLC_FCS30D bands:", glc_bands[:3], "...", glc_bands[-1], "(band i = year 1999 + i)")
    hansen = ee.Image(ASSETS["hansen"])
    print("Hansen bands:", hansen.bandNames().getInfo())
    modis = ee.ImageCollection(ASSETS["modis"])
    print("MODIS bands:", modis.first().bandNames().getInfo())
    if a.sensor == "s2":
        print("Sentinel-2 bands:", ee.ImageCollection(ASSETS["s2"]).first().bandNames().getInfo()[:13])
    years = parse_years(a.years)
    where = f"Drive folder {a.prefix}" if a.to_drive else f"gs://{a.bucket}/{a.prefix}/"
    print(f"sensor {a.sensor}, years {years[0]}-{years[-1]}, bbox {a.bbox}, exports to {where}")

    # --- masks at 30 m ----------------------------------------------------------------------------
    by_year = {1999 + i + 1: glc.select(b) for i, b in enumerate(glc_bands)}
    stable = None
    natural = None
    for y in MASK_YEARS:
        c = by_year[y].remap(CROP_CLASSES, [1] * len(CROP_CLASSES), 0)
        n = by_year[y].remap(NATURAL_CLASSES, [1] * len(NATURAL_CLASSES), 0)
        stable = c if stable is None else stable.And(c)
        natural = n if natural is None else natural.And(n)
    low_trees = hansen.select("treecover2000").lte(MAX_TREECOVER)
    crop30 = stable.And(low_trees).rename("crop").toFloat()
    nat30 = natural.rename("nat").toFloat()

    # --- monthly vegetation indices ----------------------------------------------------------------
    mproj = modis.first().projection()

    def modis_month(y, m):
        start = ee.Date.fromYMD(y, m, 1)
        col = modis.filterDate(start, start.advance(1, "month"))

        def prep(img):
            ok = img.select("SummaryQA").lte(1)
            ndvi = img.select("NDVI").multiply(0.0001)
            evi = img.select("EVI").multiply(0.0001)
            return ee.Image.cat(ndvi.rename("ndvi"), evi.rename("evi")).updateMask(ok)
        return col.map(prep).mean().setDefaultProjection(mproj)

    def s2_month(y, m):
        start = ee.Date.fromYMD(y, m, 1)
        cs = ee.ImageCollection(ASSETS["cloudscore"])
        col = ee.ImageCollection(ASSETS["s2"]).filterDate(start, start.advance(1, "month")).filterBounds(region) \
            .linkCollection(cs, ["cs_cdf"])

        def prep(img):
            ok = img.select("cs_cdf").gte(0.60)
            b2, b4, b8 = [img.select(b).multiply(0.0001) for b in ("B2", "B4", "B8")]
            ndvi = b8.subtract(b4).divide(b8.add(b4))
            evi = b8.subtract(b4).multiply(2.5).divide(b8.add(b4.multiply(6)).subtract(b2.multiply(7.5)).add(1))
            return ee.Image.cat(ndvi.rename("ndvi"), evi.rename("evi")).updateMask(ok)
        return col.map(prep).median().reproject(crs="EPSG:4326", scale=S2_SCALE)

    # season months from the MODIS 2001-2014 climatology (fixed before the treatment window)
    clim = ee.Image.cat([
        modis.filter(ee.Filter.calendarRange(CLIM_YEARS[0], CLIM_YEARS[1], "year"))
             .filter(ee.Filter.calendarRange(m, m, "month"))
             .map(lambda img: img.select("NDVI").multiply(0.0001).updateMask(img.select("SummaryQA").lte(1)))
             .mean().rename(f"m{m:02d}") for m in range(1, 13)]).setDefaultProjection(mproj)
        # list comprehension: 12 bands m01..m12
    cmin, cmax = clim.reduce(ee.Reducer.min()), clim.reduce(ee.Reducer.max())
    thr = cmin.add(cmax.subtract(cmin).multiply(0.5))
    season = clim.gte(thr)                                   # 12 bands, 1 = season month

    def vigour(y, month_fn, proj):
        months = [month_fn(y, m) for m in range(1, 13)]
        ndvi = ee.Image.cat([mm.select("ndvi").rename(f"n{i:02d}") for i, mm in enumerate(months, 1)])
        evi = ee.Image.cat([mm.select("evi").rename(f"e{i:02d}") for i, mm in enumerate(months, 1)])
        kndvi = ndvi.pow(2).tanh()
        s = season.rename(ndvi.bandNames())
        insea = ndvi.updateMask(s)
        out = ee.Image.cat(
            insea.reduce(ee.Reducer.sum()).rename("ndvi_integral"),
            insea.reduce(ee.Reducer.max()).rename("ndvi_peak"),
            kndvi.updateMask(s).reduce(ee.Reducer.sum()).rename("kndvi_integral"),
            evi.updateMask(s.rename(evi.bandNames())).reduce(ee.Reducer.sum()).rename("evi_integral"),
            ndvi.updateMask(s.Not()).reduce(ee.Reducer.mean()).rename("ndvi_dry_integral"),
            insea.reduce(ee.Reducer.count()).rename("n_obs"),
        ).setDefaultProjection(proj)
        return out

    def to_cell(img, frac30, proj):
        """Mean of img over the pixels (of proj) that are >= MIN_PIXEL_FRAC under the 30 m mask frac30,
        aggregated to the 30 arc-second grid."""
        frac = frac30.reduceResolution(ee.Reducer.mean(), maxPixels=65535).reproject(proj)
        return img.updateMask(frac.gte(MIN_PIXEL_FRAC)) \
            .reduceResolution(ee.Reducer.mean(), maxPixels=65535) \
            .reproject(crs="EPSG:4326", crsTransform=GRID_TRANSFORM)

    if a.sensor == "modis":
        month_fn, proj = modis_month, mproj
    else:
        month_fn, proj = s2_month, ee.Projection("EPSG:4326").atScale(S2_SCALE)
    crop_frac_cell = crop30.reduceResolution(ee.Reducer.mean(), maxPixels=65535) \
        .reproject(crs="EPSG:4326", crsTransform=GRID_TRANSFORM).rename("crop_frac")
    if a.dry_run:
        print("dry run: assets and band names checked; no export started")
        return
    for y in years:
        v = vigour(y, month_fn, proj)
        crop_part = to_cell(v.select(["ndvi_integral", "ndvi_peak", "kndvi_integral", "evi_integral",
                                      "ndvi_dry_integral", "n_obs"]), crop30, proj)
        noncrop = to_cell(v.select("ndvi_integral"), nat30, proj).rename("ndvi_noncrop_integral")
        img = ee.Image.cat(crop_part.select(["ndvi_integral", "ndvi_peak", "kndvi_integral", "evi_integral",
                                             "ndvi_dry_integral"]), noncrop, crop_frac_cell,
                           crop_part.select("n_obs")).toFloat().unmask(NODATA)    # masked -> NODATA, not 0
        name = f"vigour_{a.sensor}_{y}"
        common = dict(image=img, description=name, region=region, crs="EPSG:4326", crsTransform=GRID_TRANSFORM,
                      maxPixels=10 ** 13, fileFormat="GeoTIFF", formatOptions={"noData": NODATA})
        if a.to_drive:
            task = ee.batch.Export.image.toDrive(folder=a.prefix, fileNamePrefix=name, **common)
        else:
            task = ee.batch.Export.image.toCloudStorage(bucket=a.bucket, fileNamePrefix=f"{a.prefix}/{name}", **common)
        task.start()
        print(f"started {name} (task {task.id}); follow it at https://code.earthengine.google.com/tasks")


if __name__ == "__main__":
    main()
