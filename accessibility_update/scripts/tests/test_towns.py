"""Smoke test of run_towns_benin.py on synthetic outputs of the earlier steps."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import friction as fr  # noqa: E402
import run_towns_benin as towns  # noqa: E402
from test_traveltime import _ghsl, _grid, LONLAT  # noqa: E402


def test_towns(tmp_path):
    root = tmp_path
    data = root / "data"
    data.mkdir()
    for k in ("roads", "friction", "traveltime"):
        (root / "output" / k).mkdir(parents=True)

    # nine 0.03 x 0.03 degree "communes" on a 3 x 3 layout
    w, s = LONLAT[0] + 0.005, LONLAT[1] + 0.005
    polys = [box(w + 0.032 * (i % 3), s + 0.032 * (i // 3),
                 w + 0.032 * (i % 3) + 0.03, s + 0.032 * (i // 3) + 0.03) for i in range(9)]
    gpd.GeoDataFrame({"shapeName": list(towns.TOWNS.values())}, geometry=polys, crs=4326) \
        .to_file(data / "geoBoundaries-BEN-ADM2.geojson", driver="GeoJSON")

    paths, _ = _ghsl(tmp_path)
    for y in (2020, 2025):
        (data / towns.POP.format(y=y)).write_bytes(paths["pop"].read_bytes())

    # roads: one E-W line per commune row; the northern one is new, plus an ML road
    lines = [LineString([(LONLAT[0], s + 0.015 + 0.032 * r), (LONLAT[2], s + 0.015 + 0.032 * r)])
             for r in range(3)]
    roads = gpd.GeoDataFrame({"source": ["osm", "osm", "osm", "microsoft"],
                              "new_since_t1": [False, False, True, None],
                              "speed": [70.0, 40.0, 40.0, 15.0]},
                             geometry=lines + [LineString([(w + 0.01, s), (w + 0.01, s + 0.09)])],
                             crs=4326).to_crs(towns.CRS)
    osm1 = gpd.GeoDataFrame({"gone_by_t2": [False, False]}, geometry=lines[:2],
                            crs=4326).to_crs(towns.CRS)
    gpkg = root / "output" / "roads" / "roads_merged.gpkg"
    roads.to_file(gpkg, layer="roads", driver="GPKG")
    osm1.to_file(gpkg, layer="osm_t1", driver="GPKG")

    g = _grid()
    f1 = np.full(g.shape, 0.06 / 4, dtype="float32")
    f2 = f1.copy(); f2[10:12, :] = 0.06 / 40
    fr.write_tif(root / "output" / "friction" / "friction_t1.tif", f1, g)
    fr.write_tif(root / "output" / "friction" / "friction_t2.tif", f2, g)
    for scen in towns.SCENARIOS:
        for layer in towns.LAYERS:
            a = np.full(g.shape, 60.0 if scen == "2020" else 48.0, dtype="float32")
            fr.write_tif(root / "output" / "traveltime" / f"traveltime_{scen}_{layer}.tif", a, g)
    fr.write_tif(root / "output" / "traveltime" / "traveltime_change_2026r_minus_2020_city6.tif",
                 np.full(g.shape, -5, dtype="float32"), g)

    summary, long = towns.main(root)
    res = root / "results" / "towns"
    assert summary["town"].tolist() == list(towns.TOWNS)
    assert len(long) == 9 * 4 * 4
    assert (summary["osm_2026_km"] >= summary["osm_2020_km"]).all()
    assert (summary["osm_new_km"] > 0).sum() == 3                # northern row of communes
    has_pop = summary["pop_2020"] > 0
    assert (summary.loc[has_pop, "tt_city6_change_roads_min"] == -12).all()
    assert summary.loc[~has_pop, "tt_city6_2020_min"].isna().all()   # no people -> no mean
    for f in ["town_summary.csv", "town_traveltime.csv", "overview_city6.png",
              "map_Parakou.png", "map_Come.png", "map_Sakete.png"]:
        assert (res / f).exists(), f
