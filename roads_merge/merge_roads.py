"""
Merge Microsoft ML Road Detections with OSM roads, flag roads that are new
between two OSM snapshots, and rasterize road speeds for a friction surface.

Improved version of original/Claude_merge_roads_v00.py (see README.md for the
list of changes and why).

Example (Benin + Togo):
    python merge_roads.py \
        --osm-pbf data/benin-latest.osm.pbf data/togo-latest.osm.pbf \
        --osm-pbf-t1 data/benin-200101.osm.pbf data/togo-200101.osm.pbf \
        --ms-roads data/Western_Africa.zip \
        --iso3 BEN TGO \
        --out-dir output

pip install -r requirements.txt   (geopandas, pyogrio, shapely>=2, rasterio)
"""
from __future__ import annotations

import argparse
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from shapely.geometry import shape

HERE = Path(__file__).resolve().parent

# ---------------- defaults ----------------
BUFFER_M = 20        # ML road within this distance of OSM = "already mapped"
MAX_OVERLAP = 0.5    # drop ML road if >50% of its length lies within BUFFER_M of OSM
MIN_LEN_M = 50       # drop tiny ML fragments
SAMPLE_STEP_M = 10   # spacing of points used to measure overlap along a line
RES_M = 100          # output raster resolution (m)
ML_SPEED = 15        # untagged ML roads treated as tracks (km/h)
UNPAVED = {"unpaved", "dirt", "gravel", "ground", "earth", "sand", "compacted",
           "mud", "fine_gravel", "grass", "laterite"}
UNPAVED_FACTOR = 0.7
SPEED_TABLE = HERE / "speed_table.csv"

_SURFACE_RE = re.compile(r'"surface"=>"([^"]*)"')


# ---------------- speeds ----------------
def load_speed_table(path: str | Path = SPEED_TABLE) -> pd.DataFrame:
    """CSV with columns highway, speed_kmh, paved_if_missing (yes/no).

    paved_if_missing = no -> the unpaved factor applies when the surface tag is
    absent (most rural roads in data-scarce areas carry no surface tag).
    """
    tab = pd.read_csv(path, comment="#")
    tab["paved_if_missing"] = tab["paved_if_missing"].str.strip().str.lower().eq("yes")
    return tab.set_index("highway")


def assign_speed(highway: pd.Series, surface: pd.Series, table: pd.DataFrame,
                 unpaved_factor: float = UNPAVED_FACTOR) -> pd.Series:
    base = highway.map(table["speed_kmh"]).astype(float)
    paved_default = highway.map(table["paved_if_missing"]).fillna(False).astype(bool)
    missing = surface.isna() | surface.eq("")
    unpaved = surface.isin(UNPAVED) | (missing & ~paved_default)
    return base.where(~unpaved, base * unpaved_factor)


# ---------------- readers ----------------
def read_osm_roads(pbf_paths: list[str], table: pd.DataFrame) -> gpd.GeoDataFrame:
    """Read highway lines from one or more .osm.pbf files with GDAL's OSM driver.

    Avoids the pyrosm dependency. Ways shared by two country extracts (border
    roads) are de-duplicated on osm_id.
    """
    parts = []
    for p in pbf_paths:
        g = gpd.read_file(p, layer="lines", engine="pyogrio",
                          columns=["osm_id", "highway", "other_tags"],
                          where="highway IS NOT NULL")
        g["extract"] = Path(p).name
        parts.append(g)
    osm = pd.concat(parts, ignore_index=True)
    osm = osm.drop_duplicates("osm_id")
    osm = osm[osm["highway"].isin(table.index)].copy()
    osm["surface"] = osm["other_tags"].str.extract(_SURFACE_RE, expand=False)
    osm = osm.drop(columns="other_tags")
    osm = osm.explode(index_parts=False).reset_index(drop=True)
    osm["speed"] = assign_speed(osm["highway"], osm["surface"], table)
    osm["source"] = "osm"
    return gpd.GeoDataFrame(osm, geometry="geometry", crs=4326)


def _iter_tsv_lines(path: Path):
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            data = [n for n in names if n.lower().endswith((".tsv", ".txt"))] or names
            for name in data:
                with z.open(name) as f:
                    yield from io.TextIOWrapper(f, encoding="utf-8")
    else:
        with open(path, encoding="utf-8") as f:
            yield from f


