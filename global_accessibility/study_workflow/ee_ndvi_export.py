#!/usr/bin/env python3
"""
ee_ndvi_export.py - vegetation vigour on stable rainfed cropland (study estimand E2d), computed in
Google Earth Engine and exported as one GeoTIFF per sensor and year on the 30 arc-second grid of
global_accessibility_v3.py (the grid of access_effects_v01.py).

Run --dry-run first: it checks the login, the bucket, every asset and band name, and evaluates the export
image of the first and last year on a small box (PROBE_BOX), so computation errors show before any task starts.

Login: a service-account key (JSON) given with --key-file or the environment variable GEE_KEY_FILE (never
printed, never copied; keep it outside this folder with chmod 600). Without a key, the user credentials of
`earthengine authenticate` are used. The service account needs the roles Earth Engine Resource Writer and
Service Usage Consumer on the project, and Storage Object Admin on the bucket.

    pip install earthengine-api google-cloud-storage
    export GEE_KEY_FILE=/mnt/users/dhougni/post-harvest-aidi-field-mgt-XXXXXXXX.json
    python ee_ndvi_export.py --bucket <bucket> --dry-run
    python ee_ndvi_export.py --bucket <bucket> --make-static              # once per sensor; wait for the task
    python ee_ndvi_export.py --bucket <bucket> --sensor modis --years 2001-2024
    python ee_ndvi_export.py --bucket <bucket> --sensor s2 --make-static
    python ee_ndvi_export.py --bucket <bucket> --sensor s2 --years 2017-2024
    python ee_ndvi_export.py --bucket <bucket> --download ndvi_exports     # when the tasks have finished

Exports go to gs://<bucket>/<prefix>/vigour_<sensor>_<year>*.tif (prefix default "ae_ndvi"; Earth Engine splits
large images into several files), or to Google Drive with --to-drive. Cells without a value hold -9999 (also
written as the GeoTIFF nodata value). --download copies them to NDVI_DIR of access_effects_v01.py (default
./ndvi_exports); stage ndvi can also fetch them itself (NDVI_GCS_BUCKET).

Bands, in this order (VIGOUR_BANDS of access_effects_v01.py), per 30 arc-second cell, as means over the
fine-grid pixels that are at least MIN_PIXEL_FRAC under the mask:
    1 ndvi_integral          season NDVI integral: mean monthly NDVI over the valid season months x the number
                             of season months (a cloudy month does not lower it)
    2 ndvi_peak              highest monthly NDVI in the season
    3 kndvi_integral         the same integral for kNDVI = tanh(NDVI^2)
    4 evi_integral           the same integral for EVI
    5 ndvi_dry_integral      mean monthly NDVI outside the season, in the same 12 months (placebo)
    6 ndvi_noncrop_integral  NDVI integral of the natural vegetation in the cell (placebo)
    7 crop_frac              share of the cell under the stable rainfed cropland mask
    8 n_obs                  valid season months (mean over the pixels)
Pixel-years with fewer than MIN_SEASON_COVER of their season months valid are left out.

Season year. Season months are fixed per pixel from the 2001-2014 MODIS climatology (months whose mean NDVI is
at least halfway between the climatological minimum and maximum), so roads built after 2014 cannot move them.
Season year y is the 12 months that start at the pixel's climatological minimum month and whose last season
month (the end of the season, near harvest) falls in calendar year y. A southern-African season (Nov-Apr) is
therefore one season year, labelled by its harvest year, instead of being split across two calendar years.

Grids. Monthly indices are computed on a fine grid aligned with the 30" cells: 7.5" (4 x 4 per cell, about
230 m) for MODIS, 3" (10 x 10, about 90 m) for Sentinel-2, whose cloud mask and indices are computed at the
native 10 m first. The cropland mask (30 m): GLC_FCS30D classes 10/11 (rainfed, herbaceous) in every year
2015-2022, Hansen tree cover 2000 <= 10%; irrigated (20) and tree/orchard (12) cropland are excluded.
access_effects_v01.py adds the GACED30 and AFCD stable-cropland filter on the cells.

Cost. The masks and season window do not change between years. --make-static exports them once per sensor as
an Earth Engine asset (projects/<project>/assets/<prefix>/static_<sensor>); the year exports read it when it
exists, and otherwise recompute it in every task. A Community-tier project has 150 EECU-hours a month; past it,
tasks still run but slower. Sentinel-2 at 10 m over the whole of Sub-Saharan Africa is expensive: give it a
--bbox (e.g. the pilot countries). Years already in the bucket, or queued, are skipped (--force exports again).
"""
import argparse
import base64
import hashlib
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
MIN_PIXEL_FRAC = 0.7                                 # a fine-grid pixel counts as cropland above this share
MIN_SEASON_COVER = 0.5                               # share of the season months that must be valid in a year
S2_CLEAR = 0.60                                      # Cloud Score+ cs_cdf threshold (clear above)
NODATA = -9999.0                                     # VIGOUR_NODATA of access_effects_v01.py
# fine grids, aligned with the 30 arc-second cells: 4 x 4 pixels of 7.5" (about 230 m, MODIS) or
# 10 x 10 pixels of 3" (about 90 m, Sentinel-2) per cell
FINE = {"modis": 4, "s2": 10}
UNUSED_MONTHS = (0, 35)                              # of the 36-month stack: see season_window_start
FIRST_YEAR = {"modis": 2001, "s2": 2017}             # MOD13Q1 from Feb 2000; Sentinel-2 L2A from Mar 2017
PROBE_BOX = (8.0, 11.5, 8.25, 11.75)                 # dry run: small cropland box near Kano, Nigeria (W, S, E, N)
CROP_BANDS = ["ndvi_integral", "ndvi_peak", "kndvi_integral", "evi_integral", "ndvi_dry_integral"]
EXPORT_BANDS = CROP_BANDS + ["ndvi_noncrop_integral", "crop_frac", "n_obs"]   # = VIGOUR_BANDS of access_effects


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


