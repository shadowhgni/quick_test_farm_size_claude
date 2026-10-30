"""Offline tests of global_accessibility_v2.py on synthetic data.

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
import shapely
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Polygon, box

os.environ.setdefault("GA_WORK_DIR", tempfile.mkdtemp(prefix="ga_test_"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import global_accessibility_v3 as ga  # noqa: E402
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
<way id="11"><nd ref="3"/><nd ref="4"/><tag k="highway" v="track"/><tag k="bridge" v="yes"/></way>
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
    assert s["crossing_segments"] == 1                        # the track tagged bridge=yes
    # the bridge track lies exactly on the bounding-box edge (lat 6.2): must not be clipped
    rows = np.nonzero(d["bridge"].any(axis=1))[0]
    assert d["bridge"].sum() >= 120 and len(rows) <= 2 and rows.min() >= d["bridge"].shape[0] - 3
    w = pd.read_parquet(tmp_path / "x.ways.parquet")                     # way table for stage events
    assert w.osm_id.nunique() == 3 and (w.km > 0).all() and not w.clipped.any()     # km per way and 0.1 deg cell
    assert w.km.sum() == pytest.approx(sum(s["km_by_class"].values()), rel=1e-3)


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
        ga.write_cog(tmp_path / name, g, [getter, getter], "uint16", ga.TT_NODATA, ["a", "b"], factor,
                     units="minutes")
        with rasterio.open(tmp_path / name) as r:
            assert r.units == ("minutes", "minutes") and r.tags()["UNITS"] == "minutes"
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
    monkeypatch.setattr(ga, "ROUTING_CITIES_PER_CONTINENT", 5)
    monkeypatch.setattr(ga, "ROUTING_ORIGINS_PER_CITY", 12)
    monkeypatch.setattr(ga, "ROUTING_BANDS_KM", (10, 50, 100, 150))
    monkeypatch.setattr(ga, "ROUTING_RADIUS_KM", (10, 150))
    ctx = {"grid": g, "work": work, "results": tmp_path / "res", "years": [2015, 2020, 2026],
           "epoch": {2015: 2015, 2020: 2020, 2026: 2025}}
    ga.stage_validate(ctx)
    pairs = pd.read_csv(tmp_path / "res" / "routing_validation" / "pairs_2026.csv")
    assert calls == [13, 13]                                   # 2 settlements >= 50k, 12 origins + city
    assert len(pairs) == 24 and pairs.great_circle_km.between(10, 150).all()
    per_band = pd.cut(pairs.great_circle_km, [10, 50, 100, 150]).value_counts()
    assert (per_band == 8).all()                               # spread evenly over the distance bands
    assert set(pairs.origin_iso3) == {"AAA"}
    ga.stage_validate(ctx)                                     # rerun: resumes, no new requests
    assert calls == [13, 13]
    bd = pd.read_csv(tmp_path / "res" / "routing_validation" / "summary_by_distance_2026.csv")
    assert set(bd.continent) == {"all", "Africa"} and len(bd) == 6
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


def test_stages_friction_to_compare_offline(tmp_path, monkeypatch):
    """friction -> traveltime -> outputs -> store -> compare -> sensitivity, three years."""
    g = ga.Grid((1.0, 6.0, 3.0, 8.0), D)                       # 240 x 240 cells
    work, dl, res = tmp_path / "work", tmp_path / "work" / "downloads", tmp_path / "res"
    (dl / "nelson").mkdir(parents=True)
    lc = np.full(g.shape, 40, np.uint8); lc[:, 118:121] = 80           # river
    np.save(work / "landcover.npy", lc)
    wp = np.zeros(g.shape, np.uint8); wp[:, 118:121] = 100; wp[:, 117] = 60   # river + bank
    np.save(work / "water_pct.npy", wp)
    np.save(work / "tan_slope.npy", np.full(g.shape, 0.02, np.float32))
    cg = np.ones(g.shape, np.int16); cg[:, 120:] = 2
    np.save(work / "countries.npy", cg)
    pd.DataFrame({"cid": [1, 2], "iso3": ["AAA", "BBB"], "ADM0_A3": ["AAA", "BBB"],
                  "NAME": ["A", "B"], "CONTINENT": ["Africa", "Africa"]}).to_csv(work / "countries.csv", index=False)
    pd.DataFrame({"iso3": ["AAA", "BBB"], "year": [2015, 2015], "score": [40.0, 30.0]}) \
        .to_csv(dl / "wgi_control_of_corruption.csv", index=False)
    for y in (2015, 2020, 2026):
        r = np.zeros(g.shape, np.float32); r[120, :] = 70                     # E-W primary road
        if y == 2020:
            r[100:240, 60] = np.maximum(r[100:240, 60], 40)                   # N-S road, southern part
        if y == 2026:
            r[:, 60] = np.maximum(r[:, 60], 40)                               # new N-S road
            r[20:40, 119] = 30                                                 # "road" in the river
            r[20:40, 117] = 30                                                 # road on the bank
        np.save(work / f"road_speed_{y}.npy", r)
        cr = np.zeros(g.shape, np.uint8); cr[120, 118:121] = 1                 # the bridge
        np.save(work / f"road_crossing_{y}.npy", cr)
    ml = np.zeros(g.shape, np.uint8); ml[200, 20:100] = 1; ml[200, 110:125] = 1
    # Weiss 2015: the E-W road (in OSM 2015) plus 40 cells of the N-S road (not in OSM 2015)
    # plus a "river" at 20 km/h with no OSM road in 2026 (must not be used)
    wz = np.zeros(g.shape, np.float32); wz[120, :] = 60; wz[0:40, 60] = 50; wz[150, 150:200] = 20
    np.save(work / "weiss2015_speed.npy", wz)
    np.save(work / "ml_roads.npy", ml)
    pd.DataFrame([{"year": y, "lon": 2.0, "lat": 7.0 - 0.5 / 120, "iso3_a": "AAA", "iso3_b": "BBB",
                   "highway": "primary"} for y in (2015, 2020, 2026)]).to_csv(work / "checkpoints_raw.csv", index=False)
    for e in (2015, 2020, 2025):
        lab = np.zeros(g.shape, np.int32); lab[118:123, 200:205] = 1; lab[30:32, 30:32] = 2
        st_ = pd.DataFrame({"settlement_id": [1, 2], "population": [2e5, 8e3], "lon": [2.7, 1.26],
                            "lat": [7.0, 7.74], "cells_1km": [25, 4]})
        if e == 2025:                                                    # a town that grew past 50,000
            lab[200:203, 30:33] = 3
            st_ = pd.concat([st_, pd.DataFrame({"settlement_id": [3], "population": [6e4], "lon": [1.26],
                                                "lat": [6.32], "cells_1km": [9]})])
        np.save(work / f"settlement_id_{e}.npy", lab)
        np.save(work / f"population_{e}.npy", np.full(g.shape, 50, np.float32))
        st_.to_csv(work / f"settlements_{e}.csv", index=False)
    pd.DataFrame({"Main Port Name": ["P"], "Country Code": ["A"], "Harbor Size": ["Medium"],
                  "Latitude": [6.2], "Longitude": [1.1]}).to_csv(dl / "UpdatedPub150.csv", index=False)
    nel = np.full((17400, 43200), 65535, np.uint16)                          # global, like Nelson
    wr = ga.Grid(ga.NELSON_EXTENT, D).window_of(g.bounds)
    nel[wr[0]:wr[0] + wr[2], wr[1]:wr[1] + wr[3]] = 100
    with rasterio.open(dl / "nelson" / "travel_time_to_cities_11.tif", "w", driver="GTiff",
                       height=17400, width=43200, count=1, dtype="uint16", crs="EPSG:4326",
                       transform=from_origin(-180, 85, D, D), compress="deflate") as d:
        d.write(nel, 1)
    ctx = {"work": work, "dl": dl, "results": res, "grid": g, "years": [2015, 2020, 2026],
           "epoch": {2015: 2015, 2020: 2020, 2026: 2025}, "nelson_layers": ["cities_11"]}
    monkeypatch.setattr(ga, "LIGHT_FACTOR", 10)
    monkeypatch.setattr(ga, "ROAD_ONLY", True)
    monkeypatch.setattr(ga, "ROAD_ONLY_LAYERS", ["cities_11"])
    ga.stage_friction(ctx)
    f15, f26 = np.load(work / "friction_2015.npy"), np.load(work / "friction_2026.npy")
    assert np.isinf(f15[0, 119]) and np.isfinite(f15[120, 119])             # river, bridge
    assert np.isinf(f26[30, 119]) and np.isfinite(f26[30, 117])             # water road dropped, bank kept
    assert np.isinf(f26[200, 119]) and np.isfinite(f26[200, 115])           # ML over water dropped
    st15 = json.loads((work / "friction_2015.json").read_text())
    assert st15["weiss2015_cells_added"] == 40                             # only where OSM 2026 has a road
    assert np.isclose(f15[10, 60], 0.06 / (40 * (1 - 0.1 * 0.6)))           # min(Weiss, OSM 2026) x corruption
    assert f15[150, 170] > 0.06 / 10                                        # Weiss river not used
    tiles = pd.read_csv(work / "osm2015_completeness_tiles.csv")
    assert len(tiles) == 1 and tiles.completeness[0] == pytest.approx(237 / 277)   # 3 bridge cells on open water excluded and tiles.osm2015_complete[0]
    st20 = json.loads((work / "friction_2020.json").read_text())
    assert st20["weiss2015_cells_added"] == 40                             # 2020 completed too (rows 0-39)
    assert st20["ml_cells"] == 0                                           # ML roads: last year only
    assert (work / "osm2020_completeness_tiles.csv").exists()
    st26 = json.loads((work / "friction_2026.json").read_text())
    assert st26["weiss2015_cells_added"] == 0                             # never for the last year
    assert st26["osm_road_cells_dropped_on_water"] == 20
    assert st26["osm_road_cells_kept_as_crossings"] == 3
    assert st26["ml_road_cells_dropped_on_water"] == 3
    cp = pd.read_csv(work / "checkpoints_2015.csv")
    assert len(cp) == 1 and cp.delay_min[0] > 15
    ga.stage_traveltime(ctx)
    t15 = np.load(work / "tt" / "tt_2015_cities_11.npy"); t26 = np.load(work / "tt" / "tt_2026_cities_11.npy")
    assert t15[120, 202] == 0 and (t26 <= t15 + 1e-3)[np.isfinite(t15)].all()
    assert (t26 < t15 - 1).sum() > 100                                       # new road helps
    t20 = np.load(work / "tt" / "tt_2020_cities_11.npy")
    fin = np.isfinite(t15)
    # road-only: settlements of 2015, same roads -> ignores the new town of 2025
    r15 = np.load(work / "tt" / "tt_roadonly_2015_cities_11.npy"); r26 = np.load(work / "tt" / "tt_roadonly_2026_cities_11.npy")
    assert np.allclose(r15[fin], t15[fin])                               # first year: identical
    assert t26[201, 31] == 0 and r26[201, 31] > 30                       # new town is a destination only in total
    assert (r26 >= t26 - 1e-3)[np.isfinite(r26)].all() and (r26 <= r15 + 1e-3)[fin].all()
    assert (r26 < r15 - 1).sum() > 100                                   # roads alone still help
    assert (t26 <= t20 + 1e-3)[fin].all() and (t20 <= t15 + 1e-3)[fin].all()
    assert np.isinf(np.load(work / "tt" / "tt_2015_cities_1.npy")).all()   # no city of 5-50 M
    # resume reuses layers, but recomputes them when the friction grid was rebuilt since
    ffile = work / "friction_2015.npy"
    fr0 = np.load(ffile); np.save(ffile, fr0 * 2)
    later = (work / "tt" / "tt_2015_cities_11.npy.done").stat().st_mtime + 10
    os.utime(ffile, (later, later))
    ga.stage_traveltime(ctx)
    t15x2 = np.load(work / "tt" / "tt_2015_cities_11.npy")
    assert np.allclose(t15x2[np.isfinite(t15)], 2 * t15[np.isfinite(t15)], rtol=1e-4)
    np.save(ffile, fr0); os.utime(ffile, (later + 10, later + 10)); ga.stage_traveltime(ctx)
    assert np.array_equal(np.load(work / "tt" / "tt_2015_cities_11.npy"), t15)
    # crossing the checkpoint costs ~ its delay: compare with a run without it
    ga.stage_outputs(ctx)
    with rasterio.open(res / "cog_1km" / "traveltime_2026_1km.tif") as r:
        assert r.count == 17 and r.descriptions[10].startswith("cities_11")
        assert r.tags(ns="IMAGE_STRUCTURE").get("LAYOUT") == "COG"
    for a_, b_ in ((2015, 2020), (2020, 2026), (2015, 2026)):
        with rasterio.open(res / "cog_10km" / f"traveltime_change_{b_}_minus_{a_}_10km.tif") as r:
            assert r.shape == (24, 24) and r.dtypes[0] == "int16"
    assert len(list((res / "png").glob("*.png"))) == 3 * 17 + 3 + 3 * 17
    tab = pd.read_csv(res / "tables" / "pop_weighted_traveltime_global.csv")
    assert set(tab.layer) == set(ga.layer_names()) and len(tab) == 3 * 17
    # --- store: every grid, reloadable by another script
    ga.stage_store(ctx)
    man = json.loads((res / "store" / "manifest.json").read_text())
    names = {(it["name"], it["year"], it["layer"]) for it in man["items"]}
    assert ("friction", 2020, None) in names and ("traveltime", 2026, "ports_5") in names
    assert ("population", 2020, None) in names and ("landcover", None, None) in names
    assert ("traveltime_roadonly", 2026, "cities_11") in names and ("friction_roadonly", 2020, None) in names
    ro, _ = ga.load_store(res, "traveltime_roadonly", 2026, "cities_11")
    assert np.allclose(ro[np.isfinite(r26)], r26[np.isfinite(r26)])
    assert (res / "tables" / "pop_weighted_traveltime_roadonly_global.csv").exists()
    assert sum(1 for n in names if n[0] == "traveltime") == 3 * 17
    arr, prof = ga.load_store(res, "traveltime", 2020, "cities_11")
    ref = np.load(work / "tt" / "tt_2020_cities_11.npy")
    assert np.allclose(arr[np.isfinite(ref)], ref[np.isfinite(ref)]) and np.isnan(arr[~np.isfinite(ref)]).all()
    # --- stage roadonly: a run whose traveltime finished before 3.1 (no road-only grids) gets them added,
    # without recomputing the existing travel time, and the store is re-armed (HPC, 2026-10-30)
    for f in list(work.glob("friction_roadonly_*.npy")) + list((work / "tt").glob("tt_roadonly_*")):
        f.unlink()
    (work / "_done").mkdir(exist_ok=True)
    (work / "_done" / "store").write_text("x")
    main_mtime = (work / "tt" / "tt_2026_cities_11.npy").stat().st_mtime
    ga.stage_roadonly(ctx)
    assert np.allclose(np.load(work / "tt" / "tt_roadonly_2026_cities_11.npy")[np.isfinite(r26)], r26[np.isfinite(r26)])
    assert (work / "tt" / "tt_2026_cities_11.npy").stat().st_mtime == main_mtime      # not recomputed
    assert not (work / "_done" / "store").exists()
    ga.stage_roadonly(ctx)                                                  # complete: nothing to do
    part, pprof = ga.load_store(res, "friction", 2026, bbox=(1.5, 6.5, 2.0, 7.0))
    assert part.shape == (60, 60) and pprof["transform"].c == pytest.approx(1.5)
    lcs, _ = ga.load_store(res, "landcover")
    assert lcs.dtype == np.uint8 and (lcs == lc).all()
    assert (res / "store" / "tables" / "settlements_2020.csv").exists()
    with pytest.raises(KeyError, match="not in the store"):
        ga.load_store(res, "friction", 1999)
    ga.stage_compare(ctx)
    cmp_ = pd.read_csv(res / "nelson_comparison" / "comparison_by_layer.csv")
    assert list(cmp_.our_year) == [2015, 2015, 2020, 2020, 2026, 2026] and (cmp_.cells > 50000).all()
    assert list(cmp_.subset) == ["all", "osm2015_complete_tiles"] * 3
    r0 = cmp_.iloc[0]                                                     # relative to Nelson
    assert r0.rel_bias_pct == pytest.approx(100 * r0.mean_diff_min / r0.nelson_mean_min)
    assert r0.rel_mad_pct == pytest.approx(100 * r0.mean_abs_diff_min / r0.nelson_mean_min)
    assert r0.pw_rel_bias_pct == pytest.approx(
        100 * (r0.pop_weighted_ours_min / r0.pop_weighted_nelson_min - 1), rel=1e-6)
    assert r0.rel_mad_pct >= abs(r0.rel_bias_pct) and r0.pw_rel_mad_pct >= abs(r0.pw_rel_bias_pct) - 1e-9
    assert r0.median_abs_pct_diff >= abs(r0.median_pct_diff) and r0.pct_sample_cells > 0
    assert (res / "methods" / "osm2015_completeness_tiles.csv").exists()
    assert (res / "methods" / "osm2020_completeness_tiles.csv").exists()
    for f in ["config.json", "speed_table.csv", "corruption_2026.csv", "checkpoints_2026.csv",
              "software_versions.json", "destinations.csv"]:
        assert (res / "methods" / f).exists(), f
    monkeypatch.setattr(ga, "MANIFEST", [])                             # resumed run: nothing downloaded
    ga.write_methods(ctx); ga.write_methods(ctx)
    # --- sensitivity to K and to the border delay
    monkeypatch.setattr(ga, "SENS_LAYERS", ["cities_11"])
    ga.stage_sensitivity(ctx)
    sc = pd.read_csv(res / "sensitivity" / "scenarios.csv")
    assert len(sc) == 7 and sc.baseline.sum() == 1                      # one-at-a-time design
    dom = pd.read_csv(res / "sensitivity" / "sensitivity_domain.csv")
    base = dom[dom.baseline].iloc[0]
    tab = pd.read_csv(res / "tables" / "pop_weighted_traveltime_global.csv")
    main15 = tab[(tab.year == 2015) & (tab.layer == "cities_11")].pop_weighted_mean_min.item()
    assert base.mean_min_2015 == pytest.approx(main15, rel=1e-9)         # baseline = main run
    byk = dom[dom.delay_min == 15].sort_values("K")
    assert byk.mean_min_2015.is_monotonic_increasing and byk.mean_min_2015.iloc[-1] > byk.mean_min_2015.iloc[0]
    byd = dom[dom.K == 0.1].sort_values("delay_min")
    assert byd.mean_min_2026.is_monotonic_increasing and byd.mean_min_2026.iloc[-1] > byd.mean_min_2026.iloc[0]
    assert (dom[dom.baseline].filter(like="_vs_baseline").abs() < 1e-9).all(axis=None)
    for c in ("mean_min_2020", "change_2020_minus_2015_min", "change_2026_minus_2020_min",
              "change_2026_minus_2015_min"):
        assert c in dom.columns, c
    assert (res / "sensitivity" / "sensitivity.png").exists()
    assert (res / "sensitivity" / "sensitivity_country.csv").exists()
    assert not list((work / "sens").glob("*.npy"))                       # scenario grids removed


def test_block_mode_and_water():
    a = np.zeros((10, 10), np.uint8)
    a[:5, :5] = 80; a[:5, 5:] = 40; a[5:, :5] = 10; a[5:, 5:] = 0
    a[0, 0] = 40                                         # 24 water + 1 cropland
    mode, w = ga.block_mode_and_water(a, 5)
    assert mode.tolist() == [[80, 40], [10, 0]] and w.tolist() == [[96, 0], [0, 0]]


def test_geofabrik_plan_falls_back_to_next_snapshot(tmp_path, monkeypatch):
    """Snapshots are read from Geofabrik's folder listings (HEAD only where there is none,
    e.g. the site root). Russia has no 2015 snapshot (the first is russia-160101)."""
    import types
    import pytest
    sq = lambda w, s_, e, n: {"type": "Polygon", "coordinates": [[[w, s_], [e, s_], [e, n], [w, n], [w, s_]]]}
    base = "https://download.geofabrik.de/"
    feats = [
        {"properties": {"id": "europe", "urls": {"pbf": base + "europe-latest.osm.pbf"}}, "geometry": sq(0, 40, 30, 60)},
        {"properties": {"id": "france", "parent": "europe", "urls": {"pbf": base + "europe/france-latest.osm.pbf"}},
         "geometry": sq(0, 40, 10, 50)},
        {"properties": {"id": "russia", "urls": {"pbf": base + "russia-latest.osm.pbf"}}, "geometry": sq(30, 40, 60, 60)},
        {"properties": {"id": "ural", "parent": "russia", "urls": {"pbf": base + "russia/ural-latest.osm.pbf"}},
         "geometry": sq(30, 40, 60, 60)},
        {"properties": {"id": "mars", "urls": {"pbf": base + "mars-latest.osm.pbf"}}, "geometry": sq(60, 40, 70, 60)},
    ]
    idx = tmp_path / "idx.json"; idx.write_text(json.dumps({"features": feats}))
    apache = lambda names: "<pre>\n" + "\n".join(
        f'<a href="{n}">{n}</a>   2026-01-02 00:25  46M' for n in names) + "\n</pre>"
    table = lambda names: "<table>\n" + "\n".join(
        f'<tr><td><a href="{n}">{n}</a></td><td align="right">2026-01-02 00:25  </td><td align="right">1.5G</td></tr>'
        for n in names) + "\n</table>"
    pages = {base + "europe/": apache(["france-150101.osm.pbf", "france-260101.osm.pbf", "france-latest.osm.pbf"]),
             base + "russia/": table(["ural-260101.osm.pbf", "ural-latest.osm.pbf"]),
             base: '<html>Geofabrik home page <a href="europe-latest.osm.pbf">Europe</a> '
                   '<a href="russia-latest.osm.pbf">Russia</a> <a href="mars-latest.osm.pbf">x</a></html>'}
    root_files = {base + "russia-160101.osm.pbf": 3_900_000_000}
    calls = []

    def fake(url, sess, method="HEAD", tries=6, **kw):
        calls.append((method, url))
        if method == "GET":
            return types.SimpleNamespace(status_code=200, ok=True, text=pages.get(url, ""), headers={})
        n = root_files.get(url)
        return types.SimpleNamespace(status_code=200 if n else 404, ok=bool(n), text="",
                                     headers={"Content-Length": str(n or 0)})
    monkeypatch.setattr(ga, "download", lambda url, dest, sess: idx)
    monkeypatch.setattr(ga, "http_request", fake)
    grid = ga.Grid((0, 40, 70, 60), 0.5)
    monkeypatch.setattr(ga, "OSM_MAX_MISSING_REGIONS", 1)                # mars has no data at all
    plan = ga.geofabrik_plan(tmp_path, grid, [2015, 2026], None)
    p15 = {r["region"]: r for r in plan[2015]}
    assert set(p15) == {"france", "russia"}
    assert p15["russia"]["url"].endswith("russia-160101.osm.pbf") and p15["russia"]["snapshot_year"] == 2016
    assert p15["russia"]["bytes"] == 3_900_000_000                     # HEAD at the site root
    assert p15["france"]["snapshot_year"] == 2015 and p15["france"]["bytes"] == 46 * 2**20
    p26 = {r["region"]: r for r in plan[2026]}
    assert set(p26) == {"france", "ural"} and p26["ural"]["bytes"] == int(1.5 * 2**30)   # mars: no data
    assert any("no snapshot for 1 regions" in m and "mars" in m for m in ga.LOG)
    assert ("HEAD", base + "russia-150101.osm.pbf") in calls              # root: asked, not assumed absent
    gets = [u for m, u in calls if m == "GET"]
    assert len(gets) == len(set(gets)) == 3                              # one request per folder
    n = len(calls); ga.geofabrik_plan(tmp_path, grid, [2015], None)
    assert not [c for c in calls[n:] if c[0] == "GET"]                   # listings cached on disk

    monkeypatch.setattr(ga, "OSM_MAX_MISSING_REGIONS", 0)
    with pytest.raises(SystemExit, match="mars"):
        ga.geofabrik_plan(tmp_path, grid, [2015], None)
    # a server that keeps failing stops the run instead of planning a world without roads
    def down(url, sess, method="HEAD", tries=6, **kw):
        raise ga.RemoteUnavailable(f"{url}: ConnectionError after 6 attempts")
    monkeypatch.setattr(ga, "http_request", down)
    with pytest.raises(SystemExit, match="not reachable"):
        ga.geofabrik_plan(tmp_path / "fresh", grid, [2015], None)
    # ... and so does a plan that is implausibly empty
    monkeypatch.setattr(ga, "http_request", lambda url, sess, method="HEAD", tries=6, **kw: types.SimpleNamespace(
        status_code=404, ok=False, text="", headers={}))
    with pytest.raises(SystemExit, match="no Geofabrik extract found"):
        ga.geofabrik_plan(tmp_path / "fresh2", grid, [2015], None)


def test_http_request_retries_then_raises(monkeypatch):
    import types
    import pytest
    monkeypatch.setattr(ga.time, "sleep", lambda s: None)
    seq = iter([503, 429, 200])

    class S:
        def request(self, method, url, **kw):
            return types.SimpleNamespace(status_code=next(seq), headers={})
    assert ga.http_request("u", S()).status_code == 200
    assert ga.head_ok.__doc__ and ga.http_request("u", types.SimpleNamespace(
        request=lambda *a, **k: types.SimpleNamespace(status_code=404, headers={}))).status_code == 404

    class Down:
        def request(self, method, url, **kw):
            raise ga.requests.ConnectionError("reset by peer")
    with pytest.raises(ga.RemoteUnavailable):
        ga.http_request("u", Down(), tries=3)


def test_fix_proj_data_prefers_a_setting_without_proj_errors(monkeypatch):
    """The HPC case: the environment 'works' but PROJ prints 'Open of /opt/conda/share/proj
    failed'; the script must move on to a setting where PROJ is silent."""
    import types
    monkeypatch.setenv("PROJ_LIB", "/opt/conda/share/proj")
    monkeypatch.delenv("PROJ_DATA", raising=False)
    monkeypatch.delenv("GA_PROJ_DATA", raising=False)
    seen = []

    def run(cmd, env, **kw):
        seen.append(env.get("PROJ_LIB"))
        noisy = env.get("PROJ_LIB") == "/opt/conda/share/proj"
        return types.SimpleNamespace(returncode=0, stderr="ERROR 1: PROJ: proj_create_from_database: "
                                     "Open of /opt/conda/share/proj failed\n" if noisy else "")
    monkeypatch.setattr(ga.subprocess, "run", run)
    ga.fix_proj_data()
    assert seen == ["/opt/conda/share/proj", None]                      # as set (noisy), then unset
    assert "PROJ_LIB" not in ga.os.environ and "PROJ_DATA" not in ga.os.environ