def read_ms_roads(path: str | Path, iso3: list[str]) -> gpd.GeoDataFrame:
    """Microsoft ML roads for the requested countries.

    Accepts the official regional .zip/.tsv (ISO3 <tab> GeoJSON Feature) or a
    GeoParquet file (e.g. the country-partitioned copy on Source Cooperative).
    """
    path = Path(path)
    wanted = {c.upper() for c in iso3}
    if path.suffix == ".parquet":
        ms = gpd.read_parquet(path)
        col = next((c for c in ms.columns if c.lower() in {"iso3", "country", "country_iso"}), None)
        if col is not None:
            ms = ms[ms[col].str.upper().isin(wanted)].rename(columns={col: "iso3"})
        return ms.to_crs(4326) if ms.crs else ms.set_crs(4326)

    rows, geoms = [], []
    for line in _iter_tsv_lines(path):
        code, _, gj = line.rstrip("\r\n").partition("\t")
        if code.strip().upper() not in wanted or not gj:
            continue
        obj = json.loads(gj)
        geom = obj.get("geometry", obj)            # Feature or bare geometry
        props = obj.get("properties") or {}
        geoms.append(shape(geom))
        rows.append({"iso3": code.strip().upper(),
                     "width_m": props.get("WidthMeters")})
    if not geoms:
        raise ValueError(f"No Microsoft roads found for {sorted(wanted)} in {path}")
    ms = gpd.GeoDataFrame(rows, geometry=geoms, crs=4326)
    # WidthMeters is stored as a string in the 2025.04.28 drop
    ms["width_m"] = pd.to_numeric(ms["width_m"], errors="coerce")
    return ms


# ---------------- conflation ----------------
def overlap_fraction(lines, ref_lines, dist_m: float,
                     step_m: float = SAMPLE_STEP_M, chunk: int = 50_000) -> np.ndarray:
    """Share of each line's length lying within dist_m of any reference line.

    Lines are sampled every step_m (at segment mid-points), and each sample is
    tested with an STRtree 'dwithin' query. This replaces the per-segment
    union of OSM buffers in v00, which gave the same answer but scaled badly
    (one polygon union per ML segment). Coordinates must be metric.
    """
    lines = np.asarray(lines)
    tree = shapely.STRtree(np.asarray(ref_lines))
    out = np.zeros(len(lines))
    for start in range(0, len(lines), chunk):
        part = lines[start:start + chunk]
        length = shapely.length(part)
        n = np.maximum(1, np.ceil(length / step_m).astype(int))
        owner = np.repeat(np.arange(len(part)), n)
        # position of sample k of n on the line: (k + 0.5) / n, normalized
        k = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
        frac = (k + 0.5) / np.repeat(n, n)
        pts = shapely.line_interpolate_point(part[owner], frac, normalized=True)
        hit_pt, _ = tree.query(pts, predicate="dwithin", distance=dist_m)
        near = np.zeros(len(pts), dtype=bool)
        near[hit_pt] = True
        out[start:start + len(part)] = np.bincount(owner, weights=near, minlength=len(part)) / n
    return out


def conflate(ms: gpd.GeoDataFrame, osm: gpd.GeoDataFrame,
             buffer_m: float = BUFFER_M, max_overlap: float = MAX_OVERLAP,
             min_len_m: float = MIN_LEN_M, ml_speed: float = ML_SPEED) -> gpd.GeoDataFrame:
    """ML roads not already in OSM (both inputs in the same metric CRS)."""
    ms = ms.explode(index_parts=False)
    ms = ms[ms.length >= min_len_m].reset_index(drop=True)
    ms["osm_overlap"] = overlap_fraction(ms.geometry.values, osm.geometry.values, buffer_m)
    new = ms[ms["osm_overlap"] <= max_overlap].copy()
    new["highway"] = "ml_detected"
    new["surface"] = None
    new["speed"] = float(ml_speed)
    new["source"] = "microsoft"
    return new


def flag_new_roads(osm_t2: gpd.GeoDataFrame, osm_t1: gpd.GeoDataFrame,
                   buffer_m: float = BUFFER_M, max_overlap: float = MAX_OVERLAP) -> pd.Series:
    """True for t2 roads that are absent from t1 (same proximity rule as conflate).

    Uses geometry rather than osm_id, because ways are often split, merged or
    re-drawn between snapshots without any change on the ground. NOTE: a road
    new in OSM is new *in the map*, not necessarily new on the ground.
    """
    return pd.Series(overlap_fraction(osm_t2.geometry.values, osm_t1.geometry.values,
                                      buffer_m) <= max_overlap, index=osm_t2.index)


