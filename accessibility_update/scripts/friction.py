"""
Friction surfaces (minutes per metre) for two dates, from OSM roads, land cover
and topography, for updating accessibility (travel-time) maps.

Speed per cell (km/h), fastest option wins:
  - road cells:     speed of the fastest road class in the cell
                    (speed_table.csv, incl. the unpaved factor; see merge_roads.py)
  - off-road cells: land-cover walking speed (landcover_speed.csv, flat terrain)
                    x Tobler slope factor exp(-3.5 * tan(slope))
Friction = 60 / (1000 * speed)  [min/m]; impassable cells (speed 0) are nodata.

With --base-friction, an existing friction raster (min/m) replaces the land
cover + slope part, and only the roads of each date are burned into it.

Example (Benin + Togo, see run_friction_benin_togo.py):
    python friction.py \
      --osm-pbf-t1 data/benin-200101.osm.pbf data/togo-200101.osm.pbf \
      --osm-pbf-t2 data/benin-260901.osm.pbf data/togo-260901.osm.pbf \
      --landcover-t1 <WorldCover tiles> --dem <Copernicus DEM tiles> \
      --boundary data/benin.poly data/togo.poly --out-dir output_friction
"""
from __future__ import annotations

import argparse
import math
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from shapely.geometry import Polygon
from shapely.ops import unary_union

import merge_roads as mr

HERE = Path(__file__).resolve().parent
LANDCOVER_TABLE = HERE.parent / "config" / "landcover_speed.csv"
RES_M = 100
NODATA = -9999.0
TOBLER_K = 3.5

WORLDCOVER_URL = ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/{v}/{y}/map/"
                  "ESA_WorldCover_10m_{y}_{v}_{tile}_Map.tif")
WORLDCOVER_VERSION = {2020: "v100", 2021: "v200"}
COPDEM_URL = ("https://copernicus-dem-30m.s3.amazonaws.com/"
              "Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM/"
              "Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM.tif")


# ---------------- grid ----------------
@dataclass
class Grid:
    crs: object
    transform: object
    height: int
    width: int

    @property
    def shape(self):
        return (self.height, self.width)

    @property
    def res(self):
        return self.transform.a

    @classmethod
    def from_bounds(cls, bounds_lonlat, crs, res_m=RES_M):
        """Grid covering lon/lat bounds, snapped to multiples of res_m."""
        minx, miny, maxx, maxy = transform_bounds(4326, crs, *bounds_lonlat)
        minx, miny = math.floor(minx / res_m) * res_m, math.floor(miny / res_m) * res_m
        maxx, maxy = math.ceil(maxx / res_m) * res_m, math.ceil(maxy / res_m) * res_m
        return cls(crs, from_origin(minx, maxy, res_m, res_m),
                   int(round((maxy - miny) / res_m)), int(round((maxx - minx) / res_m)))

    @classmethod
    def from_raster(cls, path):
        with rasterio.open(path) as r:
            return cls(r.crs, r.transform, r.height, r.width)


def write_tif(path, arr, grid, nodata=NODATA):
    with rasterio.open(path, "w", driver="GTiff", height=grid.height, width=grid.width,
                       count=1, dtype="float32", crs=grid.crs, transform=grid.transform,
                       nodata=nodata, compress="deflate", tiled=True,
                       predictor=3) as dst:
        dst.write(arr.astype("float32"), 1)


# ---------------- tile lists ----------------
def _hemi(v, pos, neg, width):
    return f"{pos if v >= 0 else neg}{abs(int(v)):0{width}d}"


def worldcover_urls(bounds_lonlat, year=2021):
    """3x3 degree ESA WorldCover tiles covering the bounds (2020 = v100, 2021 = v200)."""
    w, s, e, n = bounds_lonlat
    urls = []
    for lat in range(math.floor(s / 3) * 3, math.floor(n / 3) * 3 + 1, 3):
        for lon in range(math.floor(w / 3) * 3, math.floor(e / 3) * 3 + 1, 3):
            tile = _hemi(lat, "N", "S", 2) + _hemi(lon, "E", "W", 3)
            urls.append(WORLDCOVER_URL.format(v=WORLDCOVER_VERSION[year], y=year, tile=tile))
    return urls


def copdem_urls(bounds_lonlat):
    """1x1 degree Copernicus GLO-30 tiles covering the bounds (ocean tiles do not exist)."""
    w, s, e, n = bounds_lonlat
    return [COPDEM_URL.format(lat=_hemi(lat, "N", "S", 2), lon=_hemi(lon, "E", "W", 3))
            for lat in range(math.floor(s), math.floor(n) + 1)
            for lon in range(math.floor(w), math.floor(e) + 1)]