class _FakeResp:
    def __init__(self, body, status=200):
        self.body, self.status_code, self.headers = body, status, {"Last-Modified": "Thu, 01 Jan 2026"}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ga.requests.HTTPError(str(self.status_code))

    def iter_content(self, n):
        yield self.body


def test_download_keeps_complete_files_and_replaces_damaged_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(ga.time, "sleep", lambda s: None)
    calls = []

    class S:
        body = b"x" * 1000

        def get(self, url, **kw):
            calls.append(url)
            return _FakeResp(self.body)
    dest = tmp_path / "a.osm.pbf"
    ga.download("u", dest, S())
    meta = json.loads((tmp_path / "a.osm.pbf.meta.json").read_text())
    assert dest.read_bytes() == S.body and meta["bytes"] == 1000 and len(calls) == 1
    ga.download("u", dest, S())                                            # unchanged: not downloaded again
    assert len(calls) == 1
    dest.write_bytes(b"x" * 10)                                            # damaged: downloaded again
    ga.download("u", dest, S())
    assert len(calls) == 2 and dest.stat().st_size == 1000
    dest.write_bytes(b"x" * 10)                                            # damaged and the server is down:
    fail = type("F", (), {"get": lambda self, url, **kw: (_ for _ in ()).throw(ga.requests.ConnectionError("down"))})
    with pytest.raises(ga.RemoteUnavailable):
        ga.download("u", dest, fail(), retries=2)
    assert dest.read_bytes() == b"x" * 10                                  # the old file is left as it was
    old = tmp_path / "old.zip"; old.write_bytes(b"y" * 5)                 # file from a run before .meta.json
    ga.download("u2", old, fail())
    assert json.loads((tmp_path / "old.zip.meta.json").read_text())["bytes"] == 5


