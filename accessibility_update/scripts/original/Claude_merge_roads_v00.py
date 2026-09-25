"""
Merge Microsoft ML Road Detections with an OSM extract, then rasterize road speeds.

pip install geopandas pyrosm rasterio shapely pandas pyogrio

Inputs:
  - OSM country extract (.osm.pbf) from https://download.geofabrik.de
  - Microsoft region zip (TSV: ISO3 <tab> GeoJSON feature) from
    https://github.com/microsoft/RoadDetections (links in the README)
"""
import json
import zipfile

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely import STRtree, union_all
from shapely.geometry import shape
from pyrosm import OSM

# ---------------- settings ----------------
OSM_PBF     = "country-latest.osm.pbf"
MS_ZIP      = "Africa-Full.zip"   # region file from the Microsoft README
ISO3        = "XXX"               # your country's ISO3 code (first TSV column)
BUFFER_M    = 20     # ML road within this distance of OSM = "already mapped"
MAX_OVERLAP = 0.5    # drop ML road if >50% of its length lies inside OSM buffer
MIN_LEN_M   = 50     # drop tiny ML fragments
RES_M       = 100    # output raster resolution (m)
OUT_GPKG    = "roads_merged.gpkg"
OUT_TIF     = "road_speed_kmh.tif"

# km/h by OSM highway class -- calibrate these for your area
SPEEDS = {
    "motorway": 100, "trunk": 80, "primary": 70, "secondary": 55,
    "tertiary": 40, "unclassified": 30, "residential": 25,
    "motorway_link": 60, "trunk_link": 50, "primary_link": 45,
    "secondary_link": 40, "tertiary_link": 30,
    "service": 20, "track": 15, "living_street": 15,
}
ML_SPEED = 15                      # untagged ML roads treated as tracks
UNPAVED = {"unpaved", "dirt", "gravel", "ground", "earth", "sand", "compacted"}
UNPAVED_FACTOR = 0.7

# ---------------- 1. OSM roads ----------------
osm = OSM(OSM_PBF).get_network(network_type="all")
if "surface" not in osm.columns:
    osm["surface"] = None
osm = osm[osm["highway"].isin(SPEEDS)][["highway", "surface", "geometry"]]
osm = osm.explode(index_parts=False).reset_index(drop=True)
osm["speed"] = osm["highway"].map(SPEEDS).astype(float)
osm.loc[osm["surface"].isin(UNPAVED), "speed"] *= UNPAVED_FACTOR
osm["source"] = "osm"

# ---------------- 2. Microsoft roads (streamed, one country) ----------------
geoms = []
with zipfile.ZipFile(MS_ZIP) as z:
    with z.open(z.namelist()[0]) as f:
        for line in f:
            code, gj = line.decode("utf-8").rstrip("\n").split("\t", 1)
            if code == ISO3:
                geoms.append(shape(json.loads(gj)["geometry"]))
ms = gpd.GeoDataFrame(geometry=geoms, crs=4326)
print(f"OSM segments: {len(osm):,}  |  ML segments: {len(ms):,}")

# ---------------- 3. Project to metric CRS ----------------
utm = osm.estimate_utm_crs()
osm = osm.to_crs(utm)
ms = ms.to_crs(utm)
ms = ms[ms.length >= MIN_LEN_M].reset_index(drop=True)

# ---------------- 4. Conflation: keep ML roads not already in OSM ----------------
osm_buf = osm.buffer(BUFFER_M).values
ms_geoms = ms.geometry.values
tree = STRtree(osm_buf)
ms_idx, osm_idx = tree.query(ms_geoms, predicate="intersects")

overlap = np.zeros(len(ms))
pairs = pd.DataFrame({"ms": ms_idx, "osm": osm_idx})
for m, grp in pairs.groupby("ms"):
    local = union_all(osm_buf[grp["osm"].values])
    overlap[m] = ms_geoms[m].intersection(local).length / ms_geoms[m].length

ms_new = ms[overlap <= MAX_OVERLAP].copy()
ms_new["highway"] = "ml_detected"
ms_new["surface"] = None
ms_new["speed"] = float(ML_SPEED)
ms_new["source"] = "microsoft"
print(f"ML segments kept (not in OSM): {len(ms_new):,}")

# ---------------- 5. Merge and save ----------------
roads = pd.concat([osm, ms_new], ignore_index=True)
roads = gpd.GeoDataFrame(roads, geometry="geometry", crs=utm)
roads.to_file(OUT_GPKG, layer="roads", driver="GPKG")

# ---------------- 6. Rasterize (fastest road wins in each cell) ----------------
# Tip: for the final friction map, copy the grid (transform/shape/crs) from your
# land-cover raster instead, so all layers align exactly.
minx, miny, maxx, maxy = roads.total_bounds
width = int(np.ceil((maxx - minx) / RES_M))
height = int(np.ceil((maxy - miny) / RES_M))
transform = from_origin(minx, maxy, RES_M, RES_M)

roads = roads.sort_values("speed")  # slow burned first, fast overwrites
speed = rasterize(
    zip(roads.geometry, roads["speed"]),
    out_shape=(height, width), transform=transform,
    fill=0, all_touched=True, dtype="float32",
)

with rasterio.open(
    OUT_TIF, "w", driver="GTiff", height=height, width=width, count=1,
    dtype="float32", crs=utm, transform=transform, nodata=0, compress="deflate",
) as dst:
    dst.write(speed, 1)

print(f"Saved {OUT_GPKG} and {OUT_TIF}")