# ---------------- raster inputs ----------------
def warp_to_grid(sources, grid, resampling, nodata, dtype="float32"):
    """Mosaic raster tiles (paths or URLs) onto the grid; first valid value wins.

    Missing tiles (e.g. Copernicus DEM over the ocean) are skipped with a warning.
    """
    out = np.full(grid.shape, nodata, dtype=dtype)
    for src_path in sources:
        try:
            src = rasterio.open(src_path)
        except rasterio.errors.RasterioIOError:
            warnings.warn(f"skipping unreadable tile: {src_path}")
            continue
        with src, WarpedVRT(src, crs=grid.crs, transform=grid.transform,
                            width=grid.width, height=grid.height,
                            resampling=resampling, nodata=nodata) as vrt:
            a = vrt.read(1).astype(dtype)
        fill = (out == nodata) & (a != nodata)
        out[fill] = a[fill]
    return out


def read_boundary(paths, crs):
    """Country outline(s): Geofabrik .poly files or any vector file."""
    geoms = []
    for p in paths:
        if str(p).endswith(".poly"):
            geoms.append(parse_poly(Path(p).read_text()))
        else:
            geoms.append(gpd.read_file(p).to_crs(4326).union_all())
    return gpd.GeoSeries([unary_union(geoms)], crs=4326).to_crs(crs)


