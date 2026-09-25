"""
Travel time (minutes) to the nearest city or port, from friction surfaces made
by friction.py, with the size classes of Nelson et al. (2019):

  to = "city"                         to = "port" (World Port Index 'Harbor Size')
  size  inhabitants                   size  description
  1     5,000,000 - 50,000,000        1     Large
  2     1,000,000 -  5,000,000        2     Medium
  3       500,000 -  1,000,000        3     Small
  4       200,000 -    500,000        4     Very small
  5       100,000 -    200,000        5     Any (incl. ports without a size)
  6        50,000 -    100,000
  7        20,000 -     50,000
  8        10,000 -     20,000
  9         5,000 -     10,000

By default a size means "this class or larger" (e.g. city 6 = cities of at
least 50,000 inhabitants); --exact-class uses only the class itself.

Cities are settlements built from GHSL for each date: contiguous 1 km cells of
the Degree of Urbanisation grid (GHS-SMOD) classed urban cluster or urban centre
(codes 21, 22, 23, 30; 8-connected), with population summed from GHS-POP. Urban
clusters have >= 5,000 inhabitants by definition, which matches class 9.

Example:
    python traveltime.py \
      --friction output_friction/friction_t1.tif output_friction/friction_t2.tif \
      --labels 2020 2026 \
      --smod GHS_SMOD_E2020...zip GHS_SMOD_E2025...zip \
      --pop  GHS_POP_E2020...zip  GHS_POP_E2025...zip \
      --ports UpdatedPub150.csv --city-sizes 6 --port-sizes 5 --out-dir output_tt
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize, shapes
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from scipy import ndimage
from shapely.geometry import shape
from skimage.graph import MCP_Geometric

import friction as fr

NODATA = fr.NODATA
# lower bound of each city class (class 1 = largest)
CITY_BREAKS = {1: 5e6, 2: 1e6, 3: 5e5, 4: 2e5, 5: 1e5, 6: 5e4, 7: 2e4, 8: 1e4, 9: 5e3}
CITY_UPPER = 5e7
PORT_CLASS = {"Large": 1, "Medium": 2, "Small": 3, "Very Small": 4}
URBAN_CODES = (21, 22, 23, 30)
SNAP_MAX_M = 5000   # move a destination on an impassable cell (e.g. a port on water) this far


# ---------------- destinations ----------------
def city_class(pop):
    """Nelson et al. size class (1-9) from population; 0 = below 5,000 or above 50M."""
    pop = np.asarray(pop, dtype=float)
    out = np.zeros(pop.shape, dtype=int)
    for cls in sorted(CITY_BREAKS, reverse=True):          # 9 .. 1
        out[pop >= CITY_BREAKS[cls]] = cls
    out[pop >= CITY_UPPER] = 0
    return out


def _raster_path(path):
    """A .tif inside a GHSL .zip is opened through GDAL's /vsizip/."""
    path = str(path)
    if path.endswith(".zip"):
        tif = next(n for n in zipfile.ZipFile(path).namelist() if n.endswith(".tif"))
        return f"/vsizip/{path}/{tif}"
    return path


def settlements_from_ghsl(smod, pop, bounds_lonlat, margin_m=20_000):
    """Settlement polygons (GHS-SMOD urban clusters) with GHS-POP population and class."""
    with rasterio.open(_raster_path(smod)) as s, rasterio.open(_raster_path(pop)) as p:
        if s.transform != p.transform or s.crs != p.crs:
            raise ValueError("GHS-SMOD and GHS-POP must be on the same grid (use the "
                             "same resolution and projection, e.g. both 54009_1000)")
        b = transform_bounds(4326, s.crs, *bounds_lonlat)
        win = from_bounds(b[0] - margin_m, b[1] - margin_m, b[2] + margin_m, b[3] + margin_m,
                          s.transform).round_offsets().round_lengths()
        codes = s.read(1, window=win, boundless=True, fill_value=0)
        people = p.read(1, window=win, boundless=True, fill_value=0).astype("float64")
        people[people < 0] = 0
        transform, crs = s.window_transform(win), s.crs
    urban = np.isin(codes, URBAN_CODES)
    labels, n = ndimage.label(urban, structure=np.ones((3, 3)))
    if n == 0:
        return gpd.GeoDataFrame({"pop": [], "size_class": []}, geometry=[], crs=crs)
    pop_sum = ndimage.sum(people, labels, index=np.arange(1, n + 1))
    polys = [(shape(g), int(v)) for g, v in shapes(labels.astype("int32"), mask=urban,
                                                    transform=transform)]
    g = gpd.GeoDataFrame({"label": [v for _, v in polys]},
                         geometry=[p for p, _ in polys], crs=crs).dissolve("label")
    g["pop"] = pop_sum[g.index.values - 1].round()
    g["size_class"] = city_class(g["pop"])
    return g.reset_index()


