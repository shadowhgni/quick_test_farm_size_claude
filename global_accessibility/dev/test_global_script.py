"""Offline tests of global_accessibility.py on synthetic data.

Run:  python -m pytest global_accessibility/dev -q
"""
import json
import math
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Polygon, box

os.environ.setdefault("GA_WORK_DIR", tempfile.mkdtemp(prefix="ga_test_"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import global_accessibility as ga  # noqa: E402
import geodijkstra as gd  # noqa: E402

D = 1 / 120


def test_grid_snapping_window_and_area():
    g = ga.Grid((0.004, 6.004, 2.996, 8.996), D)
    assert (g.west, g.south, g.east, g.north) == pytest.approx((0.0, 6.0, 3.0, 9.0))
    assert g.shape == (360, 360) and not g.wrap
    assert g.window_of((1.0, 7.0, 2.0, 8.0)) == (120, 120, 120, 120)
    assert g.window_of((10, 10, 11, 11)) is None
    glob = ga.Grid(ga.NELSON_EXTENT, D)
    assert glob.shape == (17400, 43200) and glob.wrap
    band = 2 * math.pi * ga.R_EARTH ** 2 * (math.sin(math.radians(85)) - math.sin(math.radians(-60)))
    assert glob.cell_area_m2().sum() * glob.width == pytest.approx(band, rel=1e-9)


def test_travel_time_same_as_dev_module():
    rng = np.random.default_rng(3)
    g = ga.Grid((10, 40, 12, 42), D)
    f = rng.uniform(0.001, 0.03, g.shape).astype(np.float32)
    f[100:120, :200] = np.inf
    src = np.zeros(g.shape, bool); src[5, 5] = True; src[200, 180] = True
    a = ga.travel_time(f, np.flatnonzero(src), g)
    b = gd.travel_time(f, src, g.north, D, D)
    assert np.array_equal(np.isfinite(a), np.isfinite(b))
    assert np.allclose(a[np.isfinite(a)], b[np.isfinite(b)], rtol=1e-6)


def test_road_speed_and_lengths():
    hw = pd.Series(["primary", "tertiary", "track", "tertiary"])
    tags = pd.Series([None, None, '"surface"=>"asphalt"', '"surface"=>"dirt","lanes"=>"2"'])
    sp, _ = ga.road_speed(hw, tags)
    assert sp.tolist() == [70, 40 * 0.7, 15, 40 * 0.7]
    km = ga.line_lengths_km(np.array([LineString([(0, 0), (1, 0)]), LineString([(0, 60), (1, 60)])]))
    assert km[0] == pytest.approx(111.195, rel=1e-3) and km[1] == pytest.approx(km[0] / 2, rel=1e-3)


def _countries():
    return gpd.GeoDataFrame({
        "cid": np.array([1, 2, 3], np.int16), "iso3": ["AAA", "BBB", "EEE"],
        "ADM0_A3": ["AAA", "BBB", "EEE"], "NAME": ["A", "B", "E"],
        "CONTINENT": ["Africa", "Africa", "Europe"]},
        geometry=[box(0, 6, 1, 7), box(1, 6, 2, 7), box(2, 6, 3, 7)], crs=4326)


def test_african_borders_only_between_african_countries():
    b = ga.african_borders(_countries())
    assert len(b) == 1 and {b.iso3_a[0], b.iso3_b[0]} == {"AAA", "BBB"}
    assert b.geometry[0].length == pytest.approx(1.0)


OSM = """<?xml version="1.0"?><osm version="0.6">
<node id="1" lat="6.5" lon="0.5"/><node id="2" lat="6.5" lon="1.5"/>
<node id="3" lat="6.2" lon="0.5"/><node id="4" lat="6.2" lon="1.5"/>
<node id="5" lat="6.8" lon="1.5"/><node id="6" lat="6.8" lon="2.5"/>
<way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="primary"/></way>
<way id="11"><nd ref="3"/><nd ref="4"/><tag k="highway" v="track"/></way>
<way id="12"><nd ref="5"/><nd ref="6"/><tag k="highway" v="trunk"/></way>
</osm>"""


def test_roads_job_rasterizes_and_finds_checkpoints(tmp_path):
    (tmp_path / "x.osm").write_text(OSM)
    ga.african_borders(_countries()).to_file(tmp_path / "b.gpkg", driver="GPKG")
    g = ga.Grid((0, 6, 3, 7), D)
    s = ga.roads_job({"pbf": str(tmp_path / "x.osm"), "out": str(tmp_path / "x.npz"),
                      "grid": g.to_dict(), "borders": str(tmp_path / "b.gpkg"), "bytes": 1})
    assert s["segments"] == 3
    # only the primary road crosses the A-B border (the track is minor, the trunk
    # crosses into Europe, which is not penalized)
    assert [c[4] for c in s["checkpoints"]] == ["primary"]
    assert s["checkpoints"][0][0] == pytest.approx(1.0)
    d = np.load(tmp_path / "x.npz")
    assert d["speed"].max() == 80 and (d["speed"] == 70).any()


def test_corruption_and_border_delay(tmp_path):
    work = tmp_path; dl = tmp_path / "downloads"; dl.mkdir()
    _countries().drop(columns="geometry").to_csv(work / "countries.csv", index=False)
    pd.DataFrame({"iso3": ["AAA", "AAA", "BBB"], "year": [2019, 2021, 2019],
                  "score": [40.0, 60.0, 20.0]}).to_csv(dl / "wgi_control_of_corruption.csv", index=False)
    ctx = {"dl": dl, "work": work, "grid": ga.Grid((0, 6, 3, 7), D)}
    t = ga.corruption_table(ctx, 2020).set_index("iso3")
    assert t.loc["AAA", "score"] == 40 and t.loc["AAA", "wgi_year"] == 2019   # latest <= 2020
    assert t.loc["AAA", "road_speed_factor"] == pytest.approx(1 - 0.1 * 0.6)
    assert t.loc["EEE", "score_source"] == "continent median"
    pd.DataFrame([{"year": 2020, "lon": 1.0, "lat": 6.5, "iso3_a": "AAA", "iso3_b": "BBB",
                   "highway": "primary"}] * 2).to_csv(work / "checkpoints_raw.csv", index=False)
    cp = ga.checkpoint_cells(ctx, 2020, t.reset_index())
    assert len(cp) == 1                                                         # de-duplicated
    assert cp.delay_min.iloc[0] == pytest.approx(15 / (1 - 0.1 * (0.6 + 0.8) / 2))


def test_nearest_epoch():
    assert [ga.nearest_epoch(y) for y in (2015, 2020, 2023, 2026, 2031)] == [2015, 2020, 2025, 2025, 2030]


def _ghsl_zip(tmp, name, arr, dtype, tr):
    tif = tmp / f"{name}.tif"
    with rasterio.open(tif, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
                       dtype=dtype, crs="ESRI:54009", transform=tr) as d:
        d.write(arr.astype(dtype), 1)
    z = tmp / "downloads" / "ghsl" / f"{name}.zip"
    z.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(tif, tif.name)


def test_settlements_epoch(tmp_path):
    from rasterio.warp import transform_bounds
    g = ga.Grid((1.0, 6.0, 2.0, 7.0), D)
    w, s, e, n = transform_bounds(4326, "ESRI:54009", 0.5, 5.5, 2.5, 7.5)
    x0, y0 = math.floor(w / 1000) * 1000, math.ceil(n / 1000) * 1000
    H, W = int((y0 - s) / 1000) + 1, int((e - x0) / 1000) + 1
    smod = np.full((H, W), 11); pop = np.zeros((H, W))
    r, c = H // 2, W // 2
    for dr, dc in [(0, 0), (0, 1), (1, 2)]:           # one town, joined diagonally
        smod[r + dr, c + dc] = 30; pop[r + dr, c + dc] = 20000
    smod[r + 20, c] = 21; pop[r + 20, c] = 6000
    tr = from_origin(x0, y0, 1000, 1000)
    _ghsl_zip(tmp_path, "smod_2020", smod, "uint8", tr)
    _ghsl_zip(tmp_path, "pop_2020", pop, "float32", tr)
    ctx = {"grid": g, "dl": tmp_path / "downloads", "work": tmp_path}
    ga.settlements_epoch(ctx, 2020)
    st = pd.read_csv(tmp_path / "settlements_2020.csv")
    assert sorted(st.population) == [6000, 60000]
    lab = np.load(tmp_path / "settlement_id_2020.npy")
    assert set(np.unique(lab)) == {0, 1, 2}
    pg = np.load(tmp_path / "population_2020.npy")
    assert pg.sum() == pytest.approx(66000, rel=0.05)


def test_block_mean_cog_and_png(tmp_path):
    g = ga.Grid((0, 6, 1, 7), D)
    a = np.arange(g.size, dtype=np.float64).reshape(g.shape) % 500
    a[:10, :10] = ga.TT_NODATA
    getter = lambda r0, r1: a[r0:r1]
    for factor, name in ((1, "t1.tif"), (10, "t10.tif")):
        ga.write_cog(tmp_path / name, g, [getter, getter], "uint16", ga.TT_NODATA, ["a", "b"], factor)
        with rasterio.open(tmp_path / name) as r:
            assert r.tags(ns="IMAGE_STRUCTURE").get("LAYOUT") == "COG"
            assert r.count == 2 and r.descriptions == ("a", "b")
            assert r.shape == (g.height // factor, g.width // factor)
            if factor == 10:
                assert r.read(1)[0, 0] == ga.TT_NODATA
                assert r.read(1)[5, 5] == pytest.approx(a[50:60, 50:60].mean(), abs=0.5)
    fr = np.full(g.shape, 0.002, np.float64)
    ga.write_cog(tmp_path / "f10.tif", g, [lambda r0, r1: fr[r0:r1]], "float32", -9999.0, ["f"], 10)
    with rasterio.open(tmp_path / "f10.tif") as r:
        assert r.read(1).mean() == pytest.approx(0.002)                  # not rounded away
        ga.png_map(tmp_path / "p.png", r.read(1), -9999.0, "t", "friction", [0, 1, 6, 7])
    ga.png_map(tmp_path / "q.png", (a[::10, ::10]).astype(np.uint16), ga.TT_NODATA, "t", "tt", [0, 1, 6, 7])
    assert (tmp_path / "p.png").stat().st_size > 1000 and (tmp_path / "q.png").exists()


def _square(x):
    return x * x


def test_run_budgeted_keeps_order():
    jobs = list(range(12))
    out = ga.run_budgeted(_square, jobs, lambda j: 1e8 * (j + 1), "test", cap=3)
    assert out == [j * j for j in jobs]


def test_port_cells_snap_to_land():
    g = ga.Grid((0, 6, 1, 7), D)
    fr = np.full(g.shape, 0.01, np.float32)
    fr[:, :60] = np.inf                                        # sea in the west half
    ports = pd.DataFrame({"Longitude": [0.48, 0.1], "Latitude": [6.5, 6.5]})
    r, c = ga.port_cells(ports, g, fr)
    assert c[0] == 60 and r[0] == 60                           # ~2 cells offshore -> coast
    assert r[1] == -1                                           # 40 km offshore -> dropped


def test_stage_validate_with_mocked_osrm(tmp_path, monkeypatch):
    g = ga.Grid((0, 6, 3, 9), D)
    work = tmp_path / "work"; work.mkdir()
    fr = np.full(g.shape, 0.06 / 30, np.float32)                     # 30 km/h everywhere
    np.save(work / "friction_2026.npy", fr)
    np.save(work / "population_2025.npy", np.full(g.shape, 100, np.float32))
    np.save(work / "countries.npy", np.ones(g.shape, np.int16))
    pd.DataFrame({"cid": [1], "iso3": ["AAA"], "NAME": ["A"], "CONTINENT": ["Africa"]}) \
        .to_csv(work / "countries.csv", index=False)
    pd.DataFrame({"settlement_id": [1, 2, 3], "population": [2e5, 6e4, 1e4],
                  "lon": [1.5, 2.2, 0.7], "lat": [7.5, 8.2, 6.7], "cells_1km": [9, 4, 1]}) \
        .to_csv(work / "settlements_2025.csv", index=False)
    calls = []

    def fake_table(self, coords, n_src):
        calls.append(len(coords))
        (x0, y0) = coords[-1]
        dur = [[float(ga.great_circle_km(x, y, x0, y0) * 1.3 / 50 * 3600)] for x, y in coords[:n_src]]
        return {"code": "Ok", "durations": dur, "distances": [[1000.0]] * n_src,
                "sources": [{"distance": 50.0}] * n_src, "destinations": [{"distance": 20.0}]}, "mock"
    monkeypatch.setattr(ga.RateLimited, "table", fake_table)
    monkeypatch.setattr(ga, "ROUTING_CITIES", 5)
    ctx = {"grid": g, "work": work, "results": tmp_path / "res", "years": [2015, 2026],
           "epoch": {2015: 2015, 2026: 2025}}
    ga.stage_validate(ctx)
    pairs = pd.read_csv(tmp_path / "res" / "routing_validation" / "pairs_2026.csv")
    assert calls == [11, 11]                                   # 2 cities >= 50k, 10 origins + city
    assert len(pairs) == 20 and pairs.great_circle_km.between(10, 150).all()
    summ = pd.read_csv(tmp_path / "res" / "routing_validation" / "summary_2026.csv", index_col=0)
    # ours: 30 km/h over ~ straight lines (8-neighbour path, slightly longer); mock: 50 km/h x 1.3
    assert 1.0 < summ.loc["all", "median_ratio_ours_over_osrm"] < 1.45
    assert (tmp_path / "res" / "routing_validation" / "scatter_2026.png").exists()


def test_grid_round_trip_is_exact():
    """Workers rebuild the grid from its bbox: shapes must never change."""
    rng = np.random.default_rng(0)
    for _ in range(2000):
        w = rng.uniform(-180, 170); s = rng.uniform(-60, 80)
        g = ga.Grid((w, s, w + rng.uniform(0.1, 10), min(85, s + rng.uniform(0.1, 5))), D)
        g2 = ga.Grid(g.to_dict()["bbox"], g.to_dict()["res_deg"])
        assert g2.shape == g.shape and g2.transform == g.transform
        r0, c0 = rng.integers(0, g.height), rng.integers(0, g.width)
        sub = g.subgrid(r0, c0, g.height - r0, g.width - c0)
        assert sub.shape == (g.height - r0, g.width - c0)
    glob = ga.Grid(ga.NELSON_EXTENT, D)
    assert ga.Grid(glob.to_dict()["bbox"], D).shape == (17400, 43200)