def test_cleanup_only_after_all_stages_succeeded(tmp_path, monkeypatch):
    work = tmp_path / "w"
    for d in ("downloads", "pylib", "_done"):
        (work / d).mkdir(parents=True)
    (work / "downloads" / "f.osm.pbf").write_bytes(b"1")
    (work / "grid.npy").write_bytes(b"1")
    monkeypatch.setattr(ga, "write_methods", lambda ctx: None)
    monkeypatch.setattr(ga, "CLEANUP", True); monkeypatch.setattr(ga, "KEEP_DOWNLOADS", False)
    ctx = {"work": work}
    for s_ in ga.STAGES[:3]:
        (work / "_done" / s_).write_text("x")
    ga.stage_cleanup(ctx)                                                  # incomplete run: nothing deleted
    assert (work / "downloads" / "f.osm.pbf").exists() and (work / "grid.npy").exists()
    for s_ in ga.STAGES:
        if s_ != "cleanup":
            (work / "_done" / s_).write_text("x")
    ga.stage_cleanup(ctx)
    assert sorted(p.name for p in work.iterdir()) == ["pylib"]


class _Resp:
    def __init__(self, status=200, body=b"x" * 10, js=None, text=""):
        self.status_code, self.body, self.js, self.text, self.headers = status, body, js, text, {}
        self.ok = status < 400

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_content(self, n):
        yield self.body

    def json(self):
        return self.js