def load_ports(csv, bounds_lonlat=None):
    """World Port Index (NGA Pub. 150 CSV) as points with size_class 1-4, 5 = no size."""
    df = pd.read_csv(csv, usecols=["Main Port Name", "Country Code", "Harbor Size",
                                   "Latitude", "Longitude"])
    if bounds_lonlat is not None:
        w, s, e, n = bounds_lonlat
        df = df[df["Longitude"].between(w, e) & df["Latitude"].between(s, n)]
    df["size_class"] = df["Harbor Size"].map(PORT_CLASS).fillna(5).astype(int)
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
                            crs=4326)


def select(dest, size, exact=False, to="city"):
    """Destinations of a size class, or of that class and larger (default)."""
    if to == "port" and size == 5:
        return dest
    return dest[dest["size_class"] == size] if exact else \
        dest[(dest["size_class"] >= 1) & (dest["size_class"] <= size)]


# ---------------- cost distance ----------------
def target_cells(dest, grid, passable):
    """Boolean grid of start cells. Polygons: every passable cell inside; points (and
    polygons with no passable cell) snap to the nearest passable cell within SNAP_MAX_M."""
    targets = np.zeros(grid.shape, dtype=bool)
    if dest.empty:
        return targets
    dest = dest.to_crs(grid.crs)
    polys = dest[dest.geom_type.isin(["Polygon", "MultiPolygon"])]
    if len(polys):
        inside = rasterize(((g, 1) for g in polys.geometry), out_shape=grid.shape,
                           transform=grid.transform, fill=0, dtype="uint8").astype(bool)
        targets |= inside & passable
    pts = dest.geometry.where(~dest.index.isin(polys.index), dest.geometry.centroid)
    covered = [targets[r, c] if 0 <= r < grid.height and 0 <= c < grid.width else False
               for r, c in (rasterio.transform.rowcol(grid.transform, p.x, p.y)
                            for p in pts)]
    need = [p for p, ok in zip(pts, covered) if not ok]
    if need:
        # nearest passable cell for every cell (indices of the closest passable one)
        _, (ri, ci) = ndimage.distance_transform_edt(~passable, return_indices=True)
        for p in need:
            r, c = rasterio.transform.rowcol(grid.transform, p.x, p.y)
            if not (0 <= r < grid.height and 0 <= c < grid.width):
                continue
            rr, cc = ri[r, c], ci[r, c]
            if np.hypot(rr - r, cc - c) * grid.res <= SNAP_MAX_M:
                targets[rr, cc] = True
    return targets


def travel_time(friction, grid, targets):
    """Minutes from every cell to the nearest target cell (least-cost, 8 neighbours).

    MCP_Geometric charges the mean cost of the two cells times the step length
    (1 or sqrt(2) cells), so costs are friction (min/m) x cell size (m).
    """
    costs = np.where(friction == NODATA, np.inf, friction.astype("float64") * grid.res)
    starts = np.argwhere(targets)
    if len(starts) == 0:
        return np.full(grid.shape, NODATA, dtype="float32")
    cum, _ = MCP_Geometric(costs, fully_connected=True).find_costs(starts)
    out = cum.astype("float32")
    out[~np.isfinite(cum)] = NODATA
    return out


def population_on_grid(pop, grid):
    """GHS-POP (people per source cell) as people per friction-grid cell.

    Averaging the counts gives people per source-cell area; scaling by the area
    ratio then gives people per target cell, for coarser or finer target grids.
    """
    with rasterio.open(_raster_path(pop)) as src:
        src_area = abs(src.transform.a * src.transform.e)
        with WarpedVRT(src, crs=grid.crs, transform=grid.transform, width=grid.width,
                       height=grid.height, resampling=Resampling.average) as vrt:
            a = vrt.read(1, masked=True).filled(0).astype("float64")
    a[a < 0] = 0
    return a * (grid.res ** 2 / src_area)


