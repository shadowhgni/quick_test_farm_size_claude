"""Offline tests for traveltime.py on synthetic friction, GHSL and port data."""
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import friction as fr  # noqa: E402
import traveltime as tt  # noqa: E402

LONLAT = (2.40, 6.40, 2.50, 6.50)
UTM = "EPSG:32631"
MOLL = "ESRI:54009"


def _grid(res=100):
    return fr.Grid.from_bounds(LONLAT, UTM, res)


def test_city_class_breaks():
    pops = [4999, 5000, 9999, 10000, 49999, 50000, 99999, 1e6, 5e6, 6e7]
    assert tt.city_class(pops).tolist() == [0, 9, 9, 8, 7, 6, 6, 2, 1, 0]


def test_select_cumulative_exact_and_any_port():
    d = gpd.GeoDataFrame({"size_class": [2, 6, 7, 9, 0]}, geometry=[Point(0, 0)] * 5)
    assert tt.select(d, 6)["size_class"].tolist() == [2, 6]
    assert tt.select(d, 6, exact=True)["size_class"].tolist() == [6]
    assert len(tt.select(d, 5, to="port")) == 5


def test_travel_time_uniform_and_barrier():
    g = _grid()
    f = np.full(g.shape, 0.06 / 6, dtype="float32")        # 6 km/h -> 0.01 min/m
    targets = np.zeros(g.shape, bool)
    targets[50, 20] = True
    t = tt.travel_time(f, g, targets)
    assert t[50, 30] == pytest.approx(10.0)                  # 1 km east = 10 min
    assert t[60, 30] == pytest.approx(10 * np.sqrt(2), rel=1e-4)   # diagonal
    f[:, 40] = fr.NODATA                                     # wall, no gap
    t = tt.travel_time(f, g, targets)
    assert t[50, 45] == fr.NODATA and t[50, 39] > 0


def test_target_snaps_port_off_water():
    g = _grid()
    passable = np.ones(g.shape, bool)
    passable[:, :30] = False                                 # "sea" in the west
    x, y = rasterio.transform.xy(g.transform, 50, 20)        # port 10 cells offshore
    port = gpd.GeoDataFrame({"size_class": [2]}, geometry=[Point(x, y)], crs=UTM)
    cells = tt.target_cells(port, g, passable)
    assert np.argwhere(cells).tolist() == [[50, 30]]         # nearest land cell


def _ghsl(tmp_path):
    """1 km SMOD + POP in Mollweide: a town of 60,000 (4 cells, one linked only
    diagonally) and a cluster of 3,000 (tests the class-0 path; real urban clusters
    have >= 5,000 people unless clipped at the window edge)."""
    w, s, e, n = transform_bounds(4326, MOLL, *LONLAT)
    x0, y0 = np.floor(w / 1000) * 1000, np.ceil(n / 1000) * 1000
    h, wd = int(np.ceil((y0 - s) / 1000)), int(np.ceil((e - x0) / 1000))
    smod = np.full((h, wd), 11, "uint8")
    pop = np.zeros((h, wd), "float32")
    for r, c in [(3, 3), (3, 4), (4, 4), (5, 5)]:            # (5,5) joins diagonally
        smod[r, c], pop[r, c] = 30, 15000
    smod[8, 8], pop[8, 8] = 21, 3000
    tr = from_origin(x0, y0, 1000, 1000)
    paths = {}
    for name, arr, dt in [("smod", smod, "uint8"), ("pop", pop, "float32")]:
        tif = tmp_path / f"GHS_{name}.tif"
        with rasterio.open(tif, "w", driver="GTiff", height=h, width=wd, count=1,
                           dtype=dt, crs=MOLL, transform=tr) as d:
            d.write(arr, 1)
        z = tmp_path / f"GHS_{name}.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.write(tif, tif.name)
        paths[name] = z
    return paths, pop.sum()


def test_settlements_from_ghsl(tmp_path):
    paths, _ = _ghsl(tmp_path)
    s = tt.settlements_from_ghsl(paths["smod"], paths["pop"], LONLAT)
    assert sorted(s["pop"].tolist()) == [3000, 60000]
    assert sorted(s["size_class"].tolist()) == [0, 6]