def test_network_check_probes_resources_and_drops_optional_servers(tmp_path, monkeypatch):
    """Each resource is fetched (first bytes); a refused file (403) or an unreachable host stops the
    run with the purpose of the resource; an unreachable routing server only drops validation."""
    blocked = {"planet.openstreetmap.org", "router.project-osrm.org"}
    refused = set()
    listing = '<a href="history-260921.osm.pbf">h</a> 2026-09-24 17:05  152G'

    class S:
        def get(self, url, **kw):
            host = url.split("/")[2]
            if host in blocked:
                raise ga.requests.ConnectionError("Failed to establish a new connection: [Errno 101] Network is unreachable")
            if any(r in url for r in refused):
                return _Resp(403)
            if "api.figshare.com" in url:
                return _Resp(js={"files": [{"download_url": "https://ndownloader.figshare.com/files/1"}]})
            return _Resp()

        def request(self, method, url, **kw):                         # http_request (OSM history listing)
            if url.split("/")[2] in blocked:
                raise ga.requests.ConnectionError("[Errno 101] Network is unreachable")
            return _Resp(text=listing)

        def head(self, url, **kw):
            return _Resp()
    monkeypatch.setattr(ga.time, "sleep", lambda s: None)
    monkeypatch.setattr(ga, "ROUTING_SERVERS", list(ga.ROUTING_SERVERS))
    monkeypatch.setattr(ga, "ROUTING_VALIDATION", True)
    monkeypatch.setattr(ga, "OSM_SOURCE", "history")
    monkeypatch.setattr(ga, "EVENT_CHANGESETS_FILE", None)
    monkeypatch.setattr(ga.shutil, "which", lambda x: "/usr/bin/osmium")   # osmium installed: no conda probe
    ctx = {"work": tmp_path, "years": [2015, 2026]}
    with pytest.raises(SystemExit) as e:
        ga.network_check(ctx, S())
    assert "OSM full-history planet" in str(e.value) and "Errno 101" in str(e.value)
    assert "routing validation" not in str(e.value)                       # optional: not a reason to stop
    assert ga.ROUTING_SERVERS == ["https://routing.openstreetmap.de/routed-car"]
    chk = pd.read_csv(tmp_path / "network_check.csv")
    assert set(chk.check) >= {"history", "range", "get", "figshare"}
    assert chk[chk.purpose.str.contains("changeset dump")].required.eq(False).all()
    # a file refused by a proxy is reported as such
    blocked.discard("planet.openstreetmap.org"); refused.add("GHS_POP_E2015")
    with pytest.raises(SystemExit, match="HTTP 403 .refused"):
        ga.network_check(ctx, S())
    refused.clear()
    ga.network_check(ctx, S())                                             # everything else answers: go on
    assert pd.read_csv(tmp_path / "network_check.csv").reachable.all()