def same_file(path, blob):
    """The local copy matches the object: same size and, when the object has one, the same MD5 (a re-export
    with --force usually has the same size)."""
    if path.stat().st_size != blob.size:
        return False
    md5 = getattr(blob, "md5_hash", None)
    if not md5:
        return True
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return base64.b64encode(h.digest()).decode() == md5


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
        if out.exists() and same_file(out, blob):
            continue
        tmp = out.with_name(out.name + ".part")
        blob.download_to_filename(str(tmp))
        tmp.replace(out)
        n += 1
    log(f"downloaded {n} export files from gs://{bucket}/{prefix} to {dest}")
    return n


def parse_years(text):
    a, _, b = text.partition("-")
    a, b = int(a), int(b or a)
    if b < a:
        sys.exit(f"--years {text}: the first year must not be after the last")
    return list(range(a, b + 1))


def fine_transform(sensor):
    k = FINE[sensor]
    return [GRID_RES / k, 0, GRID_TRANSFORM[2], 0, -GRID_RES / k, GRID_TRANSFORM[5]]


def probe_box(bbox, size=0.25):
    """A box of `size` degrees at the south-west corner of PROBE_BOX when it lies inside bbox, else at the
    centre of bbox."""
    w, s, e, n = bbox
    x0, y0 = PROBE_BOX[0], PROBE_BOX[1]
    if not (w <= x0 and s <= y0 and x0 + size <= e and y0 + size <= n):
        x0, y0 = (w + e - size) / 2, (s + n - size) / 2
    return (x0, y0, x0 + size, y0 + size)


STATIC_RULE = 2                                      # version of the fixed-layer rules; part of the asset name


def bbox_tag(bbox):
    """'' for the default bbox, else '_<w>_<s>_<e>_<n>' (asset and file names: no '.' or '-')."""
    if tuple(bbox) == tuple(SSA_BBOX):
        return ""
    return "_" + "_".join(f"{v:g}".replace(".", "p").replace("-", "m") for v in bbox)


def static_name(sensor, bbox):
    """Asset name of the fixed layers: the bbox and a hash of every rule that defines them are part of the
    name, so a changed rule makes a new asset (an image asset cannot be overwritten) instead of reusing a
    stale one."""
    rules = repr((STATIC_RULE, CROP_CLASSES, NATURAL_CLASSES, list(MASK_YEARS), MAX_TREECOVER, CLIM_YEARS,
                  FINE[sensor], ASSETS["glc"], ASSETS["hansen"], ASSETS["modis"]))
    return f"static_{sensor}{bbox_tag(bbox)}_v{hashlib.sha1(rules.encode()).hexdigest()[:6]}"