def test_population_on_grid_preserves_total(tmp_path):
    paths, total = _ghsl(tmp_path)
    g = fr.Grid.from_bounds((2.38, 6.38, 2.52, 6.52), UTM, 100)   # covers all 1 km cells
    people = tt.population_on_grid(paths["pop"], g)
    assert people.sum() == pytest.approx(total, rel=0.03)


def test_main_two_dates(tmp_path):
    paths, _ = _ghsl(tmp_path)
    g = _grid()
    slow = np.full(g.shape, 0.06 / 4, dtype="float32")           # 4 km/h everywhere
    fast = slow.copy()
    fast[45:48, :] = 0.06 / 60                                    # a new E-W road
    for name, arr in [("f1.tif", slow), ("f2.tif", fast)]:
        fr.write_tif(tmp_path / name, arr, g)
    pd.DataFrame({"Main Port Name": ["P"], "Country Code": ["Benin"],
                  "Harbor Size": ["Medium"], "Latitude": [6.41], "Longitude": [2.41]}) \
        .to_csv(tmp_path / "wpi.csv", index=False)
    out = tmp_path / "out"
    s = tt.main(["--friction", str(tmp_path / "f1.tif"), str(tmp_path / "f2.tif"),
                 "--labels", "2020", "2026",
                 "--smod", str(paths["smod"]), "--pop", str(paths["pop"]),
                 "--ports", str(tmp_path / "wpi.csv"),
                 "--city-sizes", "6", "9", "--port-sizes", "2", "--out-dir", str(out)])
    assert set(s["layer"]) == {"city6", "city9", "port2"}
    c6 = s[s["layer"] == "city6"].set_index("date")
    assert c6.loc["2026", "pop_weighted_mean_min"] <= c6.loc["2020", "pop_weighted_mean_min"]
    assert (c6["n_destinations"] == 1).all()
    with rasterio.open(out / "traveltime_change_2026_minus_2020_city6.tif") as r:
        d = r.read(1, masked=True)
    assert d.max() <= 1e-4 and d.min() < 0                       # only faster
    assert (out / "cities_2020.gpkg").exists() and (out / "ports_2026.gpkg").exists()


def test_benin_togo_driver(tmp_path, monkeypatch):
    """run_traveltime_benin_togo.py end to end on synthetic inputs."""
    import run_traveltime_benin_togo as rtb

    paths, _ = _ghsl(tmp_path)
    data, fric = tmp_path / "data", tmp_path / "fric"
    data.mkdir(); fric.mkdir()
    for y in (2020, 2025):
        (data / rtb.SMOD.format(y=y)).write_bytes(paths["smod"].read_bytes())
        (data / rtb.POP.format(y=y)).write_bytes(paths["pop"].read_bytes())
    g = _grid()
    base = np.full(g.shape, 0.06 / 4, dtype="float32")
    for name, rows in [("t1", []), ("t2", [45]), ("t2_ml", [45, 60])]:
        f = base.copy()
        for r in rows:
            f[r:r + 2, :] = 0.06 / 50
        fr.write_tif(fric / f"friction_{name}.tif", f, g)
    pd.DataFrame({"Main Port Name": ["A", "B"], "Country Code": ["Benin", "Togo"],
                  "Harbor Size": ["Medium", None], "Latitude": [6.41, 6.49],
                  "Longitude": [2.41, 2.49]}).to_csv(data / "UpdatedPub150.csv", index=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rtb, "DATA", data)
    monkeypatch.setattr(rtb, "FRIC", fric)
    rtb.main()
    res = tmp_path / "results_traveltime_benin_togo"
    s = pd.read_csv(res / "traveltime_summary.csv")
    assert len(s) == 4 * 4                                  # 4 scenarios x 4 layers
    p5 = s[s["layer"] == "port5"].set_index("date")
    p2 = s[s["layer"] == "port2"].set_index("date")
    assert (p5["n_destinations"] == 2).all() and (p2["n_destinations"] == 1).all()
    c6 = s[s["layer"] == "city6"].set_index("date")["pop_weighted_mean_min"]
    assert c6["2026ml"] <= c6["2026"] <= c6["2026r"] <= c6["2020"]
    for f in ["traveltime_city6.png", "traveltime_city6_change.png", "settlements_by_class.csv"]:
        assert (res / f).exists()
