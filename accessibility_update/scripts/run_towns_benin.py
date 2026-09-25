"""
Per-town results for nine Beninese communes, from the outputs of
run_roads_benin_togo.py, run_friction_benin_togo.py and run_traveltime_benin_togo.py.

Each town is summarised over its commune (geoBoundaries gbOpen BEN ADM2):
  - roads (km): OSM 2020, OSM 2026, new since 2020, 2020 roads gone by 2026,
    Microsoft ML gap-fill; road density
  - population (GHS-POP 2020 and 2025)
  - friction: share of cells faster in 2026 than in 2020
  - travel time for each scenario (2020, 2026r, 2026, 2026ml) and layer
    (city6, city9, port2, port5): population-weighted mean, share of people
    within 30 / 60 / 120 min
plus one map per town and an overview chart.

Expects data/geoBoundaries-BEN-ADM2.geojson and the GHS-POP zips in data/.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from rasterio.windows import from_bounds
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

import friction as fr
import traveltime as tt

ROOT = Path(__file__).resolve().parents[1]
CRS = 32631
# display name -> geoBoundaries shapeName
TOWNS = {"Parakou": "Parakou", "Kandi": "Kandi", "Malanville": "Malanville",
         "Cotonou": "Cotonou", "Porto-Novo": "Porto-Novo", "Comè": "Come",
         "Sakété": "Sakete", "Natitingou": "Natitingou", "Djougou": "Djougou"}
SCENARIOS = {"2020": ("t1", 2020), "2026r": ("t2", 2020),
             "2026": ("t2", 2025), "2026ml": ("t2_ml", 2025)}
LAYERS = ["city6", "city9", "port2", "port5"]
POP = "GHS_POP_E{y}_GLOBE_R2023A_54009_1000_V1_0.zip"
# reference categorical palette (slots 1-2) and neutral ink
BLUE, ORANGE, GREY, INK = "#2a78d6", "#eb6834", "#9a9a96", "#52514e"


def flag(s):
    """0/1, True/False or "True"/"False" (older GeoPackages) -> bool; missing -> False."""
    s = s.replace({"True": 1, "False": 0, True: 1, False: 0})
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(bool)


def km(g):
    return float(g.length.sum() / 1000)


def clip(g, poly):
    return g.iloc[g.sindex.query(poly, predicate="intersects")].clip(poly)


def commune_zones(communes, grid):
    """Raster of commune ids (1..n, 0 = outside) on the friction grid."""
    return rasterize(((geom, i + 1) for i, geom in enumerate(communes.geometry)),
                     out_shape=grid.shape, transform=grid.transform, fill=0, dtype="int16")


def weighted(tt_arr, people, zone):
    ok = zone & (tt_arr != fr.NODATA)
    w = people[ok]
    if w.sum() == 0:
        return {"pop_mean_min": np.nan, "share_30": np.nan, "share_60": np.nan,
                "share_120": np.nan}
    t = tt_arr[ok]
    return {"pop_mean_min": round(float((t * w).sum() / w.sum()), 1),
            **{f"share_{m}": round(float(w[t <= m].sum() / w.sum()), 3) for m in (30, 60, 120)}}


def town_map(name, poly, roads, out, path):
    xmin, ymin, xmax, ymax = poly.buffer(2000).bounds
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    ax = axes[0]
    r2 = clip(roads, poly)
    osm_old = r2[(r2["source"] == "osm") & ~flag(r2["new_since_t1"])]
    osm_new = r2[(r2["source"] == "osm") & flag(r2["new_since_t1"])]
    ml = r2[r2["source"] == "microsoft"]
    for g, c, lw, lab in [(osm_old, GREY, 0.6, "OSM 2020"), (osm_new, BLUE, 0.9, "OSM new by 2026"),
                          (ml, ORANGE, 0.9, "Microsoft gap-fill")]:
        if len(g):
            g.plot(ax=ax, color=c, lw=lw, label=lab)
    gpd.GeoSeries([poly], crs=CRS).boundary.plot(ax=ax, color=INK, lw=1)
    ax.legend(loc="lower left", fontsize=7, frameon=False)
    ax.set_title("roads")
    panels = [(out["traveltime"] / "traveltime_2026_city6.tif", "minutes to city ≥ 50k, 2026",
               dict(cmap="Blues", vmin=0, vmax=120)),
              (out["traveltime"] / "traveltime_change_2026r_minus_2020_city6.tif",
               "change due to new roads (min)",
               dict(cmap="RdBu_r", norm=TwoSlopeNorm(0, vmin=-30, vmax=30)))]
    for ax, (tif, title, kw) in zip(axes[1:], panels):
        with rasterio.open(tif) as r:
            win = from_bounds(xmin, ymin, xmax, ymax, r.transform)
            a = r.read(1, window=win, masked=True, boundless=True)
            ext = rasterio.windows.bounds(win, r.transform)
        im = ax.imshow(a, extent=(ext[0], ext[2], ext[1], ext[3]), interpolation="nearest", **kw)
        gpd.GeoSeries([poly], crs=CRS).boundary.plot(ax=ax, color=INK, lw=1)
        fig.colorbar(im, ax=ax, shrink=0.75)
        ax.set_title(title)
    for ax in axes:
        ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"{name} (commune)")
    fig.savefig(path, dpi=100, bbox_inches="tight"); plt.close(fig)


def overview_chart(tt_long, path):
    d = tt_long[(tt_long["layer"] == "city6") & tt_long["scenario"].isin(["2020", "2026"])]
    d = d.pivot(index="town", columns="scenario", values="pop_mean_min").sort_values("2020")
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(7, 0.5 * len(d) + 1.2))
    h = 0.38
    for off, col, c in [(-h / 2, "2020", BLUE), (h / 2, "2026", ORANGE)]:
        ax.barh(y + off, d[col], height=h - 0.04, color=c, label=col)
        for yi, v in zip(y + off, d[col]):
            ax.text(v + 0.3, yi, f"{v:.0f}", va="center", fontsize=7, color=INK)
    ax.set_yticks(y, d.index)
    ax.set_xlabel("population-weighted mean travel time to a city ≥ 50,000 (min)", color=INK)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#e6e6e3", lw=0.6); ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right")
    fig.savefig(path, dpi=110, bbox_inches="tight"); plt.close(fig)


def main(root=ROOT):
    data = root / "data"
    out = {k: root / "output" / k for k in ("roads", "friction", "traveltime")}
    res = root / "results" / "towns"
    res.mkdir(parents=True, exist_ok=True)

    adm = gpd.read_file(data / "geoBoundaries-BEN-ADM2.geojson")
    communes = adm.set_index("shapeName").loc[list(TOWNS.values())].reset_index()
    communes.insert(0, "town", list(TOWNS))
    communes = communes.to_crs(CRS)

    roads = gpd.read_file(out["roads"] / "roads_merged.gpkg", layer="roads").to_crs(CRS)
    osm1 = gpd.read_file(out["roads"] / "roads_merged.gpkg", layer="osm_t1").to_crs(CRS)

    grid = fr.Grid.from_raster(out["friction"] / "friction_t1.tif")
    zones = commune_zones(communes, grid)
    people = {y: tt.population_on_grid(data / POP.format(y=y), grid) for y in (2020, 2025)}
    with rasterio.open(out["friction"] / "friction_t1.tif") as a, \
            rasterio.open(out["friction"] / "friction_t2.tif") as b:
        f1, f2 = a.read(1), b.read(1)

    rows, long = [], []
    for i, c in communes.iterrows():
        zone = zones == i + 1
        area = c.geometry.area / 1e6
        r2, o1 = clip(roads, c.geometry), clip(osm1, c.geometry)
        osm2 = r2[r2["source"] == "osm"]
        valid = zone & (f1 != fr.NODATA) & (f2 != fr.NODATA)
        row = {"town": c["town"], "area_km2": round(area, 1),
               "pop_2020": round(float(people[2020][zone].sum())),
               "pop_2025": round(float(people[2025][zone].sum())),
               "osm_2020_km": round(km(o1), 1), "osm_2026_km": round(km(osm2), 1),
               "osm_new_km": round(km(osm2[flag(osm2["new_since_t1"])]), 1),
               "osm_gone_km": round(km(o1[flag(o1["gone_by_t2"])]), 1),
               "ml_kept_km": round(km(r2[r2["source"] == "microsoft"]), 1),
               "share_cells_faster_2026": round(float((f2[valid] < f1[valid]).mean()), 4)
               if valid.any() else np.nan}
        row["density_2020_km_per_km2"] = round(row["osm_2020_km"] / area, 2)
        row["density_2026ml_km_per_km2"] = round((row["osm_2026_km"] + row["ml_kept_km"]) / area, 2)
        for scen, (_, y) in SCENARIOS.items():
            for layer in LAYERS:
                with rasterio.open(out["traveltime"] / f"traveltime_{scen}_{layer}.tif") as r:
                    w = weighted(r.read(1), people[y], zone)
                long.append({"town": c["town"], "scenario": scen, "layer": layer, **w})
                if layer == "city6":
                    row[f"tt_city6_{scen}_min"] = w["pop_mean_min"]
        rows.append(row)
        town_map(c["town"], c.geometry, roads, out,
                 res / f"map_{c['town'].replace('è', 'e').replace('é', 'e')}.png")

    summary = pd.DataFrame(rows)
    summary["tt_city6_change_roads_min"] = summary["tt_city6_2026r_min"] - summary["tt_city6_2020_min"]
    summary["tt_city6_change_total_min"] = summary["tt_city6_2026_min"] - summary["tt_city6_2020_min"]
    summary.to_csv(res / "town_summary.csv", index=False)
    tt_long = pd.DataFrame(long)
    tt_long.to_csv(res / "town_traveltime.csv", index=False)
    overview_chart(tt_long, res / "overview_city6.png")
    print(summary.to_string(index=False))
    return summary, tt_long


if __name__ == "__main__":
    main()