def test_check_access_reports_both_osm_sources(tmp_path, monkeypatch, capsys):
    class S:
        def get(self, url, **kw):
            if "geofabrik" in url:
                raise ga.requests.ConnectionError("[Errno 101] Network is unreachable")
            if "api.figshare.com" in url:
                return _Resp(js={"files": [{"download_url": "https://ndownloader.figshare.com/files/1"}]})
            return _Resp()

        def request(self, method, url, **kw):
            return _Resp(text='<a href="history-260921.osm.pbf">h</a> 2026-09-24 17:05  152G')
    monkeypatch.setattr(ga, "session", lambda: S())
    monkeypatch.setattr(ga, "OSM_SOURCE", "history")
    ga.check_access({"work": tmp_path, "years": [2015, 2020, 2026]})
    out = capsys.readouterr().out
    assert "FAIL  OSM road extracts (Geofabrik index)" in out and "OK    OSM full-history planet" in out
    df = pd.read_csv(tmp_path / "network_check.csv")
    assert (~df.ok).sum() == 1 and df.purpose.str.contains("GHSL population 2020").any()


# ---------------------------------------------------------------------------
# v3: OSM full history cut at 1 January of each year (needs osmium-tool: found on PATH or
# installed by the script when GA_TEST_INSTALL_OSMIUM=1, as in CI)
# ---------------------------------------------------------------------------
HISTORY_OSH = """<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6" generator="test">
 <node id="1" version="1" timestamp="2014-06-01T00:00:00Z" uid="1" user="a" changeset="1" visible="true" lat="7.00" lon="0.50"/>
 <node id="2" version="1" timestamp="2014-06-01T00:00:00Z" uid="1" user="a" changeset="1" visible="true" lat="7.00" lon="2.50"/>
 <node id="3" version="1" timestamp="2018-03-01T00:00:00Z" uid="1" user="a" changeset="2" visible="true" lat="8.00" lon="0.50"/>
 <node id="4" version="1" timestamp="2018-03-01T00:00:00Z" uid="1" user="a" changeset="2" visible="true" lat="8.00" lon="2.50"/>
 <node id="5" version="1" timestamp="2014-09-01T00:00:00Z" uid="1" user="a" changeset="3" visible="true" lat="6.50" lon="0.50"/>
 <node id="6" version="1" timestamp="2014-09-01T00:00:00Z" uid="1" user="a" changeset="3" visible="true" lat="6.50" lon="1.50"/>
 <way id="10" version="1" timestamp="2014-06-01T00:00:00Z" uid="1" user="a" changeset="1" visible="true">
  <nd ref="1"/><nd ref="2"/><tag k="highway" v="primary"/></way>
 <way id="10" version="2" timestamp="2022-05-01T00:00:00Z" uid="1" user="a" changeset="4" visible="true">
  <nd ref="1"/><nd ref="2"/><tag k="highway" v="trunk"/></way>
 <way id="11" version="1" timestamp="2018-03-01T00:00:00Z" uid="1" user="a" changeset="2" visible="true">
  <nd ref="3"/><nd ref="4"/><tag k="highway" v="residential"/></way>
 <way id="12" version="1" timestamp="2014-09-01T00:00:00Z" uid="1" user="a" changeset="3" visible="true">
  <nd ref="5"/><nd ref="6"/><tag k="highway" v="track"/></way>
 <way id="12" version="2" timestamp="2019-01-01T00:00:00Z" uid="1" user="a" changeset="5" visible="false"/>
 <way id="13" version="1" timestamp="2014-06-01T00:00:00Z" uid="1" user="a" changeset="1" visible="true">
  <nd ref="1"/><nd ref="5"/><tag k="waterway" v="river"/></way>
</osm>
"""


def _osmium_or_skip(work):
    import shutil
    if shutil.which("osmium") or os.environ.get("GA_TEST_INSTALL_OSMIUM") == "1":
        return ga.ensure_osmium(work)
    pytest.skip("osmium-tool not available (set GA_TEST_INSTALL_OSMIUM=1 to let the script install it)")