def access_stats(tt, people, thresholds=(30, 60, 120, 240)):
    ok = tt != NODATA
    total = people[ok].sum()
    row = {"pop_total": round(total),
           "pop_weighted_mean_min": round(float((tt[ok] * people[ok]).sum() / total), 1)
           if total else np.nan,
           "median_min_area": round(float(np.median(tt[ok])), 1) if ok.any() else np.nan}
    for t in thresholds:
        row[f"pop_share_within_{t}min"] = round(float(people[ok & (tt <= t)].sum() / total), 4) \
            if total else np.nan
    return row


# ---------------- main ----------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--friction", nargs="+", required=True, help="one friction raster per date")
    p.add_argument("--labels", nargs="+", help="one label per date (default t1, t2, ...)")
    p.add_argument("--smod", nargs="+", help="GHS-SMOD 1 km (.zip or .tif), one per date "
                   "or one for all")
    p.add_argument("--pop", nargs="+", help="GHS-POP 1 km on the same grid as --smod")
    p.add_argument("--cities", help="alternative to GHSL: vector file with a population "
                   "column 'pop' (points or polygons)")
    p.add_argument("--ports", help="World Port Index CSV (NGA Pub. 150)")
    p.add_argument("--city-sizes", nargs="*", type=int, default=[6])
    p.add_argument("--port-sizes", nargs="*", type=int, default=[])
    p.add_argument("--exact-class", action="store_true",
                   help="only the given class, not that class and larger")
    p.add_argument("--out-dir", default="output_traveltime")
    return p.parse_args(argv)


def _per_date(values, n, name):
    if not values:
        return [None] * n
    if len(values) == 1:
        return values * n
    if len(values) != n:
        raise SystemExit(f"--{name}: give one value, or one per friction raster")
    return values


def main(argv=None):
    a = parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = len(a.friction)
    labels = a.labels or [f"t{i + 1}" for i in range(n)]
    smods, pops = _per_date(a.smod, n, "smod"), _per_date(a.pop, n, "pop")

    rows, results = [], {}
    for label, fpath, smod, pop in zip(labels, a.friction, smods, pops):
        grid = fr.Grid.from_raster(fpath)
        with rasterio.open(fpath) as r:
            friction = r.read(1)
            bounds = transform_bounds(r.crs, 4326, *r.bounds)
        passable = friction != NODATA
        # Destinations outside the passable part of the grid cannot be reached. To
        # count cities or ports across a border, build the friction surface over a
        # wider area (neighbouring OSM extracts, buffered --boundary).
        wide = bounds

        dests = {}
        if a.city_sizes:
            if a.cities:
                cities = gpd.read_file(a.cities)
                cities["size_class"] = city_class(cities["pop"])
            elif smod and pop:
                cities = settlements_from_ghsl(smod, pop, wide)
            else:
                raise SystemExit("cities need --smod and --pop, or --cities")
            cities.to_crs(4326).to_file(out / f"cities_{label}.gpkg", driver="GPKG")
            dests["city"] = cities
        if a.port_sizes:
            if not a.ports:
                raise SystemExit("--port-sizes needs --ports")
            dests["port"] = load_ports(a.ports, wide)
            dests["port"].to_file(out / f"ports_{label}.gpkg", driver="GPKG")

        people = population_on_grid(pop, grid) if pop else None
        for to, sizes in (("city", a.city_sizes), ("port", a.port_sizes)):
            for size in sizes:
                sel = select(dests[to], size, a.exact_class, to)
                tt = travel_time(friction, grid, target_cells(sel, grid, passable))
                name = f"{to}{size}{'_exact' if a.exact_class else ''}"
                fr.write_tif(out / f"traveltime_{label}_{name}.tif", tt, grid)
                results[(label, name)] = tt
                row = {"date": label, "layer": name, "n_destinations": len(sel)}
                if people is not None:
                    row.update(access_stats(tt, people))
                rows.append(row)
                print(row)

    # change between consecutive dates (negative = faster)
    for (l1, l2) in zip(labels, labels[1:]):
        for (lab, name), tt2 in results.items():
            if lab != l2 or (l1, name) not in results:
                continue
            tt1 = results[(l1, name)]
            ok = (tt1 != NODATA) & (tt2 != NODATA)
            fr.write_tif(out / f"traveltime_change_{l2}_minus_{l1}_{name}.tif",
                         np.where(ok, tt2 - tt1, NODATA), fr.Grid.from_raster(a.friction[0]))
    s = pd.DataFrame(rows)
    s.to_csv(out / "traveltime_summary.csv", index=False)
    return s


if __name__ == "__main__":
    main()
