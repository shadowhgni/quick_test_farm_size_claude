"""
Benin + Togo test run of merge_roads.py (run by .github/workflows/roads_merge.yml).

Expects in data/:
  benin-200101.osm.pbf  togo-200101.osm.pbf   (t1, Geofabrik yearly snapshot)
  benin-260901.osm.pbf  togo-260901.osm.pbf   (t2)
  Western_Africa.zip                          (Microsoft drop 2025.04.28)

Writes small, committable QA outputs to results_benin_togo/ and large ones
(gpkg, tif) to output_benin_togo/.
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import merge_roads as mr

DATA, RES, OUT = Path("data"), Path("results_benin_togo"), Path("output_benin_togo")
CRS = 32631                     # UTM 31N covers Benin and nearly all of Togo
T1, T2 = "200101", "260901"
OSM_EXT = ".osm.pbf"            # tests swap in ".osm" (XML) files
COUNTRY = {"benin": "BEN", "togo": "TGO"}
# 10 x 10 km QA windows (lon, lat): two towns and two rural areas
WINDOWS = {"Parakou_BEN": (2.63, 9.35), "Kandi_rural_BEN": (2.94, 11.13),
           "Kara_TGO": (1.19, 9.55), "Dapaong_rural_TGO": (0.20, 10.86)}


def osm_for(stamp, table):
    pbfs = [str(DATA / f"{c}-{stamp}{OSM_EXT}") for c in COUNTRY]
    g = mr.read_osm_roads(pbfs, table)
    g["iso3"] = g["extract"].str.split("-").str[0].map(COUNTRY)
    return g.to_crs(CRS)


def v00_overlap(ms_geoms, osm_geoms, buffer_m):
    """The original v00 algorithm, kept verbatim for comparison."""
    osm_buf = shapely.buffer(osm_geoms, buffer_m)
    ms_idx, osm_idx = shapely.STRtree(osm_buf).query(ms_geoms, predicate="intersects")
    overlap = np.zeros(len(ms_geoms))
    for m, grp in pd.DataFrame({"ms": ms_idx, "osm": osm_idx}).groupby("ms"):
        local = shapely.union_all(osm_buf[grp["osm"].values])
        overlap[m] = ms_geoms[m].intersection(local).length / ms_geoms[m].length
    return overlap


def km(g):
    return g.length.sum() / 1000


def qa_map(name, lonlat, osm, ms_all, path):
    c = gpd.GeoSeries(gpd.points_from_xy([lonlat[0]], [lonlat[1]]), crs=4326).to_crs(CRS)[0]
    box = shapely.box(c.x - 5000, c.y - 5000, c.x + 5000, c.y + 5000)
    o, m = osm.clip(box), ms_all.clip(box)
    fig, ax = plt.subplots(figsize=(6, 6))
    if len(o):
        o[~o.get("new_since_t1", False)].plot(ax=ax, color="#444444", lw=1.2, label=f"OSM {T1}")
        o[o.get("new_since_t1", False)].plot(ax=ax, color="#1f77b4", lw=1.2, label=f"OSM new by {T2}")
    kept = m[m["osm_overlap"] <= mr.MAX_OVERLAP]
    if len(kept):
        kept.plot(ax=ax, color="#d62728", lw=1, label="ML kept (gap-fill)")
    if len(m) - len(kept):
        m[m["osm_overlap"] > mr.MAX_OVERLAP].plot(ax=ax, color="#ff9896", lw=0.6, ls=":",
                                                  label="ML dropped (in OSM)")
    ax.set_xlim(box.bounds[0], box.bounds[2]); ax.set_ylim(box.bounds[1], box.bounds[3])
    ax.set_title(f"{name}  (10 x 10 km)"); ax.set_xticks([]); ax.set_yticks([])
    if ax.get_legend_handles_labels()[0]:
        ax.legend(loc="lower left", fontsize=7)
    fig.savefig(path, dpi=110, bbox_inches="tight"); plt.close(fig)


def main():
    RES.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    log = []
    say = lambda s: (print(s), log.append(s))
    table = mr.load_speed_table()

    t = time.time()
    osm2, osm1 = osm_for(T2, table), osm_for(T1, table)
    ms = mr.read_ms_roads(DATA / "Western_Africa.zip", list(COUNTRY.values())).to_crs(CRS)
    say(f"read inputs: {time.time() - t:.0f}s | OSM {T1}: {len(osm1):,} segs, "
        f"OSM {T2}: {len(osm2):,} segs, ML: {len(ms):,} segs")

    # --- 1. new OSM roads between snapshots
    t = time.time()
    osm2["new_since_t1"] = mr.flag_new_roads(osm2, osm1)
    say(f"flag new roads: {time.time() - t:.0f}s")

    # --- 2. conflation (new method) and comparison with v00
    ms = ms.explode(index_parts=False)
    ms = ms[ms.length >= mr.MIN_LEN_M].reset_index(drop=True)
    t = time.time()
    ms["osm_overlap"] = mr.overlap_fraction(ms.geometry.values, osm2.geometry.values, mr.BUFFER_M)
    t_new = time.time() - t
    t = time.time()
    ov_old = v00_overlap(ms.geometry.values, osm2.geometry.values, mr.BUFFER_M)
    t_old = time.time() - t
    keep_new, keep_old = ms["osm_overlap"] <= mr.MAX_OVERLAP, ov_old <= mr.MAX_OVERLAP
    differ = keep_new != keep_old
    say(f"conflation time: new {t_new:.0f}s vs v00 {t_old:.0f}s")
    say(f"keep/drop decisions differing from v00: {differ.sum():,} of {len(ms):,} "
        f"({km(ms[differ]):.0f} km of {km(ms):.0f} km)")
    ms.drop(columns="geometry").assign(osm_overlap_v00=ov_old).describe().round(3) \
      .to_csv(RES / "ml_overlap_describe.csv")

    # --- 3. sensitivity of kept ML length to BUFFER_M and MAX_OVERLAP
    rows = []
    for b in [10, 15, 20, 30, 40]:
        ov = ms["osm_overlap"].values if b == mr.BUFFER_M else \
            mr.overlap_fraction(ms.geometry.values, osm2.geometry.values, b)
        for mo in [0.3, 0.5, 0.7]:
            k = ov <= mo
            for iso in COUNTRY.values():
                sel = k & (ms["iso3"] == iso).values
                rows.append({"iso3": iso, "buffer_m": b, "max_overlap": mo,
                             "ml_kept_km": round(km(ms[sel]), 1),
                             "ml_kept_share": round(km(ms[sel]) / km(ms[ms["iso3"] == iso]), 3)})
    pd.DataFrame(rows).to_csv(RES / "sensitivity_buffer_overlap.csv", index=False)

    # --- 4. merged network + summaries
    ms_new = ms[keep_new].assign(highway="ml_detected", surface=None,
                                 speed=float(mr.ML_SPEED), source="microsoft")
    roads = gpd.GeoDataFrame(pd.concat([osm2, ms_new], ignore_index=True),
                             geometry="geometry", crs=CRS)
    roads.assign(length_km=roads.length / 1000) \
         .groupby(["iso3", "source", "highway", "new_since_t1"], dropna=False)["length_km"] \
         .sum().round(1).reset_index().to_csv(RES / "road_length_by_class.csv", index=False)

    s = []
    for iso in COUNTRY.values():
        o1, o2 = osm1[osm1["iso3"] == iso], osm2[osm2["iso3"] == iso]
        m_all, m_new = ms[ms["iso3"] == iso], ms_new[ms_new["iso3"] == iso]
        s.append({"iso3": iso, f"osm_{T1}_km": km(o1), f"osm_{T2}_km": km(o2),
                  "osm_new_since_t1_km": km(o2[o2["new_since_t1"]]),
                  "ml_total_km": km(m_all), "ml_kept_km": km(m_new),
                  "merged_km": km(o2) + km(m_new),
                  "ml_kept_median_width_m": m_new["width_m"].median(),
                  "ml_dropped_median_width_m": m_all.loc[~keep_new[m_all.index], "width_m"].median()})
    summary = pd.DataFrame(s).round(1)
    summary.to_csv(RES / "summary_by_country.csv", index=False)
    say("\n" + summary.to_string(index=False))

    # --- 5. outputs
    t = time.time()
    roads.to_file(OUT / "roads_merged.gpkg", layer="roads", driver="GPKG")
    mr.rasterize_speed(roads, OUT / "road_speed_kmh.tif", res_m=mr.RES_M)
    say(f"write gpkg + tif: {time.time() - t:.0f}s")
    for name, ll in WINDOWS.items():
        qa_map(name, ll, osm2, ms, RES / f"qa_{name}.png")
    (RES / "run_log.txt").write_text("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