@pytest.mark.parametrize("bbox", [None, (0, 6, 3, 9)])
def test_history_cut_per_year_and_tiles(tmp_path, monkeypatch, bbox):
    work = tmp_path / "work"; dl = work / "downloads"; dl.mkdir(parents=True)
    _osmium_or_skip(work)
    osh = tmp_path / "history-260105.osh"; osh.write_text(HISTORY_OSH)
    g = ga.Grid((0, 6, 3, 9), D)
    land = gpd.GeoDataFrame({"cid": [1], "iso3": ["AAA"], "ADM0_A3": ["AAA"], "NAME": ["A"],
                             "CONTINENT": ["Africa"]}, geometry=[shapely.box(-1, 5, 4, 10)], crs=4326)
    monkeypatch.setattr(ga, "countries_frame", lambda dl_: land)
    monkeypatch.setattr(ga, "OSM_HISTORY_FILE", str(osh))
    monkeypatch.setattr(ga, "OSM_TILE_DEG", 2)                            # 2 x 2 tiles over the grid
    monkeypatch.setattr(ga, "BBOX", bbox)
    cs = tmp_path / "changesets.osm"; cs.write_text(HISTORY_CHANGESETS)   # never the 8 GB planet dump
    monkeypatch.setattr(ga, "EVENT_CHANGESETS_FILE", str(cs))
    ctx = {"work": work, "dl": dl, "grid": g, "years": [2015, 2020, 2026]}
    plan = ga.osm_history_plan(ctx, None)
    if ga.importlib.util.find_spec("osmium") is not None:              # way metadata from the history
        meta = pd.read_parquet(work / "osm_way_meta.parquet").set_index("osm_id")
        assert sorted(meta.index) == [10, 11, 12] and meta.loc[11, "changeset"] == 2
        tags = pd.read_parquet(work / "osm_changeset_tags.parquet").set_index("changeset")
        assert tags.loc[1, "campaign"] and tags.loc[2, "campaign"]
    assert sorted(plan) == [2015, 2020, 2026] and all(len(v) == 4 for v in plan.values())
    assert all(r["clip"] == r["bounds"] for v in plan.values() for r in v)
    # read back what each year contains
    seen = {}
    for y, rs in plan.items():
        parts = []
        for r in rs:
            try:
                parts.append(ga.pyogrio.read_dataframe(r["file"], layer="lines", columns=["osm_id", "highway"]))
            except Exception:
                pass
        df = pd.concat(parts) if parts else pd.DataFrame(columns=["osm_id", "highway"])
        seen[y] = dict(df.dropna(subset=["highway"]).drop_duplicates("osm_id")[["osm_id", "highway"]]
                       .astype({"osm_id": int}).values.tolist())
    assert seen[2015] == {10: "primary", 12: "track"}                   # 11 not built yet; 13 is a river
    assert seen[2020] == {10: "primary", 11: "residential"}             # 12 deleted in 2019
    assert seen[2026] == {10: "trunk", 11: "residential"}               # 10 upgraded in 2022
    # stage roads: tiles hold complete ways, but lengths are counted once (clipped per tile)
    jobs = [{"pbf": r["file"], "out": str(work / "roads" / f"{r['region']}_2015.npz"), "grid": g.to_dict(),
             "borders": "", "bytes": r["bytes"], "clip": r["clip"]} for r in plan[2015]]
    (work / "roads").mkdir()
    km = sum(ga.roads_job(j).get("km_by_class", {}).get("primary", 0) for j in jobs)
    assert km == pytest.approx(ga.great_circle_km(0.5, 7, 2.5, 7), rel=0.01)   # ~220.7 km, not doubled
    # a rerun does nothing (tiles.done)
    before = {r["file"]: Path(r["file"]).stat().st_mtime for r in plan[2026]}
    ga.osm_history_plan(ctx, None)
    assert all(Path(f).stat().st_mtime == t for f, t in before.items())


def test_history_listing_and_source(monkeypatch):
    import types
    page = ('<a href="history-251229.osm.pbf">history-251229.osm.pbf</a> 2026-01-02 10:00  150G\n'
            '<a href="history-260921.osm.pbf">history-260921.osm.pbf</a> 2026-09-24 17:05  152G\n'
            '<a href="history-latest.osm.pbf">history-latest.osm.pbf</a> 2026-09-24 17:05  152G\n')
    monkeypatch.setattr(ga, "http_request", lambda url, sess, method="HEAD", **kw:
                        types.SimpleNamespace(ok=True, status_code=200, text=page))
    monkeypatch.setattr(ga, "OSM_HISTORY_FILE", None)
    files = ga.history_listing(None)
    assert files == {"history-251229.osm.pbf": 150 * 2**30, "history-260921.osm.pbf": 152 * 2**30}
    local, url, name, size = ga.history_source({"years": [2015, 2020, 2026]}, None)
    assert local is None and name == "history-260921.osm.pbf" and url.endswith("/full-history/history-260921.osm.pbf")
    monkeypatch.setattr(ga, "OSM_HISTORY_FILE", "history-251229.osm.pbf")
    with pytest.raises(SystemExit, match="older than 1 January 2026"):
        ga.history_source({"years": [2015, 2026]}, None)


def test_change_pairs_and_weiss_years():
    assert ga.change_pairs([2015, 2026]) == [(2015, 2026)]
    assert ga.change_pairs([2026, 2015, 2020]) == [(2015, 2020), (2020, 2026), (2015, 2026)]
    assert ga.weiss_needed([2015, 2020, 2026]) and ga.weiss_needed([2020, 2026])
    assert not ga.weiss_needed([2010, 2014])



def test_weiss_years(monkeypatch):
    monkeypatch.setattr(ga, "WEISS2015_AUGMENT", True)
    monkeypatch.setattr(ga, "WEISS_YEARS", None)
    assert ga.weiss_years([2015, 2016, 2020, 2026]) == [2015, 2016, 2020]
    monkeypatch.setattr(ga, "WEISS_YEARS", [])
    assert ga.weiss_years([2015, 2020, 2026]) == [] and not ga.weiss_needed([2015, 2020, 2026])
    monkeypatch.setattr(ga, "WEISS_YEARS", [2015, 2026])
    assert ga.weiss_years([2015, 2020, 2026]) == [2015]                    # never the last year
    monkeypatch.setattr(ga, "WEISS2015_AUGMENT", False)
    assert ga.weiss_years([2015, 2020, 2026]) == []