def parse_poly(text):
    """Osmosis .poly format: name, then rings (lon lat per line) ended by END; '!' = hole."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    outer, holes, ring, name = [], [], None, None
    for l in lines[1:]:
        if ring is None:
            if l == "END":
                break
            ring, name = [], l
        elif l == "END":
            (holes if name.startswith("!") else outer).append(Polygon(ring))
            ring = None
        else:
            x, y = l.split()[:2]
            ring.append((float(x), float(y)))
    return unary_union(outer).difference(unary_union(holes)) if holes else unary_union(outer)


# ---------------- speeds ----------------
def load_landcover_table(path=LANDCOVER_TABLE):
    return pd.read_csv(path, comment="#").set_index("class")["speed_kmh"]


def tan_slope(dem, res_m):
    """tan(slope) from a DEM on a metric grid; NaN (no DEM) -> 0."""
    dy, dx = np.gradient(dem.astype("float64"), res_m)
    t = np.hypot(dx, dy)
    return np.nan_to_num(t, nan=0.0)


def tobler_factor(tan_s):
    """Walking speed relative to flat ground, Tobler (1993): exp(-3.5 * tan(slope)).

    Direction of travel is unknown on a raster, so the uphill form is used
    (conservative). Flat = 1.0; 10% slope = 0.70; 30% = 0.35.
    """
    return np.exp(-TOBLER_K * tan_s)


def offroad_speed(landcover, tan_s, lc_table):
    lut = np.zeros(256, dtype="float32")
    for cls, v in lc_table.items():
        lut[int(cls)] = v
    lc = np.clip(landcover, 0, 255).astype(int)
    return lut[lc] * tobler_factor(tan_s).astype("float32")


def burn_road_speed(roads, grid, all_touched=True):
    """km/h of the fastest road per cell, 0 where there is no road."""
    roads = roads.to_crs(grid.crs).sort_values("speed")  # fast roads burned last
    if roads.empty:
        return np.zeros(grid.shape, dtype="float32")
    return rasterize(zip(roads.geometry, roads["speed"]), out_shape=grid.shape,
                     transform=grid.transform, fill=0, all_touched=all_touched,
                     dtype="float32")


def to_friction(speed_kmh):
    """km/h -> minutes per metre; speed <= 0 -> NODATA (impassable)."""
    f = np.full(speed_kmh.shape, NODATA, dtype="float32")
    ok = speed_kmh > 0
    f[ok] = 60.0 / (1000.0 * speed_kmh[ok])
    return f


def from_friction(friction):
    s = np.zeros(friction.shape, dtype="float32")
    ok = (friction > 0) & (friction != NODATA)
    s[ok] = 60.0 / (1000.0 * friction[ok])
    return s


# ---------------- main ----------------
def build_offroad(a, grid, bounds):
    """Off-road speed per date: {'t1': array, 't2': array}."""
    if a.base_friction:
        with rasterio.open(a.base_friction) as r:
            base = r.read(1, masked=True).filled(NODATA).astype("float32")
        s = from_friction(base)
        return {"t1": s, "t2": s}
    lc_table = load_landcover_table(a.landcover_table)
    dem_src = a.dem or copdem_urls(bounds)
    dem = warp_to_grid(dem_src, grid, Resampling.average, nodata=NODATA)
    dem[dem == NODATA] = np.nan
    ts = tan_slope(dem, grid.res)
    out = {}
    lc_srcs = {"t1": a.landcover_t1 or worldcover_urls(bounds, 2021),
               "t2": a.landcover_t2 or a.landcover_t1 or worldcover_urls(bounds, 2021)}
    cache = {}
    for t, srcs in lc_srcs.items():
        key = tuple(srcs)
        if key not in cache:
            lc = warp_to_grid(srcs, grid, Resampling.mode, nodata=0, dtype="uint8")
            cache[key] = offroad_speed(lc, ts, lc_table)
        out[t] = cache[key]
    return out


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--osm-pbf-t1", nargs="+", required=True)
    p.add_argument("--osm-pbf-t2", nargs="+", required=True)
    p.add_argument("--ms-roads", help="also write a t2 map with ML gap-fill roads")
    p.add_argument("--iso3", nargs="+", help="countries to take from --ms-roads")
    p.add_argument("--landcover-t1", nargs="+", help="land-cover tiles for t1 "
                   "(default: ESA WorldCover 2021 tiles)")
    p.add_argument("--landcover-t2", nargs="+", help="land-cover tiles for t2 "
                   "(default: same as t1, so only roads change)")
    p.add_argument("--dem", nargs="+", help="DEM tiles (default: Copernicus GLO-30)")
    p.add_argument("--base-friction", help="existing friction raster (min/m); its grid is "
                   "used and only roads are burned in")
    p.add_argument("--boundary", nargs="+", help=".poly or vector outline(s); cells "
                   "outside become nodata")
    p.add_argument("--speed-table", default=mr.SPEED_TABLE)
    p.add_argument("--landcover-table", default=LANDCOVER_TABLE)
    p.add_argument("--res-m", type=float, default=RES_M)
    p.add_argument("--crs", help="metric CRS (default: UTM zone estimated from OSM)")
    p.add_argument("--out-dir", default="output_friction")
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    table = mr.load_speed_table(a.speed_table)

    roads = {"t1": mr.read_osm_roads(a.osm_pbf_t1, table),
             "t2": mr.read_osm_roads(a.osm_pbf_t2, table)}
    crs = a.crs or roads["t2"].estimate_utm_crs()
    if a.boundary:
        boundary = read_boundary(a.boundary, crs)
        bounds = tuple(boundary.to_crs(4326).total_bounds)
    else:
        boundary, bounds = None, tuple(roads["t2"].total_bounds)
    grid = Grid.from_raster(a.base_friction) if a.base_friction else \
        Grid.from_bounds(bounds, crs, a.res_m)
    print(f"grid: {grid.width} x {grid.height} cells of {grid.res:g} m, {grid.crs}")

    if a.ms_roads:
        ms = mr.read_ms_roads(a.ms_roads, a.iso3).to_crs(crs)
        ms_new = mr.conflate(ms, roads["t2"].to_crs(crs))
        roads["t2_ml"] = pd.concat([roads["t2"].to_crs(crs), ms_new], ignore_index=True)

    offroad = build_offroad(a, grid, bounds)
    inside = None
    if boundary is not None:
        inside = rasterize([(boundary.iloc[0], 1)], out_shape=grid.shape,
                           transform=grid.transform, fill=0, dtype="uint8").astype(bool)

    speeds, rows = {}, []
    for t, r in roads.items():
        road = burn_road_speed(gpd.GeoDataFrame(r, geometry="geometry"), grid)
        speed = np.maximum(road, offroad["t2" if t.startswith("t2") else "t1"])
        if inside is not None:
            speed[~inside] = 0
        speeds[t] = speed
        fr = to_friction(speed)
        write_tif(out / f"friction_{t}.tif", fr, grid)
        ok = fr != NODATA
        rows.append({"map": t, "cells_valid": int(ok.sum()),
                     "road_cells": int((road > 0)[ok].sum()),
                     "mean_speed_kmh": round(float(speed[ok].mean()), 3),
                     "mean_friction_min_per_m": float(fr[ok].mean())})

    change = speeds["t2"] - speeds["t1"]
    valid = (speeds["t1"] > 0) | (speeds["t2"] > 0)
    write_tif(out / "speed_change_t2_minus_t1_kmh.tif", np.where(valid, change, NODATA), grid)
    s = pd.DataFrame(rows)
    s["cells_faster_than_t1"] = [0] + [int(((speeds[t] - speeds["t1"]) > 0).sum())
                                       for t in list(speeds)[1:]]
    s["cells_slower_than_t1"] = [0] + [int(((speeds[t] - speeds["t1"]) < 0).sum())
                                       for t in list(speeds)[1:]]
    s.to_csv(out / "friction_summary.csv", index=False)
    print(s.to_string(index=False))
    return grid, speeds


if __name__ == "__main__":
    main()