def export_name(sensor, year, bbox):
    return f"vigour_{sensor}_{year}{bbox_tag(bbox)}"


def season_window_start(m_min, last):
    """Index (into the 36 months Jan of y-1 .. Dec of y+1) of the first month of season year y. The 12 months
    start at the pixel's climatological NDVI minimum month m_min (0-11); `last` (0-11) is the position in that
    window of the last season month. Season year y is the window whose last season month (the end of the
    season, near harvest) falls in calendar year y. static_image builds the Earth Engine image from this
    function (remap over the 144 cases), so both always agree."""
    return 12 + (m_min + last) % 12 - last


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--project", default=DEFAULT_PROJECT, help="Google Cloud project registered for Earth Engine")
    p.add_argument("--key-file", default=os.environ.get("GEE_KEY_FILE"),
                   help="service-account key JSON (default: environment variable GEE_KEY_FILE)")
    p.add_argument("--bucket", help="Cloud Storage bucket for the exports")
    p.add_argument("--prefix", default=DEFAULT_PREFIX, help="folder in the bucket (or Drive folder)")
    p.add_argument("--to-drive", action="store_true", help="export to Google Drive instead of Cloud Storage")
    p.add_argument("--sensor", choices=["modis", "s2"], default="modis")
    p.add_argument("--years", default=None, help="e.g. 2001-2024 (default: the sensor's first year to 2024)")
    p.add_argument("--bbox", type=float, nargs=4, default=SSA_BBOX, metavar=("W", "S", "E", "N"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--download", metavar="DIR", help="only download finished exports from the bucket to DIR")
    p.add_argument("--make-static", action="store_true",
                   help="export the year-invariant layers (masks, season window) once as an Earth Engine asset")
    p.add_argument("--force", action="store_true", help="export years already in the bucket or queued again")
    a = p.parse_args(argv)
    a.prefix = a.prefix.strip("/")
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
    years = parse_years(a.years or f"{FIRST_YEAR[a.sensor]}-2024")
    if years[0] < FIRST_YEAR[a.sensor]:
        sys.exit(f"--sensor {a.sensor} starts in {FIRST_YEAR[a.sensor]} (season years need the months before "
                 f"and after); use --years {FIRST_YEAR[a.sensor]}-{years[-1]}")
    if a.sensor == "s2" and years[0] <= 2018:
        print("WARNING: Sentinel-2 L2A coverage of Africa is incomplete in 2017-2018; those season years are "
              "partly empty")
    where = f"Drive folder {a.prefix}" if a.to_drive else f"gs://{a.bucket}/{a.prefix}/"
    print(f"sensor {a.sensor}, years {years[0]}-{years[-1]}, bbox {a.bbox}, exports to {where}")

    # --- fixed layers (static): 30 m masks and the season window, on the sensor's fine grid ------------
    # A mosaic has no fixed projection (WGS84 at 1 degree), which reduceResolution rejects: the GLC mosaic
    # gets the projection of its tiles here, once, and every mask derived from it inherits it.
    glc_proj = glc_col.first().projection()
    glc = glc.setDefaultProjection(glc_proj)
    fine = fine_transform(a.sensor)
    to_fine = dict(crs="EPSG:4326", crsTransform=fine)
    asset_id = f"projects/{a.project}/assets/{a.prefix}/{static_name(a.sensor, a.bbox)}"

    def static_image():
        """Year-invariant layers, encoded as integers (what --make-static stores as an asset)."""
        by_year = {1999 + i + 1: glc.select(b) for i, b in enumerate(glc_bands)}
        stable = natural = None
        for y in MASK_YEARS:
            c = by_year[y].remap(CROP_CLASSES, [1] * len(CROP_CLASSES), 0)
            n = by_year[y].remap(NATURAL_CLASSES, [1] * len(NATURAL_CLASSES), 0)
            stable = c if stable is None else stable.And(c)
            natural = n if natural is None else natural.And(n)
        low_trees = hansen.select("treecover2000").lte(MAX_TREECOVER)
        crop30 = stable.And(low_trees).toFloat().setDefaultProjection(glc_proj)
        nat30 = natural.toFloat().setDefaultProjection(glc_proj)

        def pct(m30):
            return m30.reduceResolution(ee.Reducer.mean(), maxPixels=4096) \
                .reproject(crs="EPSG:4326", crsTransform=fine).multiply(100).round().toUint8()
        # season months and window from the MODIS 2001-2014 climatology (fixed before the treatment window)
        mproj = modis.first().projection()
        clim = ee.Image.cat([
            modis.filter(ee.Filter.calendarRange(CLIM_YEARS[0], CLIM_YEARS[1], "year"))
                 .filter(ee.Filter.calendarRange(m, m, "month"))
                 .map(lambda img: img.select("NDVI").multiply(0.0001).updateMask(img.select("SummaryQA").lte(1)))
                 .mean().rename(f"m{m:02d}") for m in range(1, 13)]).setDefaultProjection(mproj)
        cmin, cmax = clim.reduce(ee.Reducer.min()), clim.reduce(ee.Reducer.max())
        season = clim.gte(cmin.add(cmax.subtract(cmin).multiply(0.5)))          # 12 bands, 1 = season month
        bits = ee.Image.cat([season.select(i).toUint16().leftShift(i) for i in range(12)]) \
            .reduce(ee.Reducer.sum())
        # minimum month; masked months count as high (toArray would mask the whole pixel otherwise)
        m_min = clim.unmask(2).multiply(-1).toArray().arrayArgmax().arrayGet([0])          # 0-11
        # position in the window of the last season month
        last = ee.Image.cat([bits.rightShift(m_min.add(k).mod(12)).bitwiseAnd(1).multiply(k) for k in range(12)]) \
            .reduce(ee.Reducer.max())
        cases = list(range(144))
        start = m_min.multiply(12).add(last).remap(cases, [season_window_start(i // 12, i % 12) for i in cases])
        return ee.Image.cat(pct(crop30).rename("crop_pct"), pct(nat30).rename("nat_pct"),
                            bits.toUint16().reproject(**to_fine).rename("season_bits"),
                            start.toUint8().reproject(**to_fine).rename("win_start"))

    def asset_exists(aid):
        try:
            ee.data.getAsset(aid)
            return True
        except Exception:                            # noqa: BLE001 - not found
            return False

    if a.make_static and not a.dry_run:
        if asset_exists(asset_id):
            print(f"{asset_id} exists already (same rules); nothing to do")
            return
        parent = f"projects/{a.project}/assets/{a.prefix}"
        if not asset_exists(parent):
            ee.data.createAsset({"type": "FOLDER"}, parent)
        task = ee.batch.Export.image.toAsset(
            image=static_image(), description=static_name(a.sensor, a.bbox), assetId=asset_id, region=region,
            crs="EPSG:4326", crsTransform=fine, maxPixels=10 ** 13,
            pyramidingPolicy={"crop_pct": "mean", "nat_pct": "mean", "season_bits": "mode", "win_start": "mode"})
        task.start()
        print(f"started {static_name(a.sensor, a.bbox)} (task {task.id}) -> {asset_id}. When it has finished, run the year "
              "exports; they then read these layers instead of recomputing them in every task.")
        return
    if asset_exists(asset_id):
        static, static_src = ee.Image(asset_id), f"asset {asset_id}"
    else:
        static, static_src = static_image(), "computed in each task (run --make-static once to save EECU)"
    print(f"fixed layers: {static_src}")

    crop_f = static.select("crop_pct").divide(100)
    nat_f = static.select("nat_pct").divide(100)
    bits, start = static.select("season_bits"), static.select("win_start")
    n_season = ee.Image.cat([bits.rightShift(i).bitwiseAnd(1) for i in range(12)]).reduce(ee.Reducer.sum())
    in_win = [start.lte(k).And(start.add(12).gt(k)) for k in range(36)]
    in_sea = ee.Image.cat([w.And(bits.rightShift(k % 12).bitwiseAnd(1)) for k, w in enumerate(in_win)])
    off_sea = ee.Image.cat([w.And(bits.rightShift(k % 12).bitwiseAnd(1).Not()) for k, w in enumerate(in_win)])

    # --- monthly vegetation indices, on the fine grid -----------------------------------------------------
    blank = ee.Image.constant([0, 0]).rename(["ndvi", "evi"]).toFloat().updateMask(ee.Image.constant(0))

    def modis_month(y, m):
        start_d = ee.Date.fromYMD(y, m, 1)

        def prep(img):
            ok = img.select("SummaryQA").lte(1)
            return ee.Image.cat(img.select("NDVI").multiply(0.0001).rename("ndvi"),
                                img.select("EVI").multiply(0.0001).rename("evi")).updateMask(ok)
        # the blank image keeps the bands when a month has no composite (start or end of the record)
        col = modis.filterDate(start_d, start_d.advance(1, "month")).map(prep).merge(ee.ImageCollection([blank]))
        return col.mean().reproject(**to_fine)

    def s2_month(y, m):
        start_d = ee.Date.fromYMD(y, m, 1)
        cs = ee.ImageCollection(ASSETS["cloudscore"])

        def prep(img):
            # cloud mask and indices at the native 10 m, before any aggregation
            ok = img.select("cs_cdf").gte(S2_CLEAR)
            b2, b4, b8 = [img.select(b).multiply(0.0001) for b in ("B2", "B4", "B8")]
            ndvi = b8.subtract(b4).divide(b8.add(b4))
            evi = b8.subtract(b4).multiply(2.5).divide(b8.add(b4.multiply(6)).subtract(b2.multiply(7.5)).add(1))
            return ee.Image.cat(ndvi.rename("ndvi"), evi.rename("evi")).updateMask(ok)
        col = ee.ImageCollection(ASSETS["s2"]).filterDate(start_d, start_d.advance(1, "month")).filterBounds(region) \
            .linkCollection(cs, ["cs_cdf"]).map(prep).merge(ee.ImageCollection([blank]))
        return col.median().setDefaultProjection(ee.Projection("EPSG:4326").atScale(10)) \
            .reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject(**to_fine)

    month_fn = modis_month if a.sensor == "modis" else s2_month

    def vigour(y):
        """Season statistics of season year y (window of 12 months per pixel, see static_image)."""
        # a window never uses Jan of y-1 or Dec of y+1 (season_window_start): blank there, not computed
        months = [blank if k in UNUSED_MONTHS else month_fn(y - 1 + k // 12, k % 12 + 1) for k in range(36)]
        ndvi = ee.Image.cat([mm.select("ndvi") for mm in months]).rename([f"n{k:02d}" for k in range(36)])
        evi = ee.Image.cat([mm.select("evi") for mm in months]).rename([f"e{k:02d}" for k in range(36)])
        kndvi = ndvi.pow(2).tanh()
        n_in = ndvi.updateMask(in_sea).reduce(ee.Reducer.count())
        # integral = mean over the valid season months x season length, so a cloudy month does not lower it;
        # pixel-years with fewer than MIN_SEASON_COVER of the season months valid are left out
        enough = n_in.gte(n_season.multiply(MIN_SEASON_COVER)).And(n_season.gt(0))

        def integral(x):
            return x.updateMask(in_sea).reduce(ee.Reducer.mean()).multiply(n_season)
        return ee.Image.cat(
            integral(ndvi).rename("ndvi_integral"),
            ndvi.updateMask(in_sea).reduce(ee.Reducer.max()).rename("ndvi_peak"),
            integral(kndvi).rename("kndvi_integral"),
            integral(evi).rename("evi_integral"),
            ndvi.updateMask(off_sea).reduce(ee.Reducer.mean()).rename("ndvi_dry_integral"),
            n_in.rename("n_obs"),
        ).updateMask(enough).reproject(**to_fine)

    def to_cell(img, frac):
        """Mean of img over the fine pixels at least MIN_PIXEL_FRAC under the mask, on the 30 arc-second grid."""
        return img.updateMask(frac.gte(MIN_PIXEL_FRAC)).reduceResolution(ee.Reducer.mean(), maxPixels=256) \
            .reproject(crs="EPSG:4326", crsTransform=GRID_TRANSFORM)

    crop_frac_cell = crop_f.reduceResolution(ee.Reducer.mean(), maxPixels=256) \
        .reproject(crs="EPSG:4326", crsTransform=GRID_TRANSFORM).rename("crop_frac")

    def export_image(y):
        v = vigour(y)
        crop_part = to_cell(v.select(CROP_BANDS + ["n_obs"]), crop_f)
        noncrop = to_cell(v.select("ndvi_integral"), nat_f).rename("ndvi_noncrop_integral")
        img = ee.Image.cat(crop_part.select(CROP_BANDS), noncrop, crop_frac_cell, crop_part.select("n_obs"))
        return img.rename(EXPORT_BANDS).toFloat()

    if a.dry_run:
        # evaluate the real export image on a small box, for the first and last year, so that errors in the
        # computation (not only in the asset names) show up here and not as failed tasks
        pb = probe_box(a.bbox, 0.25 if a.sensor == "modis" else 0.05)   # S2 runs at 10 m: a small box
        box = ee.Geometry.Rectangle(list(pb), "EPSG:4326", False)
        for y in sorted({years[0], years[-1]}):
            try:
                vals = export_image(y).reduceRegion(ee.Reducer.mean(), box, crs="EPSG:4326",
                                                    crsTransform=GRID_TRANSFORM, maxPixels=10 ** 8).getInfo()
            except Exception as e:                   # noqa: BLE001 - shown to the user, then stop
                sys.exit(f"dry run: the {a.sensor} {y} export image fails on the probe box {pb}: {e}")
            print(f"probe box {pb}, {a.sensor} {y} (means over cells with a value; None = no value):")
            for k in EXPORT_BANDS:
                print(f"  {k:22s} {vals.get(k)}")
            if all(vals.get(k) is None for k in CROP_BANDS):
                print(f"WARNING: no vigour value in the probe box for {y} (no stable cropland there, or no "
                      "images that year); the computation itself ran")
        other = "s2" if a.sensor == "modis" else "modis"
        print(f"dry run: assets, band names and the {a.sensor} computation checked (not {other}: run "
              f"--dry-run --sensor {other} for it); no export started")
        return

    done = existing_exports(a, years)
    active = active_tasks(ee)
    for y in years:
        name = export_name(a.sensor, y, a.bbox)
        if not a.force and (y in done or name in active):
            print(f"skipped {name}: {'already in the bucket' if y in done else 'task already queued or running'} "
                  "(--force to export again)")
            continue
        img = export_image(y).unmask(NODATA)                  # masked -> NODATA, not 0
        common = dict(image=img, description=name, region=region, crs="EPSG:4326", crsTransform=GRID_TRANSFORM,
                      maxPixels=10 ** 13, fileFormat="GeoTIFF", formatOptions={"noData": NODATA})
        if a.to_drive:
            task = ee.batch.Export.image.toDrive(folder=a.prefix, fileNamePrefix=name, **common)
        else:
            task = ee.batch.Export.image.toCloudStorage(bucket=a.bucket, fileNamePrefix=f"{a.prefix}/{name}", **common)
        task.start()
        print(f"started {name} (task {task.id}); follow it at https://code.earthengine.google.com/tasks")


def existing_exports(a, years):
    """Years whose export (same sensor and bbox) is already in the bucket: <name>.tif or <name>-<offsets>.tif."""
    if a.to_drive:
        return set()
    b = gcs_bucket(a.bucket, a.project, a.key_file)
    out = set()
    for y in years:
        stem = f"{a.prefix}/{export_name(a.sensor, y, a.bbox)}"
        if any(bl.name[len(stem):][:1] in (".", "-") for bl in b.list_blobs(prefix=stem)):
            out.add(y)
    return out


def active_tasks(ee):
    """Descriptions of this project's export tasks that are queued or running."""
    try:
        ops = ee.data.listOperations()
    except Exception as e:                           # noqa: BLE001 - only a convenience
        print(f"WARNING: could not list the running tasks ({e}); none skipped for that reason")
        return set()
    return {o.get("metadata", {}).get("description") for o in ops
            if o.get("metadata", {}).get("state") in ("PENDING", "RUNNING")}


if __name__ == "__main__":
    main()