def test_stage_events_codes_and_bursts(tmp_path):
    """Cell events from the OSM road rasters; bursts from new-way km per 0.1 deg cell, user and tags."""
    g = ga.Grid((0, 6, 1, 7), D)                                          # 120 x 120 cells; 10 x 10 burst cells
    work = tmp_path / "work"
    r15 = np.zeros(g.shape, np.float32); r15[10, :] = 70; r15[50, :] = 40; r15[80, :] = 30
    r20 = r15.copy(); r20[50, :] = 55                                     # upgrade (40 -> 55)
    r20[80, :] = 0                                                        # removed
    r20[:, 5] = np.maximum(r20[:, 5], 20)                                 # one long new road (column 5)
    r20[30, 36:48] = 25                                                   # dense new mapping in burst cell (2, 3)
    r20[97, 95] = 15                                                      # short new road from a HOT changeset
    r20[10, 60:] = 49                                                     # slower (reclassified)
    for y, r in ((2015, r15), (2020, r20)):
        (work / "roads" / str(y)).mkdir(parents=True)
        np.save(work / f"road_speed_{y}.npy", r)
    old = pd.DataFrame({"osm_id": [1, 2], "highway": ["primary", "tertiary"], "speed": [70.0, 40.0],
                        "brow": [0, 4], "bcol": [0, 0], "km": [110.0, 110.0], "clipped": [True, True]})
    gone = pd.DataFrame({"osm_id": [3], "highway": ["unclassified"], "speed": [30.0], "brow": [6], "bcol": [0],
                         "km": [110.0], "clipped": [True]})
    long_road = pd.DataFrame({"osm_id": 10, "highway": "residential", "speed": 20.0, "brow": range(10), "bcol": 0,
                              "km": 11.1, "clipped": True})
    dense = pd.DataFrame({"osm_id": [12], "highway": ["track"], "speed": [15.0], "brow": [2], "bcol": [3],
                          "km": [30.0], "clipped": [True]})
    hot = pd.DataFrame({"osm_id": [11], "highway": ["track"], "speed": [15.0], "brow": [8], "bcol": [7],
                        "km": [4.6], "clipped": [True]})
    pd.concat([old, gone]).to_parquet(work / "roads" / "2015" / "t.ways.parquet")
    pd.concat([old, long_road, dense, hot]).to_parquet(work / "roads" / "2020" / "t.ways.parquet")
    pd.DataFrame({"osm_id": [10, 11, 12], "version": [1, 1, 1],
                  "timestamp": pd.to_datetime(["2019-05-01", "2019-06-01", "2019-07-01"], utc=True),
                  "changeset": [100, 101, 102], "uid": [7, 8, 9]}).to_parquet(work / "osm_way_meta.parquet")
    pd.DataFrame({"changeset": [100, 101, 102], "comment": ["", "#hotosm-project-1234", ""], "hashtags": [""] * 3,
                  "created_by": ["JOSM", "iD", "JOSM"], "source": [""] * 3, "imagery_used": [""] * 3,
                  "data_used": [""] * 3, "campaign": [False, True, False]}).to_parquet(work / "osm_changeset_tags.parquet")
    ga.stage_events({"grid": g, "work": work, "years": [2015, 2020]})
    ev = np.load(work / "road_events_2020.npy"); code = ev & 15
    assert (code[50, :] == 2).all() and (code[80, 6:] == 4).all() and code[80, 5] == 3 and (code[10, 60:] == 3).all()
    assert code[30, 5] == 1 and ev[30, 5] < 16                            # one long road: 11 km per cell, no burst
    assert (ev[30, 36:48] >= 16).all() and ev[97, 95] >= 16                # one user, 30 km in a cell; HOT changeset
    assert (ev[50, :] < 16).all()
    b = pd.read_csv(work / "osm_burst_cells.csv")
    assert b.burst.sum() == 2 and len(b) == 12                            # 10 cells of the long road + 2
    sm = pd.read_csv(work / "road_events_summary.csv").set_index("event")
    assert sm.loc["road removed", "cells"] == 119 and sm.loc["new ways (km)", "cells"] == pytest.approx(145.6, abs=0.2)


def test_way_cells_split_length():
    g = ga.Grid((0, 6, 1, 7), D)
    line = shapely.LineString([(0.05, 6.95), (0.95, 6.95)])               # ~99 km along 6.95 N
    w = ga.way_cells(np.array([line]), np.array([5]), g)
    assert set(w.bcol) == set(range(10)) and set(w.brow) == {0}
    assert w.km.sum() == pytest.approx(ga.great_circle_km(0.05, 6.95, 0.95, 6.95), rel=1e-3)


HISTORY_CHANGESETS = """<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6" generator="test">
 <changeset id="1" created_at="2014-06-01T00:00:00Z" closed_at="2014-06-01T01:00:00Z" open="false" num_changes="3" user="a" uid="1" min_lat="6" min_lon="0" max_lat="8" max_lon="3" comments_count="0">
  <tag k="comment" v="roads #hotosm-project-42"/><tag k="created_by" v="iD 2.0"/>
 </changeset>
 <changeset id="2" created_at="2018-03-01T00:00:00Z" closed_at="2018-03-01T01:00:00Z" open="false" num_changes="3" user="a" uid="1" min_lat="6" min_lon="0" max_lat="8" max_lon="3" comments_count="0">
  <tag k="comment" v="village road"/><tag k="created_by" v="Rapid 2.1"/><tag k="data_used" v="MapWithAI"/>
 </changeset>
 <changeset id="9" created_at="2018-03-01T00:00:00Z" closed_at="2018-03-01T01:00:00Z" open="false" num_changes="1" user="b" uid="2" min_lat="6" min_lon="0" max_lat="8" max_lon="3" comments_count="0">
  <tag k="comment" v="unrelated"/>
 </changeset>
</osm>
"""


def test_history_way_meta_and_changesets(tmp_path):
    pytest.importorskip("osmium")
    osh = tmp_path / "h.osh"; osh.write_text(HISTORY_OSH)
    m = pd.read_parquet(ga.history_way_meta(osh, tmp_path / "meta.parquet")).set_index("osm_id")
    assert sorted(m.index) == [10, 11, 12]                                 # 13 is a river
    assert m.loc[10, "version"] == 1 and m.loc[10, "changeset"] == 1 and m.loc[11, "changeset"] == 2
    assert str(m.loc[11, "timestamp"])[:10] == "2018-03-01"
    cs = tmp_path / "cs.osm"; cs.write_text(HISTORY_CHANGESETS)
    t = ga.changeset_campaigns(cs, m.changeset.unique(), tmp_path / "cs.parquet").set_index("changeset")
    assert set(t.index) == {1, 2}                                         # changeset 3 is not in the dump
    assert t.loc[1, "campaign"] and t.loc[2, "campaign"] and t.loc[2, "data_used"] == "MapWithAI"


def test_fetch_wgi_pages_and_retries(monkeypatch):
    import types
    monkeypatch.setattr(ga.time, "sleep", lambda s: None)
    calls = []

    class S:
        def request(self, method, url, **kw):
            calls.append(kw["params"]["page"])
            if len(calls) == 1:
                raise ga.requests.ReadTimeout("slow")                   # first try times out, then retried
            p = kw["params"]["page"]
            data = [{"countryiso3code": "BEN", "date": str(2000 + p), "value": 40.0 + p},
                    {"countryiso3code": "", "date": "2000", "value": 1.0},
                    {"countryiso3code": "TGO", "date": "2001", "value": None}]
            return types.SimpleNamespace(ok=True, status_code=200, headers={},
                                         json=lambda: [{"pages": 2}, data])
    rows = ga.fetch_wgi(S(), per_page=3)
    assert calls == [1, 1, 2] and rows == [{"iso3": "BEN", "year": 2001, "score": 41.0},
                                           {"iso3": "BEN", "year": 2002, "score": 42.0}]


def test_stage_events_resumed_from_older_roads_stage(tmp_path, monkeypatch):
    """HPC case: stage roads ran with a version that wrote no way tables, and no new way forms a
    burst. Missing tables are rebuilt from the OSM files; empty burst tables keep integer indices."""
    g = ga.Grid((0, 6, 3, 7), D)
    work = tmp_path / "work"; dl = work / "downloads"
    for y in (2015, 2020):
        (dl / "osm" / str(y)).mkdir(parents=True)
        (dl / "osm" / str(y) / "x.osm").write_text(OSM)                   # same roads both years
    (work / "osm_plan.json").write_text(json.dumps({str(y): [{"region": "x", "file": str(dl / "osm" / str(y) / "x.osm"),
                                                             "bytes": 1, "clip": None}] for y in (2015, 2020)}))
    r = np.zeros(g.shape, np.float32); r[100, :] = 70
    np.save(work / "road_speed_2015.npy", r); np.save(work / "road_speed_2020.npy", r)
    monkeypatch.setattr(ga, "OSM_SOURCE", "geofabrik")
    ctx = {"grid": g, "work": work, "dl": dl, "years": [2015, 2020]}
    ga.stage_events(ctx)
    assert (work / "roads" / "2020" / "x.ways.parquet").exists()
    b = pd.read_csv(work / "osm_burst_cells.csv")
    assert b.empty and (np.load(work / "road_events_2020.npy") == 0).all()
    # a source file that is gone cannot be rebuilt: say so clearly
    (work / "roads" / "2020" / "x.ways.parquet").unlink(); (dl / "osm" / "2020" / "x.osm").unlink()
    with pytest.raises(RuntimeError, match="rerun stage roads"):
        ga.stage_events(ctx)