# ---------------- raster ----------------
def rasterize_speed(roads: gpd.GeoDataFrame, out_tif: str | Path, res_m: float = RES_M,
                    template: str | Path | None = None, all_touched: bool = True) -> None:
    """Burn road speeds; the fastest road wins in each cell.

    With a template raster (e.g. your land-cover grid), its crs/transform/shape
    are reused so that all friction layers align exactly.
    """
    import rasterio
    from rasterio.features import rasterize
    from rasterio.transform import from_origin

    if template is not None:
        with rasterio.open(template) as t:
            crs, transform, shape_ = t.crs, t.transform, (t.height, t.width)
        roads = roads.to_crs(crs)
    else:
        # Snap the grid to multiples of res_m so that rasters from different
        # runs (e.g. two timepoints) share cell boundaries.
        crs = roads.crs
        minx, miny, maxx, maxy = roads.total_bounds
        minx, miny = np.floor([minx / res_m, miny / res_m]) * res_m
        maxx, maxy = (np.floor([maxx / res_m, maxy / res_m]) + 1) * res_m
        shape_ = (int(round((maxy - miny) / res_m)), int(round((maxx - minx) / res_m)))
        transform = from_origin(minx, maxy, res_m, res_m)

    roads = roads.sort_values("speed")  # slow burned first, fast overwrites
    speed = rasterize(zip(roads.geometry, roads["speed"]), out_shape=shape_,
                      transform=transform, fill=0, all_touched=all_touched,
                      dtype="float32")
    with rasterio.open(out_tif, "w", driver="GTiff", height=shape_[0], width=shape_[1],
                       count=1, dtype="float32", crs=crs, transform=transform,
                       nodata=0, compress="deflate") as dst:
        dst.write(speed, 1)


# ---------------- summary ----------------
def summarize(roads: gpd.GeoDataFrame) -> pd.DataFrame:
    keys = ["source", "highway"] + (["new_since_t1"] if "new_since_t1" in roads else [])
    s = (roads.assign(length_km=roads.length / 1000)
              .groupby(keys, dropna=False)
              .agg(n_segments=("length_km", "size"), length_km=("length_km", "sum"))
              .reset_index()
              .sort_values(["source", "length_km"], ascending=[True, False]))
    s["length_km"] = s["length_km"].round(1)
    return s


# ---------------- main ----------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--osm-pbf", nargs="+", required=True, help="current OSM extract(s)")
    p.add_argument("--osm-pbf-t1", nargs="+", help="older OSM extract(s) to flag new roads")
    p.add_argument("--ms-roads", required=True, help="Microsoft .zip/.tsv or .parquet")
    p.add_argument("--iso3", nargs="+", required=True, help="e.g. BEN TGO")
    p.add_argument("--speed-table", default=SPEED_TABLE)
    p.add_argument("--buffer-m", type=float, default=BUFFER_M)
    p.add_argument("--max-overlap", type=float, default=MAX_OVERLAP)
    p.add_argument("--min-len-m", type=float, default=MIN_LEN_M)
    p.add_argument("--ml-speed", type=float, default=ML_SPEED)
    p.add_argument("--res-m", type=float, default=RES_M)
    p.add_argument("--template", help="raster whose grid the output should copy")
    p.add_argument("--crs", help="metric CRS (default: UTM zone estimated from OSM)")
    p.add_argument("--out-dir", default="output")
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    table = load_speed_table(a.speed_table)

    osm = read_osm_roads(a.osm_pbf, table)
    ms = read_ms_roads(a.ms_roads, a.iso3)
    print(f"OSM segments: {len(osm):,}  |  ML segments ({' '.join(a.iso3)}): {len(ms):,}")

    crs = a.crs or osm.estimate_utm_crs()
    osm, ms = osm.to_crs(crs), ms.to_crs(crs)

    if a.osm_pbf_t1:
        osm_t1 = read_osm_roads(a.osm_pbf_t1, table).to_crs(crs)
        osm["new_since_t1"] = flag_new_roads(osm, osm_t1, a.buffer_m, a.max_overlap)
        print(f"OSM segments new since t1: {int(osm['new_since_t1'].sum()):,}")

    ms_new = conflate(ms, osm, a.buffer_m, a.max_overlap, a.min_len_m, a.ml_speed)
    print(f"ML segments kept (not in OSM): {len(ms_new):,} of {len(ms):,}")

    roads = gpd.GeoDataFrame(pd.concat([osm, ms_new], ignore_index=True),
                             geometry="geometry", crs=crs)
    roads.to_file(out / "roads_merged.gpkg", layer="roads", driver="GPKG")
    summarize(roads).to_csv(out / "road_length_summary.csv", index=False)
    rasterize_speed(roads, out / "road_speed_kmh.tif", a.res_m, a.template)
    print(f"Saved outputs to {out}/")
    return roads


if __name__ == "__main__":
    main()
