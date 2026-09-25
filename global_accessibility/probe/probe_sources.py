"""
Probe the global data sources used by global_accessibility.py (run on GitHub Actions,
Python 3.13). Writes small text/CSV reports to probe/out/.
"""
import concurrent.futures as cf
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import requests

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
S = requests.Session()
S.headers["User-Agent"] = "global-accessibility-probe (research; contact via GitHub)"
log = []


def say(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True)
    log.append(msg)


def get(url, **kw):
    r = S.get(url, timeout=120, allow_redirects=True, **kw)
    r.raise_for_status()
    return r


# 1. Nelson et al. 2019 README + metadata (figshare 7638134)
try:
    art = get("https://api.figshare.com/v2/articles/7638134").json()
    for f in art["files"]:
        if f["name"].endswith((".txt", ".csv", ".pdf")) and f["size"] < 2e5:
            (OUT / f"nelson_{f['name']}").write_bytes(get(f["download_url"]).content)
            say("nelson file saved:", f["name"])
except Exception as e:
    say("NELSON ERROR", repr(e))

# 2. Geofabrik: leaf regions and availability of yearly snapshots
try:
    idx = get("https://download.geofabrik.de/index-v1.json").json()
    feats = idx["features"]
    parents = {f["properties"].get("parent") for f in feats}
    leaves = [f for f in feats if f["properties"]["id"] not in parents]
    say("geofabrik features:", len(feats), "leaves:", len(leaves))
    stamps = ["150101", "180101", "200101", "230101", "250101", "260101"]

    def head(f):
        p = f["properties"]
        latest = p["urls"]["pbf"]
        row = {"id": p["id"], "parent": p.get("parent"), "latest": latest}
        for st in stamps:
            u = latest.replace("-latest.osm.pbf", f"-{st}.osm.pbf")
            try:
                h = S.head(u, timeout=60, allow_redirects=True)
                row[st] = int(h.headers.get("Content-Length", 0)) if h.ok else -h.status_code
            except Exception as e:
                row[st] = f"ERR {e.__class__.__name__}"
            time.sleep(0.05)
        return row

    with cf.ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(head, leaves))
    import csv
    with open(OUT / "geofabrik_leaf_snapshots.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "parent", "latest"] + stamps)
        w.writeheader(); w.writerows(rows)
    for st in stamps:
        ok = [r[st] for r in rows if isinstance(r[st], int) and r[st] > 0]
        say(f"geofabrik {st}: {len(ok)}/{len(rows)} leaves available, {sum(ok) / 1e9:.1f} GB")
    # leaf geometry overlap: do leaves tile the world without double counting?
    say("leaf parents:", sorted({r['parent'] for r in rows if r['parent']})[:60])
except Exception as e:
    say("GEOFABRIK ERROR", repr(e))

# 3. WorldCover 2021: tile count and one tile's structure
try:
    keys, marker = [], ""
    while True:
        r = get("https://esa-worldcover.s3.eu-central-1.amazonaws.com/",
                params={"prefix": "v200/2021/map/", "marker": marker, "max-keys": 1000})
        import re
        ks = re.findall(r"<Key>([^<]+)</Key>", r.text)
        keys += ks
        if "<IsTruncated>true</IsTruncated>" not in r.text or not ks:
            break
        marker = ks[-1]
    tifs = [k for k in keys if k.endswith("_Map.tif")]
    say("worldcover 2021 map tiles:", len(tifs), "example:", tifs[:2])
    (OUT / "worldcover_2021_tiles.txt").write_text("\n".join(tifs))
except Exception as e:
    say("WORLDCOVER LIST ERROR", repr(e))

try:
    import rasterio
    with rasterio.open("https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
                       "ESA_WorldCover_10m_2021_v200_N06E000_Map.tif") as r:
        say("worldcover tile:", r.shape, r.crs, r.res, r.dtypes, "nodata", r.nodata,
            "overviews", r.overviews(1), "blocks", r.block_shapes, "bounds", r.bounds)
except Exception as e:
    say("WORLDCOVER TILE ERROR", repr(e))

# 4. Copernicus DEM GLO-90
try:
    tl = get("https://copernicus-dem-90m.s3.amazonaws.com/tileList.txt").text.split()
    say("copernicus glo-90 tiles:", len(tl), "example:", tl[:2])
    (OUT / "copdem90_tiles.txt").write_text("\n".join(tl))
    import rasterio
    for name in [tl[0], "Copernicus_DSM_COG_30_N06_00_E001_00_DEM",
                 "Copernicus_DSM_COG_30_N65_00_E020_00_DEM"]:
        url = f"https://copernicus-dem-90m.s3.amazonaws.com/{name}/{name}.tif"
        try:
            with rasterio.open(url) as r:
                say("glo-90", name, r.shape, r.res, r.dtypes, "nodata", r.nodata,
                    "overviews", r.overviews(1), "bounds", r.bounds)
        except Exception as e:
            say("glo-90 open failed", name, repr(e))
except Exception as e:
    say("COPDEM ERROR", repr(e))

# 5. Natural Earth admin-0 (10m)
try:
    z = get("https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip").content
    say("natural earth zip MB:", round(len(z) / 1e6, 1))
    import geopandas as gpd
    p = OUT.parent / "ne.zip"; p.write_bytes(z)
    g = gpd.read_file(f"zip://{p}")
    say("natural earth rows:", len(g), "cols:", [c for c in g.columns if c in
        ("ADM0_A3", "ISO_A3", "ISO_A3_EH", "CONTINENT", "REGION_UN", "NAME", "SOV_A3")])
    say("continents:", g["CONTINENT"].value_counts().to_dict())
    af = g[g["CONTINENT"] == "Africa"]
    say("africa n:", len(af), "ISO_A3 == -99:", af.loc[af["ISO_A3"] == "-99", "NAME"].tolist())
    p.unlink()
except Exception as e:
    say("NATURAL EARTH ERROR", repr(e))

# 6. World Bank WGI control of corruption (0-100)
try:
    r = get("https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_CC.SC",
            params={"source": 3, "format": "json", "date": "2024", "per_page": 400}).json()
    rows = [x for x in r[1] if x["value"] is not None]
    say("wgi 2024 countries with value:", len(rows), "meta:", r[0])
except Exception as e:
    say("WGI ERROR", repr(e))

# 7. Nelson layer structure (one file, ~430 MB)
try:
    import rasterio, numpy as np
    f = next(x for x in art["files"] if x["name"] == "travel_time_to_cities_6.tif")
    p = OUT.parent / "nelson6.tif"
    with get(f["download_url"], stream=True) as r, open(p, "wb") as fh:
        for chunk in r.iter_content(1 << 22):
            fh.write(chunk)
    with rasterio.open(p) as r:
        say("nelson6:", r.shape, r.crs, r.res, r.dtypes, "nodata", r.nodata, "bounds", r.bounds,
            "compress", r.compression, "tags", r.tags())
        win = rasterio.windows.from_bounds(0.8, 6.0, 3.9, 12.5, r.transform)
        a = r.read(1, window=win, masked=True)
        say("nelson6 Benin/Togo window: min/median/max", a.min(), np.ma.median(a), a.max())
    p.unlink()
except Exception as e:
    say("NELSON TIF ERROR", repr(e))

say("python", sys.version)
(OUT / "probe_log.txt").write_text("\n".join(log) + "\n")