def test_burst_cells_vectorised_matches_rule():
    g = ga.Grid((0, 6, 1, 7), D)
    new = pd.DataFrame({"osm_id": [1, 2, 3, 4, 7, 5, 6], "year": 2020, "brow": [0, 0, 0, 0, 0, 5, 5],
                        "bcol": [0, 0, 0, 0, 0, 5, 5], "km": [10.0, 10.0, 5.0, 1.0, 4.0, 20.0, 20.0],
                        "uid": [1, 1, 2, 9, 10, 1, 2], "campaign": [False] * 7, "highway": "track"})
    t = ga.burst_cells(new, g, True).set_index(["brow", "bcol"])
    # cell (0, 0): users 1 (20 km), 2 (5), 10 (4), 9 (1): top three = 29 of 30 km
    assert t.loc[(0, 0), "new_km"] == 30 and t.loc[(0, 0), "top_users_share"] == pytest.approx(29 / 30)
    assert t.loc[(0, 0), "burst"]
    assert t.loc[(5, 5), "new_km"] == 40 and t.loc[(5, 5), "top_users_share"] == 1.0 and t.loc[(5, 5), "burst"]
    e = ga.burst_cells(new.iloc[:0], g, True)
    assert e.empty and e.brow.dtype == np.int64


def test_review_fixes_empty_tiles_plan_years_history_file(tmp_path, monkeypatch):
    g = ga.Grid((0, 6, 1, 7), D)
    work = tmp_path / "work"; dl = work / "downloads"; (dl / "osm" / "2015").mkdir(parents=True)
    (work / "roads" / "2015").mkdir(parents=True)
    plan = {"2015": [{"region": "sea", "file": str(dl / "osm" / "2015" / "sea.osm.pbf"), "bytes": 10, "clip": [0, 6, 1, 7],
                      "source": "history-251229.osm.pbf"}]}
    (work / "osm_plan.json").write_text(json.dumps(plan))
    (work / "roads" / "2015" / "sea.done").write_text(json.dumps({"extract": "sea.osm.pbf", "segments": 0}))
    ctx = {"grid": g, "work": work, "dl": dl, "years": [2015]}
    ga.ensure_way_tables(ctx)                                             # tile without roads, file gone: no error
    assert pd.read_parquet(work / "roads" / "2015" / "sea.ways.parquet").empty
    with pytest.raises(RuntimeError, match="no OSM files for 2020"):
        ga.road_jobs({**ctx, "years": [2015, 2020]}, 2020)
    # the history file is found on disk from the plan, without the network
    (dl / "osm" / "history-251229.osm.pbf").write_bytes(b"x"); (dl / "osm" / "history-260921.osm.pbf").write_bytes(b"y")
    monkeypatch.setattr(ga, "OSM_HISTORY_FILE", None)
    assert ga.local_history_file(ctx).name == "history-251229.osm.pbf"
    (work / "osm_plan.json").unlink()
    assert ga.local_history_file(ctx).name == "history-260921.osm.pbf"


def test_read_rows_for_ids(tmp_path):
    f = tmp_path / "m.parquet"
    pd.DataFrame({"osm_id": np.arange(100, dtype=np.int64), "uid": np.arange(100) % 7}).to_parquet(f)
    d = ga.read_rows_for_ids(f, ["osm_id", "uid"], [3, 50, 1000])
    assert sorted(d.osm_id) == [3, 50] and list(d.columns) == ["osm_id", "uid"]


def test_event_metadata_without_changeset_dump(tmp_path, monkeypatch):
    pytest.importorskip("osmium")
    osh = tmp_path / "h.osh"; osh.write_text(HISTORY_OSH)
    work = tmp_path / "w"; (work / "downloads" / "osm").mkdir(parents=True)

    def down(*a, **k):
        raise ga.RemoteUnavailable("blocked")
    monkeypatch.setattr(ga, "download", down)
    monkeypatch.setattr(ga, "EVENT_CHANGESETS_FILE", None)
    ga.osm_event_metadata({"work": work, "dl": work / "downloads"}, osh, None, None)   # no osmium-tool, dump blocked
    assert (work / "osm_way_meta.parquet").exists() and not (work / "osm_changeset_tags.parquet").exists()


def test_read_rows_for_ids_empty(tmp_path):
    f = tmp_path / "m.parquet"
    pd.DataFrame({"osm_id": np.arange(5, dtype=np.int64), "uid": np.arange(5)}).to_parquet(f)
    d = ga.read_rows_for_ids(f, ["osm_id", "uid"], [])
    assert len(d) == 0 and list(d.columns) == ["osm_id", "uid"] and d.osm_id.dtype == np.int64


def test_changeset_tags_missing_file_does_not_stop(tmp_path, monkeypatch):
    work = tmp_path / "w"; work.mkdir()
    pd.DataFrame({"osm_id": [1], "uid": [2], "changeset": [3]}).to_parquet(work / "osm_way_meta.parquet")
    monkeypatch.setattr(ga, "EVENT_CHANGESETS_FILE", str(tmp_path / "missing.osm.bz2"))
    ga.osm_changeset_tags({"work": work, "dl": work / "downloads"}, None)
    assert not (work / "osm_changeset_tags.parquet").exists()
    bad = tmp_path / "bad.osm.bz2"; bad.write_bytes(b"not bzip2")
    monkeypatch.setattr(ga, "EVENT_CHANGESETS_FILE", str(bad))
    ga.osm_changeset_tags({"work": work, "dl": work / "downloads"}, None)   # parse error logged, not raised
    assert not (work / "osm_changeset_tags.parquet").exists()


def test_stage_roads_needs_plan(tmp_path):
    with pytest.raises(RuntimeError, match="osm_plan.json"):
        ga.stage_roads({"grid": ga.Grid((0, 0, 1, 1), 0.1), "work": tmp_path, "years": [2020]})


def test_way_cells_skips_degenerate_ways():
    g = ga.Grid((0, 0, 1, 1), 1 / 120)
    good = LineString([(0.10, 0.50), (0.30, 0.50)])
    zero = shapely.from_wkt("LINESTRING (0.2 0.2, 0.2 0.2)")          # the HPC failure case
    three = shapely.from_wkt("LINESTRING (0.4 0.4, 0.4 0.4, 0.4 0.4)")
    lines = np.array([good, zero, three, shapely.LineString(), None], dtype=object)
    d = ga.way_cells(lines, np.array([1, 2, 3, 4, 5]), g)
    assert set(d.osm_id) == {1}
    assert d[d.osm_id == 1].km.sum() == pytest.approx(22.2, rel=0.01)


def test_store_temp_folder_is_unique_per_grid(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(ga, "store_job", lambda job: seen.append(job["tmp"]))
    monkeypatch.setattr(ga, "store_items", lambda ctx: [
        ("traveltime", y, "ports_3", f"tt_{y}.npy", "minutes", "x") for y in (2015, 2020)])
    for y in (2015, 2020):
        np.save(tmp_path / f"tt_{y}.npy", np.zeros((2, 2), np.float32))
    ctx = {"grid": ga.Grid((0, 0, 1, 1), 0.5), "work": tmp_path, "results": tmp_path / "res", "years": [2015, 2020],
           "epoch": {2015: 2015, 2020: 2020}}
    try:
        ga.stage_store(ctx)
    except Exception:
        pass                                 # later steps need real outputs; only the temp folders matter here
    assert len(seen) == 2 and len(set(seen)) == 2
